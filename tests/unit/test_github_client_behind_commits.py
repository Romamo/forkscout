"""Unit tests for GitHub client behind commits functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from forkscout.config import GitHubConfig
from forkscout.github.client import GitHubClient
from forkscout.models.commit_count_result import BatchCommitCountResult, CommitCountResult


class TestGitHubClientBehindCommits:
    """Test GitHub client methods for behind commits."""

    @pytest.fixture
    def github_client(self):
        """Create a GitHub client for testing."""
        config = GitHubConfig(token="test_token")
        return GitHubClient(config)

    @pytest.mark.asyncio
    async def test_get_commits_ahead_and_behind_count_success(self, github_client):
        """Test successful ahead and behind count retrieval."""
        # Mock the get_commits_ahead_behind method
        github_client.get_commits_ahead_behind = AsyncMock(return_value={
            "ahead_by": 9,
            "behind_by": 11,
            "total_commits": 9
        })
        
        result = await github_client.get_commits_ahead_and_behind_count(
            "GreatBots", "YouTube_bot_telegram",
            "sanila2007", "youtube-bot-telegram"
        )
        
        assert isinstance(result, CommitCountResult)
        assert result.ahead_count == 9
        assert result.behind_count == 11
        assert result.is_limited is False
        assert result.error is None
        assert result.is_diverged is True

    @pytest.mark.asyncio
    async def test_get_commits_ahead_and_behind_count_ahead_only(self, github_client):
        """Test ahead-only commits (no behind commits)."""
        github_client.get_commits_ahead_behind = AsyncMock(return_value={
            "ahead_by": 5,
            "behind_by": 0,
            "total_commits": 5
        })
        
        result = await github_client.get_commits_ahead_and_behind_count(
            "owner", "fork", "parent_owner", "parent_repo"
        )
        
        assert result.ahead_count == 5
        assert result.behind_count == 0
        assert result.has_ahead_commits is True
        assert result.has_behind_commits is False
        assert result.is_diverged is False

    @pytest.mark.asyncio
    async def test_get_commits_ahead_and_behind_count_behind_only(self, github_client):
        """Test behind-only commits (no ahead commits)."""
        github_client.get_commits_ahead_behind = AsyncMock(return_value={
            "ahead_by": 0,
            "behind_by": 7,
            "total_commits": 0
        })
        
        result = await github_client.get_commits_ahead_and_behind_count(
            "owner", "fork", "parent_owner", "parent_repo"
        )
        
        assert result.ahead_count == 0
        assert result.behind_count == 7
        assert result.has_ahead_commits is False
        assert result.has_behind_commits is True
        assert result.is_diverged is False

    @pytest.mark.asyncio
    async def test_get_commits_ahead_and_behind_count_no_commits(self, github_client):
        """Test no commits ahead or behind."""
        github_client.get_commits_ahead_behind = AsyncMock(return_value={
            "ahead_by": 0,
            "behind_by": 0,
            "total_commits": 0
        })
        
        result = await github_client.get_commits_ahead_and_behind_count(
            "owner", "fork", "parent_owner", "parent_repo"
        )
        
        assert result.ahead_count == 0
        assert result.behind_count == 0
        assert result.has_ahead_commits is False
        assert result.has_behind_commits is False
        assert result.is_diverged is False

    @pytest.mark.asyncio
    async def test_get_commits_ahead_and_behind_count_error(self, github_client):
        """Test error handling in commit count retrieval."""
        github_client.get_commits_ahead_behind = AsyncMock(
            side_effect=Exception("Repository not found")
        )
        
        result = await github_client.get_commits_ahead_and_behind_count(
            "owner", "fork", "parent_owner", "parent_repo"
        )
        
        assert result.ahead_count == 0
        assert result.behind_count == 0
        assert result.is_limited is False
        assert result.error == "Repository not found"

    @pytest.mark.asyncio
    async def test_get_commits_ahead_and_behind_batch_counts_success(self, github_client):
        """Test successful batch commit count retrieval."""
        # Mock the batch method
        github_client.get_commits_ahead_behind_batch = AsyncMock(return_value={
            "owner1/repo1": {"ahead_by": 5, "behind_by": 2, "total_commits": 5},
            "owner2/repo2": {"ahead_by": 0, "behind_by": 8, "total_commits": 0},
            "owner3/repo3": {"ahead_by": 12, "behind_by": 0, "total_commits": 12},
        })
        
        fork_data_list = [
            ("owner1", "repo1"),
            ("owner2", "repo2"),
            ("owner3", "repo3"),
        ]
        
        result = await github_client.get_commits_ahead_and_behind_batch_counts(
            fork_data_list, "parent_owner", "parent_repo"
        )
        
        assert isinstance(result, BatchCommitCountResult)
        assert len(result.results) == 3
        
        # Check individual results
        assert result.results["owner1/repo1"].ahead_count == 5
        assert result.results["owner1/repo1"].behind_count == 2
        assert result.results["owner2/repo2"].ahead_count == 0
        assert result.results["owner2/repo2"].behind_count == 8
        assert result.results["owner3/repo3"].ahead_count == 12
        assert result.results["owner3/repo3"].behind_count == 0
        
        # Check API call metrics
        assert result.total_api_calls == 7  # 3 forks * 2 + 1 parent
        assert result.parent_calls_saved == 2  # 3 - 1

    @pytest.mark.asyncio
    async def test_get_commits_ahead_and_behind_batch_counts_error(self, github_client):
        """Test error handling in batch commit count retrieval."""
        github_client.get_commits_ahead_behind_batch = AsyncMock(
            side_effect=Exception("API error")
        )
        
        fork_data_list = [("owner1", "repo1"), ("owner2", "repo2")]
        
        result = await github_client.get_commits_ahead_and_behind_batch_counts(
            fork_data_list, "parent_owner", "parent_repo"
        )
        
        assert isinstance(result, BatchCommitCountResult)
        assert len(result.results) == 2
        
        # All results should have error information
        for fork_key in ["owner1/repo1", "owner2/repo2"]:
            assert result.results[fork_key].ahead_count == 0
            assert result.results[fork_key].behind_count == 0
            assert result.results[fork_key].error == "API error"

    @pytest.mark.asyncio
    async def test_get_commits_ahead_and_behind_batch_counts_empty_list(self, github_client):
        """Test batch processing with empty fork list."""
        result = await github_client.get_commits_ahead_and_behind_batch_counts(
            [], "parent_owner", "parent_repo"
        )
        
        assert isinstance(result, BatchCommitCountResult)
        assert len(result.results) == 0
        assert result.total_api_calls == 1  # 0 forks * 2 + 1 parent
        assert result.parent_calls_saved == -1  # 0 - 1

    @pytest.mark.asyncio
    async def test_missing_behind_by_field_handling(self, github_client):
        """Test graceful handling when behind_by field is missing from API response."""
        # Mock response missing behind_by field
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