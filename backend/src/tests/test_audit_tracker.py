#!/usr/bin/env python3
"""
Quick test script to verify the audit tracker is working properly
"""

import asyncio
import os
import sys

# Add the src directory to Python path
sys.path.insert(0, '/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/src')

from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker
from core.model_config import get_content_model, get_default_model

async def test_audit_tracker():
    """Test the enhanced audit tracker"""
    print("🧪 Testing Enhanced Database Audit Tracker")
    print("="*50)
    
    # Create tracker
    tracker = EnhancedDatabaseAuditTracker(
        session_type="test_session",
        user_id="cmdaiv5530000z9nxqmyg445v",
        blog_id="test_blog_123"
    )
    
    # Start session
    print("\n📋 Starting audit session...")
    await tracker.start_session()
    
    # Test API call tracking
    print("\n💰 Testing API call tracking...")
    tracker.track_api_call(
        model=get_default_model(),
        input_tokens=100,
        output_tokens=50,
        phase="test_phase",
        agent_role="test_agent"
    )
    
    tracker.track_api_call(
        model=get_default_model(),
        input_tokens=200,
        output_tokens=75,
        phase="test_phase_2",
        agent_role="test_agent_2"
    )
    
    # Get session summary
    print("\n📊 Session Summary:")
    summary = tracker.get_session_summary()
    for key, value in summary.items():
        if key != 'logged_calls':  # Skip detailed calls for readability
            print(f"   {key}: {value}")
    
    print(f"\n📝 Detailed calls:")
    for i, call in enumerate(summary['logged_calls'], 1):
        print(f"   Call {i}: {call['model']} - ${call['cost']:.4f} ({call['total_tokens']} tokens)")
    
    # End session
    print("\n🏁 Ending audit session...")
    await tracker.end_session()
    
    print("\n✅ Test completed!")
    print(f"Final totals: ${tracker.total_cost:.4f}, {tracker.total_tokens} tokens, {len(tracker.logged_calls)} calls")

if __name__ == "__main__":
    asyncio.run(test_audit_tracker())
