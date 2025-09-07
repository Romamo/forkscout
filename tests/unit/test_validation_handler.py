"""Tests for ValidationHandler service."""

import pytest
from pydantic import ValidationError

from forklift.models.validation_handler import ValidationHandler, ValidationSummary


class TestValidationSummary:
    """Test ValidationSummary model."""

    def test_validation_summary_creation(self):
        """Test ValidationSummary can be created with basic data."""
        summary = ValidationSummary(
            processed=5,
            skipped=2,
            errors=[
                {"repository": "test/repo1", "error": "Invalid name"},
                {"repository": "test/repo2", "error": "Missing field"}
            ]
        )
        
        assert summary.processed == 5
        assert summary.skipped == 2
        assert len(summary.errors) == 2
        assert summary.has_errors() is True

    def test_validation_summary_no_errors(self):
        """Test ValidationSummary with no errors."""
        summary = ValidationSummary(
            processed=10,
            skipped=0,
            errors=[]
        )
        
        assert summary.processed == 10
        assert summary.skipped == 0
        assert len(summary.errors) == 0
        assert summary.has_errors() is False

    def test_get_error_summary_with_errors(self):
        """Test get_error_summary when there are errors."""
        summary = ValidationSummary(
            processed=5,
            skipped=3,
            errors=[{"repository": "test/repo", "error": "Invalid"}]
        )
        
        result = summary.get_error_summary()
        assert result == "3 items skipped due to validation errors"

    def test_get_error_summary_no_errors(self):
        """Test get_error_summary when there are no errors."""
        summary = ValidationSummary(
            processed=10,
            skipped=0,
            errors=[]
        )
        
        result = summary.get_error_summary()
        assert result == "No validation errors"


class TestValidationHandler:
    """Test ValidationHandler service."""

    def test_validation_handler_initialization(self):
        """Test ValidationHandler initializes with correct defaults."""
        handler = ValidationHandler()
        
        assert handler.processed_count == 0
        assert handler.skipped_count == 0
        assert handler.validation_errors == []

    def test_safe_create_repository_success(self):
        """Test safe_create_repository with valid data."""
        handler = ValidationHandler()
        
        # Valid repository data
        valid_data = {
            "id": 123,
            "name": "test-repo",
            "full_name": "owner/test-repo",
            "owner": {"login": "owner"},
            "url": "https://api.github.com/repos/owner/test-repo",
            "html_url": "https://github.com/owner/test-repo",
            "clone_url": "https://github.com/owner/test-repo.git",
            "stargazers_count": 10,
            "forks_count": 5,
            "watchers_count": 8,
            "open_issues_count": 2,
            "size": 1024,
            "private": False,
            "fork": False,
            "archived": False,
            "disabled": False,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-02T00:00:00Z",
            "pushed_at": "2023-01-02T12:00:00Z"
        }
        
        repository = handler.safe_create_repository(valid_data)
        
        assert repository is not None
        assert repository.name == "test-repo"
        assert repository.owner == "owner"
        assert handler.skipped_count == 0
        assert len(handler.validation_errors) == 0

    def test_safe_create_repository_validation_error(self):
        """Test safe_create_repository with invalid data that causes ValidationError."""
        handler = ValidationHandler()
        
        # Invalid repository data - missing required fields
        invalid_data = {
            "name": "test-repo",
            # Missing owner, full_name, urls, etc.
        }
        
        repository = handler.safe_create_repository(invalid_data)
        
        assert repository is None
        assert handler.skipped_count == 1
        assert len(handler.validation_errors) == 1
        
        error_record = handler.validation_errors[0]
        assert error_record["repository"] == "unknown"  # No full_name in data
        assert "error" in error_record
        assert "data" in error_record

    def test_safe_create_repository_with_full_name_in_error(self):
        """Test safe_create_repository records full_name when available."""
        handler = ValidationHandler()
        
        # Invalid data but with full_name
        invalid_data = {
            "full_name": "owner/test-repo",
            "name": "test-repo",
            # Missing other required fields
        }
        
        repository = handler.safe_create_repository(invalid_data)
        
        assert repository is None
        assert handler.skipped_count == 1
        assert len(handler.validation_errors) == 1
        
        error_record = handler.validation_errors[0]
        assert error_record["repository"] == "owner/test-repo"

    def test_safe_create_repository_edge_case_names(self):
        """Test safe_create_repository with edge case repository names."""
        handler = ValidationHandler()
        
        # Repository with consecutive periods (should be allowed now)
        edge_case_data = {
            "id": 123,
            "name": "repo..with..periods",
            "full_name": "owner/repo..with..periods",
            "owner": {"login": "owner"},
            "url": "https://api.github.com/repos/owner/repo..with..periods",
            "html_url": "https://github.com/owner/repo..with..periods",
            "clone_url": "https://github.com/owner/repo..with..periods.git",
            "stargazers_count": 0,
            "forks_count": 0,
            "watchers_count": 0,
            "open_issues_count": 0,
            "size": 0,
            "private": False,
            "fork": False,
            "archived": False,
            "disabled": False,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-02T00:00:00Z",
            "pushed_at": "2023-01-02T12:00:00Z"
        }
        
        repository = handler.safe_create_repository(edge_case_data)
        
        # Should succeed with the updated validation rules
        assert repository is not None
        assert repository.name == "repo..with..periods"
        assert handler.skipped_count == 0
        assert len(handler.validation_errors) == 0

    def test_get_summary(self):
        """Test get_summary returns correct summary data."""
        handler = ValidationHandler()
        handler.processed_count = 8
        handler.skipped_count = 2
        handler.validation_errors = [
            {"repository": "test/repo1", "error": "Invalid name"},
            {"repository": "test/repo2", "error": "Missing field"}
        ]
        
        summary = handler.get_summary()
        
        assert isinstance(summary, ValidationSummary)
        assert summary.processed == 8
        assert summary.skipped == 2
        assert len(summary.errors) == 2
        assert summary.has_errors() is True

    def test_multiple_repositories_processing(self):
        """Test processing multiple repositories with mixed success/failure."""
        handler = ValidationHandler()
        
        # Mix of valid and invalid data
        repositories_data = [
            # Valid repository
            {
                "id": 1,
                "name": "valid-repo",
                "full_name": "owner/valid-repo",
                "owner": {"login": "owner"},
                "url": "https://api.github.com/repos/owner/valid-repo",
                "html_url": "https://github.com/owner/valid-repo",
                "clone_url": "https://github.com/owner/valid-repo.git",
                "stargazers_count": 0,
                "forks_count": 0,
                "watchers_count": 0,
                "open_issues_count": 0,
                "size": 0,
                "private": False,
                "fork": False,
                "archived": False,
                "disabled": False,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-02T00:00:00Z",
                "pushed_at": "2023-01-02T12:00:00Z"
            },
            # Invalid repository - missing required fields
            {
                "name": "invalid-repo",
                "full_name": "owner/invalid-repo"
            },
            # Another valid repository
            {
                "id": 2,
                "name": "another-valid",
                "full_name": "owner/another-valid",
                "owner": {"login": "owner"},
                "url": "https://api.github.com/repos/owner/another-valid",
                "html_url": "https://github.com/owner/another-valid",
                "clone_url": "https://github.com/owner/another-valid.git",
                "stargazers_count": 0,
                "forks_count": 0,
                "watchers_count": 0,
                "open_issues_count": 0,
                "size": 0,
                "private": False,
                "fork": False,
                "archived": False,
                "disabled": False,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-02T00:00:00Z",
                "pushed_at": "2023-01-02T12:00:00Z"
            }
        ]
        
        valid_repositories = []
        for repo_data in repositories_data:
            repo = handler.safe_create_repository(repo_data)
            if repo:
                valid_repositories.append(repo)
                handler.processed_count += 1
        
        # Should have 2 valid repositories and 1 skipped
        assert len(valid_repositories) == 2
        assert handler.processed_count == 2
        assert handler.skipped_count == 1
        assert len(handler.validation_errors) == 1
        
        summary = handler.get_summary()
        assert summary.processed == 2
        assert summary.skipped == 1
        assert summary.has_errors() is True