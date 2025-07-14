"""
Centralized configuration management for the blog generator application.
"""
import os
from pathlib import Path
from typing import Optional

# Base directories
BASE_DIR = Path(__file__).parent.parent.parent
SRC_DIR = BASE_DIR / "src"
BLOGGEN_DIR = SRC_DIR / "bloggen"

class Settings:
    """Application settings and configuration."""
    
    # API Settings
    HOST: str = os.getenv("HOST", "localhost")
    PORT: int = int(os.getenv("PORT", "5000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Database Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", str(BLOGGEN_DIR / "db" / "chroma.sqlite3"))
    
    # External APIs
    UNSPLASH_ACCESS_KEY: Optional[str] = os.getenv("UNSPLASH_ACCESS_KEY")
    
    # CrewAI Settings
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
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
