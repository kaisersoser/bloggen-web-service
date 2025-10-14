"""Centralized database service for managing asyncpg connection pool.

This module creates a single shared connection pool for the entire backend.
It exposes helper methods for acquiring connections and running common
operations while ensuring the pool is initialized exactly once.
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable, Dict, Optional

import asyncpg

logger = logging.getLogger(__name__)


class DatabaseService:
    """Manage the lifecycle of a shared asyncpg connection pool."""

    _instance_counter = 0  # Track number of instances created

    def __init__(self) -> None:
        DatabaseService._instance_counter += 1
        self._instance_id = DatabaseService._instance_counter
        self._pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()
        self._pool_kwargs: dict[str, Any] = {}
        self._database_url: Optional[str] = None
        logger.info(f"🆕 DatabaseService instance #{self._instance_id} created (total instances: {DatabaseService._instance_counter})")

    async def initialize(
        self,
        database_url: str,
        *,
        min_size: int = 1,
        max_size: int = 10,
        command_timeout: int = 30,
        **pool_kwargs: Any,
    ) -> asyncpg.Pool:
        """Create the shared connection pool if it does not exist yet.
        
        Note: statement_cache_size=0 disables prepared statement caching to avoid
        conflicts when connections are reused from the pool. This is necessary
        when using connection pooling with asyncpg.
        """
        if self._pool is not None:
            return self._pool

        async with self._lock:
            if self._pool is not None:
                return self._pool

            self._database_url = database_url
            self._pool_kwargs = {
                "min_size": min_size,
                "max_size": max_size,
                "command_timeout": command_timeout,
                "statement_cache_size": 0,  # Disable prepared statement caching to prevent conflicts
                **pool_kwargs,
            }
            self._pool = await asyncpg.create_pool(database_url, **self._pool_kwargs)
            logger.info(f"✅ Pool created for instance #{self._instance_id}: pool_id={id(self._pool)}, min={min_size}, max={max_size}")
            return self._pool

    async def ensure_pool(self) -> asyncpg.Pool:
        """Return the existing pool or raise if `initialize` has not been called.
        
        If pool was unexpectedly set to None but connection details exist,
        attempt to recreate it (defensive recovery).
        """
        # Fast path: pool exists and is valid
        if self._pool:
            # Check if pool is closed (default to False if attribute doesn't exist)
            if getattr(self._pool, '_closed', False):
                logger.error(f"❌ Instance #{self._instance_id}: Pool is closed!")
                raise RuntimeError("DatabaseService pool has been closed")
            return self._pool
        
        # Pool is None - check if we can recreate it
        if self._database_url and self._pool_kwargs:
            logger.warning(f"⚠️  Instance #{self._instance_id}: Pool was None but connection details exist!")
            logger.warning(f"   This should NOT happen - investigating pool loss")
            logger.warning(f"   Stack trace:\n{''.join(traceback.format_stack())}")
            
            # Attempt defensive recovery
            async with self._lock:
                if self._pool is None:  # Double-check after acquiring lock
                    logger.warning(f"🔄 Instance #{self._instance_id}: Recreating pool defensively...")
                    try:
                        self._pool = await asyncpg.create_pool(
                            self._database_url,
                            **self._pool_kwargs
                        )
                        logger.info(f"✅ Pool recreated successfully: pool_id={id(self._pool)}")
                        return self._pool
                    except Exception as e:
                        logger.error(f"❌ Failed to recreate pool: {e}")
                        raise RuntimeError(f"Failed to recreate database pool: {e}")
                else:
                    return self._pool
        
        raise RuntimeError("DatabaseService has not been initialized")

    def is_initialized(self) -> bool:
        """Return True when the pool is ready for use."""
        # Check if pool exists and is not closed (default to False for _closed attribute)
        is_init = self._pool is not None and not getattr(self._pool, '_closed', False)
        if not is_init:
            logger.debug(f"🔍 Instance #{self._instance_id}: is_initialized={is_init} (_pool is None: {self._pool is None})")
        return is_init
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Return current pool statistics for monitoring."""
        # Check if pool exists and is not closed (default to False for _closed attribute)
        if not self._pool or getattr(self._pool, '_closed', False):
            logger.warning(f"⚠️  Instance #{self._instance_id}: Pool unavailable in get_pool_stats()")
            logger.warning(f"   _pool is None: {self._pool is None}")
            logger.warning(f"   _pool object id: {id(self._pool) if self._pool else 'N/A'}")
            logger.warning(f"   Have connection details: {bool(self._database_url and self._pool_kwargs)}")
            return {
                "initialized": False,
                "closed": True,
                "size": 0,
                "free": 0,
                "in_use": 0,
            }
        
        try:
            size = self._pool.get_size()
            free = self._pool.get_idle_size()
            return {
                "initialized": True,
                "closed": False,
                "size": size,
                "free": free,
                "in_use": size - free,
                "max_size": self._pool_kwargs.get("max_size", 10),
                "min_size": self._pool_kwargs.get("min_size", 1),
            }
        except Exception as e:
            logger.error(f"❌ Exception getting pool stats: {e}")
            return {
                "initialized": True,
                "closed": False,
                "error": f"Could not retrieve stats: {e}",
            }

    async def close(self) -> None:
        """Gracefully close the connection pool."""
        logger.warning(f"🛑 DatabaseService instance #{self._instance_id} close() called!")
        logger.warning(f"   Stack trace:\n{''.join(traceback.format_stack())}")
        
        if self._pool is None:
            logger.warning(f"   Pool already None, nothing to close")
            return

        async with self._lock:
            if self._pool is not None:
                logger.info(f"   Closing pool: pool_id={id(self._pool)}")
                await self._pool.close()
                self._pool = None
                logger.warning(f"   ✅ Pool closed and set to None")
                self._database_url = None
                self._pool_kwargs = {}

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[asyncpg.Connection]:
        """Context manager that yields a pooled database connection."""
        pool = await self.ensure_pool()
        async with pool.acquire() as connection:
            yield connection

    async def fetch(self, query: str, *args: Any) -> Any:
        pool = await self.ensure_pool()
        async with pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def fetchrow(self, query: str, *args: Any) -> Any:
        pool = await self.ensure_pool()
        async with pool.acquire() as connection:
            return await connection.fetchrow(query, *args)

    async def fetchval(self, query: str, *args: Any) -> Any:
        pool = await self.ensure_pool()
        async with pool.acquire() as connection:
            return await connection.fetchval(query, *args)

    async def execute(self, query: str, *args: Any) -> str:
        pool = await self.ensure_pool()
        async with pool.acquire() as connection:
            return await connection.execute(query, *args)

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[Any]:
        """Context manager that starts a transaction on a pooled connection."""
        pool = await self.ensure_pool()
        async with pool.acquire() as connection:
            async with connection.transaction() as tx:
                yield tx

    async def run_with_connection(
        self,
        callback: Callable[[asyncpg.Connection], Any],
        *,
        transactional: bool = False,
    ) -> Any:
        """Execute `callback` with a pooled connection.

        Args:
            callback: Callable receiving an asyncpg connection.
            transactional: Wrap the call in a transaction when True.
        """
        pool = await self.ensure_pool()
        async with pool.acquire() as connection:
            if transactional:
                async with connection.transaction():
                    return await callback(connection)
            return await callback(connection)


database_service = DatabaseService()
"""Global database service instance used across the backend."""
