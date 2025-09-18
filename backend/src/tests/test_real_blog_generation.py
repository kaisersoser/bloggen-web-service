#!/usr/bin/env python3
"""
Real Blog Generation Test with Enhanced Notifications

Tests our stdout capture wrapper with actual CrewAI blog generation
to see what detailed notifications are captured during real execution.
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
        logging.FileHandler('real_blog_test.log')
    ]
)

logger = logging.getLogger(__name__)

# Import our systems
from core.context_vars import set_request_context
from bloggen.flows import BlogGenerationFlow
from datetime import datetime


class RealBlogNotificationCollector:
    """Collects notifications during real blog generation with detailed analysis"""
    
    def __init__(self):
        self.notifications = []
        self.start_time = datetime.now()
        self.phases = {}
        self.current_phase = None
    
    def collect_notification(self, notification: Dict[str, Any]):
        """Collect and analyze notifications from real blog generation"""
        timestamp = datetime.now()
        elapsed = (timestamp - self.start_time).total_seconds()
        
        # Extract notification details
        msg_type = notification.get('message_type', 'unknown')
        message = notification.get('message', '')
        step = notification.get('step', '')
        progress = notification.get('progress', 0)
        
        # Track phase transitions
        if 'research' in message.lower() or 'Research' in step:
            self.current_phase = 'research'
        elif 'content' in message.lower() or 'Content' in step:
            self.current_phase = 'content_generation'
        elif 'fact' in message.lower() or 'Fact' in step:
            self.current_phase = 'fact_checking'
        elif 'final' in message.lower() or 'Final' in step:
            self.current_phase = 'finalization'
        
        # Store notification with analysis
        collected = {
            'timestamp': timestamp.isoformat(),
            'elapsed_seconds': elapsed,
            'phase': self.current_phase,
            'notification': notification,
            'msg_type': msg_type,
            'progress': progress
        }
        
        self.notifications.append(collected)
        
        # Track phase statistics
        if self.current_phase:
            if self.current_phase not in self.phases:
                self.phases[self.current_phase] = {
                    'start_time': elapsed,
                    'notifications': 0,
                    'agent_thoughts': 0,
                    'tool_uses': 0
                }
            
            self.phases[self.current_phase]['notifications'] += 1
            
            if msg_type == 'agentthinking':
                self.phases[self.current_phase]['agent_thoughts'] += 1
            elif msg_type == 'toolcall':
                self.phases[self.current_phase]['tool_uses'] += 1
        
        # Real-time logging with emojis for different types
        emoji_map = {
            'status': '📊',
            'agentthinking': '🧠',
            'toolcall': '🔧',
            'crewai_event': '⚙️',
            'phase_transition': '🔄',
            'progress': '📈'
        }
        
        emoji = emoji_map.get(msg_type, '📢')
        content = message or notification.get('thought', notification.get('tool_name', 'N/A'))
        
        logger.info(f"{emoji} [{elapsed:6.1f}s] [{self.current_phase or 'init':15s}] {content[:100]}")
    
    def print_detailed_summary(self):
        """Print comprehensive analysis of the blog generation process"""
        total_time = (datetime.now() - self.start_time).total_seconds()
        
        print("\n" + "="*100)
        print("🎯 REAL BLOG GENERATION ANALYSIS")
        print("="*100)
        print(f"📊 Total execution time: {total_time:.1f} seconds")
        print(f"📢 Total notifications: {len(self.notifications)}")
        print(f"🔄 Phases detected: {len(self.phases)}")
        
        # Phase breakdown
        print(f"\n📋 PHASE BREAKDOWN:")
        for phase, stats in self.phases.items():
            duration = total_time - stats['start_time']
            print(f"  🔸 {phase.upper()}")
            print(f"    ⏱️  Duration: ~{duration:.1f}s")
            print(f"    📢 Notifications: {stats['notifications']}")
            print(f"    🧠 Agent thoughts: {stats['agent_thoughts']}")
            print(f"    🔧 Tool uses: {stats['tool_uses']}")
        
        # Notification types
        print(f"\n📊 NOTIFICATION TYPES:")
        type_counts = {}
        for notif in self.notifications:
            msg_type = notif['msg_type']
            type_counts[msg_type] = type_counts.get(msg_type, 0) + 1
        
        for msg_type, count in sorted(type_counts.items()):
            percentage = (count / len(self.notifications)) * 100
            print(f"  📌 {msg_type:20s}: {count:3d} ({percentage:5.1f}%)")
        
        # Timeline of key events
        print(f"\n⏰ KEY EVENTS TIMELINE:")
        key_events = [n for n in self.notifications if n['msg_type'] in ['agentthinking', 'toolcall', 'phase_transition']]
        
        for i, event in enumerate(key_events[:20], 1):  # Show first 20 key events
            elapsed = event['elapsed_seconds']
            phase = event['phase'] or 'init'
            notification = event['notification']
            content = (notification.get('message') or 
                      notification.get('thought') or 
                      notification.get('tool_name') or 'N/A')[:80]
            
            print(f"  {i:2d}. [{elapsed:6.1f}s] [{phase:15s}] {content}")
        
        if len(key_events) > 20:
            print(f"     ... and {len(key_events) - 20} more events")
        
        # Performance metrics
        print(f"\n📈 PERFORMANCE METRICS:")
        if self.notifications:
            avg_interval = total_time / len(self.notifications)
            print(f"  📊 Average notification interval: {avg_interval:.2f}s")
            
            progress_notifications = [n for n in self.notifications if n['progress'] > 0]
            if progress_notifications:
                max_progress = max(n['progress'] for n in progress_notifications)
                print(f"  🎯 Maximum progress reached: {max_progress}%")


def test_real_blog_generation():
    """Test enhanced notifications with real blog generation"""
    
    print("🚀 Starting Real Blog Generation Test")
    print("=" * 60)
    
    # Set up test context
    task_id = f"real-test-{int(datetime.now().timestamp())}"
    
    set_request_context(
        request_id=f"req-{task_id}",
        task_id=task_id,
        user_id="test-user",
        user_email="test@example.com",
        user_role="ADMIN",
        blog_id=task_id,
        topic="AI in Modern Education"
    )
    
    # Create notification collector
    collector = RealBlogNotificationCollector()
    
    def status_callback(notification: Dict[str, Any]):
        collector.collect_notification(notification)
    
    # Create flow for real blog generation
    flow = BlogGenerationFlow(
        status_callback=status_callback,
        user_id="test-user",
        blog_id=task_id,
        topic="AI in Modern Education: Transforming Learning in 2024"
    )
    
    print(f"📝 Topic: {flow.flow_state.topic}")
    print(f"🆔 Task ID: {task_id}")
    print(f"⏰ Start time: {datetime.now().strftime('%H:%M:%S')}")
    print("\n🔄 Starting blog generation with enhanced notifications...")
    print("-" * 60)
    
    try:
        # Run the real blog generation flow
        result = flow.kickoff()
        
        print("\n" + "="*60)
        print("✅ BLOG GENERATION COMPLETED!")
        
        if result:
            # Extract the final blog content
            if hasattr(result, 'raw'):
                blog_content = result.raw
            else:
                blog_content = str(result)
            
            print(f"📄 Blog length: {len(blog_content)} characters")
            print(f"📝 Blog preview: {blog_content[:200]}...")
            
            # Save the generated blog for review
            with open(f'generated_blog_{task_id}.txt', 'w') as f:
                f.write(f"Generated Blog - {datetime.now()}\n")
                f.write("="*50 + "\n\n")
                f.write(blog_content)
            
            print(f"💾 Full blog saved to: generated_blog_{task_id}.txt")
        else:
            print("❌ No blog content generated")
        
    except Exception as e:
        print(f"\n❌ ERROR during blog generation: {e}")
        import traceback
        traceback.print_exc()
    
    # Print detailed analysis
    collector.print_detailed_summary()
    
    return collector.notifications


if __name__ == "__main__":
    print("🔍 Real Blog Generation Test with Enhanced Notifications")
    print("=" * 80)
    print("This test will generate a real blog and capture all CrewAI notifications")
    print("⚠️  Note: This will make actual API calls and may take 2-5 minutes")
    print("=" * 80)
    
    # Confirm before running
    input("Press ENTER to start real blog generation test...")
    
    start_time = datetime.now()
    
    # Run the test
    notifications = test_real_blog_generation()
    
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    
    print(f"\n🎯 FINAL SUMMARY")
    print(f"⏱️  Total test duration: {total_duration:.1f} seconds")
    print(f"📢 Total notifications captured: {len(notifications)}")
    print(f"📊 Notification rate: {len(notifications)/total_duration:.2f} notifications/second")
    print(f"📋 Check 'real_blog_test.log' for detailed logs")
    
    if len(notifications) > 0:
        print("✅ Enhanced notification system is working with real blog generation!")
    else:
        print("❌ No notifications captured - check implementation")