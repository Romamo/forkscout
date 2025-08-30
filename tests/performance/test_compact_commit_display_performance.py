"""Performance tests for compact commit display formatting changes."""

import asyncio
import time
import psutil
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from io import StringIO

import pytest
from rich.console import Console

from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.github.client import GitHubClient
from forklift.models.github import Repository
from forklift.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualificationStats,
    QualifiedForksResult,
)


class TestCompactCommitDisplayPerformance:
    """Performance tests for compact commit display formatting changes."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return AsyncMock(spec=GitHubClient)

    @pytest.fixture
    def console_with_capture(self):
        """Create a console that captures output for testing."""
        string_io = StringIO()
        console = Console(file=string_io, width=120, legacy_windows=False)
        return console, string_io

    @pytest.fixture
    def display_service(self, mock_github_client, console_with_capture):
        """Create a repository display service with output capture."""
        console, _ = console_with_capture
        return RepositoryDisplayService(mock_github_client, console)

    def create_performance_test_forks(self, count: int):
        """Create a large dataset of forks for performance testing."""
        base_time = datetime.now(timezone.utc)
        forks = []
        
        for i in range(count):
            has_commits = i % 3 != 0  # 2/3 have commits, 1/3 don't
            
            fork = Repository(
                id=i + 1,
                name=f"perf-fork-{i:04d}",
                owner=f"user{i:04d}",
                full_name=f"user{i:04d}/perf-fork-{i:04d}",
                url=f"https://api.github.com/repos/user{i:04d}/perf-fork-{i:04d}",
                html_url=f"https://github.com/user{i:04d}/perf-fork-{i:04d}",
                clone_url=f"https://github.com/user{i:04d}/perf-fork-{i:04d}.git",
                description=f"Performance test fork {i}",
                language=["Python", "JavaScript", "Go", "Rust", "Java"][i % 5],
                stars=i % 100,
                forks_count=i % 20,
                watchers_count=i % 50,
                open_issues_count=i % 10,
                size=100 + i * 5,
                topics=[f"topic-{i % 5}", f"category-{i % 3}"],
                license_name=["MIT", "Apache-2.0", "GPL-3.0", None][i % 4],
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=i % 50 == 0,  # 2% archived
                created_at=base_time - timedelta(days=i % 365),
                updated_at=base_time - timedelta(days=i % 30),
                pushed_at=base_time - timedelta(days=i % 30) if has_commits else base_time - timedelta(days=i % 365),
            )
            forks.append(fork)
        
        return forks

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_list_forks_preview_performance_with_compact_format(
        self, display_service, console_with_capture
    ):
        """Test performance of list-forks preview with compact format."""
        console, string_io = console_with_capture
        
        # Test with different fork counts
        fork_counts = [10, 50, 100, 200]
        performance_results = []
        
        for count in fork_counts:
            forks = self.create_performance_test_forks(count)
            display_service.github_client.get_repository_forks.return_value = forks
            
            # Clear previous output
            string_io.truncate(0)
            string_io.seek(0)
            
            # Measure execution time
            start_time = time.time()
            result = await display_service.list_forks_preview(f"owner/perf-repo-{count}")
            end_time = time.time()
            
            execution_time = end_time - start_time
            output_size = len(string_io.getvalue())
            
            performance_results.append({
                'fork_count': count,
                'execution_time': execution_time,
                'output_size': output_size,
                'forks_per_second': count / execution_time if execution_time > 0 else 0
            })
            
            # Verify correctness
            assert result["total_forks"] == count
            assert len(result["forks"]) == count
            
            # Performance assertions
            assert execution_time < count * 0.01  # Should be very fast (< 10ms per fork)
            assert output_size > 0
        
        # Verify performance scales reasonably
        for i in range(1, len(performance_results)):
            current = performance_results[i]
            previous = performance_results[i-1]
            
            # Time should scale roughly linearly (not exponentially)
            time_ratio = current['execution_time'] / previous['execution_time']
            count_ratio = current['fork_count'] / previous['fork_count']
            
            # Allow some overhead but not excessive scaling
            assert time_ratio < count_ratio * 2

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_fork_data_table_performance_with_compact_format(
        self, display_service, console_with_capture
    ):
        """Test performance of fork data table display with compact format."""
        console, string_io = console_with_capture
        
        # Test with moderate to large datasets
        fork_counts = [25, 75, 150]
        
        for count in fork_counts:
            forks = self.create_performance_test_forks(count)
            
            # Create qualification result
            collected_forks = []
            for fork in forks:
                metrics = ForkQualificationMetrics(
                    id=fork.id,
                    owner=fork.owner,
                    name=fork.name,
                    full_name=fork.full_name,
                    html_url=fork.html_url,
                    stargazers_count=fork.stars,
                    forks_count=fork.forks_count,
                    watchers_count=fork.watchers_count,
                    open_issues_count=fork.open_issues_count,
                    size=fork.size,
                    language=fork.language,
                    topics=fork.topics,
                    created_at=fork.created_at,
                    updated_at=fork.updated_at,
                    pushed_at=fork.pushed_at,
                    archived=fork.is_archived,
                    disabled=False,
                    fork=fork.is_fork,
                    commits_ahead_status="None" if fork.created_at >= fork.pushed_at else "Unknown",
                    can_skip_analysis=fork.created_at >= fork.pushed_at,
                )
                collected_forks.append(CollectedForkData(metrics=metrics))
            
            stats = QualificationStats(
                total_forks_discovered=count,
                forks_with_commits=count * 2 // 3,
                forks_with_no_commits=count // 3,
                archived_forks=count // 50,
                disabled_forks=0,
                processing_time_seconds=1.0,
                api_calls_made=count * 2 // 3,
                api_calls_saved=count // 3,
            )
            
            qualification_result = QualifiedForksResult(
                repository_owner="owner",
                repository_name=f"perf-repo-{count}",
                repository_url=f"https://github.com/owner/perf-repo-{count}",
                collected_forks=collected_forks,
                stats=stats,
            )
            
            # Clear previous output
            string_io.truncate(0)
            string_io.seek(0)
            
            # Measure execution time
            start_time = time.time()
            await display_service._display_fork_data_table(qualification_result)
            end_time = time.time()
            
            execution_time = end_time - start_time
            output = string_io.getvalue()
            
            # Performance assertions
            assert execution_time < count * 0.005  # Should be very fast (< 5ms per fork)
            assert len(output) > count * 50  # Should generate substantial output
            
            # Verify correctness
            assert "Commits" in output
            assert f"{count} forks" in output or str(count) in output
            
            # Verify table structure is maintained
            lines = output.split('\n')
            table_lines = [line for line in lines if "│" in line or "|" in line]
            assert len(table_lines) > count // 10  # Should have many table rows

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_detailed_fork_table_performance_with_compact_format(
        self, display_service, console_with_capture
    ):
        """Test performance of detailed fork table display with compact format."""
        console, string_io = console_with_capture
        
        # Test with different sizes
        fork_counts = [20, 60, 120]
        
        for count in fork_counts:
            forks = self.create_performance_test_forks(count)
            
            # Create detailed fork data with exact commit counts
            detailed_forks = []
            for i, fork in enumerate(forks):
                metrics = ForkQualificationMetrics(
                    id=fork.id,
                    owner=fork.owner,
                    name=fork.name,
                    full_name=fork.full_name,
                    html_url=fork.html_url,
                    stargazers_count=fork.stars,
                    forks_count=fork.forks_count,
                    watchers_count=fork.watchers_count,
                    open_issues_count=fork.open_issues_count,
                    size=fork.size,
                    language=fork.language,
                    topics=fork.topics,
                    created_at=fork.created_at,
                    updated_at=fork.updated_at,
                    pushed_at=fork.pushed_at,
                    archived=fork.is_archived,
                    disabled=False,
                    fork=fork.is_fork,
                    commits_ahead_status="None" if fork.created_at >= fork.pushed_at else "Unknown",
                    can_skip_analysis=fork.created_at >= fork.pushed_at,
                )
                
                fork_data = CollectedForkData(metrics=metrics)
                # Add exact commit counts
                if fork.created_at >= fork.pushed_at:
                    fork_data.exact_commits_ahead = 0
                else:
                    fork_data.exact_commits_ahead = (i % 20) + 1  # 1-20 commits ahead
                
                detailed_forks.append(fork_data)
            
            # Clear previous output
            string_io.truncate(0)
            string_io.seek(0)
            
            # Measure execution time
            start_time = time.time()
            await display_service._display_detailed_fork_table(
                detailed_forks,
                "owner",
                f"perf-repo-{count}",
                api_calls_made=count * 2 // 3,
                api_calls_saved=count // 3,
            )
            end_time = time.time()
            
            execution_time = end_time - start_time
            output = string_io.getvalue()
            
            # Performance assertions
            assert execution_time < count * 0.008  # Should be fast (< 8ms per fork)
            assert len(output) > count * 100  # Should generate substantial output
            
            # Verify correctness
            assert "Commits Ahead" in output
            assert "API calls" in output
            
            # Verify compact format is used
            lines = output.split('\n')
            # Should not contain verbose descriptions
            assert not any("0 commits" in line for line in lines)
            assert not any("commits ahead" in line.lower() for line in lines if "Commits Ahead" not in line)

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_memory_usage_with_large_datasets(
        self, display_service, console_with_capture
    ):
        """Test memory usage impact of compact formatting with large datasets."""
        console, string_io = console_with_capture
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Test with large dataset
        large_fork_count = 500
        forks = self.create_performance_test_forks(large_fork_count)
        display_service.github_client.get_repository_forks.return_value = forks
        
        # Measure memory during list-forks operation
        memory_before_list = process.memory_info().rss / 1024 / 1024
        
        result = await display_service.list_forks_preview("owner/large-memory-test")
        
        memory_after_list = process.memory_info().rss / 1024 / 1024
        list_memory_increase = memory_after_list - memory_before_list
        
        # Clear output buffer
        string_io.truncate(0)
        string_io.seek(0)
        
        # Test memory during fork data table operation
        collected_forks = []
        for fork in forks:
            metrics = ForkQualificationMetrics(
                id=fork.id,
                owner=fork.owner,
                name=fork.name,
                full_name=fork.full_name,
                html_url=fork.html_url,
                stargazers_count=fork.stars,
                forks_count=fork.forks_count,
                watchers_count=fork.watchers_count,
                open_issues_count=fork.open_issues_count,
                size=fork.size,
                language=fork.language,
                topics=fork.topics,
                created_at=fork.created_at,
                updated_at=fork.updated_at,
                pushed_at=fork.pushed_at,
                archived=fork.is_archived,
                disabled=False,
                fork=fork.is_fork,
                commits_ahead_status="None" if fork.created_at >= fork.pushed_at else "Unknown",
                can_skip_analysis=fork.created_at >= fork.pushed_at,
            )
            collected_forks.append(CollectedForkData(metrics=metrics))
        
        stats = QualificationStats(
            total_forks_discovered=large_fork_count,
            forks_with_commits=large_fork_count * 2 // 3,
            forks_with_no_commits=large_fork_count // 3,
            archived_forks=large_fork_count // 50,
            disabled_forks=0,
            processing_time_seconds=5.0,
            api_calls_made=large_fork_count * 2 // 3,
            api_calls_saved=large_fork_count // 3,
        )
        
        qualification_result = QualifiedForksResult(
            repository_owner="owner",
            repository_name="large-memory-test",
            repository_url="https://github.com/owner/large-memory-test",
            collected_forks=collected_forks,
            stats=stats,
        )
        
        memory_before_table = process.memory_info().rss / 1024 / 1024
        
        await display_service._display_fork_data_table(qualification_result)
        
        memory_after_table = process.memory_info().rss / 1024 / 1024
        table_memory_increase = memory_after_table - memory_before_table
        
        # Memory usage assertions
        assert list_memory_increase < 100  # Should not use more than 100MB for list operation
        assert table_memory_increase < 150  # Should not use more than 150MB for table operation
        
        # Verify operations completed successfully
        assert result["total_forks"] == large_fork_count
        assert len(result["forks"]) == large_fork_count
        
        # Verify output was generated
        output = string_io.getvalue()
        assert len(output) > large_fork_count * 50

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_display_operations_performance(
        self, display_service, console_with_capture
    ):
        """Test performance of concurrent display operations."""
        console, string_io = console_with_capture
        
        # Create different fork datasets
        small_forks = self.create_performance_test_forks(20)
        medium_forks = self.create_performance_test_forks(50)
        large_forks = self.create_performance_test_forks(100)
        
        # Mock different responses for different repos
        async def mock_get_forks(owner, repo):
            if "small" in repo:
                return small_forks
            elif "medium" in repo:
                return medium_forks
            else:
                return large_forks
        
        display_service.github_client.get_repository_forks.side_effect = mock_get_forks
        
        # Define concurrent operations
        async def list_operation(repo_name):
            return await display_service.list_forks_preview(f"owner/{repo_name}")
        
        # Measure concurrent execution time
        start_time = time.time()
        
        results = await asyncio.gather(
            list_operation("small-repo"),
            list_operation("medium-repo"),
            list_operation("large-repo"),
            return_exceptions=True
        )
        
        end_time = time.time()
        concurrent_time = end_time - start_time
        
        # Verify all operations completed successfully
        assert len(results) == 3
        for result in results:
            assert not isinstance(result, Exception)
            assert "total_forks" in result
        
        # Measure sequential execution time for comparison
        display_service.github_client.get_repository_forks.side_effect = None
        
        start_time = time.time()
        
        display_service.github_client.get_repository_forks.return_value = small_forks
        await display_service.list_forks_preview("owner/small-repo-seq")
        
        display_service.github_client.get_repository_forks.return_value = medium_forks
        await display_service.list_forks_preview("owner/medium-repo-seq")
        
        display_service.github_client.get_repository_forks.return_value = large_forks
        await display_service.list_forks_preview("owner/large-repo-seq")
        
        end_time = time.time()
        sequential_time = end_time - start_time
        
        # Performance assertions
        assert concurrent_time < sequential_time * 1.5  # Concurrent should not be much slower
        assert concurrent_time < 5.0  # Should complete within reasonable time
        
        # Verify results are correct
        assert results[0]["total_forks"] == 20
        assert results[1]["total_forks"] == 50
        assert results[2]["total_forks"] == 100

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_output_generation_performance_comparison(
        self, display_service, console_with_capture
    ):
        """Test performance comparison between compact and verbose formatting."""
        console, string_io = console_with_capture
        
        # Create test dataset
        test_forks = self.create_performance_test_forks(100)
        display_service.github_client.get_repository_forks.return_value = test_forks
        
        # Test compact format performance (current implementation)
        start_time = time.time()
        result = await display_service.list_forks_preview("owner/compact-test")
        compact_time = time.time() - start_time
        compact_output = string_io.getvalue()
        compact_output_size = len(compact_output)
        
        # Clear output
        string_io.truncate(0)
        string_io.seek(0)
        
        # Simulate verbose format by creating detailed output
        # (This is a simulation since we don't have verbose format implemented)
        start_time = time.time()
        
        # Create a more verbose output simulation
        verbose_lines = []
        for fork in result["forks"]:
            verbose_lines.append(f"Fork: {fork.name}")
            verbose_lines.append(f"  Owner: {fork.owner}")
            verbose_lines.append(f"  Stars: {fork.stars}")
            verbose_lines.append(f"  Commits Ahead: {fork.commits_ahead}")
            verbose_lines.append(f"  Last Push: {fork.last_push_date}")
            verbose_lines.append(f"  Activity: {fork.activity_status}")
            verbose_lines.append("")  # Empty line
        
        verbose_output = "\n".join(verbose_lines)
        verbose_time = time.time() - start_time
        verbose_output_size = len(verbose_output)
        
        # Performance comparison assertions
        assert compact_time < 2.0  # Compact format should be fast
        assert verbose_time < 1.0  # Verbose simulation should also be fast
        
        # Output size comparison
        # Compact format should be more efficient in terms of output size
        # while maintaining readability
        assert compact_output_size > 0
        assert verbose_output_size > compact_output_size  # Verbose should be larger
        
        # Verify compact format maintains essential information
        assert "Commits" in compact_output
        assert str(result["total_forks"]) in compact_output
        
        # Verify table structure is more efficient than verbose listing
        compact_lines = compact_output.split('\n')
        verbose_lines_count = len(verbose_lines)
        compact_lines_count = len([line for line in compact_lines if line.strip()])
        
        # Compact format should use fewer lines for the same information
        assert compact_lines_count < verbose_lines_count

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_formatting_performance_with_special_characters(
        self, display_service, console_with_capture
    ):
        """Test performance impact of formatting with special characters and Unicode."""
        console, string_io = console_with_capture
        
        base_time = datetime.now(timezone.utc)
        
        # Create forks with special characters and Unicode
        special_char_forks = []
        for i in range(50):
            fork = Repository(
                id=i + 1,
                name=f"fork-{i}-测试-🚀-{i % 10}",
                owner=f"用户{i}-@domain.com",
                full_name=f"用户{i}-@domain.com/fork-{i}-测试-🚀-{i % 10}",
                url=f"https://api.github.com/repos/用户{i}-@domain.com/fork-{i}-测试-🚀-{i % 10}",
                html_url=f"https://github.com/用户{i}-@domain.com/fork-{i}-测试-🚀-{i % 10}",
                clone_url=f"https://github.com/用户{i}-@domain.com/fork-{i}-测试-🚀-{i % 10}.git",
                description=f"Fork with Unicode: 测试 🚀 ñáéíóú !@#$%^&*()_+-=[]{{}}|;':\",./<>? {i}",
                language=["Python", "JavaScript", "Go"][i % 3],
                stars=i % 100,
                forks_count=i % 20,
                watchers_count=i % 50,
                open_issues_count=i % 10,
                size=100 + i * 10,
                topics=[f"测试-{i % 3}", f"🚀-{i % 2}"],
                license_name="MIT" if i % 2 == 0 else None,
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time - timedelta(days=i),
                updated_at=base_time - timedelta(days=i // 2),
                pushed_at=base_time - timedelta(days=i // 2) if i % 3 != 0 else base_time - timedelta(days=i),
            )
            special_char_forks.append(fork)
        
        display_service.github_client.get_repository_forks.return_value = special_char_forks
        
        # Measure performance with special characters
        start_time = time.time()
        result = await display_service.list_forks_preview("owner/unicode-perf-test")
        end_time = time.time()
        
        execution_time = end_time - start_time
        output = string_io.getvalue()
        
        # Performance assertions
        assert execution_time < 1.0  # Should handle Unicode efficiently
        assert result["total_forks"] == 50
        assert len(result["forks"]) == 50
        
        # Verify Unicode characters are handled correctly
        assert "测试" in output or "unicode" in output.lower()
        assert len(output) > 1000  # Should generate substantial output
        
        # Verify no encoding errors
        assert "UnicodeError" not in output
        assert "Error" not in output
        
        # Verify table structure is maintained with special characters
        lines = output.split('\n')
        table_lines = [line for line in lines if "│" in line or "|" in line]
        assert len(table_lines) > 10  # Should have table structure