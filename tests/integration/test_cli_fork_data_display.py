"""Integration tests for CLI fork data display functionality."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from forklift.cli import _show_comprehensive_fork_data, _display_comprehensive_fork_data
from forklift.config.settings import ForkliftConfig, GitHubConfig
from forklift.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualificationStats,
    QualifiedForksResult,
)


@pytest.fixture
def mock_config():
    """Create a mock ForkliftConfig for testing."""
    config = ForkliftConfig()
    config.github = GitHubConfig(token="ghp_1234567890123456789012345678901234567890")
    return config


@pytest.fixture
def sample_fork_data():
    """Create sample fork data for testing."""
    from datetime import datetime, timedelta
    
    # Create sample fork metrics
    metrics1 = ForkQualificationMetrics(
        id=123456,
        name="test-fork-1",
        full_name="user1/test-fork-1",
        owner="user1",
        html_url="https://github.com/user1/test-fork-1",
        stargazers_count=5,
        forks_count=2,
        watchers_count=3,
        size=1024,
        language="Python",
        topics=["testing", "python"],
        open_issues_count=1,
        created_at=datetime.utcnow() - timedelta(days=30),
        updated_at=datetime.utcnow() - timedelta(days=1),
        pushed_at=datetime.utcnow() - timedelta(days=1),  # Recent push, so active
        archived=False,
        disabled=False,
        fork=True,
        license_key="mit",
        license_name="MIT License",
        description="A test fork with commits",
        homepage="https://example.com",
        default_branch="main"
    )
    
    metrics2 = ForkQualificationMetrics(
        id=789012,
        name="test-fork-2",
        full_name="user2/test-fork-2",
        owner="user2",
        html_url="https://github.com/user2/test-fork-2",
        stargazers_count=0,
        forks_count=0,
        watchers_count=0,
        size=512,
        language="JavaScript",
        topics=[],
        open_issues_count=0,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
        pushed_at=datetime(2024, 1, 1),  # Same as created_at, so no commits
        archived=False,
        disabled=False,
        fork=True,
        license_key=None,
        license_name=None,
        description=None,
        homepage=None,
        default_branch="main"
    )
    
    return [
        CollectedForkData(metrics=metrics1),
        CollectedForkData(metrics=metrics2)
    ]


@pytest.fixture
def sample_qualification_result(sample_fork_data):
    """Create a sample QualifiedForksResult for testing."""
    stats = QualificationStats(
        total_forks_discovered=2,
        forks_with_no_commits=1,
        forks_with_commits=1,
        archived_forks=0,
        disabled_forks=0,
        api_calls_made=2,
        api_calls_saved=0,
        processing_time_seconds=1.5
    )
    
    return QualifiedForksResult(
        repository_owner="testowner",
        repository_name="testrepo",
        repository_url="https://github.com/testowner/testrepo",
        collected_forks=sample_fork_data,
        stats=stats
    )


@pytest.mark.asyncio
async def test_show_comprehensive_fork_data_basic(mock_config, sample_fork_data):
    """Test basic comprehensive fork data display functionality."""
    with patch('forklift.cli.GitHubClient') as mock_github_client, \
         patch('forklift.github.fork_list_processor.ForkListProcessor') as mock_processor, \
         patch('forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine') as mock_engine, \
         patch('forklift.cli._display_comprehensive_fork_data') as mock_display, \
         patch('forklift.cli.validate_repository_url') as mock_validate:
        
        # Setup mocks
        mock_validate.return_value = ("testowner", "testrepo")
        
        mock_client_instance = AsyncMock()
        mock_github_client.return_value.__aenter__.return_value = mock_client_instance
        
        mock_processor_instance = AsyncMock()
        mock_processor.return_value = mock_processor_instance
        mock_processor_instance.get_all_forks_list_data.return_value = [
            {"id": 123456, "name": "test-fork-1", "full_name": "user1/test-fork-1"},
            {"id": 789012, "name": "test-fork-2", "full_name": "user2/test-fork-2"}
        ]
        
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance
        mock_engine_instance.collect_fork_data_from_list.return_value = sample_fork_data
        mock_engine_instance.create_qualification_result.return_value = MagicMock()
        
        # Test the function
        await _show_comprehensive_fork_data(
            config=mock_config,
            repository_url="testowner/testrepo",
            exclude_archived=False,
            exclude_disabled=False,
            interactive=False,
            verbose=True
        )
        
        # Verify calls
        mock_validate.assert_called_once_with("testowner/testrepo")
        mock_processor_instance.get_all_forks_list_data.assert_called_once_with("testowner", "testrepo")
        mock_engine_instance.collect_fork_data_from_list.assert_called_once()
        mock_display.assert_called_once()


@pytest.mark.asyncio
async def test_show_comprehensive_fork_data_with_filters(mock_config, sample_fork_data):
    """Test comprehensive fork data display with filters applied."""
    with patch('forklift.cli.GitHubClient') as mock_github_client, \
         patch('forklift.github.fork_list_processor.ForkListProcessor') as mock_processor, \
         patch('forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine') as mock_engine, \
         patch('forklift.cli._display_comprehensive_fork_data') as mock_display, \
         patch('forklift.cli.validate_repository_url') as mock_validate:
        
        # Setup mocks
        mock_validate.return_value = ("testowner", "testrepo")
        
        mock_client_instance = AsyncMock()
        mock_github_client.return_value.__aenter__.return_value = mock_client_instance
        
        mock_processor_instance = AsyncMock()
        mock_processor.return_value = mock_processor_instance
        mock_processor_instance.get_all_forks_list_data.return_value = []
        
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance
        mock_engine_instance.collect_fork_data_from_list.return_value = sample_fork_data
        mock_engine_instance.exclude_archived_and_disabled.return_value = sample_fork_data
        mock_engine_instance.create_qualification_result.return_value = MagicMock()
        
        # Test with filters
        await _show_comprehensive_fork_data(
            config=mock_config,
            repository_url="testowner/testrepo",
            exclude_archived=True,
            exclude_disabled=True,
            interactive=False,
            verbose=False
        )
        
        # Verify filter methods were called
        mock_engine_instance.exclude_archived_and_disabled.assert_called_once()


def test_display_comprehensive_fork_data(sample_qualification_result, capsys):
    """Test the display function for comprehensive fork data."""
    with patch('forklift.cli.console') as mock_console:
        _display_comprehensive_fork_data(sample_qualification_result, verbose=True)
        
        # Verify console.print was called multiple times
        assert mock_console.print.call_count >= 3  # Summary, table, and efficiency info


def test_display_comprehensive_fork_data_no_forks():
    """Test display function with no forks."""
    from forklift.models.fork_qualification import QualificationStats, QualifiedForksResult
    
    stats = QualificationStats(
        total_forks_discovered=0,
        forks_with_no_commits=0,
        forks_with_commits=0,
        archived_forks=0,
        disabled_forks=0,
        api_calls_made=0,
        api_calls_saved=0,
        processing_time_seconds=0.1
    )
    
    empty_result = QualifiedForksResult(
        repository_owner="testowner",
        repository_name="testrepo",
        repository_url="https://github.com/testowner/testrepo",
        collected_forks=[],
        stats=stats
    )
    
    with patch('forklift.cli.console') as mock_console:
        _display_comprehensive_fork_data(empty_result, verbose=False)
        
        # Should still display summary even with no forks
        assert mock_console.print.call_count >= 2


@pytest.mark.asyncio
async def test_show_comprehensive_fork_data_error_handling(mock_config):
    """Test error handling in comprehensive fork data display."""
    with patch('forklift.cli.validate_repository_url') as mock_validate:
        mock_validate.side_effect = ValueError("Invalid URL")
        
        with pytest.raises(Exception):
            await _show_comprehensive_fork_data(
                config=mock_config,
                repository_url="invalid-url",
                exclude_archived=False,
                exclude_disabled=False,
                interactive=False,
                verbose=False
            )


def test_qualification_result_computed_properties(sample_qualification_result):
    """Test computed properties of QualifiedForksResult."""
    # Test forks_needing_analysis
    analysis_candidates = sample_qualification_result.forks_needing_analysis
    assert len(analysis_candidates) == 1
    assert analysis_candidates[0].metrics.name == "test-fork-1"
    
    # Test forks_to_skip
    skip_candidates = sample_qualification_result.forks_to_skip
    assert len(skip_candidates) == 1
    assert skip_candidates[0].metrics.name == "test-fork-2"
    
    # Test active_forks (within 90 days)
    active_forks = sample_qualification_result.active_forks
    assert len(active_forks) == 1  # Only test-fork-1 has recent activity
    
    # Test popular_forks (5+ stars)
    popular_forks = sample_qualification_result.popular_forks
    assert len(popular_forks) == 1  # Only test-fork-1 has 5+ stars


def test_fork_qualification_metrics_computed_properties():
    """Test computed properties of ForkQualificationMetrics."""
    from datetime import datetime
    
    # Test fork with commits ahead
    metrics_with_commits = ForkQualificationMetrics(
        id=123,
        name="test-fork",
        full_name="user/test-fork",
        owner="user",
        html_url="https://github.com/user/test-fork",
        created_at=datetime(2023, 1, 1),
        updated_at=datetime(2024, 1, 1),
        pushed_at=datetime(2024, 1, 15)  # After created_at
    )
    
    assert metrics_with_commits.commits_ahead_status == "Has commits"
    assert not metrics_with_commits.can_skip_analysis
    
    # Test fork with no commits ahead
    metrics_no_commits = ForkQualificationMetrics(
        id=456,
        name="test-fork-2",
        full_name="user/test-fork-2",
        owner="user",
        html_url="https://github.com/user/test-fork-2",
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
        pushed_at=datetime(2024, 1, 1)  # Same as created_at
    )
    
    assert metrics_no_commits.commits_ahead_status == "No commits ahead"
    assert metrics_no_commits.can_skip_analysis


def test_collected_fork_data_activity_summary():
    """Test activity summary generation for CollectedForkData."""
    from datetime import datetime, timedelta
    
    # Test very active fork (< 1 week)
    recent_metrics = ForkQualificationMetrics(
        id=123,
        name="recent-fork",
        full_name="user/recent-fork",
        owner="user",
        html_url="https://github.com/user/recent-fork",
        created_at=datetime.utcnow() - timedelta(days=30),
        updated_at=datetime.utcnow() - timedelta(days=1),
        pushed_at=datetime.utcnow() - timedelta(days=1)
    )
    
    recent_fork = CollectedForkData(metrics=recent_metrics)
    assert "Very Active" in recent_fork.activity_summary
    
    # Test inactive fork (> 1 year)
    old_metrics = ForkQualificationMetrics(
        id=456,
        name="old-fork",
        full_name="user/old-fork",
        owner="user",
        html_url="https://github.com/user/old-fork",
        created_at=datetime.utcnow() - timedelta(days=500),
        updated_at=datetime.utcnow() - timedelta(days=400),
        pushed_at=datetime.utcnow() - timedelta(days=400)
    )
    
    old_fork = CollectedForkData(metrics=old_metrics)
    assert "Inactive" in old_fork.activity_summary