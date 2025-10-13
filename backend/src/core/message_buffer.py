"""
Redis Message Buffer for Early Message Capture

Buffers messages published before SSE connections are established,
ensuring no early messages (taskcreated, initializing, etc.) are lost.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class BufferedMessage:
    """Represents a buffered message with metadata."""

    task_id: str
    message_data: Dict[str, Any]
    channel: str
    timestamp: str
    message_type: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RedisMessageBuffer:
    """
    Buffers Redis messages for tasks until SSE connections are established.

    This solves the timing issue where early messages (taskcreated, initializing)
    are published before the frontend SSE connection is ready to receive them.
    """

    def __init__(self, redis_manager, buffer_ttl_minutes: int = 30):
        self.redis_manager = redis_manager
        self.buffer_ttl_minutes = buffer_ttl_minutes
        self._active_buffers: Dict[str, List[BufferedMessage]] = {}

    def _get_buffer_key(self, task_id: str) -> str:
        """Generate Redis key for message buffer."""
        return f"message_buffer:{task_id}"

    def _get_buffer_metadata_key(self, task_id: str) -> str:
        """Generate Redis key for buffer metadata."""
        return f"message_buffer_meta:{task_id}"

    async def _check_buffer_exists(self, task_id: str) -> bool:
        """Check if a message buffer exists for the given task ID."""
        buffer_key = self._get_buffer_key(task_id)
        try:
            exists = await self.redis_manager.redis_client.exists(buffer_key)
            return bool(exists)
        except Exception as e:
            logger.error(f"❌ Failed to check buffer existence for task {task_id}: {e}")
            return False

    async def start_buffering(self, task_id: str) -> None:
        """
        Start buffering messages for a task ID.

        Should be called when a task ID is generated but before
        SSE connection is established.
        """
        buffer_key = self._get_buffer_key(task_id)
        meta_key = self._get_buffer_metadata_key(task_id)

        # Initialize buffer in Redis with TTL
        buffer_data = {
            "task_id": task_id,
            "created_at": datetime.utcnow().isoformat(),
            "messages": [],
        }

        try:
            # Store with TTL to prevent memory leaks
            ttl_seconds = self.buffer_ttl_minutes * 60
            await self.redis_manager.redis_client.setex(
                buffer_key, ttl_seconds, json.dumps(buffer_data)
            )
            await self.redis_manager.redis_client.setex(
                meta_key,
                ttl_seconds,
                json.dumps(
                    {"status": "buffering", "created_at": datetime.utcnow().isoformat()}
                ),
            )

            # Also track in memory for fast access
            self._active_buffers[task_id] = []

            logger.info(f"📦 Started message buffering for task {task_id}")

        except Exception as e:
            logger.error(f"❌ Failed to start buffering for task {task_id}: {e}")

    async def buffer_message(
        self, task_id: str, channel: str, message_data: Dict[str, Any]
    ) -> bool:
        """
        Buffer a message for the specified task.

        Returns True if message was buffered, False if buffering is not active.
        """
        buffer_key = self._get_buffer_key(task_id)

        try:
            # Check if buffering is active for this task
            buffer_exists = await self.redis_manager.redis_client.exists(buffer_key)
            if not buffer_exists:
                return False

            # Create buffered message
            buffered_msg = BufferedMessage(
                task_id=task_id,
                message_data=message_data,
                channel=channel,
                timestamp=datetime.utcnow().isoformat(),
                message_type=message_data.get("message_type", "unknown"),
            )

            # Add to in-memory buffer for fast access
            if task_id in self._active_buffers:
                self._active_buffers[task_id].append(buffered_msg)

            # Update Redis buffer
            buffer_data_str = await self.redis_manager.redis_client.get(buffer_key)
            if buffer_data_str:
                buffer_data = json.loads(buffer_data_str)
                buffer_data["messages"].append(buffered_msg.to_dict())

                # Update with preserved TTL
                ttl = await self.redis_manager.redis_client.ttl(buffer_key)
                if ttl > 0:
                    await self.redis_manager.redis_client.setex(
                        buffer_key, ttl, json.dumps(buffer_data)
                    )

            logger.info(
                f"📦 Buffered {buffered_msg.message_type} message for task {task_id}"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Failed to buffer message for task {task_id}: {e}")
            return False

    async def flush_buffered_messages(self, task_id: str) -> List[BufferedMessage]:
        """
        Retrieve and clear all buffered messages for a task.

        Should be called when SSE connection is established to replay
        early messages that were missed.
        """
        buffer_key = self._get_buffer_key(task_id)
        meta_key = self._get_buffer_metadata_key(task_id)

        try:
            # Get buffered messages
            buffer_data_str = await self.redis_manager.redis_client.get(buffer_key)
            messages = []

            if buffer_data_str:
                buffer_data = json.loads(buffer_data_str)
                message_dicts = buffer_data.get("messages", [])

                # Convert back to BufferedMessage objects
                for msg_dict in message_dicts:
                    messages.append(BufferedMessage(**msg_dict))

                logger.info(
                    f"📤 Flushing {len(messages)} buffered messages for task {task_id}"
                )

            # Clean up Redis keys
            await self.redis_manager.redis_client.delete(buffer_key, meta_key)

            # Clean up in-memory buffer
            self._active_buffers.pop(task_id, None)

            return messages

        except Exception as e:
            logger.error(
                f"❌ Failed to flush buffered messages for task {task_id}: {e}"
            )
            return []

    async def stop_buffering(self, task_id: str) -> None:
        """
        Stop buffering for a task without flushing messages.

        Used for cleanup when tasks are cancelled or fail.
        """
        buffer_key = self._get_buffer_key(task_id)
        meta_key = self._get_buffer_metadata_key(task_id)

        try:
            await self.redis_manager.redis_client.delete(buffer_key, meta_key)
            self._active_buffers.pop(task_id, None)
            logger.info(f"🛑 Stopped message buffering for task {task_id}")

        except Exception as e:
            logger.error(f"❌ Failed to stop buffering for task {task_id}: {e}")

    async def is_buffering(self, task_id: str) -> bool:
        """Check if buffering is active for a task."""
        buffer_key = self._get_buffer_key(task_id)
        try:
            return await self.redis_manager.redis_client.exists(buffer_key) > 0
        except Exception:
            return False

    async def get_buffer_stats(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics about a task's message buffer."""
        buffer_key = self._get_buffer_key(task_id)
        meta_key = self._get_buffer_metadata_key(task_id)

        try:
            buffer_data_str = await self.redis_manager.redis_client.get(buffer_key)
            meta_data_str = await self.redis_manager.redis_client.get(meta_key)

            if not buffer_data_str or not meta_data_str:
                return None

            buffer_data = json.loads(buffer_data_str)
            meta_data = json.loads(meta_data_str)

            return {
                "task_id": task_id,
                "message_count": len(buffer_data.get("messages", [])),
                "created_at": meta_data.get("created_at"),
                "status": meta_data.get("status"),
                "ttl_seconds": await self.redis_manager.redis_client.ttl(buffer_key),
            }

        except Exception as e:
            logger.error(f"❌ Failed to get buffer stats for task {task_id}: {e}")
            return None

    async def cleanup_expired_buffers(self) -> int:
        """
        Clean up expired buffers (Redis TTL handles most of this).

        Returns number of buffers cleaned up.
        """
        cleaned_count = 0

        # Clean up in-memory buffers for tasks that no longer exist in Redis
        tasks_to_remove = []
        for task_id in list(self._active_buffers.keys()):
            if not await self.is_buffering(task_id):
                tasks_to_remove.append(task_id)

        for task_id in tasks_to_remove:
            self._active_buffers.pop(task_id, None)
            cleaned_count += 1

        if cleaned_count > 0:
            logger.info(f"🧹 Cleaned up {cleaned_count} expired message buffers")

        return cleaned_count
