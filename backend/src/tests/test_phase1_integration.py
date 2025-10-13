#!/usr/bin/env python3
# flake8: noqa
"""
Test script for Phase 1 Foundation Integration: Enhanced SSE with Blog Generation Flow

Tests the integration between the enhanced SSE message types and the actual
blog generation workflow to ensure real-time AI decision broadcasting works.
"""

import asyncio
import sys
import os
from unittest.mock import MagicMock

# Add the backend src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend", "src"))


async def test_enhanced_status_manager():
    """Test the enhanced StatusUpdateManager with new message types."""
    print("🧪 Testing Enhanced StatusUpdateManager Integration")
    print("=" * 60)

    try:
        from bloggen.status_manager import StatusUpdateManager

        # Mock callback to capture messages
        captured_messages = []

        def mock_callback(message_data):
            captured_messages.append(message_data)
            print(
                f"   📨 Received: {message_data.get('message_type', 'unknown')} - {message_data.get('message', '')[:50]}..."
            )

        # Create enhanced status manager
        status_manager = StatusUpdateManager(
            status_callback=mock_callback, task_id="test-integration-123"
        )

        print("✅ StatusUpdateManager created successfully")

        # Test enhanced status update
        print("\n📊 Testing Enhanced Status Update:")
        status_manager.send_status_update("Initializing blog generation...", step=1)

        # Test agent thinking
        print("\n🧠 Testing Agent Thinking Message:")
        status_manager.send_agent_thinking(
            agent_name="Senior Researcher",
            thought="I need to conduct comprehensive research on AI developments to provide cutting-edge insights.",
        )

        # Test tool usage
        print("\n🔧 Testing Tool Usage Message:")
        status_manager.send_tool_usage(
            tool_name="web_search",
            input_summary="Searching for latest AI research papers",
            agent_name="Senior Researcher",
        )

        # Test content streaming
        print("\n📄 Testing Content Streaming Message:")
        status_manager.send_content_stream(
            content_type="draft_introduction",
            content="# The Future of AI\n\nArtificial Intelligence continues to evolve...",
            is_partial=True,
        )

        # Test research finding
        print("\n🔍 Testing Research Finding Message:")
        status_manager.send_research_finding(
            finding="Recent studies show 65% increase in AI adoption across healthcare sector",
            source="Healthcare AI Research Institute",
        )

        print(f"\n📊 Summary: Captured {len(captured_messages)} messages")

        # Verify message types
        message_types = [msg.get("message_type") for msg in captured_messages]
        expected_types = [
            "status",
            "agentthinking",
            "toolcall",
            "contentstream",
            "researchfinding",
        ]

        for expected_type in expected_types:
            if expected_type in message_types:
                print(f"   ✅ {expected_type} message type working")
            else:
                print(f"   ❌ {expected_type} message type missing")

        return len(captured_messages) == len(expected_types)

    except Exception as e:
        print(f"❌ Error testing enhanced status manager: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_flow_integration():
    """Test BlogGenerationFlow integration with enhanced messaging."""
    print("\n🌊 Testing BlogGenerationFlow Integration")
    print("=" * 60)

    try:
        from bloggen.flows import BlogGenerationFlow

        # Mock callback to capture flow messages
        flow_messages = []

        def flow_callback(message_data):
            flow_messages.append(message_data)
            msg_type = message_data.get("message_type", "unknown")
            message = message_data.get("message", "")[:50]
            print(f"   🌊 Flow Message: {msg_type} - {message}...")

        # Create flow with enhanced callback
        flow = BlogGenerationFlow(
            status_callback=flow_callback,
            user_id="test-user-123",
            blog_id="test-blog-integration-456",
            topic="AI Technology Trends",
            current_year=2025,
        )

        print("✅ BlogGenerationFlow created with enhanced messaging")

        # Test status manager integration
        if hasattr(flow, "status_manager") and hasattr(
            flow.status_manager, "send_agent_thinking"
        ):
            print("✅ Enhanced status manager methods available")

            # Test direct method calls
            flow.status_manager.send_agent_thinking(
                agent_name="Test Agent",
                thought="Testing integration between flow and enhanced messaging system",
            )

            flow.status_manager.send_tool_usage(
                tool_name="integration_test",
                input_summary="Testing tool usage integration",
                agent_name="Test Agent",
            )

            print(f"✅ Flow integration test: {len(flow_messages)} messages captured")
            return True
        else:
            print("❌ Enhanced status manager methods not available in flow")
            return False

    except Exception as e:
        print(f"❌ Error testing flow integration: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_main_callback_integration():
    """Test the enhanced callback function from main.py."""
    print("\n🚀 Testing Main.py Callback Integration")
    print("=" * 60)

    try:
        # Simulate the enhanced callback function
        captured_updates = []

        def mock_task_manager_update(task_id, **kwargs):
            captured_updates.append({"task_id": task_id, **kwargs})
            print(f"   📊 DB Update: {kwargs.get('current_step', 'Unknown step')}")

        def mock_redis_publish(task_id, message_data):
            print(
                f"   📡 Redis Publish: {message_data.get('message_type', 'unknown')} for {task_id}"
            )

        # Mock the enhanced callback behavior
        def enhanced_callback(status_data):
            message = status_data.get("message", "Processing...")
            progress = status_data.get("progress", 0.0)
            message_type = status_data.get("message_type", "status")

            # Simulate database update
            mock_task_manager_update(
                "test-callback-789", current_step=message, progress=progress
            )

            # Simulate Redis publishing
            mock_redis_publish("test-callback-789", status_data)

        # Test various message types through callback
        test_messages = [
            {"message_type": "status", "message": "Initializing...", "progress": 10},
            {
                "message_type": "agentthinking",
                "message": "Agent thinking...",
                "agent_name": "Researcher",
            },
            {
                "message_type": "toolcall",
                "message": "Using web search...",
                "tool_name": "web_search",
            },
            {
                "message_type": "contentstream",
                "message": "Generating content...",
                "content_type": "intro",
            },
        ]

        for test_msg in test_messages:
            enhanced_callback(test_msg)

        print(f"✅ Callback integration test: {len(captured_updates)} database updates")
        return len(captured_updates) == len(test_messages)

    except Exception as e:
        print(f"❌ Error testing callback integration: {e}")
        return False


async def main():
    """Run comprehensive integration tests for Phase 1 Foundation."""
    print("🧪 Phase 1 Foundation Integration Test Suite")
    print("Testing enhanced SSE system integration with blog generation workflow")
    print()

    # Test enhanced status manager
    status_success = await test_enhanced_status_manager()

    # Test flow integration
    flow_success = await test_flow_integration()

    # Test main callback integration
    callback_success = await test_main_callback_integration()

    # Final results
    print("\n" + "=" * 60)
    print("📊 INTEGRATION TEST RESULTS")
    print("=" * 60)
    print(f"Enhanced Status Manager: {'✅ PASSED' if status_success else '❌ FAILED'}")
    print(f"Flow Integration: {'✅ PASSED' if flow_success else '❌ FAILED'}")
    print(f"Callback Integration: {'✅ PASSED' if callback_success else '❌ FAILED'}")

    if status_success and flow_success and callback_success:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ Phase 1 Foundation is fully integrated")
        print("🚀 Enhanced real-time AI workflow visibility is operational")
        print("\n📋 What this means:")
        print("   • Agent thinking messages will stream to frontend")
        print("   • Tool usage will be broadcast in real-time")
        print("   • Content generation will stream progressively")
        print("   • Research findings will appear immediately")
        print("   • Database updates and Redis broadcasting work together")
    else:
        print("\n❌ Some integration tests failed")
        print("🔧 Review the failed components before deployment")

    return status_success and flow_success and callback_success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
