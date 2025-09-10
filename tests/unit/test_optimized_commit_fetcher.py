"""Tests for optimized commit fetcher."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from forkscout.github.client import GitHubClient
from forkscout.github.exceptions import GitHubAPIError
from forkscout.github.optimized_commit_fetcher import (
    CommitFetchingStats,
    OptimizedCommitFetcher,
    OptimizedCommitFetchingError,
)
from forkscout.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualificationStats,
    QualifiedForksResult,
)
from forkscout.models.github import RecentCommit


class TestCommitFetchingStats:
    """Test commit fetching statistics."""

    def test_init(self):
        """Test statistics initialization."""
        stats = CommitFetchingStats()

        assert stats.total_forks_processed == 0
        assert stats.forks_skipped_no_commits == 0
        assert stats.forks_with_commits_fetched == 0
        assert stats.api_calls_made == 0
        assert stats.api_calls_saved == 0
        assert stats.processing_time_seconds == 0.0
        assert stats.errors_encountered == 0
        assert stats.fallback_operations == 0

    def test_efficiency_percentage(self):
        """Test efficiency percentage calculation."""
        stats = CommitFetchingStats()

        # No calls made
        assert stats.efficiency_percentage == 0.0

        # Some calls made and saved
        stats.api_calls_made = 30
        stats.api_calls_saved = 70
        assert stats.efficiency_percentage == 70.0

    def test_skip_rate_percentage(self):
        """Test skip rate percentage calculation."""
        stats = CommitFetchingStats()

        # No forks processed
        assert stats.skip_rate_percentage == 0.0

        # Some forks processed and skipped
        stats.total_forks_processed = 100
        stats.forks_skipped_no_commits = 60
        assert stats.skip_rate_percentage == 60.0

    def test_get_summary(self):
        """Test summary generation."""
        stats = CommitFetchingStats()
        stats.total_forks_processed = 100
        stats.forks_skipped_no_commits = 60
        stats.forks_with_commits_fetched = 40
        stats.api_calls_made = 120
        stats.api_calls_saved = 180
        stats.processing_time_seconds = 45.5
        stats.errors_encountered = 2
        stats.fallback_operations = 1

        summary = stats.get_summary()

        assert "Total Forks: 100" in summary
        assert "Skipped (no commits): 60 (60.0%)" in summary
        assert "Fetched commits: 40" in summary
        assert "API calls made: 120" in summary
        assert "API calls saved: 180" in summary
        assert "Efficiency: 60.0%" in summary
        assert "Processing time: 45.50s" in summary
        assert "Errors: 2" in summary
        assert "Fallbacks: 1" in summary


class TestOptimizedCommitFetcher:
    """Test optimized commit fetcher."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return AsyncMock(spec=GitHubClient)

    @pytest.fixture
    def commit_fetcher(self, mock_github_client):
        """Create an optimized commit fetcher."""
        return OptimizedCommitFetcher(mock_github_client)

    @pytest.fixture
    def sample_fork_metrics_no_commits(self):
        """Create sample fork metrics indicating no commits ahead."""
        return ForkQualificationMetrics(
            id=1,
            name="test-repo",
            full_name="user1/test-repo",
            owner="user1",
            html_url="https://github.com/user1/test-repo",
            stargazers_count=5,
            forks_count=2,
            watchers_count=7,
            size=100,
            language="Python",
            topics=["python"],
            open_issues_count=1,
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            updated_at=datetime(2023, 1, 1, 12, 0, 0),
            pushed_at=datetime(2023, 1, 1, 12, 0, 0),  # Same as created_at = no commits
            archived=False,
            disabled=False,
            fork=True,
        )

    @pytest.fixture
    def sample_fork_metrics_has_commits(self):
        """Create sample fork metrics indicating commits ahead."""
        return ForkQualificationMetrics(
            id=2,
            name="active-repo",
            full_name="user2/active-repo",
            owner="user2",
            html_url="https://github.com/user2/active-repo",
            stargazers_count=10,
            forks_count=3,
            watchers_count=12,
            size=200,
            language="JavaScript",
            topics=["javascript"],
            open_issues_count=2,
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            updated_at=datetime(2023, 1, 2, 12, 0, 0),
            pushed_at=datetime(2023, 1, 3, 12, 0, 0),  # Later than created_at = has commits
            archived=False,
            disabled=False,
            fork=True,
        )

    @pytest.fixture
    def qualified_forks_result(self, sample_fork_metrics_no_commits, sample_fork_metrics_has_commits):
        """Create a qualified forks result with mixed fork types."""
        fork_no_commits = CollectedForkData(metrics=sample_fork_metrics_no_commits)
        fork_has_commits = CollectedForkData(metrics=sample_fork_metrics_has_commits)

        stats = QualificationStats(
            total_forks_discovered=2,
            forks_with_no_commits=1,
            forks_with_commits=1,
            api_calls_made=1,
            api_calls_saved=2,
            processing_time_seconds=1.5,
        )

        return QualifiedForksResult(
            repository_owner="parent",
            repository_name="repo",
            repository_url="https://github.com/parent/repo",
            collected_forks=[fork_no_commits, fork_has_commits],
            stats=stats,
        )

    @pytest.fixture
    def sample_recent_commits(self):
        """Create sample recent commits."""
        return [
            RecentCommit(
                short_sha="abc1234",
                message="Fix bug in parser",
                date=datetime(2024, 1, 15, 10, 30, 0),
            ),
            RecentCommit(
                short_sha="def5678",
                message="Add new feature",
                date=datetime(2024, 1, 14, 9, 15, 0),
            ),
        ]

    @pytest.mark.asyncio
    async def test_fetch_commits_for_qualified_forks_success(
        self, commit_fetcher, mock_github_client, qualified_forks_result, sample_recent_commits
    ):
        """Test successful optimized commit fetching."""
        # Mock the get_commits_ahead method to return sample commits
        mock_github_client.get_commits_ahead.return_value = sample_recent_commits

        # Track progress calls
        progress_calls = []
        def progress_callback(current, total, status):
            progress_calls.append((current, total, status))

        result = await commit_fetcher.fetch_commits_for_qualified_forks(
            qualified_forks_result,
            "parent",
            "repo",
            max_commits_per_fork=5,
            progress_callback=progress_callback,
        )

        # Verify results
        assert len(result) == 2
        assert "user1/test-repo" in result
        assert "user2/active-repo" in result

        # Fork with no commits should have empty list
        assert result["user1/test-repo"] == []

        # Fork with commits should have the sample commits
        assert result["user2/active-repo"] == sample_recent_commits

        # Verify API was only called for the fork with commits
        mock_github_client.get_commits_ahead.assert_called_once_with(
            "user2", "active-repo", "parent", "repo", 5
        )

        # Verify progress callback was called
        assert len(progress_calls) == 1
        assert progress_calls[0] == (1, 1, "Fetched commits for user2/active-repo")

    @pytest.mark.asyncio
    async def test_fetch_commits_for_qualified_forks_invalid_count(
        self, commit_fetcher, qualified_forks_result
    ):
        """Test fetch commits with invalid count parameter."""
        with pytest.raises(ValueError, match="max_commits_per_fork must be between 1 and 10"):
            await commit_fetcher.fetch_commits_for_qualified_forks(
                qualified_forks_result, "parent", "repo", max_commits_per_fork=0
            )

        with pytest.raises(ValueError, match="max_commits_per_fork must be between 1 and 10"):
            await commit_fetcher.fetch_commits_for_qualified_forks(
                qualified_forks_result, "parent", "repo", max_commits_per_fork=11
            )

    @pytest.mark.asyncio
    async def test_fetch_commits_for_qualified_forks_api_error_with_fallback(
        self, commit_fetcher, mock_github_client, qualified_forks_result, sample_recent_commits
    ):
        """Test commit fetching with API error and successful fallback."""
        # First call fails, second call (fallback) succeeds
        mock_github_client.get_commits_ahead.side_effect = [
            GitHubAPIError("API error"),
            sample_recent_commits,
        ]

        result = await commit_fetcher.fetch_commits_for_qualified_forks(
            qualified_forks_result, "parent", "repo", max_commits_per_fork=5
        )

        # Verify results - fallback should have worked
        assert len(result) == 2
        assert result["user1/test-repo"] == []  # Skipped based on qualification
        assert result["user2/active-repo"] == sample_recent_commits  # Fallback succeeded

        # Verify API was called twice (initial + fallback)
        assert mock_github_client.get_commits_ahead.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_commits_for_qualified_forks_fallback_failure(
        self, commit_fetcher, mock_github_client, qualified_forks_result
    ):
        """Test commit fetching with both primary and fallback failures."""
        # Both calls fail
        mock_github_client.get_commits_ahead.side_effect = [
            GitHubAPIError("API error"),
            GitHubAPIError("Fallback also failed"),
        ]

        result = await commit_fetcher.fetch_commits_for_qualified_forks(
            qualified_forks_result, "parent", "repo", max_commits_per_fork=5
        )

        # Verify results - fallback failure should result in empty list
        assert len(result) == 2
        assert result["user1/test-repo"] == []  # Skipped based on qualification
        assert result["user2/active-repo"] == []  # Fallback failed, empty list returned

        # Verify API was called twice (initial + fallback)
        assert mock_github_client.get_commits_ahead.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_commits_for_single_fork_with_qualification_skip(
        self, commit_fetcher, sample_fork_metrics_no_commits
    ):
        """Test single fork commit fetching with skip optimization."""
        fork_data = CollectedForkData(metrics=sample_fork_metrics_no_commits)

        result = await commit_fetcher.fetch_commits_for_single_fork_with_qualification(
            fork_data, "parent", "repo", max_commits_per_fork=5
        )

        # Should be skipped based on qualification data
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_commits_for_single_fork_with_qualification_force_fetch(
        self, commit_fetcher, mock_github_client, sample_fork_metrics_no_commits, sample_recent_commits
    ):
        """Test single fork commit fetching with force fetch override."""
        fork_data = CollectedForkData(metrics=sample_fork_metrics_no_commits)
        mock_github_client.get_commits_ahead.return_value = sample_recent_commits

        result = await commit_fetcher.fetch_commits_for_single_fork_with_qualification(
            fork_data, "parent", "repo", max_commits_per_fork=5, force_fetch=True
        )

        # Should fetch despite qualification suggesting no commits
        assert result == sample_recent_commits
        mock_github_client.get_commits_ahead.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_commits_for_single_fork_with_qualification_has_commits(
        self, commit_fetcher, mock_github_client, sample_fork_metrics_has_commits, sample_recent_commits
    ):
        """Test single fork commit fetching for fork with commits."""
        fork_data = CollectedForkData(metrics=sample_fork_metrics_has_commits)
        mock_github_client.get_commits_ahead.return_value = sample_recent_commits

        result = await commit_fetcher.fetch_commits_for_single_fork_with_qualification(
            fork_data, "parent", "repo", max_commits_per_fork=5
        )

        # Should fetch commits normally
        assert result == sample_recent_commits
        mock_github_client.get_commits_ahead.assert_called_once_with(
            "user2", "active-repo", "parent", "repo", 5
        )

    @pytest.mark.asyncio
    async def test_fetch_commits_for_single_fork_with_qualification_error(
        self, commit_fetcher, mock_github_client, sample_fork_metrics_has_commits
    ):
        """Test single fork commit fetching with error."""
        fork_data = CollectedForkData(metrics=sample_fork_metrics_has_commits)
        mock_github_client.get_commits_ahead.side_effect = GitHubAPIError("API error")

        with pytest.raises(OptimizedCommitFetchingError, match="Failed to fetch commits for user2/active-repo"):
            await commit_fetcher.fetch_commits_for_single_fork_with_qualification(
                fork_data, "parent", "repo", max_commits_per_fork=5
            )

    @pytest.mark.asyncio
    async def test_fetch_commits_for_single_fork_with_qualification_invalid_count(
        self, commit_fetcher, sample_fork_metrics_has_commits
    ):
        """Test single fork commit fetching with invalid count."""
        fork_data = CollectedForkData(metrics=sample_fork_metrics_has_commits)

        with pytest.raises(ValueError, match="max_commits_per_fork must be between 1 and 10"):
            await commit_fetcher.fetch_commits_for_single_fork_with_qualification(
                fork_data, "parent", "repo", max_commits_per_fork=0
            )

    def test_get_optimization_summary(self, commit_fetcher, qualified_forks_result):
        """Test optimization summary generation."""
        summary = commit_fetcher.get_optimization_summary(qualified_forks_result)

        assert "Total Forks: 2" in summary
        assert "Forks to Skip: 1 (50.0%)" in summary
        assert "Forks Needing Commits: 1 (50.0%)" in summary
        assert "Without optimization: 6 API calls" in summary
        assert "With optimization: 3 API calls" in summary
        assert "API calls saved: 3" in summary
        assert "Efficiency gain: 50.0%" in summary

    def test_get_optimization_summary_no_forks(self, commit_fetcher):
        """Test optimization summary with no forks."""
        empty_result = QualifiedForksResult(
            repository_owner="parent",
            repository_name="repo",
            repository_url="https://github.com/parent/repo",
            collected_forks=[],
            stats=QualificationStats(),
        )

        summary = commit_fetcher.get_optimization_summary(empty_result)

        assert "Total Forks: 0" in summary
        assert "Efficiency gain: 0.0%" in summary

    def test_get_optimization_summary_all_need_commits(self, commit_fetcher, sample_fork_metrics_has_commits):
        """Test optimization summary when all forks need commits."""
        fork_data = CollectedForkData(metrics=sample_fork_metrics_has_commits)

        result = QualifiedForksResult(
            repository_owner="parent",
            repository_name="repo",
            repository_url="https://github.com/parent/repo",
            collected_forks=[fork_data, fork_data],  # Two forks that need commits
            stats=QualificationStats(
                total_forks_discovered=2,
                forks_with_no_commits=0,
                forks_with_commits=2,
            ),
        )

        summary = commit_fetcher.get_optimization_summary(result)

        assert "Total Forks: 2" in summary
        assert "Forks to Skip: 0 (0.0%)" in summary
        assert "Forks Needing Commits: 2 (100.0%)" in summary
        assert "Efficiency gain: 0.0%" in summary  # No optimization possible

    def test_get_optimization_summary_all_can_skip(self, commit_fetcher, sample_fork_metrics_no_commits):
        """Test optimization summary when all forks can be skipped."""
        fork_data = CollectedForkData(metrics=sample_fork_metrics_no_commits)

        result = QualifiedForksResult(
            repository_owner="parent",
            repository_name="repo",
            repository_url="https://github.com/parent/repo",
            collected_forks=[fork_data, fork_data],  # Two forks that can be skipped
            stats=QualificationStats(
                total_forks_discovered=2,
                forks_with_no_commits=2,
                forks_with_commits=0,
            ),
        )

        summary = commit_fetcher.get_optimization_summary(result)

        assert "Total Forks: 2" in summary
        assert "Forks to Skip: 2 (100.0%)" in summary
        assert "Forks Needing Commits: 0 (0.0%)" in summary
        assert "Efficiency gain: 100.0%" in summary  # Maximum optimization
