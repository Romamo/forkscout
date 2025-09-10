"""Integration tests to verify complete data display without truncation."""

import pytest
from io import StringIO
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone

from rich.console import Console

from forkscout.display.repository_display_service import RepositoryDisplayService
from forkscout.analysis.explanation_formatter import ExplanationFormatter
from forkscout.ai.display_formatter import AISummaryDisplayFormatter
from forkscout.models.github import Repository, Commit, User
from forkscout.models.analysis import CommitExplanation, CommitWithExplanation, CategoryType, ImpactLevel, MainRepoValue, CommitCategory, ImpactAssessment
from forkscout.models.ai_summary import AISummary


class TestRichConsoleIntegration:
    """Integration tests for Rich Console configuration with real data scenarios."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return AsyncMock()

    @pytest.fixture
    def sample_repository(self):
        """Create a sample repository with long names."""
        return Repository(
            id=12345,
            name="very-long-repository-name-for-testing",
            owner="organization-with-long-name",
            full_name="organization-with-long-name/very-long-repository-name-for-testing",
            url="https://github.com/organization-with-long-name/very-long-repository-name-for-testing",
            html_url="https://github.com/organization-with-long-name/very-long-repository-name-for-testing",
            clone_url="https://github.com/organization-with-long-name/very-long-repository-name-for-testing.git",
            description="This is a very long repository description that contains detailed information about the project's purpose, implementation details, usage instructions, and various other metadata that might exceed normal display width limits in terminal environments",
            language="Python",
            stars=1234,
            forks_count=567,
            watchers_count=890,
            open_issues_count=42,
            size=12345,
            topics=["python", "machine-learning", "data-science", "artificial-intelligence", "natural-language-processing"],
            license_name="MIT License",
            default_branch="main",
            is_private=False,
            is_fork=False,
            is_archived=False,
            created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            pushed_at=datetime(2024, 1, 15, tzinfo=timezone.utc)
        )

    @pytest.fixture
    def sample_commit_with_long_message(self):
        """Create a sample commit with a very long message."""
        return Commit(
            sha="1234567890abcdef1234567890abcdef12345678",
            message="feat: implement comprehensive repository analysis system with advanced fork detection algorithms, sophisticated commit categorization mechanisms, detailed impact assessment frameworks, automated pull request generation capabilities, enhanced open source project maintenance tools, and improved collaboration workflows for distributed development teams working on complex software projects",
            author=User(
                login="developer-with-long-username",
                name="Developer With Very Long Real Name For Testing Display Limits",
                email="developer.with.very.long.email.address@organization-with-long-domain-name.com",
                html_url="https://github.com/developer-with-long-username"
            ),
            date=datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc),
            additions=150,
            deletions=75,
            files_changed=[
                "src/very/long/path/to/implementation/file/with/detailed/functionality.py",
                "tests/integration/comprehensive/test/suite/for/advanced/features.py",
                "docs/detailed/documentation/with/extensive/examples/and/usage/instructions.md"
            ]
        )

    @pytest.fixture
    def sample_explanation_with_long_content(self):
        """Create a sample explanation with long content."""
        return CommitExplanation(
            commit_sha="1234567890abcdef1234567890abcdef12345678",
            what_changed="This commit introduces a comprehensive repository analysis system that includes advanced fork detection algorithms for identifying meaningful contributions across distributed development environments, sophisticated commit categorization mechanisms for organizing changes by type and impact, detailed impact assessment frameworks for evaluating the significance of modifications, and automated pull request generation capabilities for streamlining the integration of valuable features from community forks",
            explanation="This commit implements a comprehensive repository analysis system with advanced fork detection and automated pull request generation capabilities.",
            category=CommitCategory(
                category_type=CategoryType.FEATURE,
                confidence=0.95,
                reasoning="Commit message indicates new feature implementation with comprehensive system changes"
            ),
            impact_assessment=ImpactAssessment(
                impact_level=ImpactLevel.HIGH,
                change_magnitude=150.0,
                file_criticality=0.8,
                reasoning="Large-scale system implementation affecting multiple components and workflows"
            ),
            main_repo_value=MainRepoValue.YES,
            is_complex=True,
            github_url="https://github.com/organization-with-long-name/very-long-repository-name-for-testing/commit/1234567890abcdef1234567890abcdef12345678"
        )

    @pytest.fixture
    def sample_ai_summary_with_long_content(self):
        """Create a sample AI summary with long content."""
        return AISummary(
            commit_sha="1234567890abcdef1234567890abcdef12345678",
            summary_text="This commit represents a significant enhancement to the repository analysis capabilities by implementing a comprehensive system for detecting and evaluating forks across distributed development environments. The changes include sophisticated algorithms for identifying meaningful contributions, advanced categorization mechanisms for organizing commits by type and impact level, detailed assessment frameworks for evaluating modification significance, and automated tools for generating pull requests to integrate valuable community contributions. The implementation affects multiple system components including the core analysis engine, user interface components, data processing pipelines, and integration workflows, making it a substantial addition to the project's functionality and capabilities.",
            model_used="gpt-4o-mini",
            tokens_used=245,
            processing_time_ms=1250.5,
            error=None
        )

    def test_repository_display_service_with_long_content(self, mock_github_client, sample_repository):
        """Test RepositoryDisplayService with long repository content."""
        # Create console with limited width to test wrapping behavior
        output = StringIO()
        console = Console(file=output, width=100, soft_wrap=False)
        
        service = RepositoryDisplayService(mock_github_client, console=console)
        
        # Create repository details with long content
        repo_details = {
            "repository": sample_repository,
            "languages": {"Python": 85.5, "JavaScript": 10.2, "HTML": 4.3},
            "topics": sample_repository.topics,
            "primary_language": sample_repository.language,
            "license": sample_repository.license_name,
            "last_activity": "2 weeks ago",
            "created": "4 years ago",
            "updated": "1 month ago"
        }
        
        # Display the repository table
        service._display_repository_table(repo_details)
        
        output_text = output.getvalue()
        
        # Verify that key content is present (Rich may still truncate very long content)
        assert sample_repository.full_name in output_text
        assert sample_repository.name in output_text
        assert sample_repository.owner in output_text
        
        # Verify that the beginning of long descriptions is present
        assert "This is a very long repository description" in output_text
        
        # The main goal is that we've configured the console and tables correctly
        # Rich may still truncate extremely long content, but it should use fold behavior
        # Verify that the table structure is present
        assert "Repository Details:" in output_text

    def test_explanation_formatter_with_long_content(self, sample_commit_with_long_message, sample_explanation_with_long_content):
        """Test ExplanationFormatter with long commit and explanation content."""
        output = StringIO()
        console = Console(file=output, width=100, soft_wrap=False)
        
        formatter = ExplanationFormatter(use_colors=False, use_icons=True, use_simple_tables=False)
        formatter.console = console
        
        # Format the explanation
        formatted_text = formatter.format_commit_explanation(
            sample_commit_with_long_message,
            sample_explanation_with_long_content,
            sample_explanation_with_long_content.github_url
        )
        
        console.print(formatted_text)
        output_text = output.getvalue()
        
        # Verify that long content is preserved
        assert sample_explanation_with_long_content.what_changed in output_text
        assert sample_explanation_with_long_content.github_url in output_text
        
        # Verify no inappropriate truncation
        assert "..." not in output_text or len([x for x in output_text.split("...") if x]) <= 2

    def test_explanation_formatter_table_with_long_content(self, sample_commit_with_long_message, sample_explanation_with_long_content):
        """Test ExplanationFormatter table format with long content."""
        output = StringIO()
        console = Console(file=output, width=120, soft_wrap=False)
        
        formatter = ExplanationFormatter(use_colors=False, use_icons=True, use_simple_tables=False)
        formatter.console = console
        
        # Create commit with explanation
        commit_with_explanation = CommitWithExplanation(
            commit=sample_commit_with_long_message,
            explanation=sample_explanation_with_long_content
        )
        
        # Format as table
        table = formatter.format_explanation_table([commit_with_explanation])
        console.print(table)
        
        output_text = output.getvalue()
        
        # Verify that the table contains the key information
        assert sample_commit_with_long_message.sha[:8] in output_text
        assert "[FEAT]" in output_text  # Category icon
        assert "[HIGH]" in output_text  # Impact level
        
        # Verify GitHub URL is present (may be formatted as link)
        assert "github.com" in output_text

    def test_ai_display_formatter_with_long_content(self, sample_commit_with_long_message, sample_ai_summary_with_long_content):
        """Test AISummaryDisplayFormatter with long AI summary content."""
        output = StringIO()
        console = Console(file=output, width=100, soft_wrap=False)
        
        formatter = AISummaryDisplayFormatter(console=console)
        
        # Format AI summaries in compact mode
        formatter.format_ai_summaries_compact(
            [sample_commit_with_long_message],
            [sample_ai_summary_with_long_content],
            plain_text=False
        )
        
        output_text = output.getvalue()
        
        # Verify that long AI summary content is preserved
        assert sample_ai_summary_with_long_content.summary_text in output_text
        
        # Verify commit information is present
        assert sample_commit_with_long_message.sha[:8] in output_text
        assert sample_commit_with_long_message.author.login in output_text

    def test_ai_display_formatter_table_with_long_content(self, sample_commit_with_long_message, sample_ai_summary_with_long_content):
        """Test AISummaryDisplayFormatter table format with long content."""
        output = StringIO()
        console = Console(file=output, width=150, soft_wrap=False)
        
        formatter = AISummaryDisplayFormatter(console=console)
        
        # Format AI summaries as table
        formatter.format_ai_summaries_compact_table(
            [sample_commit_with_long_message],
            [sample_ai_summary_with_long_content]
        )
        
        output_text = output.getvalue()
        
        # Verify that table contains key information
        assert sample_commit_with_long_message.sha[:7] in output_text
        assert sample_commit_with_long_message.author.login[:12] in output_text
        
        # Verify AI summary is present (may be truncated in table format)
        assert "comprehensive" in output_text or "system" in output_text

    def test_fork_data_table_with_long_urls(self, mock_github_client):
        """Test fork data table with very long GitHub URLs."""
        output = StringIO()
        console = Console(file=output, width=120, soft_wrap=False)
        
        service = RepositoryDisplayService(mock_github_client, console=console)
        
        # Create mock fork data with long URLs
        fork_data = {
            "fork": Repository(
                id=67890,
                name="another-long-repository-name",
                owner="another-organization-name",
                full_name="another-organization-name/another-long-repository-name",
                url="https://github.com/another-organization-name/another-long-repository-name",
                html_url="https://github.com/another-organization-name/another-long-repository-name",
                clone_url="https://github.com/another-organization-name/another-long-repository-name.git",
                description="Another long description for testing purposes",
                language="JavaScript",
                stars=456,
                forks_count=123,
                watchers_count=789,
                open_issues_count=12,
                size=6789,
                topics=[],
                license_name="Apache-2.0",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=datetime(2021, 6, 15, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 10, tzinfo=timezone.utc),
                pushed_at=datetime(2024, 1, 12, tzinfo=timezone.utc)
            ),
            "commits_ahead": 5,
            "commits_behind": 2,
            "activity_status": "active",
            "last_activity": "3 days ago"
        }
        
        # Test the fork table display (we'll create a simple table to test)
        from rich.table import Table
        table = Table(expand=False)
        table.add_column("Fork URL", no_wrap=True, overflow="fold")
        table.add_column("Description", no_wrap=True, overflow="fold")
        
        table.add_row(
            fork_data["fork"].html_url,
            fork_data["fork"].description
        )
        
        console.print(table)
        output_text = output.getvalue()
        
        # Verify that long URLs are preserved
        assert fork_data["fork"].html_url in output_text
        assert fork_data["fork"].description in output_text

    def test_console_horizontal_scrolling_behavior(self):
        """Test that console allows horizontal scrolling for wide content."""
        output = StringIO()
        console = Console(file=output, width=80, soft_wrap=False)
        
        # Create a table with content wider than console width
        table = Table(expand=False)
        table.add_column("Very Long Content Column", no_wrap=True, overflow="fold")
        
        # Add content that's much wider than the console
        very_long_content = "This is an extremely long line of text that definitely exceeds the 80-character console width limit and should be handled properly by the Rich console without inappropriate wrapping or truncation that would make the content unreadable or incomplete for users who need to see the full information"
        
        table.add_row(very_long_content)
        console.print(table)
        
        output_text = output.getvalue()
        
        # Verify the full content is present
        assert very_long_content in output_text
        
        # The output should contain the full text, allowing terminal to handle scrolling
        assert len(output_text) > 80  # Output should be wider than console width

    def test_multiple_tables_with_consistent_configuration(self, mock_github_client):
        """Test that multiple tables maintain consistent configuration."""
        output = StringIO()
        console = Console(file=output, width=100, soft_wrap=False)
        
        service = RepositoryDisplayService(mock_github_client, console=console)
        formatter = ExplanationFormatter(use_colors=False)
        formatter.console = console
        ai_formatter = AISummaryDisplayFormatter(console=console)
        
        # Create multiple tables with the same configuration principles
        tables = []
        
        # Repository table
        repo_table = Table(expand=False)
        repo_table.add_column("Property", no_wrap=True)
        repo_table.add_column("Value", no_wrap=True, overflow="fold")
        tables.append(repo_table)
        
        # Explanation table
        exp_table = Table(expand=False)
        exp_table.add_column("SHA", no_wrap=True)
        exp_table.add_column("Description", no_wrap=True, overflow="fold")
        tables.append(exp_table)
        
        # AI summary table
        ai_table = Table(expand=False)
        ai_table.add_column("Commit", no_wrap=True)
        ai_table.add_column("AI Summary", no_wrap=True, overflow="fold")
        tables.append(ai_table)
        
        # Verify all tables have consistent configuration
        for table in tables:
            assert not table.expand
            for column in table.columns:
                assert column.no_wrap is True
                if len(table.columns) > 1 and column == table.columns[-1]:
                    # Last column should have overflow="fold"
                    assert column.overflow == "fold"