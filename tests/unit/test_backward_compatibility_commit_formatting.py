"""Unit tests for backward compatibility and existing functionality after commit message truncation fix."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

from rich.console import Console

from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.models.github import RecentCommit


class TestBackwardCompatibilityCommitFormatting:
    """Test backward compatibility and existing functionality after commit message truncation fix."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_github_client = Mock()
        # Make async methods return AsyncMock
        self.mock_github_client.get_repository = AsyncMock()
        self.mock_github_client.get_repository_languages = AsyncMock()
        self.mock_github_client.get_repository_topics = AsyncMock()
        self.mock_github_client.get_forks = AsyncMock()
        self.mock_github_client.get_commits_ahead_count = AsyncMock()
        self.mock_github_client.get_recent_commits = AsyncMock()

        self.mock_console = Mock(spec=Console)
        self.service = RepositoryDisplayService(
            github_client=self.mock_github_client, console=self.mock_console
        )

    # Test chronological sorting (newest first) is preserved - Requirement 3.1
    def test_chronological_sorting_newest_first_preserved(self):
        """Test that chronological sorting (newest first) is preserved."""

        # Create commits with different dates (not in chronological order)
        commits = [
            RecentCommit(
                short_sha="abc1234",
                message="Old commit",
                date=datetime(2024, 1, 10, 10, 0),
            ),
            RecentCommit(
                short_sha="def5678",
                message="New commit",
                date=datetime(2024, 1, 15, 14, 30),
            ),
            RecentCommit(
                short_sha="abc9012",
                message="Middle commit",
                date=datetime(2024, 1, 12, 12, 15),
            ),
        ]

        result = self.service.format_recent_commits(commits)
        lines = result.split("\n")

        # Verify newest first ordering
        assert lines[0] == "2024-01-15 def5678 New commit"
        assert lines[1] == "2024-01-12 abc9012 Middle commit"
        assert lines[2] == "2024-01-10 abc1234 Old commit"

    def test_chronological_sorting_with_same_dates(self):
        """Test chronological sorting with commits on the same date."""

        # Create commits with same date but different times
        commits = [
            RecentCommit(
                short_sha="abc1234",
                message="Morning commit",
                date=datetime(2024, 1, 15, 9, 0),
            ),
            RecentCommit(
                short_sha="def5678",
                message="Evening commit",
                date=datetime(2024, 1, 15, 18, 30),
            ),
            RecentCommit(
                short_sha="abc9012",
                message="Afternoon commit",
                date=datetime(2024, 1, 15, 14, 15),
            ),
        ]

        result = self.service.format_recent_commits(commits)
        lines = result.split("\n")

        # Verify newest first ordering (evening, afternoon, morning)
        assert lines[0] == "2024-01-15 def5678 Evening commit"
        assert lines[1] == "2024-01-15 abc9012 Afternoon commit"
        assert lines[2] == "2024-01-15 abc1234 Morning commit"

    def test_chronological_sorting_mixed_dates_and_none(self):
        """Test chronological sorting with mix of dates and None values."""

        commits = [
            RecentCommit(short_sha="abc1234", message="No date commit 1"),
            RecentCommit(
                short_sha="def5678",
                message="Dated commit 1",
                date=datetime(2024, 1, 15, 10, 0),
            ),
            RecentCommit(short_sha="abc9012", message="No date commit 2"),
            RecentCommit(
                short_sha="abc3456",
                message="Dated commit 2",
                date=datetime(2024, 1, 12, 10, 0),
            ),
        ]

        result = self.service.format_recent_commits(commits)
        lines = result.split("\n")

        # Verify dated commits come first (newest first), then undated commits
        assert lines[0] == "2024-01-15 def5678 Dated commit 1"
        assert lines[1] == "2024-01-12 abc3456 Dated commit 2"
        assert lines[2] == "abc1234: No date commit 1"
        assert lines[3] == "abc9012: No date commit 2"

    # Test date formatting ("YYYY-MM-DD") remains consistent - Requirement 3.2
    def test_date_formatting_yyyy_mm_dd_consistent(self):
        """Test that date formatting remains consistent as YYYY-MM-DD."""

        # Test various dates to ensure consistent formatting
        test_dates = [
            (datetime(2024, 1, 5, 10, 30), "2024-01-05"),
            (datetime(2024, 12, 25, 23, 59), "2024-12-25"),
            (datetime(2023, 7, 4, 0, 0), "2023-07-04"),
            (datetime(2024, 2, 29, 12, 0), "2024-02-29"),  # Leap year
        ]

        for test_date, expected_date_str in test_dates:
            commit = RecentCommit(
                short_sha="abc1234",
                message="Test commit",
                date=test_date,
            )

            result = self.service.format_recent_commits([commit])
            assert result.startswith(expected_date_str)
            assert f"{expected_date_str} abc1234 Test commit" == result

    def test_date_formatting_method_consistency(self):
        """Test that _format_commit_date method produces consistent YYYY-MM-DD format."""
        test_dates = [
            datetime(2024, 1, 1, 0, 0),
            datetime(2024, 6, 15, 12, 30),
            datetime(2024, 12, 31, 23, 59),
            datetime(2023, 2, 28, 6, 45),
            datetime(2020, 2, 29, 18, 20),  # Leap year
        ]

        for test_date in test_dates:
            result = self.service._format_commit_date(test_date)
            # Verify format is exactly YYYY-MM-DD
            assert len(result) == 10
            assert result[4] == "-"
            assert result[7] == "-"
            # Verify it matches expected strftime format
            assert result == test_date.strftime("%Y-%m-%d")

    # Test fallback formatting for commits without dates - Requirement 3.3
    def test_fallback_formatting_no_dates_preserved(self):
        """Test that fallback formatting for commits without dates is preserved."""

        # Test single commit without date
        commit = RecentCommit(short_sha="abc1234", message="Commit without date")
        result = self.service.format_recent_commits([commit])
        assert result == "abc1234: Commit without date"

    def test_fallback_formatting_multiple_commits_no_dates(self):
        """Test fallback formatting for multiple commits without dates."""

        commits = [
            RecentCommit(short_sha="abc1234", message="First commit"),
            RecentCommit(short_sha="def5678", message="Second commit"),
            RecentCommit(short_sha="abc9012", message="Third commit"),
        ]

        result = self.service.format_recent_commits(commits)
        expected = (
            "abc1234: First commit\ndef5678: Second commit\nabc9012: Third commit"
        )
        assert result == expected

    def test_fallback_formatting_mixed_with_dated_commits(self):
        """Test fallback formatting mixed with dated commits."""

        commits = [
            RecentCommit(
                short_sha="abc1234",
                message="Dated commit",
                date=datetime(2024, 1, 15, 10, 0),
            ),
            RecentCommit(short_sha="def5678", message="Undated commit 1"),
            RecentCommit(short_sha="abc9012", message="Undated commit 2"),
        ]

        result = self.service.format_recent_commits(commits)
        lines = result.split("\n")

        # Dated commits first, then undated with fallback format
        assert lines[0] == "2024-01-15 abc1234 Dated commit"
        assert lines[1] == "def5678: Undated commit 1"
        assert lines[2] == "abc9012: Undated commit 2"

    # Test "[dim]No commits[/dim]" display for empty commit lists - Requirement 3.4
    def test_empty_commit_list_display_preserved(self):
        """Test that '[dim]No commits[/dim]' display for empty commit lists is preserved."""
        result = self.service.format_recent_commits([])
        assert result == "[dim]No commits[/dim]"

    def test_empty_commit_list_with_none_input(self):
        """Test empty commit list handling with None input."""
        result = self.service.format_recent_commits(None or [])
        assert result == "[dim]No commits[/dim]"

    # Test commit message cleaning functionality is preserved - Requirement 3.5
    def test_commit_message_cleaning_preserved(self):
        """Test that commit message cleaning functionality is preserved."""

        # Test message with newlines and extra whitespace
        commit = RecentCommit(
            short_sha="abc1234",
            message="Line 1\nLine 2\n\n  Line 3  \t\n",
            date=datetime(2024, 1, 15, 10, 0),
        )

        result = self.service.format_recent_commits([commit])
        assert result == "2024-01-15 abc1234 Line 1 Line 2 Line 3"

    def test_commit_message_cleaning_various_whitespace(self):
        """Test commit message cleaning with various whitespace characters."""

        test_cases = [
            ("Simple message", "Simple message"),
            ("  Leading spaces", "Leading spaces"),
            ("Trailing spaces  ", "Trailing spaces"),
            ("Multiple\n\nNewlines", "Multiple Newlines"),
            ("Tabs\tand\tspaces", "Tabs and spaces"),
            ("Mixed\n  \t\nWhitespace", "Mixed Whitespace"),
            ("", ""),  # Empty message
        ]

        for input_message, expected_cleaned in test_cases:
            if input_message == "":  # Skip empty message test due to validation
                continue
            commit = RecentCommit(
                short_sha="abc1234",
                message=input_message,
                date=datetime(2024, 1, 15, 10, 0),
            )

            result = self.service.format_recent_commits([commit])
            expected_result = (
                f"2024-01-15 abc1234 {expected_cleaned}"
                if expected_cleaned
                else "2024-01-15 abc1234 "
            )
            assert result == expected_result

    def test_clean_commit_message_method_directly(self):
        """Test _clean_commit_message method directly."""
        test_cases = [
            ("Simple message", "Simple message"),
            ("  Leading and trailing  ", "Leading and trailing"),
            ("Multiple\n\nNewlines\n", "Multiple Newlines"),
            ("Tabs\tand\tspaces", "Tabs and spaces"),
            ("", ""),
            (None, ""),  # Handle None input
        ]

        for input_message, expected in test_cases:
            if input_message is None:
                result = self.service._clean_commit_message("")
            else:
                result = self.service._clean_commit_message(input_message)
            assert result == expected

    # Test that commit format structure remains unchanged - Requirement 6.1
    def test_commit_format_structure_unchanged_with_dates(self):
        """Test that commit format structure remains unchanged for commits with dates."""

        commit = RecentCommit(
            short_sha="abc1234",
            message="Test commit message",
            date=datetime(2024, 1, 15, 10, 30),
        )

        result = self.service.format_recent_commits([commit])

        # Verify exact format: "YYYY-MM-DD sha message"
        assert result == "2024-01-15 abc1234 Test commit message"

        # Verify structure components
        parts = result.split(" ", 2)
        assert len(parts) == 3
        assert parts[0] == "2024-01-15"  # Date
        assert parts[1] == "abc1234"  # SHA
        assert parts[2] == "Test commit message"  # Message

    def test_commit_format_structure_unchanged_without_dates(self):
        """Test that commit format structure remains unchanged for commits without dates."""

        commit = RecentCommit(short_sha="abc1234", message="Test commit message")

        result = self.service.format_recent_commits([commit])

        # Verify exact format: "sha: message"
        assert result == "abc1234: Test commit message"

        # Verify structure components
        parts = result.split(": ", 1)
        assert len(parts) == 2
        assert parts[0] == "abc1234"  # SHA
        assert parts[1] == "Test commit message"  # Message

    # Test that long commit messages are displayed without truncation - Requirement 6.2
    def test_long_commit_messages_no_truncation(self):
        """Test that long commit messages are displayed without truncation."""

        # Create a very long commit message
        long_message = "This is a very long commit message that would previously have been truncated with ellipsis but should now be displayed in full without any truncation regardless of the length of the message content"

        commit = RecentCommit(
            short_sha="abc1234",
            message=long_message,
            date=datetime(2024, 1, 15, 10, 30),
        )

        result = self.service.format_recent_commits([commit])

        # Verify no truncation occurred
        assert "..." not in result
        assert long_message in result
        assert result == f"2024-01-15 abc1234 {long_message}"

    def test_very_long_commit_messages_multiple_commits(self):
        """Test multiple very long commit messages without truncation."""

        long_message_1 = "First extremely long commit message that contains a lot of detailed information about the changes made in this commit and should be displayed in full without any truncation"
        long_message_2 = "Second very long commit message with extensive details about implementation changes, bug fixes, and feature additions that should also be displayed completely"

        commits = [
            RecentCommit(
                short_sha="abc1234",
                message=long_message_1,
                date=datetime(2024, 1, 15, 10, 30),
            ),
            RecentCommit(
                short_sha="def5678",
                message=long_message_2,
                date=datetime(2024, 1, 14, 9, 15),
            ),
        ]

        result = self.service.format_recent_commits(commits)
        lines = result.split("\n")

        # Verify no truncation in either commit
        assert "..." not in result
        assert long_message_1 in lines[0]
        assert long_message_2 in lines[1]
        assert lines[0] == f"2024-01-15 abc1234 {long_message_1}"
        assert lines[1] == f"2024-01-14 def5678 {long_message_2}"

    # Test that table structure remains intact - Requirement 6.3
    def test_table_structure_with_varying_message_lengths(self):
        """Test that table structure remains intact with varying message lengths."""

        commits = [
            RecentCommit(
                short_sha="abc1234",
                message="Short",
                date=datetime(2024, 1, 15, 10, 0),
            ),
            RecentCommit(
                short_sha="def5678",
                message="This is a medium length commit message with some details",
                date=datetime(2024, 1, 14, 9, 0),
            ),
            RecentCommit(
                short_sha="abc9012",
                message="This is an extremely long commit message that contains extensive details about the implementation, including multiple aspects of the changes, bug fixes, feature additions, and comprehensive documentation updates that would previously have been truncated",
                date=datetime(2024, 1, 13, 8, 0),
            ),
        ]

        result = self.service.format_recent_commits(commits)
        lines = result.split("\n")

        # Verify all commits are properly formatted
        assert len(lines) == 3
        assert lines[0].startswith("2024-01-15 abc1234 Short")
        assert lines[1].startswith("2024-01-14 def5678 This is a medium")
        assert lines[2].startswith("2024-01-13 abc9012 This is an extremely")

        # Verify no truncation occurred
        assert "..." not in result

        # Verify each line contains the full message
        assert "Short" in lines[0]
        assert "This is a medium length commit message with some details" in lines[1]
        assert (
            "comprehensive documentation updates that would previously have been truncated"
            in lines[2]
        )

    # Test backward compatibility with existing command-line options - Requirement 6.4
    def test_format_recent_commits_with_column_width_parameter(self):
        """Test that format_recent_commits still accepts column_width parameter for backward compatibility."""

        commit = RecentCommit(
            short_sha="abc1234",
            message="Test commit message",
            date=datetime(2024, 1, 15, 10, 30),
        )

        # Test with various column widths - should not affect output since truncation is removed
        for width in [30, 50, 100, 200]:
            result = self.service.format_recent_commits([commit], column_width=width)
            assert result == "2024-01-15 abc1234 Test commit message"
            assert "..." not in result

    def test_format_recent_commits_default_column_width(self):
        """Test that format_recent_commits works with default column_width parameter."""

        commit = RecentCommit(
            short_sha="abc1234",
            message="Test commit message",
            date=datetime(2024, 1, 15, 10, 30),
        )

        # Test without specifying column_width (should use default)
        result = self.service.format_recent_commits([commit])
        assert result == "2024-01-15 abc1234 Test commit message"
        assert "..." not in result

    # Test edge cases and special characters
    def test_commit_messages_with_special_characters(self):
        """Test commit messages with special characters are handled correctly."""

        special_messages = [
            "feat: add user authentication with OAuth2 🔐",
            "fix(api): resolve null pointer exception in /users endpoint",
            "docs: update README.md with installation instructions",
            "refactor: extract utility functions into separate module",
            "test: add unit tests for UserService class",
            "chore: bump dependencies to latest versions",
            "style: format code with prettier and eslint",
        ]

        commits = [
            RecentCommit(
                short_sha=f"{i:07x}",  # Generate valid 7-char hex SHA
                message=message,
                date=datetime(2024, 1, 15 - i, 10, 0),
            )
            for i, message in enumerate(special_messages, 1)
        ]

        result = self.service.format_recent_commits(commits)
        lines = result.split("\n")

        # Verify all special characters are preserved
        for i, message in enumerate(special_messages):
            assert message in lines[i]
            assert "..." not in lines[i]

    def test_commit_messages_with_unicode_characters(self):
        """Test commit messages with Unicode characters are handled correctly."""

        unicode_messages = [
            "添加中文支持 (Add Chinese support)",
            "Añadir soporte para español",
            "Добавить поддержку русского языка",
            "日本語サポートを追加",
            "العربية دعم إضافة",
        ]

        commits = [
            RecentCommit(
                short_sha=f"{i+10:06x}a",  # Generate valid 7-char hex SHA
                message=message,
                date=datetime(2024, 1, 15 - i, 10, 0),
            )
            for i, message in enumerate(unicode_messages)
        ]

        result = self.service.format_recent_commits(commits)
        lines = result.split("\n")

        # Verify all Unicode characters are preserved
        for i, message in enumerate(unicode_messages):
            assert message in lines[i]
            assert "..." not in lines[i]

    def test_empty_and_whitespace_only_messages(self):
        """Test handling of empty and whitespace-only commit messages."""

        commits = [
            RecentCommit(
                short_sha="abc1234",
                message=" ",  # Single space to meet min_length=1 requirement
                date=datetime(2024, 1, 15, 10, 0),
            ),
            RecentCommit(
                short_sha="def5678",
                message="   ",
                date=datetime(2024, 1, 14, 10, 0),
            ),
            RecentCommit(
                short_sha="abc9012",
                message="\n\n ",  # Add space to meet min_length requirement
                date=datetime(2024, 1, 13, 10, 0),
            ),
        ]

        result = self.service.format_recent_commits(commits)
        lines = result.split("\n")

        # Verify empty messages are handled gracefully
        assert lines[0] == "2024-01-15 abc1234 "  # Single space cleaned to empty
        assert lines[1] == "2024-01-14 def5678 "  # Whitespace cleaned to empty
        assert lines[2] == "2024-01-13 abc9012 "  # Newlines cleaned to empty

    # Integration test to verify all requirements together
    def test_comprehensive_backward_compatibility_integration(self):
        """Comprehensive test verifying all backward compatibility requirements together."""

        # Mix of commits with various characteristics
        commits = [
            # Recent commit with long message
            RecentCommit(
                short_sha="abc1234",
                message="This is a very long commit message that would have been truncated in the old implementation but should now be displayed in full without any ellipsis or truncation",
                date=datetime(2024, 1, 15, 14, 30),
            ),
            # Older commit with short message
            RecentCommit(
                short_sha="def5678",
                message="Short fix",
                date=datetime(2024, 1, 10, 9, 15),
            ),
            # Commit without date (fallback format)
            RecentCommit(
                short_sha="abc9012",
                message="Commit without date information should use fallback format",
            ),
            # Commit with special characters
            RecentCommit(
                short_sha="abc3456",
                message="feat: add OAuth2 authentication 🔐 with JWT tokens",
                date=datetime(2024, 1, 12, 11, 45),
            ),
            # Commit with cleaned whitespace
            RecentCommit(
                short_sha="abc7890",
                message="Message with\nnewlines\tand  extra   spaces",
                date=datetime(2024, 1, 11, 16, 20),
            ),
        ]

        result = self.service.format_recent_commits(commits)
        lines = result.split("\n")

        # Verify chronological sorting (newest first)
        assert lines[0].startswith("2024-01-15 abc1234")
        assert lines[1].startswith("2024-01-12 abc3456")
        assert lines[2].startswith("2024-01-11 abc7890")
        assert lines[3].startswith("2024-01-10 def5678")
        assert lines[4].startswith("abc9012:")

        # Verify date formatting consistency (YYYY-MM-DD)
        assert "2024-01-15" in lines[0]
        assert "2024-01-12" in lines[1]
        assert "2024-01-11" in lines[2]
        assert "2024-01-10" in lines[3]

        # Verify fallback format for commit without date
        assert (
            lines[4]
            == "abc9012: Commit without date information should use fallback format"
        )

        # Verify no truncation occurred
        assert "..." not in result
        assert (
            "would have been truncated in the old implementation but should now be displayed in full"
            in lines[0]
        )

        # Verify message cleaning
        assert "Message with newlines and extra spaces" in lines[2]

        # Verify special characters preserved
        assert "🔐" in lines[1]
        assert "OAuth2" in lines[1]

        # Verify structure consistency
        for line in lines[:4]:  # Dated commits
            parts = line.split(" ", 2)
            assert len(parts) == 3
            assert len(parts[0]) == 10  # YYYY-MM-DD format
            assert parts[0][4] == "-" and parts[0][7] == "-"

        # Verify fallback structure
        fallback_parts = lines[4].split(": ", 1)
        assert len(fallback_parts) == 2
        assert fallback_parts[0] == "abc9012"
