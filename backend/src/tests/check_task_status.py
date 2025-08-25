#!/usr/bin/env python3
"""
Check current task statuses in database
"""
import sys
sys.path.insert(0, '/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/src')

from dotenv import load_dotenv
load_dotenv('/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/.env')

from core.task_manager import task_manager
import asyncio

async def check_tasks():
    print("🔍 Checking task statuses in database...")
    
    # Check for recent tasks
    try:
        # Get task details for the failing task ID
        task_id = "cmed5em230001z97exvila4wc"
        print(f"\n📋 Checking task: {task_id}")
        
        # Check if task exists and get its details
        task_details = await task_manager.get_task(task_id)
        if task_details:
            print(f"   Status: {task_details.get('status')}")
            print(f"   Created: {task_details.get('created_at')}")
            print(f"   User: {task_details.get('user_id')}")
            print(f"   Topic: {task_details.get('topic')}")
            print(f"   Current Step: {task_details.get('current_step', 'Unknown')}")
            print(f"   Progress: {task_details.get('progress', 0)}%")
            if task_details.get('error_message'):
                print(f"   Error: {task_details.get('error_message')}")
        else:
            print("   ❌ Task not found in database")
            
    except Exception as e:
        print(f"❌ Error checking task: {e}")

if __name__ == "__main__":
    asyncio.run(check_tasks())
