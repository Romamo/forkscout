"""Error handling for OpenAI API operations."""

import logging
from typing import Optional

import httpx

from forklift.models.ai_summary import AIError, AIErrorType

logger = logging.getLogger(__name__)


class OpenAIErrorHandler:
    """Handles different types of OpenAI API errors."""

    def __init__(self, max_retries: int = 3):
        """Initialize error handler.

        Args:
            max_retries: Maximum number of retry attempts
        """
        self.max_retries = max_retries

    def classify_error(self, error: Exception) -> AIErrorType:
        """Classify an error into an AIErrorType.

        Args:
            error: Exception to classify

        Returns:
            AIErrorType classification
        """
        if isinstance(error, httpx.HTTPStatusError):
            status_code = error.response.status_code
            
            if status_code == 401:
                return AIErrorType.AUTHENTICATION
            elif status_code == 429:
                return AIErrorType.RATE_LIMIT
            elif 400 <= status_code < 500:
                return AIErrorType.INVALID_REQUEST
            elif 500 <= status_code < 600:
                return AIErrorType.MODEL_ERROR
            else:
                return AIErrorType.UNKNOWN
                
        elif isinstance(error, httpx.TimeoutException):
            return AIErrorType.TIMEOUT
        elif isinstance(error, (httpx.RequestError, httpx.ConnectError)):
            return AIErrorType.NETWORK_ERROR
        elif isinstance(error, ValueError):
            return AIErrorType.INVALID_REQUEST
        else:
            return AIErrorType.UNKNOWN

    def is_retryable(self, error: Exception) -> bool:
        """Determine if an error is retryable.

        Args:
            error: Exception to check

        Returns:
            True if the error is retryable, False otherwise
        """
        error_type = self.classify_error(error)
        
        # Retryable errors
        retryable_types = {
            AIErrorType.RATE_LIMIT,
            AIErrorType.TIMEOUT,
            AIErrorType.NETWORK_ERROR,
            AIErrorType.MODEL_ERROR,  # Server errors (5xx)
        }
        
        return error_type in retryable_types

    def get_retry_delay(self, attempt: int, error: Exception) -> float:
        """Calculate retry delay based on attempt number and error type.

        Args:
            attempt: Current attempt number (0-based)
            error: Exception that occurred

        Returns:
            Delay in seconds before next retry
        """
        error_type = self.classify_error(error)
        
        if error_type == AIErrorType.RATE_LIMIT:
            # For rate limits, try to extract retry-after header
            if isinstance(error, httpx.HTTPStatusError):
                retry_after = error.response.headers.get("retry-after")
                if retry_after:
                    try:
                        return min(float(retry_after), 300)  # Cap at 5 minutes
                    except ValueError:
                        pass
            
            # Default rate limit backoff
            return min(60 * (2 ** attempt), 300)  # Exponential backoff, cap at 5 minutes
        
        elif error_type in {AIErrorType.TIMEOUT, AIErrorType.NETWORK_ERROR, AIErrorType.MODEL_ERROR}:
            # Exponential backoff for network and server errors
            return min(2 ** attempt, 60)  # Cap at 1 minute
        
        else:
            # Default backoff for other retryable errors
            return min(1 * (2 ** attempt), 30)  # Cap at 30 seconds

    def create_ai_error(
        self,
        error: Exception,
        commit_sha: Optional[str] = None,
        retry_count: int = 0
    ) -> AIError:
        """Create an AIError from an exception.

        Args:
            error: Exception that occurred
            commit_sha: SHA of commit being processed (optional)
            retry_count: Number of retries attempted

        Returns:
            AIError object with error details
        """
        error_type = self.classify_error(error)
        
        # Extract meaningful error message
        if isinstance(error, httpx.HTTPStatusError):
            message = f"HTTP {error.response.status_code}: {error.response.text}"
        else:
            message = str(error)
        
        return AIError(
            error_type=error_type,
            message=message,
            commit_sha=commit_sha,
            retry_count=retry_count,
            recoverable=self.is_retryable(error)
        )

    def log_error(
        self,
        error: Exception,
        commit_sha: Optional[str] = None,
        retry_count: int = 0,
        context: Optional[str] = None
    ) -> None:
        """Log an error with appropriate level and context.

        Args:
            error: Exception that occurred
            commit_sha: SHA of commit being processed (optional)
            retry_count: Number of retries attempted
            context: Additional context information (optional)
        """
        error_type = self.classify_error(error)
        
        # Build log message
        parts = []
        if context:
            parts.append(f"[{context}]")
        if commit_sha:
            parts.append(f"commit {commit_sha[:8]}")
        
        prefix = " ".join(parts)
        if prefix:
            prefix += ": "
        
        message = f"{prefix}OpenAI API error ({error_type})"
        
        if retry_count > 0:
            message += f" (retry {retry_count})"
        
        message += f": {error}"
        
        # Log at appropriate level
        if error_type == AIErrorType.AUTHENTICATION:
            logger.error(message)
        elif error_type == AIErrorType.RATE_LIMIT:
            logger.warning(message)
        elif error_type in {AIErrorType.TIMEOUT, AIErrorType.NETWORK_ERROR}:
            if retry_count == 0:
                logger.warning(message)
            else:
                logger.debug(message)  # Don't spam logs with retry attempts
        elif error_type == AIErrorType.INVALID_REQUEST:
            logger.error(message)
        elif error_type == AIErrorType.MODEL_ERROR:
            logger.error(message)
        else:
            logger.error(message)

    def should_abort(self, error: Exception, retry_count: int) -> bool:
        """Determine if processing should be aborted for this error.

        Args:
            error: Exception that occurred
            retry_count: Number of retries attempted

        Returns:
            True if processing should be aborted, False to continue
        """
        error_type = self.classify_error(error)
        
        # Always abort on authentication errors
        if error_type == AIErrorType.AUTHENTICATION:
            return True
        
        # Abort on non-retryable errors
        if not self.is_retryable(error):
            return True
        
        # Abort if max retries exceeded
        if retry_count >= self.max_retries:
            return True
        
        return False

    def get_user_friendly_message(self, error: Exception) -> str:
        """Get a user-friendly error message.

        Args:
            error: Exception that occurred

        Returns:
            User-friendly error message
        """
        error_type = self.classify_error(error)
        
        if error_type == AIErrorType.AUTHENTICATION:
            return "Invalid OpenAI API key. Please check your OPENAI_API_KEY environment variable."
        elif error_type == AIErrorType.RATE_LIMIT:
            return "OpenAI API rate limit exceeded. Please wait and try again later."
        elif error_type == AIErrorType.TIMEOUT:
            return "OpenAI API request timed out. Please try again."
        elif error_type == AIErrorType.NETWORK_ERROR:
            return "Network error connecting to OpenAI API. Please check your internet connection."
        elif error_type == AIErrorType.INVALID_REQUEST:
            return "Invalid request to OpenAI API. Please check your input."
        elif error_type == AIErrorType.MODEL_ERROR:
            return "OpenAI API server error. Please try again later."
        else:
            return f"Unexpected error: {error}"