#!/usr/bin/env python3
# flake8: noqa
"""
Supabase Database Diagnostic Tool

This script tests the Supabase connection and verifies that the audit system
is working correctly with the proper database tables.
"""

import sys
import os
import asyncio
import asyncpg
from datetime import datetime

# Add src to path
sys.path.append("src")

from core.config import config
from core.common import get_logger
from core.model_config import get_default_model

logger = get_logger(__name__)


async def test_supabase_direct_connection():
    """Test direct connection to Supabase PostgreSQL database"""
    print("🔍 Testing Direct Supabase PostgreSQL Connection")
    print("=" * 60)

    try:
        # Get database URL from config
        db_url = config.database.url
        print(f"Database URL configured: {bool(db_url)}")

        if not db_url:
            print("❌ No DATABASE_URL configured")
            return False

        # Check if URL looks like Supabase
        if "supabase.co" not in db_url:
            print(f"⚠️ URL does not appear to be Supabase: {db_url[:30]}...")

        # Test direct PostgreSQL connection
        print("🔗 Attempting direct PostgreSQL connection...")

        conn = await asyncpg.connect(db_url)
        print("✅ Direct PostgreSQL connection successful!")

        # Check if audit tables exist
        print("🔍 Checking for audit tables...")

        tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('audit_sessions', 'llm_calls')
        ORDER BY table_name;
        """

        tables = await conn.fetch(tables_query)
        print(f'Found audit tables: {[row["table_name"] for row in tables]}')

        if not tables:
            print("⚠️ No audit tables found. Creating them...")
            await create_audit_tables(conn)

        # Check recent audit sessions
        print("📊 Checking recent audit sessions...")
        try:
            sessions_query = """
            SELECT session_id, session_type, user_id, created_at, total_cost, total_tokens, api_calls_count
            FROM audit_sessions 
            ORDER BY created_at DESC 
            LIMIT 5;
            """

            sessions = await conn.fetch(sessions_query)
            print(f"Recent audit sessions ({len(sessions)} found):")
            for session in sessions:
                print(f"  - {dict(session)}")

        except Exception as e:
            print(f"⚠️ Could not query audit_sessions: {e}")

        # Check recent LLM calls
        print("📊 Checking recent LLM calls...")
        try:
            calls_query = """
            SELECT session_id, model, input_tokens, output_tokens, cost, timestamp
            FROM llm_calls 
            ORDER BY timestamp DESC 
            LIMIT 5;
            """

            calls = await conn.fetch(calls_query)
            print(f"Recent LLM calls ({len(calls)} found):")
            for call in calls:
                print(f"  - {dict(call)}")

        except Exception as e:
            print(f"⚠️ Could not query llm_calls: {e}")

        await conn.close()
        return True

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def create_audit_tables(conn):
    """Create audit tables if they don't exist"""
    print("🛠️ Creating audit tables...")

    # Create audit_sessions table
    audit_sessions_sql = """
    CREATE TABLE IF NOT EXISTS audit_sessions (
        session_id VARCHAR(255) PRIMARY KEY,
        session_type VARCHAR(100) NOT NULL,
        user_id VARCHAR(255) NOT NULL,
        blog_id VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ended_at TIMESTAMP,
        total_cost DECIMAL(10, 6) DEFAULT 0,
        total_tokens INTEGER DEFAULT 0,
        api_calls_count INTEGER DEFAULT 0,
        metadata JSONB
    );
    """

    # Create llm_calls table
    llm_calls_sql = """
    CREATE TABLE IF NOT EXISTS llm_calls (
        id SERIAL PRIMARY KEY,
        session_id VARCHAR(255) REFERENCES audit_sessions(session_id),
        model VARCHAR(100) NOT NULL,
        input_tokens INTEGER NOT NULL,
        output_tokens INTEGER NOT NULL,
        cost DECIMAL(10, 6) NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        phase VARCHAR(100),
        agent VARCHAR(100),
        user_id VARCHAR(255),
        blog_id VARCHAR(255)
    );
    """

    # Create indexes
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_audit_sessions_user_id ON audit_sessions(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_audit_sessions_created_at ON audit_sessions(created_at);",
        "CREATE INDEX IF NOT EXISTS idx_llm_calls_session_id ON llm_calls(session_id);",
        "CREATE INDEX IF NOT EXISTS idx_llm_calls_timestamp ON llm_calls(timestamp);",
        "CREATE INDEX IF NOT EXISTS idx_llm_calls_user_id ON llm_calls(user_id);",
    ]

    try:
        await conn.execute(audit_sessions_sql)
        print("✅ Created audit_sessions table")

        await conn.execute(llm_calls_sql)
        print("✅ Created llm_calls table")

        for index_sql in indexes_sql:
            await conn.execute(index_sql)
        print("✅ Created indexes")

    except Exception as e:
        print(f"❌ Failed to create tables: {e}")


async def test_audit_tracker():
    """Test the audit tracker functionality"""
    print("\\n🧪 Testing Enhanced Audit Tracker")
    print("=" * 40)

    try:
        from core import EnhancedDatabaseAuditTracker

        # Create a test tracker
        tracker = EnhancedDatabaseAuditTracker(
            session_type="test_diagnostic",
            user_id="test_user_123",
            blog_id="test_blog_456",
        )

        print(f"✅ Tracker created: {tracker.session.session_id}")

        # Start session
        await tracker.start_session()
        print("✅ Session started")

        # Track a test API call
        tracker.track_api_call(
            model=get_default_model(),
            input_tokens=50,
            output_tokens=25,
            phase="diagnostic_test",
        )
        print("✅ API call tracked")

        # End session
        await tracker.end_session()
        print("✅ Session ended")

        # Print summary
        summary = tracker.get_session_summary()
        print(f"📊 Session Summary: {summary}")

        return True

    except Exception as e:
        print(f"❌ Audit tracker test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Main diagnostic function"""
    print("🚀 Supabase Database Diagnostic Tool")
    print("=" * 60)
    print(f"Environment: {config.server.environment}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # Test 1: Direct database connection
    db_success = await test_supabase_direct_connection()

    # Test 2: Audit tracker functionality
    if db_success:
        tracker_success = await test_audit_tracker()
    else:
        print("⏭️ Skipping audit tracker test due to database connection failure")
        tracker_success = False

    # Summary
    print("\\n📋 Diagnostic Summary")
    print("=" * 30)
    print(f'Database Connection: {"✅ PASS" if db_success else "❌ FAIL"}')
    print(f'Audit Tracker: {"✅ PASS" if tracker_success else "❌ FAIL"}')

    if db_success and tracker_success:
        print("\\n🎉 All systems operational!")
    else:
        print("\\n⚠️ Some issues detected. Check the output above for details.")

    return db_success and tracker_success


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\\n❌ Diagnostic interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\\n💥 Diagnostic crashed: {e}")
        sys.exit(1)
