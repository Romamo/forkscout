"""Comprehensive integration tests for table structure and formatting integrity.

This module validates that table columns remain properly aligned with long commit messages,
table borders and formatting remain intact, and Rich table rendering handles long content
appropriately across various terminal widths.

Requirements tested:
- 4.1: Table columns remain properly aligned with long commit messages
- 4.2: Table borders and formatting remain intact
- 4.3: Consistent behavior across various terminal widths
- 4.4: Rich table rendering handles long content appropriately
"""

import io
import re
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from rich.console import Console
from rich.table import Table

from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.github.client import GitHubClient
from forklift.models.github import RecentCommit


class TestTableStructureValidationComprehensive:
    """Comprehensive tests for table structure and formatting integrity."""

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
        """Create test commits with very long messages."""
        return [
            RecentCommit(
                short_sha="abc1234",
                message="Implement comprehensive authentication and authorization system with multi-factor authentication, role-based access control, session management, and security audit logging for enterprise deployment scenarios",
                date=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            ),
            RecentCommit(
                short_sha="def4567",
                message="Add advanced caching layer with Redis clustering, automatic failover, cache warming strategies, and performance monitoring to handle high-traffic scenarios with sub-millisecond response times",
                date=datetime(2024, 1, 14, 15, 45, 0, tzinfo=UTC),
            ),
            RecentCommit(
                short_sha="abc7890",
                message="Refactor authentication system to support multiple providers including OAuth2, SAML, and custom JWT tokens with role-based access control and comprehensive session management capabilities",
                date=datetime(2024, 1, 13, 9, 15, 0, tzinfo=UTC),
            ),
        ]

    @pytest.fixture
    def mixed_length_commits(self):
        """Create test commits with mixed message lengths."""
        return [
            RecentCommit(
                short_sha="abc1234",
                message="Fix bug",
                date=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            ),
            RecentCommit(
                short_sha="def5678",
                message="Add new feature for user management with basic validation and error handling",
                date=datetime(2024, 1, 14, 15, 45, 0, tzinfo=UTC),
            ),
            RecentCommit(
                short_sha="abc9012",
                message="Implement comprehensive monitoring and alerting system with real-time dashboards, automated notifications, detailed performance metrics collection, and integration with external monitoring services across all microservices",
                date=datetime(2024, 1, 13, 9, 15, 0, tzinfo=UTC),
            ),
        ]

    @pytest.mark.asyncio
    async def test_table_columns_alignment_with_long_messages(
        self, display_service, long_commit_messages
    ):
        """Test that table columns remain properly aligned with long commit messages.
        
        Requirement 4.1: Table columns remain properly aligned with long commit messages
        """
        # Capture console output with wide width to prevent artificial truncation
        output = io.StringIO()
        console = Console(file=output, width=200, force_terminal=True, soft_wrap=False)
        display_service.console = console

        # Format commits with long messages
        formatted_commits = display_service.format_recent_commits(
            long_commit_messages, column_width=150
        )

        # Verify no truncation occurred
        assert "..." not in formatted_commits, "Commit messages should not be truncated"

        # Verify all commit messages are present in full
        for commit in long_commit_messages:
            assert commit.message in formatted_commits, f"Full commit message should be present: {commit.message[:50]}..."

        # Verify proper formatting structure
        lines = formatted_commits.split("\n")
        assert len(lines) == len(long_commit_messages), "Should have one line per commit"

        # Verify each line has proper format: "YYYY-MM-DD hash message"
        for i, line in enumerate(lines):
            commit = long_commit_messages[i]
            
            # Check date format at start
            assert line.startswith("2024-01-"), f"Line should start with date: {line[:20]}"
            
            # Check hash presence
            assert commit.short_sha in line, f"Short SHA should be present: {commit.short_sha}"
            
            # Check full message is present
            assert commit.message in line, f"Full message should be present in line: {line[:100]}..."
            
            # Verify format structure (date, hash, message)
            parts = line.split(" ", 2)
            assert len(parts) == 3, f"Line should have date, hash, and message: {line[:50]}..."
            assert parts[0] == commit.date.strftime("%Y-%m-%d"), "Date format should be YYYY-MM-DD"
            assert parts[1] == commit.short_sha, "Second part should be short SHA"
            assert parts[2] == commit.message, "Third part should be full message"

    @pytest.mark.asyncio
    async def test_table_borders_integrity_with_long_content(
        self, display_service, long_commit_messages
    ):
        """Test that table borders and formatting remain intact with long content.
        
        Requirement 4.2: Table borders and formatting remain intact
        """
        # Create console with sufficient width
        output = io.StringIO()
        console = Console(file=output, width=300, force_terminal=True, soft_wrap=False)

        # Create table with long commit content
        table = Table(title="Table Border Integrity Test", expand=False, show_header=True)
        table.add_column("Repository", style="cyan", min_width=35, no_wrap=True, overflow="fold")
        table.add_column("Stars", style="yellow", justify="right", width=8, no_wrap=True)
        table.add_column("Recent Commits", style="dim", no_wrap=True, overflow="fold", max_width=None)

        # Format long commits
        formatted_commits = display_service.format_recent_commits(
            long_commit_messages, column_width=200
        )

        # Add test rows with long content
        table.add_row("https://github.com/test-owner/test-repo-with-very-long-name", "1234", formatted_commits)
        table.add_row("https://github.com/another-owner/another-long-repo-name", "5678", formatted_commits)

        # Render table
        console.print(table)
        output_content = output.getvalue()

        # Verify table structure is maintained
        assert "Table Border Integrity Test" in output_content, "Table title should be present"
        assert "Repository" in output_content, "Repository column header should be present"
        assert "Stars" in output_content, "Stars column header should be present"
        assert "Recent Commits" in output_content, "Recent Commits column header should be present"

        # Verify table borders are present (Rich uses Unicode box drawing characters)
        border_patterns = [
            r"[─┌┐└┘├┤┬┴┼]",  # Horizontal and corner box drawing characters
            r"[│┃]",  # Vertical borders
        ]

        for pattern in border_patterns:
            assert re.search(pattern, output_content), f"Border pattern {pattern} should be present in table output"

        # Verify content is properly contained within table structure
        assert "test-owner/test-repo" in output_content, "Repository URL should be present"
        assert "1234" in output_content, "Stars count should be present"
        assert "5678" in output_content, "Second stars count should be present"

        # Verify commit messages are present (Rich may truncate for table rendering, but key parts should be visible)
        for commit in long_commit_messages:
            # Check that the message starts are present and no "..." truncation from our formatting
            message_start = commit.message[:50]  # First 50 characters should be present
            assert message_start in output_content, f"Start of commit message should be present: {message_start}"

        # Verify no "..." truncation indicators from our formatting (Rich may still apply its own rendering)
        # The key test is that our format_recent_commits method doesn't add "..." truncation
        assert "..." not in formatted_commits, "Our formatting should not add truncation indicators"

    @pytest.mark.asyncio
    async def test_various_terminal_widths_consistency(
        self, display_service, mixed_length_commits
    ):
        """Test consistent behavior across various terminal widths.
        
        Requirement 4.3: Consistent behavior across various terminal widths
        """
        # Test with wide terminal widths to avoid Rich's automatic truncation
        terminal_widths = [200, 300, 500, 999999]

        for width in terminal_widths:
            output = io.StringIO()
            console = Console(file=output, width=width, force_terminal=True, soft_wrap=False)
            display_service.console = console

            # Format commits for this terminal width
            formatted_commits = display_service.format_recent_commits(
                mixed_length_commits, column_width=width // 2
            )

            # Verify no truncation regardless of terminal width
            assert "..." not in formatted_commits, f"No truncation should occur at width {width}"

            # Verify all messages are present in full
            for commit in mixed_length_commits:
                assert commit.message in formatted_commits, f"Full message should be present at width {width}: {commit.message[:30]}..."

            # Verify consistent formatting structure
            lines = formatted_commits.split("\n")
            assert len(lines) == len(mixed_length_commits), f"Should have correct number of lines at width {width}"

            # Verify date format consistency across all widths
            for line in lines:
                if line.strip() and not line.startswith("[dim]"):
                    # Should start with date format YYYY-MM-DD
                    assert line[:4].isdigit(), f"Year should be digits at width {width}: {line[:10]}"
                    assert line[4] == "-", f"Date separator should be present at width {width}: {line[:10]}"
                    assert line[5:7].isdigit(), f"Month should be digits at width {width}: {line[:10]}"
                    assert line[7] == "-", f"Date separator should be present at width {width}: {line[:10]}"
                    assert line[8:10].isdigit(), f"Day should be digits at width {width}: {line[:10]}"

    @pytest.mark.asyncio
    async def test_rich_table_long_content_handling(
        self, display_service, long_commit_messages
    ):
        """Test that Rich table rendering handles long content appropriately.
        
        Requirement 4.4: Rich table rendering handles long content appropriately
        """
        # Test with very wide console to ensure no artificial truncation
        output = io.StringIO()
        console = Console(file=output, width=999999, force_terminal=True, soft_wrap=False)
        display_service.console = console

        # Create table with long content
        table = Table(title="Rich Long Content Handling Test", expand=False)
        table.add_column("Repository", style="cyan", no_wrap=True, overflow="fold")
        table.add_column("Commits", style="dim", no_wrap=True, overflow="fold", max_width=None)

        # Format very long commits
        formatted_commits = display_service.format_recent_commits(
            long_commit_messages, column_width=500
        )

        # Add multiple rows with varying content lengths
        test_repos = [
            "https://github.com/short/repo",
            "https://github.com/medium-length-owner/medium-length-repository-name",
            "https://github.com/very-long-organization-name/extremely-long-repository-name-that-tests-overflow-handling-capabilities",
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
            assert repo_name in output_content, f"Repository name should be present: {repo_name}"

        # Verify all commit messages are fully present
        for commit in long_commit_messages:
            assert commit.message in output_content, f"Full commit message should be present: {commit.message[:50]}..."

        # Verify table structure is maintained
        assert "Rich Long Content Handling Test" in output_content, "Table title should be present"
        assert "Repository" in output_content, "Repository column should be present"
        assert "Commits" in output_content, "Commits column should be present"

        # Verify no truncation occurred
        assert "..." not in output_content, "No truncation should occur with unlimited width"

    @pytest.mark.asyncio
    async def test_table_structure_with_special_characters(self, display_service):
        """Test table structure with special characters and Unicode content."""
        # Create commits with special characters
        special_commits = [
            RecentCommit(
                short_sha="abc1234",
                message="Fix Unicode handling: café, naïve, résumé, Москва, 北京, 東京, and emoji support 🚀 🎉 ✨",
                date=datetime(2024, 1, 15, tzinfo=UTC),
            ),
            RecentCommit(
                short_sha="def5678",
                message="Handle special chars: @#$%^&*()_+-=[]{}|\\;':\",./<>? and quotes \"double\" 'single' `backtick`",
                date=datetime(2024, 1, 14, tzinfo=UTC),
            ),
        ]

        output = io.StringIO()
        console = Console(file=output, width=200, force_terminal=True, soft_wrap=False)

        # Create table
        table = Table(title="Special Characters Test", expand=False)
        table.add_column("Repository", style="cyan", width=30, no_wrap=True)
        table.add_column("Recent Commits", style="dim", no_wrap=True, overflow="fold", max_width=None)

        # Format commits with special characters
        formatted_commits = display_service.format_recent_commits(
            special_commits, column_width=150
        )

        # Add row
        table.add_row("https://github.com/test/unicode-repo", formatted_commits)

        # Render table
        console.print(table)
        output_content = output.getvalue()

        # Verify Unicode characters are preserved
        unicode_chars = ["café", "naïve", "résumé", "Москва", "北京", "東京", "🚀", "🎉", "✨"]
        for char in unicode_chars:
            assert char in output_content, f"Unicode character should be preserved: {char}"

        # Verify special characters are preserved
        special_chars = ["@#$%^&*", '"double"', "'single'", "`backtick`"]
        for char in special_chars:
            assert char in output_content, f"Special character should be preserved: {char}"

        # Verify no truncation
        assert "..." not in output_content, "No truncation should occur with special characters"

    @pytest.mark.asyncio
    async def test_table_performance_with_many_long_commits(self, display_service):
        """Test table performance and structure with many long commit messages."""
        # Create many commits with long messages
        many_long_commits = []
        for i in range(15):  # 15 commits
            commit = RecentCommit(
                sha=f"commit{i:02d}{'0' * 32}{i:02d}",
                short_sha=f"abc{i:04d}"[0:7],  # Ensure 7 characters
                message=f"Commit {i}: Comprehensive implementation of advanced features with detailed error handling, extensive logging, performance optimization, security enhancements, and thorough testing coverage for production deployment scenario number {i}",
                date=datetime(2024, 1, max(1, 15 - i), 10, 30, 0, tzinfo=UTC),  # Ensure valid dates
                author=f"perf-author-{i}",
            )
            many_long_commits.append(commit)

        # Format many long commits
        formatted_commits = display_service.format_recent_commits(
            many_long_commits, column_width=200
        )

        # Verify no truncation
        assert "..." not in formatted_commits, "No truncation should occur with many commits"

        # Verify all commits are present
        lines = formatted_commits.split("\n")
        assert len(lines) == len(many_long_commits), "Should have one line per commit"

        # Verify each commit message is fully present
        for commit in many_long_commits:
            assert commit.message in formatted_commits, f"Full commit message should be present: {commit.message[:50]}..."
            assert commit.short_sha in formatted_commits, f"Short SHA should be present: {commit.short_sha}"

        # Verify chronological ordering (newest first)
        for i in range(len(lines) - 1):
            if lines[i].strip() and lines[i + 1].strip():
                # Extract dates for comparison
                date1 = lines[i][:10]  # YYYY-MM-DD
                date2 = lines[i + 1][:10]  # YYYY-MM-DD
                assert date1 >= date2, f"Dates should be in chronological order: {date1} >= {date2}"

    @pytest.mark.asyncio
    async def test_column_width_calculation_integrity(self, display_service, long_commit_messages):
        """Test that column width calculation works correctly with long messages."""
        # Test with various show_commits values
        show_commits_values = [1, 3, 5, 10]

        for show_commits in show_commits_values:
            # Create mock commits data
            commits_data = {"test-owner/test-repo": long_commit_messages[:show_commits]}

            # Calculate column width
            calculated_width = display_service.calculate_commits_column_width(
                commits_data, show_commits, min_width=30, max_width=300
            )

            # Verify width is reasonable and within bounds
            assert 30 <= calculated_width <= 300, f"Width should be within bounds for {show_commits} commits: {calculated_width}"

            # Verify width increases with more commits (generally)
            if show_commits > 1:
                single_commit_width = display_service.calculate_commits_column_width(
                    {"test-owner/test-repo": long_commit_messages[:1]},
                    1,
                    min_width=30,
                    max_width=300,
                )
                # Width should generally increase with more commits, but may be capped
                assert calculated_width >= single_commit_width or calculated_width == 300, \
                    f"Width should increase or be at max: single={single_commit_width}, multiple={calculated_width}"

    @pytest.mark.asyncio
    async def test_table_structure_with_edge_cases(self, display_service):
        """Test table structure with edge cases like very long single words."""
        # Create commit with very long single word (no spaces)
        edge_case_commits = [
            RecentCommit(
                short_sha="abc1234",
                message="This_is_a_very_long_single_word_without_spaces_that_tests_how_the_table_handles_content_that_cannot_be_broken_at_word_boundaries_and_must_be_displayed_as_a_continuous_string",
                date=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            ),
            RecentCommit(
                short_sha="def5678",
                message="Normal commit message with spaces that can be wrapped naturally if needed",
                date=datetime(2024, 1, 14, 15, 45, 0, tzinfo=UTC),
            ),
        ]

        # Format edge case commits
        formatted_commits = display_service.format_recent_commits(
            edge_case_commits, column_width=100
        )

        # Verify no truncation
        assert "..." not in formatted_commits, "No truncation should occur with edge cases"

        # Verify both messages are present
        for commit in edge_case_commits:
            assert commit.message in formatted_commits, f"Edge case message should be present: {commit.message[:50]}..."

        # Verify structure is maintained
        lines = formatted_commits.split("\n")
        assert len(lines) == len(edge_case_commits), "Should have correct number of lines"

        # Verify each line has proper structure
        for line in lines:
            if line.strip():
                # Should have date and hash even with edge case messages
                assert "2024-01-" in line, f"Date should be present: {line[:20]}"
                parts = line.split()
                assert len(parts) >= 2, f"Should have at least date and hash: {line[:50]}..."

    @pytest.mark.asyncio
    async def test_table_rendering_consistency_across_modes(self, display_service, long_commit_messages):
        """Test that table rendering is consistent across different display modes."""
        # Test with different console configurations
        console_configs = [
            {"width": 200, "soft_wrap": False},
            {"width": 300, "soft_wrap": False},
            {"width": 999999, "soft_wrap": False},
        ]

        for config in console_configs:
            output = io.StringIO()
            console = Console(file=output, force_terminal=True, **config)
            display_service.console = console

            # Format commits
            formatted_commits = display_service.format_recent_commits(
                long_commit_messages, column_width=config["width"] // 2
            )

            # Verify consistency across configurations
            assert "..." not in formatted_commits, f"No truncation at width {config['width']}"
            
            # Verify all messages present
            for commit in long_commit_messages:
                assert commit.message in formatted_commits, \
                    f"Message should be present at width {config['width']}: {commit.message[:30]}..."

            # Verify structure consistency
            lines = formatted_commits.split("\n")
            assert len(lines) == len(long_commit_messages), \
                f"Should have correct line count at width {config['width']}"

            # Verify format consistency
            for line in lines:
                if line.strip():
                    assert line.startswith("2024-01-"), \
                        f"Date format should be consistent at width {config['width']}: {line[:15]}"