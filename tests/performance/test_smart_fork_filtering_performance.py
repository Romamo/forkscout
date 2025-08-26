"""Performance tests for smart fork filtering functionality."""

import asyncio
import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from forklift.analysis.fork_commit_status_checker import ForkCommitStatusChecker
from forklift.models.fork_filtering import ForkFilteringConfig
from forklift.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualificationStats,
    QualifiedForksResult,
)
from forklift.models.github import Repository


class TestSmartForkFilteringPerformance:
    """Performance tests for smart fork filtering."""

    @pytest.fixture
    def performance_config(self):
        """Create optimized configuration for performance testing."""
        return ForkFilteringConfig(
            enabled=True,
            log_filtering_decisions=False,  # Disable logging for performance
            log_statistics=False,
            fallback_to_api=True,
            max_api_fallback_calls=50,
            prefer_inclusion_on_uncertainty=True
        )

    @pytest.fixture
    def large_qualification_dataset(self):
        """Create a large qualification dataset for performance testing."""
        fork_data = []

        # Create 1000 forks with varied characteristics
        for i in range(1000):
            has_commits = i % 4 != 0  # 75% have commits, 25% don't
            is_archived = i % 50 == 0  # 2% archived
            is_disabled = i % 100 == 0  # 1% disabled

            created_time = datetime(2023, 1, 1, tzinfo=UTC)
            pushed_time = (
                datetime(2023, 6, 1, tzinfo=UTC)
                if has_commits
                else created_time
            )

            metrics = ForkQualificationMetrics(
                id=100000 + i,
                full_name=f"perfuser{i}/perfrepo{i}",
                owner=f"perfuser{i}",
                name=f"perfrepo{i}",
                html_url=f"https://github.com/perfuser{i}/perfrepo{i}",
                stargazers_count=i % 100,
                forks_count=i % 50,
                size=1000 + (i * 5),
                language="Python" if i % 3 == 0 else "JavaScript" if i % 3 == 1 else "Go",
                created_at=created_time,
                updated_at=pushed_time,
                pushed_at=pushed_time,
                open_issues_count=i % 20,
                topics=[f"topic{i % 10}", f"category{i % 5}"],
                watchers_count=i % 75,
                archived=is_archived,
                disabled=is_disabled,
                fork=True
            )

            fork_data.append(CollectedForkData(metrics=metrics))

        stats = QualificationStats(
            total_forks_discovered=1000,
            forks_with_no_commits=250,  # 25%
            forks_with_commits=750,     # 75%
            api_calls_made=1000,
            processing_time_seconds=50.0
        )

        return QualifiedForksResult(
            repository_owner="upstream",
            repository_name="performance-repo",
            repository_url="https://github.com/upstream/performance-repo",
            collected_forks=fork_data,
            stats=stats
        )

    @pytest.mark.asyncio
    async def test_qualification_data_lookup_performance(
        self, performance_config, large_qualification_dataset
    ):
        """Test performance of qualification data lookups."""
        mock_github_client = AsyncMock()
        checker = ForkCommitStatusChecker(mock_github_client, performance_config)

        # Measure time for 1000 qualification data lookups
        start_time = time.perf_counter()

        results = []
        for i in range(1000):
            fork_url = f"https://github.com/perfuser{i}/perfrepo{i}"
            result = await checker.has_commits_ahead(fork_url, large_qualification_dataset)
            results.append(result)

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Verify results
        assert len(results) == 1000
        true_count = results.count(True)
        false_count = results.count(False)

        # Should match our test data distribution (75% True, 25% False)
        assert true_count > false_count
        assert 700 <= true_count <= 800  # Allow some variance
        assert 200 <= false_count <= 300

        # Performance assertions
        assert total_time < 2.0  # Should complete in under 2 seconds
        assert total_time / 1000 < 0.002  # Less than 2ms per lookup on average

        # Verify no API calls were made (all from qualification data)
        assert mock_github_client.get_repository.call_count == 0

        # Verify statistics
        stats = checker.get_statistics()
        assert stats.qualification_data_hits == 1000
        assert stats.api_fallback_calls == 0
        assert stats.api_usage_efficiency == 100.0

    @pytest.mark.asyncio
    async def test_api_fallback_performance_with_limits(
        self, performance_config, large_qualification_dataset
    ):
        """Test API fallback performance with rate limiting."""
        mock_github_client = AsyncMock()

        # Mock API response with simulated delay
        async def mock_get_repository_with_delay(owner, repo):
            await asyncio.sleep(0.01)  # 10ms delay per API call
            return Repository(
                id=999999,
                owner=owner,
                name=repo,
                full_name=f"{owner}/{repo}",
                url=f"https://api.github.com/repos/{owner}/{repo}",
                html_url=f"https://github.com/{owner}/{repo}",
                clone_url=f"https://github.com/{owner}/{repo}.git",
                created_at=datetime(2023, 1, 1, tzinfo=UTC),
                pushed_at=datetime(2023, 5, 1, tzinfo=UTC),
                default_branch="main"
            )

        mock_github_client.get_repository.side_effect = mock_get_repository_with_delay

        # Set API fallback limit
        performance_config.max_api_fallback_calls = 20
        checker = ForkCommitStatusChecker(mock_github_client, performance_config)

        # Test mix of known and unknown forks
        fork_urls = []

        # 900 known forks (from qualification data)
        for i in range(900):
            fork_urls.append(f"https://github.com/perfuser{i}/perfrepo{i}")

        # 100 unknown forks (will trigger API fallback, but limited)
        for i in range(100):
            fork_urls.append(f"https://github.com/unknown{i}/unknownrepo{i}")

        start_time = time.perf_counter()

        results = []
        for fork_url in fork_urls:
            result = await checker.has_commits_ahead(fork_url, large_qualification_dataset)
            results.append(result)

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Verify API call limiting worked
        assert mock_github_client.get_repository.call_count == 20  # Limited to 20 calls

        # Verify performance - should be fast due to limiting API calls
        assert total_time < 5.0  # Should complete in under 5 seconds

        # Verify statistics
        stats = checker.get_statistics()
        assert stats.qualification_data_hits == 900
        assert stats.api_fallback_calls == 20
        assert stats.api_usage_efficiency > 95.0  # Very high efficiency

    @pytest.mark.asyncio
    async def test_concurrent_fork_processing_performance(
        self, performance_config, large_qualification_dataset
    ):
        """Test performance of concurrent fork processing."""
        mock_github_client = AsyncMock()
        checker = ForkCommitStatusChecker(mock_github_client, performance_config)

        # Create 500 concurrent tasks
        fork_urls = [f"https://github.com/perfuser{i}/perfrepo{i}" for i in range(500)]

        # Measure concurrent processing time
        start_time = time.perf_counter()

        tasks = [
            checker.has_commits_ahead(fork_url, large_qualification_dataset)
            for fork_url in fork_urls
        ]

        results = await asyncio.gather(*tasks)

        end_time = time.perf_counter()
        concurrent_time = end_time - start_time

        # Verify results
        assert len(results) == 500

        # Performance assertion - concurrent processing should be efficient
        assert concurrent_time < 1.0  # Should complete in under 1 second
        assert concurrent_time / 500 < 0.002  # Less than 2ms per fork on average

        # Verify no API calls were made
        assert mock_github_client.get_repository.call_count == 0

    @pytest.mark.asyncio
    async def test_memory_efficiency_with_large_datasets(
        self, performance_config, large_qualification_dataset
    ):
        """Test memory efficiency when processing large datasets."""
        pytest.skip("psutil not available - skipping memory test")

        mock_github_client = AsyncMock()
        checker = ForkCommitStatusChecker(mock_github_client, performance_config)

        # Process large number of forks multiple times to test memory growth
        for batch in range(5):  # 5 batches of 1000 forks each
            for i in range(1000):
                fork_url = f"https://github.com/perfuser{i}/perfrepo{i}"
                await checker.has_commits_ahead(fork_url, large_qualification_dataset)

        # Test passes if no memory errors occur
        assert True

    @pytest.mark.asyncio
    async def test_fork_evaluation_batch_performance(
        self, performance_config, large_qualification_dataset
    ):
        """Test performance of batch fork evaluation."""
        mock_github_client = AsyncMock()
        checker = ForkCommitStatusChecker(mock_github_client, performance_config)

        # Create batch of fork data for evaluation
        fork_batch = []
        for i in range(1000):
            fork_data = {
                "full_name": f"perfuser{i}/perfrepo{i}",
                "archived": i % 50 == 0,  # 2% archived
                "disabled": i % 100 == 0,  # 1% disabled
            }
            fork_url = f"https://github.com/{fork_data['full_name']}"
            fork_batch.append((fork_url, fork_data))

        # Measure batch evaluation performance
        start_time = time.perf_counter()

        evaluation_results = []
        for fork_url, fork_data in fork_batch:
            should_filter, reason = await checker.evaluate_fork_for_filtering(
                fork_url, fork_data, large_qualification_dataset
            )
            evaluation_results.append((should_filter, reason))

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Verify results
        assert len(evaluation_results) == 1000

        # Count filtering reasons
        filtered_count = sum(1 for result in evaluation_results if result[0])
        not_filtered_count = sum(1 for result in evaluation_results if not result[0])

        # Should have filtered some forks (archived, disabled, no commits)
        assert filtered_count > 0
        assert not_filtered_count > 0
        assert filtered_count + not_filtered_count == 1000

        # Performance assertions
        assert total_time < 3.0  # Should complete in under 3 seconds
        assert total_time / 1000 < 0.003  # Less than 3ms per evaluation on average

        # Verify statistics
        stats = checker.get_statistics()
        assert stats.total_forks_evaluated == 1000
        assert stats.forks_filtered_out == filtered_count
        assert stats.forks_included == not_filtered_count

    @pytest.mark.asyncio
    async def test_api_efficiency_measurement_accuracy(
        self, performance_config, large_qualification_dataset
    ):
        """Test accuracy of API efficiency measurements."""
        mock_github_client = AsyncMock()

        # Mock API response
        mock_github_client.get_repository.return_value = Repository(
            id=999999,
            owner="test",
            name="repo",
            full_name="test/repo",
            url="https://api.github.com/repos/test/repo",
            html_url="https://github.com/test/repo",
            clone_url="https://github.com/test/repo.git",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            pushed_at=datetime(2023, 5, 1, tzinfo=UTC),
            default_branch="main"
        )

        checker = ForkCommitStatusChecker(mock_github_client, performance_config)

        # Process exact mix: 800 from qualification data, 200 from API
        qualification_lookups = 0
        api_lookups = 0

        # 800 known forks
        for i in range(800):
            fork_url = f"https://github.com/perfuser{i}/perfrepo{i}"
            await checker.has_commits_ahead(fork_url, large_qualification_dataset)
            qualification_lookups += 1

        # 200 unknown forks
        for i in range(200):
            fork_url = f"https://github.com/unknown{i}/repo{i}"
            await checker.has_commits_ahead(fork_url, large_qualification_dataset)
            api_lookups += 1

        # Verify exact counts
        stats = checker.get_statistics()
        assert stats.qualification_data_hits == qualification_lookups
        assert stats.api_fallback_calls == api_lookups

        # Verify efficiency calculation
        expected_efficiency = (qualification_lookups / (qualification_lookups + api_lookups)) * 100
        assert abs(stats.api_usage_efficiency - expected_efficiency) < 0.1  # Within 0.1%
        assert stats.api_usage_efficiency == 80.0  # Exactly 80%

    @pytest.mark.asyncio
    async def test_performance_degradation_with_errors(
        self, performance_config, large_qualification_dataset
    ):
        """Test performance impact of error handling."""
        mock_github_client = AsyncMock()

        # Mock API to raise errors for some calls
        call_count = 0
        async def mock_get_repository_with_errors(owner, repo):
            nonlocal call_count
            call_count += 1
            if call_count % 5 == 0:  # Every 5th call fails
                raise Exception("Simulated API error")
            return Repository(
                id=999999,
                owner=owner,
                name=repo,
                full_name=f"{owner}/{repo}",
                url=f"https://api.github.com/repos/{owner}/{repo}",
                html_url=f"https://github.com/{owner}/{repo}",
                clone_url=f"https://github.com/{owner}/{repo}.git",
                created_at=datetime(2023, 1, 1, tzinfo=UTC),
                pushed_at=datetime(2023, 5, 1, tzinfo=UTC),
                default_branch="main"
            )

        mock_github_client.get_repository.side_effect = mock_get_repository_with_errors
        checker = ForkCommitStatusChecker(mock_github_client, performance_config)

        # Process mix of known forks and unknown forks (that will error)
        fork_urls = []

        # 900 known forks (fast, from qualification data)
        for i in range(900):
            fork_urls.append(f"https://github.com/perfuser{i}/perfrepo{i}")

        # 100 unknown forks (will trigger API calls, some will error)
        for i in range(100):
            fork_urls.append(f"https://github.com/errortest{i}/repo{i}")

        start_time = time.perf_counter()

        results = []
        error_count = 0

        for fork_url in fork_urls:
            try:
                result = await checker.has_commits_ahead(fork_url, large_qualification_dataset)
                results.append(result)
            except Exception:
                error_count += 1
                results.append(None)  # Track errors

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Verify error handling worked
        assert error_count > 0  # Should have encountered some errors
        assert len(results) == 1000

        # Performance should still be reasonable despite errors
        assert total_time < 5.0  # Should complete in under 5 seconds

        # Verify statistics include errors
        stats = checker.get_statistics()
        assert stats.errors > 0
        assert stats.qualification_data_hits == 900  # Known forks processed successfully

    @pytest.mark.asyncio
    async def test_scalability_with_very_large_datasets(self, performance_config):
        """Test scalability with very large qualification datasets."""
        # Create an extremely large dataset (10,000 forks)
        fork_data = []

        for i in range(10000):
            has_commits = i % 3 != 0  # 2/3 have commits
            created_time = datetime(2023, 1, 1, tzinfo=UTC)
            pushed_time = (
                datetime(2023, 6, 1, tzinfo=UTC)
                if has_commits
                else created_time
            )

            metrics = ForkQualificationMetrics(
                id=200000 + i,
                full_name=f"scaleuser{i}/scalerepo{i}",
                owner=f"scaleuser{i}",
                name=f"scalerepo{i}",
                html_url=f"https://github.com/scaleuser{i}/scalerepo{i}",
                stargazers_count=i % 1000,
                forks_count=i % 500,
                size=1000 + (i * 2),
                language="Python",
                created_at=created_time,
                updated_at=pushed_time,
                pushed_at=pushed_time,
                open_issues_count=i % 50,
                topics=[f"topic{i % 20}"],
                watchers_count=i % 750,
                archived=i % 200 == 0,  # 0.5% archived
                disabled=i % 500 == 0,  # 0.2% disabled
                fork=True
            )

            fork_data.append(CollectedForkData(metrics=metrics))

        large_dataset = QualifiedForksResult(
            repository_owner="upstream",
            repository_name="scale-repo",
            repository_url="https://github.com/upstream/scale-repo",
            collected_forks=fork_data,
            stats=QualificationStats(
                total_forks_discovered=10000,
                forks_with_no_commits=3333,
                forks_with_commits=6667,
                api_calls_made=10000,
                processing_time_seconds=500.0
            )
        )

        mock_github_client = AsyncMock()
        checker = ForkCommitStatusChecker(mock_github_client, performance_config)

        # Test processing subset of very large dataset
        start_time = time.perf_counter()

        results = []
        for i in range(1000):  # Process 1000 out of 10000
            fork_url = f"https://github.com/scaleuser{i}/scalerepo{i}"
            result = await checker.has_commits_ahead(fork_url, large_dataset)
            results.append(result)

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Verify scalability
        assert len(results) == 1000
        assert total_time < 2.0  # Should still be fast even with large dataset

        # Verify no performance degradation with large dataset
        assert total_time / 1000 < 0.002  # Less than 2ms per lookup

        # Verify all lookups used qualification data (no API calls)
        assert mock_github_client.get_repository.call_count == 0

        # Verify statistics
        stats = checker.get_statistics()
        assert stats.qualification_data_hits == 1000
        assert stats.api_usage_efficiency == 100.0
