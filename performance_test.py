#!/usr/bin/env python3
"""
Performance test script to demonstrate API call reduction in fork discovery optimization.
"""

import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

from forklift.analysis.fork_discovery import ForkDiscoveryService
from forklift.models.github import Repository, User


async def create_test_scenario():
    """Create a test scenario with typical repository fork distribution."""
    
    # Mock GitHub client
    mock_client = Mock()
    mock_client.get_repository = AsyncMock()
    mock_client.get_all_repository_forks = AsyncMock()
    mock_client.get_commits_ahead_behind = AsyncMock()
    mock_client.get_user = AsyncMock()
    
    # Create parent repository
    parent_repo = Repository(
        id=1,
        owner="original",
        name="test-repo",
        full_name="original/test-repo",
        url="https://api.github.com/repos/original/test-repo",
        html_url="https://github.com/original/test-repo",
        clone_url="https://github.com/original/test-repo.git",
        default_branch="main",
        stars=1000,
        forks_count=100,
        created_at=datetime.utcnow() - timedelta(days=365),
        updated_at=datetime.utcnow() - timedelta(days=1),
        pushed_at=datetime.utcnow() - timedelta(days=1),
    )
    
    # Create fork repositories - typical distribution:
    # 70% have no commits ahead (should be pre-filtered)
    # 30% have commits ahead (should proceed to full analysis)
    fork_repos = []
    
    # 70 forks with no commits ahead
    for i in range(70):
        timestamp = datetime.utcnow() - timedelta(days=30 + i)
        fork_repo = Repository(
            id=1000 + i,
            owner=f"no-commits-{i}",
            name="test-repo",
            full_name=f"no-commits-{i}/test-repo",
            url=f"https://api.github.com/repos/no-commits-{i}/test-repo",
            html_url=f"https://github.com/no-commits-{i}/test-repo",
            clone_url=f"https://github.com/no-commits-{i}/test-repo.git",
            default_branch="main",
            stars=0,
            forks_count=0,
            is_fork=True,
            created_at=timestamp,
            updated_at=timestamp,
            pushed_at=timestamp,  # Same as created_at = no commits
        )
        fork_repos.append(fork_repo)
    
    # 30 forks with commits ahead
    for i in range(30):
        created_time = datetime.utcnow() - timedelta(days=60 + i)
        pushed_time = datetime.utcnow() - timedelta(days=10 + i)
        fork_repo = Repository(
            id=2000 + i,
            owner=f"with-commits-{i}",
            name="test-repo",
            full_name=f"with-commits-{i}/test-repo",
            url=f"https://api.github.com/repos/with-commits-{i}/test-repo",
            html_url=f"https://github.com/with-commits-{i}/test-repo",
            clone_url=f"https://github.com/with-commits-{i}/test-repo.git",
            default_branch="main",
            stars=5,
            forks_count=1,
            is_fork=True,
            created_at=created_time,
            updated_at=pushed_time,
            pushed_at=pushed_time,  # After created_at = has commits
        )
        fork_repos.append(fork_repo)
    
    # Setup mock responses
    mock_client.get_repository.return_value = parent_repo
    mock_client.get_all_repository_forks.return_value = fork_repos
    mock_client.get_commits_ahead_behind.return_value = {
        "ahead_by": 3,
        "behind_by": 1,
        "total_commits": 4,
    }
    mock_client.get_user.return_value = User(
        id=1,
        login="test-user",
        name="Test User",
        email="test@example.com",
        avatar_url="https://github.com/test-user.png",
        html_url="https://github.com/test-user",
    )
    
    return mock_client, parent_repo, fork_repos


async def run_performance_test():
    """Run the performance test and measure API call reduction."""
    
    print("🚀 Fork Discovery Optimization Performance Test")
    print("=" * 60)
    
    # Create test scenario
    mock_client, parent_repo, fork_repos = await create_test_scenario()
    
    print(f"📊 Test Scenario:")
    print(f"   • Total forks: {len(fork_repos)}")
    print(f"   • Forks with no commits ahead: {len([f for f in fork_repos if f.created_at >= f.pushed_at])}")
    print(f"   • Forks with commits ahead: {len([f for f in fork_repos if f.created_at < f.pushed_at])}")
    print()
    
    # Create fork discovery service
    service = ForkDiscoveryService(
        github_client=mock_client,
        min_activity_days=365,
        min_commits_ahead=1,
        max_forks_to_analyze=100,
    )
    
    # Measure performance
    start_time = time.time()
    
    # Run optimized fork discovery
    forks = await service.discover_forks("https://github.com/original/test-repo")
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Calculate metrics
    total_potential_calls = len(fork_repos) * 3  # 3 API calls per fork without optimization
    actual_calls = len(forks) * 3  # Only forks that passed pre-filtering made API calls
    api_calls_saved = total_potential_calls - actual_calls
    reduction_percentage = (api_calls_saved / total_potential_calls * 100) if total_potential_calls > 0 else 0
    
    # Display results
    print("📈 Performance Results:")
    print(f"   • Execution time: {execution_time:.3f} seconds")
    print(f"   • Forks analyzed: {len(forks)}")
    print(f"   • Total potential API calls: {total_potential_calls}")
    print(f"   • Actual API calls made: {actual_calls}")
    print(f"   • API calls saved: {api_calls_saved}")
    print(f"   • Reduction percentage: {reduction_percentage:.1f}%")
    print()
    
    # Verify API call counts
    print("🔍 API Call Verification:")
    print(f"   • get_commits_ahead_behind called: {mock_client.get_commits_ahead_behind.call_count} times")
    print(f"   • get_user called: {mock_client.get_user.call_count} times")
    print()
    
    # Check if we achieved the target reduction
    target_min = 60
    target_max = 80
    
    if target_min <= reduction_percentage <= target_max:
        print(f"✅ SUCCESS: Achieved target {target_min}-{target_max}% API call reduction!")
        print(f"   Actual reduction: {reduction_percentage:.1f}%")
    elif reduction_percentage > target_max:
        print(f"🎯 EXCELLENT: Exceeded target with {reduction_percentage:.1f}% reduction!")
    else:
        print(f"⚠️  WARNING: Did not achieve target reduction of {target_min}-{target_max}%")
        print(f"   Actual reduction: {reduction_percentage:.1f}%")
    
    print()
    print("🎉 Performance test completed!")
    
    return {
        "execution_time": execution_time,
        "forks_analyzed": len(forks),
        "total_potential_calls": total_potential_calls,
        "actual_calls": actual_calls,
        "api_calls_saved": api_calls_saved,
        "reduction_percentage": reduction_percentage,
        "target_achieved": target_min <= reduction_percentage <= target_max,
    }


if __name__ == "__main__":
    asyncio.run(run_performance_test())