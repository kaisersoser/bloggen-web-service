#!/usr/bin/env python3
"""
Legacy Flask API Module - Refactored with Clean Code Principles

This module provides backward compatibility for the old Flask API while
demonstrating clean code principles. The main FastAPI application in
fastapi_main.py should be used for new development.

Applied Principles:
- Single Responsibility Principle: Each class has one clear purpose
- Error Handling: Comprehensive exception management with logging
- Type Safety: Full type annotations
- DRY Principle: Reusable validation and response patterns
- Self-Documenting Code: Clear names and structured design
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass
from flask import Flask, request, jsonify, Response
import logging

# Use existing unified systems
import sys
sys.path.append('.')
from core.config import config
from core.logging_utils import get_logger
from core.error_handling import BlogGenError, handle_api_errors

# Configure specialized logger
logger = get_logger(__name__)

# Import the blog generation flow
try:
    from bloggen.flows import BlogGenerationFlow
    BLOG_GENERATION_AVAILABLE = True
except ImportError:
    logger.warning("BlogGenerationFlow not available")
    BLOG_GENERATION_AVAILABLE = False


@dataclass
class BlogGenerationRequest:
    """Type-safe blog generation request with validation."""
    topic: str
    current_year: Optional[int] = None
    
    @classmethod
    def from_request_data(cls, data: Optional[Dict[str, Any]]) -> 'BlogGenerationRequest':
        """Create request from Flask request data with validation."""
        if not data:
            raise ValueError("Request body is required")
        
        topic = data.get('topic')
        if not topic or not isinstance(topic, str) or not topic.strip():
            raise ValueError("Valid topic is required")
        
        return cls(
            topic=topic.strip(),
            current_year=data.get('current_year', datetime.now().year)
        )
    
    def to_run_inputs(self) -> Dict[str, Any]:
        """Convert to format expected by the run function."""
        return {
            'topic': self.topic,
            'current_year': str(self.current_year)
        }


@dataclass
class BlogGenerationResponse:
    """Structured response for blog generation."""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    file_path: Optional[str] = None
    
    def to_json_response(self) -> Tuple[Response, int]:
        """Convert to Flask JSON response with appropriate status code."""
        if self.success:
            response_data = {'content': self.content}
            if self.file_path:
                response_data['file_path'] = self.file_path
            return jsonify(response_data), 200
        else:
            return jsonify({'error': self.error}), 500


class BlogFileManager:
    """Handles blog file operations with proper path management."""
    
    def __init__(self, base_path: str = "generated_blogs"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
    def get_blog_file_path(self, topic: str) -> Path:
        """Generate standardized file path for blog topic."""
        # Sanitize filename
        safe_filename = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_filename = safe_filename.replace(' ', '_').lower()
        return self.base_path / f"{safe_filename}.txt"
    
    def read_blog_content(self, file_path: Path) -> Optional[str]:
        """Read blog content from file with error handling."""
        try:
            if not file_path.exists():
                logger.warning(f"Blog file not found: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read().strip()
                
            if not content:
                logger.warning(f"Blog file is empty: {file_path}")
                return None
                
            return content
            
        except Exception as e:
            logger.error(f"Failed to read blog file {file_path}: {e}")
            return None


class BlogGenerationService:
    """Handles blog generation business logic with proper error management."""
    
    def __init__(self):
        self.file_manager = BlogFileManager()
    
    @handle_api_errors("Blog generation failed")
    def generate_blog(self, request_data: BlogGenerationRequest) -> BlogGenerationResponse:
        """
        Generate blog content using the BlogGenerationFlow.
        
        Args:
            request_data: Validated blog generation request
            
        Returns:
            BlogGenerationResponse: Result with content or error
        """
        try:
            logger.info(f"Starting blog generation for topic: {request_data.topic}")
            
            if not BLOG_GENERATION_AVAILABLE:
                raise BlogGenError("Blog generation system not available")
            
            # Create and execute blog generation flow
            flow = BlogGenerationFlow()
            
            # Execute the flow (this is synchronous, unlike the FastAPI async version)
            result = flow.kickoff({
                'topic': request_data.topic,
                'current_year': request_data.current_year
            })
            
            logger.info("Blog generation completed successfully")
            
            # For the legacy API, we'll return the generated content directly
            # instead of trying to read from files
            if hasattr(result, 'output') and result.output:
                content = str(result.output)
                logger.info("Blog content generated successfully")
                return BlogGenerationResponse(
                    success=True,
                    content=content
                )
            else:
                # If no direct output, try to find generated file
                expected_file_path = self.file_manager.get_blog_file_path(request_data.topic)
                content = self.file_manager.read_blog_content(expected_file_path)
                
                if content:
                    logger.info(f"Blog content retrieved from: {expected_file_path}")
                    return BlogGenerationResponse(
                        success=True,
                        content=content,
                        file_path=str(expected_file_path)
                    )
                else:
                    # Generation succeeded but no content available
                    logger.warning("Blog generation completed but no content available")
                    return BlogGenerationResponse(
                        success=True,
                        content="Blog generated successfully, but content not accessible via legacy API.",
                        error="Content not available in legacy format"
                    )
                    
        except BlogGenError:
            # Re-raise BlogGenError as-is
            raise
        except Exception as e:
            error_msg = f"Blog generation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return BlogGenerationResponse(
                success=False,
                error=error_msg
            )


class LegacyFlaskAPI:
    """Flask API wrapper with clean separation of concerns."""
    
    def __init__(self):
        self.app = Flask(__name__)
        self.blog_service = BlogGenerationService()
        self._setup_routes()
        
        logger.info("Legacy Flask API initialized")
    
    def _setup_routes(self) -> None:
        """Configure Flask routes with proper error handling."""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint."""
            return jsonify({
                'status': 'healthy',
                'service': 'legacy-flask-api',
                'timestamp': datetime.utcnow().isoformat()
            }), 200
        
        @self.app.route('/generate-blog', methods=['POST'])
        def generate_blog():
            """
            Generate blog endpoint with comprehensive validation and error handling.
            
            Expected JSON payload:
            {
                "topic": "Your blog topic here",
                "current_year": 2025  // optional
            }
            """
            try:
                # Parse and validate request
                request_data = BlogGenerationRequest.from_request_data(request.json)
                
                # Generate blog
                result = self.blog_service.generate_blog(request_data)
                
                # Return response
                return result.to_json_response()
                
            except ValueError as e:
                logger.warning(f"Validation error: {e}")
                return jsonify({'error': str(e)}), 400
            except BlogGenError as e:
                logger.error(f"Blog generation error: {e}")
                return jsonify({'error': str(e)}), 500
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return jsonify({'error': error_msg}), 500
    
    def run_development_server(self) -> None:
        """Run Flask development server with proper configuration."""
        try:
            logger.info("Starting Legacy Flask API development server")
            logger.warning("⚠️  This is the legacy API. Use fastapi_main.py for new development.")
            
            self.app.run(
                host='127.0.0.1',
                port=5001,  # Different port from main FastAPI app
                debug=config.server.debug,
                threaded=True
            )
        except Exception as e:
            logger.error(f"Failed to start development server: {e}")
            raise


# Global API instance
legacy_api = LegacyFlaskAPI()


# Backward compatibility functions
def generate_blog():
    """Legacy function for backward compatibility."""
    logger.warning("Using deprecated generate_blog function. Use LegacyFlaskAPI class instead.")
    return legacy_api.app.view_functions['generate_blog']()


if __name__ == '__main__':
    legacy_api.run_development_server()