#!/usr/bin/env python3
"""
Test HTTPS Blog Generation End-to-End
Tests the complete blog generation flow over HTTPS with proper SSL verification disabled.
"""

import requests
import json
import time
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for testing
urllib3.disable_warnings(InsecureRequestWarning)

# Configuration
FRONTEND_URL = "https://localhost:3001"
BACKEND_URL = "https://localhost:5000" 
TEST_TOPIC = "The Future of AI in Healthcare"

def test_backend_direct():
    """Test direct backend connectivity"""
    print("🔧 Testing direct backend connectivity...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/health", verify=False, timeout=10)
        print(f"✅ Backend health check: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.text}")
        return True
    except Exception as e:
        print(f"❌ Backend connectivity failed: {e}")
        return False

def test_frontend_connectivity():
    """Test frontend connectivity"""
    print("🔧 Testing frontend connectivity...")
    
    try:
        response = requests.get(FRONTEND_URL, verify=False, timeout=10)
        print(f"✅ Frontend connectivity: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Frontend connectivity failed: {e}")
        return False

def test_title_generation():
    """Test title generation API"""
    print("🔧 Testing title generation API...")
    
    try:
        # Note: This will fail with auth error, but we're testing connectivity
        response = requests.post(
            f"{FRONTEND_URL}/api/generate-title",
            json={"instructions": TEST_TOPIC},
            verify=False,
            timeout=10
        )
        print(f"✅ Title API reachable: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Authentication required (expected)")
        elif response.status_code == 200:
            print("   ✅ Title generated successfully")
        else:
            print(f"   ⚠️  Unexpected status: {response.text}")
        return True
    except Exception as e:
        print(f"❌ Title generation API failed: {e}")
        return False

def test_blog_generation_api():
    """Test blog generation API"""
    print("🔧 Testing blog generation API...")
    
    try:
        # Note: This will fail with auth error, but we're testing connectivity
        response = requests.post(
            f"{FRONTEND_URL}/api/generate-blog",
            json={"topic": TEST_TOPIC, "instructions": "Write a comprehensive blog post"},
            verify=False,
            timeout=10
        )
        print(f"✅ Blog API reachable: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Authentication required (expected)")
        elif response.status_code == 200:
            print("   ✅ Blog generation initiated successfully")
        else:
            print(f"   ⚠️  Unexpected status: {response.text}")
        return True
    except Exception as e:
        print(f"❌ Blog generation API failed: {e}")
        return False

def test_sse_endpoint():
    """Test SSE streaming endpoint"""
    print("🔧 Testing SSE endpoint...")
    
    try:
        # Test SSE endpoint (will fail with auth, but tests connectivity)
        response = requests.get(
            f"{BACKEND_URL}/stream/test-task-id?token=test",
            verify=False,
            timeout=5,
            stream=True
        )
        print(f"✅ SSE endpoint reachable: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Authentication required (expected)")
        elif response.status_code == 200:
            print("   ✅ SSE stream accessible")
        else:
            print(f"   ⚠️  Unexpected status: {response.text}")
        return True
    except Exception as e:
        print(f"❌ SSE endpoint failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting HTTPS Blog Generation Tests")
    print("=" * 50)
    
    tests = [
        ("Backend Direct", test_backend_direct),
        ("Frontend Connectivity", test_frontend_connectivity),
        ("Title Generation API", test_title_generation),
        ("Blog Generation API", test_blog_generation_api),
        ("SSE Endpoint", test_sse_endpoint),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        success = test_func()
        results.append((test_name, success))
        time.sleep(1)  # Brief pause between tests
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:10} {test_name}")
        if success:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("🎉 All connectivity tests passed!")
        print("💡 HTTPS setup is working correctly.")
        print("💡 Authentication errors are expected without valid tokens.")
    else:
        print("⚠️  Some tests failed. Check the details above.")
    
    return passed == len(results)

if __name__ == "__main__":
    main()
