#!/usr/bin/env python3
"""
Demo script showing the behind commits display feature.
This script demonstrates how to use the behind commits functionality programmatically.
"""
import asyncio
import os
import sys

# Add src to path for imports
sys.path.insert(0, 'src')

from forklift.github.client import GitHubClient
from forklift.config import GitHubConfig
from forklift.display.repository_display_service import RepositoryDisplayService
from rich.console import Console


async def demo_behind_commits():
    """Demonstrate behind commits functionality."""
    print("🎯 Behind Commits Display Demo")
    print("=" * 50)
    
    # Check for GitHub token
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print("❌ Please set GITHUB_TOKEN environment variable")
        return
    
    # Initialize components
    config = GitHubConfig(token=token)
    github_client = GitHubClient(config)
    console = Console()
    
    try:
        print("\n1. Testing individual fork commit counts...")
        
        # Test with a known diverged fork
        result = await github_client.get_commits_ahead_and_behind_count(
            "GreatBots", "YouTube_bot_telegram",  # Fork
            "sanila2007", "youtube-bot-telegram"  # Parent
        )
        
        print(f"   GreatBots fork: {result.ahead_count} ahead, {result.behind_count} behind")
        
        print("\n2. Testing display formatting...")
        
        # Create mock fork data for different scenarios
        scenarios = [
            {"ahead": 9, "behind": 11, "desc": "Diverged fork (ahead and behind)"},
            {"ahead": 5, "behind": 0, "desc": "Ahead-only fork"},
            {"ahead": 0, "behind": 3, "desc": "Behind-only fork"},
            {"ahead": 0, "behind": 0, "desc": "Identical fork"},
        ]
        
        display_service = RepositoryDisplayService(github_client, console)
        
        for scenario in scenarios:
            # Create mock fork
            class MockFork:
                def __init__(self, ahead, behind):
                    self.exact_commits_ahead = ahead
                    self.exact_commits_behind = behind
                    self.commit_count_error = None
            
            mock_fork = MockFork(scenario["ahead"], scenario["behind"])
            
            # Format for display and CSV
            display_format = display_service._format_commit_count(mock_fork)
            csv_format = display_service._format_commit_count_for_csv(mock_fork)
            
            print(f"   {scenario['desc']}:")
            print(f"     Display: {display_format}")
            print(f"     CSV: '{csv_format}'")
        
        print("\n3. Testing batch processing...")
        
        # Test batch processing with multiple forks
        test_forks = [
            ("GreatBots", "YouTube_bot_telegram"),
            # Add more forks here if you want to test with other repositories
        ]
        
        batch_result = await github_client.get_commits_ahead_and_behind_batch_counts(
            test_forks, "sanila2007", "youtube-bot-telegram"
        )
        
        print(f"   Processed {len(batch_result.results)} forks")
        print(f"   API calls saved: {batch_result.parent_calls_saved}")
        
        for fork_key, result in batch_result.results.items():
            if result.error:
                print(f"   {fork_key}: Error - {result.error}")
            else:
                print(f"   {fork_key}: +{result.ahead_count} -{result.behind_count}")
        
        print("\n✅ Demo completed successfully!")
        print("\nTo see this in action with the CLI:")
        print("   forklift show-forks sanila2007/youtube-bot-telegram --detail --ahead-only")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if hasattr(github_client, '_client') and github_client._client:
            await github_client._client.aclose()


if __name__ == "__main__":
    asyncio.run(demo_behind_commits())