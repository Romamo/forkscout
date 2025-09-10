"""Integration tests for CSV export with fork data processing."""

import csv
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forkscout.cli import _export_forks_csv, _show_forks_summary
from forkscout.config.settings import ForkscoutConfig
from forkscout.display.interaction_mode import InteractionMode
from forkscout.display.repository_display_service import RepositoryDisplayService
from forkscout.github.client import GitHubClient


class TestCSVExportIntegration:
    """Test CSV export integration with existing fork data processing."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        client = AsyncMock(spec=GitHubClient)
        return client

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock(spec=ForkscoutConfig)
        config.github = MagicMock()
        config.github.token = "test_token"
        return config

    @pytest.fixture
    def sample_fork_data(self):
        """Create sample fork data for testing."""
        from datetime import UTC, datetime

        from forkscout.models.fork_qualification import (
            CollectedForkData,
            ForkQualificationMetrics,
        )

        # Create sample collected fork data
        metrics1 = ForkQualificationMetrics(
            id=123,
            name="test-repo",
            full_name="user1/test-repo",
            owner="user1",
            html_url="https://github.com/user1/test-repo",
            stargazers_count=10,
            forks_count=2,
            watchers_count=5,
            size=1000,
            language="Python",
            topics=[],
            open_issues_count=3,
            created_at=datetime(2024, 1, 10, tzinfo=UTC),
            updated_at=datetime(2024, 1, 14, tzinfo=UTC),
            pushed_at=datetime(2024, 1, 15, tzinfo=UTC),
            archived=False,
            disabled=False,
            fork=True,
            license_key="mit",
            license_name="MIT License",
            description="Test repository",
            homepage=None,
            default_branch="main"
        )

        metrics2 = ForkQualificationMetrics(
            id=456,
            name="test-repo",
            full_name="user2/test-repo",
            owner="user2",
            html_url="https://github.com/user2/test-repo",
            stargazers_count=5,
            forks_count=1,
            watchers_count=2,
            size=500,
            language="JavaScript",
            topics=[],
            open_issues_count=1,
            created_at=datetime(2024, 1, 5, tzinfo=UTC),
            updated_at=datetime(2024, 1, 5, tzinfo=UTC),
            pushed_at=datetime(2024, 1, 5, tzinfo=UTC),  # Same as created_at = no commits
            archived=False,
            disabled=False,
            fork=True,
            license_key=None,
            license_name=None,
            description="Another test repository",
            homepage=None,
            default_branch="main"
        )

        fork1 = CollectedForkData(metrics=metrics1)
        fork2 = CollectedForkData(metrics=metrics2)

        return [fork1, fork2]

    @pytest.mark.asyncio
    async def test_csv_export_basic_functionality(self, mock_github_client, sample_fork_data):
        """Test basic CSV export functionality."""
        # Capture stdout
        captured_output = StringIO()

        with patch("sys.stdout", captured_output):
            display_service = RepositoryDisplayService(mock_github_client)

            # Mock the fork data collection
            with patch.object(display_service, "show_fork_data") as mock_show_fork_data:
                mock_show_fork_data.return_value = {
                    "total_forks": 2,
                    "displayed_forks": 2,
                    "collected_forks": sample_fork_data
                }

                await _export_forks_csv(
                    display_service,
                    "owner/repo",
                    max_forks=None,
                    detail=False,
                    show_commits=0,
                    force_all_commits=False,
                    ahead_only=False
                )

                # Verify CSV export was called
                mock_show_fork_data.assert_called_once_with(
                    "owner/repo",
                    exclude_archived=False,
                    exclude_disabled=False,
                    sort_by="stars",
                    show_all=True,
                    disable_cache=False,
                    show_commits=0,
                    force_all_commits=False,
                    ahead_only=False,
                    csv_export=True,
                )

    @pytest.mark.asyncio
    async def test_csv_export_with_detail_flag(self, mock_github_client, sample_fork_data):
        """Test CSV export with --detail flag."""
        display_service = RepositoryDisplayService(mock_github_client)

        with patch.object(display_service, "show_fork_data_detailed") as mock_show_detailed:
            mock_show_detailed.return_value = {
                "total_forks": 2,
                "displayed_forks": 2,
                "collected_forks": sample_fork_data,
                "api_calls_made": 1
            }

            await _export_forks_csv(
                display_service,
                "owner/repo",
                max_forks=50,
                detail=True,
                show_commits=0,
                force_all_commits=False,
                ahead_only=False
            )

            # Verify detailed CSV export was called
            mock_show_detailed.assert_called_once_with(
                "owner/repo",
                max_forks=50,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False,
                ahead_only=False,
                csv_export=True,
            )

    @pytest.mark.asyncio
    async def test_csv_export_with_show_commits(self, mock_github_client, sample_fork_data):
        """Test CSV export with --show-commits flag."""
        display_service = RepositoryDisplayService(mock_github_client)

        with patch.object(display_service, "show_fork_data") as mock_show_fork_data:
            mock_show_fork_data.return_value = {
                "total_forks": 2,
                "displayed_forks": 2,
                "collected_forks": sample_fork_data
            }

            await _export_forks_csv(
                display_service,
                "owner/repo",
                max_forks=None,
                detail=False,
                show_commits=5,
                force_all_commits=True,
                ahead_only=False
            )

            # Verify show_commits parameter was passed
            mock_show_fork_data.assert_called_once_with(
                "owner/repo",
                exclude_archived=False,
                exclude_disabled=False,
                sort_by="stars",
                show_all=True,
                disable_cache=False,
                show_commits=5,
                force_all_commits=True,
                ahead_only=False,
                csv_export=True,
            )

    @pytest.mark.asyncio
    async def test_csv_export_with_ahead_only_filter(self, mock_github_client, sample_fork_data):
        """Test CSV export with --ahead-only filter."""
        display_service = RepositoryDisplayService(mock_github_client)

        with patch.object(display_service, "show_fork_data") as mock_show_fork_data:
            mock_show_fork_data.return_value = {
                "total_forks": 1,  # Filtered down
                "displayed_forks": 1,
                "collected_forks": [sample_fork_data[0]]  # Only fork with commits ahead
            }

            await _export_forks_csv(
                display_service,
                "owner/repo",
                max_forks=None,
                detail=False,
                show_commits=0,
                force_all_commits=False,
                ahead_only=True
            )

            # Verify ahead_only parameter was passed
            mock_show_fork_data.assert_called_once_with(
                "owner/repo",
                exclude_archived=False,
                exclude_disabled=False,
                sort_by="stars",
                show_all=True,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False,
                ahead_only=True,
                csv_export=True,
            )

    @pytest.mark.asyncio
    async def test_csv_export_error_handling(self, mock_github_client):
        """Test CSV export error handling sends errors to stderr."""
        display_service = RepositoryDisplayService(mock_github_client)

        # Mock stderr to capture error output
        captured_stderr = StringIO()

        with patch("sys.stderr", captured_stderr):
            with patch.object(display_service, "show_fork_data") as mock_show_fork_data:
                mock_show_fork_data.side_effect = Exception("Test error")

                with pytest.raises(Exception, match="Test error"):
                    await _export_forks_csv(
                        display_service,
                        "owner/repo",
                        max_forks=None,
                        detail=False,
                        show_commits=0,
                        force_all_commits=False,
                        ahead_only=False
                    )

                # Verify error was sent to stderr
                stderr_output = captured_stderr.getvalue()
                assert "Error exporting CSV data: Test error" in stderr_output

    @pytest.mark.asyncio
    async def test_show_forks_summary_csv_mode_routing(self, mock_config):
        """Test that _show_forks_summary properly routes to CSV export."""
        with patch("forklift.cli.GitHubClient") as mock_client_class:
            with patch("forklift.cli.RepositoryDisplayService") as mock_display_service_class:
                with patch("forklift.cli._export_forks_csv") as mock_export_csv:

                    # Configure mocks
                    mock_client = AsyncMock()
                    mock_client_class.return_value.__aenter__.return_value = mock_client
                    mock_display_service = MagicMock()
                    mock_display_service_class.return_value = mock_display_service

                    await _show_forks_summary(
                        mock_config,
                        "owner/repo",
                        max_forks=100,
                        verbose=False,
                        detail=True,
                        show_commits=3,
                        force_all_commits=True,
                        ahead_only=True,
                        csv=True,
                        interaction_mode=InteractionMode.NON_INTERACTIVE,
                        supports_prompts=False,
                    )

                    # Verify CSV export was called with correct parameters
                    mock_export_csv.assert_called_once_with(
                        mock_display_service,
                        "owner/repo",
                        100,  # max_forks
                        True,  # detail
                        3,     # show_commits
                        True,  # force_all_commits
                        True   # ahead_only
                    )

    @pytest.mark.asyncio
    async def test_show_forks_summary_non_csv_mode(self, mock_config):
        """Test that _show_forks_summary uses normal display when CSV is False."""
        with patch("forklift.cli.GitHubClient") as mock_client_class:
            with patch("forklift.cli.RepositoryDisplayService") as mock_display_service_class:
                with patch("forklift.cli._export_forks_csv") as mock_export_csv:

                    # Configure mocks
                    mock_client = AsyncMock()
                    mock_client_class.return_value.__aenter__.return_value = mock_client
                    mock_display_service = MagicMock()
                    mock_display_service_class.return_value = mock_display_service

                    # Mock the display service methods
                    mock_display_service.show_fork_data = AsyncMock(return_value={
                        "total_forks": 2,
                        "displayed_forks": 2
                    })

                    await _show_forks_summary(
                        mock_config,
                        "owner/repo",
                        max_forks=None,
                        verbose=False,
                        detail=False,
                        show_commits=0,
                        force_all_commits=False,
                        ahead_only=False,
                        csv=False,  # CSV disabled
                        interaction_mode=InteractionMode.FULLY_INTERACTIVE,
                        supports_prompts=True,
                    )

                    # Verify CSV export was NOT called
                    mock_export_csv.assert_not_called()

                    # Verify normal display was called
                    mock_display_service.show_fork_data.assert_called_once_with(
                        "owner/repo",
                        exclude_archived=False,
                        exclude_disabled=False,
                        sort_by="stars",
                        show_all=True,
                        disable_cache=False,
                        show_commits=0,
                        force_all_commits=False,
                        ahead_only=False,
                        csv_export=False,
                    )

    @pytest.mark.asyncio
    async def test_csv_export_with_show_commits_integration(self, mock_github_client):
        """Test CSV export with --show-commits flag integration."""
        from datetime import UTC, datetime

        from forkscout.models.fork_qualification import (
            CollectedForkData,
            ForkQualificationMetrics,
        )

        # Create fork data with commits ahead
        metrics = ForkQualificationMetrics(
            id=123,
            name="test-repo",
            full_name="user1/test-repo",
            owner="user1",
            html_url="https://github.com/user1/test-repo",
            stargazers_count=10,
            forks_count=2,
            watchers_count=5,
            size=1000,
            language="Python",
            topics=[],
            open_issues_count=3,
            created_at=datetime(2024, 1, 10, tzinfo=UTC),
            updated_at=datetime(2024, 1, 14, tzinfo=UTC),
            pushed_at=datetime(2024, 1, 15, tzinfo=UTC),  # After created = has commits
            archived=False,
            disabled=False,
            fork=True,
            license_key="mit",
            license_name="MIT License",
            description="Test repository",
            homepage=None,
            default_branch="main"
        )

        fork_data = CollectedForkData(metrics=metrics)

        display_service = RepositoryDisplayService(mock_github_client)

        # Mock commit fetching
        mock_commits = [
            {
                "message": "Fix authentication bug",
                "sha": "abc123",
                "date": "2024-01-15T10:00:00Z"
            },
            {
                "message": "Add new feature\nWith detailed description",
                "sha": "def456",
                "date": "2024-01-14T15:30:00Z"
            }
        ]

        # Capture CSV output
        captured_output = StringIO()

        with patch("sys.stdout", captured_output):
            with patch.object(display_service, "_fetch_raw_commits_for_csv") as mock_fetch_raw_commits:
                # Mock RecentCommit objects for CSV export
                from forkscout.models.github import RecentCommit
                from datetime import datetime, UTC
                
                mock_recent_commits = [
                    RecentCommit(
                        short_sha="abc1234",
                        message="Fix authentication bug",
                        date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
                    ),
                    RecentCommit(
                        short_sha="def4567",
                        message="Add new feature With detailed description",
                        date=datetime(2024, 1, 14, 15, 30, 0, tzinfo=UTC)
                    )
                ]
                
                mock_fetch_raw_commits.return_value = {
                    "https://github.com/user1/test-repo": mock_recent_commits
                }

                table_context = {
                    "owner": "owner",
                    "repo": "repo",
                    "has_exact_counts": False,
                    "mode": "standard"
                }

                await display_service._export_csv_data(
                    [fork_data],
                    table_context,
                    show_commits=2,  # Show 2 commits
                    force_all_commits=False
                )

        # Parse CSV output
        csv_output = captured_output.getvalue()
        reader = csv.DictReader(StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 1

        # Check that recent_commits header is present
        assert "recent_commits" in reader.fieldnames

        # Check that commit data is properly formatted with date, hash, and message
        row = rows[0]
        commits_text = row["recent_commits"]
        assert "2024-01-15 abc1234 Fix authentication bug" in commits_text
        assert "2024-01-14 def4567 Add new feature With detailed description" in commits_text
        # Verify newlines are removed and commits are separated by semicolons
        assert "\n" not in commits_text
        assert ";" in commits_text  # Multiple commits should be separated by semicolons

    @pytest.mark.asyncio
    async def test_csv_export_skips_forks_with_no_commits_ahead(self, mock_github_client):
        """Test CSV export optimization skips forks with no commits ahead."""
        from datetime import UTC, datetime

        from forkscout.models.fork_qualification import (
            CollectedForkData,
            ForkQualificationMetrics,
        )

        # Create fork data with no commits ahead (created_at >= pushed_at)
        metrics = ForkQualificationMetrics(
            id=123,
            name="test-repo",
            full_name="user1/test-repo",
            owner="user1",
            html_url="https://github.com/user1/test-repo",
            stargazers_count=5,
            forks_count=1,
            watchers_count=2,
            size=500,
            language="Python",
            topics=[],
            open_issues_count=1,
            created_at=datetime(2024, 1, 15, tzinfo=UTC),
            updated_at=datetime(2024, 1, 15, tzinfo=UTC),
            pushed_at=datetime(2024, 1, 15, tzinfo=UTC),  # Same as created = no commits
            archived=False,
            disabled=False,
            fork=True,
            license_key=None,
            license_name=None,
            description="Test repository",
            homepage=None,
            default_branch="main"
        )

        fork_data = CollectedForkData(metrics=metrics)

        display_service = RepositoryDisplayService(mock_github_client)

        # Capture CSV output
        captured_output = StringIO()

        with patch("sys.stdout", captured_output):
            with patch.object(display_service, "_fetch_raw_commits_for_csv") as mock_fetch_raw_commits:
                # Should not fetch commits for forks with no commits ahead
                mock_fetch_raw_commits.return_value = {
                    "https://github.com/user1/test-repo": []  # Empty list for no commits
                }

                table_context = {
                    "owner": "owner",
                    "repo": "repo",
                    "has_exact_counts": False,
                    "mode": "standard"
                }

                await display_service._export_csv_data(
                    [fork_data],
                    table_context,
                    show_commits=3,
                    force_all_commits=False  # Don't force commits for all forks
                )

        # Parse CSV output
        csv_output = captured_output.getvalue()
        reader = csv.DictReader(StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 1

        # Check that recent_commits header is present but empty for this fork
        assert "recent_commits" in reader.fieldnames
        row = rows[0]
        assert row["recent_commits"] == ""  # No commits fetched
        assert row["commits_ahead"] == "None"  # Should show "None" for no commits

    @pytest.mark.asyncio
    async def test_csv_export_maintains_fork_sorting(self, mock_github_client):
        """Test that CSV export maintains the same fork sorting as table display."""
        from datetime import UTC, datetime

        from forkscout.models.fork_qualification import (
            CollectedForkData,
            ForkQualificationMetrics,
        )

        # Create fork data with different star counts to test sorting
        metrics1 = ForkQualificationMetrics(
            id=123,
            name="test-repo",
            full_name="user1/test-repo",
            owner="user1",
            html_url="https://github.com/user1/test-repo",
            stargazers_count=5,  # Lower stars
            forks_count=1,
            watchers_count=2,
            size=1000,
            language="Python",
            topics=[],
            open_issues_count=1,
            created_at=datetime(2024, 1, 10, tzinfo=UTC),
            updated_at=datetime(2024, 1, 14, tzinfo=UTC),
            pushed_at=datetime(2024, 1, 15, tzinfo=UTC),
            archived=False,
            disabled=False,
            fork=True,
            license_key=None,
            license_name=None,
            description="Test repository 1",
            homepage=None,
            default_branch="main"
        )

        metrics2 = ForkQualificationMetrics(
            id=456,
            name="test-repo",
            full_name="user2/test-repo",
            owner="user2",
            html_url="https://github.com/user2/test-repo",
            stargazers_count=10,  # Higher stars
            forks_count=2,
            watchers_count=5,
            size=2000,
            language="JavaScript",
            topics=[],
            open_issues_count=2,
            created_at=datetime(2024, 1, 15, tzinfo=UTC),
            updated_at=datetime(2024, 1, 19, tzinfo=UTC),
            pushed_at=datetime(2024, 1, 20, tzinfo=UTC),
            archived=False,
            disabled=False,
            fork=True,
            license_key="apache-2.0",
            license_name="Apache License 2.0",
            description="Test repository 2",
            homepage=None,
            default_branch="main"
        )

        fork1 = CollectedForkData(metrics=metrics1)
        fork2 = CollectedForkData(metrics=metrics2)

        unsorted_forks = [fork1, fork2]  # Lower stars first

        display_service = RepositoryDisplayService(mock_github_client)

        # Capture CSV output
        captured_output = StringIO()

        with patch("sys.stdout", captured_output):
            with patch.object(display_service, "_sort_forks_universal") as mock_sort:
                # Mock sorting to return higher stars first
                mock_sort.return_value = [fork2, fork1]  # Higher stars first

                # Mock the data collection to return our test data
                table_context = {
                    "owner": "owner",
                    "repo": "repo",
                    "has_exact_counts": False,
                    "mode": "standard"
                }

                await display_service._export_csv_data(
                    unsorted_forks,
                    table_context,
                    show_commits=0,
                    force_all_commits=False
                )

                # Verify sorting was called
                mock_sort.assert_called_once_with(unsorted_forks, False)

        # Check that CSV output exists (sorting verification is in the mock)
        csv_output = captured_output.getvalue()
        assert len(csv_output) > 0
        assert "fork_name" in csv_output  # Header should be present
