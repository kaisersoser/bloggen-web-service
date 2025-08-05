"""
LiteLLM Callback Interceptor for Real-time Cost Tracking

This module provides a callback system to intercept actual OpenAI API calls
made by CrewAI and capture real usage data (tokens, costs, model) in real-time.
"""

import os
import time
from typing import Dict, Any, Optional
from datetime import datetime

# LiteLLM imports for callback system
try:
    import litellm
    from litellm.integrations.custom_logger import CustomLogger
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    print("LiteLLM not available - API interception disabled")

from core.common import get_logger

class AuditCallbackHandler(CustomLogger):
    """
    Custom LiteLLM callback handler to capture actual API usage.
    
    This class intercepts OpenAI API calls made through LiteLLM (which CrewAI uses)
    and forwards the real usage data to our audit tracker.
    """
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger("llm_interceptor")
        self.current_phase = "unknown"
        self.audit_tracker = None
        
    def set_audit_tracker(self, tracker):
        """Set the active audit tracker to receive intercepted data."""
        self.audit_tracker = tracker
        self.logger.info("LLM interceptor connected to audit tracker")
    
    def set_current_phase(self, phase: str):
        """Set the current blog generation phase for context."""
        self.current_phase = phase
        self.logger.debug(f"LLM interceptor phase set to: {phase}")
    
    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        """
        Called when an LLM API call succeeds.
        This is where we capture the actual usage data.
        """
        try:
            if not self.audit_tracker:
                return
            
            # Extract model information
            model = kwargs.get('model', 'unknown')
            
            # Extract usage data from response
            if hasattr(response_obj, 'usage'):
                usage = response_obj.usage
                input_tokens = getattr(usage, 'prompt_tokens', 0)
                output_tokens = getattr(usage, 'completion_tokens', 0)
                total_tokens = getattr(usage, 'total_tokens', input_tokens + output_tokens)
                
                # Track the actual API call
                self.audit_tracker.track_api_call(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    phase=self.current_phase,
                    agent_role="crew_agent"
                )
                
                self.logger.info(f"🎯 Intercepted API call: {model} - {total_tokens} tokens (phase: {self.current_phase})")
                
            else:
                self.logger.warning("No usage data found in API response")
                
        except Exception as e:
            self.logger.error(f"Error in LLM callback handler: {e}")
    
    def log_failure_event(self, kwargs, response_obj, start_time, end_time):
        """Called when an LLM API call fails."""
        model = kwargs.get('model', 'unknown')
        self.logger.warning(f"LLM API call failed for model {model} in phase {self.current_phase}")


# Global callback handler instance
_callback_handler = None

def setup_llm_interceptor():
    """
    Set up the LiteLLM callback interceptor.
    This should be called once during application startup.
    """
    global _callback_handler
    
    if not LITELLM_AVAILABLE:
        print("⚠️  LiteLLM not available - API interception disabled")
        return None
    
    try:
        # Create and register the callback handler
        _callback_handler = AuditCallbackHandler()
        
        # Register the callback with LiteLLM
        litellm.success_callback = [_callback_handler.log_success_event]
        litellm.failure_callback = [_callback_handler.log_failure_event]
        
        print("✅ LLM API interceptor successfully set up")
        return _callback_handler
        
    except Exception as e:
        print(f"❌ Failed to set up LLM interceptor: {e}")
        return None

def get_callback_handler():
    """Get the global callback handler instance."""
    return _callback_handler

def connect_audit_tracker(audit_tracker):
    """Connect an audit tracker to receive intercepted API data."""
    if _callback_handler:
        _callback_handler.set_audit_tracker(audit_tracker)
        return True
    return False

def set_current_phase(phase: str):
    """Set the current blog generation phase for context."""
    if _callback_handler:
        _callback_handler.set_current_phase(phase)
        return True
    return False
