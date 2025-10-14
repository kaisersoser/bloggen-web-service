"""
Background Database Worker

Handles async database operations in a separate thread.
Follows Single Responsibility Principle - only manages background database operations.
"""

import asyncio
import queue
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from core.database_manager import DatabaseConnectionManager
from core.cost_calculator import CostCalculator

logger = logging.getLogger(__name__)


class DatabaseWorker:
    """Background worker for processing database operations asynchronously."""

    def __init__(self):
        self._queue = queue.Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._db_manager = DatabaseConnectionManager()

    def start(self):
        """Start the background database worker."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(
                target=self._worker_loop, daemon=True, name="AuditDatabaseWorker"
            )
            self._thread.start()
            logger.info("🚀 Database worker started")

    def stop(self):
        """Stop the background database worker."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("🛑 Database worker stopped")

    def queue_operation(self, operation_type: str, data: Dict[str, Any]):
        """Queue a database operation for background processing."""
        operation = {"type": operation_type, "data": data, "timestamp": datetime.now()}
        self._queue.put(operation)
        logger.debug(f"📥 Queued {operation_type} operation")

    def _worker_loop(self):
        """Main worker loop that processes database operations."""
        logger.info("💾 Database worker loop started")

        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self._process_operations())
        except Exception as e:
            logger.error(f"❌ Database worker loop error: {e}")
        finally:
            # DO NOT close the loop - it closes the shared database pool!
            # asyncpg pools are tied to event loops, and closing this loop
            # will mark the shared database_service._pool as closed.
            # Just clear the reference instead.
            asyncio.set_event_loop(None)
            # loop.close()  # REMOVED: This was closing the database pool!
            self._running = False

    async def _process_operations(self):
        """Process database operations from the queue."""
        while self._running:
            try:
                operation = self._queue.get(timeout=1.0)

                if operation["type"] == "log_call":
                    await self._process_api_call_log(operation["data"])
                elif operation["type"] == "update_blog_id":
                    await self._process_blog_id_update(operation["data"])
                elif operation["type"] == "start_session":
                    await self._process_session_start(operation["data"])
                elif operation["type"] == "end_session":
                    await self._process_session_end(operation["data"])

                self._queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"❌ Database operation error: {e}")

    async def _process_api_call_log(self, call_data: Dict[str, Any]):
        """Process API call logging to database."""
        try:
            pool = await self._db_manager.get_connection_pool()
            if not pool:
                return

            # Calculate costs
            costs = CostCalculator.calculate_cost(
                call_data["model"],
                call_data["input_tokens"],
                call_data["output_tokens"],
            )

            async with pool.acquire() as conn:
                # Insert individual call record
                await conn.execute(
                    """
                    INSERT INTO llm_calls (
                        id, audit_session_id, model, input_tokens, output_tokens,
                        input_cost, output_cost, total_cost, phase, agent_role,
                        call_type, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                    call_data["call_id"],
                    call_data["session_id"],
                    call_data["model"],
                    call_data["input_tokens"],
                    call_data["output_tokens"],
                    costs["input_cost"],
                    costs["output_cost"],
                    costs["total_cost"],
                    call_data.get("phase", "unknown"),
                    call_data.get("agent_role", "unknown"),
                    "actual",
                    call_data["timestamp"],
                )

                # Update session totals
                await conn.execute(
                    """
                    UPDATE audit_sessions
                    SET total_cost = total_cost + $2,
                        total_tokens = total_tokens + $3,
                        call_count = call_count + 1,
                        end_time = $4
                    WHERE id = $1
                """,
                    call_data["session_id"],
                    costs["total_cost"],
                    call_data["input_tokens"] + call_data["output_tokens"],
                    call_data["timestamp"],
                )

            logger.debug(
                f"✅ Logged API call: {call_data['model']} | ${costs['total_cost']:.4f}"
            )

        except Exception as e:
            logger.error(f"❌ Failed to log API call: {e}")

    async def _process_blog_id_update(self, update_data: Dict[str, Any]):
        """Process blog ID update."""
        try:
            pool = await self._db_manager.get_connection_pool()
            if not pool:
                return

            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE audit_sessions
                    SET blog_id = $1
                    WHERE id = $2
                """,
                    update_data["blog_id"],
                    update_data["session_id"],
                )

            logger.info(f"✅ Updated session with blog_id: {update_data['blog_id']}")

        except Exception as e:
            logger.error(f"❌ Failed to update blog_id: {e}")

    async def _process_session_start(self, session_data: Dict[str, Any]):
        """Process session start in database."""
        try:
            pool = await self._db_manager.get_connection_pool()
            if not pool:
                return

            async with pool.acquire() as conn:
                await self._db_manager.ensure_tables_exist(conn)

                await conn.execute(
                    """
                    INSERT INTO audit_sessions (
                        id, session_type, user_id, blog_id, start_time,
                        total_cost, total_tokens, input_tokens, output_tokens, call_count
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                    session_data["session_id"],
                    session_data["session_type"],
                    session_data["user_id"],
                    None,  # blog_id can be NULL initially
                    session_data["start_time"],
                    0.0,
                    0,
                    0,
                    0,
                    0,
                )

            logger.info(f"✅ Session started in database: {session_data['session_id']}")

        except Exception as e:
            logger.error(f"❌ Failed to start session: {e}")

    async def _process_session_end(self, session_data: Dict[str, Any]):
        """Process session end in database."""
        try:
            pool = await self._db_manager.get_connection_pool()
            if not pool:
                return

            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE audit_sessions
                    SET end_time = $1, total_cost = $2, total_tokens = $3,
                        input_tokens = $4, output_tokens = $5, call_count = $6
                    WHERE id = $7
                """,
                    session_data["end_time"],
                    session_data["total_cost"],
                    session_data["total_tokens"],
                    session_data["input_tokens"],
                    session_data["output_tokens"],
                    session_data["call_count"],
                    session_data["session_id"],
                )

            logger.info(f"✅ Session ended: {session_data['session_id']}")

        except Exception as e:
            logger.error(f"❌ Failed to end session: {e}")

    async def close(self):
        """Close database connections."""
        await self._db_manager.close()
