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
import uuid
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

# Load environment variables first
from dotenv import load_dotenv
import os
# Load .env from the backend directory (one level up from src/)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn

# OpenAI for title generation
import openai

# Context variables for request isolation
from core.context_vars import (
    set_request_context,
    set_audit_context,
    update_phase,
    get_request_context,
    current_request_id,
    current_user_id,
    current_audit_tracker
)

# Enhanced SSE message types for real-time AI workflow visualization
from core.sse_message_types import (
    BaseSSEMessage,
    create_status_message,
    create_task_created_message,
    create_initializing_message,
    create_agent_thinking_message,
    create_tool_call_message,
    create_content_stream_message,
    create_research_finding_message,
    create_completed_message,
    create_error_message
)

# Core imports
from core.config import config, get_cors_origins
from core.llm_interceptor import setup_llm_interceptor
from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker  # unified import
from core.logging_utils import setup_api_logger

from core.redis_manager import redis_manager
from core.content_streaming_manager import content_streaming_manager
from config.protocol_config import get_protocol_config, is_https_mode

# Blog generation
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
    if 'logger' not in globals() or logger is None:
        try:
            from core.logging_utils import setup_api_logger as _setup_logger
            logger = _setup_logger("main")  # type: ignore
        except Exception:
            # Fallback basic logger
            import logging as _logging
            logger = _logging.getLogger("main")  # type: ignore
            if not logger.handlers:
                _handler = _logging.StreamHandler()
                _handler.setFormatter(_logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
                logger.addHandler(_handler)
            logger.setLevel(_logging.INFO)

    logger.info("🚀 Starting FastAPI Blog Generation Service")
    
    # Set up LLM interceptor with context variables
    setup_llm_interceptor()
    logger.info("✅ Context-aware LLM interceptor initialized")
    
    # Patch historical serper_api zero-cost entries (best-effort)
    try:
        async def _pool_provider():
            tracker = EnhancedDatabaseAuditTracker(session_type="startup_patch", user_id="system", blog_id=None)
            return await tracker._get_database_connection()  # type: ignore
        updated = await EnhancedDatabaseAuditTracker.patch_serper_api_costs(_pool_provider)
        if updated:
            logger.info(f"🔧 Patched {updated} historical serper_api call(s) to cost 0.001")
        # Normalize legacy phase names to current canonical phases
        phase_updates = await EnhancedDatabaseAuditTracker.normalize_phase_names(_pool_provider)
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

    # Connect managers to TaskManager for real-time updates
    task_manager.set_redis_manager(redis_manager)
    task_manager.set_content_streaming_manager(content_streaming_manager)
    logger.info("✅ Redis and Content Streaming managers connected to TaskManager")

    logger.info("✅ FastAPI application startup complete")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("🛑 Shutting down FastAPI Blog Generation Service")
    
    # Disconnect Redis
    try:
        await redis_manager.disconnect()
        logger.info("✅ Redis connection closed")
    except Exception as e:
        logger.warning(f"Redis shutdown error: {e}")
    
        # Close database connection pools
    try:
        # Close all active database connections
        from core.database_manager import DatabaseConnectionManager
        from core.direct_audit_database import DirectSupabaseAuditManager
        
        # Force close any remaining database pools (best effort)
        import gc
        for obj in gc.get_objects():
            if hasattr(obj, 'pool') and obj.pool and hasattr(obj.pool, 'close'):
                try:
                    await obj.pool.close()
                    logger.info(f"✅ Closed database pool from {type(obj).__name__}")
                except:
                    pass
        
        logger.info("✅ Database connections cleanup completed")
    except Exception as e:
        logger.warning(f"Database cleanup error: {e}")

app = FastAPI(
    title="CrewAI Blog Generation Service",
    description="AI-powered blog generation with real-time cost tracking",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
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

# Global state for task tracking (will be replaced with Redis later)
# active_tasks: Dict[str, Dict[str, Any]] = {}  # DEPRECATED: Using database-backed task manager

# Import task manager for database-backed state
from core.task_manager import task_manager

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
    topic: Optional[str] = Field(None, max_length=200, description="Blog topic (optional; auto-generated if omitted)")
    instructions: Optional[str] = Field(None, max_length=2000, description="Full user + config built instructions")
    task_id: Optional[str] = Field(None, description="Optional task ID")

class BlogGenerationResponse(BaseModel):
    """Response model for blog generation."""
    task_id: str
    status: str
    message: str

class TitleGenerationRequest(BaseModel):
    """Request model for title generation."""
    instructions: str = Field(..., min_length=3, max_length=500, description="Blog instructions")

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

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    Get current authenticated user from JWT token.
    Validates JWT tokens using the NEXTAUTH_SECRET.
    """
    try:
        import jwt
        import os
        
        # Get the secret key (same as used by NextAuth.js)
        secret = os.getenv("NEXTAUTH_SECRET", "Ver0EvKSf1T5hN4/6NDsnPyZf8S7dJZ/Ewksc2Y2L7w=")
        
        # Decode and validate the JWT token
        payload = jwt.decode(credentials.credentials, secret, algorithms=["HS256"])
        
        # Extract user information from the token
        user_id = payload.get("sub")
        email = payload.get("email", "unknown@example.com")
        role = payload.get("role", "FREE")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
        
        return User(id=user_id, email=email, role=role)
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

async def get_current_user_from_query_token(token: str) -> User:
    """
    Get current authenticated user from JWT token passed as query parameter.
    Used for SSE authentication since EventSource doesn't support custom headers.
    """
    try:
        import jwt
        import os
        
        # Get the secret key (same as used by NextAuth.js)
        secret = os.getenv("NEXTAUTH_SECRET", "Ver0EvKSf1T5hN4/6NDsnPyZf8S7dJZ/Ewksc2Y2L7w=")
        
        # Decode and validate the JWT token
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        
        # Extract user information from the token
        user_id = payload.get("sub")
        email = payload.get("email", "unknown@example.com")
        role = payload.get("role", "FREE")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
        
        return User(id=user_id, email=email, role=role)
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

# =============================================================================
# Startup and Shutdown Events - REMOVED (using lifespan instead)
# =============================================================================

# Note: Moved to lifespan event handler above

# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    import time
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "epoch": int(time.time())}

@app.post("/generate-blog", response_model=BlogGenerationResponse)
async def generate_blog(
    request: BlogGenerationRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user)
) -> BlogGenerationResponse:
    """
    Start async blog generation with perfect request isolation.
    
    This endpoint:
    1. Creates isolated context for this request
    2. Starts background blog generation task
    3. Returns task ID for tracking
    
    The context variables ensure that all OpenAI API calls made during
    blog generation are correctly attributed to this user and session.
    """
    # Generate unique identifiers
    task_id = request.task_id or str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    
    # Set request context for this async task tree
    normalized_topic = (request.topic or "").strip() or None
    set_request_context(
        request_id=request_id,
        task_id=task_id,
        user_id=user.id,
        user_email=user.email,
        user_role=user.role,
        blog_id=task_id,  # Use task_id as blog_id
        topic=normalized_topic or "<auto>"
    )
    
    # Create task record in database instead of memory
    await task_manager.create_task(task_id, user.id, normalized_topic or '<auto-generating>', (request.instructions or '').strip() or None)
    
    # Send immediate task creation notification for SSE streams
    if task_manager._redis_manager:
        task_created_message = create_task_created_message(
            task_id=task_id,
            message=f"Blog generation task created for topic: {normalized_topic or 'auto-generating'}"
        )
        await task_manager._redis_manager.publish_immediate_message(task_id, task_created_message.to_dict())
    
    # Start background blog generation
    background_tasks.add_task(
        async_blog_generation,
        task_id=task_id,
        topic=normalized_topic,  # may be None for auto-generation
        user_id=user.id,
        instructions=(request.instructions or '').strip() or None
    )
    
    logger.info(f"🚀 Blog generation started: {task_id} for user {user.id}")
    
    return BlogGenerationResponse(
        task_id=task_id,
        status="queued",
        message="Blog generation started. Connect to SSE stream for real-time updates."
    )

@app.get("/tasks/active")
async def get_active_tasks(user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Get all active tasks for the current user."""
    from core.task_manager import TaskStatus
    
    # Get in-progress tasks from database
    in_progress_tasks = await task_manager.get_user_tasks(user.id, TaskStatus.IN_PROGRESS)
    queued_tasks = await task_manager.get_user_tasks(user.id, TaskStatus.QUEUED)
    
    user_tasks = []
    all_active_tasks = in_progress_tasks + queued_tasks
    
    for task_data in all_active_tasks:
        user_tasks.append({
            "id": task_data.get('id', ''),
            "topic": task_data.get('topic', ''),
            "status": task_data.get('status', '').lower(),  # Convert ENUM to lowercase
            "created_at": task_data.get('created_at', '').isoformat() if task_data.get('created_at') else '',
            "current_step": task_data.get('current_step', ''),
            "result": task_data.get('content'),  # 'result' maps to 'content' in DB
            "error": task_data.get('error'),
            "user_id": task_data.get('user_id', ''),
            "user_email": user.email,  # Get from current user
            "user_role": user.role     # Get from current user
        })
    
    return {"tasks": user_tasks}

@app.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    user: User = Depends(get_current_user)
) -> TaskStatus:
    """Get the status of a specific task."""
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if user owns this task (or is admin)
    if task['user_id'] != user.id and user.role != 'ADMIN':
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Convert database task to TaskStatus format
    task_status = {
        'id': task['id'],
        'topic': task['topic'],
        'status': task['status'].lower() if task['status'] else 'queued',
        'created_at': task['created_at'].isoformat() if task['created_at'] else '',
        'current_step': task['current_step'],
        'result': task['content'],
        'error': task['error'],
        'user_id': task['user_id'],
        'user_email': user.email,
        'user_role': user.role,
        'request_id': task_id,  # Use task_id as request_id
        'instructions': task['instructions']
    }
    
    return TaskStatus(**task_status)

@app.get("/stream/{task_id}")
async def stream_task(task_id: str, token: str):
    """SSE stream for a specific task with Redis pub/sub support."""
    # Authenticate via query token
    user = await get_current_user_from_query_token(token)
    
    # Handle race condition: task might not exist yet if SSE connection is made immediately after creation
    task = await task_manager.get_task(task_id)
    retry_count = 0
    max_retries = 5
    
    while not task and retry_count < max_retries:
        logger.info(f"Task {task_id} not found, retrying in 0.5s (attempt {retry_count + 1}/{max_retries})")
        await asyncio.sleep(0.5)
        task = await task_manager.get_task(task_id)
        retry_count += 1
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task['user_id'] != user.id and user.role != 'ADMIN':
        raise HTTPException(status_code=403, detail="Access denied")

    async def event_generator():
        last_sent_status = None
        last_sent_step = None
        last_sent_progress = None
        last_sent_hero = None
        sent_initialization = False
        redis_pubsub = None
        
        try:
            # Immediately send connection acknowledgment
            connection_message = {
                "type": "connected",
                "message_type": "connected",
                "task_id": task_id,
                "message": "SSE connection established",
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(connection_message)}\n\n"
            
            # Try to set up Redis pub/sub subscription
            redis_pubsub = None
            if task_manager._redis_manager and hasattr(task_manager._redis_manager, 'redis_client') and task_manager._redis_manager.redis_client:
                try:
                    redis_pubsub = task_manager._redis_manager.redis_client.pubsub()
                    channel = f"task_updates:{task_id}"
                    
                    # Set timeout for Redis operations
                    await asyncio.wait_for(redis_pubsub.subscribe(channel), timeout=5.0)
                    logger.info(f"📡 SSE subscribed to Redis channel: {channel}")
                except asyncio.TimeoutError:
                    logger.warning(f"Redis subscription timeout for task {task_id}, falling back to database polling")
                    if redis_pubsub:
                        try:
                            await redis_pubsub.close()
                        except Exception as close_error:
                            logger.error(f"Error closing failed Redis pubsub: {close_error}")
                    redis_pubsub = None
                except Exception as e:
                    logger.warning(f"Redis subscription failed, falling back to database polling: {e}")
                    if redis_pubsub:
                        try:
                            await redis_pubsub.close()
                        except Exception as close_error:
                            logger.error(f"Error closing failed Redis pubsub: {close_error}")
                    redis_pubsub = None
            
            # Send initial task state
            current_task = await task_manager.get_task(task_id)
            if not current_task:
                logger.error(f"Task {task_id} not found for SSE stream")
                return
            
            # Helper function to send task updates
            def send_update(task_data):
                nonlocal last_sent_status, last_sent_step, last_sent_progress, last_sent_hero, sent_initialization
                
                status = task_data.get('status', '').lower()
                step = task_data.get('current_step')
                progress = task_data.get('progress', 0)
                hero_url = task_data.get('hero_image_url')
                
                # Send initialization message once when task starts
                if not sent_initialization and status in ['started', 'in_progress']:
                    sent_initialization = True  # Mark initialization as sent
                    init_message = create_initializing_message(
                        task_id=task_id,
                        phase="Blog Generation",
                        message="Initializing AI blog generation workflow...",
                        progress=0.0
                    )
                    return f"data: {json.dumps(init_message.to_dict())}\n\n"
                
                # Create appropriate message type based on status
                if status == 'completed':
                    final_content = task_data.get('content')
                    generation_time = task_data.get('generation_time')
                    message = create_completed_message(
                        task_id=task_id,
                        final_content=final_content,
                        generation_time=generation_time
                    )
                elif status == 'failed':
                    error_details = task_data.get('error', 'Unknown error occurred')
                    message = create_error_message(
                        task_id=task_id,
                        error_msg=error_details,
                        recoverable=False
                    )
                else:
                    # Regular status update
                    message = create_status_message(
                        task_id=task_id,
                        status=status,
                        message=task_data.get('message', f"Status: {status}"),
                        step=step,
                        progress=progress
                    )
                
                # Add hero image information if available
                payload = message.to_dict()
                if hero_url:
                    payload['hero_image_url'] = hero_url
                
                # Update tracking variables
                last_sent_status = status
                last_sent_step = step
                last_sent_progress = progress
                last_sent_hero = hero_url
                
                return f"data: {json.dumps(payload)}\n\n"
            
            # Send current task status immediately
            update = send_update(current_task)
            if update:
                yield update
            
            # Main update loop - Redis if available, otherwise database polling
            if redis_pubsub:
                logger.info(f"📡 Using Redis pub/sub for real-time updates")
                # Redis listening loop with reasonable timeout for complex blog generation
                keepalive_counter = 0
                timeout_seconds = 420  # 7 minutes - reasonable for complex blogs with fact-checking
                start_time = datetime.utcnow()
                logger.info(f"🕐 Redis listener started with {timeout_seconds}s timeout for task {task_id}")
                
                async for message in redis_pubsub.listen():
                    # Check timeout with better logging
                    elapsed_seconds = (datetime.utcnow() - start_time).total_seconds()
                    if elapsed_seconds > timeout_seconds:
                        logger.warning(f"⏰ Redis listener timeout for task {task_id} after {elapsed_seconds:.1f}s (limit: {timeout_seconds}s)")
                        break
                        
                    if message['type'] == 'message':
                        try:
                            # Parse Redis message 
                            redis_data = json.loads(message['data'].decode('utf-8'))
                            logger.info(f"📨 Redis update for {task_id}: {redis_data.get('message_type', redis_data.get('status', 'unknown'))} (elapsed: {elapsed_seconds:.1f}s)")
                            
                            # CRITICAL FIX: Use Redis message data directly for completion
                            # This prevents race condition with database queries
                            if redis_data.get('message_type') == 'completed':
                                # CRITICAL DEBUG: Log the raw Redis completion message
                                logger.info(f"🔍 RAW REDIS COMPLETION MESSAGE:")
                                logger.info(f"   redis_data keys: {list(redis_data.keys())}")
                                logger.info(f"   final_content: {redis_data.get('final_content', 'MISSING')[:100] if redis_data.get('final_content') else 'EMPTY'}")
                                logger.info(f"   content: {redis_data.get('content', 'MISSING')[:100] if redis_data.get('content') else 'EMPTY'}")
                                logger.info(f"   message: {redis_data.get('message', 'MISSING')}")
                                logger.info(f"   full message: {str(redis_data)[:500]}...")
                                
                                # Use the Redis message content directly - no database query needed
                                final_content = redis_data.get('final_content', '')
                                hero_image_url = redis_data.get('hero_image_url')
                                
                                logger.info(f"🔍 EXTRACTED CONTENT LENGTH: {len(final_content)}")
                                
                                # Create completion message with Redis data
                                completion_task_data = {
                                    'status': 'completed',
                                    'current_step': 'Blog generation completed successfully!',
                                    'progress': 100,
                                    'message': f'Blog generation completed ({len(final_content)} words)',
                                    'task_id': task_id,
                                    'content': final_content,
                                    'hero_image_url': hero_image_url
                                }
                                
                                # Send the completion message immediately
                                final_update = send_update(completion_task_data)
                                if final_update:
                                    # DEBUG: Log the exact SSE message being sent
                                    logger.info(f"🔍 EXACT SSE COMPLETION MESSAGE: {final_update[:500]}...")
                                    yield final_update
                                logger.info(f"✅ Sent completion with content ({len(final_content)} chars) for {task_id}")
                                
                                # Add a small delay to ensure frontend receives the completion message
                                # before the SSE connection closes
                                logger.info(f"⏳ Waiting 5 seconds for completion message delivery for {task_id}")
                                await asyncio.sleep(5)
                                logger.info(f"✅ Completion message delivery delay completed for {task_id}")
                                break
                            elif redis_data.get('message_type') == 'error':
                                # Handle error completion
                                error_task_data = {
                                    'status': 'failed',
                                    'current_step': 'Generation failed',
                                    'progress': 0,
                                    'message': redis_data.get('error_msg', 'Unknown error'),
                                    'task_id': task_id,
                                    'error': redis_data.get('error_msg', 'Unknown error')
                                }
                                
                                final_update = send_update(error_task_data)
                                if final_update:
                                    yield final_update
                                
                                # Add a small delay to ensure frontend receives the error message
                                # before the SSE connection closes
                                logger.info(f"⏳ Waiting 5 seconds for error message delivery for {task_id}")
                                await asyncio.sleep(5)
                                logger.info(f"✅ Error message delivery delay completed for {task_id}")
                                break
                            else:
                                # Regular status updates - use Redis data for real-time updates
                                redis_task_data = {
                                    'status': redis_data.get('status', 'in_progress'),
                                    'current_step': redis_data.get('message', 'Processing...'),
                                    'progress': redis_data.get('progress', 0),
                                    'message': redis_data.get('message', 'Processing...'),
                                    'task_id': task_id
                                }
                                
                                # Send the Redis data immediately
                                update = send_update(redis_task_data)
                                if update:
                                    yield update
                            
                        except Exception as e:
                            logger.error(f"❌ Error processing Redis message: {e}")
                    else:
                        # Send periodic keepalives
                        keepalive_counter += 1
                        if keepalive_counter % 100 == 0:  # Every ~20-30 seconds
                            keepalive_message = {
                                "type": "keepalive",
                                "message_type": "keepalive", 
                                "task_id": task_id,
                                "message": "Connection active (Redis mode)",
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            yield f"data: {json.dumps(keepalive_message)}\n\n"
            else:
                logger.info(f"📊 Using database polling")
                # Database polling loop
                poll_count = 0
                max_polls = 1500  # ~5 minutes at 0.2s intervals
                
                while poll_count < max_polls:
                    poll_count += 1
                    
                    try:
                        current_task = await task_manager.get_task(task_id)
                        if not current_task:
                            break
                        
                        status = current_task.get('status', '').lower()
                        step = current_task.get('current_step')
                        progress = current_task.get('progress', 0)
                        hero_url = current_task.get('hero_image_url')
                        
                        # Check for changes
                        has_changes = (
                            status != last_sent_status or
                            step != last_sent_step or
                            progress != last_sent_progress or
                            hero_url != last_sent_hero
                        )
                        
                        if has_changes:
                            update = send_update(current_task)
                            if update:
                                yield update
                        
                        # Exit if complete
                        if status in ['completed', 'failed']:
                            break
                        
                        # Periodic keepalive
                        if poll_count % 50 == 0:  # Every ~10 seconds
                            keepalive_message = {
                                "type": "keepalive",
                                "message_type": "keepalive",
                                "task_id": task_id,
                                "message": "Connection active (polling mode)",
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            yield f"data: {json.dumps(keepalive_message)}\n\n"
                        
                    except Exception as e:
                        logger.error(f"❌ Database polling error: {e}")
                        
                    # Wait before next poll
                    await asyncio.sleep(0.2)
                
                # Timeout reached
                timeout_message = {
                    "type": "timeout",
                    "task_id": task_id,
                    "message": "Stream timeout reached - refresh page to reconnect",
                    "timestamp": datetime.utcnow().isoformat()
                }
                yield f"data: {json.dumps(timeout_message)}\n\n"
                
        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for task {task_id}")
        except Exception as e:
            logger.error(f"Error in SSE stream for task {task_id}: {e}")
            error_message = {
                "type": "error",
                "task_id": task_id,
                "message": f"Stream error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(error_message)}\n\n"
        finally:
            # Clean up Redis subscription properly
            if redis_pubsub:
                try:
                    logger.info(f"🔌 Closing Redis pubsub for task {task_id}")
                    await asyncio.wait_for(redis_pubsub.unsubscribe(f"task_updates:{task_id}"), timeout=2.0)
                    await asyncio.wait_for(redis_pubsub.close(), timeout=2.0)
                    logger.info(f"✅ Redis pubsub closed for task {task_id}")
                except asyncio.TimeoutError:
                    logger.error(f"❌ Timeout closing Redis pubsub for task {task_id}")
                except Exception as cleanup_error:
                    logger.error(f"❌ Error closing Redis pubsub for task {task_id}: {cleanup_error}")
                finally:
                    redis_pubsub = None

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "X-Accel-Buffering": "no",  # Disable Nginx buffering
        "X-Content-Type-Options": "nosniff",
        "Transfer-Encoding": "chunked"
    })

@app.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    user: User = Depends(get_current_user)
):
    """Delete a task/blog (useful for cleaning up stuck or failed tasks)."""
    try:
        success = await task_manager.delete_task(task_id, user.id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Task not found or access denied")
        
        return {"message": "Task deleted successfully", "task_id": task_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete task")

@app.post("/tasks/{task_id}/acknowledge-completion")
async def acknowledge_completion(
    task_id: str,
    user: User = Depends(get_current_user)
):
    """
    Acknowledge that the frontend has received the blog completion.
    Part of the Enhanced Completion Protocol to prevent race conditions.
    """
    try:
        # Verify the task belongs to the user
        task_result = await task_manager.get_task(task_id)
        if not task_result or task_result.get('user_id') != user.id:
            raise HTTPException(status_code=404, detail="Task not found or access denied")
        
        # Send acknowledgment via Redis
        await redis_manager.send_completion_acknowledgment(task_id)
        
        logger.info(f"✅ Frontend acknowledged completion for task {task_id} by user {user.id}")
        
        return {
            "message": "Completion acknowledgment received",
            "task_id": task_id,
            "acknowledged": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to acknowledge completion for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to acknowledge completion")

@app.post("/generate-title", response_model=TitleGenerationResponse)
async def generate_title(
    request: TitleGenerationRequest,
    user: User = Depends(get_current_user)
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
            raise HTTPException(
                status_code=500,
                detail="OpenAI API key not configured"
            )
        
        # Set up context for this title generation request
        request_id = str(uuid.uuid4())
        set_request_context(
            request_id=request_id,
            task_id=f"title_{request_id}",
            user_id=user.id,
            user_email=user.email,
            user_role=user.role,
            blog_id=f"title_{request_id}",  # Use title task ID as blog_id
            topic=f"Title: {request.instructions[:50]}..."
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
        raise HTTPException(
            status_code=500,
            detail="Failed to generate title using AI"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error during title generation: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal error during title generation"
        )

# =============================================================================
# Background Tasks
# =============================================================================

async def async_blog_generation(task_id: str, topic: Optional[str], user_id: str, instructions: Optional[str] = None):
    """
    Async blog generation with context preservation.
    
    This function runs as a FastAPI background task and maintains
    the request context throughout the blog generation process.
    """
    try:
        logger.info(f"🔄 Starting async blog generation for task {task_id}")
        
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
            topic=topic or '<auto>'
        )
        
        # Update task status to in_progress
        await task_manager.update_task(task_id, 
            status='in_progress', 
            current_step='Initializing blog generation workflow...'
        )
        
        # Send immediate initialization message for SSE streams
        if task_manager._redis_manager:
            init_message = create_initializing_message(
                task_id=task_id,
                phase="Blog Generation",
                message="Initializing AI blog generation workflow...",
                progress=0.0
            )
            await task_manager._redis_manager.publish_immediate_message(task_id, init_message.to_dict())
        
        # Create audit tracker for this session - USING ENHANCED VERSION
        # Note: In production, user_id should come from JWT token validation
        # For now, we'll use a fallback to ensure audit logging works
        valid_user_id = user_id if user_id and len(user_id) > 10 else "cmdaiv5530000z9nxqmyg445v"
        
        audit_tracker = EnhancedDatabaseAuditTracker(
            session_type="blog_generation",
            user_id=valid_user_id,
            blog_id=task_id
        )
        
        # ===== CRITICAL FIX: Set audit context AFTER restoring request context =====
        set_audit_context(audit_tracker, f"session_{int(datetime.utcnow().timestamp())}")
        
        # Start the audit session
        await audit_tracker.start_session()
        
        logger.info(f"✅ Context restored and audit tracker initialized for task {task_id}")
        
        # Define enhanced status update callback for Phase 1 Foundation
        def update_task_status(status_data: Dict[str, Any]):
            """Enhanced task status update with immediate SSE broadcasting."""
            message = status_data.get('message', 'Processing...')
            step = status_data.get('step', 0)
            progress = status_data.get('progress', 0.0)
            message_type = status_data.get('message_type', 'status')
            
            # Handle percentage conversion for legacy format
            if progress <= 1.0:
                progress = progress * 100
            
            # Detect if running in CrewAI Flow thread context to avoid asyncio conflicts
            import threading
            current_thread = threading.current_thread()
            is_flow_thread = (
                current_thread.name.startswith('Thread-') or 
                'CrewAI' in current_thread.name or
                current_thread != threading.main_thread()
            )
            
            if is_flow_thread:
                # REDIS-ONLY updates from Flow threads to avoid asyncio conflicts
                try:
                    # Use thread-safe Redis-only update
                    task_manager.update_task_redis_only(task_id, status_data)
                    
                    # Log different message types appropriately
                    if message_type == 'agentthinking':
                        logger.info(f"🧠 {task_id}: Agent thinking - {status_data.get('agent_name', 'Unknown')}")
                    elif message_type == 'toolcall':
                        logger.info(f"🔧 {task_id}: Tool usage - {status_data.get('tool_name', 'Unknown')}")
                    elif message_type == 'contentstream':
                        logger.info(f"📄 {task_id}: Content streaming - {status_data.get('content_type', 'Unknown')}")
                    elif message_type == 'researchfinding':
                        logger.info(f"🔍 {task_id}: Research finding - {len(status_data.get('finding', ''))} chars")
                    else:
                        logger.info(f"📊 {task_id}: {message} ({progress:.1f}%) - Redis update")
                        
                except Exception as e:
                    logger.error(f"❌ Failed to send Redis status update for task {task_id}: {e}")
            else:
                # FULL DATABASE + REDIS updates from main thread
                async def update_with_enhanced_broadcasting():
                    try:
                        # Update database task status
                        await task_manager.update_task(task_id, 
                            current_step=message, 
                            progress=progress
                        )
                        
                        # Broadcast immediate message for enhanced real-time feedback
                        if task_manager._redis_manager:
                            await task_manager._redis_manager.publish_immediate_message(task_id, status_data)
                        
                        logger.info(f"📊 {task_id}: {message} ({progress:.1f}%) - Database + Redis updated")
                            
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
            instructions=instructions
        )

        async def hero_image_task():
            """Generate hero image in parallel once topic becomes available."""
            try:
                # Wait for topic (poll) or give up after 30 * 0.3s = 9s
                for _ in range(30):
                    if getattr(flow, 'topic', None):
                        break
                    await asyncio.sleep(0.3)
                final_topic = getattr(flow, 'topic', None) or topic or 'AI Blog'
                update_phase('image_generation')
                
                # Check if AI image generation is enabled
                hero_url = None
                if config.features.enable_hero_image_generation:
                    from bloggen.tools.openai_image_tool import OpenAIImageTool
                    from bloggen.tools.unsplash_tool import UnsplashImageTool
                    import re
                    
                    prompt = f"Photorealistic, high-quality professional image directly representing '{final_topic}'. Modern, stylish composition with excellent lighting, sharp focus, and cinematic quality. Suitable for premium blog header, visually striking and directly relevant to the topic."
                    hero_tool = OpenAIImageTool(audit_tracker=audit_tracker)
                    hero_result = hero_tool.run(prompt)
                    
                    # Extract URL from markdown format: ![alt](url "caption")
                    if isinstance(hero_result, str):
                        url_match = re.search(r'!\[.*?\]\((.*?)\s*(?:\".*?\")?\)', hero_result)
                        hero_url = url_match.group(1) if url_match else None
                    elif isinstance(hero_result, dict):
                        hero_url = hero_result.get('url')
                    
                    if not hero_url or 'placeholder' in (hero_url or '') or 'placehold.co' in (hero_url or ''):
                        try:
                            unsplash_tool = UnsplashImageTool()
                            unsplash_res = unsplash_tool.run(final_topic)
                            if isinstance(unsplash_res, dict):
                                hero_url = unsplash_res.get('url') or hero_url
                        except Exception:
                            logger.debug('Unsplash fallback failed', exc_info=True)
                else:
                    logger.info("AI image generation disabled - skipping hero image generation")
                        
                # Update hero image in database if found
                if hero_url:
                    current_task = await task_manager.get_task(task_id)
                    if current_task and current_task.get('status', '').lower() not in ['failed', 'completed']:
                        await task_manager.update_task(task_id, 
                            hero_image_url=hero_url,
                            current_step='Hero image ready'
                        )
                update_phase('finalization')
            except Exception as e:
                logger.debug(f"Parallel hero image generation failed for task {task_id}: {e}", exc_info=True)

        # Start hero image generation concurrently
        hero_task = asyncio.create_task(hero_image_task())

        # Execute the flow with proper inputs (topic may be None for auto-generation)
        result = await run_blog_flow_async(flow, topic)
        
        # CRITICAL DEBUG: Log the raw result from the flow
        logger.info(f"🔍 DEBUG: Blog flow result type: {type(result)}")
        logger.info(f"🔍 DEBUG: Blog flow result keys (if dict): {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        logger.info(f"🔍 DEBUG: Blog flow result attributes: {[attr for attr in dir(result) if not attr.startswith('_')] if hasattr(result, '__dict__') else 'No attributes'}")
        logger.info(f"🔍 DEBUG: Blog flow result preview: {str(result)[:200]}...")

        # Get current task state to check if it should be updated
        current_task = await task_manager.get_task(task_id)
        if current_task:
            blog_content = "Blog generation completed, but content extraction failed."
            try:
                if isinstance(result, dict) and 'final_blog_post' in result:
                    final_blog = result['final_blog_post']
                    logger.info(f"🔍 DEBUG: Found final_blog_post in dict, type: {type(final_blog)}")
                    if hasattr(final_blog, 'raw'):
                        blog_content = final_blog.raw
                        logger.info(f"🔍 DEBUG: Using final_blog.raw, length: {len(blog_content)}")
                    elif isinstance(final_blog, str):
                        blog_content = final_blog
                        logger.info(f"🔍 DEBUG: Using final_blog as string, length: {len(blog_content)}")
                    else:
                        blog_content = str(final_blog)
                        logger.info(f"🔍 DEBUG: Converting final_blog to string, length: {len(blog_content)}")
                elif hasattr(result, 'raw') and result.raw:  # type: ignore
                    blog_content = result.raw  # type: ignore
                    logger.info(f"🔍 DEBUG: Using result.raw, length: {len(blog_content)}")
                else:
                    blog_content = str(result)
                    logger.info(f"🔍 DEBUG: Using fallback string conversion, length: {len(blog_content)}")
                    logger.warning(f"⚠️ Using fallback string conversion for task {task_id}")
                    
                logger.info(f"🔍 DEBUG: Final blog_content length before completion: {len(blog_content)}")
                logger.info(f"🔍 DEBUG: Final blog_content preview: {blog_content[:200]}...")
                
            except Exception as e:
                logger.error(f"❌ Error extracting blog content for task {task_id}: {e}")
                blog_content = f"Error extracting blog content: {str(e)}"

            # Update topic if auto-generated
            if (not topic or not topic.strip()) and getattr(flow, 'topic', None):
                await task_manager.update_task(task_id, topic=flow.topic)

            # Await hero task (still parallelized with flow) to keep guarantee hero appears before completion
            try:
                await asyncio.wait_for(hero_task, timeout=15)
            except asyncio.TimeoutError:
                logger.warning(f"Hero image generation timeout for task {task_id}; completing without it")
            except Exception:
                logger.debug("Hero image coroutine error", exc_info=True)

            # Mark completion after hero attempt - ignore database status since Flow threads use Redis-only updates
            current_task = await task_manager.get_task(task_id)
            if current_task:
                # Get hero image URL if it was set during generation
                hero_image_url = current_task.get('hero_image_url')
                
                # CRITICAL DEBUG: Check content before completion call
                logger.info(f"🔍 COMPLETION DEBUG - About to call complete_task:")
                logger.info(f"   task_id: {task_id}")
                logger.info(f"   blog_content length: {len(blog_content) if blog_content else 0}")
                logger.info(f"   blog_content type: {type(blog_content)}")
                logger.info(f"   blog_content is_empty: {not blog_content or not blog_content.strip()}")
                logger.info(f"   blog_content preview: {blog_content[:300] if blog_content else 'EMPTY'}...")
                logger.info(f"   hero_image_url: {hero_image_url}")
                
                # Always complete the task since the Flow finished successfully
                await task_manager.complete_task(task_id, blog_content, hero_image_url)
                logger.info(f"✅ Task {task_id} completed - Blog content length: {len(blog_content)} chars")

        # End the audit session AFTER hero image to include its cost
        await audit_tracker.end_session()
        
        logger.info(f"✅ Blog generation completed for task {task_id}")
        
    except Exception as e:
        # Enhanced error logging for SSE timeout investigation
        import traceback
        
        logger.error(f"❌ Blog generation failed for task {task_id}: {e}")
        logger.error(f"❌ Exception type: {type(e).__name__}")  
        logger.error(f"❌ Exception module: {type(e).__module__}")
        logger.error(f"❌ Exception args: {getattr(e, 'args', 'N/A')}")
        logger.error(f"❌ Full traceback:\n{traceback.format_exc()}")
        
        # Try to end audit session on error
        try:
            audit_tracker_var = current_audit_tracker.get(None)
            if audit_tracker_var and hasattr(audit_tracker_var, 'end_session'):
                await audit_tracker_var.end_session()  # type: ignore
        except Exception as audit_error:
            logger.error(f"Failed to end audit session: {audit_error}")
            pass  # Don't fail the error handling
        
        # Update task with enhanced error details for SSE visibility
        error_details = f"{type(e).__name__}: {str(e)}"
        await task_manager.fail_task(task_id, error_details)

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

            log_topic = flow.topic if flow.topic else '<auto>'
            logger.info(f"🚀 Starting flow with topic: {log_topic}, year: {flow.current_year}")

            return flow.kickoff({
                'topic': flow.topic or '',  # kickoff context; flow handles auto-generation internally
                'current_year': flow.current_year,
            })
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
    
    # Prepare uvicorn config
    uvicorn_config = {
        "host": "0.0.0.0",
        "port": protocol_config.backend_port,
        "reload": True,
        "access_log": False  # Keep logs clean
    }
    
    # Add SSL configuration if HTTPS mode
    if protocol_config.is_https:
        ssl_config = protocol_config.get_ssl_config()
        if ssl_config:
            cert_path, key_path = ssl_config
            if os.path.exists(cert_path) and os.path.exists(key_path):
                uvicorn_config["ssl_keyfile"] = key_path
                uvicorn_config["ssl_certfile"] = cert_path
                logger.info(f"🔒 HTTPS mode enabled with SSL certificates")
            else:
                logger.warning(f"⚠️ HTTPS mode requested but SSL certificates not found:")
                logger.warning(f"   Cert: {cert_path}")
                logger.warning(f"   Key: {key_path}")
                logger.warning(f"   Falling back to HTTP mode")
        else:
            logger.warning(f"⚠️ HTTPS mode requested but no SSL config available")
    
    logger.info(f"🚀 Starting backend server: {protocol_config.get_backend_url()}")
    uvicorn.run("main:app", **uvicorn_config)
