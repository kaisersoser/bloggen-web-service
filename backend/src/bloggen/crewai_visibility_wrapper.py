"""
CrewAI Output Interceptor - Capture verbose output and convert to structured events
"""

import sys
import re
import threading
from io import StringIO
from contextlib import contextmanager
from typing import Callable, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CrewAIOutputInterceptor:
    """Intercepts CrewAI verbose output and converts to structured events"""

    def __init__(self, event_callback: Callable[[Dict[str, Any]], None]):
        self.event_callback = event_callback
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.captured_output = StringIO()

        # Patterns to match CrewAI verbose output
        self.patterns = {
            "agent_start": re.compile(r"^\> (.*?) is starting (.*)"),
            "agent_thinking": re.compile(r"^\[.*?\] (.+)"),
            "tool_call": re.compile(r"Tool:\s*(\w+)\s*-\s*(.+)"),
            "tool_result": re.compile(r"Tool Result:\s*(.+)"),
            "delegation": re.compile(r"Delegating to (.+):(.+)"),
            "final_answer": re.compile(r"Final Answer:\s*(.+)"),
            "crew_step": re.compile(r"^\*{3,}\s*(.+?)\s*\*{3,}"),
            "error": re.compile(r"Error:\s*(.+)"),
        }

    @contextmanager
    def capture_crewai_output(self):
        """Context manager to capture CrewAI stdout/stderr"""
        try:
            # Redirect stdout and stderr to our capture buffer
            sys.stdout = self.captured_output
            sys.stderr = self.captured_output

            # Start monitoring thread
            monitor_thread = threading.Thread(target=self._monitor_output, daemon=True)
            monitor_thread.start()

            yield

        finally:
            # Restore original stdout/stderr
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr

    def _monitor_output(self):
        """Monitor captured output and emit events"""
        while True:
            # Get current content
            content = self.captured_output.getvalue()
            if content:
                lines = content.split("\n")

                for line in lines:
                    if line.strip():
                        self._parse_and_emit_event(line.strip())

                # Clear processed content
                self.captured_output.seek(0)
                self.captured_output.truncate(0)

            threading.Event().wait(0.1)  # Check every 100ms

    def _parse_and_emit_event(self, line: str):
        """Parse a line of output and emit appropriate event"""
        try:
            # Try to match against known patterns
            for event_type, pattern in self.patterns.items():
                match = pattern.search(line)
                if match:
                    event = {
                        "type": event_type,
                        "raw_line": line,
                        "timestamp": self._get_timestamp(),
                        "data": match.groups(),
                    }

                    # Add specific parsing for different event types
                    if event_type == "agent_start":
                        event["agent_name"] = match.group(1)
                        event["task_description"] = match.group(2)

                    elif event_type == "tool_call":
                        event["tool_name"] = match.group(1)
                        event["tool_input"] = match.group(2)

                    elif event_type == "agent_thinking":
                        event["thought"] = match.group(1)

                    # Emit the structured event
                    self.event_callback(event)
                    return

            # If no pattern matched, emit as generic output
            self.event_callback(
                {
                    "type": "generic_output",
                    "raw_line": line,
                    "timestamp": self._get_timestamp(),
                }
            )

        except Exception as e:
            logger.warning(f"Error parsing CrewAI output line: {e}")

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime

        return datetime.utcnow().isoformat()


class CrewAIExecutionWrapper:
    """High-level wrapper for executing CrewAI with enhanced visibility"""

    def __init__(self, status_callback: Optional[Callable] = None):
        self.status_callback = status_callback
        self.interceptor = CrewAIOutputInterceptor(self._handle_crewai_event)
        self.current_phase = "unknown"

    def execute_crew_with_visibility(self, crew, phase_name: str = "crew_execution"):
        """Execute a CrewAI crew with full visibility into its processes"""
        self.current_phase = phase_name

        logger.info(
            f"🔍 Starting CrewAI execution with output interception for phase: {phase_name}"
        )

        # Send initial status
        self._send_status_update("Initializing CrewAI agents...", 0)

        with self.interceptor.capture_crewai_output():
            try:
                # Execute the crew - output will be intercepted
                result = crew.kickoff()

                # Send completion status
                self._send_status_update("CrewAI execution completed", 100)

                return result

            except Exception as e:
                self._send_status_update(f"CrewAI execution failed: {str(e)}", 0)
                raise

    def _handle_crewai_event(self, event: Dict[str, Any]):
        """Handle intercepted CrewAI events and convert to status updates"""
        event_type = event.get("type")

        if event_type == "agent_start":
            agent_name = event.get("agent_name", "Unknown Agent")
            task = event.get("task_description", "unknown task")
            self._send_agent_thinking(agent_name, f"Starting: {task}")

        elif event_type == "agent_thinking":
            thought = event.get("thought", "")
            # Extract agent name from context or use current phase
            agent_name = f"{self.current_phase.title()} Agent"
            self._send_agent_thinking(agent_name, thought)

        elif event_type == "tool_call":
            tool_name = event.get("tool_name", "Unknown Tool")
            tool_input = event.get("tool_input", "")
            agent_name = f"{self.current_phase.title()} Agent"
            self._send_tool_usage(agent_name, tool_name, tool_input)

        elif event_type == "tool_result":
            result = event.get("data", [""])[0] if event.get("data") else ""
            agent_name = f"{self.current_phase.title()} Agent"
            self._send_agent_thinking(agent_name, f"Tool result: {result[:100]}...")

        elif event_type == "final_answer":
            answer = event.get("data", [""])[0] if event.get("data") else ""
            agent_name = f"{self.current_phase.title()} Agent"
            self._send_agent_thinking(
                agent_name, f"Final answer generated: {answer[:100]}..."
            )

        # Log all events for debugging
        logger.debug(f"CrewAI Event: {event}")

    def _send_status_update(self, message: str, progress: int):
        """Send status update via callback"""
        if self.status_callback:
            self.status_callback(
                {
                    "message_type": "status",
                    "message": message,
                    "progress": progress,
                    "current_step": self.current_phase,
                    "timestamp": self._get_timestamp(),
                }
            )

    def _send_agent_thinking(self, agent_name: str, thought: str):
        """Send agent thinking update"""
        if self.status_callback:
            self.status_callback(
                {
                    "message_type": "agentthinking",
                    "agent_name": agent_name,
                    "thought": thought,
                    "timestamp": self._get_timestamp(),
                }
            )

    def _send_tool_usage(self, agent_name: str, tool_name: str, input_data: str):
        """Send tool usage notification"""
        if self.status_callback:
            self.status_callback(
                {
                    "message_type": "toolcall",
                    "agent_name": agent_name,
                    "tool_name": tool_name,
                    "input": input_data[:200],  # Truncate long inputs
                    "timestamp": self._get_timestamp(),
                }
            )

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime

        return datetime.utcnow().isoformat()
