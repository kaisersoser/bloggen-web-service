"""
LiteLLM Callback Interceptor for Real-time Cost Tracking with Context Variables

This module provides a callback system to intercept actual OpenAI API calls
made by CrewAI and capture real usage data (tokens, costs, model) in real-time.

Now enhanced with context variables for perfect request isolation in FastAPI.
"""

import os
import time
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
        Uses context variables to correctly attribute usage.
        """
        try:
            # Get context from current async task
            audit_tracker = current_audit_tracker.get(None)
            phase = current_phase.get("unknown")
            request_id = current_request_id.get("unknown")
            user_id = current_user_id.get("unknown")
            
            if not audit_tracker:
                self.logger.warning(f"No audit tracker in context for request {request_id}")
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
        
        # Register the callback with LiteLLM
        litellm.success_callback = [_callback_handler.log_success_event]
        litellm.failure_callback = [_callback_handler.log_failure_event]
        
        print("✅ Context-aware LLM API interceptor successfully set up")
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
    Legacy function for backward compatibility.
    In the new context-aware system, audit tracker is set via context variables.
    """
    from core.context_vars import current_audit_tracker
    current_audit_tracker.set(audit_tracker)
    return True

def set_current_phase(phase: str):
    """
    Set the current blog generation phase in context.
    """
    from core.context_vars import current_phase
    current_phase.set(phase)
    return True
