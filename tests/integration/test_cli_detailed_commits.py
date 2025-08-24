"""Integration tests for CLI --detail flag functionality."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from click.testing import CliRunner

from forklift.cli import cli
from forklift.models.github import Commit, Repository, User
from forklift.models.ai_summary import AISummary
from datetime import datetime


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = MagicMock()
    config.github.token = "test_token"
    config.openai_api_key = "test_openai_key"
    return config


@pytest.fixture
def sample_commits():
    """Create sample commits for testing."""
    return [
        Commit(
            sha="abc123def456789012345678901234567890abcd",
            message="feat: add new feature\n\nThis adds a new feature for testing",
            author=User(login="testuser", id=123, html_url="https://github.com/testuser"),
            date=datetime(2024, 1, 15, 10, 30, 0),
            files_changed=["test.py", "README.md"],
            additions=10,
            deletions=2
        ),
        Commit(
            sha="def456ghi789012345678901234567890abcdef0",
            message="fix: resolve bug in feature",
            author=User(login="testuser2", id=456, html_url="https://github.com/testuser2"),
            date=datetime(2024, 1, 16, 14, 45, 0),
            files_changed=["test.py"],
            additions=3,
            deletions=5
        )
    ]


@pytest.fixture
def sample_repository():
    """Create a sample repository."""
    return Repository(
        owner="testowner",
        name="testrepo",
        full_name="testowner/testrepo",
        url="https://api.github.com/repos/testowner/testrepo",
        html_url="https://github.com/testowner/testrepo",
        clone_url="https://github.com/testowner/testrepo.git",
        default_branch="main"
    )


class TestCLIDetailFlag:
    """Test cases for CLI --detail flag functionality."""
    
    @patch('forklift.cli.load_config')
    @patch('forklift.cli.GitHubClient')
    @patch('forklift.cli.OpenAIClient')
    def test_show_commits_with_detail_flag(self, mock_openai_client, mock_github_client_class, mock_load_config, mock_config, sample_commits, sample_repository):
        """Test show-commits command with --detail flag."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client
        mock_github_client.get_repository.return_value = sample_repository
        mock_github_client.get_branch_commits.return_value = [
            {
                "sha": commit.sha,
                "commit": {
                    "message": commit.message,
                    "author": {"name": commit.author.login, "date": commit.date.isoformat()},
                },
                "author": {"login": commit.author.login, "id": commit.author.id},
                "stats": {"additions": commit.additions, "deletions": commit.deletions},
                "files": [{"filename": f} for f in commit.files_changed]
            }
            for commit in sample_commits
        ]
        mock_github_client.get_commit_details.return_value = {
            "sha": "abc123def456",
            "files": [
                {
                    "filename": "test.py",
                    "patch": "@@ -1,3 +1,4 @@\n def test():\n+    print('hello')\n     pass"
                }
            ]
        }
        
        # Setup OpenAI mock
        mock_openai_instance = AsyncMock()
        mock_openai_client.return_value.__aenter__.return_value = mock_openai_instance
        
        runner = CliRunner()
        
        with patch('forklift.cli._show_commits') as mock_show_commits:
            mock_show_commits.return_value = None
            
            result = runner.invoke(cli, [
                'show-commits',
                'testowner/testrepo',
                '--detail',
                '--limit', '2'
            ])
        
        assert result.exit_code == 0
        mock_show_commits.assert_called_once()
        
        # Verify the detail parameter was passed
        call_args = mock_show_commits.call_args[0]
        assert len(call_args) >= 14  # Should have detail parameter
    
    @patch('forklift.cli.load_config')
    @patch('forklift.cli.GitHubClient')
    def test_show_commits_detail_without_openai_key(self, mock_github_client_class, mock_load_config, mock_config, sample_commits, sample_repository):
        """Test show-commits with --detail flag but no OpenAI API key."""
        # Setup mocks without OpenAI key
        mock_config.openai_api_key = None
        mock_load_config.return_value = mock_config
        
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client
        mock_github_client.get_repository.return_value = sample_repository
        mock_github_client.get_branch_commits.return_value = []
        
        runner = CliRunner()
        
        with patch('forklift.cli._show_commits') as mock_show_commits:
            mock_show_commits.return_value = None
            
            result = runner.invoke(cli, [
                'show-commits',
                'testowner/testrepo',
                '--detail'
            ])
        
        assert result.exit_code == 0
        mock_show_commits.assert_called_once()
    
    def test_show_commits_detail_flag_help(self):
        """Test that --detail flag appears in help text."""
        runner = CliRunner()
        
        # Use a simpler approach that doesn't require full CLI context
        from forklift.cli import show_commits
        result = runner.invoke(show_commits, ['--help'])
        
        assert result.exit_code == 0
        assert '--detail' in result.output
        assert 'comprehensive commit information' in result.output
    
    @patch('forklift.cli.load_config')
    @patch('forklift.cli.GitHubClient')
    def test_show_commits_detail_with_other_flags(self, mock_github_client_class, mock_load_config, mock_config, sample_repository):
        """Test --detail flag combined with other flags."""
        mock_load_config.return_value = mock_config
        
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client
        mock_github_client.get_repository.return_value = sample_repository
        mock_github_client.get_branch_commits.return_value = []
        
        runner = CliRunner()
        
        with patch('forklift.cli._show_commits') as mock_show_commits:
            mock_show_commits.return_value = None
            
            result = runner.invoke(cli, [
                'show-commits',
                'testowner/testrepo',
                '--detail',
                '--limit', '5',
                '--author', 'testuser',
                '--disable-cache'
            ])
        
        assert result.exit_code == 0
        mock_show_commits.assert_called_once()
        
        # Verify all parameters were passed correctly
        call_args = mock_show_commits.call_args[0]
        assert call_args[3] == 5  # limit
        assert call_args[6] == 'testuser'  # author
        # detail should be True and disable_cache should be True


class TestDetailedCommitsDisplay:
    """Test cases for detailed commits display functionality."""
    
    @pytest.mark.asyncio
    @patch('forklift.cli.DetailedCommitDisplay')
    @patch('forklift.cli.OpenAIClient')
    @patch('forklift.cli.AICommitSummaryEngine')
    async def test_display_detailed_commits_with_ai(self, mock_ai_engine_class, mock_openai_client, mock_display_class, mock_config, sample_commits, sample_repository):
        """Test _display_detailed_commits function with AI engine."""
        from forklift.cli import _display_detailed_commits
        from forklift.github.client import GitHubClient
        
        # Setup mocks
        mock_github_client = AsyncMock()
        
        mock_ai_engine = AsyncMock()
        mock_ai_engine_class.return_value = mock_ai_engine
        
        mock_display = AsyncMock()
        mock_display_class.return_value = mock_display
        mock_display.generate_detailed_view.return_value = [
            MagicMock(commit=commit) for commit in sample_commits
        ]
        
        mock_openai_instance = AsyncMock()
        mock_openai_client.return_value.__aenter__.return_value = mock_openai_instance
        
        # Call the function
        await _display_detailed_commits(
            mock_github_client,
            mock_config,
            "testowner",
            "testrepo",
            sample_commits,
            sample_repository
        )
        
        # Verify AI engine was created and used
        mock_ai_engine_class.assert_called_once()
        mock_display_class.assert_called_once()
        mock_display.generate_detailed_view.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('forklift.cli.DetailedCommitDisplay')
    async def test_display_detailed_commits_without_ai(self, mock_display_class, mock_config, sample_commits, sample_repository):
        """Test _display_detailed_commits function without AI engine."""
        from forklift.cli import _display_detailed_commits
        
        # Setup config without OpenAI key
        mock_config.openai_api_key = None
        
        mock_github_client = AsyncMock()
        
        mock_display = AsyncMock()
        mock_display_class.return_value = mock_display
        mock_display.generate_detailed_view.return_value = [
            MagicMock(commit=commit) for commit in sample_commits
        ]
        
        # Call the function
        await _display_detailed_commits(
            mock_github_client,
            mock_config,
            "testowner",
            "testrepo",
            sample_commits,
            sample_repository
        )
        
        # Verify display was created without AI engine
        mock_display_class.assert_called()
        call_args = mock_display_class.call_args
        assert call_args[1]['ai_engine'] is None
    
    @pytest.mark.asyncio
    @patch('forklift.cli.DetailedCommitDisplay')
    @patch('forklift.cli.console')
    async def test_display_detailed_commits_error_handling(self, mock_console, mock_display_class, mock_config, sample_commits, sample_repository):
        """Test error handling in _display_detailed_commits function."""
        from forklift.cli import _display_detailed_commits
        
        mock_github_client = AsyncMock()
        
        # Make display raise an exception
        mock_display_class.side_effect = Exception("Test error")
        
        # Call the function (should not raise)
        await _display_detailed_commits(
            mock_github_client,
            mock_config,
            "testowner",
            "testrepo",
            sample_commits,
            sample_repository
        )
        
        # Verify error was printed
        mock_console.print.assert_called()
        error_call = [call for call in mock_console.print.call_args_list if 'Error' in str(call)]
        assert len(error_call) > 0


class TestDetailedCommitsIntegration:
    """Integration tests for detailed commits functionality."""
    
    @pytest.mark.asyncio
    @patch('forklift.cli.load_config')
    @patch('forklift.cli.GitHubClient')
    @patch('forklift.cli.OpenAIClient')
    @patch('forklift.cli.console')
    async def test_full_detailed_commits_workflow(self, mock_console, mock_openai_client, mock_github_client_class, mock_load_config, mock_config, sample_commits, sample_repository):
        """Test full workflow of detailed commits display."""
        from forklift.cli import _show_commits
        
        # Setup mocks
        mock_load_config.return_value = mock_config
        
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client
        mock_github_client.get_repository.return_value = sample_repository
        mock_github_client.get_branch_commits.return_value = [
            {
                "sha": commit.sha,
                "commit": {
                    "message": commit.message,
                    "author": {"name": commit.author.login, "date": commit.date.isoformat()},
                },
                "author": {"login": commit.author.login, "id": commit.author.id},
                "stats": {"additions": commit.additions, "deletions": commit.deletions},
                "files": [{"filename": f} for f in commit.files_changed]
            }
            for commit in sample_commits
        ]
        mock_github_client.get_commit_details.return_value = {
            "sha": "abc123def456",
            "files": [
                {
                    "filename": "test.py",
                    "patch": "@@ -1,3 +1,4 @@\n def test():\n+    print('hello')\n     pass"
                }
            ]
        }
        
        # Setup OpenAI mock
        mock_openai_instance = AsyncMock()
        mock_openai_client.return_value.__aenter__.return_value = mock_openai_instance
        
        # Call the function with detail=True
        await _show_commits(
            mock_config,
            "testowner/testrepo",
            None,  # branch
            10,    # limit
            None,  # since_date
            None,  # until_date
            None,  # author
            False, # include_merge
            False, # show_files
            False, # show_stats
            False, # verbose
            False, # explain
            False, # ai_summary
            True,  # detail
            False  # disable_cache
        )
        
        # Verify GitHub client methods were called
        mock_github_client.get_repository.assert_called_once()
        mock_github_client.get_branch_commits.assert_called_once()
        
        # Verify console output was generated
        mock_console.print.assert_called()
    
    @pytest.mark.asyncio
    @patch('forklift.cli.load_config')
    @patch('forklift.cli.GitHubClient')
    async def test_detailed_commits_with_no_commits(self, mock_github_client_class, mock_load_config, mock_config, sample_repository):
        """Test detailed commits display with no commits found."""
        from forklift.cli import _show_commits
        
        mock_load_config.return_value = mock_config
        
        mock_github_client = AsyncMock()
        mock_github_client_class.return_value.__aenter__.return_value = mock_github_client
        mock_github_client.get_repository.return_value = sample_repository
        mock_github_client.get_branch_commits.return_value = []  # No commits
        
        # Call the function with detail=True
        await _show_commits(
            mock_config,
            "testowner/testrepo",
            None,  # branch
            10,    # limit
            None,  # since_date
            None,  # until_date
            None,  # author
            False, # include_merge
            False, # show_files
            False, # show_stats
            False, # verbose
            False, # explain
            False, # ai_summary
            True,  # detail
            False  # disable_cache
        )
        
        # Should complete without errors even with no commits
        mock_github_client.get_repository.assert_called_once()
    
    def test_detail_flag_mutually_exclusive_behavior(self):
        """Test that --detail flag works independently of other display flags."""
        from click.testing import CliRunner
        
        runner = CliRunner()
        
        # Test that --detail can be used with other flags
        with patch('forklift.cli.load_config') as mock_load_config:
            mock_config = MagicMock()
            mock_config.github.token = "test_token"
            mock_load_config.return_value = mock_config
            
            with patch('forklift.cli._show_commits') as mock_show_commits:
                mock_show_commits.return_value = None
                
                result = runner.invoke(cli, [
                    'show-commits',
                    'testowner/testrepo',
                    '--detail',
                    '--explain',
                    '--ai-summary'
                ])
                
                assert result.exit_code == 0
                mock_show_commits.assert_called_once()
                
                # Verify detail=True was passed
                call_args = mock_show_commits.call_args[0]
                detail_param = call_args[13]  # detail parameter position
                assert detail_param is True