from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from contextlib import asynccontextmanager
import os
import logging
from dotenv import load_dotenv

from app.api.routes import pdf, conversion, settings
from app.core.config import get_settings
from app.core.redis_client import init_redis, close_redis, redis_client
from app.services.file_manager import FileManager
from app.services.background_tasks import start_background_tasks, stop_background_tasks

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting MarkUI Backend...")
    
    # Initialize Redis
    await init_redis()
    
    # Initialize file manager
    file_manager = FileManager()
    await file_manager.ensure_directories()
    
    # Start background tasks
    await start_background_tasks(redis_client)
    logger.info("Background tasks started")
    
    logger.info("MarkUI Backend started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down MarkUI Backend...")
    
    # Stop background tasks
    await stop_background_tasks()
    logger.info("Background tasks stopped")
    
    # Close Redis
    await close_redis()

# Create FastAPI app
app = FastAPI(
    title="MarkUI Backend",
    description="FastAPI wrapper for marker library - Convert PDFs to Markdown, JSON, and HTML",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
config_settings = get_settings()
os.makedirs(config_settings.static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=config_settings.static_dir), name="static")

# Mount output directory for conversion outputs (new structure)
os.makedirs(config_settings.output_dir, exist_ok=True)
app.mount("/output", StaticFiles(directory=config_settings.output_dir), name="output")

# Old images mount removed - now using /output for job folders

# Include routers
app.include_router(pdf.router, prefix="/api/v1/pdf", tags=["pdf"])
app.include_router(conversion.router, prefix="/api/v1/conversion", tags=["conversion"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["settings"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MarkUI Backend API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 