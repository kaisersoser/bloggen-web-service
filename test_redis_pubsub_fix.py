#!/usr/bin/env python3
"""
Test SSE flow with real blog generation to verify Redis pub/sub fix.
"""
import asyncio
import json
import time
import aiohttp
import requests
import ssl
import urllib3
from datetime import datetime

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BACKEND_URL = "https://localhost:5000"

# Real user JWT token (ADMIN role)
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjbWRhaXY1NTMwMDAwejlueHFteWc0NDV2IiwiZW1haWwiOiJjaGFybGVzLnZvZ3RAZ21haWwuY29tIiwibmFtZSI6IkNoYXJsZXMgVm9ndCIsInJvbGUiOiJBRE1JTiIsImlhdCI6MTc1NTYzNTE0NiwiZXhwIjoxNzU1NzIxNTQ2fQ.e-2m_fMDMAB07lk84BP1VDzPj9cWfWilU2QW-MKA_WY"

def create_blog_generation_task():
    """Create a real blog generation task"""
    try:
        blog_request = {
            "instructions": "Write a short technical blog about Redis pub/sub patterns. Keep it concise for testing purposes.",
            "title": "Redis Pub/Sub Testing",
            "target_audience": "developers",
            "tone": "technical",
            "length": "short"
        }
        
        print(f"🚀 Creating blog generation task...")
        response = requests.post(
            f"{BACKEND_URL}/generate-blog",
            json=blog_request,
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
            verify=False
        )
        
        if response.status_code != 200:
            print(f"❌ Blog creation failed: {response.status_code} - {response.text}")
            return None
            
        task_data = response.json()
        task_id = task_data["task_id"]
        print(f"✅ Created blog task: {task_id}")
        
        return task_id
        
    except Exception as e:
        print(f"❌ Error creating blog task: {e}")
        return None

async def monitor_sse_stream(task_id):
    """Monitor SSE stream to check if Redis pub/sub is working"""
    if not task_id:
        print("❌ No task ID provided")
        return False
        
    print(f"\n📡 Monitoring SSE stream for task: {task_id}")
    
    sse_url = f"{BACKEND_URL}/stream/{task_id}?token={ADMIN_TOKEN}"
    
    try:
        timeout = aiohttp.ClientTimeout(total=120)  # 2 minute timeout
        
        # SSL context for self-signed certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            print(f"🔗 Connecting to SSE stream...")
            
            async with session.get(sse_url, headers={
                'Accept': 'text/event-stream',
                'Cache-Control': 'no-cache',
            }) as response:
                
                if response.status != 200:
                    print(f"❌ SSE connection failed: {response.status}")
                    text = await response.text()
                    print(f"Error response: {text}")
                    return False
                    
                print(f"✅ SSE connection established")
                print("📨 Monitoring for Redis pub/sub vs polling mode...")
                
                message_count = 0
                redis_mode_detected = False
                polling_mode_detected = False
                redis_subscription_log = False
                status_updates = []
                
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
                                
                                print(f"📨 [{message_count:2d}] {msg_type}: {msg_content}")
                                
                                # Detect Redis vs polling mode
                                if 'Redis mode' in msg_content:
                                    redis_mode_detected = True
                                    print("    🎯 REDIS PUB/SUB MODE DETECTED!")
                                elif 'polling mode' in msg_content:
                                    polling_mode_detected = True
                                    print("    📊 Polling mode detected")
                                
                                # Track status updates
                                if msg_type == 'status':
                                    status_updates.append({
                                        'message': msg_content,
                                        'time': datetime.now().isoformat()
                                    })
                                
                                # Check for completion
                                if msg_type in ['completed', 'failed', 'error']:
                                    print(f"✅ Task finished with type: {msg_type}")
                                    break
                                    
                                # Check for timeout
                                if msg_type == 'timeout':
                                    print("⏰ SSE stream timeout occurred")
                                    break
                                    
                                # Limit output for testing
                                if message_count > 20:
                                    print("📊 Stopping after 20 messages for testing...")
                                    break
                                    
                            except json.JSONDecodeError as e:
                                print(f"❌ Failed to parse SSE message: {data_str}")
                                
                    except Exception as e:
                        print(f"❌ Error processing SSE line: {e}")
                        
                print(f"\n📊 SSE Test Results:")
                print(f"   Messages received: {message_count}")
                print(f"   Redis pub/sub mode: {'✅ YES' if redis_mode_detected else '❌ NO'}")
                print(f"   Polling mode: {'✅ YES' if polling_mode_detected else '❌ NO'}")
                print(f"   Status updates: {len(status_updates)}")
                
                if redis_mode_detected and not polling_mode_detected:
                    print("🎉 SUCCESS: Redis pub/sub is working correctly!")
                    return True
                elif polling_mode_detected and not redis_mode_detected:
                    print("⚠️  Redis pub/sub not working - falling back to polling mode")
                    return False
                else:
                    print("🤔 Mixed results - check logs for details")
                    return False
                
    except asyncio.TimeoutError:
        print("⏰ SSE connection timed out")
        return False
    except Exception as e:
        print(f"❌ SSE connection error: {e}")
        return False

async def main():
    """Test Redis pub/sub in SSE stream during real blog generation"""
    print("🚀 Testing Redis pub/sub fix in SSE stream...")
    
    # Step 1: Create a real blog generation task
    task_id = create_blog_generation_task()
    
    if not task_id:
        print("❌ Failed to create blog generation task")
        return
        
    # Step 2: Give task a moment to start
    print("⏳ Waiting 2 seconds for task to initialize...")
    await asyncio.sleep(2)
    
    # Step 3: Monitor SSE stream for Redis pub/sub
    success = await monitor_sse_stream(task_id)
    
    if success:
        print("\n✅ Redis pub/sub fix is working!")
    else:
        print("\n❌ Redis pub/sub fix needs more work")

if __name__ == "__main__":
    asyncio.run(main())
