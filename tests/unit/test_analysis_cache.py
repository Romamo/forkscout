"""Tests for the analysis cache manager."""

import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src.forklift.models.cache import CacheConfig
from src.forklift.storage.analysis_cache import AnalysisCacheManager
from src.forklift.storage.cache import ForkliftCache


@pytest.fixture
async def temp_cache_config():
    """Create a temporary cache configuration for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        config = CacheConfig(database_path=tmp.name)
        yield config
        # Cleanup
        Path(tmp.name).unlink(missing_ok=True)


@pytest.fixture
async def analysis_cache_manager(temp_cache_config):
    """Create and initialize an analysis cache manager for testing."""
    manager = AnalysisCacheManager(config=temp_cache_config)
    await manager.initialize()
    yield manager
    await manager.close()


class TestAnalysisCacheManager:
    """Test cases for AnalysisCacheManager class."""
    
    async def test_initialization(self, temp_cache_config):
        """Test cache manager initialization and cleanup."""
        manager = AnalysisCacheManager(config=temp_cache_config)
        
        # Should not be initialized initially
        with pytest.raises(RuntimeError, match="Cache manager not initialized"):
            await manager.get_repository_metadata("owner", "repo")
        
        await manager.initialize()
        
        # Should work after initialization
        result = await manager.get_repository_metadata("owner", "repo")
        assert result is None
        
        await manager.close()
    
    async def test_context_manager(self, temp_cache_config):
        """Test using cache manager as async context manager."""
        async with AnalysisCacheManager(config=temp_cache_config) as manager:
            await manager.cache_repository_metadata("owner", "repo", {"stars": 100})
            result = await manager.get_repository_metadata("owner", "repo")
            assert result == {"stars": 100}
    
    async def test_repository_metadata_caching(self, analysis_cache_manager):
        """Test caching and retrieving repository metadata."""
        metadata = {
            "name": "test-repo",
            "owner": "test-owner",
            "stars": 100,
            "forks": 50,
            "language": "Python"
        }
        
        # Cache metadata
        await analysis_cache_manager.cache_repository_metadata("test-owner", "test-repo", metadata)
        
        # Retrieve metadata
        cached_metadata = await analysis_cache_manager.get_repository_metadata("test-owner", "test-repo")
        assert cached_metadata == metadata
        
        # Non-existent metadata should return None
        result = await analysis_cache_manager.get_repository_metadata("nonexistent", "repo")
        assert result is None
    
    async def test_fork_list_caching(self, analysis_cache_manager):
        """Test caching and retrieving fork lists."""
        forks = [
            {"name": "fork1", "owner": "user1", "stars": 10},
            {"name": "fork2", "owner": "user2", "stars": 5},
            {"name": "fork3", "owner": "user3", "stars": 15}
        ]
        
        # Cache fork list
        await analysis_cache_manager.cache_fork_list("owner", "repo", forks)
        
        # Retrieve fork list
        cached_forks = await analysis_cache_manager.get_fork_list("owner", "repo")
        assert cached_forks == forks
        
        # Non-existent fork list should return None
        result = await analysis_cache_manager.get_fork_list("nonexistent", "repo")
        assert result is None
    
    async def test_fork_analysis_caching(self, analysis_cache_manager):
        """Test caching and retrieving fork analysis results."""
        analysis = {
            "features": [
                {"id": "feat1", "score": 85, "description": "Feature 1"},
                {"id": "feat2", "score": 92, "description": "Feature 2"}
            ],
            "commits": [
                {"sha": "abc123", "message": "Add feature 1"},
                {"sha": "def456", "message": "Add feature 2"}
            ],
            "metrics": {"total_commits": 2, "total_features": 2}
        }
        
        # Cache analysis
        await analysis_cache_manager.cache_fork_analysis(
            "fork-owner", 
            "fork-repo", 
            analysis,
            branch="feature-branch",
            parent_repository_url="https://github.com/parent/repo"
        )
        
        # Retrieve analysis
        cached_analysis = await analysis_cache_manager.get_fork_analysis(
            "fork-owner", 
            "fork-repo", 
            "feature-branch"
        )
        assert cached_analysis == analysis
        
        # Default branch should work
        await analysis_cache_manager.cache_fork_analysis("fork-owner", "fork-repo", analysis)
        cached_analysis = await analysis_cache_manager.get_fork_analysis("fork-owner", "fork-repo")
        assert cached_analysis == analysis
    
    async def test_commit_list_caching(self, analysis_cache_manager):
        """Test caching and retrieving commit lists."""
        commits = [
            {"sha": "abc123", "message": "First commit", "author": "user1"},
            {"sha": "def456", "message": "Second commit", "author": "user2"},
            {"sha": "ghi789", "message": "Third commit", "author": "user1"}
        ]
        
        # Cache commit list
        await analysis_cache_manager.cache_commit_list("owner", "repo", "main", commits)
        
        # Retrieve commit list
        cached_commits = await analysis_cache_manager.get_commit_list("owner", "repo", "main")
        assert cached_commits == commits
        
        # Cache with since parameter
        since = "2024-01-01T00:00:00Z"
        await analysis_cache_manager.cache_commit_list("owner", "repo", "main", commits, since=since)
        cached_commits = await analysis_cache_manager.get_commit_list("owner", "repo", "main", since=since)
        assert cached_commits == commits
    
    async def test_feature_ranking_caching(self, analysis_cache_manager):
        """Test caching and retrieving feature ranking results."""
        config = {
            "code_quality_weight": 0.3,
            "community_engagement_weight": 0.2,
            "test_coverage_weight": 0.2,
            "documentation_weight": 0.15,
            "recency_weight": 0.15
        }
        
        ranking = {
            "features": [
                {"id": "feat1", "score": 95, "rank": 1},
                {"id": "feat2", "score": 88, "rank": 2},
                {"id": "feat3", "score": 82, "rank": 3}
            ],
            "top_features": [
                {"id": "feat1", "score": 95, "rank": 1}
            ],
            "total_analyzed": 10
        }
        
        # Cache ranking
        await analysis_cache_manager.cache_feature_ranking("owner", "repo", config, ranking)
        
        # Retrieve ranking
        cached_ranking = await analysis_cache_manager.get_feature_ranking("owner", "repo", config)
        assert cached_ranking == ranking
        
        # Different config should return None
        different_config = {**config, "code_quality_weight": 0.4}
        result = await analysis_cache_manager.get_feature_ranking("owner", "repo", different_config)
        assert result is None
    
    async def test_config_hash_generation(self, analysis_cache_manager):
        """Test configuration hash generation for consistent caching."""
        config1 = {"a": 1, "b": 2, "c": 3}
        config2 = {"c": 3, "a": 1, "b": 2}  # Same values, different order
        config3 = {"a": 1, "b": 2, "c": 4}  # Different values
        
        hash1 = analysis_cache_manager._generate_config_hash(config1)
        hash2 = analysis_cache_manager._generate_config_hash(config2)
        hash3 = analysis_cache_manager._generate_config_hash(config3)
        
        # Same configs should produce same hash regardless of order
        assert hash1 == hash2
        
        # Different configs should produce different hashes
        assert hash1 != hash3
        
        # Hash should be consistent
        assert len(hash1) == 8  # MD5 truncated to 8 chars
    
    async def test_invalidate_repository_cache(self, analysis_cache_manager):
        """Test invalidating repository cache entries."""
        # Cache various types of data for a repository
        await analysis_cache_manager.cache_repository_metadata("owner", "repo", {"stars": 100})
        await analysis_cache_manager.cache_fork_list("owner", "repo", [{"name": "fork1"}])
        await analysis_cache_manager.cache_commit_list("owner", "repo", "main", [{"sha": "abc123"}])
        
        # Cache data for different repository
        await analysis_cache_manager.cache_repository_metadata("other", "repo", {"stars": 50})
        
        # Invalidate cache for first repository
        invalidated = await analysis_cache_manager.invalidate_repository_cache("owner", "repo")
        assert invalidated == 3
        
        # First repository data should be gone
        assert await analysis_cache_manager.get_repository_metadata("owner", "repo") is None
        assert await analysis_cache_manager.get_fork_list("owner", "repo") is None
        assert await analysis_cache_manager.get_commit_list("owner", "repo", "main") is None
        
        # Other repository data should remain
        assert await analysis_cache_manager.get_repository_metadata("other", "repo") is not None
    
    async def test_is_repository_cache_valid(self, analysis_cache_manager):
        """Test checking repository cache validity."""
        # Cache some data
        await analysis_cache_manager.cache_repository_metadata("owner", "repo", {"stars": 100})
        
        # Should be valid without activity check
        is_valid = await analysis_cache_manager.is_repository_cache_valid(
            "owner", "repo", "repository_metadata"
        )
        assert is_valid is True
        
        # Should be valid with old activity
        old_activity = datetime.utcnow() - timedelta(hours=2)
        is_valid = await analysis_cache_manager.is_repository_cache_valid(
            "owner", "repo", "repository_metadata", old_activity
        )
        assert is_valid is True
        
        # Should be invalid with recent activity
        recent_activity = datetime.utcnow() + timedelta(minutes=1)
        is_valid = await analysis_cache_manager.is_repository_cache_valid(
            "owner", "repo", "repository_metadata", recent_activity
        )
        assert is_valid is False
        
        # Should handle different cache types
        await analysis_cache_manager.cache_fork_analysis("owner", "repo", {"features": []}, "main")
        is_valid = await analysis_cache_manager.is_repository_cache_valid(
            "owner", "repo", "fork_analysis", branch="main"
        )
        assert is_valid is True
        
        # Should raise error for unknown cache type
        with pytest.raises(ValueError, match="Unknown cache type"):
            await analysis_cache_manager.is_repository_cache_valid(
                "owner", "repo", "unknown_type"
            )
    
    async def test_get_cache_stats(self, analysis_cache_manager):
        """Test getting cache statistics."""
        # Add some test data
        await analysis_cache_manager.cache_repository_metadata("owner1", "repo1", {"stars": 100})
        await analysis_cache_manager.cache_fork_list("owner1", "repo1", [{"name": "fork1"}])
        await analysis_cache_manager.cache_fork_analysis("owner2", "repo2", {"features": []})
        
        # Trigger some cache hits and misses
        await analysis_cache_manager.get_repository_metadata("owner1", "repo1")  # hit
        await analysis_cache_manager.get_repository_metadata("nonexistent", "repo")  # miss
        
        stats = await analysis_cache_manager.get_cache_stats()
        
        assert isinstance(stats, dict)
        assert stats["total_entries"] == 3
        assert stats["hit_count"] >= 1
        assert stats["miss_count"] >= 1
        assert "hit_rate" in stats
        assert 0 <= stats["hit_rate"] <= 1
        assert "entries_by_type" in stats
        assert stats["entries_by_type"]["repo_metadata"] == 1
        assert stats["entries_by_type"]["fork_list"] == 1
        assert stats["entries_by_type"]["fork_analysis"] == 1
    
    async def test_cleanup_expired_entries(self, analysis_cache_manager):
        """Test cleaning up expired cache entries."""
        # Cache some data with short TTL
        await analysis_cache_manager.cache_repository_metadata(
            "owner", "repo", {"stars": 100}, ttl_hours=-1  # Already expired
        )
        await analysis_cache_manager.cache_fork_list(
            "owner", "repo", [{"name": "fork1"}], ttl_hours=24  # Valid
        )
        
        # Cleanup expired entries
        cleaned = await analysis_cache_manager.cleanup_expired_entries()
        assert cleaned == 1
        
        # Expired entry should be gone, valid entry should remain
        assert await analysis_cache_manager.get_repository_metadata("owner", "repo") is None
        assert await analysis_cache_manager.get_fork_list("owner", "repo") is not None
    
    async def test_with_existing_cache_instance(self, temp_cache_config):
        """Test using an existing cache instance."""
        # Create cache instance
        cache = ForkliftCache(temp_cache_config)
        await cache.initialize()
        
        # Create manager with existing cache
        manager = AnalysisCacheManager(cache=cache)
        await manager.initialize()
        
        # Should work normally
        await manager.cache_repository_metadata("owner", "repo", {"stars": 100})
        result = await manager.get_repository_metadata("owner", "repo")
        assert result == {"stars": 100}
        
        await manager.close()
        await cache.close()