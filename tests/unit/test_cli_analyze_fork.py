"""Tests for analyze-fork CLI command."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from forklift.cli import cli
from forklift.config.settings import ForkliftConfig, GitHubConfig
from forklift.models.filters import BranchInfo, ForkDetails
from forklift.models.github import Commit, Repository, User


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    from forklift.config.settings import AnalysisConfig, CacheConfig, ScoringConfig

    return ForkliftConfig(
        github=GitHubConfig(token="ghp_1234567890abcdef1234567890abcdef12345678"),
        analysis=AnalysisConfig(
            min_score_threshold=70.0,
            max_forks_to_analyze=100,
            auto_pr_enabled=False
        ),
        scoring=ScoringConfig(),
        cache=CacheConfig(duration_hours=24),
        output_format="markdown",
        dry_run=False
    )


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    return Repository(
        id=123,
        owner="test-owner",
        name="test-repo",
        full_name="test-owner/test-repo",
        url="https://api.github.com/repos/test-owner/test-repo",
        html_url="https://github.com/test-owner/test-repo",
        clone_url="https://github.com/test-owner/test-repo.git",
        default_branch="main",
        stars=100,
        forks_count=50,
        language="Python",
        description="Test repository",
        created_at=datetime(2023, 1, 1),
        updated_at=datetime(2024, 1, 1),
        pushed_at=datetime(2024, 1, 15)
    )


@pytest.fixture
def mock_commits():
    """Create mock commits."""
    user = User(
        id=1,
        login="test-author",
        html_url="https://github.com/test-author"
    )

    return [
        Commit(
            sha="a" * 40,
            message="feat: add new feature",
            author=user,
            date=datetime(2024, 1, 15),
            additions=50,
            deletions=10,
            files_changed=["src/feature.py", "tests/test_feature.py"]
        ),
        Commit(
            sha="b" * 40,
            message="fix: resolve bug in authentication",
            author=user,
            date=datetime(2024, 1, 14),
            additions=5,
            deletions=3,
            files_changed=["src/auth.py"]
        ),
        Commit(
            sha="c" * 40,
            message="docs: update README",
            author=user,
            date=datetime(2024, 1, 13),
            additions=20,
            deletions=5,
            files_changed=["README.md"]
        )
    ]


@pytest.fixture
def mock_fork_details(mock_repository):
    """Create mock fork details."""
    branches = [
        BranchInfo(
            name="main",
            commit_count=100,
            last_commit_date=datetime(2024, 1, 15),
            commits_ahead_of_main=0,
            is_default=True
        ),
        BranchInfo(
            name="feature-branch",
            commit_count=25,
            last_commit_date=datetime(2024, 1, 10),
            commits_ahead_of_main=5,
            is_default=False
        )
    ]

    return ForkDetails(
        fork=mock_repository,
        branches=branches,
        total_commits=125,
        contributors=["test-author", "contributor2"],
        contributor_count=2,
        languages={"Python": 80, "JavaScript": 20},
        topics=["cli", "github", "analysis"]
    )


class TestAnalyzeForkCommand:
    """Test cases for analyze-fork command."""

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.analysis.interactive_analyzer.InteractiveAnalyzer")
    def test_analyze_fork_basic(self, mock_analyzer_class, mock_client_class, mock_load_config,
                               mock_config, mock_fork_details, mock_commits):
        """Test basic analyze-fork command execution."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_analyzer = AsyncMock()
        mock_analyzer_class.return_value = mock_analyzer

        # Mock analysis result
        analysis_result = {
            "fork_details": mock_fork_details,
            "branch_analysis": {
                "branch": "main",
                "commits": mock_commits,
                "commit_types": {"feature": 1, "fix": 1, "docs": 1},
                "total_changes": 93,
                "unique_authors": ["test-author"]
            },
            "analysis_date": datetime(2024, 1, 15)
        }
        mock_analyzer.analyze_specific_fork.return_value = analysis_result

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze-fork", "test-owner/test-repo"])

        # Assertions
        assert result.exit_code == 0
        mock_analyzer.analyze_specific_fork.assert_called_once()

        # Check that output contains expected elements
        assert "Fork Analysis Results" in result.output
        assert "test-owner/test-repo" in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.analysis.interactive_analyzer.InteractiveAnalyzer")
    def test_analyze_fork_with_branch(self, mock_analyzer_class, mock_client_class, mock_load_config,
                                     mock_config, mock_fork_details, mock_commits):
        """Test analyze-fork command with specific branch."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_analyzer = AsyncMock()
        mock_analyzer_class.return_value = mock_analyzer

        analysis_result = {
            "fork_details": mock_fork_details,
            "branch_analysis": {
                "branch": "feature-branch",
                "commits": mock_commits[:2],  # Fewer commits for feature branch
                "commit_types": {"feature": 1, "fix": 1},
                "total_changes": 68,
                "unique_authors": ["test-author"]
            },
            "analysis_date": datetime(2024, 1, 15)
        }
        mock_analyzer.analyze_specific_fork.return_value = analysis_result

        # Run command with branch option
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze-fork", "test-owner/test-repo", "--branch", "feature-branch"])

        # Assertions
        assert result.exit_code == 0

        # Check that the analyzer was called with the correct branch
        call_args = mock_analyzer.analyze_specific_fork.call_args
        assert call_args[0][1] == "feature-branch"  # Second argument should be the branch

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.analysis.interactive_analyzer.InteractiveAnalyzer")
    def test_analyze_fork_with_options(self, mock_analyzer_class, mock_client_class, mock_load_config,
                                      mock_config, mock_fork_details, mock_commits):
        """Test analyze-fork command with various options."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_analyzer = AsyncMock()
        mock_analyzer_class.return_value = mock_analyzer

        analysis_result = {
            "fork_details": mock_fork_details,
            "branch_analysis": {
                "branch": "main",
                "commits": mock_commits,
                "commit_types": {"feature": 1, "fix": 1, "docs": 1},
                "total_changes": 93,
                "unique_authors": ["test-author"]
            },
            "analysis_date": datetime(2024, 1, 15)
        }
        mock_analyzer.analyze_specific_fork.return_value = analysis_result

        # Run command with options
        runner = CliRunner()
        result = runner.invoke(cli, [
            "analyze-fork", "test-owner/test-repo",
            "--max-commits", "100",
            "--include-merge-commits",
            "--show-commit-details"
        ])

        # Assertions
        assert result.exit_code == 0
        mock_analyzer.analyze_specific_fork.assert_called_once()

    @patch("forklift.cli.load_config")
    def test_analyze_fork_no_token(self, mock_load_config):
        """Test analyze-fork command without GitHub token."""
        from forklift.config.settings import AnalysisConfig, CacheConfig, ScoringConfig

        # Setup config without token
        config = ForkliftConfig(
            github=GitHubConfig(token=None),
            analysis=AnalysisConfig(),
            scoring=ScoringConfig(),
            cache=CacheConfig(),
            output_format="markdown",
            dry_run=False
        )
        mock_load_config.return_value = config

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze-fork", "test-owner/test-repo"])

        # Assertions
        assert result.exit_code == 1
        assert "GitHub token not configured" in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.analysis.interactive_analyzer.InteractiveAnalyzer")
    def test_analyze_fork_api_error(self, mock_analyzer_class, mock_client_class, mock_load_config, mock_config):
        """Test analyze-fork command with API error."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_analyzer = AsyncMock()
        mock_analyzer_class.return_value = mock_analyzer
        mock_analyzer.analyze_specific_fork.side_effect = Exception("API Error")

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze-fork", "test-owner/test-repo"])

        # Assertions
        assert result.exit_code == 1
        assert "Failed to analyze fork" in result.output

    def test_analyze_fork_invalid_url(self):
        """Test analyze-fork command with invalid repository URL."""
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze-fork", "invalid-url"])

        # Should fail during URL validation
        assert result.exit_code == 1


class TestAnalyzeForkHelpers:
    """Test helper functions for analyze-fork command."""

    def test_format_datetime_simple(self):
        """Test datetime formatting helper."""
        from forklift.cli import _format_datetime_simple

        # Test various time differences
        now = datetime.utcnow()

        # Today
        today = now
        assert _format_datetime_simple(today) == "Today"

        # Yesterday
        yesterday = datetime(now.year, now.month, now.day - 1) if now.day > 1 else datetime(now.year, now.month - 1, 28)
        result = _format_datetime_simple(yesterday)
        assert "Yesterday" in result or "1d ago" in result

        # None value
        assert _format_datetime_simple(None) == "Unknown"

    @patch("forklift.cli.console")
    def test_display_feature_analysis_summary(self, mock_console, mock_fork_details):
        """Test feature analysis summary display."""
        from forklift.cli import _display_feature_analysis_summary

        branch_analysis = {
            "commits": [Mock() for _ in range(25)],
            "commit_types": {"feature": 15, "fix": 8, "docs": 2},
            "total_changes": 500,
            "unique_authors": ["author1", "author2"]
        }

        # Should not raise any exceptions
        _display_feature_analysis_summary(mock_fork_details, branch_analysis)

        # Check that console.print was called
        assert mock_console.print.called

    @patch("forklift.cli.console")
    def test_display_commits_table(self, mock_console, mock_commits, mock_repository):
        """Test commits table display."""
        from forklift.cli import _display_commits_table

        # Should not raise any exceptions
        _display_commits_table(mock_commits, mock_repository, "main", True, True)

        # Check that console.print was called
        assert mock_console.print.called

    @patch("forklift.cli.console")
    def test_display_commits_table_empty(self, mock_console, mock_repository):
        """Test commits table display with empty commits."""
        from forklift.cli import _display_commits_table

        # Should handle empty commits gracefully
        _display_commits_table([], mock_repository, "main", False, False)

        # Should show "No commits found" message
        assert mock_console.print.called

    @patch("forklift.cli.console")
    def test_display_commit_statistics(self, mock_console, mock_commits):
        """Test commit statistics display."""
        from forklift.cli import _display_commit_statistics

        # Should not raise any exceptions
        _display_commit_statistics(mock_commits)

        # Check that console.print was called
        assert mock_console.print.called

    @patch("forklift.cli.console")
    def test_display_file_changes(self, mock_console, mock_commits):
        """Test file changes display."""
        from forklift.cli import _display_file_changes

        # Should not raise any exceptions
        _display_file_changes(mock_commits)

        # Check that console.print was called
        assert mock_console.print.called


class TestAnalyzeForkIntegration:
    """Integration tests for analyze-fork command."""

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.analysis.interactive_analyzer.InteractiveAnalyzer")
    @patch("forklift.cli.validate_repository_url")
    def test_analyze_fork_full_workflow(self, mock_validate_url, mock_analyzer_class,
                                       mock_client_class, mock_load_config,
                                       mock_config, mock_fork_details, mock_commits):
        """Test complete analyze-fork workflow."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("test-owner", "test-repo")

        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_analyzer = AsyncMock()
        mock_analyzer_class.return_value = mock_analyzer

        # Mock complete analysis result
        analysis_result = {
            "fork_details": mock_fork_details,
            "branch_analysis": {
                "branch": "main",
                "commits": mock_commits,
                "commit_types": {"feature": 1, "fix": 1, "docs": 1},
                "total_changes": 93,
                "unique_authors": ["test-author"]
            },
            "analysis_date": datetime(2024, 1, 15)
        }
        mock_analyzer.analyze_specific_fork.return_value = analysis_result

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze-fork", "test-owner/test-repo"])

        # Assertions
        assert result.exit_code == 0

        # Verify all components were called
        mock_validate_url.assert_called_once_with("test-owner/test-repo")
        mock_analyzer.analyze_specific_fork.assert_called_once()

        # Check output contains expected sections
        assert "Fork Analysis Results" in result.output
        assert "analysis completed successfully" in result.output
