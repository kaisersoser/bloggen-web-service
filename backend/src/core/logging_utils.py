"""
Centralized Logging Utilities

Provides standardized logger creation and configuration across the application.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """
    Create a standardized logger with consistent formatting

    Args:
        name: Logger name (typically __name__)
        level: Logging level (default: INFO)
        log_file: Optional file path for logging
        format_string: Custom format string

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Prevent duplicate handlers if logger already exists
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Default format with timestamp, level, name, and message
    if not format_string:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(format_string)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str, **kwargs) -> logging.Logger:
    """
    Convenience function to get a standardized logger

    Args:
        name: Logger name (typically __name__)
        **kwargs: Additional arguments passed to setup_logger

    Returns:
        Logger instance
    """
    return setup_logger(name, **kwargs)


def setup_cost_tracking_logger(module_name: str) -> logging.Logger:
    """
    Create a logger specifically for cost tracking modules

    Args:
        module_name: Name of the cost tracking module

    Returns:
        Configured logger for cost tracking
    """
    from core.config import config

    log_file = (
        config.paths.logs_dir / f"cost_tracking_{datetime.now().strftime('%Y%m%d')}.log"
    )

    return setup_logger(
        f"cost_tracking.{module_name}",
        level=logging.DEBUG,
        log_file=log_file,
        format_string="%(asctime)s - %(levelname)s - [%(name)s] - %(message)s",
    )


def setup_api_logger(endpoint_name: str) -> logging.Logger:
    """
    Create a logger specifically for API endpoints

    Args:
        endpoint_name: Name of the API endpoint

    Returns:
        Configured logger for API operations
    """
    from core.config import config

    log_file = config.paths.logs_dir / f"api_{datetime.now().strftime('%Y%m%d')}.log"

    return setup_logger(
        f"api.{endpoint_name}",
        level=logging.INFO,
        log_file=log_file,
        format_string="%(asctime)s - %(levelname)s - [API:%(name)s] - %(message)s",
    )


def setup_flow_logger(flow_name: str) -> logging.Logger:
    """
    Create a logger specifically for CrewAI flows

    Args:
        flow_name: Name of the flow

    Returns:
        Configured logger for flow operations
    """
    from core.config import config

    log_file = config.paths.logs_dir / f"flows_{datetime.now().strftime('%Y%m%d')}.log"

    return setup_logger(
        f"flows.{flow_name}",
        level=logging.DEBUG,
        log_file=log_file,
        format_string="%(asctime)s - %(levelname)s - [FLOW:%(name)s] - %(message)s",
    )
