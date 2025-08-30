"""Performance tests for show-forks --detail functionality."""

import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console

from forklift.config.settings import ForkliftConfig, GitHubConfig
from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.github.client import GitHubClient
from forklift.github.fork_list_processor import ForkListProcessor


class TestShowForksDetailPerformance:
    """Performance test suite for show-forks --detail functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        config = ForkliftConfig()
        config.github = GitHubConfig(token="ghp_1234567890123456789012345678901234567890")
        return config

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

    def create_large_forks_dataset(self, fork_count: int):
        """Create a large dataset of forks for performance testing."""
        base_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
        forks_data = []
        
        for i in range(fork_count):
            # Mix of forks with and without commits ahead
            has_commits_ahead = i % 3 != 0  # 2/3 have commits ahead, 1/3 don't
            
            if has_commits_ahead:
                created_at = base_time
                pushed_at = base_time.replace(month=6)  # Later than created_at
            else:
                created_at = base_time.replace(month=6)
                pushed_at = base_time  # Earlier than created_at
            
            fork_data = {
                "id": 1000 + i,
                "name": f"fork-{i}",
                "full_name": f"user{i}/fork-{i}",
                "owner": {"login": f"user{i}"},
                "html_url": f"https://github.com/user{i}/fork-{i}",
                "stargazers_count": i % 100,  # Vary stars
                "forks_count": i % 20,
                "watchers_count": i % 50,
                "size": 1000 + i * 10,
                "language": ["Python", "JavaScript", "Go", "Rust"][i % 4],
                "topics": [f"topic-{i % 5}"],
                "open_issues_count": i % 10,
                "created_at": created_at.isoformat(),
                "updated_at": pushed_at.isoformat(),
                "pushed_at": pushed_at.isoformat(),
                "archived": i % 50 == 0,  # 2% archived
                "disabled": False,
                "fork": True,
                "description": f"Fork {i} description",
                "homepage": f"https://fork{i}.example.com" if i % 10 == 0 else None,
                "default_branch": "main",
                "license": {"key": "mit", "name": "MIT License"} if i % 5 == 0 else None,
            }
            forks_data.append(fork_data)
        
        return forks_data

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_show_forks_detail_performance_with_10_forks(
        self, display_service, mock_config
    ):
        """Test performance with 10 forks in detailed mode."""
        fork_count = 10
        forks_data = self.create_large_forks_dataset(fork_count)
        
        # Setup mocks
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = forks_data

        # Mock compare API with realistic delay
        api_call_times = []
        
        async def mock_compare_repositories(base_owner, base_repo, fork_owner, fork_repo):
            start_time = time.time()
            await asyncio.sleep(0.005)  # 5ms simulated API delay
            end_time = time.time()
            api_call_times.append(end_time - start_time)
            return {"ahead_by": 3, "behind_by": 1}

        display_service.github_client.compare_repositories = mock_compare_repositories

        # Measure execution time
        start_time = time.time()
        
        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False
            )
        
        end_time = time.time()
        total_time = end_time - start_time

        # Performance assertions
        assert total_time < 2.0  # Should complete within 2 seconds
        assert result["total_forks"] == fork_count
        
        # Verify API optimization (some forks should be skipped)
        expected_api_calls = len([f for f in forks_data if not f["archived"] and f["pushed_at"] > f["created_at"]])
        assert result["api_calls_made"] == expected_api_calls
        assert result["api_calls_saved"] > 0  # Some forks should be skipped

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_show_forks_detail_performance_with_50_forks(
        self, display_service, mock_config
    ):
        """Test performance with 50 forks in detailed mode."""
        fork_count = 50
        forks_data = self.create_large_forks_dataset(fork_count)
        
        # Setup mocks
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = forks_data

        # Mock compare API with realistic delay
        api_call_count = 0
        
        async def mock_compare_repositories(base_owner, base_repo, fork_owner, fork_repo):
            nonlocal api_call_count
            api_call_count += 1
            await asyncio.sleep(0.01)  # 10ms simulated API delay
            return {"ahead_by": api_call_count % 10, "behind_by": 1}

        display_service.github_client.compare_repositories = mock_compare_repositories

        # Measure execution time
        start_time = time.time()
        
        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False
            )
        
        end_time = time.time()
        total_time = end_time - start_time

        # Performance assertions
        assert total_time < 10.0  # Should complete within 10 seconds
        assert result["total_forks"] == fork_count
        
        # Verify significant API call savings
        assert result["api_calls_saved"] > 10  # Should save significant API calls
        assert result["api_calls_made"] < fork_count  # Should be less than total forks

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_show_forks_detail_performance_comparison_with_without_optimization(
        self, display_service, mock_config
    ):
        """Compare performance with and without API call optimization."""
        fork_count = 30
        forks_data = self.create_large_forks_dataset(fork_count)
        
        # Setup mocks
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = forks_data

        api_call_count = 0
        
        async def mock_compare_repositories(base_owner, base_repo, fork_owner, fork_repo):
            nonlocal api_call_count
            api_call_count += 1
            await asyncio.sleep(0.008)  # 8ms simulated API delay
            return {"ahead_by": 2, "behind_by": 0}

        display_service.github_client.compare_repositories = mock_compare_repositories

        # Test with optimization (default behavior)
        api_call_count = 0
        start_time = time.time()
        
        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result_optimized = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False  # Optimization enabled
            )
        
        optimized_time = time.time() - start_time
        optimized_api_calls = api_call_count

        # Test without optimization (force all commits)
        api_call_count = 0
        start_time = time.time()
        
        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result_unoptimized = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=True  # Optimization disabled
            )
        
        unoptimized_time = time.time() - start_time
        unoptimized_api_calls = api_call_count

        # Performance comparison assertions
        assert optimized_time < unoptimized_time  # Optimized should be faster
        assert optimized_api_calls < unoptimized_api_calls  # Fewer API calls
        
        # Verify optimization effectiveness
        api_call_savings = unoptimized_api_calls - optimized_api_calls
        time_savings = unoptimized_time - optimized_time
        
        assert api_call_savings > 5  # Should save significant API calls
        assert time_savings > 0.1  # Should save noticeable time
        
        # Both should process same number of forks
        assert result_optimized["total_forks"] == result_unoptimized["total_forks"]

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_show_forks_detail_performance_with_api_errors(
        self, display_service, mock_config
    ):
        """Test performance impact when some API calls fail."""
        fork_count = 25
        forks_data = self.create_large_forks_dataset(fork_count)
        
        # Setup mocks
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = forks_data

        api_call_count = 0
        failed_calls = 0
        
        async def mock_compare_repositories(base_owner, base_repo, fork_owner, fork_repo):
            nonlocal api_call_count, failed_calls
            api_call_count += 1
            
            # Simulate 20% failure rate
            if api_call_count % 5 == 0:
                failed_calls += 1
                await asyncio.sleep(0.02)  # Failed calls take longer
                raise Exception("GitHub API rate limit exceeded")
            else:
                await asyncio.sleep(0.005)  # Successful calls
                return {"ahead_by": 3, "behind_by": 1}

        display_service.github_client.compare_repositories = mock_compare_repositories

        # Measure execution time
        start_time = time.time()
        
        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False
            )
        
        end_time = time.time()
        total_time = end_time - start_time

        # Performance assertions with error handling
        assert total_time < 5.0  # Should still complete reasonably fast
        assert result["total_forks"] == fork_count
        assert failed_calls > 0  # Some calls should have failed
        
        # Verify that processing continued despite errors
        assert len(result["collected_forks"]) > 0
        
        # Check that some forks have "Unknown" status due to API errors
        unknown_count = sum(1 for fork in result["collected_forks"] 
                          if fork.exact_commits_ahead == "Unknown")
        assert unknown_count > 0

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_show_forks_detail_memory_usage_with_large_dataset(
        self, display_service, mock_config
    ):
        """Test memory usage with large datasets."""
        import psutil
        import os
        
        fork_count = 100
        forks_data = self.create_large_forks_dataset(fork_count)
        
        # Setup mocks
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = forks_data

        async def mock_compare_repositories(base_owner, base_repo, fork_owner, fork_repo):
            await asyncio.sleep(0.001)  # Minimal delay
            return {"ahead_by": 1, "behind_by": 0}

        display_service.github_client.compare_repositories = mock_compare_repositories

        # Measure memory usage
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False
            )

        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = memory_after - memory_before

        # Memory usage assertions
        assert memory_increase < 50  # Should not use more than 50MB additional memory
        assert result["total_forks"] == fork_count
        
        # Verify that large datasets are handled efficiently
        assert len(result["collected_forks"]) <= fork_count

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_show_forks_detail_scalability_with_different_fork_sizes(
        self, display_service, mock_config
    ):
        """Test scalability with different numbers of forks."""
        fork_sizes = [5, 15, 30, 60]
        execution_times = []
        api_call_counts = []
        
        for fork_count in fork_sizes:
            forks_data = self.create_large_forks_dataset(fork_count)
            
            # Setup mocks
            fork_processor = AsyncMock(spec=ForkListProcessor)
            fork_processor.get_all_forks_list_data.return_value = forks_data

            api_calls_made = 0
            
            async def mock_compare_repositories(base_owner, base_repo, fork_owner, fork_repo):
                nonlocal api_calls_made
                api_calls_made += 1
                await asyncio.sleep(0.003)  # 3ms delay
                return {"ahead_by": 2, "behind_by": 0}

            display_service.github_client.compare_repositories = mock_compare_repositories

            # Measure execution time
            start_time = time.time()
            
            with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
                result = await display_service.show_fork_data_detailed(
                    "owner/test-repo",
                    max_forks=None,
                    disable_cache=False,
                    show_commits=0,
                    force_all_commits=False
                )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            execution_times.append(execution_time)
            api_call_counts.append(api_calls_made)
            
            # Verify results for this size
            assert result["total_forks"] == fork_count
            assert result["api_calls_made"] == api_calls_made

        # Scalability assertions
        # Execution time should scale roughly linearly with API calls needed
        for i in range(1, len(execution_times)):
            time_ratio = execution_times[i] / execution_times[i-1]
            api_ratio = api_call_counts[i] / api_call_counts[i-1] if api_call_counts[i-1] > 0 else 1
            
            # Time scaling should be reasonable (not exponential)
            assert time_ratio < api_ratio * 2  # Allow some overhead but not excessive

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_show_forks_detail_concurrent_processing_efficiency(
        self, display_service, mock_config
    ):
        """Test efficiency of concurrent API call processing."""
        fork_count = 20
        forks_data = self.create_large_forks_dataset(fork_count)
        
        # Setup mocks
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = forks_data

        # Track concurrent API calls
        active_calls = 0
        max_concurrent_calls = 0
        call_times = []
        
        async def mock_compare_repositories(base_owner, base_repo, fork_owner, fork_repo):
            nonlocal active_calls, max_concurrent_calls
            
            active_calls += 1
            max_concurrent_calls = max(max_concurrent_calls, active_calls)
            
            start_time = time.time()
            await asyncio.sleep(0.05)  # 50ms delay to test concurrency
            end_time = time.time()
            
            call_times.append(end_time - start_time)
            active_calls -= 1
            
            return {"ahead_by": 1, "behind_by": 0}

        display_service.github_client.compare_repositories = mock_compare_repositories

        # Measure total execution time
        start_time = time.time()
        
        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=True  # Force all calls to test concurrency
            )
        
        end_time = time.time()
        total_time = end_time - start_time

        # Concurrency efficiency assertions
        expected_sequential_time = len(call_times) * 0.05  # If all calls were sequential
        
        # Total time should be significantly less than sequential execution
        # (allowing for some overhead and the fact that not all forks may need API calls)
        efficiency_ratio = total_time / expected_sequential_time if expected_sequential_time > 0 else 1
        assert efficiency_ratio < 0.8  # Should be at least 20% more efficient than sequential
        
        # Verify that some level of concurrency was achieved
        # (This depends on the implementation - may be sequential in current version)
        assert result["total_forks"] == fork_count