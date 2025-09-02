"""Repository Display Service for incremental repository exploration."""

import asyncio
import logging
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, ClassVar

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table

from forklift.display.terminal_detector import TerminalDetector

from forklift.github.client import GitHubClient
from forklift.models.ahead_only_filter import (
    create_default_ahead_only_filter,
)
from forklift.models.analysis import ForkPreviewItem, ForksPreview
from forklift.models.filters import PromisingForksFilter
from forklift.models.github import Repository
from forklift.storage.analysis_cache import AnalysisCacheManager
from forklift.storage.cache_validation import CacheValidationError, CacheValidator

logger = logging.getLogger(__name__)


@dataclass
class ForkTableConfig:
    """Configuration for universal fork table rendering."""

    # Standard column widths (consistent across modes)
    COLUMN_WIDTHS: ClassVar[dict[str, int]] = {
        "url": 35,
        "stars": 8,
        "forks": 8,
        "commits": 15,  # Unified width for both status and exact counts
        "last_push": 14,  # Accommodate "11 months ago"
        "recent_commits_base": 30,  # Minimum width, calculated dynamically
    }

    # Column styles
    COLUMN_STYLES: ClassVar[dict[str, str]] = {
        "url": "cyan",
        "stars": "yellow",
        "forks": "green",
        "commits": "magenta",
        "last_push": "blue",
        "recent_commits": "dim"
    }


class CommitDataFormatter:
    """Handles adaptive formatting of commit information."""

    @staticmethod
    def format_commit_info(fork_data, has_exact_counts: bool) -> str:
        """Format commit information based on available data.
        
        Args:
            fork_data: Fork data object (CollectedForkData or similar)
            has_exact_counts: Whether exact commit counts are available
            
        Returns:
            Formatted commit information string
        """
        if has_exact_counts:
            # Detailed mode: show exact counts
            exact_count = getattr(fork_data, "exact_commits_ahead", None)
            if isinstance(exact_count, int):
                return f"[green]+{exact_count}[/green]" if exact_count > 0 else ""
            else:
                return "[yellow]Unknown[/yellow]"
        else:
            # Standard mode: show status indicators
            metrics = getattr(fork_data, "metrics", fork_data)
            status = getattr(metrics, "commits_ahead_status", "Unknown")
            if status == "No commits ahead":
                return "0 commits"
            elif status == "Has commits":
                return "Has commits"
            else:
                return "[yellow]Unknown[/yellow]"


class RepositoryDisplayService:
    """Service for displaying repository information in a structured format."""

    def __init__(
        self,
        github_client: GitHubClient,
        console: Console | None = None,
        cache_manager: AnalysisCacheManager | None = None,
        should_exclude_language_distribution: bool = True,
        should_exclude_fork_insights: bool = True,
    ):
        """Initialize the repository display service.

        Args:
            github_client: GitHub API client for fetching data
            console: Rich console for output (optional, creates new if None)
            cache_manager: Cache manager for caching repository data (optional)
            should_exclude_language_distribution: Whether to exclude language distribution table
            should_exclude_fork_insights: Whether to exclude fork insights section
        """
        self.github_client = github_client
        # Configure console with appropriate width for file output
        from .interaction_mode import get_interaction_mode_detector, InteractionMode
        detector = get_interaction_mode_detector()
        interaction_mode = detector.get_interaction_mode()
        
        if console:
            self.console = console
        else:
            if interaction_mode == InteractionMode.OUTPUT_REDIRECTED:
                # Use a very wide width for file output to prevent table truncation
                # Force width and disable auto-detection, disable soft wrapping
                self.console = Console(file=sys.stdout, width=None, force_terminal=True, soft_wrap=False, _environ={})
            else:
                # Use default width for terminal output, disable soft wrapping
                self.console = Console(file=sys.stdout, soft_wrap=False)
        self.cache_manager = cache_manager
        self._should_exclude_language_distribution = (
            should_exclude_language_distribution
        )
        self._should_exclude_fork_insights = should_exclude_fork_insights
        
        # Create a separate console for progress bars that always goes to stderr
        # This ensures progress bars don't interfere with output redirection
        if interaction_mode == InteractionMode.OUTPUT_REDIRECTED:
            # When output is redirected, progress should go to stderr, disable soft wrapping
            self.progress_console = Console(file=sys.stderr, soft_wrap=False, width=None)
        else:
            # For other modes, use the same console as content
            self.progress_console = self.console

    async def list_forks_preview(self, repo_url: str) -> dict[str, Any]:
        """Display a lightweight preview of repository forks using minimal API calls.

        Args:
            repo_url: Repository URL in format owner/repo or full GitHub URL

        Returns:
            Dictionary containing forks preview data

        Raises:
            ValueError: If repository URL format is invalid
            GitHubAPIError: If forks cannot be fetched
        """
        owner, repo_name = self._parse_repository_url(repo_url)

        logger.info(f"Fetching lightweight forks preview for {owner}/{repo_name}")

        try:
            # Get basic fork information without detailed analysis
            forks = await self.github_client.get_repository_forks(owner, repo_name)

            if not forks:
                self.console.print(
                    "[yellow]No forks found for this repository.[/yellow]"
                )
                preview_data = ForksPreview(total_forks=0, forks=[])
                return preview_data.dict()

            # Create lightweight fork preview items
            fork_items = []
            for fork in forks:
                activity_status = self._calculate_fork_activity_status(fork)
                commits_ahead = self._calculate_commits_ahead_status(fork)
                fork_item = ForkPreviewItem(
                    name=fork.name,
                    owner=fork.owner,
                    stars=fork.stars,
                    last_push_date=fork.pushed_at,
                    fork_url=fork.html_url,
                    activity_status=activity_status,
                    commits_ahead=commits_ahead,
                )
                fork_items.append(fork_item)

            # Sort by stars and last push date
            fork_items.sort(
                key=lambda x: (
                    x.stars,
                    x.last_push_date or datetime.min.replace(tzinfo=UTC),
                ),
                reverse=True,
            )

            # Convert to dict format for display
            fork_items_dict = [
                {
                    "name": item.name,
                    "owner": item.owner,
                    "stars": item.stars,
                    "last_push_date": item.last_push_date,
                    "fork_url": item.fork_url,
                    "activity_status": item.activity_status,
                    "commits_ahead": item.commits_ahead,
                }
                for item in fork_items
            ]

            # Display the lightweight forks table
            self._display_forks_preview_table(fork_items_dict)

            # Create ForksPreview object
            preview_data = ForksPreview(total_forks=len(forks), forks=fork_items)

            return preview_data.dict()

        except Exception as e:
            logger.error(f"Failed to fetch forks preview: {e}")
            self.console.print(f"[red]Error: Failed to fetch forks preview: {e}[/red]")
            raise

    async def show_repository_details(self, repo_url: str) -> dict[str, Any]:
        """Display detailed repository information with caching support.

        Args:
            repo_url: Repository URL in format owner/repo or full GitHub URL

        Returns:
            Dictionary containing repository details

        Raises:
            ValueError: If repository URL format is invalid
            GitHubAPIError: If repository cannot be fetched
        """
        owner, repo_name = self._parse_repository_url(repo_url)

        logger.info(f"Fetching repository details for {owner}/{repo_name}")

        try:
            # Try to get from cache first if cache manager is available
            cached_details = None
            if self.cache_manager:
                try:
                    cached_data = await self.cache_manager.get_repository_metadata(
                        owner, repo_name
                    )
                    if cached_data:
                        logger.info(
                            f"Using cached repository details for {owner}/{repo_name}"
                        )

                        # Validate cached data before reconstruction
                        try:
                            CacheValidator.validate_repository_reconstruction(
                                cached_data["repository_data"]
                            )
                        except CacheValidationError as e:
                            logger.warning(
                                f"Cache validation failed for {owner}/{repo_name}: {e}"
                            )
                            # Fall through to fetch from API
                            cached_data = None

                        if cached_data:
                            # Reconstruct Repository object from cached data
                            repo_data = cached_data["repository_data"]
                            repository = Repository(
                                id=repo_data.get("id"),  # May not be cached
                                name=repo_data["name"],
                                owner=repo_data["owner"],
                                full_name=repo_data["full_name"],
                                url=repo_data.get(
                                    "url",
                                    f"https://github.com/{repo_data['full_name']}",
                                ),
                                html_url=repo_data.get(
                                    "html_url",
                                    f"https://github.com/{repo_data['full_name']}",
                                ),
                                clone_url=repo_data.get(
                                    "clone_url",
                                    f"https://github.com/{repo_data['full_name']}.git",
                                ),
                                description=repo_data.get("description"),
                                language=repo_data.get("language"),
                                stars=repo_data.get("stars", 0),
                                forks_count=repo_data.get("forks_count", 0),
                                watchers_count=repo_data.get("watchers_count", 0),
                                open_issues_count=repo_data.get("open_issues_count", 0),
                                size=repo_data.get("size", 0),
                                topics=cached_data.get(
                                    "topics", []
                                ),  # Add topics from cache
                                license_name=repo_data.get("license_name"),
                                default_branch=repo_data.get("default_branch", "main"),
                                is_private=repo_data.get("is_private", False),
                                is_fork=repo_data.get("is_fork", False),
                                is_archived=repo_data.get("is_archived", False),
                                created_at=(
                                    datetime.fromisoformat(repo_data["created_at"])
                                    if repo_data.get("created_at")
                                    else None
                                ),
                                updated_at=(
                                    datetime.fromisoformat(repo_data["updated_at"])
                                    if repo_data.get("updated_at")
                                    else None
                                ),
                                pushed_at=(
                                    datetime.fromisoformat(repo_data["pushed_at"])
                                    if repo_data.get("pushed_at")
                                    else None
                                ),
                            )

                            # Reconstruct the full repo_details structure
                            cached_details = {
                                "repository": repository,
                                "languages": cached_data["languages"],
                                "topics": cached_data["topics"],
                                "primary_language": cached_data["primary_language"],
                                "license": cached_data["license"],
                                "last_activity": cached_data["last_activity"],
                                "created": cached_data["created"],
                                "updated": cached_data["updated"],
                            }

                            # Display the cached information
                            self._display_repository_table(cached_details)
                            return cached_details
                except Exception as e:
                    logger.warning(f"Failed to get cached repository details: {e}")
                    # Continue to fetch from API

            # Fetch from GitHub API if not in cache
            repository = await self.github_client.get_repository(owner, repo_name)

            # Get additional information
            languages = await self.github_client.get_repository_languages(
                owner, repo_name
            )
            topics = await self.github_client.get_repository_topics(owner, repo_name)

            # Create repository details dictionary
            repo_details = {
                "repository": repository,
                "languages": languages,
                "topics": topics,
                "primary_language": repository.language or "Not specified",
                "license": repository.license_name or "No license",
                "last_activity": self._format_datetime(repository.pushed_at),
                "created": self._format_datetime(repository.created_at),
                "updated": self._format_datetime(repository.updated_at),
            }

            # Cache the results if cache manager is available
            if self.cache_manager:
                try:
                    # Create a serializable version for caching
                    cacheable_details = {
                        "repository_data": {
                            "id": repository.id,
                            "name": repository.name,
                            "owner": repository.owner,
                            "full_name": repository.full_name,
                            "url": repository.url,
                            "html_url": repository.html_url,
                            "clone_url": repository.clone_url,
                            "description": repository.description,
                            "language": repository.language,
                            "stars": repository.stars,
                            "forks_count": repository.forks_count,
                            "watchers_count": repository.watchers_count,
                            "open_issues_count": repository.open_issues_count,
                            "size": repository.size,
                            "license_name": repository.license_name,
                            "default_branch": repository.default_branch,
                            "is_private": repository.is_private,
                            "is_fork": repository.is_fork,
                            "is_archived": repository.is_archived,
                            "created_at": (
                                repository.created_at.isoformat()
                                if repository.created_at
                                else None
                            ),
                            "updated_at": (
                                repository.updated_at.isoformat()
                                if repository.updated_at
                                else None
                            ),
                            "pushed_at": (
                                repository.pushed_at.isoformat()
                                if repository.pushed_at
                                else None
                            ),
                        },
                        "languages": languages,
                        "topics": topics,
                        "primary_language": repository.language or "Not specified",
                        "license": repository.license_name or "No license",
                        "last_activity": self._format_datetime(repository.pushed_at),
                        "created": self._format_datetime(repository.created_at),
                        "updated": self._format_datetime(repository.updated_at),
                    }

                    await self.cache_manager.cache_repository_metadata(
                        owner,
                        repo_name,
                        cacheable_details,
                        ttl_hours=24,  # Cache for 24 hours
                    )
                    logger.info(f"Cached repository details for {owner}/{repo_name}")
                except Exception as e:
                    logger.warning(f"Failed to cache repository details: {e}")

            # Display the information
            self._display_repository_table(repo_details)

            return repo_details

        except Exception as e:
            logger.error(f"Failed to fetch repository details: {e}")
            self.console.print(
                f"[red]Error: Failed to fetch repository details: {e}[/red]"
            )
            raise

    def _parse_repository_url(self, repo_url: str) -> tuple[str, str]:
        """Parse repository URL to extract owner and repo name.

        Args:
            repo_url: Repository URL in various formats

        Returns:
            Tuple of (owner, repo_name)

        Raises:
            ValueError: If URL format is invalid
        """
        import re

        # Support various GitHub URL formats
        patterns = [
            r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
            r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$",
            r"^([^/]+)/([^/]+)$",  # Simple owner/repo format
        ]

        for pattern in patterns:
            match = re.match(pattern, repo_url.strip())
            if match:
                owner, repo = match.groups()
                return owner, repo

        raise ValueError(f"Invalid GitHub repository URL: {repo_url}")

    def _format_datetime(self, dt: datetime | None) -> str:
        """Format datetime for display.

        Args:
            dt: Datetime to format

        Returns:
            Formatted datetime string
        """
        if not dt:
            return "Unknown"

        # Calculate days ago
        days_ago = (datetime.utcnow() - dt.replace(tzinfo=None)).days

        if days_ago == 0:
            return "Today"
        elif days_ago == 1:
            return "Yesterday"
        elif days_ago < 7:
            return f"{days_ago} days ago"
        elif days_ago < 30:
            weeks = days_ago // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        elif days_ago < 365:
            months = days_ago // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        else:
            years = days_ago // 365
            return f"{years} year{'s' if years > 1 else ''} ago"

    def _calculate_activity_status(self, fork: Repository) -> str:
        """Calculate activity status for a fork.

        Args:
            fork: Fork repository

        Returns:
            Activity status string
        """
        if not fork.pushed_at:
            return "inactive"

        days_since_activity = (
            datetime.utcnow() - fork.pushed_at.replace(tzinfo=None)
        ).days

        if days_since_activity <= 30:
            return "active"
        elif days_since_activity <= 90:
            return "moderate"
        elif days_since_activity <= 365:
            return "stale"
        else:
            return "inactive"

    def _calculate_fork_activity_status(self, fork: Repository) -> str:
        """Calculate activity status for a fork based on created_at vs pushed_at comparison.

        This method determines if a fork has any commits by comparing creation and push dates.
        If they are the same (or very close), it means no commits were made after forking.

        Args:
            fork: Fork repository

        Returns:
            Activity status string: "Active", "Stale", or "No commits"
        """
        if not fork.created_at or not fork.pushed_at:
            return "No commits"

        # Remove timezone info for comparison
        created_at = fork.created_at.replace(tzinfo=None)
        pushed_at = fork.pushed_at.replace(tzinfo=None)

        # If created_at and pushed_at are the same (or within 1 minute), no commits were made
        time_diff = abs((pushed_at - created_at).total_seconds())
        if time_diff <= 60:  # Within 1 minute means no commits after fork
            return "No commits"

        # Calculate days since last push
        days_since_push = (datetime.utcnow() - pushed_at).days

        if days_since_push <= 90:  # Active within last 3 months
            return "Active"
        else:  # Stale if no activity for more than 3 months
            return "Stale"

    def _calculate_commits_ahead_status(self, fork: Repository) -> str:
        """Calculate commits ahead status using corrected logic.

        Uses created_at >= pushed_at comparison to identify forks with no new commits.
        This covers both scenarios:
        - created_at == pushed_at: Fork created but never had commits pushed
        - created_at > pushed_at: Fork created after last push (inherited old commits only)

        Args:
            fork: Fork repository

        Returns:
            Commits ahead status: "None" or "Unknown"
        """
        if not fork.created_at or not fork.pushed_at:
            return "None"

        # Remove timezone info for comparison
        created_at = fork.created_at.replace(tzinfo=None)
        pushed_at = fork.pushed_at.replace(tzinfo=None)

        # If created_at >= pushed_at, fork has no new commits
        if created_at >= pushed_at:
            return "None"
        else:
            return "Unknown"

    def _display_repository_table(self, repo_details: dict[str, Any]) -> None:
        """Display repository information in a formatted table.

        Args:
            repo_details: Repository details dictionary
        """
        repository = repo_details["repository"]

        # Create main repository info table
        table = Table(title=f"Repository Details: {repository.full_name}", expand=False)
        table.add_column("Property", style="cyan", width=20, no_wrap=True)
        table.add_column("Value", style="green", no_wrap=True, overflow="fold")

        table.add_row("Name", repository.name)
        table.add_row("Owner", repository.owner)
        table.add_row("Description", repository.description or "No description")
        table.add_row("Primary Language", repo_details["primary_language"])
        table.add_row("Stars", f"STARS: {repository.stars:,}")
        table.add_row("Forks", f"FORKS: {repository.forks_count:,}")
        table.add_row("Watchers", f"WATCHERS: {repository.watchers_count:,}")
        table.add_row("Open Issues", f"ISSUES: {repository.open_issues_count:,}")
        table.add_row("Size", f"SIZE: {repository.size:,} KB")
        table.add_row("License", repo_details["license"])
        table.add_row("Default Branch", repository.default_branch)
        table.add_row("Created", repo_details["created"])
        table.add_row("Last Updated", repo_details["updated"])
        table.add_row("Last Activity", repo_details["last_activity"])
        table.add_row(
            "Private", "PRIVATE: Yes" if repository.is_private else "PUBLIC: Yes"
        )
        table.add_row("Fork", "FORK: Yes" if repository.is_fork else "ORIGINAL: Yes")
        table.add_row(
            "Archived", "ARCHIVED: Yes" if repository.is_archived else "ACTIVE: Yes"
        )

        self.console.print(table)

        # Display languages if available
        if repo_details["languages"]:
            self._display_languages_panel(repo_details["languages"])

        # Display topics if available
        if repo_details["topics"]:
            self._display_topics_panel(repo_details["topics"])

    def _display_languages_panel(self, languages: dict[str, int]) -> None:
        """Display programming languages panel.

        Args:
            languages: Dictionary of language names to byte counts
        """
        total_bytes = sum(languages.values())

        if total_bytes == 0:
            return

        language_info = []
        for lang, bytes_count in sorted(
            languages.items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (bytes_count / total_bytes) * 100
            language_info.append(f"{lang}: {percentage:.1f}%")

        languages_text = " • ".join(language_info[:5])  # Show top 5 languages
        if len(languages) > 5:
            languages_text += f" • +{len(languages) - 5} more"

        panel = Panel(
            languages_text, title="Programming Languages", border_style="blue"
        )
        self.console.print(panel)

    def _display_topics_panel(self, topics: list[str]) -> None:
        """Display repository topics panel.

        Args:
            topics: List of topic strings
        """
        if not topics:
            return

        topics_text = " • ".join(topics[:10])  # Show first 10 topics
        if len(topics) > 10:
            topics_text += f" • +{len(topics) - 10} more"

        panel = Panel(topics_text, title="Topics", border_style="green")
        self.console.print(panel)

    def _display_forks_table(
        self, enhanced_forks: list[dict[str, Any]], max_display: int = 50
    ) -> None:
        """Display forks in a formatted table.

        Args:
            enhanced_forks: List of enhanced fork data dictionaries
            max_display: Maximum number of forks to display
        """
        if not enhanced_forks:
            self.console.print("[yellow]No forks found.[/yellow]")
            return

        table = Table(title=f"Fork Summary ({len(enhanced_forks)} forks found)", expand=False)
        table.add_column("#", style="dim", width=4, no_wrap=True)
        table.add_column("Fork Name", style="cyan", min_width=25, no_wrap=True, overflow="fold")
        table.add_column("Owner", style="blue", min_width=15, no_wrap=True, overflow="fold")
        table.add_column("Stars", style="yellow", justify="right", width=8, no_wrap=True)
        table.add_column("Commits", style="green", justify="right", width=12, no_wrap=True)
        table.add_column("Last Activity", style="magenta", width=15, no_wrap=True)
        table.add_column("Status", style="white", width=10, no_wrap=True)
        table.add_column("Language", style="white", width=12, no_wrap=True)

        display_count = min(len(enhanced_forks), max_display)

        for i, fork_data in enumerate(enhanced_forks[:display_count], 1):
            fork = fork_data["fork"]

            # Style status with colors
            status = fork_data["activity_status"]
            status_styled = self._style_activity_status(status)

            # Use compact format for commits ahead/behind
            commits_ahead = fork_data["commits_ahead"]
            commits_behind = fork_data["commits_behind"]

            commits_status = self.format_commits_compact(commits_ahead, commits_behind)

            table.add_row(
                str(i),
                fork.name,
                fork.owner,
                f"⭐{fork.stars}",
                commits_status,
                fork_data["last_activity"],
                status_styled,
                fork.language or "N/A",
            )

        self.console.print(table)

        if len(enhanced_forks) > max_display:
            self.console.print(
                f"[dim]... and {len(enhanced_forks) - max_display} more forks[/dim]"
            )

    def _style_activity_status(self, status: str) -> str:
        """Apply color styling to activity status.

        Args:
            status: Activity status string

        Returns:
            Styled status string
        """
        status_colors = {
            "active": "[green]Active[/green]",
            "moderate": "[yellow]Moderate[/yellow]",
            "stale": "[orange3]Stale[/orange3]",
            "inactive": "[red]Inactive[/red]",
            "unknown": "[dim]Unknown[/dim]",
        }

        return status_colors.get(status, status)

    def _style_fork_activity_status(self, status: str) -> str:
        """Apply color styling to fork activity status.

        Args:
            status: Fork activity status string

        Returns:
            Styled status string
        """
        status_colors = {
            "Active": "[green]Active[/green]",
            "Stale": "[orange3]Stale[/orange3]",
            "No commits": "[red]No commits[/red]",
        }

        return status_colors.get(status, status)

    def _style_commits_ahead_status(self, status: str) -> str:
        """Apply color styling to commits ahead status.

        Args:
            status: Commits ahead status string

        Returns:
            Styled status string with simple Yes/No format
        """
        # Convert to simple format first
        simple_status = self._format_commits_ahead_simple(status)

        status_colors = {"No": "[red]No[/red]", "Yes": "[green]Yes[/green]"}

        return status_colors.get(simple_status, simple_status)

    def _format_commits_ahead_simple(self, status: str) -> str:
        """Format commits ahead status as simple Yes/No.

        Args:
            status: Commits ahead status string

        Returns:
            Simple Yes/No formatted string
        """
        if status in ["None", "No commits ahead"]:
            return "No"
        elif status in ["Unknown", "Has commits"]:
            return "Yes"
        else:
            return "Unknown"

    def _format_commits_ahead_detailed(self, status: str) -> str:
        """Format commits ahead status for detailed display.

        Args:
            status: Commits ahead status string

        Returns:
            Formatted status string matching detailed table format
        """
        if status in ["None", "No commits ahead"]:
            return "[dim]0 commits[/dim]"
        elif status in ["Unknown", "Has commits"]:
            return "[yellow]Unknown[/yellow]"
        else:
            return "[yellow]Unknown[/yellow]"

    def format_commits_status(self, commits_ahead: int, commits_behind: int) -> str:
        """Format commits ahead/behind into compact "+X -Y" format.

        Args:
            commits_ahead: Number of commits ahead
            commits_behind: Number of commits behind

        Returns:
            Formatted commits status string in "+X -Y" format
        """
        ahead_text = f"+{commits_ahead}" if commits_ahead > 0 else "+0"
        behind_text = f"-{commits_behind}" if commits_behind > 0 else "-0"
        return f"{ahead_text} {behind_text}"

    def format_commits_compact(self, commits_ahead: int, commits_behind: int) -> str:
        """Format commits ahead/behind into compact format with edge case handling.

        Args:
            commits_ahead: Number of commits ahead (or -1 for unknown)
            commits_behind: Number of commits behind (or -1 for unknown)

        Returns:
            Formatted commits status string with edge cases:
            - Empty cell for 0 ahead, 0 behind
            - "+X" for only ahead commits
            - "-Y" for only behind commits
            - "+X -Y" for both ahead and behind
            - "Unknown" for cases where status cannot be determined
        """
        # Handle unknown status (represented by -1)
        if commits_ahead == -1 or commits_behind == -1:
            return "Unknown"

        # Handle edge case: both zero (empty cell)
        if commits_ahead == 0 and commits_behind == 0:
            return ""

        # Handle only ahead commits
        if commits_ahead > 0 and commits_behind == 0:
            return f"[green]+{commits_ahead}[/green]"

        # Handle only behind commits
        if commits_ahead == 0 and commits_behind > 0:
            return f"[red]-{commits_behind}[/red]"

        # Handle both ahead and behind commits
        if commits_ahead > 0 and commits_behind > 0:
            return f"[green]+{commits_ahead}[/green] [red]-{commits_behind}[/red]"

        # Fallback for any other case
        return "Unknown"

    async def _display_fork_data_table(
        self,
        qualification_result,
        sort_by: str = "stars",
        show_all: bool = False,
        exclude_archived: bool = False,
        exclude_disabled: bool = False,
        show_commits: int = 0,
        force_all_commits: bool = False,
    ) -> None:
        """Display comprehensive fork data in a formatted table.

        Args:
            qualification_result: QualifiedForksResult containing all fork data
            sort_by: Sort criteria for the table
            show_all: Whether to show all forks or limit display
            exclude_archived: Whether archived forks were excluded
            exclude_disabled: Whether disabled forks were excluded
            show_commits: Number of recent commits to show for each fork (0-10)
        """

        # Display summary statistics
        stats = qualification_result.stats
        self.console.print(
            f"\n[bold blue]Fork Data Summary for {qualification_result.repository_owner}/{qualification_result.repository_name}[/bold blue]"
        )
        self.console.print("=" * 80)

        summary_table = Table(title="Collection Summary", expand=False)
        summary_table.add_column("Metric", style="cyan", width=25, no_wrap=True)
        summary_table.add_column("Count", style="green", justify="right", width=10, no_wrap=True)
        summary_table.add_column(
            "Percentage", style="yellow", justify="right", width=12, no_wrap=True
        )

        total = stats.total_forks_discovered
        summary_table.add_row("Total Forks", str(total), "100.0%")
        summary_table.add_row(
            "Need Analysis",
            str(stats.forks_with_commits),
            f"{stats.analysis_candidate_percentage:.1f}%",
        )
        summary_table.add_row(
            "Can Skip",
            str(stats.forks_with_no_commits),
            f"{stats.skip_rate_percentage:.1f}%",
        )
        summary_table.add_row(
            "Archived",
            str(stats.archived_forks),
            f"{(stats.archived_forks/total*100) if total > 0 else 0:.1f}%",
        )
        summary_table.add_row(
            "Disabled",
            str(stats.disabled_forks),
            f"{(stats.disabled_forks/total*100) if total > 0 else 0:.1f}%",
        )

        self.console.print(summary_table)

        # Display detailed fork data table
        if qualification_result.collected_forks:
            self.console.print("\n[bold blue]Detailed Fork Information[/bold blue]")
            self.console.print("=" * 80)

            # Sort forks using enhanced multi-level sorting
            sorted_forks = self._sort_forks_enhanced(
                qualification_result.collected_forks
            )

            # Create main fork data table using detailed format
            title_suffix = (
                f" (showing {show_commits} recent commits)" if show_commits > 0 else ""
            )
            fork_table = Table(
                title=f"All Forks ({len(sorted_forks)} displayed, sorted by commits status, stars, forks, activity){title_suffix}",
                expand=False
            )
            fork_table.add_column("URL", style="cyan", min_width=35, no_wrap=True, overflow="fold")
            fork_table.add_column("Stars", style="yellow", justify="right", width=8, no_wrap=True)
            fork_table.add_column("Forks", style="green", justify="right", width=8, no_wrap=True)
            fork_table.add_column("Commits", style="magenta", justify="right", width=12, no_wrap=True)
            fork_table.add_column("Last Push", style="blue", width=12, no_wrap=True)

            # Conditionally add Recent Commits column
            if show_commits > 0:
                # Calculate intelligent width based on expected content
                # Format: "YYYY-MM-DD abc1234 message..."
                # Base width: 10 (date) + 1 (space) + 7 (hash) + 1 (space) = 19
                # Message width: estimate based on show_commits count and typical message length
                base_width = 19  # Date and hash with spaces
                estimated_message_width = min(
                    300, 400 // show_commits
                )  # Much larger for full commit messages with wide console
                commits_width = max(50, min(400, base_width + estimated_message_width))

                fork_table.add_column(
                    "Recent Commits", style="dim", width=commits_width, no_wrap=True, overflow="fold"
                )

            # Determine display limit
            display_limit = (
                len(sorted_forks) if show_all else min(50, len(sorted_forks))
            )

            # Fetch commits concurrently if requested
            commits_cache = {}
            if show_commits > 0:
                forks_to_display = sorted_forks[:display_limit]
                commits_cache = await self._fetch_commits_concurrently(
                    forks_to_display,
                    show_commits,
                    qualification_result.repository_owner,
                    qualification_result.repository_name,
                    force_all_commits,
                )

            for _i, fork_data in enumerate(sorted_forks[:display_limit], 1):
                metrics = fork_data.metrics

                # Use compact format for commits ahead status
                if metrics.commits_ahead_status == "No commits ahead":
                    commits_status = "0 commits"  # Clear indication of no commits ahead
                elif metrics.commits_ahead_status == "Has commits":
                    commits_status = "Has commits"  # Indicates commits exist, use --detail for exact count
                else:
                    commits_status = self._format_commits_ahead_detailed(
                        metrics.commits_ahead_status
                    )

                # Format last push date
                last_push = self._format_datetime(metrics.pushed_at)

                # Generate fork URL
                fork_url = self._format_fork_url(metrics.owner, metrics.name)

                # Prepare row data using detailed format
                row_data = [
                    fork_url,
                    str(metrics.stargazers_count),
                    str(metrics.forks_count),
                    commits_status,
                    last_push,
                ]

                # Add recent commits data from cache
                if show_commits > 0:
                    fork_key = f"{metrics.owner}/{metrics.name}"
                    recent_commits_text = commits_cache.get(
                        fork_key, "[dim]No commits available[/dim]"
                    )
                    row_data.append(recent_commits_text)

                fork_table.add_row(*row_data)

            self.console.print(fork_table)

            if len(sorted_forks) > display_limit:
                remaining = len(sorted_forks) - display_limit
                self.console.print(
                    f"[dim]... and {remaining} more forks (use --show-all to see all)[/dim]"
                )

            # Show filtering information
            self._display_filtering_info(exclude_archived, exclude_disabled, stats)

            # Show additional insights (only if not excluded)
            if not self._should_exclude_fork_insights:
                self._display_fork_insights(qualification_result)

        else:
            self.console.print("[yellow]No forks found matching the criteria.[/yellow]")

    def _sort_forks(self, collected_forks, sort_by: str):
        """Sort forks based on the specified criteria.

        Args:
            collected_forks: List of CollectedForkData
            sort_by: Sort criteria

        Returns:
            Sorted list of forks
        """
        sort_functions = {
            "stars": lambda x: x.metrics.stargazers_count,
            "forks": lambda x: x.metrics.forks_count,
            "size": lambda x: x.metrics.size,
            "activity": lambda x: -x.metrics.days_since_last_push,  # Negative for recent first
            "commits_status": lambda x: (
                x.metrics.commits_ahead_status == "Has commits",
                x.metrics.stargazers_count,
            ),
            "commits": lambda x: self._get_commits_sort_key(x),
            "name": lambda x: x.metrics.name.lower(),
            "owner": lambda x: x.metrics.owner.lower(),
            "language": lambda x: x.metrics.language or "zzz",  # Put None at end
        }

        sort_func = sort_functions.get(sort_by, sort_functions["stars"])
        reverse = sort_by not in [
            "name",
            "owner",
            "language",
        ]  # These should be ascending

        return sorted(collected_forks, key=sort_func, reverse=reverse)

    def _get_commits_sort_key(self, fork_data) -> tuple:
        """Get sort key for commits sorting with compact format support.

        Implements primary sort by commits ahead, secondary sort by commits behind.
        Handles "Unknown" commit status entries by treating them as having potential commits.

        Args:
            fork_data: CollectedForkData object

        Returns:
            Tuple for multi-level sorting (commits_ahead, commits_behind)
        """
        # Get commits ahead and behind values
        commits_ahead = getattr(fork_data, "exact_commits_ahead", None)
        commits_behind = getattr(fork_data, "exact_commits_behind", None)

        # Handle different data types for commits_ahead
        if commits_ahead is None or commits_ahead == "Unknown":
            # Unknown status - treat as potentially having commits (high priority)
            ahead_sort_value = 999  # High value to sort first
        elif isinstance(commits_ahead, int):
            ahead_sort_value = commits_ahead
        else:
            # String values like "No commits ahead" or "Has commits"
            if commits_ahead in ["None", "No commits ahead"]:
                ahead_sort_value = 0
            else:
                ahead_sort_value = 999  # Treat as unknown/potential commits

        # Handle different data types for commits_behind
        if commits_behind is None or commits_behind == "Unknown":
            # Unknown status - use 0 as neutral value
            behind_sort_value = 0
        elif isinstance(commits_behind, int):
            behind_sort_value = commits_behind
        else:
            # String values - use 0 as default
            behind_sort_value = 0

        # Return tuple for multi-level sorting
        # Positive values since reverse=True will be applied
        return (ahead_sort_value, behind_sort_value)

    def _sort_forks_enhanced(self, collected_forks: list) -> list:
        """Sort forks with enhanced multi-level sorting logic.

        Implements improved multi-level sorting with proper priority order:
        1. Commits ahead status (forks with commits first)
        2. Stars count (descending - highest stars first)
        3. Forks count (descending - most forked first)
        4. Last push date (descending - most recent first)

        Args:
            collected_forks: List of CollectedForkData objects

        Returns:
            Sorted list of forks with improved sorting criteria
        """

        def sort_key(fork_data):
            """Multi-level sort key for improved fork sorting."""
            metrics = fork_data.metrics

            # 1. Commits ahead status - primary sort criterion
            # Use exact_commits_ahead if available, otherwise fall back to computed status
            exact_commits = getattr(fork_data, "exact_commits_ahead", None)

            if exact_commits is not None:
                # Use exact commit information when available
                if isinstance(exact_commits, int):
                    commits_priority = 0 if exact_commits > 0 else 1
                elif exact_commits == "Unknown":
                    commits_priority = 0  # Unknown - treat as potentially having commits
                else:
                    # String values like "No commits ahead" or "Has commits"
                    if exact_commits in ["None", "No commits ahead"]:
                        commits_priority = 1  # No commits
                    else:
                        commits_priority = 0  # Treat as having commits
            else:
                # Fall back to computed status from timestamps
                commits_status = metrics.commits_ahead_status
                if commits_status == "Has commits":
                    commits_priority = 0  # Highest priority
                elif commits_status == "No commits ahead":
                    commits_priority = 1  # Lower priority
                else:
                    # Handle unknown/other statuses - treat as potentially having commits
                    commits_priority = 0  # High priority for unknown status

            # 2. Stars count (descending - highest stars first)
            stars_count = metrics.stargazers_count

            # 3. Forks count (descending - most forked first)
            forks_count = metrics.forks_count

            # 4. Last push date (descending - most recent first)
            # Use negative timestamp for descending order
            # Handle potential None values defensively
            if metrics.pushed_at:
                push_timestamp = -metrics.pushed_at.timestamp()
            else:
                push_timestamp = float("inf")  # Sort None values last

            # Return tuple for multi-level sorting
            # Note: Python sorts tuples lexicographically, so we need to negate
            # numeric values for descending order
            return (
                commits_priority,     # 0 for "Has commits", 1 for "No commits ahead"
                -stars_count,        # Negative for descending order (highest stars first)
                -forks_count,        # Negative for descending order (most forked first)
                push_timestamp,      # Already negative for descending order (most recent first)
            )

        return sorted(collected_forks, key=sort_key)

    def _style_commits_ahead_display(self, status: str) -> str:
        """Apply color styling to commits ahead status for display.

        Args:
            status: Commits ahead status string

        Returns:
            Styled status string with simple Yes/No format
        """
        # Convert to simple format first
        simple_status = self._format_commits_ahead_simple(status)

        status_colors = {"No": "[red]No[/red]", "Yes": "[green]Yes[/green]"}

        return status_colors.get(simple_status, simple_status)

    def _format_fork_url(self, owner: str, repo_name: str) -> str:
        """Generate proper GitHub URL for a fork repository.

        Args:
            owner: Repository owner
            repo_name: Repository name

        Returns:
            Formatted GitHub URL
        """
        return f"https://github.com/{owner}/{repo_name}"

    def _display_filtering_info(
        self, exclude_archived: bool, exclude_disabled: bool, stats
    ) -> None:
        """Display information about applied filters.

        Args:
            exclude_archived: Whether archived forks were excluded
            exclude_disabled: Whether disabled forks were excluded
            stats: QualificationStats object
        """
        if exclude_archived or exclude_disabled:
            self.console.print("\n[bold yellow]Applied Filters:[/bold yellow]")
            filter_table = Table(expand=False)
            filter_table.add_column("Filter", style="cyan", no_wrap=True)
            filter_table.add_column("Status", style="green", no_wrap=True)
            filter_table.add_column("Excluded Count", style="red", justify="right", no_wrap=True)

            if exclude_archived:
                filter_table.add_row(
                    "Archived Forks", "Excluded", str(stats.archived_forks)
                )
            if exclude_disabled:
                filter_table.add_row(
                    "Disabled Forks", "Excluded", str(stats.disabled_forks)
                )

            self.console.print(filter_table)

    def _display_fork_insights(self, qualification_result) -> None:
        """Display additional insights about the fork data.

        Args:
            qualification_result: QualifiedForksResult containing all fork data
        """
        # Get insights from computed properties
        active_forks = qualification_result.active_forks
        popular_forks = qualification_result.popular_forks
        analysis_candidates = qualification_result.forks_needing_analysis
        skip_candidates = qualification_result.forks_to_skip

        self.console.print("\n[bold green]Fork Insights:[/bold green]")
        insights_table = Table(expand=False)
        insights_table.add_column("Category", style="cyan", width=25, no_wrap=True)
        insights_table.add_column("Count", style="green", justify="right", width=8, no_wrap=True)
        insights_table.add_column("Description", style="white", no_wrap=True, overflow="fold")

        insights_table.add_row(
            "Active Forks",
            str(len(active_forks)),
            "Forks with activity in last 90 days",
        )
        insights_table.add_row(
            "Popular Forks", str(len(popular_forks)), "Forks with 5+ stars"
        )
        insights_table.add_row(
            "Analysis Candidates",
            str(len(analysis_candidates)),
            "Forks that need detailed analysis",
        )
        insights_table.add_row(
            "Skip Candidates", str(len(skip_candidates)), "Forks with no commits ahead"
        )

        self.console.print(insights_table)

        # Show language distribution (only if not excluded)
        if not self._should_exclude_language_distribution:
            languages = {}
            for fork_data in qualification_result.collected_forks:
                lang = fork_data.metrics.language or "Unknown"
                languages[lang] = languages.get(lang, 0) + 1

            if languages:
                self.console.print("\n[bold blue]Language Distribution:[/bold blue]")
                lang_table = Table(expand=False)
                lang_table.add_column("Language", style="cyan", no_wrap=True)
                lang_table.add_column("Fork Count", style="green", justify="right", no_wrap=True)
                lang_table.add_column("Percentage", style="yellow", justify="right", no_wrap=True)

                total_forks = len(qualification_result.collected_forks)
                for lang, count in sorted(
                    languages.items(), key=lambda x: x[1], reverse=True
                )[:10]:
                    percentage = (count / total_forks) * 100
                    lang_table.add_row(lang, str(count), f"{percentage:.1f}%")

                self.console.print(lang_table)

    async def show_fork_data(
        self,
        repo_url: str,
        exclude_archived: bool = False,
        exclude_disabled: bool = False,
        sort_by: str = "stars",
        show_all: bool = False,
        disable_cache: bool = False,
        show_commits: int = 0,
        force_all_commits: bool = False,
        ahead_only: bool = False,
        csv_export: bool = False,
    ) -> dict[str, Any]:
        """Display comprehensive fork data with all collected metrics.

        Args:
            repo_url: Repository URL in format owner/repo or full GitHub URL
            exclude_archived: Whether to exclude archived forks from display
            exclude_disabled: Whether to exclude disabled forks from display
            sort_by: Sort criteria (stars, activity, size, commits_status, name)
            show_all: Whether to show all forks or limit display
            disable_cache: Whether to bypass cache for fresh data
            show_commits: Number of recent commits to show for each fork (0-10)
            force_all_commits: If True, bypass optimization and download commits for all forks
            ahead_only: If True, filter to show only forks with commits ahead
            csv_export: If True, export data in CSV format instead of table format

        Returns:
            Dictionary containing comprehensive fork data

        Raises:
            ValueError: If repository URL format is invalid
            GitHubAPIError: If fork data cannot be fetched
        """
        from forklift.analysis.fork_data_collection_engine import (
            ForkDataCollectionEngine,
        )
        from forklift.github.fork_list_processor import ForkListProcessor

        owner, repo_name = self._parse_repository_url(repo_url)

        logger.info(f"Collecting comprehensive fork data for {owner}/{repo_name}")

        try:
            # Initialize components
            fork_processor = ForkListProcessor(self.github_client)
            data_engine = ForkDataCollectionEngine()

            # Get all forks data from GitHub API
            forks_list_data = await fork_processor.get_all_forks_list_data(
                owner, repo_name
            )

            if not forks_list_data:
                self.console.print(
                    "[yellow]No forks found for this repository.[/yellow]"
                )
                return {"total_forks": 0, "collected_forks": [], "stats": None}

            # Collect comprehensive fork data
            collected_forks = data_engine.collect_fork_data_from_list(forks_list_data)

            # Apply filters if requested
            original_count = len(collected_forks)
            filtered_forks = collected_forks.copy()

            if exclude_archived:
                filtered_forks = data_engine.exclude_archived_and_disabled(
                    filtered_forks
                )

            if exclude_disabled:
                filtered_forks = [
                    fork for fork in filtered_forks if not fork.metrics.disabled
                ]

            # Apply ahead-only filtering if requested
            if ahead_only:
                ahead_only_filter = create_default_ahead_only_filter()
                # Convert collected fork data to Repository objects for filtering
                repositories = [self._convert_collected_fork_to_repository(fork) for fork in filtered_forks]
                filter_result = ahead_only_filter.filter_forks(repositories)

                # Filter the collected forks to match the filtered repositories
                filtered_repo_urls = {repo.html_url for repo in filter_result.forks}
                filtered_forks = [
                    fork for fork in filtered_forks
                    if fork.metrics.html_url in filtered_repo_urls
                ]

                # Display filtering statistics
                if filter_result.total_excluded > 0:
                    self.console.print(f"[dim]{filter_result.exclusion_summary}[/dim]")

            # Create qualification result
            qualification_result = data_engine.create_qualification_result(
                repository_owner=owner,
                repository_name=repo_name,
                collected_forks=filtered_forks,
                processing_time_seconds=0.0,
                api_calls_made=len(forks_list_data),
                api_calls_saved=0,
            )

            # Display comprehensive fork data using universal renderer
            table_context = {
                "owner": owner,
                "repo": repo_name,
                "has_exact_counts": False,
                "mode": "standard",
                "api_calls_made": len(forks_list_data),
                "api_calls_saved": 0,
                "qualification_result": qualification_result,
                "fork_data_list": filtered_forks
            }

            await self._render_fork_table(
                filtered_forks, table_context, show_commits, force_all_commits, csv_export
            )

            return {
                "total_forks": original_count,
                "displayed_forks": len(filtered_forks),
                "collected_forks": filtered_forks,
                "stats": qualification_result.stats,
                "qualification_result": qualification_result,
            }

        except Exception as e:
            logger.error(f"Failed to collect fork data: {e}")
            self.console.print(f"[red]Error: Failed to collect fork data: {e}[/red]")
            raise

    async def show_fork_data_detailed(
        self,
        repo_url: str,
        max_forks: int | None = None,
        disable_cache: bool = False,
        show_commits: int = 0,
        force_all_commits: bool = False,
        ahead_only: bool = False,
        csv_export: bool = False,
    ) -> dict[str, Any]:
        """Display detailed fork data with exact commit counts ahead.

        This method makes additional API requests to fetch precise commit counts
        ahead for each fork using GitHub's compare API endpoint.

        Args:
            repo_url: Repository URL in format owner/repo or full GitHub URL
            max_forks: Maximum number of forks to display (None for all)
            disable_cache: Whether to bypass cache for fresh data
            show_commits: Number of recent commits to show for each fork (0-10)
            force_all_commits: If True, bypass optimization and download commits for all forks
            ahead_only: If True, filter to show only forks with commits ahead
            csv_export: If True, export data in CSV format instead of table format

        Returns:
            Dictionary containing detailed fork data with exact commit counts

        Raises:
            ValueError: If repository URL format is invalid
            GitHubAPIError: If fork data cannot be fetched
        """
        from rich.progress import (
            BarColumn,
            Progress,
            SpinnerColumn,
            TaskProgressColumn,
            TextColumn,
        )

        from forklift.analysis.fork_data_collection_engine import (
            ForkDataCollectionEngine,
        )
        from forklift.github.fork_list_processor import ForkListProcessor

        owner, repo_name = self._parse_repository_url(repo_url)

        logger.info(
            f"Collecting detailed fork data with exact commit counts for {owner}/{repo_name}"
        )

        try:
            # Initialize components
            fork_processor = ForkListProcessor(self.github_client)
            data_engine = ForkDataCollectionEngine()

            # Get all forks data from GitHub API
            forks_list_data = await fork_processor.get_all_forks_list_data(
                owner, repo_name
            )

            if not forks_list_data:
                self.console.print(
                    "[yellow]No forks found for this repository.[/yellow]"
                )
                return {
                    "total_forks": 0,
                    "collected_forks": [],
                    "stats": None,
                    "api_calls_made": 0,
                }

            # Apply max_forks limit if specified
            if max_forks and len(forks_list_data) > max_forks:
                forks_list_data = forks_list_data[:max_forks]

            # Collect basic fork data
            collected_forks = data_engine.collect_fork_data_from_list(forks_list_data)

            # Filter out archived and disabled forks for detailed analysis
            active_forks = [
                fork
                for fork in collected_forks
                if not fork.metrics.archived and not fork.metrics.disabled
            ]

            # Apply ahead-only filtering if requested
            if ahead_only:
                ahead_only_filter = create_default_ahead_only_filter()
                # Convert collected fork data to Repository objects for filtering
                repositories = [self._convert_collected_fork_to_repository(fork) for fork in active_forks]
                filter_result = ahead_only_filter.filter_forks(repositories)

                # Filter the collected forks to match the filtered repositories
                filtered_repo_urls = {repo.html_url for repo in filter_result.forks}
                active_forks = [
                    fork for fork in active_forks
                    if fork.metrics.html_url in filtered_repo_urls
                ]

                # Display filtering statistics
                if filter_result.total_excluded > 0:
                    self.console.print(f"[dim]{filter_result.exclusion_summary}[/dim]")

            # Separate forks that can be skipped from those needing API calls
            forks_to_skip = []
            forks_needing_api = []

            for fork_data in active_forks:
                if fork_data.metrics.can_skip_analysis:
                    # Fork has no commits ahead based on created_at >= pushed_at logic
                    fork_data.exact_commits_ahead = 0
                    forks_to_skip.append(fork_data)
                else:
                    # Fork needs API call to determine exact commits ahead
                    forks_needing_api.append(fork_data)

            # Log API call savings
            skipped_count = len(forks_to_skip)
            api_needed_count = len(forks_needing_api)

            if skipped_count > 0:
                logger.info(
                    f"Skipped {skipped_count} forks with no commits ahead, saved {skipped_count} API calls"
                )
                self.console.print(
                    f"[dim]Skipped {skipped_count} forks with no commits ahead (saved {skipped_count} API calls)[/dim]"
                )

            # Fetch exact commit counts using optimized batch processing
            api_calls_made = 0
            detailed_forks = list(forks_to_skip)  # Start with skipped forks

            if forks_needing_api:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=self.progress_console,
                ) as progress:
                    task = progress.add_task(
                        "Fetching exact commit counts...", total=len(forks_needing_api)
                    )

                    try:
                        # Use optimized batch processing to eliminate redundant parent repo requests
                        fork_data_list = [
                            (fork_data.metrics.owner, fork_data.metrics.name)
                            for fork_data in forks_needing_api
                        ]
                        
                        logger.info(f"Using optimized batch processing for {len(fork_data_list)} forks")
                        
                        # Batch process all forks against the same parent repository
                        batch_results = await self.github_client.get_commits_ahead_batch(
                            fork_data_list, owner, repo_name, count=1  # Minimum count to get commit info
                        )
                        
                        # Count API calls made by batch processing
                        # Batch processing makes: 1 parent repo call + N fork repo calls + N comparison calls
                        successful_forks = 0
                        parent_calls_saved = 0
                        
                        # Process batch results
                        for fork_data in forks_needing_api:
                            fork_full_name = f"{fork_data.metrics.owner}/{fork_data.metrics.name}"
                            
                            if fork_full_name in batch_results:
                                # Successfully processed
                                commits_ahead_list = batch_results[fork_full_name]
                                commits_ahead = len(commits_ahead_list) if commits_ahead_list else 0
                                fork_data.exact_commits_ahead = commits_ahead
                                successful_forks += 1
                                parent_calls_saved += 1  # Each fork would have needed a parent repo call
                            else:
                                # Failed to process (e.g., 404 error)
                                fork_data.exact_commits_ahead = "Unknown"
                            
                            detailed_forks.append(fork_data)
                            progress.update(task, advance=1)
                        
                        # Calculate API calls made by batch processing
                        # 1 parent repo call + successful_forks fork repo calls + successful_forks comparison calls
                        api_calls_made = 1 + (successful_forks * 2)
                        
                        # Log optimization results
                        logger.info(f"Batch processing completed: {successful_forks}/{len(forks_needing_api)} forks processed")
                        logger.info(f"API optimization: {parent_calls_saved} parent repository calls saved")
                        
                    except Exception as e:
                        logger.warning(f"Batch processing failed, falling back to individual requests: {e}")
                        
                        # Fallback to individual API calls if batch processing fails
                        for fork_data in forks_needing_api:
                            try:
                                # Get exact commits ahead count using compare API
                                commits_ahead = await self._get_exact_commits_ahead(
                                    owner,
                                    repo_name,
                                    fork_data.metrics.owner,
                                    fork_data.metrics.name,
                                )

                                # Count successful API calls (including those that return "Unknown" due to data issues)
                                api_calls_made += 1

                                # Update fork data with exact commit count
                                fork_data.exact_commits_ahead = commits_ahead
                                detailed_forks.append(fork_data)

                                progress.update(
                                    task,
                                    advance=1,
                                    description=f"Fetching commits for {fork_data.metrics.owner}/{fork_data.metrics.name}",
                                )

                            except Exception as e:
                                logger.warning(
                                    f"Failed to get commits ahead for {fork_data.metrics.owner}/{fork_data.metrics.name}: {e}"
                                )
                                # Don't count failed API calls
                                # Set to unknown and continue
                                fork_data.exact_commits_ahead = "Unknown"
                                detailed_forks.append(fork_data)
                                progress.update(task, advance=1)
            else:
                self.console.print(
                    "[dim]No forks require API calls for commit count analysis[/dim]"
                )

            # Display detailed fork data using universal renderer
            table_context = {
                "owner": owner,
                "repo": repo_name,
                "has_exact_counts": True,
                "mode": "detailed",
                "api_calls_made": api_calls_made,
                "api_calls_saved": skipped_count,
                "fork_data_list": detailed_forks
            }

            await self._render_fork_table(
                detailed_forks, table_context, show_commits, force_all_commits, csv_export
            )

            return {
                "total_forks": len(forks_list_data),
                "displayed_forks": len(detailed_forks),
                "collected_forks": detailed_forks,
                "api_calls_made": api_calls_made,
                "api_calls_saved": skipped_count,
                "forks_skipped": skipped_count,
                "forks_analyzed": api_needed_count,
            }

        except Exception as e:
            logger.error(f"Failed to collect detailed fork data: {e}")
            self.console.print(
                f"[red]Error: Failed to collect detailed fork data: {e}[/red]"
            )
            raise

    async def _get_exact_commits_ahead(
        self, base_owner: str, base_repo: str, fork_owner: str, fork_repo: str
    ) -> int | str:
        """Get exact number of commits ahead using GitHub's compare API.

        Args:
            base_owner: Base repository owner
            base_repo: Base repository name
            fork_owner: Fork repository owner
            fork_repo: Fork repository name

        Returns:
            Number of commits ahead or "Unknown" if cannot be determined

        Raises:
            Exception: If API call fails (for proper error handling by caller)
        """
        try:
            # Use GitHub's compare API to get exact commit count
            comparison = await self.github_client.compare_repositories(
                base_owner, base_repo, fork_owner, fork_repo
            )

            if comparison and "ahead_by" in comparison:
                return comparison["ahead_by"]
            else:
                return "Unknown"

        except Exception as e:
            logger.debug(
                f"Failed to compare {fork_owner}/{fork_repo} with {base_owner}/{base_repo}: {e}"
            )
            # Re-raise the exception so caller can handle it properly
            raise

    async def _display_fork_table(
        self,
        fork_data_list: list[Any],
        base_owner: str,
        base_repo: str,
        *,
        table_title: str,
        show_exact_counts: bool = False,
        show_commits: int = 0,
        show_insights: bool = False,
        api_calls_made: int = 0,
        api_calls_saved: int = 0,
        force_all_commits: bool = False
    ) -> None:
        """Universal fork table rendering method.
        
        Args:
            fork_data_list: List of fork data (CollectedForkData with optional exact_commits_ahead)
            base_owner: Base repository owner
            base_repo: Base repository name
            table_title: Title to display above the table
            show_exact_counts: Whether to show exact commit counts vs status text
            show_commits: Number of recent commits to show (0 = none)
            show_insights: Whether to show additional fork insights
            api_calls_made: Number of API calls made (for summary)
            api_calls_saved: Number of API calls saved (for summary)
            force_all_commits: Whether all commits were forced to be fetched
        """
        if not fork_data_list:
            self.console.print("[yellow]No forks found.[/yellow]")
            return

        # Display header
        self.console.print(f"\n[bold blue]Detailed Fork Information for {base_owner}/{base_repo}[/bold blue]")
        self.console.print("=" * 80)

        # Create table with universal column configuration
        fork_table = Table(show_header=True, header_style="bold magenta", expand=False)

        # Standard columns with automatic sizing
        fork_table.add_column("URL", style="cyan", no_wrap=True, overflow="fold")
        fork_table.add_column("Stars", style="yellow", justify="right", no_wrap=True)
        fork_table.add_column("Forks", style="green", justify="right", no_wrap=True)
        fork_table.add_column("Commits Ahead", style="magenta", justify="right", no_wrap=True)
        fork_table.add_column("Last Push", style="blue", no_wrap=True)

        # Conditionally add Recent Commits column
        commits_cache = {}
        if show_commits > 0:
            fork_table.add_column(
                "Recent Commits", 
                style="dim", 
                no_wrap=True,
                min_width=200,     # Much larger minimum width to prevent truncation
                overflow="fold"  # Show full content instead of truncating
            )

            # Fetch commits concurrently if needed
            commits_cache = await self._fetch_commits_concurrently(
                fork_data_list, base_owner, base_repo, show_commits, force_all_commits
            )

        # Add rows to table
        for fork_data in fork_data_list:
            # Get metrics (works for both standard and detailed fork data)
            metrics = getattr(fork_data, "metrics", fork_data)

            # Format URL
            fork_url = self._format_fork_url(metrics.owner, metrics.name)

            # Format commits display based on mode
            commits_display = self._format_commits_display(fork_data, show_exact_counts)

            # Format last push date
            last_push = self._format_datetime(metrics.pushed_at)

            # Prepare row data
            row_data = [
                fork_url,
                str(metrics.stargazers_count),
                str(metrics.forks_count),
                commits_display,
                last_push
            ]

            # Add recent commits if requested
            if show_commits > 0:
                fork_key = f"{metrics.owner}/{metrics.name}"
                recent_commits = commits_cache.get(fork_key, "")
                row_data.append(recent_commits)

            fork_table.add_row(*row_data)

        # Display table with title
        self.console.print(f"\n[bold]{table_title}[/bold]")
        self.console.print(fork_table)

        # Display summary
        self._display_fork_summary(fork_data_list, show_exact_counts, api_calls_made, api_calls_saved)

        # Display insights if requested
        if show_insights:
            await self._display_fork_insights(fork_data_list)

    def _format_commits_display(self, fork_data, show_exact_counts: bool) -> str:
        """Format commits display based on available data and display mode."""
        if show_exact_counts and hasattr(fork_data, "exact_commits_ahead"):
            # Use exact counts from compare API
            if isinstance(fork_data.exact_commits_ahead, int):
                if fork_data.exact_commits_ahead == 0:
                    return ""
                else:
                    return f"[green]+{fork_data.exact_commits_ahead}[/green]"
        else:
            # Use status from timestamp analysis
            metrics = getattr(fork_data, "metrics", fork_data)
            if hasattr(metrics, "commits_ahead_status"):
                status = metrics.commits_ahead_status
                if status == "No commits ahead":
                    return "0 commits"
                elif status == "Has commits":
                    return "Has commits"
        return "Unknown"

    def _display_fork_summary(self, fork_data_list, show_exact_counts: bool, api_calls_made: int, api_calls_saved: int) -> None:
        """Display summary statistics for fork data."""
        if show_exact_counts:
            # Summary for detailed mode
            forks_with_commits = sum(
                1 for fork in fork_data_list
                if hasattr(fork, "exact_commits_ahead") and
                isinstance(fork.exact_commits_ahead, int) and
                fork.exact_commits_ahead > 0
            )
            total_commits = sum(
                fork.exact_commits_ahead for fork in fork_data_list
                if hasattr(fork, "exact_commits_ahead") and
                isinstance(fork.exact_commits_ahead, int)
            )

            self.console.print("\nSummary:")
            self.console.print(f"• {forks_with_commits} forks have commits ahead")
            self.console.print(f"• {total_commits} total commits ahead across all forks")
            self.console.print(f"• {api_calls_made} API calls made for exact commit counts")
            if api_calls_saved > 0:
                self.console.print(f"• {api_calls_saved} API calls saved through optimization")
            self.console.print("• Exact commit counts fetched using GitHub compare API")
        else:
            # Summary for standard mode
            forks_with_commits = sum(
                1 for fork in fork_data_list
                if hasattr(fork, "metrics") and
                getattr(fork.metrics, "commits_ahead_status", "") == "Has commits"
            )

            self.console.print("\nSummary:")
            self.console.print(f"• {len(fork_data_list)} forks displayed")
            self.console.print(f"• {forks_with_commits} forks likely have commits ahead")
            self.console.print("• Commit status determined by timestamp analysis")

    async def _display_fork_insights(self, fork_data_list) -> None:
        """Display additional fork insights and analysis."""
        if not fork_data_list:
            return

        # This method can be expanded to show additional insights
        # For now, it's a placeholder that maintains compatibility
        pass

    async def _display_detailed_fork_table(
        self,
        detailed_forks: list,
        base_owner: str,
        base_repo: str,
        api_calls_made: int = 0,
        api_calls_saved: int = 0,
        show_commits: int = 0,
        force_all_commits: bool = False,
    ) -> None:
        """Display detailed fork information table with exact commit counts.

        Args:
            detailed_forks: List of fork data with exact commit counts
            base_owner: Base repository owner
            base_repo: Base repository name
            api_calls_made: Number of API calls made for commit counts
            api_calls_saved: Number of API calls saved by filtering
            show_commits: Number of recent commits to show for each fork (0-10)
            force_all_commits: If True, commits were fetched for all forks (no optimization)
        """
        if not detailed_forks:
            self.console.print(
                "[yellow]No active forks found for detailed analysis.[/yellow]"
            )
            return

        # Sort forks by commits ahead (descending), then by stars (descending)
        sorted_forks = sorted(
            detailed_forks,
            key=lambda x: (
                x.exact_commits_ahead if isinstance(x.exact_commits_ahead, int) else -1,
                x.metrics.stargazers_count,
            ),
            reverse=True,
        )

        # Create detailed fork table with simplified columns
        self.console.print(
            f"\n[bold blue]Detailed Fork Information for {base_owner}/{base_repo}[/bold blue]"
        )
        self.console.print("=" * 80)

        title_suffix = (
            f" (showing {show_commits} recent commits)" if show_commits > 0 else ""
        )
        # 3. Create consistent table structure
        table_title = self._build_table_title(sorted_forks, table_context, show_commits)
        fork_table = Table(
            title=table_title,
            expand=False,
            show_lines=True,
            collapse_padding=True,
            pad_edge=False,
            width=None  # Remove table width restrictions
        )
        fork_table.add_column("URL", style="cyan", min_width=35, no_wrap=True, overflow="fold")
        fork_table.add_column("Stars", style="yellow", justify="right", width=8, no_wrap=True, overflow="fold")
        fork_table.add_column("Forks", style="green", justify="right", width=8, no_wrap=True, overflow="fold")

        fork_table.add_column(
            "Commits Ahead", style="magenta", justify="right", width=15, no_wrap=True, overflow="fold"
        )
        fork_table.add_column("Last Push", style="blue", width=14, no_wrap=True, overflow="fold")

        # Conditionally add Recent Commits column
        if show_commits > 0:
            # Add Recent Commits column with no width limits to prevent truncation
            fork_table.add_column(
                "Recent Commits", 
                style="dim", 
                no_wrap=True,
                min_width=50,      # Minimum readable width
                overflow="fold",   # Show full content instead of truncating
                max_width=None     # Remove maximum width restriction
            )

        # Fetch commits concurrently if requested, with optimization
        commits_cache = {}
        if show_commits > 0:
            commits_cache = await self._fetch_commits_concurrently(
                sorted_forks, show_commits, base_owner, base_repo, force_all_commits
            )

        for fork_data in sorted_forks:
            metrics = fork_data.metrics

            # Format URL
            fork_url = self._format_fork_url(metrics.owner, metrics.name)

            # Use compact format for commits ahead
            if isinstance(fork_data.exact_commits_ahead, int):
                if fork_data.exact_commits_ahead == 0:
                    commits_display = ""  # Empty cell for no commits ahead
                else:
                    commits_display = f"[green]+{fork_data.exact_commits_ahead}[/green]"
            else:
                commits_display = (
                    "[green]+?[/green]"  # Unknown but potentially has commits
                )

            # Format last push date
            last_push = self._format_datetime(metrics.pushed_at)

            # Prepare row data
            row_data = [
                fork_url,
                str(metrics.stargazers_count),
                str(metrics.forks_count),
                commits_display,
                last_push,
            ]

            # Add recent commits data from cache
            if show_commits > 0:
                fork_key = f"{metrics.owner}/{metrics.name}"
                recent_commits_text = commits_cache.get(
                    fork_key, "[dim]No commits available[/dim]"
                )
                row_data.append(recent_commits_text)

            fork_table.add_row(*row_data)

        self.console.print(fork_table)

        # Show summary statistics
        total_commits_ahead = sum(
            fork.exact_commits_ahead
            for fork in sorted_forks
            if isinstance(fork.exact_commits_ahead, int)
        )
        forks_with_commits = len(
            [
                fork
                for fork in sorted_forks
                if isinstance(fork.exact_commits_ahead, int)
                and fork.exact_commits_ahead > 0
            ]
        )

        self.console.print("\n[bold]Summary:[/bold]")
        self.console.print(f"• {forks_with_commits} forks have commits ahead")
        self.console.print(
            f"• {total_commits_ahead} total commits ahead across all forks"
        )
        self.console.print(f"• {api_calls_made} API calls made for exact commit counts")
        if api_calls_saved > 0:
            self.console.print(
                f"• {api_calls_saved} API calls saved by smart filtering"
            )
            efficiency_percent = (
                api_calls_saved / (api_calls_made + api_calls_saved)
            ) * 100
            self.console.print(
                f"• {efficiency_percent:.1f}% API efficiency improvement"
            )
        self.console.print("• Exact commit counts fetched using GitHub compare API")

    async def show_promising_forks(
        self,
        repo_url: str,
        filters: PromisingForksFilter | None = None,
        max_forks: int | None = None,
    ) -> dict[str, Any]:
        """Display promising forks based on filter criteria.

        Args:
            repo_url: Repository URL in format owner/repo or full GitHub URL
            filters: Filter criteria for promising forks (optional)
            max_forks: Maximum number of forks to analyze (None for all)

        Returns:
            Dictionary containing promising forks data

        Raises:
            ValueError: If repository URL format is invalid
            GitHubAPIError: If forks cannot be fetched
        """
        owner, repo_name = self._parse_repository_url(repo_url)
        filters = filters or PromisingForksFilter()

        logger.info(f"Finding promising forks for {owner}/{repo_name}")

        try:
            # TODO: Update this method to use show_fork_data instead of removed show_forks_summary
            # For now, return empty result to avoid breaking the system
            # This method needs to be refactored to work with the new pagination-only approach
            self.console.print(
                "[yellow]show_promising_forks temporarily disabled - needs refactoring for pagination-only approach[/yellow]"
            )
            return {"total_forks": 0, "promising_forks": 0, "forks": []}

        except Exception as e:
            logger.error(f"Failed to find promising forks: {e}")
            self.console.print(f"[red]Error: Failed to find promising forks: {e}[/red]")
            raise

    def _display_promising_forks_table(
        self, promising_forks: list[dict[str, Any]], filters: PromisingForksFilter
    ) -> None:
        """Display promising forks in a formatted table.

        Args:
            promising_forks: List of promising fork data dictionaries
            filters: Filter criteria used
        """
        if not promising_forks:
            return

        # Display filter criteria first
        self._display_filter_criteria(filters)

        # Create table
        table = Table(title=f"Promising Forks ({len(promising_forks)} found)", expand=False)
        table.add_column("#", style="dim", width=4, no_wrap=True)
        table.add_column("Fork Name", style="cyan", min_width=25, no_wrap=True, overflow="fold")
        table.add_column("Owner", style="blue", min_width=15, no_wrap=True, overflow="fold")
        table.add_column("Stars", style="yellow", justify="right", width=8, no_wrap=True)
        table.add_column("Commits", style="green", justify="right", width=12, no_wrap=True)
        table.add_column("Activity Score", style="magenta", justify="right", width=13, no_wrap=True)
        table.add_column("Last Activity", style="white", width=15, no_wrap=True)
        table.add_column("Language", style="white", width=12, no_wrap=True)

        for i, fork_data in enumerate(promising_forks, 1):
            fork = fork_data["fork"]

            # Calculate activity score
            activity_score = filters._calculate_activity_score(
                fork_data["activity_status"], fork.pushed_at
            )

            # Format activity score with color
            if activity_score >= 0.8:
                score_text = f"[green]{activity_score:.2f}[/green]"
            elif activity_score >= 0.5:
                score_text = f"[yellow]{activity_score:.2f}[/yellow]"
            else:
                score_text = f"[red]{activity_score:.2f}[/red]"

            # Use compact format for commits ahead
            commits_ahead = fork_data["commits_ahead"]
            if commits_ahead == 0:
                commits_compact = ""  # Empty cell for no commits ahead
            else:
                commits_compact = f"[green]+{commits_ahead}[/green]"

            table.add_row(
                str(i),
                fork.name,
                fork.owner,
                f"⭐{fork.stars}",
                commits_compact,
                score_text,
                fork_data["last_activity"],
                fork.language or "N/A",
            )

        self.console.print(table)

    def _display_filter_criteria(self, filters: PromisingForksFilter) -> None:
        """Display the filter criteria used for promising forks.

        Args:
            filters: Filter criteria object
        """
        criteria_text = f"""
[bold cyan]Filter Criteria:[/bold cyan]
• Minimum Stars: {filters.min_stars}
• Minimum Commits Ahead: {filters.min_commits_ahead}
• Maximum Days Since Activity: {filters.max_days_since_activity}
• Minimum Activity Score: {filters.min_activity_score:.2f}
• Exclude Archived: {'Yes' if filters.exclude_archived else 'No'}
• Exclude Disabled: {'Yes' if filters.exclude_disabled else 'No'}
        """.strip()

        if filters.min_fork_age_days > 0:
            criteria_text += f"\n• Minimum Fork Age: {filters.min_fork_age_days} days"

        if filters.max_fork_age_days:
            criteria_text += f"\n• Maximum Fork Age: {filters.max_fork_age_days} days"

        panel = Panel(
            criteria_text, title="Promising Forks Analysis", border_style="blue"
        )
        self.console.print(panel)

    async def _fetch_commits_concurrently(
        self,
        forks_data: list,
        show_commits: int,
        base_owner: str,
        base_repo: str,
        force_all_commits: bool = False,
        column_width: int = 50,
    ) -> dict[str, str]:
        """Fetch commits ahead for multiple forks concurrently with progress tracking and optimization.

        Args:
            forks_data: List of fork data objects
            show_commits: Number of commits ahead to fetch for each fork
            base_owner: Base repository owner
            base_repo: Base repository name
            force_all_commits: If True, bypass optimization and fetch commits for all forks
            column_width: Column width for commit formatting

        Returns:
            Dictionary mapping fork keys (owner/name) to formatted commit strings
        """
        if show_commits <= 0 or not forks_data:
            return {}

        # Separate forks that can be skipped from those needing commit downloads
        forks_to_skip = []
        forks_needing_commits = []

        for fork_data in forks_data:
            fork_key = f"{fork_data.metrics.owner}/{fork_data.metrics.name}"

            # Check if fork can be skipped (no commits ahead) unless force_all_commits is True
            if (
                not force_all_commits
                and hasattr(fork_data.metrics, "can_skip_analysis")
                and fork_data.metrics.can_skip_analysis
            ):
                forks_to_skip.append((fork_key, fork_data))
            else:
                forks_needing_commits.append((fork_key, fork_data))

        # Initialize commits cache with skipped forks
        commits_cache = {}

        # Add "No commits ahead" message for skipped forks
        for fork_key, _fork_data in forks_to_skip:
            commits_cache[fork_key] = "[dim]No commits ahead[/dim]"

        # Log optimization statistics
        skipped_count = len(forks_to_skip)
        processing_count = len(forks_needing_commits)
        total_forks = len(forks_data)

        if skipped_count > 0:
            logger.info(
                f"Commit download optimization: Skipped {skipped_count}/{total_forks} forks with no commits ahead"
            )
            self.console.print(
                f"[dim]Skipped {skipped_count} forks with no commits ahead (saved {skipped_count} API calls)[/dim]"
            )

        # If no forks need commit downloads, return early
        if not forks_needing_commits:
            self.console.print("[dim]No forks require commit downloads[/dim]")
            return commits_cache

        # Create semaphore to limit concurrent requests (respect rate limits)
        # Use optimized batch processing to eliminate redundant parent repo requests
        try:
            # Prepare fork data for batch processing
            fork_data_list = [
                (fork_data.metrics.owner, fork_data.metrics.name)
                for fork_key, fork_data in forks_needing_commits
            ]
            
            logger.info(f"Using optimized batch processing for {len(fork_data_list)} forks")
            
            # Batch process all forks against the same parent repository
            batch_results = await self.github_client.get_commits_ahead_batch(
                fork_data_list, base_owner, base_repo, count=show_commits
            )
            
            # Format results for display
            for fork_key, fork_data in forks_needing_commits:
                fork_full_name = f"{fork_data.metrics.owner}/{fork_data.metrics.name}"
                commits_ahead = batch_results.get(fork_full_name, [])
                
                formatted_commits = self.format_recent_commits(
                    commits_ahead, column_width
                )
                commits_cache[fork_key] = formatted_commits
                
        except Exception as e:
            logger.warning(f"Batch processing failed, falling back to individual requests: {e}")
            
            # Fallback to original method if batch processing fails
            semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent requests

            async def fetch_fork_commits(
                fork_key: str, fork_data, base_owner: str, base_repo: str
            ) -> tuple[str, str]:
                """Fetch commits ahead for a single fork with rate limiting."""
                async with semaphore:
                    try:
                        # Add small delay to respect rate limits
                        await asyncio.sleep(0.1)

                        # Get commits ahead instead of recent commits
                        commits_ahead = await self.github_client.get_commits_ahead(
                            fork_data.metrics.owner,
                            fork_data.metrics.name,
                            base_owner,
                            base_repo,
                            count=show_commits,
                        )
                        formatted_commits = self.format_recent_commits(
                            commits_ahead, column_width
                        )
                        return fork_key, formatted_commits
                    except Exception as e:
                        logger.debug(f"Failed to fetch commits ahead for {fork_key}: {e}")
                        return fork_key, "[dim]No commits available[/dim]"

            # Show progress indicator for commit fetching (fallback mode)
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.progress_console,
            ) as progress:
                task = progress.add_task(
                    f"Fetching recent commits for {processing_count} forks (skipped {skipped_count})...",
                    total=processing_count,
                )

                # Create tasks for concurrent execution
                tasks = []
                for fork_key, fork_data in forks_needing_commits:
                    task_coro = fetch_fork_commits(
                        fork_key, fork_data, base_owner, base_repo
                    )
                    tasks.append(task_coro)

                # Execute tasks concurrently with progress updates
                completed_count = 0
                for coro in asyncio.as_completed(tasks):
                    try:
                        fork_key, formatted_commits = await coro
                        commits_cache[fork_key] = formatted_commits
                        completed_count += 1

                        # Update progress
                        progress.update(
                            task,
                            advance=1,
                            description=f"Fetched commits for {completed_count}/{processing_count} forks (skipped {skipped_count})",
                        )
                    except Exception as e:
                        logger.warning(f"Failed to fetch commits for fork: {e}")
                        completed_count += 1
                        progress.update(task, advance=1)

        # Log final statistics
        api_calls_saved = skipped_count
        total_potential_calls = total_forks

        if api_calls_saved > 0:
            savings_percentage = (api_calls_saved / total_potential_calls) * 100
            self.console.print(
                f"[green]✓ Commit download optimization saved {api_calls_saved} API calls ({savings_percentage:.1f}% reduction)[/green]"
            )

        return commits_cache

    async def _get_and_format_commits_ahead(
        self,
        fork_owner: str,
        fork_repo: str,
        base_owner: str,
        base_repo: str,
        count: int,
    ) -> str:
        """Get and format commits ahead for a fork.

        Args:
            fork_owner: Fork owner
            fork_repo: Fork repository name
            base_owner: Base repository owner
            base_repo: Base repository name
            count: Number of commits ahead to fetch

        Returns:
            Formatted string with commits ahead, each on a separate line
        """
        try:
            commits_ahead = await self.github_client.get_commits_ahead(
                fork_owner, fork_repo, base_owner, base_repo, count=count
            )
            # Calculate column width for formatting (use a reasonable default)
            column_width = 50  # This will be passed from the calling method
            return self.format_recent_commits(commits_ahead, column_width)
        except Exception as e:
            logger.debug(
                f"Failed to fetch commits ahead for {fork_owner}/{fork_repo}: {e}"
            )
            return "[dim]No commits available[/dim]"

    def format_recent_commits(self, commits: list, column_width: int = 50) -> str:
        """Format recent commits for display in table with improved formatting.

        This method provides clear, scannable formatting with consistent date display,
        proper column width management, and chronological ordering (newest first).

        Args:
            commits: List of RecentCommit objects
            column_width: Available column width for formatting (default: 50)

        Returns:
            Formatted string with each commit on a separate line, chronologically ordered (newest first)
            Format: "YYYY-MM-DD abc1234 commit message" or "abc1234: commit message" (fallback)
        """
        if not commits:
            return "[dim]No commits[/dim]"

        # Sort commits chronologically (newest first)
        sorted_commits = self._sort_commits_chronologically(commits)

        # Calculate max message length based on column width
        # Format: "YYYY-MM-DD abc1234 message"
        # Base width: 10 (date) + 1 (space) + 7 (hash) + 1 (space) = 19
        base_width = 19
        max_message_length = max(
            10, column_width - base_width - 2
        )  # Reserve 2 chars for padding

        # Format: YYYY-MM-DD hash commit message for each commit
        formatted_commits = []
        for commit in sorted_commits:
            if commit.date:
                # Use consistent YYYY-MM-DD date format
                date_str = self._format_commit_date(commit.date)
                # Truncate message for table display if needed
                truncated_message = self._truncate_commit_message(
                    commit.message, max_message_length
                )
                formatted_commits.append(
                    f"{date_str} {commit.short_sha} {truncated_message}"
                )
            else:
                # Fallback to old format if date is not available
                # Format: "abc1234: message"
                # Base width: 7 (hash) + 2 (colon and space) = 9
                fallback_base_width = 9
                fallback_max_message_length = max(
                    10, column_width - fallback_base_width - 2
                )
                truncated_message = self._truncate_commit_message(
                    commit.message, fallback_max_message_length
                )
                formatted_commits.append(f"{commit.short_sha}: {truncated_message}")

        # Join with newlines for multi-line display in table cell
        return "\n".join(formatted_commits)

    def _format_commit_date(self, date: datetime) -> str:
        """Format commit date consistently as YYYY-MM-DD.

        Args:
            date: Commit datetime

        Returns:
            Formatted date string in YYYY-MM-DD format
        """
        return date.strftime("%Y-%m-%d")

    def _sort_commits_chronologically(self, commits: list) -> list:
        """Sort commits chronologically with newest first.

        Args:
            commits: List of RecentCommit objects

        Returns:
            List of commits sorted by date (newest first), with commits without dates at the end
        """
        # Separate commits with and without dates
        commits_with_dates = [c for c in commits if c.date is not None]
        commits_without_dates = [c for c in commits if c.date is None]

        # Sort commits with dates (newest first)
        commits_with_dates.sort(key=lambda c: c.date, reverse=True)

        # Return sorted commits with dates first, then commits without dates
        return commits_with_dates + commits_without_dates

    def _truncate_commit_message(self, message: str, max_length: int) -> str:
        """Return the full commit message without truncation.

        Args:
            message: Original commit message
            max_length: Maximum allowed length (ignored - kept for compatibility)

        Returns:
            Full commit message without truncation
        """
        if not message:
            return ""
        
        # Return the full message without any truncation
        return message

    def calculate_commits_column_width(
        self,
        commits_data: dict,
        show_commits: int,
        min_width: int = 30,
        max_width: int = 60,
    ) -> int:
        """Calculate optimal width for Recent Commits column based on actual content.

        This method analyzes the actual commit data to determine the best column width
        that balances readability with table layout constraints.

        Args:
            commits_data: Dictionary mapping fork keys to commit lists
            show_commits: Number of commits to show per fork
            min_width: Minimum column width (default: 30)
            max_width: Maximum column width (default: 60)

        Returns:
            Optimal column width for Recent Commits column, bounded by min/max constraints
        """
        if not commits_data or show_commits == 0:
            return min_width

        max_content_width = 0
        sample_count = 0
        total_message_length = 0

        for fork_commits in commits_data.values():
            if fork_commits:
                # Calculate width needed for this fork's commits
                sorted_commits = self._sort_commits_chronologically(
                    fork_commits[:show_commits]
                )
                for commit in sorted_commits:
                    sample_count += 1

                    if commit.date:
                        # Format: "YYYY-MM-DD abc1234 message"
                        # Date: 10 chars, space: 1, hash: 7, space: 1, message: variable
                        base_width = 19  # 10 + 1 + 7 + 1
                        message_width = len(commit.message)
                        total_width = base_width + message_width
                        max_content_width = max(max_content_width, total_width)
                        total_message_length += message_width
                    else:
                        # Format: "abc1234: message"
                        # Hash: 7, colon and space: 2, message: variable
                        base_width = 9  # 7 + 2
                        message_width = len(commit.message)
                        total_width = base_width + message_width
                        max_content_width = max(max_content_width, total_width)
                        total_message_length += message_width

        # Calculate average message length for better width estimation
        if sample_count > 0:
            avg_message_length = total_message_length / sample_count
            # Use average + some buffer for more reasonable width
            estimated_width = 19 + int(avg_message_length * 1.2)  # 20% buffer
            # Take the smaller of max content width and estimated width
            optimal_width = min(max_content_width, estimated_width)
        else:
            optimal_width = min_width

        # Return width within bounds, accounting for padding
        return max(min_width, min(max_width, optimal_width + 4))  # 4 chars padding

    def _display_forks_preview_table(self, fork_items: list[dict[str, Any]]) -> None:
        """Display forks preview in a lightweight table format with compact commit formatting.

        Args:
            fork_items: List of fork preview item dictionaries
        """
        if not fork_items:
            self.console.print("[yellow]No forks found.[/yellow]")
            return

        table = Table(
            title=f"Forks Preview ({len(fork_items)} forks found)",
            expand=False       # Don't expand to full console width
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("Fork Name", style="cyan", min_width=25)
        table.add_column("Owner", style="blue", min_width=15)
        table.add_column("Stars", style="yellow", justify="right", width=8)
        table.add_column("Last Push", style="magenta", width=15)
        table.add_column("Commits", style="green", width=13)

        for i, fork_item in enumerate(fork_items, 1):
            # Format last push date
            last_push = self._format_datetime(fork_item["last_push_date"])

            # Use compact format for commits ahead status
            commits_ahead = fork_item["commits_ahead"]
            if commits_ahead == "None":
                commits_compact = ""  # Empty cell for no commits ahead
            elif commits_ahead == "Unknown":
                commits_compact = (
                    "[green]+?[/green]"  # Unknown but potentially has commits
                )
            else:
                commits_compact = self._style_commits_ahead_status(commits_ahead)

            table.add_row(
                str(i),
                fork_item["name"],
                fork_item["owner"],
                f"⭐{fork_item['stars']}",
                last_push,
                commits_compact,
            )

        self.console.print(table)
    async def _render_fork_table(
        self,
        fork_data_list: list,
        table_context: dict,
        show_commits: int = 0,
        force_all_commits: bool = False,
        csv_export: bool = False
    ) -> None:
        """Universal fork table rendering method.
        
        Args:
            fork_data_list: List of fork data objects
            table_context: Context information (owner, repo, mode, etc.)
            show_commits: Number of recent commits to show
            force_all_commits: Whether to fetch commits for all forks
            csv_export: If True, export data in CSV format instead of table format
        """
        if not fork_data_list:
            if csv_export:
                # For CSV export, just output empty CSV with headers
                self._export_csv_data([], table_context, show_commits)
            else:
                self.console.print("[yellow]No forks found for display.[/yellow]")
            return

        # Handle CSV export mode
        if csv_export:
            await self._export_csv_data(fork_data_list, table_context, show_commits, force_all_commits)
            return

        # 1. Determine rendering mode and capabilities
        has_exact_counts = table_context.get("has_exact_counts", False)
        owner = table_context["owner"]
        repo = table_context["repo"]

        # 2. Sort data consistently
        sorted_forks = self._sort_forks_universal(fork_data_list, has_exact_counts)

        # 3. Create consistent table structure
        table_title = self._build_table_title(sorted_forks, table_context, show_commits)
        fork_table = Table(
            title=table_title,
            expand=False       # Don't expand to full console width
        )

        # 4. Add standard columns with unified widths
        self._add_standard_columns(fork_table)

        # 5. Conditionally add Recent Commits column
        if show_commits > 0:
            commits_width = self._calculate_commits_column_width_universal(
                fork_data_list, show_commits
            )
            fork_table.add_column(
                "Recent Commits",
                style=ForkTableConfig.COLUMN_STYLES["recent_commits"],
                # Remove fixed width to prevent truncation
                no_wrap=True,
                overflow="fold",
                max_width=None  # Remove maximum width restriction
            )

        # 6. Fetch commits if needed
        commits_cache = {}
        if show_commits > 0:
            commits_cache = await self._fetch_commits_concurrently(
                sorted_forks, show_commits, owner, repo, force_all_commits
            )

        # 7. Populate table rows
        for fork_data in sorted_forks:
            row_data = self._build_table_row(
                fork_data, has_exact_counts, commits_cache, show_commits
            )
            fork_table.add_row(*row_data)

        # 8. Display table and summary
        self._display_table_with_context(fork_table, table_context)

    def _sort_forks_universal(self, fork_data_list: list, has_exact_counts: bool) -> list:
        """Universal fork sorting that handles both data types.
        
        Args:
            fork_data_list: List of fork data objects
            has_exact_counts: Whether exact commit counts are available
            
        Returns:
            Sorted list of fork data
        """
        if has_exact_counts:
            # Detailed mode: sort by exact commits ahead, then by stars
            return sorted(
                fork_data_list,
                key=lambda x: (
                    x.exact_commits_ahead if isinstance(x.exact_commits_ahead, int) else -1,
                    x.metrics.stargazers_count,
                ),
                reverse=True,
            )
        else:
            # Standard mode: use enhanced multi-level sorting
            return self._sort_forks_enhanced(fork_data_list)

    def _build_table_title(self, sorted_forks: list, table_context: dict, show_commits: int) -> str:
        """Build consistent table title based on context.
        
        Args:
            sorted_forks: Sorted list of fork data
            table_context: Context information
            show_commits: Number of recent commits to show
            
        Returns:
            Formatted table title string
        """
        has_exact_counts = table_context.get("has_exact_counts", False)
        title_suffix = f" (showing {show_commits} recent commits)" if show_commits > 0 else ""

        if has_exact_counts:
            return f"Detailed Forks ({len(sorted_forks)} active forks with exact commit counts){title_suffix}"
        else:
            return f"All Forks ({len(sorted_forks)} displayed, sorted by commits status, stars, forks, activity){title_suffix}"

    def _add_standard_columns(self, fork_table: Table) -> None:
        """Add standard columns with unified configuration.
        
        Args:
            fork_table: Rich Table object to configure
        """
        config = ForkTableConfig

        fork_table.add_column(
            "URL",
            style=config.COLUMN_STYLES["url"],
            min_width=config.COLUMN_WIDTHS["url"],
            no_wrap=True,
            overflow="fold"
        )
        fork_table.add_column(
            "Stars",
            style=config.COLUMN_STYLES["stars"],
            justify="right",
            width=config.COLUMN_WIDTHS["stars"],
            no_wrap=True,
            overflow="fold"
        )
        fork_table.add_column(
            "Forks",
            style=config.COLUMN_STYLES["forks"],
            justify="right",
            width=config.COLUMN_WIDTHS["forks"],
            no_wrap=True,
            overflow="fold"
        )
        fork_table.add_column(
            "Commits",
            style=config.COLUMN_STYLES["commits"],
            justify="right",
            width=config.COLUMN_WIDTHS["commits"],
            no_wrap=True,
            overflow="fold"
        )
        fork_table.add_column(
            "Last Push",
            style=config.COLUMN_STYLES["last_push"],
            width=config.COLUMN_WIDTHS["last_push"],
            no_wrap=True,
            overflow="fold"
        )

    def _calculate_commits_column_width_universal(
        self, fork_data_list: list, show_commits: int
    ) -> int:
        """Calculate optimal width for Recent Commits column (universal version).
        
        Args:
            fork_data_list: List of fork data objects
            show_commits: Number of commits to show
            
        Returns:
            Optimal column width
        """
        # Use existing calculation method but with universal data handling
        min_width = ForkTableConfig.COLUMN_WIDTHS["recent_commits_base"]
        max_width = 1000  # Much larger for wide console output

        # For now, use a reasonable default based on show_commits - no truncation
        # This can be enhanced later with actual commit data analysis
        base_width = 19  # Date and hash with spaces
        estimated_message_width = min(800, 1000 // max(1, show_commits))  # Much larger for full messages
        commits_width = max(min_width, min(max_width, base_width + estimated_message_width))

        return commits_width

    def _build_table_row(
        self,
        fork_data,
        has_exact_counts: bool,
        commits_cache: dict,
        show_commits: int
    ) -> list:
        """Build table row data for a fork.
        
        Args:
            fork_data: Fork data object
            has_exact_counts: Whether exact commit counts are available
            commits_cache: Cache of commit data
            show_commits: Number of recent commits to show
            
        Returns:
            List of formatted row data
        """
        # Get metrics (handle both data structures)
        metrics = getattr(fork_data, "metrics", fork_data)

        # Format URL
        fork_url = self._format_fork_url(metrics.owner, metrics.name)

        # Format commit information using adaptive formatter
        commits_display = CommitDataFormatter.format_commit_info(fork_data, has_exact_counts)

        # Format last push date
        last_push = self._format_datetime(metrics.pushed_at)

        # Prepare row data
        row_data = [
            fork_url,
            str(metrics.stargazers_count),
            str(metrics.forks_count),
            commits_display,
            last_push,
        ]

        # Add recent commits data from cache if requested
        if show_commits > 0:
            fork_key = f"{metrics.owner}/{metrics.name}"
            recent_commits_text = commits_cache.get(
                fork_key, "[dim]No commits available[/dim]"
            )
            row_data.append(recent_commits_text)

        return row_data

    def _display_table_with_context(self, fork_table: Table, table_context: dict) -> None:
        """Display table with consistent context and summary information.
        
        Args:
            fork_table: Configured Rich Table object
            table_context: Context information for display
        """
        owner = table_context["owner"]
        repo = table_context["repo"]
        has_exact_counts = table_context.get("has_exact_counts", False)
        api_calls_made = table_context.get("api_calls_made", 0)
        api_calls_saved = table_context.get("api_calls_saved", 0)

        # Display header
        mode_name = "Detailed" if has_exact_counts else "Fork Data Summary"
        self.console.print(f"\n[bold blue]{mode_name} for {owner}/{repo}[/bold blue]")
        self.console.print("=" * 80)

        # Display the table
        self.console.print(fork_table)

        # Display summary information
        if has_exact_counts:
            # Detailed mode summary
            self._display_detailed_summary(table_context)
        else:
            # Standard mode summary (if qualification_result is available)
            qualification_result = table_context.get("qualification_result")
            if qualification_result:
                self._display_standard_summary(qualification_result)

    def _display_detailed_summary(self, table_context: dict) -> None:
        """Display summary for detailed mode.
        
        Args:
            table_context: Context information
        """
        api_calls_made = table_context.get("api_calls_made", 0)
        api_calls_saved = table_context.get("api_calls_saved", 0)

        # Calculate summary statistics from the context if available
        detailed_forks = table_context.get("fork_data_list", [])

        total_commits_ahead = sum(
            fork.exact_commits_ahead
            for fork in detailed_forks
            if hasattr(fork, "exact_commits_ahead") and isinstance(fork.exact_commits_ahead, int)
        )
        forks_with_commits = len(
            [
                fork
                for fork in detailed_forks
                if hasattr(fork, "exact_commits_ahead")
                and isinstance(fork.exact_commits_ahead, int)
                and fork.exact_commits_ahead > 0
            ]
        )

        self.console.print("\n[bold]Summary:[/bold]")
        self.console.print(f"• {forks_with_commits} forks have commits ahead")
        self.console.print(f"• {total_commits_ahead} total commits ahead across all forks")
        self.console.print(f"• {api_calls_made} API calls made for exact commit counts")

        if api_calls_saved > 0:
            self.console.print(f"• {api_calls_saved} API calls saved by smart filtering")
            efficiency_percent = (api_calls_saved / (api_calls_made + api_calls_saved)) * 100
            self.console.print(f"• {efficiency_percent:.1f}% API efficiency improvement")

        self.console.print("• Exact commit counts fetched using GitHub compare API")

    def _display_standard_summary(self, qualification_result) -> None:
        """Display summary for standard mode.
        
        Args:
            qualification_result: QualifiedForksResult object
        """
        # Display summary statistics (existing logic from _display_fork_data_table)
        stats = qualification_result.stats

        summary_table = Table(title="Collection Summary", expand=False)
        summary_table.add_column("Metric", style="cyan", width=25, no_wrap=True)
        summary_table.add_column("Count", style="green", justify="right", width=10, no_wrap=True)
        summary_table.add_column("Percentage", style="yellow", justify="right", width=12)

        total = stats.total_forks_discovered
        summary_table.add_row("Total Forks", str(total), "100.0%")
        summary_table.add_row(
            "Need Analysis",
            str(stats.forks_with_commits),
            f"{stats.analysis_candidate_percentage:.1f}%",
        )
        summary_table.add_row(
            "Can Skip",
            str(stats.forks_with_no_commits),
            f"{stats.skip_rate_percentage:.1f}%",
        )
        summary_table.add_row(
            "Archived",
            str(stats.archived_forks),
            f"{(stats.archived_forks/total*100) if total > 0 else 0:.1f}%",
        )
        summary_table.add_row(
            "Disabled",
            str(stats.disabled_forks),
            f"{(stats.disabled_forks/total*100) if total > 0 else 0:.1f}%",
        )

        self.console.print(summary_table)
    def _convert_collected_fork_to_repository(self, collected_fork) -> Repository:
        """Convert CollectedForkData to Repository object for filtering.
        
        Args:
            collected_fork: CollectedForkData object
            
        Returns:
            Repository object compatible with ahead-only filter
        """
        metrics = collected_fork.metrics
        
        return Repository(
            id=metrics.id,
            owner=metrics.owner,
            name=metrics.name,
            full_name=metrics.full_name,
            url=f"https://api.github.com/repos/{metrics.full_name}",
            html_url=metrics.html_url,
            clone_url=f"https://github.com/{metrics.full_name}.git",
            default_branch=metrics.default_branch,
            stars=metrics.stargazers_count,
            forks_count=metrics.forks_count,
            watchers_count=metrics.watchers_count,
            open_issues_count=metrics.open_issues_count,
            size=metrics.size,
            language=metrics.language,
            description=metrics.description,
            topics=metrics.topics,
            license_name=metrics.license_name,
            is_private=False,  # Forks are typically public
            is_fork=metrics.fork,
            is_archived=metrics.archived,
            is_disabled=metrics.disabled,
            created_at=metrics.created_at,
            updated_at=metrics.updated_at,
            pushed_at=metrics.pushed_at,
        )

    async def _export_csv_data(
        self,
        fork_data_list: list,
        table_context: dict,
        show_commits: int = 0,
        force_all_commits: bool = False
    ) -> None:
        """Export fork data in CSV format to stdout using CSVExporter.
        
        Args:
            fork_data_list: List of fork data objects
            table_context: Context information (owner, repo, mode, etc.)
            show_commits: Number of recent commits to show
            force_all_commits: Whether to fetch commits for all forks
        """
        from forklift.reporting.csv_exporter import CSVExporter, CSVExportConfig
        from forklift.models.analysis import ForksPreview, ForkPreviewItem
        import sys
        
        try:
            if not fork_data_list:
                # Output empty CSV with headers only
                config = CSVExportConfig(
                    include_commits=(show_commits > 0),
                    detail_mode=table_context.get("has_exact_counts", False),
                    include_urls=True
                )
                exporter = CSVExporter(config)
                empty_preview = ForksPreview(total_forks=0, forks=[])
                csv_content = exporter.export_forks_preview(empty_preview)
                sys.stdout.write(csv_content)
                return

            # Determine rendering mode and capabilities
            has_exact_counts = table_context.get("has_exact_counts", False)
            owner = table_context["owner"]
            repo = table_context["repo"]

            # Sort data consistently
            sorted_forks = self._sort_forks_universal(fork_data_list, has_exact_counts)

            # Fetch raw commits data if needed (for CSV we need the raw commit objects, not formatted strings)
            raw_commits_cache = {}
            if show_commits > 0:
                raw_commits_cache = await self._fetch_raw_commits_for_csv(
                    sorted_forks, show_commits, owner, repo, force_all_commits
                )

            # Convert fork data to ForkPreviewItem format for CSV export
            fork_preview_items = []
            for fork_data in sorted_forks:
                preview_item = self._convert_fork_data_to_preview_item_csv(
                    fork_data, has_exact_counts, raw_commits_cache, show_commits
                )
                fork_preview_items.append(preview_item)

            # Create ForksPreview object
            forks_preview = ForksPreview(
                total_forks=len(fork_preview_items),
                forks=fork_preview_items
            )

            # Configure CSV exporter
            config = CSVExportConfig(
                include_commits=(show_commits > 0),
                detail_mode=has_exact_counts,
                include_urls=True,
                max_commits_per_fork=show_commits
            )
            exporter = CSVExporter(config)

            # Export to CSV and write to stdout
            csv_content = exporter.export_forks_preview(forks_preview)
            sys.stdout.write(csv_content)

        except Exception as e:
            # Send errors to stderr to keep stdout clean for CSV data
            import sys
            sys.stderr.write(f"Error exporting CSV data: {e}\n")
            sys.stderr.flush()
            raise

    def _build_csv_row(
        self,
        fork_data,
        has_exact_counts: bool,
        commits_cache: dict,
        show_commits: int
    ) -> list:
        """Build a CSV row for fork data.
        
        Args:
            fork_data: Fork data object
            has_exact_counts: Whether exact commit counts are available
            commits_cache: Cache of commit data
            show_commits: Number of recent commits to show
            
        Returns:
            List of values for CSV row
        """
        # Extract basic fork information
        if hasattr(fork_data, 'metrics'):
            # Standard fork data
            metrics = fork_data.metrics
            fork_url = metrics.html_url
            owner = metrics.full_name.split('/')[0]
            stars = metrics.stargazers_count
            forks = metrics.forks_count
            language = metrics.language or ""
            last_push = self._format_datetime(metrics.pushed_at) if metrics.pushed_at else ""
            
            # Format commits information
            if has_exact_counts and hasattr(fork_data, 'exact_commits_ahead'):
                if isinstance(fork_data.exact_commits_ahead, int):
                    commits = str(fork_data.exact_commits_ahead) if fork_data.exact_commits_ahead > 0 else ""
                else:
                    commits = "Unknown"
            else:
                # Use status-based information
                if hasattr(fork_data, 'commits_ahead_status'):
                    if fork_data.commits_ahead_status == "no_commits":
                        commits = "0"
                    elif fork_data.commits_ahead_status == "has_commits":
                        commits = "Has commits"
                    else:
                        commits = "Unknown"
                else:
                    commits = "Unknown"
        else:
            # Detailed fork data structure
            fork_url = getattr(fork_data, 'html_url', '')
            owner = getattr(fork_data, 'owner', {}).get('login', '') if hasattr(fork_data, 'owner') else ''
            stars = getattr(fork_data, 'stargazers_count', 0)
            forks = getattr(fork_data, 'forks_count', 0)
            language = getattr(fork_data, 'language', '') or ""
            last_push = self._format_datetime(getattr(fork_data, 'pushed_at', None)) if getattr(fork_data, 'pushed_at', None) else ""
            
            # For detailed data, check exact commits ahead
            if hasattr(fork_data, 'exact_commits_ahead'):
                if isinstance(fork_data.exact_commits_ahead, int):
                    commits = str(fork_data.exact_commits_ahead) if fork_data.exact_commits_ahead > 0 else ""
                else:
                    commits = "Unknown"
            else:
                commits = "Unknown"

        # Build base row
        row = [fork_url, owner, stars, forks, commits, last_push, language]

        # Add recent commits if requested
        if show_commits > 0:
            fork_key = fork_url
            if fork_key in commits_cache:
                commit_messages = []
                for commit in commits_cache[fork_key][:show_commits]:
                    # Clean commit message for CSV (remove newlines, quotes)
                    message = commit.get('message', '').replace('\n', ' ').replace('\r', ' ')
                    message = message.replace('"', '""')  # Escape quotes for CSV
                    commit_messages.append(message)
                recent_commits = "; ".join(commit_messages)
            else:
                recent_commits = ""
            row.append(recent_commits)

        return row

    async def _fetch_raw_commits_for_csv(
        self,
        forks_data: list,
        show_commits: int,
        base_owner: str,
        base_repo: str,
        force_all_commits: bool = False,
    ) -> dict[str, list]:
        """Fetch raw commit data for CSV export (returns RecentCommit objects, not formatted strings).

        Args:
            forks_data: List of fork data objects
            show_commits: Number of commits ahead to fetch for each fork
            base_owner: Base repository owner
            base_repo: Base repository name
            force_all_commits: If True, bypass optimization and fetch commits for all forks

        Returns:
            Dictionary mapping fork URLs to lists of RecentCommit objects
        """
        if show_commits <= 0 or not forks_data:
            return {}

        # Separate forks that can be skipped from those needing commit downloads
        forks_to_skip = []
        forks_needing_commits = []

        for fork_data in forks_data:
            fork_url = fork_data.metrics.html_url

            # Check if fork can be skipped (no commits ahead) unless force_all_commits is True
            if (
                not force_all_commits
                and hasattr(fork_data.metrics, "can_skip_analysis")
                and fork_data.metrics.can_skip_analysis
            ):
                forks_to_skip.append((fork_url, fork_data))
            else:
                forks_needing_commits.append((fork_url, fork_data))

        # Initialize commits cache with skipped forks
        raw_commits_cache = {}

        # Add empty list for skipped forks
        for fork_url, _fork_data in forks_to_skip:
            raw_commits_cache[fork_url] = []

        # If no forks need commit downloads, return early
        if not forks_needing_commits:
            return raw_commits_cache

        try:
            # Prepare fork data for batch processing
            fork_data_list = [
                (fork_data.metrics.owner, fork_data.metrics.name)
                for fork_url, fork_data in forks_needing_commits
            ]
            
            # Batch process all forks against the same parent repository
            batch_results = await self.github_client.get_commits_ahead_batch(
                fork_data_list, base_owner, base_repo, count=show_commits
            )
            
            # Store raw commit objects for CSV processing
            for fork_url, fork_data in forks_needing_commits:
                fork_full_name = f"{fork_data.metrics.owner}/{fork_data.metrics.name}"
                commits_ahead = batch_results.get(fork_full_name, [])
                raw_commits_cache[fork_url] = commits_ahead
                
        except Exception as e:
            logger.warning(f"Batch processing failed for CSV export: {e}")
            # For CSV export, we'll just return empty commits on failure
            for fork_url, _fork_data in forks_needing_commits:
                raw_commits_cache[fork_url] = []

        return raw_commits_cache

    def _convert_fork_data_to_preview_item_csv(
        self,
        fork_data,
        has_exact_counts: bool,
        raw_commits_cache: dict,
        show_commits: int
    ) -> "ForkPreviewItem":
        """Convert fork data to ForkPreviewItem for CSV export with proper commit formatting.
        
        Args:
            fork_data: Fork data object
            has_exact_counts: Whether exact commit counts are available
            raw_commits_cache: Cache of raw RecentCommit objects
            show_commits: Number of recent commits to show
            
        Returns:
            ForkPreviewItem object for CSV export
        """
        from forklift.models.analysis import ForkPreviewItem
        
        # Extract basic fork information
        if hasattr(fork_data, 'metrics'):
            # Standard fork data
            metrics = fork_data.metrics
            fork_url = metrics.html_url
            owner = metrics.full_name.split('/')[0]
            name = metrics.full_name.split('/')[1]
            stars = metrics.stargazers_count
            last_push_date = metrics.pushed_at
            
            # Format commits information for CSV export
            if has_exact_counts and hasattr(fork_data, 'exact_commits_ahead'):
                if isinstance(fork_data.exact_commits_ahead, int):
                    # In detail mode CSV, use "+X" format for exact counts, empty for zero
                    commits_ahead = f"+{fork_data.exact_commits_ahead}" if fork_data.exact_commits_ahead > 0 else ""
                else:
                    commits_ahead = "Unknown"
            else:
                # Use status-based information from metrics
                status = metrics.commits_ahead_status
                if status == "No commits ahead":
                    commits_ahead = "None"
                elif status == "Has commits":
                    commits_ahead = "Unknown"
                else:
                    commits_ahead = "Unknown"
                    
            # Determine activity status
            activity_status = getattr(fork_data, 'activity_status', 'Unknown')
            
        else:
            # Detailed fork data structure
            fork_url = getattr(fork_data, 'html_url', '')
            owner_obj = getattr(fork_data, 'owner', {})
            owner = owner_obj.get('login', '') if isinstance(owner_obj, dict) else getattr(owner_obj, 'login', '')
            name = getattr(fork_data, 'name', '')
            stars = getattr(fork_data, 'stargazers_count', 0)
            last_push_date = getattr(fork_data, 'pushed_at', None)
            
            # For detailed data, check exact commits ahead
            if hasattr(fork_data, 'exact_commits_ahead'):
                if isinstance(fork_data.exact_commits_ahead, int):
                    # In detail mode CSV, use "+X" format for exact counts, empty for zero
                    commits_ahead = f"+{fork_data.exact_commits_ahead}" if fork_data.exact_commits_ahead > 0 else ""
                else:
                    commits_ahead = "Unknown"
            else:
                commits_ahead = "Unknown"
                
            activity_status = "Unknown"

        # Format recent commits for CSV export with date, hash, and message
        recent_commits_text = ""
        if show_commits > 0:
            if fork_url in raw_commits_cache:
                commit_entries = []
                for commit in raw_commits_cache[fork_url][:show_commits]:
                    # Format consistently with table display: "YYYY-MM-DD hash message"
                    if commit.date:
                        date_str = commit.date.strftime("%Y-%m-%d")
                        formatted_commit = f"{date_str} {commit.short_sha} {commit.message}"
                    else:
                        # Fallback format: "hash: message"
                        formatted_commit = f"{commit.short_sha}: {commit.message}"
                    
                    commit_entries.append(formatted_commit)
                
                # Join multiple commits with semicolon separator for CSV
                recent_commits_text = "; ".join(commit_entries)

        return ForkPreviewItem(
            name=name,
            owner=owner,
            stars=stars,
            last_push_date=last_push_date,
            fork_url=fork_url,
            activity_status=activity_status,
            commits_ahead=commits_ahead,
            recent_commits=recent_commits_text if show_commits > 0 else None
        )

    def _convert_fork_data_to_preview_item(
        self,
        fork_data,
        has_exact_counts: bool,
        commits_cache: dict,
        show_commits: int
    ) -> "ForkPreviewItem":
        """Convert fork data to ForkPreviewItem for table display (legacy method).
        
        Args:
            fork_data: Fork data object
            has_exact_counts: Whether exact commit counts are available
            commits_cache: Cache of formatted commit strings
            show_commits: Number of recent commits to show
            
        Returns:
            ForkPreviewItem object for table display
        """
        from forklift.models.analysis import ForkPreviewItem
        
        # Extract basic fork information
        if hasattr(fork_data, 'metrics'):
            # Standard fork data
            metrics = fork_data.metrics
            fork_url = metrics.html_url
            owner = metrics.full_name.split('/')[0]
            name = metrics.full_name.split('/')[1]
            stars = metrics.stargazers_count
            last_push_date = metrics.pushed_at
            
            # Format commits information
            if has_exact_counts and hasattr(fork_data, 'exact_commits_ahead'):
                if isinstance(fork_data.exact_commits_ahead, int):
                    commits_ahead = str(fork_data.exact_commits_ahead) if fork_data.exact_commits_ahead > 0 else "None"
                else:
                    commits_ahead = "Unknown"
            else:
                # Use status-based information from metrics
                status = metrics.commits_ahead_status
                if status == "No commits ahead":
                    commits_ahead = "None"
                elif status == "Has commits":
                    commits_ahead = "Unknown"
                else:
                    commits_ahead = "Unknown"
                    
            # Determine activity status
            activity_status = getattr(fork_data, 'activity_status', 'Unknown')
            
        else:
            # Detailed fork data structure
            fork_url = getattr(fork_data, 'html_url', '')
            owner_obj = getattr(fork_data, 'owner', {})
            owner = owner_obj.get('login', '') if isinstance(owner_obj, dict) else getattr(owner_obj, 'login', '')
            name = getattr(fork_data, 'name', '')
            stars = getattr(fork_data, 'stargazers_count', 0)
            last_push_date = getattr(fork_data, 'pushed_at', None)
            
            # For detailed data, check exact commits ahead
            if hasattr(fork_data, 'exact_commits_ahead'):
                if isinstance(fork_data.exact_commits_ahead, int):
                    commits_ahead = str(fork_data.exact_commits_ahead) if fork_data.exact_commits_ahead > 0 else "None"
                else:
                    commits_ahead = "Unknown"
            else:
                commits_ahead = "Unknown"
                
            activity_status = "Unknown"

        # For table display, use the formatted commit strings from cache
        recent_commits_text = ""
        if show_commits > 0:
            fork_key = fork_url
            if fork_key in commits_cache:
                # commits_cache contains formatted strings for table display
                formatted_commits_string = commits_cache[fork_key]
                # Convert newline-separated commits to semicolon-separated for CSV compatibility
                if formatted_commits_string and not formatted_commits_string.startswith("[dim]"):
                    commit_lines = formatted_commits_string.split('\n')
                    recent_commits_text = "; ".join(commit_lines)

        return ForkPreviewItem(
            name=name,
            owner=owner,
            stars=stars,
            last_push_date=last_push_date,
            fork_url=fork_url,
            activity_status=activity_status,
            commits_ahead=commits_ahead,
            recent_commits=recent_commits_text if show_commits > 0 else None
        )