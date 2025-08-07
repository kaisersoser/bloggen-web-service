"""
Shared constants and configurations for the blog generation system.

This module contains pricing information, model configurations, and other
constants that are used across multiple modules to avoid duplication.
"""

# OpenAI pricing per 1K tokens (as of 2024)
# Source: https://openai.com/pricing
OPENAI_PRICING = {
    "gpt-4": {
        "input": 0.03,
        "output": 0.06
    },
    "gpt-4-turbo": {
        "input": 0.01,
        "output": 0.03
    },
    "gpt-3.5-turbo": {
        "input": 0.0015,
        "output": 0.002
    },
    "gpt-4o": {
        "input": 0.0025,
        "output": 0.01
    },
    "gpt-4o-mini": {
        "input": 0.00015,
        "output": 0.0006
    },
    # Remove GPT-4.1 series - using real OpenAI models instead
    "gpt-4o": {
        "input": 0.0025,
        "output": 0.01
    },
    "gpt-4o-mini": {
        "input": 0.00015,
        "output": 0.0006
    }
}

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

def normalize_model_name(model: str) -> str:
    """
    Normalize model name to match pricing keys.
    
    Args:
        model: Raw model name from API
        
    Returns:
        Normalized model name for pricing lookup
    """
    model = model.lower()
    
    if "gpt-4o-mini" in model:
        return "gpt-4o-mini"
    elif "gpt-4o" in model:
        return "gpt-4o"
    elif "gpt-4-turbo" in model:
        return "gpt-4-turbo"
    elif "gpt-4" in model:
        return "gpt-4"
    elif "gpt-3.5" in model:
        return "gpt-3.5-turbo"
    else:
        return "gpt-4o-mini"  # Default to most efficient model

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
