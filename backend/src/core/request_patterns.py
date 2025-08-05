"""
Request/Response Validation and Common Patterns

Provides commonly used request validation, response formatting, and
business logic patterns to reduce code duplication.
"""

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from datetime import datetime
import uuid

from core.common import *
from core.error_handling import ValidationError, APIError


@dataclass
class PaginationParams:
    """Standard pagination parameters"""
    page: int = field(default=1)
    page_size: int = field(default=DEFAULT_PAGE_SIZE)
    offset: int = field(init=False)
    
    def __post_init__(self):
        # Validate page and page_size
        if self.page < 1:
            self.page = 1
        if self.page_size < 1 or self.page_size > 100:
            self.page_size = DEFAULT_PAGE_SIZE
        
        # Calculate offset
        self.offset = (self.page - 1) * self.page_size


@dataclass
class SortParams:
    """Standard sorting parameters"""
    sort_by: str = field(default="created_at")
    sort_order: str = field(default="desc")
    
    def __post_init__(self):
        # Validate sort_order
        if self.sort_order.lower() not in ['asc', 'desc']:
            self.sort_order = 'desc'


@dataclass
class FilterParams:
    """Standard filtering parameters"""
    search: Optional[str] = None
    status: Optional[str] = None
    user_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database queries"""
        filters = {}
        if self.search:
            filters['search'] = self.search.strip()
        if self.status:
            filters['status'] = self.status
        if self.user_id:
            filters['user_id'] = self.user_id
        if self.date_from:
            filters['date_from'] = self.date_from
        if self.date_to:
            filters['date_to'] = self.date_to
        return filters


@dataclass
class StandardResponse:
    """Standard API response format"""
    success: bool
    message: str = ""
    data: Any = None
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        response = {
            'success': self.success,
            'message': self.message,
            'timestamp': format_timestamp(self.timestamp)
        }
        
        if self.data is not None:
            response['data'] = self.data
        
        if self.errors:
            response['errors'] = self.errors
        
        if self.metadata:
            response['metadata'] = self.metadata
        
        return response


@dataclass
class PaginatedResponse(StandardResponse):
    """Paginated API response format"""
    total_count: int = 0
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE
    total_pages: int = field(init=False)
    has_next: bool = field(init=False)
    
    def __post_init__(self):
        # Calculate pagination metadata
        self.total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
        self.has_next = self.page < self.total_pages
        self.has_prev = self.page > 1
        
        # Add pagination to metadata
        self.metadata.update({
            'pagination': {
                'total_count': self.total_count,
                'page': self.page,
                'page_size': self.page_size,
                'total_pages': self.total_pages,
                'has_next': self.has_next,
                'has_prev': self.has_prev
            }
        })


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
    """Validate that all required fields are present and not empty"""
    missing_fields = []
    empty_fields = []
    
    for field in required_fields:
        if field not in data:
            missing_fields.append(field)
        elif not data[field] or (isinstance(data[field], str) and not data[field].strip()):
            empty_fields.append(field)
    
    errors = []
    if missing_fields:
        errors.append(f"Missing required fields: {', '.join(missing_fields)}")
    if empty_fields:
        errors.append(f"Empty required fields: {', '.join(empty_fields)}")
    
    if errors:
        raise ValidationError("; ".join(errors), "required_fields")


def validate_string_length(value: str, field_name: str, min_length: int = 0, max_length: int = 1000) -> str:
    """Validate string field length"""
    if value is None:
        raise ValidationError(f"{field_name} cannot be None", field_name)
    
    value = value.strip()
    
    if len(value) < min_length:
        raise ValidationError(f"{field_name} must be at least {min_length} characters long", field_name)
    
    if len(value) > max_length:
        raise ValidationError(f"{field_name} cannot exceed {max_length} characters", field_name)
    
    return value


def validate_enum_field(value: str, field_name: str, allowed_values: List[str]) -> str:
    """Validate that field value is in allowed list"""
    if value not in allowed_values:
        raise ValidationError(f"{field_name} must be one of: {', '.join(allowed_values)}", field_name)
    
    return value


def parse_request_params(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse and validate common request parameters"""
    # Extract pagination
    pagination = PaginationParams(
        page=safe_int(request_data.get('page', 1), 1),
        page_size=safe_int(request_data.get('page_size', DEFAULT_PAGE_SIZE), DEFAULT_PAGE_SIZE)
    )
    
    # Extract sorting
    sorting = SortParams(
        sort_by=request_data.get('sort_by', 'created_at'),
        sort_order=request_data.get('sort_order', 'desc')
    )
    
    # Extract filtering
    filtering = FilterParams(
        search=request_data.get('search'),
        status=request_data.get('status'),
        user_id=request_data.get('user_id'),
        date_from=request_data.get('date_from'),
        date_to=request_data.get('date_to')
    )
    
    return {
        'pagination': pagination,
        'sorting': sorting,
        'filtering': filtering
    }


def create_success_response(
    data: Any = None, 
    message: str = "Operation successful",
    metadata: Optional[Dict[str, Any]] = None
) -> StandardResponse:
    """Create a standardized success response"""
    return StandardResponse(
        success=True,
        message=message,
        data=data,
        metadata=metadata or {}
    )


def create_error_response_standard(
    message: str = "An error occurred",
    errors: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> StandardResponse:
    """Create a standardized error response"""
    return StandardResponse(
        success=False,
        message=message,
        errors=errors or [],
        metadata=metadata or {}
    )


def create_paginated_response(
    data: List[Any],
    total_count: int,
    page: int,
    page_size: int,
    message: str = "Data retrieved successfully"
) -> PaginatedResponse:
    """Create a standardized paginated response"""
    return PaginatedResponse(
        success=True,
        message=message,
        data=data,
        total_count=total_count,
        page=page,
        page_size=page_size
    )


class RequestValidator:
    """Request validation utility class"""
    
    @staticmethod
    def validate_blog_generation_request(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate blog generation request"""
        validate_required_fields(data, ['topic'])
        
        topic = validate_string_length(data['topic'], 'topic', min_length=5, max_length=200)
        
        # Optional fields with defaults
        length = validate_enum_field(
            data.get('length', 'medium'),
            'length',
            ['short', 'medium', 'long']
        )
        
        tone = validate_enum_field(
            data.get('tone', 'professional'),
            'tone',
            ['professional', 'casual', 'technical', 'creative']
        )
        
        include_images = safe_bool(data.get('include_images', True))
        
        return {
            'topic': topic,
            'length': length,
            'tone': tone,
            'include_images': include_images
        }
    
    @staticmethod
    def validate_user_registration(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user registration request"""
        validate_required_fields(data, ['email', 'name'])
        
        email = data['email'].strip().lower()
        if not is_valid_email(email):
            raise ValidationError("Invalid email format", "email")
        
        name = validate_string_length(data['name'], 'name', min_length=2, max_length=100)
        
        role = validate_enum_field(
            data.get('role', 'FREE'),
            'role',
            ['FREE', 'PREMIUM', 'ADMIN']
        )
        
        return {
            'email': email,
            'name': name,
            'role': role
        }
    
    @staticmethod
    def validate_blog_update(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate blog update request"""
        allowed_fields = ['title', 'content', 'status', 'tags']
        
        # Filter out unknown fields
        validated_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if 'title' in validated_data:
            validated_data['title'] = validate_string_length(
                validated_data['title'], 'title', min_length=5, max_length=200
            )
        
        if 'content' in validated_data:
            validated_data['content'] = validate_string_length(
                validated_data['content'], 'content', min_length=10, max_length=50000
            )
        
        if 'status' in validated_data:
            validated_data['status'] = validate_enum_field(
                validated_data['status'],
                'status',
                ['draft', 'published', 'archived']
            )
        
        if 'tags' in validated_data and validated_data['tags']:
            if isinstance(validated_data['tags'], str):
                # Convert comma-separated string to list
                validated_data['tags'] = [tag.strip() for tag in validated_data['tags'].split(',')]
            elif not isinstance(validated_data['tags'], list):
                raise ValidationError("Tags must be a list or comma-separated string", "tags")
        
        return validated_data


class ResponseFormatter:
    """Response formatting utility class"""
    
    @staticmethod
    def format_blog_response(blog_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format blog data for API response"""
        return {
            'id': blog_data.get('id'),
            'title': blog_data.get('title'),
            'content': blog_data.get('content'),
            'status': blog_data.get('status'),
            'user_id': blog_data.get('user_id'),
            'created_at': format_timestamp(blog_data.get('created_at')),
            'updated_at': format_timestamp(blog_data.get('updated_at')),
            'tags': blog_data.get('tags', []),
            'word_count': len(blog_data.get('content', '').split()) if blog_data.get('content') else 0,
            'reading_time': max(1, len(blog_data.get('content', '').split()) // 200) if blog_data.get('content') else 1
        }
    
    @staticmethod
    def format_user_response(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format user data for API response"""
        return {
            'id': user_data.get('id'),
            'email': user_data.get('email'),
            'name': user_data.get('name'),
            'role': user_data.get('role'),
            'created_at': format_timestamp(user_data.get('created_at')),
            'last_login': format_timestamp(user_data.get('last_login')) if user_data.get('last_login') else None,
            'blog_count': user_data.get('blog_count', 0),
            'generation_count': user_data.get('generation_count', 0)
        }
    
    @staticmethod
    def format_task_response(task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format task data for API response"""
        return {
            'id': task_data.get('id'),
            'type': task_data.get('type'),
            'status': task_data.get('status'),
            'progress': task_data.get('progress', 0),
            'current_step': task_data.get('current_step'),
            'result': task_data.get('result'),
            'error': task_data.get('error'),
            'created_at': format_timestamp(task_data.get('created_at')),
            'updated_at': format_timestamp(task_data.get('updated_at')),
            'estimated_completion': task_data.get('estimated_completion')
        }


# Export commonly used items
__all__ = [
    'PaginationParams', 'SortParams', 'FilterParams',
    'StandardResponse', 'PaginatedResponse',
    'validate_required_fields', 'validate_string_length', 'validate_enum_field',
    'parse_request_params', 'create_success_response', 'create_error_response_standard',
    'create_paginated_response', 'RequestValidator', 'ResponseFormatter'
]
