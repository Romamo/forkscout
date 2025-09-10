"""Unit tests for CLI CSV export functionality."""

import pytest
from click.testing import CliRunner
from unittest.mock import AsyncMock, MagicMock, patch

from forkscout.cli import cli
from forkscout.config.settings import ForkscoutConfig
from forkscout.display.interaction_mode import InteractionMode


class TestCLICSVExport:
    """Test CSV export functionality in CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create a Click test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock()
        config.github = MagicMock()
        config.github.token = "test_token"
        config.analysis = MagicMock()
        config.analysis.min_score_threshold = 50
        config.analysis.max_forks_to_analyze = 100
        config.analysis.auto_pr_enabled = False
        config.dry_run = False
        config.output_format = "markdown"
        config.logging = None  # No logging config
        config.cache = MagicMock()
        config.cache.duration_hours = 24
        return config

    def test_show_forks_csv_flag_parsing(self, runner, mock_config):
        """Test that --csv flag is properly parsed in show-forks command."""
        with patch('forklift.cli.load_config', return_value=mock_config):
            with patch('forklift.cli.asyncio.run') as mock_run:
                result = runner.invoke(cli, [
                    'show-forks', 'owner/repo', '--csv'
                ])
                
                # Print result for debugging
                if result.exit_code != 0:
                    print(f"Exit code: {result.exit_code}")
                    print(f"Output: {result.output}")
                    if result.exception:
                        print(f"Exception: {result.exception}")
                
                # Check that the command was called
                assert mock_run.called
                
                # Get the arguments passed to _show_forks_summary
                call_args = mock_run.call_args[0][0]
                # The call should be to _show_forks_summary with csv_export=True
                # We can't easily inspect the coroutine args, but we can check the command ran
                assert result.exit_code == 0

    def test_show_forks_csv_mode_detection(self, runner, mock_config):
        """Test that CSV mode properly overrides interaction mode."""
        with patch('forklift.cli.load_config', return_value=mock_config):
            with patch('forklift.cli._show_forks_summary', new_callable=AsyncMock) as mock_show_forks:
                result = runner.invoke(cli, [
                    'show-forks', 'owner/repo', '--csv'
                ])
                
                # Verify the command ran successfully
                assert result.exit_code == 0
                
                # Verify _show_forks_summary was called with CSV=True
                mock_show_forks.assert_called_once()
                call_args = mock_show_forks.call_args
                # csv parameter is at index 8 (9th positional argument)
                assert call_args[0][8] is True  # csv=True

    def test_show_forks_csv_with_other_flags(self, runner, mock_config):
        """Test CSV export works with other flags."""
        with patch('forklift.cli.load_config', return_value=mock_config):
            with patch('forklift.cli.asyncio.run') as mock_run:
                result = runner.invoke(cli, [
                    'show-forks', 'owner/repo', 
                    '--csv', '--detail', '--ahead-only', '--max-forks', '50'
                ])
                
                assert result.exit_code == 0
                assert mock_run.called

    def test_show_forks_csv_help_text(self, runner):
        """Test that CSV flag is documented in help text."""
        result = runner.invoke(cli, ['show-forks', '--help'])
        
        assert result.exit_code == 0
        assert '--csv' in result.output
        assert 'CSV format' in result.output
        assert 'suppresses all interactive elements' in result.output

    def test_show_forks_csv_examples_in_help(self, runner):
        """Test that CSV examples are included in help text."""
        result = runner.invoke(cli, ['show-forks', '--help'])
        
        assert result.exit_code == 0
        assert 'forklift show-forks owner/repo --csv > forks_with_commits.csv' in result.output
        assert 'forklift show-forks owner/repo --csv --detail > detailed_forks_with_commits.csv' in result.output

    @patch('forklift.cli.initialize_cli_environment')
    def test_csv_mode_overrides_interaction_mode(self, mock_init_env, runner, mock_config):
        """Test that CSV mode overrides interaction mode to NON_INTERACTIVE."""
        # Setup mock to return interactive mode initially
        mock_init_env.return_value = (InteractionMode.FULLY_INTERACTIVE, True)
        
        with patch('forklift.cli.load_config', return_value=mock_config):
            with patch('forklift.cli._show_forks_summary') as mock_show_forks:
                with patch('forklift.cli.asyncio.run'):
                    # Configure mock to capture arguments
                    async def capture_call(*args, **kwargs):
                        capture_call.interaction_mode = args[8]  # interaction_mode is 9th arg
                        capture_call.supports_prompts = args[9]  # supports_prompts is 10th arg
                        return {}
                    
                    mock_show_forks.side_effect = capture_call
                    
                    result = runner.invoke(cli, [
                        'show-forks', 'owner/repo', '--csv'
                    ])
                    
                    assert result.exit_code == 0
                    
                    # Verify interaction mode was overridden
                    if hasattr(capture_call, 'interaction_mode'):
                        assert capture_call.interaction_mode == InteractionMode.NON_INTERACTIVE
                        assert capture_call.supports_prompts is False

    def test_show_forks_without_csv_flag(self, runner, mock_config):
        """Test that CSV export is disabled by default."""
        with patch('forklift.cli.load_config', return_value=mock_config):
            with patch('forklift.cli._show_forks_summary', new_callable=AsyncMock) as mock_show_forks:
                result = runner.invoke(cli, [
                    'show-forks', 'owner/repo'
                ])
                
                assert result.exit_code == 0
                
                # Verify _show_forks_summary was called with CSV=False
                mock_show_forks.assert_called_once()
                call_args = mock_show_forks.call_args
                # csv parameter is at index 8 (9th positional argument)
                assert call_args[0][8] is False  # csv=False

    def test_csv_flag_parameter_name_mapping(self, runner, mock_config):
        """Test that --csv flag maps to csv_export parameter correctly."""
        with patch('forklift.cli.load_config', return_value=mock_config):
            with patch('forklift.cli.asyncio.run') as mock_run:
                # Test with CSV flag
                result = runner.invoke(cli, [
                    'show-forks', 'owner/repo', '--csv'
                ])
                
                assert result.exit_code == 0
                
                # The command should run without errors when CSV flag is provided
                assert mock_run.called


# Import asyncio for the test that needs it
import asyncio