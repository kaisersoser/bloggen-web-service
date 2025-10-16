#!/usr/bin/env python3
"""
Test database connection with current DATABASE_URL configuration.

This script safely tests the PostgreSQL connection without exposing credentials.
Run: python test_db_connection.py

Requires DATABASE_URL environment variable to be set.
"""

import asyncio
import os
import sys
from urllib.parse import urlparse

try:
    import asyncpg
except ImportError:
    print("❌ Error: asyncpg not installed. Run: pip install asyncpg")
    sys.exit(1)


async def test_connection():
    """Test database connection and report results."""
    
    # Read DATABASE_URL from environment
    database_url = os.environ.get("DATABASE_URL")
    
    if not database_url:
        print("❌ Error: DATABASE_URL environment variable not set")
        print("\nUsage:")
        print("  export DATABASE_URL='your_connection_string'")
        print("  python test_db_connection.py")
        return False
    
    # Parse URL to show sanitized connection info (without password)
    try:
        parsed = urlparse(database_url)
        print("🔍 Testing database connection...")
        print(f"   Scheme: {parsed.scheme}")
        print(f"   Host: {parsed.hostname}")
        print(f"   Port: {parsed.port}")
        print(f"   Database: {parsed.path}")
        print(f"   Username: {parsed.username}")
        print(f"   Password: {'*' * len(parsed.password) if parsed.password else 'NOT SET'}")
        print()
    except Exception as e:
        print(f"⚠️ Warning: Could not parse URL: {e}")
        print()
    
    # Test connection
    print("🔌 Attempting to connect...")
    pool = None
    
    try:
        # Create connection pool with timeout
        pool = await asyncio.wait_for(
            asyncpg.create_pool(
                database_url,
                min_size=1,
                max_size=1,
                command_timeout=10,
                timeout=10,
            ),
            timeout=15
        )
        
        print("✅ Connection pool created successfully!")
        
        # Test a simple query
        print("🧪 Testing simple query...")
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT version()")
            print(f"✅ Query executed successfully!")
            print(f"   PostgreSQL version: {result[:50]}...")
            
            # Check if we can see tables
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                LIMIT 5
            """)
            print(f"\n📊 Found {len(tables)} tables in database:")
            for table in tables:
                print(f"   - {table['table_name']}")
        
        print("\n✅ SUCCESS: Database connection is working correctly!")
        return True
        
    except asyncio.TimeoutError:
        print("❌ TIMEOUT: Connection attempt timed out after 15 seconds")
        print("\nPossible causes:")
        print("  1. Network connectivity issues")
        print("  2. Firewall blocking connection")
        print("  3. Incorrect host/port")
        print("  4. Database server is down")
        return False
        
    except asyncpg.InvalidPasswordError:
        print("❌ AUTHENTICATION FAILED: Invalid password")
        print("\nPossible causes:")
        print("  1. Incorrect password in DATABASE_URL")
        print("  2. Password contains special characters that need URL encoding")
        print("  3. Double colon (::) instead of single colon (:) in URL")
        print("\nTips:")
        print("  - Check for :: vs : in the URL")
        print("  - URL encode special characters (! = %21, @ = %40, etc.)")
        return False
        
    except asyncpg.InvalidCatalogNameError:
        print("❌ DATABASE NOT FOUND: Invalid database name")
        print("\nCheck that the database name in the URL is correct")
        return False
        
    except OSError as e:
        print(f"❌ NETWORK ERROR: {e}")
        print("\nPossible causes:")
        print("  1. Incorrect hostname in DATABASE_URL")
        print("  2. DNS resolution failure")
        print("  3. Network unreachable (firewall/routing issue)")
        print("  4. Supabase project is paused or deleted")
        return False
        
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {type(e).__name__}: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        return False
        
    finally:
        if pool:
            print("\n🧹 Closing connection pool...")
            await pool.close()
            print("✅ Pool closed")


def main():
    """Main entry point."""
    print("=" * 70)
    print("DATABASE CONNECTION TEST")
    print("=" * 70)
    print()
    
    # Run async test
    success = asyncio.run(test_connection())
    
    print()
    print("=" * 70)
    if success:
        print("✅ TEST PASSED: Database connection is working!")
        sys.exit(0)
    else:
        print("❌ TEST FAILED: Database connection is NOT working")
        sys.exit(1)


if __name__ == "__main__":
    main()
