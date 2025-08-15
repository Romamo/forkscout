"""Integration tests for CLI workflows."""

import json
import tempfile
import yaml
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from forklift.cli import cli
from forklift.config.settings import ForkliftConfig


class TestCLIIntegration:
    """Integration tests for complete CLI workflows."""

    def setup_method(self):
        """Setup test fixtures."""
        self.runner = CliRunner()

    def test_complete_analyze_workflow_with_config_file(self):
        """Test complete analyze workflow using configuration file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create configuration file
            config_file = temp_path / "forklift.yaml"
            config_data = {
                "github": {
                    "token": "ghp_1234567890abcdef1234567890abcdef12345678"  # Valid GitHub token format
                },
                "analysis": {
                    "min_score_threshold": 75,
                    "max_forks_to_analyze": 50,
                    "auto_pr_enabled": False
                },
                "logging": {
                    "level": "INFO",
                    "console_enabled": True,
                    "file_enabled": False
                }
            }
            
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            
            # Create output file path
            output_file = temp_path / "analysis_report.md"
            
            # Mock the analysis components
            with patch('forklift.cli.GitHubClient') as mock_github_client, \
                 patch('forklift.cli.ForkDiscoveryService') as mock_fork_discovery, \
                 patch('forklift.cli.FeatureRankingEngine') as mock_ranking_engine:
                
                # Setup mocks
                mock_client_instance = Mock()
                mock_github_client.return_value = mock_client_instance
                
                mock_discovery_instance = Mock()
                mock_discovery_instance.discover_forks = AsyncMock(return_value=[
                    Mock(full_name="user1/test-repo"),
                    Mock(full_name="user2/test-repo"),
                    Mock(full_name="user3/test-repo")
                ])
                mock_fork_discovery.return_value = mock_discovery_instance
                
                mock_ranking_instance = Mock()
                mock_ranking_engine.return_value = mock_ranking_instance
                
                # Run the analyze command
                result = self.runner.invoke(cli, [
                    "--config", str(config_file),
                    "--verbose",
                    "analyze", "owner/test-repo",
                    "--output", str(output_file),
                    "--format", "markdown",
                    "--min-score", "80"  # Override config value
                ])
                
                # Verify command succeeded
                assert result.exit_code == 0, f"Command failed with output: {result.output}"
                
                # Verify output file was created
                assert output_file.exists()
                
                # Verify report content
                report_content = output_file.read_text()
                assert "# Fork Analysis Report for owner/test-repo" in report_content
                assert "Total Forks Found:** 3" in report_content
                
                # Verify services were called correctly
                mock_github_client.assert_called_once()
                mock_fork_discovery.assert_called_once()
                mock_ranking_engine.assert_called_once()
                
                # Verify discovery was called with correct URL
                mock_discovery_instance.discover_forks.assert_called_once_with(
                    "https://github.com/owner/test-repo"
                )

    def test_configure_and_analyze_workflow(self):
        """Test configuration followed by analysis workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_file = temp_path / "test_config.yaml"
            
            # Step 1: Configure Forklift
            result = self.runner.invoke(cli, [
                "configure",
                "--github-token", "ghp_abcdef1234567890abcdef1234567890abcdef12",
                "--min-score", "85",
                "--max-forks", "25",
                "--output-format", "json",
                "--cache-duration", "12",
                "--save", str(config_file)
            ])
            
            assert result.exit_code == 0
            assert config_file.exists()
            assert "Configuration saved to:" in result.output
            
            # Verify configuration file content
            with open(config_file) as f:
                saved_config = yaml.safe_load(f)
            
            assert saved_config["github"]["token"] == "ghp_abcdef1234567890abcdef1234567890abcdef12"
            assert saved_config["analysis"]["min_score_threshold"] == 85
            assert saved_config["analysis"]["max_forks_to_analyze"] == 25
            assert saved_config["output_format"] == "json"
            assert saved_config["cache"]["duration_hours"] == 12
            
            # Step 2: Use the configuration for analysis
            output_file = temp_path / "analysis.json"
            
            with patch('forklift.cli.GitHubClient') as mock_github_client, \
                 patch('forklift.cli.ForkDiscoveryService') as mock_fork_discovery, \
                 patch('forklift.cli.FeatureRankingEngine') as mock_ranking_engine:
                
                # Setup mocks
                mock_client_instance = Mock()
                mock_github_client.return_value = mock_client_instance
                
                mock_discovery_instance = Mock()
                mock_discovery_instance.discover_forks = AsyncMock(return_value=[
                    Mock(full_name="fork1/repo"),
                    Mock(full_name="fork2/repo")
                ])
                mock_fork_discovery.return_value = mock_discovery_instance
                
                mock_ranking_instance = Mock()
                mock_ranking_engine.return_value = mock_ranking_instance
                
                # Run analysis with saved configuration
                result = self.runner.invoke(cli, [
                    "--config", str(config_file),
                    "analyze", "original/repo",
                    "--output", str(output_file)
                ])
                
                assert result.exit_code == 0
                assert output_file.exists()

    def test_schedule_configuration_workflow(self):
        """Test schedule configuration workflow."""
        # Test cron-based scheduling (without config-file to avoid path issues)
        result = self.runner.invoke(cli, [
            "schedule", "owner/repo",
            "--cron", "0 2 * * 1"  # Every Monday at 2 AM
        ])
        
        assert result.exit_code == 0
        assert "Schedule Configuration" in result.output
        assert "owner/repo" in result.output
        assert "0 2 * * 1" in result.output
        
        # Test interval-based scheduling
        result = self.runner.invoke(cli, [
            "schedule", "owner/repo",
            "--interval", "168"  # Weekly (168 hours)
        ])
        
        assert result.exit_code == 0
        assert "every 168 hours" in result.output

    def test_error_handling_workflow(self):
        """Test error handling in various workflow scenarios."""
        
        # Test invalid repository URL
        result = self.runner.invoke(cli, [
            "analyze", "not-a-valid-url"
        ])
        
        assert result.exit_code == 1
        assert "Invalid GitHub repository URL" in result.output
        
        # Test missing GitHub token
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "no_token.yaml"
            config_data = {
                "github": {"token": None},
                "analysis": {"min_score_threshold": 70}
            }
            
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            
            with patch('forklift.cli._run_analysis') as mock_run_analysis:
                from forklift.cli import CLIError
                mock_run_analysis.side_effect = CLIError("GitHub token not configured")
                
                result = self.runner.invoke(cli, [
                    "--config", str(config_file),
                    "analyze", "owner/repo"
                ])
                
                assert result.exit_code == 1
                assert "GitHub token not configured" in result.output

    def test_dry_run_workflow(self):
        """Test dry run functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "dry_run_report.md"
            
            with patch('forklift.cli.GitHubClient') as mock_github_client, \
                 patch('forklift.cli.ForkDiscoveryService') as mock_fork_discovery, \
                 patch('forklift.cli.FeatureRankingEngine') as mock_ranking_engine:
                
                # Setup mocks
                mock_client_instance = Mock()
                mock_github_client.return_value = mock_client_instance
                
                mock_discovery_instance = Mock()
                mock_discovery_instance.discover_forks = AsyncMock(return_value=[
                    Mock(full_name="test/fork")
                ])
                mock_fork_discovery.return_value = mock_discovery_instance
                
                mock_ranking_instance = Mock()
                mock_ranking_engine.return_value = mock_ranking_instance
                
                # Run with dry-run flag
                result = self.runner.invoke(cli, [
                    "analyze", "owner/repo",
                    "--output", str(output_file),
                    "--dry-run"
                ])
                
                assert result.exit_code == 0
                # In dry run mode, output file should not be created
                assert not output_file.exists()

    def test_verbose_and_debug_output(self):
        """Test verbose and debug output modes."""
        
        # Test verbose mode
        with patch('forklift.cli._run_analysis') as mock_run_analysis:
            mock_run_analysis.return_value = {
                "repository": "owner/repo",
                "total_forks": 5,
                "analyzed_forks": 3,
                "total_features": 2,
                "high_value_features": 1,
                "report": "# Test Report"
            }
            
            result = self.runner.invoke(cli, [
                "--verbose",
                "analyze", "owner/repo"
            ])
            
            assert result.exit_code == 0
            # Verbose mode should show additional information
            assert "Analyzing repository: owner/repo" in result.output
        
        # Test debug mode
        with patch('forklift.cli._run_analysis') as mock_run_analysis:
            mock_run_analysis.return_value = {
                "repository": "owner/repo",
                "total_forks": 5,
                "analyzed_forks": 3,
                "total_features": 2,
                "high_value_features": 1,
                "report": "# Test Report"
            }
            
            result = self.runner.invoke(cli, [
                "--debug",
                "analyze", "owner/repo"
            ])
            
            assert result.exit_code == 0

    def test_different_output_formats(self):
        """Test different output format options."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            formats_to_test = ["markdown", "json", "yaml"]
            
            for output_format in formats_to_test:
                output_file = temp_path / f"report.{output_format}"
                
                with patch('forklift.cli.GitHubClient') as mock_github_client, \
                     patch('forklift.cli.ForkDiscoveryService') as mock_fork_discovery, \
                     patch('forklift.cli.FeatureRankingEngine') as mock_ranking_engine:
                    
                    # Setup mocks
                    mock_client_instance = Mock()
                    mock_github_client.return_value = mock_client_instance
                    
                    mock_discovery_instance = Mock()
                    mock_discovery_instance.discover_forks = AsyncMock(return_value=[])
                    mock_fork_discovery.return_value = mock_discovery_instance
                    
                    mock_ranking_instance = Mock()
                    mock_ranking_engine.return_value = mock_ranking_instance
                    
                    result = self.runner.invoke(cli, [
                        "analyze", "owner/repo",
                        "--format", output_format,
                        "--output", str(output_file)
                    ])
                    
                    assert result.exit_code == 0, f"Failed for format {output_format}: {result.output}"
                    assert output_file.exists(), f"Output file not created for format {output_format}"

    def test_configuration_override_precedence(self):
        """Test that CLI options override configuration file values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "base_config.yaml"
            
            # Create base configuration
            config_data = {
                "github": {"token": "ghp_1111111111111111111111111111111111111111"},
                "analysis": {
                    "min_score_threshold": 60,
                    "max_forks_to_analyze": 200,
                    "auto_pr_enabled": False
                },
                "output_format": "yaml"
            }
            
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            
            with patch('forklift.cli._run_analysis') as mock_run_analysis:
                mock_run_analysis.return_value = {
                    "repository": "owner/repo",
                    "total_forks": 1,
                    "analyzed_forks": 1,
                    "total_features": 1,
                    "high_value_features": 1,
                    "report": "# Test"
                }
                
                result = self.runner.invoke(cli, [
                    "--config", str(config_file),
                    "analyze", "owner/repo",
                    "--format", "json",  # Override config yaml format
                    "--min-score", "90",  # Override config 60
                    "--max-forks", "10",  # Override config 200
                    "--auto-pr"  # Override config False
                ])
                
                assert result.exit_code == 0
                
                # Verify that _run_analysis was called with overridden values
                # The config object passed to _run_analysis should have CLI overrides
                call_args = mock_run_analysis.call_args[0]
                config_used = call_args[0]  # First argument is config
                
                assert config_used.analysis.min_score_threshold == 90
                assert config_used.analysis.max_forks_to_analyze == 10
                assert config_used.analysis.auto_pr_enabled is True
                assert config_used.output_format == "json"

    def test_help_and_version_commands(self):
        """Test help and version commands work correctly."""
        
        # Test main help
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Forklift - GitHub repository fork analysis tool" in result.output
        assert "analyze" in result.output
        assert "configure" in result.output
        assert "schedule" in result.output
        
        # Test version
        result = self.runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
        
        # Test subcommand help
        for command in ["analyze", "configure", "schedule"]:
            result = self.runner.invoke(cli, [command, "--help"])
            assert result.exit_code == 0
            assert "Usage:" in result.output

    def test_edge_cases_and_boundary_conditions(self):
        """Test edge cases and boundary conditions."""
        
        # Test minimum and maximum values for numeric options
        result = self.runner.invoke(cli, [
            "analyze", "owner/repo",
            "--min-score", "0"  # Minimum value
        ])
        # Should not fail due to validation
        assert "Invalid value" not in result.output
        
        result = self.runner.invoke(cli, [
            "analyze", "owner/repo",
            "--min-score", "100"  # Maximum value
        ])
        assert "Invalid value" not in result.output
        
        result = self.runner.invoke(cli, [
            "analyze", "owner/repo",
            "--max-forks", "1"  # Minimum value
        ])
        assert "Invalid value" not in result.output
        
        # Test invalid values
        result = self.runner.invoke(cli, [
            "analyze", "owner/repo",
            "--min-score", "101"  # Above maximum
        ])
        assert result.exit_code != 0
        
        result = self.runner.invoke(cli, [
            "analyze", "owner/repo",
            "--min-score", "-1"  # Below minimum
        ])
        assert result.exit_code != 0