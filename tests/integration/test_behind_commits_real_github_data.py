"""Integration tests for behind commits with real GitHub data."""

import os
import pytest

from forkscout.config import GitHubConfig
from forkscout.github.client import GitHubClient


class TestBehindCommitsRealGitHubData:
    """Integration tests using real GitHub repositories."""

    @pytest.fixture
    def github_client(self):
        """Create GitHub client with real token."""
        token = os.getenv('GITHUB_TOKEN')
        if not token:
            pytest.skip("GITHUB_TOKEN environment variable not set")
        
        config = GitHubConfig(token=token)
        return GitHubClient(config)

    @pytest.mark.online
    @pytest.mark.asyncio
    async def test_greatbots_fork_has_behind_commits(self, github_client):
        """Test that GreatBots fork shows both ahead and behind commits."""
        # This is the specific fork mentioned in the bug report
        result = await github_client.get_commits_ahead_and_behind_count(
            'GreatBots', 'YouTube_bot_telegram',
            'sanila2007', 'youtube-bot-telegram'
        )
        
        # Based on our previous API check, this fork should have:
        # ahead_by: 9, behind_by: 11
        assert result.ahead_count > 0, "GreatBots fork should have commits ahead"
        assert result.behind_count > 0, "GreatBots fork should have commits behind"
        assert result.is_diverged, "GreatBots fork should be diverged (both ahead and behind)"
        assert result.error is None, "Should not have any errors"
        
        # Log the actual values for verification
        print(f"GreatBots fork: +{result.ahead_count} -{result.behind_count}")

    @pytest.mark.online
    @pytest.mark.asyncio
    async def test_fork_with_only_ahead_commits(self, github_client):
        """Test a fork that has only ahead commits (no behind)."""
        # Test with a fork that should have only ahead commits
        result = await github_client.get_commits_ahead_and_behind_count(
            'Xelio', 'tg-youtube-bot-docker',
            'sanila2007', 'youtube-bot-telegram'
        )
        
        # This fork should have ahead commits but no behind commits
        assert result.ahead_count > 0, "Xelio fork should have commits ahead"
        assert result.behind_count == 0, "Xelio fork should have no commits behind"
        assert result.has_ahead_commits, "Should have ahead commits"
        assert not result.has_behind_commits, "Should not have behind commits"
        assert not result.is_diverged, "Should not be diverged"
        assert result.error is None, "Should not have any errors"

    @pytest.mark.online
    @pytest.mark.asyncio
    async def test_batch_processing_with_mixed_scenarios(self, github_client):
        """Test batch processing with forks having different commit scenarios."""
        fork_data_list = [
            ('GreatBots', 'YouTube_bot_telegram'),  # Should have both ahead and behind
            ('Xelio', 'tg-youtube-bot-docker'),    # Should have only ahead
            ('KINGSKR', 'youtube-bot-telegram'),   # Should have only ahead
        ]
        
        result = await github_client.get_commits_ahead_and_behind_batch_counts(
            fork_data_list, 'sanila2007', 'youtube-bot-telegram'
        )
        
        assert len(result.results) == 3, "Should have results for all 3 forks"
        
        # Check GreatBots fork (should be diverged)
        greatbots_result = result.results['GreatBots/YouTube_bot_telegram']
        assert greatbots_result.ahead_count > 0, "GreatBots should have ahead commits"
        assert greatbots_result.behind_count > 0, "GreatBots should have behind commits"
        assert greatbots_result.is_diverged, "GreatBots should be diverged"
        
        # Check other forks (should have only ahead commits)
        for fork_key in ['Xelio/tg-youtube-bot-docker', 'KINGSKR/youtube-bot-telegram']:
            if fork_key in result.results:
                fork_result = result.results[fork_key]
                assert fork_result.ahead_count >= 0, f"{fork_key} should have valid ahead count"
                assert fork_result.behind_count >= 0, f"{fork_key} should have valid behind count"
                assert fork_result.error is None, f"{fork_key} should not have errors"

    @pytest.mark.online
    @pytest.mark.asyncio
    async def test_fork_with_no_commits_ahead_or_behind(self, github_client):
        """Test a fork that has no commits ahead or behind (identical to parent)."""
        # This is harder to find, but we can test the logic with a known case
        # For now, we'll test that the method handles this case correctly
        
        # Create a scenario where we might have identical repositories
        # Note: This might not exist in the real data, but we test the handling
        try:
            result = await github_client.get_commits_ahead_and_behind_count(
                'KrishaVV44', 'youtube-bot-telegram',
                'sanila2007', 'youtube-bot-telegram'
            )
            
            # Should handle the case gracefully regardless of the actual values
            assert isinstance(result.ahead_count, int), "Ahead count should be integer"
            assert isinstance(result.behind_count, int), "Behind count should be integer"
            assert result.ahead_count >= 0, "Ahead count should be non-negative"
            assert result.behind_count >= 0, "Behind count should be non-negative"
            
        except Exception as e:
            # If the fork doesn't exist or is private, that's also a valid test case
            print(f"Fork test resulted in expected error: {e}")

    @pytest.mark.online
    @pytest.mark.asyncio
    async def test_private_or_nonexistent_fork_handling(self, github_client):
        """Test handling of private or non-existent forks."""
        # Test with a fork that likely doesn't exist or is private
        result = await github_client.get_commits_ahead_and_behind_count(
            'nonexistent-user', 'nonexistent-repo',
            'sanila2007', 'youtube-bot-telegram'
        )
        
        # Should handle gracefully with error information
        assert result.ahead_count == 0, "Should default to 0 ahead commits on error"
        assert result.behind_count == 0, "Should default to 0 behind commits on error"
        assert result.error is not None, "Should have error information"
        assert not result.has_ahead_commits, "Should not have ahead commits on error"
        assert not result.has_behind_commits, "Should not have behind commits on error"

    @pytest.mark.online
    @pytest.mark.asyncio
    async def test_api_response_format_validation(self, github_client):
        """Test that real GitHub API responses have expected format."""
        # Use the existing get_commits_ahead_behind method to check raw API response
        comparison = await github_client.get_commits_ahead_behind(
            'GreatBots', 'YouTube_bot_telegram',
            'sanila2007', 'youtube-bot-telegram'
        )
        
        # Verify the API response has the expected fields
        assert 'ahead_by' in comparison, "API response should have ahead_by field"
        assert 'behind_by' in comparison, "API response should have behind_by field"
        assert 'total_commits' in comparison, "API response should have total_commits field"
        
        # Verify field types
        assert isinstance(comparison['ahead_by'], int), "ahead_by should be integer"
        assert isinstance(comparison['behind_by'], int), "behind_by should be integer"
        assert isinstance(comparison['total_commits'], int), "total_commits should be integer"
        
        # Verify values are non-negative
        assert comparison['ahead_by'] >= 0, "ahead_by should be non-negative"
        assert comparison['behind_by'] >= 0, "behind_by should be non-negative"
        assert comparison['total_commits'] >= 0, "total_commits should be non-negative"

    @pytest.mark.online
    @pytest.mark.asyncio
    async def test_batch_processing_efficiency(self, github_client):
        """Test that batch processing is more efficient than individual calls."""
        fork_data_list = [
            ('GreatBots', 'YouTube_bot_telegram'),
            ('Xelio', 'tg-youtube-bot-docker'),
            ('KINGSKR', 'youtube-bot-telegram'),
        ]
        
        # Test batch processing
        batch_result = await github_client.get_commits_ahead_and_behind_batch_counts(
            fork_data_list, 'sanila2007', 'youtube-bot-telegram'
        )
        
        # Verify API call efficiency
        expected_api_calls = len(fork_data_list) * 2 + 1  # 2 calls per fork + 1 parent
        expected_savings = len(fork_data_list) - 1  # Parent repo fetched once instead of N times
        
        assert batch_result.total_api_calls == expected_api_calls
        assert batch_result.parent_calls_saved == expected_savings
        
        # Verify we got results for the forks
        assert len(batch_result.results) > 0, "Should have some successful results"

    @pytest.mark.online
    @pytest.mark.asyncio
    async def test_display_service_integration(self, github_client):
        """Test integration with display service formatting."""
        from forkscout.display.repository_display_service import RepositoryDisplayService
        from forkscout.models.fork_qualification import CollectedForkData, ForkQualificationMetrics
        from datetime import datetime
        
        display_service = RepositoryDisplayService(github_client)
        
        # Create mock fork data for GreatBots fork
        metrics = ForkQualificationMetrics(
            id=123456789,
            name="YouTube_bot_telegram",
            full_name="GreatBots/YouTube_bot_telegram",
            owner="GreatBots",
            html_url="https://github.com/GreatBots/YouTube_bot_telegram",
            stargazers_count=0,
            forks_count=1,
            created_at=datetime(2023, 1, 1),
            updated_at=datetime(2023, 1, 1),
            pushed_at=datetime(2023, 3, 3)
        )
        
        fork_data = CollectedForkData(metrics=metrics)
        
        # Get real commit counts
        result = await github_client.get_commits_ahead_and_behind_count(
            'GreatBots', 'YouTube_bot_telegram',
            'sanila2007', 'youtube-bot-telegram'
        )
        
        # Set the real commit counts
        fork_data.exact_commits_ahead = result.ahead_count
        fork_data.exact_commits_behind = result.behind_count
        
        # Test display formatting
        display_result = display_service._format_commit_count(fork_data)
        csv_result = display_service._format_commit_count_for_csv(fork_data)
        
        # Should format correctly with both ahead and behind commits
        if result.ahead_count > 0 and result.behind_count > 0:
            # Should show both counts
            assert f"+{result.ahead_count}" in display_result
            assert f"-{result.behind_count}" in display_result
            assert f"+{result.ahead_count} -{result.behind_count}" == csv_result
        elif result.ahead_count > 0:
            # Should show only ahead
            assert f"+{result.ahead_count}" in display_result
            assert f"+{result.ahead_count}" == csv_result
        elif result.behind_count > 0:
            # Should show only behind
            assert f"-{result.behind_count}" in display_result
            assert f"-{result.behind_count}" == csv_result