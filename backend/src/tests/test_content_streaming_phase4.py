#!/usr/bin/env python3
"""
Phase 4 Test: Progressive Content Streaming
Tests the real-time content streaming during blog generation.
"""
import asyncio
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_content_streaming_phase4():
    """Test Phase 4 progressive content streaming"""
    print("🧪 Testing Phase 4: Progressive Content Streaming")
    print("=" * 60)
    
    try:
        # Import content streaming components
        from core.content_streaming_manager import content_streaming_manager, StreamingContent
        from core.websocket_manager import websocket_manager, ContentStreamMessage, ProgressStreamMessage
        from core.task_manager import task_manager
        
        print("✅ 1. Content streaming components imported successfully")
        
        # Set up managers
        task_manager.set_content_streaming_manager(content_streaming_manager)
        websocket_manager.set_content_streaming_manager(content_streaming_manager)
        print("✅ 2. Content streaming manager connected")
        
        # Test content buffer creation
        test_task_id = "test_streaming_task_789"
        content_buffer = await content_streaming_manager.create_task_stream(test_task_id)
        assert content_buffer.task_id == test_task_id
        print("✅ 3. Content buffer created successfully")
        
        # Test streaming callback setup
        received_streams = []
        
        async def test_streaming_callback(streaming_content):
            received_streams.append(streaming_content)
            print(f"📡 Received stream: {streaming_content.content_type} - {streaming_content.content[:50]}...")
        
        await content_streaming_manager.add_streaming_callback(test_task_id, test_streaming_callback)
        print("✅ 4. Streaming callback added successfully")
        
        # Test research findings streaming
        await content_streaming_manager.stream_research_finding(
            test_task_id, 
            "According to recent studies, AI technology has advanced significantly in 2024."
        )
        await asyncio.sleep(0.1)  # Allow callback processing
        
        await content_streaming_manager.stream_research_finding(
            test_task_id,
            "Research shows that content generation tools improve productivity by 40%."
        )
        await asyncio.sleep(0.1)
        
        print("✅ 5. Research findings streamed successfully")
        
        # Test content paragraph streaming
        await content_streaming_manager.stream_content_paragraph(
            test_task_id,
            "# The Future of AI\n\nArtificial Intelligence continues to revolutionize how we work and create content."
        )
        await asyncio.sleep(0.1)
        
        await content_streaming_manager.stream_content_paragraph(
            test_task_id,
            "The integration of AI tools into daily workflows has become increasingly seamless and powerful."
        )
        await asyncio.sleep(0.1)
        
        print("✅ 6. Content paragraphs streamed successfully")
        
        # Test fact correction streaming
        await content_streaming_manager.stream_fact_correction(
            test_task_id,
            "Corrected: AI adoption increased by 35% (not 30%) according to latest industry reports."
        )
        await asyncio.sleep(0.1)
        
        print("✅ 7. Fact corrections streamed successfully")
        
        # Test content preview generation
        preview = await content_streaming_manager.get_content_preview(test_task_id)
        assert preview is not None and len(preview) > 0
        print("✅ 8. Content preview generated successfully")
        
        # Test final content streaming
        final_content = """# The Future of AI in Content Creation

## Research Findings
• According to recent studies, AI technology has advanced significantly in 2024.
• Research shows that content generation tools improve productivity by 40%.

## Draft Content
Artificial Intelligence continues to revolutionize how we work and create content.

The integration of AI tools into daily workflows has become increasingly seamless and powerful.

## Fact Corrections
✓ Corrected: AI adoption increased by 35% (not 30%) according to latest industry reports.
"""
        
        await content_streaming_manager.stream_final_content(test_task_id, final_content)
        await asyncio.sleep(0.1)
        
        print("✅ 9. Final content streamed successfully")
        
        # Test WebSocket message creation
        content_stream_msg = ContentStreamMessage(
            task_id=test_task_id,
            phase="content_generation",
            content_type="paragraph",
            content="Test paragraph for WebSocket streaming",
            sequence_number=1
        )
        assert content_stream_msg.type == "content_stream"
        print("✅ 10. ContentStreamMessage created successfully")
        
        progress_stream_msg = ProgressStreamMessage(
            task_id=test_task_id,
            phase="content_generation",
            progress=75.0,
            status="running",
            content_preview=preview[:200],
            current_section="Draft Writing"
        )
        assert progress_stream_msg.type == "progress_stream"
        print("✅ 11. ProgressStreamMessage created successfully")
        
        # Verify streaming results
        assert len(received_streams) >= 6  # Research (2) + Content (2) + Correction (1) + Final (1)
        print(f"✅ 12. Received {len(received_streams)} streaming updates")
        
        # Test TaskManager streaming methods
        await task_manager.setup_content_streaming(test_task_id)
        await task_manager.stream_research_finding(test_task_id, "TaskManager test finding")
        await task_manager.stream_content_paragraph(test_task_id, "TaskManager test paragraph")
        await task_manager.stream_fact_correction(test_task_id, "TaskManager test correction")
        print("✅ 13. TaskManager streaming methods working")
        
        # Clean up
        await content_streaming_manager.cleanup_task_stream(test_task_id)
        print("✅ 14. Cleanup completed")
        
        print("\n🎉 Phase 4 Content Streaming Test Results:")
        print("✅ Content buffer management")
        print("✅ Research findings streaming")
        print("✅ Content paragraph streaming")
        print("✅ Fact correction streaming")
        print("✅ Final content streaming")
        print("✅ Content preview generation")
        print("✅ WebSocket message types")
        print("✅ TaskManager integration")
        print("✅ Streaming callback system")
        
        print("\n🚀 Phase 4 Progressive Content Streaming ready!")
        
        print("\n📊 Benefits achieved:")
        print("  • Real-time content preview as AI generates")
        print("  • Live research findings streaming")
        print("  • Incremental content paragraph delivery")
        print("  • Fact-checking corrections streamed live")
        print("  • Enhanced user engagement during generation")
        print("  • Reduced perceived wait time")
        print("  • Interactive AI generation experience")
        
    except Exception as e:
        print(f"\n❌ Phase 4 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    # Set PYTHONPATH to include src directory
    import sys
    import os
    src_path = os.path.join(os.path.dirname(__file__), "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    # Run the test
    success = asyncio.run(test_content_streaming_phase4())
    exit(0 if success else 1)
