try:
    import redis.asyncio as redis
except ImportError:
    # Fallback for development when redis is not installed
    redis = None

import json
import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis client for data storage and caching"""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis: Optional[Any] = None  # Use Any to avoid type issues during development
    
    async def connect(self):
        """Connect to Redis"""
        if redis is None:
            raise RuntimeError("Redis package not installed. Please install redis package.")
        
        try:
            self.redis = redis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.redis.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
    
    def _ensure_connected(self):
        """Ensure Redis is connected"""
        if self.redis is None:
            raise RuntimeError("Redis client not connected. Call connect() first.")
    
    # PDF Document operations
    async def save_pdf_document(self, pdf_id: str, data: Dict[str, Any], ttl_hours: int = 24) -> bool:
        """Save PDF document metadata"""
        try:
            self._ensure_connected()
            key = f"pdf:{pdf_id}"
            data["created_at"] = datetime.utcnow().isoformat()
            data["updated_at"] = datetime.utcnow().isoformat()
            
            await self.redis.hset(key, mapping={k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in data.items()})  # type: ignore
            await self.redis.expire(key, timedelta(hours=ttl_hours))  # type: ignore
            return True
        except Exception as e:
            logger.error(f"Error saving PDF document {pdf_id}: {e}")
            return False
    
    async def get_pdf_document(self, pdf_id: str) -> Optional[Dict[str, Any]]:
        """Get PDF document metadata"""
        try:
            self._ensure_connected()
            key = f"pdf:{pdf_id}"
            data = await self.redis.hgetall(key)  # type: ignore
            if not data:
                return None
            
            # Parse JSON fields
            for field in ["pdf_metadata"]:
                if field in data and data[field]:
                    try:
                        data[field] = json.loads(data[field])
                    except json.JSONDecodeError:
                        pass
            
            # Convert numeric fields
            for field in ["file_size", "total_pages"]:
                if field in data and data[field]:
                    try:
                        data[field] = int(data[field])
                    except ValueError:
                        pass
            
            # Convert boolean fields
            for field in ["is_processed"]:
                if field in data and data[field]:
                    data[field] = data[field].lower() == "true"
            
            return data
        except Exception as e:
            logger.error(f"Error getting PDF document {pdf_id}: {e}")
            return None
    
    async def get_all_pdf_documents(self) -> List[Dict[str, Any]]:
        """Get all PDF documents sorted by creation time (oldest first)"""
        try:
            self._ensure_connected()
            # Get all PDF keys
            keys = await self.redis.keys("pdf:*")  # type: ignore
            if not keys:
                return []
            
            pdfs = []
            for key in keys:
                # Handle both string and bytes keys
                if isinstance(key, bytes):
                    pdf_id = key.decode('utf-8').split(':', 1)[1]
                else:
                    pdf_id = key.split(':', 1)[1]
                pdf_data = await self.get_pdf_document(pdf_id)
                if pdf_data:
                    pdfs.append(pdf_data)
            
            # Sort by creation time (oldest first)
            pdfs.sort(key=lambda x: x.get('created_at', ''))
            return pdfs
        except Exception as e:
            logger.error(f"Error getting all PDF documents: {e}")
            return []
    
    async def delete_pdf_document(self, pdf_id: str) -> bool:
        """Delete PDF document metadata from Redis"""
        try:
            self._ensure_connected()
            key = f"pdf:{pdf_id}"
            result = await self.redis.delete(key)  # type: ignore
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting PDF document {pdf_id}: {e}")
            return False
    
    async def update_pdf_access_time(self, pdf_id: str) -> bool:
        """Update the last access time for a PDF document"""
        try:
            self._ensure_connected()
            key = f"pdf:{pdf_id}"
            updates = {
                "last_accessed_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            await self.redis.hset(key, mapping=updates)  # type: ignore
            return True
        except Exception as e:
            logger.error(f"Error updating PDF access time {pdf_id}: {e}")
            return False
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get current storage statistics"""
        try:
            self._ensure_connected()
            pdfs = await self.get_all_pdf_documents()
            
            total_count = len(pdfs)
            total_size = sum(pdf.get('file_size', 0) for pdf in pdfs)
            
            return {
                "total_pdfs": total_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "pdfs": pdfs
            }
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {"total_pdfs": 0, "total_size_bytes": 0, "total_size_mb": 0, "pdfs": []}
    
    # Conversion Job operations
    async def save_conversion_job(self, job_id: str, data: Dict[str, Any], ttl_hours: int = 48) -> bool:
        """Save conversion job"""
        try:
            self._ensure_connected()
            key = f"job:{job_id}"
            data["created_at"] = data.get("created_at", datetime.utcnow().isoformat())
            data["updated_at"] = datetime.utcnow().isoformat()
            
            await self.redis.hset(key, mapping={k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in data.items()})  # type: ignore
            await self.redis.expire(key, timedelta(hours=ttl_hours))  # type: ignore
            
            # Add to job list for tracking
            await self.redis.lpush("jobs:all", job_id)  # type: ignore
            await self.redis.expire("jobs:all", timedelta(hours=ttl_hours))  # type: ignore
            
            return True
        except Exception as e:
            logger.error(f"Error saving conversion job {job_id}: {e}")
            return False
    
    async def get_conversion_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get conversion job"""
        try:
            self._ensure_connected()
            key = f"job:{job_id}"
            data = await self.redis.hgetall(key)  # type: ignore
            if not data:
                return None
            
            # Helper function to convert string 'None' to actual None
            def convert_none(value):
                if value == 'None' or value is None:
                    return None
                return value
            
            # Helper function to convert string to int, handling 'None'
            def convert_int(value):
                if value == 'None' or value is None:
                    return None
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return None
            
            # Helper function to convert string to float, handling 'None'
            def convert_float(value):
                if value == 'None' or value is None:
                    return None
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return None
            
            # Helper function to convert string to bool, handling 'None'
            def convert_bool(value):
                if value == 'None' or value is None:
                    return None
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() == "true"
                return None
            
            # Parse JSON fields
            for field in ["selected_pages", "output_metadata", "languages"]:
                if field in data and data[field] and data[field] != 'None':
                    try:
                        data[field] = json.loads(data[field])
                    except json.JSONDecodeError:
                        data[field] = None
                else:
                    data[field] = None
            
            # Convert numeric fields (integers)
            int_fields = [
                "progress",  # Removed pdf_document_id as it should be a string
                # Performance & Quality Options
                "lowres_image_dpi", "highres_image_dpi", "layout_batch_size", 
                "detection_batch_size", "recognition_batch_size",
                # Table Processing Options
                "table_rec_batch_size", "max_table_rows", "max_rows_per_batch",
                # Section & Header Processing
                "level_count", "default_level",
                # Advanced Processing Options
                "equation_batch_size",
                # LLM Processing Options
                "max_concurrency"
            ]
            for field in int_fields:
                if field in data:
                    data[field] = convert_int(data[field])
            
            # Convert float fields
            float_fields = [
                # Layout & Structure Options
                "column_gap_ratio", "gap_threshold", "list_gap_threshold",
                # Section & Header Processing
                "merge_threshold",
                # Advanced Processing Options
                "min_equation_height", "inlinemath_min_ratio",
                # LLM Processing Options
                "confidence_threshold"
            ]
            for field in float_fields:
                if field in data:
                    data[field] = convert_float(data[field])
            
            # Convert boolean fields
            bool_fields = [
                # Basic marker options
                "use_llm", "force_ocr", "strip_existing_ocr", "format_lines", 
                "redo_inline_math", "disable_image_extraction", "paginate_output",
                # OCR & Text Processing Options
                "disable_ocr_math", "keep_chars",
                # Table Processing Options
                "detect_boxes",
                # Output Control Options
                "extract_images",
                # Debug Options
                "debug", "debug_layout_images", "debug_pdf_images", "debug_json"
            ]
            for field in bool_fields:
                if field in data:
                    data[field] = convert_bool(data[field])
            
            # Convert string fields that might be 'None'
            string_fields = [
                "ocr_task_name", "force_layout_block", "page_separator", 
                "debug_data_folder", "llm_service", "llm_model",
                "gemini_api_key", "openai_api_key", "claude_api_key",
                "output_file_path", "error_message"
            ]
            for field in string_fields:
                if field in data:
                    data[field] = convert_none(data[field])
            
            return data
        except Exception as e:
            logger.error(f"Error getting conversion job {job_id}: {e}")
            return None
    
    async def update_job_status(self, job_id: str, status: str, progress: Optional[int] = None, 
                               error_message: Optional[str] = None, output_path: Optional[str] = None,
                               output_metadata: Optional[Dict] = None) -> bool:
        """Update job status and progress"""
        try:
            self._ensure_connected()
            key = f"job:{job_id}"
            updates = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if progress is not None:
                updates["progress"] = str(progress)
            if error_message is not None:
                updates["error_message"] = error_message
            if output_path is not None:
                updates["output_file_path"] = output_path
            if output_metadata is not None:
                updates["output_metadata"] = json.dumps(output_metadata)
            
            if status == "processing":
                updates["started_at"] = datetime.utcnow().isoformat()
            elif status in ["completed", "failed", "cancelled"]:
                updates["completed_at"] = datetime.utcnow().isoformat()
            
            await self.redis.hset(key, mapping=updates)  # type: ignore
            return True
        except Exception as e:
            logger.error(f"Error updating job status {job_id}: {e}")
            return False
    
    # User Settings operations
    async def save_user_settings(self, settings_data: Dict[str, Any]) -> bool:
        """Save user settings (persistent)"""
        try:
            self._ensure_connected()
            key = "settings:user"
            settings_data["updated_at"] = datetime.utcnow().isoformat()
            
            await self.redis.hset(key, mapping={k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in settings_data.items()})  # type: ignore
            return True
        except Exception as e:
            logger.error(f"Error saving user settings: {e}")
            return False
    
    async def get_user_settings(self) -> Optional[Dict[str, Any]]:
        """Get user settings"""
        try:
            self._ensure_connected()
            key = "settings:user"
            data = await self.redis.hgetall(key)  # type: ignore
            if not data:
                return None
            
            # Parse JSON fields
            for field in ["additional_settings"]:
                if field in data and data[field]:
                    try:
                        data[field] = json.loads(data[field])
                    except json.JSONDecodeError:
                        pass
            
            # Convert boolean fields
            for field in ["default_use_llm", "default_force_ocr", "default_format_lines"]:
                if field in data and data[field]:
                    data[field] = data[field].lower() == "true"
            
            return data
        except Exception as e:
            logger.error(f"Error getting user settings: {e}")
            return None
    
    # Utility methods
    async def generate_id(self, prefix: str) -> str:
        """Generate a unique ID"""
        self._ensure_connected()
        counter = await self.redis.incr(f"counter:{prefix}")  # type: ignore
        return f"{prefix}_{counter}"
    
    async def cleanup_expired_jobs(self) -> int:
        """Clean up expired job references"""
        try:
            self._ensure_connected()
            job_ids = await self.redis.lrange("jobs:all", 0, -1)  # type: ignore
            cleaned = 0
            
            for job_id in job_ids:
                exists = await self.redis.exists(f"job:{job_id}")  # type: ignore
                if not exists:
                    await self.redis.lrem("jobs:all", 1, job_id)  # type: ignore
                    cleaned += 1
            
            return cleaned
        except Exception as e:
            logger.error(f"Error cleaning up expired jobs: {e}")
            return 0

# Global Redis client instance
redis_client = RedisClient()

async def get_redis() -> RedisClient:
    """Dependency to get Redis client"""
    return redis_client

async def init_redis():
    """Initialize Redis connection"""
    await redis_client.connect()
    logger.info("Redis initialized successfully")

async def close_redis():
    """Close Redis connection"""
    await redis_client.disconnect()
    logger.info("Redis connection closed") 