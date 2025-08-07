"""
Refactored Blog Generation Flow

A clean, modular implementation of the blog generation workflow.
Follows our coding principles:
- Single Responsibility: Each component has one clear purpose
- Keep It Simple: Removed complexity and over-engineering
- DRY: Eliminated duplicate code through proper separation
- Self-Documenting: Clear structure and obvious intent
"""

from crewai.flow.flow import Flow, listen, start
from crewai import Crew
from datetime import datetime
from typing import Optional, Callable, Dict, Any
import logging

from .status_manager import StatusUpdateManager
from .agent_factory import AgentFactory
from .task_factory import TaskFactory
from .tools_manager import ToolsManager

# Import LLM interceptor for audit tracker registration
from core.llm_interceptor import _register_audit_tracker

logger = logging.getLogger(__name__)


class BlogGenerationFlow(Flow):
    """
    Simplified blog generation workflow using modular components.
    
    This refactored version demonstrates clean code principles:
    - Single responsibility for each component
    - Clear separation of concerns
    - Minimal complexity and over-engineering
    - Self-documenting structure
    """
    
    def __init__(self, status_callback: Optional[Callable] = None, 
                 user_id: Optional[str] = None, blog_id: Optional[str] = None,
                 audit_tracker: Optional[Any] = None):
        """Initialize the blog generation flow with modular components."""
        super().__init__()
        
        # Core components following single responsibility principle
        self.status_manager = StatusUpdateManager(status_callback)
        self.agent_factory = AgentFactory()
        self.task_factory = TaskFactory()
        self.tools_manager = ToolsManager()
        
        # Flow configuration
        self.user_id = user_id
        self.blog_id = blog_id
        self.audit_tracker = audit_tracker
        
        # Flow state
        self.topic: Optional[str] = None
        self.current_year: Optional[int] = None
        self.results: Dict[str, Any] = {}
        
        logger.info("🔧 Blog generation flow initialized")
    
    @start()
    def initialize_flow(self):
        """Initialize the blog generation flow with topic and year."""
        self.status_manager.send_status_update(
            "Initializing blog generation...", 
            step=0, 
            detail="Setting up workflow components"
        )
        
        # Register audit tracker for this thread if available
        if self.audit_tracker:
            try:
                _register_audit_tracker(
                    self.audit_tracker,
                    user_id=self.user_id or "unknown",
                    request_id=f"flow_{self.blog_id}",
                    phase="initialization"
                )
                logger.info(f"✅ Audit tracker registered for flow thread: {self.blog_id}")
            except Exception as e:
                logger.warning(f"Failed to register audit tracker: {e}")
        
        # Set default current year if not provided
        if not self.current_year:
            self.current_year = datetime.now().year
        
        return {
            'topic': self.topic,
            'current_year': self.current_year,
            'user_id': self.user_id,
            'blog_id': self.blog_id
        }
    
    @listen(initialize_flow)
    def research_phase(self, initialization_data: Dict[str, Any]):
        """Execute research phase to gather information on the topic."""
        if not self.topic or not self.current_year:
            raise ValueError("Topic and current_year must be set before research phase")
            
        # Update audit tracker phase if available
        if self.audit_tracker:
            try:
                _register_audit_tracker(
                    self.audit_tracker,
                    user_id=self.user_id or "unknown", 
                    request_id=f"flow_{self.blog_id}",
                    phase="research_phase"
                )
            except Exception as e:
                logger.warning(f"Failed to update audit tracker phase: {e}")
            
        self.status_manager.send_status_update(
            f"Researching '{self.topic}'...", 
            step=1,
            detail="Gathering latest insights and data"
        )
        
        try:
            # Create research agent and task
            research_tools = self.tools_manager.get_research_tools()
            researcher = self.agent_factory.create_researcher(research_tools)
            research_task = self.task_factory.create_research_task(
                researcher, self.topic, self.current_year
            )
            
            # Execute research
            research_crew = Crew(
                agents=[researcher],
                tasks=[research_task],
                verbose=True
            )
            
            research_results = research_crew.kickoff()
            self.results['research'] = research_results
            
            self.status_manager.send_status_update(
                "Research completed", 
                step=1,
                detail="Successfully gathered comprehensive research data"
            )
            
            return {
                **initialization_data,
                'research_results': research_results
            }
            
        except Exception as e:
            logger.error(f"Research phase failed: {e}")
            self.status_manager.send_error_update(f"Research failed: {str(e)}")
            raise
    
    @listen(research_phase)
    def content_generation_phase(self, research_data: Dict[str, Any]):
        """Generate initial blog content with automatic image integration."""
        if not self.topic or not self.current_year:
            raise ValueError("Topic and current_year must be set before content generation")
            
        # Update audit tracker phase if available
        if self.audit_tracker:
            try:
                _register_audit_tracker(
                    self.audit_tracker,
                    user_id=self.user_id or "unknown",
                    request_id=f"flow_{self.blog_id}",
                    phase="content_generation_phase"
                )
            except Exception as e:
                logger.warning(f"Failed to update audit tracker phase: {e}")
            
        self.status_manager.send_status_update(
            "Creating blog content...", 
            step=2,
            detail="Writing engaging content with images"
        )
        
        try:
            # Create content agent and task
            content_tools = self.tools_manager.get_content_tools()
            content_creator = self.agent_factory.create_content_creator(content_tools)
            content_task = self.task_factory.create_content_task(
                content_creator, self.topic, self.current_year
            )
            
            # Execute content generation
            content_crew = Crew(
                agents=[content_creator],
                tasks=[content_task],
                verbose=True
            )
            
            initial_content = content_crew.kickoff()
            self.results['content'] = initial_content
            
            self.status_manager.send_status_update(
                "Content generation completed", 
                step=2,
                detail="Blog content created with integrated images"
            )
            
            return {
                **research_data,
                'initial_content': initial_content
            }
            
        except Exception as e:
            logger.error(f"Content generation phase failed: {e}")
            self.status_manager.send_error_update(f"Content generation failed: {str(e)}")
            raise
    
    @listen(content_generation_phase)
    def fact_checking_phase(self, content_data: Dict[str, Any]):
        """Verify content accuracy and credibility."""
        if not self.topic:
            raise ValueError("Topic must be set before fact checking phase")
            
        # Update audit tracker phase if available
        if self.audit_tracker:
            try:
                _register_audit_tracker(
                    self.audit_tracker,
                    user_id=self.user_id or "unknown",
                    request_id=f"flow_{self.blog_id}",
                    phase="fact_checking_phase"
                )
            except Exception as e:
                logger.warning(f"Failed to update audit tracker phase: {e}")
            
        self.status_manager.send_status_update(
            "Fact-checking content...", 
            step=3,
            detail="Verifying accuracy and credibility"
        )
        
        try:
            # Create fact-checker agent and task
            fact_checker = self.agent_factory.create_fact_checker()
            fact_check_task = self.task_factory.create_fact_check_task(
                fact_checker, self.topic
            )
            
            # Execute fact checking
            fact_check_crew = Crew(
                agents=[fact_checker],
                tasks=[fact_check_task],
                verbose=True
            )
            
            fact_checked_content = fact_check_crew.kickoff()
            self.results['fact_checked'] = fact_checked_content
            
            self.status_manager.send_status_update(
                "Fact-checking completed", 
                step=3,
                detail="Content verified for accuracy and credibility"
            )
            
            return {
                **content_data,
                'fact_checked_content': fact_checked_content
            }
            
        except Exception as e:
            logger.error(f"Fact checking phase failed: {e}")
            self.status_manager.send_error_update(f"Fact checking failed: {str(e)}")
            raise
    
    @listen(fact_checking_phase)
    def finalization_phase(self, verified_content_data: Dict[str, Any]):
        """Polish and finalize the blog post for publication."""
        if not self.topic:
            raise ValueError("Topic must be set before finalization phase")
            
        # Update audit tracker phase if available
        if self.audit_tracker:
            try:
                _register_audit_tracker(
                    self.audit_tracker,
                    user_id=self.user_id or "unknown",
                    request_id=f"flow_{self.blog_id}",
                    phase="finalization_phase"
                )
            except Exception as e:
                logger.warning(f"Failed to update audit tracker phase: {e}")
            
        self.status_manager.send_status_update(
            "Finalizing blog post...", 
            step=4,
            detail="Polishing content for publication"
        )
        
        try:
            # Create finalizer agent and task
            finalizer = self.agent_factory.create_finalizer()
            finalization_task = self.task_factory.create_finalization_task(
                finalizer, self.topic
            )
            
            # Execute finalization
            finalization_crew = Crew(
                agents=[finalizer],
                tasks=[finalization_task],
                verbose=True
            )
            
            final_blog_post = finalization_crew.kickoff()
            self.results['final'] = final_blog_post
            
            # Send completion update
            self.status_manager.send_completion_update(str(final_blog_post))
            
            return {
                **verified_content_data,
                'final_blog_post': final_blog_post,
                'generation_complete': True
            }
            
        except Exception as e:
            logger.error(f"Finalization phase failed: {e}")
            self.status_manager.send_error_update(f"Finalization failed: {str(e)}")
            raise
