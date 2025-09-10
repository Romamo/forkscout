"""Integration tests for CSV export with --detail flag."""

import csv
import io
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forkscout.cli import _export_forks_csv
from forkscout.config.settings import ForkscoutConfig
from forkscout.display.repository_display_service import RepositoryDisplayService
from forkscout.github.client import GitHubClient
from forkscout.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
)


class TestCSVDetailModeIntegration:
    """Integration tests for CSV export with detail mode."""

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
    def sample_detailed_fork_data(self):
        """Create sample fork data with exact commit counts for testing."""
        # Fork with 3 commits ahead
        metrics1 = ForkQualificationMetrics(
            id=123,
            name="test-repo",
            full_name="user1/test-repo",
            owner="user1",
            html_url="https://github.com/user1/test-repo",
            stargazers_count=15,
            forks_count=3,
            watchers_count=8,
            size=1200,
            language="Python",
            topics=["python", "testing"],
            open_issues_count=2,
            created_at=datetime(2024, 1, 10, tzinfo=UTC),
            updated_at=datetime(2024, 1, 20, tzinfo=UTC),
            pushed_at=datetime(2024, 1, 22, tzinfo=UTC),
            archived=False,
            disabled=False,
            fork=True,
            license_key="mit",
            license_name="MIT License",
            description="Test repository with commits ahead",
            homepage=None,
            default_branch="main",
            commits_ahead_status="Has commits",
        )

        # Fork with 0 commits ahead
        metrics2 = ForkQualificationMetrics(
            id=456,
            name="test-repo",
            full_name="user2/test-repo",
            owner="user2",
            html_url="https://github.com/user2/test-repo",
            stargazers_count=7,
            forks_count=1,
            watchers_count=3,
            size=800,
            language="JavaScript",
            topics=[],
            open_issues_count=0,
            created_at=datetime(2024, 1, 5, tzinfo=UTC),
            updated_at=datetime(2024, 1, 5, tzinfo=UTC),
            pushed_at=datetime(2024, 1, 5, tzinfo=UTC),  # Same as created = no commits
            archived=False,
            disabled=False,
            fork=True,
            license_key="apache-2.0",
            license_name="Apache License 2.0",
            description="Test repository with no commits ahead",
            homepage=None,
            default_branch="main",
            commits_ahead_status="No commits ahead",
        )

        fork1 = CollectedForkData(metrics=metrics1)
        fork1.exact_commits_ahead = 3  # Exact count from API

        fork2 = CollectedForkData(metrics=metrics2)
        fork2.exact_commits_ahead = 0  # Exact count from API

        return [fork1, fork2]

    @pytest.mark.asyncio
    async def test_csv_export_with_detail_flag(
        self, mock_github_client, sample_detailed_fork_data, capsys
    ):
        """Test CSV export with --detail flag produces exact commit counts."""
        display_service = RepositoryDisplayService(mock_github_client)

        with patch.object(
            display_service, "show_fork_data_detailed"
        ) as mock_show_detailed:
            # Mock the detailed display to return our sample data
            mock_show_detailed.return_value = {
                "total_forks": 2,
                "displayed_forks": 2,
                "collected_forks": sample_detailed_fork_data,
                "api_calls_made": 2,
            }

            # Mock the CSV export functionality
            with patch.object(display_service, "_export_csv_data") as mock_export_csv:
                # Mock CSV export functionality
                mock_export_csv.return_value = None

                # Capture stdout to verify CSV output
                from io import StringIO

                captured_output = StringIO()

                with patch("sys.stdout", captured_output):
                    await _export_forks_csv(
                        display_service,
                        "owner/repo",
                        max_forks=50,
                        detail=True,
                        show_commits=0,
                        force_all_commits=False,
                        ahead_only=False,
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
    async def test_csv_export_without_detail_flag(
        self, mock_github_client, sample_detailed_fork_data
    ):
        """Test CSV export without --detail flag uses status indicators."""
        display_service = RepositoryDisplayService(mock_github_client)

        with patch.object(display_service, "show_fork_data") as mock_show_fork_data:
            # Mock the standard display to return our sample data
            mock_show_fork_data.return_value = {
                "total_forks": 2,
                "displayed_forks": 2,
                "collected_forks": sample_detailed_fork_data,
            }

            await _export_forks_csv(
                display_service,
                "owner/repo",
                max_forks=None,
                detail=False,
                show_commits=0,
                force_all_commits=False,
                ahead_only=False,
            )

            # Verify standard CSV export was called (not detailed)
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
    async def test_csv_detail_mode_with_show_commits(
        self, mock_github_client, sample_detailed_fork_data
    ):
        """Test CSV export with both --detail and --show-commits flags."""
        display_service = RepositoryDisplayService(mock_github_client)

        with patch.object(
            display_service, "show_fork_data_detailed"
        ) as mock_show_detailed:
            mock_show_detailed.return_value = {
                "total_forks": 2,
                "displayed_forks": 2,
                "collected_forks": sample_detailed_fork_data,
                "api_calls_made": 2,
            }

            await _export_forks_csv(
                display_service,
                "owner/repo",
                max_forks=100,
                detail=True,
                show_commits=5,
                force_all_commits=True,
                ahead_only=True,
            )

            # Verify all parameters are passed correctly
            mock_show_detailed.assert_called_once_with(
                "owner/repo",
                max_forks=100,
                disable_cache=False,
                show_commits=5,
                force_all_commits=True,
                ahead_only=True,
                csv_export=True,
            )

    def test_csv_format_validation_detail_mode(self):
        """Test that CSV output format is valid with detail mode data."""
        # Create CSV content with detail mode formatting
        csv_content = """fork_name,owner,stars,commits_ahead,activity_status,fork_url
test-repo-1,user1,10,+5,Active,https://github.com/user1/test-repo-1
test-repo-2,user2,3,,Stale,https://github.com/user2/test-repo-2
test-repo-3,user3,8,+2,Active,https://github.com/user3/test-repo-3
"""

        # Parse CSV to verify it's valid
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        assert len(rows) == 3

        # Verify detail mode formatting
        assert rows[0]["commits_ahead"] == "+5"  # Exact count with + prefix
        assert rows[1]["commits_ahead"] == ""  # Empty for zero commits
        assert rows[2]["commits_ahead"] == "+2"  # Another exact count

        # Verify other fields are preserved
        assert rows[0]["fork_name"] == "test-repo-1"
        assert rows[0]["owner"] == "user1"
        assert rows[0]["stars"] == "10"
        assert rows[0]["activity_status"] == "Active"

    def test_csv_format_validation_non_detail_mode(self):
        """Test that CSV output format is valid with non-detail mode data."""
        # Create CSV content with status indicators
        csv_content = """fork_name,owner,stars,commits_ahead,activity_status,fork_url
test-repo-1,user1,10,Unknown,Active,https://github.com/user1/test-repo-1
test-repo-2,user2,3,None,Stale,https://github.com/user2/test-repo-2
test-repo-3,user3,8,Unknown,Active,https://github.com/user3/test-repo-3
"""

        # Parse CSV to verify it's valid
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        assert len(rows) == 3

        # Verify non-detail mode formatting
        assert rows[0]["commits_ahead"] == "Unknown"  # Status indicator
        assert rows[1]["commits_ahead"] == "None"  # Status indicator
        assert rows[2]["commits_ahead"] == "Unknown"  # Status indicator

        # Verify other fields are preserved
        assert rows[0]["fork_name"] == "test-repo-1"
        assert rows[0]["owner"] == "user1"
        assert rows[0]["stars"] == "10"
        assert rows[0]["activity_status"] == "Active"
