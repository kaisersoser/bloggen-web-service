"""
Tests for Monitoring Service

Tests health checks, metrics collection, performance tracking,
and system resource monitoring.

Phase 3.5: Monitoring & Observability
Date: October 13, 2025
"""

import asyncio
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.monitoring_service import (
    HealthCheckResult,
    MetricSnapshot,
    MonitoringService,
    PerformanceMetric,
    SystemResourceMetrics,
    monitor_performance,
    monitoring_service,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_database_service():
    """Mock database service."""
    service = AsyncMock()
    service.fetchval = AsyncMock(return_value=1)
    service.is_initialized = MagicMock(return_value=True)
    return service


@pytest.fixture
def mock_redis_manager():
    """Mock Redis manager."""
    manager = AsyncMock()
    manager.is_healthy = AsyncMock(return_value=True)
    manager.get_memory_stats = AsyncMock(
        return_value={
            "used_memory_human": "1.5M",
            "connected_clients": 2,
        }
    )
    manager.get_connection_info = AsyncMock(
        return_value={
            "connection_attempts": 1,
        }
    )
    return manager


@pytest.fixture
def monitoring_svc():
    """Fresh monitoring service instance for each test."""
    return MonitoringService(retention_minutes=10)


# =============================================================================
# Health Check Tests
# =============================================================================


@pytest.mark.asyncio
async def test_database_health_check_success(monitoring_svc, mock_database_service):
    """Test successful database health check."""
    with patch("core.monitoring_service.database_service", mock_database_service):
        result = await monitoring_svc._check_database_health()
        
        assert result.service == "database"
        assert result.healthy is True
        assert result.response_time_ms > 0
        assert result.error is None
        assert "pool_initialized" in result.details
        assert result.details["query_test"] == "passed"


@pytest.mark.asyncio
async def test_database_health_check_failure(monitoring_svc, mock_database_service):
    """Test database health check failure."""
    mock_database_service.fetchval = AsyncMock(side_effect=Exception("Connection failed"))
    
    with patch("core.monitoring_service.database_service", mock_database_service):
        result = await monitoring_svc._check_database_health()
        
        assert result.service == "database"
        assert result.healthy is False
        assert result.error == "Connection failed"


@pytest.mark.asyncio
async def test_redis_health_check_success(monitoring_svc, mock_redis_manager):
    """Test successful Redis health check."""
    with patch("core.monitoring_service.redis_manager", mock_redis_manager):
        result = await monitoring_svc._check_redis_health()
        
        assert result.service == "redis"
        assert result.healthy is True
        assert result.response_time_ms > 0
        assert result.error is None
        assert "memory_used" in result.details
        assert "connected_clients" in result.details


@pytest.mark.asyncio
async def test_redis_health_check_failure(monitoring_svc, mock_redis_manager):
    """Test Redis health check failure."""
    mock_redis_manager.is_healthy = AsyncMock(return_value=False)
    
    with patch("core.monitoring_service.redis_manager", mock_redis_manager):
        result = await monitoring_svc._check_redis_health()
        
        assert result.service == "redis"
        assert result.healthy is False
        assert result.error == "Redis ping failed"


@pytest.mark.asyncio
async def test_sse_health_check(monitoring_svc, mock_redis_manager):
    """Test SSE health check."""
    with patch("core.monitoring_service.redis_manager", mock_redis_manager):
        result = await monitoring_svc._check_sse_health()
        
        assert result.service == "sse"
        assert result.healthy is True
        assert "redis_available" in result.details
        assert "fallback_available" in result.details


def test_system_health_check(monitoring_svc):
    """Test system health check."""
    result = monitoring_svc._check_system_health()
    
    assert result.service == "system"
    assert result.healthy in [True, False]  # Depends on system load
    assert result.response_time_ms > 0
    assert "cpu_percent" in result.details
    assert "memory_percent" in result.details
    assert "disk_percent" in result.details


@pytest.mark.asyncio
async def test_check_health_all_services(monitoring_svc, mock_database_service, mock_redis_manager):
    """Test checking health of all services."""
    with patch("core.monitoring_service.database_service", mock_database_service), \
         patch("core.monitoring_service.redis_manager", mock_redis_manager):
        
        results = await monitoring_svc.check_health()
        
        assert "database" in results
        assert "redis" in results
        assert "sse" in results
        assert "system" in results
        
        for service, result in results.items():
            assert isinstance(result, HealthCheckResult)
            assert result.service == service


@pytest.mark.asyncio
async def test_health_check_caching(monitoring_svc, mock_database_service):
    """Test that health checks are cached."""
    with patch("core.monitoring_service.database_service", mock_database_service):
        # First call
        result1 = await monitoring_svc.check_health()
        call_count1 = mock_database_service.fetchval.call_count
        
        # Second call immediately after (should use cache)
        result2 = await monitoring_svc.check_health()
        call_count2 = mock_database_service.fetchval.call_count
        
        # Cache should prevent additional database calls
        assert call_count2 == call_count1


@pytest.mark.asyncio
async def test_health_check_force_refresh(monitoring_svc, mock_database_service):
    """Test forcing health check refresh."""
    with patch("core.monitoring_service.database_service", mock_database_service):
        # First call
        await monitoring_svc.check_health()
        call_count1 = mock_database_service.fetchval.call_count
        
        # Force refresh
        await monitoring_svc.check_health(force=True)
        call_count2 = mock_database_service.fetchval.call_count
        
        # Should have made new database call
        assert call_count2 > call_count1


# =============================================================================
# Metrics Collection Tests
# =============================================================================


def test_record_request_success(monitoring_svc):
    """Test recording successful request."""
    monitoring_svc.record_request("/api/test", 200, 0.5)
    
    snapshot = monitoring_svc.get_metrics_snapshot("/api/test")
    
    assert snapshot.total_requests == 1
    assert snapshot.successful_requests == 1
    assert snapshot.failed_requests == 0
    assert snapshot.avg_response_time == 0.5


def test_record_request_error(monitoring_svc):
    """Test recording failed request."""
    monitoring_svc.record_request("/api/test", 500, 0.3)
    
    snapshot = monitoring_svc.get_metrics_snapshot("/api/test")
    
    assert snapshot.total_requests == 1
    assert snapshot.successful_requests == 0
    assert snapshot.failed_requests == 1


def test_record_multiple_requests(monitoring_svc):
    """Test recording multiple requests."""
    monitoring_svc.record_request("/api/test", 200, 0.5)
    monitoring_svc.record_request("/api/test", 200, 0.7)
    monitoring_svc.record_request("/api/test", 500, 0.3)
    
    snapshot = monitoring_svc.get_metrics_snapshot("/api/test")
    
    assert snapshot.total_requests == 3
    assert snapshot.successful_requests == 2
    assert snapshot.failed_requests == 1
    assert snapshot.error_rate == pytest.approx(33.33, rel=0.1)
    assert snapshot.avg_response_time == pytest.approx(0.5, rel=0.1)


def test_get_all_endpoint_metrics(monitoring_svc):
    """Test getting metrics for all endpoints."""
    monitoring_svc.record_request("/api/test1", 200, 0.5)
    monitoring_svc.record_request("/api/test2", 200, 0.7)
    
    all_metrics = monitoring_svc.get_all_endpoint_metrics()
    
    assert "/api/test1" in all_metrics
    assert "/api/test2" in all_metrics
    assert all_metrics["/api/test1"].total_requests == 1
    assert all_metrics["/api/test2"].total_requests == 1


def test_requests_per_minute(monitoring_svc):
    """Test requests per minute calculation."""
    # Record requests
    for _ in range(5):
        monitoring_svc.record_request("/api/test", 200, 0.5)
    
    snapshot = monitoring_svc.get_metrics_snapshot()
    
    # All requests are recent (within 1 minute)
    assert snapshot.requests_per_minute == 5


# =============================================================================
# Performance Monitoring Tests
# =============================================================================


def test_record_performance(monitoring_svc):
    """Test recording performance metric."""
    monitoring_svc.record_performance("test_operation", 1.5)
    
    metrics = monitoring_svc.get_performance_metrics("test_operation")
    
    assert "test_operation" in metrics
    metric = metrics["test_operation"]
    assert metric.execution_count == 1
    assert metric.avg_duration == 1.5
    assert metric.min_duration == 1.5
    assert metric.max_duration == 1.5


def test_record_multiple_performances(monitoring_svc):
    """Test recording multiple performance metrics."""
    monitoring_svc.record_performance("test_operation", 1.0)
    monitoring_svc.record_performance("test_operation", 2.0)
    monitoring_svc.record_performance("test_operation", 1.5)
    
    metrics = monitoring_svc.get_performance_metrics("test_operation")
    metric = metrics["test_operation"]
    
    assert metric.execution_count == 3
    assert metric.avg_duration == pytest.approx(1.5, rel=0.01)
    assert metric.min_duration == 1.0
    assert metric.max_duration == 2.0
    assert metric.total_duration == 4.5


def test_get_all_performance_metrics(monitoring_svc):
    """Test getting all performance metrics."""
    monitoring_svc.record_performance("operation1", 1.0)
    monitoring_svc.record_performance("operation2", 2.0)
    
    all_metrics = monitoring_svc.get_performance_metrics()
    
    assert "operation1" in all_metrics
    assert "operation2" in all_metrics


@pytest.mark.asyncio
async def test_monitor_performance_decorator_async():
    """Test monitor_performance decorator on async function."""
    test_svc = MonitoringService()
    
    @monitor_performance("test_async_op")
    async def async_function():
        await asyncio.sleep(0.1)
        return "result"
    
    # Patch the global monitoring_service
    with patch("core.monitoring_service.monitoring_service", test_svc):
        result = await async_function()
        
        assert result == "result"
        
        metrics = test_svc.get_performance_metrics("test_async_op")
        assert "test_async_op" in metrics
        assert metrics["test_async_op"].execution_count == 1
        assert metrics["test_async_op"].avg_duration >= 0.1


def test_monitor_performance_decorator_sync():
    """Test monitor_performance decorator on sync function."""
    test_svc = MonitoringService()
    
    @monitor_performance("test_sync_op")
    def sync_function():
        time.sleep(0.1)
        return "result"
    
    # Patch the global monitoring_service
    with patch("core.monitoring_service.monitoring_service", test_svc):
        result = sync_function()
        
        assert result == "result"
        
        metrics = test_svc.get_performance_metrics("test_sync_op")
        assert "test_sync_op" in metrics
        assert metrics["test_sync_op"].execution_count == 1
        assert metrics["test_sync_op"].avg_duration >= 0.1


# =============================================================================
# System Resource Monitoring Tests
# =============================================================================


def test_collect_system_metrics(monitoring_svc):
    """Test collecting system metrics."""
    metrics = monitoring_svc.collect_system_metrics()
    
    assert isinstance(metrics, SystemResourceMetrics)
    assert metrics.cpu_percent >= 0
    assert metrics.memory_percent >= 0
    assert metrics.memory_used_mb >= 0
    assert metrics.memory_available_mb >= 0
    assert metrics.disk_usage_percent >= 0
    assert metrics.open_connections >= 0
    assert metrics.thread_count >= 0


def test_system_metrics_history(monitoring_svc):
    """Test system metrics history tracking."""
    # Collect multiple metrics
    for _ in range(3):
        monitoring_svc.collect_system_metrics()
        time.sleep(0.1)
    
    history = monitoring_svc.get_system_metrics_history(minutes=1)
    
    assert len(history) == 3
    for metric in history:
        assert isinstance(metric, SystemResourceMetrics)


def test_system_metrics_history_filtering(monitoring_svc):
    """Test filtering system metrics history by time."""
    # Collect metrics
    monitoring_svc.collect_system_metrics()
    
    # Manually add old metric
    old_metric = SystemResourceMetrics(
        cpu_percent=50.0,
        memory_percent=50.0,
        memory_used_mb=1000.0,
        memory_available_mb=1000.0,
        disk_usage_percent=50.0,
        open_connections=10,
        thread_count=20,
        timestamp=datetime.utcnow() - timedelta(minutes=20)
    )
    monitoring_svc._system_metrics_history.append(old_metric)
    
    # Get recent history (should exclude old metric)
    recent_history = monitoring_svc.get_system_metrics_history(minutes=10)
    
    # Should only have the recent metric, not the old one
    assert all(
        m.timestamp > datetime.utcnow() - timedelta(minutes=10)
        for m in recent_history
    )


# =============================================================================
# Summary and Status Tests
# =============================================================================


def test_get_summary(monitoring_svc):
    """Test getting monitoring summary."""
    # Add some test data
    monitoring_svc.record_request("/api/test", 200, 0.5)
    monitoring_svc.record_performance("test_op", 1.0)
    
    summary = monitoring_svc.get_summary()
    
    assert "metrics" in summary
    assert "endpoints" in summary
    assert "performance" in summary
    assert "system" in summary
    assert "timestamp" in summary


@pytest.mark.asyncio
async def test_get_full_status(monitoring_svc, mock_database_service, mock_redis_manager):
    """Test getting full system status."""
    with patch("core.monitoring_service.database_service", mock_database_service), \
         patch("core.monitoring_service.redis_manager", mock_redis_manager):
        
        status = await monitoring_svc.get_full_status()
        
        assert "status" in status
        assert status["status"] in ["healthy", "degraded"]
        assert "health" in status
        assert "metrics" in status
        assert "endpoints" in status
        assert "performance" in status
        assert "system" in status
        assert "timestamp" in status


@pytest.mark.asyncio
async def test_full_status_degraded(monitoring_svc, mock_database_service, mock_redis_manager):
    """Test full status when service is degraded."""
    # Make Redis unhealthy
    mock_redis_manager.is_healthy = AsyncMock(return_value=False)
    
    with patch("core.monitoring_service.database_service", mock_database_service), \
         patch("core.monitoring_service.redis_manager", mock_redis_manager):
        
        status = await monitoring_svc.get_full_status()
        
        assert status["status"] == "degraded"
        assert status["health"]["redis"]["healthy"] is False


# =============================================================================
# Cleanup and Retention Tests
# =============================================================================


def test_metrics_cleanup(monitoring_svc):
    """Test automatic cleanup of old metrics."""
    # Set retention to 1 minute
    monitoring_svc.retention_minutes = 1
    
    # Add old timestamp
    old_timestamp = datetime.utcnow() - timedelta(minutes=2)
    monitoring_svc._request_timestamps.append(old_timestamp)
    
    # Add recent timestamp
    monitoring_svc._request_timestamps.append(datetime.utcnow())
    
    # Trigger cleanup
    monitoring_svc._cleanup_old_metrics()
    
    # Old timestamp should be removed
    assert old_timestamp not in monitoring_svc._request_timestamps
    assert len(monitoring_svc._request_timestamps) == 1


def test_system_metrics_history_limit(monitoring_svc):
    """Test that system metrics history is limited."""
    # Add many metrics (more than the limit of 360)
    for _ in range(400):
        monitoring_svc._system_metrics_history.append(
            SystemResourceMetrics(
                cpu_percent=50.0,
                memory_percent=50.0,
                memory_used_mb=1000.0,
                memory_available_mb=1000.0,
                disk_usage_percent=50.0,
                open_connections=10,
                thread_count=20
            )
        )
    
    # Collect new metric (should trigger cleanup)
    monitoring_svc.collect_system_metrics()
    
    # History should be limited to 360 items
    assert len(monitoring_svc._system_metrics_history) <= 360


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.asyncio
async def test_end_to_end_monitoring(monitoring_svc, mock_database_service, mock_redis_manager):
    """Test complete monitoring workflow."""
    with patch("core.monitoring_service.database_service", mock_database_service), \
         patch("core.monitoring_service.redis_manager", mock_redis_manager):
        
        # Record requests
        monitoring_svc.record_request("/api/test", 200, 0.5)
        monitoring_svc.record_request("/api/test", 200, 0.7)
        
        # Record performance
        monitoring_svc.record_performance("test_operation", 1.5)
        
        # Collect system metrics
        monitoring_svc.collect_system_metrics()
        
        # Check health
        health = await monitoring_svc.check_health()
        
        # Get full status
        status = await monitoring_svc.get_full_status()
        
        # Verify everything is recorded
        assert status["status"] == "healthy"
        assert len(health) == 4  # database, redis, sse, system
        assert status["metrics"]["total_requests"] == 2
        assert "test_operation" in status["performance"]
        assert status["system"]["cpu_percent"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
