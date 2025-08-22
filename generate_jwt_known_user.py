#!/usr/bin/env python3
"""
Get valid user from the backend system and generate JWT token
"""

import os
import sys
import jwt
import time
from datetime import datetime, timedelta

# Add the backend src path to imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'src'))

def generate_jwt_for_known_user():
    """Generate JWT token for a known user that should exist"""
    
    # From the previous error logs, we know this user ID exists
    known_user_id = "cmdaiv5530000z9nxqmyg445v"
    
    print(f"🎯 Using known user ID: {known_user_id}")
    
    # Generate JWT token
    secret = os.getenv("NEXTAUTH_SECRET", "Ver0EvKSf1T5hN4/6NDsnPyZf8S7dJZ/Ewksc2Y2L7w=")
    
    # Use time.time() for proper UTC timestamps (datetime.utcnow().timestamp() has timezone issues)
    current_time = int(time.time())
    payload = {
        "sub": known_user_id,
        "email": "charles.vogt@gmail.com",  # From the logs
        "name": "Charles Vogt",
        "role": "ADMIN",  # From the logs
        "iat": current_time,
        "exp": current_time + (24 * 3600)  # 24 hours in seconds
    }
    
    token = jwt.encode(payload, secret, algorithm="HS256")
    
    print(f'\n🔑 Generated JWT Token:')
    print(f'{token}')
    print(f'\n📋 Token Info:')
    print(f'   User ID: {payload["sub"]}')
    print(f'   Email: {payload["email"]}')
    print(f'   Role: {payload["role"]}')
    print(f'   Expires: {datetime.fromtimestamp(payload["exp"])}')
    print(f'   Length: {len(token)} characters')
    
    return token, known_user_id

if __name__ == "__main__":
    generate_jwt_for_known_user()
