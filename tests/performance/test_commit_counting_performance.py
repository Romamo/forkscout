"""Performance tests for commit counting operations."""

import asyncio
import time
import pytest
import respx
import httpx
from datetime import datetime, timezone

from forklift.config import GitHubConfig
from forklift.github.client import GitHubClient
from forklift.models.github import Repository, RecentCommit
from forklift.models.commit_count_config import CommitCountConfig


class TestCommitCountingPerformance:
    """Performance tests for commit counting operations."""

    @pytest.fixture
    def github_config(self):
        """Create GitHub configuration for testing."""
        return GitHubConfig(
            token="ghp_test_token_1234567890abcdef1234567890abcdef12345678",
            base_url="https://api.github.com",
            timeout_seconds=30,
        )

    @pytest.fixture
    def github_client(self, github_config):
        """Create GitHub client for testing."""
        return GitHubClient(github_config)

    @pytest.mark.performance
    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_count_performance_single(self, github_client):
        """Test performance of single commit count operation."""
        # Mock repository responses
        fork_repo_response = {
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

        parent_repo_response = {
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

        comparison_response = {
            "ahead_by": 50,
            "behind_by": 0,
            "total_commits": 50,
            "status": "ahead",
            "commits": []
        }

        # Mock API calls
        respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork_repo_response)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_response)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo/compare/main...fork-owner:main").mock(
            return_value=httpx.Response(200, json=comparison_response)
        )

        async with github_client:
            start_time = time.time()
            
            count = await github_client.get_commits_ahead_count(
                "fork-owner", "test-repo", "parent-owner", "test-repo"
            )
            
            end_time = time.time()
            duration = end_time - start_time

            # Performance assertions
            assert count == 50
            assert duration < 2.0, f"Single count operation took {duration:.3f}s, expected < 2.0s"

    @pytest.mark.performance
    @pytest.mark.asyncio
    @respx.mock
    async def test_batch_operations_performance(self, github_client):
        """Test performance of batch commit count operations."""
        fork_count = 5  # Smaller count for reliable testing
        
        # Mock parent repository
        parent_repo_response = {
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

        # Mock fork repositories and comparisons
        for i in range(fork_count):
            fork_repo_response = {
                "id": i + 10,
                "name": "test-repo",
                "full_name": f"fork-owner-{i}/test-repo",
                "owner": {"login": f"fork-owner-{i}"},
                "url": f"https://api.github.com/repos/fork-owner-{i}/test-repo",
                "html_url": f"https://github.com/fork-owner-{i}/test-repo",
                "clone_url": f"https://github.com/fork-owner-{i}/test-repo.git",
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

            comparison_response = {
                "ahead_by": i + 1,
                "behind_by": 0,
                "total_commits": i + 1,
                "status": "ahead",
                "commits": []
            }

            # Mock API calls for each fork
            respx.get(f"https://api.github.com/repos/fork-owner-{i}/test-repo").mock(
                return_value=httpx.Response(200, json=fork_repo_response)
            )
            respx.get(f"https://api.github.com/repos/parent-owner/test-repo/compare/main...fork-owner-{i}:main").mock(
                return_value=httpx.Response(200, json=comparison_response)
            )

        # Mock parent repository (cached)
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_response)
        )

        fork_data_list = [(f"fork-owner-{i}", "test-repo") for i in range(fork_count)]

        async with github_client:
            start_time = time.time()
            
            result = await github_client.get_commits_ahead_batch_counts(
                fork_data_list, "parent-owner", "test-repo"
            )
            
            end_time = time.time()
            duration = end_time - start_time

            # Performance assertions
            assert len(result) == fork_count
            assert duration < 5.0, f"Batch count operation for {fork_count} forks took {duration:.3f}s, expected < 5.0s"
            
            # Verify results
            for i in range(fork_count):
                fork_key = f"fork-owner-{i}/test-repo"
                assert fork_key in result
                assert result[fork_key] == i + 1

    @pytest.mark.performance
    @pytest.mark.asyncio
    @respx.mock
    async def test_api_call_efficiency(self, github_client):
        """Test that commit counting uses efficient API calls."""
        # Mock repository responses
        fork_repo_response = {
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

        parent_repo_response = {
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

        # Test with large commit count to verify efficiency
        comparison_response = {
            "ahead_by": 1000,  # Large count
            "behind_by": 0,
            "total_commits": 1000,
            "status": "ahead",
            "commits": []  # Empty array - we should use ahead_by, not count commits
        }

        # Mock API calls
        respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork_repo_response)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_response)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo/compare/main...fork-owner:main").mock(
            return_value=httpx.Response(200, json=comparison_response)
        )

        async with github_client:
            start_time = time.time()
            
            count = await github_client.get_commits_ahead_count(
                "fork-owner", "test-repo", "parent-owner", "test-repo"
            )
            
            end_time = time.time()
            duration = end_time - start_time

            # Verify efficiency - should use ahead_by field, not count commits
            assert count == 1000, "Should use ahead_by field for accurate count"
            assert duration < 2.0, f"API call took {duration:.3f}s, expected < 2.0s"
            
            # Verify only necessary API calls were made
            assert len(respx.calls) == 3, f"Expected 3 API calls, got {len(respx.calls)}"