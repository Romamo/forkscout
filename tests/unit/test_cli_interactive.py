"""Unit tests for CLI interactive functionality."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from forkscout.cli import (
    cli,
    display_fork_details,
    display_forks_summary,
    display_repository_details,
)
from forkscout.exceptions import CLIError


class TestInteractiveDisplays:
    """Test interactive display functions."""

    def test_display_repository_details(self):
        """Test repository details display."""
        repo_data = {
            "name": "test-repo",
            "full_name": "owner/test-repo",
            "owner": {"login": "owner"},
            "description": "A test repository",
            "language": "Python",
            "stargazers_count": 100,
            "forks_count": 50,
            "open_issues_count": 10,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-12-01T00:00:00Z",
            "default_branch": "main",
            "size": 1024,
            "license": {"name": "MIT License"}
        }

        # Should not raise any exceptions
        display_repository_details(repo_data)

    def test_display_repository_details_minimal(self):
        """Test repository details display with minimal data."""
        repo_data = {
            "name": "minimal-repo",
            "owner": {"login": "owner"}
        }

        # Should handle missing fields gracefully
        display_repository_details(repo_data)

    def test_display_forks_summary_empty(self):
        """Test forks summary display with no forks."""
        forks = []

        # Should handle empty list gracefully
        display_forks_summary(forks)

    def test_display_forks_summary_with_forks(self):
        """Test forks summary display with fork data."""
        fork1 = Mock()
        fork1.name = "fork1"
        fork1.owner = {"login": "user1"}
        fork1.stargazers_count = 5
        fork1.updated_at = "2023-01-01T00:00:00Z"
        fork1.language = "Python"

        fork2 = Mock()
        fork2.name = "fork2"
        fork2.owner = {"login": "user2"}
        fork2.stargazers_count = 10
        fork2.updated_at = "2023-02-01T00:00:00Z"
        fork2.language = "JavaScript"

        forks = [fork1, fork2]

        # Should display fork information
        display_forks_summary(forks)

    def test_display_fork_details(self):
        """Test individual fork details display."""
        fork = Mock()
        fork.full_name = "user/fork-repo"
        fork.owner = {"login": "user"}
        fork.description = "A forked repository"
        fork.language = "Python"
        fork.stargazers_count = 15
        fork.forks_count = 2
        fork.open_issues_count = 3
        fork.created_at = "2023-01-01T00:00:00Z"
        fork.updated_at = "2023-06-01T00:00:00Z"
        fork.default_branch = "main"

        # Should display fork details
        display_fork_details(fork)

    def test_display_fork_details_with_metrics(self):
        """Test fork details display with metrics."""
        fork = Mock()
        fork.full_name = "user/fork-repo"
        fork.owner = {"login": "user"}
        fork.description = "A forked repository"
        fork.language = "Python"
        fork.stargazers_count = 15
        fork.forks_count = 2
        fork.open_issues_count = 3
        fork.created_at = "2023-01-01T00:00:00Z"
        fork.updated_at = "2023-06-01T00:00:00Z"
        fork.default_branch = "main"

        fork_metrics = Mock()
        fork_metrics.commits_ahead = 5
        fork_metrics.commits_behind = 2
        fork_metrics.last_activity_date = "2023-06-01"

        # Should display fork details with metrics
        display_fork_details(fork, fork_metrics)


class TestInteractiveCommand:
    """Test interactive command functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.runner = CliRunner()

    @patch("forklift.cli.load_config")
    def test_interactive_command_help(self, mock_load_config):
        """Test interactive command help display."""
        mock_config = Mock()
        mock_config.logging = Mock()
        mock_config.logging.level = "INFO"
        mock_config.logging.console_enabled = True
        mock_config.logging.file_enabled = False
        mock_config.logging.format = "%(message)s"
        mock_load_config.return_value = mock_config

        result = self.runner.invoke(cli, ["interactive", "--help"])

        assert result.exit_code == 0
        assert "Launch interactive mode" in result.output
        assert "REPOSITORY_URL" in result.output

    @patch("forklift.cli.load_config")
    def test_interactive_command_invalid_url(self, mock_load_config):
        """Test interactive command with invalid repository URL."""
        mock_config = Mock()
        mock_config.logging = Mock()
        mock_config.logging.level = "INFO"
        mock_config.logging.console_enabled = True
        mock_config.logging.file_enabled = False
        mock_config.logging.format = "%(message)s"
        mock_load_config.return_value = mock_config

        result = self.runner.invoke(cli, ["interactive", "invalid-url"])

        assert result.exit_code == 1
        assert "Invalid GitHub repository URL" in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._run_interactive_analysis")
    def test_interactive_command_success(self, mock_run_interactive, mock_load_config):
        """Test successful interactive command execution."""
        mock_config = Mock()
        mock_config.logging = Mock()
        mock_config.logging.level = "INFO"
        mock_config.logging.console_enabled = True
        mock_config.logging.file_enabled = False
        mock_config.logging.format = "%(message)s"
        mock_load_config.return_value = mock_config

        mock_run_interactive.return_value = {
            "repository": "owner/repo",
            "total_forks": 5,
            "analyzed_forks": 5
        }

        result = self.runner.invoke(cli, ["interactive", "owner/repo"])

        assert result.exit_code == 0
        mock_run_interactive.assert_called_once()

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._run_interactive_analysis")
    def test_interactive_command_keyboard_interrupt(self, mock_run_interactive, mock_load_config):
        """Test interactive command with keyboard interrupt."""
        mock_config = Mock()
        mock_config.logging = Mock()
        mock_config.logging.level = "INFO"
        mock_config.logging.console_enabled = True
        mock_config.logging.file_enabled = False
        mock_config.logging.format = "%(message)s"
        mock_load_config.return_value = mock_config

        mock_run_interactive.side_effect = KeyboardInterrupt()

        result = self.runner.invoke(cli, ["interactive", "owner/repo"])

        assert result.exit_code == 130
        assert "interrupted by user" in result.output


class TestAnalyzeInteractiveOption:
    """Test analyze command with interactive option."""

    def setup_method(self):
        """Setup test fixtures."""
        self.runner = CliRunner()

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._run_interactive_analysis")
    def test_analyze_with_interactive_flag(self, mock_run_interactive, mock_load_config):
        """Test analyze command with interactive flag."""
        mock_config = Mock()
        mock_config.analysis = Mock()
        mock_config.logging = Mock()
        mock_config.analysis.min_score_threshold = 70
        mock_config.analysis.max_forks_to_analyze = 100
        mock_config.analysis.auto_pr_enabled = False
        mock_config.dry_run = False
        mock_config.output_format = "markdown"
        mock_config.logging.level = "INFO"
        mock_config.logging.console_enabled = True
        mock_config.logging.file_enabled = False
        mock_config.logging.format = "%(message)s"
        mock_load_config.return_value = mock_config

        mock_run_interactive.return_value = {
            "repository": "owner/repo",
            "total_forks": 10,
            "analyzed_forks": 5
        }

        result = self.runner.invoke(cli, [
            "analyze", "owner/repo", "--interactive"
        ])

        assert result.exit_code == 0
        mock_run_interactive.assert_called_once()

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._run_analysis")
    def test_analyze_without_interactive_flag(self, mock_run_analysis, mock_load_config):
        """Test analyze command without interactive flag (normal mode)."""
        mock_config = Mock()
        mock_config.analysis = Mock()
        mock_config.logging = Mock()
        mock_config.analysis.min_score_threshold = 70
        mock_config.analysis.max_forks_to_analyze = 100
        mock_config.analysis.auto_pr_enabled = False
        mock_config.dry_run = False
        mock_config.output_format = "markdown"
        mock_config.logging.level = "INFO"
        mock_config.logging.console_enabled = True
        mock_config.logging.file_enabled = False
        mock_config.logging.format = "%(message)s"
        mock_load_config.return_value = mock_config

        mock_run_analysis.return_value = {
            "repository": "owner/repo",
            "total_forks": 10,
            "analyzed_forks": 10,
            "total_features": 5,
            "high_value_features": 2,
            "report": "# Test Report"
        }

        result = self.runner.invoke(cli, ["analyze", "owner/repo"])

        assert result.exit_code == 0
        mock_run_analysis.assert_called_once()
        # Should not call interactive analysis
        assert "Analysis complete" in result.output


class TestInteractiveAnalysisFunction:
    """Test the interactive analysis function."""

    @pytest.mark.asyncio
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.ForkDiscoveryService")
    @patch("forklift.cli.Confirm.ask")
    async def test_run_interactive_analysis_no_token(self, mock_confirm, mock_fork_discovery, mock_github_client):
        """Test interactive analysis without GitHub token."""
        from forkscout.cli import CLIError, _run_interactive_analysis
        from forkscout.config.settings import ForkscoutConfig

        config = ForkscoutConfig()
        config.github.token = None

        with pytest.raises(CLIError, match="GitHub token not configured"):
            await _run_interactive_analysis(config, "owner", "repo", verbose=False)

    @pytest.mark.asyncio
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.ForkDiscoveryService")
    @patch("forklift.cli.Confirm.ask")
    @patch("forklift.cli.Prompt.ask")
    async def test_run_interactive_analysis_user_cancels(self, mock_prompt, mock_confirm, mock_fork_discovery, mock_github_client):
        """Test interactive analysis when user cancels."""
        from forkscout.cli import _run_interactive_analysis
        from forkscout.config.settings import ForkscoutConfig

        config = ForkscoutConfig()
        config.github.token = "ghp_1234567890abcdef1234567890abcdef12345678"

        # Setup mocks
        mock_client_instance = Mock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.get_repository = AsyncMock(return_value={
            "name": "test-repo",
            "owner": {"login": "owner"},
            "description": "Test repository"
        })
        mock_github_client.return_value = mock_client_instance

        # User cancels after seeing repository details
        mock_confirm.return_value = False

        result = await _run_interactive_analysis(config, "owner", "repo", verbose=False)

        assert result["repository"] == "owner/repo"
        assert result["cancelled"] is True

    @pytest.mark.asyncio
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.ForkDiscoveryService")
    @patch("forklift.cli.Confirm.ask")
    @patch("forklift.cli.Prompt.ask")
    async def test_run_interactive_analysis_no_forks(self, mock_prompt, mock_confirm, mock_fork_discovery, mock_github_client):
        """Test interactive analysis with no forks found."""
        from forkscout.cli import _run_interactive_analysis
        from forkscout.config.settings import ForkscoutConfig

        config = ForkscoutConfig()
        config.github.token = "ghp_1234567890abcdef1234567890abcdef12345678"

        # Setup mocks
        mock_client_instance = Mock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.get_repository = AsyncMock(return_value={
            "name": "test-repo",
            "owner": {"login": "owner"},
            "description": "Test repository"
        })
        mock_github_client.return_value = mock_client_instance

        mock_discovery_instance = Mock()
        mock_discovery_instance.discover_forks = AsyncMock(return_value=[])
        mock_fork_discovery.return_value = mock_discovery_instance

        # User continues with fork discovery
        mock_confirm.return_value = True

        result = await _run_interactive_analysis(config, "owner", "repo", verbose=False)

        assert result["repository"] == "owner/repo"
        assert result["total_forks"] == 0
        assert "No forks were found" in result["report"]
