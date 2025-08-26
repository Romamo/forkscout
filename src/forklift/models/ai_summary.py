"""AI-powered commit summary data models."""

from datetime import datetime

from pydantic import BaseModel, Field


class AISummary(BaseModel):
    """AI-generated summary for a commit."""

    commit_sha: str = Field(..., description="SHA of the summarized commit")
    summary_text: str = Field(..., description="Complete AI-generated summary")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the summary was generated"
    )
    model_used: str = Field(default="gpt-4o-mini", description="AI model used for generation")
    tokens_used: int = Field(default=0, ge=0, description="Number of tokens consumed")
    processing_time_ms: float = Field(default=0.0, ge=0.0, description="Processing time in milliseconds")
    error: str | None = Field(None, description="Error message if summary generation failed")


class AISummaryConfig(BaseModel):
    """Configuration for AI summary generation."""

    enabled: bool = Field(default=False, description="Enable AI summary generation")
    model: str = Field(default="gpt-4o-mini", description="OpenAI model to use")
    max_tokens: int = Field(default=150, ge=1, le=4000, description="Maximum tokens per summary")
    max_diff_chars: int = Field(default=8000, ge=100, description="Maximum diff characters to include")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0, description="Model temperature for creativity")
    timeout_seconds: int = Field(default=30, ge=1, description="Request timeout in seconds")
    retry_attempts: int = Field(default=3, ge=0, description="Number of retry attempts on failure")
    cost_tracking: bool = Field(default=True, description="Enable cost tracking and reporting")
    batch_size: int = Field(default=5, ge=1, le=20, description="Number of commits to process in batches")
    compact_mode: bool = Field(default=False, description="Use compact summary style with minimal formatting")
    max_sentences: int = Field(default=5, ge=1, le=10, description="Maximum number of sentences in summary (was 3, increased to 5)")

    # Cost monitoring configuration
    max_cost_per_session_usd: float = Field(default=5.0, ge=0.0, description="Maximum cost per session in USD")
    max_cost_per_request_usd: float = Field(default=0.10, ge=0.0, description="Maximum cost per request in USD")
    cost_warning_threshold_usd: float = Field(default=1.0, ge=0.0, description="Cost threshold for warnings in USD")
    usage_logging_enabled: bool = Field(default=True, description="Enable detailed usage logging")
    performance_logging_enabled: bool = Field(default=True, description="Enable performance metrics logging")

    # Model pricing configuration (per 1K tokens)
    input_cost_per_1k_tokens: float = Field(default=0.00015, ge=0.0, description="Input cost per 1K tokens in USD")
    output_cost_per_1k_tokens: float = Field(default=0.0006, ge=0.0, description="Output cost per 1K tokens in USD")

    def calculate_input_cost(self, input_tokens: int) -> float:
        """Calculate cost for input tokens."""
        return (input_tokens / 1000.0) * self.input_cost_per_1k_tokens

    def calculate_output_cost(self, output_tokens: int) -> float:
        """Calculate cost for output tokens."""
        return (output_tokens / 1000.0) * self.output_cost_per_1k_tokens

    def calculate_total_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate total cost for input and output tokens."""
        return self.calculate_input_cost(input_tokens) + self.calculate_output_cost(output_tokens)

    def estimate_request_cost(self, prompt_text: str, max_output_tokens: int | None = None) -> float:
        """Estimate cost for a request based on prompt text."""
        # Rough token estimation (4 chars per token)
        estimated_input_tokens = len(prompt_text) // 4
        estimated_output_tokens = max_output_tokens or self.max_tokens

        return self.calculate_total_cost(estimated_input_tokens, estimated_output_tokens)


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
    ai_summary: AISummary | None = Field(None, description="AI-generated summary if available")


class AIUsageStats(BaseModel):
    """Statistics for AI API usage tracking."""

    total_requests: int = Field(default=0, ge=0, description="Total API requests made")
    successful_requests: int = Field(default=0, ge=0, description="Successful API requests")
    failed_requests: int = Field(default=0, ge=0, description="Failed API requests")
    total_tokens_used: int = Field(default=0, ge=0, description="Total tokens consumed")
    input_tokens_used: int = Field(default=0, ge=0, description="Input tokens consumed")
    output_tokens_used: int = Field(default=0, ge=0, description="Output tokens consumed")
    total_cost_usd: float = Field(default=0.0, ge=0.0, description="Estimated total cost in USD")
    input_cost_usd: float = Field(default=0.0, ge=0.0, description="Estimated input cost in USD")
    output_cost_usd: float = Field(default=0.0, ge=0.0, description="Estimated output cost in USD")
    average_processing_time_ms: float = Field(default=0.0, ge=0.0, description="Average processing time")
    min_processing_time_ms: float = Field(default=0.0, ge=0.0, description="Minimum processing time")
    max_processing_time_ms: float = Field(default=0.0, ge=0.0, description="Maximum processing time")
    session_start: datetime = Field(
        default_factory=datetime.utcnow, description="When the session started"
    )
    last_request: datetime | None = Field(None, description="Timestamp of last request")

    def get_success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100.0

    def get_average_tokens_per_request(self) -> float:
        """Calculate average tokens per successful request."""
        if self.successful_requests == 0:
            return 0.0
        return self.total_tokens_used / self.successful_requests

    def get_cost_per_request(self) -> float:
        """Calculate average cost per successful request."""
        if self.successful_requests == 0:
            return 0.0
        return self.total_cost_usd / self.successful_requests

    def get_session_duration_minutes(self) -> float:
        """Calculate session duration in minutes."""
        end_time = self.last_request or datetime.utcnow()
        duration = end_time - self.session_start
        return duration.total_seconds() / 60.0


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
    commit_sha: str | None = Field(None, description="SHA of commit that failed")
    retry_count: int = Field(default=0, ge=0, description="Number of retries attempted")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the error occurred"
    )
    recoverable: bool = Field(default=True, description="Whether the error is recoverable")


class AIUsageTracker(BaseModel):
    """Tracks AI API usage with cost monitoring and limits."""

    config: AISummaryConfig = Field(..., description="AI summary configuration")
    stats: AIUsageStats = Field(default_factory=AIUsageStats, description="Current usage statistics")

    def check_session_cost_limit(self) -> bool:
        """Check if session cost limit would be exceeded."""
        return self.stats.total_cost_usd < self.config.max_cost_per_session_usd

    def check_request_cost_limit(self, estimated_cost: float) -> bool:
        """Check if request cost limit would be exceeded."""
        return estimated_cost <= self.config.max_cost_per_request_usd

    def should_warn_about_cost(self) -> bool:
        """Check if cost warning threshold has been reached."""
        return self.stats.total_cost_usd >= self.config.cost_warning_threshold_usd

    def get_remaining_budget(self) -> float:
        """Get remaining budget for the session."""
        return max(0.0, self.config.max_cost_per_session_usd - self.stats.total_cost_usd)

    def record_request(
        self,
        success: bool,
        input_tokens: int = 0,
        output_tokens: int = 0,
        processing_time_ms: float = 0.0,
        error: str | None = None
    ) -> None:
        """Record a request in usage statistics."""
        self.stats.total_requests += 1
        self.stats.last_request = datetime.utcnow()

        if success:
            self.stats.successful_requests += 1
            self.stats.total_tokens_used += input_tokens + output_tokens
            self.stats.input_tokens_used += input_tokens
            self.stats.output_tokens_used += output_tokens

            # Calculate costs
            input_cost = self.config.calculate_input_cost(input_tokens)
            output_cost = self.config.calculate_output_cost(output_tokens)

            self.stats.input_cost_usd += input_cost
            self.stats.output_cost_usd += output_cost
            self.stats.total_cost_usd += input_cost + output_cost
        else:
            self.stats.failed_requests += 1

        # Update processing time statistics
        if processing_time_ms > 0:
            if self.stats.total_requests == 1:
                self.stats.min_processing_time_ms = processing_time_ms
                self.stats.max_processing_time_ms = processing_time_ms
                self.stats.average_processing_time_ms = processing_time_ms
            else:
                self.stats.min_processing_time_ms = min(self.stats.min_processing_time_ms, processing_time_ms)
                self.stats.max_processing_time_ms = max(self.stats.max_processing_time_ms, processing_time_ms)

                # Update average
                total_time = (
                    self.stats.average_processing_time_ms * (self.stats.total_requests - 1) +
                    processing_time_ms
                )
                self.stats.average_processing_time_ms = total_time / self.stats.total_requests

    def get_usage_report(self) -> dict:
        """Generate a comprehensive usage report."""
        return {
            "session_summary": {
                "duration_minutes": self.stats.get_session_duration_minutes(),
                "total_requests": self.stats.total_requests,
                "success_rate_percent": self.stats.get_success_rate(),
                "total_cost_usd": round(self.stats.total_cost_usd, 4),
                "remaining_budget_usd": round(self.get_remaining_budget(), 4),
            },
            "token_usage": {
                "total_tokens": self.stats.total_tokens_used,
                "input_tokens": self.stats.input_tokens_used,
                "output_tokens": self.stats.output_tokens_used,
                "average_tokens_per_request": round(self.stats.get_average_tokens_per_request(), 1),
            },
            "cost_breakdown": {
                "input_cost_usd": round(self.stats.input_cost_usd, 4),
                "output_cost_usd": round(self.stats.output_cost_usd, 4),
                "total_cost_usd": round(self.stats.total_cost_usd, 4),
                "cost_per_request_usd": round(self.stats.get_cost_per_request(), 4),
            },
            "performance": {
                "average_processing_time_ms": round(self.stats.average_processing_time_ms, 1),
                "min_processing_time_ms": round(self.stats.min_processing_time_ms, 1),
                "max_processing_time_ms": round(self.stats.max_processing_time_ms, 1),
            },
            "limits": {
                "max_cost_per_session_usd": self.config.max_cost_per_session_usd,
                "max_cost_per_request_usd": self.config.max_cost_per_request_usd,
                "cost_warning_threshold_usd": self.config.cost_warning_threshold_usd,
            }
        }
