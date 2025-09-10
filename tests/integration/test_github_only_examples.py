#!/usr/bin/env python3
"""
Test GitHub API functionality integration test
"""

import os
import pytest
from forkscout.github.client import GitHubClient
from forkscout.config import GitHubConfig


@pytest.mark.asyncio
@pytest.mark.online
@pytest.mark.timeout(60)  # 60 second timeout for online tests
async def test_github_api_integration(commit_url: str):
    """Test GitHub API functionality integration."""
    # Skip if no GitHub token
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        pytest.skip("GITHUB_TOKEN not available")
    
    try:
        # Create GitHub client
        config = GitHubConfig(token=token)
        client = GitHubClient(config)
        
        # Test basic repository access
        repo = await client.get_repository("octocat", "Hello-World")
        assert repo is not None
        assert repo.name == "Hello-World"
        assert repo.owner == "octocat"
        
        # Test getting recent commits
        commits = await client.get_recent_commits("octocat", "Hello-World", count=5)
        assert len(commits) > 0
        assert all(commit.sha for commit in commits)
        
        print(f"✓ GitHub API integration test successful!")
        print(f"✓ Repository: {repo.full_name}")
        print(f"✓ Recent commits: {len(commits)}")
        
    except Exception as e:
        # Handle network errors gracefully
        if "timeout" in str(e).lower() or "network" in str(e).lower():
            pytest.skip(f"Network error during test: {e}")
        else:
            # Re-raise other errors
            raise


@pytest.mark.asyncio
@pytest.mark.online
@pytest.mark.timeout(60)  # 60 second timeout for online tests
async def test_github_repository_forks():
    """Test GitHub repository forks functionality."""
    # Skip if no GitHub token
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        pytest.skip("GITHUB_TOKEN not available")
    
    try:
        # Create GitHub client
        config = GitHubConfig(token=token)
        client = GitHubClient(config)
        
        # Test getting repository forks
        forks = await client.get_repository_forks("octocat", "Hello-World", per_page=5)
        assert isinstance(forks, list)
        
        print(f"✓ Repository forks test successful!")
        print(f"✓ Forks found: {len(forks)}")
        
    except Exception as e:
        # Handle network errors gracefully
        if "timeout" in str(e).lower() or "network" in str(e).lower():
            pytest.skip(f"Network error during test: {e}")
        else:
            # Re-raise other errors
            raise