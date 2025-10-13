"""Centralized database service for managing asyncpg connection pool.

This module creates a single shared connection pool for the entire backend.
It exposes helper methods for acquiring connections and running common
operations while ensuring the pool is initialized exactly once.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable, Optional

import asyncpg


class DatabaseService:
    """Manage the lifecycle of a shared asyncpg connection pool."""

    def __init__(self) -> None:
        self._pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()
        self._pool_kwargs: dict[str, Any] = {}
        self._database_url: Optional[str] = None

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
            return self._pool

    async def ensure_pool(self) -> asyncpg.Pool:
        """Return the existing pool or raise if `initialize` has not been called."""
        if self._pool:
            return self._pool
        raise RuntimeError("DatabaseService has not been initialized")

    def is_initialized(self) -> bool:
        """Return True when the pool is ready for use."""
        return self._pool is not None

    async def close(self) -> None:
        """Gracefully close the connection pool."""
        if self._pool is None:
            return

        async with self._lock:
            if self._pool is not None:
                await self._pool.close()
                self._pool = None
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
