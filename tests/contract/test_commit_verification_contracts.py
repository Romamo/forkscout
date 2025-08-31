"""Contract tests for CommitVerificationEngine API behavior."""

import os
import pytest
from datetime import UTC, datetime, timedelta

from forklift.analysis.commit_verification_engine import CommitVerificationEngine
from forklift.config import GitHubConfig
from forklift.github.client import GitHubClient
from forklift.models.fork_qualification import CollectedForkData, ForkQualificationMetrics


@pytest.mark.contract
@pytest.mark.asyncio
class TestCommitVerificationEngineContracts:
    """Contract tests to verify API behavior and data structures."""
    
    @pytest.fixture
    async def github_client(self):
        """Create real GitHub client for contract tests."""
        token = os.getenv('GITHUB_TOKEN')
        if not token:
            pytest.skip("GitHub token required for contract tests")
        
        config = GitHubConfig(token=token)
        client = GitHubClient(config)
        
        yield client
        
        await client.close()
    
    @pytest.fixture
    def verification_engine(self, github_client):
        """Create CommitVerificationEngine for contract testing."""
        return CommitVerificationEngine(
            github_client=github_client,
            cache_ttl_hours=1,
            retry_attempts=1  # Single attempt for contract tests
        )
    
    async def test_get_commits_ahead_success_contract(self, verification_engine):
        """Test get_commits_ahead success response contract."""
        result = await verification_engine.get_commits_ahead(
            "octocat", "Hello-World",
            "octocat", "Hello-World"
        )
        
        # Verify required fields in success response
        assert isinstance(result, dict)
        assert "success" in result
        assert result["success"] is True
        
        # Verify commit count fields
        assert "ahead_by" in result
        assert "behind_by" in result
        assert "total_commits" in result
        assert isinstance(result["ahead_by"], int)
        assert isinstance(result["behind_by"], int)
        assert isinstance(result["total_commits"], int)
        
        # Verify metadata fields
        assert "verified_at" in result
        assert "verification_method" in result
        assert result["verification_method"] == "github_compare_api"
        
        # Verify optional fields
        if "commit_count" in result:
            assert isinstance(result["commit_count"], int)
        if "fork_default_branch" in result:
            assert isinstance(result["fork_default_branch"], str)
        if "parent_default_branch" in result:
            assert isinstance(result["parent_default_branch"], str)
        
        # Verify timestamp format
        verified_at = result["verified_at"]
        assert isinstance(verified_at, str)
        # Should be parseable as ISO format
        datetime.fromisoformat(verified_at.replace("Z", "+00:00"))
    
    async def test_get_commits_ahead_error_contract(self, verification_engine):
        """Test get_commits_ahead error response contract."""
        result = await verification_engine.get_commits_ahead(
            "nonexistent-user-12345", "nonexistent-repo-12345",
            "octocat", "Hello-World"
        )
        
        # Verify required fields in error response
        assert isinstance(result, dict)
        assert "success" in result
        assert result["success"] is False
        
        # Verify error fields
        assert "error" in result
        assert "error_message" in result
        assert isinstance(result["error"], str)
        assert isinstance(result["error_message"], str)
        
        # Verify fallback values
        assert "ahead_by" in result
        assert "behind_by" in result
        assert result["ahead_by"] == 0
        assert result["behind_by"] == 0
        
        # Verify metadata
        assert "verified_at" in result
        assert isinstance(result["verified_at"], str)
    
    async def test_batch_verify_forks_contract(self, verification_engine):
        """Test batch_verify_forks response contract."""
        # Create test fork data
        metrics = ForkQualificationMetrics(
            id=1296269,
            name="Hello-World",
            full_name="octocat/Hello-World",
            owner="octocat",
            html_url="https://github.com/octocat/Hello-World",
            created_at=datetime(2011, 1, 26, 19, 1, 12, tzinfo=UTC),
            updated_at=datetime.now(UTC) - timedelta(days=1),
            pushed_at=datetime(2011, 1, 26, 19, 14, 43, tzinfo=UTC)
        )
        fork_data = CollectedForkData(metrics=metrics)
        
        result = await verification_engine.batch_verify_forks(
            [fork_data],
            "octocat",
            "Hello-World"
        )
        
        # Verify return type and structure
        assert isinstance(result, list)
        assert len(result) == 1
        
        # Verify fork data structure is preserved
        fork_result = result[0]
        assert isinstance(fork_result, CollectedForkData)
        assert fork_result.metrics.id == 1296269
        assert fork_result.metrics.name == "Hello-World"
        
        # Verify verification results are added
        assert hasattr(fork_result, 'exact_commits_ahead')
        assert hasattr(fork_result, 'exact_commits_behind')
        
        # Verify verification result types
        ahead = fork_result.exact_commits_ahead
        behind = fork_result.exact_commits_behind
        
        assert ahead is not None
        assert behind is not None
        assert isinstance(ahead, (int, str))  # int for success, "Unknown" for error
        assert isinstance(behind, (int, str))
        
        if isinstance(ahead, str):
            assert ahead == "Unknown"
        if isinstance(behind, str):
            assert behind == "Unknown"
    
    async def test_verify_individual_fork_contract(self, verification_engine):
        """Test verify_individual_fork response contract."""
        # Create test fork data
        metrics = ForkQualificationMetrics(
            id=1296269,
            name="Hello-World",
            full_name="octocat/Hello-World",
            owner="octocat",
            html_url="https://github.com/octocat/Hello-World",
            created_at=datetime(2011, 1, 26, 19, 1, 12, tzinfo=UTC),
            updated_at=datetime.now(UTC) - timedelta(days=1),
            pushed_at=datetime(2011, 1, 26, 19, 14, 43, tzinfo=UTC)
        )
        fork_data = CollectedForkData(metrics=metrics)
        
        result = await verification_engine.verify_individual_fork(
            fork_data,
            "octocat",
            "Hello-World"
        )
        
        # Verify return type
        assert isinstance(result, CollectedForkData)
        
        # Verify original data is preserved
        assert result.metrics.id == fork_data.metrics.id
        assert result.metrics.name == fork_data.metrics.name
        assert result.metrics.full_name == fork_data.metrics.full_name
        
        # Verify verification results are added
        assert hasattr(result, 'exact_commits_ahead')
        assert hasattr(result, 'exact_commits_behind')
        
        # Verify result types
        ahead = result.exact_commits_ahead
        behind = result.exact_commits_behind
        
        assert ahead is not None
        assert behind is not None
        assert isinstance(ahead, (int, str))
        assert isinstance(behind, (int, str))
    
    async def test_get_verification_stats_contract(self, verification_engine):
        """Test get_verification_stats response contract."""
        # Perform some operations to generate stats
        await verification_engine.get_commits_ahead(
            "octocat", "Hello-World",
            "octocat", "Hello-World"
        )
        
        stats = verification_engine.get_verification_stats()
        
        # Verify required fields
        assert isinstance(stats, dict)
        
        required_fields = [
            "api_calls_made",
            "cache_hits",
            "cache_misses",
            "verification_errors",
            "successful_verifications",
            "cache_stats",
            "cache_hit_rate"
        ]
        
        for field in required_fields:
            assert field in stats, f"Missing required field: {field}"
        
        # Verify field types
        assert isinstance(stats["api_calls_made"], int)
        assert isinstance(stats["cache_hits"], int)
        assert isinstance(stats["cache_misses"], int)
        assert isinstance(stats["verification_errors"], int)
        assert isinstance(stats["successful_verifications"], int)
        assert isinstance(stats["cache_hit_rate"], float)
        assert isinstance(stats["cache_stats"], dict)
        
        # Verify cache stats structure
        cache_stats = stats["cache_stats"]
        cache_required_fields = ["total_entries", "valid_entries", "expired_entries"]
        
        for field in cache_required_fields:
            assert field in cache_stats, f"Missing cache stats field: {field}"
            assert isinstance(cache_stats[field], int)
        
        # Verify value ranges
        assert 0 <= stats["cache_hit_rate"] <= 1.0
        assert stats["api_calls_made"] >= 0
        assert stats["cache_hits"] >= 0
        assert stats["cache_misses"] >= 0
        assert stats["verification_errors"] >= 0
        assert stats["successful_verifications"] >= 0
    
    async def test_fork_qualification_metrics_contract(self, verification_engine):
        """Test that ForkQualificationMetrics contract is preserved."""
        # Create fork data with all required fields
        metrics = ForkQualificationMetrics(
            id=1296269,
            name="Hello-World",
            full_name="octocat/Hello-World",
            owner="octocat",
            html_url="https://github.com/octocat/Hello-World",
            stargazers_count=2500,
            forks_count=1300,
            watchers_count=2500,
            size=108,
            language="C",
            topics=[],
            open_issues_count=0,
            created_at=datetime(2011, 1, 26, 19, 1, 12, tzinfo=UTC),
            updated_at=datetime.now(UTC) - timedelta(days=1),
            pushed_at=datetime(2011, 1, 26, 19, 14, 43, tzinfo=UTC),
            archived=False,
            disabled=False,
            fork=True,
            license_key="mit",
            license_name="MIT License",
            description="My first repository on GitHub!",
            homepage=None,
            default_branch="master"
        )
        
        fork_data = CollectedForkData(metrics=metrics)
        
        result = await verification_engine.verify_individual_fork(
            fork_data,
            "octocat",
            "Hello-World"
        )
        
        # Verify all original metrics fields are preserved
        original_metrics = fork_data.metrics
        result_metrics = result.metrics
        
        assert result_metrics.id == original_metrics.id
        assert result_metrics.name == original_metrics.name
        assert result_metrics.full_name == original_metrics.full_name
        assert result_metrics.owner == original_metrics.owner
        assert result_metrics.html_url == original_metrics.html_url
        assert result_metrics.stargazers_count == original_metrics.stargazers_count
        assert result_metrics.forks_count == original_metrics.forks_count
        assert result_metrics.watchers_count == original_metrics.watchers_count
        assert result_metrics.size == original_metrics.size
        assert result_metrics.language == original_metrics.language
        assert result_metrics.topics == original_metrics.topics
        assert result_metrics.open_issues_count == original_metrics.open_issues_count
        assert result_metrics.created_at == original_metrics.created_at
        assert result_metrics.updated_at == original_metrics.updated_at
        assert result_metrics.pushed_at == original_metrics.pushed_at
        assert result_metrics.archived == original_metrics.archived
        assert result_metrics.disabled == original_metrics.disabled
        assert result_metrics.fork == original_metrics.fork
        assert result_metrics.license_key == original_metrics.license_key
        assert result_metrics.license_name == original_metrics.license_name
        assert result_metrics.description == original_metrics.description
        assert result_metrics.homepage == original_metrics.homepage
        assert result_metrics.default_branch == original_metrics.default_branch
        
        # Verify computed properties still work
        assert isinstance(result_metrics.days_since_creation, int)
        assert isinstance(result_metrics.days_since_last_update, int)
        assert isinstance(result_metrics.days_since_last_push, int)
        assert isinstance(result_metrics.commits_ahead_status, str)
        assert isinstance(result_metrics.can_skip_analysis, bool)
        assert isinstance(result_metrics.activity_ratio, float)
        assert isinstance(result_metrics.engagement_score, float)
    
    async def test_collected_fork_data_contract(self, verification_engine):
        """Test that CollectedForkData contract is preserved."""
        # Create fork data
        metrics = ForkQualificationMetrics(
            id=1296269,
            name="Hello-World",
            full_name="octocat/Hello-World",
            owner="octocat",
            html_url="https://github.com/octocat/Hello-World",
            created_at=datetime(2011, 1, 26, 19, 1, 12, tzinfo=UTC),
            updated_at=datetime.now(UTC) - timedelta(days=1),
            pushed_at=datetime(2011, 1, 26, 19, 14, 43, tzinfo=UTC)
        )
        
        original_fork_data = CollectedForkData(
            metrics=metrics,
            collection_timestamp=datetime.now(UTC),
            exact_commits_ahead=None,
            exact_commits_behind=None
        )
        
        result = await verification_engine.verify_individual_fork(
            original_fork_data,
            "octocat",
            "Hello-World"
        )
        
        # Verify original fields are preserved
        assert result.metrics == original_fork_data.metrics
        assert result.collection_timestamp == original_fork_data.collection_timestamp
        
        # Verify verification fields are updated
        assert result.exact_commits_ahead is not None
        assert result.exact_commits_behind is not None
        
        # Verify computed properties still work
        assert hasattr(result, 'activity_summary')
        assert hasattr(result, 'qualification_summary')
        assert isinstance(result.activity_summary, str)
        assert isinstance(result.qualification_summary, str)
    
    async def test_cache_contract_consistency(self, verification_engine):
        """Test that cache operations maintain data consistency."""
        # First call should populate cache
        result1 = await verification_engine.get_commits_ahead(
            "octocat", "Hello-World",
            "octocat", "Hello-World"
        )
        
        # Second call should use cache
        result2 = await verification_engine.get_commits_ahead(
            "octocat", "Hello-World",
            "octocat", "Hello-World"
        )
        
        # Results should be identical (deep equality)
        assert result1 == result2
        
        # Verify all fields match exactly
        for key in result1.keys():
            assert key in result2
            assert result1[key] == result2[key]
        
        for key in result2.keys():
            assert key in result1
    
    async def test_error_response_consistency(self, verification_engine):
        """Test that error responses are consistent across calls."""
        # Make multiple calls to nonexistent repository
        results = []
        for _ in range(3):
            result = await verification_engine.get_commits_ahead(
                "nonexistent-user-12345", "nonexistent-repo-12345",
                "octocat", "Hello-World",
                use_cache=False  # Disable cache to test consistency
            )
            results.append(result)
        
        # All error responses should have same structure
        for result in results:
            assert result["success"] is False
            assert result["error"] == "repository_not_found"
            assert result["ahead_by"] == 0
            assert result["behind_by"] == 0
            assert "error_message" in result
            assert "verified_at" in result
        
        # Error messages should be consistent
        error_messages = [r["error_message"] for r in results]
        assert all(msg == error_messages[0] for msg in error_messages)
    
    async def test_concurrent_operations_contract(self, verification_engine):
        """Test that concurrent operations maintain contract consistency."""
        # Create multiple fork data entries
        fork_data_list = []
        for i in range(3):
            metrics = ForkQualificationMetrics(
                id=1296269 + i,
                name=f"Hello-World-{i}",
                full_name="octocat/Hello-World",
                owner="octocat",
                html_url="https://github.com/octocat/Hello-World",
                created_at=datetime(2011, 1, 26, 19, 1, 12, tzinfo=UTC),
                updated_at=datetime.now(UTC) - timedelta(days=1),
                pushed_at=datetime(2011, 1, 26, 19, 14, 43, tzinfo=UTC)
            )
            fork_data_list.append(CollectedForkData(metrics=metrics))
        
        # Batch verification
        batch_results = await verification_engine.batch_verify_forks(
            fork_data_list,
            "octocat",
            "Hello-World"
        )
        
        # Individual verification
        individual_results = []
        for fork_data in fork_data_list:
            result = await verification_engine.verify_individual_fork(
                fork_data,
                "octocat",
                "Hello-World"
            )
            individual_results.append(result)
        
        # Results should be consistent between batch and individual operations
        assert len(batch_results) == len(individual_results)
        
        for batch_result, individual_result in zip(batch_results, individual_results):
            # Metrics should be identical
            assert batch_result.metrics.id == individual_result.metrics.id
            assert batch_result.metrics.name == individual_result.metrics.name
            
            # Verification results should be consistent (allowing for cache differences)
            if (batch_result.exact_commits_ahead != "Unknown" and 
                individual_result.exact_commits_ahead != "Unknown"):
                assert batch_result.exact_commits_ahead == individual_result.exact_commits_ahead
                assert batch_result.exact_commits_behind == individual_result.exact_commits_behind