from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
import os
import logging

from app.core.database import get_db
from app.models.pdf_document import PDFDocument
from app.schemas.pdf import PDFUploadResponse
from app.services.file_manager import FileManager
from app.services.marker_service import MarkerService
from app.core.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload", response_model=PDFUploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
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
        
        # Create database record
        pdf_doc = PDFDocument(
            filename=filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=len(content),
            mime_type=file.content_type or "application/pdf",
            total_pages=pdf_info["page_count"],
            pdf_metadata=pdf_info["metadata"]
        )
        
        db.add(pdf_doc)
        await db.commit()
        await db.refresh(pdf_doc)
        
        return PDFUploadResponse(
            id=pdf_doc.id,
            filename=pdf_doc.filename,
            original_filename=pdf_doc.original_filename,
            file_size=pdf_doc.file_size,
            total_pages=pdf_doc.total_pages,
            preview_images=preview_images,
            metadata=pdf_doc.pdf_metadata or {},
            created_at=pdf_doc.created_at
        )
        
    except Exception as e:
        logger.error(f"Error uploading PDF: {e}")
        raise HTTPException(status_code=500, detail="Error uploading PDF")

@router.get("/{pdf_id}/preview")
async def get_pdf_preview(
    pdf_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get PDF preview images"""
    try:
        result = await db.execute(select(PDFDocument).where(PDFDocument.id == pdf_id))
        pdf = result.scalar_one_or_none()
        
        if not pdf:
            raise HTTPException(status_code=404, detail="PDF not found")
        
        # Generate preview images
        marker_service = MarkerService()
        preview_images = await marker_service.generate_pdf_preview(pdf.file_path)
        
        return {"preview_images": preview_images}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting PDF preview: {e}")
        raise HTTPException(status_code=500, detail="Error getting PDF preview") 