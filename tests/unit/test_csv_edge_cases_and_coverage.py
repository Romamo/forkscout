"""Unit tests for CSV edge cases and comprehensive coverage."""

import pytest
from datetime import datetime

from forklift.reporting.csv_exporter import CSVExporter, CSVExportConfig


class TestCSVEdgeCasesAndCoverage:
    """Test cases for CSV edge cases and comprehensive coverage."""

    def test_clean_text_for_csv_edge_cases(self):
        """Test _clean_text_for_csv with edge cases."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        # Test various edge cases
        test_cases = [
            ("", ""),
            (None, ""),
            ("normal text", "normal text"),
            ("text\nwith\nnewlines", "text with newlines"),
            ("text\rwith\rcarriage\rreturns", "text with carriage returns"),
            ("text\twith\ttabs", "text with tabs"),
            ("text   with    multiple     spaces", "text with multiple spaces"),
            ("text\x01with\x02control\x03chars", "textwithcontrolchars"),
        ]
        
        for input_text, expected in test_cases:
            result = exporter._clean_text_for_csv(input_text)
            if expected:
                assert expected in result or result == expected
            else:
                assert result == ""

    def test_escape_row_values_comprehensive(self):
        """Test _escape_row_values with comprehensive scenarios."""
        # Test with escaping enabled
        config = CSVExportConfig(escape_newlines=True)
        exporter = CSVExporter(config)
        
        test_row = {
            "string_field": "normal text",
            "newline_field": "text\nwith\nnewlines",
            "carriage_field": "text\rwith\rcarriage",
            "integer_field": 123,
            "boolean_field": True,
            "none_field": None,
        }
        
        result = exporter._escape_row_values(test_row)
        
        # Check string fields are escaped
        assert result["string_field"] == "normal text"
        assert result["newline_field"] == "text\\nwith\\nnewlines"
        assert result["carriage_field"] == "text\\rwith\\rcarriage"
        
        # Check non-string fields are unchanged
        assert result["integer_field"] == 123
        assert result["boolean_field"] is True
        assert result["none_field"] is None

    def test_escape_row_values_with_escaping_disabled(self):
        """Test _escape_row_values with escaping disabled."""
        config = CSVExportConfig(escape_newlines=False)
        exporter = CSVExporter(config)
        
        test_row = {
            "newline_field": "text\nwith\nnewlines",
            "carriage_field": "text\rwith\rcarriage",
        }
        
        result = exporter._escape_row_values(test_row)
        
        # Check that newlines are preserved when escaping is disabled
        assert result["newline_field"] == "text\nwith\nnewlines"
        assert result["carriage_field"] == "text\rwith\rcarriage"

    def test_validate_csv_compatibility_comprehensive(self):
        """Test CSV compatibility validation with comprehensive scenarios."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        # Test valid CSV
        valid_csv = '''name,description,count
repo1,"Simple description",100
repo2,"Description with, comma",200'''
        
        result = exporter.validate_csv_compatibility(valid_csv)
        assert result["is_valid"] is True
        assert result["statistics"]["total_rows"] == 3  # Including header
        assert result["statistics"]["total_columns"] == 3

    def test_validate_csv_compatibility_empty_csv(self):
        """Test CSV compatibility validation with empty CSV."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        result = exporter.validate_csv_compatibility("")
        assert result["is_valid"] is False
        assert any("empty" in issue.lower() for issue in result["issues"])

    def test_validate_csv_compatibility_inconsistent_columns(self):
        """Test CSV compatibility validation with inconsistent column counts."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        inconsistent_csv = '''name,description,count
repo1,desc1,100
repo2,desc2'''  # Missing third column
        
        result = exporter.validate_csv_compatibility(inconsistent_csv)
        
        assert result["is_valid"] is False
        assert any("Inconsistent column counts" in issue for issue in result["issues"])

    def test_format_commit_data_for_csv_comprehensive(self):
        """Test _format_commit_data_for_csv with comprehensive scenarios."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        test_cases = [
            (None, ""),
            ("", ""),
            ("simple commit data", "simple commit data"),
            ("commit\nwith\nnewlines", "commit with newlines"),
            ("commit\rwith\rcarriage\rreturns", "commit with carriage returns"),
            ("commit\twith\ttabs", "commit with tabs"),
            ("commit   with    multiple     spaces", "commit with multiple spaces"),
        ]
        
        for input_data, expected in test_cases:
            result = exporter._format_commit_data_for_csv(input_data)
            assert result == expected

    def test_format_dict_comprehensive(self):
        """Test _format_dict with comprehensive scenarios."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        test_cases = [
            ({}, ""),
            ({"key1": "value1"}, "key1=value1"),
            ({"key1": "value1", "key2": "value2"}, "key1=value1; key2=value2"),
            ({"key1": 123, "key2": 45.67, "key3": True}, "key1=123; key2=45.67; key3=True"),
        ]
        
        for input_dict, expected_pattern in test_cases:
            result = exporter._format_dict(input_dict)
            if expected_pattern:
                # Check that all key-value pairs are present
                for key, value in input_dict.items():
                    assert f"{key}={value}" in result
            else:
                assert result == ""

    def test_create_minimal_empty_row_comprehensive(self):
        """Test _create_minimal_empty_row with different configurations."""
        # Test with various configurations
        configs = [
            CSVExportConfig(),
            CSVExportConfig(include_urls=False),
            CSVExportConfig(detail_mode=True),
            CSVExportConfig(include_urls=True, detail_mode=True),
        ]
        
        for config in configs:
            exporter = CSVExporter(config)
            result = exporter._create_minimal_empty_row()
            
            # Should have all expected headers with empty values
            headers = exporter._generate_enhanced_fork_analysis_headers()
            assert len(result) == len(headers)
            assert all(key in result for key in headers)
            assert all(value == "" for value in result.values())

    def test_format_datetime_edge_cases(self):
        """Test _format_datetime with edge cases."""
        config = CSVExportConfig(date_format="%Y-%m-%d %H:%M:%S")
        exporter = CSVExporter(config)
        
        # Test None
        assert exporter._format_datetime(None) == ""
        
        # Test various datetime objects
        test_dates = [
            datetime(2023, 1, 1, 0, 0, 0),  # Start of year
            datetime(2023, 12, 31, 23, 59, 59),  # End of year
            datetime(2023, 2, 28, 12, 30, 45),  # Regular date
        ]
        
        for test_date in test_dates:
            result = exporter._format_datetime(test_date)
            assert len(result) > 0
            # Should be able to parse back
            parsed = datetime.strptime(result, "%Y-%m-%d %H:%M:%S")
            assert parsed == test_date

    def test_configuration_post_init_validation_comprehensive(self):
        """Test configuration validation in __post_init__ with comprehensive cases."""
        # Test that validation is called and works correctly
        valid_config = CSVExportConfig(
            date_format="%Y-%m-%d %H:%M:%S",
            commit_date_format="%Y-%m-%d"
        )
        assert valid_config.date_format == "%Y-%m-%d %H:%M:%S"
        assert valid_config.commit_date_format == "%Y-%m-%d"
        
        # Test that invalid formats raise errors
        with pytest.raises(ValueError, match="Invalid date_format"):
            CSVExportConfig(date_format=None)
        
        with pytest.raises(ValueError, match="Invalid commit_date_format"):
            CSVExportConfig(commit_date_format=None)

    def test_exporter_initialization_comprehensive(self):
        """Test CSVExporter initialization with comprehensive scenarios."""
        # Test with None config (should create default)
        exporter1 = CSVExporter(None)
        assert exporter1.config is not None
        assert isinstance(exporter1.config, CSVExportConfig)
        
        # Test with custom config
        custom_config = CSVExportConfig(include_urls=False, detail_mode=True)
        exporter2 = CSVExporter(custom_config)
        assert exporter2.config is custom_config
        assert exporter2.config.include_urls is False
        assert exporter2.config.detail_mode is True
        
        # Test with default (no arguments)
        exporter3 = CSVExporter()
        assert exporter3.config is not None
        assert isinstance(exporter3.config, CSVExportConfig)

    def test_error_handling_in_formatting_methods(self):
        """Test error handling in formatting methods."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        # Test _format_commit_sha with invalid types
        invalid_shas = [None, "", 123, [], {}]
        for invalid_sha in invalid_shas:
            result = exporter._format_commit_sha(invalid_sha)
            assert result == ""  # Should return empty string for invalid input
        
        # Test _escape_commit_message with invalid types
        invalid_messages = [None, 123, [], {}]
        for invalid_message in invalid_messages:
            result = exporter._escape_commit_message(invalid_message)
            # Should handle gracefully (convert to string or return empty)
            assert isinstance(result, str)
        
        # Test _format_commit_date with invalid dates
        invalid_dates = [None, "not a date", 123, []]
        for invalid_date in invalid_dates:
            result = exporter._format_commit_date(invalid_date)
            assert result == ""  # Should return empty string for invalid input

    def test_comprehensive_header_methods_coverage(self):
        """Test all header generation methods for comprehensive coverage."""
        config = CSVExportConfig(
            include_urls=True,
            detail_mode=True,
            include_commits=True,
            include_explanations=True
        )
        exporter = CSVExporter(config)
        
        # Test all header generation methods
        enhanced_headers = exporter._generate_enhanced_fork_analysis_headers()
        traditional_headers = exporter._generate_fork_analysis_headers()
        preview_headers = exporter._generate_forks_preview_headers()
        features_headers = exporter._generate_ranked_features_headers()
        explanations_headers = exporter._generate_commits_explanations_headers()
        
        # All should return non-empty lists
        for headers in [enhanced_headers, traditional_headers, preview_headers, features_headers, explanations_headers]:
            assert isinstance(headers, list)
            assert len(headers) > 0
            assert all(isinstance(h, str) for h in headers)

    def test_edge_case_data_types_handling(self):
        """Test handling of edge case data types in various methods."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        # Test _format_dict with various inputs
        dict_cases = [
            {},
            {"key": "value"},
            {"key": None},
            {"key": 123},
            {"key": True},
        ]
        
        for case in dict_cases:
            result = exporter._format_dict(case)
            assert isinstance(result, str)

    def test_csv_validation_statistics_comprehensive(self):
        """Test CSV validation statistics collection."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        # Test CSV with various characteristics
        test_csv = '''name,description,count
"repo1","Description with ""quotes""",100
repo2,"Description with, comma",200
repo3,Simple description,300'''
        
        result = exporter.validate_csv_compatibility(test_csv)
        
        # Check statistics are collected
        stats = result["statistics"]
        assert stats["total_rows"] == 4  # Including header
        assert stats["total_columns"] == 3
        assert stats["max_field_length"] > 0
        assert stats["fields_with_quotes"] > 0
        assert stats["fields_with_commas"] > 0
        assert isinstance(stats["fields_with_newlines"], int)

    def test_all_configuration_combinations_work(self):
        """Test that all configuration combinations work without errors."""
        # Test various boolean combinations
        boolean_combinations = [
            (True, True, True, True, True),
            (False, False, False, False, False),
            (True, False, True, False, True),
            (False, True, False, True, False),
        ]
        
        for include_urls, detail_mode, include_commits, include_explanations, escape_newlines in boolean_combinations:
            config = CSVExportConfig(
                include_urls=include_urls,
                detail_mode=detail_mode,
                include_commits=include_commits,
                include_explanations=include_explanations,
                escape_newlines=escape_newlines
            )
            exporter = CSVExporter(config)
            
            # Test that all header generation methods work
            enhanced_headers = exporter._generate_enhanced_fork_analysis_headers()
            traditional_headers = exporter._generate_fork_analysis_headers()
            preview_headers = exporter._generate_forks_preview_headers()
            
            # All should produce valid headers
            for headers in [enhanced_headers, traditional_headers, preview_headers]:
                assert isinstance(headers, list)
                assert len(headers) > 0
                assert all(isinstance(h, str) and len(h) > 0 for h in headers)