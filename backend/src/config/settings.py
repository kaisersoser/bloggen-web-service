"""
Centralized configuration management for the blog generator application.

DEPRECATED: This module is deprecated in favor of core.config.py
Please use the new unified configuration system instead.
"""
import os
from pathlib import Path
from typing import Optional

# Import the new unified configuration
from core.config import config as unified_config
from core.database_config import get_chroma_db_path

# Base directories - now delegated to unified config
BASE_DIR = unified_config.paths.base_dir
SRC_DIR = unified_config.paths.src_dir
BLOGGEN_DIR = unified_config.paths.bloggen_dir

class Settings:
    """Application settings and configuration - DEPRECATED: Use core.config instead"""
    
    # API Settings - now delegates to unified config
    HOST: str = unified_config.server.host
    PORT: int = unified_config.server.port
    DEBUG: bool = unified_config.server.debug
    
    # Database Settings - now uses centralized database configuration
    DATABASE_URL: str = get_chroma_db_path()
    
    # External APIs - now delegates to unified config
    UNSPLASH_ACCESS_KEY: Optional[str] = unified_config.api.unsplash_key
    
    # CrewAI Settings - now delegates to unified config
    OPENAI_API_KEY: Optional[str] = unified_config.api.openai_key
    
    # File Paths
    AGENTS_CONFIG: Path = BLOGGEN_DIR / "config" / "agents.yaml"
    TASKS_CONFIG: Path = BLOGGEN_DIR / "config" / "tasks.yaml"
    LOGS_DIR: Path = BLOGGEN_DIR / "logs"
    
    # WebSocket Settings
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:3001"]
    
    @classmethod
    def validate(cls) -> None:
        """Validate required environment variables."""
        required_vars = ["UNSPLASH_ACCESS_KEY", "OPENAI_API_KEY"]
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    @classmethod
    def create_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        Path(cls.DATABASE_URL).parent.mkdir(parents=True, exist_ok=True)

settings = Settings()
