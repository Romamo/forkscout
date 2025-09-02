"""Integration tests for commit count configuration in CLI."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from forklift.models.commit_count_config import CommitCountConfig
from forklift.config.settings import ForkliftConfig


class TestCommitCountConfigIntegration:
    """Integration tests for commit count configuration."""

    def test_config_in_forklift_settings(self):
        """Test that CommitCountConfig is properly integrated in ForkliftConfig."""
        config = ForkliftConfig()
        
        # Should have commit_count attribute
        assert hasattr(config, 'commit_count')
        assert isinstance(config.commit_count, CommitCountConfig)
        
        # Should have default values
        assert config.commit_count.max_count_limit == 100
        assert config.commit_count.display_limit == 5

    def test_config_from_dict(self):
        """Test loading commit count config from dictionary."""
        config_dict = {
            "commit_count": {
                "max_count_limit": 50,
                "display_limit": 3,
                "use_unlimited_counting": True,
                "timeout_seconds": 60
            }
        }
        
        config = ForkliftConfig.from_dict(config_dict)
        
        assert config.commit_count.max_count_limit == 0  # Should be 0 due to unlimited flag
        assert config.commit_count.display_limit == 3
        assert config.commit_count.use_unlimited_counting is True
        assert config.commit_count.timeout_seconds == 60

    def test_config_serialization(self):
        """Test that commit count config can be serialized and deserialized."""
        original_config = ForkliftConfig()
        original_config.commit_count.max_count_limit = 200
        original_config.commit_count.display_limit = 10
        
        # Convert to dict and back
        config_dict = original_config.to_dict()
        restored_config = ForkliftConfig.from_dict(config_dict)
        
        assert restored_config.commit_count.max_count_limit == 200
        assert restored_config.commit_count.display_limit == 10

    @patch('forklift.display.repository_display_service.RepositoryDisplayService')
    def test_cli_passes_config_to_display_service(self, mock_display_service):
        """Test that CLI properly passes commit count config to display service."""
        from forklift.cli import _show_forks_summary
        from forklift.config.settings import ForkliftConfig
        from forklift.display.interaction_mode import InteractionMode
        
        # Create test configuration
        config = ForkliftConfig()
        commit_config = CommitCountConfig(max_count_limit=50, display_limit=3)
        
        # Mock the display service constructor
        mock_service_instance = AsyncMock()
        mock_display_service.return_value = mock_service_instance
        
        # Mock the async methods
        mock_service_instance.show_fork_data_detailed = AsyncMock(return_value={
            "total_forks": 10,
            "displayed_forks": 10,
            "api_calls_made": 20
        })
        
        # Mock GitHubClient context manager
        with patch('forklift.cli.GitHubClient') as mock_github_client:
            mock_client_instance = AsyncMock()
            mock_github_client.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_github_client.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Test the function
            import asyncio
            asyncio.run(_show_forks_summary(
                config=config,
                repository_url="owner/repo",
                max_forks=None,
                verbose=False,
                detail=True,
                commit_count_config=commit_config,
                interaction_mode=InteractionMode.FULLY_INTERACTIVE,
                supports_prompts=True
            ))
        
        # Verify display service was created with commit config
        mock_display_service.assert_called_once()
        call_args = mock_display_service.call_args
        
        # Check that commit_count_config was passed
        assert 'commit_count_config' in call_args.kwargs
        passed_config = call_args.kwargs['commit_count_config']
        assert passed_config.max_count_limit == 50
        assert passed_config.display_limit == 3

    def test_commit_data_formatter_with_config(self):
        """Test that CommitDataFormatter uses configuration correctly."""
        from forklift.display.repository_display_service import CommitDataFormatter
        
        # Create test fork data
        class MockForkData:
            def __init__(self, exact_commits_ahead):
                self.exact_commits_ahead = exact_commits_ahead
        
        # Test with limited configuration
        limited_config = CommitCountConfig(max_count_limit=10)
        
        fork_data_5 = MockForkData(5)
        fork_data_15 = MockForkData(15)
        fork_data_0 = MockForkData(0)
        
        # Test normal count
        result = CommitDataFormatter.format_commit_info(fork_data_5, True, limited_config)
        assert result == "[green]+5[/green]"
        
        # Test over limit
        result = CommitDataFormatter.format_commit_info(fork_data_15, True, limited_config)
        assert result == "[green]10+[/green]"
        
        # Test zero count
        result = CommitDataFormatter.format_commit_info(fork_data_0, True, limited_config)
        assert result == ""
        
        # Test with unlimited configuration
        unlimited_config = CommitCountConfig(use_unlimited_counting=True)
        
        result = CommitDataFormatter.format_commit_info(fork_data_15, True, unlimited_config)
        assert result == "[green]+15[/green]"

    def test_repository_display_service_stores_config(self):
        """Test that RepositoryDisplayService properly stores commit count config."""
        from forklift.display.repository_display_service import RepositoryDisplayService
        from forklift.github.client import GitHubClient
        from forklift.config.settings import GitHubConfig
        
        # Create mock GitHub client with valid token format
        github_config = GitHubConfig(token="ghp_1234567890123456789012345678901234567890")
        github_client = GitHubClient(github_config)
        
        # Test with provided config
        commit_config = CommitCountConfig(max_count_limit=75)
        service = RepositoryDisplayService(
            github_client, 
            commit_count_config=commit_config
        )
        
        assert service.commit_count_config.max_count_limit == 75
        
        # Test with default config (None provided)
        service_default = RepositoryDisplayService(github_client)
        
        assert service_default.commit_count_config.max_count_limit == 100  # Default value

    def test_cli_option_parsing(self):
        """Test that CLI options are properly parsed into configuration."""
        # Test from_cli_options with various combinations
        
        # Test default values
        config = CommitCountConfig.from_cli_options()
        assert config.max_count_limit == 100
        assert config.display_limit == 5
        
        # Test custom values
        config = CommitCountConfig.from_cli_options(
            max_commits_count=200,
            commit_display_limit=8
        )
        assert config.max_count_limit == 200
        assert config.display_limit == 8
        
        # Test unlimited flag
        config = CommitCountConfig.from_cli_options(unlimited=True)
        assert config.is_unlimited is True
        assert config.max_count_limit == 0
        
        # Test zero max count (should enable unlimited)
        config = CommitCountConfig.from_cli_options(max_commits_count=0)
        assert config.is_unlimited is True

    def test_config_validation_in_integration(self):
        """Test that configuration validation works in integration context."""
        # Test that invalid configurations are rejected
        with pytest.raises(ValueError):
            CommitCountConfig.from_cli_options(max_commits_count=-1)
        
        with pytest.raises(ValueError):
            CommitCountConfig.from_cli_options(commit_display_limit=-1)
        
        # Test that valid configurations are accepted
        config = CommitCountConfig.from_cli_options(
            max_commits_count=1000,
            commit_display_limit=20
        )
        assert config.max_count_limit == 1000
        assert config.display_limit == 20