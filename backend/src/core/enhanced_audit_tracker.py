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
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class EnhancedDatabaseAuditTracker:
    """
    Enhanced audit tracker with direct database connectivity.
    
    This version bypasses the Next.js API dependency and connects
    directly to Supabase PostgreSQL for reliable audit logging.
    """
    
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
        self.total_cost = 0.0
        self.total_tokens = 0
        
        logger.info(f"🔍 Enhanced DatabaseAuditTracker initialized for {session_type}")
        logger.info(f"   User: {user_id}")
        logger.info(f"   Blog: {blog_id}")
        logger.info(f"   Session: {self.session_id}")
    
    async def _get_database_connection(self) -> Optional[asyncpg.Pool]:
        """Get or create database connection pool."""
        if self.pool:
            return self.pool
        
        try:
            # Try to get DATABASE_URL from environment
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                logger.warning("No DATABASE_URL found - database audit disabled")
                return None
            
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                database_url,
                min_size=1,
                max_size=3,
                command_timeout=10
            )
            
            # Test connection
            async with self.pool.acquire() as conn:
                await conn.execute('SELECT 1')
            
            self.database_enabled = True
            logger.info("✅ Direct database connection established")
            return self.pool
            
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
                    await conn.execute("""
                        INSERT INTO audit_sessions (
                            id, session_type, user_id, blog_id, start_time, 
                            total_cost, total_tokens, input_tokens, output_tokens, call_count
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                        self.session_id,
                        self.session_type,
                        self.user_id,
                        self.blog_id,
                        datetime.now(),  # Remove timezone for database compatibility
                        0.0,
                        0,
                        0,
                        0,
                        0
                    )
                
                logger.info(f"✅ Database audit session started: {self.session_id}")
            else:
                logger.warning(f"🔄 Fallback audit session started: {self.session_id}")
                logger.warning("   Database logging: DISABLED")
            
            return self.session_id
            
        except Exception as e:
            logger.error(f"❌ Failed to start audit session: {e}")
            logger.warning(f"🔄 Fallback to memory-only logging")
            return self.session_id
    
    async def _ensure_llm_calls_table_exists(self, conn):
        """Ensure the llm_calls table exists for storing individual API calls."""
        try:
            # Check if the table matches the Prisma schema structure
            await conn.execute("""
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
            """)
            logger.debug("✅ LLM calls table ensured (compatible with Prisma schema)")
        except Exception as e:
            logger.error(f"❌ Failed to create llm_calls table: {e}")
    
    async def track_api_call(self, model: str, input_tokens: int, output_tokens: int, 
                           phase: str, agent_role: str):
        """Track an API call with proper async handling."""
        try:
            total_tokens = input_tokens + output_tokens
            
            # Calculate cost (simplified pricing)
            cost_per_1k_input = 0.03 if 'gpt-4' in model else 0.0015
            cost_per_1k_output = 0.06 if 'gpt-4' in model else 0.002
            
            estimated_cost = (
                (input_tokens / 1000) * cost_per_1k_input +
                (output_tokens / 1000) * cost_per_1k_output
            )
            
            # Update totals
            self.total_cost += estimated_cost
            self.total_tokens += total_tokens
            
            # Log to console (always works)
            logger.info(f"💰 LLM Call: {model} ({phase}) [{agent_role}] - ${estimated_cost:.4f} ({total_tokens} tokens)")
            
            # Store in memory
            call_data = {
                'model': model,
                'phase': phase,
                'agent_role': agent_role,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': total_tokens,
                'cost': estimated_cost,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            self.logged_calls.append(call_data)
            
            # Try to log to database
            await self._log_to_database(call_data)
            
            logger.info(f"Intercepted actual API call: {model} - {total_tokens} tokens")
            
        except Exception as e:
            logger.error(f"❌ Failed to track API call: {e}")
    
    async def _log_to_database(self, call_data: Dict[str, Any]):
        """Log call data to database if available."""
        try:
            pool = await self._get_database_connection()
            if not pool:
                return
            
            # Calculate separate input/output costs to match Prisma schema
            cost_per_1k_input = 0.03 if 'gpt-4' in call_data['model'] else 0.0015
            cost_per_1k_output = 0.06 if 'gpt-4' in call_data['model'] else 0.002
            
            input_cost = (call_data['input_tokens'] / 1000) * cost_per_1k_input
            output_cost = (call_data['output_tokens'] / 1000) * cost_per_1k_output
            total_cost = input_cost + output_cost
            
            async with pool.acquire() as conn:
                # Insert into llm_calls table with Prisma-compatible schema
                await conn.execute("""
                    INSERT INTO llm_calls (
                        id, audit_session_id, model, input_tokens, output_tokens,
                        input_cost, output_cost, total_cost, phase, agent_role, 
                        call_type, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                    str(uuid.uuid4()),  # Generate ID explicitly
                    self.session_id,
                    call_data['model'],
                    call_data['input_tokens'],
                    call_data['output_tokens'],
                    input_cost,
                    output_cost,
                    total_cost,
                    call_data['phase'],
                    call_data['agent_role'],
                    'actual',
                    datetime.now()  # Remove timezone for database compatibility
                )
            
            logger.debug(f"✅ API call logged to database (Prisma compatible)")
            logger.info(f"📝 Logged LLM call: {call_data['model']} - ${input_cost + output_cost:.4f}")
            
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
                    await conn.execute("""
                        UPDATE audit_sessions 
                        SET end_time = $1, total_cost = $2, total_tokens = $3,
                            input_tokens = $4, output_tokens = $5, call_count = $6
                        WHERE id = $7
                    """,
                        datetime.now(),  # Remove timezone for database compatibility
                        self.total_cost,
                        self.total_tokens,
                        sum(call['input_tokens'] for call in self.logged_calls),
                        sum(call['output_tokens'] for call in self.logged_calls),
                        len(self.logged_calls),
                        self.session_id
                    )
                
                logger.info(f"✅ Database audit session completed: {self.session_id}")
                logger.info(f"   Total cost: ${self.total_cost:.4f}")
                logger.info(f"   Total tokens: {self.total_tokens}")
                logger.info(f"   Total calls: {len(self.logged_calls)}")
            else:
                logger.warning(f"🔄 Fallback audit session completed: {self.session_id}")
                logger.warning(f"   Total cost: ${self.total_cost:.4f} (not saved to database)")
                logger.warning(f"   Total tokens: {self.total_tokens} (not saved to database)")
            
        except Exception as e:
            logger.error(f"❌ Failed to end audit session: {e}")
        
        finally:
            # Close database connection
            if self.pool:
                try:
                    await self.pool.close()
                except:
                    pass
    
    def track_llm_call(self, *args, **kwargs):
        """Sync wrapper that creates an async task."""
        # This is called by the sync LLM interceptor
        # We need to handle it properly in the async context
        try:
            # Try to get the current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a task
                task = loop.create_task(self.track_api_call(*args, **kwargs))
                logger.debug("Created async task for LLM call tracking")
            else:
                # If not in async context, run synchronously
                loop.run_until_complete(self.track_api_call(*args, **kwargs))
        except Exception as e:
            logger.error(f"Failed to track LLM call: {e}")
            # Fallback to basic logging
            logger.info(f"💰 LLM Call (fallback): {args} {kwargs}")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the current session."""
        return {
            'session_id': self.session_id,
            'session_type': self.session_type,
            'user_id': self.user_id,
            'blog_id': self.blog_id,
            'total_cost': self.total_cost,
            'total_tokens': self.total_tokens,
            'call_count': len(self.logged_calls),
            'database_enabled': self.database_enabled,
            'calls': self.logged_calls
        }
