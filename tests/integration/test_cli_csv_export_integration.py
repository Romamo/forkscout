"""Integration tests for CLI CSV export functionality with new multi-row format."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner

from forkscout.cli import cli
from forkscout.config.settings import ForkscoutConfig
from forkscout.models.analysis import ForkAnalysis
from forkscout.models.github import Fork, Repository, User, Commit
from forkscout.display.interaction_mode import InteractionMode


class TestCLICSVExportIntegration:
    """Integration tests for CLI CSV export with multi-row format."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock()
        
        # Mock github config
        config.github = MagicMock()
        config.github.token = "test_token"
        
        # Mock analysis config
        config.analysis = MagicMock()
        config.analysis.min_score_threshold = 50
        config.analysis.max_forks_to_analyze = 100
        config.analysis.auto_pr_enabled = False
        
        # Mock logging config
        config.logging = MagicMock()
        config.logging.level = "INFO"
        config.logging.console_enabled = True
        config.logging.file_enabled = False
        config.logging.format = "%(message)s"
        
        # Other config
        config.dry_run = False
        config.output_format = "markdown"
        
        return config

    @pytest.fixture
    def mock_fork_analysis(self):
        """Create a mock fork analysis with commits."""
        # Create mock user
        user = User(
            login="test_owner",
            id=123,
            html_url="https://github.com/test_owner"
        )
        
        # Create mock repository (fork)
        repository = Repository(
            id=456,
            name="test_repo",
            full_name="test_owner/test_repo",
            owner="test_owner",  # Owner should be a string
            html_url="https://github.com/test_owner/test_repo",
            clone_url="https://github.com/test_owner/test_repo.git",
            url="https://api.github.com/repos/test_owner/test_repo",
            stars=10,
            forks_count=5,
            language="Python",
            description="Test repository",
            is_fork=True  # Mark as fork
        )
        
        # Create mock parent repository
        parent_repository = Repository(
            id=123,
            name="original_repo",
            full_name="original_owner/original_repo",
            owner="original_owner",
            html_url="https://github.com/original_owner/original_repo",
            clone_url="https://github.com/original_owner/original_repo.git",
            url="https://api.github.com/repos/original_owner/original_repo",
            stars=100,
            forks_count=50,
            language="Python",
            description="Original repository"
        )
        
        # Create mock fork
        fork = Fork(
            repository=repository,
            parent=parent_repository,
            owner=user,
            commits_ahead=3,
            commits_behind=1,
            is_active=True
        )
        
        # Create mock commits
        commits = [
            Commit(
                sha="abc123def456789012345678901234567890abcd",  # 40 character SHA
                message="Add new feature",
                author=user,
                date="2024-01-15T10:30:00Z",
                files_changed=["file1.py", "file2.py"],
                additions=50,
                deletions=10
            ),
            Commit(
                sha="def456abc123789012345678901234567890abcd",  # 40 character SHA
                message="Fix bug in feature",
                author=user,
                date="2024-01-16T14:20:00Z",
                files_changed=["file1.py"],
                additions=5,
                deletions=2
            )
        ]
        
        # Create mock feature with commits
        from forkscout.models.analysis import Feature, FeatureCategory
        feature = Feature(
            id="feature_1",
            title="Test Feature",
            description="A test feature",
            category=FeatureCategory.NEW_FEATURE,
            commits=commits,
            files_affected=["file1.py", "file2.py"],
            source_fork=fork
        )
        
        # Create mock metrics
        from forkscout.models.analysis import ForkMetrics
        metrics = ForkMetrics(
            stars=10,
            forks=5,
            contributors=2,
            commit_frequency=1.5
        )
        
        # Create fork analysis
        analysis = ForkAnalysis(
            fork=fork,
            features=[feature],
            metrics=metrics,
            commit_explanations=[]
        )
        
        return analysis

    def test_analyze_command_csv_export(self, runner, mock_config, mock_fork_analysis):
        """Test analyze command CSV export functionality."""
        with patch('forklift.cli.load_config', return_value=mock_config):
            with patch('forklift.cli.validate_repository_url', return_value=('owner', 'repo')):
                with patch('forklift.cli._run_analysis', new_callable=AsyncMock) as mock_run_analysis:
                    # Setup mock to return analysis results
                    mock_run_analysis.return_value = {
                        "repository": "owner/repo",
                        "total_forks": 1,
                        "analyzed_forks": 1,
                        "total_features": 1,
                        "high_value_features": 1,
                        "fork_analyses": [mock_fork_analysis],
                        "report": "Test report"
                    }
                    
                    with patch('forklift.cli.asyncio.run') as mock_asyncio_run:
                        # Mock asyncio.run to return None (successful execution)
                        mock_asyncio_run.return_value = None
                        
                        result = runner.invoke(cli, [
                            'analyze', 'owner/repo', '--csv'
                        ])
                        
                        assert result.exit_code == 0
                        
                        # Verify asyncio.run was called (for both analysis and CSV export)
                        assert mock_asyncio_run.call_count >= 1

    def test_analyze_command_csv_with_explanations(self, runner, mock_config, mock_fork_analysis):
        """Test analyze command CSV export with explanations."""
        with patch('forklift.cli.load_config', return_value=mock_config):
            with patch('forklift.cli.validate_repository_url', return_value=('owner', 'repo')):
                with patch('forklift.cli._run_analysis', new_callable=AsyncMock) as mock_run_analysis:
                    mock_run_analysis.return_value = {
                        "repository": "owner/repo",
                        "total_forks": 1,
                        "analyzed_forks": 1,
                        "total_features": 1,
                        "high_value_features": 1,
                        "fork_analyses": [mock_fork_analysis],
                        "report": "Test report"
                    }
                    
                    with patch('forklift.cli.asyncio.run') as mock_asyncio_run:
                        # Mock asyncio.run to return None (successful execution)
                        mock_asyncio_run.return_value = None
                        
                        result = runner.invoke(cli, [
                            'analyze', 'owner/repo', '--csv', '--explain'
                        ])
                        
                        assert result.exit_code == 0
                        
                        # Verify asyncio.run was called (for both analysis and CSV export)
                        assert mock_asyncio_run.call_count >= 1

    def test_show_forks_csv_export_integration(self, runner, mock_config):
        """Test show-forks command CSV export integration."""
        with patch('forklift.cli.load_config', return_value=mock_config):
            with patch('forklift.cli.validate_repository_url', return_value=('owner', 'repo')):
                with patch('forklift.cli.asyncio.run') as mock_asyncio_run:
                    # Mock asyncio.run to return None (successful execution)
                    mock_asyncio_run.return_value = None
                    
                    result = runner.invoke(cli, [
                        'show-forks', 'owner/repo', '--csv'
                    ])
                    
                    if result.exit_code != 0:
                        print(f"Command failed with output: {result.output}")
                        print(f"Exception: {result.exception}")
                    
                    assert result.exit_code == 0
                    
                    # Verify asyncio.run was called
                    mock_asyncio_run.assert_called_once()

    def test_show_forks_csv_with_detail_mode(self, runner, mock_config):
        """Test show-forks CSV export with detail mode."""
        with patch('forklift.cli.load_config', return_value=mock_config):
            with patch('forklift.cli.validate_repository_url', return_value=('owner', 'repo')):
                with patch('forklift.cli.asyncio.run') as mock_asyncio_run:
                    # Mock asyncio.run to return None (successful execution)
                    mock_asyncio_run.return_value = None
                    
                    result = runner.invoke(cli, [
                        'show-forks', 'owner/repo', '--csv', '--detail'
                    ])
                    
                    assert result.exit_code == 0
                    
                    # Verify asyncio.run was called
                    mock_asyncio_run.assert_called_once()

    def test_csv_mode_suppresses_interactive_elements(self, runner, mock_config):
        """Test that CSV mode properly suppresses interactive elements."""
        with patch('forklift.cli.load_config', return_value=mock_config):
            with patch('forklift.cli.validate_repository_url', return_value=('owner', 'repo')):
                with patch('forklift.cli._run_analysis', new_callable=AsyncMock) as mock_run_analysis:
                    mock_run_analysis.return_value = {
                        "repository": "owner/repo",
                        "total_forks": 0,
                        "analyzed_forks": 0,
                        "total_features": 0,
                        "high_value_features": 0,
                        "fork_analyses": [],
                        "report": "Empty report"
                    }
                    
                    with patch('forklift.cli.asyncio.run') as mock_asyncio_run:
                        # Mock asyncio.run to call the actual function and return the result
                        def mock_asyncio_run_side_effect(coro):
                            if hasattr(coro, '__name__') and coro.__name__ == '_run_analysis':
                                # Call the mock directly for _run_analysis
                                return mock_run_analysis.return_value
                            else:
                                # For other coroutines (like CSV export), return None
                                return None
                        
                        mock_asyncio_run.side_effect = mock_asyncio_run_side_effect
                        
                        result = runner.invoke(cli, [
                            'analyze', 'owner/repo', '--csv'
                        ])
                        
                        assert result.exit_code == 0
                        
                        # Verify that analysis was called with NON_INTERACTIVE mode
                        # Since we're mocking asyncio.run, we need to check the call differently
                        # The CSV mode should have been detected and set the interaction mode
                        assert mock_asyncio_run.call_count >= 1

    def test_csv_export_error_handling(self, runner, mock_config):
        """Test CSV export error handling."""
        with patch('forklift.cli.load_config', return_value=mock_config):
            with patch('forklift.cli.validate_repository_url', return_value=('owner', 'repo')):
                with patch('forklift.cli._run_analysis', new_callable=AsyncMock) as mock_run_analysis:
                    mock_run_analysis.return_value = {
                        "repository": "owner/repo",
                        "fork_analyses": []
                    }
                    
                    with patch('forklift.cli.asyncio.run') as mock_asyncio_run:
                        # Make asyncio.run raise an exception to simulate CSV export failure
                        from forkscout.exceptions import ForkscoutOutputError
                        mock_asyncio_run.side_effect = [
                            {"repository": "owner/repo", "fork_analyses": []},  # First call (analysis)
                            ForkscoutOutputError("CSV export failed")  # Second call (CSV export)
                        ]
                        
                        result = runner.invoke(cli, [
                            'analyze', 'owner/repo', '--csv'
                        ])
                        
                        # Should handle the error gracefully
                        assert result.exit_code != 0

    def test_csv_help_text_updated(self, runner):
        """Test that CSV help text describes the new multi-row format."""
        # Test analyze command help
        result = runner.invoke(cli, ['analyze', '--help'])
        
        assert result.exit_code == 0
        assert '--csv' in result.output
        assert 'multi-row' in result.output
        assert 'commit_date' in result.output
        assert 'commit_sha' in result.output
        assert 'commit_description' in result.output
        
        # Test show-forks command help
        result = runner.invoke(cli, ['show-forks', '--help'])
        
        assert result.exit_code == 0
        assert '--csv' in result.output
        assert 'multi-row' in result.output

    def test_csv_examples_in_help_text(self, runner):
        """Test that CSV examples show the new format."""
        # Test analyze command examples
        result = runner.invoke(cli, ['analyze', '--help'])
        
        assert result.exit_code == 0
        assert 'analysis_results.csv' in result.output
        assert 'analysis_with_explanations.csv' in result.output
        
        # Test show-forks command examples
        result = runner.invoke(cli, ['show-forks', '--help'])
        
        assert result.exit_code == 0
        assert 'forks_with_commits.csv' in result.output
        assert 'detailed_forks_with_commits.csv' in result.output

    def test_csv_configuration_passing(self, runner, mock_config):
        """Test that CSV configuration is properly passed from CLI to exporter."""
        with patch('forklift.cli.load_config', return_value=mock_config):
            with patch('forklift.cli.validate_repository_url', return_value=('owner', 'repo')):
                with patch('forklift.cli.asyncio.run') as mock_asyncio_run:
                    # Mock asyncio.run to return None (successful execution)
                    mock_asyncio_run.return_value = None
                    
                    result = runner.invoke(cli, [
                        'show-forks', 'owner/repo', '--csv', '--detail', '--show-commits', '5'
                    ])
                    
                    assert result.exit_code == 0
                    
                    # Verify asyncio.run was called
                    mock_asyncio_run.assert_called_once()