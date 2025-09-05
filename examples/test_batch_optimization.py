#!/usr/bin/env python3
"""
Test script to verify the batch optimization for get_commits_ahead.
"""

import asyncio
import os
import time
from forklift.config import GitHubConfig
from forklift.github.client import GitHubClient


async def test_batch_optimization():
    """Test the batch optimization vs individual calls."""
    
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ GITHUB_TOKEN environment variable not set")
        return
    
    config = GitHubConfig(
        token=token,
        base_url="https://api.github.com",
        timeout_seconds=30,
    )
    
    print("🚀 Testing Batch Optimization for get_commits_ahead")
    print("=" * 60)
    
    async with GitHubClient(config) as client:
        # Test data - multiple forks against the same parent
        parent_owner, parent_repo = "octocat", "Hello-World"
        fork_data_list = [
            ("octocat", "Hello-World"),  # Same repo for testing
            ("octocat", "Hello-World"),  # Same repo for testing  
            ("octocat", "Hello-World"),  # Same repo for testing
        ]
        
        print(f"Testing with {len(fork_data_list)} forks against {parent_owner}/{parent_repo}")
        
        # Test 1: Individual calls (current method)
        print("\n📊 Test 1: Individual get_commits_ahead calls")
        start_time = time.time()
        
        individual_results = {}
        for i, (fork_owner, fork_repo) in enumerate(fork_data_list):
            try:
                commits = await client.get_commits_ahead(
                    fork_owner, fork_repo, parent_owner, parent_repo, 3
                )
                individual_results[f"{fork_owner}/{fork_repo}_{i}"] = commits
                print(f"  Fork {i+1}: {len(commits)} commits")
            except Exception as e:
                print(f"  Fork {i+1}: Error - {e}")
        
        individual_time = time.time() - start_time
        print(f"  ⏱️  Individual calls took: {individual_time:.2f} seconds")
        
        # Test 2: Batch processing (optimized method)
        print("\n🚀 Test 2: Batch get_commits_ahead_batch call")
        start_time = time.time()
        
        try:
            batch_results = await client.get_commits_ahead_batch(
                fork_data_list, parent_owner, parent_repo, 3
            )
            
            for i, fork_key in enumerate(batch_results.keys()):
                commits = batch_results[fork_key]
                print(f"  Fork {i+1}: {len(commits)} commits")
                
        except Exception as e:
            print(f"  Batch processing error: {e}")
            batch_results = {}
        
        batch_time = time.time() - start_time
        print(f"  ⏱️  Batch processing took: {batch_time:.2f} seconds")
        
        # Compare results
        print(f"\n📈 Performance Comparison:")
        if individual_time > 0 and batch_time > 0:
            improvement = ((individual_time - batch_time) / individual_time) * 100
            print(f"  • Individual calls: {individual_time:.2f}s")
            print(f"  • Batch processing: {batch_time:.2f}s")
            print(f"  • Performance improvement: {improvement:.1f}%")
        
        print(f"\n💡 API Call Analysis:")
        print(f"  • Individual method: {len(fork_data_list) * 3} API calls")
        print(f"    - Fork repos: {len(fork_data_list)} calls")
        print(f"    - Parent repo: {len(fork_data_list)} calls (redundant!)")
        print(f"    - Comparisons: {len(fork_data_list)} calls")
        print(f"  • Batch method: {len(fork_data_list) * 2 + 1} API calls")
        print(f"    - Fork repos: {len(fork_data_list)} calls")
        print(f"    - Parent repo: 1 call (optimized!)")
        print(f"    - Comparisons: {len(fork_data_list)} calls")
        
        api_calls_saved = len(fork_data_list) - 1
        print(f"  • API calls saved: {api_calls_saved}")
        
        # Test cache stats
        parent_stats = client.get_parent_repo_cache_stats()
        print(f"\n📊 Cache Statistics:")
        print(f"  • Parent repo cache: {parent_stats}")


if __name__ == "__main__":
    asyncio.run(test_batch_optimization())