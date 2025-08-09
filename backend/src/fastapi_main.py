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

# Core imports
from core.config import config, get_cors_origins
from core import DatabaseAuditTracker, EnhancedDatabaseAuditTracker  # Use refactored version
from core.llm_interceptor import setup_llm_interceptor
from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker  # for serper cost patch
from core.logging_utils import setup_api_logger

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

    logger.info("✅ FastAPI application startup complete")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("🛑 Shutting down FastAPI Blog Generation Service")

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
active_tasks: Dict[str, Dict[str, Any]] = {}

# Logger
logger = setup_api_logger("fastapi_main")

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
    
    # Create task record
    active_tasks[task_id] = {
        'id': task_id,
        'topic': normalized_topic or '<auto-generating>',
        'status': 'queued',
        'created_at': datetime.utcnow().isoformat(),
        'current_step': 'Queued for processing',
        'result': None,
        'error': None,
        'user_id': user.id,
        'user_email': user.email,
        'user_role': user.role,
        'request_id': request_id,
        'instructions': (request.instructions or '').strip() or None
    }
    
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

@app.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    user: User = Depends(get_current_user)
) -> TaskStatus:
    """Get the status of a specific task."""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = active_tasks[task_id]
    
    # Check if user owns this task (or is admin)
    if task['user_id'] != user.id and user.role != 'ADMIN':
        raise HTTPException(status_code=403, detail="Access denied")
    
    return TaskStatus(**task)

@app.get("/stream/{task_id}")
async def stream_task_updates(
    task_id: str,
    token: str,
    request: Request
):
    """
    Server-Sent Events stream for real-time task updates.
    
    Uses query parameter authentication since EventSource doesn't support
    custom headers for JWT tokens.
    """
    try:
        # Authenticate user from query token
        user = await get_current_user_from_query_token(token)
        
        # Check if task exists
        if task_id not in active_tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task = active_tasks[task_id]
        
        # Check if user owns this task (or is admin)
        if task['user_id'] != user.id and user.role != 'ADMIN':
            raise HTTPException(status_code=403, detail="Access denied")
        
        logger.info(f"🔗 SSE stream connected for task {task_id} by user {user.id}")
        
    except Exception as e:
        logger.error(f"❌ SSE authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")
    
    async def event_generator():
        """Generate SSE events for task updates."""
        try:
            last_sent_step = None
            last_sent_status = None
            last_sent_progress = None
            
            while True:
                if task_id not in active_tasks:
                    break
                    
                current_task = active_tasks[task_id]
                status = current_task['status']
                step = current_task['current_step']
                progress = current_task.get('progress', 0)
                
                # Only send update if something actually changed
                has_changes = (
                    status != last_sent_status or 
                    step != last_sent_step or 
                    progress != last_sent_progress
                )
                
                if has_changes:
                    logger.info(f"📡 SSE: Sending update for task {task_id} - Status: {status}, Step: {step}")
                    
                    # For completed status, include the result in the same message
                    if status == 'completed' and current_task.get('result'):
                        logger.info(f"📡 SSE: Sending completion with result for task {task_id}")
                        yield f"data: {{\"status\": \"completed\", \"step\": \"{step}\", \"progress\": {progress}, \"timestamp\": \"{datetime.utcnow().isoformat()}\", \"result\": {json.dumps(current_task['result'])}}}\n\n"
                    elif status == 'failed' and current_task.get('error'):
                        logger.info(f"📡 SSE: Sending failure with error for task {task_id}")
                        yield f"data: {{\"status\": \"failed\", \"step\": \"{step}\", \"progress\": {progress}, \"timestamp\": \"{datetime.utcnow().isoformat()}\", \"error\": {json.dumps(current_task['error'])}}}\n\n"
                    else:
                        # Regular status update
                        yield f"data: {{\"status\": \"{status}\", \"step\": \"{step}\", \"progress\": {progress}, \"timestamp\": \"{datetime.utcnow().isoformat()}\"}}\n\n"
                    
                    # Update last sent values
                    last_sent_status = status
                    last_sent_step = step
                    last_sent_progress = progress
                
                # Break the loop if task is complete
                if status in ['completed', 'failed']:
                    break
                
                # Wait before checking for changes again (reduced frequency)
                await asyncio.sleep(0.5)
                
        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for task {task_id}")
        except Exception as e:
            logger.error(f"Error in SSE stream for task {task_id}: {e}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

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
        
        # Update task status
        if task_id in active_tasks:
            active_tasks[task_id]['status'] = 'in_progress'
            active_tasks[task_id]['current_step'] = 'Initializing blog generation workflow...'
        
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
            if task_id in active_tasks:
                message = status_data.get('message', 'Processing...')
                step = status_data.get('step', 0)
                progress = status_data.get('progress', 0.0) * 100  # Convert to percentage
                
                active_tasks[task_id]['current_step'] = message
                active_tasks[task_id]['progress'] = progress
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

        # Execute the flow with proper inputs (topic may be None for auto-generation)
        result = await run_blog_flow_async(flow, topic)
        
        # End the audit session
        await audit_tracker.end_session()
        
        # Update task with completion
        if task_id in active_tasks:
            # Extract just the final blog content, not the entire flow result
            blog_content = "Blog generation completed, but content extraction failed."
            
            try:
                if isinstance(result, dict) and 'final_blog_post' in result:
                    # Get the final blog post content
                    final_blog = result['final_blog_post']
                    if hasattr(final_blog, 'raw'):
                        blog_content = final_blog.raw
                    elif isinstance(final_blog, str):
                        blog_content = final_blog
                    else:
                        blog_content = str(final_blog)
                elif hasattr(result, 'raw') and result.raw:  # type: ignore
                    # Direct CrewOutput object
                    blog_content = result.raw  # type: ignore
                else:
                    # Fallback: convert to string but log warning
                    blog_content = str(result)
                    logger.warning(f"⚠️ Using fallback string conversion for task {task_id}")
                    
            except Exception as e:
                logger.error(f"❌ Error extracting blog content for task {task_id}: {e}")
                blog_content = f"Error extracting blog content: {str(e)}"
            
            # Update topic if it was auto-generated
            if (not topic or not topic.strip()) and getattr(flow, 'topic', None):
                active_tasks[task_id]['topic'] = flow.topic

            active_tasks[task_id]['status'] = 'completed'
            active_tasks[task_id]['result'] = blog_content  # Send only the blog content
            active_tasks[task_id]['current_step'] = 'Blog generation completed successfully!'
            active_tasks[task_id]['progress'] = 100
            logger.info(f"✅ Task {task_id} completed - Blog content length: {len(blog_content)} chars")
        
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
        if task_id in active_tasks:
            active_tasks[task_id]['status'] = 'failed'
            active_tasks[task_id]['error'] = str(e)
            active_tasks[task_id]['current_step'] = f'Error: {str(e)}'

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
        "fastapi_main:app",
        host="0.0.0.0",
        port=5000,  # Standard port for backend API
        reload=True,
        ssl_keyfile="/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/src/localhost-key.pem",
        ssl_certfile="/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/src/localhost.pem"
    )
