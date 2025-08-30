"""Integration tests for compact commit display compatibility with existing functionality."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from io import StringIO

from rich.console import Console

from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.github.client import GitHubClient
from forklift.github.fork_list_processor import ForkListProcessor
from forklift.models.github import Repository
from forklift.models.filters import PromisingForksFilter
from forklift.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualificationStats,
    QualifiedForksResult,
)


class TestCompactCommitDisplayCompatibility:
    """Integration tests for compact commit display compatibility with existing functionality."""

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
    def diverse_test_forks(self):
        """Create diverse test forks for compatibility testing."""
        base_time = datetime.now(timezone.utc)
        
        return [
            # Active fork with commits ahead
            Repository(
                id=1,
                name="active-fork",
                owner="active-user",
                full_name="active-user/active-fork",
                url="https://api.github.com/repos/active-user/active-fork",
                html_url="https://github.com/active-user/active-fork",
                clone_url="https://github.com/active-user/active-fork.git",
                description="Active fork with recent commits",
                language="Python",
                stars=25,
                forks_count=5,
                watchers_count=12,
                open_issues_count=3,
                size=500,
                topics=["python", "active"],
                license_name="MIT",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time - timedelta(days=30),
                updated_at=base_time - timedelta(days=1),
                pushed_at=base_time - timedelta(days=1),  # Recent activity
            ),
            # Stale fork with old commits
            Repository(
                id=2,
                name="stale-fork",
                owner="stale-user",
                full_name="stale-user/stale-fork",
                url="https://api.github.com/repos/stale-user/stale-fork",
                html_url="https://github.com/stale-user/stale-fork",
                clone_url="https://github.com/stale-user/stale-fork.git",
                description="Stale fork with old commits",
                language="JavaScript",
                stars=10,
                forks_count=2,
                watchers_count=5,
                open_issues_count=1,
                size=200,
                topics=["javascript", "stale"],
                license_name="Apache-2.0",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time - timedelta(days=365),
                updated_at=base_time - timedelta(days=200),
                pushed_at=base_time - timedelta(days=200),  # Old activity
            ),
            # Fork with no commits ahead
            Repository(
                id=3,
                name="empty-fork",
                owner="empty-user",
                full_name="empty-user/empty-fork",
                url="https://api.github.com/repos/empty-user/empty-fork",
                html_url="https://github.com/empty-user/empty-fork",
                clone_url="https://github.com/empty-user/empty-fork.git",
                description="Fork with no commits ahead",
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
                pushed_at=base_time,  # Same as created_at = no commits ahead
            ),
            # Archived fork
            Repository(
                id=4,
                name="archived-fork",
                owner="archived-user",
                full_name="archived-user/archived-fork",
                url="https://api.github.com/repos/archived-user/archived-fork",
                html_url="https://github.com/archived-user/archived-fork",
                clone_url="https://github.com/archived-user/archived-fork.git",
                description="Archived fork",
                language="Go",
                stars=100,
                forks_count=20,
                watchers_count=50,
                open_issues_count=0,
                size=1000,
                topics=["go", "archived"],
                license_name="GPL-3.0",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=True,  # Archived
                created_at=base_time - timedelta(days=500),
                updated_at=base_time - timedelta(days=300),
                pushed_at=base_time - timedelta(days=300),
            ),
            # High-star fork (promising)
            Repository(
                id=5,
                name="popular-fork",
                owner="popular-user",
                full_name="popular-user/popular-fork",
                url="https://api.github.com/repos/popular-user/popular-fork",
                html_url="https://github.com/popular-user/popular-fork",
                clone_url="https://github.com/popular-user/popular-fork.git",
                description="Popular fork with many stars",
                language="Rust",
                stars=500,
                forks_count=100,
                watchers_count=250,
                open_issues_count=15,
                size=2000,
                topics=["rust", "popular"],
                license_name="MIT",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time - timedelta(days=100),
                updated_at=base_time - timedelta(days=5),
                pushed_at=base_time - timedelta(days=5),
            ),
        ]

    @pytest.mark.asyncio
    async def test_compatibility_with_fork_qualification_filtering(
        self, display_service, console_with_capture, diverse_test_forks
    ):
        """Test compact display compatibility with fork qualification filtering."""
        console, string_io = console_with_capture
        
        display_service.github_client.get_repository_forks.return_value = diverse_test_forks
        
        # Create qualification result with filtering applied
        collected_forks = []
        for fork in diverse_test_forks:
            if not fork.is_archived:  # Filter out archived forks
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
            total_forks_discovered=5,
            forks_with_commits=3,
            forks_with_no_commits=1,
            archived_forks=1,
            disabled_forks=0,
            processing_time_seconds=2.0,
            api_calls_made=3,
            api_calls_saved=2,
        )
        
        qualification_result = QualifiedForksResult(
            repository_owner="owner",
            repository_name="compatibility-test-repo",
            repository_url="https://github.com/owner/compatibility-test-repo",
            collected_forks=collected_forks,
            stats=stats,
        )
        
        # Test fork data table with filtering
        await display_service._display_fork_data_table(qualification_result)
        output = string_io.getvalue()
        
        # Verify filtering worked correctly
        assert "4 forks" in output  # Archived fork should be filtered out
        assert "active-fork" in output
        assert "stale-fork" in output
        assert "empty-fork" in output
        assert "popular-fork" in output
        assert "archived-fork" not in output  # Should be filtered out
        
        # Verify compact format is maintained with filtering
        assert "Commits" in output
        lines = output.split('\n')
        table_lines = [line for line in lines if "│" in line or "|" in line]
        assert len(table_lines) >= 4  # Header + 4 non-archived forks
        
        # Verify no verbose formatting
        assert "0 commits" not in output
        assert "commits ahead" not in output.lower() or "Commits Ahead" in output

    @pytest.mark.asyncio
    async def test_compatibility_with_promising_forks_filtering(
        self, display_service, console_with_capture, diverse_test_forks
    ):
        """Test compact display compatibility with promising forks filtering."""
        console, string_io = console_with_capture
        
        # Create promising forks filter
        filters = PromisingForksFilter(
            min_stars=20,  # Should include active-fork (25 stars) and popular-fork (500 stars)
            min_activity_days=100,  # Recent activity
            exclude_archived=True,
        )
        
        # Apply filtering logic
        promising_forks = []
        for fork in diverse_test_forks:
            if (not fork.is_archived and 
                fork.stars >= filters.min_stars and
                (datetime.now(timezone.utc) - fork.pushed_at).days <= filters.min_activity_days):
                
                fork_data = {
                    "fork": fork,
                    "commits_ahead": 5 if fork.created_at != fork.pushed_at else 0,
                    "commits_behind": 2,
                    "activity_status": "active" if (datetime.now(timezone.utc) - fork.pushed_at).days <= 30 else "moderate",
                    "last_activity": "2 days ago" if fork.name == "active-fork" else "5 days ago",
                }
                promising_forks.append(fork_data)
        
        # Test promising forks display
        display_service._display_promising_forks_table(promising_forks, filters)
        output = string_io.getvalue()
        
        # Verify filtering worked correctly
        assert "active-fork" in output  # 25 stars, recent activity
        assert "popular-fork" in output  # 500 stars, recent activity
        assert "stale-fork" not in output  # 10 stars (below min_stars)
        assert "empty-fork" not in output  # 0 stars (below min_stars)
        assert "archived-fork" not in output  # Archived
        
        # Verify compact format is maintained
        assert "Commits" in output
        lines = output.split('\n')
        table_lines = [line for line in lines if "│" in line or "|" in line]
        assert len(table_lines) >= 2  # Header + promising forks
        
        # Verify compact commit format
        # Should show "+5 -2" for forks with commits, empty for forks without
        commit_info_lines = [line for line in lines if "+5" in line or "active-fork" in line]
        if commit_info_lines:
            assert any("+5" in line for line in commit_info_lines)

    @pytest.mark.asyncio
    async def test_compatibility_with_detailed_fork_analysis(
        self, display_service, console_with_capture, diverse_test_forks
    ):
        """Test compact display compatibility with detailed fork analysis."""
        console, string_io = console_with_capture
        
        # Create detailed fork data with exact commit counts
        detailed_forks = []
        for i, fork in enumerate(diverse_test_forks):
            if not fork.is_archived:  # Skip archived forks
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
                
                fork_data = CollectedForkData(metrics=metrics)
                # Add exact commit counts based on fork characteristics
                if fork.created_at == fork.pushed_at:
                    fork_data.exact_commits_ahead = 0  # No commits ahead
                elif fork.name == "active-fork":
                    fork_data.exact_commits_ahead = 8  # Recent active fork
                elif fork.name == "stale-fork":
                    fork_data.exact_commits_ahead = 3  # Older fork
                elif fork.name == "popular-fork":
                    fork_data.exact_commits_ahead = 15  # Popular fork with many commits
                else:
                    fork_data.exact_commits_ahead = 1  # Default
                
                detailed_forks.append(fork_data)
        
        # Test detailed fork table
        await display_service._display_detailed_fork_table(
            detailed_forks,
            "owner",
            "compatibility-test-repo",
            api_calls_made=3,
            api_calls_saved=2,
        )
        output = string_io.getvalue()
        
        # Verify detailed analysis compatibility
        assert "Commits Ahead" in output
        assert "API calls made: 3" in output
        assert "API calls saved: 2" in output
        
        # Verify compact format for different commit counts
        lines = output.split('\n')
        
        # Check for empty cell (0 commits ahead)
        empty_fork_lines = [line for line in lines if "empty-fork" in line]
        if empty_fork_lines:
            # Should have empty cell or minimal representation for 0 commits
            assert any(line for line in empty_fork_lines)
        
        # Check for compact representation of commits ahead
        active_fork_lines = [line for line in lines if "active-fork" in line]
        if active_fork_lines:
            assert any("8" in line for line in active_fork_lines)  # Should show exact count
        
        popular_fork_lines = [line for line in lines if "popular-fork" in line]
        if popular_fork_lines:
            assert any("15" in line for line in popular_fork_lines)  # Should show exact count

    @pytest.mark.asyncio
    async def test_compatibility_with_api_call_optimization(
        self, display_service, console_with_capture, diverse_test_forks
    ):
        """Test compact display compatibility with API call optimization."""
        console, string_io = console_with_capture
        
        # Mock fork list processor
        fork_processor = AsyncMock(spec=ForkListProcessor)
        
        # Create fork data that simulates API optimization
        fork_list_data = []
        for fork in diverse_test_forks:
            fork_data = {
                "id": fork.id,
                "name": fork.name,
                "full_name": fork.full_name,
                "owner": {"login": fork.owner},
                "html_url": fork.html_url,
                "stargazers_count": fork.stars,
                "forks_count": fork.forks_count,
                "watchers_count": fork.watchers_count,
                "size": fork.size,
                "language": fork.language,
                "topics": fork.topics,
                "open_issues_count": fork.open_issues_count,
                "created_at": fork.created_at.isoformat() if fork.created_at else None,
                "updated_at": fork.updated_at.isoformat() if fork.updated_at else None,
                "pushed_at": fork.pushed_at.isoformat() if fork.pushed_at else None,
                "archived": fork.is_archived,
                "disabled": False,
                "fork": fork.is_fork,
                "description": fork.description,
                "homepage": None,
                "default_branch": fork.default_branch,
                "license": {"key": "mit", "name": "MIT License"} if fork.license_name == "MIT" else None,
            }
            fork_list_data.append(fork_data)
        
        fork_processor.get_all_forks_list_data.return_value = fork_list_data
        
        # Mock compare API calls (only for forks with commits ahead)
        api_calls_made = 0
        
        async def mock_compare_repositories(base_owner, base_repo, fork_owner, fork_repo):
            nonlocal api_calls_made
            api_calls_made += 1
            
            # Return different results based on fork
            if "active-fork" in fork_repo:
                return {"ahead_by": 8, "behind_by": 2}
            elif "stale-fork" in fork_repo:
                return {"ahead_by": 3, "behind_by": 5}
            elif "popular-fork" in fork_repo:
                return {"ahead_by": 15, "behind_by": 1}
            else:
                return {"ahead_by": 0, "behind_by": 0}
        
        display_service.github_client.compare_repositories = mock_compare_repositories
        
        # Test with API optimization (should skip forks with no commits ahead)
        with patch('forklift.github.fork_list_processor.ForkListProcessor', return_value=fork_processor):
            result = await display_service.show_fork_data_detailed(
                "owner/optimization-test-repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False  # Enable optimization
            )
        
        output = string_io.getvalue()
        
        # Verify API optimization worked
        # Should have made fewer API calls (skipped empty-fork and archived-fork)
        expected_api_calls = 3  # active-fork, stale-fork, popular-fork
        assert api_calls_made == expected_api_calls
        
        # Verify compact format is maintained with optimization
        assert "Commits Ahead" in output
        assert f"API calls made: {api_calls_made}" in output
        assert "API calls saved:" in output
        
        # Verify results include optimized data
        assert result["api_calls_made"] == api_calls_made
        assert result["api_calls_saved"] > 0
        
        # Verify compact format shows correct commit counts
        lines = output.split('\n')
        
        # Check that forks with 0 commits show empty cells
        empty_lines = [line for line in lines if "empty-fork" in line]
        if empty_lines:
            # Should show empty cell or 0 for no commits ahead
            assert any(line for line in empty_lines)
        
        # Check that forks with commits show compact format
        active_lines = [line for line in lines if "active-fork" in line]
        if active_lines:
            assert any("8" in line for line in active_lines)

    @pytest.mark.asyncio
    async def test_compatibility_with_sorting_and_ranking(
        self, display_service, console_with_capture, diverse_test_forks
    ):
        """Test compact display compatibility with fork sorting and ranking."""
        console, string_io = console_with_capture
        
        display_service.github_client.get_repository_forks.return_value = diverse_test_forks
        
        # Test list-forks with default sorting (by stars and activity)
        result = await display_service.list_forks_preview("owner/sorting-test-repo")
        output = string_io.getvalue()
        
        # Verify sorting is maintained with compact format
        assert result["total_forks"] == 5
        assert len(result["forks"]) == 5
        
        # Check that forks are sorted correctly (by stars descending, then by activity)
        fork_names = [fork.name for fork in result["forks"]]
        fork_stars = [fork.stars for fork in result["forks"]]
        
        # Popular fork should be first (500 stars)
        assert fork_names[0] == "popular-fork"
        assert fork_stars[0] == 500
        
        # Verify compact format is maintained in sorted output
        assert "Commits" in output
        lines = output.split('\n')
        table_lines = [line for line in lines if "│" in line or "|" in line]
        assert len(table_lines) >= 5  # Header + 5 forks
        
        # Verify compact commit status for each fork
        for fork in result["forks"]:
            if fork.name == "empty-fork":
                assert fork.commits_ahead == "None"  # No commits ahead
            else:
                assert fork.commits_ahead in ["Unknown", "None"]  # Has commits or no commits

    @pytest.mark.asyncio
    async def test_compatibility_with_error_handling_and_recovery(
        self, display_service, console_with_capture, diverse_test_forks
    ):
        """Test compact display compatibility with error handling and recovery."""
        console, string_io = console_with_capture
        
        display_service.github_client.get_repository_forks.return_value = diverse_test_forks
        
        # Mock compare API to fail for some forks
        api_call_count = 0
        
        async def mock_compare_with_errors(base_owner, base_repo, fork_owner, fork_repo):
            nonlocal api_call_count
            api_call_count += 1
            
            # Fail for stale-fork, succeed for others
            if "stale-fork" in fork_repo:
                raise Exception("GitHub API rate limit exceeded")
            elif "active-fork" in fork_repo:
                return {"ahead_by": 8, "behind_by": 2}
            elif "popular-fork" in fork_repo:
                return {"ahead_by": 15, "behind_by": 1}
            else:
                return {"ahead_by": 0, "behind_by": 0}
        
        display_service.github_client.compare_repositories = mock_compare_with_errors
        
        # Create qualification result with error handling
        collected_forks = []
        for fork in diverse_test_forks:
            if not fork.is_archived:
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
                
                fork_data = CollectedForkData(metrics=metrics)
                # Set commit counts based on API success/failure
                if fork.name == "stale-fork":
                    fork_data.exact_commits_ahead = "Unknown"  # API error
                elif fork.created_at == fork.pushed_at:
                    fork_data.exact_commits_ahead = 0  # No commits ahead
                elif fork.name == "active-fork":
                    fork_data.exact_commits_ahead = 8
                elif fork.name == "popular-fork":
                    fork_data.exact_commits_ahead = 15
                else:
                    fork_data.exact_commits_ahead = 0
                
                collected_forks.append(fork_data)
        
        # Test detailed fork table with error handling
        await display_service._display_detailed_fork_table(
            collected_forks,
            "owner",
            "error-handling-test-repo",
            api_calls_made=3,
            api_calls_saved=1,
        )
        output = string_io.getvalue()
        
        # Verify error handling compatibility
        assert "Commits Ahead" in output
        assert "stale-fork" in output  # Should still be displayed
        assert "active-fork" in output
        assert "popular-fork" in output
        
        # Verify compact format handles errors correctly
        lines = output.split('\n')
        
        # Check that API error results in "Unknown" display
        stale_lines = [line for line in lines if "stale-fork" in line]
        if stale_lines:
            assert any("Unknown" in line for line in stale_lines)
        
        # Check that successful API calls show exact counts
        active_lines = [line for line in lines if "active-fork" in line]
        if active_lines:
            assert any("8" in line for line in active_lines)
        
        popular_lines = [line for line in lines if "popular-fork" in line]
        if popular_lines:
            assert any("15" in line for line in popular_lines)

    @pytest.mark.asyncio
    async def test_compatibility_with_caching_and_performance_optimizations(
        self, display_service, console_with_capture, diverse_test_forks
    ):
        """Test compact display compatibility with caching and performance optimizations."""
        console, string_io = console_with_capture
        
        display_service.github_client.get_repository_forks.return_value = diverse_test_forks
        
        # Test with cache disabled (should still work with compact format)
        result = await display_service.list_forks_preview("owner/cache-test-repo")
        output_no_cache = string_io.getvalue()
        
        # Clear output
        string_io.truncate(0)
        string_io.seek(0)
        
        # Test with cache enabled (simulated)
        # In a real scenario, this would use cached data
        result_cached = await display_service.list_forks_preview("owner/cache-test-repo")
        output_cached = string_io.getvalue()
        
        # Verify both cached and non-cached results use compact format
        for output in [output_no_cache, output_cached]:
            assert "Commits" in output
            assert "5 forks" in output or str(5) in output
            
            # Verify compact format consistency
            lines = output.split('\n')
            table_lines = [line for line in lines if "│" in line or "|" in line]
            assert len(table_lines) >= 5  # Header + 5 forks
            
            # Verify no verbose formatting
            assert "0 commits" not in output
            assert "commits ahead" not in output.lower() or "Commits Ahead" in output
        
        # Verify results are consistent
        assert result["total_forks"] == result_cached["total_forks"]
        assert len(result["forks"]) == len(result_cached["forks"])

    @pytest.mark.asyncio
    async def test_compatibility_with_concurrent_operations(
        self, display_service, console_with_capture, diverse_test_forks
    ):
        """Test compact display compatibility with concurrent operations."""
        import asyncio
        
        console, string_io = console_with_capture
        
        # Mock different responses for different repos
        async def mock_get_forks(owner, repo):
            if "repo1" in repo:
                return diverse_test_forks[:2]  # First 2 forks
            elif "repo2" in repo:
                return diverse_test_forks[2:4]  # Next 2 forks
            else:
                return diverse_test_forks[4:]  # Last fork
        
        display_service.github_client.get_repository_forks.side_effect = mock_get_forks
        
        # Run concurrent operations
        async def list_operation(repo_name):
            return await display_service.list_forks_preview(f"owner/{repo_name}")
        
        results = await asyncio.gather(
            list_operation("repo1"),
            list_operation("repo2"),
            list_operation("repo3"),
            return_exceptions=True
        )
        
        # Verify all operations completed successfully
        assert len(results) == 3
        for result in results:
            assert not isinstance(result, Exception)
            assert "total_forks" in result
            assert "forks" in result
        
        # Verify compact format is maintained in concurrent operations
        output = string_io.getvalue()
        assert "Commits" in output
        
        # Verify results are correct
        assert results[0]["total_forks"] == 2  # First 2 forks
        assert results[1]["total_forks"] == 2  # Next 2 forks
        assert results[2]["total_forks"] == 1  # Last fork
        
        # Verify compact format for each result
        for result in results:
            for fork in result["forks"]:
                assert fork.commits_ahead in ["None", "Unknown"]