"""Cache management service for advanced cache operations."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from ..models.cache import CacheConfig, CacheStats
from .analysis_cache import AnalysisCacheManager
from .cache import ForkscoutCache

logger = logging.getLogger(__name__)


class CacheWarmingConfig:
    """Configuration for cache warming operations."""

    def __init__(
        self,
        repositories: list[str] | None = None,
        warm_repository_metadata: bool = True,
        warm_fork_lists: bool = True,
        warm_recent_analyses: bool = True,
        max_concurrent_operations: int = 5,
        batch_size: int = 10
    ):
        """Initialize cache warming configuration.
        
        Args:
            repositories: List of repository URLs to warm (None for all)
            warm_repository_metadata: Whether to warm repository metadata
            warm_fork_lists: Whether to warm fork lists
            warm_recent_analyses: Whether to warm recent analysis results
            max_concurrent_operations: Maximum concurrent warming operations
            batch_size: Batch size for warming operations
        """
        self.repositories = repositories or []
        self.warm_repository_metadata = warm_repository_metadata
        self.warm_fork_lists = warm_fork_lists
        self.warm_recent_analyses = warm_recent_analyses
        self.max_concurrent_operations = max_concurrent_operations
        self.batch_size = batch_size


class CacheCleanupConfig:
    """Configuration for cache cleanup operations."""

    def __init__(
        self,
        remove_expired: bool = True,
        remove_old_entries: bool = True,
        max_age_days: int = 30,
        max_cache_size_mb: int = 100,
        vacuum_after_cleanup: bool = True,
        cleanup_batch_size: int = 1000
    ):
        """Initialize cache cleanup configuration.
        
        Args:
            remove_expired: Whether to remove expired entries
            remove_old_entries: Whether to remove old entries
            max_age_days: Maximum age for entries in days
            max_cache_size_mb: Maximum cache size in MB
            vacuum_after_cleanup: Whether to vacuum after cleanup
            cleanup_batch_size: Batch size for cleanup operations
        """
        self.remove_expired = remove_expired
        self.remove_old_entries = remove_old_entries
        self.max_age_days = max_age_days
        self.max_cache_size_mb = max_cache_size_mb
        self.vacuum_after_cleanup = vacuum_after_cleanup
        self.cleanup_batch_size = cleanup_batch_size


class CacheMonitoringMetrics:
    """Cache monitoring metrics and statistics."""

    def __init__(self):
        """Initialize monitoring metrics."""
        self.cache_stats: CacheStats | None = None
        self.performance_metrics: dict[str, Any] = {}
        self.health_status: str = "unknown"
        self.last_cleanup: datetime | None = None
        self.last_warming: datetime | None = None
        self.error_count: int = 0
        self.warning_count: int = 0


class CacheManager:
    """Advanced cache management service with warming, cleanup, and monitoring."""

    def __init__(
        self,
        cache: ForkscoutCache | None = None,
        analysis_cache: AnalysisCacheManager | None = None,
        config: CacheConfig | None = None
    ):
        """Initialize the cache manager.
        
        Args:
            cache: Existing cache instance (creates new if None)
            analysis_cache: Existing analysis cache manager (creates new if None)
            config: Cache configuration (uses defaults if None)
        """
        self.config = config or CacheConfig()
        self.cache = cache or ForkscoutCache(self.config)
        self.analysis_cache = analysis_cache or AnalysisCacheManager(self.cache, self.config)
        self._initialized = False
        self._monitoring_metrics = CacheMonitoringMetrics()
        self._warming_semaphore: asyncio.Semaphore | None = None

    async def initialize(self) -> None:
        """Initialize the cache manager."""
        if not self.cache._initialized:
            await self.cache.initialize()
        if not self.analysis_cache._initialized:
            await self.analysis_cache.initialize()

        self._warming_semaphore = asyncio.Semaphore(5)  # Default concurrent operations
        self._initialized = True
        logger.info("Cache manager initialized")

    async def close(self) -> None:
        """Close the cache manager."""
        await self.analysis_cache.close()
        await self.cache.close()
        self._initialized = False
        logger.info("Cache manager closed")

    def _ensure_initialized(self) -> None:
        """Ensure the cache manager is initialized."""
        if not self._initialized:
            raise RuntimeError("Cache manager not initialized. Call initialize() first.")

    async def warm_cache(
        self,
        warming_config: CacheWarmingConfig | None = None,
        github_client: Any | None = None
    ) -> dict[str, Any]:
        """Warm the cache with frequently accessed data.
        
        Args:
            warming_config: Cache warming configuration
            github_client: GitHub client for fetching data
            
        Returns:
            Dictionary with warming results and statistics
        """
        self._ensure_initialized()

        config = warming_config or CacheWarmingConfig()
        start_time = datetime.utcnow()

        results = {
            "started_at": start_time.isoformat(),
            "repositories_processed": 0,
            "metadata_warmed": 0,
            "fork_lists_warmed": 0,
            "analyses_warmed": 0,
            "errors": [],
            "warnings": []
        }

        if not github_client:
            results["warnings"].append("No GitHub client provided, skipping cache warming")
            results["completed_at"] = datetime.utcnow().isoformat()
            results["duration_seconds"] = (datetime.utcnow() - start_time).total_seconds()
            return results

        # Update semaphore for concurrent operations
        self._warming_semaphore = asyncio.Semaphore(config.max_concurrent_operations)

        try:
            # Get repositories to warm
            repositories_to_warm = await self._get_repositories_to_warm(config)

            # Process repositories in batches
            for i in range(0, len(repositories_to_warm), config.batch_size):
                batch = repositories_to_warm[i:i + config.batch_size]
                batch_results = await self._warm_repository_batch(
                    batch, config, github_client
                )

                # Aggregate results
                results["repositories_processed"] += batch_results["repositories_processed"]
                results["metadata_warmed"] += batch_results["metadata_warmed"]
                results["fork_lists_warmed"] += batch_results["fork_lists_warmed"]
                results["analyses_warmed"] += batch_results["analyses_warmed"]
                results["errors"].extend(batch_results["errors"])
                results["warnings"].extend(batch_results["warnings"])

            self._monitoring_metrics.last_warming = datetime.utcnow()

        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            results["errors"].append(f"Cache warming failed: {e!s}")

        results["completed_at"] = datetime.utcnow().isoformat()
        results["duration_seconds"] = (datetime.utcnow() - start_time).total_seconds()

        logger.info(f"Cache warming completed: {results['repositories_processed']} repositories processed")
        return results

    async def _get_repositories_to_warm(self, config: CacheWarmingConfig) -> list[str]:
        """Get list of repositories to warm.
        
        Args:
            config: Cache warming configuration
            
        Returns:
            List of repository URLs to warm
        """
        if config.repositories:
            return config.repositories

        # Get repositories from existing cache entries
        stats = await self.cache.get_stats()

        # For now, return empty list if no specific repositories provided
        # In a real implementation, this could query the database for repository URLs
        return []

    async def _warm_repository_batch(
        self,
        repositories: list[str],
        config: CacheWarmingConfig,
        github_client: Any
    ) -> dict[str, Any]:
        """Warm a batch of repositories.
        
        Args:
            repositories: List of repository URLs
            config: Cache warming configuration
            github_client: GitHub client for fetching data
            
        Returns:
            Batch warming results
        """
        results = {
            "repositories_processed": 0,
            "metadata_warmed": 0,
            "fork_lists_warmed": 0,
            "analyses_warmed": 0,
            "errors": [],
            "warnings": []
        }

        # Create tasks for concurrent processing
        tasks = []
        for repo_url in repositories:
            task = self._warm_single_repository(repo_url, config, github_client)
            tasks.append(task)

        # Execute tasks concurrently
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        for result in batch_results:
            if isinstance(result, Exception):
                results["errors"].append(str(result))
            else:
                # Only count as processed if there were no errors
                if not result.get("errors"):
                    results["repositories_processed"] += 1
                    if result.get("metadata_warmed"):
                        results["metadata_warmed"] += 1
                    if result.get("fork_list_warmed"):
                        results["fork_lists_warmed"] += 1
                    if result.get("analyses_warmed"):
                        results["analyses_warmed"] += result["analyses_warmed"]
                results["errors"].extend(result.get("errors", []))
                results["warnings"].extend(result.get("warnings", []))

        return results

    async def _warm_single_repository(
        self,
        repo_url: str,
        config: CacheWarmingConfig,
        github_client: Any
    ) -> dict[str, Any]:
        """Warm cache for a single repository.
        
        Args:
            repo_url: Repository URL
            config: Cache warming configuration
            github_client: GitHub client for fetching data
            
        Returns:
            Repository warming results
        """
        async with self._warming_semaphore:
            result = {
                "metadata_warmed": False,
                "fork_list_warmed": False,
                "analyses_warmed": 0,
                "errors": [],
                "warnings": []
            }

            try:
                # Parse repository URL
                parts = repo_url.replace("https://github.com/", "").split("/")
                if len(parts) != 2:
                    result["errors"].append(f"Invalid repository URL: {repo_url}")
                    return result

                owner, repo = parts

                # Warm repository metadata
                if config.warm_repository_metadata:
                    try:
                        # Check if already cached and valid
                        cached_metadata = await self.analysis_cache.get_repository_metadata(owner, repo)
                        if not cached_metadata:
                            # Fetch and cache metadata (placeholder - would use real GitHub client)
                            metadata = {"name": repo, "owner": owner, "warmed": True}
                            await self.analysis_cache.cache_repository_metadata(owner, repo, metadata)
                            result["metadata_warmed"] = True
                    except Exception as e:
                        result["errors"].append(f"Failed to warm metadata for {repo_url}: {e!s}")

                # Warm fork list
                if config.warm_fork_lists:
                    try:
                        cached_forks = await self.analysis_cache.get_fork_list(owner, repo)
                        if not cached_forks:
                            # Fetch and cache fork list (placeholder)
                            forks = [{"name": f"fork-{i}", "owner": f"user-{i}"} for i in range(3)]
                            await self.analysis_cache.cache_fork_list(owner, repo, forks)
                            result["fork_list_warmed"] = True
                    except Exception as e:
                        result["errors"].append(f"Failed to warm fork list for {repo_url}: {e!s}")

                # Warm recent analyses
                if config.warm_recent_analyses:
                    try:
                        # This would typically warm recent fork analyses
                        # For now, just increment the counter
                        result["analyses_warmed"] = 1
                    except Exception as e:
                        result["errors"].append(f"Failed to warm analyses for {repo_url}: {e!s}")

            except Exception as e:
                result["errors"].append(f"Failed to warm repository {repo_url}: {e!s}")

            return result

    async def cleanup_cache(
        self,
        cleanup_config: CacheCleanupConfig | None = None
    ) -> dict[str, Any]:
        """Perform cache cleanup operations.
        
        Args:
            cleanup_config: Cache cleanup configuration
            
        Returns:
            Dictionary with cleanup results and statistics
        """
        self._ensure_initialized()

        config = cleanup_config or CacheCleanupConfig()
        start_time = datetime.utcnow()

        results = {
            "started_at": start_time.isoformat(),
            "expired_entries_removed": 0,
            "old_entries_removed": 0,
            "size_before_mb": 0,
            "size_after_mb": 0,
            "vacuum_performed": False,
            "errors": [],
            "warnings": []
        }

        try:
            # Get initial cache stats
            initial_stats = await self.cache.get_stats()
            results["size_before_mb"] = initial_stats.total_size_bytes / (1024 * 1024)

            # Remove expired entries
            if config.remove_expired:
                try:
                    expired_removed = await self.cache.cleanup_expired()
                    results["expired_entries_removed"] = expired_removed
                    logger.info(f"Removed {expired_removed} expired cache entries")
                except Exception as e:
                    results["errors"].append(f"Failed to remove expired entries: {e!s}")

            # Remove old entries
            if config.remove_old_entries:
                try:
                    old_removed = await self._remove_old_entries(config.max_age_days)
                    results["old_entries_removed"] = old_removed
                    logger.info(f"Removed {old_removed} old cache entries")
                except Exception as e:
                    results["errors"].append(f"Failed to remove old entries: {e!s}")

            # Check cache size and remove entries if needed
            current_stats = await self.cache.get_stats()
            current_size_mb = current_stats.total_size_bytes / (1024 * 1024)

            if current_size_mb > config.max_cache_size_mb:
                try:
                    size_removed = await self._reduce_cache_size(config.max_cache_size_mb)
                    results["warnings"].append(f"Cache size exceeded limit, removed {size_removed} entries")
                except Exception as e:
                    results["errors"].append(f"Failed to reduce cache size: {e!s}")

            # Vacuum database
            if config.vacuum_after_cleanup:
                try:
                    await self.cache.vacuum()
                    results["vacuum_performed"] = True
                    logger.info("Database vacuum completed")
                except Exception as e:
                    results["errors"].append(f"Failed to vacuum database: {e!s}")

            # Get final cache stats
            final_stats = await self.cache.get_stats()
            results["size_after_mb"] = final_stats.total_size_bytes / (1024 * 1024)

            self._monitoring_metrics.last_cleanup = datetime.utcnow()

        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
            results["errors"].append(f"Cache cleanup failed: {e!s}")

        results["completed_at"] = datetime.utcnow().isoformat()
        results["duration_seconds"] = (datetime.utcnow() - start_time).total_seconds()

        logger.info(f"Cache cleanup completed: {results['expired_entries_removed']} expired, {results['old_entries_removed']} old entries removed")
        return results

    async def _remove_old_entries(self, max_age_days: int) -> int:
        """Remove entries older than specified age.
        
        Args:
            max_age_days: Maximum age in days
            
        Returns:
            Number of entries removed
        """
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)

        # This would require a custom query to the database
        # For now, return 0 as a placeholder
        # In a real implementation, this would execute:
        # DELETE FROM cache_entries WHERE created_at < cutoff_date

        return 0

    async def _reduce_cache_size(self, max_size_mb: int) -> int:
        """Reduce cache size by removing oldest entries.
        
        Args:
            max_size_mb: Maximum cache size in MB
            
        Returns:
            Number of entries removed
        """
        # This would require custom logic to remove oldest entries
        # until the cache size is under the limit
        # For now, return 0 as a placeholder

        return 0

    async def get_monitoring_metrics(self) -> dict[str, Any]:
        """Get comprehensive cache monitoring metrics.
        
        Returns:
            Dictionary with monitoring metrics and health status
        """
        self._ensure_initialized()

        try:
            # Get current cache stats
            cache_stats = await self.analysis_cache.get_cache_stats()

            # Calculate health status
            health_status = self._calculate_health_status(cache_stats)

            # Get performance metrics
            performance_metrics = await self._calculate_performance_metrics(cache_stats)

            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "health_status": health_status,
                "cache_stats": cache_stats,
                "performance_metrics": performance_metrics,
                "last_cleanup": self._monitoring_metrics.last_cleanup.isoformat() if self._monitoring_metrics.last_cleanup else None,
                "last_warming": self._monitoring_metrics.last_warming.isoformat() if self._monitoring_metrics.last_warming else None,
                "error_count": self._monitoring_metrics.error_count,
                "warning_count": self._monitoring_metrics.warning_count
            }

            return metrics

        except Exception as e:
            logger.error(f"Failed to get monitoring metrics: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "health_status": "error",
                "error": str(e)
            }

    def _calculate_health_status(self, cache_stats: dict[str, Any]) -> str:
        """Calculate cache health status based on metrics.
        
        Args:
            cache_stats: Cache statistics
            
        Returns:
            Health status string
        """
        try:
            # Check hit rate
            hit_rate = cache_stats.get("hit_rate", 0)

            # Check cache size
            size_mb = cache_stats.get("total_size_bytes", 0) / (1024 * 1024)
            max_size_mb = self.config.max_cache_size_mb

            # Check expired entries
            expired_entries = cache_stats.get("expired_entries", 0)
            total_entries = cache_stats.get("total_entries", 1)
            expired_ratio = expired_entries / total_entries if total_entries > 0 else 0

            # Determine health status
            if hit_rate < 0.3 or size_mb > max_size_mb * 0.9 or expired_ratio > 0.2:
                return "warning"
            elif hit_rate < 0.1 or size_mb > max_size_mb or expired_ratio > 0.5:
                return "critical"
            else:
                return "healthy"

        except Exception:
            return "unknown"

    async def _calculate_performance_metrics(self, cache_stats: dict[str, Any]) -> dict[str, Any]:
        """Calculate performance metrics.
        
        Args:
            cache_stats: Cache statistics
            
        Returns:
            Performance metrics dictionary
        """
        metrics = {}

        try:
            # Hit rate
            metrics["hit_rate"] = cache_stats.get("hit_rate", 0)

            # Cache efficiency
            total_entries = cache_stats.get("total_entries", 0)
            expired_entries = cache_stats.get("expired_entries", 0)
            metrics["cache_efficiency"] = 1 - (expired_entries / total_entries) if total_entries > 0 else 1

            # Size utilization
            size_mb = cache_stats.get("total_size_bytes", 0) / (1024 * 1024)
            max_size_mb = self.config.max_cache_size_mb
            metrics["size_utilization"] = size_mb / max_size_mb if max_size_mb > 0 else 0

            # Entry distribution
            entries_by_type = cache_stats.get("entries_by_type", {})
            metrics["entry_distribution"] = entries_by_type

        except Exception as e:
            logger.warning(f"Failed to calculate some performance metrics: {e}")

        return metrics

    async def schedule_maintenance(
        self,
        warming_config: CacheWarmingConfig | None = None,
        cleanup_config: CacheCleanupConfig | None = None,
        github_client: Any | None = None
    ) -> dict[str, Any]:
        """Schedule and perform cache maintenance operations.
        
        Args:
            warming_config: Cache warming configuration
            cleanup_config: Cache cleanup configuration
            github_client: GitHub client for warming operations
            
        Returns:
            Dictionary with maintenance results
        """
        self._ensure_initialized()

        start_time = datetime.utcnow()
        results = {
            "started_at": start_time.isoformat(),
            "cleanup_results": None,
            "warming_results": None,
            "errors": [],
            "warnings": []
        }

        try:
            # Perform cleanup first
            logger.info("Starting cache cleanup")
            cleanup_results = await self.cleanup_cache(cleanup_config)
            results["cleanup_results"] = cleanup_results

            # Then perform warming
            if github_client:
                logger.info("Starting cache warming")
                warming_results = await self.warm_cache(warming_config, github_client)
                results["warming_results"] = warming_results
            else:
                results["warnings"].append("No GitHub client provided, skipping cache warming")
                results["warming_results"] = None

        except Exception as e:
            logger.error(f"Cache maintenance failed: {e}")
            results["errors"].append(f"Cache maintenance failed: {e!s}")

        results["completed_at"] = datetime.utcnow().isoformat()
        results["duration_seconds"] = (datetime.utcnow() - start_time).total_seconds()

        logger.info("Cache maintenance completed")
        return results

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
