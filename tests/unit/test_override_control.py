"""Unit tests for override and control mechanisms."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from rich.console import Console
from io import StringIO

from forklift.analysis.override_control import (
    OverrideConfig,
    ExpensiveOperationConfirmer,
    FilteringOverride,
    OverrideController,
    create_override_controller,
)
from forklift.models.github import Fork, Repository


@pytest.fixture
def mock_console():
    """Create a mock console for testing."""
    return Console(file=StringIO(), width=80)


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


class TestOverrideConfig:
    """Test OverrideConfig class."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = OverrideConfig()
        
        assert config.scan_all is False
        assert config.force is False
        assert config.interactive_confirmations is True
        assert config.confirmation_timeout == 30
        assert config.default_choice_on_timeout is False

    def test_custom_configuration(self):
        """Test custom configuration values."""
        config = OverrideConfig(
            scan_all=True,
            force=True,
            interactive_confirmations=False,
            confirmation_timeout=60,
            default_choice_on_timeout=True,
        )
        
        assert config.scan_all is True
        assert config.force is True
        assert config.interactive_confirmations is False
        assert config.confirmation_timeout == 60
        assert config.default_choice_on_timeout is True


class TestExpensiveOperationConfirmer:
    """Test ExpensiveOperationConfirmer class."""

    def test_init(self, mock_console):
        """Test confirmer initialization."""
        config = OverrideConfig()
        confirmer = ExpensiveOperationConfirmer(mock_console, config)
        
        assert confirmer.console == mock_console
        assert confirmer.config == config

    @pytest.mark.asyncio
    async def test_confirm_fork_analysis_disabled_confirmations(self, mock_console, sample_forks):
        """Test fork analysis confirmation when confirmations are disabled."""
        config = OverrideConfig(interactive_confirmations=False)
        confirmer = ExpensiveOperationConfirmer(mock_console, config)
        
        result = await confirmer.confirm_fork_analysis(sample_forks)
        
        assert result is True

    @pytest.mark.asyncio
    @patch('forklift.analysis.override_control.Confirm.ask')
    async def test_confirm_fork_analysis_user_accepts(self, mock_confirm, mock_console, sample_forks):
        """Test fork analysis confirmation when user accepts."""
        mock_confirm.return_value = True
        config = OverrideConfig(interactive_confirmations=True)
        confirmer = ExpensiveOperationConfirmer(mock_console, config)
        
        result = await confirmer.confirm_fork_analysis(sample_forks, "test analysis")
        
        assert result is True
        mock_confirm.assert_called_once()

    @pytest.mark.asyncio
    @patch('forklift.analysis.override_control.Confirm.ask')
    async def test_confirm_fork_analysis_user_declines(self, mock_confirm, mock_console, sample_forks):
        """Test fork analysis confirmation when user declines."""
        mock_confirm.return_value = False
        config = OverrideConfig(interactive_confirmations=True)
        confirmer = ExpensiveOperationConfirmer(mock_console, config)
        
        result = await confirmer.confirm_fork_analysis(sample_forks)
        
        assert result is False
        mock_confirm.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_ai_summary_disabled_confirmations(self, mock_console):
        """Test AI summary confirmation when confirmations are disabled."""
        config = OverrideConfig(interactive_confirmations=False)
        confirmer = ExpensiveOperationConfirmer(mock_console, config)
        
        result = await confirmer.confirm_ai_summary_generation(10, 0.05)
        
        assert result is True

    @pytest.mark.asyncio
    @patch('forklift.analysis.override_control.Confirm.ask')
    async def test_confirm_ai_summary_with_cost(self, mock_confirm, mock_console):
        """Test AI summary confirmation with cost information."""
        mock_confirm.return_value = True
        config = OverrideConfig(interactive_confirmations=True)
        confirmer = ExpensiveOperationConfirmer(mock_console, config)
        
        result = await confirmer.confirm_ai_summary_generation(25, 0.12)
        
        assert result is True
        mock_confirm.assert_called_once()

    @pytest.mark.asyncio
    @patch('forklift.analysis.override_control.Confirm.ask')
    async def test_confirm_detailed_analysis_no_commits_ahead(self, mock_confirm, mock_console):
        """Test detailed analysis confirmation for fork with no commits ahead."""
        mock_confirm.return_value = True
        config = OverrideConfig(interactive_confirmations=True)
        confirmer = ExpensiveOperationConfirmer(mock_console, config)
        
        result = await confirmer.confirm_detailed_analysis(
            "https://github.com/user/repo", has_commits_ahead=False
        )
        
        assert result is True
        mock_confirm.assert_called_once()

    @pytest.mark.asyncio
    @patch('forklift.analysis.override_control.Confirm.ask')
    async def test_confirm_detailed_analysis_has_commits_ahead(self, mock_confirm, mock_console):
        """Test detailed analysis confirmation for fork with commits ahead."""
        mock_confirm.return_value = True
        config = OverrideConfig(interactive_confirmations=True)
        confirmer = ExpensiveOperationConfirmer(mock_console, config)
        
        result = await confirmer.confirm_detailed_analysis(
            "https://github.com/user/repo", has_commits_ahead=True
        )
        
        assert result is True
        mock_confirm.assert_called_once()


class TestFilteringOverride:
    """Test FilteringOverride class."""

    def test_init(self):
        """Test filtering override initialization."""
        config = OverrideConfig()
        override = FilteringOverride(config)
        
        assert override.config == config

    def test_should_bypass_filtering_scan_all_enabled(self):
        """Test bypass filtering when scan_all is enabled."""
        config = OverrideConfig(scan_all=True)
        override = FilteringOverride(config)
        
        assert override.should_bypass_filtering() is True

    def test_should_bypass_filtering_scan_all_disabled(self):
        """Test bypass filtering when scan_all is disabled."""
        config = OverrideConfig(scan_all=False)
        override = FilteringOverride(config)
        
        assert override.should_bypass_filtering() is False

    def test_should_force_analysis_force_enabled(self):
        """Test force analysis when force is enabled."""
        config = OverrideConfig(force=True)
        override = FilteringOverride(config)
        
        assert override.should_force_analysis() is True

    def test_should_force_analysis_force_disabled(self):
        """Test force analysis when force is disabled."""
        config = OverrideConfig(force=False)
        override = FilteringOverride(config)
        
        assert override.should_force_analysis() is False

    def test_apply_scan_all_override_enabled(self, sample_forks):
        """Test applying scan_all override when enabled."""
        config = OverrideConfig(scan_all=True)
        override = FilteringOverride(config)
        
        # Mark some forks as inactive
        sample_forks[0].is_active = False
        sample_forks[1].is_active = False
        
        result = override.apply_scan_all_override(sample_forks)
        
        assert len(result) == 3
        # All forks should now be marked as active
        assert all(fork.is_active for fork in result)

    def test_apply_scan_all_override_disabled(self, sample_forks):
        """Test applying scan_all override when disabled."""
        config = OverrideConfig(scan_all=False)
        override = FilteringOverride(config)
        
        # Mark some forks as inactive
        sample_forks[0].is_active = False
        sample_forks[1].is_active = True
        
        result = override.apply_scan_all_override(sample_forks)
        
        assert len(result) == 3
        # Fork activity should remain unchanged
        assert result[0].is_active is False
        assert result[1].is_active is True

    def test_apply_force_override_enabled(self, sample_forks):
        """Test applying force override when enabled."""
        config = OverrideConfig(force=True)
        override = FilteringOverride(config)
        
        fork = sample_forks[0]
        
        # Should force analysis even when no commits ahead
        assert override.apply_force_override(fork, has_commits_ahead=False) is True
        assert override.apply_force_override(fork, has_commits_ahead=True) is True
        assert override.apply_force_override(fork, has_commits_ahead=None) is True

    def test_apply_force_override_disabled(self, sample_forks):
        """Test applying force override when disabled."""
        config = OverrideConfig(force=False)
        override = FilteringOverride(config)
        
        fork = sample_forks[0]
        
        # Should respect normal filtering logic
        assert override.apply_force_override(fork, has_commits_ahead=False) is False
        assert override.apply_force_override(fork, has_commits_ahead=True) is True
        assert override.apply_force_override(fork, has_commits_ahead=None) is True


class TestOverrideController:
    """Test OverrideController class."""

    def test_init_with_defaults(self, mock_console):
        """Test controller initialization with default components."""
        config = OverrideConfig()
        controller = OverrideController(mock_console, config)
        
        assert controller.console == mock_console
        assert controller.config == config
        assert isinstance(controller.confirmer, ExpensiveOperationConfirmer)
        assert isinstance(controller.filtering_override, FilteringOverride)

    def test_init_with_custom_components(self, mock_console):
        """Test controller initialization with custom components."""
        config = OverrideConfig()
        custom_confirmer = MagicMock()
        custom_override = MagicMock()
        
        controller = OverrideController(
            mock_console, config, custom_confirmer, custom_override
        )
        
        assert controller.confirmer == custom_confirmer
        assert controller.filtering_override == custom_override

    @pytest.mark.asyncio
    async def test_check_expensive_operation_approval_fork_analysis(self, mock_console, sample_forks):
        """Test expensive operation approval for fork analysis."""
        config = OverrideConfig(interactive_confirmations=False)
        controller = OverrideController(mock_console, config)
        
        result = await controller.check_expensive_operation_approval(
            "fork_analysis", forks=sample_forks, description="test analysis"
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_check_expensive_operation_approval_ai_summary(self, mock_console):
        """Test expensive operation approval for AI summary."""
        config = OverrideConfig(interactive_confirmations=False)
        controller = OverrideController(mock_console, config)
        
        result = await controller.check_expensive_operation_approval(
            "ai_summary", commit_count=10, estimated_cost=0.05
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_check_expensive_operation_approval_detailed_analysis(self, mock_console):
        """Test expensive operation approval for detailed analysis."""
        config = OverrideConfig(interactive_confirmations=False)
        controller = OverrideController(mock_console, config)
        
        result = await controller.check_expensive_operation_approval(
            "detailed_analysis", 
            fork_url="https://github.com/user/repo",
            has_commits_ahead=True
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_check_expensive_operation_approval_unknown_type(self, mock_console):
        """Test expensive operation approval for unknown operation type."""
        config = OverrideConfig()
        controller = OverrideController(mock_console, config)
        
        result = await controller.check_expensive_operation_approval("unknown_type")
        
        assert result is True

    def test_apply_filtering_overrides(self, mock_console, sample_forks):
        """Test applying filtering overrides."""
        config = OverrideConfig(scan_all=True)
        controller = OverrideController(mock_console, config)
        
        # Mark some forks as inactive
        sample_forks[0].is_active = False
        
        result = controller.apply_filtering_overrides(sample_forks)
        
        assert len(result) == 3
        assert all(fork.is_active for fork in result)

    def test_should_force_individual_analysis(self, mock_console, sample_forks):
        """Test individual fork analysis forcing."""
        config = OverrideConfig(force=True)
        controller = OverrideController(mock_console, config)
        
        fork = sample_forks[0]
        
        assert controller.should_force_individual_analysis(fork, False) is True
        assert controller.should_force_individual_analysis(fork, True) is True

    def test_log_override_status(self, mock_console):
        """Test logging override status."""
        config = OverrideConfig(scan_all=True, force=True)
        controller = OverrideController(mock_console, config)
        
        with patch('forklift.analysis.override_control.logger') as mock_logger:
            controller.log_override_status()
            mock_logger.info.assert_called_once()

    def test_display_override_summary_with_overrides(self, mock_console):
        """Test displaying override summary when overrides are active."""
        config = OverrideConfig(scan_all=True, force=True)
        controller = OverrideController(mock_console, config)
        
        # Should not raise any exceptions
        controller.display_override_summary()

    def test_display_override_summary_no_overrides(self, mock_console):
        """Test displaying override summary when no overrides are active."""
        config = OverrideConfig(scan_all=False, force=False)
        controller = OverrideController(mock_console, config)
        
        # Should not raise any exceptions
        controller.display_override_summary()


class TestCreateOverrideController:
    """Test create_override_controller function."""

    def test_create_with_defaults(self, mock_console):
        """Test creating controller with default settings."""
        controller = create_override_controller(mock_console)
        
        assert isinstance(controller, OverrideController)
        assert controller.console == mock_console
        assert controller.config.scan_all is False
        assert controller.config.force is False
        assert controller.config.interactive_confirmations is True

    def test_create_with_custom_settings(self, mock_console):
        """Test creating controller with custom settings."""
        controller = create_override_controller(
            mock_console,
            scan_all=True,
            force=True,
            interactive_confirmations=False,
        )
        
        assert isinstance(controller, OverrideController)
        assert controller.config.scan_all is True
        assert controller.config.force is True
        assert controller.config.interactive_confirmations is False


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple override mechanisms."""

    @pytest.mark.asyncio
    async def test_scan_all_with_confirmations_disabled(self, mock_console, sample_forks):
        """Test scan_all override with confirmations disabled."""
        config = OverrideConfig(scan_all=True, interactive_confirmations=False)
        controller = OverrideController(mock_console, config)
        
        # Mark some forks as inactive
        sample_forks[0].is_active = False
        sample_forks[1].is_active = False
        
        # Apply overrides
        filtered_forks = controller.apply_filtering_overrides(sample_forks)
        
        # Check expensive operation approval
        approval = await controller.check_expensive_operation_approval(
            "fork_analysis", forks=filtered_forks
        )
        
        assert len(filtered_forks) == 3
        assert all(fork.is_active for fork in filtered_forks)
        assert approval is True

    @pytest.mark.asyncio
    async def test_force_with_no_commits_ahead(self, mock_console, sample_forks):
        """Test force override for fork with no commits ahead."""
        config = OverrideConfig(force=True, interactive_confirmations=False)
        controller = OverrideController(mock_console, config)
        
        fork = sample_forks[0]
        
        # Should force analysis despite no commits ahead
        should_analyze = controller.should_force_individual_analysis(
            fork, has_commits_ahead=False
        )
        
        # Should approve detailed analysis
        approval = await controller.check_expensive_operation_approval(
            "detailed_analysis",
            fork_url=fork.repository.html_url,
            has_commits_ahead=False
        )
        
        assert should_analyze is True
        assert approval is True

    @pytest.mark.asyncio
    @patch('forklift.analysis.override_control.Confirm.ask')
    async def test_interactive_confirmations_with_user_input(
        self, mock_confirm, mock_console, sample_forks
    ):
        """Test interactive confirmations with user input."""
        mock_confirm.side_effect = [True, False, True]  # Different responses
        
        config = OverrideConfig(interactive_confirmations=True)
        controller = OverrideController(mock_console, config)
        
        # First confirmation should succeed
        approval1 = await controller.check_expensive_operation_approval(
            "fork_analysis", forks=sample_forks
        )
        
        # Second confirmation should fail
        approval2 = await controller.check_expensive_operation_approval(
            "ai_summary", commit_count=10
        )
        
        # Third confirmation should succeed
        approval3 = await controller.check_expensive_operation_approval(
            "detailed_analysis", fork_url="https://github.com/user/repo"
        )
        
        assert approval1 is True
        assert approval2 is False
        assert approval3 is True
        assert mock_confirm.call_count == 3

    def test_override_status_logging_and_display(self, mock_console):
        """Test override status logging and display functionality."""
        config = OverrideConfig(scan_all=True, force=True)
        controller = OverrideController(mock_console, config)
        
        with patch('forklift.analysis.override_control.logger') as mock_logger:
            controller.log_override_status()
            mock_logger.info.assert_called_once()
            
            # Verify log message contains expected information
            log_call = mock_logger.info.call_args[0][0]
            assert "scan_all=True" in log_call
            assert "force=True" in log_call

        # Display should not raise exceptions
        controller.display_override_summary()