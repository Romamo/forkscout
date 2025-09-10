#!/usr/bin/env python3
"""
Demonstration of parent repository caching in GitHubClient.

This script shows how the GitHubClient caches parent repository data
to reduce API calls when analyzing multiple forks of the same parent repository.
"""

import asyncio
import os
import time
from forkscout.config import GitHubConfig
from forkscout.github.client import GitHubClient


async def demonstrate_parent_repo_caching():
    """Demonstrate parent repository caching functionality."""
    
    # Check for GitHub token
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ GITHUB_TOKEN environment variable not set")
        print("Please set your GitHub token to run this demo:")
        print("export GITHUB_TOKEN=your_token_here")
        return
    
    # Create GitHub client
    config = GitHubConfig(
        token=token,
        base_url="https://api.github.com",
        timeout_seconds=30,
    )
    
    print("🚀 Parent Repository Caching Demo")
    print("=" * 50)
    
    async with GitHubClient(config) as client:
        # Clear cache to start fresh
        client.clear_parent_repo_cache()
        print("🧹 Cleared cache to start fresh")
        
        # Show initial cache stats
        stats = client.get_parent_repo_cache_stats()
        print(f"📊 Initial cache stats: {stats['total_entries']} entries")
        
        # Use a well-known repository for testing
        parent_owner = "octocat"
        parent_repo = "Hello-World"
        
        print(f"\n🎯 Testing with parent repository: {parent_owner}/{parent_repo}")
        
        try:
            # First call - should cache the parent repository
            print("\n1️⃣ First call to get_commits_ahead (should cache parent repo)...")
            start_time = time.time()
            
            commits1 = await client.get_commits_ahead(
                "octocat", "Hello-World", parent_owner, parent_repo, 3
            )
            
            first_call_time = time.time() - start_time
            print(f"   ⏱️  First call took: {first_call_time:.2f} seconds")
            print(f"   📝 Found {len(commits1)} commits ahead")
            
            # Check cache stats after first call
            stats = client.get_parent_repo_cache_stats()
            print(f"   📊 Cache stats after first call: {stats['total_entries']} entries")
            
            # Second call - should use cached parent repository
            print("\n2️⃣ Second call to get_commits_ahead (should use cached parent repo)...")
            start_time = time.time()
            
            commits2 = await client.get_commits_ahead(
                "octocat", "Hello-World", parent_owner, parent_repo, 3
            )
            
            second_call_time = time.time() - start_time
            print(f"   ⏱️  Second call took: {second_call_time:.2f} seconds")
            print(f"   📝 Found {len(commits2)} commits ahead")
            
            # Show performance improvement
            if first_call_time > 0 and second_call_time > 0:
                improvement = ((first_call_time - second_call_time) / first_call_time) * 100
                print(f"   🚀 Performance improvement: {improvement:.1f}%")
            
            # Demonstrate cache with multiple "forks" (simulated)
            print("\n3️⃣ Simulating multiple forks of the same parent...")
            
            # This would normally be different forks, but for demo purposes
            # we'll use the same fork multiple times to show caching
            fork_calls = 3
            total_time = 0
            
            for i in range(fork_calls):
                start_time = time.time()
                commits = await client.get_commits_ahead(
                    "octocat", "Hello-World", parent_owner, parent_repo, 2
                )
                call_time = time.time() - start_time
                total_time += call_time
                print(f"   📞 Call {i+1}: {call_time:.2f}s, {len(commits)} commits")
            
            avg_time = total_time / fork_calls
            print(f"   📊 Average time per call: {avg_time:.2f}s")
            
            # Show final cache stats
            stats = client.get_parent_repo_cache_stats()
            print(f"\n📊 Final cache statistics:")
            print(f"   • Total entries: {stats['total_entries']}")
            print(f"   • Valid entries: {stats['valid_entries']}")
            print(f"   • Expired entries: {stats['expired_entries']}")
            print(f"   • Cache TTL: {stats['cache_ttl_seconds']} seconds")
            
            # Demonstrate cache clearing
            print(f"\n🧹 Clearing cache...")
            client.clear_parent_repo_cache()
            stats = client.get_parent_repo_cache_stats()
            print(f"   📊 Cache entries after clearing: {stats['total_entries']}")
            
            print(f"\n✅ Demo completed successfully!")
            print(f"\n💡 Key benefits of parent repository caching:")
            print(f"   • Reduces API calls when analyzing multiple forks")
            print(f"   • Improves performance for batch operations")
            print(f"   • Respects GitHub API rate limits")
            print(f"   • Automatic cache expiration (5 minutes TTL)")
            print(f"   • Thread-safe for concurrent operations")
            
        except Exception as e:
            print(f"❌ Error during demo: {e}")
            print(f"This might happen if the test repository is not accessible")
            print(f"or if there are network issues.")


async def demonstrate_cache_expiration():
    """Demonstrate cache expiration functionality."""
    
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ GITHUB_TOKEN environment variable not set")
        return
    
    config = GitHubConfig(
        token=token,
        base_url="https://api.github.com",
        timeout_seconds=30,
    )
    
    print("\n🕐 Cache Expiration Demo")
    print("=" * 30)
    
    async with GitHubClient(config) as client:
        # Set a very short TTL for demonstration
        original_ttl = client._cache_ttl
        client._cache_ttl = 2  # 2 seconds
        
        try:
            # Clear cache
            client.clear_parent_repo_cache()
            
            # Mock a repository for caching
            from forkscout.models.github import Repository
            
            repo_data = {
                "id": 1,
                "name": "demo-repo",
                "full_name": "demo-owner/demo-repo",
                "owner": {"login": "demo-owner"},
                "url": "https://api.github.com/repos/demo-owner/demo-repo",
                "html_url": "https://github.com/demo-owner/demo-repo",
                "clone_url": "https://github.com/demo-owner/demo-repo.git",
                "default_branch": "main",
                "stargazers_count": 100,
                "forks_count": 25,
                "watchers_count": 150,
                "open_issues_count": 5,
                "size": 1024,
                "language": "Python",
                "description": "A demo repository",
                "topics": ["demo", "caching"],
                "license": {"name": "MIT"},
                "private": False,
                "fork": False,
                "archived": False,
                "disabled": False,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-02T00:00:00Z",
                "pushed_at": "2023-01-03T00:00:00Z",
            }
            
            repo = Repository.from_github_api(repo_data)
            
            # Cache the repository
            print("📦 Caching demo repository...")
            client._cache_parent_repo("demo-owner", "demo-repo", repo)
            
            # Check it's cached
            cached = client._get_cached_parent_repo("demo-owner", "demo-repo")
            print(f"✅ Repository cached: {cached is not None}")
            
            # Wait for expiration
            print("⏳ Waiting for cache to expire (2 seconds)...")
            await asyncio.sleep(3)
            
            # Check if expired
            cached = client._get_cached_parent_repo("demo-owner", "demo-repo")
            print(f"🕐 Repository after expiration: {cached is not None}")
            
            if cached is None:
                print("✅ Cache expiration working correctly!")
            else:
                print("❌ Cache did not expire as expected")
            
        finally:
            # Restore original TTL
            client._cache_ttl = original_ttl


if __name__ == "__main__":
    print("🎭 GitHub Client Parent Repository Caching Demo")
    print("This demo shows how parent repository caching works")
    print("to optimize API usage when analyzing multiple forks.\n")
    
    asyncio.run(demonstrate_parent_repo_caching())
    asyncio.run(demonstrate_cache_expiration())