from pydantic_settings import BaseSettings
from typing import Optional, List
import os
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings"""
    
    # App settings
    app_name: str = "MarkUI Backend"
    debug: bool = False
    version: str = "1.0.0"
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    
    # CORS settings
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # File storage settings
    upload_dir: str = "uploads"
    output_dir: str = "outputs"
    static_dir: str = "static"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    
    # PDF Storage Management (Hybrid Approach)
    max_stored_pdfs: int = 50  # Maximum number of PDFs to keep
    max_storage_size_mb: int = 5000  # Maximum total storage size (5GB)
    min_retention_hours: int = 24  # Minimum time to keep a PDF before deletion
    cleanup_batch_size: int = 10  # Number of files to delete in one cleanup batch
    storage_check_interval_minutes: int = 30  # How often to check storage limits
    
    # Redis settings (for data storage and task queue)
    redis_url: str = "redis://localhost:6379"
    
    # Marker library settings
    torch_device: Optional[str] = None
    
    # LLM Service settings
    # Gemini
    gemini_api_key: Optional[str] = None
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    openai_base_url: Optional[str] = None
    
    # Claude
    claude_api_key: Optional[str] = None
    claude_model_name: str = "claude-3-sonnet-20240229"
    
    # Vertex AI
    vertex_project_id: Optional[str] = None
    
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    
    # Security settings
    secret_key: str = "your-secret-key-change-this"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "env_prefix": "",
    }

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Create directories if they don't exist
def ensure_directories():
    """Ensure required directories exist"""
    settings = get_settings()
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.output_dir, exist_ok=True)
    os.makedirs(settings.static_dir, exist_ok=True) 