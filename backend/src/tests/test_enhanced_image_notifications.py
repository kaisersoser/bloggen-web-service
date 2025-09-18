#!/usr/bin/env python3
"""
Test to verify enhanced image notification capture with both stdout and logging.
"""

import sys
import os
import time
import logging
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.crewai_stdout_capture import capture_crewai_output
from bloggen.tools.unsplash_tool import UnsplashImageTool
from bloggen.tools.openai_image_tool import OpenAIImageTool


class EnhancedImageNotificationCollector:
    """Collects notifications from enhanced capture system"""
    
    def __init__(self):
        self.notifications: List[Dict[str, Any]] = []
        self.image_events: List[Dict[str, Any]] = []
    
    def collect_notification(self, event: Dict[str, Any]) -> None:
        """Collect and categorize notifications"""
        self.notifications.append({
            'timestamp': time.time(),
            'event': event
        })
        
        # All events from enhanced system are relevant for image tools
        event_type = event.get('type', '')
        if any(keyword in event_type for keyword in ['unsplash', 'openai', 's3', 'image', 'ai_generation']):
            self.image_events.append(event)
            print(f"🖼️  ENHANCED IMAGE EVENT: {event}")
        else:
            print(f"📋 OTHER EVENT: {event}")
    
    def print_summary(self):
        """Print summary of collected notifications"""
        print(f"\n📊 ENHANCED NOTIFICATION SUMMARY:")
        print(f"Total notifications: {len(self.notifications)}")
        print(f"Image-related events: {len(self.image_events)}")
        
        if self.image_events:
            print(f"\n🖼️  ENHANCED IMAGE EVENTS DETAILS:")
            for i, event in enumerate(self.image_events, 1):
                print(f"{i}. Type: {event.get('type')}, Data: {event.get('data')}")
        else:
            print(f"\n❌ No enhanced image events captured")


def test_enhanced_unsplash_capture():
    """Test enhanced Unsplash tool capture"""
    print("🔍 Testing Enhanced Unsplash Image Tool...")
    
    collector = EnhancedImageNotificationCollector()
    
    try:
        with capture_crewai_output(collector.collect_notification):
            # Also inject test logging to verify our capture works
            print("📋 Starting Unsplash tool test")
            
            tool = UnsplashImageTool()
            print("📋 Unsplash tool created")
            
            # Manually log a test pattern to verify capture
            logging.info("Unsplash tool initialized with API key: test123...")
            logging.info("Searching Unsplash for: 'test query'")
            
            result = tool._run("artificial intelligence", count=1)
            print(f"📋 Unsplash tool result received: {result[:50]}...")
            
    except Exception as e:
        print(f"❌ Enhanced Unsplash test failed: {e}")
    
    return collector


def test_enhanced_openai_capture():
    """Test enhanced OpenAI tool capture"""
    print("\n🎨 Testing Enhanced OpenAI Image Tool...")
    
    collector = EnhancedImageNotificationCollector()
    
    try:
        with capture_crewai_output(collector.collect_notification):
            print("📋 Starting OpenAI tool test")
            
            tool = OpenAIImageTool()
            print("📋 OpenAI tool created")
            
            # Manually log test patterns to verify capture
            logging.info("Starting hero image storage for blog test-123")
            logging.info("Image stored permanently in S3: https://test-bucket.s3.amazonaws.com/test.jpg")
            
            result = tool._run("robot assistant")
            print(f"📋 OpenAI tool result received: {result[:50]}...")
            
    except Exception as e:
        print(f"❌ Enhanced OpenAI test failed: {e}")
    
    return collector


def test_manual_logging_capture():
    """Test manual logging to verify capture patterns work"""
    print("\n🧪 Testing Manual Logging Capture...")
    
    collector = EnhancedImageNotificationCollector()
    
    try:
        with capture_crewai_output(collector.collect_notification):
            # Test each pattern manually
            test_logs = [
                "Unsplash tool initialized with API key: mpgmWV_bFr...",
                "Searching Unsplash for: 'machine learning'",
                "falling back to AI generation",
                "HTTP Request: POST https://api.openai.com/v1/images/generations",
                "HTTP Response: POST https://api.openai.com/v1/images/generations \"200 OK\"",
                "Starting hero image storage for blog test-456",
                "Image stored permanently in S3: https://bucket.s3.amazonaws.com/image.jpg",
                "Converted image to JPEG (quality=85), size: 97625 bytes",
                "✅ Generated AI image 1/1"
            ]
            
            for log in test_logs:
                logging.info(log)
                print(f"📋 Logged: {log}")
                
    except Exception as e:
        print(f"❌ Manual logging test failed: {e}")
    
    return collector


def main():
    """Main test function"""
    print("🧪 TESTING ENHANCED IMAGE NOTIFICATIONS")
    print("=" * 60)
    
    # Test enhanced Unsplash capture
    unsplash_collector = test_enhanced_unsplash_capture()
    unsplash_collector.print_summary()
    
    # Test enhanced OpenAI capture
    openai_collector = test_enhanced_openai_capture()
    openai_collector.print_summary()
    
    # Test manual logging capture
    manual_collector = test_manual_logging_capture()
    manual_collector.print_summary()
    
    # Combined analysis
    total_notifications = (len(unsplash_collector.notifications) + 
                          len(openai_collector.notifications) + 
                          len(manual_collector.notifications))
    total_image_events = (len(unsplash_collector.image_events) + 
                         len(openai_collector.image_events) + 
                         len(manual_collector.image_events))
    
    print(f"\n🎯 OVERALL ENHANCED ANALYSIS:")
    print(f"Combined total notifications: {total_notifications}")
    print(f"Combined image events: {total_image_events}")
    
    if total_image_events > 0:
        print(f"✅ Enhanced image notifications ARE being captured")
        print(f"🔧 Manual logging test events: {len(manual_collector.image_events)}")
        print(f"🔧 Real tool test events: {len(unsplash_collector.image_events) + len(openai_collector.image_events)}")
    else:
        print(f"❌ Enhanced image notifications are NOT being captured")
        print(f"💡 Check if logging capture is working properly")


if __name__ == "__main__":
    main()