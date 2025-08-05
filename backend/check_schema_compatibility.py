#!/usr/bin/env python3
"""
Schema Compatibility Checker

Compares the current database schema with what the frontend Prisma 
schema expects to ensure full compatibility with admin analytics.
"""

import asyncio
import asyncpg
import os

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

# Load .env file
load_env_file()


async def check_schema_compatibility():
    """Check database schema compatibility with Prisma frontend."""
    
    print("\n" + "="*70)
    print("🔍 SCHEMA COMPATIBILITY CHECK")
    print("="*70)
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ No DATABASE_URL found")
        return
    
    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to Supabase database")
        
        # Check audit_sessions table structure
        print("\n1️⃣ Checking audit_sessions table vs Prisma schema...")
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'audit_sessions' 
            AND table_schema = 'public'
            ORDER BY ordinal_position;
        """)
        
        # Expected Prisma schema fields
        expected_fields = {
            'id': 'text',
            'blog_id': 'text',  # nullable
            'user_id': 'text',
            'session_type': 'text',
            'start_time': 'timestamp without time zone',
            'end_time': 'timestamp without time zone',  # nullable
            'total_cost': 'double precision',
            'total_tokens': 'integer',
            'input_tokens': 'integer',
            'output_tokens': 'integer',
            'call_count': 'integer',
            'created_at': 'timestamp without time zone'
        }
        
        print("   Current database schema:")
        current_fields = {}
        for col in columns:
            current_fields[col['column_name']] = col['data_type']
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            print(f"   📝 {col['column_name']}: {col['data_type']} {nullable}")
        
        print("\n   Compatibility check:")
        for field, expected_type in expected_fields.items():
            if field in current_fields:
                if current_fields[field] == expected_type:
                    print(f"   ✅ {field}: {expected_type}")
                else:
                    print(f"   ⚠️  {field}: expected {expected_type}, got {current_fields[field]}")
            else:
                print(f"   ❌ {field}: MISSING")
        
        # Check for extra fields
        for field in current_fields:
            if field not in expected_fields:
                print(f"   🆕 {field}: EXTRA FIELD")
        
        # Check llm_calls table structure
        print("\n2️⃣ Checking llm_calls table vs Prisma schema...")
        llm_columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'llm_calls' 
            AND table_schema = 'public'
            ORDER BY ordinal_position;
        """)
        
        # Expected Prisma LLMCall schema
        expected_llm_fields = {
            'id': 'text',
            'audit_session_id': 'text',
            'model': 'text',
            'input_tokens': 'integer',
            'output_tokens': 'integer',
            'input_cost': 'double precision',
            'output_cost': 'double precision',
            'total_cost': 'double precision',
            'phase': 'text',
            'agent_role': 'text',
            'call_type': 'text',
            'timestamp': 'timestamp without time zone'
        }
        
        if llm_columns:
            print("   Current llm_calls schema:")
            current_llm_fields = {}
            for col in llm_columns:
                current_llm_fields[col['column_name']] = col['data_type']
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                print(f"   📝 {col['column_name']}: {col['data_type']} {nullable}")
            
            print("\n   LLM Calls compatibility check:")
            for field, expected_type in expected_llm_fields.items():
                if field in current_llm_fields:
                    if current_llm_fields[field] == expected_type:
                        print(f"   ✅ {field}: {expected_type}")
                    else:
                        print(f"   ⚠️  {field}: expected {expected_type}, got {current_llm_fields[field]}")
                else:
                    print(f"   ❌ {field}: MISSING")
        else:
            print("   ❌ llm_calls table does not exist")
        
        # Test a sample query that the frontend would run
        print("\n3️⃣ Testing frontend-compatible queries...")
        try:
            # This mimics the Prisma query from the admin analytics
            result = await conn.fetch("""
                SELECT 
                    s.id,
                    s.created_at,
                    s.total_cost,
                    s.total_tokens,
                    s.call_count,
                    COUNT(l.id) as actual_llm_calls
                FROM audit_sessions s
                LEFT JOIN llm_calls l ON s.id = l.audit_session_id
                WHERE s.created_at >= NOW() - INTERVAL '7 days'
                GROUP BY s.id, s.created_at, s.total_cost, s.total_tokens, s.call_count
                ORDER BY s.created_at DESC
                LIMIT 5;
            """)
            
            if result:
                print("   ✅ Frontend query structure compatible")
                print(f"   📊 Found {len(result)} recent audit sessions")
                for row in result:
                    print(f"   📈 Session {row['id'][:8]}...: ${row['total_cost']:.4f}, {row['total_tokens']} tokens, {row['actual_llm_calls']} LLM calls")
            else:
                print("   ⚠️  No recent audit sessions found")
                
        except Exception as e:
            print(f"   ❌ Frontend query failed: {e}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Schema compatibility check failed: {e}")


async def main():
    """Main function."""
    print("Starting schema compatibility check...")
    await check_schema_compatibility()
    print("\nCompatibility check complete!")


if __name__ == "__main__":
    asyncio.run(main())
