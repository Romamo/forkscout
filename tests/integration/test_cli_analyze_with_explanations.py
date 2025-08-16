"""Integration tests for CLI analyze command with --explain flag."""

import pytest
from click.testing import CliRunner
from unittest.mock import Mock, AsyncMock, patch

from forklift.cli import cli


class TestAnalyzeCommandWithExplanations:
    """Integration tests for analyze command with --explain flag."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        with patch('forklift.cli.load_config') as mock_load:
            mock_config = Mock()
            mock_config.github.token = "test_token"
            mock_config.analysis.min_score_threshold = 70.0
            mock_config.analysis.max_forks_to_analyze = 100
            mock_config.analysis.auto_pr_enabled = False
            mock_config.scoring = Mock()
            mock_config.dry_run = False
            mock_config.output_format = "markdown"
            
            # Mock logging configuration
            mock_config.logging = None  # This will make setup_logging use defaults
            
            mock_load.return_value = mock_config
            yield mock_config

    @patch('forklift.cli._run_analysis')
    def test_analyze_command_with_explain_flag(self, mock_run_analysis, runner, mock_config):
        """Test analyze command with --explain flag."""
        # Mock the analysis function to return success
        mock_run_analysis.return_value = {
            "repository": "owner/repo",
            "total_forks": 1,
            "analyzed_forks": 1,
            "total_features": 1,
            "high_value_features": 1,
            "report": "# Test Report"
        }
        
        # Run command with --explain flag
        result = runner.invoke(cli, ['analyze', 'owner/repo', '--explain'])
        
        # Verify command succeeded
        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        
        # Verify _run_analysis was called with explain=True
        mock_run_analysis.assert_called_once()
        args, kwargs = mock_run_analysis.call_args
        assert len(args) >= 5  # config, owner, repo_name, verbose, scan_all, explain
        assert args[5] == True  # explain parameter should be True
        
        # Verify output contains success message
        assert "Analysis complete!" in result.output

    @patch('forklift.cli._run_analysis')
    def test_analyze_command_without_explain_flag(self, mock_run_analysis, runner, mock_config):
        """Test analyze command without --explain flag (default behavior)."""
        # Mock the analysis function to return success
        mock_run_analysis.return_value = {
            "repository": "owner/repo",
            "total_forks": 1,
            "analyzed_forks": 1,
            "total_features": 1,
            "high_value_features": 0,
            "report": "# Test Report"
        }
        
        # Run command without --explain flag
        result = runner.invoke(cli, ['analyze', 'owner/repo'])
        
        # Verify command succeeded
        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        
        # Verify _run_analysis was called with explain=False
        mock_run_analysis.assert_called_once()
        args, kwargs = mock_run_analysis.call_args
        assert len(args) >= 5  # config, owner, repo_name, verbose, scan_all, explain
        assert args[5] == False  # explain parameter should be False
        
        # Verify output contains success message
        assert "Analysis complete" in result.output

    def test_analyze_command_help_includes_explain_flag(self, runner):
        """Test that --explain flag appears in help text."""
        result = runner.invoke(cli, ['analyze', '--help'])
        
        assert result.exit_code == 0
        assert '--explain' in result.output
        assert 'Generate explanations for each commit during' in result.output

    @patch('forklift.cli._run_analysis')
    def test_analyze_command_explain_with_other_flags(self, mock_run_analysis, runner, mock_config):
        """Test analyze command with --explain combined with other flags."""
        # Mock the analysis function to return success
        mock_run_analysis.return_value = {
            "repository": "owner/repo",
            "total_forks": 1,
            "analyzed_forks": 1,
            "total_features": 1,
            "high_value_features": 0,
            "report": "# Test Report"
        }
        
        # Run command with --explain and other flags
        result = runner.invoke(cli, [
            'analyze', 'owner/repo', 
            '--explain', 
            '--dry-run', 
            '--max-forks', '50',
            '--scan-all'
        ])
        
        # Verify command succeeded
        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        
        # Verify _run_analysis was called with explain=True and scan_all=True
        mock_run_analysis.assert_called_once()
        args, kwargs = mock_run_analysis.call_args
        assert len(args) >= 6  # config, owner, repo_name, verbose, scan_all, explain
        assert args[4] == True   # scan_all parameter should be True
        assert args[5] == True   # explain parameter should be True
        
        # Verify output contains success message
        assert "Analysis complete" in result.output