from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
import os
import logging

from app.core.database import get_db
from app.models.pdf_document import PDFDocument
from app.schemas.pdf import PDFUploadResponse, PDFInfo, PDFListResponse
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

@router.get("/list", response_model=PDFListResponse)
async def list_pdfs(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List uploaded PDFs"""
    try:
        # Get total count
        count_result = await db.execute(select(func.count(PDFDocument.id)))
        total = count_result.scalar()
        
        # Get PDFs with pagination
        offset = (page - 1) * per_page
        result = await db.execute(
            select(PDFDocument)
            .order_by(PDFDocument.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        pdfs = result.scalars().all()
        
        pdf_list = [
            PDFInfo(
                id=pdf.id,
                filename=pdf.filename,
                original_filename=pdf.original_filename,
                file_size=pdf.file_size,
                total_pages=pdf.total_pages,
                metadata=pdf.pdf_metadata or {},
                is_processed=pdf.is_processed,
                created_at=pdf.created_at
            )
            for pdf in pdfs
        ]
        
        return PDFListResponse(
            pdfs=pdf_list,
            total=total,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        logger.error(f"Error listing PDFs: {e}")
        raise HTTPException(status_code=500, detail="Error listing PDFs")

@router.get("/{pdf_id}", response_model=PDFInfo)
async def get_pdf(
    pdf_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get PDF information"""
    try:
        result = await db.execute(select(PDFDocument).where(PDFDocument.id == pdf_id))
        pdf = result.scalar_one_or_none()
        
        if not pdf:
            raise HTTPException(status_code=404, detail="PDF not found")
        
        return PDFInfo(
            id=pdf.id,
            filename=pdf.filename,
            original_filename=pdf.original_filename,
            file_size=pdf.file_size,
            total_pages=pdf.total_pages,
            metadata=pdf.pdf_metadata or {},
            is_processed=pdf.is_processed,
            created_at=pdf.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting PDF: {e}")
        raise HTTPException(status_code=500, detail="Error getting PDF")

@router.delete("/{pdf_id}")
async def delete_pdf(
    pdf_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a PDF"""
    try:
        result = await db.execute(select(PDFDocument).where(PDFDocument.id == pdf_id))
        pdf = result.scalar_one_or_none()
        
        if not pdf:
            raise HTTPException(status_code=404, detail="PDF not found")
        
        # First, delete all related conversion jobs
        from app.models.conversion_job import ConversionJob
        from sqlalchemy import delete
        
        # Delete conversion jobs first (due to foreign key constraint)
        conversion_jobs_result = await db.execute(
            select(ConversionJob).where(ConversionJob.pdf_document_id == pdf_id)
        )
        conversion_jobs = conversion_jobs_result.scalars().all()
        
        logger.info(f"Found {len(conversion_jobs)} conversion jobs to delete for PDF {pdf_id}")
        
        # Delete output files for each conversion job
        file_manager = FileManager()
        for job in conversion_jobs:
            # Delete entire job directory (contains output file and images)
            job_dir = file_manager.get_job_dir(job.id)
            await file_manager.delete_directory(job_dir)
            logger.info(f"Deleted job directory: {job_dir}")
        
        # Delete conversion jobs from database
        delete_jobs_stmt = delete(ConversionJob).where(ConversionJob.pdf_document_id == pdf_id)
        result = await db.execute(delete_jobs_stmt)
        logger.info(f"Deleted {result.rowcount} conversion jobs from database")
        
        # Delete the PDF file
        file_deleted = await file_manager.delete_file(pdf.file_path)
        logger.info(f"File deletion result: {file_deleted} for path: {pdf.file_path}")
        
        # Delete PDF database record
        delete_pdf_stmt = delete(PDFDocument).where(PDFDocument.id == pdf_id)
        result = await db.execute(delete_pdf_stmt)
        logger.info(f"Deleted {result.rowcount} PDF records from database")
        
        await db.commit()
        
        logger.info(f"Successfully deleted PDF with ID: {pdf_id} and {len(conversion_jobs)} related conversion jobs")
        return {"message": "PDF deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting PDF: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting PDF: {str(e)}")

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