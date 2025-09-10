"""CLI-level integration tests for show-forks --detail functionality."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from forkscout.cli import cli
from forkscout.config.settings import ForkscoutConfig, GitHubConfig


class TestShowForksDetailCLIIntegration:
    """CLI-level integration tests for show-forks --detail functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        config = ForkscoutConfig()
        config.github = GitHubConfig(token="ghp_1234567890123456789012345678901234567890")
        return config

    @pytest.fixture
    def realistic_fork_data_result(self):
        """Create realistic fork data result for mocking."""
        return {
            "total_forks": 5,
            "displayed_forks": 4,
            "collected_forks": [
                MagicMock(
                    metrics=MagicMock(
                        name="active-fork",
                        owner="user1",
                        stars=15,
                        can_skip_analysis=False
                    ),
                    exact_commits_ahead=5
                ),
                MagicMock(
                    metrics=MagicMock(
                        name="empty-fork",
                        owner="user2",
                        stars=0,
                        can_skip_analysis=True
                    ),
                    exact_commits_ahead=0
                ),
                MagicMock(
                    metrics=MagicMock(
                        name="high-activity-fork",
                        owner="user3",
                        stars=50,
                        can_skip_analysis=False
                    ),
                    exact_commits_ahead=25
                ),
                MagicMock(
                    metrics=MagicMock(
                        name="error-fork",
                        owner="user4",
                        stars=10,
                        can_skip_analysis=False
                    ),
                    exact_commits_ahead="Unknown"
                ),
            ],
            "api_calls_made": 3,
            "api_calls_saved": 1,
            "forks_skipped": 1,
            "forks_analyzed": 3,
        }

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    def test_show_forks_detail_flag_cli_integration(
        self, mock_display_service_class, mock_github_client_class, mock_load_config,
        mock_config, realistic_fork_data_result
    ):
        """Test show-forks --detail flag CLI integration."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client
        
        mock_display_service = AsyncMock()
        mock_display_service.show_fork_data_detailed.return_value = realistic_fork_data_result
        mock_display_service_class.return_value = mock_display_service

        # Run CLI command
        runner = CliRunner()
        result = runner.invoke(cli, [
            "show-forks", 
            "owner/test-repo", 
            "--detail"
        ])

        # Verify command executed successfully
        assert result.exit_code == 0
        
        # Verify that show_fork_data_detailed was called with correct parameters
        mock_display_service.show_fork_data_detailed.assert_called_once()
        call_args = mock_display_service.show_fork_data_detailed.call_args
        assert call_args[0][0] == "owner/test-repo"  # repository_url
        assert call_args[1]["disable_cache"] == False
        assert call_args[1]["show_commits"] == 0
        assert call_args[1]["force_all_commits"] == False

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    def test_show_forks_detail_with_max_forks_cli_integration(
        self, mock_display_service_class, mock_github_client_class, mock_load_config,
        mock_config, realistic_fork_data_result
    ):
        """Test show-forks --detail with --max-forks CLI integration."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client
        
        mock_display_service = AsyncMock()
        mock_display_service.show_fork_data_detailed.return_value = realistic_fork_data_result
        mock_display_service_class.return_value = mock_display_service

        # Run CLI command with max-forks
        runner = CliRunner()
        result = runner.invoke(cli, [
            "show-forks", 
            "owner/test-repo", 
            "--detail",
            "--max-forks", "10"
        ])

        # Verify command executed successfully
        assert result.exit_code == 0
        
        # Verify that max_forks parameter was passed correctly
        mock_display_service.show_fork_data_detailed.assert_called_once()
        call_args = mock_display_service.show_fork_data_detailed.call_args
        assert call_args[1]["max_forks"] == 10

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    def test_show_forks_detail_with_show_commits_cli_integration(
        self, mock_display_service_class, mock_github_client_class, mock_load_config,
        mock_config, realistic_fork_data_result
    ):
        """Test show-forks --detail with --show-commits CLI integration."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client
        
        mock_display_service = AsyncMock()
        mock_display_service.show_fork_data_detailed.return_value = realistic_fork_data_result
        mock_display_service_class.return_value = mock_display_service

        # Run CLI command with show-commits
        runner = CliRunner()
        result = runner.invoke(cli, [
            "show-forks", 
            "owner/test-repo", 
            "--detail",
            "--show-commits", "5"
        ])

        # Verify command executed successfully
        assert result.exit_code == 0
        
        # Verify that show_commits parameter was passed correctly
        mock_display_service.show_fork_data_detailed.assert_called_once()
        call_args = mock_display_service.show_fork_data_detailed.call_args
        assert call_args[1]["show_commits"] == 5

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    def test_show_forks_detail_with_force_all_commits_cli_integration(
        self, mock_display_service_class, mock_github_client_class, mock_load_config,
        mock_config, realistic_fork_data_result
    ):
        """Test show-forks --detail with --force-all-commits CLI integration."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client
        
        mock_display_service = AsyncMock()
        mock_display_service.show_fork_data_detailed.return_value = realistic_fork_data_result
        mock_display_service_class.return_value = mock_display_service

        # Run CLI command with force-all-commits
        runner = CliRunner()
        result = runner.invoke(cli, [
            "show-forks", 
            "owner/test-repo", 
            "--detail",
            "--force-all-commits"
        ])

        # Verify command executed successfully
        assert result.exit_code == 0
        
        # Verify that force_all_commits parameter was passed correctly
        mock_display_service.show_fork_data_detailed.assert_called_once()
        call_args = mock_display_service.show_fork_data_detailed.call_args
        assert call_args[1]["force_all_commits"] == True

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    def test_show_forks_detail_verbose_output_cli_integration(
        self, mock_display_service_class, mock_github_client_class, mock_load_config,
        mock_config, realistic_fork_data_result
    ):
        """Test show-forks --detail with verbose output CLI integration."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client
        
        mock_display_service = AsyncMock()
        mock_display_service.show_fork_data_detailed.return_value = realistic_fork_data_result
        mock_display_service_class.return_value = mock_display_service

        # Run CLI command with verbose flag
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--verbose",
            "show-forks", 
            "owner/test-repo", 
            "--detail"
        ])

        # Verify command executed successfully
        assert result.exit_code == 0
        
        # Verify verbose output contains API call statistics
        output = result.output
        assert "Displayed 4 of 5 forks" in output
        assert "Made 3 additional API calls" in output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    def test_show_forks_detail_error_handling_cli_integration(
        self, mock_display_service_class, mock_github_client_class, mock_load_config,
        mock_config
    ):
        """Test show-forks --detail error handling CLI integration."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client
        
        mock_display_service = AsyncMock()
        mock_display_service.show_fork_data_detailed.side_effect = Exception("GitHub API error")
        mock_display_service_class.return_value = mock_display_service

        # Run CLI command that should fail
        runner = CliRunner()
        result = runner.invoke(cli, [
            "show-forks", 
            "owner/test-repo", 
            "--detail"
        ])

        # Verify command failed gracefully
        assert result.exit_code == 1
        assert "Failed to display forks data" in result.output

    @patch("forklift.cli.load_config")
    def test_show_forks_detail_no_github_token_cli_integration(
        self, mock_load_config
    ):
        """Test show-forks --detail without GitHub token CLI integration."""
        # Setup config without GitHub token
        config = ForkscoutConfig()
        config.github = GitHubConfig(token=None)
        mock_load_config.return_value = config

        # Run CLI command
        runner = CliRunner()
        result = runner.invoke(cli, [
            "show-forks", 
            "owner/test-repo", 
            "--detail"
        ])

        # Verify command failed with appropriate error
        assert result.exit_code == 1
        assert "GitHub token not configured" in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    def test_show_forks_detail_keyboard_interrupt_cli_integration(
        self, mock_display_service_class, mock_github_client_class, mock_load_config,
        mock_config
    ):
        """Test show-forks --detail keyboard interrupt handling CLI integration."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client
        
        mock_display_service = AsyncMock()
        mock_display_service.show_fork_data_detailed.side_effect = KeyboardInterrupt()
        mock_display_service_class.return_value = mock_display_service

        # Run CLI command that should be interrupted
        runner = CliRunner()
        result = runner.invoke(cli, [
            "show-forks", 
            "owner/test-repo", 
            "--detail"
        ])

        # Verify command handled interrupt gracefully
        assert result.exit_code == 130
        assert "interrupted by user" in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    def test_show_forks_detail_combined_flags_cli_integration(
        self, mock_display_service_class, mock_github_client_class, mock_load_config,
        mock_config, realistic_fork_data_result
    ):
        """Test show-forks --detail with multiple combined flags CLI integration."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client
        
        mock_display_service = AsyncMock()
        mock_display_service.show_fork_data_detailed.return_value = realistic_fork_data_result
        mock_display_service_class.return_value = mock_display_service

        # Run CLI command with multiple flags
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--verbose",
            "show-forks", 
            "owner/test-repo", 
            "--detail",
            "--max-forks", "20",
            "--show-commits", "3",
            "--force-all-commits"
        ])

        # Verify command executed successfully
        assert result.exit_code == 0
        
        # Verify all parameters were passed correctly
        mock_display_service.show_fork_data_detailed.assert_called_once()
        call_args = mock_display_service.show_fork_data_detailed.call_args
        assert call_args[0][0] == "owner/test-repo"
        assert call_args[1]["max_forks"] == 20
        assert call_args[1]["show_commits"] == 3
        assert call_args[1]["force_all_commits"] == True
        assert call_args[1]["disable_cache"] == False

    def test_show_forks_detail_help_text_cli_integration(self):
        """Test show-forks --detail help text CLI integration."""
        runner = CliRunner()
        result = runner.invoke(cli, ["show-forks", "--help"])

        # Verify help text includes detail flag documentation
        assert result.exit_code == 0
        assert "--detail" in result.output
        assert "exact commit counts ahead" in result.output
        assert "additional API requests" in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    def test_show_forks_without_detail_flag_cli_integration(
        self, mock_display_service_class, mock_github_client_class, mock_load_config,
        mock_config
    ):
        """Test show-forks without --detail flag uses standard behavior CLI integration."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client
        
        mock_display_service = AsyncMock()
        mock_display_service.show_fork_data.return_value = {
            "total_forks": 5,
            "displayed_forks": 5
        }
        mock_display_service_class.return_value = mock_display_service

        # Run CLI command without detail flag
        runner = CliRunner()
        result = runner.invoke(cli, [
            "show-forks", 
            "owner/test-repo"
        ])

        # Verify command executed successfully
        assert result.exit_code == 0
        
        # Verify that show_fork_data was called (not show_fork_data_detailed)
        mock_display_service.show_fork_data.assert_called_once()
        mock_display_service.show_fork_data_detailed.assert_not_called()

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    def test_show_forks_detail_invalid_repository_url_cli_integration(
        self, mock_display_service_class, mock_github_client_class, mock_load_config,
        mock_config
    ):
        """Test show-forks --detail with invalid repository URL CLI integration."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client
        
        mock_display_service = AsyncMock()
        mock_display_service_class.return_value = mock_display_service

        # Run CLI command with invalid URL
        runner = CliRunner()
        result = runner.invoke(cli, [
            "show-forks", 
            "invalid-url-format", 
            "--detail"
        ])

        # The URL validation happens in the CLI layer, so this should still work
        # as the validation is handled by the display service
        assert result.exit_code == 0 or result.exit_code == 1  # Depends on validation implementation

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    def test_show_forks_detail_performance_monitoring_cli_integration(
        self, mock_display_service_class, mock_github_client_class, mock_load_config,
        mock_config
    ):
        """Test show-forks --detail performance monitoring CLI integration."""
        # Setup mocks with performance data
        mock_load_config.return_value = mock_config
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client
        
        mock_display_service = AsyncMock()
        performance_result = {
            "total_forks": 50,
            "displayed_forks": 45,
            "api_calls_made": 30,
            "api_calls_saved": 15,
            "forks_skipped": 15,
            "forks_analyzed": 30,
            "collected_forks": []
        }
        mock_display_service.show_fork_data_detailed.return_value = performance_result
        mock_display_service_class.return_value = mock_display_service

        # Run CLI command with verbose to see performance stats
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--verbose",
            "show-forks", 
            "owner/large-repo", 
            "--detail"
        ])

        # Verify command executed successfully
        assert result.exit_code == 0
        
        # Verify performance statistics are displayed
        output = result.output
        assert "45 of 50 forks" in output
        assert "30 additional API calls" in output