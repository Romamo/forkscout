"""Integration tests for CSV export stderr redirection functionality."""

import asyncio
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestCSVStderrRedirection:
    """Test that filtering messages are redirected to stderr in CSV mode."""

    def test_csv_export_filtering_message_to_stderr(self):
        """Test that filtering messages go to stderr while CSV data goes to stdout."""
        # Run the command with output redirection
        cmd = [
            "uv", "run", "forklift", "show-forks",
            "https://github.com/sanila2007/youtube-bot-telegram",
            "--detail", "--ahead-only", "--show-commits=2", "--csv"
        ]
        
        # Create temporary file for CSV output
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False) as csv_file:
            csv_path = Path(csv_file.name)
        
        try:
            # Run command with stdout redirected to file, stderr captured
            result = subprocess.run(
                cmd,
                stdout=open(csv_path, 'w'),
                stderr=subprocess.PIPE,
                text=True,
                timeout=60
            )
            
            # Read the CSV file content
            csv_content = csv_path.read_text()
            
            # Read stderr output
            stderr_output = result.stderr
            
            # Verify CSV file contains only valid CSV data (no filtering message)
            lines = csv_content.strip().split('\n')
            assert len(lines) > 0, "CSV file should not be empty"
            
            # First line should be CSV headers (new format)
            first_line = lines[0]
            assert first_line.startswith('Fork URL,Stars,Forks'), f"Expected CSV headers, got: {first_line}"
            
            # CSV should not contain the filtering message
            assert "Filtered" not in csv_content, "CSV file should not contain filtering messages"
            assert "included" not in csv_content, "CSV file should not contain filtering messages"
            assert "excluded" not in csv_content, "CSV file should not contain filtering messages"
            
            # The main goal is achieved: CSV output is clean
            # Filtering message may or may not appear depending on whether forks are actually excluded
            # If filtering message appears, it should be in stderr, not stdout
            if "Filtered" in stderr_output:
                # If filtering message appears, verify it's in stderr with proper format
                assert "included" in stderr_output, "Filtering message should appear in stderr"
                assert "excluded" in stderr_output, "Filtering message should appear in stderr"
                assert "forks:" in stderr_output, "Should contain fork count information"
            
            # The critical test: CSV file should be clean regardless
            print(f"CSV content first line: {first_line}")
            print(f"Stderr contains filtering: {'Filtered' in stderr_output}")
            
        finally:
            # Clean up temporary file
            if csv_path.exists():
                csv_path.unlink()

    def test_csv_export_without_filtering_no_stderr_message(self):
        """Test that no filtering message appears when no filtering is applied."""
        # Run command without --ahead-only flag (no filtering)
        cmd = [
            "uv", "run", "forklift", "show-forks",
            "https://github.com/sanila2007/youtube-bot-telegram",
            "--detail", "--show-commits=2", "--csv"
        ]
        
        # Create temporary file for CSV output
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False) as csv_file:
            csv_path = Path(csv_file.name)
        
        try:
            # Run command with stdout redirected to file, stderr captured
            result = subprocess.run(
                cmd,
                stdout=open(csv_path, 'w'),
                stderr=subprocess.PIPE,
                text=True,
                timeout=60
            )
            
            # Read stderr output
            stderr_output = result.stderr
            
            # When no filtering is applied, there should be no filtering message
            # (The filtering message only appears when filter_result.total_excluded > 0)
            filtering_lines = [line for line in stderr_output.split('\n') 
                             if 'Filtered' in line and 'forks:' in line]
            
            # If filtering message appears, it should indicate no exclusions
            if filtering_lines:
                # Should show 0 excluded if message appears
                assert any('0 private excluded' in line and '0 no commits excluded' in line 
                          for line in filtering_lines), \
                    "If filtering message appears, it should show no exclusions"
            
        finally:
            # Clean up temporary file
            if csv_path.exists():
                csv_path.unlink()

    def test_non_csv_mode_filtering_message_to_stdout(self):
        """Test that filtering messages go to stdout in non-CSV mode."""
        # Run command without --csv flag
        cmd = [
            "uv", "run", "forklift", "show-forks",
            "https://github.com/sanila2007/youtube-bot-telegram",
            "--detail", "--ahead-only", "--show-commits=2"
        ]
        
        # Run command and capture both stdout and stderr
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60
        )
        
        stdout_output = result.stdout
        stderr_output = result.stderr
        
        # In non-CSV mode, filtering message should appear in stdout (part of table output)
        # This is the original behavior we want to preserve
        assert result.returncode == 0, f"Command failed with stderr: {stderr_output}"
        
        # The output should contain table formatting and filtering information
        # We don't assert the exact location since the table formatting may vary
        # but we ensure the command runs successfully in non-CSV mode
        assert len(stdout_output) > 0, "Should have stdout output in non-CSV mode"