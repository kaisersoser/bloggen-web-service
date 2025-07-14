"""
Development and production environment configurations.
"""
import os
from .settings import Settings

class DevelopmentSettings(Settings):
    """Development environment settings."""
    DEBUG = True
    HOST = "localhost"
    PORT = 5000

class ProductionSettings(Settings):
    """Production environment settings."""
    DEBUG = False
    HOST = "0.0.0.0"
    PORT = int(os.getenv("PORT", "8000"))

class TestingSettings(Settings):
    """Testing environment settings."""
    DEBUG = True
    DATABASE_URL = ":memory:"  # Use in-memory database for tests

def get_settings():
    """Get settings based on environment."""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    elif env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()
