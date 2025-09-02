"""Tests for CSV commit data formatting methods."""

import pytest
from datetime import datetime

from forklift.reporting.csv_exporter import CSVExporter, CSVExportConfig


class TestCSVCommitDataFormatting:
    """Test cases for CSV commit data formatting methods."""

    def test_format_commit_date_with_valid_date(self):
        """Test formatting commit date with valid datetime."""
        config = CSVExportConfig(commit_date_format="%Y-%m-%d")
        exporter = CSVExporter(config)
        
        test_date = datetime(2023, 11, 15, 10, 30, 45)
        formatted_date = exporter._format_commit_date(test_date)
        
        assert formatted_date == "2023-11-15"

    def test_format_commit_date_with_none(self):
        """Test formatting commit date with None value."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        formatted_date = exporter._format_commit_date(None)
        
        assert formatted_date == ""

    def test_format_commit_date_custom_format(self):
        """Test formatting commit date with custom format."""
        config = CSVExportConfig(commit_date_format="%d/%m/%Y")
        exporter = CSVExporter(config)
        
        test_date = datetime(2023, 11, 15, 10, 30, 45)
        formatted_date = exporter._format_commit_date(test_date)
        
        assert formatted_date == "15/11/2023"

    def test_format_commit_date_with_time_format(self):
        """Test formatting commit date including time."""
        config = CSVExportConfig(commit_date_format="%Y-%m-%d %H:%M:%S")
        exporter = CSVExporter(config)
        
        test_date = datetime(2023, 11, 15, 10, 30, 45)
        formatted_date = exporter._format_commit_date(test_date)
        
        assert formatted_date == "2023-11-15 10:30:45"

    def test_format_commit_date_iso_format(self):
        """Test formatting commit date in ISO format."""
        config = CSVExportConfig(commit_date_format="%Y-%m-%dT%H:%M:%SZ")
        exporter = CSVExporter(config)
        
        test_date = datetime(2023, 11, 15, 10, 30, 45)
        formatted_date = exporter._format_commit_date(test_date)
        
        assert formatted_date == "2023-11-15T10:30:45Z"

    def test_format_commit_sha_full_sha(self):
        """Test formatting full 40-character SHA to 7-character short SHA."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        full_sha = "1234567890abcdef1234567890abcdef12345678"
        short_sha = exporter._format_commit_sha(full_sha)
        
        assert short_sha == "1234567"
        assert len(short_sha) == 7

    def test_format_commit_sha_short_sha(self):
        """Test formatting already short SHA."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        short_sha_input = "abcdef1"
        short_sha = exporter._format_commit_sha(short_sha_input)
        
        assert short_sha == "abcdef1"

    def test_format_commit_sha_empty_string(self):
        """Test formatting empty SHA string."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        short_sha = exporter._format_commit_sha("")
        
        assert short_sha == ""

    def test_format_commit_sha_none(self):
        """Test formatting None SHA."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        short_sha = exporter._format_commit_sha(None)
        
        assert short_sha == ""

    def test_format_commit_sha_very_short(self):
        """Test formatting SHA shorter than 7 characters."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        short_input = "abc"
        short_sha = exporter._format_commit_sha(short_input)
        
        assert short_sha == "abc"

    def test_escape_commit_message_basic(self):
        """Test escaping basic commit message."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        message = "Fix critical bug in authentication system"
        escaped_message = exporter._escape_commit_message(message)
        
        assert escaped_message == "Fix critical bug in authentication system"

    def test_escape_commit_message_with_newlines(self):
        """Test escaping commit message with newlines."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        message = "Fix critical bug\nin authentication\nsystem"
        escaped_message = exporter._escape_commit_message(message)
        
        assert escaped_message == "Fix critical bug in authentication system"
        assert "\n" not in escaped_message

    def test_escape_commit_message_with_carriage_returns(self):
        """Test escaping commit message with carriage returns."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        message = "Fix critical bug\r\nin authentication\r\nsystem"
        escaped_message = exporter._escape_commit_message(message)
        
        assert escaped_message == "Fix critical bug in authentication system"
        assert "\r" not in escaped_message
        assert "\n" not in escaped_message

    def test_escape_commit_message_with_extra_whitespace(self):
        """Test escaping commit message with extra whitespace."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        message = "Fix   critical    bug     in authentication system"
        escaped_message = exporter._escape_commit_message(message)
        
        assert escaped_message == "Fix critical bug in authentication system"

    def test_escape_commit_message_with_tabs(self):
        """Test escaping commit message with tabs."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        message = "Fix\tcritical\tbug\tin\tauthentication\tsystem"
        escaped_message = exporter._escape_commit_message(message)
        
        assert escaped_message == "Fix critical bug in authentication system"

    def test_escape_commit_message_with_commas(self):
        """Test escaping commit message with commas (CSV special character)."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        message = "Fix bug in auth, user management, and session handling"
        escaped_message = exporter._escape_commit_message(message)
        
        # Commas should be preserved - CSV writer will handle escaping
        assert escaped_message == "Fix bug in auth, user management, and session handling"

    def test_escape_commit_message_with_quotes(self):
        """Test escaping commit message with quotes (CSV special character)."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        message = 'Fix "critical" bug in authentication system'
        escaped_message = exporter._escape_commit_message(message)
        
        # Quotes should be preserved - CSV writer will handle escaping
        assert escaped_message == 'Fix "critical" bug in authentication system'

    def test_escape_commit_message_empty_string(self):
        """Test escaping empty commit message."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        escaped_message = exporter._escape_commit_message("")
        
        assert escaped_message == ""

    def test_escape_commit_message_none(self):
        """Test escaping None commit message."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        escaped_message = exporter._escape_commit_message(None)
        
        assert escaped_message == ""

    def test_escape_commit_message_whitespace_only(self):
        """Test escaping commit message with only whitespace."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        message = "   \n\t\r   "
        escaped_message = exporter._escape_commit_message(message)
        
        assert escaped_message == ""

    def test_escape_commit_message_complex_multiline(self):
        """Test escaping complex multiline commit message."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        message = """Fix critical authentication bug

This commit addresses several issues:
- Session timeout handling
- Password validation
- User role verification

Fixes #123, #456"""
        
        escaped_message = exporter._escape_commit_message(message)
        
        # Should be on single line with proper spacing
        expected = "Fix critical authentication bug This commit addresses several issues: - Session timeout handling - Password validation - User role verification Fixes #123, #456"
        assert escaped_message == expected
        assert "\n" not in escaped_message

    def test_escape_commit_message_unicode_characters(self):
        """Test escaping commit message with Unicode characters."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        message = "Fix bug in 用户认证 system with émojis 🐛➡️✅"
        escaped_message = exporter._escape_commit_message(message)
        
        assert escaped_message == "Fix bug in 用户认证 system with émojis 🐛➡️✅"

    def test_escape_commit_message_very_long(self):
        """Test escaping very long commit message."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        # Create a very long message
        long_message = "Fix critical bug " * 100
        escaped_message = exporter._escape_commit_message(long_message)
        
        # Should not truncate - just clean up whitespace
        expected = "Fix critical bug " * 99 + "Fix critical bug"
        assert escaped_message == expected.strip()

    def test_escape_commit_message_special_csv_characters_combination(self):
        """Test escaping commit message with combination of CSV special characters."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        message = 'Fix "auth" bug,\nhandle user\'s session\r\nand "logout" properly'
        escaped_message = exporter._escape_commit_message(message)
        
        expected = 'Fix "auth" bug, handle user\'s session and "logout" properly'
        assert escaped_message == expected
        assert "\n" not in escaped_message
        assert "\r" not in escaped_message

    def test_commit_formatting_methods_integration(self):
        """Test integration of all commit formatting methods together."""
        config = CSVExportConfig(commit_date_format="%Y-%m-%d")
        exporter = CSVExporter(config)
        
        # Test data
        test_date = datetime(2023, 11, 15, 10, 30, 45)
        test_sha = "1234567890abcdef1234567890abcdef12345678"
        test_message = "Fix critical bug\nin authentication\nsystem"
        
        # Format all components
        formatted_date = exporter._format_commit_date(test_date)
        formatted_sha = exporter._format_commit_sha(test_sha)
        formatted_message = exporter._escape_commit_message(test_message)
        
        # Verify results
        assert formatted_date == "2023-11-15"
        assert formatted_sha == "1234567"
        assert formatted_message == "Fix critical bug in authentication system"

    def test_commit_formatting_edge_cases_all_none(self):
        """Test commit formatting methods with all None/empty inputs."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        # Test with None/empty values
        formatted_date = exporter._format_commit_date(None)
        formatted_sha = exporter._format_commit_sha("")
        formatted_message = exporter._escape_commit_message(None)
        
        # All should return empty strings
        assert formatted_date == ""
        assert formatted_sha == ""
        assert formatted_message == ""

    def test_commit_formatting_preserves_csv_writer_escaping(self):
        """Test that commit formatting preserves characters that CSV writer should escape."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        # Message with characters that CSV writer should handle
        message = 'Message with "quotes", commas, and other special chars'
        escaped_message = exporter._escape_commit_message(message)
        
        # Should preserve quotes and commas for CSV writer to handle
        assert '"' in escaped_message
        assert ',' in escaped_message
        assert escaped_message == 'Message with "quotes", commas, and other special chars'