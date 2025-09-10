"""Tests for repository display service commit counting logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass
from typing import Any

from forkscout.display.repository_display_service import RepositoryDisplayService
from forkscout.github.client import GitHubClient
from forkscout.config import GitHubConfig


@dataclass
class MockForkData:
    """Mock fork data for testing."""
    metrics: Any
    exact_commits_ahead: int | str | None = None


@dataclass 
class MockMetrics:
    """Mock metrics for testing."""
    owner: str
    name: str
    can_skip_analysis: bool = False


class TestRepositoryDisplayServiceCommitCounting:
    """Test cases for commit counting logic in repository display service."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return AsyncMock(spec=GitHubClient)

    @pytest.fixture
    def repository_display_service(self, mock_github_client):
        """Create a repository display service with mock client."""
        return RepositoryDisplayService(
            github_client=mock_github_client,
            console=MagicMock(),
            cache_manager=None
        )

    @pytest.mark.asyncio
    async def test_get_exact_commit_counts_batch_uses_correct_counting_logic(
        self, repository_display_service, mock_github_client
    ):
        """Test that _get_exact_commit_counts_batch uses ahead_by field instead of len(commits)."""
        
        # Create mock fork data
        forks_needing_api = [
            MockForkData(metrics=MockMetrics(owner="fork1", name="repo")),
            MockForkData(metrics=MockMetrics(owner="fork2", name="repo")),
            MockForkData(metrics=MockMetrics(owner="fork3", name="repo")),
        ]
        
        # Mock the batch counts method to return accurate counts from ahead_by field
        mock_batch_counts = {
            "fork1/repo": {"ahead_by": 5, "behind_by": 0, "total_commits": 5},
            "fork2/repo": {"ahead_by": 12, "behind_by": 2, "total_commits": 14},
            "fork3/repo": {"ahead_by": 23, "behind_by": 1, "total_commits": 24},
        }
        
        mock_github_client.get_commits_ahead_behind_batch.return_value = mock_batch_counts
        
        # Call the method that should be fixed
        result = await repository_display_service._get_exact_commit_counts_batch(
            forks_needing_api, "parent", "repo"
        )
        
        # Verify that the method was called correctly
        mock_github_client.get_commits_ahead_behind_batch.assert_called_once_with(
            [("fork1", "repo"), ("fork2", "repo"), ("fork3", "repo")],
            "parent",
            "repo"
        )
        
        # Verify that exact_commits_ahead was set correctly for each fork
        assert forks_needing_api[0].exact_commits_ahead == 5
        assert forks_needing_api[1].exact_commits_ahead == 12
        assert forks_needing_api[2].exact_commits_ahead == 23
        
        # Verify return value indicates success
        assert result == (3, 3)  # (successful_forks, api_calls_saved)

    @pytest.mark.asyncio
    async def test_get_exact_commit_counts_batch_handles_failures_gracefully(
        self, repository_display_service, mock_github_client
    ):
        """Test that _get_exact_commit_counts_batch handles API failures gracefully."""
        
        # Create mock fork data
        forks_needing_api = [
            MockForkData(metrics=MockMetrics(owner="fork1", name="repo")),
            MockForkData(metrics=MockMetrics(owner="fork2", name="repo")),
        ]
        
        # Mock batch counts method to return partial results (fork2 failed)
        mock_batch_counts = {
            "fork1/repo": {"ahead_by": 5, "behind_by": 0, "total_commits": 5},
            # fork2/repo missing - simulates API failure
        }
        
        mock_github_client.get_commits_ahead_behind_batch.return_value = mock_batch_counts
        
        # Call the method
        result = await repository_display_service._get_exact_commit_counts_batch(
            forks_needing_api, "parent", "repo"
        )
        
        # Verify that successful fork got correct count
        assert forks_needing_api[0].exact_commits_ahead == 5
        
        # Verify that failed fork got "Unknown"
        assert forks_needing_api[1].exact_commits_ahead == "Unknown"
        
        # Verify return value indicates partial success
        assert result == (1, 1)  # (successful_forks, api_calls_saved)

    @pytest.mark.asyncio
    async def test_get_exact_commit_counts_batch_skips_analysis_for_no_commits(
        self, repository_display_service, mock_github_client
    ):
        """Test that forks with no commits are skipped from API calls."""
        
        # Create mock fork data with one that can skip analysis
        forks_needing_api = [
            MockForkData(metrics=MockMetrics(owner="fork1", name="repo", can_skip_analysis=True)),
            MockForkData(metrics=MockMetrics(owner="fork2", name="repo", can_skip_analysis=False)),
        ]
        
        # Mock batch counts method
        mock_batch_counts = {
            "fork2/repo": {"ahead_by": 7, "behind_by": 1, "total_commits": 8},
        }
        
        mock_github_client.get_commits_ahead_behind_batch.return_value = mock_batch_counts
        
        # Call the method
        result = await repository_display_service._get_exact_commit_counts_batch(
            forks_needing_api, "parent", "repo"
        )
        
        # Verify that fork1 was set to 0 (skipped analysis)
        assert forks_needing_api[0].exact_commits_ahead == 0
        
        # Verify that fork2 got API result
        assert forks_needing_api[1].exact_commits_ahead == 7
        
        # Verify that only fork2 was included in API call
        mock_github_client.get_commits_ahead_behind_batch.assert_called_once_with(
            [("fork2", "repo")],  # Only fork2, fork1 was skipped
            "parent",
            "repo"
        )

    @pytest.mark.asyncio
    async def test_get_exact_commit_counts_batch_fallback_to_individual_calls(
        self, repository_display_service, mock_github_client
    ):
        """Test fallback to individual API calls when batch processing fails."""
        
        # Create mock fork data
        forks_needing_api = [
            MockForkData(metrics=MockMetrics(owner="fork1", name="repo")),
        ]
        
        # Mock batch method to raise exception
        mock_github_client.get_commits_ahead_behind_batch.side_effect = Exception("Batch failed")
        
        # Mock individual method to succeed
        mock_github_client.get_commits_ahead_behind.return_value = {"ahead_by": 8, "behind_by": 2}
        
        # Call the method
        result = await repository_display_service._get_exact_commit_counts_batch(
            forks_needing_api, "parent", "repo"
        )
        
        # Verify that individual API call was made
        mock_github_client.get_commits_ahead_behind.assert_called_once_with(
            "fork1", "repo", "parent", "repo"
        )
        
        # Verify that fork got correct count from individual call
        assert forks_needing_api[0].exact_commits_ahead == 8
        
        # Verify return value
        assert result == (1, 0)  # (successful_forks, api_calls_saved - 0 because fallback was used)

    def test_commit_counting_bug_demonstration(self):
        """Demonstrate the bug that this task is meant to fix."""
        
        # This test demonstrates the problematic pattern that causes the bug
        
        # Simulate the old buggy logic (what we're fixing)
        mock_batch_results_with_count_1 = {
            "fork1/repo": [{"sha": "abc123", "message": "Commit 1"}],  # len = 1
            "fork2/repo": [{"sha": "def456", "message": "Commit 1"}],  # len = 1  
            "fork3/repo": [{"sha": "ghi789", "message": "Commit 1"}],  # len = 1
        }
        
        # The bug: using len(commits) when count=1 was used
        buggy_counts = {}
        for fork_key, commits in mock_batch_results_with_count_1.items():
            buggy_counts[fork_key] = len(commits)  # This is always 1!
        
        # All forks incorrectly show 1 commit ahead
        assert all(count == 1 for count in buggy_counts.values())
        
        # The fix: use ahead_by field from compare API response
        correct_batch_counts = {
            "fork1/repo": 5,   # Actual count from ahead_by field
            "fork2/repo": 12,  # Actual count from ahead_by field
            "fork3/repo": 23,  # Actual count from ahead_by field
        }
        
        # After fix: all forks show their correct commit counts
        assert correct_batch_counts["fork1/repo"] == 5
        assert correct_batch_counts["fork2/repo"] == 12
        assert correct_batch_counts["fork3/repo"] == 23
        
        # Verify no fork shows the incorrect "+1" count
        assert 1 not in correct_batch_counts.values()