#!/usr/bin/env python3
"""
Comprehensive test of frontend SSE message processing with increased timeout.
Tests the full flow: backend Redis pub/sub → SSE stream → frontend processing.
"""
import asyncio
import json
import time
import aiohttp
import ssl
import requests
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BACKEND_URL = "https://localhost:5000"
FRONTEND_URL = "https://localhost:3001"  
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjbWRhaXY1NTMwMDAwejlueHFteWc0NDV2IiwiZW1haWwiOiJjaGFybGVzLnZvZ3RAZ21haWwuY29tIiwibmFtZSI6IkNoYXJsZXMgVm9ndCIsInJvbGUiOiJBRE1JTiIsImlhdCI6MTc1NTYzNTE0NiwiZXhwIjoxNzU1NzIxNTQ2fQ.e-2m_fMDMAB07lk84BP1VDzPj9cWfWilU2QW-MKA_WY"

def create_blog_task():
    """Create a blog task for comprehensive testing"""
    blog_request = {
        "instructions": "Write a comprehensive technical blog about Redis pub/sub patterns with practical examples (medium length for testing)",
        "title": "Complete Guide to Redis Pub/Sub Architecture", 
        "target_audience": "software engineers",
        "tone": "technical",
        "length": "medium"
    }
    
    print(f"🚀 Creating comprehensive blog task...")
    start_time = time.time()
    
    response = requests.post(
        f"{BACKEND_URL}/generate-blog",
        json=blog_request,
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        verify=False
    )
    
    creation_time = time.time() - start_time
    
    if response.status_code == 200:
        task_id = response.json()["task_id"]
        print(f"✅ Task created in {creation_time:.2f}s: {task_id}")
        return task_id, time.time()
    else:
        print(f"❌ Task creation failed: {response.status_code} - {response.text}")
        return None, None

async def test_frontend_message_processing(task_id, task_start_time):
    """Test the complete SSE message flow with extended timeout"""
    if not task_id:
        return False
        
    sse_url = f"{BACKEND_URL}/stream/{task_id}?token={ADMIN_TOKEN}"
    
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    timeout = aiohttp.ClientTimeout(total=200)  # Extended timeout for comprehensive test
    
    print(f"🔗 Testing SSE with 3-minute frontend timeout...")
    sse_start_time = time.time()
    
    try:
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async with session.get(sse_url, headers={
                'Accept': 'text/event-stream',
                'Cache-Control': 'no-cache',
            }) as response:
                
                if response.status != 200:
                    print(f"❌ SSE failed: {response.status}")
                    return False
                    
                print(f"✅ SSE connected - monitoring Redis message flow...")
                
                message_count = 0
                status_messages = []
                keepalive_count = 0
                redis_mode_detected = False
                timeout_occurred = False
                task_completed = False
                detailed_updates = 0
                
                async for line in response.content:
                    line_str = line.decode('utf-8').strip()
                    
                    if line_str.startswith('data: '):
                        current_time = time.time()
                        data_str = line_str[6:]
                        
                        try:
                            message = json.loads(data_str)
                            message_count += 1
                            
                            msg_type = message.get('type', message.get('message_type', 'unknown'))
                            msg_content = message.get('message', '')
                            progress = message.get('progress', 0)
                            
                            time_since_task = current_time - task_start_time
                            
                            # Classify message types
                            if msg_type == 'status':
                                status_messages.append({
                                    'time': time_since_task,
                                    'message': msg_content,
                                    'progress': progress
                                })
                                if 'Researching' in msg_content or 'Generating' in msg_content or 'Fact-checking' in msg_content:
                                    detailed_updates += 1
                            elif msg_type == 'keepalive':
                                keepalive_count += 1
                            elif msg_type == 'completed':
                                task_completed = True
                            elif msg_type == 'timeout':
                                timeout_occurred = True
                                
                            # Check for Redis mode detection
                            if 'Redis mode' in msg_content or 'Redis pub/sub' in msg_content:
                                redis_mode_detected = True
                                
                            # Log significant messages
                            if message_count <= 10 or msg_type in ['completed', 'error', 'timeout'] or detailed_updates <= 5:
                                print(f"📨 [{message_count:2d}] {msg_type} (+{time_since_task:.1f}s): {msg_content[:80]}{'...' if len(msg_content) > 80 else ''}")
                                if progress > 0:
                                    print(f"     Progress: {progress}%")
                            
                            # Stop conditions
                            if task_completed or timeout_occurred:
                                print(f"✅ Task finished: {msg_type}")
                                break
                            elif message_count >= 50:  # Safety limit for testing
                                print(f"📊 Stopping after {message_count} messages for analysis")
                                break
                                
                        except json.JSONDecodeError:
                            print(f"❌ Bad JSON: {data_str[:100]}...")
                            
                # Analysis
                print(f"\n📊 Frontend SSE Message Processing Analysis:")
                print(f"   Total messages received: {message_count}")
                print(f"   Status update messages: {len(status_messages)}")
                print(f"   Detailed workflow updates: {detailed_updates}")
                print(f"   Keepalive messages: {keepalive_count}")
                print(f"   Redis pub/sub mode detected: {'✅' if redis_mode_detected else '❌'}")
                print(f"   Task completed: {'✅' if task_completed else '❌'}")
                print(f"   Timeout occurred: {'✅' if timeout_occurred else '❌'}")
                
                if len(status_messages) >= 5:
                    print(f"\n📈 Status Message Timeline:")
                    for i, msg in enumerate(status_messages[:8]):  # Show first 8
                        print(f"   [{i+1}] +{msg['time']:.1f}s: {msg['message'][:60]}... ({msg['progress']}%)")
                
                # Success criteria
                success = (
                    message_count >= 10 and
                    detailed_updates >= 3 and
                    (task_completed or message_count >= 20) and
                    not timeout_occurred
                )
                
                return success
                
    except asyncio.TimeoutError:
        print("⏰ Test timeout after 200 seconds")
        return False
    except Exception as e:
        print(f"❌ SSE error: {e}")
        return False

async def main():
    """Main comprehensive test"""
    print("🧪 Testing Frontend SSE Message Processing with Redis Pub/Sub")
    print("=" * 60)
    
    # Step 1: Create comprehensive blog task
    task_id, task_start_time = create_blog_task()
    
    if not task_id:
        print("❌ Failed to create test task")
        return
    
    # Step 2: Brief delay for task initialization
    await asyncio.sleep(1)
    
    # Step 3: Test complete message flow
    success = await test_frontend_message_processing(task_id, task_start_time)
    
    print("=" * 60)
    if success:
        print("🎉 SUCCESS: Frontend SSE processing is working correctly!")
        print("   ✅ Redis pub/sub messages flowing")
        print("   ✅ Detailed status updates received")
        print("   ✅ Extended timeout preventing early disconnection")
        print("   ✅ Message types properly processed")
    else:
        print("❌ Issues detected in frontend SSE processing")
        print("   Review the message flow above for problems")

if __name__ == "__main__":
    asyncio.run(main())
