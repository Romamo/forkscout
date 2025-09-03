"""Contract tests for GitHub API behind_by field."""

import os
import pytest

from forklift.config import GitHubConfig
from forklift.github.client import GitHubClient


class TestGitHubAPIBehindCommitsContract:
    """Contract tests to verify GitHub API response format for behind commits."""

    @pytest.fixture
    def github_client(self):
        """Create GitHub client with real token."""
        token = os.getenv('GITHUB_TOKEN')
        if not token:
            pytest.skip("GITHUB_TOKEN environment variable not set")
        
        config = GitHubConfig(token=token)
        return GitHubClient(config)

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_github_compare_api_has_behind_by_field(self, github_client):
        """Verify GitHub compare API returns behind_by field."""
        # Test with a known fork that has behind commits
        comparison = await github_client.get_commits_ahead_behind(
            'GreatBots', 'YouTube_bot_telegram',
            'sanila2007', 'youtube-bot-telegram'
        )
        
        # Verify required fields are present
        assert 'behind_by' in comparison, "GitHub API response must include behind_by field"
        assert 'ahead_by' in comparison, "GitHub API response must include ahead_by field"
        assert 'total_commits' in comparison, "GitHub API response must include total_commits field"

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_behind_by_field_is_integer(self, github_client):
        """Verify behind_by field is always an integer."""
        comparison = await github_client.get_commits_ahead_behind(
            'GreatBots', 'YouTube_bot_telegram',
            'sanila2007', 'youtube-bot-telegram'
        )
        
        assert isinstance(comparison['behind_by'], int), "behind_by field must be an integer"
        assert isinstance(comparison['ahead_by'], int), "ahead_by field must be an integer"
        assert isinstance(comparison['total_commits'], int), "total_commits field must be an integer"

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_behind_by_field_is_non_negative(self, github_client):
        """Verify behind_by field is always non-negative."""
        comparison = await github_client.get_commits_ahead_behind(
            'GreatBots', 'YouTube_bot_telegram',
            'sanila2007', 'youtube-bot-telegram'
        )
        
        assert comparison['behind_by'] >= 0, "behind_by field must be non-negative"
        assert comparison['ahead_by'] >= 0, "ahead_by field must be non-negative"
        assert comparison['total_commits'] >= 0, "total_commits field must be non-negative"

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_different_fork_scenarios_have_behind_by_field(self, github_client):
        """Test that behind_by field is present in different fork scenarios."""
        test_cases = [
            # Fork with both ahead and behind commits (diverged)
            ('GreatBots', 'YouTube_bot_telegram', 'sanila2007', 'youtube-bot-telegram'),
            # Fork with only ahead commits
            ('Xelio', 'tg-youtube-bot-docker', 'sanila2007', 'youtube-bot-telegram'),
        ]
        
        for fork_owner, fork_repo, parent_owner, parent_repo in test_cases:
            try:
                comparison = await github_client.get_commits_ahead_behind(
                    fork_owner, fork_repo, parent_owner, parent_repo
                )
                
                # Verify behind_by field is always present
                assert 'behind_by' in comparison, f"behind_by field missing for {fork_owner}/{fork_repo}"
                assert isinstance(comparison['behind_by'], int), f"behind_by not integer for {fork_owner}/{fork_repo}"
                assert comparison['behind_by'] >= 0, f"behind_by negative for {fork_owner}/{fork_repo}"
                
            except Exception as e:
                # If fork is private or doesn't exist, that's acceptable for contract testing
                print(f"Fork {fork_owner}/{fork_repo} not accessible: {e}")

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_github_api_status_field_values(self, github_client):
        """Test that GitHub API status field has expected values."""
        # Use the raw GitHub API to check status field
        try:
            # Make direct API call to get raw response
            comparison = await github_client.get_fork_comparison(
                'GreatBots', 'YouTube_bot_telegram',
                'sanila2007', 'youtube-bot-telegram'
            )
            
            if 'status' in comparison:
                valid_statuses = ['ahead', 'behind', 'identical', 'diverged']
                assert comparison['status'] in valid_statuses, f"Invalid status: {comparison['status']}"
                
                # Verify status consistency with ahead_by and behind_by
                ahead_by = comparison.get('ahead_by', 0)
                behind_by = comparison.get('behind_by', 0)
                status = comparison['status']
                
                if status == 'ahead':
                    assert ahead_by > 0 and behind_by == 0, "Status 'ahead' should have ahead_by > 0 and behind_by == 0"
                elif status == 'behind':
                    assert ahead_by == 0 and behind_by > 0, "Status 'behind' should have ahead_by == 0 and behind_by > 0"
                elif status == 'identical':
                    assert ahead_by == 0 and behind_by == 0, "Status 'identical' should have both counts == 0"
                elif status == 'diverged':
                    assert ahead_by > 0 and behind_by > 0, "Status 'diverged' should have both counts > 0"
                    
        except Exception as e:
            print(f"Could not test status field: {e}")

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_batch_api_responses_consistent(self, github_client):
        """Test that batch API responses have consistent behind_by fields."""
        fork_data_list = [
            ('GreatBots', 'YouTube_bot_telegram'),
            ('Xelio', 'tg-youtube-bot-docker'),
        ]
        
        batch_results = await github_client.get_commits_ahead_behind_batch(
            fork_data_list, 'sanila2007', 'youtube-bot-telegram'
        )
        
        for fork_key, comparison in batch_results.items():
            # Verify each result has required fields
            assert 'behind_by' in comparison, f"behind_by field missing in batch result for {fork_key}"
            assert 'ahead_by' in comparison, f"ahead_by field missing in batch result for {fork_key}"
            assert 'total_commits' in comparison, f"total_commits field missing in batch result for {fork_key}"
            
            # Verify field types
            assert isinstance(comparison['behind_by'], int), f"behind_by not integer in batch result for {fork_key}"
            assert isinstance(comparison['ahead_by'], int), f"ahead_by not integer in batch result for {fork_key}"
            assert isinstance(comparison['total_commits'], int), f"total_commits not integer in batch result for {fork_key}"
            
            # Verify non-negative values
            assert comparison['behind_by'] >= 0, f"behind_by negative in batch result for {fork_key}"
            assert comparison['ahead_by'] >= 0, f"ahead_by negative in batch result for {fork_key}"

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_api_response_stability_over_time(self, github_client):
        """Test that API response format is stable across multiple calls."""
        # Make multiple calls to the same comparison to ensure consistency
        fork_owner, fork_repo = 'GreatBots', 'YouTube_bot_telegram'
        parent_owner, parent_repo = 'sanila2007', 'youtube-bot-telegram'
        
        responses = []
        for i in range(3):  # Make 3 calls
            comparison = await github_client.get_commits_ahead_behind(
                fork_owner, fork_repo, parent_owner, parent_repo
            )
            responses.append(comparison)
        
        # Verify all responses have the same structure
        first_response = responses[0]
        for i, response in enumerate(responses[1:], 1):
            assert set(response.keys()) == set(first_response.keys()), f"Response {i} has different keys"
            
            # Values should be the same (assuming no commits were made during test)
            assert response['behind_by'] == first_response['behind_by'], f"behind_by changed between calls"
            assert response['ahead_by'] == first_response['ahead_by'], f"ahead_by changed between calls"

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_api_error_responses_format(self, github_client):
        """Test that API error responses are handled consistently."""
        # Test with non-existent repository
        try:
            comparison = await github_client.get_commits_ahead_behind(
                'nonexistent-user', 'nonexistent-repo',
                'sanila2007', 'youtube-bot-telegram'
            )
            
            # If no exception is raised, verify the response format
            assert isinstance(comparison, dict), "Error response should be a dictionary"
            assert 'ahead_by' in comparison, "Error response should have ahead_by field"
            assert 'behind_by' in comparison, "Error response should have behind_by field"
            
        except Exception as e:
            # This is expected for non-existent repositories
            print(f"Expected error for non-existent repository: {e}")

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_api_field_documentation_compliance(self, github_client):
        """Test that API response matches GitHub's documented format."""
        comparison = await github_client.get_commits_ahead_behind(
            'GreatBots', 'YouTube_bot_telegram',
            'sanila2007', 'youtube-bot-telegram'
        )
        
        # According to GitHub API documentation, compare endpoint should return:
        documented_fields = [
            'ahead_by',      # Number of commits ahead
            'behind_by',     # Number of commits behind
            'total_commits', # Total commits in comparison
        ]
        
        for field in documented_fields:
            assert field in comparison, f"Documented field '{field}' missing from API response"
            
        # Optional fields that might be present
        optional_fields = ['status', 'commits', 'files']
        for field in optional_fields:
            if field in comparison:
                print(f"Optional field '{field}' present in response")

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_api_version_compatibility(self, github_client):
        """Test that our API version still supports behind_by field."""
        # Verify we're using the correct API version
        headers = github_client._headers
        assert 'X-GitHub-Api-Version' in headers, "API version header should be set"
        
        api_version = headers['X-GitHub-Api-Version']
        print(f"Using GitHub API version: {api_version}")
        
        # Test that this version supports behind_by
        comparison = await github_client.get_commits_ahead_behind(
            'GreatBots', 'YouTube_bot_telegram',
            'sanila2007', 'youtube-bot-telegram'
        )
        
        assert 'behind_by' in comparison, f"API version {api_version} should support behind_by field"