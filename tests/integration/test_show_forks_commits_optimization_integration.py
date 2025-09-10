"""Integration tests for show-forks --show-commits optimization functionality."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console

from forkscout.analysis.fork_data_collection_engine import ForkDataCollectionEngine
from forkscout.display.repository_display_service import RepositoryDisplayService
from forkscout.github.client import GitHubClient
from forkscout.github.fork_list_processor import ForkListProcessor
from forkscout.models.github import RecentCommit, Repository


class TestShowForksCommitsOptimizationIntegration:
    """Integration test suite for show-forks --show-commits optimization."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client with realistic responses."""
        client = AsyncMock(spec=GitHubClient)
        return client

    @pytest.fixture
    def console(self):
        """Create a Rich console for testing."""
        return Console(file=MagicMock(), width=120)

    @pytest.fixture
    def display_service(self, mock_github_client, console):
        """Create a repository display service for testing."""
        return RepositoryDisplayService(mock_github_client, console)

    @pytest.fixture
    def sample_forks_list_data(self):
        """Create sample forks list data from GitHub API."""
        base_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
        
        return [
            # Fork with commits ahead (pushed_at > created_at)
            {
                "id": 123,
                "name": "active-fork",
                "full_name": "user1/active-fork",
                "owner": {"login": "user1"},
                "html_url": "https://github.com/user1/active-fork",
                "stargazers_count": 15,
                "forks_count": 3,
                "watchers_count": 10,
                "size": 2000,
                "language": "Python",
                "topics": ["web", "api"],
                "open_issues_count": 2,
                "created_at": base_time.isoformat(),
                "updated_at": (base_time.replace(month=6)).isoformat(),
                "pushed_at": (base_time.replace(month=6)).isoformat(),
                "archived": False,
                "disabled": False,
                "fork": True,
                "description": "An active fork with changes",
                "homepage": None,
                "default_branch": "main",
                "license": {"key": "mit", "name": "MIT License"},
            },
            # Fork with no commits ahead (created_at >= pushed_at)
            {
                "id": 456,
                "name": "empty-fork",
                "full_name": "user2/empty-fork",
                "owner": {"login": "user2"},
                "html_url": "https://github.com/user2/empty-fork",
                "stargazers_count": 0,
                "forks_count": 0,
                "watchers_count": 0,
                "size": 100,
                "language": None,
                "topics": [],
                "open_issues_count": 0,
                "created_at": (base_time.replace(month=6)).isoformat(),
                "updated_at": (base_time.replace(month=6)).isoformat(),
                "pushed_at": base_time.isoformat(),  # Earlier than created_at
                "archived": False,
                "disabled": False,
                "fork": True,
                "description": None,
                "homepage": None,
                "default_branch": "main",
                "license": None,
            },
        ]

    @pytest.fixture
    def sample_recent_commits(self):
        """Create sample recent commits."""
        return [
            RecentCommit(
                short_sha="abc123d",
                message="Add user authentication system",
            ),
            RecentCommit(
                short_sha="def4567",
                message="Fix security vulnerability in login",
            ),
        ]

    @pytest.mark.asyncio
    async def test_show_fork_data_with_commits_optimization(
        self, display_service, sample_forks_list_data, sample_recent_commits
    ):
        """Test complete show_fork_data workflow with commit optimization."""
        # Setup mocks
        display_service.github_client.get_recent_commits.return_value = sample_recent_commits
        
        # Mock fork list processor and data engine
        with (
            patch('forklift.github.fork_list_processor.ForkListProcessor') as mock_processor_class,
            patch('forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine') as mock_engine_class
        ):
            # Setup processor mock
            mock_processor = AsyncMock()
            mock_processor.get_all_forks_list_data.return_value = sample_forks_list_data
            mock_processor_class.return_value = mock_processor
            
            # Setup data engine mock
            mock_engine = MagicMock()
            mock_engine_class.return_value = mock_engine
            
            # Mock the data engine methods
            real_engine = ForkDataCollectionEngine()
            collected_forks = real_engine.collect_fork_data_from_list(sample_forks_list_data)
            
            mock_engine.collect_fork_data_from_list.return_value = collected_forks
            mock_engine.create_qualification_result.return_value = real_engine.create_qualification_result(
                repository_owner="owner",
                repository_name="repo",
                collected_forks=collected_forks,
                processing_time_seconds=1.0,
                api_calls_made=len(sample_forks_list_data),
                api_calls_saved=0,
            )
            
            # Test with optimization enabled (default)
            result = await display_service.show_fork_data(
                "owner/repo",
                show_commits=3,
                force_all_commits=False
            )
            
            # Verify results
            assert result["total_forks"] == 2
            assert result["displayed_forks"] == 2
            
            # Verify API calls were only made for forks with commits ahead
            # Should be called for: active-fork (1 fork with commits)
            # Should NOT be called for: empty-fork (1 fork without commits)
            assert display_service.github_client.get_recent_commits.call_count == 1
            
            # Verify the correct fork was called
            call_args_list = display_service.github_client.get_recent_commits.call_args_list
            called_forks = {(call[0][0], call[0][1]) for call in call_args_list}
            expected_forks = {("user1", "active-fork")}
            assert called_forks == expected_forks

    @pytest.mark.asyncio
    async def test_show_fork_data_with_force_all_commits(
        self, display_service, sample_forks_list_data, sample_recent_commits
    ):
        """Test show_fork_data with force_all_commits=True bypasses optimization."""
        # Setup mocks
        display_service.github_client.get_recent_commits.return_value = sample_recent_commits
        
        # Mock fork list processor and data engine
        with (
            patch('forklift.github.fork_list_processor.ForkListProcessor') as mock_processor_class,
            patch('forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine') as mock_engine_class
        ):
            # Setup processor mock
            mock_processor = AsyncMock()
            mock_processor.get_all_forks_list_data.return_value = sample_forks_list_data
            mock_processor_class.return_value = mock_processor
            
            # Setup data engine mock
            mock_engine = MagicMock()
            mock_engine_class.return_value = mock_engine
            
            # Mock the data engine methods
            real_engine = ForkDataCollectionEngine()
            collected_forks = real_engine.collect_fork_data_from_list(sample_forks_list_data)
            
            mock_engine.collect_fork_data_from_list.return_value = collected_forks
            mock_engine.create_qualification_result.return_value = real_engine.create_qualification_result(
                repository_owner="owner",
                repository_name="repo",
                collected_forks=collected_forks,
                processing_time_seconds=1.0,
                api_calls_made=len(sample_forks_list_data),
                api_calls_saved=0,
            )
            
            # Test with optimization disabled
            result = await display_service.show_fork_data(
                "owner/repo",
                show_commits=3,
                force_all_commits=True
            )
            
            # Verify results
            assert result["total_forks"] == 2
            assert result["displayed_forks"] == 2
            
            # Verify API calls were made for ALL forks (no optimization)
            assert display_service.github_client.get_recent_commits.call_count == 2
            
            # Verify all forks were called
            call_args_list = display_service.github_client.get_recent_commits.call_args_list
            called_forks = {(call[0][0], call[0][1]) for call in call_args_list}
            expected_forks = {
                ("user1", "active-fork"),
                ("user2", "empty-fork"),
            }
            assert called_forks == expected_forks

    @pytest.mark.asyncio
    async def test_optimization_statistics_and_logging(
        self, display_service, sample_forks_list_data, sample_recent_commits
    ):
        """Test that optimization statistics are properly calculated and logged."""
        # Setup mocks
        display_service.github_client.get_recent_commits.return_value = sample_recent_commits
        
        # Capture console output
        console_output = []
        original_print = display_service.console.print
        display_service.console.print = lambda *args, **kwargs: console_output.append(str(args[0]) if args else "")
        
        try:
            # Mock fork list processor and data engine
            with (
                patch('forklift.github.fork_list_processor.ForkListProcessor') as mock_processor_class,
                patch('forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine') as mock_engine_class
            ):
                # Setup processor mock
                mock_processor = AsyncMock()
                mock_processor.get_all_forks_list_data.return_value = sample_forks_list_data
                mock_processor_class.return_value = mock_processor
                
                # Setup data engine mock
                mock_engine = MagicMock()
                mock_engine_class.return_value = mock_engine
                
                # Mock the data engine methods
                real_engine = ForkDataCollectionEngine()
                collected_forks = real_engine.collect_fork_data_from_list(sample_forks_list_data)
                
                mock_engine.collect_fork_data_from_list.return_value = collected_forks
                mock_engine.create_qualification_result.return_value = real_engine.create_qualification_result(
                    repository_owner="owner",
                    repository_name="repo",
                    collected_forks=collected_forks,
                    processing_time_seconds=1.0,
                    api_calls_made=len(sample_forks_list_data),
                    api_calls_saved=0,
                )
                
                # Test optimization
                await display_service.show_fork_data(
                    "owner/repo",
                    show_commits=2,
                    force_all_commits=False
                )
                
                # Verify statistics are displayed
                output_text = " ".join(console_output)
                
                # Should show that 1 fork was skipped (empty-fork)
                assert "Skipped 1 forks with no commits ahead" in output_text
                assert "saved 1 API calls" in output_text
                assert "50.0% reduction" in output_text
                
        finally:
            # Restore original print function
            display_service.console.print = original_print