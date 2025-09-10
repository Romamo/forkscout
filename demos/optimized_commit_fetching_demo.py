#!/usr/bin/env python3
"""
Demonstration of optimized commit fetching functionality.

This script shows how the OptimizedCommitFetcher uses fork qualification data
to minimize API calls when fetching commits from repository forks.
"""

import asyncio
import os
from datetime import datetime

from forkscout.config import GitHubConfig
from forkscout.github.client import GitHubClient
from forkscout.github.fork_list_processor import ForkListProcessor
from forkscout.github.optimized_commit_fetcher import OptimizedCommitFetcher
from forkscout.models.fork_qualification import CollectedForkData, ForkQualificationMetrics


async def demonstrate_optimization():
    """Demonstrate the optimization benefits of the commit fetcher."""
    print("🚀 Optimized Commit Fetching Demonstration")
    print("=" * 50)
    
    # Check for GitHub token
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ GITHUB_TOKEN environment variable not set")
        print("   Set your GitHub token to run this demo with real data")
        print("   Showing mock demonstration instead...")
        await demonstrate_with_mock_data()
        return
    
    # Create GitHub client
    config = GitHubConfig(token=token, base_url="https://api.github.com", timeout_seconds=30)
    
    async with GitHubClient(config) as github_client:
        # Create processors
        fork_processor = ForkListProcessor(github_client)
        commit_fetcher = OptimizedCommitFetcher(github_client)
        
        # Use a small test repository
        owner = "maliayas"
        repo = "github-network-ninja"
        
        print(f"📊 Analyzing repository: {owner}/{repo}")
        print()
        
        try:
            # Step 1: Collect fork qualification data
            print("1️⃣ Collecting fork qualification data...")
            qualified_forks = await fork_processor.collect_and_process_forks(owner, repo)
            
            print(f"   Found {len(qualified_forks.collected_forks)} forks")
            print(f"   Can skip: {len(qualified_forks.forks_to_skip)} forks")
            print(f"   Need analysis: {len(qualified_forks.forks_needing_analysis)} forks")
            print()
            
            # Step 2: Show optimization summary
            print("2️⃣ Optimization Analysis:")
            summary = commit_fetcher.get_optimization_summary(qualified_forks)
            print(summary)
            print()
            
            # Step 3: Perform optimized commit fetching
            print("3️⃣ Fetching commits with optimization...")
            
            def progress_callback(current, total, status):
                print(f"   Progress: {current}/{total} - {status}")
            
            commits_by_fork = await commit_fetcher.fetch_commits_for_qualified_forks(
                qualified_forks,
                owner,
                repo,
                max_commits_per_fork=3,
                progress_callback=progress_callback,
            )
            
            print()
            print("4️⃣ Results Summary:")
            total_commits = sum(len(commits) for commits in commits_by_fork.values())
            forks_with_commits = sum(1 for commits in commits_by_fork.values() if commits)
            
            print(f"   Total forks processed: {len(commits_by_fork)}")
            print(f"   Forks with commits: {forks_with_commits}")
            print(f"   Total commits found: {total_commits}")
            print()
            
            # Step 5: Show some example results
            print("5️⃣ Example Results:")
            count = 0
            for fork_name, commits in commits_by_fork.items():
                if commits and count < 3:  # Show first 3 forks with commits
                    print(f"   📁 {fork_name}:")
                    for commit in commits[:2]:  # Show first 2 commits
                        print(f"      • {commit.short_sha}: {commit.message}")
                    if len(commits) > 2:
                        print(f"      ... and {len(commits) - 2} more commits")
                    count += 1
            
            if count == 0:
                print("   No forks with commits found in this repository")
            
            print()
            print("✅ Demonstration completed successfully!")
            
        except Exception as e:
            print(f"❌ Error during demonstration: {e}")
            print("   This might be due to API rate limits or network issues")


async def demonstrate_with_mock_data():
    """Demonstrate optimization with mock data when no GitHub token is available."""
    print("📝 Mock Data Demonstration")
    print("-" * 30)
    
    # Create mock fork data
    fork_no_commits = ForkQualificationMetrics(
        id=1,
        name="old-fork",
        full_name="user1/old-fork",
        owner="user1",
        html_url="https://github.com/user1/old-fork",
        stargazers_count=2,
        forks_count=0,
        watchers_count=2,
        size=100,
        language="Python",
        topics=["python"],
        open_issues_count=0,
        created_at=datetime(2023, 1, 1, 12, 0, 0),
        updated_at=datetime(2023, 1, 1, 12, 0, 0),
        pushed_at=datetime(2023, 1, 1, 12, 0, 0),  # Same as created = no commits
        archived=False,
        disabled=False,
        fork=True,
    )
    
    fork_has_commits = ForkQualificationMetrics(
        id=2,
        name="active-fork",
        full_name="user2/active-fork",
        owner="user2",
        html_url="https://github.com/user2/active-fork",
        stargazers_count=10,
        forks_count=2,
        watchers_count=12,
        size=200,
        language="JavaScript",
        topics=["javascript", "web"],
        open_issues_count=1,
        created_at=datetime(2023, 1, 1, 12, 0, 0),
        updated_at=datetime(2023, 1, 2, 12, 0, 0),
        pushed_at=datetime(2023, 1, 3, 12, 0, 0),  # Later than created = has commits
        archived=False,
        disabled=False,
        fork=True,
    )
    
    print("Mock fork data created:")
    print(f"  • {fork_no_commits.full_name}: {fork_no_commits.commits_ahead_status}")
    print(f"  • {fork_has_commits.full_name}: {fork_has_commits.commits_ahead_status}")
    print()
    
    # Show optimization potential
    print("Optimization Analysis:")
    print(f"  Total forks: 2")
    print(f"  Can skip: 1 (50.0%) - {fork_no_commits.full_name}")
    print(f"  Need analysis: 1 (50.0%) - {fork_has_commits.full_name}")
    print()
    print("API Call Optimization:")
    print("  Without optimization: 6 API calls (3 per fork)")
    print("  With optimization: 3 API calls (only for forks with commits)")
    print("  API calls saved: 3")
    print("  Efficiency gain: 50.0%")
    print()
    print("✅ Mock demonstration completed!")
    print("   Set GITHUB_TOKEN environment variable to see real data")


if __name__ == "__main__":
    asyncio.run(demonstrate_optimization())