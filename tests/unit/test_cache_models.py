"""Tests for cache-related data models."""

import pytest
from datetime import datetime, timedelta
from src.forklift.models.cache import CacheEntry, CacheStats, CacheConfig, CacheKey


class TestCacheEntry:
    """Test cases for CacheEntry model."""
    
    def test_cache_entry_creation(self):
        """Test creating a cache entry with required fields."""
        entry = CacheEntry(
            key="test_key",
            value='{"data": "test"}',
            entry_type="test"
        )
        
        assert entry.key == "test_key"
        assert entry.value == '{"data": "test"}'
        assert entry.entry_type == "test"
        assert isinstance(entry.created_at, datetime)
        assert entry.expires_at is None
        assert entry.repository_url is None
        assert entry.metadata == {}
    
    def test_cache_entry_with_expiration(self):
        """Test creating a cache entry with expiration."""
        expires_at = datetime.utcnow() + timedelta(hours=24)
        entry = CacheEntry(
            key="test_key",
            value='{"data": "test"}',
            entry_type="test",
            expires_at=expires_at
        )
        
        assert entry.expires_at == expires_at
    
    def test_cache_entry_with_metadata(self):
        """Test creating a cache entry with metadata."""
        metadata = {"version": "1.0", "source": "github"}
        entry = CacheEntry(
            key="test_key",
            value='{"data": "test"}',
            entry_type="test",
            metadata=metadata
        )
        
        assert entry.metadata == metadata
    
    def test_cache_entry_validation(self):
        """Test cache entry validation."""
        with pytest.raises(ValueError):
            CacheEntry(key="", value="test", entry_type="test")
        
        with pytest.raises(ValueError):
            CacheEntry(key="test", value="", entry_type="test")
        
        with pytest.raises(ValueError):
            CacheEntry(key="test", value="test", entry_type="")


class TestCacheStats:
    """Test cases for CacheStats model."""
    
    def test_cache_stats_defaults(self):
        """Test cache stats with default values."""
        stats = CacheStats()
        
        assert stats.total_entries == 0
        assert stats.total_size_bytes == 0
        assert stats.hit_count == 0
        assert stats.miss_count == 0
        assert stats.expired_entries == 0
        assert stats.entries_by_type == {}
        assert stats.oldest_entry is None
        assert stats.newest_entry is None
    
    def test_cache_stats_with_values(self):
        """Test cache stats with specific values."""
        oldest = datetime.utcnow() - timedelta(days=1)
        newest = datetime.utcnow()
        entries_by_type = {"repo_meta": 10, "fork_list": 5}
        
        stats = CacheStats(
            total_entries=15,
            total_size_bytes=1024,
            hit_count=100,
            miss_count=20,
            expired_entries=2,
            entries_by_type=entries_by_type,
            oldest_entry=oldest,
            newest_entry=newest
        )
        
        assert stats.total_entries == 15
        assert stats.total_size_bytes == 1024
        assert stats.hit_count == 100
        assert stats.miss_count == 20
        assert stats.expired_entries == 2
        assert stats.entries_by_type == entries_by_type
        assert stats.oldest_entry == oldest
        assert stats.newest_entry == newest


class TestCacheConfig:
    """Test cases for CacheConfig model."""
    
    def test_cache_config_defaults(self):
        """Test cache config with default values."""
        config = CacheConfig()
        
        assert config.database_path == "forklift_cache.db"
        assert config.default_ttl_hours == 24
        assert config.max_cache_size_mb == 100
        assert config.cleanup_interval_hours == 6
        assert config.enable_compression is True
        assert config.vacuum_threshold == 0.3
    
    def test_cache_config_custom_values(self):
        """Test cache config with custom values."""
        config = CacheConfig(
            database_path="/tmp/test_cache.db",
            default_ttl_hours=48,
            max_cache_size_mb=200,
            cleanup_interval_hours=12,
            enable_compression=False,
            vacuum_threshold=0.5
        )
        
        assert config.database_path == "/tmp/test_cache.db"
        assert config.default_ttl_hours == 48
        assert config.max_cache_size_mb == 200
        assert config.cleanup_interval_hours == 12
        assert config.enable_compression is False
        assert config.vacuum_threshold == 0.5


class TestCacheKey:
    """Test cases for CacheKey helper class."""
    
    def test_repository_metadata_key(self):
        """Test repository metadata cache key generation."""
        key = CacheKey.repository_metadata("owner", "repo")
        assert key == "repo_meta:owner:repo"
    
    def test_fork_list_key(self):
        """Test fork list cache key generation."""
        key = CacheKey.fork_list("owner", "repo")
        assert key == "fork_list:owner:repo"
    
    def test_fork_analysis_key_default_branch(self):
        """Test fork analysis cache key with default branch."""
        key = CacheKey.fork_analysis("fork_owner", "fork_repo")
        assert key == "fork_analysis:fork_owner:fork_repo:main"
    
    def test_fork_analysis_key_custom_branch(self):
        """Test fork analysis cache key with custom branch."""
        key = CacheKey.fork_analysis("fork_owner", "fork_repo", "feature-branch")
        assert key == "fork_analysis:fork_owner:fork_repo:feature-branch"
    
    def test_commit_list_key_no_since(self):
        """Test commit list cache key without since parameter."""
        key = CacheKey.commit_list("owner", "repo", "main")
        assert key == "commits:owner:repo:main"
    
    def test_commit_list_key_with_since(self):
        """Test commit list cache key with since parameter."""
        key = CacheKey.commit_list("owner", "repo", "main", "2024-01-01")
        assert key == "commits:owner:repo:main:2024-01-01"
    
    def test_feature_ranking_key(self):
        """Test feature ranking cache key generation."""
        key = CacheKey.feature_ranking("owner", "repo", "config_hash_123")
        assert key == "ranking:owner:repo:config_hash_123"