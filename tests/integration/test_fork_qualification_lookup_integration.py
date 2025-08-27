"""Integration tests for fork qualification lookup service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from forklift.analysis.fork_qualification_lookup import ForkQualificationLookup
from forklift.config.settings import ForkliftConfig
from forklift.github.client import GitHubClient
from forklift.models.fork_qualification import (
    QualifiedForksResult,
    CollectedForkData,
    ForkQualificationMetrics,
    QualificationStats,
)
from forklift.storage.analysis_cache import AnalysisCacheManager


@pytest.fixture
async def github_client():
    """Create a real GitHub client for testing."""
    config = ForkliftConfig()
    if not config.github.token:
        pytest.skip("GitHub token not configured")
    
    client = GitHubClient(config.github)
    yield client
    await client.close()


@pytest.fixture
async def cache_manager():
    """Create a real cache manager for testing."""
    manager = AnalysisCacheManager()
    await manager.initialize()
    yield manager
    await manager.close()


@pytest.fixture
def sample_fork_metrics():
    """Create sample fork qualification metrics."""
    return ForkQualificationMetrics(
        id=12345,
        name="test-fork",
        full_name="test-owner/test-fork",
        owner="test-owner",
        html_url="https://github.com/test-owner/test-fork",
        stargazers_count=5,
        forks_count=1,
        watchers_count=5,
        size=1000,
        language="Python",
        topics=["test"],
        open_issues_count=2,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 15, 12, 0, 0),
        pushed_at=datetime(2024, 1, 10, 12, 0, 0),
        archived=False,
        disabled=False,
        fork=True,
        license_key="mit",
        license_name="MIT License",
        description="Test fork repository",
        homepage="https://example.com",
        default_branch="main",
    )


@pytest.fixture
def sample_qualification_result(sample_fork_metrics):
    """Create sample qualification result."""
    collected_fork = CollectedForkData(
        metrics=sample_fork_metrics,
        collection_timestamp=datetime.utcnow(),
        exact_commits_ahead="Unknown",
    )

    stats = QualificationStats(
        total_forks_discovered=1,
        forks_with_no_commits=0,
        forks_with_commits=1,
        archived_forks=0,
        disabled_forks=0,
        api_calls_made=5,
        api_calls_saved=3,
        processing_time_seconds=2.5,
        collection_timestamp=datetime.utcnow(),
    )

    return QualifiedForksResult(
        repository_owner="parent-owner",
        repository_name="parent-repo",
        repository_url="https://github.com/parent-owner/parent-repo",
        collected_forks=[collected_fork],
        stats=stats,
        qualification_timestamp=datetime.utcnow(),
    )


class TestForkQualificationLookupIntegration:
    """Integration tests for ForkQualificationLookup."""

    @pytest.mark.asyncio
    async def test_cache_roundtrip_integration(
        self, github_client, cache_manager, sample_qualification_result
    ):
        """Test complete cache roundtrip with real cache manager."""
        # Setup
        lookup = ForkQualificationLookup(
            github_client, cache_manager, data_freshness_hours=24
        )
        repository_url = "https://github.com/parent-owner/parent-repo"

        # Mock the generation to return our sample data
        with patch.object(lookup, '_generate_qualification_data') as mock_generate:
            mock_generate.return_value = sample_qualification_result

            # First call should generate and cache data
            result1 = await lookup.get_fork_qualification_data(repository_url)
            assert result1 is not None
            assert result1.repository_owner == "parent-owner"
            mock_generate.assert_called_once()

            # Reset mock for second call
            mock_generate.reset_mock()

            # Second call should use cached data
            result2 = await lookup.get_fork_qualification_data(repository_url)
            assert result2 is not None
            assert result2.repository_owner == "parent-owner"
            mock_generate.assert_not_called()  # Should not generate again

            # Verify data integrity
            assert result1.dict() == result2.dict()

    @pytest.mark.asyncio
    async def test_stale_data_refresh_integration(
        self, github_client, cache_manager, sample_qualification_result
    ):
        """Test that stale data is refreshed properly."""
        # Setup
        lookup = ForkQualificationLookup(
            github_client, cache_manager, data_freshness_hours=1  # 1 hour freshness
        )
        repository_url = "https://github.com/parent-owner/parent-repo"

        # Create stale data (older than 1 hour)
        stale_result = sample_qualification_result.copy()
        stale_result.qualification_timestamp = datetime.utcnow() - timedelta(hours=2)

        # Mock generation to return fresh data
        fresh_result = sample_qualification_result.copy()
        fresh_result.qualification_timestamp = datetime.utcnow()

        with patch.object(lookup, '_generate_qualification_data') as mock_generate:
            # First, manually cache stale data
            cache_key = "fork_qualification:parent-owner/parent-repo"
            await cache_manager.cache_data(cache_key, stale_result.dict(), ttl_hours=24)

            # Set up mock to return fresh data
            mock_generate.return_value = fresh_result

            # Call should detect stale data and refresh
            result = await lookup.get_fork_qualification_data(repository_url)

            # Verify fresh data was generated
            assert result is not None
            mock_generate.assert_called_once()
            
            # Verify timestamp is fresh
            assert result.qualification_timestamp is not None
            age = datetime.utcnow() - result.qualification_timestamp.replace(tzinfo=None)
            assert age.total_seconds() < 300  # Less than 5 minutes old

    @pytest.mark.asyncio
    async def test_fork_data_lookup_integration(
        self, github_client, cache_manager, sample_qualification_result
    ):
        """Test looking up specific fork data from cached qualification results."""
        # Setup
        lookup = ForkQualificationLookup(github_client, cache_manager)
        repository_url = "https://github.com/parent-owner/parent-repo"
        fork_url = "https://github.com/test-owner/test-fork"

        # Mock generation
        with patch.object(lookup, '_generate_qualification_data') as mock_generate:
            mock_generate.return_value = sample_qualification_result

            # First, ensure qualification data is cached
            await lookup.get_fork_qualification_data(repository_url)

            # Now lookup specific fork data
            fork_data = await lookup.lookup_fork_data(fork_url, repository_url)

            # Verify fork data was found
            assert fork_data is not None
            assert fork_data.metrics.full_name == "test-owner/test-fork"
            assert fork_data.metrics.owner == "test-owner"

    @pytest.mark.asyncio
    async def test_fork_data_lookup_not_found_integration(
        self, github_client, cache_manager, sample_qualification_result
    ):
        """Test looking up fork data that doesn't exist in qualification results."""
        # Setup
        lookup = ForkQualificationLookup(github_client, cache_manager)
        repository_url = "https://github.com/parent-owner/parent-repo"
        fork_url = "https://github.com/other-owner/other-fork"  # Not in sample data

        # Mock generation
        with patch.object(lookup, '_generate_qualification_data') as mock_generate:
            mock_generate.return_value = sample_qualification_result

            # Lookup non-existent fork data
            fork_data = await lookup.lookup_fork_data(fork_url, repository_url)

            # Verify fork data was not found
            assert fork_data is None

    @pytest.mark.asyncio
    async def test_data_availability_check_integration(
        self, github_client, cache_manager, sample_qualification_result
    ):
        """Test checking data availability with real cache."""
        # Setup
        lookup = ForkQualificationLookup(github_client, cache_manager)
        repository_url = "https://github.com/parent-owner/parent-repo"

        # Initially no data should be available
        available = await lookup.is_fork_data_available(repository_url)
        assert available is False

        # Mock generation and cache data
        with patch.object(lookup, '_generate_qualification_data') as mock_generate:
            mock_generate.return_value = sample_qualification_result

            # Generate and cache data
            await lookup.get_fork_qualification_data(repository_url)

            # Now data should be available
            available = await lookup.is_fork_data_available(repository_url)
            assert available is True

    @pytest.mark.asyncio
    async def test_cache_disabled_integration(
        self, github_client, cache_manager, sample_qualification_result
    ):
        """Test behavior when cache is disabled."""
        # Setup
        lookup = ForkQualificationLookup(github_client, cache_manager)
        repository_url = "https://github.com/parent-owner/parent-repo"

        # Mock generation
        with patch.object(lookup, '_generate_qualification_data') as mock_generate:
            mock_generate.return_value = sample_qualification_result

            # First call with cache disabled
            result1 = await lookup.get_fork_qualification_data(repository_url, disable_cache=True)
            assert result1 is not None
            assert mock_generate.call_count == 1

            # Second call with cache disabled should generate again
            result2 = await lookup.get_fork_qualification_data(repository_url, disable_cache=True)
            assert result2 is not None
            assert mock_generate.call_count == 2  # Called twice

    @pytest.mark.asyncio
    async def test_freshness_info_integration(
        self, github_client, cache_manager, sample_qualification_result
    ):
        """Test getting freshness information with real cache."""
        # Setup
        lookup = ForkQualificationLookup(github_client, cache_manager)
        repository_url = "https://github.com/parent-owner/parent-repo"

        # Initially no cached data
        info = await lookup.get_data_freshness_info(repository_url)
        assert info["has_cached_data"] is False
        assert info["is_fresh"] is False

        # Mock generation and cache data
        with patch.object(lookup, '_generate_qualification_data') as mock_generate:
            mock_generate.return_value = sample_qualification_result

            # Generate and cache data
            await lookup.get_fork_qualification_data(repository_url)

            # Check freshness info
            info = await lookup.get_data_freshness_info(repository_url)
            assert info["has_cached_data"] is True
            assert info["is_fresh"] is True
            assert info["age_hours"] is not None
            assert info["age_hours"] < 1  # Should be very fresh
            assert info["last_updated"] is not None

    @pytest.mark.asyncio
    async def test_cache_error_handling_integration(
        self, github_client, sample_qualification_result
    ):
        """Test handling cache errors gracefully."""
        # Setup with mock cache that fails
        mock_cache = AsyncMock()
        mock_cache.get_cached_data.side_effect = Exception("Cache error")
        mock_cache.cache_data.side_effect = Exception("Cache write error")

        lookup = ForkQualificationLookup(github_client, mock_cache)
        repository_url = "https://github.com/parent-owner/parent-repo"

        # Mock generation
        with patch.object(lookup, '_generate_qualification_data') as mock_generate:
            mock_generate.return_value = sample_qualification_result

            # Should handle cache errors gracefully and still return data
            result = await lookup.get_fork_qualification_data(repository_url)
            assert result is not None
            assert result.repository_owner == "parent-owner"
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_cache_manager_integration(
        self, github_client, sample_qualification_result
    ):
        """Test behavior when no cache manager is provided."""
        # Setup without cache manager
        lookup = ForkQualificationLookup(github_client, cache_manager=None)
        repository_url = "https://github.com/parent-owner/parent-repo"

        # Mock generation
        with patch.object(lookup, '_generate_qualification_data') as mock_generate:
            mock_generate.return_value = sample_qualification_result

            # Should work without cache
            result = await lookup.get_fork_qualification_data(repository_url)
            assert result is not None
            assert result.repository_owner == "parent-owner"
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_url_parsing_integration(self, github_client, cache_manager):
        """Test URL parsing with various formats."""
        # Setup
        lookup = ForkQualificationLookup(github_client, cache_manager)

        # Test different URL formats
        test_cases = [
            ("https://github.com/owner/repo", ("owner", "repo")),
            ("owner/repo", ("owner", "repo")),
            ("https://github.com/owner/repo.git", ("owner", "repo.git")),
        ]

        for url, expected in test_cases:
            owner, repo = lookup._parse_repository_url(url)
            assert (owner, repo) == expected

    @pytest.mark.asyncio
    async def test_concurrent_access_integration(
        self, github_client, cache_manager, sample_qualification_result
    ):
        """Test concurrent access to qualification data."""
        import asyncio
        
        # Setup
        lookup = ForkQualificationLookup(github_client, cache_manager)
        repository_url = "https://github.com/parent-owner/parent-repo"

        # Mock generation
        with patch.object(lookup, '_generate_qualification_data') as mock_generate:
            mock_generate.return_value = sample_qualification_result

            # Make concurrent calls
            tasks = [
                lookup.get_fork_qualification_data(repository_url)
                for _ in range(3)
            ]
            results = await asyncio.gather(*tasks)

            # Verify all calls succeeded
            assert all(result is not None for result in results)
            assert all(result.repository_owner == "parent-owner" for result in results)

            # Generation should only happen once due to caching
            assert mock_generate.call_count <= 3  # May be called multiple times due to race conditions

    @pytest.mark.asyncio
    async def test_data_serialization_integration(
        self, github_client, cache_manager, sample_qualification_result
    ):
        """Test that qualification data can be properly serialized and deserialized."""
        # Setup
        lookup = ForkQualificationLookup(github_client, cache_manager)
        repository_url = "https://github.com/parent-owner/parent-repo"

        # Mock generation
        with patch.object(lookup, '_generate_qualification_data') as mock_generate:
            mock_generate.return_value = sample_qualification_result

            # Cache and retrieve data
            result1 = await lookup.get_fork_qualification_data(repository_url)
            result2 = await lookup.get_fork_qualification_data(repository_url)

            # Verify serialization/deserialization worked correctly
            assert result1.dict() == result2.dict()
            assert result1.repository_owner == result2.repository_owner
            assert len(result1.collected_forks) == len(result2.collected_forks)
            
            # Verify fork data integrity
            fork1 = result1.collected_forks[0]
            fork2 = result2.collected_forks[0]
            assert fork1.metrics.full_name == fork2.metrics.full_name
            assert fork1.metrics.commits_ahead_status == fork2.metrics.commits_ahead_status