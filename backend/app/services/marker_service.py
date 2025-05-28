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
from app.models.conversion_job import ConversionJob, OutputFormat
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
        # Extract values using getattr to avoid SQLAlchemy Column type issues
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
        }
        
        # Add page range if specified (marker uses 0-based indexing)
        if selected_pages:
            page_ranges = []
            for page in selected_pages:
                # Convert from 1-based (frontend) to 0-based (marker) page numbering
                # Validate that page number is positive
                if page < 1:
                    logger.warning(f"Invalid page number {page}, skipping")
                    continue
                zero_based_page = page - 1
                page_ranges.append(str(zero_based_page))
            
            if page_ranges:
                config["page_range"] = ",".join(page_ranges)
        
        # Add marker options using correct parameter names from help output
        if use_llm:
            config["use_llm"] = True
            if llm_service:
                config["llm_service"] = llm_service
        
        if force_ocr:
            config["force_ocr"] = True
            
        if strip_existing_ocr:
            config["strip_existing_ocr"] = True
            
        if format_lines:
            config["format_lines"] = True
            
        if redo_inline_math:
            config["redo_inline_math"] = True
            
        if disable_image_extraction:
            config["disable_image_extraction"] = True
            
        if paginate_output:
            config["paginate_output"] = True
        
        # Add LLM service configuration using correct parameter names
        if use_llm and llm_service:
            # Get job-specific API keys
            job_gemini_key = getattr(job, 'gemini_api_key', None)
            job_openai_key = getattr(job, 'openai_api_key', None)
            job_claude_key = getattr(job, 'claude_api_key', None)
            
            if "gemini" in llm_service.lower():
                # Use job-specific key or fallback to settings
                api_key = job_gemini_key or self.settings.gemini_api_key
                if api_key:
                    config["gemini_api_key"] = api_key
                if llm_model:
                    config["gemini_model_name"] = llm_model
            elif "openai" in llm_service.lower():
                # Use job-specific key or fallback to settings
                api_key = job_openai_key or self.settings.openai_api_key
                if api_key:
                    config["openai_api_key"] = api_key
                config["openai_model"] = llm_model or self.settings.openai_model
                if self.settings.openai_base_url:
                    config["openai_base_url"] = self.settings.openai_base_url
            elif "claude" in llm_service.lower():
                # Use job-specific key or fallback to settings
                api_key = job_claude_key or self.settings.claude_api_key
                if api_key:
                    config["claude_api_key"] = api_key
                if llm_model:
                    config["claude_model_name"] = llm_model
            elif "ollama" in llm_service.lower():
                config["ollama_base_url"] = self.settings.ollama_base_url
                config["ollama_model"] = llm_model or self.settings.ollama_model
            elif "vertex" in llm_service.lower():
                config["vertex_project_id"] = self.settings.vertex_project_id
                vertex_location = getattr(self.settings, 'vertex_location', None)
                if vertex_location:
                    config["vertex_location"] = vertex_location
        
        # Add additional configuration options that might be useful
        # Image extraction settings
        if not disable_image_extraction:
            config["extract_images"] = True
        
        # OCR settings
        if hasattr(job, 'disable_ocr') and getattr(job, 'disable_ocr', False):
            config["disable_ocr"] = True
        
        # Debug settings
        if hasattr(job, 'debug') and getattr(job, 'debug', False):
            config["debug"] = True
        
        # Performance settings
        layout_batch_size = getattr(self.settings, 'layout_batch_size', None)
        if layout_batch_size:
            config["layout_batch_size"] = layout_batch_size
        
        recognition_batch_size = getattr(self.settings, 'recognition_batch_size', None)
        if recognition_batch_size:
            config["recognition_batch_size"] = recognition_batch_size
        
        # DPI settings for image processing
        lowres_image_dpi = getattr(self.settings, 'lowres_image_dpi', None)
        if lowres_image_dpi:
            config["lowres_image_dpi"] = lowres_image_dpi
        
        highres_image_dpi = getattr(self.settings, 'highres_image_dpi', None)
        if highres_image_dpi:
            config["highres_image_dpi"] = highres_image_dpi
        
        # Disable progress bars in production
        config["disable_tqdm"] = True
        
        # Disable multiprocessing in production for better control
        config["disable_multiprocessing"] = True
        
        # Add OCR quality thresholds if available in settings
        ocr_space_threshold = getattr(self.settings, 'ocr_space_threshold', None)
        if ocr_space_threshold:
            config["ocr_space_threshold"] = ocr_space_threshold
        
        ocr_newline_threshold = getattr(self.settings, 'ocr_newline_threshold', None)
        if ocr_newline_threshold:
            config["ocr_newline_threshold"] = ocr_newline_threshold
        
        ocr_alphanum_threshold = getattr(self.settings, 'ocr_alphanum_threshold', None)
        if ocr_alphanum_threshold:
            config["ocr_alphanum_threshold"] = ocr_alphanum_threshold
        
        # Add timeout settings for LLM services
        if use_llm:
            timeout = getattr(self.settings, 'llm_timeout', 30)
            config["timeout"] = timeout
            
            max_retries = getattr(self.settings, 'llm_max_retries', 2)
            config["max_retries"] = max_retries
            
            retry_wait_time = getattr(self.settings, 'llm_retry_wait_time', 3)
            config["retry_wait_time"] = retry_wait_time
        
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