"""Integration tests for AI summary display functionality."""

from datetime import datetime
from io import StringIO

import pytest
from rich.console import Console

from forklift.ai.display_formatter import AISummaryDisplayFormatter
from forklift.models.ai_summary import AISummary
from forklift.models.github import Commit, User


@pytest.mark.integration
class TestAISummaryDisplayIntegration:
    """Integration tests for AI summary display with CLI commands."""

    @pytest.fixture
    def sample_commits_and_summaries(self):
        """Create sample commits and AI summaries for testing."""
        commits = []
        summaries = []

        for i in range(3):
            commit = Commit(
                sha=f"abc123def45{i}" + "0" * (40 - len(f"abc123def45{i}")),
                message=f"feat: implement feature {i}",
                author=User(
                    login=f"developer{i}",
                    name=f"Developer {i}",
                    html_url=f"https://github.com/developer{i}"
                ),
                date=datetime(2024, 1, 15 + i, 10, 30, 0),
                additions=50 + i * 20,
                deletions=10 + i * 5,
                files_changed=[f"feature{i}.py", f"test_feature{i}.py"],
                is_merge=False
            )
            commits.append(commit)

            summary = AISummary(
                commit_sha=commit.sha,
                summary_text=f"Implemented feature {i} with comprehensive functionality",
                model_used="gpt-4o-mini",
                tokens_used=200 + i * 25,
                processing_time_ms=1000.0 + i * 200
            )
            summaries.append(summary)

        return commits, summaries

    def test_detailed_format_integration(self, sample_commits_and_summaries):
        """Test detailed AI summary format integration."""
        commits, summaries = sample_commits_and_summaries

        console = Console(file=StringIO(), width=120)
        formatter = AISummaryDisplayFormatter(console)

        # Test detailed format
        formatter.format_ai_summaries_detailed(commits, summaries, show_metadata=True)

        output = console.file.getvalue()

        # Verify all commits are displayed
        for i, commit in enumerate(commits, 1):
            assert f"#{i}/3" in output
            assert f"developer{i-1}" in output  # Fix off-by-one error (i starts at 1, but developer starts at 0)
            assert f"feat: implement feature {i-1}" in output

        # Verify AI summary is present (simplified format)
        assert "🤖 AI Summary" in output
        assert "Implemented feature" in output  # Part of summary text

        # Verify metadata is shown
        assert "ms" in output  # Processing time
        assert "tokens" in output  # Token usage
        assert "gpt-4o-mini" in output  # Model name

    def test_compact_format_integration(self, sample_commits_and_summaries):
        """Test compact AI summary format integration."""
        commits, summaries = sample_commits_and_summaries

        console = Console(file=StringIO(), width=150)
        formatter = AISummaryDisplayFormatter(console)

        # Test compact format
        formatter.format_ai_summaries_compact(commits, summaries)

        output = console.file.getvalue()

        # Verify table structure
        assert "AI Commit Analysis" in output
        assert "Commit" in output
        assert "Author" in output
        assert "Message" in output
        assert "AI Summary" in output  # Column header for simplified summaries
        assert "Meta" in output

        # Verify all commits are in table
        for commit in commits:
            assert commit.sha[:5] in output  # At least first 5 chars of SHA
            assert commit.author.login in output

    def test_structured_format_integration(self, sample_commits_and_summaries):
        """Test structured AI summary format integration."""
        commits, summaries = sample_commits_and_summaries

        console = Console(file=StringIO(), width=120)
        formatter = AISummaryDisplayFormatter(console)

        # Test structured format with GitHub links
        formatter.format_ai_summaries_structured(commits, summaries, show_github_links=True)

        output = console.file.getvalue()

        # Verify simplified structured display
        assert "Structured AI Commit Analysis" in output
        assert "🤖 AI Summary" in output  # Simplified summary section

        # Verify commit information
        for commit in commits:
            assert commit.sha[:8] in output
            assert commit.author.login in output

    def test_error_handling_integration(self):
        """Test error handling in AI summary display."""
        console = Console(file=StringIO(), width=120)
        formatter = AISummaryDisplayFormatter(console)

        # Create commit with error summary
        commit = Commit(
            sha="abc123def456789012345678901234567890abcd",
            message="feat: test error handling",
            author=User(
                login="testuser",
                name="Test User",
                html_url="https://github.com/testuser"
            ),
            date=datetime(2024, 1, 15, 10, 30, 0),
            additions=50,
            deletions=10,
            files_changed=["test.py"],
            is_merge=False
        )

        error_summary = AISummary(
            commit_sha=commit.sha,
            summary_text="",
            error="OpenAI API rate limit exceeded"
        )

        # Test detailed format with error
        formatter.format_ai_summaries_detailed([commit], [error_summary])

        output = console.file.getvalue()

        # Verify error is displayed properly
        assert "AI Analysis Error" in output
        assert "OpenAI API rate limit exceeded" in output

    def test_usage_statistics_integration(self):
        """Test usage statistics display integration."""
        from forklift.models.ai_summary import AIUsageStats

        console = Console(file=StringIO(), width=120)
        formatter = AISummaryDisplayFormatter(console)

        # Create usage statistics
        usage_stats = AIUsageStats(
            total_requests=10,
            successful_requests=8,
            failed_requests=2,
            total_tokens_used=2500,
            total_cost_usd=0.075,
            average_processing_time_ms=1200.0
        )

        # Test usage statistics display
        formatter.display_usage_statistics(usage_stats, "Integration Test Summary")

        output = console.file.getvalue()

        # Verify statistics are displayed
        assert "Integration Test Summary" in output
        assert "8/10 (80.0%)" in output  # Success rate
        assert "2,500" in output  # Total tokens
        assert "$0.07" in output or "$0.08" in output  # Cost (may be rounded differently)
        assert "1200ms" in output  # Processing time

    def test_disable_cache_compatibility(self, sample_commits_and_summaries):
        """Test that formatter works with --disable-cache flag."""
        commits, summaries = sample_commits_and_summaries

        console = Console(file=StringIO(), width=120)
        formatter = AISummaryDisplayFormatter(console)

        # Test that formatter works regardless of cache settings
        # (The formatter itself doesn't handle caching, but should work with any data)
        formatter.format_ai_summaries_detailed(commits, summaries)
        formatter.format_ai_summaries_compact(commits, summaries)
        formatter.format_ai_summaries_structured(commits, summaries)

        # Should complete without errors
        output = console.file.getvalue()
        assert len(output) > 0

    def test_limit_flag_compatibility(self, sample_commits_and_summaries):
        """Test that formatter works with --limit flag."""
        commits, summaries = sample_commits_and_summaries

        console = Console(file=StringIO(), width=120)
        formatter = AISummaryDisplayFormatter(console)

        # Test with limited number of commits (simulating --limit flag)
        limited_commits = commits[:2]
        limited_summaries = summaries[:2]

        formatter.format_ai_summaries_detailed(limited_commits, limited_summaries)

        output = console.file.getvalue()

        # Should only show 2 commits
        assert "#1/2" in output
        assert "#2/2" in output
        assert "#3/3" not in output  # Third commit should not be present

    def test_visual_separation_integration(self, sample_commits_and_summaries):
        """Test visual separation between original commit data and AI analysis."""
        commits, summaries = sample_commits_and_summaries

        console = Console(file=StringIO(), width=120)
        formatter = AISummaryDisplayFormatter(console)

        # Test detailed format which has the most visual separation
        formatter.format_ai_summaries_detailed(commits[:1], summaries[:1])

        output = console.file.getvalue()

        # Verify clear separation between commit info and AI analysis
        assert "📝" in output  # Commit message indicator
        assert "🔄" in output  # Changes indicator
        assert "🤖 AI Summary" in output  # Simplified AI analysis section

        # Verify panels are used for visual separation (Rich uses different box styles)
        assert any(char in output for char in ["┌", "┏", "╭", "╔"])  # Panel top borders
        assert any(char in output for char in ["└", "┗", "╰", "╚"])  # Panel bottom borders

    def test_empty_data_handling_integration(self):
        """Test handling of empty commits and summaries."""
        console = Console(file=StringIO(), width=120)
        formatter = AISummaryDisplayFormatter(console)

        # Test all formats with empty data
        formatter.format_ai_summaries_detailed([], [])
        formatter.format_ai_summaries_compact([], [])
        formatter.format_ai_summaries_structured([], [])

        output = console.file.getvalue()

        # Should show appropriate messages for empty data
        assert "No AI summaries to display" in output

    def test_mixed_success_error_integration(self, sample_commits_and_summaries):
        """Test display with mix of successful and error summaries."""
        commits, summaries = sample_commits_and_summaries

        # Make one summary an error
        summaries[1] = AISummary(
            commit_sha=commits[1].sha,
            summary_text="",
            error="Network timeout"
        )

        console = Console(file=StringIO(), width=120)
        formatter = AISummaryDisplayFormatter(console)

        formatter.format_ai_summaries_detailed(commits, summaries)

        output = console.file.getvalue()

        # Should show both successful and error summaries
        assert "🤖 AI Summary" in output  # From successful summaries
        assert "AI Analysis Error" in output  # From error summary
        assert "Network timeout" in output  # Error message
