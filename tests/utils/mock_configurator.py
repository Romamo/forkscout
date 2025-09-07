"""Mock configuration utilities to fix remaining mock issues."""

import asyncio
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, Mock, MagicMock, patch
import httpx
import respx
from datetime import datetime, timezone

from tests.utils.mock_helpers import (
    GitHubAPIMockHelper,
    AsyncMockHelper,
    HTTPXMockHelper,
    configure_async_mock_return_value,
    ensure_async_mock
)


class MockConfigurator:
    """Centralized mock configuration to ensure consistency across tests."""
    
    @staticmethod
    def configure_github_client_mock(mock_client: AsyncMock) -> AsyncMock:
        """Configure a GitHub client mock with proper async behavior."""
        # Ensure it's an AsyncMock
        mock_client = ensure_async_mock(mock_client)
        
        # Configure repository operations
        mock_client.get_repository.return_value = Mock(
            id=123456789,
            name="test-repo",
            full_name="testowner/test-repo",
            owner="testowner",
            private=False,
            html_url="https://github.com/testowner/test-repo",
            description="Test repository",
            fork=False,
            url="https://api.github.com/repos/testowner/test-repo",
            clone_url="https://github.com/testowner/test-repo.git",
            ssh_url="git@github.com:testowner/test-repo.git",
            stargazers_count=42,
            watchers_count=42,
            forks_count=5,
            open_issues_count=2,
            size=1024,
            default_branch="main",
            language="Python",
            topics=["python", "test"],
            created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2023, 12, 1, tzinfo=timezone.utc),
            pushed_at=datetime(2023, 12, 1, tzinfo=timezone.utc),
            archived=False,
            disabled=False
        )
        
        # Configure fork operations
        mock_client.get_repository_forks.return_value = [
            Mock(
                id=123456790,
                name="test-repo",
                full_name="fork1/test-repo",
                owner="fork1",
                fork=True,
                html_url="https://github.com/fork1/test-repo",
                stargazers_count=1,
                forks_count=0
            ),
            Mock(
                id=123456791,
                name="test-repo", 
                full_name="fork2/test-repo",
                owner="fork2",
                fork=True,
                html_url="https://github.com/fork2/test-repo",
                stargazers_count=3,
                forks_count=1
            )
        ]
        
        # Configure commit operations
        mock_client.get_recent_commits.return_value = [
            Mock(
                short_sha="abc1234",
                message="Test commit message",
                date=datetime(2023, 1, 1, tzinfo=timezone.utc)
            ),
            Mock(
                short_sha="def5678",
                message="Another test commit",
                date=datetime(2023, 1, 2, tzinfo=timezone.utc)
            )
        ]
        
        # Configure comparison operations
        mock_client.compare_commits.return_value = {
            "status": "ahead",
            "ahead_by": 3,
            "behind_by": 0,
            "total_commits": 3,
            "commits": [
                GitHubAPIMockHelper.create_commit_mock(sha=f"{i:040d}")
                for i in range(3)
            ]
        }
        
        # Configure rate limiting
        mock_client.get_rate_limit.return_value = Mock(
            remaining=4999,
            limit=5000,
            reset=datetime.now(timezone.utc).timestamp() + 3600
        )
        
        # Configure context manager behavior
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        return mock_client
    
    @staticmethod
    def configure_file_operations_mock() -> AsyncMock:
        """Configure file operations mock with proper async behavior."""
        mock_file = AsyncMock()
        
        # Configure async file operations
        mock_file.read.return_value = "mock file content"
        mock_file.write.return_value = None
        mock_file.close.return_value = None
        mock_file.flush.return_value = None
        
        # Configure context manager behavior
        mock_file.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file.__aexit__ = AsyncMock(return_value=None)
        
        return mock_file
    
    @staticmethod
    def configure_respx_github_api(
        owner: str = "testowner",
        repo: str = "test-repo",
        commits: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Configure respx mocks for GitHub API endpoints."""
        # Mock repository endpoint
        repo_data = GitHubAPIMockHelper.create_repository_mock(owner=owner, name=repo)
        respx.get(f"https://api.github.com/repos/{owner}/{repo}").mock(
            return_value=httpx.Response(200, json=repo_data)
        )
        
        # Mock commits endpoint
        if commits is None:
            commits = [
                GitHubAPIMockHelper.create_commit_mock(
                    sha="a1b2c3d4e5f6789012345678901234567890abcd",
                    message="Add user authentication system"
                ),
                GitHubAPIMockHelper.create_commit_mock(
                    sha="b2c3d4e5f6789012345678901234567890abcdef",
                    message="Fix bug in login validation that was causing issues"
                )
            ]
        
        respx.get(f"https://api.github.com/repos/{owner}/{repo}/commits").mock(
            return_value=httpx.Response(200, json=commits)
        )
        
        # Mock forks endpoint
        forks_data = [
            GitHubAPIMockHelper.create_repository_mock(
                owner="fork1", name=repo, fork=True
            ),
            GitHubAPIMockHelper.create_repository_mock(
                owner="fork2", name=repo, fork=True
            )
        ]
        respx.get(f"https://api.github.com/repos/{owner}/{repo}/forks").mock(
            return_value=httpx.Response(200, json=forks_data)
        )
        
        # Mock comparison endpoint
        comparison_data = GitHubAPIMockHelper.create_comparison_mock(
            ahead_by=3, behind_by=0, status="ahead"
        )
        respx.get(f"https://api.github.com/repos/{owner}/{repo}/compare/main...fork-branch").mock(
            return_value=httpx.Response(200, json=comparison_data)
        )
    
    @staticmethod
    def fix_async_mock_configuration(mock_obj: Mock) -> AsyncMock:
        """Fix common async mock configuration issues."""
        # Convert to AsyncMock if needed
        if not isinstance(mock_obj, AsyncMock):
            async_mock = AsyncMock(spec=mock_obj._spec_class if hasattr(mock_obj, '_spec_class') else None)
            
            # Copy configured attributes
            for attr in dir(mock_obj):
                if not attr.startswith('_') and not callable(getattr(mock_obj, attr, None)):
                    try:
                        setattr(async_mock, attr, getattr(mock_obj, attr))
                    except (AttributeError, TypeError):
                        pass
            
            mock_obj = async_mock
        
        # Ensure return values are properly awaitable
        if hasattr(mock_obj, 'return_value') and mock_obj.return_value is not None:
            if not asyncio.iscoroutine(mock_obj.return_value):
                original_return = mock_obj.return_value
                
                async def async_return():
                    return original_return
                
                mock_obj.return_value = async_return()
        
        # Configure side effects to be async if needed
        if hasattr(mock_obj, 'side_effect') and mock_obj.side_effect is not None:
            if callable(mock_obj.side_effect) and not asyncio.iscoroutinefunction(mock_obj.side_effect):
                original_side_effect = mock_obj.side_effect
                
                async def async_side_effect(*args, **kwargs):
                    result = original_side_effect(*args, **kwargs)
                    if asyncio.iscoroutine(result):
                        return await result
                    return result
                
                mock_obj.side_effect = async_side_effect
        
        return mock_obj
    
    @staticmethod
    def configure_display_service_mock(mock_service: AsyncMock) -> AsyncMock:
        """Configure display service mock with proper return values."""
        mock_service = ensure_async_mock(mock_service)
        
        # Configure show_fork_data method
        mock_service.show_fork_data.return_value = {
            "total_forks": 5,
            "displayed_forks": 3,
            "filtered_forks": 2,
            "processing_time": 1.5
        }
        
        # Configure show_fork_data_detailed method
        mock_service.show_fork_data_detailed.return_value = {
            "total_forks": 5,
            "displayed_forks": 3,
            "detailed_analysis": True,
            "processing_time": 2.1
        }
        
        # Configure other common methods
        mock_service.show_repository_details.return_value = None
        mock_service.list_forks_preview.return_value = {
            "preview_count": 10,
            "total_available": 25
        }
        
        return mock_service
    
    @staticmethod
    def ensure_proper_mock_interfaces():
        """Ensure all mocks have proper interfaces matching real objects."""
        # This can be extended to validate mock configurations
        pass


def apply_mock_fixes():
    """Apply comprehensive mock fixes across the test suite."""
    # This function can be called to apply fixes globally
    pass


# Decorator to automatically fix async mock issues
def fix_async_mocks(test_func):
    """Decorator to automatically fix async mock configuration issues."""
    def wrapper(*args, **kwargs):
        # Find AsyncMock objects in args and kwargs and fix them
        fixed_args = []
        for arg in args:
            if isinstance(arg, Mock):
                fixed_args.append(MockConfigurator.fix_async_mock_configuration(arg))
            else:
                fixed_args.append(arg)
        
        fixed_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, Mock):
                fixed_kwargs[key] = MockConfigurator.fix_async_mock_configuration(value)
            else:
                fixed_kwargs[key] = value
        
        return test_func(*fixed_args, **fixed_kwargs)
    
    return wrapper