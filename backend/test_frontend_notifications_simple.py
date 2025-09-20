#!/usr/bin/env python3
"""
Simplified Frontend Notification E2E Validation

This test provides a framework for validating frontend notification reception
without requiring Selenium. It monitors Redis and provides instructions for
manual frontend validation.
"""

import asyncio
import redis
import json
import time
from datetime import datetime
from typing import Dict, List
import logging
import requests
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimplifiedNotificationValidator:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.redis_messages = []
        self.start_time = None
        self.task_id = None
        
    async def monitor_redis_and_guide_frontend_test(self):
        """Monitor Redis while providing guidance for frontend testing."""
        
        logger.info("🧪 FRONTEND NOTIFICATION E2E VALIDATION")
        logger.info("=" * 60)
        logger.info("")
        logger.info("This test will:")
        logger.info("1. 📡 Monitor Redis messages in real-time")
        logger.info("2. 🌐 Provide JavaScript code to capture frontend messages")
        logger.info("3. 📊 Compare Redis vs Frontend message reception")
        logger.info("")
        
        # Display frontend JavaScript code
        self.display_frontend_javascript()
        
        logger.info("🚀 INSTRUCTIONS:")
        logger.info("1. Copy the JavaScript code above")
        logger.info("2. Open https://localhost:3001 in your browser")
        logger.info("3. Open DevTools Console (F12)")
        logger.info("4. Paste and run the JavaScript code")
        logger.info("5. Generate a blog through the UI")
        logger.info("6. Come back here for the Redis vs Frontend comparison")
        logger.info("")
        
        input("Press ENTER when you're ready to start monitoring...")
        
        # Start Redis monitoring
        pubsub = self.redis_client.pubsub()
        
        try:
            # Subscribe to all task channels
            pubsub.psubscribe('task_updates:*', 'sse_immediate:*')
            logger.info("📡 Redis monitoring started...")
            logger.info("🌐 Generate a blog in the browser now!")
            logger.info("=" * 60)
            
            self.start_time = time.time()
            
            while time.time() - self.start_time < 300:  # 5 minutes max
                try:
                    message = pubsub.get_message(timeout=2.0)
                    if message and message['type'] == 'pmessage':
                        await self._process_redis_message(message)
                        
                except Exception as e:
                    if "timed out" not in str(e):
                        logger.error(f"Redis monitoring error: {e}")
                        
        except KeyboardInterrupt:
            logger.info("\n👋 Monitoring stopped by user")
        finally:
            pubsub.close()
            await self._generate_comparison_report()
    
    def display_frontend_javascript(self):
        """Display JavaScript code for frontend message capture."""
        js_code = '''
// ====================================================
// FRONTEND MESSAGE CAPTURE CODE
// Copy and paste this into your browser console
// ====================================================

window.frontendMessages = [];
window.messageCount = 0;

// Override console.log to capture SSE messages
const originalLog = console.log;
console.log = function(...args) {
    const message = args.join(' ');
    const timestamp = new Date().toISOString();
    
    // Capture SSE-related messages
    if (message.includes('SSE Message received') || 
        message.includes('Processing SSE message') || 
        message.includes('SSE Update received') ||
        message.includes('📨') || 
        message.includes('🔄')) {
        
        window.messageCount++;
        
        // Extract message type
        let messageType = 'unknown';
        if (message.includes('received:')) {
            const parts = message.split('received:');
            if (parts.length > 1) {
                messageType = parts[1].trim().split(' ')[0];
            }
        }
        
        window.frontendMessages.push({
            timestamp: timestamp,
            message: message,
            messageType: messageType,
            count: window.messageCount
        });
        
        originalLog(`[${window.messageCount}] CAPTURED: ${messageType} at ${timestamp}`);
    }
    
    originalLog(...args);
};

// Function to get results
window.getFrontendResults = function() {
    const results = {
        totalMessages: window.frontendMessages.length,
        messages: window.frontendMessages,
        messageTypes: {}
    };
    
    // Count message types
    window.frontendMessages.forEach(msg => {
        const type = msg.messageType;
        results.messageTypes[type] = (results.messageTypes[type] || 0) + 1;
    });
    
    console.log('📊 FRONTEND RESULTS:', results);
    console.log('📋 Total Frontend Messages:', results.totalMessages);
    console.log('📋 Message Types:', results.messageTypes);
    
    return results;
};

console.log('✅ Frontend message capture initialized!');
console.log('🚀 Generate a blog now and watch messages being captured');
console.log('📊 Run getFrontendResults() when done to see the summary');

// ====================================================
'''
        
        logger.info("=" * 60)
        logger.info("📄 FRONTEND JAVASCRIPT CODE:")
        logger.info("=" * 60)
        print(js_code)
        logger.info("=" * 60)
    
    async def _process_redis_message(self, message):
        """Process and log Redis messages."""
        try:
            channel = message['channel']
            data = json.loads(message['data'])
            
            # Extract task ID
            task_id = channel.split(':')[1] if ':' in channel else 'unknown'
            if not self.task_id:
                self.task_id = task_id
                logger.info(f"🎯 Detected task ID: {task_id}")
            
            message_info = {
                'timestamp': datetime.now().isoformat(),
                'task_id': task_id,
                'channel': channel,
                'message_type': data.get('message_type', 'unknown'),
                'data': data
            }
            
            self.redis_messages.append(message_info)
            
            # Real-time logging with color coding
            msg_type = message_info['message_type']
            channel_short = channel.split(':')[0]
            
            if msg_type in ['taskcreated', 'initializing']:
                logger.info(f"🔔 EARLY: {msg_type:<15} | {channel_short}")
            elif msg_type in ['completion', 'completed']:
                logger.info(f"✅ FINAL: {msg_type:<15} | {channel_short}")
            else:
                logger.info(f"📨 MSG: {msg_type:<15} | {channel_short}")
                
        except Exception as e:
            logger.error(f"Error processing Redis message: {e}")
    
    async def _generate_comparison_report(self):
        """Generate comparison report and request frontend results."""
        logger.info("\n" + "=" * 60)
        logger.info("📊 REDIS MONITORING COMPLETE")
        logger.info("=" * 60)
        
        if not self.redis_messages:
            logger.warning("❌ No Redis messages captured!")
            logger.info("💡 Make sure to generate a blog while monitoring was active")
            return
        
        # Analyze Redis messages
        redis_message_types = {}
        early_messages = 0
        
        for msg in self.redis_messages:
            msg_type = msg['message_type']
            redis_message_types[msg_type] = redis_message_types.get(msg_type, 0) + 1
            
            if msg_type in ['taskcreated', 'initializing', 'status']:
                early_messages += 1
        
        logger.info(f"📡 REDIS RESULTS:")
        logger.info(f"   Total Messages: {len(self.redis_messages)}")
        logger.info(f"   Early Messages: {early_messages}")
        logger.info(f"   Message Types: {redis_message_types}")
        logger.info(f"   Task ID: {self.task_id}")
        
        logger.info("\n" + "=" * 60)
        logger.info("🌐 FRONTEND RESULTS NEEDED")
        logger.info("=" * 60)
        logger.info("Now run this command in your browser console:")
        logger.info("")
        logger.info("   getFrontendResults()")
        logger.info("")
        logger.info("Then compare the results:")
        logger.info("=" * 60)
        
        # Wait for user to provide frontend results
        logger.info("\nEnter the frontend results manually for comparison:")
        try:
            frontend_total = int(input("Total frontend messages received: ") or "0")
            frontend_early = int(input("Frontend early messages (taskcreated, initializing): ") or "0")
            
            # Calculate coverage
            coverage = (frontend_total / len(self.redis_messages) * 100) if self.redis_messages else 0
            early_coverage = (frontend_early / early_messages * 100) if early_messages else 0
            
            logger.info("\n" + "=" * 60)
            logger.info("📊 FINAL COMPARISON REPORT")
            logger.info("=" * 60)
            logger.info(f"📡 Redis Messages: {len(self.redis_messages)}")
            logger.info(f"🌐 Frontend Messages: {frontend_total}")
            logger.info(f"📈 Overall Coverage: {coverage:.1f}%")
            logger.info(f"🔔 Redis Early Messages: {early_messages}")
            logger.info(f"🔔 Frontend Early Messages: {frontend_early}")
            logger.info(f"📈 Early Message Coverage: {early_coverage:.1f}%")
            
            # Success evaluation
            success_criteria = {
                'Overall Coverage >= 80%': coverage >= 80,
                'Early Message Coverage >= 80%': early_coverage >= 80,
                'Minimum Messages Received': frontend_total >= 5
            }
            
            logger.info(f"\n✅ SUCCESS CRITERIA:")
            all_passed = True
            for criteria, passed in success_criteria.items():
                status = "✅ PASS" if passed else "❌ FAIL"
                logger.info(f"   {criteria}: {status}")
                if not passed:
                    all_passed = False
            
            if all_passed:
                logger.info(f"\n🎉 SUCCESS: Redis-SSE Bridge Fix Working!")
                logger.info("✅ Frontend notification system is functioning correctly")
            else:
                logger.info(f"\n❌ NEEDS IMPROVEMENT: Notification delivery issues detected")
                logger.info("💡 Check SSE connection stability and message handling")
            
            logger.info("=" * 60)
            return all_passed
            
        except (ValueError, KeyboardInterrupt):
            logger.info("\n⚠️ Manual comparison cancelled")
            return False

async def main():
    """Main function."""
    validator = SimplifiedNotificationValidator()
    
    try:
        await validator.monitor_redis_and_guide_frontend_test()
    except Exception as e:
        logger.error(f"❌ Validation error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(main())