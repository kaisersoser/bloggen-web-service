"""
Shared constants and configurations for the blog generation system.

This module contains pricing information, model configurations, and other
constants that are used across multiple modules to avoid duplication.
"""

# Import pricing constants from core to avoid circular imports
from core.pricing_constants import OPENAI_PRICING, normalize_model_name

# Default model for cost estimation
DEFAULT_MODEL = "gpt-4o-mini"

# Model name normalization mapping
MODEL_NAME_MAPPING = {
    "gpt-4o-mini": "gpt-4o-mini",
    "gpt-4o": "gpt-4o", 
    "gpt-4-turbo": "gpt-4-turbo",
    "gpt-4": "gpt-4",
    "gpt-3.5-turbo": "gpt-3.5-turbo"
}

# Tool configurations
MAX_SEARCH_RESULTS = 5
MAX_CONTENT_LENGTH = 50000
DEFAULT_TEMPERATURE = 0.7

# Blog generation settings
MIN_BLOG_LENGTH = 1000
MAX_BLOG_LENGTH = 10000
DEFAULT_BLOG_SECTIONS = [
    "Introduction", 
    "Main Content", 
    "Analysis", 
    "Conclusion"
]

# Rate limiting settings
MAX_REQUESTS_PER_MINUTE = 60
MAX_TOKENS_PER_REQUEST = 8000

# Image generation settings
MAX_IMAGES_PER_BLOG = 3
DEFAULT_IMAGE_SIZE = "1024x1024"
IMAGE_QUALITY = "standard"

def calculate_openai_cost(model: str, input_tokens: int, output_tokens: int, cached_tokens: int = 0) -> tuple[float, float, float, float]:
    """
    Calculate cost based on OpenAI pricing with support for cached input.
    
    Args:
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cached_tokens: Number of cached input tokens (default: 0)
        
    Returns:
        Tuple of (input_cost, cached_cost, output_cost, total_cost)
    """
    model_key = normalize_model_name(model)
    
    if model_key not in OPENAI_PRICING:
        model_key = "gpt-4o-mini"  # Default to most efficient model
        
    pricing = OPENAI_PRICING[model_key]
    
    input_cost = (input_tokens / 1000) * pricing["input"]
    output_cost = (output_tokens / 1000) * pricing["output"]
    
    # Calculate cached input cost if supported
    cached_cost = 0.0
    if cached_tokens > 0 and "cached_input" in pricing:
        cached_cost = (cached_tokens / 1000) * pricing["cached_input"]
    
    total_cost = input_cost + cached_cost + output_cost
    
    return input_cost, cached_cost, output_cost, total_cost

# Legacy function for backward compatibility
def calculate_openai_cost_legacy(model: str, input_tokens: int, output_tokens: int) -> tuple[float, float, float]:
    """Legacy cost calculation function for backward compatibility."""
    input_cost, _, output_cost, total_cost = calculate_openai_cost(model, input_tokens, output_tokens)
    return input_cost, output_cost, total_cost
