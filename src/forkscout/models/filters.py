"""Filter models for fork analysis."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PromisingForksFilter(BaseModel):
    """Filter criteria for identifying promising forks."""

    min_stars: int = Field(default=0, ge=0, description="Minimum star count")
    min_commits_ahead: int = Field(default=1, ge=0, description="Minimum commits ahead of upstream")
    max_days_since_activity: int = Field(default=365, ge=1, description="Maximum days since last activity")
    min_activity_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum activity score")
    exclude_archived: bool = Field(default=True, description="Exclude archived repositories")
    exclude_disabled: bool = Field(default=True, description="Exclude disabled repositories")
    min_fork_age_days: int = Field(default=0, ge=0, description="Minimum fork age in days")
    max_fork_age_days: int | None = Field(default=None, ge=1, description="Maximum fork age in days")

    @field_validator("max_fork_age_days")
    @classmethod
    def validate_max_fork_age(cls, v: int | None, info) -> int | None:
        """Validate max_fork_age_days is greater than min_fork_age_days."""
        if v is not None and "min_fork_age_days" in info.data:
            min_age = info.data["min_fork_age_days"]
            if v <= min_age:
                raise ValueError("max_fork_age_days must be greater than min_fork_age_days")
        return v

    def matches_fork(self, fork_data: dict) -> bool:
        """Check if a fork matches the filter criteria.
        
        Args:
            fork_data: Enhanced fork data dictionary with fork, commits_ahead, etc.
            
        Returns:
            True if fork matches all criteria, False otherwise
        """
        fork = fork_data["fork"]
        commits_ahead = fork_data.get("commits_ahead", 0)
        activity_status = fork_data.get("activity_status", "unknown")
        last_activity = fork_data.get("last_activity")

        # Check star count
        if fork.stars < self.min_stars:
            return False

        # Check commits ahead
        if commits_ahead < self.min_commits_ahead:
            return False

        # Check archived status
        if self.exclude_archived and fork.is_archived:
            return False

        # Check disabled status
        if self.exclude_disabled and fork.is_disabled:
            return False

        # Check activity recency
        if fork.pushed_at:
            days_since_activity = (datetime.utcnow() - fork.pushed_at.replace(tzinfo=None)).days
            if days_since_activity > self.max_days_since_activity:
                return False

        # Check fork age
        if fork.created_at:
            fork_age_days = (datetime.utcnow() - fork.created_at.replace(tzinfo=None)).days
            if fork_age_days < self.min_fork_age_days:
                return False
            if self.max_fork_age_days is not None and fork_age_days > self.max_fork_age_days:
                return False

        # Check activity score
        activity_score = self._calculate_activity_score(activity_status, fork.pushed_at)
        if activity_score < self.min_activity_score:
            return False

        return True

    def _calculate_activity_score(self, activity_status: str, pushed_at: datetime | None) -> float:
        """Calculate activity score for a fork.
        
        Args:
            activity_status: Activity status string
            pushed_at: Last push timestamp
            
        Returns:
            Activity score between 0.0 and 1.0
        """
        if not pushed_at:
            return 0.0

        days_since_activity = (datetime.utcnow() - pushed_at.replace(tzinfo=None)).days

        # Score decreases exponentially with time
        if days_since_activity <= 7:
            return 1.0
        elif days_since_activity <= 30:
            return 0.8
        elif days_since_activity <= 90:
            return 0.5
        elif days_since_activity <= 365:
            return 0.2
        else:
            return 0.1


class ForkDetailsFilter(BaseModel):
    """Filter criteria for fork details display."""

    include_branches: bool = Field(default=True, description="Include branch information")
    include_contributors: bool = Field(default=True, description="Include contributor information")
    include_commit_stats: bool = Field(default=True, description="Include commit statistics")
    max_branches: int = Field(default=10, ge=1, description="Maximum branches to display")
    max_contributors: int = Field(default=10, ge=1, description="Maximum contributors to display")


class BranchInfo(BaseModel):
    """Information about a repository branch."""

    name: str = Field(..., description="Branch name")
    commit_count: int = Field(default=0, ge=0, description="Number of commits in branch")
    last_commit_date: datetime | None = Field(None, description="Last commit date")
    commits_ahead_of_main: int = Field(default=0, ge=0, description="Commits ahead of main branch")
    is_default: bool = Field(default=False, description="Whether this is the default branch")
    is_protected: bool = Field(default=False, description="Whether branch is protected")


class ForkDetails(BaseModel):
    """Detailed information about a fork."""

    fork: Any = Field(..., description="Fork repository")  # Will be Repository type
    branches: list[BranchInfo] = Field(default_factory=list, description="Branch information")
    total_commits: int = Field(default=0, ge=0, description="Total commits across all branches")
    contributors: list[str] = Field(default_factory=list, description="Contributor usernames")
    contributor_count: int = Field(default=0, ge=0, description="Total number of contributors")
    languages: dict[str, int] = Field(default_factory=dict, description="Programming languages")
    topics: list[str] = Field(default_factory=list, description="Repository topics")
