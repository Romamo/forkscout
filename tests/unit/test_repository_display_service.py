"""Unit tests for Repository Display Service."""

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
            github_client=self.mock_github_client,
            console=self.mock_console
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

    def test_parse_repository_url_https(self):
        """Test parsing HTTPS GitHub URLs."""
        owner, repo = self.service._parse_repository_url("https://github.com/owner/repo")
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repository_url_https_with_git(self):
        """Test parsing HTTPS URLs with .git suffix."""
        owner, repo = self.service._parse_repository_url("https://github.com/owner/repo.git")
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repository_url_https_with_slash(self):
        """Test parsing HTTPS URLs with trailing slash."""
        owner, repo = self.service._parse_repository_url("https://github.com/owner/repo/")
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repository_url_ssh(self):
        """Test parsing SSH GitHub URLs."""
        owner, repo = self.service._parse_repository_url("git@github.com:owner/repo.git")
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
        repo.pushed_at = datetime.utcnow().replace(year=datetime.utcnow().year - 2).replace(tzinfo=UTC)
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
        repo.pushed_at = base_time - timedelta(days=30)    # Last push 30 days ago
        result = self.service._calculate_fork_activity_status(repo)
        assert result == "Active"

    def test_calculate_fork_activity_status_active_edge_case(self):
        """Test fork activity status calculation for fork active exactly 90 days ago."""
        base_time = datetime.utcnow().replace(tzinfo=UTC)
        repo = Mock()
        repo.created_at = base_time - timedelta(days=200)  # Created 200 days ago
        repo.pushed_at = base_time - timedelta(days=90)    # Last push exactly 90 days ago
        result = self.service._calculate_fork_activity_status(repo)
        assert result == "Active"

    def test_calculate_fork_activity_status_stale(self):
        """Test fork activity status calculation for stale fork."""
        base_time = datetime.utcnow().replace(tzinfo=UTC)
        repo = Mock()
        repo.created_at = base_time - timedelta(days=365)  # Created 1 year ago
        repo.pushed_at = base_time - timedelta(days=180)   # Last push 6 months ago
        result = self.service._calculate_fork_activity_status(repo)
        assert result == "Stale"

    def test_calculate_fork_activity_status_with_commits_but_old(self):
        """Test fork activity status calculation for fork with commits but very old."""
        base_time = datetime.utcnow().replace(tzinfo=UTC)
        repo = Mock()
        repo.created_at = base_time - timedelta(days=500)  # Created 500 days ago
        repo.pushed_at = base_time - timedelta(days=400)   # Last push 400 days ago (has commits but old)
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
            pushed_at=datetime(2023, 12, 1, tzinfo=UTC)
        )

        # Setup mock responses
        self.mock_github_client.get_repository = AsyncMock(return_value=mock_repo)
        self.mock_github_client.get_repository_languages = AsyncMock(return_value={"Python": 1000, "JavaScript": 500})
        self.mock_github_client.get_repository_topics = AsyncMock(return_value=["python", "web", "api"])

        # Call method
        result = await self.service.show_repository_details("testowner/testrepo")

        # Verify calls
        self.mock_github_client.get_repository.assert_called_once_with("testowner", "testrepo")
        self.mock_github_client.get_repository_languages.assert_called_once_with("testowner", "testrepo")
        self.mock_github_client.get_repository_topics.assert_called_once_with("testowner", "testrepo")

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
        self.mock_github_client.get_repository = AsyncMock(side_effect=GitHubAPIError("Repository not found"))

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
            language="Python"
        )

        repo_details = {
            "repository": mock_repo,
            "languages": {"Python": 1000, "JavaScript": 500},
            "topics": ["python", "web"],
            "primary_language": "Python",
            "license": "MIT License",
            "last_activity": "1 month ago",
            "created": "1 year ago",
            "updated": "1 week ago"
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
            language="Python"
        )

        enhanced_forks = [{
            "fork": mock_fork,
            "commits_ahead": 5,
            "commits_behind": 2,
            "activity_status": "active",
            "last_activity": "1 week ago"
        }]

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
                forks_count=0
            )

            enhanced_forks.append({
                "fork": mock_fork,
                "commits_ahead": 1,
                "commits_behind": 0,
                "activity_status": "active",
                "last_activity": "1 week ago"
            })

        # Call method
        self.service._display_forks_table(enhanced_forks, max_display=50)

        # Verify console.print was called multiple times (table + overflow message)
        assert self.mock_console.print.call_count >= 2

        # Check that overflow message was printed
        calls = [call[0][0] for call in self.mock_console.print.call_args_list]
        overflow_messages = [call for call in calls if "... and" in str(call) and "more forks" in str(call)]
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
            created_at=datetime.utcnow() - timedelta(days=200)  # 200 days ago
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
            created_at=datetime.utcnow() - timedelta(days=200)  # 200 days ago
        )

        # Mock the show_forks_summary method to return our test data
        _enhanced_forks = [
            {
                "fork": mock_fork1,
                "commits_ahead": 5,
                "commits_behind": 2,
                "activity_status": "moderate",
                "last_activity": "2 months ago"
            },
            {
                "fork": mock_fork2,
                "commits_ahead": 3,
                "commits_behind": 1,
                "activity_status": "stale",
                "last_activity": "3 months ago"
            }
        ]

        # Create filter that should match only the first fork
        filters = PromisingForksFilter(
            min_stars=5,  # Only fork1 has >= 5 stars
            min_commits_ahead=1
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
            created_at=datetime(2023, 1, 1, tzinfo=UTC)
        )

        _enhanced_forks = [{
            "fork": mock_fork,
            "commits_ahead": 1,
            "commits_behind": 0,
            "activity_status": "stale",
            "last_activity": "3 months ago"
        }]

        # Create strict filter that won't match
        filters = PromisingForksFilter(
            min_stars=10,  # Fork only has 2 stars
            min_commits_ahead=5  # Fork only has 1 commit ahead
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
            pushed_at=datetime(2023, 11, 1, tzinfo=UTC)
        )

        promising_forks = [{
            "fork": mock_fork,
            "commits_ahead": 5,
            "commits_behind": 2,
            "activity_status": "active",
            "last_activity": "1 week ago"
        }]

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
            pushed_at=base_time - timedelta(days=30)     # Last push 30 days ago (Active)
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
            pushed_at=base_time - timedelta(days=100)    # Same as created (No commits)
        )

        # Setup mock response
        self.mock_github_client.get_repository_forks = AsyncMock(return_value=[mock_fork1, mock_fork2])

        # Call method
        result = await self.service.list_forks_preview("testowner/testrepo")

        # Verify calls
        self.mock_github_client.get_repository_forks.assert_called_once_with("testowner", "testrepo")

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
        self.mock_github_client.get_repository_forks = AsyncMock(side_effect=GitHubAPIError("API error"))

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
            pushed_at=base_time - timedelta(days=30)  # More recent
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
            pushed_at=base_time - timedelta(days=60)  # Older
        )

        # Setup mock response (unsorted)
        self.mock_github_client.get_repository_forks = AsyncMock(return_value=[mock_fork1, mock_fork2])

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
                "commits_ahead": "Unknown"
            },
            {
                "name": "testrepo",
                "owner": "user2",
                "stars": 5,
                "last_push_date": datetime(2023, 10, 1, tzinfo=UTC),
                "fork_url": "https://github.com/user2/testrepo",
                "activity_status": "No commits",
                "commits_ahead": "None"
            }
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
            max_fork_age_days=365
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
            pushed_at=base_time - timedelta(days=10)     # Last push 10 days ago (Active)
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
            pushed_at=base_time - timedelta(days=200)    # Last push 200 days ago (Stale)
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
            created_at=base_time - timedelta(days=50),   # Created 50 days ago
            pushed_at=base_time - timedelta(days=50)     # Same as created (No commits)
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
        active_item = next(item for item in fork_items if item["owner"] == "active_user")
        assert active_item["activity_status"] == "Active"

        stale_item = next(item for item in fork_items if item["owner"] == "stale_user")
        assert stale_item["activity_status"] == "Stale"

        no_commits_item = next(item for item in fork_items if item["owner"] == "no_commits_user")
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
                "commits_ahead": "Unknown"
            },
            {
                "name": "stale_repo",
                "owner": "stale_user",
                "stars": 5,
                "last_push_date": datetime(2023, 6, 1, tzinfo=UTC),
                "fork_url": "https://github.com/stale_user/stale_repo",
                "activity_status": "Stale",
                "commits_ahead": "Unknown"
            },
            {
                "name": "no_commits_repo",
                "owner": "no_commits_user",
                "stars": 1,
                "last_push_date": datetime(2023, 1, 1, tzinfo=UTC),
                "fork_url": "https://github.com/no_commits_user/no_commits_repo",
                "activity_status": "No commits",
                "commits_ahead": "None"
            }
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
            updated_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
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
            updated_at=datetime(2023, 2, 1, 12, 0, 0, tzinfo=UTC)
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
            updated_at=datetime(2023, 2, 1, 12, 0, 0, tzinfo=UTC)
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
            updated_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
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
        assert self.service._style_commits_ahead_status("Unknown") == "[green]Yes[/green]"
        assert self.service._style_commits_ahead_status("Invalid") == "Unknown"  # Unknown status returns as "Unknown"

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
            pushed_at=base_time - timedelta(days=10)
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
            pushed_at=None  # Missing pushed_at
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
            pushed_at=base_time - timedelta(days=30) + timedelta(seconds=30)  # 30 seconds after created
        )

        # Setup mock response
        self.mock_github_client.get_repository_forks = AsyncMock(
            return_value=[missing_created_fork, missing_pushed_fork, within_minute_fork]
        )

        # Call method
        result = await self.service.list_forks_preview("testowner/testrepo")

        # Verify all edge cases are handled
        fork_items = result["forks"]

        missing_created_item = next(item for item in fork_items if item["owner"] == "missing_created")
        assert missing_created_item["activity_status"] == "No commits"

        missing_pushed_item = next(item for item in fork_items if item["owner"] == "missing_pushed")
        assert missing_pushed_item["activity_status"] == "No commits"

        within_minute_item = next(item for item in fork_items if item["owner"] == "within_minute")
        assert within_minute_item["activity_status"] == "No commits"
