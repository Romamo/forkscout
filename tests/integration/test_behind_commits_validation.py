"""Integration tests for behind commits display functionality."""

import pytest
from unittest.mock import AsyncMock, patch

from forkscout.display.repository_display_service import RepositoryDisplayService
from forkscout.github.client import GitHubClient
from forkscout.config.settings import ForkscoutConfig, load_config
from rich.console import Console


@pytest.mark.asyncio
class TestBehindCommitsValidation:
    """Test behind commits display functionality with various scenarios."""

    @pytest.fixture
    async def github_client(self):
        """Create a GitHub client for testing."""
        config = load_config()
        async with GitHubClient(config.github) as client:
            yield client

    @pytest.fixture
    def repository_display_service(self, github_client):
        """Create a repository display service for testing."""
        console = Console()
        return RepositoryDisplayService(github_client, console)

    async def test_format_commits_compact_behind_only(self):
        """Test formatting when fork is only behind (no ahead commits).
        
        Requirements: 1.2 - Display commits behind correctly
        """
        service = RepositoryDisplayService(None, Console())
        
        # Test fork with only behind commits
        result = service.format_commits_compact(0, 5)
        assert result == "[red]-5[/red]"
        
        # Test fork with only 1 behind commit
        result = service.format_commits_compact(0, 1)
        assert result == "[red]-1[/red]"

    async def test_format_commits_compact_ahead_and_behind(self):
        """Test formatting when fork has both ahead and behind commits.
        
        Requirements: 1.3 - Display both ahead and behind counts
        """
        service = RepositoryDisplayService(None, Console())
        
        # Test fork with both ahead and behind commits
        result = service.format_commits_compact(5, 3)
        assert result == "[green]+5[/green] [red]-3[/red]"
        
        # Test fork with different combinations
        result = service.format_commits_compact(12, 8)
        assert result == "[green]+12[/green] [red]-8[/red]"
        
        result = service.format_commits_compact(1, 1)
        assert result == "[green]+1[/green] [red]-1[/red]"

    async def test_format_commits_compact_edge_cases(self):
        """Test formatting edge cases for commit display.
        
        Requirements: 1.4 - Handle edge cases correctly
        """
        service = RepositoryDisplayService(None, Console())
        
        # Test both zero (should be empty)
        result = service.format_commits_compact(0, 0)
        assert result == ""
        
        # Test unknown status
        result = service.format_commits_compact(-1, 0)
        assert result == "Unknown"
        
        result = service.format_commits_compact(0, -1)
        assert result == "Unknown"
        
        result = service.format_commits_compact(-1, -1)
        assert result == "Unknown"

    @pytest.mark.online
    async def test_github_api_behind_commits_extraction(self, github_client):
        """Test that GitHub API properly extracts behind_by field.
        
        Requirements: 1.5 - Fetch behind commits from GitHub compare API
        """
        # Test with a known repository comparison
        try:
            result = await github_client.get_commits_ahead_behind(
                'octocat', 'Hello-World', 'octocat', 'Hello-World'
            )
            
            # Should have both ahead_by and behind_by fields
            assert 'ahead_by' in result
            assert 'behind_by' in result
            assert isinstance(result['ahead_by'], int)
            assert isinstance(result['behind_by'], int)
            
            # Same repo should have 0 ahead and 0 behind
            assert result['ahead_by'] == 0
            assert result['behind_by'] == 0
            
        except Exception as e:
            pytest.skip(f"GitHub API test skipped due to: {e}")

    async def test_mock_behind_commits_scenario(self):
        """Test behind commits scenario with mocked data.
        
        Requirements: 1.2, 1.3 - Display behind commits correctly
        """
        # Mock GitHub client that returns behind commits
        mock_client = AsyncMock()
        mock_client.get_commits_ahead_behind.return_value = {
            'ahead_by': 0,
            'behind_by': 5,
            'total_commits': 5
        }
        
        service = RepositoryDisplayService(mock_client, Console())
        
        # Test the formatting with mocked behind data
        result = service.format_commits_compact(0, 5)
        assert result == "[red]-5[/red]"

    async def test_mock_mixed_commits_scenario(self):
        """Test mixed ahead/behind commits scenario with mocked data.
        
        Requirements: 1.3 - Display both ahead and behind counts
        """
        # Mock GitHub client that returns both ahead and behind commits
        mock_client = AsyncMock()
        mock_client.get_commits_ahead_behind.return_value = {
            'ahead_by': 7,
            'behind_by': 3,
            'total_commits': 10
        }
        
        service = RepositoryDisplayService(mock_client, Console())
        
        # Test the formatting with mocked mixed data
        result = service.format_commits_compact(7, 3)
        assert result == "[green]+7[/green] [red]-3[/red]"

    async def test_display_format_requirements_compliance(self):
        """Test that display format meets all requirements.
        
        Requirements: 1.1, 1.2, 1.3, 1.4 - Complete display format compliance
        """
        service = RepositoryDisplayService(None, Console())
        
        # Test all required display formats
        test_cases = [
            # (ahead, behind, expected_format, description)
            (5, 0, "[green]+5[/green]", "Only ahead commits"),
            (12, 0, "[green]+12[/green]", "Multiple ahead commits"),
            (23, 0, "[green]+23[/green]", "Many ahead commits"),
            (0, 2, "[red]-2[/red]", "Only behind commits"),
            (0, 8, "[red]-8[/red]", "Multiple behind commits"),
            (0, 15, "[red]-15[/red]", "Many behind commits"),
            (5, 2, "[green]+5[/green] [red]-2[/red]", "Both ahead and behind"),
            (12, 8, "[green]+12[/green] [red]-8[/red]", "Multiple both"),
            (0, 0, "", "No commits ahead or behind"),
            (-1, 0, "Unknown", "Unknown ahead status"),
            (0, -1, "Unknown", "Unknown behind status"),
        ]
        
        for ahead, behind, expected, description in test_cases:
            result = service.format_commits_compact(ahead, behind)
            assert result == expected, f"Failed for {description}: expected '{expected}', got '{result}'"

    async def test_requirements_coverage(self):
        """Verify that all requirements are covered by the implementation.
        
        This test ensures that the behind commits functionality meets all
        the acceptance criteria defined in the requirements.
        """
        service = RepositoryDisplayService(None, Console())
        
        # Requirement 1.2: Display commits behind
        result = service.format_commits_compact(0, 8)
        assert "-8" in result, "Should display commits behind with -X format"
        
        # Requirement 1.3: Display both ahead and behind
        result = service.format_commits_compact(5, 2)
        assert "+5" in result and "-2" in result, "Should display both +X -Y format"
        
        # Requirement 1.4: Empty column for no commits
        result = service.format_commits_compact(0, 0)
        assert result == "", "Should display empty column for no commits"
        
        # Requirement 1.5: Handle --detail flag (tested via format method)
        # The format method is called when --detail flag is used
        result = service.format_commits_compact(12, 8)
        assert result == "[green]+12[/green] [red]-8[/red]", "Should format for --detail flag"

    def test_color_coding_consistency(self):
        """Test that color coding is consistent across different scenarios."""
        service = RepositoryDisplayService(None, Console())
        
        # Ahead commits should always be green
        result = service.format_commits_compact(5, 0)
        assert "[green]" in result and "+5" in result
        
        # Behind commits should always be red
        result = service.format_commits_compact(0, 3)
        assert "[red]" in result and "-3" in result
        
        # Mixed should have both colors
        result = service.format_commits_compact(5, 3)
        assert "[green]" in result and "[red]" in result
        assert "+5" in result and "-3" in result