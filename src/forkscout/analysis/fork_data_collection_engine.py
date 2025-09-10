"""Fork data collection engine for comprehensive fork data collection and organization."""

import logging
import time
from datetime import datetime
from typing import Any

from forkscout.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualificationStats,
    QualifiedForksResult,
)
from forkscout.models.github import Repository
from forkscout.models.validation_handler import ValidationHandler, ValidationSummary

logger = logging.getLogger(__name__)


class ForkDataCollectionError(Exception):
    """Raised when fork data collection fails."""

    pass


class ForkDataCollectionEngine:
    """Engine for collecting and organizing fork data without scoring or filtering."""

    def __init__(self) -> None:
        """Initialize fork data collection engine."""
        pass

    def collect_fork_data(
        self, forks: list[dict[str, Any]]
    ) -> tuple[list[Repository], ValidationSummary]:
        """
        Collect fork data with graceful validation handling.

        This method processes a list of fork data from the GitHub API and creates
        Repository objects while handling validation errors gracefully. Individual
        validation failures do not stop the entire process.

        Args:
            forks: List of fork data dictionaries from GitHub API

        Returns:
            Tuple containing:
            - List of successfully created Repository objects
            - ValidationSummary with processing statistics and error details

        Requirements: 1.2, 1.3, 4.1, 4.2
        """
        logger.info(
            f"Collecting fork data from {len(forks)} forks with graceful validation"
        )
        start_time = time.time()

        # Initialize validation handler
        validation_handler = ValidationHandler()
        valid_repositories = []

        try:
            for fork_data in forks:
                # Attempt to create Repository with graceful error handling
                repository = validation_handler.safe_create_repository(fork_data)
                if repository:
                    valid_repositories.append(repository)
                    validation_handler.processed_count += 1

            # Log processing summary
            processing_time = time.time() - start_time
            validation_handler.log_summary()

            logger.info(
                f"Fork data collection completed in {processing_time:.2f}s: "
                f"{validation_handler.processed_count} successful, "
                f"{validation_handler.skipped_count} skipped"
            )

            return valid_repositories, validation_handler.get_summary()

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                f"Fork data collection failed after {processing_time:.2f}s: {e}",
                exc_info=True,
            )
            raise ForkDataCollectionError(f"Failed to collect fork data: {e}") from e

    def collect_fork_data_from_list(
        self, forks_list_data: list[dict[str, Any]]
    ) -> list[CollectedForkData]:
        """
        Extract and organize all qualification metrics without scoring or filtering.

        Args:
            forks_list_data: Raw fork data from GitHub API forks list

        Returns:
            List of collected fork data with qualification metrics

        Raises:
            ForkDataCollectionError: If data collection fails
        """
        logger.info(f"Collecting fork data from {len(forks_list_data)} forks")
        start_time = time.time()

        try:
            collected_forks = []

            for fork_data in forks_list_data:
                try:
                    # Extract fork metrics from GitHub API data
                    metrics = self.extract_fork_metrics(fork_data)

                    # Create collected fork data
                    collected_fork = CollectedForkData(metrics=metrics)
                    collected_forks.append(collected_fork)

                    logger.debug(
                        f"Collected data for fork: {metrics.full_name} "
                        f"({metrics.commits_ahead_status})"
                    )

                except Exception as e:
                    fork_name = "unknown"
                    try:
                        if fork_data and hasattr(fork_data, "get"):
                            fork_name = fork_data.get("full_name", "unknown")
                    except Exception:
                        pass
                    logger.warning(f"Failed to collect data for fork {fork_name}: {e}")
                    continue

            processing_time = time.time() - start_time
            logger.info(
                f"Collected data for {len(collected_forks)} forks in {processing_time:.2f}s"
            )

            return collected_forks

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                f"Fork data collection failed after {processing_time:.2f}s: {e}"
            )
            raise ForkDataCollectionError(f"Failed to collect fork data: {e}") from e

    def extract_fork_metrics(
        self, fork_data: dict[str, Any]
    ) -> ForkQualificationMetrics:
        """
        Extract fork qualification metrics from GitHub API fork data.

        Args:
            fork_data: Raw fork data from GitHub API

        Returns:
            Fork qualification metrics

        Raises:
            ForkDataCollectionError: If metric extraction fails
        """
        try:
            # Use the existing from_github_api method
            return ForkQualificationMetrics.from_github_api(fork_data)

        except Exception as e:
            fork_name = "unknown"
            try:
                if fork_data and hasattr(fork_data, "get"):
                    fork_name = fork_data.get("full_name", "unknown")
            except Exception:
                pass
            raise ForkDataCollectionError(
                f"Failed to extract metrics for fork {fork_name}: {e}"
            ) from e

    def calculate_activity_patterns(self, fork_data: dict[str, Any]) -> dict[str, Any]:
        """
        Calculate activity patterns (days since creation, last update, last push).

        Args:
            fork_data: Raw fork data from GitHub API

        Returns:
            Dictionary with activity pattern calculations

        Raises:
            ForkDataCollectionError: If activity calculation fails
        """
        try:
            # Parse timestamps
            created_at = datetime.fromisoformat(
                fork_data["created_at"].replace("Z", "+00:00")
            )
            updated_at = datetime.fromisoformat(
                fork_data["updated_at"].replace("Z", "+00:00")
            )
            pushed_at = datetime.fromisoformat(
                fork_data["pushed_at"].replace("Z", "+00:00")
            )

            # Calculate days since each event
            now = (
                datetime.now(created_at.tzinfo)
                if created_at.tzinfo
                else datetime.utcnow()
            )
            days_since_creation = (now - created_at).days
            days_since_last_update = (now - updated_at).days
            days_since_last_push = (now - pushed_at).days

            # Calculate activity ratio
            total_days = days_since_creation
            if total_days == 0:
                activity_ratio = 1.0
            else:
                days_active = total_days - days_since_last_push
                activity_ratio = max(0.0, min(1.0, days_active / total_days))

            return {
                "days_since_creation": days_since_creation,
                "days_since_last_update": days_since_last_update,
                "days_since_last_push": days_since_last_push,
                "activity_ratio": activity_ratio,
                "created_at": created_at,
                "updated_at": updated_at,
                "pushed_at": pushed_at,
            }

        except Exception as e:
            fork_name = "unknown"
            try:
                if fork_data and hasattr(fork_data, "get"):
                    fork_name = fork_data.get("full_name", "unknown")
            except Exception:
                pass
            raise ForkDataCollectionError(
                f"Failed to calculate activity patterns for fork {fork_name}: {e}"
            ) from e

    def determine_commits_ahead_status(
        self, fork_data: dict[str, Any]
    ) -> tuple[str, bool]:
        """
        Determine commits ahead status using created_at >= pushed_at comparison logic.

        Args:
            fork_data: Raw fork data from GitHub API

        Returns:
            Tuple of (status_string, can_skip_analysis)
            - status_string: "No commits ahead" or "Has commits"
            - can_skip_analysis: True if fork can be skipped from detailed analysis

        Raises:
            ForkDataCollectionError: If status determination fails
        """
        try:
            # Parse timestamps
            created_at = datetime.fromisoformat(
                fork_data["created_at"].replace("Z", "+00:00")
            )
            pushed_at = datetime.fromisoformat(
                fork_data["pushed_at"].replace("Z", "+00:00")
            )

            # Apply the created_at >= pushed_at logic
            if created_at >= pushed_at:
                status = "No commits ahead"
                can_skip = True
                logger.debug(
                    f"Fork {fork_data.get('full_name', 'unknown')} has no commits ahead "
                    f"(created: {created_at}, pushed: {pushed_at})"
                )
            else:
                status = "Has commits"
                can_skip = False
                logger.debug(
                    f"Fork {fork_data.get('full_name', 'unknown')} has commits "
                    f"(created: {created_at}, pushed: {pushed_at})"
                )

            return status, can_skip

        except Exception as e:
            fork_name = "unknown"
            try:
                if fork_data and hasattr(fork_data, "get"):
                    fork_name = fork_data.get("full_name", "unknown")
            except Exception:
                pass
            raise ForkDataCollectionError(
                f"Failed to determine commits ahead status for fork {fork_name}: {e}"
            ) from e

    def generate_activity_summary(self, metrics: ForkQualificationMetrics) -> str:
        """
        Generate human-readable activity summary for fork metrics.

        Args:
            metrics: Fork qualification metrics

        Returns:
            Human-readable activity summary string
        """
        days_since_push = metrics.days_since_last_push

        if days_since_push <= 7:
            return "Very Active (< 1 week)"
        elif days_since_push <= 30:
            return "Active (< 1 month)"
        elif days_since_push <= 90:
            return "Moderately Active (< 3 months)"
        elif days_since_push <= 365:
            return "Low Activity (< 1 year)"
        else:
            return "Inactive (> 1 year)"

    def exclude_archived_and_disabled(
        self, collected_forks: list[CollectedForkData]
    ) -> list[CollectedForkData]:
        """
        Exclude archived and disabled forks from the collection.

        Args:
            collected_forks: List of collected fork data

        Returns:
            List of collected fork data excluding archived and disabled forks
        """
        logger.info(
            f"Filtering out archived and disabled forks from {len(collected_forks)} forks"
        )

        filtered_forks = []
        archived_count = 0
        disabled_count = 0

        for fork_data in collected_forks:
            if fork_data.metrics.archived:
                archived_count += 1
                logger.debug(f"Excluding archived fork: {fork_data.metrics.full_name}")
                continue

            if fork_data.metrics.disabled:
                disabled_count += 1
                logger.debug(f"Excluding disabled fork: {fork_data.metrics.full_name}")
                continue

            filtered_forks.append(fork_data)

        logger.info(
            f"Excluded {archived_count} archived and {disabled_count} disabled forks. "
            f"Remaining: {len(filtered_forks)} forks"
        )

        return filtered_forks

    def exclude_no_commits_ahead(
        self, collected_forks: list[CollectedForkData]
    ) -> list[CollectedForkData]:
        """
        Exclude forks with no commits ahead from the collection.

        Args:
            collected_forks: List of collected fork data

        Returns:
            List of collected fork data excluding forks with no commits ahead
        """
        logger.info(
            f"Filtering out forks with no commits ahead from {len(collected_forks)} forks"
        )

        filtered_forks = []
        no_commits_count = 0

        for fork_data in collected_forks:
            if fork_data.metrics.can_skip_analysis:
                no_commits_count += 1
                logger.debug(
                    f"Excluding fork with no commits ahead: {fork_data.metrics.full_name}"
                )
                continue

            filtered_forks.append(fork_data)

        logger.info(
            f"Excluded {no_commits_count} forks with no commits ahead. "
            f"Remaining: {len(filtered_forks)} forks"
        )

        return filtered_forks

    def organize_forks_by_status(
        self, collected_forks: list[CollectedForkData]
    ) -> tuple[
        list[CollectedForkData], list[CollectedForkData], list[CollectedForkData]
    ]:
        """
        Organize forks by status: active, archived/disabled, no commits ahead.

        Args:
            collected_forks: List of collected fork data

        Returns:
            Tuple of (active_forks, archived_disabled_forks, no_commits_forks)
        """
        logger.info(f"Organizing {len(collected_forks)} forks by status")

        active_forks = []
        archived_disabled_forks = []
        no_commits_forks = []

        for fork_data in collected_forks:
            metrics = fork_data.metrics

            # Check if fork has no commits ahead
            if metrics.can_skip_analysis:
                no_commits_forks.append(fork_data)
                continue

            # Check if fork is archived or disabled
            if metrics.archived or metrics.disabled:
                archived_disabled_forks.append(fork_data)
                continue

            # Otherwise, it's an active fork
            active_forks.append(fork_data)

        logger.info(
            f"Organized forks: {len(active_forks)} active, "
            f"{len(archived_disabled_forks)} archived/disabled, "
            f"{len(no_commits_forks)} no commits ahead"
        )

        return active_forks, archived_disabled_forks, no_commits_forks

    def create_qualification_result(
        self,
        repository_owner: str,
        repository_name: str,
        collected_forks: list[CollectedForkData],
        processing_time_seconds: float,
        api_calls_made: int = 0,
        api_calls_saved: int = 0,
    ) -> QualifiedForksResult:
        """
        Create a qualified forks result from collected fork data.

        Args:
            repository_owner: Repository owner
            repository_name: Repository name
            collected_forks: List of collected fork data
            processing_time_seconds: Time taken for processing
            api_calls_made: Number of API calls made
            api_calls_saved: Number of API calls saved

        Returns:
            Complete qualified forks result with statistics
        """
        logger.info(
            f"Creating qualification result for {repository_owner}/{repository_name}"
        )

        # Calculate statistics
        total_forks = len(collected_forks)
        forks_with_no_commits = sum(
            1 for fork in collected_forks if fork.metrics.can_skip_analysis
        )
        forks_with_commits = total_forks - forks_with_no_commits
        archived_forks = sum(1 for fork in collected_forks if fork.metrics.archived)
        disabled_forks = sum(1 for fork in collected_forks if fork.metrics.disabled)

        # Create statistics
        stats = QualificationStats(
            total_forks_discovered=total_forks,
            forks_with_no_commits=forks_with_no_commits,
            forks_with_commits=forks_with_commits,
            archived_forks=archived_forks,
            disabled_forks=disabled_forks,
            api_calls_made=api_calls_made,
            api_calls_saved=api_calls_saved,
            processing_time_seconds=processing_time_seconds,
        )

        # Create result
        result = QualifiedForksResult(
            repository_owner=repository_owner,
            repository_name=repository_name,
            repository_url=f"https://github.com/{repository_owner}/{repository_name}",
            collected_forks=collected_forks,
            stats=stats,
        )

        logger.info(
            f"Created qualification result: {total_forks} total forks, "
            f"{forks_with_commits} need analysis, {forks_with_no_commits} can skip"
        )

        return result
