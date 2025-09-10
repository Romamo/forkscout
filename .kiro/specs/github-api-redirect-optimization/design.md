# Design Document

## Overview

This design addresses the GitHub API redirect logging issue where HTTP 301 redirects are being logged at INFO level, creating excessive log noise. The solution is simple: change redirect logging to DEBUG level and add proper repository not found handling.

## Architecture

### Current Issue

The httpx client logs redirects at INFO level:
```
INFO - HTTP Request: GET https://api.github.com/repos/tiangolo/fastapi/forks "HTTP/1.1 301 Moved Permanently"
INFO - HTTP Request: GET https://api.github.com/repositories/160919119/forks "HTTP/1.1 200 OK"
```

### Target Solution

Configure httpx logging to use DEBUG level for redirects:
```
DEBUG - HTTP Request: GET https://api.github.com/repos/tiangolo/fastapi/forks "HTTP/1.1 301 Moved Permanently"
DEBUG - HTTP Request: GET https://api.github.com/repositories/160919119/forks "HTTP/1.1 200 OK"
```

## Components and Interfaces

### 1. Logging Configuration

```python
import logging

# Configure httpx logger to use DEBUG level
def configure_github_client_logging():
    """Configure appropriate logging levels for GitHub API client."""
    # Set httpx logger to DEBUG level to reduce redirect noise
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.DEBUG)
    
    # Keep our application logger at INFO level
    app_logger = logging.getLogger("forkscout.github.client")
    app_logger.setLevel(logging.INFO)
```

### 2. Renamed Repository Handling

```python
class RepositoryRedirectHandler:
    """Handle repository redirects for renamed repositories."""
    
    async def handle_redirect(self, original_url: str, final_url: str) -> dict:
        """Extract repository information from redirect."""
        # Extract original owner/repo
        original_parts = self._extract_repo_parts(original_url)
        final_parts = self._extract_repo_parts(final_url)
        
        if original_parts != final_parts:
            logger.debug(f"Repository renamed: {original_parts[0]}/{original_parts[1]} -> {final_parts[0]}/{final_parts[1]}")
            
        return {
            'original_owner': original_parts[0],
            'original_repo': original_parts[1],
            'current_owner': final_parts[0],
            'current_repo': final_parts[1],
            'was_renamed': original_parts != final_parts
        }
    
    def _extract_repo_parts(self, url: str) -> tuple:
        """Extract owner/repo from GitHub API URL."""
        if "/repos/" in url:
            parts = url.split("/repos/")[1].split("/")
            if len(parts) >= 2:
                return (parts[0], parts[1])
        elif "/repositories/" in url:
            # Handle numeric repository IDs from redirects
            repo_id = url.split("/repositories/")[1].split("/")[0]
            return ("unknown", repo_id)
        return ("unknown", "unknown")
```

### 3. Repository Not Found Handling

```python
class RepositoryNotFoundError(GitHubAPIError):
    """Raised when repository cannot be found."""
    pass

async def _handle_404_response(self, response: httpx.Response, url: str) -> None:
    """Handle 404 responses with immediate stop."""
    if "/repos/" in url:
        # Extract owner/repo from URL
        parts = url.split("/repos/")[1].split("/")
        if len(parts) >= 2:
            owner, repo = parts[0], parts[1]
            error_msg = f"Repository {owner}/{repo} not found"
            raise RepositoryNotFoundError(error_msg)
    
    raise RepositoryNotFoundError("Repository not found")
```

## Implementation

### Enhanced GitHub Client Implementation

```python
class GitHubClient:
    def __init__(self, config: GitHubConfig):
        # Existing initialization...
        self.redirect_handler = RepositoryRedirectHandler()
        
        # Configure logging levels
        self._configure_logging()
    
    def _configure_logging(self):
        """Configure appropriate logging levels."""
        # Reduce httpx redirect noise
        logging.getLogger("httpx").setLevel(logging.DEBUG)
    
    async def get_repository(self, owner: str, repo: str) -> Repository:
        """Get repository with redirect handling."""
        url = f"/repos/{owner}/{repo}"
        
        # Track original URL for redirect detection
        original_url = self._client.base_url + url
        
        try:
            response = await self._make_request("GET", url)
            
            # Check if we were redirected
            if len(response.history) > 0:
                redirect_info = await self.redirect_handler.handle_redirect(
                    str(response.history[0].url),
                    str(response.url)
                )
                
                if redirect_info['was_renamed']:
                    logger.info(f"Repository was renamed: {owner}/{repo} -> {redirect_info['current_owner']}/{redirect_info['current_repo']}")
            
            return Repository.from_api_response(response.json())
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                await self._handle_404_response(e.response, original_url)
            raise
    
    async def _make_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make request with proper error handling."""
        response = await self._client.request(method, url, **kwargs)
        response.raise_for_status()
        return response
```

## Testing Strategy

### Unit Tests

```python
def test_logging_configuration():
    """Test that httpx logger is set to DEBUG level."""
    client = GitHubClient(config)
    httpx_logger = logging.getLogger("httpx")
    assert httpx_logger.level == logging.DEBUG

async def test_renamed_repository_handling():
    """Test handling of renamed repositories."""
    # Mock a redirect response
    with respx.mock:
        respx.get("https://api.github.com/repos/old-owner/old-repo").mock(
            return_value=httpx.Response(301, headers={"Location": "https://api.github.com/repos/new-owner/new-repo"})
        )
        respx.get("https://api.github.com/repos/new-owner/new-repo").mock(
            return_value=httpx.Response(200, json={"name": "new-repo", "owner": {"login": "new-owner"}})
        )
        
        repo = await client.get_repository("old-owner", "old-repo")
        assert repo.owner == "new-owner"
        assert repo.name == "new-repo"

async def test_repository_not_found_handling():
    """Test immediate stop on 404."""
    with pytest.raises(RepositoryNotFoundError):
        await client.get_repository("nonexistent", "repo")

def test_redirect_handler_extracts_repo_parts():
    """Test redirect handler extracts repository information correctly."""
    handler = RepositoryRedirectHandler()
    
    result = handler.handle_redirect(
        "https://api.github.com/repos/tiangolo/fastapi",
        "https://api.github.com/repositories/160919119"
    )
    
    assert result['original_owner'] == 'tiangolo'
    assert result['original_repo'] == 'fastapi'
    assert result['was_renamed'] == True
```

This is a minimal, focused solution that addresses the core issues without unnecessary complexity.