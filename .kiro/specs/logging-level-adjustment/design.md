# Design Document

## Overview

This design addresses the specific logging level change for "Resource not found" errors in the GitHub API rate limiter. The change is minimal and focused - we need to modify the logging level from ERROR to WARNING for GitHubNotFoundError exceptions in the `RateLimitHandler.execute_with_retry()` method.

## Architecture

The change affects only the `RateLimitHandler` class in `src/forkscout/github/rate_limiter.py`. No architectural changes are needed - this is a simple logging level adjustment.

### Current Flow
1. `execute_with_retry()` catches exceptions
2. `_is_non_retryable_error()` identifies GitHubNotFoundError as non-retryable
3. Error is logged at ERROR level with "Non-retryable error" message
4. Exception is re-raised

### Modified Flow
1. `execute_with_retry()` catches exceptions
2. `_is_non_retryable_error()` identifies GitHubNotFoundError as non-retryable
3. **NEW:** Check if error is GitHubNotFoundError specifically
4. **NEW:** Log GitHubNotFoundError at WARNING level, others at ERROR level
5. Exception is re-raised

## Components and Interfaces

### Modified Component: RateLimitHandler

**File:** `src/forkscout/github/rate_limiter.py`

**Method:** `execute_with_retry()`

**Changes:**
- Replace single `logger.error()` call with conditional logging
- Use `logger.warning()` for GitHubNotFoundError
- Use `logger.error()` for all other non-retryable errors

### Interface Changes
- No public interface changes
- No method signature changes
- No return value changes

## Data Models

No data model changes required. This is purely a logging adjustment.

## Error Handling

The error handling logic remains identical:
- Same exception detection
- Same retry behavior
- Same exception re-raising
- Only the logging level changes for GitHubNotFoundError

## Testing Strategy

### Unit Tests
- Test that GitHubNotFoundError logs at WARNING level
- Test that other non-retryable errors still log at ERROR level
- Test that the error message format remains the same
- Test that exception re-raising behavior is unchanged

### Integration Tests
- Verify logging behavior in real rate limiter scenarios
- Confirm no regression in error handling behavior

### Manual Testing
- Run repository analysis that encounters missing repositories
- Verify log output shows WARNING level for "Resource not found" errors
- Verify other errors still show at ERROR level