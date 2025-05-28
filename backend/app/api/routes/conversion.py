"""
Conversion routes
"""

import os
import logging
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.core.redis_client import get_redis, RedisClient
from app.core.config import get_settings
from app.schemas.models import ConversionStatus, OutputFormat, ConversionJob
from app.schemas.conversion import (
    ConversionJobCreate, 
    ConversionJobResponse, 
    ConversionResult
)
from app.services.marker_service import MarkerService
from app.services.file_manager import FileManager

router = APIRouter()
logger = logging.getLogger(__name__)

async def process_conversion_job(job_id: str):
    """Background task to process conversion job"""
    from app.core.redis_client import redis_client
    
    try:
        # Get job data
        job_data = await redis_client.get_conversion_job(job_id)
        if not job_data:
            logger.error(f"Job {job_id} not found")
            return
        
        # Update job status to processing
        job_data["status"] = ConversionStatus.PROCESSING.value
        job_data["started_at"] = datetime.utcnow().isoformat()
        await redis_client.save_conversion_job(job_id, job_data)
        
        # Get PDF data
        pdf_data = await redis_client.get_pdf_document(job_data["pdf_document_id"])
        if not pdf_data:
            job_data["status"] = ConversionStatus.FAILED.value
            job_data["error_message"] = "PDF document not found"
            job_data["completed_at"] = datetime.utcnow().isoformat()
            await redis_client.save_conversion_job(job_id, job_data)
            return
        
        # Create job model with all options
        job_model = ConversionJob(
            id=job_data["id"],
            pdf_document_id=job_data["pdf_document_id"],
            output_format=OutputFormat(job_data["output_format"]),
            selected_pages=job_data.get("selected_pages"),
            use_llm=job_data["use_llm"],
            force_ocr=job_data["force_ocr"],
            strip_existing_ocr=job_data["strip_existing_ocr"],
            format_lines=job_data["format_lines"],
            redo_inline_math=job_data["redo_inline_math"],
            disable_image_extraction=job_data["disable_image_extraction"],
            paginate_output=job_data["paginate_output"],
            
            # Performance & Quality Options
            lowres_image_dpi=job_data.get("lowres_image_dpi"),
            highres_image_dpi=job_data.get("highres_image_dpi"),
            layout_batch_size=job_data.get("layout_batch_size"),
            detection_batch_size=job_data.get("detection_batch_size"),
            recognition_batch_size=job_data.get("recognition_batch_size"),
            
            # OCR & Text Processing Options
            languages=job_data.get("languages"),
            ocr_task_name=job_data.get("ocr_task_name"),
            disable_ocr_math=job_data.get("disable_ocr_math"),
            keep_chars=job_data.get("keep_chars"),
            
            # Layout & Structure Options
            force_layout_block=job_data.get("force_layout_block"),
            column_gap_ratio=job_data.get("column_gap_ratio"),
            gap_threshold=job_data.get("gap_threshold"),
            list_gap_threshold=job_data.get("list_gap_threshold"),
            
            # Table Processing Options
            detect_boxes=job_data.get("detect_boxes"),
            table_rec_batch_size=job_data.get("table_rec_batch_size"),
            max_table_rows=job_data.get("max_table_rows"),
            max_rows_per_batch=job_data.get("max_rows_per_batch"),
            
            # Section & Header Processing
            level_count=job_data.get("level_count"),
            merge_threshold=job_data.get("merge_threshold"),
            default_level=job_data.get("default_level"),
            
            # Advanced Processing Options
            min_equation_height=job_data.get("min_equation_height"),
            equation_batch_size=job_data.get("equation_batch_size"),
            inlinemath_min_ratio=job_data.get("inlinemath_min_ratio"),
            
            # Output Control Options
            page_separator=job_data.get("page_separator"),
            extract_images=job_data.get("extract_images"),
            
            # Debug Options
            debug=job_data.get("debug"),
            debug_layout_images=job_data.get("debug_layout_images"),
            debug_pdf_images=job_data.get("debug_pdf_images"),
            debug_json=job_data.get("debug_json"),
            debug_data_folder=job_data.get("debug_data_folder"),
            
            llm_service=job_data.get("llm_service"),
            llm_model=job_data.get("llm_model"),
            
            # LLM Processing Options
            max_concurrency=job_data.get("max_concurrency"),
            confidence_threshold=job_data.get("confidence_threshold"),
            
            # Service-specific LLM configuration
            ollama_base_url=job_data.get("ollama_base_url"),
            openai_base_url=job_data.get("openai_base_url"),
            claude_model_name=job_data.get("claude_model_name"),
            vertex_project_id=job_data.get("vertex_project_id"),
            
            # Service-specific model names
            openai_model=job_data.get("openai_model"),
            ollama_model=job_data.get("ollama_model"),
            gemini_model_name=job_data.get("gemini_model_name"),
            
            gemini_api_key=job_data.get("gemini_api_key"),
            openai_api_key=job_data.get("openai_api_key"),
            claude_api_key=job_data.get("claude_api_key"),
            
            status=ConversionStatus(job_data["status"]),
            progress=job_data["progress"],
            output_file_path=job_data.get("output_file_path"),
            output_metadata=job_data.get("output_metadata"),
            error_message=job_data.get("error_message"),
            created_at=datetime.fromisoformat(job_data["created_at"]),
            started_at=datetime.fromisoformat(job_data["started_at"]) if job_data.get("started_at") else None,
            completed_at=datetime.fromisoformat(job_data["completed_at"]) if job_data.get("completed_at") else None
        )
        
        # Process conversion
        marker_service = MarkerService()
        result = await marker_service.convert_pdf(job_model, pdf_data["file_path"])
        
        # Update job with results
        job_data["status"] = ConversionStatus.COMPLETED.value
        job_data["completed_at"] = datetime.utcnow().isoformat()
        job_data["progress"] = 100
        job_data["output_file_path"] = result.get("output_path")
        job_data["output_metadata"] = result.get("metadata")
        
        await redis_client.save_conversion_job(job_id, job_data)
        
    except Exception as e:
        logger.error(f"Error processing conversion job {job_id}: {e}")
        
        # Update job with error
        try:
            job_data = await redis_client.get_conversion_job(job_id)
            if job_data:
                job_data["status"] = ConversionStatus.FAILED.value
                job_data["error_message"] = str(e)
                job_data["completed_at"] = datetime.utcnow().isoformat()
                await redis_client.save_conversion_job(job_id, job_data)
        except Exception as update_error:
            logger.error(f"Error updating job status: {update_error}")

@router.post("/jobs", response_model=ConversionJobResponse)
async def create_conversion_job(
    job_data: ConversionJobCreate,
    background_tasks: BackgroundTasks,
    redis: RedisClient = Depends(get_redis)
):
    """Create a new conversion job"""
    try:
        # Verify PDF exists
        pdf_data = await redis.get_pdf_document(job_data.pdf_document_id)
        
        if not pdf_data:
            raise HTTPException(status_code=404, detail="PDF document not found")
        
        # Get user settings for defaults and API key fallback
        user_settings = await redis.get_user_settings()
        
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
                use_llm = user_settings.get("default_use_llm", False)
                if use_llm and user_settings.get("default_llm_service"):
                    llm_service = user_settings["default_llm_service"]
            
            if force_ocr is None:
                force_ocr = user_settings.get("default_force_ocr", False)
                
            if format_lines is None:
                format_lines = user_settings.get("default_format_lines", False)
                
            if output_format is None:
                output_format = user_settings.get("default_output_format", "markdown")
        
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
            output_format = "markdown"
        
        # Convert string to OutputFormat enum if needed
        if isinstance(output_format, str):
            output_format = OutputFormat(output_format)
        
        # Validate API keys if LLM is enabled
        if use_llm and llm_service:
            # Check if API key is available (from job, user settings, or environment)
            api_key_available = False
            service_name = llm_service.lower()
            settings = get_settings()
            
            if "gemini" in service_name:
                api_key_available = bool(
                    job_data.gemini_api_key or 
                    (user_settings and user_settings.get("gemini_api_key")) or
                    settings.gemini_api_key
                )
            elif "openai" in service_name:
                api_key_available = bool(
                    job_data.openai_api_key or 
                    (user_settings and user_settings.get("openai_api_key")) or
                    settings.openai_api_key
                )
            elif "claude" in service_name:
                api_key_available = bool(
                    job_data.claude_api_key or 
                    (user_settings and user_settings.get("claude_api_key")) or
                    settings.claude_api_key
                )
            elif "ollama" in service_name or "vertex" in service_name:
                # These services don't require API keys
                api_key_available = True
            
            if not api_key_available:
                service_display_name = llm_service.split('.')[-1] if '.' in llm_service else llm_service
                raise HTTPException(
                    status_code=400, 
                    detail=f"API key required for {service_display_name}. Please provide an API key in the conversion form or configure it in settings."
                )
        
        # Generate unique job ID
        job_id = await redis.generate_id("job")
        
        # Create job data with all options
        job_dict = {
            "id": job_id,
            "pdf_document_id": job_data.pdf_document_id,
            "output_format": output_format.value if isinstance(output_format, OutputFormat) else output_format,
            "selected_pages": job_data.selected_pages,
            "use_llm": use_llm,
            "force_ocr": force_ocr,
            "strip_existing_ocr": strip_existing_ocr,
            "format_lines": format_lines,
            "redo_inline_math": redo_inline_math,
            "disable_image_extraction": disable_image_extraction,
            "paginate_output": paginate_output,
            
            # Performance & Quality Options
            "lowres_image_dpi": job_data.lowres_image_dpi,
            "highres_image_dpi": job_data.highres_image_dpi,
            "layout_batch_size": job_data.layout_batch_size,
            "detection_batch_size": job_data.detection_batch_size,
            "recognition_batch_size": job_data.recognition_batch_size,
            
            # OCR & Text Processing Options
            "languages": job_data.languages,
            "ocr_task_name": job_data.ocr_task_name,
            "disable_ocr_math": job_data.disable_ocr_math,
            "keep_chars": job_data.keep_chars,
            
            # Layout & Structure Options
            "force_layout_block": job_data.force_layout_block,
            "column_gap_ratio": job_data.column_gap_ratio,
            "gap_threshold": job_data.gap_threshold,
            "list_gap_threshold": job_data.list_gap_threshold,
            
            # Table Processing Options
            "detect_boxes": job_data.detect_boxes,
            "table_rec_batch_size": job_data.table_rec_batch_size,
            "max_table_rows": job_data.max_table_rows,
            "max_rows_per_batch": job_data.max_rows_per_batch,
            
            # Section & Header Processing
            "level_count": job_data.level_count,
            "merge_threshold": job_data.merge_threshold,
            "default_level": job_data.default_level,
            
            # Advanced Processing Options
            "min_equation_height": job_data.min_equation_height,
            "equation_batch_size": job_data.equation_batch_size,
            "inlinemath_min_ratio": job_data.inlinemath_min_ratio,
            
            # Output Control Options
            "page_separator": job_data.page_separator,
            "extract_images": job_data.extract_images,
            
            # Debug Options
            "debug": job_data.debug,
            "debug_layout_images": job_data.debug_layout_images,
            "debug_pdf_images": job_data.debug_pdf_images,
            "debug_json": job_data.debug_json,
            "debug_data_folder": job_data.debug_data_folder,
            
            "llm_service": llm_service,
            "llm_model": job_data.llm_model,
            
            # LLM Processing Options
            "max_concurrency": job_data.max_concurrency,
            "confidence_threshold": job_data.confidence_threshold,
            
            # Service-specific LLM configuration
            "ollama_base_url": job_data.ollama_base_url,
            "openai_base_url": job_data.openai_base_url,
            "claude_model_name": job_data.claude_model_name,
            "vertex_project_id": job_data.vertex_project_id,
            
            # Service-specific model names
            "openai_model": job_data.openai_model,
            "ollama_model": job_data.ollama_model,
            "gemini_model_name": job_data.gemini_model_name,
            
            "gemini_api_key": job_data.gemini_api_key,
            "openai_api_key": job_data.openai_api_key,
            "claude_api_key": job_data.claude_api_key,
            
            "status": ConversionStatus.PENDING.value,
            "progress": 0,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Save job to Redis
        await redis.save_conversion_job(job_id, job_dict)
        
        # Start background processing
        background_tasks.add_task(process_conversion_job, job_id)
        
        return ConversionJobResponse(
            id=job_id,
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
            
            # Performance & Quality Options
            lowres_image_dpi=job_data.lowres_image_dpi,
            highres_image_dpi=job_data.highres_image_dpi,
            layout_batch_size=job_data.layout_batch_size,
            detection_batch_size=job_data.detection_batch_size,
            recognition_batch_size=job_data.recognition_batch_size,
            
            # OCR & Text Processing Options
            languages=job_data.languages,
            ocr_task_name=job_data.ocr_task_name,
            disable_ocr_math=job_data.disable_ocr_math,
            keep_chars=job_data.keep_chars,
            
            # Layout & Structure Options
            force_layout_block=job_data.force_layout_block,
            column_gap_ratio=job_data.column_gap_ratio,
            gap_threshold=job_data.gap_threshold,
            list_gap_threshold=job_data.list_gap_threshold,
            
            # Table Processing Options
            detect_boxes=job_data.detect_boxes,
            table_rec_batch_size=job_data.table_rec_batch_size,
            max_table_rows=job_data.max_table_rows,
            max_rows_per_batch=job_data.max_rows_per_batch,
            
            # Section & Header Processing
            level_count=job_data.level_count,
            merge_threshold=job_data.merge_threshold,
            default_level=job_data.default_level,
            
            # Advanced Processing Options
            min_equation_height=job_data.min_equation_height,
            equation_batch_size=job_data.equation_batch_size,
            inlinemath_min_ratio=job_data.inlinemath_min_ratio,
            
            # Output Control Options
            page_separator=job_data.page_separator,
            extract_images=job_data.extract_images,
            
            # Debug Options
            debug=job_data.debug,
            debug_layout_images=job_data.debug_layout_images,
            debug_pdf_images=job_data.debug_pdf_images,
            debug_json=job_data.debug_json,
            debug_data_folder=job_data.debug_data_folder,
            
            llm_service=llm_service,
            llm_model=job_data.llm_model,
            
            # LLM Processing Options
            max_concurrency=job_data.max_concurrency,
            confidence_threshold=job_data.confidence_threshold,
            
            # Service-specific LLM configuration
            ollama_base_url=job_data.ollama_base_url,
            openai_base_url=job_data.openai_base_url,
            claude_model_name=job_data.claude_model_name,
            vertex_project_id=job_data.vertex_project_id,
            
            # Service-specific model names
            openai_model=job_data.openai_model,
            ollama_model=job_data.ollama_model,
            gemini_model_name=job_data.gemini_model_name,
            
            status=ConversionStatus.PENDING,
            progress=0,
            output_file_path=None,
            output_metadata=None,
            error_message=None,
            created_at=datetime.utcnow(),
            started_at=None,
            completed_at=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating conversion job: {e}")
        raise HTTPException(status_code=500, detail="Error creating conversion job")

@router.get("/jobs/{job_id}", response_model=ConversionJobResponse)
async def get_conversion_job(
    job_id: str,
    redis: RedisClient = Depends(get_redis)
):
    """Get conversion job details"""
    try:
        job_data = await redis.get_conversion_job(job_id)
        
        if not job_data:
            raise HTTPException(status_code=404, detail="Conversion job not found")
        
        return ConversionJobResponse(
            id=job_data["id"],
            pdf_document_id=job_data["pdf_document_id"],
            output_format=OutputFormat(job_data["output_format"]),
            selected_pages=job_data.get("selected_pages"),
            use_llm=job_data["use_llm"],
            force_ocr=job_data["force_ocr"],
            strip_existing_ocr=job_data["strip_existing_ocr"],
            format_lines=job_data["format_lines"],
            redo_inline_math=job_data["redo_inline_math"],
            disable_image_extraction=job_data["disable_image_extraction"],
            paginate_output=job_data["paginate_output"],
            
            # Performance & Quality Options
            lowres_image_dpi=job_data.get("lowres_image_dpi"),
            highres_image_dpi=job_data.get("highres_image_dpi"),
            layout_batch_size=job_data.get("layout_batch_size"),
            detection_batch_size=job_data.get("detection_batch_size"),
            recognition_batch_size=job_data.get("recognition_batch_size"),
            
            # OCR & Text Processing Options
            languages=job_data.get("languages"),
            ocr_task_name=job_data.get("ocr_task_name"),
            disable_ocr_math=job_data.get("disable_ocr_math"),
            keep_chars=job_data.get("keep_chars"),
            
            # Layout & Structure Options
            force_layout_block=job_data.get("force_layout_block"),
            column_gap_ratio=job_data.get("column_gap_ratio"),
            gap_threshold=job_data.get("gap_threshold"),
            list_gap_threshold=job_data.get("list_gap_threshold"),
            
            # Table Processing Options
            detect_boxes=job_data.get("detect_boxes"),
            table_rec_batch_size=job_data.get("table_rec_batch_size"),
            max_table_rows=job_data.get("max_table_rows"),
            max_rows_per_batch=job_data.get("max_rows_per_batch"),
            
            # Section & Header Processing
            level_count=job_data.get("level_count"),
            merge_threshold=job_data.get("merge_threshold"),
            default_level=job_data.get("default_level"),
            
            # Advanced Processing Options
            min_equation_height=job_data.get("min_equation_height"),
            equation_batch_size=job_data.get("equation_batch_size"),
            inlinemath_min_ratio=job_data.get("inlinemath_min_ratio"),
            
            # Output Control Options
            page_separator=job_data.get("page_separator"),
            extract_images=job_data.get("extract_images"),
            
            # Debug Options
            debug=job_data.get("debug"),
            debug_layout_images=job_data.get("debug_layout_images"),
            debug_pdf_images=job_data.get("debug_pdf_images"),
            debug_json=job_data.get("debug_json"),
            debug_data_folder=job_data.get("debug_data_folder"),
            
            llm_service=job_data.get("llm_service"),
            llm_model=job_data.get("llm_model"),
            
            # LLM Processing Options
            max_concurrency=job_data.get("max_concurrency"),
            confidence_threshold=job_data.get("confidence_threshold"),
            
            # Service-specific LLM configuration
            ollama_base_url=job_data.get("ollama_base_url"),
            openai_base_url=job_data.get("openai_base_url"),
            claude_model_name=job_data.get("claude_model_name"),
            vertex_project_id=job_data.get("vertex_project_id"),
            
            # Service-specific model names
            openai_model=job_data.get("openai_model"),
            ollama_model=job_data.get("ollama_model"),
            gemini_model_name=job_data.get("gemini_model_name"),
            
            status=ConversionStatus(job_data["status"]),
            progress=job_data["progress"],
            output_file_path=job_data.get("output_file_path"),
            output_metadata=job_data.get("output_metadata"),
            error_message=job_data.get("error_message"),
            created_at=datetime.fromisoformat(job_data["created_at"]),
            started_at=datetime.fromisoformat(job_data["started_at"]) if job_data.get("started_at") else None,
            completed_at=datetime.fromisoformat(job_data["completed_at"]) if job_data.get("completed_at") else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversion job: {e}")
        raise HTTPException(status_code=500, detail="Error getting conversion job")

@router.get("/jobs/{job_id}/result", response_model=ConversionResult)
async def get_conversion_result(
    job_id: str,
    redis: RedisClient = Depends(get_redis)
):
    """Get conversion result with content"""
    try:
        job_data = await redis.get_conversion_job(job_id)
        
        if not job_data:
            raise HTTPException(status_code=404, detail="Conversion job not found")
        
        if job_data["status"] != ConversionStatus.COMPLETED.value:
            raise HTTPException(status_code=400, detail="Job not completed")
        
        # Read content and images
        file_manager = FileManager()
        content = None
        images = []
        
        if job_data.get("output_file_path"):
            content = file_manager.read_conversion_output(job_id, job_data["output_file_path"])
            images = file_manager.get_conversion_images(job_id)
        
        job_response = ConversionJobResponse(
            id=job_data["id"],
            pdf_document_id=job_data["pdf_document_id"],
            output_format=OutputFormat(job_data["output_format"]),
            selected_pages=job_data.get("selected_pages"),
            use_llm=job_data["use_llm"],
            force_ocr=job_data["force_ocr"],
            strip_existing_ocr=job_data["strip_existing_ocr"],
            format_lines=job_data["format_lines"],
            redo_inline_math=job_data["redo_inline_math"],
            disable_image_extraction=job_data["disable_image_extraction"],
            paginate_output=job_data["paginate_output"],
            
            # Performance & Quality Options
            lowres_image_dpi=job_data.get("lowres_image_dpi"),
            highres_image_dpi=job_data.get("highres_image_dpi"),
            layout_batch_size=job_data.get("layout_batch_size"),
            detection_batch_size=job_data.get("detection_batch_size"),
            recognition_batch_size=job_data.get("recognition_batch_size"),
            
            # OCR & Text Processing Options
            languages=job_data.get("languages"),
            ocr_task_name=job_data.get("ocr_task_name"),
            disable_ocr_math=job_data.get("disable_ocr_math"),
            keep_chars=job_data.get("keep_chars"),
            
            # Layout & Structure Options
            force_layout_block=job_data.get("force_layout_block"),
            column_gap_ratio=job_data.get("column_gap_ratio"),
            gap_threshold=job_data.get("gap_threshold"),
            list_gap_threshold=job_data.get("list_gap_threshold"),
            
            # Table Processing Options
            detect_boxes=job_data.get("detect_boxes"),
            table_rec_batch_size=job_data.get("table_rec_batch_size"),
            max_table_rows=job_data.get("max_table_rows"),
            max_rows_per_batch=job_data.get("max_rows_per_batch"),
            
            # Section & Header Processing
            level_count=job_data.get("level_count"),
            merge_threshold=job_data.get("merge_threshold"),
            default_level=job_data.get("default_level"),
            
            # Advanced Processing Options
            min_equation_height=job_data.get("min_equation_height"),
            equation_batch_size=job_data.get("equation_batch_size"),
            inlinemath_min_ratio=job_data.get("inlinemath_min_ratio"),
            
            # Output Control Options
            page_separator=job_data.get("page_separator"),
            extract_images=job_data.get("extract_images"),
            
            # Debug Options
            debug=job_data.get("debug"),
            debug_layout_images=job_data.get("debug_layout_images"),
            debug_pdf_images=job_data.get("debug_pdf_images"),
            debug_json=job_data.get("debug_json"),
            debug_data_folder=job_data.get("debug_data_folder"),
            
            llm_service=job_data.get("llm_service"),
            llm_model=job_data.get("llm_model"),
            
            # LLM Processing Options
            max_concurrency=job_data.get("max_concurrency"),
            confidence_threshold=job_data.get("confidence_threshold"),
            
            # Service-specific LLM configuration
            ollama_base_url=job_data.get("ollama_base_url"),
            openai_base_url=job_data.get("openai_base_url"),
            claude_model_name=job_data.get("claude_model_name"),
            vertex_project_id=job_data.get("vertex_project_id"),
            
            # Service-specific model names
            openai_model=job_data.get("openai_model"),
            ollama_model=job_data.get("ollama_model"),
            gemini_model_name=job_data.get("gemini_model_name"),
            
            status=ConversionStatus(job_data["status"]),
            progress=job_data["progress"],
            output_file_path=job_data.get("output_file_path"),
            output_metadata=job_data.get("output_metadata"),
            error_message=job_data.get("error_message"),
            created_at=datetime.fromisoformat(job_data["created_at"]),
            started_at=datetime.fromisoformat(job_data["started_at"]) if job_data.get("started_at") else None,
            completed_at=datetime.fromisoformat(job_data["completed_at"]) if job_data.get("completed_at") else None
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
    job_id: str,
    redis: RedisClient = Depends(get_redis)
):
    """Download conversion result as zip file containing all output files"""
    try:
        job_data = await redis.get_conversion_job(job_id)
        
        if not job_data:
            raise HTTPException(status_code=404, detail="Conversion job not found")
        
        if job_data["status"] != ConversionStatus.COMPLETED.value:
            raise HTTPException(status_code=400, detail="Job not completed")
        
        # Get job directory
        file_manager = FileManager()
        job_dir = file_manager.get_job_dir(job_id)
        
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
            zip_filename = f"conversion_job_{job_id}.zip"
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