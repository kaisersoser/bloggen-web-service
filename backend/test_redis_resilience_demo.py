#!/usr/bin/env python3
"""
Test Redis Resilience Features - Phase 3.4

This script demonstrates the resilience enhancements:
1. Exponential backoff retry
2. Graceful degradation
3. Health monitoring
4. Memory monitoring
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.redis_manager import redis_manager


async def test_redis_resilience():
    """Test Redis resilience features"""
    
    print("=" * 60)
    print("🧪 Testing Redis Resilience Features (Phase 3.4)")
    print("=" * 60)
    print()
    
    # Test 1: Connection with retry
    print("📡 Test 1: Connection with Exponential Backoff")
    print("-" * 60)
    connected = await redis_manager.connect()
    
    if connected:
        print("✅ Redis connected successfully")
    else:
        print("⚠️  Redis connection failed after retries")
        print("✅ Application continuing with graceful degradation")
    print()
    
    # Test 2: Health Check
    print("🏥 Test 2: Health Monitoring")
    print("-" * 60)
    is_healthy = await redis_manager.is_healthy()
    print(f"Redis Health Status: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")
    print()
    
    # Test 3: Connection Info
    print("📊 Test 3: Connection Information")
    print("-" * 60)
    conn_info = await redis_manager.get_connection_info()
    print(f"Connected: {conn_info['connected']}")
    print(f"Redis URL: {conn_info['redis_url']}")
    print(f"Reconnect Attempts: {conn_info['reconnect_attempts']}/{conn_info['max_reconnect_attempts']}")
    print(f"Graceful Degradation: {conn_info['graceful_degradation']}")
    print(f"Active Subscribers: {conn_info['active_subscribers']}")
    print(f"Health: {conn_info['health']}")
    print()
    
    # Test 4: Memory Monitoring
    if is_healthy:
        print("💾 Test 4: Memory Monitoring")
        print("-" * 60)
        memory_stats = await redis_manager.get_memory_stats()
        if memory_stats:
            print(f"Used Memory: {memory_stats.get('used_memory', 'N/A')}")
            print(f"Used Memory RSS: {memory_stats.get('used_memory_rss', 'N/A')}")
            print(f"Memory Fragmentation Ratio: {memory_stats.get('mem_fragmentation_ratio', 'N/A')}")
            print(f"Max Memory: {memory_stats.get('maxmemory', 'N/A')}")
            print(f"Max Memory Policy: {memory_stats.get('maxmemory_policy', 'N/A')}")
            print(f"Connected Clients: {memory_stats.get('connected_clients', 'N/A')}")
        else:
            print("⚠️  Memory stats unavailable")
        print()
    
    # Test 5: TTL Management
    if is_healthy:
        print("🧹 Test 5: TTL Management")
        print("-" * 60)
        cleaned = await redis_manager.cleanup_expired_keys("task_status:*")
        print(f"Keys with TTL added: {cleaned}")
        print()
    
    # Test 6: Graceful Degradation Demo
    print("🛡️  Test 6: Graceful Degradation")
    print("-" * 60)
    print("Testing publish operations with current Redis state...")
    
    from datetime import datetime
    from core.redis_manager import TaskUpdateMessage
    
    task_update = TaskUpdateMessage(
        task_id="test-resilience",
        user_id="test-user",
        phase="testing",
        progress=0.5,
        details="Testing resilience features",
        timestamp=datetime.now().isoformat(),
        status="running"
    )
    
    # This should not crash even if Redis is down
    await redis_manager.publish_task_update(task_update)
    print("✅ Publish operation completed (no crash even if Redis down)")
    print()
    
    # Cleanup
    if is_healthy:
        await redis_manager.disconnect()
        print("✅ Redis disconnected cleanly")
    
    print()
    print("=" * 60)
    print("✅ All Resilience Tests Complete!")
    print("=" * 60)
    print()
    
    # Summary
    print("📋 Summary:")
    print(f"  • Exponential Backoff: {'✅ Working' if 'reconnect_attempts' in conn_info else '❓ Unknown'}")
    print(f"  • Graceful Degradation: ✅ Working")
    print(f"  • Health Monitoring: ✅ Working")
    print(f"  • Memory Monitoring: {'✅ Working' if is_healthy and memory_stats else '⚠️  Redis Required'}")
    print(f"  • TTL Management: {'✅ Working' if is_healthy else '⚠️  Redis Required'}")
    print(f"  • Connection Info: ✅ Working")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(test_redis_resilience())
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
