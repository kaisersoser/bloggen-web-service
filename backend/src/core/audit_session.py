"""
Audit Session Manager

Manages audit session lifecycle and API call tracking.
Follows Single Responsibility Principle - only manages audit sessions.
"""

import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from core.database_worker import DatabaseWorker
from core.cost_calculator import CostCalculator

logger = logging.getLogger(__name__)


class AuditSession:
    """Manages a single audit session with API call tracking."""

    def __init__(self, session_type: str, user_id: str, blog_id: Optional[str] = None):
        self.session_id = str(uuid.uuid4())
        self.session_type = session_type
        self.user_id = user_id
        self.blog_id = blog_id
        self.start_time = datetime.now()

        # Tracking variables
        self.total_cost = 0.0
        self.total_tokens = 0
        self.logged_calls: List[Dict[str, Any]] = []
        self.is_active = False

        logger.info(f"🔍 Audit session created: {self.session_id}")

    async def start(self, db_worker: DatabaseWorker):
        """Start the audit session."""
        self.is_active = True

        # Queue session start in database
        db_worker.queue_operation(
            "start_session",
            {
                "session_id": self.session_id,
                "session_type": self.session_type,
                "user_id": self.user_id,
                "start_time": self.start_time,
            },
        )

        logger.info(f"✅ Session started: {self.session_id}")
        return self.session_id

    def track_api_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        phase: str = "unknown",
        agent_role: str = "unknown",
        cost: Optional[float] = None,
        db_worker: Optional[DatabaseWorker] = None,
    ):
        """Track an API call."""
        # Allow tracking even if session not formally started (for backward compatibility)
        if not self.is_active:
            logger.debug(
                "Session not formally started - auto-activating for API call tracking"
            )
            self.is_active = True

        # Calculate cost if not provided
        if cost is None:
            costs = CostCalculator.calculate_cost(model, input_tokens, output_tokens)
            estimated_cost = costs["total_cost"]
        else:
            estimated_cost = cost

        # Update session totals
        total_tokens = input_tokens + output_tokens
        self.total_cost += estimated_cost
        self.total_tokens += total_tokens

        # Create call record
        call_data = {
            "call_id": str(uuid.uuid4()),
            "session_id": self.session_id,
            "model": model,
            "phase": phase,
            "agent_role": agent_role,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost": estimated_cost,
            "timestamp": datetime.now(),
        }

        # Store in memory
        self.logged_calls.append(call_data)

        # Queue for database logging
        if db_worker:
            db_worker.queue_operation("log_call", call_data)

        logger.info(
            f"💰 API Call: {model} ({phase}) [{agent_role}] - ${estimated_cost:.4f}"
        )

    async def update_blog_id(self, blog_id: str, db_worker: DatabaseWorker):
        """Update the blog ID for this session."""
        self.blog_id = blog_id

        db_worker.queue_operation(
            "update_blog_id", {"session_id": self.session_id, "blog_id": blog_id}
        )

        logger.info(f"📝 Blog ID updated: {blog_id}")

    async def end(self, db_worker: DatabaseWorker):
        """End the audit session."""
        if not self.is_active:
            return

        self.is_active = False
        end_time = datetime.now()

        # Queue session end in database
        db_worker.queue_operation(
            "end_session",
            {
                "session_id": self.session_id,
                "end_time": end_time,
                "total_cost": self.total_cost,
                "total_tokens": self.total_tokens,
                "input_tokens": sum(call["input_tokens"] for call in self.logged_calls),
                "output_tokens": sum(
                    call["output_tokens"] for call in self.logged_calls
                ),
                "call_count": len(self.logged_calls),
            },
        )

        logger.info(f"🔚 Session ended: {self.session_id}")
        logger.info(f"   Total cost: ${self.total_cost:.4f}")
        logger.info(f"   Total tokens: {self.total_tokens}")
        logger.info(f"   Total calls: {len(self.logged_calls)}")

    def get_summary(self) -> Dict[str, Any]:
        """Get session summary."""
        return {
            "session_id": self.session_id,
            "session_type": self.session_type,
            "user_id": self.user_id,
            "blog_id": self.blog_id,
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
            "call_count": len(self.logged_calls),
            "is_active": self.is_active,
            "start_time": self.start_time,
            "logged_calls": self.logged_calls,
        }
