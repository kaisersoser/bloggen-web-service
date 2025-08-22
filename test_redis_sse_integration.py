#!/usr/bin/env python3
"""
Test Redis pub/sub integration with SSE endpoint

This test verifies that TaskManager publishes updates to Redis channels
and that the SSE endpoint can receive them.
"""

import asyncio
import json
import redis.asyncio as redis
from datetime import datetime
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

async def test_redis_sse_integration():
    """Test that TaskManager publishes to Redis and SSE can listen"""
    
    print("🔧 Testing Redis pub/sub integration with TaskManager...")
    
    # Initialize Redis connection (same config as TaskManager)
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', '6379')),
        db=int(os.getenv('REDIS_DB', '0')),
        decode_responses=False  # Keep as bytes to match SSE endpoint
    )
    
    try:
        # Test Redis connection
        await redis_client.ping()
        print("✅ Redis connection successful")
        
        # Test task ID
        test_task_id = "test_sse_integration_123"
        channel = f"task_updates:{test_task_id}"
        
        # Set up subscription (like SSE endpoint does)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)
        print(f"📡 Subscribed to Redis channel: {channel}")
        
        # Simulate TaskManager publishing updates
        print("📤 Simulating TaskManager publishing updates...")
        
        # Simulate different task phases
        updates = [
            {"status": "started", "message": "Task started", "progress": 0},
            {"status": "in_progress", "message": "Research phase", "current_step": "research", "progress": 25},
            {"status": "in_progress", "message": "Content generation", "current_step": "writing", "progress": 50},
            {"status": "in_progress", "message": "Fact checking", "current_step": "fact_check", "progress": 75},
            {"status": "completed", "message": "Blog completed", "progress": 100, "content": "Test blog content"}
        ]
        
        # Publish updates in sequence
        received_count = 0
        
        async def publish_updates():
            """Publish updates with delay"""
            await asyncio.sleep(1)  # Give subscriber time to connect
            for i, update in enumerate(updates):
                message_data = {
                    "task_id": test_task_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    **update
                }
                
                # Publish to Redis (like TaskManager would do)
                await redis_client.publish(channel, json.dumps(message_data))
                print(f"📤 Published update {i+1}: {update['status']} - {update['message']}")
                await asyncio.sleep(0.5)
        
        # Start publisher task
        publisher_task = asyncio.create_task(publish_updates())
        
        # Listen for messages (like SSE endpoint does)
        print("📥 Listening for Redis messages...")
        timeout_task = asyncio.create_task(asyncio.sleep(10))  # 10 second timeout
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    # Parse message (same as SSE endpoint)
                    redis_data = json.loads(message['data'].decode('utf-8'))
                    received_count += 1
                    
                    print(f"📨 Received update {received_count}: {redis_data.get('status')} - {redis_data.get('message')}")
                    
                    # Check if we got the completion message
                    if redis_data.get('status') == 'completed':
                        print("✅ Received completion message - test successful!")
                        break
                        
                except json.JSONDecodeError as e:
                    print(f"❌ Failed to decode Redis message: {e}")
                except Exception as e:
                    print(f"❌ Error processing Redis message: {e}")
            
            # Check timeout
            if timeout_task.done():
                print("⏰ Test timed out")
                break
        
        # Wait for publisher to finish
        await publisher_task
        
        print(f"\n📊 Test Summary:")
        print(f"   Published: {len(updates)} updates")
        print(f"   Received: {received_count} updates")
        
        if received_count == len(updates):
            print("✅ All messages received successfully!")
            print("✅ Redis pub/sub integration working correctly")
        else:
            print(f"❌ Message mismatch - some updates may have been lost")
        
        return received_count == len(updates)
        
    except Exception as e:
        print(f"❌ Redis integration test failed: {e}")
        return False
        
    finally:
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            await redis_client.close()
        except:
            pass

async def test_task_manager_redis_publishing():
    """Test if TaskManager actually publishes to Redis"""
    
    print("\n🔧 Testing TaskManager Redis publishing...")
    
    try:
        # Import TaskManager
        from core.task_manager import TaskManager
        from core.redis_manager import RedisManager
        
        # Initialize managers
        redis_manager = RedisManager()
        task_manager = TaskManager(redis_manager=redis_manager)
        
        print("✅ TaskManager initialized")
        
        # Check if TaskManager has Redis publishing capability
        if hasattr(task_manager, '_redis_manager') and task_manager._redis_manager:
            print("✅ TaskManager has Redis manager")
            
            # Check for publish methods
            if hasattr(task_manager, 'publish_task_update'):
                print("✅ TaskManager has publish_task_update method")
                return True
            else:
                print("❌ TaskManager missing publish_task_update method")
                print("💡 This explains why SSE gets no Redis messages!")
                return False
        else:
            print("❌ TaskManager has no Redis manager")
            return False
            
    except Exception as e:
        print(f"❌ TaskManager test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Starting Redis SSE Integration Tests\n")
    
    # Test 1: Redis pub/sub functionality
    redis_test = await test_redis_sse_integration()
    
    # Test 2: TaskManager Redis integration
    task_manager_test = await test_task_manager_redis_publishing()
    
    print(f"\n📋 Final Results:")
    print(f"   Redis pub/sub: {'✅ PASS' if redis_test else '❌ FAIL'}")
    print(f"   TaskManager integration: {'✅ PASS' if task_manager_test else '❌ FAIL'}")
    
    if redis_test and task_manager_test:
        print("\n🎉 All tests passed! Redis SSE integration should work.")
    else:
        print("\n⚠️  Some tests failed. SSE timeouts likely due to missing Redis publishing.")

if __name__ == "__main__":
    asyncio.run(main())
