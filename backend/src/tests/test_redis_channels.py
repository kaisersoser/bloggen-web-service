#!/usr/bin/env python3
"""
Simple Redis Channel Test

Test if Redis pub/sub channels are receiving notifications by monitoring
Redis directly during blog generation workflow.
"""

import sys
import os
import time
import redis
import threading
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class RedisChannelTester:
    """Test Redis pub/sub channels for notification delivery"""
    
    def __init__(self):
        try:
            self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            print("✅ Redis connection established")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            self.redis_client = None
        
        self.notifications_received = []
        self.monitoring = False
    
    def test_redis_connectivity(self) -> bool:
        """Test basic Redis connectivity and operations"""
        print("\n🔍 Testing Redis Connectivity")
        print("=" * 40)
        
        if not self.redis_client:
            print("❌ No Redis connection")
            return False
        
        try:
            # Test basic operations
            test_key = "test:notification:redis"
            test_value = {"test": "redis_connectivity", "timestamp": time.time()}
            
            # Set and get
            self.redis_client.set(test_key, str(test_value))
            retrieved = self.redis_client.get(test_key)
            if retrieved:
                print(f"✅ Redis set/get working: {str(retrieved)[:50]}...")
            else:
                print("❌ Redis set/get failed")
            
            # Test pub/sub
            pubsub = self.redis_client.pubsub()
            pubsub.subscribe("test:channel")
            
            # Publish test message
            self.redis_client.publish("test:channel", "test message")
            
            # Try to receive
            message = pubsub.get_message(timeout=1)
            if message:
                print("✅ Redis pub/sub working")
            
            pubsub.close()
            self.redis_client.delete(test_key)
            
            return True
            
        except Exception as e:
            print(f"❌ Redis operation failed: {e}")
            return False
    
    def monitor_notification_channels(self, duration: int = 30):
        """Monitor Redis channels for blog generation notifications"""
        print(f"\n📡 Monitoring Redis Notification Channels")
        print("=" * 50)
        print(f"⏱️  Monitoring for {duration} seconds...")
        
        if not self.redis_client:
            print("❌ Cannot monitor without Redis connection")
            return
        
        try:
            pubsub = self.redis_client.pubsub()
            
            # Subscribe to all relevant channels
            channels_to_monitor = [
                "task_updates:*",      # Task status updates
                "user_updates:*",      # User-specific updates
                "sse_immediate:*",     # Immediate SSE notifications
                "blog_generation:*",   # Blog generation events
                "image_events:*",      # Image generation events
                "notifications:*"      # General notifications
            ]
            
            print("📋 Subscribing to channels:")
            for channel in channels_to_monitor:
                pubsub.psubscribe(channel)
                print(f"   📢 {channel}")
            
            print(f"\n🔍 Listening for notifications...")
            
            start_time = time.time()
            message_count = 0
            
            for message in pubsub.listen():
                elapsed = time.time() - start_time
                
                if elapsed > duration:
                    print(f"⏰ Monitoring timeout after {duration}s")
                    break
                
                if message['type'] == 'pmessage':
                    message_count += 1
                    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                    
                    channel = message['channel']
                    data = message['data']
                    
                    notification = {
                        'timestamp': timestamp,
                        'elapsed': f"{elapsed:.1f}s",
                        'channel': channel,
                        'data': data
                    }
                    
                    self.notifications_received.append(notification)
                    
                    print(f"[{timestamp}] 📢 {channel}")
                    print(f"    📄 {str(data)[:100]}...")
                    
                    # Check for image-related notifications
                    if any(keyword in str(data).lower() for keyword in ['image', 'unsplash', 'openai', 'dall']):
                        print(f"    🖼️  IMAGE NOTIFICATION DETECTED!")
                    
                    print()
            
            pubsub.close()
            
            print(f"\n📊 Redis Monitoring Results:")
            print(f"   📢 Total notifications: {message_count}")
            print(f"   ⏱️  Duration: {elapsed:.1f}s")
            
            return message_count
            
        except Exception as e:
            print(f"❌ Redis monitoring error: {e}")
            return 0
    
    def analyze_redis_notifications(self):
        """Analyze notifications received through Redis channels"""
        print(f"\n🔍 Redis Notification Analysis")
        print("=" * 40)
        
        total = len(self.notifications_received)
        
        if total == 0:
            print("❌ No notifications received through Redis channels")
            print("   Possible causes:")
            print("   1. Blog generation not publishing to Redis")
            print("   2. Redis pub/sub integration not working") 
            print("   3. Wrong channel names or patterns")
            return
        
        print(f"📊 Total Redis notifications: {total}")
        
        # Analyze by channel
        channels = {}
        image_notifications = 0
        
        for notification in self.notifications_received:
            channel = notification['channel']
            channels[channel] = channels.get(channel, 0) + 1
            
            # Check for image events
            data_str = str(notification['data']).lower()
            if any(keyword in data_str for keyword in ['image', 'unsplash', 'openai', 'dall']):
                image_notifications += 1
        
        print(f"\n📋 Notifications by Channel:")
        for channel, count in sorted(channels.items(), key=lambda x: x[1], reverse=True):
            print(f"   📢 {channel}: {count}")
        
        if image_notifications > 0:
            print(f"\n✅ Image notifications found in Redis: {image_notifications}")
            print("   → Image events ARE reaching Redis pub/sub")
        else:
            print(f"\n❌ No image notifications in Redis")
            print("   → Image events NOT reaching Redis pub/sub")
    
    def run_redis_test_with_manual_trigger(self):
        """Run Redis test with instructions for manual blog generation"""
        print(f"\n🎯 Redis Channel Test with Manual Trigger")
        print("=" * 60)
        print("This test monitors Redis channels while you manually generate a blog")
        print()
        
        # Test connectivity first
        if not self.test_redis_connectivity():
            print("❌ Cannot proceed without Redis connection")
            return
        
        print("📋 Instructions:")
        print("1. Start Redis monitoring (will run for 60 seconds)")
        print("2. In another terminal/browser, start a blog generation")
        print("3. Watch for Redis notifications here")
        print("4. Check if image notifications appear")
        print()
        
        input("Press Enter when ready to start Redis monitoring...")
        
        # Start monitoring
        notification_count = self.monitor_notification_channels(duration=60)
        
        # Analyze results
        self.analyze_redis_notifications()
        
        # Assessment
        print(f"\n🎯 Redis Channel Assessment:")
        if notification_count and notification_count > 0:
            print(f"✅ Redis channels ARE receiving notifications ({notification_count} total)")
            
            image_count = sum(1 for n in self.notifications_received 
                            if any(keyword in str(n['data']).lower() 
                                 for keyword in ['image', 'unsplash', 'openai', 'dall']))
            
            if image_count > 0:
                print(f"✅ Image notifications ARE reaching Redis ({image_count} image events)")
                print("   → Problem is likely in SSE delivery or frontend reception")
            else:
                print(f"❌ Image notifications NOT reaching Redis")
                print("   → Problem is in backend notification routing to Redis")
        else:
            print(f"❌ Redis channels NOT receiving notifications")
            print("   → Problem is in Redis pub/sub integration or blog generation not triggered")


def main():
    """Main Redis channel testing function"""
    print("🧪 REDIS CHANNEL NOTIFICATION TEST")
    print("=" * 50)
    print("Testing Redis pub/sub channels for notification delivery")
    print()
    
    tester = RedisChannelTester()
    tester.run_redis_test_with_manual_trigger()
    
    print(f"\nRedis channel test completed!")


if __name__ == "__main__":
    main()