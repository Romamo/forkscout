"""OpenAI client wrapper with error handling and rate limiting."""

import asyncio
import logging
import time
from typing import Any

import httpx
from pydantic import BaseModel

from forkscout.models.ai_summary import AISummaryConfig

logger = logging.getLogger(__name__)


class OpenAIResponse(BaseModel):
    """Response from OpenAI API."""

    text: str
    usage: dict[str, Any]
    model: str
    finish_reason: str


class OpenAIClient:
    """Async HTTP client wrapper for OpenAI GPT-4 mini API calls."""

    def __init__(
        self,
        api_key: str,
        config: AISummaryConfig | None = None,
        base_url: str = "https://api.openai.com/v1"
    ):
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            config: AI summary configuration (optional)
            base_url: OpenAI API base URL
        """
        self.api_key = api_key
        self.config = config or AISummaryConfig()
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None
        self._validate_api_key()

    def _validate_api_key(self) -> None:
        """Validate API key format."""
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        if not self.api_key.startswith("sk-"):
            raise ValueError("Invalid OpenAI API key format")

        if len(self.api_key) < 20:
            raise ValueError("OpenAI API key is too short")

    async def __aenter__(self) -> "OpenAIClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout_seconds),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def create_chat_completion(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        model: str | None = None
    ) -> OpenAIResponse:
        """Create a chat completion using OpenAI API.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_tokens: Maximum tokens to generate (uses config default if None)
            temperature: Sampling temperature (uses config default if None)
            model: Model to use (uses config default if None)

        Returns:
            OpenAIResponse with generated text and usage information

        Raises:
            ValueError: If client is not initialized or parameters are invalid
            httpx.HTTPError: If API request fails
        """
        if not self._client:
            raise ValueError("Client not initialized. Use async context manager.")

        # Use config defaults if not specified
        max_tokens = max_tokens if max_tokens is not None else self.config.max_tokens
        temperature = temperature if temperature is not None else self.config.temperature
        model = model or self.config.model

        # Validate parameters
        if not messages:
            raise ValueError("Messages list cannot be empty")

        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")

        if not (0.0 <= temperature <= 2.0):
            raise ValueError("temperature must be between 0.0 and 2.0")

        # Prepare request payload
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        logger.debug(f"Making OpenAI API request with model {model}")
        start_time = time.time()

        try:
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )

            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            logger.debug(f"OpenAI API request completed in {processing_time:.2f}ms")

            # Handle HTTP errors
            if response.status_code == 401:
                raise httpx.HTTPStatusError(
                    "Authentication failed - invalid API key",
                    request=response.request,
                    response=response
                )
            elif response.status_code == 429:
                retry_after = response.headers.get("retry-after", "60")
                raise httpx.HTTPStatusError(
                    f"Rate limit exceeded - retry after {retry_after} seconds",
                    request=response.request,
                    response=response
                )
            elif response.status_code >= 400:
                error_detail = response.text
                raise httpx.HTTPStatusError(
                    f"OpenAI API error: {error_detail}",
                    request=response.request,
                    response=response
                )

            response.raise_for_status()

            # Parse response
            response_data = response.json()

            if "choices" not in response_data or not response_data["choices"]:
                raise ValueError("Invalid response format from OpenAI API")

            choice = response_data["choices"][0]

            return OpenAIResponse(
                text=choice["message"]["content"],
                usage=response_data.get("usage", {}),
                model=response_data.get("model", model),
                finish_reason=choice.get("finish_reason", "unknown")
            )

        except httpx.TimeoutException as e:
            logger.error(f"OpenAI API request timeout: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API HTTP error: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"OpenAI API request error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI API request: {e}")
            raise

    async def create_completion_with_retry(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        model: str | None = None,
        max_retries: int | None = None
    ) -> OpenAIResponse:
        """Create completion with automatic retry logic.

        Args:
            messages: List of message dictionaries
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            model: Model to use
            max_retries: Maximum retry attempts (uses config default if None)

        Returns:
            OpenAIResponse with generated text and usage information

        Raises:
            Exception: If all retry attempts fail
        """
        max_retries = max_retries or self.config.retry_attempts
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return await self.create_chat_completion(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    model=model
                )
            except httpx.HTTPStatusError as e:
                last_exception = e

                # Don't retry on authentication errors
                if e.response.status_code == 401:
                    logger.error("Authentication failed - not retrying")
                    raise

                # Handle rate limiting with exponential backoff
                if e.response.status_code == 429:
                    if attempt < max_retries:
                        retry_after = int(e.response.headers.get("retry-after", "60"))
                        backoff_delay = min(retry_after, 2 ** attempt)
                        logger.warning(
                            f"Rate limited, retrying in {backoff_delay}s (attempt {attempt + 1}/{max_retries + 1})"
                        )
                        await asyncio.sleep(backoff_delay)
                        continue
                    else:
                        logger.error("Rate limit exceeded - max retries reached")
                        raise

                # Retry on server errors (5xx)
                if 500 <= e.response.status_code < 600:
                    if attempt < max_retries:
                        backoff_delay = 2 ** attempt
                        logger.warning(
                            f"Server error {e.response.status_code}, retrying in {backoff_delay}s "
                            f"(attempt {attempt + 1}/{max_retries + 1})"
                        )
                        await asyncio.sleep(backoff_delay)
                        continue
                    else:
                        logger.error("Server error - max retries reached")
                        raise

                # Don't retry on client errors (4xx except 429)
                logger.error(f"Client error {e.response.status_code} - not retrying")
                raise

            except (httpx.TimeoutException, httpx.RequestError) as e:
                last_exception = e

                if attempt < max_retries:
                    backoff_delay = 2 ** attempt
                    logger.warning(
                        f"Network error, retrying in {backoff_delay}s "
                        f"(attempt {attempt + 1}/{max_retries + 1}): {e}"
                    )
                    await asyncio.sleep(backoff_delay)
                    continue
                else:
                    logger.error("Network error - max retries reached")
                    raise

            except Exception as e:
                # Don't retry on unexpected errors
                logger.error(f"Unexpected error - not retrying: {e}")
                raise

        # This should never be reached, but just in case
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError("All retry attempts failed")

    def get_token_estimate(self, text: str) -> int:
        """Estimate token count for text.

        This is a rough approximation. For accurate counts, use the tiktoken library.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        # Rough approximation: 1 token ≈ 4 characters for English text
        return len(text) // 4

    def truncate_to_token_limit(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token limit.

        Args:
            text: Text to truncate
            max_tokens: Maximum tokens allowed

        Returns:
            Truncated text
        """
        if max_tokens <= 0:
            return ""

        estimated_tokens = self.get_token_estimate(text)

        if estimated_tokens <= max_tokens:
            return text

        # Calculate approximate character limit
        char_limit = max_tokens * 4

        if len(text) <= char_limit:
            return text

        # Truncate and add indicator
        truncated = text[:char_limit - 20]  # Leave room for truncation indicator
        return truncated + "\n[... truncated ...]"

    async def validate_connection(self) -> bool:
        """Validate API connection and authentication.

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Make a minimal API call to test connection
            test_messages = [
                {"role": "user", "content": "Hello"}
            ]

            await self.create_chat_completion(
                messages=test_messages,
                max_tokens=1,
                temperature=0.0
            )

            logger.info("OpenAI API connection validated successfully")
            return True

        except Exception as e:
            logger.error(f"OpenAI API connection validation failed: {e}")
            return False
