"""GitHub-related data models."""

import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator


class Repository(BaseModel):
    """Represents a GitHub repository."""

    id: int | None = Field(None, description="GitHub repository ID")
    owner: str = Field(..., min_length=1, max_length=39, description="Repository owner")
    name: str = Field(..., min_length=1, max_length=100, description="Repository name")
    full_name: str = Field(..., description="Full repository name (owner/name)")
    url: str = Field(..., description="Repository URL")
    html_url: str = Field(..., description="Repository HTML URL")
    clone_url: str = Field(..., description="Repository clone URL")
    default_branch: str = Field(default="main", description="Default branch name")
    stars: int = Field(default=0, ge=0, description="Number of stars")
    forks_count: int = Field(default=0, ge=0, description="Number of forks")
    watchers_count: int = Field(default=0, ge=0, description="Number of watchers")
    open_issues_count: int = Field(default=0, ge=0, description="Number of open issues")
    size: int = Field(default=0, ge=0, description="Repository size in KB")
    language: str | None = Field(None, description="Primary programming language")
    description: str | None = Field(
        None, max_length=350, description="Repository description"
    )
    topics: list[str] = Field(default_factory=list, description="Repository topics")
    license_name: str | None = Field(None, description="License name")
    is_private: bool = Field(default=False, description="Whether repository is private")
    is_fork: bool = Field(default=False, description="Whether repository is a fork")
    is_archived: bool = Field(
        default=False, description="Whether repository is archived"
    )
    is_disabled: bool = Field(
        default=False, description="Whether repository is disabled"
    )
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")
    pushed_at: datetime | None = Field(None, description="Last push timestamp")

    @field_validator("owner", "name")
    @classmethod
    def validate_github_name(cls, v: str) -> str:
        """Validate GitHub username/repository name format."""
        if not re.match(r"^[a-zA-Z0-9._-]+$", v):
            raise ValueError("Invalid GitHub name format")
        if v.startswith(".") or v.endswith("."):
            raise ValueError("GitHub names cannot start or end with a period")
        if ".." in v:
            raise ValueError("GitHub names cannot contain consecutive periods")
        return v

    @field_validator("url", "html_url", "clone_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL format")
        return v

    @model_validator(mode="after")
    def validate_full_name_consistency(self) -> "Repository":
        """Ensure full_name matches owner/name."""
        expected_full_name = f"{self.owner}/{self.name}"
        if self.full_name != expected_full_name:
            raise ValueError(
                f'full_name "{self.full_name}" does not match "{expected_full_name}"'
            )
        return self

    @classmethod
    def from_github_api(cls, data: dict[str, Any]) -> "Repository":
        """Create Repository from GitHub API response."""
        return cls(
            id=data.get("id"),
            owner=data["owner"]["login"],
            name=data["name"],
            full_name=data["full_name"],
            url=data["url"],
            html_url=data["html_url"],
            clone_url=data["clone_url"],
            default_branch=data.get("default_branch", "main"),
            stars=data.get("stargazers_count", 0),
            forks_count=data.get("forks_count", 0),
            watchers_count=data.get("watchers_count", 0),
            open_issues_count=data.get("open_issues_count", 0),
            size=data.get("size", 0),
            language=data.get("language"),
            description=data.get("description"),
            topics=data.get("topics", []),
            license_name=data.get("license", {}).get("name")
            if data.get("license")
            else None,
            is_private=data.get("private", False),
            is_fork=data.get("fork", False),
            is_archived=data.get("archived", False),
            is_disabled=data.get("disabled", False),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
            if data.get("created_at")
            else None,
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
            if data.get("updated_at")
            else None,
            pushed_at=datetime.fromisoformat(data["pushed_at"].replace("Z", "+00:00"))
            if data.get("pushed_at")
            else None,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.model_dump(exclude_none=True)


class User(BaseModel):
    """Represents a GitHub user."""

    id: int | None = Field(None, description="GitHub user ID")
    login: str = Field(..., min_length=1, max_length=39, description="GitHub username")
    name: str | None = Field(None, description="User's display name")
    email: str | None = Field(None, description="User's email address")
    avatar_url: str | None = Field(None, description="User's avatar URL")
    html_url: str = Field(..., description="User's profile URL")
    type: str = Field(default="User", description="User type (User, Organization)")
    site_admin: bool = Field(
        default=False, description="Whether user is a site admin"
    )

    @field_validator("login")
    @classmethod
    def validate_login(cls, v: str) -> str:
        """Validate GitHub username format."""
        if not re.match(r"^[a-zA-Z0-9._-]+$", v):
            raise ValueError("Invalid GitHub username format")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        """Validate email format if provided."""
        if v is None:
            return v
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Invalid email format")
        return v

    @classmethod
    def from_github_api(cls, data: dict[str, Any]) -> "User":
        """Create User from GitHub API response."""
        return cls(
            id=data.get("id"),
            login=data["login"],
            name=data.get("name"),
            email=data.get("email"),
            avatar_url=data.get("avatar_url"),
            html_url=data["html_url"],
            type=data.get("type", "User"),
            site_admin=data.get("site_admin", False),
        )


class Fork(BaseModel):
    """Represents a fork of a repository."""

    repository: Repository = Field(..., description="Fork repository details")
    parent: Repository = Field(..., description="Parent repository details")
    owner: User = Field(..., description="Fork owner")
    last_activity: datetime | None = Field(
        None, description="Last activity timestamp"
    )
    commits_ahead: int = Field(default=0, ge=0, description="Commits ahead of parent")
    commits_behind: int = Field(default=0, ge=0, description="Commits behind parent")
    is_active: bool = Field(default=True, description="Whether fork is considered active")
    divergence_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="How much fork has diverged"
    )

    @model_validator(mode="after")
    def validate_fork_relationship(self) -> "Fork":
        """Validate that repository is actually a fork of parent."""
        if not self.repository.is_fork:
            raise ValueError("Repository must be marked as a fork")
        if self.repository.full_name == self.parent.full_name:
            raise ValueError("Fork cannot be the same as parent repository")
        return self

    @classmethod
    def from_github_api(
        cls, fork_data: dict[str, Any], parent_data: dict[str, Any]
    ) -> "Fork":
        """Create Fork from GitHub API response."""
        return cls(
            repository=Repository.from_github_api(fork_data),
            parent=Repository.from_github_api(parent_data),
            owner=User.from_github_api(fork_data["owner"]),
            last_activity=datetime.fromisoformat(
                fork_data["pushed_at"].replace("Z", "+00:00")
            )
            if fork_data.get("pushed_at")
            else None,
        )

    def calculate_activity_score(self) -> float:
        """Calculate activity score based on recent activity."""
        if not self.last_activity:
            return 0.0

        # Normalize last_activity to UTC naive datetime for comparison
        last_activity = self.last_activity
        if last_activity.tzinfo is not None:
            last_activity = last_activity.utctimetuple()
            last_activity = datetime(*last_activity[:6])

        days_since_activity = (datetime.utcnow() - last_activity).days

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


class Commit(BaseModel):
    """Represents a Git commit."""

    sha: str = Field(
        ..., min_length=40, max_length=40, description="Commit SHA hash"
    )
    message: str = Field(..., min_length=1, description="Commit message")
    author: User = Field(..., description="Commit author")
    committer: User | None = Field(None, description="Commit committer")
    date: datetime = Field(..., description="Commit timestamp")
    author_date: datetime | None = Field(None, description="Author timestamp")
    files_changed: list[str] = Field(
        default_factory=list, description="Changed files"
    )
    additions: int = Field(default=0, ge=0, description="Lines added")
    deletions: int = Field(default=0, ge=0, description="Lines deleted")
    total_changes: int = Field(default=0, ge=0, description="Total lines changed")
    parents: list[str] = Field(
        default_factory=list, description="Parent commit SHAs"
    )
    is_merge: bool = Field(default=False, description="Whether this is a merge commit")
    verification_verified: bool = Field(
        default=False, description="Whether commit is verified"
    )

    @field_validator("sha")
    @classmethod
    def validate_sha(cls, v: str) -> str:
        """Validate SHA format."""
        if not re.match(r"^[a-f0-9]{40}$", v):
            raise ValueError("Invalid SHA format - must be 40 character hex string")
        return v

    @model_validator(mode="after")
    def calculate_total_changes(self) -> "Commit":
        """Calculate total changes from additions and deletions."""
        self.total_changes = self.additions + self.deletions
        return self

    @model_validator(mode="after")
    def detect_merge_commit(self) -> "Commit":
        """Detect if this is a merge commit based on parents."""
        self.is_merge = len(self.parents) > 1
        return self

    @classmethod
    def from_github_api(cls, data: dict[str, Any]) -> "Commit":
        """Create Commit from GitHub API response."""
        commit_data = data.get("commit", data)
        stats = data.get("stats", {})

        return cls(
            sha=data["sha"],
            message=commit_data["message"],
            author=User.from_github_api(
                data.get("author", commit_data["author"])
            ),
            committer=User.from_github_api(
                data.get("committer", commit_data["committer"])
            )
            if data.get("committer")
            else None,
            date=datetime.fromisoformat(
                commit_data["committer"]["date"].replace("Z", "+00:00")
            ),
            author_date=datetime.fromisoformat(
                commit_data["author"]["date"].replace("Z", "+00:00")
            )
            if commit_data.get("author", {}).get("date")
            else None,
            files_changed=[f["filename"] for f in data.get("files", [])],
            additions=stats.get("additions", 0),
            deletions=stats.get("deletions", 0),
            parents=[p["sha"] for p in data.get("parents", [])],
            verification_verified=data.get("commit", {})
            .get("verification", {})
            .get("verified", False),
        )

    def get_commit_type(self) -> str:
        """Determine commit type based on message."""
        message_lower = self.message.lower()

        if any(
            keyword in message_lower
            for keyword in ["fix", "bug", "patch", "hotfix"]
        ):
            return "fix"
        elif any(
            keyword in message_lower
            for keyword in ["feat", "feature", "add", "implement"]
        ):
            return "feature"
        elif any(
            keyword in message_lower for keyword in ["doc", "readme", "comment"]
        ):
            return "docs"
        elif any(keyword in message_lower for keyword in ["test", "spec"]):
            return "test"
        elif any(
            keyword in message_lower
            for keyword in ["refactor", "clean", "improve"]
        ):
            return "refactor"
        elif any(
            keyword in message_lower for keyword in ["perf", "optimize", "speed"]
        ):
            return "performance"
        elif self.is_merge:
            return "merge"
        else:
            return "other"

    def is_significant(self) -> bool:
        """Determine if commit represents significant changes."""
        # Skip merge commits and very small changes
        if self.is_merge:
            return False
        if self.total_changes < 5:
            return False

        # Skip documentation-only changes for significance
        return not (self.get_commit_type() == "docs" and self.total_changes < 20)
