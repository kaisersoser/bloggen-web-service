"""
Generation Metrics Collection

Tracks detailed metrics for each blog generation to enable data-driven improvements.
Captures timing per phase, word counts per attempt, retry reasons, and quality scores.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class PhaseMetric:
    """Metrics for a single phase execution."""
    phase_name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_seconds: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    retry_count: int = 0
    
    # Content-specific metrics (only for content phase)
    word_count: Optional[int] = None
    quality_score: Optional[float] = None
    citation_count: Optional[int] = None
    
    # Research-specific metrics (only for research phase)
    fact_count: Optional[int] = None
    source_count: Optional[int] = None
    
    def complete(self, success: bool = True, error_message: Optional[str] = None) -> None:
        """Mark phase as complete and calculate duration."""
        self.end_time = time.time()
        self.duration_seconds = self.end_time - self.start_time
        self.success = success
        self.error_message = error_message


@dataclass
class ContentAttempt:
    """Metrics for a single content generation attempt."""
    attempt_number: int
    word_count: int
    quality_score: float
    citation_count: int
    paragraph_count: int
    section_count: int
    passed_validation: bool
    feedback_given: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class GenerationMetrics:
    """Complete metrics for a blog generation run."""
    blog_id: str
    user_id: str
    topic: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Overall status
    success: bool = False
    final_status: str = "in_progress"
    
    # Phase metrics
    phases: Dict[str, PhaseMetric] = field(default_factory=dict)
    
    # Content attempts (for retry tracking)
    content_attempts: List[ContentAttempt] = field(default_factory=list)
    
    # Final content metrics
    final_word_count: Optional[int] = None
    final_quality_score: Optional[float] = None
    final_citation_count: Optional[int] = None
    
    # Research metrics
    research_fact_count: Optional[int] = None
    research_source_count: Optional[int] = None
    research_quality_score: Optional[float] = None
    
    # Totals
    total_duration_seconds: Optional[float] = None
    total_retries: int = 0
    
    def start_phase(self, phase_name: str) -> PhaseMetric:
        """Start tracking a new phase."""
        metric = PhaseMetric(phase_name=phase_name)
        self.phases[phase_name] = metric
        logger.info(f"📊 Metrics: Starting phase '{phase_name}'")
        return metric
    
    def complete_phase(
        self, 
        phase_name: str, 
        success: bool = True, 
        error_message: Optional[str] = None,
        **additional_metrics
    ) -> None:
        """Complete a phase and record additional metrics."""
        if phase_name not in self.phases:
            logger.warning(f"Phase '{phase_name}' was not started, creating now")
            self.phases[phase_name] = PhaseMetric(phase_name=phase_name)
        
        phase = self.phases[phase_name]
        phase.complete(success=success, error_message=error_message)
        
        # Apply additional metrics
        for key, value in additional_metrics.items():
            if hasattr(phase, key):
                setattr(phase, key, value)
        
        duration_str = f"{phase.duration_seconds:.2f}s" if phase.duration_seconds else "N/A"
        logger.info(f"📊 Metrics: Completed phase '{phase_name}' in {duration_str} (success={success})")
    
    def record_content_attempt(
        self,
        attempt_number: int,
        word_count: int,
        quality_score: float,
        citation_count: int,
        paragraph_count: int,
        section_count: int,
        passed_validation: bool,
        feedback_given: Optional[str] = None
    ) -> None:
        """Record metrics for a content generation attempt."""
        attempt = ContentAttempt(
            attempt_number=attempt_number,
            word_count=word_count,
            quality_score=quality_score,
            citation_count=citation_count,
            paragraph_count=paragraph_count,
            section_count=section_count,
            passed_validation=passed_validation,
            feedback_given=feedback_given
        )
        self.content_attempts.append(attempt)
        
        if not passed_validation:
            self.total_retries += 1
        
        logger.info(
            f"📊 Metrics: Content attempt #{attempt_number}: "
            f"{word_count} words, score={quality_score:.1f}, "
            f"citations={citation_count}, passed={passed_validation}"
        )
    
    def finalize(self, success: bool, final_status: str) -> None:
        """Finalize the generation metrics."""
        self.completed_at = datetime.utcnow()
        self.success = success
        self.final_status = final_status
        
        if self.started_at and self.completed_at:
            self.total_duration_seconds = (
                self.completed_at - self.started_at
            ).total_seconds()
        
        # Set final content metrics from last successful attempt
        if self.content_attempts:
            last_attempt = self.content_attempts[-1]
            if last_attempt.passed_validation or success:
                self.final_word_count = last_attempt.word_count
                self.final_quality_score = last_attempt.quality_score
                self.final_citation_count = last_attempt.citation_count
        
        logger.info(
            f"📊 Metrics: Generation finalized - "
            f"success={success}, status={final_status}, "
            f"total_duration={self.total_duration_seconds:.2f}s, "
            f"total_retries={self.total_retries}"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for database storage."""
        return {
            "blog_id": self.blog_id,
            "user_id": self.user_id,
            "topic": self.topic,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "success": self.success,
            "final_status": self.final_status,
            "total_duration_seconds": self.total_duration_seconds,
            "total_retries": self.total_retries,
            
            # Phase timings
            "research_duration_seconds": self._get_phase_duration("research"),
            "content_duration_seconds": self._get_phase_duration("content"),
            "fact_check_duration_seconds": self._get_phase_duration("fact_check"),
            "finalize_duration_seconds": self._get_phase_duration("finalize"),
            
            # Final metrics
            "final_word_count": self.final_word_count,
            "final_quality_score": self.final_quality_score,
            "final_citation_count": self.final_citation_count,
            
            # Research metrics
            "research_fact_count": self.research_fact_count,
            "research_source_count": self.research_source_count,
            
            # Attempt history (JSON)
            "content_attempts": [
                {
                    "attempt": a.attempt_number,
                    "word_count": a.word_count,
                    "quality_score": a.quality_score,
                    "citation_count": a.citation_count,
                    "passed": a.passed_validation,
                }
                for a in self.content_attempts
            ],
        }
    
    def _get_phase_duration(self, phase_name: str) -> Optional[float]:
        """Get duration for a specific phase."""
        phase = self.phases.get(phase_name)
        return phase.duration_seconds if phase else None
    
    def get_summary(self) -> str:
        """Get human-readable summary of metrics."""
        lines = [
            f"📊 Generation Metrics Summary for blog {self.blog_id}",
            f"   Topic: {self.topic[:50]}..." if len(self.topic) > 50 else f"   Topic: {self.topic}",
            f"   Status: {self.final_status} (success={self.success})",
            f"   Total Duration: {self.total_duration_seconds:.2f}s" if self.total_duration_seconds else "   Total Duration: N/A",
            f"   Total Retries: {self.total_retries}",
            "",
            "   Phase Timings:",
        ]
        
        for phase_name, phase in self.phases.items():
            duration = f"{phase.duration_seconds:.2f}s" if phase.duration_seconds else "N/A"
            status = "✅" if phase.success else "❌"
            lines.append(f"      {status} {phase_name}: {duration}")
        
        if self.content_attempts:
            lines.append("")
            lines.append("   Content Attempts:")
            for attempt in self.content_attempts:
                status = "✅" if attempt.passed_validation else "❌"
                lines.append(
                    f"      {status} #{attempt.attempt_number}: "
                    f"{attempt.word_count} words, score={attempt.quality_score:.1f}"
                )
        
        if self.final_word_count:
            lines.append("")
            lines.append(f"   Final Content: {self.final_word_count} words, "
                        f"score={self.final_quality_score:.1f}, "
                        f"{self.final_citation_count} citations")
        
        return "\n".join(lines)


class MetricsCollector:
    """Manages metrics collection for a generation run."""
    
    def __init__(self, blog_id: str, user_id: str, topic: str):
        self.metrics = GenerationMetrics(
            blog_id=blog_id,
            user_id=user_id,
            topic=topic
        )
        self._current_phase: Optional[str] = None
    
    @contextmanager
    def phase(self, phase_name: str):
        """Context manager for timing a phase."""
        self._current_phase = phase_name
        self.metrics.start_phase(phase_name)
        try:
            yield self.metrics.phases[phase_name]
            self.metrics.complete_phase(phase_name, success=True)
        except Exception as e:
            self.metrics.complete_phase(
                phase_name, 
                success=False, 
                error_message=str(e)
            )
            raise
        finally:
            self._current_phase = None
    
    def record_content_attempt(self, **kwargs) -> None:
        """Record a content generation attempt."""
        self.metrics.record_content_attempt(**kwargs)
    
    def set_research_metrics(
        self, 
        fact_count: int, 
        source_count: int,
        quality_score: Optional[float] = None
    ) -> None:
        """Set research phase metrics."""
        self.metrics.research_fact_count = fact_count
        self.metrics.research_source_count = source_count
        self.metrics.research_quality_score = quality_score
        
        # Also update the phase metric if it exists
        if "research" in self.metrics.phases:
            self.metrics.phases["research"].fact_count = fact_count
            self.metrics.phases["research"].source_count = source_count
    
    def finalize(self, success: bool, final_status: str) -> GenerationMetrics:
        """Finalize and return the complete metrics."""
        self.metrics.finalize(success=success, final_status=final_status)
        logger.info(self.metrics.get_summary())
        return self.metrics
    
    def get_metrics(self) -> GenerationMetrics:
        """Get the current metrics."""
        return self.metrics
