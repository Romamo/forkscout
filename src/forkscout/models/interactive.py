"""Interactive analysis data models."""

from datetime import timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class UserChoice(str, Enum):
    """User choices for interactive confirmations."""

    CONTINUE = "continue"
    ABORT = "abort"


class StepResult(BaseModel):
    """Result of executing an interactive step."""

    model_config = {"arbitrary_types_allowed": True}

    step_name: str = Field(..., description="Name of the executed step")
    success: bool = Field(..., description="Whether the step completed successfully")
    data: Any = Field(..., description="Step result data")
    summary: str = Field(..., description="Human-readable summary of the step")
    error: Exception | None = Field(None, description="Error if step failed")
    metrics: dict[str, Any] | None = Field(None, description="Step-specific metrics")


class InteractiveAnalysisResult(BaseModel):
    """Result of an interactive analysis session."""

    completed_steps: list[StepResult] = Field(
        default_factory=list, description="List of completed steps"
    )
    final_result: Any | None = Field(None, description="Final analysis result")
    user_aborted: bool = Field(default=False, description="Whether user aborted the analysis")
    session_duration: timedelta = Field(..., description="Total session duration")
    total_confirmations: int = Field(default=0, description="Number of user confirmations")


class InteractiveConfig(BaseModel):
    """Configuration for interactive analysis mode."""

    enabled: bool = Field(default=False, description="Whether interactive mode is enabled")
    confirmation_timeout_seconds: int = Field(
        default=30, description="Auto-continue after timeout"
    )
    default_choice: str = Field(default="continue", description="Default choice: continue or abort")
    show_detailed_results: bool = Field(
        default=True, description="Whether to show detailed step results"
    )
    enable_step_rollback: bool = Field(
        default=True, description="Whether to enable step rollback"
    )
    save_session_state: bool = Field(
        default=True, description="Whether to save session state"
    )
    session_state_file: str = Field(
        default=".forkscout_session.json", description="Session state file path"
    )
