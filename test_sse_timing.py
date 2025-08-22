#!/usr/bin/env python3
"""
Test to analyze the timing delay in SSE message flow.
Measures when the first real status updates start arriving.
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
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjbWRhaXY1NTMwMDAwejlueHFteWc0NDV2IiwiZW1haWwiOiJjaGFybGVzLnZvZ3RAZ21haWwuY29tIiwibmFtZSI6IkNoYXJsZXMgVm9ndCIsInJvbGUiOiJBRE1JTiIsImlhdCI6MTc1NTYzNTE0NiwiZXhwIjoxNzU1NzIxNTQ2fQ.e-2m_fMDMAB07lk84BP1VDzPj9cWfWilU2QW-MKA_WY"

def create_blog_task():
    """Create a blog task and record creation time"""
    blog_request = {
        "instructions": "Write a short technical blog about async programming patterns (keep it brief for testing)",
        "title": "Async Programming Test",
        "target_audience": "developers",
        "tone": "technical", 
        "length": "short"
    }
    
    print(f"🚀 Creating blog task at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}...")
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
        print(f"❌ Task creation failed: {response.status_code}")
        return None, None

async def analyze_sse_timing(task_id, task_start_time):
    """Analyze the timing of SSE messages to identify delays"""
    if not task_id:
        return
        
    sse_url = f"{BACKEND_URL}/stream/{task_id}?token={ADMIN_TOKEN}"
    
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    timeout = aiohttp.ClientTimeout(total=60)  # 1 minute
    
    print(f"🔗 Connecting to SSE at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}...")
    sse_start_time = time.time()
    
    try:
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async with session.get(sse_url, headers={
                'Accept': 'text/event-stream',
                'Cache-Control': 'no-cache',
            }) as response:
                
                if response.status != 200:
                    print(f"❌ SSE failed: {response.status}")
                    return
                    
                connection_time = time.time() - sse_start_time
                print(f"✅ SSE connected in {connection_time:.2f}s")
                
                message_count = 0
                first_meaningful_message_time = None
                redis_mode_detected = False
                
                async for line in response.content:
                    line_str = line.decode('utf-8').strip()
                    
                    if line_str.startswith('data: '):
                        current_time = time.time()
                        data_str = line_str[6:]
                        
                        try:
                            message = json.loads(data_str)
                            message_count += 1
                            
                            msg_type = message.get('type', 'unknown')
                            msg_content = message.get('message', '')
                            
                            # Calculate timing from task creation
                            time_since_task = current_time - task_start_time
                            time_since_sse = current_time - sse_start_time
                            
                            print(f"📨 [{message_count:2d}] {msg_type} (+{time_since_task:.1f}s from task, +{time_since_sse:.1f}s from SSE):")
                            print(f"     {msg_content[:80]}...")
                            
                            # Check for Redis mode detection
                            if 'Redis mode' in msg_content or 'Redis pub/sub' in msg_content:
                                redis_mode_detected = True
                                print(f"     🎯 REDIS MODE DETECTED at +{time_since_task:.1f}s")
                            
                            # Identify first meaningful message (not just connection/init)
                            if (msg_type not in ['connected', 'initializing'] and 
                                'Initializing' not in msg_content and 
                                first_meaningful_message_time is None):
                                first_meaningful_message_time = current_time
                                delay = time_since_task
                                print(f"     ⭐ FIRST MEANINGFUL MESSAGE at +{delay:.1f}s from task creation")
                            
                            # Stop after 15 messages or when we get meaningful content
                            if message_count >= 15 or (first_meaningful_message_time and message_count >= 8):
                                break
                                
                        except json.JSONDecodeError:
                            print(f"❌ Bad JSON: {data_str[:50]}...")
                            
                print(f"\n📊 Timing Analysis:")
                print(f"   Task creation → SSE connection: {connection_time:.2f}s")
                if first_meaningful_message_time:
                    total_delay = first_meaningful_message_time - task_start_time
                    print(f"   Task creation → First meaningful message: {total_delay:.2f}s")
                else:
                    print(f"   ❌ No meaningful messages received in {message_count} messages")
                print(f"   Redis pub/sub mode: {'✅' if redis_mode_detected else '❌'}")
                
    except Exception as e:
        print(f"❌ SSE error: {e}")

async def main():
    """Main timing analysis"""
    print("⏱️  Analyzing SSE message timing and delays...")
    
    # Step 1: Create task and record timing
    task_id, task_start_time = create_blog_task()
    
    if not task_id:
        return
    
    # Step 2: Small delay then connect to SSE
    await asyncio.sleep(0.5)  # Brief delay to let task initialize
    
    # Step 3: Analyze SSE timing
    await analyze_sse_timing(task_id, task_start_time)

if __name__ == "__main__":
    asyncio.run(main())
