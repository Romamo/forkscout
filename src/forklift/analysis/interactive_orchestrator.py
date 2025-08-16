"""Interactive analysis orchestrator for step-by-step repository analysis."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from forklift.analysis.interactive_step import InteractiveStep
from forklift.github.client import GitHubClient
from forklift.models.interactive import (
    InteractiveAnalysisResult,
    InteractiveConfig,
    StepResult,
    UserChoice,
)

logger = logging.getLogger(__name__)


class InteractiveAnalysisOrchestrator:
    """Orchestrates step-by-step interactive analysis with user confirmations."""
    
    def __init__(
        self,
        github_client: GitHubClient,
        config: InteractiveConfig,
        console: Optional[Console] = None
    ):
        """Initialize the orchestrator.
        
        Args:
            github_client: GitHub API client
            config: Interactive configuration
            console: Rich console for output
        """
        self.github_client = github_client
        self.config = config
        self.console = console or Console()
        self.steps: List[InteractiveStep] = []
        self.context: Dict[str, Any] = {}
        self.session_start_time: Optional[datetime] = None
        self.completed_steps: List[StepResult] = []
        self.confirmation_count = 0
    
    def add_step(self, step: InteractiveStep) -> None:
        """Add a step to the analysis workflow.
        
        Args:
            step: Interactive step to add
        """
        self.steps.append(step)
    
    async def run_interactive_analysis(self, repo_url: str) -> InteractiveAnalysisResult:
        """Run the complete interactive analysis workflow.
        
        Args:
            repo_url: Repository URL to analyze
            
        Returns:
            InteractiveAnalysisResult with session results
        """
        self.session_start_time = datetime.utcnow()
        self.context["repo_url"] = repo_url
        
        try:
            # Load session state if enabled
            if self.config.save_session_state:
                await self._load_session_state()
            
            # Display welcome message
            self._display_welcome_message(repo_url)
            
            # Execute steps
            for i, step in enumerate(self.steps):
                # Check if step was already completed in a previous session
                if self._is_step_completed(step.name):
                    self.console.print(f"[yellow]⏭️  Skipping completed step: {step.name}[/yellow]")
                    continue
                
                # Execute the step
                step_result = await self.execute_step(step)
                self.completed_steps.append(step_result)
                
                # Save session state after each step
                if self.config.save_session_state:
                    await self._save_session_state()
                
                # If step failed, ask user what to do
                if not step_result.success:
                    choice = await self._handle_step_error(step.name, step_result.error)
                    if choice == UserChoice.ABORT:
                        return self._create_result(user_aborted=True)
                    # Continue to next step if user chooses to continue
                    continue
                
                # Display results and get user confirmation
                self.display_step_results(step.name, step_result)
                
                # Get user confirmation to continue (except for last step)
                if i < len(self.steps) - 1:
                    choice = await self.get_user_confirmation(step.name, step_result)
                    if choice == UserChoice.ABORT:
                        return self._create_result(user_aborted=True)
            
            # Analysis completed successfully
            final_result = self.context.get("final_result")
            return self._create_result(final_result=final_result)
            
        except Exception as e:
            logger.error(f"Interactive analysis failed: {e}")
            return self._create_result(user_aborted=True, error=e)
        finally:
            # Clean up session state on completion
            if self.config.save_session_state:
                await self._cleanup_session_state()
    
    async def execute_step(self, step: InteractiveStep) -> StepResult:
        """Execute a single step with error handling.
        
        Args:
            step: Step to execute
            
        Returns:
            StepResult with execution results
        """
        self.console.print(f"\n[bold blue]🔄 Executing: {step.name}[/bold blue]")
        self.console.print(f"[dim]{step.description}[/dim]")
        
        try:
            # Execute the step
            result = await step.execute(self.context)
            
            # Update context with step results
            self.context[f"step_{step.name.lower().replace(' ', '_')}_result"] = result.data
            
            return result
            
        except Exception as e:
            logger.error(f"Step '{step.name}' failed: {e}")
            return StepResult(
                step_name=step.name,
                success=False,
                data=None,
                summary=f"Step failed: {str(e)}",
                error=e
            )
    
    def display_step_results(self, step_name: str, results: StepResult) -> None:
        """Display step results in a formatted way.
        
        Args:
            step_name: Name of the step
            results: Step execution results
        """
        # Find the step to get its display method
        step = next((s for s in self.steps if s.name == step_name), None)
        if not step:
            return
        
        # Display results using step's display method
        display_content = step.display_results(results)
        
        # Create a panel with the results
        panel = Panel(
            display_content,
            title=f"📊 {step_name} Results",
            border_style="green" if results.success else "red"
        )
        self.console.print(panel)
        
        # Display metrics if available
        metrics = step.get_metrics_display(results)
        if metrics and self.config.show_detailed_results:
            self._display_metrics(metrics)
    
    async def get_user_confirmation(self, step_name: str, results: StepResult) -> UserChoice:
        """Get user confirmation to continue to the next step.
        
        Args:
            step_name: Name of the completed step
            results: Step execution results
            
        Returns:
            UserChoice indicating whether to continue or abort
        """
        # Find the step to get its confirmation prompt
        step = next((s for s in self.steps if s.name == step_name), None)
        if not step:
            prompt = f"Continue to the next step?"
        else:
            prompt = step.get_confirmation_prompt(results)
        
        self.console.print(f"\n[bold cyan]🤔 {prompt}[/bold cyan]")
        
        # Get user confirmation
        try:
            continue_analysis = Confirm.ask(
                "[cyan]Continue with the analysis?[/cyan]",
                default=self.config.default_choice == "continue"
            )
            
            self.confirmation_count += 1
            
            if continue_analysis:
                return UserChoice.CONTINUE
            else:
                self.console.print("[yellow]⏹️  Analysis aborted by user.[/yellow]")
                return UserChoice.ABORT
                
        except KeyboardInterrupt:
            self.console.print("\n[yellow]⏹️  Analysis interrupted by user.[/yellow]")
            return UserChoice.ABORT
    
    async def _handle_step_error(self, step_name: str, error: Optional[Exception]) -> UserChoice:
        """Handle step execution errors.
        
        Args:
            step_name: Name of the failed step
            error: Error that occurred
            
        Returns:
            UserChoice indicating whether to continue or abort
        """
        error_msg = str(error) if error else "Unknown error"
        
        self.console.print(f"\n[bold red]❌ Step '{step_name}' failed: {error_msg}[/bold red]")
        
        try:
            continue_anyway = Confirm.ask(
                "[yellow]Continue with the remaining steps anyway?[/yellow]",
                default=False
            )
            
            if continue_anyway:
                return UserChoice.CONTINUE
            else:
                return UserChoice.ABORT
                
        except KeyboardInterrupt:
            return UserChoice.ABORT
    
    def _display_welcome_message(self, repo_url: str) -> None:
        """Display welcome message for interactive analysis.
        
        Args:
            repo_url: Repository URL being analyzed
        """
        welcome_panel = Panel(
            f"[bold]Interactive Repository Analysis[/bold]\n\n"
            f"Repository: [cyan]{repo_url}[/cyan]\n"
            f"Steps: {len(self.steps)} analysis phases\n\n"
            f"[dim]You will be prompted to continue after each step completes.[/dim]",
            title="🚀 Welcome to Forklift Interactive Mode",
            border_style="blue"
        )
        self.console.print(welcome_panel)
    
    def _display_metrics(self, metrics: Dict[str, Any]) -> None:
        """Display metrics in a formatted table.
        
        Args:
            metrics: Metrics dictionary to display
        """
        if not metrics:
            return
        
        table = Table(title="📈 Step Metrics", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in metrics.items():
            table.add_row(key.replace("_", " ").title(), str(value))
        
        self.console.print(table)
    
    def _create_result(
        self,
        final_result: Any = None,
        user_aborted: bool = False,
        error: Optional[Exception] = None
    ) -> InteractiveAnalysisResult:
        """Create the final analysis result.
        
        Args:
            final_result: Final analysis result data
            user_aborted: Whether user aborted the analysis
            error: Error that occurred (if any)
            
        Returns:
            InteractiveAnalysisResult
        """
        session_duration = timedelta(0)
        if self.session_start_time:
            session_duration = datetime.utcnow() - self.session_start_time
        
        return InteractiveAnalysisResult(
            completed_steps=self.completed_steps,
            final_result=final_result,
            user_aborted=user_aborted,
            session_duration=session_duration,
            total_confirmations=self.confirmation_count
        )
    
    def _is_step_completed(self, step_name: str) -> bool:
        """Check if a step was already completed in a previous session.
        
        Args:
            step_name: Name of the step to check
            
        Returns:
            True if step was already completed
        """
        return any(step.step_name == step_name for step in self.completed_steps)
    
    async def _save_session_state(self) -> None:
        """Save current session state to file."""
        try:
            state = {
                "session_start_time": self.session_start_time.isoformat() if self.session_start_time else None,
                "completed_steps": [
                    {
                        "step_name": step.step_name,
                        "success": step.success,
                        "summary": step.summary,
                        "data": step.data if isinstance(step.data, (str, int, float, bool, list, dict)) else str(step.data)
                    }
                    for step in self.completed_steps
                ],
                "context": {
                    k: v for k, v in self.context.items()
                    if isinstance(v, (str, int, float, bool, list, dict))
                },
                "confirmation_count": self.confirmation_count
            }
            
            session_file = Path(self.config.session_state_file)
            with open(session_file, 'w') as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save session state: {e}")
    
    async def _load_session_state(self) -> None:
        """Load session state from file if it exists."""
        try:
            session_file = Path(self.config.session_state_file)
            if not session_file.exists():
                return
            
            with open(session_file, 'r') as f:
                state = json.load(f)
            
            # Restore session data
            if state.get("session_start_time"):
                self.session_start_time = datetime.fromisoformat(state["session_start_time"])
            
            # Restore completed steps
            for step_data in state.get("completed_steps", []):
                step_result = StepResult(
                    step_name=step_data["step_name"],
                    success=step_data["success"],
                    data=step_data["data"],
                    summary=step_data["summary"]
                )
                self.completed_steps.append(step_result)
            
            # Restore context
            self.context.update(state.get("context", {}))
            self.confirmation_count = state.get("confirmation_count", 0)
            
            self.console.print("[yellow]📂 Restored previous session state[/yellow]")
            
        except Exception as e:
            logger.warning(f"Failed to load session state: {e}")
    
    async def _cleanup_session_state(self) -> None:
        """Clean up session state file on completion."""
        try:
            session_file = Path(self.config.session_state_file)
            if session_file.exists():
                session_file.unlink()
        except Exception as e:
            logger.warning(f"Failed to cleanup session state: {e}")