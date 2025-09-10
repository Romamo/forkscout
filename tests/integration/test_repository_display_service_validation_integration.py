"""Integration tests for repository display service validation summary functionality."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from io import StringIO

from forkscout.display.repository_display_service import RepositoryDisplayService
from forkscout.models.validation_handler import ValidationSummary, ValidationHandler
from forkscout.models.github import Repository
from forkscout.github.client import GitHubClient
from rich.console import Console


class TestRepositoryDisplayServiceValidationIntegration:
    """Integration tests for validation summary display functionality."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        client = AsyncMock(spec=GitHubClient)
        return client

    @pytest.fixture
    def display_service(self, mock_github_client):
        """Create a display service instance for testing."""
        return RepositoryDisplayService(
            github_client=mock_github_client,
            console=Console(file=StringIO(), width=80)
        )

    @pytest.fixture
    def sample_fork_data_with_validation_issues(self):
        """Create sample fork data that will cause validation issues."""
        return [
            {
                "id": 1,
                "name": "valid-fork",
                "full_name": "user1/valid-fork",
                "owner": {"login": "user1"},
                "url": "https://api.github.com/repos/user1/valid-fork",
                "html_url": "https://github.com/user1/valid-fork",
                "clone_url": "https://github.com/user1/valid-fork.git",
                "stargazers_count": 5,
                "forks_count": 2,
                "watchers_count": 5,
                "open_issues_count": 1,
                "size": 100,
                "language": "Python",
                "default_branch": "main",
                "private": False,
                "fork": True,
                "archived": False,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-02T00:00:00Z",
                "pushed_at": "2023-01-02T00:00:00Z"
            },
            {
                "id": 2,
                "name": "repo..with..periods",  # This will cause validation error
                "full_name": "user2/repo..with..periods",
                "owner": {"login": "user2"},
                "url": "https://api.github.com/repos/user2/repo..with..periods",
                "html_url": "https://github.com/user2/repo..with..periods",
                "clone_url": "https://github.com/user2/repo..with..periods.git",
                "stargazers_count": 3,
                "forks_count": 1,
                "watchers_count": 3,
                "open_issues_count": 0,
                "size": 50,
                "language": "JavaScript",
                "default_branch": "main",
                "private": False,
                "fork": True,
                "archived": False,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-02T00:00:00Z",
                "pushed_at": "2023-01-02T00:00:00Z"
            },
            {
                "id": 3,
                "name": "another-valid-fork",
                "full_name": "user3/another-valid-fork",
                "owner": {"login": "user3"},
                "url": "https://api.github.com/repos/user3/another-valid-fork",
                "html_url": "https://github.com/user3/another-valid-fork",
                "clone_url": "https://github.com/user3/another-valid-fork.git",
                "stargazers_count": 10,
                "forks_count": 5,
                "watchers_count": 10,
                "open_issues_count": 2,
                "size": 200,
                "language": "Go",
                "default_branch": "main",
                "private": False,
                "fork": True,
                "archived": False,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-02T00:00:00Z",
                "pushed_at": "2023-01-02T00:00:00Z"
            }
        ]

    @pytest.mark.asyncio
    async def test_collect_detailed_fork_data_with_validation_success(
        self, 
        display_service, 
        mock_github_client,
        sample_fork_data_with_validation_issues
    ):
        """Test collecting fork data with validation handling."""
        # Mock the fork list processor and data engine
        with patch('forklift.github.fork_list_processor.ForkListProcessor') as mock_processor_class, \
             patch('forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine') as mock_engine_class:
            
            # Setup mock processor
            mock_processor = AsyncMock()
            mock_processor.get_all_forks_list_data.return_value = sample_fork_data_with_validation_issues
            mock_processor_class.return_value = mock_processor
            
            # Setup mock data engine with graceful validation
            mock_engine = Mock()
            
            # Simulate validation handler behavior
            validation_handler = ValidationHandler()
            valid_repositories = []
            
            for fork_data in sample_fork_data_with_validation_issues:
                repo = validation_handler.safe_create_repository(fork_data)
                if repo:
                    valid_repositories.append(repo)
                    validation_handler.processed_count += 1
            
            validation_summary = validation_handler.get_summary()
            mock_engine.collect_fork_data.return_value = (valid_repositories, validation_summary)
            mock_engine_class.return_value = mock_engine
            
            # Test the method
            collected_forks, result_summary = await display_service.collect_detailed_fork_data_with_validation(
                "owner/repo"
            )
            
            # Verify results - all repositories should be processed successfully with relaxed validation
            assert len(collected_forks) == 3  # All repositories should be processed
            assert result_summary.processed == 3  # All processed successfully
            assert result_summary.skipped == 0  # No repositories skipped with relaxed validation
            assert len(result_summary.errors) == 0  # No validation errors with relaxed validation

    @pytest.mark.asyncio
    async def test_collect_detailed_fork_data_with_validation_no_forks(
        self, 
        display_service, 
        mock_github_client
    ):
        """Test collecting fork data when no forks are found."""
        # Mock the fork list processor to return empty list
        with patch('forklift.github.fork_list_processor.ForkListProcessor') as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor.get_all_forks_list_data.return_value = []
            mock_processor_class.return_value = mock_processor
            
            # Test the method
            collected_forks, validation_summary = await display_service.collect_detailed_fork_data_with_validation(
                "owner/repo"
            )
            
            # Verify results
            assert len(collected_forks) == 0
            assert validation_summary.processed == 0
            assert validation_summary.skipped == 0
            assert len(validation_summary.errors) == 0

    @pytest.mark.asyncio
    async def test_collect_detailed_fork_data_with_validation_error_handling(
        self, 
        display_service, 
        mock_github_client
    ):
        """Test error handling in fork data collection with validation."""
        # Mock the fork list processor to raise an exception
        with patch('forklift.github.fork_list_processor.ForkListProcessor') as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor.get_all_forks_list_data.side_effect = Exception("API Error")
            mock_processor_class.return_value = mock_processor
            
            # Test the method
            collected_forks, validation_summary = await display_service.collect_detailed_fork_data_with_validation(
                "owner/repo"
            )
            
            # Verify error handling
            assert len(collected_forks) == 0
            assert validation_summary.processed == 0
            assert validation_summary.skipped == 1
            assert len(validation_summary.errors) == 1
            assert "API Error" in validation_summary.errors[0]["error"]

    def test_convert_repository_to_collected_fork_data(self, display_service):
        """Test conversion of Repository to CollectedForkData format."""
        from datetime import datetime
        
        # Create a sample Repository object
        repository = Repository(
            id=123,
            name="test-repo",
            owner="test-owner",
            full_name="test-owner/test-repo",
            url="https://api.github.com/repos/test-owner/test-repo",
            html_url="https://github.com/test-owner/test-repo",
            clone_url="https://github.com/test-owner/test-repo.git",
            description="Test repository",
            language="Python",
            stars=10,
            forks_count=5,
            watchers_count=10,
            open_issues_count=2,
            size=100,
            default_branch="main",
            is_private=False,
            is_fork=True,
            is_archived=False,
            created_at=datetime(2023, 1, 1),
            updated_at=datetime(2023, 1, 2),
            pushed_at=datetime(2023, 1, 2)
        )
        
        # Convert to CollectedForkData format
        fork_data = display_service._convert_repository_to_collected_fork_data(repository)
        
        # Verify conversion
        assert fork_data.metrics.name == "test-repo"
        assert fork_data.metrics.owner == "test-owner"
        assert fork_data.metrics.full_name == "test-owner/test-repo"
        assert fork_data.metrics.html_url == "https://github.com/test-owner/test-repo"
        assert fork_data.metrics.stargazers_count == 10
        assert fork_data.metrics.forks_count == 5
        assert fork_data.metrics.language == "Python"
        assert fork_data.metrics.archived == False
        assert fork_data.metrics.fork == True

    def test_calculate_days_since_push(self, display_service):
        """Test calculation of days since last push."""
        from datetime import datetime, timedelta
        
        # Test with recent push
        recent_push = datetime.utcnow() - timedelta(days=5)
        days = display_service._calculate_days_since_push(recent_push)
        assert days == 5
        
        # Test with None push date
        days = display_service._calculate_days_since_push(None)
        assert days == float('inf')

    def test_can_skip_analysis(self, display_service):
        """Test determination of whether repository can skip analysis."""
        from datetime import datetime, timedelta
        
        # Create repository with created_at >= pushed_at (can skip)
        repo_can_skip = Repository(
            id=1,
            name="test",
            owner="owner",
            full_name="owner/test",
            url="https://api.github.com/repos/owner/test",
            html_url="https://github.com/owner/test",
            clone_url="https://github.com/owner/test.git",
            stars=0,
            forks_count=0,
            watchers_count=0,
            open_issues_count=0,
            size=0,
            default_branch="main",
            is_private=False,
            is_fork=True,
            is_archived=False,
            created_at=datetime(2023, 1, 2),
            updated_at=datetime(2023, 1, 2),
            pushed_at=datetime(2023, 1, 1)  # Earlier than created_at
        )
        
        assert display_service._can_skip_analysis(repo_can_skip) == True
        
        # Create repository with created_at < pushed_at (cannot skip)
        repo_cannot_skip = Repository(
            id=2,
            name="test2",
            owner="owner",
            full_name="owner/test2",
            url="https://api.github.com/repos/owner/test2",
            html_url="https://github.com/owner/test2",
            clone_url="https://github.com/owner/test2.git",
            stars=0,
            forks_count=0,
            watchers_count=0,
            open_issues_count=0,
            size=0,
            default_branch="main",
            is_private=False,
            is_fork=True,
            is_archived=False,
            created_at=datetime(2023, 1, 1),
            updated_at=datetime(2023, 1, 2),
            pushed_at=datetime(2023, 1, 2)  # Later than created_at
        )
        
        assert display_service._can_skip_analysis(repo_cannot_skip) == False

    @pytest.mark.asyncio
    async def test_end_to_end_validation_summary_display(
        self, 
        display_service, 
        mock_github_client,
        sample_fork_data_with_validation_issues
    ):
        """Test end-to-end validation summary display functionality."""
        # Mock the dependencies
        with patch('forklift.github.fork_list_processor.ForkListProcessor') as mock_processor_class, \
             patch('forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine') as mock_engine_class:
            
            # Setup mock processor
            mock_processor = AsyncMock()
            mock_processor.get_all_forks_list_data.return_value = sample_fork_data_with_validation_issues
            mock_processor_class.return_value = mock_processor
            
            # Setup mock data engine with real validation handler
            mock_engine = Mock()
            validation_handler = ValidationHandler()
            valid_repositories = []
            
            for fork_data in sample_fork_data_with_validation_issues:
                repo = validation_handler.safe_create_repository(fork_data)
                if repo:
                    valid_repositories.append(repo)
                    validation_handler.processed_count += 1
            
            validation_summary = validation_handler.get_summary()
            mock_engine.collect_fork_data.return_value = (valid_repositories, validation_summary)
            mock_engine_class.return_value = mock_engine
            
            # Capture console output
            output = StringIO()
            display_service.console = Console(file=output, width=80)
            
            # Test the end-to-end method
            result = await display_service.show_forks_with_validation_summary(
                "owner/repo",
                verbose=True
            )
            
            # Verify the results - with relaxed validation, consecutive periods are allowed
            assert result["total_forks"] == 3
            assert result["processed_forks"] == 3  # All processed with relaxed validation
            assert result["skipped_forks"] == 0  # None skipped with relaxed validation
            assert len(result["collected_forks"]) == 3
            
            # Verify the console output - no validation summary needed since all processed successfully
            output_text = output.getvalue()
            assert "Fork Analysis Results for owner/repo" in output_text
            assert "Successfully processed 3 forks" in output_text
            # No validation issues expected with relaxed validation for consecutive periods

    @pytest.mark.asyncio
    async def test_validation_summary_with_different_error_types(self, display_service, mock_github_client):
        """Test validation summary display with different types of validation errors."""
        # Create fork data with various validation issues
        problematic_fork_data = [
            {
                "id": 1,
                "name": "repo..consecutive..periods",
                "full_name": "user1/repo..consecutive..periods",
                "owner": {"login": "user1"},
                "url": "https://api.github.com/repos/user1/repo..consecutive..periods",
                "html_url": "https://github.com/user1/repo..consecutive..periods",
                "clone_url": "https://github.com/user1/repo..consecutive..periods.git",
                "stargazers_count": 1,
                "forks_count": 0,
                "watchers_count": 1,
                "open_issues_count": 0,
                "size": 10,
                "language": "Python",
                "default_branch": "main",
                "private": False,
                "fork": True,
                "archived": False,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-02T00:00:00Z",
                "pushed_at": "2023-01-02T00:00:00Z"
            },
            {
                "id": 2,
                "name": ".leading-period",
                "full_name": "user2/.leading-period",
                "owner": {"login": "user2"},
                "url": "https://api.github.com/repos/user2/.leading-period",
                "html_url": "https://github.com/user2/.leading-period",
                "clone_url": "https://github.com/user2/.leading-period.git",
                "stargazers_count": 2,
                "forks_count": 1,
                "watchers_count": 2,
                "open_issues_count": 0,
                "size": 20,
                "language": "JavaScript",
                "default_branch": "main",
                "private": False,
                "fork": True,
                "archived": False,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-02T00:00:00Z",
                "pushed_at": "2023-01-02T00:00:00Z"
            }
        ]
        
        # Mock the dependencies
        with patch('forklift.github.fork_list_processor.ForkListProcessor') as mock_processor_class, \
             patch('forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine') as mock_engine_class:
            
            # Setup mocks
            mock_processor = AsyncMock()
            mock_processor.get_all_forks_list_data.return_value = problematic_fork_data
            mock_processor_class.return_value = mock_processor
            
            mock_engine = Mock()
            validation_handler = ValidationHandler()
            
            # Process the problematic data
            for fork_data in problematic_fork_data:
                repo = validation_handler.safe_create_repository(fork_data)
                if repo:
                    validation_handler.processed_count += 1
            
            validation_summary = validation_handler.get_summary()
            mock_engine.collect_fork_data.return_value = ([], validation_summary)
            mock_engine_class.return_value = mock_engine
            
            # Capture console output
            output = StringIO()
            display_service.console = Console(file=output, width=80)
            
            # Test the method
            result = await display_service.show_forks_with_validation_summary(
                "owner/repo",
                verbose=True
            )
            
            # Verify that different error types are handled
            # With relaxed validation: consecutive periods allowed, leading periods still rejected
            output_text = output.getvalue()
            assert "Leadin" in output_text  # Leading period should still be rejected
            assert result["skipped_forks"] == 1  # Only leading period rejected
            assert result["processed_forks"] == 1  # Consecutive periods allowed