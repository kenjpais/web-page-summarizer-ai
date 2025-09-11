"""Tests for RateLimiter."""

import pytest
from unittest.mock import MagicMock
from config.settings import AppSettings
from utils.rate_limiter import RateLimiter


@pytest.fixture
def settings():
    """Create test settings."""
    settings = AppSettings()
    settings.api.max_requests_per_day = 10
    return settings


@pytest.fixture
def rate_limiter(settings):
    """Create rate limiter instance."""
    return RateLimiter(settings)


def test_initialization(settings):
    """Test rate limiter initialization."""
    limiter = RateLimiter(settings)
    assert limiter.settings == settings
    assert limiter.max_rpd == settings.api.max_requests_per_day
    assert limiter.rpd_counter == 0


def test_successful_request(rate_limiter):
    """Test successful API request."""
    mock_func = MagicMock(return_value="success")
    wrapped_func = rate_limiter.check_rate_limit(mock_func)

    # Make a successful request
    result = wrapped_func()
    assert result == "success"
    assert rate_limiter.rpd_counter == 1
    mock_func.assert_called_once()


def test_rate_limit_exceeded(rate_limiter):
    """Test rate limit exceeded."""
    mock_func = MagicMock(return_value="success")
    wrapped_func = rate_limiter.check_rate_limit(mock_func)

    # Use up all requests
    for _ in range(rate_limiter.max_rpd):
        wrapped_func()

    # Next request should fail
    with pytest.raises(RuntimeError) as exc_info:
        wrapped_func()
    assert "Daily API request limit exceeded" in str(exc_info.value)
    assert rate_limiter.rpd_counter == rate_limiter.max_rpd


def test_failed_request(rate_limiter):
    """Test failed API request."""
    mock_func = MagicMock(side_effect=Exception("API Error"))
    wrapped_func = rate_limiter.check_rate_limit(mock_func)

    # Make a failed request
    with pytest.raises(Exception) as exc_info:
        wrapped_func()
    assert "API Error" in str(exc_info.value)
    assert rate_limiter.rpd_counter == 0  # Counter should not increment on failure


def test_invalid_counter_values(settings):
    """Test invalid counter values."""
    limiter = RateLimiter(settings)

    # Test negative counter
    limiter.rpd_counter = -1
    mock_func = MagicMock()
    wrapped_func = limiter.check_rate_limit(mock_func)
    with pytest.raises(ValueError) as exc_info:
        wrapped_func()
    assert "Request counter cannot be negative" in str(exc_info.value)

    # Test zero max_rpd
    settings.api.max_requests_per_day = 0
    limiter = RateLimiter(settings)
    mock_func = MagicMock()
    wrapped_func = limiter.check_rate_limit(mock_func)
    with pytest.raises(ValueError) as exc_info:
        wrapped_func()
    assert "Maximum requests per day must be positive" in str(exc_info.value)


def test_concurrent_requests(rate_limiter):
    """Test concurrent API requests."""
    mock_func = MagicMock(return_value="success")
    wrapped_func = rate_limiter.check_rate_limit(mock_func)

    # Simulate concurrent requests
    results = []
    for _ in range(5):
        results.append(wrapped_func())

    assert all(result == "success" for result in results)
    assert rate_limiter.rpd_counter == 5
    assert mock_func.call_count == 5


def test_request_with_arguments(rate_limiter):
    """Test API request with arguments."""

    def test_func(a, b, c=None):
        return a + b + (c or 0)

    wrapped_func = rate_limiter.check_rate_limit(test_func)

    # Test with positional args
    result = wrapped_func(1, 2)
    assert result == 3
    assert rate_limiter.rpd_counter == 1

    # Test with keyword args
    result = wrapped_func(a=2, b=3, c=4)
    assert result == 9
    assert rate_limiter.rpd_counter == 2


def test_request_near_limit(rate_limiter):
    """Test behavior near the rate limit."""
    mock_func = MagicMock(return_value="success")
    wrapped_func = rate_limiter.check_rate_limit(mock_func)

    # Use up all but one request
    for _ in range(rate_limiter.max_rpd - 1):
        wrapped_func()

    # Last allowed request should succeed
    result = wrapped_func()
    assert result == "success"
    assert rate_limiter.rpd_counter == rate_limiter.max_rpd

    # Next request should fail
    with pytest.raises(RuntimeError):
        wrapped_func()


def test_error_propagation(rate_limiter):
    """Test error propagation from wrapped function."""

    class CustomError(Exception):
        pass

    def failing_func():
        raise CustomError("Custom error")

    wrapped_func = rate_limiter.check_rate_limit(failing_func)

    # Error should be propagated
    with pytest.raises(CustomError) as exc_info:
        wrapped_func()
    assert "Custom error" in str(exc_info.value)
    assert rate_limiter.rpd_counter == 0  # Counter should not increment
