"""Unit tests for CSV configuration enhancement functionality."""

import pytest
from datetime import datetime

from forkscout.reporting.csv_exporter import CSVExportConfig, CSVExporter


class TestCSVConfigurationEnhancement:
    """Test cases for CSV configuration enhancement with various option combinations."""

    def test_default_configuration_values(self):
        """Test that default configuration values are set correctly."""
        config = CSVExportConfig()
        
        # Test all default values
        assert config.include_commits is False
        assert config.detail_mode is False
        assert config.include_explanations is False
        assert config.max_commits_per_fork == 10
        assert config.escape_newlines is True
        assert config.include_urls is True
        assert config.date_format == "%Y-%m-%d %H:%M:%S"
        assert config.commit_date_format == "%Y-%m-%d"

    def test_configuration_with_all_options_enabled(self):
        """Test configuration with all options enabled."""
        config = CSVExportConfig(
            include_commits=True,
            detail_mode=True,
            include_explanations=True,
            max_commits_per_fork=20,
            escape_newlines=True,
            include_urls=True,
            date_format="%Y-%m-%d %H:%M:%S",
            commit_date_format="%Y-%m-%d %H:%M"
        )
        
        assert config.include_commits is True
        assert config.detail_mode is True
        assert config.include_explanations is True
        assert config.max_commits_per_fork == 20
        assert config.escape_newlines is True
        assert config.include_urls is True
        assert config.date_format == "%Y-%m-%d %H:%M:%S"
        assert config.commit_date_format == "%Y-%m-%d %H:%M"

    def test_configuration_with_all_options_disabled(self):
        """Test configuration with all options disabled."""
        config = CSVExportConfig(
            include_commits=False,
            detail_mode=False,
            include_explanations=False,
            max_commits_per_fork=5,
            escape_newlines=False,
            include_urls=False,
            date_format="%Y-%m-%d",
            commit_date_format="%d/%m/%Y"
        )
        
        assert config.include_commits is False
        assert config.detail_mode is False
        assert config.include_explanations is False
        assert config.max_commits_per_fork == 5
        assert config.escape_newlines is False
        assert config.include_urls is False
        assert config.date_format == "%Y-%m-%d"
        assert config.commit_date_format == "%d/%m/%Y"

    def test_configuration_mixed_options_combination_1(self):
        """Test configuration with mixed options - combination 1."""
        config = CSVExportConfig(
            include_commits=True,
            detail_mode=False,
            include_explanations=True,
            max_commits_per_fork=15,
            escape_newlines=False,
            include_urls=True,
            date_format="%d/%m/%Y %H:%M",
            commit_date_format="%Y-%m-%d"
        )
        
        assert config.include_commits is True
        assert config.detail_mode is False
        assert config.include_explanations is True
        assert config.max_commits_per_fork == 15
        assert config.escape_newlines is False
        assert config.include_urls is True
        assert config.date_format == "%d/%m/%Y %H:%M"
        assert config.commit_date_format == "%Y-%m-%d"

    def test_configuration_mixed_options_combination_2(self):
        """Test configuration with mixed options - combination 2."""
        config = CSVExportConfig(
            include_commits=False,
            detail_mode=True,
            include_explanations=False,
            max_commits_per_fork=25,
            escape_newlines=True,
            include_urls=False,
            date_format="%Y%m%d",
            commit_date_format="%B %d, %Y"
        )
        
        assert config.include_commits is False
        assert config.detail_mode is True
        assert config.include_explanations is False
        assert config.max_commits_per_fork == 25
        assert config.escape_newlines is True
        assert config.include_urls is False
        assert config.date_format == "%Y%m%d"
        assert config.commit_date_format == "%B %d, %Y"

    def test_commit_date_format_validation_with_various_formats(self):
        """Test commit date format validation with various valid formats."""
        valid_formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%B %d, %Y",
            "%Y%m%d",
            "%d-%m-%Y",
            "%Y.%m.%d",
            "%d.%m.%Y",
            "%Y/%m/%d %H:%M",
            "%d %B %Y",
            "%a, %d %b %Y %H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ"
        ]
        
        for date_format in valid_formats:
            config = CSVExportConfig(commit_date_format=date_format)
            assert config.commit_date_format == date_format

    def test_date_format_validation_with_various_formats(self):
        """Test general date format validation with various valid formats."""
        valid_formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M:%S",
            "%m/%d/%Y %I:%M %p",
            "%B %d, %Y %H:%M",
            "%Y%m%d%H%M%S",
            "%d-%m-%Y %H:%M",
            "%Y.%m.%d %H:%M:%S",
            "%a %b %d %H:%M:%S %Y",
            "%Y-%m-%dT%H:%M:%S.%fZ"
        ]
        
        for date_format in valid_formats:
            config = CSVExportConfig(date_format=date_format)
            assert config.date_format == date_format

    def test_commit_date_format_validation_with_invalid_format(self):
        """Test commit date format validation with invalid format."""
        with pytest.raises(ValueError, match="Invalid commit_date_format"):
            CSVExportConfig(commit_date_format=None)

    def test_date_format_validation_with_invalid_format(self):
        """Test general date format validation with invalid format."""
        with pytest.raises(ValueError, match="Invalid date_format"):
            CSVExportConfig(date_format=None)

    def test_max_commits_per_fork_various_values(self):
        """Test max_commits_per_fork with various valid values."""
        test_values = [1, 5, 10, 15, 20, 50, 100, 1000]
        
        for value in test_values:
            config = CSVExportConfig(max_commits_per_fork=value)
            assert config.max_commits_per_fork == value

    def test_configuration_immutability_after_creation(self):
        """Test that configuration values can be modified after creation."""
        config = CSVExportConfig()
        
        # Modify values (this should work as dataclass fields are mutable by default)
        config.include_commits = True
        config.detail_mode = True
        config.max_commits_per_fork = 25
        
        assert config.include_commits is True
        assert config.detail_mode is True
        assert config.max_commits_per_fork == 25

    def test_configuration_with_exporter_integration(self):
        """Test that configuration integrates properly with CSVExporter."""
        config = CSVExportConfig(
            include_commits=True,
            detail_mode=True,
            include_explanations=True,
            max_commits_per_fork=15,
            escape_newlines=False,
            include_urls=False,
            date_format="%d/%m/%Y %H:%M",
            commit_date_format="%d/%m/%Y"
        )
        
        exporter = CSVExporter(config)
        
        # Verify configuration is properly set
        assert exporter.config.include_commits is True
        assert exporter.config.detail_mode is True
        assert exporter.config.include_explanations is True
        assert exporter.config.max_commits_per_fork == 15
        assert exporter.config.escape_newlines is False
        assert exporter.config.include_urls is False
        assert exporter.config.date_format == "%d/%m/%Y %H:%M"
        assert exporter.config.commit_date_format == "%d/%m/%Y"

    def test_configuration_default_exporter_creation(self):
        """Test that CSVExporter creates default configuration when none provided."""
        exporter = CSVExporter()
        
        # Should have default configuration
        assert exporter.config is not None
        assert exporter.config.include_commits is False
        assert exporter.config.detail_mode is False
        assert exporter.config.include_explanations is False
        assert exporter.config.max_commits_per_fork == 10
        assert exporter.config.escape_newlines is True
        assert exporter.config.include_urls is True
        assert exporter.config.date_format == "%Y-%m-%d %H:%M:%S"
        assert exporter.config.commit_date_format == "%Y-%m-%d"

    def test_configuration_validation_edge_cases(self):
        """Test configuration validation with edge cases."""
        # Test with zero max_commits_per_fork (should be allowed)
        config = CSVExportConfig(max_commits_per_fork=0)
        assert config.max_commits_per_fork == 0
        
        # Test with very large max_commits_per_fork
        config = CSVExportConfig(max_commits_per_fork=10000)
        assert config.max_commits_per_fork == 10000

    def test_configuration_date_format_functionality(self):
        """Test that date formats actually work for formatting dates."""
        test_date = datetime(2023, 11, 15, 14, 30, 45)
        
        # Test various date format configurations
        format_tests = [
            ("%Y-%m-%d", "2023-11-15"),
            ("%Y-%m-%d %H:%M:%S", "2023-11-15 14:30:45"),
            ("%d/%m/%Y", "15/11/2023"),
            ("%B %d, %Y", "November 15, 2023"),
            ("%Y%m%d", "20231115"),
        ]
        
        for date_format, expected in format_tests:
            config = CSVExportConfig(date_format=date_format)
            exporter = CSVExporter(config)
            
            formatted = exporter._format_datetime(test_date)
            assert formatted == expected

    def test_configuration_commit_date_format_functionality(self):
        """Test that commit date formats actually work for formatting dates."""
        test_date = datetime(2023, 11, 15, 14, 30, 45)
        
        # Test various commit date format configurations
        format_tests = [
            ("%Y-%m-%d", "2023-11-15"),
            ("%Y-%m-%d %H:%M", "2023-11-15 14:30"),
            ("%d/%m/%Y", "15/11/2023"),
            ("%B %d, %Y", "November 15, 2023"),
            ("%Y%m%d", "20231115"),
        ]
        
        for commit_date_format, expected in format_tests:
            config = CSVExportConfig(commit_date_format=commit_date_format)
            exporter = CSVExporter(config)
            
            formatted = exporter._format_commit_date(test_date)
            assert formatted == expected

    def test_configuration_boolean_combinations(self):
        """Test all possible boolean option combinations."""
        boolean_options = [
            'include_commits',
            'detail_mode', 
            'include_explanations',
            'escape_newlines',
            'include_urls'
        ]
        
        # Test a few key combinations (testing all 32 combinations would be excessive)
        test_combinations = [
            (True, True, True, True, True),
            (False, False, False, False, False),
            (True, False, True, False, True),
            (False, True, False, True, False),
            (True, True, False, False, False),
        ]
        
        for combination in test_combinations:
            config_kwargs = dict(zip(boolean_options, combination))
            config = CSVExportConfig(**config_kwargs)
            
            for option, expected_value in zip(boolean_options, combination):
                assert getattr(config, option) == expected_value

    def test_configuration_with_custom_formats_integration(self):
        """Test configuration with custom formats integrated with exporter methods."""
        config = CSVExportConfig(
            date_format="%d %B %Y at %H:%M",
            commit_date_format="%d-%m-%Y"
        )
        exporter = CSVExporter(config)
        
        test_date = datetime(2023, 11, 15, 14, 30, 45)
        
        # Test general date formatting
        general_formatted = exporter._format_datetime(test_date)
        assert general_formatted == "15 November 2023 at 14:30"
        
        # Test commit date formatting
        commit_formatted = exporter._format_commit_date(test_date)
        assert commit_formatted == "15-11-2023"

    def test_configuration_validation_post_init_called(self):
        """Test that __post_init__ validation is called during configuration creation."""
        # This should work without raising an exception
        config = CSVExportConfig(
            date_format="%Y-%m-%d %H:%M:%S",
            commit_date_format="%Y-%m-%d"
        )
        assert config.date_format == "%Y-%m-%d %H:%M:%S"
        assert config.commit_date_format == "%Y-%m-%d"
        
        # This should raise an exception due to invalid format
        with pytest.raises(ValueError):
            CSVExportConfig(date_format=None)
            
        with pytest.raises(ValueError):
            CSVExportConfig(commit_date_format=None)