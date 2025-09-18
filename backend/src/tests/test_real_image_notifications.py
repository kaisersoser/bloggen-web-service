#!/usr/bin/env python3
"""
Test real blog generation specifically to capture image-related notifications.

This test runs a complete blog generation with our enhanced notification system
and specifically analyzes image tool activities.
"""

import sys
import os
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bloggen.flows import BlogGenerationFlow


class ImageNotificationAnalyzer:
    """Analyzes notifications specifically for image-related events"""
    
    def __init__(self):
        self.all_notifications: List[Dict[str, Any]] = []
        self.image_notifications: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        
        # Image event types we're looking for
        self.image_event_types = {
            'unsplash_init', 'unsplash_search', 'unsplash_fallback',
            'openai_generation_request', 'openai_generation_response',
            's3_storage_start', 's3_storage_success', 'image_conversion',
            'ai_generation_success', 'image_success'
        }
    
    def process_notification(self, notification: Dict[str, Any]) -> None:
        """Process each notification and extract image events"""
        timestamp = datetime.now()
        elapsed = (timestamp - self.start_time).total_seconds()
        
        # Store all notifications
        self.all_notifications.append({
            'timestamp': timestamp.isoformat(),
            'elapsed_seconds': elapsed,
            'notification': notification
        })
        
        # Check if this is an image-related notification
        if self._is_image_notification(notification):
            image_event = {
                'timestamp': timestamp.isoformat(),
                'elapsed_seconds': elapsed,
                'event_type': notification.get('type', 'unknown'),
                'data': notification.get('data', {}),
                'source': notification.get('source', 'unknown')
            }
            self.image_notifications.append(image_event)
            print(f"🖼️  [{elapsed:6.1f}s] IMAGE EVENT: {notification.get('type')} - {notification.get('data')}")
    
    def _is_image_notification(self, notification: Dict[str, Any]) -> bool:
        """Check if notification is image-related"""
        event_type = notification.get('type', '')
        return event_type in self.image_event_types
    
    def analyze_results(self) -> Dict[str, Any]:
        """Analyze and summarize image notification results"""
        total_time = (datetime.now() - self.start_time).total_seconds()
        
        # Group image events by type
        events_by_type = {}
        for event in self.image_notifications:
            event_type = event['event_type']
            if event_type not in events_by_type:
                events_by_type[event_type] = []
            events_by_type[event_type].append(event)
        
        # Create timeline
        timeline = []
        for event in self.image_notifications:
            timeline.append({
                'time': event['elapsed_seconds'],
                'type': event['event_type'],
                'summary': self._summarize_event(event)
            })
        
        return {
            'total_execution_time': total_time,
            'total_notifications': len(self.all_notifications),
            'image_notifications': len(self.image_notifications),
            'events_by_type': events_by_type,
            'timeline': timeline,
            'image_event_rate': len(self.image_notifications) / total_time if total_time > 0 else 0
        }
    
    def _summarize_event(self, event: Dict[str, Any]) -> str:
        """Create a human-readable summary of an image event"""
        event_type = event['event_type']
        data = event['data']
        
        if event_type == 'unsplash_init':
            return f"Unsplash initialized (API key: {data.get('api_key_preview', 'N/A')})"
        elif event_type == 'unsplash_search':
            return f"Searching Unsplash for: '{data.get('query', 'N/A')}'"
        elif event_type == 'unsplash_fallback':
            return f"Unsplash fallback: {data.get('reason', 'N/A')}"
        elif event_type == 'openai_generation_request':
            return f"OpenAI image generation started"
        elif event_type == 'openai_generation_response':
            status = data.get('status_code', 'N/A')
            return f"OpenAI image generation response: {status}"
        elif event_type == 's3_storage_start':
            return f"S3 storage started for blog: {data.get('blog_id', 'N/A')}"
        elif event_type == 's3_storage_success':
            url = data.get('url', 'N/A')
            return f"S3 storage complete: {url[:50]}..."
        elif event_type == 'image_conversion':
            size = data.get('size_bytes', 'N/A')
            return f"Image converted to JPEG: {size} bytes"
        elif event_type == 'ai_generation_success':
            current = data.get('current', 'N/A')
            total = data.get('total', 'N/A')
            return f"AI image generated: {current}/{total}"
        else:
            return f"Unknown image event: {data}"
    
    def print_report(self):
        """Print comprehensive image notification report"""
        analysis = self.analyze_results()
        
        print(f"\n🖼️  IMAGE NOTIFICATION ANALYSIS REPORT")
        print(f"=" * 60)
        print(f"📊 Total execution time: {analysis['total_execution_time']:.1f} seconds")
        print(f"📢 Total notifications: {analysis['total_notifications']}")
        print(f"🖼️  Image notifications: {analysis['image_notifications']}")
        print(f"⚡ Image event rate: {analysis['image_event_rate']:.3f} events/second")
        
        if analysis['image_notifications'] > 0:
            print(f"\n📋 IMAGE EVENTS BY TYPE:")
            for event_type, events in analysis['events_by_type'].items():
                print(f"  🔸 {event_type}: {len(events)} events")
            
            print(f"\n⏰ IMAGE EVENT TIMELINE:")
            for i, event in enumerate(analysis['timeline'], 1):
                print(f"  {i:2d}. [{event['time']:6.1f}s] {event['summary']}")
        else:
            print(f"\n❌ NO IMAGE EVENTS CAPTURED")
            print(f"💡 This could indicate:")
            print(f"   - Image generation is disabled")
            print(f"   - Image tools are not being used")
            print(f"   - Logging capture is not working")


def test_real_blog_with_image_analysis():
    """Run real blog generation with image notification analysis"""
    print("🧪 REAL BLOG GENERATION WITH IMAGE ANALYSIS")
    print("=" * 60)
    
    # Set up analyzer
    analyzer = ImageNotificationAnalyzer()
    
    try:
        # Create and run blog generation flow (without audit tracker to keep test simple)
        flow = BlogGenerationFlow(
            status_callback=analyzer.process_notification
        )
        
        print(f"🚀 Starting blog generation with image analysis...")
        result = flow.kickoff({
            'topic': 'AI Image Generation in 2024: DALL-E vs Midjourney',
            'current_year': 2025,
            'user_id': 'image-test-user',
            'blog_id': 'image-test-20240917'
        })
        
        print(f"✅ Blog generation completed!")
        print(f"📄 Blog length: {len(str(result.get('final_blog_post', '')))} characters")
        
    except Exception as e:
        print(f"❌ Blog generation failed: {e}")
        return None
    
    # Generate and print analysis report
    analyzer.print_report()
    
    return analyzer


if __name__ == "__main__":
    analyzer = test_real_blog_with_image_analysis()
    
    if analyzer and analyzer.image_notifications:
        print(f"\n🎯 SUCCESS: Captured {len(analyzer.image_notifications)} image events!")
    else:
        print(f"\n⚠️  NO IMAGE EVENTS: Check image tool configuration")