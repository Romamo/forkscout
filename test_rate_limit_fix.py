#!/usr/bin/env python3
"""Test script to verify rate limit fix works."""

import asyncio
import logging
import os
from forklift.config import ForkliftConfig
from forklift.github.client import GitHubClient

# Set up logging to see debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_rate_limit_fix():
    """Test the rate limit fix with a real GitHub API call."""
    
    # Load config
    from forklift.config import load_config
    config = load_config()
    
    print(f"Testing with GitHub token: {'Yes' if config.github.token else 'No'}")
    print(f"GitHub API base URL: {config.github.base_url}")
    
    # Create GitHub client
    async with GitHubClient(config.github) as client:
        try:
            # Try to get repository info - this should trigger rate limiting if we're at the limit
            print("Making GitHub API request...")
            repo = await client.get_repository("maliayas", "github-network-ninja")
            print(f"Successfully got repository: {repo.name}")
            
            # Try to get forks - this is what was failing before
            print("Getting forks...")
            forks_data = await client.get("repos/maliayas/github-network-ninja/forks?per_page=100&page=1")
            print(f"Successfully got {len(forks_data)} forks")
            
        except Exception as e:
            print(f"Error occurred: {e}")
            print(f"Error type: {type(e)}")
            if hasattr(e, 'reset_time'):
                print(f"Reset time: {e.reset_time}")
            if hasattr(e, 'remaining'):
                print(f"Remaining: {e.remaining}")

if __name__ == "__main__":
    asyncio.run(test_rate_limit_fix())