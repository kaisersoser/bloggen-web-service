"""
Status Update Manager for Blog Generation Flow

Handles status updates and progress tracking with enhanced SSE message types
for comprehensive real-time AI workflow visibility (Phase 1 Foundation).
Follows Single Responsibility Principle - only manages status updates.
"""

from typing import Optional, Callable
import logging

# Enhanced SSE message types for Phase 1 Foundation
from core.sse_message_types import (
    create_status_message,
    create_agent_thinking_message,
    create_tool_call_message,
    create_content_stream_message,
    create_research_finding_message
)

logger = logging.getLogger(__name__)


class StatusUpdateManager:
    """
    Manages status updates and progress tracking for blog generation.
    Enhanced with Phase 1 Foundation SSE message types for comprehensive AI workflow visibility.
    """
    
    def __init__(self, status_callback: Optional[Callable] = None, total_steps: int = 4, task_id: Optional[str] = None):
        self.status_callback = status_callback
        self.total_steps = total_steps
        self.current_step = 0
        self.task_id = task_id or "unknown-task"
    
    def send_status_update(self, message: str, step: int, detail: Optional[str] = None):
        """Send enhanced status update with new SSE message types."""
        if self.status_callback:
            progress = min((step / self.total_steps), 1.0)
            
            # Create enhanced status message
            status_message = create_status_message(
                task_id=self.task_id,
                status='in_progress',
                message=message,
                step=f"Step {step}/{self.total_steps}",
                progress=progress * 100  # Convert to percentage
            )
            
            # Convert to dict for callback
            status_data = status_message.to_dict()
            if detail:
                status_data['detail'] = detail
            
            try:
                self.status_callback(status_data)
                logger.debug(f"Enhanced status update sent: {message} (Step {step}/{self.total_steps})")
            except Exception as e:
                logger.error(f"Failed to send enhanced status update: {e}")
    
    def send_log_update(self, log_message: str, step: str = "Processing"):
        """Send a log message update."""
        if self.status_callback:
            try:
                self.status_callback({
                    'status': 'log',
                    'message': log_message,
                    'step': step,
                    'timestamp': self._get_timestamp()
                })
            except Exception as e:
                logger.error(f"Failed to send log update: {e}")
    
    def send_completion_update(self, final_content: str):
        """Send completion status with final blog content."""
        if self.status_callback:
            try:
                self.status_callback({
                    'status': 'completed',
                    'message': 'Blog generation completed successfully!',
                    'progress': 1.0,
                    'content': final_content,
                    'timestamp': self._get_timestamp()
                })
            except Exception as e:
                logger.error(f"Failed to send completion update: {e}")
    
    def send_error_update(self, error_message: str):
        """Send error status update."""
        if self.status_callback:
            try:
                self.status_callback({
                    'status': 'error',
                    'message': error_message,
                    'timestamp': self._get_timestamp()
                })
            except Exception as e:
                logger.error(f"Failed to send error update: {e}")
    
    # Phase 1 Foundation: Enhanced SSE message broadcasting methods
    
    def send_agent_thinking(self, agent_name: str, thought: str):
        """Send agent thinking update for real-time AI decision visibility."""
        if self.status_callback:
            try:
                thinking_message = create_agent_thinking_message(
                    task_id=self.task_id,
                    agent_name=agent_name,
                    thought=thought
                )
                self.status_callback(thinking_message.to_dict())
                logger.debug(f"Agent thinking update sent: {agent_name} - {thought[:50]}...")
            except Exception as e:
                logger.error(f"Failed to send agent thinking update: {e}")
    
    def send_tool_usage(self, tool_name: str, input_summary: str, agent_name: Optional[str] = None):
        """Send tool usage update for real-time tool call visibility."""
        if self.status_callback:
            try:
                tool_message = create_tool_call_message(
                    task_id=self.task_id,
                    tool_name=tool_name,
                    input_summary=input_summary,
                    agent_name=agent_name
                )
                self.status_callback(tool_message.to_dict())
                logger.debug(f"Tool usage update sent: {tool_name} by {agent_name or 'unknown agent'}")
            except Exception as e:
                logger.error(f"Failed to send tool usage update: {e}")
    
    def send_content_stream(self, content_type: str, content: str, is_partial: bool = False):
        """Send content streaming update for real-time content generation visibility."""
        if self.status_callback:
            try:
                content_message = create_content_stream_message(
                    task_id=self.task_id,
                    content_type=content_type,
                    content=content,
                    is_partial=is_partial
                )
                self.status_callback(content_message.to_dict())
                logger.debug(f"Content stream update sent: {content_type} ({len(content)} chars)")
            except Exception as e:
                logger.error(f"Failed to send content stream update: {e}")
    
    def send_research_finding(self, finding: str, source: Optional[str] = None):
        """Send research finding update for enhanced research visibility."""
        if self.status_callback:
            try:
                research_message = create_research_finding_message(
                    task_id=self.task_id,
                    finding=finding,
                    source=source
                )
                self.status_callback(research_message.to_dict())
                logger.debug(f"Research finding update sent: {finding[:50]}...")
            except Exception as e:
                logger.error(f"Failed to send research finding update: {e}")
    
    def _get_timestamp(self) -> str:
        """Get ISO formatted timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()
