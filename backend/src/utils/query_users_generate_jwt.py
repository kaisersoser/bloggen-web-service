#!/usr/bin/env python3
# flake8: noqa
"""
Query database for valid users and generate JWT token
"""

import asyncio
import asyncpg
import os
import jwt
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


async def get_user_and_generate_token():
    """Get a user from database and generate JWT token"""

    # Connect with statement cache disabled for pgbouncer compatibility
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"), statement_cache_size=0)
    try:
        # Get users from database
        users = await conn.fetch("SELECT id, email, name, role FROM users LIMIT 5")

        if not users:
            print("❌ No users found in database")
            return None

        print("📋 Users in database:")
        for i, user in enumerate(users, 1):
            print(f'   {i}. ID: {user["id"]}')
            print(f'      Email: {user["email"]}')
            print(f'      Name: {user["name"]}')
            print(f'      Role: {user["role"]}')
            print("      ---")

        # Use the first user for JWT token generation
        first_user = users[0]
        user_id = first_user["id"]
        email = first_user["email"]
        name = first_user["name"]
        role = first_user["role"]

        print(f"\n🎯 Selected user for JWT token:")
        print(f"   ID: {user_id}")
        print(f"   Email: {email}")
        print(f"   Role: {role}")

        # Generate JWT token
        secret = os.getenv("NEXTAUTH_SECRET")
        if not secret:
            raise ValueError("NEXTAUTH_SECRET environment variable is required")

        # Use time.time() for proper UTC timestamps (datetime.utcnow().timestamp() has timezone issues)
        current_time = int(time.time())
        payload = {
            "sub": user_id,
            "email": email,
            "name": name,
            "role": role,
            "iat": current_time,
            "exp": current_time + 3600,  # 1 hour in seconds
        }

        token = jwt.encode(payload, secret, algorithm="HS256")

        print(f"\n🔑 Generated JWT Token:")
        print(f"{token}")
        print(f"\n📋 Token Info:")
        print(f'   Expires: {datetime.fromtimestamp(payload["exp"])}')
        print(f"   Length: {len(token)} characters")

        return token, user_id

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(get_user_and_generate_token())
