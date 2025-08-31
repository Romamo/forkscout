"""Commit status classification system for fork categorization."""

import logging
from datetime import UTC, datetime

from src.forklift.analysis.timestamp_analyzer import TimestampAnalyzer
from src.forklift.models.commits_ahead_detection import (
    CommitDetectionResult,
    CommitStatus,
    ForkQualification,
    TimestampAnalysisResult,
)

logger = logging.getLogger(__name__)


class CommitStatusClassifier:
    """
    Classifies forks based on timestamp analysis with confidence thresholds.

    Provides status assignment logic, confidence-based filtering, and
    persistence mechanisms for fork qualification data.
    """

    def __init__(
        self,
        timestamp_analyzer: TimestampAnalyzer | None = None,
        high_confidence_threshold: float = 0.9,
        medium_confidence_threshold: float = 0.7,
        low_confidence_threshold: float = 0.3,
    ):
        """
        Initialize CommitStatusClassifier.

        Args:
            timestamp_analyzer: Optional TimestampAnalyzer instance
            high_confidence_threshold: Minimum score for high confidence classification
            medium_confidence_threshold: Minimum score for medium confidence classification
            low_confidence_threshold: Minimum score for low confidence classification
        """
        self.timestamp_analyzer = timestamp_analyzer or TimestampAnalyzer()
        self.high_confidence_threshold = high_confidence_threshold
        self.medium_confidence_threshold = medium_confidence_threshold
        self.low_confidence_threshold = low_confidence_threshold

        # In-memory storage for classified forks (could be replaced with persistent storage)
        self._classified_forks: dict[str, ForkQualification] = {}

    def classify_fork(
        self,
        fork_url: str,
        owner: str,
        name: str,
        created_at: datetime,
        pushed_at: datetime,
        force_reclassify: bool = False,
    ) -> ForkQualification:
        """
        Classify a single fork based on timestamp analysis.

        Args:
            fork_url: Fork repository URL
            owner: Fork owner username
            name: Fork repository name
            created_at: Repository creation timestamp
            pushed_at: Last push timestamp
            force_reclassify: Force reclassification even if already classified

        Returns:
            ForkQualification with status and confidence information
        """
        # Check if already classified and not forcing reclassification
        if not force_reclassify and fork_url in self._classified_forks:
            existing = self._classified_forks[fork_url]
            logger.debug(
                f"Using existing classification for {fork_url}: {existing.commit_status.value}"
            )
            return existing

        # Perform timestamp analysis
        analysis_result = self.timestamp_analyzer.analyze_timestamps(
            created_at, pushed_at, fork_url
        )

        # Assign status based on analysis and confidence thresholds
        final_status = self._assign_status_with_confidence(analysis_result)

        # Create fork qualification
        qualification = ForkQualification(
            fork_url=fork_url,
            owner=owner,
            name=name,
            created_at=created_at,
            pushed_at=pushed_at,
            commit_status=final_status,
            confidence_score=analysis_result.confidence_score,
            verification_method="timestamp_analysis",
            last_verified=datetime.now(UTC),
            commits_ahead_count=None,  # Not determined by timestamp analysis
        )

        # Store classification
        self._classified_forks[fork_url] = qualification

        logger.debug(
            f"Classified {fork_url}: status={final_status.value}, "
            f"confidence={analysis_result.confidence_score:.2f}"
        )

        return qualification

    def classify_batch(
        self,
        fork_data: list[dict[str, any]],
        force_reclassify: bool = False,
    ) -> list[ForkQualification]:
        """
        Classify multiple forks in batch.

        Args:
            fork_data: List of fork data dictionaries with required fields
            force_reclassify: Force reclassification of existing entries

        Returns:
            List of ForkQualification objects
        """
        logger.info(f"Starting batch classification of {len(fork_data)} forks")

        results = []

        for fork_info in fork_data:
            try:
                qualification = self.classify_fork(
                    fork_url=fork_info["fork_url"],
                    owner=fork_info["owner"],
                    name=fork_info["name"],
                    created_at=fork_info["created_at"],
                    pushed_at=fork_info["pushed_at"],
                    force_reclassify=force_reclassify,
                )
                results.append(qualification)

            except Exception as e:
                logger.error(
                    f"Error classifying fork {fork_info.get('fork_url', 'unknown')}: {e}"
                )
                # Create error qualification
                error_qualification = ForkQualification(
                    fork_url=fork_info.get("fork_url", "unknown"),
                    owner=fork_info.get("owner", "unknown"),
                    name=fork_info.get("name", "unknown"),
                    created_at=fork_info.get("created_at", datetime.now(UTC)),
                    pushed_at=fork_info.get("pushed_at", datetime.now(UTC)),
                    commit_status=CommitStatus.UNKNOWN,
                    confidence_score=0.0,
                    verification_method="error",
                    last_verified=datetime.now(UTC),
                )
                results.append(error_qualification)

        logger.info(f"Completed batch classification: {len(results)} results")
        return results

    def _assign_status_with_confidence(
        self, analysis_result: TimestampAnalysisResult
    ) -> CommitStatus:
        """
        Assign final status based on analysis result and confidence thresholds.

        Args:
            analysis_result: Result from timestamp analysis

        Returns:
            Final CommitStatus based on confidence thresholds
        """
        base_status = analysis_result.status
        confidence = analysis_result.confidence_score

        # High confidence: use the determined status
        if (
            confidence >= self.high_confidence_threshold
            or confidence >= self.medium_confidence_threshold
        ):
            return base_status

        # Low confidence: mark as unknown for verification
        elif confidence >= self.low_confidence_threshold:
            if base_status in [CommitStatus.HAS_COMMITS, CommitStatus.NO_COMMITS]:
                return CommitStatus.UNKNOWN
            else:
                return base_status

        # Very low confidence: always unknown
        else:
            return CommitStatus.UNKNOWN

    def get_forks_by_status(self, status: CommitStatus) -> list[ForkQualification]:
        """
        Get all classified forks with a specific status.

        Args:
            status: CommitStatus to filter by

        Returns:
            List of ForkQualification objects with the specified status
        """
        return [
            qualification
            for qualification in self._classified_forks.values()
            if qualification.commit_status == status
        ]

    def get_forks_by_confidence(
        self, min_confidence: float, max_confidence: float = 1.0
    ) -> list[ForkQualification]:
        """
        Get classified forks within a confidence range.

        Args:
            min_confidence: Minimum confidence score (inclusive)
            max_confidence: Maximum confidence score (inclusive)

        Returns:
            List of ForkQualification objects within confidence range
        """
        return [
            qualification
            for qualification in self._classified_forks.values()
            if min_confidence <= qualification.confidence_score <= max_confidence
        ]

    def get_forks_needing_verification(self) -> list[ForkQualification]:
        """
        Get forks that need API verification based on confidence and status.

        Returns:
            List of ForkQualification objects needing verification
        """
        return [
            qualification
            for qualification in self._classified_forks.values()
            if (
                qualification.commit_status == CommitStatus.UNKNOWN
                or qualification.confidence_score < self.medium_confidence_threshold
            )
        ]

    def update_fork_status(
        self,
        fork_url: str,
        new_status: CommitStatus,
        verification_method: str = "manual_update",
        commits_ahead_count: int | None = None,
    ) -> bool:
        """
        Update the status of a previously classified fork.

        Args:
            fork_url: Fork repository URL
            new_status: New CommitStatus
            verification_method: Method used for verification
            commits_ahead_count: Actual commits ahead count if known

        Returns:
            True if update was successful, False if fork not found
        """
        if fork_url not in self._classified_forks:
            logger.warning(f"Cannot update status for unknown fork: {fork_url}")
            return False

        qualification = self._classified_forks[fork_url]

        # Update status and verification info
        qualification.commit_status = new_status
        qualification.verification_method = verification_method
        qualification.last_verified = datetime.now(UTC)
        qualification.commits_ahead_count = commits_ahead_count

        # Update confidence based on verification
        if verification_method.startswith("api_"):
            qualification.confidence_score = 1.0  # API verification is definitive

        logger.info(
            f"Updated fork status: {fork_url} -> {new_status.value} "
            f"(method: {verification_method})"
        )

        return True

    def get_classification_summary(self) -> CommitDetectionResult:
        """
        Generate summary statistics for all classified forks.

        Returns:
            CommitDetectionResult with classification statistics
        """
        total_forks = len(self._classified_forks)

        if total_forks == 0:
            return CommitDetectionResult(
                total_forks=0,
                has_commits=0,
                no_commits=0,
                unknown_status=0,
                api_calls_saved=0,
                processing_time=0.0,
                confidence_distribution={},
            )

        # Count status distribution
        status_counts = {
            CommitStatus.HAS_COMMITS: 0,
            CommitStatus.NO_COMMITS: 0,
            CommitStatus.UNKNOWN: 0,
            CommitStatus.VERIFIED_AHEAD: 0,
            CommitStatus.VERIFIED_NONE: 0,
        }

        # Count confidence distribution
        confidence_counts = {"high": 0, "medium": 0, "low": 0}

        for qualification in self._classified_forks.values():
            status_counts[qualification.commit_status] += 1

            # Categorize confidence
            if qualification.confidence_score >= self.high_confidence_threshold:
                confidence_counts["high"] += 1
            elif qualification.confidence_score >= self.medium_confidence_threshold:
                confidence_counts["medium"] += 1
            else:
                confidence_counts["low"] += 1

        # Calculate API calls saved (forks with high confidence don't need verification)
        high_confidence_forks = confidence_counts["high"]
        api_calls_saved = high_confidence_forks

        return CommitDetectionResult(
            total_forks=total_forks,
            has_commits=status_counts[CommitStatus.HAS_COMMITS]
            + status_counts[CommitStatus.VERIFIED_AHEAD],
            no_commits=status_counts[CommitStatus.NO_COMMITS]
            + status_counts[CommitStatus.VERIFIED_NONE],
            unknown_status=status_counts[CommitStatus.UNKNOWN],
            api_calls_saved=api_calls_saved,
            processing_time=0.0,  # Would need to track actual processing time
            confidence_distribution=confidence_counts,
        )

    def clear_classifications(self) -> None:
        """Clear all stored classifications."""
        self._classified_forks.clear()
        logger.info("Cleared all fork classifications")

    def get_classification_count(self) -> int:
        """Get the number of classified forks."""
        return len(self._classified_forks)

    def has_classification(self, fork_url: str) -> bool:
        """Check if a fork has been classified."""
        return fork_url in self._classified_forks

    def get_classification(self, fork_url: str) -> ForkQualification | None:
        """Get classification for a specific fork."""
        return self._classified_forks.get(fork_url)

    def export_classifications(self) -> list[dict[str, any]]:
        """
        Export all classifications as a list of dictionaries.

        Returns:
            List of dictionaries containing classification data
        """
        return [
            {
                "fork_url": q.fork_url,
                "owner": q.owner,
                "name": q.name,
                "created_at": q.created_at.isoformat(),
                "pushed_at": q.pushed_at.isoformat(),
                "commit_status": q.commit_status.value,
                "confidence_score": q.confidence_score,
                "verification_method": q.verification_method,
                "last_verified": (
                    q.last_verified.isoformat() if q.last_verified else None
                ),
                "commits_ahead_count": q.commits_ahead_count,
            }
            for q in self._classified_forks.values()
        ]

    def import_classifications(self, classifications_data: list[dict[str, any]]) -> int:
        """
        Import classifications from a list of dictionaries.

        Args:
            classifications_data: List of dictionaries containing classification data

        Returns:
            Number of classifications imported
        """
        imported_count = 0

        for data in classifications_data:
            try:
                qualification = ForkQualification(
                    fork_url=data["fork_url"],
                    owner=data["owner"],
                    name=data["name"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    pushed_at=datetime.fromisoformat(data["pushed_at"]),
                    commit_status=CommitStatus(data["commit_status"]),
                    confidence_score=data["confidence_score"],
                    verification_method=data["verification_method"],
                    last_verified=(
                        datetime.fromisoformat(data["last_verified"])
                        if data.get("last_verified")
                        else None
                    ),
                    commits_ahead_count=data.get("commits_ahead_count"),
                )

                self._classified_forks[qualification.fork_url] = qualification
                imported_count += 1

            except Exception as e:
                logger.error(
                    f"Error importing classification for {data.get('fork_url', 'unknown')}: {e}"
                )

        logger.info(f"Imported {imported_count} fork classifications")
        return imported_count
