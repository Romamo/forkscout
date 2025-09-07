"""Unit tests for repository validation edge cases."""

import logging

import pytest

from forklift.models.github import Repository


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
            assert any("consecutive periods" in record.message.lower() for record in caplog.records)

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
            warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
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
            assert any("consecutive periods" in record.message.lower() for record in caplog.records)

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
            assert any("consecutive periods" in record.message.lower() for record in caplog.records)
