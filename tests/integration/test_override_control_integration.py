"""Integration tests for override and control mechanisms."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from rich.console import Console
from io import StringIO

from forklift.analysis.override_control import (
    OverrideController,
    create_override_controller,
)
from forklift.analysis.fork_discovery import ForkDiscoveryService
from forklift.github.client import GitHubClient
from forklift.models.github import Fork, Repository


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    client = AsyncMock(spec=GitHubClient)
    return client


@pytest.fixture
def mock_console():
    """Create a mock console for testing."""
    return Console(file=StringIO(), width=80)


@pytest.fixture
def sample_repository():
    """Create a sample repository for testing."""
    return Repository(
        id=1,
        name="testrepo",
        full_name="testowner/testrepo",
        owner="testowner",
        url="https://api.github.com/repos/testowner/testrepo",
        html_url="https://github.com/testowner/testrepo",
        clone_url="https://github.com/testowner/testrepo.git",
        stars=100,
        forks_count=50,
        language="Python",
    )


@pytest.fixture
def sample_forks():
    """Create sample fork objects for testing."""
    from forklift.models.github import User
    
    forks = []
    
    # Create parent repository
    parent_repo = Repository(
        id=999,
        name="parent-repo",
        full_name="parent/parent-repo",
        owner="parent",
        url="https://api.github.com/repos/parent/parent-repo",
        html_url="https://github.com/parent/parent-repo",
        clone_url="https://github.com/parent/parent-repo.git",
        stars=100,
        forks_count=50,
        language="Python",
    )
    
    for i in range(5):
        # Create fork repository (marked as fork)
        repo = Repository(
            id=i,
            name=f"repo{i}",
            full_name=f"user{i}/repo{i}",
            owner=f"user{i}",
            url=f"https://api.github.com/repos/user{i}/repo{i}",
            html_url=f"https://github.com/user{i}/repo{i}",
            clone_url=f"https://github.com/user{i}/repo{i}.git",
            stars=i * 10,
            forks_count=i * 5,
            language="Python",
            is_fork=True,  # Mark as fork
        )
        
        # Create user
        user = User(
            login=f"user{i}",
            id=i,
            avatar_url=f"https://github.com/user{i}.png",
            html_url=f"https://github.com/user{i}",
        )
        
        fork = Fork(
            repository=repo,
            parent=parent_repo,
            owner=user,
            commits_ahead=i if i > 0 else 0,  # First fork has no commits ahead
            commits_behind=0,
            is_active=i > 2,  # Only forks 3 and 4 are active (3 out of 5)
        )
        forks.append(fork)
    return forks


class TestOverrideControllerIntegration:
    """Integration tests for OverrideController with real workflow scenarios."""

    @pytest.mark.asyncio
    async def test_scan_all_override_integration(
        self, mock_console, sample_forks, mock_github_client
    ):
        """Test scan_all override integration with fork discovery workflow."""
        # Create controller with scan_all enabled
        controller = create_override_controller(
            mock_console, scan_all=True, interactive_confirmations=False
        )

        # Simulate fork discovery returning filtered forks
        original_active_count = sum(1 for fork in sample_forks if fork.is_active)
        assert original_active_count == 2  # Only forks 3, 4 are active (i > 2)

        # Apply scan_all override
        result_forks = controller.apply_filtering_overrides(sample_forks)

        # All forks should now be active
        assert len(result_forks) == 5
        assert all(fork.is_active for fork in result_forks)

        # Verify expensive operation approval
        approval = await controller.check_expensive_operation_approval(
            "fork_analysis", forks=result_forks, description="comprehensive analysis"
        )
        assert approval is True

        # Log override status
        controller.log_override_status()
        controller.display_override_summary()

    @pytest.mark.asyncio
    async def test_force_override_integration(
        self, mock_console, sample_forks, mock_github_client
    ):
        """Test force override integration with individual fork analysis."""
        # Create controller with force enabled
        controller = create_override_controller(
            mock_console, force=True, interactive_confirmations=False
        )

        # Test fork with no commits ahead (normally would be skipped)
        fork_no_commits = sample_forks[0]  # Has 0 commits ahead
        assert fork_no_commits.commits_ahead == 0

        # Force override should allow analysis
        should_analyze = controller.should_force_individual_analysis(
            fork_no_commits, has_commits_ahead=False
        )
        assert should_analyze is True

        # Detailed analysis should be approved
        approval = await controller.check_expensive_operation_approval(
            "detailed_analysis",
            fork_url=fork_no_commits.repository.html_url,
            has_commits_ahead=False,
        )
        assert approval is True

    @pytest.mark.asyncio
    @patch('forklift.analysis.override_control.Confirm.ask')
    async def test_interactive_confirmation_integration(
        self, mock_confirm, mock_console, sample_forks
    ):
        """Test interactive confirmation integration with user workflow."""
        # Setup user responses: decline first, accept second
        mock_confirm.side_effect = [False, True]

        # Create controller with interactive confirmations enabled
        controller = create_override_controller(
            mock_console, interactive_confirmations=True
        )

        # First operation should be declined
        approval1 = await controller.check_expensive_operation_approval(
            "fork_analysis", forks=sample_forks[:3], description="initial analysis"
        )
        assert approval1 is False

        # Second operation should be accepted
        approval2 = await controller.check_expensive_operation_approval(
            "ai_summary", commit_count=25, estimated_cost=0.15
        )
        assert approval2 is True

        # Verify both confirmations were called
        assert mock_confirm.call_count == 2

    @pytest.mark.asyncio
    async def test_combined_overrides_integration(
        self, mock_console, sample_forks, mock_github_client
    ):
        """Test integration of multiple override mechanisms together."""
        # Create controller with both scan_all and force enabled
        controller = create_override_controller(
            mock_console,
            scan_all=True,
            force=True,
            interactive_confirmations=False,
        )

        # Display override summary
        controller.display_override_summary()

        # Apply scan_all override (should activate all forks)
        filtered_forks = controller.apply_filtering_overrides(sample_forks)
        assert len(filtered_forks) == 5
        assert all(fork.is_active for fork in filtered_forks)

        # Test force override on fork with no commits ahead
        fork_no_commits = filtered_forks[0]
        should_analyze = controller.should_force_individual_analysis(
            fork_no_commits, has_commits_ahead=False
        )
        assert should_analyze is True

        # All expensive operations should be approved
        fork_analysis_approval = await controller.check_expensive_operation_approval(
            "fork_analysis", forks=filtered_forks
        )
        ai_summary_approval = await controller.check_expensive_operation_approval(
            "ai_summary", commit_count=50, estimated_cost=0.25
        )
        detailed_analysis_approval = await controller.check_expensive_operation_approval(
            "detailed_analysis", fork_url=fork_no_commits.repository.html_url
        )

        assert fork_analysis_approval is True
        assert ai_summary_approval is True
        assert detailed_analysis_approval is True

    @pytest.mark.asyncio
    async def test_no_overrides_normal_workflow(
        self, mock_console, sample_forks, mock_github_client
    ):
        """Test normal workflow without any overrides enabled."""
        # Create controller with no overrides
        controller = create_override_controller(
            mock_console,
            scan_all=False,
            force=False,
            interactive_confirmations=False,
        )

        # Filtering should not change fork states
        filtered_forks = controller.apply_filtering_overrides(sample_forks)
        assert len(filtered_forks) == 5

        # Fork activity should remain unchanged
        for i, fork in enumerate(filtered_forks):
            expected_active = i > 2  # Original logic: only forks 3, 4 are active (i > 2)
            assert fork.is_active == expected_active

        # Force analysis should respect normal filtering
        fork_no_commits = sample_forks[0]
        should_analyze = controller.should_force_individual_analysis(
            fork_no_commits, has_commits_ahead=False
        )
        assert should_analyze is False  # Should not force analysis

        # Expensive operations should still be approved (confirmations disabled)
        approval = await controller.check_expensive_operation_approval(
            "fork_analysis", forks=filtered_forks
        )
        assert approval is True

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, mock_console, sample_forks):
        """Test error handling in override mechanisms."""
        # Create controller with confirmations disabled to avoid stdin issues
        controller = create_override_controller(
            mock_console, interactive_confirmations=False
        )

        # Test with invalid operation type
        approval = await controller.check_expensive_operation_approval(
            "invalid_operation_type", some_param="value"
        )
        assert approval is True  # Should default to True for unknown operations

        # Test with missing parameters (should not crash)
        approval = await controller.check_expensive_operation_approval("fork_analysis")
        assert approval is True

        # Test with None values
        should_analyze = controller.should_force_individual_analysis(
            sample_forks[0], has_commits_ahead=None
        )
        assert should_analyze is True  # Should default to True for None


class TestWorkflowIntegration:
    """Test integration with actual workflow components."""

    @pytest.mark.asyncio
    async def test_fork_discovery_with_scan_all_override(
        self, mock_console, mock_github_client, sample_repository, sample_forks
    ):
        """Test fork discovery integration with scan_all override."""
        # Mock fork discovery service
        mock_discovery = AsyncMock(spec=ForkDiscoveryService)
        mock_discovery.discover_forks.return_value = sample_forks

        # Create override controller with scan_all
        controller = create_override_controller(
            mock_console, scan_all=True, interactive_confirmations=False
        )

        # Simulate workflow: discover forks, then apply overrides
        discovered_forks = await mock_discovery.discover_forks(
            sample_repository.html_url
        )

        # Apply scan_all override
        final_forks = controller.apply_filtering_overrides(discovered_forks)

        # Verify all forks are now active
        assert len(final_forks) == 5
        assert all(fork.is_active for fork in final_forks)

        # Verify discovery was called
        mock_discovery.discover_forks.assert_called_once_with(
            sample_repository.html_url
        )

    @pytest.mark.asyncio
    @patch('forklift.analysis.override_control.Confirm.ask')
    async def test_expensive_operation_workflow_with_confirmations(
        self, mock_confirm, mock_console, sample_forks
    ):
        """Test expensive operation workflow with user confirmations."""
        # Setup user responses for different operations
        mock_confirm.side_effect = [
            True,   # Approve fork analysis
            False,  # Decline AI summary
            True,   # Approve detailed analysis
        ]

        # Create controller with confirmations enabled
        controller = create_override_controller(
            mock_console, interactive_confirmations=True
        )

        # Simulate workflow with multiple expensive operations
        operations = [
            ("fork_analysis", {"forks": sample_forks[:3]}),
            ("ai_summary", {"commit_count": 20, "estimated_cost": 0.10}),
            ("detailed_analysis", {"fork_url": "https://github.com/user/repo"}),
        ]

        results = []
        for operation_type, kwargs in operations:
            approval = await controller.check_expensive_operation_approval(
                operation_type, **kwargs
            )
            results.append(approval)

        # Verify expected results
        assert results == [True, False, True]
        assert mock_confirm.call_count == 3

    @pytest.mark.asyncio
    async def test_cli_integration_simulation(self, mock_console, sample_forks):
        """Test simulation of CLI integration with override flags."""
        # Simulate CLI flags
        cli_flags = {
            "scan_all": True,
            "force": False,
            "interactive": False,
        }

        # Create controller based on CLI flags
        controller = create_override_controller(
            mock_console,
            scan_all=cli_flags["scan_all"],
            force=cli_flags["force"],
            interactive_confirmations=cli_flags["interactive"],
        )

        # Display override summary (like CLI would do)
        controller.display_override_summary()

        # Simulate fork processing workflow
        processed_forks = controller.apply_filtering_overrides(sample_forks)

        # Verify scan_all effect
        assert all(fork.is_active for fork in processed_forks)

        # Simulate expensive operation check
        approval = await controller.check_expensive_operation_approval(
            "fork_analysis", forks=processed_forks
        )
        assert approval is True  # Should auto-approve when interactive=False

    @pytest.mark.asyncio
    async def test_configuration_validation_integration(self, mock_console):
        """Test configuration validation in integration scenarios."""
        # Test various configuration combinations
        configs = [
            {"scan_all": True, "force": True, "interactive_confirmations": True},
            {"scan_all": False, "force": True, "interactive_confirmations": False},
            {"scan_all": True, "force": False, "interactive_confirmations": True},
            {"scan_all": False, "force": False, "interactive_confirmations": False},
        ]

        for config in configs:
            controller = create_override_controller(mock_console, **config)

            # Verify configuration is applied correctly
            assert controller.config.scan_all == config["scan_all"]
            assert controller.config.force == config["force"]
            assert (
                controller.config.interactive_confirmations
                == config["interactive_confirmations"]
            )

            # Test basic functionality doesn't break
            controller.log_override_status()
            controller.display_override_summary()

    @pytest.mark.asyncio
    async def test_performance_impact_simulation(self, mock_console, sample_forks):
        """Test simulation of performance impact with different override settings."""
        # Create large fork list to simulate performance impact
        large_fork_list = sample_forks * 20  # 100 forks

        # Test with scan_all (should process all forks)
        scan_all_controller = create_override_controller(
            mock_console, scan_all=True, interactive_confirmations=False
        )

        processed_forks = scan_all_controller.apply_filtering_overrides(large_fork_list)
        assert len(processed_forks) == 100
        assert all(fork.is_active for fork in processed_forks)

        # Test expensive operation approval for large dataset
        approval = await scan_all_controller.check_expensive_operation_approval(
            "fork_analysis", forks=processed_forks
        )
        assert approval is True

        # Test with normal filtering (should respect original states)
        normal_controller = create_override_controller(
            mock_console, scan_all=False, interactive_confirmations=False
        )

        normal_processed = normal_controller.apply_filtering_overrides(large_fork_list)
        assert len(normal_processed) == 100

        # Count active forks (should be less than with scan_all)
        active_count = sum(1 for fork in normal_processed if fork.is_active)
        assert active_count == 40  # Only 2 out of 5 forks are active, so 40 out of 100