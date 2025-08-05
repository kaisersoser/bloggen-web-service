"""
Database Cost Tracking Integration for Blog Generation

This module provides integration between the CrewAI flows and the database
audit tracking system. It handles the async database operations while
maintaining compatibility with the existing synchronous flow system.
"""

import asyncio
import logging
from typing import Optional, Any
from .flows import BlogGenerationFlow
from .simple_audit_tracker import SimpleCostTracker as DatabaseCostTracker

class AuditTrackingFlowWrapper:
    """
    Wrapper class that handles database audit tracking for blog generation flows.
    
    This class manages the async database operations while providing a 
    synchronous interface compatible with the existing flow system.
    """
    
    def __init__(self, user_id: str, blog_id: Optional[str] = None, status_callback=None):
        self.user_id = user_id
        self.blog_id = blog_id
        self.status_callback = status_callback
        self.logger = logging.getLogger(__name__)
        
        # Create the flow with audit tracking info
        self.flow = BlogGenerationFlow(
            status_callback=status_callback,
            user_id=user_id,
            blog_id=blog_id
        )
        
        # Audit tracker will be set up during execution
        self.audit_tracker: Optional[DatabaseCostTracker] = None
    
    async def execute_flow_with_audit(self, topic: str, instructions: str = "", current_year: int = 2024):
        """
        Execute the blog generation flow with full audit tracking.
        
        Args:
            topic: Blog topic
            instructions: Additional instructions
            current_year: Current year for context
            
        Returns:
            str: Generated blog content
        """
        # Set up database audit tracking
        self.audit_tracker = DatabaseCostTracker(
            session_type="blog_generation",
            user_id=self.user_id,
            blog_id=self.blog_id
        )
        
        try:
            async with self.audit_tracker:
                self.logger.info(f"Starting audit-tracked blog generation for user {self.user_id}")
                
                # Execute the flow (this is synchronous)
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._execute_flow_sync,
                    topic,
                    instructions,
                    current_year
                )
                
                # Track the overall flow completion
                self.audit_tracker.estimate_crew_cost(
                    crew_result=result,
                    phase_name="complete_flow",
                    agent_count=4,  # research, content, fact-check, finalize
                    agent_role="flow_orchestrator"
                )
                
                # Print summary for console visibility
                self.audit_tracker.print_cost_summary()
                
                return result
                
        except Exception as e:
            self.logger.error(f"Error in audit-tracked flow execution: {e}")
            raise
    
    def _execute_flow_sync(self, topic: str, instructions: str, current_year: int):
        """Execute the flow synchronously"""
        try:
            # Run the flow
            result = self.flow.kickoff(inputs={
                'topic': topic,
                'instructions': instructions,
                'current_year': current_year
            })
            
            return str(result)
            
        except Exception as e:
            self.logger.error(f"Error in flow execution: {e}")
            raise

    def execute_flow_sync(self, topic: str, instructions: str = "", current_year: int = 2024):
        """
        Synchronous wrapper for executing the flow with audit tracking.
        
        This method handles the async audit tracking in a synchronous context.
        """
        try:
            # Run the async execution in a new event loop
            return asyncio.run(self.execute_flow_with_audit(topic, instructions, current_year))
        except Exception as e:
            self.logger.error(f"Error in synchronous flow execution: {e}")
            # Fall back to regular flow execution without audit tracking
            self.logger.warning("Falling back to regular flow execution without database audit")
            return self._execute_flow_sync(topic, instructions, current_year)


async def create_title_audit_session(user_id: str, instructions: str):
    """
    Create an audit session for title generation.
    
    Args:
        user_id: ID of the user generating the title
        instructions: Title generation instructions
        
    Returns:
        str: Generated title (placeholder for now)
    """
    audit_tracker = DatabaseCostTracker(
        session_type="title_generation",
        user_id=user_id,
        blog_id=None
    )
    
    try:
        async with audit_tracker:
            # Track title generation cost
            await audit_tracker.estimate_title_generation_cost()
            
            # Print summary
            audit_tracker.print_cost_summary()
            
            # Return placeholder - actual title generation happens in main.py
            return "Title generation tracked"
            
    except Exception as e:
        logging.getLogger(__name__).error(f"Error in title audit tracking: {e}")
        return "Title generation tracking failed"


def track_title_generation_sync(user_id: str, instructions: str):
    """
    Synchronous wrapper for title generation audit tracking.
    """
    try:
        return asyncio.run(create_title_audit_session(user_id, instructions))
    except Exception as e:
        logging.getLogger(__name__).error(f"Error in sync title tracking: {e}")
        return "Title generation tracking failed"
