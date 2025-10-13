#!/usr/bin/env python3
# flake8: noqa

"""
Simple Redis Monitor - Monitor what gets published to Redis channels
This script will help us understand what's actually being sent to Redis
during blog generation vs what the frontend SSE receives.
"""

import redis
import json
import threading
import time
from datetime import datetime


def monitor_redis_channel(channel_pattern):
    """Monitor Redis channel for published messages"""
    try:
        # Connect to Redis (same config as main app)
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)

        # Subscribe to all SSE channels
        pubsub = r.pubsub()
        pubsub.psubscribe(channel_pattern)

        print(f"🔍 MONITORING REDIS CHANNEL: {channel_pattern}")
        print(f"⏰ Started at: {datetime.now()}")
        print("=" * 60)

        message_count = 0

        for message in pubsub.listen():
            if message["type"] == "pmessage":
                message_count += 1
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                channel = message["channel"]
                data = message["data"]

                print(f"[{timestamp}] 📢 Channel: {channel}")
                print(f"[{timestamp}] 📝 Data: {data}")
                print("-" * 40)

                # Try to parse as JSON for better formatting
                try:
                    parsed = json.loads(data)
                    print(f"[{timestamp}] 🔍 Parsed: {json.dumps(parsed, indent=2)}")
                except:
                    pass
                print("=" * 60)

    except Exception as e:
        print(f"❌ Redis monitoring error: {e}")
        return 0

    return message_count


if __name__ == "__main__":
    print("🚀 REDIS SSE CHANNEL MONITOR")
    print("This will monitor all sse_immediate:* channels for published messages")
    print("Start a blog generation in another terminal to see Redis activity")
    print()

    try:
        # Monitor all SSE immediate channels
        total_messages = monitor_redis_channel("sse_immediate:*")
        print(f"\n✅ Monitoring completed. Total messages: {total_messages}")

    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
