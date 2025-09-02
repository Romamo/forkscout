"""Tests for CSV commit row generation functionality."""

import pytest
from datetime import datetime
from unittest.mock import Mock

from forklift.models.analysis import ForkAnalysis, Feature, FeatureCategory, ForkMetrics
from forklift.models.github import Fork, Repository, User, Commit
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
def sample_commit_author():
    """Create a sample commit author."""
    return User(
        id=54321,
        login="commit_author",
        name="Commit Author",
        email="author@example.com",
        html_url="https://github.com/commit_author",
        avatar_url="https://avatars.githubusercontent.com/u/54321",
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
def sample_commits(sample_commit_author):
    """Create sample commits for testing."""
    return [
        Commit(
            sha="1234567890abcdef1234567890abcdef12345678",
            message="Fix critical bug in authentication system",
            author=sample_commit_author,
            date=datetime(2023, 11, 15, 10, 0, 0),
            files_changed=["src/auth.py", "tests/test_auth.py"],
            additions=25,
            deletions=10,
            total_changes=35,
            parents=["abcdef1234567890abcdef1234567890abcdef12"]
        ),
        Commit(
            sha="abcdef1234567890abcdef1234567890abcdef12",
            message="Add new feature for user management",
            author=sample_commit_author,
            date=datetime(2023, 11, 14, 15, 30, 0),
            files_changed=["src/users.py", "src/models.py", "tests/test_users.py"],
            additions=150,
            deletions=5,
            total_changes=155,
            parents=["fedcba0987654321fedcba0987654321fedcba09"]
        ),
        Commit(
            sha="fedcba0987654321fedcba0987654321fedcba09",
            message="Update documentation for API endpoints",
            author=sample_commit_author,
            date=datetime(2023, 11, 13, 9, 15, 0),
            files_changed=["docs/api.md", "README.md"],
            additions=75,
            deletions=20,
            total_changes=95,
            parents=["1111111111111111111111111111111111111111"]
        )
    ]


@pytest.fixture
def sample_features_with_commits(sample_fork, sample_commits):
    """Create sample features with commits for testing."""
    return [
        Feature(
            id="feature_1",
            title="Bug Fix Feature",
            description="Fixes a critical bug",
            category=FeatureCategory.BUG_FIX,
            commits=[sample_commits[0]],  # First commit
            files_affected=["src/auth.py"],
            source_fork=sample_fork
        ),
        Feature(
            id="feature_2", 
            title="New Feature",
            description="Adds new functionality",
            category=FeatureCategory.NEW_FEATURE,
            commits=[sample_commits[1], sample_commits[2]],  # Second and third commits
            files_affected=["src/users.py", "src/models.py"],
            source_fork=sample_fork
        )
    ]


@pytest.fixture
def sample_fork_analysis_with_commits(sample_fork, sample_features_with_commits):
    """Create a sample fork analysis with commits."""
    metrics = ForkMetrics(
        stars=150,
        forks=25,
        contributors=3,
        last_activity=datetime(2023, 11, 15, 10, 30, 0),
        commit_frequency=2.5
    )
    
    return ForkAnalysis(
        fork=sample_fork,
        features=sample_features_with_commits,
        metrics=metrics,
        analysis_date=datetime(2023, 12, 1, 15, 0, 0)
    )


@pytest.fixture
def sample_fork_analysis_no_commits(sample_fork):
    """Create a sample fork analysis with no commits."""
    metrics = ForkMetrics(
        stars=150,
        forks=25,
        contributors=3,
        last_activity=datetime(2023, 11, 15, 10, 30, 0),
        commit_frequency=2.5
    )
    
    return ForkAnalysis(
        fork=sample_fork,
        features=[],  # No features, hence no commits
        metrics=metrics,
        analysis_date=datetime(2023, 12, 1, 15, 0, 0)
    )


class TestCSVCommitRowGeneration:
    """Test cases for CSV commit row generation."""

    def test_generate_fork_commit_rows_with_commits(self, sample_fork_analysis_with_commits):
        """Test generating multiple commit rows for a fork with commits."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        rows = exporter._generate_fork_commit_rows(sample_fork_analysis_with_commits)
        
        # Should have 3 rows (one for each commit)
        assert len(rows) == 3
        
        # Each row should have the same base fork data
        for row in rows:
            assert row["fork_name"] == "test_repo"
            assert row["owner"] == "test_owner"
            assert row["stars"] == 150
            assert row["forks_count"] == 25
            assert row["commits_ahead"] == 5
            assert row["commits_behind"] == 2
            assert row["is_active"] is True
            assert row["features_count"] == 2

        # Each row should have different commit data
        assert rows[0]["commit_sha"] == "1234567"  # Short SHA
        assert rows[0]["commit_description"] == "Fix critical bug in authentication system"
        assert rows[0]["commit_date"] == "2023-11-15"
        
        assert rows[1]["commit_sha"] == "abcdef1"  # Short SHA
        assert rows[1]["commit_description"] == "Add new feature for user management"
        assert rows[1]["commit_date"] == "2023-11-14"
        
        assert rows[2]["commit_sha"] == "fedcba0"  # Short SHA
        assert rows[2]["commit_description"] == "Update documentation for API endpoints"
        assert rows[2]["commit_date"] == "2023-11-13"

    def test_generate_fork_commit_rows_no_commits(self, sample_fork_analysis_no_commits):
        """Test generating rows for a fork with no commits."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        rows = exporter._generate_fork_commit_rows(sample_fork_analysis_no_commits)
        
        # Should have 1 row with empty commit data
        assert len(rows) == 1
        
        row = rows[0]
        # Should have fork data
        assert row["fork_name"] == "test_repo"
        assert row["owner"] == "test_owner"
        assert row["features_count"] == 0
        
        # Should have empty commit data
        assert row["commit_sha"] == ""
        assert row["commit_description"] == ""
        assert row["commit_date"] == ""

    def test_create_commit_row_combines_data(self, sample_fork_analysis_with_commits, sample_commits):
        """Test that _create_commit_row properly combines base and commit data."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        base_data = exporter._extract_base_fork_data(sample_fork_analysis_with_commits)
        commit = sample_commits[0]
        
        row = exporter._create_commit_row(base_data, commit, sample_fork_analysis_with_commits)
        
        # Should have all base data
        assert row["fork_name"] == "test_repo"
        assert row["owner"] == "test_owner"
        assert row["stars"] == 150
        
        # Should have commit data
        assert row["commit_sha"] == "1234567"
        assert row["commit_description"] == "Fix critical bug in authentication system"
        assert row["commit_date"] == "2023-11-15"

    def test_create_empty_commit_row(self, sample_fork_analysis_no_commits):
        """Test creating a row with empty commit data."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        base_data = exporter._extract_base_fork_data(sample_fork_analysis_no_commits)
        
        row = exporter._create_empty_commit_row(base_data)
        
        # Should have all base data
        assert row["fork_name"] == "test_repo"
        assert row["owner"] == "test_owner"
        assert row["stars"] == 150
        
        # Should have empty commit data
        assert row["commit_sha"] == ""
        assert row["commit_description"] == ""
        assert row["commit_date"] == ""

    def test_repository_data_consistency_across_rows(self, sample_fork_analysis_with_commits):
        """Test that repository data is identical across all commit rows for the same fork."""
        config = CSVExportConfig(include_urls=True, detail_mode=True)
        exporter = CSVExporter(config)
        
        rows = exporter._generate_fork_commit_rows(sample_fork_analysis_with_commits)
        
        # Extract repository fields (non-commit fields)
        repo_fields = [
            "fork_name", "owner", "stars", "forks_count", "commits_ahead", 
            "commits_behind", "is_active", "features_count", "fork_url", 
            "owner_url", "language", "description", "last_activity",
            "created_date", "updated_date", "pushed_date", "size_kb",
            "open_issues", "is_archived", "is_private"
        ]
        
        # Get repository data from first row
        first_row_repo_data = {field: rows[0][field] for field in repo_fields}
        
        # Check that all other rows have identical repository data
        for i, row in enumerate(rows[1:], 1):
            row_repo_data = {field: row[field] for field in repo_fields}
            assert row_repo_data == first_row_repo_data, f"Row {i} has different repository data"

    def test_commit_ordering_chronological(self, sample_fork_analysis_with_commits):
        """Test that commits are ordered chronologically (newest first)."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        rows = exporter._generate_fork_commit_rows(sample_fork_analysis_with_commits)
        
        # Extract commit dates
        commit_dates = [row["commit_date"] for row in rows]
        
        # Should be in descending order (newest first)
        assert commit_dates == ["2023-11-15", "2023-11-14", "2023-11-13"]

    def test_commit_deduplication(self, sample_fork_analysis_with_commits, sample_commits):
        """Test that duplicate commits are handled properly."""
        # Add the same commit to multiple features to test deduplication
        duplicate_feature = Feature(
            id="feature_3",
            title="Duplicate Feature",
            description="Has duplicate commit",
            category=FeatureCategory.OTHER,
            commits=[sample_commits[0]],  # Same as first feature
            files_affected=["src/duplicate.py"],
            source_fork=sample_fork_analysis_with_commits.fork
        )
        
        sample_fork_analysis_with_commits.features.append(duplicate_feature)
        
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        rows = exporter._generate_fork_commit_rows(sample_fork_analysis_with_commits)
        
        # Should still have 3 rows (duplicates removed)
        assert len(rows) == 3
        
        # Check that commit SHAs are unique
        commit_shas = [row["commit_sha"] for row in rows]
        assert len(set(commit_shas)) == len(commit_shas), "Duplicate commits found"

    def test_max_commits_per_fork_limit(self, sample_fork_analysis_with_commits, sample_commits, sample_commit_author):
        """Test that max_commits_per_fork limit is respected."""
        # Add more commits to exceed the limit
        extra_commits = [
            Commit(
                sha=f"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"[:-1] + str(i),
                message=f"Extra commit {i}",
                author=sample_commit_author,
                date=datetime(2023, 11, 10 + i, 12, 0, 0),
                files_changed=[f"src/extra{i}.py"],
                additions=10,
                deletions=5,
                total_changes=15,
                parents=["0000000000000000000000000000000000000000"]
            )
            for i in range(5)
        ]
        
        # Add extra commits to features
        sample_fork_analysis_with_commits.features[0].commits.extend(extra_commits)
        
        config = CSVExportConfig(max_commits_per_fork=3)
        exporter = CSVExporter(config)
        
        rows = exporter._generate_fork_commit_rows(sample_fork_analysis_with_commits)
        
        # Should be limited to 3 rows
        assert len(rows) <= 3

    def test_commit_row_generation_with_urls(self, sample_fork_analysis_with_commits):
        """Test commit row generation includes URLs when configured."""
        config = CSVExportConfig(include_urls=True)
        exporter = CSVExporter(config)
        
        rows = exporter._generate_fork_commit_rows(sample_fork_analysis_with_commits)
        
        # Check that URL fields are included
        for row in rows:
            assert "fork_url" in row
            assert "owner_url" in row
            assert row["fork_url"] == "https://github.com/test_owner/test_repo"
            assert row["owner_url"] == "https://github.com/test_owner"

    def test_commit_row_generation_detail_mode(self, sample_fork_analysis_with_commits):
        """Test commit row generation includes detail fields when configured."""
        config = CSVExportConfig(detail_mode=True)
        exporter = CSVExporter(config)
        
        rows = exporter._generate_fork_commit_rows(sample_fork_analysis_with_commits)
        
        # Check that detail fields are included
        for row in rows:
            assert "language" in row
            assert "description" in row
            assert "last_activity" in row
            assert row["language"] == "Python"
            assert row["description"] == "A test repository for unit testing"

    def test_empty_commit_message_handling(self, sample_fork_analysis_with_commits, sample_commits):
        """Test handling of commits with empty or None messages."""
        # Modify a commit to have empty message
        sample_commits[0].message = ""
        
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        rows = exporter._generate_fork_commit_rows(sample_fork_analysis_with_commits)
        
        # Should handle empty message gracefully
        assert rows[0]["commit_description"] == ""

    def test_commit_row_data_types(self, sample_fork_analysis_with_commits):
        """Test that commit row data has correct types."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        rows = exporter._generate_fork_commit_rows(sample_fork_analysis_with_commits)
        
        for row in rows:
            # String fields
            assert isinstance(row["fork_name"], str)
            assert isinstance(row["owner"], str)
            assert isinstance(row["commit_sha"], str)
            assert isinstance(row["commit_description"], str)
            assert isinstance(row["commit_date"], str)
            
            # Integer fields
            assert isinstance(row["stars"], int)
            assert isinstance(row["forks_count"], int)
            assert isinstance(row["commits_ahead"], int)
            assert isinstance(row["commits_behind"], int)
            assert isinstance(row["features_count"], int)
            
            # Boolean fields
            assert isinstance(row["is_active"], bool)