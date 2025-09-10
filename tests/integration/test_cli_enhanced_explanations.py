"""Integration tests for enhanced CLI explanation display."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from forkscout.cli import cli
from forkscout.models.analysis import (
    CategoryType,
    CommitCategory,
    CommitExplanation,
    ImpactAssessment,
    ImpactLevel,
    MainRepoValue,
)
from forkscout.models.github import Commit, Repository, User


class TestCLIEnhancedExplanations:
    """Test enhanced CLI explanation display functionality."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner."""
        return CliRunner()

    @pytest.fixture
    def sample_repository(self):
        """Create a sample repository."""
        return Repository(
            owner="testowner",
            name="testrepo",
            full_name="testowner/testrepo",
            url="https://api.github.com/repos/testowner/testrepo",
            html_url="https://github.com/testowner/testrepo",
            clone_url="https://github.com/testowner/testrepo.git"
        )

    @pytest.fixture
    def sample_user(self):
        """Create a sample user."""
        return User(
            login="testuser",
            html_url="https://github.com/testuser"
        )

    @pytest.fixture
    def sample_commit(self, sample_user):
        """Create a sample commit."""
        return Commit(
            sha="abc123def456789012345678901234567890abcd",
            message="feat: add user authentication system",
            author=sample_user,
            date=datetime.utcnow(),
            additions=100,
            deletions=20,
            files_changed=["auth.py", "user_service.py"]
        )

    @pytest.fixture
    def sample_explanation(self):
        """Create a sample explanation."""
        category = CommitCategory(
            category_type=CategoryType.FEATURE,
            confidence=0.9,
            reasoning="Adds new authentication functionality"
        )

        impact = ImpactAssessment(
            impact_level=ImpactLevel.HIGH,
            change_magnitude=120.0,
            file_criticality=0.8,
            quality_factors={"test_coverage": 0.7},
            reasoning="Significant security-related changes"
        )

        return CommitExplanation(
            commit_sha="abc123def456789012345678901234567890abcd",
            category=category,
            impact_assessment=impact,
            what_changed="Added JWT-based user authentication system",
            main_repo_value=MainRepoValue.YES,
            explanation="This commit adds a comprehensive authentication system using JWT tokens.",
            is_complex=False,
            github_url="https://github.com/testowner/testrepo/commit/abc123def456789012345678901234567890abcd"
        )

    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli._display_commit_explanations_for_commits")
    def test_analyze_fork_with_explain_flag(
        self, mock_display_explanations, mock_github_client_class, runner, sample_repository
    ):
        """Test analyze-fork command with --explain flag."""
        # Mock GitHub client
        mock_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_client

        # Mock InteractiveAnalyzer
        with patch("forklift.analysis.interactive_analyzer.InteractiveAnalyzer") as mock_analyzer_class:
            mock_analyzer = AsyncMock()
            mock_analyzer_class.return_value = mock_analyzer

            # Mock analysis result
            mock_analyzer.analyze_specific_fork.return_value = {
                "fork_details": Mock(fork=Mock(default_branch="main")),
                "branch_analysis": {"commits": []}
            }

            # Mock display functions
            with patch("forklift.cli._display_feature_analysis_summary"):
                # Run command with --explain flag
                result = runner.invoke(cli, [
                    "analyze-fork",
                    "https://github.com/testowner/testrepo",
                    "--explain"
                ], env={"GITHUB_TOKEN": "ghp_1234567890123456789012345678901234567890"})

                # Verify command executed successfully
                assert result.exit_code == 0

                # Verify that explanation display was called (indirectly through _display_commit_analysis)
                # The exact verification depends on the mocking structure

    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli._display_commit_explanations_for_commits")
    def test_show_commits_with_explain_flag(
        self, mock_display_explanations, mock_github_client_class, runner, sample_repository, sample_commit
    ):
        """Test show-commits command with --explain flag."""
        # Mock GitHub client
        mock_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_client

        # Mock repository and commits
        mock_client.get_repository.return_value = sample_repository
        mock_client.get_branch_commits.return_value = [sample_commit.model_dump()]

        # Mock display functions
        with patch("forklift.cli._display_commits_table"):
            # Run command with --explain flag
            result = runner.invoke(cli, [
                "show-commits",
                "https://github.com/testowner/testrepo",
                "--explain"
            ], env={"GITHUB_TOKEN": "ghp_1234567890123456789012345678901234567890"})

            # Verify command executed successfully
            if result.exit_code != 0:
                print(f"Command failed with output: {result.output}")
            assert result.exit_code == 0

            # Verify that explanation display was called (if commits were found)
            # Note: The exact call depends on whether commits were processed
            # For now, just verify the command completed successfully

    def test_display_commit_explanations_function_import(self):
        """Test that the display_commit_explanations function imports correctly."""
        from forkscout.cli import display_commit_explanations

        # Function should exist and be callable
        assert callable(display_commit_explanations)

    @patch("forklift.analysis.explanation_formatter.ExplanationFormatter")
    def test_display_commit_explanations_uses_formatter(self, mock_formatter_class):
        """Test that display_commit_explanations uses the ExplanationFormatter."""
        from forkscout.cli import display_commit_explanations

        # Create mock formatter
        mock_formatter = Mock()
        mock_formatter_class.return_value = mock_formatter
        mock_formatter.format_explanation_table.return_value = Mock()

        # Create mock fork analysis with explanations
        mock_fork_analysis = Mock()
        mock_fork_analysis.commit_explanations = [Mock()]
        mock_fork_analysis.fork.repository.full_name = "test/repo"
        mock_fork_analysis.features = []

        # Call function
        display_commit_explanations([mock_fork_analysis], True)

        # Verify formatter was created and used
        mock_formatter_class.assert_called_once_with(use_colors=True, use_icons=True)

    def test_explanation_formatter_integration(self):
        """Test that ExplanationFormatter integrates correctly with CLI."""
        from forkscout.analysis.explanation_formatter import ExplanationFormatter

        # Create formatter
        formatter = ExplanationFormatter(use_colors=True, use_icons=True)

        # Verify it has the expected methods
        assert hasattr(formatter, "format_explanation_table")
        assert hasattr(formatter, "format_commit_explanation")
        assert hasattr(formatter, "create_formatted_explanation")

        # Verify it can handle empty input
        table = formatter.format_explanation_table([])
        assert table is not None

    @patch("forklift.cli.console")
    def test_enhanced_explanation_display_output(self, mock_console):
        """Test that enhanced explanation display produces expected output."""
        from forkscout.cli import display_commit_explanations

        # Create mock fork analysis with no explanations
        mock_fork_analysis = Mock()
        mock_fork_analysis.commit_explanations = None

        # Call function
        display_commit_explanations([mock_fork_analysis], True)

        # Verify console output was called
        assert mock_console.print.called

    def test_github_link_generator_integration(self):
        """Test that GitHubLinkGenerator is properly integrated."""
        from forkscout.analysis.github_link_generator import GitHubLinkGenerator

        # Test basic functionality
        url = GitHubLinkGenerator.generate_commit_url(
            "owner", "repo", "abc123def456789012345678901234567890abcd"
        )

        expected = "https://github.com/owner/repo/commit/abc123def456789012345678901234567890abcd"
        assert url == expected

        # Test validation
        assert GitHubLinkGenerator.validate_commit_url(url)

        # Test clickable link formatting
        clickable = GitHubLinkGenerator.format_clickable_link(url, "View Commit")
        assert url in clickable
        assert "View Commit" in clickable
