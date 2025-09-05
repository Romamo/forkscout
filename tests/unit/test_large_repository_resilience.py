"""Unit tests for large repository resilience enhancements."""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock

from forklift.github.rate_limiter import (
    CircuitBreaker,
    CircuitBreakerConfig,
    FailureType,
    RepositorySizeDetector,
    DegradationConfig,
    GracefulDegradationHandler,
)
from forklift.github.exceptions import (
    GitHubRateLimitError,
    GitHubNotFoundError,
    GitHubAuthenticationError,
    GitHubPrivateRepositoryError,
    GitHubForkAccessError,
    GitHubTimeoutError,
)


class TestFailureTypeClassification:
    """Test failure type classification for circuit breaker."""

    def test_classify_rate_limit_error(self):
        """Test that rate limit errors are classified correctly."""
        config = CircuitBreakerConfig()
        cb = CircuitBreaker(config=config)
        
        error = GitHubRateLimitError("Rate limited")
        failure_type = cb.classify_failure(error)
        
        assert failure_type == FailureType.RATE_LIMIT

    def test_classify_repository_access_errors(self):
        """Test that repository access errors are classified correctly."""
        config = CircuitBreakerConfig()
        cb = CircuitBreaker(config=config)
        
        errors = [
            GitHubNotFoundError("Not found"),
            GitHubAuthenticationError("Auth failed"),
            GitHubPrivateRepositoryError("Private repo", "owner/repo"),
            GitHubForkAccessError("Fork access denied", "fork_url", "private"),
        ]
        
        for error in errors:
            failure_type = cb.classify_failure(error)
            assert failure_type == FailureType.REPOSITORY_ACCESS

    def test_classify_timeout_errors(self):
        """Test that timeout errors are classified correctly."""
        config = CircuitBreakerConfig()
        cb = CircuitBreaker(config=config)
        
        errors = [
            asyncio.TimeoutError(),
            GitHubTimeoutError("Timeout", "operation", 30.0),
        ]
        
        for error in errors:
            failure_type = cb.classify_failure(error)
            assert failure_type == FailureType.TIMEOUT

    def test_classify_network_errors(self):
        """Test that network errors are classified correctly."""
        import httpx
        
        config = CircuitBreakerConfig()
        cb = CircuitBreaker(config=config)
        
        error = httpx.NetworkError("Network error")
        failure_type = cb.classify_failure(error)
        
        assert failure_type == FailureType.NETWORK_ERROR

    def test_classify_generic_api_errors(self):
        """Test that generic errors are classified as API errors."""
        config = CircuitBreakerConfig()
        cb = CircuitBreaker(config=config)
        
        error = Exception("Generic error")
        failure_type = cb.classify_failure(error)
        
        assert failure_type == FailureType.API_ERROR


class TestCircuitBreakerConfig:
    """Test circuit breaker configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()
        
        assert config.base_failure_threshold == 5
        assert config.large_repo_failure_threshold == 25
        assert config.timeout_seconds == 60.0
        assert config.large_repo_timeout_seconds == 30.0
        assert config.large_repo_fork_threshold == 1000
        
        # Test failure weights
        assert config.failure_weights[FailureType.RATE_LIMIT] == 0.0
        assert config.failure_weights[FailureType.REPOSITORY_ACCESS] == 0.1
        assert config.failure_weights[FailureType.NETWORK_ERROR] == 0.5
        assert config.failure_weights[FailureType.TIMEOUT] == 0.5
        assert config.failure_weights[FailureType.API_ERROR] == 1.0

    def test_custom_config(self):
        """Test custom configuration values."""
        custom_weights = {
            FailureType.RATE_LIMIT: 0.0,
            FailureType.API_ERROR: 2.0,
        }
        
        config = CircuitBreakerConfig(
            base_failure_threshold=10,
            large_repo_failure_threshold=50,
            failure_weights=custom_weights
        )
        
        assert config.base_failure_threshold == 10
        assert config.large_repo_failure_threshold == 50
        assert config.failure_weights == custom_weights


class TestEnhancedCircuitBreaker:
    """Test enhanced circuit breaker functionality."""

    def test_repository_size_aware_threshold(self):
        """Test that circuit breaker adjusts threshold based on repository size."""
        config = CircuitBreakerConfig()
        
        # Small repository
        small_cb = CircuitBreaker(config=config, repository_size=100)
        assert small_cb.failure_threshold == 5
        
        # Large repository
        large_cb = CircuitBreaker(config=config, repository_size=2000)
        assert large_cb.failure_threshold == 25

    def test_repository_size_aware_timeout(self):
        """Test that circuit breaker adjusts timeout based on repository size."""
        config = CircuitBreakerConfig()
        
        # Small repository
        small_cb = CircuitBreaker(config=config, repository_size=100)
        assert small_cb.timeout == 60.0
        
        # Large repository
        large_cb = CircuitBreaker(config=config, repository_size=2000)
        assert large_cb.timeout == 30.0

    def test_weighted_failure_counting(self):
        """Test that failures are counted with appropriate weights."""
        config = CircuitBreakerConfig()
        cb = CircuitBreaker(config=config, repository_size=100)
        
        # Rate limit failure should not count
        cb._on_failure("test_op", FailureType.RATE_LIMIT)
        assert cb.weighted_failure_count == 0.0
        assert cb.state == "closed"
        
        # Repository access failure should count very little
        cb._on_failure("test_op", FailureType.REPOSITORY_ACCESS)
        assert cb.weighted_failure_count == 0.1
        assert cb.state == "closed"
        
        # API errors should count fully
        for _ in range(5):
            cb._on_failure("test_op", FailureType.API_ERROR)
        
        assert cb.weighted_failure_count >= 5.0
        assert cb.state == "open"

    def test_failure_history_cleanup(self):
        """Test that old failures are cleaned up from history."""
        config = CircuitBreakerConfig()
        cb = CircuitBreaker(config=config, repository_size=100)
        
        # Add some failures
        cb._on_failure("test_op", FailureType.API_ERROR)
        cb._on_failure("test_op", FailureType.NETWORK_ERROR)
        
        assert len(cb.failure_history) == 2
        
        # Manually set old timestamps to test cleanup
        import time
        old_time = time.time() - 400  # 400 seconds ago (older than 5 minutes)
        cb.failure_history[0] = (old_time, FailureType.API_ERROR)
        
        # Add another failure to trigger cleanup
        cb._on_failure("test_op", FailureType.API_ERROR)
        
        # Old failure should be cleaned up
        assert len(cb.failure_history) == 2  # Only recent failures remain
        assert all(timestamp > old_time + 100 for timestamp, _ in cb.failure_history)

    def test_backward_compatibility(self):
        """Test that enhanced circuit breaker maintains backward compatibility."""
        # Test legacy constructor
        cb = CircuitBreaker(failure_threshold=10, timeout=120.0)
        
        assert cb.failure_threshold == 10
        assert cb.timeout == 120.0
        assert cb.repository_size == 0
        
        # Test legacy failure counting still works
        cb._on_failure("test_op")  # Should use default API_ERROR type
        assert cb.failure_count == 1
        assert cb.weighted_failure_count == 1.0


class TestRepositorySizeDetector:
    """Test repository size detection functionality."""

    def test_extract_owner_repo_from_url(self):
        """Test URL parsing for different GitHub URL formats."""
        test_cases = [
            ("https://github.com/owner/repo", ("owner", "repo")),
            ("https://github.com/owner/repo/", ("owner", "repo")),
            ("https://github.com/owner/repo.git", ("owner", "repo")),
            ("git@github.com:owner/repo.git", ("owner", "repo")),
            ("github.com/owner/repo", ("owner", "repo")),
            ("owner/repo", ("owner", "repo")),
        ]
        
        for url, expected in test_cases:
            result = RepositorySizeDetector.extract_owner_repo_from_url(url)
            assert result == expected

    def test_extract_owner_repo_invalid_url(self):
        """Test URL parsing with invalid URLs."""
        invalid_urls = [
            "not-a-url",
            "https://gitlab.com/owner/repo",
            "just-text",
            "",
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValueError):
                RepositorySizeDetector.extract_owner_repo_from_url(url)

    def test_get_recommended_config_small_repo(self):
        """Test recommended config for small repositories."""
        config = RepositorySizeDetector.get_recommended_config(100)
        
        assert config.base_failure_threshold == 5
        assert config.large_repo_failure_threshold == 25  # Default value for small repos
        assert config.timeout_seconds == 60.0

    def test_get_recommended_config_medium_repo(self):
        """Test recommended config for medium repositories."""
        config = RepositorySizeDetector.get_recommended_config(750)
        
        assert config.base_failure_threshold == 5
        assert config.large_repo_failure_threshold == 15
        assert config.large_repo_fork_threshold == 500

    def test_get_recommended_config_large_repo(self):
        """Test recommended config for large repositories."""
        config = RepositorySizeDetector.get_recommended_config(1500)
        
        assert config.base_failure_threshold == 5
        assert config.large_repo_failure_threshold == 25
        assert config.large_repo_fork_threshold == 1000

    def test_get_recommended_config_very_large_repo(self):
        """Test recommended config for very large repositories."""
        config = RepositorySizeDetector.get_recommended_config(3000)
        
        assert config.base_failure_threshold == 5
        assert config.large_repo_failure_threshold == 50
        assert config.large_repo_fork_threshold == 2000
        assert config.large_repo_timeout_seconds == 20.0

    @pytest.mark.asyncio
    async def test_detect_repository_size_success(self):
        """Test successful repository size detection."""
        # Mock GitHub client
        mock_client = AsyncMock()
        mock_repo = Mock()
        mock_repo.forks_count = 1234
        mock_client.get_repository.return_value = mock_repo
        
        size = await RepositorySizeDetector.detect_repository_size(
            mock_client, "https://github.com/owner/repo"
        )
        
        assert size == 1234
        mock_client.get_repository.assert_called_once_with("owner", "repo")

    @pytest.mark.asyncio
    async def test_detect_repository_size_failure(self):
        """Test repository size detection with API failure."""
        # Mock GitHub client that raises an exception
        mock_client = AsyncMock()
        mock_client.get_repository.side_effect = Exception("API Error")
        
        size = await RepositorySizeDetector.detect_repository_size(
            mock_client, "https://github.com/owner/repo"
        )
        
        # Should return 0 on failure
        assert size == 0


class TestGracefulDegradationHandler:
    """Test graceful degradation functionality."""

    def test_degradation_config_defaults(self):
        """Test default degradation configuration."""
        config = DegradationConfig()
        
        assert config.continue_on_circuit_open is True
        assert config.circuit_open_retry_interval == 30.0
        assert config.max_circuit_open_retries == 10
        assert config.skip_failed_items is True

    @pytest.mark.asyncio
    async def test_handle_circuit_open_disabled(self):
        """Test behavior when continue_on_circuit_open is disabled."""
        config = DegradationConfig(continue_on_circuit_open=False)
        handler = GracefulDegradationHandler(config)
        
        mock_circuit_breaker = Mock()
        
        with pytest.raises(Exception, match="Circuit breaker is open"):
            await handler.handle_circuit_open(
                remaining_items=[1, 2, 3],
                processor_func=lambda x: x,
                circuit_breaker=mock_circuit_breaker,
                operation_name="test_op"
            )

    @pytest.mark.asyncio
    async def test_handle_circuit_open_success(self):
        """Test successful processing during circuit breaker recovery."""
        config = DegradationConfig(
            circuit_open_retry_interval=0.1,  # Fast for testing
            max_circuit_open_retries=2
        )
        handler = GracefulDegradationHandler(config)
        
        # Mock circuit breaker that succeeds on retry
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.call.return_value = "processed"
        
        # Mock processor function
        async def mock_processor(item):
            return f"processed_{item}"
        
        results = await handler.handle_circuit_open(
            remaining_items=[1, 2],
            processor_func=mock_processor,
            circuit_breaker=mock_circuit_breaker,
            operation_name="test_op"
        )
        
        assert len(results) == 2
        assert results[0] == (1, "processed")
        assert results[1] == (2, "processed")

    @pytest.mark.asyncio
    async def test_handle_circuit_open_with_failures(self):
        """Test processing with some failures during circuit breaker recovery."""
        config = DegradationConfig(
            circuit_open_retry_interval=0.1,  # Fast for testing
            max_circuit_open_retries=1,
            skip_failed_items=True
        )
        handler = GracefulDegradationHandler(config)
        
        # Mock circuit breaker that fails for item 2
        mock_circuit_breaker = AsyncMock()
        
        async def mock_call(func, operation_name):
            result = await func()
            if "item_2" in str(result):
                raise Exception("Simulated failure")
            return result
        
        mock_circuit_breaker.call.side_effect = mock_call
        
        # Mock processor function
        async def mock_processor(item):
            return f"processed_item_{item}"
        
        results = await handler.handle_circuit_open(
            remaining_items=[1, 2, 3],
            processor_func=mock_processor,
            circuit_breaker=mock_circuit_breaker,
            operation_name="test_op"
        )
        
        # Should have processed items 1 and 3, skipped item 2
        assert len(results) == 2
        processed_items = [item for item, _ in results]
        assert 1 in processed_items
        assert 3 in processed_items
        assert 2 not in processed_items

    def test_reset_retry_count(self):
        """Test retry count reset functionality."""
        config = DegradationConfig()
        handler = GracefulDegradationHandler(config)
        
        handler.circuit_open_retry_count = 5
        handler.circuit_open_start_time = 12345.0
        
        handler.reset_retry_count()
        
        assert handler.circuit_open_retry_count == 0
        assert handler.circuit_open_start_time is None