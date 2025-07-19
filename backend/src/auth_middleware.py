"""
Authentication middleware for Flask backend to work with NextAuth.js frontend.

This module provides JWT token verification and user session management
to protect API endpoints from unauthorized access.
"""

import jwt
import requests
from functools import wraps
from flask import request, jsonify, current_app
import os
from datetime import datetime


class AuthMiddleware:
    """Handles JWT token verification and user authentication"""
    
    def __init__(self, app=None):
        self.app = app
        self.nextauth_secret = os.getenv('NEXTAUTH_SECRET')
        self.nextauth_url = os.getenv('NEXTAUTH_URL', 'http://localhost:3001')
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the authentication middleware with Flask app"""
        app.config.setdefault('NEXTAUTH_SECRET', self.nextauth_secret)
        app.config.setdefault('NEXTAUTH_URL', self.nextauth_url)
    
    def verify_jwt_token(self, token):
        """
        Verify JWT token from NextAuth.js
        
        Args:
            token (str): JWT token from Authorization header
            
        Returns:
            dict: Decoded token payload with user information
            
        Raises:
            jwt.InvalidTokenError: If token is invalid or expired
        """
        if not self.nextauth_secret:
            raise jwt.InvalidTokenError("NextAuth secret not configured")
            
        try:
            # Decode the JWT token using NextAuth secret
            decoded_token = jwt.decode(
                token,
                self.nextauth_secret,
                algorithms=['HS256'],
                options={"verify_signature": True, "verify_exp": True}
            )
            
            return decoded_token
            
        except jwt.ExpiredSignatureError:
            raise jwt.InvalidTokenError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise jwt.InvalidTokenError(f"Invalid token: {str(e)}")
    
    def get_user_from_session(self, session_token):
        """
        Get user information from NextAuth session token
        
        Args:
            session_token (str): Session token from NextAuth
            
        Returns:
            dict: User information from database
        """
        try:
            # In a real implementation, you'd query your database
            # For now, we'll decode the JWT token
            user_info = self.verify_jwt_token(session_token)
            return user_info
            
        except Exception as e:
            return None
    
    def extract_token_from_request(self, request):
        """
        Extract JWT token from request headers
        
        Args:
            request: Flask request object
            
        Returns:
            str: JWT token or None if not found
        """
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            try:
                # Format: "Bearer <token>"
                scheme, token = auth_header.split(' ', 1)
                if scheme.lower() == 'bearer':
                    return token
            except ValueError:
                pass
        
        # Also check for session token in cookies (NextAuth.js format)
        session_token = request.cookies.get('next-auth.session-token')
        if session_token:
            return session_token
            
        return None


# Initialize auth middleware instance
auth = AuthMiddleware()


def require_auth(f):
    """
    Decorator to require authentication for API endpoints
    
    Usage:
        @app.route('/protected-endpoint')
        @require_auth
        def protected_endpoint():
            # Access current user with g.current_user
            return jsonify({'message': 'Protected data'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import g
        
        # Extract token from request
        token = auth.extract_token_from_request(request)
        
        if not token:
            return jsonify({
                'error': 'Authentication required',
                'message': 'No valid authentication token provided'
            }), 401
        
        try:
            # Verify and decode token
            user_data = auth.verify_jwt_token(token)
            
            # Store user information in Flask's g object for access in route handlers
            g.current_user = user_data
            g.user_id = user_data.get('sub')  # Subject (user ID)
            g.user_email = user_data.get('email')
            g.user_name = user_data.get('name')
            g.user_role = user_data.get('role', 'FREE')
            
        except jwt.InvalidTokenError as e:
            return jsonify({
                'error': 'Invalid authentication token',
                'message': str(e)
            }), 401
        except Exception as e:
            return jsonify({
                'error': 'Authentication error',
                'message': 'Could not verify authentication token'
            }), 500
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_role(allowed_roles):
    """
    Decorator to require specific user roles for API endpoints
    
    Args:
        allowed_roles (list): List of allowed roles ['FREE', 'PREMIUM', 'ADMIN']
    
    Usage:
        @app.route('/premium-endpoint')
        @require_auth
        @require_role(['PREMIUM', 'ADMIN'])
        def premium_endpoint():
            return jsonify({'message': 'Premium content'})
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import g
            
            # Check if user is authenticated (require_auth should be used first)
            if not hasattr(g, 'current_user'):
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'Please authenticate first'
                }), 401
            
            user_role = g.user_role
            
            if user_role not in allowed_roles:
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'This endpoint requires one of the following roles: {", ".join(allowed_roles)}'
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def check_generation_limits():
    """
    Decorator to check user's blog generation limits
    
    Usage:
        @app.route('/generate-blog')
        @require_auth
        @check_generation_limits()
        def generate_blog():
            return jsonify({'message': 'Generation started'})
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import g
            
            # Check if user is authenticated
            if not hasattr(g, 'current_user'):
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'Please authenticate first'
                }), 401
            
            user_role = g.user_role
            
            # Define generation limits per role
            limits = {
                'FREE': 50,     # Increased for testing
                'PREMIUM': 50,  # 50 blogs per month  
                'ADMIN': -1     # Unlimited
            }
            
            if user_role == 'ADMIN':
                # Admins have unlimited access
                return f(*args, **kwargs)
            
            # TODO: Implement actual usage tracking from database
            # For now, we'll just check the role limits
            user_limit = limits.get(user_role, 0)
            
            if user_limit <= 0:
                return jsonify({
                    'error': 'Generation limit exceeded',
                    'message': f'Your {user_role.lower()} plan has reached its monthly limit',
                    'limit': user_limit
                }), 429
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
