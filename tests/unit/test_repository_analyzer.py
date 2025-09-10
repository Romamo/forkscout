"""Tests for repository analyzer."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from forkscout.analysis.repository_analyzer import (
    RepositoryAnalysisError,
    RepositoryAnalyzer,
)
from forkscout.github.client import GitHubAPIError, GitHubClient
from forkscout.models.analysis import Feature, FeatureCategory, ForkAnalysis, ForkMetrics
from forkscout.models.github import Commit, Fork, Repository, User


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    client = Mock(spec=GitHubClient)

    # Make all methods async
    client.get_fork_comparison = AsyncMock()
    client.get_repository_contributors = AsyncMock()

    return client


@pytest.fixture
def sample_repository():
    """Create a sample repository."""
    return Repository(
        id=123,
        owner="test-owner",
        name="test-repo",
        full_name="test-owner/test-repo",
        url="https://api.github.com/repos/test-owner/test-repo",
        html_url="https://github.com/test-owner/test-repo",
        clone_url="https://github.com/test-owner/test-repo.git",
        default_branch="main",
        stars=100,
        forks_count=50,
        created_at=datetime.utcnow() - timedelta(days=365),
        updated_at=datetime.utcnow() - timedelta(days=1),
        pushed_at=datetime.utcnow() - timedelta(days=1),
    )


@pytest.fixture
def sample_fork_repository():
    """Create a sample fork repository."""
    return Repository(
        id=456,
        owner="fork-owner",
        name="test-repo",
        full_name="fork-owner/test-repo",
        url="https://api.github.com/repos/fork-owner/test-repo",
        html_url="https://github.com/fork-owner/test-repo",
        clone_url="https://github.com/fork-owner/test-repo.git",
        default_branch="main",
        stars=5,
        forks_count=1,
        is_fork=True,
        created_at=datetime.utcnow() - timedelta(days=30),
        updated_at=datetime.utcnow() - timedelta(days=5),
        pushed_at=datetime.utcnow() - timedelta(days=5),
    )


@pytest.fixture
def sample_user():
    """Create a sample user."""
    return User(
        id=789,
        login="fork-owner",
        name="Fork Owner",
        html_url="https://github.com/fork-owner",
    )


@pytest.fixture
def sample_fork(sample_fork_repository, sample_repository, sample_user):
    """Create a sample fork."""
    return Fork(
        repository=sample_fork_repository,
        parent=sample_repository,
        owner=sample_user,
        commits_ahead=5,
        commits_behind=2,
        last_activity=datetime.utcnow() - timedelta(days=5),
    )


@pytest.fixture
def sample_commits():
    """Create sample commits for testing."""
    base_date = datetime.utcnow() - timedelta(days=10)
    author = User(login="author", html_url="https://github.com/author")

    return [
        Commit(
            sha="a" * 40,
            message="feat: add new authentication system",
            author=author,
            date=base_date,
            files_changed=["src/auth.py", "tests/test_auth.py"],
            additions=150,
            deletions=20,
        ),
        Commit(
            sha="b" * 40,
            message="fix: resolve login bug in auth system",
            author=author,
            date=base_date + timedelta(hours=2),
            files_changed=["src/auth.py"],
            additions=10,
            deletions=5,
        ),
        Commit(
            sha="c" * 40,
            message="docs: update authentication documentation",
            author=author,
            date=base_date + timedelta(days=1),
            files_changed=["README.md", "docs/auth.md"],
            additions=50,
            deletions=10,
        ),
        Commit(
            sha="d" * 40,
            message="test: add comprehensive auth tests",
            author=author,
            date=base_date + timedelta(days=2),
            files_changed=["tests/test_auth.py", "tests/test_integration.py"],
            additions=200,
            deletions=0,
        ),
        Commit(
            sha="e" * 40,
            message="perf: optimize database queries in auth",
            author=author,
            date=base_date + timedelta(days=3),
            files_changed=["src/auth.py", "src/database.py"],
            additions=30,
            deletions=40,
        ),
    ]


@pytest.fixture
def repository_analyzer(mock_github_client):
    """Create a repository analyzer with mocked client."""
    return RepositoryAnalyzer(
        github_client=mock_github_client,
        min_feature_commits=1,
        max_commits_per_feature=10,
    )


class TestRepositoryAnalyzer:
    """Test cases for RepositoryAnalyzer."""

    def test_init(self, mock_github_client):
        """Test analyzer initialization."""
        analyzer = RepositoryAnalyzer(
            github_client=mock_github_client,
            min_feature_commits=2,
            max_commits_per_feature=5,
        )

        assert analyzer.github_client == mock_github_client
        assert analyzer.min_feature_commits == 2
        assert analyzer.max_commits_per_feature == 5

    @pytest.mark.asyncio
    async def test_analyze_fork_success(
        self,
        repository_analyzer,
        mock_github_client,
        sample_fork,
        sample_repository,
        sample_commits,
        sample_user,
    ):
        """Test successful fork analysis."""
        # Setup mocks
        comparison_data = {
            "commits": [
                {
                    "sha": commit.sha,
                    "commit": {
                        "message": commit.message,
                        "author": {"date": commit.date.isoformat() + "Z"},
                        "committer": {"date": commit.date.isoformat() + "Z"},
                    },
                    "author": {"login": "author", "html_url": "https://github.com/author"},
                    "committer": {"login": "author", "html_url": "https://github.com/author"},
                    "stats": {"additions": commit.additions, "deletions": commit.deletions},
                    "files": [{"filename": f} for f in commit.files_changed],
                    "parents": [{"sha": "parent_sha"}],
                }
                for commit in sample_commits
            ]
        }

        mock_github_client.get_fork_comparison.return_value = comparison_data
        mock_github_client.get_repository_contributors.return_value = [sample_user]

        # Test
        result = await repository_analyzer.analyze_fork(sample_fork, sample_repository)

        # Assertions
        assert isinstance(result, ForkAnalysis)
        assert result.fork == sample_fork
        assert len(result.features) > 0
        assert isinstance(result.metrics, ForkMetrics)
        assert result.analysis_date is not None

    @pytest.mark.asyncio
    async def test_analyze_fork_no_commits(
        self,
        repository_analyzer,
        mock_github_client,
        sample_fork,
        sample_repository,
        sample_user,
    ):
        """Test fork analysis with no unique commits."""
        # Setup mocks - no commits
        mock_github_client.get_fork_comparison.return_value = {"commits": []}
        mock_github_client.get_repository_contributors.return_value = [sample_user]

        # Test
        result = await repository_analyzer.analyze_fork(sample_fork, sample_repository)

        # Assertions
        assert isinstance(result, ForkAnalysis)
        assert result.fork == sample_fork
        assert len(result.features) == 0
        assert isinstance(result.metrics, ForkMetrics)

    @pytest.mark.asyncio
    async def test_analyze_fork_api_error(
        self,
        repository_analyzer,
        mock_github_client,
        sample_fork,
        sample_repository,
    ):
        """Test fork analysis with API error."""
        mock_github_client.get_fork_comparison.side_effect = GitHubAPIError("API Error")

        with pytest.raises(RepositoryAnalysisError, match="Failed to analyze fork"):
            await repository_analyzer.analyze_fork(sample_fork, sample_repository)

    @pytest.mark.asyncio
    async def test_extract_features(self, repository_analyzer, sample_commits, sample_fork):
        """Test feature extraction from commits."""
        result = await repository_analyzer.extract_features(sample_commits, sample_fork)

        # Should extract multiple features based on different categories
        assert len(result) > 0

        # Check that features have proper structure
        for feature in result:
            assert isinstance(feature, Feature)
            assert feature.id
            assert feature.title
            assert feature.description
            assert isinstance(feature.category, FeatureCategory)
            assert len(feature.commits) > 0
            assert feature.source_fork == sample_fork

    @pytest.mark.asyncio
    async def test_extract_features_min_commits_filter(self, mock_github_client, sample_commits, sample_fork):
        """Test that features below minimum commit threshold are filtered out."""
        # Create analyzer with higher minimum
        analyzer = RepositoryAnalyzer(
            github_client=mock_github_client,
            min_feature_commits=3,  # Higher threshold
            max_commits_per_feature=10,
        )

        result = await analyzer.extract_features(sample_commits, sample_fork)

        # Should have fewer features due to higher threshold
        for feature in result:
            assert len(feature.commits) >= 3

    @pytest.mark.asyncio
    async def test_categorize_changes(self, repository_analyzer, sample_commits):
        """Test commit categorization."""
        result = await repository_analyzer.categorize_changes(sample_commits)

        # Should categorize commits by type
        assert isinstance(result, dict)

        # Check that we have different categories
        categories_found = set(result.keys())
        expected_categories = {
            FeatureCategory.NEW_FEATURE.value,
            FeatureCategory.BUG_FIX.value,
            FeatureCategory.DOCUMENTATION.value,
            FeatureCategory.TEST.value,
            FeatureCategory.PERFORMANCE.value,
        }

        # Should find at least some of the expected categories
        assert len(categories_found.intersection(expected_categories)) > 0

    def test_categorize_commit_bug_fix(self, repository_analyzer):
        """Test bug fix commit categorization."""
        commit = Commit(
            sha="a" * 40,
            message="fix: resolve critical authentication bug",
            author=User(login="author", html_url="https://github.com/author"),
            date=datetime.utcnow(),
            files_changed=["src/auth.py"],
            additions=10,
            deletions=5,
        )

        category = repository_analyzer._categorize_commit(commit)
        assert category == FeatureCategory.BUG_FIX

    def test_categorize_commit_new_feature(self, repository_analyzer):
        """Test new feature commit categorization."""
        commit = Commit(
            sha="a" * 40,
            message="feat: implement OAuth2 authentication",
            author=User(login="author", html_url="https://github.com/author"),
            date=datetime.utcnow(),
            files_changed=["src/oauth.py"],
            additions=200,
            deletions=0,
        )

        category = repository_analyzer._categorize_commit(commit)
        assert category == FeatureCategory.NEW_FEATURE

    def test_categorize_commit_documentation(self, repository_analyzer):
        """Test documentation commit categorization."""
        commit = Commit(
            sha="a" * 40,
            message="docs: update API documentation",
            author=User(login="author", html_url="https://github.com/author"),
            date=datetime.utcnow(),
            files_changed=["README.md", "docs/api.md"],
            additions=50,
            deletions=10,
        )

        category = repository_analyzer._categorize_commit(commit)
        assert category == FeatureCategory.DOCUMENTATION

    def test_categorize_commit_test(self, repository_analyzer):
        """Test test commit categorization."""
        commit = Commit(
            sha="a" * 40,
            message="test: add unit tests for auth module",
            author=User(login="author", html_url="https://github.com/author"),
            date=datetime.utcnow(),
            files_changed=["tests/test_auth.py"],
            additions=100,
            deletions=0,
        )

        category = repository_analyzer._categorize_commit(commit)
        assert category == FeatureCategory.TEST

    def test_categorize_commit_performance(self, repository_analyzer):
        """Test performance commit categorization."""
        commit = Commit(
            sha="a" * 40,
            message="perf: optimize database queries for better performance",
            author=User(login="author", html_url="https://github.com/author"),
            date=datetime.utcnow(),
            files_changed=["src/database.py"],
            additions=30,
            deletions=40,
        )

        category = repository_analyzer._categorize_commit(commit)
        assert category == FeatureCategory.PERFORMANCE

    def test_categorize_commit_refactor(self, repository_analyzer):
        """Test refactor commit categorization."""
        commit = Commit(
            sha="a" * 40,
            message="refactor: clean up authentication code structure",
            author=User(login="author", html_url="https://github.com/author"),
            date=datetime.utcnow(),
            files_changed=["src/auth.py"],
            additions=50,
            deletions=60,
        )

        category = repository_analyzer._categorize_commit(commit)
        assert category == FeatureCategory.REFACTOR

    def test_categorize_commit_other(self, repository_analyzer):
        """Test other commit categorization."""
        commit = Commit(
            sha="a" * 40,
            message="update version number",
            author=User(login="author", html_url="https://github.com/author"),
            date=datetime.utcnow(),
            files_changed=["version.txt"],
            additions=1,
            deletions=1,
        )

        category = repository_analyzer._categorize_commit(commit)
        assert category == FeatureCategory.OTHER

    def test_generate_feature_key(self, repository_analyzer):
        """Test feature key generation."""
        commit = Commit(
            sha="a" * 40,
            message="feat: implement user authentication system",
            author=User(login="author", html_url="https://github.com/author"),
            date=datetime.utcnow(),
            files_changed=["src/auth.py", "src/user.py"],
            additions=100,
            deletions=0,
        )

        key = repository_analyzer._generate_feature_key(commit)

        # Should contain meaningful words from the commit message
        assert isinstance(key, str)
        assert len(key) > 0
        # Should include words like "implement", "user", "authentication"
        key_lower = key.lower()
        assert any(word in key_lower for word in ["implement", "user", "authentication", "auth"])

    def test_should_separate_commits_time_difference(self, repository_analyzer):
        """Test commit separation based on time difference."""
        author = User(login="author", html_url="https://github.com/author")

        commit1 = Commit(
            sha="a" * 40,
            message="feat: add feature A",
            author=author,
            date=datetime.utcnow() - timedelta(days=10),
            files_changed=["src/feature_a.py"],
            additions=50,
            deletions=0,
        )

        commit2 = Commit(
            sha="b" * 40,
            message="feat: add feature B",
            author=author,
            date=datetime.utcnow(),  # 10 days later
            files_changed=["src/feature_b.py"],
            additions=50,
            deletions=0,
        )

        should_separate = repository_analyzer._should_separate_commits(commit1, commit2)
        assert should_separate is True

    def test_should_separate_commits_file_overlap(self, repository_analyzer):
        """Test commit separation based on file overlap."""
        author = User(login="author", html_url="https://github.com/author")
        base_date = datetime.utcnow()

        commit1 = Commit(
            sha="a" * 40,
            message="feat: add auth module",
            author=author,
            date=base_date,
            files_changed=["src/auth.py", "src/user.py"],
            additions=50,
            deletions=0,
        )

        # Commit with completely different files
        commit2 = Commit(
            sha="b" * 40,
            message="feat: add database module",
            author=author,
            date=base_date + timedelta(hours=1),
            files_changed=["src/database.py", "src/models.py"],
            additions=50,
            deletions=0,
        )

        should_separate = repository_analyzer._should_separate_commits(commit1, commit2)
        assert should_separate is True

    def test_should_not_separate_commits_related(self, repository_analyzer):
        """Test that related commits are not separated."""
        author = User(login="author", html_url="https://github.com/author")
        base_date = datetime.utcnow()

        commit1 = Commit(
            sha="a" * 40,
            message="feat: add auth module",
            author=author,
            date=base_date,
            files_changed=["src/auth.py", "tests/test_auth.py"],
            additions=50,
            deletions=0,
        )

        # Related commit with overlapping files
        commit2 = Commit(
            sha="b" * 40,
            message="fix: fix auth bug",
            author=author,
            date=base_date + timedelta(hours=1),
            files_changed=["src/auth.py"],  # Same file
            additions=10,
            deletions=5,
        )

        should_separate = repository_analyzer._should_separate_commits(commit1, commit2)
        assert should_separate is False

    def test_generate_feature_title_single_commit(self, repository_analyzer):
        """Test feature title generation for single commit."""
        commit = Commit(
            sha="a" * 40,
            message="feat: implement OAuth2 authentication system",
            author=User(login="author", html_url="https://github.com/author"),
            date=datetime.utcnow(),
            files_changed=["src/oauth.py"],
            additions=200,
            deletions=0,
        )

        title = repository_analyzer._generate_feature_title([commit], FeatureCategory.NEW_FEATURE)

        # Should clean up the commit message
        assert "OAuth2 authentication system" in title
        assert "feat:" not in title

    def test_generate_feature_title_multiple_commits(self, repository_analyzer):
        """Test feature title generation for multiple commits."""
        author = User(login="author", html_url="https://github.com/author")
        commits = [
            Commit(
                sha="a" * 40,
                message="feat: implement OAuth2 authentication",
                author=author,
                date=datetime.utcnow(),
                files_changed=["src/oauth.py"],
                additions=200,
                deletions=0,
            ),
            Commit(
                sha="b" * 40,
                message="fix: resolve OAuth2 token refresh issue",
                author=author,
                date=datetime.utcnow() + timedelta(hours=1),
                files_changed=["src/oauth.py"],
                additions=20,
                deletions=10,
            ),
        ]

        title = repository_analyzer._generate_feature_title(commits, FeatureCategory.NEW_FEATURE)

        # Should indicate multiple commits
        assert "related commits" in title or "+" in title

    def test_generate_feature_description(self, repository_analyzer):
        """Test feature description generation."""
        author = User(login="author", html_url="https://github.com/author")
        commits = [
            Commit(
                sha="a" * 40,
                message="feat: implement OAuth2 authentication system",
                author=author,
                date=datetime.utcnow(),
                files_changed=["src/oauth.py", "src/auth.py"],
                additions=200,
                deletions=10,
            ),
        ]

        description = repository_analyzer._generate_feature_description(commits, FeatureCategory.NEW_FEATURE)

        # Should contain meaningful information
        assert len(description) > 0
        assert "OAuth2" in description or "authentication" in description
        assert "200 lines added" in description
        assert "10 lines removed" in description
        assert "2 files modified" in description

    def test_create_feature_from_commits(self, repository_analyzer, sample_fork):
        """Test feature creation from commits."""
        author = User(login="author", html_url="https://github.com/author")
        commits = [
            Commit(
                sha="a" * 40,
                message="feat: implement user authentication",
                author=author,
                date=datetime.utcnow(),
                files_changed=["src/auth.py", "tests/test_auth.py"],
                additions=150,
                deletions=20,
            ),
        ]

        feature = repository_analyzer._create_feature_from_commits(
            commits, FeatureCategory.NEW_FEATURE, sample_fork, 1
        )

        # Assertions
        assert isinstance(feature, Feature)
        assert feature.id
        assert feature.title
        assert feature.description
        assert feature.category == FeatureCategory.NEW_FEATURE
        assert feature.commits == commits
        assert set(feature.files_affected) == {"src/auth.py", "tests/test_auth.py"}
        assert feature.source_fork == sample_fork

    def test_group_commits_by_feature(self, repository_analyzer, sample_commits):
        """Test grouping commits by feature."""
        groups = repository_analyzer._group_commits_by_feature(sample_commits)

        # Should create multiple groups
        assert len(groups) > 0

        # Each group should have commits and category
        for group_key, (commits, category) in groups.items():
            assert isinstance(group_key, str)
            assert len(commits) > 0
            assert isinstance(category, FeatureCategory)

            # Commits should be sorted chronologically
            for i in range(1, len(commits)):
                assert commits[i-1].date <= commits[i].date

    def test_group_commits_respects_max_commits_per_feature(self, mock_github_client):
        """Test that commit grouping respects max commits per feature."""
        analyzer = RepositoryAnalyzer(
            github_client=mock_github_client,
            min_feature_commits=1,
            max_commits_per_feature=2,  # Small limit
        )

        # Create many similar commits
        author = User(login="author", html_url="https://github.com/author")
        base_date = datetime.utcnow()
        commits = []

        for i in range(5):
            commits.append(Commit(
                sha=f"{i:040d}",
                message=f"feat: add feature part {i}",
                author=author,
                date=base_date + timedelta(hours=i),
                files_changed=["src/feature.py"],
                additions=10,
                deletions=0,
            ))

        groups = analyzer._group_commits_by_feature(commits)

        # Should create multiple groups due to size limit
        total_commits_in_groups = sum(len(group_commits) for group_commits, _ in groups.values())
        assert total_commits_in_groups == len(commits)

        # Each group should respect the limit
        for group_commits, _ in groups.values():
            assert len(group_commits) <= 2


class TestRepositoryAnalyzerEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_get_unique_commits_api_error(
        self,
        repository_analyzer,
        mock_github_client,
        sample_fork,
        sample_repository,
    ):
        """Test getting unique commits with API error."""
        mock_github_client.get_fork_comparison.side_effect = GitHubAPIError("Comparison failed")

        # Test - should raise the API error
        with pytest.raises(GitHubAPIError, match="Comparison failed"):
            await repository_analyzer._get_unique_commits(sample_fork, sample_repository)

    @pytest.mark.asyncio
    async def test_get_fork_metrics_api_error(
        self,
        repository_analyzer,
        mock_github_client,
        sample_fork,
    ):
        """Test getting fork metrics with API error."""
        mock_github_client.get_repository_contributors.side_effect = GitHubAPIError("Contributors failed")

        # Test
        result = await repository_analyzer._get_fork_metrics(sample_fork)

        # Should return basic metrics even with error
        assert isinstance(result, ForkMetrics)
        assert result.stars == sample_fork.repository.stars
        assert result.contributors == 0  # Default when API fails

    def test_generate_feature_key_no_meaningful_words(self, repository_analyzer):
        """Test feature key generation with no meaningful words."""
        commit = Commit(
            sha="a" * 40,
            message=".",  # No meaningful content
            author=User(login="author", html_url="https://github.com/author"),
            date=datetime.utcnow(),
            files_changed=[],
            additions=1,
            deletions=0,
        )

        key = repository_analyzer._generate_feature_key(commit)

        # Should fall back to using SHA
        assert "feature_" in key
        assert commit.sha[:8] in key

    def test_generate_feature_title_empty_commits(self, repository_analyzer):
        """Test feature title generation with empty commits list."""
        title = repository_analyzer._generate_feature_title([], FeatureCategory.NEW_FEATURE)

        assert "Unknown New Feature" in title

    def test_generate_feature_description_empty_commits(self, repository_analyzer):
        """Test feature description generation with empty commits list."""
        description = repository_analyzer._generate_feature_description([], FeatureCategory.BUG_FIX)

        assert "bug fix" in description.lower()
        assert "no detailed information" in description.lower()

    @pytest.mark.asyncio
    async def test_extract_features_empty_commits(self, repository_analyzer, sample_fork):
        """Test feature extraction with empty commits list."""
        result = await repository_analyzer.extract_features([], sample_fork)

        assert result == []

    def test_should_separate_commits_none_previous(self, repository_analyzer):
        """Test commit separation with None previous commit."""
        commit = Commit(
            sha="a" * 40,
            message="feat: add feature",
            author=User(login="author", html_url="https://github.com/author"),
            date=datetime.utcnow(),
            files_changed=["src/feature.py"],
            additions=50,
            deletions=0,
        )

        should_separate = repository_analyzer._should_separate_commits(None, commit)
        assert should_separate is False
