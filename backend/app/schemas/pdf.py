from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class PDFUploadResponse(BaseModel):
    """Response for PDF upload"""
    id: int
    filename: str
    original_filename: str
    file_size: int
    total_pages: int
    preview_images: List[str]
    metadata: Dict[str, Any]
    created_at: datetime

class PDFInfo(BaseModel):
    """PDF information"""
    id: int
    filename: str
    original_filename: str
    file_size: int
    total_pages: int
    metadata: Dict[str, Any]
    is_processed: bool
    created_at: datetime

class PDFListResponse(BaseModel):
    """Response for PDF list"""
    pdfs: List[PDFInfo]
    total: int
    page: int
    per_page: int 