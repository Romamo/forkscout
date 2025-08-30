"""Contract tests for show-forks --detail functionality."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console

from forklift.config.settings import ForkliftConfig, GitHubConfig
from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.github.client import GitHubClient
from forklift.github.fork_list_processor import ForkListProcessor
from forklift.models.fork_qualification import CollectedForkData, ForkQualificationMetrics


class TestShowForksDetailContracts:
    """Contract tests for show-forks --detail functionality."""

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
    def standard_fork_data(self):
        """Create standard fork data for contract testing."""
        base_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
        
        return [
            {
                "id": 123,
                "name": "test-fork",
                "full_name": "user1/test-fork",
                "owner": {"login": "user1"},
                "html_url": "https://github.com/user1/test-fork",
                "stargazers_count": 10,
                "forks_count": 2,
                "watchers_count": 8,
                "size": 1500,
                "language": "Python",
                "topics": ["test"],
                "open_issues_count": 1,
                "created_at": base_time.isoformat(),
                "updated_at": (base_time.replace(month=6)).isoformat(),
                "pushed_at": (base_time.replace(month=6)).isoformat(),
                "archived": False,
                "disabled": False,
                "fork": True,
                "description": "A test fork",
                "homepage": None,
                "default_branch": "main",
                "license": {"key": "mit", "name": "MIT License"},
            }
        ]

    @pytest.mark.asyncio
    async def test_show_fork_data_detailed_return_contract(
        self, display_service, standard_fork_data
    ):
        """Test that show_fork_data_detailed returns the expected data structure."""
        # Setup mocks
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = standard_fork_data

        display_service.github_client.compare_repositories = AsyncMock(
            return_value={"ahead_by": 5, "behind_by": 2}
        )

        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False
            )

        # Contract assertions - verify required fields are present
        assert isinstance(result, dict)
        
        # Required top-level fields
        required_fields = [
            "total_forks",
            "displayed_forks", 
            "collected_forks",
            "api_calls_made",
            "api_calls_saved",
            "forks_skipped",
            "forks_analyzed"
        ]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        # Field type contracts
        assert isinstance(result["total_forks"], int)
        assert isinstance(result["displayed_forks"], int)
        assert isinstance(result["collected_forks"], list)
        assert isinstance(result["api_calls_made"], int)
        assert isinstance(result["api_calls_saved"], int)
        assert isinstance(result["forks_skipped"], int)
        assert isinstance(result["forks_analyzed"], int)
        
        # Value contracts
        assert result["total_forks"] >= 0
        assert result["displayed_forks"] >= 0
        assert result["api_calls_made"] >= 0
        assert result["api_calls_saved"] >= 0
        assert result["forks_skipped"] >= 0
        assert result["forks_analyzed"] >= 0
        
        # Logical contracts
        assert result["displayed_forks"] <= result["total_forks"]
        assert result["forks_skipped"] + result["forks_analyzed"] <= result["total_forks"]

    @pytest.mark.asyncio
    async def test_collected_fork_data_structure_contract(
        self, display_service, standard_fork_data
    ):
        """Test that collected fork data has the expected structure."""
        # Setup mocks
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = standard_fork_data

        display_service.github_client.compare_repositories = AsyncMock(
            return_value={"ahead_by": 3, "behind_by": 1}
        )

        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False
            )

        # Verify collected fork data structure
        collected_forks = result["collected_forks"]
        assert len(collected_forks) > 0
        
        for fork_data in collected_forks:
            # Each fork should have these attributes
            assert hasattr(fork_data, 'metrics')
            assert hasattr(fork_data, 'exact_commits_ahead')
            
            # Metrics should have required fields
            metrics = fork_data.metrics
            required_metrics_fields = [
                'name', 'owner', 'stargazers_count', 'forks_count', 'size',
                'language', 'created_at', 'updated_at', 'pushed_at',
                'archived', 'disabled', 'can_skip_analysis'
            ]
            
            for field in required_metrics_fields:
                assert hasattr(metrics, field), f"Missing metrics field: {field}"
            
            # exact_commits_ahead should be int, str ("Unknown"), or 0
            commits_ahead = fork_data.exact_commits_ahead
            assert isinstance(commits_ahead, (int, str))
            if isinstance(commits_ahead, str):
                assert commits_ahead == "Unknown"
            if isinstance(commits_ahead, int):
                assert commits_ahead >= 0

    @pytest.mark.asyncio
    async def test_parameter_contract_validation(
        self, display_service, standard_fork_data
    ):
        """Test that method parameters are validated according to contract."""
        # Setup mocks
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = standard_fork_data

        display_service.github_client.compare_repositories = AsyncMock(
            return_value={"ahead_by": 1, "behind_by": 0}
        )

        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            # Test with valid parameters
            result = await display_service.show_fork_data_detailed(
                repo_url="owner/test-repo",
                max_forks=10,
                disable_cache=True,
                show_commits=5,
                force_all_commits=True
            )
            
            assert isinstance(result, dict)
            
            # Test with None values (should be handled gracefully)
            result = await display_service.show_fork_data_detailed(
                repo_url="owner/test-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False
            )
            
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_error_handling_contract(
        self, display_service, standard_fork_data
    ):
        """Test that error handling follows the expected contract."""
        # Setup mocks
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = standard_fork_data

        # Mock compare API to fail
        display_service.github_client.compare_repositories = AsyncMock(
            side_effect=Exception("API Error")
        )

        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            # Method should not raise exception, but handle errors gracefully
            result = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False
            )

        # Contract: method should return valid result even with API errors
        assert isinstance(result, dict)
        assert "total_forks" in result
        assert "collected_forks" in result
        
        # Forks with API errors should have "Unknown" status
        collected_forks = result["collected_forks"]
        if len(collected_forks) > 0:
            # At least one fork should have "Unknown" status due to API error
            unknown_forks = [f for f in collected_forks if f.exact_commits_ahead == "Unknown"]
            assert len(unknown_forks) > 0

    @pytest.mark.asyncio
    async def test_empty_repository_contract(
        self, display_service
    ):
        """Test contract behavior with empty repository (no forks)."""
        # Setup mocks for empty repository
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = []

        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result = await display_service.show_fork_data_detailed(
                "owner/empty-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False
            )

        # Contract: empty repository should return valid structure
        assert isinstance(result, dict)
        assert result["total_forks"] == 0
        assert result["displayed_forks"] == 0
        assert result["collected_forks"] == []
        assert result["api_calls_made"] == 0
        assert result["api_calls_saved"] == 0
        assert result["forks_skipped"] == 0
        assert result["forks_analyzed"] == 0

    @pytest.mark.asyncio
    async def test_max_forks_limit_contract(
        self, display_service, standard_fork_data
    ):
        """Test that max_forks parameter is respected according to contract."""
        # Create multiple forks
        multiple_forks = []
        for i in range(5):
            fork_data = standard_fork_data[0].copy()
            fork_data["id"] = 123 + i
            fork_data["name"] = f"test-fork-{i}"
            fork_data["full_name"] = f"user{i}/test-fork-{i}"
            fork_data["owner"] = {"login": f"user{i}"}
            multiple_forks.append(fork_data)

        # Setup mocks
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = multiple_forks

        display_service.github_client.compare_repositories = AsyncMock(
            return_value={"ahead_by": 2, "behind_by": 0}
        )

        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=3,  # Limit to 3 forks
                disable_cache=False,
                show_commits=0,
                force_all_commits=False
            )

        # Contract: max_forks should limit the number of forks processed
        assert result["total_forks"] <= 3
        assert len(result["collected_forks"]) <= 3

    @pytest.mark.asyncio
    async def test_api_call_optimization_contract(
        self, display_service
    ):
        """Test that API call optimization follows the expected contract."""
        base_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
        
        # Create forks with different commit ahead scenarios
        mixed_forks = [
            # Fork with commits ahead (should get API call)
            {
                "id": 1,
                "name": "active-fork",
                "full_name": "user1/active-fork",
                "owner": {"login": "user1"},
                "html_url": "https://github.com/user1/active-fork",
                "stargazers_count": 5,
                "forks_count": 1,
                "watchers_count": 3,
                "size": 1000,
                "language": "Python",
                "topics": [],
                "open_issues_count": 0,
                "created_at": base_time.isoformat(),
                "updated_at": (base_time.replace(month=6)).isoformat(),
                "pushed_at": (base_time.replace(month=6)).isoformat(),  # Later than created_at
                "archived": False,
                "disabled": False,
                "fork": True,
                "description": "Active fork",
                "homepage": None,
                "default_branch": "main",
                "license": None,
            },
            # Fork with no commits ahead (should be skipped)
            {
                "id": 2,
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
            }
        ]

        # Setup mocks
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = mixed_forks

        api_calls_made = []
        
        async def mock_compare_repositories(base_owner, base_repo, fork_owner, fork_repo):
            api_calls_made.append(f"{fork_owner}/{fork_repo}")
            return {"ahead_by": 3, "behind_by": 1}

        display_service.github_client.compare_repositories = mock_compare_repositories

        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False
            )

        # Contract: optimization should skip forks with no commits ahead
        assert len(api_calls_made) == 1  # Only active-fork should get API call
        assert "user1/active-fork" in api_calls_made
        assert "user2/empty-fork" not in api_calls_made
        
        # Contract: skipped forks should have exact_commits_ahead = 0
        collected_forks = result["collected_forks"]
        for fork in collected_forks:
            if fork.metrics.name == "empty-fork":
                assert fork.exact_commits_ahead == 0
            elif fork.metrics.name == "active-fork":
                assert fork.exact_commits_ahead == 3

        # Contract: API call statistics should be accurate
        assert result["api_calls_made"] == 1
        assert result["api_calls_saved"] == 1
        assert result["forks_skipped"] == 1
        assert result["forks_analyzed"] == 1

    @pytest.mark.asyncio
    async def test_force_all_commits_contract(
        self, display_service
    ):
        """Test that force_all_commits parameter follows the expected contract."""
        base_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
        
        # Create fork that would normally be skipped
        fork_data = [{
            "id": 1,
            "name": "empty-fork",
            "full_name": "user1/empty-fork",
            "owner": {"login": "user1"},
            "html_url": "https://github.com/user1/empty-fork",
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
        }]

        # Setup mocks
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = fork_data

        api_calls_made = []
        
        async def mock_compare_repositories(base_owner, base_repo, fork_owner, fork_repo):
            api_calls_made.append(f"{fork_owner}/{fork_repo}")
            return {"ahead_by": 0, "behind_by": 5}

        display_service.github_client.compare_repositories = mock_compare_repositories

        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result = await display_service.show_fork_data_detailed(
                "owner/test-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=True  # Force API call even for empty fork
            )

        # Contract: force_all_commits should override optimization
        assert len(api_calls_made) == 1
        assert "user1/empty-fork" in api_calls_made
        
        # Contract: no forks should be skipped when force_all_commits=True
        assert result["forks_skipped"] == 0
        assert result["api_calls_saved"] == 0
        assert result["api_calls_made"] == 1

    @pytest.mark.asyncio
    async def test_console_output_contract(
        self, display_service, standard_fork_data
    ):
        """Test that console output follows the expected contract."""
        # Setup mocks
        fork_processor = AsyncMock(spec=ForkListProcessor)
        fork_processor.get_all_forks_list_data.return_value = standard_fork_data

        display_service.github_client.compare_repositories = AsyncMock(
            return_value={"ahead_by": 2, "behind_by": 1}
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

        # Contract: console output should be generated
        assert len(console_output) > 0
        
        # Contract: output should contain relevant information
        output_text = "\n".join(console_output)
        
        # Should contain fork information or table elements
        assert any(
            keyword in output_text.lower() 
            for keyword in ["fork", "table", "detailed", "information"]
        )

    @pytest.mark.asyncio
    async def test_method_signature_contract(self, display_service):
        """Test that method signature remains stable (contract)."""
        import inspect
        
        # Get method signature
        sig = inspect.signature(display_service.show_fork_data_detailed)
        
        # Contract: method should have expected parameters
        expected_params = [
            'self', 'repo_url', 'max_forks', 'disable_cache', 
            'show_commits', 'force_all_commits'
        ]
        
        actual_params = list(sig.parameters.keys())
        assert actual_params == expected_params
        
        # Contract: parameter defaults should be stable
        assert sig.parameters['max_forks'].default is None
        assert sig.parameters['disable_cache'].default is False
        assert sig.parameters['show_commits'].default == 0
        assert sig.parameters['force_all_commits'].default is False