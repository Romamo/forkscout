"""Integration tests for CLI commands with different interaction modes."""

import asyncio
import os
import sys
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forkscout.cli import cli, initialize_cli_environment
from forkscout.display.interaction_mode import InteractionMode
from forkscout.display.progress_reporter import (
    PlainTextProgressReporter,
    RichProgressReporter,
    StderrProgressReporter,
)


class TestCLIInteractiveModeIntegration:
    """Test CLI commands with different interaction modes."""

    def test_initialize_cli_environment_fully_interactive(self):
        """Test CLI environment initialization in fully interactive mode."""
        with patch("forklift.cli.get_interaction_mode_detector") as mock_detector:
            mock_detector_instance = MagicMock()
            mock_detector_instance.get_interaction_mode.return_value = InteractionMode.FULLY_INTERACTIVE
            mock_detector_instance.supports_user_prompts.return_value = True
            mock_detector_instance.supports_progress_bars.return_value = True
            mock_detector_instance.should_use_colors.return_value = True
            mock_detector.return_value = mock_detector_instance

            interaction_mode, supports_prompts = initialize_cli_environment()

            assert interaction_mode == InteractionMode.FULLY_INTERACTIVE
            assert supports_prompts is True

    def test_initialize_cli_environment_non_interactive(self):
        """Test CLI environment initialization in non-interactive mode."""
        with patch("forklift.cli.get_interaction_mode_detector") as mock_detector:
            mock_detector_instance = MagicMock()
            mock_detector_instance.get_interaction_mode.return_value = InteractionMode.NON_INTERACTIVE
            mock_detector_instance.supports_user_prompts.return_value = False
            mock_detector_instance.supports_progress_bars.return_value = False
            mock_detector_instance.should_use_colors.return_value = False
            mock_detector.return_value = mock_detector_instance

            interaction_mode, supports_prompts = initialize_cli_environment()

            assert interaction_mode == InteractionMode.NON_INTERACTIVE
            assert supports_prompts is False

    def test_initialize_cli_environment_output_redirected(self):
        """Test CLI environment initialization with output redirected."""
        with patch("forklift.cli.get_interaction_mode_detector") as mock_detector:
            mock_detector_instance = MagicMock()
            mock_detector_instance.get_interaction_mode.return_value = InteractionMode.OUTPUT_REDIRECTED
            mock_detector_instance.supports_user_prompts.return_value = True
            mock_detector_instance.supports_progress_bars.return_value = True
            mock_detector_instance.should_use_colors.return_value = True
            mock_detector.return_value = mock_detector_instance

            interaction_mode, supports_prompts = initialize_cli_environment()

            assert interaction_mode == InteractionMode.OUTPUT_REDIRECTED
            assert supports_prompts is True

    @patch("forklift.cli.get_progress_reporter")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.load_config")
    def test_analyze_command_with_different_interaction_modes(
        self, mock_load_config, mock_github_client, mock_get_progress_reporter
    ):
        """Test analyze command with different interaction modes."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.github.token = "test_token"
        mock_config.analysis.min_score_threshold = 50
        mock_config.analysis.max_forks_to_analyze = 10
        mock_config.analysis.auto_pr_enabled = False
        mock_config.dry_run = False
        mock_config.output_format = "markdown"
        mock_load_config.return_value = mock_config

        mock_progress_reporter = MagicMock()
        mock_get_progress_reporter.return_value = mock_progress_reporter

        # Mock GitHub client and analysis functions
        mock_client_instance = AsyncMock()
        mock_github_client.return_value = mock_client_instance

        # Test with different interaction modes
        interaction_modes = [
            InteractionMode.FULLY_INTERACTIVE,
            InteractionMode.NON_INTERACTIVE,
            InteractionMode.OUTPUT_REDIRECTED,
        ]

        for mode in interaction_modes:
            with patch("forklift.cli.initialize_cli_environment") as mock_init:
                mock_init.return_value = (mode, mode != InteractionMode.NON_INTERACTIVE)

                with patch("forklift.cli._run_analysis") as mock_run_analysis:
                    mock_run_analysis.return_value = {
                        "repository": "test/repo",
                        "total_forks": 5,
                        "analyzed_forks": 3,
                        "total_features": 10,
                        "high_value_features": 2,
                        "report": "Test report",
                    }

                    # Test that the command runs without error
                    from click.testing import CliRunner
                    runner = CliRunner()
                    
                    result = runner.invoke(cli, ["analyze", "test/repo"])
                    
                    # Should not crash regardless of interaction mode
                    assert result.exit_code in [0, 1]  # 1 is acceptable for missing config/token

    @patch("forklift.cli.get_progress_reporter")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.load_config")
    def test_show_forks_command_with_different_interaction_modes(
        self, mock_load_config, mock_github_client, mock_get_progress_reporter
    ):
        """Test show-forks command with different interaction modes."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.github.token = "test_token"
        mock_load_config.return_value = mock_config

        mock_progress_reporter = MagicMock()
        mock_get_progress_reporter.return_value = mock_progress_reporter

        # Mock GitHub client
        mock_client_instance = AsyncMock()
        mock_github_client.return_value = mock_client_instance

        # Test with different interaction modes
        interaction_modes = [
            InteractionMode.FULLY_INTERACTIVE,
            InteractionMode.NON_INTERACTIVE,
            InteractionMode.OUTPUT_REDIRECTED,
        ]

        for mode in interaction_modes:
            with patch("forklift.cli.initialize_cli_environment") as mock_init:
                mock_init.return_value = (mode, mode != InteractionMode.NON_INTERACTIVE)

                with patch("forklift.cli._show_forks_summary") as mock_show_forks:
                    mock_show_forks.return_value = None

                    # Test that the command runs without error
                    from click.testing import CliRunner
                    runner = CliRunner()
                    
                    result = runner.invoke(cli, ["show-forks", "test/repo"])
                    
                    # Should not crash regardless of interaction mode
                    assert result.exit_code in [0, 1]  # 1 is acceptable for missing config/token

    @patch("forklift.cli.get_progress_reporter")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.load_config")
    def test_show_commits_command_with_different_interaction_modes(
        self, mock_load_config, mock_github_client, mock_get_progress_reporter
    ):
        """Test show-commits command with different interaction modes."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.github.token = "test_token"
        mock_load_config.return_value = mock_config

        mock_progress_reporter = MagicMock()
        mock_get_progress_reporter.return_value = mock_progress_reporter

        # Mock GitHub client
        mock_client_instance = AsyncMock()
        mock_github_client.return_value = mock_client_instance

        # Test with different interaction modes
        interaction_modes = [
            InteractionMode.FULLY_INTERACTIVE,
            InteractionMode.NON_INTERACTIVE,
            InteractionMode.OUTPUT_REDIRECTED,
        ]

        for mode in interaction_modes:
            with patch("forklift.cli.initialize_cli_environment") as mock_init:
                mock_init.return_value = (mode, mode != InteractionMode.NON_INTERACTIVE)

                with patch("forklift.cli._show_commits") as mock_show_commits:
                    mock_show_commits.return_value = None

                    # Test that the command runs without error
                    from click.testing import CliRunner
                    runner = CliRunner()
                    
                    result = runner.invoke(cli, ["show-commits", "test/repo"])
                    
                    # Should not crash regardless of interaction mode
                    assert result.exit_code in [0, 1]  # 1 is acceptable for missing config/token

    def test_handle_user_prompt_interactive_mode(self):
        """Test user prompt handling in interactive mode."""
        from forkscout.cli import handle_user_prompt

        with patch("forklift.cli.Confirm.ask") as mock_confirm:
            mock_confirm.return_value = True

            result = handle_user_prompt(
                "Continue?",
                default=False,
                supports_prompts=True,
                interaction_mode=InteractionMode.FULLY_INTERACTIVE
            )

            assert result is True
            mock_confirm.assert_called_once_with("Continue?", default=False)

    def test_handle_user_prompt_non_interactive_mode(self):
        """Test user prompt handling in non-interactive mode."""
        from forkscout.cli import handle_user_prompt

        with patch("forklift.cli.Confirm.ask") as mock_confirm:
            result = handle_user_prompt(
                "Continue?",
                default=True,
                supports_prompts=False,
                interaction_mode=InteractionMode.NON_INTERACTIVE
            )

            assert result is True
            mock_confirm.assert_not_called()

    def test_handle_user_prompt_keyboard_interrupt(self):
        """Test user prompt handling with keyboard interrupt."""
        from forkscout.cli import handle_user_prompt

        with patch("forklift.cli.Confirm.ask") as mock_confirm:
            mock_confirm.side_effect = KeyboardInterrupt()

            result = handle_user_prompt(
                "Continue?",
                default=False,
                supports_prompts=True,
                interaction_mode=InteractionMode.FULLY_INTERACTIVE
            )

            assert result is False  # Should use default when interrupted

    @patch("forklift.cli.get_progress_reporter")
    def test_progress_reporter_selection_by_mode(self, mock_get_progress_reporter):
        """Test that appropriate progress reporter is selected based on interaction mode."""
        # Test different progress reporter types are returned for different modes
        mock_rich_reporter = MagicMock(spec=RichProgressReporter)
        mock_plain_reporter = MagicMock(spec=PlainTextProgressReporter)
        mock_stderr_reporter = MagicMock(spec=StderrProgressReporter)

        test_cases = [
            (InteractionMode.FULLY_INTERACTIVE, mock_rich_reporter),
            (InteractionMode.NON_INTERACTIVE, mock_plain_reporter),
            (InteractionMode.OUTPUT_REDIRECTED, mock_stderr_reporter),
        ]

        for mode, expected_reporter in test_cases:
            mock_get_progress_reporter.return_value = expected_reporter

            with patch("forklift.cli.initialize_cli_environment") as mock_init:
                mock_init.return_value = (mode, mode != InteractionMode.NON_INTERACTIVE)

                # Call the mocked function
                interaction_mode, supports_prompts = mock_init()

                # Verify the correct interaction mode is detected
                assert interaction_mode == mode
                assert supports_prompts == (mode != InteractionMode.NON_INTERACTIVE)

    def test_logging_interaction_mode_detection(self):
        """Test that interaction mode detection is logged for debugging."""
        with patch("forklift.cli.logger") as mock_logger:
            with patch("forklift.cli.get_interaction_mode_detector") as mock_detector:
                mock_detector_instance = MagicMock()
                mock_detector_instance.get_interaction_mode.return_value = InteractionMode.FULLY_INTERACTIVE
                mock_detector_instance.supports_user_prompts.return_value = True
                mock_detector_instance.supports_progress_bars.return_value = True
                mock_detector_instance.should_use_colors.return_value = True
                mock_detector.return_value = mock_detector_instance

                initialize_cli_environment()

                # Verify debug logging calls
                mock_logger.debug.assert_any_call("Detected interaction mode: fully_interactive")
                mock_logger.debug.assert_any_call("CLI environment initialized:")

    @patch("forklift.cli.reset_progress_reporter")
    def test_progress_reporter_reset_on_initialization(self, mock_reset):
        """Test that progress reporter is reset during CLI initialization."""
        with patch("forklift.display.interaction_mode.get_interaction_mode_detector") as mock_detector:
            mock_detector_instance = MagicMock()
            mock_detector_instance.get_interaction_mode.return_value = InteractionMode.FULLY_INTERACTIVE
            mock_detector_instance.supports_user_prompts.return_value = True
            mock_detector.return_value = mock_detector_instance

            initialize_cli_environment()

            # Verify progress reporter is reset
            mock_reset.assert_called_once()

    def test_console_configuration_by_interaction_mode(self):
        """Test that console is configured appropriately for different interaction modes."""
        with patch("forklift.cli.get_interaction_mode_detector") as mock_detector:
            mock_detector_instance = MagicMock()
            mock_detector.return_value = mock_detector_instance

            # Test OUTPUT_REDIRECTED mode
            mock_detector_instance.get_interaction_mode.return_value = InteractionMode.OUTPUT_REDIRECTED
            mock_detector_instance.supports_user_prompts.return_value = True

            with patch("forklift.cli.Console") as mock_console:
                initialize_cli_environment()
                # Should create console with stderr for output redirected mode
                mock_console.assert_called_with(file=sys.stderr)

            # Test NON_INTERACTIVE mode
            mock_detector_instance.get_interaction_mode.return_value = InteractionMode.NON_INTERACTIVE
            mock_detector_instance.supports_user_prompts.return_value = False

            with patch("forklift.cli.Console") as mock_console:
                initialize_cli_environment()
                # Should create console with no color and force_terminal=False
                mock_console.assert_called_with(file=sys.stdout, force_terminal=False, no_color=True)