import os
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from app.core.config import get_settings
from app.core.redis_client import RedisClient
from app.services.file_manager import FileManager

logger = logging.getLogger(__name__)

class StorageManager:
    """Hybrid PDF storage management service"""
    
    def __init__(self, redis_client: RedisClient):
        self.settings = get_settings()
        self.redis = redis_client
        self.file_manager = FileManager()
    
    async def check_and_cleanup_storage(self) -> Dict[str, Any]:
        """
        Check storage limits and perform cleanup if necessary.
        Returns cleanup statistics.
        """
        try:
            # Get current storage stats
            stats = await self.redis.get_storage_stats()
            
            cleanup_stats = {
                "initial_count": stats["total_pdfs"],
                "initial_size_mb": stats["total_size_mb"],
                "deleted_count": 0,
                "deleted_size_mb": 0,
                "final_count": 0,
                "final_size_mb": 0,
                "cleanup_reason": []
            }
            
            # Check if cleanup is needed
            needs_cleanup = False
            
            # Check count limit
            if stats["total_pdfs"] > self.settings.max_stored_pdfs:
                needs_cleanup = True
                cleanup_stats["cleanup_reason"].append(f"PDF count ({stats['total_pdfs']}) exceeds limit ({self.settings.max_stored_pdfs})")
            
            # Check size limit
            if stats["total_size_mb"] > self.settings.max_storage_size_mb:
                needs_cleanup = True
                cleanup_stats["cleanup_reason"].append(f"Storage size ({stats['total_size_mb']}MB) exceeds limit ({self.settings.max_storage_size_mb}MB)")
            
            if not needs_cleanup:
                logger.info(f"Storage within limits: {stats['total_pdfs']} PDFs, {stats['total_size_mb']}MB")
                cleanup_stats["final_count"] = stats["total_pdfs"]
                cleanup_stats["final_size_mb"] = stats["total_size_mb"]
                return cleanup_stats
            
            # Perform cleanup
            logger.info(f"Storage cleanup needed: {', '.join(cleanup_stats['cleanup_reason'])}")
            deleted_pdfs = await self._perform_smart_cleanup(stats["pdfs"])
            
            # Calculate cleanup stats
            cleanup_stats["deleted_count"] = len(deleted_pdfs)
            cleanup_stats["deleted_size_mb"] = round(sum(pdf.get("file_size", 0) for pdf in deleted_pdfs) / (1024 * 1024), 2)
            
            # Get final stats
            final_stats = await self.redis.get_storage_stats()
            cleanup_stats["final_count"] = final_stats["total_pdfs"]
            cleanup_stats["final_size_mb"] = final_stats["total_size_mb"]
            
            logger.info(f"Storage cleanup completed: deleted {cleanup_stats['deleted_count']} PDFs ({cleanup_stats['deleted_size_mb']}MB)")
            
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Error during storage cleanup: {e}")
            return cleanup_stats
    
    async def _perform_smart_cleanup(self, pdfs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Perform smart cleanup using hybrid approach.
        Returns list of deleted PDF metadata.
        """
        deleted_pdfs = []
        
        # Filter PDFs that can be deleted (respect minimum retention time)
        min_retention_time = datetime.utcnow() - timedelta(hours=self.settings.min_retention_hours)
        deletable_pdfs = []
        
        for pdf in pdfs:
            try:
                created_at = datetime.fromisoformat(pdf.get("created_at", "").replace('Z', '+00:00'))
                if created_at < min_retention_time:
                    deletable_pdfs.append(pdf)
            except (ValueError, TypeError):
                # If we can't parse the date, consider it deletable for safety
                deletable_pdfs.append(pdf)
        
        if not deletable_pdfs:
            logger.warning("No PDFs can be deleted due to minimum retention time constraint")
            return deleted_pdfs
        
        # Sort PDFs by deletion priority (smart cleanup)
        prioritized_pdfs = self._prioritize_pdfs_for_deletion(deletable_pdfs)
        
        # Calculate how many PDFs to delete
        current_count = len(pdfs)
        current_size_mb = sum(pdf.get("file_size", 0) for pdf in pdfs) / (1024 * 1024)
        
        # Delete PDFs in batches until we're within limits
        batch_size = min(self.settings.cleanup_batch_size, len(prioritized_pdfs))
        
        for i in range(0, len(prioritized_pdfs), batch_size):
            batch = prioritized_pdfs[i:i + batch_size]
            
            for pdf in batch:
                try:
                    # Delete physical file
                    file_path = pdf.get("file_path")
                    if file_path and os.path.exists(file_path):
                        await self.file_manager.delete_file(file_path)
                    
                    # Delete preview images
                    await self._delete_pdf_preview_images(pdf)
                    
                    # Delete from Redis
                    pdf_id = pdf.get("id")
                    if pdf_id:
                        await self.redis.delete_pdf_document(pdf_id)
                    
                    deleted_pdfs.append(pdf)
                    current_count -= 1
                    current_size_mb -= pdf.get("file_size", 0) / (1024 * 1024)
                    
                    logger.info(f"Deleted PDF: {pdf.get('original_filename', 'unknown')} ({pdf.get('id', 'unknown')})")
                    
                except Exception as e:
                    logger.error(f"Error deleting PDF {pdf.get('id', 'unknown')}: {e}")
            
            # Check if we're now within limits
            if (current_count <= self.settings.max_stored_pdfs and 
                current_size_mb <= self.settings.max_storage_size_mb):
                break
        
        return deleted_pdfs
    
    def _prioritize_pdfs_for_deletion(self, pdfs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prioritize PDFs for deletion using smart criteria.
        Returns PDFs sorted by deletion priority (highest priority first).
        """
        def calculate_priority(pdf: Dict[str, Any]) -> float:
            priority = 0.0
            
            # Age factor (older = higher priority for deletion)
            try:
                created_at = datetime.fromisoformat(pdf.get("created_at", "").replace('Z', '+00:00'))
                age_days = (datetime.utcnow() - created_at).days
                priority += age_days * 5  # 5 points per day (reduced from 10)
            except (ValueError, TypeError):
                priority += 500  # High priority if we can't parse date (reduced from 1000)
            
            # Size factor (larger = higher priority for deletion)
            file_size_mb = pdf.get("file_size", 0) / (1024 * 1024)
            priority += file_size_mb * 3  # 3 points per MB (increased from 2)
            
            # Processing status factor (unprocessed = higher priority for deletion)
            if not pdf.get("is_processed", False):
                priority += 100  # 100 points for unprocessed PDFs (increased from 50)
            
            # Last access factor (less recently accessed = higher priority)
            try:
                last_accessed = pdf.get("last_accessed_at")
                if last_accessed:
                    last_access_time = datetime.fromisoformat(last_accessed.replace('Z', '+00:00'))
                    days_since_access = (datetime.utcnow() - last_access_time).days
                    priority += days_since_access * 3  # 3 points per day since last access (reduced from 5)
                else:
                    # Never accessed since tracking started
                    priority += 75  # 75 points for never accessed (reduced from 100)
            except (ValueError, TypeError):
                priority += 75
            
            return priority
        
        # Sort by priority (highest first)
        return sorted(pdfs, key=calculate_priority, reverse=True)
    
    async def _delete_pdf_preview_images(self, pdf: Dict[str, Any]) -> None:
        """Delete preview images associated with a PDF"""
        try:
            filename = pdf.get("filename", "")
            if filename:
                pdf_name = os.path.splitext(filename)[0]
                static_dir = self.settings.static_dir
                
                # Look for preview images with the pattern {pdf_name}_page_*.jpg
                if os.path.exists(static_dir):
                    for item in os.listdir(static_dir):
                        if item.startswith(f"{pdf_name}_page_") and item.endswith(".jpg"):
                            preview_path = os.path.join(static_dir, item)
                            await self.file_manager.delete_file(preview_path)
        except Exception as e:
            logger.error(f"Error deleting preview images for PDF {pdf.get('id', 'unknown')}: {e}")
    
    async def trigger_cleanup_if_needed(self) -> Optional[Dict[str, Any]]:
        """
        Trigger cleanup only if storage limits are exceeded.
        Returns cleanup stats if cleanup was performed, None otherwise.
        """
        stats = await self.redis.get_storage_stats()
        
        if (stats["total_pdfs"] > self.settings.max_stored_pdfs or 
            stats["total_size_mb"] > self.settings.max_storage_size_mb):
            return await self.check_and_cleanup_storage()
        
        return None
    
    async def get_storage_info(self) -> Dict[str, Any]:
        """Get detailed storage information"""
        stats = await self.redis.get_storage_stats()
        
        return {
            **stats,
            "limits": {
                "max_pdfs": self.settings.max_stored_pdfs,
                "max_size_mb": self.settings.max_storage_size_mb,
                "min_retention_hours": self.settings.min_retention_hours
            },
            "usage_percentage": {
                "count": round((stats["total_pdfs"] / self.settings.max_stored_pdfs) * 100, 1) if self.settings.max_stored_pdfs > 0 else 0,
                "size": round((stats["total_size_mb"] / self.settings.max_storage_size_mb) * 100, 1) if self.settings.max_storage_size_mb > 0 else 0
            }
        } 