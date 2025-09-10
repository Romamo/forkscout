"""Fork filtering configuration models."""

from pydantic import BaseModel, Field


class ForkFilteringConfig(BaseModel):
    """Configuration for fork filtering behavior."""

    enabled: bool = Field(
        default=True,
        description="Enable automatic fork filtering based on commit status",
    )

    log_filtering_decisions: bool = Field(
        default=True,
        description="Log detailed filtering decisions with fork names and reasons",
    )

    log_statistics: bool = Field(
        default=True, description="Log statistics about filtered vs analyzed forks"
    )

    fallback_to_api: bool = Field(
        default=True,
        description="Use GitHub API fallback when qualification data is unavailable",
    )

    prefer_inclusion_on_uncertainty: bool = Field(
        default=True,
        description="Include forks when commit status cannot be determined",
    )

    cache_status_results: bool = Field(
        default=True, description="Cache fork commit status results for performance"
    )

    status_cache_ttl_hours: int = Field(
        default=24,
        ge=1,
        description="Time-to-live for cached fork status results in hours",
    )

    max_api_fallback_calls: int = Field(
        default=50,
        ge=0,
        description="Maximum number of GitHub API fallback calls per session (0 = unlimited)",
    )

    skip_archived_forks: bool = Field(
        default=True,
        description="Automatically skip archived forks from detailed analysis",
    )

    skip_disabled_forks: bool = Field(
        default=True,
        description="Automatically skip disabled forks from detailed analysis",
    )


class ForkFilteringStats(BaseModel):
    """Statistics for fork filtering operations."""

    total_forks_evaluated: int = Field(
        default=0, description="Total forks evaluated for filtering"
    )
    forks_filtered_out: int = Field(
        default=0, description="Number of forks filtered out"
    )
    forks_included: int = Field(
        default=0, description="Number of forks included for analysis"
    )
    qualification_data_hits: int = Field(
        default=0, description="Successful qualification data lookups"
    )
    api_fallback_calls: int = Field(
        default=0, description="GitHub API fallback calls made"
    )
    status_unknown: int = Field(
        default=0, description="Forks with unknown commit status"
    )
    errors: int = Field(default=0, description="Errors encountered during filtering")

    # Breakdown by filtering reason
    filtered_no_commits_ahead: int = Field(
        default=0, description="Filtered due to no commits ahead"
    )
    filtered_archived: int = Field(
        default=0, description="Filtered due to archived status"
    )
    filtered_disabled: int = Field(
        default=0, description="Filtered due to disabled status"
    )

    @property
    def filtering_rate(self) -> float:
        """Calculate the percentage of forks that were filtered out."""
        if self.total_forks_evaluated == 0:
            return 0.0
        return (self.forks_filtered_out / self.total_forks_evaluated) * 100

    @property
    def api_usage_efficiency(self) -> float:
        """Calculate the efficiency of API usage (qualification hits vs API calls)."""
        total_lookups = self.qualification_data_hits + self.api_fallback_calls
        if total_lookups == 0:
            return 100.0
        return (self.qualification_data_hits / total_lookups) * 100

    def reset(self) -> None:
        """Reset all statistics to zero."""
        self.total_forks_evaluated = 0
        self.forks_filtered_out = 0
        self.forks_included = 0
        self.qualification_data_hits = 0
        self.api_fallback_calls = 0
        self.status_unknown = 0
        self.errors = 0
        self.filtered_no_commits_ahead = 0
        self.filtered_archived = 0
        self.filtered_disabled = 0

    def add_fork_evaluated(self, filtered: bool, reason: str | None = None) -> None:
        """Add a fork evaluation result to statistics."""
        self.total_forks_evaluated += 1

        if filtered:
            self.forks_filtered_out += 1

            # Track filtering reasons
            if reason == "no_commits_ahead":
                self.filtered_no_commits_ahead += 1
            elif reason == "archived":
                self.filtered_archived += 1
            elif reason == "disabled":
                self.filtered_disabled += 1
        else:
            self.forks_included += 1

    def add_qualification_hit(self) -> None:
        """Record a successful qualification data lookup."""
        self.qualification_data_hits += 1

    def add_api_fallback(self) -> None:
        """Record a GitHub API fallback call."""
        self.api_fallback_calls += 1

    def add_status_unknown(self) -> None:
        """Record a fork with unknown commit status."""
        self.status_unknown += 1

    def add_error(self) -> None:
        """Record an error during filtering."""
        self.errors += 1

    def to_summary_dict(self) -> dict[str, any]:
        """Convert statistics to a summary dictionary for logging."""
        return {
            "total_evaluated": self.total_forks_evaluated,
            "filtered_out": self.forks_filtered_out,
            "included": self.forks_included,
            "filtering_rate_percent": round(self.filtering_rate, 1),
            "api_efficiency_percent": round(self.api_usage_efficiency, 1),
            "qualification_hits": self.qualification_data_hits,
            "api_fallbacks": self.api_fallback_calls,
            "status_unknown": self.status_unknown,
            "errors": self.errors,
            "filtered_reasons": {
                "no_commits_ahead": self.filtered_no_commits_ahead,
                "archived": self.filtered_archived,
                "disabled": self.filtered_disabled,
            },
        }
