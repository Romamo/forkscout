"""Unit tests for analysis data models."""


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
