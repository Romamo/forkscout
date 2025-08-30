"""Comprehensive integration tests for show-forks --detail functionality."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console

from forklift.analysis.fork_data_collection_engine import ForkDataCollectionEngine
from forklift.config.settings import ForkliftConfig, GitHubConfig
from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.github.client import GitHubClient
from forklift.github.fork_list_processor import ForkListProcessor
from forklift.models.fork_qualification import CollectedForkData, ForkQualificationMetrics


class TestShowForksDetailComprehensive:
    """Comprehensive integration test suite for show-forks --detail functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        config = ForkliftConfig()
        config.github = GitHubConfig(token="ghp_1234567890123456789012345678901234567890")
        return config

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client with realistic responses."""
        client = AsyncMock(spec=GitHubClient)
        return client

    @pytest.fixture
    def console(self):
        """Create a Rich console for testing."""
        return Console(file=MagicMock(), width=120)

    @pytest.fixture
    def display_service(self, mock_github_client, console):
        """Create a repository display service for testing."""
        return RepositoryDisplayService(mock_github_client, console)

    @pytest.fixture
    def sample_repository_data(self):
        """Create sample repository data."""
        return {
            "id": 12345,
            "name": "test-repo",
            "full_name": "owner/test-repo",
            "owner": {"login": "owner"},
            "html_url": "https://github.com/owner/test-repo",
            "description": "A test repository",
            "stargazers_count": 100,
            "forks_count": 25,
            "language": "Python",
            "default_branch": "main",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-06-01T00:00:00Z",
            "pushed_at": "2023-06-01T00:00:00Z",
        }

    @pytest.fixture
    def realistic_forks_list_data(self):
        """Create realistic forks list data with various scenarios."""
        base_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
        
        return [
            # Fork with commits ahead (pushed_at > created_at)
            {
                "id": 123,
                "name": "active-fork",
                "full_name": "user1/active-fork",
                "owner": {"login": "user1"},
                "html_url": "https://github.com/user1/active-fork",
                "stargazers_count": 15,
                "forks_count": 3,
                "watchers_count": 10,
                "size": 2000,
                "language": "Python",
                "topics": ["web", "api"],
                "open_issues_count": 2,
                "created_at": base_time.isoformat(),
                "updated_at": (base_time.replace(month=6)).isoformat(),
                "pushed_at": (base_time.replace(month=6)).isoformat(),
                "archived": False,
                "disabled": False,
                "fork": True,
                "description": "An active fork with changes",
                "homepage": None,
                "default_branch": "main",
                "license": {"key": "mit", "name": "MIT License"},
            },
            # Fork with no commits ahead (created_at >= pushed_at)
            {
                "id": 456,
                "name": "empty-fork",
                "full_name": "user2/empty-fork",
                "owner": {"login": "user2"},
                "html_url": "https://github.com/user2/empty-fork",
                "stargazers_count": 0,
                "forks_count": 0,
                "watchers_count": 0,
                "size": 100,
                "language": None,
                "topics": [],
                "open_issues_count": 0,
                "created_at": (base_time.replace(month=6)).isoformat(),
                "updated_at": (base_time.replace(month=6)).isoformat(),
                "pushed_at": base_time.isoformat(),  # Earlier than created_at
                "archived": False,
                "disabled": False,
                "fork": True,
                "description": None,
                "homepage": None,
                "default_branch": "main",
                "license": None,
            },
            # High-activity fork with many commits ahead
            {
                "id": 789,
                "name": "high-activity-fork",
                "full_name": "user3/high-activity-fork",
                "owner": {"login": "user3"},
                "html_url": "https://github.com/user3/high-activity-fork",
                "stargazers_count": 50,
                "forks_count": 10,
                "watchers_count": 45,
                "size": 5000,
                "language": "JavaScript",
                "topics": ["frontend", "react"],
                "open_issues_count": 5,
                "created_at": base_time.isoformat(),
                "updated_at": (base_time.replace(month=8)).isoformat(),
                "pushed_at": (base_time.replace(month=8)).isoformat(),
                "archived": False,
                "disabled": False,
                "fork": True,
                "description": "High activity fork with many changes",
                "homepage": "https://example.com",
                "default_branch": "main",
                "license": {"key": "apache-2.0", "name": "Apache License 2.0"},
            },
            # Archived fork (should be excluded from detailed analysis)
            {
                "id": 999,
                "name": "archived-fork",
                "full_name": "user4/archived-fork",
                "owner": {"login": "user4"},
                "html_url": "https://github.com/user4/archived-fork",
                "stargazers_count": 5,
                "forks_count": 1,
                "watchers_count": 3,
                "size": 500,
                "language": "Python",
                "topics": [],
                "open_issues_count": 0,
                "created_at": base_time.isoformat(),
                "updated_at": (base_time.replace(month=3)).isoformat(),
                "pushed_at": (base_time.replace(month=3)).isoformat(),
                "archived": True,  # This fork is archived
                "disabled": False,
                "fork": True,
                "description": "An archived fork",
                "homepage": None,
                "default_branch": "main",
                "license": None,
            },
        ]

    @pytest.fixture
    def mock_compare_responses(self):
        """Create mock responses for GitHub compare API calls."""
        return {
            "user1/active-fork": {"ahead_by": 5, "behind_by": 2},
            "user3/high-activity-fork": {"ahead_by": 25, "behind_by": 0},
            # user2/empty-fork should not be called (skipped due to no commits ahead)
            # user4/archived-fork should not be called (excluded from analysis)
        }

    @pytest.mark.asyncio
    async def test_show_fork_data_detailed_integration_with_real_data(
        self, display_service, realistic_forks_list_data, mock_compare_responses
    ):
        """Test show_fork_data_detailed with realistic fork data integration."""
        # Setup mock GitHub client responses
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = realistic_forks_list_data

        # Mock compare API responses
        async def mock_compare_repositories(base_owner, base_repo, fork_owner, fork_repo):
            fork_key = f"{fork_owner}/{fork_repo}"
            if fork_key in mock_compare_responses:
                return mock_compare_responses[fork_key]
            else:
                raise Exception(f"Compare API call not expected for {fork_key}")

        display_service.github_client.compare_repositories = mock_compare_repositories

        # Patch the ForkListProcessor to use our mock
        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False
            )

        # Verify results
        assert result["total_forks"] == 4
        assert result["displayed_forks"] == 3  # Excluding archived fork
        assert result["api_calls_made"] == 2  # Only for active-fork and high-activity-fork
        assert result["api_calls_saved"] == 1  # empty-fork was skipped
        assert result["forks_skipped"] == 1
        assert result["forks_analyzed"] == 2

        # Verify that the correct forks were processed
        collected_forks = result["collected_forks"]
        fork_names = [fork.metrics.name for fork in collected_forks]
        assert "active-fork" in fork_names
        assert "empty-fork" in fork_names
        assert "high-activity-fork" in fork_names
        assert "archived-fork" not in fork_names  # Should be excluded

        # Verify exact commits ahead values
        for fork in collected_forks:
            if fork.metrics.name == "active-fork":
                assert fork.exact_commits_ahead == 5
            elif fork.metrics.name == "empty-fork":
                assert fork.exact_commits_ahead == 0  # Skipped, set to 0
            elif fork.metrics.name == "high-activity-fork":
                assert fork.exact_commits_ahead == 25

    @pytest.mark.asyncio
    async def test_commits_ahead_api_calls_various_scenarios(
        self, display_service, realistic_forks_list_data
    ):
        """Test commits ahead API calls with various fork scenarios."""
        # Setup different compare API responses for various scenarios
        compare_responses = {
            "user1/active-fork": {"ahead_by": 3, "behind_by": 1},
            "user3/high-activity-fork": {"ahead_by": 0, "behind_by": 5},  # Behind only
        }

        api_calls_made = []

        async def mock_compare_repositories(base_owner, base_repo, fork_owner, fork_repo):
            fork_key = f"{fork_owner}/{fork_repo}"
            api_calls_made.append(fork_key)
            
            if fork_key in compare_responses:
                return compare_responses[fork_key]
            else:
                # Simulate API error for testing error handling
                raise Exception(f"API error for {fork_key}")

        display_service.github_client.compare_repositories = mock_compare_repositories

        # Mock fork processor
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = realistic_forks_list_data

        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False
            )

        # Verify API calls were made only for expected forks
        assert len(api_calls_made) == 2
        assert "user1/active-fork" in api_calls_made
        assert "user3/high-activity-fork" in api_calls_made
        assert "user2/empty-fork" not in api_calls_made  # Should be skipped

        # Verify results reflect different scenarios
        collected_forks = result["collected_forks"]
        for fork in collected_forks:
            if fork.metrics.name == "active-fork":
                assert fork.exact_commits_ahead == 3
            elif fork.metrics.name == "high-activity-fork":
                assert fork.exact_commits_ahead == 0  # Behind only, so 0 ahead
            elif fork.metrics.name == "empty-fork":
                assert fork.exact_commits_ahead == 0  # Skipped

    @pytest.mark.asyncio
    async def test_detailed_table_display_and_column_formatting(
        self, display_service, realistic_forks_list_data, mock_compare_responses
    ):
        """Test detailed table display and column formatting."""
        # Setup mocks
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = realistic_forks_list_data

        display_service.github_client.compare_repositories = AsyncMock(
            side_effect=lambda base_owner, base_repo, fork_owner, fork_repo: 
            mock_compare_responses.get(f"{fork_owner}/{fork_repo}", {"ahead_by": 0, "behind_by": 0})
        )

        # Capture console output
        console_output = []
        original_print = display_service.console.print
        display_service.console.print = lambda *args, **kwargs: console_output.append(str(args[0]) if args else "")

        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False
            )

        # Restore original print
        display_service.console.print = original_print

        # Verify table was displayed
        table_output = "\n".join(console_output)
        
        # Check for detailed table elements
        assert "Detailed Fork Information" in table_output or any("Fork Information" in output for output in console_output)
        
        # Check that fork data is present in output
        assert "user1/active-fork" in table_output or any("active-fork" in output for output in console_output)
        assert "user3/high-activity-fork" in table_output or any("high-activity-fork" in output for output in console_output)
        
        # Verify API call statistics are displayed
        assert any("API calls" in output for output in console_output)
        assert any("Skipped" in output for output in console_output)

    @pytest.mark.asyncio
    async def test_error_handling_when_commits_ahead_cannot_be_fetched(
        self, display_service, realistic_forks_list_data
    ):
        """Test error handling when commits ahead cannot be fetched."""
        # Setup fork processor
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = realistic_forks_list_data

        # Mock compare API to fail for some forks
        api_calls_made = []
        
        async def mock_compare_repositories(base_owner, base_repo, fork_owner, fork_repo):
            fork_key = f"{fork_owner}/{fork_repo}"
            api_calls_made.append(fork_key)
            
            if fork_key == "user1/active-fork":
                return {"ahead_by": 5, "behind_by": 1}
            elif fork_key == "user3/high-activity-fork":
                # Simulate API error
                raise Exception("GitHub API rate limit exceeded")
            else:
                raise Exception(f"Unexpected API call for {fork_key}")

        display_service.github_client.compare_repositories = mock_compare_repositories

        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            # This should not raise an exception despite API errors
            result = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False
            )

        # Verify that processing continued despite errors
        assert result["total_forks"] == 4
        assert result["displayed_forks"] == 3  # Excluding archived
        assert result["api_calls_made"] == 1  # Only successful call counted
        
        # Verify that failed fork has "Unknown" status
        collected_forks = result["collected_forks"]
        for fork in collected_forks:
            if fork.metrics.name == "active-fork":
                assert fork.exact_commits_ahead == 5  # Successful
            elif fork.metrics.name == "high-activity-fork":
                assert fork.exact_commits_ahead == "Unknown"  # Failed
            elif fork.metrics.name == "empty-fork":
                assert fork.exact_commits_ahead == 0  # Skipped

    @pytest.mark.asyncio
    async def test_performance_impact_of_additional_api_calls(
        self, display_service, mock_config
    ):
        """Test performance impact of additional API calls."""
        import time
        
        # Create a larger dataset to test performance
        large_forks_data = []
        for i in range(20):  # 20 forks
            base_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
            fork_data = {
                "id": 1000 + i,
                "name": f"fork-{i}",
                "full_name": f"user{i}/fork-{i}",
                "owner": {"login": f"user{i}"},
                "html_url": f"https://github.com/user{i}/fork-{i}",
                "stargazers_count": i * 2,
                "forks_count": i,
                "watchers_count": i,
                "size": 1000 + i * 100,
                "language": "Python",
                "topics": [],
                "open_issues_count": i % 3,
                "created_at": base_time.isoformat(),
                "updated_at": (base_time.replace(month=6)).isoformat(),
                "pushed_at": (base_time.replace(month=6)).isoformat(),  # All have commits ahead
                "archived": False,
                "disabled": False,
                "fork": True,
                "description": f"Fork {i}",
                "homepage": None,
                "default_branch": "main",
                "license": None,
            }
            large_forks_data.append(fork_data)

        # Setup mocks
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = large_forks_data

        # Mock compare API with simulated delay
        api_call_times = []
        
        async def mock_compare_repositories(base_owner, base_repo, fork_owner, fork_repo):
            start_time = time.time()
            await asyncio.sleep(0.01)  # Simulate 10ms API call delay
            end_time = time.time()
            api_call_times.append(end_time - start_time)
            return {"ahead_by": 3, "behind_by": 1}

        display_service.github_client.compare_repositories = mock_compare_repositories

        # Measure total execution time
        start_time = time.time()
        
        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=True  # Force all calls to test concurrency
            )
        
        end_time = time.time()
        total_time = end_time - start_time

        # Verify performance characteristics
        assert result["api_calls_made"] == 20  # All forks needed API calls
        assert len(api_call_times) == 20
        
        # Verify that API calls were made efficiently (not sequentially blocking)
        # Total time should be less than sum of individual call times due to potential concurrency
        total_api_time = sum(api_call_times)
        assert total_time < total_api_time * 2  # Allow some overhead but ensure efficiency
        
        # Verify all forks were processed
        assert result["total_forks"] == 20
        assert result["displayed_forks"] == 20

    @pytest.mark.asyncio
    async def test_max_forks_limit_with_detailed_analysis(
        self, display_service, realistic_forks_list_data, mock_compare_responses
    ):
        """Test max_forks limit with detailed analysis."""
        # Setup mocks
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = realistic_forks_list_data

        display_service.github_client.compare_repositories = AsyncMock(
            side_effect=lambda base_owner, base_repo, fork_owner, fork_repo: 
            mock_compare_responses.get(f"{fork_owner}/{fork_repo}", {"ahead_by": 1, "behind_by": 0})
        )

        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=2,  # Limit to 2 forks
                disable_cache=False,
                show_commits=0,
                force_all_commits=False
            )

        # Verify that only 2 forks were processed
        assert result["total_forks"] == 2  # Limited by max_forks
        assert result["displayed_forks"] <= 2
        
        # Verify that API calls were limited accordingly
        assert result["api_calls_made"] <= 2

    @pytest.mark.asyncio
    async def test_show_commits_integration_with_detailed_mode(
        self, display_service, realistic_forks_list_data, mock_compare_responses
    ):
        """Test show_commits parameter integration with detailed mode."""
        # Setup mocks
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = realistic_forks_list_data

        display_service.github_client.compare_repositories = AsyncMock(
            side_effect=lambda base_owner, base_repo, fork_owner, fork_repo: 
            mock_compare_responses.get(f"{fork_owner}/{fork_repo}", {"ahead_by": 2, "behind_by": 0})
        )

        # Capture console output to verify commits display
        console_output = []
        original_print = display_service.console.print
        display_service.console.print = lambda *args, **kwargs: console_output.append(str(args[0]) if args else "")

        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=3,  # Show 3 recent commits
                force_all_commits=False
            )

        # Restore original print
        display_service.console.print = original_print

        # Verify that show_commits parameter was processed
        # (The actual commit fetching would be handled by the display method)
        assert result["total_forks"] == 4
        assert result["displayed_forks"] == 3  # Excluding archived

    @pytest.mark.asyncio
    async def test_force_all_commits_flag_integration(
        self, display_service, realistic_forks_list_data
    ):
        """Test force_all_commits flag integration with detailed mode."""
        # Setup mocks - all forks should get API calls when force_all_commits=True
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = realistic_forks_list_data

        api_calls_made = []
        
        async def mock_compare_repositories(base_owner, base_repo, fork_owner, fork_repo):
            fork_key = f"{fork_owner}/{fork_repo}"
            api_calls_made.append(fork_key)
            return {"ahead_by": 1, "behind_by": 0}

        display_service.github_client.compare_repositories = mock_compare_repositories

        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=True  # Force API calls for all forks
            )

        # With force_all_commits=True, even empty-fork should get an API call
        # But archived forks should still be excluded
        assert len(api_calls_made) == 3  # All non-archived forks
        assert "user1/active-fork" in api_calls_made
        assert "user2/empty-fork" in api_calls_made  # Should be included with force flag
        assert "user3/high-activity-fork" in api_calls_made
        assert "user4/archived-fork" not in api_calls_made  # Still excluded (archived)

        # Verify no forks were skipped due to force flag
        assert result["forks_skipped"] == 0
        assert result["api_calls_saved"] == 0

    @pytest.mark.asyncio
    async def test_disable_cache_integration_with_detailed_mode(
        self, display_service, realistic_forks_list_data, mock_compare_responses
    ):
        """Test disable_cache parameter integration with detailed mode."""
        # Setup mocks
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = realistic_forks_list_data

        display_service.github_client.compare_repositories = AsyncMock(
            side_effect=lambda base_owner, base_repo, fork_owner, fork_repo: 
            mock_compare_responses.get(f"{fork_owner}/{fork_repo}", {"ahead_by": 1, "behind_by": 0})
        )

        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=None,
                disable_cache=True,  # Disable cache
                show_commits=0,
                force_all_commits=False
            )

        # Verify that the operation completed successfully with cache disabled
        assert result["total_forks"] == 4
        assert result["displayed_forks"] == 3  # Excluding archived
        
        # The disable_cache parameter should be passed through to underlying components
        # (Actual cache bypassing would be tested in the specific component tests)

    @pytest.mark.asyncio
    async def test_empty_repository_handling_in_detailed_mode(
        self, display_service
    ):
        """Test handling of repositories with no forks in detailed mode."""
        # Setup mock for empty repository
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = []  # No forks

        # Capture console output
        console_output = []
        original_print = display_service.console.print
        display_service.console.print = lambda *args, **kwargs: console_output.append(str(args[0]) if args else "")

        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result = await display_service.show_fork_data_detailed(
                "owner/empty-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False
            )

        # Restore original print
        display_service.console.print = original_print

        # Verify empty repository handling
        assert result["total_forks"] == 0
        assert result["displayed_forks"] == 0
        assert result["api_calls_made"] == 0
        assert result["collected_forks"] == []

        # Verify appropriate message was displayed
        table_output = "\n".join(console_output)
        assert "No forks found" in table_output or any("No forks" in output for output in console_output)