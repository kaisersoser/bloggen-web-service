"""
CrewAI Rate Limiting Integration

This module integrates the advanced rate limiter with CrewAI flows
to prevent OpenAI API rate limit errors during blog generation.
"""

import asyncio
import logging
from typing import Any, Optional, Callable, Dict, List, Sequence
from functools import wraps

from crewai import Crew, Agent, Task
from crewai.flow.flow import Flow

from core.rate_limiter import (
    AdvancedRateLimiter, 
    RateLimitConfig, 
    rate_limited_api_call, 
    SmartTokenEstimator,
    exponential_backoff_retry
)

logger = logging.getLogger(__name__)


class CrewAIRateLimitManager:
    """Manages rate limiting for CrewAI operations"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.rate_limiter = AdvancedRateLimiter(config)
        self.token_estimator = SmartTokenEstimator()
        
    def estimate_crew_execution_tokens(self, crew: Crew, topic: str = "") -> int:
        """Estimate total tokens for a crew execution"""
        base_tokens = 5000  # Base overhead
        
        # Add tokens per agent (conservative estimate)
        agent_tokens = len(crew.agents) * 8000
        
        # Add tokens per task
        task_tokens = len(crew.tasks) * 3000
        
        # Topic complexity factor
        topic_factor = len(topic.split()) * 100
        
        total = base_tokens + agent_tokens + task_tokens + topic_factor
        
        logger.debug(f"Estimated crew execution tokens: {total} for {len(crew.agents)} agents, {len(crew.tasks)} tasks")
        return total
    
    async def execute_crew_with_rate_limiting(
        self, 
        crew: Crew, 
        inputs: Dict[str, Any],
        phase_name: str = "crew_execution",
        max_retries: int = 3
    ) -> Any:
        """Execute a crew with rate limiting and retry logic"""
        
        # Estimate token usage
        topic = inputs.get('topic', inputs.get('query', ''))
        estimated_tokens = self.estimate_crew_execution_tokens(crew, topic)
        
        # Determine primary model (use first agent's model if available)
        primary_model = "gpt-5"  # Default
        if crew.agents:
            agent_llm = getattr(crew.agents[0], 'llm', None)
            if agent_llm and hasattr(agent_llm, 'model'):
                primary_model = agent_llm.model
        
        @rate_limited_api_call(
            model=primary_model, 
            estimated_tokens=estimated_tokens, 
            max_retries=max_retries
        )
        async def execute_crew():
            logger.info(f"Executing crew for phase '{phase_name}' with estimated {estimated_tokens} tokens")
            
            # Execute crew (CrewAI's kickoff method is typically sync)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, crew.kickoff, inputs)
            
            logger.info(f"Crew execution completed for phase '{phase_name}'")
            return result
        
        return await execute_crew()
    
    def create_rate_limited_crew(
        self,
        agents: Sequence[Agent],
        tasks: Sequence[Task],
        **crew_kwargs
    ) -> Crew:
        """Create a crew with rate limiting considerations"""
        
        # Ensure agents have reasonable model configurations
        for agent in agents:
            if hasattr(agent, 'llm') and agent.llm:
                # Could add model-specific configurations here
                pass
        
        crew = Crew(agents=list(agents), tasks=list(tasks), **crew_kwargs)
        
        # Store rate limiting metadata (use setattr to avoid type issues)
        setattr(crew, '_rate_limiter', self.rate_limiter)
        setattr(crew, '_token_estimator', self.token_estimator)
        
        return crew


def rate_limited_flow_method(
    phase_name: str,
    estimated_tokens: Optional[int] = None,
    model: str = "gpt-5",
    max_retries: int = 3
):
    """
    Decorator for CrewAI Flow methods that adds rate limiting
    
    Usage:
        class BlogGenerationFlow(Flow):
            @rate_limited_flow_method(phase_name="research", estimated_tokens=15000)
            def research_phase(self, topic: str):
                # Your crew execution here
                pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            # Extract topic for token estimation if not provided
            tokens = estimated_tokens
            if tokens is None:
                # Try to extract topic from various sources
                topic = ""
                if args:
                    topic = str(args[0])
                elif hasattr(self, 'topic') and self.topic:
                    topic = self.topic
                elif hasattr(self, 'flow_state') and self.flow_state.topic:
                    topic = self.flow_state.topic
                
                tokens = SmartTokenEstimator.estimate_crew_tokens(topic, phase_name)
            
            # Apply rate limiting
            rate_limiter = getattr(self, '_rate_limiter', None)
            if not rate_limiter:
                # Create a default rate limiter if none exists
                rate_limiter = AdvancedRateLimiter()
                self._rate_limiter = rate_limiter
            
            # Acquire permission before executing
            await rate_limiter.acquire(model, tokens)
            
            # Execute with retry logic
            @exponential_backoff_retry(max_retries=max_retries)
            async def execute_phase():
                logger.info(f"Executing flow phase '{phase_name}' with {tokens} estimated tokens")
                
                # Call the original method
                if asyncio.iscoroutinefunction(func):
                    result = await func(self, *args, **kwargs)
                else:
                    # Run sync function in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, func, self, *args, **kwargs)
                
                logger.info(f"Flow phase '{phase_name}' completed successfully")
                return result
            
            return await execute_phase()
        
        @wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            # For sync methods, run the async wrapper
            return asyncio.run(async_wrapper(self, *args, **kwargs))
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class RateLimitedFlow(Flow):
    """Enhanced Flow class with built-in rate limiting"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rate_limiter = AdvancedRateLimiter()
        self._crew_manager = CrewAIRateLimitManager()
        
        logger.info("Initialized rate-limited flow")
    
    async def execute_crew_safely(
        self, 
        crew: Crew, 
        inputs: Dict[str, Any],
        phase_name: str = "unknown",
        max_retries: int = 3
    ) -> Any:
        """Execute a crew with comprehensive error handling and rate limiting"""
        try:
            return await self._crew_manager.execute_crew_with_rate_limiting(
                crew=crew,
                inputs=inputs,
                phase_name=phase_name,
                max_retries=max_retries
            )
        except Exception as e:
            logger.error(f"Crew execution failed for phase '{phase_name}': {e}")
            
            # Send status update if callback available
            if hasattr(self, 'status_manager') and getattr(self, 'status_manager', None):
                status_manager = getattr(self, 'status_manager')
                if hasattr(status_manager, 'send_update'):
                    status_manager.send_update(
                        step_name=f"{phase_name}_failed",
                        progress=0.0,
                        details=f"Rate limit error: {str(e)}"
                    )
            
            raise e
    
    def create_rate_limited_crew(self, agents: Sequence[Agent], tasks: Sequence[Task], **kwargs) -> Crew:
        """Create a crew with rate limiting"""
        return self._crew_manager.create_rate_limited_crew(agents, tasks, **kwargs)


# Monkey patch existing Flow classes to add rate limiting
def patch_existing_flows():
    """Add rate limiting to existing flow classes"""
    
    def safe_execute_crew(original_method):
        """Wrapper for crew execution methods"""
        
        @wraps(original_method)
        async def wrapper(self, *args, **kwargs):
            # Check if we already have rate limiting
            if not hasattr(self, '_rate_limiter'):
                self._rate_limiter = AdvancedRateLimiter()
                self._crew_manager = CrewAIRateLimitManager()
            
            # Extract crew and inputs from arguments
            crew = None
            inputs = {}
            
            if args:
                if hasattr(args[0], 'agents'):  # First arg is crew
                    crew = args[0]
                    inputs = args[1] if len(args) > 1 else {}
            
            if crew:
                # Use our safe execution method
                return await self._crew_manager.execute_crew_with_rate_limiting(
                    crew=crew,
                    inputs=inputs,
                    phase_name=getattr(self, '_current_phase', 'unknown')
                )
            else:
                # Fall back to original method
                if asyncio.iscoroutinefunction(original_method):
                    return await original_method(self, *args, **kwargs)
                else:
                    return original_method(self, *args, **kwargs)
        
        return wrapper
    
    # This would patch existing methods - implementation depends on specific flow structure
    logger.info("Flow patching configured (requires specific implementation per flow class)")


# Configure global settings
def configure_global_rate_limiting(
    tokens_per_minute: int = 30000,
    requests_per_minute: int = 3500,
    max_retries: int = 5
):
    """Configure global rate limiting settings"""
    
    config = RateLimitConfig(
        tokens_per_minute=tokens_per_minute,
        requests_per_minute=requests_per_minute,
        max_retries=max_retries
    )
    
    # Update global rate limiter
    import core.rate_limiter as rl
    rl.global_rate_limiter = AdvancedRateLimiter(config)
    
    logger.info(f"Configured global rate limiting: {tokens_per_minute} TPM, {requests_per_minute} RPM")


if __name__ == "__main__":
    # Example usage
    async def test_integration():
        manager = CrewAIRateLimitManager()
        
        # Example crew creation and execution would go here
        logger.info("CrewAI rate limiting integration ready")
    
    asyncio.run(test_integration())
