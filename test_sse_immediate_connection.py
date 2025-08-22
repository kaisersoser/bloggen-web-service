#!/usr/bin/env python3
"""
Test SSE Connect    # Try with valid JWT token if we got one, otherwise use fresh token for existing user
    if not token:
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjbWRhaXY1NTMwMDAwejlueHFteWc0NDV2IiwiZW1haWwiOiJjaGFybGVzLnZvZ3RAZ21haWwuY29tIiwibmFtZSI6IkNoYXJsZXMgVm9ndCIsInJvbGUiOiJBRE1JTiIsImlhdCI6MTc1NTU0NTQ0NywiZXhwIjoxNzU1NTQ5MDQ3fQ.2Z_4YkM6pNp6IPVDE-vcBJhrwRJqixvqKRqGLkM8OrA" Immediate Acknowledgment

This test verifies that the SSE endpoint immediately sends a connection acknowledgment
when a client connects, and continues to send updates.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

async def test_sse_immediate_connection():
    """Test that SSE connection gets immediate acknowledgment"""
    print("🧪 Testing SSE Immediate Connection Acknowledgment")
    print("=" * 60)
    
    # First, let's test if we can get a JWT token from frontend
    print("📋 Step 1: Getting JWT token...")
    token = None
    try:
        async with aiohttp.ClientSession() as session:
            # Test the JWT token endpoint
            async with session.get("https://localhost:3001/api/auth/jwt-token", 
                                 ssl=False) as response:
                if response.status == 200:
                    token_data = await response.json()
                    token = token_data.get('token')
                    print(f"✅ Got JWT token: {token[:50]}...")
                else:
                    print(f"❌ Failed to get JWT token: {response.status}")
    except Exception as e:
        print(f"⚠️ JWT token request failed: {e}")
    
    if not token:
        print("🔄 Token not available, will test SSE endpoint authentication behavior")
        
    # Step 2: Create a real blog generation task first
    print(f"\n📝 Step 2: Creating a real blog generation task...")
    test_task_id = None
    
    # Try with valid JWT token if we got one, otherwise use timezone-fixed token for existing user
    if not token:
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjbWRhaXY1NTMwMDAwejlueHFteWc0NDV2IiwiZW1haWwiOiJjaGFybGVzLnZvZ3RAZ21haWwuY29tIiwibmFtZSI6IkNoYXJsZXMgVm9ndCIsInJvbGUiOiJBRE1JTiIsImlhdCI6MTc1NTU1MzQzMiwiZXhwIjoxNzU1NjM5ODMyfQ.OJATsfAwge4JbV2wfDlWTXLkfhgvjxibbXrTrlEkIt0"
        
    # Try to create a real task first
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            payload = {
                'topic': 'Test AI Blog Topic',
                'instructions': 'This is a test blog generation for SSE connection testing'
            }
            
            async with session.post("https://localhost:5000/generate-blog", 
                                  headers=headers, json=payload, ssl=False) as response:
                if response.status == 200:
                    task_data = await response.json()
                    test_task_id = task_data.get('task_id')
                    print(f"✅ Created blog generation task: {test_task_id}")
                else:
                    print(f"❌ Failed to create blog task: {response.status}")
                    response_text = await response.text()
                    print(f"Response: {response_text}")
    except Exception as e:
        print(f"❌ Error creating blog task: {e}")
    
    if not test_task_id:
        test_task_id = "test-sse-connection-123"
        print(f"🔄 Using fallback test task ID: {test_task_id}")
        # Use a timezone-fixed JWT token for existing user
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjbWRhaXY1NTMwMDAwejlueHFteWc0NDV2IiwiZW1haWwiOiJjaGFybGVzLnZvZ3RAZ21haWwuY29tIiwibmFtZSI6IkNoYXJsZXMgVm9ndCIsInJvbGUiOiJBRE1JTiIsImlhdCI6MTc1NTU1MzQzMiwiZXhwIjoxNzU1NjM5ODMyfQ.OJATsfAwge4JbV2wfDlWTXLkfhgvjxibbXrTrlEkIt0"
    
    # Test SSE connection
    print(f"\n📡 Step 3: Testing SSE connection to task {test_task_id}...")
    
    sse_url = f"https://localhost:5000/stream/{test_task_id}?token={token}"
    print(f"🔗 SSE URL: {sse_url}")
    
    connection_acknowledged = False
    messages_received = []
    start_time = time.time()
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(sse_url, ssl=False) as response:
                print(f"📊 Response Status: {response.status}")
                print(f"📋 Response Headers: {dict(response.headers)}")
                
                if response.status != 200:
                    print(f"❌ SSE connection failed with status: {response.status}")
                    response_text = await response.text()
                    print(f"Response body: {response_text}")
                    return False
                
                print("🔌 SSE connection established, waiting for messages...")
                
                async for line in response.content:
                    line_str = line.decode('utf-8').strip()
                    current_time = time.time() - start_time
                    
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]  # Remove 'data: ' prefix
                        try:
                            data = json.loads(data_str)
                            messages_received.append(data)
                            
                            print(f"📨 [{current_time:.2f}s] Message: {data.get('type', 'unknown')} - {data.get('message', '')}")
                            
                            # Check if this is the connection acknowledgment
                            if data.get('type') == 'connected':
                                connection_acknowledged = True
                                ack_time = current_time
                                print(f"✅ Connection acknowledged in {ack_time:.2f} seconds!")
                            
                        except json.JSONDecodeError as e:
                            print(f"⚠️ Failed to parse JSON: {e}")
                            print(f"Raw data: {data_str}")
                    
                    elif line_str:
                        print(f"📝 [{current_time:.2f}s] Raw line: {line_str}")
                    
                    # Break after 5 seconds to avoid infinite loop
                    if current_time > 5:
                        print("⏰ Test timeout reached (5 seconds)")
                        break
                        
    except asyncio.TimeoutError:
        print(f"⏰ SSE connection timed out after 10 seconds")
        return False
    except Exception as e:
        print(f"❌ SSE connection error: {e}")
        return False
    
    # Results
    print(f"\n📊 Test Results:")
    print(f"   Connection Acknowledged: {'✅ Yes' if connection_acknowledged else '❌ No'}")
    print(f"   Messages Received: {len(messages_received)}")
    print(f"   Total Test Time: {time.time() - start_time:.2f} seconds")
    
    if messages_received:
        print(f"\n📋 Messages Details:")
        for i, msg in enumerate(messages_received, 1):
            print(f"   {i}. Type: {msg.get('type', 'unknown')} - {msg.get('message', 'No message')}")
    
    return connection_acknowledged

async def test_backend_health():
    """Test if backend is responding"""
    print("🏥 Testing backend health...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://localhost:5000/health", ssl=False) as response:
                if response.status == 200:
                    health_data = await response.text()
                    print(f"✅ Backend is healthy: {health_data}")
                    return True
                else:
                    print(f"❌ Backend health check failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Backend health check error: {e}")
        return False

async def main():
    print("🚀 SSE Connection Test Suite")
    print("=" * 60)
    
    # Test backend health first
    backend_healthy = await test_backend_health()
    if not backend_healthy:
        print("❌ Backend is not responding - cannot proceed with SSE test")
        return
    
    print("\n")
    
    # Test SSE immediate connection
    sse_working = await test_sse_immediate_connection()
    
    print(f"\n🎯 Final Results:")
    print(f"   Backend Health: {'✅ OK' if backend_healthy else '❌ FAIL'}")
    print(f"   SSE Connection: {'✅ OK' if sse_working else '❌ FAIL'}")
    
    if not sse_working:
        print(f"\n💡 Possible Issues:")
        print(f"   - Backend may not be running on port 5000")
        print(f"   - SSL certificate issues")
        print(f"   - SSE endpoint not responding immediately")
        print(f"   - Task ID not found (expected for test task)")

if __name__ == "__main__":
    asyncio.run(main())
