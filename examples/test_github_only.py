#!/usr/bin/env python3
"""
Test GitHub API functionality without OpenAI dependency
"""

import sys
import asyncio
from test_summary import GitHubClient, parse_github_commit_url, get_commit_data


async def test_github_functionality(commit_url: str):
    """Test GitHub API functionality without OpenAI."""
    try:
        # Parse the GitHub commit URL
        owner, repo_name, commit_hash = parse_github_commit_url(commit_url)
        print(f"✓ URL parsing successful: {owner}/{repo_name} - commit {commit_hash}")
        
        # Test GitHub API
        print("Fetching commit data from GitHub API...")
        commit_message, diff_text = await get_commit_data(owner, repo_name, commit_hash)
        
        print(f"✓ Commit message: {commit_message}")
        print(f"✓ Diff fetched: {len(diff_text)} characters")
        
        # Show first few lines of diff
        diff_lines = diff_text.split('\n')[:10]
        print("\nFirst 10 lines of diff:")
        for line in diff_lines:
            print(f"  {line}")
        
        print(f"\n✓ GitHub API test successful!")
        print(f"✓ The script is ready to use with OpenAI API key")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_github_only.py <github_commit_url>")
        print("Example: python test_github_only.py https://github.com/maliayas/github-network-ninja/commit/8ce0c7b8723c6b37000695d6980222da36af176e")
        sys.exit(1)

    commit_url = sys.argv[1]
    success = asyncio.run(test_github_functionality(commit_url))
    sys.exit(0 if success else 1)