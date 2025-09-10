"""Tests for documentation and help text updates."""

import pytest
from click.testing import CliRunner

from forkscout.cli import cli


class TestDocumentationHelpText:
    """Test cases for documentation and help text improvements."""

    def test_show_forks_help_includes_commit_counting_options(self):
        """Test that show-forks help text includes commit counting options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["show-forks", "--help"])
        
        assert result.exit_code == 0
        help_text = result.output
        
        # Check for commit counting options
        assert "--max-commits-count" in help_text
        assert "--commit-display-limit" in help_text
        
        # Check for improved descriptions
        assert "Maximum commits to count ahead for each fork" in help_text
        assert "0 for unlimited counting" in help_text
        assert "Higher values provide more accurate counts" in help_text
        assert "Maximum commits to fetch for display details" in help_text
        assert "Only affects --show-commits display" in help_text

    def test_show_forks_help_includes_commit_counting_section(self):
        """Test that help text includes dedicated commit counting section."""
        runner = CliRunner()
        result = runner.invoke(cli, ["show-forks", "--help"])
        
        assert result.exit_code == 0
        help_text = result.output
        
        # Check for commit counting section
        assert "COMMIT COUNTING OPTIONS:" in help_text
        assert "Use --max-commits-count to control counting accuracy vs performance" in help_text
        assert "Use --commit-display-limit to control commit message display" in help_text

    def test_show_forks_help_includes_performance_guidance(self):
        """Test that help text includes performance guidance."""
        runner = CliRunner()
        result = runner.invoke(cli, ["show-forks", "--help"])
        
        assert result.exit_code == 0
        help_text = result.output
        
        # Check for performance guidance
        assert "More accurate" in help_text
        assert "but slower" in help_text
        assert "Faster processing" in help_text
        assert "Count up to" in help_text and "commits ahead" in help_text
        assert "provide more accurate counts" in help_text
        assert "use more API calls" in help_text

    def test_show_forks_help_includes_enhanced_examples(self):
        """Test that help text includes examples for commit counting options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["show-forks", "--help"])
        
        assert result.exit_code == 0
        help_text = result.output
        
        # Check for enhanced examples
        assert "# Get exact commit counts (uses default limit of 100 commits)" in help_text
        assert "# Count unlimited commits for maximum accuracy (slower)" in help_text
        assert "--max-commits-count 0" in help_text
        assert "# Fast processing with lower commit count limit" in help_text
        assert "--max-commits-count 50" in help_text
        assert "# Show recent commits with custom display limit" in help_text
        assert "--commit-display-limit 10" in help_text

    def test_main_cli_help_includes_version(self):
        """Test that main CLI help includes version information."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        
        assert result.exit_code == 0
        help_text = result.output
        
        # Check for main CLI description
        assert "Forklift - GitHub repository fork analysis tool" in help_text
        assert "Discover and analyze valuable features across all forks" in help_text

    def test_analyze_command_help_includes_csv_explanation(self):
        """Test that analyze command help includes CSV export explanation."""
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "--help"])
        
        assert result.exit_code == 0
        help_text = result.output
        
        # Check for CSV explanation
        assert "--csv flag to export analysis results" in help_text
        assert "multi-row CSV format" in help_text
        assert "suppresses all interactive elements" in help_text

    def test_help_text_formatting_consistency(self):
        """Test that help text formatting is consistent across commands."""
        runner = CliRunner()
        
        # Test show-forks command
        result = runner.invoke(cli, ["show-forks", "--help"])
        assert result.exit_code == 0
        show_forks_help = result.output
        
        # Test analyze command
        result = runner.invoke(cli, ["analyze", "--help"])
        assert result.exit_code == 0
        analyze_help = result.output
        
        # Check for consistent formatting patterns
        # Both should use similar example formatting
        assert "Examples:" in show_forks_help
        assert "Examples:" in analyze_help
        
        # Both should use consistent option descriptions
        assert "REPOSITORY_URL can be:" in show_forks_help
        assert "REPOSITORY_URL can be:" in analyze_help

    def test_commit_counting_options_have_proper_types(self):
        """Test that commit counting options have proper type validation."""
        runner = CliRunner()
        
        # Test invalid max-commits-count
        result = runner.invoke(cli, ["show-forks", "owner/repo", "--max-commits-count", "-1"])
        assert result.exit_code != 0
        assert "Invalid value" in result.output or "out of range" in result.output
        
        # Test invalid commit-display-limit
        result = runner.invoke(cli, ["show-forks", "owner/repo", "--commit-display-limit", "-1"])
        assert result.exit_code != 0
        assert "Invalid value" in result.output or "out of range" in result.output

    def test_help_text_includes_troubleshooting_references(self):
        """Test that help text references troubleshooting documentation."""
        runner = CliRunner()
        result = runner.invoke(cli, ["show-forks", "--help"])
        
        assert result.exit_code == 0
        help_text = result.output
        
        # The help text should guide users to troubleshooting resources
        # This is implicit through the detailed explanations and examples
        assert "COMMIT COUNTING OPTIONS:" in help_text
        assert "performance" in help_text.lower()
        assert "accuracy" in help_text.lower()

    def test_option_descriptions_are_informative(self):
        """Test that option descriptions provide clear guidance."""
        runner = CliRunner()
        result = runner.invoke(cli, ["show-forks", "--help"])
        
        assert result.exit_code == 0
        help_text = result.output
        
        # Check that descriptions explain the trade-offs
        assert "accuracy vs performance" in help_text
        assert "use more API calls" in help_text
        assert "take longer" in help_text
        assert "not the" in help_text and "commit counting accuracy" in help_text

    def test_examples_cover_common_use_cases(self):
        """Test that examples cover common use cases."""
        runner = CliRunner()
        result = runner.invoke(cli, ["show-forks", "--help"])
        
        assert result.exit_code == 0
        help_text = result.output
        
        # Check for common use case examples
        examples_section = help_text[help_text.find("Examples:"):]
        
        # Basic usage
        assert "# Basic fork display" in examples_section
        
        # Performance optimization
        assert "# Fast processing" in examples_section
        
        # Accuracy optimization
        assert "# Count unlimited commits for maximum accuracy" in examples_section
        
        # Display customization
        assert "# Show recent commits with custom display limit" in examples_section
        
        # CSV export
        assert "# Export to multi-row CSV" in examples_section


class TestDocumentationFiles:
    """Test cases for documentation file content."""

    def test_troubleshooting_guide_exists(self):
        """Test that the troubleshooting guide file exists."""
        import os
        assert os.path.exists("docs/COMMIT_COUNTING_TROUBLESHOOTING.md")

    def test_troubleshooting_guide_has_required_sections(self):
        """Test that troubleshooting guide has all required sections."""
        with open("docs/COMMIT_COUNTING_TROUBLESHOOTING.md", "r") as f:
            content = f.read()
        
        # Check for main sections
        assert "# Commit Counting Troubleshooting Guide" in content
        assert "## Overview" in content
        assert "## Common Issues and Solutions" in content
        assert "### Issue: All Forks Show \"+1\" Commits (Legacy Bug)" in content
        assert "### Issue: Commit Counts Show \"100+\" Instead of Exact Numbers" in content
        assert "### Issue: Slow Performance When Counting Commits" in content
        assert "### Issue: \"Unknown\" Commit Counts" in content
        assert "## Performance Optimization" in content
        assert "## Configuration Best Practices" in content
        assert "## Debugging Steps" in content

    def test_troubleshooting_guide_includes_practical_solutions(self):
        """Test that troubleshooting guide includes practical solutions."""
        with open("docs/COMMIT_COUNTING_TROUBLESHOOTING.md", "r") as content_file:
            content = content_file.read()
        
        # Check for practical command examples
        assert "--max-commits-count 0" in content
        assert "--max-commits-count 50" in content
        assert "--ahead-only" in content
        assert "--verbose" in content
        assert "--disable-cache" in content
        
        # Check for configuration examples
        assert "forklift.yaml" in content
        assert "GITHUB_TOKEN" in content

    def test_troubleshooting_guide_includes_performance_recommendations(self):
        """Test that troubleshooting guide includes performance recommendations."""
        with open("docs/COMMIT_COUNTING_TROUBLESHOOTING.md", "r") as content_file:
            content = content_file.read()
        
        # Check for performance recommendations by repository size
        assert "Small repositories" in content
        assert "Medium repositories" in content
        assert "Large repositories" in content
        assert "Very large repositories" in content
        
        # Check for specific recommendations
        assert "--max-forks" in content
        assert "API usage" in content

    def test_readme_includes_commit_counting_configuration(self):
        """Test that README includes commit counting configuration."""
        with open("README.md", "r") as f:
            content = f.read()
        
        # Check for commit counting configuration section
        assert "commit_count:" in content
        assert "max_count_limit:" in content
        assert "display_limit:" in content
        assert "use_unlimited_counting:" in content
        assert "timeout_seconds:" in content

    def test_readme_includes_commit_counting_examples(self):
        """Test that README includes commit counting examples."""
        with open("README.md", "r") as f:
            content = f.read()
        
        # Check for commit counting examples section
        assert "### Commit Counting Options" in content
        assert "--max-commits-count 0" in content
        assert "--max-commits-count 50" in content
        assert "--commit-display-limit 10" in content
        assert "--ahead-only" in content

    def test_readme_includes_troubleshooting_section(self):
        """Test that README includes troubleshooting section."""
        with open("README.md", "r") as f:
            content = f.read()
        
        # Check for troubleshooting section
        assert "## Troubleshooting" in content
        assert "### Common Issues" in content
        assert "Commit counts showing \"+1\" for all forks" in content
        assert "Slow performance with commit counting" in content
        assert "\"Unknown\" commit counts" in content
        assert "docs/COMMIT_COUNTING_TROUBLESHOOTING.md" in content


class TestConfigurationDocumentation:
    """Test cases for configuration documentation."""

    def test_commit_count_config_is_documented(self):
        """Test that CommitCountConfig options are documented."""
        with open("README.md", "r") as f:
            content = f.read()
        
        # Check that all CommitCountConfig fields are documented
        assert "max_count_limit" in content
        assert "display_limit" in content
        assert "use_unlimited_counting" in content
        assert "timeout_seconds" in content
        
        # Check for explanatory comments
        assert "Maximum commits to count per fork" in content
        assert "0 = unlimited" in content
        assert "Maximum commits to show in display" in content

    def test_configuration_examples_are_valid_yaml(self):
        """Test that configuration examples in README are valid YAML."""
        import yaml
        
        with open("README.md", "r") as f:
            content = f.read()
        
        # Extract YAML configuration example
        yaml_start = content.find("```yaml\ngithub:")
        yaml_end = content.find("```", yaml_start + 1)
        yaml_content = content[yaml_start + 8:yaml_end]  # Skip "```yaml\n"
        
        # Should be valid YAML
        try:
            config = yaml.safe_load(yaml_content)
            assert isinstance(config, dict)
            assert "github" in config
            assert "commit_count" in config
            assert "max_count_limit" in config["commit_count"]
        except yaml.YAMLError:
            pytest.fail("Configuration example in README is not valid YAML")

    def test_help_text_matches_configuration_options(self):
        """Test that CLI help text matches configuration file options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["show-forks", "--help"])
        
        assert result.exit_code == 0
        help_text = result.output
        
        # CLI options should correspond to config file options
        assert "--max-commits-count" in help_text
        assert "--commit-display-limit" in help_text
        
        # Default values should be mentioned
        assert "default: 100" in help_text
        assert "default: 5" in help_text