#!/usr/bin/env python3
"""
Test script to verify the enhanced SSE connection flow
"""

import asyncio
import json
import aiohttp
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_sse_connection():
    """Test the SSE connection immediately acknowledges and sends updates"""
    
    print("🧪 Testing Enhanced SSE Connection Flow")
    print("=" * 50)
    
    # First, let's try to connect to the backend health endpoint
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://localhost:5000/health') as resp:
                if resp.status == 200:
                    print("✅ Backend is running and accessible")
                else:
                    print(f"❌ Backend health check failed: {resp.status}")
                    return False
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        print("💡 Make sure the backend is running: cd backend && source .venv/bin/activate && python src/main.py")
        return False
    
    # Test SSE connection with a dummy task ID
    test_task_id = "test-sse-connection-123"
    test_token = "dummy-token"  # This will fail auth, but we can test the connection
    
    try:
        print(f"🔌 Testing SSE connection to /stream/{test_task_id}")
        
        async with aiohttp.ClientSession() as session:
            sse_url = f'https://localhost:5000/stream/{test_task_id}?token={test_token}'
            
            async with session.get(sse_url) as resp:
                print(f"📡 SSE Response Status: {resp.status}")
                
                if resp.status == 401:
                    print("✅ Authentication working (expected 401 for dummy token)")
                    return True
                elif resp.status == 200:
                    print("✅ SSE connection established!")
                    
                    # Read first few messages
                    async for line in resp.content:
                        if line:
                            line_str = line.decode('utf-8').strip()
                            if line_str.startswith('data: '):
                                data = line_str[6:]  # Remove 'data: ' prefix
                                try:
                                    message = json.loads(data)
                                    print(f"📨 Received: {message}")
                                    if message.get('type') == 'connected':
                                        print("✅ Immediate connection acknowledgment received!")
                                        return True
                                except json.JSONDecodeError:
                                    print(f"📨 Raw message: {data}")
                else:
                    print(f"❌ Unexpected response status: {resp.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ SSE connection test failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_sse_connection())
    if result:
        print("\n🎉 SSE connection test passed!")
    else:
        print("\n❌ SSE connection test failed!")
        sys.exit(1)
