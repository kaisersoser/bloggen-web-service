"""
Redis Pub/Sub Manager for Real-time Task Updates
Implements Redis-based publish/subscribe system for instant task notifications
without database polling.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any, Callable
from datetime import datetime

import redis.asyncio as aioredis
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TaskUpdateMessage(BaseModel):
    """Redis message for task updates"""

    task_id: str
    user_id: str
    phase: str
    progress: float
    details: str
    timestamp: str
    status: str  # 'running', 'completed', 'failed'

    def to_redis_message(self) -> str:
        """Convert to Redis message format"""
        return json.dumps(self.model_dump())

    @classmethod
    def from_redis_message(cls, message: str) -> "TaskUpdateMessage":
        """Create from Redis message"""
        data = json.loads(message)
        return cls(**data)


class RedisSubscriber:
    """Handles Redis subscription for a specific task/user"""

    def __init__(self, redis_client: aioredis.Redis, callback: Callable):
        self.redis_client = redis_client
        self.callback = callback
        self.subscribed_channels: Set[str] = set()
        self.pubsub: Optional[Any] = None  # Redis PubSub object
        self.listening_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the Redis subscriber"""
        try:
            self.pubsub = self.redis_client.pubsub()
            self.listening_task = asyncio.create_task(self._listen_loop())
            logger.info("✅ Redis subscriber started")
        except Exception as e:
            logger.error(f"❌ Failed to start Redis subscriber: {e}")
            raise

    async def stop(self):
        """Stop the Redis subscriber"""
        try:
            if self.listening_task:
                self.listening_task.cancel()
                try:
                    await self.listening_task
                except asyncio.CancelledError:
                    pass

            if self.pubsub:
                await self.pubsub.unsubscribe(*self.subscribed_channels)
                await self.pubsub.close()

            self.subscribed_channels.clear()
            logger.info("✅ Redis subscriber stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping Redis subscriber: {e}")

    async def subscribe_to_task(self, task_id: str):
        """Subscribe to updates for a specific task"""
        try:
            if not self.pubsub:
                logger.error("❌ PubSub not initialized")
                return

            channel = f"task_updates:{task_id}"
            if channel not in self.subscribed_channels:
                await self.pubsub.subscribe(channel)
                self.subscribed_channels.add(channel)
                logger.info(f"📡 Subscribed to task updates: {task_id}")
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to task {task_id}: {e}")

    async def subscribe_to_user(self, user_id: str):
        """Subscribe to updates for all user tasks"""
        try:
            if not self.pubsub:
                logger.error("❌ PubSub not initialized")
                return

            channel = f"user_updates:{user_id}"
            if channel not in self.subscribed_channels:
                await self.pubsub.subscribe(channel)
                self.subscribed_channels.add(channel)
                logger.info(f"📡 Subscribed to user updates: {user_id}")
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to user {user_id}: {e}")

    async def unsubscribe_from_task(self, task_id: str):
        """Unsubscribe from a specific task"""
        try:
            if not self.pubsub:
                logger.error("❌ PubSub not initialized")
                return

            channel = f"task_updates:{task_id}"
            if channel in self.subscribed_channels:
                await self.pubsub.unsubscribe(channel)
                self.subscribed_channels.remove(channel)
                logger.info(f"📡 Unsubscribed from task: {task_id}")
        except Exception as e:
            logger.error(f"❌ Failed to unsubscribe from task {task_id}: {e}")

    async def _listen_loop(self):
        """Main listening loop for Redis messages"""
        try:
            if not self.pubsub:
                logger.error("❌ PubSub not initialized")
                return

            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        # Parse the task update message
                        task_update = TaskUpdateMessage.from_redis_message(
                            message["data"].decode("utf-8")
                        )

                        # Call the callback with the update
                        await self.callback(task_update)

                    except Exception as e:
                        logger.error(f"❌ Error processing Redis message: {e}")

        except asyncio.CancelledError:
            logger.info("📡 Redis listening loop cancelled")
        except Exception as e:
            logger.error(f"❌ Error in Redis listening loop: {e}")


class RedisManager:
    """
    Manages Redis connections and pub/sub for real-time task updates.

    This replaces database polling with instant Redis notifications.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[aioredis.Redis] = None
        self.subscribers: Dict[str, RedisSubscriber] = {}
        self.connection_pool = None

    async def connect(self):
        """Establish Redis connection"""
        try:
            self.connection_pool = aioredis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=50,  # Increased from 20 to handle SSE connections
                retry_on_timeout=True,
                socket_timeout=5,  # 5 second socket timeout
                socket_connect_timeout=5,  # 5 second connect timeout
            )
            self.redis_client = aioredis.Redis(connection_pool=self.connection_pool)

            # Test the connection
            await self.redis_client.ping()
            logger.info("✅ Redis connection established")

        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Close Redis connection"""
        try:
            # Stop all subscribers
            for subscriber_id, subscriber in list(self.subscribers.items()):
                await subscriber.stop()

            self.subscribers.clear()

            if self.redis_client:
                await self.redis_client.close()

            if self.connection_pool:
                await self.connection_pool.disconnect()

            logger.info("✅ Redis connection closed")

        except Exception as e:
            logger.error(f"❌ Error closing Redis connection: {e}")

    async def publish_task_update(self, task_update: TaskUpdateMessage):
        """
        Publish a task update to Redis channels.

        Publishes to both task-specific and user-specific channels
        for maximum flexibility.
        """
        try:
            if not self.redis_client:
                logger.error("❌ Redis client not connected")
                return

            message_data = task_update.to_redis_message()

            # Publish to task-specific channel with timeout
            task_channel = f"task_updates:{task_update.task_id}"
            await asyncio.wait_for(
                self.redis_client.publish(task_channel, message_data), timeout=3.0
            )

            # Publish to user-specific channel with timeout
            user_channel = f"user_updates:{task_update.user_id}"
            await asyncio.wait_for(
                self.redis_client.publish(user_channel, message_data), timeout=3.0
            )

            logger.info(
                f"📡 Published task update: {task_update.task_id} -> {task_update.phase}"
            )

        except asyncio.TimeoutError:
            logger.error(f"❌ Timeout publishing task update: {task_update.task_id}")
        except Exception as e:
            logger.error(f"❌ Failed to publish task update: {e}")

    async def publish_immediate_message(
        self, task_id: str, message_data: Dict[str, Any]
    ):
        """
        Publish immediate SSE message for instant user feedback (Phase 1 Foundation).

        Sends structured SSE messages directly to task channels for real-time updates
        including agent decisions, tool usage, and content streaming.
        """
        try:
            if not self.redis_client:
                logger.error("❌ Redis client not connected for immediate message")
                return

            # REDIS PUBLISHING TRACKING - Detailed message analysis
            import time

            publish_timestamp = time.time()
            publish_sequence_id = int(publish_timestamp * 1000000)

            logger.warning(
                f"🔍 REDIS PUBLISH #{publish_sequence_id} - MESSAGE ANALYSIS START:"
            )
            logger.warning(f"   task_id: {task_id}")
            logger.warning(f"   message_data keys: {list(message_data.keys())}")
            logger.warning(
                f"   message_type: {message_data.get('message_type', 'MISSING')}"
            )

            # Track completion message content specifically
            if message_data.get("message_type") == "completion":
                final_content = message_data.get("final_content", "")
                word_count = message_data.get("word_count", 0)
                logger.warning(
                    f"🔍 REDIS PUBLISH #{publish_sequence_id} - COMPLETION MESSAGE:"
                )
                logger.warning(
                    f"   final_content length: {len(final_content) if final_content else 0}"
                )
                logger.warning(
                    f"   final_content preview: {final_content[:200] if final_content else 'EMPTY CONTENT'}..."
                )
                logger.warning(f"   word_count: {word_count}")

            # Add timestamp if not present
            if "timestamp" not in message_data:
                message_data["timestamp"] = datetime.utcnow().isoformat()

            # Serialize message for Redis
            message_json = json.dumps(message_data)
            logger.warning(
                f"🔍 REDIS PUBLISH #{publish_sequence_id} - JSON SERIALIZED:"
            )
            logger.warning(f"   json length: {len(message_json)}")
            logger.warning(f"   json preview: {message_json[:300]}...")

            # Publish to SSE-specific task channel for immediate delivery with timeout
            sse_channel = f"sse_immediate:{task_id}"
            await asyncio.wait_for(
                self.redis_client.publish(sse_channel, message_json), timeout=3.0
            )

            logger.warning(
                f"✅ REDIS PUBLISH #{publish_sequence_id} - MESSAGE PUBLISHED to channel: {sse_channel}"
            )
            logger.debug(
                f"📡 Published immediate message: {task_id} -> {message_data.get('message_type', 'unknown')}"
            )

        except asyncio.TimeoutError:
            logger.error(f"❌ Timeout publishing immediate message for task {task_id}")
        except Exception as e:
            logger.error(
                f"❌ Failed to publish immediate message for task {task_id}: {e}"
            )

    async def create_subscriber(
        self, subscriber_id: str, callback: Callable
    ) -> RedisSubscriber:
        """Create a new Redis subscriber"""
        try:
            if not self.redis_client:
                logger.error("❌ Redis client not connected")
                raise Exception("Redis client not connected")

            if subscriber_id in self.subscribers:
                # Stop existing subscriber
                await self.subscribers[subscriber_id].stop()

            subscriber = RedisSubscriber(self.redis_client, callback)
            await subscriber.start()

            self.subscribers[subscriber_id] = subscriber
            logger.info(f"✅ Created Redis subscriber: {subscriber_id}")

            return subscriber

        except Exception as e:
            logger.error(f"❌ Failed to create subscriber {subscriber_id}: {e}")
            raise

    async def remove_subscriber(self, subscriber_id: str):
        """Remove a Redis subscriber"""
        try:
            if subscriber_id in self.subscribers:
                await self.subscribers[subscriber_id].stop()
                del self.subscribers[subscriber_id]
                logger.info(f"✅ Removed Redis subscriber: {subscriber_id}")

        except Exception as e:
            logger.error(f"❌ Failed to remove subscriber {subscriber_id}: {e}")

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get cached task status from Redis"""
        try:
            if not self.redis_client:
                return None

            status_key = f"task_status:{task_id}"
            cached_status = await self.redis_client.get(status_key)

            if cached_status:
                return json.loads(cached_status.decode("utf-8"))

            return None

        except Exception as e:
            logger.error(f"❌ Failed to get task status from Redis: {e}")
            return None

    async def wait_for_completion_acknowledgment(
        self, task_id: str, timeout: int = 30
    ) -> bool:
        """
        Wait for completion acknowledgment from frontend.
        Returns True if ack received, False if timeout.
        """
        try:
            if not self.redis_client:
                logger.error("❌ Redis client not connected for acknowledgment wait")
                return False

            ack_key = f"completion_ack:{task_id}"

            logger.info(
                f"⏳ Waiting for completion acknowledgment for {task_id} (timeout: {timeout}s)"
            )

            # Poll for acknowledgment with timeout
            for i in range(timeout):
                ack_status = await self.redis_client.get(ack_key)
                if ack_status:
                    logger.info(
                        f"✅ Completion acknowledgment received for {task_id} after {i+1}s"
                    )
                    # Clean up the acknowledgment key
                    await self.redis_client.delete(ack_key)
                    return True
                await asyncio.sleep(1)

            logger.warning(
                f"⏰ Completion acknowledgment timeout for {task_id} after {timeout}s"
            )
            return False

        except Exception as e:
            logger.error(
                f"❌ Error waiting for completion acknowledgment {task_id}: {e}"
            )
            return False

    async def send_completion_acknowledgment(self, task_id: str):
        """
        Send completion acknowledgment from frontend to backend.
        """
        try:
            if not self.redis_client:
                logger.error("❌ Redis client not connected for acknowledgment")
                return

            ack_key = f"completion_ack:{task_id}"

            # Set acknowledgment with 60-second TTL
            await self.redis_client.setex(ack_key, 60, "acknowledged")
            logger.info(f"✅ Sent completion acknowledgment for {task_id}")

        except Exception as e:
            logger.error(f"❌ Error sending completion acknowledgment {task_id}: {e}")

    async def cache_task_status(
        self, task_id: str, status_data: Dict[str, Any], ttl: int = 3600
    ):
        """Cache task status in Redis with TTL"""
        try:
            if not self.redis_client:
                return

            status_key = f"task_status:{task_id}"

            # Serialize datetime objects to ISO format strings
            def serialize_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: serialize_datetime(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [serialize_datetime(item) for item in obj]
                return obj

            serialized_data = serialize_datetime(status_data)

            await asyncio.wait_for(
                self.redis_client.setex(status_key, ttl, json.dumps(serialized_data)),
                timeout=3.0,
            )

            logger.debug(f"💾 Cached task status: {task_id}")

        except asyncio.TimeoutError:
            logger.error(f"❌ Timeout caching task status for {task_id}")
        except Exception as e:
            logger.error(f"❌ Failed to cache task status: {e}")

    async def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            if not self.redis_client:
                return False

            await self.redis_client.ping()
            return True

        except Exception as e:
            logger.error(f"❌ Redis health check failed: {e}")
            return False


# Global Redis manager instance
redis_manager = RedisManager()
