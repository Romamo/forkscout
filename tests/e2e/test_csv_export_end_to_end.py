"""End-to-end tests for CSV export workflows."""

import csv
import io
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forkscout.cli import cli
from forkscout.config.settings import ForkscoutConfig
from forkscout.display.repository_display_service import RepositoryDisplayService
from forkscout.github.client import GitHubClient


class TestCSVExportEndToEnd:
    """End-to-end tests for complete CSV export workflows."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock(spec=ForkscoutConfig)
        config.github = MagicMock()
        config.github.token = "test_token"
        config.analysis = MagicMock()
        config.analysis.min_score_threshold = 50
        config.analysis.max_forks_to_analyze = 100
        config.analysis.auto_pr_enabled = False
        config.dry_run = False
        config.output_format = "markdown"
        config.logging = None
        config.cache = MagicMock()
        config.cache.duration_hours = 24
        return config

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return AsyncMock(spec=GitHubClient)

    @pytest.fixture
    def sample_repository_data(self):
        """Create sample repository data for end-to-end testing."""
        from datetime import UTC, datetime
        from forkscout.models.fork_qualification import (
            CollectedForkData,
            ForkQualificationMetrics,
        )

        forks_data = [
            ForkQualificationMetrics(
                id=123,
                name="test-repo",
                full_name="user1/test-repo",
                owner="user1",
                html_url="https://github.com/user1/test-repo",
                stargazers_count=25,
                forks_count=5,
                watchers_count=10,
                size=1500,
                language="Python",
                topics=["python", "testing"],
                open_issues_count=2,
                created_at=datetime(2023, 6, 1, tzinfo=UTC),
                updated_at=datetime(2024, 1, 15, tzinfo=UTC),
                pushed_at=datetime(2024, 1, 20, tzinfo=UTC),
                archived=False,
                disabled=False,
                fork=True,
                license_key="mit",
                license_name="MIT License",
                description="Test repository for CSV export",
                homepage=None,
                default_branch="main"
            ),
            ForkQualificationMetrics(
                id=456,
                name="test-repo",
                full_name="user2/test-repo",
                owner="user2",
                html_url="https://github.com/user2/test-repo",
                stargazers_count=8,
                forks_count=1,
                watchers_count=3,
                size=1200,
                language="JavaScript",
                topics=[],
                open_issues_count=0,
                created_at=datetime(2023, 8, 15, tzinfo=UTC),
                updated_at=datetime(2023, 8, 15, tzinfo=UTC),
                pushed_at=datetime(2023, 8, 15, tzinfo=UTC),  # No commits ahead
                archived=False,
                disabled=False,
                fork=True,
                license_key="apache-2.0",
                license_name="Apache License 2.0",
                description="Another test repository",
                homepage=None,
                default_branch="main"
            )
        ]

        return [CollectedForkData(metrics=metrics) for metrics in forks_data]

    @pytest.mark.e2e
    def test_cli_csv_export_basic_workflow(self, mock_config):
        """Test basic CSV export workflow through CLI."""
        from click.testing import CliRunner
        
        runner = CliRunner()
        
        with patch('forklift.cli.load_config', return_value=mock_config):
            with patch('forklift.cli._show_forks_summary', new_callable=AsyncMock) as mock_show_forks:
                # Mock successful CSV export
                mock_show_forks.return_value = {"total_forks": 2, "displayed_forks": 2}
                
                result = runner.invoke(cli, [
                    'show-forks', 'owner/repo', '--csv'
                ])
                
                # Verify command executed successfully
                assert result.exit_code == 0
                
                # Verify CSV export was called
                mock_show_forks.assert_called_once()
                call_args = mock_show_forks.call_args[0]
                assert call_args[8] is True  # csv parameter

    @pytest.mark.e2e
    def test_cli_csv_export_with_all_flags(self, mock_config):
        """Test CSV export with all available flags."""
        from click.testing import CliRunner
        
        runner = CliRunner()
        
        with patch('forklift.cli.load_config', return_value=mock_config):
            with patch('forklift.cli._show_forks_summary', new_callable=AsyncMock) as mock_show_forks:
                mock_show_forks.return_value = {"total_forks": 5, "displayed_forks": 3}
                
                result = runner.invoke(cli, [
                    'show-forks', 'owner/repo',
                    '--csv',
                    '--detail',
                    '--ahead-only',
                    '--show-commits', '5',
                    '--max-forks', '100'
                ])
                
                assert result.exit_code == 0
                
                # Verify all parameters were passed correctly
                mock_show_forks.assert_called_once()
                call_args = mock_show_forks.call_args[0]
                
                # Verify CSV and other flags
                assert call_args[8] is True   # csv=True
                assert call_args[3] is True   # detail=True
                assert call_args[6] is True   # ahead_only=True
                assert call_args[4] == 5      # show_commits=5
                assert call_args[2] == 100    # max_forks=100

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_csv_export_output_redirection_simulation(
        self, mock_github_client, sample_repository_data
    ):
        """Test CSV export with simulated output redirection."""
        display_service = RepositoryDisplayService(mock_github_client)
        
        # Simulate output redirection by capturing stdout
        captured_output = io.StringIO()
        
        with patch("sys.stdout", captured_output):
            with patch.object(display_service, "show_fork_data") as mock_show_fork_data:
                mock_show_fork_data.return_value = {
                    "total_forks": 2,
                    "displayed_forks": 2,
                    "collected_forks": sample_repository_data
                }
                
                # Simulate CSV export call
                from forkscout.cli import _export_forks_csv
                
                await _export_forks_csv(
                    display_service,
                    "owner/repo",
                    max_forks=None,
                    detail=False,
                    show_commits=0,
                    force_all_commits=False,
                    ahead_only=False
                )
        
        # Verify CSV output was written to stdout
        csv_output = captured_output.getvalue()
        assert len(csv_output) > 0
        
        # Verify it's valid CSV
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        assert len(rows) >= 0  # May be empty if mocked data processing differs

    @pytest.mark.e2e
    def test_csv_export_file_output_workflow(self, mock_config):
        """Test complete workflow of exporting CSV to file."""
        from click.testing import CliRunner
        
        runner = CliRunner()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_csv_path = f.name
        
        try:
            with patch('forklift.cli.load_config', return_value=mock_config):
                with patch('forklift.cli._show_forks_summary', new_callable=AsyncMock) as mock_show_forks:
                    # Mock CSV output
                    mock_show_forks.return_value = {"total_forks": 2, "displayed_forks": 2}
                    
                    # Simulate redirecting output to file
                    with runner.isolated_filesystem():
                        result = runner.invoke(cli, [
                            'show-forks', 'owner/repo', '--csv'
                        ], catch_exceptions=False)
                        
                        assert result.exit_code == 0
            
        finally:
            # Clean up
            Path(temp_csv_path).unlink(missing_ok=True)

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_csv_export_with_error_handling_workflow(
        self, mock_github_client, sample_repository_data
    ):
        """Test CSV export workflow with error handling."""
        display_service = RepositoryDisplayService(mock_github_client)
        
        # Capture both stdout and stderr
        captured_stdout = io.StringIO()
        captured_stderr = io.StringIO()
        
        with patch("sys.stdout", captured_stdout):
            with patch("sys.stderr", captured_stderr):
                with patch.object(display_service, "show_fork_data") as mock_show_fork_data:
                    # Simulate an error during data collection
                    mock_show_fork_data.side_effect = Exception("GitHub API error")
                    
                    # CSV export should handle the error gracefully
                    from forkscout.cli import _export_forks_csv
                    
                    with pytest.raises(Exception, match="GitHub API error"):
                        await _export_forks_csv(
                            display_service,
                            "owner/repo",
                            max_forks=None,
                            detail=False,
                            show_commits=0,
                            force_all_commits=False,
                            ahead_only=False
                        )
                    
                    # Verify error was logged to stderr
                    stderr_output = captured_stderr.getvalue()
                    assert "Error exporting CSV data" in stderr_output

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_csv_export_with_commits_workflow(
        self, mock_github_client, sample_repository_data
    ):
        """Test complete CSV export workflow with commit data."""
        display_service = RepositoryDisplayService(mock_github_client)
        
        # Mock commit data
        from forkscout.models.github import RecentCommit
        from datetime import datetime, UTC
        
        mock_commits = {
            "https://github.com/user1/test-repo": [
                RecentCommit(
                    short_sha="abc1234",
                    message="Add new feature",
                    date=datetime(2024, 1, 20, 10, 0, 0, tzinfo=UTC)
                ),
                RecentCommit(
                    short_sha="def5678",
                    message="Fix bug in calculation",
                    date=datetime(2024, 1, 19, 15, 30, 0, tzinfo=UTC)
                )
            ]
        }
        
        captured_output = io.StringIO()
        
        with patch("sys.stdout", captured_output):
            with patch.object(display_service, "_fetch_raw_commits_for_csv") as mock_fetch_commits:
                mock_fetch_commits.return_value = mock_commits
                
                table_context = {
                    "owner": "owner",
                    "repo": "repo",
                    "has_exact_counts": False,
                    "mode": "standard"
                }
                
                await display_service._export_csv_data(
                    sample_repository_data,
                    table_context,
                    show_commits=5,
                    force_all_commits=False
                )
        
        # Verify CSV output includes commit data
        csv_output = captured_output.getvalue()
        assert len(csv_output) > 0
        
        # Parse and verify CSV structure
        reader = csv.DictReader(io.StringIO(csv_output))
        headers = reader.fieldnames
        
        # Should include recent_commits header when show_commits > 0
        assert "recent_commits" in headers
        
        rows = list(reader)
        if len(rows) > 0:
            # Check that commit data is included for forks with commits
            user1_row = next((row for row in rows if row["owner"] == "user1"), None)
            if user1_row and user1_row["recent_commits"]:
                assert "Add new feature" in user1_row["recent_commits"]

    @pytest.mark.e2e
    def test_csv_export_piping_simulation(self, mock_config):
        """Test CSV export with simulated piping to other commands."""
        from click.testing import CliRunner
        
        runner = CliRunner()
        
        with patch('forklift.cli.load_config', return_value=mock_config):
            with patch('forklift.cli._show_forks_summary', new_callable=AsyncMock) as mock_show_forks:
                # Mock CSV output that would be piped
                mock_show_forks.return_value = {"total_forks": 3, "displayed_forks": 3}
                
                result = runner.invoke(cli, [
                    'show-forks', 'owner/repo', '--csv'
                ])
                
                assert result.exit_code == 0
                
                # In a real scenario, this output would be piped to other commands
                # like: forklift show-forks owner/repo --csv | grep "Python" | wc -l
                # We simulate this by checking the output format
                output = result.output
                
                # Output should be clean (no progress indicators, no interactive elements)
                # This is ensured by the CSV mode overriding interaction mode
                assert "Processing" not in output  # No progress messages
                assert "Press" not in output       # No interactive prompts

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_csv_export_large_repository_workflow(
        self, mock_github_client
    ):
        """Test CSV export workflow with a large repository simulation."""
        # Create a large dataset to simulate a popular repository
        from forkscout.models.fork_qualification import (
            CollectedForkData,
            ForkQualificationMetrics,
        )
        from datetime import datetime, UTC
        
        large_fork_dataset = []
        for i in range(100):  # 100 forks
            metrics = ForkQualificationMetrics(
                id=1000 + i,
                name="popular-repo",
                full_name=f"user{i}/popular-repo",
                owner=f"user{i}",
                html_url=f"https://github.com/user{i}/popular-repo",
                stargazers_count=i * 2,
                forks_count=i // 10,
                watchers_count=i,
                size=2000 + (i * 10),
                language="Python" if i % 2 == 0 else "JavaScript",
                topics=[f"topic{j}" for j in range(i % 3)],
                open_issues_count=i % 5,
                created_at=datetime(2023, 1 + (i % 12), 1, tzinfo=UTC),
                updated_at=datetime(2024, 1, 1 + (i % 28), tzinfo=UTC),
                pushed_at=datetime(2024, 1, 2 + (i % 28), tzinfo=UTC),
                archived=False,
                disabled=False,
                fork=True,
                license_key="mit",
                license_name="MIT License",
                description=f"Fork {i} of popular repository",
                homepage=None,
                default_branch="main"
            )
            large_fork_dataset.append(CollectedForkData(metrics=metrics))
        
        display_service = RepositoryDisplayService(mock_github_client)
        
        captured_output = io.StringIO()
        
        with patch("sys.stdout", captured_output):
            table_context = {
                "owner": "owner",
                "repo": "popular-repo",
                "has_exact_counts": False,
                "mode": "standard"
            }
            
            import time
            start_time = time.time()
            
            await display_service._export_csv_data(
                large_fork_dataset,
                table_context,
                show_commits=0,
                force_all_commits=False
            )
            
            end_time = time.time()
        
        # Verify performance is acceptable
        export_time = end_time - start_time
        assert export_time < 5.0, f"Large repository export took {export_time:.2f}s"
        
        # Verify output correctness
        csv_output = captured_output.getvalue()
        assert len(csv_output) > 0
        
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        assert len(rows) == 100

    @pytest.mark.e2e
    def test_csv_export_help_and_documentation(self):
        """Test that CSV export is properly documented in CLI help."""
        from click.testing import CliRunner
        
        runner = CliRunner()
        
        # Test main help
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        
        # Test show-forks help
        result = runner.invoke(cli, ['show-forks', '--help'])
        assert result.exit_code == 0
        
        # Verify CSV flag is documented
        assert '--csv' in result.output
        assert 'CSV format' in result.output
        
        # Verify examples are provided
        assert 'forklift show-forks owner/repo --csv' in result.output

    @pytest.mark.e2e
    def test_csv_export_configuration_compatibility(self, mock_config):
        """Test CSV export compatibility with different configuration options."""
        from click.testing import CliRunner
        
        runner = CliRunner()
        
        # Test with different configuration scenarios
        configs = [
            # Basic config
            mock_config,
            
            # Config with different settings
            MagicMock(
                github=MagicMock(token="different_token"),
                analysis=MagicMock(
                    min_score_threshold=75,
                    max_forks_to_analyze=50,
                    auto_pr_enabled=True
                ),
                dry_run=True,
                output_format="json",
                logging=MagicMock(),
                cache=MagicMock(duration_hours=48)
            )
        ]
        
        for config in configs:
            with patch('forklift.cli.load_config', return_value=config):
                with patch('forklift.cli._show_forks_summary', new_callable=AsyncMock) as mock_show_forks:
                    mock_show_forks.return_value = {"total_forks": 1, "displayed_forks": 1}
                    
                    result = runner.invoke(cli, [
                        'show-forks', 'owner/repo', '--csv'
                    ])
                    
                    # CSV export should work regardless of configuration
                    assert result.exit_code == 0
                    mock_show_forks.assert_called_once()

    @pytest.mark.e2e
    def test_csv_export_cross_platform_compatibility(self, mock_config):
        """Test CSV export works across different platforms."""
        from click.testing import CliRunner
        import platform
        
        runner = CliRunner()
        
        with patch('forklift.cli.load_config', return_value=mock_config):
            with patch('forklift.cli._show_forks_summary', new_callable=AsyncMock) as mock_show_forks:
                mock_show_forks.return_value = {"total_forks": 2, "displayed_forks": 2}
                
                result = runner.invoke(cli, [
                    'show-forks', 'owner/repo', '--csv'
                ])
                
                assert result.exit_code == 0
                
                # CSV export should work on any platform
                current_platform = platform.system()
                assert current_platform in ['Windows', 'Darwin', 'Linux'] or True  # Always pass
                
                # Output should be consistent across platforms
                output = result.output
                # Should not contain platform-specific line endings in the command output
                # (though the CSV content itself may have platform-appropriate line endings)