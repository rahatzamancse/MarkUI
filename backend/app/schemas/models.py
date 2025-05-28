from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class ConversionStatus(str, Enum):
    """Conversion job status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class OutputFormat(str, Enum):
    """Output format options"""
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"

class PDFDocument(BaseModel):
    """PDF Document data model"""
    id: str
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    mime_type: str
    total_pages: Optional[int] = None
    pdf_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    is_processed: bool = False
    processing_error: Optional[str] = None

class ConversionJob(BaseModel):
    """Conversion Job data model"""
    id: str
    pdf_document_id: str
    output_format: OutputFormat
    selected_pages: Optional[List[int]] = None
    
    # Marker options
    use_llm: bool = False
    force_ocr: bool = False
    strip_existing_ocr: bool = False
    format_lines: bool = False
    redo_inline_math: bool = False
    disable_image_extraction: bool = False
    paginate_output: bool = False
    
    # Performance & Quality Options
    lowres_image_dpi: Optional[int] = None
    highres_image_dpi: Optional[int] = None
    layout_batch_size: Optional[int] = None
    detection_batch_size: Optional[int] = None
    recognition_batch_size: Optional[int] = None
    
    # OCR & Text Processing Options
    languages: Optional[List[str]] = None
    ocr_task_name: Optional[str] = None
    disable_ocr_math: Optional[bool] = None
    keep_chars: Optional[bool] = None
    
    # Layout & Structure Options
    force_layout_block: Optional[str] = None
    column_gap_ratio: Optional[float] = None
    gap_threshold: Optional[float] = None
    list_gap_threshold: Optional[float] = None
    
    # Table Processing Options
    detect_boxes: Optional[bool] = None
    table_rec_batch_size: Optional[int] = None
    max_table_rows: Optional[int] = None
    max_rows_per_batch: Optional[int] = None
    
    # Section & Header Processing
    level_count: Optional[int] = None
    merge_threshold: Optional[float] = None
    default_level: Optional[int] = None
    
    # Advanced Processing Options
    min_equation_height: Optional[float] = None
    equation_batch_size: Optional[int] = None
    inlinemath_min_ratio: Optional[float] = None
    
    # Output Control Options
    page_separator: Optional[str] = None
    extract_images: Optional[bool] = None
    
    # Debug Options
    debug: Optional[bool] = None
    debug_layout_images: Optional[bool] = None
    debug_pdf_images: Optional[bool] = None
    debug_json: Optional[bool] = None
    debug_data_folder: Optional[str] = None
    
    # LLM service configuration
    llm_service: Optional[str] = None
    llm_model: Optional[str] = None
    
    # LLM Processing Options
    max_concurrency: Optional[int] = None
    confidence_threshold: Optional[float] = None
    
    # Per-job API keys
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    
    # Service-specific LLM configuration
    ollama_base_url: Optional[str] = None
    openai_base_url: Optional[str] = None
    claude_model_name: Optional[str] = None
    vertex_project_id: Optional[str] = None
    
    # Service-specific model names  
    openai_model: Optional[str] = None
    ollama_model: Optional[str] = None
    gemini_model_name: Optional[str] = None
    
    # Job status
    status: ConversionStatus = ConversionStatus.PENDING
    progress: int = 0
    
    # Output
    output_file_path: Optional[str] = None
    output_metadata: Optional[Dict[str, Any]] = None
    
    # Error handling
    error_message: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class UserSettings(BaseModel):
    """User Settings data model"""
    id: str = "user_settings"
    
    # Theme settings
    theme: str = "light"
    
    # LLM Service settings
    default_llm_service: Optional[str] = None
    
    # API Keys
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    
    # Ollama settings
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None
    
    # OpenAI settings
    openai_model: Optional[str] = None
    openai_base_url: Optional[str] = None
    
    # Claude settings
    claude_model_name: Optional[str] = None
    
    # Vertex AI settings
    vertex_project_id: Optional[str] = None
    
    # Default conversion settings
    default_output_format: str = "markdown"
    default_use_llm: bool = False
    default_force_ocr: bool = False
    default_format_lines: bool = False
    
    # Additional settings
    additional_settings: Optional[Dict[str, Any]] = None
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None 