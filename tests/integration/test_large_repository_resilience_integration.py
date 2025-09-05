"""Integration tests for large repository resilience."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from forklift.config import ForkliftConfig
from forklift.github.client import GitHubClient
from forklift.github.rate_limiter import CircuitBreakerConfig


class TestResilientClientIntegration:
    """Test integration of resilient GitHub client."""

    @pytest.mark.asyncio
    async def test_create_resilient_client_without_url(self):
        """Test creating resilient client without repository URL."""
        config = ForkliftConfig()
        
        client = await GitHubClient.create_resilient_client(config.github)
        
        # Should use default circuit breaker configuration
        assert client.circuit_breaker.repository_size == 0
        assert client.circuit_breaker.failure_threshold == 5
        
        await client.close()

    @pytest.mark.asyncio
    async def test_create_resilient_client_with_custom_config(self):
        """Test creating resilient client with custom circuit breaker config."""
        config = ForkliftConfig()
        custom_config = CircuitBreakerConfig(
            base_failure_threshold=15,
            large_repo_failure_threshold=30
        )
        
        client = await GitHubClient.create_resilient_client(
            config.github, 
            circuit_breaker_config=custom_config
        )
        
        # Should use custom configuration
        assert client.circuit_breaker.failure_threshold == 15
        
        await client.close()

    @pytest.mark.asyncio
    @patch('forklift.github.rate_limiter.RepositorySizeDetector.detect_repository_size')
    async def test_create_resilient_client_with_size_detection(self, mock_detect_size):
        """Test creating resilient client with repository size detection."""
        config = ForkliftConfig()
        mock_detect_size.return_value = 2500  # Very large repository
        
        client = await GitHubClient.create_resilient_client(
            config.github,
            "https://github.com/owner/large-repo"
        )
        
        # Should detect large repository and adjust threshold
        assert client.circuit_breaker.repository_size == 2500
        assert client.circuit_breaker.failure_threshold == 50  # Very large repo threshold
        
        mock_detect_size.assert_called_once()
        await client.close()

    @pytest.mark.asyncio
    @patch('forklift.github.rate_limiter.RepositorySizeDetector.detect_repository_size')
    async def test_create_resilient_client_size_detection_failure(self, mock_detect_size):
        """Test creating resilient client when size detection fails."""
        config = ForkliftConfig()
        mock_detect_size.side_effect = Exception("Detection failed")
        
        client = await GitHubClient.create_resilient_client(
            config.github,
            "https://github.com/owner/repo"
        )
        
        # Should fall back to default configuration
        assert client.circuit_breaker.repository_size == 0
        assert client.circuit_breaker.failure_threshold == 5
        
        await client.close()


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration with GitHub client."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_classification(self):
        """Test that circuit breaker correctly classifies failures in real usage."""
        from forklift.github.exceptions import GitHubRateLimitError, GitHubNotFoundError
        from forklift.github.rate_limiter import CircuitBreakerConfig, FailureType
        
        config = CircuitBreakerConfig()
        client_config = ForkliftConfig()
        
        client = await GitHubClient.create_resilient_client(
            client_config.github,
            circuit_breaker_config=config
        )
        
        # Test rate limit error classification
        rate_limit_error = GitHubRateLimitError("Rate limited")
        failure_type = client.circuit_breaker.classify_failure(rate_limit_error)
        assert failure_type == FailureType.RATE_LIMIT
        
        # Test repository access error classification
        not_found_error = GitHubNotFoundError("Not found")
        failure_type = client.circuit_breaker.classify_failure(not_found_error)
        assert failure_type == FailureType.REPOSITORY_ACCESS
        
        await client.close()

    @pytest.mark.asyncio
    async def test_circuit_breaker_weighted_counting_integration(self):
        """Test weighted failure counting in integrated environment."""
        from forklift.github.rate_limiter import CircuitBreakerConfig, FailureType
        
        config = CircuitBreakerConfig(base_failure_threshold=3)  # Low threshold for testing
        client_config = ForkliftConfig()
        
        client = await GitHubClient.create_resilient_client(
            client_config.github,
            circuit_breaker_config=config
        )
        
        cb = client.circuit_breaker
        
        # Multiple rate limit failures should not open circuit
        for _ in range(5):
            cb._on_failure("test_op", FailureType.RATE_LIMIT)
        
        assert cb.state == "closed"  # Should remain closed
        assert cb.weighted_failure_count == 0.0
        
        # But API errors should open it
        for _ in range(3):
            cb._on_failure("test_op", FailureType.API_ERROR)
        
        assert cb.state == "open"  # Should be open now
        assert cb.weighted_failure_count >= 3.0
        
        await client.close()


class TestCLIIntegration:
    """Test CLI integration with resilience features."""

    def test_cli_resilience_options_available(self):
        """Test that resilience CLI options are available."""
        from click.testing import CliRunner
        from forklift.cli import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ['show-forks', '--help'])
        
        # Check that resilience options are present in help
        assert '--circuit-breaker-threshold' in result.output
        assert '--continue-on-circuit-open' in result.output
        assert '--skip-failed-forks' in result.output
        assert '--circuit-open-retry-interval' in result.output

    def test_cli_resilience_options_validation(self):
        """Test that CLI resilience options validate correctly."""
        from click.testing import CliRunner
        from forklift.cli import cli
        
        runner = CliRunner()
        
        # Test invalid circuit breaker threshold
        result = runner.invoke(cli, [
            'show-forks', 'owner/repo',
            '--circuit-breaker-threshold', '0'  # Below minimum
        ])
        assert result.exit_code != 0
        assert 'Invalid value' in result.output
        
        # Test invalid retry interval
        result = runner.invoke(cli, [
            'show-forks', 'owner/repo', 
            '--circuit-open-retry-interval', '1.0'  # Below minimum
        ])
        assert result.exit_code != 0
        assert 'Invalid value' in result.output


class TestEndToEndResilience:
    """Test end-to-end resilience functionality."""

    @pytest.mark.asyncio
    @patch('forklift.github.client.GitHubClient.get_repository')
    async def test_resilient_client_handles_repository_detection_gracefully(self, mock_get_repo):
        """Test that resilient client handles repository detection failures gracefully."""
        from forklift.github.exceptions import GitHubAuthenticationError
        
        # Mock repository detection failure
        mock_get_repo.side_effect = GitHubAuthenticationError("Auth failed")
        
        config = ForkliftConfig()
        
        # Should not raise exception, should fall back to default config
        client = await GitHubClient.create_resilient_client(
            config.github,
            "https://github.com/owner/repo"
        )
        
        # Should have default configuration due to detection failure
        assert client.circuit_breaker.repository_size == 0
        assert client.circuit_breaker.failure_threshold == 5
        
        await client.close()

    @pytest.mark.asyncio
    async def test_circuit_breaker_maintains_backward_compatibility(self):
        """Test that enhanced circuit breaker maintains backward compatibility."""
        config = ForkliftConfig()
        
        # Create client using old-style constructor (should still work)
        client = GitHubClient(config.github)
        
        # Should have default circuit breaker
        assert hasattr(client.circuit_breaker, 'failure_threshold')
        assert hasattr(client.circuit_breaker, 'timeout')
        assert hasattr(client.circuit_breaker, 'state')
        
        # Should support both old and new failure handling
        assert hasattr(client.circuit_breaker, 'classify_failure')
        assert hasattr(client.circuit_breaker, 'weighted_failure_count')
        
        await client.close()