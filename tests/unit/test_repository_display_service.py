"""Unit tests for Repository Display Service."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from rich.console import Console

from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.github.client import GitHubAPIError
from forklift.models.github import Repository


class TestRepositoryDisplayService:
    """Test Repository Display Service functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_github_client = Mock()
        self.mock_console = Mock(spec=Console)
        self.service = RepositoryDisplayService(
            github_client=self.mock_github_client, console=self.mock_console
        )

    def test_init_with_console(self):
        """Test initialization with provided console."""
        console = Mock(spec=Console)
        service = RepositoryDisplayService(self.mock_github_client, console)
        assert service.github_client == self.mock_github_client
        assert service.console == console

    def test_init_without_console(self):
        """Test initialization without console creates new one."""
        service = RepositoryDisplayService(self.mock_github_client)
        assert service.github_client == self.mock_github_client
        assert service.console is not None

    def test_init_with_configuration_flags_default(self):
        """Test initialization with default configuration flags."""
        service = RepositoryDisplayService(self.mock_github_client)
        assert service._should_exclude_language_distribution is True
        assert service._should_exclude_fork_insights is True

    def test_init_with_configuration_flags_custom(self):
        """Test initialization with custom configuration flags."""
        service = RepositoryDisplayService(
            self.mock_github_client,
            should_exclude_language_distribution=False,
            should_exclude_fork_insights=False,
        )
        assert service._should_exclude_language_distribution is False
        assert service._should_exclude_fork_insights is False

    def test_parse_repository_url_https(self):
        """Test parsing HTTPS GitHub URLs."""
        owner, repo = self.service._parse_repository_url(
            "https://github.com/owner/repo"
        )
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repository_url_https_with_git(self):
        """Test parsing HTTPS URLs with .git suffix."""
        owner, repo = self.service._parse_repository_url(
            "https://github.com/owner/repo.git"
        )
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repository_url_https_with_slash(self):
        """Test parsing HTTPS URLs with trailing slash."""
        owner, repo = self.service._parse_repository_url(
            "https://github.com/owner/repo/"
        )
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repository_url_ssh(self):
        """Test parsing SSH GitHub URLs."""
        owner, repo = self.service._parse_repository_url(
            "git@github.com:owner/repo.git"
        )
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repository_url_short_format(self):
        """Test parsing short owner/repo format."""
        owner, repo = self.service._parse_repository_url("owner/repo")
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repository_url_invalid(self):
        """Test parsing invalid URLs raises ValueError."""
        with pytest.raises(ValueError, match="Invalid GitHub repository URL"):
            self.service._parse_repository_url("invalid-url")

    def test_format_datetime_none(self):
        """Test formatting None datetime."""
        result = self.service._format_datetime(None)
        assert result == "Unknown"

    def test_format_datetime_today(self):
        """Test formatting today's datetime."""
        now = datetime.utcnow()
        result = self.service._format_datetime(now)
        assert result == "Today"

    def test_format_datetime_yesterday(self):
        """Test formatting yesterday's datetime."""
        from datetime import timedelta

        yesterday = datetime.utcnow() - timedelta(days=1)
        result = self.service._format_datetime(yesterday)
        assert result == "Yesterday"

    def test_format_datetime_days_ago(self):
        """Test formatting datetime from days ago."""
        from datetime import timedelta

        three_days_ago = datetime.utcnow() - timedelta(days=3)
        result = self.service._format_datetime(three_days_ago)
        assert "3 days ago" in result

    def test_format_datetime_weeks_ago(self):
        """Test formatting datetime from weeks ago."""
        from datetime import timedelta

        two_weeks_ago = datetime.utcnow() - timedelta(days=14)
        result = self.service._format_datetime(two_weeks_ago)
        assert "week" in result

    def test_calculate_activity_status_no_push_date(self):
        """Test activity status calculation with no push date."""
        repo = Mock()
        repo.pushed_at = None
        result = self.service._calculate_activity_status(repo)
        assert result == "inactive"

    def test_calculate_activity_status_active(self):
        """Test activity status calculation for active repository."""
        repo = Mock()
        repo.pushed_at = datetime.utcnow().replace(tzinfo=UTC)
        result = self.service._calculate_activity_status(repo)
        assert result == "active"

    def test_calculate_activity_status_moderate(self):
        """Test activity status calculation for moderately active repository."""
        from datetime import timedelta

        repo = Mock()
        repo.pushed_at = (datetime.utcnow() - timedelta(days=60)).replace(tzinfo=UTC)
        result = self.service._calculate_activity_status(repo)
        assert result == "moderate"

    def test_calculate_activity_status_stale(self):
        """Test activity status calculation for stale repository."""
        from datetime import timedelta

        repo = Mock()
        repo.pushed_at = (datetime.utcnow() - timedelta(days=200)).replace(tzinfo=UTC)
        result = self.service._calculate_activity_status(repo)
        assert result == "stale"

    def test_calculate_activity_status_inactive(self):
        """Test activity status calculation for inactive repository."""
        repo = Mock()
        repo.pushed_at = (
            datetime.utcnow()
            .replace(year=datetime.utcnow().year - 2)
            .replace(tzinfo=UTC)
        )
        result = self.service._calculate_activity_status(repo)
        assert result == "inactive"

    def test_style_activity_status_active(self):
        """Test styling active status."""
        result = self.service._style_activity_status("active")
        assert result == "[green]Active[/green]"

    def test_style_activity_status_inactive(self):
        """Test styling inactive status."""
        result = self.service._style_activity_status("inactive")
        assert result == "[red]Inactive[/red]"

    def test_style_activity_status_unknown(self):
        """Test styling unknown status."""
        result = self.service._style_activity_status("unknown_status")
        assert result == "unknown_status"

    def test_calculate_fork_activity_status_no_created_date(self):
        """Test fork activity status calculation with no created date."""
        repo = Mock()
        repo.created_at = None
        repo.pushed_at = datetime.utcnow().replace(tzinfo=UTC)
        result = self.service._calculate_fork_activity_status(repo)
        assert result == "No commits"

    def test_calculate_fork_activity_status_no_pushed_date(self):
        """Test fork activity status calculation with no pushed date."""
        repo = Mock()
        repo.created_at = datetime.utcnow().replace(tzinfo=UTC)
        repo.pushed_at = None
        result = self.service._calculate_fork_activity_status(repo)
        assert result == "No commits"

    def test_calculate_fork_activity_status_no_commits(self):
        """Test fork activity status calculation when no commits were made after forking."""
        base_time = datetime.utcnow().replace(tzinfo=UTC)
        repo = Mock()
        repo.created_at = base_time
        repo.pushed_at = base_time  # Same time means no commits after fork
        result = self.service._calculate_fork_activity_status(repo)
        assert result == "No commits"

    def test_calculate_fork_activity_status_no_commits_within_minute(self):
        """Test fork activity status calculation when pushed_at is within 1 minute of created_at."""
        base_time = datetime.utcnow().replace(tzinfo=UTC)
        repo = Mock()
        repo.created_at = base_time
        repo.pushed_at = base_time + timedelta(seconds=30)  # 30 seconds later
        result = self.service._calculate_fork_activity_status(repo)
        assert result == "No commits"

    def test_calculate_fork_activity_status_active_recent(self):
        """Test fork activity status calculation for recently active fork."""
        base_time = datetime.utcnow().replace(tzinfo=UTC)
        repo = Mock()
        repo.created_at = base_time - timedelta(days=100)  # Created 100 days ago
        repo.pushed_at = base_time - timedelta(days=30)  # Last push 30 days ago
        result = self.service._calculate_fork_activity_status(repo)
        assert result == "Active"

    def test_calculate_fork_activity_status_active_edge_case(self):
        """Test fork activity status calculation for fork active exactly 90 days ago."""
        base_time = datetime.utcnow().replace(tzinfo=UTC)
        repo = Mock()
        repo.created_at = base_time - timedelta(days=200)  # Created 200 days ago
        repo.pushed_at = base_time - timedelta(days=90)  # Last push exactly 90 days ago
        result = self.service._calculate_fork_activity_status(repo)
        assert result == "Active"

    def test_calculate_fork_activity_status_stale(self):
        """Test fork activity status calculation for stale fork."""
        base_time = datetime.utcnow().replace(tzinfo=UTC)
        repo = Mock()
        repo.created_at = base_time - timedelta(days=365)  # Created 1 year ago
        repo.pushed_at = base_time - timedelta(days=180)  # Last push 6 months ago
        result = self.service._calculate_fork_activity_status(repo)
        assert result == "Stale"

    def test_calculate_fork_activity_status_with_commits_but_old(self):
        """Test fork activity status calculation for fork with commits but very old."""
        base_time = datetime.utcnow().replace(tzinfo=UTC)
        repo = Mock()
        repo.created_at = base_time - timedelta(days=500)  # Created 500 days ago
        repo.pushed_at = base_time - timedelta(
            days=400
        )  # Last push 400 days ago (has commits but old)
        result = self.service._calculate_fork_activity_status(repo)
        assert result == "Stale"

    def test_style_fork_activity_status_active(self):
        """Test styling fork activity status for active."""
        result = self.service._style_fork_activity_status("Active")
        assert result == "[green]Active[/green]"

    def test_style_fork_activity_status_stale(self):
        """Test styling fork activity status for stale."""
        result = self.service._style_fork_activity_status("Stale")
        assert result == "[orange3]Stale[/orange3]"

    def test_style_fork_activity_status_no_commits(self):
        """Test styling fork activity status for no commits."""
        result = self.service._style_fork_activity_status("No commits")
        assert result == "[red]No commits[/red]"

    def test_style_fork_activity_status_unknown(self):
        """Test styling fork activity status for unknown status."""
        result = self.service._style_fork_activity_status("unknown_status")
        assert result == "unknown_status"

    def test_format_commits_ahead_simple_none(self):
        """Test formatting commits ahead status 'None' as 'No'."""
        result = self.service._format_commits_ahead_simple("None")
        assert result == "No"

    def test_format_commits_ahead_simple_no_commits_ahead(self):
        """Test formatting commits ahead status 'No commits ahead' as 'No'."""
        result = self.service._format_commits_ahead_simple("No commits ahead")
        assert result == "No"

    def test_format_commits_ahead_simple_unknown(self):
        """Test formatting commits ahead status 'Unknown' as 'Yes'."""
        result = self.service._format_commits_ahead_simple("Unknown")
        assert result == "Yes"

    def test_format_commits_ahead_simple_has_commits(self):
        """Test formatting commits ahead status 'Has commits' as 'Yes'."""
        result = self.service._format_commits_ahead_simple("Has commits")
        assert result == "Yes"

    def test_format_commits_ahead_simple_other(self):
        """Test formatting unknown commits ahead status as 'Unknown'."""
        result = self.service._format_commits_ahead_simple("some_other_status")
        assert result == "Unknown"

    def test_format_commits_ahead_detailed_none(self):
        """Test format_commits_ahead_detailed with None status."""
        result = self.service._format_commits_ahead_detailed("None")
        assert result == "[dim]0 commits[/dim]"

    def test_format_commits_ahead_detailed_no_commits_ahead(self):
        """Test format_commits_ahead_detailed with 'No commits ahead' status."""
        result = self.service._format_commits_ahead_detailed("No commits ahead")
        assert result == "[dim]0 commits[/dim]"

    def test_format_commits_ahead_detailed_unknown(self):
        """Test format_commits_ahead_detailed with Unknown status."""
        result = self.service._format_commits_ahead_detailed("Unknown")
        assert result == "[yellow]Unknown[/yellow]"

    def test_format_commits_ahead_detailed_has_commits(self):
        """Test format_commits_ahead_detailed with 'Has commits' status."""
        result = self.service._format_commits_ahead_detailed("Has commits")
        assert result == "[yellow]Unknown[/yellow]"

    def test_format_commits_ahead_detailed_other(self):
        """Test format_commits_ahead_detailed with other status."""
        result = self.service._format_commits_ahead_detailed("other")
        assert result == "[yellow]Unknown[/yellow]"

    def test_style_commits_ahead_status_simple_no(self):
        """Test styling commits ahead status with simple 'No' format."""
        result = self.service._style_commits_ahead_status("None")
        assert result == "[red]No[/red]"

    def test_style_commits_ahead_status_simple_yes(self):
        """Test styling commits ahead status with simple 'Yes' format."""
        result = self.service._style_commits_ahead_status("Unknown")
        assert result == "[green]Yes[/green]"

    def test_style_commits_ahead_display_simple_no(self):
        """Test styling commits ahead display with simple 'No' format."""
        result = self.service._style_commits_ahead_display("No commits ahead")
        assert result == "[red]No[/red]"

    def test_style_commits_ahead_display_simple_yes(self):
        """Test styling commits ahead display with simple 'Yes' format."""
        result = self.service._style_commits_ahead_display("Has commits")
        assert result == "[green]Yes[/green]"

    def test_format_fork_url(self):
        """Test formatting fork URL for GitHub."""
        result = self.service._format_fork_url("testowner", "testrepo")
        assert result == "https://github.com/testowner/testrepo"

    def test_format_fork_url_with_special_characters(self):
        """Test formatting fork URL with special characters."""
        result = self.service._format_fork_url("test-owner", "test.repo")
        assert result == "https://github.com/test-owner/test.repo"

    @pytest.mark.asyncio
    async def test_display_fork_data_table_simplified_columns(self):
        """Test that fork data table uses detailed format with URL, Stars, Forks, Commits Ahead, Last Push columns."""
        from datetime import UTC, datetime

        from forklift.models.fork_qualification import (
            CollectedForkData,
            ForkQualificationMetrics,
            QualificationStats,
            QualifiedForksResult,
        )

        # Create test fork data
        metrics = ForkQualificationMetrics(
            id=123,
            name="testrepo",
            owner="testowner",
            full_name="testowner/testrepo",
            html_url="https://github.com/testowner/testrepo",
            stargazers_count=10,
            forks_count=5,
            size=1000,
            language="Python",
            archived=False,
            disabled=False,
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 12, 1, tzinfo=UTC),
            pushed_at=datetime(2023, 12, 1, tzinfo=UTC),
        )

        fork_data = CollectedForkData(
            metrics=metrics, activity_summary="Active fork with recent commits"
        )

        stats = QualificationStats(
            total_forks_discovered=1,
            forks_with_commits=1,
            forks_with_no_commits=0,
            archived_forks=0,
            disabled_forks=0,
            analysis_candidate_percentage=100.0,
            skip_rate_percentage=0.0,
        )

        qualification_result = QualifiedForksResult(
            repository_owner="testowner",
            repository_name="testrepo",
            repository_url="https://github.com/testowner/testrepo",
            collected_forks=[fork_data],
            stats=stats,
        )

        # Call method
        await self.service._display_fork_data_table(qualification_result)

        # Verify console.print was called multiple times
        assert (
            self.mock_console.print.call_count >= 3
        )  # Summary table + fork table + insights

        # Check that the table was created and printed
        # We can't easily inspect the Rich Table structure, but we can verify the method completed
        # without errors and that console.print was called appropriately

    @pytest.mark.asyncio
    async def test_show_repository_details_success(self):
        """Test successful repository details display."""
        # Setup mock repository
        mock_repo = Repository(
            id=123,
            owner="testowner",
            name="testrepo",
            full_name="testowner/testrepo",
            url="https://api.github.com/repos/testowner/testrepo",
            html_url="https://github.com/testowner/testrepo",
            clone_url="https://github.com/testowner/testrepo.git",
            default_branch="main",
            stars=100,
            forks_count=50,
            description="Test repository",
            language="Python",
            license_name="MIT License",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 12, 1, tzinfo=UTC),
            pushed_at=datetime(2023, 12, 1, tzinfo=UTC),
        )

        # Setup mock responses
        self.mock_github_client.get_repository = AsyncMock(return_value=mock_repo)
        self.mock_github_client.get_repository_languages = AsyncMock(
            return_value={"Python": 1000, "JavaScript": 500}
        )
        self.mock_github_client.get_repository_topics = AsyncMock(
            return_value=["python", "web", "api"]
        )

        # Call method
        result = await self.service.show_repository_details("testowner/testrepo")

        # Verify calls
        self.mock_github_client.get_repository.assert_called_once_with(
            "testowner", "testrepo"
        )
        self.mock_github_client.get_repository_languages.assert_called_once_with(
            "testowner", "testrepo"
        )
        self.mock_github_client.get_repository_topics.assert_called_once_with(
            "testowner", "testrepo"
        )

        # Verify result
        assert result["repository"] == mock_repo
        assert result["languages"] == {"Python": 1000, "JavaScript": 500}
        assert result["topics"] == ["python", "web", "api"]
        assert result["primary_language"] == "Python"
        assert result["license"] == "MIT License"

        # Verify console output was called
        self.mock_console.print.assert_called()

    @pytest.mark.asyncio
    async def test_show_repository_details_api_error(self):
        """Test repository details display with API error."""
        # Setup mock to raise error
        self.mock_github_client.get_repository = AsyncMock(
            side_effect=GitHubAPIError("Repository not found")
        )

        # Call method and expect exception
        with pytest.raises(GitHubAPIError):
            await self.service.show_repository_details("testowner/testrepo")

        # Verify error was logged to console
        self.mock_console.print.assert_called()
        error_call = self.mock_console.print.call_args[0][0]
        assert "[red]Error:" in error_call

    def test_display_repository_table(self):
        """Test repository table display formatting."""
        # Create test repository details
        mock_repo = Repository(
            id=123,
            owner="testowner",
            name="testrepo",
            full_name="testowner/testrepo",
            url="https://api.github.com/repos/testowner/testrepo",
            html_url="https://github.com/testowner/testrepo",
            clone_url="https://github.com/testowner/testrepo.git",
            default_branch="main",
            stars=100,
            forks_count=50,
            description="Test repository",
            language="Python",
        )

        repo_details = {
            "repository": mock_repo,
            "languages": {"Python": 1000, "JavaScript": 500},
            "topics": ["python", "web"],
            "primary_language": "Python",
            "license": "MIT License",
            "last_activity": "1 month ago",
            "created": "1 year ago",
            "updated": "1 week ago",
        }

        # Call method
        self.service._display_repository_table(repo_details)

        # Verify console.print was called multiple times (table + panels)
        assert self.mock_console.print.call_count >= 1

    def test_display_languages_panel(self):
        """Test languages panel display."""
        languages = {"Python": 1000, "JavaScript": 500, "HTML": 200}

        # Call method
        self.service._display_languages_panel(languages)

        # Verify console.print was called
        self.mock_console.print.assert_called_once()

    def test_display_languages_panel_empty(self):
        """Test languages panel display with empty languages."""
        languages = {}

        # Call method
        self.service._display_languages_panel(languages)

        # Verify console.print was not called
        self.mock_console.print.assert_not_called()

    def test_display_topics_panel(self):
        """Test topics panel display."""
        topics = ["python", "web", "api", "backend"]

        # Call method
        self.service._display_topics_panel(topics)

        # Verify console.print was called
        self.mock_console.print.assert_called_once()

    def test_display_topics_panel_empty(self):
        """Test topics panel display with empty topics."""
        topics = []

        # Call method
        self.service._display_topics_panel(topics)

        # Verify console.print was not called
        self.mock_console.print.assert_not_called()

    def test_display_forks_table_empty(self):
        """Test forks table display with no forks."""
        enhanced_forks = []

        # Call method
        self.service._display_forks_table(enhanced_forks)

        # Verify console.print was called with no forks message
        self.mock_console.print.assert_called_once()
        call_args = self.mock_console.print.call_args[0][0]
        assert call_args == "[yellow]No forks found.[/yellow]"

    def test_display_forks_table_with_forks(self):
        """Test forks table display with forks."""
        # Create mock fork data
        mock_fork = Repository(
            id=456,
            owner="user1",
            name="testrepo",
            full_name="user1/testrepo",
            url="https://api.github.com/repos/user1/testrepo",
            html_url="https://github.com/user1/testrepo",
            clone_url="https://github.com/user1/testrepo.git",
            default_branch="main",
            stars=10,
            forks_count=2,
            language="Python",
        )

        enhanced_forks = [
            {
                "fork": mock_fork,
                "commits_ahead": 5,
                "commits_behind": 2,
                "activity_status": "active",
                "last_activity": "1 week ago",
            }
        ]

        # Call method
        self.service._display_forks_table(enhanced_forks)

        # Verify console.print was called
        self.mock_console.print.assert_called()

    def test_display_forks_table_max_display_limit(self):
        """Test forks table display respects max display limit."""
        # Create many mock forks
        enhanced_forks = []
        for i in range(60):  # More than max_display=50
            mock_fork = Repository(
                id=i,
                owner=f"user{i}",
                name="testrepo",
                full_name=f"user{i}/testrepo",
                url=f"https://api.github.com/repos/user{i}/testrepo",
                html_url=f"https://github.com/user{i}/testrepo",
                clone_url=f"https://github.com/user{i}/testrepo.git",
                default_branch="main",
                stars=i,
                forks_count=0,
            )

            enhanced_forks.append(
                {
                    "fork": mock_fork,
                    "commits_ahead": 1,
                    "commits_behind": 0,
                    "activity_status": "active",
                    "last_activity": "1 week ago",
                }
            )

        # Call method
        self.service._display_forks_table(enhanced_forks, max_display=50)

        # Verify console.print was called multiple times (table + overflow message)
        assert self.mock_console.print.call_count >= 2

        # Check that overflow message was printed
        calls = [call[0][0] for call in self.mock_console.print.call_args_list]
        overflow_messages = [
            call
            for call in calls
            if "... and" in str(call) and "more forks" in str(call)
        ]
        assert len(overflow_messages) > 0

    @pytest.mark.asyncio
    async def test_show_promising_forks_success(self):
        """Test successful promising forks display."""
        from forklift.models.filters import PromisingForksFilter

        # Setup mock forks data (reuse from show_forks_summary test)
        mock_fork1 = Repository(
            id=456,
            owner="user1",
            name="testrepo",
            full_name="user1/testrepo",
            url="https://api.github.com/repos/user1/testrepo",
            html_url="https://github.com/user1/testrepo",
            clone_url="https://github.com/user1/testrepo.git",
            default_branch="main",
            stars=10,
            forks_count=2,
            is_fork=True,
            is_archived=False,
            is_disabled=False,
            pushed_at=datetime.utcnow() - timedelta(days=30),  # 30 days ago
            created_at=datetime.utcnow() - timedelta(days=200),  # 200 days ago
        )

        mock_fork2 = Repository(
            id=789,
            owner="user2",
            name="testrepo",
            full_name="user2/testrepo",
            url="https://api.github.com/repos/user2/testrepo",
            html_url="https://github.com/user2/testrepo",
            clone_url="https://github.com/user2/testrepo.git",
            default_branch="main",
            stars=2,  # Below filter threshold
            forks_count=1,
            is_fork=True,
            is_archived=False,
            is_disabled=False,
            pushed_at=datetime.utcnow() - timedelta(days=60),  # 60 days ago
            created_at=datetime.utcnow() - timedelta(days=200),  # 200 days ago
        )

        # Mock the show_forks_summary method to return our test data
        _enhanced_forks = [
            {
                "fork": mock_fork1,
                "commits_ahead": 5,
                "commits_behind": 2,
                "activity_status": "moderate",
                "last_activity": "2 months ago",
            },
            {
                "fork": mock_fork2,
                "commits_ahead": 3,
                "commits_behind": 1,
                "activity_status": "stale",
                "last_activity": "3 months ago",
            },
        ]

        # Create filter that should match only the first fork
        filters = PromisingForksFilter(
            min_stars=5, min_commits_ahead=1  # Only fork1 has >= 5 stars
        )

        # Call method - should return empty result due to temporary disabling
        result = await self.service.show_promising_forks("testowner/testrepo", filters)

        # Verify result - temporarily disabled, so should return empty
        assert result["total_forks"] == 0
        assert result["promising_forks"] == 0
        assert len(result["forks"]) == 0

        # Verify console output was called (showing disabled message)
        self.mock_console.print.assert_called()

    @pytest.mark.asyncio
    async def test_show_promising_forks_no_matches(self):
        """Test promising forks display with no matches."""
        from forklift.models.filters import PromisingForksFilter

        # Setup mock fork that won't match strict criteria
        mock_fork = Repository(
            id=456,
            owner="user1",
            name="testrepo",
            full_name="user1/testrepo",
            url="https://api.github.com/repos/user1/testrepo",
            html_url="https://github.com/user1/testrepo",
            clone_url="https://github.com/user1/testrepo.git",
            default_branch="main",
            stars=2,  # Below threshold
            forks_count=1,
            is_fork=True,
            is_archived=False,
            is_disabled=False,
            pushed_at=datetime(2023, 10, 1, tzinfo=UTC),
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
        )

        _enhanced_forks = [
            {
                "fork": mock_fork,
                "commits_ahead": 1,
                "commits_behind": 0,
                "activity_status": "stale",
                "last_activity": "3 months ago",
            }
        ]

        # Create strict filter that won't match
        filters = PromisingForksFilter(
            min_stars=10,  # Fork only has 2 stars
            min_commits_ahead=5,  # Fork only has 1 commit ahead
        )

        # Call method - should return empty result due to temporary disabling
        result = await self.service.show_promising_forks("testowner/testrepo", filters)

        # Verify result - temporarily disabled, so should return empty
        assert result["total_forks"] == 0
        assert result["promising_forks"] == 0
        assert len(result["forks"]) == 0

        # Verify disabled message was displayed
        calls = [str(call[0][0]) for call in self.mock_console.print.call_args_list]
        disabled_messages = [call for call in calls if "temporarily disabled" in call]
        assert len(disabled_messages) > 0

    @pytest.mark.asyncio
    async def test_show_promising_forks_no_forks(self):
        """Test promising forks display with no forks at all."""
        from forklift.models.filters import PromisingForksFilter

        filters = PromisingForksFilter()

        # Call method - should return empty result due to temporary disabling
        result = await self.service.show_promising_forks("testowner/testrepo", filters)

        # Verify result - temporarily disabled, so should return empty
        assert result["total_forks"] == 0
        assert result["promising_forks"] == 0
        assert len(result["forks"]) == 0

        # Verify disabled message was displayed
        calls = [str(call[0][0]) for call in self.mock_console.print.call_args_list]
        disabled_messages = [call for call in calls if "temporarily disabled" in call]
        assert len(disabled_messages) > 0

    def test_display_promising_forks_table(self):
        """Test promising forks table display."""
        from forklift.models.filters import PromisingForksFilter

        # Create test fork data
        mock_fork = Repository(
            id=456,
            owner="user1",
            name="testrepo",
            full_name="user1/testrepo",
            url="https://api.github.com/repos/user1/testrepo",
            html_url="https://github.com/user1/testrepo",
            clone_url="https://github.com/user1/testrepo.git",
            default_branch="main",
            stars=10,
            forks_count=2,
            language="Python",
            pushed_at=datetime(2023, 11, 1, tzinfo=UTC),
        )

        promising_forks = [
            {
                "fork": mock_fork,
                "commits_ahead": 5,
                "commits_behind": 2,
                "activity_status": "active",
                "last_activity": "1 week ago",
            }
        ]

        filters = PromisingForksFilter()

        # Call method
        self.service._display_promising_forks_table(promising_forks, filters)

        # Verify console.print was called multiple times (filter criteria + table)
        assert self.mock_console.print.call_count >= 2

    def test_display_promising_forks_table_empty(self):
        """Test promising forks table display with no forks."""
        from forklift.models.filters import PromisingForksFilter

        filters = PromisingForksFilter()

        # Call method with empty list
        self.service._display_promising_forks_table([], filters)

        # Should not call console.print for empty forks (method returns early)
        self.mock_console.print.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_forks_preview_success(self):
        """Test successful forks preview display."""
        # Setup mock forks with created_at and pushed_at for activity detection
        base_time = datetime.utcnow().replace(tzinfo=UTC)

        mock_fork1 = Repository(
            id=456,
            owner="user1",
            name="testrepo",
            full_name="user1/testrepo",
            url="https://api.github.com/repos/user1/testrepo",
            html_url="https://github.com/user1/testrepo",
            clone_url="https://github.com/user1/testrepo.git",
            default_branch="main",
            stars=10,
            forks_count=2,
            is_fork=True,
            created_at=base_time - timedelta(days=200),  # Created 200 days ago
            pushed_at=base_time - timedelta(days=30),  # Last push 30 days ago (Active)
        )

        mock_fork2 = Repository(
            id=789,
            owner="user2",
            name="testrepo",
            full_name="user2/testrepo",
            url="https://api.github.com/repos/user2/testrepo",
            html_url="https://github.com/user2/testrepo",
            clone_url="https://github.com/user2/testrepo.git",
            default_branch="main",
            stars=5,
            forks_count=1,
            is_fork=True,
            created_at=base_time - timedelta(days=100),  # Created 100 days ago
            pushed_at=base_time - timedelta(days=100),  # Same as created (No commits)
        )

        # Setup mock response
        self.mock_github_client.get_repository_forks = AsyncMock(
            return_value=[mock_fork1, mock_fork2]
        )

        # Call method
        result = await self.service.list_forks_preview("testowner/testrepo")

        # Verify calls
        self.mock_github_client.get_repository_forks.assert_called_once_with(
            "testowner", "testrepo"
        )

        # Verify result structure
        assert result["total_forks"] == 2
        assert len(result["forks"]) == 2

        # Check that result contains fork items with activity status
        fork_items = result["forks"]
        assert all("activity_status" in item for item in fork_items)

        # Find the active fork (should be sorted first by stars)
        active_fork = next(item for item in fork_items if item["owner"] == "user1")
        assert active_fork["name"] == "testrepo"
        assert active_fork["owner"] == "user1"
        assert active_fork["stars"] == 10
        assert active_fork["activity_status"] == "Active"
        assert active_fork["fork_url"] == "https://github.com/user1/testrepo"

        # Find the no-commits fork
        no_commits_fork = next(item for item in fork_items if item["owner"] == "user2")
        assert no_commits_fork["activity_status"] == "No commits"

        # Verify console output was called
        self.mock_console.print.assert_called()

    @pytest.mark.asyncio
    async def test_list_forks_preview_no_forks(self):
        """Test forks preview display with no forks."""
        # Setup mock to return empty list
        self.mock_github_client.get_repository_forks = AsyncMock(return_value=[])

        # Call method
        result = await self.service.list_forks_preview("testowner/testrepo")

        # Verify result
        assert result["total_forks"] == 0
        assert result["forks"] == []

        # Verify console output
        self.mock_console.print.assert_called()
        no_forks_call = self.mock_console.print.call_args[0][0]
        assert "[yellow]No forks found" in no_forks_call

    @pytest.mark.asyncio
    async def test_list_forks_preview_api_error(self):
        """Test forks preview display with API error."""
        # Setup mock to raise error
        self.mock_github_client.get_repository_forks = AsyncMock(
            side_effect=GitHubAPIError("API error")
        )

        # Call method and expect exception
        with pytest.raises(GitHubAPIError):
            await self.service.list_forks_preview("testowner/testrepo")

        # Verify error was logged to console
        self.mock_console.print.assert_called()
        error_call = self.mock_console.print.call_args[0][0]
        assert "[red]Error:" in error_call

    @pytest.mark.asyncio
    async def test_list_forks_preview_sorting(self):
        """Test that forks preview results are sorted correctly."""
        base_time = datetime.utcnow().replace(tzinfo=UTC)

        # Setup mock forks with different stars and push dates
        mock_fork1 = Repository(
            id=456,
            owner="user1",
            name="testrepo",
            full_name="user1/testrepo",
            url="https://api.github.com/repos/user1/testrepo",
            html_url="https://github.com/user1/testrepo",
            clone_url="https://github.com/user1/testrepo.git",
            default_branch="main",
            stars=5,  # Lower stars
            forks_count=1,
            is_fork=True,
            created_at=base_time - timedelta(days=100),
            pushed_at=base_time - timedelta(days=30),  # More recent
        )

        mock_fork2 = Repository(
            id=789,
            owner="user2",
            name="testrepo",
            full_name="user2/testrepo",
            url="https://api.github.com/repos/user2/testrepo",
            html_url="https://github.com/user2/testrepo",
            clone_url="https://github.com/user2/testrepo.git",
            default_branch="main",
            stars=10,  # Higher stars
            forks_count=2,
            is_fork=True,
            created_at=base_time - timedelta(days=200),
            pushed_at=base_time - timedelta(days=60),  # Older
        )

        # Setup mock response (unsorted)
        self.mock_github_client.get_repository_forks = AsyncMock(
            return_value=[mock_fork1, mock_fork2]
        )

        # Call method
        result = await self.service.list_forks_preview("testowner/testrepo")

        # Verify sorting - fork2 should be first (higher stars)
        fork_items = result["forks"]
        assert fork_items[0]["owner"] == "user2"
        assert fork_items[0]["stars"] == 10
        assert fork_items[1]["owner"] == "user1"
        assert fork_items[1]["stars"] == 5

    def test_display_forks_preview_table(self):
        """Test forks preview table display formatting."""
        from datetime import datetime

        # Create test fork items with activity status and commits ahead
        fork_items = [
            {
                "name": "testrepo",
                "owner": "user1",
                "stars": 10,
                "last_push_date": datetime(2023, 11, 1, tzinfo=UTC),
                "fork_url": "https://github.com/user1/testrepo",
                "activity_status": "Active",
                "commits_ahead": "Unknown",
            },
            {
                "name": "testrepo",
                "owner": "user2",
                "stars": 5,
                "last_push_date": datetime(2023, 10, 1, tzinfo=UTC),
                "fork_url": "https://github.com/user2/testrepo",
                "activity_status": "No commits",
                "commits_ahead": "None",
            },
        ]

        # Call method
        self.service._display_forks_preview_table(fork_items)

        # Verify console.print was called
        self.mock_console.print.assert_called_once()

    def test_display_forks_preview_table_empty(self):
        """Test forks preview table display with no forks."""
        fork_items = []

        # Call method
        self.service._display_forks_preview_table(fork_items)

        # Verify console.print was called with no forks message
        self.mock_console.print.assert_called_once()
        call_args = self.mock_console.print.call_args[0][0]
        assert call_args == "[yellow]No forks found.[/yellow]"

    def test_get_commits_sort_key_with_integer_values(self):
        """Test commits sort key generation with integer commits ahead/behind values."""
        from forklift.models.fork_qualification import (
            CollectedForkData,
            ForkQualificationMetrics,
        )
        from datetime import datetime, UTC

        # Create fork data with integer commit values
        metrics = ForkQualificationMetrics(
            id=123,
            name="testrepo",
            owner="testowner",
            full_name="testowner/testrepo",
            html_url="https://github.com/testowner/testrepo",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 12, 1, tzinfo=UTC),
            pushed_at=datetime(2023, 12, 1, tzinfo=UTC),
        )

        fork_data = CollectedForkData(metrics=metrics)
        fork_data.exact_commits_ahead = 5
        fork_data.exact_commits_behind = 2

        # Call method
        sort_key = self.service._get_commits_sort_key(fork_data)

        # Verify sort key (positive values, reverse=True will be applied)
        assert sort_key == (5, 2)

    def test_get_commits_sort_key_with_unknown_status(self):
        """Test commits sort key generation with unknown commit status."""
        from forklift.models.fork_qualification import (
            CollectedForkData,
            ForkQualificationMetrics,
        )
        from datetime import datetime, UTC

        # Create fork data with unknown commit status
        metrics = ForkQualificationMetrics(
            id=123,
            name="testrepo",
            owner="testowner",
            full_name="testowner/testrepo",
            html_url="https://github.com/testowner/testrepo",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 12, 1, tzinfo=UTC),
            pushed_at=datetime(2023, 12, 1, tzinfo=UTC),
        )

        fork_data = CollectedForkData(metrics=metrics)
        fork_data.exact_commits_ahead = "Unknown"
        fork_data.exact_commits_behind = "Unknown"

        # Call method
        sort_key = self.service._get_commits_sort_key(fork_data)

        # Verify sort key (unknown gets high priority value)
        assert sort_key == (999, 0)

    def test_get_commits_sort_key_with_no_commits_ahead(self):
        """Test commits sort key generation with no commits ahead."""
        from forklift.models.fork_qualification import (
            CollectedForkData,
            ForkQualificationMetrics,
        )
        from datetime import datetime, UTC

        # Create fork data with no commits ahead
        metrics = ForkQualificationMetrics(
            id=123,
            name="testrepo",
            owner="testowner",
            full_name="testowner/testrepo",
            html_url="https://github.com/testowner/testrepo",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 12, 1, tzinfo=UTC),
            pushed_at=datetime(2023, 12, 1, tzinfo=UTC),
        )

        fork_data = CollectedForkData(metrics=metrics)
        fork_data.exact_commits_ahead = "None"
        fork_data.exact_commits_behind = 3

        # Call method
        sort_key = self.service._get_commits_sort_key(fork_data)

        # Verify sort key (no commits ahead gets 0 priority)
        assert sort_key == (0, 3)

    def test_get_commits_sort_key_with_none_values(self):
        """Test commits sort key generation with None values."""
        from forklift.models.fork_qualification import (
            CollectedForkData,
            ForkQualificationMetrics,
        )
        from datetime import datetime, UTC

        # Create fork data with None commit values
        metrics = ForkQualificationMetrics(
            id=123,
            name="testrepo",
            owner="testowner",
            full_name="testowner/testrepo",
            html_url="https://github.com/testowner/testrepo",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 12, 1, tzinfo=UTC),
            pushed_at=datetime(2023, 12, 1, tzinfo=UTC),
        )

        fork_data = CollectedForkData(metrics=metrics)
        # exact_commits_ahead and exact_commits_behind are None by default

        # Call method
        sort_key = self.service._get_commits_sort_key(fork_data)

        # Verify sort key (None values get treated as unknown)
        assert sort_key == (999, 0)

    def test_sort_forks_by_commits_with_compact_format(self):
        """Test sorting forks by commits using the new compact format."""
        from forklift.models.fork_qualification import (
            CollectedForkData,
            ForkQualificationMetrics,
        )
        from datetime import datetime, UTC

        # Create test fork data with different commit statuses
        base_time = datetime(2023, 1, 1, tzinfo=UTC)

        # Fork 1: 5 commits ahead, 2 behind
        metrics1 = ForkQualificationMetrics(
            id=1,
            name="repo1",
            owner="user1",
            full_name="user1/repo1",
            html_url="https://github.com/user1/repo1",
            created_at=base_time,
            updated_at=base_time,
            pushed_at=base_time,
        )
        fork1 = CollectedForkData(metrics=metrics1)
        fork1.exact_commits_ahead = 5
        fork1.exact_commits_behind = 2

        # Fork 2: 3 commits ahead, 1 behind
        metrics2 = ForkQualificationMetrics(
            id=2,
            name="repo2",
            owner="user2",
            full_name="user2/repo2",
            html_url="https://github.com/user2/repo2",
            created_at=base_time,
            updated_at=base_time,
            pushed_at=base_time,
        )
        fork2 = CollectedForkData(metrics=metrics2)
        fork2.exact_commits_ahead = 3
        fork2.exact_commits_behind = 1

        # Fork 3: Unknown status
        metrics3 = ForkQualificationMetrics(
            id=3,
            name="repo3",
            owner="user3",
            full_name="user3/repo3",
            html_url="https://github.com/user3/repo3",
            created_at=base_time,
            updated_at=base_time,
            pushed_at=base_time,
        )
        fork3 = CollectedForkData(metrics=metrics3)
        fork3.exact_commits_ahead = "Unknown"
        fork3.exact_commits_behind = "Unknown"

        # Fork 4: No commits ahead
        metrics4 = ForkQualificationMetrics(
            id=4,
            name="repo4",
            owner="user4",
            full_name="user4/repo4",
            html_url="https://github.com/user4/repo4",
            created_at=base_time,
            updated_at=base_time,
            pushed_at=base_time,
        )
        fork4 = CollectedForkData(metrics=metrics4)
        fork4.exact_commits_ahead = 0
        fork4.exact_commits_behind = 5

        collected_forks = [fork4, fork2, fork1, fork3]  # Unsorted order

        # Sort by commits
        sorted_forks = self.service._sort_forks(collected_forks, "commits")

        # Verify sorting order: Unknown (fork3), 5 ahead (fork1), 3 ahead (fork2), 0 ahead (fork4)
        assert sorted_forks[0].metrics.id == 3  # Unknown status first
        assert sorted_forks[1].metrics.id == 1  # 5 commits ahead
        assert sorted_forks[2].metrics.id == 2  # 3 commits ahead
        assert sorted_forks[3].metrics.id == 4  # 0 commits ahead

    def test_sort_forks_by_commits_secondary_sort_by_behind(self):
        """Test sorting forks by commits with secondary sort by commits behind."""
        from forklift.models.fork_qualification import (
            CollectedForkData,
            ForkQualificationMetrics,
        )
        from datetime import datetime, UTC

        # Create test fork data with same commits ahead but different commits behind
        base_time = datetime(2023, 1, 1, tzinfo=UTC)

        # Fork 1: 3 commits ahead, 5 behind
        metrics1 = ForkQualificationMetrics(
            id=1,
            name="repo1",
            owner="user1",
            full_name="user1/repo1",
            html_url="https://github.com/user1/repo1",
            created_at=base_time,
            updated_at=base_time,
            pushed_at=base_time,
        )
        fork1 = CollectedForkData(metrics=metrics1)
        fork1.exact_commits_ahead = 3
        fork1.exact_commits_behind = 5

        # Fork 2: 3 commits ahead, 2 behind
        metrics2 = ForkQualificationMetrics(
            id=2,
            name="repo2",
            owner="user2",
            full_name="user2/repo2",
            html_url="https://github.com/user2/repo2",
            created_at=base_time,
            updated_at=base_time,
            pushed_at=base_time,
        )
        fork2 = CollectedForkData(metrics=metrics2)
        fork2.exact_commits_ahead = 3
        fork2.exact_commits_behind = 2

        collected_forks = [fork1, fork2]  # Unsorted order

        # Sort by commits
        sorted_forks = self.service._sort_forks(collected_forks, "commits")

        # Verify secondary sorting by commits behind (higher behind count first)
        assert sorted_forks[0].metrics.id == 1  # 3 ahead, 5 behind
        assert sorted_forks[1].metrics.id == 2  # 3 ahead, 2 behind

    def test_sort_forks_enhanced_with_compact_format(self):
        """Test enhanced fork sorting with compact commit format support."""
        from forklift.models.fork_qualification import (
            CollectedForkData,
            ForkQualificationMetrics,
        )
        from datetime import datetime, UTC

        # Create test fork data with different characteristics
        base_time = datetime(2023, 1, 1, tzinfo=UTC)

        # Fork 1: Unknown commits, high stars
        metrics1 = ForkQualificationMetrics(
            id=1,
            name="repo1",
            owner="user1",
            full_name="user1/repo1",
            html_url="https://github.com/user1/repo1",
            stargazers_count=100,
            forks_count=20,
            created_at=base_time,
            updated_at=base_time,
            pushed_at=base_time,
        )
        fork1 = CollectedForkData(metrics=metrics1)
        fork1.exact_commits_ahead = "Unknown"

        # Fork 2: 5 commits ahead, low stars
        metrics2 = ForkQualificationMetrics(
            id=2,
            name="repo2",
            owner="user2",
            full_name="user2/repo2",
            html_url="https://github.com/user2/repo2",
            stargazers_count=10,
            forks_count=5,
            created_at=base_time,
            updated_at=base_time,
            pushed_at=base_time,
        )
        fork2 = CollectedForkData(metrics=metrics2)
        fork2.exact_commits_ahead = 5

        # Fork 3: No commits ahead, high stars
        metrics3 = ForkQualificationMetrics(
            id=3,
            name="repo3",
            owner="user3",
            full_name="user3/repo3",
            html_url="https://github.com/user3/repo3",
            stargazers_count=50,
            forks_count=15,
            created_at=base_time,
            updated_at=base_time,
            pushed_at=base_time,
        )
        fork3 = CollectedForkData(metrics=metrics3)
        fork3.exact_commits_ahead = 0

        collected_forks = [fork3, fork2, fork1]  # Unsorted order

        # Sort using enhanced method
        sorted_forks = self.service._sort_forks_enhanced(collected_forks)

        # Verify sorting order: commits first, then by stars
        # Unknown (fork1) and 5 ahead (fork2) should come before 0 ahead (fork3)
        # Between fork1 and fork2, fork1 should come first due to higher stars
        assert sorted_forks[0].metrics.id == 1  # Unknown commits, high stars
        assert sorted_forks[1].metrics.id == 2  # 5 commits ahead, low stars
        assert sorted_forks[2].metrics.id == 3  # 0 commits ahead, high stars

    def test_display_filter_criteria(self):
        """Test filter criteria display."""
        from forklift.models.filters import PromisingForksFilter

        filters = PromisingForksFilter(
            min_stars=5,
            min_commits_ahead=2,
            max_days_since_activity=180,
            min_activity_score=0.5,
            exclude_archived=True,
            exclude_disabled=True,
            min_fork_age_days=30,
            max_fork_age_days=365,
        )

        # Call method
        self.service._display_filter_criteria(filters)

        # Verify console.print was called
        self.mock_console.print.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_forks_preview_with_activity_detection(self):
        """Test list_forks_preview includes activity status in results."""
        base_time = datetime.utcnow().replace(tzinfo=UTC)

        # Create forks with different activity patterns
        active_fork = Repository(
            id=1,
            owner="active_user",
            name="testrepo",
            full_name="active_user/testrepo",
            url="https://api.github.com/repos/active_user/testrepo",
            html_url="https://github.com/active_user/testrepo",
            clone_url="https://github.com/active_user/testrepo.git",
            default_branch="main",
            stars=15,
            forks_count=3,
            is_fork=True,
            created_at=base_time - timedelta(days=100),  # Created 100 days ago
            pushed_at=base_time - timedelta(days=10),  # Last push 10 days ago (Active)
        )

        stale_fork = Repository(
            id=2,
            owner="stale_user",
            name="testrepo",
            full_name="stale_user/testrepo",
            url="https://api.github.com/repos/stale_user/testrepo",
            html_url="https://github.com/stale_user/testrepo",
            clone_url="https://github.com/stale_user/testrepo.git",
            default_branch="main",
            stars=8,
            forks_count=1,
            is_fork=True,
            created_at=base_time - timedelta(days=300),  # Created 300 days ago
            pushed_at=base_time - timedelta(days=200),  # Last push 200 days ago (Stale)
        )

        no_commits_fork = Repository(
            id=3,
            owner="no_commits_user",
            name="testrepo",
            full_name="no_commits_user/testrepo",
            url="https://api.github.com/repos/no_commits_user/testrepo",
            html_url="https://github.com/no_commits_user/testrepo",
            clone_url="https://github.com/no_commits_user/testrepo.git",
            default_branch="main",
            stars=2,
            forks_count=0,
            is_fork=True,
            created_at=base_time - timedelta(days=50),  # Created 50 days ago
            pushed_at=base_time - timedelta(days=50),  # Same as created (No commits)
        )

        # Setup mock response
        self.mock_github_client.get_repository_forks = AsyncMock(
            return_value=[active_fork, stale_fork, no_commits_fork]
        )

        # Call method
        result = await self.service.list_forks_preview("testowner/testrepo")

        # Verify result structure
        assert result["total_forks"] == 3
        assert len(result["forks"]) == 3

        # Verify all forks have activity status
        fork_items = result["forks"]
        for fork_item in fork_items:
            assert "activity_status" in fork_item
            assert fork_item["activity_status"] in ["Active", "Stale", "No commits"]

        # Find specific forks and verify their activity status
        active_item = next(
            item for item in fork_items if item["owner"] == "active_user"
        )
        assert active_item["activity_status"] == "Active"

        stale_item = next(item for item in fork_items if item["owner"] == "stale_user")
        assert stale_item["activity_status"] == "Stale"

        no_commits_item = next(
            item for item in fork_items if item["owner"] == "no_commits_user"
        )
        assert no_commits_item["activity_status"] == "No commits"

    def test_display_forks_preview_table_with_activity_column(self):
        """Test that forks preview table includes Activity column with proper styling."""
        # Create test fork items with different activity statuses and commits ahead
        fork_items = [
            {
                "name": "active_repo",
                "owner": "active_user",
                "stars": 10,
                "last_push_date": datetime(2023, 11, 1, tzinfo=UTC),
                "fork_url": "https://github.com/active_user/active_repo",
                "activity_status": "Active",
                "commits_ahead": "Unknown",
            },
            {
                "name": "stale_repo",
                "owner": "stale_user",
                "stars": 5,
                "last_push_date": datetime(2023, 6, 1, tzinfo=UTC),
                "fork_url": "https://github.com/stale_user/stale_repo",
                "activity_status": "Stale",
                "commits_ahead": "Unknown",
            },
            {
                "name": "no_commits_repo",
                "owner": "no_commits_user",
                "stars": 1,
                "last_push_date": datetime(2023, 1, 1, tzinfo=UTC),
                "fork_url": "https://github.com/no_commits_user/no_commits_repo",
                "activity_status": "No commits",
                "commits_ahead": "None",
            },
        ]

        # Call method
        self.service._display_forks_preview_table(fork_items)

        # Verify console.print was called
        self.mock_console.print.assert_called_once()

    def test_calculate_commits_ahead_status(self):
        """Test commits ahead status calculation using corrected logic."""
        from datetime import datetime

        from forklift.models.github import Repository

        # Test case 1: created_at == pushed_at (no commits)
        fork1 = Repository(
            id=1,
            name="test-repo",
            full_name="user/test-repo",
            owner="user",
            url="https://api.github.com/repos/user/test-repo",
            html_url="https://github.com/user/test-repo",
            clone_url="https://github.com/user/test-repo.git",
            created_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
            pushed_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
        )

        # Test case 2: created_at > pushed_at (fork created after last push)
        fork2 = Repository(
            id=2,
            name="test-repo",
            full_name="user2/test-repo",
            owner="user2",
            url="https://api.github.com/repos/user2/test-repo",
            html_url="https://github.com/user2/test-repo",
            clone_url="https://github.com/user2/test-repo.git",
            created_at=datetime(2023, 2, 1, 12, 0, 0, tzinfo=UTC),
            pushed_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2023, 2, 1, 12, 0, 0, tzinfo=UTC),
        )

        # Test case 3: pushed_at > created_at (potentially has commits)
        fork3 = Repository(
            id=3,
            name="test-repo",
            full_name="user3/test-repo",
            owner="user3",
            url="https://api.github.com/repos/user3/test-repo",
            html_url="https://github.com/user3/test-repo",
            clone_url="https://github.com/user3/test-repo.git",
            created_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
            pushed_at=datetime(2023, 2, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2023, 2, 1, 12, 0, 0, tzinfo=UTC),
        )

        # Test case 4: Missing timestamps
        fork4 = Repository(
            id=4,
            name="test-repo",
            full_name="user4/test-repo",
            owner="user4",
            url="https://api.github.com/repos/user4/test-repo",
            html_url="https://github.com/user4/test-repo",
            clone_url="https://github.com/user4/test-repo.git",
            created_at=None,
            pushed_at=None,
            updated_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
        )

        # Test the logic
        assert self.service._calculate_commits_ahead_status(fork1) == "None"
        assert self.service._calculate_commits_ahead_status(fork2) == "None"
        assert self.service._calculate_commits_ahead_status(fork3) == "Unknown"
        assert self.service._calculate_commits_ahead_status(fork4) == "None"

    def test_style_commits_ahead_status(self):
        """Test commits ahead status styling with simple format."""
        # Test styling for different statuses - now uses simple Yes/No format
        assert self.service._style_commits_ahead_status("None") == "[red]No[/red]"
        assert (
            self.service._style_commits_ahead_status("Unknown") == "[green]Yes[/green]"
        )
        assert (
            self.service._style_commits_ahead_status("Invalid") == "Unknown"
        )  # Unknown status returns as "Unknown"

    @pytest.mark.asyncio
    async def test_list_forks_preview_activity_edge_cases(self):
        """Test activity detection edge cases."""
        base_time = datetime.utcnow().replace(tzinfo=UTC)

        # Fork with missing created_at
        missing_created_fork = Repository(
            id=1,
            owner="missing_created",
            name="testrepo",
            full_name="missing_created/testrepo",
            url="https://api.github.com/repos/missing_created/testrepo",
            html_url="https://github.com/missing_created/testrepo",
            clone_url="https://github.com/missing_created/testrepo.git",
            default_branch="main",
            stars=5,
            forks_count=1,
            is_fork=True,
            created_at=None,  # Missing created_at
            pushed_at=base_time - timedelta(days=10),
        )

        # Fork with missing pushed_at
        missing_pushed_fork = Repository(
            id=2,
            owner="missing_pushed",
            name="testrepo",
            full_name="missing_pushed/testrepo",
            url="https://api.github.com/repos/missing_pushed/testrepo",
            html_url="https://github.com/missing_pushed/testrepo",
            clone_url="https://github.com/missing_pushed/testrepo.git",
            default_branch="main",
            stars=3,
            forks_count=0,
            is_fork=True,
            created_at=base_time - timedelta(days=50),
            pushed_at=None,  # Missing pushed_at
        )

        # Fork with pushed_at within 1 minute of created_at
        within_minute_fork = Repository(
            id=3,
            owner="within_minute",
            name="testrepo",
            full_name="within_minute/testrepo",
            url="https://api.github.com/repos/within_minute/testrepo",
            html_url="https://github.com/within_minute/testrepo",
            clone_url="https://github.com/within_minute/testrepo.git",
            default_branch="main",
            stars=7,
            forks_count=2,
            is_fork=True,
            created_at=base_time - timedelta(days=30),
            pushed_at=base_time
            - timedelta(days=30)
            + timedelta(seconds=30),  # 30 seconds after created
        )

        # Setup mock response
        self.mock_github_client.get_repository_forks = AsyncMock(
            return_value=[missing_created_fork, missing_pushed_fork, within_minute_fork]
        )

        # Call method
        result = await self.service.list_forks_preview("testowner/testrepo")

        # Verify all edge cases are handled
        fork_items = result["forks"]

        missing_created_item = next(
            item for item in fork_items if item["owner"] == "missing_created"
        )
        assert missing_created_item["activity_status"] == "No commits"

        missing_pushed_item = next(
            item for item in fork_items if item["owner"] == "missing_pushed"
        )
        assert missing_pushed_item["activity_status"] == "No commits"

        within_minute_item = next(
            item for item in fork_items if item["owner"] == "within_minute"
        )
        assert within_minute_item["activity_status"] == "No commits"

    def test_format_recent_commits_empty_list(self):
        """Test formatting empty commits list."""
        result = self.service.format_recent_commits([])
        assert result == "[dim]No commits[/dim]"

    def test_format_recent_commits_single_commit(self):
        """Test formatting single commit with date."""
        from forklift.models.github import RecentCommit
        from datetime import datetime

        commit = RecentCommit(
            short_sha="abc1234",
            message="Fix bug in parser",
            date=datetime(2024, 1, 15, 10, 30),
        )
        result = self.service.format_recent_commits([commit])
        assert result == "2024-01-15 abc1234 Fix bug in parser"

    def test_format_recent_commits_single_commit_no_date(self):
        """Test formatting single commit without date (fallback to old format)."""
        from forklift.models.github import RecentCommit

        commit = RecentCommit(short_sha="abc1234", message="Fix bug in parser")
        result = self.service.format_recent_commits([commit])
        assert result == "abc1234: Fix bug in parser"

    def test_format_recent_commits_multiple_commits(self):
        """Test formatting multiple commits with dates."""
        from forklift.models.github import RecentCommit
        from datetime import datetime

        commits = [
            RecentCommit(
                short_sha="abc1234",
                message="Fix bug in parser",
                date=datetime(2024, 1, 15, 10, 30),
            ),
            RecentCommit(
                short_sha="def5678",
                message="Add new feature",
                date=datetime(2024, 1, 14, 9, 15),
            ),
            RecentCommit(
                short_sha="9012abc", message="Update documentation"
            ),  # No date
        ]
        result = self.service.format_recent_commits(commits)
        expected = "2024-01-15 abc1234 Fix bug in parser\n2024-01-14 def5678 Add new feature\n9012abc: Update documentation"
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_and_format_commits_ahead_success(self):
        """Test successful commits ahead fetching and formatting."""
        from forklift.models.github import RecentCommit
        from datetime import datetime

        # Setup mock commits with dates
        mock_commits = [
            RecentCommit(
                short_sha="abc1234",
                message="Fix bug",
                date=datetime(2024, 1, 15, 10, 30),
            ),
            RecentCommit(
                short_sha="def5678",
                message="Add feature",
                date=datetime(2024, 1, 14, 9, 15),
            ),
        ]

        self.mock_github_client.get_commits_ahead = AsyncMock(return_value=mock_commits)

        result = await self.service._get_and_format_commits_ahead(
            "fork_owner", "fork_repo", "base_owner", "base_repo", 2
        )

        expected = "2024-01-15 abc1234 Fix bug\n2024-01-14 def5678 Add feature"
        assert result == expected
        self.mock_github_client.get_commits_ahead.assert_called_once_with(
            "fork_owner", "fork_repo", "base_owner", "base_repo", count=2
        )

    @pytest.mark.asyncio
    async def test_get_and_format_commits_ahead_api_error(self):
        """Test commits ahead fetching with API error."""
        from forklift.github.client import GitHubAPIError

        self.mock_github_client.get_commits_ahead = AsyncMock(
            side_effect=GitHubAPIError("API error")
        )

        result = await self.service._get_and_format_commits_ahead(
            "fork_owner", "fork_repo", "base_owner", "base_repo", 2
        )

        assert result == "[dim]No commits available[/dim]"
        self.mock_github_client.get_commits_ahead.assert_called_once_with(
            "fork_owner", "fork_repo", "base_owner", "base_repo", count=2
        )

    def test_format_commits_status_both_zero(self):
        """Test format_commits_status with both ahead and behind as zero."""
        result = self.service.format_commits_status(0, 0)
        assert result == "+0 -0"

    def test_format_commits_status_ahead_only(self):
        """Test format_commits_status with commits ahead only."""
        result = self.service.format_commits_status(5, 0)
        assert result == "+5 -0"

    def test_format_commits_status_behind_only(self):
        """Test format_commits_status with commits behind only."""
        result = self.service.format_commits_status(0, 3)
        assert result == "+0 -3"

    def test_format_commits_status_both_nonzero(self):
        """Test format_commits_status with both ahead and behind non-zero."""
        result = self.service.format_commits_status(7, 2)
        assert result == "+7 -2"

    def test_format_commits_status_large_numbers(self):
        """Test format_commits_status with large numbers."""
        result = self.service.format_commits_status(123, 456)
        assert result == "+123 -456"

    def test_format_commits_compact_both_zero(self):
        """Test format_commits_compact with both ahead and behind as zero (empty cell)."""
        result = self.service.format_commits_compact(0, 0)
        assert result == ""

    def test_format_commits_compact_ahead_only(self):
        """Test format_commits_compact with commits ahead only."""
        result = self.service.format_commits_compact(5, 0)
        assert result == "[green]+5[/green]"

    def test_format_commits_compact_behind_only(self):
        """Test format_commits_compact with commits behind only."""
        result = self.service.format_commits_compact(0, 3)
        assert result == "[red]-3[/red]"

    def test_format_commits_compact_both_nonzero(self):
        """Test format_commits_compact with both ahead and behind non-zero."""
        result = self.service.format_commits_compact(7, 2)
        assert result == "[green]+7[/green] [red]-2[/red]"

    def test_format_commits_compact_unknown_ahead(self):
        """Test format_commits_compact with unknown commits ahead (-1)."""
        result = self.service.format_commits_compact(-1, 0)
        assert result == "Unknown"

    def test_format_commits_compact_unknown_behind(self):
        """Test format_commits_compact with unknown commits behind (-1)."""
        result = self.service.format_commits_compact(0, -1)
        assert result == "Unknown"

    def test_format_commits_compact_both_unknown(self):
        """Test format_commits_compact with both ahead and behind unknown (-1)."""
        result = self.service.format_commits_compact(-1, -1)
        assert result == "Unknown"

    def test_format_commits_compact_large_numbers(self):
        """Test format_commits_compact with large numbers."""
        result = self.service.format_commits_compact(123, 456)
        assert result == "[green]+123[/green] [red]-456[/red]"

    def test_format_commits_compact_single_ahead(self):
        """Test format_commits_compact with single commit ahead."""
        result = self.service.format_commits_compact(1, 0)
        assert result == "[green]+1[/green]"

    def test_format_commits_compact_single_behind(self):
        """Test format_commits_compact with single commit behind."""
        result = self.service.format_commits_compact(0, 1)
        assert result == "[red]-1[/red]"

    def test_format_commits_compact_edge_case_mixed_unknown(self):
        """Test format_commits_compact with mixed unknown values."""
        result = self.service.format_commits_compact(5, -1)
        assert result == "Unknown"

    # Tests for improved Recent Commits column formatting (Task 22.4)

    def test_format_commit_date_consistent_format(self):
        """Test _format_commit_date returns consistent YYYY-MM-DD format."""
        from datetime import datetime

        test_date = datetime(2024, 1, 15, 10, 30, 45)
        result = self.service._format_commit_date(test_date)
        assert result == "2024-01-15"

    def test_format_commit_date_different_months(self):
        """Test _format_commit_date with different months."""
        from datetime import datetime

        # Test single digit month
        test_date = datetime(2024, 3, 5)
        result = self.service._format_commit_date(test_date)
        assert result == "2024-03-05"

        # Test double digit month
        test_date = datetime(2024, 12, 25)
        result = self.service._format_commit_date(test_date)
        assert result == "2024-12-25"

    def test_sort_commits_chronologically_newest_first(self):
        """Test _sort_commits_chronologically sorts newest first."""
        from forklift.models.github import RecentCommit
        from datetime import datetime

        commits = [
            RecentCommit(
                short_sha="abc1234",
                message="Older commit",
                date=datetime(2024, 1, 10, 10, 0),
            ),
            RecentCommit(
                short_sha="def5678",
                message="Newer commit",
                date=datetime(2024, 1, 15, 10, 0),
            ),
            RecentCommit(
                short_sha="1234567",
                message="Oldest commit",
                date=datetime(2024, 1, 5, 10, 0),
            ),
        ]

        result = self.service._sort_commits_chronologically(commits)

        # Should be sorted newest first
        assert result[0].message == "Newer commit"
        assert result[1].message == "Older commit"
        assert result[2].message == "Oldest commit"

    def test_sort_commits_chronologically_with_none_dates(self):
        """Test _sort_commits_chronologically handles None dates correctly."""
        from forklift.models.github import RecentCommit
        from datetime import datetime

        commits = [
            RecentCommit(short_sha="abc1234", message="No date commit"),  # No date
            RecentCommit(
                short_sha="def5678",
                message="With date commit",
                date=datetime(2024, 1, 15, 10, 0),
            ),
            RecentCommit(short_sha="1234567", message="Another no date"),  # No date
        ]

        result = self.service._sort_commits_chronologically(commits)

        # Commits with dates should come first, then commits without dates
        assert result[0].message == "With date commit"
        assert result[1].message == "No date commit"
        assert result[2].message == "Another no date"

    def test_truncate_commit_message_no_truncation_needed(self):
        """Test _truncate_commit_message when message fits within limit."""
        message = "Short message"
        result = self.service._truncate_commit_message(message, 50)
        assert result == "Short message"

    def test_truncate_commit_message_empty_message(self):
        """Test _truncate_commit_message with empty message."""
        result = self.service._truncate_commit_message("", 50)
        assert result == ""

    def test_truncate_commit_message_at_word_boundary(self):
        """Test _truncate_commit_message truncates at word boundary when possible."""
        message = "This is a very long commit message that needs truncation"
        result = self.service._truncate_commit_message(message, 25)

        # Should truncate at word boundary and add ellipsis
        assert result.endswith("...")
        assert len(result) <= 25
        # Should not break words if possible
        assert not result.replace("...", "").endswith("ver")  # Shouldn't break "very"

    def test_truncate_commit_message_no_good_break_point(self):
        """Test _truncate_commit_message when no good word boundary exists."""
        message = "Verylongwordwithoutspaces"
        result = self.service._truncate_commit_message(message, 15)

        assert result.endswith("...")
        assert len(result) == 15

    def test_truncate_commit_message_very_short_limit(self):
        """Test _truncate_commit_message with very short max_length."""
        message = "Long message"
        result = self.service._truncate_commit_message(message, 3)

        assert len(result) == 3
        assert result == "Lon"  # No ellipsis for very short limits

    def test_truncate_commit_message_preserves_readability(self):
        """Test _truncate_commit_message preserves readability by avoiding mid-word breaks."""
        message = "Fix critical bug in authentication system"
        result = self.service._truncate_commit_message(message, 20)

        # Should find a good break point
        assert result.endswith("...")
        assert len(result) <= 20
        # Should break at a space, not mid-word
        words_in_result = result.replace("...", "").strip().split()
        # Last word should be complete (not broken)
        if words_in_result:
            last_word = words_in_result[-1]
            assert last_word in message  # Last word should exist completely in original

    def test_calculate_commits_column_width_empty_data(self):
        """Test calculate_commits_column_width with empty commits data."""
        result = self.service.calculate_commits_column_width({}, 3)
        assert result == 30  # Should return min_width

    def test_calculate_commits_column_width_zero_show_commits(self):
        """Test calculate_commits_column_width with zero show_commits."""
        commits_data = {"fork1": []}
        result = self.service.calculate_commits_column_width(commits_data, 0)
        assert result == 30  # Should return min_width

    def test_calculate_commits_column_width_with_commits(self):
        """Test calculate_commits_column_width calculates appropriate width."""
        from forklift.models.github import RecentCommit
        from datetime import datetime

        commits = [
            RecentCommit(
                short_sha="abc1234",
                message="Short msg",
                date=datetime(2024, 1, 15),
            ),
            RecentCommit(
                short_sha="def5678",
                message="This is a much longer commit message that needs more space",
                date=datetime(2024, 1, 14),
            ),
        ]

        commits_data = {"fork1": commits}
        result = self.service.calculate_commits_column_width(
            commits_data, 2, min_width=30, max_width=80
        )

        # Should be between min and max, accounting for content
        assert 30 <= result <= 80
        # Should be reasonable for the content (not just min_width)
        assert result > 30

    def test_calculate_commits_column_width_respects_bounds(self):
        """Test calculate_commits_column_width respects min/max bounds."""
        from forklift.models.github import RecentCommit
        from datetime import datetime

        # Very long message that would exceed max_width
        long_message = "This is an extremely long commit message " * 5
        commits = [
            RecentCommit(
                short_sha="abc1234",
                message=long_message,
                date=datetime(2024, 1, 15),
            ),
        ]

        commits_data = {"fork1": commits}
        result = self.service.calculate_commits_column_width(
            commits_data, 1, min_width=30, max_width=60
        )

        # Should not exceed max_width
        assert result <= 60

    def test_format_recent_commits_improved_formatting(self):
        """Test format_recent_commits uses improved formatting with consistent dates."""
        from forklift.models.github import RecentCommit
        from datetime import datetime

        commits = [
            RecentCommit(
                short_sha="abc1234",
                message="Fix authentication bug",
                date=datetime(2024, 1, 15, 10, 30),
            ),
            RecentCommit(
                short_sha="def5678",
                message="Add new feature for users",
                date=datetime(2024, 1, 14, 9, 15),
            ),
        ]

        result = self.service.format_recent_commits(commits, column_width=50)

        # Should use YYYY-MM-DD format and be chronologically ordered (newest first)
        lines = result.split("\n")
        assert len(lines) == 2
        assert lines[0].startswith("2024-01-15 abc1234")
        assert lines[1].startswith("2024-01-14 def5678")
        assert "Fix authentication bug" in lines[0]
        assert "Add new feature for users" in lines[1]

    def test_format_recent_commits_handles_long_messages(self):
        """Test format_recent_commits properly truncates long commit messages."""
        from forklift.models.github import RecentCommit
        from datetime import datetime

        long_message = "This is a very long commit message that should be truncated to fit within the column width constraints"
        commits = [
            RecentCommit(
                short_sha="abc1234",
                message=long_message,
                date=datetime(2024, 1, 15),
            ),
        ]

        result = self.service.format_recent_commits(commits, column_width=40)

        # Should be truncated to fit within column width
        lines = result.split("\n")
        assert len(lines) == 1
        # Total line length should be reasonable for the column width
        assert len(lines[0]) <= 40
        # Should contain ellipsis if truncated
        if len(long_message) > (40 - 19):  # 19 is base width for date and hash
            assert "..." in lines[0]

    def test_format_recent_commits_mixed_date_availability(self):
        """Test format_recent_commits handles mixed date availability correctly."""
        from forklift.models.github import RecentCommit
        from datetime import datetime

        commits = [
            RecentCommit(
                short_sha="abc1234",
                message="With date",
                date=datetime(2024, 1, 15),
            ),
            RecentCommit(
                short_sha="def5678",
                message="Without date",
            ),  # No date
        ]

        result = self.service.format_recent_commits(commits, column_width=50)

        lines = result.split("\n")
        assert len(lines) == 2
        # First line (with date) should use new format
        assert lines[0].startswith("2024-01-15 abc1234")
        # Second line (without date) should use fallback format
        assert lines[1].startswith("def5678:")
        assert "Without date" in lines[1]
    def test_display_fork_insights_excluded_by_default(self):
        """Test that fork insights section is excluded by default."""
        from unittest.mock import Mock, patch
        
        # Create service with default configuration (should exclude fork insights)
        service = RepositoryDisplayService(self.mock_github_client, self.mock_console)
        
        # Verify the configuration flag is set correctly
        assert service._should_exclude_fork_insights is True

    def test_display_fork_insights_included_when_enabled(self):
        """Test that fork insights section is included when enabled."""
        from unittest.mock import Mock
        
        # Create service with fork insights enabled
        service = RepositoryDisplayService(
            self.mock_github_client, 
            self.mock_console,
            should_exclude_fork_insights=False
        )
        
        # Verify the configuration flag is set correctly
        assert service._should_exclude_fork_insights is False

    def test_display_language_distribution_excluded_by_default(self):
        """Test that language distribution table is excluded by default."""
        from unittest.mock import Mock
        
        # Create service with default configuration (should exclude language distribution)
        service = RepositoryDisplayService(self.mock_github_client, self.mock_console)
        
        # Verify the configuration flag is set correctly
        assert service._should_exclude_language_distribution is True

    def test_display_language_distribution_included_when_enabled(self):
        """Test that language distribution table is included when enabled."""
        from unittest.mock import Mock
        
        # Create service with language distribution enabled
        service = RepositoryDisplayService(
            self.mock_github_client, 
            self.mock_console,
            should_exclude_language_distribution=False
        )
        
        # Verify the configuration flag is set correctly
        assert service._should_exclude_language_distribution is False

    @pytest.mark.asyncio
    async def test_display_fork_data_table_excludes_fork_insights_by_default(self):
        """Test that _display_fork_data_table excludes fork insights section by default."""
        from unittest.mock import Mock, AsyncMock, patch
        
        # Create service with default configuration
        service = RepositoryDisplayService(self.mock_github_client, self.mock_console)
        
        # Mock qualification result
        mock_stats = Mock()
        mock_stats.total_forks_discovered = 10
        mock_stats.forks_with_commits = 5
        mock_stats.forks_with_no_commits = 5
        mock_stats.analysis_candidate_percentage = 50.0
        mock_stats.skip_rate_percentage = 50.0
        mock_stats.archived_forks = 0
        mock_stats.disabled_forks = 0
        
        mock_qualification_result = Mock()
        mock_qualification_result.repository_owner = "test_owner"
        mock_qualification_result.repository_name = "test_repo"
        mock_qualification_result.stats = mock_stats
        mock_qualification_result.collected_forks = []
        
        # Mock the _display_fork_insights method to track if it's called
        with patch.object(service, '_display_fork_insights') as mock_display_insights:
            await service._display_fork_data_table(mock_qualification_result)
            
            # Should not call _display_fork_insights
            mock_display_insights.assert_not_called()

    @pytest.mark.asyncio
    async def test_display_fork_data_table_includes_fork_insights_when_enabled(self):
        """Test that _display_fork_data_table includes fork insights section when enabled."""
        from unittest.mock import Mock, AsyncMock, patch
        
        # Create service with fork insights enabled
        service = RepositoryDisplayService(
            self.mock_github_client, 
            self.mock_console,
            should_exclude_fork_insights=False
        )
        
        # Mock qualification result
        mock_stats = Mock()
        mock_stats.total_forks_discovered = 10
        mock_stats.forks_with_commits = 5
        mock_stats.forks_with_no_commits = 5
        mock_stats.analysis_candidate_percentage = 50.0
        mock_stats.skip_rate_percentage = 50.0
        mock_stats.archived_forks = 0
        mock_stats.disabled_forks = 0
        
        mock_qualification_result = Mock()
        mock_qualification_result.repository_owner = "test_owner"
        mock_qualification_result.repository_name = "test_repo"
        mock_qualification_result.stats = mock_stats
        # Add some mock fork data so the insights section is displayed
        mock_fork_data = Mock()
        mock_fork_data.metrics.owner = "test_owner"
        mock_fork_data.metrics.name = "test_repo"
        mock_fork_data.metrics.stargazers_count = 5
        mock_fork_data.metrics.forks_count = 2
        mock_fork_data.metrics.commits_ahead_status = "Unknown"
        mock_fork_data.metrics.pushed_at = None
        mock_qualification_result.collected_forks = [mock_fork_data]
        
        # Mock the _display_fork_insights method to track if it's called
        with patch.object(service, '_display_fork_insights') as mock_display_insights:
            await service._display_fork_data_table(mock_qualification_result)
            
            # Should call _display_fork_insights
            mock_display_insights.assert_called_once_with(mock_qualification_result)

    def test_display_fork_insights_shows_language_distribution_when_enabled(self):
        """Test that _display_fork_insights shows language distribution when enabled."""
        from unittest.mock import Mock
        
        # Create service with language distribution enabled
        service = RepositoryDisplayService(
            self.mock_github_client, 
            self.mock_console,
            should_exclude_language_distribution=False
        )
        
        # Mock qualification result with fork data that has languages
        mock_fork_data = Mock()
        mock_fork_data.metrics.language = "Python"
        
        mock_qualification_result = Mock()
        mock_qualification_result.active_forks = []
        mock_qualification_result.popular_forks = []
        mock_qualification_result.forks_needing_analysis = []
        mock_qualification_result.forks_to_skip = []
        mock_qualification_result.collected_forks = [mock_fork_data]
        
        # Call the method
        service._display_fork_insights(mock_qualification_result)
        
        # Should print Language Distribution section
        printed_calls = [call for call in self.mock_console.print.call_args_list]
        language_dist_calls = [call for call in printed_calls if "Language Distribution" in str(call)]
        assert len(language_dist_calls) > 0

    def test_display_fork_insights_hides_language_distribution_when_disabled(self):
        """Test that _display_fork_insights hides language distribution when disabled."""
        from unittest.mock import Mock
        
        # Create service with language distribution disabled (default)
        service = RepositoryDisplayService(
            self.mock_github_client, 
            self.mock_console,
            should_exclude_language_distribution=True
        )
        
        # Mock qualification result with fork data that has languages
        mock_fork_data = Mock()
        mock_fork_data.metrics.language = "Python"
        
        mock_qualification_result = Mock()
        mock_qualification_result.active_forks = []
        mock_qualification_result.popular_forks = []
        mock_qualification_result.forks_needing_analysis = []
        mock_qualification_result.forks_to_skip = []
        mock_qualification_result.collected_forks = [mock_fork_data]
        
        # Call the method
        service._display_fork_insights(mock_qualification_result)
        
        # Should not print Language Distribution section
        printed_calls = [call for call in self.mock_console.print.call_args_list]
        language_dist_calls = [call for call in printed_calls if "Language Distribution" in str(call)]
        assert len(language_dist_calls) == 0 

    def test_detailed_fork_table_recent_commits_column_no_wrap(self):
        """Test that Recent Commits column in detailed fork table has no_wrap=True to prevent soft wrapping."""
        from unittest.mock import Mock, patch
        from rich.table import Table
        
        # Create service
        service = RepositoryDisplayService(self.mock_github_client, self.mock_console)
        
        # Mock fork data with long commit messages
        mock_fork_data = Mock()
        mock_fork_data.metrics.owner = "test_owner"
        mock_fork_data.metrics.name = "test_repo"
        mock_fork_data.metrics.stargazers_count = 100
        mock_fork_data.metrics.forks_count = 50
        mock_fork_data.metrics.pushed_at = datetime.now(UTC)
        mock_fork_data.exact_commits_ahead = 5
        
        detailed_forks = [mock_fork_data]
        
        # Mock the commits cache to return long commit messages
        long_commit_message = "This is a very long commit message that would normally cause soft wrapping in table cells without proper configuration"
        commits_cache = {"test_owner/test_repo": long_commit_message}
        
        # Patch the _fetch_commits_concurrently method to return our mock cache
        with patch.object(service, '_fetch_commits_concurrently', return_value=commits_cache):
            # Patch Table to capture column configuration
            with patch('forklift.display.repository_display_service.Table') as mock_table_class:
                mock_table_instance = Mock()
                mock_table_class.return_value = mock_table_instance
                
                # Call the method with show_commits > 0 to trigger Recent Commits column
                asyncio.run(service._display_detailed_fork_table(
                    detailed_forks,
                    "base_owner",
                    "base_repo",
                    api_calls_made=0,
                    api_calls_saved=0,
                    show_commits=3,  # This should trigger Recent Commits column
                    force_all_commits=False
                ))
                
                # Verify that add_column was called with no_wrap=True for Recent Commits column
                add_column_calls = mock_table_instance.add_column.call_args_list
                
                # Find the Recent Commits column call
                recent_commits_call = None
                for call in add_column_calls:
                    args, kwargs = call
                    if args and "Recent Commits" in args[0]:
                        recent_commits_call = call
                        break
                
                # Verify the Recent Commits column was added with no_wrap=True
                assert recent_commits_call is not None, "Recent Commits column should be added when show_commits > 0"
                args, kwargs = recent_commits_call
                assert kwargs.get('no_wrap') is True, "Recent Commits column should have no_wrap=True to prevent soft wrapping"

    def test_detailed_fork_table_without_commits_no_recent_commits_column(self):
        """Test that Recent Commits column is not added when show_commits is 0."""
        from unittest.mock import Mock, patch
        from rich.table import Table
        
        # Create service
        service = RepositoryDisplayService(self.mock_github_client, self.mock_console)
        
        # Mock fork data
        mock_fork_data = Mock()
        mock_fork_data.metrics.owner = "test_owner"
        mock_fork_data.metrics.name = "test_repo"
        mock_fork_data.metrics.stargazers_count = 100
        mock_fork_data.metrics.forks_count = 50
        mock_fork_data.metrics.pushed_at = datetime.now(UTC)
        mock_fork_data.exact_commits_ahead = 5
        
        detailed_forks = [mock_fork_data]
        
        # Patch Table to capture column configuration
        with patch('forklift.display.repository_display_service.Table') as mock_table_class:
            mock_table_instance = Mock()
            mock_table_class.return_value = mock_table_instance
            
            # Call the method with show_commits = 0 (no Recent Commits column)
            asyncio.run(service._display_detailed_fork_table(
                detailed_forks,
                "base_owner",
                "base_repo",
                api_calls_made=0,
                api_calls_saved=0,
                show_commits=0,  # This should NOT trigger Recent Commits column
                force_all_commits=False
            ))
            
            # Verify that Recent Commits column was NOT added
            add_column_calls = mock_table_instance.add_column.call_args_list
            
            # Check that no Recent Commits column was added
            recent_commits_calls = []
            for call in add_column_calls:
                args, kwargs = call
                if args and "Recent Commits" in args[0]:
                    recent_commits_calls.append(call)
            
            assert len(recent_commits_calls) == 0, "Recent Commits column should not be added when show_commits is 0"
    
    def test_universal_fork_table_rendering_detailed_mode(self):
        """Test universal fork table rendering in detailed mode."""
        from unittest.mock import Mock, patch
        import asyncio
        
        # Create service
        service = RepositoryDisplayService(self.mock_github_client, self.mock_console)
        
        # Mock fork data with exact commits ahead
        mock_fork_data = Mock()
        mock_fork_data.metrics.owner = "test_owner"
        mock_fork_data.metrics.name = "test_repo"
        mock_fork_data.metrics.stargazers_count = 100
        mock_fork_data.metrics.forks_count = 50
        mock_fork_data.metrics.pushed_at = datetime.now(UTC)
        mock_fork_data.exact_commits_ahead = 5
        
        fork_data_list = [mock_fork_data]
        
        table_context = {
            'owner': 'base_owner',
            'repo': 'base_repo',
            'has_exact_counts': True,
            'mode': 'detailed',
            'api_calls_made': 1,
            'api_calls_saved': 0,
            'fork_data_list': fork_data_list
        }
        
        # Mock the _fetch_commits_concurrently method
        with patch.object(service, '_fetch_commits_concurrently', return_value={}):
            # Call the universal rendering method
            asyncio.run(service._render_fork_table(
                fork_data_list,
                table_context,
                show_commits=0,
                force_all_commits=False
            ))
        
        # Verify console.print was called (table was displayed)
        assert self.mock_console.print.called

    def test_universal_fork_table_rendering_standard_mode(self):
        """Test universal fork table rendering in standard mode."""
        from unittest.mock import Mock, patch
        import asyncio
        
        # Create service
        service = RepositoryDisplayService(self.mock_github_client, self.mock_console)
        
        # Mock fork data with status-based commits
        mock_fork_data = Mock()
        mock_fork_data.metrics.owner = "test_owner"
        mock_fork_data.metrics.name = "test_repo"
        mock_fork_data.metrics.stargazers_count = 100
        mock_fork_data.metrics.forks_count = 50
        mock_fork_data.metrics.pushed_at = datetime.now(UTC)
        mock_fork_data.metrics.commits_ahead_status = "Has commits"
        
        fork_data_list = [mock_fork_data]
        
        # Mock qualification result
        mock_qualification_result = Mock()
        mock_qualification_result.stats.total_forks_discovered = 1
        mock_qualification_result.stats.forks_with_commits = 1
        mock_qualification_result.stats.analysis_candidate_percentage = 100.0
        mock_qualification_result.stats.forks_with_no_commits = 0
        mock_qualification_result.stats.skip_rate_percentage = 0.0
        mock_qualification_result.stats.archived_forks = 0
        mock_qualification_result.stats.disabled_forks = 0
        
        table_context = {
            'owner': 'base_owner',
            'repo': 'base_repo',
            'has_exact_counts': False,
            'mode': 'standard',
            'api_calls_made': 1,
            'api_calls_saved': 0,
            'qualification_result': mock_qualification_result,
            'fork_data_list': fork_data_list
        }
        
        # Mock the _fetch_commits_concurrently method
        with patch.object(service, '_fetch_commits_concurrently', return_value={}):
            # Mock the _sort_forks_enhanced method
            with patch.object(service, '_sort_forks_enhanced', return_value=fork_data_list):
                # Call the universal rendering method
                asyncio.run(service._render_fork_table(
                    fork_data_list,
                    table_context,
                    show_commits=0,
                    force_all_commits=False
                ))
        
        # Verify console.print was called (table was displayed)
        assert self.mock_console.print.called

    def test_commit_data_formatter_detailed_mode(self):
        """Test CommitDataFormatter in detailed mode."""
        from src.forklift.display.repository_display_service import CommitDataFormatter
        
        # Test with exact commit count
        mock_fork_data = Mock()
        mock_fork_data.exact_commits_ahead = 5
        
        result = CommitDataFormatter.format_commit_info(mock_fork_data, has_exact_counts=True)
        assert result == "[green]+5[/green]"
        
        # Test with zero commits
        mock_fork_data.exact_commits_ahead = 0
        result = CommitDataFormatter.format_commit_info(mock_fork_data, has_exact_counts=True)
        assert result == ""
        
        # Test with unknown status
        mock_fork_data.exact_commits_ahead = "Unknown"
        result = CommitDataFormatter.format_commit_info(mock_fork_data, has_exact_counts=True)
        assert result == "[yellow]Unknown[/yellow]"

    def test_commit_data_formatter_standard_mode(self):
        """Test CommitDataFormatter in standard mode."""
        from src.forklift.display.repository_display_service import CommitDataFormatter
        
        # Test with "Has commits" status
        mock_fork_data = Mock()
        mock_fork_data.metrics.commits_ahead_status = "Has commits"
        
        result = CommitDataFormatter.format_commit_info(mock_fork_data, has_exact_counts=False)
        assert result == "Has commits"
        
        # Test with "No commits ahead" status
        mock_fork_data.metrics.commits_ahead_status = "No commits ahead"
        result = CommitDataFormatter.format_commit_info(mock_fork_data, has_exact_counts=False)
        assert result == "0 commits"
        
        # Test with unknown status
        mock_fork_data.metrics.commits_ahead_status = "Unknown"
        result = CommitDataFormatter.format_commit_info(mock_fork_data, has_exact_counts=False)
        assert result == "[yellow]Unknown[/yellow]"

    def test_fork_table_config_consistency(self):
        """Test that ForkTableConfig provides consistent configuration."""
        from src.forklift.display.repository_display_service import ForkTableConfig
        
        # Verify column widths are defined
        assert ForkTableConfig.COLUMN_WIDTHS['url'] == 35
        assert ForkTableConfig.COLUMN_WIDTHS['stars'] == 8
        assert ForkTableConfig.COLUMN_WIDTHS['forks'] == 8
        assert ForkTableConfig.COLUMN_WIDTHS['commits'] == 15
        assert ForkTableConfig.COLUMN_WIDTHS['last_push'] == 14
        
        # Verify column styles are defined
        assert ForkTableConfig.COLUMN_STYLES['url'] == 'cyan'
        assert ForkTableConfig.COLUMN_STYLES['stars'] == 'yellow'
        assert ForkTableConfig.COLUMN_STYLES['forks'] == 'green'
        assert ForkTableConfig.COLUMN_STYLES['commits'] == 'magenta'
        assert ForkTableConfig.COLUMN_STYLES['last_push'] == 'blue'

    def test_universal_fork_table_rendering_detailed_mode(self):
        """Test universal fork table rendering in detailed mode (exact counts)."""
        from unittest.mock import Mock, patch
        from rich.table import Table
        
        # Create service
        service = RepositoryDisplayService(self.mock_github_client, self.mock_console)
        
        # Mock detailed fork data
        mock_fork_data = Mock()
        mock_fork_data.metrics.owner = "test_owner"
        mock_fork_data.metrics.name = "test_repo"
        mock_fork_data.metrics.stargazers_count = 100
        mock_fork_data.metrics.forks_count = 50
        mock_fork_data.metrics.pushed_at = datetime.now(UTC)
        mock_fork_data.exact_commits_ahead = 5
        
        fork_data_list = [mock_fork_data]
        
        # Patch Table to capture column configuration
        with patch('forklift.display.repository_display_service.Table') as mock_table_class:
            mock_table_instance = Mock()
            mock_table_class.return_value = mock_table_instance
            
            # Call universal method in detailed mode
            asyncio.run(service._display_fork_table(
                fork_data_list,
                "base_owner",
                "base_repo",
                table_title="Test Detailed Forks",
                show_exact_counts=True,
                show_commits=0,
                show_insights=False
            ))
            
            # Verify table columns were added with correct configuration
            add_column_calls = mock_table_instance.add_column.call_args_list
            
            # Check column names and widths
            expected_columns = [
                ("URL", {"style": "cyan", "min_width": 35}),
                ("Stars", {"style": "yellow", "justify": "right", "width": 8}),
                ("Forks", {"style": "green", "justify": "right", "width": 8}),
                ("Commits Ahead", {"style": "magenta", "justify": "right", "width": 15}),
                ("Last Push", {"style": "blue", "width": 14})
            ]
            
            assert len(add_column_calls) == len(expected_columns), f"Expected {len(expected_columns)} columns, got {len(add_column_calls)}"
            
            for i, (expected_name, expected_kwargs) in enumerate(expected_columns):
                args, kwargs = add_column_calls[i]
                assert args[0] == expected_name, f"Column {i}: expected '{expected_name}', got '{args[0]}'"
                for key, value in expected_kwargs.items():
                    assert kwargs.get(key) == value, f"Column {i} ({expected_name}): expected {key}={value}, got {kwargs.get(key)}"

    def test_universal_fork_table_rendering_standard_mode(self):
        """Test universal fork table rendering in standard mode (status text)."""
        from unittest.mock import Mock, patch
        from rich.table import Table
        
        # Create service
        service = RepositoryDisplayService(self.mock_github_client, self.mock_console)
        
        # Mock standard fork data
        mock_fork_data = Mock()
        mock_fork_data.metrics.owner = "test_owner"
        mock_fork_data.metrics.name = "test_repo"
        mock_fork_data.metrics.stargazers_count = 100
        mock_fork_data.metrics.forks_count = 50
        mock_fork_data.metrics.pushed_at = datetime.now(UTC)
        mock_fork_data.metrics.commits_ahead_status = "Has commits"
        
        fork_data_list = [mock_fork_data]
        
        # Patch Table to capture column configuration
        with patch('forklift.display.repository_display_service.Table') as mock_table_class:
            mock_table_instance = Mock()
            mock_table_class.return_value = mock_table_instance
            
            # Call universal method in standard mode
            asyncio.run(service._display_fork_table(
                fork_data_list,
                "base_owner",
                "base_repo",
                table_title="Test All Forks",
                show_exact_counts=False,
                show_commits=0,
                show_insights=True
            ))
            
            # Verify same column structure is used
            add_column_calls = mock_table_instance.add_column.call_args_list
            assert len(add_column_calls) == 5, "Should have 5 columns in standard mode"
            
            # Verify "Commits Ahead" column (not "Commits")
            commits_column_call = add_column_calls[3]
            args, kwargs = commits_column_call
            assert args[0] == "Commits Ahead", "Should use 'Commits Ahead' column name in both modes"
            assert kwargs.get('width') == 15, "Should use width 15 for Commits Ahead column"

    def test_format_commits_display_exact_counts(self):
        """Test _format_commits_display method with exact counts."""
        service = RepositoryDisplayService(self.mock_github_client, self.mock_console)
        
        # Test with exact commits ahead
        mock_fork_data = Mock()
        mock_fork_data.exact_commits_ahead = 5
        
        result = service._format_commits_display(mock_fork_data, show_exact_counts=True)
        assert "[green]+5[/green]" in result
        
        # Test with zero commits ahead
        mock_fork_data.exact_commits_ahead = 0
        result = service._format_commits_display(mock_fork_data, show_exact_counts=True)
        assert result == ""

    def test_format_commits_display_status_text(self):
        """Test _format_commits_display method with status text."""
        service = RepositoryDisplayService(self.mock_github_client, self.mock_console)
        
        # Test with "Has commits" status
        mock_fork_data = Mock()
        mock_fork_data.metrics.commits_ahead_status = "Has commits"
        
        result = service._format_commits_display(mock_fork_data, show_exact_counts=False)
        assert result == "Has commits"
        
        # Test with "No commits ahead" status
        mock_fork_data.metrics.commits_ahead_status = "No commits ahead"
        result = service._format_commits_display(mock_fork_data, show_exact_counts=False)
        assert result == "0 commits"

    def test_universal_fork_table_with_recent_commits(self):
        """Test universal fork table rendering with Recent Commits column."""
        from unittest.mock import Mock, patch, AsyncMock
        from rich.table import Table
        
        # Create service
        service = RepositoryDisplayService(self.mock_github_client, self.mock_console)
        
        # Mock fork data
        mock_fork_data = Mock()
        mock_fork_data.metrics.owner = "test_owner"
        mock_fork_data.metrics.name = "test_repo"
        mock_fork_data.metrics.stargazers_count = 100
        mock_fork_data.metrics.forks_count = 50
        mock_fork_data.metrics.pushed_at = datetime.now(UTC)
        mock_fork_data.exact_commits_ahead = 3
        
        fork_data_list = [mock_fork_data]
        
        # Mock commits cache
        commits_cache = {"test_owner/test_repo": "Recent commit info"}
        
        # Patch methods
        with patch('forklift.display.repository_display_service.Table') as mock_table_class:
            with patch.object(service, '_fetch_commits_concurrently', new=AsyncMock(return_value=commits_cache)):
                mock_table_instance = Mock()
                mock_table_class.return_value = mock_table_instance
                
                # Call universal method with show_commits > 0
                asyncio.run(service._display_fork_table(
                    fork_data_list,
                    "base_owner",
                    "base_repo",
                    table_title="Test Forks with Commits",
                    show_exact_counts=True,
                    show_commits=3,
                    show_insights=False
                ))
                
                # Verify Recent Commits column was added
                add_column_calls = mock_table_instance.add_column.call_args_list
                assert len(add_column_calls) == 6, "Should have 6 columns when show_commits > 0"
                
                # Check Recent Commits column
                recent_commits_call = add_column_calls[5]
                args, kwargs = recent_commits_call
                assert args[0] == "Recent Commits"
                assert kwargs.get('no_wrap') is True, "Recent Commits column should have no_wrap=True"