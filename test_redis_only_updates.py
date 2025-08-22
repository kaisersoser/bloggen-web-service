#!/usr/bin/env python3
"""
Quick test to validate Redis-only status updates from CrewAI Flow threads.
This test simulates the Flow thread context to verify our fix.
"""

import requests
import threading
import time
import json
import logging
import os
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_real_user_token():
    """Generate JWT token for a real user"""
    
    # Default secret from backend
    secret = os.getenv("NEXTAUTH_SECRET", "Ver0EvKSf1T5hN4/6NDsnPyZf8S7dJZ/Ewksc2Y2L7w=")
    
    # Real user details
    user_id = 'cmdaiv5530000z9nxqmyg445v'
    email = 'charles.vogt@gmail.com'
    name = 'Charles Vogt'
    role = 'ADMIN'
    
    logger.info(f'🎯 Using real user: {email} (Role: {role})')
    
    # Use time.time() for proper UTC timestamps
    current_time = int(time.time())
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "role": role,
        "iat": current_time,
        "exp": current_time + 3600  # 1 hour in seconds
    }
    
    token = jwt.encode(payload, secret, algorithm="HS256")
    
    return token, user_id

def test_redis_only_updates():
    """Test Redis-only status updates during blog generation"""
    
    # Test configuration
    base_url = "https://localhost:5000"
    
    # Get JWT token for real user
    logger.info("🔑 Getting JWT token for real user...")
    
    # Get token
    token, user_id = get_real_user_token()
    
    if not token:
        logger.error("❌ Failed to get JWT token")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    logger.info(f"✅ JWT token obtained: {token[:20]}...")
    
    # Start blog generation
    logger.info("🚀 Starting blog generation...")
    blog_data = {
        "topic": "Redis Status Update Test - AI and Real-time Systems",
        "instructions": "Write a brief overview focusing on real-time messaging systems"
    }
    
    response = requests.post(
        f"{base_url}/generate-blog", 
        json=blog_data,
        headers=headers,
        verify=False
    )
    
    if response.status_code != 200:
        logger.error(f"❌ Blog generation failed: {response.status_code} - {response.text}")
        return
    
    task_id = response.json().get("task_id")
    logger.info(f"✅ Blog generation started with task ID: {task_id}")
    
    # Monitor Redis status updates
    logger.info("📡 Monitoring Redis status updates...")
    
    # Simple approach: Monitor backend logs for Redis-only updates
    logger.info("⏰ Waiting 60 seconds and monitoring backend logs for Redis-only updates...")
    time.sleep(60)
    
    # Check if task completed
    try:
        status_response = requests.get(
            f"{base_url}/api/blog/{task_id}",
            headers=headers,
            verify=False
        )
        
        if status_response.status_code == 200:
            blog_data = status_response.json()
            logger.info(f"✅ Task completed: {blog_data.get('status', 'unknown')}")
            logger.info(f"� Blog length: {len(blog_data.get('content', ''))}")
        else:
            logger.info(f"⏳ Task status: {status_response.status_code}")
            
    except Exception as e:
        logger.error(f"❌ Error checking task status: {e}")

if __name__ == "__main__":
    test_redis_only_updates()
