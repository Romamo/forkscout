"""Performance tests for show-commits functionality with large numbers of forks."""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from forklift.config.settings import ForkliftConfig
from forklift.models.github import Repository, Commit, User
from forklift.models.fork_qualification import QualifiedForksResult, CollectedForkData, ForkQualificationMetrics
from forklift.display.repository_display_service import RepositoryDisplayService


class TestShowCommitsPerformance:
    """Performance tests for show-commits functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock(spec=ForkliftConfig)
        config.github.token = "test_token"
        config.github.rate_limit_delay = 0.1  # Minimal delay for testing
        return config

    @pytest.fixture
    def sample_repository(self):
        """Create a sample repository for testing."""
        return Repository(
            id=12345,
            name="large-repo",
            full_name="testowner/large-repo",
            owner="testowner",
            description="A repository with many forks",
            html_url="https://github.com/testowner/large-repo",
            clone_url="https://github.com/testowner/large-repo.git",
            ssh_url="git@github.com:testowner/large-repo.git",
            url="https://api.github.com/repos/testowner/large-repo",
            stargazers_count=1000,
            forks_count=500,
            watchers_count=1000,
            open_issues_count=50,
            size=10240,
            default_branch="main",
            language="Python",
            topics=["python", "performance"],
            license={"key": "mit", "name": "MIT License"},
            private=False,
            fork=False,
            archived=False,
            disabled=False,
            created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            pushed_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
        )

    def create_large_fork_dataset(self, count: int) -> list[CollectedForkData]:
        """Create a large dataset of forks for performance testing."""
        return [
            CollectedForkData(
                name=f"performance-fork-{i}",
                owner=f"perfowner{i}",
                full_name=f"perfowner{i}/performance-fork-{i}",
                html_url=f"https://github.com/perfowner{i}/performance-fork-{i}",
                clone_url=f"https://github.com/perfowner{i}/performance-fork-{i}.git",
                qualification_metrics=ForkQualificationMetrics(
                    stargazers_count=i % 100,
                    forks_count=i % 10,
                    size=1024 * (i % 50 + 1),
                    language="Python" if i % 3 == 0 else "JavaScript" if i % 3 == 1 else "Go",
                    created_at=datetime(2023, 1, (i % 28) + 1, tzinfo=timezone.utc),
                    updated_at=datetime(2024, 1, (i % 28) + 1, tzinfo=timezone.utc),
                    pushed_at=datetime(2024, 1, (i % 28) + 2, tzinfo=timezone.utc),
                    open_issues_count=i % 20,
                    topics=[f"topic{i % 5}", f"category{i % 3}"],
                    watchers_count=i % 100,
                    archived=False,
                    disabled=False,
                    commits_ahead_status="Has commits",
                    can_skip_analysis=False
                )
            )
            for i in range(count)
        ]

    def create_sample_commits(self, count: int, fork_index: int) -> list[Commit]:
        """Create sample commits for a fork."""
        return [
            Commit(
                sha=f"perf{fork_index:02d}{i:034d}",  # Pad to 40 chars
                message=f"Performance test commit {i} for fork {fork_index}",
                author=User(
                    login=f"perfauthor{fork_index}",
                    name=f"Perf Author {fork_index}",
                    email=f"perfauthor{fork_index}@example.com",
                    html_url=f"https://github.com/perfauthor{fork_index}",
                    id=fork_index * 1000 + i
                ),
                date=datetime(2024, 1, (i % 28) + 1, tzinfo=timezone.utc),
                files_changed=[f"perf{i}.py"],
                additions=10 * ((i % 20) + 1),
                deletions=5 * ((i % 15) + 1)
            )
            for i in range(count)
        ]

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_show_forks_performance_with_10_forks_3_commits(self, mock_config, sample_repository):
        """Test performance with 10 forks showing 3 commits each."""
        fork_count = 10
        commits_per_fork = 3
        
        # Create test data
        forks_data = self.create_large_fork_dataset(fork_count)
        
        # Setup mocks
        mock_client = AsyncMock()
        
        def mock_get_recent_commits(owner, repo, branch=None, limit=None):
            # Extract fork index from owner name
            fork_index = int(owner.replace("perfowner", ""))
            return self.create_sample_commits(limit or commits_per_fork, fork_index)
        
        mock_client.get_recent_commits.side_effect = mock_get_recent_commits
        
        # Create display service
        display_service = RepositoryDisplayService(mock_client)
        
        # Measure performance
        start_time = time.time()
        
        with patch.object(display_service, '_get_fork_qualification_data') as mock_get_qualification:
            mock_get_qualification.return_value = ForkQualificationResult(
                total_forks=fork_count,
                collected_forks=forks_data,
                excluded_archived_disabled=0,
                excluded_no_commits_ahead=0,
                included_for_analysis=fork_count
            )
            
            result = await display_service.show_fork_data(
                repo_url="testowner/large-repo",
                max_forks=fork_count,
                show_commits=commits_per_fork
            )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Performance assertions
        assert execution_time < 5.0, f"Performance test failed: took {execution_time:.2f}s, expected < 5.0s"
        assert result["total_forks"] == fork_count
        assert result["displayed_forks"] == fork_count
        
        # Verify API calls were made for commits
        assert mock_client.get_recent_commits.call_count == fork_count
        
        print(f"Performance test (10 forks, 3 commits): {execution_time:.2f}s")

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_show_forks_performance_with_50_forks_5_commits(self, mock_config, sample_repository):
        """Test performance with 50 forks showing 5 commits each."""
        fork_count = 50
        commits_per_fork = 5
        
        # Create test data
        forks_data = self.create_large_fork_dataset(fork_count)
        
        # Setup mocks
        mock_client = AsyncMock()
        
        def mock_get_recent_commits(owner, repo, branch=None, limit=None):
            fork_index = int(owner.replace("perfowner", ""))
            return self.create_sample_commits(limit or commits_per_fork, fork_index)
        
        mock_client.get_recent_commits.side_effect = mock_get_recent_commits
        
        # Create display service
        display_service = RepositoryDisplayService(mock_client)
        
        # Measure performance
        start_time = time.time()
        
        with patch.object(display_service, '_get_fork_qualification_data') as mock_get_qualification:
            mock_get_qualification.return_value = ForkQualificationResult(
                total_forks=fork_count,
                collected_forks=forks_data,
                excluded_archived_disabled=0,
                excluded_no_commits_ahead=0,
                included_for_analysis=fork_count
            )
            
            result = await display_service.show_fork_data(
                repo_url="testowner/large-repo",
                max_forks=fork_count,
                show_commits=commits_per_fork
            )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Performance assertions - more lenient for larger dataset
        assert execution_time < 15.0, f"Performance test failed: took {execution_time:.2f}s, expected < 15.0s"
        assert result["total_forks"] == fork_count
        assert result["displayed_forks"] == fork_count
        
        # Verify API calls were made for commits
        assert mock_client.get_recent_commits.call_count == fork_count
        
        print(f"Performance test (50 forks, 5 commits): {execution_time:.2f}s")

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_show_forks_performance_comparison_with_without_commits(self, mock_config, sample_repository):
        """Compare performance with and without commit fetching."""
        fork_count = 25
        commits_per_fork = 3
        
        # Create test data
        forks_data = self.create_large_fork_dataset(fork_count)
        
        # Setup mocks
        mock_client = AsyncMock()
        
        def mock_get_recent_commits(owner, repo, branch=None, limit=None):
            fork_index = int(owner.replace("perfowner", ""))
            return self.create_sample_commits(limit or commits_per_fork, fork_index)
        
        mock_client.get_recent_commits.side_effect = mock_get_recent_commits
        
        # Create display service
        display_service = RepositoryDisplayService(mock_client)
        
        # Test without commits
        start_time = time.time()
        
        with patch.object(display_service, '_get_fork_qualification_data') as mock_get_qualification:
            mock_get_qualification.return_value = ForkQualificationResult(
                total_forks=fork_count,
                collected_forks=forks_data,
                excluded_archived_disabled=0,
                excluded_no_commits_ahead=0,
                included_for_analysis=fork_count
            )
            
            result_no_commits = await display_service.show_fork_data(
                repo_url="testowner/large-repo",
                max_forks=fork_count,
                show_commits=0  # No commits
            )
        
        time_without_commits = time.time() - start_time
        
        # Reset mock call count
        mock_client.get_recent_commits.reset_mock()
        
        # Test with commits
        start_time = time.time()
        
        with patch.object(display_service, '_get_fork_qualification_data') as mock_get_qualification:
            mock_get_qualification.return_value = ForkQualificationResult(
                total_forks=fork_count,
                collected_forks=forks_data,
                excluded_archived_disabled=0,
                excluded_no_commits_ahead=0,
                included_for_analysis=fork_count
            )
            
            result_with_commits = await display_service.show_fork_data(
                repo_url="testowner/large-repo",
                max_forks=fork_count,
                show_commits=commits_per_fork
            )
        
        time_with_commits = time.time() - start_time
        
        # Performance analysis
        performance_overhead = time_with_commits - time_without_commits
        overhead_percentage = (performance_overhead / time_without_commits) * 100
        
        print(f"Performance comparison:")
        print(f"  Without commits: {time_without_commits:.2f}s")
        print(f"  With commits: {time_with_commits:.2f}s")
        print(f"  Overhead: {performance_overhead:.2f}s ({overhead_percentage:.1f}%)")
        
        # Assertions
        assert result_no_commits["total_forks"] == fork_count
        assert result_with_commits["total_forks"] == fork_count
        
        # Verify commit API calls were made only when show_commits > 0
        assert mock_client.get_recent_commits.call_count == fork_count
        
        # Performance should be reasonable even with commits
        assert time_with_commits < 20.0, f"With commits took too long: {time_with_commits:.2f}s"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_show_forks_performance_with_api_delays(self, mock_config, sample_repository):
        """Test performance with simulated API delays."""
        fork_count = 20
        commits_per_fork = 2
        api_delay = 0.1  # 100ms delay per API call
        
        # Create test data
        forks_data = self.create_large_fork_dataset(fork_count)
        
        # Setup mocks with delays
        mock_client = AsyncMock()
        
        async def mock_get_recent_commits_with_delay(owner, repo, branch=None, limit=None):
            await asyncio.sleep(api_delay)  # Simulate API delay
            fork_index = int(owner.replace("perfowner", ""))
            return self.create_sample_commits(limit or commits_per_fork, fork_index)
        
        mock_client.get_recent_commits.side_effect = mock_get_recent_commits_with_delay
        
        # Create display service
        display_service = RepositoryDisplayService(mock_client)
        
        # Measure performance with delays
        start_time = time.time()
        
        with patch.object(display_service, '_get_fork_qualification_data') as mock_get_qualification:
            mock_get_qualification.return_value = ForkQualificationResult(
                total_forks=fork_count,
                collected_forks=forks_data,
                excluded_archived_disabled=0,
                excluded_no_commits_ahead=0,
                included_for_analysis=fork_count
            )
            
            result = await display_service.show_fork_data(
                repo_url="testowner/large-repo",
                max_forks=fork_count,
                show_commits=commits_per_fork
            )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Calculate expected minimum time (sequential API calls)
        expected_min_time = fork_count * api_delay
        
        print(f"Performance with API delays:")
        print(f"  Execution time: {execution_time:.2f}s")
        print(f"  Expected minimum (sequential): {expected_min_time:.2f}s")
        print(f"  Efficiency ratio: {expected_min_time / execution_time:.2f}")
        
        # Assertions
        assert result["total_forks"] == fork_count
        assert result["displayed_forks"] == fork_count
        assert mock_client.get_recent_commits.call_count == fork_count
        
        # Should handle delays reasonably well
        assert execution_time >= expected_min_time, "Execution time too fast (delays not applied)"
        assert execution_time < expected_min_time * 2, f"Execution time too slow: {execution_time:.2f}s"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_show_forks_memory_usage_with_large_dataset(self, mock_config, sample_repository):
        """Test memory usage with large datasets."""
        import psutil
        import os
        
        fork_count = 100
        commits_per_fork = 5
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create test data
        forks_data = self.create_large_fork_dataset(fork_count)
        
        # Setup mocks
        mock_client = AsyncMock()
        
        def mock_get_recent_commits(owner, repo, branch=None, limit=None):
            fork_index = int(owner.replace("perfowner", ""))
            return self.create_sample_commits(limit or commits_per_fork, fork_index)
        
        mock_client.get_recent_commits.side_effect = mock_get_recent_commits
        
        # Create display service
        display_service = RepositoryDisplayService(mock_client)
        
        # Execute the operation
        with patch.object(display_service, '_get_fork_qualification_data') as mock_get_qualification:
            mock_get_qualification.return_value = ForkQualificationResult(
                total_forks=fork_count,
                collected_forks=forks_data,
                excluded_archived_disabled=0,
                excluded_no_commits_ahead=0,
                included_for_analysis=fork_count
            )
            
            result = await display_service.show_fork_data(
                repo_url="testowner/large-repo",
                max_forks=fork_count,
                show_commits=commits_per_fork
            )
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"Memory usage test:")
        print(f"  Initial memory: {initial_memory:.1f} MB")
        print(f"  Final memory: {final_memory:.1f} MB")
        print(f"  Memory increase: {memory_increase:.1f} MB")
        print(f"  Memory per fork: {memory_increase / fork_count:.2f} MB")
        
        # Assertions
        assert result["total_forks"] == fork_count
        assert result["displayed_forks"] == fork_count
        
        # Memory usage should be reasonable
        assert memory_increase < 100, f"Memory usage too high: {memory_increase:.1f} MB"
        assert memory_increase / fork_count < 1.0, f"Memory per fork too high: {memory_increase / fork_count:.2f} MB"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_show_forks_scalability_different_commit_counts(self, mock_config, sample_repository):
        """Test scalability with different commit counts per fork."""
        fork_count = 20
        commit_counts = [1, 3, 5, 10]
        
        results = {}
        
        for commits_per_fork in commit_counts:
            # Create test data
            forks_data = self.create_large_fork_dataset(fork_count)
            
            # Setup mocks
            mock_client = AsyncMock()
            
            def mock_get_recent_commits(owner, repo, branch=None, limit=None):
                fork_index = int(owner.replace("perfowner", ""))
                return self.create_sample_commits(limit or commits_per_fork, fork_index)
            
            mock_client.get_recent_commits.side_effect = mock_get_recent_commits
            
            # Create display service
            display_service = RepositoryDisplayService(mock_client)
            
            # Measure performance
            start_time = time.time()
            
            with patch.object(display_service, '_get_fork_qualification_data') as mock_get_qualification:
                mock_get_qualification.return_value = ForkQualificationResult(
                    total_forks=fork_count,
                    collected_forks=forks_data,
                    excluded_archived_disabled=0,
                    excluded_no_commits_ahead=0,
                    included_for_analysis=fork_count
                )
                
                result = await display_service.show_fork_data(
                    repo_url="testowner/large-repo",
                    max_forks=fork_count,
                    show_commits=commits_per_fork
                )
            
            execution_time = time.time() - start_time
            results[commits_per_fork] = execution_time
            
            # Verify results
            assert result["total_forks"] == fork_count
            assert result["displayed_forks"] == fork_count
            assert mock_client.get_recent_commits.call_count == fork_count
        
        # Analyze scalability
        print(f"Scalability test results:")
        for commits, time_taken in results.items():
            print(f"  {commits} commits per fork: {time_taken:.2f}s")
        
        # Performance should scale reasonably with commit count
        for commits in commit_counts:
            assert results[commits] < 10.0, f"Performance too slow for {commits} commits: {results[commits]:.2f}s"
        
        # Higher commit counts should take more time, but not excessively
        assert results[10] > results[1], "Performance should increase with more commits"
        assert results[10] / results[1] < 5.0, "Performance degradation too severe with more commits"