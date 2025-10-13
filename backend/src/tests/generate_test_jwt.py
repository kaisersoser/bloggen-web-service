#!/usr/bin/env python3
# flake8: noqa
"""
Generate a valid JWT token for testing WebSocket connections
"""

import jwt
import time
import os


def generate_test_jwt():
    """Generate a valid JWT token for testing"""

    # Use the same secret as the backend
    secret = os.getenv("NEXTAUTH_SECRET")
    if not secret:
        raise ValueError("NEXTAUTH_SECRET environment variable is required")

    # Create test user payload
    now = int(time.time())
    payload = {
        "sub": "test_user_12345",  # User ID
        "email": "test@example.com",
        "name": "Test User",
        "role": "FREE",
        "iat": now,  # Issued at time
        "exp": now + 3600,  # Expires in 1 hour
    }

    # Generate JWT token
    token = jwt.encode(payload, secret, algorithm="HS256")

    return token, payload


if __name__ == "__main__":
    token, payload = generate_test_jwt()
    print("Generated test JWT token:")
    print(f"Token: {token}")
    print(f"Payload: {payload}")
    print(f"Token length: {len(token)}")
