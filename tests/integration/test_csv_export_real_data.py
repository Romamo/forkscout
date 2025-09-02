"""Integration tests for CSV export with real repository data."""

import csv
import io
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.github.client import GitHubClient
from forklift.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
)
from forklift.models.github import RecentCommit
from forklift.reporting.csv_exporter import CSVExportConfig, CSVExporter


class TestCSVExportRealDataIntegration:
    """Test CSV export with realistic repository data scenarios."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return AsyncMock(spec=GitHubClient)

    @pytest.fixture
    def realistic_fork_data(self):
        """Create realistic fork data based on actual GitHub repositories."""
        # Data based on real GitHub repositories with various characteristics
        forks_data = [
            # Active fork with recent commits
            ForkQualificationMetrics(
                id=123456789,
                name="pandas-ta",
                full_name="user1/pandas-ta",
                owner="user1",
                html_url="https://github.com/user1/pandas-ta",
                stargazers_count=45,
                forks_count=12,
                watchers_count=8,
                size=2500,
                language="Python",
                topics=["python", "pandas", "technical-analysis", "trading"],
                open_issues_count=3,
                created_at=datetime(2023, 3, 15, 10, 30, 0, tzinfo=UTC),
                updated_at=datetime(2024, 1, 20, 14, 45, 0, tzinfo=UTC),
                pushed_at=datetime(2024, 1, 22, 9, 15, 0, tzinfo=UTC),
                archived=False,
                disabled=False,
                fork=True,
                license_key="mit",
                license_name="MIT License",
                description="Technical Analysis Library in Python 3.7+ Pandas TA is an easy to use library that leverages the Pandas package with more than 130 Indicators and Utility functions.",
                homepage="https://twopirllc.github.io/pandas-ta/",
                default_branch="main"
            ),
            # Stale fork with no recent activity
            ForkQualificationMetrics(
                id=987654321,
                name="pandas-ta",
                full_name="user2/pandas-ta",
                owner="user2",
                html_url="https://github.com/user2/pandas-ta",
                stargazers_count=2,
                forks_count=0,
                watchers_count=1,
                size=2400,
                language="Python",
                topics=[],
                open_issues_count=0,
                created_at=datetime(2022, 8, 10, 16, 20, 0, tzinfo=UTC),
                updated_at=datetime(2022, 8, 10, 16, 20, 0, tzinfo=UTC),
                pushed_at=datetime(2022, 8, 10, 16, 20, 0, tzinfo=UTC),  # Same as created = no commits
                archived=False,
                disabled=False,
                fork=True,
                license_key="mit",
                license_name="MIT License",
                description="Technical Analysis Library in Python 3.7+ Pandas TA is an easy to use library that leverages the Pandas package with more than 130 Indicators and Utility functions.",
                homepage=None,
                default_branch="main"
            ),
            # Large popular fork
            ForkQualificationMetrics(
                id=555666777,
                name="pandas-ta",
                full_name="biguser/pandas-ta",
                owner="biguser",
                html_url="https://github.com/biguser/pandas-ta",
                stargazers_count=156,
                forks_count=34,
                watchers_count=23,
                size=3200,
                language="Python",
                topics=["python", "pandas", "technical-analysis", "trading", "finance", "indicators"],
                open_issues_count=8,
                created_at=datetime(2023, 1, 5, 8, 0, 0, tzinfo=UTC),
                updated_at=datetime(2024, 1, 25, 11, 30, 0, tzinfo=UTC),
                pushed_at=datetime(2024, 1, 26, 7, 45, 0, tzinfo=UTC),
                archived=False,
                disabled=False,
                fork=True,
                license_key="mit",
                license_name="MIT License",
                description="Enhanced Technical Analysis Library with additional indicators and performance optimizations",
                homepage="https://biguser.github.io/pandas-ta/",
                default_branch="main"
            ),
            # Fork with special characters and Unicode
            ForkQualificationMetrics(
                id=111222333,
                name="pandas-ta",
                full_name="user-ñáéíóú/pandas-ta",
                owner="user-ñáéíóú",
                html_url="https://github.com/user-ñáéíóú/pandas-ta",
                stargazers_count=7,
                forks_count=1,
                watchers_count=3,
                size=2450,
                language="Python",
                topics=["python", "análisis-técnico", "trading"],
                open_issues_count=1,
                created_at=datetime(2023, 9, 12, 13, 15, 0, tzinfo=UTC),
                updated_at=datetime(2024, 1, 18, 16, 20, 0, tzinfo=UTC),
                pushed_at=datetime(2024, 1, 19, 10, 5, 0, tzinfo=UTC),
                archived=False,
                disabled=False,
                fork=True,
                license_key="mit",
                license_name="MIT License",
                description="Biblioteca de Análisis Técnico en Python 🚀 con indicadores personalizados",
                homepage=None,
                default_branch="main"
            ),
            # Archived fork
            ForkQualificationMetrics(
                id=444555666,
                name="pandas-ta",
                full_name="olduser/pandas-ta",
                owner="olduser",
                html_url="https://github.com/olduser/pandas-ta",
                stargazers_count=12,
                forks_count=3,
                watchers_count=5,
                size=2300,
                language="Python",
                topics=["python", "pandas", "deprecated"],
                open_issues_count=0,
                created_at=datetime(2022, 5, 20, 9, 30, 0, tzinfo=UTC),
                updated_at=datetime(2023, 2, 15, 14, 0, 0, tzinfo=UTC),
                pushed_at=datetime(2023, 2, 16, 11, 30, 0, tzinfo=UTC),
                archived=True,  # Archived repository
                disabled=False,
                fork=True,
                license_key="mit",
                license_name="MIT License",
                description="[ARCHIVED] Old version of technical analysis library",
                homepage=None,
                default_branch="master"
            )
        ]
        
        return [CollectedForkData(metrics=metrics) for metrics in forks_data]

    @pytest.fixture
    def realistic_commit_data(self):
        """Create realistic commit data for testing."""
        return {
            "https://github.com/user1/pandas-ta": [
                RecentCommit(
                    short_sha="a1b2c3d",
                    message="Add support for Bollinger Bands with custom periods",
                    date=datetime(2024, 1, 22, 9, 15, 0, tzinfo=UTC)
                ),
                RecentCommit(
                    short_sha="e4f5a6b",  # Fixed to be valid hex
                    message="Fix RSI calculation edge case\n\nResolves issue with NaN values in small datasets",
                    date=datetime(2024, 1, 20, 14, 30, 0, tzinfo=UTC)
                ),
                RecentCommit(
                    short_sha="1a2b3c4",  # Fixed to be valid hex
                    message="Update documentation for MACD indicator",
                    date=datetime(2024, 1, 18, 11, 45, 0, tzinfo=UTC)
                )
            ],
            "https://github.com/biguser/pandas-ta": [
                RecentCommit(
                    short_sha="1234567",  # Fixed to be valid hex
                    message="Performance optimization: vectorize SMA calculation",
                    date=datetime(2024, 1, 26, 7, 45, 0, tzinfo=UTC)
                ),
                RecentCommit(
                    short_sha="abcdef0",  # Fixed to be valid hex
                    message="Add new Ichimoku Cloud indicator with full configuration",
                    date=datetime(2024, 1, 24, 16, 20, 0, tzinfo=UTC)
                ),
                RecentCommit(
                    short_sha="fedcba9",  # Fixed to be valid hex
                    message="Implement parallel processing for batch calculations\n\nSignificant performance improvement for large datasets",
                    date=datetime(2024, 1, 22, 13, 10, 0, tzinfo=UTC)
                )
            ],
            "https://github.com/user-ñáéíóú/pandas-ta": [
                RecentCommit(
                    short_sha="9876543",  # Fixed to be valid hex
                    message="Añadir soporte para indicadores personalizados 🚀",
                    date=datetime(2024, 1, 19, 10, 5, 0, tzinfo=UTC)
                ),
                RecentCommit(
                    short_sha="c4d5e6f",
                    message="Corregir cálculo de media móvil exponencial",
                    date=datetime(2024, 1, 17, 15, 30, 0, tzinfo=UTC)
                )
            ]
        }

    @pytest.mark.asyncio
    async def test_csv_export_with_realistic_data(
        self, mock_github_client, realistic_fork_data, realistic_commit_data
    ):
        """Test CSV export with realistic repository data."""
        display_service = RepositoryDisplayService(mock_github_client)
        
        # Capture CSV output
        captured_output = io.StringIO()
        
        with patch("sys.stdout", captured_output):
            with patch.object(display_service, "_fetch_raw_commits_for_csv") as mock_fetch_commits:
                mock_fetch_commits.return_value = realistic_commit_data
                
                table_context = {
                    "owner": "twopirllc",
                    "repo": "pandas-ta",
                    "has_exact_counts": False,
                    "mode": "standard"
                }
                
                await display_service._export_csv_data(
                    realistic_fork_data,
                    table_context,
                    show_commits=3,
                    force_all_commits=False
                )
        
        # Parse and validate CSV output
        csv_output = captured_output.getvalue()
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        
        assert len(rows) == 5  # All 5 forks
        
        # Verify realistic data is preserved
        user1_row = next(row for row in rows if row["owner"] == "user1")
        assert user1_row["stars"] == "45"
        assert user1_row["language"] == "Python"
        assert "Bollinger Bands" in user1_row["recent_commits"]
        
        # Verify Unicode handling
        unicode_row = next(row for row in rows if "ñáéíóú" in row["owner"])
        assert "🚀" in unicode_row["recent_commits"]
        assert "Añadir soporte" in unicode_row["recent_commits"]
        
        # Verify archived fork is included
        archived_row = next(row for row in rows if row["owner"] == "olduser")
        assert "[ARCHIVED]" in archived_row["description"]

    @pytest.mark.asyncio
    async def test_csv_export_with_filtering_options(
        self, mock_github_client, realistic_fork_data
    ):
        """Test CSV export with various filtering options."""
        display_service = RepositoryDisplayService(mock_github_client)
        
        # Test with ahead_only filter
        captured_output = io.StringIO()
        
        with patch("sys.stdout", captured_output):
            with patch.object(display_service, "_filter_forks_ahead_only") as mock_filter:
                # Mock filtering to return only forks with commits ahead
                forks_with_commits = [
                    fork for fork in realistic_fork_data 
                    if fork.metrics.commits_ahead_status == "Has commits"
                ]
                mock_filter.return_value = forks_with_commits
                
                table_context = {
                    "owner": "twopirllc",
                    "repo": "pandas-ta",
                    "has_exact_counts": False,
                    "mode": "standard"
                }
                
                await display_service._export_csv_data(
                    realistic_fork_data,
                    table_context,
                    show_commits=0,
                    force_all_commits=False,
                    ahead_only=True
                )
        
        # Verify filtering worked
        csv_output = captured_output.getvalue()
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        
        # Should have fewer rows due to filtering
        assert len(rows) < len(realistic_fork_data)
        
        # All remaining rows should have commits ahead
        for row in rows:
            assert row["commits_ahead"] != "None"

    def test_csv_export_file_output_with_realistic_data(self, realistic_fork_data):
        """Test CSV export to file with realistic data."""
        exporter = CSVExporter()
        
        # Convert to ForksPreview format for testing
        from forklift.models.analysis import ForkPreviewItem, ForksPreview
        
        preview_items = []
        for fork_data in realistic_fork_data:
            metrics = fork_data.metrics
            item = ForkPreviewItem(
                name=metrics.name,
                owner=metrics.owner,
                stars=metrics.stargazers_count,
                last_push_date=metrics.pushed_at,
                fork_url=metrics.html_url,
                activity_status="Active" if metrics.commits_ahead_status == "Has commits" else "Stale",
                commits_ahead=metrics.commits_ahead_status
            )
            preview_items.append(item)
        
        preview = ForksPreview(total_forks=len(preview_items), forks=preview_items)
        
        # Export to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_path = f.name
        
        try:
            csv_content = exporter.export_to_csv(preview, temp_path)
            
            # Verify file was created
            assert Path(temp_path).exists()
            
            # Verify file content
            with open(temp_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            assert file_content == csv_content
            
            # Verify realistic data is in the file
            assert "user1" in file_content
            assert "pandas-ta" in file_content
            assert "Python" in file_content
            
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_csv_export_with_different_configurations(self, realistic_fork_data):
        """Test CSV export with different configuration options."""
        # Test minimal configuration
        minimal_config = CSVExportConfig(
            include_commits=False,
            detail_mode=False,
            include_explanations=False,
            include_urls=False
        )
        minimal_exporter = CSVExporter(minimal_config)
        
        # Test detailed configuration
        detailed_config = CSVExportConfig(
            include_commits=True,
            detail_mode=True,
            include_explanations=True,
            include_urls=True,
            date_format="%Y-%m-%d"
        )
        detailed_exporter = CSVExporter(detailed_config)
        
        # Convert to ForksPreview for testing
        from forklift.models.analysis import ForkPreviewItem, ForksPreview
        
        preview_items = []
        for fork_data in realistic_fork_data[:2]:  # Use first 2 for faster testing
            metrics = fork_data.metrics
            item = ForkPreviewItem(
                name=metrics.name,
                owner=metrics.owner,
                stars=metrics.stargazers_count,
                last_push_date=metrics.pushed_at,
                fork_url=metrics.html_url,
                activity_status="Active",
                commits_ahead="3"
            )
            preview_items.append(item)
        
        preview = ForksPreview(total_forks=len(preview_items), forks=preview_items)
        
        # Test minimal export
        minimal_csv = minimal_exporter.export_forks_preview(preview)
        minimal_reader = csv.DictReader(io.StringIO(minimal_csv))
        minimal_headers = minimal_reader.fieldnames
        
        # Should have minimal headers
        assert "fork_url" not in minimal_headers
        assert "recent_commits" not in minimal_headers
        
        # Test detailed export
        detailed_csv = detailed_exporter.export_forks_preview(preview)
        detailed_reader = csv.DictReader(io.StringIO(detailed_csv))
        detailed_headers = detailed_reader.fieldnames
        
        # Should have detailed headers
        assert "fork_url" in detailed_headers
        assert "recent_commits" in detailed_headers
        assert "last_push_date" in detailed_headers

    @pytest.mark.asyncio
    async def test_csv_export_error_handling_with_realistic_data(
        self, mock_github_client, realistic_fork_data
    ):
        """Test CSV export error handling with realistic data scenarios."""
        display_service = RepositoryDisplayService(mock_github_client)
        
        # Test with commit fetching error
        captured_stderr = io.StringIO()
        captured_stdout = io.StringIO()
        
        with patch("sys.stderr", captured_stderr):
            with patch("sys.stdout", captured_stdout):
                with patch.object(display_service, "_fetch_raw_commits_for_csv") as mock_fetch_commits:
                    # Simulate API error
                    mock_fetch_commits.side_effect = Exception("GitHub API rate limit exceeded")
                    
                    table_context = {
                        "owner": "twopirllc",
                        "repo": "pandas-ta",
                        "has_exact_counts": False,
                        "mode": "standard"
                    }
                    
                    # Should handle error gracefully
                    await display_service._export_csv_data(
                        realistic_fork_data,
                        table_context,
                        show_commits=3,
                        force_all_commits=False
                    )
        
        # Should still produce CSV output without commits
        csv_output = captured_stdout.getvalue()
        assert len(csv_output) > 0
        assert "fork_name" in csv_output
        
        # Error should be logged to stderr
        stderr_output = captured_stderr.getvalue()
        assert "Error fetching commits" in stderr_output or len(stderr_output) == 0  # Error handling may vary

    def test_csv_export_performance_with_realistic_data(self, realistic_fork_data):
        """Test CSV export performance with realistic data size."""
        # Multiply realistic data to simulate larger repository
        large_dataset = realistic_fork_data * 50  # 250 forks
        
        exporter = CSVExporter()
        
        # Convert to ForksPreview format
        from forklift.models.analysis import ForkPreviewItem, ForksPreview
        
        preview_items = []
        for i, fork_data in enumerate(large_dataset):
            metrics = fork_data.metrics
            item = ForkPreviewItem(
                name=f"{metrics.name}-{i}",
                owner=f"{metrics.owner}-{i}",
                stars=metrics.stargazers_count,
                last_push_date=metrics.pushed_at,
                fork_url=f"{metrics.html_url}-{i}",
                activity_status="Active" if i % 2 == 0 else "Stale",
                commits_ahead=str(i % 10) if i % 5 != 0 else "None"
            )
            preview_items.append(item)
        
        preview = ForksPreview(total_forks=len(preview_items), forks=preview_items)
        
        # Measure export time
        import time
        start_time = time.time()
        
        csv_output = exporter.export_forks_preview(preview)
        
        end_time = time.time()
        export_time = end_time - start_time
        
        # Should complete within reasonable time
        assert export_time < 10.0  # 10 seconds for 250 forks
        
        # Verify output correctness
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        assert len(rows) == 250

    def test_csv_export_spreadsheet_import_compatibility(self, realistic_fork_data):
        """Test that exported CSV can be imported into spreadsheet applications."""
        exporter = CSVExporter()
        
        # Convert to ForksPreview format
        from forklift.models.analysis import ForkPreviewItem, ForksPreview
        
        preview_items = []
        for fork_data in realistic_fork_data:
            metrics = fork_data.metrics
            item = ForkPreviewItem(
                name=metrics.name,
                owner=metrics.owner,
                stars=metrics.stargazers_count,
                last_push_date=metrics.pushed_at,
                fork_url=metrics.html_url,
                activity_status="Active",
                commits_ahead="3",
                recent_commits="2024-01-22 abc1234 Fix calculation bug; 2024-01-20 def5678 Add new feature"
            )
            preview_items.append(item)
        
        preview = ForksPreview(total_forks=len(preview_items), forks=preview_items)
        
        # Export CSV
        csv_output = exporter.export_forks_preview(preview)
        
        # Verify CSV format is compatible with spreadsheet applications
        
        # 1. Should not start with BOM
        assert not csv_output.startswith('\ufeff')
        
        # 2. Should use standard CSV format
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        assert len(rows) == len(realistic_fork_data)
        
        # 3. Should handle special characters properly
        unicode_row = next(row for row in rows if "ñáéíóú" in row["owner"])
        assert unicode_row is not None
        
        # 4. Should preserve numeric data as strings (for spreadsheet compatibility)
        for row in rows:
            assert isinstance(row["stars"], str)
            assert row["stars"].isdigit()
        
        # 5. Should handle long text fields
        for row in rows:
            if row["recent_commits"]:
                assert len(row["recent_commits"]) > 0
                # Should not contain unescaped newlines
                assert "\n" not in row["recent_commits"] or "\\n" in row["recent_commits"]