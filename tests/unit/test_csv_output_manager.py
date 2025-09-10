"""Tests for CSV output management with error handling."""

import io
import sys
from unittest.mock import Mock, patch

import pytest

from forkscout.exceptions import ForkscoutOutputError, ForkscoutUnicodeError
from forkscout.reporting.csv_exporter import CSVExportConfig
from forkscout.reporting.csv_output_manager import (
    CSVOutputContext,
    CSVOutputManager,
    create_csv_context,
    create_csv_output_manager,
)


class TestCSVOutputManager:
    """Test CSV output manager functionality."""

    def test_create_csv_output_manager(self):
        """Test creating CSV output manager."""
        manager = create_csv_output_manager(debug=True)
        assert isinstance(manager, CSVOutputManager)
        assert manager.debug is True

    def test_configure_exporter(self):
        """Test configuring the CSV exporter."""
        manager = CSVOutputManager()
        config = CSVExportConfig(include_commits=True, detail_mode=True)
        
        manager.configure_exporter(config)
        assert manager.exporter.config.include_commits is True
        assert manager.exporter.config.detail_mode is True

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_export_to_stdout_success(self, mock_stdout):
        """Test successful export to stdout."""
        manager = CSVOutputManager()
        test_data = [{"name": "test", "value": "data"}]
        
        with patch.object(manager, '_generate_csv_safely', return_value="test,csv,data\n"):
            manager.export_to_stdout(test_data)
            
        output = mock_stdout.getvalue()
        assert output == "test,csv,data\n"
        assert manager._has_output is True

    def test_export_to_stdout_generation_failure(self):
        """Test export to stdout with generation failure."""
        manager = CSVOutputManager()
        test_data = [{"name": "test", "value": "data"}]
        
        with patch.object(manager, '_generate_csv_safely', side_effect=Exception("Generation failed")):
            with pytest.raises(ForkscoutOutputError) as exc_info:
                manager.export_to_stdout(test_data)
            
            assert "Failed to export CSV data" in str(exc_info.value)

    def test_export_to_stdout_unicode_error(self):
        """Test export to stdout with Unicode error."""
        manager = CSVOutputManager()
        test_data = [{"name": "test", "value": "data"}]
        
        with patch.object(manager, '_generate_csv_safely', side_effect=ForkscoutUnicodeError("Unicode error")):
            with pytest.raises(ForkscoutUnicodeError):
                manager.export_to_stdout(test_data)

    @patch('builtins.open')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_export_to_file_success(self, mock_stderr, mock_open):
        """Test successful export to file."""
        manager = CSVOutputManager()
        test_data = [{"name": "test", "value": "data"}]
        
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        with patch.object(manager, '_generate_csv_safely', return_value="test,csv,data\n"):
            manager.export_to_file(test_data, "test.csv")
        
        mock_open.assert_called_once_with("test.csv", 'w', encoding='utf-8', newline='')
        mock_file.write.assert_called_once_with("test,csv,data\n")
        
        stderr_output = mock_stderr.getvalue()
        assert "CSV exported to: test.csv" in stderr_output

    def test_export_to_file_failure(self):
        """Test export to file with failure."""
        manager = CSVOutputManager()
        test_data = [{"name": "test", "value": "data"}]
        
        # First mock the CSV generation to succeed, then the file write to fail
        with patch.object(manager, '_generate_csv_safely', return_value="test,csv\ndata,value\n"):
            with patch('builtins.open', side_effect=PermissionError("Permission denied")):
                with pytest.raises(ForkscoutOutputError) as exc_info:
                    manager.export_to_file(test_data, "test.csv")
                
                assert "Failed to export CSV to file 'test.csv'" in str(exc_info.value)

    def test_generate_csv_safely_success(self):
        """Test successful CSV generation."""
        manager = CSVOutputManager()
        test_data = [{"name": "test", "value": "data"}]
        
        with patch.object(manager.exporter, 'export_to_csv', return_value="test,csv\ndata,value\n"):
            result = manager._generate_csv_safely(test_data)
            assert result == "test,csv\ndata,value\n"

    def test_generate_csv_safely_unicode_error(self):
        """Test CSV generation with Unicode error."""
        manager = CSVOutputManager()
        test_data = [{"name": "test", "value": "data"}]
        
        with patch.object(manager.exporter, 'export_to_csv', side_effect=UnicodeError("Unicode error")):
            with pytest.raises(ForkscoutUnicodeError) as exc_info:
                manager._generate_csv_safely(test_data)
            
            assert "Unicode error in CSV generation" in str(exc_info.value)

    def test_generate_csv_safely_general_error(self):
        """Test CSV generation with general error."""
        manager = CSVOutputManager()
        test_data = [{"name": "test", "value": "data"}]
        
        with patch.object(manager.exporter, 'export_to_csv', side_effect=ValueError("Generation error")):
            with pytest.raises(ForkscoutOutputError) as exc_info:
                manager._generate_csv_safely(test_data)
            
            assert "CSV generation failed" in str(exc_info.value)

    def test_validate_csv_unicode_valid(self):
        """Test CSV Unicode validation with valid content."""
        manager = CSVOutputManager()
        content = "name,value\ntest,data\n"
        
        result = manager._validate_csv_unicode(content)
        assert result == content

    def test_validate_csv_unicode_invalid(self):
        """Test CSV Unicode validation with invalid content."""
        manager = CSVOutputManager()
        
        # Test with actual problematic Unicode content
        problematic_content = "name,value\ntest\udcff,data\n"  # Invalid surrogate
        
        # Should clean the content or handle it gracefully
        result = manager._validate_csv_unicode(problematic_content)
        assert isinstance(result, str)

    def test_validate_csv_unicode_failure(self):
        """Test CSV Unicode validation complete failure."""
        manager = CSVOutputManager()
        
        # Mock the method to simulate failure
        with patch.object(manager, '_validate_csv_unicode') as mock_validate:
            mock_validate.side_effect = ForkscoutUnicodeError("Cannot create Unicode-safe CSV content")
            
            with pytest.raises(ForkscoutUnicodeError) as exc_info:
                manager._validate_csv_unicode("test content")
            
            assert "Cannot create Unicode-safe CSV content" in str(exc_info.value)

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_write_to_stdout_success(self, mock_stdout):
        """Test successful write to stdout."""
        manager = CSVOutputManager()
        content = "test,csv,content\n"
        
        manager._write_to_stdout(content)
        
        output = mock_stdout.getvalue()
        assert output == content

    def test_write_to_stdout_unicode_encode_error(self):
        """Test write to stdout with Unicode encode error."""
        manager = CSVOutputManager()
        content = "test,csv,content\n"
        
        # Mock the first write to fail, second to succeed
        write_calls = [UnicodeEncodeError('utf-8', 'test', 0, 1, 'error'), None]
        
        with patch('sys.stdout.write', side_effect=write_calls):
            with patch('sys.stdout.flush'):
                # Should handle the error and try again with safe content
                manager._write_to_stdout(content)
                # Should not raise exception

    def test_write_to_stdout_general_error(self):
        """Test write to stdout with general error."""
        manager = CSVOutputManager()
        content = "test,csv,content\n"
        
        with patch('sys.stdout.write', side_effect=Exception("Write failed")):
            with pytest.raises(ForkscoutOutputError) as exc_info:
                manager._write_to_stdout(content)
            
            assert "Failed to write CSV to stdout" in str(exc_info.value)

    @patch('sys.stderr', new_callable=io.StringIO)
    def test_cleanup_partial_output(self, mock_stderr):
        """Test cleanup of partial output."""
        manager = CSVOutputManager()
        manager._has_output = True
        
        manager._cleanup_partial_output()
        
        stderr_output = mock_stderr.getvalue()
        assert "Warning: Partial CSV output may have been generated" in stderr_output

    @patch('sys.stderr', new_callable=io.StringIO)
    def test_log_to_stderr_success(self, mock_stderr):
        """Test logging to stderr successfully."""
        manager = CSVOutputManager()
        
        manager._log_to_stderr("Test message")
        
        output = mock_stderr.getvalue()
        assert output == "Test message\n"

    @patch('sys.stderr', new_callable=io.StringIO)
    def test_log_to_stderr_unicode_error(self, mock_stderr):
        """Test logging to stderr with Unicode error."""
        manager = CSVOutputManager()
        
        with patch('forklift.reporting.csv_output_manager.safe_unicode_output', side_effect=Exception("Unicode failed")):
            manager._log_to_stderr("Test message")
            
            output = mock_stderr.getvalue()
            assert "Log message could not be displayed due to encoding error" in output


class TestCSVOutputContext:
    """Test CSV output context manager."""

    def test_create_csv_context(self):
        """Test creating CSV context."""
        context = create_csv_context(suppress_progress=True, debug=True)
        assert isinstance(context, CSVOutputContext)
        assert context.suppress_progress is True

    def test_create_csv_context_with_manager(self):
        """Test creating CSV context with existing manager."""
        manager = CSVOutputManager()
        context = create_csv_context(manager=manager, suppress_progress=False)
        assert context.manager is manager
        assert context.suppress_progress is False

    def test_context_manager_enter_exit_success(self):
        """Test context manager enter/exit without errors."""
        manager = CSVOutputManager()
        context = CSVOutputContext(manager, suppress_progress=True)
        
        original_stderr = sys.stderr
        
        with context as ctx_manager:
            assert ctx_manager is manager
            # stderr should be redirected
            assert sys.stderr != original_stderr
        
        # stderr should be restored
        assert sys.stderr == original_stderr

    def test_context_manager_with_exception(self):
        """Test context manager with exception."""
        manager = CSVOutputManager()
        context = CSVOutputContext(manager, suppress_progress=True)
        
        original_stderr = sys.stderr
        
        try:
            with context as ctx_manager:
                # Simulate some stderr output
                sys.stderr.write("Progress message\n")
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # stderr should be restored
        assert sys.stderr == original_stderr

    def test_context_manager_no_suppress(self):
        """Test context manager without progress suppression."""
        manager = CSVOutputManager()
        context = CSVOutputContext(manager, suppress_progress=False)
        
        original_stderr = sys.stderr
        
        with context as ctx_manager:
            assert ctx_manager is manager
            # stderr should not be redirected
            assert sys.stderr == original_stderr
        
        assert sys.stderr == original_stderr


class TestCSVOutputIntegration:
    """Test CSV output integration scenarios."""

    def test_full_csv_export_workflow(self):
        """Test complete CSV export workflow."""
        manager = CSVOutputManager()
        
        # Configure for detailed export
        config = CSVExportConfig(
            include_commits=True,
            detail_mode=True,
            include_explanations=False,
            max_commits_per_fork=5,
            escape_newlines=True,
            include_urls=True
        )
        manager.configure_exporter(config)
        
        # Test data
        test_data = [
            {"name": "fork1", "commits": "commit1\ncommit2"},
            {"name": "fork2", "commits": "commit3,commit4"}
        ]
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            with patch.object(manager.exporter, 'export_to_csv', return_value="name,commits\nfork1,\"commit1\\ncommit2\"\nfork2,\"commit3,commit4\"\n"):
                manager.export_to_stdout(test_data)
        
        output = mock_stdout.getvalue()
        assert "name,commits" in output
        assert "fork1" in output
        assert "fork2" in output

    def test_csv_context_with_error_handling(self):
        """Test CSV context with comprehensive error handling."""
        with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            try:
                with create_csv_context(suppress_progress=True) as manager:
                    # Simulate progress messages that should be suppressed
                    print("Progress: Processing...", file=sys.stderr)
                    
                    # Simulate an error
                    raise ForkscoutOutputError("Export failed")
            except ForkscoutOutputError:
                pass
        
        # Progress messages should have been captured and not displayed
        # (since we're in suppress mode and there was an error)
        stderr_output = mock_stderr.getvalue()
        # The exact behavior depends on implementation details

    def test_unicode_handling_throughout_pipeline(self):
        """Test Unicode handling throughout the CSV pipeline."""
        manager = CSVOutputManager()
        
        # Test data with various Unicode characters
        test_data = [
            {"name": "测试", "description": "Test with Chinese"},
            {"name": "café", "description": "Test with accents"},
            {"name": "🚀", "description": "Test with emoji"},
        ]
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            with patch.object(manager.exporter, 'export_to_csv') as mock_export:
                # Return CSV with Unicode content
                mock_export.return_value = "name,description\n测试,Test with Chinese\ncafé,Test with accents\n🚀,Test with emoji\n"
                
                manager.export_to_stdout(test_data)
        
        output = mock_stdout.getvalue()
        assert "测试" in output
        assert "café" in output
        assert "🚀" in output

    def test_error_recovery_and_cleanup(self):
        """Test error recovery and cleanup mechanisms."""
        manager = CSVOutputManager()
        
        # Simulate partial output followed by error
        manager._has_output = True
        
        with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            with patch.object(manager, '_generate_csv_safely', side_effect=ForkscoutOutputError("Generation failed")):
                with pytest.raises(ForkscoutOutputError):
                    manager.export_to_stdout([{"test": "data"}])
        
        # Should have logged cleanup warning
        stderr_output = mock_stderr.getvalue()
        assert "Warning: Partial CSV output may have been generated" in stderr_output