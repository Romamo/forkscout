"""Unit tests for RepositoryAnalyzer explanation support."""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from forklift.analysis.repository_analyzer import RepositoryAnalyzer
from forklift.analysis.commit_explanation_engine import CommitExplanationEngine
from forklift.github.client import GitHubClient
from forklift.models import (
    Repository,
    Fork,
    User,
    Commit,
    CommitExplanation,
    CommitWithExplanation,
    CommitCategory,
    ImpactAssessment,
    CategoryType,
    ImpactLevel,
    MainRepoValue,
    AnalysisContext,
)


class TestRepositoryAnalyzerExplanations:
    """Test RepositoryAnalyzer explanation support."""

    def create_mock_commit_data(self, commits):
        """Create mock GitHub API commit data."""
        return {
            "commits": [
                {
                    "sha": commit.sha,
                    "commit": {
                        "message": commit.message,
                        "author": {"date": commit.date.isoformat() + "Z"},
                        "committer": {"date": commit.date.isoformat() + "Z"}
                    },
                    "author": {"login": commit.author.login, "html_url": commit.author.html_url},
                    "stats": {"additions": commit.additions, "deletions": commit.deletions},
                    "files": [{"filename": f} for f in commit.files_changed],
                    "parents": []
                }
                for commit in commits
            ]
        }

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        client = Mock(spec=GitHubClient)
        client.get_fork_comparison = AsyncMock()
        client.get_repository_contributors = AsyncMock()
        return client

    @pytest.fixture
    def mock_explanation_engine(self):
        """Create a mock explanation engine."""
        engine = Mock(spec=CommitExplanationEngine)
        engine.explain_commits_batch = Mock()
        engine.get_explanation_summary = Mock()
        return engine

    @pytest.fixture
    def sample_repository(self):
        """Create a sample repository."""
        return Repository(
            owner="testowner",
            name="testrepo",
            full_name="testowner/testrepo",
            url="https://api.github.com/repos/testowner/testrepo",
            html_url="https://github.com/testowner/testrepo",
            clone_url="https://github.com/testowner/testrepo.git",
            language="python",
            description="A test web application"
        )

    @pytest.fixture
    def sample_fork(self, sample_repository):
        """Create a sample fork."""
        fork_repo = Repository(
            owner="forkowner",
            name="testrepo",
            full_name="forkowner/testrepo",
            url="https://api.github.com/repos/forkowner/testrepo",
            html_url="https://github.com/forkowner/testrepo",
            clone_url="https://github.com/forkowner/testrepo.git",
            is_fork=True
        )
        
        user = User(
            login="forkowner",
            html_url="https://github.com/forkowner"
        )
        
        return Fork(
            repository=fork_repo,
            parent=sample_repository,
            owner=user
        )

    @pytest.fixture
    def sample_user(self):
        """Create a sample user."""
        return User(
            login="testuser",
            html_url="https://github.com/testuser"
        )

    @pytest.fixture
    def sample_commits(self, sample_user):
        """Create sample commits."""
        return [
            Commit(
                sha="a1b2c3d4e5f6789012345678901234567890abc1",
                message="feat: add user authentication system",
                author=sample_user,
                date=datetime.utcnow(),
                additions=100,
                deletions=20,
                files_changed=["auth.py", "user_service.py"]
            ),
            Commit(
                sha="b2c3d4e5f6a789012345678901234567890abc2d",
                message="fix: resolve login issue",
                author=sample_user,
                date=datetime.utcnow(),
                additions=15,
                deletions=5,
                files_changed=["auth.py"]
            )
        ]

    def test_analyzer_initialization_without_explanation_engine(self, mock_github_client):
        """Test analyzer initialization without explanation engine."""
        analyzer = RepositoryAnalyzer(mock_github_client)
        
        assert analyzer.github_client is mock_github_client
        assert analyzer.explanation_engine is None

    def test_analyzer_initialization_with_explanation_engine(
        self, mock_github_client, mock_explanation_engine
    ):
        """Test analyzer initialization with explanation engine."""
        analyzer = RepositoryAnalyzer(
            mock_github_client, 
            explanation_engine=mock_explanation_engine
        )
        
        assert analyzer.github_client is mock_github_client
        assert analyzer.explanation_engine is mock_explanation_engine

    @pytest.mark.asyncio
    async def test_analyze_fork_without_explanations(
        self, mock_github_client, sample_fork, sample_repository, sample_commits
    ):
        """Test fork analysis without explanations."""
        # Setup mocks
        mock_github_client.get_fork_comparison.return_value = {
            "commits": [
                {
                    "sha": commit.sha,
                    "commit": {
                        "message": commit.message,
                        "author": {"date": commit.date.isoformat() + "Z"},
                        "committer": {"date": commit.date.isoformat() + "Z"}
                    },
                    "author": {"login": commit.author.login},
                    "stats": {"additions": commit.additions, "deletions": commit.deletions},
                    "files": [{"filename": f} for f in commit.files_changed],
                    "parents": []
                }
                for commit in sample_commits
            ]
        }
        mock_github_client.get_repository_contributors.return_value = [{"login": "user1"}]
        
        analyzer = RepositoryAnalyzer(mock_github_client)
        
        # Analyze fork without explanations
        result = await analyzer.analyze_fork(sample_fork, sample_repository, explain=False)
        
        assert result.fork == sample_fork
        assert len(result.features) > 0
        assert result.commit_explanations is None
        assert result.explanation_summary is None

    @pytest.mark.asyncio
    async def test_analyze_fork_with_explanations_no_engine(
        self, mock_github_client, sample_fork, sample_repository, sample_commits
    ):
        """Test fork analysis with explanations requested but no engine available."""
        # Setup mocks
        mock_github_client.get_fork_comparison.return_value = {
            "commits": [
                {
                    "sha": commit.sha,
                    "commit": {
                        "message": commit.message,
                        "author": {"date": commit.date.isoformat() + "Z"},
                        "committer": {"date": commit.date.isoformat() + "Z"}
                    },
                    "author": {"login": commit.author.login},
                    "stats": {"additions": commit.additions, "deletions": commit.deletions},
                    "files": [{"filename": f} for f in commit.files_changed],
                    "parents": []
                }
                for commit in sample_commits
            ]
        }
        mock_github_client.get_repository_contributors.return_value = [{"login": "user1"}]
        
        analyzer = RepositoryAnalyzer(mock_github_client)  # No explanation engine
        
        # Analyze fork with explanations requested
        result = await analyzer.analyze_fork(sample_fork, sample_repository, explain=True)
        
        assert result.fork == sample_fork
        assert len(result.features) > 0
        assert result.commit_explanations is None
        assert result.explanation_summary is None

    @pytest.mark.asyncio
    async def test_analyze_fork_with_explanations_success(
        self, mock_github_client, mock_explanation_engine, sample_fork, 
        sample_repository, sample_commits
    ):
        """Test successful fork analysis with explanations."""
        # Setup GitHub client mocks
        mock_github_client.get_fork_comparison.return_value = {
            "commits": [
                {
                    "sha": commit.sha,
                    "commit": {
                        "message": commit.message,
                        "author": {"date": commit.date.isoformat() + "Z"},
                        "committer": {"date": commit.date.isoformat() + "Z"}
                    },
                    "author": {"login": commit.author.login},
                    "stats": {"additions": commit.additions, "deletions": commit.deletions},
                    "files": [{"filename": f} for f in commit.files_changed],
                    "parents": []
                }
                for commit in sample_commits
            ]
        }
        mock_github_client.get_repository_contributors.return_value = [{"login": "user1"}]
        
        # Setup explanation engine mocks
        mock_explanations = [
            CommitExplanation(
                commit_sha=sample_commits[0].sha,
                category=CommitCategory(
                    category_type=CategoryType.FEATURE,
                    confidence=0.9,
                    reasoning="Test category"
                ),
                impact_assessment=ImpactAssessment(
                    impact_level=ImpactLevel.HIGH,
                    change_magnitude=3.0,
                    file_criticality=0.8,
                    reasoning="Test impact"
                ),
                what_changed="user authentication system",
                main_repo_value=MainRepoValue.YES,
                explanation="This commit adds user authentication system. This could be useful for the main repository."
            )
        ]
        
        mock_commit_with_explanations = [
            CommitWithExplanation(commit=sample_commits[0], explanation=mock_explanations[0]),
            CommitWithExplanation(commit=sample_commits[1], explanation=None, explanation_error="Test error")
        ]
        
        mock_explanation_engine.explain_commits_batch.return_value = mock_commit_with_explanations
        mock_explanation_engine.get_explanation_summary.return_value = "Test summary"
        
        analyzer = RepositoryAnalyzer(mock_github_client, explanation_engine=mock_explanation_engine)
        
        # Analyze fork with explanations
        result = await analyzer.analyze_fork(sample_fork, sample_repository, explain=True)
        
        assert result.fork == sample_fork
        assert len(result.features) > 0
        assert result.commit_explanations == mock_explanations
        assert result.explanation_summary == "Test summary"
        
        # Verify explanation engine was called
        mock_explanation_engine.explain_commits_batch.assert_called_once()
        mock_explanation_engine.get_explanation_summary.assert_called_once_with(mock_explanations)

    @pytest.mark.asyncio
    async def test_analyze_commits_with_explanations(
        self, mock_github_client, mock_explanation_engine, sample_fork, 
        sample_repository, sample_commits
    ):
        """Test the _analyze_commits_with_explanations method."""
        # Setup explanation engine mocks
        mock_explanations = [
            CommitExplanation(
                commit_sha=sample_commits[0].sha,
                category=CommitCategory(
                    category_type=CategoryType.FEATURE,
                    confidence=0.9,
                    reasoning="Test category"
                ),
                impact_assessment=ImpactAssessment(
                    impact_level=ImpactLevel.HIGH,
                    change_magnitude=3.0,
                    file_criticality=0.8,
                    reasoning="Test impact"
                ),
                what_changed="user authentication system",
                main_repo_value=MainRepoValue.YES,
                explanation="This commit adds user authentication system."
            )
        ]
        
        mock_commit_with_explanations = [
            CommitWithExplanation(commit=sample_commits[0], explanation=mock_explanations[0]),
            CommitWithExplanation(commit=sample_commits[1], explanation=None, explanation_error="Test error")
        ]
        
        mock_explanation_engine.explain_commits_batch.return_value = mock_commit_with_explanations
        mock_explanation_engine.get_explanation_summary.return_value = "Test summary"
        
        analyzer = RepositoryAnalyzer(mock_github_client, explanation_engine=mock_explanation_engine)
        
        # Call the method directly
        explanations, summary = await analyzer._analyze_commits_with_explanations(
            sample_commits, sample_fork, sample_repository
        )
        
        assert explanations == mock_explanations
        assert summary == "Test summary"
        
        # Verify the explanation engine was called with proper context
        call_args = mock_explanation_engine.explain_commits_batch.call_args
        commits_arg, context_arg = call_args[0]
        
        assert commits_arg == sample_commits
        assert isinstance(context_arg, AnalysisContext)
        assert context_arg.repository == sample_repository
        assert context_arg.fork == sample_fork
        assert context_arg.project_type == "web"  # Inferred from description
        assert context_arg.main_language == "python"

    def test_infer_project_type_web(self, mock_github_client):
        """Test project type inference for web projects."""
        analyzer = RepositoryAnalyzer(mock_github_client)
        
        repo = Repository(
            owner="test", name="test", full_name="test/test",
            url="https://api.github.com/repos/test/test",
            html_url="https://github.com/test/test",
            clone_url="https://github.com/test/test.git",
            description="A web application for users"
        )
        
        project_type = analyzer._infer_project_type(repo)
        assert project_type == "web"

    def test_infer_project_type_api(self, mock_github_client):
        """Test project type inference for API projects."""
        analyzer = RepositoryAnalyzer(mock_github_client)
        
        repo = Repository(
            owner="test", name="test", full_name="test/test",
            url="https://api.github.com/repos/test/test",
            html_url="https://github.com/test/test",
            clone_url="https://github.com/test/test.git",
            description="REST API backend service"
        )
        
        project_type = analyzer._infer_project_type(repo)
        assert project_type == "api"

    def test_infer_project_type_cli(self, mock_github_client):
        """Test project type inference for CLI projects."""
        analyzer = RepositoryAnalyzer(mock_github_client)
        
        repo = Repository(
            owner="test", name="test", full_name="test/test",
            url="https://api.github.com/repos/test/test",
            html_url="https://github.com/test/test",
            clone_url="https://github.com/test/test.git",
            description="Command line tool for developers"
        )
        
        project_type = analyzer._infer_project_type(repo)
        assert project_type == "cli"

    def test_infer_project_type_library(self, mock_github_client):
        """Test project type inference for library projects."""
        analyzer = RepositoryAnalyzer(mock_github_client)
        
        repo = Repository(
            owner="test", name="test", full_name="test/test",
            url="https://api.github.com/repos/test/test",
            html_url="https://github.com/test/test",
            clone_url="https://github.com/test/test.git",
            description="Python library for data processing"
        )
        
        project_type = analyzer._infer_project_type(repo)
        assert project_type == "library"

    def test_infer_project_type_unknown(self, mock_github_client):
        """Test project type inference for unknown projects."""
        analyzer = RepositoryAnalyzer(mock_github_client)
        
        repo = Repository(
            owner="test", name="test", full_name="test/test",
            url="https://api.github.com/repos/test/test",
            html_url="https://github.com/test/test",
            clone_url="https://github.com/test/test.git",
            description="Some random project"
        )
        
        project_type = analyzer._infer_project_type(repo)
        assert project_type is None

    def test_infer_project_type_no_description(self, mock_github_client):
        """Test project type inference with no description."""
        analyzer = RepositoryAnalyzer(mock_github_client)
        
        repo = Repository(
            owner="test", name="test", full_name="test/test",
            url="https://api.github.com/repos/test/test",
            html_url="https://github.com/test/test",
            clone_url="https://github.com/test/test.git",
            description=None
        )
        
        project_type = analyzer._infer_project_type(repo)
        assert project_type is None

    def test_identify_critical_files_frequency_based(self, mock_github_client, sample_user):
        """Test critical file identification based on modification frequency."""
        analyzer = RepositoryAnalyzer(mock_github_client)
        
        commits = [
            Commit(
                sha=f"a{i}b2c3d4e5f6789012345678901234567890abc{i}",
                message=f"commit {i}",
                author=sample_user,
                date=datetime.utcnow(),
                files_changed=["main.py", "utils.py"] if i < 3 else ["other.py"]
            )
            for i in range(5)
        ]
        
        critical_files = analyzer._identify_critical_files(commits)
        
        # main.py and utils.py should be identified as critical (modified in 3/5 commits = 60%)
        assert "main.py" in critical_files
        assert "utils.py" in critical_files

    def test_identify_critical_files_pattern_based(self, mock_github_client, sample_user):
        """Test critical file identification based on patterns."""
        analyzer = RepositoryAnalyzer(mock_github_client)
        
        commits = [
            Commit(
                sha="a1b2c3d4e5f6789012345678901234567890abc1",
                message="update config",
                author=sample_user,
                date=datetime.utcnow(),
                files_changed=["config.py", "setup.py", "__init__.py"]
            )
        ]
        
        critical_files = analyzer._identify_critical_files(commits)
        
        # All files should be identified as critical due to patterns
        assert "config.py" in critical_files
        assert "setup.py" in critical_files
        assert "__init__.py" in critical_files

    def test_identify_critical_files_empty_commits(self, mock_github_client):
        """Test critical file identification with empty commits."""
        analyzer = RepositoryAnalyzer(mock_github_client)
        
        critical_files = analyzer._identify_critical_files([])
        
        assert critical_files == []

    @pytest.mark.asyncio
    async def test_analyze_fork_no_commits(
        self, mock_github_client, mock_explanation_engine, sample_fork, sample_repository
    ):
        """Test fork analysis with no unique commits."""
        # Setup mocks to return no commits
        mock_github_client.get_fork_comparison.return_value = {"commits": []}
        
        analyzer = RepositoryAnalyzer(mock_github_client, explanation_engine=mock_explanation_engine)
        
        # Analyze fork with explanations
        result = await analyzer.analyze_fork(sample_fork, sample_repository, explain=True)
        
        assert result.fork == sample_fork
        assert result.features == []
        assert result.commit_explanations is None
        assert result.explanation_summary is None
        
        # Explanation engine should not be called
        mock_explanation_engine.explain_commits_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_analyze_commits_with_explanations_no_engine(
        self, mock_github_client, sample_fork, sample_repository, sample_commits
    ):
        """Test _analyze_commits_with_explanations with no engine."""
        analyzer = RepositoryAnalyzer(mock_github_client)  # No explanation engine
        
        explanations, summary = await analyzer._analyze_commits_with_explanations(
            sample_commits, sample_fork, sample_repository
        )
        
        assert explanations == []
        assert summary == "No explanation engine available"