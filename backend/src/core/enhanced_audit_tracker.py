"""
Enhanced Database Audit Tracker with Direct Connection

This is an improved version of the audit tracker that:
1. Uses direct PostgreSQL connections (no frontend dependency)
2. Properly handles async/await patterns
3. Provides fallback logging when database is unavailable
4. Integrates seamlessly with the existing LLM interceptor
"""

import asyncio
import asyncpg
import os
import uuid
import queue
import threading
from datetime import datetime
from typing import Optional, Dict, Any
import logging

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv not required

logger = logging.getLogger(__name__)


class EnhancedDatabaseAuditTracker:
    """
    Enhanced audit tracker with direct database connectivity.

    This version bypasses the Next.js API dependency and connects
    directly to Supabase PostgreSQL for reliable audit logging.
    Uses background thread processing to handle database operations
    from any execution context (including thread pools).
    """

    # Class-level database worker
    _db_queue = queue.Queue()
    _db_worker_running = False
    _db_worker_thread = None

    def __init__(self, session_type: str, user_id: str, blog_id: Optional[str]):
        """Initialize the enhanced audit tracker."""
        self.session_type = session_type
        self.user_id = user_id
        self.blog_id = blog_id
        self.session_id = str(uuid.uuid4())

        # Database connection
        self.pool: Optional[asyncpg.Pool] = None
        self.database_enabled = False

        # Fallback logging
        self.logged_calls = []

        # Tracking variables
        self.total_cost = 0.0
        self.total_tokens = 0

        # Ensure database worker is running
        self._ensure_db_worker()

        logger.info(
            f"🔍 Enhanced EnhancedDatabaseAuditTracker initialized for {self.session_type}"
        )
        logger.info(f"   User: {self.user_id}")
        logger.info(f"   Blog: {self.blog_id}")
        logger.info(f"   Session: {self.session_id}")

    @classmethod
    def _ensure_db_worker(cls):
        """Ensure database worker thread is running."""
        if not cls._db_worker_running:
            cls._db_worker_running = True
            cls._db_worker_thread = threading.Thread(
                target=cls._database_worker, daemon=True, name="AuditTrackerDBWorker"
            )
            cls._db_worker_thread.start()
            logger.info("🚀 Started audit tracker database worker thread")

    @classmethod
    def _database_worker(cls):
        """Background thread worker that processes database operations."""
        logger.info("💾 Audit tracker database worker started")

        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def process_operations():
            while cls._db_worker_running:
                try:
                    # Get operation from queue with timeout
                    operation = cls._db_queue.get(timeout=1.0)

                    if operation["type"] == "log_call":
                        await cls._process_database_log(operation["data"])
                    elif operation["type"] == "update_blog_id":
                        await cls._process_blog_id_update(operation["data"])

                    cls._db_queue.task_done()

                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"❌ Database worker error: {e}")

        try:
            loop.run_until_complete(process_operations())
        except Exception as e:
            logger.error(f"❌ Database worker loop error: {e}")
        finally:
            loop.close()
            cls._db_worker_running = False

    @classmethod
    async def _process_database_log(cls, call_data: Dict[str, Any]):
        """Process database logging operation."""
        try:
            # Create temporary tracker instance for database operations
            temp_tracker = cls.__new__(cls)
            temp_tracker.session_id = call_data.get("session_id")
            temp_tracker.database_enabled = False
            temp_tracker.pool = None  # Initialize pool attribute

            pool = await temp_tracker._get_database_connection()
            if not pool:
                logger.warning("No database connection available for logging")
                return

            # Calculate separate input/output costs to match Prisma schema
            cost_per_1k_input = 0.03 if "gpt-4" in call_data["model"] else 0.0015
            cost_per_1k_output = 0.06 if "gpt-4" in call_data["model"] else 0.002

            input_cost = (call_data["input_tokens"] / 1000) * cost_per_1k_input
            output_cost = (call_data["output_tokens"] / 1000) * cost_per_1k_output
            total_cost = input_cost + output_cost

            async with pool.acquire() as conn:
                # Insert individual call record
                call_id = str(uuid.uuid4())
                await conn.execute(
                    """
                    INSERT INTO llm_calls (
                        id, audit_session_id, model, input_tokens, output_tokens,
                        input_cost, output_cost, total_cost, phase, agent_role,
                        call_type, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                    call_id,
                    call_data["session_id"],
                    call_data["model"],
                    call_data["input_tokens"],
                    call_data["output_tokens"],
                    input_cost,
                    output_cost,
                    total_cost,
                    call_data.get("phase", "unknown"),
                    call_data.get("agent_role", "unknown"),
                    "actual",
                    call_data["timestamp"].replace(
                        tzinfo=None
                    ),  # Remove timezone for database compatibility
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
                    total_cost,
                    call_data["input_tokens"] + call_data["output_tokens"],
                    call_data["timestamp"].replace(
                        tzinfo=None
                    ),  # Remove timezone for database compatibility
                )

            logger.debug(
                f"✅ Logged API call to database: {call_data['model']} | ${total_cost:.4f}"
            )

        except Exception as e:
            logger.error(f"❌ Failed to process database log: {e}")

    @classmethod
    async def _process_blog_id_update(cls, update_data: Dict[str, Any]):
        """Process blog ID update operation."""
        try:
            # Create temporary tracker instance for database operations
            temp_tracker = cls.__new__(cls)
            temp_tracker.session_id = update_data.get("session_id")
            temp_tracker.database_enabled = False
            temp_tracker.pool = None  # Initialize pool attribute

            pool = await temp_tracker._get_database_connection()
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

            logger.info(
                f"✅ Updated audit session with blog_id: {update_data['blog_id']}"
            )

        except Exception as e:
            logger.error(f"❌ Failed to update blog_id: {e}")

    def _queue_database_operation(self, operation_type: str, data: Dict[str, Any]):
        """Queue a database operation for background processing."""
        operation = {
            "type": operation_type,
            "data": data,
            "timestamp": datetime.now(),  # Remove timezone for consistency
        }
        self._db_queue.put(operation)
        logger.debug(f"📥 Queued {operation_type} operation")

    async def _get_database_connection(self) -> Optional[asyncpg.Pool]:
        """
        Get database connection using centralized DatabaseService.
        
        Phase 3.1 Migration: Now uses shared connection pool instead of
        creating a separate audit tracker-specific pool.
        """
        from core.database_service import database_service

        # Return cached pool reference if already obtained
        if self.pool:
            return self.pool

        try:
            # Use centralized database service
            self.pool = await database_service.ensure_pool()
            self.database_enabled = True
            logger.info("✅ Audit tracker using centralized database pool")
            return self.pool

        except RuntimeError:
            logger.warning("DatabaseService not initialized - database audit disabled")
            self.database_enabled = False
            return None
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            self.database_enabled = False
            return None

    async def start_session(self):
        """Start an audit session."""
        try:
            pool = await self._get_database_connection()

            if pool:
                async with pool.acquire() as conn:
                    # First, ensure the llm_calls table exists
                    await self._ensure_llm_calls_table_exists(conn)

                    # Insert into audit_sessions table (matching existing schema)
                    # Note: blog_id can be NULL for sessions that don't have a blog yet
                    await conn.execute(
                        """
                        INSERT INTO audit_sessions (
                            id, session_type, user_id, blog_id, start_time,
                            total_cost, total_tokens, input_tokens, output_tokens, call_count
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                        self.session_id,
                        self.session_type,
                        self.user_id,
                        None,  # Set blog_id to NULL for now to avoid foreign key constraint
                        datetime.now(),  # Remove timezone for database compatibility
                        0.0,
                        0,
                        0,
                        0,
                        0,
                    )

                logger.info(f"✅ Database audit session started: {self.session_id}")
            else:
                logger.warning(f"🔄 Fallback audit session started: {self.session_id}")
                logger.warning("   Database logging: DISABLED")

            return self.session_id

        except Exception as e:
            logger.error(f"❌ Failed to start audit session: {e}")
            logger.warning("🔄 Fallback to memory-only logging")
            return self.session_id

    async def _ensure_llm_calls_table_exists(self, conn):
        """Ensure the llm_calls table exists for storing individual API calls."""
        try:
            # Check if the table matches the Prisma schema structure
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
            logger.debug("✅ LLM calls table ensured (compatible with Prisma schema)")
        except Exception as e:
            logger.error(f"❌ Failed to create llm_calls table: {e}")

    def track_api_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: Optional[float] = None,
        phase: str = "unknown",
        agent_role: str = "unknown",
    ):
        """Track an API call with proper sync/async handling."""
        try:
            total_tokens = input_tokens + output_tokens

            # Calculate cost if not provided
            if cost is None:
                cost_per_1k_input = 0.03 if "gpt-4" in model else 0.0015
                cost_per_1k_output = 0.06 if "gpt-4" in model else 0.002

                estimated_cost = (input_tokens / 1000) * cost_per_1k_input + (
                    output_tokens / 1000
                ) * cost_per_1k_output
            else:
                estimated_cost = cost

            # Update totals immediately (thread-safe for basic operations)
            self.total_cost += estimated_cost
            self.total_tokens += total_tokens

            # Log to console (always works)
            logger.info(
                f"💰 LLM Call: {model} ({phase}) [{agent_role}] - ${estimated_cost:.4f} ({total_tokens} tokens)"
            )

            # Store in memory
            call_data = {
                "model": model,
                "phase": phase,
                "agent_role": agent_role,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cost": estimated_cost,
                "timestamp": datetime.now(),  # Remove timezone for database compatibility
            }
            self.logged_calls.append(call_data)

            # Schedule async database logging (non-blocking)
            self._schedule_database_log(call_data)

            logger.info(f"Intercepted actual API call: {model} - {total_tokens} tokens")

        except Exception as e:
            logger.error(f"❌ Failed to track API call: {e}")

    def _schedule_database_log(self, call_data: Dict[str, Any]):
        """Schedule database logging via background thread queue."""
        try:
            # Add session_id to call_data for background processing
            call_data["session_id"] = self.session_id

            # Queue the database operation (works from any thread context)
            self._queue_database_operation("log_call", call_data)

            logger.debug(f"📤 Scheduled database log for {call_data['model']}")

        except Exception as e:
            logger.error(f"❌ Failed to schedule database log: {e}")

    async def update_blog_id(self, blog_id: str):
        """Update the blog_id for this audit session once the blog is created."""
        try:
            self.blog_id = blog_id

            # Queue the blog_id update operation
            self._queue_database_operation(
                "update_blog_id", {"session_id": self.session_id, "blog_id": blog_id}
            )

            logger.info(f"📤 Scheduled blog_id update for session {self.session_id}")

        except Exception as e:
            logger.error(f"❌ Failed to schedule blog_id update: {e}")

    async def _log_to_database(self, call_data: Dict[str, Any]):
        """Log call data to database if available."""
        try:
            pool = await self._get_database_connection()
            if not pool:
                return

            # Calculate separate input/output costs to match Prisma schema
            if call_data["model"] == "serper_api":
                # Flat fee per call per requirements
                input_cost = 0.0
                output_cost = 0.0
                total_cost = 0.001
            else:
                cost_per_1k_input = 0.03 if "gpt-4" in call_data["model"] else 0.0015
                cost_per_1k_output = 0.06 if "gpt-4" in call_data["model"] else 0.002
                input_cost = (call_data["input_tokens"] / 1000) * cost_per_1k_input
                output_cost = (call_data["output_tokens"] / 1000) * cost_per_1k_output
                total_cost = input_cost + output_cost

            async with pool.acquire() as conn:
                # Insert into llm_calls table with Prisma-compatible schema
                await conn.execute(
                    """
                    INSERT INTO llm_calls (
                        id, audit_session_id, model, input_tokens, output_tokens,
                        input_cost, output_cost, total_cost, phase, agent_role,
                        call_type, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                    str(uuid.uuid4()),  # Generate ID explicitly
                    self.session_id,
                    call_data["model"],
                    call_data["input_tokens"],
                    call_data["output_tokens"],
                    input_cost,
                    output_cost,
                    total_cost,
                    call_data["phase"],
                    call_data["agent_role"],
                    "actual",
                    datetime.now(),  # Remove timezone for database compatibility
                )

            logger.debug("✅ API call logged to database (Prisma compatible)")
            logger.info(
                f"📝 Logged LLM call: {call_data['model']} - ${input_cost + output_cost:.4f}"
            )

        except Exception as e:
            logger.error(f"❌ Database logging failed: {e}")
            logger.debug(f"Database logging failed, using fallback: {e}")

    async def end_session(self):
        """End the audit session and update totals."""
        try:
            pool = await self._get_database_connection()

            if pool:
                async with pool.acquire() as conn:
                    # Update audit_sessions table with final totals (matching existing schema)
                    await conn.execute(
                        """
                        UPDATE audit_sessions
                        SET end_time = $1, total_cost = $2, total_tokens = $3,
                            input_tokens = $4, output_tokens = $5, call_count = $6
                        WHERE id = $7
                    """,
                        datetime.now(),  # Remove timezone for database compatibility
                        self.total_cost,
                        self.total_tokens,
                        sum(call["input_tokens"] for call in self.logged_calls),
                        sum(call["output_tokens"] for call in self.logged_calls),
                        len(self.logged_calls),
                        self.session_id,
                    )

                logger.info(f"✅ Database audit session completed: {self.session_id}")
                logger.info(f"   Total cost: ${self.total_cost:.4f}")
                logger.info(f"   Total tokens: {self.total_tokens}")
                logger.info(f"   Total calls: {len(self.logged_calls)}")
            else:
                logger.warning(
                    f"🔄 Fallback audit session completed: {self.session_id}"
                )
                logger.warning(
                    f"   Total cost: ${self.total_cost:.4f} (not saved to database)"
                )
                logger.warning(
                    f"   Total tokens: {self.total_tokens} (not saved to database)"
                )

        except Exception as e:
            logger.error(f"❌ Failed to end audit session: {e}")

        finally:
            # Close database connection
            if self.pool:
                try:
                    await self.pool.close()
                except Exception as e:
                    logger.debug(f"Error closing pool: {e}")

    def track_llm_call(self, *args, **kwargs):
        """Sync wrapper for backward compatibility."""
        # This is called by the sync LLM interceptor
        # Just delegate to our sync track_api_call method
        try:
            if len(args) >= 5:
                self.track_api_call(args[0], args[1], args[2], args[3], args[4])
            else:
                # Fallback to basic logging
                logger.info(f"💰 LLM Call (fallback): {args} {kwargs}")
        except Exception as e:
            logger.error(f"Failed to track LLM call: {e}")
            # Fallback to basic logging
            logger.info(f"💰 LLM Call (fallback): {args} {kwargs}")

    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the current session."""
        return {
            "session_id": self.session_id,
            "session_type": self.session_type,
            "user_id": self.user_id,
            "blog_id": self.blog_id,
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
            "call_count": len(self.logged_calls),
            "database_enabled": self.database_enabled,
            "logged_calls": self.logged_calls,
        }

    # ------------------------------------------------------------------
    # Retrospective Cost Patch for serper_api calls with zero cost
    # ------------------------------------------------------------------
    @staticmethod
    async def patch_serper_api_costs(pool_provider) -> int:
        """Backfill cost for existing serper_api rows with zero total_cost.

        Args:
            pool_provider: Callable returning an asyncpg pool or pool instance.
        Returns:
            int: number of rows updated.
        """
        updated = 0
        try:
            pool = await pool_provider()
            if not pool:
                return 0
            async with pool.acquire() as conn:
                # Update any serper_api calls that still have zero cost
                res = await conn.execute(
                    """
                    UPDATE llm_calls
                    SET input_cost = 0.0,
                        output_cost = 0.0,
                        total_cost = 0.001
                    WHERE model = 'serper_api' AND total_cost = 0.0
                """
                )
                # asyncpg returns command tag like 'UPDATE <count>'
                if isinstance(res, str) and res.startswith("UPDATE"):
                    try:
                        updated = int(res.split()[-1])
                    except Exception:
                        updated = 0
            if updated:
                logger.info(
                    f"🔄 Patched {updated} serper_api call(s) with flat cost 0.001"
                )
            else:
                logger.info("ℹ️ No serper_api calls required cost patch")
        except Exception as e:
            logger.error(f"❌ Failed to patch serper_api costs: {e}")
        return updated

    # ------------------------------------------------------------------
    # Phase Name Normalization Patch
    # ------------------------------------------------------------------
    @staticmethod
    async def normalize_phase_names(pool_provider) -> Dict[str, int]:
        """Normalize legacy phase names in llm_calls to current canonical set.

        Canonical phases currently in use:
            initialization, research, content_generation, fact_checking, finalization

        Historical / legacy variants will be mapped to the most appropriate
        current phase. Matching is performed case-insensitively. Already
        canonical names are left untouched. Unknown / unlisted phases remain
        unchanged so historical diagnostics are not lost.

        Args:
            pool_provider: Callable returning an asyncpg pool (or None)
        Returns:
            dict mapping canonical phase -> number of rows updated
        """
        results: Dict[str, int] = {}
        try:
            pool = await pool_provider()
            if not pool:
                return results
            # Flat variant -> canonical mapping (all lower-case for comparison)
            variant_map = {
                # Initialization
                "init": "initialization",
                "initialize": "initialization",
                "initial": "initialization",
                "initialization_phase": "initialization",
                "setup": "initialization",
                # Research
                "research_phase": "research",
                "researching": "research",
                "research-phase": "research",
                # Content generation
                "content_generation_phase": "content_generation",
                "content-generation": "content_generation",
                "draft": "content_generation",
                "drafting": "content_generation",
                "content": "content_generation",
                "generation": "content_generation",
                "writing": "content_generation",
                # Fact checking
                "fact_checking_phase": "fact_checking",
                "fact-checking": "fact_checking",
                "fact_check": "fact_checking",
                "factcheck": "fact_checking",
                "validation": "fact_checking",
                "verify": "fact_checking",
                # Finalization
                "finalization_phase": "finalization",
                "finalize": "finalization",
                "finalizing": "finalization",
                "final": "finalization",
                # Image generation
                "images": "image_generation",
                "image": "image_generation",
                "imagegen": "image_generation",
            }
            async with pool.acquire() as conn:
                for variant, canonical in variant_map.items():
                    try:
                        res = await conn.execute(
                            """
                            UPDATE llm_calls
                            SET phase = $1
                            WHERE LOWER(phase) = $2 AND phase <> $1
                            """,
                            canonical,
                            variant,
                        )
                        if isinstance(res, str) and res.startswith("UPDATE"):
                            count = (
                                int(res.split()[-1]) if res.split()[-1].isdigit() else 0
                            )
                            if count:
                                results[canonical] = results.get(canonical, 0) + count
                    except Exception as inner_e:
                        logger.warning(
                            f"Phase normalization sub-update failed ({variant} -> {canonical}): {inner_e}"
                        )
            if results:
                summary = ", ".join(f"{k}={v}" for k, v in results.items())
                logger.info(f"🔄 Phase normalization complete: {summary}")
            else:
                logger.info("ℹ️ No legacy phase names required normalization")
        except Exception as e:
            logger.error(f"❌ Failed to normalize phase names: {e}")
        return results
