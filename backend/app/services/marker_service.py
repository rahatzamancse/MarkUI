import os
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor
import json
import datetime

from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from marker.config.parser import ConfigParser
from pdf2image import convert_from_path
from PIL import Image

from app.core.config import get_settings
from app.schemas.models import ConversionJob, OutputFormat
from app.services.file_manager import FileManager

logger = logging.getLogger(__name__)

class MarkerService:
    """Service for handling PDF conversion using marker library"""
    
    def __init__(self):
        self.settings = get_settings()
        self.file_manager = FileManager()
        self.executor = ThreadPoolExecutor(max_workers=2)
        
    async def get_pdf_info(self, pdf_path: str) -> Dict[str, Any]:
        """Get PDF information including page count and metadata"""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor, 
                self._get_pdf_info_sync, 
                pdf_path
            )
        except Exception as e:
            logger.error(f"Error getting PDF info: {e}")
            raise
    
    def _get_pdf_info_sync(self, pdf_path: str) -> Dict[str, Any]:
        """Synchronous PDF info extraction"""
        from PyPDF2 import PdfReader
        
        try:
            reader = PdfReader(pdf_path)
            page_count = len(reader.pages)
            
            # Get metadata
            metadata = {}
            if reader.metadata:
                metadata = {
                    "title": reader.metadata.get("/Title", ""),
                    "author": reader.metadata.get("/Author", ""),
                    "subject": reader.metadata.get("/Subject", ""),
                    "creator": reader.metadata.get("/Creator", ""),
                    "producer": reader.metadata.get("/Producer", ""),
                    "creation_date": str(reader.metadata.get("/CreationDate", "")),
                    "modification_date": str(reader.metadata.get("/ModDate", "")),
                }
            
            return {
                "page_count": page_count,
                "metadata": metadata
            }
        except Exception as e:
            logger.error(f"Error reading PDF: {e}")
            return {"page_count": 0, "metadata": {}}
    
    async def generate_pdf_preview(self, pdf_path: str, max_pages: int = 10) -> List[str]:
        """Generate preview images for PDF pages"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor,
                self._generate_pdf_preview_sync,
                pdf_path,
                max_pages
            )
        except Exception as e:
            logger.error(f"Error generating PDF preview: {e}")
            return []
    
    def _generate_pdf_preview_sync(self, pdf_path: str, max_pages: int) -> List[str]:
        """Synchronous PDF preview generation"""
        try:
            # Convert PDF pages to images
            images = convert_from_path(
                pdf_path, 
                dpi=150, 
                first_page=1, 
                last_page=max_pages,
                fmt='JPEG'
            )
            
            preview_paths = []
            pdf_name = Path(pdf_path).stem
            
            for i, image in enumerate(images):
                # Save preview image
                preview_filename = f"{pdf_name}_page_{i+1}.jpg"
                preview_path = os.path.join(self.settings.static_dir, preview_filename)
                
                # Resize image for preview
                image.thumbnail((800, 1000), Image.Resampling.LANCZOS)
                image.save(preview_path, "JPEG", quality=85)
                
                preview_paths.append(f"/static/{preview_filename}")
            
            return preview_paths
            
        except Exception as e:
            logger.error(f"Error generating preview: {e}")
            return []
    
    async def convert_pdf(self, job: ConversionJob, pdf_path: str) -> Dict[str, Any]:
        """Convert PDF using marker library"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor,
                self._convert_pdf_sync,
                job,
                pdf_path
            )
        except Exception as e:
            logger.error(f"Error converting PDF: {e}")
            raise
    
    def _convert_pdf_sync(self, job: ConversionJob, pdf_path: str) -> Dict[str, Any]:
        """Synchronous PDF conversion using marker library"""
        try:
            # Build marker configuration
            config = self._build_marker_config(job)
            logger.info(f"Using marker config: {config}")
            
            # Create config parser and converter
            config_parser = ConfigParser(config)
            
            # Create the converter with proper configuration
            try:
                converter = PdfConverter(
                    config=config_parser.generate_config_dict(),
                    artifact_dict=create_model_dict(),
                    processor_list=config_parser.get_processors(),
                    renderer=config_parser.get_renderer(),
                    llm_service=config_parser.get_llm_service()
                )
            except Exception as e:
                logger.error(f"Error creating PdfConverter: {e}")
                # Fallback to basic converter without custom configuration
                converter = PdfConverter(
                    artifact_dict=create_model_dict(),
                )
            
            # Convert the PDF
            logger.info(f"Starting marker conversion for: {pdf_path}")
            rendered = converter(pdf_path)
            
            # Extract text and images from rendered output
            text, metadata, images = text_from_rendered(rendered)
            
            # Ensure metadata is always a dictionary
            if not isinstance(metadata, dict):
                metadata = {"format": str(metadata)} if metadata else {}
            
            # Get job details
            job_id = getattr(job, 'id')
            output_format = getattr(job, 'output_format')
            disable_image_extraction = getattr(job, 'disable_image_extraction', False)
            
            # Handle images if not disabled
            images_dir = None
            if images and not disable_image_extraction:
                # Ensure job directory exists
                images_dir = self.file_manager.ensure_job_directory(job_id)
                
                # Save extracted images
                for image_name, image_data in images.items():
                    try:
                        # Check if image_name already has an extension
                        if '.' in image_name and image_name.split('.')[-1].lower() in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
                            # Image name already has an extension, use it as is
                            image_filename = image_name
                        else:
                            # No extension, add .png
                            image_filename = f"{image_name}.png"
                        
                        image_path = os.path.join(images_dir, image_filename)
                        
                        if isinstance(image_data, bytes):
                            # Handle base64 encoded images
                            import base64
                            with open(image_path, 'wb') as f:
                                f.write(base64.b64decode(image_data))
                        elif isinstance(image_data, str):
                            # Handle base64 string
                            import base64
                            with open(image_path, 'wb') as f:
                                f.write(base64.b64decode(image_data))
                        elif hasattr(image_data, 'save'):
                            # Handle PIL Image objects
                            image_data.save(image_path)
                        else:
                            logger.warning(f"Unknown image data type for {image_name}: {type(image_data)}")
                    except Exception as e:
                        logger.error(f"Error saving image {image_name}: {e}")
                        continue
            
            # Process output based on format
            output_content = ""
            if output_format == OutputFormat.MARKDOWN:
                output_content = str(text) if text is not None else ""
            elif output_format == OutputFormat.JSON:
                # For JSON output, use the rendered object directly
                try:
                    if hasattr(rendered, 'model_dump'):
                        # Try to serialize the model dump
                        model_data = rendered.model_dump()
                        output_content = self._safe_json_dumps(model_data)
                    elif hasattr(rendered, 'dict'):
                        # Try to serialize the dict
                        dict_data = rendered.dict()
                        output_content = self._safe_json_dumps(dict_data)
                    else:
                        # Fallback to text with metadata
                        fallback_data = {
                            "text": str(text) if text is not None else "",
                            "metadata": self._make_json_serializable(metadata) if metadata else {},
                            "images": self._get_safe_image_list(images)
                        }
                        output_content = self._safe_json_dumps(fallback_data)
                except (TypeError, ValueError) as json_error:
                    logger.warning(f"JSON serialization failed: {json_error}, using fallback")
                    logger.debug(f"Rendered object type: {type(rendered)}")
                    logger.debug(f"Metadata type: {type(metadata)}")
                    logger.debug(f"Images type: {type(images)}")
                    # Safe fallback with basic data
                    fallback_data = {
                        "text": str(text) if text is not None else "",
                        "metadata": self._make_json_serializable(metadata) if metadata else {},
                        "images": self._get_safe_image_list(images),
                        "conversion_note": "Original data contained non-serializable objects"
                    }
                    output_content = self._safe_json_dumps(fallback_data)
            elif output_format == OutputFormat.HTML:
                # For HTML output, check if rendered has html attribute
                if hasattr(rendered, 'html'):
                    output_content = rendered.html
                else:
                    # Fallback to simple HTML conversion
                    # Ensure text is a string before calling replace
                    text_str = str(text) if text is not None else ""
                    output_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>PDF Conversion</title>
</head>
<body>
    <div style="max-width: 800px; margin: 0 auto; padding: 20px; font-family: Arial, sans-serif;">
        {text_str.replace('\n', '<br>')}
    </div>
</body>
</html>"""
            # Save output file
            # Ensure job directory exists
            self.file_manager.ensure_job_directory(job_id)
            output_path = self.file_manager.get_output_path(job_id, output_format.value)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(str(output_content))
            
            logger.info(f"Marker conversion completed successfully for job {job_id}")
            
            return {
                "output_path": output_path,
                "images_dir": images_dir,
                "metadata": metadata,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error in marker conversion: {e}")
            return {
                "output_path": None,
                "images_dir": None,
                "metadata": {},
                "success": False,
                "error": str(e)
            }
    
    def _build_marker_config(self, job: ConversionJob) -> Dict[str, Any]:
        """Build marker configuration from job settings"""
        # Extract values using getattr for consistent attribute access
        output_format = getattr(job, 'output_format')
        selected_pages = getattr(job, 'selected_pages', None)
        use_llm = getattr(job, 'use_llm', False)
        llm_service = getattr(job, 'llm_service', None)
        llm_model = getattr(job, 'llm_model', None)
        force_ocr = getattr(job, 'force_ocr', False)
        strip_existing_ocr = getattr(job, 'strip_existing_ocr', False)
        format_lines = getattr(job, 'format_lines', False)
        redo_inline_math = getattr(job, 'redo_inline_math', False)
        disable_image_extraction = getattr(job, 'disable_image_extraction', False)
        paginate_output = getattr(job, 'paginate_output', False)
        
        config = {
            "output_format": output_format.value,
            "use_llm": use_llm,
            "force_ocr": force_ocr,
            "strip_existing_ocr": strip_existing_ocr,
            "format_lines": format_lines,
            "redo_inline_math": redo_inline_math,
            "disable_image_extraction": disable_image_extraction,
            "paginate_output": paginate_output,
        }
        
        # Add page range if specified
        if selected_pages:
            # Convert page numbers to marker format (0-indexed)
            page_range = ",".join([str(p - 1) for p in selected_pages])
            config["page_range"] = page_range
        
        # Add LLM configuration
        if use_llm and llm_service:
            config["llm_service"] = llm_service
            
            # Add API keys from job if available
            gemini_api_key = getattr(job, 'gemini_api_key', None)
            openai_api_key = getattr(job, 'openai_api_key', None)
            claude_api_key = getattr(job, 'claude_api_key', None)
            
            if gemini_api_key:
                config["gemini_api_key"] = gemini_api_key
            if openai_api_key:
                config["openai_api_key"] = openai_api_key
            if claude_api_key:
                config["claude_api_key"] = claude_api_key
            
            # Add service-specific configuration
            ollama_base_url = getattr(job, 'ollama_base_url', None)
            openai_base_url = getattr(job, 'openai_base_url', None)
            claude_model_name = getattr(job, 'claude_model_name', None)
            vertex_project_id = getattr(job, 'vertex_project_id', None)
            
            if ollama_base_url and "ollama" in llm_service.lower():
                config["ollama_base_url"] = ollama_base_url
            if openai_base_url and "openai" in llm_service.lower():
                config["openai_base_url"] = openai_base_url
            if claude_model_name and "claude" in llm_service.lower():
                config["claude_model_name"] = claude_model_name
            if vertex_project_id and "vertex" in llm_service.lower():
                config["vertex_project_id"] = vertex_project_id
            
            # Add service-specific model names with priority over general llm_model
            service_specific_openai_model = getattr(job, 'openai_model', None)
            service_specific_ollama_model = getattr(job, 'ollama_model', None) 
            service_specific_gemini_model = getattr(job, 'gemini_model_name', None)
            general_llm_model = getattr(job, 'llm_model', None)
            
            if "gemini" in llm_service.lower():
                # Use service-specific model if available, then general model, then environment default
                if service_specific_gemini_model:
                    config["gemini_model_name"] = service_specific_gemini_model
                elif general_llm_model:
                    config["gemini_model_name"] = general_llm_model
            elif "openai" in llm_service.lower():
                # Use service-specific model if available, then general model, then environment default
                if service_specific_openai_model:
                    config["openai_model"] = service_specific_openai_model
                elif general_llm_model:
                    config["openai_model"] = general_llm_model
            elif "claude" in llm_service.lower():
                # Use service-specific model if available, then general model, then environment default
                if claude_model_name:
                    config["claude_model_name"] = claude_model_name
                elif general_llm_model:
                    config["claude_model_name"] = general_llm_model
            elif "ollama" in llm_service.lower():
                # Use service-specific model if available, then general model, then environment default
                if service_specific_ollama_model:
                    config["ollama_model"] = service_specific_ollama_model
                elif general_llm_model:
                    config["ollama_model"] = general_llm_model
        
        # Performance & Quality Options
        if hasattr(job, 'lowres_image_dpi') and job.lowres_image_dpi is not None:
            config["lowres_image_dpi"] = job.lowres_image_dpi
        if hasattr(job, 'highres_image_dpi') and job.highres_image_dpi is not None:
            config["highres_image_dpi"] = job.highres_image_dpi
        if hasattr(job, 'layout_batch_size') and job.layout_batch_size is not None:
            config["layout_batch_size"] = job.layout_batch_size
        if hasattr(job, 'detection_batch_size') and job.detection_batch_size is not None:
            config["detection_batch_size"] = job.detection_batch_size
        if hasattr(job, 'recognition_batch_size') and job.recognition_batch_size is not None:
            config["recognition_batch_size"] = job.recognition_batch_size
        
        # OCR & Text Processing Options
        if hasattr(job, 'languages') and job.languages is not None:
            config["languages"] = ",".join(job.languages)
        if hasattr(job, 'ocr_task_name') and job.ocr_task_name is not None:
            config["ocr_task_name"] = job.ocr_task_name
        if hasattr(job, 'disable_ocr_math') and job.disable_ocr_math is not None:
            config["disable_ocr_math"] = job.disable_ocr_math
        if hasattr(job, 'keep_chars') and job.keep_chars is not None:
            config["keep_chars"] = job.keep_chars
        
        # Layout & Structure Options
        if hasattr(job, 'force_layout_block') and job.force_layout_block is not None:
            config["force_layout_block"] = job.force_layout_block
        if hasattr(job, 'column_gap_ratio') and job.column_gap_ratio is not None:
            config["column_gap_ratio"] = job.column_gap_ratio
        if hasattr(job, 'gap_threshold') and job.gap_threshold is not None:
            config["gap_threshold"] = job.gap_threshold
        if hasattr(job, 'list_gap_threshold') and job.list_gap_threshold is not None:
            config["list_gap_threshold"] = job.list_gap_threshold
        
        # Table Processing Options
        if hasattr(job, 'detect_boxes') and job.detect_boxes is not None:
            config["detect_boxes"] = job.detect_boxes
        if hasattr(job, 'table_rec_batch_size') and job.table_rec_batch_size is not None:
            config["table_rec_batch_size"] = job.table_rec_batch_size
        if hasattr(job, 'max_table_rows') and job.max_table_rows is not None:
            config["max_table_rows"] = job.max_table_rows
        if hasattr(job, 'max_rows_per_batch') and job.max_rows_per_batch is not None:
            config["max_rows_per_batch"] = job.max_rows_per_batch
        
        # Section & Header Processing
        if hasattr(job, 'level_count') and job.level_count is not None:
            config["level_count"] = job.level_count
        if hasattr(job, 'merge_threshold') and job.merge_threshold is not None:
            config["merge_threshold"] = job.merge_threshold
        if hasattr(job, 'default_level') and job.default_level is not None:
            config["default_level"] = job.default_level
        
        # Advanced Processing Options
        if hasattr(job, 'min_equation_height') and job.min_equation_height is not None:
            config["min_equation_height"] = job.min_equation_height
        if hasattr(job, 'equation_batch_size') and job.equation_batch_size is not None:
            config["equation_batch_size"] = job.equation_batch_size
        if hasattr(job, 'inlinemath_min_ratio') and job.inlinemath_min_ratio is not None:
            config["inlinemath_min_ratio"] = job.inlinemath_min_ratio
        
        # Output Control Options
        if hasattr(job, 'page_separator') and job.page_separator is not None:
            config["page_separator"] = job.page_separator
        if hasattr(job, 'extract_images') and job.extract_images is not None:
            config["extract_images"] = job.extract_images
        
        # Debug Options
        if hasattr(job, 'debug') and job.debug is not None:
            config["debug"] = job.debug
        if hasattr(job, 'debug_layout_images') and job.debug_layout_images is not None:
            config["debug_layout_images"] = job.debug_layout_images
        if hasattr(job, 'debug_pdf_images') and job.debug_pdf_images is not None:
            config["debug_pdf_images"] = job.debug_pdf_images
        if hasattr(job, 'debug_json') and job.debug_json is not None:
            config["debug_json"] = job.debug_json
        if hasattr(job, 'debug_data_folder') and job.debug_data_folder is not None:
            config["debug_data_folder"] = job.debug_data_folder
        
        # LLM Processing Options
        if hasattr(job, 'max_concurrency') and job.max_concurrency is not None:
            config["max_concurrency"] = job.max_concurrency
        if hasattr(job, 'confidence_threshold') and job.confidence_threshold is not None:
            config["confidence_threshold"] = job.confidence_threshold
        
        return config

    def _make_json_serializable(self, obj):
        """Helper function to make an object JSON serializable"""
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, (str, int, float, bool)):
            return obj
        elif isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        else:
            return str(obj) 

    def _get_safe_image_list(self, images):
        """Helper function to safely convert images to a list"""
        try:
            if not images:
                return []
            elif isinstance(images, dict):
                return list(images.keys())
            elif isinstance(images, (list, tuple)):
                return list(images)
            else:
                logger.warning(f"Unexpected images type: {type(images)}")
                return []
        except Exception as e:
            logger.error(f"Error processing images for JSON: {e}")
            return [] 

    def _safe_json_dumps(self, obj):
        """Helper function to safely serialize JSON"""
        try:
            return json.dumps(obj, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"Error serializing JSON: {e}")
            # Return a basic JSON structure as fallback
            return json.dumps({
                "error": "JSON serialization failed",
                "message": str(e),
                "data_type": str(type(obj))
            }, indent=2) 