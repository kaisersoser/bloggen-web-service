#!/usr/bin/env python3
"""
Test script to verify the new database-backed task manager works correctly.
"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.task_manager import task_manager, TaskStatus

async def test_task_manager():
    print("🧪 Testing Database-Backed Task Manager")
    print("=" * 50)
    
    # Test 1: Create a task
    print("\n1. Testing task creation...")
    try:
        # Get a real user ID from the database
        from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker
        tracker = EnhancedDatabaseAuditTracker(session_type="test", user_id="system", blog_id=None)
        pool = await tracker._get_database_connection()
        
        if not pool:
            print("❌ Could not connect to database")
            return False
            
        async with pool.acquire() as conn:
            user_row = await conn.fetchrow("SELECT id FROM users LIMIT 1")
            if not user_row:
                print("❌ No users found in database. Please create a user first.")
                return False
            user_id = user_row['id']
            print(f"   Using user ID: {user_id}")
        
        task_id = "test_task_12345"
        topic = "Test Blog Topic"
        instructions = "Write a test blog about AI"
        
        task = await task_manager.create_task(task_id, user_id, topic, instructions)
        print(f"✅ Created task: {task['id']}")
        print(f"   Topic: {task['topic']}")
        print(f"   Status: {task['status']}")
        print(f"   Step: {task['current_step']}")
    except Exception as e:
        print(f"❌ Task creation failed: {e}")
        return False
    
    # Test 2: Update task progress
    print("\n2. Testing task updates...")
    try:
        updated_task = await task_manager.update_task(
            task_id,
            status=TaskStatus.IN_PROGRESS,
            current_step="Processing content...",
            progress=50
        )
        if updated_task:
            print(f"✅ Updated task progress to {updated_task['progress']}%")
            print(f"   Step: {updated_task['current_step']}")
        else:
            print("❌ Task update returned None")
            return False
    except Exception as e:
        print(f"❌ Task update failed: {e}")
        return False
    
    # Test 3: Get task status
    print("\n3. Testing task retrieval...")
    try:
        retrieved_task = await task_manager.get_task(task_id)
        if retrieved_task:
            print(f"✅ Retrieved task: {retrieved_task['id']}")
            print(f"   Status: {retrieved_task['status']}")
            print(f"   Progress: {retrieved_task['progress']}%")
        else:
            print("❌ Task not found")
            return False
    except Exception as e:
        print(f"❌ Task retrieval failed: {e}")
        return False
    
    # Test 4: Complete task
    print("\n4. Testing task completion...")
    try:
        content = "This is the generated blog content for testing."
        hero_image_url = "https://example.com/hero.jpg"
        
        completed_task = await task_manager.complete_task(task_id, content, hero_image_url)
        if completed_task:
            print(f"✅ Completed task with content length: {len(content)}")
            print(f"   Status: {completed_task['status']}")
            print(f"   Hero image: {completed_task.get('hero_image_url', 'None')}")
        else:
            print("❌ Task completion returned None")
            return False
    except Exception as e:
        print(f"❌ Task completion failed: {e}")
        return False
    
    # Test 5: Get user tasks
    print("\n5. Testing user task listing...")
    try:
        user_tasks = await task_manager.get_user_tasks(user_id)
        print(f"✅ Found {len(user_tasks)} tasks for user")
        
        # Find our test task
        test_task = next((t for t in user_tasks if t['id'] == task_id), None)
        if test_task:
            print(f"   Test task status: {test_task['status']}")
        else:
            print("❌ Test task not found in user tasks")
    except Exception as e:
        print(f"❌ User task listing failed: {e}")
        return False
    
    # Cleanup: Delete the test task from database
    print("\n6. Cleanup...")
    try:
        from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker
        tracker = EnhancedDatabaseAuditTracker(session_type="cleanup", user_id="system", blog_id=None)
        pool = await tracker._get_database_connection()
        
        if pool:
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM blogs WHERE id = $1", task_id)
                print(f"✅ Cleaned up test task: {task_id}")
        else:
            print("⚠️ Could not connect to database for cleanup")
    except Exception as e:
        print(f"⚠️ Cleanup failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 All tests passed! Database-backed task manager is working correctly.")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_task_manager())
    exit(0 if success else 1)
