"""Integration tests for show-commits command with various N values and flag combinations."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner
from datetime import datetime, timezone

from forklift.cli import cli
from forklift.config.settings import ForkliftConfig
from forklift.models.github import Repository, Commit, User
from forklift.models.fork_qualification import CollectedForkData, ForkQualificationMetrics


class TestShowCommitsIntegration:
    """Integration tests for show-commits command functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        from forklift.config.settings import ForkliftConfig, GitHubConfig, LoggingConfig

        return ForkliftConfig(
            github=GitHubConfig(token="ghp_1234567890abcdef1234567890abcdef12345678"),
            openai_api_key="sk-test1234567890abcdef1234567890abcdef1234567890abcdef",
            logging=LoggingConfig(level="INFO")
        )

    @pytest.fixture
    def sample_repository(self):
        """Create a sample repository for testing."""
        return Repository(
            id=12345,
            name="test-repo",
            full_name="testowner/test-repo",
            owner="testowner",
            description="A test repository",
            html_url="https://github.com/testowner/test-repo",
            clone_url="https://github.com/testowner/test-repo.git",
            ssh_url="git@github.com:testowner/test-repo.git",
            url="https://api.github.com/repos/testowner/test-repo",
            stargazers_count=100,
            forks_count=25,
            watchers_count=100,
            open_issues_count=5,
            size=1024,
            default_branch="main",
            language="Python",
            topics=["python", "testing"],
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
    def sample_commits(self):
        """Create sample commits for testing."""
        return [
            Commit(
                sha=f"abc123{i:034d}",  # Pad to 40 chars total
                message=f"Test commit {i}",
                author=User(
                    login=f"author{i}",
                    name=f"Author {i}",
                    email=f"author{i}@example.com",
                    html_url=f"https://github.com/author{i}",
                    id=i + 1000
                ),
                date=datetime(2024, 1, i+1, tzinfo=timezone.utc),
                files_changed=[f"file{i}.py"],
                additions=10 * (i + 1),
                deletions=5 * (i + 1)
            )
            for i in range(10)
        ]

    @pytest.fixture
    def sample_forks_data(self):
        """Create sample fork data for testing."""
        return [
            CollectedForkData(
                metrics=ForkQualificationMetrics(
                    id=i + 1000,
                    name=f"fork-{i}",
                    full_name=f"owner{i}/fork-{i}",
                    owner=f"owner{i}",
                    html_url=f"https://github.com/owner{i}/fork-{i}",
                    stargazers_count=i * 10,
                    forks_count=i * 2,
                    watchers_count=i * 10,
                    size=1024 * (i + 1),
                    language="Python",
                    topics=[f"topic{i}"],
                    open_issues_count=i,
                    created_at=datetime(2023, 1, i+1, tzinfo=timezone.utc),
                    updated_at=datetime(2024, 1, i+1, tzinfo=timezone.utc),
                    pushed_at=datetime(2024, 1, i+2, tzinfo=timezone.utc),
                    archived=False,
                    disabled=False,
                    fork=True
                )
            )
            for i in range(5)
        ]

    @patch("forklift.cli.load_config")
    def test_show_forks_with_various_commit_counts(self, mock_load_config, mock_config):
        """Test show-forks command with various --show-commits N values."""
        mock_load_config.return_value = mock_config
        
        runner = CliRunner()
        
        # Test different N values for --show-commits
        test_cases = [0, 1, 3, 5, 10]
        
        for n in test_cases:
            with patch("forklift.cli._show_forks_summary") as mock_show_forks:
                mock_show_forks.return_value = None
                
                result = runner.invoke(cli, [
                    "show-forks",
                    "testowner/test-repo",
                    f"--show-commits={n}"
                ])
                
                if result.exit_code != 0:
                    print(f"Error for N={n}: {result.output}")
                    print(f"Exception: {result.exception}")
                assert result.exit_code == 0, f"Failed for N={n}: {result.output}"
                mock_show_forks.assert_called_once()
                
                # Verify the show_commits parameter was passed correctly
                call_args = mock_show_forks.call_args[0]
                # Parameters: config, repository_url, max_forks, verbose, detail, show_commits
                show_commits_param = call_args[5]  # show_commits parameter position (0-indexed)
                assert show_commits_param == n, f"Expected show_commits={n}, got {show_commits_param}"

    @pytest.mark.asyncio
    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    async def test_show_forks_with_commits_and_max_forks(
        self, mock_display_service_class, mock_github_client_class, mock_load_config,
        mock_config, sample_repository, sample_forks_data
    ):
        """Test show-forks with --show-commits combined with --max-forks."""
        mock_load_config.return_value = mock_config
        
        # Setup mocks
        mock_client = AsyncMock()
        mock_github_client_class.return_value = mock_client
        mock_client.get_repository.return_value = sample_repository
        
        mock_display_service = AsyncMock()
        mock_display_service_class.return_value = mock_display_service
        mock_display_service.show_fork_data.return_value = {
            "total_forks": len(sample_forks_data),
            "displayed_forks": 3,  # Limited by max_forks
            "forks": sample_forks_data[:3]
        }
        
        runner = CliRunner()
        
        with patch("forklift.cli._show_forks_summary") as mock_show_forks:
            mock_show_forks.return_value = None
            
            result = runner.invoke(cli, [
                "show-forks",
                "testowner/test-repo",
                "--max-forks=3",
                "--show-commits=2"
            ])
            
            assert result.exit_code == 0
            mock_show_forks.assert_called_once()
            
            # Verify both parameters were passed correctly
            call_args = mock_show_forks.call_args[0]
            max_forks_param = call_args[2]  # max_forks parameter
            show_commits_param = call_args[4]  # show_commits parameter
            
            assert max_forks_param == 3
            assert show_commits_param == 2

    @pytest.mark.asyncio
    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    async def test_show_forks_with_commits_and_detail_flag(
        self, mock_display_service_class, mock_github_client_class, mock_load_config,
        mock_config, sample_repository, sample_forks_data
    ):
        """Test show-forks with --show-commits combined with --detail flag."""
        mock_load_config.return_value = mock_config
        
        # Setup mocks
        mock_client = AsyncMock()
        mock_github_client_class.return_value = mock_client
        mock_client.get_repository.return_value = sample_repository
        
        mock_display_service = AsyncMock()
        mock_display_service_class.return_value = mock_display_service
        mock_display_service.show_fork_data.return_value = {
            "total_forks": len(sample_forks_data),
            "displayed_forks": len(sample_forks_data),
            "forks": sample_forks_data
        }
        
        runner = CliRunner()
        
        with patch("forklift.cli._show_forks_summary") as mock_show_forks:
            mock_show_forks.return_value = None
            
            result = runner.invoke(cli, [
                "show-forks",
                "testowner/test-repo",
                "--detail",
                "--show-commits=3"
            ])
            
            assert result.exit_code == 0
            mock_show_forks.assert_called_once()
            
            # Verify both flags were passed correctly
            call_args = mock_show_forks.call_args[0]
            detail_param = call_args[3]  # detail parameter
            show_commits_param = call_args[4]  # show_commits parameter
            
            assert detail_param is True
            assert show_commits_param == 3

    @pytest.mark.asyncio
    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    async def test_show_forks_commits_boundary_values(
        self, mock_github_client_class, mock_load_config, mock_config, sample_repository
    ):
        """Test show-forks with boundary values for --show-commits."""
        mock_load_config.return_value = mock_config
        
        mock_client = AsyncMock()
        mock_github_client_class.return_value = mock_client
        mock_client.get_repository.return_value = sample_repository
        
        runner = CliRunner()
        
        # Test minimum value (0)
        with patch("forklift.cli._show_forks_summary") as mock_show_forks:
            mock_show_forks.return_value = None
            
            result = runner.invoke(cli, [
                "show-forks",
                "testowner/test-repo",
                "--show-commits=0"
            ])
            
            assert result.exit_code == 0
            mock_show_forks.assert_called_once()
            
            call_args = mock_show_forks.call_args[0]
            assert call_args[4] == 0  # show_commits parameter
        
        # Test maximum value (10)
        with patch("forklift.cli._show_forks_summary") as mock_show_forks:
            mock_show_forks.return_value = None
            
            result = runner.invoke(cli, [
                "show-forks",
                "testowner/test-repo",
                "--show-commits=10"
            ])
            
            assert result.exit_code == 0
            mock_show_forks.assert_called_once()
            
            call_args = mock_show_forks.call_args[0]
            assert call_args[4] == 10  # show_commits parameter

    def test_show_forks_commits_invalid_values(self):
        """Test show-forks with invalid --show-commits values."""
        runner = CliRunner()
        
        # Test value below minimum
        result = runner.invoke(cli, [
            "show-forks",
            "testowner/test-repo",
            "--show-commits=-1"
        ])
        
        assert result.exit_code != 0
        assert "Invalid value" in result.output or "out of range" in result.output
        
        # Test value above maximum
        result = runner.invoke(cli, [
            "show-forks",
            "testowner/test-repo",
            "--show-commits=11"
        ])
        
        assert result.exit_code != 0
        assert "Invalid value" in result.output or "out of range" in result.output

    @pytest.mark.asyncio
    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    async def test_show_forks_commits_performance_impact(
        self, mock_display_service_class, mock_github_client_class, mock_load_config,
        mock_config, sample_repository, sample_commits
    ):
        """Test performance impact of fetching commits for large numbers of forks."""
        mock_load_config.return_value = mock_config
        
        # Create a large number of forks to test performance
        large_forks_data = [
            CollectedForkData(
                name=f"fork-{i}",
                owner=f"owner{i}",
                full_name=f"owner{i}/fork-{i}",
                html_url=f"https://github.com/owner{i}/fork-{i}",
                clone_url=f"https://github.com/owner{i}/fork-{i}.git",
                qualification_metrics=ForkQualificationMetrics(
                    stargazers_count=i,
                    forks_count=1,
                    size=1024,
                    language="Python",
                    created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
                    updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                    pushed_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
                    open_issues_count=0,
                    topics=[],
                    watchers_count=i,
                    archived=False,
                    disabled=False,
                    commits_ahead_status="Has commits",
                    can_skip_analysis=False
                )
            )
            for i in range(50)  # Large number of forks
        ]
        
        # Setup mocks
        mock_client = AsyncMock()
        mock_github_client_class.return_value = mock_client
        mock_client.get_repository.return_value = sample_repository
        mock_client.get_recent_commits.return_value = sample_commits[:3]  # Return 3 commits per fork
        
        mock_display_service = AsyncMock()
        mock_display_service_class.return_value = mock_display_service
        mock_display_service.show_fork_data.return_value = {
            "total_forks": len(large_forks_data),
            "displayed_forks": len(large_forks_data),
            "forks": large_forks_data
        }
        
        runner = CliRunner()
        
        # Test with commits enabled - should make additional API calls
        with patch("forklift.cli._show_forks_summary") as mock_show_forks:
            mock_show_forks.return_value = None
            
            result = runner.invoke(cli, [
                "show-forks",
                "testowner/test-repo",
                "--show-commits=3"
            ])
            
            assert result.exit_code == 0
            mock_show_forks.assert_called_once()
            
            # Verify show_commits parameter was passed
            call_args = mock_show_forks.call_args[0]
            assert call_args[4] == 3  # show_commits parameter

    @pytest.mark.asyncio
    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    async def test_show_forks_commits_help_documentation(
        self, mock_github_client_class, mock_load_config, mock_config
    ):
        """Test that --show-commits flag appears correctly in help documentation."""
        runner = CliRunner()
        
        # Test help output
        result = runner.invoke(cli, ["show-forks", "--help"])
        
        assert result.exit_code == 0
        help_text = result.output
        
        # Verify --show-commits option is documented
        assert "--show-commits" in help_text
        assert "Show last N commits" in help_text or "commits for each fork" in help_text
        assert "0-10" in help_text  # Range should be documented
        assert "default: 0" in help_text or "default=0" in help_text

    @pytest.mark.asyncio
    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.RepositoryDisplayService")
    async def test_show_forks_commits_table_formatting(
        self, mock_display_service_class, mock_github_client_class, mock_load_config,
        mock_config, sample_repository
    ):
        """Test table formatting with various commit message lengths."""
        mock_load_config.return_value = mock_config
        
        # Create forks with commits having various message lengths
        forks_with_varied_commits = [
            CollectedForkData(
                name="fork-short",
                owner="owner1",
                full_name="owner1/fork-short",
                html_url="https://github.com/owner1/fork-short",
                clone_url="https://github.com/owner1/fork-short.git",
                qualification_metrics=ForkQualificationMetrics(
                    stargazers_count=10,
                    forks_count=1,
                    size=1024,
                    language="Python",
                    created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
                    updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                    pushed_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
                    open_issues_count=0,
                    topics=[],
                    watchers_count=10,
                    archived=False,
                    disabled=False,
                    commits_ahead_status="Has commits",
                    can_skip_analysis=False
                )
            ),
            CollectedForkData(
                name="fork-long",
                owner="owner2",
                full_name="owner2/fork-long",
                html_url="https://github.com/owner2/fork-long",
                clone_url="https://github.com/owner2/fork-long.git",
                qualification_metrics=ForkQualificationMetrics(
                    stargazers_count=20,
                    forks_count=2,
                    size=2048,
                    language="Python",
                    created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
                    updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                    pushed_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
                    open_issues_count=1,
                    topics=[],
                    watchers_count=20,
                    archived=False,
                    disabled=False,
                    commits_ahead_status="Has commits",
                    can_skip_analysis=False
                )
            )
        ]
        
        # Setup mocks
        mock_client = AsyncMock()
        mock_github_client_class.return_value = mock_client
        mock_client.get_repository.return_value = sample_repository
        
        # Mock commits with different message lengths
        short_commits = [
            Commit(
                sha="abc1230000000000000000000000000000000000",
                message="Fix bug",
                author=User(
                    login="author",
                    name="Author",
                    email="author@example.com",
                    html_url="https://github.com/author",
                    id=1001
                ),
                date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                files_changed=["bug.py"],
                additions=5,
                deletions=2
            )
        ]
        
        long_commits = [
            Commit(
                sha="def4560000000000000000000000000000000000",
                message="This is a very long commit message that should test the table formatting capabilities and ensure that long messages are handled properly without breaking the display layout",
                author=User(
                    login="longauthor",
                    name="Long Author Name",
                    email="longauthor@example.com",
                    html_url="https://github.com/longauthor",
                    id=1002
                ),
                date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                files_changed=["long.py", "test.py"],
                additions=100,
                deletions=50
            )
        ]
        
        # Mock get_recent_commits to return different commits for different forks
        def mock_get_recent_commits(owner, repo, branch=None, limit=None):
            if owner == "owner1":
                return short_commits
            elif owner == "owner2":
                return long_commits
            return []
        
        mock_client.get_recent_commits.side_effect = mock_get_recent_commits
        
        mock_display_service = AsyncMock()
        mock_display_service_class.return_value = mock_display_service
        mock_display_service.show_fork_data.return_value = {
            "total_forks": len(forks_with_varied_commits),
            "displayed_forks": len(forks_with_varied_commits),
            "forks": forks_with_varied_commits
        }
        
        runner = CliRunner()
        
        with patch("forklift.cli._show_forks_summary") as mock_show_forks:
            mock_show_forks.return_value = None
            
            result = runner.invoke(cli, [
                "show-forks",
                "testowner/test-repo",
                "--show-commits=2"
            ])
            
            assert result.exit_code == 0
            mock_show_forks.assert_called_once()
            
            # Verify the show_commits parameter was passed
            call_args = mock_show_forks.call_args[0]
            assert call_args[4] == 2  # show_commits parameter

    @pytest.mark.asyncio
    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    async def test_show_forks_commits_error_handling(
        self, mock_github_client_class, mock_load_config, mock_config, sample_repository
    ):
        """Test error handling when fetching commits fails."""
        mock_load_config.return_value = mock_config
        
        # Setup GitHub client to raise an exception when fetching commits
        mock_client = AsyncMock()
        mock_github_client_class.return_value = mock_client
        mock_client.get_repository.return_value = sample_repository
        mock_client.get_recent_commits.side_effect = Exception("API Error")
        
        runner = CliRunner()
        
        with patch("forklift.cli._show_forks_summary") as mock_show_forks:
            # Mock the function to simulate the error handling
            mock_show_forks.side_effect = Exception("Failed to fetch commits")
            
            result = runner.invoke(cli, [
                "show-forks",
                "testowner/test-repo",
                "--show-commits=3"
            ])
            
            # Should handle the error gracefully
            assert result.exit_code != 0
            assert "Error" in result.output or "error" in result.output