#!/usr/bin/env python3
"""
Comprehensive Notification Analysis Script

This script performs a detailed analysis of ALL notification types sent by the backend
versus what was received by the frontend SSE connection tester.

It analyzes:
1. ALL message types sent by backend
2. Message frequency and timing patterns
3. Missing or lost notifications
4. Message structure and field analysis
5. Comprehensive comparison with frontend logs
"""

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Any, Optional

def parse_backend_log(log_file_path: str) -> List[Dict[str, Any]]:
    """Parse the backend test_notifications.log file."""
    notifications = []
    current_notification = {}
    
    with open(log_file_path, 'r') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Check if this is a message type line
        if line and not line.startswith('{') and not line.endswith('PM') and not line.endswith('AM'):
            # This is a message type
            message_type = line
            i += 1
            
            # Next line should be timestamp
            if i < len(lines):
                timestamp_line = lines[i].strip()
                i += 1
                
                # Now collect the JSON
                json_lines = []
                while i < len(lines) and lines[i].strip().startswith(('{', '"', '}', ',', ' ')):
                    json_lines.append(lines[i])
                    i += 1
                
                # Try to parse the JSON
                try:
                    json_str = ''.join(json_lines).strip()
                    if json_str:
                        notification_data = json.loads(json_str)
                        notification_data['_parsed_type'] = message_type
                        notification_data['_parsed_timestamp'] = timestamp_line
                        notifications.append(notification_data)
                except json.JSONDecodeError as e:
                    print(f"Failed to parse JSON for message type {message_type}: {e}")
                    print(f"JSON content: {json_str[:200]}...")
        else:
            i += 1
    
    return notifications

def analyze_backend_notifications(notifications: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze all backend notifications comprehensively."""
    analysis = {
        'total_count': len(notifications),
        'message_types': Counter(),
        'unique_fields': set(),
        'field_analysis': defaultdict(Counter),
        'timeline': [],
        'message_details': defaultdict(list),
        'progress_tracking': [],
        'status_distribution': Counter(),
        'content_phases': []
    }
    
    for notification in notifications:
        # Count message types
        msg_type = notification.get('message_type', notification.get('type', 'unknown'))
        analysis['message_types'][msg_type] += 1
        
        # Collect all unique fields
        for field in notification.keys():
            analysis['unique_fields'].add(field)
            analysis['field_analysis'][field][str(notification[field])] += 1
        
        # Timeline analysis
        if 'timestamp' in notification:
            analysis['timeline'].append({
                'timestamp': notification['timestamp'],
                'type': msg_type,
                'message': notification.get('message', ''),
                'step': notification.get('step', ''),
                'progress': notification.get('progress', 0)
            })
        
        # Store message details by type
        analysis['message_details'][msg_type].append(notification)
        
        # Progress tracking
        if 'progress' in notification:
            analysis['progress_tracking'].append({
                'timestamp': notification.get('timestamp'),
                'progress': notification['progress'],
                'step': notification.get('step', ''),
                'type': msg_type
            })
        
        # Status distribution
        if 'status' in notification:
            analysis['status_distribution'][notification['status']] += 1
        
        # Content phase detection
        message = notification.get('message', '').lower()
        step = notification.get('step', '').lower()
        
        if any(keyword in message + step for keyword in ['research', 'searching', 'finding']):
            analysis['content_phases'].append(('research', notification))
        elif any(keyword in message + step for keyword in ['draft', 'content', 'writing', 'generating']):
            analysis['content_phases'].append(('content_generation', notification))
        elif any(keyword in message + step for keyword in ['fact', 'check', 'validat', 'verify']):
            analysis['content_phases'].append(('fact_checking', notification))
        elif any(keyword in message + step for keyword in ['final', 'clean', 'complete', 'deliver']):
            analysis['content_phases'].append(('finalization', notification))
    
    return analysis

def compare_with_frontend_expectations(backend_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Compare backend notifications with what frontend SSE tester expects."""
    
    # Expected message types from frontend SSE connection code
    expected_frontend_types = {
        'status', 'statusUpdate', 'taskcreated', 'initializing', 'agentthinking',
        'toolcall', 'toolresult', 'contentstream', 'researchfinding', 'contentdraft',
        'factcheck', 'revision', 'heroImage', 'completed', 'error', 'logUpdate',
        'streamEnded', 'connected'
    }
    
    backend_types = set(backend_analysis['message_types'].keys())
    
    comparison = {
        'backend_types': backend_types,
        'expected_frontend_types': expected_frontend_types,
        'matching_types': backend_types.intersection(expected_frontend_types),
        'backend_only_types': backend_types - expected_frontend_types,
        'frontend_only_types': expected_frontend_types - backend_types,
        'type_mapping_issues': []
    }
    
    # Check for potential mapping issues
    for backend_type in backend_types:
        if backend_type not in expected_frontend_types:
            # Look for similar names
            similar = [ft for ft in expected_frontend_types 
                      if backend_type.lower() in ft.lower() or ft.lower() in backend_type.lower()]
            if similar:
                comparison['type_mapping_issues'].append({
                    'backend_type': backend_type,
                    'potential_frontend_matches': similar
                })
    
    return comparison

def generate_comprehensive_report(backend_log_path: str) -> str:
    """Generate a comprehensive analysis report."""
    
    print("🔍 Parsing backend notifications...")
    notifications = parse_backend_log(backend_log_path)
    
    print("📊 Analyzing notification patterns...")
    analysis = analyze_backend_notifications(notifications)
    
    print("🔀 Comparing with frontend expectations...")
    comparison = compare_with_frontend_expectations(analysis)
    
    # Generate report
    report = []
    report.append("=" * 80)
    report.append("🔍 COMPREHENSIVE NOTIFICATION ANALYSIS REPORT")
    report.append("=" * 80)
    report.append(f"Analysis Date: {datetime.now().isoformat()}")
    report.append(f"Backend Log: {backend_log_path}")
    report.append("")
    
    # Overall Statistics
    report.append("📊 OVERALL STATISTICS")
    report.append("-" * 40)
    report.append(f"Total Notifications Sent: {analysis['total_count']}")
    report.append(f"Unique Message Types: {len(analysis['message_types'])}")
    report.append(f"Unique Fields Used: {len(analysis['unique_fields'])}")
    report.append("")
    
    # Message Type Breakdown
    report.append("📝 MESSAGE TYPE BREAKDOWN")
    report.append("-" * 40)
    for msg_type, count in analysis['message_types'].most_common():
        percentage = (count / analysis['total_count']) * 100
        report.append(f"  {msg_type:20} : {count:3d} messages ({percentage:5.1f}%)")
    report.append("")
    
    # Frontend Compatibility Analysis
    report.append("🔗 FRONTEND COMPATIBILITY ANALYSIS")
    report.append("-" * 40)
    report.append(f"Backend Types Found: {sorted(comparison['backend_types'])}")
    report.append(f"Frontend Expected Types: {sorted(comparison['expected_frontend_types'])}")
    report.append("")
    report.append(f"✅ Matching Types ({len(comparison['matching_types'])}): {sorted(comparison['matching_types'])}")
    report.append(f"❌ Backend-Only Types ({len(comparison['backend_only_types'])}): {sorted(comparison['backend_only_types'])}")
    report.append(f"⚠️  Frontend-Only Types ({len(comparison['frontend_only_types'])}): {sorted(comparison['frontend_only_types'])}")
    report.append("")
    
    if comparison['type_mapping_issues']:
        report.append("🔧 POTENTIAL TYPE MAPPING ISSUES")
        report.append("-" * 40)
        for issue in comparison['type_mapping_issues']:
            report.append(f"  Backend: '{issue['backend_type']}' → Potential Frontend: {issue['potential_frontend_matches']}")
        report.append("")
    
    # Field Analysis
    report.append("🔬 FIELD ANALYSIS")
    report.append("-" * 40)
    for field in sorted(analysis['unique_fields']):
        if not field.startswith('_'):  # Skip our internal fields
            unique_values = len(analysis['field_analysis'][field])
            report.append(f"  {field:20} : {unique_values} unique values")
    report.append("")
    
    # Progress Tracking
    if analysis['progress_tracking']:
        progress_values = [p['progress'] for p in analysis['progress_tracking']]
        report.append("📈 PROGRESS TRACKING")
        report.append("-" * 40)
        report.append(f"  Progress Updates: {len(progress_values)}")
        report.append(f"  Progress Range: {min(progress_values)} - {max(progress_values)}")
        report.append(f"  Unique Progress Values: {len(set(progress_values))}")
        report.append("")
    
    # Content Phases
    if analysis['content_phases']:
        phase_counts = Counter(phase[0] for phase in analysis['content_phases'])
        report.append("🔄 CONTENT GENERATION PHASES")
        report.append("-" * 40)
        for phase, count in phase_counts.items():
            report.append(f"  {phase:20} : {count} notifications")
        report.append("")
    
    # Critical Findings
    report.append("🚨 CRITICAL FINDINGS")
    report.append("-" * 40)
    
    # Check for missing notification types
    missing_critical = []
    if 'agentthinking' not in comparison['matching_types']:
        missing_critical.append("No 'agentthinking' notifications (agent activity)")
    if 'toolcall' not in comparison['matching_types']:
        missing_critical.append("No 'toolcall' notifications (tool usage)")
    if 'researchfinding' not in comparison['matching_types']:
        missing_critical.append("No 'researchfinding' notifications (research phase)")
    if 'contentdraft' not in comparison['matching_types']:
        missing_critical.append("No 'contentdraft' notifications (content creation)")
    if 'heroImage' not in comparison['matching_types']:
        missing_critical.append("No 'heroImage' notifications (image events)")
    
    if missing_critical:
        for finding in missing_critical:
            report.append(f"  ❌ {finding}")
    else:
        report.append("  ✅ All critical notification types present")
    report.append("")
    
    # Timeline Analysis
    if analysis['timeline']:
        report.append("⏰ TIMELINE ANALYSIS")
        report.append("-" * 40)
        first_timestamp = analysis['timeline'][0]['timestamp']
        last_timestamp = analysis['timeline'][-1]['timestamp']
        report.append(f"  First Notification: {first_timestamp}")
        report.append(f"  Last Notification: {last_timestamp}")
        report.append(f"  Duration: {len(analysis['timeline'])} notifications")
        report.append("")
    
    # Recommendations
    report.append("💡 RECOMMENDATIONS")
    report.append("-" * 40)
    
    if comparison['backend_only_types']:
        report.append("  1. Add frontend handlers for backend-only message types:")
        for msg_type in sorted(comparison['backend_only_types']):
            report.append(f"     - {msg_type}")
        report.append("")
    
    if comparison['frontend_only_types']:
        report.append("  2. Consider if these frontend-expected types should be sent:")
        for msg_type in sorted(comparison['frontend_only_types']):
            report.append(f"     - {msg_type}")
        report.append("")
    
    if not missing_critical:
        report.append("  3. ✅ Notification system appears comprehensive")
        report.append("  4. 🔍 Focus on frontend display logic and UI integration")
        report.append("  5. 📊 Check frontend message filtering and categorization")
    
    report.append("")
    report.append("=" * 80)
    
    return "\n".join(report)

if __name__ == "__main__":
    backend_log_path = "/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/test_notifications.log"
    
    try:
        report = generate_comprehensive_report(backend_log_path)
        print(report)
        
        # Save report to file
        report_path = "/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/frontend-nextjs/blog-generator-ui/src/docs/NOTIFICATION_ANALYSIS_REPORT.md"
        with open(report_path, 'w') as f:
            f.write(f"# Comprehensive Notification Analysis Report\n\n```\n{report}\n```")
        
        print(f"\n📄 Report saved to: {report_path}")
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        import traceback
        traceback.print_exc()