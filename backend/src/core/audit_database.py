"""
Supabase/Prisma Database Integration for Audit Logging

Integrates with the existing Supabase database and Prisma schema
for persistent audit logging of LLM costs and usage patterns.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import httpx
from dataclasses import dataclass

from core.common import get_logger, config
from core.database_config import db_config

logger = get_logger(__name__)


@dataclass
class DatabaseAuditConfig:
    """Configuration for Supabase database audit system"""
    database_url: str
    enable_audit: bool = True
    timeout: int = 30


class SupabaseAuditManager:
    """
    Supabase database manager for audit logging system.
    
    Integrates with the existing Prisma schema and Supabase database
    for comprehensive audit logging.
    """
    
    def __init__(self, config_override: Optional[DatabaseAuditConfig] = None):
        """Initialize Supabase audit manager"""
        self.config = config_override or self._get_default_config()
        self.logger = get_logger(__name__)
        self.client = None
        
        if self.config.enable_audit:
            self._initialize_client()
    
    def _get_default_config(self) -> DatabaseAuditConfig:
        """Get default configuration from unified config"""
        # Use the existing database URL from config (Supabase)
        database_url = config.database.url
        
        return DatabaseAuditConfig(
            database_url=database_url,
            enable_audit=True
        )
    
    def _initialize_client(self):
        """Initialize HTTP client for database operations"""
        try:
            self.client = httpx.AsyncClient(timeout=self.config.timeout)
            self.logger.info("Supabase audit system initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize audit client: {str(e)}")
            self.config.enable_audit = False
    
    async def create_audit_session(
        self,
        session_type: str,
        user_id: str,
        blog_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Create new audit session using Next.js API.
        
        Returns:
            Session ID if successful, None if audit disabled
        """
        if not self.config.enable_audit:
            return None
        
        try:
            # Call the Next.js API endpoint for creating audit sessions
            frontend_url = config.security.nextauth_url
            api_url = f"{frontend_url}/api/audit/sessions"
            
            payload = {
                'sessionType': session_type,
                'userId': user_id,
                'blogId': blog_id,
                'startTime': datetime.utcnow().isoformat()
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(api_url, json=payload)
                
                if response.status_code == 201:
                    result = response.json()
                    session_id = result.get('id')
                    self.logger.info(f"Created audit session: {session_id} ({session_type})")
                    return session_id
                else:
                    self.logger.warning(f"Failed to create audit session: {response.status_code}")
                    return None
            
        except Exception as e:
            self.logger.error(f"Failed to create audit session: {str(e)}")
            return None
    
    async def log_llm_call(
        self,
        session_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        total_cost: float,
        phase: Optional[str] = None,
        agent_role: Optional[str] = None,
        call_type: str = 'estimated'
    ) -> Optional[str]:
        """
        Log individual LLM call using Next.js API.
        
        Returns:
            Call ID if successful, None if failed
        """
        if not self.config.enable_audit:
            return None
        
        try:
            # Calculate individual costs
            try:
                from bloggen.constants import OPENAI_PRICING
            except ImportError:
                # Fallback pricing if constants not available
                OPENAI_PRICING = {
                    'gpt-4': {'input': 0.03, 'output': 0.06},
                    'gpt-3.5-turbo': {'input': 0.001, 'output': 0.002}
                }
            
            pricing = OPENAI_PRICING.get(model, OPENAI_PRICING['gpt-3.5-turbo'])
            input_cost = (input_tokens / 1000) * pricing['input']
            output_cost = (output_tokens / 1000) * pricing['output']
            
            # Call the Next.js API endpoint for logging LLM calls
            frontend_url = config.security.nextauth_url
            api_url = f"{frontend_url}/api/audit/sessions/{session_id}/llm-calls"
            
            payload = {
                'auditSessionId': session_id,
                'model': model,
                'inputTokens': input_tokens,
                'outputTokens': output_tokens,
                'inputCost': input_cost,
                'outputCost': output_cost,
                'totalCost': total_cost or (input_cost + output_cost),
                'phase': phase or 'unknown',
                'agentRole': agent_role or 'unknown',
                'callType': call_type
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(api_url, json=payload)
                
                if response.status_code == 201:
                    result = response.json()
                    call_id = result.get('id')
                    self.logger.debug(f"Logged LLM call: {call_id} (${total_cost:.4f})")
                    return call_id
                else:
                    self.logger.warning(f"Failed to log LLM call: {response.status_code}")
                    return None
            
        except Exception as e:
            self.logger.error(f"Failed to log LLM call: {str(e)}")
            return None
    
    async def complete_audit_session(
        self,
        session_id: str,
        status: str = 'completed'
    ) -> bool:
        """
        Complete audit session using Next.js API.
        
        Returns:
            True if successful, False if failed
        """
        if not self.config.enable_audit:
            return False
        
        try:
            # Call the Next.js API endpoint for completing audit sessions
            frontend_url = config.security.nextauth_url
            api_url = f"{frontend_url}/api/audit/sessions/{session_id}/complete"
            
            payload = {
                'endTime': datetime.utcnow().isoformat(),
                'status': status
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.patch(api_url, json=payload)
                
                if response.status_code == 200:
                    self.logger.info(f"Completed audit session: {session_id}")
                    return True
                else:
                    self.logger.warning(f"Failed to complete audit session: {response.status_code}")
                    return False
            
        except Exception as e:
            self.logger.error(f"Failed to complete audit session: {str(e)}")
            return False
    
    async def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get audit session summary using Next.js API"""
        if not self.config.enable_audit:
            return None
        
        try:
            frontend_url = config.security.nextauth_url
            api_url = f"{frontend_url}/api/audit/sessions/{session_id}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(api_url)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    self.logger.warning(f"Failed to get session summary: {response.status_code}")
                    return None
            
        except Exception as e:
            self.logger.error(f"Failed to get session summary: {str(e)}")
            return None
    
    async def get_user_cost_summary(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get cost summary for specific user using Next.js API"""
        if not self.config.enable_audit:
            return {'total_cost': 0, 'session_count': 0, 'total_tokens': 0}
        
        try:
            frontend_url = config.security.nextauth_url
            api_url = f"{frontend_url}/api/audit/users/{user_id}/summary"
            
            params = {}
            if start_date:
                params['startDate'] = start_date.isoformat()
            if end_date:
                params['endDate'] = end_date.isoformat()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(api_url, params=params)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    self.logger.warning(f"Failed to get user cost summary: {response.status_code}")
                    return {'total_cost': 0, 'session_count': 0, 'total_tokens': 0}
            
        except Exception as e:
            self.logger.error(f"Failed to get user cost summary: {str(e)}")
            return {'total_cost': 0, 'session_count': 0, 'total_tokens': 0}


# Global audit manager instance
audit_manager = SupabaseAuditManager()

# Async convenience functions for API compatibility
async def create_audit_session(session_type: str, user_id: str, blog_id: Optional[str] = None) -> Optional[str]:
    """Create new audit session - async convenience function"""
    return await audit_manager.create_audit_session(session_type, user_id, blog_id)

async def log_llm_call(session_id: str, model: str, input_tokens: int, output_tokens: int, total_cost: float, **kwargs) -> Optional[str]:
    """Log LLM call - async convenience function"""
    return await audit_manager.log_llm_call(session_id, model, input_tokens, output_tokens, total_cost, **kwargs)

async def complete_audit_session(session_id: str, status: str = 'completed') -> bool:
    """Complete audit session - async convenience function"""
    return await audit_manager.complete_audit_session(session_id, status)


# Export key items
__all__ = [
    'SupabaseAuditManager', 'audit_manager',
    'create_audit_session', 'log_llm_call', 'complete_audit_session'
]
