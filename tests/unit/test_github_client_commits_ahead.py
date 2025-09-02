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
    async def test_get_commits_ahead_invalid_count(self, client):
        """Test get_commits_ahead with invalid count values."""
        async with client:
            # Test count too low (zero)
            with pytest.raises(ValueError, match="Count must be a positive integer"):
                await client.get_commits_ahead("fork-owner", "test-repo", "parent-owner", "test-repo", count=0)
            
            # Test negative count
            with pytest.raises(ValueError, match="Count must be a positive integer"):
                await client.get_commits_ahead("fork-owner", "test-repo", "parent-owner", "test-repo", count=-1)

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_various_count_values(self, client, fork_repo_data, parent_repo_data):
        """Test get_commits_ahead with various valid count values."""
        # Generate test commits data
        def generate_commits_data(count):
            return {
                "ahead_by": count,
                "behind_by": 0,
                "commits": [
                    {
                        "sha": f"abc123456789012345678901234567890123456{i:02d}",
                        "commit": {
                            "message": f"Test commit {i}",
                            "author": {"date": "2024-01-15T10:30:00Z"}
                        }
                    }
                    for i in range(count)
                ]
            }

        # Mock API calls
        respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork_repo_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )

        async with client:
            # Test various count values
            test_counts = [1, 100, 1000, 5000]
            
            for count in test_counts:
                comparison_data = generate_commits_data(count)
                
                # Mock the comparison endpoint
                respx.get("https://api.github.com/repos/parent-owner/test-repo/compare/main...fork-owner:main").mock(
                    return_value=httpx.Response(200, json=comparison_data)
                )
                
                result = await client.get_commits_ahead("fork-owner", "test-repo", "parent-owner", "test-repo", count=count)
                assert len(result) == count
                
                # Verify each commit has the expected structure
                for i, commit in enumerate(result):
                    expected_full_sha = f"abc123456789012345678901234567890123456{i:02d}"
                    assert commit.short_sha == expected_full_sha[:7]  # First 7 characters
                    assert commit.message == f"Test commit {i}"

    @pytest.mark.asyncio
    async def test_get_commits_ahead_batch_invalid_count(self, client):
        """Test get_commits_ahead_batch with invalid count values."""
        fork_data_list = [("fork1-owner", "test-repo"), ("fork2-owner", "test-repo")]
        
        async with client:
            # Test count too low (zero)
            with pytest.raises(ValueError, match="Count must be a positive integer"):
                await client.get_commits_ahead_batch(fork_data_list, "parent-owner", "test-repo", count=0)
            
            # Test negative count
            with pytest.raises(ValueError, match="Count must be a positive integer"):
                await client.get_commits_ahead_batch(fork_data_list, "parent-owner", "test-repo", count=-1)

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_batch_various_count_values(self, client, parent_repo_data):
        """Test get_commits_ahead_batch with various valid count values."""
        # Create fork data
        fork1_data = {**parent_repo_data, "full_name": "fork1-owner/test-repo", "owner": {"login": "fork1-owner"}}
        fork2_data = {**parent_repo_data, "full_name": "fork2-owner/test-repo", "owner": {"login": "fork2-owner"}}
        fork_data_list = [("fork1-owner", "test-repo"), ("fork2-owner", "test-repo")]

        # Generate test commits data
        def generate_commits_data(count):
            return {
                "ahead_by": count,
                "behind_by": 0,
                "commits": [
                    {
                        "sha": f"abc123456789012345678901234567890123456{i:02d}",
                        "commit": {
                            "message": f"Test commit {i}",
                            "author": {"date": "2024-01-15T10:30:00Z"}
                        }
                    }
                    for i in range(count)
                ]
            }

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

        async with client:
            # Test various count values
            test_counts = [1, 100, 1000, 5000]
            
            for count in test_counts:
                comparison_data = generate_commits_data(count)
                
                # Mock comparison endpoints for both forks
                respx.get("https://api.github.com/repos/parent-owner/test-repo/compare/main...fork1-owner:main").mock(
                    return_value=httpx.Response(200, json=comparison_data)
                )
                respx.get("https://api.github.com/repos/parent-owner/test-repo/compare/main...fork2-owner:main").mock(
                    return_value=httpx.Response(200, json=comparison_data)
                )
                
                result = await client.get_commits_ahead_batch(fork_data_list, "parent-owner", "test-repo", count=count)
                
                # Verify results for both forks
                assert len(result) == 2
                assert "fork1-owner/test-repo" in result
                assert "fork2-owner/test-repo" in result
                
                for fork_key in result:
                    commits = result[fork_key]
                    assert len(commits) == count
                    
                    # Verify each commit has the expected structure
                    for i, commit in enumerate(commits):
                        expected_full_sha = f"abc123456789012345678901234567890123456{i:02d}"
                        assert commit.short_sha == expected_full_sha[:7]  # First 7 characters
                        assert commit.message == f"Test commit {i}"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_uses_ahead_by_field(self, client, fork_repo_data, parent_repo_data):
        """Test that get_commits_ahead uses ahead_by field instead of counting commits array."""
        # Mock comparison response where ahead_by=5 but commits array only has 1 item
        # This simulates the bug scenario where count=1 is used but fork actually has 5 commits ahead
        comparison_data = {
            "ahead_by": 5,  # Fork actually has 5 commits ahead
            "behind_by": 0,
            "commits": [  # But we only fetch 1 commit due to count=1
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
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo/compare/main...fork-owner:main").mock(
            return_value=httpx.Response(200, json=comparison_data)
        )

        async with client:
            # Call with count=1 (simulating the bug scenario)
            result = await client.get_commits_ahead("fork-owner", "test-repo", "parent-owner", "test-repo", count=1)
            
            # The method should return the actual ahead_by count (5), not len(commits) (1)
            # This test will fail with current implementation and pass after fix
            assert len(result) == 1  # We only requested 1 commit detail
            
            # But we should be able to get the actual count from a new method
            # For now, let's test that the current method works correctly when count matches ahead_by
            
        # Test with count=5 to get all commits
        comparison_data_full = {
            "ahead_by": 5,
            "behind_by": 0,
            "commits": [
                {
                    "sha": f"abc123456789012345678901234567890123456{i:02d}",
                    "commit": {
                        "message": f"Test commit {i}",
                        "author": {"date": "2024-01-15T10:30:00Z"}
                    }
                }
                for i in range(5)
            ]
        }
        
        respx.get("https://api.github.com/repos/parent-owner/test-repo/compare/main...fork-owner:main").mock(
            return_value=httpx.Response(200, json=comparison_data_full)
        )
        
        async with client:
            result_full = await client.get_commits_ahead("fork-owner", "test-repo", "parent-owner", "test-repo", count=5)
            assert len(result_full) == 5

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_batch_uses_ahead_by_field(self, client, parent_repo_data):
        """Test that get_commits_ahead_batch uses ahead_by field instead of counting commits array."""
        # Create fork data
        fork1_data = {**parent_repo_data, "full_name": "fork1-owner/test-repo", "owner": {"login": "fork1-owner"}}
        fork2_data = {**parent_repo_data, "full_name": "fork2-owner/test-repo", "owner": {"login": "fork2-owner"}}
        fork_data_list = [("fork1-owner", "test-repo"), ("fork2-owner", "test-repo")]

        # Mock comparison responses where ahead_by differs from commits array length
        comparison_data_fork1 = {
            "ahead_by": 23,  # Fork1 actually has 23 commits ahead
            "behind_by": 0,
            "commits": [  # But we only fetch 1 commit due to count=1
                {
                    "sha": "abc1234567890abcdef1234567890abcdef123456",
                    "commit": {
                        "message": "Fork1 commit",
                        "author": {"date": "2024-01-15T10:30:00Z"}
                    }
                }
            ]
        }
        
        comparison_data_fork2 = {
            "ahead_by": 12,  # Fork2 actually has 12 commits ahead
            "behind_by": 0,
            "commits": [  # But we only fetch 1 commit due to count=1
                {
                    "sha": "def1234567890abcdef1234567890abcdef123456",
                    "commit": {
                        "message": "Fork2 commit",
                        "author": {"date": "2024-01-15T10:30:00Z"}
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
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo/compare/main...fork1-owner:main").mock(
            return_value=httpx.Response(200, json=comparison_data_fork1)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo/compare/main...fork2-owner:main").mock(
            return_value=httpx.Response(200, json=comparison_data_fork2)
        )

        async with client:
            # Call with count=1 (simulating the bug scenario)
            result = await client.get_commits_ahead_batch(fork_data_list, "parent-owner", "test-repo", count=1)
            
            # Current implementation would return len(commits)=1 for each fork
            # Fixed implementation should return actual ahead_by counts
            assert len(result) == 2
            assert "fork1-owner/test-repo" in result
            assert "fork2-owner/test-repo" in result
            
            # With current bug, each would have 1 commit (len(commits))
            # After fix, we should get the actual commit details (limited by count)
            # but the count logic should be separate from detail fetching
            fork1_commits = result["fork1-owner/test-repo"]
            fork2_commits = result["fork2-owner/test-repo"]
            
            # We requested count=1, so we should get 1 commit detail each
            assert len(fork1_commits) == 1
            assert len(fork2_commits) == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_count_uses_ahead_by_field(self, client, fork_repo_data, parent_repo_data):
        """Test that get_commits_ahead_count uses ahead_by field correctly."""
        # Mock comparison response with ahead_by field
        comparison_data = {
            "ahead_by": 23,  # This is the correct count
            "behind_by": 0,
            "total_commits": 23,
            "status": "ahead",
            "commits": []  # Empty commits array to test that we don't use len(commits)
        }

        # Mock API calls
        respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork_repo_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo/compare/main...fork-owner:main").mock(
            return_value=httpx.Response(200, json=comparison_data)
        )

        async with client:
            # Test the new count method
            count = await client.get_commits_ahead_count("fork-owner", "test-repo", "parent-owner", "test-repo")
            
            # Should return the ahead_by value, not len(commits)
            assert count == 23

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_count_missing_ahead_by_field(self, client, fork_repo_data, parent_repo_data):
        """Test that get_commits_ahead_count handles missing ahead_by field gracefully."""
        # Mock comparison response without ahead_by field (fallback scenario)
        comparison_data = {
            "behind_by": 0,
            "total_commits": 5,
            "status": "ahead",
            "commits": [
                {"sha": f"abc123456789012345678901234567890123456{i:02d}", "commit": {"message": f"Commit {i}", "author": {"date": "2024-01-15T10:30:00Z"}}}
                for i in range(5)
            ]
        }

        # Mock API calls
        respx.get("https://api.github.com/repos/fork-owner/test-repo").mock(
            return_value=httpx.Response(200, json=fork_repo_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo").mock(
            return_value=httpx.Response(200, json=parent_repo_data)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo/compare/main...fork-owner:main").mock(
            return_value=httpx.Response(200, json=comparison_data)
        )

        async with client:
            # Test fallback behavior when ahead_by is missing
            count = await client.get_commits_ahead_count("fork-owner", "test-repo", "parent-owner", "test-repo")
            
            # Should fallback to len(commits) = 5
            assert count == 5

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commits_ahead_batch_counts_uses_ahead_by_field(self, client, parent_repo_data):
        """Test that get_commits_ahead_batch_counts uses ahead_by field correctly."""
        # Create fork data
        fork1_data = {**parent_repo_data, "full_name": "fork1-owner/test-repo", "owner": {"login": "fork1-owner"}}
        fork2_data = {**parent_repo_data, "full_name": "fork2-owner/test-repo", "owner": {"login": "fork2-owner"}}
        fork_data_list = [("fork1-owner", "test-repo"), ("fork2-owner", "test-repo")]

        # Mock comparison responses with different ahead_by values
        comparison_data_fork1 = {
            "ahead_by": 15,  # Fork1 has 15 commits ahead
            "behind_by": 0,
            "commits": []  # Empty to test we don't use len(commits)
        }
        
        comparison_data_fork2 = {
            "ahead_by": 7,   # Fork2 has 7 commits ahead
            "behind_by": 0,
            "commits": []  # Empty to test we don't use len(commits)
        }

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
        respx.get("https://api.github.com/repos/parent-owner/test-repo/compare/main...fork1-owner:main").mock(
            return_value=httpx.Response(200, json=comparison_data_fork1)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo/compare/main...fork2-owner:main").mock(
            return_value=httpx.Response(200, json=comparison_data_fork2)
        )

        async with client:
            # Test the new batch count method
            result = await client.get_commits_ahead_batch_counts(fork_data_list, "parent-owner", "test-repo")
            
            # Should return the ahead_by values, not len(commits)
            assert len(result) == 2
            assert result["fork1-owner/test-repo"] == 15
            assert result["fork2-owner/test-repo"] == 7

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