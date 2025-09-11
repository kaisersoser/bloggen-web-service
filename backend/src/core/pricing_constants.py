"""
Pricing constants for cost calculation.

This module contains only pricing information to avoid circular imports
between core and bloggen modules.
"""

"""
Pricing constants for cost calculation.

This module contains only pricing information to avoid circular imports
between core and bloggen modules.
"""

# LLM pricing per 1K tokens (updated for GPT-5 and Gemini models)
# Sources: OpenAI pricing, Google AI pricing
LLM_PRICING = {
    # OpenAI GPT Models
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
    },
    # GPT-5 model pricing (official OpenAI pricing August 2025)
    # Source: OpenAI pricing table - per 1M tokens converted to per 1K tokens
    "gpt-5": {
        "input": 0.0006,   # $0.60 per 1M tokens = $0.0006 per 1K tokens
        "output": 0.0048   # $4.80 per 1M tokens = $0.0048 per 1K tokens
    },
    "gpt-5-mini": {
        "input": 0.00025,  # $0.25 per 1M tokens = $0.00025 per 1K tokens
        "output": 0.002    # $2.00 per 1M tokens = $0.002 per 1K tokens
    },
    "gpt-5-nano": {
        "input": 0.00005,  # $0.05 per 1M tokens = $0.00005 per 1K tokens
        "output": 0.0004   # $0.40 per 1M tokens = $0.0004 per 1K tokens
    },
    
    # Google Gemini Models
    # Source: Google AI pricing (September 2025) - per 1M tokens converted to per 1K tokens
    "gemini/gemini-2.5-pro": {
        "input": 0.00125,  # $1.25 per 1M tokens = $0.00125 per 1K tokens (≤200k context)
        "output": 0.01000  # $10.00 per 1M tokens = $0.01000 per 1K tokens (≤200k context)
        # Note: Higher rates apply for >200k tokens: $2.50 input, $15.00 output per 1M
    },
    "gemini/gemini-2.5-flash": {
        "input": 0.00100,  # $1.00 per 1M tokens = $0.00100 per 1K tokens
        "output": 0.00350  # $3.50 per 1M tokens = $0.00350 per 1K tokens
    },
    "gemini/gemini-2.5-flash-lite": {
        "input": 0.000075, # $0.075 per 1M tokens = $0.000075 per 1K tokens
        "output": 0.00030  # $0.30 per 1M tokens = $0.00030 per 1K tokens
    },
    # Legacy Gemini models (keeping for backward compatibility)
    "gemini/gemini-2.0-flash-exp": {
        "input": 0.00000,  # Currently free during experimental phase
        "output": 0.00000  # Currently free during experimental phase
    },
    "gemini/gemini-1.5-pro": {
        "input": 0.0035,   # $3.50 per 1M tokens = $0.0035 per 1K tokens
        "output": 0.0105   # $10.50 per 1M tokens = $0.0105 per 1K tokens
    },
    "gemini/gemini-1.5-flash": {
        "input": 0.000075, # $0.075 per 1M tokens = $0.000075 per 1K tokens
        "output": 0.0003   # $0.30 per 1M tokens = $0.0003 per 1K tokens
    }
}

# Backward compatibility alias
OPENAI_PRICING = LLM_PRICING

def normalize_model_name(model_name: str) -> str:
    """
    Normalize model names to match pricing keys.
    
    Args:
        model_name: The raw model name from the API
        
    Returns:
        Normalized model name that matches LLM_PRICING keys
    """
    # Remove version suffixes and normalize common variations
    normalized = model_name.lower().strip()
    
    # Handle Gemini models first (exact matches)
    if normalized == 'gemini/gemini-2.5-pro':
        return 'gemini/gemini-2.5-pro'
    elif normalized == 'gemini/gemini-2.5-flash':
        return 'gemini/gemini-2.5-flash'
    elif normalized == 'gemini/gemini-2.5-flash-lite':
        return 'gemini/gemini-2.5-flash-lite'
    elif normalized == 'gemini/gemini-2.0-flash-exp':
        return 'gemini/gemini-2.0-flash-exp'
    elif normalized == 'gemini/gemini-1.5-pro':
        return 'gemini/gemini-1.5-pro'
    elif normalized == 'gemini/gemini-1.5-flash':
        return 'gemini/gemini-1.5-flash'
    # Handle partial Gemini matches
    elif 'gemini-2.5-pro' in normalized:
        return 'gemini/gemini-2.5-pro'
    elif 'gemini-2.5-flash-lite' in normalized:
        return 'gemini/gemini-2.5-flash-lite'
    elif 'gemini-2.5-flash' in normalized:
        return 'gemini/gemini-2.5-flash'
    elif 'gemini-2.0-flash-exp' in normalized:
        return 'gemini/gemini-2.0-flash-exp'
    elif 'gemini-1.5-pro' in normalized:
        return 'gemini/gemini-1.5-pro'
    elif 'gemini-1.5-flash' in normalized:
        return 'gemini/gemini-1.5-flash'
    
    # Handle GPT-5 models first (more specific)
    elif normalized.startswith('gpt-5-nano'):
        return 'gpt-5-nano'
    elif normalized.startswith('gpt-5-mini'):
        return 'gpt-5-mini'
    elif normalized.startswith('gpt-5'):
        return 'gpt-5'
    # Handle versioned models
    elif normalized.startswith('gpt-4-turbo'):
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
