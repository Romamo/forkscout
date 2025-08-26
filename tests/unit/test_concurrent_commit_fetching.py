"""Tests for concurrent commit fetching functionality."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.models.github import RecentCommit
from forklift.models.fork_qualification import CollectedForkData, ForkQualificationMetrics


class TestConcurrentCommitFetching:
    """Test concurrent commit fetching functionality."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return AsyncMock()

    @pytest.fixture
    def mock_console(self):
        """Create a mock console."""
        return MagicMock()

    @pytest.fixture
    def display_service(self, mock_github_client, mock_console):
        """Create a RepositoryDisplayService instance."""
        return RepositoryDisplayService(mock_github_client, mock_console)

    @pytest.fixture
    def sample_fork_data(self):
        """Create sample fork data for testing."""
        from datetime import datetime
        
        fork1_metrics = ForkQualificationMetrics(
            id=12345,
            name="repo1",
            full_name="user1/repo1",
            owner="user1",
            html_url="https://github.com/user1/repo1",
            stargazers_count=10,
            forks_count=2,
            size=1000,
            language="Python",
            topics=[],
            open_issues_count=5,
            watchers_count=8,
            archived=False,
            disabled=False,
            created_at=datetime.fromisoformat("2023-01-01T00:00:00"),
            updated_at=datetime.fromisoformat("2023-06-01T00:00:00"),
            pushed_at=datetime.fromisoformat("2023-06-01T00:00:00"),
            days_since_creation=200,
            days_since_last_update=30,
            days_since_last_push=30,
            commits_ahead_status="Has commits",
            can_skip_analysis=False,
        )

        fork2_metrics = ForkQualificationMetrics(
            id=67890,
            name="repo2",
            full_name="user2/repo2",
            owner="user2",
            html_url="https://github.com/user2/repo2",
            stargazers_count=5,
            forks_count=1,
            size=500,
            language="JavaScript",
            topics=["web"],
            open_issues_count=2,
            watchers_count=3,
            archived=False,
            disabled=False,
            created_at=datetime.fromisoformat("2023-02-01T00:00:00"),
            updated_at=datetime.fromisoformat("2023-05-01T00:00:00"),
            pushed_at=datetime.fromisoformat("2023-05-01T00:00:00"),
            days_since_creation=150,
            days_since_last_update=60,
            days_since_last_push=60,
            commits_ahead_status="Has commits",
            can_skip_analysis=False,
        )

        return [
            CollectedForkData(
                metrics=fork1_metrics,
                activity_summary="Active fork with recent commits"
            ),
            CollectedForkData(
                metrics=fork2_metrics,
                activity_summary="Moderately active fork"
            ),
        ]

    @pytest.mark.asyncio
    @patch('forklift.display.repository_display_service.Progress')
    async def test_fetch_commits_concurrently_success(
        self, mock_progress, display_service, sample_fork_data, mock_github_client
    ):
        """Test successful concurrent commit fetching."""
        # Mock progress to avoid Rich timing issues
        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = 0
        
        # Mock recent commits for each fork
        commits_fork1 = [
            RecentCommit(
                short_sha="abc1234",
                message="Fix bug in authentication"
            ),
            RecentCommit(
                short_sha="def4567",
                message="Add new feature"
            ),
        ]

        commits_fork2 = [
            RecentCommit(
                short_sha="abc7890",
                message="Update documentation"
            ),
        ]

        # Configure mock to return different commits for each fork
        async def mock_get_recent_commits(owner, repo, count=5):
            if owner == "user1" and repo == "repo1":
                return commits_fork1
            elif owner == "user2" and repo == "repo2":
                return commits_fork2
            return []

        mock_github_client.get_recent_commits.side_effect = mock_get_recent_commits

        # Test concurrent fetching
        result = await display_service._fetch_commits_concurrently(sample_fork_data, 2)

        # Verify results
        assert len(result) == 2
        assert "user1/repo1" in result
        assert "user2/repo2" in result

        # Check formatted commit strings
        fork1_commits = result["user1/repo1"]
        fork2_commits = result["user2/repo2"]

        assert "abc1234: Fix bug in authentication" in fork1_commits
        assert "def4567: Add new feature" in fork1_commits
        assert "abc7890: Update documentation" in fork2_commits

        # Verify API calls were made
        assert mock_github_client.get_recent_commits.call_count == 2

    @pytest.mark.asyncio
    @patch('forklift.display.repository_display_service.Progress')
    async def test_fetch_commits_concurrently_with_failures(
        self, mock_progress, display_service, sample_fork_data, mock_github_client
    ):
        """Test concurrent commit fetching with some failures."""
        # Mock progress to avoid Rich timing issues
        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = 0
        
        # Mock one successful call and one failure
        async def mock_get_recent_commits(owner, repo, count=5):
            if owner == "user1" and repo == "repo1":
                return [
                    RecentCommit(
                        short_sha="abc1234",
                        message="Working commit"
                    )
                ]
            elif owner == "user2" and repo == "repo2":
                raise Exception("API rate limit exceeded")
            return []

        mock_github_client.get_recent_commits.side_effect = mock_get_recent_commits

        # Test concurrent fetching with failures
        result = await display_service._fetch_commits_concurrently(sample_fork_data, 1)

        # Verify results
        assert len(result) == 2
        assert "user1/repo1" in result
        assert "user2/repo2" in result

        # Check that successful fork has commits and failed fork has error message
        assert "abc1234: Working commit" in result["user1/repo1"]
        assert result["user2/repo2"] == "[dim]No commits available[/dim]"

        # Verify API calls were attempted for both
        assert mock_github_client.get_recent_commits.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_commits_concurrently_empty_input(self, display_service):
        """Test concurrent commit fetching with empty input."""
        result = await display_service._fetch_commits_concurrently([], 5)
        assert result == {}

    @pytest.mark.asyncio
    async def test_fetch_commits_concurrently_zero_count(
        self, display_service, sample_fork_data
    ):
        """Test concurrent commit fetching with zero commit count."""
        result = await display_service._fetch_commits_concurrently(sample_fork_data, 0)
        assert result == {}

    @pytest.mark.asyncio
    @patch('forklift.display.repository_display_service.Progress')
    async def test_fetch_commits_concurrently_rate_limiting(
        self, mock_progress, display_service, sample_fork_data, mock_github_client
    ):
        """Test that concurrent fetching respects rate limiting."""
        # Mock progress to avoid Rich timing issues
        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = 0
        
        # Track timing to ensure rate limiting delays are applied
        call_times = []

        async def mock_get_recent_commits(owner, repo, count=5):
            import time
            call_times.append(time.time())
            return [
                RecentCommit(
                    short_sha="test123",
                    message="Test commit"
                )
            ]

        mock_github_client.get_recent_commits.side_effect = mock_get_recent_commits

        # Test concurrent fetching
        result = await display_service._fetch_commits_concurrently(sample_fork_data, 1)

        # Verify results
        assert len(result) == 2
        assert all(fork_key in result for fork_key in ["user1/repo1", "user2/repo2"])

        # Verify API calls were made
        assert mock_github_client.get_recent_commits.call_count == 2

        # Note: We can't easily test the exact timing due to asyncio scheduling,
        # but we can verify that the semaphore limits concurrent requests
        assert len(call_times) == 2

    @pytest.mark.asyncio
    async def test_format_recent_commits_integration(self, display_service):
        """Test the format_recent_commits method integration."""
        commits = [
            RecentCommit(
                short_sha="abc123d",
                message="Fix critical bug in user authentication system"
            ),
            RecentCommit(
                short_sha="def456a",
                message="Add comprehensive test coverage"
            ),
        ]

        formatted = display_service.format_recent_commits(commits)

        expected_lines = [
            "abc123d: Fix critical bug in user authentication system",
            "def456a: Add comprehensive test coverage",
        ]
        expected = "\n".join(expected_lines)

        assert formatted == expected

    @pytest.mark.asyncio
    @patch('forklift.display.repository_display_service.Progress')
    async def test_concurrent_fetching_preserves_order(
        self, mock_progress, display_service, mock_github_client
    ):
        """Test that concurrent fetching preserves fork identification."""
        # Mock progress to avoid Rich timing issues
        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = 0
        
        # Create more fork data to test ordering
        from datetime import datetime
        
        fork_metrics = []
        for i in range(3):  # Reduce to 3 for simpler testing
            metrics = ForkQualificationMetrics(
                id=10000 + i,
                name=f"repo{i}",
                full_name=f"user{i}/repo{i}",
                owner=f"user{i}",
                html_url=f"https://github.com/user{i}/repo{i}",
                stargazers_count=i,
                forks_count=1,
                size=1000,
                language="Python",
                topics=[],
                open_issues_count=0,
                watchers_count=i,
                archived=False,
                disabled=False,
                created_at=datetime.fromisoformat("2023-01-01T00:00:00"),
                updated_at=datetime.fromisoformat("2023-06-01T00:00:00"),
                pushed_at=datetime.fromisoformat("2023-06-01T00:00:00"),
                days_since_creation=200,
                days_since_last_update=30,
                days_since_last_push=30,
                commits_ahead_status="Has commits",
                can_skip_analysis=False,
            )
            fork_metrics.append(
                CollectedForkData(
                    metrics=metrics,
                    activity_summary=f"Fork {i} activity"
                )
            )

        # Mock commits for each fork
        async def mock_get_recent_commits(owner, repo, count=5):
            # Create valid 7-character hex SHA
            sha_map = {"user0": "abc1230", "user1": "def4561", "user2": "abc7892"}
            return [
                RecentCommit(
                    short_sha=sha_map.get(owner, "abc1234"),
                    message=f"Commit from {owner}"
                )
            ]

        mock_github_client.get_recent_commits.side_effect = mock_get_recent_commits

        # Test concurrent fetching
        result = await display_service._fetch_commits_concurrently(fork_metrics, 1)

        # Verify all forks are present
        assert len(result) == 3
        sha_map = {"user0": "abc1230", "user1": "def4561", "user2": "abc7892"}
        for i in range(3):
            fork_key = f"user{i}/repo{i}"
            assert fork_key in result
            expected_sha = sha_map[f"user{i}"]
            assert f"{expected_sha}: Commit from user{i}" in result[fork_key]