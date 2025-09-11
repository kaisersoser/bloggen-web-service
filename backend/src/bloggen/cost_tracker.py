"""
Cost Tracking Module for Blog Generation

This module provides temporary cost tracking functionality to estimate
the cost of OpenAI API calls during blog generation. This is designed
to be easily added and removed without impacting the core functionality.

Usage:
    # Wrap around crew execution
    with CostTracker() as tracker:
        result = crew.kickoff()
    
    # Get cost information
    cost_info = tracker.get_cost_summary()
"""

import os
import time
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

from core.model_config import get_default_model
from dataclasses import dataclass, field
from datetime import datetime

# Import shared constants and utilities
from .constants import OPENAI_PRICING, calculate_openai_cost, normalize_model_name, DEFAULT_MODEL

# Import new core utilities
from core.logging_utils import setup_cost_tracking_logger
from core.error_handling import handle_cost_tracking_errors

@dataclass
class LLMCall:
    """Data class to track individual LLM API calls"""
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    phase: str = "unknown"
    agent_role: str = "unknown"

@dataclass
class CostSummary:
    """Summary of all costs for a blog generation session"""
    total_cost: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    calls_by_phase: Dict[str, List[LLMCall]] = field(default_factory=dict)
    calls_by_model: Dict[str, List[LLMCall]] = field(default_factory=dict)
    session_start: Optional[datetime] = None
    session_end: Optional[datetime] = None
    duration_seconds: float = 0.0

class CostTracker:
    """
    Context manager to track OpenAI API costs during blog generation.
    
    This tracker estimates costs based on token usage patterns and
    current OpenAI pricing. It's designed to be temporary and easily
    removable without affecting core functionality.
    """
    
    def __init__(self, phase_name: str = "unknown"):
        self.phase_name = phase_name
        self.calls: List[LLMCall] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.logger = setup_cost_tracking_logger(f"tracker_{phase_name}")
        
        # Track original methods for restoration
        self._original_methods = {}
        
    def __enter__(self):
        """Start tracking when entering context"""
        self.start_time = datetime.now()
        self._monkey_patch_openai()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop tracking when exiting context"""
        self.end_time = datetime.now()
        self._restore_openai()
        
    def _monkey_patch_openai(self):
        """
        Temporarily patch OpenAI client to intercept API calls.
        This is a simple approach that can be easily removed.
        
        Note: This is a simplified implementation that estimates costs
        based on typical CrewAI usage patterns rather than intercepting
        actual API calls, which is more complex with the current OpenAI client.
        """
        # For now, we'll use a simpler approach that estimates based on
        # typical patterns rather than intercepting the actual calls
        pass
    
    def _restore_openai(self):
        """Restore original OpenAI methods"""
        # No restoration needed for simplified approach
        pass
    
    @handle_cost_tracking_errors(fallback_value=None)
    def estimate_crew_cost(self, crew_result: Any, phase_name: str, agent_count: int = 1):
        """
        Estimate cost based on crew result and typical usage patterns.
        
        This is a simplified estimation method that can be used when
        direct API interception isn't feasible.
        """
        try:
            # Estimate tokens based on content length
            content_length = len(str(crew_result)) if crew_result else 0
            
            # Rough estimation: 
            # - Input tokens: ~500-2000 per agent (prompts, context)
            # - Output tokens: based on content length (~4 chars per token)
            
            estimated_input_tokens = 1000 * agent_count  # Base prompt tokens per agent
            estimated_output_tokens = max(content_length // 4, 100)  # ~4 chars per token
            
            # Use environment-configured default model for estimation  
            model = get_default_model()
            
            # Calculate costs
            input_cost, output_cost, total_cost = self._calculate_cost(
                model, estimated_input_tokens, estimated_output_tokens
            )
            
            # Create estimated call record
            call = LLMCall(
                timestamp=datetime.now(),
                model=model,
                input_tokens=estimated_input_tokens,
                output_tokens=estimated_output_tokens,
                input_cost=input_cost,
                output_cost=output_cost,
                total_cost=total_cost,
                phase=phase_name,
                agent_role="estimated"
            )
            
            self.calls.append(call)
            
            # Log the estimation
            self.logger.info(
                f"Estimated LLM Cost for {phase_name}: "
                f"${total_cost:.4f} "
                f"(~{estimated_input_tokens + estimated_output_tokens} tokens)"
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to estimate crew cost: {e}")
    
    @handle_cost_tracking_errors(fallback_value=None)
    def estimate_title_generation_cost(self):
        """Estimate cost for title generation API call"""
        # Title generation typically uses a small prompt and short response
        estimated_input_tokens = 150  # Small prompt
        estimated_output_tokens = 20   # Short title
        
        model = get_default_model()  # Use environment-configured model
        
        input_cost, output_cost, total_cost = self._calculate_cost(
            model, estimated_input_tokens, estimated_output_tokens
        )
        
        call = LLMCall(
            timestamp=datetime.now(),
            model=model,
            input_tokens=estimated_input_tokens,
            output_tokens=estimated_output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            phase="title_generation",
            agent_role="title_generator"
        )
        
        self.calls.append(call)
    
    @handle_cost_tracking_errors(fallback_value=None)
    def _record_usage(self, model: str, usage: Any, duration: float):
        """Record usage information from OpenAI response"""
        try:
            # Extract token counts
            input_tokens = getattr(usage, 'prompt_tokens', 0)
            output_tokens = getattr(usage, 'completion_tokens', 0)
            
            # Calculate costs
            input_cost, output_cost, total_cost = self._calculate_cost(
                model, input_tokens, output_tokens
            )
            
            # Create call record
            call = LLMCall(
                timestamp=datetime.now(),
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                input_cost=input_cost,
                output_cost=output_cost,
                total_cost=total_cost,
                phase=self.phase_name,
                agent_role="agent"  # Could be enhanced to track specific agent
            )
            
            self.calls.append(call)
            
            # Log the call for debugging
            self.logger.debug(
                f"LLM Call: {model} | "
                f"Tokens: {input_tokens}+{output_tokens}={input_tokens+output_tokens} | "
                f"Cost: ${total_cost:.4f}"
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to record usage: {e}")
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> tuple:
        """Calculate cost based on model and token usage"""
        return calculate_openai_cost(model, input_tokens, output_tokens)
    
    def _normalize_model_name(self, model: str) -> str:
        """Normalize model name to match pricing keys"""
        return normalize_model_name(model)
    
    def get_cost_summary(self) -> CostSummary:
        """Generate a comprehensive cost summary"""
        if not self.calls:
            return CostSummary()
        
        # Calculate totals
        total_cost = sum(call.total_cost for call in self.calls)
        total_input_tokens = sum(call.input_tokens for call in self.calls)
        total_output_tokens = sum(call.output_tokens for call in self.calls)
        total_tokens = total_input_tokens + total_output_tokens
        
        # Group by phase
        calls_by_phase = {}
        for call in self.calls:
            if call.phase not in calls_by_phase:
                calls_by_phase[call.phase] = []
            calls_by_phase[call.phase].append(call)
        
        # Group by model
        calls_by_model = {}
        for call in self.calls:
            if call.model not in calls_by_model:
                calls_by_model[call.model] = []
            calls_by_model[call.model].append(call)
        
        # Calculate duration
        duration = 0.0
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        
        return CostSummary(
            total_cost=total_cost,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_tokens=total_tokens,
            calls_by_phase=calls_by_phase,
            calls_by_model=calls_by_model,
            session_start=self.start_time,
            session_end=self.end_time,
            duration_seconds=duration
        )
    
    def print_cost_summary(self):
        """Print a detailed cost summary to console"""
        summary = self.get_cost_summary()
        
        if not self.calls:
            print("\n" + "="*60)
            print("📊 BLOG GENERATION COST SUMMARY")
            print("="*60)
            print("No LLM calls tracked.")
            print("="*60)
            return
        
        print("\n" + "="*60)
        print("📊 BLOG GENERATION COST SUMMARY")
        print("="*60)
        
        # Overall summary
        print(f"💰 Total Estimated Cost: ${summary.total_cost:.4f}")
        print(f"🔢 Total Tokens: {summary.total_tokens:,}")
        print(f"   📥 Input Tokens: {summary.total_input_tokens:,}")
        print(f"   📤 Output Tokens: {summary.total_output_tokens:,}")
        print(f"⏱️  Duration: {summary.duration_seconds:.1f} seconds")
        print(f"📞 Total API Calls: {len(self.calls)}")
        
        # Cost breakdown by model
        if summary.calls_by_model:
            print("\n📱 Cost by Model:")
            for model, calls in summary.calls_by_model.items():
                model_cost = sum(call.total_cost for call in calls)
                model_tokens = sum(call.input_tokens + call.output_tokens for call in calls)
                print(f"   {model}: ${model_cost:.4f} ({model_tokens:,} tokens, {len(calls)} calls)")
        
        # Cost breakdown by phase
        if summary.calls_by_phase:
            print("\n🔄 Cost by Phase:")
            for phase, calls in summary.calls_by_phase.items():
                phase_cost = sum(call.total_cost for call in calls)
                phase_tokens = sum(call.input_tokens + call.output_tokens for call in calls)
                print(f"   {phase}: ${phase_cost:.4f} ({phase_tokens:,} tokens, {len(calls)} calls)")
        
        # Cost per token insight
        if summary.total_tokens > 0:
            cost_per_token = summary.total_cost / summary.total_tokens
            print(f"\n💡 Average cost per token: ${cost_per_token:.6f}")
        
        print("="*60)


# Global tracker instance for easy access
_global_tracker: Optional[CostTracker] = None

@contextmanager
def track_blog_generation_cost(phase_name: str = "blog_generation"):
    """
    Context manager for tracking blog generation costs.
    
    Usage:
        with track_blog_generation_cost("research") as tracker:
            result = crew.kickoff()
        
        tracker.print_cost_summary()
    """
    global _global_tracker
    
    tracker = CostTracker(phase_name)
    _global_tracker = tracker
    
    try:
        with tracker:
            yield tracker
    finally:
        _global_tracker = None

def get_current_tracker() -> Optional[CostTracker]:
    """Get the currently active cost tracker"""
    global _global_tracker
    return _global_tracker
