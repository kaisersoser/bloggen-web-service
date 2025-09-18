"""
CrewAI Stdout Capture Utility

Captures and parses CrewAI's verbose output to extract agent activities,
tool usage, thinking processes, and image tool operations for real-time SSE notifications.
"""

import sys
import re
import threading
from contextlib import contextmanager
from io import StringIO
from typing import Callable, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class CrewAIOutputParser:
    """Parses CrewAI verbose output for meaningful agent activities and tool operations"""
    
    def __init__(self, callback: Callable[[Dict[str, Any]], None]):
        self.callback = callback
        
        # Regex patterns for different CrewAI output types
        self.patterns = {
            'agent_thinking': re.compile(r'\[(\w+\s*\w*)\]\s*(.+)'),
            'tool_usage': re.compile(r'Action:\s*(.+?)(?:\n|$)'),
            'tool_input': re.compile(r'Action Input:\s*(.+?)(?:\n|$)'),
            'observation': re.compile(r'Observation:\s*(.+?)(?:\n|$)'),
            'final_answer': re.compile(r'Final Answer:\s*(.+?)(?:\n|$)'),
            'delegation': re.compile(r'I need to delegate this task to (.+?)'),
            'error': re.compile(r'Error:\s*(.+?)(?:\n|$)'),
            
            # Consumer-meaningful image events only
            'image_source_fallback': re.compile(r'All Unsplash images failed relevance check.*triggering AI fallback', re.IGNORECASE),
            'image_auto_enhancement': re.compile(r'Blog has insufficient images.*adding (\d+) images?', re.IGNORECASE),
            'unsplash_search': re.compile(r'Searching Unsplash for:\s*[\'"](.+?)[\'"]', re.IGNORECASE),
            'images_found': re.compile(r'Successfully found (\d+).*?images?.*Unsplash', re.IGNORECASE),
            'ai_image_generated': re.compile(r'AI image generation.*completed|Generated AI image', re.IGNORECASE),
            'image_storage_complete': re.compile(r'Image stored permanently in S3:\s*(.+)', re.IGNORECASE),
            'hero_image_selected': re.compile(r'Hero image.*selected.*(?:Unsplash|AI)', re.IGNORECASE),
        }
    
    def parse_line(self, line: str) -> None:
        """Parse a single line of CrewAI output and extract meaningful events"""
        line = line.strip()
        if not line:
            return
            
        # Check for image-related events first (high priority)
        if self._check_image_events(line):
            return
            
        # Check for agent thinking patterns
        if match := self.patterns['agent_thinking'].search(line):
            agent_name = match.group(1).strip()
            thought = match.group(2).strip()
            self._emit_event('agent_thinking', {
                'agent_name': agent_name,
                'thought': thought
            })
            return
        # Check for tool usage
        elif match := self.patterns['tool_usage'].search(line):
            tool_name = match.group(1).strip()
            self._emit_event('tool_usage', {
                'tool_name': tool_name,
                'status': 'started'
            })
            
        # Check for tool input
        elif match := self.patterns['tool_input'].search(line):
            tool_input = match.group(1).strip()
            self._emit_event('tool_input', {
                'input': tool_input
            })
            
        # Check for observations (tool results)
        elif match := self.patterns['observation'].search(line):
            observation = match.group(1).strip()
            self._emit_event('observation', {
                'result': observation
            })
            
        # Check for final answers
        elif match := self.patterns['final_answer'].search(line):
            answer = match.group(1).strip()
            self._emit_event('final_answer', {
                'answer': answer
            })
            
        # Check for task delegation
        elif match := self.patterns['delegation'].search(line):
            delegate_to = match.group(1).strip()
            self._emit_event('delegation', {
                'delegate_to': delegate_to
            })
            
        # Check for errors
        elif match := self.patterns['error'].search(line):
            error = match.group(1).strip()
            self._emit_event('error', {
                'error': error
            })
    
    def _check_image_events(self, line: str) -> bool:
        """Check for consumer-meaningful image-related events"""
        
        # Image source fallback decision (key consumer insight)
        if self.patterns['image_source_fallback'].search(line):
            self._emit_event('image_source_fallback', {
                'message': 'Switched from Unsplash to AI generation for better image relevance',
                'previous_source': 'unsplash',
                'new_source': 'ai_generation',
                'reason': 'relevance_check_failed'
            })
            return True
            
        # Automatic image enhancement (consumer action)
        if match := self.patterns['image_auto_enhancement'].search(line):
            count = match.group(1).strip()
            self._emit_event('image_auto_enhancement', {
                'message': f'Adding {count} additional images to enhance blog content',
                'images_added': int(count),
                'reason': 'insufficient_images'
            })
            return True
            
        # Unsplash search attempt (user-relevant search activity)
        if match := self.patterns['unsplash_search'].search(line):
            query = match.group(1).strip()
            self._emit_event('image_search_attempt', {
                'message': f'Searching for images related to: {query}',
                'query': query,
                'source': 'unsplash'
            })
            return True
            
        # Images successfully found (positive outcome)
        if match := self.patterns['images_found'].search(line):
            count = match.group(1).strip()
            self._emit_event('images_found', {
                'message': f'Found {count} relevant images from Unsplash',
                'count': int(count),
                'source': 'unsplash'
            })
            return True
            
        # AI image generation completed (alternative source success)
        if self.patterns['ai_image_generated'].search(line):
            self._emit_event('ai_image_generated', {
                'message': 'AI generated custom image for your blog',
                'source': 'ai_generation',
                'quality': 'high'
            })
            return True
            
        # Image storage completion (final step users care about)
        if match := self.patterns['image_storage_complete'].search(line):
            storage_info = match.group(1).strip()
            self._emit_event('image_storage_complete', {
                'message': 'Images securely stored and ready for use',
                'storage': 's3',
                'status': 'permanent'
            })
            return True
            
        # Hero image selection (main visual decision)
        if self.patterns['hero_image_selected'].search(line):
            # Determine source from line content
            source = 'ai' if 'AI' in line else 'unsplash'
            self._emit_event('hero_image_selected', {
                'message': f'Hero image selected from {source.title()}',
                'type': 'hero',
                'source': source
            })
            return True
        
        return False
    
    def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit a parsed event via callback"""
        try:
            event = {
                'type': event_type,
                'data': data,
                'source': 'crewai_stdout'
            }
            self.callback(event)
        except Exception as e:
            logger.error(f"Error emitting CrewAI event: {e}")


class LoggingCapture(logging.Handler):
    """Custom logging handler to capture logging output from image tools"""
    
    def __init__(self, parser: CrewAIOutputParser):
        super().__init__()
        self.parser = parser
        
    def emit(self, record: logging.LogRecord) -> None:
        """Process logging records and parse them for image events"""
        try:
            message = self.format(record)
            self.parser.parse_line(message)
        except Exception:
            pass  # Silently ignore logging capture errors


class EnhancedOutputCapture:
    """Context manager to capture both stdout and logging output in real-time"""
    
    def __init__(self, parser: CrewAIOutputParser):
        self.parser = parser
        self.original_stdout = None
        self.captured_output = StringIO()
        self.capture_thread = None
        self._stop_capture = threading.Event()
        self.logging_handler = LoggingCapture(parser)
        self.original_loggers = []
    
    def __enter__(self):
        # Capture stdout
        self.original_stdout = sys.stdout
        sys.stdout = self
        
        # Capture logging from image tools
        tool_loggers = [
            'bloggen.tools.unsplash_tool',
            'bloggen.tools.openai_image_tool',
            'root'  # Fallback for any other logging
        ]
        
        for logger_name in tool_loggers:
            tool_logger = logging.getLogger(logger_name)
            tool_logger.addHandler(self.logging_handler)
            self.original_loggers.append(tool_logger)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore stdout
        sys.stdout = self.original_stdout
        self._stop_capture.set()
        
        # Remove logging handlers
        for tool_logger in self.original_loggers:
            tool_logger.removeHandler(self.logging_handler)
    
    def write(self, text: str) -> int:
        """Intercept stdout writes and parse them"""
        # Write to original stdout for normal logging
        if self.original_stdout:
            self.original_stdout.write(text)
            self.original_stdout.flush()
        
        # Parse each line for CrewAI events
        for line in text.split('\n'):
            if line.strip():
                self.parser.parse_line(line)
        
        return len(text)
    
    def flush(self):
        """Flush stdout"""
        if self.original_stdout:
            self.original_stdout.flush()


class StdoutCapture:
    """Legacy stdout capture class - kept for backwards compatibility"""
    
    def __init__(self, parser: CrewAIOutputParser):
        self.parser = parser
        self.original_stdout = None
        self.captured_output = StringIO()
        self.capture_thread = None
        self._stop_capture = threading.Event()
    
    def __enter__(self):
        self.original_stdout = sys.stdout
        sys.stdout = self
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.original_stdout
        self._stop_capture.set()
    
    def write(self, text: str) -> int:
        """Intercept stdout writes and parse them"""
        # Write to original stdout for normal logging
        if self.original_stdout:
            self.original_stdout.write(text)
            self.original_stdout.flush()
        
        # Parse each line for CrewAI events
        for line in text.split('\n'):
            if line.strip():
                self.parser.parse_line(line)
        return len(text)
    
    def flush(self):
        """Flush stdout"""
        if self.original_stdout:
            self.original_stdout.flush()


@contextmanager
def capture_crewai_output(event_callback: Callable[[Dict[str, Any]], None]):
    """Context manager to capture and parse CrewAI output with enhanced logging support"""
    parser = CrewAIOutputParser(event_callback)
    capture = EnhancedOutputCapture(parser)
    
    try:
        with capture:
            yield
    except Exception as e:
        logger.error(f"Error in CrewAI enhanced capture: {e}")
        raise


@contextmanager  
def capture_crewai_output_legacy(event_callback: Callable[[Dict[str, Any]], None]):
    """Legacy context manager - stdout only capture"""
    parser = CrewAIOutputParser(event_callback)
    capture = StdoutCapture(parser)
    
    try:
        with capture:
            yield
    except Exception as e:
        logger.error(f"Error in CrewAI stdout capture: {e}")
        raise