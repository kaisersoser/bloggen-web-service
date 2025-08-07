#!/usr/bin/env python3
"""
Audit System Validation - Refactored with Clean Code Principles

Tests the complete audit pipeline to ensure both session totals and individual 
LLM calls are properly recorded. Applies the 10 principles of good code:
- Single Responsibility Principle
- Clear, self-documenting code  
- Proper error handling and logging
- DRY principle compliance
- Type safety and validation
"""

import asyncio
import asyncpg
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
from contextlib import asynccontextmanager

# Use existing unified configuration system
import sys
sys.path.append('src')
from core.config import config
from core.logging_utils import get_logger

# Configure specialized logger for audit validation
logger = get_logger(__name__)

@dataclass
class AuditSession:
    """Data class representing an audit session with type safety."""
    id: str
    session_type: str
    total_cost: float
    total_tokens: int
    call_count: int
    start_time: datetime
    
    @classmethod
    def from_db_row(cls, row) -> 'AuditSession':
        """Create AuditSession from database row."""
        return cls(
            id=row['id'],
            session_type=row['session_type'],
            total_cost=float(row['total_cost']),
            total_tokens=int(row['total_tokens']),
            call_count=int(row['call_count']),
            start_time=row['start_time']
        )
    
    def format_summary(self) -> str:
        """Generate human-readable session summary."""
        return (
            f"Session {self.id[:8]}... | Type: {self.session_type} | "
            f"Cost: ${self.total_cost:.4f} | Tokens: {self.total_tokens:,} | "
            f"Calls: {self.call_count}"
        )


@dataclass  
class LLMCall:
    """Data class representing an individual LLM call with type safety."""
    model: str
    input_tokens: int
    output_tokens: int
    total_cost: float
    phase: str
    agent_role: str
    
    @classmethod
    def from_db_row(cls, row) -> 'LLMCall':
        """Create LLMCall from database row."""
        return cls(
            model=row['model'],
            input_tokens=int(row['input_tokens']),
            output_tokens=int(row['output_tokens']),
            total_cost=float(row['total_cost']),
            phase=row['phase'],
            agent_role=row['agent_role']
        )
    
    def format_summary(self) -> str:
        """Generate human-readable call summary."""
        return (
            f"{self.model} | {self.phase} | {self.agent_role} | "
            f"{self.input_tokens}→{self.output_tokens} tokens | ${self.total_cost:.6f}"
        )


@dataclass
class ValidationResult:
    """Results of audit validation test with clear success/failure indication."""
    success: bool
    sessions_created: int
    calls_created: int
    latest_session: Optional[AuditSession] = None
    session_calls: Optional[List[LLMCall]] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.session_calls is None:
            self.session_calls = []
    
    @property
    def status_message(self) -> str:
        """Get human-readable status message."""
        if not self.success:
            return f"❌ FAILURE: {self.error_message}"
        
        if self.sessions_created > 0 and self.calls_created > 0:
            return "🎉 SUCCESS: Both sessions and LLM calls recorded!"
        elif self.sessions_created > 0:
            return "⚠️ PARTIAL: Sessions recorded but no LLM calls"
        elif self.calls_created > 0:
            return "⚠️ PARTIAL: LLM calls recorded but no sessions"
        else:
            return "❌ FAILURE: No audit data recorded"


class DatabaseConnectionManager:
    """Manages database connections with proper resource handling."""
    
    def __init__(self):
        self.database_url = config.database.url
        if not self.database_url:
            raise ValueError("DATABASE_URL not configured")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection with automatic cleanup."""
        conn = None
        try:
            logger.info("Establishing database connection")
            conn = await asyncpg.connect(
                self.database_url,
                timeout=30
            )
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise ConnectionError(f"Failed to connect to database: {e}")
        finally:
            if conn:
                await conn.close()
                logger.info("Database connection closed")


class AuditTestExecutor:
    """Handles execution of audit system tests with proper separation of concerns."""
    
    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager
        self.test_script = "debug_audit_system.py"
    
    async def get_baseline_counts(self) -> Tuple[int, int]:
        """Get current count of sessions and calls before testing."""
        async with self.db_manager.get_connection() as conn:
            try:
                session_count = await conn.fetchval("SELECT COUNT(*) FROM audit_sessions")
                calls_count = await conn.fetchval("SELECT COUNT(*) FROM llm_calls")
                logger.info(f"Baseline: {session_count} sessions, {calls_count} calls")
                return int(session_count), int(calls_count)
            except Exception as e:
                logger.error(f"Failed to get baseline counts: {e}")
                raise
    
    async def execute_audit_test(self) -> bool:
        """Execute the audit system test script."""
        try:
            logger.info(f"Running audit test: {self.test_script}")
            
            if not Path(self.test_script).exists():
                raise FileNotFoundError(f"Test script not found: {self.test_script}")
            
            process = await asyncio.create_subprocess_exec(
                "python", self.test_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path.cwd()
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info("Audit test completed successfully")
                return True
            else:
                logger.warning(f"Audit test returned code {process.returncode}")
                if stderr:
                    logger.error(f"Test stderr: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to execute audit test: {e}")
            raise
    
    async def get_latest_session_data(self) -> Tuple[Optional[AuditSession], List[LLMCall]]:
        """Retrieve the latest audit session and its associated LLM calls."""
        async with self.db_manager.get_connection() as conn:
            try:
                # Get latest session
                session_row = await conn.fetchrow("""
                    SELECT id, session_type, total_cost, total_tokens, call_count, start_time
                    FROM audit_sessions 
                    ORDER BY start_time DESC 
                    LIMIT 1
                """)
                
                if not session_row:
                    return None, []
                
                latest_session = AuditSession.from_db_row(session_row)
                
                # Get calls for this session
                call_rows = await conn.fetch("""
                    SELECT model, input_tokens, output_tokens, total_cost, phase, agent_role
                    FROM llm_calls 
                    WHERE audit_session_id = $1
                    ORDER BY timestamp
                """, latest_session.id)
                
                session_calls = [LLMCall.from_db_row(row) for row in call_rows]
                
                return latest_session, session_calls
                
            except Exception as e:
                logger.error(f"Failed to retrieve session data: {e}")
                return None, []
    
    async def wait_for_data_settlement(self, seconds: float = 1.0) -> None:
        """Wait for database writes to complete."""
        logger.info(f"Waiting {seconds}s for data settlement")
        await asyncio.sleep(seconds)


class ValidationReporter:
    """Handles formatting and display of validation results."""
    
    @staticmethod
    def print_header() -> None:
        """Print validation header."""
        print("=" * 70)
        print("🔍 AUDIT PIPELINE VALIDATION")
        print("=" * 70)
    
    @staticmethod
    def print_baseline_metrics(sessions: int, calls: int) -> None:
        """Print baseline metrics before testing."""
        print(f"📊 Before test: {sessions:,} sessions, {calls:,} LLM calls")
    
    @staticmethod
    def print_delta_metrics(sessions: int, calls: int) -> None:
        """Print metrics showing changes after testing."""
        print(f"\n📈 New data created:")
        print(f"   📝 Sessions: +{sessions}")
        print(f"   📞 LLM Calls: +{calls}")
    
    @staticmethod
    def print_session_details(session: AuditSession) -> None:
        """Print detailed session information."""
        print(f"\n📊 Latest session details:")
        print(f"   🆔 ID: {session.id[:8]}...")
        print(f"   📝 Type: {session.session_type}")
        print(f"   💰 Cost: ${session.total_cost:.4f}")
        print(f"   🎯 Tokens: {session.total_tokens:,}")
        print(f"   📞 Calls: {session.call_count}")
    
    @staticmethod
    def print_llm_calls(calls: List[LLMCall]) -> None:
        """Print detailed LLM call information."""
        if not calls:
            print("\n⚠️ No LLM calls found for this session")
            return
        
        print(f"\n📞 LLM calls for this session ({len(calls)} calls):")
        for i, call in enumerate(calls, 1):
            print(f"   {i}. {call.format_summary()}")


class AuditValidationOrchestrator:
    """Main orchestrator coordinating the complete audit validation process."""
    
    def __init__(self):
        self.db_manager = DatabaseConnectionManager()
        self.test_executor = AuditTestExecutor(self.db_manager)
        self.reporter = ValidationReporter()
    
    async def run_validation(self) -> ValidationResult:
        """Execute the complete validation pipeline with comprehensive error handling."""
        try:
            # Print header
            self.reporter.print_header()
            
            # Get baseline counts
            sessions_before, calls_before = await self.test_executor.get_baseline_counts()
            self.reporter.print_baseline_metrics(sessions_before, calls_before)
            
            # Execute audit test
            print("\n🚀 Running audit system test...")
            test_success = await self.test_executor.execute_audit_test()
            
            if test_success:
                print("✅ Audit system test completed successfully")
            else:
                print("⚠️ Audit system test had issues")
            
            # Wait for data settlement
            await self.test_executor.wait_for_data_settlement()
            
            # Get final counts
            sessions_after, calls_after = await self.test_executor.get_baseline_counts()
            
            # Calculate deltas
            sessions_created = sessions_after - sessions_before
            calls_created = calls_after - calls_before
            
            self.reporter.print_delta_metrics(sessions_created, calls_created)
            
            # Get latest session details
            latest_session, session_calls = await self.test_executor.get_latest_session_data()
            
            # Create result
            result = ValidationResult(
                success=sessions_created > 0 and calls_created > 0,
                sessions_created=sessions_created,
                calls_created=calls_created,
                latest_session=latest_session,
                session_calls=session_calls
            )
            
            # Set error message if needed
            if not result.success:
                if sessions_created == 0 and calls_created == 0:
                    result.error_message = "No new audit data recorded"
                elif sessions_created == 0:
                    result.error_message = "No session summaries recorded"
                elif calls_created == 0:
                    result.error_message = "No individual LLM calls recorded"
            
            # Print results
            print(f"\n{result.status_message}")
            
            if result.success and latest_session:
                self.reporter.print_session_details(latest_session)
                self.reporter.print_llm_calls(session_calls)
            
            # Log final result
            if result.success:
                logger.info("Audit validation completed successfully")
            else:
                logger.warning(f"Audit validation issues: {result.error_message}")
            
            return result
            
        except Exception as e:
            error_msg = f"Validation pipeline failed: {e}"
            logger.error(error_msg, exc_info=True)
            print(f"❌ Error during validation: {e}")
            
            return ValidationResult(
                success=False,
                sessions_created=0,
                calls_created=0,
                error_message=error_msg
            )


async def main() -> None:
    """Main function with proper error handling and logging."""
    try:
        orchestrator = AuditValidationOrchestrator()
        result = await orchestrator.run_validation()
        
        # Exit with appropriate code
        sys.exit(0 if result.success else 1)
        
    except Exception as e:
        logger.error(f"Main execution failed: {e}", exc_info=True)
        print(f"❌ Critical error: {e}")
        sys.exit(1)


async def test_complete_audit_pipeline():
    """Run a comprehensive test of the audit pipeline"""
    print("=" * 70)
    print("🔍 FINAL AUDIT PIPELINE VALIDATION")
    print("=" * 70)
    
    # Get database connection
    database_url = config.database.url
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return

    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to database")
        
        # Count sessions and calls before test
        session_count_before = await conn.fetchval("SELECT COUNT(*) FROM audit_sessions")
        calls_count_before = await conn.fetchval("SELECT COUNT(*) FROM llm_calls")
        print(f"📊 Before test: {session_count_before} sessions, {calls_count_before} LLM calls")
        
        # Run the debug audit system
        print("\n🚀 Running audit system test...")
        process = await asyncio.create_subprocess_exec(
            "python", "debug_audit_system.py",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            print("✅ Audit system test completed successfully")
        else:
            print(f"⚠️ Audit system test returned code {process.returncode}")
        
        # Wait a moment for database writes to complete
        await asyncio.sleep(1)
        
        # Count sessions and calls after test
        session_count_after = await conn.fetchval("SELECT COUNT(*) FROM audit_sessions")
        calls_count_after = await conn.fetchval("SELECT COUNT(*) FROM llm_calls")
        print(f"📊 After test: {session_count_after} sessions, {calls_count_after} LLM calls")
        
        # Verify new data was created
        new_sessions = session_count_after - session_count_before
        new_calls = calls_count_after - calls_count_before
        
        print(f"\n📈 New data created:")
        print(f"   📝 Sessions: +{new_sessions}")
        print(f"   📞 LLM Calls: +{new_calls}")
        
        if new_sessions > 0 and new_calls > 0:
            print("\n🎉 SUCCESS! Both session totals AND individual LLM calls are being recorded!")
            
            # Get the latest session details
            latest_session = await conn.fetchrow("""
                SELECT id, session_type, total_cost, total_tokens, call_count, start_time
                FROM audit_sessions 
                ORDER BY start_time DESC 
                LIMIT 1
            """)
            
            if latest_session:
                print(f"\n📊 Latest session details:")
                print(f"   🆔 ID: {latest_session['id'][:8]}...")
                print(f"   📝 Type: {latest_session['session_type']}")
                print(f"   💰 Cost: ${latest_session['total_cost']:.4f}")
                print(f"   🎯 Tokens: {latest_session['total_tokens']}")
                print(f"   📞 Calls: {latest_session['call_count']}")
                
                # Get LLM calls for this session
                session_calls = await conn.fetch("""
                    SELECT model, input_tokens, output_tokens, total_cost, phase, agent_role
                    FROM llm_calls 
                    WHERE audit_session_id = $1
                    ORDER BY timestamp
                """, latest_session['id'])
                
                print(f"\n📞 LLM calls for this session ({len(session_calls)} calls):")
                for i, call in enumerate(session_calls, 1):
                    print(f"   {i}. {call['model']} | {call['phase']} | {call['agent_role']} | "
                          f"{call['input_tokens']}→{call['output_tokens']} tokens | ${call['total_cost']:.6f}")
                
        elif new_sessions > 0:
            print("\n⚠️ PARTIAL SUCCESS: Sessions recorded but no individual LLM calls")
        elif new_calls > 0:
            print("\n⚠️ PARTIAL SUCCESS: LLM calls recorded but no session summaries")
        else:
            print("\n❌ FAILURE: No new audit data recorded")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error during validation: {e}")

if __name__ == "__main__":
    # Use the new refactored version by default, keep old version for compatibility
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--legacy":
        asyncio.run(test_complete_audit_pipeline())
    else:
        asyncio.run(main())