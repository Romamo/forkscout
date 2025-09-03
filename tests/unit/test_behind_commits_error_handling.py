"""Unit tests for behind commits error handling."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from forklift.config import GitHubConfig
from forklift.github.client import GitHubClient
from forklift.github.exceptions import GitHubAPIError, GitHubNotFoundError
from forklift.models.commit_count_result import CommitCountResult


class TestBehindCommitsErrorHandling:
    """Test error handling for behind commits functionality."""

    @pytest.fixture
    def github_client(self):
        """Create a GitHub client for testing."""
        config = GitHubConfig(token="test_token")
        return GitHubClient(config)

    @pytest.mark.asyncio
    async def test_missing_behind_by_field_defaults_to_zero(self, github_client):
        """Test that missing behind_by field defaults to 0."""
        # Mock API response without behind_by field
        github_client.get_commits_ahead_behind = AsyncMock(return_value={
            "ahead_by": 5,
            "total_commits": 5
            # behind_by field is missing
        })
        
        result = await github_client.get_commits_ahead_and_behind_count(
            "owner", "fork", "parent_owner", "parent_repo"
        )
        
        assert result.ahead_count == 5
        assert result.behind_count == 0  # Should default to 0
        assert result.error is None

    @pytest.mark.asyncio
    async def test_api_error_returns_error_result(self, github_client):
        """Test that API errors are captured in the result."""
        github_client.get_commits_ahead_behind = AsyncMock(
            side_effect=GitHubAPIError("Rate limit exceeded")
        )
        
        result = await github_client.get_commits_ahead_and_behind_count(
            "owner", "fork", "parent_owner", "parent_repo"
        )
        
        assert result.ahead_count == 0
        assert result.behind_count == 0
        assert result.error == "Rate limit exceeded"

    @pytest.mark.asyncio
    async def test_repository_not_found_error(self, github_client):
        """Test handling of repository not found errors."""
        github_client.get_commits_ahead_behind = AsyncMock(
            side_effect=GitHubNotFoundError("Repository not found")
        )
        
        result = await github_client.get_commits_ahead_and_behind_count(
            "owner", "nonexistent", "parent_owner", "parent_repo"
        )
        
        assert result.ahead_count == 0
        assert result.behind_count == 0
        assert result.error == "Repository not found"

    @pytest.mark.asyncio
    async def test_network_timeout_error(self, github_client):
        """Test handling of network timeout errors."""
        github_client.get_commits_ahead_behind = AsyncMock(
            side_effect=Exception("Connection timeout")
        )
        
        result = await github_client.get_commits_ahead_and_behind_count(
            "owner", "fork", "parent_owner", "parent_repo"
        )
        
        assert result.ahead_count == 0
        assert result.behind_count == 0
        assert result.error == "Connection timeout"

    @pytest.mark.asyncio
    async def test_malformed_api_response_handling(self, github_client):
        """Test handling of malformed API responses."""
        # Mock API response with invalid data types
        github_client.get_commits_ahead_behind = AsyncMock(return_value={
            "ahead_by": "invalid",  # Should be int
            "behind_by": None,      # Should be int
            "total_commits": "also_invalid"
        })
        
        result = await github_client.get_commits_ahead_and_behind_count(
            "owner", "fork", "parent_owner", "parent_repo"
        )
        
        # Should handle gracefully and default to 0
        assert result.ahead_count == 0
        assert result.behind_count == 0

    @pytest.mark.asyncio
    async def test_batch_processing_partial_failures(self, github_client):
        """Test batch processing with some forks failing."""
        # Mock batch method with mixed success/failure
        github_client.get_commits_ahead_behind_batch = AsyncMock(return_value={
            "owner1/repo1": {"ahead_by": 5, "behind_by": 2, "total_commits": 5},
            # owner2/repo2 is missing (failed to process)
            "owner3/repo3": {"ahead_by": 0, "behind_by": 8, "total_commits": 0},
        })
        
        fork_data_list = [
            ("owner1", "repo1"),
            ("owner2", "repo2"),  # This one will be missing from results
            ("owner3", "repo3"),
        ]
        
        result = await github_client.get_commits_ahead_and_behind_batch_counts(
            fork_data_list, "parent_owner", "parent_repo"
        )
        
        # Should have results for successful forks
        assert "owner1/repo1" in result.results
        assert "owner3/repo3" in result.results
        
        # Should have successful results
        assert result.results["owner1/repo1"].ahead_count == 5
        assert result.results["owner1/repo1"].behind_count == 2
        assert result.results["owner3/repo3"].ahead_count == 0
        assert result.results["owner3/repo3"].behind_count == 8

    @pytest.mark.asyncio
    async def test_empty_api_response_handling(self, github_client):
        """Test handling of empty API responses."""
        github_client.get_commits_ahead_behind = AsyncMock(return_value={})
        
        result = await github_client.get_commits_ahead_and_behind_count(
            "owner", "fork", "parent_owner", "parent_repo"
        )
        
        # Should default to 0 for missing fields
        assert result.ahead_count == 0
        assert result.behind_count == 0
        assert result.error is None

    @pytest.mark.asyncio
    async def test_negative_commit_counts_handling(self, github_client):
        """Test handling of negative commit counts from API."""
        # Mock API response with negative values (shouldn't happen but test robustness)
        github_client.get_commits_ahead_behind = AsyncMock(return_value={
            "ahead_by": -5,   # Invalid negative value
            "behind_by": -3,  # Invalid negative value
            "total_commits": 0
        })
        
        result = await github_client.get_commits_ahead_and_behind_count(
            "owner", "fork", "parent_owner", "parent_repo"
        )
        
        # Should accept the values as-is (GitHub API shouldn't return negatives)
        assert result.ahead_count == -5
        assert result.behind_count == -3

    def test_display_formatting_error_handling(self):
        """Test display formatting handles various error conditions."""
        from forklift.display.repository_display_service import RepositoryDisplayService
        from forklift.models.fork_qualification import CollectedForkData, ForkQualificationMetrics
        
        github_client = MagicMock()
        display_service = RepositoryDisplayService(github_client)
        
        # Create fork data with error
        metrics = ForkQualificationMetrics(
            id=123,
            name="test-repo",
            full_name="owner/test-repo",
            owner="owner",
            html_url="https://github.com/owner/test-repo",
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            pushed_at="2023-01-01T00:00:00Z"
        )
        
        fork_data = CollectedForkData(metrics=metrics)
        fork_data.commit_count_error = "API error"
        fork_data.exact_commits_ahead = 5
        fork_data.exact_commits_behind = 3
        
        # Should return "Unknown" when there's an error
        result = display_service._format_commit_count(fork_data)
        assert result == "Unknown"
        
        # CSV formatting should also handle errors
        csv_result = display_service._format_commit_count_for_csv(fork_data)
        assert csv_result == "Unknown"

    def test_display_formatting_handles_missing_attributes(self):
        """Test display formatting when fork data is missing commit attributes."""
        from forklift.display.repository_display_service import RepositoryDisplayService
        from forklift.models.fork_qualification import CollectedForkData, ForkQualificationMetrics
        
        github_client = MagicMock()
        display_service = RepositoryDisplayService(github_client)
        
        # Create fork data without commit count attributes
        metrics = ForkQualificationMetrics(
            id=123,
            name="test-repo",
            full_name="owner/test-repo",
            owner="owner",
            html_url="https://github.com/owner/test-repo",
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            pushed_at="2023-01-01T00:00:00Z"
        )
        
        fork_data = CollectedForkData(metrics=metrics)
        # Don't set exact_commits_ahead or exact_commits_behind
        
        # Should handle missing attributes gracefully
        result = display_service._format_commit_count(fork_data)
        assert result == ""  # Empty string for no data