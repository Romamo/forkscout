"""Unit tests for show-commits command with fork filtering logic."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

from forklift.cli import _show_commits, CLIError
from forklift.config.settings import ForkliftConfig
from forklift.models.github import Repository
from forklift.models.fork_qualification import ForkQualificationMetrics, CollectedForkData, QualifiedForksResult, QualificationStats


def create_mock_config():
    """Create a properly mocked ForkliftConfig for testing."""
    mock_config = Mock()
    mock_config.github = Mock()
    mock_config.github.token = "ghp_1234567890abcdef1234567890abcdef12345678"
    return mock_config


def create_mock_repository(has_commits_ahead=True):
    """Create a mock repository for testing."""
    created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
    pushed_at = datetime(2023, 6, 1, tzinfo=timezone.utc) if has_commits_ahead else created_at
    
    return Repository(
        owner="testowner",
        name="testrepo",
        full_name="testowner/testrepo",
        url="https://api.github.com/repos/testowner/testrepo",
        html_url="https://github.com/testowner/testrepo",
        clone_url="https://github.com/testowner/testrepo.git",
        created_at=created_at,
        pushed_at=pushed_at,
        default_branch="main"
    )


def create_mock_qualification_result(has_commits_ahead=True):
    """Create a mock qualification result for testing."""
    created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
    pushed_at = datetime(2023, 6, 1, tzinfo=timezone.utc) if has_commits_ahead else created_at
    
    metrics = ForkQualificationMetrics(
        id=12345,
        full_name="testowner/testrepo",
        owner="testowner",
        name="testrepo",
        html_url="https://github.com/testowner/testrepo",
        stargazers_count=10,
        forks_count=5,
        size=1000,
        language="Python",
        created_at=created_at,
        updated_at=pushed_at,
        pushed_at=pushed_at,
        open_issues_count=2,
        topics=["python", "test"],
        watchers_count=8,
        archived=False,
        disabled=False,
        fork=True
    )
    
    fork_data = CollectedForkData(metrics=metrics)
    
    stats = QualificationStats(
        total_forks_discovered=1,
        forks_with_no_commits=0 if has_commits_ahead else 1,
        forks_with_commits=1 if has_commits_ahead else 0,
        api_calls_made=1,
        processing_time_seconds=1.0
    )
    
    return QualifiedForksResult(
        repository_owner="upstream",
        repository_name="repo",
        repository_url="https://github.com/upstream/repo",
        collected_forks=[fork_data],
        stats=stats
    )


class TestShowCommitsForkFiltering:
    """Test fork filtering logic in show-commits command."""

    @pytest.mark.asyncio
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.validate_repository_url")
    @patch("forklift.cli.console")
    async def test_show_commits_detail_with_no_commits_ahead_skips_analysis(
        self, mock_console, mock_validate_url, mock_github_client_class
    ):
        """Test that show-commits --detail skips analysis for forks with no commits ahead."""
        # Setup mocks
        config = create_mock_config()
        mock_validate_url.return_value = ("testowner", "testrepo")
        
        # Create GitHub client mock
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client
        
        # Mock repository with no commits ahead
        mock_repo = create_mock_repository(has_commits_ahead=False)
        mock_github_client.get_repository.return_value = mock_repo
        
        # Mock qualification result with no commits ahead
        mock_qualification_result = create_mock_qualification_result(has_commits_ahead=False)
        
        with patch("forklift.analysis.fork_qualification_lookup.ForkQualificationLookup") as mock_lookup_class, \
             patch("forklift.analysis.fork_commit_status_checker.ForkCommitStatusChecker") as mock_checker_class, \
             patch("forklift.storage.analysis_cache.AnalysisCacheManager") as mock_cache_class, \
             patch("forklift.cli._get_parent_repository_url") as mock_get_parent:
            
            # Setup mocks
            mock_cache = AsyncMock()
            mock_cache_class.return_value = mock_cache
            
            mock_lookup = AsyncMock()
            mock_lookup.get_fork_qualification_data.return_value = mock_qualification_result
            mock_lookup_class.return_value = mock_lookup
            
            mock_checker = AsyncMock()
            mock_checker.has_commits_ahead.return_value = False  # No commits ahead
            mock_checker_class.return_value = mock_checker
            
            mock_get_parent.return_value = "https://github.com/upstream/repo"
            
            # Call the function
            await _show_commits(
                config=config,
                fork_url="testowner/testrepo",
                branch=None,
                limit=20,
                since_date=None,
                until_date=None,
                author=None,
                include_merge=False,
                show_files=False,
                show_stats=False,
                verbose=False,
                explain=False,
                ai_summary=False,
                ai_summary_compact=False,
                detail=True,  # Enable detail mode
                force=False,  # Don't force analysis
                disable_cache=False
            )
            
            # Verify that the function returned early with appropriate message
            mock_console.print.assert_any_call("[yellow]Fork has no commits ahead of upstream - skipping detailed analysis[/yellow]")
            mock_console.print.assert_any_call("[dim]Use --force flag to analyze anyway[/dim]")
            
            # Verify that commit fetching was not attempted
            mock_github_client.get_branch_commits.assert_not_called()
            mock_github_client.get_repository_commits.assert_not_called()

    @pytest.mark.asyncio
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.validate_repository_url")
    @patch("forklift.cli.Progress")
    @patch("forklift.cli._display_commits_table")
    async def test_show_commits_without_detail_flag_skips_filtering(
        self, mock_display_table, mock_progress_class, mock_validate_url, mock_github_client_class
    ):
        """Test that show-commits without --detail flag skips fork filtering."""
        # Setup mocks
        config = create_mock_config()
        mock_validate_url.return_value = ("testowner", "testrepo")
        
        # Create GitHub client mock
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client
        
        # Mock repository with no commits ahead
        mock_repo = create_mock_repository(has_commits_ahead=False)
        mock_github_client.get_repository.return_value = mock_repo
        mock_github_client.get_branch_commits.return_value = []
        
        # Mock progress
        mock_progress = Mock()
        mock_task = Mock()
        mock_progress.add_task.return_value = mock_task
        mock_progress_class.return_value.__enter__.return_value = mock_progress
        
        # Call the function without detail flag
        await _show_commits(
            config=config,
            fork_url="testowner/testrepo",
            branch=None,
            limit=20,
            since_date=None,
            until_date=None,
            author=None,
            include_merge=False,
            show_files=False,
            show_stats=False,
            verbose=False,
            explain=False,
            ai_summary=False,
            ai_summary_compact=False,
            detail=False,  # Disable detail mode
            force=False,
            disable_cache=False
        )
        
        # Verify that commit fetching was attempted (no filtering applied)
        mock_github_client.get_branch_commits.assert_called_once()
        
        # Verify that display was called
        mock_display_table.assert_called_once()

    @pytest.mark.asyncio
    @patch("forklift.cli.GitHubClient")
    @patch("forklift.cli.validate_repository_url")
    @patch("forklift.cli.console")
    @patch("forklift.cli.Progress")
    @patch("forklift.cli._display_detailed_commits")
    async def test_show_commits_detail_with_force_flag_bypasses_filtering(
        self, mock_display_detailed, mock_progress_class, mock_console, mock_validate_url, mock_github_client_class
    ):
        """Test that show-commits --detail --force bypasses fork filtering."""
        # Setup mocks
        config = create_mock_config()
        mock_validate_url.return_value = ("testowner", "testrepo")
        
        # Create GitHub client mock
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client
        
        # Mock repository with no commits ahead
        mock_repo = create_mock_repository(has_commits_ahead=False)
        mock_github_client.get_repository.return_value = mock_repo
        
        # Mock commits data
        mock_commits_data = [
            {
                "sha": "abc123",
                "commit": {
                    "message": "test commit",
                    "author": {"name": "test", "date": "2023-01-01T00:00:00Z"}
                },
                "author": {"login": "test", "id": 123},
                "stats": {"additions": 1, "deletions": 0},
                "files": [{"filename": "test.py"}]
            }
        ]
        mock_github_client.get_branch_commits.return_value = mock_commits_data
        
        # Mock progress
        mock_progress = Mock()
        mock_task = Mock()
        mock_progress.add_task.return_value = mock_task
        mock_progress_class.return_value.__enter__.return_value = mock_progress
        
        with patch("forklift.cli.Commit") as mock_commit_class:
            # Mock Commit.from_github_api
            mock_commit = Mock()
            mock_commit.is_merge = False
            mock_commit.author = Mock()
            mock_commit.author.login = "test"
            mock_commit.date = datetime(2023, 1, 1, tzinfo=timezone.utc)
            mock_commit_class.from_github_api.return_value = mock_commit
            
            # Call the function with force=True
            await _show_commits(
                config=config,
                fork_url="testowner/testrepo",
                branch=None,
                limit=20,
                since_date=None,
                until_date=None,
                author=None,
                include_merge=False,
                show_files=False,
                show_stats=False,
                verbose=False,
                explain=False,
                ai_summary=False,
                ai_summary_compact=False,
                detail=True,  # Enable detail mode
                force=True,   # Force analysis
                disable_cache=False
            )
            
            # Verify that fork filtering was bypassed (no filtering messages)
            # The function should not print filtering messages when force=True
            filtering_calls = [call for call in mock_console.print.call_args_list 
                             if "Fork has no commits ahead" in str(call)]
            assert len(filtering_calls) == 0
            
            # Verify that commit fetching was attempted despite no commits ahead
            mock_github_client.get_branch_commits.assert_called_once()
            
            # Verify that detailed display was called
            mock_display_detailed.assert_called_once()