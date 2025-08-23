"""AI-powered commit summary data models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AISummary(BaseModel):
    """AI-generated summary for a commit."""

    commit_sha: str = Field(..., description="SHA of the summarized commit")
    summary_text: str = Field(..., description="Complete AI-generated summary")
    what_changed: str = Field(..., description="Description of what changed in the commit")
    why_changed: str = Field(..., description="Explanation of why the change was made")
    potential_side_effects: str = Field(..., description="Potential side effects or considerations")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the summary was generated"
    )
    model_used: str = Field(default="gpt-4o-mini", description="AI model used for generation")
    tokens_used: int = Field(default=0, ge=0, description="Number of tokens consumed")
    processing_time_ms: float = Field(default=0.0, ge=0.0, description="Processing time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if summary generation failed")


class AISummaryConfig(BaseModel):
    """Configuration for AI summary generation."""

    enabled: bool = Field(default=False, description="Enable AI summary generation")
    model: str = Field(default="gpt-4o-mini", description="OpenAI model to use")
    max_tokens: int = Field(default=500, ge=1, le=4000, description="Maximum tokens per summary")
    max_diff_chars: int = Field(default=8000, ge=100, description="Maximum diff characters to include")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0, description="Model temperature for creativity")
    timeout_seconds: int = Field(default=30, ge=1, description="Request timeout in seconds")
    retry_attempts: int = Field(default=3, ge=0, description="Number of retry attempts on failure")
    cost_tracking: bool = Field(default=True, description="Enable cost tracking and reporting")
    batch_size: int = Field(default=5, ge=1, le=20, description="Number of commits to process in batches")


class CommitDetails(BaseModel):
    """Detailed information about a commit including optional AI summary."""

    commit_sha: str = Field(..., description="SHA of the commit")
    message: str = Field(..., description="Commit message")
    author: str = Field(..., description="Commit author")
    date: datetime = Field(..., description="Commit date")
    files_changed_count: int = Field(default=0, ge=0, description="Number of files changed")
    lines_added: int = Field(default=0, ge=0, description="Number of lines added")
    lines_removed: int = Field(default=0, ge=0, description="Number of lines removed")
    commit_url: str = Field(..., description="GitHub URL to the commit")
    ai_summary: Optional[AISummary] = Field(None, description="AI-generated summary if available")


class AIUsageStats(BaseModel):
    """Statistics for AI API usage tracking."""

    total_requests: int = Field(default=0, ge=0, description="Total API requests made")
    successful_requests: int = Field(default=0, ge=0, description="Successful API requests")
    failed_requests: int = Field(default=0, ge=0, description="Failed API requests")
    total_tokens_used: int = Field(default=0, ge=0, description="Total tokens consumed")
    total_cost_usd: float = Field(default=0.0, ge=0.0, description="Estimated total cost in USD")
    average_processing_time_ms: float = Field(default=0.0, ge=0.0, description="Average processing time")
    session_start: datetime = Field(
        default_factory=datetime.utcnow, description="When the session started"
    )
    last_request: Optional[datetime] = Field(None, description="Timestamp of last request")


class AIErrorType(str):
    """Types of AI API errors."""

    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    INVALID_REQUEST = "invalid_request"
    MODEL_ERROR = "model_error"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


class AIError(BaseModel):
    """AI API error information."""

    error_type: str = Field(..., description="Type of error that occurred")
    message: str = Field(..., description="Error message")
    commit_sha: Optional[str] = Field(None, description="SHA of commit that failed")
    retry_count: int = Field(default=0, ge=0, description="Number of retries attempted")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the error occurred"
    )
    recoverable: bool = Field(default=True, description="Whether the error is recoverable")