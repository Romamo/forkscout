"""Integration tests for complete fork display workflow with compact commit display."""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from io import StringIO

from rich.console import Console

from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.github.client import GitHubClient
from forklift.github.fork_list_processor import ForkListProcessor
from forklift.models.github import Repository
from forklift.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualificationStats,
    QualifiedForksResult,
)


class TestCompactCommitDisplayWorkflow:
    """Integration tests for complete fork display workflow with compact commit display."""

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
    def sample_repositories_mixed_commits(self):
        """Create sample repositories with mixed commit statuses."""
        base_time = datetime.now(timezone.utc)
        
        return [
            # Repository with no commits ahead (created_at == pushed_at)
            Repository(
                id=1,
                name="no-commits-fork",
                owner="user1",
                full_name="user1/no-commits-fork",
                url="https://api.github.com/repos/user1/no-commits-fork",
                html_url="https://github.com/user1/no-commits-fork",
                clone_url="https://github.com/user1/no-commits-fork.git",
                description="Fork with no commits ahead",
                language="Python",
                stars=5,
                forks_count=0,
                watchers_count=3,
                open_issues_count=0,
                size=100,
                topics=["python"],
                license_name="MIT",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time,
                updated_at=base_time,
                pushed_at=base_time,  # Same as created_at = no commits ahead
            ),
            # Repository with commits ahead (pushed_at > created_at)
            Repository(
                id=2,
                name="active-fork",
                owner="user2",
                full_name="user2/active-fork",
                url="https://api.github.com/repos/user2/active-fork",
                html_url="https://github.com/user2/active-fork",
                clone_url="https://github.com/user2/active-fork.git",
                description="Fork with commits ahead",
                language="JavaScript",
                stars=25,
                forks_count=3,
                watchers_count=15,
                open_issues_count=2,
                size=500,
                topics=["javascript", "web"],
                license_name="Apache-2.0",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time,
                updated_at=base_time + timedelta(days=30),
                pushed_at=base_time + timedelta(days=30),  # Later than created_at
            ),
            # Repository with unknown status (missing dates)
            Repository(
                id=3,
                name="unknown-fork",
                owner="user3",
                full_name="user3/unknown-fork",
                url="https://api.github.com/repos/user3/unknown-fork",
                html_url="https://github.com/user3/unknown-fork",
                clone_url="https://github.com/user3/unknown-fork.git",
                description="Fork with unknown status",
                language="Go",
                stars=10,
                forks_count=1,
                watchers_count=8,
                open_issues_count=1,
                size=200,
                topics=["go"],
                license_name=None,
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time - timedelta(days=100),  # Old created_at
                updated_at=base_time,
                pushed_at=base_time,
            ),
        ]

    @pytest.mark.asyncio
    async def test_complete_fork_display_workflow_with_compact_format(
        self, display_service, console_with_capture, sample_repositories_mixed_commits
    ):
        """Test complete fork display workflow uses compact format consistently."""
        console, string_io = console_with_capture
        
        # Mock GitHub client responses
        display_service.github_client.get_repository_forks.return_value = sample_repositories_mixed_commits
        display_service.github_client.compare_repositories.return_value = {"ahead_by": 3, "behind_by": 1}
        
        # Test 1: list-forks command (lightweight preview)
        result = await display_service.list_forks_preview("owner/test-repo")
        preview_output = string_io.getvalue()
        string_io.truncate(0)
        string_io.seek(0)
        
        # Verify compact format in preview
        assert "Commits" in preview_output
        assert result["total_forks"] == 3
        
        # Test 2: show-fork-data command (detailed qualification)
        # Create qualification result
        collected_forks = []
        for repo in sample_repositories_mixed_commits:
            # Handle None values for required datetime fields
            created_at = repo.created_at or datetime.now(timezone.utc)
            updated_at = repo.updated_at or datetime.now(timezone.utc)
            pushed_at = repo.pushed_at or datetime.now(timezone.utc)
            
            metrics = ForkQualificationMetrics(
                id=repo.id,
                owner=repo.owner,
                name=repo.name,
                full_name=repo.full_name,
                html_url=repo.html_url,
                stargazers_count=repo.stars,
                forks_count=repo.forks_count,
                watchers_count=repo.watchers_count,
                open_issues_count=repo.open_issues_count,
                size=repo.size,
                language=repo.language,
                topics=repo.topics,
                created_at=created_at,
                updated_at=updated_at,
                pushed_at=pushed_at,
                archived=repo.is_archived,
                disabled=False,
                fork=repo.is_fork,
                commits_ahead_status="None" if created_at == pushed_at else "Unknown",
                can_skip_analysis=created_at == pushed_at,
            )
            collected_forks.append(CollectedForkData(metrics=metrics))
        
        stats = QualificationStats(
            total_forks_discovered=3,
            forks_with_commits=2,
            forks_with_no_commits=1,
            archived_forks=0,
            disabled_forks=0,
            processing_time_seconds=1.0,
            api_calls_made=2,
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
        
        # Verify compact format in fork data table
        assert "Commits" in fork_data_output
        
        # Test 3: show-forks --detail command (with exact commit counts)
        detailed_forks = []
        for i, fork_data in enumerate(collected_forks):
            # Add exact commit counts
            if fork_data.metrics.commits_ahead_status == "None":
                fork_data.exact_commits_ahead = 0
            else:
                fork_data.exact_commits_ahead = 3 + i
            detailed_forks.append(fork_data)
        
        await display_service._display_detailed_fork_table(
            detailed_forks,
            "owner",
            "test-repo",
            api_calls_made=2,
            api_calls_saved=1,
        )
        detailed_output = string_io.getvalue()
        
        # Verify compact format in detailed table
        assert "Commits Ahead" in detailed_output
        
        # Verify consistent compact formatting across all outputs
        outputs = [preview_output, fork_data_output, detailed_output]
        for output in outputs:
            # Should contain table structure
            assert "│" in output or "|" in output
            # Should contain commit information
            assert "Commits" in output or "commits" in output.lower()
            # Should not contain overly verbose descriptions
            assert "commits ahead of upstream" not in output.lower()

    @pytest.mark.asyncio
    async def test_edge_case_repositories_with_no_forks(
        self, display_service, console_with_capture
    ):
        """Test workflow with repositories that have no forks."""
        console, string_io = console_with_capture
        
        # Mock empty forks response
        display_service.github_client.get_repository_forks.return_value = []
        
        # Test list-forks with no forks
        result = await display_service.list_forks_preview("owner/empty-repo")
        output = string_io.getvalue()
        
        # Verify graceful handling
        assert result["total_forks"] == 0
        assert "No forks found" in output
        
        # Test show-fork-data with no forks
        string_io.truncate(0)
        string_io.seek(0)
        
        empty_qualification_result = QualifiedForksResult(
            repository_owner="owner",
            repository_name="empty-repo",
            repository_url="https://github.com/owner/empty-repo",
            collected_forks=[],
            stats=QualificationStats(
                total_forks_discovered=0,
                forks_with_commits=0,
                forks_with_no_commits=0,
                archived_forks=0,
                disabled_forks=0,
                processing_time_seconds=0.1,
                api_calls_made=0,
                api_calls_saved=0,
            ),
        )
        
        await display_service._display_fork_data_table(empty_qualification_result)
        empty_output = string_io.getvalue()
        
        # Verify graceful handling of empty data
        assert "0 forks" in empty_output or "No forks" in empty_output

    @pytest.mark.asyncio
    async def test_edge_case_forks_with_various_commit_statuses(
        self, display_service, console_with_capture
    ):
        """Test workflow with forks having various commit statuses."""
        console, string_io = console_with_capture
        
        base_time = datetime.now(timezone.utc)
        
        # Create forks with edge case commit statuses
        edge_case_forks = [
            # Fork created after last push (created_at > pushed_at)
            Repository(
                id=1,
                name="reverse-time-fork",
                owner="user1",
                full_name="user1/reverse-time-fork",
                url="https://api.github.com/repos/user1/reverse-time-fork",
                html_url="https://github.com/user1/reverse-time-fork",
                clone_url="https://github.com/user1/reverse-time-fork.git",
                description="Fork with reverse timestamps",
                language="Python",
                stars=0,
                forks_count=0,
                watchers_count=0,
                open_issues_count=0,
                size=50,
                topics=[],
                license_name=None,
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time,
                updated_at=base_time,
                pushed_at=base_time - timedelta(days=1),  # Earlier than created_at
            ),
            # Fork with exactly same timestamps
            Repository(
                id=2,
                name="exact-time-fork",
                owner="user2",
                full_name="user2/exact-time-fork",
                url="https://api.github.com/repos/user2/exact-time-fork",
                html_url="https://github.com/user2/exact-time-fork",
                clone_url="https://github.com/user2/exact-time-fork.git",
                description="Fork with exact same timestamps",
                language="Java",
                stars=1,
                forks_count=0,
                watchers_count=1,
                open_issues_count=0,
                size=75,
                topics=["java"],
                license_name="MIT",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time,
                updated_at=base_time,
                pushed_at=base_time,  # Exactly same as created_at
            ),
            # Fork with very old timestamps (simulating missing data)
            Repository(
                id=3,
                name="missing-time-fork",
                owner="user3",
                full_name="user3/missing-time-fork",
                url="https://api.github.com/repos/user3/missing-time-fork",
                html_url="https://github.com/user3/missing-time-fork",
                clone_url="https://github.com/user3/missing-time-fork.git",
                description="Fork with very old timestamps",
                language=None,
                stars=0,
                forks_count=0,
                watchers_count=0,
                open_issues_count=0,
                size=25,
                topics=[],
                license_name=None,
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time - timedelta(days=1000),
                updated_at=base_time - timedelta(days=1000),
                pushed_at=base_time - timedelta(days=1000),
            ),
        ]
        
        display_service.github_client.get_repository_forks.return_value = edge_case_forks
        
        # Test list-forks with edge cases
        result = await display_service.list_forks_preview("owner/edge-case-repo")
        output = string_io.getvalue()
        
        # Verify all forks are handled
        assert result["total_forks"] == 3
        assert "Commits" in output
        
        # Verify compact format handles edge cases
        lines = output.split('\n')
        fork_lines = [line for line in lines if "github.com" in line]
        
        # Should have entries for all forks
        assert len(fork_lines) >= 3
        
        # Test that commits ahead status is determined correctly
        for fork in result["forks"]:
            if fork.name == "reverse-time-fork":
                assert fork.commits_ahead == "None"  # created_at > pushed_at
            elif fork.name == "exact-time-fork":
                assert fork.commits_ahead == "None"  # created_at == pushed_at
            elif fork.name == "missing-time-fork":
                assert fork.commits_ahead == "None"  # Missing timestamps

    @pytest.mark.asyncio
    async def test_workflow_performance_impact_of_compact_formatting(
        self, display_service, console_with_capture
    ):
        """Test that compact formatting doesn't significantly impact performance."""
        import time
        
        console, string_io = console_with_capture
        
        # Create a moderate number of forks for performance testing
        base_time = datetime.now(timezone.utc)
        performance_test_forks = []
        
        for i in range(20):
            has_commits = i % 3 != 0  # 2/3 have commits, 1/3 don't
            
            fork = Repository(
                id=i + 1,
                name=f"perf-fork-{i}",
                owner=f"user{i}",
                full_name=f"user{i}/perf-fork-{i}",
                url=f"https://api.github.com/repos/user{i}/perf-fork-{i}",
                html_url=f"https://github.com/user{i}/perf-fork-{i}",
                clone_url=f"https://github.com/user{i}/perf-fork-{i}.git",
                description=f"Performance test fork {i}",
                language=["Python", "JavaScript", "Go"][i % 3],
                stars=i * 2,
                forks_count=i,
                watchers_count=i + 5,
                open_issues_count=i % 5,
                size=100 + i * 10,
                topics=[f"topic-{i % 3}"],
                license_name="MIT" if i % 2 == 0 else None,
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time,
                updated_at=base_time + timedelta(days=i),
                pushed_at=base_time + timedelta(days=i) if has_commits else base_time,
            )
            performance_test_forks.append(fork)
        
        display_service.github_client.get_repository_forks.return_value = performance_test_forks
        
        # Measure performance of list-forks
        start_time = time.time()
        result = await display_service.list_forks_preview("owner/perf-test-repo")
        list_forks_time = time.time() - start_time
        
        # Performance assertion
        assert list_forks_time < 1.0  # Should complete within 1 second
        assert result["total_forks"] == 20
        
        # Verify output was generated
        output = string_io.getvalue()
        assert len(output) > 0
        assert "Commits" in output

    @pytest.mark.asyncio
    async def test_workflow_compatibility_with_existing_analysis_filtering(
        self, display_service, console_with_capture, sample_repositories_mixed_commits
    ):
        """Test that compact display is compatible with existing fork analysis and filtering."""
        console, string_io = console_with_capture
        
        display_service.github_client.get_repository_forks.return_value = sample_repositories_mixed_commits
        
        # Test with various filtering options
        
        # Test 1: Exclude archived forks
        archived_fork = Repository(
            id=4,
            name="archived-fork",
            owner="user4",
            full_name="user4/archived-fork",
            url="https://api.github.com/repos/user4/archived-fork",
            html_url="https://github.com/user4/archived-fork",
            clone_url="https://github.com/user4/archived-fork.git",
            description="Archived fork",
            language="Python",
            stars=100,
            forks_count=10,
            watchers_count=50,
            open_issues_count=0,
            size=1000,
            topics=["archived"],
            license_name="MIT",
            default_branch="main",
            is_private=False,
            is_fork=True,
            is_archived=True,  # Archived
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            pushed_at=datetime.now(timezone.utc),
        )
        
        all_forks = sample_repositories_mixed_commits + [archived_fork]
        display_service.github_client.get_repository_forks.return_value = all_forks
        
        # Create qualification result with filtering
        collected_forks = []
        for repo in all_forks:
            if not repo.is_archived:  # Filter out archived
                # Handle None values for required datetime fields
                created_at = repo.created_at or datetime.now(timezone.utc)
                updated_at = repo.updated_at or datetime.now(timezone.utc)
                pushed_at = repo.pushed_at or datetime.now(timezone.utc)
                
                metrics = ForkQualificationMetrics(
                    id=repo.id,
                    owner=repo.owner,
                    name=repo.name,
                    full_name=repo.full_name,
                    html_url=repo.html_url,
                    stargazers_count=repo.stars,
                    forks_count=repo.forks_count,
                    watchers_count=repo.watchers_count,
                    open_issues_count=repo.open_issues_count,
                    size=repo.size,
                    language=repo.language,
                    topics=repo.topics,
                    created_at=created_at,
                    updated_at=updated_at,
                    pushed_at=pushed_at,
                    archived=repo.is_archived,
                    disabled=False,
                    fork=repo.is_fork,
                    commits_ahead_status="None" if created_at == pushed_at else "Unknown",
                    can_skip_analysis=created_at == pushed_at,
                )
                collected_forks.append(CollectedForkData(metrics=metrics))
        
        stats = QualificationStats(
            total_forks_discovered=4,
            forks_with_commits=2,
            forks_with_no_commits=1,
            archived_forks=1,
            disabled_forks=0,
            processing_time_seconds=1.0,
            api_calls_made=2,
            api_calls_saved=2,
        )
        
        qualification_result = QualifiedForksResult(
            repository_owner="owner",
            repository_name="test-repo",
            repository_url="https://github.com/owner/test-repo",
            collected_forks=collected_forks,
            stats=stats,
        )
        
        await display_service._display_fork_data_table(qualification_result)
        output = string_io.getvalue()
        
        # Verify filtering worked and compact format is maintained
        assert "Commits" in output
        assert len(collected_forks) == 3  # Archived fork filtered out
        assert "archived-fork" not in output  # Should not appear in output
        
        # Verify compact format is still used
        lines = output.split('\n')
        fork_lines = [line for line in lines if "github.com" in line]
        assert len(fork_lines) >= 3

    @pytest.mark.asyncio
    async def test_end_to_end_fork_display_commands_with_compact_format(
        self, display_service, console_with_capture, sample_repositories_mixed_commits
    ):
        """End-to-end test covering all fork display commands with compact format."""
        console, string_io = console_with_capture
        
        display_service.github_client.get_repository_forks.return_value = sample_repositories_mixed_commits
        display_service.github_client.compare_repositories.return_value = {"ahead_by": 5, "behind_by": 2}
        
        # Command 1: list-forks (lightweight preview)
        result1 = await display_service.list_forks_preview("owner/test-repo")
        output1 = string_io.getvalue()
        string_io.truncate(0)
        string_io.seek(0)
        
        # Command 2: show-repository-details
        mock_repo = Repository(
            id=100,
            name="test-repo",
            owner="owner",
            full_name="owner/test-repo",
            url="https://api.github.com/repos/owner/test-repo",
            html_url="https://github.com/owner/test-repo",
            clone_url="https://github.com/owner/test-repo.git",
            description="Test repository",
            language="Python",
            stars=1000,
            forks_count=100,
            watchers_count=500,
            open_issues_count=10,
            size=5000,
            topics=["python", "test"],
            license_name="MIT",
            default_branch="main",
            is_private=False,
            is_fork=False,
            is_archived=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            pushed_at=datetime.now(timezone.utc),
        )
        
        display_service.github_client.get_repository.return_value = mock_repo
        display_service.github_client.get_repository_languages.return_value = {"Python": 8000, "JavaScript": 2000}
        display_service.github_client.get_repository_topics.return_value = ["python", "test", "automation"]
        
        result2 = await display_service.show_repository_details("owner/test-repo")
        output2 = string_io.getvalue()
        string_io.truncate(0)
        string_io.seek(0)
        
        # Command 3: show-fork-data (qualification)
        collected_forks = []
        for repo in sample_repositories_mixed_commits:
            # Handle None values for required datetime fields
            created_at = repo.created_at or datetime.now(timezone.utc)
            updated_at = repo.updated_at or datetime.now(timezone.utc)
            pushed_at = repo.pushed_at or datetime.now(timezone.utc)
            
            metrics = ForkQualificationMetrics(
                id=repo.id,
                owner=repo.owner,
                name=repo.name,
                full_name=repo.full_name,
                html_url=repo.html_url,
                stargazers_count=repo.stars,
                forks_count=repo.forks_count,
                watchers_count=repo.watchers_count,
                open_issues_count=repo.open_issues_count,
                size=repo.size,
                language=repo.language,
                topics=repo.topics,
                created_at=created_at,
                updated_at=updated_at,
                pushed_at=pushed_at,
                archived=repo.is_archived,
                disabled=False,
                fork=repo.is_fork,
                commits_ahead_status="None" if created_at == pushed_at else "Unknown",
                can_skip_analysis=created_at == pushed_at,
            )
            collected_forks.append(CollectedForkData(metrics=metrics))
        
        stats = QualificationStats(
            total_forks_discovered=3,
            forks_with_commits=2,
            forks_with_no_commits=1,
            archived_forks=0,
            disabled_forks=0,
            processing_time_seconds=1.5,
            api_calls_made=2,
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
        output3 = string_io.getvalue()
        string_io.truncate(0)
        string_io.seek(0)
        
        # Command 4: show-forks --detail (with exact commits)
        detailed_forks = []
        for i, fork_data in enumerate(collected_forks):
            if fork_data.metrics.commits_ahead_status == "None":
                fork_data.exact_commits_ahead = 0
            else:
                fork_data.exact_commits_ahead = 5 + i
            detailed_forks.append(fork_data)
        
        await display_service._display_detailed_fork_table(
            detailed_forks,
            "owner",
            "test-repo",
            api_calls_made=2,
            api_calls_saved=1,
        )
        output4 = string_io.getvalue()
        
        # Verify all commands completed successfully
        assert result1["total_forks"] == 3
        assert result2["repository"].name == "test-repo"
        
        # Verify compact format consistency across all commands
        fork_outputs = [output1, output3, output4]  # Commands that show fork data
        
        for output in fork_outputs:
            # Should contain commit information
            assert "Commits" in output or "commits" in output.lower()
            # Should use table format
            assert "│" in output or "|" in output
            # Should not use verbose format
            assert "0 commits" not in output
            assert "commits ahead" not in output.lower()
        
        # Verify repository details output
        assert "Repository Details" in output2
        assert "test-repo" in output2
        assert "Python" in output2