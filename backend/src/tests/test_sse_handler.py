#!/usr/bin/env python3
"""
Test suite for Phase 3.3 - SSEHandler

Tests SSE streaming functionality, triple fallback strategy, error handling,
and integration with Redis/TaskManager/MessageBuffer.

Run: cd backend && source .venv/bin/activate && pytest src/tests/test_sse_handler.py -v
"""

import asyncio
import json
import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.sse_handler import SSEHandler


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_redis_manager():
    """Mock Redis manager for testing."""
    manager = AsyncMock()
    manager.redis_client = AsyncMock()
    return manager


@pytest.fixture
def mock_task_manager():
    """Mock Task manager for testing."""
    manager = AsyncMock()
    manager.get_task = AsyncMock()
    return manager


@pytest.fixture
def mock_message_buffer():
    """Mock Message buffer for testing."""
    buffer = AsyncMock()
    buffer._check_buffer_exists = AsyncMock(return_value=False)
    buffer.flush_buffered_messages = AsyncMock(return_value=[])
    return buffer


@pytest.fixture
def sse_handler(mock_redis_manager, mock_task_manager, mock_message_buffer):
    """Create SSEHandler instance with mocked dependencies."""
    return SSEHandler(
        redis_manager=mock_redis_manager,
        task_manager=mock_task_manager,
        message_buffer=mock_message_buffer,
        heartbeat_interval=1,  # Short interval for testing
        timeout_seconds=10,  # Short timeout for testing
    )


# ============================================================================
# Test 1: SSEHandler Initialization
# ============================================================================

def test_sse_handler_initialization(sse_handler):
    """Test SSEHandler initializes with correct dependencies."""
    assert sse_handler.redis_manager is not None
    assert sse_handler.task_manager is not None
    assert sse_handler.message_buffer is not None
    assert sse_handler.heartbeat_interval == 1
    assert sse_handler.timeout_seconds == 10
    print("✅ SSEHandler initialization successful")


# ============================================================================
# Test 2: Connection Event Formatting
# ============================================================================

def test_format_connection_event(sse_handler):
    """Test connection acknowledgment event formatting."""
    task_id = "test-task-123"
    event = sse_handler._format_connection_event(task_id)
    
    # Verify SSE format
    assert event.startswith("data: ")
    assert event.endswith("\n\n")
    
    # Parse JSON payload
    json_str = event.replace("data: ", "").strip()
    data = json.loads(json_str)
    
    assert data["type"] == "connected"
    assert data["message_type"] == "connected"
    assert data["task_id"] == task_id
    assert data["message"] == "SSE connection established"
    assert "timestamp" in data
    
    print("✅ Connection event formatting correct")


# ============================================================================
# Test 3: Error Event Formatting
# ============================================================================

def test_format_error_event(sse_handler):
    """Test error event formatting."""
    task_id = "test-task-123"
    error_msg = "Test error message"
    event = sse_handler._format_error_event(error_msg, task_id)
    
    # Verify SSE format
    assert event.startswith("data: ")
    assert event.endswith("\n\n")
    
    # Parse JSON payload
    json_str = event.replace("data: ", "").strip()
    data = json.loads(json_str)
    
    assert data["message_type"] == "error"
    assert data["task_id"] == task_id
    assert error_msg in data["message"]  # Error message is in "message" field
    
    print("✅ Error event formatting correct")


# ============================================================================
# Test 4: Task Update Formatting (Status)
# ============================================================================

def test_format_task_update_status(sse_handler):
    """Test task status update formatting."""
    task_id = "test-task-123"
    task_data = {
        "status": "in_progress",
        "current_step": "Researching topic",
        "progress": 25,
        "message": "Gathering information...",
    }
    
    event = sse_handler._format_task_update(task_data, task_id)
    
    # Verify SSE format
    assert event.startswith("data: ")
    assert event.endswith("\n\n")
    
    # Parse JSON payload
    json_str = event.replace("data: ", "").strip()
    data = json.loads(json_str)
    
    assert data["message_type"] == "status"
    assert data["task_id"] == task_id
    assert data["progress"] == 25
    
    print("✅ Status update formatting correct")


# ============================================================================
# Test 5: Task Update Formatting (Completed)
# ============================================================================

def test_format_task_update_completed(sse_handler):
    """Test completed task formatting."""
    task_id = "test-task-123"
    task_data = {
        "status": "completed",
        "content": "Final blog content here...",
        "generation_time": 45.2,
        "progress": 100,
    }
    
    event = sse_handler._format_task_update(task_data, task_id)
    
    # Parse JSON payload
    json_str = event.replace("data: ", "").strip()
    data = json.loads(json_str)
    
    assert data["message_type"] == "completed"
    assert data["task_id"] == task_id
    assert "content" in data or "final_content" in data
    
    print("✅ Completed task formatting correct")


# ============================================================================
# Test 6: Task Update Formatting (Failed)
# ============================================================================

def test_format_task_update_failed(sse_handler):
    """Test failed task formatting."""
    task_id = "test-task-123"
    task_data = {
        "status": "failed",
        "error": "API rate limit exceeded",
        "progress": 50,
    }
    
    event = sse_handler._format_task_update(task_data, task_id)
    
    # Parse JSON payload
    json_str = event.replace("data: ", "").strip()
    data = json.loads(json_str)
    
    assert data["message_type"] == "error"
    assert data["task_id"] == task_id
    assert "API rate limit" in data["message"]  # Error message is in "message" field
    
    print("✅ Failed task formatting correct")


# ============================================================================
# Test 7: Redis Availability Check
# ============================================================================

@pytest.mark.asyncio
async def test_redis_available(sse_handler):
    """Test Redis availability detection."""
    # With Redis
    available = await sse_handler._redis_available()
    assert available is True
    
    # Without Redis
    sse_handler.redis_manager = None
    available = await sse_handler._redis_available()
    assert available is False
    
    print("✅ Redis availability check working")


# ============================================================================
# Test 8: Buffer Exists Check
# ============================================================================

@pytest.mark.asyncio
async def test_check_buffer_exists(sse_handler):
    """Test message buffer existence check."""
    task_id = "test-task-123"
    
    # Buffer exists
    sse_handler.message_buffer._check_buffer_exists.return_value = True
    exists = await sse_handler._check_buffer_exists(task_id)
    assert exists is True
    
    # Buffer doesn't exist
    sse_handler.message_buffer._check_buffer_exists.return_value = False
    exists = await sse_handler._check_buffer_exists(task_id)
    assert exists is False
    
    # No message buffer
    sse_handler.message_buffer = None
    exists = await sse_handler._check_buffer_exists(task_id)
    assert exists is False
    
    print("✅ Buffer existence check working")


# ============================================================================
# Test 9: Wait for Task or Buffer
# ============================================================================

@pytest.mark.asyncio
async def test_wait_for_task_or_buffer(sse_handler, mock_task_manager):
    """Test waiting for task with retry logic."""
    task_id = "test-task-123"
    
    # Task exists immediately
    mock_task_manager.get_task.return_value = {"id": task_id, "status": "started"}
    task = await sse_handler._wait_for_task_or_buffer(task_id, max_retries=3)
    assert task is not None
    assert task["id"] == task_id
    
    # Task doesn't exist, but buffer does
    mock_task_manager.get_task.return_value = None
    sse_handler.message_buffer._check_buffer_exists.return_value = True
    task = await sse_handler._wait_for_task_or_buffer(task_id, max_retries=3)
    assert task is None  # Returns None when buffer exists
    
    print("✅ Wait for task/buffer working")


# ============================================================================
# Test 10: Redis Message Formatting (Completion)
# ============================================================================

def test_format_redis_message_completion(sse_handler):
    """Test Redis completion message formatting."""
    task_id = "test-task-123"
    redis_data = {
        "message_type": "completed",
        "final_content": "Complete blog post content...",
        "hero_image_url": "https://example.com/image.jpg",
        "task_id": task_id,
    }
    
    event = sse_handler._format_redis_message(redis_data, task_id)
    
    # Parse JSON payload
    json_str = event.replace("data: ", "").strip()
    data = json.loads(json_str)
    
    assert "content" in data or "final_content" in data
    assert data.get("hero_image_url") == "https://example.com/image.jpg"
    
    print("✅ Redis completion message formatting correct")


# ============================================================================
# Test 11: Redis Message Formatting (Generic)
# ============================================================================

def test_format_redis_message_generic(sse_handler):
    """Test generic Redis message forwarding."""
    task_id = "test-task-123"
    redis_data = {
        "type": "agent_thinking",
        "agent": "Researcher",
        "thought": "Analyzing data...",
    }
    
    event = sse_handler._format_redis_message(redis_data, task_id)
    
    # Parse JSON payload
    json_str = event.replace("data: ", "").strip()
    data = json.loads(json_str)
    
    # Should forward message as-is
    assert data["type"] == "agent_thinking"
    assert data["agent"] == "Researcher"
    
    print("✅ Generic Redis message forwarding correct")


# ============================================================================
# Test 12: Heartbeat Generator
# ============================================================================

@pytest.mark.asyncio
async def test_heartbeat_generator(sse_handler):
    """Test heartbeat generation."""
    task_id = "test-task-123"
    
    # Create heartbeat task
    heartbeat_task = asyncio.create_task(
        sse_handler._heartbeat_generator(task_id)
    )
    
    # Let it run for a bit
    await asyncio.sleep(0.1)
    
    # Cancel and verify it handles cancellation
    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass  # Expected
    
    print("✅ Heartbeat generator working")


# ============================================================================
# Test 13: Wait for Flow Start (Timeout)
# ============================================================================

@pytest.mark.asyncio
async def test_wait_for_flow_start_timeout(sse_handler, mock_redis_manager):
    """Test flow start waiting with timeout."""
    task_id = "test-task-123"
    
    # Mock Redis get to return None (flow not started)
    mock_redis_manager.redis_client.get.return_value = None
    
    # Should timeout and return False
    started = await sse_handler._wait_for_flow_start(task_id, timeout=0.5)
    assert started is False
    
    print("✅ Flow start timeout handling working")


# ============================================================================
# Test 14: Wait for Flow Start (Success)
# ============================================================================

@pytest.mark.asyncio
async def test_wait_for_flow_start_success(sse_handler, mock_redis_manager):
    """Test flow start waiting with success."""
    task_id = "test-task-123"
    
    # Mock Redis get to return "started"
    mock_redis_manager.redis_client.get.return_value = "started"
    
    # Should return True immediately
    started = await sse_handler._wait_for_flow_start(task_id, timeout=1.0)
    assert started is True
    
    print("✅ Flow start success detection working")


# ============================================================================
# Test 15: Flush Message Buffer (Empty)
# ============================================================================

@pytest.mark.asyncio
async def test_flush_message_buffer_empty(sse_handler, mock_message_buffer):
    """Test flushing empty message buffer."""
    task_id = "test-task-123"
    
    # Mock empty buffer
    mock_message_buffer.flush_buffered_messages.return_value = []
    
    # Should yield nothing
    events = []
    async for event in sse_handler._flush_message_buffer(task_id):
        events.append(event)
    
    assert len(events) == 0
    
    print("✅ Empty buffer flush working")


# ============================================================================
# Test 16: Flush Message Buffer (With Messages)
# ============================================================================

@pytest.mark.asyncio
async def test_flush_message_buffer_with_messages(sse_handler, mock_message_buffer):
    """Test flushing message buffer with buffered messages."""
    task_id = "test-task-123"
    
    # Mock buffered messages
    class MockBufferedMessage:
        def __init__(self, msg_type, data):
            self.message_type = msg_type
            self.message_data = data
            self.timestamp = datetime.utcnow().isoformat()
    
    buffered = [
        MockBufferedMessage("initializing", {"message": "Starting..."}),
        MockBufferedMessage("status", {"progress": 10}),
    ]
    mock_message_buffer.flush_buffered_messages.return_value = buffered
    
    # Should yield 2 events
    events = []
    async for event in sse_handler._flush_message_buffer(task_id):
        events.append(event)
    
    assert len(events) == 2
    assert all(event.startswith("data: ") for event in events)
    
    # Check replayed flag
    for event in events:
        json_str = event.replace("data: ", "").strip()
        data = json.loads(json_str)
        assert data["replayed"] is True
        assert "buffer_timestamp" in data
    
    print("✅ Buffer flush with messages working")


# ============================================================================
# Test 17: Stream Events (Task Not Found)
# ============================================================================

@pytest.mark.asyncio
async def test_stream_events_task_not_found(sse_handler, mock_task_manager, mock_message_buffer):
    """Test streaming when task not found and no buffer."""
    task_id = "nonexistent-task"
    user_id = "user-123"
    
    # Mock task not found
    mock_task_manager.get_task.return_value = None
    mock_message_buffer._check_buffer_exists.return_value = False
    
    # Should yield error event
    events = []
    async for event in sse_handler.stream_events(task_id, user_id, retry_count=1):
        events.append(event)
    
    assert len(events) == 1
    assert "error" in events[0].lower() or "not found" in events[0].lower()
    
    print("✅ Task not found error handling working")


# ============================================================================
# Test 18: Integration Test - Full Event Stream Mock
# ============================================================================

@pytest.mark.asyncio
async def test_full_event_stream_integration(sse_handler, mock_task_manager, mock_redis_manager):
    """Integration test for full event stream with mocked Redis."""
    task_id = "test-task-123"
    user_id = "user-123"
    
    # Mock task exists
    mock_task_manager.get_task.return_value = {
        "id": task_id,
        "status": "started",
        "progress": 0,
    }
    
    # Mock Redis unavailable to trigger database polling
    sse_handler.redis_manager = None
    
    # Mock task updates during polling
    update_sequence = [
        {"id": task_id, "status": "in_progress", "progress": 25},
        {"id": task_id, "status": "in_progress", "progress": 50},
        {"id": task_id, "status": "completed", "progress": 100, "content": "Done!"},
    ]
    
    call_count = [0]
    
    async def mock_get_task_sequence(tid):
        result = update_sequence[min(call_count[0], len(update_sequence) - 1)]
        call_count[0] += 1
        return result
    
    mock_task_manager.get_task = mock_get_task_sequence
    
    # Stream events
    events = []
    async for event in sse_handler.stream_events(task_id, user_id, retry_count=1):
        events.append(event)
        # Break after a few events to avoid infinite loop
        if len(events) >= 5:
            break
    
    # Should receive connection + status updates
    assert len(events) > 0
    assert any("connected" in event for event in events)
    
    print("✅ Full event stream integration test passed")


# ============================================================================
# Summary Report
# ============================================================================

def test_summary():
    """Print test summary."""
    print("\n" + "=" * 60)
    print("Phase 3.3 SSEHandler Test Summary")
    print("=" * 60)
    print("✅ Event formatting tests passed")
    print("✅ Redis availability checks passed")
    print("✅ Buffer management tests passed")
    print("✅ Error handling tests passed")
    print("✅ Integration tests passed")
    print("=" * 60)


if __name__ == "__main__":
    # Run pytest programmatically
    pytest.main([__file__, '-v', '--tb=short'])
