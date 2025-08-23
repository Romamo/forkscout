"""Cache-related data models for the Forklift application."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class CacheEntry(BaseModel):
    """Represents a cache entry in the database."""
    
    key: str = Field(..., description="Unique cache key")
    value: str = Field(..., description="JSON-serialized cached data")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    repository_url: Optional[str] = Field(None, description="Associated repository URL")
    entry_type: str = Field(..., description="Type of cached data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator('key')
    @classmethod
    def validate_key(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Cache key cannot be empty")
        return v
    
    @field_validator('value')
    @classmethod
    def validate_value(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Cache value cannot be empty")
        return v
    
    @field_validator('entry_type')
    @classmethod
    def validate_entry_type(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Entry type cannot be empty")
        return v


class CacheStats(BaseModel):
    """Cache statistics and metrics."""
    
    total_entries: int = Field(0, description="Total number of cache entries")
    total_size_bytes: int = Field(0, description="Total cache size in bytes")
    hit_count: int = Field(0, description="Number of cache hits")
    miss_count: int = Field(0, description="Number of cache misses")
    expired_entries: int = Field(0, description="Number of expired entries")
    entries_by_type: Dict[str, int] = Field(default_factory=dict, description="Entry count by type")
    oldest_entry: Optional[datetime] = Field(None, description="Timestamp of oldest entry")
    newest_entry: Optional[datetime] = Field(None, description="Timestamp of newest entry")


class CacheConfig(BaseModel):
    """Configuration for the cache system."""
    
    database_path: str = Field("forklift_cache.db", description="Path to SQLite database file")
    default_ttl_hours: int = Field(24, description="Default TTL in hours")
    max_cache_size_mb: int = Field(100, description="Maximum cache size in MB")
    cleanup_interval_hours: int = Field(6, description="Cleanup interval in hours")
    enable_compression: bool = Field(True, description="Enable data compression")
    vacuum_threshold: float = Field(0.3, description="Vacuum when fragmentation > threshold")


@dataclass
class CacheKey:
    """Helper class for generating consistent cache keys."""
    
    @staticmethod
    def repository_metadata(owner: str, repo: str) -> str:
        """Generate cache key for repository metadata."""
        return f"repo_meta:{owner}:{repo}"
    
    @staticmethod
    def fork_list(owner: str, repo: str) -> str:
        """Generate cache key for fork list."""
        return f"fork_list:{owner}:{repo}"
    
    @staticmethod
    def fork_analysis(fork_owner: str, fork_repo: str, branch: str = "main") -> str:
        """Generate cache key for fork analysis results."""
        return f"fork_analysis:{fork_owner}:{fork_repo}:{branch}"
    
    @staticmethod
    def commit_list(owner: str, repo: str, branch: str, since: Optional[str] = None) -> str:
        """Generate cache key for commit list."""
        since_part = f":{since}" if since else ""
        return f"commits:{owner}:{repo}:{branch}{since_part}"
    
    @staticmethod
    def feature_ranking(owner: str, repo: str, config_hash: str) -> str:
        """Generate cache key for feature ranking results."""
        return f"ranking:{owner}:{repo}:{config_hash}"