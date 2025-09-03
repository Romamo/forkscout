"""Interactive Analyzer service for focused fork/branch analysis."""

import logging
import sys
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from forklift.github.client import GitHubClient
from forklift.models.filters import BranchInfo, ForkDetails, ForkDetailsFilter
from forklift.models.github import Commit

logger = logging.getLogger(__name__)


class InteractiveAnalyzer:
    """Service for focused fork and branch analysis."""

    def __init__(self, github_client: GitHubClient, console: Console | None = None):
        """Initialize the interactive analyzer.
        
        Args:
            github_client: GitHub API client for fetching data
            console: Rich console for output (optional, creates new if None)
        """
        self.github_client = github_client
        self.console = console or Console(file=sys.stdout, width=999999, soft_wrap=False)

    async def analyze_specific_fork(
        self,
        fork_url: str,
        branch: str | None = None,
        filters: ForkDetailsFilter | None = None
    ) -> dict[str, Any]:
        """Analyze a specific fork and optionally a specific branch.
        
        Args:
            fork_url: Fork repository URL in format owner/repo or full GitHub URL
            branch: Specific branch to analyze (optional)
            filters: Filter criteria for analysis (optional)
            
        Returns:
            Dictionary containing fork analysis results
            
        Raises:
            ValueError: If fork URL format is invalid
            GitHubAPIError: If fork cannot be fetched
        """
        owner, repo_name = self._parse_repository_url(fork_url)
        filters = filters or ForkDetailsFilter()

        logger.info(f"Analyzing fork {owner}/{repo_name}" + (f" branch {branch}" if branch else ""))

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Fetching fork details...", total=None)

                # Get fork repository
                fork_repo = await self.github_client.get_repository(owner, repo_name)

                progress.update(task, description="Fetching branch information...")

                # Get branch information if requested
                branches = []
                if filters.include_branches:
                    branches = await self._get_branch_info(
                        owner, repo_name, fork_repo.default_branch, filters.max_branches
                    )

                progress.update(task, description="Fetching contributor information...")

                # Get contributors if requested
                contributors = []
                contributor_count = 0
                if filters.include_contributors:
                    contributors, contributor_count = await self._get_contributors(
                        owner, repo_name, filters.max_contributors
                    )

                progress.update(task, description="Fetching additional metadata...")

                # Get additional metadata
                languages = await self.github_client.get_repository_languages(owner, repo_name)
                topics = await self.github_client.get_repository_topics(owner, repo_name)

                # Calculate total commits
                total_commits = sum(branch.commit_count for branch in branches)

                progress.update(task, description="Analysis complete!")

            # Create fork details
            fork_details = ForkDetails(
                fork=fork_repo,
                branches=branches,
                total_commits=total_commits,
                contributors=contributors,
                contributor_count=contributor_count,
                languages=languages,
                topics=topics
            )

            # Display the analysis results
            self._display_fork_analysis(fork_details, branch)

            # If specific branch requested, analyze it
            branch_analysis = None
            if branch:
                branch_analysis = await self._analyze_specific_branch(
                    owner, repo_name, branch, filters
                )

            return {
                "fork_details": fork_details,
                "branch_analysis": branch_analysis,
                "analysis_date": datetime.utcnow()
            }

        except Exception as e:
            logger.error(f"Failed to analyze fork {owner}/{repo_name}: {e}")
            self.console.print(f"[red]Error: Failed to analyze fork: {e}[/red]")
            raise

    async def show_fork_details(
        self,
        fork_url: str,
        filters: ForkDetailsFilter | None = None
    ) -> ForkDetails:
        """Show detailed information about a fork including branches and statistics.
        
        Args:
            fork_url: Fork repository URL in format owner/repo or full GitHub URL
            filters: Filter criteria for details display (optional)
            
        Returns:
            ForkDetails object with comprehensive fork information
            
        Raises:
            ValueError: If fork URL format is invalid
            GitHubAPIError: If fork cannot be fetched
        """
        owner, repo_name = self._parse_repository_url(fork_url)
        filters = filters or ForkDetailsFilter()

        logger.info(f"Fetching detailed information for fork {owner}/{repo_name}")

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Loading fork details...", total=None)

                # Get fork repository
                fork_repo = await self.github_client.get_repository(owner, repo_name)

                progress.update(task, description="Analyzing branches...")

                # Get branch information
                branches = []
                if filters.include_branches:
                    branches = await self._get_branch_info(
                        owner, repo_name, fork_repo.default_branch, filters.max_branches
                    )

                progress.update(task, description="Gathering contributor data...")

                # Get contributors
                contributors = []
                contributor_count = 0
                if filters.include_contributors:
                    contributors, contributor_count = await self._get_contributors(
                        owner, repo_name, filters.max_contributors
                    )

                progress.update(task, description="Fetching metadata...")

                # Get additional metadata
                languages = await self.github_client.get_repository_languages(owner, repo_name)
                topics = await self.github_client.get_repository_topics(owner, repo_name)

                # Calculate statistics
                total_commits = sum(branch.commit_count for branch in branches)

                progress.update(task, description="Complete!")

            # Create fork details
            fork_details = ForkDetails(
                fork=fork_repo,
                branches=branches,
                total_commits=total_commits,
                contributors=contributors,
                contributor_count=contributor_count,
                languages=languages,
                topics=topics
            )

            # Display the details
            self._display_fork_details_table(fork_details)

            return fork_details

        except Exception as e:
            logger.error(f"Failed to fetch fork details for {owner}/{repo_name}: {e}")
            self.console.print(f"[red]Error: Failed to fetch fork details: {e}[/red]")
            raise

    async def _get_branch_info(
        self,
        owner: str,
        repo_name: str,
        default_branch: str,
        max_branches: int
    ) -> list[BranchInfo]:
        """Get information about repository branches.
        
        Args:
            owner: Repository owner
            repo_name: Repository name
            default_branch: Default branch name
            max_branches: Maximum number of branches to fetch
            
        Returns:
            List of BranchInfo objects
        """
        try:
            # Get all branches
            branches_data = await self.github_client.get_repository_branches(
                owner, repo_name, max_count=max_branches
            )

            branch_info = []
            for branch_data in branches_data:
                branch_name = branch_data["name"]

                # Get commit count for branch (approximate)
                try:
                    commits = await self.github_client.get_branch_commits(
                        owner, repo_name, branch_name, max_count=100
                    )
                    commit_count = len(commits)
                    last_commit_date = None

                    if commits:
                        # Parse the last commit date
                        last_commit = commits[0]
                        if "commit" in last_commit and "committer" in last_commit["commit"]:
                            date_str = last_commit["commit"]["committer"]["date"]
                            last_commit_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

                except Exception as e:
                    logger.warning(f"Failed to get commits for branch {branch_name}: {e}")
                    commit_count = 0
                    last_commit_date = None

                # Calculate commits ahead of main (simplified)
                commits_ahead_of_main = 0
                if branch_name != default_branch:
                    try:
                        comparison = await self.github_client.get_branch_comparison(
                            owner, repo_name, default_branch, branch_name
                        )
                        commits_ahead_of_main = comparison.get("ahead_by", 0)
                    except Exception as e:
                        logger.warning(f"Failed to compare branch {branch_name} with {default_branch}: {e}")

                branch_info.append(BranchInfo(
                    name=branch_name,
                    commit_count=commit_count,
                    last_commit_date=last_commit_date,
                    commits_ahead_of_main=commits_ahead_of_main,
                    is_default=(branch_name == default_branch),
                    is_protected=branch_data.get("protected", False)
                ))

            # Sort branches by activity and importance
            branch_info.sort(key=lambda b: (
                b.is_default,  # Default branch first
                b.commits_ahead_of_main,  # Then by commits ahead
                b.commit_count,  # Then by total commits
                b.last_commit_date or datetime.min  # Then by recency
            ), reverse=True)

            return branch_info

        except Exception as e:
            logger.error(f"Failed to get branch information: {e}")
            return []

    async def _get_contributors(
        self,
        owner: str,
        repo_name: str,
        max_contributors: int
    ) -> tuple[list[str], int]:
        """Get repository contributors.
        
        Args:
            owner: Repository owner
            repo_name: Repository name
            max_contributors: Maximum number of contributors to return
            
        Returns:
            Tuple of (contributor_usernames, total_contributor_count)
        """
        try:
            contributors_data = await self.github_client.get_repository_contributors(
                owner, repo_name, max_count=max_contributors
            )

            contributor_usernames = [
                contrib["login"] for contrib in contributors_data[:max_contributors]
            ]

            # Get total count (GitHub API provides this in headers, but we'll use length as approximation)
            total_count = len(contributors_data)

            return contributor_usernames, total_count

        except Exception as e:
            logger.warning(f"Failed to get contributors: {e}")
            return [], 0

    async def _analyze_specific_branch(
        self,
        owner: str,
        repo_name: str,
        branch: str,
        filters: ForkDetailsFilter
    ) -> dict[str, Any]:
        """Analyze a specific branch in detail.
        
        Args:
            owner: Repository owner
            repo_name: Repository name
            branch: Branch name to analyze
            filters: Analysis filters
            
        Returns:
            Dictionary containing branch analysis results
        """
        try:
            # Get recent commits for the branch
            commits_data = await self.github_client.get_branch_commits(
                owner, repo_name, branch, max_count=20
            )

            # Convert to Commit objects
            commits = []
            for commit_data in commits_data:
                try:
                    commit = Commit.from_github_api(commit_data)
                    commits.append(commit)
                except Exception as e:
                    logger.warning(f"Failed to parse commit {commit_data.get('sha', 'unknown')}: {e}")

            # Analyze commit patterns
            commit_types = {}
            total_changes = 0
            authors = set()

            for commit in commits:
                commit_type = commit.get_commit_type()
                commit_types[commit_type] = commit_types.get(commit_type, 0) + 1
                total_changes += commit.total_changes
                authors.add(commit.author.login)

            # Display branch analysis
            self._display_branch_analysis(branch, commits, commit_types, total_changes, authors)

            return {
                "branch": branch,
                "commits": commits,
                "commit_types": commit_types,
                "total_changes": total_changes,
                "unique_authors": list(authors),
                "analysis_date": datetime.utcnow()
            }

        except Exception as e:
            logger.error(f"Failed to analyze branch {branch}: {e}")
            self.console.print(f"[red]Error: Failed to analyze branch {branch}: {e}[/red]")
            return {}

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

    def _display_fork_analysis(self, fork_details: ForkDetails, analyzed_branch: str | None) -> None:
        """Display comprehensive fork analysis results.
        
        Args:
            fork_details: Fork details object
            analyzed_branch: Name of specifically analyzed branch (if any)
        """
        fork = fork_details.fork

        # Main fork information panel
        info_text = f"""
[bold cyan]Repository:[/bold cyan] {fork.full_name}
[bold cyan]Owner:[/bold cyan] {fork.owner}
[bold cyan]Description:[/bold cyan] {fork.description or 'No description'}
[bold cyan]Language:[/bold cyan] {fork.language or 'Not specified'}
[bold cyan]Stars:[/bold cyan] ⭐ {fork.stars:,}
[bold cyan]Forks:[/bold cyan] 🍴 {fork.forks_count:,}
[bold cyan]Total Commits:[/bold cyan] {fork_details.total_commits:,}
[bold cyan]Contributors:[/bold cyan] 👥 {fork_details.contributor_count:,}
        """.strip()

        panel = Panel(
            info_text,
            title=f"Fork Analysis: {fork.name}",
            border_style="blue"
        )
        self.console.print(panel)

        # Display branches table
        if fork_details.branches:
            self._display_branches_table(fork_details.branches, analyzed_branch)

        # Display contributors if available
        if fork_details.contributors:
            self._display_contributors_panel(fork_details.contributors, fork_details.contributor_count)

        # Display languages if available
        if fork_details.languages:
            self._display_languages_panel(fork_details.languages)

    def _display_fork_details_table(self, fork_details: ForkDetails) -> None:
        """Display fork details in a comprehensive table format.
        
        Args:
            fork_details: Fork details object
        """
        fork = fork_details.fork

        # Create main details table
        table = Table(title=f"Fork Details: {fork.full_name}", expand=False)
        table.add_column("Property", style="cyan", width=20, no_wrap=True)
        table.add_column("Value", style="green", no_wrap=True, overflow="fold")

        table.add_row("Full Name", fork.full_name)
        table.add_row("Owner", fork.owner)
        table.add_row("Description", fork.description or "No description")
        table.add_row("Primary Language", fork.language or "Not specified")
        table.add_row("Stars", f"⭐ {fork.stars:,}")
        table.add_row("Forks", f"{fork.forks_count:,}")
        table.add_row("Watchers", f"{fork.watchers_count:,}")
        table.add_row("Open Issues", f"{fork.open_issues_count:,}")
        table.add_row("Size", f"{fork.size:,} KB")
        table.add_row("Default Branch", fork.default_branch)
        table.add_row("Total Branches", str(len(fork_details.branches)))
        table.add_row("Total Commits", f"{fork_details.total_commits:,}")
        table.add_row("Contributors", f"👥 {fork_details.contributor_count:,}")
        table.add_row("Created", self._format_datetime(fork.created_at))
        table.add_row("Last Updated", self._format_datetime(fork.updated_at))
        table.add_row("Last Push", self._format_datetime(fork.pushed_at))
        table.add_row("Is Fork", "Yes" if fork.is_fork else "Original")
        table.add_row("Is Private", "Yes" if fork.is_private else "Public")
        table.add_row("Is Archived", "Yes" if fork.is_archived else "Active")

        self.console.print(table)

        # Display additional information panels
        if fork_details.branches:
            self._display_branches_table(fork_details.branches)

        if fork_details.contributors:
            self._display_contributors_panel(fork_details.contributors, fork_details.contributor_count)

        if fork_details.languages:
            self._display_languages_panel(fork_details.languages)

        if fork_details.topics:
            self._display_topics_panel(fork_details.topics)

    def _display_branches_table(self, branches: list[BranchInfo], highlighted_branch: str | None = None) -> None:
        """Display branches information in a table.
        
        Args:
            branches: List of branch information
            highlighted_branch: Branch name to highlight (if any)
        """
        if not branches:
            return

        table = Table(title=f"Branches ({len(branches)} total)", expand=False)
        table.add_column("Branch Name", style="cyan", min_width=15, no_wrap=True, overflow="fold")
        table.add_column("Commits", style="yellow", justify="right", width=8, no_wrap=True)
        table.add_column("Ahead of Main", style="green", justify="right", width=12, no_wrap=True)
        table.add_column("Last Activity", style="magenta", width=15, no_wrap=True)
        table.add_column("Status", style="white", width=10, no_wrap=True)

        for branch in branches:
            # Highlight the analyzed branch
            branch_name = branch.name
            if highlighted_branch and branch.name == highlighted_branch:
                branch_name = f"[bold yellow]{branch.name}[/bold yellow] ⭐"
            elif branch.is_default:
                branch_name = f"[bold]{branch.name}[/bold] (default)"

            # Format status
            status_parts = []
            if branch.is_default:
                status_parts.append("[blue]Default[/blue]")
            if branch.is_protected:
                status_parts.append("[red]Protected[/red]")
            if not status_parts:
                status_parts.append("[dim]Regular[/dim]")

            status = " ".join(status_parts)

            table.add_row(
                branch_name,
                str(branch.commit_count),
                str(branch.commits_ahead_of_main) if branch.commits_ahead_of_main > 0 else "-",
                self._format_datetime(branch.last_commit_date),
                status
            )

        self.console.print(table)

    def _display_contributors_panel(self, contributors: list[str], total_count: int) -> None:
        """Display contributors information in a panel.
        
        Args:
            contributors: List of contributor usernames
            total_count: Total number of contributors
        """
        if not contributors:
            return

        contributors_text = " • ".join(contributors[:10])  # Show first 10
        if total_count > len(contributors):
            contributors_text += f" • +{total_count - len(contributors)} more"

        panel = Panel(
            contributors_text,
            title=f"Contributors ({total_count} total)",
            border_style="green"
        )
        self.console.print(panel)

    def _display_languages_panel(self, languages: dict[str, int]) -> None:
        """Display programming languages panel.
        
        Args:
            languages: Dictionary of language names to byte counts
        """
        if not languages:
            return

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

    def _display_branch_analysis(
        self,
        branch_name: str,
        commits: list[Commit],
        commit_types: dict[str, int],
        total_changes: int,
        authors: set
    ) -> None:
        """Display detailed branch analysis.
        
        Args:
            branch_name: Name of the analyzed branch
            commits: List of commits in the branch
            commit_types: Dictionary of commit types and their counts
            total_changes: Total lines changed
            authors: Set of unique authors
        """
        # Branch summary panel
        summary_text = f"""
[bold cyan]Branch:[/bold cyan] {branch_name}
[bold cyan]Recent Commits:[/bold cyan] {len(commits)}
[bold cyan]Total Changes:[/bold cyan] {total_changes:,} lines
[bold cyan]Unique Authors:[/bold cyan] {len(authors)}
        """.strip()

        panel = Panel(
            summary_text,
            title=f"Branch Analysis: {branch_name}",
            border_style="yellow"
        )
        self.console.print(panel)

        # Commit types breakdown
        if commit_types:
            types_text = " • ".join([f"{type_name}: {count}" for type_name, count in commit_types.items()])
            types_panel = Panel(
                types_text,
                title="Commit Types",
                border_style="green"
            )
            self.console.print(types_panel)

        # Recent commits table
        if commits:
            self._display_recent_commits_table(commits[:10])  # Show last 10 commits

    def _display_recent_commits_table(self, commits: list[Commit]) -> None:
        """Display recent commits in a table.
        
        Args:
            commits: List of recent commits
        """
        table = Table(title=f"Recent Commits ({len(commits)} shown)", expand=False)
        table.add_column("SHA", style="dim", width=8, no_wrap=True)
        table.add_column("Message", style="white", min_width=30, no_wrap=True, overflow="fold")
        table.add_column("Author", style="cyan", width=15, no_wrap=True)
        table.add_column("Date", style="magenta", width=12, no_wrap=True)
        table.add_column("Changes", style="yellow", justify="right", width=8, no_wrap=True)

        for commit in commits:
            # Truncate long commit messages
            message = commit.message.split("\n")[0]  # First line only
            if len(message) > 50:
                message = message[:47] + "..."

            table.add_row(
                commit.sha[:7],
                message,
                commit.author.login,
                self._format_datetime(commit.date),
                f"+{commit.additions}/-{commit.deletions}"
            )

        self.console.print(table)

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
