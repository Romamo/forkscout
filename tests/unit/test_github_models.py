"""Unit tests for GitHub data models."""

from datetime import datetime

import pytest

from forklift.models.github import Commit, Fork, Repository, User


class TestUser:
    """Test cases for User model."""

    def test_user_creation_minimal(self):
        """Test User creation with minimal required fields."""
        user = User(
            login="testuser",
            html_url="https://github.com/testuser",
        )

        assert user.login == "testuser"
        assert user.html_url == "https://github.com/testuser"
        assert user.type == "User"
        assert user.site_admin is False
        assert user.id is None
        assert user.name is None
        assert user.email is None

    def test_user_creation_full(self):
        """Test User creation with all fields."""
        user = User(
            id=12345,
            login="testuser",
            name="Test User",
            email="test@example.com",
            avatar_url="https://avatars.githubusercontent.com/u/12345",
            html_url="https://github.com/testuser",
            type="User",
            site_admin=False,
        )

        assert user.id == 12345
        assert user.login == "testuser"
        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert user.avatar_url == "https://avatars.githubusercontent.com/u/12345"

    def test_user_login_validation(self):
        """Test User login validation."""
        # Valid logins
        valid_logins = ["user", "user123", "user-name", "user.name", "user_name"]
        for login in valid_logins:
            user = User(login=login, html_url="https://github.com/user")
            assert user.login == login

        # Invalid logins
        with pytest.raises((ValueError, Exception)):
            User(login="user@invalid", html_url="https://github.com/user")

    def test_user_email_validation(self):
        """Test User email validation."""
        # Valid email
        user = User(
            login="testuser",
            html_url="https://github.com/testuser",
            email="test@example.com",
        )
        assert user.email == "test@example.com"

        # Invalid email
        with pytest.raises((ValueError, Exception)):
            User(
                login="testuser",
                html_url="https://github.com/testuser",
                email="invalid-email",
            )

    def test_user_from_github_api(self):
        """Test User creation from GitHub API response."""
        api_data = {
            "id": 12345,
            "login": "testuser",
            "name": "Test User",
            "email": "test@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
            "html_url": "https://github.com/testuser",
            "type": "User",
            "site_admin": False,
        }

        user = User.from_github_api(api_data)

        assert user.id == 12345
        assert user.login == "testuser"
        assert user.name == "Test User"
        assert user.email == "test@example.com"


class TestRepository:
    """Test cases for Repository model."""

    def test_repository_creation_minimal(self):
        """Test Repository creation with minimal required fields."""
        repo = Repository(
            owner="testowner",
            name="testrepo",
            full_name="testowner/testrepo",
            url="https://api.github.com/repos/testowner/testrepo",
            html_url="https://github.com/testowner/testrepo",
            clone_url="https://github.com/testowner/testrepo.git",
        )

        assert repo.owner == "testowner"
        assert repo.name == "testrepo"
        assert repo.full_name == "testowner/testrepo"
        assert repo.default_branch == "main"
        assert repo.stars == 0
        assert repo.forks_count == 0

    def test_repository_creation_full(self):
        """Test Repository creation with all fields."""
        repo = Repository(
            id=12345,
            owner="testowner",
            name="testrepo",
            full_name="testowner/testrepo",
            url="https://api.github.com/repos/testowner/testrepo",
            html_url="https://github.com/testowner/testrepo",
            clone_url="https://github.com/testowner/testrepo.git",
            default_branch="develop",
            stars=100,
            forks_count=25,
            watchers_count=150,
            open_issues_count=5,
            size=1024,
            language="Python",
            description="A test repository",
            topics=["python", "testing"],
            license_name="MIT",
            is_private=False,
            is_fork=False,
            is_archived=False,
            is_disabled=False,
        )

        assert repo.id == 12345
        assert repo.stars == 100
        assert repo.language == "Python"
        assert repo.topics == ["python", "testing"]
        assert repo.license_name == "MIT"

    def test_repository_name_validation(self):
        """Test Repository name validation."""
        # Valid names
        valid_names = ["repo", "repo123", "repo-name", "repo.name", "repo_name"]
        for name in valid_names:
            repo = Repository(
                owner="owner",
                name=name,
                full_name=f"owner/{name}",
                url=f"https://api.github.com/repos/owner/{name}",
                html_url=f"https://github.com/owner/{name}",
                clone_url=f"https://github.com/owner/{name}.git",
            )
            assert repo.name == name

        # Invalid names
        with pytest.raises((ValueError, Exception)):
            Repository(
                owner="owner",
                name="repo@invalid",
                full_name="owner/repo@invalid",
                url="https://api.github.com/repos/owner/repo",
                html_url="https://github.com/owner/repo",
                clone_url="https://github.com/owner/repo.git",
            )

        # Names starting/ending with period
        with pytest.raises((ValueError, Exception)):
            Repository(
                owner="owner",
                name=".repo",
                full_name="owner/.repo",
                url="https://api.github.com/repos/owner/repo",
                html_url="https://github.com/owner/repo",
                clone_url="https://github.com/owner/repo.git",
            )

    def test_repository_url_validation(self):
        """Test Repository URL validation."""
        # Invalid URL
        with pytest.raises((ValueError, Exception)):
            Repository(
                owner="owner",
                name="repo",
                full_name="owner/repo",
                url="invalid-url",
                html_url="https://github.com/owner/repo",
                clone_url="https://github.com/owner/repo.git",
            )

    def test_repository_full_name_consistency(self):
        """Test Repository full_name consistency validation."""
        # Inconsistent full_name
        with pytest.raises((ValueError, Exception)):
            Repository(
                owner="owner",
                name="repo",
                full_name="different/name",
                url="https://api.github.com/repos/owner/repo",
                html_url="https://github.com/owner/repo",
                clone_url="https://github.com/owner/repo.git",
            )

    def test_repository_from_github_api(self):
        """Test Repository creation from GitHub API response."""
        api_data = {
            "id": 12345,
            "name": "testrepo",
            "full_name": "testowner/testrepo",
            "owner": {"login": "testowner"},
            "url": "https://api.github.com/repos/testowner/testrepo",
            "html_url": "https://github.com/testowner/testrepo",
            "clone_url": "https://github.com/testowner/testrepo.git",
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

        repo = Repository.from_github_api(api_data)

        assert repo.id == 12345
        assert repo.owner == "testowner"
        assert repo.name == "testrepo"
        assert repo.stars == 100
        assert repo.language == "Python"
        assert repo.license_name == "MIT"
        assert isinstance(repo.created_at, datetime)

    def test_repository_to_dict(self):
        """Test Repository serialization to dictionary."""
        repo = Repository(
            owner="testowner",
            name="testrepo",
            full_name="testowner/testrepo",
            url="https://api.github.com/repos/testowner/testrepo",
            html_url="https://github.com/testowner/testrepo",
            clone_url="https://github.com/testowner/testrepo.git",
            stars=100,
        )

        repo_dict = repo.to_dict()

        assert repo_dict["owner"] == "testowner"
        assert repo_dict["name"] == "testrepo"
        assert repo_dict["stars"] == 100
        assert "id" not in repo_dict  # None values excluded


class TestCommit:
    """Test cases for Commit model."""

    def test_commit_creation_minimal(self):
        """Test Commit creation with minimal required fields."""
        user = User(login="testuser", html_url="https://github.com/testuser")
        commit = Commit(
            sha="a" * 40,
            message="Test commit",
            author=user,
            date=datetime.now(),
        )

        assert commit.sha == "a" * 40
        assert commit.message == "Test commit"
        assert commit.author == user
        assert commit.additions == 0
        assert commit.deletions == 0
        assert commit.total_changes == 0
        assert commit.is_merge is False

    def test_commit_sha_validation(self):
        """Test Commit SHA validation."""
        user = User(login="testuser", html_url="https://github.com/testuser")

        # Valid SHA
        commit = Commit(
            sha="a" * 40,
            message="Test commit",
            author=user,
            date=datetime.now(),
        )
        assert commit.sha == "a" * 40

        # Invalid SHA - too short
        with pytest.raises((ValueError, Exception)):  # Pydantic validation error
            Commit(
                sha="abc123",
                message="Test commit",
                author=user,
                date=datetime.now(),
            )

        # Invalid SHA - invalid characters
        with pytest.raises((ValueError, Exception)):  # Pydantic validation error
            Commit(
                sha="g" * 40,
                message="Test commit",
                author=user,
                date=datetime.now(),
            )

    def test_commit_total_changes_calculation(self):
        """Test automatic calculation of total changes."""
        user = User(login="testuser", html_url="https://github.com/testuser")
        commit = Commit(
            sha="a" * 40,
            message="Test commit",
            author=user,
            date=datetime.now(),
            additions=10,
            deletions=5,
        )

        assert commit.total_changes == 15

    def test_commit_merge_detection(self):
        """Test automatic merge commit detection."""
        user = User(login="testuser", html_url="https://github.com/testuser")

        # Regular commit
        commit = Commit(
            sha="a" * 40,
            message="Test commit",
            author=user,
            date=datetime.now(),
            parents=["b" * 40],
        )
        assert commit.is_merge is False

        # Merge commit
        merge_commit = Commit(
            sha="a" * 40,
            message="Merge branch 'feature'",
            author=user,
            date=datetime.now(),
            parents=["b" * 40, "c" * 40],
        )
        assert merge_commit.is_merge is True

    def test_commit_type_detection(self):
        """Test commit type detection based on message."""
        user = User(login="testuser", html_url="https://github.com/testuser")

        test_cases = [
            ("fix: resolve bug", "fix"),
            ("feat: add new feature", "feature"),
            ("docs: update README", "docs"),
            ("add unit tests", "feature"),  # "add" maps to feature, not test
            ("refactor: clean up code", "refactor"),
            ("perf: optimize algorithm", "performance"),
            ("chore: update dependencies", "other"),
        ]

        for message, expected_type in test_cases:
            commit = Commit(
                sha="a" * 40,
                message=message,
                author=user,
                date=datetime.now(),
            )
            assert commit.get_commit_type() == expected_type

    def test_commit_significance(self):
        """Test commit significance detection."""
        user = User(login="testuser", html_url="https://github.com/testuser")

        # Significant commit
        significant_commit = Commit(
            sha="a" * 40,
            message="feat: add new feature",
            author=user,
            date=datetime.now(),
            additions=50,
            deletions=10,
        )
        assert significant_commit.is_significant() is True

        # Insignificant commit (too small)
        small_commit = Commit(
            sha="a" * 40,
            message="fix: typo",
            author=user,
            date=datetime.now(),
            additions=1,
            deletions=1,
        )
        assert small_commit.is_significant() is False

        # Merge commit (not significant)
        merge_commit = Commit(
            sha="a" * 40,
            message="Merge branch 'feature'",
            author=user,
            date=datetime.now(),
            additions=100,
            deletions=50,
            parents=["b" * 40, "c" * 40],
        )
        assert merge_commit.is_significant() is False

    def test_commit_from_github_api(self):
        """Test Commit creation from GitHub API response."""
        api_data = {
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
            "author": {
                "login": "testuser",
                "html_url": "https://github.com/testuser",
            },
            "stats": {"additions": 10, "deletions": 5},
            "files": [{"filename": "test.py"}, {"filename": "README.md"}],
            "parents": [{"sha": "b" * 40}],
        }

        commit = Commit.from_github_api(api_data)

        assert commit.sha == "a" * 40
        assert commit.message == "Test commit"
        assert commit.author.login == "testuser"
        assert commit.additions == 10
        assert commit.deletions == 5
        assert commit.files_changed == ["test.py", "README.md"]
        assert commit.verification_verified is True


class TestFork:
    """Test cases for Fork model."""

    def test_fork_creation(self):
        """Test Fork creation."""
        parent_repo = Repository(
            owner="original",
            name="repo",
            full_name="original/repo",
            url="https://api.github.com/repos/original/repo",
            html_url="https://github.com/original/repo",
            clone_url="https://github.com/original/repo.git",
        )

        fork_repo = Repository(
            owner="forker",
            name="repo",
            full_name="forker/repo",
            url="https://api.github.com/repos/forker/repo",
            html_url="https://github.com/forker/repo",
            clone_url="https://github.com/forker/repo.git",
            is_fork=True,
        )

        owner = User(login="forker", html_url="https://github.com/forker")

        fork = Fork(
            repository=fork_repo,
            parent=parent_repo,
            owner=owner,
            commits_ahead=5,
            commits_behind=2,
        )

        assert fork.repository == fork_repo
        assert fork.parent == parent_repo
        assert fork.owner == owner
        assert fork.commits_ahead == 5
        assert fork.commits_behind == 2
        assert fork.is_active is True
        assert fork.divergence_score == 0.0

    def test_fork_validation(self):
        """Test Fork validation rules."""
        parent_repo = Repository(
            owner="original",
            name="repo",
            full_name="original/repo",
            url="https://api.github.com/repos/original/repo",
            html_url="https://github.com/original/repo",
            clone_url="https://github.com/original/repo.git",
        )

        # Repository not marked as fork
        non_fork_repo = Repository(
            owner="forker",
            name="repo",
            full_name="forker/repo",
            url="https://api.github.com/repos/forker/repo",
            html_url="https://github.com/forker/repo",
            clone_url="https://github.com/forker/repo.git",
            is_fork=False,
        )

        owner = User(login="forker", html_url="https://github.com/forker")

        with pytest.raises((ValueError, Exception)):  # Pydantic validation error
            Fork(
                repository=non_fork_repo,
                parent=parent_repo,
                owner=owner,
            )

        # Fork same as parent - need to make it a fork first
        fork_repo = Repository(
            owner="original",
            name="repo",
            full_name="original/repo",
            url="https://api.github.com/repos/original/repo",
            html_url="https://github.com/original/repo",
            clone_url="https://github.com/original/repo.git",
            is_fork=True,
        )

        with pytest.raises((ValueError, Exception)):  # Pydantic validation error
            Fork(
                repository=fork_repo,
                parent=parent_repo,
                owner=owner,
            )

    def test_fork_activity_score(self):
        """Test Fork activity score calculation."""
        parent_repo = Repository(
            owner="original",
            name="repo",
            full_name="original/repo",
            url="https://api.github.com/repos/original/repo",
            html_url="https://github.com/original/repo",
            clone_url="https://github.com/original/repo.git",
        )

        fork_repo = Repository(
            owner="forker",
            name="repo",
            full_name="forker/repo",
            url="https://api.github.com/repos/forker/repo",
            html_url="https://github.com/forker/repo",
            clone_url="https://github.com/forker/repo.git",
            is_fork=True,
        )

        owner = User(login="forker", html_url="https://github.com/forker")

        # Recent activity (within 7 days)
        recent_fork = Fork(
            repository=fork_repo,
            parent=parent_repo,
            owner=owner,
            last_activity=datetime.utcnow(),
        )
        assert recent_fork.calculate_activity_score() == 1.0

        # No activity
        inactive_fork = Fork(
            repository=fork_repo,
            parent=parent_repo,
            owner=owner,
            last_activity=None,
        )
        assert inactive_fork.calculate_activity_score() == 0.0

    def test_fork_from_github_api(self):
        """Test Fork creation from GitHub API response."""
        parent_data = {
            "id": 1,
            "name": "repo",
            "full_name": "original/repo",
            "owner": {"login": "original"},
            "url": "https://api.github.com/repos/original/repo",
            "html_url": "https://github.com/original/repo",
            "clone_url": "https://github.com/original/repo.git",
            "fork": False,
        }

        fork_data = {
            "id": 2,
            "name": "repo",
            "full_name": "forker/repo",
            "owner": {"login": "forker", "html_url": "https://github.com/forker"},
            "url": "https://api.github.com/repos/forker/repo",
            "html_url": "https://github.com/forker/repo",
            "clone_url": "https://github.com/forker/repo.git",
            "fork": True,
            "pushed_at": "2023-01-01T00:00:00Z",
        }

        fork = Fork.from_github_api(fork_data, parent_data)

        assert fork.repository.full_name == "forker/repo"
        assert fork.parent.full_name == "original/repo"
        assert fork.owner.login == "forker"
        assert isinstance(fork.last_activity, datetime)
