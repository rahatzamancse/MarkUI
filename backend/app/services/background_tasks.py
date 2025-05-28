import asyncio
import logging
from datetime import datetime
from typing import Optional

from app.core.config import get_settings
from app.core.redis_client import RedisClient
from app.services.storage_manager import StorageManager

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    """Manager for background tasks"""
    
    def __init__(self, redis_client: RedisClient):
        self.settings = get_settings()
        self.redis = redis_client
        self.storage_manager = StorageManager(redis_client)
        self._storage_cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start all background tasks"""
        if self._running:
            logger.warning("Background tasks already running")
            return
        
        self._running = True
        logger.info("Starting background tasks...")
        
        # Start storage cleanup task
        self._storage_cleanup_task = asyncio.create_task(self._storage_cleanup_loop())
        
        logger.info("Background tasks started")
    
    async def stop(self):
        """Stop all background tasks"""
        if not self._running:
            return
        
        self._running = False
        logger.info("Stopping background tasks...")
        
        # Cancel storage cleanup task
        if self._storage_cleanup_task and not self._storage_cleanup_task.done():
            self._storage_cleanup_task.cancel()
            try:
                await self._storage_cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Background tasks stopped")
    
    async def _storage_cleanup_loop(self):
        """Periodic storage cleanup task"""
        logger.info(f"Storage cleanup task started (interval: {self.settings.storage_check_interval_minutes} minutes)")
        
        while self._running:
            try:
                # Wait for the specified interval
                await asyncio.sleep(self.settings.storage_check_interval_minutes * 60)
                
                if not self._running:
                    break
                
                # Perform storage cleanup check
                logger.debug("Running periodic storage cleanup check...")
                cleanup_stats = await self.storage_manager.trigger_cleanup_if_needed()
                
                if cleanup_stats:
                    logger.info(f"Periodic storage cleanup completed: {cleanup_stats}")
                else:
                    logger.debug("No storage cleanup needed")
                
            except asyncio.CancelledError:
                logger.info("Storage cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in storage cleanup task: {e}")
                # Continue running even if there's an error
                await asyncio.sleep(60)  # Wait 1 minute before retrying
        
        logger.info("Storage cleanup task stopped")

# Global instance
_background_task_manager: Optional[BackgroundTaskManager] = None

async def start_background_tasks(redis_client: RedisClient):
    """Start background tasks"""
    global _background_task_manager
    
    if _background_task_manager is None:
        _background_task_manager = BackgroundTaskManager(redis_client)
    
    await _background_task_manager.start()

async def stop_background_tasks():
    """Stop background tasks"""
    global _background_task_manager
    
    if _background_task_manager:
        await _background_task_manager.stop()

def get_background_task_manager() -> Optional[BackgroundTaskManager]:
    """Get the background task manager instance"""
    return _background_task_manager 