#!/usr/bin/env python3
# flake8: noqa
"""
SSE Connection Diagnostic Test

This test specifically focuses on diagnosing why SSE connections might be timing out
even though authentication and database issues are resolved.
"""

import asyncio
import aiohttp
import json
import jwt
import time
import os
from datetime import datetime

BACKEND_URL = "https://localhost:5000"
REAL_USER_ID = "cmebux3a00000z983mtma7n8j"  # Real user from Supabase


def generate_valid_jwt() -> str:
    """Generate a JWT token with a real user ID from Supabase"""
    secret = os.getenv("NEXTAUTH_SECRET")
    if not secret:
        raise ValueError("NEXTAUTH_SECRET environment variable is required")
    current_time = int(time.time())
    payload = {
        "sub": REAL_USER_ID,
        "email": "kaisersoser37@gmail.com",
        "name": "Real User",
        "role": "ADMIN",
        "iat": current_time,
        "exp": current_time + 3600,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


async def test_sse_connection_timing():
    """Test SSE connection timing and response patterns"""
    print("🔍 SSE Connection Timing Diagnostic")
    print("=" * 50)

    token = generate_valid_jwt()

    connector = aiohttp.TCPConnector(ssl=False)
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        try:
            # First, create a real blog generation task
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            payload = {
                "topic": "SSE Connection Timing Test",
                "target_audience": "developers",
                "tone": "technical",
            }

            print("1️⃣ Creating blog generation task...")
            start_time = datetime.now()

            async with session.post(
                f"{BACKEND_URL}/generate-blog", json=payload, headers=headers
            ) as response:

                task_creation_time = (datetime.now() - start_time).total_seconds()
                print(f"   ⏱️ Task creation took: {task_creation_time:.2f}s")
                print(f"   📡 Response status: {response.status}")

                if response.status != 200:
                    error_text = await response.text()
                    print(f"   ❌ Task creation failed: {error_text}")
                    return

                result = await response.json()
                task_id = result.get("task_id")
                print(f"   ✅ Task created: {task_id}")

                # Now test SSE connection timing
                print(f"\n2️⃣ Testing SSE connection to {task_id}...")
                await test_detailed_sse_timing(session, task_id, token)

        except Exception as e:
            print(f"❌ Test error: {e}")


async def test_detailed_sse_timing(session, task_id, token):
    """Test detailed SSE connection timing"""
    try:
        stream_url = f"{BACKEND_URL}/stream/{task_id}?token={token}"

        print(f"   🔗 Connecting to: /stream/{task_id}")

        # Track connection timing
        connection_start = datetime.now()
        connection_established = False
        first_message_time = None
        message_count = 0

        async with session.get(stream_url) as response:
            connection_time = (datetime.now() - connection_start).total_seconds()
            print(f"   ⏱️ Connection response took: {connection_time:.2f}s")
            print(f"   📡 SSE Response Status: {response.status}")

            if response.status != 200:
                error_text = await response.text()
                print(f"   ❌ SSE connection failed: {error_text}")
                return

            connection_established = True
            print(f"   ✅ SSE connection established")

            # Monitor messages with detailed timing
            try:
                async for line in response.content:
                    elapsed = (datetime.now() - connection_start).total_seconds()

                    # Stop after 60 seconds to avoid hanging
                    if elapsed > 60:
                        print(
                            f"   ⏰ Test completed after 60s - received {message_count} messages"
                        )
                        break

                    line = line.decode("utf-8").strip()
                    if line.startswith("data: "):
                        if first_message_time is None:
                            first_message_time = datetime.now()
                            first_msg_delay = (
                                first_message_time - connection_start
                            ).total_seconds()
                            print(f"   📨 First message after: {first_msg_delay:.2f}s")

                        try:
                            data = json.loads(line[6:])
                            message_count += 1

                            msg_type = data.get("message_type", "unknown")
                            progress = data.get("progress", 0)
                            message = data.get("message", "")[:60]

                            print(
                                f"   📨 [{elapsed:5.1f}s] Message {message_count}: [{msg_type}] {progress}% - {message}..."
                            )

                            # Stop after getting several messages to analyze timing
                            if message_count >= 10:
                                print(
                                    f"   ✅ Successfully received {message_count} messages - SSE working!"
                                )
                                break

                        except json.JSONDecodeError:
                            print(f"   📄 [{elapsed:5.1f}s] Non-JSON: {line[:60]}...")

                    elif (
                        line.startswith("event: ")
                        or line.startswith("id: ")
                        or line == ""
                    ):
                        # SSE metadata lines
                        continue
                    else:
                        print(f"   📄 [{elapsed:5.1f}s] Other: {line[:60]}...")

                # Summary
                total_time = (datetime.now() - connection_start).total_seconds()
                print(f"\n   📊 SSE Timing Summary:")
                print(f"      Connection established: {connection_time:.2f}s")
                if first_message_time:
                    first_delay = (
                        first_message_time - connection_start
                    ).total_seconds()
                    print(f"      First message: {first_delay:.2f}s")
                else:
                    print(f"      First message: Never received")
                print(f"      Total messages: {message_count}")
                print(f"      Total test time: {total_time:.2f}s")

                # Diagnosis
                if connection_time > 30:
                    print(
                        f"   🚨 ISSUE: Connection took {connection_time:.2f}s (>30s timeout)"
                    )
                elif first_message_time is None:
                    print(
                        f"   🚨 ISSUE: No messages received - backend may not be sending SSE data"
                    )
                elif message_count == 0:
                    print(f"   🚨 ISSUE: Connection established but no valid messages")
                else:
                    print(f"   ✅ SSE connection working normally")

            except asyncio.TimeoutError:
                print(f"   ⏰ SSE stream timeout after {elapsed:.2f}s")
            except Exception as e:
                print(f"   ❌ SSE stream error: {e}")

    except Exception as e:
        print(f"   ❌ SSE connection error: {e}")


async def main():
    print("🚀 SSE Connection Timing Diagnostic")
    print("📅 " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("🎯 This test will help identify why SSE connections timeout")

    try:
        await test_sse_connection_timing()

        print("\n" + "=" * 50)
        print("💡 Diagnostic Complete!")
        print("\n📋 What to look for:")
        print("   • Connection time >30s = Network/SSL issues")
        print("   • No first message = Backend not sending SSE data")
        print("   • Messages stop = Backend task processing issues")
        print("   • Frequent disconnects = Authentication token expiry")

    except KeyboardInterrupt:
        print("\n⏹️ Diagnostic interrupted")
    except Exception as e:
        print(f"\n💥 Diagnostic error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
