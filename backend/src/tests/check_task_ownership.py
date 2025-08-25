#!/usr/bin/env python3
"""
Check task ownership for debugging WebSocket access
"""

import asyncio
import os
import sys
sys.path.append('/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/src')

from core.task_manager import TaskManager

async def check_task_ownership():
    """Check who owns the test task"""
    
    task_id = "cmed5pkor0003z97eool3e7n3"
    
    # Initialize task manager
    task_manager = TaskManager()
    
    try:
        task = await task_manager.get_task(task_id)
        if task:
            print(f"✅ Task {task_id} found:")
            print(f"   User ID: {task.get('user_id')}")
            print(f"   Status: {task.get('status')}")
            print(f"   Created: {task.get('created_at')}")
            print(f"   Title: {task.get('title', 'N/A')}")
        else:
            print(f"❌ Task {task_id} not found")
            
    except Exception as e:
        print(f"❌ Error checking task: {e}")

if __name__ == "__main__":
    asyncio.run(check_task_ownership())
