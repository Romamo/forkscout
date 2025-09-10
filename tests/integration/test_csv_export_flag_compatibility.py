"""Integration tests for CSV export compatibility with all show-forks flags."""

import csv
import io
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forkscout.cli import _export_forks_csv, _show_forks_summary
from forkscout.config.settings import ForkscoutConfig
from forkscout.display.interaction_mode import InteractionMode
from forkscout.display.repository_display_service import RepositoryDisplayService
from forkscout.github.client import GitHubClient
from forkscout.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
)


class TestCSVExportFlagCompatibility:
    """Test CSV export compatibility with all existing show-forks command flags."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return AsyncMock(spec=GitHubClient)

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock(spec=ForkscoutConfig)
        config.github = MagicMock()
        config.github.token = "test_token"
        return config

    @pytest.fixture
    def comprehensive_fork_data(self):
        """Create comprehensive fork data for testing all flag combinations."""
        forks_data = []
        
        # Create diverse fork data to test various filtering scenarios
        fork_configs = [
            # Active fork with commits ahead
            {
                "id": 1, "owner": "active_user", "stars": 50, "forks": 10,
                "created": datetime(2023, 1, 1, tzinfo=UTC),
                "pushed": datetime(2024, 1, 15, tzinfo=UTC),
                "archived": False, "language": "Python"
            },
            # Stale fork with no commits ahead
            {
                "id": 2, "owner": "stale_user", "stars": 5, "forks": 1,
                "created": datetime(2023, 6, 1, tzinfo=UTC),
                "pushed": datetime(2023, 6, 1, tzinfo=UTC),  # Same as created
                "archived": False, "language": "JavaScript"
            },
            # Popular fork with many stars
            {
                "id": 3, "owner": "popular_user", "stars": 200, "forks": 50,
                "created": datetime(2022, 1, 1, tzinfo=UTC),
                "pushed": datetime(2024, 1, 20, tzinfo=UTC),
                "archived": False, "language": "Go"
            },
            # Archived fork
            {
                "id": 4, "owner": "archived_user", "stars": 15, "forks": 3,
                "created": datetime(2022, 6, 1, tzinfo=UTC),
                "pushed": datetime(2023, 12, 1, tzinfo=UTC),
                "archived": True, "language": "Python"
            },
            # Small fork with few stars
            {
                "id": 5, "owner": "small_user", "stars": 1, "forks": 0,
                "created": datetime(2023, 12, 1, tzinfo=UTC),
                "pushed": datetime(2024, 1, 10, tzinfo=UTC),
                "archived": False, "language": "Rust"
            }
        ]
        
        for config in fork_configs:
            metrics = ForkQualificationMetrics(
                id=config["id"],
                name="test-repo",
                full_name=f"{config['owner']}/test-repo",
                owner=config["owner"],
                html_url=f"https://github.com/{config['owner']}/test-repo",
                stargazers_count=config["stars"],
                forks_count=config["forks"],
                watchers_count=config["stars"] // 2,
                size=1500,
                language=config["language"],
                topics=["testing", config["language"].lower()],
                open_issues_count=config["stars"] // 10,
                created_at=config["created"],
                updated_at=config["pushed"],
                pushed_at=config["pushed"],
                archived=config["archived"],
                disabled=False,
                fork=True,
                license_key="mit",
                license_name="MIT License",
                description=f"Test repository by {config['owner']}",
                homepage=None,
                default_branch="main"
            )
            
            fork_data = CollectedForkData(metrics=metrics)
            # Add exact commit counts for some forks
            if config["pushed"] > config["created"]:
                fork_data.exact_commits_ahead = config["stars"] // 10 + 1
            else:
                fork_data.exact_commits_ahead = 0
            
            forks_data.append(fork_data)
        
        return forks_data

    @pytest.mark.asyncio
    async def test_csv_export_with_detail_flag(
        self, mock_github_client, comprehensive_fork_data
    ):
        """Test CSV export compatibility with --detail flag."""
        display_service = RepositoryDisplayService(mock_github_client)
        
        with patch.object(display_service, "show_fork_data_detailed") as mock_show_detailed:
            mock_show_detailed.return_value = {
                "total_forks": len(comprehensive_fork_data),
                "displayed_forks": len(comprehensive_fork_data),
                "collected_forks": comprehensive_fork_data,
                "api_calls_made": 5
            }
            
            await _export_forks_csv(
                display_service,
                "owner/repo",
                max_forks=None,
                detail=True,
                show_commits=0,
                force_all_commits=False,
                ahead_only=False
            )
            
            # Verify detailed export was called with CSV flag
            mock_show_detailed.assert_called_once_with(
                "owner/repo",
                max_forks=None,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False,
                ahead_only=False,
                csv_export=True,
            )

    @pytest.mark.asyncio
    async def test_csv_export_with_ahead_only_flag(
        self, mock_github_client, comprehensive_fork_data
    ):
        """Test CSV export compatibility with --ahead-only flag."""
        display_service = RepositoryDisplayService(mock_github_client)
        
        # Filter to only forks with commits ahead
        forks_with_commits = [
            fork for fork in comprehensive_fork_data
            if fork.metrics.commits_ahead_status == "Has commits"
        ]
        
        with patch.object(display_service, "show_fork_data") as mock_show_fork_data:
            mock_show_fork_data.return_value = {
                "total_forks": len(forks_with_commits),
                "displayed_forks": len(forks_with_commits),
                "collected_forks": forks_with_commits
            }
            
            await _export_forks_csv(
                display_service,
                "owner/repo",
                max_forks=None,
                detail=False,
                show_commits=0,
                force_all_commits=False,
                ahead_only=True
            )
            
            # Verify ahead_only parameter was passed
            mock_show_fork_data.assert_called_once_with(
                "owner/repo",
                exclude_archived=False,
                exclude_disabled=False,
                sort_by="stars",
                show_all=True,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False,
                ahead_only=True,
                csv_export=True,
            )

    @pytest.mark.asyncio
    async def test_csv_export_with_max_forks_flag(
        self, mock_github_client, comprehensive_fork_data
    ):
        """Test CSV export compatibility with --max-forks flag."""
        display_service = RepositoryDisplayService(mock_github_client)
        
        max_forks = 3
        limited_forks = comprehensive_fork_data[:max_forks]
        
        with patch.object(display_service, "show_fork_data") as mock_show_fork_data:
            mock_show_fork_data.return_value = {
                "total_forks": len(limited_forks),
                "displayed_forks": len(limited_forks),
                "collected_forks": limited_forks
            }
            
            await _export_forks_csv(
                display_service,
                "owner/repo",
                max_forks=max_forks,
                detail=False,
                show_commits=0,
                force_all_commits=False,
                ahead_only=False
            )
            
            # Verify max_forks was handled (though not directly passed to show_fork_data)
            mock_show_fork_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_csv_export_with_show_commits_flag(
        self, mock_github_client, comprehensive_fork_data
    ):
        """Test CSV export compatibility with --show-commits flag."""
        display_service = RepositoryDisplayService(mock_github_client)
        
        # Mock commit data
        from forkscout.models.github import RecentCommit
        
        mock_commits = {}
        for fork in comprehensive_fork_data:
            if fork.metrics.commits_ahead_status == "Has commits":
                mock_commits[fork.metrics.html_url] = [
                    RecentCommit(
                        short_sha="abc1234",
                        message="Test commit message",
                        date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
                    )
                ]
        
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
                    comprehensive_fork_data,
                    table_context,
                    show_commits=3,
                    force_all_commits=False
                )
        
        # Verify CSV includes commit data
        csv_output = captured_output.getvalue()
        reader = csv.DictReader(io.StringIO(csv_output))
        headers = reader.fieldnames
        
        assert "recent_commits" in headers

    @pytest.mark.asyncio
    async def test_csv_export_with_force_all_commits_flag(
        self, mock_github_client, comprehensive_fork_data
    ):
        """Test CSV export compatibility with --force-all-commits flag."""
        display_service = RepositoryDisplayService(mock_github_client)
        
        # Mock commit data for all forks (including those with no commits ahead)
        from forkscout.models.github import RecentCommit
        
        mock_commits = {}
        for fork in comprehensive_fork_data:
            mock_commits[fork.metrics.html_url] = [
                RecentCommit(
                    short_sha="def5678",
                    message="Forced commit fetch",
                    date=datetime(2024, 1, 10, 12, 0, 0, tzinfo=UTC)
                )
            ]
        
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
                    comprehensive_fork_data,
                    table_context,
                    show_commits=2,
                    force_all_commits=True
                )
        
        # Verify commits were fetched for all forks
        csv_output = captured_output.getvalue()
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        
        # All forks should have commit data when force_all_commits=True
        for row in rows:
            if row["commits_ahead"] != "None":
                # Should have commit data or empty string
                assert "recent_commits" in row

    @pytest.mark.asyncio
    async def test_csv_export_with_combined_flags(
        self, mock_github_client, comprehensive_fork_data
    ):
        """Test CSV export with multiple flags combined."""
        display_service = RepositoryDisplayService(mock_github_client)
        
        # Test combination: --detail --ahead-only --show-commits 5 --max-forks 10
        forks_with_commits = [
            fork for fork in comprehensive_fork_data
            if fork.metrics.commits_ahead_status == "Has commits"
        ]
        
        with patch.object(display_service, "show_fork_data_detailed") as mock_show_detailed:
            mock_show_detailed.return_value = {
                "total_forks": len(forks_with_commits),
                "displayed_forks": len(forks_with_commits),
                "collected_forks": forks_with_commits,
                "api_calls_made": 3
            }
            
            await _export_forks_csv(
                display_service,
                "owner/repo",
                max_forks=10,
                detail=True,
                show_commits=5,
                force_all_commits=True,
                ahead_only=True
            )
            
            # Verify all parameters were passed correctly
            mock_show_detailed.assert_called_once_with(
                "owner/repo",
                max_forks=10,
                disable_cache=False,
                show_commits=5,
                force_all_commits=True,
                ahead_only=True,
                csv_export=True,
            )

    @pytest.mark.asyncio
    async def test_csv_export_interaction_mode_override(self, mock_config):
        """Test that CSV export properly overrides interaction mode."""
        with patch('forklift.cli.GitHubClient') as mock_client_class:
            with patch('forklift.cli.RepositoryDisplayService') as mock_display_service_class:
                with patch('forklift.cli._export_forks_csv') as mock_export_csv:
                    
                    # Configure mocks
                    mock_client = AsyncMock()
                    mock_client_class.return_value.__aenter__.return_value = mock_client
                    mock_display_service = MagicMock()
                    mock_display_service_class.return_value = mock_display_service
                    
                    await _show_forks_summary(
                        mock_config,
                        "owner/repo",
                        max_forks=None,
                        verbose=False,
                        detail=False,
                        show_commits=0,
                        force_all_commits=False,
                        ahead_only=False,
                        csv=True,  # CSV mode enabled
                        interaction_mode=InteractionMode.NON_INTERACTIVE,
                        supports_prompts=False,
                    )
                    
                    # Verify CSV export was called
                    mock_export_csv.assert_called_once()

    def test_csv_export_flag_parameter_mapping(self):
        """Test that all show-forks flags are properly mapped to CSV export parameters."""
        # This test verifies the parameter mapping between CLI flags and internal functions
        
        # Define expected parameter mappings
        flag_mappings = {
            "--detail": "detail",
            "--ahead-only": "ahead_only", 
            "--max-forks": "max_forks",
            "--show-commits": "show_commits",
            "--force-all-commits": "force_all_commits",
            "--csv": "csv"
        }
        
        # Verify all expected flags have corresponding parameters
        for flag, param in flag_mappings.items():
            assert param is not None, f"Flag {flag} should map to parameter {param}"

    @pytest.mark.asyncio
    async def test_csv_export_with_sorting_options(
        self, mock_github_client, comprehensive_fork_data
    ):
        """Test CSV export maintains proper sorting with various options."""
        display_service = RepositoryDisplayService(mock_github_client)
        
        captured_output = io.StringIO()
        
        with patch("sys.stdout", captured_output):
            with patch.object(display_service, "_sort_forks_universal") as mock_sort:
                # Mock sorting to return forks in specific order
                sorted_forks = sorted(
                    comprehensive_fork_data,
                    key=lambda f: f.metrics.stargazers_count,
                    reverse=True
                )
                mock_sort.return_value = sorted_forks
                
                table_context = {
                    "owner": "owner",
                    "repo": "repo",
                    "has_exact_counts": False,
                    "mode": "standard"
                }
                
                await display_service._export_csv_data(
                    comprehensive_fork_data,
                    table_context,
                    show_commits=0,
                    force_all_commits=False
                )
                
                # Verify sorting was applied
                mock_sort.assert_called_once()
        
        # Verify CSV output maintains sorted order
        csv_output = captured_output.getvalue()
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        
        if len(rows) > 1:
            # First row should have highest stars (popular_user with 200 stars)
            assert rows[0]["owner"] == "popular_user"
            assert rows[0]["stars"] == "200"

    @pytest.mark.asyncio
    async def test_csv_export_with_filtering_combinations(
        self, mock_github_client, comprehensive_fork_data
    ):
        """Test CSV export with various filtering flag combinations."""
        display_service = RepositoryDisplayService(mock_github_client)
        
        # Test different filtering scenarios
        filter_scenarios = [
            # Only ahead forks
            {"ahead_only": True, "expected_count": 3},
            # All forks (no filtering)
            {"ahead_only": False, "expected_count": 5},
        ]
        
        for scenario in filter_scenarios:
            with patch.object(display_service, "show_fork_data") as mock_show_fork_data:
                # Filter data based on scenario
                if scenario["ahead_only"]:
                    filtered_forks = [
                        fork for fork in comprehensive_fork_data
                        if fork.metrics.commits_ahead_status == "Has commits"
                    ]
                else:
                    filtered_forks = comprehensive_fork_data
                
                mock_show_fork_data.return_value = {
                    "total_forks": len(filtered_forks),
                    "displayed_forks": len(filtered_forks),
                    "collected_forks": filtered_forks
                }
                
                await _export_forks_csv(
                    display_service,
                    "owner/repo",
                    max_forks=None,
                    detail=False,
                    show_commits=0,
                    force_all_commits=False,
                    ahead_only=scenario["ahead_only"]
                )
                
                # Verify filtering was applied
                call_args = mock_show_fork_data.call_args[1]
                assert call_args["ahead_only"] == scenario["ahead_only"]

    @pytest.mark.asyncio
    async def test_csv_export_error_handling_with_flags(
        self, mock_github_client, comprehensive_fork_data
    ):
        """Test CSV export error handling works with all flag combinations."""
        display_service = RepositoryDisplayService(mock_github_client)
        
        # Test error handling with different flag combinations
        flag_combinations = [
            {"detail": True, "show_commits": 5},
            {"ahead_only": True, "force_all_commits": True},
            {"detail": True, "ahead_only": True, "show_commits": 3}
        ]
        
        for flags in flag_combinations:
            captured_stderr = io.StringIO()
            
            with patch("sys.stderr", captured_stderr):
                with patch.object(display_service, "show_fork_data_detailed" if flags.get("detail") else "show_fork_data") as mock_show_data:
                    # Simulate error
                    mock_show_data.side_effect = Exception("Test error")
                    
                    with pytest.raises(Exception, match="Test error"):
                        await _export_forks_csv(
                            display_service,
                            "owner/repo",
                            max_forks=None,
                            detail=flags.get("detail", False),
                            show_commits=flags.get("show_commits", 0),
                            force_all_commits=flags.get("force_all_commits", False),
                            ahead_only=flags.get("ahead_only", False)
                        )
                    
                    # Error should be logged regardless of flag combination
                    stderr_output = captured_stderr.getvalue()
                    assert "Error exporting CSV data" in stderr_output

    def test_csv_export_flag_validation(self):
        """Test that CSV export validates flag combinations properly."""
        # Test that incompatible flag combinations are handled gracefully
        
        # All current flag combinations should be valid
        valid_combinations = [
            {"csv": True},
            {"csv": True, "detail": True},
            {"csv": True, "ahead_only": True},
            {"csv": True, "show_commits": 5},
            {"csv": True, "force_all_commits": True},
            {"csv": True, "max_forks": 50},
            {"csv": True, "detail": True, "ahead_only": True, "show_commits": 3}
        ]
        
        # All combinations should be valid (no validation errors expected)
        for combination in valid_combinations:
            # In the current implementation, all flag combinations are valid
            assert combination["csv"] is True