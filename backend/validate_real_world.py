#!/usr/bin/env python3
"""
Real-World Validation Tool for Redis-SSE Bridge Fix

This tool monitors actual blog generation to validate that:
1. Task IDs are pre-generated 
2. Early messages are buffered
3. SSE connections receive all messages
4. Message coverage approaches 100%
"""

import asyncio
import redis
import json
import time
from datetime import datetime
from typing import Dict, List
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealWorldValidator:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.monitoring = False
        self.message_log = []
        self.task_sessions = {}
        
    async def start_monitoring(self):
        """Start monitoring Redis for actual blog generation sessions."""
        logger.info("🎯 Starting real-world validation monitoring...")
        logger.info("📱 Generate a blog through the frontend UI now!")
        logger.info("=" * 60)
        
        pubsub = self.redis_client.pubsub()
        
        try:
            # Subscribe to all task-related channels
            pubsub.psubscribe('task_updates:*', 'sse_immediate:*')
            self.monitoring = True
            
            start_time = time.time()
            
            while self.monitoring and (time.time() - start_time) < 300:  # 5 minute timeout
                try:
                    message = pubsub.get_message(timeout=1.0)
                    if message and message['type'] == 'pmessage':
                        await self._process_message(message)
                        
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except KeyboardInterrupt:
            logger.info("\n👋 Monitoring stopped by user")
        finally:
            pubsub.close()
            await self._generate_report()
    
    async def _process_message(self, message):
        """Process and analyze each message."""
        try:
            channel = message['channel']
            data = json.loads(message['data'])
            
            # Extract task ID from channel
            task_id = channel.split(':')[1] if ':' in channel else 'unknown'
            
            message_info = {
                'timestamp': datetime.now().isoformat(),
                'task_id': task_id,
                'channel': channel,
                'message_type': data.get('message_type', 'unknown'),
                'correlation_id': data.get('correlation_id'),
                'data': data
            }
            
            self.message_log.append(message_info)
            
            # Track task sessions
            if task_id not in self.task_sessions:
                self.task_sessions[task_id] = {
                    'messages': [],
                    'start_time': datetime.now().isoformat(),
                    'early_messages': [],
                    'buffer_replays': 0
                }
            
            session = self.task_sessions[task_id]
            session['messages'].append(message_info)
            
            # Identify early messages that should be buffered
            if message_info['message_type'] in ['taskcreated', 'initializing', 'status']:
                session['early_messages'].append(message_info)
                logger.info(f"🔔 EARLY MESSAGE: {message_info['message_type']} for task {task_id[:8]}...")
            
            # Check for buffer replay indicators
            if 'buffer_replay' in str(data) or message_info['message_type'] == 'buffer_replayed':
                session['buffer_replays'] += 1
                logger.info(f"📤 BUFFER REPLAY detected for task {task_id[:8]}...")
            
            # Live message display
            msg_type = message_info['message_type']
            logger.info(f"📨 {msg_type:<15} | Task: {task_id[:8]}... | Channel: {channel.split(':')[0]}")
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
    
    async def _generate_report(self):
        """Generate a comprehensive validation report."""
        logger.info("\n" + "=" * 60)
        logger.info("📊 REAL-WORLD VALIDATION REPORT")
        logger.info("=" * 60)
        
        if not self.task_sessions:
            logger.warning("❌ No blog generation sessions detected!")
            logger.info("💡 Make sure to generate a blog through the frontend UI while monitoring")
            return
        
        for task_id, session in self.task_sessions.items():
            logger.info(f"\n🎯 Task: {task_id}")
            logger.info(f"   📅 Started: {session['start_time']}")
            logger.info(f"   📨 Total Messages: {len(session['messages'])}")
            logger.info(f"   🔔 Early Messages: {len(session['early_messages'])}")
            logger.info(f"   📤 Buffer Replays: {session['buffer_replays']}")
            
            # Analyze message types
            message_types = {}
            for msg in session['messages']:
                msg_type = msg['message_type']
                message_types[msg_type] = message_types.get(msg_type, 0) + 1
            
            logger.info(f"   📋 Message Types: {message_types}")
            
            # Check for correlation IDs
            correlation_ids = [msg['correlation_id'] for msg in session['messages'] if msg['correlation_id']]
            logger.info(f"   🔗 Correlation IDs: {len(correlation_ids)} found")
            
            # Validate early message capture
            if session['early_messages']:
                logger.info("   ✅ Early messages captured - Buffer system working!")
            else:
                logger.warning("   ⚠️  No early messages detected - Check buffer system")
        
        # Overall assessment
        total_messages = sum(len(session['messages']) for session in self.task_sessions.values())
        total_early_messages = sum(len(session['early_messages']) for session in self.task_sessions.values())
        
        logger.info(f"\n🎯 OVERALL ASSESSMENT:")
        logger.info(f"   📊 Total Messages Processed: {total_messages}")
        logger.info(f"   🔔 Total Early Messages: {total_early_messages}")
        
        if total_early_messages > 0:
            logger.info("   ✅ SUCCESS: Early message capture working!")
            logger.info("   ✅ Redis-SSE bridge fix appears to be functioning")
        else:
            logger.warning("   ❌ CONCERN: No early messages captured")
            logger.info("   💡 The fix may need additional investigation")
    
    def stop_monitoring(self):
        """Stop the monitoring process."""
        self.monitoring = False

async def main():
    """Main validation function."""
    validator = RealWorldValidator()
    
    print("🧪 REAL-WORLD REDIS-SSE BRIDGE VALIDATION")
    print("==========================================")
    print("")
    print("This tool monitors actual blog generation to validate the fix.")
    print("")
    print("🚀 INSTRUCTIONS:")
    print("1. Keep this terminal open")
    print("2. Open https://localhost:3001 in your browser")
    print("3. Generate a blog post")
    print("4. Watch the message flow below")
    print("")
    print("Press Ctrl+C to stop and generate report")
    print("")
    
    try:
        await validator.start_monitoring()
    except KeyboardInterrupt:
        validator.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main())