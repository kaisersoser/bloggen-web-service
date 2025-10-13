"""
Resource Cleanup Manager for BlogGen Backend
Manages cleanup of resources when errors occur or operations complete
"""

import asyncio
import logging
from typing import Dict, List, Optional, Protocol, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class CleanupReason(str, Enum):
    """Reasons for resource cleanup"""

    NORMAL = "normal"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    FORCE = "force"


class CleanupResource(Protocol):
    """Protocol for resources that can be cleaned up"""

    async def cleanup(self) -> None:
        """Perform cleanup for this resource"""
        ...


class RedisSubscriptionResource:
    """Cleanup resource for Redis pub/sub subscriptions"""

    def __init__(self, pubsub, channel: str):
        self.pubsub = pubsub
        self.channel = channel
        self.cleanup_called = False

    async def cleanup(self) -> None:
        if self.cleanup_called:
            return

        self.cleanup_called = True
        try:
            await asyncio.wait_for(self.pubsub.unsubscribe(self.channel), timeout=2.0)
            await asyncio.wait_for(self.pubsub.close(), timeout=2.0)
            logger.info(f"🧹 Redis subscription cleaned up: {self.channel}")
        except Exception as e:
            logger.warning(f"Failed to cleanup Redis subscription {self.channel}: {e}")


class CrewAIFlowResource:
    """Cleanup resource for CrewAI flows"""

    def __init__(self, flow, task_id: str):
        self.flow = flow
        self.task_id = task_id
        self.cleanup_called = False

    async def cleanup(self) -> None:
        if self.cleanup_called:
            return

        self.cleanup_called = True
        try:
            # Attempt to cancel/stop the flow if it has such methods
            if hasattr(self.flow, "cancel"):
                await self.flow.cancel()
            elif hasattr(self.flow, "stop"):
                await self.flow.stop()

            logger.info(f"🧹 CrewAI flow cleaned up: {self.task_id}")
        except Exception as e:
            logger.warning(f"Failed to cleanup CrewAI flow {self.task_id}: {e}")


class DatabaseTransactionResource:
    """Cleanup resource for database transactions"""

    def __init__(self, connection, task_id: str):
        self.connection = connection
        self.task_id = task_id
        self.cleanup_called = False

    async def cleanup(self) -> None:
        if self.cleanup_called:
            return

        self.cleanup_called = True
        try:
            # Rollback any uncommitted transactions
            if hasattr(self.connection, "rollback"):
                await self.connection.rollback()

            # Close the connection
            if hasattr(self.connection, "close"):
                await self.connection.close()

            logger.info(f"🧹 Database transaction cleaned up: {self.task_id}")
        except Exception as e:
            logger.warning(
                f"Failed to cleanup database transaction {self.task_id}: {e}"
            )


class FileUploadResource:
    """Cleanup resource for temporary files and uploads"""

    def __init__(self, file_path: str, task_id: str):
        self.file_path = file_path
        self.task_id = task_id
        self.cleanup_called = False

    async def cleanup(self) -> None:
        if self.cleanup_called:
            return

        self.cleanup_called = True
        try:
            import os

            if os.path.exists(self.file_path):
                os.remove(self.file_path)
                logger.info(f"🧹 Temporary file cleaned up: {self.file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup file {self.file_path}: {e}")


class TaskCleanupContext:
    """Context for tracking resources that need cleanup for a task"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.resources: List[CleanupResource] = []
        self.metadata: Dict[str, Any] = {}
        self.created_at = datetime.utcnow()
        self.cleaned_up = False

    def add_resource(self, resource: CleanupResource) -> None:
        """Add a resource to be cleaned up"""
        if not self.cleaned_up:
            self.resources.append(resource)

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata about the task"""
        self.metadata[key] = value

    async def cleanup(self, reason: CleanupReason = CleanupReason.NORMAL) -> None:
        """Clean up all resources for this task"""
        if self.cleaned_up:
            logger.debug(f"Task {self.task_id} already cleaned up")
            return

        self.cleaned_up = True
        logger.info(f"🧹 Starting cleanup for task {self.task_id} (reason: {reason})")

        # Cleanup all resources
        cleanup_results = []
        for i, resource in enumerate(self.resources):
            try:
                await asyncio.wait_for(resource.cleanup(), timeout=5.0)
                cleanup_results.append(f"Resource {i}: ✅")
            except asyncio.TimeoutError:
                logger.error(
                    f"Timeout cleaning up resource {i} for task {self.task_id}"
                )
                cleanup_results.append(f"Resource {i}: ⏰ Timeout")
            except Exception as e:
                logger.error(
                    f"Failed to cleanup resource {i} for task {self.task_id}: {e}"
                )
                cleanup_results.append(f"Resource {i}: ❌ {str(e)[:50]}")

        logger.info(
            f"🧹 Cleanup completed for task {self.task_id}: {len(cleanup_results)} resources processed"
        )

        # Log cleanup summary if there were issues
        failed_cleanups = [r for r in cleanup_results if not r.endswith("✅")]
        if failed_cleanups:
            logger.warning(
                f"Some cleanups failed for task {self.task_id}: {failed_cleanups}"
            )


class ResourceCleanupManager:
    """Manages cleanup of resources across multiple tasks"""

    def __init__(self):
        self.active_tasks: Dict[str, TaskCleanupContext] = {}
        self._cleanup_lock = asyncio.Lock()

    async def register_task(self, task_id: str) -> TaskCleanupContext:
        """Register a new task for cleanup tracking"""
        async with self._cleanup_lock:
            if task_id not in self.active_tasks:
                context = TaskCleanupContext(task_id)
                self.active_tasks[task_id] = context
                logger.debug(f"📝 Registered task for cleanup: {task_id}")
                return context
            return self.active_tasks[task_id]

    async def add_resource(self, task_id: str, resource: CleanupResource) -> None:
        """Add a resource to be cleaned up for a task"""
        async with self._cleanup_lock:
            if task_id in self.active_tasks:
                self.active_tasks[task_id].add_resource(resource)
                logger.debug(f"📝 Added resource to task {task_id}")

    async def cleanup_task(
        self, task_id: str, reason: CleanupReason = CleanupReason.NORMAL
    ) -> None:
        """Clean up all resources for a specific task"""
        async with self._cleanup_lock:
            context = self.active_tasks.pop(task_id, None)

        if context:
            await context.cleanup(reason)
        else:
            logger.debug(f"No cleanup context found for task {task_id}")

    async def cleanup_all_tasks(
        self, reason: CleanupReason = CleanupReason.FORCE
    ) -> None:
        """Emergency cleanup of all active tasks"""
        logger.warning(f"🚨 Emergency cleanup of all tasks (reason: {reason})")

        # Get all tasks to cleanup
        async with self._cleanup_lock:
            tasks_to_cleanup = list(self.active_tasks.items())
            self.active_tasks.clear()

        # Cleanup all tasks concurrently
        cleanup_tasks = [
            context.cleanup(reason) for task_id, context in tasks_to_cleanup
        ]

        if cleanup_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*cleanup_tasks, return_exceptions=True), timeout=30.0
                )
                logger.info(
                    f"🧹 Emergency cleanup completed: {len(cleanup_tasks)} tasks"
                )
            except asyncio.TimeoutError:
                logger.error("Emergency cleanup timed out after 30 seconds")

    async def get_active_task_count(self) -> int:
        """Get the number of active tasks"""
        async with self._cleanup_lock:
            return len(self.active_tasks)

    async def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific task"""
        async with self._cleanup_lock:
            context = self.active_tasks.get(task_id)
            if context:
                return {
                    "task_id": context.task_id,
                    "created_at": context.created_at.isoformat(),
                    "resource_count": len(context.resources),
                    "metadata": context.metadata,
                    "cleaned_up": context.cleaned_up,
                }
            return None


# Global cleanup manager instance
cleanup_manager = ResourceCleanupManager()


# Convenience functions for common cleanup operations
async def register_redis_subscription(task_id: str, pubsub, channel: str) -> None:
    """Register a Redis subscription for cleanup"""
    resource = RedisSubscriptionResource(pubsub, channel)
    await cleanup_manager.add_resource(task_id, resource)


async def register_crewai_flow(task_id: str, flow) -> None:
    """Register a CrewAI flow for cleanup"""
    resource = CrewAIFlowResource(flow, task_id)
    await cleanup_manager.add_resource(task_id, resource)


async def register_database_transaction(task_id: str, connection) -> None:
    """Register a database transaction for cleanup"""
    resource = DatabaseTransactionResource(connection, task_id)
    await cleanup_manager.add_resource(task_id, resource)


async def register_temp_file(task_id: str, file_path: str) -> None:
    """Register a temporary file for cleanup"""
    resource = FileUploadResource(file_path, task_id)
    await cleanup_manager.add_resource(task_id, resource)
