"""Unit tests for CommitStatusClassifier."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from src.forklift.analysis.commit_status_classifier import CommitStatusClassifier
from src.forklift.analysis.timestamp_analyzer import TimestampAnalyzer
from src.forklift.models.commits_ahead_detection import (
    CommitStatus,
    ForkQualification,
    TimestampAnalysisResult,
)


class TestCommitStatusClassifier:
    """Test cases for CommitStatusClassifier."""

    @pytest.fixture
    def mock_timestamp_analyzer(self):
        """Create a mock TimestampAnalyzer."""
        return Mock(spec=TimestampAnalyzer)

    @pytest.fixture
    def classifier(self, mock_timestamp_analyzer):
        """Create a CommitStatusClassifier with mock analyzer."""
        return CommitStatusClassifier(
            timestamp_analyzer=mock_timestamp_analyzer,
            high_confidence_threshold=0.9,
            medium_confidence_threshold=0.7,
            low_confidence_threshold=0.3,
        )

    @pytest.fixture
    def sample_fork_data(self):
        """Sample fork data for testing."""
        base_time = datetime.now(UTC)
        return {
            "fork_url": "https://github.com/user/repo",
            "owner": "user",
            "name": "repo",
            "created_at": base_time,
            "pushed_at": base_time + timedelta(days=5),
        }

    def test_init_with_default_analyzer(self):
        """Test initialization with default TimestampAnalyzer."""
        classifier = CommitStatusClassifier()

        assert isinstance(classifier.timestamp_analyzer, TimestampAnalyzer)
        assert classifier.high_confidence_threshold == 0.9
        assert classifier.medium_confidence_threshold == 0.7
        assert classifier.low_confidence_threshold == 0.3
        assert len(classifier._classified_forks) == 0

    def test_init_with_custom_thresholds(self):
        """Test initialization with custom confidence thresholds."""
        classifier = CommitStatusClassifier(
            high_confidence_threshold=0.95,
            medium_confidence_threshold=0.8,
            low_confidence_threshold=0.5,
        )

        assert classifier.high_confidence_threshold == 0.95
        assert classifier.medium_confidence_threshold == 0.8
        assert classifier.low_confidence_threshold == 0.5

    def test_classify_fork_high_confidence_has_commits(
        self, classifier, mock_timestamp_analyzer, sample_fork_data
    ):
        """Test classifying fork with high confidence HAS_COMMITS result."""
        # Setup mock to return high confidence HAS_COMMITS
        mock_analysis = TimestampAnalysisResult(
            created_at=sample_fork_data["created_at"],
            pushed_at=sample_fork_data["pushed_at"],
            status=CommitStatus.HAS_COMMITS,
            confidence_score=0.95,
            time_difference_days=5,
            analysis_notes="High confidence analysis",
        )
        mock_timestamp_analyzer.analyze_timestamps.return_value = mock_analysis

        # Classify fork
        result = classifier.classify_fork(**sample_fork_data)

        # Verify result
        assert isinstance(result, ForkQualification)
        assert result.fork_url == sample_fork_data["fork_url"]
        assert result.owner == sample_fork_data["owner"]
        assert result.name == sample_fork_data["name"]
        assert result.commit_status == CommitStatus.HAS_COMMITS
        assert result.confidence_score == 0.95
        assert result.verification_method == "timestamp_analysis"
        assert result.last_verified is not None
        assert result.commits_ahead_count is None

        # Verify analyzer was called
        mock_timestamp_analyzer.analyze_timestamps.assert_called_once_with(
            sample_fork_data["created_at"],
            sample_fork_data["pushed_at"],
            sample_fork_data["fork_url"],
        )

    def test_classify_fork_medium_confidence_no_commits(
        self, classifier, mock_timestamp_analyzer, sample_fork_data
    ):
        """Test classifying fork with medium confidence NO_COMMITS result."""
        # Setup mock to return medium confidence NO_COMMITS
        mock_analysis = TimestampAnalysisResult(
            created_at=sample_fork_data["created_at"],
            pushed_at=sample_fork_data["pushed_at"],
            status=CommitStatus.NO_COMMITS,
            confidence_score=0.75,
            time_difference_days=0,
            analysis_notes="Medium confidence analysis",
        )
        mock_timestamp_analyzer.analyze_timestamps.return_value = mock_analysis

        # Classify fork
        result = classifier.classify_fork(**sample_fork_data)

        # Verify result
        assert result.commit_status == CommitStatus.NO_COMMITS
        assert result.confidence_score == 0.75

    def test_classify_fork_low_confidence_becomes_unknown(
        self, classifier, mock_timestamp_analyzer, sample_fork_data
    ):
        """Test that low confidence results become UNKNOWN status."""
        # Setup mock to return low confidence HAS_COMMITS
        mock_analysis = TimestampAnalysisResult(
            created_at=sample_fork_data["created_at"],
            pushed_at=sample_fork_data["pushed_at"],
            status=CommitStatus.HAS_COMMITS,
            confidence_score=0.4,
            time_difference_days=1,
            analysis_notes="Low confidence analysis",
        )
        mock_timestamp_analyzer.analyze_timestamps.return_value = mock_analysis

        # Classify fork
        result = classifier.classify_fork(**sample_fork_data)

        # Verify low confidence HAS_COMMITS becomes UNKNOWN
        assert result.commit_status == CommitStatus.UNKNOWN
        assert result.confidence_score == 0.4

    def test_classify_fork_very_low_confidence_becomes_unknown(
        self, classifier, mock_timestamp_analyzer, sample_fork_data
    ):
        """Test that very low confidence results become UNKNOWN status."""
        # Setup mock to return very low confidence NO_COMMITS
        mock_analysis = TimestampAnalysisResult(
            created_at=sample_fork_data["created_at"],
            pushed_at=sample_fork_data["pushed_at"],
            status=CommitStatus.NO_COMMITS,
            confidence_score=0.1,
            time_difference_days=0,
            analysis_notes="Very low confidence analysis",
        )
        mock_timestamp_analyzer.analyze_timestamps.return_value = mock_analysis

        # Classify fork
        result = classifier.classify_fork(**sample_fork_data)

        # Verify very low confidence becomes UNKNOWN
        assert result.commit_status == CommitStatus.UNKNOWN
        assert result.confidence_score == 0.1

    def test_classify_fork_already_classified_returns_existing(
        self, classifier, mock_timestamp_analyzer, sample_fork_data
    ):
        """Test that already classified fork returns existing result without re-analysis."""
        # Setup mock for first classification
        mock_analysis = TimestampAnalysisResult(
            created_at=sample_fork_data["created_at"],
            pushed_at=sample_fork_data["pushed_at"],
            status=CommitStatus.HAS_COMMITS,
            confidence_score=0.95,
            time_difference_days=5,
            analysis_notes="First analysis",
        )
        mock_timestamp_analyzer.analyze_timestamps.return_value = mock_analysis

        # First classification
        result1 = classifier.classify_fork(**sample_fork_data)

        # Second classification (should return existing)
        result2 = classifier.classify_fork(**sample_fork_data)

        # Verify same result returned
        assert result1.fork_url == result2.fork_url
        assert result1.commit_status == result2.commit_status
        assert result1.confidence_score == result2.confidence_score

        # Verify analyzer only called once
        assert mock_timestamp_analyzer.analyze_timestamps.call_count == 1

    def test_classify_fork_force_reclassify(
        self, classifier, mock_timestamp_analyzer, sample_fork_data
    ):
        """Test force reclassification of already classified fork."""
        # Setup mock for first classification
        mock_analysis1 = TimestampAnalysisResult(
            created_at=sample_fork_data["created_at"],
            pushed_at=sample_fork_data["pushed_at"],
            status=CommitStatus.HAS_COMMITS,
            confidence_score=0.95,
            time_difference_days=5,
            analysis_notes="First analysis",
        )

        # Setup mock for second classification
        mock_analysis2 = TimestampAnalysisResult(
            created_at=sample_fork_data["created_at"],
            pushed_at=sample_fork_data["pushed_at"],
            status=CommitStatus.NO_COMMITS,
            confidence_score=0.85,
            time_difference_days=0,
            analysis_notes="Second analysis",
        )

        mock_timestamp_analyzer.analyze_timestamps.side_effect = [
            mock_analysis1,
            mock_analysis2,
        ]

        # First classification
        result1 = classifier.classify_fork(**sample_fork_data)

        # Force reclassification
        result2 = classifier.classify_fork(**sample_fork_data, force_reclassify=True)

        # Verify different results
        assert result1.commit_status == CommitStatus.HAS_COMMITS
        assert result2.commit_status == CommitStatus.NO_COMMITS
        assert result1.confidence_score == 0.95
        assert result2.confidence_score == 0.85

        # Verify analyzer called twice
        assert mock_timestamp_analyzer.analyze_timestamps.call_count == 2

    def test_classify_batch_success(self, classifier, mock_timestamp_analyzer):
        """Test successful batch classification."""
        # Setup test data
        base_time = datetime.now(UTC)
        fork_data = [
            {
                "fork_url": "https://github.com/user1/repo1",
                "owner": "user1",
                "name": "repo1",
                "created_at": base_time,
                "pushed_at": base_time + timedelta(days=1),
            },
            {
                "fork_url": "https://github.com/user2/repo2",
                "owner": "user2",
                "name": "repo2",
                "created_at": base_time,
                "pushed_at": base_time,
            },
        ]

        # Setup mock responses
        mock_analyses = [
            TimestampAnalysisResult(
                created_at=base_time,
                pushed_at=base_time + timedelta(days=1),
                status=CommitStatus.HAS_COMMITS,
                confidence_score=0.8,
                time_difference_days=1,
                analysis_notes="Analysis 1",
            ),
            TimestampAnalysisResult(
                created_at=base_time,
                pushed_at=base_time,
                status=CommitStatus.NO_COMMITS,
                confidence_score=0.9,
                time_difference_days=0,
                analysis_notes="Analysis 2",
            ),
        ]
        mock_timestamp_analyzer.analyze_timestamps.side_effect = mock_analyses

        # Classify batch
        results = classifier.classify_batch(fork_data)

        # Verify results
        assert len(results) == 2
        assert results[0].fork_url == "https://github.com/user1/repo1"
        assert results[0].commit_status == CommitStatus.HAS_COMMITS
        assert results[1].fork_url == "https://github.com/user2/repo2"
        assert results[1].commit_status == CommitStatus.NO_COMMITS

        # Verify analyzer called for each fork
        assert mock_timestamp_analyzer.analyze_timestamps.call_count == 2

    def test_classify_batch_with_error(self, classifier, mock_timestamp_analyzer):
        """Test batch classification with error handling."""
        # Setup test data with one invalid entry
        base_time = datetime.now(UTC)
        fork_data = [
            {
                "fork_url": "https://github.com/user1/repo1",
                "owner": "user1",
                "name": "repo1",
                "created_at": base_time,
                "pushed_at": base_time + timedelta(days=1),
            },
            {
                # Missing required fields to trigger error
                "fork_url": "https://github.com/user2/repo2",
            },
        ]

        # Setup mock to succeed for first, error for second
        mock_analysis = TimestampAnalysisResult(
            created_at=base_time,
            pushed_at=base_time + timedelta(days=1),
            status=CommitStatus.HAS_COMMITS,
            confidence_score=0.8,
            time_difference_days=1,
            analysis_notes="Analysis 1",
        )
        mock_timestamp_analyzer.analyze_timestamps.return_value = mock_analysis

        # Classify batch
        results = classifier.classify_batch(fork_data)

        # Verify results
        assert len(results) == 2
        assert results[0].commit_status == CommitStatus.HAS_COMMITS
        assert results[1].commit_status == CommitStatus.UNKNOWN  # Error case
        assert results[1].confidence_score == 0.0
        assert results[1].verification_method == "error"

    def test_get_forks_by_status(self, classifier, mock_timestamp_analyzer):
        """Test filtering forks by status."""
        # Setup and classify some forks
        base_time = datetime.now(UTC)
        fork_data = [
            {
                "fork_url": "https://github.com/user1/repo1",
                "owner": "user1",
                "name": "repo1",
                "created_at": base_time,
                "pushed_at": base_time + timedelta(days=1),
            },
            {
                "fork_url": "https://github.com/user2/repo2",
                "owner": "user2",
                "name": "repo2",
                "created_at": base_time,
                "pushed_at": base_time,
            },
        ]

        # Setup mock responses
        mock_analyses = [
            TimestampAnalysisResult(
                created_at=base_time,
                pushed_at=base_time + timedelta(days=1),
                status=CommitStatus.HAS_COMMITS,
                confidence_score=0.9,
                time_difference_days=1,
                analysis_notes="Analysis 1",
            ),
            TimestampAnalysisResult(
                created_at=base_time,
                pushed_at=base_time,
                status=CommitStatus.NO_COMMITS,
                confidence_score=0.9,
                time_difference_days=0,
                analysis_notes="Analysis 2",
            ),
        ]
        mock_timestamp_analyzer.analyze_timestamps.side_effect = mock_analyses

        # Classify forks
        classifier.classify_batch(fork_data)

        # Test filtering by status
        has_commits_forks = classifier.get_forks_by_status(CommitStatus.HAS_COMMITS)
        no_commits_forks = classifier.get_forks_by_status(CommitStatus.NO_COMMITS)
        unknown_forks = classifier.get_forks_by_status(CommitStatus.UNKNOWN)

        assert len(has_commits_forks) == 1
        assert has_commits_forks[0].fork_url == "https://github.com/user1/repo1"
        assert len(no_commits_forks) == 1
        assert no_commits_forks[0].fork_url == "https://github.com/user2/repo2"
        assert len(unknown_forks) == 0

    def test_get_forks_by_confidence(self, classifier, mock_timestamp_analyzer):
        """Test filtering forks by confidence range."""
        # Setup and classify forks with different confidence levels
        base_time = datetime.now(UTC)
        fork_data = [
            {
                "fork_url": "https://github.com/user1/repo1",
                "owner": "user1",
                "name": "repo1",
                "created_at": base_time,
                "pushed_at": base_time + timedelta(days=1),
            },
            {
                "fork_url": "https://github.com/user2/repo2",
                "owner": "user2",
                "name": "repo2",
                "created_at": base_time,
                "pushed_at": base_time,
            },
        ]

        # Setup mock responses with different confidence levels
        mock_analyses = [
            TimestampAnalysisResult(
                created_at=base_time,
                pushed_at=base_time + timedelta(days=1),
                status=CommitStatus.HAS_COMMITS,
                confidence_score=0.95,  # High confidence
                time_difference_days=1,
                analysis_notes="High confidence",
            ),
            TimestampAnalysisResult(
                created_at=base_time,
                pushed_at=base_time,
                status=CommitStatus.NO_COMMITS,
                confidence_score=0.5,  # Low confidence
                time_difference_days=0,
                analysis_notes="Low confidence",
            ),
        ]
        mock_timestamp_analyzer.analyze_timestamps.side_effect = mock_analyses

        # Classify forks
        classifier.classify_batch(fork_data)

        # Test filtering by confidence
        high_confidence_forks = classifier.get_forks_by_confidence(0.9, 1.0)
        low_confidence_forks = classifier.get_forks_by_confidence(0.0, 0.6)

        assert len(high_confidence_forks) == 1
        assert high_confidence_forks[0].confidence_score == 0.95
        assert len(low_confidence_forks) == 1
        assert low_confidence_forks[0].confidence_score == 0.5

    def test_get_forks_needing_verification(self, classifier, mock_timestamp_analyzer):
        """Test identifying forks that need verification."""
        # Setup and classify forks
        base_time = datetime.now(UTC)
        fork_data = [
            {
                "fork_url": "https://github.com/user1/repo1",
                "owner": "user1",
                "name": "repo1",
                "created_at": base_time,
                "pushed_at": base_time + timedelta(days=1),
            },
            {
                "fork_url": "https://github.com/user2/repo2",
                "owner": "user2",
                "name": "repo2",
                "created_at": base_time,
                "pushed_at": base_time,
            },
            {
                "fork_url": "https://github.com/user3/repo3",
                "owner": "user3",
                "name": "repo3",
                "created_at": base_time,
                "pushed_at": base_time + timedelta(hours=1),
            },
        ]

        # Setup mock responses
        mock_analyses = [
            TimestampAnalysisResult(
                created_at=base_time,
                pushed_at=base_time + timedelta(days=1),
                status=CommitStatus.HAS_COMMITS,
                confidence_score=0.95,  # High confidence - no verification needed
                time_difference_days=1,
                analysis_notes="High confidence",
            ),
            TimestampAnalysisResult(
                created_at=base_time,
                pushed_at=base_time,
                status=CommitStatus.NO_COMMITS,
                confidence_score=0.5,  # Low confidence - needs verification
                time_difference_days=0,
                analysis_notes="Low confidence",
            ),
            TimestampAnalysisResult(
                created_at=base_time,
                pushed_at=base_time + timedelta(hours=1),
                status=CommitStatus.UNKNOWN,  # Unknown status - needs verification
                confidence_score=0.8,
                time_difference_days=0,
                analysis_notes="Unknown status",
            ),
        ]
        mock_timestamp_analyzer.analyze_timestamps.side_effect = mock_analyses

        # Classify forks
        classifier.classify_batch(fork_data)

        # Get forks needing verification
        verification_needed = classifier.get_forks_needing_verification()

        # Should include low confidence and unknown status forks
        assert len(verification_needed) == 2
        fork_urls = [f.fork_url for f in verification_needed]
        assert "https://github.com/user2/repo2" in fork_urls  # Low confidence
        assert "https://github.com/user3/repo3" in fork_urls  # Unknown status

    def test_update_fork_status_success(
        self, classifier, mock_timestamp_analyzer, sample_fork_data
    ):
        """Test successful fork status update."""
        # First classify a fork
        mock_analysis = TimestampAnalysisResult(
            created_at=sample_fork_data["created_at"],
            pushed_at=sample_fork_data["pushed_at"],
            status=CommitStatus.HAS_COMMITS,
            confidence_score=0.8,
            time_difference_days=5,
            analysis_notes="Initial analysis",
        )
        mock_timestamp_analyzer.analyze_timestamps.return_value = mock_analysis

        classifier.classify_fork(**sample_fork_data)

        # Update the status
        success = classifier.update_fork_status(
            fork_url=sample_fork_data["fork_url"],
            new_status=CommitStatus.VERIFIED_AHEAD,
            verification_method="api_compare",
            commits_ahead_count=3,
        )

        # Verify update
        assert success is True

        updated_fork = classifier.get_classification(sample_fork_data["fork_url"])
        assert updated_fork.commit_status == CommitStatus.VERIFIED_AHEAD
        assert updated_fork.verification_method == "api_compare"
        assert updated_fork.commits_ahead_count == 3
        assert updated_fork.confidence_score == 1.0  # API verification sets to 1.0
        assert updated_fork.last_verified is not None

    def test_update_fork_status_not_found(self, classifier):
        """Test updating status for non-existent fork."""
        success = classifier.update_fork_status(
            fork_url="https://github.com/nonexistent/repo",
            new_status=CommitStatus.VERIFIED_AHEAD,
        )

        assert success is False

    def test_get_classification_summary(self, classifier, mock_timestamp_analyzer):
        """Test generating classification summary."""
        # Setup and classify forks with various statuses and confidence levels
        base_time = datetime.now(UTC)
        fork_data = [
            {
                "fork_url": "https://github.com/user1/repo1",
                "owner": "user1",
                "name": "repo1",
                "created_at": base_time,
                "pushed_at": base_time + timedelta(days=1),
            },
            {
                "fork_url": "https://github.com/user2/repo2",
                "owner": "user2",
                "name": "repo2",
                "created_at": base_time,
                "pushed_at": base_time,
            },
            {
                "fork_url": "https://github.com/user3/repo3",
                "owner": "user3",
                "name": "repo3",
                "created_at": base_time,
                "pushed_at": base_time + timedelta(hours=1),
            },
        ]

        # Setup mock responses
        mock_analyses = [
            TimestampAnalysisResult(
                created_at=base_time,
                pushed_at=base_time + timedelta(days=1),
                status=CommitStatus.HAS_COMMITS,
                confidence_score=0.95,  # High confidence
                time_difference_days=1,
                analysis_notes="High confidence",
            ),
            TimestampAnalysisResult(
                created_at=base_time,
                pushed_at=base_time,
                status=CommitStatus.NO_COMMITS,
                confidence_score=0.9,  # High confidence
                time_difference_days=0,
                analysis_notes="High confidence",
            ),
            TimestampAnalysisResult(
                created_at=base_time,
                pushed_at=base_time + timedelta(hours=1),
                status=CommitStatus.UNKNOWN,
                confidence_score=0.5,  # Low confidence
                time_difference_days=0,
                analysis_notes="Low confidence",
            ),
        ]
        mock_timestamp_analyzer.analyze_timestamps.side_effect = mock_analyses

        # Classify forks
        classifier.classify_batch(fork_data)

        # Get summary
        summary = classifier.get_classification_summary()

        # Verify summary
        assert summary.total_forks == 3
        assert summary.has_commits == 1
        assert summary.no_commits == 1
        assert summary.unknown_status == 1
        assert summary.api_calls_saved == 2  # Two high confidence forks
        assert summary.confidence_distribution["high"] == 2
        assert summary.confidence_distribution["medium"] == 0
        assert summary.confidence_distribution["low"] == 1

    def test_get_classification_summary_empty(self, classifier):
        """Test generating summary with no classifications."""
        summary = classifier.get_classification_summary()

        assert summary.total_forks == 0
        assert summary.has_commits == 0
        assert summary.no_commits == 0
        assert summary.unknown_status == 0
        assert summary.api_calls_saved == 0
        assert summary.confidence_distribution == {}

    def test_clear_classifications(
        self, classifier, mock_timestamp_analyzer, sample_fork_data
    ):
        """Test clearing all classifications."""
        # First classify a fork
        mock_analysis = TimestampAnalysisResult(
            created_at=sample_fork_data["created_at"],
            pushed_at=sample_fork_data["pushed_at"],
            status=CommitStatus.HAS_COMMITS,
            confidence_score=0.8,
            time_difference_days=5,
            analysis_notes="Test analysis",
        )
        mock_timestamp_analyzer.analyze_timestamps.return_value = mock_analysis

        classifier.classify_fork(**sample_fork_data)
        assert classifier.get_classification_count() == 1

        # Clear classifications
        classifier.clear_classifications()
        assert classifier.get_classification_count() == 0
        assert not classifier.has_classification(sample_fork_data["fork_url"])

    def test_has_classification_and_get_classification(
        self, classifier, mock_timestamp_analyzer, sample_fork_data
    ):
        """Test checking and retrieving classifications."""
        # Initially no classification
        assert not classifier.has_classification(sample_fork_data["fork_url"])
        assert classifier.get_classification(sample_fork_data["fork_url"]) is None

        # Classify fork
        mock_analysis = TimestampAnalysisResult(
            created_at=sample_fork_data["created_at"],
            pushed_at=sample_fork_data["pushed_at"],
            status=CommitStatus.HAS_COMMITS,
            confidence_score=0.8,
            time_difference_days=5,
            analysis_notes="Test analysis",
        )
        mock_timestamp_analyzer.analyze_timestamps.return_value = mock_analysis

        result = classifier.classify_fork(**sample_fork_data)

        # Now should have classification
        assert classifier.has_classification(sample_fork_data["fork_url"])
        retrieved = classifier.get_classification(sample_fork_data["fork_url"])
        assert retrieved is not None
        assert retrieved.fork_url == result.fork_url
        assert retrieved.commit_status == result.commit_status

    def test_export_and_import_classifications(
        self, classifier, mock_timestamp_analyzer
    ):
        """Test exporting and importing classifications."""
        # Setup and classify some forks
        base_time = datetime.now(UTC)
        fork_data = [
            {
                "fork_url": "https://github.com/user1/repo1",
                "owner": "user1",
                "name": "repo1",
                "created_at": base_time,
                "pushed_at": base_time + timedelta(days=1),
            },
            {
                "fork_url": "https://github.com/user2/repo2",
                "owner": "user2",
                "name": "repo2",
                "created_at": base_time,
                "pushed_at": base_time,
            },
        ]

        # Setup mock responses
        mock_analyses = [
            TimestampAnalysisResult(
                created_at=base_time,
                pushed_at=base_time + timedelta(days=1),
                status=CommitStatus.HAS_COMMITS,
                confidence_score=0.9,
                time_difference_days=1,
                analysis_notes="Analysis 1",
            ),
            TimestampAnalysisResult(
                created_at=base_time,
                pushed_at=base_time,
                status=CommitStatus.NO_COMMITS,
                confidence_score=0.9,
                time_difference_days=0,
                analysis_notes="Analysis 2",
            ),
        ]
        mock_timestamp_analyzer.analyze_timestamps.side_effect = mock_analyses

        # Classify forks
        classifier.classify_batch(fork_data)
        assert classifier.get_classification_count() == 2

        # Export classifications
        exported_data = classifier.export_classifications()
        assert len(exported_data) == 2
        assert all("fork_url" in item for item in exported_data)
        assert all("commit_status" in item for item in exported_data)

        # Clear and import
        classifier.clear_classifications()
        assert classifier.get_classification_count() == 0

        imported_count = classifier.import_classifications(exported_data)
        assert imported_count == 2
        assert classifier.get_classification_count() == 2

        # Verify imported data
        for original_fork in fork_data:
            imported_fork = classifier.get_classification(original_fork["fork_url"])
            assert imported_fork is not None
            assert imported_fork.owner == original_fork["owner"]
            assert imported_fork.name == original_fork["name"]

    def test_import_classifications_with_errors(self, classifier):
        """Test importing classifications with invalid data."""
        # Invalid data (missing required fields)
        invalid_data = [
            {
                "fork_url": "https://github.com/user1/repo1",
                # Missing other required fields
            },
            {
                "fork_url": "https://github.com/user2/repo2",
                "owner": "user2",
                "name": "repo2",
                "created_at": "invalid-date",  # Invalid date format
                "pushed_at": "2024-01-01T00:00:00Z",
                "commit_status": "has_commits",
                "confidence_score": 0.8,
                "verification_method": "timestamp_analysis",
            },
        ]

        imported_count = classifier.import_classifications(invalid_data)
        assert imported_count == 0  # No valid imports
        assert classifier.get_classification_count() == 0

    def test_assign_status_with_confidence_edge_cases(self, classifier):
        """Test edge cases in status assignment with confidence thresholds."""
        # Test exactly at thresholds
        base_time = datetime.now(UTC)

        # Exactly at high confidence threshold
        analysis_high = TimestampAnalysisResult(
            created_at=base_time,
            pushed_at=base_time,
            status=CommitStatus.HAS_COMMITS,
            confidence_score=0.9,  # Exactly at high threshold
            time_difference_days=0,
            analysis_notes="Exactly high confidence",
        )

        result_high = classifier._assign_status_with_confidence(analysis_high)
        assert result_high == CommitStatus.HAS_COMMITS

        # Exactly at medium confidence threshold
        analysis_medium = TimestampAnalysisResult(
            created_at=base_time,
            pushed_at=base_time,
            status=CommitStatus.NO_COMMITS,
            confidence_score=0.7,  # Exactly at medium threshold
            time_difference_days=0,
            analysis_notes="Exactly medium confidence",
        )

        result_medium = classifier._assign_status_with_confidence(analysis_medium)
        assert result_medium == CommitStatus.NO_COMMITS

        # Exactly at low confidence threshold
        analysis_low = TimestampAnalysisResult(
            created_at=base_time,
            pushed_at=base_time,
            status=CommitStatus.HAS_COMMITS,
            confidence_score=0.3,  # Exactly at low threshold
            time_difference_days=0,
            analysis_notes="Exactly low confidence",
        )

        result_low = classifier._assign_status_with_confidence(analysis_low)
        assert (
            result_low == CommitStatus.UNKNOWN
        )  # Low confidence HAS_COMMITS becomes UNKNOWN

        # Below low confidence threshold
        analysis_very_low = TimestampAnalysisResult(
            created_at=base_time,
            pushed_at=base_time,
            status=CommitStatus.NO_COMMITS,
            confidence_score=0.1,  # Below low threshold
            time_difference_days=0,
            analysis_notes="Very low confidence",
        )

        result_very_low = classifier._assign_status_with_confidence(analysis_very_low)
        assert (
            result_very_low == CommitStatus.UNKNOWN
        )  # Very low confidence always becomes UNKNOWN

    def test_assign_status_preserves_unknown_and_verified_statuses(self, classifier):
        """Test that UNKNOWN and VERIFIED statuses are preserved regardless of confidence."""
        base_time = datetime.now(UTC)

        # UNKNOWN status with low confidence should remain UNKNOWN
        analysis_unknown = TimestampAnalysisResult(
            created_at=base_time,
            pushed_at=base_time,
            status=CommitStatus.UNKNOWN,
            confidence_score=0.4,
            time_difference_days=0,
            analysis_notes="Unknown status",
        )

        result_unknown = classifier._assign_status_with_confidence(analysis_unknown)
        assert result_unknown == CommitStatus.UNKNOWN
