"""Integration tests for show-commits command with fork qualification data."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from forklift.cli import _show_commits, _get_parent_repository_url
from forklift.config.settings import ForkliftConfig
from forklift.github.client import GitHubClient
from forklift.models.github import Repository, Commit, User
from forklift.models.fork_qualification import (
    QualifiedForksResult,
    CollectedForkData,
    ForkQualificationMetrics,
    QualificationStats,
)


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = MagicMock()
    config.github = MagicMock()
    config.github.token = "test-token"
    return config


@pytest.fixture
def sample_repository():
    """Create a sample repository."""
    return Repository(
        id=123,
        name="test-repo",
        full_name="test-owner/test-repo",
        owner="test-owner",
        url="https://api.github.com/repos/test-owner/test-repo",
        html_url="https://github.com/test-owner/test-repo",
        clone_url="https://github.com/test-owner/test-repo.git",
        default_branch="main",
        is_fork=True,
    )


@pytest.fixture
def sample_fork_metrics():
    """Create sample fork qualification metrics."""
    return ForkQualificationMetrics(
        id=123,
        name="test-repo",
        full_name="test-owner/test-repo",
        owner="test-owner",
        html_url="https://github.com/test-owner/test-repo",
        stargazers_count=5,
        forks_count=1,
        watchers_count=5,
        size=1000,
        language="Python",
        topics=["test"],
        open_issues_count=2,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 15, 12, 0, 0),
        pushed_at=datetime(2024, 1, 10, 12, 0, 0),  # pushed_at > created_at = has commits
        archived=False,
        disabled=False,
        fork=True,
        license_key="mit",
        license_name="MIT License",
        description="Test fork repository",
        homepage="https://example.com",
        default_branch="main",
    )


@pytest.fixture
def sample_qualification_result(sample_fork_metrics):
    """Create sample qualification result."""
    collected_fork = CollectedForkData(
        metrics=sample_fork_metrics,
        collection_timestamp=datetime.utcnow(),
        exact_commits_ahead="Unknown",
    )

    stats = QualificationStats(
        total_forks_discovered=1,
        forks_with_no_commits=0,
        forks_with_commits=1,
        archived_forks=0,
        disabled_forks=0,
        api_calls_made=5,
        api_calls_saved=3,
        processing_time_seconds=2.5,
        collection_timestamp=datetime.utcnow(),
    )

    return QualifiedForksResult(
        repository_owner="parent-owner",
        repository_name="parent-repo",
        repository_url="https://github.com/parent-owner/parent-repo",
        collected_forks=[collected_fork],
        stats=stats,
        qualification_timestamp=datetime.utcnow(),
    )


@pytest.fixture
def sample_commits():
    """Create sample commits."""
    user = User(id=1, login="test-user", avatar_url="https://example.com/avatar.jpg", html_url="https://github.com/test-user")
    
    return [
        Commit(
            sha="abc1234567890abcdef1234567890abcdef12345",
            message="Add new feature",
            author=user,
            date=datetime(2024, 1, 15, 10, 0, 0),
        ),
        Commit(
            sha="def4567890abcdef1234567890abcdef12345678",
            message="Fix bug in feature",
            author=user,
            date=datetime(2024, 1, 14, 10, 0, 0),
        ),
    ]


class TestShowCommitsQualificationIntegration:
    """Integration tests for show-commits command with qualification data."""

    @pytest.mark.asyncio
    async def test_get_parent_repository_url_for_fork(self, sample_repository):
        """Test getting parent repository URL for a fork."""
        # Setup
        mock_github_client = AsyncMock(spec=GitHubClient)
        mock_github_client.get.return_value = {
            "fork": True,
            "parent": {
                "html_url": "https://github.com/parent-owner/parent-repo"
            }
        }
        
        # Test
        parent_url = await _get_parent_repository_url(
            mock_github_client, "https://github.com/test-owner/test-repo"
        )
        
        # Verify
        assert parent_url == "https://github.com/parent-owner/parent-repo"
        mock_github_client.get.assert_called_once_with("repos/test-owner/test-repo")

    @pytest.mark.asyncio
    async def test_get_parent_repository_url_for_non_fork(self):
        """Test getting parent repository URL for a non-fork."""
        # Setup
        mock_github_client = AsyncMock(spec=GitHubClient)
        mock_github_client.get.return_value = {
            "fork": False
        }
        
        # Test
        parent_url = await _get_parent_repository_url(
            mock_github_client, "https://github.com/test-owner/test-repo"
        )
        
        # Verify - should return the same URL for non-forks
        assert parent_url == "https://github.com/test-owner/test-repo"

    @pytest.mark.asyncio
    async def test_get_parent_repository_url_error_handling(self):
        """Test error handling in getting parent repository URL."""
        # Setup
        mock_github_client = AsyncMock(spec=GitHubClient)
        mock_github_client.get.side_effect = Exception("API error")
        
        # Test
        parent_url = await _get_parent_repository_url(
            mock_github_client, "https://github.com/test-owner/test-repo"
        )
        
        # Verify - should return None on error
        assert parent_url is None

    @pytest.mark.asyncio
    async def test_show_commits_with_qualification_data_has_commits(
        self, mock_config, sample_repository, sample_qualification_result, sample_commits
    ):
        """Test show-commits command using qualification data when fork has commits ahead."""
        # Setup mocks
        with patch('forklift.cli.GitHubClient') as mock_client_class, \
             patch('forklift.cli.AnalysisCacheManager') as mock_cache_class, \
             patch('forklift.cli.ForkQualificationLookup') as mock_lookup_class, \
             patch('forklift.cli.ForkCommitStatusChecker') as mock_checker_class, \
             patch('forklift.cli._display_commits_table') as mock_display, \
             patch('forklift.cli.validate_repository_url') as mock_validate, \
             patch('forklift.cli._get_parent_repository_url') as mock_get_parent:

            # Configure mocks
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get_repository.return_value = sample_repository
            mock_client.get_branch_commits.return_value = [
                {
                    'sha': 'abc123',
                    'commit': {
                        'message': 'Add new feature',
                        'author': {'name': 'Test User', 'email': 'test@example.com', 'date': '2024-01-15T10:00:00Z'},
                        'committer': {'name': 'Test User', 'email': 'test@example.com', 'date': '2024-01-15T10:00:00Z'},
                    },
                    'author': {'login': 'test-user', 'id': 1, 'avatar_url': 'https://example.com/avatar.jpg'},
                    'html_url': 'https://github.com/test-owner/test-repo/commit/abc123',
                    'url': 'https://api.github.com/repos/test-owner/test-repo/commits/abc123',
                }
            ]

            mock_cache = AsyncMock()
            mock_cache_class.return_value = mock_cache

            mock_lookup = AsyncMock()
            mock_lookup_class.return_value = mock_lookup
            mock_lookup.get_fork_qualification_data.return_value = sample_qualification_result

            mock_checker = AsyncMock()
            mock_checker_class.return_value = mock_checker
            mock_checker.has_commits_ahead.return_value = True  # Fork has commits ahead

            mock_validate.return_value = ("test-owner", "test-repo")
            mock_get_parent.return_value = "https://github.com/parent-owner/parent-repo"

            # Test
            await _show_commits(
                config=mock_config,
                fork_url="https://github.com/test-owner/test-repo",
                branch=None,
                limit=20,
                since_date=None,
                until_date=None,
                author=None,
                include_merge=False,
                show_files=False,
                show_stats=False,
                verbose=True,
                explain=False,
                ai_summary=False,
                ai_summary_compact=False,
                detail=True,  # Enable detail mode to trigger qualification lookup
                force=False,
                disable_cache=False,
            )

            # Verify qualification data was used
            mock_lookup.get_fork_qualification_data.assert_called_once_with(
                "https://github.com/parent-owner/parent-repo", False
            )
            mock_checker.has_commits_ahead.assert_called_once_with(
                "https://github.com/test-owner/test-repo", sample_qualification_result
            )
            
            # Verify commits were displayed (not skipped)
            mock_display.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_commits_with_qualification_data_no_commits(
        self, mock_config, sample_repository, sample_qualification_result
    ):
        """Test show-commits command using qualification data when fork has no commits ahead."""
        # Modify qualification result to indicate no commits ahead
        sample_qualification_result.collected_forks[0].metrics.pushed_at = datetime(2024, 1, 1, 11, 0, 0)  # Before created_at
        
        # Setup mocks
        with patch('forklift.cli.GitHubClient') as mock_client_class, \
             patch('forklift.cli.AnalysisCacheManager') as mock_cache_class, \
             patch('forklift.analysis.fork_qualification_lookup.ForkQualificationLookup') as mock_lookup_class, \
             patch('forklift.cli.ForkCommitStatusChecker') as mock_checker_class, \
             patch('forklift.cli._display_commits_table') as mock_display, \
             patch('forklift.cli.validate_repository_url') as mock_validate, \
             patch('forklift.cli._get_parent_repository_url') as mock_get_parent, \
             patch('forklift.cli.console') as mock_console:

            # Configure mocks
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_cache = AsyncMock()
            mock_cache_class.return_value = mock_cache

            mock_lookup = AsyncMock()
            mock_lookup_class.return_value = mock_lookup
            mock_lookup.get_fork_qualification_data.return_value = sample_qualification_result

            mock_checker = AsyncMock()
            mock_checker_class.return_value = mock_checker
            mock_checker.has_commits_ahead.return_value = False  # Fork has no commits ahead

            mock_validate.return_value = ("test-owner", "test-repo")
            mock_get_parent.return_value = "https://github.com/parent-owner/parent-repo"

            # Test
            await _show_commits(
                config=mock_config,
                fork_url="https://github.com/test-owner/test-repo",
                branch=None,
                limit=20,
                since_date=None,
                until_date=None,
                author=None,
                include_merge=False,
                show_files=False,
                show_stats=False,
                verbose=True,
                explain=False,
                ai_summary=False,
                ai_summary_compact=False,
                detail=True,  # Enable detail mode to trigger qualification lookup
                force=False,
                disable_cache=False,
            )

            # Verify qualification data was used
            mock_lookup.get_fork_qualification_data.assert_called_once()
            mock_checker.has_commits_ahead.assert_called_once_with(
                "https://github.com/test-owner/test-repo", sample_qualification_result
            )
            
            # Verify early return message was displayed
            mock_console.print.assert_any_call(
                "[yellow]Fork has no commits ahead of upstream - skipping detailed analysis[/yellow]"
            )
            
            # Verify commits were not displayed (skipped)
            mock_display.assert_not_called()

    @pytest.mark.asyncio
    async def test_show_commits_with_force_flag_overrides_qualification(
        self, mock_config, sample_repository, sample_qualification_result, sample_commits
    ):
        """Test that --force flag overrides qualification data filtering."""
        # Modify qualification result to indicate no commits ahead
        sample_qualification_result.collected_forks[0].metrics.pushed_at = datetime(2024, 1, 1, 11, 0, 0)
        
        # Setup mocks
        with patch('forklift.cli.GitHubClient') as mock_client_class, \
             patch('forklift.cli._display_commits_table') as mock_display, \
             patch('forklift.cli.validate_repository_url') as mock_validate:

            # Configure mocks
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get_repository.return_value = sample_repository
            mock_client.get_branch_commits.return_value = [
                {
                    'sha': 'abc123',
                    'commit': {
                        'message': 'Add new feature',
                        'author': {'name': 'Test User', 'email': 'test@example.com', 'date': '2024-01-15T10:00:00Z'},
                        'committer': {'name': 'Test User', 'email': 'test@example.com', 'date': '2024-01-15T10:00:00Z'},
                    },
                    'author': {'login': 'test-user', 'id': 1, 'avatar_url': 'https://example.com/avatar.jpg'},
                    'html_url': 'https://github.com/test-owner/test-repo/commit/abc123',
                    'url': 'https://api.github.com/repos/test-owner/test-repo/commits/abc123',
                }
            ]

            mock_validate.return_value = ("test-owner", "test-repo")

            # Test with force flag
            await _show_commits(
                config=mock_config,
                fork_url="https://github.com/test-owner/test-repo",
                branch=None,
                limit=20,
                since_date=None,
                until_date=None,
                author=None,
                include_merge=False,
                show_files=False,
                show_stats=False,
                verbose=True,
                explain=False,
                ai_summary=False,
                ai_summary_compact=False,
                detail=True,
                force=True,  # Force flag should bypass qualification check
                disable_cache=False,
            )

            # Verify commits were displayed despite qualification data indicating no commits
            mock_display.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_commits_qualification_lookup_error_handling(
        self, mock_config, sample_repository, sample_commits
    ):
        """Test error handling when qualification lookup fails."""
        # Setup mocks
        with patch('forklift.cli.GitHubClient') as mock_client_class, \
             patch('forklift.cli.AnalysisCacheManager') as mock_cache_class, \
             patch('forklift.cli.ForkQualificationLookup') as mock_lookup_class, \
             patch('forklift.cli.ForkCommitStatusChecker') as mock_checker_class, \
             patch('forklift.cli._display_commits_table') as mock_display, \
             patch('forklift.cli.validate_repository_url') as mock_validate, \
             patch('forklift.cli._get_parent_repository_url') as mock_get_parent:

            # Configure mocks
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get_repository.return_value = sample_repository
            mock_client.get_branch_commits.return_value = [
                {
                    'sha': 'abc123',
                    'commit': {
                        'message': 'Add new feature',
                        'author': {'name': 'Test User', 'email': 'test@example.com', 'date': '2024-01-15T10:00:00Z'},
                        'committer': {'name': 'Test User', 'email': 'test@example.com', 'date': '2024-01-15T10:00:00Z'},
                    },
                    'author': {'login': 'test-user', 'id': 1, 'avatar_url': 'https://example.com/avatar.jpg'},
                    'html_url': 'https://github.com/test-owner/test-repo/commit/abc123',
                    'url': 'https://api.github.com/repos/test-owner/test-repo/commits/abc123',
                }
            ]

            mock_cache = AsyncMock()
            mock_cache_class.return_value = mock_cache

            mock_lookup = AsyncMock()
            mock_lookup_class.return_value = mock_lookup
            mock_lookup.get_fork_qualification_data.side_effect = Exception("Lookup error")

            mock_checker = AsyncMock()
            mock_checker_class.return_value = mock_checker
            mock_checker.has_commits_ahead.return_value = None  # Unknown status

            mock_validate.return_value = ("test-owner", "test-repo")
            mock_get_parent.return_value = "https://github.com/parent-owner/parent-repo"

            # Test - should handle error gracefully and continue
            await _show_commits(
                config=mock_config,
                fork_url="https://github.com/test-owner/test-repo",
                branch=None,
                limit=20,
                since_date=None,
                until_date=None,
                author=None,
                include_merge=False,
                show_files=False,
                show_stats=False,
                verbose=True,
                explain=False,
                ai_summary=False,
                ai_summary_compact=False,
                detail=True,
                force=False,
                disable_cache=False,
            )

            # Verify that despite the error, commits were still displayed
            mock_display.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_commits_no_detail_mode_skips_qualification(
        self, mock_config, sample_repository, sample_commits
    ):
        """Test that qualification lookup is skipped when not in detail mode."""
        # Setup mocks
        with patch('forklift.cli.GitHubClient') as mock_client_class, \
             patch('forklift.cli.ForkQualificationLookup') as mock_lookup_class, \
             patch('forklift.cli._display_commits_table') as mock_display, \
             patch('forklift.cli.validate_repository_url') as mock_validate:

            # Configure mocks
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get_repository.return_value = sample_repository
            mock_client.get_branch_commits.return_value = [
                {
                    'sha': 'abc123',
                    'commit': {
                        'message': 'Add new feature',
                        'author': {'name': 'Test User', 'email': 'test@example.com', 'date': '2024-01-15T10:00:00Z'},
                        'committer': {'name': 'Test User', 'email': 'test@example.com', 'date': '2024-01-15T10:00:00Z'},
                    },
                    'author': {'login': 'test-user', 'id': 1, 'avatar_url': 'https://example.com/avatar.jpg'},
                    'html_url': 'https://github.com/test-owner/test-repo/commit/abc123',
                    'url': 'https://api.github.com/repos/test-owner/test-repo/commits/abc123',
                }
            ]

            mock_lookup_class.return_value = AsyncMock()
            mock_validate.return_value = ("test-owner", "test-repo")

            # Test without detail mode
            await _show_commits(
                config=mock_config,
                fork_url="https://github.com/test-owner/test-repo",
                branch=None,
                limit=20,
                since_date=None,
                until_date=None,
                author=None,
                include_merge=False,
                show_files=False,
                show_stats=False,
                verbose=True,
                explain=False,
                ai_summary=False,
                ai_summary_compact=False,
                detail=False,  # Detail mode disabled
                force=False,
                disable_cache=False,
            )

            # Verify qualification lookup was not used
            mock_lookup_class.assert_not_called()
            
            # Verify commits were displayed normally
            mock_display.assert_called_once()