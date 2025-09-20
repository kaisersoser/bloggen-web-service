#!/usr/bin/env python3
"""
Frontend Notification E2E Validation Test

This test validates that the frontend actually receives all SSE notifications
by monitoring both Redis message flow AND frontend notification reception.
"""

import asyncio
import redis
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Set
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import urllib3

# Disable SSL warnings for local testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FrontendNotificationValidator:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.redis_messages = []
        self.frontend_messages = []
        self.driver = None
        self.task_id = None
        
    async def setup_browser(self):
        """Setup Chrome browser with console logging capabilities."""
        chrome_options = Options()
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        # Enable logging
        chrome_options.add_argument('--enable-logging')
        chrome_options.add_argument('--log-level=0')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        
        logger.info("🌐 Browser setup complete")
    
    async def monitor_redis_messages(self, task_id: str):
        """Monitor Redis messages for the given task ID."""
        pubsub = self.redis_client.pubsub()
        
        try:
            channels = [f"task_updates:{task_id}", f"sse_immediate:{task_id}"]
            for channel in channels:
                pubsub.subscribe(channel)
            
            logger.info(f"📡 Monitoring Redis channels: {channels}")
            
            start_time = time.time()
            while time.time() - start_time < 180:  # 3 minute timeout
                try:
                    message = pubsub.get_message(timeout=1.0)
                    if message and message['type'] == 'message':
                        data = json.loads(message['data'])
                        message_info = {
                            'timestamp': datetime.now().isoformat(),
                            'channel': message['channel'],
                            'message_type': data.get('message_type', 'unknown'),
                            'data': data,
                            'source': 'redis'
                        }
                        self.redis_messages.append(message_info)
                        logger.info(f"📨 Redis: {message_info['message_type']} on {message_info['channel']}")
                        
                except Exception as e:
                    if "timed out" not in str(e):
                        logger.error(f"Error monitoring Redis: {e}")
                    
        except Exception as e:
            logger.error(f"Redis monitoring error: {e}")
        finally:
            pubsub.close()
    
    def capture_frontend_logs(self):
        """Capture browser console logs to extract SSE messages."""
        try:
            logs = self.driver.get_log('browser')
            for log in logs:
                message = log.get('message', '')
                timestamp = log.get('timestamp', 0)
                
                # Look for SSE-related messages
                if any(keyword in message for keyword in ['SSE Message received', 'Processing SSE message', 'SSE Update received']):
                    # Parse the message to extract details
                    message_info = {
                        'timestamp': datetime.fromtimestamp(timestamp/1000).isoformat(),
                        'message': message,
                        'source': 'frontend',
                        'raw_log': log
                    }
                    
                    # Try to extract message type from the log
                    if 'SSE Message received:' in message:
                        parts = message.split('SSE Message received:')
                        if len(parts) > 1:
                            message_info['message_type'] = parts[1].strip().split()[0]
                    
                    self.frontend_messages.append(message_info)
                    logger.info(f"🌐 Frontend: {message_info.get('message_type', 'unknown')} at {message_info['timestamp']}")
                    
        except Exception as e:
            logger.error(f"Error capturing frontend logs: {e}")
    
    async def generate_blog_via_frontend(self):
        """Generate a blog through the frontend UI and capture notifications."""
        try:
            # Navigate to frontend
            self.driver.get("https://localhost:3001")
            logger.info("🌐 Navigated to frontend")
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Find and fill the topic input
            topic_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "textarea"))
            )
            topic_input.clear()
            topic_input.send_keys("E2E Test: AI trends validation test")
            logger.info("📝 Entered blog topic")
            
            # Find and click generate button
            generate_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Generate Blog') or contains(@class, 'generate')]"))
            )
            
            # Start monitoring frontend logs
            asyncio.create_task(self._periodic_log_capture())
            
            # Click generate button
            generate_button.click()
            logger.info("🚀 Clicked Generate Blog button")
            
            # Wait for generation to start and capture initial messages
            await asyncio.sleep(5)
            
            # Continue monitoring for a reasonable duration
            for i in range(36):  # 3 minutes total (36 * 5 seconds)
                await asyncio.sleep(5)
                self.capture_frontend_logs()
                
                # Check if generation completed
                try:
                    completion_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'completed') or contains(text(), 'Generated successfully')]")
                    if completion_elements:
                        logger.info("✅ Blog generation completed")
                        break
                except:
                    pass
            
        except Exception as e:
            logger.error(f"Error during frontend blog generation: {e}")
    
    async def _periodic_log_capture(self):
        """Periodically capture frontend logs."""
        for _ in range(60):  # Capture for 5 minutes max
            await asyncio.sleep(5)
            self.capture_frontend_logs()
    
    def analyze_results(self) -> Dict:
        """Analyze and compare Redis vs Frontend message reception."""
        redis_message_types = {}
        frontend_message_types = {}
        
        # Count Redis message types
        for msg in self.redis_messages:
            msg_type = msg['message_type']
            redis_message_types[msg_type] = redis_message_types.get(msg_type, 0) + 1
        
        # Count Frontend message types
        for msg in self.frontend_messages:
            msg_type = msg.get('message_type', 'unknown')
            frontend_message_types[msg_type] = frontend_message_types.get(msg_type, 0) + 1
        
        # Calculate coverage
        total_redis_messages = len(self.redis_messages)
        total_frontend_messages = len(self.frontend_messages)
        
        coverage_percentage = 0
        if total_redis_messages > 0:
            coverage_percentage = (total_frontend_messages / total_redis_messages) * 100
        
        # Check for early messages
        early_message_types = {'taskcreated', 'initializing', 'status'}
        redis_early_messages = [msg for msg in self.redis_messages if msg['message_type'] in early_message_types]
        frontend_early_messages = [msg for msg in self.frontend_messages if msg.get('message_type') in early_message_types]
        
        return {
            'total_redis_messages': total_redis_messages,
            'total_frontend_messages': total_frontend_messages,
            'coverage_percentage': coverage_percentage,
            'redis_message_types': redis_message_types,
            'frontend_message_types': frontend_message_types,
            'redis_early_messages': len(redis_early_messages),
            'frontend_early_messages': len(frontend_early_messages),
            'early_message_coverage': (len(frontend_early_messages) / len(redis_early_messages) * 100) if redis_early_messages else 0,
            'redis_messages': self.redis_messages[:10],  # Sample for review
            'frontend_messages': self.frontend_messages[:10]  # Sample for review
        }
    
    def generate_report(self, results: Dict):
        """Generate a comprehensive validation report."""
        logger.info("\n" + "=" * 80)
        logger.info("📊 FRONTEND NOTIFICATION E2E VALIDATION REPORT")
        logger.info("=" * 80)
        
        logger.info(f"\n🎯 MESSAGE RECEPTION ANALYSIS:")
        logger.info(f"   📡 Redis Messages Published: {results['total_redis_messages']}")
        logger.info(f"   🌐 Frontend Messages Received: {results['total_frontend_messages']}")
        logger.info(f"   📈 Overall Coverage: {results['coverage_percentage']:.1f}%")
        
        logger.info(f"\n🔔 EARLY MESSAGE ANALYSIS:")
        logger.info(f"   📡 Redis Early Messages: {results['redis_early_messages']}")
        logger.info(f"   🌐 Frontend Early Messages: {results['frontend_early_messages']}")
        logger.info(f"   📈 Early Message Coverage: {results['early_message_coverage']:.1f}%")
        
        logger.info(f"\n📋 MESSAGE TYPE BREAKDOWN:")
        logger.info(f"   📡 Redis Types: {results['redis_message_types']}")
        logger.info(f"   🌐 Frontend Types: {results['frontend_message_types']}")
        
        # Success criteria
        success_criteria = {
            'overall_coverage': results['coverage_percentage'] >= 80,
            'early_message_coverage': results['early_message_coverage'] >= 80,
            'minimum_messages': results['total_frontend_messages'] >= 10
        }
        
        logger.info(f"\n✅ SUCCESS CRITERIA:")
        for criteria, passed in success_criteria.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"   {criteria}: {status}")
        
        overall_success = all(success_criteria.values())
        final_status = "🎉 SUCCESS" if overall_success else "❌ NEEDS IMPROVEMENT"
        
        logger.info(f"\n{final_status}: Frontend Notification System")
        if overall_success:
            logger.info("✅ Redis-SSE bridge fix is working correctly!")
            logger.info("✅ Frontend receives notifications properly!")
        else:
            logger.info("❌ Frontend notification reception needs improvement")
            logger.info("💡 Check SSE connection stability and message parsing")
        
        logger.info("=" * 80)
        return overall_success
    
    async def cleanup(self):
        """Clean up resources."""
        if self.driver:
            self.driver.quit()
        logger.info("🧹 Cleanup completed")

async def run_frontend_validation():
    """Main function to run the frontend notification validation."""
    validator = FrontendNotificationValidator()
    
    try:
        logger.info("🧪 STARTING FRONTEND NOTIFICATION E2E VALIDATION")
        logger.info("=" * 60)
        
        # Setup browser
        await validator.setup_browser()
        
        # Start Redis monitoring in background
        redis_task = asyncio.create_task(validator.monitor_redis_messages("test-task"))
        
        # Generate blog via frontend
        await validator.generate_blog_via_frontend()
        
        # Wait a bit more for final messages
        await asyncio.sleep(10)
        
        # Cancel Redis monitoring
        redis_task.cancel()
        
        # Analyze results
        results = validator.analyze_results()
        success = validator.generate_report(results)
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        return False
    finally:
        await validator.cleanup()

if __name__ == "__main__":
    try:
        success = asyncio.run(run_frontend_validation())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n👋 Validation stopped by user")
        exit(0)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        exit(1)