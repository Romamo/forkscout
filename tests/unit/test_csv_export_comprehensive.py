"""Comprehensive unit tests for CSV export functionality."""

import csv
import io
import tempfile
from datetime import datetime, UTC
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from forklift.models.analysis import (
    CategoryType,
    CommitCategory,
    CommitExplanation,
    CommitWithExplanation,
    Feature,
    FeatureCategory,
    ForkAnalysis,
    ForkMetrics,
    ForkPreviewItem,
    ForksPreview,
    ImpactAssessment,
    ImpactLevel,
    MainRepoValue,
    RankedFeature,
)
from forklift.models.github import Commit, Fork, Repository, User
from forklift.reporting.csv_exporter import CSVExportConfig, CSVExporter


class TestCSVSpecialCharacterHandling:
    """Test CSV export with special characters and edge cases."""

    @pytest.fixture
    def exporter(self):
        """Create a CSV exporter with default config."""
        return CSVExporter()

    @pytest.fixture
    def special_chars_fork_preview(self):
        """Create fork preview with special characters."""
        forks = [
            ForkPreviewItem(
                name='repo,with"commas',
                owner="user\nwith\nnewlines",
                stars=10,
                last_push_date=datetime(2023, 6, 15, 12, 0, 0),
                fork_url="https://github.com/user/repo",
                activity_status="Active,Status",
                commits_ahead="Unknown",
                recent_commits='Fix "auth" bug\nAdd feature, update docs\r\nRefactor code'
            ),
            ForkPreviewItem(
                name="repo\twith\ttabs",
                owner="user'with'quotes",
                stars=5,
                last_push_date=datetime(2023, 5, 1, 12, 0, 0),
                fork_url="https://github.com/user2/repo",
                activity_status="Stale\r\nStatus",
                commits_ahead="None",
                recent_commits=""
            ),
            ForkPreviewItem(
                name="repo;with;semicolons",
                owner="user|with|pipes",
                stars=15,
                last_push_date=datetime(2023, 7, 1, 12, 0, 0),
                fork_url="https://github.com/user3/repo",
                activity_status="Very Active",
                commits_ahead="3",
                recent_commits="Commit with unicode: 你好世界 🚀 ñáéíóú"
            )
        ]
        return ForksPreview(total_forks=3, forks=forks)

    def test_csv_handles_commas_in_data(self, exporter, special_chars_fork_preview):
        """Test that commas in data are properly handled by CSV quoting."""
        csv_output = exporter.export_forks_preview(special_chars_fork_preview)
        
        # Parse CSV to verify it's valid
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        
        assert len(rows) == 3
        
        # Check that commas are preserved in quoted fields
        assert rows[0]["fork_name"] == 'repo,with"commas'
        assert rows[0]["activity_status"] == "Active,Status"

    def test_csv_handles_quotes_in_data(self, exporter, special_chars_fork_preview):
        """Test that quotes in data are properly escaped."""
        csv_output = exporter.export_forks_preview(special_chars_fork_preview)
        
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        
        # Check that quotes are preserved
        assert rows[0]["fork_name"] == 'repo,with"commas'
        assert rows[1]["owner"] == "user'with'quotes"

    def test_csv_handles_newlines_with_escaping(self, exporter, special_chars_fork_preview):
        """Test that newlines are escaped when escaping is enabled."""
        csv_output = exporter.export_forks_preview(special_chars_fork_preview)
        
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        
        # Check that newlines are escaped
        assert "\\n" in rows[0]["owner"]
        assert "\\r\\n" in rows[1]["activity_status"]

    def test_csv_handles_newlines_without_escaping(self, special_chars_fork_preview):
        """Test that newlines are preserved when escaping is disabled."""
        config = CSVExportConfig(escape_newlines=False)
        exporter = CSVExporter(config)
        
        csv_output = exporter.export_forks_preview(special_chars_fork_preview)
        
        # Raw CSV should contain actual newlines
        assert "\n" in csv_output
        assert "\r" in csv_output

    def test_csv_handles_tabs_and_special_chars(self, exporter, special_chars_fork_preview):
        """Test that tabs and other special characters are handled."""
        csv_output = exporter.export_forks_preview(special_chars_fork_preview)
        
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        
        # Check that tabs and other special chars are preserved
        assert rows[1]["fork_name"] == "repo\twith\ttabs"
        assert rows[2]["fork_name"] == "repo;with;semicolons"
        assert rows[2]["owner"] == "user|with|pipes"

    def test_csv_handles_unicode_characters(self, exporter, special_chars_fork_preview):
        """Test that Unicode characters are properly handled."""
        # Use config that includes commits to get recent_commits column
        config = CSVExportConfig(include_commits=True)
        exporter = CSVExporter(config)
        
        csv_output = exporter.export_forks_preview(special_chars_fork_preview)
        
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        
        # Check that Unicode characters are preserved
        recent_commits = rows[2]["recent_commits"]
        assert "你好世界" in recent_commits
        assert "🚀" in recent_commits
        assert "ñáéíóú" in recent_commits

    def test_csv_handles_empty_and_none_values(self, exporter):
        """Test that empty and None values are handled properly."""
        fork_item = ForkPreviewItem(
            name="",  # Empty string
            owner="testuser",
            stars=0,
            last_push_date=None,  # None value
            fork_url="https://github.com/testuser/repo",
            activity_status="",  # Empty string
            commits_ahead="",
            recent_commits=None  # None value
        )
        
        preview = ForksPreview(total_forks=1, forks=[fork_item])
        csv_output = exporter.export_forks_preview(preview)
        
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        
        assert len(rows) == 1
        assert rows[0]["fork_name"] == ""
        assert rows[0]["activity_status"] == ""

    def test_csv_handles_very_long_strings(self, exporter):
        """Test that very long strings are handled properly."""
        long_description = "A" * 10000  # Very long string
        long_commit_message = "B" * 5000
        
        # Use config that includes commits to get recent_commits column
        config = CSVExportConfig(include_commits=True)
        exporter = CSVExporter(config)
        
        fork_item = ForkPreviewItem(
            name="test-repo",
            owner="testuser",
            stars=10,
            last_push_date=datetime(2023, 6, 15, 12, 0, 0),
            fork_url="https://github.com/testuser/repo",
            activity_status=long_description,
            commits_ahead="3",
            recent_commits=long_commit_message
        )
        
        preview = ForksPreview(total_forks=1, forks=[fork_item])
        csv_output = exporter.export_forks_preview(preview)
        
        # Should not raise an exception
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        
        assert len(rows) == 1
        assert len(rows[0]["activity_status"]) == 10000
        assert len(rows[0]["recent_commits"]) == 5000


class TestCSVOutputRedirectionCompatibility:
    """Test CSV export compatibility with output redirection and piping."""

    @pytest.fixture
    def exporter(self):
        """Create a CSV exporter."""
        return CSVExporter()

    @pytest.fixture
    def sample_fork_preview(self):
        """Create a simple fork preview for testing."""
        forks = [
            ForkPreviewItem(
                name="test-repo",
                owner="testuser",
                stars=10,
                last_push_date=datetime(2023, 6, 15, 12, 0, 0),
                fork_url="https://github.com/testuser/repo",
                activity_status="Active",
                commits_ahead="3"
            )
        ]
        return ForksPreview(total_forks=1, forks=forks)

    def test_csv_output_to_file(self, exporter, sample_fork_preview):
        """Test CSV export to file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_path = f.name
        
        try:
            # Export to file
            csv_content = exporter.export_to_csv(sample_fork_preview, temp_path)
            
            # Verify file was created and contains expected content
            with open(temp_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Normalize line endings for comparison (CSV module may use different line endings)
            normalized_file_content = file_content.replace("\r\n", "\n").replace("\r", "\n")
            normalized_csv_output = csv_content.replace("\r\n", "\n").replace("\r", "\n")
            assert normalized_file_content == normalized_csv_output
            assert "fork_name,owner,stars" in file_content
            assert "test-repo,testuser,10" in file_content
            
        finally:
            # Clean up
            Path(temp_path).unlink(missing_ok=True)

    def test_csv_output_to_file_object(self, exporter, sample_fork_preview):
        """Test CSV export to file object."""
        output_buffer = io.StringIO()
        
        csv_content = exporter.export_to_csv(sample_fork_preview, output_buffer)
        
        # Verify buffer contains expected content
        buffer_content = output_buffer.getvalue()
        assert buffer_content == csv_content
        assert "fork_name,owner,stars" in buffer_content

    def test_csv_output_encoding_utf8(self, exporter):
        """Test that CSV output is properly UTF-8 encoded."""
        fork_item = ForkPreviewItem(
            name="test-repo-ñáéíóú",
            owner="user-你好世界",
            stars=10,
            last_push_date=datetime(2023, 6, 15, 12, 0, 0),
            fork_url="https://github.com/testuser/repo",
            activity_status="Active 🚀",
            commits_ahead="3"
        )
        
        preview = ForksPreview(total_forks=1, forks=[fork_item])
        csv_output = exporter.export_forks_preview(preview)
        
        # Should be valid UTF-8
        encoded = csv_output.encode('utf-8')
        decoded = encoded.decode('utf-8')
        assert decoded == csv_output

    def test_csv_line_endings_consistency(self, exporter, sample_fork_preview):
        """Test that CSV uses consistent line endings."""
        csv_output = exporter.export_forks_preview(sample_fork_preview)
        
        # Should use consistent line endings (Python csv module default)
        lines = csv_output.split('\n')
        assert len(lines) >= 2  # Header + at least one data row
        
        # No mixed line endings
        assert '\r\n' not in csv_output or '\n' not in csv_output.replace('\r\n', '')

    def test_csv_no_bom(self, exporter, sample_fork_preview):
        """Test that CSV output doesn't include BOM (Byte Order Mark)."""
        csv_output = exporter.export_forks_preview(sample_fork_preview)
        
        # Should not start with BOM
        assert not csv_output.startswith('\ufeff')
        assert not csv_output.encode('utf-8').startswith(b'\xef\xbb\xbf')


class TestCSVSpreadsheetCompatibility:
    """Test CSV export compatibility with spreadsheet applications."""

    @pytest.fixture
    def exporter(self):
        """Create a CSV exporter."""
        return CSVExporter()

    @pytest.fixture
    def spreadsheet_test_data(self):
        """Create test data that might cause issues in spreadsheets."""
        forks = [
            ForkPreviewItem(
                name="=SUM(1+1)",  # Formula that might be interpreted by Excel
                owner="testuser",
                stars=10,
                last_push_date=datetime(2023, 6, 15, 12, 0, 0),
                fork_url="https://github.com/testuser/repo",
                activity_status="Active",
                commits_ahead="3"
            ),
            ForkPreviewItem(
                name="@CELL",  # Another potential formula
                owner="user2",
                stars=5,
                last_push_date=datetime(2023, 5, 1, 12, 0, 0),
                fork_url="https://github.com/user2/repo",
                activity_status="+CMD|' /C calc'!A0",  # Potential command injection
                commits_ahead="None"
            ),
            ForkPreviewItem(
                name="1234567890123456",  # Long number that might be formatted as scientific notation
                owner="user3",
                stars=0,
                last_push_date=datetime(2023, 4, 1, 12, 0, 0),
                fork_url="https://github.com/user3/repo",
                activity_status="Inactive",
                commits_ahead="0"
            )
        ]
        return ForksPreview(total_forks=3, forks=forks)

    def test_csv_formula_safety(self, exporter, spreadsheet_test_data):
        """Test that potential formulas are treated as text."""
        csv_output = exporter.export_forks_preview(spreadsheet_test_data)
        
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        
        # Formulas should be preserved as text
        assert rows[0]["fork_name"] == "=SUM(1+1)"
        assert rows[1]["fork_name"] == "@CELL"
        assert rows[1]["activity_status"] == "+CMD|' /C calc'!A0"

    def test_csv_number_formatting(self, exporter, spreadsheet_test_data):
        """Test that numbers are properly formatted for spreadsheets."""
        csv_output = exporter.export_forks_preview(spreadsheet_test_data)
        
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        
        # Numbers should be preserved as strings in CSV
        assert rows[0]["stars"] == "10"
        assert rows[1]["stars"] == "5"
        assert rows[2]["stars"] == "0"
        
        # Long numbers should be preserved
        assert rows[2]["fork_name"] == "1234567890123456"

    def test_csv_date_formatting_for_spreadsheets(self, exporter):
        """Test that dates are formatted consistently for spreadsheet import."""
        fork_item = ForkPreviewItem(
            name="test-repo",
            owner="testuser",
            stars=10,
            last_push_date=datetime(2023, 6, 15, 14, 30, 45),
            fork_url="https://github.com/testuser/repo",
            activity_status="Active",
            commits_ahead="3"
        )
        
        # Test with detail mode to include dates
        config = CSVExportConfig(detail_mode=True)
        exporter = CSVExporter(config)
        
        preview = ForksPreview(total_forks=1, forks=[fork_item])
        csv_output = exporter.export_forks_preview(preview)
        
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        
        # Date should be in consistent format
        assert rows[0]["last_push_date"] == "2023-06-15 14:30:45"

    def test_csv_custom_date_format(self, spreadsheet_test_data):
        """Test CSV with custom date format for spreadsheet compatibility."""
        # Use ISO date format that's widely supported
        config = CSVExportConfig(date_format="%Y-%m-%d")
        exporter = CSVExporter(config)
        
        csv_output = exporter.export_forks_preview(spreadsheet_test_data)
        
        # Should not raise an exception and produce valid CSV
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        assert len(rows) == 3


class TestCSVPerformanceWithLargeData:
    """Test CSV export performance with large datasets."""

    @pytest.fixture
    def large_fork_dataset(self):
        """Create a large dataset for performance testing."""
        forks = []
        for i in range(1000):  # 1000 forks
            fork = ForkPreviewItem(
                name=f"test-repo-{i}",
                owner=f"user{i}",
                stars=i % 100,
                last_push_date=datetime(2023, 6, 15, 12, 0, 0),
                fork_url=f"https://github.com/user{i}/test-repo-{i}",
                activity_status="Active" if i % 2 == 0 else "Stale",
                commits_ahead=str(i % 10) if i % 5 != 0 else "None"
            )
            forks.append(fork)
        
        return ForksPreview(total_forks=1000, forks=forks)

    def test_csv_export_large_dataset_performance(self, large_fork_dataset):
        """Test CSV export performance with large dataset."""
        exporter = CSVExporter()
        
        import time
        start_time = time.time()
        
        csv_output = exporter.export_forks_preview(large_fork_dataset)
        
        end_time = time.time()
        export_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert export_time < 5.0  # 5 seconds for 1000 forks
        
        # Verify output is correct
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        assert len(rows) == 1000

    def test_csv_export_memory_usage(self, large_fork_dataset):
        """Test that CSV export doesn't consume excessive memory."""
        exporter = CSVExporter()
        
        # Export should not raise memory errors
        csv_output = exporter.export_forks_preview(large_fork_dataset)
        
        # Verify output size is reasonable
        output_size_mb = len(csv_output.encode('utf-8')) / (1024 * 1024)
        assert output_size_mb < 50  # Should be less than 50MB for 1000 forks

    def test_csv_export_with_large_commit_data(self):
        """Test CSV export with large commit data per fork."""
        # Create fork with large commit data
        large_commit_data = "; ".join([
            f"2023-06-{i:02d} abc{i:04d} Commit message {i} with some details"
            for i in range(1, 101)  # 100 commits
        ])
        
        fork_item = ForkPreviewItem(
            name="test-repo",
            owner="testuser",
            stars=10,
            last_push_date=datetime(2023, 6, 15, 12, 0, 0),
            fork_url="https://github.com/testuser/repo",
            activity_status="Active",
            commits_ahead="100",
            recent_commits=large_commit_data
        )
        
        config = CSVExportConfig(include_commits=True)
        exporter = CSVExporter(config)
        
        preview = ForksPreview(total_forks=1, forks=[fork_item])
        csv_output = exporter.export_forks_preview(preview)
        
        # Should handle large commit data without issues
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        
        assert len(rows) == 1
        assert len(rows[0]["recent_commits"]) > 1000  # Large commit data preserved


class TestCSVEndToEndWorkflows:
    """Test complete CSV export workflows."""

    @pytest.fixture
    def exporter(self):
        """Create a CSV exporter."""
        return CSVExporter()

    @pytest.fixture
    def complete_fork_analysis_data(self):
        """Create complete fork analysis data for end-to-end testing."""
        # Create sample user
        user = User(
            id=123,
            login="testuser",
            name="Test User",
            html_url="https://github.com/testuser"
        )
        
        # Create sample repository
        repository = Repository(
            id=456,
            owner="testuser",
            name="test-repo",
            full_name="testuser/test-repo",
            url="https://api.github.com/repos/testuser/test-repo",
            html_url="https://github.com/testuser/test-repo",
            clone_url="https://github.com/testuser/test-repo.git",
            stars=10,
            forks_count=2,
            language="Python",
            description="Test repository",
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            updated_at=datetime(2023, 6, 1, 12, 0, 0),
            pushed_at=datetime(2023, 6, 15, 12, 0, 0)
        )
        
        # Create fork repository (marked as fork with different owner)
        fork_repository = Repository(
            id=789,
            owner="forkuser",  # Different owner
            name="test-repo",
            full_name="forkuser/test-repo",  # Different full name
            url="https://api.github.com/repos/forkuser/test-repo",
            html_url="https://github.com/forkuser/test-repo",
            clone_url="https://github.com/forkuser/test-repo.git",
            stars=5,  # Different stats
            forks_count=1,
            language="Python",
            description="Forked test repository",
            is_fork=True,  # Mark as fork
            created_at=datetime(2023, 2, 1, 12, 0, 0),  # Different dates
            updated_at=datetime(2023, 6, 10, 12, 0, 0),
            pushed_at=datetime(2023, 6, 20, 12, 0, 0)
        )
        
        # Create fork user (different from repository owner)
        fork_user = User(
            id=456,
            login="forkuser",
            name="Fork User",
            html_url="https://github.com/forkuser"
        )
        
        # Create sample fork
        fork = Fork(
            repository=fork_repository,
            parent=repository,  # Parent repository
            owner=fork_user,  # Fork owner
            last_activity=datetime(2023, 6, 20, 12, 0, 0),
            commits_ahead=3,
            commits_behind=1,
            is_active=True
        )
        
        # Create sample commit
        commit = Commit(
            sha="abc123def456789012345678901234567890abcd",  # 40 character SHA
            message="Add new feature\n\nDetailed description",
            author=user,
            date=datetime(2023, 6, 15, 10, 30, 0),
            files_changed=["src/main.py", "tests/test_main.py"],
            additions=50,
            deletions=10
        )
        
        # Create sample feature
        feature = Feature(
            id="feat_1",
            title="Authentication System",
            description="JWT-based authentication",
            category=FeatureCategory.NEW_FEATURE,
            commits=[commit],
            files_affected=["src/auth.py", "tests/test_auth.py"],
            source_fork=fork
        )
        
        # Create fork analysis
        metrics = ForkMetrics(
            stars=10,
            forks=2,
            contributors=1,
            last_activity=datetime(2023, 6, 15, 12, 0, 0),
            commit_frequency=0.5
        )
        
        analysis = ForkAnalysis(
            fork=fork,
            features=[feature],
            metrics=metrics,
            analysis_date=datetime(2023, 6, 16, 12, 0, 0)
        )
        
        return [analysis]

    def test_complete_fork_analysis_csv_export(self, exporter, complete_fork_analysis_data):
        """Test complete fork analysis CSV export workflow."""
        csv_output = exporter.export_fork_analyses(complete_fork_analysis_data)
        
        # Verify CSV is valid and contains expected data
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        
        assert len(rows) == 1
        
        row = rows[0]
        assert row["fork_name"] == "test-repo"
        assert row["owner"] == "forkuser"  # Fork owner, not original repo owner
        assert row["stars"] == "5"  # Fork stars, not original repo stars
        assert row["features_count"] == "1"
        assert row["is_active"] == "True"

    def test_complete_workflow_with_all_export_types(self, exporter):
        """Test complete workflow with all supported export types."""
        # Test forks preview
        preview = ForksPreview(total_forks=0, forks=[])
        preview_csv = exporter.export_to_csv(preview)
        assert "fork_name" in preview_csv
        
        # Test empty lists
        empty_csv = exporter.export_to_csv([])
        assert "No data to export" in empty_csv
        
        # Test unsupported type
        with pytest.raises(ValueError, match="Unsupported data type"):
            exporter.export_to_csv("invalid_data")

    def test_csv_export_with_all_configuration_options(self):
        """Test CSV export with all configuration options enabled."""
        config = CSVExportConfig(
            include_commits=True,
            detail_mode=True,
            include_explanations=True,
            max_commits_per_fork=5,
            escape_newlines=True,
            include_urls=True,
            date_format="%Y-%m-%d %H:%M:%S"
        )
        
        exporter = CSVExporter(config)
        
        # Create minimal test data
        fork_item = ForkPreviewItem(
            name="test-repo",
            owner="testuser",
            stars=10,
            last_push_date=datetime(2023, 6, 15, 12, 0, 0),
            fork_url="https://github.com/testuser/repo",
            activity_status="Active",
            commits_ahead="3"
        )
        
        preview = ForksPreview(total_forks=1, forks=[fork_item])
        csv_output = exporter.export_forks_preview(preview)
        
        # Should include all configured headers
        reader = csv.DictReader(io.StringIO(csv_output))
        headers = reader.fieldnames
        
        assert "fork_url" in headers  # include_urls=True
        assert "last_push_date" in headers  # detail_mode=True
        assert "recent_commits" in headers  # include_commits=True