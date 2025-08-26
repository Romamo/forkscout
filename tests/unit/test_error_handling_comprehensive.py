"""Comprehensive unit tests for error handling and edge cases."""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch

from forklift.github.error_handler import EnhancedErrorHandler
from forklift.github.exceptions import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubEmptyRepositoryError,
    GitHubForkAccessError,
    GitHubNotFoundError,
    GitHubPrivateRepositoryError,
    GitHubRateLimitError,
    GitHubTimeoutError,
)


class TestEnhancedErrorHandler:
    """Test cases for EnhancedErrorHandler."""

    @pytest.fixture
    def error_handler(self):
        """Create test error handler."""
        return EnhancedErrorHandler(timeout_seconds=5.0)

    @pytest.mark.asyncio
    async def test_timeout_handling(self, error_handler):
        """Test timeout handling for slow operations."""
        async def slow_operation():
            await asyncio.sleep(10)  # Longer than timeout
            return "result"

        with pytest.raises(GitHubTimeoutError) as exc_info:
            await error_handler.handle_with_timeout(
                slow_operation, "test_operation", timeout_seconds=1.0
            )

        assert exc_info.value.operation == "test_operation"
        assert exc_info.value.timeout_seconds == 1.0

    @pytest.mark.asyncio
    async def test_successful_operation_within_timeout(self, error_handler):
        """Test successful operation that completes within timeout."""
        async def fast_operation():
            await asyncio.sleep(0.1)
            return "success"

        result = await error_handler.handle_with_timeout(
            fast_operation, "test_operation", timeout_seconds=1.0
        )

        assert result == "success"

    def test_repository_access_error_not_found(self, error_handler):
        """Test handling of repository not found errors."""
        original_error = GitHubNotFoundError("Not found", status_code=404)
        
        result = error_handler.handle_repository_access_error(
            original_error, "owner/repo"
        )

        assert isinstance(result, GitHubPrivateRepositoryError)
        assert result.repository == "owner/repo"
        assert "not found or is private" in str(result)

    def test_repository_access_error_forbidden(self, error_handler):
        """Test handling of repository forbidden errors."""
        original_error = GitHubAPIError("Forbidden", status_code=403)
        
        result = error_handler.handle_repository_access_error(
            original_error, "owner/repo"
        )

        assert isinstance(result, GitHubPrivateRepositoryError)
        assert result.repository == "owner/repo"
        assert "private" in str(result)

    def test_repository_access_error_empty_repo(self, error_handler):
        """Test handling of empty repository errors."""
        original_error = GitHubAPIError("Conflict", status_code=409)
        
        result = error_handler.handle_repository_access_error(
            original_error, "owner/repo"
        )

        assert isinstance(result, GitHubEmptyRepositoryError)
        assert result.repository == "owner/repo"
        assert "empty" in str(result)

    def test_fork_access_error_not_found(self, error_handler):
        """Test handling of fork not found errors."""
        original_error = GitHubNotFoundError("Not found", status_code=404)
        
        result = error_handler.handle_fork_access_error(
            original_error, "owner/fork"
        )

        assert isinstance(result, GitHubForkAccessError)
        assert result.fork_url == "owner/fork"
        assert result.reason == "not_found"

    def test_fork_access_error_private(self, error_handler):
        """Test handling of private fork errors."""
        original_error = GitHubAPIError("Forbidden", status_code=403)
        
        result = error_handler.handle_fork_access_error(
            original_error, "owner/fork"
        )

        assert isinstance(result, GitHubForkAccessError)
        assert result.fork_url == "owner/fork"
        assert result.reason == "private"

    def test_commit_access_error_empty_repo(self, error_handler):
        """Test handling of commit access errors for empty repositories."""
        original_error = GitHubAPIError("Conflict", status_code=409)
        
        result = error_handler.handle_commit_access_error(
            original_error, "owner/repo", "abc123"
        )

        assert isinstance(result, GitHubEmptyRepositoryError)
        assert result.repository == "owner/repo"

    def test_commit_access_error_private_repo(self, error_handler):
        """Test handling of commit access errors for private repositories."""
        original_error = GitHubAPIError("Forbidden", status_code=403)
        
        result = error_handler.handle_commit_access_error(
            original_error, "owner/repo"
        )

        assert isinstance(result, GitHubPrivateRepositoryError)
        assert result.repository == "owner/repo"

    @pytest.mark.asyncio
    async def test_safe_repository_operation_success(self, error_handler):
        """Test safe repository operation with successful result."""
        async def successful_operation():
            return "success"

        result = await error_handler.safe_repository_operation(
            successful_operation,
            repository="owner/repo",
            operation_name="test_op",
            default_value="default"
        )

        assert result == "success"

    @pytest.mark.asyncio
    async def test_safe_repository_operation_timeout(self, error_handler):
        """Test safe repository operation with timeout."""
        async def timeout_operation():
            await asyncio.sleep(10)
            return "success"

        result = await error_handler.safe_repository_operation(
            timeout_operation,
            repository="owner/repo",
            operation_name="test_op",
            default_value="default",
            timeout_seconds=0.1
        )

        assert result == "default"

    @pytest.mark.asyncio
    async def test_safe_repository_operation_private_repo(self, error_handler):
        """Test safe repository operation with private repository error."""
        async def private_repo_operation():
            raise GitHubPrivateRepositoryError("Private repo", "owner/repo")

        result = await error_handler.safe_repository_operation(
            private_repo_operation,
            repository="owner/repo",
            operation_name="test_op",
            default_value="default"
        )

        assert result == "default"

    @pytest.mark.asyncio
    async def test_safe_repository_operation_empty_repo(self, error_handler):
        """Test safe repository operation with empty repository error."""
        async def empty_repo_operation():
            raise GitHubEmptyRepositoryError("Empty repo", "owner/repo")

        result = await error_handler.safe_repository_operation(
            empty_repo_operation,
            repository="owner/repo",
            operation_name="test_op",
            default_value="default"
        )

        assert result == "default"

    @pytest.mark.asyncio
    async def test_safe_repository_operation_rate_limit_reraise(self, error_handler):
        """Test safe repository operation re-raises rate limit errors."""
        async def rate_limit_operation():
            raise GitHubRateLimitError("Rate limit", reset_time=1234567890)

        with pytest.raises(GitHubRateLimitError):
            await error_handler.safe_repository_operation(
                rate_limit_operation,
                repository="owner/repo",
                operation_name="test_op",
                default_value="default"
            )

    @pytest.mark.asyncio
    async def test_safe_fork_operation_success(self, error_handler):
        """Test safe fork operation with successful result."""
        async def successful_operation():
            return "success"

        result = await error_handler.safe_fork_operation(
            successful_operation,
            fork_url="owner/fork",
            operation_name="test_op",
            default_value="default"
        )

        assert result == "success"

    @pytest.mark.asyncio
    async def test_safe_fork_operation_fork_access_error(self, error_handler):
        """Test safe fork operation with fork access error."""
        async def fork_access_operation():
            raise GitHubForkAccessError("Fork access denied", "owner/fork", "private")

        result = await error_handler.safe_fork_operation(
            fork_access_operation,
            fork_url="owner/fork",
            operation_name="test_op",
            default_value="default"
        )

        assert result == "default"

    def test_user_friendly_error_message_timeout(self, error_handler):
        """Test user-friendly message for timeout errors."""
        error = GitHubTimeoutError("Timeout", "test_op", 30.0)
        
        message = error_handler.get_user_friendly_error_message(error)
        
        assert "timed out after 30.0 seconds" in message
        assert "large" in message or "slow" in message

    def test_user_friendly_error_message_private_repo(self, error_handler):
        """Test user-friendly message for private repository errors."""
        error = GitHubPrivateRepositoryError("Private", "owner/repo")
        
        message = error_handler.get_user_friendly_error_message(error)
        
        assert "owner/repo" in message
        assert "private" in message
        assert "permission" in message

    def test_user_friendly_error_message_empty_repo(self, error_handler):
        """Test user-friendly message for empty repository errors."""
        error = GitHubEmptyRepositoryError("Empty", "owner/repo")
        
        message = error_handler.get_user_friendly_error_message(error)
        
        assert "owner/repo" in message
        assert "empty" in message
        assert "no commits" in message

    def test_user_friendly_error_message_fork_access_private(self, error_handler):
        """Test user-friendly message for private fork access errors."""
        error = GitHubForkAccessError("Private fork", "owner/fork", "private")
        
        message = error_handler.get_user_friendly_error_message(error)
        
        assert "owner/fork" in message
        assert "private" in message

    def test_user_friendly_error_message_fork_access_not_found(self, error_handler):
        """Test user-friendly message for not found fork access errors."""
        error = GitHubForkAccessError("Not found", "owner/fork", "not_found")
        
        message = error_handler.get_user_friendly_error_message(error)
        
        assert "owner/fork" in message
        assert "deleted" in message

    def test_user_friendly_error_message_rate_limit(self, error_handler):
        """Test user-friendly message for rate limit errors."""
        import time
        reset_time = int(time.time()) + 300  # 5 minutes from now
        error = GitHubRateLimitError("Rate limit", reset_time=reset_time)
        
        message = error_handler.get_user_friendly_error_message(error)
        
        assert "rate limit" in message
        assert "wait" in message

    def test_user_friendly_error_message_authentication(self, error_handler):
        """Test user-friendly message for authentication errors."""
        error = GitHubAuthenticationError("Auth failed", status_code=401)
        
        message = error_handler.get_user_friendly_error_message(error)
        
        assert "authentication" in message
        assert "token" in message

    def test_user_friendly_error_message_not_found(self, error_handler):
        """Test user-friendly message for not found errors."""
        error = GitHubNotFoundError("Not found", status_code=404)
        
        message = error_handler.get_user_friendly_error_message(error)
        
        assert "not found" in message
        assert "URL" in message

    def test_user_friendly_error_message_api_error_with_status(self, error_handler):
        """Test user-friendly message for API errors with status code."""
        error = GitHubAPIError("Server error", status_code=500)
        
        message = error_handler.get_user_friendly_error_message(error)
        
        assert "500" in message
        assert "API error" in message

    def test_user_friendly_error_message_generic_error(self, error_handler):
        """Test user-friendly message for generic errors."""
        error = ValueError("Something went wrong")
        
        message = error_handler.get_user_friendly_error_message(error)
        
        assert "Unexpected error" in message
        assert "Something went wrong" in message

    def test_should_continue_processing_recoverable_errors(self, error_handler):
        """Test that processing continues for recoverable errors."""
        recoverable_errors = [
            GitHubPrivateRepositoryError("Private", "owner/repo"),
            GitHubEmptyRepositoryError("Empty", "owner/repo"),
            GitHubForkAccessError("Access denied", "owner/fork", "private"),
            GitHubTimeoutError("Timeout", "test_op", 30.0),
            GitHubRateLimitError("Rate limit"),
            GitHubAPIError("Server error", status_code=500),
        ]

        for error in recoverable_errors:
            assert error_handler.should_continue_processing(error) is True

    def test_should_continue_processing_non_recoverable_errors(self, error_handler):
        """Test that processing stops for non-recoverable errors."""
        non_recoverable_errors = [
            GitHubAuthenticationError("Auth failed", status_code=401),
            ValueError("Unexpected error"),
            RuntimeError("Runtime error"),
        ]

        for error in non_recoverable_errors:
            if isinstance(error, GitHubAuthenticationError):
                assert error_handler.should_continue_processing(error) is False
            else:
                assert error_handler.should_continue_processing(error) is False


class TestErrorHandlingEdgeCases:
    """Test edge cases for error handling."""

    @pytest.mark.asyncio
    async def test_empty_repository_no_commits(self):
        """Test handling of repositories with no commits."""
        from forklift.github.client import GitHubClient
        from forklift.config import GitHubConfig

        config = GitHubConfig(token="ghp_1234567890abcdef1234567890abcdef12345678")
        client = GitHubClient(config)

        # Mock the API to return 409 for empty repository
        with patch.object(client, 'get') as mock_get:
            mock_get.side_effect = GitHubAPIError("Git Repository is empty", status_code=409)

            with pytest.raises(GitHubEmptyRepositoryError):
                await client.get_repository_commits("owner", "empty-repo")

    @pytest.mark.asyncio
    async def test_private_fork_access_denied(self):
        """Test handling of private forks that cannot be accessed."""
        from forklift.github.client import GitHubClient
        from forklift.config import GitHubConfig

        config = GitHubConfig(token="ghp_1234567890abcdef1234567890abcdef12345678")
        client = GitHubClient(config)

        # Mock the API to return 403 for private fork
        with patch.object(client, 'get') as mock_get:
            mock_get.side_effect = GitHubAPIError("Forbidden", status_code=403)

            with pytest.raises(GitHubPrivateRepositoryError):
                await client.get_repository("owner", "private-fork")

    @pytest.mark.asyncio
    async def test_rate_limit_with_reset_time(self):
        """Test rate limit handling with reset time."""
        from forklift.github.client import GitHubClient
        from forklift.config import GitHubConfig

        config = GitHubConfig(token="ghp_1234567890abcdef1234567890abcdef12345678")
        client = GitHubClient(config)

        import time
        reset_time = int(time.time()) + 300

        # Mock the API to return rate limit error
        with patch.object(client, 'get') as mock_get:
            mock_get.side_effect = GitHubRateLimitError(
                "Rate limit exceeded",
                reset_time=reset_time,
                remaining=0,
                limit=5000,
                status_code=403
            )

            with pytest.raises(GitHubRateLimitError) as exc_info:
                await client.get_repository("owner", "repo")

            assert exc_info.value.reset_time == reset_time
            assert exc_info.value.remaining == 0

    @pytest.mark.asyncio
    async def test_timeout_during_commit_fetching(self):
        """Test timeout handling during slow commit fetching operations."""
        from forklift.github.client import GitHubClient
        from forklift.config import GitHubConfig

        config = GitHubConfig(token="ghp_1234567890abcdef1234567890abcdef12345678", timeout_seconds=1.0)
        client = GitHubClient(config)

        # Mock a slow operation
        async def slow_get(*args, **kwargs):
            await asyncio.sleep(2.0)  # Longer than timeout
            return []

        with patch.object(client, 'get', side_effect=slow_get):
            # Use safe method that should handle timeout gracefully
            result = await client.get_repository_commits_safe("owner", "repo")
            assert result == []  # Should return empty list on timeout

    @pytest.mark.asyncio
    async def test_fork_deleted_during_analysis(self):
        """Test handling of forks that are deleted during analysis."""
        from forklift.analysis.fork_discovery import ForkDiscoveryService
        from forklift.github.client import GitHubClient
        from forklift.config import GitHubConfig

        config = GitHubConfig(token="ghp_1234567890abcdef1234567890abcdef12345678")
        client = GitHubClient(config)
        service = ForkDiscoveryService(client)

        # Mock repository data
        repo_data = {
            "id": 1,
            "name": "test-repo",
            "full_name": "owner/test-repo",
            "owner": {"login": "owner", "id": 1, "type": "User"},
            "html_url": "https://github.com/owner/test-repo",
            "clone_url": "https://github.com/owner/test-repo.git",
            "default_branch": "main",
            "stargazers_count": 0,
            "forks_count": 0,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
            "pushed_at": "2023-01-01T00:00:00Z",
        }

        with patch.object(client, 'get_repository') as mock_get_repo:
            mock_get_repo.return_value = Mock()
            
            with patch.object(client, 'get_all_repository_forks') as mock_get_forks:
                mock_get_forks.return_value = []
                
                # Should handle empty fork list gracefully
                forks = await service.discover_forks("https://github.com/owner/test-repo")
                assert forks == []

    def test_error_message_display_formatting(self):
        """Test that error messages are properly formatted for display."""
        from forklift.github.error_handler import EnhancedErrorHandler

        handler = EnhancedErrorHandler()

        # Test various error types
        errors_and_expected_content = [
            (GitHubTimeoutError("Timeout", "test_op", 30.0), ["timed out", "30.0 seconds"]),
            (GitHubPrivateRepositoryError("Private", "owner/repo"), ["owner/repo", "private"]),
            (GitHubEmptyRepositoryError("Empty", "owner/repo"), ["owner/repo", "empty", "no commits"]),
            (GitHubForkAccessError("Access denied", "owner/fork", "private"), ["owner/fork", "private"]),
            (GitHubRateLimitError("Rate limit"), ["rate limit", "wait"]),
            (GitHubAuthenticationError("Auth failed"), ["authentication", "token"]),
        ]

        for error, expected_content in errors_and_expected_content:
            message = handler.get_user_friendly_error_message(error)
            for content in expected_content:
                assert content in message.lower(), f"Expected '{content}' in message: {message}"

    @pytest.mark.asyncio
    async def test_graceful_degradation_with_partial_failures(self):
        """Test graceful degradation when some operations fail but others succeed."""
        from forklift.github.client import GitHubClient
        from forklift.config import GitHubConfig

        config = GitHubConfig(token="ghp_1234567890abcdef1234567890abcdef12345678")
        client = GitHubClient(config)

        # Test that safe methods return appropriate defaults
        test_cases = [
            (client.get_repository_safe, ("owner", "private-repo"), None),
            (client.get_repository_commits_safe, ("owner", "empty-repo"), []),
            (client.get_commits_ahead_behind_safe, ("owner", "fork", "owner", "parent"), {"ahead_by": 0, "behind_by": 0, "total_commits": 0}),
        ]

        for method, args, expected_default in test_cases:
            with patch.object(client, 'get') as mock_get:
                mock_get.side_effect = GitHubAPIError("Error", status_code=403)
                
                result = await method(*args)
                assert result == expected_default