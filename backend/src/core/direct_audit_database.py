"""
Direct Supabase Database Integration for Audit Logging

Phase 3.1 Migration: This module now uses the centralized DatabaseService
instead of creating its own connection pool.
"""

import asyncpg
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

from core.common import get_logger, config
from core.database_service import database_service

logger = get_logger(__name__)


class DirectSupabaseAuditManager:
    """
    Direct PostgreSQL connection to Supabase for audit logging.

    Phase 3.1: Now uses centralized DatabaseService for connection pooling.
    """

    def __init__(self):
        """Initialize direct Supabase connection"""
        self.logger = get_logger(__name__)
        self.pool = None
        self.enabled = True

    async def initialize(self):
        """
        Initialize database connection using centralized DatabaseService.
        
        Phase 3.1 Migration: Delegates to shared pool instead of creating
        a separate direct_audit-specific pool.
        """
        try:
            # Use centralized database service
            self.pool = await database_service.ensure_pool()
            self.enabled = True

            # Test connection and ensure tables exist
            await self._ensure_tables_exist()

            self.logger.info("✅ Direct Supabase audit system initialized (using centralized pool)")

        except RuntimeError:
            self.logger.warning("DatabaseService not initialized - audit logging disabled")
            self.enabled = False
        except Exception as e:
            self.logger.error(
                f"❌ Failed to initialize direct database connection: {e}"
            )
            self.enabled = False

    async def _ensure_tables_exist(self):
        """Ensure required audit tables exist"""
        if not self.pool:
            return

        create_sessions_table = """
        CREATE TABLE IF NOT EXISTS audit_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_type VARCHAR(100) NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            blog_id VARCHAR(255),
            start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            end_time TIMESTAMP WITH TIME ZONE,
            total_cost DECIMAL(10, 6) DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """

        create_llm_calls_table = """
        CREATE TABLE IF NOT EXISTS audit_llm_calls (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID REFERENCES audit_sessions(id) ON DELETE CASCADE,
            model VARCHAR(100) NOT NULL,
            call_type VARCHAR(50) NOT NULL,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            total_tokens INTEGER NOT NULL,
            cost DECIMAL(10, 6) NOT NULL,
            phase VARCHAR(100),
            agent_role VARCHAR(100),
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """

        create_indexes = """
        CREATE INDEX IF NOT EXISTS idx_audit_sessions_user_id ON audit_sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_audit_sessions_blog_id ON audit_sessions(blog_id);
        CREATE INDEX IF NOT EXISTS idx_audit_sessions_start_time ON audit_sessions(start_time);
        CREATE INDEX IF NOT EXISTS idx_audit_llm_calls_session_id ON audit_llm_calls(session_id);
        CREATE INDEX IF NOT EXISTS idx_audit_llm_calls_model ON audit_llm_calls(model);
        CREATE INDEX IF NOT EXISTS idx_audit_llm_calls_timestamp ON audit_llm_calls(timestamp);
        """

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(create_sessions_table)
                await conn.execute(create_llm_calls_table)
                await conn.execute(create_indexes)

            self.logger.info("✅ Audit database tables verified/created")

        except Exception as e:
            self.logger.error(f"❌ Failed to ensure audit tables exist: {e}")
            raise

    async def create_audit_session(
        self,
        session_type: str,
        user_id: str,
        blog_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Create new audit session directly in database.

        Returns:
            Session ID if successful, None if audit disabled
        """
        if not self.enabled or not self.pool:
            return None

        try:
            session_id = str(uuid.uuid4())

            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO audit_sessions
                    (id, session_type, user_id, blog_id, metadata, start_time)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    session_id,
                    session_type,
                    user_id,
                    blog_id,
                    metadata or {},
                    datetime.utcnow(),
                )

            self.logger.info(f"✅ Created audit session: {session_id} ({session_type})")
            return session_id

        except Exception as e:
            self.logger.error(f"❌ Failed to create audit session: {e}")
            return None

    async def log_llm_call(
        self,
        session_id: str,
        model: str,
        call_type: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        phase: Optional[str] = None,
        agent_role: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Log LLM API call directly to database.

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.pool:
            return False

        try:
            total_tokens = input_tokens + output_tokens

            async with self.pool.acquire() as conn:
                # Insert the LLM call record
                await conn.execute(
                    """
                    INSERT INTO audit_llm_calls
                    (session_id, model, call_type, input_tokens, output_tokens,
                     total_tokens, cost, phase, agent_role, metadata, timestamp)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    """,
                    session_id,
                    model,
                    call_type,
                    input_tokens,
                    output_tokens,
                    total_tokens,
                    cost,
                    phase,
                    agent_role,
                    metadata or {},
                    datetime.utcnow(),
                )

                # Update session totals
                await conn.execute(
                    """
                    UPDATE audit_sessions
                    SET total_cost = total_cost + $2,
                        total_tokens = total_tokens + $3,
                        updated_at = NOW()
                    WHERE id = $1
                    """,
                    session_id,
                    cost,
                    total_tokens,
                )

            self.logger.info(
                f"💰 Logged LLM call: {model} ({call_type}) - ${cost:.6f} "
                f"({total_tokens} tokens) to session {session_id}"
            )
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to log LLM call: {e}")
            return False

    async def end_audit_session(self, session_id: str) -> bool:
        """
        Mark audit session as completed.

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.pool:
            return False

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE audit_sessions
                    SET end_time = NOW(), updated_at = NOW()
                    WHERE id = $1
                    """,
                    session_id,
                )

            self.logger.info(f"✅ Ended audit session: {session_id}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to end audit session: {e}")
            return False

    async def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for an audit session"""
        if not self.enabled or not self.pool:
            return None

        try:
            async with self.pool.acquire() as conn:
                # Get session info
                session = await conn.fetchrow(
                    """
                    SELECT * FROM audit_sessions WHERE id = $1
                    """,
                    session_id,
                )

                if not session:
                    return None

                # Get call count by model
                calls = await conn.fetch(
                    """
                    SELECT model, COUNT(*) as call_count,
                           SUM(total_tokens) as total_tokens,
                           SUM(cost) as total_cost
                    FROM audit_llm_calls
                    WHERE session_id = $1
                    GROUP BY model
                    """,
                    session_id,
                )

                return {
                    "session": dict(session),
                    "calls_by_model": [dict(call) for call in calls],
                }

        except Exception as e:
            self.logger.error(f"❌ Failed to get session stats: {e}")
            return None

    async def close(self):
        """
        Clear pool reference (DO NOT close the shared pool).
        
        Phase 3.1: This pool is managed by database_service and shared across
        the application. It should only be closed during application shutdown.
        """
        if self.pool:
            self.logger.debug("Clearing direct audit manager pool reference (shared pool remains open)")
            self.pool = None
            # REMOVED: await self.pool.close()  # This was closing the shared pool!


# Global instance
_direct_audit_manager = None


async def get_direct_audit_manager() -> DirectSupabaseAuditManager:
    """Get or create the global direct audit manager instance"""
    global _direct_audit_manager

    if _direct_audit_manager is None:
        _direct_audit_manager = DirectSupabaseAuditManager()
        await _direct_audit_manager.initialize()

    return _direct_audit_manager
