"""
LiteLLM Callback Interceptor for Real-time Cost Tracking with Context Variables

This module provides a callback system to intercept actual OpenAI API calls
made by CrewAI and capture real usage data (tokens, costs, model) in real-time.

Now enhanced with context variables for perfect request isolation in FastAPI.
"""

import os
import time
import threading
from typing import Dict, Any, Optional
from datetime import datetime

# Context variables for request isolation
from core.context_vars import (
    current_audit_tracker,
    current_phase,
    current_request_id,
    current_user_id,
    get_context_summary
)

# Global thread-safe audit tracker registry for thread pool execution
_audit_registry_lock = threading.Lock()
_audit_registry: Dict[str, Dict[str, Any]] = {}
_parent_child_threads: Dict[int, int] = {}  # child_thread_id -> parent_thread_id

def _get_thread_task_id() -> str:
    """Get a unique identifier for the current thread/task context."""
    thread_id = threading.get_ident()
    # Try to get task context first, fall back to thread ID
    try:
        # Check if we're in an asyncio context
        import asyncio
        try:
            task = asyncio.current_task()
            if task:
                return f"task_{id(task)}"
        except RuntimeError:
            pass
    except ImportError:
        pass
    
    return f"thread_{thread_id}"

def _register_audit_tracker(audit_tracker, user_id: str = "unknown", request_id: str = "unknown", phase: str = "unknown") -> str:
    """Register audit tracker in global registry and return task ID."""
    task_id = _get_thread_task_id()
    thread_id = threading.get_ident()
    
    with _audit_registry_lock:
        _audit_registry[task_id] = {
            'audit_tracker': audit_tracker,
            'user_id': user_id,
            'request_id': request_id,
            'phase': phase,
            'timestamp': time.time(),
            'thread_id': thread_id
        }
        
        # Also register by raw thread ID for child thread lookup
        _audit_registry[f"thread_{thread_id}"] = _audit_registry[task_id]
        
    return task_id

def _get_audit_tracker_from_registry() -> Optional[Dict[str, Any]]:
    """Get audit tracker from global registry for current thread/task."""
    current_thread_id = threading.get_ident()
    task_id = _get_thread_task_id()
    
    with _audit_registry_lock:
        # First try exact task/thread match
        if task_id in _audit_registry:
            return _audit_registry[task_id]
            
        # Try direct thread ID match
        thread_key = f"thread_{current_thread_id}"
        if thread_key in _audit_registry:
            return _audit_registry[thread_key]
            
        # Look for parent thread registration if this is a child thread
        for registered_task_id, data in _audit_registry.items():
            # Skip non-thread entries
            if not registered_task_id.startswith('thread_'):
                continue
                
            # Check if any registered thread could be a parent
            # This is a heuristic - we look for recent registrations
            # since thread pool tasks are typically short-lived
            if (time.time() - data.get('timestamp', 0)) < 30:  # 30 second window
                return data
                
        return None

def _cleanup_audit_registry(task_id: Optional[str] = None):
    """Clean up audit registry entry."""
    if task_id is None:
        task_id = _get_thread_task_id()
    with _audit_registry_lock:
        _audit_registry.pop(task_id, None)

# LiteLLM imports for callback system
try:
    import litellm
    from litellm.integrations.custom_logger import CustomLogger
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    print("LiteLLM not available - API interception disabled")

from core.common import get_logger

class ContextAwareAuditCallbackHandler(CustomLogger):
    """
    Context-aware LiteLLM callback handler for multi-user request isolation.
    
    This class intercepts OpenAI API calls and uses context variables to
    correctly attribute usage to the right user session, eliminating race
    conditions between concurrent requests.
    """
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger("llm_interceptor")
        self.logger.info("Context-aware LLM interceptor initialized")
    
    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        """
        Called when an LLM API call succeeds.
        Uses context variables (async) or global registry (thread pool execution).
        """
        try:
            # Add debug logging to see if this method is being called
            self.logger.info(f"🎯 LLM API call intercepted in thread {threading.current_thread().ident}")
            
            # Try context variables first (for main async context)
            audit_tracker = current_audit_tracker.get(None)
            phase = current_phase.get("unknown")
            request_id = current_request_id.get("unknown")
            user_id = current_user_id.get("unknown")
            
            # If no context available, try global registry (for thread pool execution)
            if not audit_tracker:
                registry_data = _get_audit_tracker_from_registry()
                if registry_data:
                    audit_tracker = registry_data['audit_tracker']
                    phase = registry_data.get('phase', 'thread_execution')
                    request_id = registry_data.get('request_id', 'thread_request')
                    user_id = registry_data.get('user_id', 'thread_user')
                    self.logger.info("📝 Using global registry audit tracker")
            
            self.logger.info(f"Context: tracker={audit_tracker is not None}, phase={phase}, request={request_id}, user={user_id}")
            
            if not audit_tracker:
                self.logger.warning(f"No audit tracker in context or global registry for request {request_id}")
                self.logger.warning(f"Available context vars: audit={current_audit_tracker.get(None) is not None}, "
                                  f"phase={current_phase.get('none')}, user={current_user_id.get('none')}")
                registry_data = _get_audit_tracker_from_registry()
                self.logger.warning(f"Available in global registry: {registry_data is not None}")
                return
            
            # Extract model information
            model = kwargs.get('model', 'unknown')
            
            # Extract usage data from response
            if hasattr(response_obj, 'usage'):
                usage = response_obj.usage
                input_tokens = getattr(usage, 'prompt_tokens', 0)
                output_tokens = getattr(usage, 'completion_tokens', 0)
                total_tokens = getattr(usage, 'total_tokens', input_tokens + output_tokens)
                
                # Track the actual API call with context (type: ignore for now)
                if hasattr(audit_tracker, 'track_api_call'):
                    audit_tracker.track_api_call(  # type: ignore
                        model=model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        phase=phase,
                        agent_role="crew_agent"
                    )
                
                # Enhanced logging with context
                context_summary = get_context_summary()
                self.logger.info(
                    f"🎯 API call intercepted: {model} - {total_tokens} tokens "
                    f"(phase: {phase}) {context_summary}"
                )
                
            else:
                self.logger.warning(f"No usage data in API response for {request_id}")
                
        except LookupError:
            self.logger.warning("No context available for API call - this should not happen in FastAPI")
        except Exception as e:
            self.logger.error(f"Error in context-aware LLM callback: {e}")
    
    def log_failure_event(self, kwargs, response_obj, start_time, end_time):
        """Called when an LLM API call fails."""
        try:
            model = kwargs.get('model', 'unknown')
            phase = current_phase.get("unknown")
            request_id = current_request_id.get("unknown")
            
            self.logger.warning(
                f"LLM API call failed: {model} in phase {phase} for request {request_id}"
            )
        except LookupError:
            self.logger.warning("API call failed but no context available")


# Global callback handler instance
_callback_handler = None

def setup_llm_interceptor():
    """
    Set up the context-aware LiteLLM callback interceptor.
    This should be called once during FastAPI application startup.
    """
    global _callback_handler
    
    if not LITELLM_AVAILABLE:
        print("⚠️  LiteLLM not available - API interception disabled")
        return None
    
    try:
        # Create and register the context-aware callback handler
        _callback_handler = ContextAwareAuditCallbackHandler()
        
        # For async calls, we need to use the async callback lists
        if not hasattr(litellm, '_async_success_callback'):
            litellm._async_success_callback = []
        if not hasattr(litellm, '_async_failure_callback'):
            litellm._async_failure_callback = []
        
        # Register the callback with LiteLLM for both sync and async
        litellm.success_callback = [_callback_handler.log_success_event]
        litellm.failure_callback = [_callback_handler.log_failure_event]
        litellm._async_success_callback = [_callback_handler.log_success_event]
        litellm._async_failure_callback = [_callback_handler.log_failure_event]
        
        print("✅ Context-aware LLM API interceptor successfully set up")
        print(f"   Success callbacks: {litellm.success_callback}")
        print(f"   Failure callbacks: {litellm.failure_callback}")
        print(f"   Async success callbacks: {litellm._async_success_callback}")
        print(f"   Async failure callbacks: {litellm._async_failure_callback}")
        
        return _callback_handler
        
    except Exception as e:
        print(f"❌ Failed to set up context-aware LLM interceptor: {e}")
        return None

def get_callback_handler():
    """Get the global callback handler instance."""
    return _callback_handler

# =============================================================================
# Context Management Functions (for backward compatibility)
# =============================================================================

def connect_audit_tracker(audit_tracker):
    """
    Connect audit tracker for the current execution context.
    
    For async contexts: uses context variables
    For thread pool execution: uses global registry
    """
    try:
        print(f"🔗 Connecting audit tracker in thread {threading.current_thread().ident}")
        
        # Always try to set context variables (for async contexts)
        from core.context_vars import current_audit_tracker
        current_audit_tracker.set(audit_tracker)
        print(f"   ✅ Context variable set")
        
        # Also register in global registry (for thread pool execution)
        user_id = getattr(audit_tracker, 'user_id', 'unknown')
        request_id = f"thread_{threading.current_thread().ident}"
        task_id = _register_audit_tracker(
            audit_tracker=audit_tracker,
            user_id=user_id,
            request_id=request_id,
            phase="thread_execution"
        )
        
        print(f"   ✅ Global registry set: task_id={task_id}")
        print(f"   ✅ Registry audit tracker: {audit_tracker is not None}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect audit tracker: {e}")
        return False

def set_current_phase(phase: str):
    """
    Set the current blog generation phase in context.
    """
    from core.context_vars import current_phase
    current_phase.set(phase)
    return True
