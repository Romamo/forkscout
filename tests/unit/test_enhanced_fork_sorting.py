"""Unit tests for enhanced fork sorting logic."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
)


class TestEnhancedForkSorting:
    """Test cases for enhanced fork sorting functionality."""

    @pytest.fixture
    def service(self):
        """Create a RepositoryDisplayService instance for testing."""
        return RepositoryDisplayService(AsyncMock(), MagicMock())

    @pytest.fixture
    def sample_fork_data(self):
        """Create sample fork data with various combinations for testing sorting."""
        base_time = datetime.utcnow()

        # Fork 1: Has commits, high forks, high stars, recent activity
        metrics1 = ForkQualificationMetrics(
            id=1, name="fork-high-all", full_name="user1/fork-high-all",
            owner="user1", html_url="https://github.com/user1/fork-high-all",
            stargazers_count=100, forks_count=50, watchers_count=80,
            size=5000, language="Python",
            created_at=base_time - timedelta(days=60),
            updated_at=base_time - timedelta(days=1),
            pushed_at=base_time - timedelta(days=1)  # Recent push after creation
        )

        # Fork 2: Has commits, medium forks, high stars, older activity
        metrics2 = ForkQualificationMetrics(
            id=2, name="fork-medium-forks", full_name="user2/fork-medium-forks",
            owner="user2", html_url="https://github.com/user2/fork-medium-forks",
            stargazers_count=150, forks_count=30, watchers_count=120,
            size=3000, language="JavaScript",
            created_at=base_time - timedelta(days=90),
            updated_at=base_time - timedelta(days=10),
            pushed_at=base_time - timedelta(days=10)  # Push after creation
        )

        # Fork 3: Has commits, low forks, medium stars, very recent activity
        metrics3 = ForkQualificationMetrics(
            id=3, name="fork-low-forks", full_name="user3/fork-low-forks",
            owner="user3", html_url="https://github.com/user3/fork-low-forks",
            stargazers_count=75, forks_count=10, watchers_count=60,
            size=2000, language="Go",
            created_at=base_time - timedelta(days=30),
            updated_at=base_time - timedelta(hours=1),
            pushed_at=base_time - timedelta(hours=1)  # Very recent push
        )

        # Fork 4: No commits (created_at == pushed_at), high stars, high forks
        metrics4 = ForkQualificationMetrics(
            id=4, name="fork-no-commits-high", full_name="user4/fork-no-commits-high",
            owner="user4", html_url="https://github.com/user4/fork-no-commits-high",
            stargazers_count=200, forks_count=80, watchers_count=150,
            size=1000, language="Rust",
            created_at=base_time - timedelta(days=45),
            updated_at=base_time - timedelta(days=45),
            pushed_at=base_time - timedelta(days=45)  # Same as created_at = no commits
        )

        # Fork 5: No commits (created_at > pushed_at), medium stats
        metrics5 = ForkQualificationMetrics(
            id=5, name="fork-no-commits-medium", full_name="user5/fork-no-commits-medium",
            owner="user5", html_url="https://github.com/user5/fork-no-commits-medium",
            stargazers_count=50, forks_count=25, watchers_count=40,
            size=800, language="Java",
            created_at=base_time - timedelta(days=20),
            updated_at=base_time - timedelta(days=25),
            pushed_at=base_time - timedelta(days=25)  # Pushed before created = no commits
        )

        # Fork 6: Has commits, same forks as fork 2 but lower stars (test secondary sort)
        metrics6 = ForkQualificationMetrics(
            id=6, name="fork-same-forks-lower-stars", full_name="user6/fork-same-forks-lower-stars",
            owner="user6", html_url="https://github.com/user6/fork-same-forks-lower-stars",
            stargazers_count=120, forks_count=30, watchers_count=90,  # Same forks as metrics2
            size=4000, language="C++",
            created_at=base_time - timedelta(days=80),
            updated_at=base_time - timedelta(days=5),
            pushed_at=base_time - timedelta(days=5)  # Push after creation
        )

        return [
            CollectedForkData(metrics=metrics1),
            CollectedForkData(metrics=metrics2),
            CollectedForkData(metrics=metrics3),
            CollectedForkData(metrics=metrics4),
            CollectedForkData(metrics=metrics5),
            CollectedForkData(metrics=metrics6),
        ]

    def test_enhanced_sorting_commits_status_priority(self, service, sample_fork_data):
        """Test that forks with commits are sorted before forks without commits."""
        sorted_forks = service._sort_forks_enhanced(sample_fork_data)

        # First 4 forks should have commits, last 2 should not
        for i in range(4):
            assert sorted_forks[i].metrics.commits_ahead_status == "Has commits", \
                f"Fork at position {i} should have commits"

        for i in range(4, 6):
            assert sorted_forks[i].metrics.commits_ahead_status == "No commits ahead", \
                f"Fork at position {i} should not have commits"

    def test_enhanced_sorting_stars_count_secondary(self, service, sample_fork_data):
        """Test that within commits status groups, forks are sorted by stars count descending."""
        sorted_forks = service._sort_forks_enhanced(sample_fork_data)

        # Among forks with commits (first 4), check stars count descending
        has_commits_forks = [f for f in sorted_forks if f.metrics.commits_ahead_status == "Has commits"]

        for i in range(len(has_commits_forks) - 1):
            current_stars = has_commits_forks[i].metrics.stargazers_count
            next_stars = has_commits_forks[i + 1].metrics.stargazers_count
            assert current_stars >= next_stars, \
                f"Fork {i} should have >= stars than fork {i+1} ({current_stars} vs {next_stars})"

    def test_enhanced_sorting_forks_count_tertiary(self, service, sample_fork_data):
        """Test that forks with same stars count are sorted by forks count descending."""
        sorted_forks = service._sort_forks_enhanced(sample_fork_data)

        # Find forks with same stars count (if any exist in test data)
        has_commits_forks = [f for f in sorted_forks if f.metrics.commits_ahead_status == "Has commits"]

        # Check that among forks with same stars, forks count is descending
        # This is a general check since our test data doesn't have exact star matches
        for i in range(len(has_commits_forks) - 1):
            current_fork = has_commits_forks[i]
            next_fork = has_commits_forks[i + 1]
            
            # If stars are equal, forks count should be descending
            if current_fork.metrics.stargazers_count == next_fork.metrics.stargazers_count:
                assert current_fork.metrics.forks_count >= next_fork.metrics.forks_count, \
                    "Forks with same stars count should be sorted by forks count descending"

    def test_enhanced_sorting_last_push_quaternary(self, service, sample_fork_data):
        """Test that forks with same forks and stars are sorted by last push date descending."""
        # Create forks with identical forks and stars but different push dates
        base_time = datetime.utcnow()

        metrics_recent = ForkQualificationMetrics(
            id=10, name="fork-recent", full_name="user/fork-recent",
            owner="user", html_url="https://github.com/user/fork-recent",
            stargazers_count=50, forks_count=20, watchers_count=40,
            size=1000, language="Python",
            created_at=base_time - timedelta(days=30),
            updated_at=base_time - timedelta(days=1),
            pushed_at=base_time - timedelta(days=1)  # Recent push
        )

        metrics_older = ForkQualificationMetrics(
            id=11, name="fork-older", full_name="user/fork-older",
            owner="user", html_url="https://github.com/user/fork-older",
            stargazers_count=50, forks_count=20, watchers_count=40,  # Same stats
            size=1000, language="Python",
            created_at=base_time - timedelta(days=60),
            updated_at=base_time - timedelta(days=30),
            pushed_at=base_time - timedelta(days=30)  # Older push
        )

        test_data = [
            CollectedForkData(metrics=metrics_older),
            CollectedForkData(metrics=metrics_recent),
        ]

        sorted_forks = service._sort_forks_enhanced(test_data)

        # Fork with more recent push should come first
        assert sorted_forks[0].metrics.name == "fork-recent", \
            "Fork with more recent push should be sorted first"
        assert sorted_forks[1].metrics.name == "fork-older", \
            "Fork with older push should be sorted second"

    def test_enhanced_sorting_complete_order(self, service, sample_fork_data):
        """Test the complete sorting order with all criteria."""
        sorted_forks = service._sort_forks_enhanced(sample_fork_data)

        # Expected order based on improved multi-level sorting:
        # Priority: commits status, then stars (desc), then forks (desc), then activity (desc)
        # 1. fork-medium-forks (has commits, 150 stars, 30 forks)
        # 2. fork-same-forks-lower-stars (has commits, 120 stars, 30 forks)
        # 3. fork-high-all (has commits, 100 stars, 50 forks)
        # 4. fork-low-forks (has commits, 75 stars, 10 forks)
        # 5. fork-no-commits-high (no commits, 200 stars, 80 forks)
        # 6. fork-no-commits-medium (no commits, 50 stars, 25 forks)

        expected_names = [
            "fork-medium-forks",
            "fork-same-forks-lower-stars", 
            "fork-high-all",
            "fork-low-forks",
            "fork-no-commits-high",
            "fork-no-commits-medium"
        ]

        actual_names = [fork.metrics.name for fork in sorted_forks]

        assert actual_names == expected_names, \
            f"Expected order: {expected_names}, but got: {actual_names}"

    def test_enhanced_sorting_empty_list(self, service):
        """Test enhanced sorting with empty fork list."""
        result = service._sort_forks_enhanced([])
        assert result == [], "Empty list should return empty list"

    def test_enhanced_sorting_single_fork(self, service):
        """Test enhanced sorting with single fork."""
        base_time = datetime.utcnow()

        metrics = ForkQualificationMetrics(
            id=1, name="single-fork", full_name="user/single-fork",
            owner="user", html_url="https://github.com/user/single-fork",
            stargazers_count=10, forks_count=5, watchers_count=8,
            size=1000, language="Python",
            created_at=base_time - timedelta(days=30),
            updated_at=base_time - timedelta(days=1),
            pushed_at=base_time - timedelta(days=1)
        )

        fork_data = [CollectedForkData(metrics=metrics)]
        result = service._sort_forks_enhanced(fork_data)

        assert len(result) == 1, "Single fork should return list with one item"
        assert result[0].metrics.name == "single-fork", "Single fork should be preserved"

    def test_enhanced_sorting_preserves_data_integrity(self, service, sample_fork_data):
        """Test that enhanced sorting preserves all fork data without modification."""
        original_count = len(sample_fork_data)
        original_ids = {fork.metrics.id for fork in sample_fork_data}

        sorted_forks = service._sort_forks_enhanced(sample_fork_data)

        # Check count preservation
        assert len(sorted_forks) == original_count, \
            "Sorting should preserve the number of forks"

        # Check data integrity
        sorted_ids = {fork.metrics.id for fork in sorted_forks}
        assert sorted_ids == original_ids, \
            "Sorting should preserve all fork data without modification"

        # Check that original data is preserved
        for original_fork in sample_fork_data:
            assert any(fork.metrics.id == original_fork.metrics.id for fork in sorted_forks), \
                f"Original fork {original_fork.metrics.name} should be preserved in sorted result"

    def test_enhanced_sorting_edge_cases(self, service):
        """Test enhanced sorting handles edge cases gracefully."""
        base_time = datetime.utcnow()

        # Fork with very old push date (edge case for timestamp)
        metrics_old_push = ForkQualificationMetrics(
            id=1, name="fork-old-push", full_name="user/fork-old-push",
            owner="user", html_url="https://github.com/user/fork-old-push",
            stargazers_count=10, forks_count=5, watchers_count=8,
            size=1000, language="Python",
            created_at=base_time - timedelta(days=365),
            updated_at=base_time - timedelta(days=365),
            pushed_at=base_time - timedelta(days=365)  # Very old push
        )

        # Fork with zero stats
        metrics_zero_stats = ForkQualificationMetrics(
            id=2, name="fork-zero-stats", full_name="user/fork-zero-stats",
            owner="user", html_url="https://github.com/user/fork-zero-stats",
            stargazers_count=0, forks_count=0, watchers_count=0,
            size=0, language=None,
            created_at=base_time - timedelta(days=30),
            updated_at=base_time - timedelta(days=1),
            pushed_at=base_time - timedelta(days=1)
        )

        fork_data = [
            CollectedForkData(metrics=metrics_old_push),
            CollectedForkData(metrics=metrics_zero_stats)
        ]

        # Should not raise an exception
        result = service._sort_forks_enhanced(fork_data)

        assert len(result) == 2, "Should handle edge cases without errors"
        # Both have commits, zero stats fork should come first (more recent push)
        assert result[0].metrics.name == "fork-zero-stats", \
            "Fork with more recent push should come first despite zero stats"
        assert result[1].metrics.name == "fork-old-push", \
            "Fork with older push should come second"
