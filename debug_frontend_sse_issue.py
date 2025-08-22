#!/usr/bin/env python3

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_frontend_sse_issue():
    """
    Test the exact SSE connection that's failing in the frontend logs
    """
    
    print("🔍 Frontend SSE Connection Issue Investigation")
    print("=" * 60)
    
    # The exact task ID and token from the frontend logs
    task_id = "cmehni7600001z9fmkdokvw36"
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjbWRhaXY1NTMwMDAwejlueHFteWc0NDV2IiwiZW1haWwiOiJjaGFybGVzLnZvZ3RAZ21haWwuY29tIiwibmFtZSI6IkNoYXJsZXMgVm9ndCIsInJvbGUiOiJBRE1JTiIsImlhdCI6MTc1NTU1Mzk2OCwiZXhwIjoxNzU1NTU3NTY4fQ.-ELNCWzIdgsups5gKZNU05Qa7tEA9TqWoWWaJK23AkI"
    
    # Test 1: Direct HTTP request to the SSE endpoint
    print("1️⃣ Testing direct HTTP request to SSE endpoint...")
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://localhost:5000/stream/{task_id}?token={token}"
            print(f"   URL: {url}")
            
            async with session.get(url, ssl=False, timeout=aiohttp.ClientTimeout(total=10)) as response:
                print(f"   Status: {response.status}")
                print(f"   Headers: {dict(response.headers)}")
                
                if response.status == 200:
                    # Read the first SSE message
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data:'):
                            print(f"   First message: {line_str}")
                            break
                    print("   ✅ HTTP request successful")
                else:
                    text = await response.text()
                    print(f"   ❌ HTTP request failed: {text}")
                    
    except asyncio.TimeoutError:
        print("   ❌ HTTP request timed out")
    except Exception as e:
        print(f"   ❌ HTTP request error: {e}")
    
    # Test 2: Check if the task actually exists
    print(f"\n2️⃣ Checking if task {task_id} exists...")
    try:
        async with aiohttp.ClientSession() as session:
            # Try to get task status
            headers = {'Authorization': f'Bearer {token}'}
            async with session.get(f"https://localhost:5000/tasks/{task_id}", 
                                 headers=headers, ssl=False, timeout=aiohttp.ClientTimeout(total=5)) as response:
                print(f"   Task status endpoint: {response.status}")
                if response.status == 200:
                    task_data = await response.json()
                    print(f"   Task exists: {task_data}")
                elif response.status == 404:
                    print("   ❌ Task not found - this could be the issue!")
                else:
                    text = await response.text()
                    print(f"   Task check failed: {text}")
                    
    except Exception as e:
        print(f"   Task check error: {e}")
    
    # Test 3: Test JWT token validity
    print(f"\n3️⃣ Testing JWT token validity...")
    try:
        import jwt as pyjwt
        secret = "Ver0EvKSf1T5hN4/6NDsnPyZf8S7dJZ/Ewksc2Y2L7w="
        
        # Decode without verification first
        payload = pyjwt.decode(token, options={"verify_signature": False})
        print(f"   Token payload: {payload}")
        
        # Check if expired
        import time
        current_time = int(time.time())
        exp_time = payload.get('exp', 0)
        
        print(f"   Current time: {current_time}")
        print(f"   Token expires: {exp_time}")
        print(f"   Time until expiry: {exp_time - current_time} seconds")
        
        if exp_time < current_time:
            print("   ❌ Token is EXPIRED!")
        else:
            print("   ✅ Token is still valid")
            
        # Try to validate with signature
        try:
            validated = pyjwt.decode(token, secret, algorithms=["HS256"])
            print("   ✅ Token signature valid")
        except pyjwt.ExpiredSignatureError:
            print("   ❌ Token signature validation failed: expired")
        except Exception as e:
            print(f"   ❌ Token signature validation failed: {e}")
            
    except Exception as e:
        print(f"   JWT validation error: {e}")
    
    # Test 4: Test connection to a fresh task
    print(f"\n4️⃣ Testing connection to a fresh task...")
    try:
        async with aiohttp.ClientSession() as session:
            # Create a new task first
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            payload = {
                'topic': 'SSE Connection Test',
                'instructions': 'Test for SSE connection debugging'
            }
            
            async with session.post("https://localhost:5000/generate-blog", 
                                  headers=headers, json=payload, ssl=False) as response:
                if response.status == 200:
                    task_data = await response.json() 
                    new_task_id = task_data.get('task_id')
                    print(f"   Created new task: {new_task_id}")
                    
                    # Now test SSE connection to the new task
                    sse_url = f"https://localhost:5000/stream/{new_task_id}?token={token}"
                    async with session.get(sse_url, ssl=False, timeout=aiohttp.ClientTimeout(total=5)) as sse_response:
                        print(f"   SSE to new task status: {sse_response.status}")
                        if sse_response.status == 200:
                            print("   ✅ SSE connection to new task works!")
                        else:
                            sse_text = await sse_response.text()
                            print(f"   ❌ SSE connection failed: {sse_text}")
                else:
                    text = await response.text()
                    print(f"   ❌ Failed to create new task: {text}")
                    
    except Exception as e:
        print(f"   New task test error: {e}")

if __name__ == "__main__":
    asyncio.run(test_frontend_sse_issue())
