"""Unit tests for AI summary display formatter."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from io import StringIO

from rich.console import Console

from forklift.ai.display_formatter import AISummaryDisplayFormatter
from forklift.models.ai_summary import AISummary, AIUsageStats
from forklift.models.github import Commit, User


@pytest.fixture
def mock_console():
    """Create a mock console for testing."""
    return Console(file=StringIO(), width=150)  # Wider console for table display


@pytest.fixture
def sample_commit():
    """Create a sample commit for testing."""
    return Commit(
        sha="abc123def456789012345678901234567890abcd",
        message="feat: add user authentication system",
        author=User(login="testuser", name="Test User", html_url="https://github.com/testuser"),
        date=datetime(2024, 1, 15, 10, 30, 0),
        additions=150,
        deletions=25,
        files_changed=["auth.py", "models/user.py", "tests/test_auth.py"],
        is_merge=False
    )


@pytest.fixture
def sample_ai_summary():
    """Create a sample AI summary for testing."""
    return AISummary(
        commit_sha="abc123def456789012345678901234567890abcd",
        summary_text="Added comprehensive user authentication system with JWT tokens",
        what_changed="Implemented JWT-based authentication with login/logout endpoints",
        why_changed="To provide secure user access control for the application",
        potential_side_effects="May require database migration for user sessions",
        model_used="gpt-4o-mini",
        tokens_used=245,
        processing_time_ms=1250.5
    )


@pytest.fixture
def sample_ai_summary_with_error():
    """Create a sample AI summary with error for testing."""
    return AISummary(
        commit_sha="abc123def456789012345678901234567890abcd",
        summary_text="",
        what_changed="",
        why_changed="",
        potential_side_effects="",
        error="Rate limit exceeded"
    )


@pytest.fixture
def sample_usage_stats():
    """Create sample usage statistics for testing."""
    return AIUsageStats(
        total_requests=5,
        successful_requests=4,
        failed_requests=1,
        total_tokens_used=1250,
        total_cost_usd=0.0375,
        average_processing_time_ms=1100.0
    )


class TestAISummaryDisplayFormatter:
    """Test cases for AISummaryDisplayFormatter."""

    def test_init_with_console(self, mock_console):
        """Test formatter initialization with provided console."""
        formatter = AISummaryDisplayFormatter(mock_console)
        assert formatter.console == mock_console

    def test_init_without_console(self):
        """Test formatter initialization without console creates new one."""
        formatter = AISummaryDisplayFormatter()
        assert formatter.console is not None

    def test_format_ai_summaries_detailed_empty_lists(self, mock_console):
        """Test detailed formatting with empty commit and summary lists."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        formatter.format_ai_summaries_detailed([], [])
        
        output = mock_console.file.getvalue()
        assert "No AI summaries to display" in output

    def test_format_ai_summaries_detailed_single_commit(
        self, mock_console, sample_commit, sample_ai_summary
    ):
        """Test detailed formatting with single commit and summary."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        formatter.format_ai_summaries_detailed(
            [sample_commit], [sample_ai_summary], show_metadata=True
        )
        
        output = mock_console.file.getvalue()
        assert "AI-Powered Commit Analysis" in output
        assert "abc123de" in output  # Short SHA
        assert "testuser" in output
        assert "feat: add user authentication system" in output
        assert "What Changed" in output
        assert "Why Changed" in output
        assert "Potential Impact" in output
        assert "1250ms" in output  # Processing time
        assert "245 tokens" in output

    def test_format_ai_summaries_detailed_with_error(
        self, mock_console, sample_commit, sample_ai_summary_with_error
    ):
        """Test detailed formatting with AI summary error."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        formatter.format_ai_summaries_detailed(
            [sample_commit], [sample_ai_summary_with_error]
        )
        
        output = mock_console.file.getvalue()
        assert "AI Analysis Error" in output
        assert "Rate limit exceeded" in output

    def test_format_ai_summaries_compact_empty_lists(self, mock_console):
        """Test compact formatting with empty lists."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        formatter.format_ai_summaries_compact([], [])
        
        output = mock_console.file.getvalue()
        assert "No AI summaries to display" in output

    def test_format_ai_summaries_compact_with_data(
        self, mock_console, sample_commit, sample_ai_summary
    ):
        """Test compact formatting with commit and summary data."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        formatter.format_ai_summaries_compact([sample_commit], [sample_ai_summary])
        
        output = mock_console.file.getvalue()
        assert "AI-Powered Commit Summaries" in output
        assert "AI Commit Analysis" in output
        assert "abc12" in output  # Short SHA (truncated in table)
        assert "testuser" in output
        assert "feat: add user" in output  # Message truncated in table

    def test_format_ai_summaries_structured_empty_lists(self, mock_console):
        """Test structured formatting with empty lists."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        formatter.format_ai_summaries_structured([], [])
        
        output = mock_console.file.getvalue()
        assert "No AI summaries to display" in output

    def test_format_ai_summaries_structured_with_github_links(
        self, mock_console, sample_commit, sample_ai_summary
    ):
        """Test structured formatting with GitHub links enabled."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        formatter.format_ai_summaries_structured(
            [sample_commit], [sample_ai_summary], show_github_links=True
        )
        
        output = mock_console.file.getvalue()
        assert "Structured AI Commit Analysis" in output
        assert "abc123de" in output
        assert "What Changed:" in output
        assert "Why Changed:" in output
        assert "Potential Impact:" in output

    def test_format_ai_summaries_structured_without_github_links(
        self, mock_console, sample_commit, sample_ai_summary
    ):
        """Test structured formatting with GitHub links disabled."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        formatter.format_ai_summaries_structured(
            [sample_commit], [sample_ai_summary], show_github_links=False
        )
        
        output = mock_console.file.getvalue()
        assert "Structured AI Commit Analysis" in output
        # Should not contain GitHub URL in table
        assert "github.com" not in output

    def test_display_usage_statistics(self, mock_console, sample_usage_stats):
        """Test usage statistics display."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        formatter.display_usage_statistics(sample_usage_stats, "Test Usage Summary")
        
        output = mock_console.file.getvalue()
        assert "Test Usage Summary" in output
        assert "4/5 (80.0%)" in output  # Success rate
        assert "1,250" in output  # Total tokens
        assert "$0.04" in output  # Cost
        assert "1100ms" in output  # Avg processing time

    def test_display_usage_statistics_low_cost(self, mock_console):
        """Test usage statistics display with very low cost."""
        low_cost_stats = AIUsageStats(
            total_requests=1,
            successful_requests=1,
            failed_requests=0,
            total_tokens_used=50,
            total_cost_usd=0.0015,  # Very low cost
            average_processing_time_ms=500.0
        )
        
        formatter = AISummaryDisplayFormatter(mock_console)
        formatter.display_usage_statistics(low_cost_stats)
        
        output = mock_console.file.getvalue()
        assert "$0.0015" in output  # Should show 4 decimal places for low cost

    def test_truncate_text_short_text(self, mock_console):
        """Test text truncation with short text."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        result = formatter._truncate_text("Short text", 20)
        assert result == "Short text"

    def test_truncate_text_long_text(self, mock_console):
        """Test text truncation with long text."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        long_text = "This is a very long text that should be truncated"
        result = formatter._truncate_text(long_text, 20)
        assert result == "This is a very lo..."
        assert len(result) == 20

    def test_truncate_text_empty_text(self, mock_console):
        """Test text truncation with empty text."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        result = formatter._truncate_text("", 20)
        assert result == "N/A"

    def test_truncate_text_none_text(self, mock_console):
        """Test text truncation with None text."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        result = formatter._truncate_text(None, 20)
        assert result == "N/A"

    def test_format_datetime_simple_valid_date(self, mock_console):
        """Test datetime formatting with valid date."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = formatter._format_datetime_simple(dt)
        assert result == "2024-01-15 10:30"

    def test_format_datetime_simple_none_date(self, mock_console):
        """Test datetime formatting with None date."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        result = formatter._format_datetime_simple(None)
        assert result == "Unknown"

    def test_create_commit_header(self, mock_console, sample_commit):
        """Test commit header creation."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        header = formatter._create_commit_header(sample_commit, 1)
        
        # Check that header contains expected elements
        header_text = str(header)
        assert "#1" in header_text
        assert "abc123de" in header_text
        assert "testuser" in header_text

    def test_create_commit_info_section(self, mock_console, sample_commit):
        """Test commit info section creation."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        info_section = formatter._create_commit_info_section(sample_commit)
        
        # Should be a Group with commit message and changes
        assert info_section is not None

    def test_create_ai_summary_section_no_summary(self, mock_console):
        """Test AI summary section creation with no summary."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        section = formatter._create_ai_summary_section(None, True)
        
        # Should return a Group with "No AI analysis available" message
        assert section is not None

    def test_create_ai_summary_section_with_error(self, mock_console, sample_ai_summary_with_error):
        """Test AI summary section creation with error summary."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        section = formatter._create_ai_summary_section(sample_ai_summary_with_error, True)
        
        # Should return a Group with error panel
        assert section is not None

    def test_create_ai_summary_section_with_data(self, mock_console, sample_ai_summary):
        """Test AI summary section creation with valid summary data."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        section = formatter._create_ai_summary_section(sample_ai_summary, True)
        
        # Should return a Group with panels for each section
        assert section is not None

    def test_add_compact_table_row_with_summary(self, mock_console, sample_commit, sample_ai_summary):
        """Test adding compact table row with valid summary."""
        from rich.table import Table
        
        formatter = AISummaryDisplayFormatter(mock_console)
        table = Table()
        table.add_column("Commit")
        table.add_column("Author")
        table.add_column("Message")
        table.add_column("What Changed")
        table.add_column("Why")
        table.add_column("Impact")
        table.add_column("Meta")
        
        formatter._add_compact_table_row(table, sample_commit, sample_ai_summary)
        
        # Should add a row without errors
        assert len(table.rows) == 1

    def test_add_compact_table_row_with_error(self, mock_console, sample_commit, sample_ai_summary_with_error):
        """Test adding compact table row with error summary."""
        from rich.table import Table
        
        formatter = AISummaryDisplayFormatter(mock_console)
        table = Table()
        table.add_column("Commit")
        table.add_column("Author")
        table.add_column("Message")
        table.add_column("What Changed")
        table.add_column("Why")
        table.add_column("Impact")
        table.add_column("Meta")
        
        formatter._add_compact_table_row(table, sample_commit, sample_ai_summary_with_error)
        
        # Should add a row with error information
        assert len(table.rows) == 1

    def test_add_compact_table_row_no_summary(self, mock_console, sample_commit):
        """Test adding compact table row with no summary."""
        from rich.table import Table
        
        formatter = AISummaryDisplayFormatter(mock_console)
        table = Table()
        table.add_column("Commit")
        table.add_column("Author")
        table.add_column("Message")
        table.add_column("What Changed")
        table.add_column("Why")
        table.add_column("Impact")
        table.add_column("Meta")
        
        formatter._add_compact_table_row(table, sample_commit, None)
        
        # Should add a row with "No summary" information
        assert len(table.rows) == 1

    def test_multiple_commits_detailed_format(self, mock_console):
        """Test detailed formatting with multiple commits."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        # Create multiple commits and summaries
        commits = []
        summaries = []
        
        for i in range(3):
            commit = Commit(
                sha=f"abc123def45{i}" + "0" * (40 - len(f"abc123def45{i}")),
                message=f"feat: add feature {i}",
                author=User(login=f"user{i}", name=f"User {i}", html_url=f"https://github.com/user{i}"),
                date=datetime(2024, 1, 15 + i, 10, 30, 0),
                additions=100 + i * 10,
                deletions=20 + i * 5,
                files_changed=[f"file{i}.py"],
                is_merge=False
            )
            commits.append(commit)
            
            summary = AISummary(
                commit_sha=f"abc123def45{i}" + "0" * (40 - len(f"abc123def45{i}")),
                summary_text=f"Added feature {i}",
                what_changed=f"Implemented feature {i} functionality",
                why_changed=f"To provide feature {i} capability",
                potential_side_effects=f"May affect feature {i} performance",
                model_used="gpt-4o-mini",
                tokens_used=200 + i * 10,
                processing_time_ms=1000.0 + i * 100
            )
            summaries.append(summary)
        
        formatter.format_ai_summaries_detailed(commits, summaries)
        
        output = mock_console.file.getvalue()
        assert "AI-Powered Commit Analysis" in output
        assert "#1/3" in output
        assert "#2/3" in output
        assert "#3/3" in output
        assert "user0" in output
        assert "user1" in output
        assert "user2" in output

    def test_compatibility_with_existing_flags(self, mock_console, sample_commit, sample_ai_summary):
        """Test that formatter works with existing CLI flags like --disable-cache and --limit."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        # Test that formatter doesn't break when used with limited commits
        limited_commits = [sample_commit]
        limited_summaries = [sample_ai_summary]
        
        # Should work with any number of commits
        formatter.format_ai_summaries_detailed(limited_commits, limited_summaries)
        formatter.format_ai_summaries_compact(limited_commits, limited_summaries)
        formatter.format_ai_summaries_structured(limited_commits, limited_summaries)
        
        # All should complete without errors
        output = mock_console.file.getvalue()
        assert len(output) > 0

    def test_visual_consistency_across_formats(self, mock_console, sample_commit, sample_ai_summary):
        """Test that all formatting methods provide consistent visual elements."""
        formatter = AISummaryDisplayFormatter(mock_console)
        
        # Test each format method
        formatter.format_ai_summaries_detailed([sample_commit], [sample_ai_summary])
        detailed_output = mock_console.file.getvalue()
        
        # Reset console
        mock_console.file = StringIO()
        formatter.format_ai_summaries_compact([sample_commit], [sample_ai_summary])
        compact_output = mock_console.file.getvalue()
        
        # Reset console
        mock_console.file = StringIO()
        formatter.format_ai_summaries_structured([sample_commit], [sample_ai_summary])
        structured_output = mock_console.file.getvalue()
        
        # All should contain commit SHA
        assert "abc123de" in detailed_output
        assert "abc12" in compact_output  # Shorter in compact (truncated)
        assert "abc123de" in structured_output
        
        # All should contain author
        assert "testuser" in detailed_output
        assert "testuser" in compact_output
        assert "testuser" in structured_output
        
        # All should contain some form of AI analysis
        assert any(keyword in detailed_output for keyword in ["What Changed", "AI"])
        assert any(keyword in compact_output for keyword in ["AI", "Summary"])
        assert any(keyword in structured_output for keyword in ["What Changed", "AI"])