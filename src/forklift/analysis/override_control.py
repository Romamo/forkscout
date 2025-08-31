"""Override and control mechanisms for bypassing filtering and confirmation prompts."""

import logging

from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from forklift.models.github import Fork

logger = logging.getLogger(__name__)


class OverrideConfig:
    """Configuration for override and control mechanisms."""

    def __init__(
        self,
        scan_all: bool = False,
        force: bool = False,
        interactive_confirmations: bool = True,
        confirmation_timeout: int = 30,
        default_choice_on_timeout: bool = False,
    ):
        """Initialize override configuration.
        
        Args:
            scan_all: Bypass all filtering logic and analyze every fork
            force: Force analysis even for forks with no commits ahead
            interactive_confirmations: Enable interactive confirmation prompts
            confirmation_timeout: Timeout in seconds for confirmation prompts
            default_choice_on_timeout: Default choice when timeout occurs
        """
        self.scan_all = scan_all
        self.force = force
        self.interactive_confirmations = interactive_confirmations
        self.confirmation_timeout = confirmation_timeout
        self.default_choice_on_timeout = default_choice_on_timeout


class ExpensiveOperationConfirmer:
    """Handles interactive confirmation prompts for expensive operations."""

    def __init__(self, console: Console, config: OverrideConfig):
        """Initialize the confirmer.
        
        Args:
            console: Rich console for output
            config: Override configuration
        """
        self.console = console
        self.config = config

    async def confirm_fork_analysis(
        self, forks: list[Fork], operation_description: str = "fork analysis"
    ) -> bool:
        """Confirm expensive fork analysis operation.
        
        Args:
            forks: List of forks to be analyzed
            operation_description: Description of the operation for user display
            
        Returns:
            True if user confirms, False otherwise
        """
        if not self.config.interactive_confirmations:
            return True

        # Calculate estimated cost
        estimated_api_calls = len(forks) * 5  # Rough estimate
        estimated_time_minutes = len(forks) * 0.5  # Rough estimate

        # Display operation details
        table = Table(title=f"Expensive Operation: {operation_description.title()}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("Forks to analyze", str(len(forks)))
        table.add_row("Estimated API calls", str(estimated_api_calls))
        table.add_row("Estimated time", f"{estimated_time_minutes:.1f} minutes")
        table.add_row("Rate limit impact", "Moderate to High")

        self.console.print(table)

        # Show sample of forks to be analyzed
        if len(forks) > 0:
            self.console.print("\n[bold]Sample forks to be analyzed:[/bold]")
            for i, fork in enumerate(forks[:5]):
                self.console.print(
                    f"  {i+1}. {fork.repository.full_name} "
                    f"({fork.repository.stars} stars, {fork.commits_ahead} commits ahead)"
                )
            if len(forks) > 5:
                self.console.print(f"  ... and {len(forks) - 5} more forks")

        # Ask for confirmation
        return Confirm.ask(
            f"\n[bold yellow]Proceed with {operation_description}?[/bold yellow]",
            default=self.config.default_choice_on_timeout,
        )

    async def confirm_ai_summary_generation(
        self, commit_count: int, estimated_cost: float = 0.0
    ) -> bool:
        """Confirm AI summary generation for commits.
        
        Args:
            commit_count: Number of commits to generate summaries for
            estimated_cost: Estimated cost in USD (if available)
            
        Returns:
            True if user confirms, False otherwise
        """
        if not self.config.interactive_confirmations:
            return True

        # Display cost information
        table = Table(title="AI Summary Generation")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("Commits to analyze", str(commit_count))
        if estimated_cost > 0:
            table.add_row("Estimated cost", f"${estimated_cost:.3f}")
        table.add_row("API provider", "OpenAI GPT-4 mini")
        table.add_row("Rate limit impact", "Low to Moderate")

        self.console.print(table)

        return Confirm.ask(
            "\n[bold yellow]Proceed with AI summary generation?[/bold yellow]",
            default=self.config.default_choice_on_timeout,
        )

    async def confirm_detailed_analysis(
        self, fork_url: str, has_commits_ahead: bool | None = None
    ) -> bool:
        """Confirm detailed analysis for a specific fork.
        
        Args:
            fork_url: URL of the fork to analyze
            has_commits_ahead: Whether the fork has commits ahead (if known)
            
        Returns:
            True if user confirms, False otherwise
        """
        if not self.config.interactive_confirmations:
            return True

        # Display fork information
        self.console.print("\n[bold]Detailed Analysis Request[/bold]")
        self.console.print(f"Fork: {fork_url}")

        if has_commits_ahead is not None:
            status = "has commits ahead" if has_commits_ahead else "no commits ahead"
            self.console.print(f"Status: {status}")

        if has_commits_ahead is False:
            self.console.print(
                "[yellow]Warning: This fork appears to have no commits ahead of upstream.[/yellow]"
            )
            self.console.print(
                "[dim]Detailed analysis may not provide valuable insights.[/dim]"
            )

        return Confirm.ask(
            "\n[bold yellow]Proceed with detailed analysis?[/bold yellow]",
            default=self.config.default_choice_on_timeout,
        )


class FilteringOverride:
    """Handles override mechanisms for filtering logic."""

    def __init__(self, config: OverrideConfig):
        """Initialize filtering override.
        
        Args:
            config: Override configuration
        """
        self.config = config

    def should_bypass_filtering(self) -> bool:
        """Check if all filtering should be bypassed.
        
        Returns:
            True if filtering should be bypassed
        """
        return self.config.scan_all

    def should_force_analysis(self, fork_url: str = None) -> bool:
        """Check if analysis should be forced for a specific fork.
        
        Args:
            fork_url: Optional fork URL for context
            
        Returns:
            True if analysis should be forced
        """
        return self.config.force

    def apply_scan_all_override(self, forks: list[Fork]) -> list[Fork]:
        """Apply scan-all override to fork list.
        
        Args:
            forks: Original list of forks
            
        Returns:
            All forks without filtering when scan_all is enabled
        """
        if self.config.scan_all:
            logger.info(
                f"Scan-all override: Bypassing all filtering, analyzing all {len(forks)} forks"
            )
            # Create a copy and mark all forks as active to bypass downstream filtering
            result_forks = []
            for fork in forks:
                # Create a copy of the fork with is_active set to True
                fork_copy = fork.model_copy()
                fork_copy.is_active = True
                result_forks.append(fork_copy)
            return result_forks
        return forks

    def apply_force_override(
        self, fork: Fork, has_commits_ahead: bool | None = None
    ) -> bool:
        """Apply force override for individual fork analysis.
        
        Args:
            fork: Fork to check
            has_commits_ahead: Whether fork has commits ahead (if known)
            
        Returns:
            True if analysis should proceed despite filtering
        """
        if self.config.force:
            logger.info(
                f"Force override: Analyzing fork {fork.repository.full_name} "
                f"despite filtering criteria"
            )
            return True

        # Normal filtering logic applies
        if has_commits_ahead is False:
            return False

        return True


class OverrideController:
    """Main controller for override and control mechanisms."""

    def __init__(
        self,
        console: Console,
        config: OverrideConfig,
        confirmer: ExpensiveOperationConfirmer | None = None,
        filtering_override: FilteringOverride | None = None,
    ):
        """Initialize override controller.
        
        Args:
            console: Rich console for output
            config: Override configuration
            confirmer: Optional custom confirmer (will create default if None)
            filtering_override: Optional custom filtering override (will create default if None)
        """
        self.console = console
        self.config = config
        self.confirmer = confirmer or ExpensiveOperationConfirmer(console, config)
        self.filtering_override = filtering_override or FilteringOverride(config)

    async def check_expensive_operation_approval(
        self, operation_type: str, **kwargs
    ) -> bool:
        """Check if an expensive operation should proceed.
        
        Args:
            operation_type: Type of operation ('fork_analysis', 'ai_summary', 'detailed_analysis')
            **kwargs: Operation-specific parameters
            
        Returns:
            True if operation should proceed
        """
        if operation_type == "fork_analysis":
            return await self.confirmer.confirm_fork_analysis(
                kwargs.get("forks", []), kwargs.get("description", "fork analysis")
            )
        elif operation_type == "ai_summary":
            return await self.confirmer.confirm_ai_summary_generation(
                kwargs.get("commit_count", 0), kwargs.get("estimated_cost", 0.0)
            )
        elif operation_type == "detailed_analysis":
            return await self.confirmer.confirm_detailed_analysis(
                kwargs.get("fork_url", ""), kwargs.get("has_commits_ahead")
            )
        else:
            logger.warning(f"Unknown operation type for confirmation: {operation_type}")
            return True

    def apply_filtering_overrides(self, forks: list[Fork]) -> list[Fork]:
        """Apply all filtering overrides to fork list.
        
        Args:
            forks: Original list of forks
            
        Returns:
            Filtered or unfiltered fork list based on overrides
        """
        return self.filtering_override.apply_scan_all_override(forks)

    def should_force_individual_analysis(
        self, fork: Fork, has_commits_ahead: bool | None = None
    ) -> bool:
        """Check if individual fork analysis should be forced.
        
        Args:
            fork: Fork to check
            has_commits_ahead: Whether fork has commits ahead
            
        Returns:
            True if analysis should be forced
        """
        return self.filtering_override.apply_force_override(fork, has_commits_ahead)

    def log_override_status(self) -> None:
        """Log current override configuration for debugging."""
        logger.info(
            f"Override configuration: scan_all={self.config.scan_all}, "
            f"force={self.config.force}, "
            f"interactive_confirmations={self.config.interactive_confirmations}"
        )

    def display_override_summary(self) -> None:
        """Display current override settings to user."""
        if self.config.scan_all or self.config.force:
            table = Table(title="Active Override Settings")
            table.add_column("Override", style="cyan")
            table.add_column("Status", style="yellow")
            table.add_column("Effect", style="green")

            if self.config.scan_all:
                table.add_row(
                    "--scan-all",
                    "ENABLED",
                    "All forks will be analyzed regardless of filtering criteria",
                )

            if self.config.force:
                table.add_row(
                    "--force",
                    "ENABLED",
                    "Individual fork analysis will proceed despite no commits ahead",
                )

            self.console.print(table)
            self.console.print(
                "[yellow]Note: Override settings may increase API usage and analysis time.[/yellow]\n"
            )


def create_override_controller(
    console: Console,
    scan_all: bool = False,
    force: bool = False,
    interactive_confirmations: bool = True,
) -> OverrideController:
    """Create an override controller with the specified settings.
    
    Args:
        console: Rich console for output
        scan_all: Enable scan-all override
        force: Enable force override
        interactive_confirmations: Enable interactive confirmations
        
    Returns:
        Configured OverrideController instance
    """
    config = OverrideConfig(
        scan_all=scan_all,
        force=force,
        interactive_confirmations=interactive_confirmations,
    )

    return OverrideController(console, config)
