"""Comprehensive unit tests for fork data collection system with realistic data."""

import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from forklift.analysis.fork_data_collection_engine import (
    ForkDataCollectionEngine,
    ForkDataCollectionError,
)
from forklift.github.fork_list_processor import (
    ForkListProcessor,
    ForkListProcessingError,
)
from forklift.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualificationStats,
    QualifiedForksResult,
)


class TestForkDataCollectionWithRealisticData:
    """Test fork data collection with realistic GitHub fork data patterns."""

    @pytest.fixture
    def realistic_fork_data_active(self):
        """Create realistic active fork data based on real GitHub patterns."""
        return {
            "id": 456789123,
            "name": "pandas-ta-enhanced",
            "full_name": "activedev/pandas-ta-enhanced",
            "owner": {"login": "activedev"},
            "html_url": "https://github.com/activedev/pandas-ta-enhanced",
            "stargazers_count": 47,
            "forks_count": 12,
            "watchers_count": 35,
            "size": 15420,  # KB
            "language": "Python",
            "topics": ["pandas", "technical-analysis", "trading", "finance", "indicators"],
            "open_issues_count": 8,
            "created_at": "2023-03-15T14:30:22Z",
            "updated_at": "2024-08-20T09:45:33Z",
            "pushed_at": "2024-08-22T16:20:15Z",  # Recent activity
            "archived": False,
            "disabled": False,
            "fork": True,
            "license": {"key": "mit", "name": "MIT License"},
            "description": "Enhanced pandas-ta with additional indicators and performance improvements",
            "homepage": "https://activedev.github.io/pandas-ta-enhanced",
            "default_branch": "main",
        }

    @pytest.fixture
    def realistic_fork_data_stale(self):
        """Create realistic stale fork data (no commits ahead)."""
        return {
            "id": 789123456,
            "name": "pandas-ta",
            "full_name": "staleuser/pandas-ta",
            "owner": {"login": "staleuser"},
            "html_url": "https://github.com/staleuser/pandas-ta",
            "stargazers_count": 2,
            "forks_count": 0,
            "watchers_count": 2,
            "size": 12800,
            "language": "Python",
            "topics": ["pandas", "technical-analysis"],
            "open_issues_count": 0,
            "created_at": "2023-08-10T10:15:30Z",
            "updated_at": "2023-08-10T10:15:30Z",
            "pushed_at": "2023-08-10T10:15:30Z",  # Same as created_at - no commits
            "archived": False,
            "disabled": False,
            "fork": True,
            "license": {"key": "mit", "name": "MIT License"},
            "description": None,
            "homepage": None,
            "default_branch": "main",
        }

    @pytest.fixture
    def realistic_fork_data_archived(self):
        """Create realistic archived fork data."""
        return {
            "id": 123456789,
            "name": "pandas-ta-old",
            "full_name": "oldmaintainer/pandas-ta-old",
            "owner": {"login": "oldmaintainer"},
            "html_url": "https://github.com/oldmaintainer/pandas-ta-old",
            "stargazers_count": 15,
            "forks_count": 3,
            "watchers_count": 12,
            "size": 11200,
            "language": "Python",
            "topics": ["pandas", "technical-analysis", "archived"],
            "open_issues_count": 0,
            "created_at": "2022-01-15T08:20:45Z",
            "updated_at": "2022-12-20T14:30:22Z",
            "pushed_at": "2023-01-05T11:45:18Z",  # Has commits but archived
            "archived": True,  # Archived repository
            "disabled": False,
            "fork": True,
            "license": {"key": "apache-2.0", "name": "Apache License 2.0"},
            "description": "Legacy pandas technical analysis fork - now archived",
            "homepage": None,
            "default_branch": "master",
        }

    @pytest.fixture
    def realistic_fork_data_popular(self):
        """Create realistic popular fork data with high engagement."""
        return {
            "id": 987654321,
            "name": "pandas-ta-pro",
            "full_name": "populardev/pandas-ta-pro",
            "owner": {"login": "populardev"},
            "html_url": "https://github.com/populardev/pandas-ta-pro",
            "stargazers_count": 234,
            "forks_count": 67,
            "watchers_count": 189,
            "size": 28500,
            "language": "Python",
            "topics": [
                "pandas",
                "technical-analysis",
                "trading",
                "finance",
                "indicators",
                "backtesting",
                "cryptocurrency",
            ],
            "open_issues_count": 23,
            "created_at": "2022-11-08T16:45:12Z",
            "updated_at": "2024-01-25T20:30:45Z",
            "pushed_at": "2024-01-26T08:15:33Z",  # Very recent activity
            "archived": False,
            "disabled": False,
            "fork": True,
            "license": {"key": "bsd-3-clause", "name": "BSD 3-Clause License"},
            "description": "Professional-grade pandas technical analysis with advanced indicators and backtesting",
            "homepage": "https://pandas-ta-pro.readthedocs.io",
            "default_branch": "develop",
        }

    @pytest.fixture
    def realistic_fork_data_minimal(self):
        """Create realistic minimal fork data (edge case)."""
        return {
            "id": 111222333,
            "name": "pandas-ta",
            "full_name": "minimaluser/pandas-ta",
            "owner": {"login": "minimaluser"},
            "html_url": "https://github.com/minimaluser/pandas-ta",
            "stargazers_count": 0,
            "forks_count": 0,
            "watchers_count": 0,
            "size": 0,
            "language": None,
            "topics": [],
            "open_issues_count": 0,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "pushed_at": "2023-12-31T23:59:59Z",  # Pushed before creation
            "archived": False,
            "disabled": False,
            "fork": True,
            "license": None,
            "description": None,
            "homepage": None,
            "default_branch": "main",
        }

    @pytest.fixture
    def engine(self):
        """Create ForkDataCollectionEngine instance."""
        return ForkDataCollectionEngine()

    def test_collect_realistic_fork_data_mixed_scenarios(
        self,
        engine,
        realistic_fork_data_active,
        realistic_fork_data_stale,
        realistic_fork_data_archived,
        realistic_fork_data_popular,
        realistic_fork_data_minimal,
    ):
        """Test collecting data from realistic mixed fork scenarios."""
        forks_list_data = [
            realistic_fork_data_active,
            realistic_fork_data_stale,
            realistic_fork_data_archived,
            realistic_fork_data_popular,
            realistic_fork_data_minimal,
        ]

        result = engine.collect_fork_data_from_list(forks_list_data)

        # Verify all forks were processed
        assert len(result) == 5

        # Verify each fork has correct characteristics
        fork_names = [fork.metrics.name for fork in result]
        assert "pandas-ta-enhanced" in fork_names
        assert "pandas-ta" in fork_names
        assert "pandas-ta-old" in fork_names
        assert "pandas-ta-pro" in fork_names

        # Verify commits ahead status detection
        active_fork = next(
            f for f in result if f.metrics.name == "pandas-ta-enhanced"
        )
        assert active_fork.metrics.commits_ahead_status == "Has commits"
        assert not active_fork.metrics.can_skip_analysis

        stale_fork = next(f for f in result if f.metrics.owner == "staleuser")
        assert stale_fork.metrics.commits_ahead_status == "No commits ahead"
        assert stale_fork.metrics.can_skip_analysis

        # Verify archived detection
        archived_fork = next(f for f in result if f.metrics.archived)
        assert archived_fork.metrics.name == "pandas-ta-old"
        assert archived_fork.metrics.commits_ahead_status == "Has commits"

        # Verify popular fork characteristics
        popular_fork = next(f for f in result if f.metrics.name == "pandas-ta-pro")
        assert popular_fork.metrics.stargazers_count == 234
        assert popular_fork.metrics.engagement_score > 50
        assert len(popular_fork.metrics.topics) == 7

    def test_activity_patterns_calculation_realistic_data(
        self, engine, realistic_fork_data_active
    ):
        """Test activity patterns calculation with realistic timestamps."""
        patterns = engine.calculate_activity_patterns(realistic_fork_data_active)

        # Verify all pattern fields are present
        required_fields = [
            "days_since_creation",
            "days_since_last_update",
            "days_since_last_push",
            "activity_ratio",
            "created_at",
            "updated_at",
            "pushed_at",
        ]
        for field in required_fields:
            assert field in patterns

        # Verify realistic values
        assert patterns["days_since_creation"] > 300  # Created in March 2023
        assert patterns["days_since_last_push"] > 0  # Has some age
        assert 0.0 <= patterns["activity_ratio"] <= 1.0

        # Verify datetime objects
        assert isinstance(patterns["created_at"], datetime)
        assert isinstance(patterns["updated_at"], datetime)
        assert isinstance(patterns["pushed_at"], datetime)

    def test_commits_ahead_detection_edge_cases(self, engine):
        """Test commits ahead detection with various edge cases."""
        # Case 1: Created exactly at push time
        exact_match_data = {
            "created_at": "2024-01-15T12:00:00Z",
            "pushed_at": "2024-01-15T12:00:00Z",
            "full_name": "user/exact-match",
        }
        status, can_skip = engine.determine_commits_ahead_status(exact_match_data)
        assert status == "No commits ahead"
        assert can_skip is True

        # Case 2: Created 1 second after push
        created_after_data = {
            "created_at": "2024-01-15T12:00:01Z",
            "pushed_at": "2024-01-15T12:00:00Z",
            "full_name": "user/created-after",
        }
        status, can_skip = engine.determine_commits_ahead_status(created_after_data)
        assert status == "No commits ahead"
        assert can_skip is True

        # Case 3: Pushed 1 second after creation
        pushed_after_data = {
            "created_at": "2024-01-15T12:00:00Z",
            "pushed_at": "2024-01-15T12:00:01Z",
            "full_name": "user/pushed-after",
        }
        status, can_skip = engine.determine_commits_ahead_status(pushed_after_data)
        assert status == "Has commits"
        assert can_skip is False

    def test_organize_forks_by_status_realistic_distribution(
        self,
        engine,
        realistic_fork_data_active,
        realistic_fork_data_stale,
        realistic_fork_data_archived,
        realistic_fork_data_popular,
    ):
        """Test organizing forks by status with realistic distribution."""
        # Collect fork data first
        forks_list_data = [
            realistic_fork_data_active,
            realistic_fork_data_stale,
            realistic_fork_data_archived,
            realistic_fork_data_popular,
        ]
        collected_forks = engine.collect_fork_data_from_list(forks_list_data)

        # Organize by status
        active, archived_disabled, no_commits = engine.organize_forks_by_status(
            collected_forks
        )

        # Verify organization
        assert len(active) == 2  # active and popular forks
        assert len(archived_disabled) == 1  # archived fork
        assert len(no_commits) == 1  # stale fork

        # Verify correct categorization
        active_names = [fork.metrics.name for fork in active]
        assert "pandas-ta-enhanced" in active_names
        assert "pandas-ta-pro" in active_names

        archived_names = [fork.metrics.name for fork in archived_disabled]
        assert "pandas-ta-old" in archived_names

        no_commits_names = [fork.metrics.owner for fork in no_commits]
        assert "staleuser" in no_commits_names

    def test_create_qualification_result_with_realistic_stats(
        self, engine, realistic_fork_data_active, realistic_fork_data_stale
    ):
        """Test creating qualification result with realistic statistics."""
        forks_list_data = [realistic_fork_data_active, realistic_fork_data_stale]
        collected_forks = engine.collect_fork_data_from_list(forks_list_data)

        result = engine.create_qualification_result(
            repository_owner="aarigs",
            repository_name="pandas-ta",
            collected_forks=collected_forks,
            processing_time_seconds=2.5,
            api_calls_made=1,  # Single page
            api_calls_saved=2,  # Two forks would need individual calls
        )

        # Verify result structure
        assert isinstance(result, QualifiedForksResult)
        assert result.repository_owner == "aarigs"
        assert result.repository_name == "pandas-ta"
        assert result.repository_url == "https://github.com/aarigs/pandas-ta"

        # Verify statistics
        assert result.stats.total_forks_discovered == 2
        assert result.stats.forks_with_commits == 1  # Active fork
        assert result.stats.forks_with_no_commits == 1  # Stale fork
        assert result.stats.api_calls_made == 1
        assert result.stats.api_calls_saved == 2
        assert result.stats.processing_time_seconds == 2.5

        # Verify computed properties
        assert abs(result.stats.efficiency_percentage - (2 / 3 * 100)) < 0.1  # ~66.67%
        assert result.stats.skip_rate_percentage == 50.0  # 1 out of 2
        assert result.stats.analysis_candidate_percentage == 50.0  # 1 out of 2

        # Verify computed fork lists
        assert len(result.forks_needing_analysis) == 1
        assert len(result.forks_to_skip) == 1

    def test_performance_timing_tracking(
        self, engine, realistic_fork_data_active, realistic_fork_data_popular
    ):
        """Test that performance timing is properly tracked."""
        forks_list_data = [realistic_fork_data_active, realistic_fork_data_popular]

        start_time = time.time()
        result = engine.collect_fork_data_from_list(forks_list_data)
        end_time = time.time()

        # Verify processing completed
        assert len(result) == 2

        # Verify timing is reasonable (should be very fast for unit test)
        processing_time = end_time - start_time
        assert processing_time < 1.0  # Should complete in under 1 second

    def test_error_resilience_with_mixed_valid_invalid_data(self, engine):
        """Test error resilience when processing mixed valid and invalid data."""
        valid_fork = {
            "id": 123456,
            "name": "valid-fork",
            "full_name": "user/valid-fork",
            "owner": {"login": "user"},
            "html_url": "https://github.com/user/valid-fork",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "pushed_at": "2024-01-01T00:00:00Z",
        }

        invalid_forks = [
            None,  # Null data
            {},  # Empty data
            {"invalid": "structure"},  # Invalid structure
            {"id": "not_a_number"},  # Invalid field type
        ]

        mixed_data = [valid_fork] + invalid_forks

        # Should not raise exception, but should process only valid data
        result = engine.collect_fork_data_from_list(mixed_data)

        assert len(result) == 1
        assert result[0].metrics.name == "valid-fork"

    def test_large_dataset_simulation(self, engine):
        """Test processing a large number of forks (simulated)."""
        # Create a base fork template
        base_fork = {
            "id": 100000,
            "name": "test-fork",
            "full_name": "user/test-fork",
            "owner": {"login": "user"},
            "html_url": "https://github.com/user/test-fork",
            "stargazers_count": 1,
            "forks_count": 0,
            "watchers_count": 1,
            "size": 1000,
            "language": "Python",
            "topics": ["test"],
            "open_issues_count": 0,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "pushed_at": "2024-01-02T00:00:00Z",  # Has commits
            "archived": False,
            "disabled": False,
            "fork": True,
            "license": {"key": "mit", "name": "MIT License"},
            "description": "Test fork",
            "homepage": None,
            "default_branch": "main",
        }

        # Generate 100 forks with variations
        large_dataset = []
        for i in range(100):
            fork = base_fork.copy()
            fork["id"] = 100000 + i
            fork["name"] = f"test-fork-{i}"
            fork["full_name"] = f"user{i}/test-fork-{i}"
            fork["owner"] = {"login": f"user{i}"}
            fork["html_url"] = f"https://github.com/user{i}/test-fork-{i}"
            fork["stargazers_count"] = i % 10  # Vary stars 0-9

            # Make some forks have no commits (every 10th fork)
            if i % 10 == 0:
                fork["pushed_at"] = fork["created_at"]

            large_dataset.append(fork)

        start_time = time.time()
        result = engine.collect_fork_data_from_list(large_dataset)
        processing_time = time.time() - start_time

        # Verify all forks processed
        assert len(result) == 100

        # Verify performance is reasonable (should be fast for in-memory processing)
        assert processing_time < 5.0  # Should complete in under 5 seconds

        # Verify statistics
        forks_with_commits = sum(
            1 for fork in result if not fork.metrics.can_skip_analysis
        )
        forks_no_commits = sum(
            1 for fork in result if fork.metrics.can_skip_analysis
        )

        assert forks_with_commits == 90  # 90% have commits
        assert forks_no_commits == 10  # 10% have no commits


class TestForkListProcessorRealisticScenarios:
    """Test ForkListProcessor with realistic GitHub API scenarios."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return AsyncMock()

    @pytest.fixture
    def processor(self, mock_github_client):
        """Create ForkListProcessor with mock client."""
        return ForkListProcessor(mock_github_client)

    @pytest.fixture
    def realistic_github_api_response_page1(self):
        """Create realistic first page of GitHub API response."""
        forks = []
        for i in range(100):  # Full page
            fork = {
                "id": 500000 + i,
                "name": f"pandas-ta-fork-{i}",
                "full_name": f"user{i}/pandas-ta-fork-{i}",
                "owner": {"login": f"user{i}"},
                "html_url": f"https://github.com/user{i}/pandas-ta-fork-{i}",
                "stargazers_count": i % 20,  # 0-19 stars
                "forks_count": i % 5,  # 0-4 forks
                "watchers_count": i % 15,  # 0-14 watchers
                "size": 10000 + (i * 100),  # Varying sizes
                "language": "Python" if i % 3 == 0 else "JavaScript",
                "topics": ["pandas", "technical-analysis"] if i % 2 == 0 else [],
                "open_issues_count": i % 10,
                "created_at": f"2023-{(i % 12) + 1:02d}-01T00:00:00Z",
                "updated_at": f"2024-01-{(i % 28) + 1:02d}T00:00:00Z",
                "pushed_at": f"2024-01-{(i % 28) + 1:02d}T12:00:00Z",
                "archived": i % 50 == 0,  # 2% archived
                "disabled": i % 100 == 0,  # 1% disabled
                "fork": True,
                "license": {"key": "mit", "name": "MIT License"} if i % 3 == 0 else None,
                "description": f"Fork {i} of pandas-ta" if i % 4 == 0 else None,
                "homepage": f"https://user{i}.github.io" if i % 10 == 0 else None,
                "default_branch": "main" if i % 2 == 0 else "master",
            }
            forks.append(fork)
        return forks

    @pytest.fixture
    def realistic_github_api_response_page2(self):
        """Create realistic second page of GitHub API response (partial)."""
        forks = []
        for i in range(45):  # Partial page
            fork = {
                "id": 600000 + i,
                "name": f"pandas-ta-fork-{100 + i}",
                "full_name": f"user{100 + i}/pandas-ta-fork-{100 + i}",
                "owner": {"login": f"user{100 + i}"},
                "html_url": f"https://github.com/user{100 + i}/pandas-ta-fork-{100 + i}",
                "stargazers_count": i % 30,
                "forks_count": i % 8,
                "watchers_count": i % 20,
                "size": 15000 + (i * 200),
                "language": "Python",
                "topics": ["pandas", "technical-analysis", "trading"],
                "open_issues_count": i % 15,
                "created_at": f"2023-{(i % 12) + 1:02d}-15T00:00:00Z",
                "updated_at": f"2024-01-{(i % 28) + 1:02d}T06:00:00Z",
                "pushed_at": f"2023-{(i % 12) + 1:02d}-15T00:00:00Z",  # Same as created - no commits
                "archived": False,
                "disabled": False,
                "fork": True,
                "license": {"key": "apache-2.0", "name": "Apache License 2.0"},
                "description": f"Enhanced fork {100 + i}",
                "homepage": None,
                "default_branch": "develop",
            }
            forks.append(fork)
        return forks

    @pytest.mark.asyncio
    async def test_realistic_paginated_fork_collection(
        self,
        processor,
        mock_github_client,
        realistic_github_api_response_page1,
        realistic_github_api_response_page2,
    ):
        """Test realistic paginated fork collection."""
        # Mock paginated responses
        mock_github_client.get.side_effect = [
            realistic_github_api_response_page1,
            realistic_github_api_response_page2,
        ]

        # Track progress calls
        progress_calls = []

        def progress_callback(page, total_items):
            progress_calls.append((page, total_items))

        # Test collection
        result = await processor.get_all_forks_list_data(
            "aarigs", "pandas-ta", progress_callback=progress_callback
        )

        # Verify results
        assert len(result) == 145  # 100 + 45
        assert len(progress_calls) == 2
        assert progress_calls[0] == (1, 100)
        assert progress_calls[1] == (2, 145)

        # Verify API calls
        assert mock_github_client.get.call_count == 2
        mock_github_client.get.assert_any_call(
            "repos/aarigs/pandas-ta/forks",
            params={"sort": "newest", "per_page": 100, "page": 1},
        )
        mock_github_client.get.assert_any_call(
            "repos/aarigs/pandas-ta/forks",
            params={"sort": "newest", "per_page": 100, "page": 2},
        )

    @pytest.mark.asyncio
    async def test_complete_workflow_with_realistic_data(
        self,
        processor,
        mock_github_client,
        realistic_github_api_response_page1,
        realistic_github_api_response_page2,
    ):
        """Test complete fork collection and processing workflow."""
        # Mock paginated responses
        mock_github_client.get.side_effect = [
            realistic_github_api_response_page1,
            realistic_github_api_response_page2,
        ]

        # Test complete workflow
        result = await processor.collect_and_process_forks("aarigs", "pandas-ta")

        # Verify result structure
        assert isinstance(result, QualifiedForksResult)
        assert result.repository_owner == "aarigs"
        assert result.repository_name == "pandas-ta"

        # Verify statistics
        assert result.stats.total_forks_discovered == 145
        assert result.stats.api_calls_made == 2  # Two pages
        assert result.stats.api_calls_saved == 145  # Each fork would need individual call

        # Verify efficiency
        assert result.stats.efficiency_percentage > 95  # Very efficient

        # Verify fork categorization
        # Page 1: Most forks have commits (pushed_at != created_at)
        # Page 2: All forks have no commits (pushed_at == created_at)
        assert result.stats.forks_with_commits == 100  # All from page 1
        assert result.stats.forks_with_no_commits == 45  # All from page 2

        # Verify archived/disabled counts
        assert result.stats.archived_forks == 2  # 2% of page 1
        assert result.stats.disabled_forks == 1  # 1% of page 1

        # Verify computed properties
        assert len(result.forks_needing_analysis) == 100
        assert len(result.forks_to_skip) == 45

    def test_data_validation_with_realistic_edge_cases(self, processor):
        """Test data validation with realistic edge cases from GitHub API."""
        # Valid minimal fork
        valid_minimal = {
            "id": 123456,
            "name": "minimal-fork",
            "full_name": "user/minimal-fork",
            "owner": {"login": "user"},
            "html_url": "https://github.com/user/minimal-fork",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "pushed_at": "2024-01-01T00:00:00Z",
        }
        assert processor.validate_fork_data_completeness(valid_minimal) is True

        # Missing owner login (real GitHub edge case)
        missing_owner_login = valid_minimal.copy()
        missing_owner_login["owner"] = {}
        assert processor.validate_fork_data_completeness(missing_owner_login) is False

        # Invalid timestamp format (could happen with API changes)
        invalid_timestamp = valid_minimal.copy()
        invalid_timestamp["created_at"] = 1640995200  # Unix timestamp instead of ISO
        assert processor.validate_fork_data_completeness(invalid_timestamp) is False

        # Null values in numeric fields (GitHub API sometimes returns null)
        null_numeric = valid_minimal.copy()
        null_numeric["stargazers_count"] = None
        assert processor.validate_fork_data_completeness(null_numeric) is True  # Should handle gracefully

    def test_qualification_fields_extraction_comprehensive(self, processor):
        """Test comprehensive qualification fields extraction."""
        comprehensive_fork = {
            "id": 987654321,
            "name": "comprehensive-fork",
            "full_name": "developer/comprehensive-fork",
            "owner": {"login": "developer"},
            "html_url": "https://github.com/developer/comprehensive-fork",
            "stargazers_count": 156,
            "forks_count": 34,
            "watchers_count": 123,
            "size": 45600,
            "language": "TypeScript",
            "topics": ["typescript", "react", "web", "frontend", "ui", "components"],
            "open_issues_count": 12,
            "created_at": "2023-05-20T14:30:45Z",
            "updated_at": "2024-01-25T09:15:22Z",
            "pushed_at": "2024-01-26T16:45:33Z",
            "archived": False,
            "disabled": False,
            "fork": True,
            "license": {"key": "bsd-2-clause", "name": "BSD 2-Clause License"},
            "description": "A comprehensive fork with many enhancements and features",
            "homepage": "https://comprehensive-fork.dev",
            "default_branch": "develop",
        }

        result = processor.extract_qualification_fields(comprehensive_fork)

        # Verify all fields extracted correctly
        assert result["id"] == 987654321
        assert result["name"] == "comprehensive-fork"
        assert result["full_name"] == "developer/comprehensive-fork"
        assert result["owner"] == "developer"
        assert result["stargazers_count"] == 156
        assert result["language"] == "TypeScript"
        assert result["topics"] == ["typescript", "react", "web", "frontend", "ui", "components"]
        assert result["license_key"] == "bsd-2-clause"
        assert result["license_name"] == "BSD 2-Clause License"
        assert result["description"] == "A comprehensive fork with many enhancements and features"
        assert result["homepage"] == "https://comprehensive-fork.dev"
        assert result["default_branch"] == "develop"


class TestForkQualificationMetricsRealisticScenarios:
    """Test ForkQualificationMetrics with realistic GitHub data scenarios."""

    def test_from_github_api_with_comprehensive_real_data(self):
        """Test creating metrics from comprehensive real GitHub API data."""
        real_github_data = {
            "id": 456789123,
            "name": "pandas-ta-enhanced",
            "full_name": "activedev/pandas-ta-enhanced",
            "owner": {"login": "activedev"},
            "html_url": "https://github.com/activedev/pandas-ta-enhanced",
            "stargazers_count": 89,
            "forks_count": 23,
            "watchers_count": 67,
            "size": 18750,
            "language": "Python",
            "topics": ["pandas", "technical-analysis", "trading", "finance", "indicators", "backtesting"],
            "open_issues_count": 15,
            "created_at": "2023-02-14T10:30:45Z",
            "updated_at": "2024-08-28T14:20:33Z",
            "pushed_at": "2024-08-29T09:15:22Z",
            "archived": False,
            "disabled": False,
            "fork": True,
            "license": {"key": "mit", "name": "MIT License"},
            "description": "Enhanced pandas-ta with additional indicators, performance improvements, and comprehensive documentation",
            "homepage": "https://pandas-ta-enhanced.readthedocs.io",
            "default_branch": "main",
        }

        metrics = ForkQualificationMetrics.from_github_api(real_github_data)

        # Verify all fields correctly mapped
        assert metrics.id == 456789123
        assert metrics.name == "pandas-ta-enhanced"
        assert metrics.full_name == "activedev/pandas-ta-enhanced"
        assert metrics.owner == "activedev"
        assert metrics.html_url == "https://github.com/activedev/pandas-ta-enhanced"
        assert metrics.stargazers_count == 89
        assert metrics.forks_count == 23
        assert metrics.watchers_count == 67
        assert metrics.size == 18750
        assert metrics.language == "Python"
        assert metrics.topics == ["pandas", "technical-analysis", "trading", "finance", "indicators", "backtesting"]
        assert metrics.open_issues_count == 15
        assert not metrics.archived
        assert not metrics.disabled
        assert metrics.fork
        assert metrics.license_key == "mit"
        assert metrics.license_name == "MIT License"
        assert metrics.description.startswith("Enhanced pandas-ta")
        assert metrics.homepage == "https://pandas-ta-enhanced.readthedocs.io"
        assert metrics.default_branch == "main"

        # Verify computed properties
        assert metrics.commits_ahead_status == "Has commits"
        assert not metrics.can_skip_analysis
        assert metrics.days_since_creation > 300  # Created in Feb 2023
        assert metrics.days_since_last_push > 0  # Has some age
        assert 0.0 <= metrics.activity_ratio <= 1.0
        assert metrics.engagement_score > 30  # High engagement

    def test_computed_properties_with_realistic_scenarios(self):
        """Test computed properties with various realistic scenarios."""
        now = datetime.utcnow()

        # Scenario 1: Very active popular fork
        active_popular = ForkQualificationMetrics(
            id=1,
            name="active-popular",
            full_name="dev/active-popular",
            owner="dev",
            html_url="https://github.com/dev/active-popular",
            stargazers_count=150,
            forks_count=45,
            watchers_count=120,
            created_at=now - timedelta(days=365),  # 1 year old
            updated_at=now - timedelta(days=1),    # Updated yesterday
            pushed_at=now - timedelta(days=1),     # Pushed yesterday
        )

        assert active_popular.commits_ahead_status == "Has commits"
        assert not active_popular.can_skip_analysis
        assert active_popular.days_since_creation >= 365
        assert active_popular.days_since_last_push <= 1
        assert active_popular.activity_ratio > 0.99  # Very active
        assert active_popular.engagement_score > 50  # High engagement

        # Scenario 2: Stale fork with no commits
        stale_fork = ForkQualificationMetrics(
            id=2,
            name="stale-fork",
            full_name="user/stale-fork",
            owner="user",
            html_url="https://github.com/user/stale-fork",
            stargazers_count=2,
            forks_count=0,
            watchers_count=1,
            created_at=now - timedelta(days=100),
            updated_at=now - timedelta(days=100),
            pushed_at=now - timedelta(days=101),  # Pushed before creation
        )

        assert stale_fork.commits_ahead_status == "No commits ahead"
        assert stale_fork.can_skip_analysis
        assert stale_fork.days_since_creation >= 100
        assert stale_fork.days_since_last_push >= 101
        assert stale_fork.engagement_score < 5  # Low engagement

        # Scenario 3: Moderately active fork
        moderate_fork = ForkQualificationMetrics(
            id=3,
            name="moderate-fork",
            full_name="dev2/moderate-fork",
            owner="dev2",
            html_url="https://github.com/dev2/moderate-fork",
            stargazers_count=25,
            forks_count=8,
            watchers_count=20,
            created_at=now - timedelta(days=200),  # 200 days old
            updated_at=now - timedelta(days=30),   # Updated 30 days ago
            pushed_at=now - timedelta(days=30),    # Pushed 30 days ago
        )

        assert moderate_fork.commits_ahead_status == "Has commits"
        assert not moderate_fork.can_skip_analysis
        assert moderate_fork.days_since_creation >= 200
        assert moderate_fork.days_since_last_push >= 30
        assert 0.8 <= moderate_fork.activity_ratio <= 0.9  # Moderately active
        assert 10 <= moderate_fork.engagement_score <= 30  # Moderate engagement

    def test_edge_cases_with_realistic_data_variations(self):
        """Test edge cases with realistic data variations."""
        now = datetime.utcnow()

        # Edge case 1: Fork created and pushed at exact same time
        exact_timing = ForkQualificationMetrics(
            id=1,
            name="exact-timing",
            full_name="user/exact-timing",
            owner="user",
            html_url="https://github.com/user/exact-timing",
            created_at=datetime(2024, 1, 15, 12, 0, 0),
            updated_at=datetime(2024, 1, 15, 12, 0, 0),
            pushed_at=datetime(2024, 1, 15, 12, 0, 0),
        )

        assert exact_timing.commits_ahead_status == "No commits ahead"
        assert exact_timing.can_skip_analysis

        # Edge case 2: Very new fork (created today)
        brand_new = ForkQualificationMetrics(
            id=2,
            name="brand-new",
            full_name="user/brand-new",
            owner="user",
            html_url="https://github.com/user/brand-new",
            created_at=now - timedelta(hours=1),
            updated_at=now - timedelta(minutes=30),
            pushed_at=now - timedelta(minutes=15),
        )

        assert brand_new.commits_ahead_status == "Has commits"
        assert not brand_new.can_skip_analysis
        assert brand_new.days_since_creation == 0
        assert brand_new.activity_ratio == 1.0  # Fully active (new)

        # Edge case 3: Very old inactive fork
        ancient_fork = ForkQualificationMetrics(
            id=3,
            name="ancient-fork",
            full_name="olduser/ancient-fork",
            owner="olduser",
            html_url="https://github.com/olduser/ancient-fork",
            created_at=now - timedelta(days=1000),  # ~3 years old
            updated_at=now - timedelta(days=800),   # Last updated 800 days ago
            pushed_at=now - timedelta(days=800),    # Last pushed 800 days ago
        )

        assert ancient_fork.commits_ahead_status == "Has commits"
        assert not ancient_fork.can_skip_analysis
        assert ancient_fork.days_since_creation >= 1000
        assert ancient_fork.days_since_last_push >= 800
        assert ancient_fork.activity_ratio <= 0.2  # Very inactive