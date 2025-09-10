"""Performance tests for fork data collection system measuring API call reduction and efficiency."""

import asyncio
import time
from unittest.mock import AsyncMock

import pytest

from forkscout.analysis.fork_data_collection_engine import ForkDataCollectionEngine
from forkscout.github.fork_list_processor import ForkListProcessor


class TestForkDataCollectionPerformance:
    """Performance tests measuring API call reduction and processing efficiency."""

    @pytest.fixture
    def mock_github_client(self):
        """Create mock GitHub client for performance tests."""
        return AsyncMock()

    @pytest.fixture
    def processor(self, mock_github_client):
        """Create processor with mock client."""
        return ForkListProcessor(mock_github_client)

    @pytest.fixture
    def engine(self):
        """Create data collection engine."""
        return ForkDataCollectionEngine()

    def create_mock_fork_data(self, count: int, commits_ahead_ratio: float = 0.7) -> list[dict]:
        """Create mock fork data for performance testing."""
        forks = []
        commits_ahead_count = int(count * commits_ahead_ratio)

        for i in range(count):
            # Determine if this fork has commits ahead
            has_commits = i < commits_ahead_count

            fork = {
                "id": 1000000 + i,
                "name": f"performance-fork-{i}",
                "full_name": f"user{i}/performance-fork-{i}",
                "owner": {"login": f"user{i}"},
                "html_url": f"https://github.com/user{i}/performance-fork-{i}",
                "stargazers_count": i % 50,  # 0-49 stars
                "forks_count": i % 10,  # 0-9 forks
                "watchers_count": i % 30,  # 0-29 watchers
                "size": 10000 + (i * 100),  # Varying sizes
                "language": "Python" if i % 3 == 0 else "JavaScript",
                "topics": ["performance", "testing"] if i % 2 == 0 else [],
                "open_issues_count": i % 20,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": f"2024-01-{(i % 28) + 1:02d}T00:00:00Z",
                "pushed_at": f"2024-01-{(i % 28) + 2:02d}T00:00:00Z" if has_commits else "2023-01-01T00:00:00Z",
                "archived": i % 100 == 0,  # 1% archived
                "disabled": i % 200 == 0,  # 0.5% disabled
                "fork": True,
                "license": {"key": "mit", "name": "MIT License"} if i % 4 == 0 else None,
                "description": f"Performance test fork {i}" if i % 5 == 0 else None,
                "homepage": f"https://user{i}.github.io" if i % 20 == 0 else None,
                "default_branch": "main" if i % 2 == 0 else "master",
            }
            forks.append(fork)

        return forks

    @pytest.mark.performance
    def test_api_call_reduction_small_dataset(self, processor, engine, mock_github_client):
        """Test API call reduction with small dataset (100 forks)."""
        fork_count = 100
        mock_forks = self.create_mock_fork_data(fork_count)

        # Mock single page response - return empty list on second call to end pagination
        mock_github_client.get.side_effect = [mock_forks, []]

        async def run_test():
            start_time = time.time()
            result = await processor.collect_and_process_forks("owner", "repo")
            processing_time = time.time() - start_time
            return result, processing_time

        result, processing_time = asyncio.run(run_test())

        # Verify API efficiency
        assert result.stats.total_forks_discovered == fork_count
        assert result.stats.api_calls_made == 1  # Single page (empty response doesn't count)
        assert result.stats.api_calls_saved == fork_count  # Each fork would need individual call
        expected_efficiency = (fork_count / (1 + fork_count)) * 100
        assert abs(result.stats.efficiency_percentage - expected_efficiency) < 0.1

        # Verify performance
        assert processing_time < 5.0  # Should complete quickly
        forks_per_second = fork_count / processing_time
        assert forks_per_second > 20  # Should process at least 20 forks per second

        print("Small dataset performance:")
        print(f"  Forks: {fork_count}")
        print(f"  Processing time: {processing_time:.3f}s")
        print(f"  Forks per second: {forks_per_second:.1f}")
        print(f"  API calls made: {result.stats.api_calls_made}")
        print(f"  API calls saved: {result.stats.api_calls_saved}")
        print(f"  Efficiency: {result.stats.efficiency_percentage:.1f}%")

    @pytest.mark.performance
    def test_api_call_reduction_medium_dataset(self, processor, engine, mock_github_client):
        """Test API call reduction with medium dataset (500 forks)."""
        fork_count = 500
        mock_forks = self.create_mock_fork_data(fork_count)

        # Mock paginated responses (5 pages of 100 each, then empty to end pagination)
        pages = [mock_forks[i:i+100] for i in range(0, fork_count, 100)]
        pages.append([])  # Empty page to end pagination
        mock_github_client.get.side_effect = pages

        async def run_test():
            start_time = time.time()
            result = await processor.collect_and_process_forks("owner", "repo")
            processing_time = time.time() - start_time
            return result, processing_time

        result, processing_time = asyncio.run(run_test())

        # Verify API efficiency
        assert result.stats.total_forks_discovered == fork_count
        assert result.stats.api_calls_made == 5  # Five pages (empty response doesn't count)
        assert result.stats.api_calls_saved == fork_count
        expected_efficiency = (fork_count / (5 + fork_count)) * 100
        assert abs(result.stats.efficiency_percentage - expected_efficiency) < 0.1

        # Verify performance
        assert processing_time < 10.0  # Should complete within 10 seconds
        forks_per_second = fork_count / processing_time
        assert forks_per_second > 50  # Should process at least 50 forks per second

        print("Medium dataset performance:")
        print(f"  Forks: {fork_count}")
        print(f"  Processing time: {processing_time:.3f}s")
        print(f"  Forks per second: {forks_per_second:.1f}")
        print(f"  API calls made: {result.stats.api_calls_made}")
        print(f"  API calls saved: {result.stats.api_calls_saved}")
        print(f"  Efficiency: {result.stats.efficiency_percentage:.1f}%")

    @pytest.mark.performance
    def test_api_call_reduction_large_dataset(self, processor, engine, mock_github_client):
        """Test API call reduction with large dataset (2000 forks)."""
        fork_count = 2000
        mock_forks = self.create_mock_fork_data(fork_count)

        # Mock paginated responses (20 pages of 100 each, then empty to end pagination)
        pages = [mock_forks[i:i+100] for i in range(0, fork_count, 100)]
        pages.append([])  # Empty page to end pagination
        mock_github_client.get.side_effect = pages

        async def run_test():
            start_time = time.time()
            result = await processor.collect_and_process_forks("owner", "repo")
            processing_time = time.time() - start_time
            return result, processing_time

        result, processing_time = asyncio.run(run_test())

        # Verify API efficiency
        assert result.stats.total_forks_discovered == fork_count
        assert result.stats.api_calls_made == 20  # Twenty pages (empty response doesn't count)
        assert result.stats.api_calls_saved == fork_count
        expected_efficiency = (fork_count / (20 + fork_count)) * 100
        assert abs(result.stats.efficiency_percentage - expected_efficiency) < 0.1

        # Verify performance
        assert processing_time < 30.0  # Should complete within 30 seconds
        forks_per_second = fork_count / processing_time
        assert forks_per_second > 100  # Should process at least 100 forks per second

        print("Large dataset performance:")
        print(f"  Forks: {fork_count}")
        print(f"  Processing time: {processing_time:.3f}s")
        print(f"  Forks per second: {forks_per_second:.1f}")
        print(f"  API calls made: {result.stats.api_calls_made}")
        print(f"  API calls saved: {result.stats.api_calls_saved}")
        print(f"  Efficiency: {result.stats.efficiency_percentage:.1f}%")

    @pytest.mark.performance
    def test_processing_efficiency_by_commits_ratio(self, engine):
        """Test processing efficiency with different commits ahead ratios."""
        fork_count = 1000
        ratios_to_test = [0.1, 0.3, 0.5, 0.7, 0.9]  # 10% to 90% have commits

        results = []

        for ratio in ratios_to_test:
            mock_forks = self.create_mock_fork_data(fork_count, commits_ahead_ratio=ratio)

            start_time = time.time()
            collected_forks = engine.collect_fork_data_from_list(mock_forks)
            processing_time = time.time() - start_time

            # Create qualification result
            result = engine.create_qualification_result(
                repository_owner="owner",
                repository_name="repo",
                collected_forks=collected_forks,
                processing_time_seconds=processing_time,
                api_calls_made=10,  # Simulated
                api_calls_saved=fork_count,
            )

            results.append({
                "ratio": ratio,
                "processing_time": processing_time,
                "forks_per_second": fork_count / processing_time,
                "forks_with_commits": result.stats.forks_with_commits,
                "forks_no_commits": result.stats.forks_with_no_commits,
            })

            # Verify processing is consistent regardless of ratio
            assert processing_time < 5.0  # Should be fast for all ratios
            assert result.stats.total_forks_discovered == fork_count

        print("Processing efficiency by commits ratio:")
        for result in results:
            print(f"  {result['ratio']:.0%} commits: {result['processing_time']:.3f}s, "
                  f"{result['forks_per_second']:.1f} forks/sec, "
                  f"{result['forks_with_commits']} with commits, "
                  f"{result['forks_no_commits']} no commits")

    @pytest.mark.performance
    def test_memory_efficiency_large_dataset(self, engine):
        """Test memory efficiency with large dataset."""
        import os

        import psutil

        fork_count = 5000
        mock_forks = self.create_mock_fork_data(fork_count)

        # Measure memory before processing
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        start_time = time.time()
        collected_forks = engine.collect_fork_data_from_list(mock_forks)
        processing_time = time.time() - start_time

        # Measure memory after processing
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = memory_after - memory_before

        # Verify results
        assert len(collected_forks) == fork_count
        assert processing_time < 15.0  # Should complete within 15 seconds

        # Memory usage should be reasonable (less than 100MB increase for 5000 forks)
        assert memory_increase < 100.0

        print("Memory efficiency test:")
        print(f"  Forks processed: {fork_count}")
        print(f"  Processing time: {processing_time:.3f}s")
        print(f"  Memory before: {memory_before:.1f} MB")
        print(f"  Memory after: {memory_after:.1f} MB")
        print(f"  Memory increase: {memory_increase:.1f} MB")
        print(f"  Memory per fork: {memory_increase / fork_count * 1024:.1f} KB")

    @pytest.mark.performance
    def test_concurrent_processing_simulation(self, processor, mock_github_client):
        """Test performance under simulated concurrent processing."""
        fork_count = 1000
        mock_forks = self.create_mock_fork_data(fork_count)

        # Mock paginated responses with empty page to end pagination
        pages = [mock_forks[i:i+100] for i in range(0, fork_count, 100)]
        pages.append([])  # Empty page to end pagination
        mock_github_client.get.side_effect = pages

        async def process_repository(repo_name):
            """Simulate processing a single repository."""
            start_time = time.time()
            result = await processor.collect_and_process_forks("owner", repo_name)
            processing_time = time.time() - start_time
            return result, processing_time

        async def run_concurrent_test():
            """Run multiple repository processing tasks concurrently."""
            # Simulate processing 5 repositories concurrently
            tasks = [process_repository(f"repo-{i}") for i in range(5)]

            start_time = time.time()
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time

            return results, total_time

        # Mock to return first page then empty for each repository
        call_count = 0
        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 1:  # Odd calls return data
                return pages[0] if pages else []
            else:  # Even calls return empty to end pagination
                return []

        mock_github_client.get.side_effect = mock_get

        results, total_time = asyncio.run(run_concurrent_test())

        # Verify concurrent processing
        assert len(results) == 5
        assert total_time < 20.0  # Should complete within 20 seconds

        # Calculate aggregate statistics
        total_forks_processed = sum(result[0].stats.total_forks_discovered for result, _ in results)
        average_processing_time = sum(processing_time for _, processing_time in results) / len(results)
        aggregate_forks_per_second = total_forks_processed / total_time

        print("Concurrent processing simulation:")
        print("  Repositories: 5")
        print(f"  Total forks processed: {total_forks_processed}")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Average processing time per repo: {average_processing_time:.3f}s")
        print(f"  Aggregate forks per second: {aggregate_forks_per_second:.1f}")

    @pytest.mark.performance
    def test_filtering_performance_impact(self, engine):
        """Test performance impact of different filtering operations."""
        fork_count = 2000
        mock_forks = self.create_mock_fork_data(fork_count)

        # Collect all fork data first
        start_time = time.time()
        collected_forks = engine.collect_fork_data_from_list(mock_forks)
        collection_time = time.time() - start_time

        filtering_results = {}

        # Test different filtering operations
        operations = [
            ("exclude_archived_and_disabled", lambda: engine.exclude_archived_and_disabled(collected_forks)),
            ("exclude_no_commits_ahead", lambda: engine.exclude_no_commits_ahead(collected_forks)),
            ("organize_forks_by_status", lambda: engine.organize_forks_by_status(collected_forks)),
        ]

        for operation_name, operation_func in operations:
            start_time = time.time()
            result = operation_func()
            operation_time = time.time() - start_time

            filtering_results[operation_name] = {
                "time": operation_time,
                "forks_per_second": fork_count / operation_time if operation_time > 0 else float("inf"),
                "result_size": len(result) if isinstance(result, list) else sum(len(r) for r in result),
            }

            # Verify performance
            assert operation_time < 1.0  # All filtering operations should be very fast

        print("Filtering performance impact:")
        print(f"  Collection time: {collection_time:.3f}s ({fork_count / collection_time:.1f} forks/sec)")
        for operation, stats in filtering_results.items():
            print(f"  {operation}: {stats['time']:.3f}s ({stats['forks_per_second']:.1f} forks/sec)")

    @pytest.mark.performance
    def test_scalability_analysis(self, processor, engine, mock_github_client):
        """Test scalability with increasing dataset sizes."""
        dataset_sizes = [100, 500, 1000, 2000, 5000]
        scalability_results = []

        for size in dataset_sizes:
            mock_forks = self.create_mock_fork_data(size)

            # Mock paginated responses with empty page to end pagination
            pages = [mock_forks[i:i+100] for i in range(0, size, 100)]
            pages.append([])  # Empty page to end pagination
            mock_github_client.get.side_effect = pages

            async def run_scalability_test():
                start_time = time.time()
                result = await processor.collect_and_process_forks("owner", "repo")
                processing_time = time.time() - start_time
                return result, processing_time

            result, processing_time = asyncio.run(run_scalability_test())

            scalability_results.append({
                "size": size,
                "processing_time": processing_time,
                "forks_per_second": size / processing_time,
                "api_calls_made": result.stats.api_calls_made,
                "efficiency_percentage": result.stats.efficiency_percentage,
            })

            # Verify scalability
            assert processing_time < size * 0.01  # Should scale linearly or better
            assert result.stats.efficiency_percentage > 90  # Should maintain high efficiency

        print("Scalability analysis:")
        print(f"{'Size':<6} {'Time(s)':<8} {'Forks/s':<8} {'API Calls':<10} {'Efficiency':<10}")
        print("-" * 50)
        for result in scalability_results:
            print(f"{result['size']:<6} {result['processing_time']:<8.3f} "
                  f"{result['forks_per_second']:<8.1f} {result['api_calls_made']:<10} "
                  f"{result['efficiency_percentage']:<10.1f}%")

    @pytest.mark.performance
    def test_error_handling_performance_impact(self, engine):
        """Test performance impact of error handling with mixed valid/invalid data."""
        fork_count = 1000
        valid_forks = self.create_mock_fork_data(int(fork_count * 0.8))  # 80% valid

        # Create invalid forks (20% invalid)
        invalid_forks = [
            None,  # Null data
            {},  # Empty data
            {"invalid": "structure"},  # Invalid structure
            {"id": "not_a_number"},  # Invalid field type
        ] * (fork_count // 20)  # Repeat to get desired count

        mixed_data = valid_forks + invalid_forks[:fork_count - len(valid_forks)]

        # Shuffle to mix valid and invalid data
        import random
        random.shuffle(mixed_data)

        start_time = time.time()
        collected_forks = engine.collect_fork_data_from_list(mixed_data)
        processing_time = time.time() - start_time

        # Verify error handling doesn't significantly impact performance
        assert processing_time < 10.0  # Should still be reasonably fast
        assert len(collected_forks) == len(valid_forks)  # Only valid forks processed

        valid_forks_per_second = len(collected_forks) / processing_time
        total_items_per_second = len(mixed_data) / processing_time

        print("Error handling performance impact:")
        print(f"  Total items: {len(mixed_data)}")
        print(f"  Valid forks: {len(collected_forks)}")
        print(f"  Invalid items: {len(mixed_data) - len(collected_forks)}")
        print(f"  Processing time: {processing_time:.3f}s")
        print(f"  Valid forks per second: {valid_forks_per_second:.1f}")
        print(f"  Total items per second: {total_items_per_second:.1f}")

    @pytest.mark.performance
    def test_benchmark_against_individual_api_calls(self, processor, mock_github_client):
        """Benchmark fork list approach against individual API calls approach."""
        fork_count = 500
        mock_forks = self.create_mock_fork_data(fork_count)

        # Test 1: Fork list approach (current implementation)
        pages = [mock_forks[i:i+100] for i in range(0, fork_count, 100)]
        mock_github_client.get.side_effect = pages

        async def fork_list_approach():
            start_time = time.time()
            result = await processor.collect_and_process_forks("owner", "repo")
            processing_time = time.time() - start_time
            return result, processing_time

        list_result, list_time = asyncio.run(fork_list_approach())

        # Test 2: Simulated individual API calls approach
        mock_github_client.get.side_effect = None
        mock_github_client.get.return_value = {"some": "individual_data"}

        async def individual_calls_approach():
            start_time = time.time()
            # Simulate individual API calls for each fork
            for _ in range(fork_count):
                await mock_github_client.get("individual_call")
            processing_time = time.time() - start_time
            return processing_time

        individual_time = asyncio.run(individual_calls_approach())

        # Calculate improvement
        time_improvement = individual_time / list_time if list_time > 0 else float("inf")
        api_calls_reduction = (fork_count - list_result.stats.api_calls_made) / fork_count * 100

        print("Benchmark: Fork list vs Individual API calls:")
        print(f"  Fork count: {fork_count}")
        print(f"  Fork list approach: {list_time:.3f}s, {list_result.stats.api_calls_made} API calls")
        print(f"  Individual calls approach: {individual_time:.3f}s, {fork_count} API calls")
        print(f"  Time improvement: {time_improvement:.1f}x faster")
        print(f"  API calls reduction: {api_calls_reduction:.1f}%")
        print(f"  Efficiency: {list_result.stats.efficiency_percentage:.1f}%")

        # Verify significant improvement
        assert time_improvement > 2.0  # Should be at least 2x faster
        assert api_calls_reduction > 90.0  # Should reduce API calls by >90%
