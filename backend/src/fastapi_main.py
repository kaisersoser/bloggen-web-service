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
from core.audit_tracker import DatabaseAuditTracker
from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker
from core.llm_interceptor import setup_llm_interceptor
from core.logging_utils import setup_api_logger

# Blog generation
from bloggen.flows import BlogGenerationFlow

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
    """Request model for blog generation."""
    topic: str = Field(..., min_length=3, max_length=200, description="Blog topic")
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
    set_request_context(
        request_id=request_id,
        task_id=task_id,
        user_id=user.id,
        user_email=user.email,
        user_role=user.role,
        blog_id=task_id,  # Use task_id as blog_id
        topic=request.topic
    )
    
    # Create task record
    active_tasks[task_id] = {
        'id': task_id,
        'topic': request.topic,
        'status': 'queued',
        'created_at': datetime.utcnow().isoformat(),
        'current_step': 'Queued for processing',
        'result': None,
        'error': None,
        'user_id': user.id,
        'user_email': user.email,
        'user_role': user.role,
        'request_id': request_id
    }
    
    # Start background blog generation
    background_tasks.add_task(
        async_blog_generation,
        task_id=task_id,
        topic=request.topic,
        user_id=user.id
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
        
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=openai_api_key)
        
        # Generate title using OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that creates short, engaging blog titles. Extract the core topic from user instructions and create a concise title (5-10 words max). Remove any instruction words like 'Generate', 'Write', 'Create', 'blog about', etc. Focus only on the main subject. Return only the title, nothing else."
                },
                {
                    "role": "user",
                    "content": f"Extract the core topic and create a short blog title from: \"{request.instructions}\""
                }
            ],
            max_tokens=25,
            temperature=0.5,
        )
        
        # Extract generated title
        generated_title = response.choices[0].message.content
        if not generated_title:
            raise HTTPException(
                status_code=500,
                detail="No title generated"
            )
        
        # Clean and format the title
        clean_title = generated_title.strip().replace('"', '').replace("'", "")
        formatted_title = clean_title.title()
        
        # Fix title case for common words
        lowercase_words = ['a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'if', 'in', 'nor', 'of', 'on', 'or', 'so', 'the', 'to', 'up', 'yet']
        words = formatted_title.split()
        
        for i, word in enumerate(words):
            if i > 0 and word.lower() in lowercase_words:
                words[i] = word.lower()
            elif i == 0:  # Always capitalize first word
                words[i] = word.capitalize()
        
        final_title = ' '.join(words)
        
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

async def async_blog_generation(task_id: str, topic: str, user_id: str):
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
            topic=topic
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
        def update_task_status(step_name: str, message: str, progress: float = 0.5):
            """Update task status for SSE streaming."""
            if task_id in active_tasks:
                active_tasks[task_id]['current_step'] = f"{step_name}: {message}"
                logger.info(f"📊 {task_id}: {step_name} - {message}")
        
        # Create and run blog generation flow
        flow = BlogGenerationFlow(
            status_callback=update_task_status,
            user_id=user_id,
            blog_id=task_id
        )
        
        # Execute the flow
        result = await run_blog_flow_async(flow, topic)
        
        # End the audit session
        await audit_tracker.end_session()
        
        # Update task with completion
        if task_id in active_tasks:
            active_tasks[task_id]['status'] = 'completed'
            active_tasks[task_id]['result'] = str(result)
            active_tasks[task_id]['current_step'] = 'Blog generation completed successfully!'
            active_tasks[task_id]['progress'] = 100
            logger.info(f"✅ Task {task_id} marked as completed with result length: {len(str(result))}")
        
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

async def run_blog_flow_async(flow: BlogGenerationFlow, topic: str):
    """
    Run the blog generation flow in an async context.
    
    For now, we'll run the sync flow in a thread pool.
    Later, we'll convert the flow to be fully async.
    """
    # For now, run the sync flow in a thread pool
    # TODO: Convert BlogGenerationFlow to be fully async
    loop = asyncio.get_event_loop()
    
    def run_sync_flow():
        return flow.kickoff({
            'topic': topic,
            'current_year': datetime.now().year
        })
    
    # Run in thread pool to avoid blocking the event loop
    result = await loop.run_in_executor(None, run_sync_flow)
    return result

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
