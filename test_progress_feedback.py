#!/usr/bin/env python3
"""Test script to demonstrate rate limit progress feedback."""

import asyncio
import time
from forklift.github.exceptions import GitHubRateLimitError
from forklift.github.rate_limiter import RateLimitHandler


async def test_progress_feedback():
    """Test the progress feedback system."""
    
    print("Testing rate limit progress feedback...")
    
    # Create rate limiter
    handler = RateLimitHandler(max_retries=2, base_delay=0.1)
    
    # Simulate a rate limit error with reset time
    reset_time = int(time.time()) + 10  # 10 seconds from now
    exception = GitHubRateLimitError(
        "GitHub API rate limit exceeded",
        reset_time=reset_time,
        remaining=0,
        limit=5000
    )
    
    call_count = 0
    async def failing_func():
        nonlocal call_count
        call_count += 1
        print(f"  API call attempt {call_count}")
        if call_count <= 1:  # Fail first attempt
            raise exception
        return "success"
    
    print("\n1. Testing rate limit with reset time (10 second wait):")
    try:
        result = await handler.execute_with_retry(failing_func, "test API operation")
        print(f"✅ Operation succeeded: {result}")
    except Exception as e:
        print(f"❌ Operation failed: {e}")
    
    print("\n2. Testing rate limit without reset time (progressive backoff):")
    
    # Test without reset time
    exception_no_reset = GitHubRateLimitError(
        "GitHub API rate limit exceeded",
        reset_time=0,  # No reset time
        remaining=0,
        limit=5000
    )
    
    call_count = 0
    async def failing_func_no_reset():
        nonlocal call_count
        call_count += 1
        print(f"  API call attempt {call_count}")
        if call_count <= 1:  # Fail first attempt
            raise exception_no_reset
        return "success"
    
    try:
        result = await handler.execute_with_retry(failing_func_no_reset, "test API operation")
        print(f"✅ Operation succeeded: {result}")
    except Exception as e:
        print(f"❌ Operation failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_progress_feedback())