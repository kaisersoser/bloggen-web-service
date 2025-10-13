#!/usr/bin/env python3
# flake8: noqa
"""
Test complete flow: Blog generation with Redis monitoring

This test creates a real blog generation task and monitors Redis channels
to see if TaskManager publishes updates properly.
"""

import asyncio
import json
import aiohttp
import redis.asyncio as redis
from datetime import datetime
import os
import sys


async def monitor_redis_during_blog_generation():
    """Monitor Redis channels while creating a blog post"""

    print("🔧 Testing complete blog generation with Redis monitoring...")

    # Redis connection
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        decode_responses=False,
    )

    try:
        await redis_client.ping()
        print("✅ Redis connection successful")

        # Get JWT token for authentication
        print("🔑 Getting authentication token...")

        # Use the valid JWT token
        try:
            with open("valid_jwt_token.txt", "r") as f:
                jwt_token = f.read().strip()
            print("✅ Valid JWT token loaded")
        except FileNotFoundError:
            print(
                "❌ valid_jwt_token.txt not found - please generate a valid JWT token first"
            )
            return False

        # Create blog generation task
        print("📝 Creating blog generation task...")

        backend_url = "https://localhost:5000"  # HTTPS with SSL certificates

        # SSL context for HTTPS
        import ssl

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Create blog task
            async with session.post(
                f"{backend_url}/generate-blog",
                json={
                    "topic": "The Future of AI in 2025",
                    "instructions": "Write a comprehensive overview",
                },
                headers={"Authorization": f"Bearer {jwt_token}"},
            ) as response:
                if response.status != 200:
                    print(f"❌ Failed to create blog task: {response.status}")
                    return False

                task_data = await response.json()
                task_id = task_data.get("task_id")

                if not task_id:
                    print("❌ No task_id in response")
                    return False

                print(f"✅ Blog task created: {task_id}")

                # Set up Reddit monitoring for this task
                channel = f"task_updates:{task_id}"
                pubsub = redis_client.pubsub()
                await pubsub.subscribe(channel)
                print(f"📡 Monitoring Redis channel: {channel}")

                # Monitor for 60 seconds
                message_count = 0
                timeout_task = asyncio.create_task(asyncio.sleep(60))

                print("👂 Listening for Redis messages...")
                print("   (This will show if TaskManager publishes to Redis)")

                async for message in pubsub.listen():
                    if message["type"] == "message":
                        message_count += 1
                        try:
                            redis_data = json.loads(message["data"].decode("utf-8"))
                            status = redis_data.get("status", "unknown")
                            progress = redis_data.get("progress", 0)
                            phase = redis_data.get("phase", "unknown")

                            print(
                                f"📨 Redis message {message_count}: {status} | {phase} | {progress}%"
                            )

                            # Stop if task completes
                            if status in ["completed", "failed"]:
                                print(f"✅ Task {status} - stopping monitoring")
                                break

                        except Exception as e:
                            print(f"❌ Error parsing Redis message: {e}")

                    # Check timeout
                    if timeout_task.done():
                        print("⏰ Monitoring timeout reached")
                        break

                print(f"\n📊 Redis Monitoring Results:")
                print(f"   Messages received: {message_count}")

                if message_count > 0:
                    print("✅ TaskManager IS publishing to Redis!")
                    print("✅ The SSE timeout issue must be in the SSE endpoint logic")
                else:
                    print("❌ TaskManager is NOT publishing to Redis")
                    print(
                        "💡 This explains the SSE timeouts - no Redis messages to receive"
                    )

                return message_count > 0

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        try:
            await pubsub.unsubscribe(channel)
            await redis_client.aclose()
        except:
            pass


async def test_backend_status():
    """Check if backend is running"""
    try:
        # Use SSL context that doesn't verify certificates for local development
        import ssl

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get("https://localhost:5000/health") as response:
                if response.status == 200:
                    print("✅ Backend is running (HTTPS)")
                    return True
                else:
                    print(f"❌ Backend health check failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Backend not accessible: {e}")
        return False


async def main():
    """Main test function"""
    print("🚀 Redis + Blog Generation Integration Test\n")

    # Check backend status first
    backend_running = await test_backend_status()

    if not backend_running:
        print("🔧 Please start the backend server first:")
        print("   cd backend && python src/main.py")
        return

    # Run the monitoring test
    success = await monitor_redis_during_blog_generation()

    print(f"\n📋 Final Result:")
    if success:
        print("✅ TaskManager publishes to Redis - SSE should work!")
        print(
            "🔧 If SSE still times out, the issue is in the SSE endpoint Redis listening logic"
        )
    else:
        print("❌ TaskManager doesn't publish to Redis - this explains SSE timeouts")
        print("🔧 Need to fix TaskManager Redis publishing to resolve SSE issues")


if __name__ == "__main__":
    asyncio.run(main())
