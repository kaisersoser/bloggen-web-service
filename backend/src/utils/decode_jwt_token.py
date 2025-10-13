#!/usr/bin/env python3
# flake8: noqa

import jwt
import json
from datetime import datetime


def decode_token():
    """Decode and analyze the JWT token"""

    # The token we just generated
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjbWRhaXY1NTMwMDAwejlueHFteWc0NDV2IiwiZW1haWwiOiJjaGFybGVzLnZvZ3RAZ21haWwuY29tIiwibmFtZSI6IkNoYXJsZXMgVm9ndCIsInJvbGUiOiJBRE1JTiIsImlhdCI6MTc1NTU0NTQ0NywiZXhwIjoxNzU1NTQ5MDQ3fQ.2Z_4YkM6pNp6IPVDE-vcBJhrwRJqixvqKRqGLkM8OrA"

    print("🔍 JWT Token Analysis")
    print("=" * 50)

    try:
        # Decode without verification first to see the contents
        decoded = jwt.decode(token, options={"verify_signature": False})

        print("📋 Token Payload:")
        print(json.dumps(decoded, indent=2))

        # Convert timestamps to readable dates
        if "iat" in decoded:
            issued_time = datetime.fromtimestamp(decoded["iat"])
            print(f"\n🕒 Issued At (iat): {decoded['iat']} -> {issued_time}")

        if "exp" in decoded:
            expires_time = datetime.fromtimestamp(decoded["exp"])
            print(f"⏰ Expires At (exp): {decoded['exp']} -> {expires_time}")

        # Current time
        current_timestamp = int(datetime.utcnow().timestamp())
        current_time = datetime.fromtimestamp(current_timestamp)
        print(f"🕐 Current Time: {current_timestamp} -> {current_time}")

        # Time calculations
        if "exp" in decoded:
            time_until_expiry = decoded["exp"] - current_timestamp
            print(
                f"\n⏳ Time until expiry: {time_until_expiry} seconds ({time_until_expiry/60:.1f} minutes)"
            )

            if time_until_expiry > 0:
                print("✅ Token should still be VALID")
            else:
                print("❌ Token is EXPIRED")
                print(
                    f"   Expired {-time_until_expiry} seconds ago ({-time_until_expiry/60:.1f} minutes ago)"
                )

    except Exception as e:
        print(f"❌ Error decoding token: {e}")


if __name__ == "__main__":
    decode_token()
