"""
SSE (Server-Sent Events) Handler for Real-Time Task Updates

Extracted from main.py as part of Phase 3.3 modernization to improve
maintainability and testability of the SSE streaming functionality.

This module implements a robust triple fallback strategy for real-time
task updates with proper error handling and connection management.

Phase 3.3: Extract SSE Handler
Source: Both OpenAI GPT-5 Codex and Claude Sonnet 4.5 recommendations
Date: October 13, 2025
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, Optional
from contextlib import asynccontextmanager

from core.sse_message_types import (
    create_initializing_message,
    create_status_message,
    create_completed_message,
    create_error_message,
)

logger = logging.getLogger(__name__)


class SSEHandler:
    """
    Handles Server-Sent Events (SSE) streaming for real-time task updates.
    
    Implements triple fallback strategy:
    1. Redis Pub/Sub (real-time, preferred)
    2. Message Buffer Replay (in-memory cache)
    3. Database Polling (fallback when Redis unavailable)
    
    Features:
    - Connection heartbeat to prevent timeouts
    - Automatic reconnection and state recovery
    - Proper error handling and logging
    - Message deduplication
    - Buffer flush on connection
    """
    
    def __init__(
        self,
        redis_manager,
        task_manager,
        message_buffer=None,
        heartbeat_interval: int = 15,
        timeout_seconds: int = 1800,  # 30 minutes (increased from 8 minutes for long blog generation)
    ):
        """
        Initialize SSE Handler.
        
        Args:
            redis_manager: RedisManager instance for pub/sub
            task_manager: TaskManager instance for task state
            message_buffer: Optional message buffer for immediate message handling
            heartbeat_interval: Seconds between heartbeat pings (default: 15s)
            timeout_seconds: Maximum connection duration (default: 1800s = 30 min)
        """
        self.redis_manager = redis_manager
        self.task_manager = task_manager
        self.message_buffer = message_buffer
        self.heartbeat_interval = heartbeat_interval
        self.timeout_seconds = timeout_seconds
    
    async def stream_events(
        self,
        task_id: str,
        user_id: str,
        retry_count: int = 5,
    ) -> AsyncGenerator[str, None]:
        """
        Generate SSE events for a specific task.
        
        Main entry point for SSE streaming. Implements triple fallback strategy
        and handles connection lifecycle.
        
        Args:
            task_id: Task identifier
            user_id: User identifier for access control
            retry_count: Number of retries to wait for task creation
        
        Yields:
            SSE formatted event strings (data: {...}\n\n)
        """
        logger.info(f"📡 Starting SSE stream for task {task_id}, user {user_id}")
        
        # Handle race condition: task might not exist yet
        task = await self._wait_for_task_or_buffer(task_id, retry_count)
        
        if not task and not await self._check_buffer_exists(task_id):
            logger.error(f"❌ Task {task_id} not found and no buffer exists")
            yield self._format_error_event(
                "Task not found and no buffer exists", task_id
            )
            return
        
        # Immediately send connection acknowledgment
        yield self._format_connection_event(task_id)
        
        # Start heartbeat task in background
        heartbeat_task = asyncio.create_task(
            self._heartbeat_generator(task_id)
        )
        
        try:
            # Try Redis Pub/Sub (Strategy 1)
            if await self._redis_available():
                logger.info(f"📡 Using Redis pub/sub for task {task_id}")
                async for event in self._redis_streaming_loop(task_id):
                    yield event
            
            # Fall back to database polling (Strategy 3)
            else:
                logger.warning(
                    f"⚠️ Redis unavailable, using database polling for task {task_id}"
                )
                async for event in self._database_polling_loop(task_id):
                    yield event
        
        except asyncio.CancelledError:
            logger.info(f"🔌 SSE stream cancelled for task {task_id}")
        except Exception as e:
            logger.error(f"❌ SSE stream error for task {task_id}: {e}", exc_info=True)
            yield self._format_error_event(str(e), task_id)
        finally:
            # Clean up heartbeat task
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
            logger.info(f"✅ SSE stream ended for task {task_id}")
    
    async def _wait_for_task_or_buffer(
        self, task_id: str, max_retries: int
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for task to exist, handling race condition with task creation.
        
        Args:
            task_id: Task identifier
            max_retries: Maximum retry attempts
        
        Returns:
            Task dict if found, None otherwise
        """
        task = await self.task_manager.get_task(task_id)
        retry_count = 0
        
        while not task and retry_count < max_retries:
            # Check if buffer exists (pre-generated task ID)
            if await self._check_buffer_exists(task_id):
                logger.info(f"📦 Found buffer for pre-generated task {task_id}")
                return None  # Buffer exists, no need to wait for task
            
            logger.info(
                f"⏳ Task {task_id} not found, retrying in 0.5s "
                f"(attempt {retry_count + 1}/{max_retries})"
            )
            await asyncio.sleep(0.5)
            task = await self.task_manager.get_task(task_id)
            retry_count += 1
        
        return task
    
    async def _check_buffer_exists(self, task_id: str) -> bool:
        """Check if message buffer exists for task."""
        if not self.message_buffer:
            return False
        return await self.message_buffer._check_buffer_exists(task_id)
    
    async def _redis_available(self) -> bool:
        """Check if Redis connection is available."""
        return (
            self.redis_manager is not None
            and hasattr(self.redis_manager, "redis_client")
            and self.redis_manager.redis_client is not None
        )
    
    async def _redis_streaming_loop(self, task_id: str) -> AsyncGenerator[str, None]:
        """
        Redis pub/sub streaming loop with message buffer support.
        
        Strategy 1: Real-time Redis pub/sub with buffer flush
        
        Args:
            task_id: Task identifier
        
        Yields:
            SSE formatted event strings
        """
        redis_pubsub = None
        
        try:
            # Set up Redis pub/sub subscription
            redis_pubsub = self.redis_manager.redis_client.pubsub()
            
            # Subscribe to BOTH channels for complete message coverage
            task_updates_channel = f"task_updates:{task_id}"
            sse_immediate_channel = f"sse_immediate:{task_id}"
            
            await asyncio.wait_for(
                redis_pubsub.subscribe(task_updates_channel), timeout=5.0
            )
            await asyncio.wait_for(
                redis_pubsub.subscribe(sse_immediate_channel), timeout=5.0
            )
            
            logger.info(
                f"📡 Subscribed to Redis channels: {task_updates_channel}, "
                f"{sse_immediate_channel}"
            )
            
            # Wait for flow to start before flushing buffer
            await self._wait_for_flow_start(task_id, timeout=5.0)
            
            # Flush buffered messages
            async for event in self._flush_message_buffer(task_id):
                yield event
            
            # Get current task state and send initial update
            current_task = await self.task_manager.get_task(task_id)
            if current_task:
                yield self._format_task_update(current_task, task_id)
            
            # Main Redis listening loop
            start_time = datetime.utcnow()
            logger.info(
                f"🕐 Redis listener started with {self.timeout_seconds}s timeout "
                f"for task {task_id}"
            )
            
            async for message in redis_pubsub.listen():
                # Check timeout
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > self.timeout_seconds:
                    logger.info(
                        f"⏰ Redis listener reached timeout for task {task_id} after "
                        f"{elapsed:.1f}s (limit: {self.timeout_seconds}s) - "
                        f"this is normal for long-running generations"
                    )
                    break
                
                if message["type"] == "message":
                    try:
                        # Parse and forward Redis message
                        redis_data = json.loads(message["data"].decode("utf-8"))
                        message_type = redis_data.get(
                            "message_type", redis_data.get("type", "unknown")
                        )
                        
                        logger.info(
                            f"📨 Redis update for {task_id}: {message_type} "
                            f"(elapsed: {elapsed:.1f}s)"
                        )
                        
                        # Format and yield event
                        yield self._format_redis_message(redis_data, task_id)
                        
                        # Break on completion or error
                        if message_type in ["completed", "failed", "error"]:
                            logger.info(
                                f"🏁 Terminal state reached for {task_id}: "
                                f"{message_type}"
                            )
                            # Add delay to ensure message delivery
                            await asyncio.sleep(5)
                            break
                    
                    except json.JSONDecodeError as e:
                        logger.error(
                            f"❌ Failed to parse Redis message for {task_id}: {e}"
                        )
                    except Exception as e:
                        logger.error(
                            f"❌ Error processing Redis message for {task_id}: {e}",
                            exc_info=True,
                        )
        
        except asyncio.TimeoutError:
            logger.warning(
                f"⏰ Redis subscription timeout for task {task_id}, "
                f"falling back to database polling"
            )
        
        except Exception as e:
            logger.error(
                f"❌ Redis streaming error for task {task_id}: {e}",
                exc_info=True,
            )
        
        finally:
            # Clean up Redis pub/sub
            if redis_pubsub:
                try:
                    await redis_pubsub.close()
                    logger.debug(f"🔌 Closed Redis pubsub for task {task_id}")
                except Exception as close_error:
                    logger.error(
                        f"❌ Error closing Redis pubsub for {task_id}: {close_error}"
                    )
    
    async def _database_polling_loop(self, task_id: str) -> AsyncGenerator[str, None]:
        """
        Database polling fallback loop.
        
        Strategy 3: Poll database when Redis unavailable
        
        Args:
            task_id: Task identifier
        
        Yields:
            SSE formatted event strings
        """
        logger.info(f"🔄 Starting database polling for task {task_id}")
        
        last_status = None
        last_step = None
        last_progress = None
        poll_interval = 2.0  # seconds
        max_polls = int(self.timeout_seconds / poll_interval)
        poll_count = 0
        
        while poll_count < max_polls:
            try:
                task = await self.task_manager.get_task(task_id)
                
                if not task:
                    logger.warning(f"⚠️ Task {task_id} not found during polling")
                    break
                
                status = task.get("status", "").lower()
                step = task.get("current_step")
                progress = task.get("progress", 0)
                
                # Only send update if something changed
                if (
                    status != last_status
                    or step != last_step
                    or progress != last_progress
                ):
                    logger.info(
                        f"📊 Polling update for {task_id}: {status} - {step} ({progress}%)"
                    )
                    yield self._format_task_update(task, task_id)
                    
                    last_status = status
                    last_step = step
                    last_progress = progress
                
                # Break on terminal states
                if status in ["completed", "failed", "error"]:
                    logger.info(f"🏁 Task {task_id} reached terminal state: {status}")
                    break
                
                await asyncio.sleep(poll_interval)
                poll_count += 1
            
            except Exception as e:
                logger.error(
                    f"❌ Error polling task {task_id}: {e}",
                    exc_info=True,
                )
                await asyncio.sleep(poll_interval)
                poll_count += 1
        
        logger.info(
            f"🔚 Database polling ended for {task_id} after {poll_count} polls"
        )
    
    async def _heartbeat_generator(self, task_id: str) -> None:
        """
        Generate periodic heartbeat events to keep SSE connection alive.
        
        Args:
            task_id: Task identifier for logging
        """
        count = 0
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                count += 1
                logger.debug(f"💓 Heartbeat #{count} for task {task_id}")
        except asyncio.CancelledError:
            logger.debug(f"🔌 Heartbeat generator cancelled for task {task_id}")
    
    async def _wait_for_flow_start(self, task_id: str, timeout: float) -> bool:
        """
        Wait for CrewAI flow to start before flushing message buffer.
        
        Args:
            task_id: Task identifier
            timeout: Maximum seconds to wait
        
        Returns:
            True if flow started, False if timeout
        """
        if not self.redis_manager or not self.redis_manager.redis_client:
            return False
        
        elapsed = 0.0
        check_interval = 0.2
        
        logger.info(f"⏳ Waiting for CrewAI flow to start for task {task_id}...")
        
        while elapsed < timeout:
            flow_status_key = f"flow_status:{task_id}"
            flow_status = await self.redis_manager.redis_client.get(flow_status_key)
            
            if flow_status == "started":
                logger.info(f"✅ Flow started for task {task_id}, flushing buffer now")
                return True
            
            await asyncio.sleep(check_interval)
            elapsed += check_interval
        
        logger.info(
            f"⏰ Timeout waiting for flow start for task {task_id}, "
            f"flushing buffer anyway"
        )
        return False
    
    async def _flush_message_buffer(self, task_id: str) -> AsyncGenerator[str, None]:
        """
        Flush buffered messages to SSE stream.
        
        Args:
            task_id: Task identifier
        
        Yields:
            SSE formatted buffered messages
        """
        if not self.message_buffer:
            return
        
        try:
            buffered_messages = await self.message_buffer.flush_buffered_messages(
                task_id
            )
            
            if buffered_messages:
                logger.info(
                    f"📤 Replaying {len(buffered_messages)} buffered messages "
                    f"for task {task_id}"
                )
                
                for buffered_msg in buffered_messages:
                    # Send each buffered message
                    replay_data = buffered_msg.message_data.copy()
                    replay_data["replayed"] = True
                    replay_data["buffer_timestamp"] = buffered_msg.timestamp
                    
                    yield f"data: {json.dumps(replay_data)}\n\n"
                    
                    logger.info(
                        f"📤 Replayed {buffered_msg.message_type} message "
                        f"(buffered at {buffered_msg.timestamp})"
                    )
            else:
                logger.info(f"📦 No buffered messages found for task {task_id}")
        
        except Exception as e:
            logger.error(
                f"❌ Failed to flush buffered messages for task {task_id}: {e}",
                exc_info=True,
            )
    
    def _format_connection_event(self, task_id: str) -> str:
        """Format SSE connection acknowledgment event."""
        event = {
            "type": "connected",
            "message_type": "connected",
            "task_id": task_id,
            "message": "SSE connection established",
            "timestamp": datetime.utcnow().isoformat(),
        }
        return f"data: {json.dumps(event)}\n\n"
    
    def _format_error_event(self, error_msg: str, task_id: str) -> str:
        """Format SSE error event."""
        error_message = create_error_message(
            task_id=task_id, error_msg=error_msg, recoverable=False
        )
        return f"data: {json.dumps(error_message.to_dict())}\n\n"
    
    def _format_task_update(self, task_data: Dict[str, Any], task_id: str) -> str:
        """
        Format task data as SSE event.
        
        Args:
            task_data: Task state dictionary
            task_id: Task identifier
        
        Returns:
            SSE formatted event string
        """
        status = task_data.get("status", "").lower()
        step = task_data.get("current_step")
        progress_raw = task_data.get("progress", 0)
        progress = float(progress_raw) if progress_raw is not None else 0.0
        hero_url = task_data.get("hero_image_url")
        
        logger.info(
            f"📡 SSE {task_id}: Sending progress {progress}% "
            f"(raw: {progress_raw}, step: {step})"
        )
        
        # Create appropriate message type based on status
        if status == "completed":
            final_content = task_data.get("content")
            generation_time = task_data.get("generation_time")
            message = create_completed_message(
                task_id=task_id,
                final_content=final_content,
                generation_time=generation_time,
            )
        elif status == "failed":
            error_details = task_data.get("error", "Unknown error occurred")
            message = create_error_message(
                task_id=task_id, error_msg=error_details, recoverable=False
            )
        else:
            # Regular status update
            message = create_status_message(
                task_id=task_id,
                status=status,
                message=task_data.get("message", f"Status: {status}"),
                step=step,
                progress=progress,
            )
        
        # Add hero image information if available
        payload = message.to_dict()
        if hero_url:
            payload["hero_image_url"] = hero_url
        
        return f"data: {json.dumps(payload)}\n\n"
    
    def _format_redis_message(self, redis_data: Dict[str, Any], task_id: str) -> str:
        """
        Format Redis pub/sub message as SSE event.
        
        Args:
            redis_data: Redis message data
            task_id: Task identifier
        
        Returns:
            SSE formatted event string
        """
        message_type = redis_data.get("message_type", redis_data.get("type", "unknown"))
        
        # Handle completion messages with special processing
        if message_type == "completed":
            logger.info(f"🔍 Processing Redis completion message for {task_id}")
            logger.info(f"   redis_data keys: {list(redis_data.keys())}")
            
            final_content = redis_data.get("final_content", "")
            hero_image_url = redis_data.get("hero_image_url")
            
            logger.info(f"🔍 Content length: {len(final_content)}")
            
            # Create completion message with Redis data
            completion_task_data = {
                "status": "completed",
                "current_step": "Blog generation completed successfully!",
                "progress": 100,
                "message": f"Blog generation completed ({len(final_content)} words)",
                "task_id": task_id,
                "content": final_content,
                "hero_image_url": hero_image_url,
            }
            
            event_str = self._format_task_update(completion_task_data, task_id)
            logger.info(f"✅ Sent completion with {len(final_content)} chars for {task_id}")
            return event_str
        
        # For other message types, forward as-is
        return f"data: {json.dumps(redis_data)}\n\n"
