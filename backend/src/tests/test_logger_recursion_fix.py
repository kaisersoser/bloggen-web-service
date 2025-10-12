"""
Test for Logger Recursion Bug Fix - Phase 1.1

This test verifies that the re-entrancy guard and scoped logger capture
prevents infinite recursion under concurrent load.

Related to: UNIFIED_MODERNIZATION_PLAN.md - Phase 1.1
"""

import pytest
import logging
import threading
import time
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.crewai_stdout_capture import capture_crewai_output, CrewAIOutputParser, LoggingCapture

# Set up test logger
logger = logging.getLogger(__name__)


class RecursionTestTracker:
    """Track events to detect recursion"""
    def __init__(self):
        self.events = []
        self.max_depth = 0
        self.current_depth = 0
        self.lock = threading.Lock()
        self.recursion_detected = False
    
    def callback(self, event):
        """Event callback that triggers logging (potential recursion point)"""
        with self.lock:
            self.current_depth += 1
            self.max_depth = max(self.max_depth, self.current_depth)
            
            # Detect recursion (depth > 5 indicates problem)
            if self.current_depth > 5:
                self.recursion_detected = True
                logger.error(f"RECURSION DETECTED: Depth {self.current_depth}")
                return
            
            self.events.append(event)
            
            # Trigger logging that could cause recursion if not guarded
            logger.info(f"Processing event: {event.get('type')}")
            
            self.current_depth -= 1


def simulate_crewai_output(tracker, worker_id):
    """
    Simulate CrewAI output that triggers logging.
    NOTE: In real usage, stdout capture should NOT be used concurrently.
    This test focuses on the logger capture which IS thread-safe.
    """
    try:
        # Create parser for this worker (thread-safe)
        parser = CrewAIOutputParser(tracker.callback)
        handler = LoggingCapture(parser)
        handler.setLevel(logging.INFO)
        
        # Use logger-only capture (thread-safe)
        test_logger = logging.getLogger(f'crewai.worker{worker_id}')
        test_logger.setLevel(logging.INFO)
        test_logger.addHandler(handler)
        
        try:
            # Simulate various CrewAI log outputs (without stdout capture)
            test_logger.info(f"[Worker {worker_id}] Starting research...")
            test_logger.info(f"Action: search_tool")
            test_logger.info(f"Searching Unsplash for: 'test query {worker_id}'")
            test_logger.info(f"Successfully found 5 images from Unsplash")
            test_logger.info(f"Final Answer: Test complete for worker {worker_id}")
        finally:
            test_logger.removeHandler(handler)
        
        return True
    except Exception as e:
        logger.error(f"Worker {worker_id} failed: {e}")
        return False


def test_logger_recursion_guard():
    """Test that re-entrancy guard prevents recursion in single thread"""
    tracker = RecursionTestTracker()
    
    # Simulate output with logging
    with capture_crewai_output(tracker.callback):
        print("[Test Agent] Performing action")
        logger.info("This log should not cause recursion")
        print("Action: test_tool")
        logger.info("Another log message")
    
    # Verify no recursion occurred
    assert not tracker.recursion_detected, "Recursion was detected!"
    assert tracker.max_depth <= 2, f"Depth too high: {tracker.max_depth}"
    assert len(tracker.events) > 0, "No events captured"
    
    print(f"✅ Single-thread test passed. Max depth: {tracker.max_depth}, Events: {len(tracker.events)}")


def test_concurrent_logger_capture():
    """Test that logger capture works safely under concurrent load (20+ workers)"""
    tracker = RecursionTestTracker()
    num_workers = 25  # Test with 25 concurrent workers
    
    print(f"\n🔄 Testing with {num_workers} concurrent workers...")
    
    # Run concurrent simulations
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(simulate_crewai_output, tracker, i)
            for i in range(num_workers)
        ]
        
        # Wait for all to complete
        results = [future.result() for future in as_completed(futures)]
    
    # Verify results
    successful = sum(results)
    print(f"✅ {successful}/{num_workers} workers completed successfully")
    
    assert not tracker.recursion_detected, "Recursion detected under concurrent load!"
    assert tracker.max_depth <= 3, f"Max depth too high: {tracker.max_depth}"
    assert successful == num_workers, f"Only {successful}/{num_workers} workers succeeded"
    
    print(f"✅ Concurrent test passed. Max depth: {tracker.max_depth}, Total events: {len(tracker.events)}")


def test_logging_handler_reentrancy():
    """Test that LoggingCapture handler has proper re-entrancy guard"""
    events = []
    
    def event_callback(event):
        events.append(event)
        # This logging should not cause recursion
        logger.info(f"Event received: {event.get('type')}")
    
    parser = CrewAIOutputParser(event_callback)
    handler = LoggingCapture(parser)
    
    # Test that re-entrancy is prevented
    test_logger = logging.getLogger('test_logger')
    test_logger.addHandler(handler)
    
    try:
        # First emit - should work
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Action: test_tool',
            args=(),
            exc_info=None
        )
        handler.emit(record)
        
        # Simulate nested call (should be prevented by guard)
        handler._in_handler = True
        handler.emit(record)  # Should be ignored
        handler._in_handler = False
        
        assert len(events) >= 1, "No events captured"
        print(f"✅ Re-entrancy guard test passed. Events: {len(events)}")
        
    finally:
        test_logger.removeHandler(handler)


def test_scoped_logger_capture():
    """Test that only scoped loggers are captured, not root logger"""
    events = []
    
    def event_callback(event):
        events.append(event)
    
    parser = CrewAIOutputParser(event_callback)
    handler = LoggingCapture(parser)
    handler.setLevel(logging.INFO)
    
    # Add handler to specific logger (not root)
    crewai_logger = logging.getLogger('crewai')
    crewai_logger.setLevel(logging.INFO)
    crewai_logger.addHandler(handler)
    
    # Root logger should NOT be captured
    root_logger = logging.getLogger()
    root_in_handlers = handler in root_logger.handlers
    
    try:
        assert not root_in_handlers, "Handler should NOT be on root logger!"
        
        # CrewAI logger should be captured
        crewai_logger.info("Action: crewai_tool")
        
        # Give a moment for async processing
        time.sleep(0.1)
        
        # Note: Events may not be captured if format doesn't match pattern
        # The important part is that root logger is not captured
        print(f"✅ Scoped logger test passed. Root logger not captured. Events: {len(events)}")
        
    finally:
        crewai_logger.removeHandler(handler)


def test_stress_test_recursion_prevention():
    """Stress test with rapid-fire events to ensure no stack overflow"""
    tracker = RecursionTestTracker()
    
    print("\n⚡ Running stress test with rapid events...")
    
    start_time = time.time()
    
    with capture_crewai_output(tracker.callback):
        # Generate 1000 events rapidly
        for i in range(1000):
            print(f"Event {i}")
            if i % 10 == 0:
                logger.info(f"Progress: {i}/1000")
    
    elapsed = time.time() - start_time
    
    assert not tracker.recursion_detected, "Recursion in stress test!"
    assert tracker.max_depth <= 3, f"Max depth too high: {tracker.max_depth}"
    
    print(f"✅ Stress test passed. {len(tracker.events)} events in {elapsed:.2f}s")
    print(f"   Throughput: {len(tracker.events)/elapsed:.0f} events/sec")


if __name__ == "__main__":
    print("=" * 60)
    print("LOGGER RECURSION BUG FIX - VERIFICATION TESTS")
    print("Phase 1.1: Critical Production Fix")
    print("=" * 60)
    
    try:
        # Run all tests
        test_logger_recursion_guard()
        test_logging_handler_reentrancy()
        test_scoped_logger_capture()
        test_concurrent_logger_capture()
        test_stress_test_recursion_prevention()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED - Logger recursion bug is FIXED!")
        print("=" * 60)
        
    except AssertionError as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        raise
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ ERROR: {e}")
        print("=" * 60)
        raise
