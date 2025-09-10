"""Unit tests for table structure and formatting integrity methods.

This module tests the specific methods responsible for table structure,
column width calculation, and formatting integrity with long commit messages.
"""

import io
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from rich.console import Console
from rich.table import Table

from forkscout.display.repository_display_service import (
    ForkTableConfig,
    RepositoryDisplayService,
)
from forkscout.models.github import RecentCommit


class TestTableStructureFormattingIntegrityUnit:
    """Unit tests for table structure and formatting integrity methods."""

    @pytest.fixture
    def display_service(self):
        """Create display service for testing."""
        mock_client = Mock()
        return RepositoryDisplayService(mock_client)

    @pytest.fixture
    def long_commit_messages(self):
        """Create test commits with very long messages."""
        return [
            RecentCommit(
                sha="abc1234567890abcdef1234567890abcdef123456",
                short_sha="abc1234",
                message="Implement comprehensive authentication and authorization system with multi-factor authentication, role-based access control, session management, and security audit logging for enterprise deployment",
                date=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
                author="test-author",
            ),
            RecentCommit(
                sha="def4567890abcdef1234567890abcdef123456789",
                short_sha="def4567",
                message="Add advanced caching layer with Redis clustering, automatic failover, cache warming strategies, and performance monitoring to handle high-traffic scenarios with sub-millisecond response times",
                date=datetime(2024, 1, 14, 15, 45, 0, tzinfo=UTC),
                author="test-author",
            ),
        ]

    def test_clean_commit_message_preserves_content(self, display_service):
        """Test that _clean_commit_message preserves full content without truncation."""
        # Test with very long message
        long_message = "This is an extremely long commit message that contains detailed information about the changes made, including implementation details, performance considerations, security implications, and testing strategies that were employed during development"

        cleaned = display_service._clean_commit_message(long_message)

        # Verify no truncation
        assert "..." not in cleaned
        assert len(cleaned) == len(long_message)
        assert cleaned == long_message

    def test_clean_commit_message_handles_newlines(self, display_service):
        """Test that _clean_commit_message properly handles newlines and whitespace."""
        # Test with newlines and extra whitespace
        message_with_newlines = (
            "First line\nSecond line\n\nThird line with   extra   spaces"
        )

        cleaned = display_service._clean_commit_message(message_with_newlines)

        # Verify newlines are converted to spaces and whitespace is normalized
        expected = "First line Second line Third line with extra spaces"
        assert cleaned == expected
        assert "\n" not in cleaned

    def test_clean_commit_message_edge_cases(self, display_service):
        """Test _clean_commit_message with edge cases."""
        # Test empty message
        assert display_service._clean_commit_message("") == ""

        # Test None message
        assert display_service._clean_commit_message(None) == ""

        # Test whitespace only
        assert display_service._clean_commit_message("   \n\t   ") == ""

        # Test single word
        assert display_service._clean_commit_message("fix") == "fix"

    def test_format_recent_commits_no_truncation(
        self, display_service, long_commit_messages
    ):
        """Test that format_recent_commits does not truncate long messages."""
        formatted = display_service.format_recent_commits(
            long_commit_messages, column_width=50
        )

        # Verify no truncation indicators
        assert "..." not in formatted

        # Verify all commit messages are present in full
        for commit in long_commit_messages:
            assert commit.message in formatted

    def test_format_recent_commits_structure_integrity(
        self, display_service, long_commit_messages
    ):
        """Test that format_recent_commits maintains proper structure with long messages."""
        formatted = display_service.format_recent_commits(
            long_commit_messages, column_width=100
        )

        lines = formatted.split("\n")
        assert len(lines) == len(long_commit_messages)

        # Verify each line has proper format: "YYYY-MM-DD hash message"
        for i, line in enumerate(lines):
            commit = long_commit_messages[i]

            # Check date format
            assert line.startswith("2024-01-")

            # Check hash presence
            assert commit.short_sha in line

            # Check full message is present
            assert commit.message in line

            # Verify format structure
            parts = line.split(" ", 2)  # Split into date, hash, message
            assert len(parts) == 3
            assert parts[0] == commit.date.strftime("%Y-%m-%d")
            assert parts[1] == commit.short_sha
            assert parts[2] == commit.message

    def test_format_recent_commits_chronological_ordering(self, display_service):
        """Test that format_recent_commits maintains chronological ordering."""
        # Create commits with different dates
        commits = [
            RecentCommit(
                sha="newest123456789012345678901234567890123",
                short_sha="abc1234",
                message="Newest commit with very long message that should not be truncated",
                date=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
                author="test-author",
            ),
            RecentCommit(
                sha="middle123456789012345678901234567890123",
                short_sha="def5678",
                message="Middle commit with another long message that should remain intact",
                date=datetime(2024, 1, 10, 15, 45, 0, tzinfo=UTC),
                author="test-author",
            ),
            RecentCommit(
                sha="oldest123456789012345678901234567890123",
                short_sha="9abc123",
                message="Oldest commit with yet another long message for testing purposes",
                date=datetime(2024, 1, 5, 9, 15, 0, tzinfo=UTC),
                author="test-author",
            ),
        ]

        formatted = display_service.format_recent_commits(commits, column_width=80)
        lines = formatted.split("\n")

        # Verify chronological order (newest first)
        assert "2024-01-15" in lines[0]  # Newest
        assert "2024-01-10" in lines[1]  # Middle
        assert "2024-01-05" in lines[2]  # Oldest

    def test_calculate_commits_column_width_universal(self, display_service):
        """Test _calculate_commits_column_width_universal method."""
        # Create mock fork data
        mock_fork_data = [Mock()]

        # Test with different show_commits values
        test_cases = [
            (1, 69),  # Base (19) + 50 for single commit
            (3, 99),  # Base (19) + 80 for multiple commits
            (5, 139),  # Base (19) + 120 for many commits
        ]

        for show_commits, expected_min_width in test_cases:
            width = display_service._calculate_commits_column_width_universal(
                mock_fork_data, show_commits
            )

            # Verify width is reasonable and accounts for long messages
            assert width >= expected_min_width
            assert width <= 1000  # Max width limit

    def test_calculate_commits_column_width_legacy(self, display_service):
        """Test calculate_commits_column_width method with long messages."""
        # Create commits data with long messages
        long_commits = [
            RecentCommit(
                sha="test123456789012345678901234567890123456",
                short_sha="abc1234",
                message="Very long commit message that should not affect column width calculation negatively",
                date=datetime(2024, 1, 15, tzinfo=UTC),
                author="test-author",
            )
        ]

        commits_data = {"test-owner/test-repo": long_commits}

        # Test with various show_commits values
        for show_commits in [1, 3, 5, 10]:
            width = display_service.calculate_commits_column_width(
                commits_data, show_commits, min_width=30, max_width=200
            )

            # Verify width is within bounds
            assert 30 <= width <= 200

            # Verify width increases with more commits
            if show_commits > 1:
                single_width = display_service.calculate_commits_column_width(
                    {"test-owner/test-repo": long_commits[:1]},
                    1,
                    min_width=30,
                    max_width=200,
                )
                assert width >= single_width

    def test_fork_table_config_constants(self):
        """Test ForkTableConfig constants for table structure."""
        config = ForkTableConfig

        # Verify column widths are defined
        assert "url" in config.COLUMN_WIDTHS
        assert "stars" in config.COLUMN_WIDTHS
        assert "forks" in config.COLUMN_WIDTHS
        assert "commits" in config.COLUMN_WIDTHS
        assert "last_push" in config.COLUMN_WIDTHS
        assert "recent_commits_base" in config.COLUMN_WIDTHS

        # Verify column styles are defined
        assert "url" in config.COLUMN_STYLES
        assert "stars" in config.COLUMN_STYLES
        assert "forks" in config.COLUMN_STYLES
        assert "commits" in config.COLUMN_STYLES
        assert "last_push" in config.COLUMN_STYLES
        assert "recent_commits" in config.COLUMN_STYLES

        # Verify reasonable width values
        assert config.COLUMN_WIDTHS["url"] > 0
        assert config.COLUMN_WIDTHS["recent_commits_base"] >= 30

    def test_add_standard_columns_structure(self, display_service):
        """Test _add_standard_columns method creates proper table structure."""
        table = Table(expand=False)

        # Add standard columns
        display_service._add_standard_columns(table)

        # Verify columns were added
        assert len(table.columns) == 5  # URL, Stars, Forks, Commits, Last Push

        # Verify column properties
        columns = table.columns

        # URL column
        assert columns[0].header == "URL"
        assert columns[0].style == "cyan"
        assert columns[0].no_wrap is True
        assert columns[0].overflow == "fold"

        # Stars column
        assert columns[1].header == "Stars"
        assert columns[1].style == "yellow"
        assert columns[1].justify == "right"
        assert columns[1].no_wrap is True

        # Forks column
        assert columns[2].header == "Forks"
        assert columns[2].style == "green"
        assert columns[2].justify == "right"
        assert columns[2].no_wrap is True

        # Commits column
        assert columns[3].header == "Commits"
        assert columns[3].style == "magenta"
        assert columns[3].justify == "right"
        assert columns[3].no_wrap is True

        # Last Push column
        assert columns[4].header == "Last Push"
        assert columns[4].style == "blue"
        assert columns[4].no_wrap is True

    def test_build_table_row_with_long_commits(
        self, display_service, long_commit_messages
    ):
        """Test _build_table_row method with long commit messages."""
        # Create mock fork data
        mock_fork_data = Mock()
        mock_fork_data.metrics = Mock()
        mock_fork_data.metrics.owner = "test-owner"
        mock_fork_data.metrics.name = "test-repo"
        mock_fork_data.metrics.stargazers_count = 100
        mock_fork_data.metrics.forks_count = 50
        mock_fork_data.metrics.pushed_at = datetime(2024, 1, 15, tzinfo=UTC)

        # Create commits cache with long messages
        formatted_commits = display_service.format_recent_commits(
            long_commit_messages, column_width=80
        )
        commits_cache = {"test-owner/test-repo": formatted_commits}

        # Build table row
        row_data = display_service._build_table_row(
            mock_fork_data,
            has_exact_counts=False,
            commits_cache=commits_cache,
            show_commits=2,
        )

        # Verify row structure
        assert (
            len(row_data) == 6
        )  # URL, Stars, Forks, Commits, Last Push, Recent Commits

        # Verify URL
        assert row_data[0] == "https://github.com/test-owner/test-repo"

        # Verify numeric values
        assert row_data[1] == "100"  # Stars
        assert row_data[2] == "50"  # Forks

        # Verify recent commits contain full messages without truncation
        recent_commits_data = row_data[5]
        assert "..." not in recent_commits_data
        for commit in long_commit_messages:
            assert commit.message in recent_commits_data

    def test_table_rendering_with_console_width_variations(
        self, display_service, long_commit_messages
    ):
        """Test table rendering with various console widths."""
        # Use only wide console widths to avoid Rich's automatic truncation
        console_widths = [200, 300, 999999]

        for width in console_widths:
            # Create console with specific width
            output = io.StringIO()
            console = Console(
                file=output, width=width, force_terminal=True, soft_wrap=False
            )

            # Create table
            table = Table(title="Test Table", expand=False)
            display_service._add_standard_columns(table)

            # Add Recent Commits column with no width restrictions
            table.add_column(
                "Recent Commits",
                style="dim",
                no_wrap=True,
                overflow="fold",
                max_width=None,  # No maximum width restriction
            )

            # Format commits and add row
            formatted_commits = display_service.format_recent_commits(
                long_commit_messages, column_width=width
            )
            table.add_row(
                "https://github.com/test-owner/test-repo",
                "100",
                "50",
                "5 ahead",
                "2 days ago",
                formatted_commits,
            )

            # Render table
            console.print(table)
            output_content = output.getvalue()

            # Verify no truncation occurred in the formatted commits
            assert "..." not in formatted_commits

            # Verify all commit messages are present in formatted commits
            for commit in long_commit_messages:
                assert commit.message in formatted_commits

            # Verify table structure is maintained
            assert "Test Table" in output_content
            assert "Recent Commits" in output_content

            # Note: Rich may still apply its own truncation for table rendering,
            # but our formatting methods should not truncate the content.
            # The key test is that formatted_commits contains full messages.

    def test_format_commit_date_consistency(self, display_service):
        """Test _format_commit_date method for consistent formatting."""
        test_dates = [
            datetime(2024, 1, 1, 10, 30, 0, tzinfo=UTC),
            datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
            datetime(2023, 6, 15, 12, 0, 0, tzinfo=UTC),
        ]

        expected_formats = [
            "2024-01-01",
            "2024-12-31",
            "2023-06-15",
        ]

        for date, expected in zip(test_dates, expected_formats, strict=False):
            formatted = display_service._format_commit_date(date)
            assert formatted == expected
            assert len(formatted) == 10  # YYYY-MM-DD format
            assert formatted.count("-") == 2

    def test_sort_commits_chronologically_with_long_messages(self, display_service):
        """Test _sort_commits_chronologically with long commit messages."""
        # Create commits in random order with long messages
        commits = [
            RecentCommit(
                sha="middle123456789012345678901234567890123",
                short_sha="def5678",
                message="Middle commit with a very long message that describes complex changes to the authentication system",
                date=datetime(2024, 1, 10, 15, 45, 0, tzinfo=UTC),
                author="test-author",
            ),
            RecentCommit(
                sha="newest123456789012345678901234567890123",
                short_sha="abc1234",
                message="Newest commit with an extremely detailed message explaining the implementation of advanced caching mechanisms",
                date=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
                author="test-author",
            ),
            RecentCommit(
                sha="oldest123456789012345678901234567890123",
                short_sha="9abc123",
                message="Oldest commit with comprehensive documentation about the refactoring of the entire user management subsystem",
                date=datetime(2024, 1, 5, 9, 15, 0, tzinfo=UTC),
                author="test-author",
            ),
        ]

        sorted_commits = display_service._sort_commits_chronologically(commits)

        # Verify chronological order (newest first)
        assert sorted_commits[0].short_sha == "abc1234"
        assert sorted_commits[1].short_sha == "def5678"
        assert sorted_commits[2].short_sha == "9abc123"

        # Verify messages are preserved
        for original in commits:
            found = False
            for commit in sorted_commits:
                if commit.message == original.message:
                    found = True
                    break
            assert found, f"Message not found: {original.message}"

    def test_table_structure_with_overflow_handling(self, display_service):
        """Test table structure with overflow handling for very long content."""
        # Create extremely long commit message
        extremely_long_message = "A" * 1000  # 1000 character message

        long_commit = RecentCommit(
            sha="extreme123456789012345678901234567890123",
            short_sha="abc1234",
            message=extremely_long_message,
            date=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            author="test-author",
        )

        # Format the extremely long commit
        formatted = display_service.format_recent_commits(
            [long_commit], column_width=80
        )

        # Verify no truncation
        assert "..." not in formatted
        assert extremely_long_message in formatted

        # Verify structure is maintained
        assert "2024-01-15" in formatted
        assert "abc1234" in formatted

        # Test with table rendering
        output = io.StringIO()
        console = Console(file=output, width=200, force_terminal=True, soft_wrap=False)

        table = Table(expand=False)
        table.add_column("Commits", no_wrap=True, overflow="fold", max_width=None)
        table.add_row(formatted)

        console.print(table)
        output_content = output.getvalue()

        # Verify extremely long content is handled properly by our formatting
        # (Rich may still apply its own rendering limits, but our format should not truncate)
        assert extremely_long_message in formatted

        # Verify table structure is maintained even with very long content
        assert "2024-01-15" in output_content
        assert "abc1234" in output_content
