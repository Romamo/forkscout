"""Tests for rate limiting and retry logic."""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from forklift.github.client import GitHubAPIError, GitHubRateLimitError
from forklift.github.rate_limiter import CircuitBreaker, RateLimitHandler


class TestRateLimitHandler:
    """Test rate limit handler functionality."""

    def test_calculate_delay_exponential_backoff(self):
        """Test exponential backoff delay calculation."""
        handler = RateLimitHandler(
            base_delay=1.0,
            backoff_factor=2.0,
            max_delay=60.0,
            jitter=False,
        )

        # Test exponential progression
        assert handler.calculate_delay(0) == 1.0  # 1.0 * 2^0
        assert handler.calculate_delay(1) == 2.0  # 1.0 * 2^1
        assert handler.calculate_delay(2) == 4.0  # 1.0 * 2^2
        assert handler.calculate_delay(3) == 8.0  # 1.0 * 2^3

    def test_calculate_delay_max_limit(self):
        """Test that delay doesn't exceed maximum."""
        handler = RateLimitHandler(
            base_delay=1.0,
            backoff_factor=2.0,
            max_delay=5.0,
            jitter=False,
        )

        # Should cap at max_delay
        assert handler.calculate_delay(10) == 5.0

    def test_calculate_delay_with_jitter(self):
        """Test that jitter adds randomness to delay."""
        handler = RateLimitHandler(
            base_delay=2.0,
            backoff_factor=2.0,
            max_delay=60.0,
            jitter=True,
        )

        # With jitter, delay should be between 50-100% of calculated value
        delay = handler.calculate_delay(1)  # Base would be 4.0
        assert 2.0 <= delay <= 4.0

    def test_calculate_delay_with_reset_time(self):
        """Test delay calculation with rate limit reset time."""
        handler = RateLimitHandler()

        # Reset time 30 seconds in the future
        reset_time = int(time.time()) + 30
        delay = handler.calculate_delay(0, reset_time)

        # Should wait until reset time (plus buffer)
        assert 30 <= delay <= 32

    def test_calculate_delay_with_past_reset_time(self):
        """Test delay calculation with past reset time."""
        handler = RateLimitHandler(base_delay=1.0, jitter=False)

        # Reset time in the past
        reset_time = int(time.time()) - 10
        delay = handler.calculate_delay(1, reset_time)

        # Should fall back to exponential backoff
        assert delay == 2.0  # base_delay * backoff_factor^1

    @pytest.mark.asyncio
    async def test_execute_with_retry_success_first_attempt(self):
        """Test successful execution on first attempt."""
        handler = RateLimitHandler()
        mock_func = AsyncMock(return_value="success")

        result = await handler.execute_with_retry(mock_func, "test operation")

        assert result == "success"
        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_retry_success_after_retries(self):
        """Test successful execution after retries."""
        handler = RateLimitHandler(max_retries=3, base_delay=0.01)

        # Mock function that fails twice then succeeds
        mock_func = AsyncMock(side_effect=[
            GitHubAPIError("Server error", status_code=500),
            GitHubAPIError("Server error", status_code=500),
            "success"
        ])

        result = await handler.execute_with_retry(
            mock_func,
            "test operation",
            retryable_exceptions=(GitHubAPIError,)
        )

        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_with_retry_max_retries_exceeded(self):
        """Test that max retries are respected."""
        handler = RateLimitHandler(max_retries=2, base_delay=0.01)

        # Mock function that always fails
        mock_func = AsyncMock(side_effect=GitHubAPIError("Always fails"))

        with pytest.raises(GitHubAPIError, match="Always fails"):
            await handler.execute_with_retry(
                mock_func,
                "test operation",
                retryable_exceptions=(GitHubAPIError,)
            )

        assert mock_func.call_count == 3  # Initial attempt + 2 retries

    @pytest.mark.asyncio
    async def test_execute_with_retry_non_retryable_exception(self):
        """Test that non-retryable exceptions are not retried."""
        handler = RateLimitHandler(max_retries=3)

        # Mock function that raises non-retryable exception
        mock_func = AsyncMock(side_effect=ValueError("Non-retryable"))

        with pytest.raises(ValueError, match="Non-retryable"):
            await handler.execute_with_retry(
                mock_func,
                "test operation",
                retryable_exceptions=(GitHubAPIError,)
            )

        mock_func.assert_called_once()  # Should not retry

    @pytest.mark.asyncio
    async def test_execute_with_retry_rate_limit_error(self):
        """Test retry behavior with rate limit errors."""
        handler = RateLimitHandler(max_retries=2, base_delay=0.01)

        # Mock rate limit error with reset time
        reset_time = int(time.time()) + 1
        rate_limit_error = GitHubRateLimitError(
            "Rate limited",
            reset_time=reset_time,
            remaining=0,
            limit=5000
        )

        mock_func = AsyncMock(side_effect=[rate_limit_error, "success"])

        with patch("asyncio.sleep") as mock_sleep:
            result = await handler.execute_with_retry(
                mock_func,
                "test operation",
                retryable_exceptions=(GitHubRateLimitError,)
            )

        assert result == "success"
        assert mock_func.call_count == 2
        # Should have slept for the rate limit reset time
        mock_sleep.assert_called_once()
        sleep_duration = mock_sleep.call_args[0][0]
        assert 0.5 <= sleep_duration <= 2.0  # Should be around 1 second + buffer


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker starts in closed state."""
        breaker = CircuitBreaker()
        assert breaker.state == "closed"
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_success(self):
        """Test successful operation through circuit breaker."""
        breaker = CircuitBreaker()
        mock_func = AsyncMock(return_value="success")

        result = await breaker.call(mock_func, "test operation")

        assert result == "success"
        assert breaker.state == "closed"
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures."""
        breaker = CircuitBreaker(failure_threshold=3, expected_exception=ValueError)
        mock_func = AsyncMock(side_effect=ValueError("Test error"))

        # Cause failures up to threshold
        for i in range(3):
            with pytest.raises(ValueError):
                await breaker.call(mock_func, "test operation")

        assert breaker.state == "open"
        assert breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_when_open(self):
        """Test circuit breaker blocks calls when open."""
        breaker = CircuitBreaker(failure_threshold=1, expected_exception=ValueError)
        mock_func = AsyncMock(side_effect=ValueError("Test error"))

        # Cause failure to open circuit
        with pytest.raises(ValueError):
            await breaker.call(mock_func, "test operation")

        assert breaker.state == "open"

        # Next call should be blocked
        mock_func.reset_mock()
        with pytest.raises(Exception, match="Circuit breaker is open"):
            await breaker.call(mock_func, "test operation")

        # Function should not have been called
        mock_func.assert_not_called()

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_transition(self):
        """Test circuit breaker transitions to half-open after timeout."""
        breaker = CircuitBreaker(
            failure_threshold=1,
            timeout=0.1,  # Short timeout for testing
            expected_exception=ValueError
        )
        mock_func = AsyncMock(side_effect=ValueError("Test error"))

        # Cause failure to open circuit
        with pytest.raises(ValueError):
            await breaker.call(mock_func, "test operation")

        assert breaker.state == "open"

        # Wait for timeout
        await asyncio.sleep(0.2)

        # Next call should transition to half-open
        mock_func.reset_mock()
        with pytest.raises(ValueError):
            await breaker.call(mock_func, "test operation")

        # Should have attempted the call (half-open state)
        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_circuit_breaker_closes_after_success_in_half_open(self):
        """Test circuit breaker closes after success in half-open state."""
        breaker = CircuitBreaker(
            failure_threshold=1,
            timeout=0.1,
            expected_exception=ValueError
        )

        # Open the circuit
        mock_func = AsyncMock(side_effect=ValueError("Test error"))
        with pytest.raises(ValueError):
            await breaker.call(mock_func, "test operation")

        assert breaker.state == "open"

        # Wait for timeout
        await asyncio.sleep(0.2)

        # Successful call should close the circuit
        mock_func = AsyncMock(return_value="success")
        result = await breaker.call(mock_func, "test operation")

        assert result == "success"
        assert breaker.state == "closed"
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_ignores_unexpected_exceptions(self):
        """Test circuit breaker ignores exceptions not in expected_exception."""
        breaker = CircuitBreaker(failure_threshold=2, expected_exception=ValueError)

        # RuntimeError should not trigger circuit breaker
        mock_func = AsyncMock(side_effect=RuntimeError("Unexpected error"))

        with pytest.raises(RuntimeError):
            await breaker.call(mock_func, "test operation")

        # Circuit should still be closed
        assert breaker.state == "closed"
        assert breaker.failure_count == 0


class TestIntegration:
    """Integration tests for rate limiting and error handling."""

    @pytest.mark.asyncio
    async def test_rate_limiter_with_circuit_breaker(self):
        """Test rate limiter working with circuit breaker."""
        rate_limiter = RateLimitHandler(max_retries=2, base_delay=0.01)
        circuit_breaker = CircuitBreaker(failure_threshold=3, expected_exception=GitHubAPIError)

        # Function that fails consistently
        mock_func = AsyncMock(side_effect=GitHubAPIError("Persistent error"))

        # Should retry within rate limiter, then fail
        with pytest.raises(GitHubAPIError):
            await circuit_breaker.call(
                lambda: rate_limiter.execute_with_retry(
                    mock_func,
                    "test operation",
                    retryable_exceptions=(GitHubAPIError,)
                ),
                "test operation"
            )

        # Should have been called 3 times (initial + 2 retries)
        assert mock_func.call_count == 3
        # Circuit breaker should still be closed (only 1 failure from its perspective)
        assert circuit_breaker.state == "closed"
        assert circuit_breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_complex_retry_scenario(self):
        """Test complex scenario with multiple error types."""
        handler = RateLimitHandler(max_retries=4, base_delay=0.01)

        # Sequence of different errors followed by success
        errors = [
            GitHubRateLimitError("Rate limited", reset_time=int(time.time()) + 1),
            GitHubAPIError("Server error", status_code=500),
            GitHubAPIError("Bad gateway", status_code=502),
            "success"
        ]

        mock_func = AsyncMock(side_effect=errors)

        with patch("asyncio.sleep"):  # Mock sleep to speed up test
            result = await handler.execute_with_retry(
                mock_func,
                "complex operation",
                retryable_exceptions=(GitHubRateLimitError, GitHubAPIError)
            )

        assert result == "success"
        assert mock_func.call_count == 4
