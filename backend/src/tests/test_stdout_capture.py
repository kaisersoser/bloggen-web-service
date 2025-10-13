#!/usr/bin/env python3
"""
Backend-only test script for enhanced CrewAI notifications.

This script tests the stdout capture wrapper and notification system
without requiring the frontend, allowing us to see exactly what 
notifications are being generated from CrewAI's execution.
"""

import sys
import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List

# Add the src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
sys.path.insert(0, src_dir)

# Configure logging to see detailed output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_notifications.log')
    ]
)

logger = logging.getLogger(__name__)

# Import our systems
from core.context_vars import set_request_context
from bloggen.flows import BlogGenerationFlow
from bloggen.status_manager import StatusUpdateManager


class TestNotificationCollector:
    """Collects all notifications for analysis"""
    
    def __init__(self):
        self.notifications = []
        self.start_time = datetime.now()
    
    def collect_notification(self, notification: Dict[str, Any]):
        """Collect a notification with timestamp"""
        timestamp = datetime.now()
        elapsed = (timestamp - self.start_time).total_seconds()
        
        collected = {
            'timestamp': timestamp.isoformat(),
            'elapsed_seconds': elapsed,
            'notification': notification
        }
        
        self.notifications.append(collected)
        
        # Log the notification for real-time monitoring
        msg_type = notification.get('message_type', 'unknown')
        content = notification.get('message', notification.get('thought', notification.get('tool_name', 'N/A')))
        logger.info(f"📢 [{elapsed:6.1f}s] {msg_type.upper()}: {content}")
    
    def print_summary(self):
        """Print a summary of all collected notifications"""
        print("\n" + "="*80)
        print("🔍 NOTIFICATION CAPTURE SUMMARY")
        print("="*80)
        print(f"Total notifications captured: {len(self.notifications)}")
        print(f"Test duration: {(datetime.now() - self.start_time).total_seconds():.1f} seconds")
        
        # Group by message type
        by_type = {}
        for notif in self.notifications:
            msg_type = notif['notification'].get('message_type', 'unknown')
            by_type.setdefault(msg_type, []).append(notif)
        
        print(f"\nNotifications by type:")
        for msg_type, items in by_type.items():
            print(f"  {msg_type}: {len(items)} notifications")
        
        print(f"\nDetailed timeline:")
        for i, notif in enumerate(self.notifications, 1):
            elapsed = notif['elapsed_seconds']
            notification = notif['notification']
            msg_type = notification.get('message_type', 'unknown')
            content = str(notification.get('message', notification.get('thought', notification.get('tool_name', 'N/A'))))[:100]
            print(f"  {i:2d}. [{elapsed:6.1f}s] {msg_type:15s} - {content}")


def test_crewai_notifications():
    """Test the enhanced notification system with a simple blog generation"""
    
    print("🚀 Starting CrewAI Notification Test")
    print("-" * 50)
    
    # Set up test context
    task_id = f"test-{int(datetime.now().timestamp())}"
    
    set_request_context(
        request_id=f"req-{task_id}",
        task_id=task_id,
        user_id="test-user",
        user_email="test@example.com",
        user_role="ADMIN",
        blog_id=task_id,
        topic="AI Testing"
    )
    
    # Create notification collector
    collector = TestNotificationCollector()
    
    # Create flow with the test status manager
    def flow_status_callback(notification: Dict[str, Any]):
        collector.collect_notification(notification)
    
    flow = BlogGenerationFlow(
        status_callback=flow_status_callback,
        user_id="test-user",
        blog_id=task_id,
        topic="Benefits of AI in Education"
    )
    
    try:
        logger.info("🔄 Starting blog generation flow...")
        
        # Run the flow (CrewAI flows use kickoff method)
        result = flow.kickoff()
        
        logger.info("✅ Blog generation completed!")
        print(f"\nGenerated blog length: {len(str(result)) if result else 0} characters")
        
    except Exception as e:
        logger.error(f"❌ Error during blog generation: {e}")
        import traceback
        traceback.print_exc()
    
    # Print summary of captured notifications
    collector.print_summary()
    
    return collector.notifications


if __name__ == "__main__":
    print("🔍 Backend Notification Testing Script")
    print("=" * 60)
    
    # Test full blog generation flow
    print("\n2️⃣ Testing full blog generation flow...")
    flow_results = test_crewai_notifications()
    
    print("\n🎯 TEST COMPLETE")
    print(f"Full flow captured: {len(flow_results)} notifications")
    print("\nCheck 'test_notifications.log' for detailed logs.")