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
        self.console.print(f"\n[bold blue]EXECUTING - {step.name}[/bold blue]")
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
            title=f"RESULTS - {step_name} Results",
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
        
        self.console.print(f"\n[bold cyan]CONFIRM - {prompt}[/bold cyan]")
        
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
        
        self.console.print(f"\n[bold red]FAILED - Step '{step_name}' failed: {error_msg}[/bold red]")
        
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
            title="WELCOME - Forklift Interactive Mode",
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
        
        table = Table(title="METRICS - Step Metrics", show_header=True, header_style="bold magenta")
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
        """Create the final analysis result with comprehensive summary.
        
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
        
        # Display completion summary
        self._display_completion_summary(final_result, user_aborted, session_duration, error)
        
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
        """Save current session state to file with enhanced metadata."""
        if not self.config.save_session_state:
            return
            
        try:
            # Create enhanced session state with metadata
            state = {
                "version": "1.0",
                "created_at": datetime.utcnow().isoformat(),
                "session_id": id(self),  # Simple session identifier
                "session_start_time": self.session_start_time.isoformat() if self.session_start_time else None,
                "repo_url": self.context.get("repo_url"),
                "total_steps": len(self.steps),
                "completed_steps": [
                    {
                        "step_name": step.step_name,
                        "success": step.success,
                        "summary": step.summary,
                        "completed_at": datetime.utcnow().isoformat(),
                        "data": self._serialize_step_data(step.data),
                        "metrics": step.metrics
                    }
                    for step in self.completed_steps
                ],
                "context": {
                    k: v for k, v in self.context.items()
                    if isinstance(v, (str, int, float, bool, list, dict))
                },
                "confirmation_count": self.confirmation_count,
                "session_metrics": self.get_session_metrics()
            }
            
            session_file = Path(self.config.session_state_file)
            session_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Create backup of existing session if it exists
            if session_file.exists():
                backup_file = session_file.with_suffix('.json.backup')
                session_file.rename(backup_file)
            
            with open(session_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
                
            logger.info(f"Session state saved to {session_file}")
                
        except Exception as e:
            logger.warning(f"Failed to save session state: {e}")
    
    def _serialize_step_data(self, data: Any) -> Any:
        """Serialize step data for JSON storage."""
        if isinstance(data, (str, int, float, bool, list, dict, type(None))):
            return data
        elif hasattr(data, 'model_dump'):  # Pydantic models
            try:
                return data.model_dump()
            except Exception:
                return str(data)
        elif hasattr(data, '__dict__'):  # Objects with attributes
            try:
                return {k: v for k, v in data.__dict__.items() if isinstance(v, (str, int, float, bool, list, dict))}
            except Exception:
                return str(data)
        else:
            return str(data)
    
    async def _load_session_state(self) -> None:
        """Load session state from file if it exists with enhanced recovery."""
        if not self.config.save_session_state:
            return
            
        try:
            session_file = Path(self.config.session_state_file)
            if not session_file.exists():
                return
            
            with open(session_file, 'r') as f:
                state = json.load(f)
            
            # Validate session state version
            version = state.get("version", "unknown")
            if version != "1.0":
                logger.warning(f"Unknown session state version: {version}")
            
            # Check if session is recent (within 24 hours by default)
            created_at = state.get("created_at")
            if created_at:
                created_time = datetime.fromisoformat(created_at)
                age = datetime.utcnow() - created_time
                if age > timedelta(hours=24):
                    logger.info(f"Session state is {age} old, skipping restore")
                    return
            
            # Restore session data
            if state.get("session_start_time"):
                self.session_start_time = datetime.fromisoformat(state["session_start_time"])
            
            # Restore completed steps with enhanced data
            for step_data in state.get("completed_steps", []):
                step_result = StepResult(
                    step_name=step_data["step_name"],
                    success=step_data["success"],
                    data=step_data.get("data"),
                    summary=step_data["summary"],
                    metrics=step_data.get("metrics")
                )
                self.completed_steps.append(step_result)
            
            # Restore context
            self.context.update(state.get("context", {}))
            self.confirmation_count = state.get("confirmation_count", 0)
            
            # Display restoration summary
            repo_url = state.get("repo_url", "unknown repository")
            completed_count = len(self.completed_steps)
            total_count = state.get("total_steps", len(self.steps))
            
            restore_panel = Panel(
                f"RESTORED - **Session Restored**\n\n"
                f"Repository: {repo_url}\n"
                f"Progress: {completed_count}/{total_count} steps completed\n"
                f"Session age: {self._format_duration(age) if created_at else 'unknown'}\n\n"
                f"You can continue from where you left off!",
                title="SESSION - Previous Session Found",
                border_style="blue"
            )
            self.console.print(restore_panel)
            
        except Exception as e:
            logger.warning(f"Failed to load session state: {e}")
            # Try to load backup if main file is corrupted
            await self._try_load_backup_session()
    
    async def _try_load_backup_session(self) -> None:
        """Try to load session from backup file."""
        try:
            session_file = Path(self.config.session_state_file)
            backup_file = session_file.with_suffix('.json.backup')
            
            if backup_file.exists():
                logger.info("Attempting to restore from backup session file")
                backup_file.rename(session_file)
                await self._load_session_state()
        except Exception as e:
            logger.warning(f"Failed to restore from backup: {e}")
    
    async def _cleanup_session_state(self) -> None:
        """Clean up session state file on completion."""
        try:
            session_file = Path(self.config.session_state_file)
            if session_file.exists():
                session_file.unlink()
        except Exception as e:
            logger.warning(f"Failed to cleanup session state: {e}")
    
    def _display_completion_summary(
        self,
        final_result: Any,
        user_aborted: bool,
        session_duration: timedelta,
        error: Optional[Exception] = None
    ) -> None:
        """Display comprehensive completion summary.
        
        Args:
            final_result: Final analysis result data
            user_aborted: Whether user aborted the analysis
            session_duration: Total session duration
            error: Error that occurred (if any)
        """
        self.console.print("\n" + "="*80)
        
        if user_aborted:
            self._display_abort_summary(session_duration)
        elif error:
            self._display_error_summary(error, session_duration)
        else:
            self._display_success_summary(final_result, session_duration)
        
        self.console.print("="*80)
    
    def _display_success_summary(self, final_result: Any, session_duration: timedelta) -> None:
        """Display success completion summary."""
        summary_panel = Panel(
            self._format_success_summary(final_result, session_duration),
            title="COMPLETE - Interactive Analysis Complete",
            border_style="green",
            padding=(1, 2)
        )
        self.console.print(summary_panel)
    
    def _display_abort_summary(self, session_duration: timedelta) -> None:
        """Display abort completion summary."""
        summary_panel = Panel(
            self._format_abort_summary(session_duration),
            title="⏹️  Analysis Aborted",
            border_style="yellow",
            padding=(1, 2)
        )
        self.console.print(summary_panel)
    
    def _display_error_summary(self, error: Exception, session_duration: timedelta) -> None:
        """Display error completion summary."""
        summary_panel = Panel(
            self._format_error_summary(error, session_duration),
            title="FAILED - Analysis Failed",
            border_style="red",
            padding=(1, 2)
        )
        self.console.print(summary_panel)
    
    def _format_success_summary(self, final_result: Any, session_duration: timedelta) -> str:
        """Format success summary content."""
        summary_lines = [
            "SUCCESS - **Analysis completed successfully!**",
            "",
            "**Session Statistics:**"
        ]
        
        # Add session metrics
        summary_lines.extend([
            f"DURATION: {self._format_duration(session_duration)}",
            f"STEPS: {len(self.completed_steps)}/{len(self.steps)} completed",
            f"CONFIRMATIONS: {self.confirmation_count}",
            ""
        ])
        
        # Add step completion details
        summary_lines.append("**Step Results:**")
        for step_result in self.completed_steps:
            status_emoji = "✅" if step_result.success else "❌"
            summary_lines.append(f"{status_emoji} {step_result.step_name}: {step_result.summary}")
        
        # Add final results if available
        if final_result and isinstance(final_result, dict):
            summary_lines.append("")
            summary_lines.append("**Analysis Results:**")
            
            fork_analyses = final_result.get("fork_analyses", [])
            ranked_features = final_result.get("ranked_features", [])
            total_features = final_result.get("total_features", 0)
            
            if fork_analyses:
                summary_lines.append(f"🔍 Forks analyzed: {len(fork_analyses)}")
            
            if ranked_features:
                high_value = len([f for f in ranked_features if f.score >= 80])
                summary_lines.append(f"🎯 Features discovered: {total_features}")
                summary_lines.append(f"🏆 High-value features: {high_value}")
                
                if high_value > 0:
                    summary_lines.append("")
                    summary_lines.append("**Top Features:**")
                    for i, feature in enumerate(ranked_features[:3], 1):
                        if feature.score >= 80:
                            summary_lines.append(f"{i}. {feature.feature.title} (Score: {feature.score:.1f})")
        
        return "\n".join(summary_lines)
    
    def _format_abort_summary(self, session_duration: timedelta) -> str:
        """Format abort summary content."""
        summary_lines = [
            "⏹️  **Analysis was aborted by user**",
            "",
            "**Session Statistics:**",
            f"⏱️  Duration: {self._format_duration(session_duration)}",
            f"📋 Steps completed: {len(self.completed_steps)}/{len(self.steps)}",
            f"🤔 User confirmations: {self.confirmation_count}",
            ""
        ]
        
        if self.completed_steps:
            summary_lines.append("**Completed Steps:**")
            for step_result in self.completed_steps:
                status_emoji = "✅" if step_result.success else "❌"
                summary_lines.append(f"{status_emoji} {step_result.step_name}: {step_result.summary}")
            
            summary_lines.extend([
                "",
                "💡 **Note:** You can resume this analysis later if session state is enabled."
            ])
        else:
            summary_lines.append("No steps were completed before aborting.")
        
        return "\n".join(summary_lines)
    
    def _format_error_summary(self, error: Exception, session_duration: timedelta) -> str:
        """Format error summary content."""
        summary_lines = [
            "❌ **Analysis failed due to an error**",
            "",
            f"**Error:** {str(error)}",
            f"**Error Type:** {type(error).__name__}",
            "",
            "**Session Statistics:**",
            f"⏱️  Duration: {self._format_duration(session_duration)}",
            f"📋 Steps completed: {len(self.completed_steps)}/{len(self.steps)}",
            f"🤔 User confirmations: {self.confirmation_count}",
            ""
        ]
        
        if self.completed_steps:
            summary_lines.append("**Completed Steps Before Error:**")
            for step_result in self.completed_steps:
                status_emoji = "✅" if step_result.success else "❌"
                summary_lines.append(f"{status_emoji} {step_result.step_name}: {step_result.summary}")
        
        summary_lines.extend([
            "",
            "💡 **Troubleshooting:**",
            "- Check your GitHub token and network connection",
            "- Verify the repository URL is correct and accessible",
            "- Try running the analysis again with --verbose for more details"
        ])
        
        return "\n".join(summary_lines)
    
    def _format_duration(self, duration: timedelta) -> str:
        """Format duration in a human-readable way."""
        total_seconds = int(duration.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds} seconds"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    def get_session_metrics(self) -> Dict[str, Any]:
        """Get comprehensive session metrics.
        
        Returns:
            Dictionary containing session metrics
        """
        session_duration = timedelta(0)
        if self.session_start_time:
            session_duration = datetime.utcnow() - self.session_start_time
        
        successful_steps = [s for s in self.completed_steps if s.success]
        failed_steps = [s for s in self.completed_steps if not s.success]
        
        return {
            "session_start_time": self.session_start_time,
            "session_duration": session_duration,
            "total_steps": len(self.steps),
            "completed_steps": len(self.completed_steps),
            "successful_steps": len(successful_steps),
            "failed_steps": len(failed_steps),
            "completion_rate": len(self.completed_steps) / len(self.steps) if self.steps else 0,
            "success_rate": len(successful_steps) / len(self.completed_steps) if self.completed_steps else 0,
            "total_confirmations": self.confirmation_count,
            "avg_time_per_step": session_duration / len(self.completed_steps) if self.completed_steps else timedelta(0)
        }