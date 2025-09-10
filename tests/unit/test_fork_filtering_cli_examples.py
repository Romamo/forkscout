#!/usr/bin/env python3
"""Simple test to verify fork filtering with --detail flag works."""

import asyncio
import sys
import os
import pytest

# Imports are now handled by proper test structure

from forkscout.analysis.fork_commit_status_checker import ForkCommitStatusChecker
from forkscout.github.client import GitHubClient
from forkscout.config import GitHubConfig
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_fork_filtering():
    """Test fork filtering functionality."""
    print("Testing fork filtering with --detail flag...")
    
    # Create mock GitHub client
    github_config = GitHubConfig(token="ghp_1234567890abcdef1234567890abcdef12345678")
    github_client = AsyncMock(spec=GitHubClient)
    
    # Create fork status checker
    checker = ForkCommitStatusChecker(github_client)
    
    # Test with a fork that has no commits ahead
    github_client.get_repository.return_value = AsyncMock()
    github_client.get_repository.return_value.created_at = "2023-01-01T00:00:00Z"
    github_client.get_repository.return_value.pushed_at = "2023-01-01T00:00:00Z"  # Same time = no commits
    
    has_commits = await checker.has_commits_ahead("https://github.com/test/repo")
    print(f"Fork with no commits ahead: {has_commits}")
    assert has_commits is False
    
    # Test with a fork that has commits ahead
    github_client.get_repository.return_value.pushed_at = "2023-06-01T00:00:00Z"  # Later time = has commits
    
    has_commits = await checker.has_commits_ahead("https://github.com/test/repo2")
    print(f"Fork with commits ahead: {has_commits}")
    assert has_commits is True
    
    print("✅ Fork filtering tests passed!")


if __name__ == "__main__":
    asyncio.run(test_fork_filtering())