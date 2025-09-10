"""Unit tests for repository display service validation summary functionality."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from io import StringIO
import sys

from forkscout.display.repository_display_service import RepositoryDisplayService
from forkscout.models.validation_handler import ValidationSummary
from forkscout.models.github import Repository
from rich.console import Console


class TestRepositoryDisplayServiceValidationSummary:
    """Test validation summary display functionality."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return AsyncMock()

    @pytest.fixture
    def display_service(self, mock_github_client):
        """Create a display service instance for testing."""
        return RepositoryDisplayService(
            github_client=mock_github_client,
            console=Console(file=StringIO(), width=80)
        )

    @pytest.fixture
    def validation_summary_with_errors(self):
        """Create a validation summary with errors for testing."""
        return ValidationSummary(
            processed=3,
            skipped=2,
            errors=[
                {
                    "repository": "user1/repo..with..periods",
                    "error": "GitHub names cannot contain consecutive periods",
                    "data": {"full_name": "user1/repo..with..periods"}
                },
                {
                    "repository": "user2/.invalid-start",
                    "error": "GitHub names cannot start or end with a period",
                    "data": {"full_name": "user2/.invalid-start"}
                }
            ]
        )

    @pytest.fixture
    def validation_summary_no_errors(self):
        """Create a validation summary with no errors for testing."""
        return ValidationSummary(
            processed=5,
            skipped=0,
            errors=[]
        )

    def test_display_validation_summary_no_errors(self, display_service, validation_summary_no_errors):
        """Test that no output is generated when there are no validation errors."""
        # Capture console output
        output = StringIO()
        display_service.console = Console(file=output, width=80)
        
        # Display validation summary
        display_service.display_validation_summary(validation_summary_no_errors)
        
        # Should produce no output
        assert output.getvalue() == ""

    def test_display_validation_summary_with_errors(self, display_service, validation_summary_with_errors):
        """Test validation summary display with errors."""
        # Capture console output
        output = StringIO()
        display_service.console = Console(file=output, width=80)
        
        # Display validation summary
        display_service.display_validation_summary(validation_summary_with_errors)
        
        # Check output contains expected elements
        output_text = output.getvalue()
        assert "Validation Issues Encountered" in output_text
        assert "2 repositories skipped due to validation errors" in output_text
        assert "3 repositories processed successfully" in output_text
        assert "5 total repositories processed" in output_text
        assert "Use --verbose flag to see detailed validation errors" in output_text

    def test_display_validation_summary_verbose(self, display_service, validation_summary_with_errors):
        """Test verbose validation summary display."""
        # Capture console output
        output = StringIO()
        display_service.console = Console(file=output, width=80)
        
        # Display validation summary with verbose flag
        display_service.display_validation_summary(validation_summary_with_errors, verbose=True)
        
        # Check output contains detailed error information
        output_text = output.getvalue()
        assert "Detailed Validation Errors:" in output_text
        assert "user1/repo..with..periods" in output_text
        assert "user2/.invalid-start" in output_text
        assert "consecutive p" in output_text.lower()  # Truncated in table
        assert "Actionable Information:" in output_text

    def test_display_validation_summary_csv_export(self, display_service, validation_summary_with_errors):
        """Test validation summary display in CSV export mode."""
        # Capture stderr output
        stderr_output = StringIO()
        
        with patch('sys.stderr', stderr_output):
            # Display validation summary in CSV export mode
            display_service.display_validation_summary(validation_summary_with_errors, csv_export=True)
        
        # Check that output went to stderr
        stderr_text = stderr_output.getvalue()
        assert "Validation Issues Encountered" in stderr_text
        assert "2 repositories skipped due to validation errors" in stderr_text

    def test_display_validation_summary_with_context(self, display_service, validation_summary_with_errors):
        """Test validation summary display with context."""
        # Capture console output
        output = StringIO()
        display_service.console = Console(file=output, width=80)
        
        # Display validation summary with context
        display_service.display_validation_summary_with_context(
            validation_summary_with_errors,
            "fork processing"
        )
        
        # Check output contains context information
        output_text = output.getvalue()
        assert "Validation Issues During Fork Processing" in output_text
        assert "3 repositories processed successfully" in output_text
        assert "2 repositories skipped due to validation errors" in output_text
        assert "Success rate: 60.0% (3/5)" in output_text

    def test_display_detailed_validation_errors(self, display_service, validation_summary_with_errors):
        """Test detailed validation error display."""
        # Capture console output
        output = StringIO()
        display_service.console = Console(file=output, width=80)
        
        # Display detailed validation errors
        display_service._display_detailed_validation_errors(
            validation_summary_with_errors.errors,
            display_service.console
        )
        
        # Check output contains detailed error table
        output_text = output.getvalue()
        assert "Detailed Validation Errors:" in output_text
        assert "user1/repo..with..periods" in output_text
        assert "user2/.invalid-start" in output_text
        assert "Consec" in output_text  # Truncated in table
        assert "Leadin" in output_text  # Truncated in table
        assert "Actionable Information:" in output_text

    def test_display_detailed_validation_errors_truncation(self, display_service):
        """Test that long error messages are truncated in detailed display."""
        # Create validation errors with long messages
        long_errors = [
            {
                "repository": "user/repo",
                "error": "This is a very long error message that should be truncated because it exceeds the maximum length for table display and would make the table unreadable",
                "data": {}
            }
        ]
        
        # Capture console output
        output = StringIO()
        display_service.console = Console(file=output, width=80)
        
        # Display detailed validation errors
        display_service._display_detailed_validation_errors(
            long_errors,
            display_service.console
        )
        
        # Check that error message was truncated (Rich truncates automatically)
        output_text = output.getvalue()
        # The message should be present but may be truncated by Rich table formatting
        assert "This is a very long error message that should be t" in output_text

    def test_display_detailed_validation_errors_max_limit(self, display_service):
        """Test that detailed error display respects maximum error limit."""
        # Create more errors than the default maximum
        many_errors = [
            {
                "repository": f"user{i}/repo{i}",
                "error": f"Error {i}",
                "data": {}
            }
            for i in range(15)  # More than default max of 10
        ]
        
        # Capture console output
        output = StringIO()
        display_service.console = Console(file=output, width=80)
        
        # Display detailed validation errors
        display_service._display_detailed_validation_errors(
            many_errors,
            display_service.console,
            max_errors=10
        )
        
        # Check that only 10 errors are shown plus summary
        output_text = output.getvalue()
        assert "... and 5 more validation errors" in output_text
        
        # Count actual error rows (should be 10)
        error_count = sum(1 for line in output_text.split('\n') if 'user' in line and 'repo' in line and 'Error' in line)
        assert error_count == 10

    def test_error_type_categorization(self, display_service):
        """Test that validation errors are correctly categorized by type."""
        # Create errors of different types
        mixed_errors = [
            {
                "repository": "user1/repo..periods",
                "error": "GitHub names cannot contain consecutive periods",
                "data": {}
            },
            {
                "repository": "user2/.leading",
                "error": "GitHub names cannot start or end with a period",
                "data": {}
            },
            {
                "repository": "user3/invalid@name",
                "error": "Invalid GitHub name format",
                "data": {}
            },
            {
                "repository": "user4/unknown",
                "error": "Some other validation error",
                "data": {}
            }
        ]
        
        # Capture console output
        output = StringIO()
        display_service.console = Console(file=output, width=80)
        
        # Display detailed validation errors
        display_service._display_detailed_validation_errors(
            mixed_errors,
            display_service.console
        )
        
        # Check that error types are correctly categorized (may be truncated in table)
        output_text = output.getvalue()
        assert "Consec" in output_text  # Truncated "Consecutive Periods"
        assert "Leadin" in output_text  # Truncated "Leading/Trailing"
        assert "Invali" in output_text  # Truncated "Invalid Format"
        assert "Other" in output_text

    def test_validation_summary_error_type_analysis(self, display_service):
        """Test that validation summary analyzes and displays error types."""
        # Create validation summary with mixed error types
        validation_summary = ValidationSummary(
            processed=2,
            skipped=4,
            errors=[
                {
                    "repository": "user1/repo..periods",
                    "error": "GitHub names cannot contain consecutive periods",
                    "data": {}
                },
                {
                    "repository": "user2/repo..more..periods",
                    "error": "GitHub names cannot contain consecutive periods",
                    "data": {}
                },
                {
                    "repository": "user3/.leading",
                    "error": "GitHub names cannot start or end with a period",
                    "data": {}
                },
                {
                    "repository": "user4/invalid@name",
                    "error": "Invalid GitHub name format",
                    "data": {}
                }
            ]
        )
        
        # Capture console output
        output = StringIO()
        display_service.console = Console(file=output, width=80)
        
        # Display validation summary (non-verbose)
        display_service.display_validation_summary(validation_summary)
        
        # Check that error type analysis is shown
        output_text = output.getvalue()
        assert "Common validation issues:" in output_text
        assert "Repository names with consecutive periods: 2 repositories" in output_text
        assert "Repository names with leading/trailing periods: 1 repositories" in output_text
        assert "Invalid repository name format: 1 repositories" in output_text

    @pytest.mark.asyncio
    async def test_show_forks_with_validation_summary_success(self, display_service, mock_github_client):
        """Test show_forks_with_validation_summary with successful processing."""
        # Mock the collect_detailed_fork_data_with_validation method
        mock_fork_data = Mock()
        mock_fork_data.metrics.name = "test-fork"
        mock_fork_data.metrics.owner = "test-owner"
        mock_fork_data.metrics.stargazers_count = 5
        mock_fork_data.metrics.pushed_at = None
        
        validation_summary = ValidationSummary(processed=1, skipped=0, errors=[])
        
        with patch.object(display_service, 'collect_detailed_fork_data_with_validation') as mock_collect:
            mock_collect.return_value = ([mock_fork_data], validation_summary)
            
            # Test the method
            result = await display_service.show_forks_with_validation_summary("owner/repo")
            
            # Verify results
            assert result["total_forks"] == 1
            assert result["processed_forks"] == 1
            assert result["skipped_forks"] == 0
            assert len(result["collected_forks"]) == 1

    @pytest.mark.asyncio
    async def test_show_forks_with_validation_summary_with_errors(self, display_service, mock_github_client):
        """Test show_forks_with_validation_summary with validation errors."""
        # Mock the collect_detailed_fork_data_with_validation method
        validation_summary = ValidationSummary(
            processed=1,
            skipped=1,
            errors=[
                {
                    "repository": "user/repo..periods",
                    "error": "GitHub names cannot contain consecutive periods",
                    "data": {}
                }
            ]
        )
        
        mock_fork_data = Mock()
        mock_fork_data.metrics.name = "valid-fork"
        mock_fork_data.metrics.owner = "test-owner"
        mock_fork_data.metrics.stargazers_count = 3
        mock_fork_data.metrics.pushed_at = None
        
        with patch.object(display_service, 'collect_detailed_fork_data_with_validation') as mock_collect:
            mock_collect.return_value = ([mock_fork_data], validation_summary)
            
            # Capture console output
            output = StringIO()
            display_service.console = Console(file=output, width=80)
            
            # Test the method
            result = await display_service.show_forks_with_validation_summary("owner/repo")
            
            # Verify results
            assert result["total_forks"] == 2
            assert result["processed_forks"] == 1
            assert result["skipped_forks"] == 1
            assert len(result["collected_forks"]) == 1
            
            # Check that validation summary was displayed
            output_text = output.getvalue()
            assert "Validation Issues During Fork Processing" in output_text

    @pytest.mark.asyncio
    async def test_show_forks_with_validation_summary_csv_export(self, display_service, mock_github_client):
        """Test show_forks_with_validation_summary in CSV export mode."""
        # Mock the collect_detailed_fork_data_with_validation method
        mock_fork_data = Mock()
        mock_fork_data.metrics.name = "test-fork"
        mock_fork_data.metrics.owner = "test-owner"
        mock_fork_data.metrics.stargazers_count = 5
        mock_fork_data.metrics.pushed_at = None
        
        validation_summary = ValidationSummary(
            processed=1,
            skipped=1,
            errors=[{"repository": "user/invalid", "error": "test error", "data": {}}]
        )
        
        with patch.object(display_service, 'collect_detailed_fork_data_with_validation') as mock_collect:
            mock_collect.return_value = ([mock_fork_data], validation_summary)
            
            # Capture stdout and stderr
            stdout_output = StringIO()
            stderr_output = StringIO()
            
            with patch('sys.stdout', stdout_output), patch('sys.stderr', stderr_output):
                # Test the method in CSV export mode
                result = await display_service.show_forks_with_validation_summary(
                    "owner/repo", 
                    csv_export=True
                )
            
            # Verify CSV output went to stdout
            stdout_text = stdout_output.getvalue()
            assert "fork_name,owner,stars,last_activity" in stdout_text
            assert "test-fork,test-owner,5," in stdout_text
            
            # Verify validation summary went to stderr
            stderr_text = stderr_output.getvalue()
            assert "Validation Issues During Fork Processing" in stderr_text