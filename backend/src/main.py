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
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request, WebSocket, WebSocketDisconnect
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

# Core imports
from core.config import config, get_cors_origins
from core.llm_interceptor import setup_llm_interceptor
from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker  # unified import
from core.logging_utils import setup_api_logger
from core.websocket_manager import websocket_manager, WebSocketMessage
from core.redis_manager import redis_manager

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
    task_manager.set_websocket_manager(websocket_manager)
    task_manager.set_redis_manager(redis_manager)
    websocket_manager.set_redis_manager(redis_manager)
    logger.info("✅ WebSocket and Redis managers connected to TaskManager")

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
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

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
    """SSE stream for a specific task with early hero image updates."""
    # Authenticate via query token
    user = await get_current_user_from_query_token(token)
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task['user_id'] != user.id and user.role != 'ADMIN':
        raise HTTPException(status_code=403, detail="Access denied")

    async def event_generator():
        last_sent_status = None
        last_sent_step = None
        last_sent_progress = None
        last_sent_hero = None
        try:
            while True:
                # Get current task state from database
                current_task = await task_manager.get_task(task_id)
                if not current_task:
                    break
                    
                status = current_task.get('status', '').lower()
                step = current_task.get('current_step')
                progress = current_task.get('progress', 0)
                hero_url = current_task.get('hero_image_url')
                has_changes = (
                    status != last_sent_status or
                    step != last_sent_step or
                    progress != last_sent_progress or
                    hero_url != last_sent_hero
                )
                if has_changes:
                    payload: Dict[str, Any] = {
                        'status': status,
                        'step': step,
                        'progress': progress,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    if hero_url:
                        payload['hero_image_url'] = hero_url
                    if status == 'completed' and current_task.get('content'):
                        payload['result'] = current_task['content']
                    if status == 'failed' and current_task.get('error'):
                        payload['error'] = current_task['error']
                    yield f"data: {json.dumps(payload)}\n\n"
                    last_sent_status = status
                    last_sent_step = step
                    last_sent_progress = progress
                    last_sent_hero = hero_url
                if status in ['completed', 'failed']:
                    break
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for task {task_id}")
        except Exception as e:
            logger.error(f"Error in SSE stream for task {task_id}: {e}")

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
    })

@app.websocket("/ws/{task_id}")
async def websocket_task_endpoint(websocket: WebSocket, task_id: str, token: str):
    """
    WebSocket endpoint for real-time task updates.
    
    This replaces the SSE endpoint with bidirectional WebSocket communication
    for more reliable real-time updates and better connection management.
    
    Query Parameters:
        token: JWT authentication token (same as SSE)
    
    Message Types:
        - connected: Initial connection confirmation
        - task_update: Status updates for the subscribed task
        - ping/pong: Heartbeat messages
        - error: Error notifications
    """
    connection_id = f"ws_{task_id}_{uuid.uuid4().hex[:8]}"
    
    try:
        # Authenticate user via query token (same as SSE)
        user = await get_current_user_from_query_token(token)
        
        # Verify task access
        task = await task_manager.get_task(task_id)
        if not task:
            await websocket.close(code=1003, reason="Task not found")
            return
        if task['user_id'] != user.id and user.role != 'ADMIN':
            await websocket.close(code=1003, reason="Access denied")
            return
        
        # Establish WebSocket connection
        success = await websocket_manager.connect(websocket, connection_id, user.id)
        if not success:
            await websocket.close(code=1011, reason="Connection failed")
            return
        
        # Subscribe to task updates
        await websocket_manager.subscribe_to_task(connection_id, task_id)
        
        # Send initial task state
        current_task = await task_manager.get_task(task_id)
        if current_task:
            await websocket_manager.send_to_connection(connection_id, WebSocketMessage(
                type="task_update",
                task_id=task_id,
                data={
                    'status': current_task.get('status', '').lower(),
                    'step': current_task.get('current_step'),
                    'progress': current_task.get('progress', 0),
                    'hero_image_url': current_task.get('hero_image_url'),
                    'content': current_task.get('content') if current_task.get('status') == 'completed' else None,
                    'error': current_task.get('error') if current_task.get('status') == 'failed' else None
                }
            ))
        
        # Handle incoming messages (ping, subscriptions, etc.)
        try:
            while True:
                # Wait for messages from client
                message_text = await websocket.receive_text()
                try:
                    message_data = json.loads(message_text)
                    message_type = message_data.get('type', '')
                    
                    if message_type == 'ping':
                        await websocket_manager.handle_ping(connection_id)
                    elif message_type == 'subscribe_task':
                        # Allow subscribing to additional tasks
                        new_task_id = message_data.get('task_id')
                        if new_task_id:
                            # Verify access to new task
                            new_task = await task_manager.get_task(new_task_id)
                            if new_task and (new_task['user_id'] == user.id or user.role == 'ADMIN'):
                                await websocket_manager.subscribe_to_task(connection_id, new_task_id)
                                await websocket_manager.send_to_connection(connection_id, WebSocketMessage(
                                    type="subscribed",
                                    task_id=new_task_id,
                                    data={"message": f"Subscribed to task {new_task_id}"}
                                ))
                    elif message_type == 'unsubscribe_task':
                        # Allow unsubscribing from tasks
                        old_task_id = message_data.get('task_id')
                        if old_task_id:
                            await websocket_manager.unsubscribe_from_task(connection_id, old_task_id)
                            await websocket_manager.send_to_connection(connection_id, WebSocketMessage(
                                type="unsubscribed",
                                task_id=old_task_id,
                                data={"message": f"Unsubscribed from task {old_task_id}"}
                            ))
                    
                except json.JSONDecodeError:
                    await websocket_manager.send_to_connection(connection_id, WebSocketMessage(
                        type="error",
                        data={"message": "Invalid JSON in message"}
                    ))
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket client disconnected: {connection_id}")
    
    except Exception as e:
        logger.error(f"Error in WebSocket endpoint for task {task_id}: {e}")
        try:
            await websocket.close(code=1011, reason=f"Server error: {str(e)}")
        except:
            pass
    
    finally:
        # Clean up connection
        await websocket_manager.disconnect(connection_id)

@app.websocket("/ws")
async def websocket_general_endpoint(websocket: WebSocket, token: str):
    """
    General WebSocket endpoint for user-level updates.
    
    This endpoint allows users to connect without a specific task
    and receive general notifications, new task alerts, etc.
    """
    connection_id = f"ws_general_{uuid.uuid4().hex[:8]}"
    
    try:
        # Authenticate user
        user = await get_current_user_from_query_token(token)
        
        # Establish WebSocket connection
        success = await websocket_manager.connect(websocket, connection_id, user.id)
        if not success:
            await websocket.close(code=1011, reason="Connection failed")
            return
        
        # Handle messages
        try:
            while True:
                message_text = await websocket.receive_text()
                try:
                    message_data = json.loads(message_text)
                    message_type = message_data.get('type', '')
                    
                    if message_type == 'ping':
                        await websocket_manager.handle_ping(connection_id)
                    elif message_type == 'get_stats':
                        stats = websocket_manager.get_stats()
                        await websocket_manager.send_to_connection(connection_id, WebSocketMessage(
                            type="stats",
                            data=stats
                        ))
                    
                except json.JSONDecodeError:
                    await websocket_manager.send_to_connection(connection_id, WebSocketMessage(
                        type="error",
                        data={"message": "Invalid JSON in message"}
                    ))
        
        except WebSocketDisconnect:
            logger.info(f"General WebSocket client disconnected: {connection_id}")
    
    except Exception as e:
        logger.error(f"Error in general WebSocket endpoint: {e}")
        try:
            await websocket.close(code=1011, reason=f"Server error: {str(e)}")
        except:
            pass
    
    finally:
        await websocket_manager.disconnect(connection_id)

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
        
        # Define status update callback
        def update_task_status(status_data: Dict[str, Any]):
            """Update task status for SSE streaming."""
            message = status_data.get('message', 'Processing...')
            step = status_data.get('step', 0)
            progress = status_data.get('progress', 0.0) * 100  # Convert to percentage
            
            # Update task in database instead of memory
            asyncio.create_task(task_manager.update_task(task_id, 
                current_step=message, 
                progress=progress
            ))
            logger.info(f"📊 {task_id}: Step {step} - {message} ({progress:.1f}%)")
        
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
                from bloggen.tools.openai_image_tool import OpenAIImageTool
                from bloggen.tools.unsplash_tool import UnsplashImageTool
                prompt = f"High quality, modern illustrative hero image representing: {final_topic}"
                hero_tool = OpenAIImageTool(audit_tracker=audit_tracker)
                hero_result = hero_tool.run(prompt)
                hero_url = hero_result.get('url') if isinstance(hero_result, dict) else None
                if not hero_url or 'placeholder' in (hero_url or ''):
                    try:
                        unsplash_tool = UnsplashImageTool()
                        unsplash_res = unsplash_tool.run(final_topic)
                        if isinstance(unsplash_res, dict):
                            hero_url = unsplash_res.get('url') or hero_url
                    except Exception:
                        logger.debug('Unsplash fallback failed', exc_info=True)
                        
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

        # Get current task state to check if it should be updated
        current_task = await task_manager.get_task(task_id)
        if current_task:
            blog_content = "Blog generation completed, but content extraction failed."
            try:
                if isinstance(result, dict) and 'final_blog_post' in result:
                    final_blog = result['final_blog_post']
                    if hasattr(final_blog, 'raw'):
                        blog_content = final_blog.raw
                    elif isinstance(final_blog, str):
                        blog_content = final_blog
                    else:
                        blog_content = str(final_blog)
                elif hasattr(result, 'raw') and result.raw:  # type: ignore
                    blog_content = result.raw  # type: ignore
                else:
                    blog_content = str(result)
                    logger.warning(f"⚠️ Using fallback string conversion for task {task_id}")
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

            # Mark completion after hero attempt
            current_task = await task_manager.get_task(task_id)
            if current_task and current_task.get('status', '').lower() != 'failed':
                # Get hero image URL if it was set during generation
                hero_image_url = current_task.get('hero_image_url')
                await task_manager.complete_task(task_id, blog_content, hero_image_url)
                logger.info(f"✅ Task {task_id} completed - Blog content length: {len(blog_content)} chars")

        # End the audit session AFTER hero image to include its cost
        await audit_tracker.end_session()
        
        logger.info(f"✅ Blog generation completed for task {task_id}")
        
    except Exception as e:
        logger.error(f"❌ Blog generation failed for task {task_id}: {e}")
        
        # Try to end audit session on error
        try:
            audit_tracker_var = current_audit_tracker.get(None)
            if audit_tracker_var and hasattr(audit_tracker_var, 'end_session'):
                await audit_tracker_var.end_session()  # type: ignore
        except Exception as audit_error:
            logger.error(f"Failed to end audit session: {audit_error}")
            pass  # Don't fail the error handling
        
        # Update task with error
        await task_manager.fail_task(task_id, str(e))

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
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,  # Standard port for backend API
        reload=True,
        ssl_keyfile="/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/src/localhost-key.pem",
        ssl_certfile="/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/src/localhost.pem",
        access_log=False  # Disable repetitive access logs to keep focus on essential logs
    )
