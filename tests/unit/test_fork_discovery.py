"""Tests for fork discovery service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from forkscout.analysis.fork_data_collection_engine import ForkDataCollectionEngine
from forkscout.analysis.fork_discovery import ForkDiscoveryError, ForkDiscoveryService
from forkscout.github.client import GitHubAPIError, GitHubClient, GitHubNotFoundError
from forkscout.github.fork_list_processor import ForkListProcessor
from forkscout.models.analysis import ForkMetrics
from forkscout.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualificationStats,
    QualifiedForksResult,
)
from forkscout.models.github import Commit, Fork, Repository, User


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    client = Mock(spec=GitHubClient)

    # Make all methods async
    client.get_repository = AsyncMock()
    client.get_all_repository_forks = AsyncMock()
    client.get_commits_ahead_behind = AsyncMock()
    client.get_fork_comparison = AsyncMock()
    client.get_user = AsyncMock()
    client.get_repository_contributors = AsyncMock()
    client.get = AsyncMock()  # Add the get method for ForkListProcessor

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
def sample_commit():
    """Create a sample commit."""
    return Commit(
        sha="a" * 40,
        message="feat: add new feature",
        author=User(login="author", html_url="https://github.com/author"),
        date=datetime.utcnow() - timedelta(days=1),
        files_changed=["src/main.py", "tests/test_main.py"],
        additions=50,
        deletions=10,
    )


@pytest.fixture
def mock_data_collection_engine():
    """Create a mock fork data collection engine."""
    engine = Mock(spec=ForkDataCollectionEngine)
    engine.collect_fork_data_from_list = Mock()
    engine.exclude_no_commits_ahead = Mock()
    engine.create_qualification_result = Mock()
    return engine


@pytest.fixture
def mock_fork_list_processor():
    """Create a mock fork list processor."""
    processor = Mock(spec=ForkListProcessor)
    processor.get_all_forks_list_data = AsyncMock()
    return processor


@pytest.fixture
def sample_collected_fork_data():
    """Create sample collected fork data."""
    metrics = ForkQualificationMetrics(
        id=456,
        owner="fork-owner",
        name="test-repo",
        full_name="fork-owner/test-repo",
        html_url="https://github.com/fork-owner/test-repo",
        clone_url="https://github.com/fork-owner/test-repo.git",
        default_branch="main",
        stargazers_count=5,
        forks_count=1,
        size=100,
        language="Python",
        topics=["test"],
        open_issues_count=2,
        watchers_count=5,
        archived=False,
        disabled=False,
        created_at=datetime.utcnow() - timedelta(days=30),
        updated_at=datetime.utcnow() - timedelta(days=5),
        pushed_at=datetime.utcnow() - timedelta(days=5),
        days_since_creation=30,
        days_since_last_update=5,
        days_since_last_push=5,
        activity_ratio=0.8,
        commits_ahead_status="Has commits",
        can_skip_analysis=False,
    )
    return CollectedForkData(metrics=metrics)


@pytest.fixture
def sample_qualified_forks_result(sample_collected_fork_data):
    """Create sample qualified forks result."""
    stats = QualificationStats(
        total_forks_discovered=2,
        forks_with_no_commits=1,
        forks_with_commits=1,
        archived_forks=0,
        disabled_forks=0,
        api_calls_made=10,
        api_calls_saved=3,
        processing_time_seconds=1.5,
    )

    return QualifiedForksResult(
        repository_owner="test-owner",
        repository_name="test-repo",
        repository_url="https://github.com/test-owner/test-repo",
        collected_forks=[sample_collected_fork_data],
        stats=stats,
    )


@pytest.fixture
def fork_discovery_service(mock_github_client):
    """Create a fork discovery service with mocked client."""
    return ForkDiscoveryService(
        github_client=mock_github_client,
        min_activity_days=365,
        min_commits_ahead=1,
        max_forks_to_analyze=100,
    )


@pytest.fixture
def fork_discovery_service_with_mocks(mock_github_client, mock_data_collection_engine):
    """Create a fork discovery service with mocked dependencies."""
    service = ForkDiscoveryService(
        github_client=mock_github_client,
        data_collection_engine=mock_data_collection_engine,
        min_activity_days=365,
        min_commits_ahead=1,
        max_forks_to_analyze=100,
    )
    # Mock the fork list processor
    service.fork_list_processor = Mock(spec=ForkListProcessor)
    service.fork_list_processor.get_all_forks_list_data = AsyncMock()
    return service


class TestForkDiscoveryService:
    """Test cases for ForkDiscoveryService."""

    def test_init(self, mock_github_client):
        """Test service initialization."""
        service = ForkDiscoveryService(
            github_client=mock_github_client,
            min_activity_days=180,
            min_commits_ahead=2,
            max_forks_to_analyze=50,
        )

        assert service.github_client == mock_github_client
        assert service.min_activity_days == 180
        assert service.min_commits_ahead == 2
        assert service.max_forks_to_analyze == 50

    @pytest.mark.asyncio
    async def test_discover_forks_success(
        self,
        fork_discovery_service,
        mock_github_client,
        sample_repository,
        sample_fork_repository,
        sample_user,
    ):
        """Test successful fork discovery."""
        # Setup mocks for new data collection method
        mock_github_client.get_repository.return_value = sample_repository

        # Mock the get method for ForkListProcessor
        fork_data = {
            "id": sample_fork_repository.id,
            "name": sample_fork_repository.name,
            "full_name": sample_fork_repository.full_name,
            "owner": {"login": sample_fork_repository.owner},
            "html_url": sample_fork_repository.html_url,
            "stargazers_count": sample_fork_repository.stars,
            "forks_count": sample_fork_repository.forks_count,
            "watchers_count": sample_fork_repository.stars,
            "size": sample_fork_repository.size or 100,
            "language": sample_fork_repository.language,
            "topics": sample_fork_repository.topics or [],
            "open_issues_count": 0,
            "created_at": sample_fork_repository.created_at.isoformat() + "Z",
            "updated_at": sample_fork_repository.updated_at.isoformat() + "Z",
            "pushed_at": sample_fork_repository.pushed_at.isoformat() + "Z",
            "archived": False,
            "disabled": False,
            "fork": True,
            "license": None,
            "description": None,
            "homepage": None,
            "default_branch": "main",
        }
        mock_github_client.get.return_value = [fork_data]

        # Setup mocks for fork analysis
        mock_github_client.get_commits_ahead_behind.return_value = {
            "ahead_by": 5,
            "behind_by": 2,
            "total_commits": 7,
        }
        mock_github_client.get_user.return_value = sample_user

        # Test
        result = await fork_discovery_service.discover_forks(
            "https://github.com/test-owner/test-repo"
        )

        # Assertions
        assert len(result) == 1
        fork = result[0]
        assert isinstance(fork, Fork)
        assert fork.repository.full_name == "fork-owner/test-repo"
        assert fork.parent.full_name == "test-owner/test-repo"
        assert fork.commits_ahead == 5
        assert fork.commits_behind == 2

        # Verify API calls
        mock_github_client.get_repository.assert_called_once_with(
            "test-owner", "test-repo", disable_cache=False
        )

    @pytest.mark.asyncio
    async def test_discover_forks_repository_not_found(
        self, fork_discovery_service, mock_github_client
    ):
        """Test fork discovery when repository is not found."""
        mock_github_client.get_repository.side_effect = GitHubNotFoundError("Not found")

        with pytest.raises(ForkDiscoveryError, match="Repository not found"):
            await fork_discovery_service.discover_forks(
                "https://github.com/nonexistent/repo"
            )

    @pytest.mark.asyncio
    async def test_discover_forks_github_api_error(
        self, fork_discovery_service, mock_github_client
    ):
        """Test fork discovery with GitHub API error."""
        mock_github_client.get_repository.side_effect = GitHubAPIError("API Error")

        with pytest.raises(ForkDiscoveryError, match="GitHub API error"):
            await fork_discovery_service.discover_forks(
                "https://github.com/test-owner/test-repo"
            )

    def test_parse_repository_url_https(self, fork_discovery_service):
        """Test parsing HTTPS GitHub URL."""
        owner, repo = fork_discovery_service._parse_repository_url(
            "https://github.com/owner/repo"
        )
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repository_url_https_with_git(self, fork_discovery_service):
        """Test parsing HTTPS GitHub URL with .git suffix."""
        owner, repo = fork_discovery_service._parse_repository_url(
            "https://github.com/owner/repo.git"
        )
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repository_url_ssh(self, fork_discovery_service):
        """Test parsing SSH GitHub URL."""
        owner, repo = fork_discovery_service._parse_repository_url(
            "git@github.com:owner/repo.git"
        )
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repository_url_owner_repo_format(self, fork_discovery_service):
        """Test parsing owner/repo format."""
        owner, repo = fork_discovery_service._parse_repository_url("owner/repo")
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repository_url_api_url(self, fork_discovery_service):
        """Test parsing GitHub API URL."""
        owner, repo = fork_discovery_service._parse_repository_url(
            "https://api.github.com/repos/maliayas/github-network-ninja"
        )
        assert owner == "maliayas"
        assert repo == "github-network-ninja"

    def test_parse_repository_url_invalid(self, fork_discovery_service):
        """Test parsing invalid URL."""
        with pytest.raises(ForkDiscoveryError, match="Invalid repository URL format"):
            fork_discovery_service._parse_repository_url("invalid-url")

    @pytest.mark.asyncio
    async def test_filter_active_forks(self, fork_discovery_service, sample_fork):
        """Test filtering active forks with new two-stage approach."""
        # Create forks with different characteristics
        active_fork = sample_fork
        active_fork.commits_ahead = 5
        active_fork.last_activity = datetime.utcnow() - timedelta(days=30)

        # Fork with old activity but has commits ahead - should still be included
        old_but_active_fork = Fork(
            repository=sample_fork.repository,
            parent=sample_fork.parent,
            owner=sample_fork.owner,
            commits_ahead=3,
            commits_behind=1,
            last_activity=datetime.utcnow() - timedelta(days=400),  # Old activity
        )

        # Fork with no commits ahead - should be filtered out
        no_commits_fork = Fork(
            repository=sample_fork.repository,
            parent=sample_fork.parent,
            owner=sample_fork.owner,
            commits_ahead=0,  # No unique commits
            commits_behind=5,
            last_activity=datetime.utcnow() - timedelta(days=10),
        )

        forks = [active_fork, old_but_active_fork, no_commits_fork]

        # Test
        result = await fork_discovery_service.filter_active_forks(forks)

        # Assertions - both forks with commits ahead should be included regardless of age
        assert len(result) == 2
        assert active_fork in result
        assert old_but_active_fork in result
        assert all(fork.is_active is True for fork in result)
        assert all(fork.divergence_score > 0 for fork in result)

    def test_is_fork_active_recent_activity(self, fork_discovery_service):
        """Test fork activity check with recent activity."""
        fork = Mock()
        fork.last_activity = datetime.utcnow() - timedelta(days=30)
        cutoff_date = datetime.utcnow() - timedelta(days=365)

        result = fork_discovery_service._is_fork_active(fork, cutoff_date)
        assert result is True

    def test_is_fork_active_old_activity(self, fork_discovery_service):
        """Test fork activity check with old activity."""
        fork = Mock()
        fork.last_activity = datetime.utcnow() - timedelta(days=400)
        cutoff_date = datetime.utcnow() - timedelta(days=365)

        result = fork_discovery_service._is_fork_active(fork, cutoff_date)
        assert result is False

    def test_is_fork_active_no_activity(self, fork_discovery_service):
        """Test fork activity check with no activity."""
        fork = Mock()
        fork.last_activity = None
        cutoff_date = datetime.utcnow() - timedelta(days=365)

        result = fork_discovery_service._is_fork_active(fork, cutoff_date)
        assert result is False

    def test_calculate_divergence_score(self, fork_discovery_service):
        """Test divergence score calculation."""
        fork = Mock()
        fork.commits_ahead = 10
        fork.commits_behind = 5
        fork.calculate_activity_score.return_value = 0.8

        score = fork_discovery_service._calculate_divergence_score(fork)

        # Expected: (10 / 15) * 0.8 = 0.533...
        assert 0.5 < score < 0.6

    def test_calculate_divergence_score_no_commits(self, fork_discovery_service):
        """Test divergence score with no commits."""
        fork = Mock()
        fork.commits_ahead = 0
        fork.commits_behind = 0

        score = fork_discovery_service._calculate_divergence_score(fork)
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_get_unique_commits_success(
        self,
        fork_discovery_service,
        mock_github_client,
        sample_fork,
        sample_repository,
        sample_commit,
    ):
        """Test getting unique commits from a fork."""
        # Setup mock comparison data
        comparison_data = {
            "commits": [
                {
                    "sha": sample_commit.sha,
                    "commit": {
                        "message": sample_commit.message,
                        "author": {"date": sample_commit.date.isoformat() + "Z"},
                        "committer": {"date": sample_commit.date.isoformat() + "Z"},
                    },
                    "author": {
                        "login": "author",
                        "html_url": "https://github.com/author",
                    },
                    "committer": {
                        "login": "author",
                        "html_url": "https://github.com/author",
                    },
                    "stats": {"additions": 50, "deletions": 10},
                    "files": [{"filename": "src/main.py"}],
                    "parents": [{"sha": "b" * 40}],
                }
            ]
        }

        mock_github_client.get_fork_comparison.return_value = comparison_data

        # Test
        result = await fork_discovery_service.get_unique_commits(
            sample_fork, sample_repository
        )

        # Assertions
        assert len(result) == 1
        commit = result[0]
        assert isinstance(commit, Commit)
        assert commit.sha == sample_commit.sha
        assert commit.message == sample_commit.message

    @pytest.mark.asyncio
    async def test_get_unique_commits_filters_merge_commits(
        self,
        fork_discovery_service,
        mock_github_client,
        sample_fork,
        sample_repository,
    ):
        """Test that merge commits are filtered out."""
        # Setup mock comparison data with merge commit
        comparison_data = {
            "commits": [
                {
                    "sha": "a" * 40,
                    "commit": {
                        "message": "Merge branch 'feature'",
                        "author": {"date": datetime.utcnow().isoformat() + "Z"},
                        "committer": {"date": datetime.utcnow().isoformat() + "Z"},
                    },
                    "author": {
                        "login": "author",
                        "html_url": "https://github.com/author",
                    },
                    "committer": {
                        "login": "author",
                        "html_url": "https://github.com/author",
                    },
                    "stats": {"additions": 0, "deletions": 0},
                    "files": [],
                    "parents": [
                        {"sha": "b" * 40},
                        {"sha": "c" * 40},
                    ],  # Multiple parents = merge
                }
            ]
        }

        mock_github_client.get_fork_comparison.return_value = comparison_data

        # Test
        result = await fork_discovery_service.get_unique_commits(
            sample_fork, sample_repository
        )

        # Assertions - merge commit should be filtered out
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_unique_commits_filters_insignificant_commits(
        self,
        fork_discovery_service,
        mock_github_client,
        sample_fork,
        sample_repository,
    ):
        """Test that insignificant commits are filtered out."""
        # Setup mock comparison data with small commit
        comparison_data = {
            "commits": [
                {
                    "sha": "a" * 40,
                    "commit": {
                        "message": "Fix typo",
                        "author": {"date": datetime.utcnow().isoformat() + "Z"},
                        "committer": {"date": datetime.utcnow().isoformat() + "Z"},
                    },
                    "author": {
                        "login": "author",
                        "html_url": "https://github.com/author",
                    },
                    "committer": {
                        "login": "author",
                        "html_url": "https://github.com/author",
                    },
                    "stats": {"additions": 1, "deletions": 1},  # Very small change
                    "files": [{"filename": "README.md"}],
                    "parents": [{"sha": "b" * 40}],
                }
            ]
        }

        mock_github_client.get_fork_comparison.return_value = comparison_data

        # Test
        result = await fork_discovery_service.get_unique_commits(
            sample_fork, sample_repository
        )

        # Assertions - insignificant commit should be filtered out
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_fork_metrics_success(
        self,
        fork_discovery_service,
        mock_github_client,
        sample_fork,
        sample_user,
    ):
        """Test getting fork metrics."""
        # Setup mock contributors
        contributors = [sample_user, sample_user]  # 2 contributors
        mock_github_client.get_repository_contributors.return_value = contributors

        # Test
        result = await fork_discovery_service.get_fork_metrics(sample_fork)

        # Assertions
        assert isinstance(result, ForkMetrics)
        assert result.stars == sample_fork.repository.stars
        assert result.forks == sample_fork.repository.forks_count
        assert result.contributors == 2
        assert result.last_activity == sample_fork.last_activity
        assert result.commit_frequency >= 0

    @pytest.mark.asyncio
    async def test_get_fork_metrics_api_error(
        self,
        fork_discovery_service,
        mock_github_client,
        sample_fork,
    ):
        """Test getting fork metrics with API error."""
        # Setup mock to raise error
        mock_github_client.get_repository_contributors.side_effect = GitHubAPIError(
            "API Error"
        )

        # Test
        result = await fork_discovery_service.get_fork_metrics(sample_fork)

        # Assertions - should return basic metrics even with error
        assert isinstance(result, ForkMetrics)
        assert result.stars == sample_fork.repository.stars
        assert result.forks == sample_fork.repository.forks_count
        assert result.contributors == 0  # Default when API fails
        assert result.commit_frequency == 0.0

    @pytest.mark.asyncio
    async def test_discover_and_filter_forks_integration(
        self,
        fork_discovery_service,
        mock_github_client,
        sample_repository,
        sample_fork_repository,
        sample_user,
    ):
        """Test the integrated discover and filter operation."""
        # Setup mocks for new data collection method
        mock_github_client.get_repository.return_value = sample_repository

        # Mock the get method for ForkListProcessor
        fork_data = {
            "id": sample_fork_repository.id,
            "name": sample_fork_repository.name,
            "full_name": sample_fork_repository.full_name,
            "owner": {"login": sample_fork_repository.owner},
            "html_url": sample_fork_repository.html_url,
            "stargazers_count": sample_fork_repository.stars,
            "forks_count": sample_fork_repository.forks_count,
            "watchers_count": sample_fork_repository.stars,
            "size": sample_fork_repository.size or 100,
            "language": sample_fork_repository.language,
            "topics": sample_fork_repository.topics or [],
            "open_issues_count": 0,
            "created_at": sample_fork_repository.created_at.isoformat() + "Z",
            "updated_at": sample_fork_repository.updated_at.isoformat() + "Z",
            "pushed_at": sample_fork_repository.pushed_at.isoformat() + "Z",
            "archived": False,
            "disabled": False,
            "fork": True,
            "license": None,
            "description": None,
            "homepage": None,
            "default_branch": "main",
        }
        mock_github_client.get.return_value = [fork_data]

        # Setup mocks for fork analysis
        mock_github_client.get_commits_ahead_behind.return_value = {
            "ahead_by": 5,
            "behind_by": 2,
            "total_commits": 7,
        }
        mock_github_client.get_user.return_value = sample_user

        # Test
        result = await fork_discovery_service.discover_and_filter_forks(
            "https://github.com/test-owner/test-repo"
        )

        # Assertions
        assert len(result) == 1
        fork = result[0]
        assert fork.is_active is True
        assert fork.commits_ahead == 5
        assert fork.divergence_score > 0


class TestForkFilteringLogic:
    """Test the enhanced two-stage fork filtering logic."""

    @pytest.fixture
    def fork_with_no_commits_ahead_equal_timestamps(
        self, sample_fork_repository, sample_repository, sample_user
    ):
        """Create a fork where created_at == pushed_at (no commits ahead)."""
        timestamp = datetime.utcnow() - timedelta(days=30)
        fork_repo = sample_fork_repository.model_copy()
        fork_repo.created_at = timestamp
        fork_repo.pushed_at = timestamp  # Same as created_at = no commits made

        return Fork(
            repository=fork_repo,
            parent=sample_repository,
            owner=sample_user,
            commits_ahead=0,
            commits_behind=5,
            last_activity=timestamp,
        )

    @pytest.fixture
    def fork_with_no_commits_ahead_created_after_push(
        self, sample_fork_repository, sample_repository, sample_user
    ):
        """Create a fork where created_at > pushed_at (no commits ahead)."""
        created_time = datetime.utcnow() - timedelta(days=30)
        pushed_time = datetime.utcnow() - timedelta(
            days=31
        )  # Pushed before creation (edge case)

        fork_repo = sample_fork_repository.model_copy()
        fork_repo.created_at = created_time
        fork_repo.pushed_at = pushed_time

        return Fork(
            repository=fork_repo,
            parent=sample_repository,
            owner=sample_user,
            commits_ahead=0,
            commits_behind=5,
            last_activity=pushed_time,
        )

    @pytest.fixture
    def fork_with_commits_ahead(
        self, sample_fork_repository, sample_repository, sample_user
    ):
        """Create a fork where created_at < pushed_at (has commits ahead)."""
        created_time = datetime.utcnow() - timedelta(days=30)
        pushed_time = datetime.utcnow() - timedelta(days=5)  # Pushed after creation

        fork_repo = sample_fork_repository.model_copy()
        fork_repo.created_at = created_time
        fork_repo.pushed_at = pushed_time

        return Fork(
            repository=fork_repo,
            parent=sample_repository,
            owner=sample_user,
            commits_ahead=3,
            commits_behind=1,
            last_activity=pushed_time,
        )

    def test_has_no_commits_ahead_equal_timestamps(
        self, fork_discovery_service, fork_with_no_commits_ahead_equal_timestamps
    ):
        """Test detection of forks with no commits ahead when created_at == pushed_at."""
        result = fork_discovery_service._has_no_commits_ahead(
            fork_with_no_commits_ahead_equal_timestamps
        )
        assert result is True

    def test_has_no_commits_ahead_created_after_push(
        self, fork_discovery_service, fork_with_no_commits_ahead_created_after_push
    ):
        """Test detection of forks with no commits ahead when created_at > pushed_at."""
        result = fork_discovery_service._has_no_commits_ahead(
            fork_with_no_commits_ahead_created_after_push
        )
        assert result is True

    def test_has_commits_ahead(self, fork_discovery_service, fork_with_commits_ahead):
        """Test detection of forks with commits ahead when created_at < pushed_at."""
        result = fork_discovery_service._has_no_commits_ahead(fork_with_commits_ahead)
        assert result is False

    def test_has_no_commits_ahead_missing_timestamps(
        self, fork_discovery_service, sample_fork
    ):
        """Test behavior when timestamp data is missing."""
        # Remove timestamp data
        fork = sample_fork.model_copy()
        fork.repository.created_at = None
        fork.repository.pushed_at = None

        result = fork_discovery_service._has_no_commits_ahead(fork)
        # Should return False (proceed with analysis) when data is missing
        assert result is False

    def test_has_no_commits_ahead_missing_created_at(
        self, fork_discovery_service, sample_fork
    ):
        """Test behavior when created_at is missing."""
        fork = sample_fork.model_copy()
        fork.repository.created_at = None

        result = fork_discovery_service._has_no_commits_ahead(fork)
        assert result is False

    def test_has_no_commits_ahead_missing_pushed_at(
        self, fork_discovery_service, sample_fork
    ):
        """Test behavior when pushed_at is missing."""
        fork = sample_fork.model_copy()
        fork.repository.pushed_at = None

        result = fork_discovery_service._has_no_commits_ahead(fork)
        assert result is False

    @pytest.mark.asyncio
    async def test_filter_active_forks_two_stage_approach(
        self,
        fork_discovery_service,
        fork_with_no_commits_ahead_equal_timestamps,
        fork_with_no_commits_ahead_created_after_push,
        fork_with_commits_ahead,
    ):
        """Test the two-stage filtering approach."""
        # Create a mix of forks
        forks = [
            fork_with_no_commits_ahead_equal_timestamps,  # Should be pre-filtered out
            fork_with_no_commits_ahead_created_after_push,  # Should be pre-filtered out
            fork_with_commits_ahead,  # Should proceed to full analysis
        ]

        # Test
        result = await fork_discovery_service.filter_active_forks(forks)

        # Assertions
        assert len(result) == 1  # Only the fork with commits ahead should remain
        assert result[0] == fork_with_commits_ahead
        assert result[0].is_active is True
        assert result[0].divergence_score > 0

    @pytest.mark.asyncio
    async def test_filter_active_forks_pre_filtering_logs(
        self,
        fork_discovery_service,
        fork_with_no_commits_ahead_equal_timestamps,
        fork_with_commits_ahead,
        caplog,
    ):
        """Test that pre-filtering logs are generated correctly."""
        import logging

        caplog.set_level(logging.INFO)

        forks = [
            fork_with_no_commits_ahead_equal_timestamps,
            fork_with_commits_ahead,
        ]

        # Test
        await fork_discovery_service.filter_active_forks(forks)

        # Check logs
        log_messages = [record.message for record in caplog.records]
        assert any(
            "Automatic filtering: 1 forks skipped, 1 forks proceeding to analysis" in msg
            for msg in log_messages
        )
        assert any(
            "Analysis completed: Found 1 active forks from 1 analyzed" in msg
            for msg in log_messages
        )

    @pytest.mark.asyncio
    async def test_filter_active_forks_all_pre_filtered(
        self,
        fork_discovery_service,
        fork_with_no_commits_ahead_equal_timestamps,
        fork_with_no_commits_ahead_created_after_push,
    ):
        """Test when all forks are pre-filtered out."""
        forks = [
            fork_with_no_commits_ahead_equal_timestamps,
            fork_with_no_commits_ahead_created_after_push,
        ]

        # Test
        result = await fork_discovery_service.filter_active_forks(forks)

        # Assertions
        assert len(result) == 0  # All forks should be pre-filtered out

    @pytest.mark.asyncio
    async def test_filter_active_forks_none_pre_filtered(
        self,
        fork_discovery_service,
        fork_with_commits_ahead,
    ):
        """Test when no forks are pre-filtered."""
        # Create another fork with commits ahead
        fork2 = fork_with_commits_ahead.model_copy()
        fork2.repository.full_name = "another-owner/test-repo"
        fork2.repository.owner = "another-owner"

        forks = [fork_with_commits_ahead, fork2]

        # Test
        result = await fork_discovery_service.filter_active_forks(forks)

        # Assertions
        assert len(result) == 2  # Both forks should pass filtering

    @pytest.mark.asyncio
    async def test_filter_active_forks_removes_complex_prioritization(
        self,
        fork_discovery_service,
        fork_with_commits_ahead,
    ):
        """Test that complex prioritization is removed - all forks with commits proceed regardless of age/stars."""
        # Create an old fork with few stars but has commits ahead
        old_fork = fork_with_commits_ahead.model_copy()
        old_fork.repository.created_at = datetime.utcnow() - timedelta(
            days=500
        )  # Very old
        old_fork.repository.pushed_at = datetime.utcnow() - timedelta(
            days=400
        )  # Still has commits
        old_fork.repository.stars = 0  # No stars
        old_fork.last_activity = datetime.utcnow() - timedelta(days=400)

        forks = [old_fork]

        # Test
        result = await fork_discovery_service.filter_active_forks(forks)

        # Assertions - old fork with no stars should still be included if it has commits ahead
        assert len(result) == 1
        assert result[0] == old_fork


class TestForkDiscoveryDataCollectionIntegration:
    """Test the integration with fork data collection engine."""

    def test_init_with_data_collection_engine(self, mock_github_client, mock_data_collection_engine):
        """Test service initialization with data collection engine."""
        service = ForkDiscoveryService(
            github_client=mock_github_client,
            data_collection_engine=mock_data_collection_engine,
        )

        assert service.github_client == mock_github_client
        assert service.data_collection_engine == mock_data_collection_engine
        assert isinstance(service.fork_list_processor, ForkListProcessor)

    def test_init_without_data_collection_engine(self, mock_github_client):
        """Test service initialization without data collection engine creates default."""
        service = ForkDiscoveryService(github_client=mock_github_client)

        assert service.github_client == mock_github_client
        assert isinstance(service.data_collection_engine, ForkDataCollectionEngine)
        assert isinstance(service.fork_list_processor, ForkListProcessor)

    @pytest.mark.asyncio
    async def test_discover_and_collect_fork_data_success(
        self,
        fork_discovery_service_with_mocks,
        mock_data_collection_engine,
        sample_collected_fork_data,
        sample_qualified_forks_result,
    ):
        """Test successful fork data collection."""
        # Setup mocks
        fork_discovery_service_with_mocks.fork_list_processor.get_all_forks_list_data.return_value = [
            {"full_name": "fork-owner/test-repo", "id": 456}
        ]
        mock_data_collection_engine.collect_fork_data_from_list.return_value = [
            sample_collected_fork_data
        ]
        mock_data_collection_engine.create_qualification_result.return_value = (
            sample_qualified_forks_result
        )

        # Test
        result = await fork_discovery_service_with_mocks.discover_and_collect_fork_data(
            "https://github.com/test-owner/test-repo"
        )

        # Assertions
        assert isinstance(result, QualifiedForksResult)
        assert result.repository_owner == "test-owner"
        assert result.repository_name == "test-repo"
        assert len(result.collected_forks) == 1

        # Verify method calls
        fork_discovery_service_with_mocks.fork_list_processor.get_all_forks_list_data.assert_called_once_with(
            "test-owner", "test-repo"
        )
        mock_data_collection_engine.collect_fork_data_from_list.assert_called_once()
        mock_data_collection_engine.create_qualification_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_discover_and_collect_fork_data_with_disable_cache(
        self,
        fork_discovery_service_with_mocks,
        mock_data_collection_engine,
        sample_collected_fork_data,
        sample_qualified_forks_result,
    ):
        """Test fork data collection with cache disabled."""
        # Setup mocks
        fork_discovery_service_with_mocks.fork_list_processor.get_all_forks_list_data.return_value = [
            {"full_name": "fork-owner/test-repo", "id": 456}
        ]
        mock_data_collection_engine.collect_fork_data_from_list.return_value = [
            sample_collected_fork_data
        ]
        mock_data_collection_engine.create_qualification_result.return_value = (
            sample_qualified_forks_result
        )

        # Test
        result = await fork_discovery_service_with_mocks.discover_and_collect_fork_data(
            "https://github.com/test-owner/test-repo", disable_cache=True
        )

        # Assertions
        assert isinstance(result, QualifiedForksResult)

        # Verify method was called (disable_cache not supported by ForkListProcessor)
        fork_discovery_service_with_mocks.fork_list_processor.get_all_forks_list_data.assert_called_once_with(
            "test-owner", "test-repo"
        )

    @pytest.mark.asyncio
    async def test_discover_and_collect_fork_data_error_handling(
        self, fork_discovery_service_with_mocks
    ):
        """Test error handling in fork data collection."""
        # Setup mock to raise error
        fork_discovery_service_with_mocks.fork_list_processor.get_all_forks_list_data.side_effect = (
            Exception("API Error")
        )

        # Test
        with pytest.raises(ForkDiscoveryError, match="Failed to collect fork data"):
            await fork_discovery_service_with_mocks.discover_and_collect_fork_data(
                "https://github.com/test-owner/test-repo"
            )

    def test_create_repository_from_collected_data(
        self, fork_discovery_service, sample_collected_fork_data
    ):
        """Test creating Repository object from collected fork data."""
        result = fork_discovery_service._create_repository_from_collected_data(
            sample_collected_fork_data
        )

        assert isinstance(result, Repository)
        assert result.id == sample_collected_fork_data.metrics.id
        assert result.owner == sample_collected_fork_data.metrics.owner
        assert result.name == sample_collected_fork_data.metrics.name
        assert result.full_name == sample_collected_fork_data.metrics.full_name
        assert result.html_url == sample_collected_fork_data.metrics.html_url
        assert result.clone_url == f"https://github.com/{sample_collected_fork_data.metrics.full_name}.git"
        assert result.stars == sample_collected_fork_data.metrics.stargazers_count
        assert result.forks_count == sample_collected_fork_data.metrics.forks_count
        assert result.is_fork is True
        assert result.created_at == sample_collected_fork_data.metrics.created_at
        assert result.updated_at == sample_collected_fork_data.metrics.updated_at
        assert result.pushed_at == sample_collected_fork_data.metrics.pushed_at

    @pytest.mark.asyncio
    async def test_discover_forks_with_data_collection_integration(
        self,
        fork_discovery_service_with_mocks,
        mock_github_client,
        mock_data_collection_engine,
        sample_repository,
        sample_collected_fork_data,
        sample_qualified_forks_result,
        sample_user,
    ):
        """Test discover_forks method with data collection integration."""
        # Setup mocks
        mock_github_client.get_repository.return_value = sample_repository

        # Mock the discover_and_collect_fork_data method
        fork_discovery_service_with_mocks.discover_and_collect_fork_data = AsyncMock(
            return_value=sample_qualified_forks_result
        )

        mock_data_collection_engine.exclude_no_commits_ahead.return_value = [
            sample_collected_fork_data
        ]

        mock_github_client.get_commits_ahead_behind.return_value = {
            "ahead_by": 5,
            "behind_by": 2,
            "total_commits": 7,
        }
        mock_github_client.get_user.return_value = sample_user

        # Test
        result = await fork_discovery_service_with_mocks.discover_forks(
            "https://github.com/test-owner/test-repo"
        )

        # Assertions
        assert len(result) == 1
        fork = result[0]
        assert isinstance(fork, Fork)
        assert fork.commits_ahead == 5
        assert fork.commits_behind == 2

        # Verify integration calls
        fork_discovery_service_with_mocks.discover_and_collect_fork_data.assert_called_once_with(
            "https://github.com/test-owner/test-repo", disable_cache=False
        )
        mock_data_collection_engine.exclude_no_commits_ahead.assert_called_once()

    @pytest.mark.asyncio
    async def test_discover_forks_automatic_filtering_statistics(
        self,
        fork_discovery_service_with_mocks,
        mock_github_client,
        mock_data_collection_engine,
        sample_repository,
        sample_collected_fork_data,
        sample_user,
        caplog,
    ):
        """Test that automatic filtering statistics are logged correctly."""
        import logging

        caplog.set_level(logging.INFO)

        # Create qualified result with statistics
        stats = QualificationStats(
            total_forks_discovered=10,
            forks_with_no_commits=7,
            forks_with_commits=3,
            archived_forks=0,
            disabled_forks=0,
            api_calls_made=10,
            api_calls_saved=21,  # 7 forks * 3 calls each
            processing_time_seconds=1.5,
        )

        qualified_result = QualifiedForksResult(
            repository_owner="test-owner",
            repository_name="test-repo",
            repository_url="https://github.com/test-owner/test-repo",
            collected_forks=[sample_collected_fork_data] * 3,  # 3 forks needing analysis
            stats=stats,
        )

        # Setup mocks
        mock_github_client.get_repository.return_value = sample_repository
        fork_discovery_service_with_mocks.discover_and_collect_fork_data = AsyncMock(
            return_value=qualified_result
        )
        mock_data_collection_engine.exclude_no_commits_ahead.return_value = [
            sample_collected_fork_data
        ]
        mock_github_client.get_commits_ahead_behind.return_value = {
            "ahead_by": 5,
            "behind_by": 2,
            "total_commits": 7,
        }
        mock_github_client.get_user.return_value = sample_user

        # Test
        await fork_discovery_service_with_mocks.discover_forks(
            "https://github.com/test-owner/test-repo"
        )

        # Check logs for statistics
        log_messages = [record.message for record in caplog.records]
        assert any("7 forks skipped" in msg for msg in log_messages)
        assert any("API calls saved by automatic filtering: 21" in msg for msg in log_messages)

    @pytest.mark.asyncio
    async def test_discover_and_filter_forks_with_disable_cache(
        self,
        fork_discovery_service_with_mocks,
        mock_github_client,
        mock_data_collection_engine,
        sample_repository,
        sample_collected_fork_data,
        sample_qualified_forks_result,
        sample_user,
    ):
        """Test discover_and_filter_forks with disable_cache parameter."""
        # Setup mocks
        mock_github_client.get_repository.return_value = sample_repository
        fork_discovery_service_with_mocks.discover_and_collect_fork_data = AsyncMock(
            return_value=sample_qualified_forks_result
        )
        mock_data_collection_engine.exclude_no_commits_ahead.return_value = [
            sample_collected_fork_data
        ]
        mock_github_client.get_commits_ahead_behind.return_value = {
            "ahead_by": 5,
            "behind_by": 2,
            "total_commits": 7,
        }
        mock_github_client.get_user.return_value = sample_user

        # Test
        result = await fork_discovery_service_with_mocks.discover_and_filter_forks(
            "https://github.com/test-owner/test-repo", disable_cache=True
        )

        # Assertions
        assert len(result) == 1
        assert isinstance(result[0], Fork)

        # Verify disable_cache was passed through
        fork_discovery_service_with_mocks.discover_and_collect_fork_data.assert_called_once_with(
            "https://github.com/test-owner/test-repo", disable_cache=True
        )

    @pytest.mark.asyncio
    async def test_get_unique_commits_with_disable_cache(
        self,
        fork_discovery_service,
        mock_github_client,
        sample_fork,
        sample_repository,
    ):
        """Test get_unique_commits with disable_cache parameter."""
        # Setup mock comparison data
        comparison_data = {
            "commits": [
                {
                    "sha": "a" * 40,
                    "commit": {
                        "message": "feat: add new feature",
                        "author": {"date": datetime.utcnow().isoformat() + "Z"},
                        "committer": {"date": datetime.utcnow().isoformat() + "Z"},
                    },
                    "author": {
                        "login": "author",
                        "html_url": "https://github.com/author",
                    },
                    "committer": {
                        "login": "author",
                        "html_url": "https://github.com/author",
                    },
                    "stats": {"additions": 50, "deletions": 10},
                    "files": [{"filename": "src/main.py"}],
                    "parents": [{"sha": "b" * 40}],
                }
            ]
        }

        mock_github_client.get_fork_comparison.return_value = comparison_data

        # Test
        result = await fork_discovery_service.get_unique_commits(
            sample_fork, sample_repository, disable_cache=True
        )

        # Assertions
        assert len(result) == 1
        assert isinstance(result[0], Commit)

        # Verify disable_cache was passed through
        mock_github_client.get_fork_comparison.assert_called_once_with(
            sample_fork.repository.owner,
            sample_fork.repository.name,
            sample_repository.owner,
            sample_repository.name,
            disable_cache=True,
        )

    @pytest.mark.asyncio
    async def test_get_fork_metrics_with_disable_cache(
        self,
        fork_discovery_service,
        mock_github_client,
        sample_fork,
        sample_user,
    ):
        """Test get_fork_metrics with disable_cache parameter."""
        # Setup mock contributors
        contributors = [sample_user, sample_user]  # 2 contributors
        mock_github_client.get_repository_contributors.return_value = contributors

        # Test
        result = await fork_discovery_service.get_fork_metrics(
            sample_fork, disable_cache=True
        )

        # Assertions
        assert isinstance(result, ForkMetrics)
        assert result.contributors == 2

        # Verify disable_cache was passed through
        mock_github_client.get_repository_contributors.assert_called_once_with(
            sample_fork.repository.owner,
            sample_fork.repository.name,
            per_page=100,
            disable_cache=True,
        )


class TestForkDiscoveryOptimization:
    """Test the new optimization features for fork discovery."""

    @pytest.fixture
    def fork_repo_no_commits_ahead(self, sample_fork_repository):
        """Create a fork repository with no commits ahead (created_at >= pushed_at)."""
        timestamp = datetime.utcnow() - timedelta(days=30)
        fork_repo = sample_fork_repository.model_copy()
        fork_repo.created_at = timestamp
        fork_repo.pushed_at = timestamp  # Same as created_at = no commits made
        fork_repo.full_name = "no-commits/test-repo"
        fork_repo.owner = "no-commits"
        return fork_repo

    @pytest.fixture
    def fork_repo_with_commits_ahead(self, sample_fork_repository):
        """Create a fork repository with commits ahead (created_at < pushed_at)."""
        created_time = datetime.utcnow() - timedelta(days=30)
        pushed_time = datetime.utcnow() - timedelta(days=5)  # Pushed after creation
        fork_repo = sample_fork_repository.model_copy()
        fork_repo.created_at = created_time
        fork_repo.pushed_at = pushed_time
        fork_repo.full_name = "with-commits/test-repo"
        fork_repo.owner = "with-commits"
        return fork_repo

    def test_has_no_commits_ahead_from_repo_equal_timestamps(
        self, fork_discovery_service, fork_repo_no_commits_ahead
    ):
        """Test detection of forks with no commits ahead when created_at == pushed_at."""
        result = fork_discovery_service._has_no_commits_ahead_from_repo(
            fork_repo_no_commits_ahead
        )
        assert result is True

    def test_has_no_commits_ahead_from_repo_created_after_push(
        self, fork_discovery_service, sample_fork_repository
    ):
        """Test detection of forks with no commits ahead when created_at > pushed_at."""
        created_time = datetime.utcnow() - timedelta(days=30)
        pushed_time = datetime.utcnow() - timedelta(days=31)  # Pushed before creation
        fork_repo = sample_fork_repository.model_copy()
        fork_repo.created_at = created_time
        fork_repo.pushed_at = pushed_time

        result = fork_discovery_service._has_no_commits_ahead_from_repo(fork_repo)
        assert result is True

    def test_has_no_commits_ahead_from_repo_with_commits(
        self, fork_discovery_service, fork_repo_with_commits_ahead
    ):
        """Test detection of forks with commits ahead when created_at < pushed_at."""
        result = fork_discovery_service._has_no_commits_ahead_from_repo(
            fork_repo_with_commits_ahead
        )
        assert result is False

    def test_has_no_commits_ahead_from_repo_missing_timestamps(
        self, fork_discovery_service, sample_fork_repository
    ):
        """Test behavior when timestamp data is missing."""
        fork_repo = sample_fork_repository.model_copy()
        fork_repo.created_at = None
        fork_repo.pushed_at = None

        result = fork_discovery_service._has_no_commits_ahead_from_repo(fork_repo)
        # Should return False (proceed with analysis) when data is missing
        assert result is False

    @pytest.mark.asyncio
    async def test_pre_filter_forks_by_metadata(
        self,
        fork_discovery_service,
        sample_repository,
        fork_repo_no_commits_ahead,
        fork_repo_with_commits_ahead,
    ):
        """Test pre-filtering of forks using metadata analysis."""
        fork_repos = [fork_repo_no_commits_ahead, fork_repo_with_commits_ahead]

        # Test
        filtered_forks, skipped_count, api_calls_saved = await fork_discovery_service._pre_filter_forks_by_metadata(
            fork_repos, sample_repository
        )

        # Assertions
        assert len(filtered_forks) == 1  # Only fork with commits ahead should remain
        assert filtered_forks[0] == fork_repo_with_commits_ahead
        assert skipped_count == 1  # One fork should be skipped
        assert api_calls_saved == 3  # 3 API calls saved per skipped fork

    @pytest.mark.asyncio
    async def test_pre_filter_forks_by_metadata_all_skipped(
        self,
        fork_discovery_service,
        sample_repository,
        fork_repo_no_commits_ahead,
    ):
        """Test pre-filtering when all forks are skipped."""
        # Create another fork with no commits ahead
        fork_repo_2 = fork_repo_no_commits_ahead.model_copy()
        fork_repo_2.full_name = "another-no-commits/test-repo"
        fork_repo_2.owner = "another-no-commits"

        fork_repos = [fork_repo_no_commits_ahead, fork_repo_2]

        # Test
        filtered_forks, skipped_count, api_calls_saved = await fork_discovery_service._pre_filter_forks_by_metadata(
            fork_repos, sample_repository
        )

        # Assertions
        assert len(filtered_forks) == 0  # All forks should be skipped
        assert skipped_count == 2  # Both forks should be skipped
        assert api_calls_saved == 6  # 6 API calls saved (2 forks * 3 calls each)

    @pytest.mark.asyncio
    async def test_pre_filter_forks_by_metadata_none_skipped(
        self,
        fork_discovery_service,
        sample_repository,
        fork_repo_with_commits_ahead,
    ):
        """Test pre-filtering when no forks are skipped."""
        # Create another fork with commits ahead
        fork_repo_2 = fork_repo_with_commits_ahead.model_copy()
        fork_repo_2.full_name = "another-with-commits/test-repo"
        fork_repo_2.owner = "another-with-commits"

        fork_repos = [fork_repo_with_commits_ahead, fork_repo_2]

        # Test
        filtered_forks, skipped_count, api_calls_saved = await fork_discovery_service._pre_filter_forks_by_metadata(
            fork_repos, sample_repository
        )

        # Assertions
        assert len(filtered_forks) == 2  # No forks should be skipped
        assert skipped_count == 0  # No forks should be skipped
        assert api_calls_saved == 0  # No API calls saved

    @pytest.mark.asyncio
    async def test_discover_forks_with_optimization_api_call_reduction(
        self,
        fork_discovery_service,
        mock_github_client,
        sample_repository,
        fork_repo_no_commits_ahead,
        fork_repo_with_commits_ahead,
        sample_user,
        caplog,
    ):
        """Test that discover_forks optimization reduces API calls and logs performance metrics."""
        import logging
        caplog.set_level(logging.INFO)

        # Setup mocks
        mock_github_client.get_repository.return_value = sample_repository
        mock_github_client.get_all_repository_forks.return_value = [
            fork_repo_no_commits_ahead,  # Should be pre-filtered out
            fork_repo_with_commits_ahead,  # Should proceed to full analysis
        ]
        mock_github_client.get_commits_ahead_behind.return_value = {
            "ahead_by": 5,
            "behind_by": 2,
            "total_commits": 7,
        }
        mock_github_client.get_user.return_value = sample_user

        # Test
        result = await fork_discovery_service.discover_forks(
            "https://github.com/test-owner/test-repo"
        )

        # Assertions
        assert len(result) == 1  # Only one fork should be analyzed
        assert result[0].repository.full_name == "with-commits/test-repo"

        # Verify API calls were reduced
        # get_commits_ahead_behind should only be called once (for the non-pre-filtered fork)
        assert mock_github_client.get_commits_ahead_behind.call_count == 1
        # get_user should only be called once
        assert mock_github_client.get_user.call_count == 1

        # Check performance logging
        log_messages = [record.message for record in caplog.records]
        assert any("Pre-filtering: 1 forks skipped, 1 forks proceeding to full analysis" in msg for msg in log_messages)
        assert any("API calls saved by pre-filtering: 3" in msg for msg in log_messages)
        assert any("Performance metrics: 3/6 API calls made (50.0% reduction)" in msg for msg in log_messages)

    @pytest.mark.asyncio
    async def test_discover_forks_optimization_maintains_accuracy(
        self,
        fork_discovery_service,
        mock_github_client,
        sample_repository,
        fork_repo_with_commits_ahead,
        sample_user,
    ):
        """Test that optimization maintains filtering accuracy."""
        # Setup mocks
        mock_github_client.get_repository.return_value = sample_repository
        mock_github_client.get_all_repository_forks.return_value = [
            fork_repo_with_commits_ahead
        ]
        mock_github_client.get_commits_ahead_behind.return_value = {
            "ahead_by": 5,
            "behind_by": 2,
            "total_commits": 7,
        }
        mock_github_client.get_user.return_value = sample_user

        # Test
        result = await fork_discovery_service.discover_forks(
            "https://github.com/test-owner/test-repo"
        )

        # Assertions - should maintain same accuracy as before optimization
        assert len(result) == 1
        fork = result[0]
        assert isinstance(fork, Fork)
        assert fork.repository.full_name == "with-commits/test-repo"
        assert fork.commits_ahead == 5
        assert fork.commits_behind == 2
        assert fork.owner.login == sample_user.login

    @pytest.mark.asyncio
    async def test_discover_forks_optimization_performance_target(
        self,
        fork_discovery_service,
        mock_github_client,
        sample_repository,
        sample_user,
    ):
        """Test that optimization achieves target 60-80% reduction in API calls for typical repositories."""
        # Create a typical repository scenario with 10 forks, 7 of which have no commits ahead
        fork_repos = []

        # 7 forks with no commits ahead (should be pre-filtered)
        for i in range(7):
            timestamp = datetime.utcnow() - timedelta(days=30 + i)
            fork_repo = Repository(
                id=1000 + i,
                owner=f"no-commits-{i}",
                name="test-repo",
                full_name=f"no-commits-{i}/test-repo",
                url=f"https://api.github.com/repos/no-commits-{i}/test-repo",
                html_url=f"https://github.com/no-commits-{i}/test-repo",
                clone_url=f"https://github.com/no-commits-{i}/test-repo.git",
                default_branch="main",
                stars=0,
                forks_count=0,
                is_fork=True,
                created_at=timestamp,
                updated_at=timestamp,
                pushed_at=timestamp,  # Same as created_at = no commits
            )
            fork_repos.append(fork_repo)

        # 3 forks with commits ahead (should proceed to full analysis)
        for i in range(3):
            created_time = datetime.utcnow() - timedelta(days=30 + i)
            pushed_time = datetime.utcnow() - timedelta(days=5 + i)
            fork_repo = Repository(
                id=2000 + i,
                owner=f"with-commits-{i}",
                name="test-repo",
                full_name=f"with-commits-{i}/test-repo",
                url=f"https://api.github.com/repos/with-commits-{i}/test-repo",
                html_url=f"https://github.com/with-commits-{i}/test-repo",
                clone_url=f"https://github.com/with-commits-{i}/test-repo.git",
                default_branch="main",
                stars=5,
                forks_count=1,
                is_fork=True,
                created_at=created_time,
                updated_at=pushed_time,
                pushed_at=pushed_time,  # After created_at = has commits
            )
            fork_repos.append(fork_repo)

        # Setup mocks
        mock_github_client.get_repository.return_value = sample_repository
        mock_github_client.get_all_repository_forks.return_value = fork_repos
        mock_github_client.get_commits_ahead_behind.return_value = {
            "ahead_by": 3,
            "behind_by": 1,
            "total_commits": 4,
        }
        mock_github_client.get_user.return_value = sample_user

        # Test
        result = await fork_discovery_service.discover_forks(
            "https://github.com/test-owner/test-repo"
        )

        # Assertions
        assert len(result) == 3  # Only 3 forks with commits ahead should be analyzed

        # Verify API call reduction
        # Total potential calls: 10 forks * 3 calls = 30 calls
        # Actual calls: 3 forks * 3 calls = 9 calls
        # Reduction: (30 - 9) / 30 = 70% reduction
        expected_calls = 3 * 3  # 3 forks * 3 calls each
        assert mock_github_client.get_commits_ahead_behind.call_count == 3
        assert mock_github_client.get_user.call_count == 3

        # Calculate actual reduction percentage
        total_potential_calls = len(fork_repos) * 3
        actual_calls = expected_calls
        reduction_percentage = ((total_potential_calls - actual_calls) / total_potential_calls * 100)

        # Should achieve target 60-80% reduction
        assert 60 <= reduction_percentage <= 80
        assert reduction_percentage == 70.0  # Exact expected reduction for this scenario


class TestForkDiscoveryServiceEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_create_fork_with_user_fetch_error(
        self,
        fork_discovery_service,
        mock_github_client,
        sample_repository,
        sample_fork_repository,
    ):
        """Test fork creation when user fetch fails."""
        # Setup mocks
        mock_github_client.get_commits_ahead_behind.return_value = {
            "ahead_by": 3,
            "behind_by": 1,
            "total_commits": 4,
        }
        mock_github_client.get_user.side_effect = GitHubAPIError("User not found")

        # Test
        result = await fork_discovery_service._create_fork_with_comparison(
            sample_fork_repository, sample_repository
        )

        # Assertions - should create fork with minimal user info
        assert isinstance(result, Fork)
        assert result.owner.login == sample_fork_repository.owner
        assert result.commits_ahead == 3
        assert result.commits_behind == 1

    @pytest.mark.asyncio
    async def test_get_unique_commits_api_error(
        self,
        fork_discovery_service,
        mock_github_client,
        sample_fork,
        sample_repository,
    ):
        """Test getting unique commits with API error."""
        mock_github_client.get_fork_comparison.side_effect = GitHubAPIError(
            "Comparison failed"
        )

        # Test
        result = await fork_discovery_service.get_unique_commits(
            sample_fork, sample_repository
        )

        # Assertions - should return empty list on error
        assert result == []

    def test_parse_repository_url_edge_cases(self, fork_discovery_service):
        """Test URL parsing edge cases."""
        # Test with trailing slash
        owner, repo = fork_discovery_service._parse_repository_url(
            "https://github.com/owner/repo/"
        )
        assert owner == "owner"
        assert repo == "repo"

        # Test with extra path components (should ignore them)
        owner, repo = fork_discovery_service._parse_repository_url(
            "https://github.com/owner/repo/issues"
        )
        assert owner == "owner"
        assert repo == "repo"
    @pytest.mark.asyncio
    async def test_has_no_commits_ahead_logic(self, fork_discovery_service):
        """Test the _has_no_commits_ahead method with different timestamp scenarios."""
        from datetime import datetime

        from forkscout.models.github import Fork, Repository, User

        # Helper to create test fork
        def create_test_fork(full_name, created_at, pushed_at):
            repo = Repository(
                id=1,
                owner=full_name.split("/")[0],
                name=full_name.split("/")[1],
                full_name=full_name,
                url=f"https://api.github.com/repos/{full_name}",
                html_url=f"https://github.com/{full_name}",
                clone_url=f"https://github.com/{full_name}.git",
                created_at=created_at,
                pushed_at=pushed_at,
                is_fork=True
            )
            user = User(login=repo.owner, html_url=f"https://github.com/{repo.owner}")
            parent = Repository(
                id=2,
                owner="parent",
                name="repo",
                full_name="parent/repo",
                url="https://api.github.com/repos/parent/repo",
                html_url="https://github.com/parent/repo",
                clone_url="https://github.com/parent/repo.git"
            )
            return Fork(
                repository=repo,
                parent=parent,
                owner=user,
                commits_ahead=0,
                commits_behind=0
            )

        # Test case 1: created_at == pushed_at (no commits)
        fork1 = create_test_fork(
            "user1/test-repo",
            created_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
            pushed_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        )

        # Test case 2: created_at > pushed_at (fork created after last push)
        fork2 = create_test_fork(
            "user2/test-repo",
            created_at=datetime(2023, 2, 1, 12, 0, 0, tzinfo=UTC),
            pushed_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        )

        # Test case 3: pushed_at > created_at (potentially has commits)
        fork3 = create_test_fork(
            "user3/test-repo",
            created_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
            pushed_at=datetime(2023, 2, 1, 12, 0, 0, tzinfo=UTC)
        )

        # Test case 4: Missing timestamps
        fork4 = create_test_fork("user4/test-repo", created_at=None, pushed_at=None)

        # Test the logic
        assert fork_discovery_service._has_no_commits_ahead(fork1) == True  # created_at == pushed_at
        assert fork_discovery_service._has_no_commits_ahead(fork2) == True  # created_at > pushed_at
        assert fork_discovery_service._has_no_commits_ahead(fork3) == False # pushed_at > created_at
        assert fork_discovery_service._has_no_commits_ahead(fork4) == False # Missing timestamps
