"""Unit tests for ForkListProcessor."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from forkscout.github.client import GitHubAPIError, GitHubClient
from forkscout.github.fork_list_processor import (
    ForkListProcessingError,
    ForkListProcessor,
)
from forkscout.models.fork_qualification import (
    CollectedForkData,
    QualifiedForksResult,
)


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    client = AsyncMock(spec=GitHubClient)
    return client


@pytest.fixture
def fork_list_processor(mock_github_client):
    """Create a ForkListProcessor with mock client."""
    return ForkListProcessor(mock_github_client)


@pytest.fixture
def sample_fork_data():
    """Create sample fork data from GitHub API."""
    return {
        "id": 123456,
        "name": "test-repo",
        "full_name": "testuser/test-repo",
        "owner": {"login": "testuser"},
        "html_url": "https://github.com/testuser/test-repo",
        "stargazers_count": 5,
        "forks_count": 2,
        "watchers_count": 3,
        "size": 1024,
        "language": "Python",
        "topics": ["python", "testing"],
        "open_issues_count": 1,
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-06-01T00:00:00Z",
        "pushed_at": "2023-06-15T00:00:00Z",
        "archived": False,
        "disabled": False,
        "fork": True,
        "license": {"key": "mit", "name": "MIT License"},
        "description": "A test repository",
        "homepage": "https://example.com",
        "default_branch": "main",
    }


@pytest.fixture
def sample_fork_data_no_commits():
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
        "size": 0,
        "language": None,
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


class TestForkListProcessor:
    """Test cases for ForkListProcessor."""

    def test_init(self, mock_github_client):
        """Test ForkListProcessor initialization."""
        processor = ForkListProcessor(mock_github_client)
        assert processor.github_client is mock_github_client

    @pytest.mark.asyncio
    async def test_get_all_forks_list_data_single_page(
        self, fork_list_processor, mock_github_client, sample_fork_data
    ):
        """Test getting all forks data with single page."""
        # Mock the GitHub client responses
        mock_github_client.get_repository_forks.return_value = []  # Not used directly
        mock_github_client.get.return_value = [sample_fork_data]

        # Test the method
        result = await fork_list_processor.get_all_forks_list_data("owner", "repo")

        # Verify results
        assert len(result) == 1
        assert result[0] == sample_fork_data

        # Verify API calls
        mock_github_client.get.assert_called_once_with(
            "repos/owner/repo/forks", params={"sort": "newest", "per_page": 100, "page": 1}
        )

    @pytest.mark.asyncio
    async def test_get_all_forks_list_data_multiple_pages(
        self, fork_list_processor, mock_github_client, sample_fork_data
    ):
        """Test getting all forks data with multiple pages."""
        # Create data for multiple pages
        page1_data = [sample_fork_data] * 100  # Full page
        page2_data = [sample_fork_data] * 50   # Partial page

        # Mock the GitHub client responses
        mock_github_client.get.side_effect = [page1_data, page2_data]

        # Test the method
        result = await fork_list_processor.get_all_forks_list_data("owner", "repo")

        # Verify results
        assert len(result) == 150
        assert all(fork == sample_fork_data for fork in result)

        # Verify API calls
        assert mock_github_client.get.call_count == 2
        mock_github_client.get.assert_any_call(
            "repos/owner/repo/forks", params={"sort": "newest", "per_page": 100, "page": 1}
        )
        mock_github_client.get.assert_any_call(
            "repos/owner/repo/forks", params={"sort": "newest", "per_page": 100, "page": 2}
        )

    @pytest.mark.asyncio
    async def test_get_all_forks_list_data_empty_result(
        self, fork_list_processor, mock_github_client
    ):
        """Test getting all forks data with empty result."""
        # Mock empty response
        mock_github_client.get.return_value = []

        # Test the method
        result = await fork_list_processor.get_all_forks_list_data("owner", "repo")

        # Verify results
        assert len(result) == 0

        # Verify API calls
        mock_github_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_forks_list_data_with_progress_callback(
        self, fork_list_processor, mock_github_client, sample_fork_data
    ):
        """Test getting all forks data with progress callback."""
        # Mock response
        mock_github_client.get.return_value = [sample_fork_data]

        # Create progress callback mock
        progress_callback = Mock()

        # Test the method
        result = await fork_list_processor.get_all_forks_list_data(
            "owner", "repo", progress_callback=progress_callback
        )

        # Verify results
        assert len(result) == 1

        # Verify progress callback was called
        progress_callback.assert_called_once_with(1, 1)

    @pytest.mark.asyncio
    async def test_get_all_forks_list_data_api_error(
        self, fork_list_processor, mock_github_client
    ):
        """Test handling API errors during fork list retrieval."""
        # Mock API error
        mock_github_client.get.side_effect = GitHubAPIError("API Error")

        # Test the method and expect exception
        with pytest.raises(ForkListProcessingError) as exc_info:
            await fork_list_processor.get_all_forks_list_data("owner", "repo")

        assert "Failed to process fork list" in str(exc_info.value)
        assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_forks_pages(
        self, fork_list_processor, mock_github_client, sample_fork_data
    ):
        """Test process_forks_pages method (alias for get_all_forks_list_data)."""
        # Mock response
        mock_github_client.get.return_value = [sample_fork_data]

        # Test the method
        result = await fork_list_processor.process_forks_pages("owner", "repo")

        # Verify results
        assert len(result) == 1
        assert result[0] == sample_fork_data

    def test_extract_qualification_fields_complete_data(
        self, fork_list_processor, sample_fork_data
    ):
        """Test extracting qualification fields from complete fork data."""
        result = fork_list_processor.extract_qualification_fields(sample_fork_data)

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
            assert field in result

        # Verify specific values
        assert result["id"] == 123456
        assert result["name"] == "test-repo"
        assert result["full_name"] == "testuser/test-repo"
        assert result["owner"] == "testuser"
        assert result["stargazers_count"] == 5
        assert result["language"] == "Python"
        assert result["topics"] == ["python", "testing"]
        assert result["license_key"] == "mit"
        assert result["license_name"] == "MIT License"

    def test_extract_qualification_fields_minimal_data(
        self, fork_list_processor, sample_fork_data_no_commits
    ):
        """Test extracting qualification fields from minimal fork data."""
        result = fork_list_processor.extract_qualification_fields(sample_fork_data_no_commits)

        # Verify required fields are present
        assert result["id"] == 789012
        assert result["name"] == "no-commits-repo"
        assert result["owner"] == "testuser"
        assert result["stargazers_count"] == 0
        assert result["language"] is None
        assert result["topics"] == []
        assert result["license_key"] is None
        assert result["license_name"] is None
        assert result["description"] is None

    def test_extract_qualification_fields_missing_owner(
        self, fork_list_processor, sample_fork_data
    ):
        """Test extracting qualification fields with missing owner data."""
        # Remove owner data
        fork_data = sample_fork_data.copy()
        del fork_data["owner"]

        # Test and expect exception
        with pytest.raises(ForkListProcessingError) as exc_info:
            fork_list_processor.extract_qualification_fields(fork_data)

        assert "missing owner information" in str(exc_info.value)

    def test_extract_qualification_fields_missing_required_field(
        self, fork_list_processor, sample_fork_data
    ):
        """Test extracting qualification fields with missing required field."""
        # Remove required field
        fork_data = sample_fork_data.copy()
        del fork_data["id"]

        # Test and expect exception
        with pytest.raises(ForkListProcessingError) as exc_info:
            fork_list_processor.extract_qualification_fields(fork_data)

        assert "Missing required field" in str(exc_info.value)

    def test_validate_fork_data_completeness_valid_data(
        self, fork_list_processor, sample_fork_data
    ):
        """Test validating complete and valid fork data."""
        result = fork_list_processor.validate_fork_data_completeness(sample_fork_data)
        assert result is True

    def test_validate_fork_data_completeness_minimal_valid_data(
        self, fork_list_processor, sample_fork_data_no_commits
    ):
        """Test validating minimal but valid fork data."""
        result = fork_list_processor.validate_fork_data_completeness(sample_fork_data_no_commits)
        assert result is True

    def test_validate_fork_data_completeness_missing_required_field(
        self, fork_list_processor, sample_fork_data
    ):
        """Test validating fork data with missing required field."""
        # Remove required field
        fork_data = sample_fork_data.copy()
        del fork_data["id"]

        result = fork_list_processor.validate_fork_data_completeness(fork_data)
        assert result is False

    def test_validate_fork_data_completeness_missing_owner(
        self, fork_list_processor, sample_fork_data
    ):
        """Test validating fork data with missing owner."""
        # Remove owner data
        fork_data = sample_fork_data.copy()
        del fork_data["owner"]

        result = fork_list_processor.validate_fork_data_completeness(fork_data)
        assert result is False

    def test_validate_fork_data_completeness_missing_owner_login(
        self, fork_list_processor, sample_fork_data
    ):
        """Test validating fork data with missing owner login."""
        # Remove owner login
        fork_data = sample_fork_data.copy()
        fork_data["owner"] = {}

        result = fork_list_processor.validate_fork_data_completeness(fork_data)
        assert result is False

    def test_validate_fork_data_completeness_invalid_timestamp(
        self, fork_list_processor, sample_fork_data
    ):
        """Test validating fork data with invalid timestamp."""
        # Set invalid timestamp
        fork_data = sample_fork_data.copy()
        fork_data["created_at"] = 123456  # Should be string

        result = fork_list_processor.validate_fork_data_completeness(fork_data)
        assert result is False

    def test_validate_fork_data_completeness_invalid_numeric_field(
        self, fork_list_processor, sample_fork_data
    ):
        """Test validating fork data with invalid numeric field."""
        # Set invalid numeric value
        fork_data = sample_fork_data.copy()
        fork_data["stargazers_count"] = "not_a_number"

        result = fork_list_processor.validate_fork_data_completeness(fork_data)
        assert result is False

    def test_validate_fork_data_completeness_exception_handling(
        self, fork_list_processor
    ):
        """Test validating fork data with exception during validation."""
        # Pass invalid data that will cause exception
        result = fork_list_processor.validate_fork_data_completeness(None)
        assert result is False

    @pytest.mark.asyncio
    async def test_collect_and_process_forks_success(
        self, fork_list_processor, mock_github_client, sample_fork_data, sample_fork_data_no_commits
    ):
        """Test successful fork collection and processing."""
        # Mock response with mixed fork data
        fork_data_list = [sample_fork_data, sample_fork_data_no_commits]
        mock_github_client.get.return_value = fork_data_list

        # Test the method
        result = await fork_list_processor.collect_and_process_forks("owner", "repo")

        # Verify result type and structure
        assert isinstance(result, QualifiedForksResult)
        assert result.repository_owner == "owner"
        assert result.repository_name == "repo"
        assert result.repository_url == "https://github.com/owner/repo"

        # Verify collected forks
        assert len(result.collected_forks) == 2
        assert all(isinstance(fork, CollectedForkData) for fork in result.collected_forks)

        # Verify statistics
        assert result.stats.total_forks_discovered == 2
        assert result.stats.forks_with_commits == 1  # sample_fork_data has commits
        assert result.stats.forks_with_no_commits == 1  # sample_fork_data_no_commits has no commits
        assert result.stats.api_calls_made == 1  # Single page
        assert result.stats.api_calls_saved == 2  # Two forks would need individual calls
        assert result.stats.processing_time_seconds > 0

        # Verify computed properties
        assert len(result.forks_needing_analysis) == 1
        assert len(result.forks_to_skip) == 1

    @pytest.mark.asyncio
    async def test_collect_and_process_forks_with_invalid_data(
        self, fork_list_processor, mock_github_client, sample_fork_data
    ):
        """Test fork collection with some invalid data."""
        # Create invalid fork data (missing required field)
        invalid_fork_data = sample_fork_data.copy()
        del invalid_fork_data["id"]

        # Mock response with valid and invalid data
        fork_data_list = [sample_fork_data, invalid_fork_data]
        mock_github_client.get.return_value = fork_data_list

        # Test the method
        result = await fork_list_processor.collect_and_process_forks("owner", "repo")

        # Verify only valid fork was processed
        assert result.stats.total_forks_discovered == 2
        assert len(result.collected_forks) == 1  # Only valid fork processed

    @pytest.mark.asyncio
    async def test_collect_and_process_forks_with_progress_callback(
        self, fork_list_processor, mock_github_client, sample_fork_data
    ):
        """Test fork collection with progress callback."""
        # Mock response
        mock_github_client.get.return_value = [sample_fork_data]

        # Create progress callback mock
        progress_callback = Mock()

        # Test the method
        result = await fork_list_processor.collect_and_process_forks(
            "owner", "repo", progress_callback=progress_callback
        )

        # Verify progress callback was called
        progress_callback.assert_called_once_with(1, 1)

        # Verify result
        assert len(result.collected_forks) == 1

    @pytest.mark.asyncio
    async def test_collect_and_process_forks_api_error(
        self, fork_list_processor, mock_github_client
    ):
        """Test fork collection with API error."""
        # Mock API error
        mock_github_client.get.side_effect = GitHubAPIError("API Error")

        # Test the method and expect exception
        with pytest.raises(ForkListProcessingError) as exc_info:
            await fork_list_processor.collect_and_process_forks("owner", "repo")

        assert "Failed to collect and process forks" in str(exc_info.value)
        assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_collect_and_process_forks_empty_result(
        self, fork_list_processor, mock_github_client
    ):
        """Test fork collection with empty result."""
        # Mock empty response
        mock_github_client.get.return_value = []

        # Test the method
        result = await fork_list_processor.collect_and_process_forks("owner", "repo")

        # Verify empty result
        assert result.stats.total_forks_discovered == 0
        assert len(result.collected_forks) == 0
        assert result.stats.forks_with_commits == 0
        assert result.stats.forks_with_no_commits == 0

    @pytest.mark.asyncio
    async def test_collect_and_process_forks_archived_and_disabled(
        self, fork_list_processor, mock_github_client, sample_fork_data
    ):
        """Test fork collection with archived and disabled forks."""
        # Create archived and disabled fork data
        archived_fork = sample_fork_data.copy()
        archived_fork["id"] = 999001
        archived_fork["archived"] = True

        disabled_fork = sample_fork_data.copy()
        disabled_fork["id"] = 999002
        disabled_fork["disabled"] = True

        # Mock response
        fork_data_list = [sample_fork_data, archived_fork, disabled_fork]
        mock_github_client.get.return_value = fork_data_list

        # Test the method
        result = await fork_list_processor.collect_and_process_forks("owner", "repo")

        # Verify statistics include archived and disabled counts
        assert result.stats.total_forks_discovered == 3
        assert result.stats.archived_forks == 1
        assert result.stats.disabled_forks == 1
        assert len(result.collected_forks) == 3


class TestForkListProcessorIntegration:
    """Integration-style tests for ForkListProcessor."""

    @pytest.mark.asyncio
    async def test_full_workflow_with_realistic_data(
        self, fork_list_processor, mock_github_client
    ):
        """Test complete workflow with realistic fork data."""
        from datetime import timedelta

        # Use recent dates to ensure active fork detection works
        recent_date = datetime.utcnow() - timedelta(days=30)  # 30 days ago
        very_recent_date = datetime.utcnow() - timedelta(days=10)  # 10 days ago

        # Create realistic fork data representing different scenarios
        active_fork = {
            "id": 1001,
            "name": "active-fork",
            "full_name": "activeuser/active-fork",
            "owner": {"login": "activeuser"},
            "html_url": "https://github.com/activeuser/active-fork",
            "stargazers_count": 15,
            "forks_count": 3,
            "watchers_count": 12,
            "size": 2048,
            "language": "Python",
            "topics": ["python", "web", "api"],
            "open_issues_count": 2,
            "created_at": recent_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updated_at": very_recent_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pushed_at": very_recent_date.strftime("%Y-%m-%dT%H:%M:%SZ"),  # Recent activity
            "archived": False,
            "disabled": False,
            "fork": True,
            "license": {"key": "apache-2.0", "name": "Apache License 2.0"},
            "description": "An active fork with improvements",
            "homepage": "https://activeuser.github.io/active-fork",
            "default_branch": "main",
        }

        stale_fork = {
            "id": 1002,
            "name": "stale-fork",
            "full_name": "staleuser/stale-fork",
            "owner": {"login": "staleuser"},
            "html_url": "https://github.com/staleuser/stale-fork",
            "stargazers_count": 1,
            "forks_count": 0,
            "watchers_count": 1,
            "size": 1024,
            "language": "Python",
            "topics": [],
            "open_issues_count": 0,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
            "pushed_at": "2023-01-01T00:00:00Z",  # Same as created - no commits
            "archived": False,
            "disabled": False,
            "fork": True,
            "license": None,
            "description": None,
            "homepage": None,
            "default_branch": "master",
        }

        archived_fork = {
            "id": 1003,
            "name": "archived-fork",
            "full_name": "archiveduser/archived-fork",
            "owner": {"login": "archiveduser"},
            "html_url": "https://github.com/archiveduser/archived-fork",
            "stargazers_count": 5,
            "forks_count": 1,
            "watchers_count": 3,
            "size": 512,
            "language": "JavaScript",
            "topics": ["javascript", "archived"],
            "open_issues_count": 0,
            "created_at": "2022-01-01T00:00:00Z",
            "updated_at": "2022-06-01T00:00:00Z",
            "pushed_at": "2022-06-15T00:00:00Z",
            "archived": True,  # Archived
            "disabled": False,
            "fork": True,
            "license": {"key": "mit", "name": "MIT License"},
            "description": "An archived fork",
            "homepage": None,
            "default_branch": "main",
        }

        # Mock paginated response (simulate 2 pages)
        page1_data = [active_fork] * 100  # Full page
        page2_data = [stale_fork, archived_fork]  # Partial page

        mock_github_client.get.side_effect = [page1_data, page2_data]

        # Test the complete workflow
        result = await fork_list_processor.collect_and_process_forks("owner", "repo")

        # Verify comprehensive results
        assert result.stats.total_forks_discovered == 102
        assert len(result.collected_forks) == 102

        # Verify statistics
        # active_fork (100 instances) and archived_fork have commits (pushed_at > created_at)
        # Only stale_fork has no commits (pushed_at == created_at)
        assert result.stats.forks_with_commits == 101  # 100 active_fork + 1 archived_fork
        assert result.stats.forks_with_no_commits == 1  # Only stale_fork
        assert result.stats.archived_forks == 1  # Only archived_fork
        assert result.stats.disabled_forks == 0

        # Verify API efficiency
        assert result.stats.api_calls_made == 2  # Two pages
        assert result.stats.api_calls_saved == 102  # Each fork would need individual call
        assert result.stats.efficiency_percentage > 95  # Very efficient

        # Verify computed properties work correctly
        active_forks = result.active_forks  # Recent activity
        popular_forks = result.popular_forks  # 5+ stars
        forks_needing_analysis = result.forks_needing_analysis
        forks_to_skip = result.forks_to_skip

        assert len(active_forks) > 0
        assert len(popular_forks) > 0
        assert len(forks_needing_analysis) == 101  # 100 active_fork + 1 archived_fork
        assert len(forks_to_skip) == 1  # Only stale_fork

        # Verify summary report generation
        summary = result.get_summary_report()
        assert "Total Forks: 102" in summary
        assert "Need Analysis: 101" in summary
        assert "Can Skip: 1" in summary
        assert "API Efficiency:" in summary
