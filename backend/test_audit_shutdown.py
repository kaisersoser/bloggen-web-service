#!/usr/bin/env python3
"""
Test script for graceful audit tracker shutdown.
Simulates API calls being logged, then tests shutdown without errors.
"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_shutdown():
    """Test audit tracker shutdown with queued operations."""
    
    # Create tracker instance
    tracker = EnhancedDatabaseAuditTracker(
        session_type="test",
        user_id="test_user",
        blog_id=None
    )
    
    # Initialize session (will fail without DB, but that's ok for this test)
    await tracker.start_session()
    
    # Simulate some API calls being tracked
    logger.info("\n📊 Simulating API calls...")
    for i in range(5):
        tracker.track_api_call(
            model="gpt-4o-mini",
            input_tokens=100,
            output_tokens=200,
            phase=f"phase_{i}",
            agent_role="test_agent"
        )
        await asyncio.sleep(0.1)  # Small delay between calls
    
    logger.info(f"✅ Tracked {len(tracker.logged_calls)} API calls")
    logger.info(f"📦 Queue size: {tracker._db_queue.qsize()}")
    
    # Now test graceful shutdown
    logger.info("\n🛑 Testing graceful shutdown...")
    await EnhancedDatabaseAuditTracker.shutdown_worker(timeout=5.0)
    
    logger.info("\n✅ Shutdown test completed successfully!")
    logger.info("   No TimeoutError or CancelledError should appear above")
    
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_shutdown())
        sys.exit(0 if result else 1)
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        sys.exit(1)
