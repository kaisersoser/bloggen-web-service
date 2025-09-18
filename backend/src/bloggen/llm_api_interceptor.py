"""
LLM API Call Interceptor - Monitor actual API calls made by CrewAI agents
"""
import functools
import json
import logging
from typing import Any, Callable, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class LLMAPIInterceptor:
    """Intercepts LLM API calls to provide real-time visibility into agent conversations"""
    
    def __init__(self, event_callback: Callable[[Dict[str, Any]], None]):
        self.event_callback = event_callback
        self.call_counter = 0
        self.active_phase = "unknown"
        
    def set_active_phase(self, phase_name: str):
        """Set the current phase for context"""
        self.active_phase = phase_name
    
    def create_openai_interceptor(self):
        """Create an interceptor for OpenAI API calls"""
        try:
            import openai
            
            # Store original methods
            original_create = openai.chat.completions.create
            
            @functools.wraps(original_create)
            def intercepted_create(*args, **kwargs):
                return self._intercept_api_call(original_create, *args, **kwargs)
            
            # Monkey patch the OpenAI client
            openai.chat.completions.create = intercepted_create
            
            logger.info("🔧 OpenAI API interceptor installed successfully")
            
            return {
                'restore': lambda: self._restore_openai_methods(openai, original_create)
            }
            
        except ImportError:
            logger.warning("OpenAI not available for interception")
            return {'restore': lambda: None}
        except Exception as e:
            logger.error(f"Failed to install OpenAI interceptor: {e}")
            return {'restore': lambda: None}
    
    def _restore_openai_methods(self, openai, original_create):
        """Restore original OpenAI methods"""
        try:
            openai.chat.completions.create = original_create
            logger.info("🔧 OpenAI API interceptor removed")
        except Exception as e:
            logger.error(f"Error restoring OpenAI methods: {e}")
    
    def _intercept_api_call(self, original_method, *args, **kwargs):
        """Intercept synchronous API calls"""
        self.call_counter += 1
        call_id = f"call_{self.call_counter}"
        
        # Extract key information from the call
        call_info = self._extract_call_info(args, kwargs, call_id)
        
        # Send pre-call event
        self._emit_event({
            'type': 'llm_call_start',
            'call_id': call_id,
            'phase': self.active_phase,
            'model': call_info.get('model', 'unknown'),
            'messages_count': call_info.get('messages_count', 0),
            'estimated_tokens': call_info.get('estimated_tokens', 0),
            'timestamp': self._get_timestamp()
        })
        
        try:
            # Make the actual API call
            response = original_method(*args, **kwargs)
            
            # Extract response information
            response_info = self._extract_response_info(response)
            
            # Send post-call event
            self._emit_event({
                'type': 'llm_call_complete',
                'call_id': call_id,
                'phase': self.active_phase,
                'usage': response_info.get('usage', {}),
                'response_preview': response_info.get('content_preview', ''),
                'timestamp': self._get_timestamp()
            })
            
            # Send agent response event (simulate agent thinking)
            if response_info.get('content_preview'):
                self._emit_event({
                    'type': 'agent_response',
                    'call_id': call_id,
                    'phase': self.active_phase,
                    'agent_name': f"{self.active_phase.title()} Agent",
                    'response': response_info['content_preview'],
                    'timestamp': self._get_timestamp()
                })
            
            return response
            
        except Exception as e:
            # Send error event
            self._emit_event({
                'type': 'llm_call_error',
                'call_id': call_id,
                'phase': self.active_phase,
                'error': str(e),
                'timestamp': self._get_timestamp()
            })
            raise
    
    async def _intercept_async_api_call(self, original_method, *args, **kwargs):
        """Intercept asynchronous API calls"""
        self.call_counter += 1
        call_id = f"async_call_{self.call_counter}"
        
        call_info = self._extract_call_info(args, kwargs, call_id)
        
        self._emit_event({
            'type': 'llm_call_start',
            'call_id': call_id,
            'phase': self.active_phase,
            'model': call_info.get('model', 'unknown'),
            'messages_count': call_info.get('messages_count', 0),
            'estimated_tokens': call_info.get('estimated_tokens', 0),
            'timestamp': self._get_timestamp()
        })
        
        try:
            response = await original_method(*args, **kwargs)
            response_info = self._extract_response_info(response)
            
            self._emit_event({
                'type': 'llm_call_complete',
                'call_id': call_id,
                'phase': self.active_phase,
                'usage': response_info.get('usage', {}),
                'response_preview': response_info.get('content_preview', ''),
                'timestamp': self._get_timestamp()
            })
            
            if response_info.get('content_preview'):
                self._emit_event({
                    'type': 'agent_response',
                    'call_id': call_id,
                    'phase': self.active_phase,
                    'agent_name': f"{self.active_phase.title()} Agent",
                    'response': response_info['content_preview'],
                    'timestamp': self._get_timestamp()
                })
            
            return response
            
        except Exception as e:
            self._emit_event({
                'type': 'llm_call_error',
                'call_id': call_id,
                'phase': self.active_phase,
                'error': str(e),
                'timestamp': self._get_timestamp()
            })
            raise
    
    def _extract_call_info(self, args, kwargs, call_id: str) -> Dict[str, Any]:
        """Extract information from API call parameters"""
        try:
            # Get model
            model = kwargs.get('model', 'unknown')
            
            # Get messages
            messages = kwargs.get('messages', [])
            messages_count = len(messages)
            
            # Estimate tokens (rough approximation)
            estimated_tokens = 0
            for message in messages:
                content = message.get('content', '')
                if isinstance(content, str):
                    estimated_tokens += len(content.split()) * 1.3  # Rough token estimation
            
            return {
                'model': model,
                'messages_count': messages_count,
                'estimated_tokens': int(estimated_tokens),
                'messages_preview': [msg.get('content', '')[:100] for msg in messages[-2:]]  # Last 2 messages preview
            }
            
        except Exception as e:
            logger.warning(f"Error extracting call info: {e}")
            return {}
    
    def _extract_response_info(self, response) -> Dict[str, Any]:
        """Extract information from API response"""
        try:
            # Handle different response formats
            if hasattr(response, 'choices') and response.choices:
                choice = response.choices[0]
                if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                    content = choice.message.content
                elif hasattr(choice, 'text'):
                    content = choice.text
                else:
                    content = str(choice)
            else:
                content = str(response)
            
            # Get usage information
            usage = {}
            if hasattr(response, 'usage'):
                usage = {
                    'prompt_tokens': getattr(response.usage, 'prompt_tokens', 0),
                    'completion_tokens': getattr(response.usage, 'completion_tokens', 0),
                    'total_tokens': getattr(response.usage, 'total_tokens', 0)
                }
            
            return {
                'content_preview': content[:300] if content else '',  # First 300 chars
                'usage': usage
            }
            
        except Exception as e:
            logger.warning(f"Error extracting response info: {e}")
            return {}
    
    def _emit_event(self, event: Dict[str, Any]):
        """Emit an event to the callback"""
        try:
            self.event_callback(event)
        except Exception as e:
            logger.error(f"Error emitting event: {e}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.utcnow().isoformat()


class CrewAILLMInterceptorWrapper:
    """High-level wrapper that combines LLM interception with CrewAI execution"""
    
    def __init__(self, status_callback: Optional[Callable] = None):
        self.status_callback = status_callback
        self.llm_interceptor = LLMAPIInterceptor(self._handle_llm_event)
        self.current_phase = "unknown"
        self.interceptor_handle = None
    
    def execute_crew_with_llm_visibility(self, crew, phase_name: str = "crew_execution"):
        """Execute CrewAI crew with LLM API call interception"""
        self.current_phase = phase_name
        self.llm_interceptor.set_active_phase(phase_name)
        
        # Install LLM interceptor
        self.interceptor_handle = self.llm_interceptor.create_openai_interceptor()
        
        logger.info(f"🔍 Starting CrewAI execution with LLM interception for phase: {phase_name}")
        
        try:
            # Send initial status
            self._send_status_update("Initializing AI agents...", 0)
            
            # Execute the crew - LLM calls will be intercepted
            result = crew.kickoff()
            
            # Send completion status
            self._send_status_update("AI execution completed", 100)
            
            return result
            
        finally:
            # Restore original LLM methods
            if self.interceptor_handle:
                self.interceptor_handle['restore']()
    
    def _handle_llm_event(self, event: Dict[str, Any]):
        """Handle intercepted LLM events and convert to status updates"""
        event_type = event.get('type')
        
        if event_type == 'llm_call_start':
            model = event.get('model', 'unknown')
            estimated_tokens = event.get('estimated_tokens', 0)
            agent_name = f"{self.current_phase.title()} Agent"
            self._send_agent_thinking(
                agent_name, 
                f"Thinking... (processing ~{estimated_tokens} tokens with {model})"
            )
        
        elif event_type == 'llm_call_complete':
            usage = event.get('usage', {})
            total_tokens = usage.get('total_tokens', 0)
            agent_name = f"{self.current_phase.title()} Agent"
            self._send_agent_thinking(
                agent_name,
                f"Generated response ({total_tokens} tokens used)"
            )
        
        elif event_type == 'agent_response':
            agent_name = event.get('agent_name', 'AI Agent')
            response = event.get('response', '')
            self._send_agent_thinking(
                agent_name,
                f"Response: {response[:200]}..." if len(response) > 200 else response
            )
        
        elif event_type == 'llm_call_error':
            error = event.get('error', 'Unknown error')
            agent_name = f"{self.current_phase.title()} Agent"
            self._send_agent_thinking(agent_name, f"Error: {error}")
        
        # Log all events for debugging
        logger.debug(f"LLM Event: {event}")
    
    def _send_status_update(self, message: str, progress: int):
        """Send status update via callback"""
        if self.status_callback:
            self.status_callback({
                'message_type': 'status',
                'message': message,
                'progress': progress,
                'current_step': self.current_phase,
                'timestamp': self._get_timestamp()
            })
    
    def _send_agent_thinking(self, agent_name: str, thought: str):
        """Send agent thinking update"""
        if self.status_callback:
            self.status_callback({
                'message_type': 'agentthinking',
                'agent_name': agent_name,
                'thought': thought,
                'timestamp': self._get_timestamp()
            })
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.utcnow().isoformat()