"""Unit tests for CLI show commands (show-repo and show-forks)."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from click.testing import CliRunner

from forklift.cli import cli, CLIError


class TestShowRepoCommand:
    """Test show-repo CLI command functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.runner = CliRunner()

    def create_mock_config(self):
        """Create a properly mocked ForkliftConfig for testing."""
        mock_config = Mock()
        mock_config.github = Mock()
        mock_config.logging = Mock()
        
        # Set default values
        mock_config.github.token = "ghp_1234567890abcdef1234567890abcdef12345678"
        
        mock_config.logging.level = "INFO"
        mock_config.logging.console_enabled = True
        mock_config.logging.file_enabled = False
        mock_config.logging.format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        return mock_config

    @patch('forklift.cli.load_config')
    def test_show_repo_help(self, mock_load_config):
        """Test show-repo command help display."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        result = self.runner.invoke(cli, ["show-repo", "--help"])
        
        assert result.exit_code == 0
        assert "Display detailed repository information" in result.output
        assert "REPOSITORY_URL" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._show_repository_details')
    def test_show_repo_success(self, mock_show_details, mock_load_config):
        """Test successful show-repo command execution."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_show_details.return_value = None
        
        result = self.runner.invoke(cli, ["show-repo", "owner/repo"])
        
        assert result.exit_code == 0
        mock_show_details.assert_called_once()

    @patch('forklift.cli.load_config')
    def test_show_repo_no_token(self, mock_load_config):
        """Test show-repo command without GitHub token."""
        mock_config = self.create_mock_config()
        mock_config.github.token = None
        mock_load_config.return_value = mock_config
        
        result = self.runner.invoke(cli, ["show-repo", "owner/repo"])
        
        assert result.exit_code == 1
        assert "GitHub token not configured" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._show_repository_details')
    def test_show_repo_verbose(self, mock_show_details, mock_load_config):
        """Test show-repo command with verbose flag."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_show_details.return_value = None
        
        result = self.runner.invoke(cli, ["--verbose", "show-repo", "owner/repo"])
        
        assert result.exit_code == 0
        assert "Fetching repository details" in result.output
        mock_show_details.assert_called_once()

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._show_repository_details')
    def test_show_repo_keyboard_interrupt(self, mock_show_details, mock_load_config):
        """Test show-repo command with keyboard interrupt."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_show_details.side_effect = KeyboardInterrupt()
        
        result = self.runner.invoke(cli, ["show-repo", "owner/repo"])
        
        assert result.exit_code == 130
        assert "interrupted by user" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._show_repository_details')
    def test_show_repo_cli_error(self, mock_show_details, mock_load_config):
        """Test show-repo command with CLI error."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_show_details.side_effect = CLIError("Repository not found")
        
        result = self.runner.invoke(cli, ["show-repo", "owner/repo"])
        
        assert result.exit_code == 1
        assert "Repository not found" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._show_repository_details')
    def test_show_repo_unexpected_error(self, mock_show_details, mock_load_config):
        """Test show-repo command with unexpected error."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_show_details.side_effect = Exception("Unexpected error")
        
        result = self.runner.invoke(cli, ["show-repo", "owner/repo"])
        
        assert result.exit_code == 1
        assert "Unexpected error" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._show_repository_details')
    def test_show_repo_debug_mode(self, mock_show_details, mock_load_config):
        """Test show-repo command with debug mode on error."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_show_details.side_effect = Exception("Debug error")
        
        result = self.runner.invoke(cli, ["--debug", "show-repo", "owner/repo"])
        
        assert result.exit_code == 1
        # In debug mode, should show exception details


class TestShowForksCommand:
    """Test show-forks CLI command functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.runner = CliRunner()

    def create_mock_config(self):
        """Create a properly mocked ForkliftConfig for testing."""
        mock_config = Mock()
        mock_config.github = Mock()
        mock_config.logging = Mock()
        
        # Set default values
        mock_config.github.token = "ghp_1234567890abcdef1234567890abcdef12345678"
        
        mock_config.logging.level = "INFO"
        mock_config.logging.console_enabled = True
        mock_config.logging.file_enabled = False
        mock_config.logging.format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        return mock_config

    @patch('forklift.cli.load_config')
    def test_show_forks_help(self, mock_load_config):
        """Test show-forks command help display."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        result = self.runner.invoke(cli, ["show-forks", "--help"])
        
        assert result.exit_code == 0
        assert "Display a summary table of repository forks" in result.output
        assert "REPOSITORY_URL" in result.output
        assert "--max-forks" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._show_forks_summary')
    def test_show_forks_success(self, mock_show_forks, mock_load_config):
        """Test successful show-forks command execution."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_show_forks.return_value = None
        
        result = self.runner.invoke(cli, ["show-forks", "owner/repo"])
        
        assert result.exit_code == 0
        mock_show_forks.assert_called_once()

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._show_forks_summary')
    def test_show_forks_with_max_forks(self, mock_show_forks, mock_load_config):
        """Test show-forks command with max-forks option."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_show_forks.return_value = None
        
        result = self.runner.invoke(cli, ["show-forks", "owner/repo", "--max-forks", "25"])
        
        assert result.exit_code == 0
        mock_show_forks.assert_called_once()
        
        # Check that max_forks parameter was passed correctly
        call_args = mock_show_forks.call_args[0]
        assert call_args[2] == 25  # max_forks parameter

    @patch('forklift.cli.load_config')
    def test_show_forks_no_token(self, mock_load_config):
        """Test show-forks command without GitHub token."""
        mock_config = self.create_mock_config()
        mock_config.github.token = None
        mock_load_config.return_value = mock_config
        
        result = self.runner.invoke(cli, ["show-forks", "owner/repo"])
        
        assert result.exit_code == 1
        assert "GitHub token not configured" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._show_forks_summary')
    def test_show_forks_verbose(self, mock_show_forks, mock_load_config):
        """Test show-forks command with verbose flag."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_show_forks.return_value = None
        
        result = self.runner.invoke(cli, ["--verbose", "show-forks", "owner/repo"])
        
        assert result.exit_code == 0
        assert "Fetching forks for" in result.output
        mock_show_forks.assert_called_once()

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._show_forks_summary')
    def test_show_forks_keyboard_interrupt(self, mock_show_forks, mock_load_config):
        """Test show-forks command with keyboard interrupt."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_show_forks.side_effect = KeyboardInterrupt()
        
        result = self.runner.invoke(cli, ["show-forks", "owner/repo"])
        
        assert result.exit_code == 130
        assert "interrupted by user" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._show_forks_summary')
    def test_show_forks_cli_error(self, mock_show_forks, mock_load_config):
        """Test show-forks command with CLI error."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_show_forks.side_effect = CLIError("Failed to fetch forks")
        
        result = self.runner.invoke(cli, ["show-forks", "owner/repo"])
        
        assert result.exit_code == 1
        assert "Failed to fetch forks" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._show_forks_summary')
    def test_show_forks_max_forks_validation(self, mock_show_forks, mock_load_config):
        """Test show-forks command with invalid max-forks value."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        # Test with value too high
        result = self.runner.invoke(cli, ["show-forks", "owner/repo", "--max-forks", "2000"])
        
        assert result.exit_code == 2  # Click validation error
        assert "Invalid value" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._show_forks_summary')
    def test_show_forks_max_forks_validation_too_low(self, mock_show_forks, mock_load_config):
        """Test show-forks command with max-forks value too low."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        # Test with value too low
        result = self.runner.invoke(cli, ["show-forks", "owner/repo", "--max-forks", "0"])
        
        assert result.exit_code == 2  # Click validation error
        assert "Invalid value" in result.output


class TestShowCommandHelpers:
    """Test helper functions for show commands."""

    @pytest.mark.asyncio
    @patch('forklift.cli.GitHubClient')
    @patch('forklift.cli.RepositoryDisplayService')
    async def test_show_repository_details_success(self, mock_display_service_class, mock_github_client_class):
        """Test _show_repository_details function success."""
        from forklift.cli import _show_repository_details
        from forklift.config.settings import ForkliftConfig
        
        # Setup config
        config = ForkliftConfig()
        config.github.token = "test_token"
        
        # Setup mocks
        mock_client_instance = Mock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_github_client_class.return_value = mock_client_instance
        
        mock_display_service = Mock()
        mock_display_service.show_repository_details = AsyncMock(return_value={"repository": "test"})
        mock_display_service_class.return_value = mock_display_service
        
        # Call function
        await _show_repository_details(config, "owner/repo", verbose=True)
        
        # Verify calls
        mock_github_client_class.assert_called_once_with(config.github)
        mock_display_service_class.assert_called_once()
        mock_display_service.show_repository_details.assert_called_once_with("owner/repo")

    @pytest.mark.asyncio
    @patch('forklift.cli.GitHubClient')
    @patch('forklift.cli.RepositoryDisplayService')
    async def test_show_repository_details_error(self, mock_display_service_class, mock_github_client_class):
        """Test _show_repository_details function with error."""
        from forklift.cli import _show_repository_details, CLIError
        from forklift.config.settings import ForkliftConfig
        
        # Setup config
        config = ForkliftConfig()
        config.github.token = "test_token"
        
        # Setup mocks
        mock_client_instance = Mock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_github_client_class.return_value = mock_client_instance
        
        mock_display_service = Mock()
        mock_display_service.show_repository_details = AsyncMock(side_effect=Exception("Display error"))
        mock_display_service_class.return_value = mock_display_service
        
        # Call function and expect error
        with pytest.raises(CLIError, match="Failed to display repository details"):
            await _show_repository_details(config, "owner/repo", verbose=False)

    @pytest.mark.asyncio
    @patch('forklift.cli.GitHubClient')
    @patch('forklift.cli.RepositoryDisplayService')
    async def test_show_forks_summary_success(self, mock_display_service_class, mock_github_client_class):
        """Test _show_forks_summary function success."""
        from forklift.cli import _show_forks_summary
        from forklift.config.settings import ForkliftConfig
        
        # Setup config
        config = ForkliftConfig()
        config.github.token = "test_token"
        
        # Setup mocks
        mock_client_instance = Mock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_github_client_class.return_value = mock_client_instance
        
        mock_display_service = Mock()
        mock_display_service.show_fork_data = AsyncMock(return_value={
            "total_forks": 10,
            "displayed_forks": 10,
            "collected_forks": [],
            "stats": None
        })
        mock_display_service_class.return_value = mock_display_service
        
        # Call function
        await _show_forks_summary(config, "owner/repo", max_forks=25, verbose=True)
        
        # Verify calls
        mock_github_client_class.assert_called_once_with(config.github)
        mock_display_service_class.assert_called_once()
        mock_display_service.show_fork_data.assert_called_once_with(
            "owner/repo",
            exclude_archived=False,
            exclude_disabled=False,
            sort_by="stars",
            show_all=True,
            disable_cache=False
        )

    @pytest.mark.asyncio
    @patch('forklift.cli.GitHubClient')
    @patch('forklift.cli.RepositoryDisplayService')
    async def test_show_forks_summary_error(self, mock_display_service_class, mock_github_client_class):
        """Test _show_forks_summary function with error."""
        from forklift.cli import _show_forks_summary, CLIError
        from forklift.config.settings import ForkliftConfig
        
        # Setup config
        config = ForkliftConfig()
        config.github.token = "test_token"
        
        # Setup mocks
        mock_client_instance = Mock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_github_client_class.return_value = mock_client_instance
        
        mock_display_service = Mock()
        mock_display_service.show_fork_data = AsyncMock(side_effect=Exception("Forks error"))
        mock_display_service_class.return_value = mock_display_service
        
        # Call function and expect error
        with pytest.raises(CLIError, match="Failed to display forks data"):
            await _show_forks_summary(config, "owner/repo", max_forks=None, verbose=False)


class TestShowPromisingCommand:
    """Test show-promising CLI command functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.runner = CliRunner()

    def create_mock_config(self):
        """Create a properly mocked ForkliftConfig for testing."""
        mock_config = Mock()
        mock_config.github = Mock()
        mock_config.logging = Mock()
        
        # Set default values
        mock_config.github.token = "ghp_1234567890abcdef1234567890abcdef12345678"
        
        mock_config.logging.level = "INFO"
        mock_config.logging.console_enabled = True
        mock_config.logging.file_enabled = False
        mock_config.logging.format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        return mock_config

    @patch('forklift.cli.load_config')
    def test_show_promising_help(self, mock_load_config):
        """Test show-promising command help display."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        result = self.runner.invoke(cli, ["show-promising", "--help"])
        
        assert result.exit_code == 0
        assert "Display promising forks based on configurable filtering criteria" in result.output
        assert "REPOSITORY_URL" in result.output
        assert "--min-stars" in result.output
        assert "--min-commits-ahead" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._show_promising_forks')
    def test_show_promising_success(self, mock_show_promising, mock_load_config):
        """Test successful show-promising command execution."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_show_promising.return_value = None
        
        result = self.runner.invoke(cli, ["show-promising", "owner/repo"])
        
        assert result.exit_code == 0
        mock_show_promising.assert_called_once()

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._show_promising_forks')
    def test_show_promising_with_filters(self, mock_show_promising, mock_load_config):
        """Test show-promising command with filter options."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_show_promising.return_value = None
        
        result = self.runner.invoke(cli, [
            "show-promising", "owner/repo",
            "--min-stars", "5",
            "--min-commits-ahead", "10",
            "--max-days-since-activity", "180",
            "--min-activity-score", "0.5"
        ])
        
        assert result.exit_code == 0
        mock_show_promising.assert_called_once()
        
        # Check that filter parameters were passed correctly
        call_args = mock_show_promising.call_args[0]
        assert call_args[2] == 5  # min_stars
        assert call_args[3] == 10  # min_commits_ahead
        assert call_args[4] == 180  # max_days_since_activity
        assert call_args[5] == 0.5  # min_activity_score

    @patch('forklift.cli.load_config')
    def test_show_promising_no_token(self, mock_load_config):
        """Test show-promising command without GitHub token."""
        mock_config = self.create_mock_config()
        mock_config.github.token = None
        mock_load_config.return_value = mock_config
        
        result = self.runner.invoke(cli, ["show-promising", "owner/repo"])
        
        assert result.exit_code == 1
        assert "GitHub token not configured" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._show_promising_forks')
    def test_show_promising_keyboard_interrupt(self, mock_show_promising, mock_load_config):
        """Test show-promising command with keyboard interrupt."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_show_promising.side_effect = KeyboardInterrupt()
        
        result = self.runner.invoke(cli, ["show-promising", "owner/repo"])
        
        assert result.exit_code == 130
        assert "interrupted by user" in result.output


class TestShowForkDetailsCommand:
    """Test show-fork-details CLI command functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.runner = CliRunner()

    def create_mock_config(self):
        """Create a properly mocked ForkliftConfig for testing."""
        mock_config = Mock()
        mock_config.github = Mock()
        mock_config.logging = Mock()
        
        # Set default values
        mock_config.github.token = "ghp_1234567890abcdef1234567890abcdef12345678"
        
        mock_config.logging.level = "INFO"
        mock_config.logging.console_enabled = True
        mock_config.logging.file_enabled = False
        mock_config.logging.format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        return mock_config

    @patch('forklift.cli.load_config')
    def test_show_fork_details_help(self, mock_load_config):
        """Test show-fork-details command help display."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        result = self.runner.invoke(cli, ["show-fork-details", "--help"])
        
        assert result.exit_code == 0
        assert "Display detailed information about a specific fork" in result.output
        assert "FORK_URL" in result.output
        assert "--max-branches" in result.output
        assert "--max-contributors" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._show_fork_details')
    def test_show_fork_details_success(self, mock_show_fork_details, mock_load_config):
        """Test successful show-fork-details command execution."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_show_fork_details.return_value = None
        
        result = self.runner.invoke(cli, ["show-fork-details", "owner/repo"])
        
        assert result.exit_code == 0
        mock_show_fork_details.assert_called_once()

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._show_fork_details')
    def test_show_fork_details_with_options(self, mock_show_fork_details, mock_load_config):
        """Test show-fork-details command with options."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_show_fork_details.return_value = None
        
        result = self.runner.invoke(cli, [
            "show-fork-details", "owner/repo",
            "--max-branches", "5",
            "--max-contributors", "20",
            "--no-branches",
            "--no-contributors"
        ])
        
        assert result.exit_code == 0
        mock_show_fork_details.assert_called_once()
        
        # Check that options were passed correctly
        call_args = mock_show_fork_details.call_args[0]
        assert call_args[2] == 5  # max_branches
        assert call_args[3] == 20  # max_contributors
        assert call_args[4] is False  # include_branches (inverted from no_branches)
        assert call_args[5] is False  # include_contributors (inverted from no_contributors)

    @patch('forklift.cli.load_config')
    def test_show_fork_details_no_token(self, mock_load_config):
        """Test show-fork-details command without GitHub token."""
        mock_config = self.create_mock_config()
        mock_config.github.token = None
        mock_load_config.return_value = mock_config
        
        result = self.runner.invoke(cli, ["show-fork-details", "owner/repo"])
        
        assert result.exit_code == 1
        assert "GitHub token not configured" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._show_fork_details')
    def test_show_fork_details_keyboard_interrupt(self, mock_show_fork_details, mock_load_config):
        """Test show-fork-details command with keyboard interrupt."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_show_fork_details.side_effect = KeyboardInterrupt()
        
        result = self.runner.invoke(cli, ["show-fork-details", "owner/repo"])
        
        assert result.exit_code == 130
        assert "interrupted by user" in result.output


class TestNewCommandHelpers:
    """Test helper functions for new commands."""

    @pytest.mark.asyncio
    @patch('forklift.cli.GitHubClient')
    @patch('forklift.cli.RepositoryDisplayService')
    async def test_show_promising_forks_success(self, mock_display_service_class, mock_github_client_class):
        """Test _show_promising_forks function success."""
        from forklift.cli import _show_promising_forks
        from forklift.config.settings import ForkliftConfig
        
        # Setup config
        config = ForkliftConfig()
        config.github.token = "test_token"
        
        # Setup mocks
        mock_client_instance = Mock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_github_client_class.return_value = mock_client_instance
        
        mock_display_service = Mock()
        mock_display_service.show_promising_forks = AsyncMock(return_value={
            "total_forks": 10,
            "promising_forks": 3,
            "forks": []
        })
        mock_display_service_class.return_value = mock_display_service
        
        # Call function
        await _show_promising_forks(
            config, "owner/repo", 5, 2, 365, 0.0, False, False, 0, None, None, True
        )
        
        # Verify calls
        mock_github_client_class.assert_called_once_with(config.github)
        mock_display_service_class.assert_called_once()
        mock_display_service.show_promising_forks.assert_called_once()

    @pytest.mark.asyncio
    @patch('forklift.cli.GitHubClient')
    @patch('forklift.analysis.interactive_analyzer.InteractiveAnalyzer')
    async def test_show_fork_details_success(self, mock_analyzer_class, mock_github_client_class):
        """Test _show_fork_details function success."""
        from forklift.cli import _show_fork_details
        from forklift.config.settings import ForkliftConfig
        from forklift.models.filters import ForkDetails
        
        # Setup config
        config = ForkliftConfig()
        config.github.token = "test_token"
        
        # Setup mocks
        mock_client_instance = Mock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_github_client_class.return_value = mock_client_instance
        
        mock_fork_details = Mock(spec=ForkDetails)
        mock_fork_details.branches = []
        mock_fork_details.contributor_count = 0
        
        mock_analyzer = Mock()
        mock_analyzer.show_fork_details = AsyncMock(return_value=mock_fork_details)
        mock_analyzer_class.return_value = mock_analyzer
        
        # Call function
        await _show_fork_details(
            config, "owner/repo", 10, 10, True, True, True, True
        )
        
        # Verify calls
        mock_github_client_class.assert_called_once_with(config.github)
        mock_analyzer_class.assert_called_once()
        mock_analyzer.show_fork_details.assert_called_once()


class TestListForksCommand:
    """Test list-forks CLI command functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.runner = CliRunner()

    def create_mock_config(self):
        """Create a properly mocked ForkliftConfig for testing."""
        mock_config = Mock()
        mock_config.github = Mock()
        mock_config.logging = Mock()
        
        # Set default values
        mock_config.github.token = "ghp_1234567890abcdef1234567890abcdef12345678"
        
        mock_config.logging.level = "INFO"
        mock_config.logging.console_enabled = True
        mock_config.logging.file_enabled = False
        mock_config.logging.format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        return mock_config

    @patch('forklift.cli.load_config')
    def test_list_forks_help(self, mock_load_config):
        """Test list-forks command help display."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        result = self.runner.invoke(cli, ["list-forks", "--help"])
        
        assert result.exit_code == 0
        assert "Display a lightweight preview of repository forks" in result.output
        assert "REPOSITORY_URL" in result.output
        assert "minimal API calls" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._list_forks_preview')
    def test_list_forks_success(self, mock_list_forks, mock_load_config):
        """Test successful list-forks command execution."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_list_forks.return_value = None
        
        result = self.runner.invoke(cli, ["list-forks", "owner/repo"])
        
        assert result.exit_code == 0
        mock_list_forks.assert_called_once()

    @patch('forklift.cli.load_config')
    def test_list_forks_no_token(self, mock_load_config):
        """Test list-forks command without GitHub token."""
        mock_config = self.create_mock_config()
        mock_config.github.token = None
        mock_load_config.return_value = mock_config
        
        result = self.runner.invoke(cli, ["list-forks", "owner/repo"])
        
        assert result.exit_code == 1
        assert "GitHub token not configured" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._list_forks_preview')
    def test_list_forks_verbose(self, mock_list_forks, mock_load_config):
        """Test list-forks command with verbose flag."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_list_forks.return_value = None
        
        result = self.runner.invoke(cli, ["--verbose", "list-forks", "owner/repo"])
        
        assert result.exit_code == 0
        assert "Fetching lightweight forks preview" in result.output
        mock_list_forks.assert_called_once()

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._list_forks_preview')
    def test_list_forks_keyboard_interrupt(self, mock_list_forks, mock_load_config):
        """Test list-forks command with keyboard interrupt."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_list_forks.side_effect = KeyboardInterrupt()
        
        result = self.runner.invoke(cli, ["list-forks", "owner/repo"])
        
        assert result.exit_code == 130
        assert "interrupted by user" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._list_forks_preview')
    def test_list_forks_cli_error(self, mock_list_forks, mock_load_config):
        """Test list-forks command with CLI error."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_list_forks.side_effect = CLIError("Failed to fetch forks preview")
        
        result = self.runner.invoke(cli, ["list-forks", "owner/repo"])
        
        assert result.exit_code == 1
        assert "Failed to fetch forks preview" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._list_forks_preview')
    def test_list_forks_unexpected_error(self, mock_list_forks, mock_load_config):
        """Test list-forks command with unexpected error."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_list_forks.side_effect = Exception("Unexpected error")
        
        result = self.runner.invoke(cli, ["list-forks", "owner/repo"])
        
        assert result.exit_code == 1
        assert "Unexpected error" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._list_forks_preview')
    def test_list_forks_debug_mode(self, mock_list_forks, mock_load_config):
        """Test list-forks command with debug mode on error."""
        mock_config = self.create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_list_forks.side_effect = Exception("Debug error")
        
        result = self.runner.invoke(cli, ["--debug", "list-forks", "owner/repo"])
        
        assert result.exit_code == 1
        # In debug mode, should show exception details

    @pytest.mark.asyncio
    @patch('forklift.cli.GitHubClient')
    @patch('forklift.cli.RepositoryDisplayService')
    async def test_list_forks_preview_success(self, mock_display_service_class, mock_github_client_class):
        """Test _list_forks_preview function success."""
        from forklift.cli import _list_forks_preview
        from forklift.config.settings import ForkliftConfig
        
        # Setup config
        config = ForkliftConfig()
        config.github.token = "test_token"
        
        # Setup mocks
        mock_client_instance = Mock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_github_client_class.return_value = mock_client_instance
        
        mock_display_service = Mock()
        mock_display_service.list_forks_preview = AsyncMock(return_value={
            "total_forks": 5,
            "forks": []
        })
        mock_display_service_class.return_value = mock_display_service
        
        # Call function
        await _list_forks_preview(config, "owner/repo", verbose=True)
        
        # Verify calls
        mock_github_client_class.assert_called_once_with(config.github)
        mock_display_service_class.assert_called_once()
        mock_display_service.list_forks_preview.assert_called_once_with("owner/repo")

    @pytest.mark.asyncio
    @patch('forklift.cli.GitHubClient')
    @patch('forklift.cli.RepositoryDisplayService')
    async def test_list_forks_preview_error(self, mock_display_service_class, mock_github_client_class):
        """Test _list_forks_preview function with error."""
        from forklift.cli import _list_forks_preview, CLIError
        from forklift.config.settings import ForkliftConfig
        
        # Setup config
        config = ForkliftConfig()
        config.github.token = "test_token"
        
        # Setup mocks
        mock_client_instance = Mock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_github_client_class.return_value = mock_client_instance
        
        mock_display_service = Mock()
        mock_display_service.list_forks_preview = AsyncMock(side_effect=Exception("Preview error"))
        mock_display_service_class.return_value = mock_display_service
        
        # Call function and expect error
        with pytest.raises(CLIError, match="Failed to display forks preview"):
            await _list_forks_preview(config, "owner/repo", verbose=False)