#!/usr/bin/env python3
"""
Protocol configuration manager for easy HTTP/HTTPS switching.
"""

import os
from typing import Literal, Tuple, Union, Optional
import logging

logger = logging.getLogger(__name__)

class ProtocolConfig:
    """Centralized protocol configuration manager."""
    
    def __init__(self, config_file: Optional[str] = None):
        if config_file is None:
            # Calculate path relative to this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.config_file = os.path.join(current_dir, "../../../.env.protocol")
        else:
            self.config_file = config_file
        self._load_config()
    
    def _load_config(self):
        """Load configuration from .env.protocol file."""
        # Default values
        self.protocol_mode: str = "https"
        self.frontend_port = 3001
        self.frontend_host = "localhost"
        self.backend_port = 5000
        self.backend_host = "localhost"
        self.ssl_cert_path = "./certs/localhost.pem"
        self.ssl_key_path = "./certs/localhost-key.pem"
        
        # Try to load from file
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip().lower()
                            value = value.strip()
                            
                            if key == 'protocol_mode':
                                self.protocol_mode = value.lower() if value.lower() in ['http', 'https'] else 'https'
                            elif key == 'frontend_port':
                                self.frontend_port = int(value)
                            elif key == 'frontend_host':
                                self.frontend_host = value
                            elif key == 'backend_port':
                                self.backend_port = int(value)
                            elif key == 'backend_host':
                                self.backend_host = value
                            elif key == 'ssl_cert_path':
                                self.ssl_cert_path = value
                            elif key == 'ssl_key_path':
                                self.ssl_key_path = value
                                
            except Exception as e:
                logger.warning(f"Error loading protocol config: {e}, using defaults")
        
        logger.info(f"🔧 Protocol Config: {self.protocol_mode.upper()} mode")
        logger.info(f"   Frontend: {self.get_frontend_url()}")
        logger.info(f"   Backend: {self.get_backend_url()}")
    
    @property
    def is_https(self) -> bool:
        """Check if HTTPS mode is enabled."""
        return self.protocol_mode == "https"
    
    @property
    def protocol(self) -> str:
        """Get the protocol string (http or https)."""
        return self.protocol_mode
    
    def get_frontend_url(self) -> str:
        """Get the complete frontend URL."""
        return f"{self.protocol}://{self.frontend_host}:{self.frontend_port}"
    
    def get_backend_url(self) -> str:
        """Get the complete backend URL."""
        return f"{self.protocol}://{self.backend_host}:{self.backend_port}"
    
    def get_websocket_url(self) -> str:
        """Get the WebSocket URL (ws/wss based on protocol)."""
        ws_protocol = "wss" if self.is_https else "ws"
        return f"{ws_protocol}://{self.backend_host}:{self.backend_port}"
    
    def get_ssl_config(self) -> Union[Tuple[str, str], None]:
        """Get SSL certificate paths if HTTPS is enabled."""
        if self.is_https:
            return (self.ssl_cert_path, self.ssl_key_path)
        return None
    
    def get_cors_origins(self) -> list[str]:
        """Get CORS allowed origins."""
        origins = [
            self.get_frontend_url(),
            f"{self.protocol}://{self.frontend_host}",  # Without port
        ]
        
        # Add both protocols for development flexibility
        if self.protocol == "https":
            origins.extend([
                f"http://{self.frontend_host}:{self.frontend_port}",
                f"http://{self.frontend_host}"
            ])
        else:
            origins.extend([
                f"https://{self.frontend_host}:{self.frontend_port}",
                f"https://{self.frontend_host}"
            ])
        
        return origins

# Global instance
protocol_config = ProtocolConfig()

# Convenience functions
def get_protocol_config() -> ProtocolConfig:
    """Get the global protocol configuration."""
    return protocol_config

def is_https_mode() -> bool:
    """Check if HTTPS mode is enabled."""
    return protocol_config.is_https

def get_frontend_url() -> str:
    """Get the frontend URL."""
    return protocol_config.get_frontend_url()

def get_backend_url() -> str:
    """Get the backend URL."""
    return protocol_config.get_backend_url()

def get_websocket_url() -> str:
    """Get the WebSocket URL."""
    return protocol_config.get_websocket_url()
