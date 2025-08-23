"""SQLite-based caching system for the Forklift application."""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiosqlite

from ..models.cache import CacheConfig, CacheEntry, CacheStats, CacheKey


logger = logging.getLogger(__name__)


class CacheDatabase:
    """SQLite-based cache database manager."""
    
    def __init__(self, config: CacheConfig):
        """Initialize the cache database.
        
        Args:
            config: Cache configuration settings
        """
        self.config = config
        self.db_path = Path(config.database_path)
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def initialize(self) -> None:
        """Initialize the database and create tables if they don't exist."""
        self._connection = await aiosqlite.connect(str(self.db_path))
        await self._create_tables()
        await self._create_indexes()
        logger.info(f"Cache database initialized at {self.db_path}")
    
    async def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Cache database connection closed")
    
    async def _create_tables(self) -> None:
        """Create the cache tables if they don't exist."""
        create_cache_table = """
        CREATE TABLE IF NOT EXISTS cache_entries (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            expires_at TIMESTAMP,
            repository_url TEXT,
            entry_type TEXT NOT NULL,
            metadata TEXT,
            size_bytes INTEGER NOT NULL DEFAULT 0
        )
        """
        
        create_stats_table = """
        CREATE TABLE IF NOT EXISTS cache_stats (
            id INTEGER PRIMARY KEY,
            hit_count INTEGER NOT NULL DEFAULT 0,
            miss_count INTEGER NOT NULL DEFAULT 0,
            last_cleanup TIMESTAMP,
            last_vacuum TIMESTAMP
        )
        """
        
        await self._connection.execute(create_cache_table)
        await self._connection.execute(create_stats_table)
        await self._connection.commit()
    
    async def _create_indexes(self) -> None:
        """Create database indexes for better performance."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_entries(expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_entry_type ON cache_entries(entry_type)",
            "CREATE INDEX IF NOT EXISTS idx_repository_url ON cache_entries(repository_url)",
            "CREATE INDEX IF NOT EXISTS idx_created_at ON cache_entries(created_at)",
        ]
        
        for index_sql in indexes:
            await self._connection.execute(index_sql)
        await self._connection.commit()
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Retrieve a cache entry by key.
        
        Args:
            key: The cache key to retrieve
            
        Returns:
            The cache entry if found and not expired, None otherwise
        """
        if not self._connection:
            raise RuntimeError("Database not initialized")
        
        query = """
        SELECT key, value, created_at, expires_at, repository_url, entry_type, metadata
        FROM cache_entries 
        WHERE key = ?
        """
        
        async with self._connection.execute(query, (key,)) as cursor:
            row = await cursor.fetchone()
            
            if not row:
                await self._increment_miss_count()
                return None
            
            entry = CacheEntry(
                key=row[0],
                value=row[1],
                created_at=datetime.fromisoformat(row[2]),
                expires_at=datetime.fromisoformat(row[3]) if row[3] else None,
                repository_url=row[4],
                entry_type=row[5],
                metadata=json.loads(row[6]) if row[6] else {}
            )
            
            # Check if entry is expired
            if entry.expires_at and entry.expires_at <= datetime.utcnow():
                await self.delete(key)
                await self._increment_miss_count()
                return None
            
            await self._increment_hit_count()
            return entry
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        entry_type: str,
        ttl_hours: Optional[int] = None,
        repository_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store a cache entry.
        
        Args:
            key: The cache key
            value: The value to cache (will be JSON serialized)
            entry_type: Type of the cached data
            ttl_hours: Time to live in hours (uses default if None)
            repository_url: Associated repository URL
            metadata: Additional metadata
        """
        if not self._connection:
            raise RuntimeError("Database not initialized")
        
        # Serialize the value
        serialized_value = json.dumps(value, default=str)
        size_bytes = len(serialized_value.encode('utf-8'))
        
        # Calculate expiration
        ttl = ttl_hours or self.config.default_ttl_hours
        expires_at = datetime.utcnow() + timedelta(hours=ttl)
        
        # Prepare metadata
        metadata_json = json.dumps(metadata) if metadata else None
        
        query = """
        INSERT OR REPLACE INTO cache_entries 
        (key, value, created_at, expires_at, repository_url, entry_type, metadata, size_bytes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        await self._connection.execute(query, (
            key,
            serialized_value,
            datetime.utcnow().isoformat(),
            expires_at.isoformat(),
            repository_url,
            entry_type,
            metadata_json,
            size_bytes
        ))
        await self._connection.commit()
        
        logger.debug(f"Cached entry with key: {key}, type: {entry_type}, size: {size_bytes} bytes")
    
    async def delete(self, key: str) -> bool:
        """Delete a cache entry by key.
        
        Args:
            key: The cache key to delete
            
        Returns:
            True if the entry was deleted, False if it didn't exist
        """
        if not self._connection:
            raise RuntimeError("Database not initialized")
        
        query = "DELETE FROM cache_entries WHERE key = ?"
        cursor = await self._connection.execute(query, (key,))
        await self._connection.commit()
        
        deleted = cursor.rowcount > 0
        if deleted:
            logger.debug(f"Deleted cache entry with key: {key}")
        
        return deleted
    
    async def clear(self, entry_type: Optional[str] = None, repository_url: Optional[str] = None) -> int:
        """Clear cache entries based on filters.
        
        Args:
            entry_type: Clear only entries of this type
            repository_url: Clear only entries for this repository
            
        Returns:
            Number of entries cleared
        """
        if not self._connection:
            raise RuntimeError("Database not initialized")
        
        conditions = []
        params = []
        
        if entry_type:
            conditions.append("entry_type = ?")
            params.append(entry_type)
        
        if repository_url:
            conditions.append("repository_url = ?")
            params.append(repository_url)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        query = f"DELETE FROM cache_entries{where_clause}"
        
        cursor = await self._connection.execute(query, params)
        await self._connection.commit()
        
        cleared_count = cursor.rowcount
        logger.info(f"Cleared {cleared_count} cache entries")
        
        return cleared_count
    
    async def cleanup_expired(self) -> int:
        """Remove expired cache entries.
        
        Returns:
            Number of expired entries removed
        """
        if not self._connection:
            raise RuntimeError("Database not initialized")
        
        query = "DELETE FROM cache_entries WHERE expires_at <= ?"
        cursor = await self._connection.execute(query, (datetime.utcnow().isoformat(),))
        await self._connection.commit()
        
        expired_count = cursor.rowcount
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired cache entries")
        
        # Update cleanup timestamp
        await self._update_cleanup_timestamp()
        
        return expired_count
    
    async def get_stats(self) -> CacheStats:
        """Get cache statistics.
        
        Returns:
            Cache statistics object
        """
        if not self._connection:
            raise RuntimeError("Database not initialized")
        
        # Get basic stats
        stats_query = """
        SELECT 
            COUNT(*) as total_entries,
            SUM(size_bytes) as total_size_bytes,
            MIN(created_at) as oldest_entry,
            MAX(created_at) as newest_entry,
            COUNT(CASE WHEN expires_at <= ? THEN 1 END) as expired_entries
        FROM cache_entries
        """
        
        async with self._connection.execute(stats_query, (datetime.utcnow().isoformat(),)) as cursor:
            row = await cursor.fetchone()
            total_entries, total_size_bytes, oldest_entry, newest_entry, expired_entries = row
        
        # Get entries by type
        type_query = "SELECT entry_type, COUNT(*) FROM cache_entries GROUP BY entry_type"
        entries_by_type = {}
        async with self._connection.execute(type_query) as cursor:
            async for row in cursor:
                entries_by_type[row[0]] = row[1]
        
        # Get hit/miss counts
        hit_miss_query = "SELECT hit_count, miss_count FROM cache_stats WHERE id = 1"
        hit_count = miss_count = 0
        async with self._connection.execute(hit_miss_query) as cursor:
            row = await cursor.fetchone()
            if row:
                hit_count, miss_count = row
        
        return CacheStats(
            total_entries=total_entries or 0,
            total_size_bytes=total_size_bytes or 0,
            hit_count=hit_count,
            miss_count=miss_count,
            expired_entries=expired_entries or 0,
            entries_by_type=entries_by_type,
            oldest_entry=datetime.fromisoformat(oldest_entry) if oldest_entry else None,
            newest_entry=datetime.fromisoformat(newest_entry) if newest_entry else None
        )
    
    async def vacuum(self) -> None:
        """Vacuum the database to reclaim space and optimize performance."""
        if not self._connection:
            raise RuntimeError("Database not initialized")
        
        await self._connection.execute("VACUUM")
        await self._update_vacuum_timestamp()
        logger.info("Database vacuum completed")
    
    async def _increment_hit_count(self) -> None:
        """Increment the cache hit count."""
        await self._connection.execute(
            "INSERT OR IGNORE INTO cache_stats (id, hit_count, miss_count) VALUES (1, 0, 0)"
        )
        await self._connection.execute(
            "UPDATE cache_stats SET hit_count = hit_count + 1 WHERE id = 1"
        )
        await self._connection.commit()
    
    async def _increment_miss_count(self) -> None:
        """Increment the cache miss count."""
        await self._connection.execute(
            "INSERT OR IGNORE INTO cache_stats (id, hit_count, miss_count) VALUES (1, 0, 0)"
        )
        await self._connection.execute(
            "UPDATE cache_stats SET miss_count = miss_count + 1 WHERE id = 1"
        )
        await self._connection.commit()
    
    async def _update_cleanup_timestamp(self) -> None:
        """Update the last cleanup timestamp."""
        await self._connection.execute(
            "INSERT OR IGNORE INTO cache_stats (id, hit_count, miss_count) VALUES (1, 0, 0)"
        )
        await self._connection.execute(
            "UPDATE cache_stats SET last_cleanup = ? WHERE id = 1",
            (datetime.utcnow().isoformat(),)
        )
        await self._connection.commit()
    
    async def _update_vacuum_timestamp(self) -> None:
        """Update the last vacuum timestamp."""
        await self._connection.execute(
            "INSERT OR IGNORE INTO cache_stats (id, hit_count, miss_count) VALUES (1, 0, 0)"
        )
        await self._connection.execute(
            "UPDATE cache_stats SET last_vacuum = ? WHERE id = 1",
            (datetime.utcnow().isoformat(),)
        )
        await self._connection.commit()


class ForkliftCache:
    """High-level cache interface for the Forklift application."""
    
    def __init__(self, config: Optional[CacheConfig] = None):
        """Initialize the cache.
        
        Args:
            config: Cache configuration (uses defaults if None)
        """
        self.config = config or CacheConfig()
        self.db = CacheDatabase(self.config)
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the cache system."""
        await self.db.initialize()
        self._initialized = True
        logger.info("Forklift cache system initialized")
    
    async def close(self) -> None:
        """Close the cache system."""
        await self.db.close()
        self._initialized = False
        logger.info("Forklift cache system closed")
    
    def _ensure_initialized(self) -> None:
        """Ensure the cache is initialized."""
        if not self._initialized:
            raise RuntimeError("Cache not initialized. Call initialize() first.")
    
    async def get_json(self, key: str) -> Optional[Any]:
        """Get a cached value and deserialize from JSON.
        
        Args:
            key: The cache key
            
        Returns:
            The deserialized value or None if not found/expired
        """
        self._ensure_initialized()
        
        entry = await self.db.get(key)
        if entry:
            try:
                return json.loads(entry.value)
            except json.JSONDecodeError:
                logger.warning(f"Failed to deserialize cached value for key: {key}")
                await self.db.delete(key)
        
        return None
    
    async def set_json(
        self,
        key: str,
        value: Any,
        entry_type: str,
        ttl_hours: Optional[int] = None,
        repository_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Cache a value with JSON serialization.
        
        Args:
            key: The cache key
            value: The value to cache
            entry_type: Type of the cached data
            ttl_hours: Time to live in hours
            repository_url: Associated repository URL
            metadata: Additional metadata
        """
        self._ensure_initialized()
        
        await self.db.set(
            key=key,
            value=value,
            entry_type=entry_type,
            ttl_hours=ttl_hours,
            repository_url=repository_url,
            metadata=metadata
        )
    
    async def delete(self, key: str) -> bool:
        """Delete a cache entry.
        
        Args:
            key: The cache key to delete
            
        Returns:
            True if deleted, False if not found
        """
        self._ensure_initialized()
        return await self.db.delete(key)
    
    async def clear_repository(self, repository_url: str) -> int:
        """Clear all cache entries for a specific repository.
        
        Args:
            repository_url: The repository URL
            
        Returns:
            Number of entries cleared
        """
        self._ensure_initialized()
        return await self.db.clear(repository_url=repository_url)
    
    async def clear_type(self, entry_type: str) -> int:
        """Clear all cache entries of a specific type.
        
        Args:
            entry_type: The entry type to clear
            
        Returns:
            Number of entries cleared
        """
        self._ensure_initialized()
        return await self.db.clear(entry_type=entry_type)
    
    async def cleanup_expired(self) -> int:
        """Remove expired cache entries.
        
        Returns:
            Number of expired entries removed
        """
        self._ensure_initialized()
        return await self.db.cleanup_expired()
    
    async def get_stats(self) -> CacheStats:
        """Get cache statistics.
        
        Returns:
            Cache statistics object
        """
        self._ensure_initialized()
        return await self.db.get_stats()
    
    async def vacuum(self) -> None:
        """Vacuum the database to optimize performance."""
        self._ensure_initialized()
        await self.db.vacuum()
    
    async def invalidate_repository_cache(
        self, 
        repository_url: str, 
        last_activity: Optional[datetime] = None
    ) -> int:
        """Invalidate cache entries for a repository based on activity.
        
        Args:
            repository_url: The repository URL
            last_activity: Last activity timestamp (if None, invalidates all)
            
        Returns:
            Number of entries invalidated
        """
        self._ensure_initialized()
        
        if last_activity is None:
            # Invalidate all entries for this repository
            return await self.clear_repository(repository_url)
        
        # Only invalidate entries older than the last activity
        if not self.db._connection:
            raise RuntimeError("Database not initialized")
        
        query = """
        DELETE FROM cache_entries 
        WHERE repository_url = ? AND created_at < ?
        """
        
        cursor = await self.db._connection.execute(
            query, 
            (repository_url, last_activity.isoformat())
        )
        await self.db._connection.commit()
        
        invalidated_count = cursor.rowcount
        if invalidated_count > 0:
            logger.info(f"Invalidated {invalidated_count} cache entries for {repository_url}")
        
        return invalidated_count
    
    async def is_cache_valid(
        self, 
        key: str, 
        repository_last_activity: Optional[datetime] = None
    ) -> bool:
        """Check if a cache entry is still valid based on repository activity.
        
        Args:
            key: The cache key to check
            repository_last_activity: Last activity timestamp of the repository
            
        Returns:
            True if cache is valid, False otherwise
        """
        self._ensure_initialized()
        
        entry = await self.db.get(key)
        if not entry:
            return False
        
        # Check expiration
        if entry.expires_at and entry.expires_at <= datetime.utcnow():
            return False
        
        # Check against repository activity
        if repository_last_activity and entry.created_at < repository_last_activity:
            return False
        
        return True
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()