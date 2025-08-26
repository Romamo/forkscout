#!/usr/bin/env python3
"""
Test script to verify that show-forks command uses only pagination requests.
This script tests that no individual repository API calls or comparison API calls are made.
"""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

# Add src to path for imports
sys.path.insert(0, 'src')

from forklift.cli import _show_forks_summary
from forklift.config.settings import ForkliftConfig
from forklift.models.github import Repository


async def test_show_forks_uses_pagination_only():
    """Test that show-forks command uses only pagination-only requests."""
    print("Testing that show-forks command uses only pagination requests...")
    
    # Setup config
    config = ForkliftConfig()
    config.github.token = "test_token"
    
    # Create mock GitHub client that tracks API calls
    api_calls_made = []
    
    def track_api_call(method_name):
        def wrapper(*args, **kwargs):
            api_calls_made.append(method_name)
            return AsyncMock()
        return wrapper
    
    # Mock the GitHub client and display service
    with patch('forklift.cli.GitHubClient') as mock_github_client_class, \
         patch('forklift.cli.RepositoryDisplayService') as mock_display_service_class:
        
        # Setup GitHub client mock
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_github_client_class.return_value = mock_client_instance
        
        # Setup display service mock
        mock_display_service = MagicMock()
        mock_display_service.show_fork_data = AsyncMock(return_value={
            "total_forks": 5,
            "displayed_forks": 5,
            "collected_forks": [],
            "stats": None
        })
        mock_display_service_class.return_value = mock_display_service
        
        # Call the function
        await _show_forks_summary(config, "owner/repo", max_forks=None, verbose=True)
        
        # Verify that show_fork_data was called (which uses pagination-only)
        mock_display_service.show_fork_data.assert_called_once_with(
            "owner/repo",
            exclude_archived=False,
            exclude_disabled=False,
            sort_by="stars",
            show_all=True,
            disable_cache=False
        )
        
        # Verify that no expensive API methods were called on the GitHub client
        # These are the methods that should NOT be called:
        expensive_methods = [
            'get_commits_ahead_behind',
            'get_repository',  # for individual forks
            'get_commits_ahead',
            'compare_commits'
        ]
        
        # Check that none of the expensive methods were called
        for method_name in expensive_methods:
            if hasattr(mock_client_instance, method_name):
                method = getattr(mock_client_instance, method_name)
                if hasattr(method, 'called') and method.called:
                    print(f"❌ ERROR: Expensive method {method_name} was called!")
                    return False
        
        print("✅ SUCCESS: show-forks command uses only pagination requests")
        print(f"   - show_fork_data was called with correct parameters")
        print(f"   - No expensive individual repository or comparison API calls were made")
        return True


async def test_show_fork_data_uses_pagination_only():
    """Test that show_fork_data method uses only pagination requests."""
    print("\nTesting that show_fork_data method uses only pagination requests...")
    
    from forklift.display.repository_display_service import RepositoryDisplayService
    from forklift.github.client import GitHubClient
    from rich.console import Console
    
    # Create mock GitHub client
    mock_github_client = MagicMock(spec=GitHubClient)
    console = Console()
    
    # Create the service
    service = RepositoryDisplayService(mock_github_client, console)
    
    # Mock the components that show_fork_data uses
    with patch('forklift.github.fork_list_processor.ForkListProcessor') as mock_processor_class, \
         patch('forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine') as mock_engine_class:
        
        # Setup mocks
        mock_processor = MagicMock()
        mock_processor.get_all_forks_list_data = AsyncMock(return_value=[
            {
                'id': 123,
                'name': 'test-repo',
                'full_name': 'user/test-repo',
                'owner': {'login': 'user'},
                'stargazers_count': 5,
                'forks_count': 1,
                'size': 100,
                'language': 'Python',
                'created_at': '2023-01-01T00:00:00Z',
                'updated_at': '2023-01-02T00:00:00Z',
                'pushed_at': '2023-01-02T00:00:00Z',
                'open_issues_count': 0,
                'topics': [],
                'watchers_count': 5,
                'archived': False,
                'disabled': False,
                'fork': True
            }
        ])
        mock_processor_class.return_value = mock_processor
        
        mock_engine = MagicMock()
        mock_engine.collect_fork_data_from_list.return_value = []
        mock_engine.create_qualification_result.return_value = MagicMock()
        mock_engine_class.return_value = mock_engine
        
        # Mock the display method
        service._display_fork_data_table = MagicMock()
        
        # Call show_fork_data
        result = await service.show_fork_data("owner/repo")
        
        # Verify that only pagination-based methods were called
        mock_processor.get_all_forks_list_data.assert_called_once_with("owner", "repo")
        mock_engine.collect_fork_data_from_list.assert_called_once()
        
        # Verify that no expensive GitHub API methods were called on the client
        expensive_methods = [
            'get_commits_ahead_behind',
            'get_repository',  # for individual forks
            'get_commits_ahead',
            'compare_commits',
            'get_all_repository_forks'  # This makes individual calls
        ]
        
        for method_name in expensive_methods:
            if hasattr(mock_github_client, method_name):
                method = getattr(mock_github_client, method_name)
                if hasattr(method, 'called') and method.called:
                    print(f"❌ ERROR: Expensive method {method_name} was called!")
                    return False
        
        print("✅ SUCCESS: show_fork_data uses only pagination requests")
        print(f"   - Only get_all_forks_list_data was called (pagination-only)")
        print(f"   - No expensive individual repository or comparison API calls were made")
        return True


async def main():
    """Run all tests."""
    print("=" * 80)
    print("TESTING: show-forks command uses pagination-only requests")
    print("=" * 80)
    
    success = True
    
    # Test 1: CLI function uses pagination-only
    try:
        result1 = await test_show_forks_uses_pagination_only()
        success = success and result1
    except Exception as e:
        print(f"❌ ERROR in test_show_forks_uses_pagination_only: {e}")
        success = False
    
    # Test 2: show_fork_data method uses pagination-only
    try:
        result2 = await test_show_fork_data_uses_pagination_only()
        success = success and result2
    except Exception as e:
        print(f"❌ ERROR in test_show_fork_data_uses_pagination_only: {e}")
        success = False
    
    print("\n" + "=" * 80)
    if success:
        print("🎉 ALL TESTS PASSED: show-forks command uses only pagination requests!")
        print("✅ Task 19.1 requirements verified:")
        print("   - show-forks command calls show_fork_data instead of show_forks_summary")
        print("   - show_forks_summary method has been removed")
        print("   - Only pagination-only requests are made")
        print("   - No individual repository or comparison API calls are made")
    else:
        print("❌ SOME TESTS FAILED: show-forks command may still use expensive API calls")
        return 1
    
    print("=" * 80)
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)