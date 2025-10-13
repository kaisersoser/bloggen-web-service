"""
Content Streaming Manager for Progressive Blog Generation
Handles real-time streaming of partial blog content as it's generated.
Enhanced with Phase 1 Foundation SSE message types for comprehensive AI workflow visibility.
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass

# Enhanced SSE message types for Phase 1 Foundation
from core.sse_message_types import (
    create_agent_thinking_message,
    create_tool_call_message,
    create_content_stream_message,
    create_research_finding_message,
)

logger = logging.getLogger(__name__)


@dataclass
class StreamingContent:
    """Container for streaming content data"""

    task_id: str
    phase: str
    content_type: str
    content: str
    sequence_number: int
    is_partial: bool = True
    timestamp: Optional[str] = None


class ContentBuffer:
    """Buffers and manages streaming content for a task"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.research_findings: List[str] = []
        self.content_paragraphs: List[str] = []
        self.fact_corrections: List[str] = []
        self.final_content: str = ""
        self.sequence_counter = 0
        self.last_update = datetime.utcnow()

    def add_research_finding(self, finding: str) -> StreamingContent:
        """Add a research finding to the buffer"""
        self.research_findings.append(finding)
        self.sequence_counter += 1
        self.last_update = datetime.utcnow()

        return StreamingContent(
            task_id=self.task_id,
            phase="research",
            content_type="research_finding",
            content=finding,
            sequence_number=self.sequence_counter,
            timestamp=self.last_update.isoformat(),
        )

    def add_content_paragraph(self, paragraph: str) -> StreamingContent:
        """Add a content paragraph to the buffer"""
        self.content_paragraphs.append(paragraph)
        self.sequence_counter += 1
        self.last_update = datetime.utcnow()

        return StreamingContent(
            task_id=self.task_id,
            phase="content_generation",
            content_type="paragraph",
            content=paragraph,
            sequence_number=self.sequence_counter,
            timestamp=self.last_update.isoformat(),
        )

    def add_fact_correction(self, correction: str) -> StreamingContent:
        """Add a fact correction to the buffer"""
        self.fact_corrections.append(correction)
        self.sequence_counter += 1
        self.last_update = datetime.utcnow()

        return StreamingContent(
            task_id=self.task_id,
            phase="fact_checking",
            content_type="correction",
            content=correction,
            sequence_number=self.sequence_counter,
            timestamp=self.last_update.isoformat(),
        )

    def set_final_content(self, content: str) -> StreamingContent:
        """Set the final complete content"""
        self.final_content = content
        self.sequence_counter += 1
        self.last_update = datetime.utcnow()

        return StreamingContent(
            task_id=self.task_id,
            phase="finalization",
            content_type="final_content",
            content=content,
            sequence_number=self.sequence_counter,
            is_partial=False,
            timestamp=self.last_update.isoformat(),
        )

    def get_current_preview(self) -> str:
        """Get current content preview from buffer"""
        preview_parts = []

        if self.research_findings:
            preview_parts.append("## Research Findings")
            for finding in self.research_findings[-3:]:  # Show last 3 findings
                preview_parts.append(f"• {finding}")

        if self.content_paragraphs:
            preview_parts.append("\n## Draft Content")
            preview_parts.extend(self.content_paragraphs)

        if self.fact_corrections:
            preview_parts.append("\n## Fact Corrections")
            for correction in self.fact_corrections[-2:]:  # Show last 2 corrections
                preview_parts.append(f"✓ {correction}")

        return "\n".join(preview_parts) if preview_parts else ""


class ContentStreamingManager:
    """
    Manages progressive content streaming for blog generation.

    Features:
    - Real-time content buffering
    - Intelligent chunking and streaming
    - Phase-specific streaming strategies
    - Content validation and sanitization
    """

    def __init__(self):
        self.content_buffers: Dict[str, ContentBuffer] = {}
        self.streaming_callbacks: Dict[str, List[Callable]] = {}
        self._lock = asyncio.Lock()

    async def create_task_stream(self, task_id: str) -> ContentBuffer:
        """Create a new content buffer for a task"""
        async with self._lock:
            if task_id not in self.content_buffers:
                self.content_buffers[task_id] = ContentBuffer(task_id)
                # Only initialize callbacks if they don't already exist
                if task_id not in self.streaming_callbacks:
                    self.streaming_callbacks[task_id] = []

            return self.content_buffers[task_id]

    async def cleanup_task_stream(self, task_id: str):
        """Clean up streaming resources for a completed task"""
        async with self._lock:
            self.content_buffers.pop(task_id, None)
            self.streaming_callbacks.pop(task_id, None)

    async def add_streaming_callback(self, task_id: str, callback: Callable):
        """Add a callback for streaming updates"""
        async with self._lock:
            if task_id not in self.streaming_callbacks:
                self.streaming_callbacks[task_id] = []
            self.streaming_callbacks[task_id].append(callback)

    async def stream_research_finding(self, task_id: str, finding: str):
        """Stream a research finding"""
        try:
            content_buffer = await self.create_task_stream(task_id)

            # Clean and validate the finding
            cleaned_finding = self._clean_content(finding)
            if not cleaned_finding:
                return

            # Add to buffer and create streaming content
            streaming_content = content_buffer.add_research_finding(cleaned_finding)

            # Broadcast to callbacks
            await self._broadcast_streaming_content(task_id, streaming_content)

            logger.debug(
                f"Streamed research finding for task {task_id}: {cleaned_finding[:100]}..."
            )

        except Exception as e:
            logger.error(f"Failed to stream research finding for task {task_id}: {e}")

    async def stream_content_paragraph(self, task_id: str, paragraph: str):
        """Stream a content paragraph"""
        try:
            content_buffer = await self.create_task_stream(task_id)

            # Clean and validate the paragraph
            cleaned_paragraph = self._clean_content(paragraph)
            if not cleaned_paragraph:
                return

            # Add to buffer and create streaming content
            streaming_content = content_buffer.add_content_paragraph(cleaned_paragraph)

            # Broadcast to callbacks
            await self._broadcast_streaming_content(task_id, streaming_content)

            logger.debug(
                f"Streamed content paragraph for task {task_id}: {cleaned_paragraph[:100]}..."
            )

        except Exception as e:
            logger.error(f"Failed to stream content paragraph for task {task_id}: {e}")

    async def stream_fact_correction(self, task_id: str, correction: str):
        """Stream a fact correction"""
        try:
            content_buffer = await self.create_task_stream(task_id)

            # Clean and validate the correction
            cleaned_correction = self._clean_content(correction)
            if not cleaned_correction:
                return

            # Add to buffer and create streaming content
            streaming_content = content_buffer.add_fact_correction(cleaned_correction)

            # Broadcast to callbacks
            await self._broadcast_streaming_content(task_id, streaming_content)

            logger.debug(
                f"Streamed fact correction for task {task_id}: {cleaned_correction[:100]}..."
            )

        except Exception as e:
            logger.error(f"Failed to stream fact correction for task {task_id}: {e}")

    async def stream_final_content(self, task_id: str, final_content: str):
        """Stream the final complete content"""
        try:
            content_buffer = await self.create_task_stream(task_id)

            # Set final content
            streaming_content = content_buffer.set_final_content(final_content)

            # Broadcast to callbacks
            await self._broadcast_streaming_content(task_id, streaming_content)

            logger.info(f"Streamed final content for task {task_id}")

            # Schedule cleanup after a delay
            asyncio.create_task(self._delayed_cleanup(task_id, delay=300))  # 5 minutes

        except Exception as e:
            logger.error(f"Failed to stream final content for task {task_id}: {e}")

    async def get_content_preview(self, task_id: str) -> Optional[str]:
        """Get current content preview for a task"""
        try:
            if task_id in self.content_buffers:
                return self.content_buffers[task_id].get_current_preview()
            return None
        except Exception as e:
            logger.error(f"Failed to get content preview for task {task_id}: {e}")
            return None

    def _clean_content(self, content: str) -> str:
        """Clean and validate content for streaming"""
        if not content or not isinstance(content, str):
            return ""

        # Remove excessive whitespace
        cleaned = re.sub(r"\s+", " ", content.strip())

        # Remove potential script tags or dangerous content
        cleaned = re.sub(
            r"<script[^>]*>.*?</script>", "", cleaned, flags=re.IGNORECASE | re.DOTALL
        )
        cleaned = re.sub(
            r"<iframe[^>]*>.*?</iframe>", "", cleaned, flags=re.IGNORECASE | re.DOTALL
        )

        # Limit length for streaming
        if len(cleaned) > 2000:
            cleaned = cleaned[:2000] + "..."

        return cleaned

    async def _broadcast_streaming_content(
        self, task_id: str, streaming_content: StreamingContent
    ):
        """Broadcast streaming content to all callbacks"""
        if task_id not in self.streaming_callbacks:
            return

        for callback in self.streaming_callbacks[task_id]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(streaming_content)
                else:
                    callback(streaming_content)
            except Exception as e:
                logger.error(f"Streaming callback failed for task {task_id}: {e}")

    async def _delayed_cleanup(self, task_id: str, delay: int = 300):
        """Clean up task resources after a delay"""
        await asyncio.sleep(delay)
        await self.cleanup_task_stream(task_id)
        logger.debug(f"Cleaned up streaming resources for task {task_id}")

    # Phase 1 Foundation: Enhanced SSE message broadcasting for AI workflow visibility

    async def broadcast_agent_thinking(
        self, task_id: str, agent_name: str, thought: str
    ):
        """Broadcast agent thinking message for real-time AI decision visibility."""
        try:
            message = create_agent_thinking_message(
                task_id=task_id, agent_name=agent_name, thought=thought
            )

            # Send immediate message via Redis for instant feedback
            await self._send_sse_message(task_id, message)

            logger.debug(
                f"Broadcasted agent thinking for task {task_id}: {agent_name} - {thought[:50]}..."
            )

        except Exception as e:
            logger.error(f"Failed to broadcast agent thinking for task {task_id}: {e}")

    async def broadcast_tool_usage(
        self,
        task_id: str,
        tool_name: str,
        input_summary: str,
        agent_name: Optional[str] = None,
    ):
        """Broadcast tool usage message for real-time tool call visibility."""
        try:
            message = create_tool_call_message(
                task_id=task_id,
                tool_name=tool_name,
                input_summary=input_summary,
                agent_name=agent_name,
            )

            # Send immediate message via Redis for instant feedback
            await self._send_sse_message(task_id, message)

            logger.debug(f"Broadcasted tool usage for task {task_id}: {tool_name}")

        except Exception as e:
            logger.error(f"Failed to broadcast tool usage for task {task_id}: {e}")

    async def broadcast_content_generation(
        self, task_id: str, content_type: str, content: str, is_partial: bool = False
    ):
        """Broadcast content generation message for real-time content streaming."""
        try:
            message = create_content_stream_message(
                task_id=task_id,
                content_type=content_type,
                content=content,
                is_partial=is_partial,
            )

            # Send immediate message via Redis for instant feedback
            await self._send_sse_message(task_id, message)

            logger.debug(
                f"Broadcasted content generation for task {task_id}: {content_type} ({len(content)} chars)"
            )

        except Exception as e:
            logger.error(
                f"Failed to broadcast content generation for task {task_id}: {e}"
            )

    async def broadcast_research_finding(
        self, task_id: str, finding: str, source: Optional[str] = None
    ):
        """Broadcast research finding message for enhanced research visibility."""
        try:
            message = create_research_finding_message(
                task_id=task_id, finding=finding, source=source
            )

            # Send immediate message via Redis for instant feedback
            await self._send_sse_message(task_id, message)

            logger.debug(
                f"Broadcasted research finding for task {task_id}: {finding[:50]}..."
            )

        except Exception as e:
            logger.error(
                f"Failed to broadcast research finding for task {task_id}: {e}"
            )

    async def _send_sse_message(self, task_id: str, message):
        """Send SSE message via Redis for immediate delivery."""
        try:
            # Get the task manager to access Redis publishing
            from core.task_manager import task_manager

            if task_manager and task_manager._redis_manager:
                message_data = message.to_dict()
                await task_manager._redis_manager.publish_immediate_message(
                    task_id, message_data
                )

        except Exception as e:
            logger.error(f"Failed to send SSE message for task {task_id}: {e}")


# Global content streaming manager instance
content_streaming_manager = ContentStreamingManager()
