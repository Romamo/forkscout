"""Tests for CSV base fork data extraction functionality."""

import pytest
from datetime import datetime
from unittest.mock import Mock

from forklift.models.analysis import ForkAnalysis, Feature, FeatureCategory, ForkMetrics
from forklift.models.github import Fork, Repository, User
from forklift.reporting.csv_exporter import CSVExporter, CSVExportConfig


@pytest.fixture
def sample_user():
    """Create a sample GitHub user."""
    return User(
        id=12345,
        login="test_owner",
        name="Test Owner",
        email="test@example.com",
        html_url="https://github.com/test_owner",
        avatar_url="https://avatars.githubusercontent.com/u/12345",
        type="User",
        site_admin=False
    )


@pytest.fixture
def sample_repository():
    """Create a sample repository."""
    return Repository(
        id=67890,
        owner="test_owner",
        name="test_repo",
        full_name="test_owner/test_repo",
        url="https://api.github.com/repos/test_owner/test_repo",
        html_url="https://github.com/test_owner/test_repo",
        clone_url="https://github.com/test_owner/test_repo.git",
        default_branch="main",
        stars=150,
        forks_count=25,
        watchers_count=150,
        open_issues_count=5,
        size=1024,
        language="Python",
        description="A test repository for unit testing",
        topics=["python", "testing"],
        license_name="MIT",
        is_private=False,
        is_fork=True,
        is_archived=False,
        is_disabled=False,
        created_at=datetime(2023, 1, 1, 12, 0, 0),
        updated_at=datetime(2023, 12, 1, 12, 0, 0),
        pushed_at=datetime(2023, 11, 15, 10, 30, 0)
    )


@pytest.fixture
def sample_parent_repository():
    """Create a sample parent repository."""
    return Repository(
        id=11111,
        owner="original_owner",
        name="original_repo",
        full_name="original_owner/original_repo",
        url="https://api.github.com/repos/original_owner/original_repo",
        html_url="https://github.com/original_owner/original_repo",
        clone_url="https://github.com/original_owner/original_repo.git",
        default_branch="main",
        stars=1000,
        forks_count=200,
        watchers_count=1000,
        open_issues_count=10,
        size=2048,
        language="Python",
        description="The original repository",
        topics=["python", "original"],
        license_name="MIT",
        is_private=False,
        is_fork=False,
        is_archived=False,
        is_disabled=False,
        created_at=datetime(2022, 1, 1, 12, 0, 0),
        updated_at=datetime(2023, 12, 1, 12, 0, 0),
        pushed_at=datetime(2023, 12, 1, 10, 30, 0)
    )


@pytest.fixture
def sample_fork(sample_repository, sample_parent_repository, sample_user):
    """Create a sample fork."""
    return Fork(
        repository=sample_repository,
        parent=sample_parent_repository,
        owner=sample_user,
        last_activity=datetime(2023, 11, 15, 10, 30, 0),
        commits_ahead=5,
        commits_behind=2,
        is_active=True,
        divergence_score=0.3
    )


@pytest.fixture
def sample_features(sample_fork):
    """Create sample features for testing."""
    return [
        Feature(
            id="feature_1",
            title="Bug Fix Feature",
            description="Fixes a critical bug",
            category=FeatureCategory.BUG_FIX,
            commits=[],
            files_affected=["src/main.py"],
            source_fork=sample_fork
        ),
        Feature(
            id="feature_2", 
            title="New Feature",
            description="Adds new functionality",
            category=FeatureCategory.NEW_FEATURE,
            commits=[],
            files_affected=["src/feature.py", "tests/test_feature.py"],
            source_fork=sample_fork
        )
    ]


@pytest.fixture
def sample_fork_analysis(sample_fork, sample_features):
    """Create a sample fork analysis."""
    metrics = ForkMetrics(
        stars=150,
        forks=25,
        contributors=3,
        last_activity=datetime(2023, 11, 15, 10, 30, 0),
        commit_frequency=2.5
    )
    
    return ForkAnalysis(
        fork=sample_fork,
        features=sample_features,
        metrics=metrics,
        analysis_date=datetime(2023, 12, 1, 15, 0, 0)
    )


class TestCSVBaseDataExtraction:
    """Test cases for CSV base fork data extraction."""

    def test_extract_base_fork_data_basic_fields(self, sample_fork_analysis):
        """Test extraction of basic fork data fields."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        base_data = exporter._extract_base_fork_data(sample_fork_analysis)
        
        # Check essential fork metadata
        assert base_data["fork_name"] == "test_repo"
        assert base_data["owner"] == "test_owner"
        assert base_data["stars"] == 150
        assert base_data["forks_count"] == 25
        assert base_data["commits_ahead"] == 5
        assert base_data["commits_behind"] == 2
        assert base_data["is_active"] is True
        assert base_data["features_count"] == 2

    def test_extract_base_fork_data_with_urls(self, sample_fork_analysis):
        """Test extraction with URL fields included."""
        config = CSVExportConfig(include_urls=True)
        exporter = CSVExporter(config)
        
        base_data = exporter._extract_base_fork_data(sample_fork_analysis)
        
        # Check URL fields are included
        assert "fork_url" in base_data
        assert "owner_url" in base_data
        assert base_data["fork_url"] == "https://github.com/test_owner/test_repo"
        assert base_data["owner_url"] == "https://github.com/test_owner"

    def test_extract_base_fork_data_without_urls(self, sample_fork_analysis):
        """Test extraction without URL fields."""
        config = CSVExportConfig(include_urls=False)
        exporter = CSVExporter(config)
        
        base_data = exporter._extract_base_fork_data(sample_fork_analysis)
        
        # Check URL fields are not included
        assert "fork_url" not in base_data
        assert "owner_url" not in base_data

    def test_extract_base_fork_data_detail_mode(self, sample_fork_analysis):
        """Test extraction with detail mode enabled."""
        config = CSVExportConfig(detail_mode=True)
        exporter = CSVExporter(config)
        
        base_data = exporter._extract_base_fork_data(sample_fork_analysis)
        
        # Check detail mode fields are included
        assert "language" in base_data
        assert "description" in base_data
        assert "last_activity" in base_data
        assert "created_date" in base_data
        assert "updated_date" in base_data
        assert "pushed_date" in base_data
        assert "size_kb" in base_data
        assert "open_issues" in base_data
        assert "is_archived" in base_data
        assert "is_private" in base_data
        
        # Check values
        assert base_data["language"] == "Python"
        assert base_data["description"] == "A test repository for unit testing"
        assert base_data["size_kb"] == 1024
        assert base_data["open_issues"] == 5
        assert base_data["is_archived"] is False
        assert base_data["is_private"] is False

    def test_extract_base_fork_data_without_detail_mode(self, sample_fork_analysis):
        """Test extraction without detail mode."""
        config = CSVExportConfig(detail_mode=False)
        exporter = CSVExporter(config)
        
        base_data = exporter._extract_base_fork_data(sample_fork_analysis)
        
        # Check detail mode fields are not included
        detail_fields = [
            "language", "description", "last_activity", "created_date",
            "updated_date", "pushed_date", "size_kb", "open_issues",
            "is_archived", "is_private"
        ]
        for field in detail_fields:
            assert field not in base_data

    def test_extract_base_fork_data_with_both_urls_and_detail(self, sample_fork_analysis):
        """Test extraction with both URLs and detail mode enabled."""
        config = CSVExportConfig(include_urls=True, detail_mode=True)
        exporter = CSVExporter(config)
        
        base_data = exporter._extract_base_fork_data(sample_fork_analysis)
        
        # Check both URL and detail fields are included
        assert "fork_url" in base_data
        assert "owner_url" in base_data
        assert "language" in base_data
        assert "description" in base_data
        assert "last_activity" in base_data

    def test_extract_base_fork_data_handles_none_values(self, sample_fork_analysis):
        """Test extraction handles None values gracefully."""
        # Modify the repository to have None values
        sample_fork_analysis.fork.repository.language = None
        sample_fork_analysis.fork.repository.description = None
        sample_fork_analysis.fork.repository.created_at = None
        
        config = CSVExportConfig(detail_mode=True)
        exporter = CSVExporter(config)
        
        base_data = exporter._extract_base_fork_data(sample_fork_analysis)
        
        # Check None values are handled properly (converted to empty strings)
        assert base_data["language"] == ""
        assert base_data["description"] == ""
        assert base_data["created_date"] == ""

    def test_extract_base_fork_data_date_formatting(self, sample_fork_analysis):
        """Test that dates are formatted correctly."""
        config = CSVExportConfig(detail_mode=True, date_format="%Y-%m-%d %H:%M:%S")
        exporter = CSVExporter(config)
        
        base_data = exporter._extract_base_fork_data(sample_fork_analysis)
        
        # Check date formatting
        assert base_data["last_activity"] == "2023-11-15 10:30:00"
        assert base_data["created_date"] == "2023-01-01 12:00:00"
        assert base_data["updated_date"] == "2023-12-01 12:00:00"
        assert base_data["pushed_date"] == "2023-11-15 10:30:00"

    def test_extract_base_fork_data_empty_features(self, sample_fork_analysis):
        """Test extraction with no features."""
        sample_fork_analysis.features = []
        
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        base_data = exporter._extract_base_fork_data(sample_fork_analysis)
        
        assert base_data["features_count"] == 0

    def test_extract_base_fork_data_consistency(self, sample_fork_analysis):
        """Test that extracted data is consistent across multiple calls."""
        config = CSVExportConfig(include_urls=True, detail_mode=True)
        exporter = CSVExporter(config)
        
        base_data_1 = exporter._extract_base_fork_data(sample_fork_analysis)
        base_data_2 = exporter._extract_base_fork_data(sample_fork_analysis)
        
        # Data should be identical
        assert base_data_1 == base_data_2

    def test_extract_base_fork_data_all_required_fields_present(self, sample_fork_analysis):
        """Test that all required fields are present in extracted data."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        base_data = exporter._extract_base_fork_data(sample_fork_analysis)
        
        # Check all essential fields are present
        required_fields = [
            "fork_name", "owner", "stars", "forks_count", 
            "commits_ahead", "commits_behind", "is_active", "features_count"
        ]
        
        for field in required_fields:
            assert field in base_data, f"Required field '{field}' missing from base data"
            assert base_data[field] is not None, f"Required field '{field}' is None"