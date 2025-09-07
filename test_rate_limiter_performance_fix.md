# Rate Limiter Test Performance Fix

## Issue
The test `tests/unit/test_rate_limiter.py::TestRateLimitHandler::test_execute_with_retry_rate_limit_without_reset_time_respects_max_retries` was taking extremely long to run (potentially hours) because it was using real delays without mocking `asyncio.sleep`.

## Root Cause
When a `GitHubRateLimitError` has no `reset_time`, the rate limiter uses progressive backoff delays:
- First retry: 5 minutes (300 seconds)
- Second retry: 15 minutes (900 seconds) 
- Third retry: 30 minutes (1800 seconds)

The test was actually waiting for these delays instead of mocking them.

## Solution
Added `with patch("asyncio.sleep") as mock_sleep:` to mock the sleep calls, allowing the test to verify the retry logic without actually waiting.

## Before Fix
```python
@pytest.mark.asyncio
async def test_execute_with_retry_rate_limit_without_reset_time_respects_max_retries(self):
    # ... test setup ...
    with pytest.raises(GitHubRateLimitError, match="Rate limited"):
        await handler.execute_with_retry(
            mock_func,
            "test operation", 
            retryable_exceptions=(GitHubRateLimitError,)
        )
```

## After Fix
```python
@pytest.mark.asyncio
async def test_execute_with_retry_rate_limit_without_reset_time_respects_max_retries(self):
    # ... test setup ...
    with patch("asyncio.sleep") as mock_sleep:
        with pytest.raises(GitHubRateLimitError, match="Rate limited"):
            await handler.execute_with_retry(
                mock_func,
                "test operation",
                retryable_exceptions=(GitHubRateLimitError,)
            )
```

## Results
- **Before**: Test could take 50+ minutes (5 + 15 + 30 minutes of actual waiting)
- **After**: Test completes in 0.15 seconds
- **Full test suite**: All 48 rate limiter tests now complete in 0.75 seconds

## Impact
This fix ensures that unit tests remain fast and don't block development workflows. The test still validates the retry logic and max_retries behavior, but without the performance penalty of real delays.