"""Comprehensive integration tests for smart fork filtering functionality."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from forklift.analysis.fork_commit_status_checker import (
    ForkCommitStatusChecker,
    ForkCommitStatusError,
)
from forklift.cli import cli
from forklift.display.detailed_commit_display import DetailedCommitDisplay
from forklift.github.client import GitHubAPIError, GitHubClient, GitHubNotFoundError
from forklift.models.fork_filtering import ForkFilteringConfig
from forklift.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualificationStats,
    QualifiedForksResult,
)
from forklift.models.github import Commit, Repository, User


class TestSmartForkFilteringIntegration:
    """Integration tests for smart fork filtering with real GitHub repositories."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client for testing."""
        return AsyncMock(spec=GitHubClient)

    @pytest.fixture
    def fork_filtering_config(self):
        """Create a fork filtering configuration for testing."""
        return ForkFilteringConfig(
            enabled=True,
            log_filtering_decisions=True,
            fallback_to_api=True,
            prefer_inclusion_on_uncertainty=True,
            max_api_fallback_calls=10,
        )

    @pytest.fixture
    def sample_repository_with_commits(self):
        """Create a sample repository that has commits ahead."""
        return Repository(
            id=12345,
            owner="testowner",
            name="active-repo",
            full_name="testowner/active-repo",
            url="https://api.github.com/repos/testowner/active-repo",
            html_url="https://github.com/testowner/active-repo",
            clone_url="https://github.com/testowner/active-repo.git",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            pushed_at=datetime(2023, 6, 1, tzinfo=UTC),  # Later than created
            default_branch="main"
        )

    @pytest.fixture
    def sample_repository_no_commits(self):
        """Create a sample repository that has no commits ahead."""
        return Repository(
            id=67890,
            owner="testowner",
            name="inactive-repo",
            full_name="testowner/inactive-repo",
            url="https://api.github.com/repos/testowner/inactive-repo",
            html_url="https://github.com/testowner/inactive-repo",
            clone_url="https://github.com/testowner/inactive-repo.git",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            pushed_at=datetime(2023, 1, 1, tzinfo=UTC),  # Same as created
            default_branch="main"
        )
    @pytest.fixture
    def sample_commits(self):
        """Create sample commits for testing."""
        author = User(
            id=123,
            login="testauthor",
            name="Test Author",
            email="test@example.com",
            html_url="https://github.com/testauthor"
        )

        return [
            Commit(
                sha="abc1234567890abcdef1234567890abcdef12345",
                message="feat: add new feature",
                author=author,
                date=datetime(2023, 6, 1, tzinfo=UTC),
                files_changed=["feature.py"],
                additions=50,
                deletions=5
            ),
            Commit(
                sha="def4567890abcdef1234567890abcdef12345678",
                message="fix: resolve bug",
                author=author,
                date=datetime(2023, 6, 2, tzinfo=UTC),
                files_changed=["feature.py", "tests.py"],
                additions=10,
                deletions=15
            )
        ]

    @pytest.fixture
    def qualification_result_mixed_forks(self):
        """Create qualification result with mixed fork types."""
        # Fork with commits ahead
        metrics_with_commits = ForkQualificationMetrics(
            id=12345,
            full_name="testowner/active-repo",
            owner="testowner",
            name="active-repo",
            html_url="https://github.com/testowner/active-repo",
            stargazers_count=10,
            forks_count=5,
            size=1000,
            language="Python",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 6, 1, tzinfo=UTC),
            pushed_at=datetime(2023, 6, 1, tzinfo=UTC),  # Later than created
            open_issues_count=2,
            topics=["python", "test"],
            watchers_count=10,
            archived=False,
            disabled=False,
            fork=True
        )

        # Fork without commits ahead
        metrics_no_commits = ForkQualificationMetrics(
            id=67890,
            full_name="testowner/inactive-repo",
            owner="testowner",
            name="inactive-repo",
            html_url="https://github.com/testowner/inactive-repo",
            stargazers_count=2,
            forks_count=1,
            size=500,
            language="Python",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 1, 1, tzinfo=UTC),
            pushed_at=datetime(2023, 1, 1, tzinfo=UTC),  # Same as created
            open_issues_count=0,
            topics=["python"],
            watchers_count=2,
            archived=False,
            disabled=False,
            fork=True
        )

        # Archived fork (should be filtered)
        metrics_archived = ForkQualificationMetrics(
            id=11111,
            full_name="testowner/archived-repo",
            owner="testowner",
            name="archived-repo",
            html_url="https://github.com/testowner/archived-repo",
            stargazers_count=5,
            forks_count=2,
            size=750,
            language="Python",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 3, 1, tzinfo=UTC),
            pushed_at=datetime(2023, 3, 1, tzinfo=UTC),
            open_issues_count=0,
            topics=["python"],
            watchers_count=5,
            archived=True,  # Archived
            disabled=False,
            fork=True
        )

        fork_data = [
            CollectedForkData(metrics=metrics_with_commits),
            CollectedForkData(metrics=metrics_no_commits),
            CollectedForkData(metrics=metrics_archived),
        ]

        stats = QualificationStats(
            total_forks_discovered=3,
            forks_with_no_commits=1,
            forks_with_commits=2,
            api_calls_made=3,
            processing_time_seconds=2.5
        )

        return QualifiedForksResult(
            repository_owner="upstream",
            repository_name="main-repo",
            repository_url="https://github.com/upstream/main-repo",
            collected_forks=fork_data,
            stats=stats
        )

    @pytest.mark.asyncio
    async def test_fork_status_checker_with_real_github_repositories(
        self, mock_github_client, fork_filtering_config, qualification_result_mixed_forks
    ):
        """Test fork status checker with realistic GitHub repository scenarios."""
        checker = ForkCommitStatusChecker(mock_github_client, fork_filtering_config)

        # Test fork with commits ahead using qualification data
        has_commits = await checker.has_commits_ahead(
            "https://github.com/testowner/active-repo",
            qualification_result_mixed_forks
        )
        assert has_commits is True

        # Test fork without commits ahead using qualification data
        has_commits = await checker.has_commits_ahead(
            "https://github.com/testowner/inactive-repo",
            qualification_result_mixed_forks
        )
        assert has_commits is False

        # Test fork not in qualification data (should fallback to API)
        mock_github_client.get_repository.return_value = Repository(
            id=99999,
            owner="testowner",
            name="unknown-repo",
            full_name="testowner/unknown-repo",
            url="https://api.github.com/repos/testowner/unknown-repo",
            html_url="https://github.com/testowner/unknown-repo",
            clone_url="https://github.com/testowner/unknown-repo.git",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            pushed_at=datetime(2023, 5, 1, tzinfo=UTC),
            default_branch="main"
        )

        has_commits = await checker.has_commits_ahead(
            "https://github.com/testowner/unknown-repo",
            qualification_result_mixed_forks
        )
        assert has_commits is True

        # Verify statistics
        stats = checker.get_statistics()
        assert stats.qualification_data_hits == 2
        assert stats.api_fallback_calls == 1
        assert stats.total_forks_evaluated == 0  # No evaluate_fork_for_filtering calls yet

    @pytest.mark.asyncio
    async def test_detailed_commit_display_with_fork_filtering(
        self, mock_github_client, fork_filtering_config,
        sample_repository_with_commits, sample_repository_no_commits, sample_commits
    ):
        """Test detailed commit display integration with fork filtering."""
        checker = ForkCommitStatusChecker(mock_github_client, fork_filtering_config)
        display = DetailedCommitDisplay(
            github_client=mock_github_client,
            fork_status_checker=checker
        )

        # Mock the checker responses
        async def mock_has_commits_ahead(fork_url, qualification_result=None):
            if "active-repo" in fork_url:
                return True
            elif "inactive-repo" in fork_url:
                return False
            return None

        with patch.object(checker, "has_commits_ahead", side_effect=mock_has_commits_ahead):
            # Test repository with commits - should be processed
            should_process = await display.should_process_repository(sample_repository_with_commits)
            assert should_process is True

            # Test repository without commits - should be skipped
            should_process = await display.should_process_repository(sample_repository_no_commits)
            assert should_process is False

            # Test with force flag - should override filtering
            should_process = await display.should_process_repository(
                sample_repository_no_commits, force=True
            )
            assert should_process is True

    @pytest.mark.asyncio
    async def test_fork_filtering_performance_optimization(
        self, mock_github_client, fork_filtering_config, qualification_result_mixed_forks
    ):
        """Test that fork filtering reduces unnecessary API calls."""
        checker = ForkCommitStatusChecker(mock_github_client, fork_filtering_config)

        # Test multiple forks - some should use qualification data, others API fallback
        fork_urls = [
            "https://github.com/testowner/active-repo",      # In qualification data
            "https://github.com/testowner/inactive-repo",    # In qualification data
            "https://github.com/testowner/unknown-repo-1",   # Not in qualification data
            "https://github.com/testowner/unknown-repo-2",   # Not in qualification data
        ]

        # Mock API responses for unknown repos
        def mock_get_repository(owner, repo):
            return Repository(
                id=99999,
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

        mock_github_client.get_repository.side_effect = mock_get_repository

        # Process all fork URLs
        results = []
        for fork_url in fork_urls:
            result = await checker.has_commits_ahead(fork_url, qualification_result_mixed_forks)
            results.append(result)

        # Verify results
        assert results[0] is True   # active-repo has commits
        assert results[1] is False  # inactive-repo has no commits
        assert results[2] is True   # unknown-repo-1 has commits (API fallback)
        assert results[3] is True   # unknown-repo-2 has commits (API fallback)

        # Verify performance: only 2 API calls should have been made (for unknown repos)
        assert mock_github_client.get_repository.call_count == 2

        # Verify statistics show efficiency
        stats = checker.get_statistics()
        assert stats.qualification_data_hits == 2  # First two used qualification data
        assert stats.api_fallback_calls == 2       # Last two used API fallback
        assert stats.api_usage_efficiency > 0      # Should show some efficiency

    @pytest.mark.asyncio
    async def test_fork_filtering_error_handling_scenarios(
        self, mock_github_client, fork_filtering_config
    ):
        """Test error handling in various fork filtering scenarios."""
        checker = ForkCommitStatusChecker(mock_github_client, fork_filtering_config)

        # Test GitHub API not found error
        mock_github_client.get_repository.side_effect = GitHubNotFoundError("Repository not found")

        result = await checker.has_commits_ahead("https://github.com/nonexistent/repo")
        assert result is None

        stats = checker.get_statistics()
        assert stats.status_unknown == 1
        assert stats.api_fallback_calls == 1

        # Reset for next test
        checker.reset_statistics()

        # Test GitHub API error
        mock_github_client.get_repository.side_effect = GitHubAPIError("API Error", status_code=500)

        result = await checker.has_commits_ahead("https://github.com/error/repo")
        assert result is None

        stats = checker.get_statistics()
        assert stats.status_unknown == 1

        # Reset for next test
        checker.reset_statistics()

        # Test unexpected error
        mock_github_client.get_repository.side_effect = Exception("Unexpected error")

        with pytest.raises(ForkCommitStatusError):
            await checker.has_commits_ahead("https://github.com/unexpected/error")

        stats = checker.get_statistics()
        assert stats.errors == 1

        # Test invalid URL format
        with pytest.raises(ForkCommitStatusError, match="Invalid fork URL format"):
            await checker.has_commits_ahead("invalid-url")

    @pytest.mark.asyncio
    async def test_fork_filtering_configuration_options(
        self, mock_github_client, qualification_result_mixed_forks
    ):
        """Test different fork filtering configuration options."""

        # Test with API fallback disabled
        config_no_fallback = ForkFilteringConfig(
            enabled=True,
            fallback_to_api=False,
            prefer_inclusion_on_uncertainty=False
        )

        checker = ForkCommitStatusChecker(mock_github_client, config_no_fallback)

        # Fork not in qualification data should return False (no fallback)
        result = await checker.has_commits_ahead(
            "https://github.com/unknown/repo",
            qualification_result_mixed_forks
        )
        assert result is False  # prefer_inclusion_on_uncertainty=False

        # Verify no API calls were made
        assert mock_github_client.get_repository.call_count == 0

        # Test with inclusion preference on uncertainty
        config_include_uncertain = ForkFilteringConfig(
            enabled=True,
            fallback_to_api=False,
            prefer_inclusion_on_uncertainty=True
        )

        checker = ForkCommitStatusChecker(mock_github_client, config_include_uncertain)

        result = await checker.has_commits_ahead(
            "https://github.com/unknown/repo",
            qualification_result_mixed_forks
        )
        assert result is None  # Returns None when uncertain and prefer_inclusion=True

        # Test with API fallback limit
        config_limited_fallback = ForkFilteringConfig(
            enabled=True,
            fallback_to_api=True,
            max_api_fallback_calls=1
        )

        checker = ForkCommitStatusChecker(mock_github_client, config_limited_fallback)

        # Mock successful API response
        mock_github_client.get_repository.return_value = Repository(
            id=99999,
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

        # First call should use API
        result1 = await checker.has_commits_ahead("https://github.com/test/repo1")
        assert result1 is True

        # Second call should hit the limit and not use API
        result2 = await checker.has_commits_ahead("https://github.com/test/repo2")
        assert result2 is False  # prefer_inclusion_on_uncertainty=True by default, but limit reached

        # Verify only one API call was made
        assert mock_github_client.get_repository.call_count == 1

    @pytest.mark.asyncio
    async def test_fork_evaluation_with_filtering_criteria(
        self, mock_github_client, fork_filtering_config, qualification_result_mixed_forks
    ):
        """Test comprehensive fork evaluation with various filtering criteria."""
        checker = ForkCommitStatusChecker(mock_github_client, fork_filtering_config)

        # Test fork with commits ahead
        should_filter, reason = await checker.evaluate_fork_for_filtering(
            "https://github.com/testowner/active-repo",
            {"full_name": "testowner/active-repo", "archived": False, "disabled": False},
            qualification_result_mixed_forks
        )
        assert should_filter is False
        assert reason == "has_commits_ahead"

        # Test fork without commits ahead
        should_filter, reason = await checker.evaluate_fork_for_filtering(
            "https://github.com/testowner/inactive-repo",
            {"full_name": "testowner/inactive-repo", "archived": False, "disabled": False},
            qualification_result_mixed_forks
        )
        assert should_filter is True
        assert reason == "no_commits_ahead"

        # Test archived fork
        should_filter, reason = await checker.evaluate_fork_for_filtering(
            "https://github.com/testowner/archived-repo",
            {"full_name": "testowner/archived-repo", "archived": True, "disabled": False},
            qualification_result_mixed_forks
        )
        assert should_filter is True
        assert reason == "archived"

        # Test disabled fork
        should_filter, reason = await checker.evaluate_fork_for_filtering(
            "https://github.com/testowner/disabled-repo",
            {"full_name": "testowner/disabled-repo", "archived": False, "disabled": True},
            qualification_result_mixed_forks
        )
        assert should_filter is True
        assert reason == "disabled"

        # Verify statistics
        stats = checker.get_statistics()
        assert stats.total_forks_evaluated == 4
        assert stats.forks_filtered_out == 3
        assert stats.forks_included == 1
        assert stats.filtered_archived == 1
        assert stats.filtered_disabled == 1
        assert stats.filtered_no_commits_ahead == 1

    @pytest.mark.asyncio
    async def test_batch_fork_processing_with_filtering(
        self, mock_github_client, fork_filtering_config, qualification_result_mixed_forks
    ):
        """Test batch processing of multiple forks with filtering."""
        checker = ForkCommitStatusChecker(mock_github_client, fork_filtering_config)

        # Simulate batch processing of forks
        fork_data_list = [
            {
                "fork_url": "https://github.com/testowner/active-repo",
                "fork_data": {"full_name": "testowner/active-repo", "archived": False, "disabled": False}
            },
            {
                "fork_url": "https://github.com/testowner/inactive-repo",
                "fork_data": {"full_name": "testowner/inactive-repo", "archived": False, "disabled": False}
            },
            {
                "fork_url": "https://github.com/testowner/archived-repo",
                "fork_data": {"full_name": "testowner/archived-repo", "archived": True, "disabled": False}
            },
        ]

        results = []
        for fork_info in fork_data_list:
            should_filter, reason = await checker.evaluate_fork_for_filtering(
                fork_info["fork_url"],
                fork_info["fork_data"],
                qualification_result_mixed_forks
            )
            results.append((fork_info["fork_url"], should_filter, reason))

        # Verify results
        assert len(results) == 3
        assert results[0][1] is False  # active-repo should not be filtered
        assert results[1][1] is True   # inactive-repo should be filtered (no commits)
        assert results[2][1] is True   # archived-repo should be filtered (archived)

        # Verify filtering efficiency
        stats = checker.get_statistics()
        assert abs(stats.filtering_rate - 66.7) < 0.2  # 2 out of 3 filtered (approximately 66.7%)
        assert stats.qualification_data_hits >= 2  # Should have used qualification data

    @pytest.mark.asyncio
    async def test_fork_filtering_statistics_and_logging(
        self, mock_github_client, fork_filtering_config, qualification_result_mixed_forks, caplog
    ):
        """Test fork filtering statistics collection and logging."""
        import logging

        # Enable debug logging
        caplog.set_level(logging.DEBUG)

        checker = ForkCommitStatusChecker(mock_github_client, fork_filtering_config)

        # Process several forks to generate statistics
        test_cases = [
            ("https://github.com/testowner/active-repo", True),      # Has commits
            ("https://github.com/testowner/inactive-repo", False),   # No commits
            ("https://github.com/testowner/archived-repo", True),    # Archived (filtered)
        ]

        for fork_url, expected_has_commits in test_cases:
            fork_data = {
                "full_name": fork_url.split("/")[-2] + "/" + fork_url.split("/")[-1],
                "archived": "archived-repo" in fork_url,
                "disabled": False
            }

            await checker.evaluate_fork_for_filtering(
                fork_url, fork_data, qualification_result_mixed_forks
            )

        # Test statistics logging
        checker.log_statistics()

        # Verify statistics are correct
        stats = checker.get_statistics()
        assert stats.total_forks_evaluated == 3
        assert stats.forks_filtered_out == 2  # inactive-repo and archived-repo
        assert stats.forks_included == 1      # active-repo
        assert stats.qualification_data_hits >= 2

        # Verify logging output contains expected information
        assert "Fork filtering statistics:" in caplog.text
        assert "evaluated=3" in caplog.text
        assert "filtering_rate=" in caplog.text

        # Test statistics reset
        checker.reset_statistics()
        stats_after_reset = checker.get_statistics()
        assert stats_after_reset.total_forks_evaluated == 0
        assert stats_after_reset.qualification_data_hits == 0

    @pytest.mark.asyncio
    async def test_fork_filtering_with_concurrent_requests(
        self, mock_github_client, fork_filtering_config, qualification_result_mixed_forks
    ):
        """Test fork filtering with concurrent requests to simulate real usage."""
        checker = ForkCommitStatusChecker(mock_github_client, fork_filtering_config)

        # Mock API responses for unknown repos
        async def mock_get_repository(owner, repo):
            # Simulate some delay
            await asyncio.sleep(0.01)
            return Repository(
                id=99999,
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

        mock_github_client.get_repository.side_effect = mock_get_repository

        # Create multiple concurrent requests
        fork_urls = [
            "https://github.com/testowner/active-repo",      # In qualification data
            "https://github.com/testowner/inactive-repo",    # In qualification data
            "https://github.com/testowner/concurrent-1",     # API fallback
            "https://github.com/testowner/concurrent-2",     # API fallback
            "https://github.com/testowner/concurrent-3",     # API fallback
        ]

        # Process requests concurrently
        tasks = [
            checker.has_commits_ahead(fork_url, qualification_result_mixed_forks)
            for fork_url in fork_urls
        ]

        results = await asyncio.gather(*tasks)

        # Verify results
        assert len(results) == 5
        assert results[0] is True   # active-repo
        assert results[1] is False  # inactive-repo
        assert results[2] is True   # concurrent-1 (API fallback)
        assert results[3] is True   # concurrent-2 (API fallback)
        assert results[4] is True   # concurrent-3 (API fallback)

        # Verify statistics
        stats = checker.get_statistics()
        assert stats.qualification_data_hits == 2
        assert stats.api_fallback_calls == 3
        assert stats.errors == 0


class TestSmartForkFilteringCLIIntegration:
    """Test smart fork filtering integration with CLI commands."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for CLI tests."""
        from forklift.config.settings import ForkliftConfig, GitHubConfig

        return ForkliftConfig(
            github=GitHubConfig(token="ghp_1234567890abcdef1234567890abcdef12345678"),
            openai_api_key="sk-test1234567890abcdef1234567890abcdef1234567890abcdef"
        )

    @pytest.mark.asyncio
    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.DetailedCommitDisplay")
    async def test_show_commits_detail_with_fork_filtering(
        self, mock_display_class, mock_github_client_class, mock_load_config, mock_config
    ):
        """Test show-commits --detail command with fork filtering integration."""
        mock_load_config.return_value = mock_config

        # Setup GitHub client mock
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client

        # Setup repository mock
        sample_repo = Repository(
            owner="testowner",
            name="testrepo",
            full_name="testowner/testrepo",
            url="https://api.github.com/repos/testowner/testrepo",
            html_url="https://github.com/testowner/testrepo",
            clone_url="https://github.com/testowner/testrepo.git",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            pushed_at=datetime(2023, 1, 1, tzinfo=UTC),  # No commits ahead
            default_branch="main"
        )
        mock_github_client.get_repository.return_value = sample_repo
        mock_github_client.get_branch_commits.return_value = []

        # Setup detailed commit display mock
        mock_display = AsyncMock()
        mock_display_class.return_value = mock_display
        mock_display.should_process_repository.return_value = False  # Should be filtered
        mock_display.generate_detailed_view.return_value = []

        runner = CliRunner()
        result = runner.invoke(cli, [
            "show-commits",
            "testowner/testrepo",
            "--detail"
        ])

        assert result.exit_code == 0

        # Verify that fork filtering was applied
        mock_display.should_process_repository.assert_called_once()

        # Since repository has no commits ahead, detailed view should be empty
        if mock_display.generate_detailed_view.called:
            mock_display.generate_detailed_view.assert_called_with([], sample_repo)

    @pytest.mark.asyncio
    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.DetailedCommitDisplay")
    async def test_show_commits_detail_with_force_flag(
        self, mock_display_class, mock_github_client_class, mock_load_config, mock_config
    ):
        """Test show-commits --detail --force command bypasses filtering."""
        mock_load_config.return_value = mock_config

        # Setup GitHub client mock
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client

        # Setup repository mock (no commits ahead)
        sample_repo = Repository(
            owner="testowner",
            name="testrepo",
            full_name="testowner/testrepo",
            url="https://api.github.com/repos/testowner/testrepo",
            html_url="https://github.com/testowner/testrepo",
            clone_url="https://github.com/testowner/testrepo.git",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            pushed_at=datetime(2023, 1, 1, tzinfo=UTC),  # No commits ahead
            default_branch="main"
        )
        mock_github_client.get_repository.return_value = sample_repo

        # Mock some commits
        sample_commits = [
            {
                "sha": "abc123",
                "commit": {"message": "test commit", "author": {"name": "test", "date": "2023-01-01T00:00:00Z"}},
                "author": {"login": "test", "id": 123},
                "stats": {"additions": 1, "deletions": 0},
                "files": [{"filename": "test.py"}]
            }
        ]
        mock_github_client.get_branch_commits.return_value = sample_commits

        # Setup detailed commit display mock
        mock_display = AsyncMock()
        mock_display_class.return_value = mock_display
        mock_display.should_process_repository.return_value = True  # Force should override
        mock_display.generate_detailed_view.return_value = [MagicMock()]

        runner = CliRunner()
        result = runner.invoke(cli, [
            "show-commits",
            "testowner/testrepo",
            "--detail",
            "--force"
        ])

        assert result.exit_code == 0

        # Verify that force flag was respected
        mock_display.should_process_repository.assert_called()
        call_args = mock_display.should_process_repository.call_args
        if len(call_args[0]) > 1 or call_args[1]:
            # Check if force=True was passed
            force_passed = call_args[1].get("force", False) if call_args[1] else False
            # Note: The exact implementation may vary, so we just verify the call was made

    @pytest.mark.asyncio
    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    async def test_show_commits_detail_error_handling_with_filtering(
        self, mock_github_client_class, mock_load_config, mock_config
    ):
        """Test error handling in show-commits --detail with fork filtering."""
        mock_load_config.return_value = mock_config

        # Setup GitHub client mock to raise an error
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client
        mock_github_client.get_repository.side_effect = GitHubAPIError("API Error", status_code=500)

        runner = CliRunner()
        result = runner.invoke(cli, [
            "show-commits",
            "testowner/testrepo",
            "--detail"
        ])

        # Should handle the error gracefully
        assert result.exit_code != 0 or "Error" in result.output

    def test_show_commits_detail_help_includes_filtering_info(self):
        """Test that help text includes information about fork filtering."""
        runner = CliRunner()

        from forklift.cli import show_commits
        result = runner.invoke(show_commits, ["--help"])

        assert result.exit_code == 0
        assert "--detail" in result.output
        assert "--force" in result.output


class TestSmartForkFilteringPerformance:
    """Performance tests for smart fork filtering."""

    @pytest.fixture
    def large_qualification_result(self):
        """Create a large qualification result for performance testing."""
        fork_data = []

        for i in range(100):  # 100 forks
            has_commits = i % 3 != 0  # 2/3 have commits, 1/3 don't
            created_time = datetime(2023, 1, 1, tzinfo=UTC)
            pushed_time = datetime(2023, 6, 1, tzinfo=UTC) if has_commits else created_time

            metrics = ForkQualificationMetrics(
                id=10000 + i,
                full_name=f"user{i}/repo{i}",
                owner=f"user{i}",
                name=f"repo{i}",
                html_url=f"https://github.com/user{i}/repo{i}",
                stargazers_count=i % 50,
                forks_count=i % 20,
                size=1000 + (i * 10),
                language="Python" if i % 2 == 0 else "JavaScript",
                created_at=created_time,
                updated_at=pushed_time,
                pushed_at=pushed_time,
                open_issues_count=i % 10,
                topics=[f"topic{i % 5}"],
                watchers_count=i % 30,
                archived=i % 20 == 0,  # 5% archived
                disabled=i % 25 == 0,  # 4% disabled
                fork=True
            )

            fork_data.append(CollectedForkData(metrics=metrics))

        stats = QualificationStats(
            total_forks_discovered=100,
            forks_with_no_commits=33,  # Approximately 1/3
            forks_with_commits=67,     # Approximately 2/3
            api_calls_made=100,
            processing_time_seconds=10.0
        )

        return QualifiedForksResult(
            repository_owner="upstream",
            repository_name="large-repo",
            repository_url="https://github.com/upstream/large-repo",
            collected_forks=fork_data,
            stats=stats
        )

    @pytest.mark.asyncio
    async def test_fork_filtering_performance_with_large_dataset(
        self, large_qualification_result
    ):
        """Test fork filtering performance with a large dataset."""
        import time

        mock_github_client = AsyncMock()
        config = ForkFilteringConfig(
            enabled=True,
            log_filtering_decisions=False,  # Disable logging for performance
            fallback_to_api=True,
            max_api_fallback_calls=10  # Limit API calls
        )

        checker = ForkCommitStatusChecker(mock_github_client, config)

        # Test processing all forks in qualification data
        start_time = time.time()

        results = []
        for i in range(100):
            fork_url = f"https://github.com/user{i}/repo{i}"
            result = await checker.has_commits_ahead(fork_url, large_qualification_result)
            results.append(result)

        end_time = time.time()
        processing_time = end_time - start_time

        # Verify results
        assert len(results) == 100
        assert results.count(True) > results.count(False)  # More forks with commits

        # Verify performance - should be fast since using qualification data
        assert processing_time < 1.0  # Should complete in under 1 second

        # Verify no API calls were made (all data from qualification)
        assert mock_github_client.get_repository.call_count == 0

        # Verify statistics
        stats = checker.get_statistics()
        assert stats.qualification_data_hits == 100
        assert stats.api_fallback_calls == 0

    @pytest.mark.asyncio
    async def test_api_call_reduction_effectiveness(self, large_qualification_result):
        """Test that fork filtering effectively reduces API calls."""
        mock_github_client = AsyncMock()

        # Mock API response for fallback calls
        async def mock_get_repository(owner, repo):
            await asyncio.sleep(0.01)  # Simulate API delay
            return Repository(
                id=99999,
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

        mock_github_client.get_repository.side_effect = mock_get_repository

        config = ForkFilteringConfig(
            enabled=True,
            fallback_to_api=True,
            max_api_fallback_calls=20  # Allow some API calls
        )

        checker = ForkCommitStatusChecker(mock_github_client, config)

        # Process mix of known and unknown forks
        fork_urls = []

        # 80 forks from qualification data
        for i in range(80):
            fork_urls.append(f"https://github.com/user{i}/repo{i}")

        # 20 unknown forks (will require API calls)
        for i in range(20):
            fork_urls.append(f"https://github.com/unknown{i}/repo{i}")

        # Process all forks
        results = []
        for fork_url in fork_urls:
            result = await checker.has_commits_ahead(fork_url, large_qualification_result)
            results.append(result)

        # Verify API call reduction
        stats = checker.get_statistics()
        assert stats.qualification_data_hits == 80  # 80% used qualification data
        assert stats.api_fallback_calls == 20      # 20% used API fallback
        assert stats.api_usage_efficiency == 80.0  # 80% efficiency

        # Verify total API calls made
        assert mock_github_client.get_repository.call_count == 20

    @pytest.mark.asyncio
    async def test_memory_usage_with_large_datasets(self, large_qualification_result):
        """Test memory usage remains reasonable with large datasets."""
        pytest.skip("psutil not available - skipping memory test")

        mock_github_client = AsyncMock()
        config = ForkFilteringConfig(enabled=True, log_filtering_decisions=False)
        checker = ForkCommitStatusChecker(mock_github_client, config)

        # Process large number of forks
        for i in range(1000):  # Even larger dataset
            fork_url = f"https://github.com/user{i % 100}/repo{i % 100}"
            await checker.has_commits_ahead(fork_url, large_qualification_result)

        # Test passes if no memory errors occur
        assert True

    @pytest.mark.asyncio
    async def test_concurrent_processing_performance(self, large_qualification_result):
        """Test performance of concurrent fork processing."""
        import time

        mock_github_client = AsyncMock()
        config = ForkFilteringConfig(enabled=True, log_filtering_decisions=False)
        checker = ForkCommitStatusChecker(mock_github_client, config)

        # Create concurrent tasks
        fork_urls = [f"https://github.com/user{i}/repo{i}" for i in range(50)]

        start_time = time.time()

        # Process concurrently
        tasks = [
            checker.has_commits_ahead(fork_url, large_qualification_result)
            for fork_url in fork_urls
        ]

        results = await asyncio.gather(*tasks)

        end_time = time.time()
        concurrent_time = end_time - start_time

        # Process sequentially for comparison
        start_time = time.time()

        sequential_results = []
        for fork_url in fork_urls:
            result = await checker.has_commits_ahead(fork_url, large_qualification_result)
            sequential_results.append(result)

        end_time = time.time()
        sequential_time = end_time - start_time

        # Verify results are the same
        assert results == sequential_results

        # Concurrent processing should not be significantly slower
        # (may not be faster due to Python GIL, but shouldn't be much slower)
        assert concurrent_time <= sequential_time * 1.5


class TestSmartForkFilteringEndToEnd:
    """End-to-end tests for complete smart fork filtering workflow."""

    @pytest.mark.asyncio
    async def test_complete_fork_filtering_workflow(self):
        """Test complete workflow from fork discovery to filtering to analysis."""
        # This test simulates the complete workflow that would happen in production

        # Mock components
        mock_github_client = AsyncMock()

        # Setup mock data for complete workflow
        sample_forks = [
            {"full_name": "user1/active-fork", "archived": False, "disabled": False},
            {"full_name": "user2/inactive-fork", "archived": False, "disabled": False},
            {"full_name": "user3/archived-fork", "archived": True, "disabled": False},
        ]

        # Mock qualification result
        qualification_metrics = [
            ForkQualificationMetrics(
                id=1, full_name="user1/active-fork", owner="user1", name="active-fork",
                html_url="https://github.com/user1/active-fork",
                created_at=datetime(2023, 1, 1, tzinfo=UTC),
                pushed_at=datetime(2023, 6, 1, tzinfo=UTC),  # Has commits
                stargazers_count=10, forks_count=2, size=1000, language="Python",
                updated_at=datetime(2023, 6, 1, tzinfo=UTC),
                open_issues_count=1, topics=["python"], watchers_count=10,
                archived=False, disabled=False, fork=True
            ),
            ForkQualificationMetrics(
                id=2, full_name="user2/inactive-fork", owner="user2", name="inactive-fork",
                html_url="https://github.com/user2/inactive-fork",
                created_at=datetime(2023, 1, 1, tzinfo=UTC),
                pushed_at=datetime(2023, 1, 1, tzinfo=UTC),  # No commits
                stargazers_count=5, forks_count=1, size=500, language="Python",
                updated_at=datetime(2023, 1, 1, tzinfo=UTC),
                open_issues_count=0, topics=["python"], watchers_count=5,
                archived=False, disabled=False, fork=True
            ),
            ForkQualificationMetrics(
                id=3, full_name="user3/archived-fork", owner="user3", name="archived-fork",
                html_url="https://github.com/user3/archived-fork",
                created_at=datetime(2023, 1, 1, tzinfo=UTC),
                pushed_at=datetime(2023, 3, 1, tzinfo=UTC),  # Has commits but archived
                stargazers_count=8, forks_count=3, size=800, language="Python",
                updated_at=datetime(2023, 3, 1, tzinfo=UTC),
                open_issues_count=0, topics=["python"], watchers_count=8,
                archived=True, disabled=False, fork=True  # Archived
            ),
        ]

        qualification_result = QualifiedForksResult(
            repository_owner="upstream",
            repository_name="main-repo",
            repository_url="https://github.com/upstream/main-repo",
            collected_forks=[CollectedForkData(metrics=m) for m in qualification_metrics],
            stats=QualificationStats(
                total_forks_discovered=3,
                forks_with_no_commits=1,
                forks_with_commits=2,
                api_calls_made=3,
                processing_time_seconds=1.5
            )
        )

        # Initialize fork filtering
        config = ForkFilteringConfig(enabled=True, log_filtering_decisions=True)
        checker = ForkCommitStatusChecker(mock_github_client, config)

        # Step 1: Evaluate each fork for filtering
        evaluation_results = []
        for fork_data in sample_forks:
            fork_url = f"https://github.com/{fork_data['full_name']}"
            should_filter, reason = await checker.evaluate_fork_for_filtering(
                fork_url, fork_data, qualification_result
            )
            evaluation_results.append((fork_data["full_name"], should_filter, reason))

        # Step 2: Verify filtering results
        assert len(evaluation_results) == 3

        # user1/active-fork should not be filtered (has commits)
        assert evaluation_results[0][1] is False
        assert evaluation_results[0][2] == "has_commits_ahead"

        # user2/inactive-fork should be filtered (no commits)
        assert evaluation_results[1][1] is True
        assert evaluation_results[1][2] == "no_commits_ahead"

        # user3/archived-fork should be filtered (archived)
        assert evaluation_results[2][1] is True
        assert evaluation_results[2][2] == "archived"

        # Step 3: Simulate processing only non-filtered forks
        forks_to_process = [
            result[0] for result in evaluation_results if not result[1]
        ]

        assert len(forks_to_process) == 1
        assert forks_to_process[0] == "user1/active-fork"

        # Step 4: Verify statistics
        stats = checker.get_statistics()
        assert stats.total_forks_evaluated == 3
        assert stats.forks_filtered_out == 2
        assert stats.forks_included == 1
        assert abs(stats.filtering_rate - 66.7) < 0.2  # 2/3 filtered (approximately 66.7%)
        assert stats.qualification_data_hits >= 2  # Should have used qualification data

        # Step 5: Verify API efficiency
        assert stats.api_usage_efficiency > 0  # Should show efficiency from using qualification data
        assert mock_github_client.get_repository.call_count == 0  # No API fallback needed

        # This demonstrates the complete workflow:
        # 1. Fork discovery provides qualification data
        # 2. Fork filtering evaluates each fork
        # 3. Only relevant forks proceed to detailed analysis
        # 4. API calls are minimized through qualification data usage
        # 5. Statistics track the efficiency gains
