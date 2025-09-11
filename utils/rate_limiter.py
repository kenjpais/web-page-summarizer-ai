"""Rate limiting functionality for API calls."""

import functools
from typing import Callable, TypeVar, ParamSpec
from config.settings import AppSettings
from utils.logging_config import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class RateLimiter:
    """Manages API rate limiting."""

    def __init__(self, settings: AppSettings):
        """Initialize rate limiter with settings."""
        self.settings = settings
        self.max_rpd = settings.api.max_requests_per_day
        self.rpd_counter = 0

    def check_rate_limit(self, func: Callable[P, T]) -> Callable[P, T]:
        """
        Decorator to check rate limits before executing API calls.

        Args:
            func: The function to wrap

        Returns:
            Wrapped function that checks rate limits

        Raises:
            RuntimeError: If API rate limit is exceeded
            ValueError: If rate limit counters are invalid
        """

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Validate counter values
            if self.rpd_counter < 0:
                raise ValueError("Request counter cannot be negative")
            if self.max_rpd <= 0:
                raise ValueError("Maximum requests per day must be positive")

            # Check rate limit
            if self.rpd_counter >= self.max_rpd:
                logger.warning(
                    f"Rate limit exceeded: {self.rpd_counter}/{self.max_rpd} requests used"
                )
                raise RuntimeError("Daily API request limit exceeded")

            try:
                result = func(*args, **kwargs)
                self.rpd_counter += 1
                logger.debug(
                    f"API request successful. Requests remaining: {self.max_rpd - self.rpd_counter}"
                )
                return result
            except Exception as e:
                logger.error(f"API request failed: {str(e)}")
                raise

        return wrapper
