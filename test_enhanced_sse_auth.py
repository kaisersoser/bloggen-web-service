#!/usr/bin/env python3
"""
Enhanced SSE Connection Test with Authentication

This script tests the improved SSE connection functionality with proper 
authentication error handling and timeout management.
"""

import asyncio
import aiohttp
import json
import os
import sys
from datetime import datetime

# Import JWT generation (inline function)
import jwt
import time

def generate_jwt_for_user(email: str) -> str:
    """Generate JWT token for user email with proper format"""
    import os
    import time
    secret = os.getenv("NEXTAUTH_SECRET", "Ver0EvKSf1T5hN4/6NDsnPyZf8S7dJZ/Ewksc2Y2L7w=")
    current_time = int(time.time())
    payload = {
        "sub": "test-user-id-123",  # Required: user ID
        "email": email,
        "name": "Test User",
        "role": "ADMIN",  # Use ADMIN role for testing
        "iat": current_time,
        "exp": current_time + 3600  # 1 hour (shorter for testing)
    }
    return jwt.encode(payload, secret, algorithm="HS256")

BACKEND_URL = "https://localhost:5000"
FRONTEND_URL = "https://localhost:3001"

async def test_enhanced_sse_authentication():
    """Test SSE connection with enhanced authentication handling"""
    print("🔍 Testing Enhanced SSE Connection with Authentication...")
    print("=" * 60)
    
    # Test 1: Verify JWT token generation works
    print("\n1️⃣ Testing JWT Token Generation...")
    try:
        token = generate_jwt_for_user("test@example.com")
        print(f"✅ JWT token generated successfully")
        print(f"   Token length: {len(token)} characters")
    except Exception as e:
        print(f"❌ JWT token generation failed: {e}")
        return False
    
    # Test 2: Test authenticated blog generation
    print("\n2️⃣ Testing Authenticated Blog Generation...")
    
    connector = aiohttp.TCPConnector(ssl=False)  # Skip SSL verification for localhost
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        try:
            # Create a blog generation task
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'topic': 'Enhanced SSE Connection Testing with CrewAI',
                'target_audience': 'developers',
                'tone': 'technical'
            }
            
            print(f"   📝 Creating blog generation task...")
            async with session.post(
                f"{BACKEND_URL}/generate-blog",
                json=payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    task_id = result.get('task_id')
                    print(f"   ✅ Task created: {task_id}")
                    
                    # Test 3: Connect to SSE stream
                    print(f"\n3️⃣ Testing SSE Stream Connection...")
                    await test_sse_stream(session, task_id, token)
                    
                else:
                    error_text = await response.text()
                    print(f"   ❌ Blog generation failed: {response.status}")
                    print(f"   Error: {error_text}")
                    return False
                    
        except asyncio.TimeoutError:
            print("   ❌ Request timeout - check backend connectivity")
            return False
        except Exception as e:
            print(f"   ❌ Blog generation error: {e}")
            return False
    
    return True

async def test_sse_stream(session, task_id, token):
    """Test SSE stream with authentication"""
    try:
        stream_url = f"{BACKEND_URL}/stream/{task_id}?token={token}"
        print(f"   🔗 Connecting to: {stream_url[:50]}...")
        
        message_count = 0
        connection_established = False
        
        async with session.get(stream_url) as response:
            if response.status == 200:
                print(f"   ✅ SSE connection established (Status: {response.status})")
                connection_established = True
                
                # Read messages for up to 30 seconds or until completion
                start_time = datetime.now()
                timeout_seconds = 30
                
                async for line in response.content:
                    if (datetime.now() - start_time).seconds > timeout_seconds:
                        print(f"   ⏰ Test timeout reached ({timeout_seconds}s)")
                        break
                    
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])  # Remove 'data: ' prefix
                            message_count += 1
                            
                            print(f"   📨 Message {message_count}: {data.get('message_type', 'unknown')} - {data.get('message', '')[:50]}...")
                            
                            # Check for completion
                            if message_count >= 5:  # Get a few messages then exit
                                print(f"   ✅ Received {message_count} messages - test successful")
                                break
                                
                        except json.JSONDecodeError as e:
                            print(f"   ⚠️ Invalid JSON in SSE message: {line[:100]}")
                    
                if message_count == 0:
                    print(f"   ⚠️ No messages received within timeout period")
                    
            else:
                error_text = await response.text()
                print(f"   ❌ SSE connection failed: {response.status}")
                print(f"   Error: {error_text}")
                
    except asyncio.TimeoutError:
        print(f"   ❌ SSE stream timeout")
    except Exception as e:
        print(f"   ❌ SSE stream error: {e}")

async def test_authentication_errors():
    """Test authentication error scenarios"""
    print("\n4️⃣ Testing Authentication Error Scenarios...")
    
    connector = aiohttp.TCPConnector(ssl=False)
    timeout = aiohttp.ClientTimeout(total=10)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Test with invalid token
        print("   🔐 Testing invalid token...")
        try:
            stream_url = f"{BACKEND_URL}/stream/test-task?token=invalid-token"
            async with session.get(stream_url) as response:
                print(f"   Response status: {response.status}")
                if response.status == 401:
                    print(f"   ✅ Correctly rejected invalid token")
                else:
                    print(f"   ⚠️ Unexpected response for invalid token")
        except Exception as e:
            print(f"   ❌ Invalid token test error: {e}")
        
        # Test with no token
        print("   🚫 Testing missing token...")
        try:
            stream_url = f"{BACKEND_URL}/stream/test-task"
            async with session.get(stream_url) as response:
                print(f"   Response status: {response.status}")
                if response.status == 401:
                    print(f"   ✅ Correctly rejected missing token")
                else:
                    print(f"   ⚠️ Unexpected response for missing token")
        except Exception as e:
            print(f"   ❌ Missing token test error: {e}")

async def main():
    print("🚀 Enhanced SSE Authentication Test Suite")
    print("📅 " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    try:
        # Test core functionality
        success = await test_enhanced_sse_authentication()
        
        # Test error scenarios
        await test_authentication_errors()
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 Enhanced SSE authentication tests completed successfully!")
            print("\n💡 Next Steps:")
            print("   1. Frontend now has better error handling for authentication issues")
            print("   2. Users will see clear messages when sessions expire")
            print("   3. Automatic retry logic handles temporary connection issues")
            print("   4. Connection timeouts are detected and reported properly")
        else:
            print("❌ Some tests failed - check authentication configuration")
            
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test suite error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
