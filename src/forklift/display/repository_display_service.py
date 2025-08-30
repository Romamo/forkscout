"""Repository Display Service for incremental repository exploration."""

import asyncio
import logging
from datetime import datetime
from typing import Any

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

from forklift.github.client import GitHubClient
from forklift.models.analysis import ForkPreviewItem, ForksPreview
from forklift.models.filters import PromisingForksFilter
from forklift.models.github import Repository
from forklift.storage.analysis_cache import AnalysisCacheManager
from forklift.storage.cache_validation import CacheValidationError, CacheValidator

logger = logging.getLogger(__name__)


class RepositoryDisplayService:
    """Service for displaying repository information in a structured format."""

    def __init__(
        self,
        github_client: GitHubClient,
        console: Console | None = None,
        cache_manager: AnalysisCacheManager | None = None,
    ):
        """Initialize the repository display service.

        Args:
            github_client: GitHub API client for fetching data
            console: Rich console for output (optional, creates new if None)
            cache_manager: Cache manager for caching repository data (optional)
        """
        self.github_client = github_client
        self.console = console or Console()
        self.cache_manager = cache_manager

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
                key=lambda x: (x.stars, x.last_push_date or datetime.min), reverse=True
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
        table = Table(title=f"Repository Details: {repository.full_name}")
        table.add_column("Property", style="cyan", width=20)
        table.add_column("Value", style="green")

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

        table = Table(title=f"Fork Summary ({len(enhanced_forks)} forks found)")
        table.add_column("#", style="dim", width=4)
        table.add_column("Fork Name", style="cyan", min_width=25)
        table.add_column("Owner", style="blue", min_width=15)
        table.add_column("Stars", style="yellow", justify="right", width=8)
        table.add_column("Commits", style="green", justify="right", width=12)
        table.add_column("Last Activity", style="magenta", width=15)
        table.add_column("Status", style="white", width=10)
        table.add_column("Language", style="white", width=12)

        display_count = min(len(enhanced_forks), max_display)

        for i, fork_data in enumerate(enhanced_forks[:display_count], 1):
            fork = fork_data["fork"]

            # Style status with colors
            status = fork_data["activity_status"]
            status_styled = self._style_activity_status(status)

            # Format commits ahead/behind using compact format
            commits_ahead = fork_data["commits_ahead"]
            commits_behind = fork_data["commits_behind"]

            commits_status = self.format_commits_status(commits_ahead, commits_behind)

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

        summary_table = Table(title="Collection Summary")
        summary_table.add_column("Metric", style="cyan", width=25)
        summary_table.add_column("Count", style="green", justify="right", width=10)
        summary_table.add_column(
            "Percentage", style="yellow", justify="right", width=12
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
                title=f"All Forks ({len(sorted_forks)} displayed, sorted by commits status, forks, stars, activity){title_suffix}"
            )
            fork_table.add_column("URL", style="cyan", min_width=35)
            fork_table.add_column("Stars", style="yellow", justify="right", width=8)
            fork_table.add_column("Forks", style="green", justify="right", width=8)
            fork_table.add_column("Commits", style="magenta", justify="right", width=12)
            fork_table.add_column("Last Push", style="blue", width=12)

            # Conditionally add Recent Commits column
            if show_commits > 0:
                # Calculate dynamic width based on content
                commits_width = max(
                    20, min(50, show_commits * 15)
                )  # 15 chars per commit, min 20, max 50
                fork_table.add_column(
                    "Recent Commits", style="dim", width=commits_width
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

                # Format commits ahead status for detailed display
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

            # Show additional insights
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

    def _sort_forks_enhanced(self, collected_forks: list) -> list:
        """Sort forks with enhanced multi-level sorting logic.

        Implements commits-first sorting with multi-level criteria:
        1. Commits status (has commits first)
        2. Forks count (descending)
        3. Stars count (descending)
        4. Last push date (descending - most recent first)

        Args:
            collected_forks: List of CollectedForkData objects

        Returns:
            Sorted list of forks with enhanced sorting criteria
        """

        def sort_key(fork_data):
            """Multi-level sort key for enhanced fork sorting."""
            metrics = fork_data.metrics

            # 1. Commits status - has commits first (True sorts before False)
            has_commits = metrics.commits_ahead_status == "Has commits"

            # 2. Forks count (descending)
            forks_count = metrics.forks_count

            # 3. Stars count (descending)
            stars_count = metrics.stargazers_count

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
                not has_commits,  # False (has commits) sorts before True (no commits)
                -forks_count,  # Negative for descending order
                -stars_count,  # Negative for descending order
                push_timestamp,  # Already negative for descending order
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
            filter_table = Table()
            filter_table.add_column("Filter", style="cyan")
            filter_table.add_column("Status", style="green")
            filter_table.add_column("Excluded Count", style="red", justify="right")

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
        insights_table = Table()
        insights_table.add_column("Category", style="cyan", width=25)
        insights_table.add_column("Count", style="green", justify="right", width=8)
        insights_table.add_column("Description", style="white")

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

        # Show language distribution
        languages = {}
        for fork_data in qualification_result.collected_forks:
            lang = fork_data.metrics.language or "Unknown"
            languages[lang] = languages.get(lang, 0) + 1

        if languages:
            self.console.print("\n[bold blue]Language Distribution:[/bold blue]")
            lang_table = Table()
            lang_table.add_column("Language", style="cyan")
            lang_table.add_column("Fork Count", style="green", justify="right")
            lang_table.add_column("Percentage", style="yellow", justify="right")

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

            # Create qualification result
            qualification_result = data_engine.create_qualification_result(
                repository_owner=owner,
                repository_name=repo_name,
                collected_forks=filtered_forks,
                processing_time_seconds=0.0,
                api_calls_made=len(forks_list_data),
                api_calls_saved=0,
            )

            # Display comprehensive fork data
            await self._display_fork_data_table(
                qualification_result,
                sort_by,
                show_all,
                exclude_archived,
                exclude_disabled,
                show_commits,
                force_all_commits,
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

            # Fetch exact commit counts with progress indicator for remaining forks
            api_calls_made = 0
            detailed_forks = list(forks_to_skip)  # Start with skipped forks

            if forks_needing_api:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=self.console,
                ) as progress:
                    task = progress.add_task(
                        "Fetching exact commit counts...", total=len(forks_needing_api)
                    )

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

            # Display detailed fork data table
            await self._display_detailed_fork_table(
                detailed_forks,
                owner,
                repo_name,
                api_calls_made,
                skipped_count,
                show_commits,
                force_all_commits,
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
        fork_table = Table(
            title=f"Detailed Forks ({len(sorted_forks)} active forks with exact commit counts){title_suffix}"
        )
        fork_table.add_column("URL", style="cyan", min_width=35)
        fork_table.add_column("Stars", style="yellow", justify="right", width=8)
        fork_table.add_column("Forks", style="green", justify="right", width=8)
        fork_table.add_column(
            "Commits Ahead", style="magenta", justify="right", width=15
        )
        fork_table.add_column("Last Push", style="blue", width=12)

        # Conditionally add Recent Commits column
        if show_commits > 0:
            # Calculate dynamic width based on content
            commits_width = max(
                20, min(50, show_commits * 15)
            )  # 15 chars per commit, min 20, max 50
            fork_table.add_column("Recent Commits", style="dim", width=commits_width)

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

            # Format commits ahead
            if isinstance(fork_data.exact_commits_ahead, int):
                if fork_data.exact_commits_ahead == 0:
                    commits_display = "[dim]0 commits[/dim]"
                else:
                    commits_display = (
                        f"[green]{fork_data.exact_commits_ahead} commits[/green]"
                    )
            else:
                commits_display = "[yellow]Unknown[/yellow]"

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
        table = Table(title=f"Promising Forks ({len(promising_forks)} found)")
        table.add_column("#", style="dim", width=4)
        table.add_column("Fork Name", style="cyan", min_width=25)
        table.add_column("Owner", style="blue", min_width=15)
        table.add_column("Stars", style="yellow", justify="right", width=8)
        table.add_column("Commits", style="green", justify="right", width=12)
        table.add_column("Activity Score", style="magenta", justify="right", width=13)
        table.add_column("Last Activity", style="white", width=15)
        table.add_column("Language", style="white", width=12)

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

            table.add_row(
                str(i),
                fork.name,
                fork.owner,
                f"⭐{fork.stars}",
                f"+{fork_data['commits_ahead']}",
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
    ) -> dict[str, str]:
        """Fetch commits ahead for multiple forks concurrently with progress tracking and optimization.

        Args:
            forks_data: List of fork data objects
            show_commits: Number of commits ahead to fetch for each fork
            base_owner: Base repository owner
            base_repo: Base repository name
            force_all_commits: If True, bypass optimization and fetch commits for all forks

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
                    formatted_commits = self.format_recent_commits(commits_ahead)
                    return fork_key, formatted_commits
                except Exception as e:
                    logger.debug(f"Failed to fetch commits ahead for {fork_key}: {e}")
                    return fork_key, "[dim]No commits available[/dim]"

        # Show progress indicator for commit fetching
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
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
            return self.format_recent_commits(commits_ahead)
        except Exception as e:
            logger.debug(
                f"Failed to fetch commits ahead for {fork_owner}/{fork_repo}: {e}"
            )
            return "[dim]No commits available[/dim]"

    def format_recent_commits(self, commits: list) -> str:
        """Format recent commits for display in table.

        Args:
            commits: List of RecentCommit objects

        Returns:
            Formatted string with each commit on a separate line
        """
        if not commits:
            return "[dim]No commits[/dim]"

        # Format: YYYY-MM-DD hash commit message for each commit
        formatted_commits = []
        for commit in commits:
            if commit.date:
                date_str = commit.date.strftime("%Y-%m-%d")
                formatted_commits.append(
                    f"{date_str} {commit.short_sha} {commit.message}"
                )
            else:
                # Fallback to old format if date is not available
                formatted_commits.append(f"{commit.short_sha}: {commit.message}")

        # Join with newlines for multi-line display in table cell
        return "\n".join(formatted_commits)

    def _display_forks_preview_table(self, fork_items: list[dict[str, Any]]) -> None:
        """Display forks preview in a lightweight table format.

        Args:
            fork_items: List of fork preview item dictionaries
        """
        if not fork_items:
            self.console.print("[yellow]No forks found.[/yellow]")
            return

        table = Table(title=f"Forks Preview ({len(fork_items)} forks found)")
        table.add_column("#", style="dim", width=4)
        table.add_column("Fork Name", style="cyan", min_width=25)
        table.add_column("Owner", style="blue", min_width=15)
        table.add_column("Stars", style="yellow", justify="right", width=8)
        table.add_column("Last Push", style="magenta", width=15)
        table.add_column("Commits", style="green", width=13)

        for i, fork_item in enumerate(fork_items, 1):
            # Format last push date
            last_push = self._format_datetime(fork_item["last_push_date"])

            # Style commits ahead status with colors
            commits_ahead = fork_item["commits_ahead"]
            commits_ahead_styled = self._style_commits_ahead_status(commits_ahead)

            table.add_row(
                str(i),
                fork_item["name"],
                fork_item["owner"],
                f"⭐{fork_item['stars']}",
                last_push,
                commits_ahead_styled,
            )

        self.console.print(table)
