"""
Configuration management for different deployment environments.

This module handles environment-specific settings for development, staging, and production.
"""

import os
from typing import List, Dict, Any


class Config:
    """Base configuration class"""
    
    # Environment detection
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    NEXTAUTH_SECRET = os.getenv('NEXTAUTH_SECRET')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    SERPER_API_KEY = os.getenv('SERPER_API_KEY')
    UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY')
    
    # Flask settings
    DEBUG = False
    TESTING = False
    
    @staticmethod
    def get_cors_origins() -> List[str]:
        """Get allowed CORS origins based on environment"""
        origins = []
        
        # Always include development origins for local testing
        dev_origins = [
            'http://localhost:3000',
            'http://localhost:3001',
            'http://127.0.0.1:3000',
            'http://127.0.0.1:3001'
        ]
        
        # Add environment-specific origins
        frontend_url = os.getenv('FRONTEND_URL')
        if frontend_url:
            origins.append(frontend_url)
        
        # Add production domains
        production_domains = os.getenv('PRODUCTION_DOMAINS', '').split(',')
        for domain in production_domains:
            domain = domain.strip()
            if domain and domain != 'https://yourdomain.com':  # Skip placeholder
                origins.append(domain)
        
        # Include development origins if in development
        if Config.ENVIRONMENT == 'development':
            origins.extend(dev_origins)
        
        # Remove duplicates and empty strings
        origins = list(set(filter(None, origins)))
        
        return origins


class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    ENVIRONMENT = 'development'
    
    @staticmethod
    def get_cors_origins() -> List[str]:
        """Allow all localhost origins in development"""
        return [
            'http://localhost:3000',
            'http://localhost:3001',
            'http://127.0.0.1:3000',
            'http://127.0.0.1:3001'
        ]


class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    ENVIRONMENT = 'production'
    
    @staticmethod
    def get_cors_origins() -> List[str]:
        """Strict CORS origins for production"""
        origins = []
        
        # Frontend URL from environment
        frontend_url = os.getenv('FRONTEND_URL')
        if frontend_url:
            origins.append(frontend_url)
        
        # Production domains
        production_domains = os.getenv('PRODUCTION_DOMAINS', '').split(',')
        for domain in production_domains:
            domain = domain.strip()
            if domain and domain != 'https://yourdomain.com':  # Skip placeholder
                origins.append(domain)
        
        # Add NextAuth URL if different from frontend
        nextauth_url = os.getenv('NEXTAUTH_URL')
        if nextauth_url and nextauth_url not in origins:
            origins.append(nextauth_url)
        
        return list(set(filter(None, origins)))


class StagingConfig(Config):
    """Staging environment configuration"""
    DEBUG = True
    ENVIRONMENT = 'staging'


def get_config() -> Config:
    """Get configuration based on environment"""
    env = os.getenv('ENVIRONMENT', 'development').lower()
    
    if env == 'production':
        return ProductionConfig()
    elif env == 'staging':
        return StagingConfig()
    else:
        return DevelopmentConfig()


# Export the active configuration
config = get_config()
