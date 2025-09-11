"""
Simplified Database Cost Tracker for Blog Generation Audit

This module provides cost tracking without direct database dependencies.
It focuses on console output and can be extended later with database integration.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

# Set up logger for this module
logger = logging.getLogger(__name__)

class SimpleCostTracker:
    """
    Simplified cost tracker for development and testing.
    Provides console output and basic cost calculations without database dependencies.
    """
    
    def __init__(self, session_type: str, user_id: Optional[str] = None, blog_id: Optional[str] = None):
        """
        Initialize the cost tracker.
        
        Args:
            session_type: Type of session ('blog_generation', 'title_generation', etc.)
            user_id: ID of the user performing the action
            blog_id: ID of the blog being processed (optional)
        """
        self.session_type = session_type
        self.user_id = user_id
        self.blog_id = blog_id
        self.session_id = f"session_{int(datetime.utcnow().timestamp())}"
        self.start_time = None
        self.end_time = None
        
        # Track costs and tokens
        self.total_cost = 0.0
        self.total_tokens = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.call_count = 0
        self.llm_calls = []
        
        print(f"🔍 SimpleCostTracker initialized for {session_type}")
        print(f"   Session ID: {self.session_id}")
        print(f"   User: {user_id}")
        print(f"   Blog: {blog_id}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.end_session()

    async def start_session(self):
        """Start a new audit session."""
        self.start_time = datetime.utcnow()
        
        print(f"🚀 Starting audit session: {self.session_id}")
        print(f"   Type: {self.session_type}")
        print(f"   Start Time: {self.start_time}")

    async def end_session(self):
        """End the current audit session and print summary."""
        if not self.start_time:
            return
            
        self.end_time = datetime.utcnow()
        duration = (self.end_time - self.start_time).total_seconds()
        
        print(f"\n{'='*60}")
        print(f"🏁 AUDIT SESSION SUMMARY: {self.session_id}")
        print(f"{'='*60}")
        print(f"   Session Type: {self.session_type}")
        print(f"   Duration: {duration:.2f} seconds")
        print(f"   Total Cost: ${self.total_cost:.6f}")
        print(f"   Total Tokens: {self.total_tokens:,}")
        print(f"   Input Tokens: {self.input_tokens:,}")
        print(f"   Output Tokens: {self.output_tokens:,}")
        print(f"   Total Calls: {self.call_count}")
        if self.call_count > 0:
            print(f"   Average Cost per Call: ${(self.total_cost / self.call_count):.6f}")
            print(f"   Average Tokens per Call: {(self.total_tokens / self.call_count):,.0f}")
        print(f"{'='*60}\n")

    async def track_llm_call(self, model: str, input_tokens: int, output_tokens: int, 
                           phase: str, agent_role: str = "agent", call_type: str = "estimated"):
        """
        Track an individual LLM call with cost estimation.
        
        Args:
            model: LLM model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens  
            phase: Phase of the workflow
            agent_role: Role of the agent making the call
            call_type: Type of call ('estimated', 'actual', etc.)
        """
        # Calculate costs using OpenAI pricing
        input_cost, output_cost, total_cost = self._calculate_openai_cost(
            model, input_tokens, output_tokens
        )
        
        # Update session totals
        self.total_cost += total_cost
        self.total_tokens += input_tokens + output_tokens
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.call_count += 1
        
        # Store call details
        call_data = {
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'input_cost': input_cost,
            'output_cost': output_cost,
            'total_cost': total_cost,
            'phase': phase,
            'agent_role': agent_role,
            'call_type': call_type,
            'timestamp': datetime.utcnow()
        }
        self.llm_calls.append(call_data)
        
        print(f"💰 LLM Call Tracked (#{self.call_count}):")
        print(f"   Model: {model}")
        print(f"   Phase: {phase}")
        print(f"   Agent: {agent_role}")
        print(f"   Tokens: {input_tokens:,} in + {output_tokens:,} out = {input_tokens + output_tokens:,} total")
        print(f"   Cost: ${input_cost:.6f} + ${output_cost:.6f} = ${total_cost:.6f}")
        print(f"   Session Total: ${self.total_cost:.6f}")

    def _calculate_openai_cost(self, model: str, input_tokens: int, output_tokens: int):
        """Calculate cost based on OpenAI pricing."""
        # Use centralized pricing from constants
        try:
            from .constants import OPENAI_PRICING, normalize_model_name
            normalized_model = normalize_model_name(model)
            model_pricing = OPENAI_PRICING.get(normalized_model, OPENAI_PRICING['gpt-4o-mini'])
        except ImportError as e:
            logger.error(f"Failed to import centralized pricing constants: {e}")
            # This should not happen in production - indicates missing dependency
            raise RuntimeError("Centralized pricing configuration not available")
        
        # Calculate costs (convert to per-token pricing)
        input_cost = (input_tokens / 1000) * model_pricing['input']
        output_cost = (output_tokens / 1000) * model_pricing['output']
        total_cost = input_cost + output_cost
        
        return input_cost, output_cost, total_cost

    def estimate_crew_cost(self, crew_result: Any, phase_name: str, agent_count: int = 1, agent_role: str = "agent"):
        """
        Estimate cost for a CrewAI execution and track it.
        
        Args:
            crew_result: The result from crew.kickoff()
            phase_name: Name of the phase (e.g., 'research_phase')
            agent_count: Number of agents in the crew
            agent_role: Role of the agent(s)
        """
        # Estimate tokens based on content length and agent count
        content_length = len(str(crew_result)) if crew_result else 0
        
        # Base estimation with some intelligence
        base_input = 1000  # Base context tokens per agent
        dynamic_input = min(content_length // 10, 2000)  # Additional based on input complexity
        estimated_input_tokens = (base_input + dynamic_input) * agent_count
        
        # Output estimation based on response length
        estimated_output_tokens = max(content_length // 4, 100)
        
        # Default to gpt-5-mini for estimation
        model = "gpt-5-mini"
        
        # Track this as an estimated call
        import asyncio
        asyncio.create_task(self.track_llm_call(
            model=model,
            input_tokens=estimated_input_tokens,
            output_tokens=estimated_output_tokens,
            phase=phase_name,
            agent_role=agent_role,
            call_type="estimated"
        ))
        
        print(f"📊 Phase Cost Estimation:")
        print(f"   Phase: {phase_name}")
        print(f"   Content Length: {content_length:,} characters")
        print(f"   Estimated Input: {estimated_input_tokens:,} tokens")
        print(f"   Estimated Output: {estimated_output_tokens:,} tokens")
        print(f"   Agent Count: {agent_count}")

    async def estimate_title_generation_cost(self):
        """
        Estimate cost for title generation.
        """
        # Simple estimation for title generation
        estimated_input = 500  # tokens for context
        estimated_output = 50  # tokens for title
        
        await self.track_llm_call(
            model="gpt-4o-mini",  # Use gpt-4o-mini for title generation
            input_tokens=estimated_input,
            output_tokens=estimated_output,
            phase="title_generation",
            agent_role="title_agent",
            call_type="estimated"
        )
        
        print(f"📊 Title Generation Cost Estimation:")
        print(f"   Estimated Input: {estimated_input:,} tokens")
        print(f"   Estimated Output: {estimated_output:,} tokens")

    def print_cost_summary(self):
        """
        Print a summary of all tracked costs.
        """
        print(f"\n💰 Cost Summary for {self.session_type}")
        print(f"   Session ID: {self.session_id}")
        print(f"   Total Cost: ${self.total_cost:.4f}")
        print(f"   Total Tokens: {self.total_tokens:,}")
        print(f"   Input Tokens: {self.input_tokens:,}")
        print(f"   Output Tokens: {self.output_tokens:,}")
        print(f"   Total Calls: {self.call_count}")
        if self.start_time:
            duration = (datetime.utcnow() - self.start_time).total_seconds()
            print(f"   Duration: {duration:.1f} seconds")
        print()


# Create an alias for backward compatibility
DatabaseCostTracker = SimpleCostTracker
