#!/usr/bin/env python3
"""
Simple test to see if LiteLLM callbacks work at all
"""

import asyncio
import litellm
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check if we have API key
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("❌ No OpenAI API key found")
    exit(1)

print(f"✅ OpenAI API key found: {api_key[:8]}...")

# Simple callback functions
def simple_success_callback(kwargs, response_obj, start_time, end_time):
    print("🎯 SIMPLE SUCCESS CALLBACK FIRED!")
    print(f"   Model: {kwargs.get('model', 'unknown')}")
    if hasattr(response_obj, 'usage') and response_obj.usage:
        print(f"   Tokens: {response_obj.usage.total_tokens}")
    else:
        print("   No usage data")

def simple_failure_callback(kwargs, response_obj, start_time, end_time):
    print("🔥 SIMPLE FAILURE CALLBACK FIRED!")
    print(f"   Error: {response_obj}")

async def test_callbacks():
    print("🧪 Testing LiteLLM Callbacks")
    print("=" * 50)
    
    # Set callbacks
    litellm.success_callback = [simple_success_callback]
    litellm.failure_callback = [simple_failure_callback]
    
    # Also set async callbacks
    if not hasattr(litellm, '_async_success_callback'):
        litellm._async_success_callback = []
    if not hasattr(litellm, '_async_failure_callback'):
        litellm._async_failure_callback = []
        
    litellm._async_success_callback = [simple_success_callback]
    litellm._async_failure_callback = [simple_failure_callback]
    
    print(f"📋 Success callbacks: {litellm.success_callback}")
    print(f"📋 Failure callbacks: {litellm.failure_callback}")
    print(f"📋 Async success callbacks: {getattr(litellm, '_async_success_callback', 'Not set')}")
    print(f"📋 Async failure callbacks: {getattr(litellm, '_async_failure_callback', 'Not set')}")
    
    try:
        # Test sync call
        print("\n🚀 Testing sync completion...")
        sync_response = litellm.completion(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'Hello'"}],
            max_tokens=5
        )
        
        print("✅ Sync response received")
        
        # Test async call  
        print("\n🚀 Testing async completion...")
        async_response = await litellm.acompletion(
            model="gpt-3.5-turbo", 
            messages=[{"role": "user", "content": "Say 'Hi'"}],
            max_tokens=5
        )
        
        print("✅ Async response received")
        
        # Give callbacks time to fire
        await asyncio.sleep(1)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_callbacks())
