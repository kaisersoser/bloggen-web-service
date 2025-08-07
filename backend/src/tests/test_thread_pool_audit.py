#!/usr/bin/env python3
"""
Test to verify that audit tracking works with thread pool execution (like in real blog generation)
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker
from core.llm_interceptor import setup_llm_interceptor, connect_audit_tracker
from bloggen.flows import BlogGenerationFlow

# Load environment variables
load_dotenv()

async def test_thread_pool_audit():
    """Test audit tracking in thread pool execution (simulating real blog generation)"""
    print("🧪 Testing Thread Pool Audit Integration")
    print("=" * 50)
    
    # 1. Set up LLM interceptor (this happens in FastAPI startup)
    print("📡 Setting up LLM interceptor...")
    callback_handler = setup_llm_interceptor()
    
    if not callback_handler:
        print("❌ LLM interceptor setup failed!")
        return False
    
    # 2. Create audit tracker (this happens in FastAPI endpoint)
    print("📋 Creating audit tracker...")
    audit_tracker = EnhancedDatabaseAuditTracker(
        session_type="thread_pool_test",
        user_id="cmdaiv5530000z9nxqmyg445v",
        blog_id="test_blog_123"
    )
    
    # Start audit session in main thread
    await audit_tracker.start_session()
    print(f"✅ Audit session started: {audit_tracker.session_id}")
    
    # 3. Simulate thread pool execution (like run_in_executor)
    print("🔄 Testing thread pool execution...")
    
    loop = asyncio.get_event_loop()
    
    def run_in_thread():
        """This simulates what happens in the thread pool for blog generation"""
        print("  🧵 Running in thread pool...")
        
        # Connect audit tracker in thread (this is the new fix)
        connect_result = connect_audit_tracker(audit_tracker)
        print(f"  🔗 Audit tracker connection result: {connect_result}")
        
        # Simulate LLM call in thread
        try:
            import litellm
            
            # Make a test API call
            response = litellm.completion(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello from thread pool test"}],
                max_tokens=5
            )
            
            print("  ✅ LLM call completed in thread")
            return True
            
        except Exception as e:
            print(f"  ❌ Thread LLM call failed: {e}")
            return False
    
    # Run in thread pool (like the real system)
    thread_result = await loop.run_in_executor(None, run_in_thread)
    
    # 4. Check audit results
    print("\n📊 Checking audit results...")
    await asyncio.sleep(1)  # Give callbacks time to process
    
    summary = audit_tracker.get_session_summary()
    print(f"   Session ID: {summary['session_id']}")
    print(f"   Total Cost: ${summary['total_cost']:.4f}")
    print(f"   Total Tokens: {summary['total_tokens']}")
    print(f"   Call Count: {summary['call_count']}")
    print(f"   Database Enabled: {summary['database_enabled']}")
    
    # 5. End session
    await audit_tracker.end_session()
    
    success = summary['call_count'] > 0
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Thread pool audit tracking {'works' if success else 'failed'}!")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(test_thread_pool_audit())
    
    if success:
        print("\n🎉 Thread pool audit tracking is working!")
        sys.exit(0)
    else:
        print("\n❌ Thread pool audit tracking failed!")
        sys.exit(1)
