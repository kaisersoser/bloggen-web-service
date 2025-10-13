"""
Test Suite for Redis Resilience (Phase 3.4)

Tests exponential backoff retry, graceful degradation, memory monitoring,
TTL management, and connection health checks.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Import the classes we're testing
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.redis_manager import RedisManager, TaskUpdateMessage


@pytest.fixture
def redis_url():
    """Redis URL for testing"""
    return "redis://localhost:6379"


@pytest.fixture
def redis_manager(redis_url):
    """Create RedisManager instance for testing"""
    manager = RedisManager(redis_url)
    return manager


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client"""
    mock = AsyncMock()
    mock.ping = AsyncMock(return_value=True)
    mock.publish = AsyncMock(return_value=1)
    mock.setex = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.keys = AsyncMock(return_value=[])
    mock.ttl = AsyncMock(return_value=-1)
    mock.expire = AsyncMock(return_value=True)
    mock.info = AsyncMock(return_value={
        'used_memory_human': '1.5M',
        'used_memory_rss_human': '2.0M',
        'mem_fragmentation_ratio': 1.2,
        'maxmemory_human': '100M',
        'maxmemory_policy': 'allkeys-lru',
        'connected_clients': 5
    })
    mock.close = AsyncMock()
    return mock


class TestExponentialBackoffRetry:
    """Test exponential backoff retry logic"""

    @pytest.mark.asyncio
    async def test_successful_connection_first_attempt(self, redis_manager, mock_redis_client):
        """Test successful connection on first attempt"""
        with patch('redis.asyncio.ConnectionPool.from_url') as mock_pool:
            with patch('redis.asyncio.Redis', return_value=mock_redis_client):
                mock_pool.return_value = AsyncMock()
                
                result = await redis_manager.connect()
                
                assert result is True
                assert redis_manager._is_connected is True
                assert redis_manager._reconnect_attempts == 0
                mock_redis_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_retry_with_backoff(self, redis_manager):
        """Test exponential backoff on connection failures"""
        with patch('redis.asyncio.ConnectionPool.from_url') as mock_pool:
            mock_pool.return_value = AsyncMock()
            
            # Create a mock client that fails 3 times then succeeds
            mock_client = AsyncMock()
            call_count = 0
            
            async def ping_with_failures():
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise ConnectionError("Connection refused")
                return True
            
            mock_client.ping = ping_with_failures
            
            with patch('redis.asyncio.Redis', return_value=mock_client):
                with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                    result = await redis_manager.connect()
                    
                    assert result is True
                    assert call_count == 3
                    # Check exponential backoff: 1s, 2s
                    assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_connection_failure_after_max_attempts(self, redis_manager):
        """Test graceful degradation after max retry attempts"""
        with patch('redis.asyncio.ConnectionPool.from_url') as mock_pool:
            mock_pool.return_value = AsyncMock()
            
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock(side_effect=ConnectionError("Connection refused"))
            
            with patch('redis.asyncio.Redis', return_value=mock_client):
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    result = await redis_manager.connect()
                    
                    assert result is False  # Graceful degradation
                    assert redis_manager._is_connected is False
                    assert mock_client.ping.call_count == 5  # Max attempts


class TestHealthChecks:
    """Test connection health checking"""

    @pytest.mark.asyncio
    async def test_is_healthy_when_connected(self, redis_manager, mock_redis_client):
        """Test health check returns True when Redis is healthy"""
        redis_manager.redis_client = mock_redis_client
        redis_manager._is_connected = True
        
        is_healthy = await redis_manager.is_healthy()
        
        assert is_healthy is True
        mock_redis_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_healthy_when_not_connected(self, redis_manager):
        """Test health check returns False when not connected"""
        redis_manager._is_connected = False
        redis_manager.redis_client = None
        
        is_healthy = await redis_manager.is_healthy()
        
        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_is_healthy_when_ping_fails(self, redis_manager, mock_redis_client):
        """Test health check handles ping failures"""
        mock_redis_client.ping = AsyncMock(side_effect=ConnectionError("Connection lost"))
        redis_manager.redis_client = mock_redis_client
        redis_manager._is_connected = True
        
        is_healthy = await redis_manager.is_healthy()
        
        assert is_healthy is False
        assert redis_manager._is_connected is False  # Should update state


class TestGracefulDegradation:
    """Test graceful degradation when Redis is unavailable"""

    @pytest.mark.asyncio
    async def test_publish_when_redis_unavailable(self, redis_manager):
        """Test publish doesn't crash when Redis is unavailable"""
        redis_manager._is_connected = False
        redis_manager.redis_client = None
        
        task_update = TaskUpdateMessage(
            task_id="test-task",
            user_id="test-user",
            phase="research",
            progress=0.5,
            details="Testing",
            timestamp=datetime.now().isoformat(),
            status="running"
        )
        
        # Should not raise exception
        await redis_manager.publish_task_update(task_update)

    @pytest.mark.asyncio
    async def test_publish_immediate_message_when_unhealthy(self, redis_manager):
        """Test immediate message publish degrades gracefully"""
        redis_manager._is_connected = False
        
        # Should not raise exception
        await redis_manager.publish_immediate_message(
            "test-task",
            {"type": "status", "message": "Testing"}
        )

    @pytest.mark.asyncio
    async def test_cache_task_status_when_redis_down(self, redis_manager):
        """Test cache operation degrades gracefully"""
        redis_manager._is_connected = False
        redis_manager.redis_client = None
        
        # Should not raise exception
        await redis_manager.cache_task_status(
            "test-task",
            {"status": "completed"},
            ttl=3600
        )


class TestMemoryMonitoring:
    """Test Redis memory monitoring features"""

    @pytest.mark.asyncio
    async def test_get_memory_stats_success(self, redis_manager, mock_redis_client):
        """Test successful memory stats retrieval"""
        redis_manager.redis_client = mock_redis_client
        redis_manager._is_connected = True
        
        stats = await redis_manager.get_memory_stats()
        
        assert 'used_memory' in stats
        assert 'mem_fragmentation_ratio' in stats
        assert 'maxmemory' in stats
        assert stats['used_memory'] == '1.5M'
        mock_redis_client.info.assert_called_once_with('memory')

    @pytest.mark.asyncio
    async def test_get_memory_stats_when_unhealthy(self, redis_manager):
        """Test memory stats returns empty dict when Redis unhealthy"""
        redis_manager._is_connected = False
        
        stats = await redis_manager.get_memory_stats()
        
        assert stats == {}

    @pytest.mark.asyncio
    async def test_get_memory_stats_handles_errors(self, redis_manager, mock_redis_client):
        """Test memory stats handles Redis errors gracefully"""
        mock_redis_client.info = AsyncMock(side_effect=Exception("Info command failed"))
        redis_manager.redis_client = mock_redis_client
        redis_manager._is_connected = True
        
        stats = await redis_manager.get_memory_stats()
        
        assert stats == {}


class TestTTLManagement:
    """Test TTL management and key expiration"""

    @pytest.mark.asyncio
    async def test_cleanup_expired_keys_adds_ttl(self, redis_manager, mock_redis_client):
        """Test cleanup adds TTL to keys without expiration"""
        keys_without_ttl = [b"task_status:1", b"task_status:2", b"task_status:3"]
        mock_redis_client.keys = AsyncMock(return_value=keys_without_ttl)
        mock_redis_client.ttl = AsyncMock(return_value=-1)  # No TTL
        
        redis_manager.redis_client = mock_redis_client
        redis_manager._is_connected = True
        
        count = await redis_manager.cleanup_expired_keys("task_status:*")
        
        assert count == 3
        assert mock_redis_client.expire.call_count == 3

    @pytest.mark.asyncio
    async def test_cleanup_skips_keys_with_ttl(self, redis_manager, mock_redis_client):
        """Test cleanup skips keys that already have TTL"""
        keys_with_ttl = [b"task_status:1", b"task_status:2"]
        mock_redis_client.keys = AsyncMock(return_value=keys_with_ttl)
        mock_redis_client.ttl = AsyncMock(return_value=3600)  # Has TTL
        
        redis_manager.redis_client = mock_redis_client
        redis_manager._is_connected = True
        
        count = await redis_manager.cleanup_expired_keys("task_status:*")
        
        assert count == 0
        mock_redis_client.expire.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_when_redis_unhealthy(self, redis_manager):
        """Test cleanup returns 0 when Redis unhealthy"""
        redis_manager._is_connected = False
        
        count = await redis_manager.cleanup_expired_keys()
        
        assert count == 0

    @pytest.mark.asyncio
    async def test_publish_with_ttl_success(self, redis_manager, mock_redis_client):
        """Test publish with TTL stores and publishes message"""
        redis_manager.redis_client = mock_redis_client
        redis_manager._is_connected = True
        
        await redis_manager.publish_with_ttl(
            key="test:key",
            channel="test:channel",
            data={"message": "test"},
            ttl=1800
        )
        
        mock_redis_client.setex.assert_called_once()
        mock_redis_client.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_with_ttl_when_unhealthy(self, redis_manager):
        """Test publish with TTL degrades gracefully when Redis down"""
        redis_manager._is_connected = False
        
        # Should not raise exception
        await redis_manager.publish_with_ttl(
            key="test:key",
            channel="test:channel",
            data={"message": "test"},
            ttl=1800
        )


class TestConnectionInfo:
    """Test connection information retrieval"""

    @pytest.mark.asyncio
    async def test_get_connection_info(self, redis_manager, mock_redis_client):
        """Test connection info returns current state"""
        redis_manager._is_connected = True
        redis_manager.redis_client = mock_redis_client
        redis_manager._reconnect_attempts = 2
        redis_manager.subscribers = {"sub1": MagicMock(), "sub2": MagicMock()}
        
        info = await redis_manager.get_connection_info()
        
        assert info['connected'] is True
        assert info['redis_url'] == redis_manager.redis_url
        assert info['reconnect_attempts'] == 2
        assert info['max_reconnect_attempts'] == 5
        assert info['active_subscribers'] == 2
        assert 'health' in info


class TestBackwardCompatibility:
    """Test backward compatibility with existing code"""

    @pytest.mark.asyncio
    async def test_health_check_method_exists(self, redis_manager):
        """Test legacy health_check method still works"""
        redis_manager._is_connected = False
        
        result = await redis_manager.health_check()
        
        assert result is False

    @pytest.mark.asyncio
    async def test_existing_publish_methods_work(self, redis_manager, mock_redis_client):
        """Test existing publish methods maintain compatibility"""
        redis_manager.redis_client = mock_redis_client
        redis_manager._is_connected = True
        
        task_update = TaskUpdateMessage(
            task_id="test",
            user_id="user1",
            phase="research",
            progress=0.5,
            details="test",
            timestamp=datetime.now().isoformat(),
            status="running"
        )
        
        await redis_manager.publish_task_update(task_update)
        
        # Should call publish twice (task channel + user channel)
        assert mock_redis_client.publish.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
