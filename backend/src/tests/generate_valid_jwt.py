#!/usr/bin/env python3
# flake8: noqa
"""
Generate a valid JWT token using the backend's default secret
"""

import jwt
import os
from datetime import datetime, timedelta


def create_jwt_token():
    """Create JWT token with default secret from backend"""

    # Get secret from environment
    secret = os.getenv("NEXTAUTH_SECRET")
    if not secret:
        raise ValueError("NEXTAUTH_SECRET environment variable is required")

    # Token payload for real user
    payload = {
        "sub": "cmdaiv5530000z9nxqmyg445v",  # Real user ID
        "email": "charles.vogt@gmail.com",
        "name": "Charles Vogt",
        "role": "ADMIN",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=24),  # 24 hour expiry
    }

    # Generate JWT token
    token = jwt.encode(payload, secret, algorithm="HS256")

    return token


if __name__ == "__main__":
    token = create_jwt_token()
    print(f"Generated JWT Token:")
    print(token)

    # Save to file
    with open("valid_jwt_token.txt", "w") as f:
        f.write(token)

    print(f"\n✅ Token saved to valid_jwt_token.txt")
    print(f"📏 Token length: {len(token)} characters")
