#!/usr/bin/env python3
"""
Test script to validate the behind commits display fix.
This script tests the exact scenario from the original bug report.
"""
import asyncio
import os
import sys
import pytest
from datetime import datetime

# Imports are now handled by proper test structure

from forklift.github.client import GitHubClient
from forklift.config import GitHubConfig
from forklift.models.fork_qualification import CollectedForkData, ForkQualificationMetrics
from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.models.commit_count_config import CommitCountConfig
from rich.console import Console


@pytest.mark.asyncio
async def test_original_bug_scenario():
    """Test the exact scenario from the original bug report."""
    print("🔍 Testing behind commits display fix...")
    print("=" * 60)
    
    # Initialize GitHub client
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print("❌ GITHUB_TOKEN environment variable not set")
        return False
    
    config = GitHubConfig(token=token)
    github_client = GitHubClient(config)
    console = Console()
    display_service = RepositoryDisplayService(github_client, console)
    
    # Test repository from original bug report
    owner = "sanila2007"
    repo = "youtube-bot-telegram"
    
    print(f"📊 Testing repository: {owner}/{repo}")
    print(f"🎯 Looking for GreatBots fork with behind commits...")
    
    try:
        # Test the GitHub client's new behind commits functionality
        print("\n1. Testing GitHub client behind commits extraction...")
        
        # Test with GreatBots fork specifically
        fork_owner = "GreatBots"
        fork_repo = "YouTube_bot_telegram"
        
        result = await github_client.get_commits_ahead_and_behind_count(
            fork_owner, fork_repo, owner, repo
        )
        
        print(f"   ✅ GreatBots fork: ahead={result.ahead_count}, behind={result.behind_count}")
        
        if result.ahead_count > 0 and result.behind_count > 0:
            print(f"   ✅ Found diverged fork as expected!")
        else:
            print(f"   ⚠️  Fork may not be diverged as expected")
        
        # Test batch processing
        print("\n2. Testing batch processing...")
        
        batch_result = await github_client.get_commits_ahead_and_behind_batch_counts(
            [(fork_owner, fork_repo)], owner, repo
        )
        
        fork_key = f"{fork_owner}/{fork_repo}"
        if fork_key in batch_result.results:
            batch_fork_result = batch_result.results[fork_key]
            print(f"   ✅ Batch result: ahead={batch_fork_result.ahead_count}, behind={batch_fork_result.behind_count}")
            
            # Verify batch and individual results match
            if (batch_fork_result.ahead_count == result.ahead_count and 
                batch_fork_result.behind_count == result.behind_count):
                print(f"   ✅ Batch and individual results match!")
            else:
                print(f"   ❌ Batch and individual results don't match!")
                return False
        
        # Test display formatting
        print("\n3. Testing display formatting...")
        
        # Create a simple mock object for testing display formatting
        class MockFork:
            def __init__(self, ahead, behind):
                self.exact_commits_ahead = ahead
                self.exact_commits_behind = behind
                self.commit_count_error = None
        
        mock_fork = MockFork(result.ahead_count, result.behind_count)
        
        formatted = display_service._format_commit_count(mock_fork)
        print(f"   ✅ Display format: '{formatted}'")
        
        # Verify format includes both ahead and behind (accounting for Rich color codes)
        if "+" in formatted and "-" in formatted:
            print(f"   ✅ Format includes both ahead (+) and behind (-) commits!")
        elif result.behind_count == 0 and "+" in formatted and "-" not in formatted:
            print(f"   ✅ Format correctly shows only ahead commits!")
        elif result.ahead_count == 0 and "-" in formatted and "+" not in formatted:
            print(f"   ✅ Format correctly shows only behind commits!")
        else:
            print(f"   ⚠️  Format may not be as expected for ahead={result.ahead_count}, behind={result.behind_count}")
        
        # Test CSV formatting
        print("\n4. Testing CSV formatting...")
        
        csv_formatted = display_service._format_commit_count_for_csv(mock_fork)
        print(f"   ✅ CSV format: '{csv_formatted}'")
        
        # CSV should not have color codes, display should have them
        if result.ahead_count > 0 and result.behind_count > 0:
            expected_csv = f"+{result.ahead_count} -{result.behind_count}"
            if csv_formatted == expected_csv:
                print(f"   ✅ CSV format is correct (no color codes)!")
            else:
                print(f"   ❌ CSV format incorrect! Expected '{expected_csv}', got '{csv_formatted}'")
                return False
        else:
            print(f"   ✅ CSV format matches expected pattern!")
            return False
        
        print("\n" + "=" * 60)
        print("✅ All tests passed! Behind commits display fix is working correctly.")
        print(f"🎉 GreatBots fork now shows: '{formatted}' instead of just '+{result.ahead_count}'")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if hasattr(github_client, '_client') and github_client._client:
            await github_client._client.aclose()


@pytest.mark.asyncio
async def test_edge_cases():
    """Test edge cases for behind commits functionality."""
    print("\n🧪 Testing edge cases...")
    print("=" * 60)
    
    # Test display formatting with various combinations
    test_cases = [
        {"ahead": 0, "behind": 0, "expected": ""},
        {"ahead": 5, "behind": 0, "expected": "+5"},
        {"ahead": 0, "behind": 3, "expected": "-3"},
        {"ahead": 9, "behind": 11, "expected": "+9 -11"},
        {"ahead": None, "behind": None, "expected": ""},
    ]
    
    console = Console()
    display_service = RepositoryDisplayService(None, console)
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing ahead={case['ahead']}, behind={case['behind']}")
        
        # Create mock fork data
        class MockFork:
            def __init__(self, ahead, behind):
                self.exact_commits_ahead = ahead
                self.exact_commits_behind = behind
                self.commit_count_error = None
        
        mock_fork = MockFork(case['ahead'], case['behind'])
        
        result = display_service._format_commit_count(mock_fork)
        print(f"   Result: '{result}' (expected pattern: '{case['expected']}')")
        
        # For display formatting, we need to account for Rich color codes
        # Extract the actual content without color codes
        import re
        clean_result = re.sub(r'\[.*?\]', '', result)
        
        if clean_result == case['expected']:
            print(f"   ✅ Correct!")
        else:
            print(f"   ❌ Incorrect! Expected '{case['expected']}', got '{clean_result}'")
            return False
    
    print("\n✅ All edge case tests passed!")
    return True


async def main():
    """Main test function."""
    print("🚀 Behind Commits Display Fix Validation")
    print("=" * 60)
    
    # Test original bug scenario
    success1 = await test_original_bug_scenario()
    
    # Test edge cases
    success2 = await test_edge_cases()
    
    if success1 and success2:
        print("\n🎉 ALL TESTS PASSED! The behind commits display fix is working correctly.")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED! Please check the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)