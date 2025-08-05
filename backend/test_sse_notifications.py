#!/usr/bin/env python3
"""
Test script to verify SSE streaming functionality is working after the audit fixes.
"""

import asyncio
import requests
import json
import time
import jwt
from datetime import datetime
import urllib3

# Disable SSL warnings for testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
BACKEND_URL = "https://localhost:5000"
JWT_SECRET = "Ver0EvKSf1T5hN4/6NDsnPyZf8S7dJZ/Ewksc2Y2L7w="

def create_test_jwt():
    """Create a test JWT token"""
    payload = {
        'sub': 'test_user_sse_123',
        'email': 'test-sse@example.com',
        'name': 'SSE Test User',
        'role': 'FREE',
        'iat': int(time.time()),
        'exp': int(time.time()) + 3600
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def test_sse_notifications():
    """Test if SSE notifications are working"""
    print("=" * 70)
    print("🔍 SSE NOTIFICATION SYSTEM TEST")
    print("=" * 70)
    
    # Create test token
    token = create_test_jwt()
    print(f"✅ Test JWT created: {token[:50]}...")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Start blog generation
    print("\n1️⃣ Starting blog generation...")
    data = {
        'topic': 'Testing SSE Notifications',
        'instructions': 'Write a very short blog about testing real-time notifications'
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/generate-blog",
            headers=headers,
            json=data,
            verify=False,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            task_id = result.get('task_id')
            print(f"✅ Blog generation started")
            print(f"   Task ID: {task_id}")
            print(f"   Message: {result.get('message')}")
            
            # Test SSE stream
            print(f"\n2️⃣ Testing SSE stream for task: {task_id}")
            sse_url = f"{BACKEND_URL}/stream/{task_id}?token={token}"
            print(f"   SSE URL: {sse_url[:80]}...")
            
            # Test the SSE endpoint
            try:
                stream_response = requests.get(sse_url, verify=False, timeout=5, stream=True)
                print(f"   Stream response: {stream_response.status_code}")
                print(f"   Content-Type: {stream_response.headers.get('content-type', 'N/A')}")
                
                if stream_response.status_code == 200:
                    print("✅ SSE endpoint is accessible")
                    
                    # Try to read a few lines
                    print("   Reading stream data...")
                    lines_read = 0
                    for line in stream_response.iter_lines(decode_unicode=True):
                        if line and lines_read < 5:
                            print(f"   📡 {line}")
                            lines_read += 1
                        elif lines_read >= 5:
                            break
                    
                    if lines_read > 0:
                        print("✅ SSE stream is sending data!")
                    else:
                        print("⚠️ SSE stream connected but no data received")
                        
                else:
                    print(f"❌ SSE stream failed: {stream_response.status_code}")
                    
            except Exception as e:
                print(f"❌ SSE stream test failed: {e}")
                
        else:
            print(f"❌ Blog generation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Blog generation request failed: {e}")
    
    print("\n" + "=" * 70)
    print("🎯 SSE TEST SUMMARY")
    print("=" * 70)
    print("If you see '✅ SSE stream is sending data!' above,")
    print("then the notification system is working correctly!")
    print("\nIf not, check:")
    print("1. FastAPI backend is running (python src/fastapi_main.py)")
    print("2. Blog generation flow status_callback is working")
    print("3. SSE endpoint is properly implemented")

if __name__ == "__main__":
    test_sse_notifications()
