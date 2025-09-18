"""
Standardized Error Response System for BlogGen Backend
Provides consistent error formats with user-friendly messages and correlation IDs
"""
import uuid
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class ErrorResponse(BaseModel):
    """Standardized error response model"""
    error_code: str
    user_message: str
    technical_details: Optional[str] = None
    suggested_actions: List[str] = []
    correlation_id: str
    retry_after: Optional[int] = None  # Seconds to wait before retrying
    timestamp: str
    retryable: bool = True

class ErrorContext(BaseModel):
    """Additional context for error responses"""
    user_id: Optional[str] = None
    task_id: Optional[str] = None
    endpoint: Optional[str] = None
    request_data: Optional[Dict[str, Any]] = None

# Error catalog with predefined responses
ERROR_CATALOG = {
    # Authentication Errors
    "AUTH_REQUIRED": ErrorResponse(
        error_code="AUTH_REQUIRED",
        user_message="Authentication is required to access this service.",
        suggested_actions=["Please sign in to your account", "Check if your session has expired"],
        retryable=False,
        correlation_id="",
        timestamp=""
    ),
    
    "AUTH_EXPIRED": ErrorResponse(
        error_code="AUTH_EXPIRED", 
        user_message="Your session has expired. Please sign in again.",
        suggested_actions=["Sign in again", "Refresh the page"],
        retryable=False,
        correlation_id="",
        timestamp=""
    ),
    
    "AUTH_INVALID": ErrorResponse(
        error_code="AUTH_INVALID",
        user_message="Invalid authentication credentials.",
        suggested_actions=["Sign in again", "Contact support if the problem persists"],
        retryable=False,
        correlation_id="",
        timestamp=""
    ),

    # User Limit Errors
    "GENERATION_LIMIT_EXCEEDED": ErrorResponse(
        error_code="GENERATION_LIMIT_EXCEEDED",
        user_message="You've reached your monthly blog generation limit.",
        suggested_actions=["Upgrade to Premium for unlimited generations", "Wait until next month"],
        retryable=False,
        correlation_id="",
        timestamp=""
    ),
    
    "RATE_LIMIT_EXCEEDED": ErrorResponse(
        error_code="RATE_LIMIT_EXCEEDED",
        user_message="Too many requests. Please wait before trying again.",
        suggested_actions=["Wait a moment before retrying"],
        retry_after=30,
        retryable=True,
        correlation_id="",
        timestamp=""
    ),

    # Input Validation Errors
    "INVALID_TOPIC_LENGTH": ErrorResponse(
        error_code="INVALID_TOPIC_LENGTH",
        user_message="Blog topic must be between 3 and 200 characters.",
        suggested_actions=["Shorten your topic", "Use the description field for detailed requirements"],
        retryable=True,
        correlation_id="",
        timestamp=""
    ),
    
    "INVALID_INPUT_FORMAT": ErrorResponse(
        error_code="INVALID_INPUT_FORMAT",
        user_message="The provided input format is invalid.",
        suggested_actions=["Check your input format", "Refer to the API documentation"],
        retryable=True,
        correlation_id="",
        timestamp=""
    ),
    
    "MISSING_REQUIRED_FIELD": ErrorResponse(
        error_code="MISSING_REQUIRED_FIELD",
        user_message="Required information is missing.",
        suggested_actions=["Check that all required fields are filled", "Refresh the page and try again"],
        retryable=True,
        correlation_id="",
        timestamp=""
    ),

    # External Service Errors
    "OPENAI_API_ERROR": ErrorResponse(
        error_code="OPENAI_API_ERROR",
        user_message="AI service is temporarily unavailable.",
        suggested_actions=["Try again in a few moments", "Contact support if the issue persists"],
        retry_after=60,
        retryable=True,
        correlation_id="",
        timestamp=""
    ),
    
    "OPENAI_RATE_LIMIT": ErrorResponse(
        error_code="OPENAI_RATE_LIMIT",
        user_message="AI service is temporarily busy. Please try again in a moment.",
        suggested_actions=["Wait 30 seconds and retry", "Try again later"],
        retry_after=30,
        retryable=True,
        correlation_id="",
        timestamp=""
    ),
    
    "EXTERNAL_SERVICE_TIMEOUT": ErrorResponse(
        error_code="EXTERNAL_SERVICE_TIMEOUT",
        user_message="External service took too long to respond.",
        suggested_actions=["Try again", "Check your internet connection"],
        retryable=True,
        correlation_id="",
        timestamp=""
    ),

    # System Errors
    "TASK_NOT_FOUND": ErrorResponse(
        error_code="TASK_NOT_FOUND",
        user_message="The requested task could not be found.",
        suggested_actions=["Check the task ID", "Start a new blog generation"],
        retryable=False,
        correlation_id="",
        timestamp=""
    ),
    
    "TASK_ALREADY_COMPLETED": ErrorResponse(
        error_code="TASK_ALREADY_COMPLETED",
        user_message="This task has already been completed.",
        suggested_actions=["Start a new blog generation", "Check your blog collection"],
        retryable=False,
        correlation_id="",
        timestamp=""
    ),
    
    "DATABASE_ERROR": ErrorResponse(
        error_code="DATABASE_ERROR",
        user_message="A database error occurred. Please try again.",
        technical_details="Database connection or query failed",
        suggested_actions=["Try again in a moment", "Contact support if the problem persists"],
        retryable=True,
        correlation_id="",
        timestamp=""
    ),
    
    "REDIS_CONNECTION_ERROR": ErrorResponse(
        error_code="REDIS_CONNECTION_ERROR",
        user_message="Real-time updates may be delayed. Your blog is still being generated.",
        technical_details="Redis connection failed",
        suggested_actions=["Continue waiting for completion", "Refresh the page if needed"],
        retryable=True,
        correlation_id="",
        timestamp=""
    ),

    # Generation Errors
    "GENERATION_FAILED": ErrorResponse(
        error_code="GENERATION_FAILED",
        user_message="Blog generation failed. Please try again.",
        suggested_actions=["Try again with a different topic", "Contact support if the problem persists"],
        retryable=True,
        correlation_id="",
        timestamp=""
    ),
    
    "GENERATION_TIMEOUT": ErrorResponse(
        error_code="GENERATION_TIMEOUT",
        user_message="Blog generation took too long and was cancelled.",
        suggested_actions=["Try again with a simpler topic", "Try again later"],
        retryable=True,
        correlation_id="",
        timestamp=""
    ),
    
    "CONTENT_FILTER_VIOLATION": ErrorResponse(
        error_code="CONTENT_FILTER_VIOLATION",
        user_message="The requested content violates our content policy.",
        suggested_actions=["Modify your topic to be more appropriate", "Review our content guidelines"],
        retryable=True,
        correlation_id="",
        timestamp=""
    ),

    # File/Storage Errors
    "S3_UPLOAD_FAILED": ErrorResponse(
        error_code="S3_UPLOAD_FAILED",
        user_message="Failed to save blog content. Please try again.",
        technical_details="S3 upload operation failed",
        suggested_actions=["Try generating the blog again", "Contact support if the issue persists"],
        retryable=True,
        correlation_id="",
        timestamp=""
    ),

    # Generic Fallback
    "INTERNAL_SERVER_ERROR": ErrorResponse(
        error_code="INTERNAL_SERVER_ERROR",
        user_message="An unexpected error occurred. Please try again.",
        technical_details="Unhandled server error",
        suggested_actions=["Try again", "Contact support if the problem persists"],
        retryable=True,
        correlation_id="",
        timestamp=""
    ),
    
    "SERVICE_UNAVAILABLE": ErrorResponse(
        error_code="SERVICE_UNAVAILABLE",
        user_message="The service is temporarily unavailable.",
        suggested_actions=["Try again in a few minutes", "Check our status page"],
        retry_after=300,  # 5 minutes
        retryable=True,
        correlation_id="",
        timestamp=""
    )
}

def create_error_response(
    error_type: str,
    user_message: Optional[str] = None,
    technical_details: Optional[str] = None,
    correlation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> ErrorResponse:
    """
    Create a standardized error response with correlation tracking.
    
    Args:
        error_type: Key from ERROR_CATALOG
        user_message: Optional override for user-facing message
        technical_details: Optional technical information for logging
        correlation_id: Optional correlation ID (auto-generated if not provided)
        metadata: Optional additional context data
    
    Returns:
        ErrorResponse object ready for JSON serialization
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())[:8]
    
    # Get base error definition
    base_error = ERROR_CATALOG.get(error_type, ERROR_CATALOG["INTERNAL_SERVER_ERROR"])
    
    # Create response with proper field names
    response = ErrorResponse(
        error_code=error_type,
        user_message=user_message or base_error.user_message,
        technical_details=technical_details or base_error.technical_details,
        suggested_actions=base_error.suggested_actions,
        correlation_id=correlation_id,
        retry_after=base_error.retry_after,
        timestamp=datetime.utcnow().isoformat(),
        retryable=base_error.retryable
    )
    
    # Log the error for tracking
    logger.error(
        f"Error Response [{correlation_id}]: {error_type} | "
        f"User: {response.user_message} | Technical: {response.technical_details}"
    )
    
    return response

# Convenience functions for common error types
def create_auth_error(
    error_type: str = "AUTH_REQUIRED",
    details: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> ErrorResponse:
    """Create authentication error response"""
    return create_error_response(
        error_type=error_type,
        technical_details=details,
        correlation_id=correlation_id
    )

def create_validation_error(
    field_name: str,
    details: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> ErrorResponse:
    """Create validation error response"""
    return create_error_response(
        error_type="VALIDATION_ERROR",
        user_message=f"Invalid {field_name}: {details}" if details else None,
        technical_details=f"Validation failed for field '{field_name}': {details}",
        correlation_id=correlation_id
    )

def create_rate_limit_error(
    user_role: str,
    current_usage: int,
    limit: int,
    correlation_id: Optional[str] = None
) -> ErrorResponse:
    """Create rate limiting error response"""
    return create_error_response(
        error_type="GENERATION_LIMIT_EXCEEDED",
        user_message=f"Monthly generation limit reached ({current_usage}/{limit}). Upgrade your plan for more generations.",
        technical_details=f"User role {user_role} exceeded limit: {current_usage}/{limit}",
        correlation_id=correlation_id
    )

def create_openai_error(
    error_message: str,
    error_code: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> ErrorResponse:
    """Create OpenAI API error response"""
    # Determine specific error type based on error message/code
    error_type = "OPENAI_API_ERROR"
    if error_code:
        if "rate_limit" in error_code.lower():
            error_type = "OPENAI_RATE_LIMIT"
        elif "quota" in error_code.lower() or "billing" in error_code.lower():
            error_type = "OPENAI_QUOTA_EXCEEDED"
        elif "invalid" in error_code.lower():
            error_type = "OPENAI_INVALID_REQUEST"
    
    return create_error_response(
        error_type=error_type,
        technical_details=f"OpenAI Error [{error_code}]: {error_message}",
        correlation_id=correlation_id
    )

def create_database_error(
    operation: str,
    details: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> ErrorResponse:
    """Create database error response"""
    return create_error_response(
        error_type="DATABASE_ERROR",
        technical_details=f"Database operation '{operation}' failed: {details}",
        correlation_id=correlation_id
    )

def create_system_error(
    component: str,
    details: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> ErrorResponse:
    """Create system error response"""
    return create_error_response(
        error_type="INTERNAL_SERVER_ERROR",
        technical_details=f"System component '{component}' error: {details}",
        correlation_id=correlation_id
    )

# Additional utility functions for FastAPI HTTPException integration
def error_response_to_http_exception(error_response: ErrorResponse) -> HTTPException:
    """Convert ErrorResponse to FastAPI HTTPException"""
    # Map error codes to HTTP status codes
    status_code_map = {
        "AUTH_REQUIRED": 401,
        "AUTH_EXPIRED": 401,
        "AUTH_INVALID": 401,
        "INSUFFICIENT_PERMISSIONS": 403,
        "GENERATION_LIMIT_EXCEEDED": 429,
        "OPENAI_RATE_LIMIT": 429,
        "OPENAI_QUOTA_EXCEEDED": 402,
        "OPENAI_API_ERROR": 503,
        "DATABASE_ERROR": 500,
        "VALIDATION_ERROR": 422,
        "INVALID_TOPIC_LENGTH": 422,
        "MISSING_REQUIRED_FIELD": 422,
        "INTERNAL_SERVER_ERROR": 500
    }
    
    status_code = status_code_map.get(error_response.error_code, 500)
    
    return HTTPException(
        status_code=status_code,
        detail={
            "error_code": error_response.error_code,
            "user_message": error_response.user_message,
            "technical_details": error_response.technical_details,
            "suggested_actions": error_response.suggested_actions,
            "correlation_id": error_response.correlation_id,
            "retry_after": error_response.retry_after,
            "timestamp": error_response.timestamp,
            "retryable": error_response.retryable
        }
    )

def handle_openai_error(error: Exception, correlation_id: Optional[str] = None) -> HTTPException:
    """Handle OpenAI-specific errors with appropriate error codes"""
    error_str = str(error).lower()
    
    if "rate limit" in error_str or "quota" in error_str:
        error_response = create_openai_error(str(error), "rate_limit", correlation_id)
    elif "timeout" in error_str:
        error_response = create_system_error("openai_timeout", str(error), correlation_id)
    elif "api key" in error_str or "authentication" in error_str:
        error_response = create_openai_error(str(error), "authentication", correlation_id)
    else:
        error_response = create_openai_error(str(error), "general", correlation_id)
    
    return error_response_to_http_exception(error_response)

def handle_database_error(error: Exception, operation: str = "unknown", correlation_id: Optional[str] = None) -> HTTPException:
    """Handle database-specific errors"""
    error_response = create_database_error(operation, str(error), correlation_id)
    return error_response_to_http_exception(error_response)

def handle_validation_error(error: Exception, field_name: str = "input", correlation_id: Optional[str] = None) -> HTTPException:
    """Handle validation errors from Pydantic"""
    error_response = create_validation_error(field_name, str(error), correlation_id)
    return error_response_to_http_exception(error_response)