"""
Enhanced Error Handling System for CrewAI Blog Generation

This module provides structured error handling with user-friendly messages,
technical details, and recovery suggestions for different types of errors.
"""

from datetime import datetime
from typing import Dict, List, Optional
import re


class ErrorType:
    """Error type constants for classification"""
    API_KEY = "api_key_error"
    RATE_LIMIT = "rate_limit_error"
    NETWORK = "network_error"
    VALIDATION = "validation_error"
    SYSTEM = "system_error"
    QUOTA_EXCEEDED = "quota_exceeded"
    TIMEOUT = "timeout_error"


class ErrorFormatter:
    """Formats errors into structured, user-friendly responses"""
    
    @staticmethod
    def format_error(error_type: str, technical_message: str, suggestions: Optional[List[str]] = None) -> Dict:
        """
        Format an error into a structured response with user-friendly message
        
        Args:
            error_type: Type of error (from ErrorType class)
            technical_message: Raw technical error message
            suggestions: Optional list of recovery suggestions
            
        Returns:
            Dictionary with formatted error information
        """
        return {
            "error_type": error_type,
            "user_message": ErrorFormatter._get_user_friendly_message(error_type),
            "technical_details": technical_message,
            "is_recoverable": ErrorFormatter._is_recoverable_error(error_type),
            "suggestions": suggestions or ErrorFormatter._get_default_suggestions(error_type),
            "timestamp": datetime.now().isoformat(),
            "severity": ErrorFormatter._get_error_severity(error_type)
        }
    
    @staticmethod
    def _get_user_friendly_message(error_type: str) -> str:
        """Get user-friendly error messages"""
        messages = {
            ErrorType.API_KEY: "There's an issue with the API configuration. Please check your API key settings.",
            ErrorType.RATE_LIMIT: "API rate limit reached. Please wait a moment and try again.",
            ErrorType.NETWORK: "Network connection issue. Please check your internet connection and try again.",
            ErrorType.VALIDATION: "Invalid input provided. Please check your request and try again.",
            ErrorType.SYSTEM: "An unexpected system error occurred. Please try again in a moment.",
            ErrorType.QUOTA_EXCEEDED: "API quota has been exceeded. Please check your account limits.",
            ErrorType.TIMEOUT: "The request took too long to complete. Please try again."
        }
        return messages.get(error_type, "An error occurred during blog generation. Please try again.")
    
    @staticmethod
    def _is_recoverable_error(error_type: str) -> bool:
        """Determine if an error is recoverable (user can retry)"""
        recoverable_errors = {
            ErrorType.RATE_LIMIT,
            ErrorType.NETWORK,
            ErrorType.TIMEOUT,
            ErrorType.SYSTEM
        }
        return error_type in recoverable_errors
    
    @staticmethod
    def _get_default_suggestions(error_type: str) -> List[str]:
        """Get default recovery suggestions for each error type"""
        suggestions = {
            ErrorType.API_KEY: [
                "Check your OpenAI API key in the configuration",
                "Verify your API key is valid and active",
                "Ensure your API key has the correct permissions",
                "Contact support if the issue persists"
            ],
            ErrorType.RATE_LIMIT: [
                "Wait a few minutes and try again",
                "Consider upgrading your API plan for higher limits",
                "Try again during off-peak hours"
            ],
            ErrorType.NETWORK: [
                "Check your internet connection",
                "Try again in a few moments",
                "Verify your firewall settings allow the connection"
            ],
            ErrorType.VALIDATION: [
                "Check your blog topic is not empty",
                "Ensure your input doesn't contain invalid characters",
                "Try with a different topic or shorter text"
            ],
            ErrorType.SYSTEM: [
                "Try again in a few moments",
                "Check system status",
                "Contact support if the issue persists"
            ],
            ErrorType.QUOTA_EXCEEDED: [
                "Check your API usage limits",
                "Upgrade your API plan for higher quotas",
                "Wait until your quota resets"
            ],
            ErrorType.TIMEOUT: [
                "Try again with a simpler topic",
                "Check your internet connection",
                "The system may be experiencing high load"
            ]
        }
        return suggestions.get(error_type, ["Try again in a few moments", "Contact support if the issue persists"])
    
    @staticmethod
    def _get_error_severity(error_type: str) -> str:
        """Get error severity level"""
        severity_map = {
            ErrorType.API_KEY: "high",
            ErrorType.QUOTA_EXCEEDED: "high",
            ErrorType.RATE_LIMIT: "medium",
            ErrorType.NETWORK: "medium",
            ErrorType.TIMEOUT: "medium",
            ErrorType.VALIDATION: "low",
            ErrorType.SYSTEM: "high"
        }
        return severity_map.get(error_type, "medium")


def classify_error(exception: Exception) -> str:
    """
    Classify an exception into an error type
    
    Args:
        exception: The exception to classify
        
    Returns:
        Error type string from ErrorType class
    """
    error_msg = str(exception).lower()
    
    # API Key related errors
    if any(keyword in error_msg for keyword in [
        "api key", "authentication", "unauthorized", "invalid_api_key",
        "incorrect api key", "sk-proj", "openai"
    ]):
        return ErrorType.API_KEY
    
    # Rate limit errors
    if any(keyword in error_msg for keyword in [
        "rate limit", "too many requests", "quota", "limit exceeded",
        "requests per minute", "rpm", "tpm"
    ]):
        return ErrorType.RATE_LIMIT
    
    # Network errors
    if any(keyword in error_msg for keyword in [
        "network", "connection", "timeout", "unreachable", "dns",
        "socket", "ssl", "certificate", "connection refused"
    ]):
        return ErrorType.NETWORK
    
    # Validation errors
    if any(keyword in error_msg for keyword in [
        "validation", "invalid", "malformed", "bad request",
        "missing required", "parameter"
    ]):
        return ErrorType.VALIDATION
    
    # Quota exceeded
    if any(keyword in error_msg for keyword in [
        "quota exceeded", "billing", "usage limit", "insufficient credits"
    ]):
        return ErrorType.QUOTA_EXCEEDED
    
    # Timeout errors
    if any(keyword in error_msg for keyword in [
        "timeout", "timed out", "request timeout", "read timeout"
    ]):
        return ErrorType.TIMEOUT
    
    # Default to system error
    return ErrorType.SYSTEM


def get_error_suggestions(exception: Exception) -> List[str]:
    """
    Get specific error suggestions based on the exception
    
    Args:
        exception: The exception to analyze
        
    Returns:
        List of specific suggestions for this error
    """
    error_type = classify_error(exception)
    error_msg = str(exception).lower()
    
    # Add specific suggestions based on error content
    suggestions = ErrorFormatter._get_default_suggestions(error_type).copy()
    
    # Add specific suggestions for OpenAI API key errors
    if error_type == ErrorType.API_KEY and "openai" in error_msg:
        suggestions.insert(0, "Visit https://platform.openai.com/account/api-keys to check your API key")
    
    # Add specific suggestions for rate limit errors
    if error_type == ErrorType.RATE_LIMIT:
        if "requests per minute" in error_msg:
            suggestions.insert(0, "You're making requests too quickly. Wait 60 seconds before retrying.")
        elif "tokens per minute" in error_msg:
            suggestions.insert(0, "Try using a shorter blog topic to reduce token usage.")
    
    return suggestions


def create_error_response(exception: Exception) -> Dict:
    """
    Create a complete error response from an exception
    
    Args:
        exception: The exception to process
        
    Returns:
        Complete error response dictionary
    """
    error_type = classify_error(exception)
    suggestions = get_error_suggestions(exception)
    
    return ErrorFormatter.format_error(
        error_type=error_type,
        technical_message=str(exception),
        suggestions=suggestions
    )
