"""Unit tests for show-forks --show-commits optimization functionality."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console

from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.github.client import GitHubClient
from forklift.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualifiedForksResult,
    QualificationStats,
)
from forklift.models.github import RecentCommit


class TestShowForksCommitsOptimization:
    """Test suite for show-forks --show-commits optimization."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        client = AsyncMock(spec=GitHubClient)
        return client

    @pytest.fixture
    def console(self):
        """Create a Rich console for testing."""
        return Console(file=MagicMock(), width=80)

    @pytest.fixture
    def display_service(self, mock_github_client, console):
        """Create a repository display service for testing."""
        return RepositoryDisplayService(mock_github_client, console)

    @pytest.fixture
    def sample_fork_data_with_commits(self):
        """Create sample fork data that has commits ahead."""
        created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        pushed_at = datetime(2023, 6, 1, tzinfo=timezone.utc)  # Later than created_at
        
        metrics = ForkQualificationMetrics(
            id=123,
            name="test-fork",
            full_name="user/test-fork",
            owner="user",
            html_url="https://github.com/user/test-fork",
            stargazers_count=10,
            forks_count=2,
            watchers_count=5,
            size=1000,
            language="Python",
            topics=["test"],
            open_issues_count=1,
            created_at=created_at,
            updated_at=pushed_at,
            pushed_at=pushed_at,
            archived=False,
            disabled=False,
            fork=True,
        )
        
        return CollectedForkData(
            metrics=metrics,
            activity_summary="Active fork",
        )

    @pytest.fixture
    def sample_fork_data_no_commits(self):
        """Create sample fork data that has no commits ahead."""
        created_at = datetime(2023, 6, 1, tzinfo=timezone.utc)
        pushed_at = datetime(2023, 1, 1, tzinfo=timezone.utc)  # Earlier than created_at
        
        metrics = ForkQualificationMetrics(
            id=456,
            name="empty-fork",
            full_name="user/empty-fork",
            owner="user",
            html_url="https://github.com/user/empty-fork",
            stargazers_count=0,
            forks_count=0,
            watchers_count=0,
            size=100,
            language=None,
            topics=[],
            open_issues_count=0,
            created_at=created_at,
            updated_at=created_at,
            pushed_at=pushed_at,
            archived=False,
            disabled=False,
            fork=True,
        )
        
        return CollectedForkData(
            metrics=metrics,
            activity_summary="No commits",
        )

    @pytest.fixture
    def sample_recent_commits(self):
        """Create sample recent commits."""
        return [
            RecentCommit(
                short_sha="abc123d",
                message="Add new feature",
            ),
            RecentCommit(
                short_sha="def4567",
                message="Fix bug",
            ),
        ]

    @pytest.mark.asyncio
    async def test_fetch_commits_concurrently_optimization_enabled(
        self, display_service, sample_fork_data_with_commits, sample_fork_data_no_commits, sample_recent_commits
    ):
        """Test that _fetch_commits_concurrently skips forks with no commits ahead by default."""
        # Setup
        forks_data = [sample_fork_data_with_commits, sample_fork_data_no_commits]
        
        # Mock the GitHub client to return commits for the fork with commits
        display_service.github_client.get_recent_commits.return_value = sample_recent_commits
        
        # Test with optimization enabled (default)
        result = await display_service._fetch_commits_concurrently(forks_data, show_commits=2, force_all_commits=False)
        
        # Verify results
        assert len(result) == 2
        assert "user/test-fork" in result
        assert "user/empty-fork" in result
        
        # Fork with commits should have actual commit data
        assert "abc123d: Add new feature" in result["user/test-fork"]
        
        # Fork without commits should be marked as "No commits ahead"
        assert result["user/empty-fork"] == "[dim]No commits ahead[/dim]"
        
        # Verify API was only called for the fork with commits
        display_service.github_client.get_recent_commits.assert_called_once_with("user", "test-fork", count=2)

    @pytest.mark.asyncio
    async def test_fetch_commits_concurrently_optimization_disabled(
        self, display_service, sample_fork_data_with_commits, sample_fork_data_no_commits, sample_recent_commits
    ):
        """Test that _fetch_commits_concurrently fetches commits for all forks when force_all_commits=True."""
        # Setup
        forks_data = [sample_fork_data_with_commits, sample_fork_data_no_commits]
        
        # Mock the GitHub client to return commits for both forks
        display_service.github_client.get_recent_commits.return_value = sample_recent_commits
        
        # Test with optimization disabled
        result = await display_service._fetch_commits_concurrently(forks_data, show_commits=2, force_all_commits=True)
        
        # Verify results
        assert len(result) == 2
        assert "user/test-fork" in result
        assert "user/empty-fork" in result
        
        # Both forks should have actual commit data (or attempt to fetch)
        assert "abc123d: Add new feature" in result["user/test-fork"]
        assert "abc123d: Add new feature" in result["user/empty-fork"]
        
        # Verify API was called for both forks
        assert display_service.github_client.get_recent_commits.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_commits_concurrently_no_commits_requested(
        self, display_service, sample_fork_data_with_commits, sample_fork_data_no_commits
    ):
        """Test that _fetch_commits_concurrently returns empty dict when show_commits=0."""
        # Setup
        forks_data = [sample_fork_data_with_commits, sample_fork_data_no_commits]
        
        # Test with no commits requested
        result = await display_service._fetch_commits_concurrently(forks_data, show_commits=0)
        
        # Verify no commits are fetched
        assert result == {}
        display_service.github_client.get_recent_commits.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_commits_concurrently_empty_forks_list(self, display_service):
        """Test that _fetch_commits_concurrently handles empty forks list."""
        # Test with empty forks list
        result = await display_service._fetch_commits_concurrently([], show_commits=2)
        
        # Verify no commits are fetched
        assert result == {}
        display_service.github_client.get_recent_commits.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_commits_concurrently_api_error_handling(
        self, display_service, sample_fork_data_with_commits
    ):
        """Test that _fetch_commits_concurrently handles API errors gracefully."""
        # Setup
        forks_data = [sample_fork_data_with_commits]
        
        # Mock the GitHub client to raise an exception
        display_service.github_client.get_recent_commits.side_effect = Exception("API Error")
        
        # Test error handling
        result = await display_service._fetch_commits_concurrently(forks_data, show_commits=2)
        
        # Verify error is handled gracefully
        assert len(result) == 1
        assert "user/test-fork" in result
        assert result["user/test-fork"] == "[dim]No commits available[/dim]"

    def test_can_skip_analysis_property(self, sample_fork_data_with_commits, sample_fork_data_no_commits):
        """Test that can_skip_analysis property correctly identifies forks with no commits ahead."""
        # Fork with commits should not be skippable
        assert not sample_fork_data_with_commits.metrics.can_skip_analysis
        assert sample_fork_data_with_commits.metrics.commits_ahead_status == "Has commits"
        
        # Fork without commits should be skippable
        assert sample_fork_data_no_commits.metrics.can_skip_analysis
        assert sample_fork_data_no_commits.metrics.commits_ahead_status == "No commits ahead"

    @pytest.mark.asyncio
    async def test_optimization_statistics_logging(
        self, display_service, sample_fork_data_with_commits, sample_fork_data_no_commits, sample_recent_commits
    ):
        """Test that optimization statistics are properly logged and displayed."""
        # Setup
        forks_data = [sample_fork_data_with_commits, sample_fork_data_no_commits]
        display_service.github_client.get_recent_commits.return_value = sample_recent_commits
        
        # Capture console output
        console_output = []
        original_print = display_service.console.print
        display_service.console.print = lambda *args, **kwargs: console_output.append(str(args[0]) if args else "")
        
        try:
            # Test optimization
            await display_service._fetch_commits_concurrently(forks_data, show_commits=2, force_all_commits=False)
            
            # Verify statistics are displayed
            output_text = " ".join(console_output)
            assert "Skipped 1 forks with no commits ahead" in output_text
            assert "saved 1 API calls" in output_text
            assert "50.0% reduction" in output_text
            
        finally:
            # Restore original print function
            display_service.console.print = original_print

    @pytest.mark.asyncio
    async def test_mixed_fork_types_optimization(
        self, display_service, sample_recent_commits
    ):
        """Test optimization with a mix of fork types (with/without commits, archived, etc.)."""
        # Create various fork types
        created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        pushed_at_later = datetime(2023, 6, 1, tzinfo=timezone.utc)
        pushed_at_earlier = datetime(2022, 12, 1, tzinfo=timezone.utc)
        
        # Fork with commits
        fork_with_commits = CollectedForkData(
            metrics=ForkQualificationMetrics(
                id=1, name="fork1", full_name="user/fork1", owner="user",
                html_url="https://github.com/user/fork1", stargazers_count=5,
                forks_count=1, watchers_count=3, size=500, language="Python",
                topics=[], open_issues_count=0, created_at=created_at,
                updated_at=pushed_at_later, pushed_at=pushed_at_later,
                archived=False, disabled=False, fork=True
            ),
            activity_summary="Active"
        )
        
        # Fork without commits
        fork_no_commits = CollectedForkData(
            metrics=ForkQualificationMetrics(
                id=2, name="fork2", full_name="user/fork2", owner="user",
                html_url="https://github.com/user/fork2", stargazers_count=0,
                forks_count=0, watchers_count=0, size=100, language=None,
                topics=[], open_issues_count=0, created_at=created_at,
                updated_at=created_at, pushed_at=pushed_at_earlier,
                archived=False, disabled=False, fork=True
            ),
            activity_summary="No commits"
        )
        
        # Archived fork (should still be optimized)
        fork_archived = CollectedForkData(
            metrics=ForkQualificationMetrics(
                id=3, name="fork3", full_name="user/fork3", owner="user",
                html_url="https://github.com/user/fork3", stargazers_count=2,
                forks_count=0, watchers_count=1, size=200, language="Python",
                topics=[], open_issues_count=0, created_at=created_at,
                updated_at=created_at, pushed_at=pushed_at_earlier,
                archived=True, disabled=False, fork=True
            ),
            activity_summary="Archived"
        )
        
        forks_data = [fork_with_commits, fork_no_commits, fork_archived]
        display_service.github_client.get_recent_commits.return_value = sample_recent_commits
        
        # Test optimization
        result = await display_service._fetch_commits_concurrently(forks_data, show_commits=2, force_all_commits=False)
        
        # Verify results
        assert len(result) == 3
        
        # Only fork with commits should have API call made
        assert "abc123d: Add new feature" in result["user/fork1"]
        assert result["user/fork2"] == "[dim]No commits ahead[/dim]"
        assert result["user/fork3"] == "[dim]No commits ahead[/dim]"
        
        # Verify only one API call was made
        display_service.github_client.get_recent_commits.assert_called_once_with("user", "fork1", count=2)

    def test_format_recent_commits(self, display_service, sample_recent_commits):
        """Test that recent commits are formatted correctly."""
        result = display_service.format_recent_commits(sample_recent_commits)
        
        expected = "abc123d: Add new feature\ndef4567: Fix bug"
        assert result == expected

    def test_format_recent_commits_empty(self, display_service):
        """Test that empty commits list is handled correctly."""
        result = display_service.format_recent_commits([])
        
        assert result == "[dim]No commits[/dim]"

    @pytest.mark.asyncio
    async def test_rate_limiting_in_concurrent_fetch(
        self, display_service, sample_fork_data_with_commits, sample_recent_commits
    ):
        """Test that rate limiting is properly implemented in concurrent fetch."""
        # Setup multiple forks that need commits
        forks_data = []
        for i in range(10):
            created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
            pushed_at = datetime(2023, 6, 1, tzinfo=timezone.utc)
            
            fork_data = CollectedForkData(
                metrics=ForkQualificationMetrics(
                    id=i, name=f"fork{i}", full_name=f"user/fork{i}", owner="user",
                    html_url=f"https://github.com/user/fork{i}", stargazers_count=i,
                    forks_count=0, watchers_count=0, size=100, language="Python",
                    topics=[], open_issues_count=0, created_at=created_at,
                    updated_at=pushed_at, pushed_at=pushed_at,
                    archived=False, disabled=False, fork=True
                ),
                activity_summary="Active"
            )
            forks_data.append(fork_data)
        
        display_service.github_client.get_recent_commits.return_value = sample_recent_commits
        
        # Test concurrent fetching with rate limiting
        start_time = asyncio.get_event_loop().time()
        result = await display_service._fetch_commits_concurrently(forks_data, show_commits=2, force_all_commits=True)
        end_time = asyncio.get_event_loop().time()
        
        # Verify all forks were processed
        assert len(result) == 10
        
        # Verify rate limiting caused some delay (at least 0.1s per request due to sleep)
        # With semaphore of 5, should take at least 0.2s (2 batches * 0.1s)
        assert end_time - start_time >= 0.1
        
        # Verify all API calls were made
        assert display_service.github_client.get_recent_commits.call_count == 10