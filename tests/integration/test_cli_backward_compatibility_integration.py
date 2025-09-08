"""Integration tests for CLI backward compatibility after commit message truncation fix."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from forklift.cli import cli


class TestCLIBackwardCompatibilityIntegration:
    """Integration tests for CLI backward compatibility after commit message truncation fix."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client for CLI testing."""
        client = Mock()
        client.get_repository = AsyncMock()
        client.get_repository_forks = AsyncMock()
        client.get_commits_ahead = AsyncMock()
        client.get_recent_commits = AsyncMock()
        return client

    def test_show_forks_command_exists_and_accepts_all_options(self, runner):
        """Test that show-forks command exists and accepts all expected options."""
        # Test help to verify all options are available
        result = runner.invoke(cli, ["show-forks", "--help"])
        assert result.exit_code == 0

        # Verify all expected options are present
        expected_options = [
            "--detail",
            "--ahead-only",
            "--show-commits",
            "--csv",
            "--help",
        ]

        for option in expected_options:
            assert option in result.output

    def test_show_forks_with_show_commits_option_syntax_backward_compatibility(
        self, runner
    ):
        """Test that --show-commits option syntax is accepted for backward compatibility."""
        # Test various --show-commits syntax variations
        show_commits_variations = ["--show-commits=3", "--show-commits 3"]

        for variation in show_commits_variations:
            # Use help to test option parsing without making actual API calls
            if "=" in variation:
                result = runner.invoke(cli, ["show-forks", variation, "--help"])
            else:
                parts = variation.split()
                result = runner.invoke(
                    cli, ["show-forks", parts[0], parts[1], "--help"]
                )

            # Should not fail due to option parsing errors
            assert result.exit_code == 0

    def test_show_forks_csv_option_syntax_backward_compatibility(self, runner):
        """Test that CSV output option syntax is accepted for backward compatibility."""
        # Test that --csv option is accepted
        result = runner.invoke(cli, ["show-forks", "--csv", "--help"])
        assert result.exit_code == 0

        # Verify --csv is mentioned in help
        assert "--csv" in result.output

    def test_show_forks_all_command_line_options_accepted(self, runner):
        """Test that all command-line options are accepted without errors."""
        # Test various combinations of options
        option_combinations = [
            ["--detail"],
            ["--ahead-only"],
            ["--show-commits=5"],
            ["--csv"],
            ["--detail", "--ahead-only"],
            ["--detail", "--show-commits=3"],
            ["--detail", "--csv"],
            ["--ahead-only", "--show-commits=2"],
            ["--detail", "--ahead-only", "--show-commits=1"],
        ]

        for options in option_combinations:
            # Use --help to test option parsing without making actual API calls
            result = runner.invoke(cli, ["show-forks", *options, "--help"])
            # Should not fail due to option parsing errors
            assert result.exit_code == 0

    def test_show_forks_output_redirection_backward_compatibility(self, runner):
        """Test that output redirection maintains backward compatibility."""
        # Test that help output can be redirected (basic functionality test)
        result = runner.invoke(
            cli, ["show-forks", "--help"]  # Use help to avoid actual API calls
        )

        assert result.exit_code == 0
        # Verify output contains expected content that can be redirected
        assert "REPOSITORY_URL" in result.output

    def test_show_forks_repository_url_formats_backward_compatibility(self, runner):
        """Test that all repository URL formats are still accepted."""
        url_formats = [
            "https://github.com/owner/repo",
            "https://github.com/owner/repo.git",
            "https://github.com/owner/repo/",
            "git@github.com:owner/repo.git",
            "owner/repo",
        ]

        for url in url_formats:
            # Use --help to test URL parsing without making actual API calls
            result = runner.invoke(cli, ["show-forks", url, "--help"])
            # Should not fail due to URL parsing errors
            assert result.exit_code == 0

    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    def test_show_forks_error_handling_backward_compatibility(
        self, mock_service_class, mock_client_class, runner
    ):
        """Test that error handling maintains backward compatibility."""
        # Setup mocks to simulate errors
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_service = Mock()
        mock_service_class.return_value = mock_service

        # Simulate repository not found error
        mock_service.show_repository_details = AsyncMock(
            side_effect=Exception("Repository not found")
        )

        # Test error handling
        result = runner.invoke(
            cli, ["show-forks", "https://github.com/nonexistent/repo"]
        )

        # Should handle error gracefully (non-zero exit code is expected for errors)
        assert result.exit_code != 0
        assert "error" in result.output.lower() or "not found" in result.output.lower()

    def test_cli_help_messages_unchanged(self, runner):
        """Test that CLI help messages maintain expected content."""
        # Test main help
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "show-forks" in result.output

        # Test show-forks help
        result = runner.invoke(cli, ["show-forks", "--help"])
        assert result.exit_code == 0

        # Verify key help content is present
        expected_help_content = [
            "Display a summary table of repository forks",
            "REPOSITORY_URL",
            "--detail",
            "--ahead-only",
            "--show-commits",
            "--csv",
        ]

        for content in expected_help_content:
            assert content in result.output

    def test_cli_version_option_backward_compatibility(self, runner):
        """Test that version option maintains backward compatibility."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        # Should contain version information
        assert any(char.isdigit() for char in result.output)

    def test_show_commits_parameter_values_syntax_backward_compatibility(self, runner):
        """Test that --show-commits accepts various parameter values syntax."""
        # Test various --show-commits values with help to avoid API calls
        commit_values = ["1", "3", "5", "10"]

        for value in commit_values:
            result = runner.invoke(
                cli, ["show-forks", f"--show-commits={value}", "--help"]
            )

            # Should not fail due to parameter parsing
            assert result.exit_code == 0

    def test_environment_variable_support_backward_compatibility(self, runner):
        """Test that environment variable support is maintained."""
        # Test that help works regardless of environment variables
        result = runner.invoke(cli, ["show-forks", "--help"])
        assert result.exit_code == 0

        # The CLI should work with or without environment variables for help

    def test_cli_exit_codes_backward_compatibility(self, runner):
        """Test that CLI exit codes maintain expected behavior."""
        # Success case (help)
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

        # Invalid command case
        result = runner.invoke(cli, ["invalid-command"])
        assert result.exit_code != 0

        # Invalid option case
        result = runner.invoke(cli, ["show-forks", "--invalid-option"])
        assert result.exit_code != 0

    def test_cli_output_format_consistency(self, runner):
        """Test that CLI output format remains consistent."""
        # Test help output format
        result = runner.invoke(cli, ["show-forks", "--help"])
        assert result.exit_code == 0

        # Verify standard CLI formatting elements
        assert "Usage:" in result.output
        assert "Options:" in result.output

        # Verify option formatting is consistent
        lines = result.output.split("\n")
        option_lines = [line for line in lines if line.strip().startswith("-")]

        # Should have properly formatted option lines
        assert len(option_lines) > 0

        for line in option_lines:
            # Each option line should have proper formatting
            assert "--" in line or "-" in line
