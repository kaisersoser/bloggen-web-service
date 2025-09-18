#!/usr/bin/env python3
"""
Complete notification test: Run actual blog generation and show ALL generated notifications.
This comprehensive test captures everything our enhanced system generates.
"""

import sys
import os
import time
import logging
from typing import List, Dict, Any
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bloggen.flows import BlogGenerationFlow
from core.crewai_stdout_capture import capture_crewai_output


class AllNotificationCollector:
    """Collects and analyzes ALL notifications from actual blog generation"""
    
    def __init__(self):
        self.all_notifications: List[Dict[str, Any]] = []
        self.start_time = time.time()
        
        # Categorized collections
        self.agent_events = []
        self.tool_events = []
        self.image_events = []
        self.status_events = []
        self.crewai_events = []
        self.enhanced_events = []
        self.other_events = []
    
    def collect_notification(self, event: Dict[str, Any]) -> None:
        """Collect and categorize ALL notifications with real-time display"""
        timestamp = time.time() - self.start_time
        
        notification = {
            'timestamp': timestamp,
            'relative_time': f"{timestamp:.1f}s",
            'event': event
        }
        
        self.all_notifications.append(notification)
        
        # Get event details
        event_type = event.get('type', '')
        event_data = event.get('data', {})
        source = event.get('source', 'unknown')
        
        # Real-time display with color coding
        print(f"[{timestamp:6.1f}s] 📢 {event_type}")
        if isinstance(event_data, dict) and event_data:
            for key, value in event_data.items():
                print(f"           {key}: {str(value)[:100]}")
        elif event_data:
            print(f"           data: {str(event_data)[:100]}")
        print()
        
        # Categorize for analysis
        if 'agent' in event_type or 'thinking' in event_type:
            self.agent_events.append(notification)
        elif 'tool' in event_type:
            self.tool_events.append(notification)
        elif any(keyword in event_type for keyword in ['image', 'unsplash', 'openai', 's3', 'ai_generation']):
            self.image_events.append(notification)
        elif 'status' in event_type or 'flow_status' in event_type:
            self.status_events.append(notification)
        
        # Source categorization
        if 'crewai' in source or 'stdout' in source:
            self.crewai_events.append(notification)
        elif 'enhanced' in source or 'logging' in source:
            self.enhanced_events.append(notification)
        else:
            self.other_events.append(notification)
    
    def print_detailed_analysis(self):
        """Print comprehensive analysis of all captured notifications"""
        print("\n" + "="*100)
        print("🔍 COMPLETE NOTIFICATION ANALYSIS - ACTUAL BLOG GENERATION")
        print("="*100)
        
        print(f"\n📊 OVERALL STATISTICS:")
        duration = time.time() - self.start_time
        print(f"📝 Total notifications captured: {len(self.all_notifications)}")
        print(f"⏱️  Test duration: {duration:.1f} seconds")
        print(f"📈 Notification rate: {len(self.all_notifications)/duration:.2f} events/second")
        
        print(f"\n📋 NOTIFICATION CATEGORIES:")
        print(f"  🧠 Agent events: {len(self.agent_events)}")
        print(f"  🔧 Tool events: {len(self.tool_events)}")
        print(f"  🖼️  Image events: {len(self.image_events)}")
        print(f"  📊 Status/Flow events: {len(self.status_events)}")
        print(f"  ❓ Other events: {len(self.other_events)}")
        
        print(f"\n🔍 SOURCE BREAKDOWN:")
        print(f"  🏭 CrewAI/stdout events: {len(self.crewai_events)}")
        print(f"  ⚡ Enhanced/logging events: {len(self.enhanced_events)}")
        print(f"  ❓ Other sources: {len(self.other_events)}")
        
        # Event type frequency analysis
        event_types = {}
        for notification in self.all_notifications:
            event_type = notification['event'].get('type', 'unknown')
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        print(f"\n🏷️  EVENT TYPE FREQUENCY:")
        for event_type, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(self.all_notifications)) * 100
            print(f"  {event_type}: {count} ({percentage:.1f}%)")
        
        # IMAGE EVENTS DEEP DIVE
        if self.image_events:
            print(f"\n🖼️  IMAGE EVENTS DEEP DIVE ({len(self.image_events)} events):")
            for i, notification in enumerate(self.image_events, 1):
                event = notification['event']
                print(f"  {i}. [{notification['relative_time']}] {event.get('type')}")
                if isinstance(event.get('data'), dict):
                    for key, value in event['data'].items():
                        print(f"       {key}: {str(value)[:80]}")
                else:
                    print(f"       data: {str(event.get('data', 'No data'))[:80]}")
                print()
        else:
            print(f"\n❌ NO IMAGE EVENTS CAPTURED!")
            print(f"🔍 Possible reasons:")
            print(f"  - Image tools not running (disabled or no API keys)")
            print(f"  - Image tools using different logging patterns")
            print(f"  - Enhanced capture not integrated with image tools")
        
        # AGENT EVENTS SAMPLE
        if self.agent_events:
            print(f"\n🧠 AGENT EVENTS SAMPLE (showing first 5 of {len(self.agent_events)}):")
            for i, notification in enumerate(self.agent_events[:5], 1):
                event = notification['event']
                print(f"  {i}. [{notification['relative_time']}] {event.get('type')}: {str(event.get('data', {}))[:60]}...")
        
        # TOOL EVENTS SAMPLE
        if self.tool_events:
            print(f"\n🔧 TOOL EVENTS SAMPLE (showing first 5 of {len(self.tool_events)}):")
            for i, notification in enumerate(self.tool_events[:5], 1):
                event = notification['event']
                print(f"  {i}. [{notification['relative_time']}] {event.get('type')}: {str(event.get('data', {}))[:60]}...")
        
        # CHRONOLOGICAL TIMELINE
        print(f"\n⏰ CHRONOLOGICAL TIMELINE (First 15 events):")
        for i, notification in enumerate(self.all_notifications[:15], 1):
            event = notification['event']
            source_emoji = "🏭" if notification in self.crewai_events else "⚡" if notification in self.enhanced_events else "❓"
            print(f"  {i:2d}. [{notification['relative_time']}] {source_emoji} {event.get('type')}: {str(event.get('data', {}))[:50]}...")
        
        if len(self.all_notifications) > 15:
            print(f"  ... and {len(self.all_notifications) - 15} more events")
        
        # Save comprehensive data
        log_filename = f"all_notifications_{int(time.time())}.json"
        with open(log_filename, 'w') as f:
            json.dump({
                'test_metadata': {
                    'test_type': 'comprehensive_blog_generation',
                    'timestamp': time.time(),
                    'duration': duration,
                    'total_notifications': len(self.all_notifications)
                },
                'summary': {
                    'categories': {
                        'agent_events': len(self.agent_events),
                        'tool_events': len(self.tool_events),
                        'image_events': len(self.image_events),
                        'status_events': len(self.status_events),
                        'other_events': len(self.other_events)
                    },
                    'sources': {
                        'crewai_events': len(self.crewai_events),
                        'enhanced_events': len(self.enhanced_events),
                        'other_events': len(self.other_events)
                    },
                    'event_types': event_types
                },
                'all_notifications': self.all_notifications
            }, f, indent=2, default=str)
        
        print(f"\n💾 Complete notification log saved to: {log_filename}")


def run_complete_notification_test():
    """Run actual blog generation and capture ALL notifications"""
    print("🚀 STARTING COMPLETE NOTIFICATION CAPTURE TEST")
    print("="*100)
    print("Running ACTUAL blog generation to capture ALL notifications from our enhanced system.")
    print("This will show us exactly what's being generated vs. what reaches the frontend.")
    print()
    
    collector = AllNotificationCollector()
    
    try:
        # Create status callback for flow events
        def status_callback(step_name: str, progress: int, details: str):
            """Flow status callback - this is what normally goes to frontend"""
            collector.collect_notification({
                'type': 'flow_status',
                'data': {
                    'step_name': step_name,
                    'progress': progress,
                    'details': details
                },
                'source': 'flow_status_callback'
            })
        
        # Initialize blog generation flow
        flow = BlogGenerationFlow(status_callback=status_callback)
        
        print("🔄 Initializing blog generation flow...")
        print("📡 Enhanced capture system is monitoring ALL output...")
        print()
        
        # Use enhanced capture to monitor EVERYTHING
        with capture_crewai_output(collector.collect_notification):
            print("🎯 Starting blog generation on: 'Future of AI in Renewable Energy'")
            print("-" * 80)
            
            # Run actual blog generation
            result = flow.kickoff({
                'topic': 'Future of AI in Renewable Energy',
                'current_year': 2025,
                'user_id': 'test-all-notifications',
                'blog_id': f'complete-test-{int(time.time())}'
            })
            
        print("-" * 80)
        print(f"✅ Blog generation completed!")
        
        if result and 'final_blog_post' in result:
            blog_content = result['final_blog_post']
            print(f"📄 Generated blog post ({len(blog_content)} characters)")
            print(f"📝 First 200 chars: {blog_content[:200]}...")
        else:
            print("❌ No blog content generated")
            
        return collector, result
        
    except Exception as e:
        print(f"\n❌ Blog generation failed: {e}")
        import traceback
        traceback.print_exc()
        return collector, None


def main():
    """Main test execution"""
    print("🧪 COMPLETE NOTIFICATION SYSTEM TEST - ACTUAL BLOG GENERATION")
    print("="*100)
    print("This test runs a real blog generation and captures ALL notifications.")
    print("We'll see exactly what our enhanced system generates and identify any gaps.")
    print()
    
    # Run the complete test
    collector, result = run_complete_notification_test()
    
    # Comprehensive analysis
    collector.print_detailed_analysis()
    
    # Final diagnostic assessment
    print(f"\n🎯 DIAGNOSTIC ASSESSMENT:")
    print("="*50)
    
    if len(collector.all_notifications) > 0:
        print(f"✅ Notification system IS working - captured {len(collector.all_notifications)} total events")
        
        if len(collector.image_events) > 0:
            print(f"✅ Image notifications ARE being captured - {len(collector.image_events)} image events found")
            print(f"   This means image tools are working and our enhanced capture is functional")
        else:
            print(f"❌ Image notifications NOT captured")
            print(f"   Possible causes: Image tools disabled, API keys missing, or different logging patterns")
        
        if len(collector.status_events) > 0:
            print(f"✅ Status events ARE being captured - {len(collector.status_events)} status events")
            print(f"   This means flow callbacks are working")
        
        if len(collector.crewai_events) > 0:
            print(f"✅ CrewAI events ARE being captured - {len(collector.crewai_events)} CrewAI events")
        
        if len(collector.enhanced_events) > 0:
            print(f"✅ Enhanced events ARE being captured - {len(collector.enhanced_events)} enhanced events")
        
    else:
        print(f"❌ NO notifications captured at all!")
        print(f"   System integration may be broken")
    
    print(f"\n📋 NEXT DEBUGGING STEPS:")
    if len(collector.all_notifications) > 0 and len(collector.image_events) == 0:
        print(f"1. Check if image generation is enabled (ENABLE_AI_IMAGE_GENERATION)")
        print(f"2. Verify API keys are configured (OPENAI_API_KEY, UNSPLASH_ACCESS_KEY)")
        print(f"3. Check image tool logging patterns")
    elif len(collector.all_notifications) > 0:
        print(f"1. Backend notifications are working - check frontend SSE delivery")
        print(f"2. Verify flow callback routing to SSE endpoint")
        print(f"3. Check frontend EventSource connection")
    else:
        print(f"1. Check capture_crewai_output integration in flows.py")
        print(f"2. Verify enhanced capture system is properly initialized")
        print(f"3. Check for import or initialization errors")


if __name__ == "__main__":
    main()