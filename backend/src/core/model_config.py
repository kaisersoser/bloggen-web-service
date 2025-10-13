"""
Centralized Model Configuration System

This module provides a single source of truth for all LLM model configurations,
including model names, pricing, rate limits, and fallback behaviors.
"""

import os
from typing import Dict, Tuple
from dataclasses import dataclass, field


@dataclass
class ModelConfig:
    """Configuration for a specific model"""

    name: str
    tokens_per_minute: int = 30000
    requests_per_minute: int = 3500
    input_price_per_1k: float = 0.0
    output_price_per_1k: float = 0.0
    context_window: int = 4096
    max_output_tokens: int = 4096
    is_preferred: bool = False


@dataclass
class ModelRepository:
    """Central repository for all model configurations"""

    # Default rate limits
    default_tokens_per_minute: int = 30000
    default_requests_per_minute: int = 3500

    # Model configurations
    models: Dict[str, ModelConfig] = field(
        default_factory=lambda: {
            # GPT-5 Series (Current Primary Models)
            "gpt-5": ModelConfig(
                name="gpt-5",
                tokens_per_minute=40000,
                requests_per_minute=12000,
                input_price_per_1k=0.0006,  # $0.60 per 1M tokens = $0.0006 per 1K tokens
                output_price_per_1k=0.0048,  # $4.80 per 1M tokens = $0.0048 per 1K tokens
                context_window=272000,  # 272K tokens per official specs
                max_output_tokens=128000,  # 128K tokens per official specs
                is_preferred=True,
            ),
            "gpt-5-mini": ModelConfig(
                name="gpt-5-mini",
                tokens_per_minute=250000,
                requests_per_minute=12000,
                input_price_per_1k=0.00025,  # $0.25 per 1M tokens = $0.00025 per 1K tokens
                output_price_per_1k=0.002,  # $2.00 per 1M tokens = $0.002 per 1K tokens
                context_window=400000,  # 400K tokens per official specs
                max_output_tokens=128000,  # 128K tokens per official specs
                is_preferred=True,
            ),
            "gpt-5-nano": ModelConfig(
                name="gpt-5-nano",
                tokens_per_minute=500000,
                requests_per_minute=15000,
                input_price_per_1k=0.00005,  # $0.05 per 1M tokens = $0.00005 per 1K tokens
                output_price_per_1k=0.0004,  # $0.40 per 1M tokens = $0.0004 per 1K tokens
                context_window=400000,  # 400K tokens per official specs
                max_output_tokens=128000,  # 128K tokens per official specs
                is_preferred=True,
            ),
            # GPT-4o Series (Legacy)
            "gpt-4o": ModelConfig(
                name="gpt-4o",
                tokens_per_minute=30000,
                requests_per_minute=10000,
                input_price_per_1k=0.005,
                output_price_per_1k=0.015,
                context_window=32768,
                max_output_tokens=8192,
            ),
            "gpt-4o-mini": ModelConfig(
                name="gpt-4o-mini",
                tokens_per_minute=200000,
                requests_per_minute=10000,
                input_price_per_1k=0.00015,
                output_price_per_1k=0.0006,
                context_window=16384,
                max_output_tokens=4096,
            ),
            # GPT-4 Series (Legacy)
            "gpt-4": ModelConfig(
                name="gpt-4",
                tokens_per_minute=10000,
                requests_per_minute=500,
                input_price_per_1k=0.03,
                output_price_per_1k=0.06,
                context_window=8192,
                max_output_tokens=4096,
            ),
            "gpt-4-turbo": ModelConfig(
                name="gpt-4-turbo",
                tokens_per_minute=30000,
                requests_per_minute=500,
                input_price_per_1k=0.01,
                output_price_per_1k=0.03,
                context_window=32768,
                max_output_tokens=8192,
            ),
            # GPT-3.5 Series (Legacy)
            "gpt-3.5-turbo": ModelConfig(
                name="gpt-3.5-turbo",
                tokens_per_minute=90000,
                requests_per_minute=3500,
                input_price_per_1k=0.0015,
                output_price_per_1k=0.002,
                context_window=4096,
                max_output_tokens=4096,
            ),
            # Google Gemini 2.5 Series (Primary Models)
            "gemini/gemini-2.5-pro": ModelConfig(
                name="gemini/gemini-2.5-pro",
                tokens_per_minute=4000000,  # 4M tokens per minute
                requests_per_minute=1000,  # 1000 requests per minute
                input_price_per_1k=0.00125,  # $1.25 per 1M tokens = $0.00125 per 1K tokens
                output_price_per_1k=0.01000,  # $10.00 per 1M tokens = $0.01000 per 1K tokens
                context_window=2097152,  # 2M token context window
                max_output_tokens=8192,  # 8K output tokens
                is_preferred=True,
            ),
            "gemini/gemini-2.5-flash": ModelConfig(
                name="gemini/gemini-2.5-flash",
                tokens_per_minute=4000000,  # 4M tokens per minute
                requests_per_minute=1000,  # 1000 requests per minute
                input_price_per_1k=0.00100,  # $1.00 per 1M tokens = $0.00100 per 1K tokens
                output_price_per_1k=0.00350,  # $3.50 per 1M tokens = $0.00350 per 1K tokens
                context_window=1048576,  # 1M token context window
                max_output_tokens=8192,  # 8K output tokens
                is_preferred=True,
            ),
            "gemini/gemini-2.5-flash-lite": ModelConfig(
                name="gemini/gemini-2.5-flash-lite",
                tokens_per_minute=4000000,  # 4M tokens per minute
                requests_per_minute=1000,  # 1000 requests per minute
                input_price_per_1k=0.000075,  # $0.075 per 1M tokens = $0.000075 per 1K tokens
                output_price_per_1k=0.00030,  # $0.30 per 1M tokens = $0.00030 per 1K tokens
                context_window=1048576,  # 1M token context window
                max_output_tokens=8192,  # 8K output tokens
                is_preferred=True,
            ),
            # Google Gemini 2.0 Series (Experimental)
            "gemini/gemini-2.0-flash-exp": ModelConfig(
                name="gemini/gemini-2.0-flash-exp",
                tokens_per_minute=4000000,  # 4M tokens per minute
                requests_per_minute=1000,  # 1000 requests per minute
                input_price_per_1k=0.00000,  # Currently free during experimental phase
                output_price_per_1k=0.00000,  # Currently free during experimental phase
                context_window=1048576,  # 1M token context window
                max_output_tokens=8192,  # 8K output tokens
                is_preferred=False,
            ),
            # Google Gemini 1.5 Series (Production Models)
            "gemini/gemini-1.5-pro": ModelConfig(
                name="gemini/gemini-1.5-pro",
                tokens_per_minute=4000000,  # 4M tokens per minute
                requests_per_minute=1000,  # 1000 requests per minute
                input_price_per_1k=0.0035,  # $3.50 per 1M tokens = $0.0035 per 1K tokens
                output_price_per_1k=0.0105,  # $10.50 per 1M tokens = $0.0105 per 1K tokens
                context_window=2097152,  # 2M token context window
                max_output_tokens=8192,  # 8K output tokens
                is_preferred=False,
            ),
            "gemini/gemini-1.5-flash": ModelConfig(
                name="gemini/gemini-1.5-flash",
                tokens_per_minute=4000000,  # 4M tokens per minute
                requests_per_minute=1000,  # 1000 requests per minute
                input_price_per_1k=0.000075,  # $0.075 per 1M tokens = $0.000075 per 1K tokens
                output_price_per_1k=0.0003,  # $0.30 per 1M tokens = $0.0003 per 1K tokens
                context_window=1048576,  # 1M token context window
                max_output_tokens=8192,  # 8K output tokens
                is_preferred=False,
            ),
        }
    )

    def get_model_config(self, model_name: str) -> ModelConfig:
        """Get configuration for a specific model"""
        normalized_name = self._normalize_model_name(model_name)

        if normalized_name in self.models:
            return self.models[normalized_name]

        # Return default configuration for unknown models
        return ModelConfig(
            name=normalized_name,
            tokens_per_minute=self.default_tokens_per_minute,
            requests_per_minute=self.default_requests_per_minute,
            input_price_per_1k=0.001,  # Conservative estimate
            output_price_per_1k=0.002,
        )

    def get_rate_limits(self, model_name: str) -> Tuple[int, int]:
        """Get rate limits for a model (tokens_per_minute, requests_per_minute)"""
        config = self.get_model_config(model_name)
        return config.tokens_per_minute, config.requests_per_minute

    def get_pricing(self, model_name: str) -> Dict[str, float]:
        """Get pricing for a model"""
        config = self.get_model_config(model_name)
        return {
            "input": config.input_price_per_1k,
            "output": config.output_price_per_1k,
        }

    def _normalize_model_name(self, model_name: str) -> str:
        """Normalize model names to match our configuration keys"""
        normalized = model_name.lower().strip()

        # Handle Gemini models (check for exact matches first)
        if normalized == "gemini/gemini-2.5-pro":
            return "gemini/gemini-2.5-pro"
        elif normalized == "gemini/gemini-2.5-flash":
            return "gemini/gemini-2.5-flash"
        elif normalized == "gemini/gemini-2.5-flash-lite":
            return "gemini/gemini-2.5-flash-lite"
        elif normalized == "gemini/gemini-2.0-flash-exp":
            return "gemini/gemini-2.0-flash-exp"
        elif normalized == "gemini/gemini-1.5-pro":
            return "gemini/gemini-1.5-pro"
        elif normalized == "gemini/gemini-1.5-flash":
            return "gemini/gemini-1.5-flash"
        # Handle partial Gemini matches
        elif "gemini-2.5-pro" in normalized:
            return "gemini/gemini-2.5-pro"
        elif "gemini-2.5-flash-lite" in normalized:
            return "gemini/gemini-2.5-flash-lite"
        elif "gemini-2.5-flash" in normalized:
            return "gemini/gemini-2.5-flash"
        elif "gemini-2.0-flash-exp" in normalized:
            return "gemini/gemini-2.0-flash-exp"
        elif "gemini-1.5-pro" in normalized:
            return "gemini/gemini-1.5-pro"
        elif "gemini-1.5-flash" in normalized:
            return "gemini/gemini-1.5-flash"

        # Handle GPT-5 models (most specific first)
        elif normalized.startswith("gpt-5-nano"):
            return "gpt-5-nano"
        elif normalized.startswith("gpt-5-mini"):
            return "gpt-5-mini"
        elif normalized.startswith("gpt-5"):
            return "gpt-5"
        # Handle GPT-4o models
        elif normalized.startswith("gpt-4o-mini"):
            return "gpt-4o-mini"
        elif normalized.startswith("gpt-4o"):
            return "gpt-4o"
        # Handle GPT-4 models
        elif normalized.startswith("gpt-4-turbo"):
            return "gpt-4-turbo"
        elif normalized.startswith("gpt-4"):
            return "gpt-4"
        # Handle GPT-3.5 models
        elif normalized.startswith("gpt-3.5-turbo"):
            return "gpt-3.5-turbo"

        return normalized


# Global model repository instance
model_repository = ModelRepository()


def get_env_model(env_var: str, default: str = "gemini/gemini-2.5-flash-lite") -> str:
    """Get model name from environment variable with fallback"""
    return os.getenv(env_var, default)


def get_content_model() -> str:
    """Get the content generation model from environment"""
    return get_env_model("CONTENT_MODEL", "gemini/gemini-2.5-flash-lite")


def get_research_model() -> str:
    """Get the research model from environment"""
    return get_env_model("RESEARCH_MODEL", "gemini/gemini-2.5-flash")


def get_fact_check_model() -> str:
    """Get the fact-checking model from environment"""
    return get_env_model("FACT_CHECK_MODEL", "gemini/gemini-2.5-flash")


def get_finalization_model() -> str:
    """Get the finalization model from environment"""
    return get_env_model("FINALIZATION_MODEL", "gemini/gemini-2.5-flash-lite")


def get_default_model() -> str:
    """Get the default model from environment"""
    return get_env_model("DEFAULT_MODEL", "gemini/gemini-2.5-flash-lite")


def get_summary_model() -> str:
    """Get the summary model from environment"""
    return get_env_model("SUMMARY_MODEL", "gpt-5-nano")


def get_legacy_model() -> str:
    """Get the legacy MODEL from environment (for backwards compatibility)"""
    return get_env_model("MODEL", "gpt-5-mini")


def get_researcher_model() -> str:
    """Get the legacy RESEARCHER_MODEL from environment (for backwards compatibility)"""
    return get_env_model("RESEARCHER_MODEL", "gpt-5")


# Convenience functions for getting configurations
def get_model_rate_limits(model_name: str) -> Tuple[int, int]:
    """Get rate limits for a model"""
    return model_repository.get_rate_limits(model_name)


def get_model_pricing(model_name: str) -> Dict[str, float]:
    """Get pricing for a model"""
    return model_repository.get_pricing(model_name)


def get_model_config(model_name: str) -> ModelConfig:
    """Get full configuration for a model"""
    return model_repository.get_model_config(model_name)


if __name__ == "__main__":
    # Test the centralized model configuration
    print("🧪 Testing Centralized Model Configuration")
    print("=" * 50)
    print(f"Default Model:        {get_default_model()}")
    print(f"Content Model:        {get_content_model()}")
    print(f"Research Model:       {get_research_model()}")
    print(f"Finalization Model:   {get_finalization_model()}")
    print()

    print("📊 Model Pricing Test")
    print("=" * 50)
    for model_name in [get_default_model(), get_content_model(), get_research_model()]:
        config = model_repository.get_model_config(model_name)
        print(
            f"{model_name}: ${config.input_price_per_1k:.6f} input, ${config.output_price_per_1k:.6f} output"
        )

    print("\n✅ Centralized Model Configuration Test Complete!")
