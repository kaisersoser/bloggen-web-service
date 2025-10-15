"""
Task Manager for database-backed task state management.

Replaces the in-memory active_tasks dictionary with persistent database storage.
Integrates with Redis pub/sub for real-time updates.
Enhanced with immediate SSE message broadcasting for Phase 1 Foundation.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from enum import Enum

# Import enhanced SSE message types for immediate feedback
from core.sse_message_types import create_task_created_message
from core.config import config

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class BlogStatus(str, Enum):
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskManager:
    """Manages task state using database persistence instead of in-memory storage."""

    _connection_pool = None  # Class-level connection pool

    def __init__(self):
        self._status_mapping = {
            TaskStatus.QUEUED: BlogStatus.QUEUED,
            TaskStatus.IN_PROGRESS: BlogStatus.IN_PROGRESS,
            TaskStatus.COMPLETED: BlogStatus.COMPLETED,
            TaskStatus.FAILED: BlogStatus.FAILED,
        }
        self._subscribers: Dict[str, List[Callable]] = {}
        self._redis_manager = None
        self._content_streaming_manager = None
        self._message_buffer = None

        tm_config = config.task_manager
        self._cleanup_interval_seconds = tm_config.cleanup_interval_seconds
        self._stale_incomplete_delta = timedelta(
            minutes=tm_config.stale_incomplete_minutes
        )
        self._stale_completed_delta = timedelta(
            minutes=tm_config.stale_completed_minutes
        )
        self._redis_status_ttl = tm_config.redis_status_ttl_seconds
        self._max_cleanup_batch = max(1, tm_config.max_cleanup_batch)
        self._redis_scan_count = max(1, tm_config.redis_scan_count)

        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_stop_event: Optional[asyncio.Event] = None
        self._cleanup_stats = {
            "cycles": 0,
            "expired_tasks": 0,
            "redis_keys_removed": 0,
            "buffers_pruned": 0,
        }

    def set_redis_manager(self, redis_manager):
        """Set the Redis manager for pub/sub updates."""
        self._redis_manager = redis_manager

    def set_content_streaming_manager(self, content_streaming_manager):
        """Set the content streaming manager for progressive content updates."""
        self._content_streaming_manager = content_streaming_manager

    def set_message_buffer(self, message_buffer):
        """Set the Redis-backed message buffer for cleanup coordination."""
        self._message_buffer = message_buffer

    def configure_cleanup(
        self,
        *,
        cleanup_interval_seconds: Optional[int] = None,
        stale_incomplete_minutes: Optional[int] = None,
        stale_completed_minutes: Optional[int] = None,
        redis_status_ttl_seconds: Optional[int] = None,
        max_cleanup_batch: Optional[int] = None,
        redis_scan_count: Optional[int] = None,
    ) -> None:
        """Adjust cleanup settings at runtime (primarily for testing)."""
        if cleanup_interval_seconds is not None and cleanup_interval_seconds > 0:
            self._cleanup_interval_seconds = cleanup_interval_seconds
        if stale_incomplete_minutes is not None and stale_incomplete_minutes > 0:
            self._stale_incomplete_delta = timedelta(minutes=stale_incomplete_minutes)
        if stale_completed_minutes is not None and stale_completed_minutes > 0:
            self._stale_completed_delta = timedelta(minutes=stale_completed_minutes)
        if redis_status_ttl_seconds is not None and redis_status_ttl_seconds > 0:
            self._redis_status_ttl = redis_status_ttl_seconds
        if max_cleanup_batch is not None and max_cleanup_batch > 0:
            self._max_cleanup_batch = max_cleanup_batch
        if redis_scan_count is not None and redis_scan_count > 0:
            self._redis_scan_count = redis_scan_count

    async def start_cleanup_service(self) -> None:
        """Start background cleanup loop if not already running."""
        if self._cleanup_task and not self._cleanup_task.done():
            return

        if self._cleanup_stop_event is None:
            self._cleanup_stop_event = asyncio.Event()
        else:
            self._cleanup_stop_event.clear()

        loop = asyncio.get_running_loop()
        self._cleanup_task = loop.create_task(
            self._cleanup_loop(), name="task-manager-cleanup"
        )
        logger.info(
            "🧹 TaskManager cleanup service started (interval: %ss, stale incomplete: %s min)",
            self._cleanup_interval_seconds,
            int(self._stale_incomplete_delta.total_seconds() / 60),
        )

    async def stop_cleanup_service(self) -> None:
        """Stop background cleanup loop gracefully."""
        if self._cleanup_stop_event:
            self._cleanup_stop_event.set()

        if self._cleanup_task:
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            finally:
                self._cleanup_task = None

        self._cleanup_stop_event = None
        logger.info("🧹 TaskManager cleanup service stopped")

    async def run_cleanup_cycle(self) -> None:
        """Run a single cleanup cycle (useful for tests)."""
        await self._cleanup_stale_tasks_once()

    async def _cleanup_loop(self) -> None:
        """Background loop that periodically prunes stale resources."""
        try:
            while True:
                await self._cleanup_stale_tasks_once()
                if not self._cleanup_stop_event:
                    break

                try:
                    await asyncio.wait_for(
                        self._cleanup_stop_event.wait(),
                        timeout=self._cleanup_interval_seconds,
                    )
                    break
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            raise

    async def _cleanup_stale_tasks_once(self) -> None:
        """Perform a single pass of cleanup operations."""
        cycle_expired = 0
        cycle_redis = 0
        cycle_buffers = 0

        try:
            cycle_expired = await self._expire_stale_incomplete_tasks()
        except Exception as e:
            # Silently ignore errors during shutdown when pool is closed
            error_msg = str(e).lower()
            if 'pool is closed' in error_msg or 'closed' in error_msg or 'not available' in error_msg:
                logger.debug("Database unavailable during cleanup (likely shutdown)")
            else:
                logger.error(f"Task cleanup failed while expiring incomplete tasks: {e}")

        cycle_expired = int(cycle_expired or 0)

        try:
            cycle_redis = await self._cleanup_redis_status_cache()
            if cycle_redis:
                logger.debug(
                    f"🧹 Removed {cycle_redis} stale Redis status cache entries"
                )
        except Exception as e:
            logger.error(f"Task cleanup failed while pruning Redis cache: {e}")

        cycle_redis = int(cycle_redis or 0)

        try:
            cycle_buffers = await self._cleanup_message_buffers()
        except Exception as e:
            logger.error(f"Task cleanup failed while pruning message buffers: {e}")

        cycle_buffers = int(cycle_buffers or 0)

        self._cleanup_stats["cycles"] += 1
        self._cleanup_stats["expired_tasks"] += cycle_expired
        self._cleanup_stats["redis_keys_removed"] += cycle_redis
        self._cleanup_stats["buffers_pruned"] += cycle_buffers

        logger.debug(
            "🧮 Cleanup cycle stats -> expired=%s redis=%s buffers=%s cumulative=%s",
            cycle_expired,
            cycle_redis,
            cycle_buffers,
            self._cleanup_stats,
        )

    async def _expire_stale_incomplete_tasks(self) -> int:
        """Mark queued or in-progress tasks that exceeded TTL as failed."""
        cutoff = datetime.utcnow() - self._stale_incomplete_delta
        statuses = [BlogStatus.QUEUED.value, BlogStatus.IN_PROGRESS.value]
        expired_task_ids: List[str] = []

        pool = await self._get_db_connection()
        async with pool.acquire() as conn:
            stale_rows = await conn.fetch(
                """
                SELECT id, user_id, status, updated_at
                FROM blogs
                WHERE status = ANY($1::"BlogStatus"[])
                  AND updated_at < $2
                ORDER BY updated_at ASC
                LIMIT $3
                """,
                statuses,
                cutoff,
                self._max_cleanup_batch,
            )

        if not stale_rows:
            return 0

        from core.resource_cleanup import cleanup_manager, CleanupReason

        for row in stale_rows:
            task_id = row["id"]
            try:
                await self.fail_task(task_id, "Task expired due to inactivity")
                expired_task_ids.append(task_id)

                if self._message_buffer:
                    try:
                        await self._message_buffer.stop_buffering(task_id)
                    except Exception as buffer_err:
                        logger.warning(
                            f"Failed to stop buffering for {task_id}: {buffer_err}"
                        )

                try:
                    await cleanup_manager.cleanup_task(task_id, CleanupReason.TIMEOUT)
                except Exception as cleanup_err:
                    logger.debug(
                        f"Cleanup context release failed for {task_id}: {cleanup_err}"
                    )
            except Exception as task_err:
                logger.error(f"Failed to expire stale task {task_id}: {task_err}")

        if expired_task_ids:
            logger.warning(
                "🧹 Marked %d stale task(s) as failed due to TTL: %s",
                len(expired_task_ids),
                ", ".join(expired_task_ids),
            )
        return len(expired_task_ids)

    async def _cleanup_redis_status_cache(self) -> int:
        """Remove expired task_status cache entries."""
        redis_client = getattr(self._redis_manager, "redis_client", None)
        if not redis_client:
            return 0

        keys_to_delete: List[str] = []
        cutoff = datetime.utcnow() - self._stale_completed_delta

        async for key in redis_client.scan_iter(
            match="task_status:*", count=self._redis_scan_count
        ):
            key_str = (
                key.decode("utf-8") if isinstance(key, (bytes, bytearray)) else str(key)
            )
            status_json = await redis_client.get(key)
            if not status_json:
                continue

            if isinstance(status_json, bytes):
                status_json = status_json.decode("utf-8")

            try:
                status_data = json.loads(status_json)
            except json.JSONDecodeError:
                keys_to_delete.append(key_str)
                if len(keys_to_delete) >= self._max_cleanup_batch:
                    break
                continue

            updated_at_raw = status_data.get("updated_at")
            if not updated_at_raw:
                continue

            try:
                updated_at = datetime.fromisoformat(updated_at_raw)
            except ValueError:
                continue

            if updated_at < cutoff:
                keys_to_delete.append(key_str)
                if len(keys_to_delete) >= self._max_cleanup_batch:
                    break

        if keys_to_delete:
            await redis_client.delete(*keys_to_delete)

        return len(keys_to_delete)

    async def _cleanup_message_buffers(self) -> int:
        """Prune any in-memory/Redis message buffers that expired."""
        if not self._message_buffer:
            return 0

        cleaned = await self._message_buffer.cleanup_expired_buffers()
        if cleaned:
            logger.debug(f"🧹 Cleaned up {cleaned} expired message buffers")
        return cleaned

    async def warm_cache_from_database(self) -> Dict[str, int]:
        """Populate Redis task_status cache for active tasks on startup."""
        redis_manager = self._redis_manager
        if not redis_manager or not getattr(redis_manager, "redis_client", None):
            logger.info("Redis manager unavailable; skipping task cache warmup")
            return {"total": 0, "queued": 0, "in_progress": 0}

        pool = await self._get_db_connection()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, topic, instructions, status, progress, current_step,
                       error, content, hero_image_url, created_at, updated_at
                FROM blogs
                WHERE status = ANY($1::"BlogStatus"[])
                ORDER BY updated_at DESC
                LIMIT $2
                """,
                [BlogStatus.QUEUED.value, BlogStatus.IN_PROGRESS.value],
                self._max_cleanup_batch * 5,
            )

        restored_counts = {"total": 0, "queued": 0, "in_progress": 0}

        for row in rows:
            task_state = dict(row)
            try:
                await redis_manager.cache_task_status(
                    task_state["id"], task_state, ttl=self._redis_status_ttl
                )
                restored_counts["total"] += 1
                status = task_state.get("status", "").upper()
                if status == BlogStatus.QUEUED.value:
                    restored_counts["queued"] += 1
                elif status == BlogStatus.IN_PROGRESS.value:
                    restored_counts["in_progress"] += 1
            except Exception as err:
                logger.error(
                    f"Failed to warm cache for task {task_state.get('id')}: {err}"
                )

        if restored_counts["total"]:
            logger.info(
                "🔥 Restored %s active task caches (queued=%s, in_progress=%s)",
                restored_counts["total"],
                restored_counts["queued"],
                restored_counts["in_progress"],
            )
        else:
            logger.info("No active tasks detected for cache warmup")

        return restored_counts

    def get_cleanup_stats(self) -> Dict[str, int]:
        """Return aggregate cleanup statistics (cycles, expired tasks, redis prunes, buffer prunes)."""
        return dict(self._cleanup_stats)

    def reset_cleanup_stats(self) -> None:
        """Reset cleanup statistics (primarily for testing/monitoring reset)."""
        for key in self._cleanup_stats:
            self._cleanup_stats[key] = 0

    async def _broadcast_task_update(self, task_id: str, task_data: Dict[str, Any]):
        """Broadcast task update via Redis pub/sub."""
        # Redis pub/sub broadcast
        if self._redis_manager:
            try:
                # Import here to avoid circular imports
                from core.redis_manager import TaskUpdateMessage

                # Prepare Redis message
                redis_message = TaskUpdateMessage(
                    task_id=task_id,
                    user_id=task_data.get("user_id", ""),
                    phase=task_data.get("current_step", ""),
                    progress=task_data.get("progress", 0),
                    details=task_data.get("details", ""),
                    timestamp=datetime.utcnow().isoformat(),
                    status=task_data.get("status", "").lower(),
                )

                # Publish to Redis
                await self._redis_manager.publish_task_update(redis_message)

                # Cache task status in Redis
                await self._redis_manager.cache_task_status(
                    task_id, task_data, ttl=self._redis_status_ttl
                )

                logger.debug(f"Published Redis update for task {task_id}")

            except Exception as e:
                logger.error(f"Failed to publish Redis update: {e}")

        # Content streaming broadcast (Phase 4 enhancement)
        if self._content_streaming_manager:
            try:
                # Get content preview for enhanced updates
                content_preview = (
                    await self._content_streaming_manager.get_content_preview(task_id)
                )

                if content_preview:
                    # Content streaming handled by Redis pub/sub instead of WebSocket
                    logger.debug(
                        f"Content streaming update available for task {task_id}"
                    )

            except Exception as e:
                logger.error(f"Failed to broadcast content streaming update: {e}")

    async def _send_immediate_message(self, task_id: str, message):
        """Send immediate SSE message for instant user feedback (Phase 1 Foundation)."""
        try:
            if self._redis_manager:
                # Convert SSE message to dict for Redis broadcast
                message_data = message.to_dict()

                # Publish immediate message to SSE channel
                await self._redis_manager.publish_immediate_message(
                    task_id, message_data
                )

                logger.debug(
                    f"Sent immediate message for task {task_id}: {message.message_type}"
                )

        except Exception as e:
            logger.error(f"Failed to send immediate message for task {task_id}: {e}")

    async def _get_db_connection(self):
        """
        Get database connection using centralized DatabaseService.
        
        Phase 3.1 Migration: Now uses shared connection pool instead of
        creating a separate task_manager-specific pool.
        """
        from core.database_service import database_service

        try:
            # Check if database service is still active
            if not database_service.is_initialized():
                logger.debug("DatabaseService not initialized - operations disabled")
                raise RuntimeError("DatabaseService not initialized")
            
            # Use centralized database service
            pool = await database_service.ensure_pool()
            logger.debug("✅ Task manager using centralized database pool")
            return pool

        except RuntimeError as e:
            # Handle both "not initialized" and "pool is closed" errors gracefully
            error_msg = str(e).lower()
            if 'closed' in error_msg:
                logger.debug("DatabaseService pool closed - operations disabled")
            else:
                logger.debug(f"DatabaseService not ready: {e}")
            raise Exception("Database connection not available") from e
        except Exception as e:
            # Log more details about connection pool exhaustion
            logger.error(f"❌ Failed to get database connection: {e}")
            if hasattr(database_service, '_pool') and database_service._pool:
                try:
                    pool_size = database_service._pool.get_size()
                    pool_free = database_service._pool.get_idle_size()
                    logger.error(f"   Pool stats: size={pool_size}, free={pool_free}, in_use={pool_size - pool_free}")
                except Exception:
                    pass
            raise Exception(f"Failed to get database connection: {e}") from e

    async def create_task(
        self, task_id: str, user_id: str, topic: str, instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new task in the database."""
        try:
            pool = await self._get_db_connection()
            async with pool.acquire() as conn:
                # Check if blog already exists, if not create it
                existing_blog = await conn.fetchrow(
                    "SELECT id FROM blogs WHERE id = $1", task_id
                )

                if not existing_blog:
                    # Create new blog entry
                    await conn.execute(
                        """
                        INSERT INTO blogs (id, user_id, topic, instructions, status, progress, current_step, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                        task_id,
                        user_id,
                        topic,
                        instructions,
                        BlogStatus.QUEUED.value,
                        0,
                        "Queued for processing",
                        datetime.utcnow(),
                        datetime.utcnow(),
                    )
                    logger.info(f"✅ Created new blog entry for task {task_id}")
                else:
                    # Update existing blog entry with initial task state
                    await conn.execute(
                        """
                        UPDATE blogs
                        SET status = $1, progress = $2, current_step = $3, updated_at = $4
                        WHERE id = $5 AND user_id = $6
                    """,
                        BlogStatus.QUEUED.value,
                        0,
                        "Queued for processing",
                        datetime.utcnow(),
                        task_id,
                        user_id,
                    )
                    logger.info(f"✅ Updated existing blog entry for task {task_id}")

                # Return task state
                task_state = {
                    "id": task_id,
                    "user_id": user_id,
                    "topic": topic,
                    "instructions": instructions,
                    "status": TaskStatus.QUEUED,
                    "progress": 0,
                    "current_step": "Queued for processing",
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "error": None,
                    "result": None,
                    "hero_image_url": None,
                }

                # Send immediate task created message for instant feedback
                await self._send_immediate_message(
                    task_id,
                    create_task_created_message(
                        task_id=task_id,
                        message=f"Blog generation task created successfully: {topic[:50] if topic else 'Auto-generating topic'}...",
                    ),
                )

                logger.info(f"✅ Created task {task_id} for user {user_id}")
                return task_state

        except Exception as e:
            logger.error(f"❌ Failed to create task {task_id}: {e}")
            raise

    async def update_task(self, task_id: str, **updates) -> Optional[Dict[str, Any]]:
        """Update task state in the database."""
        try:
            pool = await self._get_db_connection()

            # Map task status to blog status
            if "status" in updates:
                updates["status"] = self._status_mapping.get(
                    updates["status"], updates["status"]
                )

            # Build dynamic update query
            set_clauses = []
            values = []
            param_count = 1

            for key, value in updates.items():
                if key in [
                    "status",
                    "progress",
                    "current_step",
                    "error",
                    "content",
                    "hero_image_url",
                ]:
                    db_key = "current_step" if key == "current_step" else key
                    if key == "hero_image_url":
                        db_key = "hero_image_url"

                    set_clauses.append(f"{db_key} = ${param_count}")
                    values.append(value)
                    param_count += 1

            if not set_clauses:
                logger.warning(f"No valid updates provided for task {task_id}")
                return await self.get_task(task_id)

            # Always update the updated_at timestamp
            set_clauses.append(f"updated_at = ${param_count}")
            values.append(datetime.utcnow())
            param_count += 1

            # Add task_id for WHERE clause
            values.append(task_id)

            query = f"""
                UPDATE blogs
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count}
                RETURNING id, user_id, topic, instructions, status, progress, current_step,
                         error, content, hero_image_url, created_at, updated_at, completed_at
            """

            async with pool.acquire() as conn:
                result = await conn.fetchrow(query, *values)

                if not result:
                    logger.warning(f"Task {task_id} not found for update")
                    return None

                task_state = dict(result)

                # Notify subscribers
                await self._notify_subscribers(task_id, task_state)

                # Broadcast task update
                await self._broadcast_task_update(task_id, task_state)

                logger.info(f"✅ Updated task {task_id}: {updates}")
                return task_state

        except Exception as e:
            logger.error(f"❌ Failed to update task {task_id}: {e}")
            raise

    def update_task_redis_only(self, task_id: str, status_data: Dict[str, Any]) -> None:
        """
        Thread-safe Redis-only update for status updates from CrewAI Flow threads.
        Uses sync Redis client to avoid asyncio event loop conflicts.
        """
        try:
            import redis
            import os

            # Debug logging
            logger.info(f"🔍 DEBUG: update_task_redis_only called for task {task_id}")
            logger.info(f"🔍 DEBUG: status_data keys: {list(status_data.keys())}")
            logger.info(
                f"🔍 DEBUG: message_type: {status_data.get('message_type', 'unknown')}"
            )

            # Extract update information from status data
            message = status_data.get("message", "Processing...")
            progress = status_data.get("progress", 0.0)
            message_type = status_data.get("message_type", "status")

            # Use sync Redis client for thread-safe operations
            try:
                # Create sync Redis connection for thread-safe publishing
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                sync_redis = redis.from_url(redis_url, decode_responses=True)

                # Create message for immediate SSE broadcasting - preserve original message type
                immediate_message = {
                    "message_type": message_type,  # Preserve the original message type (agentthinking, toolcall, etc.)
                    "task_id": task_id,
                    "status": "in_progress",
                    "message": message,
                    "progress": progress,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                # Add enhanced message fields if present
                for field in [
                    "agent_name",
                    "thought",
                    "tool_name",
                    "input_summary",
                    "content_type",
                    "finding",
                    "source",
                ]:
                    if field in status_data:
                        immediate_message[field] = status_data[field]

                # Check if message buffering is active for this task
                buffer_key = f"message_buffer:{task_id}"
                try:
                    buffer_active = sync_redis.exists(buffer_key)

                    if buffer_active:
                        # Message buffering is active - store message in buffer instead of publishing
                        from core.message_buffer import BufferedMessage

                        # Create BufferedMessage
                        buffered_msg = BufferedMessage(
                            task_id=task_id,
                            message_data=immediate_message,
                            channel=f"task_updates:{task_id}",
                            timestamp=datetime.utcnow().isoformat(),
                            message_type=message_type,
                        )

                        # Add to buffer in Redis
                        buffer_key = f"message_buffer:{task_id}"
                        existing_data_raw = sync_redis.get(buffer_key)
                        if existing_data_raw:
                            buffer_data = json.loads(str(existing_data_raw))
                        else:
                            buffer_data = {"messages": []}

                        buffer_data["messages"].append(buffered_msg.to_dict())
                        sync_redis.setex(
                            buffer_key, 1800, json.dumps(buffer_data)
                        )  # 30 min TTL

                        logger.info(
                            f"📦 BUFFERED: {message_type} message for task {task_id} (buffer active)"
                        )
                        return  # Don't publish to Redis, message is buffered
                    else:
                        logger.info(
                            f"📡 DIRECT: No buffer active for task {task_id}, publishing directly"
                        )
                except Exception as buffer_err:
                    logger.warning(
                        f"⚠️ Buffer check failed for task {task_id}, proceeding with direct publish: {buffer_err}"
                    )

                # Publish to task-specific channel for SSE (if not buffered)
                task_channel = f"task_updates:{task_id}"
                sync_redis.publish(task_channel, json.dumps(immediate_message))

                # Cache task status in Redis for SSE recovery (keep numbers as numbers)
                status_key = f"task_status:{task_id}"
                status_data = {
                    "current_step": message,
                    "progress": progress,  # Keep as number, not string
                    "status": "IN_PROGRESS",
                    "updated_at": datetime.utcnow().isoformat(),
                    "message_type": message_type,
                }

                # Store as JSON string to match redis_manager.py pattern
                sync_redis.setex(
                    status_key, self._redis_status_ttl, json.dumps(status_data)
                )

                logger.info(
                    f"✅ Redis-only update for task {task_id}: {message} ({progress:.1f}%)"
                )

            except Exception as redis_error:
                logger.error(f"Redis update failed for task {task_id}: {redis_error}")
                # Graceful degradation - continue without Redis updates
                logger.info(
                    f"📊 {task_id}: {message} ({progress:.1f}%) - Redis unavailable, continuing..."
                )

        except Exception as e:
            logger.error(f"❌ Failed to send Redis-only update for task {task_id}: {e}")

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task state from the database."""
        try:
            pool = await self._get_db_connection()

            async with pool.acquire() as conn:
                result = await conn.fetchrow(
                    """
                    SELECT id, user_id, topic, instructions, status, progress, current_step,
                           error, content, hero_image_url, created_at, updated_at, completed_at
                    FROM blogs
                    WHERE id = $1
                """,
                    task_id,
                )

                if not result:
                    return None

                return dict(result)

        except Exception as e:
            logger.error(f"❌ Failed to get task {task_id}: {e}")
            raise

    async def get_user_tasks(
        self, user_id: str, status: Optional[TaskStatus] = None
    ) -> List[Dict[str, Any]]:
        """Get all tasks for a user, optionally filtered by status."""
        try:
            pool = await self._get_db_connection()

            query = """
                SELECT id, user_id, topic, instructions, status, progress, current_step,
                       error, content, hero_image_url, created_at, updated_at, completed_at
                FROM blogs
                WHERE user_id = $1
            """
            values = [user_id]

            if status:
                blog_status = self._status_mapping.get(status)
                if blog_status:
                    query += " AND status = $2"
                    values.append(blog_status.value)

            query += " ORDER BY created_at DESC"

            async with pool.acquire() as conn:
                results = await conn.fetch(query, *values)
                return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"❌ Failed to get tasks for user {user_id}: {e}")
            raise

    async def complete_task(
        self, task_id: str, content: str, hero_image_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Mark task as completed with final content."""

        # THEORY 3 TEST: Track multiple completion calls
        import traceback

        call_stack = traceback.format_stack()
        caller_info = [line for line in call_stack[-3:-1]]  # Get calling context

        logger.warning(
            f"🚨 COMPLETION CALL #{hash(call_stack[-2]) % 1000} for task {task_id}"
        )
        logger.warning(f"   📞 Called from: {caller_info}")
        logger.warning(f"   📊 Content length: {len(content) if content else 0}")
        logger.warning(
            f"   📋 Content preview: {content[:100] if content else '❌ EMPTY'}..."
        )

        # CRITICAL DEBUG: Enhanced logging for content tracking
        logger.info("🔍 TASK_MANAGER complete_task received:")
        logger.info(f"   task_id: {task_id}")
        logger.info(f"   content length: {len(content) if content else 0}")
        logger.info(f"   content type: {type(content)}")
        logger.info(f"   content is_empty: {not content or not content.strip()}")
        logger.info(
            f"   content preview: {content[:300] if content else 'EMPTY CONTENT RECEIVED'}..."
        )
        logger.info(f"   hero_image_url: {hero_image_url}")

        # THEORY 3 TEST: Check if task is already completed
        current_task = await self.get_task(task_id)
        if current_task and current_task.get("status") == TaskStatus.COMPLETED:
            logger.error(
                f"🚨 DOUBLE COMPLETION DETECTED! Task {task_id} already completed"
            )
            logger.error(
                f"   Previous completion: {current_task.get('current_step', 'unknown')}"
            )
            logger.error(
                f"   Previous content length: {len(current_task.get('content', '')) if current_task.get('content') else 0}"
            )
            logger.error(f"   New content length: {len(content) if content else 0}")
            logger.error("   This is likely the root cause of '0 words' issue!")
            # Don't return early - let's see what happens with multiple completions

        updates = {
            "status": TaskStatus.COMPLETED,
            "progress": 100,
            "current_step": "Blog generation completed successfully!",
            "content": content,
        }

        if hero_image_url:
            updates["hero_image_url"] = hero_image_url

        # Also set completed_at timestamp
        try:
            pool = await self._get_db_connection()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE blogs
                    SET completed_at = $1
                    WHERE id = $2
                """,
                    datetime.utcnow(),
                    task_id,
                )
        except Exception as e:
            logger.warning(f"Failed to set completed_at for task {task_id}: {e}")

        # Update database first
        task_result = await self.update_task(task_id, **updates)

        # CRITICAL DEBUG: Check why completion message isn't being sent
        logger.info(
            f"🔍 DEBUG complete_task - redis_manager: {self._redis_manager is not None}, task_result: {task_result is not None}"
        )

        # CRITICAL FIX: Send completion message with content via immediate Redis message
        if self._redis_manager and task_result:
            try:
                # Import required modules
                import time
                import json
                import redis

                # ENHANCED COMPLETION PROTOCOL - 2-Phase completion with acknowledgment
                timestamp = time.time()
                sequence_id = int(timestamp * 1000000)  # Microsecond precision

                logger.warning(
                    f"🔍 REDIS SEQUENCE #{sequence_id} - ENHANCED COMPLETION PROTOCOL START:"
                )
                logger.warning(f"   task_id: {task_id}")
                logger.warning(f"   content length: {len(content) if content else 0}")
                logger.warning(
                    f"   content preview: {content[:200] if content else 'NO CONTENT TO SEND'}..."
                )
                logger.warning(f"   timestamp: {timestamp}")

                # Use sync Redis to match the pattern from send_redis_only_update method
                sync_redis = redis.Redis.from_url(
                    self._redis_manager.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                task_channel = f"task_updates:{task_id}"

                # PHASE 1: Send completion_pending message with content
                completion_pending_message = {
                    "message_type": "completion_pending",
                    "task_id": task_id,
                    "message": f"Blog generation completed ({self._count_words(content)} words)",
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "completion_pending",
                    "final_content": content,
                    "word_count": self._count_words(content),
                    "hero_image_url": hero_image_url,
                }

                logger.warning(
                    f"🔍 REDIS SEQUENCE #{sequence_id} - PHASE 1: SENDING COMPLETION_PENDING:"
                )
                logger.warning(
                    f"   completion_pending keys: {list(completion_pending_message.keys())}"
                )
                logger.warning(
                    f"   final_content length: {len(completion_pending_message['final_content']) if completion_pending_message['final_content'] else 0}"
                )

                sync_redis.publish(task_channel, json.dumps(completion_pending_message))
                logger.warning(
                    f"✅ REDIS SEQUENCE #{sequence_id} - PHASE 1: COMPLETION_PENDING PUBLISHED to {task_channel}"
                )

                # PHASE 2: Wait for acknowledgment from frontend
                logger.info(
                    f"⏳ PHASE 2: Waiting for completion acknowledgment for {task_id}"
                )
                ack_received = (
                    await self._redis_manager.wait_for_completion_acknowledgment(
                        task_id, timeout=30
                    )
                )

                # PHASE 3: Send final confirmation based on acknowledgment
                if ack_received:
                    # Send completion_confirmed message
                    confirmation_message = {
                        "message_type": "completion_confirmed",
                        "task_id": task_id,
                        "message": "Blog generation confirmed and delivered",
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "completion_confirmed",
                    }

                    sync_redis.publish(task_channel, json.dumps(confirmation_message))
                    logger.warning(
                        f"✅ REDIS SEQUENCE #{sequence_id} - PHASE 3: COMPLETION_CONFIRMED sent for {task_id}"
                    )

                else:
                    # Send completion_timeout message (fallback)
                    timeout_message = {
                        "message_type": "completion_timeout",
                        "task_id": task_id,
                        "message": "Blog generation completed (delivery confirmed via timeout)",
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "completion_timeout",
                        "final_content": content,  # Resend content as fallback
                        "word_count": self._count_words(content),
                        "hero_image_url": hero_image_url,
                    }

                    sync_redis.publish(task_channel, json.dumps(timeout_message))
                    logger.warning(
                        f"⏰ REDIS SEQUENCE #{sequence_id} - PHASE 3: COMPLETION_TIMEOUT sent for {task_id} (no ack received)"
                    )

                logger.warning(
                    f"🏁 REDIS SEQUENCE #{sequence_id} - ENHANCED COMPLETION PROTOCOL COMPLETE for {task_id}"
                )

            except Exception as e:
                logger.error(
                    f"❌ Failed to send completion message for task {task_id}: {e}"
                )
                import traceback

                logger.error(
                    f"❌ Completion message traceback: {traceback.format_exc()}"
                )
        else:
            logger.error(
                f"❌ Cannot send completion message - redis_manager: {self._redis_manager is not None}, task_result: {task_result is not None}"
            )

        return task_result

    async def fail_task(
        self, task_id: str, error_message: str
    ) -> Optional[Dict[str, Any]]:
        """Mark task as failed with error message."""
        return await self.update_task(
            task_id,
            status=TaskStatus.FAILED,
            current_step=f"Error: {error_message}",
            error=error_message,
        )

    async def delete_task(self, task_id: str, user_id: str) -> bool:
        """Delete a task/blog from the database with S3 image cleanup."""
        try:
            pool = await self._get_db_connection()

            async with pool.acquire() as conn:
                # First check if the task exists and belongs to the user, and get image data
                existing_task = await conn.fetchrow(
                    """
                    SELECT id, user_id, status, content, hero_image_url FROM blogs
                    WHERE id = $1 AND user_id = $2
                """,
                    task_id,
                    user_id,
                )

                if not existing_task:
                    logger.warning(
                        f"Task {task_id} not found or doesn't belong to user {user_id}"
                    )
                    return False

                # Enqueue S3 cleanup asynchronously (non-blocking)
                try:
                    from .s3_cleanup_queue import get_cleanup_queue

                    cleanup_queue = await get_cleanup_queue()
                    await cleanup_queue.enqueue_cleanup(
                        blog_id=task_id,
                        user_id=user_id,
                        content=existing_task["content"],
                        hero_image_url=existing_task["hero_image_url"],
                    )
                    logger.info(f"Enqueued S3 cleanup for blog {task_id}")

                except Exception as cleanup_error:
                    # S3 cleanup failure should not prevent blog deletion
                    logger.error(
                        f"Failed to enqueue S3 cleanup for blog {task_id}: {cleanup_error}"
                    )

                # Delete the task from database (proceeds regardless of S3 cleanup status)
                result = await conn.execute(
                    """
                    DELETE FROM blogs
                    WHERE id = $1 AND user_id = $2
                """,
                    task_id,
                    user_id,
                )

                if result == "DELETE 1":
                    logger.info(
                        f"✅ Deleted task {task_id} for user {user_id} (S3 cleanup in progress)"
                    )

                    # Notify subscribers about deletion
                    await self._notify_subscribers(task_id, {"deleted": True})

                    # Broadcast task update about deletion
                    await self._broadcast_task_update(task_id, {"deleted": True})

                    return True
                else:
                    logger.warning(f"Failed to delete task {task_id}")
                    return False

        except Exception as e:
            logger.error(f"❌ Failed to delete task {task_id}: {e}")
            return False

    def subscribe(self, task_id: str, callback: Callable):
        """Subscribe to task updates for real-time notifications."""
        if task_id not in self._subscribers:
            self._subscribers[task_id] = []
        self._subscribers[task_id].append(callback)

    def unsubscribe(self, task_id: str, callback: Callable):
        """Unsubscribe from task updates."""
        if task_id in self._subscribers:
            try:
                self._subscribers[task_id].remove(callback)
                if not self._subscribers[task_id]:
                    del self._subscribers[task_id]
            except ValueError:
                pass

    async def _notify_subscribers(self, task_id: str, task_state: Dict[str, Any]):
        """Notify all subscribers of task updates."""
        if task_id in self._subscribers:
            for callback in self._subscribers[task_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(task_id, task_state)
                    else:
                        callback(task_id, task_state)
                except Exception as e:
                    logger.error(f"Error notifying subscriber for task {task_id}: {e}")

    # Phase 4: Content Streaming Methods

    async def stream_research_finding(self, task_id: str, finding: str):
        """Stream a research finding for progressive content updates."""
        if self._content_streaming_manager:
            try:
                await self._content_streaming_manager.stream_research_finding(
                    task_id, finding
                )
                logger.debug(f"Streamed research finding for task {task_id}")
            except Exception as e:
                logger.error(f"Failed to stream research finding: {e}")

    async def stream_content_paragraph(self, task_id: str, paragraph: str):
        """Stream a content paragraph for progressive content updates."""
        if self._content_streaming_manager:
            try:
                await self._content_streaming_manager.stream_content_paragraph(
                    task_id, paragraph
                )
                logger.debug(f"Streamed content paragraph for task {task_id}")
            except Exception as e:
                logger.error(f"Failed to stream content paragraph: {e}")

    async def stream_fact_correction(self, task_id: str, correction: str):
        """Stream a fact correction for progressive content updates."""
        if self._content_streaming_manager:
            try:
                await self._content_streaming_manager.stream_fact_correction(
                    task_id, correction
                )
                logger.debug(f"Streamed fact correction for task {task_id}")
            except Exception as e:
                logger.error(f"Failed to stream fact correction: {e}")

    async def stream_final_content(self, task_id: str, final_content: str):
        """Stream the final complete content."""
        if self._content_streaming_manager:
            try:
                await self._content_streaming_manager.stream_final_content(
                    task_id, final_content
                )
                logger.info(f"Streamed final content for task {task_id}")
            except Exception as e:
                logger.error(f"Failed to stream final content: {e}")

    async def setup_content_streaming(self, task_id: str):
        """Set up content streaming for a task."""
        if self._content_streaming_manager:
            try:
                await self._content_streaming_manager.create_task_stream(task_id)
                logger.debug(f"Set up content streaming for task {task_id}")
            except Exception as e:
                logger.error(f"Failed to setup content streaming: {e}")

    def _count_words(self, content: str) -> int:
        """Count words in content, excluding markdown formatting."""
        if not content or not content.strip():
            return 0

        # Remove common markdown formatting for more accurate word count
        import re

        # Remove markdown headers
        content = re.sub(r"^#+\s+", "", content, flags=re.MULTILINE)
        # Remove markdown links [text](url)
        content = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", content)
        # Remove markdown images ![alt](url)
        content = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", "", content)
        # Remove markdown bold/italic
        content = re.sub(r"\*\*([^\*]+)\*\*", r"\1", content)
        content = re.sub(r"\*([^\*]+)\*", r"\1", content)
        # Remove markdown code blocks
        content = re.sub(r"```[^`]*```", "", content, flags=re.DOTALL)
        content = re.sub(r"`([^`]+)`", r"\1", content)

        # Split by whitespace and count non-empty words
        words = [word.strip() for word in content.split() if word.strip()]
        return len(words)


# Global instance
task_manager = TaskManager()
