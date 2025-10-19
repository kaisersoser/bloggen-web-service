"""CrewAI event listeners that bridge structured events to status updates.

Introduced in Phase 2 to replace stdout parsing with native CrewAI events.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Set

from crewai.events.base_event_listener import BaseEventListener
from crewai.events.types.llm_events import LLMCallFailedEvent
from crewai.events.types.reasoning_events import (
    AgentReasoningCompletedEvent,
    AgentReasoningFailedEvent,
    AgentReasoningStartedEvent,
)
from crewai.events.types.task_events import (
    TaskCompletedEvent,
    TaskFailedEvent,
    TaskStartedEvent,
)
from crewai.events.types.tool_usage_events import (
    ToolUsageErrorEvent,
    ToolUsageFinishedEvent,
    ToolUsageStartedEvent,
)

from .status_manager import StatusUpdateManager

logger = logging.getLogger(__name__)


@dataclass
class RunContext:
    """Live execution metadata for a crew run."""

    crew_id: str
    phase_name: str
    status_manager: StatusUpdateManager
    task_ids: Set[str] = field(default_factory=set)


class BlogEventListener(BaseEventListener):
    """Singleton event listener that mirrors CrewAI events to SSE updates."""

    _instance: Optional["BlogEventListener"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):  # pragma: no cover - runtime side-effect wiring
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self._contexts: Dict[str, RunContext] = {}
        self._task_index: Dict[str, str] = {}
        super().__init__()
        logger.info(
            "BlogEventListener initialized and registered with CrewAI event bus"
        )

    # ------------------------------------------------------------------
    # Public API for managing live runs
    # ------------------------------------------------------------------
    def register_run(
        self, crew, phase_name: str, status_manager: StatusUpdateManager
    ) -> None:
        """Register a crew execution so event callbacks can emit updates."""
        crew_id = str(getattr(crew, "id", ""))
        if not crew_id:
            logger.warning("Unable to register crew run without crew id")
            return

        task_ids = {
            str(getattr(task, "id", ""))
            for task in getattr(crew, "tasks", [])
            if getattr(task, "id", None)
        }
        self._contexts[crew_id] = RunContext(
            crew_id=crew_id,
            phase_name=phase_name,
            status_manager=status_manager,
            task_ids=task_ids,
        )

        for task_id in task_ids:
            self._task_index[task_id] = crew_id

        logger.debug("Registered crew run %s with %d tasks", crew_id, len(task_ids))

    def unregister_run(self, crew) -> None:
        crew_id = str(getattr(crew, "id", ""))
        context = self._contexts.pop(crew_id, None)
        if not context:
            return

        for task_id in context.task_ids:
            self._task_index.pop(task_id, None)
        logger.debug("Unregistered crew run %s", crew_id)

    # ------------------------------------------------------------------
    # BaseEventListener implementation
    # ------------------------------------------------------------------
    def setup_listeners(self, crewai_event_bus):  # pragma: no cover - event wiring
        @crewai_event_bus.on(TaskStartedEvent)
        def on_task_started(source, event: TaskStartedEvent):
            self._with_context(source, event, self._handle_task_started)

        @crewai_event_bus.on(TaskCompletedEvent)
        def on_task_completed(source, event: TaskCompletedEvent):
            self._with_context(source, event, self._handle_task_completed)

        @crewai_event_bus.on(TaskFailedEvent)
        def on_task_failed(source, event: TaskFailedEvent):
            self._with_context(source, event, self._handle_task_failed)

        @crewai_event_bus.on(AgentReasoningStartedEvent)
        def on_reasoning_started(source, event: AgentReasoningStartedEvent):
            self._with_context(source, event, self._handle_agent_reasoning_started)

        @crewai_event_bus.on(AgentReasoningCompletedEvent)
        def on_reasoning_completed(source, event: AgentReasoningCompletedEvent):
            self._with_context(source, event, self._handle_agent_reasoning_completed)

        @crewai_event_bus.on(AgentReasoningFailedEvent)
        def on_reasoning_failed(source, event: AgentReasoningFailedEvent):
            self._with_context(source, event, self._handle_agent_reasoning_failed)

        @crewai_event_bus.on(ToolUsageStartedEvent)
        def on_tool_started(source, event: ToolUsageStartedEvent):
            self._with_context(source, event, self._handle_tool_started)

        @crewai_event_bus.on(ToolUsageFinishedEvent)
        def on_tool_finished(source, event: ToolUsageFinishedEvent):
            self._with_context(source, event, self._handle_tool_finished)

        @crewai_event_bus.on(ToolUsageErrorEvent)
        def on_tool_error(source, event: ToolUsageErrorEvent):
            self._with_context(source, event, self._handle_tool_error)

        @crewai_event_bus.on(LLMCallFailedEvent)
        def on_llm_failed(source, event: LLMCallFailedEvent):
            self._with_context(source, event, self._handle_llm_failed)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _handle_task_started(
        self, context: RunContext, source, event: TaskStartedEvent
    ) -> None:
        """
        Handle TaskStartedEvent from CrewAI.
        Defensive implementation - errors here should never break workflow.
        """
        try:
            # Try to get a meaningful task identifier
            task_name = getattr(source, 'name', None)
            if not task_name:
                task_name = getattr(source, 'description', 'task')
            
            context.status_manager.send_status_update(
                message=f"{context.phase_name.title()} phase in progress",
                step=self._phase_step(context.phase_name),
                detail=f"Task '{task_name}' started",
            )
            
        except AttributeError as e:
            # Expected error if CrewAI changes event/source structure
            logger.debug(f"Event structure changed in task started: {e}")
            
        except Exception as e:
            # Unexpected errors should be logged but not propagated
            logger.warning(f"Unexpected error in task started handler: {e}", exc_info=True)

    def _handle_task_completed(
        self, context: RunContext, source, event: TaskCompletedEvent
    ) -> None:
        """
        Handle TaskCompletedEvent from CrewAI.
        Defensive implementation - errors here should never break workflow.
        """
        try:
            # Try to get agent name safely
            agent_name = getattr(
                getattr(source, "agent", None), 
                "role", 
                context.phase_name.title() + " Agent"
            )
            
            context.status_manager.send_agent_thinking(
                agent_name=agent_name,
                thought="Task completed successfully. Awaiting next steps.",
            )
            
        except AttributeError as e:
            # Expected error if CrewAI changes event/source structure
            logger.debug(f"Event structure changed in task completed: {e}")
            
        except Exception as e:
            # Unexpected errors should be logged but not propagated
            logger.warning(f"Unexpected error in task completed handler: {e}", exc_info=True)

    def _handle_task_failed(
        self, context: RunContext, source, event: TaskFailedEvent
    ) -> None:
        """
        Handle TaskFailedEvent from CrewAI.
        Defensive implementation - errors here should never break workflow.
        """
        try:
            error_msg = getattr(event, 'error', 'Unknown error')
            context.status_manager.send_error_update(
                f"{context.phase_name.title()} task failed: {error_msg}",
            )
            
        except AttributeError as e:
            # Expected error if CrewAI changes event/source structure
            logger.debug(f"Event structure changed in task failed: {e}")
            try:
                # Fallback to generic error message
                context.status_manager.send_error_update(
                    f"{context.phase_name.title()} task failed",
                )
            except:
                pass  # Silently fail if even basic update fails
            
        except Exception as e:
            # Unexpected errors should be logged but not propagated
            logger.warning(f"Unexpected error in task failed handler: {e}", exc_info=True)

    def _handle_agent_reasoning_started(
        self, context: RunContext, source, event: AgentReasoningStartedEvent
    ) -> None:
        agent_name = event.agent_role or getattr(source, "role", "Agent")
        context.status_manager.send_agent_thinking(agent_name, "Evaluating approach...")

    def _handle_agent_reasoning_completed(
        self, context: RunContext, source, event: AgentReasoningCompletedEvent
    ) -> None:
        agent_name = event.agent_role or getattr(source, "role", "Agent")
        summary = event.plan if getattr(event, "plan", None) else "Reasoning complete."
        if summary and len(summary) > 240:
            summary = summary[:237] + "..."
        context.status_manager.send_agent_thinking(agent_name, summary)

    def _handle_agent_reasoning_failed(
        self, context: RunContext, source, event: AgentReasoningFailedEvent
    ) -> None:
        agent_name = event.agent_role or getattr(source, "role", "Agent")
        context.status_manager.send_agent_thinking(
            agent_name, f"Encountered an issue: {event.error}"
        )

    def _handle_tool_started(
        self, context: RunContext, source, event: ToolUsageStartedEvent
    ) -> None:
        agent_name = event.agent_role or getattr(source, "role", "Agent")
        args_preview = self._safe_preview(event.tool_args)
        context.status_manager.send_tool_usage(
            event.tool_name, args_preview, agent_name
        )

    def _handle_tool_finished(
        self, context: RunContext, source, event: ToolUsageFinishedEvent
    ) -> None:
        agent_name = event.agent_role or getattr(source, "role", "Agent")
        context.status_manager.send_agent_thinking(
            agent_name, f"{event.tool_name} returned results."
        )

    def _handle_tool_error(
        self, context: RunContext, source, event: ToolUsageErrorEvent
    ) -> None:
        agent_name = event.agent_role or getattr(source, "role", "Agent")
        context.status_manager.send_agent_thinking(
            agent_name, f"{event.tool_name} encountered an error: {event.error}"
        )

    def _handle_llm_failed(
        self, context: RunContext, source, event: LLMCallFailedEvent
    ) -> None:
        agent_name = getattr(
            getattr(source, "agent", None),
            "role",
            context.phase_name.title() + " Agent",
        )
        context.status_manager.send_agent_thinking(
            agent_name, f"LLM call failed: {event.error}"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _with_context(
        self, source: Any, event: Any, handler: Callable[[RunContext, Any, Any], None]
    ) -> None:
        """
        Wrap handler with context - callbacks must never break workflow.
        Enhanced error handling distinguishes between expected and unexpected errors.
        """
        context = self._resolve_context(source, event)
        if not context:
            return
        try:
            handler(context, source, event)
        except AttributeError as exc:
            # Common issue with CrewAI event structure changes
            logger.warning(
                f"Event structure mismatch in {handler.__name__} "
                f"for {type(event).__name__}: {exc}"
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            # Catch all other unexpected errors
            logger.error(
                f"Unexpected error in {handler.__name__} "
                f"for {type(event).__name__}: {exc}",
                exc_info=True
            )

    def _resolve_context(self, source: Any, event: Any) -> Optional[RunContext]:
        crew_id: Optional[str] = None

        if hasattr(source, "crew") and getattr(source, "crew", None) is not None:
            crew_id = str(source.crew.id)
        elif (
            hasattr(source, "agent")
            and getattr(source, "agent", None) is not None
            and getattr(source.agent, "crew", None) is not None
        ):
            crew_id = str(source.agent.crew.id)
        elif hasattr(source, "id") and str(source.id) in self._contexts:
            crew_id = str(source.id)
        elif (
            hasattr(event, "task_id")
            and event.task_id
            and event.task_id in self._task_index
        ):
            crew_id = self._task_index[event.task_id]
        elif (
            hasattr(event, "from_task")
            and getattr(event, "from_task", None) is not None
        ):
            task = getattr(event, "from_task")
            task_id = str(getattr(task, "id", ""))
            crew_id = self._task_index.get(task_id)

        if not crew_id:
            return None
        return self._contexts.get(crew_id)

    @staticmethod
    def _safe_preview(value: Any, max_length: int = 160) -> str:
        if value is None:
            return ""
        preview = str(value)
        if len(preview) > max_length:
            preview = preview[: max_length - 3] + "..."
        return preview

    @staticmethod
    def _phase_step(phase_name: str) -> int:
        mapping = {
            "initialization": 1,
            "research": 2,
            "content_generation": 3,
            "content_validation": 3,
            "image_enhancement": 3,
            "fact_checking": 4,
            "finalization": 5,
        }
        return mapping.get(phase_name.lower(), 2)


def get_event_listener() -> BlogEventListener:
    """Module-level accessor to ensure singleton semantics."""
    return BlogEventListener()
