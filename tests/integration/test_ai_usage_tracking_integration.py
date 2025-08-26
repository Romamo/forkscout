"""Integration tests for AI usage tracking and cost monitoring."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from forklift.ai.client import OpenAIClient, OpenAIResponse
from forklift.ai.summary_engine import AICommitSummaryEngine
from forklift.models.ai_summary import AISummaryConfig, AIUsageTracker
from forklift.models.github import Commit, Repository, User


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    client = AsyncMock(spec=OpenAIClient)
    return client


@pytest.fixture
def ai_config():
    """Create AI summary configuration for testing."""
    return AISummaryConfig(
        enabled=True,
        model="gpt-4o-mini",
        max_tokens=150,
        max_cost_per_session_usd=1.0,
        max_cost_per_request_usd=0.001,  # Very low limit for testing
        cost_warning_threshold_usd=0.50,
        usage_logging_enabled=True,
        performance_logging_enabled=True,
        input_cost_per_1k_tokens=0.00015,
        output_cost_per_1k_tokens=0.0006
    )


@pytest.fixture
def summary_engine(mock_openai_client, ai_config):
    """Create AI summary engine with mocked client."""
    return AICommitSummaryEngine(
        openai_client=mock_openai_client,
        config=ai_config
    )


@pytest.fixture
def sample_commit():
    """Create a sample commit for testing."""

    author = User(
        id=12345,
        login="johndoe",
        name="John Doe",
        html_url="https://github.com/johndoe"
    )

    return Commit(
        sha="abc123def456789012345678901234567890abcd",  # 40 character SHA
        message="feat: add user authentication system",
        author=author,
        date=datetime(2024, 1, 15, 10, 30, 0),
        files_changed=["auth.py", "models/user.py", "tests/test_auth.py"],
        additions=150,
        deletions=20
    )


@pytest.fixture
def sample_repository():
    """Create a sample repository for testing."""
    return Repository(
        owner="testuser",
        name="testrepo",
        full_name="testuser/testrepo",
        url="https://api.github.com/repos/testuser/testrepo",
        html_url="https://github.com/testuser/testrepo",
        clone_url="https://github.com/testuser/testrepo.git",
        default_branch="main",
        stars=100,
        forks_count=25
    )


class TestAIUsageTrackingIntegration:
    """Test AI usage tracking integration with summary engine."""

    @pytest.mark.asyncio
    async def test_successful_request_tracking(self, summary_engine, sample_commit, mock_openai_client):
        """Test that successful requests are tracked correctly."""
        # Mock successful API response
        mock_response = OpenAIResponse(
            text="This commit adds a user authentication system with login and registration functionality.",
            usage={
                "prompt_tokens": 200,
                "completion_tokens": 100,
                "total_tokens": 300
            },
            model="gpt-4o-mini",
            finish_reason="stop"
        )
        mock_openai_client.create_completion_with_retry.return_value = mock_response

        # Generate summary
        diff_text = "diff --git a/auth.py b/auth.py\n+def authenticate_user():\n+    pass"
        result = await summary_engine.generate_commit_summary(sample_commit, diff_text)

        # Verify request was tracked
        stats = summary_engine.get_usage_stats()
        assert stats.total_requests == 1
        assert stats.successful_requests == 1
        assert stats.failed_requests == 0
        assert stats.total_tokens_used == 300
        assert stats.input_tokens_used == 200
        assert stats.output_tokens_used == 100

        # Verify cost calculation
        expected_input_cost = summary_engine.config.calculate_input_cost(200)
        expected_output_cost = summary_engine.config.calculate_output_cost(100)
        expected_total_cost = expected_input_cost + expected_output_cost

        assert stats.input_cost_usd == expected_input_cost
        assert stats.output_cost_usd == expected_output_cost
        assert stats.total_cost_usd == expected_total_cost

        # Verify summary was created successfully
        assert result.commit_sha == sample_commit.sha
        assert result.error is None
        assert result.tokens_used == 300

    @pytest.mark.asyncio
    async def test_failed_request_tracking(self, summary_engine, sample_commit, mock_openai_client):
        """Test that failed requests are tracked correctly."""
        # Mock API failure
        mock_openai_client.create_completion_with_retry.side_effect = Exception("API Error")

        # Generate summary (should handle error gracefully)
        diff_text = "diff --git a/auth.py b/auth.py\n+def authenticate_user():\n+    pass"
        result = await summary_engine.generate_commit_summary(sample_commit, diff_text)

        # Verify request was tracked as failed
        stats = summary_engine.get_usage_stats()
        assert stats.total_requests == 1
        assert stats.successful_requests == 0
        assert stats.failed_requests == 1
        assert stats.total_tokens_used == 0
        assert stats.total_cost_usd == 0.0

        # Verify error summary was created
        assert result.commit_sha == sample_commit.sha
        assert result.error is not None
        assert result.tokens_used == 0

    @pytest.mark.asyncio
    async def test_session_cost_limit_enforcement(self, summary_engine, sample_commit, mock_openai_client):
        """Test that session cost limits are enforced."""
        # Set up tracker to exceed the limit
        summary_engine.usage_tracker.stats.total_cost_usd = 1.5  # Exceeds $1.00 limit

        # Generate summary (should be blocked by cost limit)
        diff_text = "diff --git a/auth.py b/auth.py\n+def authenticate_user():\n+    pass"
        result = await summary_engine.generate_commit_summary(sample_commit, diff_text)

        # Verify request was blocked
        assert result.error is not None
        assert "Session cost limit exceeded" in result.error
        assert mock_openai_client.create_completion_with_retry.call_count == 0

        # Verify stats were updated
        stats = summary_engine.get_usage_stats()
        assert stats.total_requests == 1
        assert stats.failed_requests == 1

    def test_request_cost_limit_check(self, ai_config):
        """Test that request cost limit checking works correctly."""
        tracker = AIUsageTracker(config=ai_config)

        # Test with cost under limit
        assert tracker.check_request_cost_limit(0.0005) is True

        # Test with cost over limit
        assert tracker.check_request_cost_limit(0.002) is False

        # Test with cost at limit
        assert tracker.check_request_cost_limit(0.001) is True

    def test_cost_warning_threshold(self, ai_config):
        """Test that cost warning threshold checking works correctly."""
        tracker = AIUsageTracker(config=ai_config)

        # Test under threshold
        tracker.stats.total_cost_usd = 0.30
        assert tracker.should_warn_about_cost() is False

        # Test over threshold
        tracker.stats.total_cost_usd = 0.60
        assert tracker.should_warn_about_cost() is True

        # Test at threshold
        tracker.stats.total_cost_usd = 0.50
        assert tracker.should_warn_about_cost() is True

    @pytest.mark.asyncio
    async def test_performance_logging(self, summary_engine, sample_commit, mock_openai_client, caplog):
        """Test that performance metrics are logged."""
        # Mock successful API response
        mock_response = OpenAIResponse(
            text="Summary text",
            usage={
                "prompt_tokens": 200,
                "completion_tokens": 100,
                "total_tokens": 300
            },
            model="gpt-4o-mini",
            finish_reason="stop"
        )
        mock_openai_client.create_completion_with_retry.return_value = mock_response

        # Generate summary
        diff_text = "diff --git a/auth.py b/auth.py\n+def authenticate_user():\n+    pass"

        with caplog.at_level("INFO"):
            await summary_engine.generate_commit_summary(sample_commit, diff_text)

        # Verify performance logging
        info_messages = [record.message for record in caplog.records if record.levelname == "INFO"]
        performance_logs = [msg for msg in info_messages if "Generated AI summary" in msg and "Time:" in msg]
        assert len(performance_logs) > 0

        # Check that log contains expected metrics
        log_msg = performance_logs[0]
        assert "Time:" in log_msg
        assert "Tokens:" in log_msg
        assert "Cost:" in log_msg

    @pytest.mark.asyncio
    async def test_batch_processing_usage_tracking(self, summary_engine, sample_commit, mock_openai_client):
        """Test usage tracking during batch processing."""
        # Create multiple commits
        commits_with_diffs = [
            (sample_commit, "diff1"),
            (sample_commit, "diff2"),
            (sample_commit, "diff3")
        ]

        # Mock successful API responses
        mock_response = OpenAIResponse(
            text="Summary text",
            usage={
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            },
            model="gpt-4o-mini",
            finish_reason="stop"
        )
        mock_openai_client.create_completion_with_retry.return_value = mock_response

        # Process batch
        results = await summary_engine.generate_batch_summaries(commits_with_diffs)

        # Verify all requests were tracked
        stats = summary_engine.get_usage_stats()
        assert stats.total_requests == 3
        assert stats.successful_requests == 3
        assert stats.failed_requests == 0
        assert stats.total_tokens_used == 450  # 150 * 3

        # Verify all summaries were created
        assert len(results) == 3
        assert all(result.error is None for result in results)

    def test_usage_report_generation(self, summary_engine):
        """Test comprehensive usage report generation."""
        # Simulate some usage
        tracker = summary_engine.usage_tracker
        tracker.record_request(
            success=True,
            input_tokens=200,
            output_tokens=100,
            processing_time_ms=1500.0
        )
        tracker.record_request(
            success=False,
            processing_time_ms=800.0,
            error="Rate limit"
        )

        # Generate report
        report = summary_engine.get_usage_report()

        # Verify report structure and content
        assert "session_summary" in report
        assert "token_usage" in report
        assert "cost_breakdown" in report
        assert "performance" in report
        assert "limits" in report

        # Verify specific values
        session = report["session_summary"]
        assert session["total_requests"] == 2
        assert session["success_rate_percent"] == 50.0

        tokens = report["token_usage"]
        assert tokens["total_tokens"] == 300
        assert tokens["input_tokens"] == 200
        assert tokens["output_tokens"] == 100

    def test_usage_stats_reset(self, summary_engine):
        """Test resetting usage statistics."""
        # Record some usage
        tracker = summary_engine.usage_tracker
        tracker.record_request(
            success=True,
            input_tokens=100,
            output_tokens=50,
            processing_time_ms=1000.0
        )

        # Verify stats are recorded
        stats = summary_engine.get_usage_stats()
        assert stats.total_requests == 1
        assert stats.total_tokens_used == 150

        # Reset stats
        summary_engine.reset_usage_stats()

        # Verify stats are reset
        new_stats = summary_engine.get_usage_stats()
        assert new_stats.total_requests == 0
        assert new_stats.total_tokens_used == 0
        assert new_stats.total_cost_usd == 0.0

    @pytest.mark.asyncio
    async def test_usage_logging_summary(self, summary_engine, sample_commit, mock_openai_client, caplog):
        """Test that usage summary is logged after batch processing."""
        # Create commits for batch processing
        commits_with_diffs = [
            (sample_commit, "diff1"),
            (sample_commit, "diff2")
        ]

        # Mock successful API responses
        mock_response = OpenAIResponse(
            text="Summary text",
            usage={
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            },
            model="gpt-4o-mini",
            finish_reason="stop"
        )
        mock_openai_client.create_completion_with_retry.return_value = mock_response

        # Process batch
        with caplog.at_level("INFO"):
            await summary_engine.generate_batch_summaries(commits_with_diffs)

        # Verify usage summary was logged
        info_messages = [record.message for record in caplog.records if record.levelname == "INFO"]
        usage_summary_logs = [msg for msg in info_messages if "AI Usage Summary" in msg]
        assert len(usage_summary_logs) > 0

        # Check that summary contains expected metrics
        summary_log = usage_summary_logs[0]
        assert "Requests:" in summary_log
        assert "Success:" in summary_log
        assert "Tokens:" in summary_log
        assert "Cost:" in summary_log
        assert "Duration:" in summary_log

    def test_cost_calculation_accuracy(self, ai_config):
        """Test that cost calculations are accurate."""
        # Test with known values
        input_tokens = 1000
        output_tokens = 500

        expected_input_cost = (input_tokens / 1000.0) * ai_config.input_cost_per_1k_tokens
        expected_output_cost = (output_tokens / 1000.0) * ai_config.output_cost_per_1k_tokens
        expected_total_cost = expected_input_cost + expected_output_cost

        assert ai_config.calculate_input_cost(input_tokens) == expected_input_cost
        assert ai_config.calculate_output_cost(output_tokens) == expected_output_cost
        assert ai_config.calculate_total_cost(input_tokens, output_tokens) == expected_total_cost

        # Test with GPT-4o-mini pricing
        assert ai_config.calculate_input_cost(1000) == 0.00015  # $0.00015 per 1K input tokens
        assert ai_config.calculate_output_cost(1000) == 0.0006   # $0.0006 per 1K output tokens

    def test_usage_tracker_limits_configuration(self, ai_config):
        """Test that usage tracker respects configuration limits."""
        tracker = AIUsageTracker(config=ai_config)

        # Test session limit
        assert tracker.config.max_cost_per_session_usd == 1.0
        tracker.stats.total_cost_usd = 0.5
        assert tracker.check_session_cost_limit() is True

        tracker.stats.total_cost_usd = 1.5
        assert tracker.check_session_cost_limit() is False

        # Test request limit
        assert tracker.config.max_cost_per_request_usd == 0.001
        assert tracker.check_request_cost_limit(0.0005) is True
        assert tracker.check_request_cost_limit(0.002) is False

        # Test warning threshold
        assert tracker.config.cost_warning_threshold_usd == 0.50
        tracker.stats.total_cost_usd = 0.30
        assert tracker.should_warn_about_cost() is False

        tracker.stats.total_cost_usd = 0.60
        assert tracker.should_warn_about_cost() is True
