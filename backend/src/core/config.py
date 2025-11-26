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

# Load environment variables from .env file (only in development)
from dotenv import load_dotenv
backend_dir = Path(__file__).parent.parent.parent  # Go up to backend/ directory

# Simplified configuration loading: Single .env file for development
# In production environments (Railway, Docker), all config comes from environment variables
# .env files should be excluded via .dockerignore in production builds
env_file = backend_dir / ".env"

if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment from: .env")
else:
    # No .env file found - using system environment variables (production mode)
    print(f"ℹ️  No .env file - using system environment variables (production)")


@dataclass
class DatabaseConfig:
    """Database configuration settings"""

    url: str
    chroma_path: str


@dataclass
class APIConfig:
    """External API configuration"""

    openai_key: Optional[str]
    anthropic_key: Optional[str]
    google_key: Optional[str]
    serper_key: Optional[str]
    unsplash_key: Optional[str]
    replicate_key: Optional[str]
    
    # Image generation provider settings
    image_provider: str = "replicate"  # 'replicate' or 'openai'
    image_model: str = "google/imagen-3-fast"
    image_cost_per_generation: float = 0.025


@dataclass
class ModelsConfig:
    """Configuration for AI models used in blog generation."""

    # Content creation models (balanced performance/cost)
    content_model: str
    finalization_model: str

    # Research and reasoning models (high performance)
    research_model: str
    fact_check_model: str

    # Basic task models (cost efficient)
    default_model: str
    summary_model: str


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
class RateLimitConfig:
    """Rate limiting configuration"""

    enabled: bool = True
    tokens_per_minute: int = 30000
    requests_per_minute: int = 3500
    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    enable_chunking: bool = True


@dataclass
class FeatureConfig:
    """Feature toggle configuration"""

    enable_ai_image_generation: bool = True
    enable_hero_image_generation: bool = True
    enable_content_image_injection: bool = True
    
    # Quality improvement system configuration
    enable_quality_retries: bool = True
    max_research_retries: int = 2
    max_content_retries: int = 1


@dataclass
class TaskManagerConfig:
    """Task manager retention and cleanup configuration"""

    cleanup_interval_seconds: int = 300
    stale_incomplete_minutes: int = 90
    stale_completed_minutes: int = 4320  # 3 days
    redis_status_ttl_seconds: int = 3600
    max_cleanup_batch: int = 100
    redis_scan_count: int = 200


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
        required_vars = ["NEXTAUTH_SECRET"]
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
        return value in ("true", "1", "yes", "on")

    def get_optional(self, key: str) -> Optional[str]:
        """Get optional environment variable (returns None if not set)"""
        return os.getenv(key)

    def get_list(
        self, key: str, separator: str = ",", default: Optional[List[str]] = None
    ) -> List[str]:
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

        # Initialize configuration sections
        self.paths = self._init_paths()
        self.server = self._init_server()
        self.database = self._init_database()
        self.api = self._init_api()
        self.models = self._init_models()
        self.security = self._init_security()
        self.rate_limit = self._init_rate_limit()
        self.features = self._init_features()
        self.task_manager = self._init_task_manager()

        self.logger.info(
            f"Configuration initialized for environment: {self.server.environment}"
        )

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
            tasks_config=bloggen_dir / "config" / "tasks.yaml",
        )

    def _init_server(self) -> ServerConfig:
        """Initialize server configuration"""
        return ServerConfig(
            host=self.env.get_string("HOST", "localhost"),
            port=self.env.get_int("PORT", 5000),
            debug=self.env.get_bool("DEBUG", False),
            environment=self.env.get_string("ENVIRONMENT", "development").lower(),
        )

    def _init_database(self) -> DatabaseConfig:
        """Initialize database configuration"""
        default_chroma_path = str(self.paths.bloggen_dir / "db" / "chroma.sqlite3")

        return DatabaseConfig(
            url=self.env.get_string("DATABASE_URL", default_chroma_path),
            chroma_path=self.env.get_string("CHROMA_DB_PATH", default_chroma_path),
        )

    def _init_api(self) -> APIConfig:
        """Initialize external API configuration"""
        # Also set Google API key in environment for CrewAI/LiteLLM
        google_key = self.env.get_optional("GOOGLE_API_KEY")
        if google_key:
            os.environ["GOOGLE_API_KEY"] = google_key

        # LiteLLM requires GEMINI_API_KEY for direct Gemini API access
        gemini_key = self.env.get_optional("GEMINI_API_KEY")
        if gemini_key:
            os.environ["GEMINI_API_KEY"] = gemini_key

        anthropic_key = self.env.get_optional("ANTHROPIC_API_KEY")
        if anthropic_key:
            os.environ["ANTHROPIC_API_KEY"] = anthropic_key

        return APIConfig(
            openai_key=self.env.get_optional("OPENAI_API_KEY"),
            anthropic_key=anthropic_key,
            google_key=google_key,
            serper_key=self.env.get_optional("SERPER_API_KEY"),
            unsplash_key=self.env.get_optional("UNSPLASH_ACCESS_KEY"),
            replicate_key=self.env.get_optional("REPLICATE_API_KEY"),
            image_provider=os.getenv("IMAGE_PROVIDER", "replicate"),
            image_model=os.getenv("IMAGE_MODEL", "google/imagen-3-fast"),
            image_cost_per_generation=float(os.getenv("IMAGE_COST_PER_GENERATION", "0.025")),
        )

    def _init_models(self) -> ModelsConfig:
        """Initialize model configuration from environment variables."""
        return ModelsConfig(
            content_model=os.getenv("CONTENT_MODEL", "gpt-4o-mini"),
            research_model=os.getenv("RESEARCH_MODEL", "gpt-4o"),
            fact_check_model=os.getenv("FACT_CHECK_MODEL", "gpt-4o"),
            finalization_model=os.getenv("FINALIZATION_MODEL", "gpt-4o-mini"),
            default_model=os.getenv("DEFAULT_MODEL", "gpt-4o-mini"),
            summary_model=os.getenv("SUMMARY_MODEL", "gpt-4o-mini"),
        )

    def _init_security(self) -> SecurityConfig:
        """Initialize security configuration"""
        return SecurityConfig(
            secret_key=self.env.get_string(
                "SECRET_KEY", "dev-secret-key-change-in-production"
            ),
            nextauth_secret=self.env.get_optional("NEXTAUTH_SECRET"),
            nextauth_url=self.env.get_string("NEXTAUTH_URL", "http://localhost:3001"),
        )

    def _init_rate_limit(self) -> RateLimitConfig:
        """Initialize rate limiting configuration"""
        return RateLimitConfig(
            enabled=self.env.get_string("RATE_LIMIT_ENABLED", "true").lower() == "true",
            tokens_per_minute=self.env.get_int("RATE_LIMIT_TOKENS_PER_MINUTE", 30000),
            requests_per_minute=self.env.get_int(
                "RATE_LIMIT_REQUESTS_PER_MINUTE", 3500
            ),
            max_retries=self.env.get_int("RATE_LIMIT_MAX_RETRIES", 5),
            base_delay=float(self.env.get_string("RATE_LIMIT_BASE_DELAY", "1.0")),
            max_delay=float(self.env.get_string("RATE_LIMIT_MAX_DELAY", "60.0")),
            enable_chunking=self.env.get_string(
                "RATE_LIMIT_ENABLE_CHUNKING", "true"
            ).lower()
            == "true",
        )

    def _init_features(self) -> FeatureConfig:
        """Initialize feature toggle configuration"""
        return FeatureConfig(
            enable_ai_image_generation=self.env.get_bool(
                "ENABLE_AI_IMAGE_GENERATION", False
            ),
            enable_hero_image_generation=self.env.get_bool(
                "ENABLE_HERO_IMAGE_GENERATION", False
            ),
            enable_content_image_injection=self.env.get_bool(
                "ENABLE_CONTENT_IMAGE_INJECTION", False
            ),
            enable_quality_retries=self.env.get_bool(
                "ENABLE_QUALITY_RETRIES", True
            ),
            max_research_retries=self.env.get_int(
                "MAX_RESEARCH_RETRIES", 2
            ),
            max_content_retries=self.env.get_int(
                "MAX_CONTENT_RETRIES", 1
            ),
        )

    def _init_task_manager(self) -> TaskManagerConfig:
        """Initialize task manager cleanup configuration"""
        return TaskManagerConfig(
            cleanup_interval_seconds=self.env.get_int(
                "TASK_CLEANUP_INTERVAL_SECONDS", 300
            ),
            stale_incomplete_minutes=self.env.get_int(
                "TASK_STALE_INCOMPLETE_MINUTES", 90
            ),
            stale_completed_minutes=self.env.get_int(
                "TASK_STALE_COMPLETED_MINUTES", 4320
            ),
            redis_status_ttl_seconds=self.env.get_int(
                "TASK_REDIS_STATUS_TTL_SECONDS", 3600
            ),
            max_cleanup_batch=self.env.get_int("TASK_CLEANUP_BATCH_LIMIT", 100),
            redis_scan_count=self.env.get_int("TASK_REDIS_SCAN_COUNT", 200),
        )

    def get_cors_origins(self) -> List[str]:
        """Get allowed CORS origins based on environment"""
        origins = []

        # Always include development origins for local testing
        dev_origins = [
            "http://localhost:3000",
            "http://localhost:3001",
            "https://localhost:3000",
            "https://localhost:3001",
        ]
        origins.extend(dev_origins)

        # Add environment-specific origins
        if self.server.environment == "production":
            production_domains = self.env.get_list("PRODUCTION_DOMAINS")
            origins.extend(production_domains)
        elif self.server.environment == "staging":
            staging_url = self.env.get_string("STAGING_URL")
            if staging_url:
                origins.append(staging_url)

        # Add frontend URL if specified
        frontend_url = self.env.get_string("FRONTEND_URL")
        if frontend_url and frontend_url not in origins:
            origins.append(frontend_url)

        # Add NEXTAUTH_URL
        if self.security.nextauth_url and self.security.nextauth_url not in origins:
            origins.append(self.security.nextauth_url)

        return origins

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.server.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.server.environment == "development"

    def validate_api_keys(self) -> Dict[str, bool]:
        """Validate that required API keys are configured"""
        return {
            "openai": bool(self.api.openai_key),
            "google": bool(self.api.google_key),
            "unsplash": bool(self.api.unsplash_key),
            "nextauth_secret": bool(self.security.nextauth_secret),
        }

    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for debugging"""
        api_validation = self.validate_api_keys()

        return {
            "environment": self.server.environment,
            "debug": self.server.debug,
            "host": self.server.host,
            "port": self.server.port,
            "cors_origins_count": len(self.get_cors_origins()),
            "api_keys_configured": api_validation,
            "database_url_set": bool(self.database.url),
            "paths_base_dir": str(self.paths.base_dir),
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
