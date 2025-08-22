#!/usr/bin/env python3
"""
Debug SSE issue by testing task retrieval and send_update function
"""
import asyncio
import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.append('src')

async def debug_sse_issue():
    """Debug the SSE stream issue step by step"""
    
    # Import task manager
    from core.task_manager import task_manager
    
    # Test task ID from frontend logs
    task_id = 'cmeiy24aw0003z9oxx5rmfpdj'
    
    print(f"🔍 Debugging SSE issue for task: {task_id}")
    
    try:
        # Step 1: Try to get the task
        print("📋 Step 1: Retrieving task from database...")
        task = await task_manager.get_task(task_id)
        
        if not task:
            print("❌ Task not found in database")
            return False
        
        print(f"✅ Task found: {task}")
        print(f"   - Status: {task.get('status')}")
        print(f"   - Current step: {task.get('current_step')}")
        print(f"   - Progress: {task.get('progress')}")
        print(f"   - User ID: {task.get('user_id')}")
        
        # Step 2: Test the send_update function logic
        print("\n📤 Step 2: Testing send_update function logic...")
        
        def test_send_update(task_data):
            """Replicate the send_update function from SSE stream"""
            try:
                status = task_data.get('status', '').lower()
                step = task_data.get('current_step')
                progress = task_data.get('progress', 0)
                hero_url = task_data.get('hero_image_url')
                
                print(f"   - Extracted status: '{status}'")
                print(f"   - Extracted step: '{step}'")
                print(f"   - Extracted progress: {progress}")
                print(f"   - Extracted hero_url: {hero_url}")
                
                # Test message creation logic
                if status == 'completed':
                    print("   - Would create completed message")
                elif status == 'failed':
                    print("   - Would create error message")
                else:
                    print("   - Would create status message")
                
                # Create a test message
                message = {
                    "message_type": "status",
                    "task_id": task_id,
                    "status": status,
                    "message": task_data.get('message', f"Status: {status}"),
                    "step": step,
                    "progress": progress
                }
                
                print(f"   - Test message: {json.dumps(message, indent=2)}")
                return True
                
            except Exception as e:
                print(f"❌ Error in send_update: {e}")
                return False
        
        success = test_send_update(task)
        if not success:
            return False
        
        # Step 3: Test Redis connection
        print("\n📡 Step 3: Testing Redis connection...")
        
        try:
            import redis
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            sync_redis = redis.from_url(redis_url, decode_responses=True)
            
            # Test Redis connection
            sync_redis.ping()
            print("✅ Redis connection successful")
            
            # Test publishing
            test_message = {
                'message_type': 'test',
                'task_id': task_id,
                'status': 'test',
                'message': 'Test message',
                'progress': 0,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            task_channel = f"task_updates:{task_id}"
            result = sync_redis.publish(task_channel, json.dumps(test_message))
            print(f"✅ Redis publish test successful (subscribers: {result})")
            
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            return False
        
        print("\n✅ All debug steps completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Debug failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_sse_issue())
    if success:
        print("\n🎉 Debug completed - no obvious issues found")
        print("💡 The SSE timeout might be due to frontend connection handling")
    else:
        print("\n💥 Debug revealed issues that need to be fixed")
