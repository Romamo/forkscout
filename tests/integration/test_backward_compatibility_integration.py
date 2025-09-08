"""Integration tests for backward compatibility and existing functionality after commit message truncation fix."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from rich.console import Console

from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.github.client import GitHubClient
from forklift.models.github import RecentCommit, Repository


class TestBackwardCompatibilityIntegration:
    """Integration tests for backward compatibility after commit message truncation fix."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client for testing."""
        client = Mock(spec=GitHubClient)
        client.get_repository = AsyncMock()
        client.get_repository_languages = AsyncMock()
        client.get_repository_topics = AsyncMock()
        client.get_repository_forks = AsyncMock()
        client.get_commits_ahead = AsyncMock()
        client.get_recent_commits = AsyncMock()
        return client

    @pytest.fixture
    def repository_display_service(self, mock_github_client):
        """Create a repository display service for testing."""
        console = Mock(spec=Console)
        return RepositoryDisplayService(
            github_client=mock_github_client, console=console
        )

    @pytest.mark.asyncio
    async def test_show_repository_details_backward_compatibility(
        self, repository_display_service, mock_github_client
    ):
        """Test that show_repository_details maintains backward compatibility."""
        # Setup mock repository data
        mock_repo = Repository(
            id=12345,
            name="test-repo",
            owner="test-owner",
            full_name="test-owner/test-repo",
            url="https://api.github.com/repos/test-owner/test-repo",
            html_url="https://github.com/test-owner/test-repo",
            clone_url="https://github.com/test-owner/test-repo.git",
            description="Test repository",
            language="Python",
            stars=100,
            forks_count=25,
            watchers_count=100,
            open_issues_count=5,
            size=1024,
            license_name="MIT",
            default_branch="main",
            is_private=False,
            is_fork=False,
            is_archived=False,
            created_at=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 15, 14, 30, tzinfo=UTC),
            pushed_at=datetime(2024, 1, 15, 14, 30, tzinfo=UTC),
        )

        mock_languages = {"Python": 8500, "JavaScript": 1500}
        mock_topics = ["python", "testing", "automation"]

        mock_github_client.get_repository.return_value = mock_repo
        mock_github_client.get_repository_languages.return_value = mock_languages
        mock_github_client.get_repository_topics.return_value = mock_topics

        # Test the method
        result = await repository_display_service.show_repository_details(
            "test-owner/test-repo"
        )

        # Verify backward compatibility - all expected fields present
        assert result["repository"] == mock_repo
        assert result["languages"] == mock_languages
        assert result["topics"] == mock_topics
        assert result["primary_language"] == "Python"
        assert result["license"] == "MIT"
        assert "last_activity" in result
        assert "created" in result
        assert "updated" in result

        # Verify API calls were made correctly
        mock_github_client.get_repository.assert_called_once_with(
            "test-owner", "test-repo"
        )
        mock_github_client.get_repository_languages.assert_called_once_with(
            "test-owner", "test-repo"
        )
        mock_github_client.get_repository_topics.assert_called_once_with(
            "test-owner", "test-repo"
        )

    @pytest.mark.asyncio
    async def test_get_and_format_commits_ahead_with_long_messages(
        self, repository_display_service, mock_github_client
    ):
        """Test that commit formatting works with long messages in real API context."""
        # Setup mock commits with long messages
        long_message_1 = "This is an extremely long commit message that contains detailed information about the changes made, including bug fixes, feature additions, performance improvements, and documentation updates that would previously have been truncated with ellipsis"
        long_message_2 = "Another very long commit message with comprehensive details about implementation changes, refactoring efforts, code quality improvements, and extensive testing additions that should be displayed in full"

        mock_commits = [
            RecentCommit(
                short_sha="abc1234",
                message=long_message_1,
                date=datetime(2024, 1, 15, 14, 30),
            ),
            RecentCommit(
                short_sha="def5678",
                message=long_message_2,
                date=datetime(2024, 1, 14, 10, 15),
            ),
        ]

        mock_github_client.get_commits_ahead.return_value = mock_commits

        # Test the method
        result = await repository_display_service._get_and_format_commits_ahead(
            "fork-owner", "fork-repo", "base-owner", "base-repo", 2
        )

        # Verify no truncation occurred
        assert "..." not in result
        assert long_message_1 in result
        assert long_message_2 in result

        # Verify chronological ordering (newest first)
        lines = result.split("\n")
        assert lines[0] == f"2024-01-15 abc1234 {long_message_1}"
        assert lines[1] == f"2024-01-14 def5678 {long_message_2}"

        # Verify API call was made correctly
        mock_github_client.get_commits_ahead.assert_called_once_with(
            "fork-owner", "fork-repo", "base-owner", "base-repo", count=2
        )

    @pytest.mark.asyncio
    async def test_list_forks_preview_backward_compatibility(
        self, repository_display_service, mock_github_client
    ):
        """Test that list_forks_preview maintains backward compatibility."""
        # Setup mock fork data
        mock_forks = [
            Repository(
                id=1,
                name="test-repo",
                owner="fork-owner-1",
                full_name="fork-owner-1/test-repo",
                url="https://api.github.com/repos/fork-owner-1/test-repo",
                html_url="https://github.com/fork-owner-1/test-repo",
                clone_url="https://github.com/fork-owner-1/test-repo.git",
                description="Fork 1",
                language="Python",
                stars=10,
                forks_count=2,
                watchers_count=10,
                open_issues_count=1,
                size=512,
                license_name="MIT",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=datetime(2024, 1, 10, 10, 0, tzinfo=UTC),
                updated_at=datetime(2024, 1, 15, 12, 0, tzinfo=UTC),
                pushed_at=datetime(2024, 1, 15, 12, 0, tzinfo=UTC),
            ),
            Repository(
                id=2,
                name="test-repo",
                owner="fork-owner-2",
                full_name="fork-owner-2/test-repo",
                url="https://api.github.com/repos/fork-owner-2/test-repo",
                html_url="https://github.com/fork-owner-2/test-repo",
                clone_url="https://github.com/fork-owner-2/test-repo.git",
                description="Fork 2",
                language="Python",
                stars=5,
                forks_count=1,
                watchers_count=5,
                open_issues_count=0,
                size=256,
                license_name="MIT",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=datetime(2024, 1, 5, 9, 0, tzinfo=UTC),
                updated_at=datetime(2024, 1, 10, 11, 0, tzinfo=UTC),
                pushed_at=datetime(
                    2024, 1, 5, 9, 0, tzinfo=UTC
                ),  # Same as created - no commits
            ),
        ]

        mock_github_client.get_repository_forks.return_value = mock_forks

        # Test the method
        result = await repository_display_service.list_forks_preview(
            "test-owner/test-repo"
        )

        # Verify backward compatibility - expected structure
        assert "total_forks" in result
        assert "forks" in result
        assert result["total_forks"] == 2
        assert len(result["forks"]) == 2

        # Verify fork data structure (forks are converted to dict by .dict() call)
        fork_items = result["forks"]
        assert fork_items[0]["name"] == "test-repo"
        assert fork_items[0]["owner"] == "fork-owner-1"
        assert fork_items[0]["stars"] == 10
        # Activity status depends on current time vs push time - just verify it's not None
        assert fork_items[0]["activity_status"] in ["Active", "Stale", "No commits"]

        assert fork_items[1]["name"] == "test-repo"
        assert fork_items[1]["owner"] == "fork-owner-2"
        assert fork_items[1]["stars"] == 5
        assert (
            fork_items[1]["activity_status"] == "No commits"
        )  # Same created/pushed dates

        # Verify API call was made correctly
        mock_github_client.get_repository_forks.assert_called_once_with(
            "test-owner", "test-repo"
        )

    def test_parse_repository_url_all_formats_still_work(
        self, repository_display_service
    ):
        """Test that all repository URL formats continue to work."""
        test_cases = [
            ("https://github.com/owner/repo", ("owner", "repo")),
            ("https://github.com/owner/repo.git", ("owner", "repo")),
            ("https://github.com/owner/repo/", ("owner", "repo")),
            ("git@github.com:owner/repo.git", ("owner", "repo")),
            ("owner/repo", ("owner", "repo")),
        ]

        for url, expected in test_cases:
            result = repository_display_service._parse_repository_url(url)
            assert result == expected

    def test_format_datetime_all_cases_still_work(self, repository_display_service):
        """Test that datetime formatting continues to work for all cases."""
        from datetime import timedelta

        now = datetime.utcnow()

        test_cases = [
            (None, "Unknown"),
            (now, "Today"),
            (now - timedelta(days=1), "Yesterday"),
            (now - timedelta(days=3), "3 days ago"),
            (now - timedelta(days=14), "2 weeks ago"),
            (now - timedelta(days=60), "2 months ago"),
            (now - timedelta(days=400), "1 year ago"),
        ]

        for test_date, expected_pattern in test_cases:
            result = repository_display_service._format_datetime(test_date)
            if expected_pattern in ["Today", "Yesterday", "Unknown"]:
                assert result == expected_pattern
            else:
                # For relative dates, just check the pattern is present
                assert any(word in result for word in expected_pattern.split())

    def test_activity_status_calculation_unchanged(self, repository_display_service):
        """Test that activity status calculation remains unchanged."""
        from datetime import timedelta

        now = datetime.utcnow().replace(tzinfo=UTC)

        # Test cases for different activity levels
        test_cases = [
            (None, "inactive"),
            (now, "active"),
            (now - timedelta(days=60), "moderate"),
            (now - timedelta(days=200), "stale"),
            (now - timedelta(days=400), "inactive"),
        ]

        for push_date, expected_status in test_cases:
            repo = Mock()
            repo.pushed_at = push_date
            result = repository_display_service._calculate_activity_status(repo)
            assert result == expected_status

    def test_fork_activity_status_calculation_unchanged(
        self, repository_display_service
    ):
        """Test that fork activity status calculation remains unchanged."""
        from datetime import timedelta

        base_time = datetime.utcnow().replace(tzinfo=UTC)

        test_cases = [
            # No dates
            (None, None, "No commits"),
            (base_time, None, "No commits"),
            (None, base_time, "No commits"),
            # Same time (no commits after fork)
            (base_time, base_time, "No commits"),
            # Within 1 minute (no commits after fork)
            (base_time, base_time + timedelta(seconds=30), "No commits"),
            # Recent activity (within 90 days)
            (base_time - timedelta(days=100), base_time - timedelta(days=30), "Active"),
            # Old activity (more than 90 days)
            (base_time - timedelta(days=200), base_time - timedelta(days=120), "Stale"),
        ]

        for created_at, pushed_at, expected_status in test_cases:
            repo = Mock()
            repo.created_at = created_at
            repo.pushed_at = pushed_at
            result = repository_display_service._calculate_fork_activity_status(repo)
            assert result == expected_status

    def test_commits_ahead_status_calculation_unchanged(
        self, repository_display_service
    ):
        """Test that commits ahead status calculation remains unchanged."""
        from datetime import timedelta

        base_time = datetime.utcnow().replace(tzinfo=UTC)

        test_cases = [
            # No dates
            (None, None, "None"),
            (base_time, None, "None"),
            (None, base_time, "None"),
            # Created >= pushed (no new commits)
            (base_time, base_time, "None"),
            (base_time + timedelta(seconds=1), base_time, "None"),
            # Created < pushed (has commits)
            (base_time - timedelta(days=1), base_time, "Unknown"),
        ]

        for created_at, pushed_at, expected_status in test_cases:
            repo = Mock()
            repo.created_at = created_at
            repo.pushed_at = pushed_at
            result = repository_display_service._calculate_commits_ahead_status(repo)
            assert result == expected_status

    def test_styling_methods_unchanged(self, repository_display_service):
        """Test that styling methods continue to work unchanged."""
        # Test activity status styling
        assert (
            repository_display_service._style_activity_status("active")
            == "[green]Active[/green]"
        )
        assert (
            repository_display_service._style_activity_status("inactive")
            == "[red]Inactive[/red]"
        )
        assert (
            repository_display_service._style_activity_status("unknown")
            == "[dim]Unknown[/dim]"
        )

        # Test fork activity status styling
        assert (
            repository_display_service._style_fork_activity_status("Active")
            == "[green]Active[/green]"
        )
        assert (
            repository_display_service._style_fork_activity_status("Stale")
            == "[orange3]Stale[/orange3]"
        )
        assert (
            repository_display_service._style_fork_activity_status("No commits")
            == "[red]No commits[/red]"
        )

    def test_commits_formatting_methods_unchanged(self, repository_display_service):
        """Test that commit formatting methods continue to work unchanged."""
        # Test compact format
        assert repository_display_service.format_commits_compact(0, 0) == ""
        assert (
            repository_display_service.format_commits_compact(5, 0)
            == "[green]+5[/green]"
        )
        assert (
            repository_display_service.format_commits_compact(0, 3) == "[red]-3[/red]"
        )
        assert (
            repository_display_service.format_commits_compact(7, 2)
            == "[green]+7[/green] [red]-2[/red]"
        )
        assert repository_display_service.format_commits_compact(-1, 0) == "Unknown"

        # Test status format
        assert repository_display_service.format_commits_status(0, 0) == "+0 -0"
        assert repository_display_service.format_commits_status(5, 3) == "+5 -3"

    @pytest.mark.asyncio
    async def test_end_to_end_commit_display_no_truncation(
        self, repository_display_service, mock_github_client
    ):
        """End-to-end test ensuring commit display works without truncation."""
        # Setup a realistic scenario with long commit messages
        long_commits = [
            RecentCommit(
                short_sha="abc1234",
                message="feat(auth): implement comprehensive OAuth2 authentication system with JWT token management, refresh token rotation, and secure session handling for improved user security and experience",
                date=datetime(2024, 1, 15, 14, 30),
            ),
            RecentCommit(
                short_sha="def5678",
                message="fix(api): resolve critical null pointer exception in user profile endpoint that was causing 500 errors for users with incomplete profile data and implement proper validation",
                date=datetime(2024, 1, 14, 10, 15),
            ),
            RecentCommit(
                short_sha="abc9012",
                message="docs: update comprehensive API documentation with detailed examples, error codes, authentication requirements, and usage guidelines for all endpoints",
                date=datetime(2024, 1, 13, 16, 45),
            ),
        ]

        mock_github_client.get_commits_ahead.return_value = long_commits

        # Test the formatting
        result = await repository_display_service._get_and_format_commits_ahead(
            "fork-owner", "fork-repo", "base-owner", "base-repo", 3
        )

        # Verify comprehensive requirements
        lines = result.split("\n")

        # 1. No truncation
        assert "..." not in result

        # 2. Chronological sorting (newest first)
        assert lines[0].startswith("2024-01-15 abc1234")
        assert lines[1].startswith("2024-01-14 def5678")
        assert lines[2].startswith("2024-01-13 abc9012")

        # 3. Date formatting consistency (YYYY-MM-DD)
        assert "2024-01-15" in lines[0]
        assert "2024-01-14" in lines[1]
        assert "2024-01-13" in lines[2]

        # 4. Full messages preserved
        assert "comprehensive OAuth2 authentication system" in lines[0]
        assert "critical null pointer exception in user profile endpoint" in lines[1]
        assert "comprehensive API documentation with detailed examples" in lines[2]

        # 5. Structure consistency
        for line in lines:
            parts = line.split(" ", 2)
            assert len(parts) == 3
            assert len(parts[0]) == 10  # YYYY-MM-DD
            assert parts[0][4] == "-" and parts[0][7] == "-"

    def test_column_width_parameter_backward_compatibility(
        self, repository_display_service
    ):
        """Test that column_width parameter is maintained for backward compatibility."""
        from forklift.models.github import RecentCommit

        long_message = "This is a very long commit message that would have been truncated in the old implementation but should now be displayed in full regardless of the column width parameter"

        commit = RecentCommit(
            short_sha="abc1234",
            message=long_message,
            date=datetime(2024, 1, 15, 10, 30),
        )

        # Test with various column widths - all should produce the same result (no truncation)
        expected_result = f"2024-01-15 abc1234 {long_message}"

        for width in [20, 50, 100, 200]:
            result = repository_display_service.format_recent_commits(
                [commit], column_width=width
            )
            assert result == expected_result
            assert "..." not in result

    def test_calculate_commits_column_width_method_exists(
        self, repository_display_service
    ):
        """Test that calculate_commits_column_width method still exists for backward compatibility."""
        # This method should still exist even if its behavior has changed
        assert hasattr(repository_display_service, "calculate_commits_column_width")

        # Test that it can be called without errors
        commits_data = {}
        result = repository_display_service.calculate_commits_column_width(
            commits_data, show_commits=5, min_width=30, max_width=100
        )

        # Should return a reasonable width value
        assert isinstance(result, int)
        assert result >= 30  # At least min_width
