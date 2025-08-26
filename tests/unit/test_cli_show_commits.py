"""Tests for show-commits CLI command."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from forklift.cli import cli
from forklift.config.settings import ForkliftConfig, GitHubConfig
from forklift.models.github import Commit, Repository, User


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    from forklift.config.settings import AnalysisConfig, CacheConfig, ScoringConfig

    return ForkliftConfig(
        github=GitHubConfig(token="ghp_1234567890abcdef1234567890abcdef12345678"),
        analysis=AnalysisConfig(),
        scoring=ScoringConfig(),
        cache=CacheConfig(),
        output_format="markdown",
        dry_run=False
    )


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    return Repository(
        id=123,
        owner="test-owner",
        name="test-repo",
        full_name="test-owner/test-repo",
        url="https://api.github.com/repos/test-owner/test-repo",
        html_url="https://github.com/test-owner/test-repo",
        clone_url="https://github.com/test-owner/test-repo.git",
        default_branch="main",
        stars=100,
        forks_count=50,
        language="Python",
        description="Test repository"
    )


@pytest.fixture
def mock_commits():
    """Create mock commits."""
    user1 = User(
        id=1,
        login="author1",
        html_url="https://github.com/author1"
    )

    user2 = User(
        id=2,
        login="author2",
        html_url="https://github.com/author2"
    )

    return [
        Commit(
            sha="a" * 40,
            message="feat: add new authentication system",
            author=user1,
            date=datetime(2024, 1, 15, 10, 30),
            additions=150,
            deletions=20,
            files_changed=["src/auth.py", "tests/test_auth.py", "docs/auth.md"],
            parents=["b" * 40]
        ),
        Commit(
            sha="b" * 40,
            message="fix: resolve memory leak in data processing",
            author=user2,
            date=datetime(2024, 1, 14, 14, 15),
            additions=5,
            deletions=3,
            files_changed=["src/processor.py"],
            parents=["c" * 40]
        ),
        Commit(
            sha="c" * 40,
            message="docs: update installation instructions",
            author=user1,
            date=datetime(2024, 1, 13, 9, 45),
            additions=25,
            deletions=5,
            files_changed=["README.md", "docs/install.md"],
            parents=["d" * 40]
        ),
        Commit(
            sha="d" * 40,
            message="Merge pull request #123 from feature/new-ui",
            author=user1,
            date=datetime(2024, 1, 12, 16, 20),
            additions=200,
            deletions=50,
            files_changed=["src/ui.py", "src/components.py"],
            parents=["e" * 40, "f" * 40],  # Merge commit has multiple parents
            is_merge=True
        ),
        Commit(
            sha="e" * 40,
            message="test: add comprehensive unit tests for API",
            author=user2,
            date=datetime(2024, 1, 11, 11, 0),
            additions=300,
            deletions=0,
            files_changed=["tests/test_api.py", "tests/fixtures.py"],
            parents=["g" * 40]
        )
    ]


@pytest.fixture
def mock_commits_data(mock_commits):
    """Create mock commits data as returned by GitHub API."""
    commits_data = []
    for commit in mock_commits:
        commit_data = {
            "sha": commit.sha,
            "commit": {
                "message": commit.message,
                "author": {
                    "name": commit.author.login,
                    "email": f"{commit.author.login}@example.com",
                    "date": commit.date.isoformat() + "Z"
                },
                "committer": {
                    "name": commit.author.login,
                    "email": f"{commit.author.login}@example.com",
                    "date": commit.date.isoformat() + "Z"
                }
            },
            "author": {
                "login": commit.author.login,
                "id": commit.author.id,
                "html_url": commit.author.html_url
            },
            "stats": {
                "additions": commit.additions,
                "deletions": commit.deletions,
                "total": commit.total_changes
            },
            "files": [{"filename": f} for f in commit.files_changed],
            "parents": [{"sha": p} for p in commit.parents]
        }
        commits_data.append(commit_data)

    return commits_data


class TestShowCommitsCommand:
    """Test cases for show-commits command."""

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.validate_repository_url")
    def test_show_commits_basic(self, mock_validate_url, mock_client_class, mock_load_config,
                               mock_config, mock_repository, mock_commits_data):
        """Test basic show-commits command execution."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("test-owner", "test-repo")

        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get_repository.return_value = mock_repository
        mock_client.get_branch_commits.return_value = mock_commits_data

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, ["show-commits", "test-owner/test-repo"])

        # Assertions
        assert result.exit_code == 0
        mock_client.get_repository.assert_called_once_with("test-owner", "test-repo")
        mock_client.get_branch_commits.assert_called_once()

        # Check that output contains expected elements
        assert "Commits from test-owner/test-repo" in result.output
        assert "feat: add new authentication system" in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.validate_repository_url")
    def test_show_commits_with_branch(self, mock_validate_url, mock_client_class, mock_load_config,
                                     mock_config, mock_repository, mock_commits_data):
        """Test show-commits command with specific branch."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("test-owner", "test-repo")

        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get_repository.return_value = mock_repository
        mock_client.get_branch_commits.return_value = mock_commits_data

        # Run command with branch option
        runner = CliRunner()
        result = runner.invoke(cli, ["show-commits", "test-owner/test-repo", "--branch", "feature-branch"])

        # Assertions
        assert result.exit_code == 0

        # Check that the client was called with the correct branch
        call_args = mock_client.get_branch_commits.call_args
        assert call_args[0][2] == "feature-branch"  # Third argument should be the branch

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.validate_repository_url")
    def test_show_commits_with_limit(self, mock_validate_url, mock_client_class, mock_load_config,
                                    mock_config, mock_repository, mock_commits_data):
        """Test show-commits command with limit option."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("test-owner", "test-repo")

        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get_repository.return_value = mock_repository
        mock_client.get_branch_commits.return_value = mock_commits_data[:3]  # Return limited commits

        # Run command with limit
        runner = CliRunner()
        result = runner.invoke(cli, ["show-commits", "test-owner/test-repo", "--limit", "3"])

        # Assertions
        assert result.exit_code == 0

        # Check that max_count parameter was set correctly
        call_args = mock_client.get_branch_commits.call_args
        assert call_args[1]["max_count"] == 6  # Should be limit * 2 for filtering

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.validate_repository_url")
    def test_show_commits_with_author_filter(self, mock_validate_url, mock_client_class, mock_load_config,
                                            mock_config, mock_repository, mock_commits_data):
        """Test show-commits command with author filter."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("test-owner", "test-repo")

        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get_repository.return_value = mock_repository
        mock_client.get_branch_commits.return_value = mock_commits_data

        # Run command with author filter
        runner = CliRunner()
        result = runner.invoke(cli, ["show-commits", "test-owner/test-repo", "--author", "author1"])

        # Assertions
        assert result.exit_code == 0

        # Should only show commits from author1
        assert "author1" in result.output
        # Should not show commits from author2 (they should be filtered out)
        lines_with_author2 = [line for line in result.output.split("\n") if "author2" in line]
        # author2 might appear in the table header or other places, but not in commit rows
        commit_lines_with_author2 = [line for line in lines_with_author2 if "fix: resolve memory leak" in line]
        assert len(commit_lines_with_author2) == 0

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.validate_repository_url")
    def test_show_commits_exclude_merge(self, mock_validate_url, mock_client_class, mock_load_config,
                                       mock_config, mock_repository, mock_commits_data):
        """Test show-commits command excluding merge commits by default."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("test-owner", "test-repo")

        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get_repository.return_value = mock_repository
        mock_client.get_branch_commits.return_value = mock_commits_data

        # Run command (merge commits excluded by default)
        runner = CliRunner()
        result = runner.invoke(cli, ["show-commits", "test-owner/test-repo"])

        # Assertions
        assert result.exit_code == 0

        # Should not show merge commit
        assert "Merge pull request" not in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.validate_repository_url")
    def test_show_commits_include_merge(self, mock_validate_url, mock_client_class, mock_load_config,
                                       mock_config, mock_repository, mock_commits_data):
        """Test show-commits command including merge commits."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("test-owner", "test-repo")

        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get_repository.return_value = mock_repository
        mock_client.get_branch_commits.return_value = mock_commits_data

        # Run command with include-merge flag
        runner = CliRunner()
        result = runner.invoke(cli, ["show-commits", "test-owner/test-repo", "--include-merge"])

        # Assertions
        assert result.exit_code == 0

        # Should show merge commit
        assert "Merge pull request" in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.validate_repository_url")
    def test_show_commits_with_date_filters(self, mock_validate_url, mock_client_class, mock_load_config,
                                           mock_config, mock_repository, mock_commits_data):
        """Test show-commits command with date filters."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("test-owner", "test-repo")

        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get_repository.return_value = mock_repository
        mock_client.get_branch_commits.return_value = mock_commits_data

        # Run command with date filters
        runner = CliRunner()
        result = runner.invoke(cli, [
            "show-commits", "test-owner/test-repo",
            "--since", "2024-01-13",
            "--until", "2024-01-15"
        ])

        # Assertions
        assert result.exit_code == 0

        # Should only show commits within date range
        # Commits from 2024-01-13 to 2024-01-15 should be included
        assert "feat: add new authentication system" in result.output  # 2024-01-15
        assert "docs: update installation instructions" in result.output  # 2024-01-13

        # Commit from 2024-01-11 should be excluded
        assert "test: add comprehensive unit tests" not in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.validate_repository_url")
    def test_show_commits_with_files_and_stats(self, mock_validate_url, mock_client_class, mock_load_config,
                                              mock_config, mock_repository, mock_commits_data):
        """Test show-commits command with file changes and statistics."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("test-owner", "test-repo")

        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get_repository.return_value = mock_repository
        mock_client.get_branch_commits.return_value = mock_commits_data

        # Run command with files and stats options
        runner = CliRunner()
        result = runner.invoke(cli, [
            "show-commits", "test-owner/test-repo",
            "--show-files",
            "--show-stats"
        ])

        # Assertions
        assert result.exit_code == 0

        # Should show file changes
        assert "src/auth.py" in result.output
        assert "tests/test_auth.py" in result.output

        # Should show detailed statistics
        assert "Detailed Statistics" in result.output
        assert "Total Lines Added" in result.output
        assert "Top Contributors" in result.output

    @patch("forklift.cli.load_config")
    def test_show_commits_no_token(self, mock_load_config):
        """Test show-commits command without GitHub token."""
        from forklift.config.settings import AnalysisConfig, CacheConfig, ScoringConfig

        # Setup config without token
        config = ForkliftConfig(
            github=GitHubConfig(token=None),
            analysis=AnalysisConfig(),
            scoring=ScoringConfig(),
            cache=CacheConfig(),
            output_format="markdown",
            dry_run=False
        )
        mock_load_config.return_value = config

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, ["show-commits", "test-owner/test-repo"])

        # Assertions
        assert result.exit_code == 1
        assert "GitHub token not configured" in result.output

    def test_show_commits_invalid_date_format(self):
        """Test show-commits command with invalid date format."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "show-commits", "test-owner/test-repo",
            "--since", "invalid-date"
        ])

        # Should fail with date format error
        assert result.exit_code == 1
        assert "Invalid since date format" in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.validate_repository_url")
    def test_show_commits_api_error(self, mock_validate_url, mock_client_class, mock_load_config, mock_config):
        """Test show-commits command with API error."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("test-owner", "test-repo")

        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get_repository.side_effect = Exception("API Error")

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, ["show-commits", "test-owner/test-repo"])

        # Assertions
        assert result.exit_code == 1
        assert "Failed to show commits" in result.output

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.validate_repository_url")
    def test_show_commits_no_commits_found(self, mock_validate_url, mock_client_class, mock_load_config,
                                          mock_config, mock_repository):
        """Test show-commits command when no commits are found."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("test-owner", "test-repo")

        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get_repository.return_value = mock_repository
        mock_client.get_branch_commits.return_value = []  # No commits

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, ["show-commits", "test-owner/test-repo"])

        # Assertions
        assert result.exit_code == 0
        assert "No commits found matching the criteria" in result.output


class TestShowCommitsHelpers:
    """Test helper functions for show-commits command."""

    @patch("forklift.cli.console")
    def test_display_commits_table_with_data(self, mock_console, mock_commits, mock_repository):
        """Test commits table display with data."""
        from forklift.cli import _display_commits_table

        # Should not raise any exceptions
        _display_commits_table(mock_commits, mock_repository, "main", False, False)

        # Check that console.print was called
        assert mock_console.print.called

    @patch("forklift.cli.console")
    def test_display_commit_statistics_with_data(self, mock_console, mock_commits):
        """Test commit statistics display with data."""
        from forklift.cli import _display_commit_statistics

        # Should not raise any exceptions
        _display_commit_statistics(mock_commits)

        # Check that console.print was called
        assert mock_console.print.called

    @patch("forklift.cli.console")
    def test_display_file_changes_with_data(self, mock_console, mock_commits):
        """Test file changes display with data."""
        from forklift.cli import _display_file_changes

        # Should not raise any exceptions
        _display_file_changes(mock_commits)

        # Check that console.print was called
        assert mock_console.print.called

    def test_commit_filtering_by_author(self, mock_commits):
        """Test commit filtering by author logic."""
        # Filter commits by author1
        author1_commits = [c for c in mock_commits if c.author.login == "author1"]

        # Should have 3 commits from author1
        assert len(author1_commits) == 3

        # Filter commits by author2
        author2_commits = [c for c in mock_commits if c.author.login == "author2"]

        # Should have 2 commits from author2
        assert len(author2_commits) == 2

    def test_commit_filtering_by_merge_status(self, mock_commits):
        """Test commit filtering by merge status."""
        # Filter out merge commits
        non_merge_commits = [c for c in mock_commits if not c.is_merge]

        # Should have 4 non-merge commits (all except the merge commit)
        assert len(non_merge_commits) == 4

        # Filter only merge commits
        merge_commits = [c for c in mock_commits if c.is_merge]

        # Should have 1 merge commit
        assert len(merge_commits) == 1
        assert "Merge pull request" in merge_commits[0].message

    def test_commit_filtering_by_date(self, mock_commits):
        """Test commit filtering by date."""
        since_date = datetime(2024, 1, 13)
        until_date = datetime(2024, 1, 15)

        # Filter commits within date range
        filtered_commits = [
            c for c in mock_commits
            if since_date <= c.date.replace(tzinfo=None) <= until_date
        ]

        # Should have 2 commits within the date range (2024-01-13 to 2024-01-15)
        assert len(filtered_commits) == 2


class TestShowCommitsIntegration:
    """Integration tests for show-commits command."""

    @patch("forklift.cli.load_config")
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.validate_repository_url")
    def test_show_commits_full_workflow(self, mock_validate_url, mock_client_class, mock_load_config,
                                       mock_config, mock_repository, mock_commits_data):
        """Test complete show-commits workflow."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("test-owner", "test-repo")

        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get_repository.return_value = mock_repository
        mock_client.get_branch_commits.return_value = mock_commits_data

        # Run command with all options
        runner = CliRunner()
        result = runner.invoke(cli, [
            "show-commits", "test-owner/test-repo",
            "--branch", "main",
            "--limit", "10",
            "--author", "author1",
            "--include-merge",
            "--show-files",
            "--show-stats",
            "--verbose"
        ])

        # Assertions
        assert result.exit_code == 0

        # Verify all components were called
        mock_validate_url.assert_called_once_with("test-owner/test-repo")
        mock_client.get_repository.assert_called_once_with("test-owner", "test-repo")
        mock_client.get_branch_commits.assert_called_once()

        # Check output contains expected sections
        assert "Commits from test-owner/test-repo" in result.output
        assert "Detailed Statistics" in result.output
        assert "File Changes" in result.output
        assert "displayed successfully" in result.output
