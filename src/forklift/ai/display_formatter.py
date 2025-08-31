"""AI summary display formatter with Rich formatting and visual separation."""

import logging

from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from forklift.models.ai_summary import AISummary
from forklift.models.github import Commit

logger = logging.getLogger(__name__)


class AISummaryDisplayFormatter:
    """Formatter for AI-powered commit summaries with enhanced visual presentation."""

    def __init__(self, console: Console | None = None):
        """Initialize the AI summary display formatter.

        Args:
            console: Rich console for output (optional, creates new if None)
        """
        self.console = console or Console(file=sys.stdout)

    def format_ai_summaries_detailed(
        self,
        commits: list[Commit],
        summaries: list[AISummary],
        show_metadata: bool = True
    ) -> None:
        """Display AI summaries in detailed format with visual separation.

        Args:
            commits: List of Commit objects
            summaries: List of AISummary objects
            show_metadata: Whether to show processing metadata
        """
        if not commits or not summaries:
            self.console.print("[yellow]No AI summaries to display[/yellow]")
            return

        self.console.print("\n[bold blue]AI-Powered Commit Analysis[/bold blue]")
        self.console.print(Rule(style="blue"))

        # Create a mapping of commit SHA to summary
        summary_map = {summary.commit_sha: summary for summary in summaries}

        for i, commit in enumerate(commits, 1):
            summary = summary_map.get(commit.sha)
            self._display_single_commit_with_ai_summary(
                commit, summary, i, len(commits), show_metadata
            )

    def format_ai_summaries_compact(
        self,
        commits: list[Commit],
        summaries: list[AISummary],
        plain_text: bool = False
    ) -> None:
        """Display AI summaries in compact inline format without structured sections.

        Args:
            commits: List of Commit objects
            summaries: List of AISummary objects
            plain_text: Whether to use plain text formatting (no Rich codes)
        """
        if not commits or not summaries:
            if plain_text:
                print("No AI summaries to display")
            else:
                self.console.print("[yellow]No AI summaries to display[/yellow]")
            return

        if plain_text:
            print("\nAI Commit Summaries")
        else:
            self.console.print("\n[bold blue]AI Commit Summaries[/bold blue]")

        # Create a mapping of commit SHA to summary
        summary_map = {summary.commit_sha: summary for summary in summaries}

        for i, commit in enumerate(commits, 1):
            summary = summary_map.get(commit.sha)
            if plain_text:
                self._display_compact_commit_summary_plain(commit, summary, i, len(commits))
            else:
                self._display_compact_commit_summary(commit, summary, i, len(commits))

    def format_ai_summaries_compact_table(
        self,
        commits: list[Commit],
        summaries: list[AISummary]
    ) -> None:
        """Display AI summaries in compact table format.

        Args:
            commits: List of Commit objects
            summaries: List of AISummary objects
        """
        if not commits or not summaries:
            self.console.print("[yellow]No AI summaries to display[/yellow]")
            return

        self.console.print("\n[bold blue]AI-Powered Commit Summaries[/bold blue]")
        self.console.print(f"[dim]Showing {len(summaries)} AI-generated summaries in compact format[/dim]")

        table = Table(
            title="AI Commit Analysis",
            show_header=True,
            header_style="bold magenta",
            border_style="blue"
        )
        table.add_column("Commit", style="cyan", width=8)
        table.add_column("Author", style="green", width=12)
        table.add_column("Message", style="yellow", width=30)
        table.add_column("AI Summary", style="white", width=60)
        table.add_column("Meta", style="dim", width=8)

        # Create a mapping of commit SHA to summary
        summary_map = {summary.commit_sha: summary for summary in summaries}

        for commit in commits:
            summary = summary_map.get(commit.sha)
            self._add_compact_table_row(table, commit, summary)

        self.console.print(table)

    def format_ai_summaries_structured(
        self,
        commits: list[Commit],
        summaries: list[AISummary],
        show_github_links: bool = True
    ) -> None:
        """Display AI summaries with structured sections and clear visual hierarchy.

        Args:
            commits: List of Commit objects
            summaries: List of AISummary objects
            show_github_links: Whether to show GitHub commit links
        """
        if not commits or not summaries:
            self.console.print("[yellow]No AI summaries to display[/yellow]")
            return

        self.console.print("\n[bold blue]Structured AI Commit Analysis[/bold blue]")
        self.console.print(Rule(style="blue"))

        # Create a mapping of commit SHA to summary
        summary_map = {summary.commit_sha: summary for summary in summaries}

        for i, commit in enumerate(commits, 1):
            summary = summary_map.get(commit.sha)
            self._display_structured_commit_analysis(
                commit, summary, i, len(commits), show_github_links
            )

    def _display_single_commit_with_ai_summary(
        self,
        commit: Commit,
        summary: AISummary | None,
        index: int,
        total: int,
        show_metadata: bool
    ) -> None:
        """Display a single commit with its AI summary in detailed format.

        Args:
            commit: Commit object
            summary: AISummary object (optional)
            index: Current commit index
            total: Total number of commits
            show_metadata: Whether to show processing metadata
        """
        # Create commit header with basic info
        commit_header = self._create_commit_header(commit, index)

        # Commit message and basic stats
        commit_info = self._create_commit_info_section(commit)

        # AI Summary section
        ai_section = self._create_ai_summary_section(summary, show_metadata)

        # Create main panel for this commit
        commit_panel = Panel(
            Group(commit_header, Text(""), commit_info, Text(""), ai_section),
            title=f"[bold]Commit Analysis #{index}/{total}[/bold]",
            border_style="bright_blue",
            padding=(1, 2)
        )

        self.console.print(commit_panel)

        # Add spacing between commits (except for the last one)
        if index < total:
            self.console.print()

    def _display_structured_commit_analysis(
        self,
        commit: Commit,
        summary: AISummary | None,
        index: int,
        total: int,
        show_github_links: bool
    ) -> None:
        """Display commit analysis with structured sections.

        Args:
            commit: Commit object
            summary: AISummary object (optional)
            index: Current commit index
            total: Total number of commits
            show_github_links: Whether to show GitHub commit links
        """
        # Header with commit info
        self.console.print(f"\n[bold cyan]#{index}/{total} Commit {commit.sha[:8]}[/bold cyan]")

        # Basic commit information
        info_table = Table(show_header=False, box=None, padding=(0, 1))
        info_table.add_column("Field", style="dim", width=12)
        info_table.add_column("Value", style="white")

        info_table.add_row("Author:", f"[green]{commit.author.login if commit.author else 'Unknown'}[/green]")
        info_table.add_row("Date:", f"[yellow]{self._format_datetime_simple(commit.date)}[/yellow]")
        info_table.add_row("Changes:", f"[bright_green]+{commit.additions}[/bright_green]/[red]-{commit.deletions}[/red]")

        if show_github_links:
            github_url = f"https://github.com/{commit.repository.owner if hasattr(commit, 'repository') else 'owner'}/{commit.repository.name if hasattr(commit, 'repository') else 'repo'}/commit/{commit.sha}"
            info_table.add_row("GitHub:", f"[link={github_url}]{github_url}[/link]")

        self.console.print(info_table)

        # Commit message
        message = commit.message.strip()
        message_lines = message.split("\n")
        title = message_lines[0]
        body = "\n".join(message_lines[1:]).strip() if len(message_lines) > 1 else ""

        self.console.print(f"\n[bold yellow]Message:[/bold yellow] {title}")
        if body:
            self.console.print(f"[dim]{body}[/dim]")

        # AI Analysis sections with clear separation
        if summary and not summary.error:
            self._display_ai_analysis_sections(summary)
        elif summary and summary.error:
            self.console.print(f"\n[bold red]ERROR - AI Analysis Error:[/bold red] {summary.error}")
        else:
            self.console.print("\n[dim]INFO - No AI analysis available[/dim]")

        # Separator between commits
        if index < total:
            self.console.print(Rule(style="dim"))

    def _display_ai_analysis_sections(self, summary: AISummary) -> None:
        """Display AI analysis as simple summary text.

        Args:
            summary: AISummary object with analysis data
        """
        # Display the summary text
        if summary.summary_text:
            self.console.print("\n[bold blue]AI Summary:[/bold blue]")
            self.console.print(f"[white]{summary.summary_text}[/white]")

        # Processing metadata
        if summary.processing_time_ms and summary.tokens_used:
            metadata = (
                f"[dim]Processing: {summary.processing_time_ms:.0f}ms • "
                f"Tokens: {summary.tokens_used} • "
                f"Model: {summary.model_used or 'gpt-4o-mini'}[/dim]"
            )
            self.console.print(f"\n{metadata}")

    def _create_commit_header(self, commit: Commit, index: int) -> Text:
        """Create formatted commit header.

        Args:
            commit: Commit object
            index: Commit index

        Returns:
            Formatted Text object for commit header
        """
        header = Text()
        header.append(f"#{index} ", style="dim")
        header.append(f"{commit.sha[:8]} ", style="cyan")
        header.append(f"by {commit.author.login if commit.author else 'Unknown'} ", style="green")
        header.append(f"({self._format_datetime_simple(commit.date)})", style="dim")
        return header

    def _create_commit_info_section(self, commit: Commit) -> Group:
        """Create commit information section.

        Args:
            commit: Commit object

        Returns:
            Group containing commit information
        """
        # Commit message
        message = commit.message.split("\n")[0]
        if len(message) > 80:
            message = message[:77] + "..."

        # Changes summary
        changes_text = f"CHANGES: +{commit.additions}/-{commit.deletions} changes"
        if commit.files_changed:
            changes_text += f" in {len(commit.files_changed)} files"

        return Group(
            Text(f"Message: {message}", style="yellow"),
            Text(changes_text, style="dim")
        )

    def _create_ai_summary_section(
        self,
        summary: AISummary | None,
        show_metadata: bool
    ) -> Group:
        """Create AI summary section with visual separation.

        Args:
            summary: AISummary object (optional)
            show_metadata: Whether to show processing metadata

        Returns:
            Group containing AI summary content
        """
        if not summary:
            return Group(Text("INFO - No AI analysis available", style="dim"))

        if summary.error:
            return Group(
                Panel(
                    Text(f"ERROR - {summary.error}", style="red"),
                    title="[bold red]AI Analysis Error[/bold red]",
                    border_style="red",
                    padding=(0, 1)
                )
            )

        ai_content = []

        # AI Summary panel
        if summary.summary_text:
            summary_panel = Panel(
                Text(summary.summary_text, style="white"),
                title="[bold blue]AI Summary[/bold blue]",
                border_style="blue",
                padding=(0, 1)
            )
            ai_content.append(summary_panel)

        # Processing metadata
        if show_metadata and summary.processing_time_ms and summary.tokens_used:
            metadata = Text(
                f"Processing: {summary.processing_time_ms:.0f}ms • Tokens: {summary.tokens_used} • Model: {summary.model_used or 'gpt-4o-mini'}",
                style="dim"
            )
            ai_content.append(metadata)

        return Group(*ai_content) if ai_content else Group(Text("No AI analysis available", style="dim"))

    def _display_compact_commit_summary(
        self,
        commit: Commit,
        summary: AISummary | None,
        index: int,
        total: int
    ) -> None:
        """Display a single commit with compact AI summary inline.

        Args:
            commit: Commit object
            summary: AISummary object (optional)
            index: Current commit index
            total: Total number of commits
        """
        # Basic commit info on one line
        commit_line = (
            f"[cyan]{commit.sha[:8]}[/cyan] "
            f"[green]{commit.author.login if commit.author else 'Unknown'}[/green] "
            f"[dim]({self._format_datetime_simple(commit.date)})[/dim] "
            f"[yellow]{commit.message.split(chr(10))[0][:60]}[/yellow]"
        )

        if len(commit.message.split("\n")[0]) > 60:
            commit_line += "[yellow]...[/yellow]"

        self.console.print(commit_line)

        # AI summary on the next line, indented
        if summary and not summary.error and summary.summary_text:
            # Clean summary text without formatting
            summary_text = summary.summary_text.strip()
            self.console.print(f"  [white]{summary_text}[/white]")
        elif summary and summary.error:
            self.console.print(f"  [red]AI Error: {summary.error}[/red]")
        else:
            self.console.print("  [dim]No AI summary available[/dim]")

        # Add spacing between commits (except for the last one)
        if index < total:
            self.console.print()

    def _display_compact_commit_summary_plain(
        self,
        commit: Commit,
        summary: AISummary | None,
        index: int,
        total: int
    ) -> None:
        """Display a single commit with compact AI summary inline in plain text.

        Args:
            commit: Commit object
            summary: AISummary object (optional)
            index: Current commit index
            total: Total number of commits
        """
        # Basic commit info on one line (plain text)
        commit_line = (
            f"{commit.sha[:8]} "
            f"{commit.author.login if commit.author else 'Unknown'} "
            f"({self._format_datetime_simple(commit.date)}) "
            f"{commit.message.split(chr(10))[0][:60]}"
        )

        if len(commit.message.split("\n")[0]) > 60:
            commit_line += "..."

        print(commit_line)

        # AI summary on the next line, indented (plain text)
        if summary and not summary.error and summary.summary_text:
            # Clean summary text without formatting
            summary_text = summary.summary_text.strip()
            print(f"  {summary_text}")
        elif summary and summary.error:
            print(f"  AI Error: {summary.error}")
        else:
            print("  No AI summary available")

        # Add spacing between commits (except for the last one)
        if index < total:
            print()

    def _add_compact_table_row(
        self,
        table: Table,
        commit: Commit,
        summary: AISummary | None
    ) -> None:
        """Add a row to the compact AI summaries table.

        Args:
            table: Rich Table object
            commit: Commit object
            summary: AISummary object (optional)
        """
        # Format commit info
        commit_short = commit.sha[:7]
        author = (commit.author.login if commit.author else "Unknown")[:12]
        message = commit.message.split("\n")[0]
        if len(message) > 30:
            message = message[:27] + "..."

        # Format AI summary
        if summary and not summary.error:
            ai_summary = self._truncate_text(summary.summary_text, 60)
            meta = f"{summary.tokens_used}t" if summary.tokens_used else "N/A"
        elif summary and summary.error:
            ai_summary = Text(f"Error: {summary.error[:50]}...", style="red")
            meta = "ERR"
        else:
            ai_summary = Text("No summary", style="dim")
            meta = "N/A"

        table.add_row(
            commit_short,
            author,
            message,
            ai_summary,
            meta
        )

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to specified length with ellipsis.

        Args:
            text: Text to truncate
            max_length: Maximum length

        Returns:
            Truncated text string
        """
        if not text:
            return "N/A"
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    def _format_datetime_simple(self, dt) -> str:
        """Format datetime for simple display.

        Args:
            dt: Datetime object

        Returns:
            Formatted datetime string
        """
        if not dt:
            return "Unknown"
        return dt.strftime("%Y-%m-%d %H:%M")

    def display_usage_statistics(
        self,
        usage_stats,
        title: str = "AI Usage Summary"
    ) -> None:
        """Display AI usage statistics with enhanced formatting.

        Args:
            usage_stats: AIUsageStats object
            title: Title for the statistics display
        """
        # Calculate success rate
        success_rate = (
            usage_stats.successful_requests / usage_stats.total_requests * 100
            if usage_stats.total_requests > 0 else 0
        )

        # Format cost with appropriate precision
        cost_str = (
            f"${usage_stats.total_cost_usd:.4f}"
            if usage_stats.total_cost_usd < 0.01
            else f"${usage_stats.total_cost_usd:.2f}"
        )

        self.console.print(f"\n[bold]{title}[/bold]")
        usage_table = Table(show_header=False, box=None, padding=(0, 1))
        usage_table.add_column("Metric", style="cyan")
        usage_table.add_column("Value", style="green")

        usage_table.add_row(
            "SUCCESS - Successful requests:",
            f"{usage_stats.successful_requests}/{usage_stats.total_requests} ({success_rate:.1f}%)"
        )
        usage_table.add_row("Tokens used:", f"{usage_stats.total_tokens_used:,}")
        usage_table.add_row("Estimated cost:", cost_str)
        usage_table.add_row("Avg processing time:", f"{usage_stats.average_processing_time_ms:.0f}ms")

        self.console.print(usage_table)
