"""Tests for GitHub client disable_cache parameter functionality."""

from unittest.mock import AsyncMock

import pytest

from forkscout.config import GitHubConfig
from forkscout.github.client import GitHubClient


class TestGitHubClientDisableCache:
    """Test GitHub client disable_cache parameter support."""

    @pytest.fixture
    def github_config(self):
        """Create a test GitHub configuration."""
        return GitHubConfig(token="ghp_1234567890123456789012345678901234567890")

    @pytest.fixture
    def github_client(self, github_config):
        """Create a test GitHub client."""
        return GitHubClient(github_config)

    @pytest.mark.asyncio
    async def test_get_repository_accepts_disable_cache_parameter(self, github_client):
        """Test that get_repository accepts disable_cache parameter."""
        # Mock the base get method
        github_client.get = AsyncMock(return_value={
            "id": 123,
            "owner": {"login": "test-owner"},
            "name": "test-repo",
            "full_name": "test-owner/test-repo",
            "url": "https://api.github.com/repos/test-owner/test-repo",
            "html_url": "https://github.com/test-owner/test-repo",
            "clone_url": "https://github.com/test-owner/test-repo.git",
            "default_branch": "main",
            "stargazers_count": 10,
            "forks_count": 5,
            "fork": False,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-02T00:00:00Z",
            "pushed_at": "2023-01-02T00:00:00Z",
            "size": 100,
            "language": "Python",
            "topics": [],
            "archived": False,
            "disabled": False
        })

        # Test with disable_cache=True
        repo = await github_client.get_repository("test-owner", "test-repo", disable_cache=True)
        assert repo.full_name == "test-owner/test-repo"

        # Test with disable_cache=False
        repo = await github_client.get_repository("test-owner", "test-repo", disable_cache=False)
        assert repo.full_name == "test-owner/test-repo"

        # Test without disable_cache parameter (default)
        repo = await github_client.get_repository("test-owner", "test-repo")
        assert repo.full_name == "test-owner/test-repo"

    @pytest.mark.asyncio
    async def test_get_user_accepts_disable_cache_parameter(self, github_client):
        """Test that get_user accepts disable_cache parameter."""
        # Mock the base get method
        github_client.get = AsyncMock(return_value={
            "id": 456,
            "login": "test-user",
            "name": "Test User",
            "email": None,
            "avatar_url": None,
            "html_url": "https://github.com/test-user",
            "type": "User",
            "site_admin": False
        })

        # Test with disable_cache=True
        user = await github_client.get_user("test-user", disable_cache=True)
        assert user.login == "test-user"

        # Test with disable_cache=False
        user = await github_client.get_user("test-user", disable_cache=False)
        assert user.login == "test-user"

        # Test without disable_cache parameter (default)
        user = await github_client.get_user("test-user")
        assert user.login == "test-user"

    @pytest.mark.asyncio
    async def test_get_commits_ahead_behind_accepts_disable_cache_parameter(self, github_client):
        """Test that get_commits_ahead_behind accepts disable_cache parameter."""
        # Mock the get_fork_comparison method
        github_client.get_fork_comparison = AsyncMock(return_value={
            "ahead_by": 5,
            "behind_by": 2,
            "total_commits": 7
        })

        # Test with disable_cache=True
        result = await github_client.get_commits_ahead_behind(
            "fork-owner", "fork-repo", "parent-owner", "parent-repo", disable_cache=True
        )
        assert result["ahead_by"] == 5
        assert result["behind_by"] == 2

        # Test with disable_cache=False
        result = await github_client.get_commits_ahead_behind(
            "fork-owner", "fork-repo", "parent-owner", "parent-repo", disable_cache=False
        )
        assert result["ahead_by"] == 5

        # Test without disable_cache parameter (default)
        result = await github_client.get_commits_ahead_behind(
            "fork-owner", "fork-repo", "parent-owner", "parent-repo"
        )
        assert result["ahead_by"] == 5

    @pytest.mark.asyncio
    async def test_get_fork_comparison_accepts_disable_cache_parameter(self, github_client):
        """Test that get_fork_comparison accepts disable_cache parameter."""
        # Mock the get_repository method
        github_client.get_repository = AsyncMock()
        github_client.compare_commits = AsyncMock(return_value={
            "ahead_by": 3,
            "behind_by": 1,
            "total_commits": 4
        })

        # Test with disable_cache=True
        result = await github_client.get_fork_comparison(
            "fork-owner", "fork-repo", "parent-owner", "parent-repo", disable_cache=True
        )
        assert result["ahead_by"] == 3

        # Verify that get_repository was called with disable_cache=True
        assert github_client.get_repository.call_count == 2
        calls = github_client.get_repository.call_args_list
        assert calls[0].kwargs.get("disable_cache") is True
        assert calls[1].kwargs.get("disable_cache") is True

    @pytest.mark.asyncio
    async def test_get_repository_contributors_accepts_disable_cache_parameter(self, github_client):
        """Test that get_repository_contributors accepts disable_cache parameter."""
        # Mock the base get method
        github_client.get = AsyncMock(return_value=[
            {"login": "contributor1", "contributions": 10},
            {"login": "contributor2", "contributions": 5}
        ])

        # Test with disable_cache=True
        contributors = await github_client.get_repository_contributors(
            "test-owner", "test-repo", disable_cache=True
        )
        assert len(contributors) == 2
        assert contributors[0]["login"] == "contributor1"

        # Test with disable_cache=False
        contributors = await github_client.get_repository_contributors(
            "test-owner", "test-repo", disable_cache=False
        )
        assert len(contributors) == 2

        # Test without disable_cache parameter (default)
        contributors = await github_client.get_repository_contributors(
            "test-owner", "test-repo"
        )
        assert len(contributors) == 2

    @pytest.mark.asyncio
    async def test_disable_cache_parameter_logging(self, github_client, caplog):
        """Test that disable_cache parameter triggers appropriate logging."""
        import logging
        caplog.set_level(logging.DEBUG)

        # Mock the base get method
        github_client.get = AsyncMock(return_value={
            "id": 123,
            "owner": {"login": "test-owner"},
            "name": "test-repo",
            "full_name": "test-owner/test-repo",
            "url": "https://api.github.com/repos/test-owner/test-repo",
            "html_url": "https://github.com/test-owner/test-repo",
            "clone_url": "https://github.com/test-owner/test-repo.git",
            "default_branch": "main",
            "stargazers_count": 10,
            "forks_count": 5,
            "fork": False,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-02T00:00:00Z",
            "pushed_at": "2023-01-02T00:00:00Z",
            "size": 100,
            "language": "Python",
            "topics": [],
            "archived": False,
            "disabled": False
        })

        # Test that disable_cache=True triggers debug logging
        await github_client.get_repository("test-owner", "test-repo", disable_cache=True)

        # Check that cache bypass was logged
        assert any("Cache bypass requested" in record.message for record in caplog.records)
