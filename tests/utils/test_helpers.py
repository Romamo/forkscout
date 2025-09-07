"""Test helper utilities for mocking and test setup."""

from contextlib import asynccontextmanager
from unittest.mock import patch
from typing import AsyncGenerator


@asynccontextmanager
async def mock_rate_limiter(client) -> AsyncGenerator[None, None]:
    """Context manager to mock rate limiter for tests.
    
    This prevents tests from making real API calls to check rate limits,
    which can cause tests to freeze when rate limits are exceeded.
    
    Args:
        client: GitHubClient instance to mock
        
    Usage:
        async with mock_rate_limiter(client):
            # Test code that uses the client
            result = await client.get_repository("owner", "repo")
    """
    async def mock_execute_with_retry(func, operation_name="", retryable_exceptions=None):
        """Mock execute_with_retry that just calls the function directly."""
        return await func()
    
    with patch.object(client.rate_limit_handler, 'execute_with_retry', side_effect=mock_execute_with_retry):
        yield


def create_test_github_client():
    """Create a GitHub client configured for testing."""
    from forklift.config import GitHubConfig
    from forklift.github.client import GitHubClient
    
    config = GitHubConfig(
        token="ghp_1234567890abcdef1234567890abcdef12345678",
        base_url="https://api.github.com",
        timeout_seconds=30,
    )
    return GitHubClient(config)