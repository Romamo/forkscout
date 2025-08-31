"""Timestamp-based heuristic engine for commits ahead detection."""

import logging
from datetime import UTC, datetime

from src.forklift.models.commits_ahead_detection import (
    CommitStatus,
    TimestampAnalysisResult,
)

logger = logging.getLogger(__name__)


class TimestampAnalyzer:
    """
    Analyzes fork timestamps to determine if commits are ahead of upstream.

    Uses heuristic analysis of created_at and pushed_at timestamps to classify
    forks without expensive API calls. Provides confidence scoring based on
    timestamp differences and data quality.
    """

    def __init__(
        self,
        high_confidence_threshold: float = 0.9,
        medium_confidence_threshold: float = 0.7,
        same_timestamp_tolerance_seconds: int = 60,
    ):
        """
        Initialize TimestampAnalyzer with configuration.

        Args:
            high_confidence_threshold: Minimum score for high confidence classification
            medium_confidence_threshold: Minimum score for medium confidence classification
            same_timestamp_tolerance_seconds: Tolerance for considering timestamps "same"
        """
        self.high_confidence_threshold = high_confidence_threshold
        self.medium_confidence_threshold = medium_confidence_threshold
        self.same_timestamp_tolerance_seconds = same_timestamp_tolerance_seconds

    def analyze_timestamps(
        self, created_at: datetime, pushed_at: datetime, fork_url: str | None = None
    ) -> TimestampAnalysisResult:
        """
        Analyze fork timestamps to determine commit status.

        Args:
            created_at: Repository creation timestamp
            pushed_at: Last push timestamp
            fork_url: Optional fork URL for logging context

        Returns:
            TimestampAnalysisResult with status, confidence, and analysis notes
        """
        logger.debug(
            f"Analyzing timestamps for {fork_url or 'fork'}: "
            f"created={created_at}, pushed={pushed_at}"
        )

        # Handle missing or invalid timestamps
        if not created_at or not pushed_at:
            return self._handle_missing_timestamps(created_at, pushed_at, fork_url)

        # Normalize timestamps to UTC for comparison
        created_utc = self._normalize_to_utc(created_at)
        pushed_utc = self._normalize_to_utc(pushed_at)

        # Calculate time difference
        time_diff = pushed_utc - created_utc
        time_diff_days = time_diff.days
        time_diff_seconds = abs(time_diff.total_seconds())

        # Determine status and confidence based on timestamp relationship
        if time_diff_seconds <= self.same_timestamp_tolerance_seconds:
            # Timestamps are essentially the same
            status = CommitStatus.NO_COMMITS
            confidence = self._calculate_same_timestamp_confidence(time_diff_seconds)
            notes = (
                f"created_at and pushed_at are within {time_diff_seconds:.0f} seconds"
            )

        elif pushed_utc < created_utc:
            # Push is before creation - unusual but indicates no new commits
            status = CommitStatus.NO_COMMITS
            confidence = 0.95  # High confidence - this is a clear indicator
            notes = f"pushed_at is {abs(time_diff_days)} days before created_at"

        elif time_diff_days == 0:
            # Same day but pushed after creation
            status = CommitStatus.UNKNOWN
            confidence = self._calculate_same_day_confidence(time_diff_seconds)
            notes = f"pushed_at is {time_diff_seconds/3600:.1f} hours after created_at on same day"

        elif time_diff_days > 0:
            # Push is after creation by multiple days
            status = CommitStatus.HAS_COMMITS
            confidence = self._calculate_multi_day_confidence(time_diff_days)
            notes = f"pushed_at is {time_diff_days} days after created_at"

        else:
            # Fallback for edge cases
            status = CommitStatus.UNKNOWN
            confidence = 0.5
            notes = (
                f"Ambiguous timestamp relationship: {time_diff_days} days difference"
            )

        logger.debug(
            f"Timestamp analysis result for {fork_url or 'fork'}: "
            f"status={status.value}, confidence={confidence:.2f}, notes={notes}"
        )

        return TimestampAnalysisResult(
            created_at=created_utc,
            pushed_at=pushed_utc,
            status=status,
            confidence_score=confidence,
            time_difference_days=time_diff_days,
            analysis_notes=notes,
        )

    def _handle_missing_timestamps(
        self,
        created_at: datetime | None,
        pushed_at: datetime | None,
        fork_url: str | None,
    ) -> TimestampAnalysisResult:
        """Handle cases where timestamps are missing or invalid."""
        now = datetime.now(UTC)

        if not created_at and not pushed_at:
            notes = "Both created_at and pushed_at are missing"
            confidence = 0.0
        elif not created_at:
            notes = "created_at is missing"
            confidence = 0.1
            created_at = now  # Use current time as fallback
        elif not pushed_at:
            notes = "pushed_at is missing"
            confidence = 0.1
            pushed_at = now  # Use current time as fallback
        else:
            notes = "Invalid timestamp data"
            confidence = 0.0

        logger.warning(f"Missing timestamp data for {fork_url or 'fork'}: {notes}")

        return TimestampAnalysisResult(
            created_at=created_at or now,
            pushed_at=pushed_at or now,
            status=CommitStatus.UNKNOWN,
            confidence_score=confidence,
            time_difference_days=0,
            analysis_notes=notes,
        )

    def _normalize_to_utc(self, dt: datetime) -> datetime:
        """Normalize datetime to UTC timezone."""
        if dt.tzinfo is None:
            # Assume naive datetime is UTC
            return dt.replace(tzinfo=UTC)
        elif dt.tzinfo != UTC:
            # Convert to UTC
            return dt.astimezone(UTC)
        else:
            # Already UTC
            return dt

    def _calculate_same_timestamp_confidence(self, time_diff_seconds: float) -> float:
        """Calculate confidence for timestamps that are essentially the same."""
        if time_diff_seconds == 0:
            return 0.95  # Very high confidence for exact match
        elif time_diff_seconds <= 10:
            return 0.9  # High confidence for very close timestamps
        elif time_diff_seconds <= 30:
            return 0.85  # Good confidence for close timestamps
        else:
            return 0.8  # Moderate confidence within tolerance

    def _calculate_same_day_confidence(self, time_diff_seconds: float) -> float:
        """Calculate confidence for same-day timestamp differences."""
        hours_diff = time_diff_seconds / 3600

        if hours_diff < 1:
            return 0.3  # Low confidence - could be initial commit
        elif hours_diff < 6:
            return 0.4  # Slightly higher - some development time
        elif hours_diff < 12:
            return 0.5  # Medium - half day of work
        else:
            return 0.6  # Higher - full day suggests some commits

    def _calculate_multi_day_confidence(self, time_diff_days: int) -> float:
        """Calculate confidence for multi-day timestamp differences."""
        if time_diff_days == 1:
            return 0.7  # Good confidence - likely has commits
        elif time_diff_days <= 7:
            return 0.85  # High confidence - week of development
        elif time_diff_days <= 30:
            return 0.9  # Very high confidence - month of development
        else:
            return 0.95  # Extremely high confidence - long development period

    def get_confidence_category(self, confidence_score: float) -> str:
        """
        Categorize confidence score into human-readable categories.

        Args:
            confidence_score: Confidence score between 0.0 and 1.0

        Returns:
            String category: "high", "medium", or "low"
        """
        if confidence_score >= self.high_confidence_threshold:
            return "high"
        elif confidence_score >= self.medium_confidence_threshold:
            return "medium"
        else:
            return "low"

    def should_verify_with_api(
        self, analysis_result: TimestampAnalysisResult, force_verification: bool = False
    ) -> bool:
        """
        Determine if API verification is recommended based on analysis result.

        Args:
            analysis_result: Result from timestamp analysis
            force_verification: Force verification regardless of confidence

        Returns:
            True if API verification is recommended
        """
        if force_verification:
            return True

        # Verify low confidence results
        if analysis_result.confidence_score < self.medium_confidence_threshold:
            return True

        # Verify UNKNOWN status regardless of confidence
        return analysis_result.status == CommitStatus.UNKNOWN

    def batch_analyze(
        self, fork_data: list[tuple[str, datetime, datetime]]
    ) -> list[TimestampAnalysisResult]:
        """
        Analyze multiple forks in batch for efficiency.

        Args:
            fork_data: List of tuples (fork_url, created_at, pushed_at)

        Returns:
            List of TimestampAnalysisResult objects
        """
        results = []

        logger.info(f"Starting batch timestamp analysis for {len(fork_data)} forks")

        for fork_url, created_at, pushed_at in fork_data:
            try:
                result = self.analyze_timestamps(created_at, pushed_at, fork_url)
                results.append(result)
            except Exception as e:
                logger.error(f"Error analyzing timestamps for {fork_url}: {e}")
                # Create error result
                error_result = TimestampAnalysisResult(
                    created_at=created_at or datetime.now(UTC),
                    pushed_at=pushed_at or datetime.now(UTC),
                    status=CommitStatus.UNKNOWN,
                    confidence_score=0.0,
                    time_difference_days=0,
                    analysis_notes=f"Analysis error: {e!s}",
                )
                results.append(error_result)

        logger.info(f"Completed batch timestamp analysis: {len(results)} results")
        return results

    def get_analysis_summary(self, results: list[TimestampAnalysisResult]) -> dict:
        """
        Generate summary statistics for a batch of analysis results.

        Args:
            results: List of TimestampAnalysisResult objects

        Returns:
            Dictionary with summary statistics
        """
        if not results:
            return {
                "total_analyzed": 0,
                "status_distribution": {},
                "confidence_distribution": {},
                "average_confidence": 0.0,
                "verification_recommended": 0,
            }

        # Count status distribution
        status_counts = {}
        for result in results:
            status = result.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        # Count confidence distribution
        confidence_counts = {"high": 0, "medium": 0, "low": 0}
        total_confidence = 0.0
        verification_needed = 0

        for result in results:
            category = self.get_confidence_category(result.confidence_score)
            confidence_counts[category] += 1
            total_confidence += result.confidence_score

            if self.should_verify_with_api(result):
                verification_needed += 1

        return {
            "total_analyzed": len(results),
            "status_distribution": status_counts,
            "confidence_distribution": confidence_counts,
            "average_confidence": total_confidence / len(results),
            "verification_recommended": verification_needed,
        }
