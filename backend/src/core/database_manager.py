"""
Database Connection Manager for Audit Tracking

DEPRECATED: This module is now a thin wrapper around the centralized DatabaseService.
Use `from core.database_service import database_service` directly instead.

Migration: Phase 3.1 - Unified Database Service
"""

import asyncpg
import logging
from typing import Optional
from core.database_service import database_service

logger = logging.getLogger(__name__)


class DatabaseConnectionManager:
    """
    DEPRECATED: Wrapper around centralized DatabaseService.
    
    This class now delegates to the shared database_service instance.
    Direct usage of database_service is preferred for new code.
    """

    def __init__(self):
        self.database_enabled = database_service.is_initialized()

    async def get_connection_pool(self) -> Optional[asyncpg.Pool]:
        """Get the centralized connection pool."""
        try:
            return await database_service.ensure_pool()
        except RuntimeError:
            logger.warning("DatabaseService not initialized - database audit disabled")
            return None

    async def _create_connection_pool(self) -> Optional[asyncpg.Pool]:
        """DEPRECATED: Connection pool is now managed centrally."""
        return await self.get_connection_pool()

    @property
    def pool(self) -> Optional[asyncpg.Pool]:
        """Access the centralized pool (synchronous property)."""
        if database_service.is_initialized():
            return database_service._pool
        return None

    async def close(self):
        """DEPRECATED: Pool lifecycle managed by FastAPI lifespan."""
        logger.debug("DatabaseConnectionManager.close() called - pool managed centrally")

    async def ensure_tables_exist(self, conn):
        """Ensure required audit tables exist."""
        try:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS llm_calls (
                    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
                    audit_session_id TEXT NOT NULL REFERENCES audit_sessions(id) ON DELETE CASCADE,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    input_cost DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    output_cost DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    total_cost DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    phase TEXT,
                    agent_role TEXT,
                    call_type TEXT NOT NULL DEFAULT 'actual',
                    timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """
            )
            logger.debug("✅ LLM calls table ensured")
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
