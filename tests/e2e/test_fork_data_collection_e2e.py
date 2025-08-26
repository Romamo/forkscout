"""End-to-end tests for complete fork data collection workflow with real data."""

import asyncio
import os
import time
from unittest.mock import patch

import pytest

from forklift.analysis.fork_data_collection_engine import ForkDataCollectionEngine
from forklift.analysis.fork_discovery import ForkDiscoveryService
from forklift.config.settings import ForkliftConfig, GitHubConfig
from forklift.github.client import GitHubClient
from forklift.github.fork_list_processor import ForkListProcessor


class TestForkDataCollectionEndToEnd:
    """End-to-end tests for complete fork data collection workflow."""

    # Test repositories with different characteristics
    TEST_REPOSITORIES = [
        {
            "owner": "maliayas",
            "repo": "github-network-ninja",
            "description": "Small repository for fast testing",
            "expected_min_forks": 0,
            "expected_max_forks": 50,
        },
        {
            "owner": "sanila2007", 
            "repo": "youtube-bot-telegram",
            "description": "Another small test repository",
            "expected_min_forks": 0,
            "expected_max_forks": 20,
        },
    ]

    @pytest.fixture
    def github_token(self):
        """Get GitHub token from environment."""
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            pytest.skip("GITHUB_TOKEN environment variable not set")
        return token

    @pytest.fixture
    def config(self, github_token):
        """Create ForkliftConfig for testing."""
        config = ForkliftConfig()
        config.github = GitHubConfig(token=github_token)
        return config

    @pytest.fixture
    async def github_client(self, github_token):
        """Create real GitHub client."""
        async with GitHubClient(github_token) as client:
            yield client

    @pytest.fixture
    def fork_list_processor(self, github_client):
        """Create ForkListProcessor with real client."""
        return ForkListProcessor(github_client)

    @pytest.fixture
    def data_collection_engine(self):
        """Create ForkDataCollectionEngine."""
        return ForkDataCollectionEngine()

    @pytest.fixture
    def fork_discovery_service(self, github_client):
        """Create ForkDiscoveryService with real client."""
        processor = ForkListProcessor(github_client)
        engine = ForkDataCollectionEngine()
        return ForkDiscoveryService(github_client, processor, engine)

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_complete_workflow_small_repository(
        self, fork_discovery_service, config
    ):
        """Test complete workflow with small repository."""
        test_repo = self.TEST_REPOSITORIES[0]
        repo_url = f"https://github.com/{test_repo['owner']}/{test_repo['repo']}"

        start_time = time.time()

        # Execute complete workflow
        result = await fork_discovery_service.discover_and_collect_fork_data(
            repo_url, disable_cache=True
        )

        total_time = time.time() - start_time

        # Verify workflow completion
        assert result is not None
        assert result.repository_owner == test_repo["owner"]
        assert result.repository_name == test_repo["repo"]
        assert total_time < 120.0  # Should complete within 2 minutes

        # Verify fork count is within expected range
        fork_count = result.stats.total_forks_discovered
        assert test_repo["expected_min_forks"] <= fork_count <= test_repo["expected_max_forks"]

        # Verify statistics consistency
        assert result.stats.forks_with_commits + result.stats.forks_with_no_commits == fork_count
        assert result.stats.api_calls_made > 0
        assert result.stats.processing_time_seconds > 0

        print(f"Complete workflow test - {test_repo['description']}:")
        print(f"  Repository: {repo_url}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Forks discovered: {fork_count}")
        print(f"  API calls made: {result.stats.api_calls_made}")
        print(f"  Efficiency: {result.stats.efficiency_percentage:.1f}%")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_workflow_with_all_test_repositories(
        self, fork_discovery_service
    ):
        """Test workflow with all test repositories."""
        results = []

        for test_repo in self.TEST_REPOSITORIES:
            repo_url = f"https://github.com/{test_repo['owner']}/{test_repo['repo']}"

            start_time = time.time()
            try:
                result = await fork_discovery_service.discover_and_collect_fork_data(
                    repo_url, disable_cache=True
                )
                processing_time = time.time() - start_time

                results.append({
                    "repo": f"{test_repo['owner']}/{test_repo['repo']}",
                    "success": True,
                    "result": result,
                    "time": processing_time,
                    "error": None,
                })

            except Exception as e:
                processing_time = time.time() - start_time
                results.append({
                    "repo": f"{test_repo['owner']}/{test_repo['repo']}",
                    "success": False,
                    "result": None,
                    "time": processing_time,
                    "error": str(e),
                })

        # Verify at least one repository processed successfully
        successful_results = [r for r in results if r["success"]]
        assert len(successful_results) > 0, "At least one repository should process successfully"

        # Print summary
        print(f"Workflow test with all repositories:")
        for result in results:
            status = "SUCCESS" if result["success"] else "FAILED"
            print(f"  {result['repo']}: {status} ({result['time']:.2f}s)")
            if result["success"]:
                stats = result["result"].stats
                print(f"    Forks: {stats.total_forks_discovered}, "
                      f"API calls: {stats.api_calls_made}, "
                      f"Efficiency: {stats.efficiency_percentage:.1f}%")
            else:
                print(f"    Error: {result['error']}")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_workflow_components_integration(
        self, github_client, fork_list_processor, data_collection_engine
    ):
        """Test integration between workflow components."""
        test_repo = self.TEST_REPOSITORIES[0]
        owner, repo = test_repo["owner"], test_repo["repo"]

        # Step 1: Raw fork data collection
        step1_start = time.time()
        raw_forks = await fork_list_processor.get_all_forks_list_data(owner, repo)
        step1_time = time.time() - step1_start

        # Step 2: Data processing and qualification
        step2_start = time.time()
        collected_forks = data_collection_engine.collect_fork_data_from_list(raw_forks)
        step2_time = time.time() - step2_start

        # Step 3: Result creation
        step3_start = time.time()
        result = data_collection_engine.create_qualification_result(
            repository_owner=owner,
            repository_name=repo,
            collected_forks=collected_forks,
            processing_time_seconds=step1_time + step2_time,
            api_calls_made=len(raw_forks) // 100 + (1 if len(raw_forks) % 100 > 0 else 0),
            api_calls_saved=len(raw_forks),
        )
        step3_time = time.time() - step3_start

        total_time = step1_time + step2_time + step3_time

        # Verify component integration
        assert len(raw_forks) == len(collected_forks)
        assert len(collected_forks) == result.stats.total_forks_discovered
        assert total_time < 60.0  # Should complete within 1 minute

        print(f"Component integration test:")
        print(f"  Step 1 (Raw collection): {step1_time:.3f}s")
        print(f"  Step 2 (Data processing): {step2_time:.3f}s") 
        print(f"  Step 3 (Result creation): {step3_time:.3f}s")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Forks processed: {len(collected_forks)}")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_workflow_error_recovery(self, fork_discovery_service):
        """Test workflow error recovery with invalid repository."""
        invalid_repo_url = "https://github.com/nonexistent/repository"

        start_time = time.time()
        with pytest.raises(Exception):  # Should raise some form of error
            await fork_discovery_service.discover_and_collect_fork_data(
                invalid_repo_url, disable_cache=True
            )
        
        error_time = time.time() - start_time

        # Error should be detected quickly
        assert error_time < 30.0  # Should fail within 30 seconds

        print(f"Error recovery test:")
        print(f"  Invalid repository: {invalid_repo_url}")
        print(f"  Error detection time: {error_time:.2f}s")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_workflow_with_cache_disabled(self, fork_discovery_service):
        """Test complete workflow with cache disabled."""
        test_repo = self.TEST_REPOSITORIES[0]
        repo_url = f"https://github.com/{test_repo['owner']}/{test_repo['repo']}"

        # Run twice with cache disabled
        start_time = time.time()
        result1 = await fork_discovery_service.discover_and_collect_fork_data(
            repo_url, disable_cache=True
        )
        run1_time = time.time() - start_time

        start_time = time.time()
        result2 = await fork_discovery_service.discover_and_collect_fork_data(
            repo_url, disable_cache=True
        )
        run2_time = time.time() - start_time

        # Results should be consistent
        assert result1.stats.total_forks_discovered == result2.stats.total_forks_discovered
        assert result1.repository_owner == result2.repository_owner
        assert result1.repository_name == result2.repository_name

        # Both runs should complete within reasonable time
        assert run1_time < 120.0
        assert run2_time < 120.0

        print(f"Cache disabled workflow test:")
        print(f"  Run 1: {run1_time:.2f}s, {result1.stats.total_forks_discovered} forks")
        print(f"  Run 2: {run2_time:.2f}s, {result2.stats.total_forks_discovered} forks")
        print(f"  Consistency: {'PASS' if result1.stats.total_forks_discovered == result2.stats.total_forks_discovered else 'FAIL'}")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_workflow_data_quality_validation(self, fork_discovery_service):
        """Test data quality validation in complete workflow."""
        test_repo = self.TEST_REPOSITORIES[0]
        repo_url = f"https://github.com/{test_repo['owner']}/{test_repo['repo']}"

        result = await fork_discovery_service.discover_and_collect_fork_data(
            repo_url, disable_cache=True
        )

        if result.stats.total_forks_discovered == 0:
            pytest.skip("No forks found for data quality validation")

        # Validate data quality
        for fork_data in result.collected_forks:
            metrics = fork_data.metrics

            # Verify required fields
            assert metrics.id > 0
            assert len(metrics.name) > 0
            assert len(metrics.full_name) > 0
            assert len(metrics.owner) > 0
            assert metrics.html_url.startswith("https://github.com/")

            # Verify computed properties
            assert metrics.commits_ahead_status in ["Has commits", "No commits ahead"]
            assert isinstance(metrics.can_skip_analysis, bool)
            assert metrics.days_since_creation >= 0
            assert 0.0 <= metrics.activity_ratio <= 1.0
            assert metrics.engagement_score >= 0.0

            # Verify timestamps are reasonable
            assert metrics.created_at.year >= 2008  # GitHub founded in 2008
            assert metrics.updated_at >= metrics.created_at
            
        print(f"Data quality validation:")
        print(f"  Forks validated: {result.stats.total_forks_discovered}")
        print(f"  All forks passed quality checks: PASS")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_workflow_performance_benchmarks(self, fork_discovery_service):
        """Test workflow performance benchmarks."""
        performance_targets = {
            "max_total_time": 180.0,  # 3 minutes max
            "min_forks_per_second": 5.0,  # At least 5 forks per second
            "min_api_efficiency": 80.0,  # At least 80% API efficiency
        }

        test_repo = self.TEST_REPOSITORIES[0]
        repo_url = f"https://github.com/{test_repo['owner']}/{test_repo['repo']}"

        start_time = time.time()
        result = await fork_discovery_service.discover_and_collect_fork_data(
            repo_url, disable_cache=True
        )
        total_time = time.time() - start_time

        # Calculate performance metrics
        fork_count = result.stats.total_forks_discovered
        forks_per_second = fork_count / total_time if total_time > 0 else 0
        api_efficiency = result.stats.efficiency_percentage

        # Verify performance targets
        assert total_time <= performance_targets["max_total_time"]
        if fork_count > 0:
            assert forks_per_second >= performance_targets["min_forks_per_second"]
        assert api_efficiency >= performance_targets["min_api_efficiency"]

        print(f"Performance benchmark test:")
        print(f"  Total time: {total_time:.2f}s (target: <{performance_targets['max_total_time']}s)")
        print(f"  Forks per second: {forks_per_second:.1f} (target: >{performance_targets['min_forks_per_second']})")
        print(f"  API efficiency: {api_efficiency:.1f}% (target: >{performance_targets['min_api_efficiency']}%)")
        print(f"  All benchmarks: {'PASS' if all([
            total_time <= performance_targets['max_total_time'],
            forks_per_second >= performance_targets['min_forks_per_second'] or fork_count == 0,
            api_efficiency >= performance_targets['min_api_efficiency']
        ]) else 'FAIL'}")