"""
Advanced Rate Limiting and Retry Logic for LLM API Calls

This module provides comprehensive rate limiting, retry with exponential backoff,
and intelligent token management to prevent API rate limit errors.
"""

import asyncio
import time
import random
import logging
from typing import Any, Callable, Dict, Optional, Tuple
from dataclasses import dataclass
from functools import wraps
import threading
from collections import deque

from core.model_config import model_repository

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting behavior"""

    # Default limits (will be overridden by model-specific configs)
    tokens_per_minute: int = 30000
    requests_per_minute: int = 3500

    # Retry configuration
    max_retries: int = 5
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    exponential_base: float = 2.0  # Exponential backoff multiplier
    jitter: bool = True  # Add random jitter to prevent thundering herd

    # Token management
    token_buffer: float = 0.1  # Keep 10% buffer to avoid edge cases
    chunk_size: int = 25000  # Split large requests into chunks


class TokenBucket:
    """Token bucket implementation for rate limiting"""

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self._lock = threading.Lock()

    def consume(self, tokens: int) -> bool:
        """Try to consume tokens from bucket. Returns True if successful."""
        with self._lock:
            now = time.time()
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            tokens_to_add = elapsed * self.refill_rate
            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
            self.last_refill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def time_until_tokens(self, tokens: int) -> float:
        """Calculate time until we have enough tokens"""
        with self._lock:
            if self.tokens >= tokens:
                return 0.0
            needed_tokens = tokens - self.tokens
            return needed_tokens / self.refill_rate


class AdvancedRateLimiter:
    """Advanced rate limiter with token bucket and exponential backoff"""

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._token_buckets: Dict[str, TokenBucket] = {}
        self._request_buckets: Dict[str, TokenBucket] = {}
        self._lock = threading.Lock()

        # Request tracking for monitoring
        self.request_history: deque = deque(maxlen=1000)

    def _get_model_limits(self, model: str) -> Tuple[int, int]:
        """Get token and request limits for a specific model"""
        return model_repository.get_rate_limits(model)

    def _get_or_create_buckets(self, model: str) -> Tuple[TokenBucket, TokenBucket]:
        """Get or create token buckets for a model"""
        with self._lock:
            if model not in self._token_buckets:
                token_limit, request_limit = self._get_model_limits(model)

                # Create buckets with per-second refill rates
                self._token_buckets[model] = TokenBucket(
                    capacity=token_limit, refill_rate=token_limit / 60.0  # Per second
                )
                self._request_buckets[model] = TokenBucket(
                    capacity=request_limit,
                    refill_rate=request_limit / 60.0,  # Per second
                )

                logger.info(
                    f"Created rate limiters for {model}: {token_limit} TPM, {request_limit} RPM"
                )

            return self._token_buckets[model], self._request_buckets[model]

    async def acquire(self, model: str, estimated_tokens: int) -> bool:
        """Acquire permission to make an API call"""
        token_bucket, request_bucket = self._get_or_create_buckets(model)

        # Apply safety buffer
        safe_tokens = int(estimated_tokens * (1 + self.config.token_buffer))

        # Check if we can make the request
        if token_bucket.consume(safe_tokens) and request_bucket.consume(1):
            self.request_history.append(
                {"model": model, "tokens": estimated_tokens, "timestamp": time.time()}
            )
            return True

        # Calculate wait time
        token_wait = token_bucket.time_until_tokens(safe_tokens)
        request_wait = request_bucket.time_until_tokens(1)
        wait_time = max(token_wait, request_wait)

        if wait_time > 0:
            logger.info(
                f"Rate limited for {model}. Waiting {wait_time:.2f}s for {estimated_tokens} tokens"
            )
            await asyncio.sleep(wait_time)
            return await self.acquire(model, estimated_tokens)

        return False

    def should_chunk_request(self, estimated_tokens: int, model: str) -> bool:
        """Determine if a request should be chunked"""
        token_limit, _ = self._get_model_limits(model)
        return estimated_tokens > self.config.chunk_size

    def get_chunk_size(self, model: str) -> int:
        """Get optimal chunk size for a model"""
        token_limit, _ = self._get_model_limits(model)
        return min(self.config.chunk_size, int(token_limit * 0.8))


def exponential_backoff_retry(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    rate_limiter: Optional[AdvancedRateLimiter] = None,
):
    """
    Decorator for exponential backoff retry with rate limiting

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for first retry
        max_delay: Maximum delay in seconds
        exponential_base: Multiplier for exponential backoff
        jitter: Add random jitter to prevent thundering herd
        rate_limiter: Optional rate limiter instance
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)

                except Exception as e:
                    last_exception = e
                    error_str = str(e).lower()

                    # Check if it's a rate limit error
                    is_rate_limit = any(
                        term in error_str
                        for term in [
                            "rate limit",
                            "too many requests",
                            "quota exceeded",
                            "requests per minute",
                            "tokens per minute",
                        ]
                    )

                    # Check if it's a retryable error
                    is_retryable = is_rate_limit or any(
                        term in error_str
                        for term in [
                            "timeout",
                            "connection",
                            "network",
                            "server error",
                            "502",
                            "503",
                            "504",
                        ]
                    )

                    if not is_retryable or attempt >= max_retries:
                        logger.error(f"Non-retryable error or max retries reached: {e}")
                        raise e

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base**attempt), max_delay)

                    # Add jitter to prevent thundering herd
                    if jitter:
                        delay += random.uniform(0, delay * 0.1)

                    # Extra delay for rate limit errors
                    if is_rate_limit:
                        delay *= 2  # Double the delay for rate limits

                        # Extract specific wait time from error message if available
                        if "retry after" in error_str:
                            try:
                                import re

                                match = re.search(r"retry after (\d+)", error_str)
                                if match:
                                    suggested_delay = int(match.group(1))
                                    delay = max(delay, suggested_delay)
                            except Exception:
                                pass

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    await asyncio.sleep(delay)

            # If we get here, all retries failed
            if last_exception:
                raise last_exception
            else:
                raise RuntimeError(
                    f"Function failed after {max_retries} retries with unknown error"
                )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, convert to async and run
            import asyncio

            return asyncio.run(async_wrapper(*args, **kwargs))

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class SmartTokenEstimator:
    """Intelligent token estimation for different content types"""

    @staticmethod
    def estimate_tokens(text: str, model: str = "gpt-5") -> int:
        """Estimate token count for text"""
        # Basic estimation: ~4 characters per token (conservative)
        base_estimate = len(text) // 4

        # Model-specific adjustments
        if "gpt-4" in model:
            # GPT-4 models tend to use slightly more tokens
            multiplier = 1.2
        else:
            multiplier = 1.1

        return int(base_estimate * multiplier)

    @staticmethod
    def estimate_crew_tokens(topic: str, phase: str = "research") -> int:
        """Estimate tokens for CrewAI crew operations"""
        base_tokens = {
            "research": 15000,  # Research agent with tools
            "content": 12000,  # Content creation
            "fact_check": 8000,  # Fact checking
            "finalization": 6000,  # Final editing
        }

        # Add tokens for topic complexity
        topic_tokens = len(topic) * 10  # Topic expansion factor

        return base_tokens.get(phase, 10000) + topic_tokens


# Global rate limiter instance
global_rate_limiter = AdvancedRateLimiter()


def rate_limited_api_call(
    model: str = "gpt-5", estimated_tokens: Optional[int] = None, max_retries: int = 5
):
    """
    Decorator for rate-limited API calls with intelligent token estimation

    Usage:
        @rate_limited_api_call(model="gpt-5", estimated_tokens=15000)
        async def my_api_call():
            # Your API call here
            pass
    """

    def decorator(func: Callable) -> Callable:
        @exponential_backoff_retry(
            max_retries=max_retries, rate_limiter=global_rate_limiter
        )
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Estimate tokens if not provided
            tokens = estimated_tokens
            if tokens is None:
                # Try to extract from kwargs or estimate
                if "topic" in kwargs:
                    tokens = SmartTokenEstimator.estimate_crew_tokens(kwargs["topic"])
                else:
                    tokens = 10000  # Conservative default

            # Acquire rate limit permission
            await global_rate_limiter.acquire(model, tokens)

            # Execute the function
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Convenience functions for common use cases
async def safe_openai_call(
    func: Callable,
    model: str = "gpt-4o",
    estimated_tokens: int = 10000,
    max_retries: int = 5,
    **kwargs,
) -> Any:
    """
    Safely execute an OpenAI API call with rate limiting and retries

    Args:
        func: The function to call
        model: Model being used
        estimated_tokens: Estimated token usage
        max_retries: Maximum retry attempts
        **kwargs: Arguments to pass to the function
    """

    @rate_limited_api_call(
        model=model, estimated_tokens=estimated_tokens, max_retries=max_retries
    )
    async def wrapped_call():
        return (
            await func(**kwargs)
            if asyncio.iscoroutinefunction(func)
            else func(**kwargs)
        )

    return await wrapped_call()


def configure_crewai_rate_limiting():
    """Configure CrewAI to use rate limiting"""
    logger.info("Configuring CrewAI with advanced rate limiting")

    # This would integrate with CrewAI's LLM calls
    # Implementation depends on CrewAI's internal structure
    pass


if __name__ == "__main__":
    # Example usage and testing
    async def example_usage():
        limiter = AdvancedRateLimiter()

        # Example: Check if we can make a call
        can_call = await limiter.acquire("gpt-4o", 15000)
        print(f"Can make call: {can_call}")

        # Example: Rate limited function
        @rate_limited_api_call(model="gpt-4o", estimated_tokens=15000)
        async def example_api_call():
            print("Making API call...")
            await asyncio.sleep(1)  # Simulate API call
            return "Success"

        result = await example_api_call()
        print(f"Result: {result}")

    asyncio.run(example_usage())
