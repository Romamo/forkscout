"""Integration tests for error handling and edge cases."""

import pytest
from unittest.mock import AsyncMock, patch

from forklift.analysis.fork_discovery import ForkDiscoveryService
from forklift.config import ForkliftConfig, GitHubConfig
from forklift.github.client import GitHubClient
from forklift.github.exceptions import (
    GitHubEmptyRepositoryError,
    GitHubForkAccessError,
    GitHubPrivateRepositoryError,
    GitHubTimeoutError,
)


class TestErrorHandlingIntegration:
    """Integration tests for comprehensive error handling."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ForkliftConfig(
            github=GitHubConfig(
                token="ghp_1234567890abcdef1234567890abcdef12345678",
                timeout_seconds=5.0
            )
        )

    @pytest.fixture
    def github_client(self, config):
        """Create test GitHub client."""
        return GitHubClient(config.github)

    @pytest.fixture
    def fork_discovery_service(self, github_client):
        """Create test fork discovery service."""
        return ForkDiscoveryService(github_client)

    @pytest.mark.asyncio
    async def test_fork_discovery_with_mixed_access_errors(self, fork_discovery_service):
        """Test fork discovery handles mixed access errors gracefully."""
        from forklift.models.github import Repository
        from datetime import datetime
        
        # Create mock repository objects with proper attributes
        mock_parent_repo = Repository(
            id=1,
            owner="owner",
            name="repo",
            full_name="owner/repo",
            url="https://api.github.com/repos/owner/repo",
            html_url="https://github.com/owner/repo",
            clone_url="https://github.com/owner/repo.git",
            default_branch="main",
            stars=0,
            forks_count=3,
            created_at=datetime(2023, 1, 1),
            updated_at=datetime(2023, 1, 1),
            pushed_at=datetime(2023, 1, 1),
        )
        
        mock_forks = [
            Repository(
                id=2,
                owner="user1",
                name="fork1",
                full_name="user1/fork1",
                url="https://api.github.com/repos/user1/fork1",
                html_url="https://github.com/user1/fork1",
                clone_url="https://github.com/user1/fork1.git",
                default_branch="main",
                stars=0,
                forks_count=0,
                created_at=datetime(2023, 1, 2),
                updated_at=datetime(2023, 1, 3),
                pushed_at=datetime(2023, 1, 3),
            ),
            Repository(
                id=3,
                owner="user2",
                name="fork2",
                full_name="user2/fork2",
                url="https://api.github.com/repos/user2/fork2",
                html_url="https://github.com/user2/fork2",
                clone_url="https://github.com/user2/fork2.git",
                default_branch="main",
                stars=0,
                forks_count=0,
                created_at=datetime(2023, 1, 2),
                updated_at=datetime(2023, 1, 3),
                pushed_at=datetime(2023, 1, 3),
            ),
        ]
        
        # Mock repository data
        with patch.object(fork_discovery_service.github_client, 'get_repository') as mock_get_repo:
            mock_get_repo.return_value = mock_parent_repo
            
            with patch.object(fork_discovery_service.github_client, 'get_all_repository_forks') as mock_get_forks:
                mock_get_forks.return_value = mock_forks
                
                # Mock different error types for different forks
                def mock_comparison_side_effect(*args, **kwargs):
                    return {"ahead_by": 0, "behind_by": 0, "total_commits": 0}
                
                with patch.object(fork_discovery_service.github_client, 'get_commits_ahead_behind_safe') as mock_comparison:
                    mock_comparison.side_effect = mock_comparison_side_effect
                    
                    # Should handle all errors gracefully and continue processing
                    forks = await fork_discovery_service._discover_forks_legacy(
                        "owner", "repo", mock_parent_repo, disable_cache=False
                    )
                    
                    # Should return empty list since all forks had no commits ahead
                    assert isinstance(forks, list)

    @pytest.mark.asyncio
    async def test_error_message_consistency(self, github_client):
        """Test that error messages are consistent across different components."""
        # Test various error scenarios
        error_scenarios = [
            (GitHubPrivateRepositoryError("Private", "owner/repo"), "private"),
            (GitHubEmptyRepositoryError("Empty", "owner/repo"), "empty"),
            (GitHubForkAccessError("Access denied", "owner/fork", "private"), "private"),
            (GitHubTimeoutError("Timeout", "test_op", 30.0), "timed out"),
        ]

        for error, expected_keyword in error_scenarios:
            message = github_client.get_user_friendly_error_message(error)
            assert expected_keyword in message.lower()
            assert len(message) > 10  # Should be descriptive
            assert not message.startswith("Traceback")  # Should be user-friendly