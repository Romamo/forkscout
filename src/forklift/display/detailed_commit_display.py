"""Detailed commit display with comprehensive information including AI summaries."""

import logging
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING, Optional

from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from forklift.ai.summary_engine import AICommitSummaryEngine
from forklift.github.client import GitHubClient
from forklift.models.ai_summary import AISummary
from forklift.models.github import Commit, Repository

if TYPE_CHECKING:
    from forklift.analysis.fork_commit_status_checker import ForkCommitStatusChecker

logger = logging.getLogger(__name__)


class DetailedCommitInfo:
    """Comprehensive commit information for detailed view."""

    def __init__(
        self,
        commit: Commit,
        github_url: str,
        ai_summary: AISummary | None = None,
        commit_message: str = "",
        diff_content: str = ""
    ):
        self.commit = commit
        self.github_url = github_url
        self.ai_summary = ai_summary
        self.commit_message = commit_message
        self.diff_content = diff_content


class DetailedCommitDisplay:
    """Display class for comprehensive commit information with AI summaries and diffs."""

    def __init__(
        self,
        github_client: GitHubClient,
        ai_engine: AICommitSummaryEngine | None = None,
        console: Console | None = None,
        fork_status_checker: Optional["ForkCommitStatusChecker"] = None
    ):
        """Initialize the detailed commit display.
        
        Args:
            github_client: GitHub API client
            ai_engine: AI summary engine (optional)
            console: Rich console for output (optional)
            fork_status_checker: Fork commit status checker (optional)
        """
        self.github_client = github_client
        self.ai_engine = ai_engine
        self.console = console or Console(file=sys.stdout)
        self.fork_status_checker = fork_status_checker

    async def should_process_repository(
        self,
        repository: Repository,
        force: bool = False
    ) -> bool:
        """Check if repository should be processed based on fork status.
        
        Args:
            repository: Repository object
            force: Whether to force processing regardless of fork status
            
        Returns:
            True if repository should be processed, False otherwise
        """
        if force or not self.fork_status_checker:
            logger.debug(f"Processing repository {repository.full_name} - force={force}, checker={self.fork_status_checker is not None}")
            return True

        try:
            fork_url = repository.html_url
            has_commits = await self.fork_status_checker.has_commits_ahead(fork_url)

            if has_commits is False:
                logger.info(f"Fork filtering: Skipping repository {repository.full_name} - no commits ahead")
                return False
            elif has_commits is None:
                logger.warning(f"Fork filtering: Could not determine commit status for {repository.full_name} - proceeding with analysis")
                return True
            else:
                logger.debug(f"Fork filtering: Repository {repository.full_name} has commits ahead - proceeding")
                return True

        except Exception as e:
            logger.warning(f"Fork filtering: Status check failed for {repository.full_name}: {e} - proceeding with analysis")
            return True

    async def generate_detailed_view(
        self,
        commits: list[Commit],
        repository: Repository,
        progress_callback: Callable | None = None,
        force: bool = False
    ) -> list[DetailedCommitInfo]:
        """Generate detailed view for a list of commits.
        
        Args:
            commits: List of Commit objects
            repository: Repository object
            progress_callback: Optional progress callback function
            force: Whether to force processing regardless of fork status
            
        Returns:
            List of DetailedCommitInfo objects
        """
        # Check if repository should be processed based on fork status
        if not await self.should_process_repository(repository, force):
            logger.info(f"Skipping detailed analysis for {repository.full_name} - no commits ahead")
            return []

        detailed_commits = []

        # Process commits with proper error handling
        for i, commit in enumerate(commits):
            try:
                # Apply fork filtering before expensive operations (AI summary, diff retrieval)
                detailed_info = await self._fetch_commit_details(commit, repository)
                detailed_commits.append(detailed_info)

                if progress_callback:
                    progress_callback(i + 1, len(commits))

            except Exception as e:
                logger.warning(f"Failed to fetch details for commit {commit.sha[:8]}: {e}")
                # Create minimal detailed info on error
                detailed_info = DetailedCommitInfo(
                    commit=commit,
                    github_url=self._create_github_url(commit, repository),
                    commit_message=commit.message
                )
                detailed_commits.append(detailed_info)

        return detailed_commits

    async def process_multiple_repositories(
        self,
        repositories_with_commits: list[tuple[Repository, list[Commit]]],
        progress_callback: Callable | None = None,
        force: bool = False
    ) -> list[tuple[Repository, list[DetailedCommitInfo]]]:
        """Process multiple repositories with fork filtering support.
        
        Args:
            repositories_with_commits: List of (Repository, commits) tuples
            progress_callback: Optional progress callback function
            force: Whether to force processing regardless of fork status
            
        Returns:
            List of (Repository, DetailedCommitInfo list) tuples for processed repositories
        """
        results = []
        processed_count = 0
        skipped_count = 0

        logger.info(f"Processing {len(repositories_with_commits)} repositories with fork filtering")

        for repository, commits in repositories_with_commits:
            try:
                # Apply fork filtering before expensive operations
                if not await self.should_process_repository(repository, force):
                    logger.info(f"Skipping repository {repository.full_name} - no commits ahead")
                    skipped_count += 1
                    if progress_callback:
                        processed_count += 1
                        progress_callback(processed_count, len(repositories_with_commits))
                    continue

                # Process commits for this repository (skip fork status check since already done)
                detailed_commits = await self.generate_detailed_view(
                    commits, repository, force=True  # Already checked fork status above
                )

                if detailed_commits:  # Only add if we have results
                    results.append((repository, detailed_commits))
                    logger.debug(f"Processed repository {repository.full_name} with {len(detailed_commits)} commits")

                if progress_callback:
                    processed_count += 1
                    progress_callback(processed_count, len(repositories_with_commits))

            except Exception as e:
                logger.error(f"Failed to process repository {repository.full_name}: {e}")
                if progress_callback:
                    processed_count += 1
                    progress_callback(processed_count, len(repositories_with_commits))

        logger.info(f"Batch processing complete: {len(results)} processed, {skipped_count} skipped")
        return results

    async def _fetch_commit_details(
        self,
        commit: Commit,
        repository: Repository
    ) -> DetailedCommitInfo:
        """Fetch comprehensive details for a single commit.
        
        Args:
            commit: Commit object
            repository: Repository object
            
        Returns:
            DetailedCommitInfo object with all available information
        """
        # Generate GitHub URL
        github_url = self._create_github_url(commit, repository)

        # Get commit diff
        diff_content = await self._get_commit_diff(commit, repository)

        # Generate AI summary if engine is available
        ai_summary = None
        if self.ai_engine:
            try:
                ai_summary = await self._generate_ai_summary(commit, diff_content)
            except Exception as e:
                logger.warning(f"Failed to generate AI summary for commit {commit.sha[:8]}: {e}")

        return DetailedCommitInfo(
            commit=commit,
            github_url=github_url,
            ai_summary=ai_summary,
            commit_message=commit.message,
            diff_content=diff_content
        )

    async def _get_commit_diff(self, commit: Commit, repository: Repository) -> str:
        """Get commit diff content from GitHub API.
        
        Args:
            commit: Commit object
            repository: Repository object
            
        Returns:
            Diff content as string
        """
        try:
            commit_details = await self.github_client.get_commit_details(
                repository.owner, repository.name, commit.sha
            )

            diff_text = ""
            if commit_details.get("files"):
                for file in commit_details["files"]:
                    if file.get("patch"):
                        diff_text += f"\n--- {file.get('filename', 'unknown')}\n"
                        diff_text += file["patch"]

            return diff_text

        except Exception as e:
            logger.warning(f"Failed to fetch diff for commit {commit.sha[:8]}: {e}")
            return ""

    def _create_github_url(self, commit: Commit, repository: Repository) -> str:
        """Create GitHub commit URL.
        
        Args:
            commit: Commit object
            repository: Repository object
            
        Returns:
            GitHub commit URL
        """
        return f"https://github.com/{repository.owner}/{repository.name}/commit/{commit.sha}"

    async def _generate_ai_summary(self, commit: Commit, diff_content: str) -> AISummary | None:
        """Generate AI summary for a commit.
        
        Args:
            commit: Commit object
            diff_content: Commit diff content
            
        Returns:
            AISummary object or None if generation fails
        """
        if not self.ai_engine:
            return None

        try:
            return await self.ai_engine.generate_commit_summary(commit, diff_content)
        except Exception as e:
            logger.error(f"AI summary generation failed for commit {commit.sha[:8]}: {e}")
            return None

    def format_detailed_commit_view(self, detailed_commit: DetailedCommitInfo) -> None:
        """Format and display a single detailed commit view.
        
        Args:
            detailed_commit: DetailedCommitInfo object to display
        """
        commit = detailed_commit.commit

        # Create main panel content
        content_sections = []

        # GitHub URL section
        url_section = self._create_url_section(detailed_commit.github_url)
        content_sections.append(url_section)

        # AI Summary section (if available)
        if detailed_commit.ai_summary:
            ai_section = self._create_ai_summary_section(detailed_commit.ai_summary)
            content_sections.append(ai_section)

        # Commit message section
        message_section = self._create_message_section(detailed_commit.commit_message)
        content_sections.append(message_section)

        # Diff content section
        if detailed_commit.diff_content:
            diff_section = self._create_diff_section(detailed_commit.diff_content)
            content_sections.append(diff_section)

        # Create main panel
        main_panel = Panel(
            Group(*content_sections),
            title=f"[bold]Commit Details: {commit.sha[:8]}[/bold]",
            border_style="bright_blue",
            padding=(1, 2)
        )

        self.console.print(main_panel)

    def _create_url_section(self, github_url: str) -> Panel:
        """Create GitHub URL section.
        
        Args:
            github_url: GitHub commit URL
            
        Returns:
            Panel with GitHub URL
        """
        return Panel(
            Text(github_url, style="link"),
            title="[bold blue]🔗 GitHub URL[/bold blue]",
            border_style="blue",
            padding=(0, 1)
        )

    def _create_ai_summary_section(self, ai_summary: AISummary) -> Panel:
        """Create AI summary section.
        
        Args:
            ai_summary: AISummary object
            
        Returns:
            Panel with AI summary content
        """
        if ai_summary.error:
            content = Text(f"ERROR - {ai_summary.error}", style="red")
        else:
            if ai_summary.summary_text:
                content = Text(ai_summary.summary_text, style="white")
            else:
                content = Text("No summary available", style="dim")

        return Panel(
            content,
            title="[bold green]🤖 AI Summary[/bold green]",
            border_style="green",
            padding=(0, 1)
        )

    def _create_message_section(self, commit_message: str) -> Panel:
        """Create commit message section.
        
        Args:
            commit_message: Commit message text
            
        Returns:
            Panel with formatted commit message
        """
        # Split message into title and body
        lines = commit_message.strip().split("\n")
        title = lines[0] if lines else ""
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

        content_parts = [Text(title, style="bold yellow")]

        if body:
            content_parts.append(Text(""))  # Empty line
            content_parts.append(Text(body, style="white"))

        return Panel(
            Group(*content_parts),
            title="[bold yellow]📝 Commit Message[/bold yellow]",
            border_style="yellow",
            padding=(0, 1)
        )

    def _create_diff_section(self, diff_content: str, max_lines: int = 50) -> Panel:
        """Create diff content section.
        
        Args:
            diff_content: Diff content text
            max_lines: Maximum lines to display
            
        Returns:
            Panel with formatted diff content
        """
        # Truncate diff if too long
        lines = diff_content.split("\n")
        if len(lines) > max_lines:
            truncated_diff = "\n".join(lines[:max_lines])
            truncated_diff += f"\n\n[... truncated {len(lines) - max_lines} more lines ...]"
        else:
            truncated_diff = diff_content

        # Use syntax highlighting for diff
        try:
            syntax = Syntax(
                truncated_diff,
                "diff",
                theme="monokai",
                line_numbers=False,
                word_wrap=True
            )
            content = syntax
        except Exception:
            # Fallback to plain text if syntax highlighting fails
            content = Text(truncated_diff, style="white")

        return Panel(
            content,
            title="[bold cyan]📊 Diff Content[/bold cyan]",
            border_style="cyan",
            padding=(0, 1)
        )

    async def process_commits_with_filtering(
        self,
        commits: list[Commit],
        repository: Repository,
        progress_callback: Callable | None = None,
        force: bool = False
    ) -> list[DetailedCommitInfo]:
        """Process commits with integrated fork filtering for batch operations.
        
        This method combines fork filtering with commit processing to ensure
        expensive operations (AI summaries, diff retrieval) are only performed
        on repositories that have commits ahead.
        
        Args:
            commits: List of Commit objects
            repository: Repository object
            progress_callback: Optional progress callback function
            force: Whether to force processing regardless of fork status
            
        Returns:
            List of DetailedCommitInfo objects, empty if filtered out
        """
        # Apply fork filtering before any expensive operations
        if not await self.should_process_repository(repository, force):
            logger.info(f"Fork filtering: Skipping {repository.full_name} - no commits ahead")
            return []

        # Process commits since repository passed filtering
        return await self.generate_detailed_view(
            commits, repository, progress_callback, force=True  # Skip re-checking
        )


class DetailedCommitProcessor:
    """Processor for handling detailed commit operations with rate limiting and error handling."""

    def __init__(
        self,
        github_client: GitHubClient,
        ai_engine: AICommitSummaryEngine | None = None,
        fork_status_checker: Optional["ForkCommitStatusChecker"] = None
    ):
        """Initialize the detailed commit processor.
        
        Args:
            github_client: GitHub API client
            ai_engine: AI summary engine (optional)
            fork_status_checker: Fork commit status checker (optional)
        """
        self.github_client = github_client
        self.ai_engine = ai_engine
        self.fork_status_checker = fork_status_checker

    async def process_commits_for_detail_view(
        self,
        commits: list[Commit],
        repository: Repository,
        progress_callback: Callable | None = None,
        force: bool = False
    ) -> list[DetailedCommitInfo]:
        """Process commits for detailed view with proper error handling and fork filtering.
        
        Args:
            commits: List of Commit objects
            repository: Repository object
            progress_callback: Optional progress callback function
            force: Whether to force processing regardless of fork status
            
        Returns:
            List of DetailedCommitInfo objects
        """
        # Apply fork filtering before expensive operations (AI summaries, diff retrieval)
        if not force and self.fork_status_checker:
            try:
                fork_url = repository.html_url
                has_commits = await self.fork_status_checker.has_commits_ahead(fork_url)

                if has_commits is False:
                    logger.info(f"Fork filtering: Skipping detailed processing for {repository.full_name} - no commits ahead")
                    return []
                elif has_commits is None:
                    logger.warning(f"Fork filtering: Could not determine commit status for {repository.full_name} - proceeding with processing")
                else:
                    logger.debug(f"Fork filtering: Repository {repository.full_name} has commits ahead - proceeding with processing")

            except Exception as e:
                logger.warning(f"Fork filtering: Status check failed for {repository.full_name}: {e} - proceeding with processing")

        detailed_commits = []

        # Process each commit with proper error handling
        for i, commit in enumerate(commits):
            try:
                detailed_info = await self._process_single_commit(commit, repository)
                detailed_commits.append(detailed_info)

                if progress_callback:
                    progress_callback(i + 1, len(commits))

            except Exception as e:
                logger.error(f"Failed to process commit {commit.sha[:8]} for {repository.full_name}: {e}")
                # Create error detailed info
                error_info = self._handle_processing_error(commit, repository, e)
                detailed_commits.append(error_info)

        logger.debug(f"Processed {len(detailed_commits)} commits for repository {repository.full_name}")
        return detailed_commits

    async def _process_single_commit(
        self,
        commit: Commit,
        repository: Repository
    ) -> DetailedCommitInfo:
        """Process a single commit for detailed view.
        
        Args:
            commit: Commit object
            repository: Repository object
            
        Returns:
            DetailedCommitInfo object
        """
        # Create GitHub URL
        github_url = f"https://github.com/{repository.owner}/{repository.name}/commit/{commit.sha}"

        # Fetch commit details and diff
        diff_content = ""
        try:
            commit_details = await self.github_client.get_commit_details(
                repository.owner, repository.name, commit.sha
            )

            # Extract diff from files
            if commit_details.get("files"):
                for file in commit_details["files"]:
                    if file.get("patch"):
                        diff_content += f"\n--- {file.get('filename', 'unknown')}\n"
                        diff_content += file["patch"]
        except Exception as e:
            logger.warning(f"Failed to fetch diff for commit {commit.sha[:8]}: {e}")

        # Generate AI summary if available
        ai_summary = None
        if self.ai_engine and diff_content:
            try:
                ai_summary = await self.ai_engine.generate_commit_summary(commit, diff_content)
            except Exception as e:
                logger.warning(f"Failed to generate AI summary for commit {commit.sha[:8]}: {e}")

        return DetailedCommitInfo(
            commit=commit,
            github_url=github_url,
            ai_summary=ai_summary,
            commit_message=commit.message,
            diff_content=diff_content
        )

    def _handle_processing_error(
        self,
        commit: Commit,
        repository: Repository,
        error: Exception
    ) -> DetailedCommitInfo:
        """Handle processing error and create minimal detailed info.
        
        Args:
            commit: Commit object
            repository: Repository object
            error: Exception that occurred
            
        Returns:
            DetailedCommitInfo with error information
        """
        github_url = f"https://github.com/{repository.owner}/{repository.name}/commit/{commit.sha}"

        # Create error AI summary
        error_summary = AISummary(
            commit_sha=commit.sha,
            summary_text="",
            error=f"Processing failed: {error!s}"
        )

        return DetailedCommitInfo(
            commit=commit,
            github_url=github_url,
            ai_summary=error_summary,
            commit_message=commit.message,
            diff_content=""
        )
