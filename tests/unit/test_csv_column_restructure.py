"""Unit tests for CSV column restructure functionality."""
import pytest
from unittest.mock import Mock
from datetime import datetime

from forkscout.models.analysis import ForkPreviewItem, ForksPreview
from forkscout.reporting.csv_exporter import CSVExporter, CSVExportConfig


class TestCSVColumnRestructure:
    """Test suite for CSV column restructure functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = CSVExportConfig(include_urls=True, detail_mode=False)
        self.exporter = CSVExporter(self.config)
        
        # Create sample fork data
        self.sample_fork = ForkPreviewItem(
            name="test-fork",
            owner="testuser",
            stars=42,
            forks_count=10,
            fork_url="https://github.com/testuser/test-fork",
            activity_status="active",
            commits_ahead="5",
            commits_behind="2",
            last_push_date=datetime(2023, 12, 1)
        )

    def test_new_header_generation_basic_mode(self):
        """Test that headers are generated correctly in basic mode."""
        headers = self.exporter._generate_forks_preview_headers()
        expected_headers = ["Fork URL", "Stars", "Forks", "Commits Ahead", "Commits Behind"]
        assert headers == expected_headers

    def test_new_header_generation_detail_mode(self):
        """Test that headers are generated correctly in detail mode."""
        config = CSVExportConfig(include_urls=True, detail_mode=True)
        exporter = CSVExporter(config)
        headers = exporter._generate_forks_preview_headers()
        expected_headers = [
            "Fork URL", "Stars", "Forks", "Commits Ahead", "Commits Behind",
            "Last Push Date", "Created Date", "Updated Date"
        ]
        assert headers == expected_headers

    def test_removed_columns_not_in_headers(self):
        """Test that removed columns are not present in headers."""
        headers = self.exporter._generate_forks_preview_headers()
        removed_columns = ["fork_name", "owner", "activity_status"]
        for column in removed_columns:
            assert column not in headers

    def test_proper_column_naming(self):
        """Test that columns use proper title case with spaces."""
        headers = self.exporter._generate_forks_preview_headers()
        # Check that all headers use proper title case
        expected_format_headers = ["Fork URL", "Stars", "Forks", "Commits Ahead", "Commits Behind"]
        for header in expected_format_headers:
            assert header in headers
            # Verify no underscores or lowercase
            assert "_" not in header
            assert header[0].isupper()

    def test_fork_url_first_column(self):
        """Test that Fork URL is the first column."""
        headers = self.exporter._generate_forks_preview_headers()
        assert headers[0] == "Fork URL"

    def test_forks_column_after_stars(self):
        """Test that Forks column is positioned after Stars column."""
        headers = self.exporter._generate_forks_preview_headers()
        stars_index = headers.index("Stars")
        forks_index = headers.index("Forks")
        assert forks_index == stars_index + 1

    def test_commits_split_into_two_columns(self):
        """Test that commits are split into Ahead and Behind columns."""
        headers = self.exporter._generate_forks_preview_headers()
        assert "Commits Ahead" in headers
        assert "Commits Behind" in headers
        assert "commits_ahead" not in headers  # Old format should not be present

    def test_row_data_mapping_basic(self):
        """Test that row data is mapped correctly to new structure."""
        row = self.exporter._format_fork_preview_row(self.sample_fork)
        expected_data = {
            "Fork URL": "https://github.com/testuser/test-fork",
            "Stars": 42,
            "Forks": 10,
            "Commits Ahead": "5",
            "Commits Behind": "2",
        }
        for key, value in expected_data.items():
            assert row[key] == value

    def test_row_data_mapping_detail_mode(self):
        """Test that row data includes detail columns when enabled."""
        config = CSVExportConfig(include_urls=True, detail_mode=True)
        exporter = CSVExporter(config)
        row = exporter._format_fork_preview_row(self.sample_fork)
        assert "Last Push Date" in row
        assert "Created Date" in row
        assert "Updated Date" in row

    def test_missing_fork_url_handling(self):
        """Test graceful handling of missing Fork URL."""
        fork_no_url = ForkPreviewItem(
            name="test-fork",
            owner="testuser",
            stars=42,
            forks_count=10,
            fork_url="",  # Empty URL
            activity_status="active",
            commits_ahead="5",
            commits_behind="2"
        )
        row = self.exporter._format_fork_preview_row(fork_no_url)
        # Should handle empty string gracefully
        assert "Fork URL" in row
        assert row["Fork URL"] == ""

    def test_fork_url_column_always_present(self):
        """Test that Fork URL column is always present, even when URLs disabled."""
        config = CSVExportConfig(include_urls=False, detail_mode=False)
        exporter = CSVExporter(config)
        headers = exporter._generate_forks_preview_headers()
        assert "Fork URL" in headers
        assert headers[0] == "Fork URL"

    def test_fork_url_empty_when_urls_disabled(self):
        """Test that Fork URL column is empty when URLs are disabled."""
        config = CSVExportConfig(include_urls=False, detail_mode=False)
        exporter = CSVExporter(config)
        row = exporter._format_fork_preview_row(self.sample_fork)
        assert row["Fork URL"] == ""

    def test_removed_columns_not_in_row_data(self):
        """Test that removed columns are not present in row data."""
        row = self.exporter._format_fork_preview_row(self.sample_fork)
        removed_columns = ["fork_name", "owner", "activity_status"]
        for column in removed_columns:
            assert column not in row

    def test_data_integrity_preservation(self):
        """Test that essential data is preserved in new format."""
        row = self.exporter._format_fork_preview_row(self.sample_fork)
        # Essential data should be accessible through Fork URL
        assert "testuser/test-fork" in row["Fork URL"]
        assert row["Stars"] == self.sample_fork.stars
        assert row["Commits Ahead"] == self.sample_fork.commits_ahead

    def test_zero_values_handling(self):
        """Test handling of zero values in numeric columns."""
        fork_zeros = ForkPreviewItem(
            name="test-fork",
            owner="testuser",
            stars=0,
            forks_count=0,
            fork_url="https://github.com/testuser/test-fork",
            activity_status="active",
            commits_ahead="0",
            commits_behind="0"
        )
        row = self.exporter._format_fork_preview_row(fork_zeros)
        assert row["Stars"] == 0
        assert row["Forks"] == 0
        assert row["Commits Ahead"] == "0"
        assert row["Commits Behind"] == "0"

    def test_column_order_consistency(self):
        """Test that column order is consistent across different configurations."""
        # Basic mode
        headers_basic = self.exporter._generate_forks_preview_headers()
        # Detail mode
        config_detail = CSVExportConfig(include_urls=True, detail_mode=True)
        exporter_detail = CSVExporter(config_detail)
        headers_detail = exporter_detail._generate_forks_preview_headers()
        
        # First 5 columns should be the same
        assert headers_basic == headers_detail[:len(headers_basic)]
        # Fork URL should always be first
        assert headers_basic[0] == "Fork URL"
        assert headers_detail[0] == "Fork URL"

    def test_complete_csv_export(self):
        """Test complete CSV export workflow."""
        preview = ForksPreview(total_forks=1, forks=[self.sample_fork])
        csv_output = self.exporter.export_forks_preview(preview)
        
        lines = csv_output.strip().split('\n')
        assert len(lines) == 2  # Header + 1 data row
        
        # Check header
        header_line = lines[0]
        assert "Fork URL,Stars,Forks,Commits Ahead,Commits Behind" in header_line
        
        # Check data
        data_line = lines[1]
        assert "https://github.com/testuser/test-fork" in data_line
        assert "42" in data_line  # Stars
        assert "10" in data_line  # Forks