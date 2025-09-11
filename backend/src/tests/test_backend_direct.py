#!/usr/bin/env python3
"""
Test the backend generate-blog endpoint directly to diagnose issues.
"""
import requests
import json
import jwt
import os
import urllib3
from datetime import datetime, timedelta

# Disable SSL warnings for localhost testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_backend_blog_generation():
    base_url = "https://localhost:5000"
    
    print("🔍 Testing Backend Blog Generation")
    print("=" * 50)
    
    # Create a test JWT token (same as frontend does)
    secret = os.getenv("NEXTAUTH_SECRET")
    if not secret:
        raise ValueError("NEXTAUTH_SECRET environment variable is required")
    test_user_id = "test_user_123"
    
    # Create JWT token
    now = datetime.utcnow()
    exp_time = now + timedelta(hours=24)  # 24 hour expiration
    
    payload = {
        "sub": test_user_id,
        "email": "test@example.com", 
        "name": "Test User",
        "role": "FREE",
        "iat": int(now.timestamp()),
        "exp": int(exp_time.timestamp())
    }
    
    print(f"   Token issued at: {now} ({int(now.timestamp())})")
    print(f"   Token expires at: {exp_time} ({int(exp_time.timestamp())})")
    
    test_token = jwt.encode(payload, secret, algorithm="HS256")
    
    print(f"✅ Created test JWT token for user: {test_user_id}")
    
    # Test blog generation request
    print("\n📝 Testing blog generation...")
    test_data = {
        "task_id": "test_task_123",
        "topic": "The best AI tools for productivity",
        "instructions": "Write a comprehensive blog post about AI productivity tools",
        "user_id": test_user_id
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {test_token}"
    }
    
    try:
        response = requests.post(
            f"{base_url}/generate-blog",
            headers=headers,
            json=test_data,
            verify=False,
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text[:500]}...")
        
        if response.status_code == 200:
            response_data = response.json()
            task_id = response_data.get("task_id")
            print(f"   ✅ Blog generation started with task_id: {task_id}")
            
            # Test task status endpoint
            print(f"\n🔍 Checking task status...")
            status_response = requests.get(
                f"{base_url}/tasks/{task_id}",
                headers=headers,
                verify=False
            )
            print(f"   Task status: {status_response.status_code} - {status_response.text[:200]}...")
            
        else:
            print(f"   ❌ Blog generation failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Request failed: {e}")

if __name__ == "__main__":
    test_backend_blog_generation()
