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
         patch('forklift.cli.RepositoryDisplayService') as mock_display_service:
        
        # Setup mocks
        mock_client_instance = AsyncMock()
        mock_github_client.return_value.__aenter__.return_value = mock_client_instance
        
        mock_service_instance = AsyncMock()
        mock_display_service.return_value = mock_service_instance
        # Create a proper mock stats object
        mock_stats = MagicMock()
        mock_stats.processing_time_seconds = 1.5
        mock_stats.efficiency_percentage = 75.0
        
        mock_service_instance.show_fork_data.return_value = {
            "total_forks": 2,
            "displayed_forks": 2,
            "collected_forks": sample_fork_data,
            "stats": mock_stats,
            "qualification_result": MagicMock()
        }
        
        # Test the function
        await _show_comprehensive_fork_data(
            config=mock_config,
            repository_url="testowner/testrepo",
            exclude_archived=False,
            exclude_disabled=False,
            sort_by="stars",
            show_all=False,
            disable_cache=False,
            interactive=False,
            verbose=True
        )
        
        # Verify calls
        mock_service_instance.show_fork_data.assert_called_once_with(
            repo_url="testowner/testrepo",
            exclude_archived=False,
            exclude_disabled=False,
            sort_by="stars",
            show_all=False,
            disable_cache=False
        )


@pytest.mark.asyncio
async def test_show_comprehensive_fork_data_with_filters(mock_config, sample_fork_data):
    """Test comprehensive fork data display with filters applied."""
    with patch('forklift.cli.GitHubClient') as mock_github_client, \
         patch('forklift.cli.RepositoryDisplayService') as mock_display_service:
        
        # Setup mocks
        mock_client_instance = AsyncMock()
        mock_github_client.return_value.__aenter__.return_value = mock_client_instance
        
        mock_service_instance = AsyncMock()
        mock_display_service.return_value = mock_service_instance
        # Create a proper mock stats object
        mock_stats = MagicMock()
        mock_stats.processing_time_seconds = 2.0
        mock_stats.efficiency_percentage = 80.0
        
        mock_service_instance.show_fork_data.return_value = {
            "total_forks": 2,
            "displayed_forks": 1,
            "collected_forks": sample_fork_data[:1],  # Filtered result
            "stats": mock_stats,
            "qualification_result": MagicMock()
        }
        
        # Test with filters
        await _show_comprehensive_fork_data(
            config=mock_config,
            repository_url="testowner/testrepo",
            exclude_archived=True,
            exclude_disabled=True,
            sort_by="stars",
            show_all=False,
            disable_cache=False,
            interactive=False,
            verbose=False
        )
        
        # Verify filter parameters were passed
        mock_service_instance.show_fork_data.assert_called_once_with(
            repo_url="testowner/testrepo",
            exclude_archived=True,
            exclude_disabled=True,
            sort_by="stars",
            show_all=False,
            disable_cache=False
        )


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


@pytest.mark.asyncio
async def test_repository_display_service_show_fork_data(mock_config, sample_fork_data):
    """Test RepositoryDisplayService show_fork_data method."""
    from forklift.display.repository_display_service import RepositoryDisplayService
    from forklift.github.client import GitHubClient
    from rich.console import Console
    
    with patch('forklift.github.fork_list_processor.ForkListProcessor') as mock_processor, \
         patch('forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine') as mock_engine:
        
        # Setup mocks
        mock_github_client = AsyncMock()
        mock_console = MagicMock()
        
        mock_processor_instance = AsyncMock()
        mock_processor.return_value = mock_processor_instance
        mock_processor_instance.get_all_forks_list_data.return_value = [
            {"id": 123456, "name": "test-fork-1", "full_name": "user1/test-fork-1"},
            {"id": 789012, "name": "test-fork-2", "full_name": "user2/test-fork-2"}
        ]
        
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance
        mock_engine_instance.collect_fork_data_from_list.return_value = sample_fork_data
        
        # Create a proper mock qualification result
        mock_qualification_result = MagicMock()
        mock_qualification_result.repository_owner = "testowner"
        mock_qualification_result.repository_name = "testrepo"
        mock_qualification_result.collected_forks = sample_fork_data
        mock_qualification_result.stats = MagicMock()
        mock_qualification_result.stats.total_forks_discovered = 2
        mock_qualification_result.stats.forks_with_commits = 1
        mock_qualification_result.stats.forks_with_no_commits = 1
        mock_qualification_result.stats.archived_forks = 0
        mock_qualification_result.stats.disabled_forks = 0
        mock_qualification_result.stats.analysis_candidate_percentage = 50.0
        mock_qualification_result.stats.skip_rate_percentage = 50.0
        mock_qualification_result.stats.processing_time_seconds = 1.0
        mock_qualification_result.stats.efficiency_percentage = 0.0
        
        mock_engine_instance.create_qualification_result.return_value = mock_qualification_result
        
        # Create service
        service = RepositoryDisplayService(mock_github_client, mock_console)
        
        # Test the method
        result = await service.show_fork_data(
            repo_url="testowner/testrepo",
            exclude_archived=False,
            exclude_disabled=False,
            sort_by="stars",
            show_all=False,
            disable_cache=False
        )
        
        # Verify calls
        mock_processor_instance.get_all_forks_list_data.assert_called_once_with("testowner", "testrepo")
        mock_engine_instance.collect_fork_data_from_list.assert_called_once()
        
        # Verify result structure
        assert "total_forks" in result
        assert "displayed_forks" in result
        assert "collected_forks" in result
        assert "stats" in result
        assert "qualification_result" in result


@pytest.mark.asyncio
async def test_repository_display_service_show_fork_data_with_filters(mock_config, sample_fork_data):
    """Test RepositoryDisplayService show_fork_data method with filters."""
    from forklift.display.repository_display_service import RepositoryDisplayService
    
    with patch('forklift.github.fork_list_processor.ForkListProcessor') as mock_processor, \
         patch('forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine') as mock_engine:
        
        # Setup mocks
        mock_github_client = AsyncMock()
        mock_console = MagicMock()
        
        mock_processor_instance = AsyncMock()
        mock_processor.return_value = mock_processor_instance
        mock_processor_instance.get_all_forks_list_data.return_value = [
            {"id": 123456, "name": "test-fork-1", "full_name": "user1/test-fork-1"},
            {"id": 789012, "name": "test-fork-2", "full_name": "user2/test-fork-2"}
        ]
        
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance
        mock_engine_instance.collect_fork_data_from_list.return_value = sample_fork_data
        mock_engine_instance.exclude_archived_and_disabled.return_value = sample_fork_data
        
        # Create a proper mock qualification result
        mock_qualification_result = MagicMock()
        mock_qualification_result.repository_owner = "testowner"
        mock_qualification_result.repository_name = "testrepo"
        mock_qualification_result.collected_forks = sample_fork_data
        mock_qualification_result.stats = MagicMock()
        mock_qualification_result.stats.total_forks_discovered = 2
        mock_qualification_result.stats.forks_with_commits = 1
        mock_qualification_result.stats.forks_with_no_commits = 1
        mock_qualification_result.stats.archived_forks = 0
        mock_qualification_result.stats.disabled_forks = 0
        mock_qualification_result.stats.analysis_candidate_percentage = 50.0
        mock_qualification_result.stats.skip_rate_percentage = 50.0
        mock_qualification_result.stats.processing_time_seconds = 1.0
        mock_qualification_result.stats.efficiency_percentage = 0.0
        
        mock_engine_instance.create_qualification_result.return_value = mock_qualification_result
        
        # Create service
        service = RepositoryDisplayService(mock_github_client, mock_console)
        
        # Test with filters
        result = await service.show_fork_data(
            repo_url="testowner/testrepo",
            exclude_archived=True,
            exclude_disabled=True,
            sort_by="activity",
            show_all=True,
            disable_cache=False
        )
        
        # Verify filter methods were called (exclude_archived_and_disabled is called when exclude_archived=True)
        mock_engine_instance.exclude_archived_and_disabled.assert_called_once()
        
        # Verify result
        assert result is not None


@pytest.mark.asyncio
async def test_repository_display_service_show_fork_data_no_forks():
    """Test RepositoryDisplayService show_fork_data method with no forks."""
    from forklift.display.repository_display_service import RepositoryDisplayService
    
    with patch('forklift.github.fork_list_processor.ForkListProcessor') as mock_processor, \
         patch('forklift.analysis.fork_data_collection_engine.ForkDataCollectionEngine') as mock_engine:
        
        # Setup mocks
        mock_github_client = AsyncMock()
        mock_console = MagicMock()
        
        mock_processor_instance = AsyncMock()
        mock_processor.return_value = mock_processor_instance
        mock_processor_instance.get_all_forks_list_data.return_value = []
        
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance
        
        # Create service
        service = RepositoryDisplayService(mock_github_client, mock_console)
        
        # Test with no forks
        result = await service.show_fork_data(
            repo_url="testowner/testrepo",
            exclude_archived=False,
            exclude_disabled=False,
            sort_by="stars",
            show_all=False,
            disable_cache=False
        )
        
        # Verify result for no forks
        assert result["total_forks"] == 0
        assert result["collected_forks"] == []


def test_repository_display_service_sort_forks():
    """Test fork sorting functionality."""
    from forklift.display.repository_display_service import RepositoryDisplayService
    from datetime import datetime, timedelta
    
    # Create test data with different metrics
    metrics1 = ForkQualificationMetrics(
        id=1, name="fork-a", full_name="user/fork-a", owner="user", html_url="https://github.com/user/fork-a",
        stargazers_count=10, forks_count=5, size=1000, language="Python",
        created_at=datetime.utcnow() - timedelta(days=30),
        updated_at=datetime.utcnow() - timedelta(days=1),
        pushed_at=datetime.utcnow() - timedelta(days=1)
    )
    
    metrics2 = ForkQualificationMetrics(
        id=2, name="fork-b", full_name="user/fork-b", owner="user", html_url="https://github.com/user/fork-b",
        stargazers_count=5, forks_count=10, size=2000, language="JavaScript",
        created_at=datetime.utcnow() - timedelta(days=60),
        updated_at=datetime.utcnow() - timedelta(days=30),
        pushed_at=datetime.utcnow() - timedelta(days=30)
    )
    
    fork_data = [
        CollectedForkData(metrics=metrics1),
        CollectedForkData(metrics=metrics2)
    ]
    
    service = RepositoryDisplayService(AsyncMock(), MagicMock())
    
    # Test sorting by stars (descending)
    sorted_by_stars = service._sort_forks(fork_data, "stars")
    assert sorted_by_stars[0].metrics.stargazers_count == 10
    assert sorted_by_stars[1].metrics.stargazers_count == 5
    
    # Test sorting by name (ascending)
    sorted_by_name = service._sort_forks(fork_data, "name")
    assert sorted_by_name[0].metrics.name == "fork-a"
    assert sorted_by_name[1].metrics.name == "fork-b"
    
    # Test sorting by activity (recent first)
    sorted_by_activity = service._sort_forks(fork_data, "activity")
    assert sorted_by_activity[0].metrics.days_since_last_push < sorted_by_activity[1].metrics.days_since_last_push


def test_repository_display_service_enhanced_sort_forks():
    """Test enhanced fork sorting functionality."""
    from forklift.display.repository_display_service import RepositoryDisplayService
    from datetime import datetime, timedelta
    
    base_time = datetime.utcnow()
    
    # Fork with commits, high forks count
    metrics_has_commits_high = ForkQualificationMetrics(
        id=1, name="fork-has-commits-high", full_name="user/fork-has-commits-high", 
        owner="user", html_url="https://github.com/user/fork-has-commits-high",
        stargazers_count=50, forks_count=20, watchers_count=40,
        size=1000, language="Python",
        created_at=base_time - timedelta(days=60),
        updated_at=base_time - timedelta(days=1),
        pushed_at=base_time - timedelta(days=1)  # Push after creation = has commits
    )
    
    # Fork with commits, low forks count
    metrics_has_commits_low = ForkQualificationMetrics(
        id=2, name="fork-has-commits-low", full_name="user/fork-has-commits-low",
        owner="user", html_url="https://github.com/user/fork-has-commits-low",
        stargazers_count=100, forks_count=5, watchers_count=80,
        size=2000, language="JavaScript",
        created_at=base_time - timedelta(days=90),
        updated_at=base_time - timedelta(days=5),
        pushed_at=base_time - timedelta(days=5)  # Push after creation = has commits
    )
    
    # Fork without commits, high stats
    metrics_no_commits = ForkQualificationMetrics(
        id=3, name="fork-no-commits", full_name="user/fork-no-commits",
        owner="user", html_url="https://github.com/user/fork-no-commits",
        stargazers_count=200, forks_count=50, watchers_count=150,
        size=500, language="Go",
        created_at=base_time - timedelta(days=30),
        updated_at=base_time - timedelta(days=30),
        pushed_at=base_time - timedelta(days=30)  # Same as created = no commits
    )
    
    fork_data = [
        CollectedForkData(metrics=metrics_no_commits),      # Should be last despite high stats
        CollectedForkData(metrics=metrics_has_commits_low), # Should be second (lower forks)
        CollectedForkData(metrics=metrics_has_commits_high) # Should be first (higher forks)
    ]
    
    service = RepositoryDisplayService(AsyncMock(), MagicMock())
    
    # Test enhanced sorting
    sorted_enhanced = service._sort_forks_enhanced(fork_data)
    
    # Verify commits-first sorting
    assert sorted_enhanced[0].metrics.name == "fork-has-commits-high", \
        "Fork with commits and high forks should be first"
    assert sorted_enhanced[1].metrics.name == "fork-has-commits-low", \
        "Fork with commits and low forks should be second"
    assert sorted_enhanced[2].metrics.name == "fork-no-commits", \
        "Fork without commits should be last despite high stats"
    
    # Verify all forks with commits come before forks without commits
    has_commits_count = sum(1 for fork in sorted_enhanced 
                           if fork.metrics.commits_ahead_status == "Has commits")
    no_commits_count = len(sorted_enhanced) - has_commits_count
    
    # First has_commits_count forks should have commits
    for i in range(has_commits_count):
        assert sorted_enhanced[i].metrics.commits_ahead_status == "Has commits", \
            f"Fork at position {i} should have commits"
    
    # Remaining forks should not have commits
    for i in range(has_commits_count, len(sorted_enhanced)):
        assert sorted_enhanced[i].metrics.commits_ahead_status == "No commits ahead", \
            f"Fork at position {i} should not have commits"


def test_commits_ahead_status_detection():
    """Test commits ahead status detection logic."""
    from datetime import datetime
    
    # Test fork with commits ahead (pushed_at > created_at)
    metrics_with_commits = ForkQualificationMetrics(
        id=123, name="test-fork", full_name="user/test-fork", owner="user",
        html_url="https://github.com/user/test-fork",
        created_at=datetime(2023, 1, 1),
        updated_at=datetime(2024, 1, 1),
        pushed_at=datetime(2024, 1, 15)  # After created_at
    )
    
    assert metrics_with_commits.commits_ahead_status == "Has commits"
    assert not metrics_with_commits.can_skip_analysis
    
    # Test fork with no commits ahead (created_at >= pushed_at)
    metrics_no_commits = ForkQualificationMetrics(
        id=456, name="test-fork-2", full_name="user/test-fork-2", owner="user",
        html_url="https://github.com/user/test-fork-2",
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
        pushed_at=datetime(2024, 1, 1)  # Same as created_at
    )
    
    assert metrics_no_commits.commits_ahead_status == "No commits ahead"
    assert metrics_no_commits.can_skip_analysis
    
    # Test edge case: created_at > pushed_at
    metrics_edge_case = ForkQualificationMetrics(
        id=789, name="test-fork-3", full_name="user/test-fork-3", owner="user",
        html_url="https://github.com/user/test-fork-3",
        created_at=datetime(2024, 1, 2),
        updated_at=datetime(2024, 1, 1),
        pushed_at=datetime(2024, 1, 1)  # Before created_at
    )
    
    assert metrics_edge_case.commits_ahead_status == "No commits ahead"
    assert metrics_edge_case.can_skip_analysis