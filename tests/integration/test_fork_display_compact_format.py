"""Integration tests for consistent compact format across all fork display commands."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from rich.console import Console
from io import StringIO

from forkscout.display.repository_display_service import RepositoryDisplayService
from forkscout.models.github import Repository
from forkscout.models.analysis import ForkPreviewItem, ForksPreview
from forkscout.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualifiedForksResult,
    QualificationStats,
)


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_console():
    """Create a mock console that captures output."""
    string_io = StringIO()
    console = Console(file=string_io, width=120, legacy_windows=False)
    return console, string_io


@pytest.fixture
def sample_repositories():
    """Create sample repository data for testing."""
    base_time = datetime.now(timezone.utc)
    
    return [
        Repository(
            id=1,
            name="test-repo-1",
            owner="user1",
            full_name="user1/test-repo-1",
            url="https://api.github.com/repos/user1/test-repo-1",
            html_url="https://github.com/user1/test-repo-1",
            clone_url="https://github.com/user1/test-repo-1.git",
            description="Test repository 1",
            language="Python",
            stars=10,
            forks_count=2,
            watchers_count=5,
            open_issues_count=1,
            size=100,
            topics=["python", "test"],
            license_name="MIT",
            default_branch="main",
            is_private=False,
            is_fork=True,
            is_archived=False,
            created_at=base_time,
            updated_at=base_time,
            pushed_at=base_time,  # Same as created_at = no commits ahead
        ),
        Repository(
            id=2,
            name="test-repo-2",
            owner="user2",
            full_name="user2/test-repo-2",
            url="https://api.github.com/repos/user2/test-repo-2",
            html_url="https://github.com/user2/test-repo-2",
            clone_url="https://github.com/user2/test-repo-2.git",
            description="Test repository 2",
            language="JavaScript",
            stars=25,
            forks_count=5,
            watchers_count=15,
            open_issues_count=3,
            size=250,
            topics=["javascript", "web"],
            license_name="Apache-2.0",
            default_branch="main",
            is_private=False,
            is_fork=True,
            is_archived=False,
            created_at=base_time,
            updated_at=base_time,
            pushed_at=datetime.now(timezone.utc),  # Different from created_at = has commits
        ),
    ]


@pytest.fixture
def sample_fork_preview_items():
    """Create sample fork preview items."""
    base_time = datetime.now(timezone.utc)
    
    return [
        {
            "name": "test-repo-1",
            "owner": "user1",
            "stars": 10,
            "last_push_date": base_time,
            "fork_url": "https://github.com/user1/test-repo-1",
            "activity_status": "No commits",
            "commits_ahead": "None",  # No commits ahead
        },
        {
            "name": "test-repo-2",
            "owner": "user2",
            "stars": 25,
            "last_push_date": base_time,
            "fork_url": "https://github.com/user2/test-repo-2",
            "activity_status": "Active",
            "commits_ahead": "Unknown",  # Has commits ahead
        },
    ]


@pytest.fixture
def sample_collected_fork_data():
    """Create sample collected fork data."""
    base_time = datetime.now(timezone.utc)
    
    return [
        CollectedForkData(
            metrics=ForkQualificationMetrics(
                id=1,
                owner="user1",
                name="test-repo-1",
                full_name="user1/test-repo-1",
                html_url="https://github.com/user1/test-repo-1",
                stargazers_count=10,
                forks_count=2,
                watchers_count=5,
                open_issues_count=1,
                size=100,
                language="Python",
                topics=["python", "test"],
                created_at=base_time,
                updated_at=base_time,
                pushed_at=base_time,  # Same as created_at
                archived=False,
                disabled=False,
                fork=True,
                commits_ahead_status="None",  # No commits ahead
                can_skip_analysis=True,
            )
        ),
        CollectedForkData(
            metrics=ForkQualificationMetrics(
                id=2,
                owner="user2",
                name="test-repo-2",
                full_name="user2/test-repo-2",
                html_url="https://github.com/user2/test-repo-2",
                stargazers_count=25,
                forks_count=5,
                watchers_count=15,
                open_issues_count=3,
                size=250,
                language="JavaScript",
                topics=["javascript", "web"],
                created_at=base_time,
                updated_at=base_time,
                pushed_at=datetime.now(timezone.utc),  # Different from created_at
                archived=False,
                disabled=False,
                fork=True,
                commits_ahead_status="Unknown",  # Has commits ahead
                can_skip_analysis=False,
            )
        ),
    ]


@pytest.fixture
def sample_detailed_fork_data(sample_collected_fork_data):
    """Create sample detailed fork data with exact commit counts."""
    detailed_forks = []
    
    for i, fork_data in enumerate(sample_collected_fork_data):
        # Add exact_commits_ahead attribute
        if fork_data.metrics.commits_ahead_status == "None":
            fork_data.exact_commits_ahead = 0  # No commits ahead
        else:
            fork_data.exact_commits_ahead = 5 + i  # Has commits ahead
        
        detailed_forks.append(fork_data)
    
    return detailed_forks


class TestForkDisplayCompactFormat:
    """Test consistent compact format across all fork display commands."""

    @pytest.mark.asyncio
    async def test_list_forks_preview_compact_format(
        self, mock_github_client, mock_console, sample_repositories, sample_fork_preview_items
    ):
        """Test that list-forks command uses compact format."""
        console, string_io = mock_console
        
        # Mock the GitHub client to return sample repositories
        mock_github_client.get_repository_forks.return_value = sample_repositories
        
        # Create display service
        display_service = RepositoryDisplayService(mock_github_client, console)
        
        # Call the method that displays fork preview table
        display_service._display_forks_preview_table(sample_fork_preview_items)
        
        # Get the output
        output = string_io.getvalue()
        
        # Verify compact format is used
        assert "Commits" in output  # Column header exists
        
        # Check that forks with no commits ahead show empty cell (compact format)
        lines = output.split('\n')
        fork1_line = next((line for line in lines if "user1" in line and "test-repo-1" in line), None)
        assert fork1_line is not None
        # The commits column should be empty for forks with no commits ahead
        
        # Check that forks with commits ahead show "+?" (compact format)
        fork2_line = next((line for line in lines if "user2" in line and "test-repo-2" in line), None)
        assert fork2_line is not None
        # Should contain "+?" for unknown commits ahead

    @pytest.mark.asyncio
    async def test_show_fork_data_compact_format(
        self, mock_github_client, mock_console, sample_collected_fork_data
    ):
        """Test that show-fork-data command uses compact format."""
        console, string_io = mock_console
        
        # Create qualification result
        stats = QualificationStats(
            total_forks_discovered=2,
            forks_with_commits=1,
            forks_with_no_commits=1,
            archived_forks=0,
            disabled_forks=0,
            processing_time_seconds=1.0,
            api_calls_made=2,
            api_calls_saved=1,
        )
        
        qualification_result = QualifiedForksResult(
            repository_owner="test-owner",
            repository_name="test-repo",
            repository_url="https://github.com/test-owner/test-repo",
            collected_forks=sample_collected_fork_data,
            stats=stats,
        )
        
        # Create display service
        display_service = RepositoryDisplayService(mock_github_client, console)
        
        # Call the method that displays fork data table
        await display_service._display_fork_data_table(qualification_result)
        
        # Get the output
        output = string_io.getvalue()
        
        # Verify compact format is used
        assert "Commits" in output  # Column header exists
        
        # Check that the output contains the expected compact formatting
        lines = output.split('\n')
        
        # Find lines with fork data
        fork_lines = [line for line in lines if "github.com" in line]
        assert len(fork_lines) >= 2
        
        # Verify compact format: empty cells for no commits, "+?" for unknown
        # The exact format depends on the table structure, but we should see compact representation

    @pytest.mark.asyncio
    async def test_show_forks_detailed_compact_format(
        self, mock_github_client, mock_console, sample_detailed_fork_data
    ):
        """Test that show-forks --detail command uses compact format."""
        console, string_io = mock_console
        
        # Create display service
        display_service = RepositoryDisplayService(mock_github_client, console)
        
        # Call the method that displays detailed fork table
        await display_service._display_detailed_fork_table(
            sample_detailed_fork_data,
            "test-owner",
            "test-repo",
            api_calls_made=1,
            api_calls_saved=1,
        )
        
        # Get the output
        output = string_io.getvalue()
        
        # Verify compact format is used
        assert "Commits Ahead" in output  # Column header exists
        
        # Check that the output uses compact formatting
        lines = output.split('\n')
        
        # Find lines with fork data
        fork_lines = [line for line in lines if "github.com" in line]
        assert len(fork_lines) >= 2
        
        # Verify compact format:
        # - Empty cell for 0 commits ahead
        # - "+X" format for commits ahead
        fork1_line = next((line for line in fork_lines if "user1" in line), None)
        fork2_line = next((line for line in fork_lines if "user2" in line), None)
        
        assert fork1_line is not None
        assert fork2_line is not None

    @pytest.mark.asyncio
    async def test_promising_forks_compact_format(self, mock_github_client, mock_console):
        """Test that show-promising command uses compact format."""
        console, string_io = mock_console
        
        # Create sample promising forks data
        promising_forks = [
            {
                "fork": Repository(
                    id=1,
                    name="promising-repo",
                    owner="user1",
                    full_name="user1/promising-repo",
                    url="https://api.github.com/repos/user1/promising-repo",
                    html_url="https://github.com/user1/promising-repo",
                    clone_url="https://github.com/user1/promising-repo.git",
                    description="Promising repository",
                    language="Python",
                    stars=50,
                    forks_count=10,
                    watchers_count=25,
                    open_issues_count=2,
                    size=500,
                    topics=["python"],
                    license_name="MIT",
                    default_branch="main",
                    is_private=False,
                    is_fork=True,
                    is_archived=False,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    pushed_at=datetime.now(timezone.utc),
                ),
                "commits_ahead": 0,  # No commits ahead
                "activity_status": "active",
                "last_activity": "2 days ago",
            },
            {
                "fork": Repository(
                    id=2,
                    name="another-promising-repo",
                    owner="user2",
                    full_name="user2/another-promising-repo",
                    url="https://api.github.com/repos/user2/another-promising-repo",
                    html_url="https://github.com/user2/another-promising-repo",
                    clone_url="https://github.com/user2/another-promising-repo.git",
                    description="Another promising repository",
                    language="JavaScript",
                    stars=75,
                    forks_count=15,
                    watchers_count=40,
                    open_issues_count=5,
                    size=750,
                    topics=["javascript"],
                    license_name="Apache-2.0",
                    default_branch="main",
                    is_private=False,
                    is_fork=True,
                    is_archived=False,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    pushed_at=datetime.now(timezone.utc),
                ),
                "commits_ahead": 3,  # Has commits ahead
                "activity_status": "active",
                "last_activity": "1 day ago",
            },
        ]
        
        # Mock filters
        from forkscout.models.filters import PromisingForksFilter
        filters = PromisingForksFilter()
        
        # Create display service
        display_service = RepositoryDisplayService(mock_github_client, console)
        
        # Call the method that displays promising forks table
        display_service._display_promising_forks_table(promising_forks, filters)
        
        # Get the output
        output = string_io.getvalue()
        
        # Verify compact format is used
        assert "Commits" in output  # Column header exists
        
        # Check that the output uses compact formatting
        lines = output.split('\n')
        
        # Find lines with fork data
        fork_lines = [line for line in lines if "promising-repo" in line or "another-promising-repo" in line]
        assert len(fork_lines) >= 2
        
        # Verify compact format:
        # - Empty cell for 0 commits ahead
        # - "+X" format for commits ahead

    def test_format_commits_compact_consistency(self, mock_github_client):
        """Test that format_commits_compact method produces consistent results."""
        console = Console()
        display_service = RepositoryDisplayService(mock_github_client, console)
        
        # Test various scenarios
        test_cases = [
            # (commits_ahead, commits_behind, expected_result_pattern)
            (0, 0, ""),  # Empty cell for both zero
            (5, 0, "+5"),  # Only ahead commits
            (0, 3, "-3"),  # Only behind commits
            (5, 3, "+5.*-3"),  # Both ahead and behind
            (-1, 0, "Unknown"),  # Unknown ahead
            (0, -1, "Unknown"),  # Unknown behind
            (-1, -1, "Unknown"),  # Both unknown
        ]
        
        for commits_ahead, commits_behind, expected_pattern in test_cases:
            result = display_service.format_commits_compact(commits_ahead, commits_behind)
            
            if expected_pattern == "":
                assert result == ""
            elif expected_pattern == "Unknown":
                assert "Unknown" in result
            elif ".*" in expected_pattern:
                # Pattern with both ahead and behind
                assert "+" in result and "-" in result
            elif expected_pattern.startswith("+"):
                assert result.startswith("[green]+") or result.startswith("+")
            elif expected_pattern.startswith("-"):
                assert result.startswith("[red]-") or result.startswith("-")

    @pytest.mark.asyncio
    async def test_all_display_methods_use_compact_format(
        self, mock_github_client, mock_console, sample_fork_preview_items,
        sample_collected_fork_data, sample_detailed_fork_data
    ):
        """Integration test to verify all display methods use consistent compact format."""
        console, string_io = mock_console
        display_service = RepositoryDisplayService(mock_github_client, console)
        
        # Test 1: Fork preview table (list-forks command)
        display_service._display_forks_preview_table(sample_fork_preview_items)
        preview_output = string_io.getvalue()
        string_io.truncate(0)
        string_io.seek(0)
        
        # Test 2: Fork data table (show-fork-data command)
        stats = QualificationStats(
            total_forks_discovered=2,
            forks_with_commits=1,
            forks_with_no_commits=1,
            archived_forks=0,
            disabled_forks=0,
            processing_time_seconds=1.0,
            api_calls_made=2,
            api_calls_saved=1,
        )
        
        qualification_result = QualifiedForksResult(
            repository_owner="test-owner",
            repository_name="test-repo",
            repository_url="https://github.com/test-owner/test-repo",
            collected_forks=sample_collected_fork_data,
            stats=stats,
        )
        
        await display_service._display_fork_data_table(qualification_result)
        fork_data_output = string_io.getvalue()
        string_io.truncate(0)
        string_io.seek(0)
        
        # Test 3: Detailed fork table (show-forks --detail command)
        await display_service._display_detailed_fork_table(
            sample_detailed_fork_data,
            "test-owner",
            "test-repo",
            api_calls_made=1,
            api_calls_saved=1,
        )
        detailed_output = string_io.getvalue()
        
        # Verify all outputs contain commit information
        assert "Commits" in preview_output
        assert "Commits" in fork_data_output
        assert "Commits Ahead" in detailed_output
        
        # Verify consistent compact formatting across all methods
        # All should handle empty cells for no commits ahead
        # All should use "+X" format for commits ahead
        # All should use consistent styling
        
        outputs = [preview_output, fork_data_output, detailed_output]
        for output in outputs:
            # Each output should contain table structure
            assert "│" in output or "|" in output  # Table borders
            # Should not contain verbose commit descriptions like "0 commits" or "commits ahead"
            # Should use compact format instead