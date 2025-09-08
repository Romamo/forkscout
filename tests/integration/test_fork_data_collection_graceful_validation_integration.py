"""Integration tests for fork data collection with graceful validation."""

import pytest
import logging
from unittest.mock import patch

from forklift.analysis.fork_data_collection_engine import ForkDataCollectionEngine
from forklift.models.github import Repository
from forklift.models.validation_handler import ValidationSummary


class TestForkDataCollectionGracefulValidationIntegration:
    """Integration tests for fork data collection with graceful validation."""

    @pytest.fixture
    def engine(self):
        """Create fork data collection engine."""
        return ForkDataCollectionEngine()

    @pytest.fixture
    def real_fork_data(self):
        """Create realistic fork data based on actual GitHub API responses."""
        return [
            {
                "id": 12345,
                "name": "test-repo",
                "full_name": "testuser/test-repo",
                "owner": {"login": "testuser"},
                "html_url": "https://github.com/testuser/test-repo",
                "clone_url": "https://github.com/testuser/test-repo.git",
                "url": "https://api.github.com/repos/testuser/test-repo",
                "stargazers_count": 10,
                "forks_count": 5,
                "watchers_count": 8,
                "size": 1024,
                "language": "Python",
                "topics": ["python", "testing"],
                "open_issues_count": 3,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-12-01T00:00:00Z",
                "pushed_at": "2023-11-01T00:00:00Z",
                "archived": False,
                "disabled": False,
                "fork": True,
                "license": {"key": "mit", "name": "MIT License"},
                "description": "A test repository",
                "homepage": "https://example.com",
                "default_branch": "main",
            },
            {
                "id": 67890,
                "name": "another-repo",
                "full_name": "anotheruser/another-repo",
                "owner": {"login": "anotheruser"},
                "html_url": "https://github.com/anotheruser/another-repo",
                "clone_url": "https://github.com/anotheruser/another-repo.git",
                "url": "https://api.github.com/repos/anotheruser/another-repo",
                "stargazers_count": 25,
                "forks_count": 12,
                "watchers_count": 20,
                "size": 2048,
                "language": "JavaScript",
                "topics": ["javascript", "web"],
                "open_issues_count": 7,
                "created_at": "2022-06-15T00:00:00Z",
                "updated_at": "2023-11-15T00:00:00Z",
                "pushed_at": "2023-10-20T00:00:00Z",
                "archived": False,
                "disabled": False,
                "fork": True,
                "license": {"key": "apache-2.0", "name": "Apache License 2.0"},
                "description": "Another test repository",
                "homepage": None,
                "default_branch": "main",
            },
        ]

    def test_collect_fork_data_integration_success(self, engine, real_fork_data):
        """Test fork data collection integration with realistic data."""
        repositories, validation_summary = engine.collect_fork_data(real_fork_data)

        # Verify successful processing
        assert len(repositories) == 2
        assert all(isinstance(repo, Repository) for repo in repositories)

        # Verify repository data
        repo1, repo2 = repositories
        assert repo1.name == "test-repo"
        assert repo1.owner == "testuser"
        assert repo1.language == "Python"
        assert repo1.stars == 10

        assert repo2.name == "another-repo"
        assert repo2.owner == "anotheruser"
        assert repo2.language == "JavaScript"
        assert repo2.stars == 25

        # Verify validation summary
        assert validation_summary.processed == 2
        assert validation_summary.skipped == 0
        assert not validation_summary.has_errors()

    def test_collect_fork_data_integration_with_problematic_names(self, engine):
        """Test fork data collection with repository names that might cause validation issues."""
        problematic_fork_data = [
            {
                "id": 11111,
                "name": "repo.with.dots",
                "full_name": "user/repo.with.dots",
                "owner": {"login": "user"},
                "html_url": "https://github.com/user/repo.with.dots",
                "clone_url": "https://github.com/user/repo.with.dots.git",
                "url": "https://api.github.com/repos/user/repo.with.dots",
                "stargazers_count": 1,
                "forks_count": 0,
                "watchers_count": 1,
                "size": 100,
                "language": "Python",
                "topics": [],
                "open_issues_count": 0,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-12-01T00:00:00Z",
                "pushed_at": "2023-11-01T00:00:00Z",
                "archived": False,
                "disabled": False,
                "fork": True,
                "license": None,
                "description": None,
                "homepage": None,
                "default_branch": "main",
            },
            {
                "id": 22222,
                "name": "repo-with-hyphens",
                "full_name": "user/repo-with-hyphens",
                "owner": {"login": "user"},
                "html_url": "https://github.com/user/repo-with-hyphens",
                "clone_url": "https://github.com/user/repo-with-hyphens.git",
                "url": "https://api.github.com/repos/user/repo-with-hyphens",
                "stargazers_count": 5,
                "forks_count": 2,
                "watchers_count": 3,
                "size": 500,
                "language": "Go",
                "topics": ["go", "cli"],
                "open_issues_count": 1,
                "created_at": "2023-03-01T00:00:00Z",
                "updated_at": "2023-11-01T00:00:00Z",
                "pushed_at": "2023-10-15T00:00:00Z",
                "archived": False,
                "disabled": False,
                "fork": True,
                "license": {"key": "bsd-3-clause", "name": "BSD 3-Clause License"},
                "description": "A repository with hyphens",
                "homepage": "https://example.org",
                "default_branch": "master",
            },
        ]

        repositories, validation_summary = engine.collect_fork_data(
            problematic_fork_data
        )

        # Should handle these names gracefully
        assert len(repositories) == 2
        assert repositories[0].name == "repo.with.dots"
        assert repositories[1].name == "repo-with-hyphens"
        assert validation_summary.processed == 2
        assert validation_summary.skipped == 0

    def test_collect_fork_data_integration_with_missing_fields(self, engine):
        """Test fork data collection with missing optional fields."""
        minimal_fork_data = [
            {
                "id": 33333,
                "name": "minimal-repo",
                "full_name": "user/minimal-repo",
                "owner": {"login": "user"},
                "html_url": "https://github.com/user/minimal-repo",
                "clone_url": "https://github.com/user/minimal-repo.git",
                "url": "https://api.github.com/repos/user/minimal-repo",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-12-01T00:00:00Z",
                "pushed_at": "2023-11-01T00:00:00Z",
                "fork": True,
                # Missing many optional fields
            }
        ]

        repositories, validation_summary = engine.collect_fork_data(minimal_fork_data)

        # Should handle missing optional fields gracefully
        assert len(repositories) == 1
        assert repositories[0].name == "minimal-repo"
        assert validation_summary.processed == 1
        assert validation_summary.skipped == 0

    def test_collect_fork_data_integration_logging(
        self, engine, real_fork_data, caplog
    ):
        """Test that integration logging works correctly."""
        with caplog.at_level(logging.INFO):
            repositories, validation_summary = engine.collect_fork_data(real_fork_data)

        # Verify logging messages
        assert (
            "Collecting fork data from 2 forks with graceful validation" in caplog.text
        )
        assert "Fork data collection completed" in caplog.text
        assert "2 successful, 0 skipped" in caplog.text

    def test_collect_fork_data_integration_performance(self, engine):
        """Test fork data collection performance with larger dataset."""
        # Create a larger dataset
        large_fork_data = []
        for i in range(50):
            fork_data = {
                "id": 10000 + i,
                "name": f"repo-{i}",
                "full_name": f"user{i}/repo-{i}",
                "owner": {"login": f"user{i}"},
                "html_url": f"https://github.com/user{i}/repo-{i}",
                "clone_url": f"https://github.com/user{i}/repo-{i}.git",
                "url": f"https://api.github.com/repos/user{i}/repo-{i}",
                "stargazers_count": i,
                "forks_count": i // 2,
                "watchers_count": i,
                "size": i * 100,
                "language": "Python" if i % 2 == 0 else "JavaScript",
                "topics": [f"topic-{i}"],
                "open_issues_count": i % 5,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-12-01T00:00:00Z",
                "pushed_at": "2023-11-01T00:00:00Z",
                "archived": False,
                "disabled": False,
                "fork": True,
                "license": {"key": "mit", "name": "MIT License"},
                "description": f"Repository {i}",
                "homepage": None,
                "default_branch": "main",
            }
            large_fork_data.append(fork_data)

        repositories, validation_summary = engine.collect_fork_data(large_fork_data)

        # Verify all repositories processed
        assert len(repositories) == 50
        assert validation_summary.processed == 50
        assert validation_summary.skipped == 0
        assert not validation_summary.has_errors()

    def test_collect_fork_data_integration_error_recovery(self, engine, real_fork_data):
        """Test that the system recovers gracefully from individual repository errors."""
        # Add some invalid data that will cause Repository.from_github_api to fail
        mixed_data = real_fork_data + [
            {
                "id": "invalid_id",  # Invalid ID type
                "name": "invalid-repo",
                "full_name": "user/invalid-repo",
                # Missing required fields
            }
        ]

        repositories, validation_summary = engine.collect_fork_data(mixed_data)

        # Should process valid repositories and skip invalid ones
        assert len(repositories) == 2  # Only the valid ones
        assert validation_summary.processed == 2
        assert validation_summary.skipped == 1
        assert validation_summary.has_errors()

    def test_collect_fork_data_integration_return_types(self, engine, real_fork_data):
        """Test that the method returns correct types."""
        repositories, validation_summary = engine.collect_fork_data(real_fork_data)

        # Verify return types
        assert isinstance(repositories, list)
        assert isinstance(validation_summary, ValidationSummary)
        assert all(isinstance(repo, Repository) for repo in repositories)

        # Verify ValidationSummary methods work
        assert isinstance(validation_summary.has_errors(), bool)
        assert isinstance(validation_summary.get_error_summary(), str)
        assert isinstance(validation_summary.processed, int)
        assert isinstance(validation_summary.skipped, int)
        assert isinstance(validation_summary.errors, list)
