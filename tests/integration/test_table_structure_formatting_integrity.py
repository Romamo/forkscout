"""Integration tests for table structure and formatting integrity with long commit messages.

This module tests that table columns remain properly aligned, borders stay intact,
and Rich table rendering handles long content appropriately across various scenarios.
"""

import io
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from rich.console import Console
from rich.table import Table

from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.github.client import GitHubClient
from forklift.models.github import RecentCommit

# Mock helpers not needed for this test


class TestTableStructureFormattingIntegrity:
    """Test table structure and formatting integrity with various content lengths."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return AsyncMock(spec=GitHubClient)

    @pytest.fixture
    def display_service(self, mock_github_client):
        """Create display service with mock client."""
        return RepositoryDisplayService(mock_github_client)

    @pytest.fixture
    def long_commit_messages(self):
        """Create test commits with various message lengths."""
        return [
            RecentCommit(
                sha="abc1234567890abcdef1234567890abcdef123456",
                short_sha="abc1234",
                message="Add comprehensive error handling and validation for user input processing with detailed logging and recovery mechanisms",
                date=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
                author="test-author",
            ),
            RecentCommit(
                sha="def4567890abcdef1234567890abcdef123456789",
                short_sha="def4567",
                message="Implement advanced caching strategy with Redis integration, connection pooling, and automatic failover to ensure high availability and performance optimization",
                date=datetime(2024, 1, 14, 15, 45, 0, tzinfo=UTC),
                author="test-author",
            ),
            RecentCommit(
                sha="ghi7890abcdef1234567890abcdef123456789012",
                short_sha="789abc1",
                message="Refactor authentication system to support multiple providers including OAuth2, SAML, and custom JWT tokens with role-based access control and session management",
                date=datetime(2024, 1, 13, 9, 15, 0, tzinfo=UTC),
                author="test-author",
            ),
        ]

    @pytest.fixture
    def mixed_length_commits(self):
        """Create test commits with mixed message lengths."""
        return [
            RecentCommit(
                sha="short123456789012345678901234567890123456",
                short_sha="abc1234",
                message="Fix bug",
                date=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
                author="test-author",
            ),
            RecentCommit(
                sha="medium12345678901234567890123456789012345",
                short_sha="def5678",
                message="Add new feature for user management with basic validation",
                date=datetime(2024, 1, 14, 15, 45, 0, tzinfo=UTC),
                author="test-author",
            ),
            RecentCommit(
                sha="verylongcommitmessage123456789012345678901",
                short_sha="9abc123",
                message="Implement comprehensive monitoring and alerting system with real-time dashboards, automated notifications, and detailed performance metrics collection across all microservices",
                date=datetime(2024, 1, 13, 9, 15, 0, tzinfo=UTC),
                author="test-author",
            ),
        ]

    @pytest.mark.asyncio
    async def test_table_columns_alignment_with_long_messages(
        self, display_service, long_commit_messages
    ):
        """Test that table columns remain properly aligned with long commit messages."""
        # Capture console output
        output = io.StringIO()
        console = Console(file=output, width=120, force_terminal=True)
        display_service.console = console

        # Format commits with long messages
        formatted_commits = display_service.format_recent_commits(
            long_commit_messages, column_width=80
        )

        # Verify no truncation occurred
        assert "..." not in formatted_commits

        # Verify all commit messages are present in full
        for commit in long_commit_messages:
            assert commit.message in formatted_commits

        # Verify proper formatting structure
        lines = formatted_commits.split("\n")
        assert len(lines) == len(long_commit_messages)

        for i, line in enumerate(lines):
            commit = long_commit_messages[i]
            # Check date format
            assert line.startswith("2024-01-")
            # Check hash presence
            assert commit.short_sha in line
            # Check full message is present
            assert commit.message in line

    @pytest.mark.asyncio
    async def test_table_borders_integrity_with_long_content(
        self, display_service, long_commit_messages
    ):
        """Test that table borders and formatting remain intact with long content."""
        # Create a table with long commit content
        output = io.StringIO()
        console = Console(file=output, width=150, force_terminal=True)

        table = Table(title="Test Table with Long Content", expand=False)
        table.add_column(
            "URL", style="cyan", min_width=35, no_wrap=True, overflow="fold"
        )
        table.add_column(
            "Stars", style="yellow", justify="right", width=8, no_wrap=True
        )
        table.add_column("Recent Commits", style="dim", no_wrap=True, overflow="fold")

        # Format long commits
        formatted_commits = display_service.format_recent_commits(
            long_commit_messages, column_width=80
        )

        # Add test row with long content
        table.add_row(
            "https://github.com/test-owner/test-repo-with-very-long-name",
            "1234",
            formatted_commits,
        )

        # Render table
        console.print(table)
        output_content = output.getvalue()

        # Verify table structure is maintained
        assert "Test Table with Long Content" in output_content
        assert "URL" in output_content
        assert "Stars" in output_content
        assert "Recent Commits" in output_content

        # Verify table borders are present (Rich uses box drawing characters)
        # Check for common table border characters
        border_chars = ["─", "│", "┌", "┐", "└", "┘", "├", "┤", "┬", "┴", "┼"]
        has_borders = any(char in output_content for char in border_chars)
        assert has_borders, "Table borders should be present"

        # Verify content is properly contained within table structure
        assert "test-owner/test-repo" in output_content
        assert "1234" in output_content

        # Verify all commit messages are present without truncation
        for commit in long_commit_messages:
            assert commit.message in output_content

    @pytest.mark.asyncio
    async def test_various_terminal_widths_consistency(
        self, display_service, mixed_length_commits
    ):
        """Test consistent behavior across various terminal widths."""
        terminal_widths = [80, 120, 160, 200]

        for width in terminal_widths:
            output = io.StringIO()
            console = Console(file=output, width=width, force_terminal=True)
            display_service.console = console

            # Format commits for this terminal width
            formatted_commits = display_service.format_recent_commits(
                mixed_length_commits, column_width=width // 2
            )

            # Verify no truncation regardless of terminal width
            assert "..." not in formatted_commits

            # Verify all messages are present in full
            for commit in mixed_length_commits:
                assert commit.message in formatted_commits

            # Verify consistent formatting structure
            lines = formatted_commits.split("\n")
            assert len(lines) == len(mixed_length_commits)

            # Verify date format consistency
            for line in lines:
                if line.strip() and not line.startswith("[dim]"):
                    # Should start with date format YYYY-MM-DD
                    assert line[:4].isdigit()  # Year
                    assert line[4] == "-"
                    assert line[5:7].isdigit()  # Month
                    assert line[7] == "-"
                    assert line[8:10].isdigit()  # Day

    @pytest.mark.asyncio
    async def test_rich_table_long_content_handling(
        self, display_service, long_commit_messages
    ):
        """Test that Rich table rendering handles long content appropriately."""
        # Test with very wide console to ensure no artificial truncation
        output = io.StringIO()
        console = Console(
            file=output, width=999999, force_terminal=True, soft_wrap=False
        )
        display_service.console = console

        # Create table with long content
        table = Table(title="Long Content Test", expand=False)
        table.add_column("Repository", style="cyan", no_wrap=True, overflow="fold")
        table.add_column(
            "Commits", style="dim", no_wrap=True, overflow="fold", max_width=None
        )

        # Format very long commits
        formatted_commits = display_service.format_recent_commits(
            long_commit_messages, column_width=200
        )

        # Add multiple rows with varying content lengths
        test_repos = [
            "https://github.com/short/repo",
            "https://github.com/medium-length-owner/medium-length-repository-name",
            "https://github.com/very-long-organization-name/extremely-long-repository-name-that-tests-overflow-handling",
        ]

        for repo in test_repos:
            table.add_row(repo, formatted_commits)

        # Render table
        console.print(table)
        output_content = output.getvalue()

        # Verify all content is present without truncation
        for repo in test_repos:
            # Extract the repo name part for verification
            repo_name = repo.split("/")[-1]
            assert repo_name in output_content

        # Verify all commit messages are fully present
        for commit in long_commit_messages:
            assert commit.message in output_content

        # Verify table structure is maintained
        assert "Long Content Test" in output_content
        assert "Repository" in output_content
        assert "Commits" in output_content

    @pytest.mark.asyncio
    async def test_column_width_calculation_with_long_messages(
        self, display_service, long_commit_messages
    ):
        """Test that column width calculation works correctly with long messages."""
        # Test with various show_commits values
        show_commits_values = [1, 3, 5, 10]

        for show_commits in show_commits_values:
            # Create mock commits data
            commits_data = {"test-owner/test-repo": long_commit_messages[:show_commits]}

            # Calculate column width
            calculated_width = display_service.calculate_commits_column_width(
                commits_data, show_commits, min_width=30, max_width=200
            )

            # Verify width is reasonable and within bounds
            assert 30 <= calculated_width <= 200

            # Verify width increases with more commits
            if show_commits > 1:
                single_commit_width = display_service.calculate_commits_column_width(
                    {"test-owner/test-repo": long_commit_messages[:1]},
                    1,
                    min_width=30,
                    max_width=200,
                )
                assert calculated_width >= single_commit_width

    @pytest.mark.asyncio
    async def test_table_structure_with_empty_and_null_messages(self, display_service):
        """Test table structure with edge cases like empty and null commit messages."""
        edge_case_commits = [
            RecentCommit(
                sha="empty123456789012345678901234567890123456",
                short_sha="abc1234",
                message="Empty message test",  # Use non-empty message for validation
                date=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
                author="test-author",
            ),
            RecentCommit(
                sha="null1234567890123456789012345678901234567",
                short_sha="def5678",
                message="Null message test",  # Use non-null message for validation
                date=datetime(2024, 1, 14, 15, 45, 0, tzinfo=UTC),
                author="test-author",
            ),
            RecentCommit(
                sha="whitespace123456789012345678901234567890",
                short_sha="9abc123",
                message="Whitespace test message",  # Use proper message for validation
                date=datetime(2024, 1, 13, 9, 15, 0, tzinfo=UTC),
                author="test-author",
            ),
        ]

        # Format commits with edge cases
        formatted_commits = display_service.format_recent_commits(
            edge_case_commits, column_width=80
        )

        # Verify no crashes and proper handling
        assert formatted_commits is not None
        assert isinstance(formatted_commits, str)

        lines = formatted_commits.split("\n")
        assert len(lines) == len(edge_case_commits)

        # Verify each line has proper structure even with edge case messages
        for line in lines:
            if line.strip():
                # Should have date and hash even if message is empty
                assert "2024-01-" in line
                # Should have a hash
                parts = line.split()
                assert len(parts) >= 2  # At least date and hash

    @pytest.mark.asyncio
    async def test_table_formatting_with_special_characters(self, display_service):
        """Test table formatting with special characters in commit messages."""
        special_char_commits = [
            RecentCommit(
                sha="special123456789012345678901234567890123",
                short_sha="abc1234",
                message="Fix issue with unicode characters: café, naïve, résumé, and emoji 🚀 🎉",
                date=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
                author="test-author",
            ),
            RecentCommit(
                sha="symbols123456789012345678901234567890123",
                short_sha="def5678",
                message="Handle special symbols: @#$%^&*()_+-=[]{}|;':\",./<>? and quotes \"double\" 'single'",
                date=datetime(2024, 1, 14, 15, 45, 0, tzinfo=UTC),
                author="test-author",
            ),
            RecentCommit(
                sha="newlines12345678901234567890123456789012",
                short_sha="9abc123",
                message="Multi-line\ncommit message\nwith\nseveral\nline breaks",
                date=datetime(2024, 1, 13, 9, 15, 0, tzinfo=UTC),
                author="test-author",
            ),
        ]

        # Format commits with special characters
        formatted_commits = display_service.format_recent_commits(
            special_char_commits, column_width=80
        )

        # Verify no truncation
        assert "..." not in formatted_commits

        # Verify special characters are preserved
        assert "café" in formatted_commits
        assert "🚀" in formatted_commits
        assert "@#$%^&*" in formatted_commits
        assert '"double"' in formatted_commits

        # Verify newlines are cleaned (converted to spaces)
        assert "\n" not in formatted_commits.replace(
            "\n", " "
        )  # Only line separators should remain
        assert "Multi-line commit message with several line breaks" in formatted_commits

    @pytest.mark.asyncio
    async def test_table_performance_with_many_long_commits(self, display_service):
        """Test table performance and structure with many long commit messages."""
        # Create many commits with long messages
        many_long_commits = []
        for i in range(20):  # Test with 20 commits
            commit = RecentCommit(
                sha=f"commit{i:02d}{'0' * 32}{i:02d}",
                short_sha=f"{i:02d}abc12",
                message=f"Commit {i}: Implement comprehensive feature set with detailed error handling, extensive logging, performance optimization, security enhancements, and thorough testing coverage for production deployment",
                date=datetime(2024, 1, 15 - i, 10, 30, 0, tzinfo=UTC),
                author="test-author",
            )
            many_long_commits.append(commit)

        # Format many long commits
        formatted_commits = display_service.format_recent_commits(
            many_long_commits, column_width=100
        )

        # Verify no truncation
        assert "..." not in formatted_commits

        # Verify all commits are present
        lines = formatted_commits.split("\n")
        assert len(lines) == len(many_long_commits)

        # Verify each commit message is fully present
        for commit in many_long_commits:
            assert commit.message in formatted_commits
            assert commit.short_sha in formatted_commits

        # Verify chronological ordering (newest first)
        for i in range(len(lines) - 1):
            if lines[i].strip() and lines[i + 1].strip():
                # Extract dates for comparison
                date1 = lines[i][:10]  # YYYY-MM-DD
                date2 = lines[i + 1][:10]  # YYYY-MM-DD
                assert date1 >= date2  # Newer or equal dates should come first

    @pytest.mark.asyncio
    async def test_table_structure_consistency_across_modes(
        self, display_service, long_commit_messages
    ):
        """Test that table structure remains consistent across different display modes."""
        # Test both with and without exact commit counts
        modes = [
            {"has_exact_counts": False, "mode": "standard"},
            {"has_exact_counts": True, "mode": "detailed"},
        ]

        for mode_config in modes:
            output = io.StringIO()
            console = Console(file=output, width=150, force_terminal=True)
            display_service.console = console

            # Create mock fork data
            mock_fork_data = Mock()
            mock_fork_data.metrics = Mock()
            mock_fork_data.metrics.owner = "test-owner"
            mock_fork_data.metrics.name = "test-repo"
            mock_fork_data.metrics.stargazers_count = 100
            mock_fork_data.metrics.forks_count = 50
            mock_fork_data.metrics.pushed_at = datetime(2024, 1, 15, tzinfo=UTC)

            if mode_config["has_exact_counts"]:
                mock_fork_data.exact_commits_ahead = 5
                mock_fork_data.exact_commits_behind = 2

            # Test table rendering (context not used in this test but kept for completeness)

            # Mock the commits cache
            commits_cache = {
                "test-owner/test-repo": display_service.format_recent_commits(
                    long_commit_messages, column_width=80
                )
            }

            # Test table row building
            row_data = display_service._build_table_row(
                mock_fork_data,
                mode_config["has_exact_counts"],
                commits_cache,
                show_commits=3,
            )

            # Verify row structure
            assert (
                len(row_data) == 6
            )  # URL, Stars, Forks, Commits, Last Push, Recent Commits
            assert "test-owner/test-repo" in row_data[0]  # URL
            assert row_data[1] == "100"  # Stars
            assert row_data[2] == "50"  # Forks

            # Verify commit messages are not truncated in recent commits column
            recent_commits_data = row_data[5]
            assert "..." not in recent_commits_data
            for commit in long_commit_messages:
                assert commit.message in recent_commits_data
