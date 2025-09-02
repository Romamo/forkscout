"""GitHub API exceptions."""

from typing import Any


class GitHubAPIError(Exception):
    """Base exception for GitHub API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class GitHubAuthenticationError(GitHubAPIError):
    """Raised when GitHub API authentication fails."""

    pass


class GitHubRateLimitError(GitHubAPIError):
    """Raised when GitHub API rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        reset_time: int | None = None,
        remaining: int | None = None,
        limit: int | None = None,
        status_code: int | None = None,
    ):
        super().__init__(message, status_code=status_code)
        self.reset_time = reset_time
        self.remaining = remaining
        self.limit = limit


class GitHubNotFoundError(GitHubAPIError):
    """Raised when a GitHub resource is not found."""

    pass


class GitHubTimeoutError(GitHubAPIError):
    """Raised when GitHub API operations timeout."""

    def __init__(self, message: str, operation: str, timeout_seconds: float):
        super().__init__(message)
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class GitHubPrivateRepositoryError(GitHubAPIError):
    """Raised when trying to access private repository without permission."""

    def __init__(self, message: str, repository: str):
        super().__init__(message)
        self.repository = repository


class GitHubEmptyRepositoryError(GitHubAPIError):
    """Raised when repository has no commits or is empty."""

    def __init__(self, message: str, repository: str):
        super().__init__(message)
        self.repository = repository


class GitHubForkAccessError(GitHubAPIError):
    """Raised when fork cannot be accessed (private, deleted, etc.)."""

    def __init__(self, message: str, fork_url: str, reason: str):
        super().__init__(message)
        self.fork_url = fork_url
        self.reason = reason


class GitHubCommitComparisonError(GitHubAPIError):
    """Raised when commit comparison fails due to divergent histories or other issues."""

    def __init__(self, message: str, base_repo: str, head_repo: str, reason: str):
        super().__init__(message)
        self.base_repo = base_repo
        self.head_repo = head_repo
        self.reason = reason


class GitHubDivergentHistoryError(GitHubCommitComparisonError):
    """Raised when repositories have divergent histories that cannot be compared."""

    def __init__(self, message: str, base_repo: str, head_repo: str):
        super().__init__(message, base_repo, head_repo, "divergent_history")


class GitHubCommitAccessError(GitHubAPIError):
    """Raised when commit access fails for specific reasons."""

    def __init__(self, message: str, repository: str, reason: str, commit_sha: str | None = None):
        super().__init__(message)
        self.repository = repository
        self.reason = reason
        self.commit_sha = commit_sha
