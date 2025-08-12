"""Blog generation flow orchestration (clean refactor).

This module defines the BlogGenerationFlow which coordinates a multi-phase
AI workflow (research -> draft -> fact check -> finalize) while emitting
status updates and registering phase transitions with the audit tracker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Optional, cast
import logging
import os
import asyncio
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

try:  # Optional import; flow should not hard fail if OpenAI missing
    import openai  # type: ignore
except ImportError:  # pragma: no cover
    openai = None  # type: ignore

from crewai.flow.flow import Flow, start, listen
from crewai import Crew

from .status_manager import StatusUpdateManager
from .agent_factory import AgentFactory
from .task_factory import TaskFactory
from .tools_manager import ToolsManager
from .topic_utils import generate_concise_topic
from .content_validator import ContentValidator
from .flow_post_processor import FlowPostProcessor
from core.llm_interceptor import _register_audit_tracker
from core.config import config  # reuse existing config for model + key
from core.crewai_rate_limiter import CrewAIRateLimitManager
from core.rate_limit_config import BlogGenRateLimitConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class FlowState:
    topic: Optional[str] = None
    current_year: Optional[int] = None
    current_phase: Optional[str] = None
    results: Dict[str, Any] = field(default_factory=dict)
    instructions: Optional[str] = None  # optional raw user prompt for auto-topic


class BlogGenerationFlow(Flow):
    """Orchestrates the blog generation multi-agent workflow."""

    def __init__(
        self,
        status_callback: Optional[Callable] = None,
        user_id: Optional[str] = None,
        blog_id: Optional[str] = None,
        audit_tracker: Optional[Any] = None,
        topic: Optional[str] = None,
        current_year: Optional[int] = None,
        instructions: Optional[str] = None,
    ) -> None:
        # Create mutable state BEFORE calling Flow.__init__ because the base class
        # may introspect attributes/properties (which reference flow_state)
        self.flow_state = FlowState()

        super().__init__()
        # Identifiers / context
        self.user_id = user_id
        self.blog_id = blog_id
        self.audit_tracker = audit_tracker

        # Collaborators
        self.status_manager = StatusUpdateManager(status_callback)
        self.agent_factory = AgentFactory()
        self.task_factory = TaskFactory()
        self.tools_manager = ToolsManager(audit_tracker=audit_tracker)
        
        # Initialize rate limiting based on configuration
        if config.rate_limit.enabled:
            # Convert main config to BlogGenRateLimitConfig
            rate_config = BlogGenRateLimitConfig(
                tokens_per_minute=config.rate_limit.tokens_per_minute,
                requests_per_minute=config.rate_limit.requests_per_minute,
                max_retries=config.rate_limit.max_retries,
                base_delay=config.rate_limit.base_delay,
                max_delay=config.rate_limit.max_delay,
                enable_chunking=config.rate_limit.enable_chunking
            )
            self.rate_limiter = CrewAIRateLimitManager(rate_config)
            logger.info(f"Rate limiting enabled: {config.rate_limit.tokens_per_minute} TPM, {config.rate_limit.requests_per_minute} RPM")
        else:
            self.rate_limiter = None
            logger.info("Rate limiting disabled")

    # Mutable state already created pre-super

        # Seed initial values if provided
        if topic:
            self.flow_state.topic = topic.strip() or None
        if current_year:
            self.flow_state.current_year = current_year
        if instructions:
            self.flow_state.instructions = instructions

        logger.info(
            "BlogGenerationFlow initialized (blog_id=%s user_id=%s)",
            blog_id,
            user_id,
        )

    # Public API ------------------------------------------------------
    def set_topic(self, topic: str, year: Optional[int] = None) -> None:
        self.flow_state.topic = topic
        if year:
            self.flow_state.current_year = year

    # Compatibility properties (backward compatibility with old code using flow.topic / flow.current_year)
    @property
    def topic(self) -> Optional[str]:  # type: ignore[override]
        if not hasattr(self, "flow_state"):
            return None
        return self.flow_state.topic

    @topic.setter
    def topic(self, value: Optional[str]) -> None:  # type: ignore[override]
        self.flow_state.topic = value

    @property
    def current_year(self) -> Optional[int]:  # type: ignore[override]
        if not hasattr(self, "flow_state"):
            return None
        return self.flow_state.current_year

    @current_year.setter
    def current_year(self, value: Optional[int]) -> None:  # type: ignore[override]
        self.flow_state.current_year = value

    @property
    def instructions(self) -> Optional[str]:
        return self.flow_state.instructions

    @instructions.setter
    def instructions(self, value: Optional[str]) -> None:
        self.flow_state.instructions = value

    # Internal helpers ------------------------------------------------
    def _update_audit_phase(self, phase: str) -> None:
        if not self.audit_tracker:
            return
        try:  # pragma: no cover - defensive
            _register_audit_tracker(
                self.audit_tracker,
                user_id=self.user_id or "unknown",
                request_id=f"flow_{self.blog_id}",
                phase=phase,
            )
        except Exception as e:  # pragma: no cover
            logger.warning("Audit phase update failed (%s): %s", phase, e)

    def _status(self, message: str, step: int, detail: str = "") -> None:
        self.status_manager.send_status_update(message, step=step, detail=detail)

    def _error(self, message: str) -> None:
        self.status_manager.send_error_update(message)

    def _complete(self, final_content: str) -> None:
        self.status_manager.send_completion_update(final_content)

    def _execute(self, agent, task, phase_name: str = "unknown") -> Any:
        """Execute crew with optional rate limiting and error handling"""
        crew = Crew(agents=[agent], tasks=[task], verbose=True)
        
        # If rate limiting is disabled, use direct execution
        if not self.rate_limiter:
            logger.info(f"Executing {phase_name} without rate limiting")
            return crew.kickoff()
        
        # Use asyncio to run the rate-limited execution
        import asyncio
        
        async def execute_with_rate_limiting():
            if self.rate_limiter is None:
                raise RuntimeError("Rate limiter not initialized")
            return await self.rate_limiter.execute_crew_with_rate_limiting(
                crew=crew,
                inputs={
                    'topic': self.flow_state.topic or '',
                    'current_year': self.flow_state.current_year or datetime.now().year
                },
                phase_name=phase_name,
                max_retries=config.rate_limit.max_retries
            )
        
        # Run the async function
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, schedule as task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, execute_with_rate_limiting())
                    return future.result(timeout=300)  # 5 minute timeout
            else:
                return asyncio.run(execute_with_rate_limiting())
        except Exception as e:
            logger.error(f"Rate-limited execution failed for {phase_name}: {e}")
            # Fallback to direct execution if rate limiting fails
            logger.warning(f"Falling back to direct execution for {phase_name}")
            return crew.kickoff()

    def _require_topic(self) -> None:
        if not self.flow_state.topic:
            raise ValueError("Topic must be set before starting the flow")

    def _auto_generate_topic(self) -> None:
        """Generate a topic from instructions if absent using shared utility.

        Safe no-op if topic already present. Falls back to heuristic when
        OpenAI not configured/available.
        """
        if self.flow_state.topic:
            return
        raw_instructions = (self.flow_state.instructions or "").strip()
        if not raw_instructions:
            self.flow_state.topic = "AI Blog Topic"
            logger.warning("Auto-topic generation skipped (no instructions); using fallback 'AI Blog Topic'.")
            return
        try:
            generated = generate_concise_topic(
                raw_instructions,
                openai_api_key=config.api.openai_key,
                model=config.models.default_model,
            )
            self.flow_state.topic = generated
            logger.info("Auto-generated topic: %s", generated)
        except Exception as e:  # pragma: no cover
            fallback = raw_instructions[:60].strip() or "AI Blog Topic"
            self.flow_state.topic = fallback
            logger.error("Auto topic generation failed (%s); using fallback '%s'", e, fallback)

    # Phases -----------------------------------------------------------
    @start()
    def initialize_flow(self) -> Dict[str, Any]:  # Phase 0
        self.flow_state.current_phase = "initialization"
        self._update_audit_phase("initialization")
        if not self.flow_state.current_year:
            self.flow_state.current_year = datetime.now().year
        # Auto-generate topic if missing
        if not self.flow_state.topic:
            self._auto_generate_topic()
        self._status("Initializing blog generation...", step=0, detail="Preparing context")
        return {
            "topic": self.flow_state.topic,
            "current_year": self.flow_state.current_year,
            "user_id": self.user_id,
            "blog_id": self.blog_id,
        }

    @listen(initialize_flow)
    def research_phase(self, init_data: Dict[str, Any]) -> Dict[str, Any]:  # Phase 1
        self._require_topic()
        self.flow_state.current_phase = "research"
        self._update_audit_phase("research")
        self._status(
            f"Researching '{self.flow_state.topic}'...",
            step=1,
            detail="Collecting sources",
        )
        try:
            # Assure type checker topic/year are present
            topic = cast(str, self.flow_state.topic)
            year = cast(int, self.flow_state.current_year)
            tools = self.tools_manager.get_research_tools()
            agent = self.agent_factory.create_researcher(tools)
            task = self.task_factory.create_research_task(
                agent, topic, year, self.instructions
            )
            result = self._execute(agent, task, "research")
            self.flow_state.results["research"] = result
            self._status("Research completed", step=1, detail="Sources gathered")
            return {**init_data, "research_results": result}
        except Exception as e:  # pragma: no cover
            logger.exception("Research phase failed")
            self._error(f"Research failed: {e}")
            raise

    @listen(research_phase)
    def content_generation_phase(self, research_data: Dict[str, Any]) -> Dict[str, Any]:  # Phase 2
        self._require_topic()
        self.flow_state.current_phase = "content_generation"
        self._update_audit_phase("content_generation")
        self._status("Generating draft content...", step=2, detail="Authoring with images")
        try:
            topic = cast(str, self.flow_state.topic)
            year = cast(int, self.flow_state.current_year)
            tools = self.tools_manager.get_content_tools()
            agent = self.agent_factory.create_content_creator(tools)
            task = self.task_factory.create_content_task(
                agent, topic, year, self.instructions
            )
            
            # Start parallel image generation for common blog concepts
            self._status("Generating draft content...", step=2, detail="Content + parallel image generation")
            image_futures = self._start_parallel_image_generation(topic)
            
            # Execute main content generation
            draft = self._execute(agent, task, "content_generation")
            
            # Wait for parallel image generation to complete (if any started)
            self._complete_parallel_image_generation(image_futures)
            
            self.flow_state.results["content"] = draft
            self._status("Content draft complete", step=2, detail="Draft ready")
            return {**research_data, "initial_content": draft}
        except Exception as e:  # pragma: no cover
            logger.exception("Content generation failed")
            self._error(f"Content generation failed: {e}")
            raise

    @listen(content_generation_phase)
    def content_validation_phase(self, content_data: Dict[str, Any]) -> Dict[str, Any]:  # Phase 2.5
        """Validate and clean content to ensure proper image tool usage."""
        self._require_topic()
        self._status("Validating content...", step=2, detail="Checking image sources")
        self._update_audit_phase("content_validation")
        
        try:
            initial_content = content_data.get("initial_content", "")
            content_str = str(initial_content)
            
            # Validate content
            validation = ContentValidator.validate_content(content_str)
            ContentValidator.log_validation_results(validation, "Content Validation")
            
            # If deprecated images found, clean them and regenerate if needed
            if validation['deprecated_images'] > 0:
                logger.warning(f"⚠️ Found {validation['deprecated_images']} deprecated image sources, cleaning content")
                cleaned_content = ContentValidator.clean_deprecated_images(content_str)
                
                # If we removed images and have tools available, try to regenerate proper images
                if validation['total_images'] > validation['valid_images']:
                    self._status("Regenerating images...", step=2, detail="Using proper image tools")
                    try:
                        # Get content creation tools and agent
                        tools = self.tools_manager.get_content_tools()
                        agent = self.agent_factory.create_content_creator(tools)
                        
                        # Create a task specifically for adding images to existing content
                        image_task = self.task_factory.create_image_enhancement_task(
                            agent, cleaned_content, self.flow_state.topic or ""
                        )
                        
                        # Execute image enhancement
                        enhanced_content = self._execute(agent, image_task, "image_enhancement")
                        
                        # Re-validate the enhanced content
                        final_validation = ContentValidator.validate_content(str(enhanced_content))
                        ContentValidator.log_validation_results(final_validation, "Post-Enhancement")
                        
                        self.flow_state.results["content"] = enhanced_content
                        validated_content = enhanced_content
                        
                    except Exception as e:
                        logger.error(f"Image enhancement failed: {e}")
                        # Fall back to cleaned content
                        self.flow_state.results["content"] = cleaned_content
                        validated_content = cleaned_content
                else:
                    self.flow_state.results["content"] = cleaned_content
                    validated_content = cleaned_content
            else:
                # Content is valid as-is
                logger.info("✅ Content validation passed - no deprecated images found")
                validated_content = initial_content
            
            self._status("Content validation complete", step=2, detail="Ready for fact-checking")
            return {**content_data, "initial_content": validated_content, "validated_content": validated_content}
            
        except Exception as e:  # pragma: no cover
            logger.exception("Content validation failed")
            # Fall back to original content if validation fails
            return content_data

    @listen(content_validation_phase)
    def fact_checking_phase(self, content_data: Dict[str, Any]) -> Dict[str, Any]:  # Phase 3
        self._require_topic()
        self.flow_state.current_phase = "fact_checking"
        self._update_audit_phase("fact_checking")
        self._status("Fact-checking content...", step=3, detail="Verifying claims")
        try:
            topic = cast(str, self.flow_state.topic)
            tools = self.tools_manager.get_research_tools()
            agent = self.agent_factory.create_fact_checker(tools)
            task = self.task_factory.create_fact_check_task(agent, topic, self.instructions)
            checked = self._execute(agent, task, "fact_checking")
            self.flow_state.results["fact_checked"] = checked
            self._status("Fact-check complete", step=3, detail="Content validated")
            return {**content_data, "fact_checked_content": checked}
        except Exception as e:  # pragma: no cover
            logger.exception("Fact checking failed")
            self._error(f"Fact checking failed: {e}")
            raise

    @listen(fact_checking_phase)
    def finalization_phase(self, verified_content: Dict[str, Any]) -> Dict[str, Any]:  # Phase 4
        self._require_topic()
        self.flow_state.current_phase = "finalization"
        self._update_audit_phase("finalization")
        self._status("Finalizing blog post...", step=4, detail="Polishing output")
        try:
            topic = cast(str, self.flow_state.topic)
            agent = self.agent_factory.create_finalizer()
            task = self.task_factory.create_finalization_task(agent, topic, self.instructions)
            final_post = self._execute(agent, task, "finalization")
            
            # Post-process to ensure proper image usage and clean deprecated sources
            processed_post = FlowPostProcessor.process_blog_content(
                content=str(final_post),
                topic=topic,
                force_tool_usage=True
            )
            
            # Ensure adequate images (2-3) - inject missing images if necessary
            from .mandatory_image_injector import create_mandatory_image_injector
            image_injector = create_mandatory_image_injector()
            final_content = image_injector.ensure_adequate_images(processed_post, topic)
            
            self.flow_state.results["final"] = final_content
            self._complete(final_content)
            return {**verified_content, "final_blog_post": final_content, "generation_complete": True}
        except Exception as e:  # pragma: no cover
            logger.exception("Finalization failed")
            self._error(f"Finalization failed: {e}")
            raise

    def _start_parallel_image_generation(self, topic: str) -> Dict[str, Any]:
        """Start parallel AI image generation for common blog concepts."""
        try:
            # Only run parallel generation if we have OpenAI configured
            tools = self.tools_manager.get_content_tools()
            openai_tool = next((tool for tool in tools if hasattr(tool, 'name') and tool.name == "openai_image_generate"), None)
            
            if not openai_tool or not hasattr(openai_tool, '_api_key') or not openai_tool._api_key:
                logger.info("OpenAI image tool not available, skipping parallel generation")
                return {}
            
            # Generate common image concepts for the topic
            image_concepts = self._generate_image_concepts(topic)
            
            futures = {}
            with ThreadPoolExecutor(max_workers=2) as executor:  # Limit to 2 parallel images
                for concept_name, prompt in image_concepts.items():
                    try:
                        future = executor.submit(self._generate_single_ai_image, openai_tool, prompt)
                        futures[concept_name] = future
                        logger.info(f"Started parallel image generation for: {concept_name}")
                    except Exception as e:
                        logger.warning(f"Failed to start image generation for {concept_name}: {e}")
            
            return futures
            
        except Exception as e:
            logger.warning(f"Parallel image generation setup failed: {e}")
            return {}
    
    def _complete_parallel_image_generation(self, image_futures: Dict[str, Any]) -> None:
        """Complete parallel image generation and log results."""
        if not image_futures:
            return
            
        for concept_name, future in image_futures.items():
            try:
                # Wait for completion with timeout
                result = future.result(timeout=30)
                if result and "![" in result:
                    logger.info(f"✅ Parallel image generated for {concept_name}")
                else:
                    logger.warning(f"⚠️ Parallel image generation failed for {concept_name}")
            except concurrent.futures.TimeoutError:
                logger.warning(f"⏰ Parallel image generation timed out for {concept_name}")
            except Exception as e:
                logger.warning(f"❌ Parallel image generation error for {concept_name}: {e}")
    
    def _generate_image_concepts(self, topic: str) -> Dict[str, str]:
        """Generate image concepts based on the blog topic."""
        # Extract key concepts for image generation
        topic_lower = topic.lower()
        concepts = {}
        
        # Hero image concept
        concepts["hero"] = f"Professional illustration of {topic}, clean modern style, high-tech aesthetic"
        
        # Add topic-specific concepts
        if any(word in topic_lower for word in ["ai", "artificial intelligence", "machine learning"]):
            concepts["ai_concept"] = "Artificial intelligence brain network, neural connections, futuristic technology"
        elif any(word in topic_lower for word in ["data", "analytics", "visualization"]):
            concepts["data_concept"] = "Data visualization charts and graphs, modern dashboard, analytics interface"
        elif any(word in topic_lower for word in ["business", "strategy", "management"]):
            concepts["business_concept"] = "Professional business meeting, modern office environment, collaboration"
        elif any(word in topic_lower for word in ["technology", "tech", "software"]):
            concepts["tech_concept"] = "Modern technology interface, clean software design, digital innovation"
        
        return concepts
    
    def _generate_single_ai_image(self, openai_tool, prompt: str) -> str:
        """Generate a single AI image using the OpenAI tool."""
        try:
            result = openai_tool._run(prompt=prompt, size="1024x1024", aspect="square")
            return result
        except Exception as e:
            logger.error(f"AI image generation failed for prompt '{prompt[:50]}...': {e}")
            return ""

__all__ = ["BlogGenerationFlow"]
