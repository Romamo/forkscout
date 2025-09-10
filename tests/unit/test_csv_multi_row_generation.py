"""Unit tests for CSV multi-row generation with different commit scenarios."""

import pytest
from datetime import datetime
from unittest.mock import Mock

from forkscout.models.analysis import Feature, FeatureCategory, ForkAnalysis, ForkMetrics
from forkscout.models.github import Commit, Fork, Repository, User
from forkscout.reporting.csv_exporter import CSVExporter, CSVExportConfig


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


class TestCSVMultiRowGeneration:
    """Test cases for CSV multi-row generation with different commit scenarios."""

    def test_multi_row_generation_single_commit(self, sample_fork, sample_commit_author):
        """Test multi-row generation with a single commit."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        commit = Commit(
            sha="1234567890abcdef1234567890abcdef12345678",
            message="Fix authentication bug",
            author=sample_commit_author,
            date=datetime(2023, 11, 15, 10, 0, 0),
            files_changed=["src/auth.py"],
            additions=25,
            deletions=10,
            total_changes=35,
            parents=["abcdef1234567890abcdef1234567890abcdef12"]
        )
        
        feature = Feature(
            id="feat_1",
            title="Bug Fix",
            description="Authentication bug fix",
            category=FeatureCategory.BUG_FIX,
            commits=[commit],
            files_affected=["src/auth.py"],
            source_fork=sample_fork
        )
        
        analysis = ForkAnalysis(
            fork=sample_fork,
            features=[feature],
            metrics=ForkMetrics(
                stars=150,
                forks=25,
                contributors=3,
                last_activity=datetime(2023, 11, 15, 10, 30, 0),
                commit_frequency=2.5
            ),
            analysis_date=datetime(2023, 12, 1, 15, 0, 0)
        )
        
        rows = exporter._generate_fork_commit_rows(analysis)
        
        # Should generate exactly one row
        assert len(rows) == 1
        
        row = rows[0]
        assert row["fork_name"] == "test_repo"
        assert row["owner"] == "test_owner"
        assert row["commit_sha"] == "1234567"
        assert row["commit_description"] == "Fix authentication bug"
        assert row["commit_date"] == "2023-11-15"

    def test_multi_row_generation_multiple_commits(self, sample_fork, sample_commit_author):
        """Test multi-row generation with multiple commits."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        commits = [
            Commit(
                sha="1111111111111111111111111111111111111111",
                message="First commit",
                author=sample_commit_author,
                date=datetime(2023, 11, 15, 10, 0, 0),
                files_changed=["file1.py"],
                additions=10,
                deletions=5,
                total_changes=15,
                parents=[]
            ),
            Commit(
                sha="2222222222222222222222222222222222222222",
                message="Second commit",
                author=sample_commit_author,
                date=datetime(2023, 11, 14, 15, 30, 0),
                files_changed=["file2.py"],
                additions=20,
                deletions=3,
                total_changes=23,
                parents=["1111111111111111111111111111111111111111"]
            ),
            Commit(
                sha="3333333333333333333333333333333333333333",
                message="Third commit",
                author=sample_commit_author,
                date=datetime(2023, 11, 13, 9, 15, 0),
                files_changed=["file3.py"],
                additions=15,
                deletions=8,
                total_changes=23,
                parents=["2222222222222222222222222222222222222222"]
            )
        ]
        
        feature = Feature(
            id="feat_1",
            title="Multi-commit Feature",
            description="Feature with multiple commits",
            category=FeatureCategory.NEW_FEATURE,
            commits=commits,
            files_affected=["file1.py", "file2.py", "file3.py"],
            source_fork=sample_fork
        )
        
        analysis = ForkAnalysis(
            fork=sample_fork,
            features=[feature],
            metrics=ForkMetrics(
                stars=150,
                forks=25,
                contributors=3,
                last_activity=datetime(2023, 11, 15, 10, 30, 0),
                commit_frequency=2.5
            ),
            analysis_date=datetime(2023, 12, 1, 15, 0, 0)
        )
        
        rows = exporter._generate_fork_commit_rows(analysis)
        
        # Should generate three rows (one per commit)
        assert len(rows) == 3
        
        # Check that all rows have the same fork data
        for row in rows:
            assert row["fork_name"] == "test_repo"
            assert row["owner"] == "test_owner"
            assert row["stars"] == 150
            assert row["forks_count"] == 25
            assert row["features_count"] == 1
        
        # Check that commits are ordered chronologically (newest first)
        assert rows[0]["commit_sha"] == "1111111"  # 2023-11-15
        assert rows[0]["commit_description"] == "First commit"
        assert rows[1]["commit_sha"] == "2222222"  # 2023-11-14
        assert rows[1]["commit_description"] == "Second commit"
        assert rows[2]["commit_sha"] == "3333333"  # 2023-11-13
        assert rows[2]["commit_description"] == "Third commit"

    def test_multi_row_generation_no_commits(self, sample_fork):
        """Test multi-row generation with no commits."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        analysis = ForkAnalysis(
            fork=sample_fork,
            features=[],  # No features means no commits
            metrics=ForkMetrics(
                stars=150,
                forks=25,
                contributors=3,
                last_activity=datetime(2023, 11, 15, 10, 30, 0),
                commit_frequency=0.0
            ),
            analysis_date=datetime(2023, 12, 1, 15, 0, 0)
        )
        
        rows = exporter._generate_fork_commit_rows(analysis)
        
        # Should generate one row with empty commit data
        assert len(rows) == 1
        
        row = rows[0]
        assert row["fork_name"] == "test_repo"
        assert row["owner"] == "test_owner"
        assert row["features_count"] == 0
        assert row["commit_sha"] == ""
        assert row["commit_description"] == ""
        assert row["commit_date"] == ""

    def test_multi_row_generation_with_commit_limit(self, sample_fork, sample_commit_author):
        """Test multi-row generation respects max_commits_per_fork limit."""
        config = CSVExportConfig(max_commits_per_fork=2)
        exporter = CSVExporter(config)
        
        # Create 5 commits but limit should restrict to 2
        commits = []
        for i in range(5):
            commit = Commit(
                sha=f"{str(i)*40}",
                message=f"Commit {i}",
                author=sample_commit_author,
                date=datetime(2023, 11, 15 - i, 10, 0, 0),  # Different dates for ordering
                files_changed=[f"file{i}.py"],
                additions=10,
                deletions=5,
                total_changes=15,
                parents=[]
            )
            commits.append(commit)
        
        feature = Feature(
            id="feat_1",
            title="Limited Commits Feature",
            description="Feature with commit limit",
            category=FeatureCategory.NEW_FEATURE,
            commits=commits,
            files_affected=[f"file{i}.py" for i in range(5)],
            source_fork=sample_fork
        )
        
        analysis = ForkAnalysis(
            fork=sample_fork,
            features=[feature],
            metrics=ForkMetrics(
                stars=150,
                forks=25,
                contributors=3,
                last_activity=datetime(2023, 11, 15, 10, 30, 0),
                commit_frequency=2.5
            ),
            analysis_date=datetime(2023, 12, 1, 15, 0, 0)
        )
        
        rows = exporter._generate_fork_commit_rows(analysis)
        
        # Should be limited to 2 rows
        assert len(rows) == 2
        
        # Should be the 2 most recent commits
        assert rows[0]["commit_description"] == "Commit 0"  # Most recent
        assert rows[1]["commit_description"] == "Commit 1"  # Second most recent

    def test_multi_row_generation_with_duplicate_commits(self, sample_fork, sample_commit_author):
        """Test multi-row generation handles duplicate commits across features."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        shared_commit = Commit(
            sha="1234567890abcdef1234567890abcdef12345678",
            message="Shared commit",
            author=sample_commit_author,
            date=datetime(2023, 11, 15, 10, 0, 0),
            files_changed=["shared.py"],
            additions=25,
            deletions=10,
            total_changes=35,
            parents=[]
        )
        
        unique_commit = Commit(
            sha="abcdef1234567890abcdef1234567890abcdef12",
            message="Unique commit",
            author=sample_commit_author,
            date=datetime(2023, 11, 14, 15, 30, 0),
            files_changed=["unique.py"],
            additions=15,
            deletions=5,
            total_changes=20,
            parents=[]
        )
        
        # Create two features that share one commit
        feature1 = Feature(
            id="feat_1",
            title="Feature 1",
            description="First feature",
            category=FeatureCategory.NEW_FEATURE,
            commits=[shared_commit, unique_commit],
            files_affected=["shared.py", "unique.py"],
            source_fork=sample_fork
        )
        
        feature2 = Feature(
            id="feat_2",
            title="Feature 2",
            description="Second feature",
            category=FeatureCategory.BUG_FIX,
            commits=[shared_commit],  # Same commit as in feature1
            files_affected=["shared.py"],
            source_fork=sample_fork
        )
        
        analysis = ForkAnalysis(
            fork=sample_fork,
            features=[feature1, feature2],
            metrics=ForkMetrics(
                stars=150,
                forks=25,
                contributors=3,
                last_activity=datetime(2023, 11, 15, 10, 30, 0),
                commit_frequency=2.5
            ),
            analysis_date=datetime(2023, 12, 1, 15, 0, 0)
        )
        
        rows = exporter._generate_fork_commit_rows(analysis)
        
        # Should have 2 unique rows (duplicates removed)
        assert len(rows) == 2
        
        # Check that we have both commits but no duplicates
        commit_shas = [row["commit_sha"] for row in rows]
        assert "1234567" in commit_shas
        assert "abcdef1" in commit_shas
        assert len(set(commit_shas)) == 2  # All unique

    def test_multi_row_generation_chronological_ordering(self, sample_fork, sample_commit_author):
        """Test that multi-row generation orders commits chronologically (newest first)."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        # Create commits with specific dates (not in chronological order)
        commits = [
            Commit(
                sha="1111111111111111111111111111111111111111",
                message="Middle commit",
                author=sample_commit_author,
                date=datetime(2023, 11, 14, 12, 0, 0),  # Middle date
                files_changed=["middle.py"],
                additions=10,
                deletions=5,
                total_changes=15,
                parents=[]
            ),
            Commit(
                sha="2222222222222222222222222222222222222222",
                message="Newest commit",
                author=sample_commit_author,
                date=datetime(2023, 11, 16, 10, 0, 0),  # Newest date
                files_changed=["newest.py"],
                additions=20,
                deletions=3,
                total_changes=23,
                parents=[]
            ),
            Commit(
                sha="3333333333333333333333333333333333333333",
                message="Oldest commit",
                author=sample_commit_author,
                date=datetime(2023, 11, 12, 8, 0, 0),  # Oldest date
                files_changed=["oldest.py"],
                additions=15,
                deletions=8,
                total_changes=23,
                parents=[]
            )
        ]
        
        feature = Feature(
            id="feat_1",
            title="Chronological Test",
            description="Test chronological ordering",
            category=FeatureCategory.NEW_FEATURE,
            commits=commits,
            files_affected=["middle.py", "newest.py", "oldest.py"],
            source_fork=sample_fork
        )
        
        analysis = ForkAnalysis(
            fork=sample_fork,
            features=[feature],
            metrics=ForkMetrics(
                stars=150,
                forks=25,
                contributors=3,
                last_activity=datetime(2023, 11, 16, 10, 30, 0),
                commit_frequency=2.5
            ),
            analysis_date=datetime(2023, 12, 1, 15, 0, 0)
        )
        
        rows = exporter._generate_fork_commit_rows(analysis)
        
        # Should have 3 rows in chronological order (newest first)
        assert len(rows) == 3
        
        assert rows[0]["commit_sha"] == "2222222"  # 2023-11-16
        assert rows[0]["commit_description"] == "Newest commit"
        assert rows[1]["commit_sha"] == "1111111"  # 2023-11-14
        assert rows[1]["commit_description"] == "Middle commit"
        assert rows[2]["commit_sha"] == "3333333"  # 2023-11-12
        assert rows[2]["commit_description"] == "Oldest commit"

    def test_multi_row_generation_with_various_commit_scenarios(self, sample_fork, sample_commit_author):
        """Test multi-row generation with various commit message scenarios."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        # Create commits with different message characteristics
        commits = [
            Commit(
                sha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                message="Simple commit message",
                author=sample_commit_author,
                date=datetime(2023, 11, 15, 10, 0, 0),
                files_changed=["simple.py"],
                additions=10,
                deletions=5,
                total_changes=15,
                parents=[]
            ),
            Commit(
                sha="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                message="Multi-line commit\n\nThis commit has multiple lines\nwith detailed description",
                author=sample_commit_author,
                date=datetime(2023, 11, 14, 15, 30, 0),
                files_changed=["multiline.py"],
                additions=20,
                deletions=3,
                total_changes=23,
                parents=[]
            ),
            Commit(
                sha="cccccccccccccccccccccccccccccccccccccccc",
                message='Commit with "quotes", commas, and other special chars!',
                author=sample_commit_author,
                date=datetime(2023, 11, 13, 9, 15, 0),
                files_changed=["special.py"],
                additions=15,
                deletions=8,
                total_changes=23,
                parents=[]
            ),
            Commit(
                sha="dddddddddddddddddddddddddddddddddddddddd",
                message=".",  # Minimal message (empty will be tested via escaping)
                author=sample_commit_author,
                date=datetime(2023, 11, 12, 12, 0, 0),
                files_changed=["empty.py"],
                additions=5,
                deletions=2,
                total_changes=7,
                parents=[]
            )
        ]
        
        feature = Feature(
            id="feat_1",
            title="Various Scenarios",
            description="Test various commit scenarios",
            category=FeatureCategory.NEW_FEATURE,
            commits=commits,
            files_affected=["simple.py", "multiline.py", "special.py", "empty.py"],
            source_fork=sample_fork
        )
        
        analysis = ForkAnalysis(
            fork=sample_fork,
            features=[feature],
            metrics=ForkMetrics(
                stars=150,
                forks=25,
                contributors=3,
                last_activity=datetime(2023, 11, 15, 10, 30, 0),
                commit_frequency=2.5
            ),
            analysis_date=datetime(2023, 12, 1, 15, 0, 0)
        )
        
        rows = exporter._generate_fork_commit_rows(analysis)
        
        # Should have 4 rows
        assert len(rows) == 4
        
        # Check that all rows have consistent fork data
        for row in rows:
            assert row["fork_name"] == "test_repo"
            assert row["owner"] == "test_owner"
            assert row["features_count"] == 1
        
        # Check specific commit handling
        simple_row = next(row for row in rows if row["commit_sha"] == "aaaaaaa")
        assert simple_row["commit_description"] == "Simple commit message"
        
        multiline_row = next(row for row in rows if row["commit_sha"] == "bbbbbbb")
        # Multiline should be cleaned (newlines replaced with spaces)
        assert "Multi-line commit" in multiline_row["commit_description"]
        assert "This commit has multiple lines" in multiline_row["commit_description"]
        assert "\n" not in multiline_row["commit_description"]
        
        special_row = next(row for row in rows if row["commit_sha"] == "ccccccc")
        # Special characters should be preserved (CSV writer handles escaping)
        assert '"quotes"' in special_row["commit_description"]
        assert "commas" in special_row["commit_description"]
        
        empty_row = next(row for row in rows if row["commit_sha"] == "ddddddd")
        assert empty_row["commit_description"] == "."

    def test_multi_row_generation_with_url_configuration(self, sample_fork, sample_commit_author):
        """Test multi-row generation with URL configuration enabled."""
        config = CSVExportConfig(include_urls=True)
        exporter = CSVExporter(config)
        
        commit = Commit(
            sha="1234567890abcdef1234567890abcdef12345678",
            message="Commit with URL",
            author=sample_commit_author,
            date=datetime(2023, 11, 15, 10, 0, 0),
            files_changed=["url.py"],
            additions=10,
            deletions=5,
            total_changes=15,
            parents=[]
        )
        
        feature = Feature(
            id="feat_1",
            title="URL Test",
            description="Test URL generation",
            category=FeatureCategory.NEW_FEATURE,
            commits=[commit],
            files_affected=["url.py"],
            source_fork=sample_fork
        )
        
        analysis = ForkAnalysis(
            fork=sample_fork,
            features=[feature],
            metrics=ForkMetrics(
                stars=150,
                forks=25,
                contributors=3,
                last_activity=datetime(2023, 11, 15, 10, 30, 0),
                commit_frequency=2.5
            ),
            analysis_date=datetime(2023, 12, 1, 15, 0, 0)
        )
        
        rows = exporter._generate_fork_commit_rows(analysis)
        
        assert len(rows) == 1
        row = rows[0]
        
        # Should have URL fields
        assert "fork_url" in row
        assert "owner_url" in row
        assert "commit_url" in row
        
        assert row["fork_url"] == "https://github.com/test_owner/test_repo"
        assert row["owner_url"] == "https://github.com/test_owner"
        assert row["commit_url"] == "https://github.com/test_owner/test_repo/commit/1234567890abcdef1234567890abcdef12345678"

    def test_multi_row_generation_with_detail_mode(self, sample_fork, sample_commit_author):
        """Test multi-row generation with detail mode enabled."""
        config = CSVExportConfig(detail_mode=True)
        exporter = CSVExporter(config)
        
        commit = Commit(
            sha="abcdef1234567890abcdef1234567890abcdef12",
            message="Detail mode commit",
            author=sample_commit_author,
            date=datetime(2023, 11, 15, 10, 0, 0),
            files_changed=["detail.py"],
            additions=10,
            deletions=5,
            total_changes=15,
            parents=[]
        )
        
        feature = Feature(
            id="feat_1",
            title="Detail Test",
            description="Test detail mode",
            category=FeatureCategory.NEW_FEATURE,
            commits=[commit],
            files_affected=["detail.py"],
            source_fork=sample_fork
        )
        
        analysis = ForkAnalysis(
            fork=sample_fork,
            features=[feature],
            metrics=ForkMetrics(
                stars=150,
                forks=25,
                contributors=3,
                last_activity=datetime(2023, 11, 15, 10, 30, 0),
                commit_frequency=2.5
            ),
            analysis_date=datetime(2023, 12, 1, 15, 0, 0)
        )
        
        rows = exporter._generate_fork_commit_rows(analysis)
        
        assert len(rows) == 1
        row = rows[0]
        
        # Should have detail mode fields
        detail_fields = [
            "language", "description", "last_activity", "created_date",
            "updated_date", "pushed_date", "size_kb", "open_issues",
            "is_archived", "is_private"
        ]
        
        for field in detail_fields:
            assert field in row
        
        assert row["language"] == "Python"
        assert row["description"] == "A test repository for unit testing"
        assert row["size_kb"] == 1024
        assert row["open_issues"] == 5
        assert row["is_archived"] is False
        assert row["is_private"] is False

    def test_multi_row_generation_data_consistency_across_rows(self, sample_fork, sample_commit_author):
        """Test that repository data is identical across all commit rows."""
        config = CSVExportConfig(include_urls=True, detail_mode=True)
        exporter = CSVExporter(config)
        
        # Create multiple commits
        commits = []
        sha_bases = ["1111111111111111111111111111111111111111", 
                     "2222222222222222222222222222222222222222",
                     "3333333333333333333333333333333333333333"]
        for i in range(3):
            commit = Commit(
                sha=sha_bases[i],
                message=f"Consistency test commit {i}",
                author=sample_commit_author,
                date=datetime(2023, 11, 15 - i, 10, 0, 0),
                files_changed=[f"file{i}.py"],
                additions=10 + i,
                deletions=5 + i,
                total_changes=15 + (2 * i),
                parents=[]
            )
            commits.append(commit)
        
        feature = Feature(
            id="feat_1",
            title="Consistency Test",
            description="Test data consistency",
            category=FeatureCategory.NEW_FEATURE,
            commits=commits,
            files_affected=[f"file{i}.py" for i in range(3)],
            source_fork=sample_fork
        )
        
        analysis = ForkAnalysis(
            fork=sample_fork,
            features=[feature],
            metrics=ForkMetrics(
                stars=150,
                forks=25,
                contributors=3,
                last_activity=datetime(2023, 11, 15, 10, 30, 0),
                commit_frequency=2.5
            ),
            analysis_date=datetime(2023, 12, 1, 15, 0, 0)
        )
        
        rows = exporter._generate_fork_commit_rows(analysis)
        
        assert len(rows) == 3
        
        # Extract non-commit fields (repository data)
        repo_fields = [
            "fork_name", "owner", "stars", "forks_count", "commits_ahead",
            "commits_behind", "is_active", "features_count", "fork_url",
            "owner_url", "language", "description", "last_activity",
            "created_date", "updated_date", "pushed_date", "size_kb",
            "open_issues", "is_archived", "is_private"
        ]
        
        # Get repository data from first row
        first_row_repo_data = {field: rows[0][field] for field in repo_fields}
        
        # Verify all rows have identical repository data
        for i, row in enumerate(rows):
            row_repo_data = {field: row[field] for field in repo_fields}
            assert row_repo_data == first_row_repo_data, f"Row {i} has different repository data"
            
            # But commit data should be different
            if i > 0:
                assert row["commit_sha"] != rows[0]["commit_sha"]
                assert row["commit_description"] != rows[0]["commit_description"]