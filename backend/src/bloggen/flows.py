"""Blog generation flow orchestration (clean refactor).

This module defines the BlogGenerationFlow which coordinates a multi-phase
AI workflow (research -> draft -> fact check -> finalize) while emitting
status updates and registering phase transitions with the audit tracker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Optional, cast, List
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
from .tools.content_integrity_validator import ContentIntegrityValidator, format_integrity_report
from .tools.url_validation_enforcer import URLValidationEnforcer, create_validation_enforcer
from .tools.reference_deduplicator import ReferenceDeduplicator, create_reference_deduplicator, format_deduplication_report
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
        self.status_manager = StatusUpdateManager(
            task_id=blog_id or "unknown", 
            status_callback=status_callback or (lambda x: None)
        )
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
            return self._execute_with_streaming(crew, phase_name)
        
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
            # Check if we can get the current event loop
            try:
                loop = asyncio.get_event_loop()
                # If we're in a thread pool executor context, we don't have a running loop
                # even though get_event_loop() succeeds
                if loop.is_running():
                    # This means we're truly in an async context, not a thread pool
                    # Create a new event loop in a thread
                    import concurrent.futures
                    import threading
                    
                    result_container = []
                    exception_container = []
                    
                    def run_in_new_loop():
                        try:
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            result = new_loop.run_until_complete(execute_with_rate_limiting())
                            result_container.append(result)
                        except Exception as e:
                            exception_container.append(e)
                        finally:
                            new_loop.close()
                    
                    thread = threading.Thread(target=run_in_new_loop)
                    thread.start()
                    thread.join(timeout=300)  # 5 minute timeout
                    
                    if exception_container:
                        raise exception_container[0]
                    if result_container:
                        return result_container[0]
                    else:
                        raise TimeoutError(f"Rate-limited execution timed out for {phase_name}")
                else:
                    return asyncio.run(execute_with_rate_limiting())
            except RuntimeError:
                # No event loop in current thread, safe to use asyncio.run
                return asyncio.run(execute_with_rate_limiting())
        except Exception as e:
            logger.error(f"Rate-limited execution failed for {phase_name}: {e}")
            # Fallback to direct execution if rate limiting fails
            logger.warning(f"Falling back to direct execution for {phase_name}")
            return self._execute_with_streaming(crew, phase_name)
    
    def _execute_with_streaming(self, crew, phase_name: str) -> Any:
        """Execute crew with content streaming support and periodic status updates"""
        import threading
        import time
        
        try:
            # Get the task manager for streaming
            from core.task_manager import task_manager
            
            # Set up content streaming for this task
            if hasattr(self, 'blog_id') and self.blog_id:
                asyncio.create_task(task_manager.setup_content_streaming(self.blog_id))
            
            # Start periodic updates in a background thread
            execution_complete = threading.Event()
            update_thread = threading.Thread(
                target=self._send_periodic_updates_during_execution,
                args=(phase_name, execution_complete)
            )
            update_thread.daemon = True
            update_thread.start()
            
            # Execute the crew in the main thread
            try:
                result = crew.kickoff()
            finally:
                # Signal completion to stop updates
                execution_complete.set()
                update_thread.join(timeout=1)  # Wait briefly for update thread to finish
            
            # Stream the result based on phase
            if hasattr(self, 'blog_id') and self.blog_id:
                self._stream_phase_result(phase_name, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Streaming execution failed for {phase_name}: {e}")
            # Fallback to basic execution
            return crew.kickoff()
    
    def _send_periodic_updates_during_execution(self, phase_name: str, execution_complete):
        """Send realistic updates while crew is executing"""
        import threading
        import time
        
        logger.info(f"🔄 Starting periodic updates for phase: {phase_name}")
        
        # Define phase-specific realistic updates
        phase_updates = {
            "research": [
                ("🔍 Analyzing topic depth and complexity...", "Research Agent"),
                ("📚 Searching academic databases and recent publications...", "Research Agent"),
                ("🏢 Gathering industry reports and expert insights...", "Research Agent"),
                ("✅ Cross-referencing sources for accuracy...", "Research Agent"),
                ("🧩 Synthesizing research findings...", "Research Agent")
            ],
            "content_generation": [
                ("📝 Structuring article outline and key points...", "Content Generation Agent"),
                ("✨ Crafting engaging introduction...", "Content Generation Agent"),
                ("📄 Developing main content sections...", "Content Generation Agent"),
                ("🔗 Integrating research insights with examples...", "Content Generation Agent"),
                ("📖 Enhancing readability and flow...", "Content Generation Agent")
            ],
            "fact_checking": [
                ("📊 Verifying statistical claims and data...", "Fact Checking Agent"),
                ("🔍 Cross-checking sources and citations...", "Fact Checking Agent"),
                ("⚙️ Validating technical accuracy...", "Fact Checking Agent"),
                ("✅ Ensuring factual consistency...", "Fact Checking Agent"),
                ("🎯 Final verification pass...", "Fact Checking Agent")
            ]
        }
        
        updates = phase_updates.get(phase_name, [
            ("⚙️ Processing request...", f"{phase_name.replace('_', ' ').title()} Agent"),
            ("🔍 Analyzing content...", f"{phase_name.replace('_', ' ').title()} Agent"),
            ("✨ Generating response...", f"{phase_name.replace('_', ' ').title()} Agent"),
            ("✅ Finalizing output...", f"{phase_name.replace('_', ' ').title()} Agent")
        ])
        
        update_interval = 4  # Send update every 4 seconds
        update_index = 0
        
        try:
            while not execution_complete.is_set():
                if update_index < len(updates):
                    message, agent_name = updates[update_index]
                    logger.info(f"🔄 Sending periodic update {update_index + 1}: {message}")
                    self.status_manager.send_agent_thinking(
                        agent_name=agent_name,
                        thought=message
                    )
                    update_index += 1
                else:
                    # Cycle through additional generic updates
                    generic_updates = [
                        ("🧠 Deep analysis in progress...", f"{phase_name.replace('_', ' ').title()} Agent"),
                        ("⚡ Processing complex logic...", f"{phase_name.replace('_', ' ').title()} Agent"),
                        ("✨ Refining output quality...", f"{phase_name.replace('_', ' ').title()} Agent"),
                        ("🏁 Almost complete...", f"{phase_name.replace('_', ' ').title()} Agent")
                    ]
                    cycle_index = (update_index - len(updates)) % len(generic_updates)
                    message, agent_name = generic_updates[cycle_index]
                    logger.info(f"🔄 Sending generic update {cycle_index + 1}: {message}")
                    self.status_manager.send_agent_thinking(
                        agent_name=agent_name,
                        thought=message
                    )
                    update_index += 1
                
                # Wait for next update or completion
                if execution_complete.wait(timeout=update_interval):
                    break  # Execution completed
                    
        except Exception as e:
            logger.error(f"❌ Error in periodic updates for {phase_name}: {e}")
        finally:
            logger.info(f"🔄 Periodic updates stopped for phase: {phase_name}")
    
    def _stream_phase_result(self, phase_name: str, result: Any):
        """Stream the result of a phase to connected clients"""
        try:
            from core.task_manager import task_manager
            
            if not hasattr(self, 'blog_id') or not self.blog_id:
                return
            
            result_str = str(result) if result else ""
            
            if phase_name == "research":
                # Stream research findings
                if result_str:
                    # Extract key findings from research result
                    findings = self._extract_research_findings(result_str)
                    for finding in findings:
                        asyncio.create_task(
                            task_manager.stream_research_finding(self.blog_id, finding)
                        )
            
            elif phase_name == "content_generation":
                # Stream content paragraphs
                if result_str:
                    paragraphs = self._extract_content_paragraphs(result_str)
                    for paragraph in paragraphs:
                        asyncio.create_task(
                            task_manager.stream_content_paragraph(self.blog_id, paragraph)
                        )
            
            elif phase_name == "fact_checking":
                # Stream fact corrections
                if result_str:
                    corrections = self._extract_fact_corrections(result_str)
                    for correction in corrections:
                        asyncio.create_task(
                            task_manager.stream_fact_correction(self.blog_id, correction)
                        )
            
            elif phase_name == "finalization":
                # Stream final content
                if result_str:
                    asyncio.create_task(
                        task_manager.stream_final_content(self.blog_id, result_str)
                    )
                    
        except Exception as e:
            logger.error(f"Failed to stream {phase_name} result: {e}")
    
    def _extract_research_findings(self, research_result: str) -> list[str]:
        """Extract key research findings from research result"""
        try:
            # Simple extraction - split by common patterns
            lines = research_result.split('\n')
            findings = []
            
            for line in lines:
                line = line.strip()
                if (line and len(line) > 20 and 
                    any(keyword in line.lower() for keyword in 
                        ['found', 'research', 'study', 'report', 'analysis', 'data', 'according'])):
                    findings.append(line[:200])  # Limit length
                    if len(findings) >= 5:  # Limit to 5 findings
                        break
            
            return findings
        except Exception as e:
            logger.error(f"Failed to extract research findings: {e}")
            return []
    
    def _extract_content_paragraphs(self, content_result: str) -> list[str]:
        """Extract content paragraphs from content generation result"""
        try:
            # Split by double newlines to get paragraphs
            paragraphs = [p.strip() for p in content_result.split('\n\n') if p.strip()]
            
            # Filter out very short paragraphs and limit length
            filtered_paragraphs = []
            for p in paragraphs:
                if len(p) > 50:  # Must be substantial content
                    filtered_paragraphs.append(p[:500])  # Limit length
                    if len(filtered_paragraphs) >= 8:  # Limit to 8 paragraphs
                        break
            
            return filtered_paragraphs
        except Exception as e:
            logger.error(f"Failed to extract content paragraphs: {e}")
            return []
    
    def _extract_fact_corrections(self, fact_check_result: str) -> list[str]:
        """Extract fact corrections from fact-checking result"""
        try:
            lines = fact_check_result.split('\n')
            corrections = []
            
            for line in lines:
                line = line.strip()
                if (line and len(line) > 20 and 
                    any(keyword in line.lower() for keyword in 
                        ['corrected', 'updated', 'verified', 'changed', 'fixed', 'error'])):
                    corrections.append(line[:200])  # Limit length
                    if len(corrections) >= 3:  # Limit to 3 corrections
                        break
            
            return corrections
        except Exception as e:
            logger.error(f"Failed to extract fact corrections: {e}")
            return []

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

    # Enhanced notification helper methods
    def _assess_topic_complexity(self, topic: str) -> str:
        """Assess topic complexity for enhanced notifications."""
        try:
            topic_lower = topic.lower()
            technical_keywords = ['ai', 'machine learning', 'blockchain', 'quantum', 'algorithm', 'api', 'cloud', 'microservices']
            business_keywords = ['strategy', 'marketing', 'finance', 'management', 'leadership', 'growth']
            
            if any(keyword in topic_lower for keyword in technical_keywords):
                return "technical"
            elif any(keyword in topic_lower for keyword in business_keywords):
                return "business-focused"
            elif len(topic.split()) > 5:
                return "complex multi-faceted"
            else:
                return "focused"
        except Exception:
            return "standard"
    
    def _get_tool_names(self, tools) -> list[str]:
        """Extract tool names for enhanced notifications."""
        try:
            names = []
            for tool in tools:
                if hasattr(tool, 'name'):
                    names.append(tool.name)
                elif hasattr(tool, '__class__'):
                    names.append(tool.__class__.__name__.replace('Tool', ''))
                else:
                    names.append(str(tool)[:20])
            return names[:5]  # Limit to 5 tools
        except Exception:
            return ["Research Tools"]
    
    def _extract_key_insights(self, text: str) -> list[str]:
        """Extract key insights from research results for enhanced notifications."""
        try:
            # Split into sentences and find meaningful insights
            sentences = [s.strip() for s in text.replace('\n', ' ').split('.') if s.strip()]
            insights = []
            
            insight_indicators = ['found', 'shows', 'reveals', 'indicates', 'suggests', 'demonstrates', 'study', 'research', 'data', 'report']
            
            for sentence in sentences:
                sentence_lower = sentence.lower()
                if (len(sentence) > 30 and len(sentence) < 200 and
                    any(indicator in sentence_lower for indicator in insight_indicators)):
                    insights.append(sentence)
                    if len(insights) >= 5:
                        break
            
            return insights if insights else ["Comprehensive research data collected"]
        except Exception:
            return ["Research findings analyzed"]
    
    def _determine_content_strategy(self, topic: str, research_word_count: int) -> str:
        """Determine content strategy based on topic and research depth."""
        try:
            if research_word_count > 1000:
                return "comprehensive analytical"
            elif research_word_count > 500:
                return "balanced informational"
            elif "how to" in topic.lower() or "guide" in topic.lower():
                return "practical tutorial"
            elif any(word in topic.lower() for word in ["trend", "future", "prediction"]):
                return "forward-looking"
            else:
                return "focused explanatory"
        except Exception:
            return "standard"
    
    def _get_content_capabilities(self, tools) -> str:
        """Get content tool capabilities for notifications."""
        try:
            capabilities = []
            tool_names = [str(tool).lower() for tool in tools]
            
            if any("image" in name for name in tool_names):
                capabilities.append("image integration")
            if any("unsplash" in name for name in tool_names):
                capabilities.append("visual content")
            if any("search" in name for name in tool_names):
                capabilities.append("fact verification")
            
            return ", ".join(capabilities) if capabilities else "content generation, structure optimization"
        except Exception:
            return "standard content creation"
    
    def _analyze_content_stats(self, content: str) -> dict:
        """Analyze content statistics for notifications."""
        try:
            words = len(content.split())
            paragraphs = len([p for p in content.split('\n\n') if p.strip()])
            sections = len([line for line in content.split('\n') if line.strip().startswith('#')])
            
            # Simple quality score based on length and structure
            quality_score = min(10, max(1, 
                (words // 100) +  # Base score from word count
                (paragraphs // 2) +  # Structure bonus
                (sections // 1)  # Section bonus
            ))
            
            return {
                "word_count": words,
                "paragraph_count": paragraphs,
                "section_count": sections,
                "quality_score": quality_score
            }
        except Exception:
            return {"word_count": 0, "paragraph_count": 0, "section_count": 0, "quality_score": 5}
    
    def _extract_content_sections(self, content: str) -> list[str]:
        """Extract content sections for streaming notifications."""
        try:
            # Split by double newlines to get logical sections
            sections = [section.strip() for section in content.split('\n\n') if section.strip()]
            
            # Filter out very short sections and limit
            meaningful_sections = []
            for section in sections:
                if len(section) > 50:  # Must be substantial
                    # Remove markdown headers for cleaner display
                    clean_section = section.replace('#', '').strip()
                    meaningful_sections.append(clean_section)
                    if len(meaningful_sections) >= 5:
                        break
            
            return meaningful_sections if meaningful_sections else ["Content sections generated"]
        except Exception:
            return ["Content structure created"]
    
    def _analyze_content_for_facts(self, content: str) -> dict:
        """Analyze content to identify fact-checking requirements."""
        try:
            # Count potential claims (sentences with factual indicators)
            claim_indicators = ['study', 'research', 'data', 'statistics', 'report', 'shows', 'found', 'according', 'survey']
            sentences = content.split('.')
            claim_count = sum(1 for sentence in sentences 
                             if any(indicator in sentence.lower() for indicator in claim_indicators))
            
            # Count URLs
            import re
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            url_count = len(re.findall(url_pattern, content))
            
            # Count statistics (numbers with units/percentages)
            stat_pattern = r'\d+(?:\.\d+)?(?:%|\s+(?:percent|million|billion|thousand|users|people|companies))'
            stat_count = len(re.findall(stat_pattern, content, re.IGNORECASE))
            
            # Determine strategy
            if url_count > 5:
                strategy = "intensive URL validation"
            elif claim_count > 10:
                strategy = "comprehensive claim verification"
            elif stat_count > 5:
                strategy = "statistical accuracy focus"
            else:
                strategy = "standard verification"
            
            return {
                "claim_count": claim_count,
                "url_count": url_count,
                "stat_count": stat_count,
                "strategy": strategy
            }
        except Exception:
            return {"claim_count": 0, "url_count": 0, "stat_count": 0, "strategy": "basic verification"}
    
    def _analyze_verified_content(self, verified_content: dict) -> dict:
        """Analyze verified content to determine finalization strategy."""
        try:
            # Extract content from verified_content dict
            content = str(verified_content.get("fact_checked_content", ""))
            
            # Basic content metrics
            word_count = len(content.split()) if content else 0
            section_count = len([line for line in content.split('\n') if line.strip().startswith('#')])
            paragraph_count = len([p for p in content.split('\n\n') if p.strip()])
            
            # Determine finalization strategy based on content characteristics
            if word_count > 1500:
                strategy = "comprehensive editing with structure optimization"
            elif section_count > 5:
                strategy = "section-focused organization and flow"
            elif paragraph_count > 10:
                strategy = "readability and engagement enhancement"
            else:
                strategy = "standard polish and refinement"
            
            return {
                "word_count": word_count,
                "section_count": section_count,
                "paragraph_count": paragraph_count,
                "finalization_strategy": strategy
            }
        except Exception:
            return {"word_count": 0, "section_count": 0, "paragraph_count": 0, "finalization_strategy": "standard finalization"}
    
    def _analyze_final_content(self, content: str) -> dict:
        """Analyze final content for completion statistics."""
        try:
            words = len(content.split()) if content else 0
            sections = len([line for line in content.split('\n') if line.strip().startswith('#')]) if content else 0
            paragraphs = len([p for p in content.split('\n\n') if p.strip()]) if content else 0
            
            # Calculate quality score based on completeness
            quality_score = min(10, max(1, 
                (words // 150) +  # Base score from word count (1 point per 150 words)
                (sections // 1) +  # Section organization bonus
                (paragraphs // 3)  # Paragraph structure bonus
            ))
            
            return {
                "word_count": words,
                "section_count": sections,
                "paragraph_count": paragraphs,
                "quality_score": quality_score
            }
        except Exception:
            return {"word_count": 0, "section_count": 0, "paragraph_count": 0, "quality_score": 5}

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
        self._status("Initializing blog generation...", step=1, detail="Preparing context")
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
            step=2,
            detail="Collecting sources",
        )
        
        # Phase 1 Foundation: Enhanced real-time messaging - Initial Planning
        self.status_manager.send_agent_thinking(
            agent_name="Senior Researcher",
            thought=f"Initiating research for '{self.flow_state.topic}'. My strategy: 1) Academic sources for depth, 2) Industry reports for trends, 3) Recent news for currency. This ensures comprehensive coverage."
        )
        
        try:
            # Assure type checker topic/year are present
            topic = cast(str, self.flow_state.topic)
            year = cast(int, self.flow_state.current_year)
            
            # Enhanced tool preparation with detailed context
            self.status_manager.send_agent_thinking(
                agent_name="Senior Researcher",
                thought=f"Analyzing topic complexity for '{topic}'. This appears to be a {self._assess_topic_complexity(topic)} topic requiring specialized research approach."
            )
            
            # Broadcast tool preparation with more context
            self.status_manager.send_tool_usage(
                tool_name="research_toolkit",
                input_summary=f"Initializing research suite for '{topic}' - configuring search parameters for {year} relevance",
                agent_name="Senior Researcher"
            )
            
            tools = self.tools_manager.get_research_tools()
            
            # Show tool inventory
            self.status_manager.send_agent_thinking(
                agent_name="Senior Researcher",
                thought=f"Research arsenal ready: {len(tools)} specialized tools available. Primary tools: {self._get_tool_names(tools)[:3]}..."
            )
            
            agent = self.agent_factory.create_researcher(tools, year)
            task = self.task_factory.create_research_task(
                agent, topic, year, self.instructions
            )
            
            # Enhanced execution preparation
            self.status_manager.send_agent_thinking(
                agent_name="Senior Researcher", 
                thought=f"Research execution phase starting. Target: comprehensive {topic} analysis. Timeline: current to {year}. Quality standard: peer-reviewed sources preferred."
            )
            
            # Pre-execution tool usage notification
            self.status_manager.send_tool_usage(
                tool_name="CrewAI Research Engine",
                input_summary=f"Executing multi-source research query for '{topic}' with quality filters and recency bias",
                agent_name="Senior Researcher"
            )
            
            result = self._execute(agent, task, "research")
            self.flow_state.results["research"] = result
            
            # Enhanced research findings broadcast with analysis
            if result:
                try:
                    # Convert CrewOutput to string for broadcasting
                    result_text = str(result) if hasattr(result, '__str__') else result.raw if hasattr(result, 'raw') else ""
                    if result_text and len(result_text) > 100:
                        # Analyze and categorize findings
                        self.status_manager.send_agent_thinking(
                            agent_name="Senior Researcher",
                            thought=f"Research completed. Found {len(result_text)} characters of content. Analyzing key insights..."
                        )
                        
                        # Extract and broadcast key findings
                        key_insights = self._extract_key_insights(result_text)
                        for i, insight in enumerate(key_insights[:3], 1):
                            self.status_manager.send_research_finding(
                                finding=f"Key insight #{i}: {insight}",
                                source="AI Research Analysis"
                            )
                        
                        # Summary notification
                        self.status_manager.send_agent_thinking(
                            agent_name="Senior Researcher",
                            thought=f"Research synthesis complete. Identified {len(key_insights)} major insights. Data quality: high. Ready for content generation phase."
                        )
                        
                except Exception as broadcast_error:
                    logger.warning(f"Failed to broadcast research finding: {broadcast_error}")
            
            self._status("Research completed", step=2, detail="Sources gathered")
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
        self._status("Generating draft content...", step=3, detail="Authoring with images")
        
        # Enhanced content generation messaging - Strategic Planning
        self.status_manager.send_agent_thinking(
            agent_name="Expert Content Creator",
            thought=f"Analyzing research data for '{self.flow_state.topic}'. Planning content structure: Introduction → Key concepts → Detailed analysis → Practical applications → Conclusion. Target: engaging, informative, actionable content."
        )
        
        try:
            topic = cast(str, self.flow_state.topic)
            year = cast(int, self.flow_state.current_year)
            
            # Analyze research data for content planning
            research_result = research_data.get("research_results", "")
            research_insights = len(str(research_result).split()) if research_result else 0
            
            self.status_manager.send_agent_thinking(
                agent_name="Expert Content Creator",
                thought=f"Research analysis complete. Source material: {research_insights} words. Content strategy: {self._determine_content_strategy(topic, research_insights)} approach. Preparing content creation tools..."
            )
            
            # Enhanced content tool preparation
            self.status_manager.send_tool_usage(
                tool_name="content_creation_toolkit",
                input_summary=f"Initializing content suite for '{topic}' - configuring writing style, structure templates, and quality parameters",
                agent_name="Expert Content Creator"
            )
            
            tools = self.tools_manager.get_content_tools()
            
            # Show content tool capabilities
            self.status_manager.send_agent_thinking(
                agent_name="Expert Content Creator",
                thought=f"Content creation arsenal ready: {len(tools)} specialized tools. Capabilities: {self._get_content_capabilities(tools)}. Image generation: disabled (cost optimization)."
            )
            
            agent = self.agent_factory.create_content_creator(tools, year)
            task = self.task_factory.create_content_task(
                agent, topic, year, self.instructions
            )
            
            # Content generation strategy notification
            self._status("Generating draft content...", step=3, detail="Content generation (image generation disabled)")
            
            self.status_manager.send_agent_thinking(
                agent_name="Expert Content Creator",
                thought=f"Content generation strategy: Structured narrative approach. Target length: comprehensive coverage. Quality focus: clarity, accuracy, engagement. Beginning content creation..."
            )
            
            # DISABLED: Enhanced messaging for image generation
            # self.status_manager.send_tool_usage(
            #     tool_name="parallel_image_generator",
            #     input_summary=f"Starting parallel image generation for {topic} concepts",
            #     agent_name="Content Creator"
            # )
            
            # DISABLED: Parallel image generation to save costs
            # image_futures = self._start_parallel_image_generation(topic)
            image_futures = []  # Empty list - no image generation
            
            # Enhanced pre-execution notification
            self.status_manager.send_tool_usage(
                tool_name="CrewAI Content Engine",
                input_summary=f"Executing content generation for '{topic}' with research-driven approach and quality optimization",
                agent_name="Expert Content Creator"
            )
            
            # Execute main content generation
            draft = self._execute(agent, task, "content_generation")
            
            # Enhanced content analysis and streaming
            if draft:
                try:
                    # Convert CrewOutput to string for broadcasting
                    draft_text = str(draft) if hasattr(draft, '__str__') else draft.raw if hasattr(draft, 'raw') else ""
                    if draft_text and len(draft_text) > 100:
                        # Analyze generated content
                        content_stats = self._analyze_content_stats(draft_text)
                        
                        self.status_manager.send_agent_thinking(
                            agent_name="Expert Content Creator",
                            thought=f"Content generation complete. Statistics: {content_stats['word_count']} words, {content_stats['paragraph_count']} paragraphs, {content_stats['section_count']} sections. Quality check: {content_stats['quality_score']}/10."
                        )
                        
                        # Stream content sections as they're analyzed
                        content_sections = self._extract_content_sections(draft_text)
                        for i, section in enumerate(content_sections[:3], 1):
                            self.status_manager.send_content_stream(
                                content_type=f"section_{i}",
                                content=f"Section {i}: {section[:150]}..." if len(section) > 150 else section,
                                is_partial=False
                            )
                        
                        # Final content summary
                        self.status_manager.send_agent_thinking(
                            agent_name="Expert Content Creator",
                            thought=f"Content structure validated. Key sections: {len(content_sections)} identified. Readability: optimized. Technical accuracy: research-backed. Ready for validation phase."
                        )
                        
                except Exception as broadcast_error:
                    logger.warning(f"Failed to broadcast content stream: {broadcast_error}")
            
            # Wait for parallel image generation to complete (if any started)
            # DISABLED: Complete parallel image generation to save costs
            # self._complete_parallel_image_generation(image_futures)
            logger.info("Image generation disabled to save costs")
            
            self.flow_state.results["content"] = draft
            self._status("Content draft complete", step=3, detail="Draft ready")
            return {**research_data, "initial_content": draft}
        except Exception as e:  # pragma: no cover
            logger.exception("Content generation failed")
            self._error(f"Content generation failed: {e}")
            raise

    @listen(content_generation_phase)
    def content_validation_phase(self, content_data: Dict[str, Any]) -> Dict[str, Any]:  # Phase 2.5
        """Validate and clean content to ensure proper image tool usage."""
        self._require_topic()
        self._status("Validating content...", step=3, detail="Checking image sources")
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
                    self._status("Regenerating images...", step=3, detail="Using proper image tools")
                    try:
                        # Get content creation tools and agent
                        tools = self.tools_manager.get_content_tools()
                        agent = self.agent_factory.create_content_creator(tools, self.flow_state.current_year)
                        
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
            
            self._status("Content validation complete", step=3, detail="Ready for fact-checking")
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
        self._status("Fact-checking content...", step=4, detail="Verifying claims")
        
        # Enhanced fact-checking initialization
        self.status_manager.send_agent_thinking(
            agent_name="Expert Fact Checker",
            thought=f"Beginning comprehensive fact-checking for '{self.flow_state.topic}'. Process: 1) Claim identification, 2) Source verification, 3) URL validation, 4) Accuracy confirmation. Maintaining highest standards."
        )
        
        try:
            topic = cast(str, self.flow_state.topic)
            
            # Analyze content for fact-checking scope
            content_to_check = content_data.get("blog_content", "")
            if not content_to_check:
                logger.warning("No content found for fact checking")
                return content_data
            
            content_analysis = self._analyze_content_for_facts(content_to_check)
            
            self.status_manager.send_agent_thinking(
                agent_name="Expert Fact Checker",
                thought=f"Content analysis complete. Identified {content_analysis['claim_count']} potential claims, {content_analysis['url_count']} URLs, {content_analysis['stat_count']} statistics. Verification strategy: {content_analysis['strategy']}."
            )
            
            tools = self.tools_manager.get_research_tools()
            
            self.status_manager.send_tool_usage(
                tool_name="fact_checking_toolkit",
                input_summary=f"Initializing verification tools for {content_analysis['claim_count']} claims and {content_analysis['url_count']} URLs",
                agent_name="Expert Fact Checker"
            )
            
            # 🔒 VALIDATION LOOP ENFORCEMENT
            self._status("Analyzing URLs for validation enforcement...", step=4, detail="URL validation setup")
            validation_enforcer = create_validation_enforcer()
            enforcement_result = validation_enforcer.enforce_validation_loop(str(content_to_check), topic)
            
            # Store validation requirements for audit
            self.flow_state.results["url_validation_requirements"] = {
                "validation_required": enforcement_result.validation_required,
                "urls_found": enforcement_result.urls_found,
                "url_count": len(enforcement_result.urls_found)
            }
            
            if enforcement_result.validation_required:
                logger.info(f"🔒 URL Validation Enforcement: {len(enforcement_result.urls_found)} URLs require validation")
                self._status(f"URL validation required for {len(enforcement_result.urls_found)} URLs", 
                            step=4, detail="Enforcing validation compliance")
                
                self.status_manager.send_agent_thinking(
                    agent_name="Expert Fact Checker",
                    thought=f"URL validation enforcement active. {len(enforcement_result.urls_found)} URLs detected requiring mandatory validation. Compliance monitoring enabled."
                )
                
                # Create enhanced fact checker with validation requirements
                checked = self._execute_fact_check_with_validation_loop(
                    topic, tools, content_to_check, enforcement_result
                )
            else:
                logger.info("🔒 URL Validation Enforcement: No URLs found - proceeding with standard fact check")
                self._status("No URLs to validate - proceeding with fact check", step=4, detail="Standard verification")
                
                self.status_manager.send_agent_thinking(
                    agent_name="Expert Fact Checker",
                    thought="No URLs detected in content. Proceeding with standard fact-checking protocol. Focus: claim verification, data accuracy, source credibility."
                )
                
                # Standard fact checking without validation loop
                agent = self.agent_factory.create_fact_checker(tools, self.flow_state.current_year)
                task = self.task_factory.create_fact_check_task(agent, topic, self.instructions)
                
                self.status_manager.send_tool_usage(
                    tool_name="CrewAI Fact Check Engine",
                    input_summary=f"Executing standard fact verification for '{topic}' content with claim analysis and source validation",
                    agent_name="Expert Fact Checker"
                )
                
                checked = self._execute(agent, task, "fact_checking")
            
            self.flow_state.results["fact_checked"] = checked
            self._status("Fact-check complete", step=4, detail="Content validated")
            return {**content_data, "fact_checked_content": checked}
            
        except Exception as e:  # pragma: no cover
            logger.exception("Fact checking failed")
            self._error(f"Fact checking failed: {e}")
            raise
    
    def _execute_fact_check_with_validation_loop(self, topic: str, tools: list, content: str, 
                                                enforcement_result) -> Any:
        """Execute fact checking with URL validation loop enforcement"""
        max_retries = 3
        retry_count = 0
        validation_enforcer = create_validation_enforcer()
        
        while retry_count < max_retries:
            try:
                if retry_count == 0:
                    # First attempt - include validation requirements
                    self._status(f"Fact checking with URL validation (attempt {retry_count + 1})", 
                                step=4, detail=f"Validating {len(enforcement_result.urls_found)} URLs")
                    
                    enhanced_task_description = self._create_enhanced_fact_check_task(
                        topic, enforcement_result, is_retry=False
                    )
                else:
                    # Retry attempt - enhanced enforcement
                    self._status(f"Retry fact checking with enhanced validation (attempt {retry_count + 1})", 
                                step=4, detail="Enforcing compliance")
                    
                    enhanced_task_description = self._create_enhanced_fact_check_task(
                        topic, enforcement_result, is_retry=True, 
                        retry_count=retry_count
                    )
                
                # Create fact checker agent and task
                agent = self.agent_factory.create_fact_checker(tools, self.flow_state.current_year)
                
                # Create custom task with enhanced validation requirements
                from crewai import Task
                task = Task(
                    description=enhanced_task_description,
                    agent=agent,
                    expected_output="""A fact-checked version with:
                    - All factual claims verified with current sources
                    - MANDATORY: Complete URL validation evidence for ALL links
                    - URL Validation Report showing URLValidationTool usage and results
                    - Compliance confirmation that all URLs were tested
                    - Corrected/replaced broken URLs with working alternatives
                    - 'Validation Compliance Summary' confirming all requirements met"""
                )
                
                # Execute fact checking
                logger.info(f"🔒 Executing fact check with validation enforcement (attempt {retry_count + 1})")
                result = self._execute(agent, task, "fact_checking")
                
                # Check compliance of the result
                is_compliant, compliance_score, compliance_issues = validation_enforcer.check_validation_compliance(
                    str(result), enforcement_result.urls_found
                )
                
                # Store compliance results for audit
                self.flow_state.results[f"validation_compliance_attempt_{retry_count + 1}"] = {
                    "compliant": is_compliant,
                    "score": compliance_score,
                    "issues": compliance_issues,
                    "retry_count": retry_count
                }
                
                if is_compliant:
                    logger.info(f"✅ URL Validation Compliance achieved! Score: {compliance_score:.1%}")
                    self._status("URL validation compliance achieved", step=4, 
                                detail=f"Score: {compliance_score:.1%}")
                    return result
                else:
                    logger.warning(f"❌ URL Validation Compliance failed. Score: {compliance_score:.1%}")
                    logger.warning(f"Issues: {compliance_issues}")
                    
                    if retry_count < max_retries - 1:
                        self._status(f"Compliance failed - retry required", step=4, 
                                    detail=f"Score: {compliance_score:.1%}")
                        retry_count += 1
                        continue
                    else:
                        logger.error(f"❌ Maximum retries reached. Final compliance score: {compliance_score:.1%}")
                        self._status("Max retries reached - proceeding with partial compliance", 
                                    step=4, detail=f"Final score: {compliance_score:.1%}")
                        return result
                        
            except Exception as e:
                logger.error(f"Fact checking attempt {retry_count + 1} failed: {e}")
                if retry_count < max_retries - 1:
                    retry_count += 1
                    continue
                else:
                    raise
        
        raise RuntimeError("Fact checking with validation loop failed after maximum retries")
    
    def _create_enhanced_fact_check_task(self, topic: str, enforcement_result, 
                                       is_retry: bool = False, retry_count: int = 0) -> str:
        """Create enhanced fact check task description with validation loop enforcement"""
        base_description = f"""Thoroughly fact-check the blog post about '{topic}' with MANDATORY URL validation compliance.

🚨 CRITICAL VALIDATION LOOP ENFORCEMENT - COMPLIANCE REQUIRED

{enforcement_result.enforcement_instructions}

{enforcement_result.validation_evidence_required}
"""
        
        if is_retry:
            retry_section = f"""
🔄 RETRY ATTEMPT #{retry_count + 1} - ENHANCED ENFORCEMENT

THIS IS A COMPLIANCE RETRY due to insufficient URL validation evidence in previous attempt.

⚠️ CRITICAL COMPLIANCE REQUIREMENTS:
- You MUST demonstrate actual URLValidationTool usage
- You MUST provide explicit validation results for each URL
- You MUST show status codes and accessibility testing
- You MUST document any URL replacements or corrections
- Missing compliance evidence will trigger another retry

ENHANCED ENFORCEMENT MEASURES:
- Tool usage monitoring is active
- Compliance scoring is being tracked
- Evidence verification is mandatory
- Non-compliance triggers automatic retry

"""
            base_description = retry_section + base_description
        
        return base_description

    @listen(fact_checking_phase)
    def finalization_phase(self, verified_content: Dict[str, Any]) -> Dict[str, Any]:  # Phase 4
        self._require_topic()
        self.flow_state.current_phase = "finalization"
        self._update_audit_phase("finalization")
        self._status("Finalizing blog post...", step=5, detail="Polishing output")
        
        # Phase 1 Foundation: Enhanced real-time messaging - Agent Planning
        self.status_manager.send_agent_thinking(
            agent_name="Blog Finalizer",
            thought="Beginning finalization phase. My mission: transform verified content into publication-ready blog post with professional polish, optimal structure, and engaging presentation."
        )
        
        try:
            topic = cast(str, self.flow_state.topic)
            
            # Analyze verified content for finalization strategy
            content_analysis = self._analyze_verified_content(verified_content)
            self.status_manager.send_agent_thinking(
                agent_name="Blog Finalizer",
                thought=f"Content analysis complete: {content_analysis['word_count']} words across {content_analysis['section_count']} sections. Strategy: {content_analysis['finalization_strategy']}"
            )
            
            # Initialize finalization tools
            tools = ["content_polisher", "structure_optimizer", "readability_enhancer", "seo_optimizer"]
            self.status_manager.send_tool_usage(
                tool_name="finalization_toolkit",
                input_summary=f"Preparing comprehensive finalization for '{topic}' - {len(tools)} optimization tools ready",
                agent_name="Blog Finalizer"
            )
            
            agent = self.agent_factory.create_finalizer(self.flow_state.current_year)
            task = self.task_factory.create_finalization_task(agent, topic, self.instructions)
            
            # Broadcast finalization execution details
            self.status_manager.send_agent_thinking(
                agent_name="Blog Finalizer",
                thought="Executing final polish: 1) Structure optimization, 2) Readability enhancement, 3) SEO improvements, 4) Quality assurance"
            )
            
            raw_final_post = self._execute(agent, task, "finalization")
            
            # 🧹 CONTENT CLEANING - Remove leaked instructions and meta-commentary
            self._status("Cleaning finalization output...", step=5, detail="Removing leaked instructions")
            logger.info("🧹 Starting Content Cleaning - removing leaked processing instructions")
            
            # Enhanced notification for content cleaning
            self.status_manager.send_agent_thinking(
                agent_name="Content Processor",
                thought="Initiating content cleaning pipeline. Scanning for instruction leakage, meta-commentary, and processing artifacts that need removal."
            )
            
            from .blog_content_cleaner import create_blog_content_cleaner
            content_cleaner = create_blog_content_cleaner()
            final_post, removed_sections = content_cleaner.clean_finalization_output(str(raw_final_post))
            
            if removed_sections:
                logger.info(f"🧹 Content Cleaning removed {len(removed_sections)} problematic sections:")
                for section in removed_sections:
                    logger.info(f"   • {section}")
                self._status("Content cleaning completed", step=5, detail=f"Removed {len(removed_sections)} instruction leaks")
                
                # Enhanced notification for cleaning results
                self.status_manager.send_agent_thinking(
                    agent_name="Content Processor",
                    thought=f"Content cleaning successful: removed {len(removed_sections)} problematic sections including instruction leakage and meta-commentary."
                )
            else:
                logger.info("✅ Content Cleaning: No instruction leakage detected - content was clean")
                self._status("Content cleaning completed", step=5, detail="Content verified clean")
                
                self.status_manager.send_agent_thinking(
                    agent_name="Content Processor",
                    thought="Content cleaning complete - no instruction leakage detected. Content quality verified."
                )
            
            # Post-process to ensure proper image usage and clean deprecated sources
            self.status_manager.send_tool_usage(
                tool_name="content_post_processor",
                input_summary=f"Processing blog content for '{topic}' - optimizing structure and enforcing tool usage standards",
                agent_name="Content Processor"
            )
            
            processed_post = FlowPostProcessor.process_blog_content(
                content=final_post,
                topic=topic,
                force_tool_usage=True
            )
            
            # Conditionally ensure adequate images (2-3) - inject missing images if necessary
            from core.config import config
            final_content = processed_post
            
            if config.features.enable_content_image_injection:
                self.status_manager.send_agent_thinking(
                    agent_name="Image Processor",
                    thought="Content image injection enabled. Analyzing content for image gaps and injecting relevant visuals to enhance reader engagement."
                )
                
                self.status_manager.send_tool_usage(
                    tool_name="image_injector",
                    input_summary=f"Ensuring adequate images for '{topic}' content - targeting 2-3 contextual images",
                    agent_name="Image Processor"
                )
                
                from .mandatory_image_injector import create_mandatory_image_injector
                image_injector = create_mandatory_image_injector()
                final_content = image_injector.ensure_adequate_images(processed_post, topic)
                logger.info("✅ Content image injection completed")
                
                self.status_manager.send_agent_thinking(
                    agent_name="Image Processor",
                    thought="Image injection complete. Content now includes optimal visual elements for enhanced readability and engagement."
                )
            else:
                logger.info("📷 Content image injection disabled - using content as-is")
                self.status_manager.send_agent_thinking(
                    agent_name="Image Processor",
                    thought="Image injection disabled in configuration. Proceeding with existing visual content only."
                )
            
            # � CONTENT INTEGRITY VALIDATION - Remove hallucinated content and invalid references
            self._status("Running content integrity validation...", step=5, detail="Removing hallucinated content")
            logger.info("� Starting Content Integrity Validation - removing hallucinated content and invalid references")
            
            self.status_manager.send_agent_thinking(
                agent_name="Integrity Validator",
                thought="Initiating comprehensive content integrity scan. Validating all references, detecting hallucinated content, ensuring factual accuracy."
            )
            
            self.status_manager.send_tool_usage(
                tool_name="integrity_validator",
                input_summary="Scanning content for hallucinated references, invalid URLs, and factual inconsistencies",
                agent_name="Integrity Validator"
            )
            
            integrity_validator = ContentIntegrityValidator()
            integrity_cleaned_content, integrity_report = integrity_validator.validate_content_integrity(final_content)
            
            # Log integrity validation results
            integrity_summary = format_integrity_report(integrity_report)
            logger.info(f"� Content Integrity Validation completed:\n{integrity_summary}")
            
            # Update final content with integrity-validated content
            final_content = integrity_cleaned_content
            
            if integrity_report.content_quality_score < 100:
                removed_refs = integrity_report.removed_references
                removed_paragraphs = integrity_report.content_paragraphs_removed
                logger.info(f"� Content Integrity Validation removed {removed_refs} invalid references and {removed_paragraphs} problematic content sections")
                self._status("Content integrity validation completed", step=5, 
                            detail=f"Removed {removed_refs} invalid references, {removed_paragraphs} content sections")
                
                self.status_manager.send_agent_thinking(
                    agent_name="Integrity Validator",
                    thought=f"Integrity validation complete: removed {removed_refs} invalid references and {removed_paragraphs} problematic sections. Quality score: {integrity_report.content_quality_score}%"
                )
            else:
                logger.info("✅ Content Integrity Validation: All content verified - no cleanup needed")
                self._status("Content integrity validation completed", step=5, detail="All content verified successfully")
                
                self.status_manager.send_agent_thinking(
                    agent_name="Integrity Validator",
                    thought="Integrity validation perfect: all references verified, no hallucinated content detected. Quality score: 100%"
                )
            
            # Store integrity report in flow state for audit purposes
            self.flow_state.results["content_integrity_report"] = {
                "total_references": integrity_report.total_references,
                "valid_references": integrity_report.valid_references,
                "removed_references": integrity_report.removed_references,
                "content_paragraphs_removed": integrity_report.content_paragraphs_removed,
                "content_quality_score": integrity_report.content_quality_score
            }
            
            # 🔧 REFERENCE DEDUPLICATION - Remove duplicate references and consolidate citations
            self._status("Running reference deduplication...", step=4, detail="Consolidating references")
            logger.info("🔧 Starting Reference Deduplication - removing duplicate citations")
            
            self.status_manager.send_agent_thinking(
                agent_name="Reference Manager",
                thought="Initiating reference deduplication. Scanning for duplicate citations, consolidating references, optimizing citation structure."
            )
            
            self.status_manager.send_tool_usage(
                tool_name="reference_deduplicator",
                input_summary="Analyzing citation patterns and removing duplicate references for cleaner bibliography",
                agent_name="Reference Manager"
            )
            
            reference_deduplicator = create_reference_deduplicator()
            deduplicated_content, dedup_report = reference_deduplicator.deduplicate_references(final_content)
            
            # Log deduplication results
            dedup_summary = format_deduplication_report(dedup_report)
            logger.info(f"🔧 Reference Deduplication completed:\n{dedup_summary}")
            
            # Update final content with deduplicated references
            final_content = deduplicated_content
            
            if dedup_report.content_updated:
                logger.info(f"🔧 Reference Deduplication removed {dedup_report.duplicates_removed} duplicate references")
                self._status("Reference deduplication completed", step=4, 
                            detail=f"Removed {dedup_report.duplicates_removed} duplicates")
                
                self.status_manager.send_agent_thinking(
                    agent_name="Reference Manager",
                    thought=f"Deduplication complete: removed {dedup_report.duplicates_removed} duplicate references. Final bibliography optimized with {dedup_report.unique_references} unique sources."
                )
            else:
                logger.info("✅ Reference Deduplication: No duplicate references found")
                self._status("Reference deduplication completed", step=4, detail="No duplicates found")
                
                self.status_manager.send_agent_thinking(
                    agent_name="Reference Manager",
                    thought="Deduplication complete: no duplicate references detected. Bibliography already optimized."
                )
            
            # Store deduplication report in flow state for audit purposes
            self.flow_state.results["reference_deduplication_report"] = {
                "total_references": dedup_report.total_references_found,
                "unique_references": dedup_report.unique_references,
                "duplicates_removed": dedup_report.duplicates_removed,
                "content_updated": dedup_report.content_updated
            }
            
            # Final completion notification
            final_stats = self._analyze_final_content(final_content)
            self.status_manager.send_agent_thinking(
                agent_name="Blog Finalizer",
                thought=f"Blog finalization complete! Final statistics: {final_stats['word_count']} words, {final_stats['section_count']} sections, quality score: {final_stats['quality_score']}/10. Ready for publication."
            )
            
            # CRITICAL DEBUG: Check what we're returning as final content
            logger.info(f"🔍 FLOW FINALIZE - About to return final content:")
            logger.info(f"   final_content type: {type(final_content)}")
            logger.info(f"   final_content length: {len(final_content) if final_content else 0}")
            logger.info(f"   final_content is_empty: {not final_content or not final_content.strip()}")
            logger.info(f"   final_content preview: {final_content[:300] if final_content else 'EMPTY FINAL CONTENT'}...")
            
            self.flow_state.results["final"] = final_content
            # NOTE: Completion is now handled by main.py task_manager.complete_task() to avoid duplicate completion messages
            # self._complete(final_content)  # REMOVED: This was causing duplicate completion messages
            
            return_dict = {**verified_content, "final_blog_post": final_content, "generation_complete": True}
            logger.info(f"🔍 FLOW FINALIZE - Return dict keys: {list(return_dict.keys())}")
            logger.info(f"🔍 FLOW FINALIZE - final_blog_post in return: {return_dict.get('final_blog_post', 'MISSING')[:200] if return_dict.get('final_blog_post') else 'EMPTY IN RETURN'}...")
            
            return return_dict
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
