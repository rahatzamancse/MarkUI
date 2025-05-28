from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON
from sqlalchemy.sql import func
from app.core.database import Base

class UserSettings(Base):
    """User Settings model"""
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Theme settings
    theme = Column(String(20), default="light")  # light, dark
    
    # LLM Service settings
    default_llm_service = Column(String(100), nullable=True)
    
    # API Keys (encrypted)
    gemini_api_key = Column(Text, nullable=True)
    openai_api_key = Column(Text, nullable=True)
    claude_api_key = Column(Text, nullable=True)
    
    # Ollama settings
    ollama_base_url = Column(String(255), nullable=True)
    ollama_model = Column(String(100), nullable=True)
    
    # OpenAI settings
    openai_model = Column(String(100), nullable=True)
    openai_base_url = Column(String(255), nullable=True)
    
    # Claude settings
    claude_model_name = Column(String(100), nullable=True)
    
    # Vertex AI settings
    vertex_project_id = Column(String(255), nullable=True)
    
    # Default conversion settings
    default_output_format = Column(String(20), default="markdown")
    default_use_llm = Column(Boolean, default=False)
    default_force_ocr = Column(Boolean, default=False)
    default_format_lines = Column(Boolean, default=False)
    
    # Additional settings as JSON
    additional_settings = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 