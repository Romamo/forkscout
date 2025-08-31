"""Tests for commits ahead detection data models."""

import pytest
from datetime import datetime, timezone
from src.forklift.models.commits_ahead_detection import (
    CommitStatus,
    ForkQualification,
    CommitDetectionResult,
    TimestampAnalysisResult,
)


class TestCommitStatus:
    """Test CommitStatus enum."""

    def test_commit_status_values(self):
        """Test that CommitStatus has all required values."""
        assert CommitStatus.HAS_COMMITS.value == "has_commits"
        assert CommitStatus.NO_COMMITS.value == "no_commits"
        assert CommitStatus.UNKNOWN.value == "unknown"
        assert CommitStatus.VERIFIED_AHEAD.value == "verified_ahead"
        assert CommitStatus.VERIFIED_NONE.value == "verified_none"

    def test_commit_status_string_representation(self):
        """Test string representation of CommitStatus."""
        assert CommitStatus.HAS_COMMITS.value == "has_commits"
        assert CommitStatus.NO_COMMITS.value == "no_commits"


class TestForkQualification:
    """Test ForkQualification dataclass."""

    def test_fork_qualification_creation(self):
        """Test creating ForkQualification with required fields."""
        created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        pushed_at = datetime(2023, 1, 15, tzinfo=timezone.utc)
        
        qualification = ForkQualification(
            fork_url="https://github.com/user/repo",
            owner="user",
            name="repo",
            created_at=created_at,
            pushed_at=pushed_at,
            commit_status=CommitStatus.HAS_COMMITS,
            confidence_score=0.95,
            verification_method="timestamp"
        )
        
        assert qualification.fork_url == "https://github.com/user/repo"
        assert qualification.owner == "user"
        assert qualification.name == "repo"
        assert qualification.created_at == created_at
        assert qualification.pushed_at == pushed_at
        assert qualification.commit_status == CommitStatus.HAS_COMMITS
        assert qualification.confidence_score == 0.95
        assert qualification.verification_method == "timestamp"
        assert qualification.last_verified is None
        assert qualification.commits_ahead_count is None

    def test_fork_qualification_with_optional_fields(self):
        """Test ForkQualification with optional fields."""
        created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        pushed_at = datetime(2023, 1, 15, tzinfo=timezone.utc)
        verified_at = datetime(2023, 2, 1, tzinfo=timezone.utc)
        
        qualification = ForkQualification(
            fork_url="https://github.com/user/repo",
            owner="user",
            name="repo",
            created_at=created_at,
            pushed_at=pushed_at,
            commit_status=CommitStatus.VERIFIED_AHEAD,
            confidence_score=1.0,
            verification_method="api",
            last_verified=verified_at,
            commits_ahead_count=5
        )
        
        assert qualification.last_verified == verified_at
        assert qualification.commits_ahead_count == 5

    def test_fork_qualification_confidence_score_validation(self):
        """Test confidence score validation."""
        created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        pushed_at = datetime(2023, 1, 15, tzinfo=timezone.utc)
        
        # Valid confidence scores
        for score in [0.0, 0.5, 1.0]:
            qualification = ForkQualification(
                fork_url="https://github.com/user/repo",
                owner="user",
                name="repo",
                created_at=created_at,
                pushed_at=pushed_at,
                commit_status=CommitStatus.HAS_COMMITS,
                confidence_score=score,
                verification_method="timestamp"
            )
            assert qualification.confidence_score == score

    def test_fork_qualification_serialization(self):
        """Test ForkQualification serialization and deserialization."""
        created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        pushed_at = datetime(2023, 1, 15, tzinfo=timezone.utc)
        
        original = ForkQualification(
            fork_url="https://github.com/user/repo",
            owner="user",
            name="repo",
            created_at=created_at,
            pushed_at=pushed_at,
            commit_status=CommitStatus.HAS_COMMITS,
            confidence_score=0.95,
            verification_method="timestamp"
        )
        
        # Test that it can be converted to dict and back
        data = original.__dict__
        reconstructed = ForkQualification(**data)
        
        assert reconstructed.fork_url == original.fork_url
        assert reconstructed.commit_status == original.commit_status
        assert reconstructed.confidence_score == original.confidence_score


class TestTimestampAnalysisResult:
    """Test TimestampAnalysisResult dataclass."""

    def test_timestamp_analysis_result_creation(self):
        """Test creating TimestampAnalysisResult."""
        created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        pushed_at = datetime(2023, 1, 15, tzinfo=timezone.utc)
        
        result = TimestampAnalysisResult(
            created_at=created_at,
            pushed_at=pushed_at,
            status=CommitStatus.HAS_COMMITS,
            confidence_score=0.95,
            time_difference_days=14,
            analysis_notes="pushed_at is 14 days after created_at"
        )
        
        assert result.created_at == created_at
        assert result.pushed_at == pushed_at
        assert result.status == CommitStatus.HAS_COMMITS
        assert result.confidence_score == 0.95
        assert result.time_difference_days == 14
        assert result.analysis_notes == "pushed_at is 14 days after created_at"

    def test_timestamp_analysis_result_with_same_timestamps(self):
        """Test TimestampAnalysisResult with same timestamps."""
        timestamp = datetime(2023, 1, 1, tzinfo=timezone.utc)
        
        result = TimestampAnalysisResult(
            created_at=timestamp,
            pushed_at=timestamp,
            status=CommitStatus.NO_COMMITS,
            confidence_score=0.8,
            time_difference_days=0,
            analysis_notes="created_at equals pushed_at"
        )
        
        assert result.time_difference_days == 0
        assert result.status == CommitStatus.NO_COMMITS


class TestCommitDetectionResult:
    """Test CommitDetectionResult dataclass."""

    def test_commit_detection_result_creation(self):
        """Test creating CommitDetectionResult."""
        result = CommitDetectionResult(
            total_forks=100,
            has_commits=30,
            no_commits=60,
            unknown_status=10,
            api_calls_saved=70,
            processing_time=5.5,
            confidence_distribution={"high": 80, "medium": 15, "low": 5}
        )
        
        assert result.total_forks == 100
        assert result.has_commits == 30
        assert result.no_commits == 60
        assert result.unknown_status == 10
        assert result.api_calls_saved == 70
        assert result.processing_time == 5.5
        assert result.confidence_distribution == {"high": 80, "medium": 15, "low": 5}

    def test_commit_detection_result_validation(self):
        """Test CommitDetectionResult validation."""
        # Test that counts add up correctly
        result = CommitDetectionResult(
            total_forks=100,
            has_commits=30,
            no_commits=60,
            unknown_status=10,
            api_calls_saved=70,
            processing_time=5.5,
            confidence_distribution={}
        )
        
        # Verify the counts add up to total
        assert result.has_commits + result.no_commits + result.unknown_status == result.total_forks

    def test_commit_detection_result_empty_confidence_distribution(self):
        """Test CommitDetectionResult with empty confidence distribution."""
        result = CommitDetectionResult(
            total_forks=0,
            has_commits=0,
            no_commits=0,
            unknown_status=0,
            api_calls_saved=0,
            processing_time=0.0,
            confidence_distribution={}
        )
        
        assert result.confidence_distribution == {}
        assert result.total_forks == 0


class TestDataModelIntegration:
    """Test integration between different data models."""

    def test_fork_qualification_to_detection_result_integration(self):
        """Test that ForkQualification data can be aggregated into CommitDetectionResult."""
        created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        
        # Create sample qualifications
        qualifications = [
            ForkQualification(
                fork_url="https://github.com/user1/repo",
                owner="user1",
                name="repo",
                created_at=created_at,
                pushed_at=datetime(2023, 1, 15, tzinfo=timezone.utc),
                commit_status=CommitStatus.HAS_COMMITS,
                confidence_score=0.95,
                verification_method="timestamp"
            ),
            ForkQualification(
                fork_url="https://github.com/user2/repo",
                owner="user2",
                name="repo",
                created_at=created_at,
                pushed_at=created_at,  # Same as created_at
                commit_status=CommitStatus.NO_COMMITS,
                confidence_score=0.9,
                verification_method="timestamp"
            ),
            ForkQualification(
                fork_url="https://github.com/user3/repo",
                owner="user3",
                name="repo",
                created_at=created_at,
                pushed_at=created_at,
                commit_status=CommitStatus.UNKNOWN,
                confidence_score=0.5,
                verification_method="timestamp"
            )
        ]
        
        # Aggregate into detection result
        has_commits = sum(1 for q in qualifications if q.commit_status == CommitStatus.HAS_COMMITS)
        no_commits = sum(1 for q in qualifications if q.commit_status == CommitStatus.NO_COMMITS)
        unknown = sum(1 for q in qualifications if q.commit_status == CommitStatus.UNKNOWN)
        
        result = CommitDetectionResult(
            total_forks=len(qualifications),
            has_commits=has_commits,
            no_commits=no_commits,
            unknown_status=unknown,
            api_calls_saved=2,  # Saved 2 API calls by using timestamp analysis
            processing_time=1.0,
            confidence_distribution={"high": 2, "medium": 1, "low": 0}
        )
        
        assert result.total_forks == 3
        assert result.has_commits == 1
        assert result.no_commits == 1
        assert result.unknown_status == 1
        assert result.api_calls_saved == 2

    def test_timestamp_analysis_to_fork_qualification_integration(self):
        """Test converting TimestampAnalysisResult to ForkQualification."""
        created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        pushed_at = datetime(2023, 1, 15, tzinfo=timezone.utc)
        
        # Create timestamp analysis result
        analysis = TimestampAnalysisResult(
            created_at=created_at,
            pushed_at=pushed_at,
            status=CommitStatus.HAS_COMMITS,
            confidence_score=0.95,
            time_difference_days=14,
            analysis_notes="pushed_at is 14 days after created_at"
        )
        
        # Convert to fork qualification
        qualification = ForkQualification(
            fork_url="https://github.com/user/repo",
            owner="user",
            name="repo",
            created_at=analysis.created_at,
            pushed_at=analysis.pushed_at,
            commit_status=analysis.status,
            confidence_score=analysis.confidence_score,
            verification_method="timestamp"
        )
        
        assert qualification.created_at == analysis.created_at
        assert qualification.pushed_at == analysis.pushed_at
        assert qualification.commit_status == analysis.status
        assert qualification.confidence_score == analysis.confidence_score