"""Integration tests for end-to-end validation error handling."""

import logging
from io import StringIO
from unittest.mock import AsyncMock, Mock, patch

import pytest
from rich.console import Console

from forklift.analysis.fork_data_collection_engine import ForkDataCollectionEngine
from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.github.client import GitHubClient
from forklift.models.validation_handler import ValidationHandler, ValidationSummary


class TestValidationErrorHandlingIntegration:
    """Integration tests for end-to-end validation error handling."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        client = AsyncMock(spec=GitHubClient)
        return client

    @pytest.fixture
    def display_service(self, mock_github_client):
        """Create a display service instance for testing."""
        return RepositoryDisplayService(
            github_client=mock_github_client,
            console=Console(file=StringIO(), width=80)
        )

    @pytest.fixture
    def fork_data_collection_engine(self):
        """Create a fork data collection engine."""
        return ForkDataCollectionEngine()

    @pytest.fixture
    def mixed_valid_invalid_fork_data(self):
        """Create mixed valid and invalid repository data for testing."""
        return [
            # Valid repository data
            {
                "id": 1,
                "name": "valid-repo",
                "full_name": "user1/valid-repo",
                "owner": {"login": "user1"},
                "url": "https://api.github.com/repos/user1/valid-repo",
                "html_url": "https://github.com/user1/valid-repo",
                "clone_url": "https://github.com/user1/valid-repo.git",
                "stargazers_count": 10,
                "forks_count": 5,
                "watchers_count": 10,
                "open_issues_count": 2,
                "size": 1024,
                "language": "Python",
                "topics": ["python", "testing"],
                "default_branch": "main",
                "private": False,
                "fork": True,
                "archived": False,
                "disabled": False,
                "license": {"key": "mit", "name": "MIT License"},
                "description": "A valid test repository",
                "homepage": "https://example.com",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-12-01T00:00:00Z",
                "pushed_at": "2023-11-01T00:00:00Z",
            },
            # Repository with consecutive periods (should be allowed with relaxed validation)
            {
                "id": 2,
                "name": "repo..with..periods",
                "full_name": "user2/repo..with..periods",
                "owner": {"login": "user2"},
                "url": "https://api.github.com/repos/user2/repo..with..periods",
                "html_url": "https://github.com/user2/repo..with..periods",
                "clone_url": "https://github.com/user2/repo..with..periods.git",
                "stargazers_count": 3,
                "forks_count": 1,
                "watchers_count": 3,
                "open_issues_count": 0,
                "size": 512,
                "language": "JavaScript",
                "topics": ["javascript"],
                "default_branch": "main",
                "private": False,
                "fork": True,
                "archived": False,
                "disabled": False,
                "license": {"key": "apache-2.0", "name": "Apache License 2.0"},
                "description": "Repository with consecutive periods",
                "homepage": None,
                "created_at": "2023-02-01T00:00:00Z",
                "updated_at": "2023-11-01T00:00:00Z",
                "pushed_at": "2023-10-15T00:00:00Z",
            },
            # Repository with leading period (should fail validation)
            {
                "id": 3,
                "name": ".leading-period",
                "full_name": "user3/.leading-period",
                "owner": {"login": "user3"},
                "url": "https://api.github.com/repos/user3/.leading-period",
                "html_url": "https://github.com/user3/.leading-period",
                "clone_url": "https://github.com/user3/.leading-period.git",
                "stargazers_count": 1,
                "forks_count": 0,
                "watchers_count": 1,
                "open_issues_count": 0,
                "size": 256,
                "language": "Go",
                "topics": ["go"],
                "default_branch": "main",
                "private": False,
                "fork": True,
                "archived": False,
                "disabled": False,
                "license": {"key": "bsd-3-clause", "name": "BSD 3-Clause License"},
                "description": "Repository with leading period",
                "homepage": None,
                "created_at": "2023-03-01T00:00:00Z",
                "updated_at": "2023-10-01T00:00:00Z",
                "pushed_at": "2023-09-15T00:00:00Z",
            },
            # Repository with trailing period (should fail validation)
            {
                "id": 4,
                "name": "trailing-period.",
                "full_name": "user4/trailing-period.",
                "owner": {"login": "user4"},
                "url": "https://api.github.com/repos/user4/trailing-period.",
                "html_url": "https://github.com/user4/trailing-period.",
                "clone_url": "https://github.com/user4/trailing-period..git",
                "stargazers_count": 2,
                "forks_count": 1,
                "watchers_count": 2,
                "open_issues_count": 1,
                "size": 128,
                "language": "Rust",
                "topics": ["rust"],
                "default_branch": "main",
                "private": False,
                "fork": True,
                "archived": False,
                "disabled": False,
                "license": {"key": "mit", "name": "MIT License"},
                "description": "Repository with trailing period",
                "homepage": None,
                "created_at": "2023-04-01T00:00:00Z",
                "updated_at": "2023-09-01T00:00:00Z",
                "pushed_at": "2023-08-15T00:00:00Z",
            },
            # Another valid repository
            {
                "id": 5,
                "name": "another-valid-repo",
                "full_name": "user5/another-valid-repo",
                "owner": {"login": "user5"},
                "url": "https://api.github.com/repos/user5/another-valid-repo",
                "html_url": "https://github.com/user5/another-valid-repo",
                "clone_url": "https://github.com/user5/another-valid-repo.git",
                "stargazers_count": 15,
                "forks_count": 8,
                "watchers_count": 15,
                "open_issues_count": 3,
                "size": 2048,
                "language": "TypeScript",
                "topics": ["typescript", "web", "frontend"],
                "default_branch": "main",
                "private": False,
                "fork": True,
                "archived": False,
                "disabled": False,
                "license": {"key": "mit", "name": "MIT License"},
                "description": "Another valid test repository",
                "homepage": "https://example.org",
                "created_at": "2023-05-01T00:00:00Z",
                "updated_at": "2023-11-15T00:00:00Z",
                "pushed_at": "2023-11-10T00:00:00Z",
            },
        ]

    @pytest.fixture
    def completely_invalid_fork_data(self):
        """Create completely invalid repository data for testing."""
        return [
            # Missing required fields
            {
                "id": "invalid_id",  # Wrong type
                "name": "incomplete-repo",
                # Missing full_name, owner, urls, etc.
            },
            # Invalid data types
            {
                "id": 999,
                "name": 123,  # Wrong type - should be string
                "full_name": "user/numeric-name",
                "owner": "not_a_dict",  # Wrong type - should be dict
                "stargazers_count": "not_a_number",  # Wrong type
            },
            # Empty/null values for required fields
            {
                "id": 1000,
                "name": "",  # Empty name
                "full_name": "",
                "owner": {"login": ""},
                "url": "",
                "html_url": "",
                "clone_url": "",
            },
        ]

    def test_fork_data_collection_with_mixed_valid_invalid_data(
        self, fork_data_collection_engine, mixed_valid_invalid_fork_data
    ):
        """Test full fork processing pipeline with mixed valid/invalid repository data.

        Requirements: 1.1, 1.2, 4.1, 4.2
        """
        # Process the mixed data
        repositories, validation_summary = fork_data_collection_engine.collect_fork_data(
            mixed_valid_invalid_fork_data
        )

        # Verify that valid repositories were processed successfully
        # With relaxed validation: consecutive periods allowed, leading/trailing periods rejected
        assert len(repositories) == 3  # valid-repo, repo..with..periods, another-valid-repo
        assert validation_summary.processed == 3
        assert validation_summary.skipped == 2  # .leading-period and trailing-period.
        assert validation_summary.has_errors()
        assert len(validation_summary.errors) == 2

        # Verify the valid repositories
        repo_names = [repo.name for repo in repositories]
        assert "valid-repo" in repo_names
        assert "repo..with..periods" in repo_names  # Should be allowed with relaxed validation
        assert "another-valid-repo" in repo_names

        # Verify the rejected repositories
        error_repos = [error["repository"] for error in validation_summary.errors]
        assert "user3/.leading-period" in error_repos
        assert "user4/trailing-period." in error_repos

        # Verify error summary
        error_summary = validation_summary.get_error_summary()
        assert "2 items skipped due to validation errors" in error_summary

    def test_fork_data_collection_with_completely_invalid_data(
        self, fork_data_collection_engine, completely_invalid_fork_data
    ):
        """Test fork processing with completely invalid data.

        Requirements: 4.1, 4.2
        """
        # Process the invalid data
        repositories, validation_summary = fork_data_collection_engine.collect_fork_data(
            completely_invalid_fork_data
        )

        # All repositories should be skipped due to validation errors
        assert len(repositories) == 0
        assert validation_summary.processed == 0
        assert validation_summary.skipped == 3
        assert validation_summary.has_errors()
        assert len(validation_summary.errors) == 3

        # Verify error summary
        error_summary = validation_summary.get_error_summary()
        assert "3 items skipped due to validation errors" in error_summary

    def test_individual_validation_failures_dont_crash_process(
        self, fork_data_collection_engine, mixed_valid_invalid_fork_data
    ):
        """Verify that individual validation failures don't crash the entire process.

        Requirements: 1.1, 1.2, 4.1, 4.2
        """
        # This should not raise any exceptions despite having invalid data
        try:
            repositories, validation_summary = fork_data_collection_engine.collect_fork_data(
                mixed_valid_invalid_fork_data
            )

            # Process should complete successfully
            assert isinstance(repositories, list)
            assert isinstance(validation_summary, ValidationSummary)

            # Some repositories should be processed, some skipped
            assert validation_summary.processed > 0
            assert validation_summary.skipped > 0

        except Exception as e:
            pytest.fail(f"Fork data collection should not crash on invalid data, but got: {e}")

    @pytest.mark.asyncio
    async def test_display_service_behavior_with_validation_errors(
        self, display_service, mixed_valid_invalid_fork_data
    ):
        """Test display service behavior when validation errors occur.

        Requirements: 1.4, 3.3, 3.4
        """
        # Mock the dependencies to return our test data
        with patch("forklift.github.fork_list_processor.ForkListProcessor") as mock_processor_class, \
             patch("forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine") as mock_engine_class:

            # Setup mock processor
            mock_processor = AsyncMock()
            mock_processor.get_all_forks_list_data.return_value = mixed_valid_invalid_fork_data
            mock_processor_class.return_value = mock_processor

            # Setup mock data engine with real validation handler
            mock_engine = Mock()
            validation_handler = ValidationHandler()
            valid_repositories = []

            for fork_data in mixed_valid_invalid_fork_data:
                repo = validation_handler.safe_create_repository(fork_data)
                if repo:
                    valid_repositories.append(repo)
                    validation_handler.processed_count += 1

            validation_summary = validation_handler.get_summary()
            mock_engine.collect_fork_data.return_value = (valid_repositories, validation_summary)
            mock_engine_class.return_value = mock_engine

            # Capture console output
            output = StringIO()
            display_service.console = Console(file=output, width=80)

            # Test the display service method
            result = await display_service.show_forks_with_validation_summary(
                "owner/repo",
                verbose=True
            )

            # Verify the results
            assert result["total_forks"] == 5
            assert result["processed_forks"] == 3  # With relaxed validation
            assert result["skipped_forks"] == 2   # Leading and trailing periods rejected
            assert len(result["collected_forks"]) == 3

            # Verify console output contains validation summary
            output_text = output.getvalue()
            assert "Fork Analysis Results for owner/repo" in output_text
            assert "Successfully processed 3 forks" in output_text
            assert "repositories skipped due to validation errors" in output_text

    @pytest.mark.asyncio
    async def test_display_service_with_no_validation_errors(
        self, display_service
    ):
        """Test display service behavior when no validation errors occur."""
        # Create only valid fork data
        valid_fork_data = [
            {
                "id": 1,
                "name": "valid-repo-1",
                "full_name": "user1/valid-repo-1",
                "owner": {"login": "user1"},
                "url": "https://api.github.com/repos/user1/valid-repo-1",
                "html_url": "https://github.com/user1/valid-repo-1",
                "clone_url": "https://github.com/user1/valid-repo-1.git",
                "stargazers_count": 10,
                "forks_count": 5,
                "watchers_count": 10,
                "open_issues_count": 2,
                "size": 1024,
                "language": "Python",
                "topics": ["python"],
                "default_branch": "main",
                "private": False,
                "fork": True,
                "archived": False,
                "disabled": False,
                "license": {"key": "mit", "name": "MIT License"},
                "description": "Valid repository 1",
                "homepage": None,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-12-01T00:00:00Z",
                "pushed_at": "2023-11-01T00:00:00Z",
            },
            {
                "id": 2,
                "name": "valid-repo-2",
                "full_name": "user2/valid-repo-2",
                "owner": {"login": "user2"},
                "url": "https://api.github.com/repos/user2/valid-repo-2",
                "html_url": "https://github.com/user2/valid-repo-2",
                "clone_url": "https://github.com/user2/valid-repo-2.git",
                "stargazers_count": 5,
                "forks_count": 2,
                "watchers_count": 5,
                "open_issues_count": 1,
                "size": 512,
                "language": "JavaScript",
                "topics": ["javascript"],
                "default_branch": "main",
                "private": False,
                "fork": True,
                "archived": False,
                "disabled": False,
                "license": {"key": "apache-2.0", "name": "Apache License 2.0"},
                "description": "Valid repository 2",
                "homepage": None,
                "created_at": "2023-02-01T00:00:00Z",
                "updated_at": "2023-11-01T00:00:00Z",
                "pushed_at": "2023-10-15T00:00:00Z",
            },
        ]

        # Mock the dependencies
        with patch("forklift.github.fork_list_processor.ForkListProcessor") as mock_processor_class, \
             patch("forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine") as mock_engine_class:

            # Setup mocks
            mock_processor = AsyncMock()
            mock_processor.get_all_forks_list_data.return_value = valid_fork_data
            mock_processor_class.return_value = mock_processor

            mock_engine = Mock()
            validation_handler = ValidationHandler()
            valid_repositories = []

            for fork_data in valid_fork_data:
                repo = validation_handler.safe_create_repository(fork_data)
                if repo:
                    valid_repositories.append(repo)
                    validation_handler.processed_count += 1

            validation_summary = validation_handler.get_summary()
            mock_engine.collect_fork_data.return_value = (valid_repositories, validation_summary)
            mock_engine_class.return_value = mock_engine

            # Capture console output
            output = StringIO()
            display_service.console = Console(file=output, width=80)

            # Test the display service method
            result = await display_service.show_forks_with_validation_summary(
                "owner/repo",
                verbose=False
            )

            # Verify the results
            assert result["total_forks"] == 2
            assert result["processed_forks"] == 2
            assert result["skipped_forks"] == 0
            assert len(result["collected_forks"]) == 2

            # Verify console output does not contain validation warnings
            output_text = output.getvalue()
            assert "Fork Analysis Results for owner/repo" in output_text
            assert "Successfully processed 2 forks" in output_text
            assert "skipped due to data validation issues" not in output_text

    def test_validation_handler_error_collection(self):
        """Test that ValidationHandler properly collects and reports errors."""
        handler = ValidationHandler()

        # Test with various invalid data
        invalid_data_sets = [
            {
                "id": "invalid",
                "name": ".leading-period",
                "full_name": "user/.leading-period",
            },
            {
                "id": 123,
                "name": "trailing-period.",
                "full_name": "user/trailing-period.",
            },
            {
                "name": 456,  # Wrong type
                "full_name": "user/numeric-name",
            },
        ]

        for invalid_data in invalid_data_sets:
            repo = handler.safe_create_repository(invalid_data)
            assert repo is None  # Should return None for invalid data

        # Verify error collection
        summary = handler.get_summary()
        assert summary.processed == 0
        assert summary.skipped == 3
        assert len(summary.errors) == 3
        assert summary.has_errors()

        # Verify error details
        for error in summary.errors:
            assert "repository" in error
            assert "error" in error
            assert "data" in error

    def test_validation_handler_mixed_data_processing(self, mixed_valid_invalid_fork_data):
        """Test ValidationHandler with mixed valid and invalid data."""
        handler = ValidationHandler()
        valid_repos = []

        for fork_data in mixed_valid_invalid_fork_data:
            repo = handler.safe_create_repository(fork_data)
            if repo:
                valid_repos.append(repo)
                handler.processed_count += 1

        summary = handler.get_summary()

        # With relaxed validation: consecutive periods allowed, leading/trailing rejected
        assert len(valid_repos) == 3
        assert summary.processed == 3
        assert summary.skipped == 2
        assert len(summary.errors) == 2

        # Verify valid repositories
        valid_names = [repo.name for repo in valid_repos]
        assert "valid-repo" in valid_names
        assert "repo..with..periods" in valid_names  # Should be allowed
        assert "another-valid-repo" in valid_names

    def test_validation_handler_reset_functionality(self):
        """Test ValidationHandler reset functionality."""
        handler = ValidationHandler()

        # Process some data
        invalid_data = {
            "id": "invalid",
            "name": ".invalid",
            "full_name": "user/.invalid",
        }

        repo = handler.safe_create_repository(invalid_data)
        assert repo is None

        # Verify state before reset
        summary = handler.get_summary()
        assert summary.skipped == 1
        assert len(summary.errors) == 1

        # Reset and verify clean state
        handler.reset()
        summary_after_reset = handler.get_summary()
        assert summary_after_reset.processed == 0
        assert summary_after_reset.skipped == 0
        assert len(summary_after_reset.errors) == 0
        assert not summary_after_reset.has_errors()

    def test_validation_handler_logging(self, caplog, mixed_valid_invalid_fork_data):
        """Test that ValidationHandler logs validation issues appropriately."""
        handler = ValidationHandler()

        with caplog.at_level(logging.INFO):  # Capture INFO level to get success messages
            for fork_data in mixed_valid_invalid_fork_data:
                repo = handler.safe_create_repository(fork_data)
                if repo:
                    handler.processed_count += 1  # Increment processed count for successful repos

            # Should log summary
            handler.log_summary()

        # Verify logging for validation errors
        log_messages = [record.message for record in caplog.records]

        # Should log warnings for repositories with leading/trailing periods
        leading_period_logged = any(
            ".leading-period" in msg and "Validation error" in msg
            for msg in log_messages
        )
        trailing_period_logged = any(
            "trailing-period." in msg and "Validation error" in msg
            for msg in log_messages
        )

        assert leading_period_logged
        assert trailing_period_logged

        # Verify summary logging
        summary_logged = any(
            "Successfully processed" in msg for msg in log_messages
        )
        validation_errors_logged = any(
            "Skipped" in msg and "validation errors" in msg for msg in log_messages
        )

        assert summary_logged
        assert validation_errors_logged

    @pytest.mark.asyncio
    async def test_end_to_end_validation_pipeline_resilience(
        self, display_service, mixed_valid_invalid_fork_data, completely_invalid_fork_data
    ):
        """Test end-to-end pipeline resilience with various error scenarios.

        Requirements: 1.1, 1.2, 4.1, 4.2
        """
        # Combine mixed and completely invalid data for maximum stress test
        all_test_data = mixed_valid_invalid_fork_data + completely_invalid_fork_data

        # Mock the dependencies
        with patch("forklift.github.fork_list_processor.ForkListProcessor") as mock_processor_class, \
             patch("forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine") as mock_engine_class:

            # Setup mocks
            mock_processor = AsyncMock()
            mock_processor.get_all_forks_list_data.return_value = all_test_data
            mock_processor_class.return_value = mock_processor

            mock_engine = Mock()
            validation_handler = ValidationHandler()
            valid_repositories = []

            for fork_data in all_test_data:
                repo = validation_handler.safe_create_repository(fork_data)
                if repo:
                    valid_repositories.append(repo)
                    validation_handler.processed_count += 1

            validation_summary = validation_handler.get_summary()
            mock_engine.collect_fork_data.return_value = (valid_repositories, validation_summary)
            mock_engine_class.return_value = mock_engine

            # Capture console output
            output = StringIO()
            display_service.console = Console(file=output, width=80)

            # This should not crash despite having many invalid repositories
            try:
                result = await display_service.show_forks_with_validation_summary(
                    "owner/repo",
                    verbose=True
                )

                # Verify the pipeline completed successfully
                assert isinstance(result, dict)
                assert "total_forks" in result
                assert "processed_forks" in result
                assert "skipped_forks" in result
                assert "collected_forks" in result

                # Should have processed some valid repositories
                assert result["processed_forks"] > 0
                # Should have skipped invalid repositories
                assert result["skipped_forks"] > 0
                # Total should equal processed + skipped
                assert result["total_forks"] == result["processed_forks"] + result["skipped_forks"]

                # Verify console output includes appropriate messaging
                output_text = output.getvalue()
                assert "Fork Analysis Results" in output_text
                assert "repositories skipped due to validation errors" in output_text

            except Exception as e:
                pytest.fail(f"End-to-end pipeline should be resilient to validation errors, but got: {e}")

    def test_validation_summary_error_reporting(self):
        """Test ValidationSummary error reporting functionality."""
        # Create a validation summary with errors
        errors = [
            {
                "repository": "user1/.invalid",
                "error": "GitHub names cannot start with a period",
                "data": {"name": ".invalid"}
            },
            {
                "repository": "user2/invalid.",
                "error": "GitHub names cannot end with a period",
                "data": {"name": "invalid."}
            },
        ]

        summary = ValidationSummary(
            processed=2,
            skipped=2,
            errors=errors
        )

        # Test error reporting methods
        assert summary.has_errors()
        assert summary.get_error_summary() == "2 items skipped due to validation errors"
        assert len(summary.errors) == 2

        # Test with no errors
        no_error_summary = ValidationSummary(
            processed=5,
            skipped=0,
            errors=[]
        )

        assert not no_error_summary.has_errors()
        assert no_error_summary.get_error_summary() == "No validation errors"
