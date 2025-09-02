"""Unit tests for CommitCountConfig."""

import pytest

from forklift.models.commit_count_config import CommitCountConfig


class TestCommitCountConfig:
    """Test cases for CommitCountConfig."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = CommitCountConfig()
        
        assert config.max_count_limit == 100
        assert config.display_limit == 5
        assert config.use_unlimited_counting is False
        assert config.timeout_seconds == 30
        assert config.is_unlimited is False
        assert config.effective_max_count == 100

    def test_custom_configuration(self):
        """Test custom configuration values."""
        config = CommitCountConfig(
            max_count_limit=50,
            display_limit=3,
            timeout_seconds=60
        )
        
        assert config.max_count_limit == 50
        assert config.display_limit == 3
        assert config.timeout_seconds == 60
        assert config.is_unlimited is False
        assert config.effective_max_count == 50

    def test_unlimited_counting_via_flag(self):
        """Test unlimited counting via use_unlimited_counting flag."""
        config = CommitCountConfig(use_unlimited_counting=True)
        
        assert config.use_unlimited_counting is True
        assert config.max_count_limit == 0  # Should be set to 0 in __post_init__
        assert config.is_unlimited is True
        assert config.effective_max_count is None

    def test_unlimited_counting_via_zero_limit(self):
        """Test unlimited counting via max_count_limit=0."""
        config = CommitCountConfig(max_count_limit=0)
        
        assert config.max_count_limit == 0
        assert config.is_unlimited is True
        assert config.effective_max_count is None

    def test_validation_negative_max_count(self):
        """Test validation fails for negative max_count_limit."""
        with pytest.raises(ValueError, match="max_count_limit must be non-negative"):
            CommitCountConfig(max_count_limit=-1)

    def test_validation_negative_display_limit(self):
        """Test validation fails for negative display_limit."""
        with pytest.raises(ValueError, match="display_limit must be non-negative"):
            CommitCountConfig(display_limit=-1)

    def test_validation_zero_timeout(self):
        """Test validation fails for zero or negative timeout."""
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            CommitCountConfig(timeout_seconds=0)
        
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            CommitCountConfig(timeout_seconds=-5)

    def test_get_display_indicator_limited(self):
        """Test display indicator generation with limits."""
        config = CommitCountConfig(max_count_limit=100)
        
        # Normal counts
        assert config.get_display_indicator(0) == ""
        assert config.get_display_indicator(5) == "+5"
        assert config.get_display_indicator(50) == "+50"
        
        # At limit
        assert config.get_display_indicator(100) == "100+"
        
        # Over limit
        assert config.get_display_indicator(150) == "100+"

    def test_get_display_indicator_unlimited(self):
        """Test display indicator generation without limits."""
        config = CommitCountConfig(use_unlimited_counting=True)
        
        # Normal counts
        assert config.get_display_indicator(0) == ""
        assert config.get_display_indicator(5) == "+5"
        assert config.get_display_indicator(150) == "+150"
        assert config.get_display_indicator(1000) == "+1000"

    def test_from_cli_options_defaults(self):
        """Test creating config from CLI options with defaults."""
        config = CommitCountConfig.from_cli_options()
        
        assert config.max_count_limit == 100
        assert config.display_limit == 5
        assert config.use_unlimited_counting is False

    def test_from_cli_options_custom_values(self):
        """Test creating config from CLI options with custom values."""
        config = CommitCountConfig.from_cli_options(
            max_commits_count=50,
            commit_display_limit=3
        )
        
        assert config.max_count_limit == 50
        assert config.display_limit == 3
        assert config.use_unlimited_counting is False

    def test_from_cli_options_unlimited(self):
        """Test creating config from CLI options with unlimited flag."""
        config = CommitCountConfig.from_cli_options(unlimited=True)
        
        assert config.use_unlimited_counting is True
        assert config.max_count_limit == 0
        assert config.is_unlimited is True

    def test_from_cli_options_zero_max_count(self):
        """Test creating config from CLI options with zero max count."""
        config = CommitCountConfig.from_cli_options(max_commits_count=0)
        
        assert config.max_count_limit == 0
        assert config.is_unlimited is True

    def test_from_cli_options_validation(self):
        """Test validation in from_cli_options method."""
        # Should raise validation error for negative values
        with pytest.raises(ValueError):
            CommitCountConfig.from_cli_options(max_commits_count=-1)
        
        with pytest.raises(ValueError):
            CommitCountConfig.from_cli_options(commit_display_limit=-1)

    def test_post_init_unlimited_override(self):
        """Test that unlimited flag overrides max_count_limit."""
        config = CommitCountConfig(
            max_count_limit=50,
            use_unlimited_counting=True
        )
        
        # Should be overridden to 0 by __post_init__
        assert config.max_count_limit == 0
        assert config.is_unlimited is True

    def test_edge_case_display_indicators(self):
        """Test edge cases for display indicators."""
        config = CommitCountConfig(max_count_limit=1)
        
        assert config.get_display_indicator(0) == ""
        assert config.get_display_indicator(1) == "1+"
        assert config.get_display_indicator(2) == "1+"

    def test_configuration_immutability_after_creation(self):
        """Test that configuration behaves correctly after creation."""
        config = CommitCountConfig(max_count_limit=100)
        
        # Test that properties work correctly
        assert config.is_unlimited is False
        assert config.effective_max_count == 100
        
        # Test display indicators
        assert config.get_display_indicator(50) == "+50"
        assert config.get_display_indicator(100) == "100+"
        assert config.get_display_indicator(150) == "100+"