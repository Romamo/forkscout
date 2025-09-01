"""Tests for GitHub client commits ahead functionality."""

import pytest
import respx
import httpx
from datetime import datetime

from forklift.config import GitHubConfig
from forklift.github.client import GitHubClient
from forklift.github.exceptions import GitHubAPIError
from forklift.models.github import RecentCommit


class TestGitHubClientCommitsAhead:
    """Test GitHub client commits ahead functionality."""

    @pytest.fixture
    def client(self):
        """Create a GitHub client for testing."""
        config = GitHubConfig(
            token="ghp_1234567890abcdef1234567890abcdef12345678",
            base_url="https://api.github.com",
            timeout_seconds=30,
        )
        return GitHubClient(config)

    @pytest.fixture
    def fork_repo_data(self):
        """Mock fork repository data."""
        return {
            "id": 1,
            "name": "test-repo",
            "full_name": "fork-owner/test-repo",
            "owner": {"login": "fork-owner"},
            "url": "https://api.github.com/repos/fork-owner/test-repo",
            "html_url": "https://github.com/fork-owner/test-repo",
            "clone_url": "https://github.com/fork-owner/test-repo.git",
            "default_branch": "main",
            "stargazers_count": 10,
            "forks_count": 2,
            "watchers_count": 15,
            "open_issues_count": 1,
            "size": 512,
            "language": "Python",
            "description": "A test fork repository",
            "topics": ["python", "testing"],
            "license": {"name": "MIT"},
            "private": False,
            "fork": True,
            "archived": False,
            "disabled": False,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-02T00:00:00Z",
            "pushed_at": "2023-01-03T00:00:00Z",
        }

    @pytest.fixture
    def parent_repo_data(self):
        """Mock parent repository data."""
        return {
            "id": 2,
            "name": "test-repo",
            "full_name": "parent-owner/test-repo",
            "owner": {"login": "parent-owner"},
            "url": "https://api.github.com/repos/parent-owner/test-repo",
            "html_url": "https://github.com/parent-owner/test-repo",
            "clone_url": "https://github.com/parent-owner/test-repo.git",
            "default_branch": "main",
            "stargazers_count": 100,
            "forks_count": 25,
            "watchers_count": 150,
            "open_issues_count": 5,
            "size": 1024,
            "language": "Python",
            "description": "A test parent repository",
            "topics": ["python", "testing"],
            "license": {"name": "MIT"},
            "private": False,
            "fork": False,
            "archived": False,
            "disabled": False,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-02T00:00:00Z",
            "pushed_at": "2023-01-03T00:00:00Z",
        }

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_parent_repo_caching(self, client, fork_repo_data, parent_repo_data):
        """Test that parent repository data is cached to reduce API calls."""
        # Mock comparison response with commits
        comparison_data = {
            "ahead_by": 1,
            "behind_by": 0,
            "commits": [
                {
                    "sha": "abc1234567890abcdef1234567890abcdef123456",
                    "commit": {
                        "message": "Fix bug in parser",
                        "author": {
                            "date": "2024-01-15T10:30:00Z"
                        }
                    }
                }
            ]
        }

        # Mock API calls - parent repo should only be called once
        fork_mock = respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork_repo_data)
        )
        parent_mock = respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        compare_mock = respx.get("https://api.github.com/repos/parent-owner/test-repo/compare/main...fork-owner:main").mock(
            return_value=httpx.Response(200, json=comparison_data)
        )

        async with client:
            # First call - should fetch parent repo from API
            result1 = await client.get_commits_ahead("fork-owner", "test-repo", "parent-owner", "test-repo", 5)
            
            # Second call - should use cached parent repo data
            result2 = await client.get_commits_ahead("fork-owner", "test-repo", "parent-owner", "test-repo", 5)

        # Verify results are the same
        assert len(result1) == 1
        assert len(result2) == 1
        assert result1[0].short_sha == result2[0].short_sha

        # Verify API call counts
        assert fork_mock.call_count == 2  # Fork repo called twice (not cached)
        assert parent_mock.call_count == 1  # Parent repo called only once (cached on second call)
        assert compare_mock.call_count == 2  # Compare called twice

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_multiple_forks_same_parent(self, client, parent_repo_data):
        """Test caching with multiple forks of the same parent repository."""
        # Create different fork data
        fork1_data = {**parent_repo_data, "full_name": "fork1-owner/test-repo", "owner": {"login": "fork1-owner"}}
        fork2_data = {**parent_repo_data, "full_name": "fork2-owner/test-repo", "owner": {"login": "fork2-owner"}}

        comparison_data = {
            "ahead_by": 1,
            "behind_by": 0,
            "commits": [
                {
                    "sha": "abc1234567890abcdef1234567890abcdef123456",
                    "commit": {
                        "message": "Fix bug in parser",
                        "author": {
                            "date": "2024-01-15T10:30:00Z"
                        }
                    }
                }
            ]
        }

        # Mock API calls
        respx.get("https://api.github.com/repos/fork1-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork1_data)
        )
        respx.get("https://api.github.com/repos/fork2-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork2_data)
        )
        parent_mock = respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo/compare/main...fork1-owner:main").mock(
            return_value=httpx.Response(200, json=comparison_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo/compare/main...fork2-owner:main").mock(
            return_value=httpx.Response(200, json=comparison_data)
        )

        async with client:
            # Compare multiple forks against the same parent
            result1 = await client.get_commits_ahead("fork1-owner", "test-repo", "parent-owner", "test-repo", 5)
            result2 = await client.get_commits_ahead("fork2-owner", "test-repo", "parent-owner", "test-repo", 5)

        # Verify results
        assert len(result1) == 1
        assert len(result2) == 1

        # Parent repo should only be called once due to caching
        assert parent_mock.call_count == 1

    @pytest.mark.asyncio
    async def test_parent_repo_cache_management(self, client):
        """Test parent repository cache management methods."""
        async with client:
            # Initially cache should be empty
            stats = client.get_parent_repo_cache_stats()
            assert stats["total_entries"] == 0
            assert stats["valid_entries"] == 0
            assert stats["expired_entries"] == 0
            assert stats["cache_ttl_seconds"] == 300

            # Test cache clearing
            client.clear_parent_repo_cache()
            stats = client.get_parent_repo_cache_stats()
            assert stats["total_entries"] == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_parent_repo_cache_expiration(self, client, fork_repo_data, parent_repo_data):
        """Test that cached parent repository data expires after TTL."""
        import time
        
        # Set a very short TTL for testing
        client._cache_ttl = 0.1  # 100ms
        
        comparison_data = {
            "ahead_by": 1,
            "behind_by": 0,
            "commits": [
                {
                    "sha": "abc1234567890abcdef1234567890abcdef123456",
                    "commit": {
                        "message": "Fix bug in parser",
                        "author": {
                            "date": "2024-01-15T10:30:00Z"
                        }
                    }
                }
            ]
        }

        # Mock API calls
        respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork_repo_data)
        )
        parent_mock = respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo/compare/main...fork-owner:main").mock(
            return_value=httpx.Response(200, json=comparison_data)
        )

        async with client:
            # First call - should cache parent repo
            await client.get_commits_ahead("fork-owner", "test-repo", "parent-owner", "test-repo", 5)
            
            # Wait for cache to expire
            time.sleep(0.2)
            
            # Second call - cache should be expired, should fetch again
            await client.get_commits_ahead("fork-owner", "test-repo", "parent-owner", "test-repo", 5)

        # Parent repo should be called twice due to cache expiration
        assert parent_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_cleared_on_close(self, client):
        """Test that cache is cleared when client is closed."""
        # Manually add something to cache
        from forklift.models.github import Repository
        
        repo_data = {
            "id": 1,
            "name": "test",
            "full_name": "owner/test",
            "owner": {"login": "owner"},
            "url": "https://api.github.com/repos/owner/test",
            "html_url": "https://github.com/owner/test",
            "clone_url": "https://github.com/owner/test.git",
            "default_branch": "main",
            "stargazers_count": 0,
            "forks_count": 0,
            "watchers_count": 0,
            "open_issues_count": 0,
            "size": 0,
            "language": None,
            "description": None,
            "topics": [],
            "license": None,
            "private": False,
            "fork": False,
            "archived": False,
            "disabled": False,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
            "pushed_at": "2023-01-01T00:00:00Z",
        }
        
        repo = Repository.from_github_api(repo_data)
        client._cache_parent_repo("owner", "test", repo)
        
        # Verify cache has entry
        stats = client.get_parent_repo_cache_stats()
        assert stats["total_entries"] == 1
        
        # Close client
        await client.close()
        
        # Verify cache is cleared
        stats = client.get_parent_repo_cache_stats()
        assert stats["total_entries"] == 0