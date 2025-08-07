#!/usr/bin/env python3
"""
Integration test for LLM interceptor with audit tracking
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker
from core.llm_interceptor import setup_llm_interceptor
from core.context_vars import (
    set_audit_context, 
    current_audit_tracker, 
    current_phase, 
    current_request_id, 
    current_user_id
)

# Load environment variables
load_dotenv()

def test_success_callback(kwargs, response_obj, start_time, end_time):
    print("🎯 TEST CALLBACK FIRED!")
    print(f"   Model: {kwargs.get('model', 'unknown')}")
    if hasattr(response_obj, 'usage'):
        print(f"   Tokens: {response_obj.usage.total_tokens}")

async def test_llm_interceptor_integration():
    """
    Test the LLM interceptor integration with audit tracking
    """
    print("🧪 Testing LLM Interceptor Integration")
    print("=" * 50)
    
    # 1. Set up the LLM interceptor
    print("📡 Setting up LLM interceptor...")
    callback_handler = setup_llm_interceptor()
    
    if callback_handler:
        # Add the test callback to verify callbacks work
        import litellm
        litellm.success_callback.append(test_success_callback)
        litellm._async_success_callback.append(test_success_callback)
        print(f"   Total sync callbacks: {len(litellm.success_callback)}")
        print(f"   Total async callbacks: {len(litellm._async_success_callback)}")
    
    if not callback_handler:
        print("❌ LLM interceptor setup failed!")
        return False
    
    # 2. Create audit tracker
    print("📋 Creating audit tracker...")
    audit_tracker = EnhancedDatabaseAuditTracker(
        session_type="integration_test",
        user_id="cmdaiv5530000z9nxqmyg445v",
        blog_id=None  # No blog_id for this test
    )
    
    # 3. Set up context
    print("🔧 Setting up context...")
    set_audit_context(audit_tracker, "test_session_123")
    current_phase.set("testing")
    
    # 4. Start audit session
    print("🚀 Starting audit session...")
    await audit_tracker.start_session()
    
    # 5. Make actual API calls
    print("💬 Making OpenAI API calls...")
    
    try:
        import litellm
        
        # Check for API key
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            print("❌ OPENAI_API_KEY not found in environment!")
            return False

        # Test sync call
        print("   Testing sync completion...")
        sync_response = litellm.completion(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say hello in exactly 5 words."}],
            temperature=0.1,
            max_tokens=20
        )
        print("✅ Sync call completed")
        
        # Give callbacks time to process
        await asyncio.sleep(0.5)
        
        # Check status after sync call
        summary = audit_tracker.get_session_summary()
        print(f"   After sync call - Call Count: {summary['call_count']}")
        
        # Test async call
        print("   Testing async completion...")
        async_response = await litellm.acompletion(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say hello in exactly 5 words."}],
            temperature=0.1,
            max_tokens=20
        )
        print("✅ Async call completed")
        
        # Give callbacks time to process
        await asyncio.sleep(0.5)
        
        # Check status after async call
        summary = audit_tracker.get_session_summary()
        print(f"   After async call - Call Count: {summary['call_count']}")
        
    except Exception as e:
        print(f"❌ OpenAI API call failed: {e}")
        return False
    
    # 6. Check final audit tracker state
    print("\n📊 Checking final audit tracker state...")
    summary = audit_tracker.get_session_summary()
    
    print(f"   Session ID: {summary['session_id']}")
    print(f"   Total Cost: ${summary['total_cost']:.4f}")
    print(f"   Total Tokens: {summary['total_tokens']}")
    print(f"   Call Count: {summary['call_count']}")
    print(f"   Database Enabled: {summary['database_enabled']}")
    
    if summary['call_count'] > 0:
        print("✅ LLM interceptor is working!")
        print("\n📝 Intercepted calls:")
        for i, call in enumerate(summary['logged_calls'], 1):
            print(f"   Call {i}: {call['model']} - ${call['cost']:.4f} ({call['total_tokens']} tokens)")
    else:
        print("❌ No API calls were intercepted!")
    
    # 7. End audit session
    print("\n🏁 Ending audit session...")
    await audit_tracker.end_session()
    
    print("\n✅ Integration test completed!")
    
    return summary['call_count'] > 0

if __name__ == "__main__":
    # Run the integration test
    success = asyncio.run(test_llm_interceptor_integration())
    
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Integration test failed!")
        sys.exit(1)
