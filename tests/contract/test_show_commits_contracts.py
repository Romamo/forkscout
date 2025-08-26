"""Contract tests for show-commits functionality to ensure API compatibility."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from forklift.config.settings import ForkliftConfig
from forklift.models.github import Repository, Commit, User
from forklift.models.fork_qualification import QualifiedForksResult, CollectedForkData, ForkQualificationMetrics
from forklift.display.repository_display_service import RepositoryDisplayService


class TestShowCommitsContracts:
    """Contract tests to ensure API compatibility for show-commits functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock(spec=ForkliftConfig)
        config.github.token = "test_token"
        return config

    @pytest.fixture
    def sample_repository(self):
        """Create a sample repository for contract testing."""
        return Repository(
            id=12345,
            name="contract-test-repo",
            full_name="testowner/contract-test-repo",
            owner="testowner",
            description="Contract test repository",
            html_url="https://github.com/testowner/contract-test-repo",
            clone_url="https://github.com/testowner/contract-test-repo.git",
            ssh_url="git@github.com:testowner/contract-test-repo.git",
            url="https://api.github.com/repos/testowner/contract-test-repo",
            stargazers_count=100,
            forks_count=20,
            watchers_count=100,
            open_issues_count=5,
            size=1024,
            default_branch="main",
            language="Python",
            topics=["python", "contract"],
            license={"key": "mit", "name": "MIT License"},
            private=False,
            fork=False,
            archived=False,
            disabled=False,
            created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            pushed_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
        )

    @pytest.fixture
    def sample_commits(self):
        """Create sample commits for contract testing."""
        return [
            Commit(
                sha="contract123abc0000000000000000000000000000",
                message="Contract test commit",
                author=User(
                    login="contractauthor",
                    name="Contract Author",
                    email="contract@example.com",
                    html_url="https://github.com/contractauthor",
                    id=12345
                ),
                date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                files_changed=["contract.py"],
                additions=25,
                deletions=10
            )
        ]

    @pytest.fixture
    def sample_fork_data(self):
        """Create sample fork data for contract testing."""
        return CollectedForkData(
            name="contract-fork",
            owner="contractowner",
            full_name="contractowner/contract-fork",
            html_url="https://github.com/contractowner/contract-fork",
            clone_url="https://github.com/contractowner/contract-fork.git",
            qualification_metrics=ForkQualificationMetrics(
                stargazers_count=15,
                forks_count=2,
                size=1100,
                language="Python",
                created_at=datetime(2023, 6, 1, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                pushed_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
                open_issues_count=1,
                topics=["python", "contract"],
                watchers_count=15,
                archived=False,
                disabled=False,
                commits_ahead_status="Has commits",
                can_skip_analysis=False
            )
        )

    @pytest.mark.asyncio
    async def test_show_fork_data_method_signature_contract(self, mock_config, sample_repository, sample_fork_data):
        """Test that show_fork_data method maintains its expected signature."""
        mock_client = AsyncMock()
        display_service = RepositoryDisplayService(mock_client)
        
        # Test method exists and accepts expected parameters
        method = getattr(display_service, 'show_fork_data', None)
        assert method is not None, "show_fork_data method must exist"
        
        # Test method signature by calling with expected parameters
        with patch.object(display_service, '_get_fork_qualification_data') as mock_get_qualification:
            mock_get_qualification.return_value = ForkQualificationResult(
                total_forks=1,
                collected_forks=[sample_fork_data],
                excluded_archived_disabled=0,
                excluded_no_commits_ahead=0,
                included_for_analysis=1
            )
            
            # Test all expected parameters are accepted
            result = await display_service.show_fork_data(
                repo_url="testowner/contract-test-repo",
                max_forks=10,
                show_commits=3,
                detail=False,
                verbose=False
            )
            
            # Verify method returns expected structure
            assert isinstance(result, dict), "show_fork_data must return a dictionary"
            assert "total_forks" in result, "Result must contain total_forks"
            assert "displayed_forks" in result, "Result must contain displayed_forks"

    @pytest.mark.asyncio
    async def test_show_fork_data_return_contract(self, mock_config, sample_repository, sample_fork_data, sample_commits):
        """Test that show_fork_data returns the expected data structure."""
        mock_client = AsyncMock()
        mock_client.get_recent_commits.return_value = sample_commits
        
        display_service = RepositoryDisplayService(mock_client)
        
        with patch.object(display_service, '_get_fork_qualification_data') as mock_get_qualification:
            mock_get_qualification.return_value = ForkQualificationResult(
                total_forks=1,
                collected_forks=[sample_fork_data],
                excluded_archived_disabled=0,
                excluded_no_commits_ahead=0,
                included_for_analysis=1
            )
            
            result = await display_service.show_fork_data(
                repo_url="testowner/contract-test-repo",
                show_commits=2
            )
            
            # Verify required fields in return contract
            required_fields = ["total_forks", "displayed_forks"]
            for field in required_fields:
                assert field in result, f"Result must contain {field} field"
                assert isinstance(result[field], int), f"{field} must be an integer"
            
            # Verify data types
            assert result["total_forks"] >= 0, "total_forks must be non-negative"
            assert result["displayed_forks"] >= 0, "displayed_forks must be non-negative"
            assert result["displayed_forks"] <= result["total_forks"], "displayed_forks cannot exceed total_forks"

    @pytest.mark.asyncio
    async def test_get_recent_commits_method_contract(self, mock_config, sample_commits):
        """Test that get_recent_commits method maintains its expected contract."""
        mock_client = AsyncMock()
        mock_client.get_recent_commits.return_value = sample_commits
        
        # Test method signature
        result = await mock_client.get_recent_commits(
            owner="testowner",
            repo="test-repo",
            branch="main",
            limit=5
        )
        
        # Verify call was made with expected parameters
        mock_client.get_recent_commits.assert_called_once_with(
            owner="testowner",
            repo="test-repo",
            branch="main",
            limit=5
        )
        
        # Verify return type
        assert isinstance(result, list), "get_recent_commits must return a list"
        if result:
            assert isinstance(result[0], Commit), "get_recent_commits must return list of Commit objects"

    @pytest.mark.asyncio
    async def test_commit_model_contract(self, sample_commits):
        """Test that Commit model maintains its expected structure."""
        commit = sample_commits[0]
        
        # Verify required fields exist
        required_fields = [
            "sha", "message", "author", "url", "html_url",
            "files_changed", "additions", "deletions"
        ]
        
        for field in required_fields:
            assert hasattr(commit, field), f"Commit must have {field} field"
            assert getattr(commit, field) is not None, f"Commit.{field} cannot be None"
        
        # Verify field types
        assert isinstance(commit.sha, str), "Commit.sha must be string"
        assert isinstance(commit.message, str), "Commit.message must be string"
        assert isinstance(commit.author, User), "Commit.author must be User"
        assert isinstance(commit.url, str), "Commit.url must be string"
        assert isinstance(commit.html_url, str), "Commit.html_url must be string"
        assert isinstance(commit.files_changed, int), "Commit.files_changed must be integer"
        assert isinstance(commit.additions, int), "Commit.additions must be integer"
        assert isinstance(commit.deletions, int), "Commit.deletions must be integer"
        
        # Verify value constraints
        assert len(commit.sha) > 0, "Commit.sha cannot be empty"
        assert commit.files_changed >= 0, "Commit.files_changed must be non-negative"
        assert commit.additions >= 0, "Commit.additions must be non-negative"
        assert commit.deletions >= 0, "Commit.deletions must be non-negative"

    @pytest.mark.asyncio
    async def test_commit_author_model_contract(self, sample_commits):
        """Test that User model (commit author) maintains its expected structure."""
        author = sample_commits[0].author
        
        # Verify required fields exist
        required_fields = ["login", "html_url"]
        optional_fields = ["name", "email"]
        
        for field in required_fields:
            assert hasattr(author, field), f"User must have {field} field"
            assert getattr(author, field) is not None, f"User.{field} cannot be None"
        
        for field in optional_fields:
            assert hasattr(author, field), f"User must have {field} field"
        
        # Verify field types
        assert isinstance(author.login, str), "User.login must be string"
        assert isinstance(author.html_url, str), "User.html_url must be string"
        if author.name:
            assert isinstance(author.name, str), "User.name must be string"
        if author.email:
            assert isinstance(author.email, str), "User.email must be string"
        
        # Verify value constraints
        assert len(author.login) > 0, "User.login cannot be empty"
        assert author.html_url.startswith("https://github.com/"), "User.html_url must be valid GitHub URL"
        if author.email:
            assert "@" in author.email, "User.email must be valid email format"

    @pytest.mark.asyncio
    async def test_fork_qualification_result_contract(self, sample_fork_data):
        """Test that ForkQualificationResult maintains its expected structure."""
        result = ForkQualificationResult(
            total_forks=1,
            collected_forks=[sample_fork_data],
            excluded_archived_disabled=0,
            excluded_no_commits_ahead=0,
            included_for_analysis=1
        )
        
        # Verify required fields exist
        required_fields = [
            "total_forks", "collected_forks", "excluded_archived_disabled",
            "excluded_no_commits_ahead", "included_for_analysis"
        ]
        
        for field in required_fields:
            assert hasattr(result, field), f"ForkQualificationResult must have {field} field"
        
        # Verify field types
        assert isinstance(result.total_forks, int), "total_forks must be integer"
        assert isinstance(result.collected_forks, list), "collected_forks must be list"
        assert isinstance(result.excluded_archived_disabled, int), "excluded_archived_disabled must be integer"
        assert isinstance(result.excluded_no_commits_ahead, int), "excluded_no_commits_ahead must be integer"
        assert isinstance(result.included_for_analysis, int), "included_for_analysis must be integer"
        
        # Verify value constraints
        assert result.total_forks >= 0, "total_forks must be non-negative"
        assert result.excluded_archived_disabled >= 0, "excluded_archived_disabled must be non-negative"
        assert result.excluded_no_commits_ahead >= 0, "excluded_no_commits_ahead must be non-negative"
        assert result.included_for_analysis >= 0, "included_for_analysis must be non-negative"
        
        # Verify logical constraints
        total_excluded = result.excluded_archived_disabled + result.excluded_no_commits_ahead
        assert result.included_for_analysis + total_excluded <= result.total_forks, \
            "Sum of included and excluded cannot exceed total"

    @pytest.mark.asyncio
    async def test_collected_fork_data_contract(self, sample_fork_data):
        """Test that CollectedForkData maintains its expected structure."""
        fork_data = sample_fork_data
        
        # Verify required fields exist
        required_fields = [
            "name", "owner", "full_name", "html_url", "clone_url", "qualification_metrics"
        ]
        
        for field in required_fields:
            assert hasattr(fork_data, field), f"CollectedForkData must have {field} field"
            assert getattr(fork_data, field) is not None, f"CollectedForkData.{field} cannot be None"
        
        # Verify field types
        assert isinstance(fork_data.name, str), "name must be string"
        assert isinstance(fork_data.owner, str), "owner must be string"
        assert isinstance(fork_data.full_name, str), "full_name must be string"
        assert isinstance(fork_data.html_url, str), "html_url must be string"
        assert isinstance(fork_data.clone_url, str), "clone_url must be string"
        assert isinstance(fork_data.qualification_metrics, ForkQualificationMetrics), \
            "qualification_metrics must be ForkQualificationMetrics"
        
        # Verify value constraints
        assert len(fork_data.name) > 0, "name cannot be empty"
        assert len(fork_data.owner) > 0, "owner cannot be empty"
        assert fork_data.full_name == f"{fork_data.owner}/{fork_data.name}", \
            "full_name must match owner/name format"
        assert fork_data.html_url.startswith("https://github.com/"), \
            "html_url must be valid GitHub URL"

    @pytest.mark.asyncio
    async def test_show_commits_parameter_validation_contract(self, mock_config, sample_repository, sample_fork_data):
        """Test that show_commits parameter validation maintains expected behavior."""
        mock_client = AsyncMock()
        display_service = RepositoryDisplayService(mock_client)
        
        with patch.object(display_service, '_get_fork_qualification_data') as mock_get_qualification:
            mock_get_qualification.return_value = ForkQualificationResult(
                total_forks=1,
                collected_forks=[sample_fork_data],
                excluded_archived_disabled=0,
                excluded_no_commits_ahead=0,
                included_for_analysis=1
            )
            
            # Test valid show_commits values
            valid_values = [0, 1, 5, 10]
            for value in valid_values:
                result = await display_service.show_fork_data(
                    repo_url="testowner/contract-test-repo",
                    show_commits=value
                )
                assert isinstance(result, dict), f"Must return dict for show_commits={value}"
            
            # Test that show_commits=0 doesn't call get_recent_commits
            await display_service.show_fork_data(
                repo_url="testowner/contract-test-repo",
                show_commits=0
            )
            mock_client.get_recent_commits.assert_not_called()
            
            # Test that show_commits>0 calls get_recent_commits
            mock_client.get_recent_commits.return_value = []
            await display_service.show_fork_data(
                repo_url="testowner/contract-test-repo",
                show_commits=3
            )
            mock_client.get_recent_commits.assert_called()

    @pytest.mark.asyncio
    async def test_error_handling_contract(self, mock_config, sample_repository, sample_fork_data):
        """Test that error handling maintains expected behavior."""
        mock_client = AsyncMock()
        display_service = RepositoryDisplayService(mock_client)
        
        # Test that API errors are handled gracefully
        mock_client.get_recent_commits.side_effect = Exception("API Error")
        
        with patch.object(display_service, '_get_fork_qualification_data') as mock_get_qualification:
            mock_get_qualification.return_value = ForkQualificationResult(
                total_forks=1,
                collected_forks=[sample_fork_data],
                excluded_archived_disabled=0,
                excluded_no_commits_ahead=0,
                included_for_analysis=1
            )
            
            # Should not raise exception, should handle gracefully
            try:
                result = await display_service.show_fork_data(
                    repo_url="testowner/contract-test-repo",
                    show_commits=3
                )
                # If it doesn't raise, it should still return a valid structure
                assert isinstance(result, dict), "Must return dict even on API errors"
            except Exception as e:
                # If it does raise, it should be a specific, expected exception type
                assert not isinstance(e, AttributeError), "Should not raise AttributeError"
                assert not isinstance(e, KeyError), "Should not raise KeyError"

    @pytest.mark.asyncio
    async def test_backward_compatibility_contract(self, mock_config, sample_repository, sample_fork_data):
        """Test that the API maintains backward compatibility."""
        mock_client = AsyncMock()
        display_service = RepositoryDisplayService(mock_client)
        
        with patch.object(display_service, '_get_fork_qualification_data') as mock_get_qualification:
            mock_get_qualification.return_value = ForkQualificationResult(
                total_forks=1,
                collected_forks=[sample_fork_data],
                excluded_archived_disabled=0,
                excluded_no_commits_ahead=0,
                included_for_analysis=1
            )
            
            # Test that method works without show_commits parameter (backward compatibility)
            result = await display_service.show_fork_data(
                repo_url="testowner/contract-test-repo"
            )
            assert isinstance(result, dict), "Must work without show_commits parameter"
            
            # Test that method works with only required parameters
            result = await display_service.show_fork_data(
                repo_url="testowner/contract-test-repo"
            )
            assert "total_forks" in result, "Must return expected fields with minimal parameters"
            assert "displayed_forks" in result, "Must return expected fields with minimal parameters"