#!/usr/bin/env python3
"""
Test creating a new blog generation task to verify the fix works end-to-end
"""
import sys
sys.path.insert(0, '/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/src')

from dotenv import load_dotenv
load_dotenv('/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/.env')

import aiohttp
import asyncio
import json

async def create_new_blog():
    """Create a new blog generation task via the API"""
    print("🚀 Testing new blog generation with fixed backend...")
    
    # First get a JWT token
    async with aiohttp.ClientSession() as session:
        try:
            # Create blog generation request
            blog_data = {
                "topic": "The Future of AI in 2025",
                "instructions": "Write an informative blog post about AI trends and developments"
            }
            
            # Mock authentication by including user info
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer test-token"  # We'll need to handle auth properly
            }
            
            print(f"📝 Creating blog with topic: {blog_data['topic']}")
            print("💡 Note: This test will verify the API endpoint exists and responds")
            
            # Test the blog creation endpoint
            async with session.post(
                "https://localhost:5000/api/blogs/generate",
                json=blog_data,
                headers=headers,
                ssl=False  # Skip SSL verification for localhost
            ) as response:
                print(f"📊 Response status: {response.status}")
                if response.status == 200:
                    result = await response.json()
                    task_id = result.get('task_id')
                    print(f"✅ Blog generation started! Task ID: {task_id}")
                    print("🔗 Frontend can now connect to this task and see real-time progress")
                    return task_id
                else:
                    error_text = await response.text()
                    print(f"❌ Blog creation failed: {error_text}")
                    
        except Exception as e:
            print(f"❌ Error creating blog: {e}")
            print("💡 This is expected if authentication is required")
            
    return None

if __name__ == "__main__":
    asyncio.run(create_new_blog())
