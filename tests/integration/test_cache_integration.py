"""Integration tests for cache system with real data flow."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from forkscout.display.repository_display_service import RepositoryDisplayService
from forkscout.models.cache import CacheConfig
from forkscout.models.github import Repository
from forkscout.storage.analysis_cache import AnalysisCacheManager


@pytest.mark.asyncio
async def test_repository_cache_roundtrip():
    """Test that cached repository data can be successfully reconstructed."""
    # Create a complete Repository object with all required fields
    original_repo = Repository(
        id=12345,
        owner="test_owner",
        name="test_repo",
        full_name="test_owner/test_repo",
        url="https://github.com/test_owner/test_repo",
        html_url="https://github.com/test_owner/test_repo",
        clone_url="https://github.com/test_owner/test_repo.git",
        default_branch="main",
        stars=100,
        forks_count=50,
        watchers_count=75,
        open_issues_count=5,
        size=1024,
        language="Python",
        description="Test repository",
        topics=["test", "python"],
        license_name="MIT",
        is_private=False,
        is_fork=False,
        is_archived=False,
        is_disabled=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        pushed_at=datetime.now()
    )

    # Mock GitHub client
    mock_github_client = AsyncMock()
    mock_github_client.get_repository.return_value = original_repo
    mock_github_client.get_repository_languages.return_value = {"Python": 100}
    mock_github_client.get_repository_topics.return_value = ["test", "python"]

    # Initialize cache manager with in-memory database
    config = CacheConfig(database_path=":memory:")
    cache_manager = AnalysisCacheManager(config=config)
    await cache_manager.initialize()

    try:
        # Create display service
        display_service = RepositoryDisplayService(
            github_client=mock_github_client,
            cache_manager=cache_manager
        )

        # First call - should cache the data
        with patch("builtins.print"):  # Suppress console output
            result1 = await display_service.show_repository_details("test_owner/test_repo")

        # Verify data was cached
        cached_data = await cache_manager.get_repository_metadata("test_owner", "test_repo")
        assert cached_data is not None

        # Second call - should use cached data without errors
        with patch("builtins.print"):  # Suppress console output
            result2 = await display_service.show_repository_details("test_owner/test_repo")

        # Verify both results are equivalent
        assert result1["repository"].name == result2["repository"].name
        assert result1["repository"].owner == result2["repository"].owner
        assert result1["repository"].full_name == result2["repository"].full_name

        # Verify GitHub client was only called once (second call used cache)
        mock_github_client.get_repository.assert_called_once()

    finally:
        await cache_manager.close()


@pytest.mark.asyncio
async def test_cache_validation_failure_fallback():
    """Test that cache validation failures gracefully fall back to API."""
    # Mock GitHub client
    mock_github_client = AsyncMock()
    original_repo = Repository(
        id=12345,
        owner="test_owner",
        name="test_repo",
        full_name="test_owner/test_repo",
        url="https://github.com/test_owner/test_repo",
        html_url="https://github.com/test_owner/test_repo",
        clone_url="https://github.com/test_owner/test_repo.git"
    )
    mock_github_client.get_repository.return_value = original_repo
    mock_github_client.get_repository_languages.return_value = {"Python": 100}
    mock_github_client.get_repository_topics.return_value = ["test"]

    # Initialize cache manager and inject invalid cached data
    config = CacheConfig(database_path=":memory:")
    cache_manager = AnalysisCacheManager(config=config)
    await cache_manager.initialize()

    try:
        # Inject invalid cached data (missing required fields)
        invalid_cached_data = {
            "repository_data": {
                "name": "test_repo",
                "owner": "test_owner",
                "full_name": "test_owner/test_repo",
                "description": "Test repo",
                # Missing: url, html_url, clone_url (required fields)
                "language": "Python",
                "stars": 100,
                "forks_count": 50,
                "watchers_count": 75,
                "open_issues_count": 5,
                "size": 1024,
                "license_name": "MIT",
                "default_branch": "main",
                "is_private": False,
                "is_fork": False,
                "is_archived": False,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "pushed_at": "2024-01-01T00:00:00"
            },
            "languages": {"Python": 100},
            "topics": ["test"],
            "primary_language": "Python",
            "license": "MIT",
            "last_activity": "2024-01-01T00:00:00",
            "created": "2024-01-01T00:00:00",
            "updated": "2024-01-01T00:00:00"
        }

        await cache_manager.cache_repository_metadata(
            "test_owner", "test_repo", invalid_cached_data
        )

        # Create display service
        display_service = RepositoryDisplayService(
            github_client=mock_github_client,
            cache_manager=cache_manager
        )

        # Call should succeed despite invalid cached data
        with patch("builtins.print"):  # Suppress console output
            result = await display_service.show_repository_details("test_owner/test_repo")

        # Verify it fell back to API call
        mock_github_client.get_repository.assert_called_once()

        # Verify result is valid
        assert result["repository"].name == "test_repo"
        assert result["repository"].url is not None  # Should have URL from API

    finally:
        await cache_manager.close()
