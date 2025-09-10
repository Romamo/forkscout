"""Integration tests for enhanced commit operation error handling."""

import pytest
from unittest.mock import AsyncMock, Mock

from forkscout.display.repository_display_service import RepositoryDisplayService
from forkscout.github.client import GitHubClient
from forkscout.github.exceptions import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubCommitComparisonError,
    GitHubDivergentHistoryError,
    GitHubPrivateRepositoryError,
)
from forkscout.config import GitHubConfig
from forkscout.models.fork_qualification import CollectedForkData, ForkQualificationMetrics


def create_mock_repo_response(owner: str, name: str) -> dict:
    """Create a mock repository response with all required fields."""
    return {
        "name": name,
        "owner": {"login": owner},
        "full_name": f"{owner}/{name}",
        "default_branch": "main",
        "html_url": f"https://github.com/{owner}/{name}",
        "clone_url": f"https://github.com/{owner}/{name}.git",
        "url": f"https://api.github.com/repos/{owner}/{name}"
    }


class TestEnhancedCommitErrorHandlingIntegration:
    """Integration tests for enhanced commit error handling."""

    @pytest.fixture
    def github_client(self):
        """Create GitHub client for testing."""
        config = GitHubConfig(token="ghp_1234567890123456789012345678901234567890")
        client = GitHubClient(config)
        client._client = AsyncMock()
        return client

    @pytest.fixture
    def repository_display_service(self, github_client):
        """Create repository display service for testing."""
        return RepositoryDisplayService(github_client)

    def create_mock_fork_data(self, owner: str, name: str) -> CollectedForkData:
        """Create mock fork data for testing."""
        from datetime import datetime
        metrics = ForkQualificationMetrics(
            id=12345,
            owner=owner,
            name=name,
            full_name=f"{owner}/{name}",
            html_url=f"https://github.com/{owner}/{name}",
            stargazers_count=10,
            forks_count=5,
            pushed_at=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
            created_at=datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
            updated_at=datetime.fromisoformat("2024-01-15T10:30:00+00:00"),
        )
        return CollectedForkData(metrics=metrics)

    @pytest.mark.asyncio
    async def test_batch_processing_handles_private_repositories(
        self, repository_display_service, github_client
    ):
        """Test that batch processing handles private repositories gracefully."""
        # Create test fork data
        fork_data_list = [
            self.create_mock_fork_data("public_fork", "repo"),
            self.create_mock_fork_data("private_fork", "repo"),
        ]

        # Mock GitHub client responses
        def mock_request(method, url, **kwargs):
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            
            if "repos/parent/repo" in url:
                # Parent repo succeeds
                mock_response.status_code = 200
                mock_response.json.return_value = create_mock_repo_response("parent", "repo")
            elif "repos/public_fork/repo" in url:
                # Public fork succeeds
                mock_response.status_code = 200
                mock_response.json.return_value = create_mock_repo_response("public_fork", "repo")
            elif "repos/private_fork/repo" in url:
                # Private fork returns 404
                raise GitHubAPIError("Not found", status_code=404)
            elif "compare" in url and "public_fork" in url:
                # Comparison with public fork succeeds
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "ahead_by": 3,
                    "behind_by": 0,
                    "commits": []
                }
            else:
                raise GitHubAPIError("Not found", status_code=404)
            
            return mock_response

        github_client._client.request = AsyncMock(side_effect=mock_request)

        # Execute batch processing
        successful_forks, api_calls_saved = await repository_display_service._get_exact_commit_counts_batch(
            fork_data_list, "parent", "repo"
        )

        # Verify results
        assert successful_forks == 1  # Only public fork should succeed
        assert fork_data_list[0].exact_commits_ahead == 3  # Public fork has 3 commits
        assert fork_data_list[1].exact_commits_ahead == "Unknown"  # Private fork is unknown

    @pytest.mark.asyncio
    async def test_batch_processing_handles_divergent_histories(
        self, repository_display_service, github_client
    ):
        """Test that batch processing handles divergent histories gracefully."""
        # Create test fork data
        fork_data_list = [
            self.create_mock_fork_data("normal_fork", "repo"),
            self.create_mock_fork_data("divergent_fork", "repo"),
        ]

        # Mock GitHub client responses
        def mock_request(method, url, **kwargs):
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            
            if "repos/parent/repo" in url:
                # Parent repo succeeds
                mock_response.status_code = 200
                mock_response.json.return_value = create_mock_repo_response("parent", "repo")
            elif "repos/normal_fork/repo" in url or "repos/divergent_fork/repo" in url:
                # Both forks succeed
                owner = "normal_fork" if "normal_fork" in url else "divergent_fork"
                mock_response.status_code = 200
                mock_response.json.return_value = create_mock_repo_response(owner, "repo")
            elif "compare" in url and "normal_fork" in url:
                # Normal fork comparison succeeds
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "ahead_by": 2,
                    "behind_by": 0,
                    "commits": []
                }
            elif "compare" in url and "divergent_fork" in url:
                # Divergent fork comparison fails with 422
                raise GitHubAPIError("Unprocessable Entity", status_code=422)
            else:
                raise GitHubAPIError("Not found", status_code=404)
            
            return mock_response

        github_client._client.request = AsyncMock(side_effect=mock_request)

        # Execute batch processing
        successful_forks, api_calls_saved = await repository_display_service._get_exact_commit_counts_batch(
            fork_data_list, "parent", "repo"
        )

        # Verify results
        assert successful_forks == 1  # Only normal fork should succeed
        assert fork_data_list[0].exact_commits_ahead == 2  # Normal fork has 2 commits
        assert fork_data_list[1].exact_commits_ahead == "Unknown"  # Divergent fork is unknown

    @pytest.mark.asyncio
    async def test_individual_fallback_handles_errors_gracefully(
        self, repository_display_service, github_client
    ):
        """Test that individual fallback processing handles errors gracefully."""
        # Create test fork data
        fork_data_list = [
            self.create_mock_fork_data("accessible_fork", "repo"),
            self.create_mock_fork_data("inaccessible_fork", "repo"),
        ]

        # Mock batch processing to fail, forcing individual fallback
        github_client.get_commits_ahead_batch_counts = AsyncMock(
            side_effect=Exception("Batch processing failed")
        )

        # Mock individual comparison calls
        async def mock_compare_repositories(base_owner, base_repo, fork_owner, fork_repo):
            if fork_owner == "accessible_fork":
                return {"ahead_by": 4}
            elif fork_owner == "inaccessible_fork":
                raise GitHubPrivateRepositoryError(
                    f"Repository '{fork_owner}/{fork_repo}' is private",
                    repository=f"{fork_owner}/{fork_repo}"
                )
            else:
                raise GitHubAPIError("Not found", status_code=404)

        github_client.compare_repositories = AsyncMock(side_effect=mock_compare_repositories)

        # Execute batch processing (which will fall back to individual calls)
        successful_forks, api_calls_saved = await repository_display_service._get_exact_commit_counts_batch(
            fork_data_list, "parent", "repo"
        )

        # Verify results
        assert successful_forks == 1  # Only accessible fork should succeed
        assert fork_data_list[0].exact_commits_ahead == 4  # Accessible fork has 4 commits
        assert fork_data_list[1].exact_commits_ahead == "Unknown"  # Inaccessible fork is unknown

    @pytest.mark.asyncio
    async def test_critical_errors_stop_processing(
        self, repository_display_service, github_client
    ):
        """Test that critical errors (like authentication failures) stop processing."""
        # Create test fork data
        fork_data_list = [
            self.create_mock_fork_data("fork1", "repo"),
            self.create_mock_fork_data("fork2", "repo"),
        ]

        # Mock batch processing to fail, forcing individual fallback
        github_client.get_commits_ahead_batch_counts = AsyncMock(
            side_effect=Exception("Batch processing failed")
        )

        # Mock individual comparison to raise authentication error on first fork
        async def mock_compare_repositories(base_owner, base_repo, fork_owner, fork_repo):
            from forkscout.github.exceptions import GitHubAuthenticationError
            raise GitHubAuthenticationError("Authentication failed", status_code=401)

        github_client.compare_repositories = AsyncMock(side_effect=mock_compare_repositories)

        # Execute batch processing - should raise authentication error
        with pytest.raises(GitHubAuthenticationError):
            await repository_display_service._get_exact_commit_counts_batch(
                fork_data_list, "parent", "repo"
            )

    @pytest.mark.asyncio
    async def test_error_logging_includes_user_friendly_messages(
        self, repository_display_service, github_client, caplog
    ):
        """Test that error logging includes user-friendly messages."""
        import logging
        
        # Set up logging
        caplog.set_level(logging.DEBUG)
        
        # Create test fork data
        fork_data_list = [
            self.create_mock_fork_data("divergent_fork", "repo"),
        ]

        # Mock batch processing to fail, forcing individual fallback
        github_client.get_commits_ahead_batch_counts = AsyncMock(
            side_effect=Exception("Batch processing failed")
        )

        # Mock individual comparison to raise divergent history error
        async def mock_compare_repositories(base_owner, base_repo, fork_owner, fork_repo):
            raise GitHubDivergentHistoryError(
                "Divergent history", f"{base_owner}/{base_repo}", f"{fork_owner}/{fork_repo}"
            )

        github_client.compare_repositories = AsyncMock(side_effect=mock_compare_repositories)

        # Execute batch processing
        successful_forks, api_calls_saved = await repository_display_service._get_exact_commit_counts_batch(
            fork_data_list, "parent", "repo"
        )

        # Verify that user-friendly error message appears in logs
        assert any("divergent histories" in record.message for record in caplog.records)
        assert fork_data_list[0].exact_commits_ahead == "Unknown"

    @pytest.mark.asyncio
    async def test_mixed_error_scenarios_in_batch(
        self, repository_display_service, github_client
    ):
        """Test batch processing with multiple different error types."""
        # Create test fork data with various scenarios
        fork_data_list = [
            self.create_mock_fork_data("success_fork", "repo"),
            self.create_mock_fork_data("private_fork", "repo"),
            self.create_mock_fork_data("divergent_fork", "repo"),
            self.create_mock_fork_data("empty_fork", "repo"),
        ]

        # Mock GitHub client responses for various scenarios
        def mock_request(method, url, **kwargs):
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            
            if "repos/parent/repo" in url:
                # Parent repo succeeds
                mock_response.status_code = 200
                mock_response.json.return_value = create_mock_repo_response("parent", "repo")
            elif "repos/success_fork/repo" in url:
                # Success fork succeeds
                mock_response.status_code = 200
                mock_response.json.return_value = create_mock_repo_response("success_fork", "repo")
            elif "repos/private_fork/repo" in url:
                # Private fork returns 404
                raise GitHubAPIError("Not found", status_code=404)
            elif "repos/divergent_fork/repo" in url:
                # Divergent fork succeeds (error happens in comparison)
                mock_response.status_code = 200
                mock_response.json.return_value = create_mock_repo_response("divergent_fork", "repo")
            elif "repos/empty_fork/repo" in url:
                # Empty fork succeeds (error happens in comparison)
                mock_response.status_code = 200
                mock_response.json.return_value = create_mock_repo_response("empty_fork", "repo")
            elif "compare" in url and "success_fork" in url:
                # Success fork comparison succeeds
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "ahead_by": 7,
                    "behind_by": 0,
                    "commits": []
                }
            elif "compare" in url and "divergent_fork" in url:
                # Divergent fork comparison fails with 422
                raise GitHubAPIError("Unprocessable Entity", status_code=422)
            elif "compare" in url and "empty_fork" in url:
                # Empty fork comparison fails with 409
                raise GitHubAPIError("Conflict", status_code=409)
            else:
                raise GitHubAPIError("Not found", status_code=404)
            
            return mock_response

        github_client._client.request = AsyncMock(side_effect=mock_request)

        # Execute batch processing
        successful_forks, api_calls_saved = await repository_display_service._get_exact_commit_counts_batch(
            fork_data_list, "parent", "repo"
        )

        # Verify results
        assert successful_forks == 1  # Only success_fork should succeed
        assert fork_data_list[0].exact_commits_ahead == 7  # Success fork has 7 commits
        assert fork_data_list[1].exact_commits_ahead == "Unknown"  # Private fork is unknown
        assert fork_data_list[2].exact_commits_ahead == "Unknown"  # Divergent fork is unknown
        assert fork_data_list[3].exact_commits_ahead == "Unknown"  # Empty fork is unknown