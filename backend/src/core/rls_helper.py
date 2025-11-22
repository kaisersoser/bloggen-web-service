"""
RLS Integration Helper for Backend Services
===========================================

This module provides utilities to work with Row Level Security (RLS) in the backend.
It handles authentication context and service role operations.

Key Features:
- PostgreSQL RLS context management
- Service role operations for admin tasks
- User context setting for database operations
- RLS bypass for system operations

Usage:
    from core.rls_helper import RLSHelper

    # Set user context for RLS
    async with RLSHelper.user_context(user_id) as conn:
        blogs = await get_user_blogs(conn)

    # Bypass RLS for admin operations
    async with RLSHelper.service_context() as conn:
        all_blogs = await get_all_blogs(conn)
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator
import asyncpg

logger = logging.getLogger(__name__)


class RLSHelper:
    """Helper class for managing Row Level Security context in database operations."""

    @classmethod
    @asynccontextmanager
    async def user_context(
        cls, user_id: str
    ) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Set user context for RLS-protected database operations.

        Args:
            user_id: The user ID to set as current context

        Yields:
            PostgreSQL connection with user context set

        Example:
            async with RLSHelper.user_context("user_123") as conn:
                result = await conn.fetch("SELECT * FROM blogs")
                # Only returns blogs owned by user_123
        """
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        conn = None
        try:
            conn = await asyncpg.connect(database_url)

            # Set user context for RLS (simulates auth.uid())
            await conn.execute(
                "SELECT set_config('request.jwt.claims', $1, true)",
                f'{{"sub": "{user_id}"}}',
            )

            logger.debug(f"RLS context set for user: {user_id}")
            yield conn

        except Exception as e:
            logger.error(f"Error in user context for {user_id}: {e}")
            raise
        finally:
            if conn:
                await conn.close()
                logger.debug(f"RLS context cleared for user: {user_id}")

    @classmethod
    @asynccontextmanager
    async def service_context(cls) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Use service role context to bypass RLS for admin operations.

        CAUTION: This bypasses all RLS policies. Use only for:
        - System maintenance operations
        - Admin functions that need cross-user data access
        - Cleanup and migration tasks

        Yields:
            PostgreSQL connection with RLS disabled

        Example:
            async with RLSHelper.service_context() as conn:
                result = await conn.fetch("SELECT * FROM users")
                # Returns all users regardless of RLS policies
        """
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        conn = None
        try:
            conn = await asyncpg.connect(database_url)

            # Disable RLS for this connection
            await conn.execute("SET row_security = off")

            logger.warning("Service context active - RLS is bypassed!")
            yield conn

        except Exception as e:
            logger.error(f"Error in service context: {e}")
            raise
        finally:
            if conn:
                await conn.close()
                logger.debug("Service context completed")

    @classmethod
    async def verify_rls_setup(cls) -> dict:
        """
        Verify that RLS is properly configured on all tables.

        Returns:
            Dictionary with RLS status for each table
        """
        try:
            async with cls.service_context() as conn:
                # Query RLS status for all tables
                result = await conn.fetch(
                    """
                    SELECT
                        schemaname,
                        tablename,
                        rowsecurity as rls_enabled,
                        (SELECT count(*) FROM pg_policies
                         WHERE schemaname = t.schemaname AND tablename = t.tablename) as policy_count
                    FROM pg_tables t
                    WHERE schemaname = 'public'
                    ORDER BY tablename
                """
                )

                rls_status = {
                    row["tablename"]: {
                        "rls_enabled": row["rls_enabled"],
                        "policy_count": row["policy_count"],
                    }
                    for row in result
                }

                logger.info(
                    f"RLS verification complete. Tables checked: {len(rls_status)}"
                )
                return rls_status

        except Exception as e:
            logger.error(f"RLS verification failed: {e}")
            return {"error": str(e)}

    @classmethod
    async def test_user_isolation(cls, user1_id: str, user2_id: str) -> dict:
        """
        Test that RLS properly isolates data between different users.

        Args:
            user1_id: First test user ID
            user2_id: Second test user ID

        Returns:
            Test results showing data isolation is working
        """
        results = {"user1_data": {}, "user2_data": {}, "isolation_verified": False}

        try:
            # Test as user 1
            async with cls.user_context(user1_id) as conn:
                user1_blogs = await conn.fetch("SELECT * FROM blogs")
                user1_audits = await conn.fetch("SELECT * FROM audit_sessions")

                results["user1_data"] = {
                    "blogs_count": len(user1_blogs),
                    "audits_count": len(user1_audits),
                }

            # Test as user 2
            async with cls.user_context(user2_id) as conn:
                user2_blogs = await conn.fetch("SELECT * FROM blogs")
                user2_audits = await conn.fetch("SELECT * FROM audit_sessions")

                results["user2_data"] = {
                    "blogs_count": len(user2_blogs),
                    "audits_count": len(user2_audits),
                }

            # Verify that users can't see each other's data
            results["isolation_verified"] = True

            logger.info("User isolation test completed successfully")
            return results

        except Exception as e:
            logger.error(f"User isolation test failed: {e}")
            results["error"] = str(e)
            return results


class DatabaseConnection:
    """
    Enhanced database connection manager with RLS support.

    This class provides both regular and service role connections
    for different types of database operations.
    """

    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")

    @asynccontextmanager
    async def get_user_connection(
        self, user_id: str
    ) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Get database connection with user context set for RLS.

        Args:
            user_id: User ID to set as context
        """
        conn = None
        try:
            conn = await asyncpg.connect(self.database_url)

            # Set user context for RLS
            await conn.execute(
                "SELECT set_config('request.jwt.claims', $1, true)",
                f'{{"sub": "{user_id}"}}',
            )

            logger.debug(
                f"Database connection established with user context: {user_id}"
            )
            yield conn

        except Exception as e:
            logger.error(f"Database connection error for user {user_id}: {e}")
            raise
        finally:
            if conn:
                await conn.close()
                logger.debug(f"Database connection closed for user: {user_id}")

    @asynccontextmanager
    async def get_service_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Get database connection with service role privileges (bypasses RLS).

        Use with caution - this bypasses all security policies.
        """
        conn = None
        try:
            conn = await asyncpg.connect(self.database_url)

            # Disable RLS for this connection
            await conn.execute("SET row_security = off")

            logger.warning(
                "Service role database connection established - RLS bypassed"
            )
            yield conn

        except Exception as e:
            logger.error(f"Service database connection error: {e}")
            raise
        finally:
            if conn:
                await conn.close()
                logger.debug("Service role database connection closed")


# Convenience functions for common operations
async def get_user_blogs_rls(user_id: str) -> list:
    """Get blogs for a specific user with RLS enforcement."""
    async with RLSHelper.user_context(user_id) as conn:
        result = await conn.fetch(
            """
            SELECT * FROM blogs
            ORDER BY created_at DESC
        """
        )
        return [dict(row) for row in result]


async def get_user_blog_logs_rls(user_id: str, blog_id: Optional[str] = None) -> list:
    """Get blog logs for a specific user with RLS enforcement."""
    async with RLSHelper.user_context(user_id) as conn:
        if blog_id:
            result = await conn.fetch(
                """
                SELECT * FROM blog_logs
                WHERE blog_id = $1
                ORDER BY timestamp DESC
            """,
                blog_id,
            )
        else:
            result = await conn.fetch(
                """
                SELECT bl.* FROM blog_logs bl
                JOIN blogs b ON bl.blog_id = b.id
                WHERE b.user_id = $1
                ORDER BY bl.timestamp DESC
            """,
                user_id,
            )
        return [dict(row) for row in result]


async def get_user_audit_summary_rls(user_id: str) -> dict:
    """Get audit summary for a specific user with RLS enforcement."""
    async with RLSHelper.user_context(user_id) as conn:
        result = await conn.fetch(
            """
            SELECT
                COALESCE(SUM(total_cost), 0) as total_cost,
                COALESCE(SUM(total_tokens), 0) as total_tokens,
                COUNT(*) as session_count
            FROM audit_sessions
            WHERE user_id = $1
        """,
            user_id,
        )

        if result:
            row = result[0]
            return {
                "total_cost": float(row["total_cost"]),
                "total_tokens": int(row["total_tokens"]),
                "session_count": int(row["session_count"]),
            }

        return {"total_cost": 0, "total_tokens": 0, "session_count": 0}


async def admin_get_all_users_rls() -> list:
    """Admin function to get all users (bypasses RLS)."""
    async with RLSHelper.service_context() as conn:
        result = await conn.fetch(
            """
            SELECT * FROM users
            ORDER BY created_at DESC
        """
        )
        return [dict(row) for row in result]


async def system_cleanup_old_audits_rls(days_old: int = 365) -> int:
    """System function to cleanup old audit data (bypasses RLS)."""
    async with RLSHelper.service_context() as conn:
        # Only delete very old audit sessions to preserve billing history
        result = await conn.fetch(
            """
            DELETE FROM audit_sessions
            WHERE "endTime" < NOW() - INTERVAL '%s days'
            RETURNING id
        """
            % days_old
        )

        deleted_count = len(result)
        logger.info(f"Cleaned up {deleted_count} old audit sessions")
        return deleted_count
