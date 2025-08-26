"""Unit tests for detailed commit display functionality."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from forklift.display.detailed_commit_display import (
    DetailedCommitDisplay,
    DetailedCommitInfo,
    DetailedCommitProcessor,
)
from forklift.models.ai_summary import AISummary
from forklift.models.github import Commit, Repository, User


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    client = AsyncMock()
    client.get_commit_details.return_value = {
        "sha": "abc123",
        "files": [
            {
                "filename": "test.py",
                "patch": "@@ -1,3 +1,4 @@\n def test():\n+    print('hello')\n     pass"
            }
        ]
    }
    return client


@pytest.fixture
def mock_ai_engine():
    """Create a mock AI summary engine."""
    engine = AsyncMock()
    engine.generate_commit_summary.return_value = AISummary(
        commit_sha="abc123",
        summary_text="Test summary: Added print statement for debugging purposes"
    )
    return engine


@pytest.fixture
def sample_commit():
    """Create a sample commit object."""
    return Commit(
        sha="abc123def456789012345678901234567890abcd",
        message="feat: add new feature\n\nThis adds a new feature for testing",
        author=User(login="testuser", id=123, html_url="https://github.com/testuser"),
        date=datetime(2024, 1, 15, 10, 30, 0),
        files_changed=["test.py", "README.md"],
        additions=10,
        deletions=2
    )


@pytest.fixture
def sample_repository():
    """Create a sample repository object."""
    return Repository(
        owner="testowner",
        name="testrepo",
        full_name="testowner/testrepo",
        url="https://api.github.com/repos/testowner/testrepo",
        html_url="https://github.com/testowner/testrepo",
        clone_url="https://github.com/testowner/testrepo.git"
    )


class TestDetailedCommitInfo:
    """Test cases for DetailedCommitInfo class."""

    def test_detailed_commit_info_creation(self, sample_commit):
        """Test creating DetailedCommitInfo object."""
        github_url = "https://github.com/testowner/testrepo/commit/abc123def456"

        detailed_info = DetailedCommitInfo(
            commit=sample_commit,
            github_url=github_url,
            commit_message="Test message",
            diff_content="Test diff"
        )

        assert detailed_info.commit == sample_commit
        assert detailed_info.github_url == github_url
        assert detailed_info.commit_message == "Test message"
        assert detailed_info.diff_content == "Test diff"
        assert detailed_info.ai_summary is None

    def test_detailed_commit_info_with_ai_summary(self, sample_commit):
        """Test creating DetailedCommitInfo with AI summary."""
        ai_summary = AISummary(
            commit_sha="abc123",
            summary_text="Test summary with comprehensive details about the changes made"
        )

        detailed_info = DetailedCommitInfo(
            commit=sample_commit,
            github_url="https://github.com/test/repo/commit/abc123",
            ai_summary=ai_summary
        )

        assert detailed_info.ai_summary == ai_summary


class TestDetailedCommitDisplay:
    """Test cases for DetailedCommitDisplay class."""

    def test_initialization(self, mock_github_client):
        """Test DetailedCommitDisplay initialization."""
        display = DetailedCommitDisplay(mock_github_client)

        assert display.github_client == mock_github_client
        assert display.ai_engine is None
        assert display.console is not None

    def test_initialization_with_ai_engine(self, mock_github_client, mock_ai_engine):
        """Test DetailedCommitDisplay initialization with AI engine."""
        display = DetailedCommitDisplay(mock_github_client, mock_ai_engine)

        assert display.github_client == mock_github_client
        assert display.ai_engine == mock_ai_engine

    def test_create_github_url(self, mock_github_client, sample_commit, sample_repository):
        """Test GitHub URL creation."""
        display = DetailedCommitDisplay(mock_github_client)

        url = display._create_github_url(sample_commit, sample_repository)

        expected_url = f"https://github.com/{sample_repository.owner}/{sample_repository.name}/commit/{sample_commit.sha}"
        assert url == expected_url

    @pytest.mark.asyncio
    async def test_get_commit_diff_success(self, mock_github_client, sample_commit, sample_repository):
        """Test successful commit diff retrieval."""
        display = DetailedCommitDisplay(mock_github_client)

        diff_content = await display._get_commit_diff(sample_commit, sample_repository)

        assert "test.py" in diff_content
        assert "print('hello')" in diff_content
        mock_github_client.get_commit_details.assert_called_once_with(
            sample_repository.owner, sample_repository.name, sample_commit.sha
        )

    @pytest.mark.asyncio
    async def test_get_commit_diff_failure(self, mock_github_client, sample_commit, sample_repository):
        """Test commit diff retrieval failure."""
        mock_github_client.get_commit_details.side_effect = Exception("API error")
        display = DetailedCommitDisplay(mock_github_client)

        diff_content = await display._get_commit_diff(sample_commit, sample_repository)

        assert diff_content == ""

    @pytest.mark.asyncio
    async def test_generate_ai_summary_success(self, mock_github_client, mock_ai_engine, sample_commit):
        """Test successful AI summary generation."""
        display = DetailedCommitDisplay(mock_github_client, mock_ai_engine)

        summary = await display._generate_ai_summary(sample_commit, "test diff")

        assert summary is not None
        assert summary.commit_sha == "abc123"
        mock_ai_engine.generate_commit_summary.assert_called_once_with(sample_commit, "test diff")

    @pytest.mark.asyncio
    async def test_generate_ai_summary_no_engine(self, mock_github_client, sample_commit):
        """Test AI summary generation without engine."""
        display = DetailedCommitDisplay(mock_github_client)

        summary = await display._generate_ai_summary(sample_commit, "test diff")

        assert summary is None

    @pytest.mark.asyncio
    async def test_generate_ai_summary_failure(self, mock_github_client, mock_ai_engine, sample_commit):
        """Test AI summary generation failure."""
        mock_ai_engine.generate_commit_summary.side_effect = Exception("AI error")
        display = DetailedCommitDisplay(mock_github_client, mock_ai_engine)

        summary = await display._generate_ai_summary(sample_commit, "test diff")

        assert summary is None

    @pytest.mark.asyncio
    async def test_fetch_commit_details_success(self, mock_github_client, mock_ai_engine, sample_commit, sample_repository):
        """Test successful commit details fetching."""
        display = DetailedCommitDisplay(mock_github_client, mock_ai_engine)

        detailed_info = await display._fetch_commit_details(sample_commit, sample_repository)

        assert detailed_info.commit == sample_commit
        assert detailed_info.github_url.endswith(sample_commit.sha)
        assert detailed_info.ai_summary is not None
        assert detailed_info.commit_message == sample_commit.message
        assert "test.py" in detailed_info.diff_content

    @pytest.mark.asyncio
    async def test_generate_detailed_view_success(self, mock_github_client, mock_ai_engine, sample_commit, sample_repository):
        """Test successful detailed view generation."""
        display = DetailedCommitDisplay(mock_github_client, mock_ai_engine)
        commits = [sample_commit]

        detailed_commits = await display.generate_detailed_view(commits, sample_repository)

        assert len(detailed_commits) == 1
        assert detailed_commits[0].commit == sample_commit

    @pytest.mark.asyncio
    async def test_generate_detailed_view_with_progress_callback(self, mock_github_client, sample_commit, sample_repository):
        """Test detailed view generation with progress callback."""
        display = DetailedCommitDisplay(mock_github_client)
        commits = [sample_commit]
        progress_calls = []

        def progress_callback(completed, total):
            progress_calls.append((completed, total))

        detailed_commits = await display.generate_detailed_view(
            commits, sample_repository, progress_callback
        )

        assert len(detailed_commits) == 1
        assert progress_calls == [(1, 1)]

    @pytest.mark.asyncio
    async def test_generate_detailed_view_with_error(self, mock_github_client, sample_commit, sample_repository):
        """Test detailed view generation with error handling."""
        mock_github_client.get_commit_details.side_effect = Exception("API error")
        display = DetailedCommitDisplay(mock_github_client)
        commits = [sample_commit]

        detailed_commits = await display.generate_detailed_view(commits, sample_repository)

        assert len(detailed_commits) == 1
        assert detailed_commits[0].commit == sample_commit
        assert detailed_commits[0].diff_content == ""

    def test_format_detailed_commit_view(self, mock_github_client, sample_commit):
        """Test formatting detailed commit view."""
        mock_console = Mock()
        display = DetailedCommitDisplay(mock_github_client, console=mock_console)

        detailed_info = DetailedCommitInfo(
            commit=sample_commit,
            github_url="https://github.com/test/repo/commit/abc123",
            commit_message="Test message",
            diff_content="Test diff"
        )

        display.format_detailed_commit_view(detailed_info)

        # Verify console.print was called
        mock_console.print.assert_called()

    def test_create_url_section(self, mock_github_client):
        """Test URL section creation."""
        display = DetailedCommitDisplay(mock_github_client)

        url_section = display._create_url_section("https://github.com/test/repo/commit/abc123")

        assert url_section.title == "[bold blue]🔗 GitHub URL[/bold blue]"

    def test_create_ai_summary_section_with_summary(self, mock_github_client):
        """Test AI summary section creation with summary."""
        display = DetailedCommitDisplay(mock_github_client)

        ai_summary = AISummary(
            commit_sha="abc123",
            summary_text="Test summary with comprehensive details about the changes made"
        )

        ai_section = display._create_ai_summary_section(ai_summary)

        assert ai_section.title == "[bold green]🤖 AI Summary[/bold green]"

    def test_create_ai_summary_section_with_error(self, mock_github_client):
        """Test AI summary section creation with error."""
        display = DetailedCommitDisplay(mock_github_client)

        ai_summary = AISummary(
            commit_sha="abc123",
            summary_text="",
            error="Test error"
        )

        ai_section = display._create_ai_summary_section(ai_summary)

        assert ai_section.title == "[bold green]🤖 AI Summary[/bold green]"

    def test_create_message_section(self, mock_github_client):
        """Test commit message section creation."""
        display = DetailedCommitDisplay(mock_github_client)

        message_section = display._create_message_section("feat: test\n\nDetailed description")

        assert message_section.title == "[bold yellow]📝 Commit Message[/bold yellow]"

    def test_create_diff_section(self, mock_github_client):
        """Test diff section creation."""
        display = DetailedCommitDisplay(mock_github_client)

        diff_content = "@@ -1,3 +1,4 @@\n def test():\n+    print('hello')\n     pass"
        diff_section = display._create_diff_section(diff_content)

        assert diff_section.title == "[bold cyan]📊 Diff Content[/bold cyan]"

    def test_create_diff_section_truncated(self, mock_github_client):
        """Test diff section creation with truncation."""
        display = DetailedCommitDisplay(mock_github_client)

        # Create a diff with many lines
        diff_lines = [f"line {i}" for i in range(100)]
        diff_content = "\n".join(diff_lines)

        diff_section = display._create_diff_section(diff_content, max_lines=10)

        assert diff_section.title == "[bold cyan]📊 Diff Content[/bold cyan]"


class TestDetailedCommitProcessor:
    """Test cases for DetailedCommitProcessor class."""

    def test_initialization(self, mock_github_client):
        """Test DetailedCommitProcessor initialization."""
        processor = DetailedCommitProcessor(mock_github_client)

        assert processor.github_client == mock_github_client
        assert processor.ai_engine is None

    def test_initialization_with_ai_engine(self, mock_github_client, mock_ai_engine):
        """Test DetailedCommitProcessor initialization with AI engine."""
        processor = DetailedCommitProcessor(mock_github_client, mock_ai_engine)

        assert processor.github_client == mock_github_client
        assert processor.ai_engine == mock_ai_engine

    @pytest.mark.asyncio
    async def test_process_single_commit_success(self, mock_github_client, mock_ai_engine, sample_commit, sample_repository):
        """Test successful single commit processing."""
        processor = DetailedCommitProcessor(mock_github_client, mock_ai_engine)

        detailed_info = await processor._process_single_commit(sample_commit, sample_repository)

        assert detailed_info.commit == sample_commit
        assert detailed_info.github_url.endswith(sample_commit.sha)
        assert detailed_info.ai_summary is not None

    @pytest.mark.asyncio
    async def test_process_single_commit_without_ai(self, mock_github_client, sample_commit, sample_repository):
        """Test single commit processing without AI engine."""
        processor = DetailedCommitProcessor(mock_github_client)

        detailed_info = await processor._process_single_commit(sample_commit, sample_repository)

        assert detailed_info.commit == sample_commit
        assert detailed_info.ai_summary is None

    @pytest.mark.asyncio
    async def test_process_commits_for_detail_view_success(self, mock_github_client, sample_commit, sample_repository):
        """Test successful commits processing for detail view."""
        processor = DetailedCommitProcessor(mock_github_client)
        commits = [sample_commit]

        detailed_commits = await processor.process_commits_for_detail_view(commits, sample_repository)

        assert len(detailed_commits) == 1
        assert detailed_commits[0].commit == sample_commit

    @pytest.mark.asyncio
    async def test_process_commits_with_progress_callback(self, mock_github_client, sample_commit, sample_repository):
        """Test commits processing with progress callback."""
        processor = DetailedCommitProcessor(mock_github_client)
        commits = [sample_commit]
        progress_calls = []

        def progress_callback(completed, total):
            progress_calls.append((completed, total))

        detailed_commits = await processor.process_commits_for_detail_view(
            commits, sample_repository, progress_callback
        )

        assert len(detailed_commits) == 1
        assert progress_calls == [(1, 1)]

    @pytest.mark.asyncio
    async def test_process_commits_with_error(self, mock_github_client, sample_commit, sample_repository):
        """Test commits processing with error handling."""
        # Make the entire _process_single_commit method fail to trigger error handling
        mock_github_client.get_commit_details.side_effect = Exception("API error")
        processor = DetailedCommitProcessor(mock_github_client)

        # Mock _process_single_commit to raise an exception
        async def failing_process_single_commit(commit, repository):
            raise Exception("Processing failed")

        processor._process_single_commit = failing_process_single_commit
        commits = [sample_commit]

        detailed_commits = await processor.process_commits_for_detail_view(commits, sample_repository)

        assert len(detailed_commits) == 1
        assert detailed_commits[0].commit == sample_commit
        # Should have error AI summary
        assert detailed_commits[0].ai_summary is not None
        assert detailed_commits[0].ai_summary.error is not None

    def test_handle_processing_error(self, mock_github_client, sample_commit, sample_repository):
        """Test processing error handling."""
        processor = DetailedCommitProcessor(mock_github_client)
        error = Exception("Test error")

        detailed_info = processor._handle_processing_error(sample_commit, sample_repository, error)

        assert detailed_info.commit == sample_commit
        assert detailed_info.ai_summary is not None
        assert "Test error" in detailed_info.ai_summary.error


class TestDetailedCommitDisplayIntegration:
    """Integration tests for detailed commit display functionality."""

    @pytest.mark.asyncio
    async def test_end_to_end_detailed_display(self, mock_github_client, mock_ai_engine, sample_commit, sample_repository):
        """Test end-to-end detailed commit display."""
        display = DetailedCommitDisplay(mock_github_client, mock_ai_engine)
        commits = [sample_commit]

        # Generate detailed view
        detailed_commits = await display.generate_detailed_view(commits, sample_repository)

        # Verify results
        assert len(detailed_commits) == 1
        detailed_info = detailed_commits[0]

        assert detailed_info.commit == sample_commit
        assert detailed_info.github_url.endswith(sample_commit.sha)
        assert detailed_info.ai_summary is not None
        assert detailed_info.commit_message == sample_commit.message
        assert "test.py" in detailed_info.diff_content

        # Test formatting (should not raise exceptions)
        display.format_detailed_commit_view(detailed_info)

    @pytest.mark.asyncio
    async def test_detailed_display_without_ai_engine(self, mock_github_client, sample_commit, sample_repository):
        """Test detailed display without AI engine."""
        display = DetailedCommitDisplay(mock_github_client)
        commits = [sample_commit]

        detailed_commits = await display.generate_detailed_view(commits, sample_repository)

        assert len(detailed_commits) == 1
        detailed_info = detailed_commits[0]

        assert detailed_info.commit == sample_commit
        assert detailed_info.ai_summary is None
        assert detailed_info.commit_message == sample_commit.message

    @pytest.mark.asyncio
    async def test_detailed_display_with_multiple_commits(self, mock_github_client, mock_ai_engine, sample_repository):
        """Test detailed display with multiple commits."""
        # Create multiple commits
        commits = []
        for i in range(3):
            commit = Commit(
                sha=f"abc123def456789012345678901234567890abc{i}",
                message=f"feat: add feature {i}",
                author=User(login="testuser", id=123, html_url="https://github.com/testuser"),
                date=datetime(2024, 1, 15, 10, 30, i),
                files_changed=[f"test{i}.py"],
                additions=5,
                deletions=1
            )
            commits.append(commit)

        display = DetailedCommitDisplay(mock_github_client, mock_ai_engine)

        detailed_commits = await display.generate_detailed_view(commits, sample_repository)

        assert len(detailed_commits) == 3
        for i, detailed_info in enumerate(detailed_commits):
            assert detailed_info.commit.sha == f"abc123def456789012345678901234567890abc{i}"
            assert detailed_info.ai_summary is not None
