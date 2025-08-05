# Add your utilities or helper functions to this file.

from core.common import config, get_logger

# Migration note: This file now uses centralized configuration
# from core.config for consistent environment management

def load_env():
    """Load environment variables - now handled by unified config"""
    # Environment loading is now handled automatically by unified config
    # This function is kept for backward compatibility
    pass

def get_openai_api_key():
    """Get OpenAI API key from centralized config"""
    return config.api.openai_key

def get_serper_api_key():
    """Get Serper API key from centralized config"""
    return config.api.serper_key

def get_researcher_model():
    """Get researcher model from centralized config"""
    # This should be added to the API config, for now use environment variable
    import os
    return os.getenv("RESEARCHER_MODEL")

def get_database_path():
    """Get database path from centralized config"""
    from core.database_config import get_chroma_db_path
    return get_chroma_db_path()

def get_api_config():
    """Get all API configuration from centralized config"""
    import os
    return {
        'openai_api_key': config.api.openai_key,
        'serper_api_key': config.api.serper_key,
        'researcher_model': os.getenv("RESEARCHER_MODEL"),
        'unsplash_access_key': config.api.unsplash_key
    }