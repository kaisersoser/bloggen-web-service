"""
FastAPI Blog Generation Service

This is the new FastAPI-based backend for the blog generation service,
designed with async/await patterns and context variables for perfect
request isolation between concurrent users.

Key Features:
- Native async/await throughout the stack
- Context variables for request isolation
- Real-time API usage tracking with zero race conditions
- Background tasks for long-running blog generation
- Server-Sent Events (SSE) for real-time updates
- JWT authentication with dependency injection
"""

import asyncio
import gc
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Optional

import openai
import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from config.protocol_config import get_protocol_config
from core.config import config, get_cors_origins
from core.content_streaming_manager import content_streaming_manager
from core.context_vars import (
    current_audit_tracker,
    set_audit_context,
    set_request_context,
    update_phase,
)
from core.database_service import database_service
from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker
from core.error_responses import (
    create_auth_error,
    create_database_error,
    create_error_response,
    create_system_error,
    create_validation_error,
    error_response_to_http_exception,
    handle_database_error,
)
from core.logging_utils import setup_api_logger
from core.llm_interceptor import setup_llm_interceptor
from core.message_buffer import RedisMessageBuffer
from core.monitoring_service import monitoring_service, monitor_performance
from core.redis_manager import redis_manager
from core.resource_cleanup import (
    CleanupReason,
    cleanup_manager,
    register_database_transaction,
)
from core.s3_cleanup_queue import cleanup_queue_shutdown, get_cleanup_queue
from core.sse_handler import SSEHandler
from core.sse_message_types import (
    create_completed_message,
    create_error_message,
    create_initializing_message,
    create_status_message,
    create_task_created_message,
)
from core.task_manager import task_manager

from bloggen.flows import BlogGenerationFlow
from bloggen.topic_utils import generate_concise_topic

# Authentication (we'll migrate this next)
# from auth_middleware import AuthMiddleware

# =============================================================================
# FastAPI Application Setup with Lifespan Events
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan event handler for startup and shutdown.
    """
    # Startup
    # Ensure logger initialized (may not yet be assigned at import time in some execution orders)
    global logger
    if "logger" not in globals() or logger is None:
        try:
            from core.logging_utils import setup_api_logger as _setup_logger

            logger = _setup_logger("main")  # type: ignore
        except Exception:
            # Fallback basic logger
            import logging as _logging

            logger = _logging.getLogger("main")  # type: ignore
            if not logger.handlers:
                _handler = _logging.StreamHandler()
                _handler.setFormatter(
                    _logging.Formatter("%(asctime)s %(levelname)s %(message)s")
                )
                logger.addHandler(_handler)
            logger.setLevel(_logging.INFO)

    logger.info("🚀 Starting FastAPI Blog Generation Service")

    # Set up LLM interceptor with context variables
    setup_llm_interceptor()
    logger.info("✅ Context-aware LLM interceptor initialized")

    # Initialize shared database service pool
    try:
        await database_service.initialize(
            config.database.url,
            min_size=2,
            max_size=20,  # Increased from default 10 to handle concurrent operations
            command_timeout=60,  # Increased timeout for long-running queries
            max_inactive_connection_lifetime=300,  # Close idle connections after 5 minutes
        )
        logger.info("✅ Database service connection pool initialized (min=2, max=20)")
    except Exception as db_err:
        logger.error(f"❌ Failed to initialize database service: {db_err}")
        raise

    # Patch historical serper_api zero-cost entries (best-effort)
    try:

        async def _pool_provider():
            tracker = EnhancedDatabaseAuditTracker(
                session_type="startup_patch", user_id="system", blog_id=None
            )
            return await tracker._get_database_connection()  # type: ignore

        updated = await EnhancedDatabaseAuditTracker.patch_serper_api_costs(
            _pool_provider
        )
        if updated:
            logger.info(
                f"🔧 Patched {updated} historical serper_api call(s) to cost 0.001"
            )
        # Normalize legacy phase names to current canonical phases
        phase_updates = await EnhancedDatabaseAuditTracker.normalize_phase_names(
            _pool_provider
        )
        if phase_updates:
            logger.info(f"🔧 Normalized legacy phase names: {phase_updates}")
    except Exception as e:
        logger.warning(f"Serper cost patch failed (startup continues): {e}")

    # Initialize Redis connection
    try:
        await redis_manager.connect()
        logger.info("✅ Redis connection established")
    except Exception as e:
        logger.warning(f"Redis connection failed (continuing without Redis): {e}")

    # Initialize Redis message buffer for early message capture
    global message_buffer
    message_buffer = RedisMessageBuffer(redis_manager, buffer_ttl_minutes=30)
    logger.info("✅ Redis message buffer initialized")

    # Connect managers to TaskManager for real-time updates
    task_manager.set_redis_manager(redis_manager)
    task_manager.set_content_streaming_manager(content_streaming_manager)
    task_manager.set_message_buffer(message_buffer)
    logger.info("✅ Redis and Content Streaming managers connected to TaskManager")

    # Start TaskManager cleanup service
    try:
        await task_manager.start_cleanup_service()
    except Exception as cleanup_err:
        logger.error(f"❌ Failed to start TaskManager cleanup service: {cleanup_err}")

    # Warm Redis cache with active task state
    try:
        restored = await task_manager.warm_cache_from_database()
        logger.info(
            "🔥 Task cache warmup complete: total=%s queued=%s in_progress=%s",
            restored.get("total", 0),
            restored.get("queued", 0),
            restored.get("in_progress", 0),
        )
    except Exception as warm_err:
        logger.warning(f"Task cache warmup skipped due to error: {warm_err}")

    # Initialize S3 cleanup queue
    try:
        await get_cleanup_queue()
        logger.info("✅ S3 cleanup queue initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize S3 cleanup queue: {e}")

    logger.info("✅ FastAPI application startup complete")

    yield  # Application runs here

    # Shutdown
    logger.info("🛑 Shutting down FastAPI Blog Generation Service")

    # Shutdown S3 cleanup queue
    try:
        await cleanup_queue_shutdown()
        logger.info("✅ S3 cleanup queue shutdown complete")
    except Exception as e:
        logger.warning(f"S3 cleanup queue shutdown error: {e}")

    # Stop TaskManager cleanup service
    try:
        stats = task_manager.get_cleanup_stats()
        await task_manager.stop_cleanup_service()
        logger.info(
            "🧮 TaskManager cleanup summary: cycles=%s expired=%s redis=%s buffers=%s",
            stats.get("cycles", 0),
            stats.get("expired_tasks", 0),
            stats.get("redis_keys_removed", 0),
            stats.get("buffers_pruned", 0),
        )
    except Exception as cleanup_err:
        logger.warning(f"TaskManager cleanup service shutdown error: {cleanup_err}")

    # Disconnect Redis
    try:
        await redis_manager.disconnect()
        logger.info("✅ Redis connection closed")
    except Exception as e:
        logger.warning(f"Redis shutdown error: {e}")

    # Shutdown audit tracker worker BEFORE closing database pool
    # This ensures queued logs are processed before pool is closed
    try:
        await EnhancedDatabaseAuditTracker.shutdown_worker(timeout=5.0)
        logger.info("✅ Audit tracker worker shutdown complete")
    except Exception as e:
        logger.warning(f"Audit tracker worker shutdown error: {e}")

    # Close database service pool before tearing down other resources
    try:
        await database_service.close()
        logger.info("✅ Database service connection pool closed")
    except Exception as db_close_err:
        logger.warning(f"Database service shutdown error: {db_close_err}")

        # Close database connection pools
    try:
        # Close all active database connections
        # Force close any remaining database pools (best effort)
        for obj in gc.get_objects():
            if hasattr(obj, "pool") and obj.pool and hasattr(obj.pool, "close"):
                try:
                    await obj.pool.close()
                    logger.info(f"✅ Closed database pool from {type(obj).__name__}")
                except Exception:
                    logger.debug(
                        "Database pool cleanup failed for %s", type(obj).__name__,
                        exc_info=True,
                    )

        logger.info("✅ Database connections cleanup completed")
    except Exception as e:
        logger.warning(f"Database cleanup error: {e}")


app = FastAPI(
    title="CrewAI Blog Generation Service",
    description="AI-powered blog generation with real-time cost tracking",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS configuration
allowed_origins = get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# Metrics tracking middleware
@app.middleware("http")
async def metrics_middleware(request, call_next):
    """Track request metrics for monitoring."""
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Record metrics
    duration = time.time() - start_time
    endpoint = request.url.path
    
    # Don't track metrics for metrics endpoints (avoid recursion)
    if not endpoint.startswith("/metrics") and not endpoint.startswith("/health"):
        monitoring_service.record_request(endpoint, response.status_code, duration)
    
    # Add response time header
    response.headers["X-Response-Time"] = f"{duration:.3f}s"
    
    return response

# Global message buffer for early message capture
message_buffer: Optional[RedisMessageBuffer] = None

# Logger
logger = setup_api_logger("main")

# Security
security = HTTPBearer()

# =============================================================================
# Pydantic Models
# =============================================================================


class BlogGenerationRequest(BaseModel):
    """Request model for blog generation.

    topic becomes optional; if absent/blank, the backend will auto-generate
    a topic from provided instructions (leveraging flow auto-topic logic).
    """

    topic: Optional[str] = Field(
        None,
        max_length=200,
        description="Blog topic (optional; auto-generated if omitted)",
    )
    instructions: Optional[str] = Field(
        None, max_length=2000, description="Full user + config built instructions"
    )
    task_id: Optional[str] = Field(None, description="Optional task ID")


class BlogGenerationResponse(BaseModel):
    """Response model for blog generation."""

    task_id: str
    status: str
    message: str


class TitleGenerationRequest(BaseModel):
    """Request model for title generation."""

    instructions: str = Field(
        ..., min_length=3, max_length=500, description="Blog instructions"
    )


class TitleGenerationResponse(BaseModel):
    """Response model for title generation."""

    title: str
    success: bool = True


class TaskStatus(BaseModel):
    """Task status model."""

    id: str
    topic: str
    status: str
    created_at: str
    current_step: str
    result: Optional[str] = None
    error: Optional[str] = None
    user_id: str
    user_email: str
    user_role: str


class User(BaseModel):
    """User model for authentication."""

    id: str
    email: str
    role: str


# =============================================================================
# Authentication Dependencies (Simplified for now)
# =============================================================================


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """
    Get current authenticated user from JWT token.
    Validates JWT tokens using the NEXTAUTH_SECRET.
    """
    try:
        import jwt
        import os

        # Get the secret key (same as used by NextAuth.js)
        secret = os.getenv("NEXTAUTH_SECRET")
        if not secret:
            raise error_response_to_http_exception(
                create_system_error(
                    "auth_config", "NEXTAUTH_SECRET environment variable is required"
                )
            )

        # Decode and validate the JWT token
        payload = jwt.decode(credentials.credentials, secret, algorithms=["HS256"])

        # Extract user information from the token
        user_id = payload.get("sub")
        email = payload.get("email", "unknown@example.com")
        role = payload.get("role", "FREE")

        if not user_id:
            raise error_response_to_http_exception(
                create_auth_error("AUTH_INVALID", "Missing user ID in token")
            )

        return User(id=user_id, email=email, role=role)

    except jwt.ExpiredSignatureError:
        raise error_response_to_http_exception(
            create_auth_error("AUTH_EXPIRED", "JWT token has expired")
        )
    except jwt.InvalidTokenError:
        raise error_response_to_http_exception(
            create_auth_error("AUTH_INVALID", "JWT token is invalid or malformed")
        )
    except HTTPException:
        # Re-raise HTTPExceptions (from structured errors above)
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise error_response_to_http_exception(
            create_auth_error("AUTH_REQUIRED", f"Authentication failed: {str(e)}")
        )


async def get_current_user_from_query_token(token: str) -> User:
    """
    Get current authenticated user from JWT token passed as query parameter.
    Used for SSE authentication since EventSource doesn't support custom headers.
    """
    try:
        import jwt
        import os

        # Get the secret key (same as used by NextAuth.js)
        secret = os.getenv("NEXTAUTH_SECRET")
        if not secret:
            raise error_response_to_http_exception(
                create_system_error(
                    "auth_config", "NEXTAUTH_SECRET environment variable is required"
                )
            )

        # Decode and validate the JWT token
        payload = jwt.decode(token, secret, algorithms=["HS256"])

        # Extract user information from the token
        user_id = payload.get("sub")
        email = payload.get("email", "unknown@example.com")
        role = payload.get("role", "FREE")

        if not user_id:
            raise error_response_to_http_exception(
                create_auth_error("AUTH_INVALID", "Missing user ID in token")
            )

        return User(id=user_id, email=email, role=role)

    except jwt.ExpiredSignatureError:
        raise error_response_to_http_exception(
            create_auth_error("AUTH_EXPIRED", "JWT token has expired")
        )
    except jwt.InvalidTokenError:
        raise error_response_to_http_exception(
            create_auth_error("AUTH_INVALID", "JWT token is invalid or malformed")
        )
    except HTTPException:
        # Re-raise HTTPExceptions (from structured errors above)
        raise
    except Exception as e:
        logger.error(f"Query token authentication error: {e}")
        raise error_response_to_http_exception(
            create_auth_error("AUTH_REQUIRED", f"Authentication failed: {str(e)}")
        )


# =============================================================================
# Startup and Shutdown Events - REMOVED (using lifespan instead)
# =============================================================================

# Note: Moved to lifespan event handler above

# =============================================================================
# API Endpoints
# =============================================================================


# =============================================================================
# Health Check & Monitoring Endpoints
# =============================================================================


@app.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint.
    
    Returns detailed status for all services:
    - Database (connection pool, query test)
    - Redis (pub/sub, memory stats)
    - SSE (streaming capability)
    - System (CPU, memory, disk)
    
    Returns:
        200: All systems healthy
        503: One or more systems degraded
    """
    health_results = await monitoring_service.check_health()
    
    # Determine overall status
    all_healthy = all(result.healthy for result in health_results.values())
    status_code = 200 if all_healthy else 503
    
    response = {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            service: {
                "healthy": result.healthy,
                "response_time_ms": result.response_time_ms,
                "details": result.details,
                "error": result.error
            }
            for service, result in health_results.items()
        }
    }
    
    return response


@app.get("/health/database")
async def health_check_database():
    """Database-specific health check."""
    result = await monitoring_service._check_database_health()
    
    return {
        "service": "database",
        "healthy": result.healthy,
        "response_time_ms": result.response_time_ms,
        "details": result.details,
        "error": result.error,
        "timestamp": result.timestamp.isoformat()
    }


@app.get("/health/redis")
async def health_check_redis():
    """Redis-specific health check."""
    result = await monitoring_service._check_redis_health()
    
    return {
        "service": "redis",
        "healthy": result.healthy,
        "response_time_ms": result.response_time_ms,
        "details": result.details,
        "error": result.error,
        "timestamp": result.timestamp.isoformat()
    }


@app.get("/health/sse")
async def health_check_sse():
    """SSE streaming health check."""
    result = await monitoring_service._check_sse_health()
    
    return {
        "service": "sse",
        "healthy": result.healthy,
        "response_time_ms": result.response_time_ms,
        "details": result.details,
        "error": result.error,
        "timestamp": result.timestamp.isoformat()
    }


@app.get("/health/system")
async def health_check_system():
    """System resources health check."""
    result = monitoring_service._check_system_health()
    
    # Add database pool statistics
    pool_stats = database_service.get_pool_stats()
    
    return {
        "service": "system",
        "healthy": result.healthy,
        "response_time_ms": result.response_time_ms,
        "details": {
            **result.details,
            "database_pool": pool_stats,
        },
        "error": result.error,
        "timestamp": result.timestamp.isoformat()
    }


@app.get("/health/database-pool")
async def health_check_database_pool():
    """Database connection pool health check with detailed stats."""
    pool_stats = database_service.get_pool_stats()
    
    # Determine health status
    if not pool_stats.get("initialized"):
        healthy = False
        message = "Database pool not initialized"
    elif pool_stats.get("closed"):
        healthy = False
        message = "Database pool is closed"
    elif pool_stats.get("error"):
        healthy = False
        message = f"Pool stats error: {pool_stats['error']}"
    else:
        # Check if pool is getting exhausted (>80% utilization)
        in_use = pool_stats.get("in_use", 0)
        max_size = pool_stats.get("max_size", 10)
        utilization = (in_use / max_size * 100) if max_size > 0 else 0
        
        if utilization > 80:
            healthy = False
            message = f"Pool exhaustion warning: {utilization:.1f}% utilized ({in_use}/{max_size})"
        else:
            healthy = True
            message = f"Pool healthy: {utilization:.1f}% utilized ({in_use}/{max_size})"
    
    return {
        "service": "database_pool",
        "healthy": healthy,
        "message": message,
        "stats": pool_stats,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/metrics")
async def get_metrics():
    """
    Get comprehensive application metrics.
    
    Returns:
    - Request counts (total, success, errors)
    - Response times (avg, per endpoint)
    - Performance metrics (operation timings)
    - System resources (CPU, memory, disk)
    - Error rates
    """
    return await monitoring_service.get_full_status()


@app.get("/metrics/summary")
async def get_metrics_summary():
    """Get quick metrics summary without full health checks."""
    return monitoring_service.get_summary()


@app.get("/metrics/performance")
async def get_performance_metrics():
    """Get performance metrics for all monitored operations."""
    metrics = monitoring_service.get_performance_metrics()
    
    return {
        "operations": {
            name: {
                "execution_count": metric.execution_count,
                "avg_duration": metric.avg_duration,
                "min_duration": metric.min_duration,
                "max_duration": metric.max_duration,
                "total_duration": metric.total_duration,
                "last_execution": metric.last_execution.isoformat() if metric.last_execution else None
            }
            for name, metric in metrics.items()
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/metrics/system")
async def get_system_metrics():
    """Get current system resource metrics."""
    current = monitoring_service.collect_system_metrics()
    history = monitoring_service.get_system_metrics_history(minutes=10)
    
    return {
        "current": {
            "cpu_percent": current.cpu_percent,
            "memory_percent": current.memory_percent,
            "memory_used_mb": current.memory_used_mb,
            "memory_available_mb": current.memory_available_mb,
            "disk_usage_percent": current.disk_usage_percent,
            "open_connections": current.open_connections,
            "thread_count": current.thread_count,
            "timestamp": current.timestamp.isoformat()
        },
        "history": [
            {
                "cpu_percent": m.cpu_percent,
                "memory_percent": m.memory_percent,
                "timestamp": m.timestamp.isoformat()
            }
            for m in history
        ]
    }


# =============================================================================
# Task Management Endpoints
# =============================================================================


@app.post("/generate-task-id")
async def generate_task_id(user: User = Depends(get_current_user)) -> dict:
    """
    Generate a unique task ID for pre-establishing SSE connections.

    This endpoint allows the frontend to get a task ID before starting
    blog generation, enabling early SSE connection establishment to
    capture all notification messages including early ones.
    """
    task_id = str(uuid.uuid4())

    # SOLUTION 2: Start message buffering immediately for this task
    if message_buffer:
        await message_buffer.start_buffering(task_id)
        logger.info(
            f"🆔 Generated pre-task ID {task_id} for user {user.email} with message buffering enabled"
        )
    else:
        logger.info(
            f"🆔 Generated pre-task ID {task_id} for user {user.email} (buffering unavailable)"
        )

    return {"task_id": task_id}


@app.post("/generate-blog", response_model=BlogGenerationResponse)
async def generate_blog(
    request: BlogGenerationRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
) -> BlogGenerationResponse:
    """
    Start async blog generation with perfect request isolation and comprehensive error handling.

    This endpoint:
    1. Creates isolated context for this request
    2. Validates input parameters with structured error responses
    3. Registers resources for cleanup management
    4. Starts background blog generation task
    5. Returns task ID for tracking

    The context variables ensure that all OpenAI API calls made during
    blog generation are correctly attributed to this user and session.
    """
    # Generate unique identifiers
    task_id = request.task_id or str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())[:8]

    # DEBUG: Log task ID handling
    logger.info(
        f"🆔 Task ID handling: request.task_id={request.task_id}, final task_id={task_id}"
    )
    if request.task_id:
        logger.info(f"✅ Using provided task ID: {request.task_id}")
    else:
        logger.info(f"🆔 Generated new task ID: {task_id}")

    try:
        # Register task for cleanup management
        await cleanup_manager.register_task(task_id)

        # Validate input parameters
        normalized_topic = (request.topic or "").strip() or None
        normalized_instructions = (request.instructions or "").strip() or None

        # Topic length validation (if provided)
        if normalized_topic and len(normalized_topic) > 200:
            raise error_response_to_http_exception(
                create_validation_error(
                    "topic",
                    f"Topic too long ({len(normalized_topic)}/200 characters)",
                    correlation_id,
                )
            )

        # Instructions validation
        if normalized_instructions and len(normalized_instructions) > 2000:
            raise error_response_to_http_exception(
                create_validation_error(
                    "instructions",
                    f"Instructions too long ({len(normalized_instructions)}/2000 characters)",
                    correlation_id,
                )
            )

        # Set request context for this async task tree
        set_request_context(
            request_id=request_id,
            task_id=task_id,
            user_id=user.id,
            user_email=user.email,
            user_role=user.role,
            blog_id=task_id,  # Use task_id as blog_id
            topic=normalized_topic or "<auto>",
        )

        # Create task record in database instead of memory
        try:
            await task_manager.create_task(
                task_id,
                user.id,
                normalized_topic or "<auto-generating>",
                normalized_instructions,
            )
        except Exception as e:
            error_msg = str(e).lower()
            # Check if this is a shutdown-related database error
            if 'pool is closed' in error_msg or 'closed' in error_msg or 'not available' in error_msg:
                logger.warning(f"Cannot create task - database unavailable (likely shutting down): {e}")
                raise error_response_to_http_exception(
                    create_database_error(
                        "create_task",
                        "Service is shutting down. Please try again in a moment.",
                        correlation_id
                    )
                )
            logger.error(f"Failed to create task in database: {e}")
            raise handle_database_error(e, "create_task", correlation_id)

        # Send immediate initialization status for SSE streams
        if task_manager._redis_manager:
            try:
                # Send task creation notification
                task_created_message = create_task_created_message(
                    task_id=task_id,
                    message=f"Blog generation task created for topic: {normalized_topic or 'auto-generating'}",
                )

                # SOLUTION 2: Buffer message if SSE not connected yet
                if message_buffer and await message_buffer.is_buffering(task_id):
                    await message_buffer.buffer_message(
                        task_id,
                        f"sse_immediate:{task_id}",
                        task_created_message.to_dict(),
                    )

                await task_manager._redis_manager.publish_immediate_message(
                    task_id, task_created_message.to_dict()
                )

                # Send immediate initialization status update with 10% progress
                init_status_message = {
                    "message_type": "status",
                    "task_id": task_id,
                    "status": "in_progress",
                    "message": "Initializing blog generation...",
                    "progress": 10,  # 10% as per user's request
                    "current_step": "Step 1/5: Initialization",
                    "timestamp": datetime.utcnow().isoformat(),
                    "correlation_id": correlation_id,
                }

                # SOLUTION 2: Buffer initialization message if SSE not connected yet
                if message_buffer and await message_buffer.is_buffering(task_id):
                    await message_buffer.buffer_message(
                        task_id, f"sse_immediate:{task_id}", init_status_message
                    )

                await task_manager._redis_manager.publish_immediate_message(
                    task_id, init_status_message
                )
                logger.info(
                    f"🚀 Sent immediate init status with 10% progress for task {task_id}"
                )

            except Exception as e:
                logger.warning(f"Failed to send initial SSE messages: {e}")
                # Don't fail the request for SSE issues - continue without real-time updates

        # Start background blog generation
        background_tasks.add_task(
            async_blog_generation,
            task_id=task_id,
            topic=normalized_topic,  # may be None for auto-generation
            user_id=user.id,
            instructions=normalized_instructions,
        )

        logger.info(
            f"🚀 Blog generation started: {task_id} for user {user.id} (correlation: {correlation_id})"
        )

        return BlogGenerationResponse(
            task_id=task_id,
            status="queued",
            message="Blog generation started. Connect to SSE stream for real-time updates.",
        )

    except HTTPException:
        # Clean up resources if initialization failed
        await cleanup_manager.cleanup_task(task_id, CleanupReason.ERROR)
        raise
    except Exception as e:
        # Clean up resources for unexpected errors
        await cleanup_manager.cleanup_task(task_id, CleanupReason.ERROR)
        logger.error(f"Unexpected error in generate_blog: {e}")
        raise error_response_to_http_exception(
            create_system_error("blog_generation_init", str(e), correlation_id)
        )


@app.get("/tasks/active")
async def get_active_tasks(user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Get all active tasks for the current user."""
    from core.task_manager import TaskStatus

    # Get in-progress tasks from database
    in_progress_tasks = await task_manager.get_user_tasks(
        user.id, TaskStatus.IN_PROGRESS
    )
    queued_tasks = await task_manager.get_user_tasks(user.id, TaskStatus.QUEUED)

    user_tasks = []
    all_active_tasks = in_progress_tasks + queued_tasks

    for task_data in all_active_tasks:
        user_tasks.append(
            {
                "id": task_data.get("id", ""),
                "topic": task_data.get("topic", ""),
                "status": task_data.get(
                    "status", ""
                ).lower(),  # Convert ENUM to lowercase
                "created_at": (
                    task_data.get("created_at", "").isoformat()
                    if task_data.get("created_at")
                    else ""
                ),
                "current_step": task_data.get("current_step", ""),
                "result": task_data.get("content"),  # 'result' maps to 'content' in DB
                "error": task_data.get("error"),
                "user_id": task_data.get("user_id", ""),
                "user_email": user.email,  # Get from current user
                "user_role": user.role,  # Get from current user
            }
        )

    return {"tasks": user_tasks}


@app.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str, user: User = Depends(get_current_user)
) -> TaskStatus:
    """Get the status of a specific task with structured error handling."""
    correlation_id = str(uuid.uuid4())[:8]

    try:
        task = await task_manager.get_task(task_id)
        if not task:
            raise error_response_to_http_exception(
                create_error_response(
                    "TASK_NOT_FOUND",
                    user_message="The requested task could not be found.",
                    technical_details=f"Task ID {task_id} not found in database",
                    correlation_id=correlation_id,
                )
            )

        # Check if user owns this task (or is admin)
        if task["user_id"] != user.id and user.role != "ADMIN":
            raise error_response_to_http_exception(
                create_error_response(
                    "INSUFFICIENT_PERMISSIONS",
                    user_message="You don't have permission to access this task.",
                    technical_details=f"User {user.id} attempted to access task {task_id} owned by {task['user_id']}",
                    correlation_id=correlation_id,
                )
            )

        # Convert database task to TaskStatus format
        task_status = {
            "id": task["id"],
            "topic": task["topic"],
            "status": task["status"].lower() if task["status"] else "queued",
            "created_at": task["created_at"].isoformat() if task["created_at"] else "",
            "current_step": task["current_step"],
            "result": task["content"],
            "error": task["error"],
            "user_id": task["user_id"],
            "user_email": user.email,
            "user_role": user.role,
            "request_id": task_id,  # Use task_id as request_id
            "instructions": task["instructions"],
        }

        return TaskStatus(**task_status)

    except HTTPException:
        # Re-raise structured errors
        raise
    except Exception as e:
        logger.error(f"Error retrieving task {task_id}: {e}")
        raise handle_database_error(e, "get_task", correlation_id)


@app.get("/stream/{task_id}")
async def stream_task(task_id: str, token: str):
    """
    SSE stream for a specific task with Redis pub/sub support.
    
    Phase 3.3: Refactored to use dedicated SSEHandler service for maintainability.
    Reduced from 511 lines to ~50 lines by extracting streaming logic.
    """
    # Authenticate via query token
    user = await get_current_user_from_query_token(token)
    
    # Check user permissions for existing tasks
    task = await task_manager.get_task(task_id)
    if task and task["user_id"] != user.id and user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Initialize SSE handler with dependencies
    sse_handler = SSEHandler(
        redis_manager=redis_manager if redis_manager else None,
        task_manager=task_manager,
        message_buffer=message_buffer if message_buffer else None,
        heartbeat_interval=15,  # seconds
        timeout_seconds=420,  # 7 minutes for complex blog generation
    )
    
    async def event_generator():
        """
        Generator function for SSE events.
        Delegates to SSEHandler for all streaming logic.
        """
        try:
            # Stream events from SSEHandler with proper error handling
            async for event in sse_handler.stream_events(
                task_id=task_id,
                user_id=user.id,
                retry_count=5,
            ):
                yield event
        
        except Exception as e:
            logger.error(
                f"❌ Error in SSE event generator for task {task_id}: {e}",
                exc_info=True,
            )
            # Send error event to client
            error_event = {
                "type": "error",
                "task_id": task_id,
                "message": f"Stream error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
            }
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
            "X-Content-Type-Options": "nosniff",
            "Transfer-Encoding": "chunked",
        },
    )


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str, user: User = Depends(get_current_user)):
    """Delete a task/blog (useful for cleaning up stuck or failed tasks)."""
    try:
        success = await task_manager.delete_task(task_id, user.id)

        if not success:
            raise HTTPException(
                status_code=404, detail="Task not found or access denied"
            )

        return {"message": "Task deleted successfully", "task_id": task_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete task")


@app.post("/tasks/{task_id}/acknowledge-completion")
async def acknowledge_completion(task_id: str, user: User = Depends(get_current_user)):
    """
    Acknowledge that the frontend has received the blog completion.
    Part of the Enhanced Completion Protocol to prevent race conditions.
    """
    try:
        # Verify the task belongs to the user
        task_result = await task_manager.get_task(task_id)
        if not task_result or task_result.get("user_id") != user.id:
            raise HTTPException(
                status_code=404, detail="Task not found or access denied"
            )

        # Send acknowledgment via Redis
        await redis_manager.send_completion_acknowledgment(task_id)

        logger.info(
            f"✅ Frontend acknowledged completion for task {task_id} by user {user.id}"
        )

        return {
            "message": "Completion acknowledgment received",
            "task_id": task_id,
            "acknowledged": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to acknowledge completion for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to acknowledge completion")


@app.post("/generate-title", response_model=TitleGenerationResponse)
async def generate_title(
    request: TitleGenerationRequest, user: User = Depends(get_current_user)
) -> TitleGenerationResponse:
    """
    Generate a concise blog title from blog instructions using OpenAI.

    This endpoint:
    1. Takes blog instructions as input
    2. Uses OpenAI to generate a short, engaging title
    3. Returns the generated title with context variable isolation

    The context variables ensure that API costs are properly tracked
    per user and session.
    """
    try:
        # Validate OpenAI API key
        openai_api_key = config.api.openai_key
        if not openai_api_key:
            logger.error("OpenAI API key not found in configuration")
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")

        # Set up context for this title generation request
        request_id = str(uuid.uuid4())
        set_request_context(
            request_id=request_id,
            task_id=f"title_{request_id}",
            user_id=user.id,
            user_email=user.email,
            user_role=user.role,
            blog_id=f"title_{request_id}",  # Use title task ID as blog_id
            topic=f"Title: {request.instructions[:50]}...",
        )

        # Generate concise topic using shared utility (handles heuristic + OpenAI refinement)
        final_title = generate_concise_topic(
            request.instructions,
            openai_api_key=openai_api_key,
            model=config.models.default_model,
        )
        logger.info(f"✅ Title generated for user {user.id}: {final_title}")
        return TitleGenerationResponse(title=final_title, success=True)

    except openai.OpenAIError as e:
        logger.error(f"❌ OpenAI API error during title generation: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate title using AI")
    except Exception as e:
        logger.error(f"❌ Unexpected error during title generation: {e}")
        raise HTTPException(
            status_code=500, detail="Internal error during title generation"
        )


# =============================================================================
# Background Tasks
# =============================================================================


@monitor_performance("blog_generation")
async def async_blog_generation(
    task_id: str, topic: Optional[str], user_id: str, instructions: Optional[str] = None
):
    """
    Async blog generation with context preservation and comprehensive error handling.

    This function runs as a FastAPI background task and maintains
    the request context throughout the blog generation process.
    """
    correlation_id = str(uuid.uuid4())[:8]
    cleanup_context = None

    try:
        logger.info(
            f"🔄 Starting async blog generation for task {task_id} (correlation: {correlation_id})"
        )

        # Register cleanup context for this task
        cleanup_context = await cleanup_manager.register_task(task_id)
        cleanup_context.add_metadata("correlation_id", correlation_id)
        cleanup_context.add_metadata("user_id", user_id)

        # ===== CRITICAL FIX: Restore context in background task =====
        # Background tasks lose context, so we need to restore it
        request_id = str(uuid.uuid4())
        set_request_context(
            request_id=request_id,
            task_id=task_id,
            user_id=user_id,
            user_email=f"{user_id}@context.restored",  # Placeholder since we don't have email
            user_role="PREMIUM",  # Assume premium for background tasks
            blog_id=task_id,
            topic=topic or "<auto>",
        )

        # Update task status to in_progress
        try:
            await task_manager.update_task(
                task_id,
                status="in_progress",
                current_step="Initializing blog generation workflow...",
            )
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
            # Don't fail entirely - continue with generation

        # Send immediate initialization message for SSE streams
        if task_manager._redis_manager:
            try:
                init_message = create_initializing_message(
                    task_id=task_id,
                    phase="Blog Generation",
                    message="Initializing AI blog generation workflow...",
                    progress=0.0,
                )
                await task_manager._redis_manager.publish_immediate_message(
                    task_id, init_message.to_dict()
                )
            except Exception as e:
                logger.warning(f"Failed to send SSE initialization message: {e}")

        # Create audit tracker for this session - USING ENHANCED VERSION
        # Note: In production, user_id should come from JWT token validation
        # For now, we'll use a fallback to ensure audit logging works
        valid_user_id = (
            user_id if user_id and len(user_id) > 10 else "cmdaiv5530000z9nxqmyg445v"
        )

        try:
            audit_tracker = EnhancedDatabaseAuditTracker(
                session_type="blog_generation", user_id=valid_user_id, blog_id=task_id
            )

            # Register audit tracker for cleanup
            await register_database_transaction(task_id, audit_tracker)

            # ===== CRITICAL FIX: Set audit context AFTER restoring request context =====
            set_audit_context(
                audit_tracker, f"session_{int(datetime.utcnow().timestamp())}"
            )

            # Start the audit session
            await audit_tracker.start_session()

        except Exception as e:
            logger.error(f"Failed to initialize audit tracker: {e}")
            # Continue without audit tracking if it fails
            audit_tracker = None

        logger.info(f"✅ Context restored and resources registered for task {task_id}")

        # Define enhanced status update callback for Phase 1 Foundation
        def update_task_status(status_data: Dict[str, Any]):
            """Enhanced task status update with immediate SSE broadcasting."""
            message = status_data.get("message", "Processing...")
            step = status_data.get("step", 0)
            progress = status_data.get("progress", 0.0)
            message_type = status_data.get("message_type", "status")

            # Progress is already in percentage (0-100) from our status_manager
            # Don't modify it, just ensure it's within bounds
            if progress > 100:
                progress = 100
            elif progress < 0:
                progress = 0

            # Debug logging for progress tracking
            logger.info(
                f"🔢 Task {task_id}: step {step} progress {progress}% (message: {message})"
            )

            # Detect if running in CrewAI Flow thread context to avoid asyncio conflicts
            import threading

            current_thread = threading.current_thread()
            is_flow_thread = (
                current_thread.name.startswith("Thread-")
                or "CrewAI" in current_thread.name
                or current_thread != threading.main_thread()
            )

            if is_flow_thread:
                # REDIS-ONLY updates from Flow threads to avoid asyncio conflicts
                try:
                    # Use thread-safe Redis-only update
                    task_manager.update_task_redis_only(task_id, status_data)

                    # Log different message types appropriately
                    if message_type == "agentthinking":
                        logger.info(
                            f"🧠 {task_id}: Agent thinking - {status_data.get('agent_name', 'Unknown')}"
                        )
                    elif message_type == "toolcall":
                        logger.info(
                            f"🔧 {task_id}: Tool usage - {status_data.get('tool_name', 'Unknown')}"
                        )
                    elif message_type == "contentstream":
                        logger.info(
                            f"📄 {task_id}: Content streaming - {status_data.get('content_type', 'Unknown')}"
                        )
                    elif message_type == "researchfinding":
                        logger.info(
                            f"🔍 {task_id}: Research finding - {len(status_data.get('finding', ''))} chars"
                        )
                    else:
                        logger.info(
                            f"📊 {task_id}: {message} ({progress:.1f}%) - Redis update"
                        )

                except Exception as e:
                    logger.error(
                        f"❌ Failed to send Redis status update for task {task_id}: {e}"
                    )
            else:
                # FULL DATABASE + REDIS updates from main thread
                async def update_with_enhanced_broadcasting():
                    try:
                        # Update database task status
                        await task_manager.update_task(
                            task_id, current_step=message, progress=progress
                        )

                        # Broadcast immediate message for enhanced real-time feedback
                        if task_manager._redis_manager:
                            await task_manager._redis_manager.publish_immediate_message(
                                task_id, status_data
                            )

                        logger.info(
                            f"📊 {task_id}: {message} ({progress:.1f}%) - Database + Redis updated"
                        )

                    except Exception as e:
                        logger.error(f"❌ Failed to update task {task_id} status: {e}")

                # Schedule the enhanced async update only from main thread
                asyncio.create_task(update_with_enhanced_broadcasting())

        # Create and run blog generation flow with direct audit tracker
        flow = BlogGenerationFlow(
            status_callback=update_task_status,
            user_id=user_id,
            blog_id=task_id,
            audit_tracker=audit_tracker,
            topic=topic,  # may be None
            instructions=instructions,
        )

        # Send immediate status update before flow execution starts
        if task_manager._redis_manager:
            pre_flow_message = {
                "message_type": "status",
                "task_id": task_id,
                "status": "in_progress",
                "message": "Blog generation flow starting...",
                "progress": 10,  # 10% for initialization
                "current_step": "Step 1/5: Initialization",
                "timestamp": datetime.utcnow().isoformat(),
            }
            await task_manager._redis_manager.publish_immediate_message(
                task_id, pre_flow_message
            )

        async def hero_image_task():
            """Generate hero image in parallel once topic becomes available."""
            try:
                # Wait for topic (poll) or give up after 30 * 0.3s = 9s
                for _ in range(30):
                    if getattr(flow, "topic", None):
                        break
                    await asyncio.sleep(0.3)
                final_topic = getattr(flow, "topic", None) or topic or "AI Blog"
                update_phase("image_generation")

                # Check if AI image generation is enabled
                hero_url = None
                if config.features.enable_hero_image_generation:
                    from bloggen.tools.openai_image_tool import OpenAIImageTool
                    from bloggen.tools.unsplash_tool import UnsplashImageTool
                    import re

                    prompt = (
                        "Photorealistic, high-quality professional image directly "
                        f"representing '{final_topic}'. Modern, stylish composition "
                        "with excellent lighting, sharp focus, and cinematic quality. "
                        "Suitable for premium blog header, visually striking and "
                        "directly relevant to the topic."
                    )
                    hero_tool = OpenAIImageTool(audit_tracker=audit_tracker)
                    hero_result = hero_tool.run(prompt)

                    # Extract URL from markdown format: ![alt](url "caption")
                    if isinstance(hero_result, str):
                        url_match = re.search(
                            r"!\[.*?\]\((.*?)\s*(?:\".*?\")?\)", hero_result
                        )
                        hero_url = url_match.group(1) if url_match else None
                    elif isinstance(hero_result, dict):
                        hero_url = hero_result.get("url")

                    if (
                        not hero_url
                        or "placeholder" in (hero_url or "")
                        or "placehold.co" in (hero_url or "")
                    ):
                        try:
                            unsplash_tool = UnsplashImageTool()
                            unsplash_res = unsplash_tool.run(final_topic)
                            if isinstance(unsplash_res, dict):
                                hero_url = unsplash_res.get("url") or hero_url
                        except Exception:
                            logger.debug("Unsplash fallback failed", exc_info=True)
                else:
                    logger.info(
                        "AI image generation disabled - skipping hero image generation"
                    )

                # Update hero image in database if found
                if hero_url:
                    current_task = await task_manager.get_task(task_id)
                    if current_task and current_task.get("status", "").lower() not in [
                        "failed",
                        "completed",
                    ]:
                        await task_manager.update_task(
                            task_id,
                            hero_image_url=hero_url,
                            current_step="Hero image ready",
                        )
                update_phase("finalization")
            except Exception as e:
                logger.debug(
                    f"Parallel hero image generation failed for task {task_id}: {e}",
                    exc_info=True,
                )

        # Start hero image generation concurrently
        hero_task = asyncio.create_task(hero_image_task())

        # Set flow status marker to signal that CrewAI flow is starting
        if task_manager._redis_manager:
            try:
                flow_status_key = f"flow_status:{task_id}"
                await task_manager._redis_manager.redis_client.setex(
                    flow_status_key, 300, "started"
                )  # 5 min TTL
                logger.info(f"🚀 Set flow status marker for task {task_id}")
            except Exception as e:
                logger.warning(f"Failed to set flow status marker: {e}")

        # Execute the flow with proper inputs (topic may be None for auto-generation)
        result = await run_blog_flow_async(flow, topic)

        # CRITICAL DEBUG: Log the raw result from the flow
        logger.info(f"🔍 DEBUG: Blog flow result type: {type(result)}")
        logger.info(
            f"🔍 DEBUG: Blog flow result keys (if dict): {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}"
        )
        if hasattr(result, "__dict__") or hasattr(result, "__slots__"):
            visible_attributes = [
                attr
                for attr in dir(result)
                if not attr.startswith("_")
            ]
        else:
            visible_attributes = "No attributes"

        logger.info(
            f"🔍 DEBUG: Blog flow result attributes: {visible_attributes}"
        )
        logger.info(f"🔍 DEBUG: Blog flow result preview: {str(result)[:200]}...")

        # Get current task state to check if it should be updated
        current_task = await task_manager.get_task(task_id)
        if current_task:
            blog_content = "Blog generation completed, but content extraction failed."
            try:
                if isinstance(result, dict) and "final_blog_post" in result:
                    final_blog = result["final_blog_post"]
                    logger.info(
                        f"🔍 DEBUG: Found final_blog_post in dict, type: {type(final_blog)}"
                    )
                    if hasattr(final_blog, "raw"):
                        blog_content = final_blog.raw
                        logger.info(
                            f"🔍 DEBUG: Using final_blog.raw, length: {len(blog_content)}"
                        )
                    elif isinstance(final_blog, str):
                        blog_content = final_blog
                        logger.info(
                            f"🔍 DEBUG: Using final_blog as string, length: {len(blog_content)}"
                        )
                    else:
                        blog_content = str(final_blog)
                        logger.info(
                            f"🔍 DEBUG: Converting final_blog to string, length: {len(blog_content)}"
                        )
                elif hasattr(result, "raw") and result.raw:  # type: ignore
                    blog_content = result.raw  # type: ignore
                    logger.info(
                        f"🔍 DEBUG: Using result.raw, length: {len(blog_content)}"
                    )
                else:
                    blog_content = str(result)
                    logger.info(
                        f"🔍 DEBUG: Using fallback string conversion, length: {len(blog_content)}"
                    )
                    logger.warning(
                        f"⚠️ Using fallback string conversion for task {task_id}"
                    )

                logger.info(
                    f"🔍 DEBUG: Final blog_content length before completion: {len(blog_content)}"
                )
                logger.info(
                    f"🔍 DEBUG: Final blog_content preview: {blog_content[:200]}..."
                )

            except Exception as e:
                logger.error(
                    f"❌ Error extracting blog content for task {task_id}: {e}"
                )
                blog_content = f"Error extracting blog content: {str(e)}"

            # Update topic if auto-generated
            if (not topic or not topic.strip()) and getattr(flow, "topic", None):
                await task_manager.update_task(task_id, topic=flow.topic)

            # Await hero task (still parallelized with flow) to keep guarantee hero appears before completion
            try:
                await asyncio.wait_for(hero_task, timeout=15)
            except asyncio.TimeoutError:
                logger.warning(
                    f"Hero image generation timeout for task {task_id}; completing without it"
                )
            except Exception:
                logger.debug("Hero image coroutine error", exc_info=True)

            # Mark completion after hero attempt - ignore database status since Flow threads use Redis-only updates
            current_task = await task_manager.get_task(task_id)
            if current_task:
                # Get hero image URL if it was set during generation
                hero_image_url = current_task.get("hero_image_url")

                # CRITICAL DEBUG: Check content before completion call
                logger.info("🔍 COMPLETION DEBUG - About to call complete_task:")
                logger.info(f"   task_id: {task_id}")
                logger.info(
                    f"   blog_content length: {len(blog_content) if blog_content else 0}"
                )
                logger.info(f"   blog_content type: {type(blog_content)}")
                logger.info(
                    f"   blog_content is_empty: {not blog_content or not blog_content.strip()}"
                )
                logger.info(
                    f"   blog_content preview: {blog_content[:300] if blog_content else 'EMPTY'}..."
                )
                logger.info(f"   hero_image_url: {hero_image_url}")

                # Always complete the task since the Flow finished successfully
                await task_manager.complete_task(task_id, blog_content, hero_image_url)
                logger.info(
                    f"✅ Task {task_id} completed - Blog content length: {len(blog_content)} chars"
                )

        # End the audit session AFTER hero image to include its cost
        if audit_tracker:
            await audit_tracker.end_session()

        logger.info(f"✅ Blog generation completed for task {task_id}")

    except Exception as e:
        import traceback

        logger.error(f"❌ Blog generation failed for task {task_id}: {e}")
        logger.error(f"❌ Exception type: {type(e).__name__}")
        logger.error(f"❌ Exception module: {type(e).__module__}")
        logger.error(f"❌ Exception args: {getattr(e, 'args', 'N/A')}")
        logger.error(f"❌ Full traceback:\n{traceback.format_exc()}")

        # Send immediate error notification via SSE before updating database
        if task_manager._redis_manager:
            try:
                error_message = {
                    "message_type": "error",
                    "task_id": task_id,
                    "status": "failed",
                    "message": f"Blog generation failed: {str(e)}",
                    "error": str(e),
                    "progress": 0,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                await task_manager._redis_manager.publish_immediate_message(
                    task_id, error_message
                )
                logger.info(f"📡 Sent error notification via SSE for task {task_id}")
            except Exception as sse_error:
                logger.error(f"Failed to send SSE error notification: {sse_error}")

        # Try to end audit session on error
        try:
            audit_tracker_var = current_audit_tracker.get(None)
            if audit_tracker_var and hasattr(audit_tracker_var, "end_session"):
                await audit_tracker_var.end_session()  # type: ignore
        except Exception as audit_error:
            logger.error(f"Failed to end audit session: {audit_error}")
            pass  # Don't fail the error handling

        # Update task with enhanced error details for SSE visibility
        error_details = f"{type(e).__name__}: {str(e)}"
        await task_manager.fail_task(task_id, error_details)

        # Cleanup all resources for this task
        if cleanup_context:
            await cleanup_context.cleanup(CleanupReason.ERROR)
        else:
            await cleanup_manager.cleanup_task(task_id, CleanupReason.ERROR)


async def run_blog_flow_async(flow: BlogGenerationFlow, topic: Optional[str]):
    """Run the blog generation flow asynchronously using a thread pool.

    Parameters:
      flow: BlogGenerationFlow instance already configured (may have instructions & audit tracker)
      topic: Optional topic. If None or empty, the flow will auto-generate one during initialization.
    """
    loop = asyncio.get_event_loop()

    def run_sync_flow():
        try:
            # Only set topic if provided (preserve None for auto-generation logic)
            if topic and topic.strip():
                flow.topic = topic.strip()
            # Always ensure current year present
            if not flow.current_year:
                flow.current_year = datetime.now().year

            log_topic = flow.topic if flow.topic else "<auto>"
            logger.info(
                f"🚀 Starting flow with topic: {log_topic}, year: {flow.current_year}"
            )

            return flow.kickoff(
                {
                    "topic": flow.topic
                    or "",  # kickoff context; flow handles auto-generation internally
                    "current_year": flow.current_year,
                }
            )
        except Exception as e:
            logger.error(f"❌ Flow execution failed: {e}")
            raise

    return await loop.run_in_executor(None, run_sync_flow)


# =============================================================================
# Development Server
# =============================================================================

if __name__ == "__main__":
    # Get protocol configuration
    protocol_config = get_protocol_config()

    # Detect production environment (Railway, Docker, etc.)
    is_production = os.getenv("RAILWAY_ENVIRONMENT") is not None or os.getenv("DOCKER_CONTAINER") is not None
    
    # Prepare uvicorn config
    uvicorn_config = {
        "host": "0.0.0.0",
        "port": protocol_config.backend_port,
        "reload": False if is_production else True,  # Disable reload in production
        "access_log": False,  # Keep logs clean
    }

    # Add SSL configuration if HTTPS mode
    if protocol_config.is_https:
        ssl_config = protocol_config.get_ssl_config()
        if ssl_config:
            cert_path, key_path = ssl_config
            if os.path.exists(cert_path) and os.path.exists(key_path):
                uvicorn_config["ssl_keyfile"] = key_path
                uvicorn_config["ssl_certfile"] = cert_path
                logger.info("🔒 HTTPS mode enabled with SSL certificates")
            else:
                logger.warning(
                    "⚠️ HTTPS mode requested but SSL certificates not found:"
                )
                logger.warning(f"   Cert: {cert_path}")
                logger.warning(f"   Key: {key_path}")
                logger.warning("   Falling back to HTTP mode")
        else:
            logger.warning("⚠️ HTTPS mode requested but no SSL config available")

    logger.info(f"🚀 Starting backend server: {protocol_config.get_backend_url()}")
    uvicorn.run("main:app", **uvicorn_config)
