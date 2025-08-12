"""
Rate limiting and retry mechanism for Gemini API requests.
Implements token bucket algorithm and exponential backoff.
"""

import time
import random
from typing import Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
from functools import wraps


@dataclass
class RateLimitConfig:
    """Configuration for rate limits"""

    requests_per_minute: int = 5
    requests_per_day: int = 25
    min_request_interval: float = 0.2  # seconds
    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 32.0  # seconds
    jitter: float = 0.1  # +/- 10% random jitter


class TokenBucket:
    """
    Token bucket rate limiter implementation
    - Smooths out request rate
    - Allows brief bursts while maintaining average rate
    """

    def __init__(self, rate: float, capacity: int):
        """
        Initialize token bucket

        Args:
            rate: Token refill rate per second
            capacity: Maximum number of tokens bucket can hold
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = threading.Lock()

    def _refill(self):
        """Refill tokens based on time elapsed"""
        now = time.time()
        delta = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + delta * self.rate)
        self.last_update = now

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


class GeminiRateLimiter:
    """
    Rate limiter for Gemini API with retry mechanism
    - Implements per-minute and per-day limits
    - Handles retries with exponential backoff
    - Adds jitter to prevent thundering herd
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()

        # Token bucket for per-minute rate limiting
        self.minute_limiter = TokenBucket(
            rate=self.config.requests_per_minute / 60.0,
            capacity=self.config.requests_per_minute,
        )

        # Track daily request count
        self.daily_requests = 0
        self.last_reset = datetime.now()
        self._lock = threading.Lock()

    def _should_reset_daily(self) -> bool:
        """Check if daily counters should be reset"""
        now = datetime.now()
        return now.date() > self.last_reset.date()

    def _reset_daily(self):
        """Reset daily request counter"""
        with self._lock:
            if self._should_reset_daily():
                self.daily_requests = 0
                self.last_reset = datetime.now()

    def _add_jitter(self, delay: float) -> float:
        """Add random jitter to delay"""
        jitter_range = delay * self.config.jitter
        return delay + random.uniform(-jitter_range, jitter_range)

    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt with exponential backoff"""
        delay = min(
            self.config.base_delay * (2 ** (attempt - 1)), self.config.max_delay
        )
        return self._add_jitter(delay)

    def can_make_request(self) -> bool:
        """Check if a request can be made within rate limits"""
        self._reset_daily()

        with self._lock:
            if self.daily_requests >= self.config.requests_per_day:
                return False

            # Initialize token bucket if needed
            if not hasattr(self.minute_limiter, "tokens"):
                self.minute_limiter.tokens = self.minute_limiter.capacity

            if not self.minute_limiter.consume():
                return False

            return True

    def wait_if_needed(self):
        """Wait until a request can be made"""
        while not self.can_make_request():
            time.sleep(self.config.min_request_interval)

    def increment_counters(self):
        """Increment request counters after successful request"""
        with self._lock:
            self.daily_requests += 1

    def retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry and backoff logic

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from successful function execution

        Raises:
            Exception: If all retries fail
        """
        last_exception = None

        for attempt in range(1, self.config.max_retries + 1):
            try:
                # Wait for rate limit if needed
                self.wait_if_needed()

                # Execute function
                result = func(*args, **kwargs)

                # Increment counters on success
                self.increment_counters()

                return result

            except Exception as e:
                last_exception = e

                if attempt < self.config.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    time.sleep(delay)

        raise last_exception


def rate_limited(func: Callable) -> Callable:
    """
    Decorator to apply rate limiting to a function

    Usage:
        @rate_limited
        def my_api_call():
            ...
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get or create rate limiter
        if not hasattr(wrapper, "rate_limiter"):
            wrapper.rate_limiter = GeminiRateLimiter()

        return wrapper.rate_limiter.retry_with_backoff(func, *args, **kwargs)

    return wrapper
