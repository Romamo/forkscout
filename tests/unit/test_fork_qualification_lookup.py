"""Unit tests for fork qualification lookup service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from forklift.analysis.fork_qualification_lookup import (
    ForkQualificationLookup,
    ForkQualificationLookupError,
)
from forklift.github.client import GitHubClient
from forklift.models.fork_qualification import (
    QualifiedForksResult,
    CollectedForkData,
    ForkQualificationMetrics,
    QualificationStats,
)
from forklift.storage.analysis_cache import AnalysisCacheManager


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    return AsyncMock(spec=GitHubClient)


@pytest.fixture
def mock_cache_manager():
    """Create a mock cache manager."""
    mock_manager = AsyncMock(spec=AnalysisCacheManager)
    mock_manager.cache = AsyncMock()
    return mock_manager


@pytest.fixture
def sample_fork_metrics():
    """Create sample fork qualification metrics."""
    return ForkQualificationMetrics(
        id=12345,
        name="test-fork",
        full_name="fork-owner/test-fork",
        owner="fork-owner",
        html_url="https://github.com/fork-owner/test-fork",
        stargazers_count=5,
        forks_count=1,
        watchers_count=5,
        size=1000,
        language="Python",
        topics=["test", "fork"],
        open_issues_count=2,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 15, 12, 0, 0),
        pushed_at=datetime(2024, 1, 10, 12, 0, 0),  # pushed_at > created_at = has commits
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
def sample_collected_fork_data(sample_fork_metrics):
    """Create sample collected fork data."""
    return CollectedForkData(
        metrics=sample_fork_metrics,
        collection_timestamp=datetime.utcnow(),
        exact_commits_ahead="Unknown",
    )


@pytest.fixture
def sample_qualification_result(sample_collected_fork_data):
    """Create sample qualification result."""
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
        repository_owner="test-owner",
        repository_name="test-repo",
        repository_url="https://github.com/test-owner/test-repo",
        collected_forks=[sample_collected_fork_data],
        stats=stats,
        qualification_timestamp=datetime.utcnow(),
    )


@pytest.fixture
def fork_qualification_lookup(mock_github_client, mock_cache_manager):
    """Create fork qualification lookup service."""
    return ForkQualificationLookup(
        github_client=mock_github_client,
        cache_manager=mock_cache_manager,
        data_freshness_hours=24,
    )


class TestForkQualificationLookup:
    """Test cases for ForkQualificationLookup."""

    @pytest.mark.asyncio
    async def test_get_fork_qualification_data_from_cache(
        self, fork_qualification_lookup, mock_cache_manager, sample_qualification_result
    ):
        """Test getting fresh qualification data from cache."""
        # Setup
        repository_url = "https://github.com/test-owner/test-repo"
        cache_key = "fork_qualification:test-owner/test-repo"
        
        # Mock cache returning fresh data
        mock_cache_manager.cache.get_json.return_value = sample_qualification_result.model_dump()

        # Test
        result = await fork_qualification_lookup.get_fork_qualification_data(repository_url)

        # Verify
        assert result is not None
        assert result.repository_owner == "test-owner"
        assert result.repository_name == "test-repo"
        assert len(result.collected_forks) == 1
        
        mock_cache_manager.cache.get_json.assert_called_once_with(cache_key)

    @pytest.mark.asyncio
    async def test_get_fork_qualification_data_stale_cache(
        self, fork_qualification_lookup, mock_cache_manager, sample_qualification_result
    ):
        """Test handling stale cached data."""
        # Setup
        repository_url = "https://github.com/test-owner/test-repo"
        
        # Make the data stale (older than 24 hours)
        stale_timestamp = datetime.utcnow() - timedelta(hours=25)
        sample_qualification_result.qualification_timestamp = stale_timestamp
        
        mock_cache_manager.cache.get_json.return_value = sample_qualification_result.model_dump()

        # Mock fork discovery service to generate fresh data
        with patch.object(
            fork_qualification_lookup, '_generate_qualification_data'
        ) as mock_generate:
            fresh_result = sample_qualification_result.copy()
            fresh_result.qualification_timestamp = datetime.utcnow()
            mock_generate.return_value = fresh_result

            # Test
            result = await fork_qualification_lookup.get_fork_qualification_data(repository_url)

            # Verify
            assert result is not None
            mock_generate.assert_called_once_with(repository_url, False)
            mock_cache_manager.cache.set_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_fork_qualification_data_no_cache(
        self, fork_qualification_lookup, mock_cache_manager, sample_qualification_result
    ):
        """Test getting qualification data when no cache is available."""
        # Setup
        repository_url = "https://github.com/test-owner/test-repo"
        
        # Mock no cached data
        mock_cache_manager.cache.get_json.return_value = None

        # Mock fork discovery service
        with patch.object(
            fork_qualification_lookup, '_generate_qualification_data'
        ) as mock_generate:
            mock_generate.return_value = sample_qualification_result

            # Test
            result = await fork_qualification_lookup.get_fork_qualification_data(repository_url)

            # Verify
            assert result is not None
            assert result.repository_owner == "test-owner"
            mock_generate.assert_called_once_with(repository_url, False)

    @pytest.mark.asyncio
    async def test_get_fork_qualification_data_disable_cache(
        self, fork_qualification_lookup, mock_cache_manager, sample_qualification_result
    ):
        """Test getting qualification data with cache disabled."""
        # Setup
        repository_url = "https://github.com/test-owner/test-repo"

        # Mock fork discovery service
        with patch.object(
            fork_qualification_lookup, '_generate_qualification_data'
        ) as mock_generate:
            mock_generate.return_value = sample_qualification_result

            # Test
            result = await fork_qualification_lookup.get_fork_qualification_data(
                repository_url, disable_cache=True
            )

            # Verify
            assert result is not None
            mock_generate.assert_called_once_with(repository_url, True)
            
            # Cache should not be checked or written when disabled
            mock_cache_manager.cache.get_json.assert_not_called()
            mock_cache_manager.cache.set_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_lookup_fork_data_found(
        self, fork_qualification_lookup, sample_qualification_result
    ):
        """Test looking up specific fork data when found."""
        # Setup
        fork_url = "https://github.com/fork-owner/test-fork"
        repository_url = "https://github.com/test-owner/test-repo"

        # Mock getting qualification data
        with patch.object(
            fork_qualification_lookup, 'get_fork_qualification_data'
        ) as mock_get_data:
            mock_get_data.return_value = sample_qualification_result

            # Test
            result = await fork_qualification_lookup.lookup_fork_data(fork_url, repository_url)

            # Verify
            assert result is not None
            assert result.metrics.full_name == "fork-owner/test-fork"
            assert result.metrics.owner == "fork-owner"
            mock_get_data.assert_called_once_with(repository_url, False)

    @pytest.mark.asyncio
    async def test_lookup_fork_data_not_found(
        self, fork_qualification_lookup, sample_qualification_result
    ):
        """Test looking up fork data when not found."""
        # Setup
        fork_url = "https://github.com/other-owner/other-fork"
        repository_url = "https://github.com/test-owner/test-repo"

        # Mock getting qualification data
        with patch.object(
            fork_qualification_lookup, 'get_fork_qualification_data'
        ) as mock_get_data:
            mock_get_data.return_value = sample_qualification_result

            # Test
            result = await fork_qualification_lookup.lookup_fork_data(fork_url, repository_url)

            # Verify
            assert result is None

    @pytest.mark.asyncio
    async def test_lookup_fork_data_no_qualification_data(
        self, fork_qualification_lookup
    ):
        """Test looking up fork data when no qualification data is available."""
        # Setup
        fork_url = "https://github.com/fork-owner/test-fork"
        repository_url = "https://github.com/test-owner/test-repo"

        # Mock no qualification data
        with patch.object(
            fork_qualification_lookup, 'get_fork_qualification_data'
        ) as mock_get_data:
            mock_get_data.return_value = None

            # Test
            result = await fork_qualification_lookup.lookup_fork_data(fork_url, repository_url)

            # Verify
            assert result is None

    @pytest.mark.asyncio
    async def test_is_fork_data_available_true(
        self, fork_qualification_lookup, sample_qualification_result
    ):
        """Test checking data availability when data is available."""
        # Setup
        repository_url = "https://github.com/test-owner/test-repo"

        # Mock getting qualification data
        with patch.object(
            fork_qualification_lookup, 'get_fork_qualification_data'
        ) as mock_get_data:
            mock_get_data.return_value = sample_qualification_result

            # Test
            result = await fork_qualification_lookup.is_fork_data_available(repository_url)

            # Verify
            assert result is True

    @pytest.mark.asyncio
    async def test_is_fork_data_available_false(
        self, fork_qualification_lookup
    ):
        """Test checking data availability when no data is available."""
        # Setup
        repository_url = "https://github.com/test-owner/test-repo"

        # Mock no qualification data
        with patch.object(
            fork_qualification_lookup, 'get_fork_qualification_data'
        ) as mock_get_data:
            mock_get_data.return_value = None

            # Test
            result = await fork_qualification_lookup.is_fork_data_available(repository_url)

            # Verify
            assert result is False

    def test_is_data_fresh_true(self, fork_qualification_lookup, sample_qualification_result):
        """Test data freshness check for fresh data."""
        # Setup - recent timestamp
        sample_qualification_result.qualification_timestamp = datetime.utcnow() - timedelta(hours=1)

        # Test
        result = fork_qualification_lookup._is_data_fresh(sample_qualification_result)

        # Verify
        assert result is True

    def test_is_data_fresh_false(self, fork_qualification_lookup, sample_qualification_result):
        """Test data freshness check for stale data."""
        # Setup - old timestamp
        sample_qualification_result.qualification_timestamp = datetime.utcnow() - timedelta(hours=25)

        # Test
        result = fork_qualification_lookup._is_data_fresh(sample_qualification_result)

        # Verify
        assert result is False

    def test_is_data_fresh_no_timestamp(self, fork_qualification_lookup, sample_qualification_result):
        """Test data freshness check when no timestamp is available."""
        # Setup - no timestamp
        sample_qualification_result.qualification_timestamp = None

        # Test
        result = fork_qualification_lookup._is_data_fresh(sample_qualification_result)

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_generate_qualification_data_success(
        self, fork_qualification_lookup, sample_qualification_result
    ):
        """Test generating fresh qualification data successfully."""
        # Setup
        repository_url = "https://github.com/test-owner/test-repo"

        # Mock fork discovery service
        with patch('forklift.analysis.fork_qualification_lookup.ForkDiscoveryService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.discover_and_collect_fork_data.return_value = sample_qualification_result
            mock_service_class.return_value = mock_service

            # Test
            result = await fork_qualification_lookup._generate_qualification_data(repository_url)

            # Verify
            assert result is not None
            assert result.repository_owner == "test-owner"
            mock_service.discover_and_collect_fork_data.assert_called_once_with(repository_url, False)

    @pytest.mark.asyncio
    async def test_generate_qualification_data_failure(
        self, fork_qualification_lookup
    ):
        """Test handling failure when generating qualification data."""
        # Setup
        repository_url = "https://github.com/test-owner/test-repo"

        # Mock fork discovery service to raise exception
        with patch('forklift.analysis.fork_qualification_lookup.ForkDiscoveryService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.discover_and_collect_fork_data.side_effect = Exception("API error")
            mock_service_class.return_value = mock_service

            # Test
            result = await fork_qualification_lookup._generate_qualification_data(repository_url)

            # Verify
            assert result is None

    def test_parse_repository_url_full_url(self, fork_qualification_lookup):
        """Test parsing full GitHub URL."""
        # Test
        owner, repo = fork_qualification_lookup._parse_repository_url(
            "https://github.com/test-owner/test-repo"
        )

        # Verify
        assert owner == "test-owner"
        assert repo == "test-repo"

    def test_parse_repository_url_short_format(self, fork_qualification_lookup):
        """Test parsing owner/repo format."""
        # Test
        owner, repo = fork_qualification_lookup._parse_repository_url("test-owner/test-repo")

        # Verify
        assert owner == "test-owner"
        assert repo == "test-repo"

    def test_parse_repository_url_invalid(self, fork_qualification_lookup):
        """Test parsing invalid URL format."""
        # Test
        with pytest.raises(ForkQualificationLookupError):
            fork_qualification_lookup._parse_repository_url("invalid-url")

    def test_parse_repository_url_empty(self, fork_qualification_lookup):
        """Test parsing empty URL."""
        # Test
        with pytest.raises(ForkQualificationLookupError):
            fork_qualification_lookup._parse_repository_url("")

    def test_parse_repository_url_non_github(self, fork_qualification_lookup):
        """Test parsing non-GitHub URL."""
        # Test
        with pytest.raises(ForkQualificationLookupError):
            fork_qualification_lookup._parse_repository_url("https://gitlab.com/owner/repo")

    @pytest.mark.asyncio
    async def test_get_data_freshness_info_with_cache(
        self, fork_qualification_lookup, mock_cache_manager, sample_qualification_result
    ):
        """Test getting freshness info when cached data exists."""
        # Setup
        repository_url = "https://github.com/test-owner/test-repo"
        cache_key = "fork_qualification:test-owner/test-repo"
        
        mock_cache_manager.cache.get_json.return_value = sample_qualification_result.model_dump()

        # Test
        info = await fork_qualification_lookup.get_data_freshness_info(repository_url)

        # Verify
        assert info["repository"] == "test-owner/test-repo"
        assert info["has_cached_data"] is True
        assert info["is_fresh"] is True
        assert info["age_hours"] is not None
        assert info["max_age_hours"] == 24
        assert info["last_updated"] is not None

    @pytest.mark.asyncio
    async def test_get_data_freshness_info_no_cache(
        self, fork_qualification_lookup, mock_cache_manager
    ):
        """Test getting freshness info when no cached data exists."""
        # Setup
        repository_url = "https://github.com/test-owner/test-repo"
        
        mock_cache_manager.cache.get_json.return_value = None

        # Test
        info = await fork_qualification_lookup.get_data_freshness_info(repository_url)

        # Verify
        assert info["repository"] == "test-owner/test-repo"
        assert info["has_cached_data"] is False
        assert info["is_fresh"] is False
        assert info["age_hours"] is None
        assert info["max_age_hours"] == 24
        assert info["last_updated"] is None

    @pytest.mark.asyncio
    async def test_error_handling_in_get_fork_qualification_data(
        self, fork_qualification_lookup, mock_cache_manager
    ):
        """Test error handling in get_fork_qualification_data."""
        # Setup
        repository_url = "invalid-url"

        # Test
        with pytest.raises(ForkQualificationLookupError):
            await fork_qualification_lookup.get_fork_qualification_data(repository_url)

    @pytest.mark.asyncio
    async def test_error_handling_in_lookup_fork_data(
        self, fork_qualification_lookup
    ):
        """Test error handling in lookup_fork_data."""
        # Setup
        fork_url = "invalid-fork-url"
        repository_url = "https://github.com/test-owner/test-repo"

        # Test
        with pytest.raises(ForkQualificationLookupError):
            await fork_qualification_lookup.lookup_fork_data(fork_url, repository_url)

    @pytest.mark.asyncio
    async def test_cache_error_handling(
        self, fork_qualification_lookup, mock_cache_manager, sample_qualification_result
    ):
        """Test handling cache errors gracefully."""
        # Setup
        repository_url = "https://github.com/test-owner/test-repo"
        
        # Mock cache error
        mock_cache_manager.cache.get_json.side_effect = Exception("Cache error")

        # Mock fork discovery service
        with patch.object(
            fork_qualification_lookup, '_generate_qualification_data'
        ) as mock_generate:
            mock_generate.return_value = sample_qualification_result

            # Test - should not raise exception, should fallback to generation
            result = await fork_qualification_lookup.get_fork_qualification_data(repository_url)

            # Verify
            assert result is not None
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialization_without_cache_manager(self, mock_github_client):
        """Test initialization without cache manager."""
        # Test
        lookup = ForkQualificationLookup(mock_github_client)

        # Verify
        assert lookup.github_client == mock_github_client
        assert lookup.cache_manager is None
        assert lookup.data_freshness_hours == 24

    @pytest.mark.asyncio
    async def test_custom_freshness_hours(self, mock_github_client, mock_cache_manager):
        """Test initialization with custom freshness hours."""
        # Test
        lookup = ForkQualificationLookup(
            mock_github_client, mock_cache_manager, data_freshness_hours=48
        )

        # Verify
        assert lookup.data_freshness_hours == 48