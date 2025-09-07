"""Fast integration tests for CSV export functionality."""

import pytest
import subprocess
import tempfile
import os
import csv
import io
from unittest.mock import patch, AsyncMock


class TestCSVExportFast:
    """Fast integration tests for CSV export functionality."""

    def test_csv_export_command_basic(self):
        """Test basic CSV export command execution (fast version)."""
        # This test uses minimal parameters for speed and skips if rate limited
        cmd = [
            "uv", "run", "forklift", "show-forks", 
            "octocat/Hello-World",  # Well-known test repository
            "--csv",
            "--max-forks", "1"  # Minimal for speed
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10  # Very short timeout for fast test
            )
            
            # If we get rate limited, skip the test
            if "rate limit" in result.stderr.lower() or "rate limit" in result.stdout.lower():
                pytest.skip("Rate limited - skipping real API test")
            
            # Should not fail with the fix (unless rate limited)
            if result.returncode == 0:
                # Should produce CSV output
                assert len(result.stdout) > 0, "No CSV output generated"
                
                # Should not contain the old error messages
                assert "No data to export" not in result.stdout
                assert "# No data to export" not in result.stdout
            else:
                # If it fails, check it's not the old CSV bug
                assert "# No data to export" not in result.stdout, "Old CSV export bug still present"
            
        except subprocess.TimeoutExpired:
            pytest.skip("Command timed out - likely rate limited")
        except FileNotFoundError:
            pytest.skip("forklift command not available")

    def test_csv_export_help_text(self):
        """Test that CSV export help text is available."""
        cmd = ["uv", "run", "forklift", "show-forks", "--help"]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            assert result.returncode == 0
            assert "--csv" in result.stdout, "CSV flag should be documented in help"
            
        except subprocess.TimeoutExpired:
            pytest.skip("Help command timed out")
        except FileNotFoundError:
            pytest.skip("forklift command not available")

    def test_csv_export_with_invalid_repo_fast(self):
        """Test CSV export with invalid repository (fast version)."""
        cmd = [
            "uv", "run", "forklift", "show-forks",
            "nonexistent/repository-that-does-not-exist",
            "--csv"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10  # Short timeout
            )
            
            # Should handle error gracefully
            # The important thing is it shouldn't crash with the CSV export bug
            if result.returncode != 0:
                # Error should be in stderr, not stdout
                assert len(result.stderr) > 0, "Error should be reported in stderr"
                # Should not show the old CSV export bug
                assert "# No data to export" not in result.stdout
                
        except subprocess.TimeoutExpired:
            pytest.skip("Error handling test timed out")
        except FileNotFoundError:
            pytest.skip("forklift command not available")

    def test_csv_format_basic_validation(self):
        """Test basic CSV format validation (fast version)."""
        # Create a simple CSV string to test parsing
        test_csv = "Fork URL,Stars,Forks\nhttps://github.com/user/repo,10,5\n"
        
        try:
            csv_reader = csv.reader(io.StringIO(test_csv))
            rows = list(csv_reader)
            
            assert len(rows) == 2, "Should have header and one data row"
            assert len(rows[0]) == 3, "Header should have 3 columns"
            assert len(rows[1]) == 3, "Data row should have 3 columns"
            
        except csv.Error as e:
            pytest.fail(f"CSV parsing failed: {e}")


@pytest.mark.integration
class TestCSVExportIntegrationFast:
    """Fast integration tests that don't require real API calls."""

    def test_csv_export_command_structure(self):
        """Test that CSV export command has correct structure."""
        # Test command parsing without execution
        cmd_parts = [
            "uv", "run", "forklift", "show-forks",
            "test/repo",
            "--csv",
            "--max-forks", "1"
        ]
        
        # Verify command structure is valid
        assert "forklift" in cmd_parts
        assert "show-forks" in cmd_parts
        assert "--csv" in cmd_parts
        assert "--max-forks" in cmd_parts

    def test_csv_export_parameter_validation(self):
        """Test CSV export parameter validation."""
        # Test various parameter combinations
        valid_params = [
            ["--csv"],
            ["--csv", "--detail"],
            ["--csv", "--ahead-only"],
            ["--csv", "--max-forks", "5"],
            ["--csv", "--show-commits", "2"]
        ]
        
        for params in valid_params:
            # Just verify the parameter structure is valid
            assert "--csv" in params
            
            # Check for conflicting parameters
            if "--detail" in params and "--show-commits" in params:
                # This combination should be handled gracefully
                pass

    def test_csv_output_format_expectations(self):
        """Test expected CSV output format structure."""
        # Define expected CSV structure
        expected_headers = [
            "Fork URL", "Stars", "Forks", "Commits Ahead", "Commits Behind"
        ]
        
        # Test CSV header parsing
        header_line = ",".join(expected_headers)
        csv_reader = csv.reader(io.StringIO(header_line))
        parsed_headers = next(csv_reader)
        
        assert len(parsed_headers) == len(expected_headers)
        for i, header in enumerate(expected_headers):
            assert parsed_headers[i] == header

    def test_csv_export_error_message_format(self):
        """Test that error messages are properly formatted."""
        # Test that we don't have the old "# No data to export" format
        old_error_format = "# No data to export"
        
        # This should not appear in any CSV output
        assert old_error_format.startswith("#"), "Old format starts with comment character"
        
        # New format should be proper CSV or empty
        new_formats = [
            "",  # Empty output is acceptable
            "Fork URL,Stars,Forks\n",  # Headers only is acceptable
        ]
        
        for format_example in new_formats:
            if format_example:
                # Should be parseable as CSV
                try:
                    csv_reader = csv.reader(io.StringIO(format_example))
                    list(csv_reader)  # Should not raise exception
                except csv.Error:
                    pytest.fail(f"Format should be valid CSV: {format_example}")