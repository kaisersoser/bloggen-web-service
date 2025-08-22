#!/usr/bin/env python3

import jwt
import os
from datetime import datetime
import time

def test_jwt_validation():
    """Test JWT validation exactly like the backend does"""
    
    # The timezone-fixed token we just generated
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjbWRhaXY1NTMwMDAwejlueHFteWc0NDV2IiwiZW1haWwiOiJjaGFybGVzLnZvZ3RAZ21haWwuY29tIiwibmFtZSI6IkNoYXJsZXMgVm9ndCIsInJvbGUiOiJBRE1JTiIsImlhdCI6MTc1NTU1MzQzMiwiZXhwIjoxNzU1NjM5ODMyfQ.OJATsfAwge4JbV2wfDlWTXLkfhgvjxibbXrTrlEkIt0"
    
    print("🧪 JWT Validation Test (Backend Simulation)")
    print("=" * 60)
    
    # Use the same secret as the backend
    secret = os.getenv("NEXTAUTH_SECRET", "Ver0EvKSf1T5hN4/6NDsnPyZf8S7dJZ/Ewksc2Y2L7w=")
    
    print(f"🔑 Using secret: {secret[:20]}...")
    
    # Show different time references
    current_local = datetime.now().timestamp()
    current_utc = datetime.utcnow().timestamp()
    print(f"\n🕐 Time References:")
    print(f"   time.time(): {time.time()}")
    print(f"   datetime.now().timestamp(): {current_local}")
    print(f"   datetime.utcnow().timestamp(): {current_utc}")
    print(f"   TIMEZONE DIFFERENCE: {current_local - current_utc} seconds ({(current_local - current_utc)/3600} hours)")
    
    try:
        # First decode without verification to see payload
        payload = jwt.decode(token, options={"verify_signature": False})
        print(f"\n📋 Token Payload (unverified):")
        print(f"   iat: {payload['iat']} -> {datetime.fromtimestamp(payload['iat'])}")
        print(f"   exp: {payload['exp']} -> {datetime.fromtimestamp(payload['exp'])}")
        
        # Check if token is expired according to UTC time
        print(f"\n⏰ Expiry Analysis:")
        print(f"   Token expires at (UTC): {payload['exp']}")
        print(f"   Current UTC time: {current_utc}")
        print(f"   Time until expiry (UTC): {payload['exp'] - current_utc} seconds")
        
        if payload['exp'] < current_utc:
            print("   ❌ Token is EXPIRED according to UTC time")
        else:
            print("   ✅ Token is still VALID according to UTC time")
        
        # Now try to validate exactly like the backend
        print(f"\n🔍 Attempting JWT validation (with verification)...")
        validated_payload = jwt.decode(token, secret, algorithms=["HS256"])
        
        print("✅ JWT validation SUCCESSFUL!")
        print(f"   User ID: {validated_payload.get('sub')}")
        print(f"   Email: {validated_payload.get('email')}")
        print(f"   Role: {validated_payload.get('role')}")
        
    except jwt.ExpiredSignatureError as e:
        print(f"❌ JWT validation FAILED: Token expired")
        print(f"   Error: {e}")
        print(f"   This confirms the backend is using UTC time for validation")
        
    except Exception as e:
        print(f"❌ JWT validation FAILED: {e}")

if __name__ == "__main__":
    test_jwt_validation()
