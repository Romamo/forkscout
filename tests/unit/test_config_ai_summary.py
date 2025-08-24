"""Unit tests for AI summary configuration in ForkliftConfig."""

import pytest
from pydantic import ValidationError

from forklift.config.settings import ForkliftConfig
from forklift.models.ai_summary import AISummaryConfig


class TestForkliftConfigAISummary:
    """Test cases for AI summary configuration in ForkliftConfig."""

    def test_forklift_config_includes_ai_summary_config(self):
        """Test that ForkliftConfig includes AI summary configuration."""
        config = ForkliftConfig()
        
        assert hasattr(config, 'ai_summary')
        assert isinstance(config.ai_summary, AISummaryConfig)
        assert config.ai_summary.enabled is False  # Default value

    def test_forklift_config_includes_openai_api_key(self):
        """Test that ForkliftConfig includes OpenAI API key field."""
        import os
        from unittest.mock import patch
        
        # Mock environment to avoid loading from .env file
        with patch.dict(os.environ, {}, clear=True):
            config = ForkliftConfig(_env_file=None)  # Don't load from .env
            
            assert hasattr(config, 'openai_api_key')
            assert config.openai_api_key is None  # Default value when no env var

    def test_forklift_config_with_valid_openai_api_key(self):
        """Test ForkliftConfig with valid OpenAI API key."""
        config = ForkliftConfig(openai_api_key="sk-1234567890abcdef1234567890abcdef")
        
        assert config.openai_api_key == "sk-1234567890abcdef1234567890abcdef"

    def test_forklift_config_openai_api_key_validation_invalid_prefix(self):
        """Test validation of OpenAI API key with invalid prefix."""
        import os
        from unittest.mock import patch
        
        # Mock environment to avoid loading from .env file
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                ForkliftConfig(openai_api_key="invalid-key-format", _env_file=None)
            
            assert "must start with 'sk-'" in str(exc_info.value)

    def test_forklift_config_openai_api_key_validation_too_short(self):
        """Test validation of OpenAI API key that is too short."""
        import os
        from unittest.mock import patch
        
        # Mock environment to avoid loading from .env file
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                ForkliftConfig(openai_api_key="sk-short", _env_file=None)
            
            assert "too short" in str(exc_info.value)

    def test_forklift_config_openai_api_key_validation_none_allowed(self):
        """Test that None is allowed for OpenAI API key."""
        import os
        from unittest.mock import patch
        
        # Mock environment to avoid loading from .env file
        with patch.dict(os.environ, {}, clear=True):
            config = ForkliftConfig(openai_api_key=None, _env_file=None)
            
            assert config.openai_api_key is None

    def test_forklift_config_ai_summary_custom_values(self):
        """Test ForkliftConfig with custom AI summary configuration."""
        config = ForkliftConfig(
            ai_summary=AISummaryConfig(
                enabled=True,
                model="gpt-4",
                max_tokens=1000,
                temperature=0.5
            )
        )
        
        assert config.ai_summary.enabled is True
        assert config.ai_summary.model == "gpt-4"
        assert config.ai_summary.max_tokens == 1000
        assert config.ai_summary.temperature == 0.5

    def test_validate_openai_api_key_method_with_valid_key(self):
        """Test validate_openai_api_key_available method with valid key."""
        config = ForkliftConfig(openai_api_key="sk-1234567890abcdef1234567890abcdef")
        
        assert config.validate_openai_api_key_available() is True

    def test_validate_openai_api_key_method_with_none(self):
        """Test validate_openai_api_key_available method with None key."""
        import os
        from unittest.mock import patch
        
        # Mock environment to avoid loading from .env file
        with patch.dict(os.environ, {}, clear=True):
            config = ForkliftConfig(openai_api_key=None, _env_file=None)
            
            assert config.validate_openai_api_key_available() is False

    def test_validate_openai_api_key_method_with_invalid_key(self):
        """Test validate_openai_api_key_available method with invalid key."""
        # Create config without validation to test the method
        config = ForkliftConfig()
        config.openai_api_key = "invalid-key"  # Set directly to bypass validation
        
        assert config.validate_openai_api_key_available() is False

    def test_forklift_config_serialization_with_ai_summary(self):
        """Test ForkliftConfig serialization includes AI summary fields."""
        config = ForkliftConfig(
            openai_api_key="sk-1234567890abcdef1234567890abcdef",
            ai_summary=AISummaryConfig(
                enabled=True,
                model="gpt-4",
                max_tokens=800
            )
        )
        
        data = config.to_dict()
        
        assert "openai_api_key" in data
        assert "ai_summary" in data
        assert data["ai_summary"]["enabled"] is True
        assert data["ai_summary"]["model"] == "gpt-4"
        assert data["ai_summary"]["max_tokens"] == 800

    def test_forklift_config_from_dict_with_ai_summary(self):
        """Test ForkliftConfig creation from dict with AI summary fields."""
        data = {
            "openai_api_key": "sk-1234567890abcdef1234567890abcdef",
            "ai_summary": {
                "enabled": True,
                "model": "gpt-4",
                "max_tokens": 800,
                "temperature": 0.7
            }
        }
        
        config = ForkliftConfig.from_dict(data)
        
        assert config.openai_api_key == "sk-1234567890abcdef1234567890abcdef"
        assert config.ai_summary.enabled is True
        assert config.ai_summary.model == "gpt-4"
        assert config.ai_summary.max_tokens == 800
        assert config.ai_summary.temperature == 0.7

    def test_forklift_config_environment_variable_mapping(self):
        """Test that OPENAI_API_KEY environment variable is mapped correctly."""
        import os
        
        # Set environment variable
        os.environ["OPENAI_API_KEY"] = "sk-test1234567890abcdef1234567890"
        
        try:
            config = ForkliftConfig()
            merged_config = config.merge_with_env()
            
            assert merged_config.openai_api_key == "sk-test1234567890abcdef1234567890"
        finally:
            # Clean up environment variable
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    def test_forklift_config_yaml_serialization_with_ai_summary(self):
        """Test ForkliftConfig YAML serialization includes AI summary fields."""
        config = ForkliftConfig(
            openai_api_key="sk-1234567890abcdef1234567890abcdef",
            ai_summary=AISummaryConfig(enabled=True, model="gpt-4")
        )
        
        yaml_str = config.to_yaml()
        
        assert "openai_api_key:" in yaml_str
        assert "ai_summary:" in yaml_str
        assert "enabled: true" in yaml_str
        assert "model: gpt-4" in yaml_str

    def test_forklift_config_json_serialization_with_ai_summary(self):
        """Test ForkliftConfig JSON serialization includes AI summary fields."""
        config = ForkliftConfig(
            openai_api_key="sk-1234567890abcdef1234567890abcdef",
            ai_summary=AISummaryConfig(enabled=True, model="gpt-4")
        )
        
        json_str = config.to_json()
        
        assert '"openai_api_key"' in json_str
        assert '"ai_summary"' in json_str
        assert '"enabled": true' in json_str
        assert '"model": "gpt-4"' in json_str


class TestAISummaryConfigIntegration:
    """Test cases for AISummaryConfig integration with ForkliftConfig."""

    def test_ai_summary_config_defaults_in_forklift_config(self):
        """Test that AISummaryConfig defaults are preserved in ForkliftConfig."""
        config = ForkliftConfig()
        
        assert config.ai_summary.enabled is False
        assert config.ai_summary.model == "gpt-4o-mini"
        assert config.ai_summary.max_tokens == 150
        assert config.ai_summary.max_diff_chars == 8000
        assert config.ai_summary.temperature == 0.3
        assert config.ai_summary.timeout_seconds == 30
        assert config.ai_summary.retry_attempts == 3
        assert config.ai_summary.cost_tracking is True
        assert config.ai_summary.batch_size == 5

    def test_ai_summary_config_validation_in_forklift_config(self):
        """Test that AISummaryConfig validation works within ForkliftConfig."""
        # Test invalid max_tokens
        with pytest.raises(ValidationError):
            ForkliftConfig(
                ai_summary=AISummaryConfig(max_tokens=5000)  # Too high
            )
        
        # Test invalid temperature
        with pytest.raises(ValidationError):
            ForkliftConfig(
                ai_summary=AISummaryConfig(temperature=3.0)  # Too high
            )
        
        # Test invalid batch_size
        with pytest.raises(ValidationError):
            ForkliftConfig(
                ai_summary=AISummaryConfig(batch_size=25)  # Too high
            )

    def test_ai_summary_config_nested_dict_creation(self):
        """Test creating ForkliftConfig with nested AI summary dict."""
        config_data = {
            "ai_summary": {
                "enabled": True,
                "model": "gpt-4",
                "max_tokens": 1000,
                "temperature": 0.5,
                "timeout_seconds": 60,
                "retry_attempts": 5,
                "cost_tracking": False,
                "batch_size": 10,
                "compact_mode": True
            }
        }
        
        config = ForkliftConfig(**config_data)
        
        assert config.ai_summary.enabled is True
        assert config.ai_summary.model == "gpt-4"
        assert config.ai_summary.max_tokens == 1000
        assert config.ai_summary.temperature == 0.5
        assert config.ai_summary.timeout_seconds == 60
        assert config.ai_summary.retry_attempts == 5
        assert config.ai_summary.cost_tracking is False
        assert config.ai_summary.batch_size == 10
        assert config.ai_summary.compact_mode is True

    def test_ai_summary_config_compact_mode_integration(self):
        """Test ForkliftConfig integration with compact_mode setting."""
        # Test default compact_mode is False
        config = ForkliftConfig()
        assert config.ai_summary.compact_mode is False
        
        # Test setting compact_mode to True
        config_compact = ForkliftConfig(
            ai_summary=AISummaryConfig(compact_mode=True)
        )
        assert config_compact.ai_summary.compact_mode is True
        
        # Test serialization includes compact_mode
        data = config_compact.to_dict()
        assert data["ai_summary"]["compact_mode"] is True
        
        # Test deserialization preserves compact_mode
        reconstructed = ForkliftConfig.from_dict(data)
        assert reconstructed.ai_summary.compact_mode is True