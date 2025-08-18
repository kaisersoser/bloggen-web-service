"""
Redis Pub/Sub Manager for Real-time Task Updates
Implements Redis-based publish/subscribe system for instant task notifications
without database polling.
"""
import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any, Callable, Union
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
    def from_redis_message(cls, message: str) -> 'TaskUpdateMessage':
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
                if message['type'] == 'message':
                    try:
                        # Parse the task update message
                        task_update = TaskUpdateMessage.from_redis_message(
                            message['data'].decode('utf-8')
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
                max_connections=20,
                retry_on_timeout=True
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
            
            # Publish to task-specific channel
            task_channel = f"task_updates:{task_update.task_id}"
            await self.redis_client.publish(task_channel, message_data)
            
            # Publish to user-specific channel
            user_channel = f"user_updates:{task_update.user_id}"
            await self.redis_client.publish(user_channel, message_data)
            
            logger.info(f"📡 Published task update: {task_update.task_id} -> {task_update.phase}")
            
        except Exception as e:
            logger.error(f"❌ Failed to publish task update: {e}")
            
    async def create_subscriber(self, subscriber_id: str, callback: Callable) -> RedisSubscriber:
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
                return json.loads(cached_status.decode('utf-8'))
                
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get task status from Redis: {e}")
            return None
            
    async def cache_task_status(self, task_id: str, status_data: Dict[str, Any], ttl: int = 3600):
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
            
            await self.redis_client.setex(
                status_key, 
                ttl, 
                json.dumps(serialized_data)
            )
            
            logger.debug(f"💾 Cached task status: {task_id}")
            
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
