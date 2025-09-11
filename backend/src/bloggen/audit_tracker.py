"""
Enhanced Cost Tracking Module with Database Persistence

This module provides comprehensive audit tracking for blog generation,
storing all LLM calls and costs in the database for detailed analytics.

Features:
- Database persistence of all LLM calls and costs
- Audit sessions linked to blogs and users
- Admin analytics and reporting
- Cost tracking that persists even if blogs are deleted
"""

import os
import time
from typing import Dict, List, Optional, Any, Union
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio

# Import shared constants and utilities
from .constants import OPENAI_PRICING, calculate_openai_cost, normalize_model_name, DEFAULT_MODEL
from core.model_config import get_summary_model

# Import new core utilities
from core.logging_utils import setup_cost_tracking_logger
from core.error_handling import handle_cost_tracking_errors

# Database imports - will be available after schema migration
# For now, we'll use a simplified approach without direct Prisma dependency
try:
    import requests
    import json
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Requests not available - API communication disabled")

@dataclass
class LLMCallData:
    """Data class for individual LLM API calls"""
    model: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    phase: str
    agent_role: str
    call_type: str = "estimated"
    timestamp: Optional[datetime] = None

@dataclass
class AuditSessionData:
    """Data class for audit session summary"""
    session_type: str
    user_id: str
    blog_id: Optional[str] = None
    total_cost: float = 0.0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    call_count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class DatabaseCostTracker:
    """
    Enhanced cost tracker with database persistence for audit trails.
    
    This tracker stores all LLM calls and costs in the database,
    providing comprehensive audit trails and analytics capabilities.
    
    NOTE: Database functionality is currently disabled due to Prisma dependencies.
    This class provides console-based cost tracking as a fallback.
    """
    
    def __init__(self, session_type: str, user_id: str, blog_id: Optional[str] = None):
        self.session_type = session_type
        self.user_id = user_id
        self.blog_id = blog_id
        self.calls: List[LLMCallData] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.logger = setup_cost_tracking_logger(f"audit_{session_type}")
        self.audit_session_id: Optional[str] = None
        
        # Database connection disabled for now
        self.db_available = False
        
        print(f"🔍 DatabaseCostTracker initialized (console mode) for {session_type}")
        print(f"   User: {user_id}, Blog: {blog_id}")
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.start_time = datetime.now()
        self.audit_session_id = f"console_{int(self.start_time.timestamp())}"
        print(f"🚀 Starting audit session: {self.audit_session_id}")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self.end_time = datetime.now()
        self.print_cost_summary()
    
    @handle_cost_tracking_errors(fallback_value=None)
    async def estimate_crew_cost(self, crew_result: Any, phase_name: str, agent_count: int = 1, agent_role: str = "agent"):
        """Estimate cost and store in memory"""
        try:
            content_length = len(str(crew_result)) if crew_result else 0
            
            # Estimation logic
            estimated_input_tokens = 1000 * agent_count
            estimated_output_tokens = max(content_length // 4, 100)
            
            model = DEFAULT_MODEL
            input_cost, output_cost, total_cost, cached_cost = calculate_openai_cost(
                model, estimated_input_tokens, estimated_output_tokens
            )
            
            # Create call data
            call_data = LLMCallData(
                model=model,
                input_tokens=estimated_input_tokens,
                output_tokens=estimated_output_tokens,
                input_cost=input_cost,
                output_cost=output_cost,
                total_cost=total_cost,
                phase=phase_name,
                agent_role=agent_role,
                call_type="estimated",
                timestamp=datetime.now()
            )
            
            # Store in memory
            self.calls.append(call_data)
            
            print(f"💰 Estimated LLM Cost for {phase_name}: ${total_cost:.4f} "
                  f"(~{estimated_input_tokens + estimated_output_tokens} tokens)")
            
        except Exception as e:
            self.logger.error(f"Failed to estimate crew cost: {e}")
    
    @handle_cost_tracking_errors(fallback_value=None)
    async def estimate_title_generation_cost(self):
        """Estimate title generation cost"""
        try:
            estimated_input_tokens = 150
            estimated_output_tokens = 20
            model = get_summary_model()  # Use environment-configured model
            
            input_cost, output_cost, total_cost, cached_cost = calculate_openai_cost(
                model, estimated_input_tokens, estimated_output_tokens
            )
            
            call_data = LLMCallData(
                model=model,
                input_tokens=estimated_input_tokens,
                output_tokens=estimated_output_tokens,
                input_cost=input_cost,
                output_cost=output_cost,
                total_cost=total_cost,
                phase="title_generation",
                agent_role="title_generator",
                call_type="estimated",
                timestamp=datetime.now()
            )
            
            self.calls.append(call_data)
            print(f"💰 Title Generation Cost: ${total_cost:.4f}")
            
        except Exception as e:
            self.logger.error(f"Failed to estimate title generation cost: {e}")
    
    @handle_cost_tracking_errors(fallback_value=None)
    async def record_actual_usage(self, model: str, usage: Any, phase: str, agent_role: str = "agent"):
        """Record actual OpenAI API usage"""
        try:
            input_tokens = getattr(usage, 'prompt_tokens', 0)
            output_tokens = getattr(usage, 'completion_tokens', 0)
            
            input_cost, output_cost, total_cost, cached_cost = calculate_openai_cost(
                model, input_tokens, output_tokens
            )
            
            call_data = LLMCallData(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                input_cost=input_cost,
                output_cost=output_cost,
                total_cost=total_cost,
                phase=phase,
                agent_role=agent_role,
                call_type="actual",
                timestamp=datetime.now()
            )
            
            self.calls.append(call_data)
            
            print(f"💰 Actual LLM Call: {model} | "
                  f"Tokens: {input_tokens}+{output_tokens}={input_tokens+output_tokens} | "
                  f"Cost: ${total_cost:.4f}")
            
        except Exception as e:
            self.logger.error(f"Failed to record actual usage: {e}")
    
    def print_cost_summary(self):
        """Print cost summary to console"""
        if not self.calls:
            print("\n" + "="*60)
            print("📊 AUDIT SESSION COST SUMMARY")
            print("="*60)
            print("No LLM calls tracked.")
            print("="*60)
            return
        
        total_cost = sum(call.total_cost for call in self.calls)
        total_tokens = sum(call.input_tokens + call.output_tokens for call in self.calls)
        total_input_tokens = sum(call.input_tokens for call in self.calls)
        total_output_tokens = sum(call.output_tokens for call in self.calls)
        
        print("\n" + "="*60)
        print("📊 AUDIT SESSION COST SUMMARY")
        print("="*60)
        print(f"🆔 Session ID: {self.audit_session_id}")
        print(f"👤 User ID: {self.user_id}")
        print(f"📝 Blog ID: {self.blog_id or 'N/A'}")
        print(f"🔄 Session Type: {self.session_type}")
        print(f"💰 Total Cost: ${total_cost:.4f}")
        print(f"🔢 Total Tokens: {total_tokens:,}")
        print(f"   📥 Input: {total_input_tokens:,}")
        print(f"   📤 Output: {total_output_tokens:,}")
        print(f"📞 Total Calls: {len(self.calls)}")
        
        # Group by phase
        phase_costs = {}
        for call in self.calls:
            if call.phase not in phase_costs:
                phase_costs[call.phase] = {"cost": 0, "tokens": 0, "calls": 0}
            phase_costs[call.phase]["cost"] += call.total_cost
            phase_costs[call.phase]["tokens"] += call.input_tokens + call.output_tokens
            phase_costs[call.phase]["calls"] += 1
        
        if phase_costs:
            print("\n🔄 Cost by Phase:")
            for phase, data in phase_costs.items():
                print(f"   {phase}: ${data['cost']:.4f} ({data['tokens']:,} tokens, {data['calls']} calls)")
        
        print("="*60)


class AuditAnalytics:
    """
    Analytics service for cost tracking and audit data.
    Provides methods for admin dashboard analytics.
    
    NOTE: Database functionality is currently disabled due to Prisma dependencies.
    This class is a placeholder for future database-based analytics.
    """
    
    def __init__(self):
        self.logger = setup_cost_tracking_logger("analytics")
        print("🔍 AuditAnalytics initialized (console mode)")
    
    async def get_cost_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get cost trends over time - placeholder implementation"""
        self.logger.warning("Database not available for cost trends")
        return {
            "daily_costs": {},
            "phase_costs": {},
            "model_costs": {},
            "user_role_costs": {},
            "total_sessions": 0,
            "total_cost": 0,
            "date_range": {"from": "", "to": ""}
        }
    
    async def get_detailed_audit_data(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get detailed audit data with filters - placeholder implementation"""
        self.logger.warning("Database not available for detailed audit data")
        return []


# Backwards compatibility - keep the original CostTracker for non-async contexts
from .cost_tracker import CostTracker

# Global tracker for easy access
_global_db_tracker: Optional[DatabaseCostTracker] = None

async def create_audit_session(session_type: str, user_id: str, blog_id: Optional[str] = None) -> DatabaseCostTracker:
    """Create a new audit session for cost tracking"""
    global _global_db_tracker
    _global_db_tracker = DatabaseCostTracker(session_type, user_id, blog_id)
    return _global_db_tracker

def get_current_db_tracker() -> Optional[DatabaseCostTracker]:
    """Get the currently active database cost tracker"""
    global _global_db_tracker
    return _global_db_tracker
