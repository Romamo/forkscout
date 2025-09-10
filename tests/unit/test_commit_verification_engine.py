"""Unit tests for CommitVerificationEngine."""

import asyncio
import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from forkscout.analysis.commit_verification_engine import CommitVerificationEngine, VerificationCache
from forkscout.github.exceptions import GitHubAPIError, GitHubNotFoundError, GitHubRateLimitError
from forkscout.models.fork_qualification import CollectedForkData, ForkQualificationMetrics
from forkscout.models.github import Repository


class TestVerificationCache:
    """Test cases for VerificationCache."""
    
    def test_cache_initialization(self):
        """Test cache initialization with default TTL."""
        cache = VerificationCache()
        assert cache.ttl_hours == 24
        assert cache._cache == {}
    
    def test_cache_initialization_custom_ttl(self):
        """Test cache initialization with custom TTL."""
        cache = VerificationCache(ttl_hours=12)
        assert cache.ttl_hours == 12
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        cache = VerificationCache()
        key = cache._get_cache_key("fork_owner", "fork_repo", "parent_owner", "parent_repo")
        assert key == "parent_owner/parent_repo:fork_owner/fork_repo"
    
    def test_cache_set_and_get(self):
        """Test setting and getting cache values."""
        cache = VerificationCache()
        result = {"ahead_by": 5, "behind_by": 2}
        
        cache.set("fork_owner", "fork_repo", "parent_owner", "parent_repo", result)
        retrieved = cache.get("fork_owner", "fork_repo", "parent_owner", "parent_repo")
        
        assert retrieved == result
    
    def test_cache_miss(self):
        """Test cache miss for non-existent key."""
        cache = VerificationCache()
        result = cache.get("nonexistent", "repo", "parent", "repo")
        assert result is None
    
    def test_cache_expiry(self):
        """Test cache expiry based on TTL."""
        cache = VerificationCache(ttl_hours=1)
        result = {"ahead_by": 5, "behind_by": 2}
        
        # Manually set expired cache entry
        key = cache._get_cache_key("fork_owner", "fork_repo", "parent_owner", "parent_repo")
        expired_time = datetime.now(UTC) - timedelta(hours=2)
        cache._cache[key] = {
            "result": result,
            "cached_at": expired_time
        }
        
        # Should return None for expired entry
        retrieved = cache.get("fork_owner", "fork_repo", "parent_owner", "parent_repo")
        assert retrieved is None
        assert key not in cache._cache  # Should be cleaned up
    
    def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache = VerificationCache()
        result = {"ahead_by": 5, "behind_by": 2}
        
        cache.set("fork_owner", "fork_repo", "parent_owner", "parent_repo", result)
        cache.invalidate("fork_owner", "fork_repo", "parent_owner", "parent_repo")
        
        retrieved = cache.get("fork_owner", "fork_repo", "parent_owner", "parent_repo")
        assert retrieved is None
    
    def test_cache_clear(self):
        """Test clearing all cache entries."""
        cache = VerificationCache()
        
        cache.set("fork1", "repo1", "parent", "repo", {"ahead_by": 1})
        cache.set("fork2", "repo2", "parent", "repo", {"ahead_by": 2})
        
        assert len(cache._cache) == 2
        
        cache.clear()
        assert len(cache._cache) == 0
    
    def test_cache_stats(self):
        """Test cache statistics."""
        cache = VerificationCache(ttl_hours=1)
        
        # Add valid entry
        cache.set("fork1", "repo1", "parent", "repo", {"ahead_by": 1})
        
        # Add expired entry manually
        key = cache._get_cache_key("fork2", "repo2", "parent", "repo")
        expired_time = datetime.now(UTC) - timedelta(hours=2)
        cache._cache[key] = {
            "result": {"ahead_by": 2},
            "cached_at": expired_time
        }
        
        stats = cache.get_stats()
        assert stats["total_entries"] == 2
        assert stats["valid_entries"] == 1
        assert stats["expired_entries"] == 1


class TestCommitVerificationEngine:
    """Test cases for CommitVerificationEngine."""
    
    @pytest.fixture
    def mock_github_client(self):
        """Create mock GitHub client."""
        client = AsyncMock()
        return client
    
    @pytest.fixture
    def verification_engine(self, mock_github_client):
        """Create CommitVerificationEngine with mock client."""
        return CommitVerificationEngine(
            github_client=mock_github_client,
            cache_ttl_hours=1,
            max_concurrent_requests=2,
            retry_attempts=2,
            backoff_base_seconds=0.1  # Fast for testing
        )
    
    @pytest.fixture
    def sample_fork_data(self):
        """Create sample fork data for testing."""
        metrics = ForkQualificationMetrics(
            id=123,
            name="test-fork",
            full_name="fork_owner/test-fork",
            owner="fork_owner",
            html_url="https://github.com/fork_owner/test-fork",
            created_at=datetime.now(UTC) - timedelta(days=10),
            updated_at=datetime.now(UTC) - timedelta(days=1),
            pushed_at=datetime.now(UTC) - timedelta(days=5)
        )
        return CollectedForkData(metrics=metrics)
    
    def test_engine_initialization(self, mock_github_client):
        """Test engine initialization with default parameters."""
        engine = CommitVerificationEngine(mock_github_client)
        
        assert engine.github_client == mock_github_client
        assert engine.cache.ttl_hours == 24
        assert engine.max_concurrent_requests == 5
        assert engine.retry_attempts == 3
        assert engine.backoff_base_seconds == 1.0
        assert engine.progress_callback is None
    
    def test_engine_initialization_custom_params(self, mock_github_client):
        """Test engine initialization with custom parameters."""
        progress_callback = MagicMock()
        
        engine = CommitVerificationEngine(
            github_client=mock_github_client,
            cache_ttl_hours=12,
            max_concurrent_requests=3,
            retry_attempts=5,
            backoff_base_seconds=2.0,
            progress_callback=progress_callback
        )
        
        assert engine.cache.ttl_hours == 12
        assert engine.max_concurrent_requests == 3
        assert engine.retry_attempts == 5
        assert engine.backoff_base_seconds == 2.0
        assert engine.progress_callback == progress_callback
    
    @pytest.mark.asyncio
    async def test_get_commits_ahead_success(self, verification_engine, mock_github_client):
        """Test successful commits ahead verification."""
        # Mock repository responses
        fork_repo = Repository(
            id=123,
            name="test-fork",
            full_name="fork_owner/test-fork",
            owner="fork_owner",
            default_branch="main",
            url="https://api.github.com/repos/fork_owner/test-fork",
            html_url="https://github.com/fork_owner/test-fork",
            clone_url="https://github.com/fork_owner/test-fork.git"
        )
        
        parent_repo = Repository(
            id=456,
            name="parent-repo",
            full_name="parent_owner/parent-repo",
            owner="parent_owner",
            default_branch="main",
            url="https://api.github.com/repos/parent_owner/parent-repo",
            html_url="https://github.com/parent_owner/parent-repo",
            clone_url="https://github.com/parent_owner/parent-repo.git"
        )
        
        comparison_result = {
            "ahead_by": 5,
            "behind_by": 2,
            "total_commits": 7,
            "commits": [{"sha": "abc123"}, {"sha": "def456"}]
        }
        
        mock_github_client.get_repository.side_effect = [fork_repo, parent_repo]
        mock_github_client.compare_commits.return_value = comparison_result
        
        result = await verification_engine.get_commits_ahead(
            "fork_owner", "test-fork", "parent_owner", "parent-repo"
        )
        
        assert result["success"] is True
        assert result["ahead_by"] == 5
        assert result["behind_by"] == 2
        assert result["total_commits"] == 7
        assert result["commit_count"] == 2
        assert result["verification_method"] == "github_compare_api"
        assert "verified_at" in result
        
        # Verify API calls
        mock_github_client.get_repository.assert_any_call("fork_owner", "test-fork")
        mock_github_client.get_repository.assert_any_call("parent_owner", "parent-repo")
        mock_github_client.compare_commits.assert_called_once_with(
            "parent_owner", "parent-repo", "main", "fork_owner:main"
        )
    
    @pytest.mark.asyncio
    async def test_get_commits_ahead_cached_result(self, verification_engine, mock_github_client):
        """Test using cached verification result."""
        cached_result = {
            "success": True,
            "ahead_by": 3,
            "behind_by": 1,
            "total_commits": 4
        }
        
        # Pre-populate cache
        verification_engine.cache.set(
            "fork_owner", "test-fork", "parent_owner", "parent-repo", cached_result
        )
        
        result = await verification_engine.get_commits_ahead(
            "fork_owner", "test-fork", "parent_owner", "parent-repo"
        )
        
        assert result == cached_result
        assert verification_engine.stats["cache_hits"] == 1
        assert verification_engine.stats["cache_misses"] == 0
        
        # Verify no API calls were made
        mock_github_client.get_repository.assert_not_called()
        mock_github_client.compare_commits.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_commits_ahead_cache_disabled(self, verification_engine, mock_github_client):
        """Test verification with cache disabled."""
        # Pre-populate cache
        cached_result = {"success": True, "ahead_by": 3}
        verification_engine.cache.set(
            "fork_owner", "test-fork", "parent_owner", "parent-repo", cached_result
        )
        
        # Mock successful API response
        fork_repo = Repository(
            id=123, name="test-fork", full_name="fork_owner/test-fork",
            owner="fork_owner", default_branch="main",
            url="https://api.github.com/repos/fork_owner/test-fork",
            html_url="https://github.com/fork_owner/test-fork",
            clone_url="https://github.com/fork_owner/test-fork.git"
        )
        parent_repo = Repository(
            id=456, name="parent-repo", full_name="parent_owner/parent-repo",
            owner="parent_owner", default_branch="main",
            url="https://api.github.com/repos/parent_owner/parent-repo",
            html_url="https://github.com/parent_owner/parent-repo",
            clone_url="https://github.com/parent_owner/parent-repo.git"
        )
        
        mock_github_client.get_repository.side_effect = [fork_repo, parent_repo]
        mock_github_client.compare_commits.return_value = {"ahead_by": 5, "behind_by": 0}
        
        result = await verification_engine.get_commits_ahead(
            "fork_owner", "test-fork", "parent_owner", "parent-repo", use_cache=False
        )
        
        assert result["ahead_by"] == 5  # From API, not cache
        assert verification_engine.stats["cache_hits"] == 0
        
        # Verify API calls were made
        mock_github_client.get_repository.assert_called()
        mock_github_client.compare_commits.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_commits_ahead_repository_not_found(self, verification_engine, mock_github_client):
        """Test handling of repository not found error."""
        mock_github_client.get_repository.side_effect = GitHubNotFoundError(
            "Repository not found", status_code=404
        )
        
        result = await verification_engine.get_commits_ahead(
            "fork_owner", "nonexistent", "parent_owner", "parent-repo"
        )
        
        assert result["success"] is False
        assert result["error"] == "repository_not_found"
        assert result["ahead_by"] == 0
        assert result["behind_by"] == 0
        assert "error_message" in result
        assert verification_engine.stats["verification_errors"] == 1
    
    @pytest.mark.asyncio
    async def test_get_commits_ahead_rate_limit_retry(self, verification_engine, mock_github_client):
        """Test retry logic for rate limit errors."""
        # First call raises rate limit error, second succeeds
        rate_limit_error = GitHubRateLimitError(
            "Rate limit exceeded", reset_time=int(datetime.now().timestamp()) + 1
        )
        
        fork_repo = Repository(
            id=123, name="test-fork", full_name="fork_owner/test-fork",
            owner="fork_owner", default_branch="main",
            url="https://api.github.com/repos/fork_owner/test-fork",
            html_url="https://github.com/fork_owner/test-fork",
            clone_url="https://github.com/fork_owner/test-fork.git"
        )
        parent_repo = Repository(
            id=456, name="parent-repo", full_name="parent_owner/parent-repo",
            owner="parent_owner", default_branch="main",
            url="https://api.github.com/repos/parent_owner/parent-repo",
            html_url="https://github.com/parent_owner/parent-repo",
            clone_url="https://github.com/parent_owner/parent-repo.git"
        )
        
        mock_github_client.get_repository.side_effect = [
            rate_limit_error,  # First attempt fails
            fork_repo,         # Second attempt succeeds
            parent_repo
        ]
        mock_github_client.compare_commits.return_value = {"ahead_by": 3, "behind_by": 1}
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await verification_engine.get_commits_ahead(
                "fork_owner", "test-fork", "parent_owner", "parent-repo"
            )
        
        assert result["success"] is True
        assert result["ahead_by"] == 3
        assert mock_sleep.called  # Should have waited for rate limit
    
    @pytest.mark.asyncio
    async def test_get_commits_ahead_max_retries_exceeded(self, verification_engine, mock_github_client):
        """Test failure after max retries exceeded."""
        api_error = GitHubAPIError("Server error", status_code=500)
        mock_github_client.get_repository.side_effect = api_error
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await verification_engine.get_commits_ahead(
                "fork_owner", "test-fork", "parent_owner", "parent-repo"
            )
        
        assert result["success"] is False
        assert result["error"] == "verification_failed"
        assert verification_engine.stats["verification_errors"] == 1
        
        # Should have made retry_attempts calls
        assert mock_github_client.get_repository.call_count == verification_engine.retry_attempts
    
    @pytest.mark.asyncio
    async def test_batch_verify_forks(self, verification_engine, mock_github_client, sample_fork_data):
        """Test batch verification of multiple forks."""
        # Create multiple fork data entries
        fork_data_list = []
        for i in range(3):
            metrics = ForkQualificationMetrics(
                id=100 + i,
                name=f"fork-{i}",
                full_name=f"owner{i}/fork-{i}",
                owner=f"owner{i}",
                html_url=f"https://github.com/owner{i}/fork-{i}",
                created_at=datetime.now(UTC) - timedelta(days=10),
                updated_at=datetime.now(UTC) - timedelta(days=1),
                pushed_at=datetime.now(UTC) - timedelta(days=5)  # Has commits
            )
            fork_data_list.append(CollectedForkData(metrics=metrics))
        
        # Mock repository responses
        mock_repos = []
        for i in range(6):  # 3 forks + 3 parent calls
            repo = Repository(
                id=200 + i,
                name=f"repo-{i}",
                full_name=f"owner/repo-{i}",
                owner="owner",
                default_branch="main",
                url=f"https://api.github.com/repos/owner/repo-{i}",
                html_url=f"https://github.com/owner/repo-{i}",
                clone_url=f"https://github.com/owner/repo-{i}.git"
            )
            mock_repos.append(repo)
        
        mock_github_client.get_repository.side_effect = mock_repos
        mock_github_client.compare_commits.return_value = {
            "ahead_by": 2, "behind_by": 1, "total_commits": 3
        }
        
        result = await verification_engine.batch_verify_forks(
            fork_data_list, "parent_owner", "parent_repo"
        )
        
        assert len(result) == 3
        for fork_data in result:
            assert fork_data.exact_commits_ahead == 2
            assert fork_data.exact_commits_behind == 1
    
    @pytest.mark.asyncio
    async def test_batch_verify_forks_skip_no_commits(self, verification_engine, mock_github_client):
        """Test batch verification with skipping forks that have no commits."""
        # Create fork data with no commits ahead (created_at >= pushed_at)
        no_commits_metrics = ForkQualificationMetrics(
            id=100,
            name="no-commits-fork",
            full_name="owner/no-commits-fork",
            owner="owner",
            html_url="https://github.com/owner/no-commits-fork",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            pushed_at=datetime.now(UTC) - timedelta(minutes=1)  # Before creation
        )
        
        # Create fork data with commits ahead
        has_commits_metrics = ForkQualificationMetrics(
            id=101,
            name="has-commits-fork",
            full_name="owner/has-commits-fork",
            owner="owner",
            html_url="https://github.com/owner/has-commits-fork",
            created_at=datetime.now(UTC) - timedelta(days=5),
            updated_at=datetime.now(UTC),
            pushed_at=datetime.now(UTC)  # After creation
        )
        
        fork_data_list = [
            CollectedForkData(metrics=no_commits_metrics),
            CollectedForkData(metrics=has_commits_metrics)
        ]
        
        # Mock only for the fork with commits
        fork_repo = Repository(
            id=101, name="has-commits-fork", full_name="owner/has-commits-fork",
            owner="owner", default_branch="main",
            url="https://api.github.com/repos/owner/has-commits-fork",
            html_url="https://github.com/owner/has-commits-fork",
            clone_url="https://github.com/owner/has-commits-fork.git"
        )
        parent_repo = Repository(
            id=200, name="parent-repo", full_name="parent/parent-repo",
            owner="parent", default_branch="main",
            url="https://api.github.com/repos/parent/parent-repo",
            html_url="https://github.com/parent/parent-repo",
            clone_url="https://github.com/parent/parent-repo.git"
        )
        
        mock_github_client.get_repository.side_effect = [fork_repo, parent_repo]
        mock_github_client.compare_commits.return_value = {"ahead_by": 3, "behind_by": 0}
        
        result = await verification_engine.batch_verify_forks(
            fork_data_list, "parent", "parent-repo", skip_no_commits=True
        )
        
        assert len(result) == 2
        
        # Find results by name
        no_commits_result = next(r for r in result if r.metrics.name == "no-commits-fork")
        has_commits_result = next(r for r in result if r.metrics.name == "has-commits-fork")
        
        # No commits fork should not be verified (no exact counts)
        assert no_commits_result.exact_commits_ahead is None
        assert no_commits_result.exact_commits_behind is None
        
        # Has commits fork should be verified
        assert has_commits_result.exact_commits_ahead == 3
        assert has_commits_result.exact_commits_behind == 0
        
        # Should only have made API calls for one fork
        assert mock_github_client.get_repository.call_count == 2  # Fork + parent
        assert mock_github_client.compare_commits.call_count == 1
    
    @pytest.mark.asyncio
    async def test_verify_individual_fork(self, verification_engine, mock_github_client, sample_fork_data):
        """Test individual fork verification."""
        # Mock repository responses
        fork_repo = Repository(
            id=123, name="test-fork", full_name="fork_owner/test-fork",
            owner="fork_owner", default_branch="main",
            url="https://api.github.com/repos/fork_owner/test-fork",
            html_url="https://github.com/fork_owner/test-fork",
            clone_url="https://github.com/fork_owner/test-fork.git"
        )
        parent_repo = Repository(
            id=456, name="parent-repo", full_name="parent_owner/parent-repo",
            owner="parent_owner", default_branch="main",
            url="https://api.github.com/repos/parent_owner/parent-repo",
            html_url="https://github.com/parent_owner/parent-repo",
            clone_url="https://github.com/parent_owner/parent-repo.git"
        )
        
        mock_github_client.get_repository.side_effect = [fork_repo, parent_repo]
        mock_github_client.compare_commits.return_value = {"ahead_by": 4, "behind_by": 1}
        
        result = await verification_engine.verify_individual_fork(
            sample_fork_data, "parent_owner", "parent-repo"
        )
        
        assert result.exact_commits_ahead == 4
        assert result.exact_commits_behind == 1
    
    @pytest.mark.asyncio
    async def test_verify_individual_fork_skip_no_commits(self, verification_engine, mock_github_client):
        """Test individual fork verification skipping forks with no commits."""
        # Create fork data with no commits ahead
        no_commits_metrics = ForkQualificationMetrics(
            id=100,
            name="no-commits-fork",
            full_name="owner/no-commits-fork",
            owner="owner",
            html_url="https://github.com/owner/no-commits-fork",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            pushed_at=datetime.now(UTC) - timedelta(minutes=1)  # Before creation
        )
        fork_data = CollectedForkData(metrics=no_commits_metrics)
        
        result = await verification_engine.verify_individual_fork(
            fork_data, "parent_owner", "parent-repo"
        )
        
        # Should return original data without verification
        assert result.exact_commits_ahead is None
        assert result.exact_commits_behind is None
        
        # No API calls should be made
        mock_github_client.get_repository.assert_not_called()
        mock_github_client.compare_commits.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_verify_individual_fork_force_verification(self, verification_engine, mock_github_client):
        """Test individual fork verification with force flag."""
        # Create fork data with no commits ahead
        no_commits_metrics = ForkQualificationMetrics(
            id=100,
            name="no-commits-fork",
            full_name="owner/no-commits-fork",
            owner="owner",
            html_url="https://github.com/owner/no-commits-fork",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            pushed_at=datetime.now(UTC) - timedelta(minutes=1)
        )
        fork_data = CollectedForkData(metrics=no_commits_metrics)
        
        # Mock repository responses
        fork_repo = Repository(
            id=100, name="no-commits-fork", full_name="owner/no-commits-fork",
            owner="owner", default_branch="main",
            url="https://api.github.com/repos/owner/no-commits-fork",
            html_url="https://github.com/owner/no-commits-fork",
            clone_url="https://github.com/owner/no-commits-fork.git"
        )
        parent_repo = Repository(
            id=200, name="parent-repo", full_name="parent/parent-repo",
            owner="parent", default_branch="main",
            url="https://api.github.com/repos/parent/parent-repo",
            html_url="https://github.com/parent/parent-repo",
            clone_url="https://github.com/parent/parent-repo.git"
        )
        
        mock_github_client.get_repository.side_effect = [fork_repo, parent_repo]
        mock_github_client.compare_commits.return_value = {"ahead_by": 0, "behind_by": 5}
        
        result = await verification_engine.verify_individual_fork(
            fork_data, "parent", "parent-repo", force_verification=True
        )
        
        # Should be verified despite no commits ahead
        assert result.exact_commits_ahead == 0
        assert result.exact_commits_behind == 5
        
        # API calls should be made
        mock_github_client.get_repository.assert_called()
        mock_github_client.compare_commits.assert_called()
    
    def test_get_verification_stats(self, verification_engine):
        """Test getting verification statistics."""
        # Simulate some activity
        verification_engine.stats["api_calls_made"] = 10
        verification_engine.stats["cache_hits"] = 3
        verification_engine.stats["cache_misses"] = 7
        verification_engine.stats["successful_verifications"] = 8
        verification_engine.stats["verification_errors"] = 2
        
        stats = verification_engine.get_verification_stats()
        
        assert stats["api_calls_made"] == 10
        assert stats["cache_hits"] == 3
        assert stats["cache_misses"] == 7
        assert stats["successful_verifications"] == 8
        assert stats["verification_errors"] == 2
        assert stats["cache_hit_rate"] == 0.3  # 3 / (3 + 7)
        assert "cache_stats" in stats
    
    def test_reset_stats(self, verification_engine):
        """Test resetting verification statistics."""
        # Set some stats
        verification_engine.stats["api_calls_made"] = 5
        verification_engine.stats["cache_hits"] = 2
        
        verification_engine.reset_stats()
        
        assert verification_engine.stats["api_calls_made"] == 0
        assert verification_engine.stats["cache_hits"] == 0
        assert verification_engine.stats["cache_misses"] == 0
    
    def test_clear_cache(self, verification_engine):
        """Test clearing verification cache."""
        # Add some cache entries
        verification_engine.cache.set("fork1", "repo1", "parent", "repo", {"ahead_by": 1})
        verification_engine.cache.set("fork2", "repo2", "parent", "repo", {"ahead_by": 2})
        
        assert len(verification_engine.cache._cache) == 2
        
        verification_engine.clear_cache()
        
        assert len(verification_engine.cache._cache) == 0


class TestCommitVerificationEngineIntegration:
    """Integration test scenarios for CommitVerificationEngine."""
    
    @pytest.fixture
    def mock_github_client(self):
        """Create mock GitHub client for integration tests."""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_progress_callback_integration(self, mock_github_client):
        """Test progress callback integration."""
        progress_messages = []
        
        def progress_callback(message):
            progress_messages.append(message)
        
        engine = CommitVerificationEngine(
            github_client=mock_github_client,
            progress_callback=progress_callback
        )
        
        # Create fork data
        metrics = ForkQualificationMetrics(
            id=123,
            name="test-fork",
            full_name="owner/test-fork",
            owner="owner",
            html_url="https://github.com/owner/test-fork",
            created_at=datetime.now(UTC) - timedelta(days=5),
            updated_at=datetime.now(UTC),
            pushed_at=datetime.now(UTC)
        )
        fork_data = CollectedForkData(metrics=metrics)
        
        # Mock successful responses
        fork_repo = Repository(
            id=123, name="test-fork", full_name="owner/test-fork",
            owner="owner", default_branch="main",
            url="https://api.github.com/repos/owner/test-fork",
            html_url="https://github.com/owner/test-fork",
            clone_url="https://github.com/owner/test-fork.git"
        )
        parent_repo = Repository(
            id=456, name="parent-repo", full_name="parent/parent-repo",
            owner="parent", default_branch="main",
            url="https://api.github.com/repos/parent/parent-repo",
            html_url="https://github.com/parent/parent-repo",
            clone_url="https://github.com/parent/parent-repo.git"
        )
        
        mock_github_client.get_repository.side_effect = [fork_repo, parent_repo]
        mock_github_client.compare_commits.return_value = {"ahead_by": 2, "behind_by": 0}
        
        await engine.batch_verify_forks([fork_data], "parent", "parent-repo")
        
        # Should have received progress callback
        assert len(progress_messages) > 0
        assert any("Verifying owner/test-fork" in msg for msg in progress_messages)
    
    @pytest.mark.asyncio
    async def test_concurrent_verification_limits(self, mock_github_client):
        """Test that concurrent verification respects limits."""
        engine = CommitVerificationEngine(
            github_client=mock_github_client,
            max_concurrent_requests=2  # Low limit for testing
        )
        
        # Create multiple fork data entries
        fork_data_list = []
        for i in range(5):
            metrics = ForkQualificationMetrics(
                id=100 + i,
                name=f"fork-{i}",
                full_name=f"owner/fork-{i}",
                owner="owner",
                html_url=f"https://github.com/owner/fork-{i}",
                created_at=datetime.now(UTC) - timedelta(days=5),
                updated_at=datetime.now(UTC),
                pushed_at=datetime.now(UTC)
            )
            fork_data_list.append(CollectedForkData(metrics=metrics))
        
        # Track concurrent calls
        active_calls = 0
        max_concurrent = 0
        
        async def mock_get_repository(*args, **kwargs):
            nonlocal active_calls, max_concurrent
            active_calls += 1
            max_concurrent = max(max_concurrent, active_calls)
            await asyncio.sleep(0.1)  # Simulate API delay
            active_calls -= 1
            return Repository(
                id=1, name="repo", full_name="owner/repo", owner="owner",
                default_branch="main", url="https://api.github.com/repos/owner/repo",
                html_url="https://github.com/owner/repo",
                clone_url="https://github.com/owner/repo.git"
            )
        
        mock_github_client.get_repository.side_effect = mock_get_repository
        mock_github_client.compare_commits.return_value = {"ahead_by": 1, "behind_by": 0}
        
        await engine.batch_verify_forks(fork_data_list, "parent", "parent-repo")
        
        # Should not exceed concurrent limit (accounting for fork + parent calls)
        assert max_concurrent <= engine.max_concurrent_requests