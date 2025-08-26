"""Fork commit status detection system for determining if forks have commits ahead."""

import logging
from urllib.parse import urlparse

from forklift.github.client import GitHubAPIError, GitHubClient, GitHubNotFoundError
from forklift.models.fork_qualification import QualifiedForksResult

logger = logging.getLogger(__name__)


class ForkCommitStatusError(Exception):
    """Raised when fork commit status detection fails."""

    pass


class ForkCommitStatusChecker:
    """Determines if forks have commits ahead using qualification data with GitHub API fallback."""

    def __init__(self, github_client: GitHubClient):
        """
        Initialize fork commit status checker.

        Args:
            github_client: GitHub API client for fallback operations
        """
        self.github_client = github_client
        self.stats = {
            "qualification_data_hits": 0,
            "api_fallback_calls": 0,
            "status_unknown": 0,
            "no_commits_ahead": 0,
            "has_commits_ahead": 0,
            "errors": 0,
        }

    async def has_commits_ahead(
        self, fork_url: str, qualification_result: QualifiedForksResult | None = None
    ) -> bool | None:
        """
        Determine if fork has commits ahead of upstream using qualification data or GitHub API fallback.

        Args:
            fork_url: URL of the fork repository
            qualification_result: Optional qualification result containing fork data

        Returns:
            True: Fork has commits ahead
            False: Fork has no commits ahead
            None: Status cannot be determined

        Raises:
            ForkCommitStatusError: If fork URL is invalid or other errors occur
        """
        try:
            # Parse fork URL to extract owner and repo
            owner, repo = self._parse_fork_url(fork_url)

            # First try using qualification data if available
            if qualification_result:
                status = await self._check_using_qualification_data(
                    owner, repo, qualification_result
                )
                if status is not None:
                    self.stats["qualification_data_hits"] += 1
                    if status:
                        self.stats["has_commits_ahead"] += 1
                    else:
                        self.stats["no_commits_ahead"] += 1

                    logger.debug(
                        f"Fork {owner}/{repo} commit status from qualification data: {status}"
                    )
                    return status

            # Fallback to GitHub API
            logger.debug(f"Using GitHub API fallback for fork {owner}/{repo}")
            status = await self._check_using_github_api(owner, repo)
            self.stats["api_fallback_calls"] += 1

            if status is not None:
                if status:
                    self.stats["has_commits_ahead"] += 1
                else:
                    self.stats["no_commits_ahead"] += 1
            else:
                self.stats["status_unknown"] += 1

            logger.debug(f"Fork {owner}/{repo} commit status from GitHub API: {status}")
            return status

        except ForkCommitStatusError:
            # Re-raise our own exceptions
            self.stats["errors"] += 1
            raise
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Error checking commit status for {fork_url}: {e}")
            raise ForkCommitStatusError(
                f"Failed to check commit status for {fork_url}: {e}"
            ) from e

    async def _check_using_qualification_data(
        self, owner: str, repo: str, qualification_result: QualifiedForksResult
    ) -> bool | None:
        """
        Check commit status using cached qualification data.

        Args:
            owner: Fork owner username
            repo: Fork repository name
            qualification_result: Qualification result containing fork data

        Returns:
            True if fork has commits ahead, False if no commits ahead, None if not found
        """
        full_name = f"{owner}/{repo}"

        # Find the fork in qualification data
        for fork_data in qualification_result.collected_forks:
            if fork_data.metrics.full_name == full_name:
                # Use the computed property from ForkQualificationMetrics
                has_commits = not fork_data.metrics.can_skip_analysis
                logger.debug(
                    f"Found fork {full_name} in qualification data: "
                    f"created_at={fork_data.metrics.created_at}, "
                    f"pushed_at={fork_data.metrics.pushed_at}, "
                    f"has_commits={has_commits}"
                )
                return has_commits

        logger.debug(f"Fork {full_name} not found in qualification data")
        return None

    async def _check_using_github_api(self, owner: str, repo: str) -> bool | None:
        """
        Fallback to GitHub API when qualification data is unavailable.

        Args:
            owner: Fork owner username
            repo: Fork repository name

        Returns:
            True if fork has commits ahead, False if no commits ahead, None if cannot determine

        Raises:
            Exception: Re-raises unexpected errors for handling by caller
        """
        try:
            # Get repository information to check timestamps
            repository = await self.github_client.get_repository(owner, repo)

            # Use the same logic as qualification data: created_at >= pushed_at means no commits ahead
            if repository.created_at is None or repository.pushed_at is None:
                # If we can't determine timestamps, assume there might be commits
                has_commits = True
            else:
                has_commits = repository.pushed_at > repository.created_at

            logger.debug(
                f"GitHub API check for {owner}/{repo}: "
                f"created_at={repository.created_at}, "
                f"pushed_at={repository.pushed_at}, "
                f"has_commits={has_commits}"
            )

            return has_commits

        except GitHubNotFoundError:
            logger.warning(f"Fork {owner}/{repo} not found via GitHub API")
            return None
        except GitHubAPIError as e:
            logger.warning(f"GitHub API error checking {owner}/{repo}: {e}")
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error checking {owner}/{repo} via GitHub API: {e}"
            )
            # Re-raise unexpected errors for handling by caller
            raise

    def _parse_fork_url(self, fork_url: str) -> tuple[str, str]:
        """
        Parse fork URL to extract owner and repository name.

        Args:
            fork_url: GitHub repository URL

        Returns:
            Tuple of (owner, repo)

        Raises:
            ForkCommitStatusError: If URL format is invalid
        """
        if not fork_url or not fork_url.strip():
            raise ForkCommitStatusError(f"Invalid fork URL format: {fork_url}")

        try:
            # Handle both full URLs and owner/repo format
            if fork_url.startswith("http"):
                parsed = urlparse(fork_url)

                # Check if it's a GitHub URL
                if parsed.netloc != "github.com":
                    raise ValueError("Not a GitHub URL")

                path_parts = [
                    part for part in parsed.path.strip("/").split("/") if part
                ]
                if len(path_parts) >= 2:
                    return path_parts[0], path_parts[1]
                else:
                    raise ValueError("Invalid GitHub URL path")
            else:
                # Handle owner/repo format
                if "/" in fork_url:
                    parts = fork_url.split("/")
                    if len(parts) == 2 and all(part.strip() for part in parts):
                        return parts[0], parts[1]
                    else:
                        raise ValueError("Invalid owner/repo format")
                else:
                    raise ValueError("Invalid fork URL format")

        except Exception as e:
            raise ForkCommitStatusError(f"Invalid fork URL format: {fork_url}") from e

    def get_statistics(self) -> dict[str, int]:
        """
        Get statistics about fork commit status checking operations.

        Returns:
            Dictionary containing operation statistics
        """
        return self.stats.copy()

    def reset_statistics(self) -> None:
        """Reset all statistics counters."""
        for key in self.stats:
            self.stats[key] = 0

    def log_statistics(self) -> None:
        """Log current statistics for monitoring."""
        total_checks = sum(self.stats.values())
        if total_checks == 0:
            logger.info("No fork commit status checks performed yet")
            return

        logger.info(
            "Fork commit status checker statistics: "
            f"total_checks={total_checks}, "
            f"qualification_hits={self.stats['qualification_data_hits']}, "
            f"api_fallbacks={self.stats['api_fallback_calls']}, "
            f"has_commits={self.stats['has_commits_ahead']}, "
            f"no_commits={self.stats['no_commits_ahead']}, "
            f"unknown={self.stats['status_unknown']}, "
            f"errors={self.stats['errors']}"
        )
