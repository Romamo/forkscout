"""Performance tests for CSV export functionality."""

import csv
import io
import time
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch

import pytest

from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.github.client import GitHubClient
from forklift.models.analysis import ForkPreviewItem, ForksPreview
from forklift.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
)
from forklift.models.github import RecentCommit
from forklift.reporting.csv_exporter import CSVExportConfig, CSVExporter


class TestCSVExportPerformance:
    """Performance tests for CSV export with large datasets."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return AsyncMock(spec=GitHubClient)

    def create_large_fork_dataset(self, size: int) -> list[CollectedForkData]:
        """Create a large dataset of fork data for performance testing."""
        forks = []
        
        for i in range(size):
            metrics = ForkQualificationMetrics(
                id=1000000 + i,
                name=f"test-repo-{i}",
                full_name=f"user{i}/test-repo-{i}",
                owner=f"user{i}",
                html_url=f"https://github.com/user{i}/test-repo-{i}",
                stargazers_count=i % 1000,  # Vary stars from 0-999
                forks_count=i % 100,        # Vary forks from 0-99
                watchers_count=i % 50,      # Vary watchers from 0-49
                size=1000 + (i % 5000),     # Vary size from 1000-6000 KB
                language="Python" if i % 3 == 0 else "JavaScript" if i % 3 == 1 else "Go",
                topics=[f"topic{j}" for j in range(i % 5)],  # 0-4 topics
                open_issues_count=i % 20,   # 0-19 open issues
                created_at=datetime(2023, 1 + (i % 12), 1 + (i % 28), tzinfo=UTC),
                updated_at=datetime(2023, 6 + (i % 6), 1 + (i % 28), tzinfo=UTC),
                pushed_at=datetime(2023, 6 + (i % 6), 2 + (i % 28), tzinfo=UTC),
                archived=i % 100 == 0,      # 1% archived
                disabled=False,
                fork=True,
                license_key="mit" if i % 2 == 0 else "apache-2.0",
                license_name="MIT License" if i % 2 == 0 else "Apache License 2.0",
                description=f"Test repository {i} with some description text that varies in length",
                homepage=f"https://user{i}.github.io/test-repo-{i}" if i % 10 == 0 else None,
                default_branch="main" if i % 4 != 0 else "master"
            )
            
            fork_data = CollectedForkData(metrics=metrics)
            # Add exact commit counts for some forks
            if i % 3 == 0:
                fork_data.exact_commits_ahead = i % 50
            
            forks.append(fork_data)
        
        return forks

    def create_large_commit_dataset(self, fork_urls: list[str], commits_per_fork: int) -> dict[str, list[RecentCommit]]:
        """Create large commit dataset for performance testing."""
        commit_data = {}
        
        for url in fork_urls:
            commits = []
            for i in range(commits_per_fork):
                commit = RecentCommit(
                    short_sha=f"abc{i:04d}",
                    message=f"Commit {i}: Add feature or fix bug with detailed description that might be quite long",
                    date=datetime(2024, 1, 1 + (i % 30), 10 + (i % 14), i % 60, tzinfo=UTC)
                )
                commits.append(commit)
            commit_data[url] = commits
        
        return commit_data

    @pytest.mark.performance
    def test_csv_export_1000_forks_performance(self):
        """Test CSV export performance with 1000 forks."""
        # Create large dataset
        fork_data = self.create_large_fork_dataset(1000)
        
        # Convert to ForksPreview format
        preview_items = []
        for fork in fork_data:
            metrics = fork.metrics
            item = ForkPreviewItem(
                name=metrics.name,
                owner=metrics.owner,
                stars=metrics.stargazers_count,
                last_push_date=metrics.pushed_at,
                fork_url=metrics.html_url,
                activity_status="Active" if metrics.commits_ahead_status == "Has commits" else "Stale",
                commits_ahead=str(getattr(fork, 'exact_commits_ahead', 0)) if hasattr(fork, 'exact_commits_ahead') else "Unknown"
            )
            preview_items.append(item)
        
        preview = ForksPreview(total_forks=len(preview_items), forks=preview_items)
        
        # Test basic export performance
        exporter = CSVExporter()
        
        start_time = time.time()
        csv_output = exporter.export_forks_preview(preview)
        end_time = time.time()
        
        export_time = end_time - start_time
        
        # Performance assertions
        assert export_time < 5.0, f"Export took {export_time:.2f}s, expected < 5.0s"
        
        # Verify output correctness
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        assert len(rows) == 1000
        
        # Verify output size is reasonable
        output_size_mb = len(csv_output.encode('utf-8')) / (1024 * 1024)
        assert output_size_mb < 10, f"Output size {output_size_mb:.2f}MB, expected < 10MB"

    @pytest.mark.performance
    def test_csv_export_5000_forks_performance(self):
        """Test CSV export performance with 5000 forks (large repository scenario)."""
        # Create very large dataset
        fork_data = self.create_large_fork_dataset(5000)
        
        # Convert to ForksPreview format
        preview_items = []
        for fork in fork_data:
            metrics = fork.metrics
            item = ForkPreviewItem(
                name=metrics.name,
                owner=metrics.owner,
                stars=metrics.stargazers_count,
                last_push_date=metrics.pushed_at,
                fork_url=metrics.html_url,
                activity_status="Active" if metrics.commits_ahead_status == "Has commits" else "Stale",
                commits_ahead="Unknown"
            )
            preview_items.append(item)
        
        preview = ForksPreview(total_forks=len(preview_items), forks=preview_items)
        
        # Test with minimal configuration for best performance
        config = CSVExportConfig(
            include_commits=False,
            detail_mode=False,
            include_explanations=False,
            include_urls=True
        )
        exporter = CSVExporter(config)
        
        start_time = time.time()
        csv_output = exporter.export_forks_preview(preview)
        end_time = time.time()
        
        export_time = end_time - start_time
        
        # Performance assertions for large dataset
        assert export_time < 15.0, f"Export took {export_time:.2f}s, expected < 15.0s"
        
        # Verify output correctness
        lines = csv_output.count('\n')
        assert lines >= 5000, f"Expected at least 5000 lines, got {lines}"
        
        # Memory usage should be reasonable
        output_size_mb = len(csv_output.encode('utf-8')) / (1024 * 1024)
        assert output_size_mb < 50, f"Output size {output_size_mb:.2f}MB, expected < 50MB"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_csv_export_with_commits_performance(self, mock_github_client):
        """Test CSV export performance with commit data included."""
        # Create moderate dataset with commits
        fork_data = self.create_large_fork_dataset(500)
        
        # Create commit data for forks with commits ahead
        fork_urls = [fork.metrics.html_url for fork in fork_data if fork.metrics.commits_ahead_status == "Has commits"]
        commit_data = self.create_large_commit_dataset(fork_urls[:100], 10)  # Limit to 100 forks with 10 commits each
        
        display_service = RepositoryDisplayService(mock_github_client)
        
        # Capture output
        captured_output = io.StringIO()
        
        with patch("sys.stdout", captured_output):
            with patch.object(display_service, "_fetch_raw_commits_for_csv") as mock_fetch_commits:
                mock_fetch_commits.return_value = commit_data
                
                table_context = {
                    "owner": "testowner",
                    "repo": "testrepo",
                    "has_exact_counts": False,
                    "mode": "standard"
                }
                
                start_time = time.time()
                
                await display_service._export_csv_data(
                    fork_data,
                    table_context,
                    show_commits=10,
                    force_all_commits=False
                )
                
                end_time = time.time()
        
        export_time = end_time - start_time
        
        # Performance assertions
        assert export_time < 10.0, f"Export with commits took {export_time:.2f}s, expected < 10.0s"
        
        # Verify output
        csv_output = captured_output.getvalue()
        assert len(csv_output) > 0
        assert "recent_commits" in csv_output

    @pytest.mark.performance
    def test_csv_export_memory_efficiency(self):
        """Test that CSV export is memory efficient with large datasets."""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large dataset
        fork_data = self.create_large_fork_dataset(2000)
        
        # Convert to ForksPreview format
        preview_items = []
        for fork in fork_data:
            metrics = fork.metrics
            item = ForkPreviewItem(
                name=metrics.name,
                owner=metrics.owner,
                stars=metrics.stargazers_count,
                last_push_date=metrics.pushed_at,
                fork_url=metrics.html_url,
                activity_status="Active",
                commits_ahead="3",
                recent_commits="2024-01-15 abc1234 Fix bug; 2024-01-14 def5678 Add feature; 2024-01-13 ghi9012 Update docs"
            )
            preview_items.append(item)
        
        preview = ForksPreview(total_forks=len(preview_items), forks=preview_items)
        
        # Export CSV
        config = CSVExportConfig(include_commits=True, detail_mode=True)
        exporter = CSVExporter(config)
        
        csv_output = exporter.export_forks_preview(preview)
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable
        assert memory_increase < 200, f"Memory increased by {memory_increase:.2f}MB, expected < 200MB"
        
        # Verify output was generated
        assert len(csv_output) > 0
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        assert len(rows) == 2000

    @pytest.mark.performance
    def test_csv_export_with_unicode_performance(self):
        """Test CSV export performance with Unicode-heavy data."""
        # Create dataset with lots of Unicode characters
        fork_data = []
        
        unicode_strings = [
            "测试仓库",
            "тестовый репозиторий", 
            "مستودع الاختبار",
            "テストリポジトリ",
            "저장소 테스트",
            "Δοκιμαστικό αποθετήριο",
            "Repositório de teste",
            "Dépôt de test",
            "Repositorio de prueba",
            "Test-Repository"
        ]
        
        for i in range(1000):
            unicode_name = unicode_strings[i % len(unicode_strings)]
            unicode_owner = f"用户{i}"
            unicode_desc = f"这是一个测试仓库 🚀 with émojis and spëcial chars ñáéíóú {i}"
            
            item = ForkPreviewItem(
                name=f"{unicode_name}-{i}",
                owner=unicode_owner,
                stars=i % 100,
                last_push_date=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
                fork_url=f"https://github.com/{unicode_owner}/{unicode_name}-{i}",
                activity_status="活跃" if i % 2 == 0 else "不活跃",
                commits_ahead=str(i % 10),
                recent_commits=f"2024-01-15 abc{i:04d} 修复错误 🐛; 2024-01-14 def{i:04d} 添加功能 ✨"
            )
            fork_data.append(item)
        
        preview = ForksPreview(total_forks=len(fork_data), forks=fork_data)
        
        # Test export performance with Unicode
        config = CSVExportConfig(include_commits=True)
        exporter = CSVExporter(config)
        
        start_time = time.time()
        csv_output = exporter.export_forks_preview(preview)
        end_time = time.time()
        
        export_time = end_time - start_time
        
        # Performance should not be significantly impacted by Unicode
        assert export_time < 8.0, f"Unicode export took {export_time:.2f}s, expected < 8.0s"
        
        # Verify Unicode is preserved
        assert "测试仓库" in csv_output
        assert "用户" in csv_output
        assert "🚀" in csv_output
        assert "修复错误" in csv_output
        
        # Verify output is valid CSV
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        assert len(rows) == 1000

    @pytest.mark.performance
    def test_csv_export_concurrent_performance(self):
        """Test CSV export performance under concurrent usage."""
        import threading
        import concurrent.futures
        
        def export_csv_task(task_id: int) -> tuple[int, float]:
            """Export CSV in a separate thread."""
            # Create dataset for this task
            fork_data = self.create_large_fork_dataset(200)
            
            preview_items = []
            for fork in fork_data:
                metrics = fork.metrics
                item = ForkPreviewItem(
                    name=f"{metrics.name}-task{task_id}",
                    owner=f"{metrics.owner}-task{task_id}",
                    stars=metrics.stargazers_count,
                    last_push_date=metrics.pushed_at,
                    fork_url=f"{metrics.html_url}-task{task_id}",
                    activity_status="Active",
                    commits_ahead="3"
                )
                preview_items.append(item)
            
            preview = ForksPreview(total_forks=len(preview_items), forks=preview_items)
            
            # Export CSV
            exporter = CSVExporter()
            
            start_time = time.time()
            csv_output = exporter.export_forks_preview(preview)
            end_time = time.time()
            
            # Verify output
            reader = csv.DictReader(io.StringIO(csv_output))
            rows = list(reader)
            assert len(rows) == 200
            
            return task_id, end_time - start_time
        
        # Run multiple concurrent exports
        num_threads = 5
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(export_csv_task, i) for i in range(num_threads)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # All tasks should complete successfully
        assert len(results) == num_threads
        
        # Total time should be reasonable for concurrent execution
        assert total_time < 15.0, f"Concurrent export took {total_time:.2f}s, expected < 15.0s"
        
        # Individual task times should be reasonable
        for task_id, task_time in results:
            assert task_time < 10.0, f"Task {task_id} took {task_time:.2f}s, expected < 10.0s"

    @pytest.mark.performance
    def test_csv_export_streaming_performance(self):
        """Test CSV export performance with streaming-like usage."""
        # Simulate streaming by exporting in batches
        batch_size = 100
        total_forks = 1000
        
        exporter = CSVExporter()
        
        all_csv_parts = []
        headers_written = False
        
        start_time = time.time()
        
        for batch_start in range(0, total_forks, batch_size):
            batch_end = min(batch_start + batch_size, total_forks)
            batch_data = self.create_large_fork_dataset(batch_end - batch_start)
            
            # Convert to ForksPreview format
            preview_items = []
            for fork in batch_data:
                metrics = fork.metrics
                item = ForkPreviewItem(
                    name=f"{metrics.name}-batch{batch_start}",
                    owner=metrics.owner,
                    stars=metrics.stargazers_count,
                    last_push_date=metrics.pushed_at,
                    fork_url=metrics.html_url,
                    activity_status="Active",
                    commits_ahead="3"
                )
                preview_items.append(item)
            
            preview = ForksPreview(total_forks=len(preview_items), forks=preview_items)
            
            # Export batch
            csv_output = exporter.export_forks_preview(preview)
            
            if not headers_written:
                all_csv_parts.append(csv_output)
                headers_written = True
            else:
                # Skip headers for subsequent batches
                lines = csv_output.split('\n')
                all_csv_parts.append('\n'.join(lines[1:]))
        
        end_time = time.time()
        
        # Combine all parts
        combined_csv = ''.join(all_csv_parts)
        
        export_time = end_time - start_time
        
        # Performance should be reasonable for batch processing
        assert export_time < 12.0, f"Batch export took {export_time:.2f}s, expected < 12.0s"
        
        # Verify combined output
        reader = csv.DictReader(io.StringIO(combined_csv))
        rows = list(reader)
        assert len(rows) == total_forks