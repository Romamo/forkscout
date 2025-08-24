"""Unit tests for AI summary data models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from forklift.models.ai_summary import (
    AISummary,
    AISummaryConfig,
    CommitDetails,
    AIUsageStats,
    AIError,
    AIErrorType,
)


class TestAISummary:
    """Test cases for AISummary model."""

    def test_ai_summary_creation_with_required_fields(self):
        """Test creating AISummary with required fields."""
        summary = AISummary(
            commit_sha="abc123",
            summary_text="This commit adds user authentication functionality to secure user access"
        )
        
        assert summary.commit_sha == "abc123"
        assert summary.summary_text == "This commit adds user authentication functionality to secure user access"
        assert summary.model_used == "gpt-4o-mini"  # Default value
        assert summary.tokens_used == 0  # Default value
        assert summary.processing_time_ms == 0.0  # Default value
        assert summary.error is None  # Default value
        assert isinstance(summary.generated_at, datetime)

    def test_ai_summary_creation_with_all_fields(self):
        """Test creating AISummary with all fields."""
        generated_at = datetime(2024, 1, 15, 10, 30, 0)
        
        summary = AISummary(
            commit_sha="def456",
            summary_text="Complete summary text describing database schema modifications for performance improvements",
            generated_at=generated_at,
            model_used="gpt-4",
            tokens_used=150,
            processing_time_ms=1250.5,
            error=None
        )
        
        assert summary.commit_sha == "def456"
        assert summary.summary_text == "Complete summary text describing database schema modifications for performance improvements"
        assert summary.model_used == "gpt-4"
        assert summary.tokens_used == 150
        assert summary.processing_time_ms == 1250.5
        assert summary.generated_at == generated_at

    def test_ai_summary_with_error(self):
        """Test creating AISummary with error information."""
        summary = AISummary(
            commit_sha="error123",
            summary_text="",
            error="Rate limit exceeded"
        )
        
        assert summary.error == "Rate limit exceeded"
        assert summary.summary_text == ""

    def test_ai_summary_validation_negative_tokens(self):
        """Test that negative tokens_used raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AISummary(
                commit_sha="abc123",
                summary_text="Test",
                tokens_used=-1
            )
        
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_ai_summary_validation_negative_processing_time(self):
        """Test that negative processing_time_ms raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AISummary(
                commit_sha="abc123",
                summary_text="Test",
                processing_time_ms=-1.0
            )
        
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_ai_summary_serialization(self):
        """Test AISummary serialization to dict."""
        summary = AISummary(
            commit_sha="serialize123",
            summary_text="Test summary with comprehensive details"
        )
        
        data = summary.model_dump()
        
        assert data["commit_sha"] == "serialize123"
        assert data["summary_text"] == "Test summary with comprehensive details"
        assert data["model_used"] == "gpt-4o-mini"
        assert "generated_at" in data

    def test_ai_summary_deserialization(self):
        """Test AISummary deserialization from dict."""
        data = {
            "commit_sha": "deserialize123",
            "summary_text": "Test summary with comprehensive details",
            "generated_at": "2024-01-15T10:30:00",
            "model_used": "gpt-4o-mini",
            "tokens_used": 100,
            "processing_time_ms": 500.0,
            "error": None
        }
        
        summary = AISummary(**data)
        
        assert summary.commit_sha == "deserialize123"
        assert summary.tokens_used == 100
        assert summary.processing_time_ms == 500.0


class TestAISummaryConfig:
    """Test cases for AISummaryConfig model."""

    def test_ai_summary_config_defaults(self):
        """Test AISummaryConfig with default values."""
        config = AISummaryConfig()
        
        assert config.enabled is False
        assert config.model == "gpt-4o-mini"
        assert config.max_tokens == 150
        assert config.max_diff_chars == 8000
        assert config.temperature == 0.3
        assert config.timeout_seconds == 30
        assert config.retry_attempts == 3
        assert config.cost_tracking is True
        assert config.batch_size == 5
        assert config.compact_mode is False

    def test_ai_summary_config_custom_values(self):
        """Test AISummaryConfig with custom values."""
        config = AISummaryConfig(
            enabled=True,
            model="gpt-4",
            max_tokens=1000,
            max_diff_chars=10000,
            temperature=0.5,
            timeout_seconds=60,
            retry_attempts=5,
            cost_tracking=False,
            batch_size=10,
            compact_mode=True
        )
        
        assert config.enabled is True
        assert config.model == "gpt-4"
        assert config.max_tokens == 1000
        assert config.max_diff_chars == 10000
        assert config.temperature == 0.5
        assert config.timeout_seconds == 60
        assert config.retry_attempts == 5
        assert config.cost_tracking is False
        assert config.batch_size == 10
        assert config.compact_mode is True

    def test_ai_summary_config_validation_max_tokens(self):
        """Test validation of max_tokens field."""
        # Test minimum value
        with pytest.raises(ValidationError):
            AISummaryConfig(max_tokens=0)
        
        # Test maximum value
        with pytest.raises(ValidationError):
            AISummaryConfig(max_tokens=5000)
        
        # Test valid values
        config = AISummaryConfig(max_tokens=1)
        assert config.max_tokens == 1
        
        config = AISummaryConfig(max_tokens=4000)
        assert config.max_tokens == 4000

    def test_ai_summary_config_validation_temperature(self):
        """Test validation of temperature field."""
        # Test minimum value
        with pytest.raises(ValidationError):
            AISummaryConfig(temperature=-0.1)
        
        # Test maximum value
        with pytest.raises(ValidationError):
            AISummaryConfig(temperature=2.1)
        
        # Test valid values
        config = AISummaryConfig(temperature=0.0)
        assert config.temperature == 0.0
        
        config = AISummaryConfig(temperature=2.0)
        assert config.temperature == 2.0

    def test_ai_summary_config_validation_batch_size(self):
        """Test validation of batch_size field."""
        # Test minimum value
        with pytest.raises(ValidationError):
            AISummaryConfig(batch_size=0)
        
        # Test maximum value
        with pytest.raises(ValidationError):
            AISummaryConfig(batch_size=21)
        
        # Test valid values
        config = AISummaryConfig(batch_size=1)
        assert config.batch_size == 1
        
        config = AISummaryConfig(batch_size=20)
        assert config.batch_size == 20


class TestCommitDetails:
    """Test cases for CommitDetails model."""

    def test_commit_details_creation_without_ai_summary(self):
        """Test creating CommitDetails without AI summary."""
        commit_date = datetime(2024, 1, 15, 10, 30, 0)
        
        details = CommitDetails(
            commit_sha="commit123",
            message="Fix bug in authentication",
            author="John Doe",
            date=commit_date,
            files_changed_count=3,
            lines_added=25,
            lines_removed=10,
            commit_url="https://github.com/owner/repo/commit/commit123"
        )
        
        assert details.commit_sha == "commit123"
        assert details.message == "Fix bug in authentication"
        assert details.author == "John Doe"
        assert details.date == commit_date
        assert details.files_changed_count == 3
        assert details.lines_added == 25
        assert details.lines_removed == 10
        assert details.commit_url == "https://github.com/owner/repo/commit/commit123"
        assert details.ai_summary is None

    def test_commit_details_creation_with_ai_summary(self):
        """Test creating CommitDetails with AI summary."""
        commit_date = datetime(2024, 1, 15, 10, 30, 0)
        ai_summary = AISummary(
            commit_sha="commit123",
            summary_text="This commit fixes authentication bug by modifying login validation to prevent unauthorized access"
        )
        
        details = CommitDetails(
            commit_sha="commit123",
            message="Fix bug in authentication",
            author="John Doe",
            date=commit_date,
            commit_url="https://github.com/owner/repo/commit/commit123",
            ai_summary=ai_summary
        )
        
        assert details.ai_summary is not None
        assert details.ai_summary.commit_sha == "commit123"
        assert details.ai_summary.summary_text == "This commit fixes authentication bug by modifying login validation to prevent unauthorized access"

    def test_commit_details_validation_negative_counts(self):
        """Test validation of count fields."""
        commit_date = datetime(2024, 1, 15, 10, 30, 0)
        
        # Test negative files_changed_count
        with pytest.raises(ValidationError):
            CommitDetails(
                commit_sha="test",
                message="test",
                author="test",
                date=commit_date,
                commit_url="https://github.com/test/test/commit/test",
                files_changed_count=-1
            )
        
        # Test negative lines_added
        with pytest.raises(ValidationError):
            CommitDetails(
                commit_sha="test",
                message="test",
                author="test",
                date=commit_date,
                commit_url="https://github.com/test/test/commit/test",
                lines_added=-1
            )
        
        # Test negative lines_removed
        with pytest.raises(ValidationError):
            CommitDetails(
                commit_sha="test",
                message="test",
                author="test",
                date=commit_date,
                commit_url="https://github.com/test/test/commit/test",
                lines_removed=-1
            )


class TestAIUsageStats:
    """Test cases for AIUsageStats model."""

    def test_ai_usage_stats_defaults(self):
        """Test AIUsageStats with default values."""
        stats = AIUsageStats()
        
        assert stats.total_requests == 0
        assert stats.successful_requests == 0
        assert stats.failed_requests == 0
        assert stats.total_tokens_used == 0
        assert stats.total_cost_usd == 0.0
        assert stats.average_processing_time_ms == 0.0
        assert isinstance(stats.session_start, datetime)
        assert stats.last_request is None

    def test_ai_usage_stats_custom_values(self):
        """Test AIUsageStats with custom values."""
        session_start = datetime(2024, 1, 15, 10, 0, 0)
        last_request = datetime(2024, 1, 15, 10, 30, 0)
        
        stats = AIUsageStats(
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
            total_tokens_used=50000,
            total_cost_usd=2.50,
            average_processing_time_ms=1250.5,
            session_start=session_start,
            last_request=last_request
        )
        
        assert stats.total_requests == 100
        assert stats.successful_requests == 95
        assert stats.failed_requests == 5
        assert stats.total_tokens_used == 50000
        assert stats.total_cost_usd == 2.50
        assert stats.average_processing_time_ms == 1250.5
        assert stats.session_start == session_start
        assert stats.last_request == last_request

    def test_ai_usage_stats_validation_negative_values(self):
        """Test validation of non-negative fields."""
        # Test negative total_requests
        with pytest.raises(ValidationError):
            AIUsageStats(total_requests=-1)
        
        # Test negative successful_requests
        with pytest.raises(ValidationError):
            AIUsageStats(successful_requests=-1)
        
        # Test negative failed_requests
        with pytest.raises(ValidationError):
            AIUsageStats(failed_requests=-1)
        
        # Test negative total_tokens_used
        with pytest.raises(ValidationError):
            AIUsageStats(total_tokens_used=-1)
        
        # Test negative total_cost_usd
        with pytest.raises(ValidationError):
            AIUsageStats(total_cost_usd=-0.01)
        
        # Test negative average_processing_time_ms
        with pytest.raises(ValidationError):
            AIUsageStats(average_processing_time_ms=-1.0)


class TestAIError:
    """Test cases for AIError model."""

    def test_ai_error_creation(self):
        """Test creating AIError with required fields."""
        error = AIError(
            error_type=AIErrorType.RATE_LIMIT,
            message="Rate limit exceeded"
        )
        
        assert error.error_type == AIErrorType.RATE_LIMIT
        assert error.message == "Rate limit exceeded"
        assert error.commit_sha is None
        assert error.retry_count == 0
        assert isinstance(error.timestamp, datetime)
        assert error.recoverable is True

    def test_ai_error_creation_with_all_fields(self):
        """Test creating AIError with all fields."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        
        error = AIError(
            error_type=AIErrorType.AUTHENTICATION,
            message="Invalid API key",
            commit_sha="error123",
            retry_count=3,
            timestamp=timestamp,
            recoverable=False
        )
        
        assert error.error_type == AIErrorType.AUTHENTICATION
        assert error.message == "Invalid API key"
        assert error.commit_sha == "error123"
        assert error.retry_count == 3
        assert error.timestamp == timestamp
        assert error.recoverable is False

    def test_ai_error_validation_negative_retry_count(self):
        """Test validation of retry_count field."""
        with pytest.raises(ValidationError):
            AIError(
                error_type=AIErrorType.TIMEOUT,
                message="Request timeout",
                retry_count=-1
            )


class TestAIErrorType:
    """Test cases for AIErrorType constants."""

    def test_ai_error_type_values(self):
        """Test that AIErrorType has expected values."""
        assert AIErrorType.AUTHENTICATION == "authentication"
        assert AIErrorType.RATE_LIMIT == "rate_limit"
        assert AIErrorType.TIMEOUT == "timeout"
        assert AIErrorType.INVALID_REQUEST == "invalid_request"
        assert AIErrorType.MODEL_ERROR == "model_error"
        assert AIErrorType.NETWORK_ERROR == "network_error"
        assert AIErrorType.UNKNOWN == "unknown"


class TestModelSerialization:
    """Test serialization and deserialization of all models."""

    def test_ai_summary_roundtrip(self):
        """Test AISummary serialization roundtrip."""
        original = AISummary(
            commit_sha="roundtrip123",
            summary_text="Test summary with comprehensive details",
            tokens_used=100,
            processing_time_ms=500.0
        )
        
        # Serialize to dict
        data = original.model_dump()
        
        # Deserialize back to object
        reconstructed = AISummary(**data)
        
        assert reconstructed.commit_sha == original.commit_sha
        assert reconstructed.summary_text == original.summary_text
        assert reconstructed.tokens_used == original.tokens_used
        assert reconstructed.processing_time_ms == original.processing_time_ms

    def test_commit_details_roundtrip(self):
        """Test CommitDetails serialization roundtrip."""
        ai_summary = AISummary(
            commit_sha="roundtrip123",
            summary_text="Test summary with comprehensive details"
        )
        
        original = CommitDetails(
            commit_sha="roundtrip123",
            message="Test commit",
            author="Test Author",
            date=datetime(2024, 1, 15, 10, 30, 0),
            files_changed_count=5,
            lines_added=100,
            lines_removed=50,
            commit_url="https://github.com/test/test/commit/roundtrip123",
            ai_summary=ai_summary
        )
        
        # Serialize to dict
        data = original.model_dump()
        
        # Deserialize back to object
        reconstructed = CommitDetails(**data)
        
        assert reconstructed.commit_sha == original.commit_sha
        assert reconstructed.message == original.message
        assert reconstructed.ai_summary is not None
        assert reconstructed.ai_summary.commit_sha == original.ai_summary.commit_sha

    def test_ai_usage_stats_roundtrip(self):
        """Test AIUsageStats serialization roundtrip."""
        original = AIUsageStats(
            total_requests=50,
            successful_requests=45,
            failed_requests=5,
            total_tokens_used=25000,
            total_cost_usd=1.25,
            average_processing_time_ms=750.0
        )
        
        # Serialize to dict
        data = original.model_dump()
        
        # Deserialize back to object
        reconstructed = AIUsageStats(**data)
        
        assert reconstructed.total_requests == original.total_requests
        assert reconstructed.successful_requests == original.successful_requests
        assert reconstructed.total_cost_usd == original.total_cost_usd

    def test_ai_summary_config_compact_mode(self):
        """Test AISummaryConfig compact_mode functionality."""
        # Test default compact_mode is False
        config = AISummaryConfig()
        assert config.compact_mode is False
        
        # Test setting compact_mode to True
        config_compact = AISummaryConfig(compact_mode=True)
        assert config_compact.compact_mode is True
        
        # Test that compact_mode can be combined with other settings
        config_full = AISummaryConfig(
            enabled=True,
            model="gpt-4o-mini",
            max_tokens=100,
            compact_mode=True
        )
        assert config_full.enabled is True
        assert config_full.model == "gpt-4o-mini"
        assert config_full.max_tokens == 100
        assert config_full.compact_mode is True

    def test_ai_summary_config_compact_mode_serialization(self):
        """Test AISummaryConfig compact_mode serialization."""
        config = AISummaryConfig(compact_mode=True)
        
        # Serialize to dict
        data = config.model_dump()
        assert data["compact_mode"] is True
        
        # Deserialize back to object
        reconstructed = AISummaryConfig(**data)
        assert reconstructed.compact_mode is True