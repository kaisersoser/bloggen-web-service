"""
Standardized Error Handling Framework

Provides decorators and utilities for consistent error handling across the application.
"""

import functools
import traceback
from typing import Callable, Any, Dict, Optional, Union
from datetime import datetime

from core.logging_utils import get_logger


class BlogGenError(Exception):
    """Base exception for blog generation errors"""

    def __init__(
        self,
        message: str,
        error_code: str = "GENERAL_ERROR",
        details: Optional[Dict] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now()
        super().__init__(message)


class ConfigurationError(BlogGenError):
    """Configuration-related errors"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, "CONFIG_ERROR", details)


class APIError(BlogGenError):
    """External API-related errors"""

    def __init__(self, message: str, api_name: str, details: Optional[Dict] = None):
        details = details or {}
        details["api_name"] = api_name
        super().__init__(message, "API_ERROR", details)


class AuthenticationError(BlogGenError):
    """Authentication-related errors"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, "AUTH_ERROR", details)


class ValidationError(BlogGenError):
    """Input validation errors"""

    def __init__(self, message: str, field: str, details: Optional[Dict] = None):
        details = details or {}
        details["field"] = field
        super().__init__(message, "VALIDATION_ERROR", details)


def handle_api_errors(
    error_message: str = "API operation failed",
    logger_name: Optional[str] = None,
    return_none_on_error: bool = False,
):
    """
    Decorator for standardized API error handling

    Args:
        error_message: Default error message for exceptions
        logger_name: Name for logger (defaults to function module)
        return_none_on_error: Whether to return None instead of raising
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name or func.__module__)

            try:
                return func(*args, **kwargs)
            except BlogGenError:
                # Re-raise our custom exceptions
                raise
            except Exception as e:
                error_details = {
                    "function": func.__name__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys()),
                    "exception_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                }

                logger.error(f"{error_message}: {str(e)}", extra=error_details)

                if return_none_on_error:
                    return None

                raise APIError(f"{error_message}: {str(e)}", "unknown", error_details)

        return wrapper

    return decorator


def handle_cost_tracking_errors(
    fallback_value: Any = None, logger_name: Optional[str] = None
):
    """
    Decorator for cost tracking operations that should not fail the main process

    Args:
        fallback_value: Value to return on error
        logger_name: Name for logger
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name or func.__module__)

            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"Cost tracking operation failed in {func.__name__}: {str(e)}",
                    extra={"exception_type": type(e).__name__},
                )
                return fallback_value

        return wrapper

    return decorator


def handle_flow_errors(phase_name: str, logger_name: Optional[str] = None):
    """
    Decorator for CrewAI flow error handling

    Args:
        phase_name: Name of the flow phase for context
        logger_name: Name for logger
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name or func.__module__)

            try:
                logger.info(f"Starting {phase_name} phase")
                result = func(*args, **kwargs)
                logger.info(f"Completed {phase_name} phase successfully")
                return result
            except Exception as e:
                error_details = {
                    "phase": phase_name,
                    "function": func.__name__,
                    "exception_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                }

                logger.error(
                    f"Failed in {phase_name} phase: {str(e)}", extra=error_details
                )
                raise BlogGenError(
                    f"Flow failed in {phase_name}: {str(e)}",
                    "FLOW_ERROR",
                    error_details,
                )

        return wrapper

    return decorator


def create_error_response(
    error: Union[Exception, BlogGenError], include_traceback: bool = False
) -> Dict[str, Any]:
    """
    Create standardized error response for API endpoints

    Args:
        error: Exception instance
        include_traceback: Whether to include full traceback (for debugging)

    Returns:
        Standardized error response dictionary
    """
    if isinstance(error, BlogGenError):
        response = {
            "error": True,
            "message": error.message,
            "error_code": error.error_code,
            "timestamp": error.timestamp.isoformat(),
            "details": error.details,
        }
    else:
        response = {
            "error": True,
            "message": str(error),
            "error_code": "UNEXPECTED_ERROR",
            "timestamp": datetime.now().isoformat(),
            "details": {"exception_type": type(error).__name__},
        }

    if include_traceback:
        response["traceback"] = traceback.format_exc()

    return response


def validate_required_config(config_keys: Dict[str, Any]) -> None:
    """
    Validate that required configuration is present

    Args:
        config_keys: Dictionary of config key names to values

    Raises:
        ConfigurationError: If required config is missing
    """
    missing_keys = [key for key, value in config_keys.items() if not value]

    if missing_keys:
        raise ConfigurationError(
            f"Missing required configuration: {', '.join(missing_keys)}",
            details={"missing_keys": missing_keys},
        )


def safe_execute(
    func: Callable,
    *args,
    fallback_value: Any = None,
    error_message: str = "Operation failed",
    logger_name: Optional[str] = None,
    **kwargs,
) -> Any:
    """
    Safely execute a function with error handling

    Args:
        func: Function to execute
        *args: Positional arguments for function
        fallback_value: Value to return on error
        error_message: Error message for logging
        logger_name: Logger name
        **kwargs: Keyword arguments for function

    Returns:
        Function result or fallback value on error
    """
    logger = get_logger(logger_name or func.__module__)

    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.warning(f"{error_message}: {str(e)}")
        return fallback_value
