from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class UserSettingsUpdate(BaseModel):
    """Schema for updating user settings"""
    theme: Optional[str] = None
    
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
    default_output_format: Optional[str] = None
    default_use_llm: Optional[bool] = None
    default_force_ocr: Optional[bool] = None
    default_format_lines: Optional[bool] = None
    
    # Additional settings
    additional_settings: Optional[Dict[str, Any]] = None

class UserSettingsResponse(BaseModel):
    """Response for user settings"""
    id: int
    theme: str
    
    # LLM Service settings
    default_llm_service: Optional[str]
    
    # API Keys (masked)
    has_gemini_api_key: bool
    has_openai_api_key: bool
    has_claude_api_key: bool
    
    # Ollama settings
    ollama_base_url: Optional[str]
    ollama_model: Optional[str]
    
    # OpenAI settings
    openai_model: Optional[str]
    openai_base_url: Optional[str]
    
    # Claude settings
    claude_model_name: Optional[str]
    
    # Vertex AI settings
    vertex_project_id: Optional[str]
    
    # Default conversion settings
    default_output_format: str
    default_use_llm: bool
    default_force_ocr: bool
    default_format_lines: bool
    
    # Additional settings
    additional_settings: Optional[Dict[str, Any]]

class LLMServiceInfo(BaseModel):
    """Information about available LLM services"""
    name: str
    display_name: str
    requires_api_key: bool
    models: Optional[List[str]] = None
    description: str

class LLMServicesResponse(BaseModel):
    """Response for available LLM services"""
    services: List[LLMServiceInfo]

class LLMServiceTestRequest(BaseModel):
    """Request for testing LLM service connection"""
    service_name: str
    # API keys for testing (optional, will fallback to settings if not provided)
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    # Service-specific settings
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None
    openai_model: Optional[str] = None
    openai_base_url: Optional[str] = None
    claude_model_name: Optional[str] = None
    vertex_project_id: Optional[str] = None

class LLMServiceTestResponse(BaseModel):
    """Response for LLM service connection test"""
    service_name: str
    success: bool
    message: str
    response_time_ms: Optional[int] = None
    error_details: Optional[str] = None 