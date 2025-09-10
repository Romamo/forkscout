"""End-to-end tests covering all fork display commands with compact format."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from io import StringIO

from rich.console import Console

from forkscout.display.repository_display_service import RepositoryDisplayService
from forkscout.github.client import GitHubClient
from forkscout.models.github import Repository
from forkscout.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualificationStats,
    QualifiedForksResult,
)


class TestCompactCommitDisplayEndToEnd:
    """End-to-end tests covering all fork display commands with compact format."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return AsyncMock(spec=GitHubClient)

    @pytest.fixture
    def console_with_capture(self):
        """Create a console that captures output for testing."""
        string_io = StringIO()
        console = Console(file=string_io, width=120, legacy_windows=False)
        return console, string_io

    @pytest.fixture
    def display_service(self, mock_github_client, console_with_capture):
        """Create a repository display service with output capture."""
        console, _ = console_with_capture
        return RepositoryDisplayService(mock_github_client, console)

    @pytest.fixture
    def comprehensive_test_data(self):
        """Create comprehensive test data for end-to-end testing."""
        base_time = datetime.now(timezone.utc)
        
        # Main repository
        main_repo = Repository(
            id=100,
            name="test-repo",
            owner="owner",
            full_name="owner/test-repo",
            url="https://api.github.com/repos/owner/test-repo",
            html_url="https://github.com/owner/test-repo",
            clone_url="https://github.com/owner/test-repo.git",
            description="Main test repository",
            language="Python",
            stars=1000,
            forks_count=50,
            watchers_count=500,
            open_issues_count=10,
            size=5000,
            topics=["python", "test", "main"],
            license_name="MIT",
            default_branch="main",
            is_private=False,
            is_fork=False,
            is_archived=False,
            created_at=base_time - timedelta(days=365),
            updated_at=base_time - timedelta(days=1),
            pushed_at=base_time - timedelta(days=1),
        )
        
        # Fork repositories
        forks = [
            Repository(
                id=1,
                name="test-repo",
                owner="contributor1",
                full_name="contributor1/test-repo",
                url="https://api.github.com/repos/contributor1/test-repo",
                html_url="https://github.com/contributor1/test-repo",
                clone_url="https://github.com/contributor1/test-repo.git",
                description="Active contributor fork",
                language="Python",
                stars=15,
                forks_count=3,
                watchers_count=8,
                open_issues_count=2,
                size=5200,
                topics=["python", "fork", "active"],
                license_name="MIT",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time - timedelta(days=60),
                updated_at=base_time - timedelta(days=2),
                pushed_at=base_time - timedelta(days=2),  # Has commits ahead
            ),
            Repository(
                id=2,
                name="test-repo",
                owner="contributor2",
                full_name="contributor2/test-repo",
                url="https://api.github.com/repos/contributor2/test-repo",
                html_url="https://github.com/contributor2/test-repo",
                clone_url="https://github.com/contributor2/test-repo.git",
                description="Fork with no commits",
                language="Python",
                stars=0,
                forks_count=0,
                watchers_count=1,
                open_issues_count=0,
                size=5000,
                topics=["python"],
                license_name="MIT",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time - timedelta(days=30),
                updated_at=base_time - timedelta(days=30),
                pushed_at=base_time - timedelta(days=30),  # Same as created_at = no commits
            ),
        ]
        
        return {
            "main_repo": main_repo,
            "forks": forks,
            "languages": {"Python": 8000, "JavaScript": 2000},
            "topics": ["python", "test", "automation", "main"],
        }

    @pytest.mark.asyncio
    async def test_complete_fork_display_workflow_end_to_end(
        self, display_service, console_with_capture, comprehensive_test_data
    ):
        """Test complete fork display workflow from start to finish."""
        console, string_io = console_with_capture
        
        main_repo = comprehensive_test_data["main_repo"]
        forks = comprehensive_test_data["forks"]
        languages = comprehensive_test_data["languages"]
        topics = comprehensive_test_data["topics"]
        
        # Setup mocks
        display_service.github_client.get_repository.return_value = main_repo
        display_service.github_client.get_repository_languages.return_value = languages
        display_service.github_client.get_repository_topics.return_value = topics
        display_service.github_client.get_repository_forks.return_value = forks
        display_service.github_client.compare_repositories.return_value = {"ahead_by": 5, "behind_by": 2}
        
        # Step 1: Show repository details
        repo_result = await display_service.show_repository_details("owner/test-repo")
        repo_output = string_io.getvalue()
        string_io.truncate(0)
        string_io.seek(0)
        
        # Step 2: List forks preview
        list_result = await display_service.list_forks_preview("owner/test-repo")
        list_output = string_io.getvalue()
        string_io.truncate(0)
        string_io.seek(0)
        
        # Step 3: Show fork data (qualification)
        collected_forks = []
        for fork in forks:
            metrics = ForkQualificationMetrics(
                id=fork.id,
                owner=fork.owner,
                name=fork.name,
                full_name=fork.full_name,
                html_url=fork.html_url,
                stargazers_count=fork.stars,
                forks_count=fork.forks_count,
                watchers_count=fork.watchers_count,
                open_issues_count=fork.open_issues_count,
                size=fork.size,
                language=fork.language,
                topics=fork.topics,
                created_at=fork.created_at,
                updated_at=fork.updated_at,
                pushed_at=fork.pushed_at,
                archived=fork.is_archived,
                disabled=False,
                fork=fork.is_fork,
                commits_ahead_status="None" if fork.created_at == fork.pushed_at else "Unknown",
                can_skip_analysis=fork.created_at == fork.pushed_at,
            )
            collected_forks.append(CollectedForkData(metrics=metrics))
        
        stats = QualificationStats(
            total_forks_discovered=2,
            forks_with_commits=1,
            forks_with_no_commits=1,
            archived_forks=0,
            disabled_forks=0,
            processing_time_seconds=1.5,
            api_calls_made=1,
            api_calls_saved=1,
        )
        
        qualification_result = QualifiedForksResult(
            repository_owner="owner",
            repository_name="test-repo",
            repository_url="https://github.com/owner/test-repo",
            collected_forks=collected_forks,
            stats=stats,
        )
        
        await display_service._display_fork_data_table(qualification_result)
        fork_data_output = string_io.getvalue()
        string_io.truncate(0)
        string_io.seek(0)
        
        # Step 4: Show detailed fork analysis
        detailed_forks = []
        for i, fork_data in enumerate(collected_forks):
            if fork_data.metrics.commits_ahead_status == "None":
                fork_data.exact_commits_ahead = 0
            else:
                fork_data.exact_commits_ahead = 5  # From compare API
            detailed_forks.append(fork_data)
        
        await display_service._display_detailed_fork_table(
            detailed_forks,
            "owner",
            "test-repo",
            api_calls_made=1,
            api_calls_saved=1,
        )
        detailed_output = string_io.getvalue()
        
        # Verify complete workflow
        assert repo_result["repository"].name == "test-repo"
        assert list_result["total_forks"] == 2
        assert len(collected_forks) == 2
        
        # Verify compact format consistency across all steps
        fork_outputs = [list_output, fork_data_output, detailed_output]
        
        for output in fork_outputs:
            assert "Commits" in output or "commits" in output.lower()
            assert "│" in output or "|" in output  # Table structure
            assert "0 commits" not in output  # No verbose format
            assert "commits ahead" not in output.lower() or "Commits Ahead" in output
        
        # Verify repository details
        assert "Repository Details" in repo_output
        assert "test-repo" in repo_output
        assert "Python" in repo_output
        
        # Verify list output
        assert "contributor1" in list_output
        assert "contributor2" in list_output
        
        # Verify fork data output
        assert "2 forks" in fork_data_output
        assert "API calls saved: 1" in fork_data_output
        
        # Verify detailed output
        assert "Commits Ahead" in detailed_output
        assert "5" in detailed_output  # Exact commit count for active fork