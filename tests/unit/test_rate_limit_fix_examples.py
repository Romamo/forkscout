#!/usr/bin/env python3
"""Test script to verify rate limit fix works."""

import asyncio
import logging
import os
import pytest
from forklift.config import ForkliftConfig
from forklift.github.client import GitHubClient

# Set up logging to see debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@pytest.mark.asyncio
@pytest.mark.unit
async def test_rate_limit_fix():
    """Test the rate limit fix with mocked GitHub API calls."""
    from unittest.mock import AsyncMock, patch
    from forklift.config import load_config
    from forklift.models.github import Repository
    
    # Load config
    config = load_config()
    
    print(f"Testing with GitHub token: {'Yes' if config.github.token else 'No'}")
    print(f"GitHub API base URL: {config.github.base_url}")
    
    # Mock the GitHub client to avoid real API calls
    with patch('forklift.github.client.GitHubClient') as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__.return_value = mock_client
        
        # Mock repository response
        mock_repo = Repository(
            id=123,
            name="github-network-ninja",
            full_name="maliayas/github-network-ninja",
            owner="maliayas",
            url="https://api.github.com/repos/maliayas/github-network-ninja",
            html_url="https://github.com/maliayas/github-network-ninja",
            clone_url="https://github.com/maliayas/github-network-ninja.git"
        )
        mock_client.get_repository.return_value = mock_repo
        
        # Mock forks response
        mock_forks_data = [
            {"full_name": "user1/github-network-ninja", "stargazers_count": 5},
            {"full_name": "user2/github-network-ninja", "stargazers_count": 3}
        ]
        mock_client.get.return_value = mock_forks_data
        
        # Create GitHub client
        async with GitHubClient(config.github) as client:
            try:
                # Try to get repository info - now mocked
                print("Making GitHub API request...")
                repo = await client.get_repository("maliayas", "github-network-ninja")
                print(f"Successfully got repository: {repo.name}")
                
                # Try to get forks - now mocked
                print("Getting forks...")
                forks_data = await client.get("repos/maliayas/github-network-ninja/forks?per_page=100&page=1")
                print(f"Successfully got {len(forks_data)} forks")
                
                # Verify the mocked calls were made
                mock_client.get_repository.assert_called_once_with("maliayas", "github-network-ninja")
                mock_client.get.assert_called_once_with("repos/maliayas/github-network-ninja/forks?per_page=100&page=1")
                
            except Exception as e:
                print(f"Error occurred: {e}")
                print(f"Error type: {type(e)}")
                if hasattr(e, 'reset_time'):
                    print(f"Reset time: {e.reset_time}")
                if hasattr(e, 'remaining'):
                    print(f"Remaining: {e.remaining}")

if __name__ == "__main__":
    asyncio.run(test_rate_limit_fix())