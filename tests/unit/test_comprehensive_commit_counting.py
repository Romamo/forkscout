"""Comprehensive unit tests for GitHub client commit counting functionality.

This test suite covers all commit counting methods with various scenarios,
error handling, and edge cases as required by task 6 of the commits-ahead-count-fix spec.
"""

import httpx
import pytest
import respx

from forklift.config import GitHubConfig
from forklift.github.client import GitHubClient
from forklift.github.exceptions import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubPrivateRepositoryError,
    GitHubRateLimitError,
)


class TestComprehensiveCommitCounting:
    """Comprehensive tests for commit counting functionality."""

    @pytest.fixture
    def client(self):
        """Create a GitHub client for testing."""
        from forklift.github.rate_limiter import RateLimitHandler
        
        config = GitHubConfig(
            token="ghp_1234567890abcdef1234567890abcdef12345678",
            base_url="https://api.github.com",
            timeout_seconds=30,
        )
        # Create rate limit handler with no retries for testing
        rate_limit_handler = RateLimitHandler(max_retries=0)
        return GitHubClient(config, rate_limit_handler=rate_limit_handler)

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

    # Test get_commits_ahead_count method with various scenarios

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_count_basic_functionality(
        self, client, fork_repo_data, parent_repo_data
    ):
        """Test basic functionality of get_commits_ahead_count method."""
        comparison_data = {
            "ahead_by": 5,
            "behind_by": 0,
            "total_commits": 5,
            "status": "ahead",
            "commits": [],
        }

        # Mock API calls
        respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork_repo_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        respx.get(
            "https://api.github.com/repos/parent-owner/test-repo/compare/main...fork-owner:main"
        ).mock(return_value=httpx.Response(200, json=comparison_data))

        async with client:
            count = await client.get_commits_ahead_count(
                "fork-owner", "test-repo", "parent-owner", "test-repo"
            )
            assert count == 5

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_count_zero_commits(
        self, client, fork_repo_data, parent_repo_data
    ):
        """Test get_commits_ahead_count when fork has no commits ahead."""
        comparison_data = {
            "ahead_by": 0,
            "behind_by": 2,
            "total_commits": 0,
            "status": "behind",
            "commits": [],
        }

        # Mock API calls
        respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork_repo_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        respx.get(
            "https://api.github.com/repos/parent-owner/test-repo/compare/main...fork-owner:main"
        ).mock(return_value=httpx.Response(200, json=comparison_data))

        async with client:
            count = await client.get_commits_ahead_count(
                "fork-owner", "test-repo", "parent-owner", "test-repo"
            )
            assert count == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_count_large_numbers(
        self, client, fork_repo_data, parent_repo_data
    ):
        """Test get_commits_ahead_count with large commit counts."""
        comparison_data = {
            "ahead_by": 1500,
            "behind_by": 0,
            "total_commits": 1500,
            "status": "ahead",
            "commits": [],
        }

        # Mock API calls
        respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork_repo_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        respx.get(
            "https://api.github.com/repos/parent-owner/test-repo/compare/main...fork-owner:main"
        ).mock(return_value=httpx.Response(200, json=comparison_data))

        async with client:
            count = await client.get_commits_ahead_count(
                "fork-owner", "test-repo", "parent-owner", "test-repo"
            )
            assert count == 1500

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_count_fallback_to_commits_array(
        self, client, fork_repo_data, parent_repo_data
    ):
        """Test get_commits_ahead_count fallback when ahead_by field is missing."""
        comparison_data = {
            "behind_by": 0,
            "total_commits": 3,
            "status": "ahead",
            "commits": [
                {
                    "sha": "abc123",
                    "commit": {
                        "message": "Commit 1",
                        "author": {"date": "2024-01-15T10:30:00Z"},
                    },
                },
                {
                    "sha": "def456",
                    "commit": {
                        "message": "Commit 2",
                        "author": {"date": "2024-01-15T10:31:00Z"},
                    },
                },
                {
                    "sha": "ghi789",
                    "commit": {
                        "message": "Commit 3",
                        "author": {"date": "2024-01-15T10:32:00Z"},
                    },
                },
            ],
        }

        # Mock API calls
        respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork_repo_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        respx.get(
            "https://api.github.com/repos/parent-owner/test-repo/compare/main...fork-owner:main"
        ).mock(return_value=httpx.Response(200, json=comparison_data))

        async with client:
            count = await client.get_commits_ahead_count(
                "fork-owner", "test-repo", "parent-owner", "test-repo"
            )
            assert count == 3  # Should fallback to len(commits)

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_count_different_branches(
        self, client, parent_repo_data
    ):
        """Test get_commits_ahead_count with different default branches."""
        # Fork with different default branch
        fork_data_develop = {
            **parent_repo_data,
            "full_name": "fork-owner/test-repo",
            "owner": {"login": "fork-owner"},
            "default_branch": "develop",
        }

        comparison_data = {
            "ahead_by": 8,
            "behind_by": 0,
            "total_commits": 8,
            "status": "ahead",
            "commits": [],
        }

        # Mock API calls
        respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork_data_develop)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        respx.get(
            "https://api.github.com/repos/parent-owner/test-repo/compare/main...fork-owner:develop"
        ).mock(return_value=httpx.Response(200, json=comparison_data))

        async with client:
            count = await client.get_commits_ahead_count(
                "fork-owner", "test-repo", "parent-owner", "test-repo"
            )
            assert count == 8

    # Test batch counting methods for accuracy and efficiency

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_batch_counts_basic_functionality(
        self, client, parent_repo_data
    ):
        """Test basic functionality of get_commits_ahead_batch_counts method."""
        # Create multiple fork data
        fork1_data = {
            **parent_repo_data,
            "full_name": "fork1-owner/test-repo",
            "owner": {"login": "fork1-owner"},
        }
        fork2_data = {
            **parent_repo_data,
            "full_name": "fork2-owner/test-repo",
            "owner": {"login": "fork2-owner"},
        }
        fork3_data = {
            **parent_repo_data,
            "full_name": "fork3-owner/test-repo",
            "owner": {"login": "fork3-owner"},
        }

        fork_data_list = [
            ("fork1-owner", "test-repo"),
            ("fork2-owner", "test-repo"),
            ("fork3-owner", "test-repo"),
        ]

        # Mock comparison responses with different ahead_by values
        comparison_data_fork1 = {"ahead_by": 15, "behind_by": 0, "commits": []}
        comparison_data_fork2 = {"ahead_by": 7, "behind_by": 0, "commits": []}
        comparison_data_fork3 = {"ahead_by": 0, "behind_by": 1, "commits": []}

        # Mock API calls
        respx.get("https://api.github.com/repos/fork1-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork1_data)
        )
        respx.get("https://api.github.com/repos/fork2-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork2_data)
        )
        respx.get("https://api.github.com/repos/fork3-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork3_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        respx.get(
            "https://api.github.com/repos/parent-owner/test-repo/compare/main...fork1-owner:main"
        ).mock(return_value=httpx.Response(200, json=comparison_data_fork1))
        respx.get(
            "https://api.github.com/repos/parent-owner/test-repo/compare/main...fork2-owner:main"
        ).mock(return_value=httpx.Response(200, json=comparison_data_fork2))
        respx.get(
            "https://api.github.com/repos/parent-owner/test-repo/compare/main...fork3-owner:main"
        ).mock(return_value=httpx.Response(200, json=comparison_data_fork3))

        async with client:
            result = await client.get_commits_ahead_batch_counts(
                fork_data_list, "parent-owner", "test-repo"
            )

            assert len(result) == 3
            assert result["fork1-owner/test-repo"] == 15
            assert result["fork2-owner/test-repo"] == 7
            assert result["fork3-owner/test-repo"] == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_batch_counts_empty_list(self, client):
        """Test get_commits_ahead_batch_counts with empty fork list."""
        async with client:
            result = await client.get_commits_ahead_batch_counts(
                [], "parent-owner", "test-repo"
            )
            assert result == {}

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_batch_counts_single_fork(
        self, client, fork_repo_data, parent_repo_data
    ):
        """Test get_commits_ahead_batch_counts with single fork."""
        fork_data_list = [("fork-owner", "test-repo")]
        comparison_data = {"ahead_by": 12, "behind_by": 0, "commits": []}

        # Mock API calls
        respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork_repo_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        respx.get(
            "https://api.github.com/repos/parent-owner/test-repo/compare/main...fork-owner:main"
        ).mock(return_value=httpx.Response(200, json=comparison_data))

        async with client:
            result = await client.get_commits_ahead_batch_counts(
                fork_data_list, "parent-owner", "test-repo"
            )

            assert len(result) == 1
            assert result["fork-owner/test-repo"] == 12

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_batch_counts_efficiency(
        self, client, parent_repo_data
    ):
        """Test that batch counting is efficient and fetches parent repo only once."""
        # Create multiple fork data
        fork_data_list = [
            ("fork1-owner", "test-repo"),
            ("fork2-owner", "test-repo"),
            ("fork3-owner", "test-repo"),
        ]

        fork1_data = {
            **parent_repo_data,
            "full_name": "fork1-owner/test-repo",
            "owner": {"login": "fork1-owner"},
        }
        fork2_data = {
            **parent_repo_data,
            "full_name": "fork2-owner/test-repo",
            "owner": {"login": "fork2-owner"},
        }
        fork3_data = {
            **parent_repo_data,
            "full_name": "fork3-owner/test-repo",
            "owner": {"login": "fork3-owner"},
        }

        comparison_data = {"ahead_by": 5, "behind_by": 0, "commits": []}

        # Mock API calls
        respx.get("https://api.github.com/repos/fork1-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork1_data)
        )
        respx.get("https://api.github.com/repos/fork2-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork2_data)
        )
        respx.get("https://api.github.com/repos/fork3-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork3_data)
        )
        parent_mock = respx.get(
            "https://api.github.com/repos/parent-owner/test-repo"
        ).mock(return_value=httpx.Response(200, json=parent_repo_data))
        respx.get(
            "https://api.github.com/repos/parent-owner/test-repo/compare/main...fork1-owner:main"
        ).mock(return_value=httpx.Response(200, json=comparison_data))
        respx.get(
            "https://api.github.com/repos/parent-owner/test-repo/compare/main...fork2-owner:main"
        ).mock(return_value=httpx.Response(200, json=comparison_data))
        respx.get(
            "https://api.github.com/repos/parent-owner/test-repo/compare/main...fork3-owner:main"
        ).mock(return_value=httpx.Response(200, json=comparison_data))

        async with client:
            result = await client.get_commits_ahead_batch_counts(
                fork_data_list, "parent-owner", "test-repo"
            )

            assert len(result) == 3
            # Parent repository should only be fetched once for efficiency
            assert parent_mock.call_count == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_batch_counts_concurrent_processing(
        self, client, parent_repo_data
    ):
        """Test that batch counting processes forks concurrently."""
        # Create many forks to test concurrent processing
        fork_data_list = [(f"fork{i}-owner", "test-repo") for i in range(10)]

        # Mock data for all forks
        for i in range(10):
            fork_data = {
                **parent_repo_data,
                "full_name": f"fork{i}-owner/test-repo",
                "owner": {"login": f"fork{i}-owner"},
            }
            comparison_data = {"ahead_by": i + 1, "behind_by": 0, "commits": []}

            respx.get(f"https://api.github.com/repos/fork{i}-owner/test-repo").mock(
                return_value=httpx.Response(200, json=fork_data)
            )
            respx.get(
                f"https://api.github.com/repos/parent-owner/test-repo/compare/main...fork{i}-owner:main"
            ).mock(return_value=httpx.Response(200, json=comparison_data))

        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )

        async with client:
            import time

            start_time = time.time()
            result = await client.get_commits_ahead_batch_counts(
                fork_data_list, "parent-owner", "test-repo"
            )
            end_time = time.time()

            # Verify all forks were processed
            assert len(result) == 10
            for i in range(10):
                assert result[f"fork{i}-owner/test-repo"] == i + 1

            # Processing should be reasonably fast due to concurrency
            # This is a rough check - in real scenarios, concurrent processing should be faster
            assert end_time - start_time < 5.0  # Should complete within 5 seconds

    # Test error handling for different failure modes

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_count_fork_not_found(
        self, client, parent_repo_data
    ):
        """Test error handling when fork repository is not found."""
        # Mock parent repo success but fork repo 404
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        respx.get("https://api.github.com/repos/nonexistent-fork/test-repo").mock(
            return_value=httpx.Response(404, json={"message": "Not Found"})
        )

        async with client:
            with pytest.raises(GitHubPrivateRepositoryError):
                await client.get_commits_ahead_count(
                    "nonexistent-fork", "test-repo", "parent-owner", "test-repo"
                )

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_count_parent_not_found(
        self, client, fork_repo_data
    ):
        """Test error handling when parent repository is not found."""
        # Mock fork repo success but parent repo 404
        respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork_repo_data)
        )
        respx.get("https://api.github.com/repos/nonexistent-parent/test-repo").mock(
            return_value=httpx.Response(404, json={"message": "Not Found"})
        )

        async with client:
            with pytest.raises(GitHubPrivateRepositoryError):
                await client.get_commits_ahead_count(
                    "fork-owner", "test-repo", "nonexistent-parent", "test-repo"
                )

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_count_comparison_fails(
        self, client, fork_repo_data, parent_repo_data
    ):
        """Test error handling when comparison fails (e.g., divergent histories)."""
        # Mock repos success but comparison fails
        respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork_repo_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        respx.get(
            "https://api.github.com/repos/parent-owner/test-repo/compare/main...fork-owner:main"
        ).mock(return_value=httpx.Response(404, json={"message": "Not Found"}))

        async with client:
            # Should return 0 when comparison fails (handled by compare_commits_safe)
            count = await client.get_commits_ahead_count(
                "fork-owner", "test-repo", "parent-owner", "test-repo"
            )
            assert count == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_count_rate_limit_error(
        self, client, fork_repo_data, parent_repo_data
    ):
        """Test error handling when rate limit is exceeded."""
        # Mock rate limit error
        respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            return_value=httpx.Response(
                403,
                json={"message": "API rate limit exceeded"},
                headers={
                    "x-ratelimit-remaining": "0",
                    "x-ratelimit-limit": "5000",
                },
            )
        )

        async with client:
            with pytest.raises(GitHubRateLimitError):
                await client.get_commits_ahead_count(
                    "fork-owner", "test-repo", "parent-owner", "test-repo"
                )

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_count_authentication_error(self, client):
        """Test error handling when authentication fails."""
        # Mock authentication error
        respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            return_value=httpx.Response(401, json={"message": "Bad credentials"})
        )

        async with client:
            with pytest.raises(GitHubAuthenticationError):
                await client.get_commits_ahead_count(
                    "fork-owner", "test-repo", "parent-owner", "test-repo"
                )

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_count_server_error(self, client):
        """Test error handling when server returns 500 error."""
        # Mock server error
        respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            return_value=httpx.Response(500, json={"message": "Internal Server Error"})
        )

        async with client:
            with pytest.raises(GitHubAPIError):
                await client.get_commits_ahead_count(
                    "fork-owner", "test-repo", "parent-owner", "test-repo"
                )

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_batch_counts_partial_failures(
        self, client, parent_repo_data
    ):
        """Test batch counting with some forks failing to fetch."""
        fork_data_list = [
            ("fork1-owner", "test-repo"),  # Success
            ("fork2-owner", "test-repo"),  # Failure (404)
            ("fork3-owner", "test-repo"),  # Success
        ]

        fork1_data = {
            **parent_repo_data,
            "full_name": "fork1-owner/test-repo",
            "owner": {"login": "fork1-owner"},
        }
        fork3_data = {
            **parent_repo_data,
            "full_name": "fork3-owner/test-repo",
            "owner": {"login": "fork3-owner"},
        }

        comparison_data = {"ahead_by": 5, "behind_by": 0, "commits": []}

        # Mock API calls - fork2 returns 404
        respx.get("https://api.github.com/repos/fork1-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork1_data)
        )
        respx.get("https://api.github.com/repos/fork2-owner/test-repo").mock(
            return_value=httpx.Response(404, json={"message": "Not Found"})
        )
        respx.get("https://api.github.com/repos/fork3-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork3_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        respx.get(
            "https://api.github.com/repos/parent-owner/test-repo/compare/main...fork1-owner:main"
        ).mock(return_value=httpx.Response(200, json=comparison_data))
        respx.get(
            "https://api.github.com/repos/parent-owner/test-repo/compare/main...fork3-owner:main"
        ).mock(return_value=httpx.Response(200, json=comparison_data))

        async with client:
            result = await client.get_commits_ahead_batch_counts(
                fork_data_list, "parent-owner", "test-repo"
            )

            # Should only include successful forks
            assert len(result) == 2
            assert "fork1-owner/test-repo" in result
            assert "fork3-owner/test-repo" in result
            assert "fork2-owner/test-repo" not in result
            assert result["fork1-owner/test-repo"] == 5
            assert result["fork3-owner/test-repo"] == 5

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_batch_counts_comparison_failures(
        self, client, parent_repo_data
    ):
        """Test batch counting with some comparisons failing."""
        fork_data_list = [
            ("fork1-owner", "test-repo"),  # Success
            ("fork2-owner", "test-repo"),  # Comparison fails
        ]

        fork1_data = {
            **parent_repo_data,
            "full_name": "fork1-owner/test-repo",
            "owner": {"login": "fork1-owner"},
        }
        fork2_data = {
            **parent_repo_data,
            "full_name": "fork2-owner/test-repo",
            "owner": {"login": "fork2-owner"},
        }

        comparison_data_success = {"ahead_by": 10, "behind_by": 0, "commits": []}

        # Mock API calls
        respx.get("https://api.github.com/repos/fork1-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork1_data)
        )
        respx.get("https://api.github.com/repos/fork2-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork2_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        respx.get(
            "https://api.github.com/repos/parent-owner/test-repo/compare/main...fork1-owner:main"
        ).mock(return_value=httpx.Response(200, json=comparison_data_success))
        respx.get(
            "https://api.github.com/repos/parent-owner/test-repo/compare/main...fork2-owner:main"
        ).mock(return_value=httpx.Response(404, json={"message": "Not Found"}))

        async with client:
            result = await client.get_commits_ahead_batch_counts(
                fork_data_list, "parent-owner", "test-repo"
            )

            # Should include both forks, with failed comparison returning 0
            assert len(result) == 2
            assert result["fork1-owner/test-repo"] == 10
            assert result["fork2-owner/test-repo"] == 0  # Failed comparison returns 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_batch_counts_network_timeout(
        self, client, parent_repo_data
    ):
        """Test batch counting with network timeout errors."""
        fork_data_list = [("fork-owner", "test-repo")]

        # Mock parent repo success
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )

        # Mock fork repo with timeout
        respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            side_effect=httpx.TimeoutException("Request timeout")
        )

        async with client:
            # Should handle timeout gracefully and not include failed fork
            result = await client.get_commits_ahead_batch_counts(
                fork_data_list, "parent-owner", "test-repo"
            )
            assert len(result) == 0  # No successful forks

    @pytest.mark.asyncio
    async def test_get_commits_ahead_count_invalid_parameters(self, client):
        """Test error handling with invalid parameters."""
        async with client:
            # Test with empty strings - should raise GitHubAPIError or similar
            with pytest.raises((GitHubAPIError, ValueError)):
                await client.get_commits_ahead_count(
                    "", "test-repo", "parent-owner", "test-repo"
                )

            with pytest.raises((GitHubAPIError, ValueError)):
                await client.get_commits_ahead_count(
                    "fork-owner", "", "parent-owner", "test-repo"
                )

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_count_malformed_response(
        self, client, fork_repo_data, parent_repo_data
    ):
        """Test error handling with malformed API responses."""
        # Mock repos success but malformed comparison response
        respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork_repo_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        respx.get(
            "https://api.github.com/repos/parent-owner/test-repo/compare/main...fork-owner:main"
        ).mock(return_value=httpx.Response(200, json={"invalid": "response"}))

        async with client:
            # Should handle malformed response gracefully
            count = await client.get_commits_ahead_count(
                "fork-owner", "test-repo", "parent-owner", "test-repo"
            )
            assert count == 0  # Should return 0 for malformed response

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_batch_counts_all_failures(
        self, client, parent_repo_data
    ):
        """Test batch counting when all forks fail to fetch."""
        fork_data_list = [
            ("fork1-owner", "test-repo"),
            ("fork2-owner", "test-repo"),
        ]

        # Mock parent repo success
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )

        # Mock all forks with 404
        respx.get("https://api.github.com/repos/fork1-owner/test-repo").mock(
            return_value=httpx.Response(404, json={"message": "Not Found"})
        )
        respx.get("https://api.github.com/repos/fork2-owner/test-repo").mock(
            return_value=httpx.Response(404, json={"message": "Not Found"})
        )

        async with client:
            result = await client.get_commits_ahead_batch_counts(
                fork_data_list, "parent-owner", "test-repo"
            )
            assert len(result) == 0  # No successful forks

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_batch_counts_parent_failure(self, client):
        """Test batch counting when parent repository fetch fails."""
        fork_data_list = [("fork-owner", "test-repo")]

        # Mock parent repo failure
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(404, json={"message": "Not Found"})
        )

        async with client:
            with pytest.raises(GitHubPrivateRepositoryError):
                await client.get_commits_ahead_batch_counts(
                    fork_data_list, "parent-owner", "test-repo"
                )

    # Test edge cases and boundary conditions

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_count_identical_repositories(
        self, client, parent_repo_data
    ):
        """Test counting when fork and parent are identical."""
        comparison_data = {
            "ahead_by": 0,
            "behind_by": 0,
            "total_commits": 0,
            "status": "identical",
            "commits": [],
        }

        # Mock API calls - same repo for both fork and parent
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        respx.get(
            "https://api.github.com/repos/parent-owner/test-repo/compare/main...parent-owner:main"
        ).mock(return_value=httpx.Response(200, json=comparison_data))

        async with client:
            count = await client.get_commits_ahead_count(
                "parent-owner", "test-repo", "parent-owner", "test-repo"
            )
            assert count == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_count_very_large_numbers(
        self, client, fork_repo_data, parent_repo_data
    ):
        """Test counting with very large commit numbers."""
        comparison_data = {
            "ahead_by": 999999,
            "behind_by": 0,
            "total_commits": 999999,
            "status": "ahead",
            "commits": [],
        }

        # Mock API calls
        respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork_repo_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        respx.get(
            "https://api.github.com/repos/parent-owner/test-repo/compare/main...fork-owner:main"
        ).mock(return_value=httpx.Response(200, json=comparison_data))

        async with client:
            count = await client.get_commits_ahead_count(
                "fork-owner", "test-repo", "parent-owner", "test-repo"
            )
            assert count == 999999

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_count_string_ahead_by_field(
        self, client, fork_repo_data, parent_repo_data
    ):
        """Test counting when ahead_by field is a string (should be converted to int)."""
        comparison_data = {
            "ahead_by": "42",  # String instead of int
            "behind_by": 0,
            "total_commits": 42,
            "status": "ahead",
            "commits": [],
        }

        # Mock API calls
        respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork_repo_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        respx.get(
            "https://api.github.com/repos/parent-owner/test-repo/compare/main...fork-owner:main"
        ).mock(return_value=httpx.Response(200, json=comparison_data))

        async with client:
            count = await client.get_commits_ahead_count(
                "fork-owner", "test-repo", "parent-owner", "test-repo"
            )
            assert count == 42  # Should convert string to int
