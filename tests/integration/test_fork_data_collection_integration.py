"""Integration tests for fork data collection system using test repositories."""

import asyncio
import os
import time
from unittest.mock import AsyncMock, patch

import pytest

from forklift.analysis.fork_data_collection_engine import ForkDataCollectionEngine
from forklift.github.client import GitHubClient
from forklift.github.fork_list_processor import ForkListProcessor
from forklift.models.fork_qualification import QualifiedForksResult


class TestForkDataCollectionIntegration:
    """Integration tests for fork data collection with real test repositories."""

    # Test repositories with known fork patterns
    TEST_REPOSITORIES = [
        ("maliayas", "github-network-ninja"),  # Small repository for fast testing
        ("sanila2007", "youtube-bot-telegram"),  # Another small test repository
    ]

    @pytest.fixture
    def github_token(self):
        """Get GitHub token from environment."""
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            pytest.skip("GITHUB_TOKEN environment variable not set")
        return token

    @pytest.fixture
    async def github_client(self, github_token):
        """Create real GitHub client for integration tests."""
        async with GitHubClient(github_token) as client:
            yield client

    @pytest.fixture
    def fork_list_processor(self, github_client):
        """Create ForkListProcessor with real GitHub client."""
        return ForkListProcessor(github_client)

    @pytest.fixture
    def data_collection_engine(self):
        """Create ForkDataCollectionEngine."""
        return ForkDataCollectionEngine()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_fork_list_collection(self, fork_list_processor):
        """Test real fork list collection with test repository."""
        owner, repo = self.TEST_REPOSITORIES[0]  # Use first test repository

        # Track progress
        progress_calls = []

        def progress_callback(page, total_items):
            progress_calls.append((page, total_items))

        start_time = time.time()
        forks_data = await fork_list_processor.get_all_forks_list_data(
            owner, repo, progress_callback=progress_callback
        )
        processing_time = time.time() - start_time

        # Verify results
        assert isinstance(forks_data, list)
        assert processing_time < 30.0  # Should complete within 30 seconds

        # Verify progress tracking
        if len(forks_data) > 0:
            assert len(progress_calls) > 0
            assert all(isinstance(call, tuple) and len(call) == 2 for call in progress_calls)

        # Verify data structure
        if len(forks_data) > 0:
            sample_fork = forks_data[0]
            required_fields = ["id", "name", "full_name", "owner", "html_url", "created_at", "updated_at", "pushed_at"]
            for field in required_fields:
                assert field in sample_fork, f"Missing required field: {field}"

        print(f"Collected {len(forks_data)} forks in {processing_time:.2f} seconds")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_fork_data_collection_workflow(
        self, fork_list_processor, data_collection_engine
    ):
        """Test complete fork data collection workflow with real data."""
        owner, repo = self.TEST_REPOSITORIES[0]

        start_time = time.time()

        # Step 1: Collect raw fork data
        raw_forks_data = await fork_list_processor.get_all_forks_list_data(owner, repo)

        # Step 2: Process fork data
        collected_forks = data_collection_engine.collect_fork_data_from_list(raw_forks_data)

        # Step 3: Create qualification result
        result = data_collection_engine.create_qualification_result(
            repository_owner=owner,
            repository_name=repo,
            collected_forks=collected_forks,
            processing_time_seconds=time.time() - start_time,
            api_calls_made=len(raw_forks_data) // 100 + (1 if len(raw_forks_data) % 100 > 0 else 0),
            api_calls_saved=len(raw_forks_data),  # Each fork would need individual call
        )

        total_time = time.time() - start_time

        # Verify complete workflow
        assert isinstance(result, QualifiedForksResult)
        assert result.repository_owner == owner
        assert result.repository_name == repo
        assert len(result.collected_forks) == len(raw_forks_data)
        assert total_time < 60.0  # Complete workflow should finish within 60 seconds

        # Verify statistics make sense
        assert result.stats.total_forks_discovered >= 0
        assert result.stats.forks_with_commits >= 0
        assert result.stats.forks_with_no_commits >= 0
        assert result.stats.forks_with_commits + result.stats.forks_with_no_commits == result.stats.total_forks_discovered

        # Verify computed properties work
        assert len(result.forks_needing_analysis) == result.stats.forks_with_commits
        assert len(result.forks_to_skip) == result.stats.forks_with_no_commits

        print(f"Complete workflow processed {result.stats.total_forks_discovered} forks in {total_time:.2f} seconds")
        print(f"API efficiency: {result.stats.efficiency_percentage:.1f}%")
        print(f"Forks needing analysis: {len(result.forks_needing_analysis)}")
        print(f"Forks to skip: {len(result.forks_to_skip)}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fork_data_validation_with_real_data(self, fork_list_processor):
        """Test fork data validation with real GitHub API responses."""
        owner, repo = self.TEST_REPOSITORIES[1]  # Use second test repository

        forks_data = await fork_list_processor.get_all_forks_list_data(owner, repo)

        if len(forks_data) == 0:
            pytest.skip(f"No forks found for {owner}/{repo}")

        # Test validation with real data
        valid_count = 0
        invalid_count = 0

        for fork_data in forks_data:
            is_valid = fork_list_processor.validate_fork_data_completeness(fork_data)
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1

        # Most real data should be valid
        total_forks = len(forks_data)
        validity_rate = valid_count / total_forks if total_forks > 0 else 0

        assert validity_rate >= 0.9  # At least 90% of real data should be valid
        print(f"Data validation: {valid_count}/{total_forks} valid ({validity_rate:.1%})")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_qualification_fields_extraction_real_data(self, fork_list_processor):
        """Test qualification fields extraction with real GitHub data."""
        owner, repo = self.TEST_REPOSITORIES[0]

        forks_data = await fork_list_processor.get_all_forks_list_data(owner, repo)

        if len(forks_data) == 0:
            pytest.skip(f"No forks found for {owner}/{repo}")

        # Test extraction with first fork
        sample_fork = forks_data[0]
        extracted_fields = fork_list_processor.extract_qualification_fields(sample_fork)

        # Verify all expected fields are present
        expected_fields = [
            "id", "name", "full_name", "owner", "html_url",
            "stargazers_count", "forks_count", "watchers_count",
            "size", "language", "topics", "open_issues_count",
            "created_at", "updated_at", "pushed_at",
            "archived", "disabled", "fork",
            "license_key", "license_name",
            "description", "homepage", "default_branch"
        ]

        for field in expected_fields:
            assert field in extracted_fields, f"Missing field: {field}"

        # Verify field types
        assert isinstance(extracted_fields["id"], int)
        assert isinstance(extracted_fields["name"], str)
        assert isinstance(extracted_fields["stargazers_count"], int)
        assert isinstance(extracted_fields["topics"], list)
        assert isinstance(extracted_fields["archived"], bool)

        print(f"Successfully extracted {len(extracted_fields)} fields from real fork data")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_commits_ahead_detection_real_patterns(self, data_collection_engine):
        """Test commits ahead detection with real fork patterns."""
        # Create realistic test cases based on actual GitHub patterns
        real_patterns = [
            # Pattern 1: Fork with commits (typical case)
            {
                "created_at": "2023-06-15T10:30:00Z",
                "pushed_at": "2023-08-20T14:45:22Z",  # Pushed after creation
                "full_name": "user/active-fork",
                "expected_status": "Has commits",
                "expected_can_skip": False,
            },
            # Pattern 2: Fork with no commits (created_at == pushed_at)
            {
                "created_at": "2023-09-10T12:00:00Z",
                "pushed_at": "2023-09-10T12:00:00Z",  # Same time
                "full_name": "user/stale-fork",
                "expected_status": "No commits ahead",
                "expected_can_skip": True,
            },
            # Pattern 3: Fork created after last push (edge case)
            {
                "created_at": "2023-07-01T15:30:00Z",
                "pushed_at": "2023-06-30T20:15:00Z",  # Pushed before creation
                "full_name": "user/edge-case-fork",
                "expected_status": "No commits ahead",
                "expected_can_skip": True,
            },
        ]

        for pattern in real_patterns:
            status, can_skip = data_collection_engine.determine_commits_ahead_status(pattern)

            assert status == pattern["expected_status"], f"Wrong status for {pattern['full_name']}"
            assert can_skip == pattern["expected_can_skip"], f"Wrong can_skip for {pattern['full_name']}"

        print(f"Verified commits ahead detection for {len(real_patterns)} real patterns")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_handling_with_real_api_conditions(self, github_client):
        """Test error handling with real API conditions."""
        processor = ForkListProcessor(github_client)

        # Test with non-existent repository
        with pytest.raises(Exception):  # Should raise some form of API error
            await processor.get_all_forks_list_data("nonexistent", "repository")

        # Test with invalid repository name
        with pytest.raises(Exception):
            await processor.get_all_forks_list_data("", "")

        print("Error handling verified with real API conditions")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_performance_with_varying_repository_sizes(self, fork_list_processor, data_collection_engine):
        """Test performance with repositories of different sizes."""
        performance_results = []

        for owner, repo in self.TEST_REPOSITORIES:
            start_time = time.time()

            # Collect fork data
            forks_data = await fork_list_processor.get_all_forks_list_data(owner, repo)

            # Process data
            collected_forks = data_collection_engine.collect_fork_data_from_list(forks_data)

            processing_time = time.time() - start_time
            fork_count = len(forks_data)

            performance_results.append({
                "repository": f"{owner}/{repo}",
                "fork_count": fork_count,
                "processing_time": processing_time,
                "forks_per_second": fork_count / processing_time if processing_time > 0 else 0,
            })

            # Verify reasonable performance
            assert processing_time < 120.0  # Should complete within 2 minutes
            if fork_count > 0:
                assert processing_time / fork_count < 1.0  # Less than 1 second per fork

        # Print performance summary
        print("\nPerformance Results:")
        for result in performance_results:
            print(f"  {result['repository']}: {result['fork_count']} forks in {result['processing_time']:.2f}s "
                  f"({result['forks_per_second']:.1f} forks/sec)")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_data_consistency_across_multiple_runs(self, fork_list_processor):
        """Test data consistency across multiple collection runs."""
        owner, repo = self.TEST_REPOSITORIES[0]

        # Run collection twice
        run1_data = await fork_list_processor.get_all_forks_list_data(owner, repo)
        await asyncio.sleep(1)  # Small delay
        run2_data = await fork_list_processor.get_all_forks_list_data(owner, repo)

        # Data should be consistent (same forks, same order for newest sort)
        assert len(run1_data) == len(run2_data), "Fork count changed between runs"

        if len(run1_data) > 0:
            # Compare first few forks (order should be consistent with "newest" sort)
            compare_count = min(5, len(run1_data))
            for i in range(compare_count):
                assert run1_data[i]["id"] == run2_data[i]["id"], f"Fork order changed at position {i}"

        print(f"Data consistency verified across multiple runs ({len(run1_data)} forks)")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_comprehensive_workflow_with_filters(self, fork_list_processor, data_collection_engine):
        """Test comprehensive workflow with various filtering options."""
        owner, repo = self.TEST_REPOSITORIES[0]

        # Collect all fork data
        all_forks_data = await fork_list_processor.get_all_forks_list_data(owner, repo)
        all_collected = data_collection_engine.collect_fork_data_from_list(all_forks_data)

        if len(all_collected) == 0:
            pytest.skip(f"No forks found for {owner}/{repo}")

        # Test different filtering scenarios
        filtering_results = {}

        # 1. Exclude archived and disabled
        filtered_active = data_collection_engine.exclude_archived_and_disabled(all_collected)
        filtering_results["active"] = len(filtered_active)

        # 2. Exclude forks with no commits ahead
        filtered_with_commits = data_collection_engine.exclude_no_commits_ahead(all_collected)
        filtering_results["with_commits"] = len(filtered_with_commits)

        # 3. Organize by status
        active, archived_disabled, no_commits = data_collection_engine.organize_forks_by_status(all_collected)
        filtering_results["organized"] = {
            "active": len(active),
            "archived_disabled": len(archived_disabled),
            "no_commits": len(no_commits),
        }

        # Verify filtering logic
        total_forks = len(all_collected)
        assert filtering_results["active"] <= total_forks
        assert filtering_results["with_commits"] <= total_forks

        organized = filtering_results["organized"]
        assert organized["active"] + organized["archived_disabled"] + organized["no_commits"] == total_forks

        print(f"Filtering results for {owner}/{repo}:")
        print(f"  Total forks: {total_forks}")
        print(f"  Active forks: {filtering_results['active']}")
        print(f"  Forks with commits: {filtering_results['with_commits']}")
        print(f"  Organized - Active: {organized['active']}, Archived/Disabled: {organized['archived_disabled']}, No commits: {organized['no_commits']}")


class TestForkDataCollectionContractTests:
    """Contract tests for GitHub API fork list response handling."""

    @pytest.fixture
    def mock_github_client(self):
        """Create mock GitHub client for contract tests."""
        return AsyncMock()

    @pytest.fixture
    def processor(self, mock_github_client):
        """Create processor with mock client."""
        return ForkListProcessor(mock_github_client)

    def test_github_api_response_contract_minimal(self, processor):
        """Test contract for minimal valid GitHub API response."""
        minimal_response = {
            "id": 123456789,
            "name": "test-repo",
            "full_name": "user/test-repo",
            "owner": {"login": "user"},
            "html_url": "https://github.com/user/test-repo",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
            "pushed_at": "2023-01-01T00:00:00Z",
        }

        # Should validate successfully
        assert processor.validate_fork_data_completeness(minimal_response) is True

        # Should extract fields successfully
        fields = processor.extract_qualification_fields(minimal_response)
        assert fields["id"] == 123456789
        assert fields["name"] == "test-repo"
        assert fields["owner"] == "user"

    def test_github_api_response_contract_comprehensive(self, processor):
        """Test contract for comprehensive GitHub API response."""
        comprehensive_response = {
            "id": 987654321,
            "name": "comprehensive-repo",
            "full_name": "developer/comprehensive-repo",
            "owner": {
                "login": "developer",
                "id": 12345,
                "avatar_url": "https://avatars.githubusercontent.com/u/12345",
                "type": "User",
            },
            "html_url": "https://github.com/developer/comprehensive-repo",
            "description": "A comprehensive test repository",
            "fork": True,
            "url": "https://api.github.com/repos/developer/comprehensive-repo",
            "created_at": "2023-06-15T14:30:22Z",
            "updated_at": "2024-01-20T09:45:33Z",
            "pushed_at": "2024-01-22T16:20:15Z",
            "clone_url": "https://github.com/developer/comprehensive-repo.git",
            "size": 15420,
            "stargazers_count": 47,
            "watchers_count": 35,
            "language": "Python",
            "forks_count": 12,
            "archived": False,
            "disabled": False,
            "open_issues_count": 8,
            "license": {
                "key": "mit",
                "name": "MIT License",
                "spdx_id": "MIT",
                "url": "https://api.github.com/licenses/mit",
            },
            "topics": ["python", "testing", "api"],
            "visibility": "public",
            "default_branch": "main",
            "homepage": "https://developer.github.io/comprehensive-repo",
        }

        # Should validate successfully
        assert processor.validate_fork_data_completeness(comprehensive_response) is True

        # Should extract all fields successfully
        fields = processor.extract_qualification_fields(comprehensive_response)

        # Verify all expected fields
        assert fields["id"] == 987654321
        assert fields["name"] == "comprehensive-repo"
        assert fields["full_name"] == "developer/comprehensive-repo"
        assert fields["owner"] == "developer"
        assert fields["html_url"] == "https://github.com/developer/comprehensive-repo"
        assert fields["description"] == "A comprehensive test repository"
        assert fields["stargazers_count"] == 47
        assert fields["forks_count"] == 12
        assert fields["watchers_count"] == 35
        assert fields["size"] == 15420
        assert fields["language"] == "Python"
        assert fields["topics"] == ["python", "testing", "api"]
        assert fields["open_issues_count"] == 8
        assert fields["archived"] is False
        assert fields["disabled"] is False
        assert fields["fork"] is True
        assert fields["license_key"] == "mit"
        assert fields["license_name"] == "MIT License"
        assert fields["homepage"] == "https://developer.github.io/comprehensive-repo"
        assert fields["default_branch"] == "main"

    def test_github_api_response_contract_edge_cases(self, processor):
        """Test contract for GitHub API response edge cases."""
        edge_cases = [
            # Case 1: Null license
            {
                "id": 111111111,
                "name": "no-license",
                "full_name": "user/no-license",
                "owner": {"login": "user"},
                "html_url": "https://github.com/user/no-license",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "pushed_at": "2023-01-01T00:00:00Z",
                "license": None,
            },
            # Case 2: Empty topics
            {
                "id": 222222222,
                "name": "no-topics",
                "full_name": "user/no-topics",
                "owner": {"login": "user"},
                "html_url": "https://github.com/user/no-topics",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "pushed_at": "2023-01-01T00:00:00Z",
                "topics": [],
            },
            # Case 3: Null description and homepage
            {
                "id": 333333333,
                "name": "minimal-info",
                "full_name": "user/minimal-info",
                "owner": {"login": "user"},
                "html_url": "https://github.com/user/minimal-info",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "pushed_at": "2023-01-01T00:00:00Z",
                "description": None,
                "homepage": None,
            },
        ]

        for i, edge_case in enumerate(edge_cases):
            # Should validate successfully
            assert processor.validate_fork_data_completeness(edge_case) is True, f"Edge case {i+1} failed validation"

            # Should extract fields successfully
            fields = processor.extract_qualification_fields(edge_case)
            assert fields["id"] == edge_case["id"], f"Edge case {i+1} failed extraction"

    def test_github_api_response_contract_invalid_cases(self, processor):
        """Test contract for invalid GitHub API responses."""
        invalid_cases = [
            # Case 1: Missing required field
            {
                "name": "missing-id",
                "full_name": "user/missing-id",
                "owner": {"login": "user"},
                "html_url": "https://github.com/user/missing-id",
            },
            # Case 2: Missing owner
            {
                "id": 123456789,
                "name": "missing-owner",
                "full_name": "user/missing-owner",
                "html_url": "https://github.com/user/missing-owner",
            },
            # Case 3: Missing owner login
            {
                "id": 123456789,
                "name": "missing-owner-login",
                "full_name": "user/missing-owner-login",
                "owner": {},
                "html_url": "https://github.com/user/missing-owner-login",
            },
        ]

        for i, invalid_case in enumerate(invalid_cases):
            # Should fail validation
            assert processor.validate_fork_data_completeness(invalid_case) is False, f"Invalid case {i+1} should fail validation"

    @pytest.mark.asyncio
    async def test_api_pagination_contract(self, processor, mock_github_client):
        """Test contract for GitHub API pagination behavior."""
        # Mock paginated responses
        page1_response = [{"id": i, "name": f"fork-{i}", "full_name": f"user{i}/fork-{i}",
                          "owner": {"login": f"user{i}"}, "html_url": f"https://github.com/user{i}/fork-{i}",
                          "created_at": "2023-01-01T00:00:00Z", "updated_at": "2023-01-01T00:00:00Z",
                          "pushed_at": "2023-01-01T00:00:00Z"} for i in range(100)]  # Full page

        page2_response = [{"id": i, "name": f"fork-{i}", "full_name": f"user{i}/fork-{i}",
                          "owner": {"login": f"user{i}"}, "html_url": f"https://github.com/user{i}/fork-{i}",
                          "created_at": "2023-01-01T00:00:00Z", "updated_at": "2023-01-01T00:00:00Z",
                          "pushed_at": "2023-01-01T00:00:00Z"} for i in range(100, 150)]  # Partial page

        empty_response = []  # End of pagination

        mock_github_client.get.side_effect = [page1_response, page2_response, empty_response]

        # Test pagination
        result = await processor.get_all_forks_list_data("owner", "repo")

        # Verify pagination contract
        assert len(result) == 150  # 100 + 50
        assert mock_github_client.get.call_count == 2  # Should stop after empty response

        # Verify API calls follow contract
        expected_calls = [
            (("repos/owner/repo/forks",), {"params": {"sort": "newest", "per_page": 100, "page": 1}}),
            (("repos/owner/repo/forks",), {"params": {"sort": "newest", "per_page": 100, "page": 2}}),
        ]

        actual_calls = mock_github_client.get.call_args_list
        for i, (expected_args, expected_kwargs) in enumerate(expected_calls):
            actual_args, actual_kwargs = actual_calls[i]
            assert actual_args == expected_args
            assert actual_kwargs == expected_kwargs