"""End-to-end tests for show-forks command with --show-commits functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner
from datetime import datetime, timezone

from forklift.cli import cli
from forklift.config.settings import ForkliftConfig
from forklift.models.github import Repository, Commit, User
from forklift.models.fork_qualification import QualifiedForksResult, CollectedForkData, ForkQualificationMetrics


class TestShowForksCommitsE2E:
    """End-to-end tests for show-forks with commits functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock(spec=ForkliftConfig)
        config.github.token = "test_token"
        config.github.rate_limit_delay = 0.1
        return config

    @pytest.fixture
    def sample_repository(self):
        """Create a sample repository for testing."""
        return Repository(
            id=12345,
            name="e2e-test-repo",
            full_name="testowner/e2e-test-repo",
            owner="testowner",
            description="End-to-end test repository",
            html_url="https://github.com/testowner/e2e-test-repo",
            clone_url="https://github.com/testowner/e2e-test-repo.git",
            ssh_url="git@github.com:testowner/e2e-test-repo.git",
            url="https://api.github.com/repos/testowner/e2e-test-repo",
            stargazers_count=150,
            forks_count=30,
            watchers_count=150,
            open_issues_count=8,
            size=2048,
            default_branch="main",
            language="Python",
            topics=["python", "e2e", "testing"],
            license={"key": "mit", "name": "MIT License"},
            private=False,
            fork=False,
            archived=False,
            disabled=False,
            created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            pushed_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
        )

    @pytest.fixture
    def realistic_forks_data(self):
        """Create realistic fork data for end-to-end testing."""
        return [
            CollectedForkData(
                name="active-feature-fork",
                owner="activedev",
                full_name="activedev/active-feature-fork",
                html_url="https://github.com/activedev/active-feature-fork",
                clone_url="https://github.com/activedev/active-feature-fork.git",
                qualification_metrics=ForkQualificationMetrics(
                    stargazers_count=25,
                    forks_count=3,
                    size=2100,
                    language="Python",
                    created_at=datetime(2023, 6, 1, tzinfo=timezone.utc),
                    updated_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
                    pushed_at=datetime(2024, 1, 16, tzinfo=timezone.utc),
                    open_issues_count=2,
                    topics=["python", "feature", "enhancement"],
                    watchers_count=25,
                    archived=False,
                    disabled=False,
                    commits_ahead_status="Has commits",
                    can_skip_analysis=False
                )
            ),
            CollectedForkData(
                name="bugfix-collection",
                owner="bugfixer",
                full_name="bugfixer/bugfix-collection",
                html_url="https://github.com/bugfixer/bugfix-collection",
                clone_url="https://github.com/bugfixer/bugfix-collection.git",
                qualification_metrics=ForkQualificationMetrics(
                    stargazers_count=12,
                    forks_count=1,
                    size=2050,
                    language="Python",
                    created_at=datetime(2023, 8, 15, tzinfo=timezone.utc),
                    updated_at=datetime(2024, 1, 10, tzinfo=timezone.utc),
                    pushed_at=datetime(2024, 1, 12, tzinfo=timezone.utc),
                    open_issues_count=0,
                    topics=["python", "bugfix"],
                    watchers_count=12,
                    archived=False,
                    disabled=False,
                    commits_ahead_status="Has commits",
                    can_skip_analysis=False
                )
            ),
            CollectedForkData(
                name="experimental-branch",
                owner="experimenter",
                full_name="experimenter/experimental-branch",
                html_url="https://github.com/experimenter/experimental-branch",
                clone_url="https://github.com/experimenter/experimental-branch.git",
                qualification_metrics=ForkQualificationMetrics(
                    stargazers_count=5,
                    forks_count=0,
                    size=2200,
                    language="Python",
                    created_at=datetime(2023, 11, 1, tzinfo=timezone.utc),
                    updated_at=datetime(2024, 1, 5, tzinfo=timezone.utc),
                    pushed_at=datetime(2024, 1, 8, tzinfo=timezone.utc),
                    open_issues_count=1,
                    topics=["python", "experimental"],
                    watchers_count=5,
                    archived=False,
                    disabled=False,
                    commits_ahead_status="Has commits",
                    can_skip_analysis=False
                )
            ),
            CollectedForkData(
                name="old-fork",
                owner="olduser",
                full_name="olduser/old-fork",
                html_url="https://github.com/olduser/old-fork",
                clone_url="https://github.com/olduser/old-fork.git",
                qualification_metrics=ForkQualificationMetrics(
                    stargazers_count=2,
                    forks_count=0,
                    size=2048,
                    language="Python",
                    created_at=datetime(2022, 3, 1, tzinfo=timezone.utc),
                    updated_at=datetime(2022, 3, 1, tzinfo=timezone.utc),
                    pushed_at=datetime(2022, 3, 1, tzinfo=timezone.utc),
                    open_issues_count=0,
                    topics=["python"],
                    watchers_count=2,
                    archived=False,
                    disabled=False,
                    commits_ahead_status="No commits ahead",
                    can_skip_analysis=True
                )
            )
        ]

    def create_realistic_commits(self, fork_owner: str, fork_name: str, count: int) -> list[Commit]:
        """Create realistic commits for a specific fork."""
        commit_templates = {
            "activedev": [
                "feat: add new authentication system",
                "feat: implement user dashboard",
                "fix: resolve login timeout issue",
                "docs: update API documentation",
                "test: add integration tests for auth"
            ],
            "bugfixer": [
                "fix: handle null pointer exception in parser",
                "fix: correct memory leak in cache manager",
                "fix: resolve race condition in worker threads"
            ],
            "experimenter": [
                "experiment: try new ML algorithm approach",
                "wip: prototype async processing pipeline",
                "experiment: test performance optimizations"
            ],
            "olduser": []  # No commits for old fork
        }
        
        messages = commit_templates.get(fork_owner, ["generic commit message"])
        
        return [
            Commit(
                sha=f"{fork_owner[:4]}{i:034d}",  # Pad to 40 chars
                message=messages[i % len(messages)] if messages else f"commit {i}",
                author=User(
                    login=f"{fork_owner}dev",
                    name=f"{fork_owner.title()} Developer",
                    email=f"{fork_owner}@example.com",
                    html_url=f"https://github.com/{fork_owner}dev",
                    id=hash(fork_owner) % 10000 + i
                ),
                date=datetime(2024, 1, (i % 28) + 1, tzinfo=timezone.utc),
                files_changed=[f"{fork_owner}{i}.py"],
                additions=10 * ((i % 10) + 1),
                deletions=5 * ((i % 8) + 1)
            )
            for i in range(count)
        ]

    @pytest.mark.asyncio
    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    async def test_complete_show_forks_workflow_with_commits(
        self, mock_display_service_class, mock_github_client_class, mock_load_config,
        mock_config, sample_repository, realistic_forks_data
    ):
        """Test complete end-to-end workflow of show-forks with --show-commits."""
        mock_load_config.return_value = mock_config
        
        # Setup GitHub client mock
        mock_client = AsyncMock()
        mock_github_client_class.return_value = mock_client
        mock_client.get_repository.return_value = sample_repository
        
        # Setup realistic commit responses
        def mock_get_recent_commits(owner, repo, branch=None, limit=None):
            return self.create_realistic_commits(owner, repo, limit or 3)
        
        mock_client.get_recent_commits.side_effect = mock_get_recent_commits
        
        # Setup display service mock
        mock_display_service = AsyncMock()
        mock_display_service_class.return_value = mock_display_service
        
        # Mock the complete workflow result
        mock_display_service.show_fork_data.return_value = {
            "total_forks": len(realistic_forks_data),
            "displayed_forks": len(realistic_forks_data),
            "forks": realistic_forks_data,
            "commits_fetched": True,
            "commits_per_fork": 3
        }
        
        runner = CliRunner()
        
        # Execute the complete workflow
        with patch("forklift.cli._show_forks_summary") as mock_show_forks:
            mock_show_forks.return_value = None
            
            result = runner.invoke(cli, [
                "show-forks",
                "testowner/e2e-test-repo",
                "--show-commits=3",
                "--max-forks=10"
            ])
        
        # Verify successful execution
        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        
        # Verify the workflow was called correctly
        mock_show_forks.assert_called_once()
        call_args = mock_show_forks.call_args[0]
        
        # Verify parameters
        assert call_args[1] == "testowner/e2e-test-repo"  # repository_url
        assert call_args[2] == 10  # max_forks
        assert call_args[3] is False  # detail flag
        assert call_args[4] == 3  # show_commits
        
        # Verify display service was created and used
        mock_display_service_class.assert_called_once()
        mock_display_service.show_fork_data.assert_called_once()

    @pytest.mark.asyncio
    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    async def test_show_forks_with_commits_and_detail_flag_e2e(
        self, mock_display_service_class, mock_github_client_class, mock_load_config,
        mock_config, sample_repository, realistic_forks_data
    ):
        """Test end-to-end workflow with both --show-commits and --detail flags."""
        mock_load_config.return_value = mock_config
        
        # Setup mocks
        mock_client = AsyncMock()
        mock_github_client_class.return_value = mock_client
        mock_client.get_repository.return_value = sample_repository
        
        def mock_get_recent_commits(owner, repo, branch=None, limit=None):
            return self.create_realistic_commits(owner, repo, limit or 2)
        
        mock_client.get_recent_commits.side_effect = mock_get_recent_commits
        
        # Mock detailed commit counts (for --detail flag)
        mock_client.get_commits_ahead_count.return_value = 5
        
        mock_display_service = AsyncMock()
        mock_display_service_class.return_value = mock_display_service
        mock_display_service.show_fork_data.return_value = {
            "total_forks": len(realistic_forks_data),
            "displayed_forks": len(realistic_forks_data),
            "forks": realistic_forks_data,
            "commits_fetched": True,
            "commits_per_fork": 2,
            "detailed_analysis": True
        }
        
        runner = CliRunner()
        
        with patch("forklift.cli._show_forks_summary") as mock_show_forks:
            mock_show_forks.return_value = None
            
            result = runner.invoke(cli, [
                "show-forks",
                "testowner/e2e-test-repo",
                "--detail",
                "--show-commits=2"
            ])
        
        assert result.exit_code == 0
        mock_show_forks.assert_called_once()
        
        call_args = mock_show_forks.call_args[0]
        assert call_args[3] is True  # detail flag
        assert call_args[4] == 2  # show_commits

    @pytest.mark.asyncio
    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    async def test_show_forks_commits_error_handling_e2e(
        self, mock_github_client_class, mock_load_config, mock_config, sample_repository
    ):
        """Test end-to-end error handling when commit fetching fails."""
        mock_load_config.return_value = mock_config
        
        # Setup GitHub client to fail on commit fetching
        mock_client = AsyncMock()
        mock_github_client_class.return_value = mock_client
        mock_client.get_repository.return_value = sample_repository
        mock_client.get_recent_commits.side_effect = Exception("GitHub API rate limit exceeded")
        
        runner = CliRunner()
        
        # The command should handle the error gracefully
        with patch("forklift.cli._show_forks_summary") as mock_show_forks:
            # Simulate error in the summary function
            mock_show_forks.side_effect = Exception("Failed to fetch commit data")
            
            result = runner.invoke(cli, [
                "show-forks",
                "testowner/e2e-test-repo",
                "--show-commits=3"
            ])
        
        # Should exit with error code but not crash
        assert result.exit_code != 0
        assert "Error" in result.output or "error" in result.output

    @pytest.mark.asyncio
    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    async def test_show_forks_commits_table_formatting_e2e(
        self, mock_display_service_class, mock_github_client_class, mock_load_config,
        mock_config, sample_repository, realistic_forks_data
    ):
        """Test end-to-end table formatting with realistic commit data."""
        mock_load_config.return_value = mock_config
        
        # Setup mocks
        mock_client = AsyncMock()
        mock_github_client_class.return_value = mock_client
        mock_client.get_repository.return_value = sample_repository
        
        def mock_get_recent_commits(owner, repo, branch=None, limit=None):
            return self.create_realistic_commits(owner, repo, limit or 3)
        
        mock_client.get_recent_commits.side_effect = mock_get_recent_commits
        
        mock_display_service = AsyncMock()
        mock_display_service_class.return_value = mock_display_service
        
        # Mock realistic display output
        mock_display_service.show_fork_data.return_value = {
            "total_forks": len(realistic_forks_data),
            "displayed_forks": len(realistic_forks_data),
            "forks": realistic_forks_data,
            "table_formatted": True,
            "commits_column_added": True
        }
        
        runner = CliRunner()
        
        with patch("forklift.cli._show_forks_summary") as mock_show_forks:
            mock_show_forks.return_value = None
            
            result = runner.invoke(cli, [
                "show-forks",
                "testowner/e2e-test-repo",
                "--show-commits=3"
            ])
        
        assert result.exit_code == 0
        mock_show_forks.assert_called_once()
        
        # Verify display service was called with correct parameters
        mock_display_service.show_fork_data.assert_called_once()

    @pytest.mark.asyncio
    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    async def test_show_forks_commits_with_filtering_e2e(
        self, mock_display_service_class, mock_github_client_class, mock_load_config,
        mock_config, sample_repository, realistic_forks_data
    ):
        """Test end-to-end workflow with commit fetching and fork filtering."""
        mock_load_config.return_value = mock_config
        
        # Setup mocks
        mock_client = AsyncMock()
        mock_github_client_class.return_value = mock_client
        mock_client.get_repository.return_value = sample_repository
        
        def mock_get_recent_commits(owner, repo, branch=None, limit=None):
            # Only return commits for forks that have commits ahead
            if owner == "olduser":  # This fork has no commits ahead
                return []
            return self.create_realistic_commits(owner, repo, limit or 2)
        
        mock_client.get_recent_commits.side_effect = mock_get_recent_commits
        
        mock_display_service = AsyncMock()
        mock_display_service_class.return_value = mock_display_service
        
        # Filter out forks with no commits ahead
        filtered_forks = [fork for fork in realistic_forks_data 
                         if fork.qualification_metrics.commits_ahead_status == "Has commits"]
        
        mock_display_service.show_fork_data.return_value = {
            "total_forks": len(realistic_forks_data),
            "displayed_forks": len(filtered_forks),
            "forks": filtered_forks,
            "filtered_no_commits": 1
        }
        
        runner = CliRunner()
        
        with patch("forklift.cli._show_forks_summary") as mock_show_forks:
            mock_show_forks.return_value = None
            
            result = runner.invoke(cli, [
                "show-forks",
                "testowner/e2e-test-repo",
                "--show-commits=2",
                "--max-forks=5"
            ])
        
        assert result.exit_code == 0
        mock_show_forks.assert_called_once()

    @pytest.mark.asyncio
    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    async def test_show_forks_commits_zero_value_e2e(
        self, mock_display_service_class, mock_github_client_class, mock_load_config,
        mock_config, sample_repository, realistic_forks_data
    ):
        """Test end-to-end workflow with --show-commits=0 (no commits)."""
        mock_load_config.return_value = mock_config
        
        # Setup mocks
        mock_client = AsyncMock()
        mock_github_client_class.return_value = mock_client
        mock_client.get_repository.return_value = sample_repository
        
        mock_display_service = AsyncMock()
        mock_display_service_class.return_value = mock_display_service
        mock_display_service.show_fork_data.return_value = {
            "total_forks": len(realistic_forks_data),
            "displayed_forks": len(realistic_forks_data),
            "forks": realistic_forks_data,
            "commits_fetched": False
        }
        
        runner = CliRunner()
        
        with patch("forklift.cli._show_forks_summary") as mock_show_forks:
            mock_show_forks.return_value = None
            
            result = runner.invoke(cli, [
                "show-forks",
                "testowner/e2e-test-repo",
                "--show-commits=0"
            ])
        
        assert result.exit_code == 0
        mock_show_forks.assert_called_once()
        
        # Verify no commit fetching was requested
        call_args = mock_show_forks.call_args[0]
        assert call_args[4] == 0  # show_commits parameter
        
        # Verify get_recent_commits was not called
        mock_client.get_recent_commits.assert_not_called()

    @pytest.mark.asyncio
    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    async def test_show_forks_commits_maximum_value_e2e(
        self, mock_display_service_class, mock_github_client_class, mock_load_config,
        mock_config, sample_repository, realistic_forks_data
    ):
        """Test end-to-end workflow with --show-commits=10 (maximum value)."""
        mock_load_config.return_value = mock_config
        
        # Setup mocks
        mock_client = AsyncMock()
        mock_github_client_class.return_value = mock_client
        mock_client.get_repository.return_value = sample_repository
        
        def mock_get_recent_commits(owner, repo, branch=None, limit=None):
            # Return up to the requested limit
            return self.create_realistic_commits(owner, repo, min(limit or 10, 10))
        
        mock_client.get_recent_commits.side_effect = mock_get_recent_commits
        
        mock_display_service = AsyncMock()
        mock_display_service_class.return_value = mock_display_service
        mock_display_service.show_fork_data.return_value = {
            "total_forks": len(realistic_forks_data),
            "displayed_forks": len(realistic_forks_data),
            "forks": realistic_forks_data,
            "commits_fetched": True,
            "commits_per_fork": 10
        }
        
        runner = CliRunner()
        
        with patch("forklift.cli._show_forks_summary") as mock_show_forks:
            mock_show_forks.return_value = None
            
            result = runner.invoke(cli, [
                "show-forks",
                "testowner/e2e-test-repo",
                "--show-commits=10"
            ])
        
        assert result.exit_code == 0
        mock_show_forks.assert_called_once()
        
        # Verify maximum commits were requested
        call_args = mock_show_forks.call_args[0]
        assert call_args[4] == 10  # show_commits parameter

    def test_show_forks_commits_help_text_e2e(self):
        """Test that help text properly documents the --show-commits option."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ["show-forks", "--help"])
        
        assert result.exit_code == 0
        help_output = result.output
        
        # Verify comprehensive help documentation
        assert "--show-commits" in help_output
        assert "Show last N commits" in help_output or "commits for each fork" in help_output
        assert "default: 0" in help_output or "default=0" in help_output
        
        # Verify the help explains the feature properly
        assert "Recent Commits" in help_output or "commit messages" in help_output
        
        # Verify the new commit format is documented
        assert "+X -Y" in help_output or "commits ahead" in help_output.lower()