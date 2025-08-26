"""Unit tests for analysis data models."""


from datetime import UTC

import pytest

from forklift.models import Feature, Fork, RankedFeature, Repository, User
from forklift.models.analysis import FeatureCategory


def test_feature_model():
    """Test Feature model creation and validation."""
    repo = Repository(
        owner="test-owner",
        name="test-repo",
        full_name="test-owner/test-repo",
        url="https://api.github.com/repos/test-owner/test-repo",
        html_url="https://github.com/test-owner/test-repo",
        clone_url="https://github.com/test-owner/test-repo.git",
        is_fork=True,
    )

    parent_repo = Repository(
        owner="original-owner",
        name="test-repo",
        full_name="original-owner/test-repo",
        url="https://api.github.com/repos/original-owner/test-repo",
        html_url="https://github.com/original-owner/test-repo",
        clone_url="https://github.com/original-owner/test-repo.git",
    )

    user = User(login="test-owner", html_url="https://github.com/test-owner")

    fork = Fork(
        repository=repo,
        parent=parent_repo,
        owner=user,
    )

    feature = Feature(
        id="feature-1",
        title="Test Feature",
        description="A test feature",
        category=FeatureCategory.NEW_FEATURE,
        source_fork=fork,
    )

    assert feature.id == "feature-1"
    assert feature.title == "Test Feature"
    assert feature.description == "A test feature"
    assert feature.category == FeatureCategory.NEW_FEATURE
    assert feature.commits == []
    assert feature.files_affected == []


def test_ranked_feature_model():
    """Test RankedFeature model creation and validation."""
    repo = Repository(
        owner="test-owner",
        name="test-repo",
        full_name="test-owner/test-repo",
        url="https://api.github.com/repos/test-owner/test-repo",
        html_url="https://github.com/test-owner/test-repo",
        clone_url="https://github.com/test-owner/test-repo.git",
        is_fork=True,
    )

    parent_repo = Repository(
        owner="original-owner",
        name="test-repo",
        full_name="original-owner/test-repo",
        url="https://api.github.com/repos/original-owner/test-repo",
        html_url="https://github.com/original-owner/test-repo",
        clone_url="https://github.com/original-owner/test-repo.git",
    )

    user = User(login="test-owner", html_url="https://github.com/test-owner")

    fork = Fork(
        repository=repo,
        parent=parent_repo,
        owner=user,
    )

    feature = Feature(
        id="feature-1",
        title="Test Feature",
        description="A test feature",
        category=FeatureCategory.NEW_FEATURE,
        source_fork=fork,
    )

    ranked_feature = RankedFeature(
        feature=feature,
        score=85.5,
        ranking_factors={"code_quality": 0.8, "community": 0.9},
    )

    assert ranked_feature.feature == feature
    assert ranked_feature.score == 85.5
    assert ranked_feature.ranking_factors["code_quality"] == 0.8
    assert ranked_feature.similar_implementations == []


def test_feature_score_validation():
    """Test that feature scores are validated to be between 0 and 100."""
    repo = Repository(
        owner="test-owner",
        name="test-repo",
        full_name="test-owner/test-repo",
        url="https://api.github.com/repos/test-owner/test-repo",
        html_url="https://github.com/test-owner/test-repo",
        clone_url="https://github.com/test-owner/test-repo.git",
        is_fork=True,
    )

    parent_repo = Repository(
        owner="original-owner",
        name="test-repo",
        full_name="original-owner/test-repo",
        url="https://api.github.com/repos/original-owner/test-repo",
        html_url="https://github.com/original-owner/test-repo",
        clone_url="https://github.com/original-owner/test-repo.git",
    )

    user = User(login="test-owner", html_url="https://github.com/test-owner")

    fork = Fork(
        repository=repo,
        parent=parent_repo,
        owner=user,
    )

    feature = Feature(
        id="feature-1",
        title="Test Feature",
        description="A test feature",
        category=FeatureCategory.NEW_FEATURE,
        source_fork=fork,
    )

    # Valid score
    ranked_feature = RankedFeature(feature=feature, score=50.0)
    assert ranked_feature.score == 50.0

    # Test boundary values
    ranked_feature_min = RankedFeature(feature=feature, score=0.0)
    assert ranked_feature_min.score == 0.0

    ranked_feature_max = RankedFeature(feature=feature, score=100.0)
    assert ranked_feature_max.score == 100.0

    # Invalid scores should raise validation error
    with pytest.raises(ValueError):
        RankedFeature(feature=feature, score=-1.0)

    with pytest.raises(ValueError):
        RankedFeature(feature=feature, score=101.0)


def test_fork_preview_item_model():
    """Test ForkPreviewItem model creation and validation."""
    from datetime import datetime

    from forklift.models.analysis import ForkPreviewItem

    fork_item = ForkPreviewItem(
        name="test-repo",
        owner="test-owner",
        stars=42,
        last_push_date=datetime(2023, 12, 1, tzinfo=UTC),
        fork_url="https://github.com/test-owner/test-repo",
        activity_status="Active",
        commits_ahead="Unknown"
    )

    assert fork_item.name == "test-repo"
    assert fork_item.owner == "test-owner"
    assert fork_item.stars == 42
    assert fork_item.last_push_date == datetime(2023, 12, 1, tzinfo=UTC)
    assert fork_item.fork_url == "https://github.com/test-owner/test-repo"
    assert fork_item.activity_status == "Active"
    assert fork_item.commits_ahead == "Unknown"


def test_fork_preview_item_model_defaults():
    """Test ForkPreviewItem model with default values."""
    from forklift.models.analysis import ForkPreviewItem

    fork_item = ForkPreviewItem(
        name="test-repo",
        owner="test-owner",
        fork_url="https://github.com/test-owner/test-repo",
        activity_status="No commits",
        commits_ahead="None"
    )

    assert fork_item.name == "test-repo"
    assert fork_item.owner == "test-owner"
    assert fork_item.stars == 0  # Default value
    assert fork_item.last_push_date is None  # Default value
    assert fork_item.fork_url == "https://github.com/test-owner/test-repo"
    assert fork_item.activity_status == "No commits"
    assert fork_item.commits_ahead == "None"


def test_forks_preview_model():
    """Test ForksPreview model creation and validation."""
    from datetime import datetime

    from forklift.models.analysis import ForkPreviewItem, ForksPreview

    fork_item1 = ForkPreviewItem(
        name="test-repo",
        owner="user1",
        stars=10,
        last_push_date=datetime(2023, 12, 1, tzinfo=UTC),
        fork_url="https://github.com/user1/test-repo",
        activity_status="Active",
        commits_ahead="Unknown"
    )

    fork_item2 = ForkPreviewItem(
        name="test-repo",
        owner="user2",
        stars=5,
        last_push_date=datetime(2023, 11, 1, tzinfo=UTC),
        fork_url="https://github.com/user2/test-repo",
        activity_status="Stale",
        commits_ahead="Unknown"
    )

    forks_preview = ForksPreview(
        total_forks=2,
        forks=[fork_item1, fork_item2]
    )

    assert forks_preview.total_forks == 2
    assert len(forks_preview.forks) == 2
    assert forks_preview.forks[0] == fork_item1
    assert forks_preview.forks[1] == fork_item2


def test_fork_preview_item_activity_status_validation():
    """Test ForkPreviewItem model activity status field validation."""
    import pytest

    from forklift.models.analysis import ForkPreviewItem

    # Test valid activity statuses
    valid_statuses = ["Active", "Stale", "No commits"]
    commits_ahead_statuses = ["Unknown", "Unknown", "None"]
    for status, commits_ahead in zip(valid_statuses, commits_ahead_statuses, strict=False):
        fork_item = ForkPreviewItem(
            name="test-repo",
            owner="test-owner",
            fork_url="https://github.com/test-owner/test-repo",
            activity_status=status,
            commits_ahead=commits_ahead
        )
        assert fork_item.activity_status == status
        assert fork_item.commits_ahead == commits_ahead

    # Test that activity_status is required
    with pytest.raises(Exception):  # ValidationError
        ForkPreviewItem(
            name="test-repo",
            owner="test-owner",
            fork_url="https://github.com/test-owner/test-repo"
            # Missing activity_status
        )


def test_forks_preview_model_empty():
    """Test ForksPreview model with empty forks list."""
    from forklift.models.analysis import ForksPreview

    forks_preview = ForksPreview(total_forks=0)

    assert forks_preview.total_forks == 0
    assert forks_preview.forks == []  # Default empty list
