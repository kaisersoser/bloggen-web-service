#!/usr/bin/env python3
# flake8: noqa
"""
Diagnostic test to see what's happening inside the Blog Generation Flow
and why we're not getting detailed status updates
"""

import asyncio
import ssl
import aiohttp
import json
import time
from datetime import datetime


async def test_detailed_flow_execution():
    """Test blog generation and capture all status updates"""

    print("🔧 Testing detailed flow execution with status monitoring...")

    # Load JWT token
    try:
        with open("valid_jwt_token.txt", "r") as f:
            jwt_token = f.read().strip()
        print("✅ Valid JWT token loaded")
    except FileNotFoundError:
        print("❌ No valid JWT token found")
        return False

    # SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    connector = aiohttp.TCPConnector(ssl=ssl_context)

    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            # Create blog task
            start_time = time.time()
            print(
                f"📝 Creating blog generation task at {datetime.now().strftime('%H:%M:%S')}"
            )

            async with session.post(
                "https://localhost:5000/generate-blog",
                json={
                    "topic": "Advanced Machine Learning Techniques in 2025",
                    "instructions": "Write a comprehensive technical deep dive with research",
                },
                headers={"Authorization": f"Bearer {jwt_token}"},
            ) as response:
                if response.status != 200:
                    print(f"❌ Failed to create blog task: {response.status}")
                    return False

                task_data = await response.json()
                task_id = task_data.get("task_id")
                print(f"✅ Blog task created: {task_id}")

                # Start SSE monitoring
                print(f"📡 Starting SSE monitoring for {task_id}")

                sse_url = f"https://localhost:5000/stream/{task_id}?token={jwt_token}"

                message_count = 0
                message_types = {}

                timeout = aiohttp.ClientTimeout(total=120)  # 2 minute timeout
                async with session.get(sse_url, timeout=timeout) as sse_response:
                    if sse_response.status != 200:
                        print(f"❌ SSE connection failed: {sse_response.status}")
                        return False

                    print("📨 SSE connection established, monitoring messages...")

                    async for line in sse_response.content:
                        line_str = line.decode("utf-8").strip()

                        if line_str.startswith("data: "):
                            message_count += 1
                            elapsed = time.time() - start_time

                            data = line_str[6:]  # Remove 'data: ' prefix
                            try:
                                msg = json.loads(data)
                                msg_type = msg.get("type", "unknown")
                                message_types[msg_type] = (
                                    message_types.get(msg_type, 0) + 1
                                )

                                # Extract key information
                                status = msg.get("status", "N/A")
                                phase = msg.get("phase", "N/A")
                                progress = msg.get("progress", "N/A")
                                message = msg.get("message", "N/A")

                                print(
                                    f"📨 [{elapsed:.1f}s] Message {message_count}: {msg_type}"
                                )
                                print(
                                    f"    Status: {status}, Phase: {phase}, Progress: {progress}"
                                )
                                print(f"    Message: {message[:80]}...")

                                # Check for agent thinking or tool usage
                                if "agent_name" in msg:
                                    print(f"    🧠 Agent: {msg.get('agent_name')}")
                                if "tool_name" in msg:
                                    print(f"    🔧 Tool: {msg.get('tool_name')}")

                                print()

                                # Stop on completion or error
                                if msg_type in ["completed", "error", "timeout"]:
                                    break

                            except json.JSONDecodeError as e:
                                print(
                                    f"❌ Invalid JSON in message {message_count}: {e}"
                                )
                                print(f"    Raw data: {data[:100]}...")

                total_time = time.time() - start_time

                print(f"\n📊 Flow Execution Summary:")
                print(f"   Total time: {total_time:.1f} seconds")
                print(f"   Total messages: {message_count}")
                print(f"   Message types: {message_types}")

                # Analysis
                if message_count <= 3:
                    print(
                        f"\n🔍 Analysis: Only {message_count} messages - Flow likely bypassing detailed phases"
                    )
                    print(
                        "   Expected messages: connected, agent_thinking, tool_usage, research_finding, content_stream, completed"
                    )
                    print("   Possible causes:")
                    print("   - CrewAI Flow using cached/simplified execution")
                    print("   - Rate limiting forcing direct execution")
                    print("   - Flow phases not properly triggering status callbacks")
                else:
                    print(
                        f"\n✅ Analysis: {message_count} messages indicates detailed workflow execution"
                    )

                return message_count > 3

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    print("🚀 Detailed Flow Execution Diagnostic\n")

    success = await test_detailed_flow_execution()

    print(f"\n📋 Final Analysis:")
    if success:
        print("✅ Flow is executing detailed workflow phases")
    else:
        print(
            "❌ Flow is bypassing detailed phases - need to investigate CrewAI execution"
        )
        print("🔧 Possible fixes:")
        print("   1. Check if CrewAI Flow is using cached results")
        print("   2. Verify status callbacks are properly wired")
        print("   3. Check if rate limiting is forcing simplified execution")


if __name__ == "__main__":
    asyncio.run(main())
