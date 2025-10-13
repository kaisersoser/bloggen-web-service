"""
Rate Limiting Configuration for Blog Generation Service

This module provides configuration management for rate limiting settings
that can prevent OpenAI API rate limit errors.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from core.rate_limiter import RateLimitConfig


@dataclass
class BlogGenRateLimitConfig(RateLimitConfig):
    """Extended rate limit configuration for blog generation"""

    # Model-specific token limits (updated for GPT-5 models)
    model_limits: Dict[str, Dict[str, int]] = field(
        default_factory=lambda: {
            # GPT-5 family (latest models for blog generation)
            "gpt-5": {"tokens_per_minute": 40000, "requests_per_minute": 12000},
            "gpt-5-mini": {"tokens_per_minute": 250000, "requests_per_minute": 12000},
            "gpt-5-nano": {"tokens_per_minute": 500000, "requests_per_minute": 15000},
            # GPT-4o family (legacy support)
            "gpt-4o": {"tokens_per_minute": 30000, "requests_per_minute": 10000},
            "gpt-4o-mini": {"tokens_per_minute": 200000, "requests_per_minute": 10000},
            # GPT-4 family
            "gpt-4": {"tokens_per_minute": 10000, "requests_per_minute": 500},
            "gpt-4-turbo": {"tokens_per_minute": 30000, "requests_per_minute": 500},
            "gpt-4-1106-preview": {
                "tokens_per_minute": 30000,
                "requests_per_minute": 500,
            },
            # GPT-3.5 family (fallback models)
            "gpt-3.5-turbo": {"tokens_per_minute": 90000, "requests_per_minute": 3500},
            "gpt-3.5-turbo-16k": {
                "tokens_per_minute": 90000,
                "requests_per_minute": 3500,
            },
            # Claude models (if using via OpenAI-compatible API)
            "claude-3-opus": {"tokens_per_minute": 20000, "requests_per_minute": 1000},
            "claude-3-sonnet": {
                "tokens_per_minute": 40000,
                "requests_per_minute": 1000,
            },
            "claude-3-haiku": {
                "tokens_per_minute": 100000,
                "requests_per_minute": 1000,
            },
        }
    )

    # Phase-specific configurations
    phase_configs: Dict[str, Dict[str, Any]] = field(
        default_factory=lambda: {
            "research": {
                "estimated_tokens": 15000,
                "max_retries": 5,
                "preferred_model": "gpt-5",
                "chunk_size": 20000,
            },
            "content_generation": {
                "estimated_tokens": 12000,
                "max_retries": 3,
                "preferred_model": "gpt-5-mini",
                "chunk_size": 25000,
            },
            "fact_checking": {
                "estimated_tokens": 8000,
                "max_retries": 4,
                "preferred_model": "gpt-4o",
                "chunk_size": 15000,
            },
            "finalization": {
                "estimated_tokens": 6000,
                "max_retries": 3,
                "preferred_model": "gpt-4o-mini",
                "chunk_size": 10000,
            },
            "title_generation": {
                "estimated_tokens": 2000,
                "max_retries": 3,
                "preferred_model": "gpt-4o-mini",
                "chunk_size": 5000,
            },
        }
    )

    # Aggressive rate limiting for free tier users
    free_tier_limits: Dict[str, int] = field(
        default_factory=lambda: {
            "tokens_per_minute": 15000,  # Half the default
            "requests_per_minute": 50,  # Very conservative
            "max_concurrent_requests": 1,
        }
    )

    # Environment-based overrides
    enable_rate_limiting: bool = True
    enable_chunking: bool = True
    enable_retries: bool = True

    # Safety settings
    emergency_cooldown: int = 300  # 5 minutes cooldown if repeated failures
    max_failures_before_cooldown: int = 3


def get_rate_limit_config_from_env() -> BlogGenRateLimitConfig:
    """Create rate limit configuration from environment variables"""

    config = BlogGenRateLimitConfig()

    # Override from environment variables
    tpm_env = os.getenv("RATE_LIMIT_TOKENS_PER_MINUTE")
    if tpm_env:
        config.tokens_per_minute = int(tpm_env)

    rpm_env = os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE")
    if rpm_env:
        config.requests_per_minute = int(rpm_env)

    retries_env = os.getenv("RATE_LIMIT_MAX_RETRIES")
    if retries_env:
        config.max_retries = int(retries_env)

    base_delay_env = os.getenv("RATE_LIMIT_BASE_DELAY")
    if base_delay_env:
        config.base_delay = float(base_delay_env)

    max_delay_env = os.getenv("RATE_LIMIT_MAX_DELAY")
    if max_delay_env:
        config.max_delay = float(max_delay_env)

    # Feature flags
    config.enable_rate_limiting = (
        os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true"
    )
    config.enable_chunking = (
        os.getenv("ENABLE_REQUEST_CHUNKING", "true").lower() == "true"
    )
    config.enable_retries = os.getenv("ENABLE_RETRY_LOGIC", "true").lower() == "true"

    return config


def get_phase_config(
    phase: str, config: Optional[BlogGenRateLimitConfig] = None
) -> Dict[str, Any]:
    """Get configuration for a specific blog generation phase"""
    if config is None:
        config = get_rate_limit_config_from_env()

    return config.phase_configs.get(
        phase,
        {
            "estimated_tokens": 10000,
            "max_retries": 3,
            "preferred_model": "gpt-4o-mini",
            "chunk_size": 20000,
        },
    )


def suggest_model_for_phase(phase: str, user_tier: str = "premium") -> str:
    """Suggest the best model for a phase based on user tier and requirements"""
    config = get_rate_limit_config_from_env()
    phase_config = config.phase_configs.get(phase, {})

    preferred_model = phase_config.get("preferred_model", "gpt-5-mini")

    # Ensure we always have a string return value
    if not isinstance(preferred_model, str):
        preferred_model = "gpt-5-mini"

    # Downgrade models for free tier users
    if user_tier == "free":
        model_downgrades = {
            "gpt-5": "gpt-5-mini",
            "gpt-5-mini": "gpt-5-nano",
            "gpt-4o": "gpt-4o-mini",
            "gpt-4": "gpt-4o-mini",
            "gpt-4-turbo": "gpt-4o-mini",
        }
        preferred_model = model_downgrades.get(preferred_model, preferred_model)

    return preferred_model


def get_adaptive_rate_limits(recent_failures: int = 0) -> Dict[str, int]:
    """Get adaptive rate limits based on recent API failures"""
    config = get_rate_limit_config_from_env()

    base_tpm = config.tokens_per_minute
    base_rpm = config.requests_per_minute

    # Reduce limits if we've had recent failures
    if recent_failures > 0:
        reduction_factor = max(0.3, 1.0 - (recent_failures * 0.2))

        return {
            "tokens_per_minute": int(base_tpm * reduction_factor),
            "requests_per_minute": int(base_rpm * reduction_factor),
        }

    return {"tokens_per_minute": base_tpm, "requests_per_minute": base_rpm}


# Export default configuration
default_config = get_rate_limit_config_from_env()


if __name__ == "__main__":
    # Test configuration
    config = get_rate_limit_config_from_env()
    print(f"Rate limiting enabled: {config.enable_rate_limiting}")
    print(f"Default TPM: {config.tokens_per_minute}")
    print(f"Default RPM: {config.requests_per_minute}")

    for phase in ["research", "content_generation", "fact_checking", "finalization"]:
        phase_config = get_phase_config(phase, config)
        print(
            f"{phase}: {phase_config['estimated_tokens']} tokens, {phase_config['preferred_model']} model"
        )
