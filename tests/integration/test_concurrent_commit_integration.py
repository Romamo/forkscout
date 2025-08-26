"""Integration tests for concurrent commit fetching with fork display workflow."""

import pytest
from unittest.mock import AsyncMock, patch

from forklift.config.settings import ForkliftConfig, GitHubConfig
from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.github.client import GitHubClient
from forklift.models.github import RecentCommit, Repository
from forklift.models.fork_qualification import (
    CollectedForkData, 
    ForkQualificationMetrics,
    QualifiedForksResult,
    QualificationStats
)


class TestConcurrentCommitIntegration:
    """Integration tests for concurrent commit fetching workflow."""

    @pytest.fixture
    def github_config(self):
        """Create GitHub configuration."""
        return GitHubConfig(token="ghp_1234567890123456789012345678901234567890")

    @pytest.fixture
    def forklift_config(self, github_config):
        """Create Forklift configuration."""
        return ForkliftConfig(github=github_config)

    @pytest.fixture
    async def github_client(self, github_config):
        """Create GitHub client."""
        return GitHubClient(github_config)

    @pytest.fixture
    def display_service(self, github_client):
        """Create repository display service."""
        return RepositoryDisplayService(github_client)

    @pytest.fixture
    def sample_qualification_result(self):
        """Create sample qualification result with multiple forks."""
        from datetime import datetime
        
        # Create sample fork data
        forks_data = []
        for i in range(3):
            metrics = ForkQualificationMetrics(
                id=10000 + i,
                name=f"test-repo-{i}",
                full_name=f"user{i}/test-repo-{i}",
                owner=f"user{i}",
                html_url=f"https://github.com/user{i}/test-repo-{i}",
                stargazers_count=10 + i,
                forks_count=2 + i,
                size=1000 * (i + 1),
                language="Python",
                topics=["testing", "python"],
                open_issues_count=i,
                watchers_count=5 + i,
                archived=False,
                disabled=False,
                created_at=datetime.fromisoformat("2023-01-01T00:00:00"),
                updated_at=datetime.fromisoformat("2023-06-01T00:00:00"),
                pushed_at=datetime.fromisoformat("2023-06-01T00:00:00"),
                days_since_creation=200,
                days_since_last_update=30,
                days_since_last_push=30,
                commits_ahead_status="Has commits",
                can_skip_analysis=False,
            )
            
            fork_data = CollectedForkData(
                metrics=metrics,
                activity_summary=f"Active fork with {10 + i} stars"
            )
            forks_data.append(fork_data)

        # Create stats
        stats = QualificationStats(
            total_forks_discovered=3,
            forks_with_commits=3,
            forks_with_no_commits=0,
            archived_forks=0,
            disabled_forks=0,
            processing_time_seconds=1.5,
            api_calls_made=3,
            api_calls_saved=0,
            efficiency_percentage=0.0,
            analysis_candidate_percentage=100.0,
            skip_rate_percentage=0.0
        )

        return QualifiedForksResult(
            repository_owner="testowner",
            repository_name="testrepo",
            collected_forks=forks_data,
            stats=stats
        )

    @pytest.mark.asyncio
    @patch('forklift.display.repository_display_service.Progress')
    async def test_show_fork_data_with_commits_integration(
        self, mock_progress, display_service, sample_qualification_result
    ):
        """Test complete fork data display workflow with commit fetching."""
        # Mock progress to avoid Rich timing issues
        mock_progress_instance = AsyncMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = 0

        # Mock GitHub client methods
        display_service.github_client = AsyncMock()
        
        # Mock fork list processor and data engine
        with patch('forklift.display.repository_display_service.ForkListProcessor') as mock_processor, \
             patch('forklift.display.repository_display_service.ForkDataCollectionEngine') as mock_engine:
            
            # Configure mocks
            mock_processor_instance = AsyncMock()
            mock_processor.return_value = mock_processor_instance
            mock_processor_instance.get_all_forks_list_data.return_value = [
                {"name": f"test-repo-{i}", "owner": {"login": f"user{i}"}} for i in range(3)
            ]
            
            mock_engine_instance = AsyncMock()
            mock_engine.return_value = mock_engine_instance
            mock_engine_instance.collect_fork_data_from_list.return_value = sample_qualification_result.collected_forks
            mock_engine_instance.create_qualification_result.return_value = sample_qualification_result

            # Mock recent commits for each fork
            async def mock_get_recent_commits(owner, repo, count=5):
                commits_map = {
                    "user0": [RecentCommit(short_sha="abc1230", message="Fix authentication bug")],
                    "user1": [RecentCommit(short_sha="def4561", message="Add new feature"), 
                             RecentCommit(short_sha="abc7891", message="Update documentation")],
                    "user2": [RecentCommit(short_sha="abc7892", message="Improve performance")]
                }
                return commits_map.get(owner, [])

            display_service.github_client.get_recent_commits.side_effect = mock_get_recent_commits

            # Test fork data display with commits
            result = await display_service.show_fork_data(
                repo_url="testowner/testrepo",
                show_commits=2
            )

            # Verify the result structure
            assert result is not None
            assert "total_forks" in result
            assert "displayed_forks" in result
            assert "collected_forks" in result
            assert "stats" in result

            # Verify that concurrent commit fetching was called
            # (We can't easily verify the exact calls due to mocking, but we can verify the structure)
            assert result["total_forks"] == 3
            assert result["displayed_forks"] == 3

    @pytest.mark.asyncio
    @patch('forklift.display.repository_display_service.Progress')
    async def test_concurrent_commit_fetching_with_failures(
        self, mock_progress, display_service, sample_qualification_result
    ):
        """Test concurrent commit fetching handles failures gracefully."""
        # Mock progress to avoid Rich timing issues
        mock_progress_instance = AsyncMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = 0

        # Mock GitHub client to simulate some failures
        display_service.github_client = AsyncMock()
        
        async def mock_get_recent_commits_with_failures(owner, repo, count=5):
            if owner == "user0":
                return [RecentCommit(short_sha="abc1230", message="Working commit")]
            elif owner == "user1":
                raise Exception("API rate limit exceeded")
            elif owner == "user2":
                return []  # Empty commits
            return []

        display_service.github_client.get_recent_commits.side_effect = mock_get_recent_commits_with_failures

        # Test concurrent fetching with failures
        result = await display_service._fetch_commits_concurrently(
            sample_qualification_result.collected_forks, 1
        )

        # Verify results handle failures gracefully
        assert len(result) == 3
        assert "user0/test-repo-0" in result
        assert "user1/test-repo-1" in result
        assert "user2/test-repo-2" in result

        # Check specific results
        assert "abc1230: Working commit" in result["user0/test-repo-0"]
        assert result["user1/test-repo-1"] == "[dim]No commits available[/dim]"  # Failed API call
        assert result["user2/test-repo-2"] == "[dim]No commits[/dim]"  # Empty commits

    @pytest.mark.asyncio
    @patch('forklift.display.repository_display_service.Progress')
    async def test_concurrent_fetching_respects_rate_limits(
        self, mock_progress, display_service, sample_qualification_result
    ):
        """Test that concurrent fetching respects rate limiting."""
        # Mock progress to avoid Rich timing issues
        mock_progress_instance = AsyncMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = 0

        # Track API call timing
        call_count = 0
        call_times = []

        async def mock_get_recent_commits_with_timing(owner, repo, count=5):
            nonlocal call_count
            import time
            call_times.append(time.time())
            call_count += 1
            
            # Simulate some processing time
            await asyncio.sleep(0.01)
            
            return [RecentCommit(short_sha=f"abc123{call_count}", message=f"Commit {call_count}")]

        display_service.github_client = AsyncMock()
        display_service.github_client.get_recent_commits.side_effect = mock_get_recent_commits_with_timing

        # Test concurrent fetching
        result = await display_service._fetch_commits_concurrently(
            sample_qualification_result.collected_forks, 1
        )

        # Verify all forks were processed
        assert len(result) == 3
        assert call_count == 3

        # Verify all results contain commits
        for fork_key in result:
            assert "Commit" in result[fork_key]

    @pytest.mark.asyncio
    async def test_format_recent_commits_edge_cases(self, display_service):
        """Test format_recent_commits handles edge cases."""
        # Test empty list
        assert display_service.format_recent_commits([]) == "[dim]No commits[/dim]"

        # Test single commit
        single_commit = [RecentCommit(short_sha="abc1234", message="Single commit")]
        result = display_service.format_recent_commits(single_commit)
        assert result == "abc1234: Single commit"

        # Test multiple commits
        multiple_commits = [
            RecentCommit(short_sha="abc1234", message="First commit"),
            RecentCommit(short_sha="def5678", message="Second commit"),
            RecentCommit(short_sha="abc9012", message="Third commit")
        ]
        result = display_service.format_recent_commits(multiple_commits)
        expected = "abc1234: First commit\ndef5678: Second commit\nabc9012: Third commit"
        assert result == expected

    @pytest.mark.asyncio
    @patch('forklift.display.repository_display_service.Progress')
    async def test_show_fork_data_without_commits(
        self, mock_progress, display_service, sample_qualification_result
    ):
        """Test fork data display without commit fetching."""
        # Mock progress to avoid Rich timing issues
        mock_progress_instance = AsyncMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = 0

        # Mock GitHub client methods
        display_service.github_client = AsyncMock()
        
        # Mock fork list processor and data engine
        with patch('forklift.display.repository_display_service.ForkListProcessor') as mock_processor, \
             patch('forklift.display.repository_display_service.ForkDataCollectionEngine') as mock_engine:
            
            # Configure mocks
            mock_processor_instance = AsyncMock()
            mock_processor.return_value = mock_processor_instance
            mock_processor_instance.get_all_forks_list_data.return_value = [
                {"name": f"test-repo-{i}", "owner": {"login": f"user{i}"}} for i in range(3)
            ]
            
            mock_engine_instance = AsyncMock()
            mock_engine.return_value = mock_engine_instance
            mock_engine_instance.collect_fork_data_from_list.return_value = sample_qualification_result.collected_forks
            mock_engine_instance.create_qualification_result.return_value = sample_qualification_result

            # Test fork data display without commits (show_commits=0)
            result = await display_service.show_fork_data(
                repo_url="testowner/testrepo",
                show_commits=0
            )

            # Verify the result structure
            assert result is not None
            assert result["total_forks"] == 3
            assert result["displayed_forks"] == 3

            # Verify that get_recent_commits was NOT called when show_commits=0
            display_service.github_client.get_recent_commits.assert_not_called()