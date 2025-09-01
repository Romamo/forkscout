"""Integration tests for parent repository caching functionality."""

import os
import pytest
import pytest_asyncio
import asyncio
from unittest.mock import patch, MagicMock

from forklift.config import GitHubConfig
from forklift.github.client import GitHubClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestParentRepositoryCachingIntegration:
    """Integration tests for parent repository caching."""

    @pytest_asyncio.fixture
    async def github_client(self):
        """Create a real GitHub client for integration testing."""
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            pytest.skip("GITHUB_TOKEN environment variable not set")
        
        config = GitHubConfig(
            token=token,
            base_url="https://api.github.com",
            timeout_seconds=30,
        )
        
        client = GitHubClient(config)
        async with client:
            yield client

    async def test_parent_repo_caching_reduces_api_calls(self, github_client):
        """Test that parent repository caching reduces API calls in real scenarios."""
        # Use a well-known repository with forks for testing
        parent_owner = "octocat"
        parent_repo = "Hello-World"
        
        # We'll simulate multiple forks by calling get_commits_ahead multiple times
        # with different fork names but the same parent
        
        # Clear cache to start fresh
        github_client.clear_parent_repo_cache()
        
        # Mock the get_repository method to count calls
        original_get_repository = github_client.get_repository
        call_count = {"count": 0}
        
        async def counting_get_repository(*args, **kwargs):
            call_count["count"] += 1
            return await original_get_repository(*args, **kwargs)
        
        with patch.object(github_client, 'get_repository', side_effect=counting_get_repository):
            try:
                # First call - should fetch parent repo from API
                await github_client.get_commits_ahead(
                    "octocat", "Hello-World", parent_owner, parent_repo, 1
                )
                first_call_count = call_count["count"]
                
                # Second call with same parent - should use cached parent repo
                await github_client.get_commits_ahead(
                    "octocat", "Hello-World", parent_owner, parent_repo, 1
                )
                second_call_count = call_count["count"]
                
                # The parent repository should only be fetched once due to caching
                # Each call fetches the fork repo (2 calls) + parent repo (1 call total due to caching)
                # So we expect: first call = 2 (fork + parent), second call = 1 (fork only)
                assert second_call_count == first_call_count + 1, (
                    f"Expected parent repo to be cached. "
                    f"First call count: {first_call_count}, Second call count: {second_call_count}"
                )
                
            except Exception as e:
                # If the repository doesn't exist or has no forks, that's okay for this test
                # We're mainly testing the caching mechanism
                if "not found" in str(e).lower() or "no commits" in str(e).lower():
                    pytest.skip(f"Test repository not suitable for testing: {e}")
                else:
                    raise

    async def test_cache_statistics_tracking(self, github_client):
        """Test that cache statistics are properly tracked."""
        # Clear cache to start fresh
        github_client.clear_parent_repo_cache()
        
        # Check initial stats
        stats = github_client.get_parent_repo_cache_stats()
        assert stats["total_entries"] == 0
        assert stats["valid_entries"] == 0
        assert stats["expired_entries"] == 0
        assert stats["cache_ttl_seconds"] == 300

    async def test_cache_expiration_behavior(self, github_client):
        """Test cache expiration behavior with a very short TTL."""
        # Set a very short TTL for testing
        original_ttl = github_client._cache_ttl
        github_client._cache_ttl = 0.1  # 100ms
        
        try:
            # Clear cache to start fresh
            github_client.clear_parent_repo_cache()
            
            # Mock a simple repository for caching
            from forklift.models.github import Repository
            
            repo_data = {
                "id": 1,
                "name": "test",
                "full_name": "owner/test",
                "owner": {"login": "owner"},
                "url": "https://api.github.com/repos/owner/test",
                "html_url": "https://github.com/owner/test",
                "clone_url": "https://github.com/owner/test.git",
                "default_branch": "main",
                "stargazers_count": 0,
                "forks_count": 0,
                "watchers_count": 0,
                "open_issues_count": 0,
                "size": 0,
                "language": None,
                "description": None,
                "topics": [],
                "license": None,
                "private": False,
                "fork": False,
                "archived": False,
                "disabled": False,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "pushed_at": "2023-01-01T00:00:00Z",
            }
            
            repo = Repository.from_github_api(repo_data)
            
            # Cache the repository
            github_client._cache_parent_repo("owner", "test", repo)
            
            # Verify it's cached
            stats = github_client.get_parent_repo_cache_stats()
            assert stats["total_entries"] == 1
            assert stats["valid_entries"] == 1
            
            # Wait for cache to expire
            await asyncio.sleep(0.2)
            
            # Check that cache entry is now considered expired
            cached_repo = github_client._get_cached_parent_repo("owner", "test")
            assert cached_repo is None
            
            # Verify cache stats reflect expiration
            stats = github_client.get_parent_repo_cache_stats()
            assert stats["total_entries"] == 0  # Expired entries are removed
            
        finally:
            # Restore original TTL
            github_client._cache_ttl = original_ttl

    async def test_cache_clearing_functionality(self, github_client):
        """Test cache clearing functionality."""
        # Mock and cache some repositories
        from forklift.models.github import Repository
        
        repo_data = {
            "id": 1,
            "name": "test",
            "full_name": "owner/test",
            "owner": {"login": "owner"},
            "url": "https://api.github.com/repos/owner/test",
            "html_url": "https://github.com/owner/test",
            "clone_url": "https://github.com/owner/test.git",
            "default_branch": "main",
            "stargazers_count": 0,
            "forks_count": 0,
            "watchers_count": 0,
            "open_issues_count": 0,
            "size": 0,
            "language": None,
            "description": None,
            "topics": [],
            "license": None,
            "private": False,
            "fork": False,
            "archived": False,
            "disabled": False,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
            "pushed_at": "2023-01-01T00:00:00Z",
        }
        
        repo = Repository.from_github_api(repo_data)
        
        # Cache multiple repositories
        github_client._cache_parent_repo("owner1", "test1", repo)
        github_client._cache_parent_repo("owner2", "test2", repo)
        github_client._cache_parent_repo("owner3", "test3", repo)
        
        # Verify they're cached
        stats = github_client.get_parent_repo_cache_stats()
        assert stats["total_entries"] == 3
        
        # Clear cache
        github_client.clear_parent_repo_cache()
        
        # Verify cache is empty
        stats = github_client.get_parent_repo_cache_stats()
        assert stats["total_entries"] == 0

    async def test_concurrent_cache_access(self, github_client):
        """Test that concurrent access to cache is safe."""
        from forklift.models.github import Repository
        
        repo_data = {
            "id": 1,
            "name": "test",
            "full_name": "owner/test",
            "owner": {"login": "owner"},
            "url": "https://api.github.com/repos/owner/test",
            "html_url": "https://github.com/owner/test",
            "clone_url": "https://github.com/owner/test.git",
            "default_branch": "main",
            "stargazers_count": 0,
            "forks_count": 0,
            "watchers_count": 0,
            "open_issues_count": 0,
            "size": 0,
            "language": None,
            "description": None,
            "topics": [],
            "license": None,
            "private": False,
            "fork": False,
            "archived": False,
            "disabled": False,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
            "pushed_at": "2023-01-01T00:00:00Z",
        }
        
        repo = Repository.from_github_api(repo_data)
        
        # Clear cache
        github_client.clear_parent_repo_cache()
        
        # Define concurrent operations
        async def cache_operation(i):
            # Cache a repository
            github_client._cache_parent_repo(f"owner{i}", f"test{i}", repo)
            
            # Try to retrieve it
            cached = github_client._get_cached_parent_repo(f"owner{i}", f"test{i}")
            assert cached is not None
            
            # Get stats
            stats = github_client.get_parent_repo_cache_stats()
            assert stats["total_entries"] >= 1
        
        # Run multiple concurrent operations
        tasks = [cache_operation(i) for i in range(5)]
        await asyncio.gather(*tasks)
        
        # Verify final state
        stats = github_client.get_parent_repo_cache_stats()
        assert stats["total_entries"] == 5
        assert stats["valid_entries"] == 5

    async def test_cache_with_real_api_calls_logging(self, github_client, caplog):
        """Test that cache usage is properly logged."""
        import logging
        
        # Set logging level to capture debug messages
        logging.getLogger("forklift.github.client").setLevel(logging.DEBUG)
        
        # Clear cache
        github_client.clear_parent_repo_cache()
        
        try:
            # Make a call that should cache the parent repo
            await github_client.get_commits_ahead(
                "octocat", "Hello-World", "octocat", "Hello-World", 1
            )
            
            # Check that caching was logged
            cache_logs = [record for record in caplog.records 
                         if "Cached parent repository data" in record.message]
            assert len(cache_logs) > 0
            
            # Make another call that should use the cache
            caplog.clear()
            await github_client.get_commits_ahead(
                "octocat", "Hello-World", "octocat", "Hello-World", 1
            )
            
            # Check that cache usage was logged
            cache_usage_logs = [record for record in caplog.records 
                               if "Using cached parent repository data" in record.message or
                                  "API call saved using cached parent repository data" in record.message]
            assert len(cache_usage_logs) > 0
            
        except Exception as e:
            # If the repository doesn't exist or has issues, that's okay for this test
            if "not found" in str(e).lower() or "no commits" in str(e).lower():
                pytest.skip(f"Test repository not suitable for testing: {e}")
            else:
                raise