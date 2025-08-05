"""
Unified Configuration Management for Blog Generation Service

This module provides centralized configuration management with environment
variable validation, type safety, and clear hierarchical organization.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    url: str
    chroma_path: str


@dataclass
class APIConfig:
    """External API configuration"""
    openai_key: Optional[str]
    serper_key: Optional[str] 
    unsplash_key: Optional[str]


@dataclass
class SecurityConfig:
    """Security and authentication configuration"""
    secret_key: str
    nextauth_secret: Optional[str]
    nextauth_url: str


@dataclass
class ServerConfig:
    """Server runtime configuration"""
    host: str
    port: int
    debug: bool
    environment: str


@dataclass
class PathConfig:
    """File system paths configuration"""
    base_dir: Path
    src_dir: Path
    bloggen_dir: Path
    logs_dir: Path
    agents_config: Path
    tasks_config: Path


class EnvironmentManager:
    """Centralized environment variable management with validation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._validate_required_vars()
    
    def _validate_required_vars(self):
        """Validate that required environment variables are present"""
        required_vars = ['NEXTAUTH_SECRET']
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            self.logger.warning(f"Missing environment variables: {missing}")
    
    def get_string(self, key: str, default: str = "") -> str:
        """Get string environment variable with default"""
        return os.getenv(key, default)
    
    def get_int(self, key: str, default: int) -> int:
        """Get integer environment variable with default"""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            self.logger.warning(f"Invalid integer for {key}, using default: {default}")
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean environment variable with default"""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def get_optional(self, key: str) -> Optional[str]:
        """Get optional environment variable (returns None if not set)"""
        return os.getenv(key)
    
    def get_list(self, key: str, separator: str = ',', default: Optional[List[str]] = None) -> List[str]:
        """Get list from environment variable"""
        value = os.getenv(key)
        if not value:
            return default or []
        return [item.strip() for item in value.split(separator) if item.strip()]


class UnifiedConfig:
    """
    Unified configuration management system
    
    Consolidates all configuration sources into a single, type-safe interface
    """
    
    def __init__(self):
        self.env = EnvironmentManager()
        self.logger = logging.getLogger(__name__)
        
        # Initialize all configuration sections
        self.paths = self._init_paths()
        self.server = self._init_server()
        self.database = self._init_database()
        self.api = self._init_api()
        self.security = self._init_security()
        
        self.logger.info(f"Configuration initialized for environment: {self.server.environment}")
    
    def _init_paths(self) -> PathConfig:
        """Initialize file system paths"""
        base_dir = Path(__file__).parent.parent.parent
        src_dir = base_dir / "src"
        bloggen_dir = src_dir / "bloggen"
        
        return PathConfig(
            base_dir=base_dir,
            src_dir=src_dir,
            bloggen_dir=bloggen_dir,
            logs_dir=bloggen_dir / "logs",
            agents_config=bloggen_dir / "config" / "agents.yaml",
            tasks_config=bloggen_dir / "config" / "tasks.yaml"
        )
    
    def _init_server(self) -> ServerConfig:
        """Initialize server configuration"""
        return ServerConfig(
            host=self.env.get_string("HOST", "localhost"),
            port=self.env.get_int("PORT", 5000),
            debug=self.env.get_bool("DEBUG", False),
            environment=self.env.get_string("ENVIRONMENT", "development").lower()
        )
    
    def _init_database(self) -> DatabaseConfig:
        """Initialize database configuration"""
        default_chroma_path = str(self.paths.bloggen_dir / "db" / "chroma.sqlite3")
        
        return DatabaseConfig(
            url=self.env.get_string("DATABASE_URL", default_chroma_path),
            chroma_path=self.env.get_string("CHROMA_DB_PATH", default_chroma_path)
        )
    
    def _init_api(self) -> APIConfig:
        """Initialize external API configuration"""
        return APIConfig(
            openai_key=self.env.get_optional("OPENAI_API_KEY"),
            serper_key=self.env.get_optional("SERPER_API_KEY"),
            unsplash_key=self.env.get_optional("UNSPLASH_ACCESS_KEY")
        )
    
    def _init_security(self) -> SecurityConfig:
        """Initialize security configuration"""
        return SecurityConfig(
            secret_key=self.env.get_string("SECRET_KEY", "dev-secret-key-change-in-production"),
            nextauth_secret=self.env.get_optional("NEXTAUTH_SECRET"),
            nextauth_url=self.env.get_string("NEXTAUTH_URL", "http://localhost:3001")
        )
    
    def get_cors_origins(self) -> List[str]:
        """Get allowed CORS origins based on environment"""
        origins = []
        
        # Always include development origins for local testing
        dev_origins = [
            'http://localhost:3000',
            'http://localhost:3001',
            'https://localhost:3000',
            'https://localhost:3001'
        ]
        origins.extend(dev_origins)
        
        # Add environment-specific origins
        if self.server.environment == 'production':
            production_domains = self.env.get_list('PRODUCTION_DOMAINS')
            origins.extend(production_domains)
        elif self.server.environment == 'staging':
            staging_url = self.env.get_string('STAGING_URL')
            if staging_url:
                origins.append(staging_url)
        
        # Add frontend URL if specified
        frontend_url = self.env.get_string('FRONTEND_URL')
        if frontend_url and frontend_url not in origins:
            origins.append(frontend_url)
        
        # Add NEXTAUTH_URL
        if self.security.nextauth_url and self.security.nextauth_url not in origins:
            origins.append(self.security.nextauth_url)
        
        return origins
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.server.environment == 'production'
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.server.environment == 'development'
    
    def validate_api_keys(self) -> Dict[str, bool]:
        """Validate that required API keys are configured"""
        return {
            'openai': bool(self.api.openai_key),
            'unsplash': bool(self.api.unsplash_key),
            'nextauth_secret': bool(self.security.nextauth_secret)
        }
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for debugging"""
        api_validation = self.validate_api_keys()
        
        return {
            'environment': self.server.environment,
            'debug': self.server.debug,
            'host': self.server.host,
            'port': self.server.port,
            'cors_origins_count': len(self.get_cors_origins()),
            'api_keys_configured': api_validation,
            'database_url_set': bool(self.database.url),
            'paths_base_dir': str(self.paths.base_dir)
        }


# Global configuration instance
config = UnifiedConfig()

# Convenience exports for backward compatibility
def get_config() -> UnifiedConfig:
    """Get the global configuration instance"""
    return config

def get_cors_origins() -> List[str]:
    """Convenience function for CORS origins"""
    return config.get_cors_origins()

def is_production() -> bool:
    """Convenience function to check production environment"""
    return config.is_production()

def get_openai_key() -> Optional[str]:
    """Convenience function for OpenAI API key"""
    return config.api.openai_key

def get_database_url() -> str:
    """Convenience function for database URL"""
    return config.database.url
