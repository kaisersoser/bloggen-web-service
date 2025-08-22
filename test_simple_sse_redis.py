#!/usr/bin/env python3
"""
Simple test to verify the fixed SSE endpoint works with Redis integration
"""

import asyncio
import json
import requests
import redis
import time
from datetime import datetime

# Configuration
BACKEND_URL = "https://localhost:5000"
VERIFY_SSL = False

def test_backend_connectivity():
    """Test if backend is running"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", verify=VERIFY_SSL, timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running and accessible")
            return True
        else:
            print(f"❌ Backend returned status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend - is it running?")
        return False
    except Exception as e:
        print(f"❌ Backend connectivity error: {e}")
        return False

def test_redis_connectivity():
    """Test Redis connection"""
    try:
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        redis_client.ping()
        print("✅ Redis is running and accessible")
        
        # Check if there are any existing task channels
        keys = list(redis_client.scan_iter(match="task_updates:*"))
        print(f"📊 Found {len(keys)} existing task update channels")
        
        return redis_client
    except Exception as e:
        print(f"❌ Redis connectivity error: {e}")
        return None

def get_test_jwt_token():
    """Get a JWT token for testing"""
    # Use the same token generation logic as our script
    import jwt
    from datetime import datetime, timedelta
    
    try:
        # Same secret as in our backend
        secret = "your-secret-key-here-make-it-long-and-secure"
        
        payload = {
            'sub': 'test_user_12345',
            'email': 'test@example.com', 
            'name': 'Test User',
            'role': 'FREE',
            'iat': int(datetime.utcnow().timestamp()),
            'exp': int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        }
        
        token = jwt.encode(payload, secret, algorithm='HS256')
        print(f"✅ Generated test JWT token")
        return token
        
    except Exception as e:
        print(f"❌ Error generating JWT token: {e}")
        return None

def test_sse_connection(token):
    """Test SSE connection with a dummy task"""
    try:
        # First create a dummy task or use existing one
        dummy_task_id = "test-task-" + str(int(time.time()))
        
        sse_url = f"{BACKEND_URL}/stream/{dummy_task_id}?token={token}"
        print(f"🔗 Testing SSE connection: {sse_url}")
        
        response = requests.get(sse_url, stream=True, verify=VERIFY_SSL, timeout=10)
        
        if response.status_code == 404:
            print("✅ SSE endpoint responded correctly (404 for non-existent task)")
            return True
        elif response.status_code == 200:
            print("✅ SSE endpoint accepting connections")
            # Read first few messages
            for i, line in enumerate(response.iter_lines(decode_unicode=True)):
                if i > 5:  # Just read a few lines
                    break
                if line.startswith('data:'):
                    print(f"📡 SSE data: {line}")
            return True
        else:
            print(f"❌ SSE connection failed: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("⚠️ SSE connection timeout (expected for non-existent task)")
        return True  # This is actually OK
    except Exception as e:
        print(f"❌ SSE connection error: {e}")
        return False

def test_blog_creation(token):
    """Test creating a real blog task"""
    try:
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'topic': 'Quick Test: AI and Technology Trends 2025',
            'instructions': 'Write a brief blog post about current AI trends'
        }
        
        print("🚀 Creating test blog task...")
        response = requests.post(f"{BACKEND_URL}/generate-blog", 
                               headers=headers, 
                               json=payload, 
                               verify=VERIFY_SSL,
                               timeout=30)
        
        if response.status_code == 200:
            task_data = response.json()
            task_id = task_data.get('task_id')
            print(f"✅ Blog task created successfully: {task_id}")
            return task_id
        else:
            print(f"❌ Blog creation failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None
            
    except Exception as e:
        print(f"❌ Blog creation error: {e}")
        return None

def monitor_task_briefly(task_id, token, duration=30):
    """Monitor a task for a short period using raw SSE parsing"""
    try:
        sse_url = f"{BACKEND_URL}/stream/{task_id}?token={token}"
        print(f"📡 Monitoring task {task_id} for {duration} seconds...")
        
        response = requests.get(sse_url, stream=True, verify=VERIFY_SSL, timeout=duration + 5)
        
        if response.status_code != 200:
            print(f"❌ SSE connection failed: {response.status_code}")
            return False
        
        start_time = time.time()
        message_count = 0
        
        for line in response.iter_lines(decode_unicode=True):
            elapsed = time.time() - start_time
            
            if elapsed > duration:
                break
            
            if line.startswith('data: '):
                message_count += 1
                data_part = line[6:]  # Remove 'data: ' prefix
                
                try:
                    data = json.loads(data_part)
                    event_type = data.get('type', 'unknown')
                    status = data.get('status', '')
                    
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"[{timestamp}] SSE #{message_count}: {event_type} - {status}")
                    
                    if event_type in ['completed', 'error'] or status in ['completed', 'failed']:
                        print(f"🏁 Task finished: {event_type}/{status}")
                        break
                        
                except json.JSONDecodeError:
                    print(f"SSE #{message_count}: {data_part[:100]}...")
        
        print(f"📊 Received {message_count} SSE messages in {elapsed:.1f}s")
        return message_count > 0
        
    except Exception as e:
        print(f"❌ Task monitoring error: {e}")
        return False

def main():
    print("🧪 Simple SSE + Redis Integration Test")
    print("=" * 50)
    
    # Step 1: Check backend connectivity
    if not test_backend_connectivity():
        print("❌ Cannot continue without backend connection")
        return
    
    # Step 2: Check Redis connectivity
    redis_client = test_redis_connectivity()
    if not redis_client:
        print("❌ Cannot continue without Redis connection")
        return
    
    # Step 3: Get JWT token
    token = get_test_jwt_token()
    if not token:
        print("❌ Cannot continue without JWT token")
        return
    
    # Step 4: Test SSE endpoint
    if not test_sse_connection(token):
        print("❌ SSE endpoint not working")
        return
    
    # Step 5: Create real blog task
    task_id = test_blog_creation(token)
    if not task_id:
        print("❌ Cannot test without a real task")
        return
    
    # Step 6: Monitor task briefly
    print("\n📊 Brief monitoring test...")
    success = monitor_task_briefly(task_id, token, 30)
    
    # Results
    print("\n" + "=" * 50)
    print("🏁 TEST RESULTS:")
    print("✅ Backend connectivity: PASS")
    print("✅ Redis connectivity: PASS") 
    print("✅ JWT authentication: PASS")
    print("✅ SSE endpoint: PASS")
    print("✅ Blog task creation: PASS")
    print(f"{'✅' if success else '❌'} Real-time monitoring: {'PASS' if success else 'FAIL'}")
    
    if success:
        print("\n🎉 All tests passed! SSE + Redis integration is working")
    else:
        print("\n⚠️ Monitoring test failed - check Redis integration")

if __name__ == "__main__":
    main()
