#!/usr/bin/env python3
"""
Debug script to test message buffering system step by step.
This will help identify where the early message buffering is failing.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.redis_manager import RedisManager
from core.message_buffer import RedisMessageBuffer


async def test_message_buffering():
    """Test the complete message buffering flow"""
    print("🧪 Testing Message Buffering System")
    print("=" * 50)
    
    # Initialize Redis components
    redis_manager = RedisManager()
    await redis_manager.connect()
    
    message_buffer = RedisMessageBuffer(redis_manager)
    
    test_task_id = f"test_task_{int(time.time())}"
    print(f"📋 Test Task ID: {test_task_id}")
    
    try:
        # Step 1: Start buffering (simulates /generate-task-id)
        print("\n1️⃣ Starting message buffering...")
        await message_buffer.start_buffering(test_task_id)
        
        buffer_active = await message_buffer.is_buffering(test_task_id)
        print(f"   ✅ Buffer active: {buffer_active}")
        
        # Step 2: Send some early messages (simulates early CrewAI flow messages)
        print("\n2️⃣ Sending early messages to buffer...")
        
        early_messages = [
            {
                "message_type": "taskcreated",
                "task_id": test_task_id,
                "message": "Blog generation task created",
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "message_type": "initializing", 
                "task_id": test_task_id,
                "message": "Initializing AI blog generation workflow...",
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "message_type": "agentthinking",
                "task_id": test_task_id,
                "agent_name": "Senior Researcher",
                "thought": "Initiating research strategy...",
                "message": "Processing...",
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
        
        for msg in early_messages:
            buffered = await message_buffer.buffer_message(
                test_task_id, 
                f"task_updates:{test_task_id}", 
                msg
            )
            print(f"   📦 Buffered {msg['message_type']}: {buffered}")
        
        # Step 3: Check buffer contents
        print("\n3️⃣ Checking buffer contents...")
        buffer_stats = await message_buffer.get_buffer_stats(test_task_id)
        if buffer_stats:
            print(f"   📊 Buffer stats: {buffer_stats}")
        else:
            print("   ❌ No buffer stats available")
        
        # Step 4: Simulate SSE connection and flush buffer
        print("\n4️⃣ Simulating SSE connection and buffer flush...")
        flushed_messages = await message_buffer.flush_buffered_messages(test_task_id)
        
        print(f"   📤 Flushed {len(flushed_messages)} messages:")
        for i, msg in enumerate(flushed_messages, 1):
            print(f"      {i}. {msg.message_type}: {msg.message_data.get('message', 'N/A')}")
        
        # Step 5: Verify buffer is cleaned up
        print("\n5️⃣ Verifying buffer cleanup...")
        buffer_active_after = await message_buffer.is_buffering(test_task_id)
        print(f"   🧹 Buffer active after flush: {buffer_active_after}")
        
        print("\n✅ Message buffering test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await redis_manager.disconnect()


async def test_sync_redis_buffering():
    """Test the sync Redis buffering used by update_task_redis_only"""
    print("\n🔧 Testing Sync Redis Buffering")
    print("=" * 50)
    
    import redis
    
    test_task_id = f"sync_test_task_{int(time.time())}"
    print(f"📋 Test Task ID: {test_task_id}")
    
    try:
        # Create sync Redis connection (same as in update_task_redis_only)
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        sync_redis = redis.from_url(redis_url, decode_responses=True)
        
        # Step 1: Create a buffer manually (simulates message_buffer.start_buffering)
        buffer_key = f"message_buffer:{test_task_id}"
        buffer_data = {
            "task_id": test_task_id,
            "created_at": datetime.utcnow().isoformat(),
            "messages": []
        }
        sync_redis.setex(buffer_key, 1800, json.dumps(buffer_data))
        print(f"   📦 Created buffer: {buffer_key}")
        
        # Step 2: Test buffer check (simulates update_task_redis_only logic)
        buffer_active = sync_redis.exists(buffer_key)
        print(f"   ✅ Buffer exists check: {buffer_active}")
        
        # Step 3: Simulate adding a message to buffer (sync version)
        if buffer_active:
            from core.message_buffer import BufferedMessage
            
            test_message = {
                'message_type': 'agentthinking',
                'task_id': test_task_id,
                'agent_name': 'Test Agent',
                'thought': 'Test thought',
                'message': 'Processing...',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            buffered_msg = BufferedMessage(
                task_id=test_task_id,
                message_data=test_message,
                channel=f"task_updates:{test_task_id}",
                timestamp=datetime.utcnow().isoformat(),
                message_type='agentthinking'
            )
            
            # Add to buffer (simulates update_task_redis_only logic)
            existing_data_raw = sync_redis.get(buffer_key)
            if existing_data_raw:
                buffer_data = json.loads(str(existing_data_raw))
            else:
                buffer_data = {"messages": []}
            
            buffer_data["messages"].append(buffered_msg.to_dict())
            sync_redis.setex(buffer_key, 1800, json.dumps(buffer_data))
            
            print(f"   📦 Added message to buffer via sync Redis")
            
            # Verify the message was added
            updated_data_raw = sync_redis.get(buffer_key)
            if updated_data_raw:
                updated_data = json.loads(str(updated_data_raw))
                message_count = len(updated_data.get('messages', []))
                print(f"   ✅ Buffer now contains {message_count} messages")
        
        # Cleanup
        sync_redis.delete(buffer_key)
        print(f"   🧹 Cleaned up test buffer")
        
        print("\n✅ Sync Redis buffering test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Sync test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    async def main():
        await test_message_buffering()
        await test_sync_redis_buffering()
    
    asyncio.run(main())