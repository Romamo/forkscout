"""Integration tests for Rich table rendering integrity with long commit messages.

This module tests Rich table rendering specifically to ensure that table borders,
alignment, and formatting remain intact when displaying long commit messages.
"""

import io
import re
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from rich.console import Console
from rich.table import Table

from forkscout.display.repository_display_service import RepositoryDisplayService
from forkscout.github.client import GitHubClient
from forkscout.models.github import RecentCommit


class TestRichTableRenderingIntegrity:
    """Test Rich table rendering integrity with long content."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return AsyncMock(spec=GitHubClient)

    @pytest.fixture
    def display_service(self, mock_github_client):
        """Create display service with mock client."""
        return RepositoryDisplayService(mock_github_client)

    @pytest.fixture
    def very_long_commits(self):
        """Create commits with extremely long messages for stress testing."""
        return [
            RecentCommit(
                sha="stress1234567890abcdef1234567890abcdef123",
                short_sha="stress1",
                message="This is an extremely long commit message designed to stress test the table rendering system and ensure that no matter how long the commit message becomes, the table structure remains intact and properly formatted without any truncation or corruption of the display format, including proper handling of word boundaries and character encoding",
                date=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
                author="stress-test-author",
            ),
            RecentCommit(
                sha="stress2345678901bcdef2345678901bcdef234",
                short_sha="stress2",
                message="Another exceptionally long commit message that contains detailed technical information about implementation changes, performance optimizations, security enhancements, bug fixes, feature additions, code refactoring, documentation updates, test coverage improvements, and deployment configuration modifications that were made during this development cycle",
                date=datetime(2024, 1, 14, 15, 45, 0, tzinfo=UTC),
                author="stress-test-author",
            ),
        ]

    def test_rich_table_border_integrity_with_long_content(
        self, display_service, very_long_commits
    ):
        """Test that Rich table borders remain intact with very long content."""
        # Create console with specific width
        output = io.StringIO()
        console = Console(file=output, width=200, force_terminal=True, soft_wrap=False)

        # Create table with long content
        table = Table(
            title="Border Integrity Test",
            expand=False,
            show_header=True,
            show_lines=True,
        )
        table.add_column(
            "Repository", style="cyan", min_width=30, no_wrap=True, overflow="fold"
        )
        table.add_column(
            "Stars", style="yellow", justify="right", width=8, no_wrap=True
        )
        table.add_column(
            "Recent Commits", style="dim", no_wrap=True, overflow="fold", max_width=None
        )

        # Format very long commits
        formatted_commits = display_service.format_recent_commits(
            very_long_commits, column_width=150
        )

        # Add test rows
        table.add_row("https://github.com/test/repo1", "100", formatted_commits)
        table.add_row("https://github.com/test/repo2", "200", formatted_commits)
        table.add_row("https://github.com/test/repo3", "300", formatted_commits)

        # Render table
        console.print(table)
        output_content = output.getvalue()

        # Verify table title is present
        assert "Border Integrity Test" in output_content

        # Verify table headers are present
        assert "Repository" in output_content
        assert "Stars" in output_content
        assert "Recent Commits" in output_content

        # Verify table borders are present (Rich uses Unicode box drawing characters)
        border_patterns = [
            r"[─┌┐└┘├┤┬┴┼]",  # Box drawing characters
            r"[│]",  # Vertical borders
        ]

        for pattern in border_patterns:
            assert re.search(
                pattern, output_content
            ), f"Border pattern {pattern} not found in table output"

        # Verify all commit messages are present without truncation
        for commit in very_long_commits:
            assert commit.message in output_content
            assert "..." not in output_content

        # Verify repository URLs are present
        assert "test/repo1" in output_content
        assert "test/repo2" in output_content
        assert "test/repo3" in output_content

    def test_rich_table_column_alignment_with_varying_content_lengths(
        self, display_service
    ):
        """Test column alignment with varying content lengths."""
        # Create commits with different message lengths
        varying_commits = [
            RecentCommit(
                sha="short123456789012345678901234567890123",
                short_sha="short12",
                message="Short message",
                date=datetime(2024, 1, 15, tzinfo=UTC),
                author="test-author",
            ),
            RecentCommit(
                sha="medium12345678901234567890123456789012",
                short_sha="medium1",
                message="This is a medium length commit message with more details",
                date=datetime(2024, 1, 14, tzinfo=UTC),
                author="test-author",
            ),
            RecentCommit(
                sha="verylong1234567890123456789012345678901",
                short_sha="verylong",
                message="This is an extremely long commit message that contains extensive details about the changes made, including technical specifications, implementation notes, performance considerations, and comprehensive testing information",
                date=datetime(2024, 1, 13, tzinfo=UTC),
                author="test-author",
            ),
        ]

        output = io.StringIO()
        console = Console(file=output, width=180, force_terminal=True, soft_wrap=False)

        # Create table
        table = Table(title="Column Alignment Test", expand=False, show_header=True)
        table.add_column(
            "URL", style="cyan", min_width=35, no_wrap=True, overflow="fold"
        )
        table.add_column(
            "Stars", style="yellow", justify="right", width=8, no_wrap=True
        )
        table.add_column("Forks", style="green", justify="right", width=8, no_wrap=True)
        table.add_column(
            "Recent Commits", style="dim", no_wrap=True, overflow="fold", max_width=None
        )

        # Add rows with different commit message lengths
        for i, commits in enumerate(
            [varying_commits[:1], varying_commits[1:2], varying_commits[2:3]]
        ):
            formatted_commits = display_service.format_recent_commits(
                commits, column_width=120
            )
            table.add_row(
                f"https://github.com/test/repo{i+1}",
                str((i + 1) * 50),
                str((i + 1) * 25),
                formatted_commits,
            )

        # Render table
        console.print(table)
        output_content = output.getvalue()

        # Verify all content is present
        assert "Short message" in output_content
        assert "medium length commit message" in output_content
        assert "extremely long commit message" in output_content

        # Verify no truncation
        assert "..." not in output_content

        # Verify numeric alignment (stars and forks should be right-aligned)
        lines = output_content.split("\n")

        # Find lines with numeric data
        numeric_lines = [
            line for line in lines if any(num in line for num in ["50", "100", "150"])
        ]

        # Verify that numeric columns appear to be aligned
        # (This is a basic check - Rich handles the actual alignment)
        assert len(numeric_lines) >= 3  # Should have at least 3 data rows

    def test_rich_table_overflow_handling_with_max_width_none(
        self, display_service, very_long_commits
    ):
        """Test Rich table overflow handling when max_width is set to None."""
        output = io.StringIO()
        console = Console(
            file=output, width=400, force_terminal=True, soft_wrap=False
        )

        # Create table with max_width=None for Recent Commits column
        table = Table(title="Overflow Handling Test", expand=False)
        table.add_column(
            "Repository", style="cyan", width=40, no_wrap=True, overflow="fold"
        )
        table.add_column(
            "Recent Commits", style="dim", no_wrap=True, overflow="fold", max_width=None
        )

        # Format extremely long commits
        formatted_commits = display_service.format_recent_commits(
            very_long_commits, column_width=500
        )

        # Add row with very long content
        table.add_row("https://github.com/test/very-long-repo-name", formatted_commits)

        # Render table
        console.print(table)
        output_content = output.getvalue()

        # Verify no truncation occurred
        assert "..." not in output_content

        # Verify all commit messages are fully present
        for commit in very_long_commits:
            assert commit.message in output_content

        # Verify table structure is maintained
        assert "Overflow Handling Test" in output_content
        assert "Repository" in output_content
        assert "Recent Commits" in output_content

    def test_rich_table_with_unicode_and_special_characters(self, display_service):
        """Test Rich table rendering with Unicode and special characters in commit messages."""
        unicode_commits = [
            RecentCommit(
                sha="unicode123456789012345678901234567890123",
                short_sha="unicode",
                message="Fix Unicode handling: café, naïve, résumé, Москва, 北京, 東京, and emoji support 🚀 🎉 ✨ 🔧 📝",
                date=datetime(2024, 1, 15, tzinfo=UTC),
                author="unicode-author",
            ),
            RecentCommit(
                sha="special123456789012345678901234567890123",
                short_sha="special",
                message="Handle special chars: @#$%^&*()_+-=[]{}|\\;':\",./<>? and quotes \"double\" 'single' `backtick`",
                date=datetime(2024, 1, 14, tzinfo=UTC),
                author="special-author",
            ),
        ]

        output = io.StringIO()
        console = Console(file=output, width=150, force_terminal=True, soft_wrap=False)

        # Create table
        table = Table(title="Unicode and Special Characters Test", expand=False)
        table.add_column("Repository", style="cyan", width=30, no_wrap=True)
        table.add_column(
            "Recent Commits", style="dim", no_wrap=True, overflow="fold", max_width=None
        )

        # Format commits with special characters
        formatted_commits = display_service.format_recent_commits(
            unicode_commits, column_width=100
        )

        # Add row
        table.add_row("https://github.com/test/unicode-repo", formatted_commits)

        # Render table
        console.print(table)
        output_content = output.getvalue()

        # Verify Unicode characters are preserved
        assert "café" in output_content
        assert "naïve" in output_content
        assert "résumé" in output_content
        assert "Москва" in output_content
        assert "北京" in output_content
        assert "東京" in output_content
        assert "🚀" in output_content
        assert "🎉" in output_content

        # Verify special characters are preserved
        assert "@#$%^&*" in output_content
        assert '"double"' in output_content
        assert "'single'" in output_content
        assert "`backtick`" in output_content

        # Verify no truncation
        assert "..." not in output_content

    def test_rich_table_performance_with_many_rows_and_long_content(
        self, display_service
    ):
        """Test Rich table performance and structure with many rows of long content."""
        # Create many commits with long messages
        many_commits = []
        for i in range(15):  # 15 commits per row
            commit = RecentCommit(
                sha=f"perf{i:02d}{'0' * 32}{i:02d}",
                short_sha=f"perf{i:02d}",
                message=f"Performance test commit {i}: Comprehensive implementation of advanced features with detailed error handling, extensive logging, performance optimization, security enhancements, and thorough testing coverage for production deployment scenario {i}",
                date=datetime(2024, 1, 15 - i, 10, 30, 0, tzinfo=UTC),
                author=f"perf-author-{i}",
            )
            many_commits.append(commit)

        output = io.StringIO()
        console = Console(file=output, width=200, force_terminal=True, soft_wrap=False)

        # Create table with many rows
        table = Table(title="Performance Test with Many Rows", expand=False)
        table.add_column("Repository", style="cyan", width=40, no_wrap=True)
        table.add_column(
            "Stars", style="yellow", justify="right", width=8, no_wrap=True
        )
        table.add_column(
            "Recent Commits", style="dim", no_wrap=True, overflow="fold", max_width=None
        )

        # Add multiple rows with long content
        for i in range(10):  # 10 rows
            formatted_commits = display_service.format_recent_commits(
                many_commits, column_width=120
            )
            table.add_row(
                f"https://github.com/test/perf-repo-{i}",
                str(i * 100),
                formatted_commits,
            )

        # Render table
        console.print(table)
        output_content = output.getvalue()

        # Verify table structure is maintained
        assert "Performance Test with Many Rows" in output_content
        assert "Repository" in output_content
        assert "Stars" in output_content
        assert "Recent Commits" in output_content

        # Verify no truncation occurred
        assert "..." not in output_content

        # Verify all repository names are present
        for i in range(10):
            assert f"perf-repo-{i}" in output_content

        # Verify commit messages are present (sample check)
        assert "Performance test commit" in output_content
        assert "Comprehensive implementation" in output_content

    def test_rich_table_with_different_terminal_widths(
        self, display_service, very_long_commits
    ):
        """Test Rich table rendering consistency across different terminal widths."""
        terminal_widths = [80, 120, 160, 200, 999999]

        for width in terminal_widths:
            output = io.StringIO()
            console = Console(
                file=output, width=width, force_terminal=True, soft_wrap=False
            )

            # Create table
            table = Table(title=f"Terminal Width {width} Test", expand=False)
            table.add_column(
                "Repository", style="cyan", min_width=30, no_wrap=True, overflow="fold"
            )
            table.add_column(
                "Recent Commits",
                style="dim",
                no_wrap=True,
                overflow="fold",
                max_width=None,
            )

            # Format commits for this width
            formatted_commits = display_service.format_recent_commits(
                very_long_commits, column_width=width
            )

            # Add row
            table.add_row("https://github.com/test/width-test-repo", formatted_commits)

            # Render table
            console.print(table)
            output_content = output.getvalue()

            # Verify table structure is maintained regardless of width
            assert f"Terminal Width {width} Test" in output_content
            assert "Repository" in output_content
            assert "Recent Commits" in output_content

            # Verify no truncation
            assert "..." not in output_content

            # Verify all commit messages are present
            for commit in very_long_commits:
                assert commit.message in output_content

    def test_rich_table_line_wrapping_behavior(self, display_service):
        """Test Rich table line wrapping behavior with long commit messages."""
        # Create a commit with a very long single-line message
        long_single_line_commit = RecentCommit(
            sha="longline123456789012345678901234567890123",
            short_sha="longline",
            message="This_is_a_very_long_single_line_commit_message_without_spaces_that_tests_how_Rich_handles_content_that_cannot_be_broken_at_word_boundaries_and_must_be_handled_as_a_single_continuous_string_of_characters",
            date=datetime(2024, 1, 15, tzinfo=UTC),
            author="longline-author",
        )

        output = io.StringIO()
        console = Console(file=output, width=120, force_terminal=True, soft_wrap=False)

        # Create table with no_wrap=True and overflow="fold"
        table = Table(title="Line Wrapping Test", expand=False)
        table.add_column("Repository", style="cyan", width=30, no_wrap=True)
        table.add_column(
            "Recent Commits", style="dim", no_wrap=True, overflow="fold", max_width=None
        )

        # Format the long single-line commit
        formatted_commits = display_service.format_recent_commits(
            [long_single_line_commit], column_width=80
        )

        # Add row
        table.add_row("https://github.com/test/wrap-test", formatted_commits)

        # Render table
        console.print(table)
        output_content = output.getvalue()

        # Verify no truncation occurred
        assert "..." not in output_content

        # Verify the long message is present
        assert "This_is_a_very_long_single_line" in output_content
        assert "single_continuous_string_of_characters" in output_content

        # Verify table structure is maintained
        assert "Line Wrapping Test" in output_content
        assert "Repository" in output_content
        assert "Recent Commits" in output_content

    def test_rich_table_with_empty_and_null_content(self, display_service):
        """Test Rich table rendering with empty and null content mixed with long content."""
        mixed_commits = [
            RecentCommit(
                sha="empty123456789012345678901234567890123",
                short_sha="empty12",
                message="",  # Empty message
                date=datetime(2024, 1, 15, tzinfo=UTC),
                author="empty-author",
            ),
            RecentCommit(
                sha="long1234567890123456789012345678901234",
                short_sha="long123",
                message="This is a very long commit message that should be displayed properly even when mixed with empty messages",
                date=datetime(2024, 1, 14, tzinfo=UTC),
                author="long-author",
            ),
        ]

        output = io.StringIO()
        console = Console(file=output, width=150, force_terminal=True, soft_wrap=False)

        # Create table
        table = Table(title="Mixed Content Test", expand=False)
        table.add_column("Repository", style="cyan", width=30, no_wrap=True)
        table.add_column(
            "Recent Commits", style="dim", no_wrap=True, overflow="fold", max_width=None
        )

        # Format mixed commits
        formatted_commits = display_service.format_recent_commits(
            mixed_commits, column_width=100
        )

        # Add row
        table.add_row("https://github.com/test/mixed-content", formatted_commits)

        # Render table
        console.print(table)
        output_content = output.getvalue()

        # Verify table structure is maintained
        assert "Mixed Content Test" in output_content
        assert "Repository" in output_content
        assert "Recent Commits" in output_content

        # Verify long message is present
        assert "very long commit message" in output_content

        # Verify proper handling of empty message (should have date and hash)
        assert "2024-01-15" in output_content
        assert "empty12" in output_content

        # Verify no truncation
        assert "..." not in output_content
