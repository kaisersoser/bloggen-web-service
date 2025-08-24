#!/usr/bin/env python3
"""
Test SSE connection to debug completion notification issue
"""
import asyncio
import aiohttp
import json
import sys

async def test_sse_connection():
    """Test SSE connection to check if completion messages are being sent"""
    
    # Task ID from the logs - the one that completed but frontend didn't receive
    task_id = "cmenfx7xm0001z931eywqcxk0"
    
    # Get JWT token first
    async with aiohttp.ClientSession() as session:
        try:
            # Get JWT token
            print("🔑 Getting JWT token...")
            async with session.get('https://localhost:3001/api/auth/jwt-token', 
                                   ssl=False) as resp:
                if resp.status != 200:
                    print(f"❌ Failed to get JWT token: {resp.status}")
                    text = await resp.text()
                    print(f"Response: {text}")
                    return
                
                token_data = await resp.json()
                jwt_token = token_data.get('token')
                if not jwt_token:
                    print("❌ No JWT token in response")
                    return
                    
                print(f"✅ Got JWT token: {jwt_token[:50]}...")
            
            # Test SSE connection
            sse_url = f"https://localhost:5000/stream/{task_id}?token={jwt_token}"
            print(f"🔗 Connecting to SSE: {sse_url}")
            
            timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout for test
            
            async with session.get(sse_url, 
                                   ssl=False,
                                   timeout=timeout,
                                   headers={'Accept': 'text/event-stream',
                                           'Cache-Control': 'no-cache'}) as resp:
                
                if resp.status != 200:
                    print(f"❌ SSE connection failed: {resp.status}")
                    text = await resp.text()
                    print(f"Response: {text}")
                    return
                
                print(f"✅ SSE connection established (status: {resp.status})")
                print("📨 Waiting for messages (30 second timeout)...")
                
                message_count = 0
                async for line in resp.content:
                    line = line.decode('utf-8').strip()
                    if line:
                        message_count += 1
                        print(f"📨 Message #{message_count}: {line}")
                        
                        # Parse SSE format
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])  # Remove 'data: ' prefix
                                print(f"   📋 Parsed data: {json.dumps(data, indent=2)}")
                                
                                # Check if this is a completion message
                                if data.get('message_type') == 'completed' or data.get('type') == 'completed':
                                    print("🎉 FOUND COMPLETION MESSAGE!")
                                    print(f"   📝 Content length: {len(data.get('final_content', ''))}")
                                    print(f"   📊 Word count: {data.get('word_count')}")
                                    return
                                    
                            except json.JSONDecodeError as e:
                                print(f"   ❌ JSON decode error: {e}")
                        
                        # Stop after 50 messages to avoid spam
                        if message_count > 50:
                            print("⏹️ Stopping after 50 messages")
                            break
                
                print("⏰ Timeout reached or connection closed")
                
        except asyncio.TimeoutError:
            print("⏰ Connection timeout")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_sse_connection())
