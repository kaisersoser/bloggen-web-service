"""
Pricing constants for cost calculation.

This module contains only pricing information to avoid circular imports
between core and bloggen modules.
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
    "gpt-3.5-turbo-16k": {
        "input": 0.003,
        "output": 0.004
    },
    "gpt-4-32k": {
        "input": 0.06,
        "output": 0.12
    },
    "gpt-4o": {
        "input": 0.005,
        "output": 0.015
    },
    "gpt-4o-mini": {
        "input": 0.00015,
        "output": 0.0006
    }
}

def normalize_model_name(model_name: str) -> str:
    """
    Normalize model names to match pricing keys.
    
    Args:
        model_name: The raw model name from the API
        
    Returns:
        Normalized model name that matches OPENAI_PRICING keys
    """
    # Remove version suffixes and normalize common variations
    normalized = model_name.lower().strip()
    
    # Handle versioned models
    if normalized.startswith('gpt-4-turbo'):
        return 'gpt-4-turbo'
    elif normalized.startswith('gpt-4-32k'):
        return 'gpt-4-32k'
    elif normalized.startswith('gpt-4o-mini'):
        return 'gpt-4o-mini'
    elif normalized.startswith('gpt-4o'):
        return 'gpt-4o'
    elif normalized.startswith('gpt-4'):
        return 'gpt-4'
    elif normalized.startswith('gpt-3.5-turbo-16k'):
        return 'gpt-3.5-turbo-16k'
    elif normalized.startswith('gpt-3.5-turbo'):
        return 'gpt-3.5-turbo'
    
    # Return as-is if no normalization needed
    return model_name
