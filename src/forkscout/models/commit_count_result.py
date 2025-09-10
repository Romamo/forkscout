"""Commit count result models for GitHub API operations."""

from dataclasses import dataclass


@dataclass
class CommitCountResult:
    """Result of commit count operation including both ahead and behind."""
    
    ahead_count: int
    behind_count: int
    is_limited: bool = False
    error: str | None = None
    
    @property
    def has_ahead_commits(self) -> bool:
        """True if fork has commits ahead of parent."""
        return self.ahead_count > 0
    
    @property
    def has_behind_commits(self) -> bool:
        """True if fork has commits behind parent."""
        return self.behind_count > 0
    
    @property
    def is_diverged(self) -> bool:
        """True if fork has both ahead and behind commits."""
        return self.ahead_count > 0 and self.behind_count > 0


@dataclass
class BatchCommitCountResult:
    """Result of batch commit count operation."""
    
    results: dict[str, CommitCountResult]
    total_api_calls: int
    parent_calls_saved: int