"""Comprehensive GitHub API verification and commits ahead detection engine."""

import asyncio
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from forklift.github.client import GitHubClient
from forklift.github.exceptions import (
    GitHubAPIError,
    GitHubNotFoundError,
    GitHubPrivateRepositoryError,
    GitHubRateLimitError,
)
from forklift.models.fork_qualification import (
    CollectedForkData,
)

logger = logging.getLogger(__name__)


class VerificationCache:
    """TTL cache for verification results with invalidation policies."""

    def __init__(self, ttl_hours: int = 24):
        """Initialize cache with TTL in hours."""
        self.ttl_hours = ttl_hours
        self._cache: dict[str, dict[str, Any]] = {}

    def _get_cache_key(self, fork_owner: str, fork_repo: str, parent_owner: str, parent_repo: str) -> str:
        """Generate cache key for fork comparison."""
        return f"{parent_owner}/{parent_repo}:{fork_owner}/{fork_repo}"

    def get(self, fork_owner: str, fork_repo: str, parent_owner: str, parent_repo: str) -> dict[str, Any] | None:
        """Get cached verification result if not expired."""
        key = self._get_cache_key(fork_owner, fork_repo, parent_owner, parent_repo)

        if key not in self._cache:
            return None

        cached_data = self._cache[key]
        cached_time = cached_data.get("cached_at")

        if not cached_time:
            # Invalid cache entry
            del self._cache[key]
            return None

        # Check if expired
        expiry_time = cached_time + timedelta(hours=self.ttl_hours)
        if datetime.now(UTC) > expiry_time:
            del self._cache[key]
            return None

        logger.debug(f"Cache hit for {key}")
        return cached_data.get("result")

    def set(self, fork_owner: str, fork_repo: str, parent_owner: str, parent_repo: str, result: dict[str, Any]) -> None:
        """Cache verification result with timestamp."""
        key = self._get_cache_key(fork_owner, fork_repo, parent_owner, parent_repo)

        self._cache[key] = {
            "result": result,
            "cached_at": datetime.now(UTC)
        }

        logger.debug(f"Cached result for {key}")

    def invalidate(self, fork_owner: str, fork_repo: str, parent_owner: str, parent_repo: str) -> None:
        """Invalidate specific cache entry."""
        key = self._get_cache_key(fork_owner, fork_repo, parent_owner, parent_repo)
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Invalidated cache for {key}")

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        logger.debug("Cleared all cache entries")

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        total_entries = len(self._cache)
        expired_entries = 0

        current_time = datetime.now(UTC)
        for cached_data in self._cache.values():
            cached_time = cached_data.get("cached_at")
            if cached_time:
                expiry_time = cached_time + timedelta(hours=self.ttl_hours)
                if current_time > expiry_time:
                    expired_entries += 1

        return {
            "total_entries": total_entries,
            "valid_entries": total_entries - expired_entries,
            "expired_entries": expired_entries
        }


class CommitVerificationEngine:
    """
    Comprehensive GitHub API verification engine for commits ahead detection.

    Provides lazy verification that only calls API when explicitly needed,
    with caching, rate limiting, and comprehensive error handling.
    """

    def __init__(
        self,
        github_client: GitHubClient,
        cache_ttl_hours: int = 24,
        max_concurrent_requests: int = 5,
        retry_attempts: int = 3,
        backoff_base_seconds: float = 1.0,
        progress_callback: Callable[[str], None] | None = None
    ):
        """
        Initialize CommitVerificationEngine.

        Args:
            github_client: GitHub API client instance
            cache_ttl_hours: Cache TTL in hours (default: 24)
            max_concurrent_requests: Maximum concurrent API requests
            retry_attempts: Number of retry attempts for failed requests
            backoff_base_seconds: Base seconds for exponential backoff
            progress_callback: Optional callback for progress updates
        """
        self.github_client = github_client
        self.cache = VerificationCache(ttl_hours=cache_ttl_hours)
        self.max_concurrent_requests = max_concurrent_requests
        self.retry_attempts = retry_attempts
        self.backoff_base_seconds = backoff_base_seconds
        self.progress_callback = progress_callback

        # Statistics tracking
        self.stats = {
            "api_calls_made": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "verification_errors": 0,
            "successful_verifications": 0
        }

    async def get_commits_ahead(
        self,
        fork_owner: str,
        fork_repo: str,
        parent_owner: str,
        parent_repo: str,
        use_cache: bool = True
    ) -> dict[str, Any]:
        """
        Get commits ahead/behind count with comprehensive error handling.

        Args:
            fork_owner: Fork repository owner
            fork_repo: Fork repository name
            parent_owner: Parent repository owner
            parent_repo: Parent repository name
            use_cache: Whether to use cached results

        Returns:
            Dictionary with ahead_by, behind_by, total_commits, and metadata
        """
        # Check cache first if enabled
        if use_cache:
            cached_result = self.cache.get(fork_owner, fork_repo, parent_owner, parent_repo)
            if cached_result:
                self.stats["cache_hits"] += 1
                logger.debug(f"Using cached result for {fork_owner}/{fork_repo}")
                return cached_result

            self.stats["cache_misses"] += 1

        # Perform API verification with retry logic
        result = await self._verify_with_retry(fork_owner, fork_repo, parent_owner, parent_repo)

        # Cache successful results
        if use_cache and result.get("success", False):
            self.cache.set(fork_owner, fork_repo, parent_owner, parent_repo, result)

        return result

    async def _verify_with_retry(
        self,
        fork_owner: str,
        fork_repo: str,
        parent_owner: str,
        parent_repo: str
    ) -> dict[str, Any]:
        """Verify commits ahead with retry logic and exponential backoff."""
        last_exception: Exception | None = None

        for attempt in range(self.retry_attempts):
            try:
                result = await self._perform_verification(fork_owner, fork_repo, parent_owner, parent_repo)
                self.stats["successful_verifications"] += 1
                return result

            except GitHubRateLimitError as e:
                logger.warning(f"Rate limit hit during verification (attempt {attempt + 1}): {e}")
                if attempt < self.retry_attempts - 1:
                    # Wait for rate limit reset
                    await self._handle_rate_limit(e)
                last_exception = e

            except (GitHubNotFoundError, GitHubPrivateRepositoryError) as e:
                logger.warning(f"Repository not found during verification: {e}")
                # Don't retry for 404 errors or private repository errors
                self.stats["verification_errors"] += 1
                return {
                    "success": False,
                    "error": "repository_not_found",
                    "error_message": str(e),
                    "ahead_by": 0,
                    "behind_by": 0,
                    "total_commits": 0,
                    "verified_at": datetime.now(UTC).isoformat()
                }

            except GitHubAPIError as e:
                logger.warning(f"GitHub API error during verification (attempt {attempt + 1}): {e}")
                if attempt < self.retry_attempts - 1:
                    # Exponential backoff
                    wait_time = self.backoff_base_seconds * (2 ** attempt)
                    logger.debug(f"Waiting {wait_time}s before retry")
                    await asyncio.sleep(wait_time)
                last_exception = e

            except Exception as e:
                logger.error(f"Unexpected error during verification (attempt {attempt + 1}): {e}")
                if attempt < self.retry_attempts - 1:
                    wait_time = self.backoff_base_seconds * (2 ** attempt)
                    await asyncio.sleep(wait_time)
                last_exception = e

        # All retries failed
        self.stats["verification_errors"] += 1
        return {
            "success": False,
            "error": "verification_failed",
            "error_message": str(last_exception) if last_exception else "Unknown error",
            "ahead_by": 0,
            "behind_by": 0,
            "total_commits": 0,
            "verified_at": datetime.now(UTC).isoformat()
        }

    async def _perform_verification(
        self,
        fork_owner: str,
        fork_repo: str,
        parent_owner: str,
        parent_repo: str
    ) -> dict[str, Any]:
        """Perform actual GitHub API verification."""
        self.stats["api_calls_made"] += 1

        logger.debug(f"Verifying commits for {fork_owner}/{fork_repo} vs {parent_owner}/{parent_repo}")

        try:
            # Get repository information to find default branches
            fork_info = await self.github_client.get_repository(fork_owner, fork_repo)
            parent_info = await self.github_client.get_repository(parent_owner, parent_repo)

            # Use GitHub's compare API
            comparison = await self.github_client.compare_commits(
                parent_owner,
                parent_repo,
                parent_info.default_branch,
                f"{fork_owner}:{fork_info.default_branch}"
            )

            # Extract commit counts
            ahead_by = comparison.get("ahead_by", 0)
            behind_by = comparison.get("behind_by", 0)
            total_commits = comparison.get("total_commits", 0)

            # Get commit details if available
            commits = comparison.get("commits", [])
            commit_count = len(commits)

            return {
                "success": True,
                "ahead_by": ahead_by,
                "behind_by": behind_by,
                "total_commits": total_commits,
                "commit_count": commit_count,
                "fork_default_branch": fork_info.default_branch,
                "parent_default_branch": parent_info.default_branch,
                "verified_at": datetime.now(UTC).isoformat(),
                "verification_method": "github_compare_api"
            }

        except Exception as e:
            logger.error(f"Failed to verify {fork_owner}/{fork_repo}: {e}")
            raise

    async def _handle_rate_limit(self, rate_limit_error: GitHubRateLimitError) -> None:
        """Handle rate limit by waiting for reset."""
        if hasattr(rate_limit_error, "reset_time") and rate_limit_error.reset_time:
            current_time = time.time()
            wait_time = max(0, rate_limit_error.reset_time - current_time + 1)  # +1 second buffer

            if wait_time > 0:
                logger.info(f"Rate limit exceeded, waiting {wait_time:.1f}s for reset")
                if self.progress_callback:
                    self.progress_callback(f"Rate limit hit, waiting {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
        else:
            # Fallback wait time
            logger.info("Rate limit exceeded, waiting 60s")
            if self.progress_callback:
                self.progress_callback("Rate limit hit, waiting 60s...")
            await asyncio.sleep(60)

    async def batch_verify_forks(
        self,
        fork_data_list: list[CollectedForkData],
        parent_owner: str,
        parent_repo: str,
        use_cache: bool = True,
        skip_no_commits: bool = True
    ) -> list[CollectedForkData]:
        """
        Batch verify multiple forks with concurrency control.

        Args:
            fork_data_list: List of fork data to verify
            parent_owner: Parent repository owner
            parent_repo: Parent repository name
            use_cache: Whether to use cached results
            skip_no_commits: Whether to skip forks with no commits ahead

        Returns:
            List of fork data with updated verification results
        """
        logger.info(f"Starting batch verification of {len(fork_data_list)} forks")

        # Filter forks if skip_no_commits is enabled
        forks_to_verify = []
        skipped_forks = []

        for fork_data in fork_data_list:
            if skip_no_commits and fork_data.metrics.can_skip_analysis:
                logger.debug(f"Skipping {fork_data.metrics.full_name} - no commits ahead")
                skipped_forks.append(fork_data)
            else:
                forks_to_verify.append(fork_data)

        logger.info(f"Verifying {len(forks_to_verify)} forks, skipping {len(skipped_forks)}")

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        async def verify_single_fork(fork_data: CollectedForkData) -> CollectedForkData:
            """Verify a single fork with semaphore control."""
            async with semaphore:
                if self.progress_callback:
                    self.progress_callback(f"Verifying {fork_data.metrics.full_name}...")

                verification_result = await self.get_commits_ahead(
                    fork_data.metrics.owner,
                    fork_data.metrics.name,
                    parent_owner,
                    parent_repo,
                    use_cache=use_cache
                )

                # Update fork data with verification results
                if verification_result.get("success", False):
                    fork_data.exact_commits_ahead = verification_result.get("ahead_by", 0)
                    fork_data.exact_commits_behind = verification_result.get("behind_by", 0)
                else:
                    fork_data.exact_commits_ahead = "Unknown"
                    fork_data.exact_commits_behind = "Unknown"

                return fork_data

        # Execute verification tasks concurrently
        start_time = time.time()

        if forks_to_verify:
            tasks = [verify_single_fork(fork_data) for fork_data in forks_to_verify]
            verified_forks = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle any exceptions
            successful_verifications = []
            for i, result in enumerate(verified_forks):
                if isinstance(result, Exception):
                    logger.error(f"Failed to verify fork {forks_to_verify[i].metrics.full_name}: {result}")
                    # Keep original fork data
                    successful_verifications.append(forks_to_verify[i])
                elif isinstance(result, CollectedForkData):
                    successful_verifications.append(result)
        else:
            successful_verifications = []

        processing_time = time.time() - start_time

        # Combine verified and skipped forks
        all_forks = successful_verifications + skipped_forks

        logger.info(
            f"Batch verification completed in {processing_time:.2f}s - "
            f"verified: {len(successful_verifications)}, skipped: {len(skipped_forks)}"
        )

        return all_forks

    async def verify_individual_fork(
        self,
        fork_data: CollectedForkData,
        parent_owner: str,
        parent_repo: str,
        force_verification: bool = False
    ) -> CollectedForkData:
        """
        Verify individual fork for detailed mode operations.

        Args:
            fork_data: Fork data to verify
            parent_owner: Parent repository owner
            parent_repo: Parent repository name
            force_verification: Force verification even if fork has no commits

        Returns:
            Updated fork data with verification results
        """
        # Check if verification is needed
        if not force_verification and fork_data.metrics.can_skip_analysis:
            logger.debug(f"Skipping verification for {fork_data.metrics.full_name} - no commits ahead")
            return fork_data

        logger.info(f"Verifying individual fork: {fork_data.metrics.full_name}")

        verification_result = await self.get_commits_ahead(
            fork_data.metrics.owner,
            fork_data.metrics.name,
            parent_owner,
            parent_repo
        )

        # Update fork data with verification results
        if verification_result.get("success", False):
            fork_data.exact_commits_ahead = verification_result.get("ahead_by", 0)
            fork_data.exact_commits_behind = verification_result.get("behind_by", 0)
        else:
            fork_data.exact_commits_ahead = "Unknown"
            fork_data.exact_commits_behind = "Unknown"

        return fork_data

    def get_verification_stats(self) -> dict[str, Any]:
        """Get verification engine statistics."""
        cache_stats = self.cache.get_stats()

        return {
            "api_calls_made": self.stats["api_calls_made"],
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "verification_errors": self.stats["verification_errors"],
            "successful_verifications": self.stats["successful_verifications"],
            "cache_stats": cache_stats,
            "cache_hit_rate": (
                self.stats["cache_hits"] / (self.stats["cache_hits"] + self.stats["cache_misses"])
                if (self.stats["cache_hits"] + self.stats["cache_misses"]) > 0
                else 0.0
            )
        }

    def reset_stats(self) -> None:
        """Reset verification statistics."""
        self.stats = {
            "api_calls_made": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "verification_errors": 0,
            "successful_verifications": 0
        }

    def clear_cache(self) -> None:
        """Clear verification cache."""
        self.cache.clear()
