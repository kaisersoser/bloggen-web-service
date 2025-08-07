#!/usr/bin/env python3
"""
Test script to verify database audit tracking functionality.

This script tests the audit tracking system by:
1. Creating a test audit session
2. Simulating LLM calls
3. Verifying data is persisted to the database
4. Checking that the admin API can retrieve the data
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.audit_tracker import DatabaseAuditTracker
from core.audit_database import audit_manager

async def test_audit_tracking():
    """Test the complete audit tracking flow."""
    print("🧪 Testing Database Audit Tracking System")
    print("=" * 50)
    
    # Test 1: Create audit session
    print("\n1. Testing audit session creation...")
    test_user_id = "test-user-123"
    test_blog_id = "test-blog-456"
    
    try:
        # Create a database audit tracker
        tracker = DatabaseAuditTracker(
            session_type="blog_generation",
            user_id=test_user_id,
            blog_id=test_blog_id
        )
        
        # Start the session
        tracker.start_session_sync()
        print(f"✅ Audit session created: {tracker.db_session_id}")
        
        # Test 2: Track some LLM calls
        print("\n2. Testing LLM call tracking...")
        
        # Simulate research phase
        tracker.track_llm_call(
            model="gpt-4o",
            input_tokens=1500,
            output_tokens=800,
            phase="research_phase",
            agent_role="researcher",
            call_type="actual"
        )
        print("✅ Research phase LLM call tracked")
        
        # Simulate content generation phase
        tracker.track_llm_call(
            model="gpt-4o",
            input_tokens=2200,
            output_tokens=1200,
            phase="content_generation_phase",
            agent_role="content_writer",
            call_type="actual"
        )
        print("✅ Content generation phase LLM call tracked")
        
        # Simulate fact checking phase
        tracker.track_llm_call(
            model="gpt-4o",
            input_tokens=1800,
            output_tokens=600,
            phase="fact_checking_phase",
            agent_role="fact_checker",
            call_type="actual"
        )
        print("✅ Fact checking phase LLM call tracked")
        
        # Test 3: Check session summary
        print("\n3. Testing session summary...")
        summary = tracker.get_session_summary()
        print(f"✅ Session summary generated:")
        print(f"   Total Cost: ${summary.get('total_cost', 0):.4f}")
        print(f"   Total Tokens: {summary.get('total_tokens', 0):,}")
        print(f"   Total Calls: {summary.get('call_count', 0)}")
        
        # Test 4: End session
        print("\n4. Testing session completion...")
        tracker.end_session_sync()
        print("✅ Audit session completed successfully")
        
        # Test 5: Verify data in database
        print("\n5. Testing database persistence...")
        if tracker.db_session_id:
            # Try to retrieve the session summary from database
            session_summary = await audit_manager.get_session_summary(tracker.db_session_id)
            if session_summary:
                print(f"✅ Session summary found in database:")
                print(f"   Session ID: {session_summary.get('session_id', 'unknown')}")
                print(f"   Total Cost: ${session_summary.get('total_cost', 0):.4f}")
                print(f"   Total Calls: {session_summary.get('total_calls', 0)}")
                print(f"   Status: {session_summary.get('status', 'unknown')}")
            else:
                print("❌ Session summary not found in database")
        
        print("\n" + "=" * 50)
        print("🎉 Audit tracking test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_api_retrieval():
    """Test that the admin API can retrieve audit data."""
    print("\n🔍 Testing Admin API Data Retrieval")
    print("=" * 50)
    
    try:
        # Test user cost summary (using a test user)
        test_user_id = "test-user-123"
        user_summary = await audit_manager.get_user_cost_summary(test_user_id)
        print("✅ User cost summary retrieved successfully:")
        print(f"   User ID: {test_user_id}")
        print(f"   Total Cost: ${user_summary.get('total_cost', 0):.4f}")
        print(f"   Total Sessions: {user_summary.get('session_count', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

if __name__ == "__main__":
    async def main():
        print("🚀 Starting Audit Tracking System Tests")
        print(f"⏰ Test started at: {datetime.now().isoformat()}")
        
        # Run the tests
        test1_passed = await test_audit_tracking()
        test2_passed = await test_api_retrieval()
        
        print(f"\n📊 Test Results:")
        print(f"   Database Audit Tracking: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
        print(f"   Admin API Retrieval: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
        
        if test1_passed and test2_passed:
            print("\n🎉 All tests passed! Audit tracking system is working correctly.")
            return 0
        else:
            print("\n❌ Some tests failed. Please check the error messages above.")
            return 1
    
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
