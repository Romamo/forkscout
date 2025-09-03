#!/usr/bin/env python3
"""Debug script to test behind commits functionality."""

import asyncio
import sys
from forklift.github.client import GitHubClient
from forklift.config.settings import load_config
from forklift.display.repository_display_service import RepositoryDisplayService
from rich.console import Console

async def debug_behind_commits():
    """Debug the behind commits functionality step by step."""
    config = load_config()
    console = Console()
    
    async with GitHubClient(config.github) as client:
        print("🔍 Debugging Behind Commits Functionality")
        print("=" * 60)
        
        # Step 1: Test the new batch method
        print("\n1. Testing get_commits_ahead_behind_batch method:")
        fork_data_list = [('GreatBots', 'YouTube_bot_telegram')]
        
        batch_result = await client.get_commits_ahead_behind_batch(
            fork_data_list, 'sanila2007', 'youtube-bot-telegram'
        )
        
        for fork_key, counts in batch_result.items():
            print(f"   {fork_key}:")
            print(f"     ahead_by: {counts['ahead_by']}")
            print(f"     behind_by: {counts['behind_by']}")
        
        # Step 2: Test the display service with a mock fork data
        print("\n2. Testing display service formatting:")
        service = RepositoryDisplayService(client, console)
        
        # Create a mock fork data object
        class MockForkData:
            def __init__(self):
                self.exact_commits_ahead = 9
                self.exact_commits_behind = 11
        
        mock_fork = MockForkData()
        
        # Test the condition check
        ahead_is_int = isinstance(mock_fork.exact_commits_ahead, int)
        behind_is_int = isinstance(getattr(mock_fork, 'exact_commits_behind', 0), int)
        
        print(f"   exact_commits_ahead is int: {ahead_is_int}")
        print(f"   exact_commits_behind is int: {behind_is_int}")
        print(f"   Both conditions met: {ahead_is_int and behind_is_int}")
        
        if ahead_is_int and behind_is_int:
            commits_ahead = mock_fork.exact_commits_ahead
            commits_behind = getattr(mock_fork, 'exact_commits_behind', 0)
            commits_display = service.format_commits_compact(commits_ahead, commits_behind)
            print(f"   Formatted display: {commits_display}")
        
        # Step 3: Test with actual forklift show-forks call (limited)
        print("\n3. Testing actual forklift call:")
        try:
            result = await service.show_fork_data_detailed(
                'https://github.com/sanila2007/youtube-bot-telegram',
                max_forks=1,  # Just get the first fork
                disable_cache=True,
                show_commits=0,
                force_all_commits=False,
                ahead_only=False,
                csv_export=False
            )
            print(f"   Forklift call completed successfully")
            print(f"   Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        except Exception as e:
            print(f"   Error in forklift call: {e}")

if __name__ == "__main__":
    asyncio.run(debug_behind_commits())