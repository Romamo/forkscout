"""Integration tests for user interaction flows with override mechanisms."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from rich.console import Console
from io import StringIO

from forkscout.analysis.override_control import (
    OverrideController,
    create_override_controller,
)
from forkscout.models.github import Fork, Repository


@pytest.fixture
def mock_console():
    """Create a mock console for testing."""
    return Console(file=StringIO(), width=80)


@pytest.fixture
def sample_forks():
    """Create sample fork objects for testing."""
    from forkscout.models.github import User
    
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
    
    for i in range(3):
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
            commits_ahead=i + 1,
            commits_behind=0,
            is_active=True,
        )
        forks.append(fork)
    return forks


class TestUserInteractionFlows:
    """Test user interaction flows with override mechanisms."""

    @pytest.mark.asyncio
    @patch('forklift.analysis.override_control.Confirm.ask')
    async def test_user_accepts_all_confirmations(
        self, mock_confirm, mock_console, sample_forks
    ):
        """Test user flow where user accepts all confirmation prompts."""
        # User accepts all prompts
        mock_confirm.return_value = True

        controller = create_override_controller(
            mock_console, interactive_confirmations=True
        )

        # Simulate multiple expensive operations in sequence
        operations = [
            ("fork_analysis", {"forks": sample_forks, "description": "comprehensive analysis"}),
            ("ai_summary", {"commit_count": 15, "estimated_cost": 0.08}),
            ("detailed_analysis", {"fork_url": "https://github.com/user/repo", "has_commits_ahead": True}),
        ]

        results = []
        for operation_type, kwargs in operations:
            result = await controller.check_expensive_operation_approval(
                operation_type, **kwargs
            )
            results.append(result)

        # All operations should be approved
        assert all(results)
        assert mock_confirm.call_count == 3

    @pytest.mark.asyncio
    @patch('forklift.analysis.override_control.Confirm.ask')
    async def test_user_declines_all_confirmations(
        self, mock_confirm, mock_console, sample_forks
    ):
        """Test user flow where user declines all confirmation prompts."""
        # User declines all prompts
        mock_confirm.return_value = False

        controller = create_override_controller(
            mock_console, interactive_confirmations=True
        )

        # Simulate multiple expensive operations
        operations = [
            ("fork_analysis", {"forks": sample_forks}),
            ("ai_summary", {"commit_count": 20}),
            ("detailed_analysis", {"fork_url": "https://github.com/user/repo"}),
        ]

        results = []
        for operation_type, kwargs in operations:
            result = await controller.check_expensive_operation_approval(
                operation_type, **kwargs
            )
            results.append(result)

        # All operations should be declined
        assert not any(results)
        assert mock_confirm.call_count == 3

    @pytest.mark.asyncio
    @patch('forklift.analysis.override_control.Confirm.ask')
    async def test_user_selective_confirmations(
        self, mock_confirm, mock_console, sample_forks
    ):
        """Test user flow with selective confirmations."""
        # User makes selective choices: accept, decline, accept
        mock_confirm.side_effect = [True, False, True]

        controller = create_override_controller(
            mock_console, interactive_confirmations=True
        )

        # Test fork analysis (should be accepted)
        fork_analysis_result = await controller.check_expensive_operation_approval(
            "fork_analysis", forks=sample_forks, description="initial scan"
        )

        # Test AI summary (should be declined)
        ai_summary_result = await controller.check_expensive_operation_approval(
            "ai_summary", commit_count=50, estimated_cost=0.25
        )

        # Test detailed analysis (should be accepted)
        detailed_analysis_result = await controller.check_expensive_operation_approval(
            "detailed_analysis", 
            fork_url="https://github.com/user/repo",
            has_commits_ahead=False
        )

        assert fork_analysis_result is True
        assert ai_summary_result is False
        assert detailed_analysis_result is True
        assert mock_confirm.call_count == 3

    @pytest.mark.asyncio
    async def test_user_bypasses_confirmations_with_flags(
        self, mock_console, sample_forks
    ):
        """Test user flow where confirmations are bypassed with CLI flags."""
        # Create controller with confirmations disabled
        controller = create_override_controller(
            mock_console, interactive_confirmations=False
        )

        # All operations should be auto-approved
        operations = [
            ("fork_analysis", {"forks": sample_forks}),
            ("ai_summary", {"commit_count": 100, "estimated_cost": 0.50}),
            ("detailed_analysis", {"fork_url": "https://github.com/user/repo"}),
        ]

        results = []
        for operation_type, kwargs in operations:
            result = await controller.check_expensive_operation_approval(
                operation_type, **kwargs
            )
            results.append(result)

        # All should be approved without user interaction
        assert all(results)

    @pytest.mark.asyncio
    @patch('forklift.analysis.override_control.Confirm.ask')
    async def test_user_confirmation_with_cost_information(
        self, mock_confirm, mock_console
    ):
        """Test user confirmation flow with detailed cost information."""
        mock_confirm.return_value = True

        controller = create_override_controller(
            mock_console, interactive_confirmations=True
        )

        # Test AI summary with cost information
        result = await controller.check_expensive_operation_approval(
            "ai_summary", 
            commit_count=75, 
            estimated_cost=0.35
        )

        assert result is True
        mock_confirm.assert_called_once()

        # Verify the confirmation was called with appropriate parameters
        call_args = mock_confirm.call_args
        assert "Proceed with AI summary generation?" in str(call_args)

    @pytest.mark.asyncio
    @patch('forklift.analysis.override_control.Confirm.ask')
    async def test_user_confirmation_for_fork_with_no_commits(
        self, mock_confirm, mock_console
    ):
        """Test user confirmation for analyzing fork with no commits ahead."""
        mock_confirm.return_value = True

        controller = create_override_controller(
            mock_console, interactive_confirmations=True
        )

        # Test detailed analysis for fork with no commits ahead
        result = await controller.check_expensive_operation_approval(
            "detailed_analysis",
            fork_url="https://github.com/user/inactive-fork",
            has_commits_ahead=False
        )

        assert result is True
        mock_confirm.assert_called_once()

    @pytest.mark.asyncio
    async def test_user_workflow_with_scan_all_override(
        self, mock_console, sample_forks
    ):
        """Test complete user workflow with scan_all override."""
        # Create controller with scan_all enabled
        controller = create_override_controller(
            mock_console, 
            scan_all=True, 
            interactive_confirmations=False
        )

        # Display override summary to user
        controller.display_override_summary()

        # Mark some forks as inactive (simulating normal filtering)
        sample_forks[0].is_active = False
        sample_forks[1].is_active = False

        # Apply scan_all override
        processed_forks = controller.apply_filtering_overrides(sample_forks)

        # Verify all forks are now active
        assert all(fork.is_active for fork in processed_forks)

        # Expensive operations should be auto-approved
        approval = await controller.check_expensive_operation_approval(
            "fork_analysis", forks=processed_forks
        )
        assert approval is True

    @pytest.mark.asyncio
    async def test_user_workflow_with_force_override(
        self, mock_console, sample_forks
    ):
        """Test user workflow with force override for individual forks."""
        # Create controller with force enabled
        controller = create_override_controller(
            mock_console, 
            force=True, 
            interactive_confirmations=False
        )

        # Test forcing analysis of fork with no commits ahead
        fork_no_commits = sample_forks[0]
        fork_no_commits.commits_ahead = 0

        # Force override should allow analysis
        should_analyze = controller.should_force_individual_analysis(
            fork_no_commits, has_commits_ahead=False
        )
        assert should_analyze is True

        # Detailed analysis should be approved
        approval = await controller.check_expensive_operation_approval(
            "detailed_analysis",
            fork_url=fork_no_commits.repository.html_url,
            has_commits_ahead=False
        )
        assert approval is True

    @pytest.mark.asyncio
    @patch('forklift.analysis.override_control.Confirm.ask')
    async def test_user_workflow_mixed_overrides_and_confirmations(
        self, mock_confirm, mock_console, sample_forks
    ):
        """Test user workflow with mixed override settings and confirmations."""
        # User accepts some operations, declines others
        mock_confirm.side_effect = [True, False, True]

        # Create controller with scan_all but interactive confirmations
        controller = create_override_controller(
            mock_console,
            scan_all=True,
            force=False,
            interactive_confirmations=True
        )

        # Apply scan_all override
        processed_forks = controller.apply_filtering_overrides(sample_forks)
        assert all(fork.is_active for fork in processed_forks)

        # Test multiple operations with user confirmations
        fork_analysis_result = await controller.check_expensive_operation_approval(
            "fork_analysis", forks=processed_forks
        )

        ai_summary_result = await controller.check_expensive_operation_approval(
            "ai_summary", commit_count=30
        )

        detailed_analysis_result = await controller.check_expensive_operation_approval(
            "detailed_analysis", fork_url="https://github.com/user/repo"
        )

        # Results should match user choices
        assert fork_analysis_result is True
        assert ai_summary_result is False
        assert detailed_analysis_result is True

    @pytest.mark.asyncio
    async def test_user_error_recovery_workflow(self, mock_console, sample_forks):
        """Test user workflow with error recovery scenarios."""
        controller = create_override_controller(
            mock_console, interactive_confirmations=False
        )

        # Test with invalid operation type (should not crash)
        result = await controller.check_expensive_operation_approval(
            "invalid_operation"
        )
        assert result is True  # Should default to True

        # Test with missing parameters (should not crash)
        result = await controller.check_expensive_operation_approval(
            "fork_analysis"
        )
        assert result is True

        # Test force override with None values
        should_analyze = controller.should_force_individual_analysis(
            sample_forks[0], has_commits_ahead=None
        )
        assert should_analyze is True

    @pytest.mark.asyncio
    @patch('forklift.analysis.override_control.Confirm.ask')
    async def test_user_workflow_large_dataset_confirmation(
        self, mock_confirm, mock_console, sample_forks
    ):
        """Test user confirmation workflow with large datasets."""
        mock_confirm.return_value = True

        controller = create_override_controller(
            mock_console, interactive_confirmations=True
        )

        # Create large fork dataset
        large_fork_list = sample_forks * 50  # 150 forks

        # Test confirmation for large fork analysis
        result = await controller.check_expensive_operation_approval(
            "fork_analysis", 
            forks=large_fork_list,
            description="comprehensive repository analysis"
        )

        assert result is True
        mock_confirm.assert_called_once()

        # Test AI summary for many commits
        result = await controller.check_expensive_operation_approval(
            "ai_summary",
            commit_count=500,
            estimated_cost=2.50
        )

        assert result is True
        assert mock_confirm.call_count == 2

    @pytest.mark.asyncio
    async def test_user_workflow_configuration_display(self, mock_console):
        """Test user workflow with configuration display and logging."""
        # Test different configuration combinations
        configs = [
            {"scan_all": True, "force": False, "interactive_confirmations": True},
            {"scan_all": False, "force": True, "interactive_confirmations": False},
            {"scan_all": True, "force": True, "interactive_confirmations": True},
        ]

        for config in configs:
            controller = create_override_controller(mock_console, **config)

            # Display configuration to user
            controller.display_override_summary()

            # Log configuration for debugging
            controller.log_override_status()

            # Verify configuration is accessible
            assert controller.config.scan_all == config["scan_all"]
            assert controller.config.force == config["force"]
            assert (
                controller.config.interactive_confirmations 
                == config["interactive_confirmations"]
            )

    @pytest.mark.asyncio
    @patch('forklift.analysis.override_control.Confirm.ask')
    async def test_user_workflow_timeout_simulation(
        self, mock_confirm, mock_console, sample_forks
    ):
        """Test user workflow simulating confirmation timeouts."""
        # Simulate timeout by raising KeyboardInterrupt
        mock_confirm.side_effect = KeyboardInterrupt("User interrupted")

        controller = create_override_controller(
            mock_console, interactive_confirmations=True
        )

        # Test that KeyboardInterrupt is properly handled
        with pytest.raises(KeyboardInterrupt):
            await controller.check_expensive_operation_approval(
                "fork_analysis", forks=sample_forks
            )

    @pytest.mark.asyncio
    async def test_user_workflow_progressive_analysis(
        self, mock_console, sample_forks
    ):
        """Test user workflow with progressive analysis steps."""
        controller = create_override_controller(
            mock_console, interactive_confirmations=False
        )

        # Step 1: Initial fork filtering
        filtered_forks = controller.apply_filtering_overrides(sample_forks)

        # Step 2: Approve fork analysis
        fork_analysis_approved = await controller.check_expensive_operation_approval(
            "fork_analysis", forks=filtered_forks
        )
        assert fork_analysis_approved is True

        # Step 3: For each fork, check if detailed analysis should proceed
        detailed_analysis_results = []
        for fork in filtered_forks:
            should_analyze = controller.should_force_individual_analysis(
                fork, has_commits_ahead=True
            )
            detailed_analysis_results.append(should_analyze)

        # Step 4: Approve AI summary generation
        ai_summary_approved = await controller.check_expensive_operation_approval(
            "ai_summary", commit_count=len(filtered_forks) * 5
        )
        assert ai_summary_approved is True

        # Verify progressive workflow completed successfully
        assert len(detailed_analysis_results) == len(filtered_forks)
        assert all(detailed_analysis_results)  # All should be approved