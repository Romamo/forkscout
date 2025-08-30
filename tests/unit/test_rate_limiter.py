"""Tests for rate limiting and retry logic."""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from forklift.github.client import GitHubAPIError, GitHubRateLimitError
from forklift.github.rate_limiter import CircuitBreaker, RateLimitHandler, RequestBatcher


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

    def test_calculate_delay_with_long_reset_time_ignores_max_delay(self):
        """Test that reset time is used even when it exceeds max_delay."""
        handler = RateLimitHandler(max_delay=60.0)

        # Reset time 300 seconds (5 minutes) in the future - exceeds max_delay
        reset_time = int(time.time()) + 300
        delay = handler.calculate_delay(0, reset_time)

        # Should wait for full reset time, ignoring max_delay limit
        assert 300 <= delay <= 302

    def test_calculate_delay_with_very_long_reset_time(self):
        """Test that very long reset times are respected."""
        handler = RateLimitHandler(max_delay=60.0)

        # Reset time 3600 seconds (1 hour) in the future
        reset_time = int(time.time()) + 3600
        delay = handler.calculate_delay(0, reset_time)

        # Should wait for full reset time, ignoring max_delay limit
        assert 3600 <= delay <= 3602

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

    @pytest.mark.asyncio
    async def test_execute_with_retry_rate_limit_exceeds_max_delay(self):
        """Test that rate limit reset time is used even when it exceeds max_delay."""
        handler = RateLimitHandler(max_retries=2, base_delay=0.01, max_delay=5.0)

        # Mock rate limit error with long reset time (exceeds max_delay)
        reset_time = int(time.time()) + 300  # 5 minutes
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
        # Should have slept for the full reset time, not limited by max_delay
        mock_sleep.assert_called_once()
        sleep_duration = mock_sleep.call_args[0][0]
        assert 299 <= sleep_duration <= 302  # Should be around 300 seconds + buffer

    @pytest.mark.asyncio
    async def test_execute_with_retry_rate_limit_continues_beyond_max_retries(self):
        """Test that rate limit errors with reset time continue beyond max_retries."""
        handler = RateLimitHandler(max_retries=2, base_delay=0.01)

        # Mock rate limit error with reset time
        reset_time = int(time.time()) + 1
        rate_limit_error = GitHubRateLimitError(
            "Rate limited",
            reset_time=reset_time,
            remaining=0,
            limit=5000
        )

        # Create a sequence where rate limit errors exceed max_retries but eventually succeed
        mock_func = AsyncMock(side_effect=[
            rate_limit_error,  # Attempt 1
            rate_limit_error,  # Attempt 2
            rate_limit_error,  # Attempt 3 (exceeds max_retries=2)
            rate_limit_error,  # Attempt 4 (still continuing due to reset time)
            "success"          # Attempt 5 (finally succeeds)
        ])

        with patch("asyncio.sleep") as mock_sleep:
            result = await handler.execute_with_retry(
                mock_func,
                "test operation",
                retryable_exceptions=(GitHubRateLimitError,)
            )

        assert result == "success"
        assert mock_func.call_count == 5  # Should continue beyond max_retries
        assert mock_sleep.call_count == 4  # Should have slept 4 times

    @pytest.mark.asyncio
    async def test_execute_with_retry_non_rate_limit_respects_max_retries(self):
        """Test that non-rate-limit errors still respect max_retries."""
        handler = RateLimitHandler(max_retries=2, base_delay=0.01)

        # Mock non-rate-limit error
        api_error = GitHubAPIError("Server error", status_code=500)
        mock_func = AsyncMock(side_effect=api_error)

        with pytest.raises(GitHubAPIError, match="Server error"):
            await handler.execute_with_retry(
                mock_func,
                "test operation",
                retryable_exceptions=(GitHubAPIError,)
            )

        # Should respect max_retries for non-rate-limit errors
        assert mock_func.call_count == 3  # Initial attempt + 2 retries

    @pytest.mark.asyncio
    async def test_execute_with_retry_rate_limit_without_reset_time_respects_max_retries(self):
        """Test that rate limit errors without reset time still respect max_retries."""
        handler = RateLimitHandler(max_retries=2, base_delay=0.01)

        # Mock rate limit error without reset time
        rate_limit_error = GitHubRateLimitError(
            "Rate limited",
            reset_time=None,  # No reset time
            remaining=0,
            limit=5000
        )

        mock_func = AsyncMock(side_effect=rate_limit_error)

        with pytest.raises(GitHubRateLimitError, match="Rate limited"):
            await handler.execute_with_retry(
                mock_func,
                "test operation",
                retryable_exceptions=(GitHubRateLimitError,)
            )

        # Should respect max_retries when no reset time is available
        assert mock_func.call_count == 3  # Initial attempt + 2 retries

    def test_get_delay_for_exception_rate_limit_with_reset_time(self):
        """Test delay calculation for rate limit exception with reset time."""
        handler = RateLimitHandler(max_delay=60.0)

        # Create rate limit error with long reset time
        reset_time = int(time.time()) + 300  # 5 minutes
        rate_limit_error = GitHubRateLimitError(
            "Rate limited",
            reset_time=reset_time,
            remaining=0,
            limit=5000
        )

        delay = handler._get_delay_for_exception(rate_limit_error, 0)

        # Should use reset time, ignoring max_delay
        assert 299 <= delay <= 302

    def test_get_delay_for_exception_rate_limit_without_reset_time(self):
        """Test delay calculation for rate limit exception without reset time."""
        handler = RateLimitHandler(max_delay=60.0)

        # Create rate limit error without reset time
        rate_limit_error = GitHubRateLimitError(
            "Rate limited",
            reset_time=None,
            remaining=0,
            limit=5000
        )

        # Test progressive delays
        delay_0 = handler._get_delay_for_exception(rate_limit_error, 0)
        delay_1 = handler._get_delay_for_exception(rate_limit_error, 1)
        delay_2 = handler._get_delay_for_exception(rate_limit_error, 2)
        delay_3 = handler._get_delay_for_exception(rate_limit_error, 3)

        # Should use progressive backoff: 5min, 15min, 30min, 30min
        assert delay_0 == 300   # 5 minutes
        assert delay_1 == 900   # 15 minutes
        assert delay_2 == 1800  # 30 minutes
        assert delay_3 == 1800  # 30 minutes (max)

    def test_get_delay_for_exception_non_rate_limit(self):
        """Test delay calculation for non-rate-limit exceptions."""
        handler = RateLimitHandler(base_delay=1.0, backoff_factor=2.0, max_delay=60.0, jitter=False)

        # Create non-rate-limit error
        api_error = GitHubAPIError("Server error", status_code=500)

        # Should use standard exponential backoff
        delay_0 = handler._get_delay_for_exception(api_error, 0)
        delay_1 = handler._get_delay_for_exception(api_error, 1)
        delay_2 = handler._get_delay_for_exception(api_error, 2)

        assert delay_0 == 1.0  # 1.0 * 2^0
        assert delay_1 == 2.0  # 1.0 * 2^1
        assert delay_2 == 4.0  # 1.0 * 2^2

    def test_calculate_delay_with_extremely_long_reset_time(self):
        """Test that extremely long reset times (hours) are respected."""
        handler = RateLimitHandler(max_delay=60.0)

        # Reset time 7200 seconds (2 hours) in the future
        reset_time = int(time.time()) + 7200
        delay = handler.calculate_delay(0, reset_time)

        # Should wait for full reset time, completely ignoring max_delay limit
        assert 7200 <= delay <= 7202

    def test_calculate_delay_with_zero_reset_time(self):
        """Test delay calculation with zero reset time."""
        handler = RateLimitHandler(base_delay=1.0, jitter=False)

        # Reset time of 0 (invalid)
        delay = handler.calculate_delay(1, 0)

        # Should fall back to exponential backoff
        assert delay == 2.0  # base_delay * backoff_factor^1

    def test_calculate_delay_with_negative_reset_time(self):
        """Test delay calculation with negative reset time."""
        handler = RateLimitHandler(base_delay=1.0, jitter=False)

        # Negative reset time (invalid)
        delay = handler.calculate_delay(1, -100)

        # Should fall back to exponential backoff
        assert delay == 2.0  # base_delay * backoff_factor^1

    @pytest.mark.asyncio
    async def test_execute_with_retry_rate_limit_with_very_long_reset_time(self):
        """Test that very long reset times (hours) are handled correctly."""
        handler = RateLimitHandler(max_retries=1, base_delay=0.01, max_delay=5.0)

        # Mock rate limit error with very long reset time (2 hours)
        reset_time = int(time.time()) + 7200  # 2 hours
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
        # Should have slept for the full reset time, not limited by max_delay
        mock_sleep.assert_called_once()
        sleep_duration = mock_sleep.call_args[0][0]
        assert 7199 <= sleep_duration <= 7202  # Should be around 7200 seconds + buffer

    @pytest.mark.asyncio
    async def test_execute_with_retry_multiple_rate_limits_with_reset_times(self):
        """Test handling multiple consecutive rate limit errors with reset times."""
        handler = RateLimitHandler(max_retries=1, base_delay=0.01)

        # Mock multiple rate limit errors with reset times
        reset_time_1 = int(time.time()) + 300  # 5 minutes
        reset_time_2 = int(time.time()) + 600  # 10 minutes
        
        rate_limit_error_1 = GitHubRateLimitError(
            "Rate limited 1",
            reset_time=reset_time_1,
            remaining=0,
            limit=5000
        )
        
        rate_limit_error_2 = GitHubRateLimitError(
            "Rate limited 2", 
            reset_time=reset_time_2,
            remaining=0,
            limit=5000
        )

        mock_func = AsyncMock(side_effect=[
            rate_limit_error_1,  # First rate limit
            rate_limit_error_2,  # Second rate limit (exceeds max_retries but has reset time)
            "success"            # Finally succeeds
        ])

        with patch("asyncio.sleep") as mock_sleep:
            result = await handler.execute_with_retry(
                mock_func,
                "test operation",
                retryable_exceptions=(GitHubRateLimitError,)
            )

        assert result == "success"
        assert mock_func.call_count == 3  # Should continue beyond max_retries
        assert mock_sleep.call_count == 2  # Should have slept twice
        
        # Check that both sleep calls used the full reset times
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert 299 <= sleep_calls[0] <= 302  # First sleep ~300s
        assert 599 <= sleep_calls[1] <= 602  # Second sleep ~600s

    @pytest.mark.asyncio
    async def test_get_user_friendly_error_message_rate_limit_with_reset(self):
        """Test user-friendly error messages for rate limits with reset time."""
        handler = RateLimitHandler()
        
        reset_time = int(time.time()) + 300  # 5 minutes from now
        exception = GitHubRateLimitError(
            "Rate limit exceeded",
            reset_time=reset_time,
            remaining=0,
            limit=5000
        )
        
        message = handler._get_user_friendly_error_message(exception)
        
        assert "Temporary rate limit exceeded" in message
        assert "Will automatically retry" in message
        assert "not a permanent failure" in message
        assert "300" in message or "299" in message  # Should mention wait time

    @pytest.mark.asyncio
    async def test_get_user_friendly_error_message_rate_limit_without_reset(self):
        """Test user-friendly error messages for rate limits without reset time."""
        handler = RateLimitHandler()
        
        exception = GitHubRateLimitError(
            "Rate limit exceeded",
            reset_time=None,
            remaining=0,
            limit=5000
        )
        
        message = handler._get_user_friendly_error_message(exception)
        
        assert "Temporary rate limit exceeded" in message
        assert "progressive backoff" in message
        assert "not a permanent failure" in message

    @pytest.mark.asyncio
    async def test_get_user_friendly_error_message_auth_error(self):
        """Test user-friendly error messages for authentication errors."""
        handler = RateLimitHandler()
        
        from forklift.github.exceptions import GitHubAuthenticationError
        exception = GitHubAuthenticationError("Invalid token")
        
        message = handler._get_user_friendly_error_message(exception)
        
        assert "Permanent authentication failure" in message
        assert "check your GitHub token" in message
        assert "not be retried automatically" in message

    @pytest.mark.asyncio
    async def test_get_user_friendly_error_message_client_error(self):
        """Test user-friendly error messages for client errors."""
        handler = RateLimitHandler()
        
        exception = GitHubAPIError("Bad request", status_code=400)
        
        message = handler._get_user_friendly_error_message(exception)
        
        assert "Client error (400)" in message
        assert "permanent failure" in message
        assert "won't be retried" in message

    @pytest.mark.asyncio
    async def test_get_user_friendly_error_message_server_error(self):
        """Test user-friendly error messages for server errors."""
        handler = RateLimitHandler()
        
        exception = GitHubAPIError("Internal server error", status_code=500)
        
        message = handler._get_user_friendly_error_message(exception)
        
        assert "Server error (500)" in message
        assert "temporary failure" in message
        assert "retried automatically" in message

    @pytest.mark.asyncio
    async def test_handle_rate_limit_wait_with_reset_time(self):
        """Test enhanced rate limit wait handling with reset time."""
        handler = RateLimitHandler()
        
        reset_time = int(time.time()) + 60  # 1 minute from now
        exception = GitHubRateLimitError(
            "Rate limit exceeded",
            reset_time=reset_time,
            remaining=0,
            limit=5000
        )
        
        with patch("asyncio.sleep") as mock_sleep, \
             patch("forklift.github.rate_limiter.get_progress_manager") as mock_progress:
            
            mock_tracker = AsyncMock()
            mock_progress.return_value.get_tracker.return_value = mock_tracker
            
            await handler._handle_rate_limit_wait(exception, 60.0, "test_operation", 0)
            
            # Should have called progress tracking methods
            mock_tracker.show_rate_limit_info.assert_called_once()
            mock_tracker.track_rate_limit_wait.assert_called_once()
            mock_tracker.show_completion_message.assert_called_once()
            
            # Should have slept for the calculated delay
            mock_sleep.assert_called_once_with(60.0)

    @pytest.mark.asyncio
    async def test_immediate_resumption_after_rate_limit_recovery(self):
        """Test that operations resume immediately after rate limit recovery."""
        handler = RateLimitHandler(max_retries=1, base_delay=0.01)
        
        reset_time = int(time.time()) + 1  # 1 second from now
        rate_limit_error = GitHubRateLimitError(
            "Rate limit exceeded",
            reset_time=reset_time,
            remaining=0,
            limit=5000
        )
        
        call_count = 0
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise rate_limit_error
            return "success"
        
        start_time = time.time()
        
        with patch("asyncio.sleep") as mock_sleep:
            # Mock sleep to return immediately
            mock_sleep.return_value = None
            
            result = await handler.execute_with_retry(test_func, "test_operation")
        
        end_time = time.time()
        
        assert result == "success"
        assert call_count == 2
        # Should have completed quickly (immediate resumption)
        assert end_time - start_time < 1.0  # Should be very fast due to mocked sleep

    @pytest.mark.asyncio
    async def test_enhanced_error_logging_with_context(self):
        """Test that error logging includes enhanced context and user-friendly messages."""
        handler = RateLimitHandler(max_retries=1, base_delay=0.01)
        
        from forklift.github.exceptions import GitHubAuthenticationError
        auth_error = GitHubAuthenticationError("Invalid token", status_code=401)
        
        mock_func = AsyncMock(side_effect=auth_error)
        
        with patch("forklift.github.rate_limiter.logger") as mock_logger:
            with pytest.raises(GitHubAuthenticationError):
                await handler.execute_with_retry(mock_func, "test_operation")
            
            # Should have logged user-friendly error message
            mock_logger.error.assert_called()
            error_call = mock_logger.error.call_args[0][0]
            assert "Permanent authentication failure" in error_call
            assert "check your GitHub token" in error_call


class TestRequestBatcher:
    """Test request batching functionality."""

    @pytest.mark.asyncio
    async def test_execute_batched_requests_single_batch(self):
        """Test executing requests in a single batch."""
        batcher = RequestBatcher(batch_size=5, batch_delay=0.01)
        
        # Create mock requests
        requests = [AsyncMock(return_value=f"result_{i}") for i in range(3)]
        
        results = await batcher.execute_batched_requests(requests, "test_operation")
        
        assert len(results) == 3
        assert results == ["result_0", "result_1", "result_2"]
        
        # All requests should have been called
        for request in requests:
            request.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_batched_requests_multiple_batches(self):
        """Test executing requests across multiple batches."""
        batcher = RequestBatcher(batch_size=2, batch_delay=0.01)
        
        # Create mock requests
        requests = [AsyncMock(return_value=f"result_{i}") for i in range(5)]
        
        with patch("asyncio.sleep") as mock_sleep:
            results = await batcher.execute_batched_requests(requests, "test_operation")
        
        assert len(results) == 5
        assert results == ["result_0", "result_1", "result_2", "result_3", "result_4"]
        
        # Should have slept between batches (3 batches = 2 sleeps)
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_batched_requests_with_rate_limit_handler(self):
        """Test executing batched requests with rate limit handler."""
        batcher = RequestBatcher(batch_size=2, batch_delay=0.01)
        rate_limit_handler = RateLimitHandler(max_retries=1, base_delay=0.01)
        
        # Create mock requests
        requests = [AsyncMock(return_value=f"result_{i}") for i in range(3)]
        
        results = await batcher.execute_batched_requests(
            requests, "test_operation", rate_limit_handler
        )
        
        assert len(results) == 3
        assert results == ["result_0", "result_1", "result_2"]

    @pytest.mark.asyncio
    async def test_adaptive_batching_reduces_size_on_rate_limits(self):
        """Test that adaptive batching reduces batch size when hitting rate limits."""
        batcher = RequestBatcher(batch_size=4, adaptive_batching=True)
        
        from forklift.github.exceptions import GitHubRateLimitError
        rate_limit_error = GitHubRateLimitError("Rate limited", reset_time=int(time.time()) + 60)
        
        # First batch will hit rate limits
        requests_batch_1 = [
            AsyncMock(side_effect=rate_limit_error),
            AsyncMock(side_effect=rate_limit_error),
        ]
        
        # Execute first batch to trigger rate limit detection
        await batcher._execute_batch(requests_batch_1, "test_batch", None)
        
        # Batch size should be reduced after rate limit hits
        assert batcher.current_batch_size < batcher.batch_size

    @pytest.mark.asyncio
    async def test_adaptive_batching_increases_size_on_success(self):
        """Test that adaptive batching increases batch size after consistent success."""
        batcher = RequestBatcher(batch_size=8, adaptive_batching=True)
        batcher.current_batch_size = 2  # Start with reduced size
        
        # Simulate multiple successful batches
        for _ in range(6):  # Need 5+ consecutive successes
            successful_requests = [
                AsyncMock(return_value="success"),
                AsyncMock(return_value="success"),
            ]
            await batcher._execute_batch(successful_requests, "test_batch", None)
        
        # Batch size should have increased
        assert batcher.current_batch_size > 2

    @pytest.mark.asyncio
    async def test_calculate_batch_delay_adapts_to_conditions(self):
        """Test that batch delay adapts based on rate limit conditions."""
        batcher = RequestBatcher(batch_delay=1.0)
        
        # Normal conditions
        assert batcher._calculate_batch_delay() == 1.0
        
        # After rate limits
        batcher.consecutive_rate_limits = 2
        delay = batcher._calculate_batch_delay()
        assert delay > 1.0  # Should increase delay
        
        # After many successes
        batcher.consecutive_rate_limits = 0
        batcher.consecutive_successes = 15
        delay = batcher._calculate_batch_delay()
        assert delay < 1.0  # Should decrease delay

    @pytest.mark.asyncio
    async def test_empty_requests_list(self):
        """Test handling of empty requests list."""
        batcher = RequestBatcher()
        
        results = await batcher.execute_batched_requests([], "test_operation")
        
        assert results == []


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
