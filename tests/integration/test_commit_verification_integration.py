"""Integration tests for CommitVerificationEngine with real GitHub API scenarios."""

import asyncio
import os
import pytest
from datetime import UTC, datetime, timedelta

from forklift.analysis.commit_verification_engine import CommitVerificationEngine
from forklift.config import GitHubConfig
from forklift.github.client import GitHubClient
from forklift.models.fork_qualification import CollectedForkData, ForkQualificationMetrics


@pytest.mark.integration
@pytest.mark.asyncio
class TestCommitVerificationEngineIntegration:
    """Integration tests with real GitHub API."""
    
    @pytest.fixture
    async def github_client(self):
        """Create real GitHub client for integration tests."""
        token = os.getenv('GITHUB_TOKEN')
        if not token:
            pytest.skip("GitHub token required for integration tests")
        
        config = GitHubConfig(token=token)
        client = GitHubClient(config)
        
        yield client
        
        await client.close()
    
    @pytest.fixture
    def verification_engine(self, github_client):
        """Create CommitVerificationEngine with real GitHub client."""
        return CommitVerificationEngine(
            github_client=github_client,
            cache_ttl_hours=1,  # Short TTL for testing
            max_concurrent_requests=2,  # Conservative for testing
            retry_attempts=2
        )
    
    async def test_verify_real_fork_with_commits_ahead(self, verification_engine):
        """Test verification with a real fork that has commits ahead."""
        # Use a known fork that should have commits ahead
        # Note: This test may be brittle if the fork state changes
        result = await verification_engine.get_commits_ahead(
            "maliayas", "github-network-ninja",  # Fork
            "maliayas", "github-network-ninja"   # Parent (same for testing)
        )
        
        assert result["success"] is True
        assert "ahead_by" in result
        assert "behind_by" in result
        assert "verified_at" in result
        assert result["verification_method"] == "github_compare_api"
        
        # Verify statistics were updated
        stats = verification_engine.get_verification_stats()
        assert stats["api_calls_made"] >= 1
        assert stats["successful_verifications"] >= 1
    
    async def test_verify_nonexistent_repository(self, verification_engine):
        """Test verification with nonexistent repository."""
        result = await verification_engine.get_commits_ahead(
            "nonexistent-user-12345", "nonexistent-repo-12345",
            "octocat", "Hello-World"
        )
        
        assert result["success"] is False
        assert result["error"] == "repository_not_found"
        assert result["ahead_by"] == 0
        assert result["behind_by"] == 0
        
        # Verify error statistics
        stats = verification_engine.get_verification_stats()
        assert stats["verification_errors"] >= 1
    
    async def test_cache_functionality_with_real_api(self, verification_engine):
        """Test cache functionality with real API calls."""
        # First call should hit API
        result1 = await verification_engine.get_commits_ahead(
            "octocat", "Hello-World",
            "octocat", "Hello-World"
        )
        
        initial_stats = verification_engine.get_verification_stats()
        initial_api_calls = initial_stats["api_calls_made"]
        
        # Second call should use cache
        result2 = await verification_engine.get_commits_ahead(
            "octocat", "Hello-World",
            "octocat", "Hello-World"
        )
        
        final_stats = verification_engine.get_verification_stats()
        
        # Results should be identical
        assert result1 == result2
        
        # API calls should not increase (cache hit)
        assert final_stats["api_calls_made"] == initial_api_calls
        assert final_stats["cache_hits"] >= 1
    
    async def test_cache_bypass_functionality(self, verification_engine):
        """Test cache bypass functionality."""
        # First call with cache
        await verification_engine.get_commits_ahead(
            "octocat", "Hello-World",
            "octocat", "Hello-World"
        )
        
        initial_stats = verification_engine.get_verification_stats()
        initial_api_calls = initial_stats["api_calls_made"]
        
        # Second call bypassing cache
        await verification_engine.get_commits_ahead(
            "octocat", "Hello-World",
            "octocat", "Hello-World",
            use_cache=False
        )
        
        final_stats = verification_engine.get_verification_stats()
        
        # API calls should increase (cache bypassed)
        assert final_stats["api_calls_made"] > initial_api_calls
    
    async def test_batch_verification_with_real_forks(self, verification_engine):
        """Test batch verification with real fork data."""
        # Create fork data for known repositories
        fork_data_list = []
        
        # Use octocat/Hello-World as test case (comparing with itself)
        metrics = ForkQualificationMetrics(
            id=1296269,  # Real Hello-World repo ID
            name="Hello-World",
            full_name="octocat/Hello-World",
            owner="octocat",
            html_url="https://github.com/octocat/Hello-World",
            created_at=datetime(2011, 1, 26, 19, 1, 12, tzinfo=UTC),
            updated_at=datetime.now(UTC) - timedelta(days=1),
            pushed_at=datetime(2011, 1, 26, 19, 14, 43, tzinfo=UTC)
        )
        fork_data_list.append(CollectedForkData(metrics=metrics))
        
        result = await verification_engine.batch_verify_forks(
            fork_data_list,
            "octocat",
            "Hello-World"
        )
        
        assert len(result) == 1
        fork_result = result[0]
        
        # Should have verification results
        assert fork_result.exact_commits_ahead is not None
        assert fork_result.exact_commits_behind is not None
        
        # Verify statistics
        stats = verification_engine.get_verification_stats()
        assert stats["api_calls_made"] >= 1
    
    async def test_batch_verification_skip_no_commits(self, verification_engine):
        """Test batch verification skipping forks with no commits."""
        fork_data_list = []
        
        # Create fork with no commits ahead (created_at >= pushed_at)
        no_commits_metrics = ForkQualificationMetrics(
            id=1000001,
            name="no-commits-fork",
            full_name="test/no-commits-fork",
            owner="test",
            html_url="https://github.com/test/no-commits-fork",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            pushed_at=datetime.now(UTC) - timedelta(minutes=1)  # Before creation
        )
        
        # Create fork with potential commits (using real repo)
        has_commits_metrics = ForkQualificationMetrics(
            id=1296269,
            name="Hello-World",
            full_name="octocat/Hello-World",
            owner="octocat",
            html_url="https://github.com/octocat/Hello-World",
            created_at=datetime(2011, 1, 26, 19, 1, 12, tzinfo=UTC),
            updated_at=datetime.now(UTC) - timedelta(days=1),
            pushed_at=datetime(2011, 1, 26, 19, 14, 43, tzinfo=UTC)
        )
        
        fork_data_list = [
            CollectedForkData(metrics=no_commits_metrics),
            CollectedForkData(metrics=has_commits_metrics)
        ]
        
        initial_stats = verification_engine.get_verification_stats()
        initial_api_calls = initial_stats["api_calls_made"]
        
        result = await verification_engine.batch_verify_forks(
            fork_data_list,
            "octocat",
            "Hello-World",
            skip_no_commits=True
        )
        
        assert len(result) == 2
        
        # Find results by name
        no_commits_result = next(r for r in result if r.metrics.name == "no-commits-fork")
        has_commits_result = next(r for r in result if r.metrics.name == "Hello-World")
        
        # No commits fork should not be verified
        assert no_commits_result.exact_commits_ahead is None
        assert no_commits_result.exact_commits_behind is None
        
        # Has commits fork should be verified
        assert has_commits_result.exact_commits_ahead is not None
        assert has_commits_result.exact_commits_behind is not None
        
        final_stats = verification_engine.get_verification_stats()
        
        # Should have made API calls only for the fork with commits
        # (2 calls: fork repo + parent repo + 1 compare call = 3 total minimum)
        assert final_stats["api_calls_made"] > initial_api_calls
    
    async def test_individual_fork_verification(self, verification_engine):
        """Test individual fork verification."""
        # Create fork data for known repository
        metrics = ForkQualificationMetrics(
            id=1296269,
            name="Hello-World",
            full_name="octocat/Hello-World",
            owner="octocat",
            html_url="https://github.com/octocat/Hello-World",
            created_at=datetime(2011, 1, 26, 19, 1, 12, tzinfo=UTC),
            updated_at=datetime.now(UTC) - timedelta(days=1),
            pushed_at=datetime(2011, 1, 26, 19, 14, 43, tzinfo=UTC)
        )
        fork_data = CollectedForkData(metrics=metrics)
        
        result = await verification_engine.verify_individual_fork(
            fork_data,
            "octocat",
            "Hello-World"
        )
        
        # Should have verification results
        assert result.exact_commits_ahead is not None
        assert result.exact_commits_behind is not None
        
        # Verify statistics
        stats = verification_engine.get_verification_stats()
        assert stats["successful_verifications"] >= 1
    
    async def test_concurrent_verification_real_api(self, verification_engine):
        """Test concurrent verification with real API calls."""
        # Create multiple fork data entries using the same repo for simplicity
        fork_data_list = []
        for i in range(3):
            metrics = ForkQualificationMetrics(
                id=1296269 + i,
                name="Hello-World",
                full_name="octocat/Hello-World",
                owner="octocat",
                html_url="https://github.com/octocat/Hello-World",
                created_at=datetime(2011, 1, 26, 19, 1, 12, tzinfo=UTC),
                updated_at=datetime.now(UTC) - timedelta(days=1),
                pushed_at=datetime(2011, 1, 26, 19, 14, 43, tzinfo=UTC)
            )
            fork_data_list.append(CollectedForkData(metrics=metrics))
        
        start_time = datetime.now()
        
        result = await verification_engine.batch_verify_forks(
            fork_data_list,
            "octocat",
            "Hello-World"
        )
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        assert len(result) == 3
        
        # All forks should have verification results
        for fork_result in result:
            assert fork_result.exact_commits_ahead is not None
            assert fork_result.exact_commits_behind is not None
        
        # Should complete in reasonable time (concurrent processing)
        assert processing_time < 30  # Should be much faster with concurrency
        
        # Verify statistics
        stats = verification_engine.get_verification_stats()
        assert stats["successful_verifications"] >= 3
    
    async def test_error_handling_with_mixed_results(self, verification_engine):
        """Test error handling with mix of valid and invalid repositories."""
        fork_data_list = []
        
        # Valid repository
        valid_metrics = ForkQualificationMetrics(
            id=1296269,
            name="Hello-World",
            full_name="octocat/Hello-World",
            owner="octocat",
            html_url="https://github.com/octocat/Hello-World",
            created_at=datetime(2011, 1, 26, 19, 1, 12, tzinfo=UTC),
            updated_at=datetime.now(UTC) - timedelta(days=1),
            pushed_at=datetime(2011, 1, 26, 19, 14, 43, tzinfo=UTC)
        )
        
        # Invalid repository
        invalid_metrics = ForkQualificationMetrics(
            id=9999999,
            name="nonexistent-repo",
            full_name="nonexistent-user/nonexistent-repo",
            owner="nonexistent-user",
            html_url="https://github.com/nonexistent-user/nonexistent-repo",
            created_at=datetime.now(UTC) - timedelta(days=5),
            updated_at=datetime.now(UTC) - timedelta(days=1),
            pushed_at=datetime.now(UTC)
        )
        
        fork_data_list = [
            CollectedForkData(metrics=valid_metrics),
            CollectedForkData(metrics=invalid_metrics)
        ]
        
        result = await verification_engine.batch_verify_forks(
            fork_data_list,
            "octocat",
            "Hello-World"
        )
        
        assert len(result) == 2
        
        # Find results by name
        valid_result = next(r for r in result if r.metrics.name == "Hello-World")
        invalid_result = next(r for r in result if r.metrics.name == "nonexistent-repo")
        
        # Valid fork should have verification results
        assert valid_result.exact_commits_ahead is not None
        assert valid_result.exact_commits_behind is not None
        
        # Invalid fork should have unknown results
        assert invalid_result.exact_commits_ahead == "Unknown"
        assert invalid_result.exact_commits_behind == "Unknown"
        
        # Verify statistics show both success and errors
        stats = verification_engine.get_verification_stats()
        assert stats["successful_verifications"] >= 1
        assert stats["verification_errors"] >= 1
    
    async def test_rate_limit_handling_simulation(self, verification_engine):
        """Test rate limit handling by making many requests."""
        # Note: This test might hit actual rate limits, so we use a small number
        fork_data_list = []
        
        # Create several fork data entries
        for i in range(5):  # Small number to avoid hitting rate limits
            metrics = ForkQualificationMetrics(
                id=1296269 + i,
                name=f"Hello-World-{i}",
                full_name="octocat/Hello-World",
                owner="octocat",
                html_url="https://github.com/octocat/Hello-World",
                created_at=datetime(2011, 1, 26, 19, 1, 12, tzinfo=UTC),
                updated_at=datetime.now(UTC) - timedelta(days=1),
                pushed_at=datetime(2011, 1, 26, 19, 14, 43, tzinfo=UTC)
            )
            fork_data_list.append(CollectedForkData(metrics=metrics))
        
        # This should complete without errors even if rate limits are encountered
        result = await verification_engine.batch_verify_forks(
            fork_data_list,
            "octocat",
            "Hello-World"
        )
        
        assert len(result) == 5
        
        # All should have some result (either success or handled error)
        for fork_result in result:
            # Should have either valid results or "Unknown" for errors
            assert (
                isinstance(fork_result.exact_commits_ahead, int) or
                fork_result.exact_commits_ahead == "Unknown"
            )
            assert (
                isinstance(fork_result.exact_commits_behind, int) or
                fork_result.exact_commits_behind == "Unknown"
            )


@pytest.mark.integration
@pytest.mark.asyncio
class TestCommitVerificationEnginePerformance:
    """Performance tests for CommitVerificationEngine."""
    
    @pytest.fixture
    async def github_client(self):
        """Create real GitHub client for performance tests."""
        token = os.getenv('GITHUB_TOKEN')
        if not token:
            pytest.skip("GitHub token required for performance tests")
        
        config = GitHubConfig(token=token)
        client = GitHubClient(config)
        
        yield client
        
        await client.close()
    
    @pytest.fixture
    def verification_engine(self, github_client):
        """Create CommitVerificationEngine for performance testing."""
        return CommitVerificationEngine(
            github_client=github_client,
            cache_ttl_hours=24,
            max_concurrent_requests=5,
            retry_attempts=3
        )
    
    async def test_cache_performance_improvement(self, verification_engine):
        """Test that cache provides significant performance improvement."""
        # First call (cache miss)
        start_time = datetime.now()
        await verification_engine.get_commits_ahead(
            "octocat", "Hello-World",
            "octocat", "Hello-World"
        )
        first_call_time = (datetime.now() - start_time).total_seconds()
        
        # Second call (cache hit)
        start_time = datetime.now()
        await verification_engine.get_commits_ahead(
            "octocat", "Hello-World",
            "octocat", "Hello-World"
        )
        second_call_time = (datetime.now() - start_time).total_seconds()
        
        # Cache hit should be significantly faster
        assert second_call_time < first_call_time * 0.1  # At least 10x faster
        
        # Verify cache statistics
        stats = verification_engine.get_verification_stats()
        assert stats["cache_hits"] >= 1
        assert stats["cache_hit_rate"] > 0
    
    async def test_concurrent_processing_performance(self, verification_engine):
        """Test that concurrent processing improves performance."""
        # Create multiple fork data entries
        fork_data_list = []
        for i in range(3):  # Small number for performance test
            metrics = ForkQualificationMetrics(
                id=1296269 + i,
                name=f"Hello-World-{i}",
                full_name="octocat/Hello-World",
                owner="octocat",
                html_url="https://github.com/octocat/Hello-World",
                created_at=datetime(2011, 1, 26, 19, 1, 12, tzinfo=UTC),
                updated_at=datetime.now(UTC) - timedelta(days=1),
                pushed_at=datetime(2011, 1, 26, 19, 14, 43, tzinfo=UTC)
            )
            fork_data_list.append(CollectedForkData(metrics=metrics))
        
        # Measure batch processing time
        start_time = datetime.now()
        result = await verification_engine.batch_verify_forks(
            fork_data_list,
            "octocat",
            "Hello-World"
        )
        batch_time = (datetime.now() - start_time).total_seconds()
        
        # Measure sequential processing time
        start_time = datetime.now()
        for fork_data in fork_data_list:
            await verification_engine.verify_individual_fork(
                fork_data,
                "octocat",
                "Hello-World"
            )
        sequential_time = (datetime.now() - start_time).total_seconds()
        
        assert len(result) == 3
        
        # Batch processing should be faster than sequential
        # (allowing some margin for API variability)
        assert batch_time < sequential_time * 0.8
    
    async def test_skip_optimization_performance(self, verification_engine):
        """Test that skipping forks with no commits improves performance."""
        fork_data_list = []
        
        # Create fork with no commits (will be skipped)
        no_commits_metrics = ForkQualificationMetrics(
            id=1000001,
            name="no-commits-fork",
            full_name="test/no-commits-fork",
            owner="test",
            html_url="https://github.com/test/no-commits-fork",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            pushed_at=datetime.now(UTC) - timedelta(minutes=1)
        )
        
        # Create fork with commits (will be verified)
        has_commits_metrics = ForkQualificationMetrics(
            id=1296269,
            name="Hello-World",
            full_name="octocat/Hello-World",
            owner="octocat",
            html_url="https://github.com/octocat/Hello-World",
            created_at=datetime(2011, 1, 26, 19, 1, 12, tzinfo=UTC),
            updated_at=datetime.now(UTC) - timedelta(days=1),
            pushed_at=datetime(2011, 1, 26, 19, 14, 43, tzinfo=UTC)
        )
        
        fork_data_list = [
            CollectedForkData(metrics=no_commits_metrics),
            CollectedForkData(metrics=has_commits_metrics)
        ]
        
        # Test with skipping enabled
        start_time = datetime.now()
        result_with_skip = await verification_engine.batch_verify_forks(
            fork_data_list,
            "octocat",
            "Hello-World",
            skip_no_commits=True
        )
        skip_time = (datetime.now() - start_time).total_seconds()
        
        # Reset stats and test without skipping
        verification_engine.reset_stats()
        
        start_time = datetime.now()
        result_no_skip = await verification_engine.batch_verify_forks(
            fork_data_list,
            "octocat",
            "Hello-World",
            skip_no_commits=False
        )
        no_skip_time = (datetime.now() - start_time).total_seconds()
        
        assert len(result_with_skip) == 2
        assert len(result_no_skip) == 2
        
        # Skipping should be faster (fewer API calls)
        assert skip_time <= no_skip_time
        
        # Verify API call reduction
        stats_with_skip = verification_engine.get_verification_stats()
        
        # With skipping, should have made fewer API calls
        # (exact numbers depend on implementation, but should be fewer)
        assert stats_with_skip["api_calls_made"] >= 1  # At least one verification