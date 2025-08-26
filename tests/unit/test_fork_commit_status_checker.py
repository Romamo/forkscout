"""Unit tests for ForkCommitStatusChecker."""

import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from forklift.analysis.fork_commit_status_checker import (
    ForkCommitStatusChecker,
    ForkCommitStatusError,
)
from forklift.github.client import GitHubAPIError, GitHubClient, GitHubNotFoundError
from forklift.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualificationStats,
    QualifiedForksResult,
)
from forklift.models.github import Repository


class TestForkCommitStatusChecker:
    """Test cases for ForkCommitStatusChecker."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return AsyncMock(spec=GitHubClient)

    @pytest.fixture
    def status_checker(self, mock_github_client):
        """Create a ForkCommitStatusChecker instance."""
        return ForkCommitStatusChecker(mock_github_client)

    @pytest.fixture
    def sample_fork_metrics_no_commits(self):
        """Create sample fork metrics with no commits ahead (created_at >= pushed_at)."""
        created_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        pushed_time = datetime(2024, 1, 15, 9, 30, 0, tzinfo=UTC)  # Earlier than created

        return ForkQualificationMetrics(
            id=12345,
            name="test-repo",
            full_name="testuser/test-repo",
            owner="testuser",
            html_url="https://github.com/testuser/test-repo",
            created_at=created_time,
            updated_at=created_time,
            pushed_at=pushed_time,
        )

    @pytest.fixture
    def sample_fork_metrics_has_commits(self):
        """Create sample fork metrics with commits ahead (pushed_at > created_at)."""
        created_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        pushed_time = datetime(2024, 1, 15, 11, 30, 0, tzinfo=UTC)  # Later than created

        return ForkQualificationMetrics(
            id=12346,
            name="active-repo",
            full_name="activeuser/active-repo",
            owner="activeuser",
            html_url="https://github.com/activeuser/active-repo",
            created_at=created_time,
            updated_at=pushed_time,
            pushed_at=pushed_time,
        )

    @pytest.fixture
    def qualification_result_with_forks(self, sample_fork_metrics_no_commits, sample_fork_metrics_has_commits):
        """Create a qualification result with sample forks."""
        fork_data_no_commits = CollectedForkData(metrics=sample_fork_metrics_no_commits)
        fork_data_has_commits = CollectedForkData(metrics=sample_fork_metrics_has_commits)

        stats = QualificationStats(
            total_forks_discovered=2,
            forks_with_no_commits=1,
            forks_with_commits=1,
        )

        return QualifiedForksResult(
            repository_owner="upstream",
            repository_name="main-repo",
            repository_url="https://github.com/upstream/main-repo",
            collected_forks=[fork_data_no_commits, fork_data_has_commits],
            stats=stats,
        )

    @pytest.mark.asyncio
    async def test_has_commits_ahead_using_qualification_data_no_commits(
        self, status_checker, qualification_result_with_forks
    ):
        """Test detecting no commits ahead using qualification data."""
        fork_url = "https://github.com/testuser/test-repo"

        result = await status_checker.has_commits_ahead(fork_url, qualification_result_with_forks)

        assert result is False
        assert status_checker.stats.qualification_data_hits == 1
        assert status_checker.stats.api_fallback_calls == 0

    @pytest.mark.asyncio
    async def test_has_commits_ahead_using_qualification_data_has_commits(
        self, status_checker, qualification_result_with_forks
    ):
        """Test detecting commits ahead using qualification data."""
        fork_url = "https://github.com/activeuser/active-repo"

        result = await status_checker.has_commits_ahead(fork_url, qualification_result_with_forks)

        assert result is True
        assert status_checker.stats.qualification_data_hits == 1
        assert status_checker.stats.api_fallback_calls == 0

    @pytest.mark.asyncio
    async def test_has_commits_ahead_fork_not_in_qualification_data(
        self, status_checker, qualification_result_with_forks, mock_github_client
    ):
        """Test fallback to GitHub API when fork not found in qualification data."""
        fork_url = "https://github.com/unknown/unknown-repo"

        # Mock GitHub API response
        mock_repo = Repository(
            id=99999,
            name="unknown-repo",
            full_name="unknown/unknown-repo",
            owner="unknown",
            url="https://api.github.com/repos/unknown/unknown-repo",
            html_url="https://github.com/unknown/unknown-repo",
            clone_url="https://github.com/unknown/unknown-repo.git",
            created_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            pushed_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),  # Later than created
        )
        mock_github_client.get_repository.return_value = mock_repo

        result = await status_checker.has_commits_ahead(fork_url, qualification_result_with_forks)

        assert result is True
        assert status_checker.stats.api_fallback_calls == 1
        mock_github_client.get_repository.assert_called_once_with("unknown", "unknown-repo")

    @pytest.mark.asyncio
    async def test_has_commits_ahead_no_qualification_data_fallback_to_api(
        self, status_checker, mock_github_client
    ):
        """Test fallback to GitHub API when no qualification data provided."""
        fork_url = "https://github.com/testuser/test-repo"

        # Mock GitHub API response - no commits ahead
        mock_repo = Repository(
            id=12345,
            name="test-repo",
            full_name="testuser/test-repo",
            owner="testuser",
            url="https://api.github.com/repos/testuser/test-repo",
            html_url="https://github.com/testuser/test-repo",
            clone_url="https://github.com/testuser/test-repo.git",
            created_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            pushed_at=datetime(2024, 1, 15, 9, 30, 0, tzinfo=UTC),  # Earlier than created
        )
        mock_github_client.get_repository.return_value = mock_repo

        result = await status_checker.has_commits_ahead(fork_url, None)

        assert result is False
        assert status_checker.stats.api_fallback_calls == 1
        mock_github_client.get_repository.assert_called_once_with("testuser", "test-repo")

    @pytest.mark.asyncio
    async def test_has_commits_ahead_github_api_not_found(
        self, status_checker, mock_github_client
    ):
        """Test handling GitHub API not found error."""
        fork_url = "https://github.com/nonexistent/repo"

        mock_github_client.get_repository.side_effect = GitHubNotFoundError("Repository not found")

        result = await status_checker.has_commits_ahead(fork_url, None)

        assert result is None
        assert status_checker.stats.api_fallback_calls == 1
        assert status_checker.stats.status_unknown == 1

    @pytest.mark.asyncio
    async def test_has_commits_ahead_github_api_error(
        self, status_checker, mock_github_client
    ):
        """Test handling GitHub API errors."""
        fork_url = "https://github.com/testuser/test-repo"

        mock_github_client.get_repository.side_effect = GitHubAPIError("API Error", status_code=500)

        result = await status_checker.has_commits_ahead(fork_url, None)

        assert result is None
        assert status_checker.stats.api_fallback_calls == 1
        assert status_checker.stats.status_unknown == 1

    @pytest.mark.asyncio
    async def test_has_commits_ahead_invalid_url_format(self, status_checker):
        """Test handling invalid fork URL formats."""
        invalid_urls = [
            "not-a-url",
            "https://github.com/",
            "https://github.com/single-part",
            "https://example.com/owner/repo",
            "",
        ]

        for invalid_url in invalid_urls:
            with pytest.raises(ForkCommitStatusError, match="Invalid fork URL format"):
                await status_checker.has_commits_ahead(invalid_url, None)

    def test_parse_fork_url_valid_formats(self, status_checker):
        """Test parsing various valid fork URL formats."""
        test_cases = [
            ("https://github.com/owner/repo", ("owner", "repo")),
            ("https://github.com/owner/repo/", ("owner", "repo")),
            ("https://github.com/owner/repo.git", ("owner", "repo.git")),
            ("owner/repo", ("owner", "repo")),
        ]

        for url, expected in test_cases:
            result = status_checker._parse_fork_url(url)
            assert result == expected

    def test_parse_fork_url_invalid_formats(self, status_checker):
        """Test parsing invalid fork URL formats."""
        invalid_urls = [
            "https://github.com/",
            "https://github.com/single-part",
            "https://example.com/owner/repo",
            "owner",
            "owner/repo/extra/parts",
            "",
            "   ",  # whitespace only
        ]

        for invalid_url in invalid_urls:
            with pytest.raises(ForkCommitStatusError):
                status_checker._parse_fork_url(invalid_url)

    def test_get_statistics_initial_state(self, status_checker):
        """Test getting statistics in initial state."""
        stats = status_checker.get_statistics()

        # Check that we get a ForkFilteringStats object
        assert hasattr(stats, "qualification_data_hits")
        assert hasattr(stats, "api_fallback_calls")
        assert hasattr(stats, "status_unknown")
        assert hasattr(stats, "errors")

        # Check initial values are zero
        assert stats.qualification_data_hits == 0
        assert stats.api_fallback_calls == 0
        assert stats.status_unknown == 0
        assert stats.errors == 0

    @pytest.mark.asyncio
    async def test_statistics_tracking(self, status_checker, qualification_result_with_forks, mock_github_client):
        """Test that statistics are properly tracked."""
        # Test qualification data hit
        await status_checker.has_commits_ahead(
            "https://github.com/testuser/test-repo",
            qualification_result_with_forks
        )

        # Mock GitHub API response for API fallback test
        mock_repo = Repository(
            id=99999,
            name="repo",
            full_name="unknown/repo",
            owner="unknown",
            url="https://api.github.com/repos/unknown/repo",
            html_url="https://github.com/unknown/repo",
            clone_url="https://github.com/unknown/repo.git",
            created_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            pushed_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        )
        mock_github_client.get_repository.return_value = mock_repo

        # Test API fallback
        await status_checker.has_commits_ahead(
            "https://github.com/unknown/repo",
            qualification_result_with_forks
        )

        stats = status_checker.get_statistics()
        assert stats.qualification_data_hits == 1
        assert stats.api_fallback_calls == 1

    def test_reset_statistics(self, status_checker):
        """Test resetting statistics."""
        # Manually set some stats
        status_checker.stats.add_qualification_hit()
        status_checker.stats.add_api_fallback()
        status_checker.stats.add_error()

        # Verify stats are set
        assert status_checker.stats.qualification_data_hits > 0
        assert status_checker.stats.api_fallback_calls > 0
        assert status_checker.stats.errors > 0

        status_checker.reset_statistics()

        stats = status_checker.get_statistics()
        assert stats.qualification_data_hits == 0
        assert stats.api_fallback_calls == 0
        assert stats.errors == 0

    def test_log_statistics_no_checks(self, status_checker, caplog):
        """Test logging statistics when no checks have been performed."""
        with caplog.at_level(logging.INFO):
            status_checker.log_statistics()

        assert "No fork filtering operations performed yet" in caplog.text

    def test_log_statistics_with_data(self, status_checker, caplog):
        """Test logging statistics with data."""
        # Set some test data
        status_checker.stats.add_qualification_hit()
        status_checker.stats.add_qualification_hit()
        status_checker.stats.add_api_fallback()
        status_checker.stats.add_fork_evaluated(filtered=True, reason="no_commits_ahead")
        status_checker.stats.add_fork_evaluated(filtered=False)
        status_checker.stats.add_error()

        with caplog.at_level(logging.INFO):
            status_checker.log_statistics()

        assert "Fork filtering statistics:" in caplog.text
        assert "evaluated=2" in caplog.text
        assert "filtering_rate=50.0%" in caplog.text
        assert "Fork filtering reasons:" in caplog.text
        assert "Fork filtering errors encountered: 1" in caplog.text

    @pytest.mark.asyncio
    async def test_owner_repo_format_url(self, status_checker, mock_github_client):
        """Test handling owner/repo format URLs."""
        fork_url = "testuser/test-repo"

        # Mock GitHub API response
        mock_repo = Repository(
            id=12345,
            name="test-repo",
            full_name="testuser/test-repo",
            owner="testuser",
            url="https://api.github.com/repos/testuser/test-repo",
            html_url="https://github.com/testuser/test-repo",
            clone_url="https://github.com/testuser/test-repo.git",
            created_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            pushed_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        )
        mock_github_client.get_repository.return_value = mock_repo

        result = await status_checker.has_commits_ahead(fork_url, None)

        assert result is True
        mock_github_client.get_repository.assert_called_once_with("testuser", "test-repo")

    @pytest.mark.asyncio
    async def test_edge_case_same_timestamps(self, status_checker):
        """Test edge case where created_at equals pushed_at."""
        same_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        fork_metrics = ForkQualificationMetrics(
            id=12347,
            name="same-time-repo",
            full_name="sameuser/same-time-repo",
            owner="sameuser",
            html_url="https://github.com/sameuser/same-time-repo",
            created_at=same_time,
            updated_at=same_time,
            pushed_at=same_time,
        )

        fork_data = CollectedForkData(metrics=fork_metrics)
        stats = QualificationStats(total_forks_discovered=1, forks_with_no_commits=1)

        qualification_result = QualifiedForksResult(
            repository_owner="upstream",
            repository_name="main-repo",
            repository_url="https://github.com/upstream/main-repo",
            collected_forks=[fork_data],
            stats=stats,
        )

        result = await status_checker.has_commits_ahead(
            "https://github.com/sameuser/same-time-repo",
            qualification_result
        )

        # When created_at == pushed_at, should be considered no commits ahead
        assert result is False
        assert status_checker.stats.qualification_data_hits == 1

    @pytest.mark.asyncio
    async def test_unexpected_error_handling(self, status_checker, mock_github_client):
        """Test handling of unexpected errors."""
        fork_url = "https://github.com/testuser/test-repo"

        # Mock an unexpected error
        mock_github_client.get_repository.side_effect = Exception("Unexpected error")

        with pytest.raises(ForkCommitStatusError, match="Failed to check commit status"):
            await status_checker.has_commits_ahead(fork_url, None)

        assert status_checker.stats.errors == 1
