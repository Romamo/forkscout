"""Validation and edge case tests for CSV export commit enhancement.

This module tests the validation requirements and edge cases for the multi-row
CSV export format, ensuring data integrity, consistency, and proper handling
of various edge cases.

Requirements tested:
- 2.4: Repository information consistency across commit rows
- 2.5: Chronological ordering of commits  
- 3.2: Proper handling of varying numbers of commits
- 3.3: Edge cases like empty repositories and no commits
- 6.6: Data integrity and consistency in new format
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
import logging

from forklift.models.analysis import Feature, FeatureCategory, ForkAnalysis, ForkMetrics
from forklift.models.github import Commit, Fork, Repository, User
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
        description="A test repository for validation testing",
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


class TestCSVValidationAndEdgeCases:
    """Test cases for CSV validation and edge cases in multi-row format."""

    def test_repository_data_consistency_across_commit_rows(self, sample_fork, sample_commit_author):
        """Test that repository information is identical across commit rows for same fork.
        
        Requirement 2.4: Repository information consistency across commit rows.
        """
        config = CSVExportConfig(include_urls=True, detail_mode=True)
        exporter = CSVExporter(config)
        
        # Create multiple commits with different data
        commits = []
        for i in range(5):
            commit = Commit(
                sha=f"{str(i)*40}",
                message=f"Commit {i} with different content",
                author=sample_commit_author,
                date=datetime(2023, 11, 15 - i, 10, i, 0),
                files_changed=[f"file{i}.py", f"other{i}.js"],
                additions=10 + i * 5,
                deletions=5 + i * 2,
                total_changes=15 + i * 7,
                parents=[f"{str(i-1)*40}"] if i > 0 else []
            )
            commits.append(commit)
        
        feature = Feature(
            id="feat_consistency",
            title="Consistency Test Feature",
            description="Feature to test data consistency",
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
        
        # Should have 5 rows (one per commit)
        assert len(rows) == 5
        
        # Define repository fields that should be identical across all rows
        repository_fields = [
            "fork_name", "owner", "stars", "forks_count", "commits_ahead",
            "commits_behind", "is_active", "features_count", "fork_url",
            "owner_url", "language", "description", "last_activity",
            "created_date", "updated_date", "pushed_date", "size_kb",
            "open_issues", "is_archived", "is_private"
        ]
        
        # Extract repository data from first row as reference
        reference_repo_data = {field: rows[0][field] for field in repository_fields}
        
        # Verify all rows have identical repository data
        for i, row in enumerate(rows):
            for field in repository_fields:
                assert row[field] == reference_repo_data[field], (
                    f"Row {i} field '{field}' differs: {row[field]} != {reference_repo_data[field]}"
                )
        
        # Verify commit data is different across rows
        commit_fields = ["commit_sha", "commit_description", "commit_date"]
        for i in range(1, len(rows)):
            for field in commit_fields:
                # At least one commit field should be different between rows
                if rows[i][field] != rows[0][field]:
                    break
            else:
                pytest.fail(f"Row {i} has identical commit data to row 0")

    def test_chronological_ordering_of_commits(self, sample_fork, sample_commit_author):
        """Test chronological ordering of commits in multi-row format.
        
        Requirement 2.5: Chronological ordering of commits (newest first).
        """
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        # Create commits with specific dates in non-chronological order
        commit_dates = [
            datetime(2023, 11, 10, 8, 0, 0),   # Oldest
            datetime(2023, 11, 15, 14, 30, 0), # Newest
            datetime(2023, 11, 12, 10, 15, 0), # Middle
            datetime(2023, 11, 14, 16, 45, 0), # Second newest
            datetime(2023, 11, 11, 12, 30, 0), # Second oldest
        ]
        
        commits = []
        for i, date in enumerate(commit_dates):
            # Create valid 40-character hex SHA (only hex characters)
            sha = f"{i:02d}" + "0" * 38  # 2-digit number + 38 zeros = 40 chars
            commit = Commit(
                sha=sha,
                message=f"Commit {i} at {date.strftime('%Y-%m-%d %H:%M')}",
                author=sample_commit_author,
                date=date,
                files_changed=[f"file{i}.py"],
                additions=10,
                deletions=5,
                total_changes=15,
                parents=[]
            )
            commits.append(commit)
        
        feature = Feature(
            id="feat_chronological",
            title="Chronological Test Feature",
            description="Feature to test chronological ordering",
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
        
        # Should have 5 rows
        assert len(rows) == 5
        
        # Extract commit dates and verify chronological order (newest first)
        row_dates = []
        for row in rows:
            date_str = row["commit_date"]
            # Parse the date string back to datetime for comparison
            row_date = datetime.strptime(date_str, "%Y-%m-%d")
            row_dates.append(row_date.date())
        
        # Verify dates are in descending order (newest first)
        for i in range(1, len(row_dates)):
            assert row_dates[i-1] >= row_dates[i], (
                f"Commits not in chronological order: {row_dates[i-1]} should be >= {row_dates[i]}"
            )
        
        # Verify specific expected order based on our test data
        expected_order = [
            datetime(2023, 11, 15, 14, 30, 0).date(),  # Newest
            datetime(2023, 11, 14, 16, 45, 0).date(),  # Second newest
            datetime(2023, 11, 12, 10, 15, 0).date(),  # Middle
            datetime(2023, 11, 11, 12, 30, 0).date(),  # Second oldest
            datetime(2023, 11, 10, 8, 0, 0).date(),    # Oldest
        ]
        
        assert row_dates == expected_order
        
        # Verify the SHA values are correct (first 7 chars of our generated SHAs)
        expected_shas = ["0100000", "0300000", "0200000", "0400000", "0000000"]  # Based on chronological order
        actual_shas = [row["commit_sha"] for row in rows]
        assert actual_shas == expected_shas

    def test_varying_numbers_of_commits_per_fork(self, sample_user, sample_commit_author):
        """Test proper handling of forks with varying numbers of commits.
        
        Requirement 3.2: Proper handling of varying numbers of commits.
        """
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        # Create multiple forks with different numbers of commits
        fork_commit_counts = [0, 1, 3, 5, 10]  # Different commit counts
        analyses = []
        
        for fork_idx, commit_count in enumerate(fork_commit_counts):
            # Create repository for this fork
            repository = Repository(
                id=1000 + fork_idx,
                owner="test_owner",
                name=f"repo_{fork_idx}",
                full_name=f"test_owner/repo_{fork_idx}",
                url=f"https://api.github.com/repos/test_owner/repo_{fork_idx}",
                html_url=f"https://github.com/test_owner/repo_{fork_idx}",
                clone_url=f"https://github.com/test_owner/repo_{fork_idx}.git",
                default_branch="main",
                stars=100 + fork_idx * 10,
                forks_count=20 + fork_idx * 5,
                watchers_count=100 + fork_idx * 10,
                open_issues_count=fork_idx,
                size=1024,
                language="Python",
                description=f"Repository {fork_idx} with {commit_count} commits",
                topics=["python"],
                license_name="MIT",
                is_private=False,
                is_fork=True,
                is_archived=False,
                is_disabled=False,
                created_at=datetime(2023, 1, 1, 12, 0, 0),
                updated_at=datetime(2023, 12, 1, 12, 0, 0),
                pushed_at=datetime(2023, 11, 15, 10, 30, 0)
            )
            
            # Create parent repository
            parent_repository = Repository(
                id=2000 + fork_idx,
                owner="original_owner",
                name=f"original_repo_{fork_idx}",
                full_name=f"original_owner/original_repo_{fork_idx}",
                url=f"https://api.github.com/repos/original_owner/original_repo_{fork_idx}",
                html_url=f"https://github.com/original_owner/original_repo_{fork_idx}",
                clone_url=f"https://github.com/original_owner/original_repo_{fork_idx}.git",
                default_branch="main",
                stars=1000,
                forks_count=200,
                watchers_count=1000,
                open_issues_count=10,
                size=2048,
                language="Python",
                description="Original repository",
                topics=["python"],
                license_name="MIT",
                is_private=False,
                is_fork=False,
                is_archived=False,
                is_disabled=False,
                created_at=datetime(2022, 1, 1, 12, 0, 0),
                updated_at=datetime(2023, 12, 1, 12, 0, 0),
                pushed_at=datetime(2023, 12, 1, 10, 30, 0)
            )
            
            # Create fork
            fork = Fork(
                repository=repository,
                parent=parent_repository,
                owner=sample_user,
                last_activity=datetime(2023, 11, 15, 10, 30, 0),
                commits_ahead=commit_count,
                commits_behind=2,
                is_active=commit_count > 0,
                divergence_score=0.1 * commit_count
            )
            
            # Create commits for this fork
            commits = []
            for commit_idx in range(commit_count):
                # Create valid 40-character hex SHA (only hex characters)
                sha = f"{fork_idx:02d}{commit_idx:02d}" + "0" * 36  # 4 digits + 36 zeros = 40 chars
                commit = Commit(
                    sha=sha,
                    message=f"Fork {fork_idx} commit {commit_idx}",
                    author=sample_commit_author,
                    date=datetime(2023, 11, 15 - commit_idx, 10, 0, 0),
                    files_changed=[f"file{commit_idx}.py"],
                    additions=10,
                    deletions=5,
                    total_changes=15,
                    parents=[]
                )
                commits.append(commit)
            
            # Create feature (empty if no commits)
            features = []
            if commits:
                feature = Feature(
                    id=f"feat_{fork_idx}",
                    title=f"Feature {fork_idx}",
                    description=f"Feature for fork {fork_idx}",
                    category=FeatureCategory.NEW_FEATURE,
                    commits=commits,
                    files_affected=[f"file{i}.py" for i in range(commit_count)],
                    source_fork=fork
                )
                features.append(feature)
            
            # Create analysis
            analysis = ForkAnalysis(
                fork=fork,
                features=features,
                metrics=ForkMetrics(
                    stars=100 + fork_idx * 10,
                    forks=20 + fork_idx * 5,
                    contributors=max(1, commit_count),
                    last_activity=datetime(2023, 11, 15, 10, 30, 0),
                    commit_frequency=float(commit_count)
                ),
                analysis_date=datetime(2023, 12, 1, 15, 0, 0)
            )
            analyses.append(analysis)
        
        # Test each fork analysis
        for fork_idx, (analysis, expected_commit_count) in enumerate(zip(analyses, fork_commit_counts)):
            rows = exporter._generate_fork_commit_rows(analysis)
            
            if expected_commit_count == 0:
                # Fork with no commits should have exactly 1 row with empty commit data
                assert len(rows) == 1, f"Fork {fork_idx} with 0 commits should have 1 row"
                row = rows[0]
                assert row["commit_sha"] == "", f"Fork {fork_idx} should have empty commit_sha"
                assert row["commit_description"] == "", f"Fork {fork_idx} should have empty commit_description"
                assert row["commit_date"] == "", f"Fork {fork_idx} should have empty commit_date"
                assert row["fork_name"] == f"repo_{fork_idx}"
                assert row["features_count"] == 0
            else:
                # Fork with commits should have exactly commit_count rows
                assert len(rows) == expected_commit_count, (
                    f"Fork {fork_idx} with {expected_commit_count} commits should have {expected_commit_count} rows"
                )
                
                # All rows should have the same fork data but different commit data
                for row_idx, row in enumerate(rows):
                    assert row["fork_name"] == f"repo_{fork_idx}"
                    assert row["features_count"] == 1
                    assert row["commit_sha"] != "", f"Fork {fork_idx} row {row_idx} should have commit_sha"
                    assert row["commit_description"] != "", f"Fork {fork_idx} row {row_idx} should have commit_description"
                    assert row["commit_date"] != "", f"Fork {fork_idx} row {row_idx} should have commit_date"
                
                # Verify all rows have the same repository data
                repo_fields = ["fork_name", "owner", "stars", "forks_count", "features_count"]
                reference_data = {field: rows[0][field] for field in repo_fields}
                for row in rows[1:]:
                    for field in repo_fields:
                        assert row[field] == reference_data[field]

    def test_empty_repositories_and_no_commits_edge_cases(self, sample_fork):
        """Test edge cases like empty repositories and forks with no commits.
        
        Requirement 3.3: Edge cases like empty repositories and forks with no commits.
        """
        config = CSVExportConfig(include_urls=True, detail_mode=True)
        exporter = CSVExporter(config)
        
        # Test Case 1: Fork with completely empty features list
        empty_analysis = ForkAnalysis(
            fork=sample_fork,
            features=[],  # No features at all
            metrics=ForkMetrics(
                stars=0,
                forks=0,
                contributors=0,
                last_activity=None,
                commit_frequency=0.0
            ),
            analysis_date=datetime(2023, 12, 1, 15, 0, 0)
        )
        
        rows = exporter._generate_fork_commit_rows(empty_analysis)
        
        # Should generate exactly one row with empty commit data
        assert len(rows) == 1
        row = rows[0]
        
        # Repository data should be present
        assert row["fork_name"] == "test_repo"
        assert row["owner"] == "test_owner"
        assert row["stars"] == 150
        assert row["features_count"] == 0
        
        # Commit data should be empty
        assert row["commit_sha"] == ""
        assert row["commit_description"] == ""
        assert row["commit_date"] == ""
        
        # URL fields should be present but commit URL should be empty
        assert row["fork_url"] == "https://github.com/test_owner/test_repo"
        assert row["owner_url"] == "https://github.com/test_owner"
        assert row["commit_url"] == ""
        
        # Detail mode fields should be present
        assert row["language"] == "Python"
        assert row["description"] == "A test repository for validation testing"
        assert row["size_kb"] == 1024
        
        # Test Case 2: Fork with features but no commits in features
        feature_no_commits = Feature(
            id="empty_feat",
            title="Empty Feature",
            description="Feature with no commits",
            category=FeatureCategory.NEW_FEATURE,
            commits=[],  # Empty commits list
            files_affected=[],
            source_fork=sample_fork
        )
        
        no_commits_analysis = ForkAnalysis(
            fork=sample_fork,
            features=[feature_no_commits],
            metrics=ForkMetrics(
                stars=150,
                forks=25,
                contributors=1,
                last_activity=datetime(2023, 11, 15, 10, 30, 0),
                commit_frequency=0.0
            ),
            analysis_date=datetime(2023, 12, 1, 15, 0, 0)
        )
        
        rows = exporter._generate_fork_commit_rows(no_commits_analysis)
        
        # Should generate exactly one row with empty commit data
        assert len(rows) == 1
        row = rows[0]
        
        # Repository data should be present
        assert row["fork_name"] == "test_repo"
        assert row["features_count"] == 1  # One feature, but no commits
        
        # Commit data should be empty
        assert row["commit_sha"] == ""
        assert row["commit_description"] == ""
        assert row["commit_date"] == ""

    def test_data_integrity_and_consistency_comprehensive(self, sample_fork, sample_commit_author):
        """Test data integrity and consistency in new format comprehensively.
        
        Requirement 6.6: Data integrity and consistency in new format.
        """
        config = CSVExportConfig(include_urls=True, detail_mode=True)
        exporter = CSVExporter(config)
        
        # Create commits with various edge case data
        commits = [
            # Normal commit
            Commit(
                sha="1234567890abcdef1234567890abcdef12345678",
                message="Normal commit message",
                author=sample_commit_author,
                date=datetime(2023, 11, 15, 10, 0, 0),
                files_changed=["normal.py"],
                additions=10,
                deletions=5,
                total_changes=15,
                parents=[]
            ),
            # Commit with very long message
            Commit(
                sha="abcdef1234567890abcdef1234567890abcdef12",
                message="Very long commit message " * 100 + "that exceeds normal length limits and contains various special characters like @#$%^&*()[]{}|\\:;\"'<>,.?/~`",
                author=sample_commit_author,
                date=datetime(2023, 11, 14, 15, 30, 0),
                files_changed=["long.py"],
                additions=50,
                deletions=25,
                total_changes=75,
                parents=[]
            ),
            # Commit with special characters and newlines
            Commit(
                sha="fedcba0987654321fedcba0987654321fedcba09",
                message='Commit with "quotes", commas, and\nnewlines\r\nand tabs\tand other\x01control\x02chars',
                author=sample_commit_author,
                date=datetime(2023, 11, 13, 9, 15, 0),
                files_changed=["special.py"],
                additions=15,
                deletions=8,
                total_changes=23,
                parents=[]
            ),
            # Commit with minimal data
            Commit(
                sha="1111111111111111111111111111111111111111",
                message=".",
                author=sample_commit_author,
                date=datetime(2023, 11, 12, 12, 0, 0),
                files_changed=["minimal.py"],
                additions=1,
                deletions=0,
                total_changes=1,
                parents=[]
            )
        ]
        
        feature = Feature(
            id="integrity_test",
            title="Data Integrity Test",
            description="Feature to test data integrity and consistency",
            category=FeatureCategory.NEW_FEATURE,
            commits=commits,
            files_affected=["normal.py", "long.py", "special.py", "minimal.py"],
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
        
        # Test data integrity for each row
        for i, row in enumerate(rows):
            # All rows should have complete data structure
            required_fields = [
                "fork_name", "owner", "stars", "forks_count", "commits_ahead",
                "commits_behind", "is_active", "features_count", "fork_url",
                "owner_url", "language", "description", "last_activity",
                "created_date", "updated_date", "pushed_date", "size_kb",
                "open_issues", "is_archived", "is_private", "commit_date",
                "commit_sha", "commit_description", "commit_url"
            ]
            
            for field in required_fields:
                assert field in row, f"Row {i} missing required field: {field}"
                # Field should not be None (empty string is OK for commit fields)
                assert row[field] is not None, f"Row {i} field {field} is None"
            
            # Repository data should be consistent
            assert row["fork_name"] == "test_repo"
            assert row["owner"] == "test_owner"
            assert row["stars"] == 150
            assert row["forks_count"] == 25
            assert row["features_count"] == 1
            
            # Commit data should be present and valid
            assert len(row["commit_sha"]) == 7, f"Row {i} commit_sha should be 7 characters"
            assert row["commit_description"] != "", f"Row {i} should have commit_description"
            assert row["commit_date"] != "", f"Row {i} should have commit_date"
            
            # Date format should be consistent
            try:
                datetime.strptime(row["commit_date"], "%Y-%m-%d")
            except ValueError:
                pytest.fail(f"Row {i} commit_date format is invalid: {row['commit_date']}")
            
            # URL format should be valid
            assert row["commit_url"].startswith("https://github.com/"), f"Row {i} commit_url format invalid"
            assert row["commit_sha"] in row["commit_url"], f"Row {i} commit_url should contain commit_sha"
        
        # Test specific data handling
        # Find the row with very long message
        long_message_row = None
        for row in rows:
            if "Very long commit message" in row["commit_description"]:
                long_message_row = row
                break
        
        assert long_message_row is not None, "Long message commit not found"
        # Long message should be preserved without truncation
        assert len(long_message_row["commit_description"]) > 1000, "Long message was truncated"
        
        # Find the row with special characters
        special_char_row = None
        for row in rows:
            if "quotes" in row["commit_description"]:
                special_char_row = row
                break
        
        assert special_char_row is not None, "Special character commit not found"
        # Special characters should be handled properly (newlines converted to spaces)
        assert '"quotes"' in special_char_row["commit_description"], "Quotes should be preserved"
        assert "\n" not in special_char_row["commit_description"], "Newlines should be converted to spaces"
        assert "\r" not in special_char_row["commit_description"], "Carriage returns should be converted"

    def test_error_handling_during_validation(self, sample_fork, sample_commit_author):
        """Test error handling during validation and edge case processing."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        # Test with malformed commit data
        malformed_commit = Mock(spec=Commit)
        malformed_commit.sha = None  # Invalid SHA
        malformed_commit.message = None  # Invalid message
        malformed_commit.date = "not a date"  # Invalid date
        malformed_commit.author = sample_commit_author
        malformed_commit.files_changed = []
        malformed_commit.additions = 0
        malformed_commit.deletions = 0
        malformed_commit.total_changes = 0
        malformed_commit.parents = []
        
        feature = Feature(
            id="error_test",
            title="Error Handling Test",
            description="Feature to test error handling",
            category=FeatureCategory.NEW_FEATURE,
            commits=[malformed_commit],
            files_affected=[],
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
        
        # Should handle errors gracefully and still produce a row
        with patch('forklift.reporting.csv_exporter.logger') as mock_logger:
            rows = exporter._generate_fork_commit_rows(analysis)
            
            # Should still produce a row (with empty commit data due to errors)
            assert len(rows) >= 1
            
            # Should have logged warnings about the errors
            assert mock_logger.warning.called
        
        # Row should have repository data but empty/safe commit data
        row = rows[0]
        assert row["fork_name"] == "test_repo"
        assert row["owner"] == "test_owner"
        # Commit fields should be empty or safe values due to error handling
        assert isinstance(row["commit_sha"], str)
        assert isinstance(row["commit_description"], str)
        assert isinstance(row["commit_date"], str)

    def test_csv_export_full_integration_validation(self, sample_fork, sample_commit_author):
        """Test full CSV export integration with validation."""
        config = CSVExportConfig(include_urls=True, detail_mode=True)
        exporter = CSVExporter(config)
        
        # Create a comprehensive test scenario
        commits = []
        for i in range(3):
            # Create valid 40-character hex SHA (only hex characters)
            sha = f"{i:02d}" + "0" * 38  # 2-digit number + 38 zeros = 40 chars
            commit = Commit(
                sha=sha,
                message=f"Integration test commit {i}",
                author=sample_commit_author,
                date=datetime(2023, 11, 15 - i, 10, 0, 0),
                files_changed=[f"integration{i}.py"],
                additions=10 + i,
                deletions=5 + i,
                total_changes=15 + (2 * i),
                parents=[]
            )
            commits.append(commit)
        
        feature = Feature(
            id="integration_feat",
            title="Integration Test Feature",
            description="Feature for full integration testing",
            category=FeatureCategory.NEW_FEATURE,
            commits=commits,
            files_affected=[f"integration{i}.py" for i in range(3)],
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
        
        # Export to full CSV
        csv_content = exporter.export_fork_analyses([analysis])
        
        # Validate CSV structure
        lines = csv_content.strip().split('\n')
        assert len(lines) == 4  # Header + 3 data rows
        
        # Validate header
        header = lines[0]
        expected_fields = [
            "fork_name", "owner", "stars", "forks_count", "commits_ahead",
            "commits_behind", "is_active", "features_count", "fork_url",
            "owner_url", "language", "description", "last_activity",
            "created_date", "updated_date", "pushed_date", "size_kb",
            "open_issues", "is_archived", "is_private", "commit_date",
            "commit_sha", "commit_description", "commit_url"
        ]
        
        for field in expected_fields:
            assert field in header, f"Header missing field: {field}"
        
        # Validate CSV compatibility
        validation_result = exporter.validate_csv_compatibility(csv_content)
        assert validation_result["is_valid"], f"CSV validation failed: {validation_result['issues']}"
        
        # Check statistics
        stats = validation_result["statistics"]
        assert stats["total_rows"] == 4  # Header + 3 data rows
        assert stats["total_columns"] == len(expected_fields)
        assert stats["max_field_length"] > 0