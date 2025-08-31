"""Ahead-only filtering models and logic for fork analysis."""

from dataclasses import dataclass
from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from .github import Repository


@dataclass
class FilteredForkResult:
    """Result of ahead-only filtering operation."""
    
    forks: List[Repository]
    total_processed: int
    excluded_private: int
    excluded_no_commits: int
    
    @property
    def included_count(self) -> int:
        """Number of forks included after filtering."""
        return len(self.forks)
    
    @property
    def total_excluded(self) -> int:
        """Total number of forks excluded."""
        return self.excluded_private + self.excluded_no_commits
    
    @property
    def exclusion_summary(self) -> str:
        """Human-readable summary of filtering results."""
        return (
            f"Filtered {self.total_processed} forks: "
            f"{self.included_count} included, "
            f"{self.excluded_private} private excluded, "
            f"{self.excluded_no_commits} no commits excluded"
        )


class AheadOnlyConfig(BaseModel):
    """Configuration for ahead-only filtering."""
    
    enabled: bool = Field(default=False, description="Enable ahead-only filtering")
    include_uncertain: bool = Field(
        default=True, 
        description="Include forks with unknown commit status"
    )
    conservative_filtering: bool = Field(
        default=False, 
        description="Use more aggressive filtering for uncertain cases"
    )
    exclude_private: bool = Field(
        default=True, 
        description="Exclude private forks from results"
    )


class AheadOnlyFilter:
    """Filter forks to show only those with commits ahead and exclude private forks."""
    
    def __init__(self, config: AheadOnlyConfig | None = None):
        """Initialize the filter with optional configuration.
        
        Args:
            config: Configuration for filtering behavior. Uses defaults if None.
        """
        self.config = config or AheadOnlyConfig()
    
    def filter_forks(self, forks: List[Repository]) -> FilteredForkResult:
        """Apply ahead-only filtering to fork list.
        
        Args:
            forks: List of fork repositories to filter
            
        Returns:
            FilteredForkResult with included forks and exclusion statistics
        """
        included_forks = []
        excluded_private = 0
        excluded_no_commits = 0
        
        for fork in forks:
            # Always exclude private forks if configured to do so
            if self.config.exclude_private and fork.is_private:
                excluded_private += 1
                continue
            
            # Check commits ahead status
            if self._has_commits_ahead(fork):
                included_forks.append(fork)
            else:
                excluded_no_commits += 1
        
        return FilteredForkResult(
            forks=included_forks,
            total_processed=len(forks),
            excluded_private=excluded_private,
            excluded_no_commits=excluded_no_commits
        )
    
    def _has_commits_ahead(self, fork: Repository) -> bool:
        """Determine if fork has commits ahead using timestamp comparison.
        
        Args:
            fork: Repository to check for commits ahead
            
        Returns:
            True if fork likely has commits ahead, False otherwise
        """
        # If we don't have timestamp data, handle based on configuration
        if not fork.created_at or not fork.pushed_at:
            return self.config.include_uncertain
        
        # Use created_at < pushed_at to identify forks with commits ahead
        # This indicates the fork was pushed to after creation, suggesting new commits
        return fork.pushed_at > fork.created_at
    
    def get_filtering_stats(self, result: FilteredForkResult) -> dict:
        """Get detailed filtering statistics.
        
        Args:
            result: Result from filter_forks operation
            
        Returns:
            Dictionary with detailed filtering statistics
        """
        return {
            "total_forks": result.total_processed,
            "included_forks": result.included_count,
            "excluded_forks": result.total_excluded,
            "excluded_private": result.excluded_private,
            "excluded_no_commits": result.excluded_no_commits,
            "inclusion_rate": result.included_count / result.total_processed if result.total_processed > 0 else 0.0,
            "private_exclusion_rate": result.excluded_private / result.total_processed if result.total_processed > 0 else 0.0,
            "no_commits_exclusion_rate": result.excluded_no_commits / result.total_processed if result.total_processed > 0 else 0.0
        }


def create_default_ahead_only_filter() -> AheadOnlyFilter:
    """Create an AheadOnlyFilter with default configuration.
    
    Returns:
        AheadOnlyFilter configured with sensible defaults
    """
    config = AheadOnlyConfig(
        enabled=True,
        include_uncertain=True,
        conservative_filtering=False,
        exclude_private=True
    )
    return AheadOnlyFilter(config)