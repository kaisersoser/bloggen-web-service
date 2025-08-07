"""
Refactored Database Audit Tracker

A clean, modular implementation following our coding principles:
- Single Responsibility: Each component has one clear purpose
- Keep It Simple: Removed over-engineering and complexity
- DRY: Eliminated duplicate code through proper separation
- Clear and Self-Documenting: Obvious intent and structure
"""

import logging
from typing import Optional, Dict, Any

from .audit_session import AuditSession
from .database_worker import DatabaseWorker

logger = logging.getLogger(__name__)


class DatabaseAuditTracker:
    """
    Simplified audit tracker that orchestrates session management and database operations.
    
    This refactored version follows our coding principles:
    - Each class has a single responsibility
    - Complex background threading is isolated
    - Database operations are centralized
    - Cost calculation logic is separated
    """
    
    # Shared database worker instance
    _db_worker: Optional[DatabaseWorker] = None
    
    def __init__(self, session_type: str, user_id: str, blog_id: Optional[str] = None):
        """Initialize audit tracker with a new session."""
        self.session = AuditSession(session_type, user_id, blog_id)
        self._ensure_database_worker()
        
        logger.info(f"🔍 Audit tracker initialized for {session_type}")
    
    @classmethod
    def _ensure_database_worker(cls):
        """Ensure database worker is running (singleton pattern)."""
        if cls._db_worker is None:
            cls._db_worker = DatabaseWorker()
            cls._db_worker.start()
    
    async def start_session(self) -> str:
        """Start the audit session."""
        if not self._db_worker:
            raise RuntimeError("Database worker not initialized")
        return await self.session.start(self._db_worker)
    
    def track_api_call(self, model: str, input_tokens: int, output_tokens: int,
                      phase: str = "unknown", agent_role: str = "unknown",
                      cost: Optional[float] = None):
        """Track an API call."""
        self.session.track_api_call(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            phase=phase,
            agent_role=agent_role,
            cost=cost,
            db_worker=self._db_worker
        )
    
    async def update_blog_id(self, blog_id: str):
        """Update the blog ID for this session."""
        if not self._db_worker:
            raise RuntimeError("Database worker not initialized")
        await self.session.update_blog_id(blog_id, self._db_worker)
    
    async def end_session(self):
        """End the audit session."""
        if not self._db_worker:
            raise RuntimeError("Database worker not initialized")
        await self.session.end(self._db_worker)
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get session summary."""
        return self.session.get_summary()
    
    # Backward compatibility methods
    def track_llm_call(self, *args, **kwargs):
        """Backward compatibility wrapper for LLM interceptor."""
        try:
            if len(args) >= 5:
                self.track_api_call(args[0], args[1], args[2], args[4], args[3])
            else:
                logger.info(f"💰 LLM Call (fallback): {args} {kwargs}")
        except Exception as e:
            logger.error(f"Failed to track LLM call: {e}")
    
    @classmethod
    async def shutdown(cls):
        """Shutdown the database worker (for cleanup)."""
        if cls._db_worker:
            cls._db_worker.stop()
            await cls._db_worker.close()
            cls._db_worker = None
            logger.info("🛑 Audit tracker shutdown complete")


# Alias for backward compatibility
EnhancedDatabaseAuditTracker = DatabaseAuditTracker
