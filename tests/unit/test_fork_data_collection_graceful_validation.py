"""Tests for fork data collection with graceful validation."""

import logging
import pytest
from unittest.mock import patch, MagicMock

from forkscout.analysis.fork_data_collection_engine import (
    ForkDataCollectionEngine,
    ForkDataCollectionError,
)
from forkscout.models.github import Repository
from forkscout.models.validation_handler import ValidationSummary


class TestForkDataCollectionGracefulValidation:
    """Test fork data collection with graceful validation handling."""

    @pytest.fixture
    def engine(self):
        """Create fork data collection engine."""
        return ForkDataCollectionEngine()

    @pytest.fixture
    def valid_fork_data(self):
        """Create valid fork data for testing."""
        return {
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
        }

    @pytest.fixture
    def invalid_fork_data(self):
        """Create invalid fork data that will cause validation errors."""
        return {
            "id": 67890,
            "name": "maybe.._..maybe",  # Consecutive periods that might cause validation issues
            "full_name": "testuser/maybe.._..maybe",
            "owner": {"login": "testuser"},
            "html_url": "https://github.com/testuser/maybe.._..maybe",
            "clone_url": "https://github.com/testuser/maybe.._..maybe.git",
            "url": "https://api.github.com/repos/testuser/maybe.._..maybe",
            # Missing required fields to trigger validation error
            "stargazers_count": 0,
            "forks_count": 0,
            "watchers_count": 0,
            "size": 0,
            "language": None,
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
        }

    def test_collect_fork_data_success_all_valid(self, engine, valid_fork_data):
        """Test successful fork data collection with all valid repositories."""
        forks = [valid_fork_data]

        repositories, validation_summary = engine.collect_fork_data(forks)

        # Verify successful processing
        assert len(repositories) == 1
        assert isinstance(repositories[0], Repository)
        assert repositories[0].name == "test-repo"
        assert repositories[0].owner == "testuser"

        # Verify validation summary
        assert isinstance(validation_summary, ValidationSummary)
        assert validation_summary.processed == 1
        assert validation_summary.skipped == 0
        assert not validation_summary.has_errors()
        assert len(validation_summary.errors) == 0

    def test_collect_fork_data_mixed_valid_invalid(
        self, engine, valid_fork_data, invalid_fork_data
    ):
        """Test fork data collection with mixed valid and invalid repositories."""
        # Create a scenario where Repository.from_github_api fails for invalid data
        with patch(
            "forklift.models.github.Repository.from_github_api"
        ) as mock_from_api:

            def side_effect(data):
                if data.get("name") == "maybe.._..maybe":
                    raise ValueError("Repository validation failed")
                return Repository(
                    id=data["id"],
                    name=data["name"],
                    full_name=data["full_name"],
                    owner=data["owner"]["login"],
                    html_url=data["html_url"],
                    clone_url=data["clone_url"],
                    url=data["url"],
                )

            mock_from_api.side_effect = side_effect

            forks = [valid_fork_data, invalid_fork_data]
            repositories, validation_summary = engine.collect_fork_data(forks)

            # Verify partial success
            assert len(repositories) == 1
            assert repositories[0].name == "test-repo"

            # Verify validation summary shows errors
            assert validation_summary.processed == 1
            assert validation_summary.skipped == 1
            assert validation_summary.has_errors()
            assert len(validation_summary.errors) == 1
            assert "maybe.._..maybe" in validation_summary.errors[0]["repository"]

    def test_collect_fork_data_all_invalid(self, engine, invalid_fork_data):
        """Test fork data collection with all invalid repositories."""
        with patch(
            "forklift.models.github.Repository.from_github_api"
        ) as mock_from_api:
            # Use a simple ValueError that will be caught as unexpected error
            mock_from_api.side_effect = ValueError("Repository validation failed")

            forks = [invalid_fork_data]
            repositories, validation_summary = engine.collect_fork_data(forks)

            # Verify no repositories created
            assert len(repositories) == 0

            # Verify validation summary shows all errors
            assert validation_summary.processed == 0
            assert validation_summary.skipped == 1
            assert validation_summary.has_errors()
            assert len(validation_summary.errors) == 1

    def test_collect_fork_data_empty_list(self, engine):
        """Test fork data collection with empty list."""
        repositories, validation_summary = engine.collect_fork_data([])

        # Verify empty results
        assert len(repositories) == 0
        assert validation_summary.processed == 0
        assert validation_summary.skipped == 0
        assert not validation_summary.has_errors()

    def test_collect_fork_data_unexpected_error(self, engine, valid_fork_data):
        """Test fork data collection with unexpected errors."""
        with patch(
            "forklift.models.github.Repository.from_github_api"
        ) as mock_from_api:
            mock_from_api.side_effect = RuntimeError("Unexpected error")

            forks = [valid_fork_data]
            repositories, validation_summary = engine.collect_fork_data(forks)

            # Verify error handling
            assert len(repositories) == 0
            assert validation_summary.processed == 0
            assert validation_summary.skipped == 1
            assert validation_summary.has_errors()
            assert "Unexpected error" in validation_summary.errors[0]["error"]

    def test_collect_fork_data_logging(self, engine, valid_fork_data, caplog):
        """Test that appropriate logging occurs during fork data collection."""
        with caplog.at_level(logging.INFO):
            repositories, validation_summary = engine.collect_fork_data(
                [valid_fork_data]
            )

        # Verify logging messages
        assert (
            "Collecting fork data from 1 forks with graceful validation" in caplog.text
        )
        assert "Fork data collection completed" in caplog.text
        assert "1 successful, 0 skipped" in caplog.text

    def test_collect_fork_data_logging_with_errors(
        self, engine, valid_fork_data, invalid_fork_data, caplog
    ):
        """Test logging when validation errors occur."""
        with patch(
            "forklift.models.github.Repository.from_github_api"
        ) as mock_from_api:

            def side_effect(data):
                if data.get("name") == "maybe.._..maybe":
                    raise ValueError("Repository validation failed")
                return Repository(
                    id=data["id"],
                    name=data["name"],
                    full_name=data["full_name"],
                    owner=data["owner"]["login"],
                    html_url=data["html_url"],
                    clone_url=data["clone_url"],
                    url=data["url"],
                )

            mock_from_api.side_effect = side_effect

            with caplog.at_level(logging.ERROR):
                repositories, validation_summary = engine.collect_fork_data(
                    [valid_fork_data, invalid_fork_data]
                )

            # Verify error logging (ValueError will be caught as unexpected error)
            assert "Unexpected error creating repository" in caplog.text
            assert "maybe.._..maybe" in caplog.text

    def test_collect_fork_data_processing_time_logging(
        self, engine, valid_fork_data, caplog
    ):
        """Test that processing time is logged."""
        with caplog.at_level(logging.INFO):
            repositories, validation_summary = engine.collect_fork_data(
                [valid_fork_data]
            )

        # Verify processing time is logged
        assert "completed in" in caplog.text
        assert "s:" in caplog.text  # Should contain time in seconds

    def test_collect_fork_data_large_dataset(self, engine, valid_fork_data):
        """Test fork data collection with larger dataset."""
        # Create multiple valid fork data entries
        forks = []
        for i in range(10):
            fork_data = valid_fork_data.copy()
            fork_data["id"] = 12345 + i
            fork_data["name"] = f"test-repo-{i}"
            fork_data["full_name"] = f"testuser/test-repo-{i}"
            forks.append(fork_data)

        repositories, validation_summary = engine.collect_fork_data(forks)

        # Verify all repositories processed
        assert len(repositories) == 10
        assert validation_summary.processed == 10
        assert validation_summary.skipped == 0
        assert not validation_summary.has_errors()

    def test_collect_fork_data_exception_handling(self, engine, valid_fork_data):
        """Test that exceptions during processing are properly handled."""
        with patch(
            "forklift.models.validation_handler.ValidationHandler.safe_create_repository"
        ) as mock_safe_create:
            mock_safe_create.side_effect = Exception("Critical error")

            with pytest.raises(ForkDataCollectionError) as exc_info:
                engine.collect_fork_data([valid_fork_data])

            assert "Failed to collect fork data" in str(exc_info.value)
            assert "Critical error" in str(exc_info.value)

    def test_collect_fork_data_validation_summary_structure(
        self, engine, valid_fork_data, invalid_fork_data
    ):
        """Test that validation summary has correct structure."""
        with patch(
            "forklift.models.github.Repository.from_github_api"
        ) as mock_from_api:

            def side_effect(data):
                if data.get("name") == "maybe.._..maybe":
                    raise ValueError("Repository validation failed")
                return Repository(
                    id=data["id"],
                    name=data["name"],
                    full_name=data["full_name"],
                    owner=data["owner"]["login"],
                    html_url=data["html_url"],
                    clone_url=data["clone_url"],
                    url=data["url"],
                )

            mock_from_api.side_effect = side_effect

            forks = [valid_fork_data, invalid_fork_data]
            repositories, validation_summary = engine.collect_fork_data(forks)

            # Verify validation summary structure
            assert hasattr(validation_summary, "processed")
            assert hasattr(validation_summary, "skipped")
            assert hasattr(validation_summary, "errors")
            assert hasattr(validation_summary, "has_errors")
            assert hasattr(validation_summary, "get_error_summary")

            # Verify error structure
            error = validation_summary.errors[0]
            assert "repository" in error
            assert "error" in error
            assert "data" in error

    def test_collect_fork_data_requirements_coverage(
        self, engine, valid_fork_data, invalid_fork_data
    ):
        """Test that all requirements are covered by the implementation."""
        with patch(
            "forklift.models.github.Repository.from_github_api"
        ) as mock_from_api:

            def side_effect(data):
                if data.get("name") == "maybe.._..maybe":
                    raise ValueError("Repository validation failed")
                return Repository(
                    id=data["id"],
                    name=data["name"],
                    full_name=data["full_name"],
                    owner=data["owner"]["login"],
                    html_url=data["html_url"],
                    clone_url=data["clone_url"],
                    url=data["url"],
                )

            mock_from_api.side_effect = side_effect

            forks = [valid_fork_data, invalid_fork_data]
            repositories, validation_summary = engine.collect_fork_data(forks)

            # Requirement 1.2: Continue processing other forks instead of failing completely
            assert (
                len(repositories) == 1
            )  # Valid fork was processed despite invalid one

            # Requirement 1.3: Log warning but continue execution
            # (Verified in logging tests above)

            # Requirement 4.1: Handle validation errors for individual repositories gracefully
            assert (
                validation_summary.skipped == 1
            )  # Invalid repository was handled gracefully

            # Requirement 4.2: Continue processing remaining repositories
            assert (
                validation_summary.processed == 1
            )  # Valid repository was still processed
