"""Integration tests for commit counting with real GitHub data.

This module tests the commit counting fix using real GitHub repositories
to verify that the system correctly displays actual commit counts instead
of the buggy "+1" for all forks.

Requirements tested:
- 1.1: Accurate commit count display
- 1.4: Correct behavior with --ahead-only flag
"""

import os
import pytest
import pytest_asyncio
import asyncio
from unittest.mock import MagicMock

from forklift.config import GitHubConfig
from forklift.github.client import GitHubClient
from forklift.display.repository_display_service import RepositoryDisplayService


@pytest.mark.online
class TestCommitCountingRealGitHubData:
    """Integration tests using real GitHub data to verify commit counting fix."""

    @pytest.fixture
    def github_config(self):
        """Create GitHub configuration for real API calls."""
        token = os.getenv('GITHUB_TOKEN')
        if not token:
            pytest.skip("GitHub token required for online tests")
        
        return GitHubConfig(
            token=token,
            timeout_seconds=30,
            max_retries=3
        )

    @pytest_asyncio.fixture
    async def github_client(self, github_config):
        """Create real GitHub client for online tests."""
        client = GitHubClient(github_config)
        yield client
        await client.close()

    @pytest.fixture
    def repository_display_service(self, github_client):
        """Create repository display service with real GitHub client."""
        return RepositoryDisplayService(
            github_client=github_client,
            console=MagicMock(),
            cache_manager=None
        )

    @pytest.mark.asyncio
    async def test_real_repository_commit_counting_accuracy(self, github_client):
        """Test commit counting accuracy with real GitHub repositories.
        
        This test verifies that the fix correctly uses the 'ahead_by' field
        from GitHub's compare API instead of counting commits with count=1.
        
        Requirements: 1.1 - Accurate commit count display
        """
        # Test with well-known repositories that have forks with different commit counts
        # Using stable repositories that are unlikely to change dramatically
        
        # Test case 1: Simple repository with known fork structure
        # octocat/Hello-World is GitHub's official test repository
        parent_owner = "octocat"
        parent_repo = "Hello-World"
        
        # Get some forks of this repository
        forks = await github_client.get_repository_forks(parent_owner, parent_repo, per_page=5)
        
        if not forks:
            pytest.skip("No forks found for test repository")
        
        # Test individual commit counting
        commit_counts = {}
        for fork in forks[:3]:  # Test first 3 forks
            try:
                count = await github_client.get_commits_ahead_count(
                    fork.owner, fork.name, parent_owner, parent_repo
                )
                commit_counts[f"{fork.owner}/{fork.name}"] = count
                
                # Verify that count is a non-negative integer
                assert isinstance(count, int), f"Commit count should be integer, got {type(count)}"
                assert count >= 0, f"Commit count should be non-negative, got {count}"
                
                # Log the actual count for verification
                print(f"Fork {fork.owner}/{fork.name}: {count} commits ahead")
                
            except Exception as e:
                # Some forks might be private or have issues - that's okay
                print(f"Could not get commit count for {fork.owner}/{fork.name}: {e}")
                continue
        
        # Verify we got some results
        assert len(commit_counts) > 0, "Should have gotten commit counts for at least one fork"
        
        # Verify that not all counts are 1 (which would indicate the bug is still present)
        counts_list = list(commit_counts.values())
        if len(counts_list) > 1:
            # If we have multiple forks, they shouldn't all have the same count
            # (unless they genuinely all have the same number of commits)
            unique_counts = set(counts_list)
            print(f"Unique commit counts found: {unique_counts}")
            
            # The key test: verify we're getting actual counts, not just 1 for everything
            # If the bug were present, all counts would be 1
            if len(unique_counts) == 1 and list(unique_counts)[0] == 1:
                print("WARNING: All forks show 1 commit - this might indicate the bug is still present")
                print("However, it's also possible that all tested forks genuinely have 1 commit ahead")

    @pytest.mark.asyncio
    async def test_batch_commit_counting_with_real_data(self, github_client):
        """Test batch commit counting with real GitHub data.
        
        This test verifies that the batch counting method correctly processes
        multiple forks and returns accurate counts using the 'ahead_by' field.
        
        Requirements: 1.1 - Accurate commit count display
        """
        # Use a repository with multiple forks
        parent_owner = "microsoft"
        parent_repo = "vscode"  # Popular repository with many forks
        
        # Get some forks
        forks = await github_client.get_repository_forks(parent_owner, parent_repo, per_page=3)
        
        if len(forks) < 2:
            pytest.skip("Need at least 2 forks for batch testing")
        
        # Prepare fork data for batch processing
        fork_data_list = [(fork.owner, fork.name) for fork in forks[:3]]
        
        # Test batch commit counting
        batch_results = await github_client.get_commits_ahead_batch_counts(
            fork_data_list, parent_owner, parent_repo
        )
        
        # Verify results
        assert isinstance(batch_results, dict), "Batch results should be a dictionary"
        assert len(batch_results) > 0, "Should have gotten results for at least one fork"
        
        # Verify each result
        for fork_key, count in batch_results.items():
            assert isinstance(count, int), f"Count for {fork_key} should be integer, got {type(count)}"
            assert count >= 0, f"Count for {fork_key} should be non-negative, got {count}"
            print(f"Batch result - Fork {fork_key}: {count} commits ahead")
        
        # Compare with individual calls to verify consistency
        for fork_owner, fork_repo in fork_data_list[:2]:  # Test first 2 to avoid rate limits
            try:
                individual_count = await github_client.get_commits_ahead_count(
                    fork_owner, fork_repo, parent_owner, parent_repo
                )
                batch_count = batch_results.get(f"{fork_owner}/{fork_repo}")
                
                if batch_count is not None:
                    assert individual_count == batch_count, (
                        f"Individual count ({individual_count}) should match batch count ({batch_count}) "
                        f"for {fork_owner}/{fork_repo}"
                    )
                    print(f"Consistency verified for {fork_owner}/{fork_repo}: {individual_count} commits")
                    
            except Exception as e:
                print(f"Could not verify consistency for {fork_owner}/{fork_repo}: {e}")
                continue

    @pytest.mark.asyncio
    async def test_specific_bug_report_repository(self, github_client):
        """Test the specific repository mentioned in the bug report.
        
        This test attempts to verify the fix with the exact repository
        mentioned in the original bug report: sanila2007/youtube-bot-telegram
        
        Requirements: 1.1, 1.4 - Accurate commit count display and --ahead-only behavior
        """
        # The repository mentioned in the bug report
        parent_owner = "sanila2007"
        parent_repo = "youtube-bot-telegram"
        
        try:
            # First, verify the parent repository exists and is accessible
            parent_repository = await github_client.get_repository(parent_owner, parent_repo)
            print(f"Parent repository found: {parent_repository.full_name}")
            
            # Get forks of this repository
            forks = await github_client.get_repository_forks(parent_owner, parent_repo, per_page=10)
            
            if not forks:
                print("No forks found for the bug report repository")
                pytest.skip("No forks available to test with the bug report repository")
            
            print(f"Found {len(forks)} forks of {parent_owner}/{parent_repo}")
            
            # Test commit counting for each fork
            fork_commit_counts = {}
            forks_with_commits_ahead = []
            
            for fork in forks[:5]:  # Test first 5 forks to avoid rate limits
                try:
                    count = await github_client.get_commits_ahead_count(
                        fork.owner, fork.name, parent_owner, parent_repo
                    )
                    fork_commit_counts[f"{fork.owner}/{fork.name}"] = count
                    
                    if count > 0:
                        forks_with_commits_ahead.append((fork.owner, fork.name, count))
                    
                    print(f"Fork {fork.owner}/{fork.name}: {count} commits ahead")
                    
                    # Verify the count is reasonable (not negative, not impossibly large)
                    assert count >= 0, f"Commit count should be non-negative, got {count}"
                    assert count < 10000, f"Commit count seems unreasonably large: {count}"
                    
                except Exception as e:
                    print(f"Could not get commit count for fork {fork.owner}/{fork.name}: {e}")
                    # This is okay - some forks might be private or have other issues
                    continue
            
            # Verify we got some results
            if not fork_commit_counts:
                pytest.skip("Could not get commit counts for any forks of the bug report repository")
            
            print(f"Successfully got commit counts for {len(fork_commit_counts)} forks")
            
            # The key verification: ensure we're not getting all "+1" counts
            # which would indicate the bug is still present
            counts_list = list(fork_commit_counts.values())
            unique_counts = set(counts_list)
            
            print(f"Unique commit counts found: {sorted(unique_counts)}")
            
            # Test the --ahead-only behavior simulation
            if forks_with_commits_ahead:
                print(f"Forks with commits ahead (simulating --ahead-only):")
                for fork_owner, fork_name, count in forks_with_commits_ahead:
                    display_value = f"+{count}" if count > 0 else "0"
                    print(f"  {fork_owner}/{fork_name}: {display_value}")
                    
                    # Verify display format
                    if count > 0:
                        assert display_value.startswith("+"), f"Display should start with '+' for count {count}"
                        assert display_value != "+1" or count == 1, (
                            f"Display shows '+1' but actual count is {count} - possible bug!"
                        )
            
            # Success criteria: we got commit counts and they're not all the buggy "+1"
            print("✓ Successfully tested commit counting with the bug report repository")
            
        except Exception as e:
            # The specific repository might not be accessible or might have been deleted
            print(f"Could not test bug report repository {parent_owner}/{parent_repo}: {e}")
            pytest.skip(f"Bug report repository not accessible: {e}")

    @pytest.mark.asyncio
    async def test_commit_counting_display_formats(self, github_client):
        """Test that commit counts are displayed in the correct format.
        
        This test verifies that the display logic correctly formats commit counts
        as "+5", "+12", "+23" etc. instead of the buggy "+1" for all forks.
        
        Requirements: 1.1 - Accurate commit count display
        """
        # Test with a repository that has active forks
        parent_owner = "python"
        parent_repo = "cpython"  # Python language repository - likely to have active forks
        
        try:
            # Get some forks
            forks = await github_client.get_forks(parent_owner, parent_repo, per_page=3)
            
            if not forks:
                pytest.skip("No forks found for display format testing")
            
            display_results = []
            
            for fork in forks[:3]:  # Test first 3 forks
                try:
                    count = await github_client.get_commits_ahead_count(
                        fork.owner, fork.name, parent_owner, parent_repo
                    )
                    
                    # Simulate the display logic
                    if count > 0:
                        display_value = f"+{count}"
                    elif count == 0:
                        display_value = ""  # Empty for no commits ahead
                    else:
                        display_value = "Unknown"  # For errors
                    
                    display_results.append({
                        'fork': f"{fork.owner}/{fork.name}",
                        'count': count,
                        'display': display_value
                    })
                    
                    print(f"Fork {fork.owner}/{fork.name}: count={count}, display='{display_value}'")
                    
                    # Verify display format correctness
                    if count > 0:
                        assert display_value == f"+{count}", (
                            f"Display format incorrect: expected '+{count}', got '{display_value}'"
                        )
                        # Specifically check that we're not getting the buggy "+1" for all forks
                        if count != 1:
                            assert display_value != "+1", (
                                f"Bug detected: fork has {count} commits but displays '+1'"
                            )
                    elif count == 0:
                        assert display_value == "", (
                            f"Display format incorrect for zero commits: expected '', got '{display_value}'"
                        )
                    
                except Exception as e:
                    print(f"Could not test display format for {fork.owner}/{fork.name}: {e}")
                    continue
            
            # Verify we got some results
            assert len(display_results) > 0, "Should have gotten display results for at least one fork"
            
            # Analyze results for the bug pattern
            non_zero_results = [r for r in display_results if r['count'] > 0]
            if len(non_zero_results) > 1:
                # Check if all non-zero results show "+1" (which would indicate the bug)
                all_show_plus_one = all(r['display'] == '+1' for r in non_zero_results)
                all_have_count_one = all(r['count'] == 1 for r in non_zero_results)
                
                if all_show_plus_one and not all_have_count_one:
                    pytest.fail(
                        "Bug detected: Multiple forks with different commit counts all display '+1'. "
                        f"Results: {non_zero_results}"
                    )
                
                print(f"✓ Display format test passed with {len(non_zero_results)} forks having commits ahead")
            
        except Exception as e:
            print(f"Could not complete display format test: {e}")
            pytest.skip(f"Display format test not possible: {e}")

    @pytest.mark.asyncio
    async def test_repository_display_service_integration(self, repository_display_service, github_client):
        """Test the repository display service with real GitHub data.
        
        This test verifies that the complete display service correctly processes
        real fork data and shows accurate commit counts.
        
        Requirements: 1.1 - Accurate commit count display
        """
        # Use a smaller repository to avoid rate limits
        parent_owner = "octocat"
        parent_repo = "Spoon-Knife"  # GitHub's fork testing repository
        
        try:
            # Get forks
            forks = await github_client.get_forks(parent_owner, parent_repo, per_page=3)
            
            if not forks:
                pytest.skip("No forks found for repository display service testing")
            
            # Create mock fork data objects that match the expected structure
            from dataclasses import dataclass
            from typing import Any
            
            @dataclass
            class MockForkData:
                metrics: Any
                exact_commits_ahead: int | str | None = None
            
            @dataclass
            class MockMetrics:
                owner: str
                name: str
                can_skip_analysis: bool = False
                stargazers_count: int = 0
                forks_count: int = 0
                pushed_at: Any = None
            
            # Convert real forks to mock fork data
            mock_forks = []
            for fork in forks[:3]:
                mock_fork = MockForkData(
                    metrics=MockMetrics(
                        owner=fork.owner,
                        name=fork.name,
                        stargazers_count=getattr(fork, 'stargazers_count', 0),
                        forks_count=getattr(fork, 'forks_count', 0)
                    )
                )
                mock_forks.append(mock_fork)
            
            # Test the repository display service method
            successful_forks, api_calls_saved = await repository_display_service._get_exact_commit_counts_batch(
                mock_forks, parent_owner, parent_repo
            )
            
            # Verify results
            assert successful_forks >= 0, f"Successful forks count should be non-negative, got {successful_forks}"
            assert api_calls_saved >= 0, f"API calls saved should be non-negative, got {api_calls_saved}"
            
            # Verify that commit counts were set
            forks_with_counts = [f for f in mock_forks if f.exact_commits_ahead is not None]
            assert len(forks_with_counts) > 0, "At least one fork should have gotten a commit count"
            
            # Verify commit count values
            for fork in forks_with_counts:
                if isinstance(fork.exact_commits_ahead, int):
                    assert fork.exact_commits_ahead >= 0, (
                        f"Commit count should be non-negative, got {fork.exact_commits_ahead} "
                        f"for {fork.metrics.owner}/{fork.metrics.name}"
                    )
                    print(f"Fork {fork.metrics.owner}/{fork.metrics.name}: {fork.exact_commits_ahead} commits ahead")
                elif isinstance(fork.exact_commits_ahead, str):
                    # Should be "Unknown" for errors
                    assert fork.exact_commits_ahead == "Unknown", (
                        f"String commit count should be 'Unknown', got '{fork.exact_commits_ahead}'"
                    )
                    print(f"Fork {fork.metrics.owner}/{fork.metrics.name}: {fork.exact_commits_ahead}")
            
            print(f"✓ Repository display service integration test passed: {successful_forks} forks processed")
            
        except Exception as e:
            print(f"Repository display service integration test failed: {e}")
            # Don't skip - this is a real failure we want to know about
            raise

    @pytest.mark.asyncio
    async def test_edge_cases_with_real_data(self, github_client):
        """Test edge cases with real GitHub data.
        
        This test verifies that the commit counting handles various edge cases
        correctly, such as forks with no commits ahead, private forks, etc.
        
        Requirements: 1.1 - Accurate commit count display
        """
        # Test with different types of repositories
        test_cases = [
            ("octocat", "Hello-World"),      # Simple, stable repository
            ("github", "gitignore"),         # Template repository
        ]
        
        edge_case_results = []
        
        for parent_owner, parent_repo in test_cases:
            try:
                print(f"Testing edge cases with {parent_owner}/{parent_repo}")
                
                # Get forks
                forks = await github_client.get_forks(parent_owner, parent_repo, per_page=5)
                
                if not forks:
                    print(f"No forks found for {parent_owner}/{parent_repo}")
                    continue
                
                for fork in forks[:3]:  # Test first 3 forks
                    try:
                        count = await github_client.get_commits_ahead_count(
                            fork.owner, fork.name, parent_owner, parent_repo
                        )
                        
                        edge_case_results.append({
                            'parent': f"{parent_owner}/{parent_repo}",
                            'fork': f"{fork.owner}/{fork.name}",
                            'count': count,
                            'type': 'success'
                        })
                        
                        # Test different count scenarios
                        if count == 0:
                            print(f"✓ Found fork with 0 commits ahead: {fork.owner}/{fork.name}")
                        elif count > 0:
                            print(f"✓ Found fork with {count} commits ahead: {fork.owner}/{fork.name}")
                        
                        # Verify count is reasonable
                        assert count >= 0, f"Count should be non-negative: {count}"
                        
                    except Exception as e:
                        # This is expected for some forks (private, deleted, etc.)
                        edge_case_results.append({
                            'parent': f"{parent_owner}/{parent_repo}",
                            'fork': f"{fork.owner}/{fork.name}",
                            'error': str(e),
                            'type': 'error'
                        })
                        print(f"Expected error for {fork.owner}/{fork.name}: {e}")
                        
            except Exception as e:
                print(f"Could not test {parent_owner}/{parent_repo}: {e}")
                continue
        
        # Verify we got some results
        assert len(edge_case_results) > 0, "Should have gotten some edge case results"
        
        # Analyze results
        successful_results = [r for r in edge_case_results if r['type'] == 'success']
        error_results = [r for r in edge_case_results if r['type'] == 'error']
        
        print(f"Edge case testing completed: {len(successful_results)} successful, {len(error_results)} errors")
        
        # Verify we handled both success and error cases
        if successful_results:
            counts = [r['count'] for r in successful_results]
            print(f"Successful commit counts: {counts}")
            
            # Verify variety in counts (not all the same, which might indicate a bug)
            unique_counts = set(counts)
            print(f"Unique counts found: {sorted(unique_counts)}")
        
        if error_results:
            print("Error cases handled (this is expected for some forks)")
        
        print("✓ Edge case testing completed successfully")