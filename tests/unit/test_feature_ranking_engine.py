"""Tests for the FeatureRankingEngine."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from src.forklift.config.settings import ScoringConfig
from src.forklift.models.analysis import Feature, ForkMetrics, FeatureCategory
from src.forklift.models.github import Fork, Repository, Commit, User
from src.forklift.ranking.feature_ranking_engine import FeatureRankingEngine


class TestFeatureRankingEngine:
    """Test cases for FeatureRankingEngine."""

    @pytest.fixture
    def scoring_config(self):
        """Create a test scoring configuration."""
        return ScoringConfig()

    @pytest.fixture
    def ranking_engine(self, scoring_config):
        """Create a FeatureRankingEngine instance."""
        return FeatureRankingEngine(scoring_config)

    @pytest.fixture
    def sample_repository(self):
        """Create a sample repository."""
        return Repository(
            owner="test-owner",
            name="test-repo",
            full_name="test-owner/test-repo",
            url="https://api.github.com/repos/test-owner/test-repo",
            html_url="https://github.com/test-owner/test-repo",
            clone_url="https://github.com/test-owner/test-repo.git",
            default_branch="main",
            stars=100,
            forks_count=50
        )

    @pytest.fixture
    def sample_user(self):
        """Create a sample user."""
        return User(
            login="test-user",
            html_url="https://github.com/test-user"
        )

    @pytest.fixture
    def sample_fork(self, sample_repository, sample_user):
        """Create a sample fork."""
        fork_repo = Repository(
            owner="fork-owner",
            name="test-repo",
            full_name="fork-owner/test-repo",
            url="https://api.github.com/repos/fork-owner/test-repo",
            html_url="https://github.com/fork-owner/test-repo",
            clone_url="https://github.com/fork-owner/test-repo.git",
            default_branch="main",
            stars=10,
            forks_count=2,
            is_fork=True
        )
        return Fork(
            repository=fork_repo,
            parent=sample_repository,
            owner=sample_user,
            last_activity=datetime.utcnow() - timedelta(days=7),
            commits_ahead=5,
            commits_behind=2
        )

    @pytest.fixture
    def sample_commit(self, sample_user):
        """Create a sample commit."""
        return Commit(
            sha="a1b2c3d4e5f6789012345678901234567890abcd",
            message="feat: add user authentication system",
            author=sample_user,
            date=datetime.utcnow() - timedelta(days=1),
            files_changed=["src/auth.py", "tests/test_auth.py", "README.md"],
            additions=150,
            deletions=20
        )

    @pytest.fixture
    def sample_feature(self, sample_fork, sample_commit):
        """Create a sample feature."""
        return Feature(
            id="feature-1",
            title="User Authentication",
            description="Adds JWT-based user authentication",
            category=FeatureCategory.NEW_FEATURE,
            commits=[sample_commit],
            files_affected=["src/auth.py", "tests/test_auth.py", "README.md"],
            source_fork=sample_fork
        )

    @pytest.fixture
    def sample_fork_metrics(self):
        """Create sample fork metrics."""
        return ForkMetrics(
            stars=25,
            forks=5,
            contributors=3,
            last_activity=datetime.utcnow() - timedelta(days=5),
            commit_frequency=0.5
        )

    def test_calculate_feature_score_basic(self, ranking_engine, sample_feature, sample_fork_metrics):
        """Test basic feature score calculation."""
        score = ranking_engine.calculate_feature_score(sample_feature, sample_fork_metrics)
        
        assert 0 <= score <= 100
        assert isinstance(score, float)

    def test_calculate_feature_score_with_good_metrics(self, ranking_engine, sample_feature):
        """Test feature scoring with good fork metrics."""
        good_metrics = ForkMetrics(
            stars=100,
            forks=20,
            contributors=10,
            last_activity=datetime.utcnow() - timedelta(days=1),
            commit_frequency=2.0
        )
        
        score = ranking_engine.calculate_feature_score(sample_feature, good_metrics)
        assert score > 50  # Should be above average with good metrics

    def test_calculate_feature_score_with_poor_metrics(self, ranking_engine, sample_feature):
        """Test feature scoring with poor fork metrics."""
        poor_metrics = ForkMetrics(
            stars=0,
            forks=0,
            contributors=1,
            last_activity=datetime.utcnow() - timedelta(days=365),
            commit_frequency=0.0
        )
        
        score = ranking_engine.calculate_feature_score(sample_feature, poor_metrics)
        assert score < 70  # Should be lower with poor metrics

    def test_rank_features_sorting(self, ranking_engine, sample_fork):
        """Test that features are ranked correctly by score."""
        # Create features with different characteristics
        author1 = User(login="author1", html_url="https://github.com/author1")
        author2 = User(login="author2", html_url="https://github.com/author2")
        
        recent_commit = Commit(
            sha="1234567890abcdef1234567890abcdef12345678",
            message="feat: add excellent new feature with comprehensive tests",
            author=author1,
            date=datetime.utcnow() - timedelta(days=1),
            files_changed=["src/feature.py", "tests/test_feature.py", "docs/feature.md"],
            additions=100,
            deletions=10
        )
        
        old_commit = Commit(
            sha="abcdef1234567890abcdef1234567890abcdef12",
            message="fix",
            author=author2,
            date=datetime.utcnow() - timedelta(days=365),
            files_changed=["src/old.py"],
            additions=5,
            deletions=1
        )
        
        good_feature = Feature(
            id="good-feature",
            title="Excellent Feature",
            description="Well-documented feature with tests",
            category=FeatureCategory.NEW_FEATURE,
            commits=[recent_commit],
            files_affected=["src/feature.py", "tests/test_feature.py", "docs/feature.md"],
            source_fork=sample_fork
        )
        
        poor_feature = Feature(
            id="poor-feature",
            title="Poor Feature",
            description="Minimal feature",
            category=FeatureCategory.OTHER,
            commits=[old_commit],
            files_affected=["src/old.py"],
            source_fork=sample_fork
        )
        
        features = [poor_feature, good_feature]  # Intentionally out of order
        fork_metrics_map = {
            sample_fork.repository.url: ForkMetrics(
                stars=50,
                forks=10,
                contributors=5,
                last_activity=datetime.utcnow() - timedelta(days=2),
                commit_frequency=1.0
            )
        }
        
        ranked_features = ranking_engine.rank_features(features, fork_metrics_map)
        
        assert len(ranked_features) == 2
        assert ranked_features[0].feature.id == "good-feature"  # Should be ranked first
        assert ranked_features[1].feature.id == "poor-feature"  # Should be ranked second
        assert ranked_features[0].score > ranked_features[1].score

    def test_rank_features_includes_ranking_factors(self, ranking_engine, sample_feature, sample_fork_metrics):
        """Test that ranking includes breakdown of factors."""
        features = [sample_feature]
        fork_metrics_map = {sample_feature.source_fork.repository.url: sample_fork_metrics}
        
        ranked_features = ranking_engine.rank_features(features, fork_metrics_map)
        
        assert len(ranked_features) == 1
        ranked_feature = ranked_features[0]
        
        # Check that ranking factors are included
        assert "code_quality" in ranked_feature.ranking_factors
        assert "community_engagement" in ranked_feature.ranking_factors
        assert "test_coverage" in ranked_feature.ranking_factors
        assert "documentation" in ranked_feature.ranking_factors
        assert "recency" in ranked_feature.ranking_factors
        
        # All factors should be numeric
        for factor_score in ranked_feature.ranking_factors.values():
            assert isinstance(factor_score, (int, float))
            assert 0 <= factor_score <= 100

    def test_code_quality_score_with_good_commit_message(self, ranking_engine, sample_fork):
        """Test code quality scoring with good commit messages."""
        author = User(login="author", html_url="https://github.com/author")
        good_commit = Commit(
            sha="1111111111111111111111111111111111111111",
            message="feat(auth): implement JWT token validation with comprehensive error handling",
            author=author,
            date=datetime.utcnow(),
            files_changed=["src/auth.py", "tests/test_auth.py"],
            additions=80,
            deletions=10
        )
        
        feature = Feature(
            id="test-feature",
            title="Test Feature",
            description="Test",
            category=FeatureCategory.NEW_FEATURE,
            commits=[good_commit],
            files_affected=["src/auth.py", "tests/test_auth.py"],
            source_fork=sample_fork
        )
        
        score = ranking_engine._calculate_code_quality_score(feature)
        assert score > 50  # Should be above average

    def test_code_quality_score_with_poor_commit_message(self, ranking_engine, sample_fork):
        """Test code quality scoring with poor commit messages."""
        author = User(login="author", html_url="https://github.com/author")
        poor_commit = Commit(
            sha="2222222222222222222222222222222222222222",
            message="fix",
            author=author,
            date=datetime.utcnow(),
            files_changed=["file.py"],
            additions=1,
            deletions=0
        )
        
        feature = Feature(
            id="test-feature",
            title="Test Feature",
            description="Test",
            category=FeatureCategory.BUG_FIX,
            commits=[poor_commit],
            files_affected=["file.py"],
            source_fork=sample_fork
        )
        
        score = ranking_engine._calculate_code_quality_score(feature)
        assert score < 60  # Should be below average

    def test_community_engagement_score_calculation(self, ranking_engine):
        """Test community engagement score calculation."""
        high_engagement_metrics = ForkMetrics(
            stars=200,
            forks=50,
            contributors=15,
            last_activity=datetime.utcnow() - timedelta(days=1),
            commit_frequency=3.0
        )
        
        low_engagement_metrics = ForkMetrics(
            stars=0,
            forks=0,
            contributors=1,
            last_activity=datetime.utcnow() - timedelta(days=365),
            commit_frequency=0.0
        )
        
        high_score = ranking_engine._calculate_community_engagement_score(high_engagement_metrics)
        low_score = ranking_engine._calculate_community_engagement_score(low_engagement_metrics)
        
        assert high_score > low_score
        assert 0 <= high_score <= 100
        assert 0 <= low_score <= 100

    def test_test_coverage_score_with_tests(self, ranking_engine, sample_fork):
        """Test coverage scoring when tests are present."""
        feature_with_tests = Feature(
            id="test-feature",
            title="Feature with Tests",
            description="Well-tested feature",
            category=FeatureCategory.NEW_FEATURE,
            commits=[],
            files_affected=["src/feature.py", "tests/test_feature.py"],
            source_fork=sample_fork
        )
        
        score = ranking_engine._calculate_test_coverage_score(feature_with_tests)
        assert score >= 80  # Should have high score with 1:1 test ratio

    def test_test_coverage_score_without_tests(self, ranking_engine, sample_fork):
        """Test coverage scoring when no tests are present."""
        feature_without_tests = Feature(
            id="test-feature",
            title="Feature without Tests",
            description="Untested feature",
            category=FeatureCategory.NEW_FEATURE,
            commits=[],
            files_affected=["src/feature.py"],
            source_fork=sample_fork
        )
        
        score = ranking_engine._calculate_test_coverage_score(feature_without_tests)
        assert score <= 30  # Should have low score without tests

    def test_documentation_score_with_docs(self, ranking_engine, sample_fork):
        """Test documentation scoring with documentation files."""
        author = User(login="author", html_url="https://github.com/author")
        
        feature_with_docs = Feature(
            id="test-feature",
            title="Documented Feature",
            description="Well-documented feature",
            category=FeatureCategory.NEW_FEATURE,
            commits=[
                Commit(
                    sha="3333333333333333333333333333333333333333",
                    message="docs: add comprehensive documentation for new authentication system",
                    author=author,
                    date=datetime.utcnow(),
                    files_changed=["docs/auth.md", "README.md"],
                    additions=100,
                    deletions=5
                )
            ],
            files_affected=["src/auth.py", "docs/auth.md", "README.md"],
            source_fork=sample_fork
        )
        
        score = ranking_engine._calculate_documentation_score(feature_with_docs)
        assert score >= 70  # Should have high score with documentation

    def test_recency_score_calculation(self, ranking_engine, sample_fork):
        """Test recency score calculation."""
        author = User(login="author", html_url="https://github.com/author")
        
        recent_feature = Feature(
            id="recent-feature",
            title="Recent Feature",
            description="Recently added",
            category=FeatureCategory.NEW_FEATURE,
            commits=[
                Commit(
                    sha="4444444444444444444444444444444444444444",
                    message="feat: recent change",
                    author=author,
                    date=datetime.utcnow() - timedelta(days=1),
                    files_changed=["file.py"],
                    additions=10,
                    deletions=0
                )
            ],
            files_affected=["file.py"],
            source_fork=sample_fork
        )
        
        old_feature = Feature(
            id="old-feature",
            title="Old Feature",
            description="Old addition",
            category=FeatureCategory.NEW_FEATURE,
            commits=[
                Commit(
                    sha="5555555555555555555555555555555555555555",
                    message="feat: old change",
                    author=author,
                    date=datetime.utcnow() - timedelta(days=400),
                    files_changed=["file.py"],
                    additions=10,
                    deletions=0
                )
            ],
            files_affected=["file.py"],
            source_fork=sample_fork
        )
        
        recent_score = ranking_engine._calculate_recency_score(recent_feature)
        old_score = ranking_engine._calculate_recency_score(old_feature)
        
        assert recent_score > old_score
        assert recent_score >= 90  # Recent should be high
        assert old_score <= 20     # Old should be low

    def test_commit_message_quality_analysis(self, ranking_engine):
        """Test commit message quality analysis."""
        # Good conventional commit
        good_score = ranking_engine._analyze_commit_message_quality(
            "feat(auth): implement JWT token validation with error handling"
        )
        
        # Poor commit message
        poor_score = ranking_engine._analyze_commit_message_quality("fix")
        
        # Empty commit message
        empty_score = ranking_engine._analyze_commit_message_quality("")
        
        assert good_score > poor_score
        assert poor_score > empty_score  # Poor should be better than empty
        assert empty_score < 0  # Should be negative

    def test_change_size_analysis(self, ranking_engine):
        """Test change size analysis."""
        # Moderate changes (preferred)
        moderate_score = ranking_engine._analyze_change_size(50, 10)
        
        # Very large changes (less preferred)
        large_score = ranking_engine._analyze_change_size(1000, 500)
        
        # Very small changes (might be trivial)
        small_score = ranking_engine._analyze_change_size(1, 0)
        
        assert moderate_score > large_score
        assert moderate_score > small_score

    def test_file_type_detection(self, ranking_engine):
        """Test file type detection methods."""
        # Test files
        assert ranking_engine._is_test_file("test_auth.py")
        assert ranking_engine._is_test_file("tests/test_user.py")
        assert ranking_engine._is_test_file("auth_test.py")
        assert not ranking_engine._is_test_file("auth.py")
        
        # Source files
        assert ranking_engine._is_source_file("auth.py")
        assert ranking_engine._is_source_file("main.js")
        assert not ranking_engine._is_source_file("test_auth.py")
        assert not ranking_engine._is_source_file("README.md")
        
        # Documentation files
        assert ranking_engine._is_documentation_file("README.md")
        assert ranking_engine._is_documentation_file("docs/guide.rst")
        assert not ranking_engine._is_documentation_file("auth.py")

    def test_scoring_config_weights_applied(self, sample_feature, sample_fork_metrics):
        """Test that scoring configuration weights are properly applied."""
        # Create config with extreme weights to test application
        config = ScoringConfig(
            code_quality_weight=1.0,
            community_engagement_weight=0.0,
            test_coverage_weight=0.0,
            documentation_weight=0.0,
            recency_weight=0.0
        )
        
        engine = FeatureRankingEngine(config)
        score = engine.calculate_feature_score(sample_feature, sample_fork_metrics)
        
        # Score should only reflect code quality
        code_quality_score = engine._calculate_code_quality_score(sample_feature)
        assert abs(score - code_quality_score) < 0.1  # Allow for floating point precision

    def test_score_bounds_enforcement(self, ranking_engine, sample_feature):
        """Test that scores are always within 0-100 bounds."""
        # Test with extreme metrics that might cause out-of-bounds scores
        extreme_metrics = ForkMetrics(
            stars=10000,
            forks=1000,
            contributors=100,
            last_activity=datetime.utcnow(),
            commit_frequency=100.0
        )
        
        score = ranking_engine.calculate_feature_score(sample_feature, extreme_metrics)
        assert 0 <= score <= 100

    def test_empty_feature_handling(self, ranking_engine, sample_fork):
        """Test handling of features with no commits or files."""
        empty_feature = Feature(
            id="empty-feature",
            title="Empty Feature",
            description="Feature with no commits",
            category=FeatureCategory.OTHER,
            commits=[],
            files_affected=[],
            source_fork=sample_fork
        )
        
        empty_metrics = ForkMetrics()
        
        score = ranking_engine.calculate_feature_score(empty_feature, empty_metrics)
        assert 0 <= score <= 100
        assert score < 50  # Should be low for empty feature

    def test_group_similar_features(self, ranking_engine, sample_user):
        """Test feature grouping functionality."""
        # Create similar features
        auth_feature1 = Feature(
            id="auth-feature-1",
            title="User Authentication System",
            description="Implements JWT-based user authentication with login and logout",
            category=FeatureCategory.NEW_FEATURE,
            commits=[],
            files_affected=["src/auth.py", "tests/test_auth.py"],
            source_fork=self._create_test_fork("fork1", sample_user)
        )
        
        auth_feature2 = Feature(
            id="auth-feature-2", 
            title="Authentication System",
            description="Adds JWT authentication for user login and session management",
            category=FeatureCategory.NEW_FEATURE,
            commits=[],
            files_affected=["lib/authentication.py", "tests/auth_test.py"],
            source_fork=self._create_test_fork("fork2", sample_user)
        )
        
        # Create dissimilar feature
        cache_feature = Feature(
            id="cache-feature",
            title="Redis Caching",
            description="Implements Redis-based caching for improved performance",
            category=FeatureCategory.PERFORMANCE,
            commits=[],
            files_affected=["src/cache.py", "tests/test_cache.py"],
            source_fork=self._create_test_fork("fork3", sample_user)
        )
        
        features = [auth_feature1, auth_feature2, cache_feature]
        groups = ranking_engine.group_similar_features(features)
        
        # Should have 2 groups: one with auth features, one with cache feature
        assert len(groups) == 2
        
        # Find the auth group and cache group
        auth_group = None
        cache_group = None
        
        for group in groups:
            if any(f.id.startswith("auth") for f in group):
                auth_group = group
            elif any(f.id.startswith("cache") for f in group):
                cache_group = group
        
        assert auth_group is not None
        assert cache_group is not None
        assert len(auth_group) == 2  # Both auth features should be grouped
        assert len(cache_group) == 1  # Cache feature should be alone

    def test_feature_similarity_detection(self, ranking_engine, sample_user):
        """Test similarity detection between features."""
        feature1 = Feature(
            id="feature-1",
            title="User Authentication",
            description="JWT authentication system",
            category=FeatureCategory.NEW_FEATURE,
            commits=[],
            files_affected=["src/auth.py"],
            source_fork=self._create_test_fork("fork1", sample_user)
        )
        
        # Similar feature
        similar_feature = Feature(
            id="feature-2",
            title="Authentication System",
            description="JWT user authentication",
            category=FeatureCategory.NEW_FEATURE,
            commits=[],
            files_affected=["lib/auth.py"],
            source_fork=self._create_test_fork("fork2", sample_user)
        )
        
        # Dissimilar feature
        dissimilar_feature = Feature(
            id="feature-3",
            title="Database Migration",
            description="Migrate from MySQL to PostgreSQL",
            category=FeatureCategory.REFACTOR,
            commits=[],
            files_affected=["migrations/001.sql"],
            source_fork=self._create_test_fork("fork3", sample_user)
        )
        
        assert ranking_engine._are_features_similar(feature1, similar_feature)
        assert not ranking_engine._are_features_similar(feature1, dissimilar_feature)

    def test_text_similarity_calculation(self, ranking_engine):
        """Test text similarity calculation."""
        # Very similar texts
        text1 = "User authentication system"
        text2 = "Authentication system for users"
        similarity = ranking_engine._calculate_text_similarity(text1, text2)
        assert similarity > 0.6
        
        # Dissimilar texts
        text3 = "Database migration script"
        similarity2 = ranking_engine._calculate_text_similarity(text1, text3)
        assert similarity2 < 0.5  # Adjusted threshold
        
        # Empty text handling
        similarity3 = ranking_engine._calculate_text_similarity("", text1)
        assert similarity3 == 0.0

    def test_file_similarity_calculation(self, ranking_engine):
        """Test file similarity calculation."""
        files1 = ["src/auth.py", "tests/test_auth.py", "docs/auth.md"]
        files2 = ["src/auth.py", "tests/test_auth.py", "docs/authentication.md"]  # More similar files
        
        similarity = ranking_engine._calculate_file_similarity(files1, files2)
        assert 0.0 < similarity < 1.0  # Should have some similarity but not perfect
        
        # Identical files
        similarity2 = ranking_engine._calculate_file_similarity(files1, files1)
        assert similarity2 == 1.0
        
        # No overlap
        files3 = ["src/cache.py", "tests/test_cache.py"]
        similarity3 = ranking_engine._calculate_file_similarity(files1, files3)
        assert similarity3 == 0.0

    def test_ranking_with_similar_features(self, ranking_engine, sample_user):
        """Test that ranking populates similar_implementations field."""
        # Create similar features
        auth_feature1 = Feature(
            id="auth-1",
            title="JWT Authentication",
            description="JWT-based authentication system",
            category=FeatureCategory.NEW_FEATURE,
            commits=[],
            files_affected=["src/auth.py"],
            source_fork=self._create_test_fork("fork1", sample_user)
        )
        
        auth_feature2 = Feature(
            id="auth-2",
            title="User Authentication",
            description="Authentication system using JWT tokens",
            category=FeatureCategory.NEW_FEATURE,
            commits=[],
            files_affected=["lib/auth.py"],
            source_fork=self._create_test_fork("fork2", sample_user)
        )
        
        features = [auth_feature1, auth_feature2]
        fork_metrics_map = {
            auth_feature1.source_fork.repository.url: ForkMetrics(),
            auth_feature2.source_fork.repository.url: ForkMetrics()
        }
        
        ranked_features = ranking_engine.rank_features(features, fork_metrics_map)
        
        # Both features should have each other as similar implementations
        assert len(ranked_features) == 2
        for rf in ranked_features:
            assert len(rf.similar_implementations) == 1
            similar_feature = rf.similar_implementations[0]
            assert similar_feature.id != rf.feature.id

    def test_keyword_extraction(self, ranking_engine):
        """Test keyword extraction from text."""
        text = "This is a user authentication system with JWT tokens"
        keywords = ranking_engine._extract_keywords(text)
        
        # Should extract meaningful keywords and exclude stop words
        assert "user" in keywords
        assert "authentication" in keywords
        assert "system" in keywords
        assert "jwt" in keywords
        assert "tokens" in keywords
        
        # Should exclude stop words and short words
        assert "this" not in keywords
        assert "is" not in keywords
        assert "a" not in keywords
        assert "with" not in keywords

    def test_file_path_normalization(self, ranking_engine):
        """Test file path normalization."""
        # Test long paths
        long_path = "project/src/main/java/com/example/auth/AuthService.java"
        normalized = ranking_engine._normalize_file_path(long_path)
        assert normalized == "example/auth/authservice.java"  # Only last 3 parts
        
        # Test short paths
        short_path = "src/auth.py"
        normalized2 = ranking_engine._normalize_file_path(short_path)
        assert normalized2 == "src/auth.py"

    def _create_test_fork(self, fork_name: str, user: User) -> Fork:
        """Helper method to create test fork objects."""
        parent_repo = Repository(
            owner="upstream",
            name="repo",
            full_name="upstream/repo",
            url="https://api.github.com/repos/upstream/repo",
            html_url="https://github.com/upstream/repo",
            clone_url="https://github.com/upstream/repo.git"
        )
        
        fork_repo = Repository(
            owner=fork_name,
            name="repo",
            full_name=f"{fork_name}/repo",
            url=f"https://api.github.com/repos/{fork_name}/repo",
            html_url=f"https://github.com/{fork_name}/repo",
            clone_url=f"https://github.com/{fork_name}/repo.git",
            is_fork=True
        )
        
        return Fork(
            repository=fork_repo,
            parent=parent_repo,
            owner=user,
            commits_ahead=5,
            commits_behind=2
        )