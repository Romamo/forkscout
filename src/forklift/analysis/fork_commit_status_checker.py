"""Fork commit status detection system for determining if forks have commits ahead."""

import logging
from urllib.parse import urlparse

from forklift.github.client import GitHubAPIError, GitHubClient, GitHubNotFoundError
from forklift.models.fork_filtering import ForkFilteringConfig, ForkFilteringStats
from forklift.models.fork_qualification import QualifiedForksResult

logger = logging.getLogger(__name__)


class ForkCommitStatusError(Exception):
    """Raised when fork commit status detection fails."""

    pass


class ForkCommitStatusChecker:
    """Determines if forks have commits ahead using qualification data with GitHub API fallback."""

    def __init__(
        self, github_client: GitHubClient, config: ForkFilteringConfig | None = None
    ):
        """
        Initialize fork commit status checker.

        Args:
            github_client: GitHub API client for fallback operations
            config: Fork filtering configuration
        """
        self.github_client = github_client
        self.config = config or ForkFilteringConfig()
        self.stats = ForkFilteringStats()
        self._api_fallback_count = 0

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
            fork_name = f"{owner}/{repo}"

            # First try using qualification data if available
            if qualification_result:
                status = await self._check_using_qualification_data(
                    owner, repo, qualification_result
                )
                if status is not None:
                    self.stats.add_qualification_hit()

                    if self.config.log_filtering_decisions:
                        logger.info(
                            f"Fork filtering decision: {fork_name} - "
                            f"{'has commits ahead' if status else 'no commits ahead'} "
                            f"(source: qualification data)"
                        )

                    return status

            # Check if we should use API fallback
            if not self.config.fallback_to_api:
                if self.config.log_filtering_decisions:
                    logger.info(
                        f"Fork filtering decision: {fork_name} - "
                        f"status unknown (API fallback disabled)"
                    )
                self.stats.add_status_unknown()
                return None if self.config.prefer_inclusion_on_uncertainty else False

            # Check API fallback limits
            if (
                self.config.max_api_fallback_calls > 0
                and self._api_fallback_count >= self.config.max_api_fallback_calls
            ):
                if self.config.log_filtering_decisions:
                    logger.warning(
                        f"Fork filtering decision: {fork_name} - "
                        f"status unknown (API fallback limit reached: {self.config.max_api_fallback_calls})"
                    )
                self.stats.add_status_unknown()
                return None if self.config.prefer_inclusion_on_uncertainty else False

            # Fallback to GitHub API
            if self.config.log_filtering_decisions:
                logger.debug(f"Using GitHub API fallback for fork {fork_name}")

            status = await self._check_using_github_api(owner, repo)
            self._api_fallback_count += 1
            self.stats.add_api_fallback()

            if status is not None:
                if self.config.log_filtering_decisions:
                    logger.info(
                        f"Fork filtering decision: {fork_name} - "
                        f"{'has commits ahead' if status else 'no commits ahead'} "
                        f"(source: GitHub API)"
                    )
            else:
                self.stats.add_status_unknown()
                if self.config.log_filtering_decisions:
                    logger.warning(
                        f"Fork filtering decision: {fork_name} - "
                        f"status unknown (GitHub API could not determine)"
                    )

            return status

        except ForkCommitStatusError:
            # Re-raise our own exceptions
            self.stats.add_error()
            raise
        except Exception as e:
            self.stats.add_error()
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

                if self.config.log_filtering_decisions:
                    logger.debug(
                        f"Found fork {full_name} in qualification data: "
                        f"created_at={fork_data.metrics.created_at}, "
                        f"pushed_at={fork_data.metrics.pushed_at}, "
                        f"has_commits={has_commits}"
                    )
                return has_commits

        if self.config.log_filtering_decisions:
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

            if self.config.log_filtering_decisions:
                logger.debug(
                    f"GitHub API check for {owner}/{repo}: "
                    f"created_at={repository.created_at}, "
                    f"pushed_at={repository.pushed_at}, "
                    f"has_commits={has_commits}"
                )

            return has_commits

        except GitHubNotFoundError:
            if self.config.log_filtering_decisions:
                logger.warning(f"Fork {owner}/{repo} not found via GitHub API")
            return None
        except GitHubAPIError as e:
            if self.config.log_filtering_decisions:
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

    def should_filter_fork(
        self, fork_data: dict, qualification_result: QualifiedForksResult | None = None
    ) -> tuple[bool, str]:
        """
        Determine if a fork should be filtered out based on configuration and fork data.

        Args:
            fork_data: Fork data dictionary containing metadata
            qualification_result: Optional qualification result for commit status checking

        Returns:
            Tuple of (should_filter, reason) where should_filter is True if fork should be filtered
        """
        fork_name = fork_data.get("full_name", "unknown")

        # Check if filtering is enabled
        if not self.config.enabled:
            if self.config.log_filtering_decisions:
                logger.debug(f"Fork filtering disabled - including {fork_name}")
            return False, "filtering_disabled"

        # Check archived status
        if self.config.skip_archived_forks and fork_data.get("archived", False):
            if self.config.log_filtering_decisions:
                logger.info(
                    f"Fork filtering decision: {fork_name} - filtered (archived)"
                )
            return True, "archived"

        # Check disabled status
        if self.config.skip_disabled_forks and fork_data.get("disabled", False):
            if self.config.log_filtering_decisions:
                logger.info(
                    f"Fork filtering decision: {fork_name} - filtered (disabled)"
                )
            return True, "disabled"

        return False, "not_filtered"

    async def evaluate_fork_for_filtering(
        self,
        fork_url: str,
        fork_data: dict = None,
        qualification_result: QualifiedForksResult | None = None,
    ) -> tuple[bool, str]:
        """
        Evaluate a fork for filtering and update statistics.

        Args:
            fork_url: URL of the fork repository
            fork_data: Optional fork metadata
            qualification_result: Optional qualification result

        Returns:
            Tuple of (should_filter, reason)
        """
        # First check basic filtering criteria
        if fork_data:
            should_filter, reason = self.should_filter_fork(
                fork_data, qualification_result
            )
            if should_filter:
                self.stats.add_fork_evaluated(filtered=True, reason=reason)
                return True, reason

        # Check commit status
        try:
            has_commits = await self.has_commits_ahead(fork_url, qualification_result)

            if has_commits is False:
                # Fork has no commits ahead - filter it out
                self.stats.add_fork_evaluated(filtered=True, reason="no_commits_ahead")
                return True, "no_commits_ahead"
            elif has_commits is True:
                # Fork has commits ahead - include it
                self.stats.add_fork_evaluated(filtered=False)
                return False, "has_commits_ahead"
            else:
                # Status unknown - use preference setting
                should_filter = not self.config.prefer_inclusion_on_uncertainty
                reason = (
                    "status_unknown_excluded"
                    if should_filter
                    else "status_unknown_included"
                )
                self.stats.add_fork_evaluated(
                    filtered=should_filter, reason=reason if should_filter else None
                )
                return should_filter, reason

        except Exception as e:
            logger.error(f"Error evaluating fork {fork_url} for filtering: {e}")
            self.stats.add_error()
            # On error, use preference setting
            should_filter = not self.config.prefer_inclusion_on_uncertainty
            reason = "error_excluded" if should_filter else "error_included"
            self.stats.add_fork_evaluated(
                filtered=should_filter, reason=reason if should_filter else None
            )
            return should_filter, reason

    def get_statistics(self) -> ForkFilteringStats:
        """
        Get statistics about fork filtering operations.

        Returns:
            ForkFilteringStats object containing operation statistics
        """
        return self.stats

    def reset_statistics(self) -> None:
        """Reset all statistics counters."""
        self.stats.reset()
        self._api_fallback_count = 0

    def log_statistics(self) -> None:
        """Log current statistics for monitoring."""
        if not self.config.log_statistics:
            return

        if self.stats.total_forks_evaluated == 0:
            logger.info("No fork filtering operations performed yet")
            return

        stats_summary = self.stats.to_summary_dict()

        logger.info(
            f"Fork filtering statistics: "
            f"evaluated={stats_summary['total_evaluated']}, "
            f"filtered_out={stats_summary['filtered_out']}, "
            f"included={stats_summary['included']}, "
            f"filtering_rate={stats_summary['filtering_rate_percent']}%, "
            f"api_efficiency={stats_summary['api_efficiency_percent']}%"
        )

        if stats_summary["filtered_reasons"]:
            reasons = ", ".join(
                [
                    f"{reason}={count}"
                    for reason, count in stats_summary["filtered_reasons"].items()
                    if count > 0
                ]
            )
            if reasons:
                logger.info(f"Fork filtering reasons: {reasons}")

        if stats_summary["errors"] > 0:
            logger.warning(
                f"Fork filtering errors encountered: {stats_summary['errors']}"
            )

    def get_config(self) -> ForkFilteringConfig:
        """Get the current fork filtering configuration."""
        return self.config

    def update_config(self, config: ForkFilteringConfig) -> None:
        """Update the fork filtering configuration."""
        self.config = config
