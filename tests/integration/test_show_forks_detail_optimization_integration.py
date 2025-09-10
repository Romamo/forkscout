"""Integration tests for show-forks --detail optimization with real repository data."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forkscout.display.repository_display_service import RepositoryDisplayService
from forkscout.github.client import GitHubClient
from forkscout.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
)


class TestShowForksDetailOptimizationIntegration:
    """Integration tests for optimized show-forks --detail command."""

    @pytest.fixture
    def github_client(self):
        """Create a real GitHub client for integration testing."""
        from forkscout.config import GitHubConfig
        config = GitHubConfig(token="ghp_1234567890123456789012345678901234567890")
        return GitHubClient(config)

    @pytest.fixture
    def repository_display_service(self, github_client):
        """Create repository display service with real client."""
        return RepositoryDisplayService(github_client)

    @pytest.fixture
    def base_time(self):
        """Base time for creating test timestamps."""
        return datetime(2024, 1, 15, 12, 0, 0)

    def create_realistic_fork_data(
        self,
        owner: str,
        name: str,
        created_at: datetime,
        pushed_at: datetime,
        stars: int = 0,
        archived: bool = False,
        disabled: bool = False
    ) -> CollectedForkData:
        """Create realistic fork data based on real GitHub repository patterns."""
        metrics = ForkQualificationMetrics(
            id=12345 + hash(f"{owner}/{name}") % 1000000,
            name=name,
            full_name=f"{owner}/{name}",
            owner=owner,
            html_url=f"https://github.com/{owner}/{name}",
            stargazers_count=stars,
            forks_count=max(0, stars // 10),  # Realistic fork count
            watchers_count=stars,  # Often equals stars
            size=1000 + (stars * 10),  # Realistic size in KB
            language="Python",
            topics=["python", "tool"] if stars > 5 else [],
            open_issues_count=max(0, stars // 20),
            created_at=created_at,
            updated_at=max(created_at, pushed_at),
            pushed_at=pushed_at,
            archived=archived,
            disabled=disabled,
            fork=True,
            license_key="mit" if stars > 10 else None,
            license_name="MIT License" if stars > 10 else None,
            description=f"Fork of repository with {stars} stars",
            homepage=f"https://{owner}.github.io/{name}" if stars > 20 else None,
            default_branch="main"
        )

        return CollectedForkData(
            metrics=metrics,
            activity_summary=f"Active fork with {stars} stars",
            exact_commits_ahead=None
        )

    @pytest.mark.asyncio
    async def test_realistic_fork_distribution_optimization(
        self, repository_display_service, base_time
    ):
        """Test optimization with realistic distribution of fork types."""
        # Create realistic fork distribution based on real repository patterns
        # - Most forks have no commits ahead (created and never touched)
        # - Some forks have commits ahead
        # - Few forks are archived/disabled

        forks_data = []

        # 70% of forks have no commits ahead (realistic pattern)
        for i in range(7):
            fork = self.create_realistic_fork_data(
                f"user{i}", f"repo{i}",
                created_at=base_time - timedelta(days=i*10),
                pushed_at=base_time - timedelta(days=i*10),  # Same time = no commits
                stars=i
            )
            forks_data.append(fork)

        # 20% of forks have commits ahead
        for i in range(7, 9):
            fork = self.create_realistic_fork_data(
                f"user{i}", f"repo{i}",
                created_at=base_time - timedelta(days=i*10),
                pushed_at=base_time - timedelta(days=i*10-1),  # 1 day later = has commits
                stars=i*2
            )
            forks_data.append(fork)

        # 10% of forks are archived (should be filtered out)
        archived_fork = self.create_realistic_fork_data(
            "archived_user", "archived_repo",
            created_at=base_time - timedelta(days=100),
            pushed_at=base_time - timedelta(days=99),
            stars=5,
            archived=True
        )
        forks_data.append(archived_fork)

        # Mock the external dependencies
        mock_forks_list_data = [
            {"full_name": fork.metrics.full_name} for fork in forks_data
        ]

        with patch("forklift.github.fork_list_processor.ForkListProcessor") as mock_processor_class, \
             patch("forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine") as mock_engine_class:

            # Setup mocks
            mock_processor = AsyncMock()
            mock_processor.get_all_forks_list_data.return_value = mock_forks_list_data
            mock_processor_class.return_value = mock_processor

            mock_engine = MagicMock()
            mock_engine.collect_fork_data_from_list.return_value = forks_data
            mock_engine_class.return_value = mock_engine

            # Mock GitHub API calls for forks that need them
            repository_display_service.github_client.compare_repositories = AsyncMock()
            repository_display_service.github_client.compare_repositories.return_value = {"ahead_by": 3}

            # Mock console
            repository_display_service.console = MagicMock()

            # Call the method
            result = await repository_display_service.show_fork_data_detailed(
                "owner/repo", max_forks=None, disable_cache=False
            )

            # Verify optimization results
            # Expected: 7 forks skipped (no commits), 2 forks analyzed (has commits), 1 filtered (archived)
            assert result["api_calls_saved"] == 7  # 70% of active forks skipped
            assert result["api_calls_made"] == 2   # Only 2 forks needed API calls
            assert result["forks_skipped"] == 7
            assert result["forks_analyzed"] == 2

            # Verify API efficiency
            total_potential_calls = result["api_calls_made"] + result["api_calls_saved"]
            efficiency = (result["api_calls_saved"] / total_potential_calls) * 100
            assert efficiency >= 70.0  # At least 70% efficiency

            # Verify compare API was called only for forks with commits
            assert repository_display_service.github_client.compare_repositories.call_count == 2

    @pytest.mark.asyncio
    async def test_large_repository_optimization_performance(
        self, repository_display_service, base_time
    ):
        """Test optimization performance with large number of forks."""
        # Simulate a large repository with many forks (like popular open source projects)
        forks_data = []

        # Create 100 forks with realistic distribution
        for i in range(100):
            if i < 80:  # 80% have no commits ahead
                created_time = base_time - timedelta(days=i)
                pushed_time = created_time  # Same time = no commits
                has_commits = False
            else:  # 20% have commits ahead
                created_time = base_time - timedelta(days=i)
                pushed_time = created_time + timedelta(hours=1)  # Has commits
                has_commits = True

            fork = self.create_realistic_fork_data(
                f"user{i}", f"repo{i}",
                created_at=created_time,
                pushed_at=pushed_time,
                stars=max(0, 50 - i)  # Decreasing stars
            )
            forks_data.append(fork)

        mock_forks_list_data = [
            {"full_name": fork.metrics.full_name} for fork in forks_data
        ]

        with patch("forklift.github.fork_list_processor.ForkListProcessor") as mock_processor_class, \
             patch("forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine") as mock_engine_class:

            # Setup mocks
            mock_processor = AsyncMock()
            mock_processor.get_all_forks_list_data.return_value = mock_forks_list_data
            mock_processor_class.return_value = mock_processor

            mock_engine = MagicMock()
            mock_engine.collect_fork_data_from_list.return_value = forks_data
            mock_engine_class.return_value = mock_engine

            # Mock GitHub API calls
            repository_display_service.github_client.compare_repositories = AsyncMock()
            repository_display_service.github_client.compare_repositories.return_value = {"ahead_by": 2}

            # Mock console
            repository_display_service.console = MagicMock()

            # Measure performance
            import time
            start_time = time.time()

            result = await repository_display_service.show_fork_data_detailed(
                "owner/repo", max_forks=None, disable_cache=False
            )

            end_time = time.time()
            execution_time = end_time - start_time

            # Verify significant API call reduction
            assert result["api_calls_saved"] == 80  # 80 forks skipped
            assert result["api_calls_made"] == 20   # 20 forks analyzed

            # Verify high efficiency
            efficiency = (result["api_calls_saved"] / 100) * 100
            assert efficiency == 80.0  # Exactly 80% efficiency

            # Verify performance is reasonable (should be fast since most API calls are skipped)
            assert execution_time < 1.0  # Should complete quickly due to optimization

            # Verify API was called only for necessary forks
            assert repository_display_service.github_client.compare_repositories.call_count == 20

    @pytest.mark.asyncio
    async def test_edge_case_timestamp_handling(
        self, repository_display_service, base_time
    ):
        """Test edge cases in timestamp comparison logic."""
        # Test various timestamp edge cases
        edge_case_forks = []

        # Case 1: Exact same timestamps (microsecond precision)
        exact_same_time = base_time
        fork1 = self.create_realistic_fork_data(
            "user1", "repo1",
            created_at=exact_same_time,
            pushed_at=exact_same_time,
            stars=5
        )
        edge_case_forks.append(fork1)

        # Case 2: Very small time difference (1 second)
        fork2 = self.create_realistic_fork_data(
            "user2", "repo2",
            created_at=base_time,
            pushed_at=base_time + timedelta(seconds=1),
            stars=3
        )
        edge_case_forks.append(fork2)

        # Case 3: Created after pushed (unusual but possible)
        fork3 = self.create_realistic_fork_data(
            "user3", "repo3",
            created_at=base_time + timedelta(minutes=5),
            pushed_at=base_time,
            stars=2
        )
        edge_case_forks.append(fork3)

        mock_forks_list_data = [
            {"full_name": fork.metrics.full_name} for fork in edge_case_forks
        ]

        with patch("forklift.github.fork_list_processor.ForkListProcessor") as mock_processor_class, \
             patch("forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine") as mock_engine_class:

            # Setup mocks
            mock_processor = AsyncMock()
            mock_processor.get_all_forks_list_data.return_value = mock_forks_list_data
            mock_processor_class.return_value = mock_processor

            mock_engine = MagicMock()
            mock_engine.collect_fork_data_from_list.return_value = edge_case_forks
            mock_engine_class.return_value = mock_engine

            # Mock GitHub API calls
            repository_display_service.github_client.compare_repositories = AsyncMock()
            repository_display_service.github_client.compare_repositories.return_value = {"ahead_by": 1}

            # Mock console
            repository_display_service.console = MagicMock()

            # Call the method
            result = await repository_display_service.show_fork_data_detailed(
                "owner/repo", max_forks=None, disable_cache=False
            )

            # Verify edge case handling
            # fork1: created_at == pushed_at -> should be skipped
            # fork2: pushed_at > created_at -> should need API call
            # fork3: created_at > pushed_at -> should be skipped

            assert result["api_calls_saved"] == 2  # fork1 and fork3 skipped
            assert result["api_calls_made"] == 1   # only fork2 needs API call
            assert result["forks_skipped"] == 2
            assert result["forks_analyzed"] == 1

            # Verify API was called only for fork2
            assert repository_display_service.github_client.compare_repositories.call_count == 1

    @pytest.mark.asyncio
    async def test_mixed_fork_states_comprehensive(
        self, repository_display_service, base_time
    ):
        """Test comprehensive scenario with all possible fork states."""
        forks_data = []

        # Active fork with commits ahead
        active_with_commits = self.create_realistic_fork_data(
            "active", "with_commits",
            created_at=base_time - timedelta(days=10),
            pushed_at=base_time - timedelta(days=9),
            stars=15
        )
        forks_data.append(active_with_commits)

        # Active fork with no commits ahead
        active_no_commits = self.create_realistic_fork_data(
            "active", "no_commits",
            created_at=base_time - timedelta(days=5),
            pushed_at=base_time - timedelta(days=5),
            stars=8
        )
        forks_data.append(active_no_commits)

        # Archived fork with commits (should be filtered out)
        archived_with_commits = self.create_realistic_fork_data(
            "archived", "with_commits",
            created_at=base_time - timedelta(days=20),
            pushed_at=base_time - timedelta(days=19),
            stars=12,
            archived=True
        )
        forks_data.append(archived_with_commits)

        # Disabled fork with no commits (should be filtered out)
        disabled_no_commits = self.create_realistic_fork_data(
            "disabled", "no_commits",
            created_at=base_time - timedelta(days=15),
            pushed_at=base_time - timedelta(days=15),
            stars=3,
            disabled=True
        )
        forks_data.append(disabled_no_commits)

        mock_forks_list_data = [
            {"full_name": fork.metrics.full_name} for fork in forks_data
        ]

        with patch("forklift.github.fork_list_processor.ForkListProcessor") as mock_processor_class, \
             patch("forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine") as mock_engine_class:

            # Setup mocks
            mock_processor = AsyncMock()
            mock_processor.get_all_forks_list_data.return_value = mock_forks_list_data
            mock_processor_class.return_value = mock_processor

            mock_engine = MagicMock()
            mock_engine.collect_fork_data_from_list.return_value = forks_data
            mock_engine_class.return_value = mock_engine

            # Mock GitHub API calls
            repository_display_service.github_client.compare_repositories = AsyncMock()
            repository_display_service.github_client.compare_repositories.return_value = {"ahead_by": 4}

            # Mock console
            repository_display_service.console = MagicMock()

            # Call the method
            result = await repository_display_service.show_fork_data_detailed(
                "owner/repo", max_forks=None, disable_cache=False
            )

            # Verify comprehensive filtering and optimization
            # Expected: 2 active forks processed, 2 archived/disabled filtered out
            # Of the 2 active: 1 skipped (no commits), 1 analyzed (has commits)

            assert result["total_forks"] == 4  # All forks in input
            assert result["displayed_forks"] == 2  # Only active forks displayed
            assert result["api_calls_saved"] == 1  # 1 active fork skipped
            assert result["api_calls_made"] == 1   # 1 active fork analyzed
            assert result["forks_skipped"] == 1
            assert result["forks_analyzed"] == 1

            # Verify API was called only for active fork with commits
            assert repository_display_service.github_client.compare_repositories.call_count == 1
            repository_display_service.github_client.compare_repositories.assert_called_with(
                "owner", "repo", "active", "with_commits"
            )

            # Verify final fork data
            collected_forks = result["collected_forks"]
            assert len(collected_forks) == 2  # Only active forks

            # Find forks in results
            active_with_commits_result = next(
                f for f in collected_forks if f.metrics.owner == "active" and f.metrics.name == "with_commits"
            )
            active_no_commits_result = next(
                f for f in collected_forks if f.metrics.owner == "active" and f.metrics.name == "no_commits"
            )

            # Verify exact_commits_ahead values
            assert active_with_commits_result.exact_commits_ahead == 4  # From API call
            assert active_no_commits_result.exact_commits_ahead == 0    # Skipped, set to 0
