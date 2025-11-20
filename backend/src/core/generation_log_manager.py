"""
Generation Log Manager

Manages generation logs with Redis-backed storage and automatic cleanup.
Logs are stored during generation and automatically deleted after completion.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, AsyncIterator

logger = logging.getLogger(__name__)


class GenerationLogManager:
    """
    Manages generation logs with automatic cleanup.
    
    Features:
    - Redis-backed storage for temporary logs
    - Automatic TTL for cleanup
    - SSE streaming support
    - Pub/sub for real-time updates
    """
    
    def __init__(self, redis_manager):
        """
        Initialize log manager.
        
        Args:
            redis_manager: Redis manager instance for storage and pub/sub
        """
        self.redis = redis_manager
        self.log_ttl = 3600  # 1 hour default TTL
        self.cleanup_delay = 300  # 5 minutes retention after completion
        
        logger.info("📝 GenerationLogManager initialized")
    
    async def append_log(
        self,
        task_id: str,
        step: str,
        message: str,
        progress: int = 0,
        level: str = "info"
    ):
        """
        Append a log entry to Redis and publish to subscribers.
        
        Args:
            task_id: Task identifier
            step: Current step name
            message: Log message
            progress: Progress percentage (0-100)
            level: Log level (info, warning, error)
        """
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "step": step,
                "message": message,
                "progress": progress,
                "level": level
            }
            
            # Store in Redis list
            key = f"generation_logs:{task_id}"
            await self.redis.redis_client.rpush(key, json.dumps(log_entry))
            await self.redis.redis_client.expire(key, self.log_ttl)
            
            # Publish to pub/sub for real-time streaming
            pubsub_channel = f"log_updates:{task_id}"
            await self.redis.redis_client.publish(
                pubsub_channel,
                json.dumps(log_entry)
            )
            
            logger.debug(f"📝 Log appended for {task_id}: {step} - {message}")
            
        except Exception as e:
            logger.error(f"Failed to append log for {task_id}: {e}", exc_info=True)
    
    async def get_logs(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all logs for a task.
        
        Args:
            task_id: Task identifier
        
        Returns:
            List of log entries
        """
        try:
            key = f"generation_logs:{task_id}"
            logs_raw = await self.redis.redis_client.lrange(key, 0, -1)
            
            if not logs_raw:
                return []
            
            logs = [json.loads(log) for log in logs_raw]
            logger.debug(f"📖 Retrieved {len(logs)} logs for {task_id}")
            
            return logs
            
        except Exception as e:
            logger.error(f"Failed to get logs for {task_id}: {e}", exc_info=True)
            return []
    
    async def get_recent_logs(
        self,
        task_id: str,
        count: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get the most recent N logs.
        
        Args:
            task_id: Task identifier
            count: Number of recent logs to retrieve
        
        Returns:
            List of recent log entries
        """
        try:
            key = f"generation_logs:{task_id}"
            # Get last N entries
            logs_raw = await self.redis.redis_client.lrange(key, -count, -1)
            
            if not logs_raw:
                return []
            
            logs = [json.loads(log) for log in logs_raw]
            return logs
            
        except Exception as e:
            logger.error(
                f"Failed to get recent logs for {task_id}: {e}",
                exc_info=True
            )
            return []
    
    async def stream_logs_sse(self, task_id: str) -> AsyncIterator[str]:
        """
        Stream logs via Server-Sent Events.
        
        Yields existing logs first, then streams new logs as they arrive.
        
        Args:
            task_id: Task identifier
        
        Yields:
            SSE-formatted log messages
        """
        try:
            # First, send all existing logs
            existing_logs = await self.get_logs(task_id)
            for log in existing_logs:
                yield f"data: {json.dumps(log)}\n\n"
            
            # Subscribe to new logs
            pubsub_channel = f"log_updates:{task_id}"
            pubsub = self.redis.redis_client.pubsub()
            
            try:
                await pubsub.subscribe(pubsub_channel)
                logger.info(f"📡 SSE log stream started for {task_id}")
                
                # Stream new logs as they arrive
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        log_data = message["data"]
                        
                        # Redis returns bytes, decode if needed
                        if isinstance(log_data, bytes):
                            log_data = log_data.decode('utf-8')
                        
                        yield f"data: {log_data}\n\n"
                        
            finally:
                await pubsub.unsubscribe(pubsub_channel)
                await pubsub.close()
                logger.info(f"📡 SSE log stream ended for {task_id}")
                
        except asyncio.CancelledError:
            logger.info(f"📡 SSE log stream cancelled for {task_id}")
            raise
        except Exception as e:
            logger.error(
                f"Error streaming logs for {task_id}: {e}",
                exc_info=True
            )
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    async def cleanup_logs(self, task_id: str, delay_seconds: Optional[int] = None):
        """
        Schedule log deletion after a delay.
        
        Args:
            task_id: Task identifier
            delay_seconds: Delay before deletion (uses default if None)
        """
        try:
            delay = delay_seconds if delay_seconds is not None else self.cleanup_delay
            key = f"generation_logs:{task_id}"
            
            # Set shorter TTL so logs expire after delay
            await self.redis.redis_client.expire(key, delay)
            
            logger.info(
                f"🗑️ Logs for {task_id} will be deleted in {delay} seconds"
            )
            
        except Exception as e:
            logger.error(
                f"Failed to schedule log cleanup for {task_id}: {e}",
                exc_info=True
            )
    
    async def delete_logs_immediately(self, task_id: str):
        """
        Delete logs immediately without delay.
        
        Args:
            task_id: Task identifier
        """
        try:
            key = f"generation_logs:{task_id}"
            await self.redis.redis_client.delete(key)
            
            logger.info(f"🗑️ Logs deleted immediately for {task_id}")
            
        except Exception as e:
            logger.error(
                f"Failed to delete logs for {task_id}: {e}",
                exc_info=True
            )
    
    async def check_logs_exist(self, task_id: str) -> bool:
        """
        Check if logs exist for a task.
        
        Args:
            task_id: Task identifier
        
        Returns:
            True if logs exist, False otherwise
        """
        try:
            key = f"generation_logs:{task_id}"
            exists = await self.redis.redis_client.exists(key)
            return bool(exists)
            
        except Exception as e:
            logger.error(
                f"Failed to check log existence for {task_id}: {e}",
                exc_info=True
            )
            return False
    
    async def get_log_count(self, task_id: str) -> int:
        """
        Get the number of log entries for a task.
        
        Args:
            task_id: Task identifier
        
        Returns:
            Number of log entries
        """
        try:
            key = f"generation_logs:{task_id}"
            count = await self.redis.redis_client.llen(key)
            return count
            
        except Exception as e:
            logger.error(
                f"Failed to get log count for {task_id}: {e}",
                exc_info=True
            )
            return 0
    
    def configure(self, log_ttl: Optional[int] = None, cleanup_delay: Optional[int] = None):
        """
        Configure log manager settings.
        
        Args:
            log_ttl: Maximum TTL for logs (seconds)
            cleanup_delay: Delay before cleanup after completion (seconds)
        """
        if log_ttl is not None:
            self.log_ttl = log_ttl
            logger.info(f"📝 Log TTL configured to {log_ttl} seconds")
        
        if cleanup_delay is not None:
            self.cleanup_delay = cleanup_delay
            logger.info(f"📝 Cleanup delay configured to {cleanup_delay} seconds")


# Note: Global instance will be created in main.py after redis_manager is initialized
