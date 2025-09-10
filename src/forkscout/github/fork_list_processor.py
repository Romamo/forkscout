"""Fork list processor for efficient API usage using paginated forks list endpoint."""

import logging
import time
from collections.abc import Callable
from typing import Any

from forkscout.github.client import GitHubClient
from forkscout.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualificationStats,
    QualifiedForksResult,
)

logger = logging.getLogger(__name__)


class ForkListProcessingError(Exception):
    """Raised when fork list processing fails."""

    pass


class ForkListProcessor:
    """Processes GitHub repository forks using efficient paginated API calls."""

    def __init__(self, github_client: GitHubClient):
        """Initialize fork list processor with GitHub client."""
        self.github_client = github_client

    async def get_all_forks_list_data(
        self,
        owner: str,
        repo: str,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get all forks using only the paginated forks list endpoint.

        Uses only `/repos/{owner}/{repo}/forks?per_page=100&page=N` calls
        to minimize API usage while collecting comprehensive fork data.

        Args:
            owner: Repository owner
            repo: Repository name
            progress_callback: Optional callback for progress updates (current_page, total_items)

        Returns:
            List of fork data dictionaries from GitHub API

        Raises:
            ForkListProcessingError: If fork list processing fails
        """
        logger.info(f"Starting fork list data collection for {owner}/{repo}")
        start_time = time.time()

        try:
            all_forks_data: list[dict[str, Any]] = []
            page = 1
            per_page = 100  # Maximum allowed by GitHub API

            while True:
                logger.debug(f"Fetching forks page {page} for {owner}/{repo}")

                # Get raw API data directly to extract all qualification fields
                params = {"sort": "newest", "per_page": per_page, "page": page}
                raw_forks_data_response = await self.github_client.get(
                    f"repos/{owner}/{repo}/forks", params=params
                )
                # The forks endpoint returns a list, not a dict
                raw_forks_data: list[dict[str, Any]] = raw_forks_data_response  # type: ignore[assignment]

                if not raw_forks_data:
                    logger.debug(f"No more forks found at page {page}")
                    break

                all_forks_data.extend(raw_forks_data)

                # Call progress callback if provided
                if progress_callback:
                    progress_callback(page, len(all_forks_data))

                # If we got fewer than per_page, we're done
                if len(raw_forks_data) < per_page:
                    logger.debug(f"Reached end of forks at page {page}")
                    break

                page += 1

            processing_time = time.time() - start_time
            logger.info(
                f"Collected {len(all_forks_data)} forks in {processing_time:.2f}s "
                f"using {page} API calls"
            )

            return all_forks_data

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                f"Fork list processing failed after {processing_time:.2f}s: {e}"
            )
            raise ForkListProcessingError(
                f"Failed to process fork list for {owner}/{repo}: {e}"
            ) from e

    async def process_forks_pages(
        self,
        owner: str,
        repo: str,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Process all forks pages with progress tracking.

        This is an alias for get_all_forks_list_data with enhanced logging.

        Args:
            owner: Repository owner
            repo: Repository name
            progress_callback: Optional callback for progress updates

        Returns:
            List of fork data dictionaries from GitHub API
        """
        logger.info(f"Processing forks pages for {owner}/{repo}")
        return await self.get_all_forks_list_data(owner, repo, progress_callback)

    def extract_qualification_fields(self, fork_data: dict[str, Any]) -> dict[str, Any]:
        """
        Extract all available qualification metrics from fork list response.

        Extracts comprehensive fork information from the GitHub API response
        without making additional API calls.

        Args:
            fork_data: Raw fork data from GitHub API

        Returns:
            Dictionary with extracted qualification fields

        Raises:
            ForkListProcessingError: If required fields are missing
        """
        try:
            # Extract owner information
            owner_data = fork_data.get("owner", {})
            if not owner_data:
                raise ForkListProcessingError("Fork data missing owner information")

            # Extract license information
            license_data = fork_data.get("license", {})

            # Build qualification fields dictionary
            qualification_fields = {
                # Basic repository information
                "id": fork_data["id"],
                "name": fork_data["name"],
                "full_name": fork_data["full_name"],
                "owner": owner_data["login"],
                "html_url": fork_data["html_url"],
                # Community engagement metrics
                "stargazers_count": fork_data.get("stargazers_count", 0),
                "forks_count": fork_data.get("forks_count", 0),
                "watchers_count": fork_data.get("watchers_count", 0),
                # Development activity metrics
                "size": fork_data.get("size", 0),
                "language": fork_data.get("language"),
                "topics": fork_data.get("topics", []),
                "open_issues_count": fork_data.get("open_issues_count", 0),
                # Activity timeline metrics
                "created_at": fork_data["created_at"],
                "updated_at": fork_data["updated_at"],
                "pushed_at": fork_data["pushed_at"],
                # Repository status
                "archived": fork_data.get("archived", False),
                "disabled": fork_data.get("disabled", False),
                "fork": fork_data.get("fork", True),
                # License information
                "license_key": license_data.get("key") if license_data else None,
                "license_name": license_data.get("name") if license_data else None,
                # Additional metadata
                "description": fork_data.get("description"),
                "homepage": fork_data.get("homepage"),
                "default_branch": fork_data.get("default_branch", "main"),
            }

            logger.debug(
                f"Extracted qualification fields for {qualification_fields['full_name']}"
            )
            return qualification_fields

        except KeyError as e:
            raise ForkListProcessingError(
                f"Missing required field in fork data: {e}"
            ) from e
        except Exception as e:
            raise ForkListProcessingError(
                f"Failed to extract qualification fields: {e}"
            ) from e

    def validate_fork_data_completeness(self, fork_data: dict[str, Any]) -> bool:
        """
        Validate fork data completeness for handling missing data gracefully.

        Checks if the fork data contains all required fields for processing.
        Handles missing data gracefully by returning validation status.

        Args:
            fork_data: Raw fork data from GitHub API

        Returns:
            True if data is complete enough for processing, False otherwise
        """
        try:
            # Required fields that must be present
            required_fields = [
                "id",
                "name",
                "full_name",
                "html_url",
                "created_at",
                "updated_at",
                "pushed_at",
                "owner",
            ]

            # Check for required fields
            for field in required_fields:
                if field == "owner":
                    # Owner is a nested object
                    owner_data = fork_data.get("owner", {})
                    if not owner_data or "login" not in owner_data:
                        logger.warning(
                            f"Fork data missing owner.login field: {fork_data.get('full_name', 'unknown')}"
                        )
                        return False
                else:
                    if field not in fork_data or fork_data[field] is None:
                        logger.warning(
                            f"Fork data missing required field '{field}': {fork_data.get('full_name', 'unknown')}"
                        )
                        return False

            # Validate timestamp format (basic check)
            timestamp_fields = ["created_at", "updated_at", "pushed_at"]
            for field in timestamp_fields:
                timestamp = fork_data.get(field)
                if timestamp and not isinstance(timestamp, str):
                    logger.warning(
                        f"Fork data has invalid timestamp format for '{field}': {fork_data.get('full_name', 'unknown')}"
                    )
                    return False

            # Validate numeric fields
            numeric_fields = [
                "id",
                "stargazers_count",
                "forks_count",
                "watchers_count",
                "size",
                "open_issues_count",
            ]
            for field in numeric_fields:
                value = fork_data.get(field)
                if value is not None and not isinstance(value, int):
                    logger.warning(
                        f"Fork data has invalid numeric value for '{field}': {fork_data.get('full_name', 'unknown')}"
                    )
                    return False

            logger.debug(
                f"Fork data validation passed for {fork_data.get('full_name', 'unknown')}"
            )
            return True

        except Exception as e:
            fork_name = "unknown"
            try:
                if fork_data and hasattr(fork_data, "get"):
                    fork_name = fork_data.get("full_name", "unknown")
            except Exception:
                pass
            logger.error(f"Fork data validation failed: {e} for {fork_name}")
            return False

    async def collect_and_process_forks(
        self,
        owner: str,
        repo: str,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> QualifiedForksResult:
        """
        Collect and process all forks for a repository.

        Combines fork list collection, data extraction, and qualification
        into a single comprehensive operation.

        Args:
            owner: Repository owner
            repo: Repository name
            progress_callback: Optional callback for progress updates

        Returns:
            Complete qualified forks result with statistics

        Raises:
            ForkListProcessingError: If processing fails
        """
        logger.info(f"Starting comprehensive fork collection for {owner}/{repo}")
        start_time = time.time()

        try:
            # Collect all forks data
            all_forks_data = await self.get_all_forks_list_data(
                owner, repo, progress_callback
            )

            # Process each fork
            collected_forks = []
            valid_forks = 0
            invalid_forks = 0
            forks_with_no_commits = 0
            forks_with_commits = 0
            archived_forks = 0
            disabled_forks = 0

            for fork_data in all_forks_data:
                # Validate data completeness
                if not self.validate_fork_data_completeness(fork_data):
                    invalid_forks += 1
                    logger.warning(
                        f"Skipping invalid fork data: {fork_data.get('full_name', 'unknown')}"
                    )
                    continue

                valid_forks += 1

                # Create qualification metrics
                metrics = ForkQualificationMetrics.from_github_api(fork_data)

                # Create collected fork data
                collected_fork = CollectedForkData(metrics=metrics)
                collected_forks.append(collected_fork)

                # Update statistics
                if metrics.can_skip_analysis:
                    forks_with_no_commits += 1
                else:
                    forks_with_commits += 1

                if metrics.archived:
                    archived_forks += 1

                if metrics.disabled:
                    disabled_forks += 1

            # Calculate processing statistics
            processing_time = time.time() - start_time
            total_forks = len(all_forks_data)
            api_calls_made = len(all_forks_data) // 100 + (
                1 if len(all_forks_data) % 100 > 0 else 0
            )

            # Estimate API calls saved (compared to individual repository calls)
            api_calls_saved = total_forks  # Each fork would need individual API call

            # Create statistics
            stats = QualificationStats(
                total_forks_discovered=total_forks,
                forks_with_no_commits=forks_with_no_commits,
                forks_with_commits=forks_with_commits,
                archived_forks=archived_forks,
                disabled_forks=disabled_forks,
                api_calls_made=api_calls_made,
                api_calls_saved=api_calls_saved,
                processing_time_seconds=processing_time,
            )

            # Create result
            result = QualifiedForksResult(
                repository_owner=owner,
                repository_name=repo,
                repository_url=f"https://github.com/{owner}/{repo}",
                collected_forks=collected_forks,
                stats=stats,
            )

            logger.info(
                f"Fork collection completed: {total_forks} total, "
                f"{valid_forks} valid, {invalid_forks} invalid, "
                f"{forks_with_commits} need analysis, {forks_with_no_commits} can skip"
            )

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                f"Fork collection and processing failed after {processing_time:.2f}s: {e}"
            )
            raise ForkListProcessingError(
                f"Failed to collect and process forks for {owner}/{repo}: {e}"
            ) from e
