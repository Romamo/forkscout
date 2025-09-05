"""Analysis-related data models."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from .github import Commit, Fork, Repository


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
    commit_explanations: list["CommitExplanation"] | None = Field(
        None, description="Commit explanations if generated"
    )
    explanation_summary: str | None = Field(
        None, description="Summary of explanation analysis"
    )


class ForkPreviewItem(BaseModel):
    """Lightweight fork preview item for fast display."""

    name: str = Field(..., description="Fork repository name")
    owner: str = Field(..., description="Fork owner username")
    stars: int = Field(default=0, description="Number of stars")
    forks_count: int = Field(default=0, description="Number of forks")
    last_push_date: datetime | None = Field(None, description="Last push date")
    fork_url: str = Field(..., description="Fork HTML URL")
    activity_status: str = Field(..., description="Activity status: Active, Stale, or No commits")
    commits_ahead: str = Field(..., description="Commits ahead status: None or Unknown")
    commits_behind: str = Field(default="Unknown", description="Commits behind status: None or Unknown")
    recent_commits: str | None = Field(None, description="Recent commit messages for CSV export")


class ForksPreview(BaseModel):
    """Lightweight preview of repository forks."""

    total_forks: int = Field(..., description="Total number of forks")
    forks: list[ForkPreviewItem] = Field(
        default_factory=list, description="Fork preview items"
    )


# Commit Explanation Models


class CategoryType(str, Enum):
    """Types of commit categories for explanation system."""

    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    DOCS = "docs"
    TEST = "test"
    CHORE = "chore"
    PERFORMANCE = "performance"
    SECURITY = "security"
    OTHER = "other"


class ImpactLevel(str, Enum):
    """Impact levels for commit assessment."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MainRepoValue(str, Enum):
    """Assessment of whether a commit could be valuable for the main repository."""

    YES = "yes"      # This change could be useful for the main repository
    NO = "no"        # This change is not relevant for the main repository
    UNCLEAR = "unclear"  # Cannot determine if this would be useful


class FileChange(BaseModel):
    """Represents a file change in a commit."""

    filename: str = Field(..., description="Name of the changed file")
    status: str = Field(..., description="Change status: added, modified, deleted, renamed")
    additions: int = Field(default=0, ge=0, description="Number of lines added")
    deletions: int = Field(default=0, ge=0, description="Number of lines deleted")
    patch: str | None = Field(None, description="Patch content if available")


class CommitCategory(BaseModel):
    """Category information for a commit."""

    category_type: CategoryType = Field(..., description="Primary category of the commit")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for categorization")
    reasoning: str = Field(..., description="Explanation of why this category was chosen")


class ImpactAssessment(BaseModel):
    """Impact assessment for a commit."""

    impact_level: ImpactLevel = Field(..., description="Assessed impact level")
    change_magnitude: float = Field(..., ge=0.0, description="Magnitude of changes (lines, files)")
    file_criticality: float = Field(..., ge=0.0, le=1.0, description="Criticality of affected files")
    quality_factors: dict[str, float] = Field(
        default_factory=dict, description="Quality factors (test coverage, documentation, etc.)"
    )
    reasoning: str = Field(..., description="Explanation of impact assessment")


class AnalysisContext(BaseModel):
    """Context information for commit analysis."""

    repository: Repository = Field(..., description="Repository being analyzed")
    fork: Fork | None = Field(None, description="Fork being analyzed (None for original repositories)")
    project_type: str | None = Field(None, description="Type of project (web, library, cli, etc.)")
    main_language: str | None = Field(None, description="Primary programming language")
    critical_files: list[str] = Field(
        default_factory=list, description="List of critical files in the project"
    )


class CommitExplanation(BaseModel):
    """Explanation for a single commit."""

    commit_sha: str = Field(..., description="SHA of the explained commit")
    category: CommitCategory = Field(..., description="Commit category information")
    impact_assessment: ImpactAssessment = Field(..., description="Impact assessment")
    what_changed: str = Field(..., description="Simple description of what the commit does")
    main_repo_value: MainRepoValue = Field(..., description="Assessment of value for main repository")
    explanation: str = Field(..., description="1-2 sentence human-readable explanation")
    is_complex: bool = Field(default=False, description="True if commit does multiple things")
    github_url: str = Field(..., description="Direct GitHub URL to the commit")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the explanation was generated"
    )


class FormattedExplanation(BaseModel):
    """Formatted explanation with separated description and evaluation."""

    commit_sha: str = Field(..., description="SHA of the explained commit")
    github_url: str = Field(..., description="Direct GitHub URL to the commit")
    category_display: str = Field(..., description="Category with icon/color formatting")
    description: str = Field(..., description="Factual 'what changed' description")
    evaluation: str = Field(..., description="System assessment/verdict")
    impact_indicator: str = Field(..., description="Visual impact level indicator")
    is_complex: bool = Field(default=False, description="True if commit does multiple things")


class CommitWithExplanation(BaseModel):
    """A commit paired with its optional explanation."""

    commit: Commit = Field(..., description="The commit")
    explanation: CommitExplanation | None = Field(None, description="Generated explanation")
    explanation_error: str | None = Field(None, description="Error message if explanation failed")
