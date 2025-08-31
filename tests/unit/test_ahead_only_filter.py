"""Unit tests for ahead-only filtering functionality."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from forklift.models.ahead_only_filter import (
    AheadOnlyConfig,
    AheadOnlyFilter,
    FilteredForkResult,
    create_default_ahead_only_filter,
)
from forklift.models.github import Repository


class TestFilteredForkResult:
    """Test FilteredForkResult data class."""
    
    def test_init(self):
        """Test FilteredForkResult initialization."""
        forks = [Mock(), Mock()]
        result = FilteredForkResult(
            forks=forks,
            total_processed=10,
            excluded_private=3,
            excluded_no_commits=5
        )
        
        assert result.forks == forks
        assert result.total_processed == 10
        assert result.excluded_private == 3
        assert result.excluded_no_commits == 5
    
    def test_included_count(self):
        """Test included_count property."""
        forks = [Mock(), Mock(), Mock()]
        result = FilteredForkResult(
            forks=forks,
            total_processed=10,
            excluded_private=3,
            excluded_no_commits=4
        )
        
        assert result.included_count == 3
    
    def test_total_excluded(self):
        """Test total_excluded property."""
        result = FilteredForkResult(
            forks=[],
            total_processed=10,
            excluded_private=3,
            excluded_no_commits=5
        )
        
        assert result.total_excluded == 8
    
    def test_exclusion_summary(self):
        """Test exclusion_summary property."""
        forks = [Mock(), Mock()]
        result = FilteredForkResult(
            forks=forks,
            total_processed=10,
            excluded_private=3,
            excluded_no_commits=5
        )
        
        expected = "Filtered 10 forks: 2 included, 3 private excluded, 5 no commits excluded"
        assert result.exclusion_summary == expected


class TestAheadOnlyConfig:
    """Test AheadOnlyConfig model."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = AheadOnlyConfig()
        
        assert config.enabled is False
        assert config.include_uncertain is True
        assert config.conservative_filtering is False
        assert config.exclude_private is True
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = AheadOnlyConfig(
            enabled=True,
            include_uncertain=False,
            conservative_filtering=True,
            exclude_private=False
        )
        
        assert config.enabled is True
        assert config.include_uncertain is False
        assert config.conservative_filtering is True
        assert config.exclude_private is False


class TestAheadOnlyFilter:
    """Test AheadOnlyFilter class."""
    
    def create_test_repository(
        self,
        name: str = "test-repo",
        owner: str = "test-owner",
        is_private: bool = False,
        created_at: datetime | None = None,
        pushed_at: datetime | None = None
    ) -> Repository:
        """Create a test repository with specified parameters."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        return Repository(
            id=123,
            owner=owner,
            name=name,
            full_name=f"{owner}/{name}",
            url=f"https://api.github.com/repos/{owner}/{name}",
            html_url=f"https://github.com/{owner}/{name}",
            clone_url=f"https://github.com/{owner}/{name}.git",
            is_private=is_private,
            created_at=created_at or base_time,
            pushed_at=pushed_at or base_time
        )
    
    def test_init_with_default_config(self):
        """Test filter initialization with default config."""
        filter_obj = AheadOnlyFilter()
        
        assert isinstance(filter_obj.config, AheadOnlyConfig)
        assert filter_obj.config.enabled is False
        assert filter_obj.config.include_uncertain is True
        assert filter_obj.config.exclude_private is True
    
    def test_init_with_custom_config(self):
        """Test filter initialization with custom config."""
        config = AheadOnlyConfig(enabled=True, include_uncertain=False)
        filter_obj = AheadOnlyFilter(config)
        
        assert filter_obj.config == config
        assert filter_obj.config.enabled is True
        assert filter_obj.config.include_uncertain is False
    
    def test_has_commits_ahead_with_commits(self):
        """Test _has_commits_ahead with fork that has commits ahead."""
        filter_obj = AheadOnlyFilter()
        
        # Fork created at 12:00, pushed at 13:00 (1 hour later)
        created_at = datetime(2024, 1, 1, 12, 0, 0)
        pushed_at = datetime(2024, 1, 1, 13, 0, 0)
        
        fork = self.create_test_repository(
            created_at=created_at,
            pushed_at=pushed_at
        )
        
        assert filter_obj._has_commits_ahead(fork) is True
    
    def test_has_commits_ahead_no_commits(self):
        """Test _has_commits_ahead with fork that has no commits ahead."""
        filter_obj = AheadOnlyFilter()
        
        # Fork created at 12:00, pushed at 12:00 (same time)
        created_at = datetime(2024, 1, 1, 12, 0, 0)
        pushed_at = datetime(2024, 1, 1, 12, 0, 0)
        
        fork = self.create_test_repository(
            created_at=created_at,
            pushed_at=pushed_at
        )
        
        assert filter_obj._has_commits_ahead(fork) is False
    
    def test_has_commits_ahead_pushed_before_created(self):
        """Test _has_commits_ahead with fork pushed before creation (edge case)."""
        filter_obj = AheadOnlyFilter()
        
        # Fork created at 13:00, pushed at 12:00 (pushed before created - unusual)
        created_at = datetime(2024, 1, 1, 13, 0, 0)
        pushed_at = datetime(2024, 1, 1, 12, 0, 0)
        
        fork = self.create_test_repository(
            created_at=created_at,
            pushed_at=pushed_at
        )
        
        assert filter_obj._has_commits_ahead(fork) is False
    
    def test_has_commits_ahead_missing_timestamps_include_uncertain(self):
        """Test _has_commits_ahead with missing timestamps and include_uncertain=True."""
        config = AheadOnlyConfig(include_uncertain=True)
        filter_obj = AheadOnlyFilter(config)
        
        # Create repository with explicitly None timestamps
        fork = Repository(
            id=123,
            owner="test-owner",
            name="test-repo",
            full_name="test-owner/test-repo",
            url="https://api.github.com/repos/test-owner/test-repo",
            html_url="https://github.com/test-owner/test-repo",
            clone_url="https://github.com/test-owner/test-repo.git",
            created_at=None,
            pushed_at=None
        )
        
        assert filter_obj._has_commits_ahead(fork) is True
    
    def test_has_commits_ahead_missing_timestamps_exclude_uncertain(self):
        """Test _has_commits_ahead with missing timestamps and include_uncertain=False."""
        config = AheadOnlyConfig(include_uncertain=False)
        filter_obj = AheadOnlyFilter(config)
        
        # Create repository with explicitly None timestamps
        fork = Repository(
            id=123,
            owner="test-owner",
            name="test-repo",
            full_name="test-owner/test-repo",
            url="https://api.github.com/repos/test-owner/test-repo",
            html_url="https://github.com/test-owner/test-repo",
            clone_url="https://github.com/test-owner/test-repo.git",
            created_at=None,
            pushed_at=None
        )
        
        assert filter_obj._has_commits_ahead(fork) is False
    
    def test_has_commits_ahead_close_timestamps_include_uncertain(self):
        """Test _has_commits_ahead with very close timestamps and include_uncertain=True."""
        config = AheadOnlyConfig(include_uncertain=True)
        filter_obj = AheadOnlyFilter(config)
        
        # Fork created at 12:00:00, pushed at 12:00:30 (30 seconds later)
        created_at = datetime(2024, 1, 1, 12, 0, 0)
        pushed_at = datetime(2024, 1, 1, 12, 0, 30)
        
        fork = self.create_test_repository(
            created_at=created_at,
            pushed_at=pushed_at
        )
        
        # Should return True because pushed_at > created_at (even if close)
        assert filter_obj._has_commits_ahead(fork) is True
    
    def test_filter_forks_mixed_scenario(self):
        """Test filter_forks with mixed fork scenarios."""
        filter_obj = AheadOnlyFilter()
        
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        forks = [
            # Public fork with commits ahead
            self.create_test_repository(
                name="fork1",
                is_private=False,
                created_at=base_time,
                pushed_at=base_time + timedelta(hours=1)
            ),
            # Private fork with commits ahead (should be excluded)
            self.create_test_repository(
                name="fork2",
                is_private=True,
                created_at=base_time,
                pushed_at=base_time + timedelta(hours=1)
            ),
            # Public fork with no commits ahead
            self.create_test_repository(
                name="fork3",
                is_private=False,
                created_at=base_time,
                pushed_at=base_time
            ),
            # Public fork with commits ahead
            self.create_test_repository(
                name="fork4",
                is_private=False,
                created_at=base_time,
                pushed_at=base_time + timedelta(minutes=30)
            ),
        ]
        
        result = filter_obj.filter_forks(forks)
        
        assert result.total_processed == 4
        assert result.included_count == 2  # fork1 and fork4
        assert result.excluded_private == 1  # fork2
        assert result.excluded_no_commits == 1  # fork3
        
        # Check that correct forks are included
        included_names = [fork.name for fork in result.forks]
        assert "fork1" in included_names
        assert "fork4" in included_names
        assert "fork2" not in included_names
        assert "fork3" not in included_names
    
    def test_filter_forks_all_private(self):
        """Test filter_forks with all private forks."""
        filter_obj = AheadOnlyFilter()
        
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        forks = [
            self.create_test_repository(
                name="private1",
                is_private=True,
                created_at=base_time,
                pushed_at=base_time + timedelta(hours=1)
            ),
            self.create_test_repository(
                name="private2",
                is_private=True,
                created_at=base_time,
                pushed_at=base_time + timedelta(hours=2)
            ),
        ]
        
        result = filter_obj.filter_forks(forks)
        
        assert result.total_processed == 2
        assert result.included_count == 0
        assert result.excluded_private == 2
        assert result.excluded_no_commits == 0
    
    def test_filter_forks_no_commits_ahead(self):
        """Test filter_forks with no forks having commits ahead."""
        filter_obj = AheadOnlyFilter()
        
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        forks = [
            self.create_test_repository(
                name="fork1",
                is_private=False,
                created_at=base_time,
                pushed_at=base_time  # Same time
            ),
            self.create_test_repository(
                name="fork2",
                is_private=False,
                created_at=base_time + timedelta(hours=1),
                pushed_at=base_time  # Pushed before created
            ),
        ]
        
        result = filter_obj.filter_forks(forks)
        
        assert result.total_processed == 2
        assert result.included_count == 0
        assert result.excluded_private == 0
        assert result.excluded_no_commits == 2
    
    def test_filter_forks_exclude_private_disabled(self):
        """Test filter_forks with exclude_private disabled."""
        config = AheadOnlyConfig(exclude_private=False)
        filter_obj = AheadOnlyFilter(config)
        
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        forks = [
            # Private fork with commits ahead (should be included)
            self.create_test_repository(
                name="private_fork",
                is_private=True,
                created_at=base_time,
                pushed_at=base_time + timedelta(hours=1)
            ),
        ]
        
        result = filter_obj.filter_forks(forks)
        
        assert result.total_processed == 1
        assert result.included_count == 1
        assert result.excluded_private == 0
        assert result.excluded_no_commits == 0
    
    def test_get_filtering_stats(self):
        """Test get_filtering_stats method."""
        filter_obj = AheadOnlyFilter()
        
        result = FilteredForkResult(
            forks=[Mock(), Mock()],
            total_processed=10,
            excluded_private=3,
            excluded_no_commits=5
        )
        
        stats = filter_obj.get_filtering_stats(result)
        
        assert stats["total_forks"] == 10
        assert stats["included_forks"] == 2
        assert stats["excluded_forks"] == 8
        assert stats["excluded_private"] == 3
        assert stats["excluded_no_commits"] == 5
        assert stats["inclusion_rate"] == 0.2  # 2/10
        assert stats["private_exclusion_rate"] == 0.3  # 3/10
        assert stats["no_commits_exclusion_rate"] == 0.5  # 5/10
    
    def test_get_filtering_stats_empty_result(self):
        """Test get_filtering_stats with empty result."""
        filter_obj = AheadOnlyFilter()
        
        result = FilteredForkResult(
            forks=[],
            total_processed=0,
            excluded_private=0,
            excluded_no_commits=0
        )
        
        stats = filter_obj.get_filtering_stats(result)
        
        assert stats["total_forks"] == 0
        assert stats["included_forks"] == 0
        assert stats["excluded_forks"] == 0
        assert stats["inclusion_rate"] == 0.0
        assert stats["private_exclusion_rate"] == 0.0
        assert stats["no_commits_exclusion_rate"] == 0.0


class TestCreateDefaultAheadOnlyFilter:
    """Test create_default_ahead_only_filter function."""
    
    def test_creates_filter_with_correct_config(self):
        """Test that function creates filter with correct default configuration."""
        filter_obj = create_default_ahead_only_filter()
        
        assert isinstance(filter_obj, AheadOnlyFilter)
        assert filter_obj.config.enabled is True
        assert filter_obj.config.include_uncertain is True
        assert filter_obj.config.conservative_filtering is False
        assert filter_obj.config.exclude_private is True
    
    def test_filter_works_correctly(self):
        """Test that created filter works correctly."""
        filter_obj = create_default_ahead_only_filter()
        
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        # Create a test repository with commits ahead
        repo = Repository(
            id=123,
            owner="test-owner",
            name="test-repo",
            full_name="test-owner/test-repo",
            url="https://api.github.com/repos/test-owner/test-repo",
            html_url="https://github.com/test-owner/test-repo",
            clone_url="https://github.com/test-owner/test-repo.git",
            is_private=False,
            created_at=base_time,
            pushed_at=base_time + timedelta(hours=1)
        )
        
        result = filter_obj.filter_forks([repo])
        
        assert result.included_count == 1
        assert result.excluded_private == 0
        assert result.excluded_no_commits == 0


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_filter_empty_list(self):
        """Test filtering empty fork list."""
        filter_obj = AheadOnlyFilter()
        
        result = filter_obj.filter_forks([])
        
        assert result.total_processed == 0
        assert result.included_count == 0
        assert result.excluded_private == 0
        assert result.excluded_no_commits == 0
    
    def test_filter_with_none_timestamps(self):
        """Test filtering with None timestamps in various combinations."""
        config = AheadOnlyConfig(include_uncertain=True)
        filter_obj = AheadOnlyFilter(config)
        
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        forks = [
            Repository(
                id=1,
                owner="owner1",
                name="repo1",
                full_name="owner1/repo1",
                url="https://api.github.com/repos/owner1/repo1",
                html_url="https://github.com/owner1/repo1",
                clone_url="https://github.com/owner1/repo1.git",
                created_at=None,
                pushed_at=base_time
            ),
            Repository(
                id=2,
                owner="owner2",
                name="repo2",
                full_name="owner2/repo2",
                url="https://api.github.com/repos/owner2/repo2",
                html_url="https://github.com/owner2/repo2",
                clone_url="https://github.com/owner2/repo2.git",
                created_at=base_time,
                pushed_at=None
            ),
        ]
        
        result = filter_obj.filter_forks(forks)
        
        # Both should be included because include_uncertain=True
        assert result.included_count == 2
        assert result.excluded_no_commits == 0