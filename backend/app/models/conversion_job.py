from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

class ConversionStatus(str, enum.Enum):
    """Conversion job status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class OutputFormat(str, enum.Enum):
    """Output format options"""
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"

class ConversionJob(Base):
    """Conversion Job model"""
    __tablename__ = "conversion_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    pdf_document_id = Column(Integer, ForeignKey("pdf_documents.id"), nullable=False)
    
    # Job configuration
    output_format = Column(Enum(OutputFormat), nullable=False)
    selected_pages = Column(JSON, nullable=True)  # List of page numbers
    
    # Marker options
    use_llm = Column(Boolean, default=False)
    force_ocr = Column(Boolean, default=False)
    strip_existing_ocr = Column(Boolean, default=False)
    format_lines = Column(Boolean, default=False)
    redo_inline_math = Column(Boolean, default=False)
    disable_image_extraction = Column(Boolean, default=False)
    paginate_output = Column(Boolean, default=False)
    
    # LLM service configuration
    llm_service = Column(String(100), nullable=True)
    llm_model = Column(String(100), nullable=True)
    
    # Per-job API keys (optional, will fallback to settings if not provided)
    gemini_api_key = Column(Text, nullable=True)
    openai_api_key = Column(Text, nullable=True)
    claude_api_key = Column(Text, nullable=True)
    
    # Job status
    status = Column(Enum(ConversionStatus), default=ConversionStatus.PENDING)
    progress = Column(Integer, default=0)  # 0-100
    
    # Output
    output_file_path = Column(String(500), nullable=True)
    output_metadata = Column(JSON, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    pdf_document = relationship("PDFDocument", backref="conversion_jobs") 