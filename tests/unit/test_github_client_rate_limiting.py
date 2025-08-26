"""Tests for GitHub client rate limiting and error handling."""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from forklift.config import GitHubConfig
from forklift.github.client import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubClient,
    GitHubNotFoundError,
)
from forklift.github.rate_limiter import CircuitBreaker, RateLimitHandler


@pytest.fixture
def github_config():
    """Create a test GitHub configuration."""
    return GitHubConfig(
        token="ghp_1234567890abcdef1234567890abcdef12345678",  # Valid format for testing
        base_url="https://api.github.com",
        timeout_seconds=30,
    )


@pytest.fixture
def rate_limit_handler():
    """Create a test rate limit handler with fast retries."""
    return RateLimitHandler(
        max_retries=3,
        base_delay=0.01,  # Fast for testing
        max_delay=1.0,
        backoff_factor=2.0,
        jitter=False,  # Deterministic for testing
    )


@pytest.fixture
def circuit_breaker():
    """Create a test circuit breaker."""
    return CircuitBreaker(
        failure_threshold=3,
        timeout=0.1,  # Fast for testing
        expected_exception=GitHubAPIError,
    )


class TestGitHubClientRateLimiting:
    """Test GitHub client rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limit_error_triggers_retry(self, github_config, rate_limit_handler):
        """Test that rate limit errors trigger retry logic."""
        client = GitHubClient(
            config=github_config,
            rate_limit_handler=rate_limit_handler,
        )

        # Mock HTTP client
        mock_response_1 = Mock()
        mock_response_1.status_code = 403
        mock_response_1.headers = {
            "x-ratelimit-remaining": "0",
            "x-ratelimit-reset": str(int(time.time()) + 1),
            "x-ratelimit-limit": "5000",
        }

        mock_response_2 = Mock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = {"test": "data"}
        mock_response_2.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.request.side_effect = [
            httpx.Response(
                status_code=403,
                headers={
                    "x-ratelimit-remaining": "0",
                    "x-ratelimit-reset": str(int(time.time()) + 1),
                    "x-ratelimit-limit": "5000",
                },
                content=b'{"message": "API rate limit exceeded"}',
            ),
            mock_response_2,
        ]

        with patch("asyncio.sleep"):  # Mock sleep to speed up test
            client._client = mock_client
            result = await client.get("test/endpoint")

        assert result == {"test": "data"}
        assert mock_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_429_rate_limit_error_handling(self, github_config, rate_limit_handler):
        """Test handling of 429 Too Many Requests errors."""
        client = GitHubClient(
            config=github_config,
            rate_limit_handler=rate_limit_handler,
        )

        mock_response_1 = Mock()
        mock_response_1.status_code = 429
        mock_response_1.headers = {"retry-after": "60"}

        mock_response_2 = Mock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = {"test": "data"}
        mock_response_2.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.request.side_effect = [mock_response_1, mock_response_2]

        with patch("asyncio.sleep") as mock_sleep:
            client._client = mock_client
            result = await client.get("test/endpoint")

        assert result == {"test": "data"}
        assert mock_client.request.call_count == 2
        # Should have slept for retry delay
        mock_sleep.assert_called()

    @pytest.mark.asyncio
    async def test_network_error_retry(self, github_config, rate_limit_handler):
        """Test that network errors trigger retry logic."""
        client = GitHubClient(
            config=github_config,
            rate_limit_handler=rate_limit_handler,
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.request.side_effect = [
            httpx.NetworkError("Connection failed"),
            mock_response,
        ]

        client._client = mock_client
        result = await client.get("test/endpoint")

        assert result == {"test": "data"}
        assert mock_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_timeout_error_retry(self, github_config, rate_limit_handler):
        """Test that timeout errors trigger retry logic."""
        client = GitHubClient(
            config=github_config,
            rate_limit_handler=rate_limit_handler,
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.request.side_effect = [
            httpx.TimeoutException("Request timeout"),
            mock_response,
        ]

        client._client = mock_client
        result = await client.get("test/endpoint")

        assert result == {"test": "data"}
        assert mock_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_server_error_retry(self, github_config, rate_limit_handler):
        """Test that server errors (5xx) trigger retry logic."""
        client = GitHubClient(
            config=github_config,
            rate_limit_handler=rate_limit_handler,
        )

        mock_response_1 = Mock()
        mock_response_1.status_code = 500

        mock_response_2 = Mock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = {"test": "data"}
        mock_response_2.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.request.side_effect = [mock_response_1, mock_response_2]

        client._client = mock_client
        result = await client.get("test/endpoint")

        assert result == {"test": "data"}
        assert mock_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_authentication_error_no_retry(self, github_config, rate_limit_handler):
        """Test that authentication errors are not retried."""
        client = GitHubClient(
            config=github_config,
            rate_limit_handler=rate_limit_handler,
        )

        mock_response = Mock()
        mock_response.status_code = 401

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        client._client = mock_client

        with pytest.raises(GitHubAuthenticationError):
            await client.get("test/endpoint")

        # Should not retry authentication errors
        assert mock_client.request.call_count == 1

    @pytest.mark.asyncio
    async def test_not_found_error_no_retry(self, github_config, rate_limit_handler):
        """Test that 404 errors are not retried."""
        client = GitHubClient(
            config=github_config,
            rate_limit_handler=rate_limit_handler,
        )

        mock_response = Mock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        client._client = mock_client

        with pytest.raises(GitHubNotFoundError):
            await client.get("test/endpoint")

        # Should not retry 404 errors
        assert mock_client.request.call_count == 1

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, github_config):
        """Test that max retries are respected."""
        rate_limit_handler = RateLimitHandler(max_retries=2, base_delay=0.01)
        client = GitHubClient(
            config=github_config,
            rate_limit_handler=rate_limit_handler,
        )

        mock_response = Mock()
        mock_response.status_code = 500

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        client._client = mock_client

        with pytest.raises(GitHubAPIError):
            await client.get("test/endpoint")

        # Should have tried 3 times (initial + 2 retries)
        assert mock_client.request.call_count == 3


class TestGitHubClientCircuitBreaker:
    """Test GitHub client circuit breaker functionality."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self, github_config, circuit_breaker):
        """Test that circuit breaker opens after repeated failures."""
        client = GitHubClient(
            config=github_config,
            circuit_breaker=circuit_breaker,
        )

        mock_response = Mock()
        mock_response.status_code = 500

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        client._client = mock_client

        # Cause failures to open circuit breaker
        for i in range(3):
            with pytest.raises(GitHubAPIError):
                await client.get(f"test/endpoint/{i}")

        assert circuit_breaker.state == "open"

        # Next request should be blocked by circuit breaker
        with pytest.raises(Exception, match="Circuit breaker is open"):
            await client.get("test/endpoint/blocked")

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self, github_config):
        """Test circuit breaker recovery after timeout."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            timeout=0.1,  # Short timeout for testing
            expected_exception=GitHubAPIError,
        )

        client = GitHubClient(
            config=github_config,
            circuit_breaker=circuit_breaker,
        )

        # Open the circuit breaker
        mock_response_error = Mock()
        mock_response_error.status_code = 500

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response_error

        client._client = mock_client

        for i in range(2):
            with pytest.raises(GitHubAPIError):
                await client.get(f"test/endpoint/{i}")

        assert circuit_breaker.state == "open"

        # Wait for timeout
        await asyncio.sleep(0.2)

        # Successful request should close the circuit
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"test": "data"}
        mock_response_success.raise_for_status.return_value = None

        mock_client.request.return_value = mock_response_success

        result = await client.get("test/endpoint/recovery")

        assert result == {"test": "data"}
        assert circuit_breaker.state == "closed"


class TestGitHubClientUtilityMethods:
    """Test GitHub client utility methods for monitoring."""

    @pytest.mark.asyncio
    async def test_wait_for_rate_limit_reset(self, github_config):
        """Test waiting for rate limit reset."""
        client = GitHubClient(config=github_config)

        # Mock rate limit response
        rate_limit_data = {
            "rate": {
                "limit": 5000,
                "remaining": 5,  # Low remaining
                "reset": int(time.time()) + 1,  # Reset in 1 second
                "used": 4995,
            }
        }

        with patch.object(client, "get_rate_limit", return_value=rate_limit_data):
            with patch("asyncio.sleep") as mock_sleep:
                await client.wait_for_rate_limit_reset()

        # Should have slept for approximately 1 second + buffer
        mock_sleep.assert_called_once()
        sleep_duration = mock_sleep.call_args[0][0]
        assert 0.5 <= sleep_duration <= 2.5

    @pytest.mark.asyncio
    async def test_wait_for_rate_limit_reset_high_remaining(self, github_config):
        """Test that we don't wait when rate limit remaining is high."""
        client = GitHubClient(config=github_config)

        # Mock rate limit response with high remaining
        rate_limit_data = {
            "rate": {
                "limit": 5000,
                "remaining": 1000,  # High remaining
                "reset": int(time.time()) + 3600,
                "used": 4000,
            }
        }

        with patch.object(client, "get_rate_limit", return_value=rate_limit_data):
            with patch("asyncio.sleep") as mock_sleep:
                await client.wait_for_rate_limit_reset()

        # Should not have slept
        mock_sleep.assert_not_called()

    def test_get_circuit_breaker_status(self, github_config, circuit_breaker):
        """Test getting circuit breaker status."""
        client = GitHubClient(
            config=github_config,
            circuit_breaker=circuit_breaker,
        )

        status = client.get_circuit_breaker_status()

        assert status["state"] == "closed"
        assert status["failure_count"] == 0
        assert status["failure_threshold"] == 3
        assert status["timeout"] == 0.1

    def test_reset_circuit_breaker(self, github_config, circuit_breaker):
        """Test manually resetting circuit breaker."""
        client = GitHubClient(
            config=github_config,
            circuit_breaker=circuit_breaker,
        )

        # Simulate some failures
        circuit_breaker.failure_count = 2
        circuit_breaker.last_failure_time = time.time()
        circuit_breaker.state = "open"

        client.reset_circuit_breaker()

        assert circuit_breaker.state == "closed"
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.last_failure_time is None


class TestIntegrationScenarios:
    """Integration tests for complex error handling scenarios."""

    @pytest.mark.asyncio
    async def test_complex_error_recovery_scenario(self, github_config):
        """Test complex scenario with multiple error types and recovery."""
        rate_limit_handler = RateLimitHandler(max_retries=5, base_delay=0.01)
        circuit_breaker = CircuitBreaker(failure_threshold=3, expected_exception=GitHubAPIError)

        client = GitHubClient(
            config=github_config,
            rate_limit_handler=rate_limit_handler,
            circuit_breaker=circuit_breaker,
        )

        # Sequence of errors followed by success
        responses = [
            # Rate limit error
            Mock(
                status_code=403,
                headers={
                    "x-ratelimit-remaining": "0",
                    "x-ratelimit-reset": str(int(time.time()) + 1),
                    "x-ratelimit-limit": "5000",
                }
            ),
            # Server error
            Mock(status_code=500),
            # Network error (will be raised as exception)
            httpx.NetworkError("Connection failed"),
            # Success
            Mock(
                status_code=200,
                json=Mock(return_value={"test": "success"}),
                raise_for_status=Mock(return_value=None)
            ),
        ]

        mock_client = AsyncMock()
        mock_client.request.side_effect = responses

        with patch("asyncio.sleep"):  # Mock sleep to speed up test
            client._client = mock_client
            result = await client.get("test/endpoint")

        assert result == {"test": "success"}
        # Should have made 4 requests (3 failures + 1 success)
        assert mock_client.request.call_count == 4
        # Circuit breaker should still be closed (only 1 failure from its perspective)
        assert circuit_breaker.state == "closed"

    @pytest.mark.asyncio
    async def test_repository_operations_with_error_handling(self, github_config):
        """Test that repository operations work with error handling."""
        client = GitHubClient(config=github_config)

        # Mock successful repository response after initial failure
        repo_data = {
            "id": 123,
            "name": "test-repo",
            "full_name": "owner/test-repo",
            "owner": {"login": "owner", "id": 456},
            "private": False,
            "url": "https://api.github.com/repos/owner/test-repo",
            "html_url": "https://github.com/owner/test-repo",
            "clone_url": "https://github.com/owner/test-repo.git",
            "description": "Test repository",
            "fork": False,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-02T00:00:00Z",
            "pushed_at": "2023-01-02T00:00:00Z",
            "stargazers_count": 10,
            "watchers_count": 5,
            "forks_count": 2,
            "default_branch": "main",
        }

        responses = [
            Mock(status_code=500),  # Server error
            Mock(
                status_code=200,
                json=Mock(return_value=repo_data),
                raise_for_status=Mock(return_value=None)
            ),
        ]

        mock_client = AsyncMock()
        mock_client.request.side_effect = responses

        client._client = mock_client
        repository = await client.get_repository("owner", "test-repo")

        assert repository.name == "test-repo"
        assert repository.owner == "owner"
        assert mock_client.request.call_count == 2
