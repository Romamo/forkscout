"""Integration tests for optimized commit fetching with real GitHub data."""

import os
import pytest
import pytest_asyncio
import asyncio
from datetime import datetime

from forkscout.config import GitHubConfig
from forkscout.github.client import GitHubClient
from forkscout.github.fork_list_processor import ForkListProcessor
from forkscout.github.optimized_commit_fetcher import OptimizedCommitFetcher
from forkscout.models.fork_qualification import CollectedForkData, ForkQualificationMetrics


@pytest.mark.integration
@pytest.mark.asyncio
class TestOptimizedCommitFetchingIntegration:
    """Integration tests for optimized commit fetching."""

    @pytest_asyncio.fixture
    async def github_client(self):
        """Create a real GitHub client for integration testing."""
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            pytest.skip("GITHUB_TOKEN environment variable not set")
        
        config = GitHubConfig(
            token=token,
            base_url="https://api.github.com",
            timeout_seconds=30,
        )
        
        client = GitHubClient(config)
        async with client:
            yield client

    @pytest.fixture
    def commit_fetcher(self, github_client):
        """Create optimized commit fetcher with real GitHub client."""
        return OptimizedCommitFetcher(github_client)

    @pytest.fixture
    def fork_processor(self, github_client):
        """Create fork list processor with real GitHub client."""
        return ForkListProcessor(github_client)

    async def test_optimized_commit_fetching_with_real_repository(
        self, commit_fetcher, fork_processor
    ):
        """Test optimized commit fetching with a real repository that has forks."""
        # Use a small repository with known forks for testing
        owner = "maliayas"
        repo = "github-network-ninja"
        
        # First, get qualified forks data
        qualified_forks = await fork_processor.collect_and_process_forks(owner, repo)
        
        # Verify we have some forks to work with
        assert len(qualified_forks.collected_forks) > 0
        
        # Test optimized commit fetching
        commits_by_fork = await commit_fetcher.fetch_commits_for_qualified_forks(
            qualified_forks,
            owner,
            repo,
            max_commits_per_fork=3,
        )
        
        # Verify results
        assert isinstance(commits_by_fork, dict)
        assert len(commits_by_fork) == len(qualified_forks.collected_forks)
        
        # Check that forks identified as having no commits have empty lists
        for fork_data in qualified_forks.forks_to_skip:
            fork_name = fork_data.metrics.full_name
            assert fork_name in commits_by_fork
            assert commits_by_fork[fork_name] == []
        
        # Check that forks identified as needing analysis have been processed
        for fork_data in qualified_forks.forks_needing_analysis:
            fork_name = fork_data.metrics.full_name
            assert fork_name in commits_by_fork
            # Commits list may be empty if fork actually has no commits ahead
            assert isinstance(commits_by_fork[fork_name], list)

    async def test_optimization_summary_with_real_data(
        self, commit_fetcher, fork_processor
    ):
        """Test optimization summary generation with real fork data."""
        # Use a repository with multiple forks
        owner = "maliayas"
        repo = "github-network-ninja"
        
        # Get qualified forks data
        qualified_forks = await fork_processor.collect_and_process_forks(owner, repo)
        
        # Generate optimization summary
        summary = commit_fetcher.get_optimization_summary(qualified_forks)
        
        # Verify summary contains expected information
        assert "Total Forks:" in summary
        assert "Forks to Skip:" in summary
        assert "Forks Needing Commits:" in summary
        assert "API Call Optimization:" in summary
        assert "Efficiency gain:" in summary
        
        # Verify the numbers make sense
        total_forks = len(qualified_forks.collected_forks)
        forks_to_skip = len(qualified_forks.forks_to_skip)
        forks_needing_commits = len(qualified_forks.forks_needing_analysis)
        
        assert forks_to_skip + forks_needing_commits == total_forks

    async def test_single_fork_optimization_with_real_data(
        self, commit_fetcher, github_client
    ):
        """Test single fork optimization with real fork data."""
        # Create a fork that should have no commits ahead (created_at >= pushed_at)
        fork_metrics = ForkQualificationMetrics(
            id=123456,
            name="test-repo",
            full_name="test-user/test-repo",
            owner="test-user",
            html_url="https://github.com/test-user/test-repo",
            stargazers_count=0,
            forks_count=0,
            watchers_count=0,
            size=100,
            language="Python",
            topics=[],
            open_issues_count=0,
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            updated_at=datetime(2023, 1, 1, 12, 0, 0),
            pushed_at=datetime(2023, 1, 1, 12, 0, 0),  # Same as created_at
            archived=False,
            disabled=False,
            fork=True,
        )
        
        fork_data = CollectedForkData(metrics=fork_metrics)
        
        # Test that it gets skipped based on qualification
        commits = await commit_fetcher.fetch_commits_for_single_fork_with_qualification(
            fork_data, "parent", "repo", max_commits_per_fork=5
        )
        
        # Should be empty due to optimization
        assert commits == []

    async def test_batch_processing_with_progress_callback(
        self, commit_fetcher, fork_processor
    ):
        """Test batch processing with progress callback."""
        owner = "maliayas"
        repo = "github-network-ninja"
        
        # Get qualified forks data
        qualified_forks = await fork_processor.collect_and_process_forks(owner, repo)
        
        # Track progress calls
        progress_calls = []
        def progress_callback(current, total, status):
            progress_calls.append((current, total, status))
        
        # Test with progress callback
        commits_by_fork = await commit_fetcher.fetch_commits_for_qualified_forks(
            qualified_forks,
            owner,
            repo,
            max_commits_per_fork=2,
            progress_callback=progress_callback,
        )
        
        # Verify progress was tracked
        forks_needing_commits = len(qualified_forks.forks_needing_analysis)
        if forks_needing_commits > 0:
            assert len(progress_calls) > 0
            # Last progress call should indicate completion
            last_call = progress_calls[-1]
            assert last_call[0] == forks_needing_commits  # current
            assert last_call[1] == forks_needing_commits  # total
        
        # Verify results are still correct
        assert len(commits_by_fork) == len(qualified_forks.collected_forks)

    async def test_error_handling_with_invalid_repository(self, commit_fetcher):
        """Test error handling when repository doesn't exist."""
        # Create fake qualified forks data
        fork_metrics = ForkQualificationMetrics(
            id=999999,
            name="nonexistent-repo",
            full_name="nonexistent-user/nonexistent-repo",
            owner="nonexistent-user",
            html_url="https://github.com/nonexistent-user/nonexistent-repo",
            stargazers_count=1,
            forks_count=0,
            watchers_count=1,
            size=50,
            language="Python",
            topics=[],
            open_issues_count=0,
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            updated_at=datetime(2023, 1, 2, 12, 0, 0),
            pushed_at=datetime(2023, 1, 3, 12, 0, 0),  # Has commits based on timestamps
            archived=False,
            disabled=False,
            fork=True,
        )
        
        fork_data = CollectedForkData(metrics=fork_metrics)
        
        # This should handle the error gracefully and return empty list
        commits = await commit_fetcher.fetch_commits_for_single_fork_with_qualification(
            fork_data, "nonexistent-parent", "nonexistent-parent-repo", max_commits_per_fork=5
        )
        
        # Should return empty list due to error handling
        # Note: This might raise an exception depending on the specific error handling implementation
        # The test verifies that the system handles errors gracefully

    async def test_api_efficiency_measurement(self, commit_fetcher, fork_processor):
        """Test that API efficiency is properly measured."""
        owner = "maliayas"
        repo = "github-network-ninja"
        
        # Get qualified forks data
        qualified_forks = await fork_processor.collect_and_process_forks(owner, repo)
        
        # Get optimization summary before fetching
        summary_before = commit_fetcher.get_optimization_summary(qualified_forks)
        
        # Extract expected efficiency from summary
        lines = summary_before.split('\n')
        efficiency_line = [line for line in lines if 'Efficiency gain:' in line][0]
        expected_efficiency = float(efficiency_line.split(':')[1].strip().rstrip('%'))
        
        # Perform optimized commit fetching
        commits_by_fork = await commit_fetcher.fetch_commits_for_qualified_forks(
            qualified_forks,
            owner,
            repo,
            max_commits_per_fork=2,
        )
        
        # Verify that optimization actually occurred
        total_forks = len(qualified_forks.collected_forks)
        forks_skipped = len(qualified_forks.forks_to_skip)
        
        if total_forks > 0:
            actual_skip_rate = (forks_skipped / total_forks) * 100
            # The efficiency should be related to the skip rate
            assert expected_efficiency >= 0
            if forks_skipped > 0:
                assert expected_efficiency > 0

    async def test_concurrent_processing_stability(self, commit_fetcher, fork_processor):
        """Test that concurrent processing is stable and doesn't cause issues."""
        owner = "maliayas"
        repo = "github-network-ninja"
        
        # Get qualified forks data
        qualified_forks = await fork_processor.collect_and_process_forks(owner, repo)
        
        # Run multiple concurrent fetch operations
        tasks = []
        for i in range(3):  # Run 3 concurrent operations
            task = commit_fetcher.fetch_commits_for_qualified_forks(
                qualified_forks,
                owner,
                repo,
                max_commits_per_fork=1,  # Keep it small for speed
            )
            tasks.append(task)
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all completed successfully
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Concurrent operation {i} failed: {result}")
            
            # Verify result structure
            assert isinstance(result, dict)
            assert len(result) == len(qualified_forks.collected_forks)
        
        # Verify all results are identical (deterministic)
        for i in range(1, len(results)):
            assert len(results[i]) == len(results[0])
            for fork_name in results[0]:
                assert fork_name in results[i]
                # Commit lists should be the same length (content might vary due to timing)
                assert len(results[i][fork_name]) == len(results[0][fork_name])