"""Unit tests for CLI interface."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from forklift.cli import CLIError, cli, validate_repository_url
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

    @patch("forklift.cli.load_config")
    def test_cli_with_config_file(self, mock_load_config):
        """Test CLI with configuration file."""
        mock_config = Mock(spec=ForkliftConfig)
        mock_load_config.return_value = mock_config

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("github:\n  token: test_token\n")
            config_path = f.name

        try:
            result = self.runner.invoke(cli, ["--config", config_path, "--help"])
            assert result.exit_code == 0
            # Note: load_config is called during CLI initialization, not during help display
            # The help command exits early, so we just check it doesn't crash
        finally:
            Path(config_path).unlink()

    @patch("forklift.cli.load_config")
    def test_cli_with_invalid_config_file(self, mock_load_config):
        """Test CLI with invalid configuration file."""
        # Create a temporary file that exists but has invalid content
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
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

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._run_analysis")
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

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._run_analysis")
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

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._run_analysis")
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

    @patch("forklift.cli.load_config")
    def test_analyze_invalid_repository_url(self, mock_load_config):
        """Test analyze command with invalid repository URL."""
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config

        result = self.runner.invoke(cli, ["analyze", "invalid-url"])

        assert result.exit_code == 1
        assert "Invalid GitHub repository URL" in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._run_analysis")
    def test_analyze_keyboard_interrupt(self, mock_run_analysis, mock_load_config):
        """Test analyze command with keyboard interrupt."""
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config

        mock_run_analysis.side_effect = KeyboardInterrupt()

        result = self.runner.invoke(cli, ["analyze", "owner/repo"])

        assert result.exit_code == 130
        assert "Analysis interrupted by user" in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._run_analysis")
    def test_analyze_unexpected_error(self, mock_run_analysis, mock_load_config):
        """Test analyze command with unexpected error."""
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config

        mock_run_analysis.side_effect = Exception("Unexpected error")

        result = self.runner.invoke(cli, ["analyze", "owner/repo"])

        assert result.exit_code == 1
        assert "Unexpected error" in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._run_analysis")
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
            assert call_kwargs.get("scan_all", False) == True  # scan_all as keyword arg


class TestConfigureCommand:
    """Test configure command functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.runner = CliRunner()

    @patch("forklift.cli.load_config")
    def test_configure_display_current(self, mock_load_config):
        """Test configure command displaying current configuration."""
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config

        # Use --min-score to avoid interactive mode
        result = self.runner.invoke(cli, ["configure", "--min-score", "80"])

        assert result.exit_code == 0
        assert "Current Configuration" in result.output
        assert "***" in result.output  # Token should be masked

    @patch("forklift.cli.load_config")
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

    @patch("forklift.cli.load_config")
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

    @patch("forklift.cli.load_config")
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

    @patch("forklift.cli.load_config")
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

    @patch("forklift.cli.load_config")
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

    @patch("forklift.cli.load_config")
    def test_schedule_no_schedule_specified(self, mock_load_config):
        """Test schedule command without schedule specification."""
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config

        result = self.runner.invoke(cli, [
            "schedule", "owner/repo"
        ])

        assert result.exit_code == 1
        assert "Either --cron or --interval must be specified" in result.output

    @patch("forklift.cli.load_config")
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

    @patch("forklift.cli.load_config")
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
    @patch("forklift.cli.RepositoryAnalyzer")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.ForkDiscoveryService")
    @patch("forklift.cli.FeatureRankingEngine")
    async def test_run_analysis_success(self, mock_ranking_engine, mock_fork_discovery, mock_github_client, mock_repository_analyzer):
        """Test successful analysis run."""
        from forklift.cli import _run_analysis
        from forklift.config.settings import ForkliftConfig
        from forklift.models.analysis import Feature, ForkAnalysis
        from forklift.models.github import Fork, Repository

        # Setup config
        config = ForkliftConfig()
        config.github.token = "test_token"

        # Create mock repository and forks
        mock_base_repo = Mock(spec=Repository)
        mock_base_repo.full_name = "owner/repo"

        mock_fork1 = Mock(spec=Fork)
        mock_fork1.repository = Mock()
        mock_fork1.repository.full_name = "user1/repo"

        mock_fork2 = Mock(spec=Fork)
        mock_fork2.repository = Mock()
        mock_fork2.repository.full_name = "user2/repo"

        # Setup GitHub client mock
        mock_client_instance = Mock()
        mock_client_instance.get_repository = AsyncMock(return_value=mock_base_repo)
        mock_github_client.return_value = mock_client_instance

        # Setup fork discovery mock
        mock_discovery_instance = Mock()
        mock_discovery_instance.discover_forks = AsyncMock(return_value=[mock_fork1, mock_fork2])
        mock_discovery_instance.filter_active_forks = AsyncMock(return_value=[mock_fork1, mock_fork2])
        mock_fork_discovery.return_value = mock_discovery_instance

        # Setup repository analyzer mock
        mock_analyzer_instance = Mock()
        mock_feature1 = Mock(spec=Feature)
        mock_feature1.commits = [Mock(), Mock()]  # 2 commits = high value
        mock_feature2 = Mock(spec=Feature)
        mock_feature2.commits = [Mock()]  # 1 commit = not high value

        mock_analysis1 = Mock(spec=ForkAnalysis)
        mock_analysis1.features = [mock_feature1]
        mock_analysis2 = Mock(spec=ForkAnalysis)
        mock_analysis2.features = [mock_feature2]

        mock_analyzer_instance.analyze_fork = AsyncMock(side_effect=[mock_analysis1, mock_analysis2])
        mock_repository_analyzer.return_value = mock_analyzer_instance

        # Setup ranking engine mock
        mock_ranking_instance = Mock()
        mock_ranking_engine.return_value = mock_ranking_instance

        # Run analysis
        results = await _run_analysis(config, "owner", "repo", verbose=False)

        # Verify results
        assert results["repository"] == "owner/repo"
        assert results["total_forks"] == 2
        assert results["analyzed_forks"] == 2
        assert results["total_features"] == 2
        assert results["high_value_features"] == 1  # Only mock_feature1 has 2+ commits
        assert "# Fork Analysis Report for owner/repo" in results["report"]
        assert "Explanations Enabled: False" in results["report"]

        # Verify service initialization
        mock_github_client.assert_called_once_with(config.github)
        mock_fork_discovery.assert_called_once()
        mock_ranking_engine.assert_called_once()
        mock_repository_analyzer.assert_called_once()

        # Verify repository analyzer was called correctly
        assert mock_analyzer_instance.analyze_fork.call_count == 2
        mock_analyzer_instance.analyze_fork.assert_any_call(fork=mock_fork1, base_repo=mock_base_repo, explain=False)
        mock_analyzer_instance.analyze_fork.assert_any_call(fork=mock_fork2, base_repo=mock_base_repo, explain=False)

    @pytest.mark.asyncio
    @patch("forklift.cli.CommitExplanationEngine")
    @patch("forklift.cli.ExplanationGenerator")
    @patch("forklift.cli.ImpactAssessor")
    @patch("forklift.cli.CommitCategorizer")
    @patch("forklift.cli.RepositoryAnalyzer")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.ForkDiscoveryService")
    @patch("forklift.cli.FeatureRankingEngine")
    async def test_run_analysis_with_explanations(self, mock_ranking_engine, mock_fork_discovery, mock_github_client,
                                                 mock_repository_analyzer, mock_categorizer, mock_assessor, mock_generator, mock_explanation_engine):
        """Test successful analysis run with explanations enabled."""
        from forklift.cli import _run_analysis
        from forklift.config.settings import ForkliftConfig
        from forklift.models.analysis import Feature, ForkAnalysis
        from forklift.models.github import Fork, Repository

        # Setup config
        config = ForkliftConfig()
        config.github.token = "test_token"

        # Create mock repository and forks
        mock_base_repo = Mock(spec=Repository)
        mock_base_repo.full_name = "owner/repo"

        mock_fork1 = Mock(spec=Fork)
        mock_fork1.repository = Mock()
        mock_fork1.repository.full_name = "user1/repo"

        # Setup GitHub client mock
        mock_client_instance = Mock()
        mock_client_instance.get_repository = AsyncMock(return_value=mock_base_repo)
        mock_github_client.return_value = mock_client_instance

        # Setup fork discovery mock
        mock_discovery_instance = Mock()
        mock_discovery_instance.discover_forks = AsyncMock(return_value=[mock_fork1])
        mock_discovery_instance.filter_active_forks = AsyncMock(return_value=[mock_fork1])
        mock_fork_discovery.return_value = mock_discovery_instance

        # Setup explanation engine components
        mock_categorizer_instance = Mock()
        mock_categorizer.return_value = mock_categorizer_instance

        mock_assessor_instance = Mock()
        mock_assessor.return_value = mock_assessor_instance

        mock_generator_instance = Mock()
        mock_generator.return_value = mock_generator_instance

        mock_explanation_engine_instance = Mock()
        mock_explanation_engine.return_value = mock_explanation_engine_instance

        # Setup repository analyzer mock
        mock_analyzer_instance = Mock()
        mock_feature1 = Mock(spec=Feature)
        mock_feature1.commits = [Mock(), Mock()]

        mock_analysis1 = Mock(spec=ForkAnalysis)
        mock_analysis1.features = [mock_feature1]

        mock_analyzer_instance.analyze_fork = AsyncMock(return_value=mock_analysis1)
        mock_repository_analyzer.return_value = mock_analyzer_instance

        # Setup ranking engine mock
        mock_ranking_instance = Mock()
        mock_ranking_engine.return_value = mock_ranking_instance

        # Run analysis with explanations
        results = await _run_analysis(config, "owner", "repo", verbose=False, explain=True)

        # Verify results
        assert results["repository"] == "owner/repo"
        assert results["total_forks"] == 1
        assert results["analyzed_forks"] == 1
        assert results["total_features"] == 1
        assert results["high_value_features"] == 1
        assert "# Fork Analysis Report for owner/repo" in results["report"]
        assert "Explanations Enabled: True" in results["report"]
        assert "Commit Explanations Summary" in results["report"]

        # Verify explanation engine was created
        mock_categorizer.assert_called_once()
        mock_assessor.assert_called_once()
        mock_generator.assert_called_once()
        mock_explanation_engine.assert_called_once_with(mock_categorizer_instance, mock_assessor_instance, mock_generator_instance)

        # Verify repository analyzer was created with explanation engine
        mock_repository_analyzer.assert_called_once_with(
            github_client=mock_client_instance,
            explanation_engine=mock_explanation_engine_instance
        )

        # Verify repository analyzer was called with explain=True
        mock_analyzer_instance.analyze_fork.assert_called_once_with(
            fork=mock_fork1, base_repo=mock_base_repo, explain=True
        )

    @pytest.mark.asyncio
    async def test_run_analysis_no_token(self):
        """Test analysis run without GitHub token."""
        from forklift.cli import CLIError, _run_analysis
        from forklift.config.settings import ForkliftConfig

        config = ForkliftConfig()
        config.github.token = None

        with pytest.raises(CLIError, match="GitHub token not configured"):
            await _run_analysis(config, "owner", "repo", verbose=False)

    @pytest.mark.asyncio
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.ForkDiscoveryService")
    async def test_run_analysis_discovery_error(self, mock_fork_discovery, mock_github_client):
        """Test analysis run with fork discovery error."""
        from forklift.cli import CLIError, _run_analysis
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


class TestShowCommitsCommand:
    """Test show-commits command functionality with fork filtering."""

    def setup_method(self):
        """Setup test fixtures."""
        self.runner = CliRunner()

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_commits")
    def test_show_commits_basic(self, mock_show_commits, mock_load_config):
        """Test basic show-commits command."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_commits.return_value = None

        result = self.runner.invoke(cli, ["show-commits", "owner/repo"])

        assert result.exit_code == 0
        mock_show_commits.assert_called_once()

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_commits")
    def test_show_commits_with_detail_flag(self, mock_show_commits, mock_load_config):
        """Test show-commits command with --detail flag."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_commits.return_value = None

        result = self.runner.invoke(cli, ["show-commits", "owner/repo", "--detail"])

        assert result.exit_code == 0
        mock_show_commits.assert_called_once()
        
        # Verify detail flag was passed (positional argument 14)
        call_args = mock_show_commits.call_args[0]
        assert len(call_args) >= 15  # Should have at least 15 positional arguments
        assert call_args[14] is True  # detail flag
        assert call_args[15] is False  # force flag

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_commits")
    def test_show_commits_with_force_flag(self, mock_show_commits, mock_load_config):
        """Test show-commits command with --force flag."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_commits.return_value = None

        result = self.runner.invoke(cli, ["show-commits", "owner/repo", "--detail", "--force"])

        assert result.exit_code == 0
        mock_show_commits.assert_called_once()
        
        # Verify flags were passed (positional arguments 14 and 15)
        call_args = mock_show_commits.call_args[0]
        assert len(call_args) >= 16  # Should have at least 16 positional arguments
        assert call_args[14] is True  # detail flag
        assert call_args[15] is True  # force flag

    def test_show_commits_help_includes_filtering_info(self):
        """Test that help text includes information about fork filtering."""
        result = self.runner.invoke(cli, ["show-commits", "--help"])

        assert result.exit_code == 0
        assert "--detail" in result.output
        assert "--force" in result.output
        assert "Automatically skips forks with no commits ahead" in result.output
        assert "Force analysis even for forks with no commits ahead" in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_commits")
    def test_show_commits_invalid_repository_url(self, mock_show_commits, mock_load_config):
        """Test show-commits command with invalid repository URL."""
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_commits.side_effect = CLIError("Invalid GitHub repository URL")

        result = self.runner.invoke(cli, ["show-commits", "invalid-url"])

        assert result.exit_code == 1
        assert "Invalid GitHub repository URL" in result.output
        mock_show_commits.assert_called_once()

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_commits")
    def test_show_commits_keyboard_interrupt(self, mock_show_commits, mock_load_config):
        """Test show-commits command with keyboard interrupt."""
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_commits.side_effect = KeyboardInterrupt()

        result = self.runner.invoke(cli, ["show-commits", "owner/repo"])

        assert result.exit_code == 130
        assert "Operation interrupted by user" in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_commits")
    def test_show_commits_cli_error(self, mock_show_commits, mock_load_config):
        """Test show-commits command with CLI error."""
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_commits.side_effect = CLIError("Test CLI error")

        result = self.runner.invoke(cli, ["show-commits", "owner/repo"])

        assert result.exit_code == 1
        assert "Error: Test CLI error" in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_commits")
    def test_show_commits_unexpected_error(self, mock_show_commits, mock_load_config):
        """Test show-commits command with unexpected error."""
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_commits.side_effect = Exception("Unexpected error")

        result = self.runner.invoke(cli, ["show-commits", "owner/repo"])

        assert result.exit_code == 1
        assert "Unexpected error" in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_commits")
    def test_show_commits_with_all_flags(self, mock_show_commits, mock_load_config):
        """Test show-commits command with multiple flags."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_commits.return_value = None

        result = self.runner.invoke(cli, [
            "show-commits", "owner/repo",
            "--branch", "main",
            "--limit", "10",
            "--since", "2024-01-01",
            "--until", "2024-12-31",
            "--author", "testuser",
            "--include-merge",
            "--show-files",
            "--show-stats",
            "--explain",
            "--detail",
            "--force",
            "--disable-cache"
        ])

        assert result.exit_code == 0
        mock_show_commits.assert_called_once()
        
        # Verify all flags were passed correctly as positional arguments
        call_args = mock_show_commits.call_args[0]
        assert len(call_args) >= 16  # Should have at least 16 positional arguments
        # Arguments: config, fork_url, branch, limit, since_date, until_date, author, include_merge, show_files, show_stats, verbose, explain, ai_summary, ai_summary_compact, detail, force, disable_cache
        assert call_args[2] == "main"  # branch
        assert call_args[3] == 10  # limit
        assert call_args[6] == "testuser"  # author
        assert call_args[7] is True  # include_merge
        assert call_args[8] is True  # show_files
        assert call_args[9] is True  # show_stats
        assert call_args[11] is True  # explain
        assert call_args[14] is True  # detail
        assert call_args[15] is True  # force
        assert call_args[16] is True  # disable_cache


class TestShowForksCommand:
    """Test show-forks command functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.runner = CliRunner()

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_forks_summary")
    def test_show_forks_basic(self, mock_show_forks_summary, mock_load_config):
        """Test basic show-forks command."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_forks_summary.return_value = None

        result = self.runner.invoke(cli, ["show-forks", "owner/repo"])

        assert result.exit_code == 0
        mock_show_forks_summary.assert_called_once_with(
            mock_config, "owner/repo", None, False, False, 0, False, False
        )

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_forks_summary")
    def test_show_forks_with_detail_flag(self, mock_show_forks_summary, mock_load_config):
        """Test show-forks command with --detail flag."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_forks_summary.return_value = None

        result = self.runner.invoke(cli, ["show-forks", "owner/repo", "--detail"])

        assert result.exit_code == 0
        mock_show_forks_summary.assert_called_once_with(
            mock_config, "owner/repo", None, False, True, 0, False, False
        )

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_forks_summary")
    def test_show_forks_with_max_forks_and_detail(self, mock_show_forks_summary, mock_load_config):
        """Test show-forks command with --max-forks and --detail flags."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_forks_summary.return_value = None

        result = self.runner.invoke(cli, ["show-forks", "owner/repo", "--max-forks", "50", "--detail"])

        assert result.exit_code == 0
        mock_show_forks_summary.assert_called_once_with(
            mock_config, "owner/repo", 50, False, True, 0, False, False
        )

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_forks_summary")
    def test_show_forks_with_verbose_and_detail(self, mock_show_forks_summary, mock_load_config):
        """Test show-forks command with --verbose and --detail flags."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_forks_summary.return_value = None

        result = self.runner.invoke(cli, ["--verbose", "show-forks", "owner/repo", "--detail"])

        assert result.exit_code == 0
        mock_show_forks_summary.assert_called_once_with(
            mock_config, "owner/repo", None, True, True, 0, False, False
        )

    def test_show_forks_help_includes_detail_flag(self):
        """Test that show-forks help includes --detail flag documentation."""
        result = self.runner.invoke(cli, ["show-forks", "--help"])

        assert result.exit_code == 0
        assert "--detail" in result.output
        assert "Fetch exact commit counts ahead" in result.output
        assert "additional API requests" in result.output

    @patch("forklift.cli.load_config")
    def test_show_forks_no_github_token(self, mock_load_config):
        """Test show-forks command without GitHub token."""
        # Setup mock config without token
        mock_config = create_mock_config()
        mock_config.github.token = None
        mock_load_config.return_value = mock_config

        result = self.runner.invoke(cli, ["show-forks", "owner/repo"])

        assert result.exit_code == 1
        assert "GitHub token not configured" in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_forks_summary")
    def test_show_forks_invalid_max_forks(self, mock_show_forks_summary, mock_load_config):
        """Test show-forks command with invalid --max-forks value."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config

        # Test with value too low
        result = self.runner.invoke(cli, ["show-forks", "owner/repo", "--max-forks", "0"])
        assert result.exit_code != 0

        # Test with value too high
        result = self.runner.invoke(cli, ["show-forks", "owner/repo", "--max-forks", "1001"])
        assert result.exit_code != 0

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_forks_summary")
    def test_show_forks_exception_handling(self, mock_show_forks_summary, mock_load_config):
        """Test show-forks command exception handling."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_forks_summary.side_effect = Exception("Test error")

        result = self.runner.invoke(cli, ["show-forks", "owner/repo"])

        assert result.exit_code == 1
        assert "Unexpected error" in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_forks_summary")
    def test_show_forks_with_show_commits_default(self, mock_show_forks_summary, mock_load_config):
        """Test show-forks command with default --show-commits value."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_forks_summary.return_value = None

        result = self.runner.invoke(cli, ["show-forks", "owner/repo"])

        assert result.exit_code == 0
        mock_show_forks_summary.assert_called_once_with(
            mock_config, "owner/repo", None, False, False, 0, False, False
        )

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_forks_summary")
    def test_show_forks_with_show_commits_valid_value(self, mock_show_forks_summary, mock_load_config):
        """Test show-forks command with valid --show-commits value."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_forks_summary.return_value = None

        result = self.runner.invoke(cli, ["show-forks", "owner/repo", "--show-commits", "5"])

        assert result.exit_code == 0
        mock_show_forks_summary.assert_called_once_with(
            mock_config, "owner/repo", None, False, False, 5, False, False
        )

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_forks_summary")
    def test_show_forks_with_show_commits_max_value(self, mock_show_forks_summary, mock_load_config):
        """Test show-forks command with maximum --show-commits value."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_forks_summary.return_value = None

        result = self.runner.invoke(cli, ["show-forks", "owner/repo", "--show-commits", "10"])

        assert result.exit_code == 0
        mock_show_forks_summary.assert_called_once_with(
            mock_config, "owner/repo", None, False, False, 10, False, False
        )

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_forks_summary")
    def test_show_forks_with_show_commits_combined_flags(self, mock_show_forks_summary, mock_load_config):
        """Test show-forks command with --show-commits combined with other flags."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_forks_summary.return_value = None

        result = self.runner.invoke(cli, ["show-forks", "owner/repo", "--detail", "--max-forks", "25", "--show-commits", "3"])

        assert result.exit_code == 0
        mock_show_forks_summary.assert_called_once_with(
            mock_config, "owner/repo", 25, False, True, 3, False, False
        )

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_forks_summary")
    def test_show_forks_with_force_all_commits_flag(self, mock_show_forks_summary, mock_load_config):
        """Test show-forks command with --force-all-commits flag."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_forks_summary.return_value = None

        result = self.runner.invoke(cli, ["show-forks", "owner/repo", "--show-commits", "3", "--force-all-commits"])

        assert result.exit_code == 0
        mock_show_forks_summary.assert_called_once_with(
            mock_config, "owner/repo", None, False, False, 3, True, False
        )

    @patch("forklift.cli.load_config")
    def test_show_forks_with_show_commits_invalid_negative(self, mock_load_config):
        """Test show-forks command with invalid negative --show-commits value."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config

        result = self.runner.invoke(cli, ["show-forks", "owner/repo", "--show-commits", "-1"])

        assert result.exit_code != 0
        assert "Invalid value" in result.output

    @patch("forklift.cli.load_config")
    def test_show_forks_with_show_commits_invalid_too_high(self, mock_load_config):
        """Test show-forks command with invalid too high --show-commits value."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config

        result = self.runner.invoke(cli, ["show-forks", "owner/repo", "--show-commits", "11"])

        assert result.exit_code != 0
        assert "Invalid value" in result.output

    def test_show_forks_help_includes_show_commits_flag(self):
        """Test that show-forks help includes --show-commits flag documentation."""
        result = self.runner.invoke(cli, ["show-forks", "--help"])

        assert result.exit_code == 0
        assert "--show-commits" in result.output
        assert "Show last N commits for each fork" in result.output or "Recent Commits column" in result.output
        assert "default: 0" in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_forks_summary")
    def test_show_forks_with_ahead_only_flag(self, mock_show_forks_summary, mock_load_config):
        """Test show-forks command with --ahead-only flag."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_forks_summary.return_value = None

        result = self.runner.invoke(cli, ["show-forks", "owner/repo", "--ahead-only"])

        assert result.exit_code == 0
        mock_show_forks_summary.assert_called_once_with(
            mock_config, "owner/repo", None, False, False, 0, False, True
        )

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_forks_summary")
    def test_show_forks_with_ahead_only_and_detail_flags(self, mock_show_forks_summary, mock_load_config):
        """Test show-forks command with --ahead-only and --detail flags."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_forks_summary.return_value = None

        result = self.runner.invoke(cli, ["show-forks", "owner/repo", "--ahead-only", "--detail"])

        assert result.exit_code == 0
        mock_show_forks_summary.assert_called_once_with(
            mock_config, "owner/repo", None, False, True, 0, False, True
        )

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_forks_summary")
    def test_show_forks_with_ahead_only_and_show_commits(self, mock_show_forks_summary, mock_load_config):
        """Test show-forks command with --ahead-only and --show-commits flags."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_forks_summary.return_value = None

        result = self.runner.invoke(cli, ["show-forks", "owner/repo", "--ahead-only", "--show-commits", "5"])

        assert result.exit_code == 0
        mock_show_forks_summary.assert_called_once_with(
            mock_config, "owner/repo", None, False, False, 5, False, True
        )

    @patch("forklift.cli.load_config")
    @patch("forklift.cli._show_forks_summary")
    def test_show_forks_with_all_flags_combined(self, mock_show_forks_summary, mock_load_config):
        """Test show-forks command with --ahead-only combined with all other flags."""
        # Setup mocks
        mock_config = create_mock_config()
        mock_load_config.return_value = mock_config
        mock_show_forks_summary.return_value = None

        result = self.runner.invoke(cli, [
            "show-forks", "owner/repo", 
            "--ahead-only", 
            "--detail", 
            "--max-forks", "25", 
            "--show-commits", "3", 
            "--force-all-commits"
        ])

        assert result.exit_code == 0
        mock_show_forks_summary.assert_called_once_with(
            mock_config, "owner/repo", 25, False, True, 3, True, True
        )

    def test_show_forks_help_includes_ahead_only_flag(self):
        """Test that show-forks help includes --ahead-only flag documentation."""
        result = self.runner.invoke(cli, ["show-forks", "--help"])

        assert result.exit_code == 0
        assert "--ahead-only" in result.output
        assert "Show only forks that have commits ahead" in result.output
