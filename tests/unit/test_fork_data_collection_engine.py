"""Unit tests for ForkDataCollectionEngine."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from forkscout.analysis.fork_data_collection_engine import (
    ForkDataCollectionEngine,
    ForkDataCollectionError,
)
from forkscout.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualifiedForksResult,
)


class TestForkDataCollectionEngine:
    """Test cases for ForkDataCollectionEngine."""

    @pytest.fixture
    def engine(self):
        """Create ForkDataCollectionEngine instance."""
        return ForkDataCollectionEngine()

    @pytest.fixture
    def sample_fork_data(self):
        """Create sample fork data from GitHub API."""
        return {
            "id": 123456,
            "name": "test-repo",
            "full_name": "testuser/test-repo",
            "owner": {"login": "testuser"},
            "html_url": "https://github.com/testuser/test-repo",
            "stargazers_count": 10,
            "forks_count": 5,
            "watchers_count": 8,
            "size": 1024,
            "language": "Python",
            "topics": ["python", "testing"],
            "open_issues_count": 3,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-06-01T00:00:00Z",
            "pushed_at": "2023-06-15T00:00:00Z",
            "archived": False,
            "disabled": False,
            "fork": True,
            "license": {"key": "mit", "name": "MIT License"},
            "description": "Test repository",
            "homepage": "https://example.com",
            "default_branch": "main",
        }

    @pytest.fixture
    def sample_fork_data_no_commits(self):
        """Create sample fork data with no commits ahead (created_at >= pushed_at)."""
        return {
            "id": 789012,
            "name": "no-commits-repo",
            "full_name": "testuser/no-commits-repo",
            "owner": {"login": "testuser"},
            "html_url": "https://github.com/testuser/no-commits-repo",
            "stargazers_count": 0,
            "forks_count": 0,
            "watchers_count": 0,
            "size": 100,
            "language": "JavaScript",
            "topics": [],
            "open_issues_count": 0,
            "created_at": "2023-06-15T00:00:00Z",
            "updated_at": "2023-06-15T00:00:00Z",
            "pushed_at": "2023-06-15T00:00:00Z",  # Same as created_at
            "archived": False,
            "disabled": False,
            "fork": True,
            "license": None,
            "description": None,
            "homepage": None,
            "default_branch": "main",
        }

    @pytest.fixture
    def sample_archived_fork_data(self):
        """Create sample archived fork data."""
        return {
            "id": 345678,
            "name": "archived-repo",
            "full_name": "testuser/archived-repo",
            "owner": {"login": "testuser"},
            "html_url": "https://github.com/testuser/archived-repo",
            "stargazers_count": 2,
            "forks_count": 1,
            "watchers_count": 2,
            "size": 500,
            "language": "Java",
            "topics": ["java"],
            "open_issues_count": 0,
            "created_at": "2022-01-01T00:00:00Z",
            "updated_at": "2022-06-01T00:00:00Z",
            "pushed_at": "2022-06-15T00:00:00Z",
            "archived": True,  # Archived fork
            "disabled": False,
            "fork": True,
            "license": {"key": "apache-2.0", "name": "Apache License 2.0"},
            "description": "Archived test repository",
            "homepage": None,
            "default_branch": "master",
        }

    def test_collect_fork_data_from_list_success(self, engine, sample_fork_data):
        """Test successful fork data collection from list."""
        forks_list_data = [sample_fork_data]

        result = engine.collect_fork_data_from_list(forks_list_data)

        assert len(result) == 1
        assert isinstance(result[0], CollectedForkData)
        assert result[0].metrics.full_name == "testuser/test-repo"
        assert result[0].metrics.stargazers_count == 10
        assert result[0].metrics.language == "Python"

    def test_collect_fork_data_from_list_multiple_forks(
        self, engine, sample_fork_data, sample_fork_data_no_commits
    ):
        """Test collecting data from multiple forks."""
        forks_list_data = [sample_fork_data, sample_fork_data_no_commits]

        result = engine.collect_fork_data_from_list(forks_list_data)

        assert len(result) == 2
        assert result[0].metrics.full_name == "testuser/test-repo"
        assert result[1].metrics.full_name == "testuser/no-commits-repo"

    def test_collect_fork_data_from_list_empty_list(self, engine):
        """Test collecting data from empty list."""
        result = engine.collect_fork_data_from_list([])

        assert result == []

    def test_collect_fork_data_from_list_invalid_data(self, engine):
        """Test collecting data with invalid fork data."""
        invalid_fork_data = {"invalid": "data"}
        forks_list_data = [invalid_fork_data]

        # Should not raise exception, but should skip invalid data
        result = engine.collect_fork_data_from_list(forks_list_data)

        assert result == []

    def test_extract_fork_metrics_success(self, engine, sample_fork_data):
        """Test successful fork metrics extraction."""
        metrics = engine.extract_fork_metrics(sample_fork_data)

        assert isinstance(metrics, ForkQualificationMetrics)
        assert metrics.id == 123456
        assert metrics.name == "test-repo"
        assert metrics.full_name == "testuser/test-repo"
        assert metrics.owner == "testuser"
        assert metrics.stargazers_count == 10
        assert metrics.language == "Python"
        assert metrics.topics == ["python", "testing"]

    def test_extract_fork_metrics_missing_required_field(self, engine):
        """Test fork metrics extraction with missing required field."""
        invalid_data = {"name": "test-repo"}  # Missing required fields

        with pytest.raises(ForkDataCollectionError):
            engine.extract_fork_metrics(invalid_data)

    def test_calculate_activity_patterns_success(self, engine, sample_fork_data):
        """Test successful activity patterns calculation."""
        patterns = engine.calculate_activity_patterns(sample_fork_data)

        assert "days_since_creation" in patterns
        assert "days_since_last_update" in patterns
        assert "days_since_last_push" in patterns
        assert "activity_ratio" in patterns
        assert "created_at" in patterns
        assert "updated_at" in patterns
        assert "pushed_at" in patterns

        # Verify types
        assert isinstance(patterns["days_since_creation"], int)
        assert isinstance(patterns["days_since_last_update"], int)
        assert isinstance(patterns["days_since_last_push"], int)
        assert isinstance(patterns["activity_ratio"], float)
        assert isinstance(patterns["created_at"], datetime)
        assert isinstance(patterns["updated_at"], datetime)
        assert isinstance(patterns["pushed_at"], datetime)

        # Verify activity ratio is between 0 and 1
        assert 0.0 <= patterns["activity_ratio"] <= 1.0

    def test_calculate_activity_patterns_invalid_timestamps(self, engine):
        """Test activity patterns calculation with invalid timestamps."""
        invalid_data = {
            "created_at": "invalid-timestamp",
            "updated_at": "2023-06-01T00:00:00Z",
            "pushed_at": "2023-06-15T00:00:00Z",
            "full_name": "test/repo",
        }

        with pytest.raises(ForkDataCollectionError):
            engine.calculate_activity_patterns(invalid_data)

    def test_determine_commits_ahead_status_no_commits(
        self, engine, sample_fork_data_no_commits
    ):
        """Test commits ahead status determination for fork with no commits."""
        status, can_skip = engine.determine_commits_ahead_status(
            sample_fork_data_no_commits
        )

        assert status == "No commits ahead"
        assert can_skip is True

    def test_determine_commits_ahead_status_has_commits(self, engine, sample_fork_data):
        """Test commits ahead status determination for fork with commits."""
        status, can_skip = engine.determine_commits_ahead_status(sample_fork_data)

        assert status == "Has commits"
        assert can_skip is False

    def test_determine_commits_ahead_status_edge_case_same_time(self, engine):
        """Test commits ahead status when created_at equals pushed_at."""
        fork_data = {
            "created_at": "2023-06-15T12:00:00Z",
            "pushed_at": "2023-06-15T12:00:00Z",
            "full_name": "test/repo",
        }

        status, can_skip = engine.determine_commits_ahead_status(fork_data)

        assert status == "No commits ahead"
        assert can_skip is True

    def test_determine_commits_ahead_status_created_after_push(self, engine):
        """Test commits ahead status when created_at is after pushed_at."""
        fork_data = {
            "created_at": "2023-06-15T12:00:00Z",
            "pushed_at": "2023-06-15T11:00:00Z",  # Earlier than created_at
            "full_name": "test/repo",
        }

        status, can_skip = engine.determine_commits_ahead_status(fork_data)

        assert status == "No commits ahead"
        assert can_skip is True

    def test_determine_commits_ahead_status_invalid_timestamps(self, engine):
        """Test commits ahead status determination with invalid timestamps."""
        invalid_data = {
            "created_at": "invalid-timestamp",
            "pushed_at": "2023-06-15T00:00:00Z",
            "full_name": "test/repo",
        }

        with pytest.raises(ForkDataCollectionError):
            engine.determine_commits_ahead_status(invalid_data)

    def test_generate_activity_summary_very_active(self, engine):
        """Test activity summary generation for very active fork."""
        # Mock metrics with recent push (3 days ago)
        metrics = Mock()
        metrics.days_since_last_push = 3

        summary = engine.generate_activity_summary(metrics)

        assert summary == "Very Active (< 1 week)"

    def test_generate_activity_summary_active(self, engine):
        """Test activity summary generation for active fork."""
        metrics = Mock()
        metrics.days_since_last_push = 15

        summary = engine.generate_activity_summary(metrics)

        assert summary == "Active (< 1 month)"

    def test_generate_activity_summary_moderately_active(self, engine):
        """Test activity summary generation for moderately active fork."""
        metrics = Mock()
        metrics.days_since_last_push = 60

        summary = engine.generate_activity_summary(metrics)

        assert summary == "Moderately Active (< 3 months)"

    def test_generate_activity_summary_low_activity(self, engine):
        """Test activity summary generation for low activity fork."""
        metrics = Mock()
        metrics.days_since_last_push = 200

        summary = engine.generate_activity_summary(metrics)

        assert summary == "Low Activity (< 1 year)"

    def test_generate_activity_summary_inactive(self, engine):
        """Test activity summary generation for inactive fork."""
        metrics = Mock()
        metrics.days_since_last_push = 400

        summary = engine.generate_activity_summary(metrics)

        assert summary == "Inactive (> 1 year)"

    def test_exclude_archived_and_disabled_success(self, engine):
        """Test excluding archived and disabled forks."""
        # Create mock collected fork data
        active_fork = Mock(spec=CollectedForkData)
        active_fork.metrics = Mock()
        active_fork.metrics.archived = False
        active_fork.metrics.disabled = False
        active_fork.metrics.full_name = "user/active-repo"

        archived_fork = Mock(spec=CollectedForkData)
        archived_fork.metrics = Mock()
        archived_fork.metrics.archived = True
        archived_fork.metrics.disabled = False
        archived_fork.metrics.full_name = "user/archived-repo"

        disabled_fork = Mock(spec=CollectedForkData)
        disabled_fork.metrics = Mock()
        disabled_fork.metrics.archived = False
        disabled_fork.metrics.disabled = True
        disabled_fork.metrics.full_name = "user/disabled-repo"

        collected_forks = [active_fork, archived_fork, disabled_fork]

        result = engine.exclude_archived_and_disabled(collected_forks)

        assert len(result) == 1
        assert result[0] == active_fork

    def test_exclude_archived_and_disabled_empty_list(self, engine):
        """Test excluding archived and disabled forks from empty list."""
        result = engine.exclude_archived_and_disabled([])

        assert result == []

    def test_exclude_no_commits_ahead_success(self, engine):
        """Test excluding forks with no commits ahead."""
        # Create mock collected fork data
        fork_with_commits = Mock(spec=CollectedForkData)
        fork_with_commits.metrics = Mock()
        fork_with_commits.metrics.can_skip_analysis = False
        fork_with_commits.metrics.full_name = "user/active-repo"

        fork_no_commits = Mock(spec=CollectedForkData)
        fork_no_commits.metrics = Mock()
        fork_no_commits.metrics.can_skip_analysis = True
        fork_no_commits.metrics.full_name = "user/no-commits-repo"

        collected_forks = [fork_with_commits, fork_no_commits]

        result = engine.exclude_no_commits_ahead(collected_forks)

        assert len(result) == 1
        assert result[0] == fork_with_commits

    def test_exclude_no_commits_ahead_empty_list(self, engine):
        """Test excluding forks with no commits ahead from empty list."""
        result = engine.exclude_no_commits_ahead([])

        assert result == []

    def test_organize_forks_by_status_success(self, engine):
        """Test organizing forks by status."""
        # Create mock collected fork data
        active_fork = Mock(spec=CollectedForkData)
        active_fork.metrics = Mock()
        active_fork.metrics.can_skip_analysis = False
        active_fork.metrics.archived = False
        active_fork.metrics.disabled = False

        archived_fork = Mock(spec=CollectedForkData)
        archived_fork.metrics = Mock()
        archived_fork.metrics.can_skip_analysis = False
        archived_fork.metrics.archived = True
        archived_fork.metrics.disabled = False

        disabled_fork = Mock(spec=CollectedForkData)
        disabled_fork.metrics = Mock()
        disabled_fork.metrics.can_skip_analysis = False
        disabled_fork.metrics.archived = False
        disabled_fork.metrics.disabled = True

        no_commits_fork = Mock(spec=CollectedForkData)
        no_commits_fork.metrics = Mock()
        no_commits_fork.metrics.can_skip_analysis = True
        no_commits_fork.metrics.archived = False
        no_commits_fork.metrics.disabled = False

        collected_forks = [active_fork, archived_fork, disabled_fork, no_commits_fork]

        active, archived_disabled, no_commits = engine.organize_forks_by_status(
            collected_forks
        )

        assert len(active) == 1
        assert active[0] == active_fork

        assert len(archived_disabled) == 2
        assert archived_fork in archived_disabled
        assert disabled_fork in archived_disabled

        assert len(no_commits) == 1
        assert no_commits[0] == no_commits_fork

    def test_organize_forks_by_status_empty_list(self, engine):
        """Test organizing forks by status with empty list."""
        active, archived_disabled, no_commits = engine.organize_forks_by_status([])

        assert active == []
        assert archived_disabled == []
        assert no_commits == []

    def test_create_qualification_result_success(self, engine):
        """Test creating qualification result."""
        # Create mock collected fork data
        fork_with_commits = Mock(spec=CollectedForkData)
        fork_with_commits.metrics = Mock()
        fork_with_commits.metrics.can_skip_analysis = False
        fork_with_commits.metrics.archived = False
        fork_with_commits.metrics.disabled = False

        fork_no_commits = Mock(spec=CollectedForkData)
        fork_no_commits.metrics = Mock()
        fork_no_commits.metrics.can_skip_analysis = True
        fork_no_commits.metrics.archived = False
        fork_no_commits.metrics.disabled = False

        archived_fork = Mock(spec=CollectedForkData)
        archived_fork.metrics = Mock()
        archived_fork.metrics.can_skip_analysis = False
        archived_fork.metrics.archived = True
        archived_fork.metrics.disabled = False

        collected_forks = [fork_with_commits, fork_no_commits, archived_fork]

        result = engine.create_qualification_result(
            repository_owner="testowner",
            repository_name="testrepo",
            collected_forks=collected_forks,
            processing_time_seconds=1.5,
            api_calls_made=5,
            api_calls_saved=10,
        )

        assert isinstance(result, QualifiedForksResult)
        assert result.repository_owner == "testowner"
        assert result.repository_name == "testrepo"
        assert result.repository_url == "https://github.com/testowner/testrepo"
        assert len(result.collected_forks) == 3
        assert result.stats.total_forks_discovered == 3
        assert result.stats.forks_with_commits == 2  # fork_with_commits + archived_fork
        assert result.stats.forks_with_no_commits == 1  # fork_no_commits
        assert result.stats.archived_forks == 1
        assert result.stats.disabled_forks == 0
        assert result.stats.api_calls_made == 5
        assert result.stats.api_calls_saved == 10
        assert result.stats.processing_time_seconds == 1.5

    def test_create_qualification_result_empty_forks(self, engine):
        """Test creating qualification result with empty forks list."""
        result = engine.create_qualification_result(
            repository_owner="testowner",
            repository_name="testrepo",
            collected_forks=[],
            processing_time_seconds=0.1,
        )

        assert isinstance(result, QualifiedForksResult)
        assert len(result.collected_forks) == 0
        assert result.stats.total_forks_discovered == 0
        assert result.stats.forks_with_commits == 0
        assert result.stats.forks_with_no_commits == 0

    @patch("forklift.analysis.fork_data_collection_engine.time.time")
    def test_collect_fork_data_from_list_timing(
        self, mock_time, engine, sample_fork_data
    ):
        """Test that timing is properly tracked during data collection."""
        # Mock time.time() to return predictable values
        mock_time.side_effect = [
            0.0,
            1.5,
            2.0,
        ]  # start_time, end_time, potential extra call

        forks_list_data = [sample_fork_data]

        result = engine.collect_fork_data_from_list(forks_list_data)

        assert len(result) == 1
        # Verify time.time() was called at least twice (start and end)
        assert mock_time.call_count >= 2

    def test_integration_full_workflow(
        self,
        engine,
        sample_fork_data,
        sample_fork_data_no_commits,
        sample_archived_fork_data,
    ):
        """Test integration of full workflow with real data."""
        forks_list_data = [
            sample_fork_data,
            sample_fork_data_no_commits,
            sample_archived_fork_data,
        ]

        # Step 1: Collect fork data
        collected_forks = engine.collect_fork_data_from_list(forks_list_data)
        assert len(collected_forks) == 3

        # Step 2: Organize by status
        active, archived_disabled, no_commits = engine.organize_forks_by_status(
            collected_forks
        )
        assert len(active) == 1  # sample_fork_data
        assert len(archived_disabled) == 1  # sample_archived_fork_data
        assert len(no_commits) == 1  # sample_fork_data_no_commits

        # Step 3: Apply filters
        filtered_active = engine.exclude_archived_and_disabled(collected_forks)
        assert len(filtered_active) == 2  # Excludes archived fork

        filtered_with_commits = engine.exclude_no_commits_ahead(filtered_active)
        assert len(filtered_with_commits) == 1  # Excludes no commits fork

        # Step 4: Create qualification result
        result = engine.create_qualification_result(
            repository_owner="testowner",
            repository_name="testrepo",
            collected_forks=collected_forks,
            processing_time_seconds=2.0,
            api_calls_made=3,
            api_calls_saved=6,
        )

        assert result.stats.total_forks_discovered == 3
        assert result.stats.forks_with_commits == 2
        assert result.stats.forks_with_no_commits == 1
        assert result.stats.archived_forks == 1
        assert result.stats.disabled_forks == 0

        # Verify computed properties work
        assert len(result.forks_needing_analysis) == 2
        assert len(result.forks_to_skip) == 1

    def test_error_handling_robustness(self, engine):
        """Test error handling with various edge cases."""
        # Test with None data - should skip gracefully
        result = engine.collect_fork_data_from_list([None])
        assert result == []

        # Test with mixed valid and invalid data
        valid_data = {
            "id": 123,
            "name": "test",
            "full_name": "user/test",
            "owner": {"login": "user"},
            "html_url": "https://github.com/user/test",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
            "pushed_at": "2023-01-01T00:00:00Z",
        }
        invalid_data = {"invalid": "data"}

        result = engine.collect_fork_data_from_list([valid_data, invalid_data])
        assert len(result) == 1  # Only valid data processed
