#!/usr/bin/env python3
# flake8: noqa
"""
Redis-SSE Bridge Diagnostic Tool

This tool monitors both Redis pub/sub channels AND SSE connections simultaneously
to identify where messages are being lost between Redis and the frontend.

It will:
1. Connect directly to Redis and monitor task channels
2. Connect to SSE endpoint and monitor messages
3. Compare what's published to Redis vs what reaches SSE
4. Identify the disconnect point
"""

import asyncio
import json
import logging
import signal
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import aioredis
import aiohttp
import ssl

# Configuration
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
BACKEND_URL = "https://localhost:5000"
FRONTEND_URL = "https://localhost:3001"

# SSL context for self-signed certificates
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


class RedisSSEDiagnostic:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.redis_client: Optional[aioredis.Redis] = None
        self.redis_messages: List[Dict[str, Any]] = []
        self.sse_messages: List[Dict[str, Any]] = []
        self.is_running = True

        # Redis channels to monitor
        self.redis_channels = [
            f"task_updates:{task_id}",
            f"sse_immediate:{task_id}",
            f"notifications:{task_id}",
            f"blog_generation:{task_id}",
        ]

    async def connect_redis(self):
        """Connect to Redis"""
        try:
            self.redis_client = aioredis.from_url(
                f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}", decode_responses=True
            )
            await self.redis_client.ping()
            print("✅ Redis connection established")
            return True
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            return False

    async def monitor_redis_channels(self):
        """Monitor Redis pub/sub channels"""
        if not self.redis_client:
            return

        try:
            pubsub = self.redis_client.pubsub()

            # Subscribe to all relevant channels
            for channel in self.redis_channels:
                await pubsub.subscribe(channel)
                print(f"📡 Subscribed to Redis channel: {channel}")

            print("🔍 Monitoring Redis publications...")

            async for message in pubsub.listen():
                if not self.is_running:
                    break

                if message["type"] == "message":
                    timestamp = datetime.now().isoformat()
                    channel = message["channel"]
                    data = message["data"]

                    try:
                        # Try to parse as JSON
                        parsed_data = (
                            json.loads(data) if isinstance(data, str) else data
                        )
                    except json.JSONDecodeError:
                        parsed_data = {"raw_data": data}

                    redis_msg = {
                        "timestamp": timestamp,
                        "channel": channel,
                        "data": parsed_data,
                        "raw": data,
                    }

                    self.redis_messages.append(redis_msg)

                    # Display Redis message
                    msg_type = parsed_data.get(
                        "message_type", parsed_data.get("type", "unknown")
                    )
                    message_text = parsed_data.get("message", str(parsed_data)[:50])
                    print(
                        f"🔴 REDIS [{datetime.now().strftime('%H:%M:%S')}] {channel} → {msg_type}: {message_text}"
                    )

        except Exception as e:
            print(f"❌ Redis monitoring error: {e}")
        finally:
            await pubsub.unsubscribe(*self.redis_channels)
            await pubsub.close()

    async def get_jwt_token(self) -> Optional[str]:
        """Get JWT token for SSE authentication"""
        try:
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=ssl_context)
            ) as session:
                async with session.get(
                    f"{FRONTEND_URL}/api/auth/jwt-token"
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("token")
                    else:
                        print(f"❌ JWT token request failed: {response.status}")
                        return None
        except Exception as e:
            print(f"❌ JWT token error: {e}")
            return None

    async def monitor_sse_connection(self):
        """Monitor SSE connection"""
        print("🔍 Attempting to get JWT token...")
        token = await self.get_jwt_token()

        if not token:
            print("❌ Cannot get JWT token - continuing without SSE monitoring")
            print(
                "   (SSE requires authentication, but Redis monitoring will continue)"
            )
            return

        sse_url = f"{BACKEND_URL}/stream/{self.task_id}?token={token}"
        print(f"🔗 Connecting to SSE: /stream/{self.task_id}")

        try:
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=ssl_context)
            ) as session:
                async with session.get(sse_url) as response:
                    if response.status != 200:
                        print(f"❌ SSE connection failed: {response.status}")
                        return

                    print("✅ SSE connection established")

                    async for line in response.content:
                        if not self.is_running:
                            break

                        line = line.decode("utf-8").strip()

                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove 'data: ' prefix
                            timestamp = datetime.now().isoformat()

                            try:
                                parsed_data = json.loads(data_str)

                                sse_msg = {
                                    "timestamp": timestamp,
                                    "data": parsed_data,
                                    "raw": data_str,
                                }

                                self.sse_messages.append(sse_msg)

                                # Display SSE message
                                msg_type = parsed_data.get(
                                    "message_type", parsed_data.get("type", "unknown")
                                )
                                message_text = parsed_data.get(
                                    "message", str(parsed_data)[:50]
                                )
                                print(
                                    f"🔵 SSE   [{datetime.now().strftime('%H:%M:%S')}] → {msg_type}: {message_text}"
                                )

                            except json.JSONDecodeError as e:
                                print(f"❌ Failed to parse SSE data: {e}")

        except Exception as e:
            print(f"❌ SSE monitoring error: {e}")

    async def generate_comparison_report(self):
        """Generate a comparison report between Redis and SSE messages"""
        print("\n" + "=" * 80)
        print("📊 REDIS vs SSE COMPARISON REPORT")
        print("=" * 80)

        print(f"📡 Redis Messages Received: {len(self.redis_messages)}")
        print(f"🔗 SSE Messages Received: {len(self.sse_messages)}")

        if self.redis_messages:
            print("\n🔴 REDIS MESSAGE TYPES:")
            redis_types = {}
            for msg in self.redis_messages:
                msg_type = msg["data"].get(
                    "message_type", msg["data"].get("type", "unknown")
                )
                redis_types[msg_type] = redis_types.get(msg_type, 0) + 1

            for msg_type, count in sorted(redis_types.items()):
                print(f"   {msg_type}: {count}")

        if self.sse_messages:
            print("\n🔵 SSE MESSAGE TYPES:")
            sse_types = {}
            for msg in self.sse_messages:
                msg_type = msg["data"].get(
                    "message_type", msg["data"].get("type", "unknown")
                )
                sse_types[msg_type] = sse_types.get(msg_type, 0) + 1

            for msg_type, count in sorted(sse_types.items()):
                print(f"   {msg_type}: {count}")

        # Find missing message types
        if self.redis_messages and self.sse_messages:
            redis_types_set = set(
                msg["data"].get("message_type", msg["data"].get("type", "unknown"))
                for msg in self.redis_messages
            )
            sse_types_set = set(
                msg["data"].get("message_type", msg["data"].get("type", "unknown"))
                for msg in self.sse_messages
            )

            missing_in_sse = redis_types_set - sse_types_set
            extra_in_sse = sse_types_set - redis_types_set

            print(f"\n❌ Message types in Redis but NOT in SSE: {missing_in_sse}")
            print(f"➕ Message types in SSE but NOT in Redis: {extra_in_sse}")

        print("\n💾 Saving detailed logs...")

        # Save detailed comparison
        report = {
            "analysis_time": datetime.now().isoformat(),
            "task_id": self.task_id,
            "redis_messages": self.redis_messages,
            "sse_messages": self.sse_messages,
            "summary": {
                "redis_count": len(self.redis_messages),
                "sse_count": len(self.sse_messages),
                "redis_channels_monitored": self.redis_channels,
            },
        }

        with open("redis_sse_diagnostic_report.json", "w") as f:
            json.dump(report, f, indent=2)

        print("✅ Report saved to: redis_sse_diagnostic_report.json")

    async def run_diagnostic(self):
        """Run the complete diagnostic"""
        print("🔍 Starting Redis-SSE Bridge Diagnostic")
        print(f"📋 Task ID: {self.task_id}")
        print(f"📡 Redis Channels: {self.redis_channels}")
        print("=" * 60)

        # Connect to Redis
        if not await self.connect_redis():
            print("❌ Cannot proceed without Redis connection")
            return

        # Start monitoring tasks
        redis_task = asyncio.create_task(self.monitor_redis_channels())
        sse_task = asyncio.create_task(self.monitor_sse_connection())

        try:
            # Wait for both monitoring tasks
            await asyncio.gather(redis_task, sse_task, return_exceptions=True)
        except KeyboardInterrupt:
            print("\n⏹️  Diagnostic interrupted by user")
        finally:
            self.is_running = False

            # Cancel tasks
            for task in [redis_task, sse_task]:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            # Generate report
            await self.generate_comparison_report()

            # Cleanup
            if self.redis_client:
                await self.redis_client.close()


def signal_handler(signum, frame):
    print("\n⏹️  Stopping diagnostic...")
    sys.exit(0)


async def main():
    if len(sys.argv) != 2:
        print("Usage: python redis_sse_diagnostic.py <task_id>")
        print("Example: python redis_sse_diagnostic.py cmfqqtk3w0001z9jjx2gkd3y1")
        sys.exit(1)

    task_id = sys.argv[1]

    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)

    diagnostic = RedisSSEDiagnostic(task_id)
    await diagnostic.run_diagnostic()


if __name__ == "__main__":
    asyncio.run(main())
