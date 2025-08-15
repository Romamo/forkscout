"""Unit tests for CLI interface."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from forklift.cli import cli, validate_repository_url, CLIError
from forklift.config.settings import ForkliftConfig


def create_mock_config():
    """Create a properly mocked ForkliftConfig for testing."""
    mock_config = Mock()
    mock_config.analysis = Mock()
    mock_config.github = Mock()
    mock_config.cache = Mock()
    mock_config.logging = Mock()
    
    # Set default values
    mock_config.analysis.min_score_threshold = 70
    mock_config.analysis.max_forks_to_analyze = 100
    mock_config.analysis.auto_pr_enabled = False
    mock_config.dry_run = False
    mock_config.output_format = "markdown"
    
    mock_config.github.token = "ghp_1234567890abcdef1234567890abcdef12345678"
    
    mock_config.cache.duration_hours = 24
    
    mock_config.logging.level = "INFO"
    mock_config.logging.console_enabled = True
    mock_config.logging.file_enabled = False
    mock_config.logging.format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    mock_config.save_to_file = Mock()
    
    return mock_config


class TestRepositoryURLValidation:
    """Test repository URL validation."""

    def test_validate_https_url(self):
        """Test validation of HTTPS GitHub URLs."""
        owner, repo = validate_repository_url("https://github.com/owner/repo")
        assert owner == "owner"
        assert repo == "repo"

    def test_validate_https_url_with_git_suffix(self):
        """Test validation of HTTPS URLs with .git suffix."""
        owner, repo = validate_repository_url("https://github.com/owner/repo.git")
        assert owner == "owner"
        assert repo == "repo"

    def test_validate_https_url_with_trailing_slash(self):
        """Test validation of HTTPS URLs with trailing slash."""
        owner, repo = validate_repository_url("https://github.com/owner/repo/")
        assert owner == "owner"
        assert repo == "repo"

    def test_validate_ssh_url(self):
        """Test validation of SSH GitHub URLs."""
        owner, repo = validate_repository_url("git@github.com:owner/repo.git")
        assert owner == "owner"
        assert repo == "repo"

    def test_validate_short_format(self):
        """Test validation of short owner/repo format."""
        owner, repo = validate_repository_url("owner/repo")
        assert owner == "owner"
        assert repo == "repo"

    def test_validate_invalid_url(self):
        """Test validation of invalid URLs."""
        with pytest.raises(CLIError, match="Invalid GitHub repository URL"):
            validate_repository_url("not-a-valid-url")

    def test_validate_empty_url(self):
        """Test validation of empty URL."""
        with pytest.raises(CLIError, match="Invalid GitHub repository URL"):
            validate_repository_url("")

    def test_validate_non_github_url(self):
        """Test validation of non-GitHub URLs."""
        with pytest.raises(CLIError, match="Invalid GitHub repository URL"):
            validate_repository_url("https://gitlab.com/owner/repo")


class TestCLICommands:
    """Test CLI command functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.runner = CliRunner()

    def test_cli_version(self):
        """Test CLI version display."""
        result = self.runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_cli_help(self):
        """Test CLI help display."""
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Forklift - GitHub repository fork analysis tool" in result.output
        assert "analyze" in result.output
        assert "configure" in result.output
        assert "schedule" in result.output

    @patch('forklift.cli.load_config')
    def test_cli_with_config_file(self, mock_load_config):
        """Test CLI with configuration file."""
        mock_config = Mock(spec=ForkliftConfig)
        mock_load_config.return_value = mock_config
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("github:\n  token: test_token\n")
            config_path = f.name
        
        try:
            result = self.runner.invoke(cli, ["--config", config_path, "--help"])
            assert result.exit_code == 0
            # Note: load_config is called during CLI initialization, not during help display
            # The help command exits early, so we just check it doesn't crash
        finally:
            Path(config_path).unlink()

    @patch('forklift.cli.load_config')
    def test_cli_with_invalid_config_file(self, mock_load_config):
        """Test CLI with invalid configuration file."""
        # Create a temporary file that exists but has invalid content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content:")
            config_path = f.name
        
        mock_load_config.side_effect = Exception("Invalid config")
        
        try:
            result = self.runner.invoke(cli, ["--config", config_path, "analyze", "owner/repo"])
            assert result.exit_code != 0  # Any non-zero exit code indicates error
            assert "Error loading configuration" in result.output
        finally:
            Path(config_path).unlink()


class TestAnalyzeCommand:
    """Test analyze command functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.runner = CliRunner()

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._run_analysis')
    def test_analyze_basic(self, mock_run_analysis, mock_load_config):
        """Test basic analyze command."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_run_analysis.return_value = {
            "repository": "owner/repo",
            "total_forks": 10,
            "analyzed_forks": 8,
            "total_features": 5,
            "high_value_features": 2,
            "report": "# Test Report"
        }
        
        result = self.runner.invoke(cli, ["analyze", "owner/repo"])
        
        assert result.exit_code == 0
        assert "Analysis complete" in result.output
        assert "Found 2 high-value features" in result.output
        mock_run_analysis.assert_called_once()

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._run_analysis')
    def test_analyze_with_output_file(self, mock_run_analysis, mock_load_config):
        """Test analyze command with output file."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_run_analysis.return_value = {
            "repository": "owner/repo",
            "total_forks": 10,
            "analyzed_forks": 8,
            "total_features": 5,
            "high_value_features": 2,
            "report": "# Test Report"
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report.md"
            
            result = self.runner.invoke(cli, [
                "analyze", "owner/repo", 
                "--output", str(output_path)
            ])
            
            assert result.exit_code == 0
            assert output_path.exists()
            assert output_path.read_text() == "# Test Report"
            assert "Report saved to:" in result.output
            assert str(output_path) in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._run_analysis')
    def test_analyze_with_options(self, mock_run_analysis, mock_load_config):
        """Test analyze command with various options."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_run_analysis.return_value = {
            "repository": "owner/repo",
            "total_forks": 10,
            "analyzed_forks": 8,
            "total_features": 5,
            "high_value_features": 2,
            "report": "# Test Report"
        }
        
        result = self.runner.invoke(cli, [
            "analyze", "owner/repo",
            "--format", "json",
            "--auto-pr",
            "--min-score", "80",
            "--max-forks", "50",
            "--dry-run"
        ])
        
        assert result.exit_code == 0
        
        # Verify config was updated with CLI options
        assert mock_config.analysis.min_score_threshold == 80
        assert mock_config.analysis.max_forks_to_analyze == 50
        assert mock_config.analysis.auto_pr_enabled is True
        assert mock_config.dry_run is True
        assert mock_config.output_format == "json"

    @patch('forklift.cli.load_config')
    def test_analyze_invalid_repository_url(self, mock_load_config):
        """Test analyze command with invalid repository URL."""
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        
        result = self.runner.invoke(cli, ["analyze", "invalid-url"])
        
        assert result.exit_code == 1
        assert "Invalid GitHub repository URL" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._run_analysis')
    def test_analyze_keyboard_interrupt(self, mock_run_analysis, mock_load_config):
        """Test analyze command with keyboard interrupt."""
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_run_analysis.side_effect = KeyboardInterrupt()
        
        result = self.runner.invoke(cli, ["analyze", "owner/repo"])
        
        assert result.exit_code == 130
        assert "Analysis interrupted by user" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._run_analysis')
    def test_analyze_unexpected_error(self, mock_run_analysis, mock_load_config):
        """Test analyze command with unexpected error."""
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_run_analysis.side_effect = Exception("Unexpected error")
        
        result = self.runner.invoke(cli, ["analyze", "owner/repo"])
        
        assert result.exit_code == 1
        assert "Unexpected error" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli._run_analysis')
    def test_analyze_with_scan_all_flag(self, mock_run_analysis, mock_load_config):
        """Test analyze command with --scan-all flag."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        
        mock_run_analysis.return_value = {
            "repository": "owner/repo",
            "total_forks": 5,
            "analyzed_forks": 5,  # All forks analyzed with --scan-all
            "total_features": 0,
            "high_value_features": 0,
            "report": "Test report"
        }
        
        # Run command with --scan-all flag
        result = self.runner.invoke(cli, ["analyze", "owner/repo", "--scan-all"])
        
        # Verify success
        assert result.exit_code == 0
        
        # Verify _run_analysis was called with scan_all=True
        mock_run_analysis.assert_called_once()
        call_args = mock_run_analysis.call_args[0]
        call_kwargs = mock_run_analysis.call_args[1] if mock_run_analysis.call_args[1] else {}
        
        # Check that scan_all parameter was passed as True
        assert len(call_args) >= 4  # config, owner, repo_name, verbose
        if len(call_args) > 4:
            assert call_args[4] == True  # scan_all as positional arg
        else:
            assert call_kwargs.get('scan_all', False) == True  # scan_all as keyword arg


class TestConfigureCommand:
    """Test configure command functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.runner = CliRunner()

    @patch('forklift.cli.load_config')
    def test_configure_display_current(self, mock_load_config):
        """Test configure command displaying current configuration."""
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        
        # Use --min-score to avoid interactive mode
        result = self.runner.invoke(cli, ["configure", "--min-score", "80"])
        
        assert result.exit_code == 0
        assert "Current Configuration" in result.output
        assert "***" in result.output  # Token should be masked

    @patch('forklift.cli.load_config')
    def test_configure_with_options(self, mock_load_config):
        """Test configure command with CLI options."""
        mock_config = create_mock_config()
        mock_config.github.token = None  # Override for this test
        mock_load_config.return_value = mock_config
        
        result = self.runner.invoke(cli, [
            "configure",
            "--github-token", "new_token",
            "--min-score", "80",
            "--max-forks", "50",
            "--output-format", "json",
            "--cache-duration", "12"
        ])
        
        assert result.exit_code == 0
        assert mock_config.github.token == "new_token"
        assert mock_config.analysis.min_score_threshold == 80
        assert mock_config.analysis.max_forks_to_analyze == 50
        assert mock_config.output_format == "json"
        assert mock_config.cache.duration_hours == 12

    @patch('forklift.cli.load_config')
    def test_configure_save_to_file(self, mock_load_config):
        """Test configure command saving to file."""
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            
            result = self.runner.invoke(cli, [
                "configure",
                "--min-score", "80",  # Provide an option to avoid interactive mode
                "--save", str(config_path)
            ])
            
            assert result.exit_code == 0
            mock_config.save_to_file.assert_called_once_with(str(config_path))
            assert "Configuration saved to:" in result.output
            assert str(config_path) in result.output

    @patch('forklift.cli.load_config')
    def test_configure_save_error(self, mock_load_config):
        """Test configure command save error."""
        mock_config = create_mock_config()
        mock_config.save_to_file = Mock(side_effect=Exception("Save error"))
        mock_load_config.return_value = mock_config
        
        result = self.runner.invoke(cli, [
            "configure",
            "--min-score", "80",  # Provide an option to avoid interactive mode
            "--save", "invalid/path/config.yaml"
        ])
        
        assert result.exit_code == 1
        assert "Error saving configuration" in result.output


class TestScheduleCommand:
    """Test schedule command functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.runner = CliRunner()

    @patch('forklift.cli.load_config')
    def test_schedule_with_cron(self, mock_load_config):
        """Test schedule command with cron expression."""
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        
        result = self.runner.invoke(cli, [
            "schedule", "owner/repo",
            "--cron", "0 0 * * 0"
        ])
        
        assert result.exit_code == 0
        assert "Schedule Configuration" in result.output
        assert "owner/repo" in result.output
        assert "0 0 * * 0" in result.output

    @patch('forklift.cli.load_config')
    def test_schedule_with_interval(self, mock_load_config):
        """Test schedule command with interval."""
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        
        result = self.runner.invoke(cli, [
            "schedule", "owner/repo",
            "--interval", "24"
        ])
        
        assert result.exit_code == 0
        assert "Schedule Configuration" in result.output
        assert "owner/repo" in result.output
        assert "every 24 hours" in result.output

    @patch('forklift.cli.load_config')
    def test_schedule_no_schedule_specified(self, mock_load_config):
        """Test schedule command without schedule specification."""
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        
        result = self.runner.invoke(cli, [
            "schedule", "owner/repo"
        ])
        
        assert result.exit_code == 1
        assert "Either --cron or --interval must be specified" in result.output

    @patch('forklift.cli.load_config')
    def test_schedule_both_cron_and_interval(self, mock_load_config):
        """Test schedule command with both cron and interval."""
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        
        result = self.runner.invoke(cli, [
            "schedule", "owner/repo",
            "--cron", "0 0 * * 0",
            "--interval", "24"
        ])
        
        assert result.exit_code == 1
        assert "Cannot specify both --cron and --interval" in result.output

    @patch('forklift.cli.load_config')
    def test_schedule_invalid_repository_url(self, mock_load_config):
        """Test schedule command with invalid repository URL."""
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        
        result = self.runner.invoke(cli, [
            "schedule", "invalid-url",
            "--cron", "0 0 * * 0"
        ])
        
        assert result.exit_code == 1
        assert "Invalid GitHub repository URL" in result.output


class TestRunAnalysis:
    """Test the _run_analysis function."""

    @pytest.mark.asyncio
    @patch('forklift.cli.GitHubClient')
    @patch('forklift.cli.ForkDiscoveryService')
    @patch('forklift.cli.FeatureRankingEngine')
    async def test_run_analysis_success(self, mock_ranking_engine, mock_fork_discovery, mock_github_client):
        """Test successful analysis run."""
        from forklift.cli import _run_analysis
        from forklift.config.settings import ForkliftConfig
        
        # Setup config
        config = ForkliftConfig()
        config.github.token = "test_token"
        
        # Setup mocks
        mock_client_instance = Mock()
        mock_github_client.return_value = mock_client_instance
        
        mock_discovery_instance = Mock()
        mock_discovery_instance.discover_forks = AsyncMock(return_value=[
            Mock(full_name="user1/repo"),
            Mock(full_name="user2/repo")
        ])
        mock_discovery_instance.filter_active_forks = AsyncMock(return_value=[
            Mock(full_name="user1/repo"),
            Mock(full_name="user2/repo")
        ])
        mock_fork_discovery.return_value = mock_discovery_instance
        
        mock_ranking_instance = Mock()
        mock_ranking_engine.return_value = mock_ranking_instance
        
        # Run analysis
        results = await _run_analysis(config, "owner", "repo", verbose=False)
        
        # Verify results
        assert results["repository"] == "owner/repo"
        assert results["total_forks"] == 2
        assert results["analyzed_forks"] == 2
        assert "# Fork Analysis Report for owner/repo" in results["report"]
        
        # Verify service initialization
        mock_github_client.assert_called_once_with(config.github)
        mock_fork_discovery.assert_called_once()
        mock_ranking_engine.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_analysis_no_token(self):
        """Test analysis run without GitHub token."""
        from forklift.cli import _run_analysis, CLIError
        from forklift.config.settings import ForkliftConfig
        
        config = ForkliftConfig()
        config.github.token = None
        
        with pytest.raises(CLIError, match="GitHub token not configured"):
            await _run_analysis(config, "owner", "repo", verbose=False)

    @pytest.mark.asyncio
    @patch('forklift.cli.GitHubClient')
    @patch('forklift.cli.ForkDiscoveryService')
    async def test_run_analysis_discovery_error(self, mock_fork_discovery, mock_github_client):
        """Test analysis run with fork discovery error."""
        from forklift.cli import _run_analysis, CLIError
        from forklift.config.settings import ForkliftConfig
        
        config = ForkliftConfig()
        config.github.token = "test_token"
        
        # Setup mocks
        mock_client_instance = Mock()
        mock_github_client.return_value = mock_client_instance
        
        mock_discovery_instance = Mock()
        mock_discovery_instance.discover_forks = AsyncMock(side_effect=Exception("Discovery failed"))
        mock_fork_discovery.return_value = mock_discovery_instance
        
        with pytest.raises(CLIError, match="Failed to discover forks"):
            await _run_analysis(config, "owner", "repo", verbose=False)