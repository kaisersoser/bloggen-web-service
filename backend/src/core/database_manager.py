"""
Database Connection Manager for Audit Tracking

Handles PostgreSQL connection pooling and basic database operations.
Follows Single Responsibility Principle - only manages database connectivity.
"""

import asyncpg
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DatabaseConnectionManager:
    """Manages PostgreSQL connection pools for audit tracking."""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.database_enabled = False

    async def get_connection_pool(self) -> Optional[asyncpg.Pool]:
        """Get or create database connection pool."""
        if self.pool:
            return self.pool

        return await self._create_connection_pool()

    async def _create_connection_pool(self) -> Optional[asyncpg.Pool]:
        """Create new database connection pool."""
        try:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                logger.warning("No DATABASE_URL found - database audit disabled")
                return None

            self.pool = await asyncpg.create_pool(
                database_url,
                min_size=0,  # No minimum connections
                max_size=1,  # Single connection for pgbouncer
                command_timeout=30,
                max_inactive_connection_lifetime=60,
                statement_cache_size=0,  # Disable prepared statements for pgbouncer compatibility
                server_settings={"application_name": "bloggen_database_manager"},
            )

            # Test connection
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")

            self.database_enabled = True
            logger.info("✅ Database connection established")
            return self.pool

        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            self.database_enabled = False
            return None

    async def close(self):
        """Close database connection pool."""
        if self.pool:
            try:
                await self.pool.close()
                logger.info("📥 Database connection pool closed")
            except Exception as e:
                logger.error(f"❌ Error closing database pool: {e}")

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
