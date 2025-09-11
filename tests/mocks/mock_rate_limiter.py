"""Mock implementation of RateLimiter for testing."""

from typing import Callable, TypeVar, ParamSpec
from config.settings import AppSettings

P = ParamSpec("P")
T = TypeVar("T")


class MockRateLimiter:
    """Mock implementation of RateLimiter."""

    def __init__(self, settings: AppSettings):
        """Initialize mock rate limiter."""
        self.settings = settings
        self.max_rpd = settings.api.max_requests_per_day
        self.rpd_counter = 0
        self.should_fail = False

    def check_rate_limit(self, func: Callable[P, T]) -> Callable[P, T]:
        """Mock rate limit checking."""

        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if self.should_fail:
                raise RuntimeError("Test rate limit error")
            if self.rpd_counter >= self.max_rpd:
                raise RuntimeError("Daily API request limit exceeded")
            result = func(*args, **kwargs)
            self.rpd_counter += 1
            return result

        return wrapper
