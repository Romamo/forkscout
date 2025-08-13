"""Tests for fork discovery service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

from forklift.analysis.fork_discovery import ForkDiscoveryService, ForkDiscoveryError
from forklift.github.client import GitHubClient, GitHubAPIError, GitHubNotFoundError
from forklift.models.github import Repository, Fork, User, Commit
from forklift.models.analysis import ForkMetrics


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
def fork_discovery_service(mock_github_client):
    """Create a fork discovery service with mocked client."""
    return ForkDiscoveryService(
        github_client=mock_github_client,
        min_activity_days=365,
        min_commits_ahead=1,
        max_forks_to_analyze=100,
    )


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
        # Setup mocks
        mock_github_client.get_repository.return_value = sample_repository
        mock_github_client.get_all_repository_forks.return_value = [sample_fork_repository]
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
        mock_github_client.get_repository.assert_called_once_with("test-owner", "test-repo")
        mock_github_client.get_all_repository_forks.assert_called_once_with(
            "test-owner", "test-repo", max_forks=100
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

    def test_parse_repository_url_invalid(self, fork_discovery_service):
        """Test parsing invalid URL."""
        with pytest.raises(ForkDiscoveryError, match="Invalid repository URL format"):
            fork_discovery_service._parse_repository_url("invalid-url")

    @pytest.mark.asyncio
    async def test_filter_active_forks(self, fork_discovery_service, sample_fork):
        """Test filtering active forks."""
        # Create forks with different activity levels
        active_fork = sample_fork
        active_fork.commits_ahead = 5
        active_fork.last_activity = datetime.utcnow() - timedelta(days=30)
        
        inactive_fork = Fork(
            repository=sample_fork.repository,
            parent=sample_fork.parent,
            owner=sample_fork.owner,
            commits_ahead=3,
            commits_behind=1,
            last_activity=datetime.utcnow() - timedelta(days=400),  # Too old
        )
        
        no_commits_fork = Fork(
            repository=sample_fork.repository,
            parent=sample_fork.parent,
            owner=sample_fork.owner,
            commits_ahead=0,  # No unique commits
            commits_behind=5,
            last_activity=datetime.utcnow() - timedelta(days=10),
        )
        
        forks = [active_fork, inactive_fork, no_commits_fork]
        
        # Test
        result = await fork_discovery_service.filter_active_forks(forks)
        
        # Assertions
        assert len(result) == 1
        assert result[0] == active_fork
        assert result[0].is_active is True
        assert result[0].divergence_score > 0

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
                    "author": {"login": "author", "html_url": "https://github.com/author"},
                    "committer": {"login": "author", "html_url": "https://github.com/author"},
                    "stats": {"additions": 50, "deletions": 10},
                    "files": [{"filename": "src/main.py"}],
                    "parents": [{"sha": "b" * 40}],
                }
            ]
        }
        
        mock_github_client.get_fork_comparison.return_value = comparison_data
        
        # Test
        result = await fork_discovery_service.get_unique_commits(sample_fork, sample_repository)
        
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
                    "author": {"login": "author", "html_url": "https://github.com/author"},
                    "committer": {"login": "author", "html_url": "https://github.com/author"},
                    "stats": {"additions": 0, "deletions": 0},
                    "files": [],
                    "parents": [{"sha": "b" * 40}, {"sha": "c" * 40}],  # Multiple parents = merge
                }
            ]
        }
        
        mock_github_client.get_fork_comparison.return_value = comparison_data
        
        # Test
        result = await fork_discovery_service.get_unique_commits(sample_fork, sample_repository)
        
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
                    "author": {"login": "author", "html_url": "https://github.com/author"},
                    "committer": {"login": "author", "html_url": "https://github.com/author"},
                    "stats": {"additions": 1, "deletions": 1},  # Very small change
                    "files": [{"filename": "README.md"}],
                    "parents": [{"sha": "b" * 40}],
                }
            ]
        }
        
        mock_github_client.get_fork_comparison.return_value = comparison_data
        
        # Test
        result = await fork_discovery_service.get_unique_commits(sample_fork, sample_repository)
        
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
        mock_github_client.get_repository_contributors.side_effect = GitHubAPIError("API Error")
        
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
        # Setup mocks
        mock_github_client.get_repository.return_value = sample_repository
        mock_github_client.get_all_repository_forks.return_value = [sample_fork_repository]
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


class TestForkDiscoveryServiceEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_create_fork_with_user_fetch_error(
        self, fork_discovery_service, mock_github_client, sample_repository, sample_fork_repository
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
        mock_github_client.get_fork_comparison.side_effect = GitHubAPIError("Comparison failed")
        
        # Test
        result = await fork_discovery_service.get_unique_commits(sample_fork, sample_repository)
        
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