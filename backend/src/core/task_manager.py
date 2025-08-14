"""
Task Manager for database-backed task state management.

Replaces the in-memory active_tasks dictionary with persistent database storage.
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

# Global instance
task_manager = TaskManager()
