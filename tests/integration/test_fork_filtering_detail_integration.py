"""Integration tests for fork filtering with --detail functionality."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from forkscout.analysis.fork_commit_status_checker import ForkCommitStatusChecker
from forkscout.display.detailed_commit_display import (
    DetailedCommitDisplay,
    DetailedCommitProcessor,
)
from forkscout.github.client import GitHubClient
from forkscout.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualificationStats,
    QualifiedForksResult,
)
from forkscout.models.github import Commit, Repository


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    client = AsyncMock(spec=GitHubClient)
    return client


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    return Repository(
        owner="test_owner",
        name="test_repo",
        full_name="test_owner/test_repo",
        url="https://api.github.com/repos/test_owner/test_repo",
        html_url="https://github.com/test_owner/test_repo",
        clone_url="https://github.com/test_owner/test_repo.git",
        created_at=datetime(2023, 1, 1),
        pushed_at=datetime(2023, 6, 1)  # pushed_at > created_at = has commits
    )


@pytest.fixture
def mock_repository_no_commits():
    """Create a mock repository with no commits ahead."""
    return Repository(
        owner="test_owner",
        name="test_repo_no_commits",
        full_name="test_owner/test_repo_no_commits",
        url="https://api.github.com/repos/test_owner/test_repo_no_commits",
        html_url="https://github.com/test_owner/test_repo_no_commits",
        clone_url="https://github.com/test_owner/test_repo_no_commits.git",
        created_at=datetime(2023, 1, 1),
        pushed_at=datetime(2023, 1, 1)  # created_at == pushed_at = no commits
    )


@pytest.fixture
def mock_commits():
    """Create mock commits."""
    from forkscout.models.github import User

    author = User(
        id=123,
        login="testauthor",
        name="Test Author",
        email="test@example.com",
        html_url="https://github.com/testauthor"
    )

    return [
        Commit(
            sha="abc1234567890abcdef1234567890abcdef12345",
            message="Test commit 1",
            author=author,
            date=datetime(2023, 6, 1)
        ),
        Commit(
            sha="def4567890abcdef1234567890abcdef12345678",
            message="Test commit 2",
            author=author,
            date=datetime(2023, 6, 2)
        )
    ]


@pytest.fixture
def qualification_result_with_commits():
    """Create qualification result with fork that has commits ahead."""
    metrics = ForkQualificationMetrics(
        id=12345,
        full_name="test_owner/test_repo",
        owner="test_owner",
        name="test_repo",
        html_url="https://github.com/test_owner/test_repo",
        stargazers_count=10,
        forks_count=5,
        size=1000,
        language="Python",
        created_at=datetime(2023, 1, 1),
        updated_at=datetime(2023, 6, 1),
        pushed_at=datetime(2023, 6, 1),  # pushed_at > created_at
        open_issues_count=2,
        topics=["python", "test"],
        watchers_count=10,
        archived=False,
        disabled=False,
        fork=True
    )

    fork_data = CollectedForkData(metrics=metrics)

    stats = QualificationStats(
        total_forks_discovered=1,
        forks_with_no_commits=0,
        forks_with_commits=1,
        api_calls_made=1,
        processing_time_seconds=1.0
    )

    return QualifiedForksResult(
        repository_owner="test_owner",
        repository_name="test_repo",
        repository_url="https://github.com/test_owner/test_repo",
        collected_forks=[fork_data],
        stats=stats
    )


@pytest.fixture
def qualification_result_no_commits():
    """Create qualification result with fork that has no commits ahead."""
    metrics = ForkQualificationMetrics(
        id=67890,
        full_name="test_owner/test_repo_no_commits",
        owner="test_owner",
        name="test_repo_no_commits",
        html_url="https://github.com/test_owner/test_repo_no_commits",
        stargazers_count=5,
        forks_count=2,
        size=500,
        language="Python",
        created_at=datetime(2023, 1, 1),
        updated_at=datetime(2023, 1, 1),
        pushed_at=datetime(2023, 1, 1),  # created_at == pushed_at
        open_issues_count=0,
        topics=["python"],
        watchers_count=5,
        archived=False,
        disabled=False,
        fork=True
    )

    fork_data = CollectedForkData(metrics=metrics)

    stats = QualificationStats(
        total_forks_discovered=1,
        forks_with_no_commits=1,
        forks_with_commits=0,
        api_calls_made=1,
        processing_time_seconds=1.0
    )

    return QualifiedForksResult(
        repository_owner="test_owner",
        repository_name="test_repo_no_commits",
        repository_url="https://github.com/test_owner/test_repo_no_commits",
        collected_forks=[fork_data],
        stats=stats
    )


@pytest.mark.asyncio
async def test_fork_status_checker_with_qualification_data_has_commits(
    mock_github_client, qualification_result_with_commits
):
    """Test fork status checker with qualification data for fork with commits."""
    checker = ForkCommitStatusChecker(mock_github_client)

    has_commits = await checker.has_commits_ahead(
        "https://github.com/test_owner/test_repo",
        qualification_result_with_commits
    )

    assert has_commits is True
    assert checker.stats["qualification_data_hits"] == 1
    assert checker.stats["has_commits_ahead"] == 1


@pytest.mark.asyncio
async def test_fork_status_checker_with_qualification_data_no_commits(
    mock_github_client, qualification_result_no_commits
):
    """Test fork status checker with qualification data for fork without commits."""
    checker = ForkCommitStatusChecker(mock_github_client)

    has_commits = await checker.has_commits_ahead(
        "https://github.com/test_owner/test_repo_no_commits",
        qualification_result_no_commits
    )

    assert has_commits is False
    assert checker.stats["qualification_data_hits"] == 1
    assert checker.stats["no_commits_ahead"] == 1


@pytest.mark.asyncio
async def test_fork_status_checker_github_api_fallback(
    mock_github_client, mock_repository
):
    """Test fork status checker fallback to GitHub API."""
    # Configure mock to return repository data
    mock_github_client.get_repository.return_value = mock_repository

    checker = ForkCommitStatusChecker(mock_github_client)

    has_commits = await checker.has_commits_ahead(
        "https://github.com/test_owner/test_repo"
    )

    assert has_commits is True
    assert checker.stats["api_fallback_calls"] == 1
    assert checker.stats["has_commits_ahead"] == 1
    mock_github_client.get_repository.assert_called_once_with("test_owner", "test_repo")


@pytest.mark.asyncio
async def test_detailed_commit_display_should_process_repository_with_commits(
    mock_github_client, mock_repository, qualification_result_with_commits
):
    """Test detailed commit display should process repository with commits."""
    checker = ForkCommitStatusChecker(mock_github_client)
    display = DetailedCommitDisplay(
        github_client=mock_github_client,
        fork_status_checker=checker
    )

    # Mock the checker to return True
    with patch.object(checker, "has_commits_ahead", return_value=True):
        should_process = await display.should_process_repository(mock_repository)

    assert should_process is True


@pytest.mark.asyncio
async def test_detailed_commit_display_should_skip_repository_no_commits(
    mock_github_client, mock_repository_no_commits, qualification_result_no_commits
):
    """Test detailed commit display should skip repository without commits."""
    checker = ForkCommitStatusChecker(mock_github_client)
    display = DetailedCommitDisplay(
        github_client=mock_github_client,
        fork_status_checker=checker
    )

    # Mock the checker to return False
    with patch.object(checker, "has_commits_ahead", return_value=False):
        should_process = await display.should_process_repository(mock_repository_no_commits)

    assert should_process is False


@pytest.mark.asyncio
async def test_detailed_commit_display_force_processing(
    mock_github_client, mock_repository_no_commits
):
    """Test detailed commit display force processing even without commits."""
    checker = ForkCommitStatusChecker(mock_github_client)
    display = DetailedCommitDisplay(
        github_client=mock_github_client,
        fork_status_checker=checker
    )

    # Mock the checker to return False, but force should override
    with patch.object(checker, "has_commits_ahead", return_value=False):
        should_process = await display.should_process_repository(
            mock_repository_no_commits, force=True
        )

    assert should_process is True


@pytest.mark.asyncio
async def test_detailed_commit_display_generate_detailed_view_skips_no_commits(
    mock_github_client, mock_repository_no_commits, mock_commits
):
    """Test detailed commit display skips repositories without commits."""
    checker = ForkCommitStatusChecker(mock_github_client)
    display = DetailedCommitDisplay(
        github_client=mock_github_client,
        fork_status_checker=checker
    )

    # Mock the checker to return False
    with patch.object(checker, "has_commits_ahead", return_value=False):
        detailed_commits = await display.generate_detailed_view(
            mock_commits, mock_repository_no_commits
        )

    assert detailed_commits == []


@pytest.mark.asyncio
async def test_detailed_commit_display_generate_detailed_view_processes_with_commits(
    mock_github_client, mock_repository, mock_commits
):
    """Test detailed commit display processes repositories with commits."""
    checker = ForkCommitStatusChecker(mock_github_client)
    display = DetailedCommitDisplay(
        github_client=mock_github_client,
        fork_status_checker=checker
    )

    # Mock the checker to return True
    with patch.object(checker, "has_commits_ahead", return_value=True):
        # Mock the _fetch_commit_details method to avoid actual API calls
        with patch.object(display, "_fetch_commit_details") as mock_fetch:
            from forkscout.display.detailed_commit_display import DetailedCommitInfo
            mock_fetch.return_value = DetailedCommitInfo(
                commit=mock_commits[0],
                github_url="https://github.com/test_owner/test_repo/commit/abc123"
            )

            detailed_commits = await display.generate_detailed_view(
                mock_commits[:1], mock_repository  # Only process one commit for simplicity
            )

    assert len(detailed_commits) == 1
    assert detailed_commits[0].commit.sha == "abc1234567890abcdef1234567890abcdef12345"


@pytest.mark.asyncio
async def test_detailed_commit_processor_skips_no_commits(
    mock_github_client, mock_repository_no_commits, mock_commits
):
    """Test detailed commit processor skips repositories without commits."""
    checker = ForkCommitStatusChecker(mock_github_client)
    processor = DetailedCommitProcessor(
        github_client=mock_github_client,
        fork_status_checker=checker
    )

    # Mock the checker to return False
    with patch.object(checker, "has_commits_ahead", return_value=False):
        detailed_commits = await processor.process_commits_for_detail_view(
            mock_commits, mock_repository_no_commits
        )

    assert detailed_commits == []


@pytest.mark.asyncio
async def test_detailed_commit_processor_force_processing(
    mock_github_client, mock_repository_no_commits, mock_commits
):
    """Test detailed commit processor force processing even without commits."""
    checker = ForkCommitStatusChecker(mock_github_client)
    processor = DetailedCommitProcessor(
        github_client=mock_github_client,
        fork_status_checker=checker
    )

    # Mock the checker to return False, but force should override
    with patch.object(checker, "has_commits_ahead", return_value=False):
        with patch.object(processor, "_process_single_commit") as mock_process:
            from forkscout.display.detailed_commit_display import DetailedCommitInfo
            mock_process.return_value = DetailedCommitInfo(
                commit=mock_commits[0],
                github_url="https://github.com/test_owner/test_repo_no_commits/commit/abc123"
            )

            detailed_commits = await processor.process_commits_for_detail_view(
                mock_commits[:1], mock_repository_no_commits, force=True
            )

    assert len(detailed_commits) == 1


@pytest.mark.asyncio
async def test_detailed_commit_display_process_multiple_repositories(
    mock_github_client, mock_repository, mock_repository_no_commits, mock_commits
):
    """Test detailed commit display processes multiple repositories with filtering."""
    checker = ForkCommitStatusChecker(mock_github_client)
    display = DetailedCommitDisplay(
        github_client=mock_github_client,
        fork_status_checker=checker
    )

    repositories_with_commits = [
        (mock_repository, mock_commits),  # Should be processed
        (mock_repository_no_commits, mock_commits)  # Should be skipped
    ]

    # Mock the checker to return appropriate values
    def mock_has_commits(fork_url):
        if "test_repo_no_commits" in fork_url:
            return False
        return True

    with patch.object(checker, "has_commits_ahead", side_effect=mock_has_commits):
        with patch.object(display, "_fetch_commit_details") as mock_fetch:
            from forkscout.display.detailed_commit_display import DetailedCommitInfo
            mock_fetch.return_value = DetailedCommitInfo(
                commit=mock_commits[0],
                github_url="https://github.com/test_owner/test_repo/commit/abc123"
            )

            results = await display.process_multiple_repositories(
                repositories_with_commits
            )

    # Only one repository should be processed (the one with commits)
    assert len(results) == 1
    assert results[0][0].name == "test_repo"


@pytest.mark.asyncio
async def test_detailed_commit_display_error_handling_in_fork_status_check(
    mock_github_client, mock_repository, mock_commits
):
    """Test detailed commit display handles errors in fork status check gracefully."""
    checker = ForkCommitStatusChecker(mock_github_client)
    display = DetailedCommitDisplay(
        github_client=mock_github_client,
        fork_status_checker=checker
    )

    # Mock the checker to raise an exception
    with patch.object(checker, "has_commits_ahead", side_effect=Exception("API Error")):
        should_process = await display.should_process_repository(mock_repository)

    # Should default to processing when error occurs
    assert should_process is True


@pytest.mark.asyncio
async def test_detailed_commit_display_no_fork_status_checker(
    mock_github_client, mock_repository, mock_commits
):
    """Test detailed commit display works without fork status checker."""
    display = DetailedCommitDisplay(
        github_client=mock_github_client,
        fork_status_checker=None
    )

    should_process = await display.should_process_repository(mock_repository)

    # Should always process when no checker is provided
    assert should_process is True


@pytest.mark.asyncio
async def test_fork_status_checker_statistics_tracking(
    mock_github_client, qualification_result_with_commits, qualification_result_no_commits
):
    """Test fork status checker tracks statistics correctly."""
    checker = ForkCommitStatusChecker(mock_github_client)

    # Test with qualification data - has commits
    await checker.has_commits_ahead(
        "https://github.com/test_owner/test_repo",
        qualification_result_with_commits
    )

    # Test with qualification data - no commits
    await checker.has_commits_ahead(
        "https://github.com/test_owner/test_repo_no_commits",
        qualification_result_no_commits
    )

    # Test API fallback
    mock_github_client.get_repository.return_value = Repository(
        owner="test_owner",
        name="test_repo_api",
        full_name="test_owner/test_repo_api",
        url="https://api.github.com/repos/test_owner/test_repo_api",
        html_url="https://github.com/test_owner/test_repo_api",
        clone_url="https://github.com/test_owner/test_repo_api.git",
        created_at=datetime(2023, 1, 1),
        pushed_at=datetime(2023, 6, 1)
    )

    await checker.has_commits_ahead("https://github.com/test_owner/test_repo_api")

    stats = checker.get_statistics()
    assert stats["qualification_data_hits"] == 2
    assert stats["api_fallback_calls"] == 1
    assert stats["has_commits_ahead"] == 2
    assert stats["no_commits_ahead"] == 1
    assert stats["errors"] == 0


@pytest.mark.asyncio
async def test_fork_status_checker_invalid_url_handling(mock_github_client):
    """Test fork status checker handles invalid URLs gracefully."""
    checker = ForkCommitStatusChecker(mock_github_client)

    with pytest.raises(Exception):  # Should raise ForkCommitStatusError
        await checker.has_commits_ahead("invalid-url")

    stats = checker.get_statistics()
    assert stats["errors"] == 1


@pytest.mark.asyncio
async def test_detailed_commit_display_process_commits_with_filtering_has_commits(
    mock_github_client, mock_repository, mock_commits
):
    """Test process_commits_with_filtering for repository with commits."""
    checker = ForkCommitStatusChecker(mock_github_client)
    display = DetailedCommitDisplay(
        github_client=mock_github_client,
        fork_status_checker=checker
    )

    # Mock the checker to return True
    with patch.object(checker, "has_commits_ahead", return_value=True):
        with patch.object(display, "_fetch_commit_details") as mock_fetch:
            from forkscout.display.detailed_commit_display import DetailedCommitInfo
            mock_fetch.return_value = DetailedCommitInfo(
                commit=mock_commits[0],
                github_url="https://github.com/test_owner/test_repo/commit/abc123"
            )

            detailed_commits = await display.process_commits_with_filtering(
                mock_commits[:1], mock_repository
            )

    assert len(detailed_commits) == 1
    assert detailed_commits[0].commit.sha == "abc1234567890abcdef1234567890abcdef12345"


@pytest.mark.asyncio
async def test_detailed_commit_display_process_commits_with_filtering_no_commits(
    mock_github_client, mock_repository_no_commits, mock_commits
):
    """Test process_commits_with_filtering for repository without commits."""
    checker = ForkCommitStatusChecker(mock_github_client)
    display = DetailedCommitDisplay(
        github_client=mock_github_client,
        fork_status_checker=checker
    )

    # Mock the checker to return False
    with patch.object(checker, "has_commits_ahead", return_value=False):
        detailed_commits = await display.process_commits_with_filtering(
            mock_commits, mock_repository_no_commits
        )

    assert detailed_commits == []


@pytest.mark.asyncio
async def test_detailed_commit_display_process_commits_with_filtering_force(
    mock_github_client, mock_repository_no_commits, mock_commits
):
    """Test process_commits_with_filtering with force flag."""
    checker = ForkCommitStatusChecker(mock_github_client)
    display = DetailedCommitDisplay(
        github_client=mock_github_client,
        fork_status_checker=checker
    )

    # Mock the checker to return False, but force should override
    with patch.object(checker, "has_commits_ahead", return_value=False):
        with patch.object(display, "_fetch_commit_details") as mock_fetch:
            from forkscout.display.detailed_commit_display import DetailedCommitInfo
            mock_fetch.return_value = DetailedCommitInfo(
                commit=mock_commits[0],
                github_url="https://github.com/test_owner/test_repo_no_commits/commit/abc123"
            )

            detailed_commits = await display.process_commits_with_filtering(
                mock_commits[:1], mock_repository_no_commits, force=True
            )

    assert len(detailed_commits) == 1


@pytest.mark.asyncio
async def test_detailed_commit_display_batch_processing_with_mixed_repositories(
    mock_github_client, mock_repository, mock_repository_no_commits, mock_commits
):
    """Test batch processing with mixed repositories (some with commits, some without)."""
    checker = ForkCommitStatusChecker(mock_github_client)
    display = DetailedCommitDisplay(
        github_client=mock_github_client,
        fork_status_checker=checker
    )

    repositories_with_commits = [
        (mock_repository, mock_commits),  # Should be processed
        (mock_repository_no_commits, mock_commits)  # Should be skipped
    ]

    # Mock the checker to return appropriate values
    def mock_has_commits(fork_url):
        if "test_repo_no_commits" in fork_url:
            return False
        return True

    with patch.object(checker, "has_commits_ahead", side_effect=mock_has_commits):
        with patch.object(display, "_fetch_commit_details") as mock_fetch:
            from forkscout.display.detailed_commit_display import DetailedCommitInfo
            mock_fetch.return_value = DetailedCommitInfo(
                commit=mock_commits[0],
                github_url="https://github.com/test_owner/test_repo/commit/abc123"
            )

            results = await display.process_multiple_repositories(
                repositories_with_commits
            )

    # Only one repository should be processed (the one with commits)
    assert len(results) == 1
    assert results[0][0].name == "test_repo"
    assert len(results[0][1]) == 2  # Should have processed both commits


@pytest.mark.asyncio
async def test_detailed_commit_processor_integration_with_fork_filtering(
    mock_github_client, mock_repository, mock_repository_no_commits, mock_commits
):
    """Test DetailedCommitProcessor integration with fork filtering."""
    checker = ForkCommitStatusChecker(mock_github_client)
    processor = DetailedCommitProcessor(
        github_client=mock_github_client,
        fork_status_checker=checker
    )

    # Test repository with commits
    with patch.object(checker, "has_commits_ahead", return_value=True):
        with patch.object(processor, "_process_single_commit") as mock_process:
            from forkscout.display.detailed_commit_display import DetailedCommitInfo
            mock_process.return_value = DetailedCommitInfo(
                commit=mock_commits[0],
                github_url="https://github.com/test_owner/test_repo/commit/abc123"
            )

            detailed_commits = await processor.process_commits_for_detail_view(
                mock_commits[:1], mock_repository
            )

    assert len(detailed_commits) == 1

    # Test repository without commits
    with patch.object(checker, "has_commits_ahead", return_value=False):
        detailed_commits = await processor.process_commits_for_detail_view(
            mock_commits, mock_repository_no_commits
        )

    assert detailed_commits == []


@pytest.mark.asyncio
async def test_fork_filtering_error_handling_in_batch_operations(
    mock_github_client, mock_repository, mock_commits
):
    """Test error handling in fork filtering during batch operations."""
    checker = ForkCommitStatusChecker(mock_github_client)
    display = DetailedCommitDisplay(
        github_client=mock_github_client,
        fork_status_checker=checker
    )

    repositories_with_commits = [
        (mock_repository, mock_commits)
    ]

    # Mock the checker to raise an exception
    with patch.object(checker, "has_commits_ahead", side_effect=Exception("API Error")):
        with patch.object(display, "_fetch_commit_details") as mock_fetch:
            from forkscout.display.detailed_commit_display import DetailedCommitInfo
            mock_fetch.return_value = DetailedCommitInfo(
                commit=mock_commits[0],
                github_url="https://github.com/test_owner/test_repo/commit/abc123"
            )

            results = await display.process_multiple_repositories(
                repositories_with_commits
            )

    # Should still process the repository despite the error
    assert len(results) == 1
    assert results[0][0].name == "test_repo"


@pytest.mark.asyncio
async def test_fork_filtering_with_qualification_data_integration(
    mock_github_client, mock_repository, mock_commits, qualification_result_with_commits
):
    """Test fork filtering integration with qualification data."""
    checker = ForkCommitStatusChecker(mock_github_client)
    display = DetailedCommitDisplay(
        github_client=mock_github_client,
        fork_status_checker=checker
    )

    # Mock the checker to use qualification data
    with patch.object(checker, "has_commits_ahead") as mock_check:
        mock_check.return_value = True

        with patch.object(display, "_fetch_commit_details") as mock_fetch:
            from forkscout.display.detailed_commit_display import DetailedCommitInfo
            mock_fetch.return_value = DetailedCommitInfo(
                commit=mock_commits[0],
                github_url="https://github.com/test_owner/test_repo/commit/abc123"
            )

            detailed_commits = await display.process_commits_with_filtering(
                mock_commits[:1], mock_repository
            )

    assert len(detailed_commits) == 1
    mock_check.assert_called_once_with("https://github.com/test_owner/test_repo")


@pytest.mark.asyncio
async def test_fork_filtering_performance_with_large_batch(
    mock_github_client, mock_commits
):
    """Test fork filtering performance with large batch of repositories."""
    checker = ForkCommitStatusChecker(mock_github_client)
    display = DetailedCommitDisplay(
        github_client=mock_github_client,
        fork_status_checker=checker
    )

    # Create a large batch of repositories
    repositories_with_commits = []
    for i in range(10):
        repo = Repository(
            owner="test_owner",
            name=f"test_repo_{i}",
            full_name=f"test_owner/test_repo_{i}",
            url=f"https://api.github.com/repos/test_owner/test_repo_{i}",
            html_url=f"https://github.com/test_owner/test_repo_{i}",
            clone_url=f"https://github.com/test_owner/test_repo_{i}.git",
            created_at=datetime(2023, 1, 1),
            pushed_at=datetime(2023, 6, 1) if i % 2 == 0 else datetime(2023, 1, 1)
        )
        repositories_with_commits.append((repo, mock_commits))

    # Mock the checker to return alternating results
    def mock_has_commits(fork_url):
        result = "test_repo_0" in fork_url or "test_repo_2" in fork_url or "test_repo_4" in fork_url or "test_repo_6" in fork_url or "test_repo_8" in fork_url
        # Update statistics manually since we're mocking
        if result:
            checker.stats["has_commits_ahead"] += 1
        else:
            checker.stats["no_commits_ahead"] += 1
        return result

    with patch.object(checker, "has_commits_ahead", side_effect=mock_has_commits):
        with patch.object(display, "_fetch_commit_details") as mock_fetch:
            from forkscout.display.detailed_commit_display import DetailedCommitInfo
            mock_fetch.return_value = DetailedCommitInfo(
                commit=mock_commits[0],
                github_url="https://github.com/test_owner/test_repo/commit/abc123"
            )

            results = await display.process_multiple_repositories(
                repositories_with_commits
            )

    # Should only process repositories with commits (every other one)
    assert len(results) == 5  # repos 0, 2, 4, 6, 8

    # Verify statistics
    stats = checker.get_statistics()
    assert stats["has_commits_ahead"] == 5
    assert stats["no_commits_ahead"] == 5
