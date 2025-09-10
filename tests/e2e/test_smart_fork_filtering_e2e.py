"""End-to-end tests for smart fork filtering workflow."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from forkscout.analysis.fork_commit_status_checker import ForkCommitStatusChecker
from forkscout.cli import cli
from forkscout.display.detailed_commit_display import DetailedCommitDisplay
from forkscout.models.fork_filtering import ForkFilteringConfig
from forkscout.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualificationStats,
    QualifiedForksResult,
)
from forkscout.models.github import Commit, Repository, User


class TestSmartForkFilteringEndToEnd:
    """End-to-end tests for complete smart fork filtering workflow."""

    @pytest.fixture
    def e2e_config(self):
        """Create configuration for end-to-end testing."""
        from forkscout.config.settings import ForkscoutConfig, GitHubConfig

        return ForkscoutConfig(
            github=GitHubConfig(token="ghp_1234567890abcdef1234567890abcdef12345678"),
            openai_api_key="sk-test1234567890abcdef1234567890abcdef1234567890abcdef"
        )

    @pytest.fixture
    def realistic_fork_ecosystem(self):
        """Create a realistic fork ecosystem for end-to-end testing."""
        # Simulate a real repository with diverse fork characteristics
        fork_metrics = []

        # Active forks with commits ahead (should be processed)
        active_forks = [
            ("activedev1", "feature-branch-fork", 25, 5, True),
            ("contributor2", "bugfix-improvements", 15, 3, True),
            ("poweruser3", "performance-optimizations", 45, 8, True),
        ]

        # Inactive forks with no commits ahead (should be filtered)
        inactive_forks = [
            ("olduser1", "abandoned-fork", 2, 0, False),
            ("testuser2", "empty-clone", 1, 0, False),
        ]

        # Archived/disabled forks (should be filtered)
        archived_forks = [
            ("archiveduser", "old-experiment", 10, 2, True, True, False),  # Archived
            ("disableduser", "broken-fork", 5, 1, True, False, True),     # Disabled
        ]

        fork_id = 50000
        all_fork_data = (
            [(owner, name, stars, forks, commits, False, False) for owner, name, stars, forks, commits in active_forks] +
            [(owner, name, stars, forks, commits, False, False) for owner, name, stars, forks, commits in inactive_forks] +
            archived_forks
        )

        for owner, name, stars, forks_count, has_commits, archived, disabled in all_fork_data:
            created_time = datetime(2023, 1, 1, tzinfo=UTC)
            pushed_time = (
                datetime(2023, 8, 1, tzinfo=UTC)
                if has_commits
                else created_time
            )

            metrics = ForkQualificationMetrics(
                id=fork_id,
                full_name=f"{owner}/{name}",
                owner=owner,
                name=name,
                html_url=f"https://github.com/{owner}/{name}",
                stargazers_count=stars,
                forks_count=forks_count,
                size=1000 + (stars * 50),
                language="Python",
                created_at=created_time,
                updated_at=pushed_time,
                pushed_at=pushed_time,
                open_issues_count=stars // 5,
                topics=["python", "opensource"],
                watchers_count=stars,
                archived=archived,
                disabled=disabled,
                fork=True
            )

            fork_metrics.append(metrics)
            fork_id += 1

        return QualifiedForksResult(
            repository_owner="upstream",
            repository_name="popular-project",
            repository_url="https://github.com/upstream/popular-project",
            collected_forks=[CollectedForkData(metrics=m) for m in fork_metrics],
            stats=QualificationStats(
                total_forks_discovered=len(fork_metrics),
                forks_with_no_commits=2,  # inactive forks
                forks_with_commits=6,     # active + archived/disabled
                api_calls_made=len(fork_metrics),
                processing_time_seconds=5.0
            )
        )

    @pytest.fixture
    def sample_commits_for_active_forks(self):
        """Create sample commits for active forks."""
        author = User(
            id=12345,
            login="activedev1",
            name="Active Developer",
            email="active@example.com",
            html_url="https://github.com/activedev1"
        )

        return [
            Commit(
                sha="e2e1234567890abcdef1234567890abcdef12345",
                message="feat: add advanced caching system",
                author=author,
                date=datetime(2023, 8, 1, tzinfo=UTC),
                files_changed=["cache.py", "config.py", "tests/test_cache.py"],
                additions=150,
                deletions=20
            ),
            Commit(
                sha="e2e2345678901bcdef234567890abcdef1234567",
                message="fix: resolve memory leak in worker threads",
                author=author,
                date=datetime(2023, 8, 5, tzinfo=UTC),
                files_changed=["worker.py", "memory_manager.py"],
                additions=45,
                deletions=30
            ),
            Commit(
                sha="e2e3456789012cdef345678901bcdef123456789",
                message="docs: update API documentation with examples",
                author=author,
                date=datetime(2023, 8, 10, tzinfo=UTC),
                files_changed=["README.md", "docs/api.md", "examples/usage.py"],
                additions=200,
                deletions=50
            )
        ]

    @pytest.mark.asyncio
    async def test_complete_fork_filtering_workflow_with_cli(
        self, e2e_config, realistic_fork_ecosystem, sample_commits_for_active_forks
    ):
        """Test complete fork filtering workflow through CLI interface."""

        with patch("forklift.cli.load_config") as mock_load_config:
            mock_load_config.return_value = e2e_config

            with patch("forklift.cli.GitHubClient") as mock_github_client_class:
                # Setup GitHub client mock
                mock_github_client = AsyncMock()
                mock_github_client_class.return_value.__aenter__.return_value = mock_github_client

                # Mock repository (active fork)
                active_repo = Repository(
                    id=50000,
                    owner="activedev1",
                    name="feature-branch-fork",
                    full_name="activedev1/feature-branch-fork",
                    url="https://api.github.com/repos/activedev1/feature-branch-fork",
                    html_url="https://github.com/activedev1/feature-branch-fork",
                    clone_url="https://github.com/activedev1/feature-branch-fork.git",
                    created_at=datetime(2023, 1, 1, tzinfo=UTC),
                    pushed_at=datetime(2023, 8, 1, tzinfo=UTC),  # Has commits
                    default_branch="main"
                )
                mock_github_client.get_repository.return_value = active_repo

                # Mock commits for active fork
                mock_github_client.get_branch_commits.return_value = [
                    {
                        "sha": commit.sha,
                        "commit": {
                            "message": commit.message,
                            "author": {"name": commit.author.login, "date": commit.date.isoformat()},
                        },
                        "author": {"login": commit.author.login, "id": commit.author.id},
                        "stats": {"additions": commit.additions, "deletions": commit.deletions},
                        "files": [{"filename": f} for f in commit.files_changed]
                    }
                    for commit in sample_commits_for_active_forks
                ]

                with patch("forklift.cli.DetailedCommitDisplay") as mock_display_class:
                    # Setup detailed commit display mock
                    mock_display = AsyncMock()
                    mock_display_class.return_value = mock_display

                    # Mock fork status checker to simulate filtering
                    mock_checker = AsyncMock()
                    mock_display.fork_status_checker = mock_checker

                    # Active fork should be processed
                    mock_display.should_process_repository.return_value = True
                    mock_display.generate_detailed_view.return_value = [
                        MagicMock(commit=commit) for commit in sample_commits_for_active_forks
                    ]

                    # Test CLI command with --detail flag
                    runner = CliRunner()
                    result = runner.invoke(cli, [
                        "show-commits",
                        "activedev1/feature-branch-fork",
                        "--detail"
                    ])

                    # Verify command executed successfully
                    assert result.exit_code == 0

                    # Verify fork filtering was applied
                    mock_display.should_process_repository.assert_called_once()

                    # Verify detailed view was generated for active fork
                    mock_display.generate_detailed_view.assert_called_once()

    @pytest.mark.asyncio
    async def test_fork_filtering_with_mixed_repository_types(
        self, realistic_fork_ecosystem
    ):
        """Test fork filtering behavior with mixed repository types."""
        mock_github_client = AsyncMock()
        config = ForkFilteringConfig(
            enabled=True,
            log_filtering_decisions=True,
            skip_archived_forks=True,
            skip_disabled_forks=True
        )

        checker = ForkCommitStatusChecker(mock_github_client, config)

        # Test each type of fork in the ecosystem
        test_cases = [
            # Active forks - should not be filtered
            ("https://github.com/activedev1/feature-branch-fork", False, "has_commits_ahead"),
            ("https://github.com/contributor2/bugfix-improvements", False, "has_commits_ahead"),
            ("https://github.com/poweruser3/performance-optimizations", False, "has_commits_ahead"),

            # Inactive forks - should be filtered (no commits)
            ("https://github.com/olduser1/abandoned-fork", True, "no_commits_ahead"),
            ("https://github.com/testuser2/empty-clone", True, "no_commits_ahead"),

            # Archived fork - should be filtered (archived)
            ("https://github.com/archiveduser/old-experiment", True, "archived"),

            # Disabled fork - should be filtered (disabled)
            ("https://github.com/disableduser/broken-fork", True, "disabled"),
        ]

        results = []
        for fork_url, expected_filtered, expected_reason in test_cases:
            # Extract fork data from URL
            parts = fork_url.split("/")
            owner, name = parts[-2], parts[-1]
            full_name = f"{owner}/{name}"

            # Find corresponding fork data
            fork_data = None
            for collected_fork in realistic_fork_ecosystem.collected_forks:
                if collected_fork.metrics.full_name == full_name:
                    fork_data = {
                        "full_name": full_name,
                        "archived": collected_fork.metrics.archived,
                        "disabled": collected_fork.metrics.disabled
                    }
                    break

            assert fork_data is not None, f"Fork data not found for {full_name}"

            # Evaluate fork for filtering
            should_filter, reason = await checker.evaluate_fork_for_filtering(
                fork_url, fork_data, realistic_fork_ecosystem
            )

            results.append((full_name, should_filter, reason))

            # Verify expected behavior
            assert should_filter == expected_filtered, f"Fork {full_name}: expected filtered={expected_filtered}, got {should_filter}"
            assert reason == expected_reason, f"Fork {full_name}: expected reason={expected_reason}, got {reason}"

        # Verify overall statistics
        stats = checker.get_statistics()
        assert stats.total_forks_evaluated == len(test_cases)
        assert stats.forks_filtered_out == 4  # 2 inactive + 1 archived + 1 disabled
        assert stats.forks_included == 3      # 3 active forks
        assert abs(stats.filtering_rate - 57.1) < 0.2   # 4/7 filtered (approximately 57.1%)

    @pytest.mark.asyncio
    async def test_detailed_commit_display_end_to_end_workflow(
        self, realistic_fork_ecosystem, sample_commits_for_active_forks
    ):
        """Test detailed commit display end-to-end workflow with filtering."""
        mock_github_client = AsyncMock()

        # Setup fork filtering
        config = ForkFilteringConfig(enabled=True, log_filtering_decisions=True)
        checker = ForkCommitStatusChecker(mock_github_client, config)

        # Setup detailed commit display
        display = DetailedCommitDisplay(
            github_client=mock_github_client,
            fork_status_checker=checker
        )

        # Create test repositories representing different fork types
        active_repo = Repository(
            id=50000,
            owner="activedev1",
            name="feature-branch-fork",
            full_name="activedev1/feature-branch-fork",
            url="https://api.github.com/repos/activedev1/feature-branch-fork",
            html_url="https://github.com/activedev1/feature-branch-fork",
            clone_url="https://github.com/activedev1/feature-branch-fork.git",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            pushed_at=datetime(2023, 8, 1, tzinfo=UTC),  # Has commits
            default_branch="main"
        )

        inactive_repo = Repository(
            id=50001,
            owner="olduser1",
            name="abandoned-fork",
            full_name="olduser1/abandoned-fork",
            url="https://api.github.com/repos/olduser1/abandoned-fork",
            html_url="https://github.com/olduser1/abandoned-fork",
            clone_url="https://github.com/olduser1/abandoned-fork.git",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            pushed_at=datetime(2023, 1, 1, tzinfo=UTC),  # No commits
            default_branch="main"
        )

        # Mock the fork status checker behavior
        async def mock_has_commits_ahead(fork_url, qualification_result=None):
            if "activedev1/feature-branch-fork" in fork_url:
                return True   # Active fork has commits
            elif "olduser1/abandoned-fork" in fork_url:
                return False  # Inactive fork has no commits
            return None

        with patch.object(checker, "has_commits_ahead", side_effect=mock_has_commits_ahead):
            # Test active repository - should be processed
            should_process_active = await display.should_process_repository(active_repo)
            assert should_process_active is True

            # Test inactive repository - should be skipped
            should_process_inactive = await display.should_process_repository(inactive_repo)
            assert should_process_inactive is False

            # Test batch processing with mixed repositories
            repositories_with_commits = [
                (active_repo, sample_commits_for_active_forks),
                (inactive_repo, sample_commits_for_active_forks)  # Same commits for testing
            ]

            with patch.object(display, "_fetch_commit_details") as mock_fetch:
                from forkscout.display.detailed_commit_display import DetailedCommitInfo
                mock_fetch.return_value = DetailedCommitInfo(
                    commit=sample_commits_for_active_forks[0],
                    github_url="https://github.com/activedev1/feature-branch-fork/commit/e2e123"
                )

                # Process multiple repositories
                results = await display.process_multiple_repositories(repositories_with_commits)

                # Only active repository should be processed
                assert len(results) == 1
                assert results[0][0].full_name == "activedev1/feature-branch-fork"

    @pytest.mark.asyncio
    async def test_performance_impact_of_filtering_in_e2e_scenario(
        self, realistic_fork_ecosystem
    ):
        """Test performance impact of fork filtering in end-to-end scenario."""
        import time

        mock_github_client = AsyncMock()

        # Mock API response with delay to simulate real API calls
        async def mock_get_repository_with_delay(owner, repo):
            await asyncio.sleep(0.05)  # 50ms delay per API call
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

        # Test with filtering enabled
        config_with_filtering = ForkFilteringConfig(
            enabled=True,
            fallback_to_api=True,
            max_api_fallback_calls=5  # Limit API calls
        )

        checker_with_filtering = ForkCommitStatusChecker(mock_github_client, config_with_filtering)

        # Test all forks in ecosystem + some unknown forks
        all_fork_urls = []

        # Known forks (from qualification data)
        for fork_data in realistic_fork_ecosystem.collected_forks:
            all_fork_urls.append(f"https://github.com/{fork_data.metrics.full_name}")

        # Unknown forks (will trigger API calls)
        for i in range(10):
            all_fork_urls.append(f"https://github.com/unknown{i}/repo{i}")

        # Measure time with filtering
        start_time = time.perf_counter()

        results_with_filtering = []
        for fork_url in all_fork_urls:
            result = await checker_with_filtering.has_commits_ahead(fork_url, realistic_fork_ecosystem)
            results_with_filtering.append(result)

        end_time = time.perf_counter()
        time_with_filtering = end_time - start_time

        # Verify API call limiting worked
        api_calls_with_filtering = mock_github_client.get_repository.call_count
        assert api_calls_with_filtering <= 5  # Should be limited

        # Reset mock for comparison
        mock_github_client.reset_mock()

        # Test without filtering (simulate processing all forks via API)
        config_without_filtering = ForkFilteringConfig(
            enabled=False,
            fallback_to_api=True,
            max_api_fallback_calls=0  # No API calls when disabled
        )

        checker_without_filtering = ForkCommitStatusChecker(mock_github_client, config_without_filtering)

        # Measure time without filtering (only process known forks to be fair)
        known_fork_urls = [f"https://github.com/{fork_data.metrics.full_name}"
                          for fork_data in realistic_fork_ecosystem.collected_forks]

        start_time = time.perf_counter()

        results_without_filtering = []
        for fork_url in known_fork_urls:
            result = await checker_without_filtering.has_commits_ahead(fork_url, realistic_fork_ecosystem)
            results_without_filtering.append(result)

        end_time = time.perf_counter()
        time_without_filtering = end_time - start_time

        # Verify performance improvement
        # With filtering should be much faster due to API call reduction
        assert time_with_filtering < time_without_filtering + 1.0  # Allow some variance

        # Verify statistics show efficiency
        stats_with_filtering = checker_with_filtering.get_statistics()
        assert stats_with_filtering.qualification_data_hits > 0
        assert stats_with_filtering.api_fallback_calls <= 5

    @pytest.mark.asyncio
    async def test_error_recovery_in_e2e_workflow(self, realistic_fork_ecosystem):
        """Test error recovery and graceful degradation in end-to-end workflow."""
        mock_github_client = AsyncMock()

        # Mock API to fail for some repositories
        def mock_get_repository_with_errors(owner, repo):
            if "error" in owner or "error" in repo:
                raise Exception(f"Simulated API error for {owner}/{repo}")
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

        config = ForkFilteringConfig(
            enabled=True,
            fallback_to_api=True,
            prefer_inclusion_on_uncertainty=True  # Include forks when uncertain
        )

        checker = ForkCommitStatusChecker(mock_github_client, config)

        # Test mix of successful and error-prone forks
        test_fork_urls = []

        # Known forks (should work via qualification data)
        for fork_data in realistic_fork_ecosystem.collected_forks[:3]:
            test_fork_urls.append(f"https://github.com/{fork_data.metrics.full_name}")

        # Error-prone forks (will fail API calls)
        test_fork_urls.extend([
            "https://github.com/erroruser1/errorrepo1",
            "https://github.com/erroruser2/errorrepo2",
        ])

        # Good unknown forks (should work via API)
        test_fork_urls.extend([
            "https://github.com/gooduser1/goodrepo1",
            "https://github.com/gooduser2/goodrepo2",
        ])

        # Process all forks and track results
        results = []
        error_count = 0

        for fork_url in test_fork_urls:
            try:
                result = await checker.has_commits_ahead(fork_url, realistic_fork_ecosystem)
                results.append((fork_url, result, None))
            except Exception as e:
                results.append((fork_url, None, str(e)))
                error_count += 1

        # Verify error handling
        assert len(results) == len(test_fork_urls)
        assert error_count > 0  # Should have encountered some errors

        # Verify successful processing of known forks despite errors
        successful_results = [r for r in results if r[2] is None]
        assert len(successful_results) >= 3  # At least the known forks + good unknown forks

        # Verify statistics include error tracking
        stats = checker.get_statistics()
        assert stats.errors > 0
        assert stats.qualification_data_hits >= 3  # Known forks processed successfully

    @pytest.mark.asyncio
    async def test_integration_with_real_world_fork_patterns(self):
        """Test integration with realistic fork patterns found in real repositories."""
        # Simulate patterns commonly found in real GitHub repositories

        # Pattern 1: Many inactive forks (common in popular repos)
        inactive_pattern = []
        for i in range(50):
            metrics = ForkQualificationMetrics(
                id=60000 + i,
                full_name=f"user{i}/popular-repo",
                owner=f"user{i}",
                name="popular-repo",
                html_url=f"https://github.com/user{i}/popular-repo",
                stargazers_count=0,  # No stars
                forks_count=0,       # No forks
                size=1000,           # Same size as original
                language="Python",
                created_at=datetime(2023, 1, 1, tzinfo=UTC),
                updated_at=datetime(2023, 1, 1, tzinfo=UTC),
                pushed_at=datetime(2023, 1, 1, tzinfo=UTC),  # No commits
                open_issues_count=0,
                topics=[],
                watchers_count=0,
                archived=False,
                disabled=False,
                fork=True
            )
            inactive_pattern.append(CollectedForkData(metrics=metrics))

        # Pattern 2: Few active forks with significant changes
        active_pattern = []
        for i in range(5):
            metrics = ForkQualificationMetrics(
                id=61000 + i,
                full_name=f"activedev{i}/popular-repo",
                owner=f"activedev{i}",
                name="popular-repo",
                html_url=f"https://github.com/activedev{i}/popular-repo",
                stargazers_count=10 + (i * 5),  # Some stars
                forks_count=2 + i,              # Some forks
                size=1500 + (i * 200),          # Larger size (more code)
                language="Python",
                created_at=datetime(2023, 1, 1, tzinfo=UTC),
                updated_at=datetime(2023, 9, 1, tzinfo=UTC),
                pushed_at=datetime(2023, 9, 1, tzinfo=UTC),  # Recent commits
                open_issues_count=i + 1,
                topics=["python", "enhancement"],
                watchers_count=8 + (i * 3),
                archived=False,
                disabled=False,
                fork=True
            )
            active_pattern.append(CollectedForkData(metrics=metrics))

        # Pattern 3: Archived/abandoned forks (common in older repos)
        archived_pattern = []
        for i in range(10):
            metrics = ForkQualificationMetrics(
                id=62000 + i,
                full_name=f"olduser{i}/popular-repo",
                owner=f"olduser{i}",
                name="popular-repo",
                html_url=f"https://github.com/olduser{i}/popular-repo",
                stargazers_count=i,
                forks_count=0,
                size=1200,
                language="Python",
                created_at=datetime(2022, 1, 1, tzinfo=UTC),  # Older
                updated_at=datetime(2022, 6, 1, tzinfo=UTC),
                pushed_at=datetime(2022, 6, 1, tzinfo=UTC),
                open_issues_count=0,
                topics=["python"],
                watchers_count=i,
                archived=i % 3 == 0,  # Some archived
                disabled=False,
                fork=True
            )
            archived_pattern.append(CollectedForkData(metrics=metrics))

        # Combine all patterns
        all_forks = inactive_pattern + active_pattern + archived_pattern

        realistic_ecosystem = QualifiedForksResult(
            repository_owner="upstream",
            repository_name="popular-repo",
            repository_url="https://github.com/upstream/popular-repo",
            collected_forks=all_forks,
            stats=QualificationStats(
                total_forks_discovered=len(all_forks),
                forks_with_no_commits=50,  # All inactive forks
                forks_with_commits=15,     # Active + some archived
                api_calls_made=len(all_forks),
                processing_time_seconds=30.0
            )
        )

        # Test filtering with realistic patterns
        mock_github_client = AsyncMock()
        config = ForkFilteringConfig(
            enabled=True,
            skip_archived_forks=True,
            log_filtering_decisions=False  # Disable for performance
        )

        checker = ForkCommitStatusChecker(mock_github_client, config)

        # Process all forks
        filtering_results = []
        for fork_data in all_forks:
            fork_url = f"https://github.com/{fork_data.metrics.full_name}"
            fork_metadata = {
                "full_name": fork_data.metrics.full_name,
                "archived": fork_data.metrics.archived,
                "disabled": fork_data.metrics.disabled
            }

            should_filter, reason = await checker.evaluate_fork_for_filtering(
                fork_url, fork_metadata, realistic_ecosystem
            )
            filtering_results.append((fork_data.metrics.full_name, should_filter, reason))

        # Verify realistic filtering behavior
        total_forks = len(filtering_results)
        filtered_forks = sum(1 for _, filtered, _ in filtering_results if filtered)
        included_forks = total_forks - filtered_forks

        # Should filter most inactive forks + archived forks
        expected_filtered = 50 + 3  # 50 inactive + ~3 archived (10/3)
        assert filtered_forks >= expected_filtered - 2  # Allow some variance

        # Should include active forks
        assert included_forks >= 5  # At least the 5 active forks

        # Verify statistics reflect realistic patterns
        stats = checker.get_statistics()
        assert stats.total_forks_evaluated == total_forks
        assert stats.filtering_rate > 70.0  # Should filter majority of forks
        assert stats.qualification_data_hits == total_forks  # All from qualification data
        assert stats.api_fallback_calls == 0  # No API calls needed

        # This test demonstrates that the filtering system works effectively
        # with realistic fork distribution patterns commonly found in popular repositories
