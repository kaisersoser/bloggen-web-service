#!/usr/bin/env python3
"""
Final comprehensive audit system validation test.
Tests the complete audit pipeline to ensure both session totals AND individual LLM calls are properly recorded.
"""

import asyncio
import asyncpg
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_complete_audit_pipeline():
    """Run a comprehensive test of the audit pipeline"""
    print("=" * 70)
    print("🔍 FINAL AUDIT PIPELINE VALIDATION")
    print("=" * 70)
    
    # Get database connection
    database_url = os.getenv('DATABASE_URL')
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
    asyncio.run(test_complete_audit_pipeline())
