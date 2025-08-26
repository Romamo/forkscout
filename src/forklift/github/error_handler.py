"""Enhanced error handling for GitHub API operations."""

import asyncio
import logging
from typing import Any, Callable, TypeVar

from .exceptions import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubEmptyRepositoryError,
    GitHubForkAccessError,
    GitHubNotFoundError,
    GitHubPrivateRepositoryError,
    GitHubRateLimitError,
    GitHubTimeoutError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")





class EnhancedErrorHandler:
    """Enhanced error handler for GitHub API operations with comprehensive edge case handling."""

    def __init__(self, timeout_seconds: float = 30.0):
        """Initialize enhanced error handler.
        
        Args:
            timeout_seconds: Default timeout for operations
        """
        self.timeout_seconds = timeout_seconds

    async def handle_with_timeout(
        self,
        operation: Callable[[], T],
        operation_name: str,
        timeout_seconds: float | None = None,
    ) -> T:
        """Execute operation with timeout handling.
        
        Args:
            operation: Async operation to execute
            operation_name: Name of operation for logging
            timeout_seconds: Timeout in seconds (uses default if None)
            
        Returns:
            Result of operation
            
        Raises:
            GitHubTimeoutError: If operation times out
        """
        timeout = timeout_seconds or self.timeout_seconds
        
        try:
            return await asyncio.wait_for(operation(), timeout=timeout)
        except asyncio.TimeoutError as e:
            logger.error(f"Operation '{operation_name}' timed out after {timeout}s")
            raise GitHubTimeoutError(
                f"Operation '{operation_name}' timed out after {timeout} seconds",
                operation=operation_name,
                timeout_seconds=timeout,
            ) from e

    def handle_repository_access_error(
        self, error: GitHubAPIError, repository: str
    ) -> GitHubAPIError:
        """Handle repository access errors with specific error types.
        
        Args:
            error: Original GitHub API error
            repository: Repository identifier (owner/repo)
            
        Returns:
            More specific error type based on the original error
        """
        # Don't convert rate limit errors - they should be handled by retry logic
        if isinstance(error, GitHubRateLimitError):
            return error
        
        if isinstance(error, GitHubNotFoundError):
            # Could be private repository or truly not found
            return GitHubPrivateRepositoryError(
                f"Repository '{repository}' not found or is private",
                repository=repository,
            )
        
        if isinstance(error, GitHubAPIError):
            if error.status_code == 403:
                # Check if this is a rate limit error (some rate limits use 403)
                if hasattr(error, 'reset_time') or 'rate limit' in str(error).lower():
                    return error  # Keep as rate limit error
                # Otherwise, it's likely a private repository
                return GitHubPrivateRepositoryError(
                    f"Access denied to repository '{repository}' - repository may be private",
                    repository=repository,
                )
            elif error.status_code == 409:
                # Conflict - repository might be empty
                return GitHubEmptyRepositoryError(
                    f"Repository '{repository}' appears to be empty or has no commits",
                    repository=repository,
                )
        
        return error

    def handle_fork_access_error(
        self, error: GitHubAPIError, fork_url: str
    ) -> GitHubAPIError:
        """Handle fork access errors with specific error types.
        
        Args:
            error: Original GitHub API error
            fork_url: Fork URL or identifier
            
        Returns:
            More specific error type based on the original error
        """
        if isinstance(error, GitHubNotFoundError):
            return GitHubForkAccessError(
                f"Fork '{fork_url}' not found - may be deleted or private",
                fork_url=fork_url,
                reason="not_found",
            )
        
        if isinstance(error, GitHubAPIError):
            if error.status_code == 403:
                return GitHubForkAccessError(
                    f"Access denied to fork '{fork_url}' - fork may be private",
                    fork_url=fork_url,
                    reason="private",
                )
        
        return error

    def handle_commit_access_error(
        self, error: GitHubAPIError, repository: str, commit_sha: str | None = None
    ) -> GitHubAPIError:
        """Handle commit access errors.
        
        Args:
            error: Original GitHub API error
            repository: Repository identifier
            commit_sha: Optional commit SHA
            
        Returns:
            More specific error type based on the original error
        """
        if isinstance(error, GitHubAPIError):
            if error.status_code == 409:
                # Repository is empty (no commits)
                return GitHubEmptyRepositoryError(
                    f"Repository '{repository}' has no commits",
                    repository=repository,
                )
            elif error.status_code == 403:
                # Private repository or access denied
                return GitHubPrivateRepositoryError(
                    f"Cannot access commits in repository '{repository}' - may be private",
                    repository=repository,
                )
        
        return error

    async def safe_repository_operation(
        self,
        operation: Callable[[], T],
        repository: str,
        operation_name: str,
        default_value: T | None = None,
        timeout_seconds: float | None = None,
    ) -> T | None:
        """Safely execute repository operation with comprehensive error handling.
        
        Args:
            operation: Async operation to execute
            repository: Repository identifier for error context
            operation_name: Name of operation for logging
            default_value: Value to return on error (None if not specified)
            timeout_seconds: Timeout in seconds
            
        Returns:
            Result of operation or default_value on error
        """
        try:
            return await self.handle_with_timeout(
                operation, operation_name, timeout_seconds
            )
        except GitHubTimeoutError:
            logger.warning(f"Timeout in {operation_name} for repository '{repository}'")
            return default_value
        except (GitHubPrivateRepositoryError, GitHubEmptyRepositoryError) as e:
            logger.warning(f"Repository access issue in {operation_name}: {e}")
            return default_value
        except GitHubRateLimitError as e:
            logger.warning(f"Rate limit hit in {operation_name} for repository '{repository}': {e}")
            # Re-raise rate limit errors so they can be handled by retry logic
            raise
        except GitHubAPIError as e:
            # Convert to more specific error type if possible
            specific_error = self.handle_repository_access_error(e, repository)
            if isinstance(specific_error, (GitHubPrivateRepositoryError, GitHubEmptyRepositoryError)):
                logger.warning(f"Repository access issue in {operation_name}: {specific_error}")
                return default_value
            else:
                logger.error(f"API error in {operation_name} for repository '{repository}': {e}")
                return default_value
        except Exception as e:
            logger.error(f"Unexpected error in {operation_name} for repository '{repository}': {e}")
            return default_value

    async def safe_fork_operation(
        self,
        operation: Callable[[], T],
        fork_url: str,
        operation_name: str,
        default_value: T | None = None,
        timeout_seconds: float | None = None,
    ) -> T | None:
        """Safely execute fork operation with comprehensive error handling.
        
        Args:
            operation: Async operation to execute
            fork_url: Fork URL for error context
            operation_name: Name of operation for logging
            default_value: Value to return on error (None if not specified)
            timeout_seconds: Timeout in seconds
            
        Returns:
            Result of operation or default_value on error
        """
        try:
            return await self.handle_with_timeout(
                operation, operation_name, timeout_seconds
            )
        except GitHubTimeoutError:
            logger.warning(f"Timeout in {operation_name} for fork '{fork_url}'")
            return default_value
        except GitHubForkAccessError as e:
            logger.warning(f"Fork access issue in {operation_name}: {e}")
            return default_value
        except GitHubRateLimitError as e:
            logger.warning(f"Rate limit hit in {operation_name} for fork '{fork_url}': {e}")
            # Re-raise rate limit errors so they can be handled by retry logic
            raise
        except GitHubAPIError as e:
            # Convert to more specific error type if possible
            specific_error = self.handle_fork_access_error(e, fork_url)
            if isinstance(specific_error, GitHubForkAccessError):
                logger.warning(f"Fork access issue in {operation_name}: {specific_error}")
                return default_value
            else:
                logger.error(f"API error in {operation_name} for fork '{fork_url}': {e}")
                return default_value
        except Exception as e:
            logger.error(f"Unexpected error in {operation_name} for fork '{fork_url}': {e}")
            return default_value

    def get_user_friendly_error_message(self, error: Exception) -> str:
        """Get user-friendly error message for display.
        
        Args:
            error: Exception to convert to user-friendly message
            
        Returns:
            User-friendly error message
        """
        if isinstance(error, GitHubTimeoutError):
            return f"Operation timed out after {error.timeout_seconds} seconds. The repository may be very large or GitHub API is slow."
        
        elif isinstance(error, GitHubPrivateRepositoryError):
            return f"Cannot access repository '{error.repository}' - it may be private or you may not have permission."
        
        elif isinstance(error, GitHubEmptyRepositoryError):
            return f"Repository '{error.repository}' appears to be empty or has no commits."
        
        elif isinstance(error, GitHubForkAccessError):
            if error.reason == "private":
                return f"Cannot access fork '{error.fork_url}' - it may be private."
            elif error.reason == "not_found":
                return f"Fork '{error.fork_url}' not found - it may have been deleted."
            else:
                return f"Cannot access fork '{error.fork_url}'."
        
        elif isinstance(error, GitHubRateLimitError):
            if error.reset_time:
                import time
                wait_time = max(0, error.reset_time - time.time())
                return f"GitHub API rate limit exceeded. Please wait {wait_time:.0f} seconds before retrying."
            else:
                return "GitHub API rate limit exceeded. Please wait before retrying."
        
        elif isinstance(error, GitHubAuthenticationError):
            return "GitHub authentication failed. Please check your API token."
        
        elif isinstance(error, GitHubNotFoundError):
            return "GitHub resource not found. Please check the repository URL."
        
        elif isinstance(error, GitHubAPIError):
            if error.status_code:
                return f"GitHub API error ({error.status_code}): {error}"
            else:
                return f"GitHub API error: {error}"
        
        else:
            return f"Unexpected error: {error}"

    def should_continue_processing(self, error: Exception) -> bool:
        """Determine if processing should continue after an error.
        
        Args:
            error: Exception that occurred
            
        Returns:
            True if processing should continue, False if it should stop
        """
        # Continue processing for these recoverable errors
        if isinstance(error, (
            GitHubPrivateRepositoryError,
            GitHubEmptyRepositoryError,
            GitHubForkAccessError,
            GitHubTimeoutError,
        )):
            return True
        
        # Stop processing for authentication errors
        if isinstance(error, GitHubAuthenticationError):
            return False
        
        # For rate limit errors, let the retry logic handle it
        if isinstance(error, GitHubRateLimitError):
            return True
        
        # For other API errors, continue but log the issue
        if isinstance(error, GitHubAPIError):
            return True
        
        # For unexpected errors, stop processing
        return False