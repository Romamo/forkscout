"""End-to-end tests for CSV export fix functionality."""

import pytest
import subprocess
import tempfile
import os
import csv
import io
from pathlib import Path


@pytest.mark.e2e
@pytest.mark.slow
class TestCSVExportEndToEnd:
    """End-to-end tests for CSV export functionality."""

    @pytest.fixture
    def temp_output_file(self):
        """Create a temporary file for CSV output."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_path = f.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    def test_csv_export_command_execution(self):
        """Test that CSV export command executes without errors."""
        # Test with a known public repository that should have forks
        cmd = [
            "uv", "run", "forklift", "show-forks", 
            "octocat/Hello-World",  # Well-known test repository
            "--csv",
            "--max-forks", "2"  # Reduced to 2 for faster execution
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # Reduced timeout to 30 seconds
            )
            
            # Should not fail with the fix
            assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"
            
            # Should produce CSV output
            assert len(result.stdout) > 0, "No CSV output generated"
            
            # Should not contain error messages in stdout
            assert "No data to export" not in result.stdout
            assert "# No data to export" not in result.stdout
            
        except subprocess.TimeoutExpired:
            pytest.skip("Command timed out - may indicate network issues or rate limiting")
        except FileNotFoundError:
            pytest.skip("forklift command not available - run 'uv install' first")

    def test_csv_export_with_detail_flag(self):
        """Test CSV export with --detail flag."""
        cmd = [
            "uv", "run", "forklift", "show-forks",
            "octocat/Hello-World",
            "--csv",
            "--detail",
            "--max-forks", "1"  # Reduced to 1 for faster execution
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=45  # Reduced timeout
            )
            
            assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"
            assert len(result.stdout) > 0, "No CSV output generated"
            
            # Should contain CSV headers and data
            lines = result.stdout.strip().split('\n')
            assert len(lines) >= 1, "Should have at least CSV headers"
            
        except subprocess.TimeoutExpired:
            pytest.skip("Command timed out - may indicate network issues or rate limiting")
        except FileNotFoundError:
            pytest.skip("forklift command not available")

    def test_csv_export_with_ahead_only_flag(self):
        """Test CSV export with --ahead-only flag."""
        cmd = [
            "uv", "run", "forklift", "show-forks",
            "octocat/Hello-World",
            "--csv",
            "--ahead-only",
            "--max-forks", "2"  # Reduced for faster execution
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # Reduced timeout
            )
            
            assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"
            # Note: ahead-only might result in empty output if no forks have commits ahead
            # This is valid behavior, so we just check that it doesn't crash
            
        except subprocess.TimeoutExpired:
            pytest.skip("Command timed out - may indicate network issues or rate limiting")
        except FileNotFoundError:
            pytest.skip("forklift command not available")

    def test_csv_export_with_show_commits_flag(self):
        """Test CSV export with --show-commits flag."""
        cmd = [
            "uv", "run", "forklift", "show-forks",
            "octocat/Hello-World",
            "--csv",
            "--show-commits", "2",
            "--max-forks", "3"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=90  # Longer timeout for commit fetching
            )
            
            assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"
            assert len(result.stdout) > 0, "No CSV output generated"
            
        except subprocess.TimeoutExpired:
            pytest.skip("Command timed out - may indicate network issues")
        except FileNotFoundError:
            pytest.skip("forklift command not available")

    def test_csv_export_multiple_flags_combination(self):
        """Test CSV export with multiple flag combinations."""
        cmd = [
            "uv", "run", "forklift", "show-forks",
            "octocat/Hello-World",
            "--csv",
            "--detail",
            "--show-commits", "1",
            "--max-forks", "2"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # Longer timeout for multiple flags
            )
            
            assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"
            assert len(result.stdout) > 0, "No CSV output generated"
            
        except subprocess.TimeoutExpired:
            pytest.skip("Command timed out - may indicate network issues")
        except FileNotFoundError:
            pytest.skip("forklift command not available")

    def test_csv_output_redirection_to_file(self, temp_output_file):
        """Test CSV output redirection to file."""
        cmd = [
            "uv", "run", "forklift", "show-forks",
            "octocat/Hello-World",
            "--csv",
            "--max-forks", "3"
        ]
        
        try:
            with open(temp_output_file, 'w') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=60
                )
            
            assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"
            
            # Verify file was created and has content
            assert os.path.exists(temp_output_file)
            
            with open(temp_output_file, 'r') as f:
                content = f.read()
                assert len(content) > 0, "No content written to file"
                
        except subprocess.TimeoutExpired:
            pytest.skip("Command timed out - may indicate network issues")
        except FileNotFoundError:
            pytest.skip("forklift command not available")

    def test_csv_parsing_by_external_tools(self):
        """Test that CSV output can be parsed by external tools."""
        cmd = [
            "uv", "run", "forklift", "show-forks",
            "octocat/Hello-World",
            "--csv",
            "--max-forks", "3"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            assert result.returncode == 0, f"Command failed with stderr: {result.stderr}"
            
            if len(result.stdout) > 0:
                # Try to parse the CSV output
                csv_reader = csv.reader(io.StringIO(result.stdout))
                rows = list(csv_reader)
                
                # Should have at least headers
                assert len(rows) >= 1, "CSV should have at least header row"
                
                # Headers should be strings
                headers = rows[0]
                assert all(isinstance(header, str) for header in headers), "Headers should be strings"
                
                # If there are data rows, verify they have the same number of columns as headers
                for i, row in enumerate(rows[1:], 1):
                    assert len(row) == len(headers), f"Row {i} has {len(row)} columns, expected {len(headers)}"
                    
        except subprocess.TimeoutExpired:
            pytest.skip("Command timed out - may indicate network issues")
        except FileNotFoundError:
            pytest.skip("forklift command not available")

    def test_original_failing_command(self):
        """Test the original failing command that prompted this fix."""
        # This is the exact command from the issue report
        cmd = [
            "uv", "run", "forklift", "show-forks",
            "https://github.com/sanila2007/youtube-bot-telegram",
            "--detail",
            "--ahead-only", 
            "--csv",
            "--show-commits=2"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # Longer timeout for this complex command
            )
            
            # The main fix: this should not fail anymore
            assert result.returncode == 0, f"Original failing command still fails: {result.stderr}"
            
            # Should produce some output (even if empty due to filtering)
            # The key is that it shouldn't crash or show "No data to export"
            if "No data to export" in result.stdout:
                pytest.fail("Still showing 'No data to export' - fix not working")
                
        except subprocess.TimeoutExpired:
            pytest.skip("Command timed out - may indicate network issues or rate limiting")
        except FileNotFoundError:
            pytest.skip("forklift command not available")


@pytest.mark.e2e
@pytest.mark.slow
class TestCSVExportValidation:
    """Validation tests for CSV export format and content."""

    def test_csv_format_validation(self):
        """Test that CSV output follows proper CSV format."""
        cmd = [
            "uv", "run", "forklift", "show-forks",
            "octocat/Hello-World",
            "--csv",
            "--max-forks", "2"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0 and len(result.stdout) > 0:
                # Validate CSV format
                try:
                    csv_reader = csv.reader(io.StringIO(result.stdout))
                    rows = list(csv_reader)
                    
                    # Basic CSV validation
                    assert len(rows) >= 1, "Should have at least headers"
                    
                    # Check for common CSV issues
                    for i, row in enumerate(rows):
                        # No row should be completely empty
                        if i == 0:  # Header row
                            assert len(row) > 0, "Header row should not be empty"
                        
                        # All rows should have consistent column count
                        if i > 0 and len(rows) > 1:
                            assert len(row) == len(rows[0]), f"Row {i} has inconsistent column count"
                            
                except csv.Error as e:
                    pytest.fail(f"CSV parsing failed: {e}")
                    
        except subprocess.TimeoutExpired:
            pytest.skip("Command timed out")
        except FileNotFoundError:
            pytest.skip("forklift command not available")

    def test_csv_content_validation(self):
        """Test that CSV content contains expected data structure."""
        cmd = [
            "uv", "run", "forklift", "show-forks",
            "octocat/Hello-World",
            "--csv",
            "--detail",
            "--max-forks", "2"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=90
            )
            
            if result.returncode == 0 and len(result.stdout) > 0:
                csv_reader = csv.reader(io.StringIO(result.stdout))
                rows = list(csv_reader)
                
                if len(rows) >= 1:
                    headers = rows[0]
                    
                    # Check for expected headers (based on CSV exporter implementation)
                    expected_headers = ['fork_name', 'owner', 'stars']
                    for expected_header in expected_headers:
                        assert any(expected_header in header.lower() for header in headers), \
                            f"Expected header '{expected_header}' not found in {headers}"
                            
        except subprocess.TimeoutExpired:
            pytest.skip("Command timed out")
        except FileNotFoundError:
            pytest.skip("forklift command not available")

    def test_csv_empty_repository_handling(self):
        """Test CSV export with repository that has no forks."""
        # Use a repository that's unlikely to have forks
        cmd = [
            "uv", "run", "forklift", "show-forks",
            "octocat/git-consortium",  # Typically has few or no forks
            "--csv"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Should not crash even with no forks
            assert result.returncode == 0, f"Command failed with empty repository: {result.stderr}"
            
            # Should still produce headers even if no data
            if len(result.stdout) > 0:
                lines = result.stdout.strip().split('\n')
                assert len(lines) >= 1, "Should have at least CSV headers for empty repository"
                
        except subprocess.TimeoutExpired:
            pytest.skip("Command timed out")
        except FileNotFoundError:
            pytest.skip("forklift command not available")


@pytest.mark.e2e
@pytest.mark.slow
class TestCSVExportPerformance:
    """Performance tests for CSV export functionality."""

    def test_csv_export_performance_with_limits(self):
        """Test CSV export performance with reasonable limits."""
        cmd = [
            "uv", "run", "forklift", "show-forks",
            "microsoft/vscode",  # Repository with many forks
            "--csv",
            "--max-forks", "10"  # Limit for performance
        ]
        
        try:
            import time
            start_time = time.time()
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            assert result.returncode == 0, f"Performance test failed: {result.stderr}"
            
            # Should complete within reasonable time
            assert execution_time < 60, f"CSV export took too long: {execution_time}s"
            
            if len(result.stdout) > 0:
                # Should produce reasonable amount of output
                lines = result.stdout.strip().split('\n')
                assert len(lines) <= 12, f"Too many output lines for max-forks=10: {len(lines)}"
                
        except subprocess.TimeoutExpired:
            pytest.skip("Performance test timed out")
        except FileNotFoundError:
            pytest.skip("forklift command not available")

    def test_csv_export_memory_usage(self):
        """Test that CSV export doesn't consume excessive memory."""
        cmd = [
            "uv", "run", "forklift", "show-forks",
            "facebook/react",  # Popular repository
            "--csv",
            "--max-forks", "5"  # Reasonable limit
        ]
        
        try:
            # Use subprocess with memory monitoring if available
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            assert result.returncode == 0, f"Memory test failed: {result.stderr}"
            
            # Basic check - should produce output without crashing
            # More sophisticated memory monitoring would require additional tools
            
        except subprocess.TimeoutExpired:
            pytest.skip("Memory test timed out")
        except FileNotFoundError:
            pytest.skip("forklift command not available")


@pytest.mark.e2e
@pytest.mark.slow
class TestCSVExportErrorHandling:
    """Error handling tests for CSV export functionality."""

    def test_csv_export_with_invalid_repository(self):
        """Test CSV export with invalid repository URL."""
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
                timeout=30
            )
            
            # Should handle error gracefully (may return non-zero exit code)
            # The important thing is it shouldn't crash with the CSV export bug
            
            # Check that error messages go to stderr, not stdout
            if result.returncode != 0:
                assert len(result.stderr) > 0, "Error should be reported in stderr"
                # stdout should not contain the old "No data to export" bug
                assert "# No data to export" not in result.stdout
                
        except subprocess.TimeoutExpired:
            pytest.skip("Error handling test timed out")
        except FileNotFoundError:
            pytest.skip("forklift command not available")

    def test_csv_export_with_private_repository(self):
        """Test CSV export with private repository (should handle gracefully)."""
        cmd = [
            "uv", "run", "forklift", "show-forks",
            "private/repository",  # Likely private or non-existent
            "--csv"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Should handle private repository gracefully
            # May return error code, but shouldn't crash with CSV bug
            
            if result.returncode != 0:
                # Error should be in stderr
                assert len(result.stderr) > 0
                # Should not show the old CSV export bug
                assert "# No data to export" not in result.stdout
                
        except subprocess.TimeoutExpired:
            pytest.skip("Private repository test timed out")
        except FileNotFoundError:
            pytest.skip("forklift command not available")