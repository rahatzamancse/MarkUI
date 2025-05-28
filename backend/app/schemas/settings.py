from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

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

class ServerConfigResponse(BaseModel):
    """Response for server configuration (environment variables availability)"""
    # API key availability (boolean flags, not the actual keys)
    has_gemini_api_key: bool = False
    has_openai_api_key: bool = False
    has_claude_api_key: bool = False
    
    # Default model configurations from environment
    default_openai_model: Optional[str] = None
    default_openai_base_url: Optional[str] = None
    default_claude_model_name: Optional[str] = None
    default_ollama_base_url: Optional[str] = None
    default_ollama_model: Optional[str] = None
    default_vertex_project_id: Optional[str] = None 