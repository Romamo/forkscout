"""Configuration for commit counting operations."""

from dataclasses import dataclass


@dataclass
class CommitCountConfig:
    """Configuration for commit counting operations.

    This configuration controls how commits ahead are counted and displayed,
    allowing users to balance between accuracy and performance.
    """

    max_count_limit: int = 100
    """Maximum commits to count (default: 100). Set to 0 for unlimited counting."""

    display_limit: int = 5
    """Maximum commits to fetch for display details (default: 5)."""

    use_unlimited_counting: bool = False
    """For accuracy-critical scenarios, bypass count limits (default: False)."""

    timeout_seconds: int = 30
    """Timeout for counting operations in seconds (default: 30)."""

    def __post_init__(self) -> None:
        """Validate configuration values after initialization."""
        if self.max_count_limit < 0:
            raise ValueError("max_count_limit must be non-negative (0 for unlimited)")

        if self.display_limit < 0:
            raise ValueError("display_limit must be non-negative")

        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        # If unlimited counting is enabled, set max_count_limit to 0
        if self.use_unlimited_counting:
            self.max_count_limit = 0

    @property
    def is_unlimited(self) -> bool:
        """Check if unlimited counting is enabled."""
        return self.max_count_limit == 0 or self.use_unlimited_counting

    @property
    def effective_max_count(self) -> int | None:
        """Get the effective maximum count limit.

        Returns:
            None for unlimited counting, otherwise the max_count_limit
        """
        return None if self.is_unlimited else self.max_count_limit

    def get_display_indicator(self, count: int) -> str:
        """Get the display indicator for a commit count.

        Args:
            count: The actual commit count

        Returns:
            String representation for display (e.g., "+5", "100+")
        """
        if self.is_unlimited:
            return f"+{count}" if count > 0 else ""

        if count >= self.max_count_limit:
            return f"{self.max_count_limit}+"

        return f"+{count}" if count > 0 else ""

    @classmethod
    def from_cli_options(
        cls,
        max_commits_count: int | None = None,
        commit_display_limit: int | None = None,
        unlimited: bool = False
    ) -> "CommitCountConfig":
        """Create configuration from CLI options.

        Args:
            max_commits_count: Maximum commits to count (0 for unlimited)
            commit_display_limit: Maximum commits to fetch for display
            unlimited: Enable unlimited counting

        Returns:
            CommitCountConfig instance
        """
        config = cls()

        if max_commits_count is not None:
            config.max_count_limit = max_commits_count

        if commit_display_limit is not None:
            config.display_limit = commit_display_limit

        if unlimited:
            config.use_unlimited_counting = True

        # Re-run validation
        config.__post_init__()

        return config
