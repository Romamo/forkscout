"""Tests for the SQLite-based caching system."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.forklift.models.cache import CacheConfig, CacheStats
from src.forklift.storage.cache import CacheDatabase, ForkliftCache


@pytest.fixture
async def temp_cache_config():
    """Create a temporary cache configuration for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        config = CacheConfig(database_path=tmp.name)
        yield config
        # Cleanup
        Path(tmp.name).unlink(missing_ok=True)


@pytest.fixture
async def cache_db(temp_cache_config):
    """Create and initialize a cache database for testing."""
    db = CacheDatabase(temp_cache_config)
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
async def forklift_cache(temp_cache_config):
    """Create and initialize a ForkliftCache for testing."""
    cache = ForkliftCache(temp_cache_config)
    await cache.initialize()
    yield cache
    await cache.close()


class TestCacheDatabase:
    """Test cases for CacheDatabase class."""

    async def test_initialize_creates_tables(self, temp_cache_config):
        """Test that initialization creates the required tables."""
        db = CacheDatabase(temp_cache_config)
        await db.initialize()

        # Check that tables exist
        query = "SELECT name FROM sqlite_master WHERE type='table'"
        async with db._connection.execute(query) as cursor:
            tables = [row[0] for row in await cursor.fetchall()]

        assert "cache_entries" in tables
        assert "cache_stats" in tables

        await db.close()

    async def test_set_and_get_cache_entry(self, cache_db):
        """Test storing and retrieving a cache entry."""
        test_data = {"key": "value", "number": 42}

        await cache_db.set(
            key="test_key",
            value=test_data,
            entry_type="test",
            repository_url="https://github.com/owner/repo"
        )

        entry = await cache_db.get("test_key")

        assert entry is not None
        assert entry.key == "test_key"
        assert json.loads(entry.value) == test_data
        assert entry.entry_type == "test"
        assert entry.repository_url == "https://github.com/owner/repo"
        assert isinstance(entry.created_at, datetime)
        assert isinstance(entry.expires_at, datetime)

    async def test_get_nonexistent_key(self, cache_db):
        """Test retrieving a non-existent cache entry."""
        entry = await cache_db.get("nonexistent_key")
        assert entry is None

    async def test_cache_expiration(self, cache_db):
        """Test that expired entries are not returned."""
        test_data = {"expired": True}

        # Set entry with very short TTL
        await cache_db.set(
            key="expired_key",
            value=test_data,
            entry_type="test",
            ttl_hours=-1  # Already expired
        )

        # Should return None for expired entry
        entry = await cache_db.get("expired_key")
        assert entry is None

    async def test_delete_cache_entry(self, cache_db):
        """Test deleting a cache entry."""
        await cache_db.set("delete_me", {"data": "test"}, "test")

        # Verify entry exists
        entry = await cache_db.get("delete_me")
        assert entry is not None

        # Delete entry
        deleted = await cache_db.delete("delete_me")
        assert deleted is True

        # Verify entry is gone
        entry = await cache_db.get("delete_me")
        assert entry is None

        # Try to delete non-existent entry
        deleted = await cache_db.delete("delete_me")
        assert deleted is False

    async def test_clear_by_type(self, cache_db):
        """Test clearing cache entries by type."""
        # Add entries of different types
        await cache_db.set("key1", {"data": 1}, "type_a")
        await cache_db.set("key2", {"data": 2}, "type_b")
        await cache_db.set("key3", {"data": 3}, "type_a")

        # Clear type_a entries
        cleared = await cache_db.clear(entry_type="type_a")
        assert cleared == 2

        # Verify only type_b entry remains
        assert await cache_db.get("key1") is None
        assert await cache_db.get("key2") is not None
        assert await cache_db.get("key3") is None

    async def test_clear_by_repository(self, cache_db):
        """Test clearing cache entries by repository URL."""
        repo1 = "https://github.com/owner1/repo1"
        repo2 = "https://github.com/owner2/repo2"

        await cache_db.set("key1", {"data": 1}, "test", repository_url=repo1)
        await cache_db.set("key2", {"data": 2}, "test", repository_url=repo2)
        await cache_db.set("key3", {"data": 3}, "test", repository_url=repo1)

        # Clear repo1 entries
        cleared = await cache_db.clear(repository_url=repo1)
        assert cleared == 2

        # Verify only repo2 entry remains
        assert await cache_db.get("key1") is None
        assert await cache_db.get("key2") is not None
        assert await cache_db.get("key3") is None

    async def test_cleanup_expired(self, cache_db):
        """Test cleaning up expired entries."""
        # Add expired and non-expired entries
        await cache_db.set("expired1", {"data": 1}, "test", ttl_hours=-1)
        await cache_db.set("expired2", {"data": 2}, "test", ttl_hours=-1)
        await cache_db.set("valid", {"data": 3}, "test", ttl_hours=24)

        # Cleanup expired entries
        cleaned = await cache_db.cleanup_expired()
        assert cleaned == 2

        # Verify only valid entry remains
        assert await cache_db.get("expired1") is None
        assert await cache_db.get("expired2") is None
        assert await cache_db.get("valid") is not None

    async def test_get_stats(self, cache_db):
        """Test getting cache statistics."""
        # Add some test entries
        await cache_db.set("key1", {"data": 1}, "type_a")
        await cache_db.set("key2", {"data": 2}, "type_b")
        await cache_db.set("key3", {"data": 3}, "type_a")

        # Trigger some hits and misses
        await cache_db.get("key1")  # hit
        await cache_db.get("key2")  # hit
        await cache_db.get("nonexistent")  # miss

        stats = await cache_db.get_stats()

        assert stats.total_entries == 3
        assert stats.total_size_bytes > 0
        assert stats.hit_count == 2
        assert stats.miss_count == 1
        assert stats.entries_by_type["type_a"] == 2
        assert stats.entries_by_type["type_b"] == 1
        assert isinstance(stats.oldest_entry, datetime)
        assert isinstance(stats.newest_entry, datetime)

    async def test_vacuum(self, cache_db):
        """Test database vacuum operation."""
        # Add and delete some entries to create fragmentation
        for i in range(10):
            await cache_db.set(f"key{i}", {"data": i}, "test")

        for i in range(5):
            await cache_db.delete(f"key{i}")

        # Vacuum should complete without error
        await cache_db.vacuum()

    async def test_database_not_initialized_error(self, temp_cache_config):
        """Test that operations fail when database is not initialized."""
        db = CacheDatabase(temp_cache_config)

        with pytest.raises(RuntimeError, match="Database not initialized"):
            await db.get("test_key")

        with pytest.raises(RuntimeError, match="Database not initialized"):
            await db.set("test_key", {"data": "test"}, "test")


class TestForkliftCache:
    """Test cases for ForkliftCache class."""

    async def test_cache_initialization(self, temp_cache_config):
        """Test cache initialization and cleanup."""
        cache = ForkliftCache(temp_cache_config)

        # Should not be initialized initially
        with pytest.raises(RuntimeError, match="Cache not initialized"):
            await cache.get_json("test_key")

        await cache.initialize()

        # Should work after initialization
        result = await cache.get_json("test_key")
        assert result is None

        await cache.close()

    async def test_context_manager(self, temp_cache_config):
        """Test using cache as async context manager."""
        async with ForkliftCache(temp_cache_config) as cache:
            await cache.set_json("test_key", {"data": "test"}, "test")
            result = await cache.get_json("test_key")
            assert result == {"data": "test"}

    async def test_set_and_get_json(self, forklift_cache):
        """Test JSON serialization and deserialization."""
        test_data = {
            "string": "value",
            "number": 42,
            "boolean": True,
            "list": [1, 2, 3],
            "nested": {"key": "value"}
        }

        await forklift_cache.set_json(
            key="json_test",
            value=test_data,
            entry_type="test",
            repository_url="https://github.com/owner/repo"
        )

        result = await forklift_cache.get_json("json_test")
        assert result == test_data

    async def test_get_json_invalid_data(self, forklift_cache):
        """Test handling of invalid JSON data."""
        # Manually insert invalid JSON by directly inserting into database
        query = """
        INSERT INTO cache_entries 
        (key, value, created_at, expires_at, entry_type, size_bytes)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        expires_at = datetime.utcnow() + timedelta(hours=24)
        await forklift_cache.db._connection.execute(query, (
            "invalid_json",
            "invalid json data {not valid}",
            datetime.utcnow().isoformat(),
            expires_at.isoformat(),
            "test",
            len("invalid json data {not valid}")
        ))
        await forklift_cache.db._connection.commit()

        # Should return None and clean up invalid entry
        result = await forklift_cache.get_json("invalid_json")
        assert result is None

        # Entry should be deleted
        entry = await forklift_cache.db.get("invalid_json")
        assert entry is None

    async def test_delete(self, forklift_cache):
        """Test deleting cache entries."""
        await forklift_cache.set_json("delete_test", {"data": "test"}, "test")

        deleted = await forklift_cache.delete("delete_test")
        assert deleted is True

        result = await forklift_cache.get_json("delete_test")
        assert result is None

    async def test_clear_repository(self, forklift_cache):
        """Test clearing entries by repository."""
        repo1 = "https://github.com/owner1/repo1"
        repo2 = "https://github.com/owner2/repo2"

        await forklift_cache.set_json("key1", {"data": 1}, "test", repository_url=repo1)
        await forklift_cache.set_json("key2", {"data": 2}, "test", repository_url=repo2)
        await forklift_cache.set_json("key3", {"data": 3}, "test", repository_url=repo1)

        cleared = await forklift_cache.clear_repository(repo1)
        assert cleared == 2

        assert await forklift_cache.get_json("key1") is None
        assert await forklift_cache.get_json("key2") is not None
        assert await forklift_cache.get_json("key3") is None

    async def test_clear_type(self, forklift_cache):
        """Test clearing entries by type."""
        await forklift_cache.set_json("key1", {"data": 1}, "type_a")
        await forklift_cache.set_json("key2", {"data": 2}, "type_b")
        await forklift_cache.set_json("key3", {"data": 3}, "type_a")

        cleared = await forklift_cache.clear_type("type_a")
        assert cleared == 2

        assert await forklift_cache.get_json("key1") is None
        assert await forklift_cache.get_json("key2") is not None
        assert await forklift_cache.get_json("key3") is None

    async def test_cleanup_expired(self, forklift_cache):
        """Test cleaning up expired entries."""
        await forklift_cache.set_json("expired", {"data": 1}, "test", ttl_hours=-1)
        await forklift_cache.set_json("valid", {"data": 2}, "test", ttl_hours=24)

        cleaned = await forklift_cache.cleanup_expired()
        assert cleaned == 1

        assert await forklift_cache.get_json("expired") is None
        assert await forklift_cache.get_json("valid") is not None

    async def test_get_stats(self, forklift_cache):
        """Test getting cache statistics."""
        await forklift_cache.set_json("key1", {"data": 1}, "test")
        await forklift_cache.set_json("key2", {"data": 2}, "test")

        # Trigger some cache operations
        await forklift_cache.get_json("key1")
        await forklift_cache.get_json("nonexistent")

        stats = await forklift_cache.get_stats()

        assert stats.total_entries == 2
        assert stats.hit_count >= 1
        assert stats.miss_count >= 1
        assert isinstance(stats, CacheStats)

    async def test_vacuum(self, forklift_cache):
        """Test database vacuum operation."""
        # Add some data
        for i in range(5):
            await forklift_cache.set_json(f"key{i}", {"data": i}, "test")

        # Vacuum should complete without error
        await forklift_cache.vacuum()

    async def test_default_config(self):
        """Test using default configuration."""
        cache = ForkliftCache()
        assert isinstance(cache.config, CacheConfig)
        assert cache.config.database_path == "forklift_cache.db"
        assert cache.config.default_ttl_hours == 24

    async def test_invalidate_repository_cache_all(self, forklift_cache):
        """Test invalidating all cache entries for a repository."""
        repo1 = "https://github.com/owner1/repo1"
        repo2 = "https://github.com/owner2/repo2"

        await forklift_cache.set_json("key1", {"data": 1}, "test", repository_url=repo1)
        await forklift_cache.set_json("key2", {"data": 2}, "test", repository_url=repo2)
        await forklift_cache.set_json("key3", {"data": 3}, "test", repository_url=repo1)

        # Invalidate all entries for repo1
        invalidated = await forklift_cache.invalidate_repository_cache(repo1)
        assert invalidated == 2

        # Check that only repo2 entries remain
        assert await forklift_cache.get_json("key1") is None
        assert await forklift_cache.get_json("key2") is not None
        assert await forklift_cache.get_json("key3") is None

    async def test_invalidate_repository_cache_by_activity(self, forklift_cache):
        """Test invalidating cache entries based on repository activity."""
        repo_url = "https://github.com/owner/repo"

        # Create entries at different times
        old_time = datetime.utcnow() - timedelta(hours=2)
        recent_time = datetime.utcnow() - timedelta(minutes=30)

        # Manually set creation times by inserting directly
        await forklift_cache.set_json("old_key", {"data": "old"}, "test", repository_url=repo_url)
        await forklift_cache.set_json("recent_key", {"data": "recent"}, "test", repository_url=repo_url)

        # Update creation times manually
        await forklift_cache.db._connection.execute(
            "UPDATE cache_entries SET created_at = ? WHERE key = ?",
            (old_time.isoformat(), "old_key")
        )
        await forklift_cache.db._connection.execute(
            "UPDATE cache_entries SET created_at = ? WHERE key = ?",
            (recent_time.isoformat(), "recent_key")
        )
        await forklift_cache.db._connection.commit()

        # Invalidate entries older than 1 hour ago
        activity_time = datetime.utcnow() - timedelta(hours=1)
        invalidated = await forklift_cache.invalidate_repository_cache(repo_url, activity_time)
        assert invalidated == 1

        # Check that only recent entry remains
        assert await forklift_cache.get_json("old_key") is None
        assert await forklift_cache.get_json("recent_key") is not None

    async def test_is_cache_valid(self, forklift_cache):
        """Test checking cache validity based on repository activity."""
        repo_url = "https://github.com/owner/repo"

        # Create a cache entry
        await forklift_cache.set_json("test_key", {"data": "test"}, "test", repository_url=repo_url)

        # Should be valid without activity check
        is_valid = await forklift_cache.is_cache_valid("test_key")
        assert is_valid is True

        # Should be valid with old activity time
        old_activity = datetime.utcnow() - timedelta(hours=2)
        is_valid = await forklift_cache.is_cache_valid("test_key", old_activity)
        assert is_valid is True

        # Should be invalid with recent activity time
        recent_activity = datetime.utcnow() + timedelta(minutes=1)
        is_valid = await forklift_cache.is_cache_valid("test_key", recent_activity)
        assert is_valid is False

        # Should be invalid for non-existent key
        is_valid = await forklift_cache.is_cache_valid("nonexistent_key")
        assert is_valid is False
