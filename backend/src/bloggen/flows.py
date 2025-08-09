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
from core.llm_interceptor import _register_audit_tracker
from core.config import config  # reuse existing config for model + key

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

    def _execute(self, agent, task) -> Any:
        crew = Crew(agents=[agent], tasks=[task], verbose=True)
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
            result = self._execute(agent, task)
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
            draft = self._execute(agent, task)
            self.flow_state.results["content"] = draft
            self._status("Content draft complete", step=2, detail="Draft ready")
            return {**research_data, "initial_content": draft}
        except Exception as e:  # pragma: no cover
            logger.exception("Content generation failed")
            self._error(f"Content generation failed: {e}")
            raise

    @listen(content_generation_phase)
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
            checked = self._execute(agent, task)
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
            final_post = self._execute(agent, task)
            self.flow_state.results["final"] = final_post
            self._complete(str(final_post))
            return {**verified_content, "final_blog_post": final_post, "generation_complete": True}
        except Exception as e:  # pragma: no cover
            logger.exception("Finalization failed")
            self._error(f"Finalization failed: {e}")
            raise

__all__ = ["BlogGenerationFlow"]
