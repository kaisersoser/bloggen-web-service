#!/usr/bin/env python3
"""
Test real blog generation specifically to capture image-related notifications directly from enhanced capture system.

This test bypasses the flow's status callback and connects directly to the enhanced capture system
to verify image tool activities are being captured properly.
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
from core.crewai_stdout_capture import capture_crewai_output


class DirectImageNotificationCapture:
    """Captures image notifications directly from enhanced capture system"""
    
    def __init__(self):
        self.all_events: List[Dict[str, Any]] = []
        self.image_events: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        
        # Consumer-meaningful image event types we're looking for
        self.image_event_types = {
            'image_source_fallback', 'image_auto_enhancement', 'image_search_attempt',
            'images_found', 'ai_image_generated', 'image_storage_complete', 'hero_image_selected'
        }
    
    def capture_callback(self, event: Dict[str, Any]) -> None:
        """Directly capture events from enhanced capture system"""
        timestamp = datetime.now()
        elapsed = (timestamp - self.start_time).total_seconds()
        
        # Store all events
        event_data = {
            'timestamp': timestamp.isoformat(),
            'elapsed_seconds': elapsed,
            'event': event
        }
        self.all_events.append(event_data)
        
        # Check if this is an image-related event
        event_type = event.get('type', '')
        if event_type in self.image_event_types:
            self.image_events.append(event_data)
            print(f"🖼️  [{elapsed:6.1f}s] IMAGE EVENT: {event_type} - {event.get('data', {})}")
        else:
            print(f"📢 [{elapsed:6.1f}s] OTHER EVENT: {event_type}")
    
    def analyze_results(self) -> Dict[str, Any]:
        """Analyze and summarize captured events"""
        total_time = (datetime.now() - self.start_time).total_seconds()
        
        # Group image events by type
        events_by_type = {}
        for event_data in self.image_events:
            event_type = event_data['event'].get('type', 'unknown')
            if event_type not in events_by_type:
                events_by_type[event_type] = []
            events_by_type[event_type].append(event_data)
        
        # Group all events by type for analysis
        all_events_by_type = {}
        for event_data in self.all_events:
            event_type = event_data['event'].get('type', 'unknown')
            if event_type not in all_events_by_type:
                all_events_by_type[event_type] = []
            all_events_by_type[event_type].append(event_data)
        
        return {
            'total_execution_time': total_time,
            'total_events': len(self.all_events),
            'image_events': len(self.image_events),
            'events_by_type': events_by_type,
            'all_events_by_type': all_events_by_type,
            'image_event_rate': len(self.image_events) / total_time if total_time > 0 else 0
        }
    
    def print_report(self):
        """Print comprehensive analysis report"""
        analysis = self.analyze_results()
        
        print(f"\n🖼️  DIRECT IMAGE CAPTURE ANALYSIS REPORT")
        print(f"=" * 60)
        print(f"📊 Total execution time: {analysis['total_execution_time']:.1f} seconds")
        print(f"📢 Total events captured: {analysis['total_events']}")
        print(f"🖼️  Image events captured: {analysis['image_events']}")
        print(f"⚡ Image event rate: {analysis['image_event_rate']:.3f} events/second")
        
        if analysis['image_events'] > 0:
            print(f"\n✅ IMAGE EVENTS BY TYPE:")
            for event_type, events in analysis['events_by_type'].items():
                print(f"  🔸 {event_type}: {len(events)} events")
        else:
            print(f"\n❌ NO IMAGE EVENTS CAPTURED")
        
        print(f"\n📋 ALL EVENT TYPES CAPTURED:")
        for event_type, events in analysis['all_events_by_type'].items():
            print(f"  📍 {event_type}: {len(events)} events")
        
        if analysis['image_events'] > 0:
            print(f"\n⏰ IMAGE EVENT TIMELINE:")
            for i, event_data in enumerate(self.image_events, 1):
                event = event_data['event']
                time_str = f"{event_data['elapsed_seconds']:6.1f}s"
                event_type = event.get('type', 'unknown')
                data = event.get('data', {})
                print(f"  {i:2d}. [{time_str}] {event_type}: {data}")


def test_direct_image_capture():
    """Test direct image capture from enhanced capture system during blog generation"""
    print("🧪 DIRECT IMAGE CAPTURE TEST")
    print("=" * 60)
    
    # Set up direct capture
    capture_system = DirectImageNotificationCapture()
    
    try:
        print(f"🚀 Starting blog generation with direct image capture...")
        
        # Use capture_crewai_output directly to intercept all events
        with capture_crewai_output(capture_system.capture_callback):
            # Create and run blog generation flow
            flow = BlogGenerationFlow()
            
            result = flow.kickoff({
                'topic': 'AI Image Generation Technologies 2025',
                'current_year': 2025,
                'user_id': 'direct-test-user',
                'blog_id': 'direct-test-20240917'
            })
        
        print(f"✅ Blog generation completed!")
        print(f"📄 Blog length: {len(str(result.get('final_blog_post', '')))} characters")
        
    except Exception as e:
        print(f"❌ Blog generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Generate and print analysis report
    capture_system.print_report()
    
    return capture_system


if __name__ == "__main__":
    capture_system = test_direct_image_capture()
    
    if capture_system and capture_system.image_events:
        print(f"\n🎯 SUCCESS: Captured {len(capture_system.image_events)} image events!")
        print(f"🎯 VERIFICATION: Enhanced image capture system is working!")
    else:
        print(f"\n⚠️  NO IMAGE EVENTS: System may need debugging")