from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    settings = get_settings()
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.version
    } 