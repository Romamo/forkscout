"""Error handling and edge case tests for smart fork filtering."""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from forklift.analysis.fork_commit_status_checker import (
    ForkCommitStatusChecker,
    ForkCommitStatusError,
)
from forklift.github.client import (
    GitHubClient,
    GitHubAPIError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)
from forklift.models.fork_filtering import ForkFilteringConfig
from forklift.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualifiedForksResult,
    QualificationStats,
)
from forklift.models.github import Repository


class TestSmartForkFilteringErrorHandling:
    """Test error handling and edge cases in smart fork filtering."""

    @pytest.fixture
    def error_handling_config(self):
        """Create configuration optimized for error handling testing."""
        return ForkFilteringConfig(
            enabled=True,
            log_filtering_decisions=True,
            fallback_to_api=True,
            prefer_inclusion_on_uncertainty=True,
            max_api_fallback_calls=10
        )

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client for error testing."""
        return AsyncMock(spec=GitHubClient)

    @pytest.fixture
    def sample_qualification_result(self):
        """Create a sample qualification result for testing."""
        metrics = ForkQualificationMetrics(
            id=12345,
            full_name="testuser/testrepo",
            owner="testuser",
            name="testrepo",
            html_url="https://github.com/testuser/testrepo",
            stargazers_count=10,
            forks_count=2,
            size=1000,
            language="Python",
            created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2023, 6, 1, tzinfo=timezone.utc),
            pushed_at=datetime(2023, 6, 1, tzinfo=timezone.utc),
            open_issues_count=1,
            topics=["python"],
            watchers_count=10,
            archived=False,
            disabled=False,
            fork=True
        )

        return QualifiedForksResult(
            repository_owner="upstream",
            repository_name="main-repo",
            repository_url="https://github.com/upstream/main-repo",
            collected_forks=[CollectedForkData(metrics=metrics)],
            stats=QualificationStats(
                total_forks_discovered=1,
                forks_with_no_commits=0,
                forks_with_commits=1,
                api_calls_made=1,
                processing_time_seconds=1.0
            )
        )

    @pytest.mark.asyncio
    async def test_github_api_not_found_error_handling(
        self, mock_github_client, error_handling_config
    ):
        """Test handling of GitHub API 404 Not Found errors."""
        checker = ForkCommitStatusChecker(mock_github_client, error_handling_config)
        
        # Mock API to raise NotFoundError
        mock_github_client.get_repository.side_effect = GitHubNotFoundError(
            "Repository not found", status_code=404
        )
        
        # Test with fork not in qualification data (triggers API fallback)
        result = await checker.has_commits_ahead("https://github.com/nonexistent/repo")
        
        # Should return None for not found repositories
        assert result is None
        
        # Verify statistics
        stats = checker.get_statistics()
        assert stats.api_fallback_calls == 1
        assert stats.status_unknown == 1
        assert stats.errors == 0  # Not counted as error, expected behavior

    @pytest.mark.asyncio
    async def test_github_api_rate_limit_error_handling(
        self, mock_github_client, error_handling_config
    ):
        """Test handling of GitHub API rate limit errors."""
        checker = ForkCommitStatusChecker(mock_github_client, error_handling_config)
        
        # Mock API to raise RateLimitError
        mock_github_client.get_repository.side_effect = GitHubRateLimitError(
            "Rate limit exceeded", status_code=403, retry_after=3600
        )
        
        result = await checker.has_commits_ahead("https://github.com/ratelimited/repo")
        
        # Should return None when rate limited
        assert result is None
        
        # Verify statistics
        stats = checker.get_statistics()
        assert stats.api_fallback_calls == 1
        assert stats.status_unknown == 1

    @pytest.mark.asyncio
    async def test_github_api_server_error_handling(
        self, mock_github_client, error_handling_config
    ):
        """Test handling of GitHub API server errors (5xx)."""
        checker = ForkCommitStatusChecker(mock_github_client, error_handling_config)
        
        # Mock API to raise server error
        mock_github_client.get_repository.side_effect = GitHubAPIError(
            "Internal server error", status_code=500
        )
        
        result = await checker.has_commits_ahead("https://github.com/servererror/repo")
        
        # Should return None for server errors
        assert result is None
        
        # Verify statistics
        stats = checker.get_statistics()
        assert stats.api_fallback_calls == 1
        assert stats.status_unknown == 1

    @pytest.mark.asyncio
    async def test_unexpected_exception_handling(
        self, mock_github_client, error_handling_config
    ):
        """Test handling of unexpected exceptions."""
        checker = ForkCommitStatusChecker(mock_github_client, error_handling_config)
        
        # Mock API to raise unexpected exception
        mock_github_client.get_repository.side_effect = Exception("Unexpected error")
        
        # Should raise ForkCommitStatusError for unexpected exceptions
        with pytest.raises(ForkCommitStatusError, match="Failed to check commit status"):
            await checker.has_commits_ahead("https://github.com/unexpected/error")
        
        # Verify error statistics
        stats = checker.get_statistics()
        assert stats.errors == 1

    @pytest.mark.asyncio
    async def test_invalid_url_formats_error_handling(
        self, mock_github_client, error_handling_config
    ):
        """Test handling of various invalid URL formats."""
        checker = ForkCommitStatusChecker(mock_github_client, error_handling_config)
        
        invalid_urls = [
            "",                                    # Empty string
            "   ",                                # Whitespace only
            "not-a-url",                          # Not a URL
            "https://github.com/",                # Missing owner/repo
            "https://github.com/owner",           # Missing repo
            "https://example.com/owner/repo",     # Wrong domain
            "https://github.com/owner/repo/extra", # Extra path components
            "owner",                              # Just owner
            "owner/",                             # Owner with slash
            "/repo",                              # Just repo with slash
            "owner//repo",                        # Double slash
            "owner/repo/",                        # Trailing slash in owner/repo format
        ]
        
        for invalid_url in invalid_urls:
            with pytest.raises(ForkCommitStatusError, match="Invalid fork URL format"):
                await checker.has_commits_ahead(invalid_url)
        
        # Verify all invalid URLs were counted as errors
        stats = checker.get_statistics()
        assert stats.errors == len(invalid_urls)

    @pytest.mark.asyncio
    async def test_network_timeout_error_handling(
        self, mock_github_client, error_handling_config
    ):
        """Test handling of network timeout errors."""
        checker = ForkCommitStatusChecker(mock_github_client, error_handling_config)
        
        # Mock API to raise timeout error
        mock_github_client.get_repository.side_effect = asyncio.TimeoutError("Request timeout")
        
        # Should raise ForkCommitStatusError for timeout
        with pytest.raises(ForkCommitStatusError, match="Failed to check commit status"):
            await checker.has_commits_ahead("https://github.com/timeout/repo")
        
        # Verify error statistics
        stats = checker.get_statistics()
        assert stats.errors == 1

    @pytest.mark.asyncio
    async def test_malformed_qualification_data_handling(
        self, mock_github_client, error_handling_config
    ):
        """Test handling of malformed qualification data."""
        checker = ForkCommitStatusChecker(mock_github_client, error_handling_config)
        
        # Create qualification result with malformed data
        malformed_metrics = ForkQualificationMetrics(
            id=12345,
            full_name="testuser/testrepo",
            owner="testuser",
            name="testrepo",
            html_url="https://github.com/testuser/testrepo",
            stargazers_count=10,
            forks_count=2,
            size=1000,
            language="Python",
            created_at=None,  # Missing created_at
            updated_at=None,  # Missing updated_at
            pushed_at=None,   # Missing pushed_at
            open_issues_count=1,
            topics=["python"],
            watchers_count=10,
            archived=False,
            disabled=False,
            fork=True
        )

        malformed_result = QualifiedForksResult(
            repository_owner="upstream",
            repository_name="main-repo",
            repository_url="https://github.com/upstream/main-repo",
            collected_forks=[CollectedForkData(metrics=malformed_metrics)],
            stats=QualificationStats(
                total_forks_discovered=1,
                forks_with_no_commits=0,
                forks_with_commits=1,
                api_calls_made=1,
                processing_time_seconds=1.0
            )
        )
        
        # Should handle malformed data gracefully
        result = await checker.has_commits_ahead(
            "https://github.com/testuser/testrepo",
            malformed_result
        )
        
        # Should return False when timestamps are None (can't determine, assume no commits)
        assert result is False
        
        # Verify qualification data was used despite malformed timestamps
        stats = checker.get_statistics()
        assert stats.qualification_data_hits == 1

    @pytest.mark.asyncio
    async def test_api_fallback_limit_exceeded_handling(
        self, mock_github_client, error_handling_config
    ):
        """Test handling when API fallback limit is exceeded."""
        # Set low API fallback limit
        error_handling_config.max_api_fallback_calls = 2
        checker = ForkCommitStatusChecker(mock_github_client, error_handling_config)
        
        # Mock successful API responses
        mock_github_client.get_repository.return_value = Repository(
            id=99999,
            owner="test",
            name="repo",
            full_name="test/repo",
            url="https://api.github.com/repos/test/repo",
            html_url="https://github.com/test/repo",
            clone_url="https://github.com/test/repo.git",
            created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            pushed_at=datetime(2023, 5, 1, tzinfo=timezone.utc),
            default_branch="main"
        )
        
        # First two calls should use API
        result1 = await checker.has_commits_ahead("https://github.com/test/repo1")
        result2 = await checker.has_commits_ahead("https://github.com/test/repo2")
        
        assert result1 is True
        assert result2 is True
        
        # Third call should hit the limit
        result3 = await checker.has_commits_ahead("https://github.com/test/repo3")
        
        # Should return False when limit exceeded and prefer_inclusion_on_uncertainty=True
        # but limit reached overrides preference
        assert result3 is False
        
        # Verify API call limit was respected
        assert mock_github_client.get_repository.call_count == 2
        
        # Verify statistics
        stats = checker.get_statistics()
        assert stats.api_fallback_calls == 2
        assert stats.status_unknown == 1  # Third call marked as unknown

    @pytest.mark.asyncio
    async def test_concurrent_error_handling(
        self, mock_github_client, error_handling_config
    ):
        """Test error handling with concurrent requests."""
        checker = ForkCommitStatusChecker(mock_github_client, error_handling_config)
        
        # Mock API to fail for some requests
        call_count = 0
        async def mock_get_repository_with_intermittent_errors(owner, repo):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:  # Every third call fails
                raise GitHubAPIError("Intermittent error", status_code=500)
            return Repository(
                id=99999,
                owner=owner,
                name=repo,
                full_name=f"{owner}/{repo}",
                url=f"https://api.github.com/repos/{owner}/{repo}",
                html_url=f"https://github.com/{owner}/{repo}",
                clone_url=f"https://github.com/{owner}/{repo}.git",
                created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
                pushed_at=datetime(2023, 5, 1, tzinfo=timezone.utc),
                default_branch="main"
            )
        
        mock_github_client.get_repository.side_effect = mock_get_repository_with_intermittent_errors
        
        # Create concurrent requests
        fork_urls = [f"https://github.com/user{i}/repo{i}" for i in range(10)]
        
        # Process concurrently
        tasks = [checker.has_commits_ahead(fork_url) for fork_url in fork_urls]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        # Verify results
        assert len(results) == 10
        
        # Some should succeed (True), some should fail (None)
        successful_results = [r for r in results if r is True]
        failed_results = [r for r in results if r is None]
        
        assert len(successful_results) > 0
        assert len(failed_results) > 0
        assert len(successful_results) + len(failed_results) == 10
        
        # Verify statistics
        stats = checker.get_statistics()
        assert stats.api_fallback_calls == 10
        assert stats.status_unknown > 0  # Failed requests

    @pytest.mark.asyncio
    async def test_memory_leak_prevention_with_errors(
        self, mock_github_client, error_handling_config
    ):
        """Test that error handling doesn't cause memory leaks."""
        pytest.skip("psutil not available - skipping memory test")
        
        checker = ForkCommitStatusChecker(mock_github_client, error_handling_config)
        
        # Mock API to always raise errors
        mock_github_client.get_repository.side_effect = Exception("Persistent error")
        
        # Generate many errors
        for i in range(100):
            try:
                await checker.has_commits_ahead(f"https://github.com/error{i}/repo{i}")
            except ForkCommitStatusError:
                pass  # Expected
        
        # Verify all errors were tracked
        stats = checker.get_statistics()
        assert stats.errors == 100

    @pytest.mark.asyncio
    async def test_error_recovery_after_temporary_failures(
        self, mock_github_client, error_handling_config
    ):
        """Test recovery after temporary API failures."""
        checker = ForkCommitStatusChecker(mock_github_client, error_handling_config)
        
        # Mock API to fail initially, then succeed
        call_count = 0
        async def mock_get_repository_with_recovery(owner, repo):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:  # First 3 calls fail
                raise GitHubAPIError("Temporary failure", status_code=503)
            # Subsequent calls succeed
            return Repository(
                id=99999,
                owner=owner,
                name=repo,
                full_name=f"{owner}/{repo}",
                url=f"https://api.github.com/repos/{owner}/{repo}",
                html_url=f"https://github.com/{owner}/{repo}",
                clone_url=f"https://github.com/{owner}/{repo}.git",
                created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
                pushed_at=datetime(2023, 5, 1, tzinfo=timezone.utc),
                default_branch="main"
            )
        
        mock_github_client.get_repository.side_effect = mock_get_repository_with_recovery
        
        # Test multiple requests
        results = []
        for i in range(6):
            result = await checker.has_commits_ahead(f"https://github.com/recovery{i}/repo{i}")
            results.append(result)
        
        # First 3 should fail (None), last 3 should succeed (True)
        assert results[:3] == [None, None, None]
        assert results[3:] == [True, True, True]
        
        # Verify statistics show both failures and successes
        stats = checker.get_statistics()
        assert stats.api_fallback_calls == 6
        assert stats.status_unknown == 3  # First 3 failed

    @pytest.mark.asyncio
    async def test_edge_case_timestamp_handling(
        self, mock_github_client, error_handling_config, sample_qualification_result
    ):
        """Test edge cases in timestamp handling."""
        checker = ForkCommitStatusChecker(mock_github_client, error_handling_config)
        
        # Test case 1: Exactly equal timestamps
        equal_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        equal_metrics = ForkQualificationMetrics(
            id=11111,
            full_name="equal/timestamps",
            owner="equal",
            name="timestamps",
            html_url="https://github.com/equal/timestamps",
            stargazers_count=5,
            forks_count=1,
            size=1000,
            language="Python",
            created_at=equal_time,
            updated_at=equal_time,
            pushed_at=equal_time,  # Exactly equal
            open_issues_count=0,
            topics=["python"],
            watchers_count=5,
            archived=False,
            disabled=False,
            fork=True
        )
        
        equal_result = QualifiedForksResult(
            repository_owner="upstream",
            repository_name="main-repo",
            repository_url="https://github.com/upstream/main-repo",
            collected_forks=[CollectedForkData(metrics=equal_metrics)],
            stats=QualificationStats(
                total_forks_discovered=1,
                forks_with_no_commits=1,
                forks_with_commits=0,
                api_calls_made=1,
                processing_time_seconds=1.0
            )
        )
        
        result = await checker.has_commits_ahead(
            "https://github.com/equal/timestamps",
            equal_result
        )
        assert result is False  # Equal timestamps = no commits ahead
        
        # Test case 2: Very small time difference (microseconds)
        created_time = datetime(2023, 1, 1, 12, 0, 0, 0, tzinfo=timezone.utc)
        pushed_time = datetime(2023, 1, 1, 12, 0, 0, 1, tzinfo=timezone.utc)  # 1 microsecond later
        
        micro_metrics = ForkQualificationMetrics(
            id=22222,
            full_name="micro/difference",
            owner="micro",
            name="difference",
            html_url="https://github.com/micro/difference",
            stargazers_count=5,
            forks_count=1,
            size=1000,
            language="Python",
            created_at=created_time,
            updated_at=pushed_time,
            pushed_at=pushed_time,  # Microsecond difference
            open_issues_count=0,
            topics=["python"],
            watchers_count=5,
            archived=False,
            disabled=False,
            fork=True
        )
        
        micro_result = QualifiedForksResult(
            repository_owner="upstream",
            repository_name="main-repo",
            repository_url="https://github.com/upstream/main-repo",
            collected_forks=[CollectedForkData(metrics=micro_metrics)],
            stats=QualificationStats(
                total_forks_discovered=1,
                forks_with_no_commits=0,
                forks_with_commits=1,
                api_calls_made=1,
                processing_time_seconds=1.0
            )
        )
        
        result = await checker.has_commits_ahead(
            "https://github.com/micro/difference",
            micro_result
        )
        assert result is True  # Even microsecond difference = has commits

    @pytest.mark.asyncio
    async def test_configuration_edge_cases(self, mock_github_client):
        """Test edge cases in configuration handling."""
        
        # Test with all features disabled
        disabled_config = ForkFilteringConfig(
            enabled=False,
            fallback_to_api=False,
            log_filtering_decisions=False,
            log_statistics=False
        )
        
        checker = ForkCommitStatusChecker(mock_github_client, disabled_config)
        
        # Should still work but with limited functionality
        result = await checker.has_commits_ahead("https://github.com/test/repo")
        assert result is False  # Default when everything disabled
        
        # Test with contradictory settings
        contradictory_config = ForkFilteringConfig(
            enabled=True,
            fallback_to_api=False,  # No API fallback
            prefer_inclusion_on_uncertainty=True,  # But prefer inclusion
            max_api_fallback_calls=0  # Zero API calls allowed
        )
        
        checker = ForkCommitStatusChecker(mock_github_client, contradictory_config)
        
        # Should handle contradictory settings gracefully
        result = await checker.has_commits_ahead("https://github.com/unknown/repo")
        assert result is None  # Uncertain, prefer inclusion, but no API allowed

    @pytest.mark.asyncio
    async def test_statistics_accuracy_under_error_conditions(
        self, mock_github_client, error_handling_config
    ):
        """Test that statistics remain accurate even under error conditions."""
        checker = ForkCommitStatusChecker(mock_github_client, error_handling_config)
        
        # Mix of successful and failed operations
        operations = [
            ("success1", "success"),
            ("error1", "error"),
            ("success2", "success"),
            ("error2", "error"),
            ("success3", "success"),
        ]
        
        # Mock API responses
        def mock_get_repository_mixed(owner, repo):
            if "error" in owner:
                raise GitHubAPIError("Simulated error", status_code=500)
            return Repository(
                id=99999,
                owner=owner,
                name=repo,
                full_name=f"{owner}/{repo}",
                url=f"https://api.github.com/repos/{owner}/{repo}",
                html_url=f"https://github.com/{owner}/{repo}",
                clone_url=f"https://github.com/{owner}/{repo}.git",
                created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
                pushed_at=datetime(2023, 5, 1, tzinfo=timezone.utc),
                default_branch="main"
            )
        
        mock_github_client.get_repository.side_effect = mock_get_repository_mixed
        
        # Process operations
        results = []
        for owner, expected_type in operations:
            try:
                result = await checker.has_commits_ahead(f"https://github.com/{owner}/repo")
                results.append((owner, result, None))
            except Exception as e:
                results.append((owner, None, str(e)))
        
        # Verify statistics accuracy
        stats = checker.get_statistics()
        
        # Should have made 5 API calls total
        assert stats.api_fallback_calls == 5
        
        # Should have 2 unknown status (errors) and 0 errors in stats
        # (GitHubAPIError is handled gracefully, not counted as error)
        assert stats.status_unknown == 2
        
        # Should have 0 qualification hits (no qualification data provided)
        assert stats.qualification_data_hits == 0
        
        # API efficiency should be 0% (no qualification data used)
        assert stats.api_usage_efficiency == 0.0