from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from typing import List
import os
import logging
from datetime import datetime

from app.core.redis_client import get_redis, RedisClient
from app.schemas.models import PDFDocument
from app.schemas.pdf import PDFUploadResponse
from app.services.file_manager import FileManager
from app.services.marker_service import MarkerService
from app.services.storage_manager import StorageManager
from app.core.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload", response_model=PDFUploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    redis: RedisClient = Depends(get_redis)
):
    """Upload a PDF file"""
    settings = get_settings()
    
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Check file size
    content = await file.read()
    if len(content) > settings.max_file_size:
        raise HTTPException(status_code=400, detail="File too large")
    
    # Reset file pointer
    await file.seek(0)
    
    try:
        # Save file
        file_manager = FileManager()
        filename, file_path = await file_manager.save_uploaded_file(file)
        
        # Get PDF info
        marker_service = MarkerService()
        pdf_info = await marker_service.get_pdf_info(file_path)
        
        # Generate preview images
        preview_images = await marker_service.generate_pdf_preview(file_path)
        
        # Generate unique ID for PDF document
        pdf_id = await redis.generate_id("pdf")
        
        # Create PDF document data
        pdf_data = {
            "id": pdf_id,
            "filename": filename,
            "original_filename": file.filename,
            "file_path": file_path,
            "file_size": len(content),
            "mime_type": file.content_type or "application/pdf",
            "total_pages": pdf_info["page_count"],
            "pdf_metadata": pdf_info["metadata"],
            "is_processed": False,
            "last_accessed_at": datetime.utcnow().isoformat()
        }
        
        # Save to Redis
        await redis.save_pdf_document(pdf_id, pdf_data)
        
        # Trigger storage cleanup if needed
        storage_manager = StorageManager(redis)
        cleanup_stats = await storage_manager.trigger_cleanup_if_needed()
        if cleanup_stats:
            logger.info(f"Storage cleanup triggered after upload: {cleanup_stats}")
        
        return PDFUploadResponse(
            id=pdf_id,
            filename=filename,
            original_filename=file.filename,
            file_size=len(content),
            total_pages=pdf_info["page_count"],
            preview_images=preview_images,
            metadata=pdf_info["metadata"] or {},
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error uploading PDF: {e}")
        raise HTTPException(status_code=500, detail="Error uploading PDF")

@router.get("/list")
async def list_pdfs(redis: RedisClient = Depends(get_redis)):
    """List all uploaded PDFs"""
    # Note: This is a simplified implementation
    # In a production system, you might want to maintain a separate index
    # or use Redis SCAN to find all PDF documents
    return {"message": "PDF listing not implemented yet - use individual PDF access"}

@router.get("/{pdf_id}")
async def get_pdf(pdf_id: str, redis: RedisClient = Depends(get_redis)):
    """Get PDF document details"""
    try:
        pdf_data = await redis.get_pdf_document(pdf_id)
        if not pdf_data:
            raise HTTPException(status_code=404, detail="PDF document not found")
        
        # Update access time
        await redis.update_pdf_access_time(pdf_id)
        
        return pdf_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting PDF: {e}")
        raise HTTPException(status_code=500, detail="Error getting PDF document")

@router.get("/{pdf_id}/preview")
async def get_pdf_preview(
    pdf_id: str,
    redis: RedisClient = Depends(get_redis)
):
    """Get PDF preview images"""
    try:
        pdf_data = await redis.get_pdf_document(pdf_id)
        if not pdf_data:
            raise HTTPException(status_code=404, detail="PDF not found")
        
        # Generate preview images
        marker_service = MarkerService()
        preview_images = await marker_service.generate_pdf_preview(pdf_data["file_path"])
        
        return {"preview_images": preview_images}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting PDF preview: {e}")
        raise HTTPException(status_code=500, detail="Error getting PDF preview")

@router.get("/storage/info")
async def get_storage_info(redis: RedisClient = Depends(get_redis)):
    """Get storage information and statistics"""
    try:
        storage_manager = StorageManager(redis)
        storage_info = await storage_manager.get_storage_info()
        return storage_info
    except Exception as e:
        logger.error(f"Error getting storage info: {e}")
        raise HTTPException(status_code=500, detail="Error getting storage information")

@router.post("/storage/cleanup")
async def trigger_storage_cleanup(redis: RedisClient = Depends(get_redis)):
    """Manually trigger storage cleanup"""
    try:
        storage_manager = StorageManager(redis)
        cleanup_stats = await storage_manager.check_and_cleanup_storage()
        return {
            "message": "Storage cleanup completed",
            "stats": cleanup_stats
        }
    except Exception as e:
        logger.error(f"Error during manual storage cleanup: {e}")
        raise HTTPException(status_code=500, detail="Error during storage cleanup") 