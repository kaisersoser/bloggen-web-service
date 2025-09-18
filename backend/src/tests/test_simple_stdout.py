#!/usr/bin/env python3
"""
Simple test for CrewAI stdout capture functionality.
Tests the parsing logic without requiring API calls.
"""

import sys
import os

# Add the src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
sys.path.insert(0, src_dir)

from core.crewai_stdout_capture import CrewAIOutputParser, StdoutCapture
from datetime import datetime

def test_stdout_parsing():
    """Test the stdout parsing logic with mock CrewAI output"""
    
    print("🧪 Testing CrewAI Stdout Parsing")
    print("-" * 50)
    
    captured_events = []
    
    def test_callback(event):
        captured_events.append(event)
        event_type = event.get('type')
        data = event.get('data', {})
        print(f"📢 Captured: {event_type} - {data}")
    
    parser = CrewAIOutputParser(test_callback)
    
    # Test various CrewAI output patterns
    test_outputs = [
        "[Research Agent] I need to analyze the latest trends in AI education",
        "Action: search_web",
        "Action Input: AI education benefits latest research 2024",
        "Observation: Found 15 relevant articles about AI in education",
        "Final Answer: AI offers personalized learning and improved accessibility.",
        "I need to delegate this task to Content Creation Agent",
        "Error: Connection timeout occurred",
        "[Content Agent] Analyzing research findings and structuring content",
        "# Agent: Research Agent\n## Task: Research AI education trends",
        "╭─ Agent Execution Started ─╮",
        "│ Research Agent thinking... │",
        "╰─────────────────────────────╯"
    ]
    
    print("\n🔍 Testing output patterns:")
    for i, output in enumerate(test_outputs, 1):
        print(f"\n{i:2d}. Testing: {output}")
        parser.parse_line(output)
    
    print(f"\n✅ Parsing test completed!")
    print(f"📊 Total events captured: {len(captured_events)}")
    
    print(f"\n📋 Event breakdown:")
    event_types = {}
    for event in captured_events:
        event_type = event.get('type', 'unknown')
        event_types[event_type] = event_types.get(event_type, 0) + 1
    
    for event_type, count in event_types.items():
        print(f"  - {event_type}: {count}")
    
    return captured_events

def test_stdout_capture_context():
    """Test the stdout capture context manager"""
    
    print("\n🎯 Testing Stdout Capture Context Manager")
    print("-" * 50)
    
    captured_events = []
    
    def test_callback(event):
        captured_events.append(event)
        print(f"📤 Context captured: {event.get('type')} - {event.get('data')}")
    
    from core.crewai_stdout_capture import capture_crewai_output
    
    print("🔄 Starting capture context...")
    
    with capture_crewai_output(test_callback):
        # Simulate CrewAI-style output
        print("[Test Agent] Starting analysis of AI benefits")
        print("Action: research_tool")
        print("Action Input: AI education benefits")
        print("Observation: AI improves personalized learning experiences")
        print("Final Answer: AI enhances education through personalization")
        
    print(f"✅ Context capture completed!")
    print(f"📊 Events captured via context: {len(captured_events)}")
    
    return captured_events

if __name__ == "__main__":
    print("🔍 Simple CrewAI Stdout Capture Test")
    print("=" * 60)
    
    # Test parsing logic
    parsing_events = test_stdout_parsing()
    
    # Test context manager
    context_events = test_stdout_capture_context()
    
    print("\n🎯 TEST SUMMARY")
    print(f"Parsing events: {len(parsing_events)}")
    print(f"Context events: {len(context_events)}")
    print(f"Total captured: {len(parsing_events) + len(context_events)}")
    
    if len(parsing_events) > 0 or len(context_events) > 0:
        print("✅ Stdout capture is working!")
    else:
        print("❌ No events captured - check implementation")