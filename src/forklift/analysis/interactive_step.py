"""Base class for interactive analysis steps."""

from abc import ABC, abstractmethod
from typing import Any

from forklift.models.interactive import StepResult


class InteractiveStep(ABC):
    """Base class for interactive analysis steps."""

    def __init__(self, name: str, description: str):
        """Initialize the interactive step.
        
        Args:
            name: Step name
            description: Step description
        """
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> StepResult:
        """Execute the step with the given context.
        
        Args:
            context: Analysis context containing shared data
            
        Returns:
            StepResult with execution results
        """
        pass

    @abstractmethod
    def display_results(self, results: StepResult) -> str:
        """Display the step results in a formatted way.
        
        Args:
            results: Step execution results
            
        Returns:
            Formatted string for display
        """
        pass

    @abstractmethod
    def get_confirmation_prompt(self, results: StepResult) -> str:
        """Get the confirmation prompt for this step.
        
        Args:
            results: Step execution results
            
        Returns:
            Confirmation prompt string
        """
        pass

    def format_completion_summary(self, results: StepResult) -> str:
        """Format a completion summary for this step.
        
        Args:
            results: Step execution results
            
        Returns:
            Formatted completion summary
        """
        if results.success:
            return f"SUCCESS: {self.name}: {results.summary}"
        else:
            error_msg = str(results.error) if results.error else "Unknown error"
            return f"ERROR: {self.name}: Failed - {error_msg}"

    def get_metrics_display(self, results: StepResult) -> dict[str, Any]:
        """Get metrics for display.
        
        Args:
            results: Step execution results
            
        Returns:
            Dictionary of metrics for display
        """
        return results.metrics or {}
