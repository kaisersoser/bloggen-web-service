#!/usr/bin/env python3
"""
Test script to check image-related notifications in CrewAI stdout capture.

Tests whether image search and generation events are being captured
by our notification system.
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


class ImageNotificationCollector:
    """Collects notifications from image tool operations"""
    
    def __init__(self):
        self.notifications: List[Dict[str, Any]] = []
        self.image_events: List[Dict[str, Any]] = []
    
    def collect_notification(self, event: Dict[str, Any]) -> None:
        """Collect and categorize notifications"""
        self.notifications.append({
            'timestamp': time.time(),
            'event': event
        })
        
        # Check if this is an image-related event
        if self._is_image_event(event):
            self.image_events.append(event)
            print(f"🖼️  IMAGE EVENT: {event}")
    
    def _is_image_event(self, event: Dict[str, Any]) -> bool:
        """Check if an event is image-related"""
        event_str = str(event).lower()
        image_keywords = [
            'image', 'unsplash', 'openai', 'dall-e', 'photo', 'picture',
            'visual', 'generate', 'search', 'api', 'url'
        ]
        return any(keyword in event_str for keyword in image_keywords)
    
    def print_summary(self):
        """Print summary of collected notifications"""
        print(f"\n📊 NOTIFICATION SUMMARY:")
        print(f"Total notifications: {len(self.notifications)}")
        print(f"Image-related events: {len(self.image_events)}")
        
        if self.image_events:
            print(f"\n🖼️  IMAGE EVENTS DETAILS:")
            for i, event in enumerate(self.image_events, 1):
                print(f"{i}. {event}")
        else:
            print(f"\n❌ No image-related events captured")


def test_unsplash_tool():
    """Test Unsplash tool with stdout capture"""
    print("🔍 Testing Unsplash Image Tool...")
    
    collector = ImageNotificationCollector()
    
    try:
        with capture_crewai_output(collector.collect_notification):
            tool = UnsplashImageTool()
            result = tool._run("artificial intelligence robot", count=1, orientation="landscape")
            print(f"✅ Unsplash result: {result[:100]}...")
            
    except Exception as e:
        print(f"❌ Unsplash test failed: {e}")
    
    return collector


def test_openai_tool():
    """Test OpenAI image tool with stdout capture"""
    print("\n🎨 Testing OpenAI Image Tool...")
    
    collector = ImageNotificationCollector()
    
    try:
        with capture_crewai_output(collector.collect_notification):
            tool = OpenAIImageTool()
            result = tool._run("a futuristic AI robot in a modern office", size="1024x1024")
            print(f"✅ OpenAI result: {result[:100]}...")
            
    except Exception as e:
        print(f"❌ OpenAI test failed: {e}")
    
    return collector


def main():
    """Main test function"""
    print("🧪 TESTING IMAGE TOOL NOTIFICATIONS")
    print("=" * 50)
    
    # Test Unsplash tool
    unsplash_collector = test_unsplash_tool()
    unsplash_collector.print_summary()
    
    # Test OpenAI tool
    openai_collector = test_openai_tool()
    openai_collector.print_summary()
    
    # Combined analysis
    total_notifications = len(unsplash_collector.notifications) + len(openai_collector.notifications)
    total_image_events = len(unsplash_collector.image_events) + len(openai_collector.image_events)
    
    print(f"\n🎯 OVERALL ANALYSIS:")
    print(f"Combined total notifications: {total_notifications}")
    print(f"Combined image events: {total_image_events}")
    
    if total_image_events > 0:
        print(f"✅ Image notifications ARE being captured")
    else:
        print(f"❌ Image notifications are NOT being captured")
        print(f"💡 Recommendation: Add specific patterns for image tool output")


if __name__ == "__main__":
    main()