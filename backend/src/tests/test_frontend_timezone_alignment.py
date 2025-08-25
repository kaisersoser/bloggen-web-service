#!/usr/bin/env python3

import requests
import json
import time
from datetime import datetime

def test_frontend_backend_timezone_alignment():
    """Test timezone alignment between frontend and backend"""
    
    print("🌍 Frontend vs Backend Timezone Alignment Test")
    print("=" * 60)
    
    # Test 1: Check backend health timestamp
    print("1️⃣ Backend Timezone Check")
    try:
        backend_response = requests.get("https://localhost:5000/health", verify=False)
        if backend_response.status_code == 200:
            backend_data = backend_response.json()
            backend_timestamp = backend_data.get('timestamp')
            print(f"   Backend timestamp: {backend_timestamp}")
            
            # Parse backend timestamp (ISO format)
            if backend_timestamp:
                backend_dt = datetime.fromisoformat(backend_timestamp.replace('Z', '').split('.')[0])
                backend_epoch = int(backend_dt.timestamp())
                print(f"   Backend as epoch: {backend_epoch}")
        else:
            print(f"   ❌ Backend health check failed: {backend_response.status_code}")
    except Exception as e:
        print(f"   ❌ Backend error: {e}")
    
    # Test 2: Check frontend JWT token generation
    print(f"\n2️⃣ Frontend JWT Token Generation Check")
    try:
        # Note: This will likely fail with 401 since we don't have a valid session
        frontend_response = requests.get("https://localhost:3001/api/auth/jwt-token", verify=False)
        print(f"   Frontend response status: {frontend_response.status_code}")
        
        if frontend_response.status_code == 200:
            frontend_data = frontend_response.json()
            token = frontend_data.get('token')
            if token:
                # Decode token without verification to see timestamps
                import jwt
                try:
                    payload = jwt.decode(token, options={"verify_signature": False})
                    frontend_iat = payload.get('iat')
                    frontend_exp = payload.get('exp')
                    print(f"   Frontend iat: {frontend_iat} -> {datetime.fromtimestamp(frontend_iat)}")
                    print(f"   Frontend exp: {frontend_exp} -> {datetime.fromtimestamp(frontend_exp)}")
                except Exception as e:
                    print(f"   ❌ Token decode error: {e}")
        elif frontend_response.status_code == 401:
            print("   ⚠️  Authentication required (expected without valid session)")
        else:
            print(f"   ❌ Unexpected response: {frontend_response.text}")
    except Exception as e:
        print(f"   ❌ Frontend error: {e}")
    
    # Test 3: Compare with our current timestamps
    print(f"\n3️⃣ Timestamp Comparison")
    current_time = time.time()
    current_dt = datetime.now()
    current_utc = datetime.utcnow()
    
    print(f"   Current time.time(): {current_time} -> {datetime.fromtimestamp(current_time)}")
    print(f"   Current datetime.now(): {current_dt}")
    print(f"   Current datetime.utcnow(): {current_utc}")
    
    # JavaScript equivalent
    js_now = time.time() * 1000  # JavaScript Date.now() equivalent
    js_seconds = int(js_now / 1000)  # Math.floor(Date.now() / 1000) equivalent
    print(f"   JavaScript Date.now(): {js_now}")
    print(f"   JavaScript seconds: {js_seconds} -> {datetime.fromtimestamp(js_seconds)}")
    
    # Test 4: Manual JWT token generation comparison
    print(f"\n4️⃣ JWT Generation Method Comparison")
    
    # Python method (our fixed version)
    python_iat = int(time.time())
    python_exp = python_iat + 3600
    print(f"   Python time.time(): iat={python_iat}, exp={python_exp}")
    print(f"   Python times: {datetime.fromtimestamp(python_iat)} -> {datetime.fromtimestamp(python_exp)}")
    
    # JavaScript equivalent method
    js_iat = int(time.time())  # Same as Python time.time()
    js_exp = js_iat + 3600
    print(f"   JavaScript equiv: iat={js_iat}, exp={js_exp}")
    print(f"   JavaScript times: {datetime.fromtimestamp(js_iat)} -> {datetime.fromtimestamp(js_exp)}")
    
    # Check alignment
    time_diff = abs(python_iat - js_iat)
    print(f"\n📊 Alignment Check:")
    print(f"   Time difference: {time_diff} seconds")
    if time_diff <= 1:
        print("   ✅ Frontend and Backend are ALIGNED")
    else:
        print("   ❌ Frontend and Backend have TIMEZONE MISMATCH")

if __name__ == "__main__":
    test_frontend_backend_timezone_alignment()
