"""Unit tests for GitHub API client."""


import httpx
import pytest
import respx

from forklift.config import GitHubConfig
from forklift.github import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubClient,
    GitHubNotFoundError,
    GitHubRateLimitError,
)
from forklift.models.github import Commit, RecentCommit, Repository, User


class TestGitHubClient:
    """Test cases for GitHubClient."""

    @pytest.fixture
    def github_config(self):
        """Create a test GitHub configuration."""
        return GitHubConfig(
            token="ghp_1234567890abcdef1234567890abcdef12345678",
            base_url="https://api.github.com",
            timeout_seconds=30,
        )

    @pytest.fixture
    def client(self, github_config):
        """Create a test GitHub client."""
        return GitHubClient(github_config)

    def test_client_initialization(self, github_config):
        """Test GitHubClient initialization."""
        client = GitHubClient(github_config)

        assert client.config == github_config
        assert client._client is None
        assert "Authorization" in client._headers
        assert client._headers["Authorization"] == f"Bearer {github_config.token}"
        assert client._headers["Accept"] == "application/vnd.github+json"

    def test_client_initialization_no_token(self):
        """Test GitHubClient initialization without token."""
        config = GitHubConfig()
        client = GitHubClient(config)

        assert "Authorization" not in client._headers

    def test_is_authenticated(self, client):
        """Test authentication check."""
        assert client.is_authenticated() is True

        # Test without token
        config = GitHubConfig()
        client_no_auth = GitHubClient(config)
        assert client_no_auth.is_authenticated() is False

    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Test async context manager."""
        async with client as c:
            assert c is client
            assert client._client is not None

        # Client should be closed after context
        assert client._client is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_request_success(self, client):
        """Test successful GET request."""
        mock_response = {"id": 123, "name": "test"}

        respx.get("https://api.github.com/test").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        async with client:
            result = await client.get("test")
            assert result == mock_response

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_request_with_params(self, client):
        """Test GET request with parameters."""
        mock_response = {"items": []}

        respx.get("https://api.github.com/test").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        async with client:
            result = await client.get("test", params={"page": 1, "per_page": 50})
            assert result == mock_response

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_request(self, client):
        """Test POST request."""
        mock_response = {"id": 123, "created": True}
        request_data = {"name": "test", "description": "Test repo"}

        respx.post("https://api.github.com/test").mock(
            return_value=httpx.Response(201, json=mock_response)
        )

        async with client:
            result = await client.post("test", json_data=request_data)
            assert result == mock_response

    @pytest.mark.asyncio
    @respx.mock
    async def test_authentication_error(self, client):
        """Test authentication error handling."""
        respx.get("https://api.github.com/test").mock(
            return_value=httpx.Response(401, json={"message": "Bad credentials"})
        )

        async with client:
            with pytest.raises(GitHubAuthenticationError) as exc_info:
                await client.get("test")

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @respx.mock
    async def test_not_found_error(self, client):
        """Test not found error handling."""
        respx.get("https://api.github.com/repos/nonexistent/repo").mock(
            return_value=httpx.Response(404, json={"message": "Not Found"})
        )

        async with client:
            with pytest.raises(GitHubNotFoundError) as exc_info:
                await client.get("repos/nonexistent/repo")

            assert exc_info.value.status_code == 404

    # NOTE: Removed test_rate_limit_error as it was taking too long to execute
    # Rate limit error handling is covered by integration tests in:
    # - tests/integration/test_smart_fork_filtering_error_handling.py
    # - tests/integration/test_rate_limiting_integration.py

    @pytest.mark.asyncio
    @respx.mock
    async def test_server_error(self, client):
        """Test server error handling."""
        respx.get("https://api.github.com/test").mock(
            return_value=httpx.Response(500, json={"message": "Internal Server Error"})
        )

        async with client:
            with pytest.raises(GitHubAPIError) as exc_info:
                await client.get("test")

            assert exc_info.value.status_code == 500
            assert "server error" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_network_error(self, client):
        """Test network error handling."""
        respx.get("https://api.github.com/test").mock(
            side_effect=httpx.NetworkError("Connection failed")
        )

        async with client:
            with pytest.raises(GitHubAPIError) as exc_info:
                await client.get("test")

            assert "network error" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_timeout_error(self, client):
        """Test timeout error handling."""
        respx.get("https://api.github.com/test").mock(
            side_effect=httpx.TimeoutException("Request timeout")
        )

        async with client:
            with pytest.raises(GitHubAPIError) as exc_info:
                await client.get("test")

            assert "timeout" in str(exc_info.value).lower()


class TestGitHubClientRepositoryOperations:
    """Test repository-related operations."""

    @pytest.fixture
    def client(self):
        """Create a test GitHub client."""
        config = GitHubConfig(token="ghp_1234567890abcdef1234567890abcdef12345678")
        return GitHubClient(config)

    @pytest.fixture
    def mock_repository_data(self):
        """Mock repository data from GitHub API."""
        return {
            "id": 123456,
            "name": "test-repo",
            "full_name": "testowner/test-repo",
            "owner": {"login": "testowner", "html_url": "https://github.com/testowner"},
            "url": "https://api.github.com/repos/testowner/test-repo",
            "html_url": "https://github.com/testowner/test-repo",
            "clone_url": "https://github.com/testowner/test-repo.git",
            "default_branch": "main",
            "stargazers_count": 100,
            "forks_count": 25,
            "watchers_count": 150,
            "open_issues_count": 5,
            "size": 1024,
            "language": "Python",
            "description": "A test repository",
            "topics": ["python", "testing"],
            "license": {"name": "MIT"},
            "private": False,
            "fork": False,
            "archived": False,
            "disabled": False,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-02T00:00:00Z",
            "pushed_at": "2023-01-03T00:00:00Z",
        }

    @pytest.fixture
    def mock_user_data(self):
        """Mock user data from GitHub API."""
        return {
            "id": 12345,
            "login": "testuser",
            "name": "Test User",
            "email": "test@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
            "html_url": "https://github.com/testuser",
            "type": "User",
            "site_admin": False,
        }

    @pytest.fixture
    def mock_commit_data(self, mock_user_data):
        """Mock commit data from GitHub API."""
        return {
            "sha": "a" * 40,
            "commit": {
                "message": "Test commit",
                "author": {
                    "name": "Test User",
                    "email": "test@example.com",
                    "date": "2023-01-01T00:00:00Z",
                },
                "committer": {
                    "name": "Test User",
                    "email": "test@example.com",
                    "date": "2023-01-01T00:00:00Z",
                },
                "verification": {"verified": True},
            },
            "author": mock_user_data,
            "committer": mock_user_data,
            "stats": {"additions": 10, "deletions": 5},
            "files": [{"filename": "test.py"}, {"filename": "README.md"}],
            "parents": [{"sha": "b" * 40}],
        }

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_repository(self, client, mock_repository_data):
        """Test getting repository information."""
        respx.get("https://api.github.com/repos/testowner/test-repo").mock(
            return_value=httpx.Response(200, json=mock_repository_data)
        )

        async with client:
            repo = await client.get_repository("testowner", "test-repo")

            assert isinstance(repo, Repository)
            assert repo.owner == "testowner"
            assert repo.name == "test-repo"
            assert repo.full_name == "testowner/test-repo"
            assert repo.stars == 100
            assert repo.language == "Python"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_repository_forks(self, client, mock_repository_data):
        """Test getting repository forks."""
        fork_data = mock_repository_data.copy()
        fork_data.update({
            "name": "test-repo",
            "full_name": "forker/test-repo",
            "owner": {"login": "forker", "html_url": "https://github.com/forker"},
            "fork": True,
        })

        respx.get("https://api.github.com/repos/testowner/test-repo/forks").mock(
            return_value=httpx.Response(200, json=[fork_data])
        )

        async with client:
            forks = await client.get_repository_forks("testowner", "test-repo")

            assert len(forks) == 1
            assert isinstance(forks[0], Repository)
            assert forks[0].owner == "forker"
            assert forks[0].is_fork is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_all_repository_forks_pagination(self, client, mock_repository_data):
        """Test getting all repository forks with pagination."""
        # Create 100 forks for first page (full page)
        first_page_forks = []
        for i in range(100):
            fork = mock_repository_data.copy()
            fork.update({
                "full_name": f"forker{i}/test-repo",
                "owner": {"login": f"forker{i}", "html_url": f"https://github.com/forker{i}"},
                "fork": True,
            })
            first_page_forks.append(fork)

        # Create 50 forks for second page (partial page)
        second_page_forks = []
        for i in range(100, 150):
            fork = mock_repository_data.copy()
            fork.update({
                "full_name": f"forker{i}/test-repo",
                "owner": {"login": f"forker{i}", "html_url": f"https://github.com/forker{i}"},
                "fork": True,
            })
            second_page_forks.append(fork)

        # Mock different pages based on page parameter
        def mock_forks_response(request):
            page = int(request.url.params.get("page", 1))
            if page == 1:
                return httpx.Response(200, json=first_page_forks)
            elif page == 2:
                return httpx.Response(200, json=second_page_forks)
            else:
                return httpx.Response(200, json=[])

        respx.get("https://api.github.com/repos/testowner/test-repo/forks").mock(
            side_effect=mock_forks_response
        )

        async with client:
            forks = await client.get_all_repository_forks("testowner", "test-repo")

            assert len(forks) == 150
            assert forks[0].owner == "forker0"
            assert forks[99].owner == "forker99"
            assert forks[149].owner == "forker149"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_all_repository_forks_max_limit(self, client, mock_repository_data):
        """Test getting repository forks with max limit."""
        # Create 5 forks but limit to 3
        forks_data = []
        for i in range(5):
            fork = mock_repository_data.copy()
            fork.update({
                "full_name": f"forker{i}/test-repo",
                "owner": {"login": f"forker{i}", "html_url": f"https://github.com/forker{i}"},
                "fork": True,
            })
            forks_data.append(fork)

        respx.get("https://api.github.com/repos/testowner/test-repo/forks").mock(
            return_value=httpx.Response(200, json=forks_data)
        )

        async with client:
            forks = await client.get_all_repository_forks("testowner", "test-repo", max_forks=3)

            assert len(forks) == 3

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_repository_commits(self, client, mock_commit_data):
        """Test getting repository commits."""
        respx.get("https://api.github.com/repos/testowner/test-repo/commits").mock(
            return_value=httpx.Response(200, json=[mock_commit_data])
        )

        async with client:
            commits = await client.get_repository_commits("testowner", "test-repo")

            assert len(commits) == 1
            assert isinstance(commits[0], Commit)
            assert commits[0].sha == "a" * 40
            assert commits[0].message == "Test commit"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_commit(self, client, mock_commit_data):
        """Test getting detailed commit information."""
        sha = "a" * 40
        respx.get(f"https://api.github.com/repos/testowner/test-repo/commits/{sha}").mock(
            return_value=httpx.Response(200, json=mock_commit_data)
        )

        async with client:
            commit = await client.get_commit("testowner", "test-repo", sha)

            assert isinstance(commit, Commit)
            assert commit.sha == sha
            assert commit.message == "Test commit"
            assert commit.additions == 10
            assert commit.deletions == 5

    @pytest.mark.asyncio
    @respx.mock
    async def test_compare_commits(self, client):
        """Test comparing commits."""
        comparison_data = {
            "status": "ahead",
            "ahead_by": 5,
            "behind_by": 0,
            "total_commits": 5,
            "commits": [],
        }

        respx.get("https://api.github.com/repos/testowner/test-repo/compare/main...feature").mock(
            return_value=httpx.Response(200, json=comparison_data)
        )

        async with client:
            result = await client.compare_commits("testowner", "test-repo", "main", "feature")

            assert result["ahead_by"] == 5
            assert result["behind_by"] == 0
            assert result["status"] == "ahead"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_recent_commits_default_branch(self, client, mock_commit_data, mock_repository_data):
        """Test getting recent commits from default branch."""
        # Mock repository info to get default branch
        respx.get("https://api.github.com/repos/testowner/test-repo").mock(
            return_value=httpx.Response(200, json=mock_repository_data)
        )
        
        # Mock commits endpoint
        respx.get("https://api.github.com/repos/testowner/test-repo/commits").mock(
            return_value=httpx.Response(200, json=[mock_commit_data, mock_commit_data])
        )

        async with client:
            commits = await client.get_recent_commits("testowner", "test-repo", count=2)

            assert len(commits) == 2
            assert isinstance(commits[0], RecentCommit)
            assert commits[0].short_sha == "aaaaaaa"  # First 7 chars of "a" * 40
            assert commits[0].message == "Test commit"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_recent_commits_specific_branch(self, client, mock_commit_data):
        """Test getting recent commits from specific branch."""
        respx.get("https://api.github.com/repos/testowner/test-repo/commits").mock(
            return_value=httpx.Response(200, json=[mock_commit_data])
        )

        async with client:
            commits = await client.get_recent_commits("testowner", "test-repo", branch="feature", count=1)

            assert len(commits) == 1
            assert isinstance(commits[0], RecentCommit)
            assert commits[0].short_sha == "aaaaaaa"
            assert commits[0].message == "Test commit"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_recent_commits_empty_repository(self, client, mock_repository_data):
        """Test getting recent commits from empty repository."""
        # Mock repository info
        respx.get("https://api.github.com/repos/testowner/test-repo").mock(
            return_value=httpx.Response(200, json=mock_repository_data)
        )
        
        # Mock empty commits response
        respx.get("https://api.github.com/repos/testowner/test-repo/commits").mock(
            return_value=httpx.Response(200, json=[])
        )

        async with client:
            commits = await client.get_recent_commits("testowner", "test-repo")

            assert len(commits) == 0

    @pytest.mark.asyncio
    async def test_get_recent_commits_invalid_count(self, client):
        """Test get_recent_commits with invalid count values."""
        async with client:
            # Test count too low (zero)
            with pytest.raises(ValueError, match="Count must be a positive integer"):
                await client.get_recent_commits("testowner", "test-repo", count=0)
            
            # Test negative count
            with pytest.raises(ValueError, match="Count must be a positive integer"):
                await client.get_recent_commits("testowner", "test-repo", count=-1)

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_recent_commits_various_count_values(self, client, mock_repository_data):
        """Test get_recent_commits with various valid count values."""
        # Mock repository info
        respx.get("https://api.github.com/repos/testowner/test-repo").mock(
            return_value=httpx.Response(200, json=mock_repository_data)
        )
        
        # Mock commits response
        commits_data = [
            {
                "sha": f"abc123456789012345678901234567890123456{i:02d}",
                "commit": {
                    "message": f"Test commit {i}",
                    "author": {"date": "2024-01-15T10:30:00Z"}
                }
            }
            for i in range(5000)  # Generate enough commits for testing
        ]
        
        async with client:
            # Test various count values
            test_counts = [1, 100, 1000, 5000]
            
            for count in test_counts:
                # Mock the commits endpoint to return the requested number
                respx.get("https://api.github.com/repos/testowner/test-repo/commits").mock(
                    return_value=httpx.Response(200, json=commits_data[:count])
                )
                
                result = await client.get_recent_commits("testowner", "test-repo", count=count)
                assert len(result) == count
                
                # Verify each commit has the expected structure
                for i, commit in enumerate(result):
                    expected_full_sha = f"abc123456789012345678901234567890123456{i:02d}"
                    assert commit.short_sha == expected_full_sha[:7]  # First 7 characters
                    assert commit.message == f"Test commit {i}"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_recent_commits_api_error(self, client, mock_repository_data):
        """Test get_recent_commits with API error."""
        # Mock repository info
        respx.get("https://api.github.com/repos/testowner/test-repo").mock(
            return_value=httpx.Response(200, json=mock_repository_data)
        )
        
        # Mock API error
        respx.get("https://api.github.com/repos/testowner/test-repo/commits").mock(
            return_value=httpx.Response(404, json={"message": "Not Found"})
        )

        async with client:
            with pytest.raises(GitHubAPIError):
                await client.get_recent_commits("testowner", "test-repo")

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_recent_commits_with_long_message(self, client, mock_repository_data):
        """Test getting recent commits with long commit message."""
        long_message_commit = {
            "sha": "a" * 40,
            "commit": {
                "message": "This is a very long commit message that should be truncated because it exceeds the maximum length limit",
                "author": {
                    "name": "Test User",
                    "email": "test@example.com",
                    "date": "2023-01-01T00:00:00Z",
                },
                "committer": {
                    "name": "Test User",
                    "email": "test@example.com",
                    "date": "2023-01-01T00:00:00Z",
                },
            },
        }
        
        # Mock repository info
        respx.get("https://api.github.com/repos/testowner/test-repo").mock(
            return_value=httpx.Response(200, json=mock_repository_data)
        )
        
        # Mock commits endpoint
        respx.get("https://api.github.com/repos/testowner/test-repo/commits").mock(
            return_value=httpx.Response(200, json=[long_message_commit])
        )

        async with client:
            commits = await client.get_recent_commits("testowner", "test-repo", count=1)

            assert len(commits) == 1
            assert isinstance(commits[0], RecentCommit)
            assert commits[0].short_sha == "aaaaaaa"
            # The message should be truncated to 50 characters by default
            assert len(commits[0].message) <= 50
            # If the original message was longer than 47 chars, it should end with "..."
            original_message = "This is a very long commit message that should be truncated because it exceeds the maximum length limit"
            if len(original_message) > 47:
                assert commits[0].message.endswith("...")
            else:
                assert commits[0].message == original_message


class TestGitHubClientUserOperations:
    """Test user-related operations."""

    @pytest.fixture
    def client(self):
        """Create a test GitHub client."""
        config = GitHubConfig(token="ghp_1234567890abcdef1234567890abcdef12345678")
        return GitHubClient(config)

    @pytest.fixture
    def mock_user_data(self):
        """Mock user data from GitHub API."""
        return {
            "id": 12345,
            "login": "testuser",
            "name": "Test User",
            "email": "test@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
            "html_url": "https://github.com/testuser",
            "type": "User",
            "site_admin": False,
        }

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_user(self, client, mock_user_data):
        """Test getting user information."""
        respx.get("https://api.github.com/users/testuser").mock(
            return_value=httpx.Response(200, json=mock_user_data)
        )

        async with client:
            user = await client.get_user("testuser")

            assert isinstance(user, User)
            assert user.login == "testuser"
            assert user.name == "Test User"
            assert user.email == "test@example.com"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_authenticated_user(self, client, mock_user_data):
        """Test getting authenticated user information."""
        respx.get("https://api.github.com/user").mock(
            return_value=httpx.Response(200, json=mock_user_data)
        )

        async with client:
            user = await client.get_authenticated_user()

            assert isinstance(user, User)
            assert user.login == "testuser"

    @pytest.mark.asyncio
    @respx.mock
    async def test_test_authentication_success(self, client, mock_user_data):
        """Test successful authentication test."""
        respx.get("https://api.github.com/user").mock(
            return_value=httpx.Response(200, json=mock_user_data)
        )

        async with client:
            result = await client.test_authentication()
            assert result is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_test_authentication_failure(self, client):
        """Test failed authentication test."""
        respx.get("https://api.github.com/user").mock(
            return_value=httpx.Response(401, json={"message": "Bad credentials"})
        )

        async with client:
            result = await client.test_authentication()
            assert result is False


class TestGitHubClientUtilityOperations:
    """Test utility operations."""

    @pytest.fixture
    def client(self):
        """Create a test GitHub client."""
        config = GitHubConfig(token="ghp_1234567890abcdef1234567890abcdef12345678")
        return GitHubClient(config)

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_rate_limit(self, client):
        """Test getting rate limit information."""
        rate_limit_data = {
            "rate": {
                "limit": 5000,
                "remaining": 4999,
                "reset": 1640995200,
                "used": 1,
            }
        }

        respx.get("https://api.github.com/rate_limit").mock(
            return_value=httpx.Response(200, json=rate_limit_data)
        )

        async with client:
            result = await client.get_rate_limit()
            assert result == rate_limit_data

    @pytest.mark.asyncio
    @respx.mock
    async def test_check_rate_limit(self, client):
        """Test checking simplified rate limit status."""
        rate_limit_data = {
            "rate": {
                "limit": 5000,
                "remaining": 4999,
                "reset": 1640995200,
                "used": 1,
            }
        }

        respx.get("https://api.github.com/rate_limit").mock(
            return_value=httpx.Response(200, json=rate_limit_data)
        )

        async with client:
            result = await client.check_rate_limit()

            assert result["limit"] == 5000
            assert result["remaining"] == 4999
            assert result["reset"] == 1640995200
            assert result["used"] == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_repository_languages(self, client):
        """Test getting repository languages."""
        languages_data = {"Python": 12345, "JavaScript": 6789, "HTML": 1234}

        respx.get("https://api.github.com/repos/testowner/test-repo/languages").mock(
            return_value=httpx.Response(200, json=languages_data)
        )

        async with client:
            result = await client.get_repository_languages("testowner", "test-repo")
            assert result == languages_data

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_repository_topics(self, client):
        """Test getting repository topics."""
        topics_data = {"names": ["python", "web", "api"]}

        respx.get("https://api.github.com/repos/testowner/test-repo/topics").mock(
            return_value=httpx.Response(200, json=topics_data)
        )

        async with client:
            result = await client.get_repository_topics("testowner", "test-repo")
            assert result == ["python", "web", "api"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_repository_contributors(self, client):
        """Test getting repository contributors."""
        contributor_data = {
            "id": 12345,
            "login": "contributor1",
            "html_url": "https://github.com/contributor1",
            "contributions": 42,
        }

        respx.get("https://api.github.com/repos/testowner/test-repo/contributors").mock(
            return_value=httpx.Response(200, json=[contributor_data])
        )

        async with client:
            result = await client.get_repository_contributors("testowner", "test-repo")

            assert len(result) == 1
            assert isinstance(result[0], dict)
            assert result[0]["login"] == "contributor1"


    @pytest.mark.asyncio
    @respx.mock
    async def test_get_recent_commits_success(self, client):
        """Test successful recent commits fetching."""
        mock_repo_response = {
            "default_branch": "main",
            "owner": {"login": "testowner"},
            "name": "testrepo",
            "full_name": "testowner/testrepo",
            "url": "https://api.github.com/repos/testowner/testrepo",
            "html_url": "https://github.com/testowner/testrepo",
            "clone_url": "https://github.com/testowner/testrepo.git",
        }

        mock_commits_response = [
            {
                "sha": "a1b2c3d4e5f6789012345678901234567890abcd",
                "commit": {
                    "message": "Add user authentication system",
                    "author": {
                        "name": "John Doe",
                        "date": "2024-01-15T10:30:00Z"
                    }
                }
            },
            {
                "sha": "b2c3d4e5f6789012345678901234567890abcdef",
                "commit": {
                    "message": "Fix bug in login validation that was causing issues",
                    "author": {
                        "name": "Jane Smith",
                        "date": "2024-01-14T15:45:00Z"
                    }
                }
            }
        ]

        respx.get("https://api.github.com/repos/testowner/testrepo").mock(
            return_value=httpx.Response(200, json=mock_repo_response)
        )
        respx.get("https://api.github.com/repos/testowner/testrepo/commits").mock(
            return_value=httpx.Response(200, json=mock_commits_response)
        )

        async with client:
            commits = await client.get_recent_commits("testowner", "testrepo", count=2)

            assert len(commits) == 2
            assert commits[0].short_sha == "a1b2c3d"
            assert commits[0].message == "Add user authentication system"

            assert commits[1].short_sha == "b2c3d4e"
            # Message should be truncated to 50 characters max (47 chars + "...")
            # The original message is "Fix bug in login validation that was causing issues" (51 chars)
            # Truncated to 47 chars + "..." = "Fix bug in login validation that was causing is..."
            expected_truncated = "Fix bug in login validation that was causing is..."
            assert commits[1].message == expected_truncated
            assert len(commits[1].message) <= 50

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_recent_commits_with_branch(self, client):
        """Test recent commits fetching with specific branch."""
        mock_commits_response = [
            {
                "sha": "a1b2c3d4e5f6789012345678901234567890abcd",
                "commit": {
                    "message": "Feature branch commit",
                    "author": {
                        "name": "Developer",
                        "date": "2024-01-15T10:30:00Z"
                    }
                }
            }
        ]

        respx.get("https://api.github.com/repos/testowner/testrepo/commits").mock(
            return_value=httpx.Response(200, json=mock_commits_response)
        )

        async with client:
            commits = await client.get_recent_commits("testowner", "testrepo", count=1, branch="feature-branch")

            assert len(commits) == 1
            assert commits[0].short_sha == "a1b2c3d"
            assert commits[0].message == "Feature branch commit"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_recent_commits_empty_repository(self, client):
        """Test recent commits fetching from empty repository."""
        mock_repo_response = {
            "default_branch": "main",
            "owner": {"login": "testowner"},
            "name": "testrepo",
            "full_name": "testowner/testrepo",
            "url": "https://api.github.com/repos/testowner/testrepo",
            "html_url": "https://github.com/testowner/testrepo",
            "clone_url": "https://github.com/testowner/testrepo.git",
        }

        respx.get("https://api.github.com/repos/testowner/testrepo").mock(
            return_value=httpx.Response(200, json=mock_repo_response)
        )
        respx.get("https://api.github.com/repos/testowner/testrepo/commits").mock(
            return_value=httpx.Response(200, json=[])
        )

        async with client:
            commits = await client.get_recent_commits("testowner", "testrepo", count=5)

            assert len(commits) == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_recent_commits_fewer_than_requested(self, client):
        """Test recent commits when repository has fewer commits than requested."""
        mock_repo_response = {
            "default_branch": "main",
            "owner": {"login": "testowner"},
            "name": "testrepo",
            "full_name": "testowner/testrepo",
            "url": "https://api.github.com/repos/testowner/testrepo",
            "html_url": "https://github.com/testowner/testrepo",
            "clone_url": "https://github.com/testowner/testrepo.git",
        }

        mock_commits_response = [
            {
                "sha": "a1b2c3d4e5f6789012345678901234567890abcd",
                "commit": {
                    "message": "Initial commit",
                    "author": {
                        "name": "Developer",
                        "date": "2024-01-15T10:30:00Z"
                    }
                }
            }
        ]

        respx.get("https://api.github.com/repos/testowner/testrepo").mock(
            return_value=httpx.Response(200, json=mock_repo_response)
        )
        respx.get("https://api.github.com/repos/testowner/testrepo/commits").mock(
            return_value=httpx.Response(200, json=mock_commits_response)
        )

        async with client:
            commits = await client.get_recent_commits("testowner", "testrepo", count=5)

            assert len(commits) == 1
            assert commits[0].message == "Initial commit"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_recent_commits_message_truncation(self, client):
        """Test commit message truncation for long messages."""
        mock_repo_response = {
            "default_branch": "main",
            "owner": {"login": "testowner"},
            "name": "testrepo",
            "full_name": "testowner/testrepo",
            "url": "https://api.github.com/repos/testowner/testrepo",
            "html_url": "https://github.com/testowner/testrepo",
            "clone_url": "https://github.com/testowner/testrepo.git",
        }

        mock_commits_response = [
            {
                "sha": "a1b2c3d4e5f6789012345678901234567890abcd",
                "commit": {
                    "message": "This is a very long commit message that exceeds the 50 character limit and should be truncated",
                    "author": {
                        "name": "Developer",
                        "date": "2024-01-15T10:30:00Z"
                    }
                }
            },
            {
                "sha": "b2c3d4e5f6789012345678901234567890abcdef",
                "commit": {
                    "message": "Short message",
                    "author": {
                        "name": "Developer",
                        "date": "2024-01-14T15:45:00Z"
                    }
                }
            }
        ]

        respx.get("https://api.github.com/repos/testowner/testrepo").mock(
            return_value=httpx.Response(200, json=mock_repo_response)
        )
        respx.get("https://api.github.com/repos/testowner/testrepo/commits").mock(
            return_value=httpx.Response(200, json=mock_commits_response)
        )

        async with client:
            commits = await client.get_recent_commits("testowner", "testrepo", count=2)

            assert len(commits) == 2
            assert commits[0].message == "This is a very long commit message that exceeds..."
            assert len(commits[0].message) == 50
            assert commits[1].message == "Short message"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_recent_commits_multiline_message(self, client):
        """Test commit message handling for multiline messages."""
        mock_repo_response = {
            "default_branch": "main",
            "owner": {"login": "testowner"},
            "name": "testrepo",
            "full_name": "testowner/testrepo",
            "url": "https://api.github.com/repos/testowner/testrepo",
            "html_url": "https://github.com/testowner/testrepo",
            "clone_url": "https://github.com/testowner/testrepo.git",
        }

        mock_commits_response = [
            {
                "sha": "a1b2c3d4e5f6789012345678901234567890abcd",
                "commit": {
                    "message": "Add user authentication\n\nThis commit adds a complete user authentication system\nwith login, logout, and session management.",
                    "author": {
                        "name": "Developer",
                        "date": "2024-01-15T10:30:00Z"
                    }
                }
            }
        ]

        respx.get("https://api.github.com/repos/testowner/testrepo").mock(
            return_value=httpx.Response(200, json=mock_repo_response)
        )
        respx.get("https://api.github.com/repos/testowner/testrepo/commits").mock(
            return_value=httpx.Response(200, json=mock_commits_response)
        )

        async with client:
            commits = await client.get_recent_commits("testowner", "testrepo", count=1)

            assert len(commits) == 1
            assert commits[0].message == "Add user authentication This commit adds a com..."
            # Should handle multiline by joining with spaces and truncating

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_recent_commits_repository_not_found(self, client):
        """Test recent commits fetching when repository is not found."""
        respx.get("https://api.github.com/repos/nonexistent/repo").mock(
            return_value=httpx.Response(404, json={"message": "Not Found"})
        )

        async with client:
            with pytest.raises(GitHubAPIError) as exc_info:
                await client.get_recent_commits("nonexistent", "repo", count=5)

            assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_recent_commits_branch_not_found(self, client):
        """Test recent commits fetching when branch is not found."""
        respx.get("https://api.github.com/repos/testowner/testrepo/commits").mock(
            return_value=httpx.Response(404, json={"message": "Not Found"})
        )

        async with client:
            with pytest.raises(GitHubAPIError) as exc_info:
                await client.get_recent_commits("testowner", "testrepo", count=5, branch="nonexistent-branch")

            assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_recent_commits_api_error(self, client):
        """Test recent commits fetching with API error."""
        mock_repo_response = {
            "default_branch": "main",
            "owner": {"login": "testowner"},
            "name": "testrepo",
            "full_name": "testowner/testrepo",
            "url": "https://api.github.com/repos/testowner/testrepo",
            "html_url": "https://github.com/testowner/testrepo",
            "clone_url": "https://github.com/testowner/testrepo.git",
        }

        respx.get("https://api.github.com/repos/testowner/testrepo").mock(
            return_value=httpx.Response(200, json=mock_repo_response)
        )
        respx.get("https://api.github.com/repos/testowner/testrepo/commits").mock(
            return_value=httpx.Response(500, json={"message": "Internal Server Error"})
        )

        async with client:
            with pytest.raises(GitHubAPIError) as exc_info:
                await client.get_recent_commits("testowner", "testrepo", count=5)

            assert exc_info.value.status_code == 500


class TestRecentCommit:
    """Test cases for RecentCommit model."""

    def test_recent_commit_creation(self):
        """Test RecentCommit creation with valid data."""
        commit = RecentCommit(
            short_sha="abcdef1",
            message="Test commit message"
        )
        
        assert commit.short_sha == "abcdef1"
        assert commit.message == "Test commit message"

    def test_recent_commit_invalid_short_sha(self):
        """Test RecentCommit creation with invalid short SHA."""
        with pytest.raises(ValueError, match="Invalid short SHA format"):
            RecentCommit(
                short_sha="invalid",
                message="Test commit message"
            )

    def test_recent_commit_from_github_api(self):
        """Test creating RecentCommit from GitHub API data."""
        api_data = {
            "sha": "abcdef1234567890abcdef1234567890abcdef12",
            "commit": {
                "message": "Test commit message"
            }
        }
        
        commit = RecentCommit.from_github_api(api_data)
        
        assert commit.short_sha == "abcdef1"
        assert commit.message == "Test commit message"

    def test_recent_commit_from_github_api_long_message(self):
        """Test creating RecentCommit from GitHub API data with long message (no truncation)."""
        long_message = "This is a very long commit message that should be displayed in full without truncation because we want to show complete information"
        api_data = {
            "sha": "abcdef1234567890abcdef1234567890abcdef12",
            "commit": {
                "message": long_message
            }
        }
        
        commit = RecentCommit.from_github_api(api_data)
        
        assert commit.short_sha == "abcdef1"
        assert commit.message == long_message
        assert not commit.message.endswith("...")

    def test_recent_commit_from_github_api_multiline_message(self):
        """Test creating RecentCommit from GitHub API data with multiline message."""
        api_data = {
            "sha": "abcdef1234567890abcdef1234567890abcdef12",
            "commit": {
                "message": "First line\n\nSecond line\nThird line"
            }
        }
        
        commit = RecentCommit.from_github_api(api_data)
        
        assert commit.short_sha == "abcdef1"
        assert "\n" not in commit.message
        assert commit.message == "First line Second line Third line"
