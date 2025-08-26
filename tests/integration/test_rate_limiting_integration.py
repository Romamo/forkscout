"""Integration tests for rate limiting and error handling."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from forklift.config import GitHubConfig
from forklift.github.client import GitHubClient
from forklift.github.rate_limiter import CircuitBreaker, RateLimitHandler


@pytest.mark.asyncio
async def test_rate_limiting_integration():
    """Test rate limiting integration with real-like scenario."""
    config = GitHubConfig(
        token="ghp_1234567890abcdef1234567890abcdef12345678",
        base_url="https://api.github.com",
        timeout_seconds=30,
    )

    # Create rate limiter with fast settings for testing
    rate_limiter = RateLimitHandler(
        max_retries=3,
        base_delay=0.01,
        max_delay=1.0,
        backoff_factor=2.0,
        jitter=False,
    )

    client = GitHubClient(config=config, rate_limit_handler=rate_limiter)

    # Mock a sequence of responses: rate limit, server error, success
    responses = [
        # First request: rate limited
        Mock(
            status_code=403,
            headers={
                "x-ratelimit-remaining": "0",
                "x-ratelimit-reset": "1234567890",
                "x-ratelimit-limit": "5000",
            }
        ),
        # Second request: server error
        Mock(status_code=500),
        # Third request: success
        Mock(
            status_code=200,
            json=Mock(return_value={"message": "Success after retries"}),
            raise_for_status=Mock(return_value=None)
        ),
    ]

    mock_client = AsyncMock()
    mock_client.request.side_effect = responses

    with patch("asyncio.sleep"):  # Mock sleep to speed up test
        client._client = mock_client
        result = await client.get("test/endpoint")

    assert result == {"message": "Success after retries"}
    assert mock_client.request.call_count == 3


@pytest.mark.asyncio
async def test_circuit_breaker_integration():
    """Test circuit breaker integration with multiple failures."""
    config = GitHubConfig(
        token="ghp_1234567890abcdef1234567890abcdef12345678",
        base_url="https://api.github.com",
        timeout_seconds=30,
    )

    # Create circuit breaker with low threshold for testing
    circuit_breaker = CircuitBreaker(
        failure_threshold=2,
        timeout=0.1,
        expected_exception=Exception,
    )

    client = GitHubClient(config=config, circuit_breaker=circuit_breaker)

    # Mock consistent failures
    mock_response = Mock(status_code=500)
    mock_client = AsyncMock()
    mock_client.request.return_value = mock_response

    client._client = mock_client

    # First two requests should fail and open the circuit
    for i in range(2):
        with pytest.raises(Exception):
            await client.get(f"test/endpoint/{i}")

    # Circuit should be open now
    assert circuit_breaker.state == "open"

    # Next request should be blocked by circuit breaker
    with pytest.raises(Exception, match="Circuit breaker is open"):
        await client.get("test/endpoint/blocked")


@pytest.mark.asyncio
async def test_comprehensive_error_handling():
    """Test comprehensive error handling with various error types."""
    config = GitHubConfig(
        token="ghp_1234567890abcdef1234567890abcdef12345678",
        base_url="https://api.github.com",
        timeout_seconds=30,
    )

    client = GitHubClient(config=config)

    # Test different error scenarios
    test_cases = [
        # Authentication error - should not retry
        (Mock(status_code=401), 1, "authentication"),
        # Not found error - should not retry
        (Mock(status_code=404), 1, "not found"),
        # Server error - should retry
        (Mock(status_code=500), 4, "server error"),  # 1 initial + 3 retries
    ]

    for mock_response, expected_calls, error_type in test_cases:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        client._client = mock_client

        with pytest.raises(Exception):
            await client.get(f"test/{error_type}")

        # Check that the expected number of calls were made
        if error_type in ["authentication", "not found"]:
            # These should not be retried
            assert mock_client.request.call_count == expected_calls
        else:
            # Server errors should be retried
            assert mock_client.request.call_count == expected_calls


@pytest.mark.asyncio
async def test_rate_limit_monitoring():
    """Test rate limit monitoring functionality."""
    config = GitHubConfig(
        token="ghp_1234567890abcdef1234567890abcdef12345678",
        base_url="https://api.github.com",
        timeout_seconds=30,
    )

    client = GitHubClient(config=config)

    # Mock rate limit response
    rate_limit_data = {
        "rate": {
            "limit": 5000,
            "remaining": 4500,
            "reset": 1234567890,
            "used": 500,
        }
    }

    mock_client = AsyncMock()
    mock_client.request.return_value = Mock(
        status_code=200,
        json=Mock(return_value=rate_limit_data),
        raise_for_status=Mock(return_value=None)
    )

    client._client = mock_client

    # Test rate limit checking
    status = await client.check_rate_limit()

    assert status["limit"] == 5000
    assert status["remaining"] == 4500
    assert status["used"] == 500
    assert status["reset"] == 1234567890


@pytest.mark.asyncio
async def test_circuit_breaker_status_monitoring():
    """Test circuit breaker status monitoring."""
    config = GitHubConfig(
        token="ghp_1234567890abcdef1234567890abcdef12345678",
        base_url="https://api.github.com",
        timeout_seconds=30,
    )

    circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=60.0)
    client = GitHubClient(config=config, circuit_breaker=circuit_breaker)

    # Test initial status
    status = client.get_circuit_breaker_status()

    assert status["state"] == "closed"
    assert status["failure_count"] == 0
    assert status["failure_threshold"] == 3
    assert status["timeout"] == 60.0

    # Test manual reset
    circuit_breaker.failure_count = 2
    circuit_breaker.state = "open"

    client.reset_circuit_breaker()

    status = client.get_circuit_breaker_status()
    assert status["state"] == "closed"
    assert status["failure_count"] == 0
