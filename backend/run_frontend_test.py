#!/usr/bin/env python3
"""
Quick Frontend Notification Test Runner

Simplified E2E test that doesn't require Selenium.
Run this script and follow the on-screen instructions.
"""

import subprocess
import sys
import os

def ensure_redis_running():
    """Check if Redis is running."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("✅ Redis is running")
        return True
    except Exception as e:
        print(f"❌ Redis not available: {e}")
        print("💡 Start Redis with: redis-server")
        return False

def check_servers():
    """Check if backend and frontend servers are running."""
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    backend_ok = False
    frontend_ok = False
    
    # Check backend
    try:
        response = requests.get('https://localhost:5000/health', timeout=3, verify=False)
        if response.status_code == 200:
            backend_ok = True
            print("✅ Backend server is running")
    except:
        print("❌ Backend server not running")
        print("💡 Start with: cd backend && python src/main.py")
    
    # Check frontend
    try:
        response = requests.get('https://localhost:3001', timeout=3, verify=False)
        if response.status_code == 200:
            frontend_ok = True
            print("✅ Frontend server is running")
    except:
        print("❌ Frontend server not running")
        print("💡 Start with: cd frontend-nextjs/blog-generator-ui && npm run dev")
    
    return backend_ok, frontend_ok

def main():
    """Main test runner."""
    print("🧪 FRONTEND NOTIFICATION E2E TEST")
    print("=" * 50)
    
    # Check prerequisites
    if not ensure_redis_running():
        return 1
    
    backend_ok, frontend_ok = check_servers()
    
    if not backend_ok or not frontend_ok:
        print("\n❌ Prerequisites not met!")
        print("🔧 Please start the required servers and try again")
        return 1
    
    print("\n✅ All prerequisites met!")
    print("🚀 Starting frontend notification validation...")
    print("=" * 50)
    
    # Navigate to backend directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Run the test
    try:
        result = subprocess.run([
            sys.executable, 
            os.path.join(script_dir, 'test_frontend_notifications_simple.py')
        ], cwd=script_dir)
        
        return result.returncode
        
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())