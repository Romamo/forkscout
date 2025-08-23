"""Contract tests to ensure cache serialization/deserialization works correctly."""

import pytest
from datetime import datetime
from forklift.models.github import Repository
from forklift.models.cache import CacheConfig
from forklift.storage.analysis_cache import AnalysisCacheManager
from forklift.display.repository_display_service import RepositoryDisplayService
from unittest.mock import AsyncMock


@pytest.mark.asyncio
class TestCacheContracts:
    """Contract tests for cache data integrity."""
    
    async def test_repository_cache_contract(self):
        """Test that Repository objects can be cached and reconstructed without data loss."""
        # Create a complete Repository object
        original_repo = Repository(
            id=12345,
            owner="contract_test",
            name="test_repo",
            full_name="contract_test/test_repo",
            url="https://github.com/contract_test/test_repo",
            html_url="https://github.com/contract_test/test_repo",
            clone_url="https://github.com/contract_test/test_repo.git",
            default_branch="main",
            stars=100,
            forks_count=50,
            watchers_count=75,
            open_issues_count=5,
            size=1024,
            language="Python",
            description="Contract test repository",
            topics=["test", "contract"],
            license_name="MIT",
            is_private=False,
            is_fork=False,
            is_archived=False,
            is_disabled=False,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 2, 12, 0, 0),
            pushed_at=datetime(2024, 1, 3, 12, 0, 0)
        )
        
        # Initialize cache with in-memory database
        config = CacheConfig(database_path=":memory:")
        cache_manager = AnalysisCacheManager(config=config)
        await cache_manager.initialize()
        
        try:
            # Mock GitHub client to return our test repository
            mock_github_client = AsyncMock()
            mock_github_client.get_repository.return_value = original_repo
            mock_github_client.get_repository_languages.return_value = {"Python": 80, "JavaScript": 20}
            mock_github_client.get_repository_topics.return_value = ["test", "contract"]
            
            # Create display service
            display_service = RepositoryDisplayService(
                github_client=mock_github_client,
                cache_manager=cache_manager
            )
            
            # First call - caches the data
            result1 = await display_service.show_repository_details("contract_test/test_repo")
            
            # Verify GitHub API was called
            assert mock_github_client.get_repository.call_count == 1
            
            # Reset mock to verify cache is used
            mock_github_client.reset_mock()
            
            # Second call - should use cache
            result2 = await display_service.show_repository_details("contract_test/test_repo")
            
            # Verify GitHub API was NOT called (cache was used)
            assert mock_github_client.get_repository.call_count == 0
            
            # Contract: All critical fields must be preserved
            repo1 = result1["repository"]
            repo2 = result2["repository"]
            
            critical_fields = [
                "name", "owner", "full_name", "url", "html_url", "clone_url",
                "stars", "forks_count", "language", "description"
            ]
            
            for field in critical_fields:
                assert getattr(repo1, field) == getattr(repo2, field), f"Field {field} not preserved in cache"
            
            # Contract: Additional data must be preserved
            assert result1["languages"] == result2["languages"]
            assert result1["topics"] == result2["topics"]
            
        finally:
            await cache_manager.close()
    
    async def test_cache_handles_model_evolution(self):
        """Test that cache gracefully handles model schema changes."""
        config = CacheConfig(database_path=":memory:")
        cache_manager = AnalysisCacheManager(config=config)
        await cache_manager.initialize()
        
        try:
            # Simulate old cached data with missing fields
            old_cached_data = {
                "repository_data": {
                    "name": "old_repo",
                    "owner": "old_owner",
                    "full_name": "old_owner/old_repo",
                    # Missing new required fields that might be added in future
                    "description": "Old cached repository",
                    "language": "Python",
                    "stars": 50,
                    "forks_count": 25,
                    "watchers_count": 30,
                    "open_issues_count": 2,
                    "size": 512,
                    "license_name": "Apache-2.0",
                    "default_branch": "master",
                    "is_private": False,
                    "is_fork": True,
                    "is_archived": False,
                    "created_at": "2023-01-01T00:00:00",
                    "updated_at": "2023-06-01T00:00:00",
                    "pushed_at": "2023-06-15T00:00:00"
                },
                "languages": {"Python": 100},
                "topics": ["old", "legacy"],
                "primary_language": "Python",
                "license": "Apache-2.0",
                "last_activity": "2023-06-15T00:00:00",
                "created": "2023-01-01T00:00:00",
                "updated": "2023-06-01T00:00:00"
            }
            
            # Cache the old data
            await cache_manager.cache_repository_metadata("old_owner", "old_repo", old_cached_data)
            
            # Mock GitHub client for fallback
            mock_github_client = AsyncMock()
            new_repo = Repository(
                id=67890,
                owner="old_owner",
                name="old_repo",
                full_name="old_owner/old_repo",
                url="https://github.com/old_owner/old_repo",
                html_url="https://github.com/old_owner/old_repo",
                clone_url="https://github.com/old_owner/old_repo.git",
                default_branch="main",
                stars=75,
                forks_count=30
            )
            mock_github_client.get_repository.return_value = new_repo
            mock_github_client.get_repository_languages.return_value = {"Python": 100}
            mock_github_client.get_repository_topics.return_value = ["updated", "modern"]
            
            # Create display service
            display_service = RepositoryDisplayService(
                github_client=mock_github_client,
                cache_manager=cache_manager
            )
            
            # This should gracefully fall back to API when cache validation fails
            result = await display_service.show_repository_details("old_owner/old_repo")
            
            # Contract: System must not crash and must return valid data
            assert result is not None
            assert result["repository"].name == "old_repo"
            assert result["repository"].owner == "old_owner"
            
            # Contract: Must have fallen back to API (GitHub client called)
            assert mock_github_client.get_repository.call_count == 1
            
        finally:
            await cache_manager.close()
    
    async def test_cache_data_types_preserved(self):
        """Test that all data types are correctly preserved through cache serialization."""
        config = CacheConfig(database_path=":memory:")
        cache_manager = AnalysisCacheManager(config=config)
        await cache_manager.initialize()
        
        try:
            # Test data with various types
            test_repo = Repository(
                id=99999,  # int
                owner="type_test",  # str
                name="data_types",  # str
                full_name="type_test/data_types",  # str
                url="https://github.com/type_test/data_types",  # str
                html_url="https://github.com/type_test/data_types",  # str
                clone_url="https://github.com/type_test/data_types.git",  # str
                default_branch="main",  # str
                stars=42,  # int
                forks_count=7,  # int
                watchers_count=35,  # int
                open_issues_count=3,  # int
                size=2048,  # int
                language="TypeScript",  # Optional[str]
                description="Testing data type preservation",  # Optional[str]
                topics=["testing", "types", "cache"],  # List[str]
                license_name="BSD-3-Clause",  # Optional[str]
                is_private=False,  # bool
                is_fork=True,  # bool
                is_archived=False,  # bool
                is_disabled=False,  # bool
                created_at=datetime(2024, 2, 14, 10, 30, 45),  # datetime
                updated_at=datetime(2024, 3, 15, 14, 22, 18),  # datetime
                pushed_at=datetime(2024, 3, 16, 9, 45, 33)   # datetime
            )
            
            # Mock GitHub client
            mock_github_client = AsyncMock()
            mock_github_client.get_repository.return_value = test_repo
            mock_github_client.get_repository_languages.return_value = {
                "TypeScript": 60,
                "JavaScript": 30,
                "CSS": 10
            }
            mock_github_client.get_repository_topics.return_value = ["testing", "types", "cache"]
            
            # Create display service
            display_service = RepositoryDisplayService(
                github_client=mock_github_client,
                cache_manager=cache_manager
            )
            
            # Cache the data
            result1 = await display_service.show_repository_details("type_test/data_types")
            
            # Use cached data
            mock_github_client.reset_mock()
            result2 = await display_service.show_repository_details("type_test/data_types")
            
            # Verify cache was used
            assert mock_github_client.get_repository.call_count == 0
            
            # Contract: All data types must be preserved exactly
            repo1, repo2 = result1["repository"], result2["repository"]
            
            # Test integers
            assert repo1.id == repo2.id == 99999
            assert repo1.stars == repo2.stars == 42
            assert repo1.forks_count == repo2.forks_count == 7
            
            # Test strings
            assert repo1.owner == repo2.owner == "type_test"
            assert repo1.language == repo2.language == "TypeScript"
            assert repo1.license_name == repo2.license_name == "BSD-3-Clause"
            
            # Test booleans
            assert repo1.is_private == repo2.is_private == False
            assert repo1.is_fork == repo2.is_fork == True
            
            # Test lists
            assert repo1.topics == repo2.topics == ["testing", "types", "cache"]
            
            # Test datetime objects
            assert repo1.created_at == repo2.created_at
            assert repo1.updated_at == repo2.updated_at
            assert repo1.pushed_at == repo2.pushed_at
            
            # Test complex nested data
            assert result1["languages"] == result2["languages"]
            
        finally:
            await cache_manager.close()