"""Tests for enhanced rate limit error detection and handling."""

import json
import time
from unittest.mock import Mock, patch

import httpx
import pytest

from forkscout.config import GitHubConfig
from forkscout.github.client import GitHubClient
from forkscout.github.exceptions import GitHubRateLimitError, GitHubAuthenticationError


class TestEnhancedRateLimitDetection:
    """Test enhanced rate limit error detection."""

    def setup_method(self):
        """Set up test fixtures."""
        config = GitHubConfig(token="ghp_1234567890123456789012345678901234567890")
        self.client = GitHubClient(config)

    def test_is_rate_limit_error_with_zero_remaining(self):
        """Test rate limit detection with zero remaining requests."""
        response = Mock(spec=httpx.Response)
        response.text = "API rate limit exceeded"
        response.json.return_value = {"message": "API rate limit exceeded"}
        
        assert self.client._is_rate_limit_error(response, "0") is True

    def test_is_rate_limit_error_with_numeric_zero_remaining(self):
        """Test rate limit detection with numeric zero remaining."""
        response = Mock(spec=httpx.Response)
        response.text = "API rate limit exceeded"
        response.json.return_value = {"message": "API rate limit exceeded"}
        
        assert self.client._is_rate_limit_error(response, "0") is True

    def test_is_rate_limit_error_with_response_text_indicators(self):
        """Test rate limit detection via response text indicators."""
        response = Mock(spec=httpx.Response)
        response.text = "You have exceeded the GitHub API rate limit"
        response.json.side_effect = Exception("No JSON")
        
        assert self.client._is_rate_limit_error(response, "100") is True

    def test_is_rate_limit_error_with_abuse_detection(self):
        """Test rate limit detection for abuse detection."""
        response = Mock(spec=httpx.Response)
        response.text = "You have been flagged for abuse detection"
        response.json.side_effect = Exception("No JSON")
        
        assert self.client._is_rate_limit_error(response, "100") is True

    def test_is_rate_limit_error_with_secondary_rate_limit(self):
        """Test rate limit detection for secondary rate limits."""
        response = Mock(spec=httpx.Response)
        response.text = "You have exceeded a secondary rate limit"
        response.json.side_effect = Exception("No JSON")
        
        assert self.client._is_rate_limit_error(response, "100") is True

    def test_is_rate_limit_error_with_json_message(self):
        """Test rate limit detection via JSON message."""
        response = Mock(spec=httpx.Response)
        response.text = "Forbidden"
        response.json.return_value = {
            "message": "API rate limit exceeded for user",
            "documentation_url": "https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limiting"
        }
        
        assert self.client._is_rate_limit_error(response, "50") is True

    def test_is_rate_limit_error_with_documentation_url(self):
        """Test rate limit detection via documentation URL."""
        response = Mock(spec=httpx.Response)
        response.text = "Forbidden"
        response.json.return_value = {
            "message": "Forbidden",
            "documentation_url": "https://docs.github.com/rest/overview/resources-in-the-rest-api#abuse-rate-limits"
        }
        
        assert self.client._is_rate_limit_error(response, "100") is True

    def test_is_rate_limit_error_false_for_auth_error(self):
        """Test that authentication errors are not detected as rate limits."""
        response = Mock(spec=httpx.Response)
        response.text = "Bad credentials"
        response.json.return_value = {
            "message": "Bad credentials",
            "documentation_url": "https://docs.github.com/rest"
        }
        
        assert self.client._is_rate_limit_error(response, "100") is False

    def test_is_rate_limit_error_false_for_permission_error(self):
        """Test that permission errors are not detected as rate limits."""
        response = Mock(spec=httpx.Response)
        response.text = "Repository access blocked"
        response.json.return_value = {
            "message": "Repository access blocked",
            "documentation_url": "https://docs.github.com/rest"
        }
        
        assert self.client._is_rate_limit_error(response, "100") is False

    def test_is_rate_limit_error_handles_json_parse_error(self):
        """Test that JSON parse errors are handled gracefully."""
        response = Mock(spec=httpx.Response)
        response.text = "Some error text"
        response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        # Should not crash and should return False for non-rate-limit text
        assert self.client._is_rate_limit_error(response, "100") is False

    def test_is_rate_limit_error_handles_text_access_error(self):
        """Test that text access errors are handled gracefully."""
        response = Mock(spec=httpx.Response)
        response.text = property(lambda self: exec('raise Exception("Text access error")'))
        response.json.return_value = {"message": "Some error"}
        
        # Should not crash and should return False when text access fails
        assert self.client._is_rate_limit_error(response, "100") is False

    @pytest.mark.asyncio
    async def test_request_distinguishes_rate_limit_from_auth_error(self):
        """Test that 403 responses are properly distinguished between rate limits and auth errors."""
        from tests.utils.test_helpers import mock_rate_limiter
        
        async with mock_rate_limiter(self.client):
            # Mock HTTP client
            mock_response = Mock(spec=httpx.Response)
            mock_response.status_code = 403
            mock_response.headers = {
                "x-ratelimit-remaining": "0",
                "x-ratelimit-reset": str(int(time.time()) + 3600),
                "x-ratelimit-limit": "5000"
            }
            mock_response.text = "API rate limit exceeded"
            mock_response.json.return_value = {"message": "API rate limit exceeded"}
            
            mock_client = Mock(spec=httpx.AsyncClient)
            mock_client.request.return_value = mock_response
            
            self.client._client = mock_client
            
            # Should raise GitHubRateLimitError, not GitHubAuthenticationError
            with pytest.raises(GitHubRateLimitError) as exc_info:
                await self.client._request("GET", "/test")
            
            assert exc_info.value.reset_time is not None
            assert exc_info.value.remaining == 0
            assert exc_info.value.limit == 5000

    @pytest.mark.asyncio
    async def test_request_handles_auth_error_when_not_rate_limited(self):
        """Test that 403 responses without rate limit indicators are treated as auth errors."""
        from tests.utils.test_helpers import mock_rate_limiter
        
        async with mock_rate_limiter(self.client):
            # Mock HTTP client
            mock_response = Mock(spec=httpx.Response)
            mock_response.status_code = 403
            mock_response.headers = {
                "x-ratelimit-remaining": "4999",  # Not rate limited
                "x-ratelimit-reset": str(int(time.time()) + 3600),
                "x-ratelimit-limit": "5000"
            }
            mock_response.text = "Repository access blocked"
            mock_response.json.return_value = {"message": "Repository access blocked"}
            
            mock_client = Mock(spec=httpx.AsyncClient)
            mock_client.request.return_value = mock_response
            
            self.client._client = mock_client
            
            # Should raise GitHubAPIError (not GitHubRateLimitError) for 403 without rate limit indicators
            from forkscout.github.exceptions import GitHubAPIError
            with pytest.raises(GitHubAPIError) as exc_info:
                await self.client._request("GET", "/test")
            
            # Verify it's not a rate limit error
            assert exc_info.value.status_code == 403
            assert "403" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_request_handles_429_as_rate_limit(self):
        """Test that 429 responses are properly handled as rate limits."""
        from tests.utils.test_helpers import mock_rate_limiter
        
        async with mock_rate_limiter(self.client):
            # Mock HTTP client
            mock_response = Mock(spec=httpx.Response)
            mock_response.status_code = 429
            mock_response.headers = {
                "retry-after": "60"
            }
            mock_response.text = "Too Many Requests"
            mock_response.json.return_value = {"message": "Too Many Requests"}
            
            mock_client = Mock(spec=httpx.AsyncClient)
            mock_client.request.return_value = mock_response
            
            self.client._client = mock_client
            
            # Should raise GitHubRateLimitError
            with pytest.raises(GitHubRateLimitError) as exc_info:
                await self.client._request("GET", "/test")
            
            # Should have calculated reset time from retry-after header
            assert exc_info.value.reset_time is not None
            assert exc_info.value.remaining == 0

    @pytest.mark.asyncio
    async def test_request_handles_429_without_retry_after(self):
        """Test that 429 responses without retry-after header are handled."""
        from tests.utils.test_helpers import mock_rate_limiter
        
        async with mock_rate_limiter(self.client):
            # Mock HTTP client
            mock_response = Mock(spec=httpx.Response)
            mock_response.status_code = 429
            mock_response.headers = {}
            mock_response.text = "Too Many Requests"
            mock_response.json.return_value = {"message": "Too Many Requests"}
            
            mock_client = Mock(spec=httpx.AsyncClient)
            mock_client.request.return_value = mock_response
            
            self.client._client = mock_client
            
            # Should raise GitHubRateLimitError
            with pytest.raises(GitHubRateLimitError) as exc_info:
                await self.client._request("GET", "/test")
            
            assert exc_info.value.reset_time is None
            assert exc_info.value.remaining == 0


class TestRateLimitErrorMessages:
    """Test enhanced rate limit error messages."""

    def test_rate_limit_error_message_with_reset_time(self):
        """Test rate limit error message includes reset time information."""
        reset_time = int(time.time()) + 3600  # 1 hour from now
        error = GitHubRateLimitError(
            "Rate limit exceeded",
            reset_time=reset_time,
            remaining=0,
            limit=5000
        )
        
        # The error should contain useful information
        assert error.reset_time == reset_time
        assert error.remaining == 0
        assert error.limit == 5000

    def test_rate_limit_error_message_without_reset_time(self):
        """Test rate limit error message when no reset time is available."""
        error = GitHubRateLimitError(
            "Rate limit exceeded",
            reset_time=None,
            remaining=0,
            limit=5000
        )
        
        # The error should still contain useful information
        assert error.reset_time is None
        assert error.remaining == 0
        assert error.limit == 5000

    def test_rate_limit_error_preserves_status_code(self):
        """Test that rate limit errors preserve the HTTP status code."""
        error = GitHubRateLimitError(
            "Rate limit exceeded",
            reset_time=int(time.time()) + 3600,
            remaining=0,
            limit=5000,
            status_code=403
        )
        
        assert error.status_code == 403