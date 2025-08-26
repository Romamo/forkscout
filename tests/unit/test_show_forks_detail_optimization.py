"""Unit tests for show-forks --detail optimization to skip API calls for forks with no commits ahead."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.github.client import GitHubClient
from forklift.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
)


class TestShowForksDetailOptimization:
    """Test cases for optimized show-forks --detail command."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        client = AsyncMock(spec=GitHubClient)
        return client

    @pytest.fixture
    def repository_display_service(self, mock_github_client):
        """Create repository display service with mock client."""
        return RepositoryDisplayService(mock_github_client)

    @pytest.fixture
    def base_time(self):
        """Base time for creating test timestamps."""
        return datetime(2024, 1, 15, 12, 0, 0)

    def create_fork_data(
        self,
        owner: str,
        name: str,
        created_at: datetime,
        pushed_at: datetime,
        stars: int = 0,
        archived: bool = False,
        disabled: bool = False
    ) -> CollectedForkData:
        """Create test fork data with specified timestamps."""
        metrics = ForkQualificationMetrics(
            id=12345,
            name=name,
            full_name=f"{owner}/{name}",
            owner=owner,
            html_url=f"https://github.com/{owner}/{name}",
            stargazers_count=stars,
            forks_count=0,
            watchers_count=0,
            size=100,
            language="Python",
            topics=[],
            open_issues_count=0,
            created_at=created_at,
            updated_at=created_at,
            pushed_at=pushed_at,
            archived=archived,
            disabled=disabled,
            fork=True,
            license_key=None,
            license_name=None,
            description="Test fork",
            homepage=None,
            default_branch="main"
        )

        return CollectedForkData(
            metrics=metrics,
            activity_summary="Test activity",
            exact_commits_ahead=None  # Will be set during processing
        )

    @pytest.mark.asyncio
    async def test_skip_forks_with_no_commits_ahead(
        self, repository_display_service, mock_github_client, base_time
    ):
        """Test that forks with no commits ahead are skipped from API calls."""
        # Create test forks - some with commits ahead, some without
        fork_with_commits = self.create_fork_data(
            "user1", "repo1",
            created_at=base_time,
            pushed_at=base_time + timedelta(hours=1),  # pushed_at > created_at
            stars=5
        )

        fork_no_commits_1 = self.create_fork_data(
            "user2", "repo2",
            created_at=base_time,
            pushed_at=base_time,  # pushed_at == created_at
            stars=2
        )

        fork_no_commits_2 = self.create_fork_data(
            "user3", "repo3",
            created_at=base_time + timedelta(hours=1),
            pushed_at=base_time,  # pushed_at < created_at
            stars=1
        )

        # Mock the fork list processor and data engine
        mock_forks_list_data = [
            {"full_name": "user1/repo1"},
            {"full_name": "user2/repo2"},
            {"full_name": "user3/repo3"}
        ]

        collected_forks = [fork_with_commits, fork_no_commits_1, fork_no_commits_2]

        with patch("forklift.github.fork_list_processor.ForkListProcessor") as mock_processor_class, \
             patch("forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine") as mock_engine_class:

            # Setup mocks
            mock_processor = AsyncMock()
            mock_processor.get_all_forks_list_data.return_value = mock_forks_list_data
            mock_processor_class.return_value = mock_processor

            mock_engine = MagicMock()
            mock_engine.collect_fork_data_from_list.return_value = collected_forks
            mock_engine_class.return_value = mock_engine

            # Mock the compare API call (should only be called once for fork_with_commits)
            mock_github_client.compare_repositories.return_value = {"ahead_by": 3}

            # Mock console to capture output
            repository_display_service.console = MagicMock()

            # Call the method
            result = await repository_display_service.show_fork_data_detailed(
                "owner/repo", max_forks=None, disable_cache=False
            )

            # Verify API calls were optimized
            assert result["api_calls_made"] == 1  # Only one API call for fork_with_commits
            assert result["api_calls_saved"] == 2  # Two forks skipped
            assert result["forks_skipped"] == 2
            assert result["forks_analyzed"] == 1

            # Verify compare API was only called once
            assert mock_github_client.compare_repositories.call_count == 1
            mock_github_client.compare_repositories.assert_called_with(
                "owner", "repo", "user1", "repo1"
            )

            # Verify fork data was set correctly
            collected_forks_result = result["collected_forks"]

            # Find each fork in results
            fork_with_commits_result = next(f for f in collected_forks_result if f.metrics.owner == "user1")
            fork_no_commits_1_result = next(f for f in collected_forks_result if f.metrics.owner == "user2")
            fork_no_commits_2_result = next(f for f in collected_forks_result if f.metrics.owner == "user3")

            # Verify exact_commits_ahead values
            assert fork_with_commits_result.exact_commits_ahead == 3  # From API call
            assert fork_no_commits_1_result.exact_commits_ahead == 0  # Skipped, set to 0
            assert fork_no_commits_2_result.exact_commits_ahead == 0  # Skipped, set to 0

    @pytest.mark.asyncio
    async def test_skip_archived_and_disabled_forks(
        self, repository_display_service, mock_github_client, base_time
    ):
        """Test that archived and disabled forks are filtered out entirely."""
        # Create test forks including archived and disabled ones
        active_fork = self.create_fork_data(
            "user1", "repo1",
            created_at=base_time,
            pushed_at=base_time + timedelta(hours=1),
            stars=5
        )

        archived_fork = self.create_fork_data(
            "user2", "repo2",
            created_at=base_time,
            pushed_at=base_time + timedelta(hours=1),
            stars=3,
            archived=True
        )

        disabled_fork = self.create_fork_data(
            "user3", "repo3",
            created_at=base_time,
            pushed_at=base_time + timedelta(hours=1),
            stars=2,
            disabled=True
        )

        mock_forks_list_data = [
            {"full_name": "user1/repo1"},
            {"full_name": "user2/repo2"},
            {"full_name": "user3/repo3"}
        ]

        collected_forks = [active_fork, archived_fork, disabled_fork]

        with patch("forklift.github.fork_list_processor.ForkListProcessor") as mock_processor_class, \
             patch("forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine") as mock_engine_class:

            # Setup mocks
            mock_processor = AsyncMock()
            mock_processor.get_all_forks_list_data.return_value = mock_forks_list_data
            mock_processor_class.return_value = mock_processor

            mock_engine = MagicMock()
            mock_engine.collect_fork_data_from_list.return_value = collected_forks
            mock_engine_class.return_value = mock_engine

            # Mock the compare API call
            mock_github_client.compare_repositories.return_value = {"ahead_by": 2}

            # Mock console
            repository_display_service.console = MagicMock()

            # Call the method
            result = await repository_display_service.show_fork_data_detailed(
                "owner/repo", max_forks=None, disable_cache=False
            )

            # Verify only active fork was processed
            assert result["api_calls_made"] == 1  # Only one API call for active fork
            assert result["displayed_forks"] == 1  # Only active fork displayed

            # Verify compare API was only called for active fork
            assert mock_github_client.compare_repositories.call_count == 1
            mock_github_client.compare_repositories.assert_called_with(
                "owner", "repo", "user1", "repo1"
            )

    @pytest.mark.asyncio
    async def test_all_forks_skipped_scenario(
        self, repository_display_service, mock_github_client, base_time
    ):
        """Test scenario where all forks can be skipped (no API calls needed)."""
        # Create forks that all have no commits ahead
        fork_no_commits_1 = self.create_fork_data(
            "user1", "repo1",
            created_at=base_time,
            pushed_at=base_time,  # Same time = no commits
            stars=3
        )

        fork_no_commits_2 = self.create_fork_data(
            "user2", "repo2",
            created_at=base_time + timedelta(hours=1),
            pushed_at=base_time,  # created_at > pushed_at = no commits
            stars=1
        )

        mock_forks_list_data = [
            {"full_name": "user1/repo1"},
            {"full_name": "user2/repo2"}
        ]

        collected_forks = [fork_no_commits_1, fork_no_commits_2]

        with patch("forklift.github.fork_list_processor.ForkListProcessor") as mock_processor_class, \
             patch("forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine") as mock_engine_class:

            # Setup mocks
            mock_processor = AsyncMock()
            mock_processor.get_all_forks_list_data.return_value = mock_forks_list_data
            mock_processor_class.return_value = mock_processor

            mock_engine = MagicMock()
            mock_engine.collect_fork_data_from_list.return_value = collected_forks
            mock_engine_class.return_value = mock_engine

            # Mock console
            repository_display_service.console = MagicMock()

            # Call the method
            result = await repository_display_service.show_fork_data_detailed(
                "owner/repo", max_forks=None, disable_cache=False
            )

            # Verify no API calls were made
            assert result["api_calls_made"] == 0
            assert result["api_calls_saved"] == 2
            assert result["forks_skipped"] == 2
            assert result["forks_analyzed"] == 0

            # Verify compare API was never called
            assert mock_github_client.compare_repositories.call_count == 0

            # Verify console messages about no API calls needed
            console_calls = repository_display_service.console.print.call_args_list
            no_api_calls_message = any(
                "No forks require API calls" in str(call) for call in console_calls
            )
            assert no_api_calls_message

    @pytest.mark.asyncio
    async def test_api_call_failure_handling(
        self, repository_display_service, mock_github_client, base_time
    ):
        """Test handling of API call failures during commit count fetching."""
        # Create fork that needs API call
        fork_with_commits = self.create_fork_data(
            "user1", "repo1",
            created_at=base_time,
            pushed_at=base_time + timedelta(hours=1),
            stars=5
        )

        mock_forks_list_data = [{"full_name": "user1/repo1"}]
        collected_forks = [fork_with_commits]

        with patch("forklift.github.fork_list_processor.ForkListProcessor") as mock_processor_class, \
             patch("forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine") as mock_engine_class:

            # Setup mocks
            mock_processor = AsyncMock()
            mock_processor.get_all_forks_list_data.return_value = mock_forks_list_data
            mock_processor_class.return_value = mock_processor

            mock_engine = MagicMock()
            mock_engine.collect_fork_data_from_list.return_value = collected_forks
            mock_engine_class.return_value = mock_engine

            # Mock API call to fail
            mock_github_client.compare_repositories.side_effect = Exception("API Error")

            # Mock console
            repository_display_service.console = MagicMock()

            # Call the method
            result = await repository_display_service.show_fork_data_detailed(
                "owner/repo", max_forks=None, disable_cache=False
            )

            # Verify API call was attempted but failed gracefully
            assert result["api_calls_made"] == 0  # No successful API calls
            assert result["displayed_forks"] == 1  # Fork still displayed

            # Verify fork has "Unknown" commits ahead due to API failure
            fork_result = result["collected_forks"][0]
            assert fork_result.exact_commits_ahead == "Unknown"

    @pytest.mark.asyncio
    async def test_logging_api_savings(
        self, repository_display_service, mock_github_client, base_time, caplog
    ):
        """Test that API savings are properly logged."""
        import logging

        # Create mix of forks
        fork_with_commits = self.create_fork_data(
            "user1", "repo1",
            created_at=base_time,
            pushed_at=base_time + timedelta(hours=1),
            stars=5
        )

        fork_no_commits = self.create_fork_data(
            "user2", "repo2",
            created_at=base_time,
            pushed_at=base_time,
            stars=2
        )

        mock_forks_list_data = [
            {"full_name": "user1/repo1"},
            {"full_name": "user2/repo2"}
        ]

        collected_forks = [fork_with_commits, fork_no_commits]

        with patch("forklift.github.fork_list_processor.ForkListProcessor") as mock_processor_class, \
             patch("forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine") as mock_engine_class:

            # Setup mocks
            mock_processor = AsyncMock()
            mock_processor.get_all_forks_list_data.return_value = mock_forks_list_data
            mock_processor_class.return_value = mock_processor

            mock_engine = MagicMock()
            mock_engine.collect_fork_data_from_list.return_value = collected_forks
            mock_engine_class.return_value = mock_engine

            # Mock API call
            mock_github_client.compare_repositories.return_value = {"ahead_by": 2}

            # Mock console
            repository_display_service.console = MagicMock()

            # Set logging level to capture info messages
            with caplog.at_level(logging.INFO):
                # Call the method
                await repository_display_service.show_fork_data_detailed(
                    "owner/repo", max_forks=None, disable_cache=False
                )

            # Verify logging message about API savings
            log_messages = [record.message for record in caplog.records]
            api_savings_logged = any(
                "saved 1 API calls" in message for message in log_messages
            )
            assert api_savings_logged

    def test_can_skip_analysis_property(self, base_time):
        """Test the can_skip_analysis property logic."""
        # Fork with no commits (created_at == pushed_at)
        metrics_no_commits_equal = ForkQualificationMetrics(
            id=1,
            name="test",
            full_name="user/test",
            owner="user",
            html_url="https://github.com/user/test",
            created_at=base_time,
            pushed_at=base_time,  # Same time
            updated_at=base_time
        )
        assert metrics_no_commits_equal.can_skip_analysis is True
        assert metrics_no_commits_equal.commits_ahead_status == "No commits ahead"

        # Fork with no commits (created_at > pushed_at)
        metrics_no_commits_greater = ForkQualificationMetrics(
            id=2,
            name="test2",
            full_name="user/test2",
            owner="user",
            html_url="https://github.com/user/test2",
            created_at=base_time + timedelta(hours=1),
            pushed_at=base_time,  # created_at > pushed_at
            updated_at=base_time
        )
        assert metrics_no_commits_greater.can_skip_analysis is True
        assert metrics_no_commits_greater.commits_ahead_status == "No commits ahead"

        # Fork with commits (pushed_at > created_at)
        metrics_has_commits = ForkQualificationMetrics(
            id=3,
            name="test3",
            full_name="user/test3",
            owner="user",
            html_url="https://github.com/user/test3",
            created_at=base_time,
            pushed_at=base_time + timedelta(hours=1),  # pushed_at > created_at
            updated_at=base_time
        )
        assert metrics_has_commits.can_skip_analysis is False
        assert metrics_has_commits.commits_ahead_status == "Has commits"
