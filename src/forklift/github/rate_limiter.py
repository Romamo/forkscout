"""Rate limiting and retry logic for GitHub API client."""

import asyncio
import logging
import random
import time
from collections.abc import Callable
from typing import Any, TypeVar

from .rate_limit_progress import get_progress_manager

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RateLimitHandler:
    """Handles rate limiting and retry logic for GitHub API requests."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
    ):
        """Initialize rate limit handler.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
            max_delay: Maximum delay in seconds
            backoff_factor: Multiplier for exponential backoff
            jitter: Whether to add random jitter to delays
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter

    def calculate_delay(self, attempt: int, reset_time: int | None = None) -> float:
        """Calculate delay for retry attempt.
        
        Args:
            attempt: Current attempt number (0-based)
            reset_time: Optional rate limit reset time (Unix timestamp)
            
        Returns:
            Delay in seconds
        """
        if reset_time:
            # If we have a rate limit reset time, wait until then (plus a small buffer)
            current_time = time.time()
            reset_delay = max(0, reset_time - current_time + 1)  # +1 second buffer

            # Always use reset delay if it's valid and in the future, ignoring max_delay
            if reset_delay > 0:
                if reset_delay > self.max_delay:
                    logger.info(f"Rate limit reset in {reset_delay:.1f} seconds (exceeds max_delay of {self.max_delay}s), waiting for full reset time...")
                else:
                    logger.info(f"Rate limit reset in {reset_delay:.1f} seconds, waiting...")
                return reset_delay

        # Calculate exponential backoff delay
        delay = min(self.base_delay * (self.backoff_factor ** attempt), self.max_delay)

        # Add jitter to prevent thundering herd
        if self.jitter:
            jitter_factor = 0.5 + random.random() * 0.5  # 50-100% of calculated delay
            delay *= jitter_factor

        return delay

    async def execute_with_retry(
        self,
        func: Callable[[], Any],
        operation_name: str = "API request",
        retryable_exceptions: tuple = None,
    ) -> Any:
        """Execute function with retry logic and exponential backoff.
        
        Args:
            func: Async function to execute
            operation_name: Name of operation for logging
            retryable_exceptions: Tuple of exception types that should trigger retry
            
        Returns:
            Result of function execution
            
        Raises:
            Last exception if all retries are exhausted
        """
        if retryable_exceptions is None:
            import httpx

            from .exceptions import GitHubAPIError, GitHubRateLimitError
            retryable_exceptions = (
                GitHubRateLimitError,
                httpx.TimeoutException,
                httpx.NetworkError,
                GitHubAPIError,
            )

        last_exception = None
        attempt = 0

        while True:
            try:
                if attempt == 0:
                    logger.debug(f"Executing {operation_name} (attempt {attempt + 1})")
                else:
                    logger.debug(f"Executing {operation_name} (attempt {attempt + 1})")
                result = await func()

                if attempt > 0:
                    logger.info(f"{operation_name} succeeded after {attempt + 1} attempts")

                return result

            except retryable_exceptions as e:
                # Check if this is a non-retryable GitHubAPIError
                if self._is_non_retryable_error(e):
                    logger.error(f"Non-retryable error in {operation_name}: {e}")
                    raise

                last_exception = e

                # For rate limit errors with reset time, continue retrying indefinitely
                from .exceptions import GitHubRateLimitError
                is_rate_limit_with_reset = (
                    isinstance(e, GitHubRateLimitError) and 
                    e.reset_time and 
                    e.reset_time > 0
                )

                # Check if we should stop retrying
                if attempt >= self.max_retries and not is_rate_limit_with_reset:
                    logger.error(f"Max retries ({self.max_retries}) exceeded for {operation_name}")
                    break
                elif attempt >= self.max_retries and is_rate_limit_with_reset:
                    logger.info(f"Max retries reached but continuing for rate limit with reset time: {e.reset_time}")

                # Calculate delay based on exception type
                delay = self._get_delay_for_exception(e, attempt)

                # Show progress for rate limit waits
                from .exceptions import GitHubRateLimitError
                if isinstance(e, GitHubRateLimitError):
                    # Get progress tracker for this operation
                    progress_manager = get_progress_manager()
                    tracker = progress_manager.get_tracker(operation_name)
                    
                    # Show rate limit info if available
                    if hasattr(e, 'remaining') and hasattr(e, 'limit'):
                        await tracker.show_rate_limit_info(
                            remaining=e.remaining or 0,
                            limit=e.limit or 5000,
                            reset_time=e.reset_time
                        )
                    
                    # Track progress during the wait
                    await tracker.track_rate_limit_wait(
                        wait_seconds=delay,
                        reset_time=e.reset_time,
                        operation_name=operation_name
                    )
                    
                    # Sleep with progress tracking
                    await asyncio.sleep(delay)
                    
                    # Show completion message
                    await tracker.show_completion_message(operation_name)
                    
                    # Clean up tracker
                    progress_manager.cleanup_tracker(operation_name)
                else:
                    # Non-rate-limit error, just log and sleep
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {operation_name}, "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    await asyncio.sleep(delay)

                attempt += 1

            except Exception as e:
                # Non-retryable exception, re-raise immediately
                logger.error(f"Non-retryable error in {operation_name}: {e}")
                raise

        # All retries exhausted, raise the last exception
        raise last_exception

    def _is_non_retryable_error(self, exception: Exception) -> bool:
        """Check if an exception should not be retried."""
        from .exceptions import (
            GitHubAPIError,
            GitHubAuthenticationError,
            GitHubNotFoundError,
        )

        # Authentication and not found errors are never retryable
        if isinstance(exception, (GitHubAuthenticationError, GitHubNotFoundError)):
            return True

        # For GitHubAPIError, only retry server errors (5xx)
        if isinstance(exception, GitHubAPIError):
            if exception.status_code and 400 <= exception.status_code < 500:
                # Don't retry client errors (4xx) except rate limits
                from .exceptions import GitHubRateLimitError
                if not isinstance(exception, GitHubRateLimitError):
                    return True

        return False

    def _get_delay_for_exception(self, exception: Exception, attempt: int) -> float:
        """Get appropriate delay based on exception type."""
        from .exceptions import GitHubRateLimitError

        if isinstance(exception, GitHubRateLimitError):
            # For rate limit errors, use the reset time if available
            if exception.reset_time and exception.reset_time > 0:
                return self.calculate_delay(attempt, exception.reset_time)
            else:
                # No reset time available, use progressive backoff for rate limits
                # Use longer delays: 5min, 15min, 30min instead of short exponential backoff
                progressive_delays = [300, 900, 1800]  # 5min, 15min, 30min in seconds
                if attempt < len(progressive_delays):
                    delay = progressive_delays[attempt]
                    logger.info(f"Rate limit without reset time, using progressive backoff: {delay}s")
                    return delay
                else:
                    # For attempts beyond our progressive delays, use 30min
                    logger.info("Rate limit without reset time, using maximum backoff: 1800s (30min)")
                    return 1800
        else:
            # For other errors, use standard exponential backoff
            return self.calculate_delay(attempt)


class CircuitBreaker:
    """Circuit breaker pattern implementation for API resilience."""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: type = Exception,
    ):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Time in seconds before attempting to close circuit
            expected_exception: Exception type that triggers circuit breaker
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "closed"  # closed, open, half_open

    async def call(self, func: Callable[[], T], operation_name: str = "operation") -> T:
        """Execute function through circuit breaker.
        
        Args:
            func: Async function to execute
            operation_name: Name of operation for logging
            
        Returns:
            Result of function execution
            
        Raises:
            Exception if circuit is open or function fails
        """
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
                logger.info(f"Circuit breaker transitioning to half-open for {operation_name}")
            else:
                raise Exception(f"Circuit breaker is open for {operation_name}")

        try:
            result = await func()
            self._on_success(operation_name)
            return result

        except self.expected_exception as e:
            self._on_failure(operation_name)
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time > self.timeout

    def _on_success(self, operation_name: str) -> None:
        """Handle successful operation."""
        if self.state == "half_open":
            self.state = "closed"
            logger.info(f"Circuit breaker reset to closed for {operation_name}")
        self.failure_count = 0

    def _on_failure(self, operation_name: str) -> None:
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                f"Circuit breaker opened for {operation_name} "
                f"after {self.failure_count} failures"
            )
