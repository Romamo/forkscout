"""Unit tests for OpenAI client wrapper."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, Mock, patch

import httpx

from forklift.ai.client import OpenAIClient, OpenAIResponse
from forklift.models.ai_summary import AISummaryConfig


class TestOpenAIClient:
    """Test cases for OpenAI client."""

    def test_openai_client_initialization(self):
        """Test OpenAI client initialization with valid API key."""
        api_key = "sk-1234567890abcdef1234567890abcdef"
        client = OpenAIClient(api_key)
        
        assert client.api_key == api_key
        assert client.base_url == "https://api.openai.com/v1"
        assert isinstance(client.config, AISummaryConfig)

    def test_openai_client_initialization_with_config(self):
        """Test OpenAI client initialization with custom config."""
        api_key = "sk-1234567890abcdef1234567890abcdef"
        config = AISummaryConfig(
            model="gpt-4",
            max_tokens=1000,
            temperature=0.5
        )
        
        client = OpenAIClient(api_key, config)
        
        assert client.config.model == "gpt-4"
        assert client.config.max_tokens == 1000
        assert client.config.temperature == 0.5

    def test_openai_client_initialization_with_custom_base_url(self):
        """Test OpenAI client initialization with custom base URL."""
        api_key = "sk-1234567890abcdef1234567890abcdef"
        base_url = "https://custom.openai.com/v1"
        
        client = OpenAIClient(api_key, base_url=base_url)
        
        assert client.base_url == base_url

    def test_api_key_validation_empty_key(self):
        """Test API key validation with empty key."""
        with pytest.raises(ValueError, match="OpenAI API key is required"):
            OpenAIClient("")

    def test_api_key_validation_invalid_prefix(self):
        """Test API key validation with invalid prefix."""
        with pytest.raises(ValueError, match="Invalid OpenAI API key format"):
            OpenAIClient("invalid-key-format")

    def test_api_key_validation_too_short(self):
        """Test API key validation with too short key."""
        with pytest.raises(ValueError, match="OpenAI API key is too short"):
            OpenAIClient("sk-short")

    @pytest.mark.asyncio
    async def test_context_manager_initialization(self):
        """Test async context manager initialization."""
        api_key = "sk-1234567890abcdef1234567890abcdef"
        
        async with OpenAIClient(api_key) as client:
            assert client._client is not None
            assert isinstance(client._client, httpx.AsyncClient)
        
        # Client should be closed after context exit
        assert client._client is None

    @pytest.mark.asyncio
    async def test_create_chat_completion_success(self):
        """Test successful chat completion."""
        api_key = "sk-1234567890abcdef1234567890abcdef"
        
        # Mock response
        mock_response_data = {
            "choices": [
                {
                    "message": {
                        "content": "This is a test response"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            },
            "model": "gpt-4o-mini"
        }
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.post.return_value = mock_response
            
            async with OpenAIClient(api_key) as client:
                messages = [{"role": "user", "content": "Hello"}]
                response = await client.create_chat_completion(messages)
                
                assert isinstance(response, OpenAIResponse)
                assert response.text == "This is a test response"
                assert response.model == "gpt-4o-mini"
                assert response.finish_reason == "stop"
                assert response.usage["total_tokens"] == 15

    @pytest.mark.asyncio
    async def test_create_chat_completion_without_context_manager(self):
        """Test chat completion without context manager raises error."""
        api_key = "sk-1234567890abcdef1234567890abcdef"
        client = OpenAIClient(api_key)
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with pytest.raises(ValueError, match="Client not initialized"):
            await client.create_chat_completion(messages)

    @pytest.mark.asyncio
    async def test_create_chat_completion_empty_messages(self):
        """Test chat completion with empty messages list."""
        api_key = "sk-1234567890abcdef1234567890abcdef"
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            async with OpenAIClient(api_key) as client:
                with pytest.raises(ValueError, match="Messages list cannot be empty"):
                    await client.create_chat_completion([])

    @pytest.mark.asyncio
    async def test_create_chat_completion_invalid_max_tokens(self):
        """Test chat completion with invalid max_tokens."""
        api_key = "sk-1234567890abcdef1234567890abcdef"
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            async with OpenAIClient(api_key) as client:
                messages = [{"role": "user", "content": "Hello"}]
                
                with pytest.raises(ValueError, match="max_tokens must be positive"):
                    await client.create_chat_completion(messages, max_tokens=0)

    @pytest.mark.asyncio
    async def test_create_chat_completion_invalid_temperature(self):
        """Test chat completion with invalid temperature."""
        api_key = "sk-1234567890abcdef1234567890abcdef"
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            async with OpenAIClient(api_key) as client:
                messages = [{"role": "user", "content": "Hello"}]
                
                with pytest.raises(ValueError, match="temperature must be between"):
                    await client.create_chat_completion(messages, temperature=3.0)

    @pytest.mark.asyncio
    async def test_create_chat_completion_authentication_error(self):
        """Test chat completion with authentication error."""
        api_key = "sk-1234567890abcdef1234567890abcdef"
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.request = Mock()
            mock_client.post.return_value = mock_response
            
            async with OpenAIClient(api_key) as client:
                messages = [{"role": "user", "content": "Hello"}]
                
                with pytest.raises(httpx.HTTPStatusError, match="Authentication failed"):
                    await client.create_chat_completion(messages)

    @pytest.mark.asyncio
    async def test_create_chat_completion_rate_limit_error(self):
        """Test chat completion with rate limit error."""
        api_key = "sk-1234567890abcdef1234567890abcdef"
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.headers = {"retry-after": "60"}
            mock_response.request = Mock()
            mock_client.post.return_value = mock_response
            
            async with OpenAIClient(api_key) as client:
                messages = [{"role": "user", "content": "Hello"}]
                
                with pytest.raises(httpx.HTTPStatusError, match="Rate limit exceeded"):
                    await client.create_chat_completion(messages)

    @pytest.mark.asyncio
    async def test_create_chat_completion_timeout_error(self):
        """Test chat completion with timeout error."""
        api_key = "sk-1234567890abcdef1234567890abcdef"
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            mock_client.post.side_effect = httpx.TimeoutException("Request timeout")
            
            async with OpenAIClient(api_key) as client:
                messages = [{"role": "user", "content": "Hello"}]
                
                with pytest.raises(httpx.TimeoutException):
                    await client.create_chat_completion(messages)

    @pytest.mark.asyncio
    async def test_create_chat_completion_invalid_response_format(self):
        """Test chat completion with invalid response format."""
        api_key = "sk-1234567890abcdef1234567890abcdef"
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Response without choices
            mock_response_data = {
                "usage": {"total_tokens": 15},
                "model": "gpt-4o-mini"
            }
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.post.return_value = mock_response
            
            async with OpenAIClient(api_key) as client:
                messages = [{"role": "user", "content": "Hello"}]
                
                with pytest.raises(ValueError, match="Invalid response format"):
                    await client.create_chat_completion(messages)

    @pytest.mark.asyncio
    async def test_create_completion_with_retry_success_after_retry(self):
        """Test completion with retry succeeds after initial failure."""
        api_key = "sk-1234567890abcdef1234567890abcdef"
        
        # Mock successful response
        mock_response_data = {
            "choices": [
                {
                    "message": {"content": "Success after retry"},
                    "finish_reason": "stop"
                }
            ],
            "usage": {"total_tokens": 15},
            "model": "gpt-4o-mini"
        }
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # First call fails with rate limit, second succeeds
            rate_limit_response = Mock()
            rate_limit_response.status_code = 429
            rate_limit_response.headers = {"retry-after": "1"}
            rate_limit_response.request = Mock()
            
            success_response = Mock()
            success_response.status_code = 200
            success_response.json.return_value = mock_response_data
            success_response.raise_for_status.return_value = None
            
            mock_client.post.side_effect = [
                httpx.HTTPStatusError("Rate limit", request=Mock(), response=rate_limit_response),
                success_response
            ]
            
            with patch("asyncio.sleep") as mock_sleep:  # Mock sleep to speed up test
                async with OpenAIClient(api_key) as client:
                    messages = [{"role": "user", "content": "Hello"}]
                    response = await client.create_completion_with_retry(messages)
                    
                    assert response.text == "Success after retry"
                    mock_sleep.assert_called_once()  # Should have slept for backoff

    @pytest.mark.asyncio
    async def test_create_completion_with_retry_authentication_error_no_retry(self):
        """Test completion with retry doesn't retry on authentication error."""
        api_key = "sk-1234567890abcdef1234567890abcdef"
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            auth_response = Mock()
            auth_response.status_code = 401
            auth_response.request = Mock()
            
            mock_client.post.side_effect = httpx.HTTPStatusError(
                "Authentication failed", request=Mock(), response=auth_response
            )
            
            async with OpenAIClient(api_key) as client:
                messages = [{"role": "user", "content": "Hello"}]
                
                with pytest.raises(httpx.HTTPStatusError):
                    await client.create_completion_with_retry(messages)

    @pytest.mark.asyncio
    async def test_create_completion_with_retry_max_retries_exceeded(self):
        """Test completion with retry fails after max retries."""
        api_key = "sk-1234567890abcdef1234567890abcdef"
        config = AISummaryConfig(retry_attempts=2)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Always return server error
            server_error_response = Mock()
            server_error_response.status_code = 500
            server_error_response.request = Mock()
            
            mock_client.post.side_effect = httpx.HTTPStatusError(
                "Server error", request=Mock(), response=server_error_response
            )
            
            with patch("asyncio.sleep"):  # Mock sleep to speed up test
                async with OpenAIClient(api_key, config) as client:
                    messages = [{"role": "user", "content": "Hello"}]
                    
                    with pytest.raises(httpx.HTTPStatusError):
                        await client.create_completion_with_retry(messages)

    def test_get_token_estimate(self):
        """Test token estimation."""
        api_key = "sk-1234567890abcdef1234567890abcdef"
        client = OpenAIClient(api_key)
        
        # Test with various text lengths
        assert client.get_token_estimate("") == 0
        assert client.get_token_estimate("test") == 1  # 4 chars / 4 = 1 token
        assert client.get_token_estimate("this is a test") == 3  # 14 chars / 4 = 3.5 -> 3 tokens
        assert client.get_token_estimate("a" * 100) == 25  # 100 chars / 4 = 25 tokens

    def test_truncate_to_token_limit(self):
        """Test text truncation to token limit."""
        api_key = "sk-1234567890abcdef1234567890abcdef"
        client = OpenAIClient(api_key)
        
        # Test with text that doesn't need truncation
        short_text = "short text"
        assert client.truncate_to_token_limit(short_text, 10) == short_text
        
        # Test with text that needs truncation
        long_text = "a" * 1000
        truncated = client.truncate_to_token_limit(long_text, 10)  # 10 tokens = ~40 chars
        assert len(truncated) <= 40
        assert "[... truncated ...]" in truncated
        
        # Test with zero token limit
        assert client.truncate_to_token_limit("any text", 0) == ""

    @pytest.mark.asyncio
    async def test_validate_connection_success(self):
        """Test successful connection validation."""
        api_key = "sk-1234567890abcdef1234567890abcdef"
        
        # Mock successful response
        mock_response_data = {
            "choices": [
                {
                    "message": {"content": "Hi"},
                    "finish_reason": "stop"
                }
            ],
            "usage": {"total_tokens": 2},
            "model": "gpt-4o-mini"
        }
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.post.return_value = mock_response
            
            async with OpenAIClient(api_key) as client:
                is_valid = await client.validate_connection()
                assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self):
        """Test connection validation failure."""
        api_key = "sk-1234567890abcdef1234567890abcdef"
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock authentication error
            auth_response = Mock()
            auth_response.status_code = 401
            auth_response.request = Mock()
            
            mock_client.post.side_effect = httpx.HTTPStatusError(
                "Authentication failed", request=Mock(), response=auth_response
            )
            
            async with OpenAIClient(api_key) as client:
                is_valid = await client.validate_connection()
                assert is_valid is False


class TestOpenAIResponse:
    """Test cases for OpenAIResponse model."""

    def test_openai_response_creation(self):
        """Test OpenAIResponse creation."""
        usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        
        response = OpenAIResponse(
            text="Test response",
            usage=usage,
            model="gpt-4o-mini",
            finish_reason="stop"
        )
        
        assert response.text == "Test response"
        assert response.usage == usage
        assert response.model == "gpt-4o-mini"
        assert response.finish_reason == "stop"

    def test_openai_response_serialization(self):
        """Test OpenAIResponse serialization."""
        usage = {"total_tokens": 15}
        
        response = OpenAIResponse(
            text="Test response",
            usage=usage,
            model="gpt-4o-mini",
            finish_reason="stop"
        )
        
        data = response.model_dump()
        
        assert data["text"] == "Test response"
        assert data["usage"] == usage
        assert data["model"] == "gpt-4o-mini"
        assert data["finish_reason"] == "stop"

    def test_openai_response_deserialization(self):
        """Test OpenAIResponse deserialization."""
        data = {
            "text": "Test response",
            "usage": {"total_tokens": 15},
            "model": "gpt-4o-mini",
            "finish_reason": "stop"
        }
        
        response = OpenAIResponse(**data)
        
        assert response.text == "Test response"
        assert response.usage == {"total_tokens": 15}
        assert response.model == "gpt-4o-mini"
        assert response.finish_reason == "stop"