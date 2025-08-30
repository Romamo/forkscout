"""Integration tests for edge cases in compact commit display."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from io import StringIO

from rich.console import Console

from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.github.client import GitHubClient, GitHubAPIError
from forklift.models.github import Repository
from forklift.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualificationStats,
    QualifiedForksResult,
)


class TestCompactCommitDisplayEdgeCases:
    """Integration tests for edge cases in compact commit display."""

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

    @pytest.mark.asyncio
    async def test_repositories_with_no_forks_display(
        self, display_service, console_with_capture
    ):
        """Test compact display with repositories that have no forks."""
        console, string_io = console_with_capture
        
        # Mock empty forks response
        display_service.github_client.get_repository_forks.return_value = []
        
        # Test list-forks with no forks
        result = await display_service.list_forks_preview("owner/empty-repo")
        output = string_io.getvalue()
        
        # Verify graceful handling
        assert result["total_forks"] == 0
        assert result["forks"] == []
        assert "No forks found" in output
        
        # Test show-fork-data with empty qualification result
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
        # Should not crash or produce malformed output
        assert len(empty_output) > 0

    @pytest.mark.asyncio
    async def test_forks_with_various_commit_statuses(
        self, display_service, console_with_capture
    ):
        """Test compact display with forks having various commit statuses."""
        console, string_io = console_with_capture
        
        base_time = datetime.now(timezone.utc)
        
        # Create forks with different commit status scenarios
        edge_case_forks = [
            # Fork with created_at > pushed_at (reverse timestamps)
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
            # Fork with exactly same timestamps (within 1 minute)
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
            # Fork with timestamps within 1 minute (should be treated as no commits)
            Repository(
                id=3,
                name="close-time-fork",
                owner="user3",
                full_name="user3/close-time-fork",
                url="https://api.github.com/repos/user3/close-time-fork",
                html_url="https://github.com/user3/close-time-fork",
                clone_url="https://github.com/user3/close-time-fork.git",
                description="Fork with close timestamps",
                language="Go",
                stars=2,
                forks_count=0,
                watchers_count=1,
                open_issues_count=0,
                size=100,
                topics=["go"],
                license_name=None,
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time,
                updated_at=base_time,
                pushed_at=base_time + timedelta(seconds=30),  # 30 seconds later
            ),
            # Fork with missing created_at
            Repository(
                id=4,
                name="missing-created-fork",
                owner="user4",
                full_name="user4/missing-created-fork",
                url="https://api.github.com/repos/user4/missing-created-fork",
                html_url="https://github.com/user4/missing-created-fork",
                clone_url="https://github.com/user4/missing-created-fork.git",
                description="Fork with missing created_at",
                language="Rust",
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
                created_at=None,  # Missing created_at
                updated_at=base_time,
                pushed_at=base_time,
            ),
            # Fork with missing pushed_at
            Repository(
                id=5,
                name="missing-pushed-fork",
                owner="user5",
                full_name="user5/missing-pushed-fork",
                url="https://api.github.com/repos/user5/missing-pushed-fork",
                html_url="https://github.com/user5/missing-pushed-fork",
                clone_url="https://github.com/user5/missing-pushed-fork.git",
                description="Fork with missing pushed_at",
                language="C++",
                stars=0,
                forks_count=0,
                watchers_count=0,
                open_issues_count=0,
                size=30,
                topics=[],
                license_name=None,
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time,
                updated_at=base_time,
                pushed_at=None,  # Missing pushed_at
            ),
            # Fork with both timestamps missing
            Repository(
                id=6,
                name="missing-both-fork",
                owner="user6",
                full_name="user6/missing-both-fork",
                url="https://api.github.com/repos/user6/missing-both-fork",
                html_url="https://github.com/user6/missing-both-fork",
                clone_url="https://github.com/user6/missing-both-fork.git",
                description="Fork with both timestamps missing",
                language=None,
                stars=0,
                forks_count=0,
                watchers_count=0,
                open_issues_count=0,
                size=10,
                topics=[],
                license_name=None,
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=None,  # Missing created_at
                updated_at=None,
                pushed_at=None,  # Missing pushed_at
            ),
        ]
        
        display_service.github_client.get_repository_forks.return_value = edge_case_forks
        
        # Test list-forks with edge cases
        result = await display_service.list_forks_preview("owner/edge-case-repo")
        output = string_io.getvalue()
        
        # Verify all forks are handled without errors
        assert result["total_forks"] == 6
        assert len(result["forks"]) == 6
        assert "Commits" in output
        
        # Verify compact format handles edge cases correctly
        for fork in result["forks"]:
            if fork.name == "reverse-time-fork":
                assert fork.commits_ahead == "None"  # created_at > pushed_at
            elif fork.name == "exact-time-fork":
                assert fork.commits_ahead == "None"  # created_at == pushed_at
            elif fork.name == "close-time-fork":
                assert fork.commits_ahead == "None"  # Within 1 minute
            elif fork.name in ["missing-created-fork", "missing-pushed-fork", "missing-both-fork"]:
                assert fork.commits_ahead == "None"  # Missing timestamps
        
        # Test show-fork-data with edge cases
        string_io.truncate(0)
        string_io.seek(0)
        
        collected_forks = []
        for repo in edge_case_forks:
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
                created_at=repo.created_at,
                updated_at=repo.updated_at,
                pushed_at=repo.pushed_at,
                archived=repo.is_archived,
                disabled=False,
                fork=repo.is_fork,
                commits_ahead_status="None",  # All edge cases should be "None"
                can_skip_analysis=True,
            )
            collected_forks.append(CollectedForkData(metrics=metrics))
        
        stats = QualificationStats(
            total_forks_discovered=6,
            forks_with_commits=0,
            forks_with_no_commits=6,
            archived_forks=0,
            disabled_forks=0,
            processing_time_seconds=0.5,
            api_calls_made=0,
            api_calls_saved=6,
        )
        
        qualification_result = QualifiedForksResult(
            repository_owner="owner",
            repository_name="edge-case-repo",
            repository_url="https://github.com/owner/edge-case-repo",
            collected_forks=collected_forks,
            stats=stats,
        )
        
        await display_service._display_fork_data_table(qualification_result)
        edge_case_output = string_io.getvalue()
        
        # Verify edge cases are handled in fork data table
        assert "Commits" in edge_case_output
        assert "6 forks" in edge_case_output
        
        # Verify no errors in output
        assert "Error" not in edge_case_output
        assert "Exception" not in edge_case_output

    @pytest.mark.asyncio
    async def test_forks_with_extreme_values(
        self, display_service, console_with_capture
    ):
        """Test compact display with forks having extreme values."""
        console, string_io = console_with_capture
        
        base_time = datetime.now(timezone.utc)
        
        # Create forks with extreme values
        extreme_forks = [
            # Fork with very high star count
            Repository(
                id=1,
                name="popular-fork",
                owner="popular-user",
                full_name="popular-user/popular-fork",
                url="https://api.github.com/repos/popular-user/popular-fork",
                html_url="https://github.com/popular-user/popular-fork",
                clone_url="https://github.com/popular-user/popular-fork.git",
                description="Very popular fork",
                language="Python",
                stars=999999,  # Very high star count
                forks_count=50000,
                watchers_count=100000,
                open_issues_count=5000,
                size=1000000,  # Very large size
                topics=["popular", "trending"],
                license_name="MIT",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time,
                updated_at=base_time + timedelta(days=100),
                pushed_at=base_time + timedelta(days=100),
            ),
            # Fork with zero values
            Repository(
                id=2,
                name="empty-fork",
                owner="empty-user",
                full_name="empty-user/empty-fork",
                url="https://api.github.com/repos/empty-user/empty-fork",
                html_url="https://github.com/empty-user/empty-fork",
                clone_url="https://github.com/empty-user/empty-fork.git",
                description="",  # Empty description
                language=None,  # No language
                stars=0,
                forks_count=0,
                watchers_count=0,
                open_issues_count=0,
                size=0,  # Zero size
                topics=[],  # No topics
                license_name=None,  # No license
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time,
                updated_at=base_time,
                pushed_at=base_time,
            ),
            # Fork with very long names and descriptions
            Repository(
                id=3,
                name="a" * 100,  # Very long name
                owner="user-with-very-long-username-that-exceeds-normal-limits",
                full_name="user-with-very-long-username-that-exceeds-normal-limits/" + "a" * 100,
                url="https://api.github.com/repos/user-with-very-long-username-that-exceeds-normal-limits/" + "a" * 100,
                html_url="https://github.com/user-with-very-long-username-that-exceeds-normal-limits/" + "a" * 100,
                clone_url="https://github.com/user-with-very-long-username-that-exceeds-normal-limits/" + "a" * 100 + ".git",
                description="This is a very long description that goes on and on and on and contains lots of text that might cause formatting issues in tables and displays and should be handled gracefully by the compact display format without breaking the layout or causing any visual problems.",
                language="JavaScript",
                stars=42,
                forks_count=7,
                watchers_count=15,
                open_issues_count=3,
                size=500,
                topics=["very-long-topic-name-that-might-cause-issues", "another-long-topic"],
                license_name="Apache License 2.0 with very long name",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time,
                updated_at=base_time + timedelta(days=30),
                pushed_at=base_time + timedelta(days=30),
            ),
        ]
        
        display_service.github_client.get_repository_forks.return_value = extreme_forks
        
        # Test list-forks with extreme values
        result = await display_service.list_forks_preview("owner/extreme-repo")
        output = string_io.getvalue()
        
        # Verify all forks are handled without errors
        assert result["total_forks"] == 3
        assert len(result["forks"]) == 3
        assert "Commits" in output
        
        # Verify extreme values are displayed correctly
        for fork in result["forks"]:
            if fork.name == "popular-fork":
                assert fork.stars == 999999
            elif fork.name == "empty-fork":
                assert fork.stars == 0
            elif fork.name == "a" * 100:
                assert fork.stars == 42
        
        # Verify output doesn't contain formatting errors
        lines = output.split('\n')
        # Check that table structure is maintained
        table_lines = [line for line in lines if "│" in line or "|" in line]
        assert len(table_lines) > 0
        
        # Verify no line is excessively long (should be wrapped or truncated)
        for line in lines:
            assert len(line) < 200  # Reasonable line length limit

    @pytest.mark.asyncio
    async def test_api_errors_during_fork_display(
        self, display_service, console_with_capture
    ):
        """Test compact display behavior when API errors occur."""
        console, string_io = console_with_capture
        
        # Test with GitHub API error
        display_service.github_client.get_repository_forks.side_effect = GitHubAPIError(
            "API rate limit exceeded", status_code=403
        )
        
        # Test list-forks with API error
        with pytest.raises(GitHubAPIError):
            await display_service.list_forks_preview("owner/error-repo")
        
        # Verify error message was displayed
        output = string_io.getvalue()
        assert "Error" in output or "Failed" in output
        
        # Test partial API errors (some forks succeed, some fail)
        string_io.truncate(0)
        string_io.seek(0)
        
        # Reset mock to return some forks
        base_time = datetime.now(timezone.utc)
        partial_forks = [
            Repository(
                id=1,
                name="working-fork",
                owner="user1",
                full_name="user1/working-fork",
                url="https://api.github.com/repos/user1/working-fork",
                html_url="https://github.com/user1/working-fork",
                clone_url="https://github.com/user1/working-fork.git",
                description="Working fork",
                language="Python",
                stars=10,
                forks_count=2,
                watchers_count=5,
                open_issues_count=1,
                size=100,
                topics=["python"],
                license_name="MIT",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time,
                updated_at=base_time + timedelta(days=10),
                pushed_at=base_time + timedelta(days=10),
            ),
        ]
        
        display_service.github_client.get_repository_forks.side_effect = None
        display_service.github_client.get_repository_forks.return_value = partial_forks
        
        # Mock compare_repositories to fail for some forks
        display_service.github_client.compare_repositories.side_effect = GitHubAPIError(
            "Repository comparison failed", status_code=404
        )
        
        # Create qualification result with API error handling
        collected_forks = []
        for repo in partial_forks:
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
                created_at=repo.created_at,
                updated_at=repo.updated_at,
                pushed_at=repo.pushed_at,
                archived=repo.is_archived,
                disabled=False,
                fork=repo.is_fork,
                commits_ahead_status="Unknown",  # API error case
                can_skip_analysis=False,
            )
            fork_data = CollectedForkData(metrics=metrics)
            fork_data.exact_commits_ahead = "Unknown"  # API error result
            collected_forks.append(fork_data)
        
        stats = QualificationStats(
            total_forks_discovered=1,
            forks_with_commits=0,
            forks_with_no_commits=0,
            archived_forks=0,
            disabled_forks=0,
            processing_time_seconds=1.0,
            api_calls_made=1,
            api_calls_saved=0,
        )
        
        qualification_result = QualifiedForksResult(
            repository_owner="owner",
            repository_name="partial-error-repo",
            repository_url="https://github.com/owner/partial-error-repo",
            collected_forks=collected_forks,
            stats=stats,
        )
        
        await display_service._display_fork_data_table(qualification_result)
        partial_error_output = string_io.getvalue()
        
        # Verify partial errors are handled gracefully
        assert "Commits" in partial_error_output
        assert "working-fork" in partial_error_output
        # Should show "Unknown" for commits ahead due to API error
        assert "Unknown" in partial_error_output

    @pytest.mark.asyncio
    async def test_unicode_and_special_characters_in_fork_data(
        self, display_service, console_with_capture
    ):
        """Test compact display with Unicode and special characters."""
        console, string_io = console_with_capture
        
        base_time = datetime.now(timezone.utc)
        
        # Create forks with Unicode and special characters
        unicode_forks = [
            Repository(
                id=1,
                name="unicode-fork-测试",
                owner="用户名",
                full_name="用户名/unicode-fork-测试",
                url="https://api.github.com/repos/用户名/unicode-fork-测试",
                html_url="https://github.com/用户名/unicode-fork-测试",
                clone_url="https://github.com/用户名/unicode-fork-测试.git",
                description="Fork with Unicode characters: 测试 🚀 ñáéíóú",
                language="Python",
                stars=42,
                forks_count=7,
                watchers_count=15,
                open_issues_count=2,
                size=300,
                topics=["测试", "unicode", "🚀"],
                license_name="MIT",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time,
                updated_at=base_time + timedelta(days=5),
                pushed_at=base_time + timedelta(days=5),
            ),
            Repository(
                id=2,
                name="special-chars-fork",
                owner="user@domain.com",
                full_name="user@domain.com/special-chars-fork",
                url="https://api.github.com/repos/user@domain.com/special-chars-fork",
                html_url="https://github.com/user@domain.com/special-chars-fork",
                clone_url="https://github.com/user@domain.com/special-chars-fork.git",
                description="Fork with special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?",
                language="C++",
                stars=13,
                forks_count=3,
                watchers_count=8,
                open_issues_count=1,
                size=150,
                topics=["special", "chars"],
                license_name="GPL-3.0",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time,
                updated_at=base_time + timedelta(days=2),
                pushed_at=base_time + timedelta(days=2),
            ),
        ]
        
        display_service.github_client.get_repository_forks.return_value = unicode_forks
        
        # Test list-forks with Unicode characters
        result = await display_service.list_forks_preview("owner/unicode-repo")
        output = string_io.getvalue()
        
        # Verify Unicode characters are handled correctly
        assert result["total_forks"] == 2
        assert len(result["forks"]) == 2
        assert "Commits" in output
        
        # Verify Unicode characters appear in output
        assert "测试" in output or "unicode-fork" in output
        assert "special-chars-fork" in output
        
        # Verify no encoding errors
        assert "UnicodeError" not in output
        assert "Error" not in output or "Failed" not in output
        
        # Test that table structure is maintained with Unicode
        lines = output.split('\n')
        table_lines = [line for line in lines if "│" in line or "|" in line]
        assert len(table_lines) > 0

    @pytest.mark.asyncio
    async def test_very_large_number_of_forks(
        self, display_service, console_with_capture
    ):
        """Test compact display performance with large number of forks."""
        import time
        
        console, string_io = console_with_capture
        
        # Create a large number of forks
        base_time = datetime.now(timezone.utc)
        large_fork_list = []
        
        for i in range(100):  # 100 forks for performance testing
            has_commits = i % 4 != 0  # 3/4 have commits, 1/4 don't
            
            fork = Repository(
                id=i + 1,
                name=f"fork-{i:03d}",
                owner=f"user{i:03d}",
                full_name=f"user{i:03d}/fork-{i:03d}",
                url=f"https://api.github.com/repos/user{i:03d}/fork-{i:03d}",
                html_url=f"https://github.com/user{i:03d}/fork-{i:03d}",
                clone_url=f"https://github.com/user{i:03d}/fork-{i:03d}.git",
                description=f"Fork number {i}",
                language=["Python", "JavaScript", "Go", "Rust"][i % 4],
                stars=i % 50,
                forks_count=i % 10,
                watchers_count=i % 25,
                open_issues_count=i % 5,
                size=100 + i * 5,
                topics=[f"topic-{i % 3}"],
                license_name="MIT" if i % 3 == 0 else None,
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=i % 20 == 0,  # 5% archived
                created_at=base_time,
                updated_at=base_time + timedelta(days=i % 30),
                pushed_at=base_time + timedelta(days=i % 30) if has_commits else base_time,
            )
            large_fork_list.append(fork)
        
        display_service.github_client.get_repository_forks.return_value = large_fork_list
        
        # Measure performance
        start_time = time.time()
        result = await display_service.list_forks_preview("owner/large-repo")
        end_time = time.time()
        
        execution_time = end_time - start_time
        output = string_io.getvalue()
        
        # Performance assertions
        assert execution_time < 2.0  # Should complete within 2 seconds
        assert result["total_forks"] == 100
        assert len(result["forks"]) == 100
        
        # Verify output is generated correctly
        assert "Commits" in output
        assert len(output) > 1000  # Should have substantial output
        
        # Verify table structure is maintained with large dataset
        lines = output.split('\n')
        table_lines = [line for line in lines if "│" in line or "|" in line]
        assert len(table_lines) > 50  # Should have many table rows
        
        # Verify no memory issues or truncation errors
        assert "..." not in output  # No truncation indicators
        assert "Error" not in output
        assert "Exception" not in output

    @pytest.mark.asyncio
    async def test_mixed_archived_and_disabled_forks(
        self, display_service, console_with_capture
    ):
        """Test compact display with mix of archived and disabled forks."""
        console, string_io = console_with_capture
        
        base_time = datetime.now(timezone.utc)
        
        # Create mix of normal, archived, and disabled forks
        mixed_status_forks = [
            # Normal active fork
            Repository(
                id=1,
                name="normal-fork",
                owner="user1",
                full_name="user1/normal-fork",
                url="https://api.github.com/repos/user1/normal-fork",
                html_url="https://github.com/user1/normal-fork",
                clone_url="https://github.com/user1/normal-fork.git",
                description="Normal active fork",
                language="Python",
                stars=25,
                forks_count=5,
                watchers_count=12,
                open_issues_count=3,
                size=500,
                topics=["python"],
                license_name="MIT",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time,
                updated_at=base_time + timedelta(days=10),
                pushed_at=base_time + timedelta(days=10),
            ),
            # Archived fork
            Repository(
                id=2,
                name="archived-fork",
                owner="user2",
                full_name="user2/archived-fork",
                url="https://api.github.com/repos/user2/archived-fork",
                html_url="https://github.com/user2/archived-fork",
                clone_url="https://github.com/user2/archived-fork.git",
                description="Archived fork",
                language="JavaScript",
                stars=100,
                forks_count=20,
                watchers_count=50,
                open_issues_count=0,
                size=1000,
                topics=["javascript", "archived"],
                license_name="Apache-2.0",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=True,  # Archived
                created_at=base_time - timedelta(days=365),
                updated_at=base_time - timedelta(days=100),
                pushed_at=base_time - timedelta(days=100),
            ),
            # Fork with no commits (should be skipped from analysis)
            Repository(
                id=3,
                name="empty-fork",
                owner="user3",
                full_name="user3/empty-fork",
                url="https://api.github.com/repos/user3/empty-fork",
                html_url="https://github.com/user3/empty-fork",
                clone_url="https://github.com/user3/empty-fork.git",
                description="Fork with no commits",
                language=None,
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
                pushed_at=base_time,  # Same as created_at = no commits
            ),
        ]
        
        display_service.github_client.get_repository_forks.return_value = mixed_status_forks
        
        # Test list-forks with mixed status forks
        result = await display_service.list_forks_preview("owner/mixed-status-repo")
        output = string_io.getvalue()
        
        # Verify all forks are included in preview (filtering happens later)
        assert result["total_forks"] == 3
        assert len(result["forks"]) == 3
        assert "Commits" in output
        
        # Verify different statuses are handled correctly
        for fork in result["forks"]:
            if fork.name == "normal-fork":
                assert fork.commits_ahead == "Unknown"  # Has commits
            elif fork.name == "archived-fork":
                assert fork.commits_ahead == "Unknown"  # Has commits (archived status separate)
            elif fork.name == "empty-fork":
                assert fork.commits_ahead == "None"  # No commits
        
        # Test show-fork-data with filtering (archived forks might be excluded)
        string_io.truncate(0)
        string_io.seek(0)
        
        # Create qualification result with filtering applied
        collected_forks = []
        for repo in mixed_status_forks:
            if not repo.is_archived:  # Filter out archived forks
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
                    created_at=repo.created_at,
                    updated_at=repo.updated_at,
                    pushed_at=repo.pushed_at,
                    archived=repo.is_archived,
                    disabled=False,
                    fork=repo.is_fork,
                    commits_ahead_status="None" if repo.created_at == repo.pushed_at else "Unknown",
                    can_skip_analysis=repo.created_at == repo.pushed_at,
                )
                collected_forks.append(CollectedForkData(metrics=metrics))
        
        stats = QualificationStats(
            total_forks_discovered=3,
            forks_with_commits=1,
            forks_with_no_commits=1,
            archived_forks=1,
            disabled_forks=0,
            processing_time_seconds=0.8,
            api_calls_made=1,
            api_calls_saved=1,
        )
        
        qualification_result = QualifiedForksResult(
            repository_owner="owner",
            repository_name="mixed-status-repo",
            repository_url="https://github.com/owner/mixed-status-repo",
            collected_forks=collected_forks,
            stats=stats,
        )
        
        await display_service._display_fork_data_table(qualification_result)
        filtered_output = string_io.getvalue()
        
        # Verify filtering worked correctly
        assert "Commits" in filtered_output
        assert "normal-fork" in filtered_output
        assert "empty-fork" in filtered_output
        assert "archived-fork" not in filtered_output  # Should be filtered out
        
        # Verify compact format is maintained
        lines = filtered_output.split('\n')
        table_lines = [line for line in lines if "│" in line or "|" in line]
        assert len(table_lines) > 0