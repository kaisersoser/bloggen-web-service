#!/usr/bin/env python3
# flake8: noqa
"""
Test script to verify enhanced notifications are working properly.
"""

import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "."))


def test_enhanced_notifications():
    """Test that enhanced notifications work end-to-end."""
    print("🧪 Testing Enhanced Notification System...")

    try:
        # Import our enhanced components
        from bloggen.status_manager import StatusUpdateManager
        from core.sse_message_types import (
            create_agent_thinking_message,
            create_tool_call_message,
            create_content_stream_message,
            create_research_finding_message,
        )

        print("✅ All imports successful")

        # Track received messages
        received_messages = []

        def mock_status_callback(message_data):
            """Mock callback to capture messages."""
            received_messages.append(message_data)
            message_type = message_data.get("message_type", "unknown")
            print(f"📨 Received {message_type}: {message_data}")

        # Create StatusUpdateManager with mock callback
        status_manager = StatusUpdateManager(
            status_callback=mock_status_callback, task_id="test-task-123"
        )

        print("✅ StatusUpdateManager created")

        # Test enhanced notification methods
        print("\n🧠 Testing agent thinking...")
        status_manager.send_agent_thinking(
            agent_name="Test Agent",
            thought="I'm testing the enhanced notification system to ensure agent thinking is properly broadcast.",
        )

        print("\n🔧 Testing tool usage...")
        status_manager.send_tool_usage(
            tool_name="TestTool",
            input_summary="Testing tool with sample input for enhanced notifications",
            agent_name="Test Agent",
        )

        print("\n📄 Testing content streaming...")
        status_manager.send_content_stream(
            content_type="introduction",
            content="This is a test content stream for enhanced notifications system.",
            is_partial=False,
        )

        print("\n🔍 Testing research findings...")
        status_manager.send_research_finding(
            finding="Test research finding: Enhanced notifications are working properly!",
            source="Test Source",
        )

        # Verify we received all messages
        expected_types = [
            "agentthinking",
            "toolcall",
            "contentstream",
            "researchfinding",
        ]
        received_types = [
            msg.get("message_type", "unknown") for msg in received_messages
        ]

        print(f"\n📊 Test Results:")
        print(f"   Expected types: {expected_types}")
        print(f"   Received types: {received_types}")

        missing_types = set(expected_types) - set(received_types)
        if missing_types:
            print(f"❌ Missing message types: {missing_types}")
            return False

        print("✅ All enhanced notification types working!")

        # Test message structure
        for msg in received_messages:
            required_fields = ["message_type", "task_id", "timestamp"]
            for field in required_fields:
                if field not in msg:
                    print(f"❌ Missing required field '{field}' in message: {msg}")
                    return False

        print("✅ All messages have required fields!")

        return True

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_enhanced_notifications()
    if success:
        print("\n🎉 Enhanced Notification System Test: PASSED")
        sys.exit(0)
    else:
        print("\n💥 Enhanced Notification System Test: FAILED")
        sys.exit(1)
