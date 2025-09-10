"""Tests for fork filtering configuration and statistics."""

from unittest.mock import AsyncMock

import pytest

from forkscout.analysis.fork_commit_status_checker import ForkCommitStatusChecker
from forkscout.models.fork_filtering import ForkFilteringConfig, ForkFilteringStats


class TestForkFilteringConfig:
    """Test fork filtering configuration model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ForkFilteringConfig()

        assert config.enabled is True
        assert config.log_filtering_decisions is True
        assert config.log_statistics is True
        assert config.fallback_to_api is True
        assert config.prefer_inclusion_on_uncertainty is True
        assert config.cache_status_results is True
        assert config.status_cache_ttl_hours == 24
        assert config.max_api_fallback_calls == 50
        assert config.skip_archived_forks is True
        assert config.skip_disabled_forks is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ForkFilteringConfig(
            enabled=False,
            log_filtering_decisions=False,
            log_statistics=False,
            fallback_to_api=False,
            prefer_inclusion_on_uncertainty=False,
            cache_status_results=False,
            status_cache_ttl_hours=12,
            max_api_fallback_calls=25,
            skip_archived_forks=False,
            skip_disabled_forks=False,
        )

        assert config.enabled is False
        assert config.log_filtering_decisions is False
        assert config.log_statistics is False
        assert config.fallback_to_api is False
        assert config.prefer_inclusion_on_uncertainty is False
        assert config.cache_status_results is False
        assert config.status_cache_ttl_hours == 12
        assert config.max_api_fallback_calls == 25
        assert config.skip_archived_forks is False
        assert config.skip_disabled_forks is False

    def test_config_validation(self):
        """Test configuration validation."""
        # Test valid values
        config = ForkFilteringConfig(status_cache_ttl_hours=1)
        assert config.status_cache_ttl_hours == 1

        config = ForkFilteringConfig(max_api_fallback_calls=0)
        assert config.max_api_fallback_calls == 0

        # Test invalid values
        with pytest.raises(ValueError):
            ForkFilteringConfig(status_cache_ttl_hours=0)

        with pytest.raises(ValueError):
            ForkFilteringConfig(max_api_fallback_calls=-1)


class TestForkFilteringStats:
    """Test fork filtering statistics model."""

    def test_default_stats(self):
        """Test default statistics values."""
        stats = ForkFilteringStats()

        assert stats.total_forks_evaluated == 0
        assert stats.forks_filtered_out == 0
        assert stats.forks_included == 0
        assert stats.qualification_data_hits == 0
        assert stats.api_fallback_calls == 0
        assert stats.status_unknown == 0
        assert stats.errors == 0
        assert stats.filtered_no_commits_ahead == 0
        assert stats.filtered_archived == 0
        assert stats.filtered_disabled == 0

    def test_filtering_rate_calculation(self):
        """Test filtering rate calculation."""
        stats = ForkFilteringStats()

        # No evaluations - should be 0%
        assert stats.filtering_rate == 0.0

        # Add some evaluations
        stats.total_forks_evaluated = 10
        stats.forks_filtered_out = 3
        stats.forks_included = 7

        assert stats.filtering_rate == 30.0

    def test_api_usage_efficiency_calculation(self):
        """Test API usage efficiency calculation."""
        stats = ForkFilteringStats()

        # No lookups - should be 100%
        assert stats.api_usage_efficiency == 100.0

        # Add some lookups
        stats.qualification_data_hits = 8
        stats.api_fallback_calls = 2

        assert stats.api_usage_efficiency == 80.0

    def test_add_fork_evaluated(self):
        """Test adding fork evaluation results."""
        stats = ForkFilteringStats()

        # Add filtered fork
        stats.add_fork_evaluated(filtered=True, reason="no_commits_ahead")
        assert stats.total_forks_evaluated == 1
        assert stats.forks_filtered_out == 1
        assert stats.forks_included == 0
        assert stats.filtered_no_commits_ahead == 1

        # Add included fork
        stats.add_fork_evaluated(filtered=False)
        assert stats.total_forks_evaluated == 2
        assert stats.forks_filtered_out == 1
        assert stats.forks_included == 1

        # Add archived fork
        stats.add_fork_evaluated(filtered=True, reason="archived")
        assert stats.total_forks_evaluated == 3
        assert stats.forks_filtered_out == 2
        assert stats.filtered_archived == 1

    def test_add_operations(self):
        """Test adding various operation results."""
        stats = ForkFilteringStats()

        stats.add_qualification_hit()
        assert stats.qualification_data_hits == 1

        stats.add_api_fallback()
        assert stats.api_fallback_calls == 1

        stats.add_status_unknown()
        assert stats.status_unknown == 1

        stats.add_error()
        assert stats.errors == 1

    def test_reset(self):
        """Test resetting statistics."""
        stats = ForkFilteringStats()

        # Add some data
        stats.add_fork_evaluated(filtered=True, reason="no_commits_ahead")
        stats.add_qualification_hit()
        stats.add_api_fallback()
        stats.add_error()

        # Verify data is there
        assert stats.total_forks_evaluated > 0
        assert stats.qualification_data_hits > 0
        assert stats.api_fallback_calls > 0
        assert stats.errors > 0

        # Reset and verify all zeros
        stats.reset()
        assert stats.total_forks_evaluated == 0
        assert stats.forks_filtered_out == 0
        assert stats.forks_included == 0
        assert stats.qualification_data_hits == 0
        assert stats.api_fallback_calls == 0
        assert stats.status_unknown == 0
        assert stats.errors == 0
        assert stats.filtered_no_commits_ahead == 0
        assert stats.filtered_archived == 0
        assert stats.filtered_disabled == 0

    def test_to_summary_dict(self):
        """Test converting statistics to summary dictionary."""
        stats = ForkFilteringStats()

        # Add some data
        stats.add_fork_evaluated(filtered=True, reason="no_commits_ahead")
        stats.add_fork_evaluated(filtered=True, reason="archived")
        stats.add_fork_evaluated(filtered=False)
        stats.add_qualification_hit()
        stats.add_api_fallback()
        stats.add_error()

        summary = stats.to_summary_dict()

        assert summary["total_evaluated"] == 3
        assert summary["filtered_out"] == 2
        assert summary["included"] == 1
        assert summary["filtering_rate_percent"] == 66.7
        assert summary["api_efficiency_percent"] == 50.0
        assert summary["qualification_hits"] == 1
        assert summary["api_fallbacks"] == 1
        assert summary["status_unknown"] == 0
        assert summary["errors"] == 1
        assert summary["filtered_reasons"]["no_commits_ahead"] == 1
        assert summary["filtered_reasons"]["archived"] == 1
        assert summary["filtered_reasons"]["disabled"] == 0


class TestForkCommitStatusCheckerConfig:
    """Test fork commit status checker with configuration."""

    @pytest.fixture
    def mock_github_client(self):
        """Create mock GitHub client."""
        return AsyncMock()

    @pytest.fixture
    def default_config(self):
        """Create default configuration."""
        return ForkFilteringConfig()

    @pytest.fixture
    def custom_config(self):
        """Create custom configuration."""
        return ForkFilteringConfig(
            enabled=True,
            log_filtering_decisions=False,
            fallback_to_api=False,
            prefer_inclusion_on_uncertainty=False,
            max_api_fallback_calls=5,
        )

    def test_init_with_default_config(self, mock_github_client):
        """Test initialization with default configuration."""
        checker = ForkCommitStatusChecker(mock_github_client)

        assert checker.config.enabled is True
        assert checker.config.log_filtering_decisions is True
        assert isinstance(checker.stats, ForkFilteringStats)
        assert checker._api_fallback_count == 0

    def test_init_with_custom_config(self, mock_github_client, custom_config):
        """Test initialization with custom configuration."""
        checker = ForkCommitStatusChecker(mock_github_client, custom_config)

        assert checker.config.enabled is True
        assert checker.config.log_filtering_decisions is False
        assert checker.config.fallback_to_api is False
        assert checker.config.max_api_fallback_calls == 5

    def test_should_filter_fork_disabled(self, mock_github_client):
        """Test fork filtering when filtering is disabled."""
        config = ForkFilteringConfig(enabled=False)
        checker = ForkCommitStatusChecker(mock_github_client, config)

        fork_data = {"full_name": "owner/repo", "archived": True, "disabled": True}
        should_filter, reason = checker.should_filter_fork(fork_data)

        assert should_filter is False
        assert reason == "filtering_disabled"

    def test_should_filter_fork_archived(self, mock_github_client, default_config):
        """Test filtering archived forks."""
        checker = ForkCommitStatusChecker(mock_github_client, default_config)

        fork_data = {"full_name": "owner/repo", "archived": True}
        should_filter, reason = checker.should_filter_fork(fork_data)

        assert should_filter is True
        assert reason == "archived"

    def test_should_filter_fork_disabled_repo(self, mock_github_client, default_config):
        """Test filtering disabled forks."""
        checker = ForkCommitStatusChecker(mock_github_client, default_config)

        fork_data = {"full_name": "owner/repo", "disabled": True}
        should_filter, reason = checker.should_filter_fork(fork_data)

        assert should_filter is True
        assert reason == "disabled"

    def test_should_filter_fork_normal(self, mock_github_client, default_config):
        """Test normal fork that should not be filtered."""
        checker = ForkCommitStatusChecker(mock_github_client, default_config)

        fork_data = {"full_name": "owner/repo", "archived": False, "disabled": False}
        should_filter, reason = checker.should_filter_fork(fork_data)

        assert should_filter is False
        assert reason == "not_filtered"

    def test_should_filter_fork_skip_archived_disabled(self, mock_github_client):
        """Test when skipping archived/disabled forks is disabled."""
        config = ForkFilteringConfig(
            skip_archived_forks=False, skip_disabled_forks=False
        )
        checker = ForkCommitStatusChecker(mock_github_client, config)

        fork_data = {"full_name": "owner/repo", "archived": True, "disabled": True}
        should_filter, reason = checker.should_filter_fork(fork_data)

        assert should_filter is False
        assert reason == "not_filtered"

    @pytest.mark.asyncio
    async def test_evaluate_fork_for_filtering_archived(
        self, mock_github_client, default_config
    ):
        """Test evaluating archived fork for filtering."""
        checker = ForkCommitStatusChecker(mock_github_client, default_config)

        fork_data = {"full_name": "owner/repo", "archived": True}
        should_filter, reason = await checker.evaluate_fork_for_filtering(
            "https://github.com/owner/repo", fork_data
        )

        assert should_filter is True
        assert reason == "archived"
        assert checker.stats.total_forks_evaluated == 1
        assert checker.stats.forks_filtered_out == 1
        assert checker.stats.filtered_archived == 1

    @pytest.mark.asyncio
    async def test_evaluate_fork_for_filtering_no_commits(
        self, mock_github_client, default_config
    ):
        """Test evaluating fork with no commits ahead."""
        checker = ForkCommitStatusChecker(mock_github_client, default_config)

        # Mock has_commits_ahead to return False
        checker.has_commits_ahead = AsyncMock(return_value=False)

        fork_data = {"full_name": "owner/repo", "archived": False, "disabled": False}
        should_filter, reason = await checker.evaluate_fork_for_filtering(
            "https://github.com/owner/repo", fork_data
        )

        assert should_filter is True
        assert reason == "no_commits_ahead"
        assert checker.stats.total_forks_evaluated == 1
        assert checker.stats.forks_filtered_out == 1
        assert checker.stats.filtered_no_commits_ahead == 1

    @pytest.mark.asyncio
    async def test_evaluate_fork_for_filtering_has_commits(
        self, mock_github_client, default_config
    ):
        """Test evaluating fork with commits ahead."""
        checker = ForkCommitStatusChecker(mock_github_client, default_config)

        # Mock has_commits_ahead to return True
        checker.has_commits_ahead = AsyncMock(return_value=True)

        fork_data = {"full_name": "owner/repo", "archived": False, "disabled": False}
        should_filter, reason = await checker.evaluate_fork_for_filtering(
            "https://github.com/owner/repo", fork_data
        )

        assert should_filter is False
        assert reason == "has_commits_ahead"
        assert checker.stats.total_forks_evaluated == 1
        assert checker.stats.forks_included == 1

    @pytest.mark.asyncio
    async def test_evaluate_fork_for_filtering_unknown_status_include(
        self, mock_github_client
    ):
        """Test evaluating fork with unknown status when preferring inclusion."""
        config = ForkFilteringConfig(prefer_inclusion_on_uncertainty=True)
        checker = ForkCommitStatusChecker(mock_github_client, config)

        # Mock has_commits_ahead to return None (unknown)
        checker.has_commits_ahead = AsyncMock(return_value=None)

        fork_data = {"full_name": "owner/repo", "archived": False, "disabled": False}
        should_filter, reason = await checker.evaluate_fork_for_filtering(
            "https://github.com/owner/repo", fork_data
        )

        assert should_filter is False
        assert reason == "status_unknown_included"
        assert checker.stats.total_forks_evaluated == 1
        assert checker.stats.forks_included == 1

    @pytest.mark.asyncio
    async def test_evaluate_fork_for_filtering_unknown_status_exclude(
        self, mock_github_client
    ):
        """Test evaluating fork with unknown status when preferring exclusion."""
        config = ForkFilteringConfig(prefer_inclusion_on_uncertainty=False)
        checker = ForkCommitStatusChecker(mock_github_client, config)

        # Mock has_commits_ahead to return None (unknown)
        checker.has_commits_ahead = AsyncMock(return_value=None)

        fork_data = {"full_name": "owner/repo", "archived": False, "disabled": False}
        should_filter, reason = await checker.evaluate_fork_for_filtering(
            "https://github.com/owner/repo", fork_data
        )

        assert should_filter is True
        assert reason == "status_unknown_excluded"
        assert checker.stats.total_forks_evaluated == 1
        assert checker.stats.forks_filtered_out == 1

    @pytest.mark.asyncio
    async def test_evaluate_fork_for_filtering_error_handling(self, mock_github_client):
        """Test error handling during fork evaluation."""
        config = ForkFilteringConfig(prefer_inclusion_on_uncertainty=True)
        checker = ForkCommitStatusChecker(mock_github_client, config)

        # Mock has_commits_ahead to raise an exception
        checker.has_commits_ahead = AsyncMock(side_effect=Exception("Test error"))

        fork_data = {"full_name": "owner/repo", "archived": False, "disabled": False}
        should_filter, reason = await checker.evaluate_fork_for_filtering(
            "https://github.com/owner/repo", fork_data
        )

        assert should_filter is False
        assert reason == "error_included"
        assert checker.stats.total_forks_evaluated == 1
        assert checker.stats.forks_included == 1
        assert checker.stats.errors == 1

    def test_get_and_update_config(self, mock_github_client, default_config):
        """Test getting and updating configuration."""
        checker = ForkCommitStatusChecker(mock_github_client, default_config)

        # Get current config
        current_config = checker.get_config()
        assert current_config.enabled is True
        assert current_config.log_filtering_decisions is True

        # Update config
        new_config = ForkFilteringConfig(enabled=False, log_filtering_decisions=False)
        checker.update_config(new_config)

        updated_config = checker.get_config()
        assert updated_config.enabled is False
        assert updated_config.log_filtering_decisions is False

    def test_reset_statistics(self, mock_github_client, default_config):
        """Test resetting statistics."""
        checker = ForkCommitStatusChecker(mock_github_client, default_config)

        # Add some statistics
        checker.stats.add_fork_evaluated(filtered=True, reason="archived")
        checker.stats.add_qualification_hit()
        checker._api_fallback_count = 5

        # Verify statistics exist
        assert checker.stats.total_forks_evaluated > 0
        assert checker.stats.qualification_data_hits > 0
        assert checker._api_fallback_count > 0

        # Reset and verify
        checker.reset_statistics()
        assert checker.stats.total_forks_evaluated == 0
        assert checker.stats.qualification_data_hits == 0
        assert checker._api_fallback_count == 0

    def test_log_statistics_disabled(self, mock_github_client, caplog):
        """Test logging statistics when disabled."""
        config = ForkFilteringConfig(log_statistics=False)
        checker = ForkCommitStatusChecker(mock_github_client, config)

        # Add some statistics
        checker.stats.add_fork_evaluated(filtered=True, reason="archived")

        # Log statistics - should not log anything
        checker.log_statistics()

        # Verify no log messages
        assert len(caplog.records) == 0

    def test_log_statistics_no_operations(
        self, mock_github_client, default_config, caplog
    ):
        """Test logging statistics when no operations performed."""
        import logging

        caplog.set_level(logging.INFO)

        checker = ForkCommitStatusChecker(mock_github_client, default_config)

        checker.log_statistics()

        # Should log that no operations were performed
        assert "No fork filtering operations performed yet" in caplog.text

    def test_log_statistics_with_data(self, mock_github_client, default_config, caplog):
        """Test logging statistics with data."""
        import logging

        caplog.set_level(logging.INFO)

        checker = ForkCommitStatusChecker(mock_github_client, default_config)

        # Add various statistics
        checker.stats.add_fork_evaluated(filtered=True, reason="no_commits_ahead")
        checker.stats.add_fork_evaluated(filtered=True, reason="archived")
        checker.stats.add_fork_evaluated(filtered=False)
        checker.stats.add_qualification_hit()
        checker.stats.add_api_fallback()
        checker.stats.add_error()

        checker.log_statistics()

        # Verify log contains expected information
        assert "Fork filtering statistics:" in caplog.text
        assert "evaluated=3" in caplog.text
        assert "filtered_out=2" in caplog.text
        assert "included=1" in caplog.text
        assert "filtering_rate=66.7%" in caplog.text
        assert "Fork filtering reasons:" in caplog.text
        assert "no_commits_ahead=1" in caplog.text
        assert "archived=1" in caplog.text
        assert "Fork filtering errors encountered: 1" in caplog.text
