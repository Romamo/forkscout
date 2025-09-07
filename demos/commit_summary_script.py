#!/usr/bin/env python3
"""
GitHub Commit Summarizer

This script fetches commit data from GitHub and generates AI-powered summaries.
It accepts GitHub commit URLs and uses the GitHub API to fetch commit details
and diffs, then uses OpenAI to generate human-readable summaries.

Requirements:
- OPENAI_API_KEY environment variable (required)
- GITHUB_TOKEN environment variable (optional, but recommended for higher rate limits)

Usage:
    python test_summary.py <github_commit_url>

Example:
    python test_summary.py https://github.com/maliayas/github-network-ninja/commit/8ce0c7b8723c6b37000695d6980222da36af176e
"""

import os
import sys
import re
import asyncio
import aiohttp
from typing import Dict, Any, Optional
import openai

# Set your OpenAI API key as an environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")


class GitHubClient:
    """GitHub API client for fetching commit data."""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.session = None
    
    async def __aenter__(self):
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "commit-summary-tool"
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        
        self.session = aiohttp.ClientSession(headers=headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_commit(self, owner: str, repo: str, sha: str) -> Dict[str, Any]:
        """Fetch commit data from GitHub API."""
        url = f"{self.base_url}/repos/{owner}/{repo}/commits/{sha}"
        
        async with self.session.get(url) as response:
            if response.status == 404:
                raise ValueError(f"Commit {sha} not found in {owner}/{repo}. Please check the URL and ensure the repository is public.")
            elif response.status == 403:
                raise Exception("GitHub API rate limit exceeded or access denied. Consider setting GITHUB_TOKEN environment variable.")
            elif response.status != 200:
                error_text = await response.text()
                raise Exception(f"GitHub API error: {response.status} - {error_text}")
            
            return await response.json()
    
    async def get_commit_diff(self, owner: str, repo: str, sha: str) -> str:
        """Fetch commit diff in patch format from GitHub API."""
        url = f"{self.base_url}/repos/{owner}/{repo}/commits/{sha}"
        
        headers = {"Accept": "application/vnd.github.v3.diff"}
        async with self.session.get(url, headers=headers) as response:
            if response.status == 404:
                raise ValueError(f"Commit {sha} not found in {owner}/{repo}. Please check the URL and ensure the repository is public.")
            elif response.status == 403:
                raise Exception("GitHub API rate limit exceeded or access denied. Consider setting GITHUB_TOKEN environment variable.")
            elif response.status != 200:
                error_text = await response.text()
                raise Exception(f"GitHub API error: {response.status} - {error_text}")
            
            return await response.text()


def parse_github_commit_url(url: str) -> tuple[str, str, str]:
    """
    Parse GitHub commit URL to extract owner, repo, and commit hash.
    Example: https://github.com/maliayas/github-network-ninja/commit/8ce0c7b8723c6b37000695d6980222da36af176e
    Returns: (owner, repo_name, commit_hash)
    """
    pattern = r'https://github\.com/([^/]+)/([^/]+)/commit/([a-f0-9]+)'
    match = re.match(pattern, url)
    if not match:
        raise ValueError(f"Invalid GitHub commit URL: {url}")
    
    owner, repo_name, commit_hash = match.groups()
    return owner, repo_name, commit_hash


async def get_commit_data(owner: str, repo: str, sha: str) -> tuple[str, str]:
    """
    Fetch commit message and diff from GitHub API.
    Returns: (commit_message, diff_text)
    """
    async with GitHubClient() as github:
        # Fetch commit metadata
        commit_data = await github.get_commit(owner, repo, sha)
        commit_message = commit_data["commit"]["message"]
        
        # Fetch commit diff
        diff_text = await github.get_commit_diff(owner, repo, sha)
        
        return commit_message, diff_text


def summarize_commit(diff_text: str, commit_message: str) -> str:
    """Generate a human-readable summary of the commit using OpenAI."""
    # Truncate diff if it's too large (OpenAI has token limits)
    max_diff_chars = 8000  # Conservative limit to stay within token limits
    if len(diff_text) > max_diff_chars:
        diff_text = diff_text[:max_diff_chars] + "\n\n[... diff truncated due to size ...]"
        print(f"Warning: Diff was truncated to {max_diff_chars} characters due to size limits.")
    
    prompt = f"""
    You are a senior developer. Summarize the following Git commit into a clear, human-readable explanation.
    Include:
    - What changed
    - Why it changed
    - Potential side effects or considerations

    Commit message: {commit_message}

    Diff:
    {diff_text}
    """
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You summarize git commits into human-readable explanations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise Exception(f"OpenAI API error: {e}")


async def main():
    """Main function to process GitHub commit URL and generate summary."""
    if len(sys.argv) < 2:
        print("Usage: python test_summary.py <github_commit_url>")
        print("Example: python test_summary.py https://github.com/maliayas/github-network-ninja/commit/8ce0c7b8723c6b37000695d6980222da36af176e")
        sys.exit(1)

    commit_url = sys.argv[1]
    
    try:
        # Parse the GitHub commit URL
        owner, repo_name, commit_hash = parse_github_commit_url(commit_url)
        print(f"Analyzing commit {commit_hash} from {owner}/{repo_name}")
        
        # Fetch commit data from GitHub API
        commit_message, diff_text = await get_commit_data(owner, repo_name, commit_hash)
        
        print(f"\nCommit Message: {commit_message}")
        print(f"Diff size: {len(diff_text)} characters")
        
        # Generate AI summary
        print("\nGenerating summary...")
        summary = summarize_commit(diff_text, commit_message)
        
        print("\n=== Commit Summary ===\n")
        print(summary)
        
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is required")
        sys.exit(1)
    
    # Run the async main function
    asyncio.run(main())
