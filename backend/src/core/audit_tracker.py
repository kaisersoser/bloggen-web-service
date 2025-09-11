"""
Enhanced Database Audit Tracker

Combines console output with persistent database logging for comprehensive
audit tracking of LLM costs and usage patterns.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import json
from contextlib import asynccontextmanager

from core.common import get_logger, format_timestamp
from core.audit_database import audit_manager, create_audit_session, log_llm_call, complete_audit_session
from core.model_config import get_default_model

# Import OPENAI_PRICING from the constants file
try:
    from bloggen.constants import OPENAI_PRICING
except ImportError:
    # Fallback pricing if constants not available - using official OpenAI pricing
    OPENAI_PRICING = {
        'gpt-5': {'input': 0.0006, 'output': 0.0048},
        'gpt-5-mini': {'input': 0.00025, 'output': 0.002},
        'gpt-5-nano': {'input': 0.00005, 'output': 0.0004},
        'gpt-4': {'input': 0.03, 'output': 0.06},
        'gpt-3.5-turbo': {'input': 0.001, 'output': 0.002}
    }


class DatabaseAuditTracker:
    """
    Enhanced audit tracker with database persistence.
    
    Provides both console output for immediate feedback and database persistence
    for long-term audit trails and analytics.
    """
    
    def __init__(self, session_type: str, user_id: Optional[str] = None, blog_id: Optional[str] = None):
        """
        Initialize the database audit tracker.
        
        Args:
            session_type: Type of session ('blog_generation', 'title_generation', etc.)
            user_id: ID of the user performing the action
            blog_id: ID of the blog being processed (optional)
        """
        self.session_type = session_type
        self.user_id = user_id
        self.blog_id = blog_id
        self.session_id = None
        self.db_session_id = None
        self.start_time = None
        self.end_time = None
        
        # Track costs and tokens (for console output)
        self.total_cost = 0.0
        self.total_tokens = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.call_count = 0
        self.llm_calls = []
        
        self.logger = get_logger(__name__)
        
        # Console output
        print(f"🔍 DatabaseAuditTracker initialized for {session_type}")
        print(f"   User: {user_id}")
        print(f"   Blog: {blog_id}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.end_session()
    
    def __enter__(self):
        """Sync context manager entry."""
        self.start_session_sync()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.end_session_sync()

    async def start_session(self):
        """Start audit session (async)."""
        self.start_session_sync()

    def start_session_sync(self):
        """Start audit session (sync)."""
        self.start_time = datetime.utcnow()
        self.session_id = f"session_{int(self.start_time.timestamp())}"
        
        # Create database session using async manager
        if self.user_id and self.blog_id:  # Only create session if both user_id and blog_id are provided
            try:
                import asyncio
                
                # Check if we're already in an async context
                try:
                    loop = asyncio.get_running_loop()
                    # We're in an async context, need to use create_task
                    import concurrent.futures
                    import threading
                    
                    # Create a future to hold the result
                    future = concurrent.futures.Future()
                    
                    def run_in_thread():
                        try:
                            # Create a new event loop in a separate thread
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            try:
                                # Type assertions for the type checker
                                assert self.user_id is not None
                                assert self.blog_id is not None
                                
                                result = new_loop.run_until_complete(
                                    audit_manager.create_audit_session(
                                        session_type=self.session_type,
                                        user_id=self.user_id,
                                        blog_id=self.blog_id
                                    )
                                )
                                future.set_result(result)
                            finally:
                                new_loop.close()
                        except Exception as e:
                            future.set_exception(e)
                    
                    # Run in a separate thread to avoid event loop conflicts
                    thread = threading.Thread(target=run_in_thread)
                    thread.start()
                    thread.join()
                    
                    # Get the result from the future
                    self.db_session_id = future.result()
                    
                except RuntimeError:
                    # No event loop running, create one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # Type assertions for the type checker
                        assert self.user_id is not None
                        assert self.blog_id is not None
                        
                        self.db_session_id = loop.run_until_complete(
                            audit_manager.create_audit_session(
                                session_type=self.session_type,
                                user_id=self.user_id,
                                blog_id=self.blog_id
                            )
                        )
                    finally:
                        loop.close()
            except Exception as e:
                self.logger.error(f"Failed to create database session: {e}")
                self.db_session_id = None
        
        print(f"🚀 Audit session started: {self.session_id}")
        if self.db_session_id:
            print(f"   Database session: {self.db_session_id}")
        else:
            print(f"   Database logging: DISABLED")
        
        self.logger.info(f"Started audit session: {self.session_type} for user {self.user_id}")

    async def end_session(self):
        """End audit session (async)."""
        self.end_session_sync()

    def end_session_sync(self):
        """End audit session (sync)."""
        self.end_time = datetime.utcnow()
        duration = (self.end_time - self.start_time).total_seconds() if self.start_time else 0
        
        # Complete database session
        if self.db_session_id and isinstance(self.db_session_id, str):  # Type guard to ensure it's a string
            try:
                import asyncio
                
                # Check if we're already in an async context
                try:
                    loop = asyncio.get_running_loop()
                    # We're in an async context, need to use create_task
                    import concurrent.futures
                    import threading
                    
                    # Create a future to hold the result
                    future = concurrent.futures.Future()
                    
                    def run_in_thread():
                        try:
                            # Create a new event loop in a separate thread
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            try:
                                # Type assertion for the type checker
                                assert isinstance(self.db_session_id, str)
                                
                                new_loop.run_until_complete(
                                    audit_manager.complete_audit_session(
                                        session_id=self.db_session_id,
                                        status='completed'
                                    )
                                )
                                future.set_result(None)
                            finally:
                                new_loop.close()
                        except Exception as e:
                            future.set_exception(e)
                    
                    # Run in a separate thread to avoid event loop conflicts
                    thread = threading.Thread(target=run_in_thread)
                    thread.start()
                    thread.join()
                    
                    # Check for any exceptions
                    future.result()
                    
                except RuntimeError:
                    # No event loop running, create one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # Type assertion for the type checker
                        assert isinstance(self.db_session_id, str)
                        
                        loop.run_until_complete(
                            audit_manager.complete_audit_session(
                                session_id=self.db_session_id,
                                status='completed'
                            )
                        )
                    finally:
                        loop.close()
            except Exception as e:
                self.logger.error(f"Failed to complete database session: {e}")
        
        # Console summary
        print(f"\n🎯 Audit Session Complete: {self.session_id}")
        print(f"   Duration: {duration:.1f}s")
        print(f"   Total Cost: ${self.total_cost:.4f}")
        print(f"   Total Tokens: {self.total_tokens:,}")
        print(f"   LLM Calls: {self.call_count}")
        
        if self.llm_calls:
            print(f"\n📊 Call Breakdown:")
            for call in self.llm_calls:
                print(f"   {call['model']} ({call.get('phase', 'unknown')}): "
                      f"${call['total_cost']:.4f} ({call['total_tokens']} tokens)")
        
        self.logger.info(f"Completed audit session: {self.session_id} - ${self.total_cost:.4f}")

    def track_llm_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        phase: Optional[str] = None,
        agent_role: Optional[str] = None,
        call_type: str = 'estimated',
        request_metadata: Optional[Dict[str, Any]] = None,
        response_metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Track an individual LLM call.
        
        Args:
            model: Model name (e.g., 'gpt-4', 'gpt-3.5-turbo')
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            phase: Generation phase ('research', 'content', 'fact_check', etc.)
            agent_role: Agent role ('researcher', 'content_creator', etc.)
            call_type: 'estimated' or 'actual'
            request_metadata: Additional request metadata
            response_metadata: Additional response metadata
        """
        # Calculate costs
        default_model = get_default_model()
        pricing = OPENAI_PRICING.get(model, OPENAI_PRICING.get(default_model, OPENAI_PRICING.get('gpt-5-nano', {'input': 0.000001, 'output': 0.000002})))
        input_cost = (input_tokens / 1000) * pricing['input']
        output_cost = (output_tokens / 1000) * pricing['output']
        total_cost = input_cost + output_cost
        total_tokens = input_tokens + output_tokens
        
        # Update totals
        self.total_cost += total_cost
        self.total_tokens += total_tokens
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.call_count += 1
        
        # Store call details
        call_data = {
            'model': model,
            'phase': phase,
            'agent_role': agent_role,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': total_tokens,
            'input_cost': input_cost,
            'output_cost': output_cost,
            'total_cost': total_cost,
            'call_type': call_type,
            'timestamp': datetime.utcnow(),
            'request_metadata': request_metadata,
            'response_metadata': response_metadata
        }
        
        self.llm_calls.append(call_data)
        
        # Log to database
        if self.db_session_id and isinstance(self.db_session_id, str):
            try:
                import asyncio
                
                # Check if we're already in an async context
                try:
                    loop = asyncio.get_running_loop()
                    # We're in an async context, need to use separate thread
                    import concurrent.futures
                    import threading
                    
                    # Create a future to hold the result
                    future = concurrent.futures.Future()
                    
                    def run_in_thread():
                        try:
                            # Create a new event loop in a separate thread
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            try:
                                # Type assertion for the type checker
                                assert isinstance(self.db_session_id, str)
                                
                                new_loop.run_until_complete(
                                    audit_manager.log_llm_call(
                                        session_id=self.db_session_id,
                                        model=model,
                                        input_tokens=input_tokens,
                                        output_tokens=output_tokens,
                                        total_cost=total_cost,
                                        phase=phase or "unknown",
                                        agent_role=agent_role or "unknown",
                                        call_type=call_type
                                    )
                                )
                                future.set_result(None)
                            finally:
                                new_loop.close()
                        except Exception as e:
                            future.set_exception(e)
                    
                    # Run in a separate thread to avoid event loop conflicts
                    thread = threading.Thread(target=run_in_thread)
                    thread.start()
                    thread.join()
                    
                    # Check for any exceptions
                    future.result()
                    
                except RuntimeError:
                    # No event loop running, create one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # Type assertion for the type checker
                        assert isinstance(self.db_session_id, str)
                        
                        loop.run_until_complete(
                            audit_manager.log_llm_call(
                                session_id=self.db_session_id,
                                model=model,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                total_cost=total_cost,
                                phase=phase or "unknown",
                                agent_role=agent_role or "unknown",
                                call_type=call_type
                            )
                        )
                    finally:
                        loop.close()
            except Exception as e:
                self.logger.error(f"Failed to log LLM call to database: {e}")
        
        # Console output
        phase_str = f" ({phase})" if phase else ""
        agent_str = f" [{agent_role}]" if agent_role else ""
        print(f"💰 LLM Call: {model}{phase_str}{agent_str} - "
              f"${total_cost:.4f} ({total_tokens:,} tokens)")
        
        self.logger.debug(f"Tracked LLM call: {model} - ${total_cost:.4f}")

    def track_crewai_execution(self, crew_result: Any, phase: str = "unknown"):
        """
        Track CrewAI crew execution with cost estimation.
        
        Args:
            crew_result: Result from crew.kickoff()
            phase: Generation phase identifier
        """
        try:
            # Try to extract usage stats from CrewAI result
            if hasattr(crew_result, 'usage_metrics'):
                metrics = crew_result.usage_metrics
                self._process_crew_metrics(metrics, phase)
            elif hasattr(crew_result, 'token_usage'):
                # Alternative attribute name
                metrics = crew_result.token_usage
                self._process_crew_metrics(metrics, phase)
            else:
                # Fallback estimation - this will be replaced by actual API interception
                self.logger.info(f"No usage metrics found in CrewAI result, relying on API interception for {phase}")
                # We no longer do fallback estimation here since we'll capture real API calls
                
        except Exception as e:
            self.logger.warning(f"Could not extract CrewAI usage metrics: {str(e)}")
            # We no longer do fallback estimation here since we'll capture real API calls
    
    def track_api_call(self, model: str, input_tokens: int, output_tokens: int, phase: str, agent_role: str = "crew_aggregate"):
        """
        Track actual OpenAI API call - to be called from LiteLLM callback interceptor.
        
        Args:
            model: The model used (e.g., 'gpt-4o-mini', 'gpt-3.5-turbo')
            input_tokens: Actual input tokens from API response
            output_tokens: Actual output tokens from API response
            phase: Current phase of blog generation
            agent_role: Role of the agent making the call
        """
        self.track_llm_call(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            phase=phase,
            agent_role=agent_role,
            call_type='actual'
        )
        
        # Log the successful interception
        self.logger.info(f"Intercepted actual API call: {model} - {input_tokens + output_tokens} tokens")
    
    def track_storage_cleanup(self, blog_id: str, images_deleted: int, estimated_storage_gb: float, monthly_savings: float, status: str = "success"):
        """
        Track S3 storage cleanup metrics for cost analysis.
        
        Args:
            blog_id: Blog identifier
            images_deleted: Number of images successfully deleted
            estimated_storage_gb: Estimated storage freed in GB
            monthly_savings: Estimated monthly cost savings in USD
            status: Cleanup status ('success', 'partial', 'failed')
        """
        try:
            # Log storage cleanup as a special LLM call entry for audit purposes
            # Note: We track negative costs as savings in the existing system
            self.track_llm_call(
                model='s3-storage-cleanup',
                input_tokens=images_deleted,  # Reuse input_tokens field for image count
                output_tokens=int(estimated_storage_gb * 1000),  # Convert GB to MB for storage tracking
                phase='storage_cleanup',
                agent_role='s3_cleanup_system',
                call_type='storage'
            )
            
            # Update total cost with negative savings (represents cost reduction)
            self.total_cost -= monthly_savings
            
            # Detailed logging
            self.logger.info(f"S3 Storage Cleanup Tracked: blog_id={blog_id}, "
                           f"images={images_deleted}, storage={estimated_storage_gb:.4f}GB, "
                           f"savings=${monthly_savings:.6f}/month, status={status}")
            
            # Console output for immediate feedback
            print(f"💾 Storage Cleanup: {images_deleted} images deleted")
            print(f"   Storage freed: ~{estimated_storage_gb:.4f} GB")
            print(f"   Monthly savings: ~${monthly_savings:.6f}")
            print(f"   Status: {status}")
            
        except Exception as e:
            self.logger.error(f"Failed to track storage cleanup metrics: {e}")

    def _process_crew_metrics(self, metrics: Any, phase: str):
        """Process actual CrewAI metrics."""
        try:
            # Handle Pydantic UsageMetrics object
            if hasattr(metrics, 'total_tokens'):
                # It's a UsageMetrics object, extract basic info
                total_tokens = getattr(metrics, 'total_tokens', 0)
                prompt_tokens = getattr(metrics, 'prompt_tokens', 0)
                completion_tokens = getattr(metrics, 'completion_tokens', 0)
                
                # Track a single aggregated call since we don't have per-agent breakdown
                self.track_llm_call(
                    model=get_default_model(),  # Default model
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                    phase=phase,
                    agent_role='crew_aggregate',
                    call_type='actual'
                )
            elif isinstance(metrics, dict):
                # Handle dictionary format
                for agent_metrics in metrics.get('agents', []):
                    model = agent_metrics.get('model', get_default_model())
                    input_tokens = agent_metrics.get('prompt_tokens', 0)
                    output_tokens = agent_metrics.get('completion_tokens', 0)
                    agent_role = agent_metrics.get('agent_name', 'unknown')
                    
                    self.track_llm_call(
                        model=model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        phase=phase,
                        agent_role=agent_role,
                        call_type='actual'
                    )
            else:
                # Unknown format, fallback to estimation
                self.logger.warning(f"Unknown metrics format: {type(metrics)}")
                raise ValueError("Unknown metrics format")
                
        except Exception as e:
            self.logger.warning(f"Error processing crew metrics: {str(e)}")
            # Fall back to estimation
            raise e

    def _estimate_crew_usage(self, crew_result: Any, phase: str):
        """Estimate CrewAI usage when actual metrics unavailable."""
        # Conservative estimation based on typical multi-agent usage
        estimated_calls = [
            {'model': 'gpt-4', 'input': 1500, 'output': 800, 'agent': 'researcher'},
            {'model': 'gpt-4', 'input': 2000, 'output': 1200, 'agent': 'content_creator'},
            {'model': 'gpt-3.5-turbo', 'input': 1000, 'output': 500, 'agent': 'fact_checker'},
        ]
        
        for call in estimated_calls:
            self.track_llm_call(
                model=call['model'],
                input_tokens=call['input'],
                output_tokens=call['output'],
                phase=phase,
                agent_role=call['agent'],
                call_type='estimated'
            )

    def get_session_summary(self) -> Dict[str, Any]:
        """Get comprehensive session summary."""
        duration = (
            (self.end_time - self.start_time).total_seconds()
            if self.end_time and self.start_time else None
        )
        
        return {
            'session_id': self.session_id,
            'db_session_id': self.db_session_id,
            'session_type': self.session_type,
            'user_id': self.user_id,
            'blog_id': self.blog_id,
            'total_cost': self.total_cost,
            'total_tokens': self.total_tokens,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'call_count': self.call_count,
            'start_time': format_timestamp(self.start_time) if self.start_time else None,
            'end_time': format_timestamp(self.end_time) if self.end_time else None,
            'duration_seconds': duration,
            'calls': self.llm_calls
        }

    def _get_console_summary(self) -> Dict[str, Any]:
        """Get summary for console output."""
        return {
            'total_cost': self.total_cost,
            'total_tokens': self.total_tokens,
            'call_count': self.call_count,
            'calls_by_model': self._group_calls_by_model(),
            'calls_by_phase': self._group_calls_by_phase()
        }

    def _group_calls_by_model(self) -> Dict[str, Dict[str, Any]]:
        """Group calls by model for summary."""
        grouped = {}
        for call in self.llm_calls:
            model = call['model']
            if model not in grouped:
                grouped[model] = {'count': 0, 'cost': 0.0, 'tokens': 0}
            
            grouped[model]['count'] += 1
            grouped[model]['cost'] += call['total_cost']
            grouped[model]['tokens'] += call['total_tokens']
        
        return grouped

    def _group_calls_by_phase(self) -> Dict[str, Dict[str, Any]]:
        """Group calls by phase for summary."""
        grouped = {}
        for call in self.llm_calls:
            phase = call.get('phase', 'unknown')
            if phase not in grouped:
                grouped[phase] = {'count': 0, 'cost': 0.0, 'tokens': 0}
            
            grouped[phase]['count'] += 1
            grouped[phase]['cost'] += call['total_cost']
            grouped[phase]['tokens'] += call['total_tokens']
        
        return grouped


# Convenience functions for common use cases
@asynccontextmanager
async def track_blog_generation(user_id: str, blog_id: Optional[str] = None):
    """Async context manager for blog generation tracking."""
    async with DatabaseAuditTracker('blog_generation', user_id, blog_id) as tracker:
        yield tracker

@asynccontextmanager  
async def track_title_generation(user_id: str):
    """Async context manager for title generation tracking."""
    async with DatabaseAuditTracker('title_generation', user_id) as tracker:
        yield tracker

def track_blog_generation_sync(user_id: str, blog_id: Optional[str] = None):
    """Sync context manager for blog generation tracking."""
    return DatabaseAuditTracker('blog_generation', user_id, blog_id)

def track_title_generation_sync(user_id: str):
    """Sync context manager for title generation tracking."""
    return DatabaseAuditTracker('title_generation', user_id)


# Export key items
__all__ = [
    'DatabaseAuditTracker',
    'track_blog_generation',
    'track_title_generation', 
    'track_blog_generation_sync',
    'track_title_generation_sync'
]
