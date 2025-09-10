"""Data access layer for cached fork analysis results."""

import hashlib
import logging
from datetime import datetime
from typing import Any

from ..models.cache import CacheConfig, CacheKey
from .cache import ForkscoutCache

logger = logging.getLogger(__name__)


class AnalysisCacheManager:
    """High-level cache manager for fork analysis results."""

    def __init__(self, cache: ForkscoutCache | None = None, config: CacheConfig | None = None):
        """Initialize the analysis cache manager.
        
        Args:
            cache: Existing cache instance (creates new if None)
            config: Cache configuration (uses defaults if None)
        """
        self.cache = cache or ForkscoutCache(config)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the cache manager."""
        if not self.cache._initialized:
            await self.cache.initialize()
        self._initialized = True
        logger.info("Analysis cache manager initialized")

    async def close(self) -> None:
        """Close the cache manager."""
        await self.cache.close()
        self._initialized = False
        logger.info("Analysis cache manager closed")

    def _ensure_initialized(self) -> None:
        """Ensure the cache manager is initialized."""
        if not self._initialized:
            raise RuntimeError("Cache manager not initialized. Call initialize() first.")

    def _generate_config_hash(self, config: dict[str, Any]) -> str:
        """Generate a hash for configuration to use in cache keys.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Hash string for the configuration
        """
        config_str = str(sorted(config.items()))
        return hashlib.md5(config_str.encode()).hexdigest()[:8]

    async def get_repository_metadata(self, owner: str, repo: str) -> dict[str, Any] | None:
        """Get cached repository metadata.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Repository metadata or None if not cached
        """
        self._ensure_initialized()

        key = CacheKey.repository_metadata(owner, repo)
        return await self.cache.get_json(key)

    async def cache_repository_metadata(
        self,
        owner: str,
        repo: str,
        metadata: dict[str, Any],
        ttl_hours: int | None = None
    ) -> None:
        """Cache repository metadata.
        
        Args:
            owner: Repository owner
            repo: Repository name
            metadata: Repository metadata to cache
            ttl_hours: Time to live in hours
        """
        self._ensure_initialized()

        key = CacheKey.repository_metadata(owner, repo)
        repository_url = f"https://github.com/{owner}/{repo}"

        await self.cache.set_json(
            key=key,
            value=metadata,
            entry_type="repo_metadata",
            ttl_hours=ttl_hours,
            repository_url=repository_url,
            metadata={"owner": owner, "repo": repo}
        )

        logger.debug(f"Cached repository metadata for {owner}/{repo}")

    async def get_fork_list(self, owner: str, repo: str) -> list[dict[str, Any]] | None:
        """Get cached fork list.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            List of forks or None if not cached
        """
        self._ensure_initialized()

        key = CacheKey.fork_list(owner, repo)
        return await self.cache.get_json(key)

    async def cache_fork_list(
        self,
        owner: str,
        repo: str,
        forks: list[dict[str, Any]],
        ttl_hours: int | None = None
    ) -> None:
        """Cache fork list.
        
        Args:
            owner: Repository owner
            repo: Repository name
            forks: List of forks to cache
            ttl_hours: Time to live in hours
        """
        self._ensure_initialized()

        key = CacheKey.fork_list(owner, repo)
        repository_url = f"https://github.com/{owner}/{repo}"

        await self.cache.set_json(
            key=key,
            value=forks,
            entry_type="fork_list",
            ttl_hours=ttl_hours,
            repository_url=repository_url,
            metadata={"owner": owner, "repo": repo, "fork_count": len(forks)}
        )

        logger.debug(f"Cached {len(forks)} forks for {owner}/{repo}")

    async def get_fork_analysis(
        self,
        fork_owner: str,
        fork_repo: str,
        branch: str = "main"
    ) -> dict[str, Any] | None:
        """Get cached fork analysis results.
        
        Args:
            fork_owner: Fork owner
            fork_repo: Fork repository name
            branch: Branch name
            
        Returns:
            Fork analysis results or None if not cached
        """
        self._ensure_initialized()

        key = CacheKey.fork_analysis(fork_owner, fork_repo, branch)
        return await self.cache.get_json(key)

    async def cache_fork_analysis(
        self,
        fork_owner: str,
        fork_repo: str,
        analysis: dict[str, Any],
        branch: str = "main",
        parent_repository_url: str | None = None,
        ttl_hours: int | None = None
    ) -> None:
        """Cache fork analysis results.
        
        Args:
            fork_owner: Fork owner
            fork_repo: Fork repository name
            analysis: Analysis results to cache
            branch: Branch name
            parent_repository_url: URL of the parent repository
            ttl_hours: Time to live in hours
        """
        self._ensure_initialized()

        key = CacheKey.fork_analysis(fork_owner, fork_repo, branch)
        fork_url = f"https://github.com/{fork_owner}/{fork_repo}"

        metadata = {
            "fork_owner": fork_owner,
            "fork_repo": fork_repo,
            "branch": branch,
            "parent_repository_url": parent_repository_url
        }

        # Add analysis summary to metadata
        if "features" in analysis:
            metadata["feature_count"] = len(analysis["features"])
        if "commits" in analysis:
            metadata["commit_count"] = len(analysis["commits"])

        await self.cache.set_json(
            key=key,
            value=analysis,
            entry_type="fork_analysis",
            ttl_hours=ttl_hours,
            repository_url=parent_repository_url or fork_url,
            metadata=metadata
        )

        logger.debug(f"Cached fork analysis for {fork_owner}/{fork_repo}:{branch}")

    async def get_commit_list(
        self,
        owner: str,
        repo: str,
        branch: str,
        since: str | None = None
    ) -> list[dict[str, Any]] | None:
        """Get cached commit list.
        
        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name
            since: Since timestamp (ISO format)
            
        Returns:
            List of commits or None if not cached
        """
        self._ensure_initialized()

        key = CacheKey.commit_list(owner, repo, branch, since)
        return await self.cache.get_json(key)

    async def cache_commit_list(
        self,
        owner: str,
        repo: str,
        branch: str,
        commits: list[dict[str, Any]],
        since: str | None = None,
        ttl_hours: int | None = None
    ) -> None:
        """Cache commit list.
        
        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name
            commits: List of commits to cache
            since: Since timestamp (ISO format)
            ttl_hours: Time to live in hours
        """
        self._ensure_initialized()

        key = CacheKey.commit_list(owner, repo, branch, since)
        repository_url = f"https://github.com/{owner}/{repo}"

        await self.cache.set_json(
            key=key,
            value=commits,
            entry_type="commit_list",
            ttl_hours=ttl_hours,
            repository_url=repository_url,
            metadata={
                "owner": owner,
                "repo": repo,
                "branch": branch,
                "since": since,
                "commit_count": len(commits)
            }
        )

        logger.debug(f"Cached {len(commits)} commits for {owner}/{repo}:{branch}")

    async def get_feature_ranking(
        self,
        owner: str,
        repo: str,
        config: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Get cached feature ranking results.
        
        Args:
            owner: Repository owner
            repo: Repository name
            config: Ranking configuration
            
        Returns:
            Feature ranking results or None if not cached
        """
        self._ensure_initialized()

        config_hash = self._generate_config_hash(config)
        key = CacheKey.feature_ranking(owner, repo, config_hash)
        return await self.cache.get_json(key)

    async def cache_feature_ranking(
        self,
        owner: str,
        repo: str,
        config: dict[str, Any],
        ranking: dict[str, Any],
        ttl_hours: int | None = None
    ) -> None:
        """Cache feature ranking results.
        
        Args:
            owner: Repository owner
            repo: Repository name
            config: Ranking configuration
            ranking: Ranking results to cache
            ttl_hours: Time to live in hours
        """
        self._ensure_initialized()

        config_hash = self._generate_config_hash(config)
        key = CacheKey.feature_ranking(owner, repo, config_hash)
        repository_url = f"https://github.com/{owner}/{repo}"

        metadata = {
            "owner": owner,
            "repo": repo,
            "config_hash": config_hash
        }

        # Add ranking summary to metadata
        if "features" in ranking:
            metadata["feature_count"] = len(ranking["features"])
        if "top_features" in ranking:
            metadata["top_feature_count"] = len(ranking["top_features"])

        await self.cache.set_json(
            key=key,
            value=ranking,
            entry_type="feature_ranking",
            ttl_hours=ttl_hours,
            repository_url=repository_url,
            metadata=metadata
        )

        logger.debug(f"Cached feature ranking for {owner}/{repo} (config: {config_hash})")

    async def invalidate_repository_cache(
        self,
        owner: str,
        repo: str,
        last_activity: datetime | None = None
    ) -> int:
        """Invalidate all cache entries for a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            last_activity: Last activity timestamp (if None, invalidates all)
            
        Returns:
            Number of entries invalidated
        """
        self._ensure_initialized()

        repository_url = f"https://github.com/{owner}/{repo}"
        return await self.cache.invalidate_repository_cache(repository_url, last_activity)

    async def is_repository_cache_valid(
        self,
        owner: str,
        repo: str,
        cache_type: str,
        repository_last_activity: datetime | None = None,
        **kwargs
    ) -> bool:
        """Check if repository cache is still valid.
        
        Args:
            owner: Repository owner
            repo: Repository name
            cache_type: Type of cache to check
            repository_last_activity: Last activity timestamp of the repository
            **kwargs: Additional parameters for cache key generation
            
        Returns:
            True if cache is valid, False otherwise
        """
        self._ensure_initialized()

        # Generate appropriate cache key based on type
        if cache_type == "repository_metadata":
            key = CacheKey.repository_metadata(owner, repo)
        elif cache_type == "fork_list":
            key = CacheKey.fork_list(owner, repo)
        elif cache_type == "fork_analysis":
            branch = kwargs.get("branch", "main")
            key = CacheKey.fork_analysis(owner, repo, branch)
        elif cache_type == "commit_list":
            branch = kwargs.get("branch", "main")
            since = kwargs.get("since")
            key = CacheKey.commit_list(owner, repo, branch, since)
        elif cache_type == "feature_ranking":
            config = kwargs.get("config", {})
            config_hash = self._generate_config_hash(config)
            key = CacheKey.feature_ranking(owner, repo, config_hash)
        else:
            raise ValueError(f"Unknown cache type: {cache_type}")

        return await self.cache.is_cache_valid(key, repository_last_activity)

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics with analysis-specific metrics.
        
        Returns:
            Cache statistics dictionary
        """
        self._ensure_initialized()

        stats = await self.cache.get_stats()

        # Convert to dictionary and add analysis-specific information
        stats_dict = {
            "total_entries": stats.total_entries,
            "total_size_bytes": stats.total_size_bytes,
            "hit_count": stats.hit_count,
            "miss_count": stats.miss_count,
            "expired_entries": stats.expired_entries,
            "entries_by_type": stats.entries_by_type,
            "oldest_entry": stats.oldest_entry.isoformat() if stats.oldest_entry else None,
            "newest_entry": stats.newest_entry.isoformat() if stats.newest_entry else None,
        }

        # Calculate hit rate
        total_requests = stats.hit_count + stats.miss_count
        if total_requests > 0:
            stats_dict["hit_rate"] = stats.hit_count / total_requests
        else:
            stats_dict["hit_rate"] = 0.0

        return stats_dict

    async def cleanup_expired_entries(self) -> int:
        """Clean up expired cache entries.
        
        Returns:
            Number of entries cleaned up
        """
        self._ensure_initialized()
        return await self.cache.cleanup_expired()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
