"""
Status Update Manager for Blog Generation Flow

Handles status updates and progress tracking.
Follows Single Responsibility Principle - only manages status updates.
"""

from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class StatusUpdateManager:
    """Manages status updates and progress tracking for blog generation."""
    
    def __init__(self, status_callback: Optional[Callable] = None, total_steps: int = 4):
        self.status_callback = status_callback
        self.total_steps = total_steps
        self.current_step = 0
    
    def send_status_update(self, message: str, step: int, detail: Optional[str] = None):
        """Send a status update via callback function."""
        if self.status_callback:
            progress = min((step / self.total_steps), 1.0)
            
            status_data = {
                'status': 'processing',
                'message': message,
                'progress': progress,
                'step': step,
                'total_steps': self.total_steps,
                'timestamp': self._get_timestamp()
            }
            
            if detail:
                status_data['detail'] = detail
            
            try:
                self.status_callback(status_data)
                logger.debug(f"Status update sent: {message} (Step {step}/{self.total_steps})")
            except Exception as e:
                logger.error(f"Failed to send status update: {e}")
    
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
                    'message': f'Error: {error_message}',
                    'timestamp': self._get_timestamp()
                })
            except Exception as e:
                logger.error(f"Failed to send error update: {e}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for status updates."""
        from datetime import datetime
        return datetime.now().isoformat()
