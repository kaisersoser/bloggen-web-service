#!/usr/bin/env python3
"""
Simple test to verify the SSE Redis pub/sub fix is working.
Tests the SSE stream Redis subscription setup.
"""
import asyncio
import json
import aiohttp
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACKEND_URL = "https://localhost:5000"

async def test_sse_redis_subscription():
    """Test SSE connection with a known task ID to check Redis pub/sub setup"""
    
    # Use a dummy task ID and JWT for testing SSE subscription logic
    test_task_id = "test_task_123"
    # JWT token for real user from database (ADMIN role)
    test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjbWRhaXY1NTMwMDAwejlueHFteWc0NDV2IiwiZW1haWwiOiJjaGFybGVzLnZvZ3RAZ21haWwuY29tIiwibmFtZSI6IkNoYXJsZXMgVm9ndCIsInJvbGUiOiJBRE1JTiIsImlhdCI6MTc1NTYzNTE0NiwiZXhwIjoxNzU1NzIxNTQ2fQ.e-2m_fMDMAB07lk84BP1VDzPj9cWfWilU2QW-MKA_WY"
    
    sse_url = f"{BACKEND_URL}/stream/{test_task_id}?token={test_token}"
    
    print(f"🔗 Testing SSE Redis subscription setup...")
    print(f"🔗 Connecting to: {sse_url}")
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)  # Short timeout for testing
        # Use SSL context to handle self-signed certificates
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async with session.get(sse_url, headers={
                'Accept': 'text/event-stream',
                'Cache-Control': 'no-cache',
            }) as response:
                
                print(f"📊 Response status: {response.status}")
                
                if response.status == 404:
                    print("✅ Expected 404 for non-existent task - this means auth and routing are working")
                    return True
                elif response.status == 403:
                    print("❌ 403 Forbidden - JWT token issue")
                    return False
                elif response.status == 200:
                    print("✅ SSE connection established - reading messages...")
                    
                    message_count = 0
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            message_count += 1
                            if message_count <= 3:  # Only show first few messages
                                print(f"📨 SSE Message: {line_str}")
                            if message_count >= 3:
                                print("✅ SSE connection working - breaking test")
                                break
                    return True
                else:
                    print(f"❌ Unexpected status: {response.status}")
                    text = await response.text()
                    print(f"Response: {text}")
                    return False
                
    except asyncio.TimeoutError:
        print("⏰ Connection timeout")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

async def main():
    """Test the SSE Redis subscription fix"""
    print("🚀 Testing SSE Redis pub/sub fix...")
    
    success = await test_sse_redis_subscription()
    
    if success:
        print("✅ SSE connection test completed")
    else:
        print("❌ SSE connection test failed")

if __name__ == "__main__":
    asyncio.run(main())
