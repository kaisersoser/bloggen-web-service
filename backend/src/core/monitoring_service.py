"""
Monitoring Service for Blog Generation Application

Provides comprehensive monitoring capabilities:
- Health checks for all critical services (DB, Redis, SSE)
- Metrics collection (requests, latency, errors, resources)
- Performance tracking with decorators
- System resource monitoring

Usage:
    from core.monitoring_service import monitoring_service, monitor_performance
    
    # Check health
    health = await monitoring_service.check_health()
    
    # Track metrics
    monitoring_service.record_request("/api/generate", 200, 1.5)
    
    # Monitor function
    @monitor_performance("blog_generation")
    async def generate_blog():
        ...
"""

import asyncio
import functools
import psutil
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from core.database_service import database_service
from core.logging_utils import setup_api_logger
from core.redis_manager import redis_manager

logger = setup_api_logger("monitoring_service")


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    service: str
    healthy: bool
    response_time_ms: float
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MetricSnapshot:
    """Snapshot of metrics at a point in time."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    error_rate: float
    requests_per_minute: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PerformanceMetric:
    """Performance metric for a specific operation."""
    operation: str
    execution_count: int
    total_duration: float
    avg_duration: float
    min_duration: float
    max_duration: float
    last_execution: datetime


@dataclass
class SystemResourceMetrics:
    """System resource usage metrics."""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    open_connections: int
    thread_count: int
    timestamp: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# Monitoring Service
# =============================================================================


class MonitoringService:
    """
    Centralized monitoring service for health checks and metrics.
    
    Features:
    - Health checks for DB, Redis, SSE
    - Request/response metrics tracking
    - Performance monitoring with decorators
    - System resource monitoring
    - Time-series data with configurable retention
    """
    
    def __init__(self, retention_minutes: int = 60):
        """
        Initialize monitoring service.
        
        Args:
            retention_minutes: How long to retain metrics data
        """
        self.retention_minutes = retention_minutes
        
        # Request metrics
        self._request_count: Dict[str, int] = defaultdict(int)
        self._success_count: Dict[str, int] = defaultdict(int)
        self._error_count: Dict[str, int] = defaultdict(int)
        self._response_times: Dict[str, List[float]] = defaultdict(list)
        self._request_timestamps: List[datetime] = []
        
        # Performance metrics
        self._performance_metrics: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "total_duration": 0.0,
                "durations": [],
                "last_execution": None
            }
        )
        
        # Health check cache (avoid hammering services)
        self._health_cache: Dict[str, HealthCheckResult] = {}
        self._health_cache_ttl = 5  # seconds
        self._last_health_check: Dict[str, datetime] = {}
        
        # System metrics history
        self._system_metrics_history: List[SystemResourceMetrics] = []
        
        logger.info(f"MonitoringService initialized (retention: {retention_minutes}m)")
    
    # =========================================================================
    # Health Checks
    # =========================================================================
    
    async def check_health(self, force: bool = False) -> Dict[str, HealthCheckResult]:
        """
        Perform health checks on all services.
        
        Args:
            force: Force fresh health check (bypass cache)
            
        Returns:
            Dictionary of service name to HealthCheckResult
        """
        services = ["database", "redis", "sse", "system"]
        results = {}
        
        for service in services:
            # Check cache first
            if not force and service in self._health_cache:
                cache_age = (datetime.utcnow() - self._last_health_check.get(service, datetime.min)).total_seconds()
                if cache_age < self._health_cache_ttl:
                    results[service] = self._health_cache[service]
                    continue
            
            # Perform fresh health check
            if service == "database":
                result = await self._check_database_health()
            elif service == "redis":
                result = await self._check_redis_health()
            elif service == "sse":
                result = await self._check_sse_health()
            elif service == "system":
                result = self._check_system_health()
            else:
                result = HealthCheckResult(
                    service=service,
                    healthy=False,
                    response_time_ms=0.0,
                    error="Unknown service"
                )
            
            # Cache result
            self._health_cache[service] = result
            self._last_health_check[service] = datetime.utcnow()
            results[service] = result
        
        return results
    
    async def _check_database_health(self) -> HealthCheckResult:
        """Check database health."""
        start_time = time.time()
        
        try:
            # Simple query to verify connection
            result = await database_service.fetchval("SELECT 1")
            
            if result == 1:
                response_time = (time.time() - start_time) * 1000
                
                # Check if pool is initialized
                is_initialized = database_service.is_initialized()
                
                return HealthCheckResult(
                    service="database",
                    healthy=True,
                    response_time_ms=response_time,
                    details={
                        "pool_initialized": is_initialized,
                        "query_test": "passed"
                    }
                )
            else:
                return HealthCheckResult(
                    service="database",
                    healthy=False,
                    response_time_ms=(time.time() - start_time) * 1000,
                    error="Query test failed"
                )
                    
        except Exception as e:
            return HealthCheckResult(
                service="database",
                healthy=False,
                response_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
    
    async def _check_redis_health(self) -> HealthCheckResult:
        """Check Redis health."""
        start_time = time.time()
        
        try:
            is_healthy = await redis_manager.is_healthy()
            response_time = (time.time() - start_time) * 1000
            
            if is_healthy:
                # Get additional stats
                memory_stats = await redis_manager.get_memory_stats()
                connection_info = await redis_manager.get_connection_info()
                
                return HealthCheckResult(
                    service="redis",
                    healthy=True,
                    response_time_ms=response_time,
                    details={
                        "memory_used": memory_stats.get("used_memory_human", "unknown"),
                        "connected_clients": memory_stats.get("connected_clients", 0),
                        "connection_attempts": connection_info.get("connection_attempts", 0)
                    }
                )
            else:
                return HealthCheckResult(
                    service="redis",
                    healthy=False,
                    response_time_ms=response_time,
                    error="Redis ping failed"
                )
                
        except Exception as e:
            return HealthCheckResult(
                service="redis",
                healthy=False,
                response_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
    
    async def _check_sse_health(self) -> HealthCheckResult:
        """Check SSE handler health."""
        start_time = time.time()
        
        try:
            # SSE handler is part of main.py, so we check if Redis is available
            # since SSE depends on Redis for pub/sub
            redis_healthy = await redis_manager.is_healthy()
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                service="sse",
                healthy=redis_healthy,
                response_time_ms=response_time,
                details={
                    "redis_available": redis_healthy,
                    "fallback_available": True  # Database polling always available
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                service="sse",
                healthy=False,
                response_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
    
    def _check_system_health(self) -> HealthCheckResult:
        """Check system resource health."""
        start_time = time.time()
        
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Determine if system is healthy (simple thresholds)
            healthy = (
                cpu_percent < 90.0 and
                memory.percent < 90.0 and
                disk.percent < 90.0
            )
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                service="system",
                healthy=healthy,
                response_time_ms=response_time,
                details={
                    "cpu_percent": round(cpu_percent, 2),
                    "memory_percent": round(memory.percent, 2),
                    "disk_percent": round(disk.percent, 2),
                    "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                service="system",
                healthy=False,
                response_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
    
    # =========================================================================
    # Metrics Collection
    # =========================================================================
    
    def record_request(
        self,
        endpoint: str,
        status_code: int,
        response_time: float
    ) -> None:
        """
        Record a request for metrics tracking.
        
        Args:
            endpoint: API endpoint path
            status_code: HTTP status code
            response_time: Response time in seconds
        """
        self._request_count[endpoint] += 1
        self._request_timestamps.append(datetime.utcnow())
        
        if 200 <= status_code < 400:
            self._success_count[endpoint] += 1
        else:
            self._error_count[endpoint] += 1
        
        self._response_times[endpoint].append(response_time)
        
        # Cleanup old data
        self._cleanup_old_metrics()
    
    def get_metrics_snapshot(self, endpoint: Optional[str] = None) -> MetricSnapshot:
        """
        Get current metrics snapshot.
        
        Args:
            endpoint: Optional specific endpoint (None for all)
            
        Returns:
            MetricSnapshot with current metrics
        """
        if endpoint:
            total = self._request_count.get(endpoint, 0)
            success = self._success_count.get(endpoint, 0)
            failed = self._error_count.get(endpoint, 0)
            response_times = self._response_times.get(endpoint, [])
        else:
            total = sum(self._request_count.values())
            success = sum(self._success_count.values())
            failed = sum(self._error_count.values())
            response_times = [rt for times in self._response_times.values() for rt in times]
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
        error_rate = (failed / total * 100) if total > 0 else 0.0
        
        # Calculate requests per minute
        cutoff_time = datetime.utcnow() - timedelta(minutes=1)
        recent_requests = sum(1 for ts in self._request_timestamps if ts > cutoff_time)
        
        return MetricSnapshot(
            total_requests=total,
            successful_requests=success,
            failed_requests=failed,
            avg_response_time=avg_response_time,
            error_rate=error_rate,
            requests_per_minute=recent_requests
        )
    
    def get_all_endpoint_metrics(self) -> Dict[str, MetricSnapshot]:
        """Get metrics for all endpoints."""
        endpoints = set(self._request_count.keys())
        return {
            endpoint: self.get_metrics_snapshot(endpoint)
            for endpoint in endpoints
        }
    
    # =========================================================================
    # Performance Monitoring
    # =========================================================================
    
    def record_performance(
        self,
        operation: str,
        duration: float,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Record performance metric for an operation.
        
        Args:
            operation: Name of the operation
            duration: Duration in seconds
            timestamp: Optional timestamp (defaults to now)
        """
        metrics = self._performance_metrics[operation]
        metrics["count"] += 1
        metrics["total_duration"] += duration
        metrics["durations"].append(duration)
        metrics["last_execution"] = timestamp or datetime.utcnow()
        
        # Keep only recent durations (for accurate stats)
        if len(metrics["durations"]) > 1000:
            metrics["durations"] = metrics["durations"][-1000:]
    
    def get_performance_metrics(
        self,
        operation: Optional[str] = None
    ) -> Dict[str, PerformanceMetric]:
        """
        Get performance metrics for operations.
        
        Args:
            operation: Optional specific operation (None for all)
            
        Returns:
            Dictionary of operation name to PerformanceMetric
        """
        if operation:
            operations = {operation: self._performance_metrics.get(operation)}
        else:
            operations = self._performance_metrics
        
        results = {}
        for op_name, metrics in operations.items():
            if metrics and metrics["count"] > 0:
                durations = metrics["durations"]
                results[op_name] = PerformanceMetric(
                    operation=op_name,
                    execution_count=metrics["count"],
                    total_duration=metrics["total_duration"],
                    avg_duration=metrics["total_duration"] / metrics["count"],
                    min_duration=min(durations) if durations else 0.0,
                    max_duration=max(durations) if durations else 0.0,
                    last_execution=metrics["last_execution"]
                )
        
        return results
    
    # =========================================================================
    # System Resource Monitoring
    # =========================================================================
    
    def collect_system_metrics(self) -> SystemResourceMetrics:
        """Collect current system resource metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            process = psutil.Process()
            
            metrics = SystemResourceMetrics(
                cpu_percent=round(cpu_percent, 2),
                memory_percent=round(memory.percent, 2),
                memory_used_mb=round(memory.used / 1024 / 1024, 2),
                memory_available_mb=round(memory.available / 1024 / 1024, 2),
                disk_usage_percent=round(disk.percent, 2),
                open_connections=len(process.connections()),
                thread_count=process.num_threads()
            )
            
            # Store in history
            self._system_metrics_history.append(metrics)
            
            # Keep only recent history
            if len(self._system_metrics_history) > 360:  # 1 hour at 10s intervals
                self._system_metrics_history = self._system_metrics_history[-360:]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return SystemResourceMetrics(
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
                disk_usage_percent=0.0,
                open_connections=0,
                thread_count=0
            )
    
    def get_system_metrics_history(
        self,
        minutes: int = 10
    ) -> List[SystemResourceMetrics]:
        """
        Get system metrics history.
        
        Args:
            minutes: How many minutes of history to return
            
        Returns:
            List of SystemResourceMetrics
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        return [
            m for m in self._system_metrics_history
            if m.timestamp > cutoff_time
        ]
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def _cleanup_old_metrics(self) -> None:
        """Remove metrics older than retention period."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.retention_minutes)
        
        # Cleanup request timestamps
        self._request_timestamps = [
            ts for ts in self._request_timestamps
            if ts > cutoff_time
        ]
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive monitoring summary.
        
        Returns:
            Dictionary with all monitoring data
        """
        return {
            "metrics": self.get_metrics_snapshot().__dict__,
            "endpoints": {
                endpoint: snapshot.__dict__
                for endpoint, snapshot in self.get_all_endpoint_metrics().items()
            },
            "performance": {
                op: metric.__dict__
                for op, metric in self.get_performance_metrics().items()
            },
            "system": self.collect_system_metrics().__dict__,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_full_status(self) -> Dict[str, Any]:
        """
        Get full system status including health checks.
        
        Returns:
            Complete status dictionary
        """
        health_checks = await self.check_health()
        summary = self.get_summary()
        
        return {
            "status": "healthy" if all(h.healthy for h in health_checks.values()) else "degraded",
            "health": {
                service: {
                    "healthy": result.healthy,
                    "response_time_ms": result.response_time_ms,
                    "details": result.details,
                    "error": result.error,
                    "timestamp": result.timestamp.isoformat()
                }
                for service, result in health_checks.items()
            },
            "metrics": summary["metrics"],
            "endpoints": summary["endpoints"],
            "performance": summary["performance"],
            "system": summary["system"],
            "timestamp": datetime.utcnow().isoformat()
        }


# =============================================================================
# Global Instance
# =============================================================================

monitoring_service = MonitoringService(retention_minutes=60)


# =============================================================================
# Performance Monitoring Decorator
# =============================================================================

def monitor_performance(operation: str):
    """
    Decorator to monitor function performance.
    
    Usage:
        @monitor_performance("blog_generation")
        async def generate_blog():
            ...
    """
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    monitoring_service.record_performance(operation, duration)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    monitoring_service.record_performance(operation, duration)
            return sync_wrapper
    return decorator
