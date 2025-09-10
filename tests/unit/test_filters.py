"""Unit tests for filter models."""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from forkscout.models.filters import (
    BranchInfo,
    ForkDetails,
    ForkDetailsFilter,
    PromisingForksFilter,
)


class TestPromisingForksFilter:
    """Test PromisingForksFilter functionality."""

    def test_default_filter_creation(self):
        """Test creating filter with default values."""
        filter_obj = PromisingForksFilter()

        assert filter_obj.min_stars == 0
        assert filter_obj.min_commits_ahead == 1
        assert filter_obj.max_days_since_activity == 365
        assert filter_obj.min_activity_score == 0.0
        assert filter_obj.exclude_archived is True
        assert filter_obj.exclude_disabled is True
        assert filter_obj.min_fork_age_days == 0
        assert filter_obj.max_fork_age_days is None

    def test_custom_filter_creation(self):
        """Test creating filter with custom values."""
        filter_obj = PromisingForksFilter(
            min_stars=5,
            min_commits_ahead=10,
            max_days_since_activity=180,
            min_activity_score=0.5,
            exclude_archived=False,
            exclude_disabled=False,
            min_fork_age_days=30,
            max_fork_age_days=730
        )

        assert filter_obj.min_stars == 5
        assert filter_obj.min_commits_ahead == 10
        assert filter_obj.max_days_since_activity == 180
        assert filter_obj.min_activity_score == 0.5
        assert filter_obj.exclude_archived is False
        assert filter_obj.exclude_disabled is False
        assert filter_obj.min_fork_age_days == 30
        assert filter_obj.max_fork_age_days == 730

    def test_max_fork_age_validation_error(self):
        """Test validation error when max_fork_age_days <= min_fork_age_days."""
        with pytest.raises(ValueError, match="max_fork_age_days must be greater than min_fork_age_days"):
            PromisingForksFilter(
                min_fork_age_days=100,
                max_fork_age_days=50
            )

    def test_max_fork_age_validation_equal(self):
        """Test validation error when max_fork_age_days equals min_fork_age_days."""
        with pytest.raises(ValueError, match="max_fork_age_days must be greater than min_fork_age_days"):
            PromisingForksFilter(
                min_fork_age_days=100,
                max_fork_age_days=100
            )

    def test_max_fork_age_validation_success(self):
        """Test successful validation when max_fork_age_days > min_fork_age_days."""
        filter_obj = PromisingForksFilter(
            min_fork_age_days=30,
            max_fork_age_days=365
        )
        assert filter_obj.min_fork_age_days == 30
        assert filter_obj.max_fork_age_days == 365

    def test_matches_fork_basic_criteria(self):
        """Test fork matching with basic criteria."""
        filter_obj = PromisingForksFilter(
            min_stars=5,
            min_commits_ahead=2
        )

        # Create mock fork data
        mock_fork = Mock()
        mock_fork.stars = 10
        mock_fork.is_archived = False
        mock_fork.is_disabled = False
        mock_fork.pushed_at = datetime.utcnow() - timedelta(days=30)
        mock_fork.created_at = datetime.utcnow() - timedelta(days=100)

        fork_data = {
            "fork": mock_fork,
            "commits_ahead": 5,
            "activity_status": "active"
        }

        assert filter_obj.matches_fork(fork_data) is True

    def test_matches_fork_fails_star_count(self):
        """Test fork matching fails on star count."""
        filter_obj = PromisingForksFilter(min_stars=10)

        mock_fork = Mock()
        mock_fork.stars = 5  # Below minimum
        mock_fork.is_archived = False
        mock_fork.is_disabled = False
        mock_fork.pushed_at = datetime.utcnow() - timedelta(days=30)
        mock_fork.created_at = datetime.utcnow() - timedelta(days=100)

        fork_data = {
            "fork": mock_fork,
            "commits_ahead": 5,
            "activity_status": "active"
        }

        assert filter_obj.matches_fork(fork_data) is False

    def test_matches_fork_fails_commits_ahead(self):
        """Test fork matching fails on commits ahead."""
        filter_obj = PromisingForksFilter(min_commits_ahead=10)

        mock_fork = Mock()
        mock_fork.stars = 10
        mock_fork.is_archived = False
        mock_fork.is_disabled = False
        mock_fork.pushed_at = datetime.utcnow() - timedelta(days=30)
        mock_fork.created_at = datetime.utcnow() - timedelta(days=100)

        fork_data = {
            "fork": mock_fork,
            "commits_ahead": 5,  # Below minimum
            "activity_status": "active"
        }

        assert filter_obj.matches_fork(fork_data) is False

    def test_matches_fork_fails_archived(self):
        """Test fork matching fails on archived status."""
        filter_obj = PromisingForksFilter(exclude_archived=True)

        mock_fork = Mock()
        mock_fork.stars = 10
        mock_fork.is_archived = True  # Archived
        mock_fork.is_disabled = False
        mock_fork.pushed_at = datetime.utcnow() - timedelta(days=30)
        mock_fork.created_at = datetime.utcnow() - timedelta(days=100)

        fork_data = {
            "fork": mock_fork,
            "commits_ahead": 5,
            "activity_status": "active"
        }

        assert filter_obj.matches_fork(fork_data) is False

    def test_matches_fork_fails_disabled(self):
        """Test fork matching fails on disabled status."""
        filter_obj = PromisingForksFilter(exclude_disabled=True)

        mock_fork = Mock()
        mock_fork.stars = 10
        mock_fork.is_archived = False
        mock_fork.is_disabled = True  # Disabled
        mock_fork.pushed_at = datetime.utcnow() - timedelta(days=30)
        mock_fork.created_at = datetime.utcnow() - timedelta(days=100)

        fork_data = {
            "fork": mock_fork,
            "commits_ahead": 5,
            "activity_status": "active"
        }

        assert filter_obj.matches_fork(fork_data) is False

    def test_matches_fork_fails_activity_recency(self):
        """Test fork matching fails on activity recency."""
        filter_obj = PromisingForksFilter(max_days_since_activity=30)

        mock_fork = Mock()
        mock_fork.stars = 10
        mock_fork.is_archived = False
        mock_fork.is_disabled = False
        mock_fork.pushed_at = datetime.utcnow() - timedelta(days=60)  # Too old
        mock_fork.created_at = datetime.utcnow() - timedelta(days=100)

        fork_data = {
            "fork": mock_fork,
            "commits_ahead": 5,
            "activity_status": "stale"
        }

        assert filter_obj.matches_fork(fork_data) is False

    def test_matches_fork_fails_fork_age_too_young(self):
        """Test fork matching fails on fork being too young."""
        filter_obj = PromisingForksFilter(min_fork_age_days=100)

        mock_fork = Mock()
        mock_fork.stars = 10
        mock_fork.is_archived = False
        mock_fork.is_disabled = False
        mock_fork.pushed_at = datetime.utcnow() - timedelta(days=30)
        mock_fork.created_at = datetime.utcnow() - timedelta(days=50)  # Too young

        fork_data = {
            "fork": mock_fork,
            "commits_ahead": 5,
            "activity_status": "active"
        }

        assert filter_obj.matches_fork(fork_data) is False

    def test_matches_fork_fails_fork_age_too_old(self):
        """Test fork matching fails on fork being too old."""
        filter_obj = PromisingForksFilter(
            min_fork_age_days=30,
            max_fork_age_days=365
        )

        mock_fork = Mock()
        mock_fork.stars = 10
        mock_fork.is_archived = False
        mock_fork.is_disabled = False
        mock_fork.pushed_at = datetime.utcnow() - timedelta(days=30)
        mock_fork.created_at = datetime.utcnow() - timedelta(days=400)  # Too old

        fork_data = {
            "fork": mock_fork,
            "commits_ahead": 5,
            "activity_status": "active"
        }

        assert filter_obj.matches_fork(fork_data) is False

    def test_matches_fork_fails_activity_score(self):
        """Test fork matching fails on activity score."""
        filter_obj = PromisingForksFilter(min_activity_score=0.8)

        mock_fork = Mock()
        mock_fork.stars = 10
        mock_fork.is_archived = False
        mock_fork.is_disabled = False
        mock_fork.pushed_at = datetime.utcnow() - timedelta(days=200)  # Low activity score
        mock_fork.created_at = datetime.utcnow() - timedelta(days=300)

        fork_data = {
            "fork": mock_fork,
            "commits_ahead": 5,
            "activity_status": "stale"
        }

        assert filter_obj.matches_fork(fork_data) is False

    def test_matches_fork_with_none_pushed_at(self):
        """Test fork matching with None pushed_at date."""
        filter_obj = PromisingForksFilter()

        mock_fork = Mock()
        mock_fork.stars = 10
        mock_fork.is_archived = False
        mock_fork.is_disabled = False
        mock_fork.pushed_at = None  # No push date
        mock_fork.created_at = datetime.utcnow() - timedelta(days=100)

        fork_data = {
            "fork": mock_fork,
            "commits_ahead": 5,
            "activity_status": "inactive"
        }

        # Should pass other criteria but fail on activity score (0.0 for None pushed_at)
        assert filter_obj.matches_fork(fork_data) is True  # min_activity_score is 0.0 by default

    def test_calculate_activity_score_recent(self):
        """Test activity score calculation for recent activity."""
        filter_obj = PromisingForksFilter()

        # Recent activity (within 7 days)
        recent_date = datetime.utcnow() - timedelta(days=3)
        score = filter_obj._calculate_activity_score("active", recent_date)
        assert score == 1.0

    def test_calculate_activity_score_moderate(self):
        """Test activity score calculation for moderate activity."""
        filter_obj = PromisingForksFilter()

        # Moderate activity (within 30 days)
        moderate_date = datetime.utcnow() - timedelta(days=20)
        score = filter_obj._calculate_activity_score("moderate", moderate_date)
        assert score == 0.8

    def test_calculate_activity_score_stale(self):
        """Test activity score calculation for stale activity."""
        filter_obj = PromisingForksFilter()

        # Stale activity (within 90 days)
        stale_date = datetime.utcnow() - timedelta(days=60)
        score = filter_obj._calculate_activity_score("stale", stale_date)
        assert score == 0.5

    def test_calculate_activity_score_old(self):
        """Test activity score calculation for old activity."""
        filter_obj = PromisingForksFilter()

        # Old activity (within 365 days)
        old_date = datetime.utcnow() - timedelta(days=200)
        score = filter_obj._calculate_activity_score("inactive", old_date)
        assert score == 0.2

    def test_calculate_activity_score_very_old(self):
        """Test activity score calculation for very old activity."""
        filter_obj = PromisingForksFilter()

        # Very old activity (over 365 days)
        very_old_date = datetime.utcnow() - timedelta(days=400)
        score = filter_obj._calculate_activity_score("inactive", very_old_date)
        assert score == 0.1

    def test_calculate_activity_score_none_date(self):
        """Test activity score calculation with None date."""
        filter_obj = PromisingForksFilter()

        score = filter_obj._calculate_activity_score("unknown", None)
        assert score == 0.0


class TestForkDetailsFilter:
    """Test ForkDetailsFilter functionality."""

    def test_default_filter_creation(self):
        """Test creating filter with default values."""
        filter_obj = ForkDetailsFilter()

        assert filter_obj.include_branches is True
        assert filter_obj.include_contributors is True
        assert filter_obj.include_commit_stats is True
        assert filter_obj.max_branches == 10
        assert filter_obj.max_contributors == 10

    def test_custom_filter_creation(self):
        """Test creating filter with custom values."""
        filter_obj = ForkDetailsFilter(
            include_branches=False,
            include_contributors=False,
            include_commit_stats=False,
            max_branches=5,
            max_contributors=20
        )

        assert filter_obj.include_branches is False
        assert filter_obj.include_contributors is False
        assert filter_obj.include_commit_stats is False
        assert filter_obj.max_branches == 5
        assert filter_obj.max_contributors == 20


class TestBranchInfo:
    """Test BranchInfo model functionality."""

    def test_branch_info_creation(self):
        """Test creating BranchInfo with all fields."""
        branch_date = datetime.utcnow()

        branch_info = BranchInfo(
            name="feature-branch",
            commit_count=25,
            last_commit_date=branch_date,
            commits_ahead_of_main=10,
            is_default=False,
            is_protected=True
        )

        assert branch_info.name == "feature-branch"
        assert branch_info.commit_count == 25
        assert branch_info.last_commit_date == branch_date
        assert branch_info.commits_ahead_of_main == 10
        assert branch_info.is_default is False
        assert branch_info.is_protected is True

    def test_branch_info_defaults(self):
        """Test BranchInfo with default values."""
        branch_info = BranchInfo(name="main")

        assert branch_info.name == "main"
        assert branch_info.commit_count == 0
        assert branch_info.last_commit_date is None
        assert branch_info.commits_ahead_of_main == 0
        assert branch_info.is_default is False
        assert branch_info.is_protected is False


class TestForkDetails:
    """Test ForkDetails model functionality."""

    def test_fork_details_creation(self):
        """Test creating ForkDetails with all fields."""
        mock_fork = Mock()
        mock_fork.name = "test-repo"

        branch_info = BranchInfo(name="main", commit_count=100)

        fork_details = ForkDetails(
            fork=mock_fork,
            branches=[branch_info],
            total_commits=100,
            contributors=["user1", "user2"],
            contributor_count=2,
            languages={"Python": 1000, "JavaScript": 500},
            topics=["web", "api"]
        )

        assert fork_details.fork == mock_fork
        assert len(fork_details.branches) == 1
        assert fork_details.branches[0].name == "main"
        assert fork_details.total_commits == 100
        assert fork_details.contributors == ["user1", "user2"]
        assert fork_details.contributor_count == 2
        assert fork_details.languages == {"Python": 1000, "JavaScript": 500}
        assert fork_details.topics == ["web", "api"]

    def test_fork_details_defaults(self):
        """Test ForkDetails with default values."""
        mock_fork = Mock()

        fork_details = ForkDetails(fork=mock_fork)

        assert fork_details.fork == mock_fork
        assert fork_details.branches == []
        assert fork_details.total_commits == 0
        assert fork_details.contributors == []
        assert fork_details.contributor_count == 0
        assert fork_details.languages == {}
        assert fork_details.topics == []
