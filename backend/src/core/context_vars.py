"""
Context Variables for Request Isolation in FastAPI

This module provides context variables that ensure perfect isolation between
concurrent requests in our async FastAPI application. Each async task tree
gets its own isolated context, preventing data leakage between users.

Context variables automatically propagate through async function calls,
ensuring that LLM interceptor callbacks can correctly attribute API usage
to the right user and blog generation session.
"""

import contextvars
from typing import Optional
from datetime import datetime

# =============================================================================
# Core Context Variables
# =============================================================================

# Request identification
current_request_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('request_id', default=None)
current_task_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('task_id', default=None)

# User context
current_user_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('user_id', default=None)
current_user_email: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('user_email', default=None)
current_user_role: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('user_role', default=None)

# Blog generation context
current_blog_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('blog_id', default=None)
current_topic: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('topic', default=None)
current_phase: contextvars.ContextVar[str] = contextvars.ContextVar('phase', default='unknown')

# Audit tracking context
current_audit_tracker: contextvars.ContextVar[Optional[object]] = contextvars.ContextVar('audit_tracker', default=None)
current_session_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('session_id', default=None)

# Timestamps
request_start_time: contextvars.ContextVar[Optional[datetime]] = contextvars.ContextVar('request_start_time', default=None)

# =============================================================================
# Context Management Functions
# =============================================================================

def set_request_context(
    request_id: str,
    task_id: str,
    user_id: str,
    user_email: str,
    user_role: str,
    blog_id: str,
    topic: str
):
    """
    Set the complete request context for a blog generation session.
    
    This should be called at the beginning of each blog generation request
    to establish the context that will be inherited by all async operations.
    
    Args:
        request_id: Unique identifier for this HTTP request
        task_id: Unique identifier for this blog generation task
        user_id: ID of the authenticated user
        user_email: Email of the authenticated user
        user_role: Role of the authenticated user (FREE, PREMIUM, ADMIN)
        blog_id: ID of the blog being generated
        topic: Topic of the blog being generated
    """
    # Set all context variables
    current_request_id.set(request_id)
    current_task_id.set(task_id)
    current_user_id.set(user_id)
    current_user_email.set(user_email)
    current_user_role.set(user_role)
    current_blog_id.set(blog_id)
    current_topic.set(topic)
    current_phase.set('initialization')
    request_start_time.set(datetime.utcnow())

def set_audit_context(audit_tracker, session_id: str):
    """
    Set audit tracking context.
    
    Args:
        audit_tracker: EnhancedDatabaseAuditTracker instance for this session
        session_id: Database session ID for audit tracking
    """
    current_audit_tracker.set(audit_tracker)
    current_session_id.set(session_id)

def update_phase(phase: str):
    """
    Update the current blog generation phase.
    
    Args:
        phase: New phase name (e.g., 'research_phase', 'content_generation_phase')
    """
    current_phase.set(phase)

def get_request_context() -> dict:
    """
    Get the current request context as a dictionary.
    
    Returns:
        dict: Current context values
    """
    return {
        'request_id': current_request_id.get(None),
        'task_id': current_task_id.get(None),
        'user_id': current_user_id.get(None),
        'user_email': current_user_email.get(None),
        'user_role': current_user_role.get(None),
        'blog_id': current_blog_id.get(None),
        'topic': current_topic.get(None),
        'phase': current_phase.get('unknown'),
        'session_id': current_session_id.get(None),
        'start_time': request_start_time.get(None)
    }

def get_audit_tracker():
    """
    Get the current audit tracker from context.
    
    Returns:
        EnhancedDatabaseAuditTracker or None: Current audit tracker
    """
    return current_audit_tracker.get(None)

def get_current_phase() -> str:
    """
    Get the current blog generation phase.
    
    Returns:
        str: Current phase name
    """
    return current_phase.get('unknown')

def get_user_context() -> dict:
    """
    Get current user context.
    
    Returns:
        dict: User information from context
    """
    return {
        'user_id': current_user_id.get(None),
        'user_email': current_user_email.get(None),
        'user_role': current_user_role.get(None)
    }

# =============================================================================
# Context Validation
# =============================================================================

def validate_context() -> bool:
    """
    Validate that required context is available.
    
    Returns:
        bool: True if context is valid, False otherwise
    """
    required_vars = [
        current_request_id.get(None),
        current_task_id.get(None),
        current_user_id.get(None),
        current_blog_id.get(None)
    ]
    
    return all(var is not None for var in required_vars)

def get_context_summary() -> str:
    """
    Get a human-readable summary of current context.
    
    Returns:
        str: Context summary for logging
    """
    context = get_request_context()
    request_id = context['request_id'] or 'unknown'
    user_id = context['user_id'] or 'unknown'
    phase = context['phase'] or 'unknown'
    topic = context['topic'] or 'unknown'
    
    # Handle potential None values safely
    request_prefix = request_id[:8] + "..." if len(request_id) > 8 else request_id
    topic_prefix = topic[:30] + "..." if len(topic) > 30 else topic
    
    return (
        f"[{request_prefix}] "
        f"User: {user_id} "
        f"Phase: {phase} "
        f"Topic: {topic_prefix}"
    )
