#!/usr/bin/env python3
"""
Test LLM Interceptor Integration

This script tests the fu        # 3. Make actual LLM API calls to test the interceptor
        print("\n🚀 Making LLM API calls...")
        
        # Try sync call first  
        print("   Testing sync completion...")
        sync_response = litellm.completion(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say hello in exactly 5 words."}],
            temperature=0.1,
            max_tokens=20
        )
        print(f"✅ Sync call completed: {sync_response.choices[0].message.content}")
        
        # Give a moment for callback to process
        await asyncio.sleep(0.5)
        
        # Check if sync call was intercepted
        summary = audit_tracker.get_session_summary()
        print(f"   After sync call - Call Count: {summary['call_count']}")
        
        # Then try async call
        print("   Testing async completion...")
        async_response = await litellm.acompletion(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say hello in exactly 5 words."}],
            temperature=0.1,
            max_tokens=20
        )
        
        print(f"✅ Async call completed: {async_response.choices[0].message.content}")
        
        # Give the interceptor a moment to process
        await asyncio.sleep(0.5)
        
        # Check if async call was intercepted
        summary = audit_tracker.get_session_summary()
        print(f"   After async call - Call Count: {summary['call_count']}")on between the LLM interceptor,
context variables, and the database audit tracker.
"""

import asyncio
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker
from core.llm_interceptor import setup_llm_interceptor
from core.context_vars import set_audit_context, current_phase

async def test_llm_interceptor_integration():
    """Test the full integration of LLM interceptor with audit tracking."""
    
    print("🧪 Testing LLM Interceptor Integration")
    print("=" * 50)
    
    # 1. Set up the LLM interceptor
    print("📡 Setting up LLM interceptor...")
    
    # Add a simple test callback first
    def test_success_callback(kwargs, response_obj, start_time, end_time):
        print("🎯 TEST CALLBACK FIRED!")
        print(f"   Model: {kwargs.get('model', 'unknown')}")
        if hasattr(response_obj, 'usage'):
            print(f"   Tokens: {response_obj.usage.total_tokens}")
    
    # Register both our test callback and the real one
    callback_handler = setup_llm_interceptor()
    
    if callback_handler:
        # Add the test callback to the list
        import litellm
        litellm.success_callback.append(test_success_callback)
        print(f"   Total callbacks: {len(litellm.success_callback)}")
    
    if not callback_handler:
        print("❌ LLM interceptor setup failed!")
        return
    
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
    
    # 5. Simulate an OpenAI API call
    print("💬 Simulating OpenAI API call...")
    
    try:
        import litellm
        
        # Set OpenAI API key from environment
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            print("❌ OPENAI_API_KEY not found in environment!")
            return

        # 3. Make actual LLM API calls to test the interceptor
        print("\n🚀 Making LLM API calls...")
        
        # Try sync call first  
        print("   Testing sync completion...")
        sync_response = litellm.completion(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say hello in exactly 5 words."}],
            temperature=0.1,
            max_tokens=20
        )
        print(f"✅ Sync call completed: {sync_response.choices[0].message.content}")
        
        # Give a moment for callback to process
        await asyncio.sleep(0.5)
        
        # Check if sync call was intercepted
        summary = audit_tracker.get_session_summary()
        print(f"   After sync call - Call Count: {summary['call_count']}")
        
        # Then try async call
        print("   Testing async completion...")
        async_response = await litellm.acompletion(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say hello in exactly 5 words."}],
            temperature=0.1,
            max_tokens=20
        )
        
        print(f"✅ Async call completed: {async_response.choices[0].message.content}")
        
        # Give the interceptor a moment to process
        await asyncio.sleep(0.5)
        
        # Check if async call was intercepted
        summary = audit_tracker.get_session_summary()
        print(f"   After async call - Call Count: {summary['call_count']}")
        
    except Exception as e:
        print(f"❌ OpenAI API call failed: {e}")
    
    # 6. Check audit tracker state
    print("\n📊 Checking audit tracker state...")
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
