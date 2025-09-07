"""Unit tests for CSV export detail mode functionality."""

import csv
import io
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.models.analysis import ForkPreviewItem, ForksPreview
from forklift.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
)
from forklift.reporting.csv_exporter import CSVExportConfig, CSVExporter


class TestCSVDetailMode:
    """Test CSV export with detail mode for exact commit counts."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return MagicMock()

    @pytest.fixture
    def display_service(self, mock_github_client):
        """Create a repository display service."""
        return RepositoryDisplayService(mock_github_client)

    @pytest.fixture
    def sample_fork_data_with_exact_counts(self):
        """Create sample fork data with exact commit counts."""
        # Fork with 5 commits ahead
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
            stargazers_count=5,
            forks_count=1,
            watchers_count=2,
            size=500,
            language="JavaScript",
            topics=[],
            open_issues_count=1,
            created_at=datetime(2024, 1, 5, tzinfo=UTC),
            updated_at=datetime(2024, 1, 5, tzinfo=UTC),
            pushed_at=datetime(2024, 1, 5, tzinfo=UTC),
            archived=False,
            disabled=False,
            fork=True,
            license_key=None,
            license_name=None,
            description="Another test repository",
            homepage=None,
            default_branch="main",
            commits_ahead_status="No commits ahead",
        )

        fork1 = CollectedForkData(metrics=metrics1)
        fork1.exact_commits_ahead = 5  # Add exact count

        fork2 = CollectedForkData(metrics=metrics2)
        fork2.exact_commits_ahead = 0  # Add exact count

        return [fork1, fork2]

    def test_convert_fork_data_to_preview_item_csv_detail_mode(
        self, display_service, sample_fork_data_with_exact_counts
    ):
        """Test CSV conversion with detail mode formatting."""
        fork_data = sample_fork_data_with_exact_counts[0]  # Fork with 5 commits ahead

        # Convert to CSV format with exact counts
        preview_item = display_service._convert_fork_data_to_preview_item_csv(
            fork_data=fork_data,
            has_exact_counts=True,
            raw_commits_cache={},
            show_commits=0,
        )

        # Should use "+X" format for exact counts
        assert preview_item.commits_ahead == "+5"
        assert preview_item.name == "test-repo"
        assert preview_item.owner == "user1"
        assert preview_item.stars == 10

    def test_convert_fork_data_to_preview_item_csv_detail_mode_zero_commits(
        self, display_service, sample_fork_data_with_exact_counts
    ):
        """Test CSV conversion with detail mode for fork with zero commits ahead."""
        fork_data = sample_fork_data_with_exact_counts[1]  # Fork with 0 commits ahead

        # Convert to CSV format with exact counts
        preview_item = display_service._convert_fork_data_to_preview_item_csv(
            fork_data=fork_data,
            has_exact_counts=True,
            raw_commits_cache={},
            show_commits=0,
        )

        # Should use empty string for zero commits in detail mode
        assert preview_item.commits_ahead == ""
        assert preview_item.name == "test-repo"
        assert preview_item.owner == "user2"
        assert preview_item.stars == 5

    def test_convert_fork_data_to_preview_item_csv_non_detail_mode(
        self, display_service, sample_fork_data_with_exact_counts
    ):
        """Test CSV conversion without detail mode uses status indicators."""
        fork_data = sample_fork_data_with_exact_counts[0]  # Fork with commits ahead

        # Convert to CSV format without exact counts
        preview_item = display_service._convert_fork_data_to_preview_item_csv(
            fork_data=fork_data,
            has_exact_counts=False,
            raw_commits_cache={},
            show_commits=0,
        )

        # Should use status indicator, not exact count
        assert preview_item.commits_ahead == "Unknown"  # Based on status from metrics

    def test_csv_exporter_detail_mode_headers(self):
        """Test that CSV exporter includes proper headers for detail mode."""
        config = CSVExportConfig(detail_mode=True, include_urls=True)
        exporter = CSVExporter(config)

        headers = exporter._generate_forks_preview_headers()

        # Should include detail mode headers (new title case format)
        assert "Fork URL" in headers
        assert "Stars" in headers
        assert "Commits Ahead" in headers
        assert "Last Push Date" in headers
        assert "Created Date" in headers
        assert "Updated Date" in headers

    def test_csv_export_with_detail_mode_formatting(self):
        """Test complete CSV export with detail mode formatting."""
        # Create sample data with exact commit counts
        fork1 = ForkPreviewItem(
            name="test-repo-1",
            owner="user1",
            stars=10,
            last_push_date=datetime(2024, 1, 15, tzinfo=UTC),
            fork_url="https://github.com/user1/test-repo-1",
            activity_status="Active",
            commits_ahead="+5",  # Detail mode format
            recent_commits=None,
        )

        fork2 = ForkPreviewItem(
            name="test-repo-2",
            owner="user2",
            stars=3,
            last_push_date=datetime(2024, 1, 10, tzinfo=UTC),
            fork_url="https://github.com/user2/test-repo-2",
            activity_status="Stale",
            commits_ahead="",  # Empty for zero commits in detail mode
            recent_commits=None,
        )

        preview = ForksPreview(total_forks=2, forks=[fork1, fork2])

        # Export with detail mode
        config = CSVExportConfig(detail_mode=True, include_urls=True)
        exporter = CSVExporter(config)
        csv_output = exporter.export_forks_preview(preview)

        # Parse CSV output
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 2

        # Check first row (fork with commits ahead)
        # Check first row data (new title case format)
        assert "test-repo-1" in rows[0]["Fork URL"]
        assert "user1" in rows[0]["Fork URL"]
        assert rows[0]["Stars"] == "10"
        assert rows[0]["Commits Ahead"] == "+5"  # Should be in "+X" format
        assert rows[0]["Fork URL"] == "https://github.com/user1/test-repo-1"

        # Check second row (fork with no commits ahead)
        assert "test-repo-2" in rows[1]["Fork URL"]
        assert "user2" in rows[1]["Fork URL"]
        assert rows[1]["Stars"] == "3"
        assert rows[1]["Commits Ahead"] == ""  # Should be empty for zero commits
        # Note: activity_status is not included in basic forks preview export
        assert rows[1]["Fork URL"] == "https://github.com/user2/test-repo-2"

    def test_csv_export_non_detail_mode_formatting(self):
        """Test CSV export without detail mode uses status indicators."""
        # Create sample data with status indicators
        fork1 = ForkPreviewItem(
            name="test-repo-1",
            owner="user1",
            stars=10,
            last_push_date=datetime(2024, 1, 15, tzinfo=UTC),
            fork_url="https://github.com/user1/test-repo-1",
            activity_status="Active",
            commits_ahead="Unknown",  # Status indicator format
            recent_commits=None,
        )

        fork2 = ForkPreviewItem(
            name="test-repo-2",
            owner="user2",
            stars=3,
            last_push_date=datetime(2024, 1, 10, tzinfo=UTC),
            fork_url="https://github.com/user2/test-repo-2",
            activity_status="Stale",
            commits_ahead="None",  # Status indicator format
            recent_commits=None,
        )

        preview = ForksPreview(total_forks=2, forks=[fork1, fork2])

        # Export without detail mode
        config = CSVExportConfig(detail_mode=False, include_urls=True)
        exporter = CSVExporter(config)
        csv_output = exporter.export_forks_preview(preview)

        # Parse CSV output
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 2

        # Check Commits Ahead uses status indicators (new title case format)
        assert rows[0]["Commits Ahead"] == "Unknown"
        assert rows[1]["Commits Ahead"] == "None"
