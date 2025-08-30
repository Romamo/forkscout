"""Tests for CLI help text documentation accuracy."""

import pytest
from click.testing import CliRunner

from forklift.cli import cli


class TestHelpTextDocumentation:
    """Test that CLI help text accurately documents the new commit format."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_show_forks_help_documents_commit_format(self):
        """Test that show-forks help text documents the new +X -Y commit format."""
        result = self.runner.invoke(cli, ["show-forks", "--help"])
        
        assert result.exit_code == 0
        help_text = result.output
        
        # Verify the new commit format is documented
        assert "+X -Y" in help_text
        assert "commits ahead" in help_text.lower()
        assert "commits behind" in help_text.lower()
        
        # Verify specific format examples are included
        assert "+5 -2" in help_text
        assert "+3" in help_text
        assert "-1" in help_text
        
        # Verify explanation of format components
        assert "X=ahead" in help_text or "X commits ahead" in help_text
        assert "Y=behind" in help_text or "Y commits behind" in help_text
        
        # Verify edge cases are documented
        assert "up-to-date" in help_text.lower()
        assert "empty cell" in help_text.lower()

    def test_show_fork_data_help_documents_commit_format(self):
        """Test that show-fork-data help text documents the new +X -Y commit format."""
        result = self.runner.invoke(cli, ["show-fork-data", "--help"])
        
        assert result.exit_code == 0
        help_text = result.output
        
        # Verify the new commit format is documented
        assert "+X -Y" in help_text
        assert "commits ahead" in help_text.lower()
        assert "commits behind" in help_text.lower()
        
        # Verify specific format examples are included
        assert "+5 -2" in help_text
        assert "+3" in help_text
        assert "-1" in help_text

    def test_show_commits_option_help_mentions_recent_commits_column(self):
        """Test that --show-commits option help mentions Recent Commits column."""
        result = self.runner.invoke(cli, ["show-forks", "--help"])
        
        assert result.exit_code == 0
        help_text = result.output
        
        # Verify --show-commits option mentions Recent Commits column
        assert "--show-commits" in help_text
        assert "Recent Commits" in help_text

    def test_show_fork_data_show_commits_option_help(self):
        """Test that show-fork-data --show-commits option help mentions Recent Commits column."""
        result = self.runner.invoke(cli, ["show-fork-data", "--help"])
        
        assert result.exit_code == 0
        help_text = result.output
        
        # Verify --show-commits option mentions Recent Commits column
        assert "--show-commits" in help_text
        assert "Recent Commits" in help_text

    def test_help_text_consistency_across_commands(self):
        """Test that commit format documentation is consistent across commands."""
        # Get help text from both commands
        show_forks_result = self.runner.invoke(cli, ["show-forks", "--help"])
        show_fork_data_result = self.runner.invoke(cli, ["show-fork-data", "--help"])
        
        assert show_forks_result.exit_code == 0
        assert show_fork_data_result.exit_code == 0
        
        show_forks_help = show_forks_result.output
        show_fork_data_help = show_fork_data_result.output
        
        # Verify consistent format examples
        format_examples = ["+5 -2", "+3", "-1"]
        for example in format_examples:
            assert example in show_forks_help
            assert example in show_fork_data_help
        
        # Verify consistent terminology
        consistent_terms = ["commits ahead", "commits behind", "+X -Y"]
        for term in consistent_terms:
            assert term in show_forks_help
            assert term in show_fork_data_help

    def test_help_text_includes_all_format_variations(self):
        """Test that help text includes all possible commit format variations."""
        result = self.runner.invoke(cli, ["show-forks", "--help"])
        
        assert result.exit_code == 0
        help_text = result.output
        
        # Test all documented format variations
        format_variations = [
            "+5 -2",  # Both ahead and behind
            "+3",     # Only ahead
            "-1",     # Only behind
        ]
        
        for variation in format_variations:
            assert variation in help_text
        
        # Test edge case documentation
        edge_cases = [
            "empty cell",
            "up-to-date",
            "completely up-to-date"
        ]
        
        for case in edge_cases:
            assert case in help_text.lower()

    def test_help_text_explains_format_meaning(self):
        """Test that help text explains what the format components mean."""
        result = self.runner.invoke(cli, ["show-forks", "--help"])
        
        assert result.exit_code == 0
        help_text = result.output
        
        # Verify format explanation is present
        assert "X=ahead" in help_text or "X commits ahead" in help_text
        assert "Y=behind" in help_text or "Y commits behind" in help_text
        
        # Verify examples have explanations
        assert "means" in help_text  # Should have explanatory text like "means 5 commits ahead"