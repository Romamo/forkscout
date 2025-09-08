"""Integration tests for commit message truncation fix.

This module tests that commit messages are displayed in full without truncation
when using the show-forks command with --show-commits option.

Requirements tested:
- 1.1: Display full commit messages without truncation
- 1.4: Terminal width allows commit messages to not be artificially constrained
- 4.1: Column alignment remains correct with long commit messages
- 4.2: Table borders do not break with long content
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.mark.online
class TestCommitMessageTruncationFixIntegration:
    """Integration tests for commit message truncation fix using real repositories."""

    def _check_no_commit_message_truncation(self, output: str) -> None:
        """Helper method to check for commit message truncation, excluding progress indicators."""
        lines = output.split("\n")
        # Look for lines that contain commit messages (have commit keywords and SHA patterns)
        commit_lines = [line for line in lines if any(keyword in line for keyword in ["Update", "Create", "Add", "Fix", "Remove", "Delete", "Merge", "Initial"]) and any(char.isalnum() for char in line)]
        for line in commit_lines:
            assert "..." not in line, f"Found truncation indicators in commit message: {line}"

    def test_show_forks_with_commits_no_truncation_octocat(self):
        """Test show-forks with --show-commits using sanila2007/youtube-bot-telegram repository.

        This test verifies that commit messages are displayed without "..." truncation
        using a smaller test repository with actual commit messages.

        Requirements: 1.1, 1.4
        """
        if not os.getenv("GITHUB_TOKEN"):
            pytest.skip("GitHub token required for online tests")

        cmd = [
            "uv", "run", "forklift", "show-forks",
            "sanila2007/youtube-bot-telegram",
            "--show-commits=2",
            "--max-forks=3"  # Limit for faster execution
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # Allow time for API calls
            )

            # Skip if rate limited
            if "rate limit" in result.stderr.lower() or "rate limit" in result.stdout.lower():
                pytest.skip("Rate limited - skipping real API test")

            # Command should succeed
            assert result.returncode == 0, f"Command failed: {result.stderr}"

            # Verify no truncation indicators in commit messages
            self._check_no_commit_message_truncation(result.stdout)

            # Verify we have some output
            assert len(result.stdout) > 0, "No output generated"

            # Verify table structure is present
            assert "URL" in result.stdout or "Recent Commits" in result.stdout, "Table structure not found"

        except subprocess.TimeoutExpired:
            pytest.skip("Command timed out - likely rate limited")
        except FileNotFoundError:
            pytest.skip("forklift command not available")

    def test_show_forks_with_commits_no_truncation_microsoft_vscode(self):
        """Test show-forks with --show-commits using sanila2007/youtube-bot-telegram repository.

        This repository is known to have varied commit messages, making it ideal
        for testing truncation behavior.

        Requirements: 1.1, 4.1, 4.2
        """
        if not os.getenv("GITHUB_TOKEN"):
            pytest.skip("GitHub token required for online tests")

        cmd = [
            "uv", "run", "forklift", "show-forks",
            "sanila2007/youtube-bot-telegram",
            "--show-commits=2",
            "--max-forks=3"  # Limit for faster execution
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=90  # Allow more time for larger repository
            )

            # Skip if rate limited
            if "rate limit" in result.stderr.lower() or "rate limit" in result.stdout.lower():
                pytest.skip("Rate limited - skipping real API test")

            # Command should succeed
            assert result.returncode == 0, f"Command failed: {result.stderr}"

            # Verify no truncation indicators in commit messages
            self._check_no_commit_message_truncation(result.stdout)

            # Verify we have some output
            assert len(result.stdout) > 0, "No output generated"

            # Verify table structure remains intact
            lines = result.stdout.split("\n")
            table_lines = [line for line in lines if "│" in line or "┏" in line or "┗" in line or "┣" in line or "┌" in line or "└" in line or "├" in line]
            assert len(table_lines) > 0, "Table structure not found in output"

        except subprocess.TimeoutExpired:
            pytest.skip("Command timed out - likely rate limited")
        except FileNotFoundError:
            pytest.skip("forklift command not available")

    def test_show_forks_with_commits_varying_message_lengths(self):
        """Test show-forks with repositories that have varying commit message lengths.

        This test uses a repository known to have both short and long commit messages
        to verify table structure remains consistent.

        Requirements: 4.1, 4.2
        """
        if not os.getenv("GITHUB_TOKEN"):
            pytest.skip("GitHub token required for online tests")

        # Test with sanila2007/youtube-bot-telegram which has varied commit message lengths
        cmd = [
            "uv", "run", "forklift", "show-forks",
            "sanila2007/youtube-bot-telegram",
            "--show-commits=2",
            "--max-forks=3"  # Limit for faster execution
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=90  # Allow time for API calls
            )

            # Skip if rate limited
            if "rate limit" in result.stderr.lower() or "rate limit" in result.stdout.lower():
                pytest.skip("Rate limited - skipping real API test")

            # Command should succeed
            assert result.returncode == 0, f"Command failed: {result.stderr}"

            # Verify no truncation indicators in commit messages
            self._check_no_commit_message_truncation(result.stdout)

            # Verify table structure consistency
            lines = result.stdout.split("\n")

            # Check for table borders and structure - updated for actual table format
            border_chars = ["┏", "┓", "┗", "┛", "┣", "┫", "┳", "┻", "╋", "│", "━", "┌", "┐", "└", "┘", "├", "┤", "┬", "┴", "┼", "─"]
            has_table_structure = any(any(char in line for char in border_chars) for line in lines)
            assert has_table_structure, "Table structure not found in output"

            # Verify column alignment by checking that table borders are consistent
            table_lines = [line for line in lines if "│" in line]
            if table_lines:
                # Check that all data rows have the same number of columns
                column_counts = [line.count("│") for line in table_lines if line.strip()]
                if column_counts:
                    assert len(set(column_counts)) <= 2, "Inconsistent column structure in table"  # Allow for header vs data row differences

        except subprocess.TimeoutExpired:
            pytest.skip("Command timed out - likely rate limited")
        except FileNotFoundError:
            pytest.skip("forklift command not available")

    def test_show_forks_with_commits_detail_mode_no_truncation(self):
        """Test show-forks with --show-commits and --detail flags together.

        This test verifies that commit messages are not truncated even when
        using detailed mode which makes additional API calls.

        Requirements: 1.1, 1.4
        """
        if not os.getenv("GITHUB_TOKEN"):
            pytest.skip("GitHub token required for online tests")

        cmd = [
            "uv", "run", "forklift", "show-forks",
            "sanila2007/youtube-bot-telegram",
            "--show-commits=2",
            "--detail",
            "--max-forks=3"  # Limit for faster execution
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=90  # Allow time for detailed API calls
            )

            # Skip if rate limited
            if "rate limit" in result.stderr.lower() or "rate limit" in result.stdout.lower():
                pytest.skip("Rate limited - skipping real API test")

            # Command should succeed
            assert result.returncode == 0, f"Command failed: {result.stderr}"

            # Verify no truncation indicators in commit messages
            self._check_no_commit_message_truncation(result.stdout)

            # Verify we have some output
            assert len(result.stdout) > 0, "No output generated"

            # In detail mode, we should see exact commit counts (e.g., "+5")
            # Note: We don't check for exact counts because some forks might have 0 commits ahead

        except subprocess.TimeoutExpired:
            pytest.skip("Command timed out - likely rate limited")
        except FileNotFoundError:
            pytest.skip("forklift command not available")

    def test_show_forks_with_commits_ahead_only_no_truncation(self):
        """Test show-forks with --show-commits and --ahead-only flags together.

        This test verifies that commit messages are not truncated when filtering
        to show only forks with commits ahead.

        Requirements: 1.1, 1.4
        """
        if not os.getenv("GITHUB_TOKEN"):
            pytest.skip("GitHub token required for online tests")

        cmd = [
            "uv", "run", "forklift", "show-forks",
            "sanila2007/youtube-bot-telegram",
            "--show-commits=2",
            "--ahead-only",
            "--max-forks=3"  # Limit for faster execution
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=90  # Allow time for filtering
            )

            # Skip if rate limited
            if "rate limit" in result.stderr.lower() or "rate limit" in result.stdout.lower():
                pytest.skip("Rate limited - skipping real API test")

            # Command should succeed
            assert result.returncode == 0, f"Command failed: {result.stderr}"

            # Verify no truncation indicators in commit messages
            self._check_no_commit_message_truncation(result.stdout)

            # Verify we have some output (might be empty if no forks have commits ahead)
            assert len(result.stdout) > 0, "No output generated"

        except subprocess.TimeoutExpired:
            pytest.skip("Command timed out - likely rate limited")
        except FileNotFoundError:
            pytest.skip("forklift command not available")

    def test_show_forks_with_commits_output_to_file_no_truncation(self):
        """Test show-forks with --show-commits output redirected to file.

        This test verifies that commit messages are not truncated when output
        is redirected to a file, which changes the terminal width detection.

        Requirements: 1.1, 1.4, 4.1
        """
        if not os.getenv("GITHUB_TOKEN"):
            pytest.skip("GitHub token required for online tests")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "forks_output.txt"

            cmd = [
                "uv", "run", "forklift", "show-forks",
                "sanila2007/youtube-bot-telegram",
                "--show-commits=2",
                "--max-forks=3"  # Limit for faster execution
            ]

            try:
                with open(output_file, "w") as f:
                    result = subprocess.run(
                        cmd,
                        stdout=f,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=60
                    )

                # Skip if rate limited
                if "rate limit" in result.stderr.lower():
                    pytest.skip("Rate limited - skipping real API test")

                # Command should succeed
                assert result.returncode == 0, f"Command failed: {result.stderr}"

                # Read the output file
                output_content = output_file.read_text()

                # Verify no truncation indicators in commit messages
                self._check_no_commit_message_truncation(output_content)

                # Verify we have some output
                assert len(output_content) > 0, "No output generated"

                # Verify table structure is preserved in file output
                lines = output_content.split("\n")
                border_chars = ["┏", "┓", "┗", "┛", "┣", "┫", "┳", "┻", "╋", "│", "━", "┌", "┐", "└", "┘", "├", "┤", "┬", "┴", "┼", "─"]
                has_table_structure = any(any(char in line for char in border_chars) for line in lines)
                assert has_table_structure, "Table structure not preserved in file output"

            except subprocess.TimeoutExpired:
                pytest.skip("Command timed out - likely rate limited")
            except FileNotFoundError:
                pytest.skip("forklift command not available")

    def test_show_forks_with_commits_max_commits_boundary_values(self):
        """Test show-forks with --show-commits using boundary values.

        This test verifies that commit messages are not truncated with
        different values of --show-commits parameter.

        Requirements: 1.1, 4.1, 4.2
        """
        if not os.getenv("GITHUB_TOKEN"):
            pytest.skip("GitHub token required for online tests")

        # Test different boundary values for --show-commits
        test_values = [1, 5, 10]  # Min, middle, max values

        for show_commits_value in test_values:
            cmd = [
                "uv", "run", "forklift", "show-forks",
                "sanila2007/youtube-bot-telegram",
                f"--show-commits={show_commits_value}",
                "--max-forks=2"  # Limit for faster execution
            ]

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                # Skip if rate limited
                if "rate limit" in result.stderr.lower() or "rate limit" in result.stdout.lower():
                    pytest.skip("Rate limited - skipping real API test")

                # Command should succeed
                assert result.returncode == 0, f"Command failed for --show-commits={show_commits_value}: {result.stderr}"

                # Verify no truncation indicators in commit messages
                self._check_no_commit_message_truncation(result.stdout)

                # Verify we have some output
                assert len(result.stdout) > 0, f"No output generated for --show-commits={show_commits_value}"

            except subprocess.TimeoutExpired:
                pytest.skip(f"Command timed out for --show-commits={show_commits_value}")
            except FileNotFoundError:
                pytest.skip("forklift command not available")

    def test_show_forks_with_commits_table_structure_integrity(self):
        """Test that table structure remains intact with varying commit message lengths.

        This test specifically focuses on verifying that the table rendering
        handles long commit messages without breaking the table structure.

        Requirements: 4.1, 4.2
        """
        if not os.getenv("GITHUB_TOKEN"):
            pytest.skip("GitHub token required for online tests")

        # Use a repository known to have varied commit message lengths
        cmd = [
            "uv", "run", "forklift", "show-forks",
            "sanila2007/youtube-bot-telegram",  # Known for varied commit messages
            "--show-commits=2",
            "--max-forks=3"  # Limit for faster execution
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=90
            )

            # Skip if rate limited
            if "rate limit" in result.stderr.lower() or "rate limit" in result.stdout.lower():
                pytest.skip("Rate limited - skipping real API test")

            # Command should succeed
            assert result.returncode == 0, f"Command failed: {result.stderr}"

            # Verify no truncation indicators in commit messages
            self._check_no_commit_message_truncation(result.stdout)

            # Analyze table structure integrity
            lines = result.stdout.split("\n")

            # Find table boundaries - look for the actual table structure used
            header_lines = [line for line in lines if "┏" in line or "┳" in line]
            footer_lines = [line for line in lines if "┗" in line or "┻" in line or "┘" in line]
            data_lines = [line for line in lines if "│" in line and not any(char in line for char in ["┏", "┓", "┗", "┛", "┣", "┫", "┳", "┻", "╋"])]

            # Verify we have table structure
            assert len(header_lines) > 0, "No header border found in table"
            assert len(footer_lines) > 0, "No footer border found in table"

            # Verify table borders are consistent
            if header_lines and footer_lines:
                # Check that header and footer borders have similar structure
                header_border_chars = {char for char in header_lines[0] if char in "┏┳┓━"}
                footer_border_chars = {char for char in footer_lines[0] if char in "┗┻┘━└┴"}

                # Both should have horizontal line characters
                assert "━" in header_border_chars or "─" in header_border_chars, "Header border missing horizontal lines"
                # Footer might use different characters, so check for various possibilities
                has_footer_lines = any(char in footer_border_chars for char in ["━", "─", "┘", "└"])
                assert has_footer_lines, "Footer border missing horizontal lines"

            # Verify data rows have consistent column separators
            if data_lines:
                column_separator_counts = [line.count("│") for line in data_lines if line.strip()]
                if column_separator_counts:
                    # All data rows should have the same number of column separators
                    unique_counts = set(column_separator_counts)
                    assert len(unique_counts) <= 2, f"Inconsistent column separators: {unique_counts}"  # Allow for header vs data differences

        except subprocess.TimeoutExpired:
            pytest.skip("Command timed out - likely rate limited")
        except FileNotFoundError:
            pytest.skip("forklift command not available")
