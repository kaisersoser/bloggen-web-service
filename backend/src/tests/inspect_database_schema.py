#!/usr/bin/env python3
"""
Database Schema Inspector

Check the current Supabase database schema to understand
what tables and columns exist for audit logging.
"""

import asyncio
import asyncpg
import os
import sys

# Add the backend src to path
sys.path.insert(0, '/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/src')

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file."""
    env_path = '/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/.env'
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"').strip("'")
                    os.environ[key] = value
        print(f"✅ Loaded environment variables from {env_path}")
    else:
        print(f"❌ .env file not found at {env_path}")

# Load .env file
load_env_file()


async def inspect_database_schema():
    """Inspect the current database schema."""
    
    print("\n" + "="*70)
    print("🔍 DATABASE SCHEMA INSPECTION")
    print("="*70)
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ No DATABASE_URL found")
        return
    
    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to Supabase database")
        
        # Check what tables exist
        print("\n1️⃣ Checking existing tables...")
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        
        if tables:
            print("Found tables:")
            for table in tables:
                print(f"   📋 {table['table_name']}")
        else:
            print("   No tables found")
        
        # Check audit_sessions table if it exists
        audit_sessions_exists = any(t['table_name'] == 'audit_sessions' for t in tables)
        if audit_sessions_exists:
            print("\n2️⃣ Inspecting audit_sessions table structure...")
            columns = await conn.fetch("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'audit_sessions' 
                AND table_schema = 'public'
                ORDER BY ordinal_position;
            """)
            
            print("   Columns:")
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"   📝 {col['column_name']}: {col['data_type']} {nullable}{default}")
        else:
            print("\n❌ audit_sessions table does not exist")
        
        # Check audit_llm_calls table if it exists
        audit_calls_exists = any(t['table_name'] == 'audit_llm_calls' for t in tables)
        if audit_calls_exists:
            print("\n3️⃣ Inspecting audit_llm_calls table structure...")
            columns = await conn.fetch("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'audit_llm_calls' 
                AND table_schema = 'public'
                ORDER BY ordinal_position;
            """)
            
            print("   Columns:")
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"   📝 {col['column_name']}: {col['data_type']} {nullable}{default}")
        else:
            print("\n❌ audit_llm_calls table does not exist")
        
        # Sample existing data if any
        if audit_sessions_exists:
            print("\n4️⃣ Checking existing audit sessions data...")
            sessions = await conn.fetch("SELECT * FROM audit_sessions LIMIT 5")
            if sessions:
                print(f"   Found {len(sessions)} sample session(s):")
                for session in sessions:
                    print(f"   🎯 {dict(session)}")
            else:
                print("   No existing sessions found")
        
        # Check for valid user IDs
        print("\n📝 Checking existing users for valid user_id...")
        users = await conn.fetch("SELECT id, email FROM users LIMIT 3")
        if users:
            print(f"   Found {len(users)} user(s):")
            for user in users:
                print(f"   👤 {user['id']} - {user['email']}")
        else:
            print("   No users found")
        
        if audit_calls_exists:
            print("\n5️⃣ Checking existing LLM calls data...")
            calls = await conn.fetch("SELECT * FROM audit_llm_calls LIMIT 3")
            if calls:
                print(f"   Found {len(calls)} sample call(s):")
                for call in calls:
                    print(f"   💰 {dict(call)}")
            else:
                print("   No existing calls found")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Database inspection failed: {e}")


async def main():
    """Main function."""
    print("Starting database schema inspection...")
    await inspect_database_schema()
    print("\nInspection complete!")


if __name__ == "__main__":
    asyncio.run(main())
