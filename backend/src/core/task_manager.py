"""
Task Manager for database-backed task state management.

Replaces the in-memory active_tasks dictionary with persistent database storage.
Integrates with Redis pub/sub for real-time updates.
Enhanced with immediate SSE message broadcasting for Phase 1 Foundation.
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from enum import Enum

# Import enhanced SSE message types for immediate feedback
from core.sse_message_types import create_task_created_message, create_status_message, create_completed_message

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
    
    def set_redis_manager(self, redis_manager):
        """Set the Redis manager for pub/sub updates."""
        self._redis_manager = redis_manager
    
    def set_content_streaming_manager(self, content_streaming_manager):
        """Set the content streaming manager for progressive content updates."""
        self._content_streaming_manager = content_streaming_manager
    
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
                    user_id=task_data.get('user_id', ''),
                    phase=task_data.get('current_step', ''),
                    progress=task_data.get('progress', 0),
                    details=task_data.get('details', ''),
                    timestamp=datetime.utcnow().isoformat(),
                    status=task_data.get('status', '').lower()
                )
                
                # Publish to Redis
                await self._redis_manager.publish_task_update(redis_message)
                
                # Cache task status in Redis
                await self._redis_manager.cache_task_status(task_id, task_data)
                
                logger.debug(f"Published Redis update for task {task_id}")
                
            except Exception as e:
                logger.error(f"Failed to publish Redis update: {e}")
        
        # Content streaming broadcast (Phase 4 enhancement)
        if self._content_streaming_manager:
            try:
                # Get content preview for enhanced updates
                content_preview = await self._content_streaming_manager.get_content_preview(task_id)
                
                if content_preview:
                    # Content streaming handled by Redis pub/sub instead of WebSocket
                    logger.debug(f"Content streaming update available for task {task_id}")
                
            except Exception as e:
                logger.error(f"Failed to broadcast content streaming update: {e}")
    
    async def _send_immediate_message(self, task_id: str, message):
        """Send immediate SSE message for instant user feedback (Phase 1 Foundation)."""
        try:
            if self._redis_manager:
                # Convert SSE message to dict for Redis broadcast
                message_data = message.to_dict()
                
                # Publish immediate message to SSE channel
                await self._redis_manager.publish_immediate_message(task_id, message_data)
                
                logger.debug(f"Sent immediate message for task {task_id}: {message.message_type}")
            
        except Exception as e:
            logger.error(f"Failed to send immediate message for task {task_id}: {e}")
    
    async def _get_db_connection(self):
        """Get database connection with proper pool management for task operations."""
        import os
        import asyncpg
        
        # Use a class-level connection pool to avoid connection conflicts
        if not hasattr(self.__class__, '_connection_pool') or self.__class__._connection_pool is None:
            try:
                database_url = os.getenv('DATABASE_URL')
                if not database_url:
                    raise Exception("No DATABASE_URL found in environment")
                
                # Create connection pool optimized for task management operations
                self.__class__._connection_pool = await asyncpg.create_pool(
                    database_url,
                    min_size=1,
                    max_size=3,
                    command_timeout=30,
                    max_inactive_connection_lifetime=60,
                    max_queries=1000,
                    statement_cache_size=0,  # Disable prepared statements for pgbouncer compatibility
                    server_settings={
                        'application_name': 'bloggen_task_manager'
                    }
                )
                
                # Test connection
                async with self.__class__._connection_pool.acquire() as conn:
                    await conn.execute('SELECT 1')
                
                logger.info("✅ Task manager database connection pool established")
                
            except Exception as e:
                logger.error(f"❌ Failed to create task manager database pool: {e}")
                self.__class__._connection_pool = None
                raise Exception(f"Failed to get database connection: {e}")
        
        return self.__class__._connection_pool
    
    async def create_task(self, task_id: str, user_id: str, topic: str, instructions: Optional[str] = None) -> Dict[str, Any]:
        """Create a new task in the database."""
        try:
            pool = await self._get_db_connection()
            async with pool.acquire() as conn:
                # Check if blog already exists, if not create it
                existing_blog = await conn.fetchrow("SELECT id FROM blogs WHERE id = $1", task_id)
                
                if not existing_blog:
                    # Create new blog entry
                    await conn.execute("""
                        INSERT INTO blogs (id, user_id, topic, instructions, status, progress, current_step, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """, task_id, user_id, topic, instructions, BlogStatus.QUEUED.value, 0, "Queued for processing", datetime.utcnow(), datetime.utcnow())
                    logger.info(f"✅ Created new blog entry for task {task_id}")
                else:
                    # Update existing blog entry with initial task state
                    await conn.execute("""
                        UPDATE blogs 
                        SET status = $1, progress = $2, current_step = $3, updated_at = $4
                        WHERE id = $5 AND user_id = $6
                    """, BlogStatus.QUEUED.value, 0, "Queued for processing", datetime.utcnow(), task_id, user_id)
                    logger.info(f"✅ Updated existing blog entry for task {task_id}")
                
                # Return task state
                task_state = {
                    'id': task_id,
                    'user_id': user_id,
                    'topic': topic,
                    'instructions': instructions,
                    'status': TaskStatus.QUEUED,
                    'progress': 0,
                    'current_step': 'Queued for processing',
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat(),
                    'error': None,
                    'result': None,
                    'hero_image_url': None
                }
                
                # Send immediate task created message for instant feedback
                await self._send_immediate_message(task_id, create_task_created_message(
                    task_id=task_id,
                    message=f"Blog generation task created successfully: {topic[:50] if topic else 'Auto-generating topic'}..."
                ))
                
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
            if 'status' in updates:
                updates['status'] = self._status_mapping.get(updates['status'], updates['status'])
            
            # Build dynamic update query
            set_clauses = []
            values = []
            param_count = 1
            
            for key, value in updates.items():
                if key in ['status', 'progress', 'current_step', 'error', 'content', 'hero_image_url']:
                    db_key = 'current_step' if key == 'current_step' else key
                    if key == 'hero_image_url':
                        db_key = 'hero_image_url'
                    
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
            import threading
            import redis
            import os
            
            # Debug logging
            logger.info(f"🔍 DEBUG: update_task_redis_only called for task {task_id}")
            logger.info(f"🔍 DEBUG: status_data keys: {list(status_data.keys())}")
            logger.info(f"🔍 DEBUG: message_type: {status_data.get('message_type', 'unknown')}")
            
            # Extract update information from status data
            message = status_data.get('message', 'Processing...')
            progress = status_data.get('progress', 0.0)
            message_type = status_data.get('message_type', 'status')
            
            # Use sync Redis client for thread-safe operations
            try:
                # Create sync Redis connection for thread-safe publishing
                redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
                sync_redis = redis.from_url(redis_url, decode_responses=True)
                
                # Create message for immediate SSE broadcasting - preserve original message type
                immediate_message = {
                    'message_type': message_type,  # Preserve the original message type (agentthinking, toolcall, etc.)
                    'task_id': task_id,
                    'status': 'in_progress',
                    'message': message,
                    'progress': progress,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                # Add enhanced message fields if present
                for field in ['agent_name', 'thought', 'tool_name', 'input_summary', 'content_type', 'finding', 'source']:
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
                            message_type=message_type
                        )
                        
                        # Add to buffer in Redis
                        buffer_key = f"message_buffer:{task_id}"
                        existing_data_raw = sync_redis.get(buffer_key)
                        if existing_data_raw:
                            buffer_data = json.loads(str(existing_data_raw))
                        else:
                            buffer_data = {"messages": []}
                        
                        buffer_data["messages"].append(buffered_msg.to_dict())
                        sync_redis.setex(buffer_key, 1800, json.dumps(buffer_data))  # 30 min TTL
                        
                        logger.info(f"📦 BUFFERED: {message_type} message for task {task_id} (buffer active)")
                        return  # Don't publish to Redis, message is buffered
                    else:
                        logger.info(f"📡 DIRECT: No buffer active for task {task_id}, publishing directly")
                except Exception as buffer_err:
                    logger.warning(f"⚠️ Buffer check failed for task {task_id}, proceeding with direct publish: {buffer_err}")
                
                # Publish to task-specific channel for SSE (if not buffered)
                task_channel = f"task_updates:{task_id}"
                sync_redis.publish(task_channel, json.dumps(immediate_message))
                
                # Cache task status in Redis for SSE recovery (keep numbers as numbers)
                status_key = f"task_status:{task_id}"
                status_data = {
                    'current_step': message,
                    'progress': progress,  # Keep as number, not string
                    'status': 'IN_PROGRESS',
                    'updated_at': datetime.utcnow().isoformat(),
                    'message_type': message_type
                }
                
                # Store as JSON string to match redis_manager.py pattern
                sync_redis.setex(status_key, 86400, json.dumps(status_data))
                
                logger.info(f"✅ Redis-only update for task {task_id}: {message} ({progress:.1f}%)")
                
            except Exception as redis_error:
                logger.error(f"Redis update failed for task {task_id}: {redis_error}")
                # Graceful degradation - continue without Redis updates
                logger.info(f"📊 {task_id}: {message} ({progress:.1f}%) - Redis unavailable, continuing...")
            
        except Exception as e:
            logger.error(f"❌ Failed to send Redis-only update for task {task_id}: {e}")
    
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task state from the database."""
        try:
            pool = await self._get_db_connection()
            
            async with pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT id, user_id, topic, instructions, status, progress, current_step,
                           error, content, hero_image_url, created_at, updated_at, completed_at
                    FROM blogs 
                    WHERE id = $1
                """, task_id)
                
                if not result:
                    return None
                
                return dict(result)
                
        except Exception as e:
            logger.error(f"❌ Failed to get task {task_id}: {e}")
            raise
    
    async def get_user_tasks(self, user_id: str, status: Optional[TaskStatus] = None) -> List[Dict[str, Any]]:
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
    
    async def complete_task(self, task_id: str, content: str, hero_image_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Mark task as completed with final content."""
        
        # THEORY 3 TEST: Track multiple completion calls
        import traceback
        call_stack = traceback.format_stack()
        caller_info = [line for line in call_stack[-3:-1]]  # Get calling context
        
        logger.warning(f"🚨 COMPLETION CALL #{hash(call_stack[-2]) % 1000} for task {task_id}")
        logger.warning(f"   📞 Called from: {caller_info}")
        logger.warning(f"   📊 Content length: {len(content) if content else 0}")
        logger.warning(f"   📋 Content preview: {content[:100] if content else '❌ EMPTY'}...")
        
        # CRITICAL DEBUG: Enhanced logging for content tracking
        logger.info(f"🔍 TASK_MANAGER complete_task received:")
        logger.info(f"   task_id: {task_id}")
        logger.info(f"   content length: {len(content) if content else 0}")
        logger.info(f"   content type: {type(content)}")
        logger.info(f"   content is_empty: {not content or not content.strip()}")
        logger.info(f"   content preview: {content[:300] if content else 'EMPTY CONTENT RECEIVED'}...")
        logger.info(f"   hero_image_url: {hero_image_url}")
        
        # THEORY 3 TEST: Check if task is already completed
        current_task = await self.get_task(task_id)
        if current_task and current_task.get('status') == TaskStatus.COMPLETED:
            logger.error(f"🚨 DOUBLE COMPLETION DETECTED! Task {task_id} already completed")
            logger.error(f"   Previous completion: {current_task.get('current_step', 'unknown')}")
            logger.error(f"   Previous content length: {len(current_task.get('content', '')) if current_task.get('content') else 0}")
            logger.error(f"   New content length: {len(content) if content else 0}")
            logger.error(f"   This is likely the root cause of '0 words' issue!")
            # Don't return early - let's see what happens with multiple completions
        
        updates = {
            'status': TaskStatus.COMPLETED,
            'progress': 100,
            'current_step': 'Blog generation completed successfully!',
            'content': content
        }
        
        if hero_image_url:
            updates['hero_image_url'] = hero_image_url
        
        # Also set completed_at timestamp
        try:
            pool = await self._get_db_connection()
            async with pool.acquire() as conn:
                await conn.execute("""
                    UPDATE blogs 
                    SET completed_at = $1
                    WHERE id = $2
                """, datetime.utcnow(), task_id)
        except Exception as e:
            logger.warning(f"Failed to set completed_at for task {task_id}: {e}")
        
        # Update database first
        task_result = await self.update_task(task_id, **updates)
        
        # CRITICAL DEBUG: Check why completion message isn't being sent
        logger.info(f"🔍 DEBUG complete_task - redis_manager: {self._redis_manager is not None}, task_result: {task_result is not None}")
        
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
                
                logger.warning(f"🔍 REDIS SEQUENCE #{sequence_id} - ENHANCED COMPLETION PROTOCOL START:")
                logger.warning(f"   task_id: {task_id}")
                logger.warning(f"   content length: {len(content) if content else 0}")
                logger.warning(f"   content preview: {content[:200] if content else 'NO CONTENT TO SEND'}...")
                logger.warning(f"   timestamp: {timestamp}")
                
                # Use sync Redis to match the pattern from send_redis_only_update method
                sync_redis = redis.Redis.from_url(
                    self._redis_manager.redis_url,
                    encoding='utf-8',
                    decode_responses=True
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
                    "hero_image_url": hero_image_url
                }
                
                logger.warning(f"🔍 REDIS SEQUENCE #{sequence_id} - PHASE 1: SENDING COMPLETION_PENDING:")
                logger.warning(f"   completion_pending keys: {list(completion_pending_message.keys())}")
                logger.warning(f"   final_content length: {len(completion_pending_message['final_content']) if completion_pending_message['final_content'] else 0}")
                
                sync_redis.publish(task_channel, json.dumps(completion_pending_message))
                logger.warning(f"✅ REDIS SEQUENCE #{sequence_id} - PHASE 1: COMPLETION_PENDING PUBLISHED to {task_channel}")
                
                # PHASE 2: Wait for acknowledgment from frontend
                logger.info(f"⏳ PHASE 2: Waiting for completion acknowledgment for {task_id}")
                ack_received = await self._redis_manager.wait_for_completion_acknowledgment(task_id, timeout=30)
                
                # PHASE 3: Send final confirmation based on acknowledgment
                if ack_received:
                    # Send completion_confirmed message
                    confirmation_message = {
                        "message_type": "completion_confirmed",
                        "task_id": task_id,
                        "message": "Blog generation confirmed and delivered",
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "completion_confirmed"
                    }
                    
                    sync_redis.publish(task_channel, json.dumps(confirmation_message))
                    logger.warning(f"✅ REDIS SEQUENCE #{sequence_id} - PHASE 3: COMPLETION_CONFIRMED sent for {task_id}")
                    
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
                        "hero_image_url": hero_image_url
                    }
                    
                    sync_redis.publish(task_channel, json.dumps(timeout_message))
                    logger.warning(f"⏰ REDIS SEQUENCE #{sequence_id} - PHASE 3: COMPLETION_TIMEOUT sent for {task_id} (no ack received)")
                
                logger.warning(f"🏁 REDIS SEQUENCE #{sequence_id} - ENHANCED COMPLETION PROTOCOL COMPLETE for {task_id}")
                
            except Exception as e:
                logger.error(f"❌ Failed to send completion message for task {task_id}: {e}")
                import traceback
                logger.error(f"❌ Completion message traceback: {traceback.format_exc()}")
        else:
            logger.error(f"❌ Cannot send completion message - redis_manager: {self._redis_manager is not None}, task_result: {task_result is not None}")
        
        return task_result
    
    async def fail_task(self, task_id: str, error_message: str) -> Optional[Dict[str, Any]]:
        """Mark task as failed with error message."""
        return await self.update_task(
            task_id,
            status=TaskStatus.FAILED,
            current_step=f'Error: {error_message}',
            error=error_message
        )
    
    async def delete_task(self, task_id: str, user_id: str) -> bool:
        """Delete a task/blog from the database with S3 image cleanup."""
        try:
            pool = await self._get_db_connection()
            
            async with pool.acquire() as conn:
                # First check if the task exists and belongs to the user, and get image data
                existing_task = await conn.fetchrow("""
                    SELECT id, user_id, status, content, hero_image_url FROM blogs 
                    WHERE id = $1 AND user_id = $2
                """, task_id, user_id)
                
                if not existing_task:
                    logger.warning(f"Task {task_id} not found or doesn't belong to user {user_id}")
                    return False
                
                # Enqueue S3 cleanup asynchronously (non-blocking)
                try:
                    from .s3_cleanup_queue import get_cleanup_queue
                    
                    cleanup_queue = await get_cleanup_queue()
                    await cleanup_queue.enqueue_cleanup(
                        blog_id=task_id,
                        user_id=user_id,
                        content=existing_task['content'],
                        hero_image_url=existing_task['hero_image_url']
                    )
                    logger.info(f"Enqueued S3 cleanup for blog {task_id}")
                    
                except Exception as cleanup_error:
                    # S3 cleanup failure should not prevent blog deletion
                    logger.error(f"Failed to enqueue S3 cleanup for blog {task_id}: {cleanup_error}")
                
                # Delete the task from database (proceeds regardless of S3 cleanup status)
                result = await conn.execute("""
                    DELETE FROM blogs 
                    WHERE id = $1 AND user_id = $2
                """, task_id, user_id)
                
                if result == "DELETE 1":
                    logger.info(f"✅ Deleted task {task_id} for user {user_id} (S3 cleanup in progress)")
                    
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
                await self._content_streaming_manager.stream_research_finding(task_id, finding)
                logger.debug(f"Streamed research finding for task {task_id}")
            except Exception as e:
                logger.error(f"Failed to stream research finding: {e}")
    
    async def stream_content_paragraph(self, task_id: str, paragraph: str):
        """Stream a content paragraph for progressive content updates."""
        if self._content_streaming_manager:
            try:
                await self._content_streaming_manager.stream_content_paragraph(task_id, paragraph)
                logger.debug(f"Streamed content paragraph for task {task_id}")
            except Exception as e:
                logger.error(f"Failed to stream content paragraph: {e}")
    
    async def stream_fact_correction(self, task_id: str, correction: str):
        """Stream a fact correction for progressive content updates."""
        if self._content_streaming_manager:
            try:
                await self._content_streaming_manager.stream_fact_correction(task_id, correction)
                logger.debug(f"Streamed fact correction for task {task_id}")
            except Exception as e:
                logger.error(f"Failed to stream fact correction: {e}")
    
    async def stream_final_content(self, task_id: str, final_content: str):
        """Stream the final complete content."""
        if self._content_streaming_manager:
            try:
                await self._content_streaming_manager.stream_final_content(task_id, final_content)
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
        content = re.sub(r'^#+\s+', '', content, flags=re.MULTILINE)
        # Remove markdown links [text](url)
        content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
        # Remove markdown images ![alt](url)
        content = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', '', content)
        # Remove markdown bold/italic
        content = re.sub(r'\*\*([^\*]+)\*\*', r'\1', content)
        content = re.sub(r'\*([^\*]+)\*', r'\1', content)
        # Remove markdown code blocks
        content = re.sub(r'```[^`]*```', '', content, flags=re.DOTALL)
        content = re.sub(r'`([^`]+)`', r'\1', content)
        
        # Split by whitespace and count non-empty words
        words = [word.strip() for word in content.split() if word.strip()]
        return len(words)

# Global instance
task_manager = TaskManager()
