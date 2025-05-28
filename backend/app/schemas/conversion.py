from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.schemas.models import ConversionStatus, OutputFormat

class ConversionJobCreate(BaseModel):
    """Schema for creating a conversion job"""
    pdf_document_id: str
    output_format: Optional[OutputFormat] = None
    selected_pages: Optional[List[int]] = None
    
    # Marker options - use Optional to distinguish between not provided and explicitly false
    use_llm: Optional[bool] = None
    force_ocr: Optional[bool] = None
    strip_existing_ocr: Optional[bool] = None
    format_lines: Optional[bool] = None
    redo_inline_math: Optional[bool] = None
    disable_image_extraction: Optional[bool] = None
    paginate_output: Optional[bool] = None
    
    # Performance & Quality Options
    lowres_image_dpi: Optional[int] = Field(None, description="DPI for low-resolution images (layout/line detection)", ge=50, le=300)
    highres_image_dpi: Optional[int] = Field(None, description="DPI for high-resolution images (OCR)", ge=100, le=600)
    layout_batch_size: Optional[int] = Field(None, description="Batch size for layout model", ge=1, le=32)
    detection_batch_size: Optional[int] = Field(None, description="Batch size for detection model", ge=1, le=32)
    recognition_batch_size: Optional[int] = Field(None, description="Batch size for recognition model", ge=1, le=32)
    
    # OCR & Text Processing Options
    languages: Optional[List[str]] = Field(None, description="Languages for OCR processing (e.g., ['en', 'fr', 'de'])")
    ocr_task_name: Optional[str] = Field(None, description="OCR mode: 'ocr_with_boxes' or 'ocr_without_boxes'")
    disable_ocr_math: Optional[bool] = Field(None, description="Disable inline math recognition in OCR")
    keep_chars: Optional[bool] = Field(None, description="Keep individual character information")
    
    # Layout & Structure Options
    force_layout_block: Optional[str] = Field(None, description="Force every page to be treated as specific block type")
    column_gap_ratio: Optional[float] = Field(None, description="Minimum ratio of page width to column gap", ge=0.0, le=1.0)
    gap_threshold: Optional[float] = Field(None, description="Minimum gap between blocks for grouping", ge=0.0, le=1.0)
    list_gap_threshold: Optional[float] = Field(None, description="Minimum gap between list items", ge=0.0, le=1.0)
    
    # Table Processing Options
    detect_boxes: Optional[bool] = Field(None, description="Detect boxes for table recognition")
    table_rec_batch_size: Optional[int] = Field(None, description="Batch size for table recognition", ge=1, le=32)
    max_table_rows: Optional[int] = Field(None, description="Maximum table rows to process with LLM", ge=1, le=500)
    max_rows_per_batch: Optional[int] = Field(None, description="Chunk tables with more rows than this", ge=1, le=200)
    
    # Section & Header Processing
    level_count: Optional[int] = Field(None, description="Number of heading levels to use", ge=1, le=10)
    merge_threshold: Optional[float] = Field(None, description="Minimum gap between headings for grouping", ge=0.0, le=1.0)
    default_level: Optional[int] = Field(None, description="Default heading level if none detected", ge=1, le=6)
    
    # Advanced Processing Options
    min_equation_height: Optional[float] = Field(None, description="Minimum equation height ratio for processing", ge=0.0, le=1.0)
    equation_batch_size: Optional[int] = Field(None, description="Batch size for equation processing", ge=1, le=32)
    inlinemath_min_ratio: Optional[float] = Field(None, description="Ratio threshold for assuming everything has math", ge=0.0, le=1.0)
    
    # Output Control Options
    page_separator: Optional[str] = Field(None, description="Separator to use between pages")
    extract_images: Optional[bool] = Field(None, description="Extract images from document")
    
    # Debug Options
    debug: Optional[bool] = Field(None, description="Enable debug mode")
    debug_layout_images: Optional[bool] = Field(None, description="Save layout debug images")
    debug_pdf_images: Optional[bool] = Field(None, description="Save PDF debug images")
    debug_json: Optional[bool] = Field(None, description="Save block debug data")
    debug_data_folder: Optional[str] = Field(None, description="Folder to save debug data")
    
    # LLM service configuration
    llm_service: Optional[str] = None
    llm_model: Optional[str] = None
    
    # LLM Processing Options
    max_concurrency: Optional[int] = Field(None, description="Maximum concurrent LLM requests", ge=1, le=20)
    confidence_threshold: Optional[float] = Field(None, description="Confidence threshold for relabeling", ge=0.0, le=1.0)
    
    # Per-job API keys (optional, will fallback to settings if not provided)
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None

class ConversionJobResponse(BaseModel):
    """Response for conversion job"""
    id: str
    pdf_document_id: str
    output_format: OutputFormat
    selected_pages: Optional[List[int]]
    
    # Marker options
    use_llm: bool
    force_ocr: bool
    strip_existing_ocr: bool
    format_lines: bool
    redo_inline_math: bool
    disable_image_extraction: bool
    paginate_output: bool
    
    # Performance & Quality Options
    lowres_image_dpi: Optional[int]
    highres_image_dpi: Optional[int]
    layout_batch_size: Optional[int]
    detection_batch_size: Optional[int]
    recognition_batch_size: Optional[int]
    
    # OCR & Text Processing Options
    languages: Optional[List[str]]
    ocr_task_name: Optional[str]
    disable_ocr_math: Optional[bool]
    keep_chars: Optional[bool]
    
    # Layout & Structure Options
    force_layout_block: Optional[str]
    column_gap_ratio: Optional[float]
    gap_threshold: Optional[float]
    list_gap_threshold: Optional[float]
    
    # Table Processing Options
    detect_boxes: Optional[bool]
    table_rec_batch_size: Optional[int]
    max_table_rows: Optional[int]
    max_rows_per_batch: Optional[int]
    
    # Section & Header Processing
    level_count: Optional[int]
    merge_threshold: Optional[float]
    default_level: Optional[int]
    
    # Advanced Processing Options
    min_equation_height: Optional[float]
    equation_batch_size: Optional[int]
    inlinemath_min_ratio: Optional[float]
    
    # Output Control Options
    page_separator: Optional[str]
    extract_images: Optional[bool]
    
    # Debug Options
    debug: Optional[bool]
    debug_layout_images: Optional[bool]
    debug_pdf_images: Optional[bool]
    debug_json: Optional[bool]
    debug_data_folder: Optional[str]
    
    # LLM service configuration
    llm_service: Optional[str]
    llm_model: Optional[str]
    
    # LLM Processing Options
    max_concurrency: Optional[int]
    confidence_threshold: Optional[float]
    
    # Job status
    status: ConversionStatus
    progress: int
    
    # Output
    output_file_path: Optional[str]
    output_metadata: Optional[Dict[str, Any]]
    
    # Error handling
    error_message: Optional[str]
    
    # Timestamps
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

class ConversionResult(BaseModel):
    """Conversion result with content"""
    job: ConversionJobResponse
    content: Optional[str] = None
    images: Optional[List[str]] = None 