"""Analysis-related data models."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from .github import Commit, Fork


class FeatureCategory(str, Enum):
    """Categories for features found in forks."""

    BUG_FIX = "bug_fix"
    NEW_FEATURE = "new_feature"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"
    REFACTOR = "refactor"
    TEST = "test"
    OTHER = "other"


class Feature(BaseModel):
    """Represents a feature or improvement found in a fork."""

    id: str = Field(..., description="Unique feature identifier")
    title: str = Field(..., description="Feature title")
    description: str = Field(..., description="Feature description")
    category: FeatureCategory = Field(..., description="Feature category")
    commits: list[Commit] = Field(default_factory=list, description="Related commits")
    files_affected: list[str] = Field(
        default_factory=list, description="Affected files"
    )
    source_fork: Fork = Field(..., description="Source fork")


class RankedFeature(BaseModel):
    """Represents a feature with ranking information."""

    feature: Feature = Field(..., description="The feature")
    score: float = Field(..., ge=0, le=100, description="Feature score (0-100)")
    ranking_factors: dict[str, float] = Field(
        default_factory=dict, description="Breakdown of ranking factors"
    )
    similar_implementations: list[Feature] = Field(
        default_factory=list, description="Similar features in other forks"
    )


class ForkMetrics(BaseModel):
    """Metrics for a fork repository."""

    stars: int = Field(default=0, description="Number of stars")
    forks: int = Field(default=0, description="Number of forks")
    contributors: int = Field(default=0, description="Number of contributors")
    last_activity: datetime | None = Field(None, description="Last activity")
    commit_frequency: float = Field(default=0.0, description="Commits per day")


class ForkAnalysis(BaseModel):
    """Complete analysis results for a fork."""

    fork: Fork = Field(..., description="The analyzed fork")
    features: list[Feature] = Field(
        default_factory=list, description="Discovered features"
    )
    metrics: ForkMetrics = Field(..., description="Fork metrics")
    analysis_date: datetime = Field(
        default_factory=datetime.utcnow, description="Analysis timestamp"
    )
