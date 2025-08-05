"""
Import Organization and Common Utilities

Provides commonly used imports and utilities to reduce repetitive import statements
across the codebase.
"""

# Standard library imports (commonly used)
import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager
import asyncio
import threading
import uuid

# Third-party imports (commonly used)
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import jwt
    HAS_JWT = True
except ImportError:
    HAS_JWT = False

try:
    from flask import Flask, request, jsonify, Response
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

# Core utilities (our own)
from core.config import config
from core.logging_utils import get_logger, setup_api_logger, setup_cost_tracking_logger
from core.error_handling import (
    BlogGenError, 
    APIError, 
    ConfigurationError, 
    AuthenticationError,
    handle_api_errors,
    handle_cost_tracking_errors,
    create_error_response
)
from core.env_validation import validate_env, get_env_summary
from core.database_config import db_config, get_chroma_db_path, get_database_summary

# Common type aliases
StrDict = Dict[str, str]
AnyDict = Dict[str, Any]
StrList = List[str]
OptionalStr = Optional[str]
OptionalInt = Optional[int]

# Common constants
DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3
DEFAULT_PAGE_SIZE = 20
MAX_CONTENT_LENGTH = 1024 * 1024  # 1MB

# Common decorators and context managers
@contextmanager
def timer(operation_name: str = "Operation"):
    """Context manager to time operations"""
    logger = get_logger(__name__)
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.debug(f"{operation_name} completed in {duration:.2f} seconds")

@contextmanager
def error_context(operation_name: str, fallback_value: Any = None):
    """Context manager for safe operation execution"""
    logger = get_logger(__name__)
    try:
        yield
    except Exception as e:
        logger.error(f"{operation_name} failed: {str(e)}")
        if fallback_value is not None:
            return fallback_value
        raise

# Common utility functions
def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to integer"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_bool(value: Any, default: bool = False) -> bool:
    """Safely convert value to boolean"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    return bool(value) if value is not None else default

def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate string to maximum length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def format_timestamp(dt: Optional[datetime] = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format timestamp with default format"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime(format_str)

def generate_id(prefix: str = "", length: int = 8) -> str:
    """Generate a unique ID with optional prefix"""
    unique_id = str(uuid.uuid4())[:length]
    return f"{prefix}{unique_id}" if prefix else unique_id

def ensure_directory(path: Union[str, Path]) -> Path:
    """Ensure directory exists, create if necessary"""
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj

def get_file_size(file_path: Union[str, Path]) -> int:
    """Get file size in bytes, return 0 if file doesn't exist"""
    try:
        return Path(file_path).stat().st_size
    except (OSError, FileNotFoundError):
        return 0

def is_valid_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe filesystem usage"""
    import re
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove multiple underscores
    sanitized = re.sub(r'_{2,}', '_', sanitized)
    # Remove leading/trailing underscores and dots
    sanitized = sanitized.strip('_.')
    return sanitized or 'unnamed_file'

def deep_merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Deep merge two dictionaries"""
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    return result

class SimpleCache:
    """Simple in-memory cache with TTL support"""
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self.default_ttl = default_ttl
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cache value with TTL"""
        ttl = ttl or self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)
        self._cache[key] = (value, expires_at)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get cache value, return default if expired or missing"""
        if key not in self._cache:
            return default
        
        value, expires_at = self._cache[key]
        if datetime.now() > expires_at:
            del self._cache[key]
            return default
        
        return value
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """Remove expired entries, return count removed"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, expires_at) in self._cache.items()
            if now > expires_at
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)


# Global cache instance
cache = SimpleCache()

# Export commonly used items for easy imports
__all__ = [
    # Standard library
    'os', 'sys', 'time', 'logging', 'Path', 'datetime', 'timedelta',
    'Dict', 'List', 'Optional', 'Any', 'Union', 'Tuple',
    'dataclass', 'field', 'contextmanager', 'asyncio', 'threading', 'uuid',
    
    # Third-party (conditional)
    'requests', 'jwt', 'Flask', 'request', 'jsonify', 'Response',
    'HAS_REQUESTS', 'HAS_JWT', 'HAS_FLASK',
    
    # Core utilities
    'config', 'get_logger', 'setup_api_logger', 'setup_cost_tracking_logger',
    'BlogGenError', 'APIError', 'ConfigurationError', 'AuthenticationError',
    'handle_api_errors', 'handle_cost_tracking_errors', 'create_error_response',
    'validate_env', 'get_env_summary', 'db_config', 'get_chroma_db_path', 'get_database_summary',
    
    # Type aliases
    'StrDict', 'AnyDict', 'StrList', 'OptionalStr', 'OptionalInt',
    
    # Constants
    'DEFAULT_TIMEOUT', 'DEFAULT_RETRIES', 'DEFAULT_PAGE_SIZE', 'MAX_CONTENT_LENGTH',
    
    # Utilities
    'timer', 'error_context', 'safe_int', 'safe_float', 'safe_bool',
    'truncate_string', 'format_timestamp', 'generate_id', 'ensure_directory',
    'get_file_size', 'is_valid_email', 'sanitize_filename', 'deep_merge_dicts',
    'SimpleCache', 'cache'
]
