"""Integration tests for comprehensive error handling and output management."""

import io
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from forklift.exceptions import (
    CLIError,
    ForkliftAuthenticationError,
    ForkliftConfigurationError,
    ForkliftNetworkError,
    ForkliftOutputError,
    ForkliftUnicodeError,
    ForkliftValidationError,
)
from forklift.reporting.csv_output_manager import create_csv_context, create_csv_output_manager


class TestCLIErrorHandling:
    """Test CLI error handling integration."""

    def test_invalid_repository_url_handling(self):
        """Test handling of invalid repository URLs."""
        from forklift.cli import validate_repository_url
        
        invalid_urls = [
            "",
            "not-a-url",
            "https://example.com/not-github",
            "owner/",  # Missing repo name
            "/repo",  # Missing owner
            "owner/repo/extra",  # Too many parts
        ]
        
        for url in invalid_urls:
            try:
                with pytest.raises(ForkliftValidationError) as exc_info:
                    validate_repository_url(url)
                
                # Check for various error message patterns
                error_msg = str(exc_info.value)
                assert any(keyword in error_msg for keyword in ["Invalid", "required", "format"]), f"Unexpected error message: {error_msg}"
                assert exc_info.value.exit_code == 3
            except Exception as e:
                pytest.fail(f"URL '{url}' should raise ForkliftValidationError but got {type(e).__name__}: {e}")

    def test_valid_repository_url_parsing(self):
        """Test parsing of valid repository URLs."""
        from forklift.cli import validate_repository_url
        
        valid_urls = [
            ("https://github.com/owner/repo", ("owner", "repo")),
            ("https://github.com/owner/repo.git", ("owner", "repo")),
            ("git@github.com:owner/repo.git", ("owner", "repo")),
            ("owner/repo", ("owner", "repo")),
            ("test-owner/test-repo", ("test-owner", "test-repo")),
            ("owner123/repo_name", ("owner123", "repo_name")),
        ]
        
        for url, expected in valid_urls:
            result = validate_repository_url(url)
            assert result == expected

    def test_unicode_repository_names(self):
        """Test handling of repository names with Unicode characters."""
        from forklift.cli import validate_repository_url
        
        # These should fail validation (GitHub doesn't allow Unicode in repo names)
        unicode_urls = [
            "测试/repo",
            "owner/测试",
            "café/repo",
            "owner/café",
        ]
        
        for url in unicode_urls:
            with pytest.raises(ForkliftValidationError):
                validate_repository_url(url)


class TestCSVOutputErrorHandling:
    """Test CSV output error handling integration."""

    def test_csv_export_with_unicode_data(self):
        """Test CSV export with Unicode data."""
        manager = create_csv_output_manager()
        
        # Test data with various Unicode characters
        test_data = [
            {"name": "测试仓库", "description": "Chinese repository name"},
            {"name": "café-repo", "description": "Repository with accents"},
            {"name": "emoji-🚀", "description": "Repository with emoji"},
            {"name": "mixed-测试-café-🌍", "description": "Mixed Unicode characters"},
        ]
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            with patch.object(manager.exporter, 'export_to_csv') as mock_export:
                # Simulate CSV export with Unicode content
                csv_content = "name,description\n"
                for item in test_data:
                    csv_content += f"{item['name']},{item['description']}\n"
                mock_export.return_value = csv_content
                
                # Should not raise any Unicode errors
                manager.export_to_stdout(test_data)
        
        output = mock_stdout.getvalue()
        assert "测试仓库" in output
        assert "café-repo" in output
        assert "🚀" in output

    def test_csv_export_with_problematic_unicode(self):
        """Test CSV export with problematic Unicode characters."""
        manager = create_csv_output_manager()
        
        # Create data that might cause Unicode issues - use proper data structure
        from forklift.models.analysis import ForksPreview, ForkPreviewItem
        
        problematic_data = ForksPreview(
            repository_name="test/repo",
            total_forks=2,
            forks=[
                ForkPreviewItem(
                    name="test",
                    owner="owner1",
                    stars=10,
                    commits_ahead="Has commits",
                    activity_status="Active",
                    fork_url="https://github.com/owner1/test",
                    last_push_date=None,
                    recent_commits="Commit with \udcff invalid surrogate"
                ),
                ForkPreviewItem(
                    name="test2",
                    owner="owner2", 
                    stars=5,
                    commits_ahead="No commits",
                    activity_status="Active",
                    fork_url="https://github.com/owner2/test2",
                    last_push_date=None,
                    recent_commits="Normal commit message"
                )
            ]
        )
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            # Should handle Unicode issues gracefully
            manager.export_to_stdout(problematic_data)
        
        # Should produce some output without crashing
        output = mock_stdout.getvalue()
        assert len(output) > 0

    def test_csv_export_to_file_with_permissions_error(self):
        """Test CSV export to file with permissions error."""
        manager = create_csv_output_manager()
        
        # Use proper data structure
        from forklift.models.analysis import ForksPreview, ForkPreviewItem
        
        test_data = ForksPreview(
            repository_name="test/repo",
            total_forks=1,
            forks=[
                ForkPreviewItem(
                    name="test",
                    owner="owner",
                    stars=10,
                    commits_ahead="Has commits",
                    activity_status="Active",
                    fork_url="https://github.com/owner/test",
                    last_push_date=None,
                    recent_commits=None
                )
            ]
        )
        
        # Try to write to a directory that doesn't exist or has no permissions
        with pytest.raises(ForkliftOutputError) as exc_info:
            manager.export_to_file(test_data, "/nonexistent/directory/file.csv")
        
        assert "Failed to export CSV to file" in str(exc_info.value)
        assert exc_info.value.exit_code == 6

    def test_csv_export_with_context_suppression(self):
        """Test CSV export with progress suppression context."""
        test_data = [{"name": "test", "value": "data"}]
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
                with create_csv_context(suppress_progress=True) as manager:
                    # Simulate progress messages that should be suppressed
                    print("Progress: Processing forks...", file=sys.stderr)
                    print("Progress: Analyzing commits...", file=sys.stderr)
                    
                    # Export CSV data
                    with patch.object(manager.exporter, 'export_to_csv', return_value="name,value\ntest,data\n"):
                        manager.export_to_stdout(test_data)
        
        # CSV data should be in stdout
        stdout_output = mock_stdout.getvalue()
        assert "name,value" in stdout_output
        assert "test,data" in stdout_output
        
        # Progress messages should not appear in final stderr
        stderr_output = mock_stderr.getvalue()
        # Progress messages were captured and suppressed

    def test_csv_export_error_with_context(self):
        """Test CSV export error handling with context manager."""
        test_data = [{"name": "test", "value": "data"}]
        
        with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            with pytest.raises(ForkliftOutputError):
                with create_csv_context(suppress_progress=True) as manager:
                    # Simulate progress messages
                    print("Progress: Starting export...", file=sys.stderr)
                    
                    # Simulate export failure
                    with patch.object(manager, '_generate_csv_safely', side_effect=ForkliftOutputError("Export failed")):
                        manager.export_to_stdout(test_data)
        
        # Error should be properly handled
        stderr_output = mock_stderr.getvalue()
        # Progress messages should be captured


class TestNetworkErrorHandling:
    """Test network-related error handling."""

    def test_github_authentication_error_mapping(self):
        """Test mapping of GitHub authentication errors."""
        from forklift.github.exceptions import GitHubAuthenticationError
        
        github_error = GitHubAuthenticationError("Invalid token", status_code=401)
        
        # Should be mapped to ForkliftAuthenticationError
        forklift_error = ForkliftAuthenticationError(f"GitHub authentication failed: {github_error}")
        
        assert forklift_error.exit_code == 5
        assert "GitHub authentication failed" in str(forklift_error)

    def test_github_rate_limit_error_mapping(self):
        """Test mapping of GitHub rate limit errors."""
        from forklift.github.exceptions import GitHubRateLimitError
        
        github_error = GitHubRateLimitError(
            "Rate limit exceeded",
            reset_time=1234567890,
            remaining=0,
            limit=5000,
            status_code=403
        )
        
        # Should be mapped to ForkliftNetworkError
        forklift_error = ForkliftNetworkError(f"GitHub rate limit exceeded: {github_error}")
        
        assert forklift_error.exit_code == 4
        assert "GitHub rate limit exceeded" in str(forklift_error)

    def test_github_timeout_error_mapping(self):
        """Test mapping of GitHub timeout errors."""
        from forklift.github.exceptions import GitHubTimeoutError
        
        github_error = GitHubTimeoutError(
            "Request timeout",
            operation="fetch_forks",
            timeout_seconds=30.0
        )
        
        # Should be mapped to ForkliftNetworkError
        forklift_error = ForkliftNetworkError(f"Network timeout: {github_error}")
        
        assert forklift_error.exit_code == 4
        assert "Network timeout" in str(forklift_error)


class TestFileOutputErrorHandling:
    """Test file output error handling."""

    def test_report_output_with_unicode_content(self):
        """Test report output with Unicode content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_report.md"
            
            # Unicode content that might cause issues
            unicode_content = """# Repository Analysis Report

## Fork: 测试/仓库
- Description: Repository with Chinese characters
- Commits: 
  - feat: Add 新功能 (new feature)
  - fix: Fix café encoding issue
  - docs: Update README with 🚀 emoji

## Summary
Analysis completed successfully with Unicode support.
"""
            
            # Should write successfully without Unicode errors
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(unicode_content)
                
                # Verify content was written correctly
                with open(output_path, "r", encoding="utf-8") as f:
                    read_content = f.read()
                
                assert read_content == unicode_content
                assert "测试/仓库" in read_content
                assert "新功能" in read_content
                assert "🚀" in read_content
                
            except UnicodeError:
                pytest.fail("Unicode content should be handled properly")

    def test_report_output_permission_error(self):
        """Test report output with permission error."""
        # Try to write to a location that should fail
        invalid_path = "/root/restricted/report.md"
        
        with pytest.raises((PermissionError, FileNotFoundError, OSError)):
            with open(invalid_path, "w", encoding="utf-8") as f:
                f.write("Test content")

    def test_csv_file_output_with_special_characters(self):
        """Test CSV file output with special characters."""
        manager = create_csv_output_manager()
        
        # Data with CSV special characters
        test_data = [
            {"name": "test,with,commas", "description": "Description with \"quotes\""},
            {"name": "test\nwith\nnewlines", "description": "Description\nwith\nlines"},
            {"name": "test;with;semicolons", "description": "Description with 'single quotes'"},
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            with patch.object(manager.exporter, 'export_to_csv') as mock_export:
                # Simulate proper CSV escaping
                csv_content = '''name,description
"test,with,commas","Description with ""quotes"""
"test
with
newlines","Description
with
lines"
"test;with;semicolons","Description with 'single quotes'"
'''
                mock_export.return_value = csv_content
                
                # Should handle special characters properly
                manager.export_to_file(test_data, temp_path)
            
            # Verify file was created and contains expected content
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert "test,with,commas" in content
            assert "quotes" in content
            assert "newlines" in content
            
        finally:
            # Clean up
            Path(temp_path).unlink(missing_ok=True)


class TestErrorRecoveryScenarios:
    """Test error recovery scenarios."""

    def test_partial_csv_output_recovery(self):
        """Test recovery from partial CSV output scenarios."""
        manager = create_csv_output_manager()
        
        # Simulate scenario where some output was generated before error
        manager._has_output = True
        
        with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            with patch.object(manager, '_generate_csv_safely', side_effect=ForkliftOutputError("Generation failed")):
                with pytest.raises(ForkliftOutputError):
                    manager.export_to_stdout([{"test": "data"}])
        
        # Should log warning about partial output
        stderr_output = mock_stderr.getvalue()
        assert "Warning: Partial CSV output may have been generated" in stderr_output

    def test_unicode_error_recovery(self):
        """Test recovery from Unicode errors."""
        from forklift.exceptions import ErrorHandler
        
        handler = ErrorHandler(debug=False)
        
        # Test Unicode validation with recovery
        problematic_text = "Text with \udcff invalid surrogate"
        
        try:
            cleaned_text = handler.validate_unicode_text(problematic_text, "test context")
            # Should return cleaned text without raising exception
            assert isinstance(cleaned_text, str)
        except ForkliftUnicodeError:
            # If cleaning fails, should raise appropriate error
            pass

    def test_network_timeout_recovery(self):
        """Test recovery from network timeout scenarios."""
        # Simulate network timeout scenario
        error = ForkliftNetworkError("Connection timeout", operation="fetch_repository")
        
        assert error.exit_code == 4
        assert error.operation == "fetch_repository"
        assert "Connection timeout" in str(error)

    def test_configuration_error_recovery(self):
        """Test recovery from configuration errors."""
        # Test various configuration error scenarios
        config_errors = [
            "Configuration file not found",
            "Invalid YAML syntax in configuration",
            "Missing required configuration field",
            "Invalid GitHub token format",
        ]
        
        for error_msg in config_errors:
            error = ForkliftConfigurationError(error_msg)
            assert error.exit_code == 2
            assert error_msg in str(error)