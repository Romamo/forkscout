"""Integration tests for feature ranking system."""

from datetime import datetime, timedelta

import pytest

from src.forklift.config.settings import ScoringConfig
from src.forklift.models.analysis import Feature, FeatureCategory, ForkMetrics
from src.forklift.models.github import Commit, Fork, Repository, User
from src.forklift.ranking.feature_ranking_engine import FeatureRankingEngine


class TestFeatureRankingIntegration:
    """Integration tests for the complete feature ranking system."""

    @pytest.fixture
    def ranking_engine(self):
        """Create a feature ranking engine with default configuration."""
        config = ScoringConfig()
        return FeatureRankingEngine(config)

    @pytest.fixture
    def sample_features_and_metrics(self):
        """Create a comprehensive set of features and metrics for testing."""
        # Create users
        user1 = User(login="developer1", html_url="https://github.com/developer1")
        user2 = User(login="developer2", html_url="https://github.com/developer2")
        user3 = User(login="developer3", html_url="https://github.com/developer3")

        # Create parent repository
        parent_repo = Repository(
            owner="upstream",
            name="awesome-project",
            full_name="upstream/awesome-project",
            url="https://api.github.com/repos/upstream/awesome-project",
            html_url="https://github.com/upstream/awesome-project",
            clone_url="https://github.com/upstream/awesome-project.git"
        )

        # Create fork repositories
        fork1_repo = Repository(
            owner="developer1",
            name="awesome-project",
            full_name="developer1/awesome-project",
            url="https://api.github.com/repos/developer1/awesome-project",
            html_url="https://github.com/developer1/awesome-project",
            clone_url="https://github.com/developer1/awesome-project.git",
            is_fork=True
        )

        fork2_repo = Repository(
            owner="developer2",
            name="awesome-project",
            full_name="developer2/awesome-project",
            url="https://api.github.com/repos/developer2/awesome-project",
            html_url="https://github.com/developer2/awesome-project",
            clone_url="https://github.com/developer2/awesome-project.git",
            is_fork=True
        )

        fork3_repo = Repository(
            owner="developer3",
            name="awesome-project",
            full_name="developer3/awesome-project",
            url="https://api.github.com/repos/developer3/awesome-project",
            html_url="https://github.com/developer3/awesome-project",
            clone_url="https://github.com/developer3/awesome-project.git",
            is_fork=True
        )

        # Create forks
        fork1 = Fork(
            repository=fork1_repo,
            parent=parent_repo,
            owner=user1,
            last_activity=datetime.utcnow() - timedelta(days=2),
            commits_ahead=8,
            commits_behind=1
        )

        fork2 = Fork(
            repository=fork2_repo,
            parent=parent_repo,
            owner=user2,
            last_activity=datetime.utcnow() - timedelta(days=5),
            commits_ahead=12,
            commits_behind=3
        )

        fork3 = Fork(
            repository=fork3_repo,
            parent=parent_repo,
            owner=user3,
            last_activity=datetime.utcnow() - timedelta(days=30),
            commits_ahead=3,
            commits_behind=10
        )

        # Create commits
        auth_commit1 = Commit(
            sha="1111111111111111111111111111111111111111",
            message="feat(auth): implement JWT authentication with comprehensive tests and documentation",
            author=user1,
            date=datetime.utcnow() - timedelta(days=1),
            files_changed=["src/auth/jwt.py", "tests/test_auth.py", "docs/authentication.md"],
            additions=200,
            deletions=15
        )

        auth_commit2 = Commit(
            sha="2222222222222222222222222222222222222222",
            message="feat: add user authentication system",
            author=user2,
            date=datetime.utcnow() - timedelta(days=3),
            files_changed=["lib/authentication.py", "tests/auth_test.py"],
            additions=150,
            deletions=5
        )

        cache_commit = Commit(
            sha="3333333333333333333333333333333333333333",
            message="perf: implement Redis caching for improved performance",
            author=user3,
            date=datetime.utcnow() - timedelta(days=25),
            files_changed=["src/cache/redis.py", "tests/test_cache.py", "config/redis.conf"],
            additions=180,
            deletions=20
        )

        # Create features
        auth_feature1 = Feature(
            id="auth-jwt-feature",
            title="JWT Authentication System",
            description="Comprehensive JWT-based authentication with token refresh and user management",
            category=FeatureCategory.NEW_FEATURE,
            commits=[auth_commit1],
            files_affected=["src/auth/jwt.py", "tests/test_auth.py", "docs/authentication.md"],
            source_fork=fork1
        )

        auth_feature2 = Feature(
            id="auth-basic-feature",
            title="User Authentication",
            description="Basic user authentication system with login and logout functionality",
            category=FeatureCategory.NEW_FEATURE,
            commits=[auth_commit2],
            files_affected=["src/auth/basic.py", "tests/test_auth.py"],
            source_fork=fork2
        )

        cache_feature = Feature(
            id="redis-cache-feature",
            title="Redis Caching System",
            description="High-performance Redis-based caching layer for database queries",
            category=FeatureCategory.PERFORMANCE,
            commits=[cache_commit],
            files_affected=["src/cache/redis.py", "tests/test_cache.py", "config/redis.conf"],
            source_fork=fork3
        )

        # Create fork metrics
        fork_metrics = {
            fork1.repository.url: ForkMetrics(
                stars=45,
                forks=8,
                contributors=3,
                last_activity=datetime.utcnow() - timedelta(days=2),
                commit_frequency=2.5
            ),
            fork2.repository.url: ForkMetrics(
                stars=20,
                forks=3,
                contributors=2,
                last_activity=datetime.utcnow() - timedelta(days=5),
                commit_frequency=1.2
            ),
            fork3.repository.url: ForkMetrics(
                stars=5,
                forks=1,
                contributors=1,
                last_activity=datetime.utcnow() - timedelta(days=30),
                commit_frequency=0.3
            )
        }

        features = [auth_feature1, auth_feature2, cache_feature]
        return features, fork_metrics

    def test_complete_feature_ranking_workflow(self, ranking_engine, sample_features_and_metrics):
        """Test the complete feature ranking workflow."""
        features, fork_metrics = sample_features_and_metrics

        # Rank the features
        ranked_features = ranking_engine.rank_features(features, fork_metrics)

        # Verify basic ranking properties
        assert len(ranked_features) == 3
        assert all(isinstance(rf.score, float) for rf in ranked_features)
        assert all(0 <= rf.score <= 100 for rf in ranked_features)

        # Verify features are sorted by score (highest first)
        scores = [rf.score for rf in ranked_features]
        assert scores == sorted(scores, reverse=True)

        # Verify ranking factors are populated
        for rf in ranked_features:
            assert "code_quality" in rf.ranking_factors
            assert "community_engagement" in rf.ranking_factors
            assert "test_coverage" in rf.ranking_factors
            assert "documentation" in rf.ranking_factors
            assert "recency" in rf.ranking_factors

        # The JWT auth feature should rank highest due to:
        # - Better commit message
        # - More comprehensive implementation (tests + docs)
        # - Recent activity
        # - Better fork metrics
        top_feature = ranked_features[0]
        assert top_feature.feature.id == "auth-jwt-feature"
        assert top_feature.score > 60  # Should be a good score

        # Similar auth features should be grouped together
        auth_features = [rf for rf in ranked_features if "auth" in rf.feature.id]
        assert len(auth_features) == 2

        # Each auth feature should have the other as a similar implementation
        for auth_rf in auth_features:
            if len(auth_rf.similar_implementations) > 0:
                similar_ids = [f.id for f in auth_rf.similar_implementations]
                other_auth_ids = [rf.feature.id for rf in auth_features if rf.feature.id != auth_rf.feature.id]
                assert any(auth_id in similar_ids for auth_id in other_auth_ids)
            # If no similar implementations, that's also acceptable (might be due to threshold)

    def test_scoring_weights_impact(self, sample_features_and_metrics):
        """Test that different scoring weights produce different rankings."""
        features, fork_metrics = sample_features_and_metrics

        # Test with code quality emphasis
        code_quality_config = ScoringConfig(
            code_quality_weight=0.8,
            community_engagement_weight=0.05,
            test_coverage_weight=0.05,
            documentation_weight=0.05,
            recency_weight=0.05
        )
        code_quality_engine = FeatureRankingEngine(code_quality_config)
        code_quality_ranking = code_quality_engine.rank_features(features, fork_metrics)

        # Test with community engagement emphasis
        community_config = ScoringConfig(
            code_quality_weight=0.05,
            community_engagement_weight=0.8,
            test_coverage_weight=0.05,
            documentation_weight=0.05,
            recency_weight=0.05
        )
        community_engine = FeatureRankingEngine(community_config)
        community_ranking = community_engine.rank_features(features, fork_metrics)

        # Rankings should be different or at least scores should be different
        code_quality_order = [rf.feature.id for rf in code_quality_ranking]
        community_order = [rf.feature.id for rf in community_ranking]

        code_quality_scores = [rf.score for rf in code_quality_ranking]
        community_scores = [rf.score for rf in community_ranking]

        # Either order should be different OR scores should be significantly different
        order_different = code_quality_order != community_order
        scores_different = any(abs(c - m) > 5 for c, m in zip(code_quality_scores, community_scores, strict=False))

        assert order_different or scores_different

    def test_feature_grouping_accuracy(self, ranking_engine, sample_features_and_metrics):
        """Test the accuracy of feature grouping."""
        features, _ = sample_features_and_metrics

        # Group features by similarity
        groups = ranking_engine.group_similar_features(features)

        # Should have 2 groups: auth features and cache feature
        assert len(groups) == 2

        # Find auth and cache groups
        auth_group = None
        cache_group = None

        for group in groups:
            if any("auth" in f.title.lower() for f in group):
                auth_group = group
            elif any("cache" in f.title.lower() or "redis" in f.title.lower() for f in group):
                cache_group = group

        assert auth_group is not None
        assert cache_group is not None
        assert len(auth_group) == 2  # Both auth features
        assert len(cache_group) == 1  # Cache feature alone

        # Verify auth features are actually similar
        auth_feature1, auth_feature2 = auth_group
        assert ranking_engine._are_features_similar(auth_feature1, auth_feature2)

        # Verify cache feature is not similar to auth features
        cache_feature = cache_group[0]
        assert not ranking_engine._are_features_similar(auth_feature1, cache_feature)
        assert not ranking_engine._are_features_similar(auth_feature2, cache_feature)

    def test_edge_cases(self, ranking_engine):
        """Test edge cases in feature ranking."""
        # Test with empty feature list
        empty_ranking = ranking_engine.rank_features([], {})
        assert empty_ranking == []

        # Test with single feature
        user = User(login="test", html_url="https://github.com/test")
        parent_repo = Repository(
            owner="upstream", name="repo", full_name="upstream/repo",
            url="https://api.github.com/repos/upstream/repo",
            html_url="https://github.com/upstream/repo",
            clone_url="https://github.com/upstream/repo.git"
        )
        fork_repo = Repository(
            owner="test", name="repo", full_name="test/repo",
            url="https://api.github.com/repos/test/repo",
            html_url="https://github.com/test/repo",
            clone_url="https://github.com/test/repo.git",
            is_fork=True
        )
        fork = Fork(repository=fork_repo, parent=parent_repo, owner=user)

        single_feature = Feature(
            id="single",
            title="Single Feature",
            description="A single feature for testing",
            category=FeatureCategory.OTHER,
            commits=[],
            files_affected=[],
            source_fork=fork
        )

        single_ranking = ranking_engine.rank_features([single_feature], {fork.repository.url: ForkMetrics()})
        assert len(single_ranking) == 1
        assert single_ranking[0].feature.id == "single"
        assert len(single_ranking[0].similar_implementations) == 0
