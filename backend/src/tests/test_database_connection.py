#!/usr/bin/env python3
# flake8: noqa
"""
Test database connectivity for the blog generation system.
"""
import asyncio
import sys
import os

sys.path.append("/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/src")

from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker


async def test_database_connection():
    print("🔍 Testing Database Connection")
    print("=" * 40)

    try:
        # Test database connection using the same method as task manager
        print("\n1. Testing audit tracker database connection...")
        tracker = EnhancedDatabaseAuditTracker(
            session_type="diagnostic_test", user_id="test_user", blog_id=None
        )

        pool = await tracker._get_database_connection()
        if not pool:
            print("   ❌ Failed to get database connection pool")
            return

        print("   ✅ Database connection pool obtained")

        # Test a simple query
        print("\n2. Testing simple database query...")
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT version()")
            print(f"   ✅ Database version: {result}")

            # Test blogs table existence
            print("\n3. Testing blogs table...")
            table_exists = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'blogs'
                )
            """
            )

            if table_exists:
                print("   ✅ Blogs table exists")

                # Count blogs
                blog_count = await conn.fetchval("SELECT COUNT(*) FROM blogs")
                print(f"   📊 Total blogs in database: {blog_count}")

                # Show recent blogs
                recent_blogs = await conn.fetch(
                    """
                    SELECT id, user_id, topic, status, created_at 
                    FROM blogs 
                    ORDER BY created_at DESC 
                    LIMIT 5
                """
                )

                print(f"   📝 Recent blogs:")
                for blog in recent_blogs:
                    print(
                        f"      - {blog['id'][:8]}... | {blog['status']} | {blog['topic'][:30]}..."
                    )
            else:
                print("   ❌ Blogs table does not exist")

    except Exception as e:
        print(f"   ❌ Database test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_database_connection())
