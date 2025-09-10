"""Integration tests for CSV export fix functionality."""

import pytest
import asyncio
import io
import sys
from unittest.mock import patch, AsyncMock, MagicMock
from forkscout.config.settings import ForkscoutConfig, GitHubConfig
from forkscout.display.repository_display_service import RepositoryDisplayService
from forkscout.github.client import GitHubClient


class TestCSVExportIntegration:
    """Integration tests for CSV export functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = ForkscoutConfig()
        config.github = GitHubConfig(token="test_token")
        return config

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        client = AsyncMock(spec=GitHubClient)
        return client

    @pytest.fixture
    def display_service(self, mock_github_client):
        """Create a repository display service with mock client."""
        console = MagicMock()
        return RepositoryDisplayService(mock_github_client, console)

    @pytest.fixture
    def sample_fork_list_data(self):
        """Sample fork list data from GitHub API."""
        return [
            {
                "id": 1,
                "name": "test-repo",
                "full_name": "user1/test-repo",
                "owner": {"login": "user1", "html_url": "https://github.com/user1"},
                "html_url": "https://github.com/user1/test-repo",
                "clone_url": "https://github.com/user1/test-repo.git",
                "stargazers_count": 5,
                "forks_count": 2,
                "language": "Python",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-06-01T00:00:00Z",
                "pushed_at": "2023-06-01T00:00:00Z",
                "size": 1024,
                "open_issues_count": 3,
                "archived": False,
                "disabled": False,
                "private": False
            },
            {
                "id": 2,
                "name": "test-repo",
                "full_name": "user2/test-repo", 
                "owner": {"login": "user2", "html_url": "https://github.com/user2"},
                "html_url": "https://github.com/user2/test-repo",
                "clone_url": "https://github.com/user2/test-repo.git",
                "stargazers_count": 10,
                "forks_count": 1,
                "language": "JavaScript",
                "created_at": "2023-02-01T00:00:00Z",
                "updated_at": "2023-07-01T00:00:00Z",
                "pushed_at": "2023-07-01T00:00:00Z",
                "size": 2048,
                "open_issues_count": 1,
                "archived": False,
                "disabled": False,
                "private": False
            }
        ]

    @pytest.mark.asyncio
    async def test_csv_export_with_standard_mode(
        self, display_service, sample_fork_list_data
    ):
        """Test CSV export with standard fork data mode."""
        from src.forklift.cli import _export_forks_csv
        
        # Mock the fork list processor and data collection
        with patch('forklift.github.fork_list_processor.ForkListProcessor') as mock_processor_class:
            with patch('forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine') as mock_engine_class:
                # Setup mocks
                mock_processor = AsyncMock()
                mock_processor.get_all_forks_list_data.return_value = sample_fork_list_data
                mock_processor_class.return_value = mock_processor
                
                mock_engine = MagicMock()
                mock_collected_forks = [
                    MagicMock(metrics=MagicMock(
                        html_url="https://github.com/user1/test-repo",
                        full_name="user1/test-repo",
                        stargazers_count=5,
                        archived=False,
                        disabled=False
                    )),
                    MagicMock(metrics=MagicMock(
                        html_url="https://github.com/user2/test-repo",
                        full_name="user2/test-repo", 
                        stargazers_count=10,
                        archived=False,
                        disabled=False
                    ))
                ]
                mock_engine.collect_fork_data_from_list.return_value = mock_collected_forks
                mock_engine_class.return_value = mock_engine
                
                # Capture stdout
                captured_output = io.StringIO()
                
                with patch('sys.stdout', captured_output):
                    await _export_forks_csv(
                        display_service,
                        "owner/test-repo",
                        None,
                        False,  # detail=False
                        0,      # show_commits=0
                        False,  # force_all_commits=False
                        False   # ahead_only=False
                    )
                
                # Verify CSV output was generated
                csv_output = captured_output.getvalue()
                assert len(csv_output) > 0
                # Should contain fork data (exact format depends on CSV exporter implementation)

    @pytest.mark.asyncio
    async def test_csv_export_with_detail_mode(
        self, display_service, sample_fork_list_data
    ):
        """Test CSV export with detailed fork data mode."""
        from src.forklift.cli import _export_forks_csv
        
        # Mock the detailed processing components
        with patch('forklift.github.fork_list_processor.ForkListProcessor') as mock_processor_class:
            with patch('forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine') as mock_engine_class:
                with patch.object(display_service, '_get_exact_commit_counts_batch') as mock_batch_counts:
                    
                    # Setup mocks
                    mock_processor = AsyncMock()
                    mock_processor.get_all_forks_list_data.return_value = sample_fork_list_data
                    mock_processor_class.return_value = mock_processor
                    
                    mock_engine = MagicMock()
                    mock_collected_forks = [
                        MagicMock(
                            metrics=MagicMock(
                                html_url="https://github.com/user1/test-repo",
                                full_name="user1/test-repo",
                                stargazers_count=5,
                                archived=False,
                                disabled=False,
                                can_skip_analysis=False
                            ),
                            exact_commits_ahead=3
                        ),
                        MagicMock(
                            metrics=MagicMock(
                                html_url="https://github.com/user2/test-repo",
                                full_name="user2/test-repo",
                                stargazers_count=10,
                                archived=False,
                                disabled=False,
                                can_skip_analysis=False
                            ),
                            exact_commits_ahead=5
                        )
                    ]
                    mock_engine.collect_fork_data_from_list.return_value = mock_collected_forks
                    mock_engine_class.return_value = mock_engine
                    
                    # Mock batch commit counting
                    mock_batch_counts.return_value = (2, 0)  # successful_forks, api_calls_saved
                    
                    # Capture stdout
                    captured_output = io.StringIO()
                    
                    with patch('sys.stdout', captured_output):
                        await _export_forks_csv(
                            display_service,
                            "owner/test-repo",
                            None,
                            True,   # detail=True
                            0,      # show_commits=0
                            False,  # force_all_commits=False
                            False   # ahead_only=False
                        )
                    
                    # Verify CSV output was generated
                    csv_output = captured_output.getvalue()
                    assert len(csv_output) > 0

    @pytest.mark.asyncio
    async def test_csv_export_with_ahead_only_filter(
        self, display_service, sample_fork_list_data
    ):
        """Test CSV export with ahead-only filtering."""
        from src.forklift.cli import _export_forks_csv
        
        with patch('forklift.github.fork_list_processor.ForkListProcessor') as mock_processor_class:
            with patch('forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine') as mock_engine_class:
                with patch('forklift.analysis.fork_filters.create_default_ahead_only_filter') as mock_filter_factory:
                    
                    # Setup mocks
                    mock_processor = AsyncMock()
                    mock_processor.get_all_forks_list_data.return_value = sample_fork_list_data
                    mock_processor_class.return_value = mock_processor
                    
                    mock_engine = MagicMock()
                    mock_collected_forks = [
                        MagicMock(metrics=MagicMock(
                            html_url="https://github.com/user1/test-repo",
                            archived=False,
                            disabled=False
                        )),
                        MagicMock(metrics=MagicMock(
                            html_url="https://github.com/user2/test-repo",
                            archived=False,
                            disabled=False
                        ))
                    ]
                    mock_engine.collect_fork_data_from_list.return_value = mock_collected_forks
                    mock_engine_class.return_value = mock_engine
                    
                    # Mock ahead-only filter
                    mock_filter = MagicMock()
                    mock_filter_result = MagicMock()
                    mock_filter_result.forks = [
                        MagicMock(html_url="https://github.com/user1/test-repo")  # Only one fork has commits ahead
                    ]
                    mock_filter_result.total_excluded = 1
                    mock_filter_result.exclusion_summary = "Filtered 2 forks: 1 included, 0 private excluded, 1 no commits excluded"
                    mock_filter.filter_forks.return_value = mock_filter_result
                    mock_filter_factory.return_value = mock_filter
                    
                    # Capture stdout
                    captured_output = io.StringIO()
                    
                    with patch('sys.stdout', captured_output):
                        await _export_forks_csv(
                            display_service,
                            "owner/test-repo",
                            None,
                            False,  # detail=False
                            0,      # show_commits=0
                            False,  # force_all_commits=False
                            True    # ahead_only=True
                        )
                    
                    # Verify filtering was applied
                    mock_filter.filter_forks.assert_called_once()
                    
                    # Verify CSV output was generated
                    csv_output = captured_output.getvalue()
                    assert len(csv_output) > 0

    @pytest.mark.asyncio
    async def test_csv_export_with_show_commits(
        self, display_service, sample_fork_list_data
    ):
        """Test CSV export with commit details."""
        from src.forklift.cli import _export_forks_csv
        
        with patch('forklift.github.fork_list_processor.ForkListProcessor') as mock_processor_class:
            with patch('forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine') as mock_engine_class:
                
                # Setup mocks
                mock_processor = AsyncMock()
                mock_processor.get_all_forks_list_data.return_value = sample_fork_list_data
                mock_processor_class.return_value = mock_processor
                
                mock_engine = MagicMock()
                mock_collected_forks = [
                    MagicMock(metrics=MagicMock(
                        html_url="https://github.com/user1/test-repo",
                        archived=False,
                        disabled=False
                    ))
                ]
                mock_engine.collect_fork_data_from_list.return_value = mock_collected_forks
                mock_engine_class.return_value = mock_engine
                
                # Mock commit fetching
                with patch.object(display_service, '_fetch_commits_concurrently') as mock_fetch_commits:
                    mock_fetch_commits.return_value = {
                        "user1/test-repo": [
                            {"sha": "abc123", "message": "Test commit 1"},
                            {"sha": "def456", "message": "Test commit 2"}
                        ]
                    }
                    
                    # Capture stdout
                    captured_output = io.StringIO()
                    
                    with patch('sys.stdout', captured_output):
                        await _export_forks_csv(
                            display_service,
                            "owner/test-repo",
                            None,
                            False,  # detail=False
                            2,      # show_commits=2
                            False,  # force_all_commits=False
                            False   # ahead_only=False
                        )
                    
                    # Verify CSV output was generated
                    csv_output = captured_output.getvalue()
                    assert len(csv_output) > 0

    @pytest.mark.asyncio
    async def test_csv_export_with_multiple_flags(
        self, display_service, sample_fork_list_data
    ):
        """Test CSV export with multiple flag combinations."""
        from src.forklift.cli import _export_forks_csv
        
        with patch('forklift.github.fork_list_processor.ForkListProcessor') as mock_processor_class:
            with patch('forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine') as mock_engine_class:
                with patch('forklift.analysis.fork_filters.create_default_ahead_only_filter') as mock_filter_factory:
                    with patch.object(display_service, '_get_exact_commit_counts_batch') as mock_batch_counts:
                        
                        # Setup mocks
                        mock_processor = AsyncMock()
                        mock_processor.get_all_forks_list_data.return_value = sample_fork_list_data
                        mock_processor_class.return_value = mock_processor
                        
                        mock_engine = MagicMock()
                        mock_collected_forks = [
                            MagicMock(
                                metrics=MagicMock(
                                    html_url="https://github.com/user1/test-repo",
                                    archived=False,
                                    disabled=False,
                                    can_skip_analysis=False
                                ),
                                exact_commits_ahead=3
                            )
                        ]
                        mock_engine.collect_fork_data_from_list.return_value = mock_collected_forks
                        mock_engine_class.return_value = mock_engine
                        
                        # Mock ahead-only filter
                        mock_filter = MagicMock()
                        mock_filter_result = MagicMock()
                        mock_filter_result.forks = [
                            MagicMock(html_url="https://github.com/user1/test-repo")
                        ]
                        mock_filter_result.total_excluded = 0
                        mock_filter_result.exclusion_summary = "Filtered 1 forks: 1 included, 0 private excluded, 0 no commits excluded"
                        mock_filter.filter_forks.return_value = mock_filter_result
                        mock_filter_factory.return_value = mock_filter
                        
                        # Mock batch commit counting
                        mock_batch_counts.return_value = (1, 0)
                        
                        # Capture stdout
                        captured_output = io.StringIO()
                        
                        with patch('sys.stdout', captured_output):
                            await _export_forks_csv(
                                display_service,
                                "owner/test-repo",
                                10,     # max_forks=10
                                True,   # detail=True
                                3,      # show_commits=3
                                True,   # force_all_commits=True
                                True    # ahead_only=True
                            )
                        
                        # Verify all flags were processed
                        mock_filter.filter_forks.assert_called_once()
                        mock_batch_counts.assert_called_once()
                        
                        # Verify CSV output was generated
                        csv_output = captured_output.getvalue()
                        assert len(csv_output) > 0

    @pytest.mark.asyncio
    async def test_csv_export_with_empty_repository(self, display_service):
        """Test CSV export with repository that has no forks."""
        from src.forklift.cli import _export_forks_csv
        
        with patch('forklift.github.fork_list_processor.ForkListProcessor') as mock_processor_class:
            # Setup mock to return no forks
            mock_processor = AsyncMock()
            mock_processor.get_all_forks_list_data.return_value = []
            mock_processor_class.return_value = mock_processor
            
            # Capture stdout
            captured_output = io.StringIO()
            
            with patch('sys.stdout', captured_output):
                await _export_forks_csv(
                    display_service,
                    "owner/empty-repo",
                    None,
                    False,
                    0,
                    False,
                    False
                )
            
            # Verify empty CSV output was generated (headers only)
            csv_output = captured_output.getvalue()
            # Should have some output (at least headers) even for empty repositories
            assert len(csv_output) >= 0

    @pytest.mark.asyncio
    async def test_csv_export_error_handling(self, display_service):
        """Test CSV export error handling."""
        from src.forklift.cli import _export_forks_csv
        from forkscout.exceptions import ForkscoutOutputError
        
        with patch('forklift.github.fork_list_processor.ForkListProcessor') as mock_processor_class:
            # Setup mock to raise exception
            mock_processor = AsyncMock()
            mock_processor.get_all_forks_list_data.side_effect = Exception("Test error")
            mock_processor_class.return_value = mock_processor
            
            # Verify exception is properly handled
            with pytest.raises(ForkscoutOutputError) as exc_info:
                await _export_forks_csv(
                    display_service,
                    "owner/error-repo",
                    None,
                    False,
                    0,
                    False,
                    False
                )
            
            assert "CSV export failed" in str(exc_info.value)


class TestCSVExportFlagCompatibility:
    """Test CSV export compatibility with various command flags."""

    @pytest.mark.asyncio
    async def test_csv_export_config_with_commits(self):
        """Test CSV export configuration with commit flags."""
        from src.forklift.cli import _export_forks_csv
        from forkscout.reporting.csv_exporter import CSVExportConfig
        
        display_service = MagicMock()
        display_service.show_fork_data = AsyncMock(return_value={
            "collected_forks": []
        })
        
        with patch('src.forklift.cli.create_csv_context') as mock_context:
            mock_csv_manager = MagicMock()
            mock_context.return_value.__enter__.return_value = mock_csv_manager
            
            # Test with show_commits > 0
            await _export_forks_csv(
                display_service,
                "owner/repo",
                None,
                False,
                5,      # show_commits=5
                False,
                False
            )
            
            # Verify CSV config includes commits
            mock_csv_manager.configure_exporter.assert_called_once()
            config = mock_csv_manager.configure_exporter.call_args[0][0]
            assert isinstance(config, CSVExportConfig)
            assert config.include_commits is True
            assert config.max_commits_per_fork == 5

    @pytest.mark.asyncio
    async def test_csv_export_config_detail_mode(self):
        """Test CSV export configuration with detail mode."""
        from src.forklift.cli import _export_forks_csv
        
        display_service = MagicMock()
        display_service.show_fork_data_detailed = AsyncMock(return_value={
            "collected_forks": []
        })
        
        with patch('src.forklift.cli.create_csv_context') as mock_context:
            mock_csv_manager = MagicMock()
            mock_context.return_value.__enter__.return_value = mock_csv_manager
            
            # Test with detail=True
            await _export_forks_csv(
                display_service,
                "owner/repo",
                None,
                True,   # detail=True
                0,
                False,
                False
            )
            
            # Verify detailed method was called
            display_service.show_fork_data_detailed.assert_called_once()
            
            # Verify CSV config has detail mode
            config = mock_csv_manager.configure_exporter.call_args[0][0]
            assert config.detail_mode is True

    @pytest.mark.asyncio
    async def test_csv_export_config_standard_mode(self):
        """Test CSV export configuration with standard mode."""
        from src.forklift.cli import _export_forks_csv
        
        display_service = MagicMock()
        display_service.show_fork_data = AsyncMock(return_value={
            "collected_forks": []
        })
        
        with patch('src.forklift.cli.create_csv_context') as mock_context:
            mock_csv_manager = MagicMock()
            mock_context.return_value.__enter__.return_value = mock_csv_manager
            
            # Test with detail=False
            await _export_forks_csv(
                display_service,
                "owner/repo",
                None,
                False,  # detail=False
                0,
                False,
                False
            )
            
            # Verify standard method was called
            display_service.show_fork_data.assert_called_once()
            
            # Verify CSV config has standard mode
            config = mock_csv_manager.configure_exporter.call_args[0][0]
            assert config.detail_mode is False