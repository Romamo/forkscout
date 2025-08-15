"""Repository Display Service for incremental repository exploration."""

import logging
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from forklift.github.client import GitHubClient
from forklift.models.analysis import ForkPreviewItem, ForksPreview
from forklift.models.filters import PromisingForksFilter
from forklift.models.github import Repository

logger = logging.getLogger(__name__)


class RepositoryDisplayService:
    """Service for displaying repository information in a structured format."""

    def __init__(self, github_client: GitHubClient, console: Console | None = None):
        """Initialize the repository display service.

        Args:
            github_client: GitHub API client for fetching data
            console: Rich console for output (optional, creates new if None)
        """
        self.github_client = github_client
        self.console = console or Console()

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
                self.console.print("[yellow]No forks found for this repository.[/yellow]")
                preview_data = ForksPreview(
                    total_forks=0,
                    forks=[]
                )
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
                    commits_ahead=commits_ahead
                )
                fork_items.append(fork_item)

            # Sort by stars and last push date
            fork_items.sort(
                key=lambda x: (x.stars, x.last_push_date or datetime.min),
                reverse=True
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
                    "commits_ahead": item.commits_ahead
                }
                for item in fork_items
            ]

            # Display the lightweight forks table
            self._display_forks_preview_table(fork_items_dict)

            # Create ForksPreview object
            preview_data = ForksPreview(
                total_forks=len(forks),
                forks=fork_items
            )

            return preview_data.dict()

        except Exception as e:
            logger.error(f"Failed to fetch forks preview: {e}")
            self.console.print(f"[red]Error: Failed to fetch forks preview: {e}[/red]")
            raise

    async def show_repository_details(self, repo_url: str) -> dict[str, Any]:
        """Display detailed repository information.

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
            repository = await self.github_client.get_repository(owner, repo_name)

            # Get additional information
            languages = await self.github_client.get_repository_languages(owner, repo_name)
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
                "updated": self._format_datetime(repository.updated_at)
            }

            # Display the information
            self._display_repository_table(repo_details)

            return repo_details

        except Exception as e:
            logger.error(f"Failed to fetch repository details: {e}")
            self.console.print(f"[red]Error: Failed to fetch repository details: {e}[/red]")
            raise

    async def show_forks_summary(self, repo_url: str, max_forks: int | None = None) -> dict[str, Any]:
        """Display a summary table of repository forks.

        Args:
            repo_url: Repository URL in format owner/repo or full GitHub URL
            max_forks: Maximum number of forks to display (None for all)

        Returns:
            Dictionary containing forks summary data

        Raises:
            ValueError: If repository URL format is invalid
            GitHubAPIError: If forks cannot be fetched
        """
        owner, repo_name = self._parse_repository_url(repo_url)

        logger.info(f"Fetching forks for {owner}/{repo_name}")

        try:
            # Get all forks
            forks = await self.github_client.get_all_repository_forks(
                owner, repo_name, max_forks=max_forks
            )

            if not forks:
                self.console.print("[yellow]No forks found for this repository.[/yellow]")
                return {
                    "total_forks": 0,
                    "displayed_forks": 0,
                    "forks": []
                }

            # Enhance fork data with activity metrics
            enhanced_forks = []
            for fork in forks:
                try:
                    # Get commits ahead/behind information
                    comparison = await self.github_client.get_commits_ahead_behind(
                        fork.owner, fork.name, owner, repo_name
                    )

                    fork_data = {
                        "fork": fork,
                        "commits_ahead": comparison.get("ahead_by", 0),
                        "commits_behind": comparison.get("behind_by", 0),
                        "activity_status": self._calculate_activity_status(fork),
                        "last_activity": self._format_datetime(fork.pushed_at)
                    }
                    enhanced_forks.append(fork_data)

                except Exception as e:
                    logger.warning(f"Failed to get comparison data for fork {fork.full_name}: {e}")
                    # Add fork with default values
                    fork_data = {
                        "fork": fork,
                        "commits_ahead": 0,
                        "commits_behind": 0,
                        "activity_status": "unknown",
                        "last_activity": self._format_datetime(fork.pushed_at)
                    }
                    enhanced_forks.append(fork_data)

            # Sort forks by activity and stars
            enhanced_forks.sort(
                key=lambda x: (
                    x["commits_ahead"],
                    x["fork"].stars,
                    x["fork"].pushed_at or datetime.min
                ),
                reverse=True
            )

            # Display the forks table
            self._display_forks_table(enhanced_forks, max_display=50)

            summary = {
                "total_forks": len(forks),
                "displayed_forks": min(len(enhanced_forks), 50),
                "forks": enhanced_forks
            }

            return summary

        except Exception as e:
            logger.error(f"Failed to fetch forks: {e}")
            self.console.print(f"[red]Error: Failed to fetch forks: {e}[/red]")
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
            r"^([^/]+)/([^/]+)$"  # Simple owner/repo format
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

        days_since_activity = (datetime.utcnow() - fork.pushed_at.replace(tzinfo=None)).days

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
        table.add_row("Stars", f"⭐ {repository.stars:,}")
        table.add_row("Forks", f"🍴 {repository.forks_count:,}")
        table.add_row("Watchers", f"👀 {repository.watchers_count:,}")
        table.add_row("Open Issues", f"🐛 {repository.open_issues_count:,}")
        table.add_row("Size", f"📦 {repository.size:,} KB")
        table.add_row("License", repo_details["license"])
        table.add_row("Default Branch", repository.default_branch)
        table.add_row("Created", repo_details["created"])
        table.add_row("Last Updated", repo_details["updated"])
        table.add_row("Last Activity", repo_details["last_activity"])
        table.add_row("Private", "🔒 Yes" if repository.is_private else "🌍 Public")
        table.add_row("Fork", "🍴 Yes" if repository.is_fork else "📦 Original")
        table.add_row("Archived", "📦 Yes" if repository.is_archived else "✅ Active")

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
        for lang, bytes_count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
            percentage = (bytes_count / total_bytes) * 100
            language_info.append(f"{lang}: {percentage:.1f}%")

        languages_text = " • ".join(language_info[:5])  # Show top 5 languages
        if len(languages) > 5:
            languages_text += f" • +{len(languages) - 5} more"

        panel = Panel(
            languages_text,
            title="Programming Languages",
            border_style="blue"
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

        panel = Panel(
            topics_text,
            title="Topics",
            border_style="green"
        )
        self.console.print(panel)

    def _display_forks_table(self, enhanced_forks: list[dict[str, Any]], max_display: int = 50) -> None:
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
        table.add_column("Commits Ahead", style="green", justify="right", width=12)
        table.add_column("Commits Behind", style="red", justify="right", width=13)
        table.add_column("Last Activity", style="magenta", width=15)
        table.add_column("Status", style="white", width=10)
        table.add_column("Language", style="white", width=12)

        display_count = min(len(enhanced_forks), max_display)

        for i, fork_data in enumerate(enhanced_forks[:display_count], 1):
            fork = fork_data["fork"]

            # Style status with colors
            status = fork_data["activity_status"]
            status_styled = self._style_activity_status(status)

            # Format commits ahead/behind
            commits_ahead = fork_data["commits_ahead"]
            commits_behind = fork_data["commits_behind"]

            ahead_text = f"+{commits_ahead}" if commits_ahead > 0 else "0"
            behind_text = f"-{commits_behind}" if commits_behind > 0 else "0"

            table.add_row(
                str(i),
                fork.name,
                fork.owner,
                f"⭐{fork.stars}",
                ahead_text,
                behind_text,
                fork_data["last_activity"],
                status_styled,
                fork.language or "N/A"
            )

        self.console.print(table)

        if len(enhanced_forks) > max_display:
            self.console.print(f"[dim]... and {len(enhanced_forks) - max_display} more forks[/dim]")

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
            "unknown": "[dim]Unknown[/dim]"
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
            "No commits": "[red]No commits[/red]"
        }

        return status_colors.get(status, status)

    def _style_commits_ahead_status(self, status: str) -> str:
        """Apply color styling to commits ahead status.

        Args:
            status: Commits ahead status string

        Returns:
            Styled status string
        """
        status_colors = {
            "None": "[red]None[/red]",
            "Unknown": "[green]Unknown[/green]"
        }

        return status_colors.get(status, status)

    async def show_promising_forks(
        self,
        repo_url: str,
        filters: PromisingForksFilter | None = None,
        max_forks: int | None = None
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
            # Get all forks first
            forks_summary = await self.show_forks_summary(repo_url, max_forks)
            all_forks = forks_summary["forks"]

            if not all_forks:
                self.console.print("[yellow]No forks found to analyze.[/yellow]")
                return {
                    "total_forks": 0,
                    "promising_forks": 0,
                    "forks": []
                }

            # Filter for promising forks
            promising_forks = [
                fork_data for fork_data in all_forks
                if filters.matches_fork(fork_data)
            ]

            if not promising_forks:
                self.console.print("[yellow]No promising forks found matching the criteria.[/yellow]")
                self._display_filter_criteria(filters)
                return {
                    "total_forks": len(all_forks),
                    "promising_forks": 0,
                    "forks": []
                }

            # Sort promising forks by relevance score
            promising_forks.sort(
                key=lambda x: (
                    x["commits_ahead"],
                    x["fork"].stars,
                    filters._calculate_activity_score(
                        x["activity_status"],
                        x["fork"].pushed_at
                    )
                ),
                reverse=True
            )

            # Display results
            self._display_promising_forks_table(promising_forks, filters)

            return {
                "total_forks": len(all_forks),
                "promising_forks": len(promising_forks),
                "forks": promising_forks,
                "filter_criteria": filters
            }

        except Exception as e:
            logger.error(f"Failed to find promising forks: {e}")
            self.console.print(f"[red]Error: Failed to find promising forks: {e}[/red]")
            raise

    def _display_promising_forks_table(
        self,
        promising_forks: list[dict[str, Any]],
        filters: PromisingForksFilter
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
        table.add_column("Commits Ahead", style="green", justify="right", width=12)
        table.add_column("Activity Score", style="magenta", justify="right", width=13)
        table.add_column("Last Activity", style="white", width=15)
        table.add_column("Language", style="white", width=12)

        for i, fork_data in enumerate(promising_forks, 1):
            fork = fork_data["fork"]

            # Calculate activity score
            activity_score = filters._calculate_activity_score(
                fork_data["activity_status"],
                fork.pushed_at
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
                fork.language or "N/A"
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
            criteria_text,
            title="Promising Forks Analysis",
            border_style="blue"
        )
        self.console.print(panel)

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
        table.add_column("Commits Ahead", style="green", width=13)

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
                commits_ahead_styled
            )

        self.console.print(table)
