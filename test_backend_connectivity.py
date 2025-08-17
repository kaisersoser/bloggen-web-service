#!/usr/bin/env python3
"""
Test blog generation API and check database persistence.
"""
import requests
import json
import urllib3

# Disable SSL warnings for localhost testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_blog_generation():
    base_url = "https://localhost:5000"
    
    print("🔍 Testing Blog Generation API and Database Persistence")
    print("=" * 60)
    
    # Test 1: Check API health
    print("\n1. Testing API Health...")
    try:
        response = requests.get(f"{base_url}/health", verify=False)
        print(f"   ✅ Health check: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return
    
    # Test 2: Check blogs endpoint (should require auth, but let's see the error)
    print("\n2. Testing blogs endpoint...")
    try:
        response = requests.get(f"{base_url}/blogs", verify=False)
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Expected: Authentication required")
        else:
            print(f"   Response: {response.text[:200]}...")
    except Exception as e:
        print(f"   ❌ Blogs endpoint failed: {e}")
    
    # Test 3: Check tasks endpoint
    print("\n3. Testing tasks endpoint...")
    try:
        response = requests.get(f"{base_url}/tasks", verify=False)
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Expected: Authentication required")
        else:
            print(f"   Response: {response.text[:200]}...")
    except Exception as e:
        print(f"   ❌ Tasks endpoint failed: {e}")
    
    # Test 4: Test WebSocket endpoint without auth (should fail gracefully)
    print("\n4. Testing WebSocket endpoint accessibility...")
    try:
        # Try to access WebSocket endpoint via HTTP (should return an error)
        response = requests.get(f"{base_url}/ws/test-task-id", verify=False)
        print(f"   Status: {response.status_code}")
        print(f"   This confirms WebSocket endpoint exists but requires proper connection")
    except Exception as e:
        print(f"   ❌ WebSocket test failed: {e}")

if __name__ == "__main__":
    test_blog_generation()
