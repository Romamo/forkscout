"""Optimized commit fetcher that uses fork qualification data to minimize API calls."""

import asyncio
import logging
import time
from collections.abc import Callable

from forkscout.github.client import GitHubClient
from forkscout.github.exceptions import GitHubAPIError
from forkscout.models.fork_qualification import CollectedForkData, QualifiedForksResult
from forkscout.models.github import RecentCommit

logger = logging.getLogger(__name__)


class OptimizedCommitFetchingError(Exception):
    """Raised when optimized commit fetching fails."""

    pass


class CommitFetchingStats:
    """Statistics for commit fetching operations."""

    def __init__(self) -> None:
        """Initialize commit fetching statistics."""
        self.total_forks_processed = 0
        self.forks_skipped_no_commits = 0
        self.forks_with_commits_fetched = 0
        self.api_calls_made = 0
        self.api_calls_saved = 0
        self.processing_time_seconds = 0.0
        self.errors_encountered = 0
        self.fallback_operations = 0

    @property
    def efficiency_percentage(self) -> float:
        """Calculate API efficiency percentage."""
        total_potential_calls = self.api_calls_made + self.api_calls_saved
        if total_potential_calls == 0:
            return 0.0
        return (self.api_calls_saved / total_potential_calls) * 100

    @property
    def skip_rate_percentage(self) -> float:
        """Calculate percentage of forks skipped."""
        if self.total_forks_processed == 0:
            return 0.0
        return (self.forks_skipped_no_commits / self.total_forks_processed) * 100

    def get_summary(self) -> str:
        """Get human-readable summary of statistics."""
        return f"""Commit Fetching Statistics:
Total Forks: {self.total_forks_processed}
Skipped (no commits): {self.forks_skipped_no_commits} ({self.skip_rate_percentage:.1f}%)
Fetched commits: {self.forks_with_commits_fetched}
API calls made: {self.api_calls_made}
API calls saved: {self.api_calls_saved}
Efficiency: {self.efficiency_percentage:.1f}%
Processing time: {self.processing_time_seconds:.2f}s
Errors: {self.errors_encountered}
Fallbacks: {self.fallback_operations}"""


class OptimizedCommitFetcher:
    """Optimized commit fetcher using fork qualification data."""

    def __init__(self, github_client: GitHubClient):
        """Initialize optimized commit fetcher."""
        self.github_client = github_client

    async def fetch_commits_for_qualified_forks(
        self,
        qualified_forks: QualifiedForksResult,
        parent_owner: str,
        parent_repo: str,
        max_commits_per_fork: int = 5,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> dict[str, list[RecentCommit]]:
        """
        Fetch commits for qualified forks using optimization.

        Uses fork qualification data to skip expensive API calls for forks
        that have no commits ahead, and batch processes forks that do.

        Args:
            qualified_forks: Result from fork qualification process
            parent_owner: Parent repository owner
            parent_repo: Parent repository name
            max_commits_per_fork: Maximum commits to fetch per fork (1-10)
            progress_callback: Optional callback for progress updates (current, total, status)

        Returns:
            Dictionary mapping fork full_name to list of RecentCommit objects

        Raises:
            OptimizedCommitFetchingError: If commit fetching fails
        """
        if not (1 <= max_commits_per_fork <= 10):
            raise ValueError("max_commits_per_fork must be between 1 and 10")

        logger.info(
            f"Starting optimized commit fetching for {len(qualified_forks.collected_forks)} forks"
        )
        start_time = time.time()
        stats = CommitFetchingStats()

        try:
            # Separate forks that need commit fetching from those that can be skipped
            forks_needing_commits = qualified_forks.forks_needing_analysis
            forks_to_skip = qualified_forks.forks_to_skip

            logger.info(
                f"Optimization: {len(forks_to_skip)} forks can be skipped, "
                f"{len(forks_needing_commits)} need commit fetching"
            )

            # Update statistics
            stats.total_forks_processed = len(qualified_forks.collected_forks)
            stats.forks_skipped_no_commits = len(forks_to_skip)
            stats.forks_with_commits_fetched = len(forks_needing_commits)
            stats.api_calls_saved = len(forks_to_skip) * 3  # Each fork would need 3 API calls (fork repo, parent repo, compare)

            # Initialize result dictionary
            commits_by_fork: dict[str, list[RecentCommit]] = {}

            # Skip forks with no commits ahead
            for fork_data in forks_to_skip:
                fork_name = fork_data.metrics.full_name
                commits_by_fork[fork_name] = []
                logger.debug(f"Skipped {fork_name} - no commits ahead based on qualification data")

            # Batch fetch commits for forks that need them
            if forks_needing_commits:
                await self._batch_fetch_commits(
                    forks_needing_commits,
                    parent_owner,
                    parent_repo,
                    max_commits_per_fork,
                    commits_by_fork,
                    stats,
                    progress_callback,
                )

            # Update final statistics
            stats.processing_time_seconds = time.time() - start_time

            logger.info(
                f"Optimized commit fetching completed: {stats.forks_with_commits_fetched} forks processed, "
                f"{stats.api_calls_saved} API calls saved ({stats.efficiency_percentage:.1f}% efficiency)"
            )

            return commits_by_fork

        except Exception as e:
            stats.processing_time_seconds = time.time() - start_time
            stats.errors_encountered += 1
            logger.error(f"Optimized commit fetching failed after {stats.processing_time_seconds:.2f}s: {e}")
            raise OptimizedCommitFetchingError(f"Failed to fetch commits optimally: {e}") from e

    async def _batch_fetch_commits(
        self,
        forks_needing_commits: list[CollectedForkData],
        parent_owner: str,
        parent_repo: str,
        max_commits_per_fork: int,
        commits_by_fork: dict[str, list[RecentCommit]],
        stats: CommitFetchingStats,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> None:
        """
        Batch fetch commits for forks that need them.

        Args:
            forks_needing_commits: List of forks that need commit fetching
            parent_owner: Parent repository owner
            parent_repo: Parent repository name
            max_commits_per_fork: Maximum commits to fetch per fork
            commits_by_fork: Dictionary to store results
            stats: Statistics object to update
            progress_callback: Optional progress callback
        """
        logger.info(f"Batch fetching commits for {len(forks_needing_commits)} forks")

        # Process forks in batches to avoid overwhelming the API
        batch_size = 5  # Process 5 forks concurrently
        total_forks = len(forks_needing_commits)

        for i in range(0, total_forks, batch_size):
            batch = forks_needing_commits[i:i + batch_size]
            batch_tasks = []

            for fork_data in batch:
                task = self._fetch_commits_for_single_fork(
                    fork_data,
                    parent_owner,
                    parent_repo,
                    max_commits_per_fork,
                    stats,
                )
                batch_tasks.append(task)

            # Execute batch concurrently
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Process batch results
            for j, result in enumerate(batch_results):
                fork_data = batch[i + j]
                fork_name = fork_data.metrics.full_name

                if isinstance(result, Exception):
                    logger.warning(f"Failed to fetch commits for {fork_name}: {result}")
                    stats.errors_encountered += 1
                    # Try fallback approach
                    fallback_commits = await self._fallback_commit_fetch(
                        fork_data, parent_owner, parent_repo, max_commits_per_fork, stats
                    )
                    commits_by_fork[fork_name] = fallback_commits
                else:
                    commits_by_fork[fork_name] = result  # type: ignore[assignment]

                # Update progress
                if progress_callback:
                    current_progress = min(i + j + 1, total_forks)
                    progress_callback(current_progress, total_forks, f"Fetched commits for {fork_name}")

            # Small delay between batches to be respectful to the API
            if i + batch_size < total_forks:
                await asyncio.sleep(0.1)

    async def _fetch_commits_for_single_fork(
        self,
        fork_data: CollectedForkData,
        parent_owner: str,
        parent_repo: str,
        max_commits_per_fork: int,
        stats: CommitFetchingStats,
    ) -> list[RecentCommit]:
        """
        Fetch commits for a single fork.

        Args:
            fork_data: Fork data with qualification metrics
            parent_owner: Parent repository owner
            parent_repo: Parent repository name
            max_commits_per_fork: Maximum commits to fetch
            stats: Statistics object to update

        Returns:
            List of RecentCommit objects

        Raises:
            GitHubAPIError: If API calls fail
        """
        fork_owner = fork_data.metrics.owner
        fork_repo = fork_data.metrics.name
        fork_name = fork_data.metrics.full_name

        logger.debug(f"Fetching commits for {fork_name}")

        try:
            # Use the existing get_commits_ahead method
            commits = await self.github_client.get_commits_ahead(
                fork_owner, fork_repo, parent_owner, parent_repo, max_commits_per_fork
            )

            # Update statistics (get_commits_ahead makes 3 API calls: fork repo, parent repo, compare)
            stats.api_calls_made += 3

            logger.debug(f"Successfully fetched {len(commits)} commits for {fork_name}")
            return commits

        except GitHubAPIError as e:
            logger.warning(f"GitHub API error fetching commits for {fork_name}: {e}")
            stats.errors_encountered += 1
            raise

    async def _fallback_commit_fetch(
        self,
        fork_data: CollectedForkData,
        parent_owner: str,
        parent_repo: str,
        max_commits_per_fork: int,
        stats: CommitFetchingStats,
    ) -> list[RecentCommit]:
        """
        Fallback commit fetching when qualification data is unreliable.

        This method is used when we can't determine commit status from
        qualification data or when the primary fetch method fails.

        Args:
            fork_data: Fork data with qualification metrics
            parent_owner: Parent repository owner
            parent_repo: Parent repository name
            max_commits_per_fork: Maximum commits to fetch
            stats: Statistics object to update

        Returns:
            List of RecentCommit objects (may be empty on failure)
        """
        fork_name = fork_data.metrics.full_name
        logger.debug(f"Using fallback commit fetch for {fork_name}")

        try:
            stats.fallback_operations += 1

            # Try to fetch commits using the standard method
            fork_owner = fork_data.metrics.owner
            fork_repo = fork_data.metrics.name

            commits = await self.github_client.get_commits_ahead(
                fork_owner, fork_repo, parent_owner, parent_repo, max_commits_per_fork
            )

            stats.api_calls_made += 3  # Track API calls made in fallback
            logger.debug(f"Fallback successful for {fork_name}: {len(commits)} commits")
            return commits

        except Exception as e:
            logger.warning(f"Fallback commit fetch failed for {fork_name}: {e}")
            stats.errors_encountered += 1
            return []  # Return empty list on failure

    async def fetch_commits_for_single_fork_with_qualification(
        self,
        fork_data: CollectedForkData,
        parent_owner: str,
        parent_repo: str,
        max_commits_per_fork: int = 5,
        force_fetch: bool = False,
    ) -> list[RecentCommit]:
        """
        Fetch commits for a single fork using qualification data optimization.

        Args:
            fork_data: Fork data with qualification metrics
            parent_owner: Parent repository owner
            parent_repo: Parent repository name
            max_commits_per_fork: Maximum commits to fetch (1-10)
            force_fetch: If True, bypass qualification optimization

        Returns:
            List of RecentCommit objects

        Raises:
            OptimizedCommitFetchingError: If commit fetching fails
        """
        if not (1 <= max_commits_per_fork <= 10):
            raise ValueError("max_commits_per_fork must be between 1 and 10")

        fork_name = fork_data.metrics.full_name

        # Check if we can skip based on qualification data
        if not force_fetch and fork_data.metrics.can_skip_analysis:
            logger.debug(f"Skipping {fork_name} - no commits ahead based on qualification data")
            return []

        # Fetch commits normally
        logger.debug(f"Fetching commits for {fork_name} (qualification suggests commits ahead)")

        try:
            stats = CommitFetchingStats()
            commits = await self._fetch_commits_for_single_fork(
                fork_data, parent_owner, parent_repo, max_commits_per_fork, stats
            )
            return commits

        except Exception as e:
            logger.error(f"Failed to fetch commits for {fork_name}: {e}")
            raise OptimizedCommitFetchingError(f"Failed to fetch commits for {fork_name}: {e}") from e

    def get_optimization_summary(self, qualified_forks: QualifiedForksResult) -> str:
        """
        Get a summary of potential optimization benefits.

        Args:
            qualified_forks: Result from fork qualification process

        Returns:
            Human-readable optimization summary
        """
        total_forks = len(qualified_forks.collected_forks)
        forks_to_skip = len(qualified_forks.forks_to_skip)
        forks_needing_commits = len(qualified_forks.forks_needing_analysis)

        api_calls_without_optimization = total_forks * 3  # Each fork needs 3 API calls
        api_calls_with_optimization = forks_needing_commits * 3  # Only process forks with commits
        api_calls_saved = api_calls_without_optimization - api_calls_with_optimization

        efficiency_percentage = (api_calls_saved / api_calls_without_optimization) * 100 if api_calls_without_optimization > 0 else 0

        skip_percentage = (forks_to_skip / total_forks) * 100 if total_forks > 0 else 0.0
        commits_percentage = (forks_needing_commits / total_forks) * 100 if total_forks > 0 else 0.0

        return f"""Commit Fetching Optimization Summary:
Total Forks: {total_forks}
Forks to Skip: {forks_to_skip} ({skip_percentage:.1f}%)
Forks Needing Commits: {forks_needing_commits} ({commits_percentage:.1f}%)

API Call Optimization:
Without optimization: {api_calls_without_optimization} API calls
With optimization: {api_calls_with_optimization} API calls
API calls saved: {api_calls_saved}
Efficiency gain: {efficiency_percentage:.1f}%"""
