"""Unit tests for Interactive Analyzer service."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from rich.console import Console

from forklift.analysis.interactive_analyzer import InteractiveAnalyzer
from forklift.models.github import Repository, User, Commit
from forklift.models.filters import ForkDetails, BranchInfo, ForkDetailsFilter
from forklift.github.client import GitHubAPIError


class TestInteractiveAnalyzer:
    """Test Interactive Analyzer functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_github_client = Mock()
        self.mock_console = Mock()
        # Add the methods that Rich Progress expects
        self.mock_console.get_time = Mock(return_value=0.0)
        self.mock_console.set_live = Mock(return_value=True)
        self.mock_console.show_cursor = Mock()
        self.mock_console.push_render_hook = Mock()
        self.mock_console.clear_live = Mock()
        self.mock_console._live_stack = []
        self.mock_console.__enter__ = Mock(return_value=self.mock_console)
        self.mock_console.__exit__ = Mock(return_value=None)
        
        self.analyzer = InteractiveAnalyzer(
            github_client=self.mock_github_client,
            console=self.mock_console
        )

    def test_init_with_console(self):
        """Test initialization with provided console."""
        console = Mock(spec=Console)
        analyzer = InteractiveAnalyzer(self.mock_github_client, console)
        assert analyzer.github_client == self.mock_github_client
        assert analyzer.console == console

    def test_init_without_console(self):
        """Test initialization without console creates new one."""
        analyzer = InteractiveAnalyzer(self.mock_github_client)
        assert analyzer.github_client == self.mock_github_client
        assert analyzer.console is not None

    def test_parse_repository_url_https(self):
        """Test parsing HTTPS GitHub URLs."""
        owner, repo = self.analyzer._parse_repository_url("https://github.com/owner/repo")
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repository_url_https_with_git(self):
        """Test parsing HTTPS URLs with .git suffix."""
        owner, repo = self.analyzer._parse_repository_url("https://github.com/owner/repo.git")
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repository_url_ssh(self):
        """Test parsing SSH GitHub URLs."""
        owner, repo = self.analyzer._parse_repository_url("git@github.com:owner/repo.git")
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repository_url_short_format(self):
        """Test parsing short owner/repo format."""
        owner, repo = self.analyzer._parse_repository_url("owner/repo")
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repository_url_invalid(self):
        """Test parsing invalid URLs raises ValueError."""
        with pytest.raises(ValueError, match="Invalid GitHub repository URL"):
            self.analyzer._parse_repository_url("invalid-url")

    def test_format_datetime_none(self):
        """Test formatting None datetime."""
        result = self.analyzer._format_datetime(None)
        assert result == "Unknown"

    def test_format_datetime_today(self):
        """Test formatting today's datetime."""
        now = datetime.utcnow()
        result = self.analyzer._format_datetime(now)
        assert result == "Today"

    def test_format_datetime_yesterday(self):
        """Test formatting yesterday's datetime."""
        from datetime import timedelta
        yesterday = datetime.utcnow() - timedelta(days=1)
        result = self.analyzer._format_datetime(yesterday)
        assert result == "Yesterday"

    def test_format_datetime_days_ago(self):
        """Test formatting datetime from days ago."""
        from datetime import timedelta
        three_days_ago = datetime.utcnow() - timedelta(days=3)
        result = self.analyzer._format_datetime(three_days_ago)
        assert "3 days ago" in result

    def test_format_datetime_weeks_ago(self):
        """Test formatting datetime from weeks ago."""
        from datetime import timedelta
        two_weeks_ago = datetime.utcnow() - timedelta(days=14)
        result = self.analyzer._format_datetime(two_weeks_ago)
        assert "week" in result

    @pytest.mark.asyncio
    async def test_show_fork_details_success(self):
        """Test successful fork details display."""
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
            created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2023, 12, 1, tzinfo=timezone.utc),
            pushed_at=datetime(2023, 12, 1, tzinfo=timezone.utc)
        )
        
        # Setup mock responses
        self.mock_github_client.get_repository = AsyncMock(return_value=mock_repo)
        self.mock_github_client.get_repository_branches = AsyncMock(return_value=[
            {"name": "main", "protected": False},
            {"name": "feature-branch", "protected": False}
        ])
        self.mock_github_client.get_branch_commits = AsyncMock(return_value=[
            {
                "sha": "abc123",
                "commit": {
                    "committer": {"date": "2023-12-01T10:00:00Z"},
                    "message": "Test commit"
                }
            }
        ])
        self.mock_github_client.get_branch_comparison = AsyncMock(return_value={"ahead_by": 5})
        self.mock_github_client.get_repository_contributors = AsyncMock(return_value=[
            {"login": "user1"},
            {"login": "user2"}
        ])
        self.mock_github_client.get_repository_languages = AsyncMock(return_value={"Python": 1000})
        self.mock_github_client.get_repository_topics = AsyncMock(return_value=["python", "web"])
        
        # Call method
        result = await self.analyzer.show_fork_details("testowner/testrepo")
        
        # Verify calls
        self.mock_github_client.get_repository.assert_called_once_with("testowner", "testrepo")
        self.mock_github_client.get_repository_branches.assert_called_once()
        self.mock_github_client.get_repository_contributors.assert_called_once()
        self.mock_github_client.get_repository_languages.assert_called_once_with("testowner", "testrepo")
        self.mock_github_client.get_repository_topics.assert_called_once_with("testowner", "testrepo")
        
        # Verify result
        assert isinstance(result, ForkDetails)
        assert result.fork == mock_repo
        assert len(result.branches) == 2
        assert result.contributors == ["user1", "user2"]
        assert result.contributor_count == 2
        assert result.languages == {"Python": 1000}
        assert result.topics == ["python", "web"]
        
        # Verify console output was called
        self.mock_console.print.assert_called()

    @pytest.mark.asyncio
    async def test_show_fork_details_with_filters(self):
        """Test fork details display with custom filters."""
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
            forks_count=50
        )
        
        # Setup filters to exclude branches and contributors
        filters = ForkDetailsFilter(
            include_branches=False,
            include_contributors=False,
            max_branches=5,
            max_contributors=5
        )
        
        # Setup mock responses
        self.mock_github_client.get_repository = AsyncMock(return_value=mock_repo)
        self.mock_github_client.get_repository_languages = AsyncMock(return_value={})
        self.mock_github_client.get_repository_topics = AsyncMock(return_value=[])
        
        # Call method
        result = await self.analyzer.show_fork_details("testowner/testrepo", filters)
        
        # Verify that branches and contributors were not fetched
        self.mock_github_client.get_repository_branches.assert_not_called()
        self.mock_github_client.get_repository_contributors.assert_not_called()
        
        # Verify result
        assert isinstance(result, ForkDetails)
        assert result.fork == mock_repo
        assert result.branches == []
        assert result.contributors == []
        assert result.contributor_count == 0

    @pytest.mark.asyncio
    async def test_show_fork_details_api_error(self):
        """Test fork details display with API error."""
        # Setup mock to raise error
        self.mock_github_client.get_repository = AsyncMock(side_effect=GitHubAPIError("Repository not found"))
        
        # Call method and expect exception
        with pytest.raises(GitHubAPIError):
            await self.analyzer.show_fork_details("testowner/testrepo")
        
        # Verify error was logged to console
        self.mock_console.print.assert_called()
        error_call = self.mock_console.print.call_args[0][0]
        assert "[red]Error:" in error_call

    @pytest.mark.asyncio
    async def test_analyze_specific_fork_success(self):
        """Test successful specific fork analysis."""
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
            forks_count=50
        )
        
        # Setup mock responses
        self.mock_github_client.get_repository = AsyncMock(return_value=mock_repo)
        self.mock_github_client.get_repository_branches = AsyncMock(return_value=[
            {"name": "main", "protected": False}
        ])
        self.mock_github_client.get_branch_commits = AsyncMock(return_value=[])
        self.mock_github_client.get_repository_contributors = AsyncMock(return_value=[])
        self.mock_github_client.get_repository_languages = AsyncMock(return_value={})
        self.mock_github_client.get_repository_topics = AsyncMock(return_value=[])
        
        # Call method
        result = await self.analyzer.analyze_specific_fork("testowner/testrepo")
        
        # Verify result structure
        assert "fork_details" in result
        assert "branch_analysis" in result
        assert "analysis_date" in result
        assert isinstance(result["fork_details"], ForkDetails)
        assert result["branch_analysis"] is None  # No specific branch analyzed

    @pytest.mark.asyncio
    async def test_analyze_specific_fork_with_branch(self):
        """Test specific fork analysis with branch analysis."""
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
            forks_count=50
        )
        
        # Setup mock commit data
        mock_commit_data = {
            "sha": "def456abc123789012345678901234567890abcd",  # 40 character SHA
            "commit": {
                "message": "feat: add new feature",
                "author": {"date": "2023-12-01T10:00:00Z"},
                "committer": {"date": "2023-12-01T10:00:00Z"}
            },
            "author": {"login": "testuser", "html_url": "https://github.com/testuser"},
            "committer": {"login": "testuser", "html_url": "https://github.com/testuser"},
            "stats": {"additions": 10, "deletions": 5},
            "files": [{"filename": "test.py"}],
            "parents": [{"sha": "parent456789012345678901234567890abcd"}]  # 40 character SHA
        }
        
        # Setup mock responses
        self.mock_github_client.get_repository = AsyncMock(return_value=mock_repo)
        self.mock_github_client.get_repository_branches = AsyncMock(return_value=[
            {"name": "main", "protected": False},
            {"name": "feature-branch", "protected": False}
        ])
        self.mock_github_client.get_branch_commits = AsyncMock(return_value=[mock_commit_data])
        self.mock_github_client.get_branch_comparison = AsyncMock(return_value={"ahead_by": 1})
        self.mock_github_client.get_repository_contributors = AsyncMock(return_value=[])
        self.mock_github_client.get_repository_languages = AsyncMock(return_value={})
        self.mock_github_client.get_repository_topics = AsyncMock(return_value=[])
        
        # Call method with specific branch
        result = await self.analyzer.analyze_specific_fork("testowner/testrepo", branch="feature-branch")
        
        # Verify result structure
        assert "fork_details" in result
        assert "branch_analysis" in result
        assert "analysis_date" in result
        assert isinstance(result["fork_details"], ForkDetails)
        assert result["branch_analysis"] is not None
        assert result["branch_analysis"]["branch"] == "feature-branch"

    @pytest.mark.asyncio
    async def test_get_branch_info_success(self):
        """Test successful branch information retrieval."""
        # Setup mock branch data
        mock_branches = [
            {"name": "main", "protected": False},
            {"name": "feature-branch", "protected": True}
        ]
        
        mock_commits = [
            {
                "sha": "abc123",
                "commit": {
                    "committer": {"date": "2023-12-01T10:00:00Z"}
                }
            }
        ]
        
        # Setup mock responses
        self.mock_github_client.get_repository_branches = AsyncMock(return_value=mock_branches)
        self.mock_github_client.get_branch_commits = AsyncMock(return_value=mock_commits)
        self.mock_github_client.get_branch_comparison = AsyncMock(return_value={"ahead_by": 5})
        
        # Call method
        result = await self.analyzer._get_branch_info("owner", "repo", "main", 10)
        
        # Verify result
        assert len(result) == 2
        assert isinstance(result[0], BranchInfo)
        assert result[0].name in ["main", "feature-branch"]
        
        # Verify API calls
        self.mock_github_client.get_repository_branches.assert_called_once_with("owner", "repo", max_count=10)

    @pytest.mark.asyncio
    async def test_get_branch_info_with_errors(self):
        """Test branch information retrieval with some errors."""
        # Setup mock branch data
        mock_branches = [
            {"name": "main", "protected": False},
            {"name": "error-branch", "protected": False}
        ]
        
        # Setup mock responses - second branch will fail
        self.mock_github_client.get_repository_branches = AsyncMock(return_value=mock_branches)
        
        def mock_get_commits(owner, repo, branch, max_count):
            if branch == "error-branch":
                raise GitHubAPIError("Branch not found")
            return [{"sha": "abc123", "commit": {"committer": {"date": "2023-12-01T10:00:00Z"}}}]
        
        self.mock_github_client.get_branch_commits = AsyncMock(side_effect=mock_get_commits)
        self.mock_github_client.get_branch_comparison = AsyncMock(return_value={"ahead_by": 0})
        
        # Call method
        result = await self.analyzer._get_branch_info("owner", "repo", "main", 10)
        
        # Should still return both branches, but error-branch will have 0 commits
        assert len(result) == 2
        
        # Find the error branch
        error_branch = next(b for b in result if b.name == "error-branch")
        assert error_branch.commit_count == 0

    @pytest.mark.asyncio
    async def test_get_contributors_success(self):
        """Test successful contributors retrieval."""
        mock_contributors = [
            {"login": "user1"},
            {"login": "user2"},
            {"login": "user3"}
        ]
        
        self.mock_github_client.get_repository_contributors = AsyncMock(return_value=mock_contributors)
        
        # Call method
        usernames, total_count = await self.analyzer._get_contributors("owner", "repo", 10)
        
        # Verify result
        assert usernames == ["user1", "user2", "user3"]
        assert total_count == 3
        
        # Verify API call
        self.mock_github_client.get_repository_contributors.assert_called_once_with("owner", "repo", max_count=10)

    @pytest.mark.asyncio
    async def test_get_contributors_with_limit(self):
        """Test contributors retrieval with limit."""
        mock_contributors = [
            {"login": "user1"},
            {"login": "user2"},
            {"login": "user3"},
            {"login": "user4"},
            {"login": "user5"}
        ]
        
        self.mock_github_client.get_repository_contributors = AsyncMock(return_value=mock_contributors)
        
        # Call method with limit of 3
        usernames, total_count = await self.analyzer._get_contributors("owner", "repo", 3)
        
        # Verify result - should only return first 3
        assert usernames == ["user1", "user2", "user3"]
        assert total_count == 5  # Total count should still be 5

    @pytest.mark.asyncio
    async def test_get_contributors_error(self):
        """Test contributors retrieval with error."""
        self.mock_github_client.get_repository_contributors = AsyncMock(side_effect=GitHubAPIError("API Error"))
        
        # Call method
        usernames, total_count = await self.analyzer._get_contributors("owner", "repo", 10)
        
        # Should return empty results on error
        assert usernames == []
        assert total_count == 0

    @pytest.mark.asyncio
    async def test_analyze_specific_branch_success(self):
        """Test successful specific branch analysis."""
        # Setup mock commit data
        mock_commit_data = {
            "sha": "abc123def456789012345678901234567890abcd",  # 40 character SHA
            "commit": {
                "message": "feat: add new feature\n\nDetailed description",
                "author": {"date": "2023-12-01T10:00:00Z"},
                "committer": {"date": "2023-12-01T10:00:00Z"}
            },
            "author": {"login": "testuser", "html_url": "https://github.com/testuser"},
            "committer": {"login": "testuser", "html_url": "https://github.com/testuser"},
            "stats": {"additions": 10, "deletions": 5},
            "files": [{"filename": "test.py"}],
            "parents": [{"sha": "parent123456789012345678901234567890"}]  # 40 character SHA
        }
        
        self.mock_github_client.get_branch_commits = AsyncMock(return_value=[mock_commit_data])
        
        # Call method
        result = await self.analyzer._analyze_specific_branch("owner", "repo", "feature-branch", ForkDetailsFilter())
        
        # Verify result
        assert result["branch"] == "feature-branch"
        assert len(result["commits"]) == 1
        assert "commit_types" in result
        assert "total_changes" in result
        assert "unique_authors" in result
        assert result["total_changes"] == 15  # 10 additions + 5 deletions
        assert "testuser" in result["unique_authors"]

    @pytest.mark.asyncio
    async def test_analyze_specific_branch_error(self):
        """Test specific branch analysis with error."""
        self.mock_github_client.get_branch_commits = AsyncMock(side_effect=GitHubAPIError("Branch not found"))
        
        # Call method
        result = await self.analyzer._analyze_specific_branch("owner", "repo", "nonexistent", ForkDetailsFilter())
        
        # Should return empty result on error
        assert result == {}
        
        # Verify error was logged to console
        self.mock_console.print.assert_called()

    def test_display_fork_analysis(self):
        """Test fork analysis display formatting."""
        # Create test fork details
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
        
        branch_info = BranchInfo(name="main", commit_count=100)
        
        fork_details = ForkDetails(
            fork=mock_repo,
            branches=[branch_info],
            total_commits=100,
            contributors=["user1", "user2"],
            contributor_count=2,
            languages={"Python": 1000},
            topics=["python", "web"]
        )
        
        # Call method
        self.analyzer._display_fork_analysis(fork_details, "main")
        
        # Verify console.print was called multiple times
        assert self.mock_console.print.call_count >= 1

    def test_display_fork_details_table(self):
        """Test fork details table display."""
        # Create test fork details
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
            forks_count=50
        )
        
        fork_details = ForkDetails(
            fork=mock_repo,
            branches=[],
            total_commits=0,
            contributors=[],
            contributor_count=0,
            languages={},
            topics=[]
        )
        
        # Call method
        self.analyzer._display_fork_details_table(fork_details)
        
        # Verify console.print was called
        self.mock_console.print.assert_called()

    def test_display_branches_table(self):
        """Test branches table display."""
        branches = [
            BranchInfo(name="main", commit_count=100, is_default=True),
            BranchInfo(name="feature", commit_count=25, commits_ahead_of_main=10)
        ]
        
        # Call method
        self.analyzer._display_branches_table(branches, "feature")
        
        # Verify console.print was called
        self.mock_console.print.assert_called()

    def test_display_branches_table_empty(self):
        """Test branches table display with no branches."""
        # Call method with empty list
        self.analyzer._display_branches_table([])
        
        # Should not call console.print for empty branches
        self.mock_console.print.assert_not_called()

    def test_display_contributors_panel(self):
        """Test contributors panel display."""
        contributors = ["user1", "user2", "user3"]
        
        # Call method
        self.analyzer._display_contributors_panel(contributors, 3)
        
        # Verify console.print was called
        self.mock_console.print.assert_called()

    def test_display_contributors_panel_empty(self):
        """Test contributors panel display with no contributors."""
        # Call method with empty list
        self.analyzer._display_contributors_panel([], 0)
        
        # Should not call console.print for empty contributors
        self.mock_console.print.assert_not_called()

    def test_display_languages_panel(self):
        """Test languages panel display."""
        languages = {"Python": 1000, "JavaScript": 500, "HTML": 200}
        
        # Call method
        self.analyzer._display_languages_panel(languages)
        
        # Verify console.print was called
        self.mock_console.print.assert_called()

    def test_display_languages_panel_empty(self):
        """Test languages panel display with no languages."""
        # Call method with empty dict
        self.analyzer._display_languages_panel({})
        
        # Should not call console.print for empty languages
        self.mock_console.print.assert_not_called()

    def test_display_topics_panel(self):
        """Test topics panel display."""
        topics = ["python", "web", "api", "backend"]
        
        # Call method
        self.analyzer._display_topics_panel(topics)
        
        # Verify console.print was called
        self.mock_console.print.assert_called()

    def test_display_topics_panel_empty(self):
        """Test topics panel display with no topics."""
        # Call method with empty list
        self.analyzer._display_topics_panel([])
        
        # Should not call console.print for empty topics
        self.mock_console.print.assert_not_called()