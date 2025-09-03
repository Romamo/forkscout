"""Tests for console natural width configuration."""

import pytest
from unittest.mock import Mock
from rich.console import Console

from src.forklift.cli import initialize_cli_environment, console as cli_console
from src.forklift.display.repository_display_service import RepositoryDisplayService
from src.forklift.display.detailed_commit_display import DetailedCommitDisplay
from src.forklift.ai.display_formatter import AISummaryDisplayFormatter
from src.forklift.analysis.explanation_formatter import ExplanationFormatter
from src.forklift.analysis.interactive_orchestrator import InteractiveAnalysisOrchestrator
from src.forklift.analysis.interactive_analyzer import InteractiveAnalyzer


class TestConsoleNaturalWidthConfiguration:
    """Test that all Console instances are configured for natural width rendering."""

    def test_cli_console_configuration(self):
        """Test that CLI console is configured for natural width rendering."""
        # Initialize CLI environment to update global console
        initialize_cli_environment()
        
        # Import the updated console
        from src.forklift.cli import console as updated_console
        
        # Verify console configuration
        assert updated_console.width == 999999, f"CLI console width should be 999999, got {updated_console.width}"
        assert updated_console.soft_wrap is False, f"CLI console soft_wrap should be False, got {updated_console.soft_wrap}"

    def test_repository_display_service_console_configuration(self):
        """Test that RepositoryDisplayService console is configured for natural width rendering."""
        mock_github_client = Mock()
        service = RepositoryDisplayService(mock_github_client)
        
        # Verify console configuration
        assert service.console.width == 999999, f"Repository Display Service console width should be 999999, got {service.console.width}"
        assert service.console.soft_wrap is False, f"Repository Display Service console soft_wrap should be False, got {service.console.soft_wrap}"
        
        # Verify progress console configuration
        assert service.progress_console.width == 999999, f"Repository Display Service progress console width should be 999999, got {service.progress_console.width}"
        assert service.progress_console.soft_wrap is False, f"Repository Display Service progress console soft_wrap should be False, got {service.progress_console.soft_wrap}"

    def test_detailed_commit_display_console_configuration(self):
        """Test that DetailedCommitDisplay console is configured for natural width rendering."""
        mock_github_client = Mock()
        detailed_display = DetailedCommitDisplay(mock_github_client, None, None)
        
        # Verify console configuration
        assert detailed_display.console.width == 999999, f"Detailed Commit Display console width should be 999999, got {detailed_display.console.width}"
        assert detailed_display.console.soft_wrap is False, f"Detailed Commit Display console soft_wrap should be False, got {detailed_display.console.soft_wrap}"

    def test_ai_display_formatter_console_configuration(self):
        """Test that AISummaryDisplayFormatter console is configured for natural width rendering."""
        ai_formatter = AISummaryDisplayFormatter()
        
        # Verify console configuration
        assert ai_formatter.console.width == 999999, f"AI Display Formatter console width should be 999999, got {ai_formatter.console.width}"
        assert ai_formatter.console.soft_wrap is False, f"AI Display Formatter console soft_wrap should be False, got {ai_formatter.console.soft_wrap}"

    def test_explanation_formatter_console_configuration(self):
        """Test that ExplanationFormatter console is configured for natural width rendering."""
        explanation_formatter = ExplanationFormatter()
        
        # Verify console configuration
        assert explanation_formatter.console.width == 999999, f"Explanation Formatter console width should be 999999, got {explanation_formatter.console.width}"
        assert explanation_formatter.console.soft_wrap is False, f"Explanation Formatter console soft_wrap should be False, got {explanation_formatter.console.soft_wrap}"

    def test_interactive_orchestrator_console_configuration(self):
        """Test that InteractiveAnalysisOrchestrator console is configured for natural width rendering."""
        mock_github_client = Mock()
        mock_config = Mock()
        orchestrator = InteractiveAnalysisOrchestrator(mock_github_client, mock_config)
        
        # Verify console configuration
        assert orchestrator.console.width == 999999, f"Interactive Orchestrator console width should be 999999, got {orchestrator.console.width}"
        assert orchestrator.console.soft_wrap is False, f"Interactive Orchestrator console soft_wrap should be False, got {orchestrator.console.soft_wrap}"

    def test_interactive_analyzer_console_configuration(self):
        """Test that InteractiveAnalyzer console is configured for natural width rendering."""
        mock_github_client = Mock()
        analyzer = InteractiveAnalyzer(mock_github_client)
        
        # Verify console configuration
        assert analyzer.console.width == 999999, f"Interactive Analyzer console width should be 999999, got {analyzer.console.width}"
        assert analyzer.console.soft_wrap is False, f"Interactive Analyzer console soft_wrap should be False, got {analyzer.console.soft_wrap}"

    def test_console_with_provided_instance(self):
        """Test that services respect provided console instances."""
        # Create a custom console
        custom_console = Console(width=500, soft_wrap=True)
        
        # Test that services use the provided console
        mock_github_client = Mock()
        service = RepositoryDisplayService(mock_github_client, console=custom_console)
        
        # Should use the provided console, not create a new one
        assert service.console is custom_console
        assert service.console.width == 500
        assert service.console.soft_wrap is True

    def test_natural_width_table_rendering(self):
        """Test that tables render at natural width without truncation."""
        from rich.table import Table
        from io import StringIO
        
        # Create console with natural width configuration
        console = Console(width=999999, soft_wrap=False)
        
        # Create a table with very long content
        table = Table(expand=False)
        table.add_column("URL", min_width=35)
        table.add_column("Description", min_width=30)
        
        long_url = "https://github.com/very-long-username/very-long-repository-name-that-exceeds-normal-terminal-width"
        long_description = "This is a very long description that definitely exceeds the normal terminal width and should not be truncated"
        
        table.add_row(long_url, long_description)
        
        # Capture output
        string_io = StringIO()
        test_console = Console(file=string_io, width=999999, soft_wrap=False)
        test_console.print(table)
        output = string_io.getvalue()
        
        # Verify full content is preserved
        assert long_url in output, "Full URL should be preserved in table output"
        assert long_description in output, "Full description should be preserved in table output"
        assert "..." not in output or output.count("...") == 0, "Content should not be truncated with ellipsis"

    def test_console_configuration_consistency(self):
        """Test that all console configurations are consistent across the application."""
        # This test verifies that all console instances use the same configuration
        # for natural width rendering (width=999999, soft_wrap=False)
        
        mock_github_client = Mock()
        
        # Test multiple service instances
        services = [
            RepositoryDisplayService(mock_github_client),
            DetailedCommitDisplay(mock_github_client, None, None),
            AISummaryDisplayFormatter(),
            ExplanationFormatter(),
            InteractiveAnalysisOrchestrator(mock_github_client, Mock()),
            InteractiveAnalyzer(mock_github_client),
        ]
        
        # Verify all services use consistent console configuration
        for service in services:
            console = getattr(service, 'console', None)
            if console:
                assert console.width == 999999, f"{service.__class__.__name__} console width should be 999999"
                assert console.soft_wrap is False, f"{service.__class__.__name__} console soft_wrap should be False"