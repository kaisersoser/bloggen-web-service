#!/usr/bin/env python3

import os
import sys
import jwt
from datetime import datetime, timedelta
import time

def debug_token_generation():
    """Debug the exact timezone handling in our token generation"""
    
    print("🔍 JWT Token Generation Timezone Debug")
    print("=" * 60)
    
    print("📅 Current Time References:")
    now_local = datetime.now()
    now_utc = datetime.utcnow()
    now_timestamp = time.time()
    
    print(f"   datetime.now():        {now_local}")
    print(f"   datetime.utcnow():     {now_utc}")
    print(f"   time.time():           {now_timestamp}")
    print(f"   Local->timestamp:      {now_local.timestamp()}")
    print(f"   UTC->timestamp:        {now_utc.timestamp()}")
    print(f"   Difference:            {now_local.timestamp() - now_utc.timestamp()} seconds")
    
    # Generate tokens using different time references
    secret = os.getenv("NEXTAUTH_SECRET", "Ver0EvKSf1T5hN4/6NDsnPyZf8S7dJZ/Ewksc2Y2L7w=")
    user_id = "cmdaiv5530000z9nxqmyg445v"
    
    print(f"\n🔑 Token Generation Comparison:")
    
    # Method 1: Using datetime.utcnow() (current method)
    utc_time = datetime.utcnow()
    payload_utc = {
        "sub": user_id,
        "email": "charles.vogt@gmail.com",
        "name": "Charles Vogt", 
        "role": "ADMIN",
        "iat": int(utc_time.timestamp()),
        "exp": int((utc_time + timedelta(hours=1)).timestamp())
    }
    token_utc = jwt.encode(payload_utc, secret, algorithm="HS256")
    
    print(f"1️⃣ UTC Method (datetime.utcnow()):")
    print(f"   iat: {payload_utc['iat']} -> {datetime.fromtimestamp(payload_utc['iat'])}")
    print(f"   exp: {payload_utc['exp']} -> {datetime.fromtimestamp(payload_utc['exp'])}")
    
    # Method 2: Using time.time() directly
    current_timestamp = int(time.time())
    payload_time = {
        "sub": user_id,
        "email": "charles.vogt@gmail.com",
        "name": "Charles Vogt",
        "role": "ADMIN", 
        "iat": current_timestamp,
        "exp": current_timestamp + 3600
    }
    token_time = jwt.encode(payload_time, secret, algorithm="HS256")
    
    print(f"\n2️⃣ time.time() Method:")
    print(f"   iat: {payload_time['iat']} -> {datetime.fromtimestamp(payload_time['iat'])}")
    print(f"   exp: {payload_time['exp']} -> {datetime.fromtimestamp(payload_time['exp'])}")
    
    # Test validation of both tokens
    print(f"\n🧪 Validation Test:")
    for i, (method, token) in enumerate([(("UTC Method", token_utc)), (("time.time() Method", token_time))], 1):
        try:
            decoded = jwt.decode(token, secret, algorithms=["HS256"])
            print(f"   {i}️⃣ {method[0]}: ✅ VALID")
        except jwt.ExpiredSignatureError:
            print(f"   {i}️⃣ {method[0]}: ❌ EXPIRED")
        except Exception as e:
            print(f"   {i}️⃣ {method[0]}: ❌ ERROR: {e}")

if __name__ == "__main__":
    debug_token_generation()
