"""Unit tests for behind commits display formatting."""

import pytest
from unittest.mock import MagicMock

from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.models.fork_qualification import CollectedForkData, ForkQualificationMetrics


class TestBehindCommitsDisplayFormatting:
    """Test display formatting for behind commits."""

    @pytest.fixture
    def display_service(self):
        """Create a display service for testing."""
        github_client = MagicMock()
        return RepositoryDisplayService(github_client)

    @pytest.fixture
    def create_fork_data(self):
        """Helper to create fork data with commit counts."""
        def _create_fork_data(ahead_count=None, behind_count=None, error=None):
            # Create minimal metrics
            metrics = ForkQualificationMetrics(
                id=123,
                name="test-repo",
                full_name="owner/test-repo",
                owner="owner",
                html_url="https://github.com/owner/test-repo",
                created_at="2023-01-01T00:00:00Z",
                updated_at="2023-01-01T00:00:00Z",
                pushed_at="2023-01-01T00:00:00Z"
            )
            
            fork_data = CollectedForkData(metrics=metrics)
            
            if ahead_count is not None:
                fork_data.exact_commits_ahead = ahead_count
            if behind_count is not None:
                fork_data.exact_commits_behind = behind_count
            if error is not None:
                fork_data.commit_count_error = error
                
            return fork_data
        return _create_fork_data

    def test_format_commit_count_ahead_only(self, display_service, create_fork_data):
        """Test formatting forks with only ahead commits."""
        fork_data = create_fork_data(ahead_count=9, behind_count=0)
        result = display_service._format_commit_count(fork_data)
        assert result == "[green]+9[/green]"

    def test_format_commit_count_behind_only(self, display_service, create_fork_data):
        """Test formatting forks with only behind commits."""
        fork_data = create_fork_data(ahead_count=0, behind_count=11)
        result = display_service._format_commit_count(fork_data)
        assert result == "[red]-11[/red]"

    def test_format_commit_count_both_ahead_and_behind(self, display_service, create_fork_data):
        """Test formatting forks with both ahead and behind commits."""
        fork_data = create_fork_data(ahead_count=9, behind_count=11)
        result = display_service._format_commit_count(fork_data)
        assert result == "[green]+9[/green] [red]-11[/red]"

    def test_format_commit_count_no_commits(self, display_service, create_fork_data):
        """Test formatting forks with no commits ahead or behind."""
        fork_data = create_fork_data(ahead_count=0, behind_count=0)
        result = display_service._format_commit_count(fork_data)
        assert result == ""

    def test_format_commit_count_unknown_ahead(self, display_service, create_fork_data):
        """Test formatting when ahead count is unknown."""
        fork_data = create_fork_data(ahead_count="Unknown", behind_count=5)
        result = display_service._format_commit_count(fork_data)
        assert result == "Unknown"

    def test_format_commit_count_unknown_behind(self, display_service, create_fork_data):
        """Test formatting when behind count is unknown."""
        fork_data = create_fork_data(ahead_count=5, behind_count="Unknown")
        result = display_service._format_commit_count(fork_data)
        assert result == "Unknown"

    def test_format_commit_count_with_error(self, display_service, create_fork_data):
        """Test formatting when there's an error."""
        fork_data = create_fork_data(ahead_count=5, behind_count=2, error="API error")
        result = display_service._format_commit_count(fork_data)
        assert result == "Unknown"

    def test_format_commit_count_none_values(self, display_service, create_fork_data):
        """Test formatting when counts are None."""
        fork_data = create_fork_data(ahead_count=None, behind_count=None)
        result = display_service._format_commit_count(fork_data)
        assert result == ""

    def test_format_commit_count_for_csv_ahead_only(self, display_service, create_fork_data):
        """Test CSV formatting for forks with only ahead commits."""
        fork_data = create_fork_data(ahead_count=9, behind_count=0)
        result = display_service._format_commit_count_for_csv(fork_data)
        assert result == "+9"

    def test_format_commit_count_for_csv_behind_only(self, display_service, create_fork_data):
        """Test CSV formatting for forks with only behind commits."""
        fork_data = create_fork_data(ahead_count=0, behind_count=11)
        result = display_service._format_commit_count_for_csv(fork_data)
        assert result == "-11"

    def test_format_commit_count_for_csv_both_ahead_and_behind(self, display_service, create_fork_data):
        """Test CSV formatting for forks with both ahead and behind commits."""
        fork_data = create_fork_data(ahead_count=9, behind_count=11)
        result = display_service._format_commit_count_for_csv(fork_data)
        assert result == "+9 -11"

    def test_format_commit_count_for_csv_no_commits(self, display_service, create_fork_data):
        """Test CSV formatting for forks with no commits."""
        fork_data = create_fork_data(ahead_count=0, behind_count=0)
        result = display_service._format_commit_count_for_csv(fork_data)
        assert result == ""

    def test_format_commit_count_for_csv_unknown(self, display_service, create_fork_data):
        """Test CSV formatting for unknown commit counts."""
        fork_data = create_fork_data(ahead_count="Unknown", behind_count=5)
        result = display_service._format_commit_count_for_csv(fork_data)
        assert result == "Unknown"

    def test_format_commits_compact_all_combinations(self, display_service):
        """Test format_commits_compact method with all combinations."""
        # Only ahead commits
        result = display_service.format_commits_compact(5, 0)
        assert result == "[green]+5[/green]"
        
        # Only behind commits
        result = display_service.format_commits_compact(0, 7)
        assert result == "[red]-7[/red]"
        
        # Both ahead and behind commits
        result = display_service.format_commits_compact(9, 11)
        assert result == "[green]+9[/green] [red]-11[/red]"
        
        # No commits
        result = display_service.format_commits_compact(0, 0)
        assert result == ""
        
        # Unknown status (represented by -1)
        result = display_service.format_commits_compact(-1, 5)
        assert result == "Unknown"
        
        result = display_service.format_commits_compact(5, -1)
        assert result == "Unknown"

    def test_format_commits_display_with_behind_commits(self, display_service, create_fork_data):
        """Test _format_commits_display method includes behind commits."""
        fork_data = create_fork_data(ahead_count=9, behind_count=11)
        
        # Mock the format_commits_compact method to verify it's called
        display_service.format_commits_compact = MagicMock(return_value="[green]+9[/green] [red]-11[/red]")
        
        result = display_service._format_commits_display(fork_data, show_exact_counts=True)
        
        # Verify format_commits_compact was called with correct parameters
        display_service.format_commits_compact.assert_called_once_with(9, 11)
        assert result == "[green]+9[/green] [red]-11[/red]"

    def test_format_commits_display_handles_string_behind_count(self, display_service, create_fork_data):
        """Test _format_commits_display handles string behind count gracefully."""
        fork_data = create_fork_data(ahead_count=5, behind_count="Unknown")
        
        # Should treat string behind count as 0
        display_service.format_commits_compact = MagicMock(return_value="[green]+5[/green]")
        
        result = display_service._format_commits_display(fork_data, show_exact_counts=True)
        
        # Should call with behind_count=0 when it's a string
        display_service.format_commits_compact.assert_called_once_with(5, 0)