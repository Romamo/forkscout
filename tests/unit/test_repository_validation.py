"""Unit tests for repository validation edge cases."""

import logging

import pytest

from forklift.models.github import Repository
from forklift.models.validation_handler import ValidationHandler

# Test fixtures with problematic repository names from real-world cases
REPOSITORY_NAME_TEST_CASES = [
    # Valid names that should pass without warnings
    ("valid-repo", True, False),
    ("repo.name", True, False),
    ("repo_name", True, False),
    ("123repo", True, False),
    ("repo-123", True, False),
    ("a", True, False),  # Single character
    ("a" * 100, True, False),  # Long name
    # Edge cases that should be allowed but warn
    (
        "maybe-finance.._..maybe",
        True,
        True,
    ),  # The actual failing case from requirements
    ("repo..name", True, True),  # Consecutive periods - warn but allow
    ("test...repo", True, True),  # Multiple consecutive periods
    ("repo..with..many..periods", True, True),  # Many consecutive periods
    ("owner..name", True, True),  # Consecutive periods in owner name
    # Invalid names that should fail
    (".invalid", False, False),  # Leading period
    ("invalid.", False, False),  # Trailing period
    ("", False, False),  # Empty name
    ("..", False, False),  # Only periods
    ("...", False, False),  # Only periods
    (".repo.", False, False),  # Both leading and trailing periods
]

# Real-world problematic repository data for testing
PROBLEMATIC_REPOSITORY_DATA = [
    {
        "name": "maybe-finance.._..maybe",
        "description": "Repository with consecutive periods that caused original issue",
        "api_data": {
            "id": 12345,
            "name": "maybe.._..maybe",
            "full_name": "maybe-finance/maybe.._..maybe",
            "owner": {"login": "maybe-finance"},
            "url": "https://api.github.com/repos/maybe-finance/maybe.._..maybe",
            "html_url": "https://github.com/maybe-finance/maybe.._..maybe",
            "clone_url": "https://github.com/maybe-finance/maybe.._..maybe.git",
            "default_branch": "main",
            "stargazers_count": 100,
            "forks_count": 25,
            "private": False,
            "fork": False,
            "archived": False,
            "disabled": False,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-02T00:00:00Z",
            "pushed_at": "2023-01-02T12:00:00Z",
        },
    },
    {
        "name": "repo..with..periods",
        "description": "Repository with multiple consecutive periods",
        "api_data": {
            "id": 67890,
            "name": "repo..with..periods",
            "full_name": "testowner/repo..with..periods",
            "owner": {"login": "testowner"},
            "url": "https://api.github.com/repos/testowner/repo..with..periods",
            "html_url": "https://github.com/testowner/repo..with..periods",
            "clone_url": "https://github.com/testowner/repo..with..periods.git",
            "default_branch": "master",
            "stargazers_count": 5,
            "forks_count": 2,
            "private": False,
            "fork": True,
            "archived": False,
            "disabled": False,
            "created_at": "2023-06-01T00:00:00Z",
            "updated_at": "2023-06-02T00:00:00Z",
            "pushed_at": "2023-06-02T12:00:00Z",
        },
    },
]


class TestRepositoryValidation:
    """Test cases for Repository validation edge cases."""

    def test_repository_with_consecutive_periods_should_warn_not_fail(self, caplog):
        """Test that repository names with consecutive periods log warnings but don't fail."""
        # This is the specific case mentioned in the requirements
        with caplog.at_level(logging.WARNING):
            repo = Repository(
                owner="maybe-finance",
                name="maybe.._..maybe",  # This should warn but not fail
                full_name="maybe-finance/maybe.._..maybe",
                url="https://api.github.com/repos/maybe-finance/maybe.._..maybe",
                html_url="https://github.com/maybe-finance/maybe.._..maybe",
                clone_url="https://github.com/maybe-finance/maybe.._..maybe.git",
            )

            # Should successfully create the repository
            assert repo.owner == "maybe-finance"
            assert repo.name == "maybe.._..maybe"
            assert repo.full_name == "maybe-finance/maybe.._..maybe"

            # Should have logged a warning about consecutive periods
            assert any(
                "consecutive periods" in record.message.lower()
                for record in caplog.records
            )

    def test_repository_with_leading_period_should_fail(self):
        """Test that repository names with leading periods still fail validation."""
        with pytest.raises(ValueError, match="cannot start or end with a period"):
            Repository(
                owner="testowner",
                name=".invalid",
                full_name="testowner/.invalid",
                url="https://api.github.com/repos/testowner/.invalid",
                html_url="https://github.com/testowner/.invalid",
                clone_url="https://github.com/testowner/.invalid.git",
            )

    def test_repository_with_trailing_period_should_fail(self):
        """Test that repository names with trailing periods still fail validation."""
        with pytest.raises(ValueError, match="cannot start or end with a period"):
            Repository(
                owner="testowner",
                name="invalid.",
                full_name="testowner/invalid.",
                url="https://api.github.com/repos/testowner/invalid.",
                html_url="https://github.com/testowner/invalid.",
                clone_url="https://github.com/testowner/invalid..git",
            )

    def test_repository_with_invalid_characters_should_warn_not_fail(self, caplog):
        """Test that repository names with unusual characters log warnings but don't fail."""
        with caplog.at_level(logging.WARNING):
            # This tests the edge case where GitHub might allow characters we don't expect
            repo = Repository(
                owner="testowner",
                name="repo-with-unusual-chars",  # This should be fine
                full_name="testowner/repo-with-unusual-chars",
                url="https://api.github.com/repos/testowner/repo-with-unusual-chars",
                html_url="https://github.com/testowner/repo-with-unusual-chars",
                clone_url="https://github.com/testowner/repo-with-unusual-chars.git",
            )

            assert repo.name == "repo-with-unusual-chars"

    def test_repository_validation_logging_includes_context(self, caplog):
        """Test that validation warnings include helpful context for debugging."""
        with caplog.at_level(logging.WARNING):
            Repository(
                owner="test-owner",
                name="test..repo",
                full_name="test-owner/test..repo",
                url="https://api.github.com/repos/test-owner/test..repo",
                html_url="https://github.com/test-owner/test..repo",
                clone_url="https://github.com/test-owner/test..repo.git",
            )

            # Should log the specific repository name for debugging
            warning_messages = [
                record.message
                for record in caplog.records
                if record.levelname == "WARNING"
            ]
            assert any("test..repo" in msg for msg in warning_messages)

    def test_owner_validation_with_consecutive_periods(self, caplog):
        """Test that owner names with consecutive periods also log warnings but don't fail."""
        with caplog.at_level(logging.WARNING):
            repo = Repository(
                owner="owner..name",  # This should warn but not fail
                name="testrepo",
                full_name="owner..name/testrepo",
                url="https://api.github.com/repos/owner..name/testrepo",
                html_url="https://github.com/owner..name/testrepo",
                clone_url="https://github.com/owner..name/testrepo.git",
            )

            assert repo.owner == "owner..name"
            assert any(
                "consecutive periods" in record.message.lower()
                for record in caplog.records
            )

    def test_from_github_api_with_consecutive_periods(self, caplog):
        """Test Repository.from_github_api with consecutive periods in name."""
        api_data = {
            "id": 12345,
            "name": "maybe.._..maybe",
            "full_name": "maybe-finance/maybe.._..maybe",
            "owner": {"login": "maybe-finance"},
            "url": "https://api.github.com/repos/maybe-finance/maybe.._..maybe",
            "html_url": "https://github.com/maybe-finance/maybe.._..maybe",
            "clone_url": "https://github.com/maybe-finance/maybe.._..maybe.git",
            "default_branch": "main",
            "stargazers_count": 100,
            "forks_count": 25,
            "private": False,
            "fork": False,
            "archived": False,
            "disabled": False,
        }

        with caplog.at_level(logging.WARNING):
            repo = Repository.from_github_api(api_data)

            assert repo.name == "maybe.._..maybe"
            assert repo.owner == "maybe-finance"
            assert any(
                "consecutive periods" in record.message.lower()
                for record in caplog.records
            )

    @pytest.mark.parametrize("name,should_pass,should_warn", REPOSITORY_NAME_TEST_CASES)
    def test_repository_name_validation_patterns(
        self, name, should_pass, should_warn, caplog
    ):
        """Test repository name validation with various patterns."""
        with caplog.at_level(logging.WARNING):
            if should_pass:
                # Should successfully create repository
                repo = Repository(
                    owner="testowner",
                    name=name,
                    full_name=f"testowner/{name}",
                    url=f"https://api.github.com/repos/testowner/{name}",
                    html_url=f"https://github.com/testowner/{name}",
                    clone_url=f"https://github.com/testowner/{name}.git",
                )
                assert repo.name == name

                # Check if warning was logged when expected
                if should_warn:
                    assert any(
                        "consecutive periods" in record.message.lower()
                        for record in caplog.records
                    )
                else:
                    # Should not have warnings for valid names
                    warning_messages = [
                        record.message
                        for record in caplog.records
                        if record.levelname == "WARNING"
                    ]
                    assert not any(
                        "consecutive periods" in msg.lower() for msg in warning_messages
                    )
            else:
                # Should fail validation
                with pytest.raises(ValueError):
                    Repository(
                        owner="testowner",
                        name=name,
                        full_name=f"testowner/{name}",
                        url=f"https://api.github.com/repos/testowner/{name}",
                        html_url=f"https://github.com/testowner/{name}",
                        clone_url=f"https://github.com/testowner/{name}.git",
                    )

    @pytest.mark.parametrize("repo_data", PROBLEMATIC_REPOSITORY_DATA)
    def test_problematic_repository_data_fixtures(self, repo_data, caplog):
        """Test with real-world problematic repository data fixtures."""
        with caplog.at_level(logging.WARNING):
            repo = Repository.from_github_api(repo_data["api_data"])

            # Should successfully create repository despite edge-case name
            assert repo is not None
            assert repo.name == repo_data["api_data"]["name"]
            assert repo.owner == repo_data["api_data"]["owner"]["login"]

            # Should log warning for consecutive periods
            if ".." in repo_data["api_data"]["name"]:
                assert any(
                    "consecutive periods" in record.message.lower()
                    for record in caplog.records
                )

    def test_validation_handler_with_edge_case_repositories(self):
        """Test ValidationHandler with various edge-case repository names."""
        handler = ValidationHandler()

        # Test with all problematic repository data
        valid_repositories = []
        for repo_data in PROBLEMATIC_REPOSITORY_DATA:
            repo = handler.safe_create_repository(repo_data["api_data"])
            if repo:
                valid_repositories.append(repo)
                handler.processed_count += 1

        # All should be processed successfully with updated validation
        assert len(valid_repositories) == len(PROBLEMATIC_REPOSITORY_DATA)
        assert handler.processed_count == len(PROBLEMATIC_REPOSITORY_DATA)
        assert handler.skipped_count == 0
        assert len(handler.validation_errors) == 0

        summary = handler.get_summary()
        assert summary.processed == len(PROBLEMATIC_REPOSITORY_DATA)
        assert summary.skipped == 0
        assert not summary.has_errors()

    def test_validation_handler_error_collection_comprehensive(self):
        """Test ValidationHandler comprehensive error collection and reporting."""
        handler = ValidationHandler()

        # Mix of valid, edge-case, and invalid repository data
        test_data = [
            # Valid repository
            {
                "id": 1,
                "name": "valid-repo",
                "full_name": "owner/valid-repo",
                "owner": {"login": "owner"},
                "url": "https://api.github.com/repos/owner/valid-repo",
                "html_url": "https://github.com/owner/valid-repo",
                "clone_url": "https://github.com/owner/valid-repo.git",
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
                "pushed_at": "2023-01-02T12:00:00Z",
            },
            # Edge case with consecutive periods (should work now)
            {
                "id": 2,
                "name": "edge..case",
                "full_name": "owner/edge..case",
                "owner": {"login": "owner"},
                "url": "https://api.github.com/repos/owner/edge..case",
                "html_url": "https://github.com/owner/edge..case",
                "clone_url": "https://github.com/owner/edge..case.git",
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
                "pushed_at": "2023-01-02T12:00:00Z",
            },
            # Invalid repository - missing required fields
            {
                "name": "invalid-repo",
                "full_name": "owner/invalid-repo",
                # Missing required fields like owner, urls, etc.
            },
            # Another invalid - completely malformed
            {
                "id": "not-a-number",  # Invalid type
                "name": 123,  # Invalid type
                "full_name": "owner/malformed",
            },
        ]

        valid_repositories = []
        for repo_data in test_data:
            repo = handler.safe_create_repository(repo_data)
            if repo:
                valid_repositories.append(repo)
                handler.processed_count += 1

        # Should have 2 valid repositories (including edge case) and 2 skipped
        assert len(valid_repositories) == 2
        assert handler.processed_count == 2
        assert handler.skipped_count == 2
        assert len(handler.validation_errors) == 2

        # Check error details
        error_repos = [error["repository"] for error in handler.validation_errors]
        assert "owner/invalid-repo" in error_repos
        assert "owner/malformed" in error_repos

        # Test summary generation
        summary = handler.get_summary()
        assert summary.processed == 2
        assert summary.skipped == 2
        assert summary.has_errors() is True
        assert summary.get_error_summary() == "2 items skipped due to validation errors"

    def test_validation_handler_all_failures_scenario(self):
        """Test ValidationHandler when all repositories fail validation."""
        handler = ValidationHandler()

        # All invalid repository data
        invalid_data_list = [
            {"name": "incomplete1"},  # Missing required fields
            {"name": "incomplete2"},  # Missing required fields
            {"invalid": "structure"},  # Wrong structure entirely
        ]

        valid_repositories = []
        for repo_data in invalid_data_list:
            repo = handler.safe_create_repository(repo_data)
            if repo:
                valid_repositories.append(repo)
                handler.processed_count += 1

        # All should fail
        assert len(valid_repositories) == 0
        assert handler.processed_count == 0
        assert handler.skipped_count == 3
        assert len(handler.validation_errors) == 3

        summary = handler.get_summary()
        assert summary.processed == 0
        assert summary.skipped == 3
        assert summary.has_errors() is True
        assert "3 items skipped" in summary.get_error_summary()

    def test_validation_error_context_and_debugging_info(self):
        """Test that validation errors include helpful context for debugging."""
        handler = ValidationHandler()

        # Repository with specific validation issue
        problematic_data = {
            "name": "test-repo",
            "full_name": "owner/test-repo",
            # Missing critical fields like owner, urls
        }

        repo = handler.safe_create_repository(problematic_data)

        assert repo is None
        assert len(handler.validation_errors) == 1

        error_record = handler.validation_errors[0]
        assert error_record["repository"] == "owner/test-repo"
        assert "error" in error_record
        assert "data" in error_record
        assert error_record["data"] == problematic_data

        # Error message should be descriptive
        assert len(error_record["error"]) > 0

    def test_repository_validation_backward_compatibility(self):
        """Test that validation changes maintain backward compatibility."""
        # Test that repositories that were valid before are still valid
        classic_valid_names = [
            "simple-repo",
            "repo_with_underscores",
            "repo.with.dots",
            "123numeric",
            "CamelCase",  # Though not typical, should still work
        ]

        for name in classic_valid_names:
            repo = Repository(
                owner="testowner",
                name=name,
                full_name=f"testowner/{name}",
                url=f"https://api.github.com/repos/testowner/{name}",
                html_url=f"https://github.com/testowner/{name}",
                clone_url=f"https://github.com/testowner/{name}.git",
            )
            assert repo.name == name

    def test_validation_performance_with_large_dataset(self):
        """Test validation performance doesn't degrade with larger datasets."""
        handler = ValidationHandler()

        # Create a larger dataset of mixed valid/invalid repositories
        large_dataset = []

        # Add many valid repositories
        large_dataset.extend(
            [
                {
                    "id": i,
                    "name": f"repo-{i}",
                    "full_name": f"owner/repo-{i}",
                    "owner": {"login": "owner"},
                    "url": f"https://api.github.com/repos/owner/repo-{i}",
                    "html_url": f"https://github.com/owner/repo-{i}",
                    "clone_url": f"https://github.com/owner/repo-{i}.git",
                    "stargazers_count": i,
                    "forks_count": i // 2,
                    "watchers_count": i,
                    "open_issues_count": 0,
                    "size": 1024,
                    "private": False,
                    "fork": False,
                    "archived": False,
                    "disabled": False,
                    "created_at": "2023-01-01T00:00:00Z",
                    "updated_at": "2023-01-02T00:00:00Z",
                    "pushed_at": "2023-01-02T12:00:00Z",
                }
                for i in range(50)
            ]
        )

        # Add some edge cases
        large_dataset.extend(
            [
                {
                    "id": 100 + i,
                    "name": f"edge..case.{i}",
                    "full_name": f"owner/edge..case.{i}",
                    "owner": {"login": "owner"},
                    "url": f"https://api.github.com/repos/owner/edge..case.{i}",
                    "html_url": f"https://github.com/owner/edge..case.{i}",
                    "clone_url": f"https://github.com/owner/edge..case.{i}.git",
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
                    "pushed_at": "2023-01-02T12:00:00Z",
                }
                for i in range(5)
            ]
        )

        # Add some invalid ones
        large_dataset.extend(
            [
                {
                    "name": f"invalid-{i}",
                    "full_name": f"owner/invalid-{i}",
                    # Missing required fields
                }
                for i in range(5)
            ]
        )

        # Process all repositories
        valid_repositories = []
        for repo_data in large_dataset:
            repo = handler.safe_create_repository(repo_data)
            if repo:
                valid_repositories.append(repo)
                handler.processed_count += 1

        # Should process 55 valid repositories (50 normal + 5 edge cases)
        assert len(valid_repositories) == 55
        assert handler.processed_count == 55
        assert handler.skipped_count == 5  # 5 invalid ones

        summary = handler.get_summary()
        assert summary.processed == 55
        assert summary.skipped == 5


class TestValidationHandlerComprehensive:
    """Comprehensive tests for ValidationHandler service focusing on requirements 4.1-4.4."""

    def test_graceful_individual_repository_failure_handling(self):
        """Test requirement 4.1: Handle validation errors for individual repositories gracefully."""
        handler = ValidationHandler()

        # Repository that will fail validation
        failing_repo_data = {
            "name": "test-repo",
            # Missing all required fields except name
        }

        # Should not raise exception, should return None
        result = handler.safe_create_repository(failing_repo_data)

        assert result is None
        assert handler.skipped_count == 1
        assert len(handler.validation_errors) == 1

        # Error should be recorded with context
        error = handler.validation_errors[0]
        assert error["repository"] == "unknown"  # No full_name available
        assert "error" in error
        assert "data" in error

    def test_continue_processing_after_validation_error(self):
        """Test requirement 4.2: Continue processing remaining repositories after error."""
        handler = ValidationHandler()

        repositories_data = [
            # This one will fail
            {"name": "failing-repo"},
            # This one will succeed
            {
                "id": 1,
                "name": "working-repo",
                "full_name": "owner/working-repo",
                "owner": {"login": "owner"},
                "url": "https://api.github.com/repos/owner/working-repo",
                "html_url": "https://github.com/owner/working-repo",
                "clone_url": "https://github.com/owner/working-repo.git",
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
                "pushed_at": "2023-01-02T12:00:00Z",
            },
        ]

        valid_repos = []
        for repo_data in repositories_data:
            repo = handler.safe_create_repository(repo_data)
            if repo:
                valid_repos.append(repo)
                handler.processed_count += 1

        # Should have processed the valid one despite the failure
        assert len(valid_repos) == 1
        assert valid_repos[0].name == "working-repo"
        assert handler.processed_count == 1
        assert handler.skipped_count == 1

    def test_collect_and_report_multiple_validation_errors(self):
        """Test requirement 4.3: Collect and report all errors at the end."""
        handler = ValidationHandler()

        # Multiple repositories with different validation issues
        failing_repositories = [
            {"name": "fail1", "full_name": "owner/fail1"},  # Missing required fields
            {"name": "fail2", "full_name": "owner/fail2"},  # Missing required fields
            {"name": "fail3", "full_name": "owner/fail3"},  # Missing required fields
        ]

        for repo_data in failing_repositories:
            repo = handler.safe_create_repository(repo_data)
            assert repo is None  # All should fail

        # All errors should be collected
        assert handler.skipped_count == 3
        assert len(handler.validation_errors) == 3

        # Each error should have proper context
        for i, error in enumerate(handler.validation_errors):
            assert error["repository"] == f"owner/fail{i+1}"
            assert "error" in error
            assert "data" in error

        # Summary should reflect all errors
        summary = handler.get_summary()
        assert summary.skipped == 3
        assert summary.has_errors() is True
        assert "3 items skipped" in summary.get_error_summary()

    def test_clear_error_message_when_all_repositories_fail(self):
        """Test requirement 4.4: Provide clear error message when all repositories fail validation."""
        handler = ValidationHandler()

        # All repositories will fail
        all_failing_data = [
            {"invalid": "data1"},
            {"invalid": "data2"},
            {"invalid": "data3"},
        ]

        valid_repos = []
        for repo_data in all_failing_data:
            repo = handler.safe_create_repository(repo_data)
            if repo:
                valid_repos.append(repo)
                handler.processed_count += 1

        # No repositories should be processed successfully
        assert len(valid_repos) == 0
        assert handler.processed_count == 0
        assert handler.skipped_count == 3

        # Summary should clearly indicate the failure
        summary = handler.get_summary()
        assert summary.processed == 0
        assert summary.skipped == 3
        assert summary.has_errors() is True

        error_summary = summary.get_error_summary()
        assert error_summary == "3 items skipped due to validation errors"


class TestRepositoryValidationRequirements:
    """Test specific requirements from the requirements document."""

    def test_requirement_2_3_prioritize_functionality_over_strict_validation(
        self, caplog
    ):
        """Test requirement 2.3: Prioritize functionality over strict validation for edge cases."""
        # The original failing case should now work
        with caplog.at_level(logging.WARNING):
            repo = Repository(
                owner="maybe-finance",
                name="maybe.._..maybe",
                full_name="maybe-finance/maybe.._..maybe",
                url="https://api.github.com/repos/maybe-finance/maybe.._..maybe",
                html_url="https://github.com/maybe-finance/maybe.._..maybe",
                clone_url="https://github.com/maybe-finance/maybe.._..maybe.git",
            )

            # Should create successfully (functionality over strict validation)
            assert repo is not None
            assert repo.name == "maybe.._..maybe"

            # Should log warning but not fail
            assert any(
                "consecutive periods" in record.message.lower()
                for record in caplog.records
            )

    def test_requirement_2_1_match_github_actual_naming_constraints(self):
        """Test requirement 2.1: Use validation rules that match GitHub's actual constraints."""
        # Test names that GitHub actually allows based on real API responses
        github_allowed_names = [
            "repo-name",
            "repo_name",
            "repo.name",
            "123repo",
            "repo123",
            "a",  # Single character
            "repo..with..periods",  # Consecutive periods (found in real data)
        ]

        for name in github_allowed_names:
            repo = Repository(
                owner="testowner",
                name=name,
                full_name=f"testowner/{name}",
                url=f"https://api.github.com/repos/testowner/{name}",
                html_url=f"https://github.com/testowner/{name}",
                clone_url=f"https://github.com/testowner/{name}.git",
            )
            assert repo.name == name

    def test_requirement_2_2_permissive_for_unclear_rules(self, caplog):
        """Test requirement 2.2: Be permissive when GitHub's naming rules are unclear."""
        # Edge cases where GitHub's rules are unclear - should be permissive
        unclear_cases = [
            "maybe.._..maybe",  # The original issue case
            "repo...name",  # Multiple consecutive periods
            "test..case..repo",  # Multiple sets of consecutive periods
        ]

        with caplog.at_level(logging.WARNING):
            for name in unclear_cases:
                repo = Repository(
                    owner="testowner",
                    name=name,
                    full_name=f"testowner/{name}",
                    url=f"https://api.github.com/repos/testowner/{name}",
                    html_url=f"https://github.com/testowner/{name}",
                    clone_url=f"https://github.com/testowner/{name}.git",
                )

                # Should be permissive and allow the name
                assert repo.name == name

            # Should log warnings for unclear cases
            assert any(
                "consecutive periods" in record.message.lower()
                for record in caplog.records
            )

    def test_requirement_4_4_comprehensive_error_collection(self):
        """Test requirement 4.4: ValidationHandler comprehensive error collection."""
        handler = ValidationHandler()

        # Test data with various types of validation issues
        test_cases = [
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
                "pushed_at": "2023-01-02T12:00:00Z",
            },
            # Edge case that should work now
            {
                "id": 2,
                "name": "edge..case",
                "full_name": "owner/edge..case",
                "owner": {"login": "owner"},
                "url": "https://api.github.com/repos/owner/edge..case",
                "html_url": "https://github.com/owner/edge..case",
                "clone_url": "https://github.com/owner/edge..case.git",
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
                "pushed_at": "2023-01-02T12:00:00Z",
            },
            # Invalid - missing required fields
            {"name": "invalid1", "full_name": "owner/invalid1"},
            # Invalid - wrong data types
            {"id": "not-number", "name": 123, "full_name": "owner/invalid2"},
        ]

        results = []
        for repo_data in test_cases:
            repo = handler.safe_create_repository(repo_data)
            if repo:
                results.append(repo)
                handler.processed_count += 1

        # Should have 2 successful (including edge case) and 2 failed
        assert len(results) == 2
        assert handler.processed_count == 2
        assert handler.skipped_count == 2
        assert len(handler.validation_errors) == 2

        # Verify error collection includes proper context
        for error in handler.validation_errors:
            assert "repository" in error
            assert "error" in error
            assert "data" in error
            assert len(error["error"]) > 0  # Should have meaningful error message
