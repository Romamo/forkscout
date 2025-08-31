"""Data models for commits ahead detection system."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Optional


class CommitStatus(Enum):
    """Enumeration of possible commit status values."""
    
    HAS_COMMITS = "has_commits"
    NO_COMMITS = "no_commits"
    UNKNOWN = "unknown"
    VERIFIED_AHEAD = "verified_ahead"
    VERIFIED_NONE = "verified_none"


@dataclass
class ForkQualification:
    """Fork qualification data with commit status and confidence information."""
    
    fork_url: str
    owner: str
    name: str
    created_at: datetime
    pushed_at: datetime
    commit_status: CommitStatus
    confidence_score: float
    verification_method: str
    last_verified: Optional[datetime] = None
    commits_ahead_count: Optional[int] = None


@dataclass
class TimestampAnalysisResult:
    """Result of timestamp-based commit analysis."""
    
    created_at: datetime
    pushed_at: datetime
    status: CommitStatus
    confidence_score: float
    time_difference_days: int
    analysis_notes: str


@dataclass
class CommitDetectionResult:
    """Summary result of commit detection analysis."""
    
    total_forks: int
    has_commits: int
    no_commits: int
    unknown_status: int
    api_calls_saved: int
    processing_time: float
    confidence_distribution: Dict[str, int]