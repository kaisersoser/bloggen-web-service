"""
Generation Queue Manager

Manages the FIFO queue for blog generation with single-worker processing.
Ensures only one blog is generated at a time with automatic queuing.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from core.database_service import database_service

logger = logging.getLogger(__name__)


class QueueStatus(str, Enum):
    """Queue status states"""
    IDLE = "idle"
    PROCESSING = "processing"
    ERROR = "error"


class GenerationQueueManager:
    """
    Manages the FIFO queue for blog generation.
    Ensures only one blog is processed at a time.
    
    Key features:
    - Single worker processing with asyncio lock
    - FIFO queue based on database createdAt timestamp
    - Automatic job startup after completion
    - Queue position tracking
    - Estimated wait time calculation
    """
    
    _instance: Optional['GenerationQueueManager'] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        """Singleton pattern to ensure single queue manager"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize queue manager"""
        if self._initialized:
            return
            
        self.current_job_id: Optional[str] = None
        self.processing_lock = asyncio.Lock()
        self.status = QueueStatus.IDLE
        self.queue_worker_task: Optional[asyncio.Task] = None
        self._stop_worker = False
        self._initialized = True
        self._generation_callback = None  # Callback to trigger blog generation
        
        # Statistics
        self.stats = {
            "total_processed": 0,
            "total_failed": 0,
            "average_duration": 0,
            "current_job_started_at": None
        }
        
        logger.info("🎯 GenerationQueueManager initialized")
    
    def set_generation_callback(self, callback):
        """
        Set the callback function to trigger blog generation.
        
        Args:
            callback: Async function that takes (task_id, topic, user_id, instructions)
        """
        self._generation_callback = callback
        logger.info("✅ Generation callback registered")
    
    async def start_queue_worker(self):
        """Start the background queue worker"""
        if self.queue_worker_task and not self.queue_worker_task.done():
            logger.warning("Queue worker already running")
            return
        
        # Recover any stuck IN_PROGRESS jobs on startup
        await self._recover_stuck_jobs()
        
        self._stop_worker = False
        self.queue_worker_task = asyncio.create_task(
            self._queue_worker_loop(),
            name="generation-queue-worker"
        )
        logger.info("🚀 Queue worker started")
    
    async def stop_queue_worker(self):
        """Stop the background queue worker gracefully"""
        if not self.queue_worker_task:
            return
        
        self._stop_worker = True
        
        if self.queue_worker_task:
            try:
                await asyncio.wait_for(self.queue_worker_task, timeout=5.0)
            except asyncio.TimeoutError:
                self.queue_worker_task.cancel()
                try:
                    await self.queue_worker_task
                except asyncio.CancelledError:
                    pass
        
        logger.info("🛑 Queue worker stopped")
    
    async def _queue_worker_loop(self):
        """Background worker that processes queued jobs"""
        logger.info("🔄 Queue worker loop started")
        
        while not self._stop_worker:
            try:
                # Check for next job
                await self.start_next_job()
                
                # Wait before checking again
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in queue worker loop: {e}", exc_info=True)
                self.status = QueueStatus.ERROR
                await asyncio.sleep(5)  # Longer wait on error
        
        logger.info("🔄 Queue worker loop stopped")
    
    async def enqueue_blog(
        self,
        task_id: str,
        user_id: str,
        topic: Optional[str],
        instructions: Optional[str]
    ) -> Dict[str, Any]:
        """
        Add blog to generation queue.
        
        Args:
            task_id: Unique task identifier
            user_id: User who requested the blog
            topic: Blog topic (may be None for auto-generation)
            instructions: Optional generation instructions
        
        Returns:
            Dictionary with task_id, status, queue_position, message
        """
        try:
            # Blog record should already be created by task_manager.create_task()
            # We just need to check queue position and possibly start processing
            
            queue_position = await self._get_queue_position(task_id)
            
            logger.info(
                f"📥 Blog enqueued: {task_id} for user {user_id} "
                f"(position: {queue_position})"
            )
            
            # If no job is currently processing, start immediately
            if self.current_job_id is None:
                asyncio.create_task(self.start_next_job())
            
            return {
                "task_id": task_id,
                "status": "queued",
                "queue_position": queue_position,
                "message": f"Blog queued for generation (position: {queue_position})"
            }
            
        except Exception as e:
            logger.error(f"Failed to enqueue blog {task_id}: {e}", exc_info=True)
            raise
    
    async def start_next_job(self):
        """
        Process the next queued blog.
        Called automatically by worker loop and after job completion.
        """
        async with self.processing_lock:
            # Skip if already processing
            if self.current_job_id is not None:
                return
            
            try:
                # Find oldest QUEUED blog
                next_blog = await self._get_next_queued_blog()
                
                if next_blog is None:
                    self.status = QueueStatus.IDLE
                    return
                
                # Mark as current job
                self.current_job_id = next_blog["id"]
                self.status = QueueStatus.PROCESSING
                self.stats["current_job_started_at"] = datetime.utcnow().isoformat()
                
                logger.info(f"🎬 Starting blog generation: {self.current_job_id}")
                
                # Update status to IN_PROGRESS
                await database_service.execute(
                    """
                    UPDATE blogs
                    SET status = 'IN_PROGRESS',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                    """,
                    self.current_job_id
                )
                
                # Trigger actual blog generation if callback is registered
                if self._generation_callback:
                    logger.info(f"🚀 Triggering blog generation via callback for {self.current_job_id}")
                    asyncio.create_task(
                        self._generation_callback(
                            next_blog["id"],
                            next_blog.get("topic"),
                            next_blog["user_id"],
                            next_blog.get("instructions")
                        )
                    )
                else:
                    logger.error("❌ No generation callback registered! Blog will not be generated.")
                    self.current_job_id = None
                    self.status = QueueStatus.ERROR
                
            except Exception as e:
                logger.error(f"Error starting next job: {e}", exc_info=True)
                self.status = QueueStatus.ERROR
                self.current_job_id = None
    
    async def mark_job_completed(self, task_id: str, success: bool = True):
        """
        Mark a job as completed and start the next one.
        
        Args:
            task_id: Task identifier
            success: Whether job completed successfully
        """
        async with self.processing_lock:
            if self.current_job_id != task_id:
                logger.warning(
                    f"Attempted to complete job {task_id} but current job is "
                    f"{self.current_job_id}"
                )
                return
            
            # Update statistics
            self.stats["total_processed"] += 1
            if not success:
                self.stats["total_failed"] += 1
            
            if self.stats["current_job_started_at"]:
                started = datetime.fromisoformat(self.stats["current_job_started_at"])
                duration = (datetime.utcnow() - started).total_seconds()
                
                # Update average duration (exponential moving average)
                if self.stats["average_duration"] == 0:
                    self.stats["average_duration"] = duration
                else:
                    self.stats["average_duration"] = (
                        0.7 * self.stats["average_duration"] + 0.3 * duration
                    )
            
            # Clear current job
            self.current_job_id = None
            self.stats["current_job_started_at"] = None
            self.status = QueueStatus.IDLE
            
            logger.info(
                f"✅ Job completed: {task_id} (success: {success})"
            )
        
        # Start next job (outside lock to avoid blocking)
        await self.start_next_job()
    
    async def get_queue_status(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current queue status.
        
        Args:
            user_id: Optional user ID to get user-specific counts
        
        Returns:
            Dictionary with queue statistics
        """
        try:
            # Count total queued blogs
            total_queued = await database_service.fetchrow(
                "SELECT COUNT(*) as count FROM blogs WHERE status = 'QUEUED'"
            )
            
            # Count user's queued blogs if user_id provided
            user_queued_count = 0
            if user_id:
                result = await database_service.fetchrow(
                    """
                    SELECT COUNT(*) as count
                    FROM blogs
                    WHERE status = 'QUEUED' AND user_id = $1
                    """,
                    user_id
                )
                user_queued_count = result["count"] if result else 0
            
            # Calculate estimated wait time
            queued_count = total_queued["count"] if total_queued else 0
            estimated_wait = self._calculate_estimated_wait(queued_count)
            
            return {
                "current_job": self.current_job_id,
                "status": self.status.value,
                "queued_count": queued_count,
                "user_queued_count": user_queued_count,
                "estimated_wait_time_seconds": estimated_wait,
                "stats": {
                    "total_processed": self.stats["total_processed"],
                    "total_failed": self.stats["total_failed"],
                    "average_duration_seconds": int(self.stats["average_duration"])
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting queue status: {e}", exc_info=True)
            return {
                "current_job": self.current_job_id,
                "status": "error",
                "queued_count": 0,
                "user_queued_count": 0,
                "estimated_wait_time_seconds": 0
            }
    
    async def _get_next_queued_blog(self) -> Optional[Dict[str, Any]]:
        """Get the oldest queued blog from database"""
        try:
            blog = await database_service.fetchrow(
                """
                SELECT id, user_id, topic, instructions
                FROM blogs
                WHERE status = 'QUEUED'
                ORDER BY created_at ASC
                LIMIT 1
                """
            )
            return blog
        except Exception as e:
            logger.error(f"Error fetching next queued blog: {e}", exc_info=True)
            return None
    
    async def _get_queue_position(self, task_id: str) -> int:
        """
        Get the position of a task in the queue.
        
        Args:
            task_id: Task identifier
        
        Returns:
            Queue position (1-indexed, 1 = next to process)
        """
        try:
            result = await database_service.fetchrow(
                """
                WITH numbered_queue AS (
                    SELECT 
                        id,
                        ROW_NUMBER() OVER (ORDER BY created_at ASC) as position
                    FROM blogs
                    WHERE status = 'QUEUED'
                )
                SELECT position
                FROM numbered_queue
                WHERE id = $1
                """,
                task_id
            )
            
            return result["position"] if result else 0
            
        except Exception as e:
            logger.error(f"Error getting queue position: {e}", exc_info=True)
            return 0
    
    def _calculate_estimated_wait(self, queued_count: int) -> int:
        """
        Calculate estimated wait time in seconds.
        
        Args:
            queued_count: Number of blogs in queue
        
        Returns:
            Estimated wait time in seconds
        """
        if queued_count == 0:
            return 0
        
        # Use average duration if available, otherwise use default estimate
        avg_duration = self.stats["average_duration"] or 180  # 3 minutes default
        
        # If currently processing, account for remaining time
        if self.current_job_id and self.stats["current_job_started_at"]:
            started = datetime.fromisoformat(self.stats["current_job_started_at"])
            elapsed = (datetime.utcnow() - started).total_seconds()
            remaining = max(0, avg_duration - elapsed)
            
            # Wait time = remaining time + (queued_count * avg_duration)
            return int(remaining + (queued_count * avg_duration))
        
        # No current job, just multiply queue count by average
        return int(queued_count * avg_duration)
    
    async def _recover_stuck_jobs(self):
        """
        Recover stuck IN_PROGRESS jobs on startup.
        Resets abandoned jobs back to QUEUED status so they can be retried.
        """
        try:
            result = await database_service.execute(
                """
                UPDATE blogs
                SET status = 'QUEUED',
                    updated_at = CURRENT_TIMESTAMP
                WHERE status = 'IN_PROGRESS'
                RETURNING id
                """
            )
            
            if result and result != "UPDATE 0":
                # Extract count from result like "UPDATE 2"
                count = int(result.split()[1]) if len(result.split()) > 1 else 0
                if count > 0:
                    logger.info(f"🔄 Recovered {count} stuck IN_PROGRESS jobs, reset to QUEUED")
            
        except Exception as e:
            logger.error(f"Error recovering stuck jobs: {e}", exc_info=True)


# Global instance
queue_manager = GenerationQueueManager()
