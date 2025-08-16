"""GitHub link generation utilities."""

import re
from typing import Optional
from urllib.parse import urlparse


class GitHubLinkGenerator:
    """Generates and validates GitHub URLs for commits and repositories."""

    @staticmethod
    def generate_commit_url(owner: str, repo: str, commit_sha: str) -> str:
        """
        Generate a GitHub commit URL.
        
        Args:
            owner: Repository owner username
            repo: Repository name
            commit_sha: Commit SHA (can be full or abbreviated)
            
        Returns:
            Complete GitHub commit URL
            
        Raises:
            ValueError: If any parameter is empty or invalid
        """
        if not owner or not owner.strip():
            raise ValueError("Owner cannot be empty")
        if not repo or not repo.strip():
            raise ValueError("Repository name cannot be empty")
        if not commit_sha or not commit_sha.strip():
            raise ValueError("Commit SHA cannot be empty")
        
        # Clean parameters
        owner = owner.strip()
        repo = repo.strip()
        commit_sha = commit_sha.strip()
        
        # Validate commit SHA format (should be hexadecimal)
        if not re.match(r'^[a-fA-F0-9]+$', commit_sha):
            raise ValueError(f"Invalid commit SHA format: {commit_sha}")
        
        # Validate owner and repo names (GitHub username/repo name rules)
        if not re.match(r'^[a-zA-Z0-9._-]+$', owner):
            raise ValueError(f"Invalid owner name: {owner}")
        if not re.match(r'^[a-zA-Z0-9._-]+$', repo):
            raise ValueError(f"Invalid repository name: {repo}")
        
        return f"https://github.com/{owner}/{repo}/commit/{commit_sha}"
    
    @staticmethod
    def validate_github_url(url: str) -> bool:
        """
        Validate if a URL is a valid GitHub URL.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is a valid GitHub URL, False otherwise
        """
        if not url or not url.strip():
            return False
        
        try:
            parsed = urlparse(url.strip())
            return (
                parsed.scheme in ('http', 'https') and
                parsed.netloc == 'github.com' and
                len(parsed.path.split('/')) >= 3  # At least /owner/repo
            )
        except Exception:
            return False
    
    @staticmethod
    def validate_commit_url(url: str) -> bool:
        """
        Validate if a URL is a valid GitHub commit URL.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is a valid GitHub commit URL, False otherwise
        """
        if not GitHubLinkGenerator.validate_github_url(url):
            return False
        
        try:
            parsed = urlparse(url.strip())
            path_parts = parsed.path.strip('/').split('/')
            
            # Should be: owner/repo/commit/sha
            return (
                len(path_parts) == 4 and
                path_parts[2] == 'commit' and
                re.match(r'^[a-fA-F0-9]+$', path_parts[3])
            )
        except Exception:
            return False
    
    @staticmethod
    def format_clickable_link(url: str, text: Optional[str] = None) -> str:
        """
        Format a URL as a clickable link for terminal output.
        
        Args:
            url: URL to format
            text: Optional display text (defaults to URL)
            
        Returns:
            Formatted link string with ANSI escape codes for clickable links
        """
        if not url or not url.strip():
            return ""
        
        display_text = text or url
        # ANSI escape sequence for clickable links (OSC 8)
        return f"\033]8;;{url}\033\\{display_text}\033]8;;\033\\"
    
    @staticmethod
    def extract_repo_info_from_url(github_url: str) -> Optional[tuple[str, str]]:
        """
        Extract owner and repository name from a GitHub URL.
        
        Args:
            github_url: GitHub repository or commit URL
            
        Returns:
            Tuple of (owner, repo) if valid, None otherwise
        """
        if not GitHubLinkGenerator.validate_github_url(github_url):
            return None
        
        try:
            parsed = urlparse(github_url.strip())
            path_parts = parsed.path.strip('/').split('/')
            
            if len(path_parts) >= 2:
                return path_parts[0], path_parts[1]
        except Exception:
            pass
        
        return None