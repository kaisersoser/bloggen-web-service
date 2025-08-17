#!/usr/bin/env python3
"""
Test WebSocket completion notifications for blog generation.

This script will test whether the WebSocket connection properly receives
completion notifications when a blog generation task finishes.
"""

import asyncio
import websockets
import json
import sys
import logging
import requests
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class WebSocketTester:
    def __init__(self, backend_url: str = "http://localhost:5000"):
        self.backend_url = backend_url
        self.ws_url = backend_url.replace("http://", "ws://").replace("https://", "wss://")
        self.jwt_token: Optional[str] = None
        
    def get_jwt_token(self) -> str:
        """Get a JWT token for authentication."""
        # Use the same JWT generation as the frontend
        import jwt
        import time
        
        payload = {
            'sub': 'cmdaiv5530000z9nxqmyg445v',  # Test user ID
            'email': 'test@example.com',
            'name': 'Test User',
            'role': 'PREMIUM',
            'iat': int(time.time()),
            'exp': int(time.time()) + 3600  # 1 hour
        }
        
        # Use the same secret as NextAuth
        secret = "Ver0EvKSf1T5hN4/6NDsnPyZf8S7dJZ/Ewksc2Y2L7w="
        token = jwt.encode(payload, secret, algorithm='HS256')
        logger.info(f"Generated JWT token: {token[:50]}...")
        return token
    
    async def test_task_completion_websocket(self, task_id: str):
        """Test WebSocket connection for a specific task."""
        self.jwt_token = self.get_jwt_token()
        ws_endpoint = f"{self.ws_url}/ws/{task_id}?token={self.jwt_token}"
        
        logger.info(f"Connecting to WebSocket: {ws_endpoint}")
        
        try:
            async with websockets.connect(ws_endpoint) as websocket:
                logger.info("✅ WebSocket connected successfully")
                
                # Send ping to test connection
                ping_message = json.dumps({"type": "ping"})
                await websocket.send(ping_message)
                logger.info("📤 Sent ping message")
                
                # Listen for messages
                message_count = 0
                max_messages = 50  # Limit to prevent infinite loop
                
                async for message in websocket:
                    message_count += 1
                    if message_count > max_messages:
                        logger.warning(f"⚠️ Reached maximum message limit ({max_messages})")
                        break
                        
                    try:
                        data = json.loads(message)
                        msg_type = data.get('type', 'unknown')
                        task_data = data.get('data', {})
                        
                        logger.info(f"📥 Received message #{message_count}: {msg_type}")
                        
                        if msg_type == 'task_update':
                            status = task_data.get('status', 'unknown')
                            step = task_data.get('step', 'unknown')
                            progress = task_data.get('progress', 0)
                            
                            logger.info(f"   📊 Task Update: {status} | {step} | {progress}%")
                            
                            if status == 'completed':
                                content = task_data.get('content', '')
                                hero_url = task_data.get('hero_image_url', '')
                                logger.info(f"   ✅ TASK COMPLETED!")
                                logger.info(f"   📄 Content length: {len(content)} characters")
                                logger.info(f"   🖼️ Hero image: {hero_url}")
                                break
                            elif status == 'failed':
                                error = task_data.get('error', 'Unknown error')
                                logger.error(f"   ❌ TASK FAILED: {error}")
                                break
                        elif msg_type == 'pong':
                            logger.info("   🏓 Pong received - connection alive")
                        else:
                            logger.info(f"   ℹ️ Other message: {data}")
                            
                    except json.JSONDecodeError:
                        logger.error(f"❌ Failed to parse message: {message}")
                        
        except Exception as e:
            logger.error(f"❌ WebSocket connection failed: {e}")
            return False
            
        return True
    
    def start_blog_generation(self, topic: str = "Test WebSocket Blog Generation") -> Optional[str]:
        """Start a blog generation task and return the task ID."""
        try:
            headers = {
                'Authorization': f'Bearer {self.jwt_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'topic': topic,
                'instructions': 'Generate a short test blog post to verify WebSocket completion notifications work properly.'
            }
            
            logger.info(f"🚀 Starting blog generation: {topic}")
            response = requests.post(f"{self.backend_url}/generate-blog", 
                                   json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                task_id = data.get('task_id')
                logger.info(f"✅ Blog generation started. Task ID: {task_id}")
                return task_id
            else:
                logger.error(f"❌ Failed to start blog generation: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error starting blog generation: {e}")
            return None

async def main():
    """Main test function."""
    logger.info("🔍 Starting WebSocket completion notification test")
    
    tester = WebSocketTester()
    
    # Start blog generation
    task_id = tester.start_blog_generation("WebSocket Test Blog")
    if not task_id:
        logger.error("❌ Could not start blog generation")
        sys.exit(1)
    
    # Test WebSocket connection
    logger.info(f"🔌 Testing WebSocket connection for task: {task_id}")
    success = await tester.test_task_completion_websocket(task_id)
    
    if success:
        logger.info("✅ WebSocket test completed successfully")
    else:
        logger.error("❌ WebSocket test failed")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        sys.exit(1)
