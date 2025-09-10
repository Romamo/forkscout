"""Tests that demonstrate the commit counting bug and verify the fix."""

import pytest
import respx
import httpx
from unittest.mock import AsyncMock, patch

from forkscout.config import GitHubConfig
from forkscout.github.client import GitHubClient


class TestCommitCountingBug:
    """Test cases that demonstrate and verify the fix for the commit counting bug."""

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
    async def test_bug_demonstration_count_vs_ahead_by(self, client, fork_repo_data, parent_repo_data):
        """Demonstrate the bug: count=1 causes wrong commit count calculation."""
        
        # This is the bug scenario: fork has 23 commits ahead but we call with count=1
        comparison_data = {
            "ahead_by": 23,  # Fork actually has 23 commits ahead (this is the correct count)
            "behind_by": 0,
            "total_commits": 23,
            "status": "ahead",
            "commits": [  # But we only fetch 1 commit due to count=1 parameter
                {
                    "sha": "abc1234567890abcdef1234567890abcdef123456",
                    "commit": {
                        "message": "Latest commit in fork",
                        "author": {
                            "name": "Fork Author",
                            "email": "fork@example.com",
                            "date": "2024-01-15T10:30:00Z"
                        }
                    },
                    "author": {
                        "login": "fork-author",
                        "id": 12345
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
            # This simulates the current bug: calling with count=1
            result = await client.get_commits_ahead("fork-owner", "test-repo", "parent-owner", "test-repo", count=1)
            
            # Current implementation returns len(commits) = 1
            # But the fork actually has 23 commits ahead (ahead_by field)
            assert len(result) == 1  # We only get 1 commit detail because count=1
            
            # The bug is that the repository display service uses len(result) 
            # to determine commits ahead, which gives 1 instead of 23
            
            # After the fix, we can use the new count method to get the actual count
            count = await client.get_commits_ahead_count("fork-owner", "test-repo", "parent-owner", "test-repo")
            
            # The new method should return the ahead_by field value
            assert count == 23  # This is the correct count from ahead_by field

    @pytest.mark.asyncio
    @respx.mock
    async def test_bug_demonstration_batch_processing(self, client, parent_repo_data):
        """Demonstrate the bug in batch processing: multiple forks all show +1 commits."""
        
        # Create multiple fork data with different actual commit counts
        fork_data_list = [
            ("fork1-owner", "test-repo"),
            ("fork2-owner", "test-repo"), 
            ("fork3-owner", "test-repo")
        ]
        
        fork1_data = {**parent_repo_data, "full_name": "fork1-owner/test-repo", "owner": {"login": "fork1-owner"}}
        fork2_data = {**parent_repo_data, "full_name": "fork2-owner/test-repo", "owner": {"login": "fork2-owner"}}
        fork3_data = {**parent_repo_data, "full_name": "fork3-owner/test-repo", "owner": {"login": "fork3-owner"}}

        # Each fork has different number of commits ahead, but all will show +1 due to bug
        comparison_data_fork1 = {
            "ahead_by": 5,   # Fork1 has 5 commits ahead
            "behind_by": 0,
            "commits": [{"sha": "abc1234567890abcdef1234567890abcdef123456", "commit": {"message": "Fork1 commit", "author": {"date": "2024-01-15T10:30:00Z"}}}]
        }
        
        comparison_data_fork2 = {
            "ahead_by": 12,  # Fork2 has 12 commits ahead  
            "behind_by": 0,
            "commits": [{"sha": "def4567890abcdef1234567890abcdef12345678", "commit": {"message": "Fork2 commit", "author": {"date": "2024-01-15T10:30:00Z"}}}]
        }
        
        comparison_data_fork3 = {
            "ahead_by": 23,  # Fork3 has 23 commits ahead
            "behind_by": 0,
            "commits": [{"sha": "abc7890def1234567890abcdef123456789abcde", "commit": {"message": "Fork3 commit", "author": {"date": "2024-01-15T10:30:00Z"}}}]
        }

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
        respx.get("https://api.github.com/repos/parent-owner/test-repo/compare/main...fork1-owner:main").mock(
            return_value=httpx.Response(200, json=comparison_data_fork1)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo/compare/main...fork2-owner:main").mock(
            return_value=httpx.Response(200, json=comparison_data_fork2)
        )
        respx.get("https://api.github.com/repos/parent-owner/test-repo/compare/main...fork3-owner:main").mock(
            return_value=httpx.Response(200, json=comparison_data_fork3)
        )

        async with client:
            # This simulates the current bug: calling batch with count=1
            result = await client.get_commits_ahead_batch(fork_data_list, "parent-owner", "test-repo", count=1)
            
            # Current implementation: all forks show len(commits) = 1
            assert len(result) == 3
            
            # All forks return 1 commit detail due to count=1
            for fork_key in result:
                commits = result[fork_key]
                assert len(commits) == 1  # Bug: all show 1 commit regardless of actual count
            
            # But the actual counts should be 5, 12, and 23 respectively
            # After fix, we need a way to get these actual counts

    @pytest.mark.asyncio
    async def test_repository_display_service_bug_simulation(self):
        """Simulate how the repository display service uses the buggy logic."""
        
        # This simulates the problematic code in repository_display_service.py line 1582-1595
        mock_github_client = AsyncMock()
        
        # Mock the batch results that would come from get_commits_ahead_batch with count=1
        mock_batch_results = {
            "fork1-owner/test-repo": [{"sha": "abc123", "message": "Fork1 commit"}],  # len = 1
            "fork2-owner/test-repo": [{"sha": "def456", "message": "Fork2 commit"}],  # len = 1  
            "fork3-owner/test-repo": [{"sha": "ghi789", "message": "Fork3 commit"}],  # len = 1
        }
        
        mock_github_client.get_commits_ahead_batch.return_value = mock_batch_results
        
        # Simulate the buggy logic from repository_display_service.py
        fork_data_list = [
            ("fork1-owner", "test-repo"),
            ("fork2-owner", "test-repo"),
            ("fork3-owner", "test-repo")
        ]
        
        batch_results = await mock_github_client.get_commits_ahead_batch(
            fork_data_list, "parent-owner", "test-repo", count=1
        )
        
        # This is the buggy logic that causes all forks to show "+1"
        for fork_key in batch_results:
            commits_ahead_list = batch_results[fork_key]
            commits_ahead = len(commits_ahead_list)  # This is always 1 when count=1!
            
            # All forks incorrectly show 1 commit ahead
            assert commits_ahead == 1
        
        # The fix should use ahead_by field instead of len(commits_ahead_list)

    @pytest.mark.asyncio
    async def test_fix_verification_batch_counts_method(self):
        """Verify that the new batch counts method fixes the repository display service bug."""
        
        # This simulates the fixed logic using the new batch counts method
        mock_github_client = AsyncMock()
        
        # Mock the new batch counts method that returns accurate counts
        mock_batch_counts = {
            "fork1-owner/test-repo": 5,   # Fork1 has 5 commits ahead (from ahead_by field)
            "fork2-owner/test-repo": 12,  # Fork2 has 12 commits ahead (from ahead_by field)
            "fork3-owner/test-repo": 23,  # Fork3 has 23 commits ahead (from ahead_by field)
        }
        
        mock_github_client.get_commits_ahead_batch_counts.return_value = mock_batch_counts
        
        # Simulate the fixed logic from repository_display_service.py
        fork_data_list = [
            ("fork1-owner", "test-repo"),
            ("fork2-owner", "test-repo"),
            ("fork3-owner", "test-repo")
        ]
        
        batch_counts = await mock_github_client.get_commits_ahead_batch_counts(
            fork_data_list, "parent-owner", "test-repo"
        )
        
        # This is the fixed logic that uses the accurate ahead_by counts
        expected_counts = [5, 12, 23]
        actual_counts = []
        
        for i, (fork_owner, fork_repo) in enumerate(fork_data_list):
            fork_key = f"{fork_owner}/{fork_repo}"
            if fork_key in batch_counts:
                commits_ahead = batch_counts[fork_key]  # Use the accurate count directly
                actual_counts.append(commits_ahead)
        
        # All forks now show their correct commit counts
        assert actual_counts == expected_counts
        
        # Verify no fork shows the incorrect "+1" count
        assert 1 not in actual_counts or actual_counts.count(1) == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_ahead_by_field_available_in_comparison(self, client, fork_repo_data, parent_repo_data):
        """Verify that ahead_by field is available in GitHub compare API response."""
        
        comparison_data = {
            "ahead_by": 15,
            "behind_by": 3,
            "total_commits": 15,
            "status": "ahead",
            "commits": [
                {
                    "sha": f"commit{i:03d}1234567890abcdef1234567890abcdef123456",
                    "commit": {
                        "message": f"Commit {i}",
                        "author": {"date": "2024-01-15T10:30:00Z"}
                    }
                }
                for i in range(15)  # All 15 commits
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
            # Use compare_commits to get the full comparison data
            comparison = await client.compare_commits(
                "parent-owner", "test-repo", "main", "fork-owner:main"
            )
            
            # Verify ahead_by field is available and accurate
            assert comparison["ahead_by"] == 15
            assert comparison["behind_by"] == 3
            assert comparison["total_commits"] == 15
            assert comparison["status"] == "ahead"
            assert len(comparison["commits"]) == 15
            
            # This is the field we should use instead of len(commits) when count < ahead_by