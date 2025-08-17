"""
Task Manager for database-backed task state management.

Replaces the in-memory active_tasks dictionary with persistent database storage.
Integrates with WebSocket manager and Redis pub/sub for real-time updates.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from enum import Enum

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
    
    def __init__(self):
        self._status_mapping = {
            TaskStatus.QUEUED: BlogStatus.QUEUED,
            TaskStatus.IN_PROGRESS: BlogStatus.IN_PROGRESS,
            TaskStatus.COMPLETED: BlogStatus.COMPLETED,
            TaskStatus.FAILED: BlogStatus.FAILED,
        }
        self._subscribers: Dict[str, List[Callable]] = {}
        self._websocket_manager = None
        self._redis_manager = None
        self._content_streaming_manager = None
    
    def set_websocket_manager(self, websocket_manager):
        """Set the WebSocket manager for real-time updates."""
        self._websocket_manager = websocket_manager
    
    def set_redis_manager(self, redis_manager):
        """Set the Redis manager for pub/sub updates."""
        self._redis_manager = redis_manager
    
    def set_content_streaming_manager(self, content_streaming_manager):
        """Set the content streaming manager for progressive content updates."""
        self._content_streaming_manager = content_streaming_manager
    
    async def _broadcast_task_update(self, task_id: str, task_data: Dict[str, Any]):
        """Broadcast task update via WebSocket and Redis pub/sub."""
        # WebSocket broadcast (existing functionality)
        if self._websocket_manager:
            try:
                # Import here to avoid circular imports
                from core.websocket_manager import WebSocketMessage
                
                # Prepare WebSocket message
                message = WebSocketMessage(
                    type="task_update",
                    task_id=task_id,
                    data={
                        'status': task_data.get('status', '').lower(),
                        'step': task_data.get('current_step'),
                        'progress': task_data.get('progress', 0),
                        'hero_image_url': task_data.get('hero_image_url'),
                        'content': task_data.get('content') if task_data.get('status') == 'COMPLETED' else None,
                        'error': task_data.get('error') if task_data.get('status') == 'FAILED' else None
                    }
                )
                
                # Broadcast to all connections subscribed to this task
                await self._websocket_manager.broadcast_to_task(task_id, message)
                logger.debug(f"Broadcasted WebSocket update for task {task_id}")
                
            except Exception as e:
                logger.error(f"Failed to broadcast WebSocket update: {e}")
        
        # Redis pub/sub broadcast (new functionality)
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
                    # Import here to avoid circular imports
                    from core.websocket_manager import ProgressStreamMessage
                    
                    # Send enhanced progress message with content preview
                    progress_message = ProgressStreamMessage(
                        task_id=task_id,
                        phase=task_data.get('current_step', ''),
                        progress=task_data.get('progress', 0),
                        status=task_data.get('status', '').lower(),
                        content_preview=content_preview,
                        current_section=task_data.get('current_section')
                    )
                    
                    # Broadcast enhanced progress message
                    if self._websocket_manager:
                        await self._websocket_manager.broadcast_to_task(task_id, progress_message)
                    
                    logger.debug(f"Broadcasted content streaming update for task {task_id}")
                
            except Exception as e:
                logger.error(f"Failed to broadcast content streaming update: {e}")
    
    async def _get_db_connection(self):
        """Get database connection using the existing audit tracker pattern."""
        from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker
        tracker = EnhancedDatabaseAuditTracker(session_type="task_management", user_id="system", blog_id=None)
        pool = await tracker._get_database_connection()
        if not pool:
            raise Exception("Failed to get database connection")
        return pool
    
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
                
                # Broadcast WebSocket update
                await self._broadcast_task_update(task_id, task_state)
                
                logger.info(f"✅ Updated task {task_id}: {updates}")
                return task_state
                
        except Exception as e:
            logger.error(f"❌ Failed to update task {task_id}: {e}")
            raise
    
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
        
        return await self.update_task(task_id, **updates)
    
    async def fail_task(self, task_id: str, error_message: str) -> Optional[Dict[str, Any]]:
        """Mark task as failed with error message."""
        return await self.update_task(
            task_id,
            status=TaskStatus.FAILED,
            current_step=f'Error: {error_message}',
            error=error_message
        )
    
    async def delete_task(self, task_id: str, user_id: str) -> bool:
        """Delete a task/blog from the database."""
        try:
            pool = await self._get_db_connection()
            
            async with pool.acquire() as conn:
                # First check if the task exists and belongs to the user
                existing_task = await conn.fetchrow("""
                    SELECT id, user_id, status FROM blogs 
                    WHERE id = $1 AND user_id = $2
                """, task_id, user_id)
                
                if not existing_task:
                    logger.warning(f"Task {task_id} not found or doesn't belong to user {user_id}")
                    return False
                
                # Delete the task
                result = await conn.execute("""
                    DELETE FROM blogs 
                    WHERE id = $1 AND user_id = $2
                """, task_id, user_id)
                
                if result == "DELETE 1":
                    logger.info(f"✅ Deleted task {task_id} for user {user_id}")
                    
                    # Notify subscribers about deletion
                    await self._notify_subscribers(task_id, {"deleted": True})
                    
                    # Broadcast WebSocket update about deletion
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

# Global instance
task_manager = TaskManager()
