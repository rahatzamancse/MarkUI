from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.conversion_job import ConversionStatus, OutputFormat

class ConversionJobCreate(BaseModel):
    """Schema for creating a conversion job"""
    pdf_document_id: int
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
    
    # LLM service configuration
    llm_service: Optional[str] = None
    llm_model: Optional[str] = None
    
    # Per-job API keys (optional, will fallback to settings if not provided)
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None

class ConversionJobResponse(BaseModel):
    """Response for conversion job"""
    id: int
    pdf_document_id: int
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
    
    # LLM service configuration
    llm_service: Optional[str]
    llm_model: Optional[str]
    
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

class ConversionJobListResponse(BaseModel):
    """Response for conversion job list"""
    jobs: List[ConversionJobResponse]
    total: int
    page: int
    per_page: int

class ConversionResult(BaseModel):
    """Conversion result with content"""
    job: ConversionJobResponse
    content: Optional[str] = None
    images: Optional[List[str]] = None 