#!/usr/bin/env python3
"""
Quick notification capture test to see what types of notifications we receive.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.crewai_stdout_capture import capture_crewai_output
from bloggen.flows import BlogGenerationFlow
import time
import re

def main():
    print('=== Quick Notification Capture Test ===')
    
    # Store all notifications
    all_notifications = []
    notification_types = {
        'status_callbacks': [],
        'agent_activity': [],
        'tool_usage': [],
        'image_events': [],
        'content_processing': [],
        'research_activity': [],
        'errors_warnings': [],
        'other': []
    }
    
    def status_callback(step_name, progress, details):
        """Capture status callback notifications"""
        timestamp = time.time()
        notification = {
            'timestamp': timestamp,
            'type': 'status_callback',
            'step': step_name,
            'progress': progress,
            'details': details
        }
        all_notifications.append(notification)
        notification_types['status_callbacks'].append(notification)
        print(f'📢 STATUS: {step_name} ({progress}%) - {details}')
    
    def capture_notification(output):
        """Capture stdout notifications and categorize them"""
        timestamp = time.time()
        content = output.strip()
        
        notification = {
            'timestamp': timestamp,
            'type': 'stdout_capture',
            'content': content
        }
        all_notifications.append(notification)
        
        # Categorize the notification
        content_lower = content.lower()
        
        if any(keyword in content_lower for keyword in ['agent', 'researcher', 'content creator', 'fact checker', 'finalizer']):
            notification_types['agent_activity'].append(notification)
            print(f'🤖 AGENT: {content[:80]}...')
        elif any(keyword in content_lower for keyword in ['tool', 'search', 'serper', 'unsplash']):
            notification_types['tool_usage'].append(notification)
            print(f'🔧 TOOL: {content[:80]}...')
        elif any(keyword in content_lower for keyword in ['image', 'photo', 'unsplash', 'dall-e', 'visual']):
            notification_types['image_events'].append(notification)
            print(f'🖼️ IMAGE: {content[:80]}...')
        elif any(keyword in content_lower for keyword in ['content', 'writing', 'blog', 'article']):
            notification_types['content_processing'].append(notification)
            print(f'📝 CONTENT: {content[:80]}...')
        elif any(keyword in content_lower for keyword in ['research', 'findings', 'data', 'information']):
            notification_types['research_activity'].append(notification)
            print(f'🔍 RESEARCH: {content[:80]}...')
        elif any(keyword in content_lower for keyword in ['error', 'warning', 'failed', 'exception']):
            notification_types['errors_warnings'].append(notification)
            print(f'⚠️ ERROR: {content[:80]}...')
        else:
            notification_types['other'].append(notification)
            print(f'📋 OTHER: {content[:80]}...')
    
    # Start a simple blog generation using kickoff
    topic = 'AI notification system testing'
    flow = BlogGenerationFlow(status_callback=status_callback)
    
    print(f'Starting blog generation for topic: {topic}')
    print('Capturing notifications for 2 minutes...\n')
    
    try:
        start_time = time.time()
        with capture_crewai_output(capture_notification):
            # Run the full flow
            result = flow.kickoff({
                'topic': topic,
                'current_year': 2025,
                'user_id': 'quick-test-user',
                'blog_id': 'quick-test-001'
            })
            print(f'\nBlog generation completed successfully!')
            print(f'📄 Blog length: {len(str(result.get("final_blog_post", "")))} characters')
            
    except Exception as e:
        print(f'\nError during execution: {e}')
    
    # Print comprehensive summary
    print(f'\n=== COMPREHENSIVE NOTIFICATION SUMMARY ===')
    print(f'Total execution time: {time.time() - start_time:.1f} seconds')
    print(f'Total notifications captured: {len(all_notifications)}')
    print(f'Notification rate: {len(all_notifications)/(time.time() - start_time):.1f} notifications/second')
    
    print(f'\n📊 NOTIFICATION BREAKDOWN BY TYPE:')
    for category, notifications in notification_types.items():
        count = len(notifications)
        print(f'  {category}: {count} notifications')
        if count > 0 and count <= 3:
            # Show examples for small counts
            for i, notif in enumerate(notifications):
                if notif['type'] == 'status_callback':
                    print(f'    {i+1}. [{notif["step"]}] {notif["details"]}')
                else:
                    print(f'    {i+1}. {notif["content"][:100]}...')
    
    print(f'\n📈 RECENT NOTIFICATIONS (Last 10):')
    for i, notif in enumerate(all_notifications[-10:]):
        if notif['type'] == 'status_callback':
            print(f'  {i+1}. [{notif["step"]}] {notif["details"]} ({notif["progress"]}%)')
        else:
            print(f'  {i+1}. {notif["content"][:100]}...')
    
    print(f'\n🎯 KEY INSIGHTS:')
    print(f'  - Status callbacks: {len(notification_types["status_callbacks"])} (flow progress)')
    print(f'  - Agent activity: {len(notification_types["agent_activity"])} (AI agent actions)')
    print(f'  - Tool usage: {len(notification_types["tool_usage"])} (external API calls)')
    print(f'  - Image events: {len(notification_types["image_events"])} (image processing)')
    print(f'  - Content processing: {len(notification_types["content_processing"])} (blog creation)')
    print(f'  - Research activity: {len(notification_types["research_activity"])} (information gathering)')
    print(f'  - Errors/warnings: {len(notification_types["errors_warnings"])} (issues detected)')
    print(f'  - Other: {len(notification_types["other"])} (miscellaneous)')
    
    print(f'\n✅ Notification capture test completed successfully!')
    return len(all_notifications)

if __name__ == '__main__':
    main()