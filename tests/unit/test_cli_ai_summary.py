"""Tests for AI summary functionality in CLI commands."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner

from forklift.cli import cli
from forklift.models.github import Repository, Commit, User
from forklift.models.ai_summary import AISummary, AIUsageStats


@pytest.fixture
def mock_config():
    """Mock ForkliftConfig with OpenAI API key."""
    from forklift.config.settings import ForkliftConfig, GitHubConfig
    
    config = ForkliftConfig(
        github=GitHubConfig(
            token="ghp_1234567890abcdef1234567890abcdef12345678"
        ),
        openai_api_key="sk-test1234567890abcdef1234567890abcdef1234567890abcdef"
    )
    return config


@pytest.fixture
def mock_repository():
    """Mock Repository object."""
    return Repository(
        id=123,
        owner="test-owner",
        name="test-repo",
        full_name="test-owner/test-repo",
        url="https://api.github.com/repos/test-owner/test-repo",
        html_url="https://github.com/test-owner/test-repo",
        clone_url="https://github.com/test-owner/test-repo.git",
        default_branch="main"
    )


@pytest.fixture
def mock_commits():
    """Mock list of Commit objects."""
    author = User(login="test-author", html_url="https://github.com/test-author")
    
    return [
        Commit(
            sha="abc123def456789012345678901234567890abcdef",
            message="feat: add new feature",
            author=author,
            date="2024-01-15T10:30:00Z",
            additions=50,
            deletions=10,
            total_changes=60
        ),
        Commit(
            sha="def456ghi789012345678901234567890abcdef12",
            message="fix: resolve bug in authentication",
            author=author,
            date="2024-01-14T15:45:00Z",
            additions=5,
            deletions=2,
            total_changes=7
        )
    ]


@pytest.fixture
def mock_commit_details():
    """Mock commit details with diff data."""
    return [
        {
            "sha": "abc123def456789012345678901234567890abcdef",
            "files": [
                {
                    "filename": "src/feature.py",
                    "patch": "@@ -1,3 +1,6 @@\n def feature():\n+    # New implementation\n+    return True\n     pass"
                }
            ]
        },
        {
            "sha": "def456ghi789012345678901234567890abcdef12",
            "files": [
                {
                    "filename": "src/auth.py",
                    "patch": "@@ -10,7 +10,7 @@\n def authenticate(user):\n-    return False\n+    return validate_user(user)"
                }
            ]
        }
    ]


@pytest.fixture
def mock_ai_summaries():
    """Mock AI summaries."""
    return [
        AISummary(
            commit_sha="abc123def456789012345678901234567890abcdef",
            summary_text="Added a new feature implementation with proper validation",
            what_changed="Implemented new feature function with validation logic",
            why_changed="To provide the requested functionality to users",
            potential_side_effects="May affect existing code that depends on the old behavior",
            model_used="gpt-4o-mini",
            tokens_used=150,
            processing_time_ms=1200
        ),
        AISummary(
            commit_sha="def456ghi789012345678901234567890abcdef12",
            summary_text="Fixed authentication bug by adding proper user validation",
            what_changed="Changed authentication logic to use validate_user function",
            why_changed="The previous implementation always returned False",
            potential_side_effects="Authentication behavior will change for all users",
            model_used="gpt-4o-mini",
            tokens_used=120,
            processing_time_ms=980
        )
    ]


class TestShowCommitsAISummary:
    """Test cases for show-commits command with AI summary functionality."""

    @patch('forklift.cli.load_config')
    @patch('forklift.cli.GitHubClient')
    @patch('forklift.cli.validate_repository_url')
    @patch('forklift.ai.client.OpenAIClient')
    @patch('forklift.ai.summary_engine.AICommitSummaryEngine')
    def test_show_commits_with_ai_summary_flag(
        self, 
        mock_summary_engine_class,
        mock_openai_client_class,
        mock_validate_url, 
        mock_client_class, 
        mock_load_config,
        mock_config, 
        mock_repository, 
        mock_commits,
        mock_commit_details,
        mock_ai_summaries
    ):
        """Test show-commits command with --ai-summary flag."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("test-owner", "test-repo")
        
        # Mock GitHub client
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get_repository.return_value = mock_repository
        mock_client.get_branch_commits.return_value = [
            {"sha": "abc123def456789012345678901234567890abcdef", "commit": {"message": "feat: add new feature"}},
            {"sha": "def456ghi789012345678901234567890abcdef12", "commit": {"message": "fix: resolve bug"}}
        ]
        mock_client.get_commit_details.side_effect = mock_commit_details
        
        # Mock OpenAI client and summary engine
        mock_openai_client = AsyncMock()
        mock_openai_client_class.return_value = mock_openai_client
        
        mock_summary_engine = AsyncMock()
        mock_summary_engine_class.return_value = mock_summary_engine
        mock_summary_engine.generate_batch_summaries.return_value = mock_ai_summaries
        mock_summary_engine.get_usage_stats.return_value = AIUsageStats(
            total_requests=2,
            successful_requests=2,
            failed_requests=0,
            total_tokens_used=270,
            total_cost_usd=0.0001,
            average_processing_time_ms=1090
        )
        
        # Run command with AI summary flag
        runner = CliRunner()
        result = runner.invoke(cli, [
            'show-commits', 'test-owner/test-repo',
            '--ai-summary'
        ])
        
        # Assertions
        assert result.exit_code == 0
        assert "🤖 AI-Powered Commit Summaries" in result.output
        assert "What:" in result.output
        assert "Why:" in result.output
        assert "Impact:" in result.output
        assert "AI Usage:" in result.output
        
        # Verify AI components were called
        mock_openai_client_class.assert_called_once()
        mock_summary_engine_class.assert_called_once()
        mock_summary_engine.generate_batch_summaries.assert_called_once()

    def test_show_commits_ai_summary_no_api_key(self):
        """Test AI summary function directly with no API key."""
        import asyncio
        from forklift.cli import _display_ai_summaries_for_commits
        from forklift.config.settings import ForkliftConfig, GitHubConfig
        from forklift.github.client import GitHubClient
        from unittest.mock import AsyncMock
        from io import StringIO
        import sys
        
        config = ForkliftConfig(
            github=GitHubConfig(
                token="ghp_1234567890abcdef1234567890abcdef12345678"
            ),
            openai_api_key=None  # No API key
        )
        
        # Capture output
        captured_output = StringIO()
        sys.stdout = captured_output
        
        async def test_function():
            github_client = AsyncMock()
            commits = [AsyncMock()]  # Mock commit
            
            await _display_ai_summaries_for_commits(
                github_client, config, "test-owner", "test-repo", commits
            )
        
        # Run the async function
        asyncio.run(test_function())
        
        # Restore stdout
        sys.stdout = sys.__stdout__
        
        # Check output
        output = captured_output.getvalue()
        assert "OpenAI API key not configured" in output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli.GitHubClient')
    @patch('forklift.cli.validate_repository_url')
    @patch('forklift.ai.client.OpenAIClient')
    @patch('forklift.ai.summary_engine.AICommitSummaryEngine')
    def test_show_commits_ai_summary_with_errors(
        self,
        mock_summary_engine_class,
        mock_openai_client_class,
        mock_validate_url,
        mock_client_class,
        mock_load_config,
        mock_config,
        mock_repository,
        mock_commits
    ):
        """Test show-commits command with AI summary when errors occur."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("test-owner", "test-repo")
        
        # Mock GitHub client
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get_repository.return_value = mock_repository
        mock_client.get_branch_commits.return_value = [
            {"sha": "abc123def456789012345678901234567890abcdef", "commit": {"message": "feat: add new feature"}}
        ]
        mock_client.get_commit_details.return_value = {"sha": "abc123def456789012345678901234567890abcdef", "files": []}
        
        # Mock AI components with error
        mock_openai_client = AsyncMock()
        mock_openai_client_class.return_value = mock_openai_client
        
        mock_summary_engine = AsyncMock()
        mock_summary_engine_class.return_value = mock_summary_engine
        
        # Return summary with error
        error_summary = AISummary(
            commit_sha="abc123def456789012345678901234567890abcdef",
            summary_text="",
            what_changed="",
            why_changed="",
            potential_side_effects="",
            error="API rate limit exceeded"
        )
        mock_summary_engine.generate_batch_summaries.return_value = [error_summary]
        mock_summary_engine.get_usage_stats.return_value = AIUsageStats()
        
        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, [
            'show-commits', 'test-owner/test-repo',
            '--ai-summary'
        ])
        
        # Should handle errors gracefully
        assert result.exit_code == 0
        assert "Error: API rate limit exceeded" in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli.GitHubClient')
    @patch('forklift.cli.validate_repository_url')
    def test_show_commits_without_ai_summary_flag(
        self,
        mock_validate_url,
        mock_client_class,
        mock_load_config,
        mock_config,
        mock_repository
    ):
        """Test show-commits command without --ai-summary flag (should work normally)."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("test-owner", "test-repo")
        
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get_repository.return_value = mock_repository
        mock_client.get_branch_commits.return_value = []
        
        # Run command without AI summary flag
        runner = CliRunner()
        result = runner.invoke(cli, [
            'show-commits', 'test-owner/test-repo'
        ])
        
        # Should work normally without AI summaries
        assert result.exit_code == 0
        assert "🤖 AI-Powered Commit Summaries" not in result.output

    @patch('forklift.cli.load_config')
    @patch('forklift.cli.GitHubClient')
    @patch('forklift.cli.validate_repository_url')
    @patch('forklift.ai.client.OpenAIClient')
    @patch('forklift.ai.summary_engine.AICommitSummaryEngine')
    def test_show_commits_ai_summary_with_explain_flag(
        self,
        mock_summary_engine_class,
        mock_openai_client_class,
        mock_validate_url,
        mock_client_class,
        mock_load_config,
        mock_config,
        mock_repository,
        mock_ai_summaries
    ):
        """Test show-commits command with both --explain and --ai-summary flags."""
        # Setup mocks
        mock_load_config.return_value = mock_config
        mock_validate_url.return_value = ("test-owner", "test-repo")
        
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get_repository.return_value = mock_repository
        mock_client.get_branch_commits.return_value = [
            {"sha": "abc123def456789012345678901234567890abcdef", "commit": {"message": "feat: add new feature"}}
        ]
        mock_client.get_commit_details.return_value = {"sha": "abc123def456789012345678901234567890abcdef", "files": []}
        
        # Mock AI components
        mock_openai_client = AsyncMock()
        mock_openai_client_class.return_value = mock_openai_client
        
        mock_summary_engine = AsyncMock()
        mock_summary_engine_class.return_value = mock_summary_engine
        mock_summary_engine.generate_batch_summaries.return_value = mock_ai_summaries
        mock_summary_engine.get_usage_stats.return_value = AIUsageStats()
        
        # Run command with both flags
        runner = CliRunner()
        result = runner.invoke(cli, [
            'show-commits', 'test-owner/test-repo',
            '--explain',
            '--ai-summary'
        ])
        
        # Should show both explanations and AI summaries
        assert result.exit_code == 0
        assert "📝 Commit Explanations" in result.output
        assert "🤖 AI-Powered Commit Summaries" in result.output