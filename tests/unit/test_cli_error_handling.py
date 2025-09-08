"""Tests for CLI error handling and user messaging improvements."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from click.testing import CliRunner

from forklift.cli import cli, _handle_cli_error_with_context, _get_validation_error_exit_code
from forklift.exceptions import (
    ForkliftValidationError,
    ForkliftAuthenticationError,
    ForkliftNetworkError,
    ErrorHandler
)
from forklift.models.validation_handler import ValidationSummary


class TestCLIErrorHandling:
    """Test CLI error handling improvements."""

    def test_handle_cli_error_with_context_validation_error(self):
        """Test enhanced validation error handling."""
        error_handler = Mock(spec=ErrorHandler)
        error = ForkliftValidationError("repository name validation failed")
        
        _handle_cli_error_with_context(
            error_handler, error, "test context", verbose_validation=True
        )
        
        # Verify enhanced error message was created
        error_handler.handle_error.assert_called_once()
        call_args = error_handler.handle_error.call_args
        enhanced_error = call_args[0][0]
        context = call_args[0][1]
        
        assert isinstance(enhanced_error, ForkliftValidationError)
        assert "repository name validation failed" in str(enhanced_error)
        assert "unusual characters" in str(enhanced_error)
        assert "Troubleshooting tips" in str(enhanced_error)
        assert context == "test context"

    def test_handle_cli_error_with_context_authentication_error(self):
        """Test enhanced authentication error handling."""
        error_handler = Mock(spec=ErrorHandler)
        error = ForkliftAuthenticationError("token invalid")
        
        _handle_cli_error_with_context(
            error_handler, error, "test context", verbose_validation=False
        )
        
        # Verify enhanced error message was created
        error_handler.handle_error.assert_called_once()
        call_args = error_handler.handle_error.call_args
        enhanced_error = call_args[0][0]
        
        assert isinstance(enhanced_error, ForkliftAuthenticationError)
        assert "token invalid" in str(enhanced_error)
        assert "forklift configure" in str(enhanced_error)
        assert "permissions" in str(enhanced_error)

    def test_handle_cli_error_with_context_network_error(self):
        """Test enhanced network error handling."""
        error_handler = Mock(spec=ErrorHandler)
        error = ForkliftNetworkError("connection timeout")
        
        _handle_cli_error_with_context(
            error_handler, error, "test context", verbose_validation=False
        )
        
        # Verify enhanced error message was created
        error_handler.handle_error.assert_called_once()
        call_args = error_handler.handle_error.call_args
        enhanced_error = call_args[0][0]
        
        assert isinstance(enhanced_error, ForkliftNetworkError)
        assert "connection timeout" in str(enhanced_error)
        assert "internet connection" in str(enhanced_error)
        assert "temporary issue" in str(enhanced_error)

    def test_get_validation_error_exit_code_no_errors(self):
        """Test exit code determination with no validation errors."""
        validation_summary = ValidationSummary(processed=5, skipped=0, errors=[])
        exit_code = _get_validation_error_exit_code(validation_summary)
        assert exit_code == 0

    def test_get_validation_error_exit_code_partial_success(self):
        """Test exit code determination with partial success."""
        validation_summary = ValidationSummary(
            processed=3, 
            skipped=2, 
            errors=[
                {"repository": "test/repo1", "error": "validation failed"},
                {"repository": "test/repo2", "error": "validation failed"}
            ]
        )
        exit_code = _get_validation_error_exit_code(validation_summary)
        assert exit_code == 1

    def test_get_validation_error_exit_code_complete_failure(self):
        """Test exit code determination with complete failure."""
        validation_summary = ValidationSummary(
            processed=0, 
            skipped=3, 
            errors=[
                {"repository": "test/repo1", "error": "validation failed"},
                {"repository": "test/repo2", "error": "validation failed"},
                {"repository": "test/repo3", "error": "validation failed"}
            ]
        )
        exit_code = _get_validation_error_exit_code(validation_summary)
        assert exit_code == 2

    def test_get_validation_error_exit_code_none_summary(self):
        """Test exit code determination with None validation summary."""
        exit_code = _get_validation_error_exit_code(None)
        assert exit_code == 0


class TestCLIVerboseValidationFlag:
    """Test --verbose-validation flag functionality."""

    @patch('forklift.cli.asyncio.run')
    @patch('forklift.cli.validate_repository_url')
    @patch('forklift.cli.load_config')
    def test_show_forks_verbose_validation_flag(self, mock_load_config, mock_validate_url, mock_asyncio_run):
        """Test that --verbose-validation flag is passed through correctly."""
        # Setup mocks
        mock_config = Mock()
        mock_config.github.token = "test_token"
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("owner", "repo")
        
        # Mock validation summary with errors
        mock_validation_summary = ValidationSummary(
            processed=1,
            skipped=1,
            errors=[{"repository": "test/repo", "error": "validation failed"}]
        )
        mock_asyncio_run.return_value = mock_validation_summary
        
        runner = CliRunner()
        
        # Test with --verbose-validation flag
        with patch('forklift.cli.RepositoryDisplayService') as mock_display_service:
            mock_display_instance = Mock()
            mock_display_service.return_value = mock_display_instance
            
            result = runner.invoke(cli, [
                'show-forks', 
                'owner/repo', 
                '--verbose-validation'
            ])
            
            # Verify the flag was processed
            assert result.exit_code in [0, 1, 2]  # Valid exit codes
            
            # Verify display_validation_summary_with_context was called with verbose=True
            mock_display_instance.display_validation_summary_with_context.assert_called_once()
            call_args = mock_display_instance.display_validation_summary_with_context.call_args
            assert call_args[1]['verbose'] is True

    @patch('forklift.cli.asyncio.run')
    @patch('forklift.cli.validate_repository_url')
    @patch('forklift.cli.load_config')
    def test_analyze_verbose_validation_flag(self, mock_load_config, mock_validate_url, mock_asyncio_run):
        """Test that --verbose-validation flag works in analyze command."""
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
        
        # Mock analysis results with validation summary
        mock_results = {
            "repository": "owner/repo",
            "total_forks": 5,
            "analyzed_forks": 3,
            "validation_summary": ValidationSummary(
                processed=3,
                skipped=2,
                errors=[
                    {"repository": "test/repo1", "error": "validation failed"},
                    {"repository": "test/repo2", "error": "validation failed"}
                ]
            )
        }
        mock_asyncio_run.return_value = mock_results
        
        runner = CliRunner()
        
        # Test with --verbose-validation flag
        with patch('forklift.cli.RepositoryDisplayService') as mock_display_service:
            mock_display_instance = Mock()
            mock_display_service.return_value = mock_display_instance
            
            result = runner.invoke(cli, [
                'analyze', 
                'owner/repo', 
                '--verbose-validation'
            ])
            
            # Verify the flag was processed
            assert result.exit_code in [0, 1, 2]  # Valid exit codes
            
            # Verify display_validation_summary_with_context was called with verbose=True
            mock_display_instance.display_validation_summary_with_context.assert_called_once()
            call_args = mock_display_instance.display_validation_summary_with_context.call_args
            assert call_args[1]['verbose'] is True


class TestCLIExitCodes:
    """Test proper exit codes for different failure scenarios."""

    @patch('forklift.cli.sys.exit')
    @patch('forklift.cli.asyncio.run')
    @patch('forklift.cli.validate_repository_url')
    @patch('forklift.cli.load_config')
    def test_show_forks_exit_code_partial_failure(self, mock_load_config, mock_validate_url, mock_asyncio_run, mock_sys_exit):
        """Test exit code 1 for partial validation failures."""
        # Setup mocks
        mock_config = Mock()
        mock_config.github.token = "test_token"
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("owner", "repo")
        
        # Mock validation summary with partial failure
        mock_validation_summary = ValidationSummary(
            processed=3,
            skipped=2,
            errors=[
                {"repository": "test/repo1", "error": "validation failed"},
                {"repository": "test/repo2", "error": "validation failed"}
            ]
        )
        mock_asyncio_run.return_value = mock_validation_summary
        
        runner = CliRunner()
        
        with patch('forklift.cli.RepositoryDisplayService'):
            result = runner.invoke(cli, ['show-forks', 'owner/repo'])
            
            # Verify sys.exit was called with code 1 for partial failure
            mock_sys_exit.assert_called_with(1)

    @patch('forklift.cli.sys.exit')
    @patch('forklift.cli.asyncio.run')
    @patch('forklift.cli.validate_repository_url')
    @patch('forklift.cli.load_config')
    def test_show_forks_exit_code_complete_failure(self, mock_load_config, mock_validate_url, mock_asyncio_run, mock_sys_exit):
        """Test exit code 2 for complete validation failures."""
        # Setup mocks
        mock_config = Mock()
        mock_config.github.token = "test_token"
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("owner", "repo")
        
        # Mock validation summary with complete failure
        mock_validation_summary = ValidationSummary(
            processed=0,
            skipped=5,
            errors=[
                {"repository": "test/repo1", "error": "validation failed"},
                {"repository": "test/repo2", "error": "validation failed"},
                {"repository": "test/repo3", "error": "validation failed"},
                {"repository": "test/repo4", "error": "validation failed"},
                {"repository": "test/repo5", "error": "validation failed"}
            ]
        )
        mock_asyncio_run.return_value = mock_validation_summary
        
        runner = CliRunner()
        
        with patch('forklift.cli.RepositoryDisplayService'):
            result = runner.invoke(cli, ['show-forks', 'owner/repo'])
            
            # Verify sys.exit was called with code 2 for complete failure
            mock_sys_exit.assert_called_with(2)