"""Unit tests for configuration management."""

import json
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from forkscout.config import (
    AnalysisConfig,
    CacheConfig,
    ForkscoutConfig,
    GitHubConfig,
    LoggingConfig,
    RateLimitConfig,
    ScoringConfig,
    load_config,
)


class TestScoringConfig:
    """Test cases for ScoringConfig."""

    def test_scoring_config_defaults(self):
        """Test ScoringConfig with default values."""
        config = ScoringConfig()

        assert config.code_quality_weight == 0.3
        assert config.community_engagement_weight == 0.2
        assert config.test_coverage_weight == 0.2
        assert config.documentation_weight == 0.15
        assert config.recency_weight == 0.15

        # Check that weights sum to 1.0
        total = (
            config.code_quality_weight
            + config.community_engagement_weight
            + config.test_coverage_weight
            + config.documentation_weight
            + config.recency_weight
        )
        assert abs(total - 1.0) < 0.01

    def test_scoring_config_custom_weights(self):
        """Test ScoringConfig with custom weights."""
        config = ScoringConfig(
            code_quality_weight=0.4,
            community_engagement_weight=0.3,
            test_coverage_weight=0.2,
            documentation_weight=0.05,
            recency_weight=0.05,
        )

        assert config.code_quality_weight == 0.4
        assert config.community_engagement_weight == 0.3

    def test_scoring_config_weights_validation(self):
        """Test ScoringConfig weight validation."""
        # Weights that don't sum to 1.0
        with pytest.raises(ValueError, match="must sum to 1.0"):
            ScoringConfig(
                code_quality_weight=0.5,
                community_engagement_weight=0.5,
                test_coverage_weight=0.5,
                documentation_weight=0.5,
                recency_weight=0.5,
            )

    def test_scoring_config_normalize_weights(self):
        """Test ScoringConfig weight normalization."""
        config = ScoringConfig.create_unnormalized(
            code_quality_weight=0.4,
            community_engagement_weight=0.4,
            test_coverage_weight=0.4,
            documentation_weight=0.4,
            recency_weight=0.4,
        )

        normalized = config.normalize_weights()

        # Each weight should be 0.2 (1.0 / 5)
        assert abs(normalized.code_quality_weight - 0.2) < 0.01
        assert abs(normalized.community_engagement_weight - 0.2) < 0.01
        assert abs(normalized.test_coverage_weight - 0.2) < 0.01
        assert abs(normalized.documentation_weight - 0.2) < 0.01
        assert abs(normalized.recency_weight - 0.2) < 0.01

    def test_scoring_config_normalize_zero_weights(self):
        """Test ScoringConfig normalization with all zero weights."""
        config = ScoringConfig.create_unnormalized(
            code_quality_weight=0.0,
            community_engagement_weight=0.0,
            test_coverage_weight=0.0,
            documentation_weight=0.0,
            recency_weight=0.0,
        )

        normalized = config.normalize_weights()

        # Should set equal weights
        assert normalized.code_quality_weight == 0.2
        assert normalized.community_engagement_weight == 0.2
        assert normalized.test_coverage_weight == 0.2
        assert normalized.documentation_weight == 0.2
        assert normalized.recency_weight == 0.2


class TestGitHubConfig:
    """Test cases for GitHubConfig."""

    def test_github_config_defaults(self):
        """Test GitHubConfig with default values."""
        config = GitHubConfig()

        assert config.token is None
        assert config.base_url == "https://api.github.com"
        assert config.timeout_seconds == 30
        assert config.max_retries == 3
        assert config.retry_delay_seconds == 1.0

    def test_github_config_token_validation_valid(self):
        """Test GitHubConfig token validation with valid tokens."""
        valid_tokens = [
            "ghp_1234567890abcdef1234567890abcdef12345678",
            "gho_1234567890abcdef1234567890abcdef12345678",
            "ghu_1234567890abcdef1234567890abcdef12345678",
            "ghs_1234567890abcdef1234567890abcdef12345678",
            "ghr_1234567890abcdef1234567890abcdef12345678",
            "1234567890abcdef1234567890abcdef12345678",  # Classic token
        ]

        for token in valid_tokens:
            config = GitHubConfig(token=token)
            assert config.token == token

    def test_github_config_token_validation_invalid(self):
        """Test GitHubConfig token validation with invalid tokens."""
        from pydantic_core import ValidationError

        invalid_tokens = [
            "invalid_token",
            "ghp_short",
            "xyz_1234567890abcdef1234567890abcdef12345678",
        ]

        for token in invalid_tokens:
            with pytest.raises(ValidationError):
                GitHubConfig(token=token)


class TestAnalysisConfig:
    """Test cases for AnalysisConfig."""

    def test_analysis_config_defaults(self):
        """Test AnalysisConfig with default values."""
        config = AnalysisConfig()

        assert config.min_score_threshold == 70.0
        assert config.max_forks_to_analyze == 100
        assert config.auto_pr_enabled is False
        assert "*.md" in config.excluded_file_patterns
        assert config.min_commit_changes == 5
        assert config.max_commit_age_days == 365
        assert config.include_merge_commits is False


class TestCacheConfig:
    """Test cases for CacheConfig."""

    def test_cache_config_defaults(self):
        """Test CacheConfig with default values."""
        config = CacheConfig()

        assert config.enabled is True
        assert config.duration_hours == 24
        assert config.max_size_mb == 100
        assert config.cache_dir == ".forklift/cache"
        assert config.cleanup_on_startup is True


class TestRateLimitConfig:
    """Test cases for RateLimitConfig."""

    def test_rate_limit_config_defaults(self):
        """Test RateLimitConfig with default values."""
        config = RateLimitConfig()

        assert config.requests_per_minute == 60
        assert config.max_concurrent_requests == 10
        assert config.burst_limit == 100
        assert config.backoff_factor == 2.0
        assert config.max_backoff_seconds == 300.0


class TestLoggingConfig:
    """Test cases for LoggingConfig."""

    def test_logging_config_defaults(self):
        """Test LoggingConfig with default values."""
        config = LoggingConfig()

        assert config.level == "CRITICAL"
        assert "%(asctime)s" in config.format
        assert config.file_enabled is True
        assert config.file_path == "forkscout.log"
        assert config.max_file_size_mb == 10
        assert config.backup_count == 5
        assert config.console_enabled is True

    def test_logging_config_level_validation(self):
        """Test LoggingConfig level validation."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            config = LoggingConfig(level=level)
            assert config.level == level

        # Test case insensitive
        config = LoggingConfig(level="info")
        assert config.level == "INFO"

        # Invalid level
        with pytest.raises(ValueError, match="Invalid log level"):
            LoggingConfig(level="INVALID")


class TestForkscoutConfig:
    """Test cases for ForkscoutConfig."""

    def test_forklift_config_defaults(self):
        """Test ForkscoutConfig with default values."""
        config = ForkscoutConfig()

        assert isinstance(config.github, GitHubConfig)
        assert isinstance(config.analysis, AnalysisConfig)
        assert isinstance(config.cache, CacheConfig)
        assert isinstance(config.rate_limit, RateLimitConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.scoring, ScoringConfig)

        assert config.debug is False
        assert config.dry_run is False
        assert config.output_format == "markdown"

    def test_forklift_config_output_format_validation(self):
        """Test ForkscoutConfig output format validation."""
        valid_formats = ["markdown", "json", "yaml"]

        for fmt in valid_formats:
            config = ForkscoutConfig(output_format=fmt)
            assert config.output_format == fmt

        # Test case insensitive
        config = ForkscoutConfig(output_format="MARKDOWN")
        assert config.output_format == "markdown"

        # Invalid format
        with pytest.raises(ValueError, match="Invalid output format"):
            ForkscoutConfig(output_format="invalid")

    def test_forklift_config_from_dict(self):
        """Test ForkscoutConfig creation from dictionary."""
        data = {
            "github": {"token": "ghp_1234567890abcdef1234567890abcdef12345678"},
            "analysis": {"min_score_threshold": 80.0},
            "debug": True,
        }

        config = ForkscoutConfig.from_dict(data)

        assert config.github.token == "ghp_1234567890abcdef1234567890abcdef12345678"
        assert config.analysis.min_score_threshold == 80.0
        assert config.debug is True

    def test_forklift_config_to_dict(self):
        """Test ForkscoutConfig conversion to dictionary."""
        config = ForkscoutConfig(debug=True)
        data = config.to_dict()

        assert isinstance(data, dict)
        assert data["debug"] is True
        assert "github" in data
        assert "analysis" in data

    def test_forklift_config_to_yaml(self):
        """Test ForkscoutConfig conversion to YAML."""
        config = ForkscoutConfig(debug=True)
        yaml_str = config.to_yaml()

        assert isinstance(yaml_str, str)
        assert "debug: true" in yaml_str

        # Should be valid YAML
        parsed = yaml.safe_load(yaml_str)
        assert parsed["debug"] is True

    def test_forklift_config_to_json(self):
        """Test ForkscoutConfig conversion to JSON."""
        config = ForkscoutConfig(debug=True)
        json_str = config.to_json()

        assert isinstance(json_str, str)

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["debug"] is True

    def test_forklift_config_from_yaml_file(self):
        """Test ForkscoutConfig loading from YAML file."""
        yaml_content = """
        github:
          token: ghp_1234567890abcdef1234567890abcdef12345678
        analysis:
          min_score_threshold: 85.0
        debug: true
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                config = ForkscoutConfig.from_file(f.name)

                assert config.github.token == "ghp_1234567890abcdef1234567890abcdef12345678"
                assert config.analysis.min_score_threshold == 85.0
                assert config.debug is True
            finally:
                os.unlink(f.name)

    def test_forklift_config_from_json_file(self):
        """Test ForkscoutConfig loading from JSON file."""
        json_content = {
            "github": {"token": "ghp_1234567890abcdef1234567890abcdef12345678"},
            "analysis": {"min_score_threshold": 85.0},
            "debug": True,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_content, f)
            f.flush()

            try:
                config = ForkscoutConfig.from_file(f.name)

                assert config.github.token == "ghp_1234567890abcdef1234567890abcdef12345678"
                assert config.analysis.min_score_threshold == 85.0
                assert config.debug is True
            finally:
                os.unlink(f.name)

    def test_forklift_config_from_file_not_found(self):
        """Test ForkscoutConfig loading from non-existent file."""
        with pytest.raises(FileNotFoundError):
            ForkscoutConfig.from_file("nonexistent.yaml")

    def test_forklift_config_from_file_invalid_format(self):
        """Test ForkscoutConfig loading from unsupported file format."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("invalid content")
            f.flush()

            try:
                with pytest.raises(ValueError, match="Unsupported config file format"):
                    ForkscoutConfig.from_file(f.name)
            finally:
                os.unlink(f.name)

    def test_forklift_config_save_to_yaml_file(self):
        """Test ForkscoutConfig saving to YAML file."""
        config = ForkscoutConfig(debug=True)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            try:
                config.save_to_file(f.name)

                # Load and verify
                loaded_config = ForkscoutConfig.from_file(f.name)
                assert loaded_config.debug is True
            finally:
                os.unlink(f.name)

    def test_forklift_config_save_to_json_file(self):
        """Test ForkscoutConfig saving to JSON file."""
        config = ForkscoutConfig(debug=True)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            try:
                config.save_to_file(f.name)

                # Load and verify
                loaded_config = ForkscoutConfig.from_file(f.name)
                assert loaded_config.debug is True
            finally:
                os.unlink(f.name)

    def test_forklift_config_merge_with_env(self, monkeypatch):
        """Test ForkscoutConfig merging with environment variables."""
        # Set environment variables
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_1234567890abcdef1234567890abcdef12345678")
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("MIN_SCORE_THRESHOLD", "85.5")

        config = ForkscoutConfig()
        merged_config = config.merge_with_env()

        assert merged_config.github.token == "ghp_1234567890abcdef1234567890abcdef12345678"
        assert merged_config.debug is True
        assert merged_config.analysis.min_score_threshold == 85.5

    def test_forklift_config_validate_github_token(self):
        """Test ForkscoutConfig GitHub token validation."""
        # No token
        config = ForkscoutConfig()
        config.github.token = None  # Explicitly set to None to override .env
        assert config.validate_github_token() is False

        # Valid token
        config = ForkscoutConfig()
        config.github.token = "ghp_1234567890abcdef1234567890abcdef12345678"
        assert config.validate_github_token() is True

        # Invalid token
        config = ForkscoutConfig()
        config.github.token = "invalid_token"
        assert config.validate_github_token() is False

    def test_forklift_config_get_cache_path(self):
        """Test ForkscoutConfig cache path resolution."""
        config = ForkscoutConfig()
        cache_path = config.get_cache_path()

        assert isinstance(cache_path, Path)
        assert cache_path.name == "cache"

    def test_forklift_config_get_log_path(self):
        """Test ForkscoutConfig log path resolution."""
        config = ForkscoutConfig()
        log_path = config.get_log_path()

        assert isinstance(log_path, Path)
        assert log_path.name == "forklift.log"


class TestLoadConfig:
    """Test cases for load_config function."""

    def test_load_config_no_file(self):
        """Test load_config with no configuration file."""
        # Should return default config
        config = load_config()
        assert isinstance(config, ForkscoutConfig)

    def test_load_config_with_file(self, monkeypatch):
        """Test load_config with specific file."""
        # Clear any existing GITHUB_TOKEN env var
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        yaml_content = """
        debug: true
        github:
          token: ghp_1234567890abcdef1234567890abcdef12345678
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                config = load_config(f.name)
                assert config.debug is True
                assert config.github.token == "ghp_1234567890abcdef1234567890abcdef12345678"
            finally:
                os.unlink(f.name)

    def test_load_config_with_env_override(self, monkeypatch):
        """Test load_config with environment variable override."""
        yaml_content = """
        debug: false
        github:
          token: ghp_1234567890abcdef1234567890abcdef12345678
        """

        # Set environment variable that should override file
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_9876543210fedcba9876543210fedcba98765432")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                config = load_config(f.name)
                # Environment should override file
                assert config.debug is True
                assert config.github.token == "ghp_9876543210fedcba9876543210fedcba98765432"
            finally:
                os.unlink(f.name)
