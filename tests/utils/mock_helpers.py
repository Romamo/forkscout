"""Mock configuration helpers for test suite stabilization."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, MagicMock
import httpx


class GitHubAPIMockHelper:
    """Helper class for creating properly structured GitHub API mocks."""
    
    @staticmethod
    def create_repository_mock(
        owner: str = "testowner",
        name: str = "test-repo",
        **kwargs
    ) -> Dict[str, Any]:
        """Create a properly structured repository mock response."""
        default_data = {
            "id": 123456789,
            "name": name,
            "full_name": f"{owner}/{name}",
            "owner": {
                "login": owner,
                "id": 12345,
                "type": "User"
            },
            "private": False,
            "html_url": f"https://github.com/{owner}/{name}",
            "description": "Test repository",
            "fork": False,
            "url": f"https://api.github.com/repos/{owner}/{name}",
            "clone_url": f"https://github.com/{owner}/{name}.git",
            "ssh_url": f"git@github.com:{owner}/{name}.git",
            "stargazers_count": 42,
            "watchers_count": 42,
            "forks_count": 5,
            "open_issues_count": 2,
            "size": 1024,
            "default_branch": "main",
            "language": "Python",
            "topics": ["python", "test"],
            "license": {
                "key": "mit",
                "name": "MIT License",
                "spdx_id": "MIT"
            },
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-12-01T00:00:00Z",
            "pushed_at": "2023-12-01T00:00:00Z",
            "archived": False,
            "disabled": False
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def create_commit_mock(
        sha: str = "a" * 40,
        message: str = "Test commit message",
        author_name: str = "Test User",
        author_email: str = "test@example.com",
        date: str = "2023-01-01T00:00:00Z",
        **kwargs
    ) -> Dict[str, Any]:
        """Create a properly structured commit mock response."""
        default_data = {
            "sha": sha,
            "commit": {
                "message": message,
                "author": {
                    "name": author_name,
                    "email": author_email,
                    "date": date,
                },
                "committer": {
                    "name": author_name,
                    "email": author_email,
                    "date": date,
                },
                "tree": {
                    "sha": "b" * 40,
                    "url": f"https://api.github.com/repos/owner/repo/git/trees/{'b' * 40}"
                },
                "url": f"https://api.github.com/repos/owner/repo/git/commits/{sha}",
                "comment_count": 0
            },
            "url": f"https://api.github.com/repos/owner/repo/commits/{sha}",
            "html_url": f"https://github.com/owner/repo/commit/{sha}",
            "comments_url": f"https://api.github.com/repos/owner/repo/commits/{sha}/comments",
            "author": {
                "login": "testuser",
                "id": 12345,
                "type": "User"
            },
            "committer": {
                "login": "testuser",
                "id": 12345,
                "type": "User"
            },
            "parents": [
                {
                    "sha": "c" * 40,
                    "url": f"https://api.github.com/repos/owner/repo/commits/{'c' * 40}",
                    "html_url": f"https://github.com/owner/repo/commit/{'c' * 40}"
                }
            ],
            "stats": {
                "total": 10,
                "additions": 8,
                "deletions": 2
            },
            "files": [
                {
                    "sha": "d" * 40,
                    "filename": "test.py",
                    "status": "modified",
                    "additions": 8,
                    "deletions": 2,
                    "changes": 10,
                    "blob_url": f"https://github.com/owner/repo/blob/{sha}/test.py",
                    "raw_url": f"https://github.com/owner/repo/raw/{sha}/test.py",
                    "contents_url": f"https://api.github.com/repos/owner/repo/contents/test.py?ref={sha}",
                    "patch": "@@ -1,3 +1,3 @@\n-old line\n+new line"
                }
            ]
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def create_comparison_mock(
        ahead_by: int = 0,
        behind_by: int = 0,
        status: str = "identical",
        **kwargs
    ) -> Dict[str, Any]:
        """Create a properly structured comparison mock response."""
        default_data = {
            "url": "https://api.github.com/repos/owner/repo/compare/base...head",
            "html_url": "https://github.com/owner/repo/compare/base...head",
            "permalink_url": "https://github.com/owner/repo/compare/owner:base...owner:head",
            "diff_url": "https://github.com/owner/repo/compare/base...head.diff",
            "patch_url": "https://github.com/owner/repo/compare/base...head.patch",
            "base_commit": GitHubAPIMockHelper.create_commit_mock(sha="b" * 40),
            "merge_base_commit": GitHubAPIMockHelper.create_commit_mock(sha="m" * 40),
            "status": status,
            "ahead_by": ahead_by,
            "behind_by": behind_by,
            "total_commits": ahead_by,
            "commits": [
                GitHubAPIMockHelper.create_commit_mock(sha=f"{i:040d}")
                for i in range(ahead_by)
            ],
            "files": []
        }
        default_data.update(kwargs)
        return default_data


class AsyncMockHelper:
    """Helper class for creating properly configured async mocks."""
    
    @staticmethod
    def create_github_client_mock() -> AsyncMock:
        """Create a properly configured GitHub client mock."""
        mock_client = AsyncMock()
        
        # Configure common methods with realistic return values
        mock_client.get_repository.return_value = Mock(
            **GitHubAPIMockHelper.create_repository_mock()
        )
        
        mock_client.get_repository_forks.return_value = [
            Mock(**GitHubAPIMockHelper.create_repository_mock(
                owner="fork1", name="test-repo", fork=True
            )),
            Mock(**GitHubAPIMockHelper.create_repository_mock(
                owner="fork2", name="test-repo", fork=True
            ))
        ]
        
        mock_client.get_recent_commits.return_value = [
            Mock(
                short_sha="abc1234",
                message="Test commit message",
                date=datetime(2023, 1, 1, tzinfo=timezone.utc)
            )
        ]
        
        mock_client.compare_commits.return_value = GitHubAPIMockHelper.create_comparison_mock()
        
        # Configure context manager behavior
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        return mock_client
    
    @staticmethod
    def create_file_operation_mock() -> AsyncMock:
        """Create a properly configured file operation mock."""
        mock_file = AsyncMock()
        
        # Configure async file operations
        mock_file.read.return_value = "mock file content"
        mock_file.write.return_value = None
        mock_file.close.return_value = None
        
        # Configure context manager behavior
        mock_file.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file.__aexit__ = AsyncMock(return_value=None)
        
        return mock_file
    
    @staticmethod
    def create_openai_client_mock() -> AsyncMock:
        """Create a properly configured OpenAI client mock."""
        mock_client = AsyncMock()
        
        # Configure completion method
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="Mock AI response"))
        ]
        mock_response.usage = Mock(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        
        mock_client.chat.completions.create.return_value = mock_response
        
        return mock_client


class HTTPXMockHelper:
    """Helper class for creating properly configured httpx mocks."""
    
    @staticmethod
    def create_response_mock(
        status_code: int = 200,
        json_data: Optional[Dict[str, Any]] = None,
        text_data: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Mock:
        """Create a properly configured httpx Response mock."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = status_code
        mock_response.headers = headers or {}
        
        if json_data is not None:
            mock_response.json.return_value = json_data
        
        if text_data is not None:
            mock_response.text = text_data
        
        mock_response.raise_for_status.return_value = None
        if status_code >= 400:
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                f"HTTP {status_code}", request=Mock(), response=mock_response
            )
        
        return mock_response
    
    @staticmethod
    def create_client_mock() -> AsyncMock:
        """Create a properly configured httpx AsyncClient mock."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        
        # Configure default successful response
        mock_client.get.return_value = HTTPXMockHelper.create_response_mock()
        mock_client.post.return_value = HTTPXMockHelper.create_response_mock(201)
        mock_client.put.return_value = HTTPXMockHelper.create_response_mock()
        mock_client.delete.return_value = HTTPXMockHelper.create_response_mock(204)
        
        # Configure context manager behavior
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        return mock_client


def configure_async_mock_return_value(mock_obj: AsyncMock, return_value: Any) -> None:
    """Configure an AsyncMock to return a specific value."""
    if asyncio.iscoroutine(return_value):
        mock_obj.return_value = return_value
    else:
        # Create a coroutine that returns the value
        async def async_return():
            return return_value
        mock_obj.return_value = async_return()


def ensure_async_mock(mock_obj: Mock) -> AsyncMock:
    """Ensure a mock object is properly configured as an AsyncMock."""
    if not isinstance(mock_obj, AsyncMock):
        # Convert Mock to AsyncMock
        async_mock = AsyncMock(spec=mock_obj._spec_class if hasattr(mock_obj, '_spec_class') else None)
        
        # Copy over any configured attributes
        for attr_name in dir(mock_obj):
            if not attr_name.startswith('_') and hasattr(mock_obj, attr_name):
                try:
                    setattr(async_mock, attr_name, getattr(mock_obj, attr_name))
                except (AttributeError, TypeError):
                    pass
        
        return async_mock
    
    return mock_obj