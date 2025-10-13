"""Tests for the BlogEventListener native callback wiring.

These tests ensure CrewAI events are mirrored to the StatusUpdateManager
without relying on legacy stdout scraping.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from bloggen.callbacks import get_event_listener


class DummyStatusManager:
    def __init__(self) -> None:
        self.status_updates: List[Dict[str, Any]] = []
        self.agent_thinking: List[Dict[str, Any]] = []
        self.tool_usage: List[Dict[str, Any]] = []
        self.errors: List[str] = []

    def send_status_update(self, message: str, step: int, detail: str = "") -> None:
        self.status_updates.append({"message": message, "step": step, "detail": detail})

    def send_agent_thinking(self, agent_name: str, thought: str) -> None:
        self.agent_thinking.append({"agent_name": agent_name, "thought": thought})

    def send_tool_usage(self, tool_name: str, input_summary: str, agent_name: str) -> None:
        self.tool_usage.append({
            "tool_name": tool_name,
            "input_summary": input_summary,
            "agent_name": agent_name,
        })

    def send_error_update(self, message: str) -> None:
        self.errors.append(message)


@pytest.fixture(autouse=True)
def reset_listener_state() -> None:
    listener = get_event_listener()
    listener._contexts.clear()  # type: ignore[attr-defined]
    listener._task_index.clear()  # type: ignore[attr-defined]


def _register_listener(phase: str = "research"):
    listener = get_event_listener()
    status_manager = DummyStatusManager()
    crew = SimpleNamespace(
        id="crew-123",
        tasks=[SimpleNamespace(id="task-1", name="Primary Task")],
    )
    listener.register_run(crew, phase, status_manager)
    context = listener._contexts[str(crew.id)]  # type: ignore[attr-defined]
    return listener, context, crew, status_manager


def test_task_events_emit_status_updates():
    listener, context, crew, status_manager = _register_listener("content_generation")
    source = SimpleNamespace(name="Draft Article", agent=SimpleNamespace(role="Content Creator"), crew=crew)
    event = SimpleNamespace(task_id="task-1")

    listener._handle_task_started(context, source, event)
    listener._handle_task_completed(context, source, event)

    assert status_manager.status_updates == [
        {
            "message": "Content_Generation phase in progress",
            "step": 3,
            "detail": "Task 'Draft Article' started",
        }
    ]
    assert status_manager.agent_thinking[-1]["agent_name"] == "Content Creator"
    assert "Task completed" in status_manager.agent_thinking[-1]["thought"]

    listener.unregister_run(crew)


def test_tool_events_emit_usage_messages():
    listener, context, crew, status_manager = _register_listener("fact_checking")
    source = SimpleNamespace(agent=SimpleNamespace(role="Fact Checker"), crew=crew)
    event = SimpleNamespace(
        tool_name="URLValidationTool",
        agent_role="Fact Checker",
        tool_args={"url": "https://example.com"},
    )

    listener._handle_tool_started(context, source, event)
    listener._handle_tool_finished(context, source, event)

    assert status_manager.tool_usage == [
        {
            "tool_name": "URLValidationTool",
            "input_summary": "{'url': 'https://example.com'}",
            "agent_name": "Fact Checker",
        }
    ]
    assert status_manager.agent_thinking[-1]["thought"] == "URLValidationTool returned results."

    listener.unregister_run(crew)


def test_reasoning_events_share_agent_thoughts():
    listener, context, crew, status_manager = _register_listener("research")
    source = SimpleNamespace(role="Senior Researcher", crew=crew)

    reasoning_started = SimpleNamespace(agent_role="Senior Researcher")
    reasoning_completed = SimpleNamespace(agent_role="Senior Researcher", plan="Assess data sources")

    listener._handle_agent_reasoning_started(context, source, reasoning_started)
    listener._handle_agent_reasoning_completed(context, source, reasoning_completed)

    assert status_manager.agent_thinking[0] == {
        "agent_name": "Senior Researcher",
        "thought": "Evaluating approach...",
    }
    assert status_manager.agent_thinking[1]["thought"] == "Assess data sources"

    listener.unregister_run(crew)


def test_phase_step_mapping_recognizes_extended_phases():
    listener = get_event_listener()
    assert listener._phase_step("initialization") == 1
    assert listener._phase_step("content_validation") == 3
    assert listener._phase_step("image_enhancement") == 3
    assert listener._phase_step("fact_checking") == 4
    assert listener._phase_step("finalization") == 5