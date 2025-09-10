"""Unit tests for OpenAI error handler."""

from unittest.mock import Mock

import httpx

from forkscout.ai.error_handler import OpenAIErrorHandler
from forkscout.models.ai_summary import AIErrorType


class TestOpenAIErrorHandler:
    """Test cases for OpenAI error handler."""

    def test_error_handler_initialization(self):
        """Test error handler initialization."""
        handler = OpenAIErrorHandler()
        assert handler.max_retries == 3

        handler = OpenAIErrorHandler(max_retries=5)
        assert handler.max_retries == 5

    def test_classify_error_authentication(self):
        """Test error classification for authentication errors."""
        handler = OpenAIErrorHandler()

        # Mock 401 response
        response = Mock()
        response.status_code = 401
        error = httpx.HTTPStatusError("Auth error", request=Mock(), response=response)

        assert handler.classify_error(error) == AIErrorType.AUTHENTICATION

    def test_classify_error_rate_limit(self):
        """Test error classification for rate limit errors."""
        handler = OpenAIErrorHandler()

        # Mock 429 response
        response = Mock()
        response.status_code = 429
        error = httpx.HTTPStatusError("Rate limit", request=Mock(), response=response)

        assert handler.classify_error(error) == AIErrorType.RATE_LIMIT

    def test_classify_error_invalid_request(self):
        """Test error classification for invalid request errors."""
        handler = OpenAIErrorHandler()

        # Mock 400 response
        response = Mock()
        response.status_code = 400
        error = httpx.HTTPStatusError("Bad request", request=Mock(), response=response)

        assert handler.classify_error(error) == AIErrorType.INVALID_REQUEST

        # Test ValueError
        error = ValueError("Invalid parameter")
        assert handler.classify_error(error) == AIErrorType.INVALID_REQUEST

    def test_classify_error_model_error(self):
        """Test error classification for model/server errors."""
        handler = OpenAIErrorHandler()

        # Mock 500 response
        response = Mock()
        response.status_code = 500
        error = httpx.HTTPStatusError("Server error", request=Mock(), response=response)

        assert handler.classify_error(error) == AIErrorType.MODEL_ERROR

    def test_classify_error_timeout(self):
        """Test error classification for timeout errors."""
        handler = OpenAIErrorHandler()

        error = httpx.TimeoutException("Request timeout")
        assert handler.classify_error(error) == AIErrorType.TIMEOUT

    def test_classify_error_network(self):
        """Test error classification for network errors."""
        handler = OpenAIErrorHandler()

        error = httpx.RequestError("Network error")
        assert handler.classify_error(error) == AIErrorType.NETWORK_ERROR

        error = httpx.ConnectError("Connection failed")
        assert handler.classify_error(error) == AIErrorType.NETWORK_ERROR

    def test_classify_error_unknown(self):
        """Test error classification for unknown errors."""
        handler = OpenAIErrorHandler()

        error = RuntimeError("Unknown error")
        assert handler.classify_error(error) == AIErrorType.UNKNOWN

    def test_is_retryable_true(self):
        """Test retryable error detection for retryable errors."""
        handler = OpenAIErrorHandler()

        # Rate limit error
        response = Mock()
        response.status_code = 429
        error = httpx.HTTPStatusError("Rate limit", request=Mock(), response=response)
        assert handler.is_retryable(error) is True

        # Timeout error
        error = httpx.TimeoutException("Timeout")
        assert handler.is_retryable(error) is True

        # Network error
        error = httpx.RequestError("Network error")
        assert handler.is_retryable(error) is True

        # Server error
        response = Mock()
        response.status_code = 500
        error = httpx.HTTPStatusError("Server error", request=Mock(), response=response)
        assert handler.is_retryable(error) is True

    def test_is_retryable_false(self):
        """Test retryable error detection for non-retryable errors."""
        handler = OpenAIErrorHandler()

        # Authentication error
        response = Mock()
        response.status_code = 401
        error = httpx.HTTPStatusError("Auth error", request=Mock(), response=response)
        assert handler.is_retryable(error) is False

        # Invalid request error
        response = Mock()
        response.status_code = 400
        error = httpx.HTTPStatusError("Bad request", request=Mock(), response=response)
        assert handler.is_retryable(error) is False

        # Unknown error
        error = RuntimeError("Unknown error")
        assert handler.is_retryable(error) is False

    def test_get_retry_delay_rate_limit_with_header(self):
        """Test retry delay calculation for rate limit with retry-after header."""
        handler = OpenAIErrorHandler()

        response = Mock()
        response.status_code = 429
        response.headers = {"retry-after": "30"}
        error = httpx.HTTPStatusError("Rate limit", request=Mock(), response=response)

        delay = handler.get_retry_delay(0, error)
        assert delay == 30.0

    def test_get_retry_delay_rate_limit_without_header(self):
        """Test retry delay calculation for rate limit without retry-after header."""
        handler = OpenAIErrorHandler()

        response = Mock()
        response.status_code = 429
        response.headers = {}
        error = httpx.HTTPStatusError("Rate limit", request=Mock(), response=response)

        delay = handler.get_retry_delay(0, error)
        assert delay == 60  # Default rate limit backoff

        delay = handler.get_retry_delay(1, error)
        assert delay == 120  # Exponential backoff

    def test_get_retry_delay_rate_limit_cap(self):
        """Test retry delay calculation caps at maximum."""
        handler = OpenAIErrorHandler()

        response = Mock()
        response.status_code = 429
        response.headers = {"retry-after": "600"}  # 10 minutes
        error = httpx.HTTPStatusError("Rate limit", request=Mock(), response=response)

        delay = handler.get_retry_delay(0, error)
        assert delay == 300  # Capped at 5 minutes

    def test_get_retry_delay_network_error(self):
        """Test retry delay calculation for network errors."""
        handler = OpenAIErrorHandler()

        error = httpx.TimeoutException("Timeout")

        delay = handler.get_retry_delay(0, error)
        assert delay == 1  # 2^0 = 1

        delay = handler.get_retry_delay(2, error)
        assert delay == 4  # 2^2 = 4

        delay = handler.get_retry_delay(10, error)
        assert delay == 60  # Capped at 1 minute

    def test_get_retry_delay_server_error(self):
        """Test retry delay calculation for server errors."""
        handler = OpenAIErrorHandler()

        response = Mock()
        response.status_code = 500
        error = httpx.HTTPStatusError("Server error", request=Mock(), response=response)

        delay = handler.get_retry_delay(0, error)
        assert delay == 1  # 2^0 = 1

        delay = handler.get_retry_delay(3, error)
        assert delay == 8  # 2^3 = 8

    def test_create_ai_error_http_status_error(self):
        """Test AIError creation from HTTP status error."""
        handler = OpenAIErrorHandler()

        response = Mock()
        response.status_code = 429
        response.text = "Rate limit exceeded"
        error = httpx.HTTPStatusError("Rate limit", request=Mock(), response=response)

        ai_error = handler.create_ai_error(error, commit_sha="abc123", retry_count=2)

        assert ai_error.error_type == AIErrorType.RATE_LIMIT
        assert "HTTP 429" in ai_error.message
        assert "Rate limit exceeded" in ai_error.message
        assert ai_error.commit_sha == "abc123"
        assert ai_error.retry_count == 2
        assert ai_error.recoverable is True

    def test_create_ai_error_generic_exception(self):
        """Test AIError creation from generic exception."""
        handler = OpenAIErrorHandler()

        error = ValueError("Invalid input")

        ai_error = handler.create_ai_error(error)

        assert ai_error.error_type == AIErrorType.INVALID_REQUEST
        assert ai_error.message == "Invalid input"
        assert ai_error.commit_sha is None
        assert ai_error.retry_count == 0
        assert ai_error.recoverable is False

    def test_log_error_with_context(self, caplog):
        """Test error logging with context."""
        handler = OpenAIErrorHandler()

        error = ValueError("Test error")

        handler.log_error(
            error,
            commit_sha="abc123",
            retry_count=1,
            context="test_context"
        )

        assert "test_context" in caplog.text
        assert "commit abc123" in caplog.text
        assert "retry 1" in caplog.text
        assert "Test error" in caplog.text

    def test_log_error_authentication(self, caplog):
        """Test error logging for authentication errors."""
        handler = OpenAIErrorHandler()

        response = Mock()
        response.status_code = 401
        error = httpx.HTTPStatusError("Auth error", request=Mock(), response=response)

        with caplog.at_level("ERROR"):
            handler.log_error(error)

        assert "OpenAI API error (authentication)" in caplog.text

    def test_log_error_rate_limit(self, caplog):
        """Test error logging for rate limit errors."""
        handler = OpenAIErrorHandler()

        response = Mock()
        response.status_code = 429
        error = httpx.HTTPStatusError("Rate limit", request=Mock(), response=response)

        with caplog.at_level("WARNING"):
            handler.log_error(error)

        assert "OpenAI API error (rate_limit)" in caplog.text

    def test_should_abort_authentication_error(self):
        """Test abort decision for authentication errors."""
        handler = OpenAIErrorHandler()

        response = Mock()
        response.status_code = 401
        error = httpx.HTTPStatusError("Auth error", request=Mock(), response=response)

        assert handler.should_abort(error, retry_count=0) is True

    def test_should_abort_non_retryable_error(self):
        """Test abort decision for non-retryable errors."""
        handler = OpenAIErrorHandler()

        response = Mock()
        response.status_code = 400
        error = httpx.HTTPStatusError("Bad request", request=Mock(), response=response)

        assert handler.should_abort(error, retry_count=0) is True

    def test_should_abort_max_retries_exceeded(self):
        """Test abort decision when max retries exceeded."""
        handler = OpenAIErrorHandler(max_retries=2)

        error = httpx.TimeoutException("Timeout")

        assert handler.should_abort(error, retry_count=1) is False  # Still retryable
        assert handler.should_abort(error, retry_count=2) is True   # Max retries reached

    def test_should_abort_retryable_error_within_limit(self):
        """Test abort decision for retryable error within limit."""
        handler = OpenAIErrorHandler()

        error = httpx.TimeoutException("Timeout")

        assert handler.should_abort(error, retry_count=0) is False
        assert handler.should_abort(error, retry_count=2) is False

    def test_get_user_friendly_message_authentication(self):
        """Test user-friendly message for authentication error."""
        handler = OpenAIErrorHandler()

        response = Mock()
        response.status_code = 401
        error = httpx.HTTPStatusError("Auth error", request=Mock(), response=response)

        message = handler.get_user_friendly_message(error)
        assert "Invalid OpenAI API key" in message
        assert "OPENAI_API_KEY" in message

    def test_get_user_friendly_message_rate_limit(self):
        """Test user-friendly message for rate limit error."""
        handler = OpenAIErrorHandler()

        response = Mock()
        response.status_code = 429
        error = httpx.HTTPStatusError("Rate limit", request=Mock(), response=response)

        message = handler.get_user_friendly_message(error)
        assert "rate limit exceeded" in message.lower()

    def test_get_user_friendly_message_timeout(self):
        """Test user-friendly message for timeout error."""
        handler = OpenAIErrorHandler()

        error = httpx.TimeoutException("Timeout")

        message = handler.get_user_friendly_message(error)
        assert "timed out" in message.lower()

    def test_get_user_friendly_message_network(self):
        """Test user-friendly message for network error."""
        handler = OpenAIErrorHandler()

        error = httpx.RequestError("Network error")

        message = handler.get_user_friendly_message(error)
        assert "network error" in message.lower()
        assert "internet connection" in message.lower()

    def test_get_user_friendly_message_invalid_request(self):
        """Test user-friendly message for invalid request error."""
        handler = OpenAIErrorHandler()

        response = Mock()
        response.status_code = 400
        error = httpx.HTTPStatusError("Bad request", request=Mock(), response=response)

        message = handler.get_user_friendly_message(error)
        assert "invalid request" in message.lower()

    def test_get_user_friendly_message_model_error(self):
        """Test user-friendly message for model/server error."""
        handler = OpenAIErrorHandler()

        response = Mock()
        response.status_code = 500
        error = httpx.HTTPStatusError("Server error", request=Mock(), response=response)

        message = handler.get_user_friendly_message(error)
        assert "server error" in message.lower()

    def test_get_user_friendly_message_unknown(self):
        """Test user-friendly message for unknown error."""
        handler = OpenAIErrorHandler()

        error = RuntimeError("Unknown error")

        message = handler.get_user_friendly_message(error)
        assert "unexpected error" in message.lower()
        assert "Unknown error" in message
