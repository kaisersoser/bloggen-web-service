"""
Enhanced SSE Message Types for Real-Time AI Workflow Visualization

This module provides a comprehensive set of message types for streaming
detailed updates about the AI blog generation process, including agent
thoughts, tool usage, content generation, and research findings.

Designed for Phase 1 of UX Enhancement Phase 2 - Foundation implementation
to provide immediate feedback and eliminate delays in user experience.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

from typing import Dict, Any, Optional, Union, Literal
from datetime import datetime
import json
from dataclasses import dataclass, asdict


# Enhanced SSE Message Types
SSEMessageType = Literal[
    'status',           # Overall status
    'progress',         # Progress percentage
    'task_created',     # Task acknowledgment
    'initializing',     # System initialization
    'agent_thinking',   # Agent decision process
    'agent_action',     # Agent taking specific action
    'tool_call',        # Tool being invoked
    'tool_result',      # Tool result summary
    'content_stream',   # Live content generation
    'research_finding', # Research discovery
    'content_draft',    # Content section completed
    'fact_check',       # Fact-checking process
    'revision',         # Content revision
    'hero_image',       # Hero image update
    'completed',        # Final completion
    'error'            # Error state
]


@dataclass
class BaseSSEMessage:
    """Base class for all SSE messages with consistent structure."""
    task_id: str
    message: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    message_type: str = field(init=False)
    
    def __post_init__(self):
        """Set message_type automatically based on class name."""
        self.message_type = self.__class__.__name__.replace('Message', '').lower()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for JSON serialization."""
        return {
            'message_type': self.message_type,
            'task_id': self.task_id,
            'message': self.message,
            'timestamp': self.timestamp,
            **{k: v for k, v in self.__dict__.items() 
               if k not in ['message_type', 'task_id', 'message', 'timestamp'] and v is not None}
        }


@dataclass
class StatusMessage(BaseSSEMessage):
    """Basic status update message"""
    type: Literal['status'] = 'status'
    status: str = ''
    step: Optional[str] = None
    progress: float = 0.0


@dataclass
class TaskCreatedMessage(BaseSSEMessage):
    """Immediate task creation acknowledgment"""
    type: Literal['task_created'] = 'task_created'
    queue_position: Optional[int] = None
    estimated_wait_time: Optional[int] = None  # seconds


@dataclass
class InitializingMessage(BaseSSEMessage):
    """System initialization message"""
    type: Literal['initializing'] = 'initializing'
    phase: str = ''  # 'setup_agents', 'load_tools', 'prepare_flow'
    progress: float = 0.0


@dataclass
class AgentThinkingMessage(BaseSSEMessage):
    """Agent decision process message"""
    type: Literal['agent_thinking'] = 'agent_thinking'
    agent_name: str = ''
    thought: str = ''
    confidence: Optional[float] = None
    alternatives_considered: Optional[list] = None


@dataclass
class AgentActionMessage(BaseSSEMessage):
    """Agent taking specific action"""
    type: Literal['agent_action'] = 'agent_action'
    agent_name: str = ''
    action: str = ''
    target: Optional[str] = None  # What the action is targeting


@dataclass
class ToolCallMessage(BaseSSEMessage):
    """Tool being invoked"""
    type: Literal['tool_call'] = 'tool_call'
    tool_name: str = ''
    input_summary: str = ''
    agent_name: Optional[str] = None


@dataclass
class ToolResultMessage(BaseSSEMessage):
    """Tool result summary"""
    type: Literal['tool_result'] = 'tool_result'
    tool_name: str = ''
    result_summary: str = ''
    success: bool = True
    processing_time: Optional[float] = None


@dataclass
class ContentStreamMessage(BaseSSEMessage):
    """Live content generation"""
    type: Literal['content_stream'] = 'content_stream'
    content_type: str = ''  # 'research', 'outline', 'introduction', 'section', 'conclusion'
    content: str = ''
    is_partial: bool = False
    section_title: Optional[str] = None
    word_count: Optional[int] = None


@dataclass
class ResearchFindingMessage(BaseSSEMessage):
    """Research discovery"""
    type: Literal['research_finding'] = 'research_finding'
    finding: str = ''
    source: Optional[str] = None
    relevance_score: Optional[float] = None


@dataclass
class ContentDraftMessage(BaseSSEMessage):
    """Content section completed"""
    type: Literal['content_draft'] = 'content_draft'
    section_name: str = ''
    content: str = ''
    word_count: int = 0
    is_complete: bool = True


@dataclass
class FactCheckMessage(BaseSSEMessage):
    """Fact-checking process"""
    type: Literal['fact_check'] = 'fact_check'
    claim: str = ''
    verification_result: str = ''  # 'verified', 'disputed', 'needs_revision'
    confidence: Optional[float] = None


@dataclass
class RevisionMessage(BaseSSEMessage):
    """Content revision"""
    type: Literal['revision'] = 'revision'
    section: str = ''
    old_content: str = ''
    new_content: str = ''
    reason: str = ''


@dataclass
class HeroImageMessage(BaseSSEMessage):
    """Hero image update"""
    type: Literal['hero_image'] = 'hero_image'
    image_url: str = ''
    alt_text: Optional[str] = None
    selection_reason: Optional[str] = None


@dataclass
class CompletedMessage(BaseSSEMessage):
    """Final completion"""
    type: Literal['completed'] = 'completed'
    final_content: Optional[str] = None
    word_count: Optional[int] = None
    generation_time: Optional[float] = None
    hero_image_url: Optional[str] = None


@dataclass
class ErrorMessage(BaseSSEMessage):
    """Error state"""
    type: Literal['error'] = 'error'
    error_code: Optional[str] = None
    error_details: Optional[str] = None
    recoverable: bool = False


# Message factory functions for convenience
def create_status_message(task_id: str, status: str, message: str, step: Optional[str] = None, progress: float = 0.0) -> StatusMessage:
    return StatusMessage(task_id=task_id, message=message, status=status, step=step, progress=progress)

def create_task_created_message(task_id: str, message: str = "Task received and queued") -> TaskCreatedMessage:
    return TaskCreatedMessage(task_id=task_id, message=message)

def create_initializing_message(task_id: str, phase: str, message: str, progress: float = 0.0) -> InitializingMessage:
    return InitializingMessage(task_id=task_id, message=message, phase=phase, progress=progress)

def create_agent_thinking_message(task_id: str, agent_name: str, thought: str, message: Optional[str] = None) -> AgentThinkingMessage:
    return AgentThinkingMessage(
        task_id=task_id, 
        message=message or f"{agent_name} is thinking: {thought[:50]}...",
        agent_name=agent_name,
        thought=thought
    )

def create_tool_call_message(task_id: str, tool_name: str, input_summary: str, agent_name: Optional[str] = None) -> ToolCallMessage:
    return ToolCallMessage(
        task_id=task_id,
        message=f"Calling {tool_name}: {input_summary}",
        tool_name=tool_name,
        input_summary=input_summary,
        agent_name=agent_name
    )

def create_content_stream_message(task_id: str, content_type: str, content: str, is_partial: bool = False) -> ContentStreamMessage:
    return ContentStreamMessage(
        task_id=task_id,
        message=f"Generating {content_type}: {len(content)} characters",
        content_type=content_type,
        content=content,
        is_partial=is_partial,
        word_count=len(content.split()) if content else 0
    )

def create_research_finding_message(task_id: str, finding: str, source: Optional[str] = None) -> ResearchFindingMessage:
    return ResearchFindingMessage(
        task_id=task_id,
        message=f"Research finding: {finding[:50]}...",
        finding=finding,
        source=source
    )

def create_completed_message(task_id: str, final_content: Optional[str] = None, generation_time: Optional[float] = None) -> CompletedMessage:
    word_count = len(final_content.split()) if final_content else 0
    return CompletedMessage(
        task_id=task_id,
        message=f"Blog generation completed ({word_count} words)",
        final_content=final_content,
        word_count=word_count,
        generation_time=generation_time
    )

def create_error_message(task_id: str, error_msg: str, error_code: Optional[str] = None, recoverable: bool = False) -> ErrorMessage:
    return ErrorMessage(
        task_id=task_id,
        message=f"Error: {error_msg}",
        error_code=error_code,
        error_details=error_msg,
        recoverable=recoverable
    )
