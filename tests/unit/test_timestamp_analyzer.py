"""Tests for TimestampAnalyzer class."""

from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from src.forklift.analysis.timestamp_analyzer import TimestampAnalyzer
from src.forklift.models.commits_ahead_detection import (
    CommitStatus,
    TimestampAnalysisResult,
)


class TestTimestampAnalyzer:
    """Test TimestampAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create TimestampAnalyzer instance with default settings."""
        return TimestampAnalyzer()

    @pytest.fixture
    def custom_analyzer(self):
        """Create TimestampAnalyzer with custom thresholds."""
        return TimestampAnalyzer(
            high_confidence_threshold=0.8,
            medium_confidence_threshold=0.6,
            same_timestamp_tolerance_seconds=30,
        )

    def test_analyzer_initialization_default(self):
        """Test TimestampAnalyzer initialization with default values."""
        analyzer = TimestampAnalyzer()

        assert analyzer.high_confidence_threshold == 0.9
        assert analyzer.medium_confidence_threshold == 0.7
        assert analyzer.same_timestamp_tolerance_seconds == 60

    def test_analyzer_initialization_custom(self):
        """Test TimestampAnalyzer initialization with custom values."""
        analyzer = TimestampAnalyzer(
            high_confidence_threshold=0.8,
            medium_confidence_threshold=0.6,
            same_timestamp_tolerance_seconds=30,
        )

        assert analyzer.high_confidence_threshold == 0.8
        assert analyzer.medium_confidence_threshold == 0.6
        assert analyzer.same_timestamp_tolerance_seconds == 30


class TestTimestampAnalysis:
    """Test timestamp analysis logic."""

    @pytest.fixture
    def analyzer(self):
        """Create TimestampAnalyzer instance."""
        return TimestampAnalyzer()

    def test_analyze_identical_timestamps(self, analyzer):
        """Test analysis when created_at and pushed_at are identical."""
        timestamp = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

        result = analyzer.analyze_timestamps(timestamp, timestamp)

        assert result.status == CommitStatus.NO_COMMITS
        assert result.confidence_score == 0.95
        assert result.time_difference_days == 0
        assert "within 0 seconds" in result.analysis_notes
        assert result.created_at == timestamp
        assert result.pushed_at == timestamp

    def test_analyze_same_timestamps_within_tolerance(self, analyzer):
        """Test analysis when timestamps are within tolerance."""
        created_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        pushed_at = datetime(2023, 1, 1, 12, 0, 30, tzinfo=UTC)  # 30 seconds later

        result = analyzer.analyze_timestamps(created_at, pushed_at)

        assert result.status == CommitStatus.NO_COMMITS
        assert result.confidence_score == 0.85  # Close timestamps
        assert result.time_difference_days == 0
        assert "within 30 seconds" in result.analysis_notes

    def test_analyze_pushed_before_created(self, analyzer):
        """Test analysis when pushed_at is before created_at."""
        created_at = datetime(2023, 1, 15, 12, 0, 0, tzinfo=UTC)
        pushed_at = datetime(2023, 1, 10, 12, 0, 0, tzinfo=UTC)  # 5 days before

        result = analyzer.analyze_timestamps(created_at, pushed_at)

        assert result.status == CommitStatus.NO_COMMITS
        assert result.confidence_score == 0.95  # High confidence for this unusual case
        assert result.time_difference_days == -5
        assert "5 days before created_at" in result.analysis_notes

    def test_analyze_same_day_different_hours(self, analyzer):
        """Test analysis when timestamps are on same day but different hours."""
        created_at = datetime(2023, 1, 1, 9, 0, 0, tzinfo=UTC)
        pushed_at = datetime(2023, 1, 1, 15, 0, 0, tzinfo=UTC)  # 6 hours later

        result = analyzer.analyze_timestamps(created_at, pushed_at)

        assert result.status == CommitStatus.UNKNOWN
        assert 0.4 <= result.confidence_score <= 0.6  # Medium confidence for same day
        assert result.time_difference_days == 0
        assert "6.0 hours after created_at on same day" in result.analysis_notes

    def test_analyze_one_day_difference(self, analyzer):
        """Test analysis when pushed_at is one day after created_at."""
        created_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        pushed_at = datetime(2023, 1, 2, 12, 0, 0, tzinfo=UTC)  # 1 day later

        result = analyzer.analyze_timestamps(created_at, pushed_at)

        assert result.status == CommitStatus.HAS_COMMITS
        assert result.confidence_score == 0.7  # Good confidence for 1 day
        assert result.time_difference_days == 1
        assert "1 days after created_at" in result.analysis_notes

    def test_analyze_week_difference(self, analyzer):
        """Test analysis when pushed_at is a week after created_at."""
        created_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        pushed_at = datetime(2023, 1, 8, 12, 0, 0, tzinfo=UTC)  # 7 days later

        result = analyzer.analyze_timestamps(created_at, pushed_at)

        assert result.status == CommitStatus.HAS_COMMITS
        assert result.confidence_score == 0.85  # High confidence for week
        assert result.time_difference_days == 7
        assert "7 days after created_at" in result.analysis_notes

    def test_analyze_month_difference(self, analyzer):
        """Test analysis when pushed_at is a month after created_at."""
        created_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        pushed_at = datetime(2023, 2, 1, 12, 0, 0, tzinfo=UTC)  # 31 days later

        result = analyzer.analyze_timestamps(created_at, pushed_at)

        assert result.status == CommitStatus.HAS_COMMITS
        assert result.confidence_score == 0.95  # Very high confidence for month
        assert result.time_difference_days == 31
        assert "31 days after created_at" in result.analysis_notes

    def test_analyze_with_fork_url_logging(self, analyzer):
        """Test analysis includes fork URL in logging context."""
        created_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        pushed_at = datetime(2023, 1, 2, 12, 0, 0, tzinfo=UTC)
        fork_url = "https://github.com/user/repo"

        with patch("src.forklift.analysis.timestamp_analyzer.logger") as mock_logger:
            analyzer.analyze_timestamps(created_at, pushed_at, fork_url)

            # Verify logging calls include fork URL
            mock_logger.debug.assert_called()
            debug_calls = [call.args[0] for call in mock_logger.debug.call_args_list]
            assert any(fork_url in call for call in debug_calls)


class TestMissingTimestamps:
    """Test handling of missing or invalid timestamps."""

    @pytest.fixture
    def analyzer(self):
        """Create TimestampAnalyzer instance."""
        return TimestampAnalyzer()

    def test_analyze_both_timestamps_missing(self, analyzer):
        """Test analysis when both timestamps are None."""
        result = analyzer.analyze_timestamps(None, None)

        assert result.status == CommitStatus.UNKNOWN
        assert result.confidence_score == 0.0
        assert "Both created_at and pushed_at are missing" in result.analysis_notes

    def test_analyze_created_at_missing(self, analyzer):
        """Test analysis when created_at is None."""
        pushed_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

        result = analyzer.analyze_timestamps(None, pushed_at)

        assert result.status == CommitStatus.UNKNOWN
        assert result.confidence_score == 0.1
        assert "created_at is missing" in result.analysis_notes
        assert result.pushed_at == pushed_at

    def test_analyze_pushed_at_missing(self, analyzer):
        """Test analysis when pushed_at is None."""
        created_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

        result = analyzer.analyze_timestamps(created_at, None)

        assert result.status == CommitStatus.UNKNOWN
        assert result.confidence_score == 0.1
        assert "pushed_at is missing" in result.analysis_notes
        assert result.created_at == created_at

    def test_missing_timestamps_with_fork_url(self, analyzer):
        """Test missing timestamp handling includes fork URL in logging."""
        fork_url = "https://github.com/user/repo"

        with patch("src.forklift.analysis.timestamp_analyzer.logger") as mock_logger:
            analyzer.analyze_timestamps(None, None, fork_url)

            # Verify warning log includes fork URL
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args[0][0]
            assert fork_url in warning_call


class TestTimezoneHandling:
    """Test timezone normalization and handling."""

    @pytest.fixture
    def analyzer(self):
        """Create TimestampAnalyzer instance."""
        return TimestampAnalyzer()

    def test_normalize_naive_datetime_to_utc(self, analyzer):
        """Test normalization of naive datetime to UTC."""
        naive_dt = datetime(2023, 1, 1, 12, 0, 0)  # No timezone

        normalized = analyzer._normalize_to_utc(naive_dt)

        assert normalized.tzinfo == UTC
        assert normalized.replace(tzinfo=None) == naive_dt

    def test_normalize_utc_datetime_unchanged(self, analyzer):
        """Test UTC datetime remains unchanged."""
        utc_dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

        normalized = analyzer._normalize_to_utc(utc_dt)

        assert normalized == utc_dt
        assert normalized.tzinfo == UTC

    def test_normalize_different_timezone_to_utc(self, analyzer):
        """Test conversion from different timezone to UTC."""
        # Create EST timezone (UTC-5)
        est = timezone(timedelta(hours=-5))
        est_dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=est)

        normalized = analyzer._normalize_to_utc(est_dt)

        assert normalized.tzinfo == UTC
        # 12:00 EST should be 17:00 UTC
        assert normalized.hour == 17

    def test_analyze_mixed_timezones(self, analyzer):
        """Test analysis with timestamps in different timezones."""
        # Create timestamps in different timezones
        est = timezone(timedelta(hours=-5))
        pst = timezone(timedelta(hours=-8))

        created_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=est)  # 12:00 EST = 17:00 UTC
        pushed_at = datetime(2023, 1, 1, 15, 0, 0, tzinfo=pst)  # 15:00 PST = 23:00 UTC

        result = analyzer.analyze_timestamps(created_at, pushed_at)

        # Both should be normalized to UTC
        assert result.created_at.tzinfo == UTC
        assert result.pushed_at.tzinfo == UTC
        # 6 hour difference in UTC (17:00 to 23:00)
        assert result.time_difference_days == 0
        assert result.status == CommitStatus.UNKNOWN  # Same day


class TestConfidenceScoring:
    """Test confidence scoring algorithms."""

    @pytest.fixture
    def analyzer(self):
        """Create TimestampAnalyzer instance."""
        return TimestampAnalyzer()

    def test_same_timestamp_confidence_exact_match(self, analyzer):
        """Test confidence for exact timestamp match."""
        confidence = analyzer._calculate_same_timestamp_confidence(0)
        assert confidence == 0.95

    def test_same_timestamp_confidence_very_close(self, analyzer):
        """Test confidence for very close timestamps."""
        confidence = analyzer._calculate_same_timestamp_confidence(5)
        assert confidence == 0.9

    def test_same_timestamp_confidence_close(self, analyzer):
        """Test confidence for close timestamps."""
        confidence = analyzer._calculate_same_timestamp_confidence(20)
        assert confidence == 0.85

    def test_same_timestamp_confidence_within_tolerance(self, analyzer):
        """Test confidence for timestamps within tolerance."""
        confidence = analyzer._calculate_same_timestamp_confidence(50)
        assert confidence == 0.8

    def test_same_day_confidence_progression(self, analyzer):
        """Test same day confidence increases with time difference."""
        # Less than 1 hour
        conf_1h = analyzer._calculate_same_day_confidence(1800)  # 30 minutes
        # 3 hours
        conf_3h = analyzer._calculate_same_day_confidence(10800)  # 3 hours
        # 8 hours
        conf_8h = analyzer._calculate_same_day_confidence(28800)  # 8 hours
        # 15 hours
        conf_15h = analyzer._calculate_same_day_confidence(54000)  # 15 hours

        assert conf_1h < conf_3h < conf_8h < conf_15h
        assert conf_1h == 0.3
        assert conf_3h == 0.4
        assert conf_8h == 0.5
        assert conf_15h == 0.6

    def test_multi_day_confidence_progression(self, analyzer):
        """Test multi-day confidence increases with time difference."""
        conf_1d = analyzer._calculate_multi_day_confidence(1)
        conf_5d = analyzer._calculate_multi_day_confidence(5)
        conf_20d = analyzer._calculate_multi_day_confidence(20)
        conf_60d = analyzer._calculate_multi_day_confidence(60)

        assert conf_1d < conf_5d < conf_20d < conf_60d
        assert conf_1d == 0.7
        assert conf_5d == 0.85
        assert conf_20d == 0.9
        assert conf_60d == 0.95

    def test_get_confidence_category_high(self, analyzer):
        """Test high confidence category."""
        assert analyzer.get_confidence_category(0.95) == "high"
        assert analyzer.get_confidence_category(0.9) == "high"

    def test_get_confidence_category_medium(self, analyzer):
        """Test medium confidence category."""
        assert analyzer.get_confidence_category(0.8) == "medium"
        assert analyzer.get_confidence_category(0.7) == "medium"

    def test_get_confidence_category_low(self, analyzer):
        """Test low confidence category."""
        assert analyzer.get_confidence_category(0.6) == "low"
        assert analyzer.get_confidence_category(0.3) == "low"
        assert analyzer.get_confidence_category(0.0) == "low"

    def test_custom_confidence_thresholds(self):
        """Test confidence categories with custom thresholds."""
        analyzer = TimestampAnalyzer(
            high_confidence_threshold=0.8, medium_confidence_threshold=0.6
        )

        assert analyzer.get_confidence_category(0.85) == "high"
        assert analyzer.get_confidence_category(0.7) == "medium"
        assert analyzer.get_confidence_category(0.5) == "low"


class TestAPIVerificationRecommendations:
    """Test API verification recommendation logic."""

    @pytest.fixture
    def analyzer(self):
        """Create TimestampAnalyzer instance."""
        return TimestampAnalyzer()

    def test_should_verify_force_verification(self, analyzer):
        """Test forced verification overrides confidence."""
        result = TimestampAnalysisResult(
            created_at=datetime.now(UTC),
            pushed_at=datetime.now(UTC),
            status=CommitStatus.HAS_COMMITS,
            confidence_score=0.95,  # High confidence
            time_difference_days=1,
            analysis_notes="Test",
        )

        assert analyzer.should_verify_with_api(result, force_verification=True)

    def test_should_verify_low_confidence(self, analyzer):
        """Test verification recommended for low confidence."""
        result = TimestampAnalysisResult(
            created_at=datetime.now(UTC),
            pushed_at=datetime.now(UTC),
            status=CommitStatus.HAS_COMMITS,
            confidence_score=0.5,  # Low confidence
            time_difference_days=1,
            analysis_notes="Test",
        )

        assert analyzer.should_verify_with_api(result)

    def test_should_verify_unknown_status(self, analyzer):
        """Test verification recommended for unknown status."""
        result = TimestampAnalysisResult(
            created_at=datetime.now(UTC),
            pushed_at=datetime.now(UTC),
            status=CommitStatus.UNKNOWN,
            confidence_score=0.8,  # High confidence but unknown status
            time_difference_days=0,
            analysis_notes="Test",
        )

        assert analyzer.should_verify_with_api(result)

    def test_should_not_verify_high_confidence(self, analyzer):
        """Test no verification needed for high confidence results."""
        result = TimestampAnalysisResult(
            created_at=datetime.now(UTC),
            pushed_at=datetime.now(UTC),
            status=CommitStatus.HAS_COMMITS,
            confidence_score=0.95,  # High confidence
            time_difference_days=7,
            analysis_notes="Test",
        )

        assert not analyzer.should_verify_with_api(result)

    def test_should_not_verify_medium_confidence_clear_status(self, analyzer):
        """Test no verification needed for medium confidence with clear status."""
        result = TimestampAnalysisResult(
            created_at=datetime.now(UTC),
            pushed_at=datetime.now(UTC),
            status=CommitStatus.NO_COMMITS,
            confidence_score=0.8,  # Medium confidence
            time_difference_days=0,
            analysis_notes="Test",
        )

        assert not analyzer.should_verify_with_api(result)


class TestBatchAnalysis:
    """Test batch analysis functionality."""

    @pytest.fixture
    def analyzer(self):
        """Create TimestampAnalyzer instance."""
        return TimestampAnalyzer()

    def test_batch_analyze_empty_list(self, analyzer):
        """Test batch analysis with empty list."""
        results = analyzer.batch_analyze([])
        assert results == []

    def test_batch_analyze_single_fork(self, analyzer):
        """Test batch analysis with single fork."""
        created_at = datetime(2023, 1, 1, tzinfo=UTC)
        pushed_at = datetime(2023, 1, 2, tzinfo=UTC)
        fork_data = [("https://github.com/user/repo", created_at, pushed_at)]

        results = analyzer.batch_analyze(fork_data)

        assert len(results) == 1
        assert results[0].status == CommitStatus.HAS_COMMITS
        assert results[0].time_difference_days == 1

    def test_batch_analyze_multiple_forks(self, analyzer):
        """Test batch analysis with multiple forks."""
        base_time = datetime(2023, 1, 1, tzinfo=UTC)
        fork_data = [
            ("https://github.com/user1/repo", base_time, base_time),  # No commits
            (
                "https://github.com/user2/repo",
                base_time,
                base_time + timedelta(days=1),
            ),  # Has commits
            (
                "https://github.com/user3/repo",
                base_time,
                base_time + timedelta(hours=6),
            ),  # Unknown
        ]

        results = analyzer.batch_analyze(fork_data)

        assert len(results) == 3
        assert results[0].status == CommitStatus.NO_COMMITS
        assert results[1].status == CommitStatus.HAS_COMMITS
        assert results[2].status == CommitStatus.UNKNOWN

    def test_batch_analyze_with_errors(self, analyzer):
        """Test batch analysis handles individual errors gracefully."""
        # Create fork data with one invalid entry
        fork_data = [
            ("https://github.com/user1/repo", None, None),  # Will cause error handling
            (
                "https://github.com/user2/repo",
                datetime(2023, 1, 1, tzinfo=UTC),
                datetime(2023, 1, 2, tzinfo=UTC),
            ),  # Valid
        ]

        results = analyzer.batch_analyze(fork_data)

        assert len(results) == 2
        # First result should be error case with UNKNOWN status
        assert results[0].status == CommitStatus.UNKNOWN
        assert results[0].confidence_score == 0.0
        # Second result should be normal
        assert results[1].status == CommitStatus.HAS_COMMITS

    def test_batch_analyze_logging(self, analyzer):
        """Test batch analysis includes appropriate logging."""
        fork_data = [
            (
                "https://github.com/user/repo",
                datetime(2023, 1, 1, tzinfo=UTC),
                datetime(2023, 1, 2, tzinfo=UTC),
            )
        ]

        with patch("src.forklift.analysis.timestamp_analyzer.logger") as mock_logger:
            analyzer.batch_analyze(fork_data)

            # Verify info logs for batch start and completion
            info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
            assert any(
                "Starting batch timestamp analysis" in call for call in info_calls
            )
            assert any(
                "Completed batch timestamp analysis" in call for call in info_calls
            )


class TestAnalysisSummary:
    """Test analysis summary generation."""

    @pytest.fixture
    def analyzer(self):
        """Create TimestampAnalyzer instance."""
        return TimestampAnalyzer()

    def test_get_analysis_summary_empty_results(self, analyzer):
        """Test summary generation with empty results."""
        summary = analyzer.get_analysis_summary([])

        expected = {
            "total_analyzed": 0,
            "status_distribution": {},
            "confidence_distribution": {},
            "average_confidence": 0.0,
            "verification_recommended": 0,
        }
        assert summary == expected

    def test_get_analysis_summary_single_result(self, analyzer):
        """Test summary generation with single result."""
        result = TimestampAnalysisResult(
            created_at=datetime.now(UTC),
            pushed_at=datetime.now(UTC),
            status=CommitStatus.HAS_COMMITS,
            confidence_score=0.95,
            time_difference_days=7,
            analysis_notes="Test",
        )

        summary = analyzer.get_analysis_summary([result])

        assert summary["total_analyzed"] == 1
        assert summary["status_distribution"] == {"has_commits": 1}
        assert summary["confidence_distribution"] == {"high": 1, "medium": 0, "low": 0}
        assert summary["average_confidence"] == 0.95
        assert (
            summary["verification_recommended"] == 0
        )  # High confidence, no verification needed

    def test_get_analysis_summary_mixed_results(self, analyzer):
        """Test summary generation with mixed results."""
        results = [
            TimestampAnalysisResult(
                created_at=datetime.now(UTC),
                pushed_at=datetime.now(UTC),
                status=CommitStatus.HAS_COMMITS,
                confidence_score=0.95,  # High confidence
                time_difference_days=7,
                analysis_notes="Test 1",
            ),
            TimestampAnalysisResult(
                created_at=datetime.now(UTC),
                pushed_at=datetime.now(UTC),
                status=CommitStatus.NO_COMMITS,
                confidence_score=0.8,  # Medium confidence
                time_difference_days=0,
                analysis_notes="Test 2",
            ),
            TimestampAnalysisResult(
                created_at=datetime.now(UTC),
                pushed_at=datetime.now(UTC),
                status=CommitStatus.UNKNOWN,
                confidence_score=0.5,  # Low confidence
                time_difference_days=0,
                analysis_notes="Test 3",
            ),
        ]

        summary = analyzer.get_analysis_summary(results)

        assert summary["total_analyzed"] == 3
        assert summary["status_distribution"] == {
            "has_commits": 1,
            "no_commits": 1,
            "unknown": 1,
        }
        assert summary["confidence_distribution"] == {"high": 1, "medium": 1, "low": 1}
        assert summary["average_confidence"] == (0.95 + 0.8 + 0.5) / 3
        assert (
            summary["verification_recommended"] == 1
        )  # Only the UNKNOWN status needs verification


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def analyzer(self):
        """Create TimestampAnalyzer instance."""
        return TimestampAnalyzer()

    def test_analyze_very_large_time_difference(self, analyzer):
        """Test analysis with very large time differences."""
        created_at = datetime(2020, 1, 1, tzinfo=UTC)
        pushed_at = datetime(2023, 1, 1, tzinfo=UTC)  # 3 years later

        result = analyzer.analyze_timestamps(created_at, pushed_at)

        assert result.status == CommitStatus.HAS_COMMITS
        assert result.confidence_score == 0.95  # Very high confidence
        assert result.time_difference_days > 1000

    def test_analyze_microsecond_differences(self, analyzer):
        """Test analysis with microsecond-level differences."""
        created_at = datetime(2023, 1, 1, 12, 0, 0, 0, tzinfo=UTC)
        pushed_at = datetime(
            2023, 1, 1, 12, 0, 0, 500000, tzinfo=UTC
        )  # 0.5 seconds later

        result = analyzer.analyze_timestamps(created_at, pushed_at)

        assert result.status == CommitStatus.NO_COMMITS
        assert (
            result.confidence_score == 0.9
        )  # High confidence for very close timestamps

    def test_custom_tolerance_affects_analysis(self):
        """Test that custom tolerance settings affect analysis."""
        # Analyzer with very tight tolerance
        tight_analyzer = TimestampAnalyzer(same_timestamp_tolerance_seconds=10)

        created_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        pushed_at = datetime(2023, 1, 1, 12, 0, 30, tzinfo=UTC)  # 30 seconds later

        result = tight_analyzer.analyze_timestamps(created_at, pushed_at)

        # With tight tolerance, 30 seconds should be treated as same day, not same timestamp
        assert result.status == CommitStatus.UNKNOWN
        assert "0.0 hours after created_at on same day" in result.analysis_notes

    def test_analyze_leap_year_handling(self, analyzer):
        """Test analysis handles leap year correctly."""
        # February 29, 2024 (leap year)
        created_at = datetime(2024, 2, 29, 12, 0, 0, tzinfo=UTC)
        pushed_at = datetime(2024, 3, 1, 12, 0, 0, tzinfo=UTC)  # Next day

        result = analyzer.analyze_timestamps(created_at, pushed_at)

        assert result.status == CommitStatus.HAS_COMMITS
        assert result.time_difference_days == 1

    def test_analyze_daylight_saving_transition(self, analyzer):
        """Test analysis during daylight saving time transitions."""
        # Create timezone that observes DST (EST/EDT)
        from datetime import timedelta, timezone

        # Before DST (EST = UTC-5)
        est = timezone(timedelta(hours=-5))
        created_at = datetime(2023, 3, 11, 12, 0, 0, tzinfo=est)

        # After DST (EDT = UTC-4) - same local time but different UTC offset
        edt = timezone(timedelta(hours=-4))
        pushed_at = datetime(2023, 3, 12, 12, 0, 0, tzinfo=edt)

        result = analyzer.analyze_timestamps(created_at, pushed_at)

        # Should handle timezone conversion correctly
        # The actual time difference in UTC is 23 hours (same day), not 24 hours (different days)
        # 12:00 EST (17:00 UTC) to 12:00 EDT next day (16:00 UTC) = 23 hours
        assert result.status == CommitStatus.UNKNOWN  # Same day in UTC
        assert result.time_difference_days == 0  # Same day
        # Both timestamps should be normalized to UTC
        assert result.created_at.tzinfo == UTC
        assert result.pushed_at.tzinfo == UTC
