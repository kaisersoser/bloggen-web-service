#!/usr/bin/env python3
# flake8: noqa
"""
Test database connectivity for the blog generation system.
Updated to use Phase 3.1 DatabaseService instead of legacy methods.
"""
import asyncio
import sys
import os

sys.path.append("/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/src")

from core.database_service import database_service


async def test_database_connection():
    print("🔍 Testing Database Connection (Phase 3.1 DatabaseService)")
    print("=" * 60)

    try:
        # Test database connection using new DatabaseService
        print("\n1. Initializing DatabaseService (shared pool)...")
        database_url = os.getenv(
            'DATABASE_URL',
            'postgresql://postgres:postgres@localhost:5432/bloggen'
        )
        
        pool = await database_service.initialize(
            database_url,
            min_size=1,
            max_size=10
        )
        
        if not pool:
            print("   ❌ Failed to initialize database service")
            return

        print("   ✅ DatabaseService initialized with shared pool")

        # Test a simple query
        print("\n2. Testing simple database query...")
        async with database_service.acquire() as conn:
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
        
        # Test pool statistics
        print("\n4. Testing pool statistics...")
        pool_size = pool.get_size()
        idle_size = pool.get_idle_size()
        print(f"   📊 Pool size: {pool_size}")
        print(f"   📊 Idle connections: {idle_size}")
        print(f"   ✅ Pool statistics accessible")

    except Exception as e:
        print(f"   ❌ Database test failed: {e}")
        import traceback

        traceback.print_exc()
    
    finally:
        # Clean up
        print("\n5. Closing database service...")
        await database_service.close()
        print("   ✅ Database service closed")


if __name__ == "__main__":
    asyncio.run(test_database_connection())
