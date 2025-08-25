"""Fork qualification data models for comprehensive fork data collection."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field

# mypy: disable-error-code=prop-decorator


class ForkQualificationMetrics(BaseModel):
    """Comprehensive metrics for fork qualification using GitHub API data."""

    # Basic repository information
    id: int = Field(..., description="GitHub repository ID")
    name: str = Field(..., description="Repository name")
    full_name: str = Field(..., description="Full repository name (owner/name)")
    owner: str = Field(..., description="Repository owner username")
    html_url: str = Field(..., description="Repository HTML URL")

    # Community engagement metrics
    stargazers_count: int = Field(default=0, ge=0, description="Number of stars")
    forks_count: int = Field(default=0, ge=0, description="Number of forks")
    watchers_count: int = Field(default=0, ge=0, description="Number of watchers")

    # Development activity metrics
    size: int = Field(default=0, ge=0, description="Repository size in KB")
    language: str | None = Field(None, description="Primary programming language")
    topics: list[str] = Field(default_factory=list, description="Repository topics")
    open_issues_count: int = Field(default=0, ge=0, description="Number of open issues")

    # Activity timeline metrics
    created_at: datetime = Field(..., description="Repository creation date")
    updated_at: datetime = Field(..., description="Last update date")
    pushed_at: datetime = Field(..., description="Last push date")

    # Repository status
    archived: bool = Field(default=False, description="Whether repository is archived")
    disabled: bool = Field(default=False, description="Whether repository is disabled")
    fork: bool = Field(default=True, description="Confirms this is a fork")

    # License information
    license_key: str | None = Field(
        None, description="License key (e.g., 'mit', 'apache-2.0')"
    )
    license_name: str | None = Field(None, description="License name")

    # Additional metadata
    description: str | None = Field(None, description="Repository description")
    homepage: str | None = Field(None, description="Repository homepage URL")
    default_branch: str = Field(default="main", description="Default branch name")

    @computed_field
    @property
    def days_since_creation(self) -> int:
        """Calculate days since repository creation."""
        return (datetime.utcnow() - self.created_at).days

    @computed_field
    @property
    def days_since_last_update(self) -> int:
        """Calculate days since last update."""
        return (datetime.utcnow() - self.updated_at).days

    @computed_field
    @property
    def days_since_last_push(self) -> int:
        """Calculate days since last push."""
        return (datetime.utcnow() - self.pushed_at).days

    @computed_field
    @property
    def commits_ahead_status(self) -> str:
        """Determine commits ahead status based on timestamps."""
        # If created_at >= pushed_at, likely no commits ahead
        if self.created_at >= self.pushed_at:
            return "No commits ahead"
        else:
            return "Has commits"

    @computed_field
    @property
    def can_skip_analysis(self) -> bool:
        """Determine if this fork can be skipped from detailed analysis."""
        return self.commits_ahead_status == "No commits ahead"

    @computed_field
    @property
    def activity_ratio(self) -> float:
        """Calculate activity ratio (days active / total days)."""
        total_days = self.days_since_creation
        if total_days == 0:
            return 1.0

        days_active = total_days - self.days_since_last_push
        return max(0.0, min(1.0, days_active / total_days))

    @computed_field
    @property
    def engagement_score(self) -> float:
        """Calculate engagement score based on stars, forks, and watchers."""
        # Weighted score with stars having highest weight
        score = (
            self.stargazers_count * 3 + self.forks_count * 2 + self.watchers_count
        ) / 6
        return min(100.0, score)  # Cap at 100

    @classmethod
    def from_github_api(cls, fork_data: dict[str, Any]) -> "ForkQualificationMetrics":
        """Create ForkQualificationMetrics from GitHub API fork list response."""
        license_info = fork_data.get("license")

        return cls(
            id=fork_data["id"],
            name=fork_data["name"],
            full_name=fork_data["full_name"],
            owner=fork_data["owner"]["login"],
            html_url=fork_data["html_url"],
            stargazers_count=fork_data.get("stargazers_count", 0),
            forks_count=fork_data.get("forks_count", 0),
            watchers_count=fork_data.get("watchers_count", 0),
            size=fork_data.get("size", 0),
            language=fork_data.get("language"),
            topics=fork_data.get("topics", []),
            open_issues_count=fork_data.get("open_issues_count", 0),
            created_at=datetime.fromisoformat(
                fork_data["created_at"].replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                fork_data["updated_at"].replace("Z", "+00:00")
            ),
            pushed_at=datetime.fromisoformat(
                fork_data["pushed_at"].replace("Z", "+00:00")
            ),
            archived=fork_data.get("archived", False),
            disabled=fork_data.get("disabled", False),
            fork=fork_data.get("fork", True),
            license_key=license_info.get("key") if license_info else None,
            license_name=license_info.get("name") if license_info else None,
            description=fork_data.get("description"),
            homepage=fork_data.get("homepage"),
            default_branch=fork_data.get("default_branch", "main"),
        )


class CollectedForkData(BaseModel):
    """Container for collected fork data with qualification metrics."""

    metrics: ForkQualificationMetrics = Field(
        ..., description="Fork qualification metrics"
    )
    collection_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When this data was collected"
    )

    @computed_field
    @property
    def activity_summary(self) -> str:
        """Generate human-readable activity summary."""
        days_since_push = self.metrics.days_since_last_push

        if days_since_push <= 7:
            return "Very Active (< 1 week)"
        elif days_since_push <= 30:
            return "Active (< 1 month)"
        elif days_since_push <= 90:
            return "Moderately Active (< 3 months)"
        elif days_since_push <= 365:
            return "Low Activity (< 1 year)"
        else:
            return "Inactive (> 1 year)"

    @computed_field
    @property
    def qualification_summary(self) -> str:
        """Generate qualification summary for display."""
        stars = self.metrics.stargazers_count
        commits_status = self.metrics.commits_ahead_status
        activity = self.activity_summary

        return f"{stars} stars, {commits_status}, {activity}"


class QualificationStats(BaseModel):
    """Summary statistics for fork qualification process."""

    total_forks_discovered: int = Field(
        default=0, ge=0, description="Total forks found"
    )
    forks_with_no_commits: int = Field(
        default=0, ge=0, description="Forks with no commits ahead"
    )
    forks_with_commits: int = Field(
        default=0, ge=0, description="Forks with potential commits"
    )
    archived_forks: int = Field(default=0, ge=0, description="Archived forks")
    disabled_forks: int = Field(default=0, ge=0, description="Disabled forks")

    # API efficiency metrics
    api_calls_made: int = Field(default=0, ge=0, description="Total API calls made")
    api_calls_saved: int = Field(
        default=0, ge=0, description="API calls saved by pre-filtering"
    )

    # Processing time
    processing_time_seconds: float = Field(
        default=0.0, ge=0.0, description="Total processing time"
    )

    # Data collection timestamp
    collection_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When qualification was performed"
    )

    @computed_field
    @property
    def efficiency_percentage(self) -> float:
        """Calculate API efficiency percentage."""
        total_potential_calls = self.api_calls_made + self.api_calls_saved
        if total_potential_calls == 0:
            return 0.0
        return (self.api_calls_saved / total_potential_calls) * 100

    @computed_field
    @property
    def skip_rate_percentage(self) -> float:
        """Calculate percentage of forks that can be skipped."""
        if self.total_forks_discovered == 0:
            return 0.0
        return (self.forks_with_no_commits / self.total_forks_discovered) * 100

    @computed_field
    @property
    def analysis_candidate_percentage(self) -> float:
        """Calculate percentage of forks that need detailed analysis."""
        if self.total_forks_discovered == 0:
            return 0.0
        return (self.forks_with_commits / self.total_forks_discovered) * 100


class QualifiedForksResult(BaseModel):
    """Complete result of fork qualification process."""

    # Repository information
    repository_owner: str = Field(..., description="Repository owner")
    repository_name: str = Field(..., description="Repository name")
    repository_url: str = Field(..., description="Repository URL")

    # Collected fork data
    collected_forks: list[CollectedForkData] = Field(
        default_factory=list, description="All collected fork data"
    )

    # Summary statistics
    stats: QualificationStats = Field(..., description="Qualification statistics")

    # Processing metadata
    qualification_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When qualification was completed"
    )

    @computed_field
    @property
    def forks_needing_analysis(self) -> list[CollectedForkData]:
        """Get forks that need detailed analysis."""
        return [
            fork_data
            for fork_data in self.collected_forks
            if not fork_data.metrics.can_skip_analysis
        ]

    @computed_field
    @property
    def forks_to_skip(self) -> list[CollectedForkData]:
        """Get forks that can be skipped from analysis."""
        return [
            fork_data
            for fork_data in self.collected_forks
            if fork_data.metrics.can_skip_analysis
        ]

    @computed_field
    @property
    def active_forks(self) -> list[CollectedForkData]:
        """Get forks with recent activity (pushed within last 90 days)."""
        return [
            fork_data
            for fork_data in self.collected_forks
            if fork_data.metrics.days_since_last_push <= 90
        ]

    @computed_field
    @property
    def popular_forks(self) -> list[CollectedForkData]:
        """Get forks with significant community engagement (5+ stars)."""
        return [
            fork_data
            for fork_data in self.collected_forks
            if fork_data.metrics.stargazers_count >= 5
        ]

    def get_forks_by_language(self, language: str) -> list[CollectedForkData]:
        """Get forks using a specific programming language."""
        return [
            fork_data
            for fork_data in self.collected_forks
            if fork_data.metrics.language == language
        ]

    def get_forks_with_topics(self, topics: list[str]) -> list[CollectedForkData]:
        """Get forks that have any of the specified topics."""
        return [
            fork_data
            for fork_data in self.collected_forks
            if any(topic in fork_data.metrics.topics for topic in topics)
        ]

    def get_summary_report(self) -> str:
        """Generate a human-readable summary report."""
        # Use stats for totals, computed fields for actual counts
        total = self.stats.total_forks_discovered
        need_analysis = len(self.forks_needing_analysis)
        can_skip = len(self.forks_to_skip)
        active = len(self.active_forks)
        popular = len(self.popular_forks)

        return f"""Fork Qualification Summary for {self.repository_owner}/{self.repository_name}:

Total Forks: {total}
Need Analysis: {need_analysis} ({self.stats.analysis_candidate_percentage:.1f}%)
Can Skip: {can_skip} ({self.stats.skip_rate_percentage:.1f}%)
Active (90 days): {active}
Popular (5+ stars): {popular}

API Efficiency: {self.stats.efficiency_percentage:.1f}% calls saved
Processing Time: {self.stats.processing_time_seconds:.2f} seconds
"""
