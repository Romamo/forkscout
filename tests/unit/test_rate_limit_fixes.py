"""Tests for rate limiting fixes."""

import time
from unittest.mock import Mock, patch

import pytest

from forkscout.github.exceptions import GitHubRateLimitError
from forkscout.github.rate_limiter import RateLimitHandler


class TestRateLimitFixes:
    """Test rate limiting improvements."""

    def test_calculate_delay_ignores_max_delay_for_reset_time(self):
        """Test that calculate_delay ignores max_delay when reset_time is available."""
        handler = RateLimitHandler(max_delay=60.0)
        
        # Reset time that would exceed max_delay (2 hours from now)
        reset_time = int(time.time()) + 7200  # 2 hours
        
        delay = handler.calculate_delay(attempt=0, reset_time=reset_time)
        
        # Should return the full reset delay, not limited by max_delay
        assert delay > 60.0  # Should exceed max_delay
        assert delay >= 7200  # Should be close to 2 hours (plus buffer)

    def test_calculate_delay_with_no_reset_time_uses_exponential_backoff(self):
        """Test that calculate_delay uses exponential backoff when no reset_time."""
        handler = RateLimitHandler(max_delay=60.0, base_delay=1.0, backoff_factor=2.0)
        
        delay = handler.calculate_delay(attempt=2, reset_time=None)
        
        # Should use exponential backoff: base_delay * (backoff_factor ^ attempt)
        # For attempt=2: 1.0 * (2.0 ^ 2) = 4.0 seconds (plus jitter)
        assert delay <= 60.0  # Should respect max_delay
        assert delay >= 2.0   # Should be at least base calculation

    def test_get_delay_for_exception_with_valid_reset_time(self):
        """Test delay calculation for rate limit error with valid reset time."""
        handler = RateLimitHandler()
        
        reset_time = int(time.time()) + 3600  # 1 hour from now
        exception = GitHubRateLimitError(
            "Rate limit exceeded",
            reset_time=reset_time,
            remaining=0,
            limit=5000
        )
        
        delay = handler._get_delay_for_exception(exception, attempt=0)
        
        # Should use reset time, not exponential backoff
        assert delay >= 3600  # Should be close to 1 hour

    def test_get_delay_for_exception_without_reset_time_uses_progressive_backoff(self):
        """Test delay calculation for rate limit error without reset time."""
        handler = RateLimitHandler()
        
        exception = GitHubRateLimitError(
            "Rate limit exceeded",
            reset_time=0,  # No reset time
            remaining=0,
            limit=5000
        )
        
        # Test progressive delays: 5min, 15min, 30min
        delay_0 = handler._get_delay_for_exception(exception, attempt=0)
        delay_1 = handler._get_delay_for_exception(exception, attempt=1)
        delay_2 = handler._get_delay_for_exception(exception, attempt=2)
        delay_3 = handler._get_delay_for_exception(exception, attempt=3)
        
        assert delay_0 == 300   # 5 minutes
        assert delay_1 == 900   # 15 minutes
        assert delay_2 == 1800  # 30 minutes
        assert delay_3 == 1800  # 30 minutes (max)

    def test_get_delay_for_exception_with_none_reset_time_uses_progressive_backoff(self):
        """Test delay calculation for rate limit error with None reset time."""
        handler = RateLimitHandler()
        
        exception = GitHubRateLimitError(
            "Rate limit exceeded",
            reset_time=None,  # No reset time
            remaining=0,
            limit=5000
        )
        
        delay = handler._get_delay_for_exception(exception, attempt=0)
        
        assert delay == 300  # Should use progressive backoff (5 minutes)

    @pytest.mark.asyncio
    async def test_execute_with_retry_continues_beyond_max_retries_for_rate_limits_with_reset_time(self):
        """Test that rate limit errors with reset time continue beyond max_retries."""
        handler = RateLimitHandler(max_retries=2, base_delay=0.01)
        
        reset_time = int(time.time()) + 1  # 1 second from now
        exception = GitHubRateLimitError(
            "Rate limit exceeded",
            reset_time=reset_time,
            remaining=0,
            limit=5000
        )
        
        call_count = 0
        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:  # Fail first 3 attempts (beyond max_retries)
                raise exception
            return "success"
        
        with patch("asyncio.sleep"):  # Mock sleep to speed up test
            result = await handler.execute_with_retry(failing_func, "test operation")
        
        assert result == "success"
        assert call_count == 4  # Should have tried 4 times (beyond max_retries of 2)

    @pytest.mark.asyncio
    async def test_execute_with_retry_respects_max_retries_for_rate_limits_without_reset_time(self):
        """Test that rate limit errors without reset time still respect max_retries."""
        handler = RateLimitHandler(max_retries=2, base_delay=0.01)
        
        exception = GitHubRateLimitError(
            "Rate limit exceeded",
            reset_time=0,  # No reset time
            remaining=0,
            limit=5000
        )
        
        call_count = 0
        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise exception
        
        with patch("asyncio.sleep"):  # Mock sleep to speed up test
            with pytest.raises(GitHubRateLimitError):
                await handler.execute_with_retry(failing_func, "test operation")
        
        assert call_count == 3  # Should have tried 3 times (initial + 2 retries)