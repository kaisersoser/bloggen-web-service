#!/usr/bin/env python3
"""
Quick test to see the first 10 SSE messages with detailed logging.
"""
import asyncio
import json
import aiohttp
import ssl
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BACKEND_URL = "https://localhost:5000"
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjbWRhaXY1NTMwMDAwejlueHFteWc0NDV2IiwiZW1haWwiOiJjaGFybGVzLnZvZ3RAZ21haWwuY29tIiwibmFtZSI6IkNoYXJsZXMgVm9ndCIsInJvbGUiOiJBRE1JTiIsImlhdCI6MTc1NTYzNTE0NiwiZXhwIjoxNzU1NzIxNTQ2fQ.e-2m_fMDMAB07lk84BP1VDzPj9cWfWilU2QW-MKA_WY"

def create_blog_task():
    """Create a quick blog task"""
    blog_request = {
        "instructions": "Write a very short blog about testing Redis (one paragraph only)",
        "title": "Redis Testing",
        "target_audience": "developers", 
        "tone": "technical",
        "length": "short"
    }
    
    response = requests.post(
        f"{BACKEND_URL}/generate-blog",
        json=blog_request,
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        verify=False
    )
    
    if response.status_code == 200:
        return response.json()["task_id"]
    return None

async def monitor_first_messages(task_id):
    """Monitor just the first 10 SSE messages"""
    if not task_id:
        return
        
    sse_url = f"{BACKEND_URL}/stream/{task_id}?token={ADMIN_TOKEN}"
    
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    timeout = aiohttp.ClientTimeout(total=30)  # Short timeout
    
    try:
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async with session.get(sse_url, headers={
                'Accept': 'text/event-stream',
                'Cache-Control': 'no-cache',
            }) as response:
                
                if response.status != 200:
                    print(f"❌ SSE failed: {response.status}")
                    return
                    
                print(f"✅ SSE connected, showing first 10 messages:")
                message_count = 0
                
                async for line in response.content:
                    line_str = line.decode('utf-8').strip()
                    
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]
                        
                        try:
                            message = json.loads(data_str)
                            message_count += 1
                            
                            msg_type = message.get('type', 'unknown')
                            msg_content = message.get('message', '')
                            progress = message.get('progress', 0)
                            
                            print(f"📨 [{message_count:2d}] {msg_type}: {msg_content[:100]}...")
                            if progress > 0:
                                print(f"     Progress: {progress}%")
                            
                            if message_count >= 10:
                                print("✅ Captured first 10 messages, stopping test")
                                break
                                
                        except json.JSONDecodeError:
                            print(f"❌ Bad JSON: {data_str[:100]}...")
                            
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    print("🚀 Quick SSE message test...")
    
    task_id = create_blog_task()
    if not task_id:
        print("❌ Failed to create task")
        return
        
    print(f"✅ Created task: {task_id}")
    await asyncio.sleep(1)  # Brief pause
    
    await monitor_first_messages(task_id)

if __name__ == "__main__":
    asyncio.run(main())
