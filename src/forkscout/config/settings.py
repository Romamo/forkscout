"""Configuration settings for Forkscout application."""

import json
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from forkscout.models.ai_summary import AISummaryConfig
from forkscout.models.commit_count_config import CommitCountConfig
from forkscout.models.fork_filtering import ForkFilteringConfig
from forkscout.models.interactive import InteractiveConfig


class ScoringConfig(BaseModel):
    """Configuration for feature scoring algorithm."""

    code_quality_weight: float = Field(
        default=0.3, ge=0, le=1, description="Weight for code quality metrics"
    )
    community_engagement_weight: float = Field(
        default=0.2, ge=0, le=1, description="Weight for community engagement metrics"
    )
    test_coverage_weight: float = Field(
        default=0.2, ge=0, le=1, description="Weight for test coverage metrics"
    )
    documentation_weight: float = Field(
        default=0.15, ge=0, le=1, description="Weight for documentation quality"
    )
    recency_weight: float = Field(
        default=0.15, ge=0, le=1, description="Weight for recency of changes"
    )

    @model_validator(mode="after")
    def validate_weights_sum(self) -> "ScoringConfig":
        """Validate that all weights sum to approximately 1.0."""
        total_weight = (
            self.code_quality_weight
            + self.community_engagement_weight
            + self.test_coverage_weight
            + self.documentation_weight
            + self.recency_weight
        )

        # Allow small floating point differences
        if not (0.99 <= total_weight <= 1.01):
            raise ValueError(f"Scoring weights must sum to 1.0, got {total_weight:.3f}")
        return self

    @classmethod
    def create_unnormalized(
        cls,
        code_quality_weight: float = 0.3,
        community_engagement_weight: float = 0.2,
        test_coverage_weight: float = 0.2,
        documentation_weight: float = 0.15,
        recency_weight: float = 0.15,
    ) -> "ScoringConfig":
        """Create ScoringConfig without validation for testing purposes."""

        # Create a simple object with the weights for testing normalization
        class UnnormalizedConfig:
            def __init__(self):
                self.code_quality_weight = code_quality_weight
                self.community_engagement_weight = community_engagement_weight
                self.test_coverage_weight = test_coverage_weight
                self.documentation_weight = documentation_weight
                self.recency_weight = recency_weight

            def normalize_weights(self) -> "ScoringConfig":
                """Normalize weights to sum to exactly 1.0."""
                total = (
                    self.code_quality_weight
                    + self.community_engagement_weight
                    + self.test_coverage_weight
                    + self.documentation_weight
                    + self.recency_weight
                )

                if total == 0:
                    # If all weights are 0, set equal weights
                    equal_weight = 0.2
                    return ScoringConfig(
                        code_quality_weight=equal_weight,
                        community_engagement_weight=equal_weight,
                        test_coverage_weight=equal_weight,
                        documentation_weight=equal_weight,
                        recency_weight=equal_weight,
                    )

                return ScoringConfig(
                    code_quality_weight=self.code_quality_weight / total,
                    community_engagement_weight=self.community_engagement_weight
                    / total,
                    test_coverage_weight=self.test_coverage_weight / total,
                    documentation_weight=self.documentation_weight / total,
                    recency_weight=self.recency_weight / total,
                )

        return UnnormalizedConfig()

    def normalize_weights(self) -> "ScoringConfig":
        """Normalize weights to sum to exactly 1.0."""
        total = (
            self.code_quality_weight
            + self.community_engagement_weight
            + self.test_coverage_weight
            + self.documentation_weight
            + self.recency_weight
        )

        if total == 0:
            # If all weights are 0, set equal weights
            equal_weight = 0.2
            return ScoringConfig(
                code_quality_weight=equal_weight,
                community_engagement_weight=equal_weight,
                test_coverage_weight=equal_weight,
                documentation_weight=equal_weight,
                recency_weight=equal_weight,
            )

        return ScoringConfig(
            code_quality_weight=self.code_quality_weight / total,
            community_engagement_weight=self.community_engagement_weight / total,
            test_coverage_weight=self.test_coverage_weight / total,
            documentation_weight=self.documentation_weight / total,
            recency_weight=self.recency_weight / total,
        )


class GitHubConfig(BaseModel):
    """GitHub API configuration."""

    token: str | None = Field(None, description="GitHub API token")
    base_url: str = Field(
        default="https://api.github.com", description="GitHub API base URL"
    )
    timeout_seconds: int = Field(default=30, ge=1, description="Request timeout")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")
    retry_delay_seconds: float = Field(
        default=1.0, ge=0, description="Base delay between retries"
    )

    @field_validator("token")
    @classmethod
    def validate_token_format(cls, v: str | None) -> str | None:
        """Validate GitHub token format."""
        if v is None:
            return v

        # GitHub tokens should start with specific prefixes and have minimum length
        valid_prefixes = ["ghp_", "gho_", "ghu_", "ghs_", "ghr_"]
        has_valid_prefix = any(v.startswith(prefix) for prefix in valid_prefixes)

        if has_valid_prefix:
            # New format tokens should be at least 36 characters
            if len(v) < 36:
                raise ValueError("GitHub token is too short")
            return v
        else:
            # Allow classic tokens (40 character hex) for backward compatibility
            if len(v) == 40 and all(c in "0123456789abcdef" for c in v.lower()):
                return v
            raise ValueError(
                "Invalid GitHub token format. Token should start with ghp_, gho_, ghu_, ghs_, or ghr_ or be a 40-character hex string"
            )

        return v

    def validate_token_format_static(self, token: str) -> None:
        """Static method to validate token format for testing."""
        self.validate_token_format(token)


class AnalysisConfig(BaseModel):
    """Analysis configuration."""

    min_score_threshold: float = Field(
        default=70.0, ge=0, le=100, description="Minimum score for feature inclusion"
    )
    max_forks_to_analyze: int = Field(
        default=100, ge=1, description="Maximum number of forks to analyze"
    )
    auto_pr_enabled: bool = Field(
        default=False, description="Enable automatic PR creation"
    )
    excluded_file_patterns: list[str] = Field(
        default_factory=lambda: ["*.md", "*.txt", ".github/*", "docs/*"],
        description="File patterns to exclude from analysis",
    )
    min_commit_changes: int = Field(
        default=5, ge=1, description="Minimum changes for significant commits"
    )
    max_commit_age_days: int = Field(
        default=365, ge=1, description="Maximum age of commits to consider"
    )
    include_merge_commits: bool = Field(
        default=False, description="Include merge commits in analysis"
    )


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = Field(default=True, description="Enable caching")
    duration_hours: int = Field(default=24, ge=1, description="Cache duration in hours")
    max_size_mb: int = Field(default=100, ge=1, description="Maximum cache size in MB")
    cache_dir: str = Field(default=".forkscout/cache", description="Cache directory")
    cleanup_on_startup: bool = Field(
        default=True, description="Clean expired cache on startup"
    )


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""

    requests_per_minute: int = Field(
        default=60, ge=1, description="Requests per minute limit"
    )
    max_concurrent_requests: int = Field(
        default=10, ge=1, description="Maximum concurrent requests"
    )
    burst_limit: int = Field(default=100, ge=1, description="Burst request limit")
    backoff_factor: float = Field(
        default=2.0, ge=1.0, description="Exponential backoff factor"
    )
    max_backoff_seconds: float = Field(
        default=300.0, ge=1.0, description="Maximum backoff delay"
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="CRITICAL", description="Log level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )
    file_enabled: bool = Field(default=True, description="Enable file logging")
    file_path: str = Field(default="forkscout.log", description="Log file path")
    max_file_size_mb: int = Field(
        default=10, ge=1, description="Maximum log file size in MB"
    )
    backup_count: int = Field(default=5, ge=0, description="Number of backup log files")
    console_enabled: bool = Field(default=True, description="Enable console logging")

    @field_validator("level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.upper()


class ForkscoutConfig(BaseSettings):
    """Main configuration for Forkscout application."""

    # Configuration sections
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    interactive: InteractiveConfig = Field(default_factory=InteractiveConfig)
    ai_summary: AISummaryConfig = Field(default_factory=AISummaryConfig)
    fork_filtering: ForkFilteringConfig = Field(default_factory=ForkFilteringConfig)
    commit_count: CommitCountConfig = Field(default_factory=CommitCountConfig)

    # Global settings
    debug: bool = Field(default=False, description="Enable debug mode")
    dry_run: bool = Field(default=False, description="Enable dry run mode")
    output_format: str = Field(
        default="markdown", description="Output format (markdown, json, yaml)"
    )
    openai_api_key: str | None = Field(
        None, description="OpenAI API key for AI summaries"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    @field_validator("output_format")
    @classmethod
    def validate_output_format(cls, v: str) -> str:
        """Validate output format."""
        valid_formats = ["markdown", "json", "yaml"]
        if v.lower() not in valid_formats:
            raise ValueError(f"Invalid output format. Must be one of: {valid_formats}")
        return v.lower()

    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_api_key(cls, v: str | None) -> str | None:
        """Validate OpenAI API key format."""
        if v is None:
            return v

        # OpenAI API keys should start with 'sk-' and be at least 20 characters
        if not v.startswith("sk-"):
            raise ValueError("OpenAI API key must start with 'sk-'")

        if len(v) < 20:
            raise ValueError("OpenAI API key is too short")

        return v

    @classmethod
    def from_file(cls, config_path: str | Path) -> "ForkscoutConfig":
        """Load configuration from YAML or JSON file."""
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path, encoding="utf-8") as f:
                if config_path.suffix.lower() in [".yaml", ".yml"]:
                    data = yaml.safe_load(f)
                elif config_path.suffix.lower() == ".json":
                    data = json.load(f)
                else:
                    raise ValueError(
                        f"Unsupported config file format: {config_path.suffix}"
                    )

            # Handle empty or None data
            if data is None:
                data = {}

            return cls(**data)

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file: {e}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}") from e
        except Exception as e:
            raise ValueError(f"Error loading config file: {e}") from e

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ForkscoutConfig":
        """Create configuration from dictionary."""
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump(exclude_none=True)

    def to_yaml(self) -> str:
        """Convert configuration to YAML string."""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    def to_json(self) -> str:
        """Convert configuration to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def save_to_file(self, config_path: str | Path) -> None:
        """Save configuration to file."""
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w", encoding="utf-8") as f:
            if config_path.suffix.lower() in [".yaml", ".yml"]:
                f.write(self.to_yaml())
            elif config_path.suffix.lower() == ".json":
                f.write(self.to_json())
            else:
                raise ValueError(
                    f"Unsupported config file format: {config_path.suffix}"
                )

    def merge_with_env(self) -> "ForkscoutConfig":
        """Merge configuration with environment variables."""
        # Create a new instance that will automatically load env vars
        env_data = {}

        # Map environment variables to config structure
        env_mappings = {
            "GITHUB_TOKEN": ("github", "token"),
            "GITHUB_BASE_URL": ("github", "base_url"),
            "MIN_SCORE_THRESHOLD": ("analysis", "min_score_threshold"),
            "MAX_FORKS_TO_ANALYZE": ("analysis", "max_forks_to_analyze"),
            "AUTO_PR_ENABLED": ("analysis", "auto_pr_enabled"),
            "CACHE_DURATION_HOURS": ("cache", "duration_hours"),
            "MAX_CACHE_SIZE_MB": ("cache", "max_size_mb"),
            "REQUESTS_PER_MINUTE": ("rate_limit", "requests_per_minute"),
            "MAX_CONCURRENT_REQUESTS": ("rate_limit", "max_concurrent_requests"),
            "LOG_LEVEL": ("logging", "level"),
            "DEBUG": ("debug",),
            "OPENAI_API_KEY": ("openai_api_key",),
        }

        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Navigate to the correct nested structure
                current = env_data
                for key in config_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]

                # Convert value to appropriate type
                final_key = config_path[-1]
                if env_var in ["AUTO_PR_ENABLED", "DEBUG"]:
                    current[final_key] = value.lower() in ("true", "1", "yes", "on")
                elif env_var in [
                    "MIN_SCORE_THRESHOLD",
                    "MAX_FORKS_TO_ANALYZE",
                    "CACHE_DURATION_HOURS",
                    "MAX_CACHE_SIZE_MB",
                    "REQUESTS_PER_MINUTE",
                    "MAX_CONCURRENT_REQUESTS",
                ]:
                    try:
                        current[final_key] = (
                            int(value) if "." not in value else float(value)
                        )
                    except ValueError:
                        continue  # Skip invalid numeric values
                else:
                    current[final_key] = value

        # Merge with current config
        current_dict = self.to_dict()
        merged_dict = self._deep_merge(current_dict, env_data)

        return self.__class__.from_dict(merged_dict)

    @staticmethod
    def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = ForkscoutConfig._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def validate_github_token(self) -> bool:
        """Validate that GitHub token is available and properly formatted."""
        if not self.github.token:
            return False

        try:
            self.github.validate_token_format(self.github.token)
            return True
        except ValueError:
            return False

    def validate_openai_api_key_available(self) -> bool:
        """Validate that OpenAI API key is available and properly formatted."""
        if not self.openai_api_key:
            return False

        try:
            # Call the class method validator
            self.__class__.validate_openai_api_key(self.openai_api_key)
            return True
        except ValueError:
            return False

    def get_cache_path(self) -> Path:
        """Get the full cache directory path."""
        return Path(self.cache.cache_dir).expanduser().resolve()

    def get_log_path(self) -> Path:
        """Get the full log file path."""
        return Path(self.logging.file_path).expanduser().resolve()


def load_config(config_path: str | Path | None = None) -> ForkscoutConfig:
    """Load configuration from file or environment variables."""
    if config_path:
        config = ForkscoutConfig.from_file(config_path)
    else:
        # Try to find config file in common locations
        possible_paths = [
            Path("forkscout.yaml"),
            Path("forkscout.yml"),
            Path("forkscout.json"),
            Path(".forkscout/config.yaml"),
            Path(".forkscout/config.yml"),
            Path(".forkscout/config.json"),
        ]

        config = None
        for path in possible_paths:
            if path.exists():
                config = ForkscoutConfig.from_file(path)
                break

        if config is None:
            # No config file found, use defaults
            config = ForkscoutConfig()

    # Merge with environment variables
    return config.merge_with_env()
