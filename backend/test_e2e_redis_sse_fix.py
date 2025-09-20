#!/usr/bin/env python3
"""
Comprehensive End-to-End Test for Redis-SSE Bridge Fix

This script validates all three solutions working together:
1. Immediate SSE Connection (pre-generated task IDs)
2. Redis Message Buffering (early message capture)
3. Synchronous Setup Flow (proper sequencing)

Expected Result: 100% message coverage including early messages
"""

import asyncio
import json
import time
import redis
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class MessageStats:
    """Track message reception statistics."""
    total_published: int = 0
    total_received: int = 0
    message_types: Dict[str, int] = field(default_factory=dict)
    first_message_time: str = ""
    last_message_time: str = ""
    buffered_messages: int = 0
    replayed_messages: int = 0
    missed_messages: List[str] = field(default_factory=list)
    
    @property
    def coverage_percentage(self) -> float:
        if self.total_published == 0:
            return 0.0
        return (self.total_received / self.total_published) * 100.0
    
    def add_published_message(self, message_type: str):
        self.total_published += 1
        self.message_types[f"published_{message_type}"] = self.message_types.get(f"published_{message_type}", 0) + 1
    
    def add_received_message(self, message_type: str, is_replayed: bool = False):
        self.total_received += 1
        if is_replayed:
            self.replayed_messages += 1
            self.message_types[f"replayed_{message_type}"] = self.message_types.get(f"replayed_{message_type}", 0) + 1
        else:
            self.message_types[f"received_{message_type}"] = self.message_types.get(f"received_{message_type}", 0) + 1


class E2EMessageMonitor:
    """Enhanced end-to-end message monitoring for complete flow validation."""
    
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.stats = MessageStats()
        self.published_messages: Set[str] = set()
        self.received_messages: Set[str] = set()
        self.test_start_time: Optional[float] = None
        self.task_id: Optional[str] = None
        
    async def monitor_redis_publications(self, task_id: str, duration_seconds: int = 120):
        """Monitor Redis channels for published messages."""
        pubsub = self.redis_client.pubsub()
        
        try:
            # Monitor both channels
            channels = [f"task_updates:{task_id}", f"sse_immediate:{task_id}"]
            for channel in channels:
                pubsub.subscribe(channel)
            
            logger.info(f"🔍 Monitoring Redis publications on channels: {channels}")
            
            start_time = time.time()
            while time.time() - start_time < duration_seconds:
                try:
                    message = pubsub.get_message(timeout=1.0)
                    if message and message['type'] == 'message':
                        await self._process_published_message(message)
                except Exception as e:
                    logger.error(f"Error processing Redis message: {e}")
                    
        except Exception as e:
            logger.error(f"Redis monitoring error: {e}")
        finally:
            pubsub.close()
    
    async def _process_published_message(self, redis_message):
        """Process a message published to Redis."""
        try:
            channel = redis_message['channel']
            data = json.loads(redis_message['data'])
            message_type = data.get('message_type', 'unknown')
            message_id = f"{message_type}_{data.get('timestamp', time.time())}"
            
            if message_id not in self.published_messages:
                self.published_messages.add(message_id)
                self.stats.add_published_message(message_type)
                
                if not self.stats.first_message_time:
                    self.stats.first_message_time = datetime.now().isoformat()
                self.stats.last_message_time = datetime.now().isoformat()
                
                logger.info(f"📨 PUBLISHED: {message_type} on {channel} (total: {self.stats.total_published})")
                
                # Special logging for critical early messages
                if message_type in ['taskcreated', 'initializing'] or 'correlation_id' in data:
                    logger.warning(f"🚨 CRITICAL EARLY MESSAGE: {message_type} - {data}")
                    
        except Exception as e:
            logger.error(f"Error processing published message: {e}")
    
    def monitor_frontend_reception(self, frontend_messages: List[Dict]):
        """Process messages received by frontend SSE connection."""
        for message in frontend_messages:
            try:
                message_type = message.get('message_type', message.get('type', 'unknown'))
                is_replayed = message.get('replayed', False)
                message_id = f"{message_type}_{message.get('timestamp', message.get('buffer_timestamp', time.time()))}"
                
                if message_id not in self.received_messages:
                    self.received_messages.add(message_id)
                    self.stats.add_received_message(message_type, is_replayed)
                    
                    if is_replayed:
                        logger.info(f"📤 REPLAYED: {message_type} (buffered message replayed)")
                    else:
                        logger.info(f"📡 RECEIVED: {message_type} via SSE (total: {self.stats.total_received})")
                        
            except Exception as e:
                logger.error(f"Error processing received message: {e}")
    
    async def check_message_buffer_status(self, task_id: str):
        """Check Redis message buffer status."""
        try:
            buffer_key = f"message_buffer:{task_id}"
            meta_key = f"message_buffer_meta:{task_id}"
            
            buffer_exists = self.redis_client.exists(buffer_key)
            meta_exists = self.redis_client.exists(meta_key)
            
            if buffer_exists:
                buffer_data_str = self.redis_client.get(buffer_key)
                if buffer_data_str and isinstance(buffer_data_str, str):
                    buffer_data = json.loads(buffer_data_str)
                    self.stats.buffered_messages = len(buffer_data.get('messages', []))
                    logger.info(f"📦 Buffer status: {self.stats.buffered_messages} messages buffered")
            else:
                logger.info(f"📦 Buffer status: No active buffer (flushed or expired)")
                
        except Exception as e:
            logger.error(f"Error checking buffer status: {e}")
    
    def analyze_coverage(self) -> Dict:
        """Analyze message coverage and identify gaps."""
        
        # Identify missed messages
        published_types = set()
        received_types = set()
        
        for key, count in self.stats.message_types.items():
            if key.startswith('published_'):
                msg_type = key.replace('published_', '')
                published_types.add(msg_type)
            elif key.startswith('received_') or key.startswith('replayed_'):
                msg_type = key.replace('received_', '').replace('replayed_', '')
                received_types.add(msg_type)
        
        missed_types = published_types - received_types
        self.stats.missed_messages = list(missed_types)
        
        analysis = {
            'coverage_percentage': self.stats.coverage_percentage,
            'total_published': self.stats.total_published,
            'total_received': self.stats.total_received,
            'buffered_messages': self.stats.buffered_messages,
            'replayed_messages': self.stats.replayed_messages,
            'message_types_breakdown': self.stats.message_types,
            'missed_message_types': self.stats.missed_messages,
            'test_duration': self.stats.last_message_time if self.stats.last_message_time else "No messages",
            'early_messages_captured': any(t in received_types for t in ['taskcreated', 'initializing']),
            'correlation_id_present': any('correlation' in str(self.stats.message_types).lower() for _ in [True])
        }
        
        return analysis
    
    def print_comprehensive_report(self):
        """Print detailed test results."""
        analysis = self.analyze_coverage()
        
        print("\n" + "="*80)
        print("🧪 COMPREHENSIVE E2E TEST RESULTS")
        print("="*80)
        
        print(f"📊 MESSAGE COVERAGE: {analysis['coverage_percentage']:.1f}%")
        print(f"📨 Total Published: {analysis['total_published']}")
        print(f"📡 Total Received: {analysis['total_received']}")
        print(f"📤 Replayed from Buffer: {analysis['replayed_messages']}")
        print(f"📦 Buffered Messages: {analysis['buffered_messages']}")
        
        print(f"\n🎯 CRITICAL VALIDATIONS:")
        print(f"✅ Early Messages Captured: {analysis['early_messages_captured']}")
        print(f"✅ Buffering System Active: {analysis['buffered_messages'] > 0}")
        print(f"✅ Message Replay Working: {analysis['replayed_messages'] > 0}")
        
        if analysis['missed_message_types']:
            print(f"\n❌ MISSED MESSAGE TYPES: {analysis['missed_message_types']}")
        else:
            print(f"\n✅ ALL MESSAGE TYPES RECEIVED!")
            
        print(f"\n📋 MESSAGE TYPE BREAKDOWN:")
        for msg_type, count in sorted(analysis['message_types_breakdown'].items()):
            print(f"   {msg_type}: {count}")
            
        print(f"\n⏱️  TEST DURATION: {analysis['test_duration']}")
        
        # Overall assessment
        if analysis['coverage_percentage'] >= 95 and analysis['early_messages_captured']:
            print(f"\n🎉 TEST RESULT: SUCCESS - Redis-SSE bridge issue RESOLVED!")
        elif analysis['coverage_percentage'] >= 80:
            print(f"\n⚠️  TEST RESULT: PARTIAL SUCCESS - Significant improvement but some gaps remain")
        else:
            print(f"\n❌ TEST RESULT: FAILURE - Issues persist")
            
        print("="*80)


async def run_comprehensive_e2e_test():
    """Execute the comprehensive end-to-end test."""
    
    print("🚀 Starting Comprehensive E2E Test for Redis-SSE Bridge Fix")
    print("This test validates all three solutions working together:")
    print("1. ⚡ Immediate SSE Connection")
    print("2. 📦 Redis Message Buffering") 
    print("3. 🔄 Synchronous Setup Flow")
    print()
    
    monitor = E2EMessageMonitor()
    
    # Test configuration
    test_task_id = "e2e-test-" + str(int(time.time()))
    monitor.task_id = test_task_id
    
    print(f"🆔 Test Task ID: {test_task_id}")
    print(f"📍 Monitoring Redis channels: task_updates:{test_task_id}, sse_immediate:{test_task_id}")
    print()
    
    # Start Redis monitoring in background
    redis_monitor_task = asyncio.create_task(
        monitor.monitor_redis_publications(test_task_id, duration_seconds=180)
    )
    
    print("🔍 Redis monitoring started - waiting for frontend test...")
    print()
    print("🎯 INSTRUCTIONS FOR FRONTEND TEST:")
    print("1. Open frontend at https://localhost:3001")
    print("2. Navigate to blog generator")
    print("3. Use AdminDiagnosticMonitor with task ID:", test_task_id)
    print("4. Generate a blog and monitor SSE reception")
    print("5. Press ENTER here when test is complete")
    print()
    
    # Wait for user to complete frontend test
    input("Press ENTER when frontend test is complete...")
    
    # Cancel Redis monitoring
    redis_monitor_task.cancel()
    try:
        await redis_monitor_task
    except asyncio.CancelledError:
        pass
    
    # Check final buffer status
    await monitor.check_message_buffer_status(test_task_id)
    
    # Print comprehensive results
    monitor.print_comprehensive_report()
    
    return monitor.analyze_coverage()


if __name__ == "__main__":
    asyncio.run(run_comprehensive_e2e_test())