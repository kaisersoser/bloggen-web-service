"""
Status Update Manager for Blog Generation Flow

Handles status updates and progress tracking with enhanced SSE message types
for comprehensive real-time AI workflow visibility (Phase 1 Foundation).
Follows Single Responsibility Principle - only manages status updates.
"""

from typing import Optional, Callable, Dict, Any
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
    
    def __init__(self, task_id: str, status_callback: Callable[[Dict[str, Any]], None], total_steps: int = 5):
        self.task_id = task_id
        self.status_callback = status_callback
        self.total_steps = total_steps
        self._current_progress = 0  # Track current progress to avoid overriding
    
    def send_status_update(self, message: str, step: int, detail: Optional[str] = None):
        """Send enhanced status update with new SSE message types."""
        if self.status_callback:
            # Map step numbers to specific progress percentages
            step_progress_map = {
                1: 10,   # Initialization (10%)
                2: 25,   # Research (25%)
                3: 50,   # Content Generation (50%)
                4: 75,   # Fact Checking (75%)
                5: 90    # Finalization (90%)
            }
            
            progress = step_progress_map.get(step, min((step / self.total_steps) * 100, 100))
            
            # Track current progress to avoid overriding in agent/tool messages
            self._current_progress = progress
            
            # Create enhanced status message
            status_message = create_status_message(
                task_id=self.task_id,
                status='in_progress',
                message=message,
                step=f"Step {step}/{self.total_steps}",
                progress=progress  # Already in percentage
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
                    'progress': 1.0,  # Always 100% completion
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
        """Send an agent thinking message without overriding progress."""
        print(f"🚨 PRINT DEBUG: send_agent_thinking called with agent={agent_name}")
        logger.info(f"🔍 DEBUG StatusUpdateManager.send_agent_thinking called: agent={agent_name}, thought={thought[:50]}...")
        if self.status_callback:
            try:
                # Get current progress to avoid overriding it
                current_progress = getattr(self, '_current_progress', 0)
                
                logger.info(f"🔍 DEBUG StatusUpdateManager.send_agent_thinking calling callback with progress={current_progress}")
                self.status_callback({
                    'message_type': 'agentthinking',
                    'agent_name': agent_name,
                    'thought': thought,
                    'timestamp': self._get_timestamp(),
                    'progress': current_progress  # Preserve current progress instead of defaulting to 0
                })
                logger.info(f"🔍 DEBUG StatusUpdateManager.send_agent_thinking callback completed successfully")
            except Exception as e:
                logger.error(f"Failed to send agent thinking update: {e}")
        else:
            logger.warning(f"🔍 DEBUG StatusUpdateManager.send_agent_thinking: No status_callback available!")
    
    def send_tool_usage(self, tool_name: str, input_summary: str, agent_name: str = "Unknown"):
        """Send a tool usage message without overriding progress.""" 
        if self.status_callback:
            try:
                # Get current progress to avoid overriding it
                current_progress = getattr(self, '_current_progress', 0)
                
                self.status_callback({
                    'message_type': 'toolcall',
                    'tool_name': tool_name,
                    'input_summary': input_summary,
                    'agent_name': agent_name,
                    'timestamp': self._get_timestamp(),
                    'progress': current_progress  # Preserve current progress instead of defaulting to 0
                })
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
    
    def send_research_finding(self, finding: str, source: str = "Research"):
        """Send a research finding message without overriding progress."""
        if self.status_callback:
            try:
                # Get current progress to avoid overriding it
                current_progress = getattr(self, '_current_progress', 0)
                
                self.status_callback({
                    'message_type': 'researchfinding',
                    'finding': finding,
                    'source': source,
                    'timestamp': self._get_timestamp(),
                    'progress': current_progress  # Preserve current progress instead of defaulting to 0
                })
            except Exception as e:
                logger.error(f"Failed to send research finding update: {e}")
    
    def _get_timestamp(self) -> str:
        """Get ISO formatted timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()
