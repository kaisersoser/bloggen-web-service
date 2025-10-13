"""
Asynchronous S3 Image Cleanup Queue System

This module provides a background queue system for cleaning up S3 images
when blogs are deleted, with retry mechanisms and proper error handling.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class CleanupStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class CleanupTask:
    """Represents an S3 cleanup task"""

    blog_id: str
    user_id: str
    content: Optional[str] = None
    hero_image_url: Optional[str] = None
    status: CleanupStatus = CleanupStatus.PENDING
    attempts: int = 0
    max_attempts: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    last_attempt: Optional[datetime] = None
    error_message: Optional[str] = None
    successful_deletions: int = 0
    failed_urls: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage"""
        return {
            "blog_id": self.blog_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "created_at": self.created_at.isoformat(),
            "last_attempt": (
                self.last_attempt.isoformat() if self.last_attempt else None
            ),
            "error_message": self.error_message,
            "successful_deletions": self.successful_deletions,
            "failed_urls": self.failed_urls,
        }


class S3CleanupQueue:
    """
    Asynchronous queue system for S3 image cleanup with retry mechanism
    """

    def __init__(self, max_concurrent_tasks: int = 5):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.active_tasks: Dict[str, CleanupTask] = {}
        self.completed_tasks: Dict[str, CleanupTask] = {}
        self.max_concurrent_tasks = max_concurrent_tasks
        self.running = False
        self.worker_tasks: List[asyncio.Task] = []

    async def start(self):
        """Start the cleanup queue workers"""
        if self.running:
            logger.warning("S3 cleanup queue is already running")
            return

        self.running = True
        logger.info(
            f"Starting S3 cleanup queue with {self.max_concurrent_tasks} workers"
        )

        # Start worker tasks
        for i in range(self.max_concurrent_tasks):
            task = asyncio.create_task(self._worker(f"worker-{i}"))
            self.worker_tasks.append(task)

    async def stop(self):
        """Stop the cleanup queue workers"""
        if not self.running:
            return

        logger.info("Stopping S3 cleanup queue...")
        self.running = False

        # Cancel all worker tasks
        for task in self.worker_tasks:
            task.cancel()

        # Wait for workers to complete
        await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        self.worker_tasks.clear()

        logger.info("S3 cleanup queue stopped")

    async def enqueue_cleanup(
        self,
        blog_id: str,
        user_id: str,
        content: Optional[str] = None,
        hero_image_url: Optional[str] = None,
    ) -> CleanupTask:
        """
        Enqueue a new S3 cleanup task

        Args:
            blog_id: Blog identifier
            user_id: User identifier for audit
            content: Blog content to scan for S3 URLs
            hero_image_url: Hero image URL to delete

        Returns:
            CleanupTask: The created cleanup task
        """
        cleanup_task = CleanupTask(
            blog_id=blog_id,
            user_id=user_id,
            content=content,
            hero_image_url=hero_image_url,
        )

        # Add to active tasks tracking
        self.active_tasks[blog_id] = cleanup_task

        # Enqueue the task
        await self.queue.put(cleanup_task)

        logger.info(f"Enqueued S3 cleanup for blog {blog_id}")
        return cleanup_task

    async def get_task_status(self, blog_id: str) -> Optional[CleanupTask]:
        """Get the status of a cleanup task"""
        # Check active tasks first
        if blog_id in self.active_tasks:
            return self.active_tasks[blog_id]

        # Check completed tasks
        if blog_id in self.completed_tasks:
            return self.completed_tasks[blog_id]

        return None

    async def _worker(self, worker_name: str):
        """Worker coroutine that processes cleanup tasks"""
        logger.info(f"S3 cleanup worker {worker_name} started")

        while self.running:
            try:
                # Get next task from queue (wait up to 1 second)
                try:
                    task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                # Process the cleanup task
                await self._process_cleanup_task(task, worker_name)

                # Mark queue task as done
                self.queue.task_done()

            except asyncio.CancelledError:
                logger.info(f"S3 cleanup worker {worker_name} cancelled")
                break
            except Exception as e:
                logger.error(f"S3 cleanup worker {worker_name} error: {e}")
                await asyncio.sleep(1)  # Brief pause on error

        logger.info(f"S3 cleanup worker {worker_name} stopped")

    async def _process_cleanup_task(self, task: CleanupTask, worker_name: str):
        """Process a single cleanup task with retry logic"""
        task.last_attempt = datetime.now()
        task.attempts += 1
        task.status = CleanupStatus.IN_PROGRESS

        logger.info(
            f"Worker {worker_name} processing cleanup for blog {task.blog_id} (attempt {task.attempts}/{task.max_attempts})"
        )

        try:
            # Import here to avoid circular imports
            from .s3_storage import get_s3_storage

            s3_storage = get_s3_storage()

            # Perform the S3 cleanup
            successful_deletions, failed_urls = s3_storage.delete_blog_images(
                blog_id=task.blog_id,
                content=task.content,
                hero_image_url=task.hero_image_url,
            )

            task.successful_deletions = successful_deletions
            task.failed_urls = failed_urls

            if failed_urls and task.attempts < task.max_attempts:
                # Some failures but we can retry
                task.status = CleanupStatus.RETRY
                task.error_message = (
                    f"Partial failure: {len(failed_urls)} images failed to delete"
                )

                # Re-enqueue for retry with exponential backoff
                retry_delay = min(60 * (2 ** (task.attempts - 1)), 300)  # Max 5 minutes
                logger.warning(
                    f"Blog {task.blog_id} cleanup partial failure, retrying in {retry_delay}s"
                )

                await asyncio.sleep(retry_delay)
                await self.queue.put(task)
                return

            elif failed_urls:
                # Max attempts reached
                task.status = CleanupStatus.FAILED
                task.error_message = (
                    f"Max attempts reached. {len(failed_urls)} images failed to delete"
                )
                logger.error(
                    f"Blog {task.blog_id} cleanup failed after {task.attempts} attempts"
                )
            else:
                # Complete success
                task.status = CleanupStatus.COMPLETED
                task.error_message = None
                logger.info(
                    f"Blog {task.blog_id} cleanup completed successfully: {successful_deletions} images deleted"
                )

            # Move to completed tasks and track metrics
            await self._complete_task(task)

        except Exception as e:
            task.error_message = str(e)

            if task.attempts < task.max_attempts:
                # Retry on exception
                task.status = CleanupStatus.RETRY
                retry_delay = min(60 * (2 ** (task.attempts - 1)), 300)
                logger.warning(
                    f"Blog {task.blog_id} cleanup error, retrying in {retry_delay}s: {e}"
                )

                await asyncio.sleep(retry_delay)
                await self.queue.put(task)
            else:
                # Max attempts reached
                task.status = CleanupStatus.FAILED
                logger.error(
                    f"Blog {task.blog_id} cleanup failed permanently after {task.attempts} attempts: {e}"
                )
                await self._complete_task(task)

    async def _complete_task(self, task: CleanupTask):
        """Move task to completed status and log metrics"""
        # Remove from active tasks
        if task.blog_id in self.active_tasks:
            del self.active_tasks[task.blog_id]

        # Add to completed tasks (keep last 1000 for monitoring)
        self.completed_tasks[task.blog_id] = task
        if len(self.completed_tasks) > 1000:
            # Remove oldest completed task
            oldest_blog_id = next(iter(self.completed_tasks))
            del self.completed_tasks[oldest_blog_id]

        # Log completion metrics
        logger.info(f"S3 cleanup task completed: {task.to_dict()}")

        # TODO: Integrate with audit system for cost tracking
        await self._track_cleanup_metrics(task)

    async def _track_cleanup_metrics(self, task: CleanupTask):
        """Track cleanup metrics in audit system"""
        try:
            # Estimate storage cost savings (approximate calculation)
            # Average image size: ~200KB, S3 storage cost: ~$0.023/GB/month
            estimated_size_gb = (
                task.successful_deletions * 0.0002
            )  # 200KB per image in GB
            monthly_savings = estimated_size_gb * 0.023

            # Determine status for tracking
            if task.status == CleanupStatus.COMPLETED:
                status = "success"
            elif task.status == CleanupStatus.FAILED:
                status = "failed"
            else:
                status = "partial"

            # Track in audit system using a storage cleanup audit session
            try:
                from .audit_tracker import EnhancedDatabaseAuditTracker

                # Create a dedicated audit session for storage cleanup
                async with EnhancedDatabaseAuditTracker(
                    "storage_cleanup", user_id=task.user_id, blog_id=task.blog_id
                ) as tracker:
                    tracker.track_storage_cleanup(
                        blog_id=task.blog_id,
                        images_deleted=task.successful_deletions,
                        estimated_storage_gb=estimated_size_gb,
                        monthly_savings=monthly_savings,
                        status=status,
                    )

            except Exception as audit_error:
                logger.error(f"Failed to track cleanup in audit system: {audit_error}")

            # Fallback logging
            logger.info(
                f"Estimated storage savings for blog {task.blog_id}: "
                f"{task.successful_deletions} images, ~{estimated_size_gb:.4f}GB, "
                f"~${monthly_savings:.6f}/month, status={status}"
            )

        except Exception as e:
            logger.error(
                f"Failed to track cleanup metrics for blog {task.blog_id}: {e}"
            )

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get current queue statistics"""
        pending_count = self.queue.qsize()
        active_count = len(self.active_tasks)
        completed_count = len(self.completed_tasks)

        # Count by status in completed tasks
        status_counts = {}
        for task in self.completed_tasks.values():
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "pending": pending_count,
            "active": active_count,
            "completed": completed_count,
            "status_breakdown": status_counts,
            "running": self.running,
            "workers": len(self.worker_tasks),
        }


# Global instance
_cleanup_queue: Optional[S3CleanupQueue] = None


async def get_cleanup_queue() -> S3CleanupQueue:
    """Get or create global S3 cleanup queue instance"""
    global _cleanup_queue
    if _cleanup_queue is None:
        _cleanup_queue = S3CleanupQueue()
        await _cleanup_queue.start()
    return _cleanup_queue


async def cleanup_queue_shutdown():
    """Shutdown the global cleanup queue"""
    global _cleanup_queue
    if _cleanup_queue:
        await _cleanup_queue.stop()
        _cleanup_queue = None
