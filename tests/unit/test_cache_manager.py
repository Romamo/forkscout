"""Tests for the cache management service."""

import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from src.forklift.models.cache import CacheConfig
from src.forklift.storage.cache_manager import (
    CacheManager, 
    CacheWarmingConfig, 
    CacheCleanupConfig,
    CacheMonitoringMetrics
)
from src.forklift.storage.cache import ForkliftCache
from src.forklift.storage.analysis_cache import AnalysisCacheManager


@pytest.fixture
async def temp_cache_config():
    """Create a temporary cache configuration for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        config = CacheConfig(database_path=tmp.name)
        yield config
        # Cleanup
        Path(tmp.name).unlink(missing_ok=True)


@pytest.fixture
async def cache_manager(temp_cache_config):
    """Create and initialize a cache manager for testing."""
    manager = CacheManager(config=temp_cache_config)
    await manager.initialize()
    yield manager
    await manager.close()


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client for testing."""
    client = Mock()
    client.get_repository = AsyncMock()
    client.get_forks = AsyncMock()
    return client


class TestCacheWarmingConfig:
    """Test cases for CacheWarmingConfig class."""
    
    def test_default_config(self):
        """Test default cache warming configuration."""
        config = CacheWarmingConfig()
        
        assert config.repositories == []
        assert config.warm_repository_metadata is True
        assert config.warm_fork_lists is True
        assert config.warm_recent_analyses is True
        assert config.max_concurrent_operations == 5
        assert config.batch_size == 10
    
    def test_custom_config(self):
        """Test custom cache warming configuration."""
        repositories = ["https://github.com/owner1/repo1", "https://github.com/owner2/repo2"]
        config = CacheWarmingConfig(
            repositories=repositories,
            warm_repository_metadata=False,
            warm_fork_lists=True,
            warm_recent_analyses=False,
            max_concurrent_operations=10,
            batch_size=5
        )
        
        assert config.repositories == repositories
        assert config.warm_repository_metadata is False
        assert config.warm_fork_lists is True
        assert config.warm_recent_analyses is False
        assert config.max_concurrent_operations == 10
        assert config.batch_size == 5


class TestCacheCleanupConfig:
    """Test cases for CacheCleanupConfig class."""
    
    def test_default_config(self):
        """Test default cache cleanup configuration."""
        config = CacheCleanupConfig()
        
        assert config.remove_expired is True
        assert config.remove_old_entries is True
        assert config.max_age_days == 30
        assert config.max_cache_size_mb == 100
        assert config.vacuum_after_cleanup is True
        assert config.cleanup_batch_size == 1000
    
    def test_custom_config(self):
        """Test custom cache cleanup configuration."""
        config = CacheCleanupConfig(
            remove_expired=False,
            remove_old_entries=True,
            max_age_days=7,
            max_cache_size_mb=50,
            vacuum_after_cleanup=False,
            cleanup_batch_size=500
        )
        
        assert config.remove_expired is False
        assert config.remove_old_entries is True
        assert config.max_age_days == 7
        assert config.max_cache_size_mb == 50
        assert config.vacuum_after_cleanup is False
        assert config.cleanup_batch_size == 500


class TestCacheMonitoringMetrics:
    """Test cases for CacheMonitoringMetrics class."""
    
    def test_initialization(self):
        """Test monitoring metrics initialization."""
        metrics = CacheMonitoringMetrics()
        
        assert metrics.cache_stats is None
        assert metrics.performance_metrics == {}
        assert metrics.health_status == "unknown"
        assert metrics.last_cleanup is None
        assert metrics.last_warming is None
        assert metrics.error_count == 0
        assert metrics.warning_count == 0


class TestCacheManager:
    """Test cases for CacheManager class."""
    
    async def test_initialization(self, temp_cache_config):
        """Test cache manager initialization and cleanup."""
        manager = CacheManager(config=temp_cache_config)
        
        # Should not be initialized initially
        with pytest.raises(RuntimeError, match="Cache manager not initialized"):
            await manager.get_monitoring_metrics()
        
        await manager.initialize()
        
        # Should work after initialization
        metrics = await manager.get_monitoring_metrics()
        assert isinstance(metrics, dict)
        assert "health_status" in metrics
        
        await manager.close()
    
    async def test_context_manager(self, temp_cache_config):
        """Test using cache manager as async context manager."""
        async with CacheManager(config=temp_cache_config) as manager:
            metrics = await manager.get_monitoring_metrics()
            assert isinstance(metrics, dict)
    
    async def test_with_existing_cache_instances(self, temp_cache_config):
        """Test using existing cache instances."""
        # Create cache instances
        cache = ForkliftCache(temp_cache_config)
        await cache.initialize()
        
        analysis_cache = AnalysisCacheManager(cache, temp_cache_config)
        await analysis_cache.initialize()
        
        # Create manager with existing instances
        manager = CacheManager(cache=cache, analysis_cache=analysis_cache)
        await manager.initialize()
        
        # Should work normally
        metrics = await manager.get_monitoring_metrics()
        assert isinstance(metrics, dict)
        
        await manager.close()
        await analysis_cache.close()
        await cache.close()
    
    async def test_warm_cache_no_github_client(self, cache_manager):
        """Test cache warming without GitHub client."""
        config = CacheWarmingConfig(repositories=["https://github.com/owner/repo"])
        
        results = await cache_manager.warm_cache(config)
        
        assert "started_at" in results
        assert "completed_at" in results
        assert results["repositories_processed"] == 0
        assert len(results["warnings"]) > 0
        assert "No GitHub client provided" in results["warnings"][0]
    
    async def test_warm_cache_with_repositories(self, cache_manager, mock_github_client):
        """Test cache warming with specific repositories."""
        repositories = [
            "https://github.com/owner1/repo1",
            "https://github.com/owner2/repo2"
        ]
        config = CacheWarmingConfig(repositories=repositories, batch_size=1)
        
        results = await cache_manager.warm_cache(config, mock_github_client)
        
        assert "started_at" in results
        assert "completed_at" in results
        assert "duration_seconds" in results
        assert results["repositories_processed"] == len(repositories)
        assert results["metadata_warmed"] == len(repositories)
        assert results["fork_lists_warmed"] == len(repositories)
    
    async def test_warm_cache_with_invalid_repository_url(self, cache_manager, mock_github_client):
        """Test cache warming with invalid repository URL."""
        config = CacheWarmingConfig(repositories=["invalid-url"])
        
        results = await cache_manager.warm_cache(config, mock_github_client)
        
        assert results["repositories_processed"] == 0
        assert len(results["errors"]) > 0
        assert "Invalid repository URL" in results["errors"][0]
    
    async def test_warm_cache_selective_warming(self, cache_manager, mock_github_client):
        """Test selective cache warming."""
        repositories = ["https://github.com/owner/repo"]
        config = CacheWarmingConfig(
            repositories=repositories,
            warm_repository_metadata=True,
            warm_fork_lists=False,
            warm_recent_analyses=False
        )
        
        results = await cache_manager.warm_cache(config, mock_github_client)
        
        assert results["repositories_processed"] == 1
        assert results["metadata_warmed"] == 1
        assert results["fork_lists_warmed"] == 0
        assert results["analyses_warmed"] == 0
    
    async def test_cleanup_cache_default_config(self, cache_manager):
        """Test cache cleanup with default configuration."""
        # Add some test data first
        await cache_manager.analysis_cache.cache_repository_metadata("owner", "repo", {"stars": 100})
        await cache_manager.analysis_cache.cache_fork_list("owner", "repo", [{"name": "fork1"}])
        
        results = await cache_manager.cleanup_cache()
        
        assert "started_at" in results
        assert "completed_at" in results
        assert "duration_seconds" in results
        assert "expired_entries_removed" in results
        assert "old_entries_removed" in results
        assert "size_before_mb" in results
        assert "size_after_mb" in results
        assert results["vacuum_performed"] is True
    
    async def test_cleanup_cache_custom_config(self, cache_manager):
        """Test cache cleanup with custom configuration."""
        config = CacheCleanupConfig(
            remove_expired=True,
            remove_old_entries=False,
            vacuum_after_cleanup=False
        )
        
        results = await cache_manager.cleanup_cache(config)
        
        assert results["vacuum_performed"] is False
        assert "expired_entries_removed" in results
        assert "old_entries_removed" in results
    
    async def test_cleanup_cache_with_expired_entries(self, cache_manager):
        """Test cache cleanup with expired entries."""
        # Add expired entry
        await cache_manager.analysis_cache.cache_repository_metadata(
            "owner", "repo", {"stars": 100}, ttl_hours=-1
        )
        
        results = await cache_manager.cleanup_cache()
        
        assert results["expired_entries_removed"] >= 1
    
    async def test_get_monitoring_metrics(self, cache_manager):
        """Test getting monitoring metrics."""
        # Add some test data
        await cache_manager.analysis_cache.cache_repository_metadata("owner", "repo", {"stars": 100})
        await cache_manager.analysis_cache.cache_fork_list("owner", "repo", [{"name": "fork1"}])
        
        # Trigger some cache operations
        await cache_manager.analysis_cache.get_repository_metadata("owner", "repo")
        await cache_manager.analysis_cache.get_repository_metadata("nonexistent", "repo")
        
        metrics = await cache_manager.get_monitoring_metrics()
        
        assert isinstance(metrics, dict)
        assert "timestamp" in metrics
        assert "health_status" in metrics
        assert "cache_stats" in metrics
        assert "performance_metrics" in metrics
        assert metrics["health_status"] in ["healthy", "warning", "critical", "unknown"]
        
        # Check cache stats
        cache_stats = metrics["cache_stats"]
        assert "total_entries" in cache_stats
        assert "hit_count" in cache_stats
        assert "miss_count" in cache_stats
        assert "hit_rate" in cache_stats
        
        # Check performance metrics
        perf_metrics = metrics["performance_metrics"]
        assert "hit_rate" in perf_metrics
        assert "cache_efficiency" in perf_metrics
        assert "size_utilization" in perf_metrics
    
    async def test_health_status_calculation(self, cache_manager):
        """Test health status calculation logic."""
        # Add test data to get meaningful stats
        await cache_manager.analysis_cache.cache_repository_metadata("owner", "repo", {"stars": 100})
        
        # Trigger cache hits to improve hit rate
        for _ in range(10):
            await cache_manager.analysis_cache.get_repository_metadata("owner", "repo")
        
        metrics = await cache_manager.get_monitoring_metrics()
        
        # Should be healthy with good hit rate and normal size
        assert metrics["health_status"] in ["healthy", "warning"]
    
    async def test_schedule_maintenance(self, cache_manager, mock_github_client):
        """Test scheduled maintenance operations."""
        warming_config = CacheWarmingConfig(repositories=["https://github.com/owner/repo"])
        cleanup_config = CacheCleanupConfig(vacuum_after_cleanup=True)
        
        results = await cache_manager.schedule_maintenance(
            warming_config=warming_config,
            cleanup_config=cleanup_config,
            github_client=mock_github_client
        )
        
        assert "started_at" in results
        assert "completed_at" in results
        assert "duration_seconds" in results
        assert "cleanup_results" in results
        assert "warming_results" in results
        
        # Check cleanup results
        cleanup_results = results["cleanup_results"]
        assert isinstance(cleanup_results, dict)
        assert "expired_entries_removed" in cleanup_results
        
        # Check warming results
        warming_results = results["warming_results"]
        assert isinstance(warming_results, dict)
        assert "repositories_processed" in warming_results
    
    async def test_schedule_maintenance_no_github_client(self, cache_manager):
        """Test scheduled maintenance without GitHub client."""
        results = await cache_manager.schedule_maintenance()
        
        assert "cleanup_results" in results
        assert results["warming_results"] is None
        assert len(results["warnings"]) > 0
        assert "No GitHub client provided" in results["warnings"][0]
    
    async def test_monitoring_metrics_with_maintenance_history(self, cache_manager):
        """Test monitoring metrics after maintenance operations."""
        # Perform cleanup
        await cache_manager.cleanup_cache()
        
        # Perform warming (without GitHub client)
        await cache_manager.warm_cache()
        
        metrics = await cache_manager.get_monitoring_metrics()
        
        assert "last_cleanup" in metrics
        assert "last_warming" in metrics
        assert metrics["last_cleanup"] is not None
        # last_warming should be None since no GitHub client was provided
    
    async def test_error_handling_in_monitoring(self, cache_manager):
        """Test error handling in monitoring metrics."""
        # Close the cache to simulate an error
        await cache_manager.cache.close()
        
        metrics = await cache_manager.get_monitoring_metrics()
        
        assert metrics["health_status"] == "error"
        assert "error" in metrics
    
    async def test_concurrent_warming_operations(self, cache_manager, mock_github_client):
        """Test concurrent warming operations with semaphore."""
        repositories = [f"https://github.com/owner{i}/repo{i}" for i in range(10)]
        config = CacheWarmingConfig(
            repositories=repositories,
            max_concurrent_operations=3,
            batch_size=5
        )
        
        results = await cache_manager.warm_cache(config, mock_github_client)
        
        assert results["repositories_processed"] == len(repositories)
        assert len(results["errors"]) == 0  # Should handle concurrency without errors
    
    async def test_batch_processing_in_warming(self, cache_manager, mock_github_client):
        """Test batch processing in cache warming."""
        repositories = [f"https://github.com/owner{i}/repo{i}" for i in range(7)]
        config = CacheWarmingConfig(repositories=repositories, batch_size=3)
        
        results = await cache_manager.warm_cache(config, mock_github_client)
        
        # Should process all repositories despite batching
        assert results["repositories_processed"] == len(repositories)
    
    async def test_cache_manager_with_default_config(self):
        """Test cache manager with default configuration."""
        manager = CacheManager()
        await manager.initialize()
        
        assert isinstance(manager.config, CacheConfig)
        assert manager.config.database_path == "forklift_cache.db"
        
        await manager.close()
        
        # Cleanup default database file
        Path("forklift_cache.db").unlink(missing_ok=True)