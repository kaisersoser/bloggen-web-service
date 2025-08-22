#!/usr/bin/env python3
"""
Redis Pub/Sub Test for Task Updates

This test checks if Redis pub/sub is working correctly for task updates.
"""

import asyncio
import json
import redis.asyncio as aioredis
from datetime import datetime

async def test_redis_pubsub():
    """Test Redis pub/sub functionality"""
    print("🔍 Testing Redis Pub/Sub for Task Updates")
    print("=" * 50)
    
    try:
        # Connect to Redis
        redis_client = aioredis.from_url("redis://localhost:6379")
        
        # Test basic connection
        pong = await redis_client.ping()
        print(f"✅ Redis connection: {pong}")
        
        # Subscribe to task updates
        pubsub = redis_client.pubsub()
        test_task_id = "test-task-123"
        channel = f"task_updates:{test_task_id}"
        
        print(f"📡 Subscribing to channel: {channel}")
        await pubsub.subscribe(channel)
        
        # Simulate publishing a task update
        test_message = {
            "task_id": test_task_id,
            "user_id": "test-user",
            "phase": "research",
            "progress": 25.0,
            "details": "Testing Redis pub/sub",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "in_progress"
        }
        
        print(f"📤 Publishing test message...")
        await redis_client.publish(channel, json.dumps(test_message))
        
        # Listen for the message
        print(f"👂 Listening for messages (5s timeout)...")
        
        try:
            message_received = False
            async with asyncio.timeout(5):  # 5 second timeout
                async for message in pubsub.listen():
                    if message['type'] == 'message':
                        print(f"📨 Received message: {message['data'].decode()}")
                        message_received = True
                        break
                        
            if not message_received:
                print("❌ No message received within timeout")
                
        except asyncio.TimeoutError:
            print("⏰ Listening timeout - no messages received")
            
        # Clean up
        await pubsub.unsubscribe(channel)
        await redis_client.close()
        
        return message_received
        
    except Exception as e:
        print(f"❌ Redis test error: {e}")
        return False

async def check_existing_redis_channels():
    """Check what Redis channels currently exist"""
    try:
        redis_client = aioredis.from_url("redis://localhost:6379")
        
        # Get all keys matching task update patterns
        task_keys = await redis_client.keys("task_updates:*")
        user_keys = await redis_client.keys("user_updates:*") 
        
        print(f"\n📋 Existing Redis Channels:")
        print(f"   Task update channels: {len(task_keys)}")
        print(f"   User update channels: {len(user_keys)}")
        
        if task_keys:
            print(f"   Recent task channels: {[k.decode() for k in task_keys[:5]]}")
            
        await redis_client.close()
        
    except Exception as e:
        print(f"❌ Error checking Redis channels: {e}")

async def main():
    print("🚀 Redis Pub/Sub Diagnostic Test")
    print("📅 " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    try:
        # Check existing channels
        await check_existing_redis_channels()
        
        # Test pub/sub functionality
        pubsub_works = await test_redis_pubsub()
        
        print("\n" + "=" * 50)
        if pubsub_works:
            print("🎉 Redis Pub/Sub is working correctly!")
            print("\n💡 This means the SSE timeout issue is likely caused by:")
            print("   • SSE endpoint not listening to Redis messages properly")
            print("   • Task updates not being published to Redis channels")
            print("   • Database polling delays in SSE endpoint")
        else:
            print("❌ Redis Pub/Sub test failed")
            print("\n💡 This indicates:")
            print("   • Redis connection issues")
            print("   • Pub/sub configuration problems") 
            print("   • Need to check Redis server status")
            
    except Exception as e:
        print(f"\n💥 Test error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
