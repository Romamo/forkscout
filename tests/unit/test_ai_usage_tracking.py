"""Tests for AI usage tracking and cost monitoring."""

from datetime import datetime, timedelta

import pytest

from forklift.models.ai_summary import (
    AISummaryConfig,
    AIUsageStats,
    AIUsageTracker,
)


class TestAISummaryConfig:
    """Test AI summary configuration with cost monitoring."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AISummaryConfig()

        assert config.enabled is False
        assert config.model == "gpt-4o-mini"
        assert config.max_tokens == 150
        assert config.cost_tracking is True
        assert config.max_cost_per_session_usd == 5.0
        assert config.max_cost_per_request_usd == 0.10
        assert config.cost_warning_threshold_usd == 1.0
        assert config.usage_logging_enabled is True
        assert config.performance_logging_enabled is True
        assert config.input_cost_per_1k_tokens == 0.00015
        assert config.output_cost_per_1k_tokens == 0.0006

    def test_calculate_input_cost(self):
        """Test input cost calculation."""
        config = AISummaryConfig()

        # Test with 1000 tokens
        cost = config.calculate_input_cost(1000)
        assert cost == 0.00015

        # Test with 500 tokens
        cost = config.calculate_input_cost(500)
        assert cost == 0.000075

        # Test with 0 tokens
        cost = config.calculate_input_cost(0)
        assert cost == 0.0

    def test_calculate_output_cost(self):
        """Test output cost calculation."""
        config = AISummaryConfig()

        # Test with 1000 tokens
        cost = config.calculate_output_cost(1000)
        assert cost == 0.0006

        # Test with 250 tokens
        cost = config.calculate_output_cost(250)
        assert cost == 0.00015

        # Test with 0 tokens
        cost = config.calculate_output_cost(0)
        assert cost == 0.0

    def test_calculate_total_cost(self):
        """Test total cost calculation."""
        config = AISummaryConfig()

        # Test with 1000 input and 500 output tokens
        cost = config.calculate_total_cost(1000, 500)
        expected = 0.00015 + 0.0003  # input + output
        assert cost == expected

        # Test with 0 tokens
        cost = config.calculate_total_cost(0, 0)
        assert cost == 0.0

    def test_estimate_request_cost(self):
        """Test request cost estimation."""
        config = AISummaryConfig()

        # Test with short prompt
        prompt = "Hello world"  # ~3 tokens
        cost = config.estimate_request_cost(prompt)

        # Should estimate input tokens and use max_tokens for output
        expected_input_tokens = len(prompt) // 4
        expected_output_tokens = config.max_tokens
        expected_cost = config.calculate_total_cost(expected_input_tokens, expected_output_tokens)

        assert cost == expected_cost

    def test_estimate_request_cost_with_custom_output(self):
        """Test request cost estimation with custom output tokens."""
        config = AISummaryConfig()

        prompt = "Hello world"
        max_output = 100
        cost = config.estimate_request_cost(prompt, max_output)

        expected_input_tokens = len(prompt) // 4
        expected_cost = config.calculate_total_cost(expected_input_tokens, max_output)

        assert cost == expected_cost


class TestAIUsageStats:
    """Test AI usage statistics model."""

    def test_default_stats(self):
        """Test default statistics values."""
        stats = AIUsageStats()

        assert stats.total_requests == 0
        assert stats.successful_requests == 0
        assert stats.failed_requests == 0
        assert stats.total_tokens_used == 0
        assert stats.input_tokens_used == 0
        assert stats.output_tokens_used == 0
        assert stats.total_cost_usd == 0.0
        assert stats.input_cost_usd == 0.0
        assert stats.output_cost_usd == 0.0
        assert stats.average_processing_time_ms == 0.0
        assert stats.min_processing_time_ms == 0.0
        assert stats.max_processing_time_ms == 0.0
        assert isinstance(stats.session_start, datetime)
        assert stats.last_request is None

    def test_get_success_rate_no_requests(self):
        """Test success rate calculation with no requests."""
        stats = AIUsageStats()
        assert stats.get_success_rate() == 0.0

    def test_get_success_rate_with_requests(self):
        """Test success rate calculation with requests."""
        stats = AIUsageStats()
        stats.total_requests = 10
        stats.successful_requests = 8

        assert stats.get_success_rate() == 80.0

    def test_get_average_tokens_per_request_no_requests(self):
        """Test average tokens per request with no successful requests."""
        stats = AIUsageStats()
        assert stats.get_average_tokens_per_request() == 0.0

    def test_get_average_tokens_per_request_with_requests(self):
        """Test average tokens per request with successful requests."""
        stats = AIUsageStats()
        stats.successful_requests = 5
        stats.total_tokens_used = 1000

        assert stats.get_average_tokens_per_request() == 200.0

    def test_get_cost_per_request_no_requests(self):
        """Test cost per request with no successful requests."""
        stats = AIUsageStats()
        assert stats.get_cost_per_request() == 0.0

    def test_get_cost_per_request_with_requests(self):
        """Test cost per request with successful requests."""
        stats = AIUsageStats()
        stats.successful_requests = 4
        stats.total_cost_usd = 0.20

        assert stats.get_cost_per_request() == 0.05

    def test_get_session_duration_minutes(self):
        """Test session duration calculation."""
        stats = AIUsageStats()

        # Mock session start time
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        stats.session_start = start_time

        # Mock last request time (30 minutes later)
        last_request = datetime(2024, 1, 1, 12, 30, 0)
        stats.last_request = last_request

        assert stats.get_session_duration_minutes() == 30.0

    def test_get_session_duration_minutes_no_last_request(self):
        """Test session duration calculation with no last request."""
        stats = AIUsageStats()

        # Mock session start time (1 hour ago)
        start_time = datetime.utcnow() - timedelta(hours=1)
        stats.session_start = start_time

        # Should use current time
        duration = stats.get_session_duration_minutes()
        assert 59 <= duration <= 61  # Allow for small timing differences


class TestAIUsageTracker:
    """Test AI usage tracker with cost monitoring."""

    def test_initialization(self):
        """Test usage tracker initialization."""
        config = AISummaryConfig()
        tracker = AIUsageTracker(config=config)

        assert tracker.config == config
        assert isinstance(tracker.stats, AIUsageStats)

    def test_check_session_cost_limit_under_limit(self):
        """Test session cost limit check when under limit."""
        config = AISummaryConfig(max_cost_per_session_usd=5.0)
        tracker = AIUsageTracker(config=config)
        tracker.stats.total_cost_usd = 2.0

        assert tracker.check_session_cost_limit() is True

    def test_check_session_cost_limit_over_limit(self):
        """Test session cost limit check when over limit."""
        config = AISummaryConfig(max_cost_per_session_usd=5.0)
        tracker = AIUsageTracker(config=config)
        tracker.stats.total_cost_usd = 6.0

        assert tracker.check_session_cost_limit() is False

    def test_check_session_cost_limit_at_limit(self):
        """Test session cost limit check when at limit."""
        config = AISummaryConfig(max_cost_per_session_usd=5.0)
        tracker = AIUsageTracker(config=config)
        tracker.stats.total_cost_usd = 5.0

        assert tracker.check_session_cost_limit() is False

    def test_check_request_cost_limit_under_limit(self):
        """Test request cost limit check when under limit."""
        config = AISummaryConfig(max_cost_per_request_usd=0.10)
        tracker = AIUsageTracker(config=config)

        assert tracker.check_request_cost_limit(0.05) is True

    def test_check_request_cost_limit_over_limit(self):
        """Test request cost limit check when over limit."""
        config = AISummaryConfig(max_cost_per_request_usd=0.10)
        tracker = AIUsageTracker(config=config)

        assert tracker.check_request_cost_limit(0.15) is False

    def test_check_request_cost_limit_at_limit(self):
        """Test request cost limit check when at limit."""
        config = AISummaryConfig(max_cost_per_request_usd=0.10)
        tracker = AIUsageTracker(config=config)

        assert tracker.check_request_cost_limit(0.10) is True

    def test_should_warn_about_cost_under_threshold(self):
        """Test cost warning check when under threshold."""
        config = AISummaryConfig(cost_warning_threshold_usd=1.0)
        tracker = AIUsageTracker(config=config)
        tracker.stats.total_cost_usd = 0.5

        assert tracker.should_warn_about_cost() is False

    def test_should_warn_about_cost_over_threshold(self):
        """Test cost warning check when over threshold."""
        config = AISummaryConfig(cost_warning_threshold_usd=1.0)
        tracker = AIUsageTracker(config=config)
        tracker.stats.total_cost_usd = 1.5

        assert tracker.should_warn_about_cost() is True

    def test_should_warn_about_cost_at_threshold(self):
        """Test cost warning check when at threshold."""
        config = AISummaryConfig(cost_warning_threshold_usd=1.0)
        tracker = AIUsageTracker(config=config)
        tracker.stats.total_cost_usd = 1.0

        assert tracker.should_warn_about_cost() is True

    def test_get_remaining_budget(self):
        """Test remaining budget calculation."""
        config = AISummaryConfig(max_cost_per_session_usd=5.0)
        tracker = AIUsageTracker(config=config)
        tracker.stats.total_cost_usd = 2.0

        assert tracker.get_remaining_budget() == 3.0

    def test_get_remaining_budget_over_limit(self):
        """Test remaining budget calculation when over limit."""
        config = AISummaryConfig(max_cost_per_session_usd=5.0)
        tracker = AIUsageTracker(config=config)
        tracker.stats.total_cost_usd = 6.0

        assert tracker.get_remaining_budget() == 0.0

    def test_record_successful_request(self):
        """Test recording a successful request."""
        config = AISummaryConfig()
        tracker = AIUsageTracker(config=config)

        tracker.record_request(
            success=True,
            input_tokens=100,
            output_tokens=50,
            processing_time_ms=1500.0
        )

        assert tracker.stats.total_requests == 1
        assert tracker.stats.successful_requests == 1
        assert tracker.stats.failed_requests == 0
        assert tracker.stats.total_tokens_used == 150
        assert tracker.stats.input_tokens_used == 100
        assert tracker.stats.output_tokens_used == 50
        assert tracker.stats.average_processing_time_ms == 1500.0
        assert tracker.stats.min_processing_time_ms == 1500.0
        assert tracker.stats.max_processing_time_ms == 1500.0
        assert tracker.stats.last_request is not None

        # Check cost calculation
        expected_input_cost = config.calculate_input_cost(100)
        expected_output_cost = config.calculate_output_cost(50)
        expected_total_cost = expected_input_cost + expected_output_cost

        assert tracker.stats.input_cost_usd == expected_input_cost
        assert tracker.stats.output_cost_usd == expected_output_cost
        assert tracker.stats.total_cost_usd == expected_total_cost

    def test_record_failed_request(self):
        """Test recording a failed request."""
        config = AISummaryConfig()
        tracker = AIUsageTracker(config=config)

        tracker.record_request(
            success=False,
            processing_time_ms=500.0,
            error="API error"
        )

        assert tracker.stats.total_requests == 1
        assert tracker.stats.successful_requests == 0
        assert tracker.stats.failed_requests == 1
        assert tracker.stats.total_tokens_used == 0
        assert tracker.stats.input_tokens_used == 0
        assert tracker.stats.output_tokens_used == 0
        assert tracker.stats.total_cost_usd == 0.0
        assert tracker.stats.last_request is not None

    def test_record_multiple_requests_processing_time_stats(self):
        """Test processing time statistics with multiple requests."""
        config = AISummaryConfig()
        tracker = AIUsageTracker(config=config)

        # Record first request
        tracker.record_request(
            success=True,
            input_tokens=100,
            output_tokens=50,
            processing_time_ms=1000.0
        )

        # Record second request
        tracker.record_request(
            success=True,
            input_tokens=200,
            output_tokens=100,
            processing_time_ms=2000.0
        )

        # Record third request
        tracker.record_request(
            success=True,
            input_tokens=150,
            output_tokens=75,
            processing_time_ms=500.0
        )

        assert tracker.stats.total_requests == 3
        assert tracker.stats.successful_requests == 3
        assert tracker.stats.min_processing_time_ms == 500.0
        assert tracker.stats.max_processing_time_ms == 2000.0
        assert tracker.stats.average_processing_time_ms == 1166.6666666666667  # (1000 + 2000 + 500) / 3

    def test_get_usage_report(self):
        """Test usage report generation."""
        config = AISummaryConfig(
            max_cost_per_session_usd=5.0,
            max_cost_per_request_usd=0.10,
            cost_warning_threshold_usd=1.0
        )
        tracker = AIUsageTracker(config=config)

        # Record some requests
        tracker.record_request(
            success=True,
            input_tokens=1000,
            output_tokens=500,
            processing_time_ms=1500.0
        )
        tracker.record_request(
            success=False,
            processing_time_ms=800.0,
            error="Rate limit"
        )

        report = tracker.get_usage_report()

        # Check report structure
        assert "session_summary" in report
        assert "token_usage" in report
        assert "cost_breakdown" in report
        assert "performance" in report
        assert "limits" in report

        # Check session summary
        session = report["session_summary"]
        assert session["total_requests"] == 2
        assert session["success_rate_percent"] == 50.0
        assert "duration_minutes" in session
        assert "total_cost_usd" in session
        assert "remaining_budget_usd" in session

        # Check token usage
        tokens = report["token_usage"]
        assert tokens["total_tokens"] == 1500
        assert tokens["input_tokens"] == 1000
        assert tokens["output_tokens"] == 500
        assert tokens["average_tokens_per_request"] == 1500.0  # Only successful requests

        # Check cost breakdown
        costs = report["cost_breakdown"]
        assert "input_cost_usd" in costs
        assert "output_cost_usd" in costs
        assert "total_cost_usd" in costs
        assert "cost_per_request_usd" in costs

        # Check performance
        performance = report["performance"]
        assert performance["average_processing_time_ms"] == 1150.0  # (1500 + 800) / 2
        assert performance["min_processing_time_ms"] == 800.0
        assert performance["max_processing_time_ms"] == 1500.0

        # Check limits
        limits = report["limits"]
        assert limits["max_cost_per_session_usd"] == 5.0
        assert limits["max_cost_per_request_usd"] == 0.10
        assert limits["cost_warning_threshold_usd"] == 1.0

    def test_get_usage_report_no_requests(self):
        """Test usage report generation with no requests."""
        config = AISummaryConfig()
        tracker = AIUsageTracker(config=config)

        report = tracker.get_usage_report()

        # Should handle empty stats gracefully
        session = report["session_summary"]
        assert session["total_requests"] == 0
        assert session["success_rate_percent"] == 0.0

        tokens = report["token_usage"]
        assert tokens["total_tokens"] == 0
        assert tokens["average_tokens_per_request"] == 0.0

        costs = report["cost_breakdown"]
        assert costs["total_cost_usd"] == 0.0
        assert costs["cost_per_request_usd"] == 0.0


class TestAISummaryConfigValidation:
    """Test AI summary configuration validation."""

    def test_valid_config(self):
        """Test creating a valid configuration."""
        config = AISummaryConfig(
            enabled=True,
            model="gpt-4o-mini",
            max_tokens=1000,
            max_diff_chars=10000,
            temperature=0.5,
            timeout_seconds=60,
            retry_attempts=5,
            cost_tracking=True,
            batch_size=10,
            max_cost_per_session_usd=10.0,
            max_cost_per_request_usd=0.20,
            cost_warning_threshold_usd=2.0,
            usage_logging_enabled=True,
            performance_logging_enabled=True,
            input_cost_per_1k_tokens=0.0002,
            output_cost_per_1k_tokens=0.0008
        )

        assert config.enabled is True
        assert config.model == "gpt-4o-mini"
        assert config.max_tokens == 1000
        assert config.max_cost_per_session_usd == 10.0

    def test_invalid_max_tokens(self):
        """Test validation of max_tokens field."""
        with pytest.raises(ValueError):
            AISummaryConfig(max_tokens=0)

        with pytest.raises(ValueError):
            AISummaryConfig(max_tokens=5000)  # Above maximum

    def test_invalid_temperature(self):
        """Test validation of temperature field."""
        with pytest.raises(ValueError):
            AISummaryConfig(temperature=-0.1)

        with pytest.raises(ValueError):
            AISummaryConfig(temperature=2.1)

    def test_invalid_timeout_seconds(self):
        """Test validation of timeout_seconds field."""
        with pytest.raises(ValueError):
            AISummaryConfig(timeout_seconds=0)

    def test_invalid_retry_attempts(self):
        """Test validation of retry_attempts field."""
        with pytest.raises(ValueError):
            AISummaryConfig(retry_attempts=-1)

    def test_invalid_batch_size(self):
        """Test validation of batch_size field."""
        with pytest.raises(ValueError):
            AISummaryConfig(batch_size=0)

        with pytest.raises(ValueError):
            AISummaryConfig(batch_size=25)  # Above maximum

    def test_negative_costs(self):
        """Test validation of cost fields."""
        with pytest.raises(ValueError):
            AISummaryConfig(max_cost_per_session_usd=-1.0)

        with pytest.raises(ValueError):
            AISummaryConfig(max_cost_per_request_usd=-0.1)

        with pytest.raises(ValueError):
            AISummaryConfig(cost_warning_threshold_usd=-0.5)

        with pytest.raises(ValueError):
            AISummaryConfig(input_cost_per_1k_tokens=-0.001)

        with pytest.raises(ValueError):
            AISummaryConfig(output_cost_per_1k_tokens=-0.001)
