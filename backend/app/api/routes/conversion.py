"""
Conversion routes
"""

import os
import logging
import zipfile
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.pdf_document import PDFDocument
from app.models.conversion_job import ConversionJob, ConversionStatus, OutputFormat
from app.schemas.conversion import (
    ConversionJobCreate, 
    ConversionJobResponse, 
    ConversionJobListResponse,
    ConversionResult
)
from app.services.marker_service import MarkerService
from app.services.file_manager import FileManager

router = APIRouter()
logger = logging.getLogger(__name__)

async def process_conversion_job(job_id: int):
    """Background task to process conversion job"""
    from app.core.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        try:
            # Get job
            result = await db.execute(select(ConversionJob).where(ConversionJob.id == job_id))
            job = result.scalar_one_or_none()
            
            if not job:
                logger.error(f"Job {job_id} not found")
                return
            
            # Get PDF document
            result = await db.execute(select(PDFDocument).where(PDFDocument.id == job.pdf_document_id))
            pdf_doc = result.scalar_one_or_none()
            
            if not pdf_doc:
                job.status = ConversionStatus.FAILED
                job.error_message = "PDF document not found"
                await db.commit()
                return
            
            # Update job status
            job.status = ConversionStatus.PROCESSING
            job.progress = 10
            await db.commit()
            
            # Process conversion
            marker_service = MarkerService()
            result = await marker_service.convert_pdf(job, pdf_doc.file_path)
            
            if result["success"]:
                job.status = ConversionStatus.COMPLETED
                job.progress = 100
                job.output_file_path = result["output_path"]
                job.output_metadata = result["metadata"]
            else:
                job.status = ConversionStatus.FAILED
                job.error_message = result.get("error", "Unknown error")
            
            await db.commit()
            
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")
            # Update job status to failed
            try:
                result = await db.execute(select(ConversionJob).where(ConversionJob.id == job_id))
                job = result.scalar_one_or_none()
                if job:
                    job.status = ConversionStatus.FAILED
                    job.error_message = str(e)
                    await db.commit()
            except Exception as commit_error:
                logger.error(f"Error updating job status: {commit_error}")

@router.post("/jobs", response_model=ConversionJobResponse)
async def create_conversion_job(
    job_data: ConversionJobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create a new conversion job"""
    try:
        # Verify PDF exists
        result = await db.execute(select(PDFDocument).where(PDFDocument.id == job_data.pdf_document_id))
        pdf_doc = result.scalar_one_or_none()
        
        if not pdf_doc:
            raise HTTPException(status_code=404, detail="PDF document not found")
        
        # Get user settings for defaults and API key fallback
        from app.models.user_settings import UserSettings
        settings_result = await db.execute(select(UserSettings).limit(1))
        user_settings = settings_result.scalar_one_or_none()
        
        # Apply user defaults only when values are not explicitly provided (None)
        use_llm = job_data.use_llm
        llm_service = job_data.llm_service
        force_ocr = job_data.force_ocr
        format_lines = job_data.format_lines
        output_format = job_data.output_format
        strip_existing_ocr = job_data.strip_existing_ocr
        redo_inline_math = job_data.redo_inline_math
        disable_image_extraction = job_data.disable_image_extraction
        paginate_output = job_data.paginate_output
        
        # Apply user defaults if values are None (not provided) and user settings exist
        if user_settings:
            if use_llm is None:
                use_llm = user_settings.default_use_llm
                if use_llm and user_settings.default_llm_service:
                    llm_service = user_settings.default_llm_service
            
            if force_ocr is None:
                force_ocr = user_settings.default_force_ocr
                
            if format_lines is None:
                format_lines = user_settings.default_format_lines
                
            if output_format is None:
                output_format = user_settings.default_output_format
        
        # Apply system defaults for any remaining None values
        if use_llm is None:
            use_llm = False
        if force_ocr is None:
            force_ocr = False
        if format_lines is None:
            format_lines = False
        if strip_existing_ocr is None:
            strip_existing_ocr = False
        if redo_inline_math is None:
            redo_inline_math = False
        if disable_image_extraction is None:
            disable_image_extraction = False
        if paginate_output is None:
            paginate_output = False
        if output_format is None:
            output_format = OutputFormat.MARKDOWN
        
        # Convert string to OutputFormat enum if needed
        if isinstance(output_format, str):
            output_format = OutputFormat(output_format)
        
        # Validate API keys if LLM is enabled
        if use_llm and llm_service:
            # Check if API key is available (either from job or settings)
            api_key_available = False
            service_name = llm_service.lower()
            
            if "gemini" in service_name:
                api_key_available = bool(job_data.gemini_api_key or (user_settings and user_settings.gemini_api_key))
            elif "openai" in service_name:
                api_key_available = bool(job_data.openai_api_key or (user_settings and user_settings.openai_api_key))
            elif "claude" in service_name:
                api_key_available = bool(job_data.claude_api_key or (user_settings and user_settings.claude_api_key))
            elif "ollama" in service_name or "vertex" in service_name:
                # These services don't require API keys
                api_key_available = True
            
            if not api_key_available:
                service_display_name = llm_service.split('.')[-1] if '.' in llm_service else llm_service
                raise HTTPException(
                    status_code=400, 
                    detail=f"API key required for {service_display_name}. Please provide an API key in the conversion form or configure it in settings."
                )
        
        # Create job with applied defaults
        job = ConversionJob(
            pdf_document_id=job_data.pdf_document_id,
            output_format=output_format,
            selected_pages=job_data.selected_pages,
            use_llm=use_llm,
            force_ocr=force_ocr,
            strip_existing_ocr=strip_existing_ocr,
            format_lines=format_lines,
            redo_inline_math=redo_inline_math,
            disable_image_extraction=disable_image_extraction,
            paginate_output=paginate_output,
            llm_service=llm_service,
            llm_model=job_data.llm_model,
            gemini_api_key=job_data.gemini_api_key,
            openai_api_key=job_data.openai_api_key,
            claude_api_key=job_data.claude_api_key
        )
        
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        # Start background processing
        background_tasks.add_task(process_conversion_job, job.id)
        
        return ConversionJobResponse(
            id=job.id,
            pdf_document_id=job.pdf_document_id,
            output_format=job.output_format,
            selected_pages=job.selected_pages,
            use_llm=job.use_llm,
            force_ocr=job.force_ocr,
            strip_existing_ocr=job.strip_existing_ocr,
            format_lines=job.format_lines,
            redo_inline_math=job.redo_inline_math,
            disable_image_extraction=job.disable_image_extraction,
            paginate_output=job.paginate_output,
            llm_service=job.llm_service,
            llm_model=job.llm_model,
            status=job.status,
            progress=job.progress,
            output_file_path=job.output_file_path,
            output_metadata=job.output_metadata,
            error_message=job.error_message,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating conversion job: {e}")
        raise HTTPException(status_code=500, detail="Error creating conversion job")

@router.get("/jobs", response_model=ConversionJobListResponse)
async def list_conversion_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    status: ConversionStatus = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List conversion jobs"""
    try:
        # Build query
        query = select(ConversionJob)
        if status:
            query = query.where(ConversionJob.status == status)
        
        # Get total count
        count_query = select(func.count(ConversionJob.id))
        if status:
            count_query = count_query.where(ConversionJob.status == status)
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Get jobs with pagination
        offset = (page - 1) * per_page
        result = await db.execute(
            query.order_by(ConversionJob.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        jobs = result.scalars().all()
        
        job_list = [
            ConversionJobResponse(
                id=job.id,
                pdf_document_id=job.pdf_document_id,
                output_format=job.output_format,
                selected_pages=job.selected_pages,
                use_llm=job.use_llm,
                force_ocr=job.force_ocr,
                strip_existing_ocr=job.strip_existing_ocr,
                format_lines=job.format_lines,
                redo_inline_math=job.redo_inline_math,
                disable_image_extraction=job.disable_image_extraction,
                paginate_output=job.paginate_output,
                llm_service=job.llm_service,
                llm_model=job.llm_model,
                status=job.status,
                progress=job.progress,
                output_file_path=job.output_file_path,
                output_metadata=job.output_metadata,
                error_message=job.error_message,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at
            )
            for job in jobs
        ]
        
        return ConversionJobListResponse(
            jobs=job_list,
            total=total,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        logger.error(f"Error listing conversion jobs: {e}")
        raise HTTPException(status_code=500, detail="Error listing conversion jobs")

@router.get("/jobs/{job_id}", response_model=ConversionJobResponse)
async def get_conversion_job(
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get conversion job details"""
    try:
        result = await db.execute(select(ConversionJob).where(ConversionJob.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Conversion job not found")
        
        return ConversionJobResponse(
            id=job.id,
            pdf_document_id=job.pdf_document_id,
            output_format=job.output_format,
            selected_pages=job.selected_pages,
            use_llm=job.use_llm,
            force_ocr=job.force_ocr,
            strip_existing_ocr=job.strip_existing_ocr,
            format_lines=job.format_lines,
            redo_inline_math=job.redo_inline_math,
            disable_image_extraction=job.disable_image_extraction,
            paginate_output=job.paginate_output,
            llm_service=job.llm_service,
            llm_model=job.llm_model,
            status=job.status,
            progress=job.progress,
            output_file_path=job.output_file_path,
            output_metadata=job.output_metadata,
            error_message=job.error_message,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversion job: {e}")
        raise HTTPException(status_code=500, detail="Error getting conversion job")

@router.get("/jobs/{job_id}/result", response_model=ConversionResult)
async def get_conversion_result(
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get conversion result with content"""
    try:
        result = await db.execute(select(ConversionJob).where(ConversionJob.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Conversion job not found")
        
        if job.status != ConversionStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Job not completed")
        
        # Read output content
        content = None
        if job.output_file_path and os.path.exists(job.output_file_path):
            with open(job.output_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        # Get images if any
        images = []
        file_manager = FileManager()
        job_dir = file_manager.get_job_dir(job.id)
        if os.path.exists(job_dir):
            for item in os.listdir(job_dir):
                item_path = os.path.join(job_dir, item)
                # Only include image files, not the output file
                if os.path.isfile(item_path) and item.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg')):
                    images.append(f"/output/job_{job.id}/{item}")
        
        job_response = ConversionJobResponse(
            id=job.id,
            pdf_document_id=job.pdf_document_id,
            output_format=job.output_format,
            selected_pages=job.selected_pages,
            use_llm=job.use_llm,
            force_ocr=job.force_ocr,
            strip_existing_ocr=job.strip_existing_ocr,
            format_lines=job.format_lines,
            redo_inline_math=job.redo_inline_math,
            disable_image_extraction=job.disable_image_extraction,
            paginate_output=job.paginate_output,
            llm_service=job.llm_service,
            llm_model=job.llm_model,
            status=job.status,
            progress=job.progress,
            output_file_path=job.output_file_path,
            output_metadata=job.output_metadata,
            error_message=job.error_message,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at
        )
        
        return ConversionResult(
            job=job_response,
            content=content,
            images=images
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversion result: {e}")
        raise HTTPException(status_code=500, detail="Error getting conversion result")

@router.get("/jobs/{job_id}/download")
async def download_conversion_result(
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Download conversion result as zip file containing all output files"""
    try:
        result = await db.execute(select(ConversionJob).where(ConversionJob.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Conversion job not found")
        
        if job.status != ConversionStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Job not completed")
        
        # Get job directory
        file_manager = FileManager()
        job_dir = file_manager.get_job_dir(job.id)
        
        if not os.path.exists(job_dir):
            raise HTTPException(status_code=404, detail="Job output directory not found")
        
        # Create temporary zip file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
            with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add all files from job directory to zip
                job_path = Path(job_dir)
                for file_path in job_path.rglob('*'):
                    if file_path.is_file():
                        # Use relative path within the zip
                        arcname = file_path.relative_to(job_path)
                        zipf.write(file_path, arcname)
            
            # Return zip file with proper background task for cleanup
            zip_filename = f"conversion_job_{job.id}.zip"
            return FileResponse(
                temp_zip.name,
                filename=zip_filename,
                media_type="application/zip",
                background=BackgroundTask(os.unlink, temp_zip.name)
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating zip download: {e}")
        raise HTTPException(status_code=500, detail="Error creating download package")

@router.delete("/jobs/{job_id}")
async def delete_conversion_job(
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversion job"""
    try:
        result = await db.execute(select(ConversionJob).where(ConversionJob.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Conversion job not found")
        
        # Delete output files and job directory
        file_manager = FileManager()
        job_dir = file_manager.get_job_dir(job.id)
        await file_manager.delete_directory(job_dir)
        
        # Delete database record
        await db.delete(job)
        await db.commit()
        
        return {"message": "Conversion job deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversion job: {e}")
        raise HTTPException(status_code=500, detail="Error deleting conversion job")

@router.get("/llm-services/requirements")
async def get_llm_service_requirements():
    """Get API key requirements for each LLM service"""
    return {
        "marker.services.gemini.GoogleGeminiService": {
            "display_name": "Google Gemini",
            "required_fields": ["gemini_api_key"],
            "field_labels": {"gemini_api_key": "Gemini API Key"}
        },
        "marker.services.openai.OpenAIService": {
            "display_name": "OpenAI",
            "required_fields": ["openai_api_key"],
            "field_labels": {"openai_api_key": "OpenAI API Key"}
        },
        "marker.services.claude.ClaudeService": {
            "display_name": "Anthropic Claude",
            "required_fields": ["claude_api_key"],
            "field_labels": {"claude_api_key": "Claude API Key"}
        },
        "marker.services.ollama.OllamaService": {
            "display_name": "Ollama (Local)",
            "required_fields": [],
            "field_labels": {}
        },
        "marker.services.vertex.GoogleVertexService": {
            "display_name": "Google Vertex AI",
            "required_fields": [],
            "field_labels": {}
        }
    }

@router.get("/defaults")
async def get_conversion_defaults(db: AsyncSession = Depends(get_db)):
    """Get default conversion settings from user settings"""
    try:
        from app.models.user_settings import UserSettings
        
        # Get user settings
        result = await db.execute(select(UserSettings).limit(1))
        user_settings = result.scalar_one_or_none()
        
        if not user_settings:
            # Return system defaults if no user settings exist
            return {
                "output_format": "markdown",
                "use_llm": False,
                "force_ocr": False,
                "format_lines": False,
                "llm_service": None,
                "disable_image_extraction": False,
                "strip_existing_ocr": False,
                "redo_inline_math": False,
                "paginate_output": False
            }
        
        return {
            "output_format": user_settings.default_output_format,
            "use_llm": user_settings.default_use_llm,
            "force_ocr": user_settings.default_force_ocr,
            "format_lines": user_settings.default_format_lines,
            "llm_service": user_settings.default_llm_service,
            "disable_image_extraction": False,  # Not in settings yet
            "strip_existing_ocr": False,  # Not in settings yet
            "redo_inline_math": False,  # Not in settings yet
            "paginate_output": False  # Not in settings yet
        }
        
    except Exception as e:
        logger.error(f"Error getting conversion defaults: {e}")
        raise HTTPException(status_code=500, detail="Error getting conversion defaults") 