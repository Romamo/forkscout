"""Tests for enhanced commit operation error handling."""

import pytest
from unittest.mock import AsyncMock, Mock

from forklift.github.client import GitHubClient
from forklift.github.error_handler import EnhancedErrorHandler
from forklift.github.exceptions import (
    GitHubAPIError,
    GitHubCommitAccessError,
    GitHubCommitComparisonError,
    GitHubDivergentHistoryError,
    GitHubPrivateRepositoryError,
    GitHubEmptyRepositoryError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)
from forklift.config import GitHubConfig


class TestEnhancedCommitErrorHandling:
    """Test enhanced error handling for commit operations."""

    @pytest.fixture
    def error_handler(self):
        """Create error handler for testing."""
        return EnhancedErrorHandler()

    @pytest.fixture
    def github_client(self, error_handler):
        """Create GitHub client with error handler for testing."""
        config = GitHubConfig(token="ghp_1234567890123456789012345678901234567890")
        client = GitHubClient(config, error_handler=error_handler)
        client._client = AsyncMock()
        return client

    def test_handle_commit_comparison_error_not_found(self, error_handler):
        """Test handling of 404 errors in commit comparison."""
        original_error = GitHubAPIError("Not found", status_code=404)
        
        result = error_handler.handle_commit_comparison_error(
            original_error, "owner/repo", "fork_owner/fork_repo"
        )
        
        assert isinstance(result, GitHubCommitComparisonError)
        assert result.reason == "not_found"
        assert result.base_repo == "owner/repo"
        assert result.head_repo == "fork_owner/fork_repo"

    def test_handle_commit_comparison_error_access_denied(self, error_handler):
        """Test handling of 403 errors in commit comparison."""
        original_error = GitHubAPIError("Forbidden", status_code=403)
        
        result = error_handler.handle_commit_comparison_error(
            original_error, "owner/repo", "fork_owner/fork_repo"
        )
        
        assert isinstance(result, GitHubCommitComparisonError)
        assert result.reason == "access_denied"

    def test_handle_commit_comparison_error_divergent_history(self, error_handler):
        """Test handling of 422 errors (divergent history) in commit comparison."""
        original_error = GitHubAPIError("Unprocessable Entity", status_code=422)
        
        result = error_handler.handle_commit_comparison_error(
            original_error, "owner/repo", "fork_owner/fork_repo"
        )
        
        assert isinstance(result, GitHubDivergentHistoryError)
        assert result.base_repo == "owner/repo"
        assert result.head_repo == "fork_owner/fork_repo"

    def test_handle_commit_comparison_error_empty_repository(self, error_handler):
        """Test handling of 409 errors (empty repository) in commit comparison."""
        original_error = GitHubAPIError("Conflict", status_code=409)
        
        result = error_handler.handle_commit_comparison_error(
            original_error, "owner/repo", "fork_owner/fork_repo"
        )
        
        assert isinstance(result, GitHubCommitComparisonError)
        assert result.reason == "empty_repository"

    def test_handle_commit_access_error_unprocessable(self, error_handler):
        """Test handling of 422 errors in commit access."""
        original_error = GitHubAPIError("Unprocessable Entity", status_code=422)
        
        result = error_handler.handle_commit_access_error(
            original_error, "owner/repo", "abc123"
        )
        
        assert isinstance(result, GitHubCommitAccessError)
        assert result.reason == "unprocessable"
        assert result.repository == "owner/repo"
        assert result.commit_sha == "abc123"

    @pytest.mark.asyncio
    async def test_safe_commit_comparison_operation_success(self, error_handler):
        """Test successful commit comparison operation."""
        async def mock_operation():
            return {"ahead_by": 5, "behind_by": 0}
        
        result = await error_handler.safe_commit_comparison_operation(
            mock_operation,
            base_repo="owner/repo",
            head_repo="fork_owner/fork_repo",
            operation_name="test_comparison",
        )
        
        assert result == {"ahead_by": 5, "behind_by": 0}

    @pytest.mark.asyncio
    async def test_safe_commit_comparison_operation_divergent_history(self, error_handler):
        """Test commit comparison with divergent history error."""
        async def mock_operation():
            raise GitHubDivergentHistoryError(
                "Divergent history", "owner/repo", "fork_owner/fork_repo"
            )
        
        result = await error_handler.safe_commit_comparison_operation(
            mock_operation,
            base_repo="owner/repo",
            head_repo="fork_owner/fork_repo",
            operation_name="test_comparison",
            default_value=None,
        )
        
        assert result is None

    @pytest.mark.asyncio
    async def test_safe_commit_comparison_operation_private_repo(self, error_handler):
        """Test commit comparison with private repository error."""
        async def mock_operation():
            raise GitHubPrivateRepositoryError(
                "Private repository", "owner/repo"
            )
        
        result = await error_handler.safe_commit_comparison_operation(
            mock_operation,
            base_repo="owner/repo",
            head_repo="fork_owner/fork_repo",
            operation_name="test_comparison",
            default_value=0,
        )
        
        assert result == 0

    @pytest.mark.asyncio
    async def test_safe_commit_comparison_operation_rate_limit_reraises(self, error_handler):
        """Test that rate limit errors are re-raised."""
        async def mock_operation():
            raise GitHubRateLimitError("Rate limit exceeded")
        
        with pytest.raises(GitHubRateLimitError):
            await error_handler.safe_commit_comparison_operation(
                mock_operation,
                base_repo="owner/repo",
                head_repo="fork_owner/fork_repo",
                operation_name="test_comparison",
            )

    def test_get_user_friendly_error_message_divergent_history(self, error_handler):
        """Test user-friendly message for divergent history error."""
        error = GitHubDivergentHistoryError(
            "Divergent history", "owner/repo", "fork_owner/fork_repo"
        )
        
        message = error_handler.get_user_friendly_error_message(error)
        
        assert "divergent histories" in message
        assert "owner/repo" in message
        assert "fork_owner/fork_repo" in message

    def test_get_user_friendly_error_message_commit_comparison(self, error_handler):
        """Test user-friendly message for commit comparison error."""
        error = GitHubCommitComparisonError(
            "Access denied", "owner/repo", "fork_owner/fork_repo", "access_denied"
        )
        
        message = error_handler.get_user_friendly_error_message(error)
        
        assert "access denied" in message
        assert "may be private" in message

    def test_get_user_friendly_error_message_commit_access(self, error_handler):
        """Test user-friendly message for commit access error."""
        error = GitHubCommitAccessError(
            "Unprocessable", "owner/repo", "unprocessable", "abc123"
        )
        
        message = error_handler.get_user_friendly_error_message(error)
        
        assert "unusual history" in message
        assert "owner/repo" in message

    def test_should_continue_processing_commit_errors(self, error_handler):
        """Test that commit-related errors allow continued processing."""
        errors_to_continue = [
            GitHubCommitComparisonError("Error", "base", "head", "not_found"),
            GitHubDivergentHistoryError("Error", "base", "head"),
            GitHubCommitAccessError("Error", "repo", "unprocessable"),
            GitHubPrivateRepositoryError("Error", "repo"),
            GitHubEmptyRepositoryError("Error", "repo"),
        ]
        
        for error in errors_to_continue:
            assert error_handler.should_continue_processing(error)

    @pytest.mark.asyncio
    async def test_compare_commits_safe_returns_none_on_error(self, github_client):
        """Test that compare_commits_safe returns None on errors."""
        # Mock the get method to raise an error
        github_client._client.request = AsyncMock(side_effect=GitHubAPIError("Not found", status_code=404))
        
        result = await github_client.compare_commits_safe("owner", "repo", "main", "fork_owner:main")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_compare_commits_safe_returns_data_on_success(self, github_client):
        """Test that compare_commits_safe returns data on success."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ahead_by": 5,
            "behind_by": 0,
            "commits": []
        }
        mock_response.raise_for_status.return_value = None
        github_client._client.request = AsyncMock(return_value=mock_response)
        
        result = await github_client.compare_commits_safe("owner", "repo", "main", "fork_owner:main")
        
        assert result is not None
        assert result["ahead_by"] == 5

    @pytest.mark.asyncio
    async def test_get_commits_ahead_count_handles_comparison_failure(self, github_client):
        """Test that get_commits_ahead_count handles comparison failures gracefully."""
        # Mock repository calls to succeed
        mock_repo_response = Mock()
        mock_repo_response.status_code = 200
        mock_repo_response.json.return_value = {
            "name": "test_repo",
            "owner": {"login": "test_owner"},
            "full_name": "test_owner/test_repo",
            "default_branch": "main",
            "html_url": "https://github.com/test_owner/test_repo",
            "clone_url": "https://github.com/test_owner/test_repo.git",
            "url": "https://api.github.com/repos/test_owner/test_repo"
        }
        mock_repo_response.raise_for_status.return_value = None
        
        # Mock comparison to fail
        def mock_request(method, url, **kwargs):
            if "compare" in url:
                raise GitHubAPIError("Not found", status_code=404)
            return mock_repo_response
        
        github_client._client.request = AsyncMock(side_effect=mock_request)
        
        result = await github_client.get_commits_ahead_count(
            "fork_owner", "fork_repo", "parent_owner", "parent_repo"
        )
        
        assert result == 0  # Should return 0 when comparison fails


class TestCommitErrorHandlingIntegration:
    """Integration tests for commit error handling."""

    @pytest.fixture
    def github_client(self):
        """Create GitHub client for integration testing."""
        config = GitHubConfig(token="ghp_1234567890123456789012345678901234567890")
        client = GitHubClient(config)
        client._client = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_batch_count_handles_mixed_success_failure(self, github_client):
        """Test that batch counting handles mixed success and failure scenarios."""
        # Mock repository responses
        def mock_request(method, url, **kwargs):
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            
            
            if url == "/repos/parent/repo":
                # Parent repo succeeds
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "name": "repo",
                    "owner": {"login": "parent"},
                    "full_name": "parent/repo",
                    "default_branch": "main",
                    "html_url": "https://github.com/parent/repo",
                    "clone_url": "https://github.com/parent/repo.git",
                    "url": "https://api.github.com/repos/parent/repo"
                }
            elif url == "/repos/fork1/repo":
                # Fork1 succeeds
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "name": "repo",
                    "owner": {"login": "fork1"},
                    "full_name": "fork1/repo",
                    "default_branch": "main",
                    "html_url": "https://github.com/fork1/repo",
                    "clone_url": "https://github.com/fork1/repo.git",
                    "url": "https://api.github.com/repos/fork1/repo"
                }
            elif url == "/repos/fork2/repo":
                # Fork2 is private (403)
                raise GitHubAPIError("Forbidden", status_code=403)
            elif url == "/repos/parent/repo/compare/main...fork1:main":
                # Comparison with fork1 succeeds
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "ahead_by": 5,
                    "behind_by": 0,
                    "commits": []
                }
            elif "compare" in url and "fork2" in url:
                # This shouldn't be called since fork2 repo fetch fails
                raise GitHubAPIError("Not found", status_code=404)
            else:
                raise GitHubAPIError("Not found", status_code=404)
            
            return mock_response
        
        github_client._client.request = AsyncMock(side_effect=mock_request)
        
        fork_data_list = [("fork1", "repo"), ("fork2", "repo")]
        
        result = await github_client.get_commits_ahead_batch_counts(
            fork_data_list, "parent", "repo"
        )
        
        # Should have result for fork1 but not fork2
        assert "fork1/repo" in result
        assert result["fork1/repo"] == 5
        assert "fork2/repo" not in result

    @pytest.mark.asyncio
    async def test_error_propagation_in_individual_calls(self, github_client):
        """Test that individual calls properly propagate specific error types."""
        # Mock to raise divergent history error
        def mock_request(method, url, **kwargs):
            if "compare" in url:
                raise GitHubAPIError("Unprocessable Entity", status_code=422)
            
            # Repository calls succeed
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "name": "repo",
                "owner": {"login": "owner"},
                "full_name": "owner/repo",
                "default_branch": "main",
                "html_url": "https://github.com/owner/repo",
                "clone_url": "https://github.com/owner/repo.git",
                "url": "https://api.github.com/repos/owner/repo"
            }
            mock_response.raise_for_status.return_value = None
            return mock_response
        
        github_client._client.request = AsyncMock(side_effect=mock_request)
        
        with pytest.raises(GitHubDivergentHistoryError):
            await github_client.compare_repositories(
                "parent", "repo", "fork", "repo"
            )