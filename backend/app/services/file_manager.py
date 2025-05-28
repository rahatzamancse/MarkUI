import os
import shutil
import uuid
from pathlib import Path
from typing import Optional
import aiofiles
from fastapi import UploadFile
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)

class FileManager:
    """File management service"""
    
    def __init__(self):
        self.settings = get_settings()
        
    async def ensure_directories(self):
        """Ensure all required directories exist"""
        directories = [
            self.settings.upload_dir,
            self.settings.output_dir,
            self.settings.static_dir,
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            
    async def save_uploaded_file(self, file: UploadFile) -> tuple[str, str]:
        """
        Save uploaded file and return (filename, file_path)
        """
        # Generate unique filename
        if file.filename is None:
            raise ValueError("File must have a filename")
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(self.settings.upload_dir, unique_filename)
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
            
        logger.info(f"Saved uploaded file: {unique_filename}")
        return unique_filename, file_path
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False
    
    async def delete_directory(self, dir_path: str) -> bool:
        """Delete a directory and all its contents"""
        try:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
                logger.info(f"Deleted directory: {dir_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting directory {dir_path}: {e}")
            return False
    
    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        return os.path.getsize(file_path) if os.path.exists(file_path) else 0
    
    def get_job_dir(self, job_id: int) -> str:
        """Get job directory for a conversion job"""
        return os.path.join(self.settings.output_dir, f"job_{job_id}")
    
    def get_output_path(self, job_id: int, output_format: str) -> str:
        """Get output file path for a conversion job"""
        job_dir = self.get_job_dir(job_id)
        
        # Use specific filenames based on format
        if output_format == "markdown":
            filename = "index.md"
        elif output_format == "json":
            filename = "index.json"
        elif output_format == "html":
            filename = "index.html"
        else:
            filename = f"index.{output_format}"
        
        return os.path.join(job_dir, filename)
    
    def get_images_dir(self, job_id: int) -> str:
        """Get images directory for a conversion job (same as job directory)"""
        return self.get_job_dir(job_id)
    
    def ensure_job_directory(self, job_id: int) -> str:
        """Ensure job directory exists and return its path"""
        job_dir = self.get_job_dir(job_id)
        os.makedirs(job_dir, exist_ok=True)
        return job_dir
    
    async def cleanup_old_files(self, max_age_days: int = 7):
        """Clean up old files and directories"""
        import time
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60
        
        # Clean upload directory
        await self._cleanup_directory(self.settings.upload_dir, current_time, max_age_seconds)
        
        # Clean output directory
        await self._cleanup_directory(self.settings.output_dir, current_time, max_age_seconds)
        
    async def _cleanup_directory(self, directory: str, current_time: float, max_age_seconds: int):
        """Helper method to clean up a directory"""
        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isfile(item_path):
                    file_age = current_time - os.path.getmtime(item_path)
                    if file_age > max_age_seconds:
                        await self.delete_file(item_path)
                elif os.path.isdir(item_path):
                    dir_age = current_time - os.path.getmtime(item_path)
                    if dir_age > max_age_seconds:
                        await self.delete_directory(item_path)
        except Exception as e:
            logger.error(f"Error cleaning up directory {directory}: {e}") 