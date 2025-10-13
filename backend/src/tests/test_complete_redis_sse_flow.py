#!/usr/bin/env python3
# flake8: noqa
"""
Complete test of Redis + SSE integration flow
Tests the end-to-end communication from blog generation → Redis → SSE → Frontend
"""

import asyncio
import json
import time
import redis
import requests
import threading
from datetime import datetime
from contextlib import asynccontextmanager

# Backend configuration
BACKEND_URL = "https://localhost:5000"  # Fixed port
JWT_TOKEN = None

# Redis connection
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)


def get_jwt_token():
    """Get a valid JWT token for testing"""
    global JWT_TOKEN

    if JWT_TOKEN:
        return JWT_TOKEN

    try:
        # Try to get token from auth endpoint
        response = requests.post(
            f"{BACKEND_URL}/api/auth/jwt-token",
            json={"email": "test@example.com"},
            verify=False,
        )

        if response.status_code == 200:
            JWT_TOKEN = response.json().get("token")
            print(f"✅ Got JWT token: {JWT_TOKEN[:20]}...")
            return JWT_TOKEN
        else:
            print(f"❌ Failed to get JWT token: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Error getting JWT token: {e}")
        return None


def monitor_redis_channels():
    """Monitor Redis pub/sub channels for task updates"""
    try:
        pubsub = redis_client.pubsub()

        # Subscribe to all task update channels
        pubsub.psubscribe("task_updates:*")
        pubsub.psubscribe("user_updates:*")

        print("🔍 Monitoring Redis channels for updates...")

        for message in pubsub.listen():
            if message["type"] == "pmessage":
                channel = message["channel"]
                data = message["data"]
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

                try:
                    parsed_data = json.loads(data) if isinstance(data, str) else data
                    status = (
                        parsed_data.get("status", "unknown")
                        if isinstance(parsed_data, dict)
                        else "raw"
                    )
                    print(
                        f"📨 [{timestamp}] Redis Channel: {channel} → Status: {status}"
                    )

                    if isinstance(parsed_data, dict):
                        phase = parsed_data.get("phase", "")
                        progress = parsed_data.get("progress", 0)
                        if phase or progress:
                            print(f"    Phase: {phase}, Progress: {progress}%")
                except:
                    print(f"📨 [{timestamp}] Redis Channel: {channel} → Raw: {data}")

    except Exception as e:
        print(f"❌ Redis monitoring error: {e}")


def create_blog_task():
    """Create a new blog generation task"""
    token = get_jwt_token()
    if not token:
        print("❌ Cannot create task without JWT token")
        return None

    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "topic": "The Future of AI in Healthcare 2025",
            "instructions": "Write a comprehensive blog post about AI healthcare innovations",
        }

        print(f"🚀 Creating blog task...")
        response = requests.post(
            f"{BACKEND_URL}/generate-blog", headers=headers, json=payload, verify=False
        )

        if response.status_code == 200:
            task_data = response.json()
            task_id = task_data.get("task_id")
            print(f"✅ Blog task created: {task_id}")
            return task_id
        else:
            print(f"❌ Failed to create blog task: {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error creating blog task: {e}")
        return None


def monitor_sse_stream(task_id, duration=120):
    """Monitor SSE stream for a task"""
    token = get_jwt_token()
    if not token:
        print("❌ Cannot monitor SSE without JWT token")
        return

    try:
        import sseclient

        sse_url = f"{BACKEND_URL}/stream/{task_id}?token={token}"
        print(f"📡 Connecting to SSE stream: {sse_url}")

        response = requests.get(sse_url, stream=True, verify=False, timeout=duration)
        client = sseclient.SSEClient(response)

        start_time = time.time()

        for event in client.events():
            elapsed = time.time() - start_time
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

            if elapsed > duration:
                print(f"⏰ SSE monitoring timeout after {duration}s")
                break

            try:
                data = json.loads(event.data)
                event_type = data.get("type", "unknown")
                status = data.get("status", "")
                message = data.get("message", "")

                print(f"📺 [{timestamp}] SSE Event: {event_type}")
                if status:
                    print(f"    Status: {status}")
                if message:
                    print(f"    Message: {message}")

                # Exit if task completed
                if event_type == "completed" or status == "completed":
                    print("✅ Task completed, stopping SSE monitoring")
                    break
                elif event_type == "error" or status == "failed":
                    print("❌ Task failed, stopping SSE monitoring")
                    break

            except json.JSONDecodeError:
                print(f"📺 [{timestamp}] SSE Raw: {event.data}")

    except Exception as e:
        print(f"❌ SSE monitoring error: {e}")


def main():
    print("🧪 Testing Complete Redis + SSE Integration Flow")
    print("=" * 60)

    # Step 1: Check Redis connectivity
    try:
        redis_client.ping()
        print("✅ Redis connection successful")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return

    # Step 2: Check existing Redis channels
    channels = redis_client.pubsub()
    all_keys = redis_client.keys("*")
    print(f"📊 Redis keys found: {len(all_keys)}")

    # Step 3: Start Redis monitoring in background
    redis_thread = threading.Thread(target=monitor_redis_channels, daemon=True)
    redis_thread.start()
    time.sleep(1)  # Let Redis monitoring start

    # Step 4: Create blog generation task
    task_id = create_blog_task()
    if not task_id:
        print("❌ Cannot continue without task ID")
        return

    print(f"\n🎯 Task ID: {task_id}")
    print("📊 Monitoring both Redis and SSE for real-time updates...")
    print("=" * 60)

    # Step 5: Monitor SSE stream
    sse_thread = threading.Thread(
        target=monitor_sse_stream, args=(task_id, 180), daemon=True
    )
    sse_thread.start()

    # Step 6: Wait and monitor
    try:
        # Let it run for 3 minutes
        time.sleep(180)
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")

    print("\n🏁 Test completed")
    print("=" * 60)

    # Summary
    print("\n📋 SUMMARY:")
    print("✅ Redis monitoring: Running")
    print("✅ SSE monitoring: Running")
    print("✅ Blog task: Created")
    print("\n🔍 Check the logs above to see if:")
    print("  - Redis received task updates")
    print("  - SSE stream received updates")
    print("  - Both systems synchronized properly")


if __name__ == "__main__":
    main()
