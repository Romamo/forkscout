"""Integration tests for CLI validation error handling."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from click.testing import CliRunner

from forklift.cli import cli
from forklift.models.validation_handler import ValidationSummary


class TestCLIValidationErrorHandlingIntegration:
    """Integration tests for CLI validation error handling."""

    @patch('forklift.cli.load_config')
    @patch('forklift.cli.validate_repository_url')
    @patch('forklift.cli.GitHubClient')
    @patch('forklift.cli.RepositoryDisplayService')
    def test_show_forks_displays_validation_summary_on_errors(
        self, 
        mock_display_service_class,
        mock_github_client_class,
        mock_validate_url,
        mock_load_config
    ):
        """Test that show-forks command displays validation summaries when errors occur."""
        # Setup mocks
        mock_config = Mock()
        mock_config.github.token = "test_token"
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("owner", "repo")
        
        # Mock GitHub client
        mock_github_client = Mock()
        mock_github_client_class.return_value = mock_github_client
        
        # Mock display service with validation errors
        mock_display_service = Mock()
        mock_display_service_class.return_value = mock_display_service
        
        # Create validation summary with errors
        validation_summary = ValidationSummary(
            processed=3,
            skipped=2,
            errors=[
                {"repository": "test/repo1", "error": "consecutive periods in name"},
                {"repository": "test/repo2", "error": "invalid character in name"}
            ]
        )
        
        # Mock the show_fork_data method to return validation summary
        mock_display_service.show_fork_data.return_value = {
            "total_forks": 5,
            "displayed_forks": 3,
            "validation_summary": validation_summary
        }
        
        runner = CliRunner()
        
        # Test show-forks command
        result = runner.invoke(cli, ['show-forks', 'owner/repo'])
        
        # Verify the command completed (may exit with validation error code)
        assert result.exit_code in [0, 1, 2]  # Valid exit codes
        
        # Verify display_validation_summary_with_context was called
        mock_display_service.display_validation_summary_with_context.assert_called_once()
        call_args = mock_display_service.display_validation_summary_with_context.call_args
        
        # Verify the validation summary was passed correctly
        assert call_args[0][0] == validation_summary
        assert call_args[1]['context'] == "fork processing"
        assert call_args[1]['verbose'] is False  # Default verbose_validation is False
        assert call_args[1]['csv_export'] is False

    @patch('forklift.cli.load_config')
    @patch('forklift.cli.validate_repository_url')
    @patch('forklift.cli.GitHubClient')
    @patch('forklift.cli.RepositoryDisplayService')
    def test_show_forks_verbose_validation_flag_integration(
        self, 
        mock_display_service_class,
        mock_github_client_class,
        mock_validate_url,
        mock_load_config
    ):
        """Test that --verbose-validation flag works in integration."""
        # Setup mocks
        mock_config = Mock()
        mock_config.github.token = "test_token"
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("owner", "repo")
        
        # Mock GitHub client
        mock_github_client = Mock()
        mock_github_client_class.return_value = mock_github_client
        
        # Mock display service with validation errors
        mock_display_service = Mock()
        mock_display_service_class.return_value = mock_display_service
        
        # Create validation summary with errors
        validation_summary = ValidationSummary(
            processed=1,
            skipped=1,
            errors=[{"repository": "test/repo", "error": "validation failed"}]
        )
        
        # Mock the show_fork_data method to return validation summary
        mock_display_service.show_fork_data.return_value = {
            "total_forks": 2,
            "displayed_forks": 1,
            "validation_summary": validation_summary
        }
        
        runner = CliRunner()
        
        # Test with --verbose-validation flag
        result = runner.invoke(cli, ['show-forks', 'owner/repo', '--verbose-validation'])
        
        # Verify the command completed
        assert result.exit_code in [0, 1, 2]  # Valid exit codes
        
        # Verify display_validation_summary_with_context was called with verbose=True
        mock_display_service.display_validation_summary_with_context.assert_called_once()
        call_args = mock_display_service.display_validation_summary_with_context.call_args
        assert call_args[1]['verbose'] is True

    @patch('forklift.cli.load_config')
    @patch('forklift.cli.validate_repository_url')
    @patch('forklift.cli.sys.exit')
    def test_cli_exit_codes_for_validation_failures(
        self, 
        mock_sys_exit,
        mock_validate_url,
        mock_load_config
    ):
        """Test that CLI uses appropriate exit codes for validation failures."""
        # Setup mocks
        mock_config = Mock()
        mock_config.github.token = "test_token"
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("owner", "repo")
        
        # Mock the _show_forks_summary function to return validation summary
        with patch('forklift.cli._show_forks_summary') as mock_show_forks:
            # Test partial failure (exit code 1)
            partial_failure_summary = ValidationSummary(
                processed=3,
                skipped=2,
                errors=[
                    {"repository": "test/repo1", "error": "validation failed"},
                    {"repository": "test/repo2", "error": "validation failed"}
                ]
            )
            mock_show_forks.return_value = partial_failure_summary
            
            runner = CliRunner()
            
            with patch('forklift.cli.RepositoryDisplayService'):
                result = runner.invoke(cli, ['show-forks', 'owner/repo'])
                
                # Verify sys.exit was called with code 1 for partial failure
                mock_sys_exit.assert_called_with(1)

    @patch('forklift.cli.load_config')
    @patch('forklift.cli.validate_repository_url')
    def test_cli_no_exit_code_for_successful_processing(
        self, 
        mock_validate_url,
        mock_load_config
    ):
        """Test that CLI doesn't call sys.exit for successful processing."""
        # Setup mocks
        mock_config = Mock()
        mock_config.github.token = "test_token"
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("owner", "repo")
        
        # Mock the _show_forks_summary function to return no validation errors
        with patch('forklift.cli._show_forks_summary') as mock_show_forks:
            success_summary = ValidationSummary(processed=5, skipped=0, errors=[])
            mock_show_forks.return_value = success_summary
            
            runner = CliRunner()
            
            with patch('forklift.cli.RepositoryDisplayService'):
                with patch('forklift.cli.sys.exit') as mock_sys_exit:
                    result = runner.invoke(cli, ['show-forks', 'owner/repo'])
                    
                    # Verify sys.exit was NOT called for successful processing
                    mock_sys_exit.assert_not_called()
                    assert result.exit_code == 0

    @patch('forklift.cli.load_config')
    @patch('forklift.cli.validate_repository_url')
    def test_analyze_command_validation_error_handling(
        self, 
        mock_validate_url,
        mock_load_config
    ):
        """Test that analyze command handles validation errors correctly."""
        # Setup mocks
        mock_config = Mock()
        mock_config.github.token = "test_token"
        mock_config.analysis.min_score_threshold = 50
        mock_config.analysis.max_forks_to_analyze = 100
        mock_config.analysis.auto_pr_enabled = False
        mock_config.dry_run = False
        mock_config.output_format = "markdown"
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("owner", "repo")
        
        # Mock the _run_analysis function to return validation summary
        with patch('forklift.cli._run_analysis') as mock_run_analysis:
            # Create analysis results with validation summary
            validation_summary = ValidationSummary(
                processed=2,
                skipped=1,
                errors=[{"repository": "test/repo", "error": "validation failed"}]
            )
            
            mock_results = {
                "repository": "owner/repo",
                "total_forks": 3,
                "analyzed_forks": 2,
                "validation_summary": validation_summary
            }
            mock_run_analysis.return_value = mock_results
            
            runner = CliRunner()
            
            with patch('forklift.cli.RepositoryDisplayService') as mock_display_service_class:
                mock_display_service = Mock()
                mock_display_service_class.return_value = mock_display_service
                
                with patch('forklift.cli.sys.exit') as mock_sys_exit:
                    result = runner.invoke(cli, ['analyze', 'owner/repo'])
                    
                    # Verify display_validation_summary_with_context was called
                    mock_display_service.display_validation_summary_with_context.assert_called_once()
                    call_args = mock_display_service.display_validation_summary_with_context.call_args
                    assert call_args[0][0] == validation_summary
                    assert call_args[1]['context'] == "repository analysis"
                    
                    # Verify sys.exit was called with appropriate code
                    mock_sys_exit.assert_called_with(1)  # Partial failure