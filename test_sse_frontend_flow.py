#!/usr/bin/env python3
"""
Test to verify the complete SSE flow from backend to frontend is working.
Tests the actual Redis pub/sub subscription in the SSE stream.
"""
import asyncio
import json
import time
import aiohttp
import requests
from datetime import datetime

BACKEND_URL = "https://localhost:5000"
FRONTEND_URL = "https://localhost:3001"

def test_jwt_and_blog_creation():
    """Create a blog and get a valid JWT token"""
    try:
        # Get a valid JWT token first (disable SSL verification for self-signed certs)
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        response = requests.post(f"{BACKEND_URL}/auth/login", json={
            "username": "user1@example.com",
            "password": "password123"
        }, verify=False)
        
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return None, None
            
        token = response.json()["access_token"]
        print(f"✅ Got JWT token: {token[:50]}...")
        
        # Create a blog generation task
        blog_request = {
            "instructions": "Write a detailed technical blog about Python async/await patterns",
            "title": "Mastering Python Async Programming",
            "target_audience": "Python developers",
            "tone": "technical",
            "length": "medium"
        }
        
        response = requests.post(
            f"{BACKEND_URL}/generate-blog",
            json=blog_request,
            headers={"Authorization": f"Bearer {token}"},
            verify=False
        )
        
        if response.status_code != 200:
            print(f"❌ Blog creation failed: {response.status_code} - {response.text}")
            return token, None
            
        task_data = response.json()
        task_id = task_data["task_id"]
        print(f"✅ Created blog task: {task_id}")
        
        return token, task_id
        
    except Exception as e:
        print(f"❌ Error in JWT/blog creation: {e}")
        return None, None

async def test_sse_connection(token, task_id):
    """Test the SSE connection and monitor Redis pub/sub messages"""
    if not token or not task_id:
        print("❌ Missing token or task_id, skipping SSE test")
        return
        
    print(f"\n📡 Testing SSE connection for task: {task_id}")
    
    sse_url = f"{BACKEND_URL}/stream/{task_id}?token={token}"
    
    try:
        timeout = aiohttp.ClientTimeout(total=60)  # 60 second timeout
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            print(f"🔗 Connecting to: {sse_url}")
            
            async with session.get(sse_url, headers={
                'Accept': 'text/event-stream',
                'Cache-Control': 'no-cache',
            }) as response:
                
                if response.status != 200:
                    print(f"❌ SSE connection failed: {response.status}")
                    text = await response.text()
                    print(f"Error response: {text}")
                    return
                    
                print(f"✅ SSE connection established (status: {response.status})")
                print("📨 Listening for SSE messages...")
                
                message_count = 0
                redis_mode_detected = False
                polling_mode_detected = False
                
                async for line in response.content:
                    try:
                        line_str = line.decode('utf-8').strip()
                        
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]  # Remove 'data: ' prefix
                            
                            try:
                                message = json.loads(data_str)
                                message_count += 1
                                
                                msg_type = message.get('type', 'unknown')
                                msg_content = message.get('message', '')
                                timestamp = message.get('timestamp', '')
                                
                                print(f"📨 [{message_count:2d}] {msg_type}: {msg_content}")
                                
                                # Detect which mode we're in
                                if 'Redis mode' in msg_content:
                                    redis_mode_detected = True
                                    print("    🎯 Redis pub/sub mode detected!")
                                elif 'polling mode' in msg_content:
                                    polling_mode_detected = True
                                    print("    📊 Database polling mode detected")
                                
                                # Check for completion or error
                                if msg_type in ['completed', 'failed', 'error']:
                                    print(f"✅ Task finished with type: {msg_type}")
                                    break
                                    
                                # Check for timeout
                                if msg_type == 'timeout':
                                    print("⏰ SSE stream timeout occurred")
                                    break
                                    
                            except json.JSONDecodeError as e:
                                print(f"❌ Failed to parse SSE message: {data_str}")
                                
                    except Exception as e:
                        print(f"❌ Error processing SSE line: {e}")
                        
                print(f"\n📊 SSE Test Results:")
                print(f"   Messages received: {message_count}")
                print(f"   Redis mode: {'✅' if redis_mode_detected else '❌'}")
                print(f"   Polling mode: {'✅' if polling_mode_detected else '❌'}")
                
                if redis_mode_detected:
                    print("🎉 SUCCESS: Redis pub/sub is working in SSE stream!")
                else:
                    print("⚠️  WARNING: Only polling mode detected, Redis pub/sub may not be working")
                
    except asyncio.TimeoutError:
        print("⏰ SSE connection timed out")
    except Exception as e:
        print(f"❌ SSE connection error: {e}")

async def main():
    """Main test execution"""
    print("🚀 Testing complete SSE frontend flow...")
    
    # Step 1: Get JWT and create blog task
    token, task_id = test_jwt_and_blog_creation()
    
    if not token or not task_id:
        print("❌ Failed to set up test prerequisites")
        return
        
    # Small delay to let task start
    print("⏳ Waiting 2 seconds for task to initialize...")
    await asyncio.sleep(2)
    
    # Step 2: Test SSE connection
    await test_sse_connection(token, task_id)
    
    print("\n✅ Test completed")

if __name__ == "__main__":
    asyncio.run(main())
