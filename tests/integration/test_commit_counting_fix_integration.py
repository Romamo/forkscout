"""Integration tests for the commit counting fix."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass
from typing import Any

from forkscout.display.repository_display_service import RepositoryDisplayService
from forkscout.github.client import GitHubClient
from forkscout.config import GitHubConfig


@dataclass
class MockForkData:
    """Mock fork data for integration testing."""
    metrics: Any
    exact_commits_ahead: int | str | None = None


@dataclass 
class MockMetrics:
    """Mock metrics for integration testing."""
    owner: str
    name: str
    can_skip_analysis: bool = False
    stargazers_count: int = 0
    forks_count: int = 0
    pushed_at: Any = None


class TestCommitCountingFixIntegration:
    """Integration tests for the commit counting fix."""

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
    async def test_commit_counting_fix_end_to_end(
        self, repository_display_service, mock_github_client
    ):
        """Test that the commit counting fix works end-to-end."""
        
        # Create mock fork data that would previously show "+1" for all forks
        forks_needing_api = [
            MockForkData(metrics=MockMetrics(owner="fork1", name="repo")),
            MockForkData(metrics=MockMetrics(owner="fork2", name="repo")),
            MockForkData(metrics=MockMetrics(owner="fork3", name="repo")),
        ]
        
        # Mock the batch counts method to return the CORRECT counts from ahead_by field
        # This simulates the fix where we use ahead_by instead of len(commits) with count=1
        mock_batch_counts = {
            "fork1/repo": 5,   # Fork1 has 5 commits ahead (from ahead_by field)
            "fork2/repo": 12,  # Fork2 has 12 commits ahead (from ahead_by field)
            "fork3/repo": 23,  # Fork3 has 23 commits ahead (from ahead_by field)
        }
        
        mock_github_client.get_commits_ahead_batch_counts.return_value = mock_batch_counts
        
        # Call the fixed method
        successful_forks, api_calls_saved = await repository_display_service._get_exact_commit_counts_batch(
            forks_needing_api, "parent", "repo"
        )
        
        # Verify that the method was called with the correct parameters
        mock_github_client.get_commits_ahead_batch_counts.assert_called_once_with(
            [("fork1", "repo"), ("fork2", "repo"), ("fork3", "repo")],
            "parent",
            "repo"
        )
        
        # Verify that exact_commits_ahead was set correctly for each fork
        # This is the key fix: instead of all showing 1, they show their actual counts
        assert forks_needing_api[0].exact_commits_ahead == 5
        assert forks_needing_api[1].exact_commits_ahead == 12
        assert forks_needing_api[2].exact_commits_ahead == 23
        
        # Verify return values
        assert successful_forks == 3
        assert api_calls_saved == 3
        
        # Verify that no fork shows the buggy "+1" count
        actual_counts = [fork.exact_commits_ahead for fork in forks_needing_api]
        assert 1 not in actual_counts  # The bug would have made all counts = 1

    @pytest.mark.asyncio
    async def test_commit_counting_fix_demonstrates_bug_resolution(
        self, repository_display_service, mock_github_client
    ):
        """Test that demonstrates how the fix resolves the original bug."""
        
        # Simulate the scenario from the bug report:
        # Repository: sanila2007/youtube-bot-telegram
        # Command: uv run forklift show-forks https://github.com/sanila2007/youtube-bot-telegram --detail --ahead-only
        # Bug: All forks showed "+1" commits ahead regardless of actual count
        
        # Create mock fork data representing forks that actually have different commit counts
        forks_needing_api = [
            MockForkData(metrics=MockMetrics(owner="user1", name="youtube-bot-telegram")),
            MockForkData(metrics=MockMetrics(owner="user2", name="youtube-bot-telegram")),
            MockForkData(metrics=MockMetrics(owner="user3", name="youtube-bot-telegram")),
        ]
        
        # Mock the GitHub compare API responses that would return ahead_by field
        # These represent the ACTUAL commit counts that were being ignored due to the bug
        mock_batch_counts = {
            "user1/youtube-bot-telegram": 3,   # User1 fork has 3 commits ahead
            "user2/youtube-bot-telegram": 7,   # User2 fork has 7 commits ahead  
            "user3/youtube-bot-telegram": 15,  # User3 fork has 15 commits ahead
        }
        
        mock_github_client.get_commits_ahead_batch_counts.return_value = mock_batch_counts
        
        # Call the fixed method
        await repository_display_service._get_exact_commit_counts_batch(
            forks_needing_api, "sanila2007", "youtube-bot-telegram"
        )
        
        # Before the fix: all forks would show exact_commits_ahead = 1
        # After the fix: forks show their actual commit counts
        
        assert forks_needing_api[0].exact_commits_ahead == 3   # Not 1!
        assert forks_needing_api[1].exact_commits_ahead == 7   # Not 1!
        assert forks_needing_api[2].exact_commits_ahead == 15  # Not 1!
        
        # Verify that the display would now show "+3", "+7", "+15" instead of "+1", "+1", "+1"
        display_values = []
        for fork in forks_needing_api:
            if isinstance(fork.exact_commits_ahead, int) and fork.exact_commits_ahead > 0:
                display_values.append(f"+{fork.exact_commits_ahead}")
        
        expected_display = ["+3", "+7", "+15"]
        assert display_values == expected_display
        
        # The bug would have produced ["+1", "+1", "+1"] instead

    @pytest.mark.asyncio
    async def test_commit_counting_fix_handles_mixed_scenarios(
        self, repository_display_service, mock_github_client
    ):
        """Test that the fix handles mixed scenarios correctly."""
        
        # Create a mix of forks: some with commits, some without, some with errors
        forks_needing_api = [
            MockForkData(metrics=MockMetrics(owner="fork1", name="repo", can_skip_analysis=True)),  # No commits
            MockForkData(metrics=MockMetrics(owner="fork2", name="repo")),  # Has commits
            MockForkData(metrics=MockMetrics(owner="fork3", name="repo")),  # API error
            MockForkData(metrics=MockMetrics(owner="fork4", name="repo")),  # Has commits
        ]
        
        # Mock batch counts - fork3 missing (simulates API error)
        mock_batch_counts = {
            "fork2/repo": 8,   # Fork2 has 8 commits ahead
            "fork4/repo": 2,   # Fork4 has 2 commits ahead
            # fork3/repo missing - simulates API failure
        }
        
        mock_github_client.get_commits_ahead_batch_counts.return_value = mock_batch_counts
        
        # Call the fixed method
        successful_forks, api_calls_saved = await repository_display_service._get_exact_commit_counts_batch(
            forks_needing_api, "parent", "repo"
        )
        
        # Verify results
        assert forks_needing_api[0].exact_commits_ahead == 0        # Skipped analysis
        assert forks_needing_api[1].exact_commits_ahead == 8        # Got correct count
        assert forks_needing_api[2].exact_commits_ahead == "Unknown"  # API error
        assert forks_needing_api[3].exact_commits_ahead == 2        # Got correct count
        
        # Verify that only forks needing API calls were included in the batch request
        mock_github_client.get_commits_ahead_batch_counts.assert_called_once_with(
            [("fork2", "repo"), ("fork3", "repo"), ("fork4", "repo")],  # fork1 was skipped
            "parent",
            "repo"
        )
        
        # Verify return values
        assert successful_forks == 3  # fork1 (skipped) + fork2 (success) + fork4 (success)
        assert api_calls_saved == 2  # fork2 and fork4 saved parent repo calls

    @pytest.mark.asyncio
    async def test_commit_counting_fix_fallback_behavior(
        self, repository_display_service, mock_github_client
    ):
        """Test that the fix handles fallback to individual calls correctly."""
        
        # Create mock fork data
        forks_needing_api = [
            MockForkData(metrics=MockMetrics(owner="fork1", name="repo")),
        ]
        
        # Mock batch method to fail (simulates network error or API issue)
        mock_github_client.get_commits_ahead_batch_counts.side_effect = Exception("Batch API failed")
        
        # Mock individual compare method to succeed
        mock_github_client.compare_repositories.return_value = {"ahead_by": 6}
        
        # Call the fixed method
        successful_forks, api_calls_saved = await repository_display_service._get_exact_commit_counts_batch(
            forks_needing_api, "parent", "repo"
        )
        
        # Verify that individual API call was made as fallback
        mock_github_client.compare_repositories.assert_called_once_with(
            "parent", "repo", "fork1", "repo"
        )
        
        # Verify that fork got correct count from individual call
        assert forks_needing_api[0].exact_commits_ahead == 6
        
        # Verify return values (no API calls saved since fallback was used)
        assert successful_forks == 1
        assert api_calls_saved == 0