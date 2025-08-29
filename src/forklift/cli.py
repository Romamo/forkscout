"""Command-line interface for Forklift."""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

from forklift.ai.display_formatter import AISummaryDisplayFormatter
from forklift.analysis.commit_categorizer import CommitCategorizer
from forklift.analysis.commit_explanation_engine import CommitExplanationEngine
from forklift.analysis.explanation_generator import ExplanationGenerator
from forklift.analysis.fork_discovery import ForkDiscoveryService
from forklift.analysis.impact_assessor import ImpactAssessor
from forklift.analysis.interactive_orchestrator import InteractiveAnalysisOrchestrator
from forklift.analysis.interactive_steps import (
    FeatureRankingStep,
    ForkAnalysisStep,
    ForkDiscoveryStep,
    ForkFilteringStep,
    RepositoryDiscoveryStep,
)
from forklift.analysis.repository_analyzer import RepositoryAnalyzer
from forklift.config.settings import ForkliftConfig, load_config
from forklift.display.detailed_commit_display import (
    DetailedCommitDisplay,
)
from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.github.client import GitHubClient
from forklift.github.exceptions import (
    GitHubEmptyRepositoryError,
    GitHubForkAccessError,
    GitHubPrivateRepositoryError,
    GitHubTimeoutError,
)
from forklift.models.github import Commit
from forklift.ranking.feature_ranking_engine import FeatureRankingEngine
from forklift.storage.analysis_cache import AnalysisCacheManager

console = Console()
logger = logging.getLogger(__name__)


class CLIError(Exception):
    """Base exception for CLI errors."""
    pass


def setup_logging(verbose: bool = False, debug: bool = False, config: ForkliftConfig | None = None) -> None:
    """Setup logging configuration for CLI."""
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING

    # Use config logging settings if available
    if config and config.logging:
        level = getattr(logging, config.logging.level.upper(), level)
        log_format = config.logging.format

        handlers = []

        # Console handler
        if config.logging.console_enabled:
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setFormatter(logging.Formatter(log_format))
            handlers.append(console_handler)

        # File handler
        if config.logging.file_enabled:
            try:
                file_handler = logging.FileHandler(config.logging.file_path)
                file_handler.setFormatter(logging.Formatter(log_format))
                handlers.append(file_handler)
            except Exception as e:
                # Fallback to console only if file logging fails
                console.print(f"[yellow]Warning: Could not setup file logging: {e}[/yellow]")

        logging.basicConfig(
            level=level,
            format=log_format,
            handlers=handlers,
            force=True  # Override any existing configuration
        )
    else:
        # Default logging setup
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(sys.stderr)
            ],
            force=True
        )


def validate_repository_url(url: str) -> tuple[str, str]:
    """Validate and parse GitHub repository URL.

    Args:
        url: Repository URL to validate

    Returns:
        Tuple of (owner, repo_name)

    Raises:
        CLIError: If URL is invalid
    """
    import re

    # Support various GitHub URL formats
    patterns = [
        r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
        r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$",
        r"^([^/]+)/([^/]+)$"  # Simple owner/repo format
    ]

    for pattern in patterns:
        match = re.match(pattern, url.strip())
        if match:
            owner, repo = match.groups()
            return owner, repo

    raise CLIError(f"Invalid GitHub repository URL: {url}")


def display_analysis_summary(results: dict) -> None:
    """Display analysis results summary."""
    table = Table(title="Analysis Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Repository", results.get("repository", "N/A"))
    table.add_row("Total Forks Found", str(results.get("total_forks", 0)))
    table.add_row("Active Forks Analyzed", str(results.get("analyzed_forks", 0)))
    table.add_row("Features Discovered", str(results.get("total_features", 0)))
    table.add_row("High-Value Features", str(results.get("high_value_features", 0)))

    console.print(table)


def display_repository_details(repo_data: dict) -> None:
    """Display detailed repository information."""
    table = Table(title=f"Repository Details: {repo_data.get('full_name', 'Unknown')}")
    table.add_column("Property", style="cyan", width=20)
    table.add_column("Value", style="green")

    table.add_row("Name", repo_data.get("name", "N/A"))
    table.add_row("Owner", repo_data.get("owner", {}).get("login", "N/A"))
    table.add_row("Description", repo_data.get("description", "No description") or "No description")
    table.add_row("Language", repo_data.get("language", "N/A") or "Not specified")
    table.add_row("Stars", str(repo_data.get("stargazers_count", 0)))
    table.add_row("Forks", str(repo_data.get("forks_count", 0)))
    table.add_row("Open Issues", str(repo_data.get("open_issues_count", 0)))
    table.add_row("Created", repo_data.get("created_at", "N/A"))
    table.add_row("Updated", repo_data.get("updated_at", "N/A"))
    table.add_row("Default Branch", repo_data.get("default_branch", "N/A"))
    table.add_row("Size (KB)", str(repo_data.get("size", 0)))
    table.add_row("License", repo_data.get("license", {}).get("name", "No license") if repo_data.get("license") else "No license")

    console.print(table)


def display_forks_summary(forks: list) -> None:
    """Display a summary table of forks."""
    if not forks:
        console.print("[yellow]No forks found.[/yellow]")
        return

    table = Table(title=f"Fork Summary ({len(forks)} forks found)")
    table.add_column("#", style="dim", width=4)
    table.add_column("Fork Name", style="cyan", min_width=25)
    table.add_column("Owner", style="blue", min_width=15)
    table.add_column("Stars", style="yellow", justify="right", width=8)
    table.add_column("Commits Ahead", style="green", justify="right", width=12)
    table.add_column("Last Updated", style="magenta", width=12)
    table.add_column("Language", style="white", width=10)

    for i, fork in enumerate(forks[:50], 1):  # Show first 50 forks
        commits_ahead = getattr(fork, "commits_ahead", 0) if hasattr(fork, "commits_ahead") else "Unknown"
        last_updated = getattr(fork, "updated_at", "Unknown")
        if last_updated != "Unknown" and "T" in str(last_updated):
            last_updated = str(last_updated).split("T")[0]

        table.add_row(
            str(i),
            getattr(fork, "name", "Unknown"),
            getattr(fork, "owner", {}).get("login", "Unknown") if hasattr(fork, "owner") else "Unknown",
            str(getattr(fork, "stargazers_count", 0)),
            str(commits_ahead),
            str(last_updated),
            getattr(fork, "language", "N/A") or "N/A"
        )

    console.print(table)

    if len(forks) > 50:
        console.print(f"[dim]... and {len(forks) - 50} more forks[/dim]")


def display_commit_explanations(fork_analyses: list, explain: bool) -> None:
    """Display commit explanations for analyzed forks."""
    if not explain or not fork_analyses:
        return

    from forklift.analysis.explanation_formatter import ExplanationFormatter
    from forklift.models.analysis import CommitWithExplanation

    console.print("\n[bold blue]Commit Explanations[/bold blue]")
    console.print("=" * 60)

    formatter = ExplanationFormatter(use_colors=True, use_icons=True, use_simple_tables=True)
    total_explanations = 0

    for fork_analysis in fork_analyses:
        if not fork_analysis.commit_explanations:
            continue

        fork_name = fork_analysis.fork.repository.full_name
        explanations = fork_analysis.commit_explanations

        console.print(f"\n[bold cyan]Fork: {fork_name}[/bold cyan]")
        console.print(f"Found {len(explanations)} explained commits:")

        # Create CommitWithExplanation objects for the formatter
        commits_with_explanations = []
        for explanation in explanations:
            # Find the corresponding commit from the fork analysis
            commit = None
            for feature in fork_analysis.features:
                for feature_commit in feature.commits:
                    if feature_commit.sha == explanation.commit_sha:
                        commit = feature_commit
                        break
                if commit:
                    break

            if commit:
                commits_with_explanations.append(CommitWithExplanation(
                    commit=commit,
                    explanation=explanation
                ))

        if commits_with_explanations:
            # Use the formatter to display explanations as a table
            table = formatter.format_explanation_table(commits_with_explanations)
            if isinstance(table, str):
                # Simple ASCII table
                print(table)
            else:
                # Rich table
                console.print(table)
            total_explanations += len(commits_with_explanations)

        console.print()  # Empty line between forks

    if total_explanations > 0:
        console.print(f"[green]✓ Generated {total_explanations} commit explanations[/green]")
    else:
        console.print("[yellow]No commit explanations were generated[/yellow]")


def display_fork_details(fork, fork_metrics=None) -> None:
    """Display detailed information about a specific fork."""
    fork_name = getattr(fork, "full_name", "Unknown Fork")

    # Basic fork information
    table = Table(title=f"Fork Details: {fork_name}")
    table.add_column("Property", style="cyan", width=20)
    table.add_column("Value", style="green")

    table.add_row("Full Name", getattr(fork, "full_name", "N/A"))
    table.add_row("Owner", getattr(fork, "owner", {}).get("login", "N/A") if hasattr(fork, "owner") else "N/A")
    table.add_row("Description", getattr(fork, "description", "No description") or "No description")
    table.add_row("Language", getattr(fork, "language", "N/A") or "N/A")
    table.add_row("Stars", str(getattr(fork, "stargazers_count", 0)))
    table.add_row("Forks", str(getattr(fork, "forks_count", 0)))
    table.add_row("Open Issues", str(getattr(fork, "open_issues_count", 0)))
    table.add_row("Created", str(getattr(fork, "created_at", "N/A")))
    table.add_row("Updated", str(getattr(fork, "updated_at", "N/A")))
    table.add_row("Default Branch", getattr(fork, "default_branch", "N/A"))

    if fork_metrics:
        table.add_row("Commits Ahead", str(getattr(fork_metrics, "commits_ahead", "N/A")))
        table.add_row("Commits Behind", str(getattr(fork_metrics, "commits_behind", "N/A")))
        table.add_row("Last Activity", str(getattr(fork_metrics, "last_activity_date", "N/A")))

    console.print(table)


async def interactive_fork_selection(forks: list, config: ForkliftConfig) -> None:
    """Interactive mode for selecting and analyzing specific forks."""
    if not forks:
        console.print("[yellow]No forks available for selection.[/yellow]")
        return

    while True:
        console.print("\n" + "="*60)
        console.print("[bold blue]Interactive Fork Analysis[/bold blue]")
        console.print("="*60)

        # Display options
        console.print("\n[bold]Available Actions:[/bold]")
        console.print("1. View forks summary")
        console.print("2. View detailed fork information")
        console.print("3. Analyze specific fork")
        console.print("4. Analyze multiple forks")
        console.print("5. Exit interactive mode")

        choice = Prompt.ask(
            "\n[bold cyan]Choose an action[/bold cyan]",
            choices=["1", "2", "3", "4", "5"],
            default="1"
        )

        if choice == "1":
            # Show forks summary
            display_forks_summary(forks)

        elif choice == "2":
            # Show detailed fork information
            display_forks_summary(forks)

            try:
                fork_num = int(Prompt.ask(
                    f"\n[cyan]Enter fork number (1-{min(len(forks), 50)})[/cyan]",
                    default="1"
                ))

                if 1 <= fork_num <= min(len(forks), 50):
                    selected_fork = forks[fork_num - 1]
                    display_fork_details(selected_fork)
                else:
                    console.print("[red]Invalid fork number![/red]")

            except ValueError:
                console.print("[red]Please enter a valid number![/red]")

        elif choice == "3":
            # Analyze specific fork
            display_forks_summary(forks)

            try:
                fork_num = int(Prompt.ask(
                    f"\n[cyan]Enter fork number to analyze (1-{min(len(forks), 50)})[/cyan]",
                    default="1"
                ))

                if 1 <= fork_num <= min(len(forks), 50):
                    selected_fork = forks[fork_num - 1]

                    console.print(f"\n[green]Analyzing fork: {getattr(selected_fork, 'full_name', 'Unknown')}[/green]")

                    # Simulate fork analysis (placeholder for actual implementation)
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=console
                    ) as progress:
                        task = progress.add_task("Analyzing fork...", total=None)
                        await asyncio.sleep(2)  # Simulate analysis
                        progress.update(task, description="Analysis complete!")

                    # Display results
                    display_fork_details(selected_fork)
                    console.print("\n[green]✓ Fork analysis completed![/green]")

                else:
                    console.print("[red]Invalid fork number![/red]")

            except ValueError:
                console.print("[red]Please enter a valid number![/red]")

        elif choice == "4":
            # Analyze multiple forks
            display_forks_summary(forks)

            fork_range = Prompt.ask(
                "\n[cyan]Enter fork range (e.g., '1-5' or '1,3,5')[/cyan]",
                default="1-5"
            )

            try:
                selected_forks = []

                if "-" in fork_range:
                    # Range selection
                    start, end = map(int, fork_range.split("-"))
                    start = max(1, start)
                    end = min(len(forks), end)
                    selected_forks = forks[start-1:end]

                elif "," in fork_range:
                    # Individual selection
                    fork_nums = [int(x.strip()) for x in fork_range.split(",")]
                    selected_forks = [forks[i-1] for i in fork_nums if 1 <= i <= len(forks)]

                else:
                    # Single fork
                    fork_num = int(fork_range)
                    if 1 <= fork_num <= len(forks):
                        selected_forks = [forks[fork_num-1]]

                if selected_forks:
                    console.print(f"\n[green]Analyzing {len(selected_forks)} forks...[/green]")

                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        TaskProgressColumn(),
                        console=console
                    ) as progress:
                        task = progress.add_task("Analyzing forks...", total=len(selected_forks))

                        for i, fork in enumerate(selected_forks):
                            progress.update(task, advance=1, description=f"Analyzing {getattr(fork, 'name', 'fork')} ({i+1}/{len(selected_forks)})")
                            await asyncio.sleep(0.5)  # Simulate analysis

                    console.print(f"\n[green]✓ Analyzed {len(selected_forks)} forks successfully![/green]")
                else:
                    console.print("[red]No valid forks selected![/red]")

            except ValueError:
                console.print("[red]Invalid range format! Use '1-5' or '1,3,5'[/red]")

        elif choice == "5":
            # Exit
            console.print("\n[yellow]Exiting interactive mode...[/yellow]")
            break

        # Ask if user wants to continue
        if choice != "5":
            if not Confirm.ask("\n[dim]Continue with interactive mode?[/dim]", default=True):
                break


@click.group()
@click.version_option(version="0.1.0")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--debug", is_flag=True, help="Enable debug output")
@click.option("--config", "-c", type=click.Path(exists=True), help="Configuration file path")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, debug: bool, config: str | None) -> None:
    """Forklift - GitHub repository fork analysis tool.

    Discover and analyze valuable features across all forks of a GitHub repository.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Load configuration
    try:
        loaded_config = load_config(config) if config else load_config()
        ctx.obj["config"] = loaded_config
    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        sys.exit(1)

    # Setup logging with configuration
    setup_logging(verbose, debug, loaded_config)

    # Store CLI options
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug


@cli.command()
@click.argument("repository_url")
@click.option("--output", "-o", type=click.Path(), help="Output file path for report")
@click.option("--format", "output_format", type=click.Choice(["markdown", "json", "yaml"]),
              default="markdown", help="Output format")
@click.option("--auto-pr", is_flag=True, help="Automatically create pull requests for high-value features")
@click.option("--min-score", type=click.IntRange(0, 100), help="Minimum score threshold for features")
@click.option("--max-forks", type=click.IntRange(1, 1000), help="Maximum number of forks to analyze")
@click.option("--dry-run", is_flag=True, help="Perform analysis without creating PRs or writing files")
@click.option("--interactive", "-i", is_flag=True, help="Enter interactive mode for fork selection and analysis")
@click.option("--scan-all", is_flag=True, help="Scan all forks including those with no commits ahead (bypasses default filtering)")
@click.option("--explain", is_flag=True, help="Generate explanations for each commit during analysis")
@click.option("--disable-cache", is_flag=True, help="Bypass cache and fetch fresh data from GitHub API")
@click.pass_context
def analyze(
    ctx: click.Context,
    repository_url: str,
    output: str | None,
    output_format: str,
    auto_pr: bool,
    min_score: int | None,
    max_forks: int | None,
    dry_run: bool,
    interactive: bool,
    scan_all: bool,
    explain: bool,
    disable_cache: bool
) -> None:
    """Analyze a repository and its forks for valuable features.

    REPOSITORY_URL can be:
    - Full GitHub URL: https://github.com/owner/repo
    - SSH URL: git@github.com:owner/repo.git
    - Short format: owner/repo
    """
    config: ForkliftConfig = ctx.obj["config"]
    verbose: bool = ctx.obj["verbose"]

    # Override config with CLI options
    if min_score is not None:
        config.analysis.min_score_threshold = min_score
    if max_forks is not None:
        config.analysis.max_forks_to_analyze = max_forks
    if auto_pr:
        config.analysis.auto_pr_enabled = auto_pr
    if dry_run:
        config.dry_run = dry_run

    config.output_format = output_format

    try:
        # Validate repository URL
        owner, repo_name = validate_repository_url(repository_url)

        if verbose:
            console.print(f"[blue]Analyzing repository: {owner}/{repo_name}[/blue]")

        if interactive:
            # Run interactive analysis
            results = asyncio.run(_run_interactive_analysis(config, owner, repo_name, verbose, scan_all, explain, disable_cache))
        else:
            # Run standard analysis
            results = asyncio.run(_run_analysis(config, owner, repo_name, verbose, scan_all, explain, disable_cache))

            # Display results
            display_analysis_summary(results)

            # Display commit explanations if generated
            if explain and results.get("fork_analyses"):
                display_commit_explanations(results["fork_analyses"], explain)

            # Save output if specified
            if output and not dry_run:
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(results.get("report", ""))

                console.print(f"[green]Report saved to: {output_path}[/green]")

            # Success message
            high_value_count = results.get("high_value_features", 0)
            if high_value_count > 0:
                console.print(f"[green]✓ Analysis complete! Found {high_value_count} high-value features.[/green]")
            else:
                console.print("[yellow]Analysis complete. No high-value features found.[/yellow]")

    except CLIError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except (GitHubPrivateRepositoryError, GitHubEmptyRepositoryError, GitHubForkAccessError, GitHubTimeoutError) as e:
        # Display user-friendly error message
        console.print(f"[yellow]Repository access issue: {e}[/yellow]")
        console.print("[dim]Tip: Check repository URL and ensure you have access to the repository[/dim]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Analysis interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        if ctx.obj["debug"]:
            console.print_exception()
        else:
            console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--github-token", help="GitHub API token")
@click.option("--min-score", type=click.IntRange(0, 100), help="Minimum score threshold")
@click.option("--max-forks", type=click.IntRange(1, 1000), help="Maximum forks to analyze")
@click.option("--output-format", type=click.Choice(["markdown", "json", "yaml"]), help="Default output format")
@click.option("--cache-duration", type=int, help="Cache duration in hours")
@click.option("--save", type=click.Path(), help="Save configuration to file")
@click.pass_context
def configure(
    ctx: click.Context,
    github_token: str | None,
    min_score: int | None,
    max_forks: int | None,
    output_format: str | None,
    cache_duration: int | None,
    save: str | None
) -> None:
    """Configure Forklift settings interactively or via options."""
    config: ForkliftConfig = ctx.obj["config"]

    # Update configuration with provided options
    if github_token:
        config.github.token = github_token
    if min_score is not None:
        config.analysis.min_score_threshold = min_score
    if max_forks is not None:
        config.analysis.max_forks_to_analyze = max_forks
    if output_format:
        config.output_format = output_format
    if cache_duration is not None:
        config.cache.duration_hours = cache_duration

    # Interactive configuration if no options provided
    if not any([github_token, min_score, max_forks, output_format, cache_duration]):
        console.print("[blue]Interactive Configuration[/blue]")

        # GitHub token
        if not config.github.token:
            token = click.prompt("GitHub API token", hide_input=True, default="")
            if token:
                config.github.token = token

        # Analysis settings
        config.analysis.min_score_threshold = click.prompt(
            "Minimum score threshold (0-100)",
            default=config.analysis.min_score_threshold,
            type=click.IntRange(0, 100)
        )

        config.analysis.max_forks_to_analyze = click.prompt(
            "Maximum forks to analyze",
            default=config.analysis.max_forks_to_analyze,
            type=click.IntRange(1, 1000)
        )

        config.output_format = click.prompt(
            "Default output format",
            default=config.output_format,
            type=click.Choice(["markdown", "json", "yaml"])
        )

    # Display current configuration
    table = Table(title="Current Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("GitHub Token", "***" if config.github.token else "Not set")
    table.add_row("Min Score Threshold", str(config.analysis.min_score_threshold))
    table.add_row("Max Forks to Analyze", str(config.analysis.max_forks_to_analyze))
    table.add_row("Output Format", config.output_format)
    table.add_row("Cache Duration (hours)", str(config.cache.duration_hours))
    table.add_row("Auto PR Enabled", str(config.analysis.auto_pr_enabled))

    console.print(table)

    # Save configuration if requested
    if save:
        try:
            config.save_to_file(save)
            console.print(f"[green]Configuration saved to: {save}[/green]")
        except Exception as e:
            console.print(f"[red]Error saving configuration: {e}[/red]")
            sys.exit(1)


@cli.command()
@click.argument("repository_url")
@click.pass_context
def interactive(ctx: click.Context, repository_url: str) -> None:
    """Launch interactive mode for repository analysis.

    REPOSITORY_URL can be:
    - Full GitHub URL: https://github.com/owner/repo
    - SSH URL: git@github.com:owner/repo.git
    - Short format: owner/repo
    """
    config: ForkliftConfig = ctx.obj["config"]
    verbose: bool = ctx.obj["verbose"]

    try:
        # Validate repository URL
        owner, repo_name = validate_repository_url(repository_url)

        console.print(f"[blue]Starting interactive analysis for: {owner}/{repo_name}[/blue]")

        # Run interactive analysis
        asyncio.run(_run_interactive_analysis(config, owner, repo_name, verbose))

    except CLIError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interactive mode interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        if ctx.obj["debug"]:
            console.print_exception()
        else:
            console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("repository_url")
@click.option("--cron", help="Cron expression for scheduling (e.g., '0 0 * * 0' for weekly)")
@click.option("--interval", type=int, help="Interval in hours for recurring analysis")
@click.option("--config-file", type=click.Path(exists=True), help="Configuration file for scheduled runs")
@click.pass_context
def schedule(
    ctx: click.Context,
    repository_url: str,
    cron: str | None,
    interval: int | None,
    config_file: str | None
) -> None:
    """Schedule recurring repository analysis.

    Note: This command sets up the schedule configuration but requires
    an external scheduler (like cron) to actually run the analysis.
    """
    if not cron and not interval:
        console.print("[red]Error: Either --cron or --interval must be specified[/red]")
        sys.exit(1)

    if cron and interval:
        console.print("[red]Error: Cannot specify both --cron and --interval[/red]")
        sys.exit(1)

    try:
        owner, repo_name = validate_repository_url(repository_url)
    except CLIError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    # Create schedule configuration
    schedule_config = {
        "repository": f"{owner}/{repo_name}",
        "schedule": cron if cron else f"every {interval} hours",
        "config_file": config_file or "forklift.yaml"
    }

    # Display schedule information
    panel = Panel.fit(
        f"Repository: {owner}/{repo_name}\n"
        f"Schedule: {schedule_config['schedule']}\n"
        f"Config: {schedule_config['config_file']}\n\n"
        f"To activate this schedule, add the following to your crontab:\n"
        f"[code]{cron or f'0 */{interval} * * *'} forklift analyze {repository_url}[/code]",
        title="Schedule Configuration",
        border_style="blue"
    )

    console.print(panel)

    console.print("\n[yellow]Note: This command only displays the schedule configuration.[/yellow]")
    console.print("[yellow]Use your system's cron or task scheduler to actually run the analysis.[/yellow]")


@cli.command("show-repo")
@click.argument("repository_url")
@click.pass_context
def show_repo(ctx: click.Context, repository_url: str) -> None:
    """Display detailed repository information.

    REPOSITORY_URL can be:
    - Full GitHub URL: https://github.com/owner/repo
    - SSH URL: git@github.com:owner/repo.git
    - Short format: owner/repo
    """
    config: ForkliftConfig = ctx.obj["config"]
    verbose: bool = ctx.obj["verbose"]

    try:
        # Validate GitHub token
        if not config.github.token:
            raise CLIError("GitHub token not configured. Use 'forklift configure' to set it up.")

        if verbose:
            console.print(f"[blue]Fetching repository details for: {repository_url}[/blue]")

        # Run repository details display
        asyncio.run(_show_repository_details(config, repository_url, verbose))

    except CLIError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        if ctx.obj["debug"]:
            console.print_exception()
        else:
            console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


@cli.command("show-forks")
@click.argument("repository_url")
@click.option("--max-forks", type=click.IntRange(1, 1000), help="Maximum number of forks to display")
@click.option("--detail", is_flag=True, help="Fetch exact commit counts ahead for each fork using additional API requests")
@click.option("--show-commits", type=click.IntRange(0, 1000000), default=0, help="Show last N commits for each fork (default: 0)")
@click.option("--force-all-commits", is_flag=True, help="Bypass optimization and download commits for all forks when using --show-commits")
@click.pass_context
def show_forks(ctx: click.Context, repository_url: str, max_forks: int | None, detail: bool, show_commits: int, force_all_commits: bool) -> None:
    """Display a summary table of repository forks with key metrics.

    Use --detail flag to fetch exact commit counts ahead for each fork.
    This makes additional API requests but provides precise commit information.

    Use --show-commits N to display the last N commits for each fork.
    This adds a "Recent Commits" column showing commit messages (max 10 commits).
    
    Use --force-all-commits to bypass optimization and download commits for all forks,
    even those with no commits ahead (normally skipped to save API calls).

    REPOSITORY_URL can be:
    - Full GitHub URL: https://github.com/owner/repo
    - SSH URL: git@github.com:owner/repo.git
    - Short format: owner/repo
    """
    config: ForkliftConfig = ctx.obj["config"]
    verbose: bool = ctx.obj["verbose"]

    try:
        # Validate GitHub token
        if not config.github.token:
            raise CLIError("GitHub token not configured. Use 'forklift configure' to set it up.")

        if verbose:
            console.print(f"[blue]Fetching forks for: {repository_url}[/blue]")

        # Run forks summary display
        asyncio.run(_show_forks_summary(config, repository_url, max_forks, verbose, detail, show_commits, force_all_commits))

    except CLIError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        if ctx.obj["debug"]:
            console.print_exception()
        else:
            console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


@cli.command("list-forks")
@click.argument("repository_url")
@click.pass_context
def list_forks(ctx: click.Context, repository_url: str) -> None:
    """Display a lightweight preview of repository forks using minimal API calls.

    This command provides a fast overview of all forks without detailed analysis,
    showing basic information like fork name, owner, stars, and last push date.

    REPOSITORY_URL can be:
    - Full GitHub URL: https://github.com/owner/repo
    - SSH URL: git@github.com:owner/repo.git
    - Short format: owner/repo
    """
    config: ForkliftConfig = ctx.obj["config"]
    verbose: bool = ctx.obj["verbose"]

    try:
        # Validate GitHub token
        if not config.github.token:
            raise CLIError("GitHub token not configured. Use 'forklift configure' to set it up.")

        if verbose:
            console.print(f"[blue]Fetching lightweight forks preview for: {repository_url}[/blue]")

        # Run forks preview display
        asyncio.run(_list_forks_preview(config, repository_url, verbose))

    except CLIError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        if ctx.obj["debug"]:
            console.print_exception()
        else:
            console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


@cli.command("show-fork-data")
@click.argument("repository_url")
@click.option("--exclude-archived", is_flag=True, help="Exclude archived forks from display")
@click.option("--exclude-disabled", is_flag=True, help="Exclude disabled forks from display")
@click.option("--sort-by", type=click.Choice(["stars", "forks", "size", "activity", "commits_status", "name", "owner", "language"]), default="stars", help="Sort forks by specified criteria")
@click.option("--show-all", is_flag=True, help="Show all forks instead of limiting to 50")
@click.option("--disable-cache", is_flag=True, help="Bypass cache and fetch fresh data")
@click.option("--show-commits", type=click.IntRange(0, 10), default=0, help="Show last N commits for each fork (0-10, default: 0)")
@click.option("--interactive", "-i", is_flag=True, help="Enter interactive mode for fork selection")
@click.pass_context
def show_fork_data(
    ctx: click.Context,
    repository_url: str,
    exclude_archived: bool,
    exclude_disabled: bool,
    sort_by: str,
    show_all: bool,
    disable_cache: bool,
    show_commits: int,
    interactive: bool
) -> None:
    """Display comprehensive fork data and let users choose which forks to analyze.

    This command shows all available fork information without automatic filtering or scoring,
    allowing users to make informed decisions about which forks warrant detailed analysis.

    Use --show-commits N to display the last N commits for each fork (0-10).
    This adds a "Recent Commits" column showing commit messages and requires additional API calls.

    REPOSITORY_URL can be:
    - Full GitHub URL: https://github.com/owner/repo
    - SSH URL: git@github.com:owner/repo.git
    - Short format: owner/repo
    """
    config: ForkliftConfig = ctx.obj["config"]
    verbose: bool = ctx.obj["verbose"]

    try:
        # Validate GitHub token
        if not config.github.token:
            raise CLIError("GitHub token not configured. Use 'forklift configure' to set it up.")

        if verbose:
            console.print(f"[blue]Collecting comprehensive fork data for: {repository_url}[/blue]")

        # Run comprehensive fork data display
        asyncio.run(_show_comprehensive_fork_data(
            config, repository_url, exclude_archived, exclude_disabled, sort_by, show_all, disable_cache, show_commits, interactive, verbose
        ))

    except CLIError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        if ctx.obj["debug"]:
            console.print_exception()
        else:
            console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


@cli.command("show-promising")
@click.argument("repository_url")
@click.option("--min-stars", type=click.IntRange(0, 10000), default=0, help="Minimum star count")
@click.option("--min-commits-ahead", type=click.IntRange(0, 1000), default=1, help="Minimum commits ahead of upstream")
@click.option("--max-days-since-activity", type=click.IntRange(1, 3650), default=365, help="Maximum days since last activity")
@click.option("--min-activity-score", type=click.FloatRange(0.0, 1.0), default=0.0, help="Minimum activity score (0.0-1.0)")
@click.option("--include-archived", is_flag=True, help="Include archived repositories")
@click.option("--include-disabled", is_flag=True, help="Include disabled repositories")
@click.option("--min-fork-age-days", type=click.IntRange(0, 3650), default=0, help="Minimum fork age in days")
@click.option("--max-fork-age-days", type=click.IntRange(1, 3650), help="Maximum fork age in days")
@click.option("--max-forks", type=click.IntRange(1, 1000), help="Maximum number of forks to analyze")
@click.pass_context
def show_promising(
    ctx: click.Context,
    repository_url: str,
    min_stars: int,
    min_commits_ahead: int,
    max_days_since_activity: int,
    min_activity_score: float,
    include_archived: bool,
    include_disabled: bool,
    min_fork_age_days: int,
    max_fork_age_days: int | None,
    max_forks: int | None
) -> None:
    """Display promising forks based on configurable filtering criteria.

    This command analyzes all forks and displays only those that meet
    the specified criteria for being "promising" - having significant
    changes, recent activity, and community engagement.

    REPOSITORY_URL can be:
    - Full GitHub URL: https://github.com/owner/repo
    - SSH URL: git@github.com:owner/repo.git
    - Short format: owner/repo
    """
    config: ForkliftConfig = ctx.obj["config"]
    verbose: bool = ctx.obj["verbose"]

    try:
        # Validate GitHub token
        if not config.github.token:
            raise CLIError("GitHub token not configured. Use 'forklift configure' to set it up.")

        if verbose:
            console.print(f"[blue]Finding promising forks for: {repository_url}[/blue]")

        # Run promising forks analysis
        asyncio.run(_show_promising_forks(
            config, repository_url, min_stars, min_commits_ahead,
            max_days_since_activity, min_activity_score, include_archived,
            include_disabled, min_fork_age_days, max_fork_age_days, max_forks, verbose
        ))

    except CLIError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        if ctx.obj["debug"]:
            console.print_exception()
        else:
            console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


@cli.command("analyze-fork")
@click.argument("fork_url")
@click.option("--branch", "-b", help="Specific branch to analyze (defaults to repository default branch)")
@click.option("--max-commits", type=click.IntRange(1, 200), default=50, help="Maximum commits to analyze")
@click.option("--include-merge-commits", is_flag=True, help="Include merge commits in analysis")
@click.option("--show-commit-details", is_flag=True, help="Show detailed commit information")
@click.option("--explain", is_flag=True, help="Generate explanations for each commit during analysis")
@click.pass_context
def analyze_fork(
    ctx: click.Context,
    fork_url: str,
    branch: str | None,
    max_commits: int,
    include_merge_commits: bool,
    show_commit_details: bool,
    explain: bool
) -> None:
    """Analyze a specific fork and optionally a specific branch for features and changes.

    This command performs detailed analysis of a fork including:
    - Repository and branch information
    - Commit analysis and categorization
    - Feature extraction and significance scoring
    - Change patterns and author statistics
    - Comparison with upstream repository

    FORK_URL can be:
    - Full GitHub URL: https://github.com/owner/repo
    - SSH URL: git@github.com:owner/repo.git
    - Short format: owner/repo
    """
    config: ForkliftConfig = ctx.obj["config"]
    verbose: bool = ctx.obj["verbose"]

    try:
        # Validate GitHub token
        if not config.github.token:
            raise CLIError("GitHub token not configured. Use 'forklift configure' to set it up.")

        if verbose:
            console.print(f"[blue]Analyzing fork: {fork_url}" + (f" (branch: {branch})" if branch else "") + "[/blue]")

        # Run fork analysis
        asyncio.run(_analyze_fork(
            config, fork_url, branch, max_commits, include_merge_commits, show_commit_details, verbose, explain
        ))

    except CLIError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Analysis interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        if ctx.obj["debug"]:
            console.print_exception()
        else:
            console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


@cli.command("show-commits")
@click.argument("fork_url")
@click.option("--branch", "-b", help="Branch to show commits from (defaults to repository default branch)")
@click.option("--limit", "-l", type=click.IntRange(1, 200), default=20, help="Number of commits to display")
@click.option("--since", help="Show commits since date (YYYY-MM-DD format)")
@click.option("--until", help="Show commits until date (YYYY-MM-DD format)")
@click.option("--author", help="Filter commits by author username")
@click.option("--include-merge", is_flag=True, help="Include merge commits")
@click.option("--show-files", is_flag=True, help="Show changed files for each commit")
@click.option("--show-stats", is_flag=True, help="Show detailed statistics")
@click.option("--explain", is_flag=True, help="Generate explanations for each commit")
@click.option("--ai-summary", is_flag=True, help="Generate AI-powered summaries for each commit (requires OpenAI API key)")
@click.option("--ai-summary-compact", is_flag=True, help="Generate compact AI summaries with minimal formatting (requires OpenAI API key)")
@click.option("--detail", is_flag=True, help="Display comprehensive commit information including GitHub URLs, AI summaries, messages, and diffs. Automatically skips forks with no commits ahead unless --force is used.")
@click.option("--force", is_flag=True, help="Force analysis even for forks with no commits ahead (only applies with --detail flag)")
@click.option("--disable-cache", is_flag=True, help="Disable caching and fetch fresh data from GitHub API")
@click.pass_context
def show_commits(
    ctx: click.Context,
    fork_url: str,
    branch: str | None,
    limit: int,
    since: str | None,
    until: str | None,
    author: str | None,
    include_merge: bool,
    show_files: bool,
    show_stats: bool,
    explain: bool,
    ai_summary: bool,
    ai_summary_compact: bool,
    detail: bool,
    force: bool,
    disable_cache: bool
) -> None:
    """Display detailed commit information for a repository or specific branch.

    This command shows commit history with detailed information including:
    - Commit SHA, message, author, and date
    - File changes and line statistics
    - Commit type categorization
    - Author and activity patterns

    When using the --detail flag, the command automatically checks if the fork
    has commits ahead of its upstream repository. If no commits are ahead,
    the analysis is skipped with a clear message. Use --force to override
    this behavior and analyze all forks regardless of commit status.

    FORK_URL can be:
    - Full GitHub URL: https://github.com/owner/repo
    - SSH URL: git@github.com:owner/repo.git
    - Short format: owner/repo
    """
    config: ForkliftConfig = ctx.obj["config"]
    verbose: bool = ctx.obj["verbose"]

    try:
        # Validate GitHub token
        if not config.github.token:
            raise CLIError("GitHub token not configured. Use 'forklift configure' to set it up.")

        # Validate AI summary options
        if ai_summary and ai_summary_compact:
            raise CLIError("Cannot use both --ai-summary and --ai-summary-compact flags together. Choose one.")

        # Parse date filters if provided
        since_date = None
        until_date = None

        if since:
            try:
                since_date = datetime.strptime(since, "%Y-%m-%d")
            except ValueError:
                raise CLIError(f"Invalid since date format: {since}. Use YYYY-MM-DD format.")

        if until:
            try:
                until_date = datetime.strptime(until, "%Y-%m-%d")
            except ValueError:
                raise CLIError(f"Invalid until date format: {until}. Use YYYY-MM-DD format.")

        if verbose:
            console.print(f"[blue]Fetching commits from: {fork_url}" + (f" (branch: {branch})" if branch else "") + "[/blue]")

        # Run commit display
        asyncio.run(_show_commits(
            config, fork_url, branch, limit, since_date, until_date,
            author, include_merge, show_files, show_stats, verbose, explain, ai_summary, ai_summary_compact, detail, force, disable_cache
        ))

    except CLIError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        if ctx.obj["debug"]:
            console.print_exception()
        else:
            console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


@cli.command("show-fork-details")
@click.argument("fork_url")
@click.option("--max-branches", type=click.IntRange(1, 100), default=10, help="Maximum branches to display")
@click.option("--max-contributors", type=click.IntRange(1, 100), default=10, help="Maximum contributors to display")
@click.option("--no-branches", is_flag=True, help="Skip branch information")
@click.option("--no-contributors", is_flag=True, help="Skip contributor information")
@click.option("--no-commit-stats", is_flag=True, help="Skip commit statistics")
@click.pass_context
def show_fork_details(
    ctx: click.Context,
    fork_url: str,
    max_branches: int,
    max_contributors: int,
    no_branches: bool,
    no_contributors: bool,
    no_commit_stats: bool
) -> None:
    """Display detailed information about a specific fork including branches and statistics.

    This command provides comprehensive information about a fork including:
    - Basic repository information
    - Branch details with commit counts and activity
    - Contributor information
    - Programming languages and topics
    - Repository statistics

    FORK_URL can be:
    - Full GitHub URL: https://github.com/owner/repo
    - SSH URL: git@github.com:owner/repo.git
    - Short format: owner/repo
    """
    config: ForkliftConfig = ctx.obj["config"]
    verbose: bool = ctx.obj["verbose"]

    try:
        # Validate GitHub token
        if not config.github.token:
            raise CLIError("GitHub token not configured. Use 'forklift configure' to set it up.")

        if verbose:
            console.print(f"[blue]Fetching detailed information for fork: {fork_url}[/blue]")

        # Run fork details display
        asyncio.run(_show_fork_details(
            config, fork_url, max_branches, max_contributors,
            not no_branches, not no_contributors, not no_commit_stats, verbose
        ))

    except CLIError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        if ctx.obj["debug"]:
            console.print_exception()
        else:
            console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


async def _show_repository_details(
    config: ForkliftConfig,
    repository_url: str,
    verbose: bool
) -> None:
    """Show repository details using the display service with caching.

    Args:
        config: Forklift configuration
        repository_url: Repository URL to display
        verbose: Whether to show verbose output
    """
    # Initialize cache manager
    cache_manager = None
    try:
        cache_manager = AnalysisCacheManager()
        await cache_manager.initialize()
    except Exception as e:
        logger.warning(f"Failed to initialize cache manager: {e}")
        # Continue without cache

    try:
        async with GitHubClient(config.github) as github_client:
            display_service = RepositoryDisplayService(github_client, console, cache_manager)

            try:
                repo_details = await display_service.show_repository_details(repository_url)

                if verbose:
                    console.print("\n[green]✓ Repository details displayed successfully[/green]")

            except Exception as e:
                logger.error(f"Failed to display repository details: {e}")
                raise CLIError(f"Failed to display repository details: {e}")

    finally:
        # Clean up cache manager
        if cache_manager:
            try:
                await cache_manager.close()
            except Exception as e:
                logger.warning(f"Failed to close cache manager: {e}")


async def _list_forks_preview(
    config: ForkliftConfig,
    repository_url: str,
    verbose: bool
) -> None:
    """Show lightweight forks preview using the display service.

    Args:
        config: Forklift configuration
        repository_url: Repository URL to get forks for
        verbose: Whether to show verbose output
    """
    async with GitHubClient(config.github) as github_client:
        display_service = RepositoryDisplayService(github_client, console)

        try:
            forks_preview = await display_service.list_forks_preview(repository_url)

            if verbose:
                total_forks = forks_preview["total_forks"]
                console.print(f"\n[green]✓ Displayed {total_forks} forks in lightweight preview[/green]")

        except Exception as e:
            logger.error(f"Failed to display forks preview: {e}")
            raise CLIError(f"Failed to display forks preview: {e}")


async def _show_comprehensive_fork_data(
    config: ForkliftConfig,
    repository_url: str,
    exclude_archived: bool,
    exclude_disabled: bool,
    sort_by: str,
    show_all: bool,
    disable_cache: bool,
    show_commits: int,
    interactive: bool,
    verbose: bool
) -> None:
    """Show comprehensive fork data and allow user-driven fork selection.

    Args:
        config: Forklift configuration
        repository_url: Repository URL to analyze
        exclude_archived: Whether to exclude archived forks
        exclude_disabled: Whether to exclude disabled forks
        sort_by: Sort criteria for the display
        show_all: Whether to show all forks or limit display
        disable_cache: Whether to bypass cache for fresh data
        show_commits: Number of recent commits to show for each fork (0-10)
        interactive: Whether to enter interactive mode
        verbose: Enable verbose output
    """
    async with GitHubClient(config.github) as github_client:
        try:
            # Use RepositoryDisplayService for consistent display
            display_service = RepositoryDisplayService(github_client, console)

            if verbose:
                console.print(f"[blue]Collecting comprehensive fork data for: {repository_url}[/blue]")

            # Show comprehensive fork data using the service
            result = await display_service.show_fork_data(
                repo_url=repository_url,
                exclude_archived=exclude_archived,
                exclude_disabled=exclude_disabled,
                sort_by=sort_by,
                show_all=show_all,
                disable_cache=disable_cache,
                show_commits=show_commits
            )

            if verbose:
                stats = result.get("stats")
                if stats:
                    console.print(f"\n[green]✓ Data collection completed in {stats.processing_time_seconds:.2f} seconds[/green]")
                    console.print(f"[blue]API Efficiency: {stats.efficiency_percentage:.1f}% calls saved[/blue]")

            # Enter interactive mode if requested
            if interactive:
                qualification_result = result.get("qualification_result")
                if qualification_result:
                    await _interactive_fork_selection(qualification_result, config, verbose)

        except Exception as e:
            logger.error(f"Failed to show comprehensive fork data: {e}")
            raise CLIError(f"Failed to show comprehensive fork data: {e}")


async def _show_forks_summary(
    config: ForkliftConfig,
    repository_url: str,
    max_forks: int | None,
    verbose: bool,
    detail: bool = False,
    show_commits: int = 0,
    force_all_commits: bool = False
) -> None:
    """Show forks summary using pagination-only fork data collection.

    Args:
        config: Forklift configuration
        repository_url: Repository URL to get forks for
        max_forks: Maximum number of forks to display (ignored - shows all)
        verbose: Whether to show verbose output
        detail: Whether to fetch exact commit counts ahead using additional API requests
        show_commits: Number of recent commits to show for each fork (0-10)
        force_all_commits: If True, bypass optimization and download commits for all forks
    """
    async with GitHubClient(config.github) as github_client:
        display_service = RepositoryDisplayService(github_client, console)

        try:
            if detail:
                # Use detailed fork display with exact commit counts
                fork_data_result = await display_service.show_fork_data_detailed(
                    repository_url,
                    max_forks=max_forks,
                    disable_cache=False,
                    show_commits=show_commits,
                    force_all_commits=force_all_commits
                )

                if verbose:
                    total_forks = fork_data_result["total_forks"]
                    displayed_forks = fork_data_result["displayed_forks"]
                    api_calls_made = fork_data_result.get("api_calls_made", 0)
                    console.print(f"\n[green]✓ Displayed {displayed_forks} of {total_forks} forks with detailed commit information[/green]")
                    console.print(f"[blue]Made {api_calls_made} additional API calls for commit comparison[/blue]")
            else:
                # Use standard fork data display (pagination-only)
                fork_data_result = await display_service.show_fork_data(
                    repository_url,
                    exclude_archived=False,
                    exclude_disabled=False,
                    sort_by="stars",
                    show_all=True,
                    disable_cache=False,
                    show_commits=show_commits,
                    force_all_commits=force_all_commits
                )

                if verbose:
                    total_forks = fork_data_result["total_forks"]
                    displayed_forks = fork_data_result["displayed_forks"]
                    console.print(f"\n[green]✓ Displayed {displayed_forks} of {total_forks} forks using pagination-only requests[/green]")

        except Exception as e:
            logger.error(f"Failed to display forks data: {e}")
            raise CLIError(f"Failed to display forks data: {e}")


async def _run_analysis(
    config: ForkliftConfig,
    owner: str,
    repo_name: str,
    verbose: bool,
    scan_all: bool = False,
    explain: bool = False,
    disable_cache: bool = False
) -> dict:
    """Run the actual repository analysis.

    Args:
        config: Forklift configuration
        owner: Repository owner
        repo_name: Repository name
        verbose: Whether to show verbose output
        scan_all: Whether to scan all forks (bypass filtering)
        explain: Whether to generate commit explanations
        disable_cache: Whether to bypass cache and fetch fresh data

    Returns:
        Dictionary with analysis results
    """
    # Validate GitHub token
    if not config.github.token:
        raise CLIError("GitHub token not configured. Use 'forklift configure' to set it up.")

    # Initialize services
    github_client = GitHubClient(config.github)

    fork_discovery = ForkDiscoveryService(
        github_client=github_client,
        max_forks_to_analyze=config.analysis.max_forks_to_analyze
    )

    # Initialize explanation engine if explanations are requested
    explanation_engine = None
    if explain:
        categorizer = CommitCategorizer()
        assessor = ImpactAssessor()
        generator = ExplanationGenerator()
        explanation_engine = CommitExplanationEngine(categorizer, assessor, generator)

    # Initialize repository analyzer
    repository_analyzer = RepositoryAnalyzer(
        github_client=github_client,
        explanation_engine=explanation_engine
    )

    ranking_engine = FeatureRankingEngine(config.scoring)

    results = {
        "repository": f"{owner}/{repo_name}",
        "total_forks": 0,
        "analyzed_forks": 0,
        "total_features": 0,
        "high_value_features": 0,
        "report": ""
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=not verbose
    ) as progress:

        # Step 1: Discover and filter forks
        task1 = progress.add_task("Discovering forks...", total=None)
        try:
            repository_url = f"https://github.com/{owner}/{repo_name}"
            all_forks = await fork_discovery.discover_forks(repository_url, disable_cache=disable_cache)
            results["total_forks"] = len(all_forks)

            if scan_all:
                # Skip filtering - analyze all forks
                forks = all_forks
                progress.update(task1, completed=True, description=f"Found {len(all_forks)} forks, scanning all (--scan-all enabled)")
            else:
                # Apply default filtering - skip forks with no commits ahead
                progress.update(task1, description=f"Found {len(all_forks)} forks, filtering...")
                forks = await fork_discovery.filter_active_forks(all_forks)
                skipped_count = len(all_forks) - len(forks)
                progress.update(task1, completed=True, description=f"Found {len(all_forks)} forks, {skipped_count} skipped (no commits ahead), {len(forks)} to analyze")
        except Exception as e:
            progress.update(task1, description=f"Failed to discover forks: {e}")
            raise CLIError(f"Failed to discover forks: {e}")

        # Step 2: Get base repository for comparison
        base_repo_task = progress.add_task("Getting base repository...", total=None)
        try:
            base_repo = await github_client.get_repository(owner, repo_name, disable_cache=disable_cache)
            progress.update(base_repo_task, completed=True, description="Base repository retrieved")
        except Exception as e:
            progress.update(base_repo_task, description=f"Failed to get base repository: {e}")
            raise CLIError(f"Failed to get base repository: {e}")

        # Step 3: Analyze forks
        forks_to_analyze = forks[:config.analysis.max_forks_to_analyze]
        task2 = progress.add_task("Analyzing forks...", total=len(forks_to_analyze))
        analyzed_count = 0
        total_features = 0
        high_value_features = 0
        fork_analyses = []

        for i, fork in enumerate(forks_to_analyze):
            try:
                # Update progress with current fork and explanation status
                fork_name = fork.repository.full_name
                if explain:
                    description = f"Analyzing fork {i+1}/{len(forks_to_analyze)}: {fork_name} (with explanations)"
                else:
                    description = f"Analyzing fork {i+1}/{len(forks_to_analyze)}: {fork_name}"

                progress.update(task2, description=description)

                # Perform actual fork analysis
                fork_analysis = await repository_analyzer.analyze_fork(
                    fork=fork,
                    base_repo=base_repo,
                    explain=explain
                )

                fork_analyses.append(fork_analysis)
                analyzed_count += 1
                total_features += len(fork_analysis.features)

                # Count high-value features (placeholder scoring)
                for feature in fork_analysis.features:
                    if len(feature.commits) >= 2:  # Simple heuristic for now
                        high_value_features += 1

                progress.update(task2, advance=1)

            except Exception as e:
                if verbose:
                    console.print(f"[yellow]Warning: Failed to analyze fork {fork.repository.full_name}: {e}[/yellow]")
                progress.update(task2, advance=1)

        results["analyzed_forks"] = analyzed_count
        results["total_features"] = total_features
        results["high_value_features"] = high_value_features
        results["fork_analyses"] = fork_analyses

        # Step 4: Generate report
        task3 = progress.add_task("Generating report...", total=None)

        # Create analysis report
        report_lines = [
            f"# Fork Analysis Report for {owner}/{repo_name}",
            "",
            f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Forks Found:** {results['total_forks']}",
            f"**Forks Analyzed:** {results['analyzed_forks']}",
            f"**Total Features Discovered:** {results['total_features']}",
            f"**High-Value Features:** {results['high_value_features']}",
            f"**Explanations Generated:** {'Yes' if explain else 'No'}",
            "",
            "## Summary",
            "",
            f"Analysis completed for {results['analyzed_forks']} forks out of {results['total_forks']} total forks found.",
            f"Discovered {results['total_features']} features across all analyzed forks.",
            f"Found {results['high_value_features']} features that appear to be high-value contributions.",
            "",
        ]

        if explain and fork_analyses:
            report_lines.extend([
                "## Commit Explanations Summary",
                "",
                "Explanations were generated for commits in the analyzed forks.",
                "This helps understand what each commit does and its potential value.",
                "",
            ])

        report_lines.extend([
            "## Configuration Used",
            "",
            f"- Minimum Score Threshold: {config.analysis.min_score_threshold}",
            f"- Maximum Forks to Analyze: {config.analysis.max_forks_to_analyze}",
            f"- Auto PR Enabled: {config.analysis.auto_pr_enabled}",
            f"- Explanations Enabled: {explain}",
            f"- Scan All Forks: {scan_all}",
        ])

        results["report"] = "\n".join(report_lines)
        progress.update(task3, completed=True, description="Report generated")

    return results


async def _run_interactive_analysis(
    config: ForkliftConfig,
    owner: str,
    repo_name: str,
    verbose: bool,
    scan_all: bool = False,
    explain: bool = False,
    disable_cache: bool = False
) -> dict:
    """Run interactive repository analysis with user confirmation stops.

    Args:
        config: Forklift configuration
        owner: Repository owner
        repo_name: Repository name
        verbose: Whether to show verbose output
        scan_all: Whether to scan all forks (bypass filtering)
        explain: Whether to generate commit explanations
        disable_cache: Whether to bypass cache and fetch fresh data

    Returns:
        Dictionary with analysis results
    """
    # Validate GitHub token
    if not config.github.token:
        raise CLIError("GitHub token not configured. Use 'forklift configure' to set it up.")

    # Warn about cache disabling in interactive mode
    if disable_cache:
        console.print("[yellow]WARNING: Cache disabling in interactive mode is not fully implemented yet.[/yellow]")

    # Initialize GitHub client
    github_client = GitHubClient(config.github)

    # Initialize explanation engine if requested
    explanation_engine = None
    if explain:
        categorizer = CommitCategorizer()
        impact_assessor = ImpactAssessor()
        generator = ExplanationGenerator()
        explanation_engine = CommitExplanationEngine(categorizer, generator)

    # Initialize interactive orchestrator
    orchestrator = InteractiveAnalysisOrchestrator(
        github_client=github_client,
        config=config.interactive,
        console=console
    )

    # Add analysis steps
    orchestrator.add_step(RepositoryDiscoveryStep(github_client))
    orchestrator.add_step(ForkDiscoveryStep(github_client, config.analysis.max_forks_to_analyze))

    # Configure filtering based on scan_all flag
    if not scan_all:
        orchestrator.add_step(ForkFilteringStep(min_commits_ahead=1, min_stars=0))

    orchestrator.add_step(ForkAnalysisStep(github_client, explanation_engine))
    orchestrator.add_step(FeatureRankingStep())

    try:
        # Run interactive analysis
        async with github_client:
            repo_url = f"https://github.com/{owner}/{repo_name}"
            result = await orchestrator.run_interactive_analysis(repo_url)

        # Convert result to expected format
        if result.user_aborted:
            return {
                "repository": f"{owner}/{repo_name}",
                "cancelled": True,
                "session_duration": str(result.session_duration),
                "completed_steps": len(result.completed_steps)
            }

        # Extract final results
        final_result = result.final_result or {}
        fork_analyses = final_result.get("fork_analyses", [])
        ranked_features = final_result.get("ranked_features", [])

        # Calculate summary metrics
        total_forks = len(fork_analyses)
        total_features = len(ranked_features)
        high_value_features = len([f for f in ranked_features if f.score >= 80])

        return {
            "repository": f"{owner}/{repo_name}",
            "total_forks": total_forks,
            "analyzed_forks": total_forks,
            "total_features": total_features,
            "high_value_features": high_value_features,
            "session_duration": str(result.session_duration),
            "completed_steps": len(result.completed_steps),
            "total_confirmations": result.total_confirmations,
            "report": f"# Interactive Analysis Report for {owner}/{repo_name}\n\nInteractive analysis completed with {total_features} features found across {total_forks} forks."
        }

    except Exception as e:
        logger.error(f"Interactive analysis failed: {e}")
        raise CLIError(f"Interactive analysis failed: {e}")


async def _show_promising_forks(
    config: ForkliftConfig,
    repository_url: str,
    min_stars: int,
    min_commits_ahead: int,
    max_days_since_activity: int,
    min_activity_score: float,
    include_archived: bool,
    include_disabled: bool,
    min_fork_age_days: int,
    max_fork_age_days: int | None,
    max_forks: int | None,
    verbose: bool
) -> None:
    """Show promising forks using the display service.

    Args:
        config: Forklift configuration
        repository_url: Repository URL to analyze
        min_stars: Minimum star count filter
        min_commits_ahead: Minimum commits ahead filter
        max_days_since_activity: Maximum days since activity filter
        min_activity_score: Minimum activity score filter
        include_archived: Whether to include archived repositories
        include_disabled: Whether to include disabled repositories
        min_fork_age_days: Minimum fork age in days
        max_fork_age_days: Maximum fork age in days (optional)
        max_forks: Maximum number of forks to analyze
        verbose: Whether to show verbose output
    """
    from forklift.models.filters import PromisingForksFilter

    async with GitHubClient(config.github) as github_client:
        display_service = RepositoryDisplayService(github_client, console)

        try:
            # Create filter object
            filters = PromisingForksFilter(
                min_stars=min_stars,
                min_commits_ahead=min_commits_ahead,
                max_days_since_activity=max_days_since_activity,
                min_activity_score=min_activity_score,
                exclude_archived=not include_archived,
                exclude_disabled=not include_disabled,
                min_fork_age_days=min_fork_age_days,
                max_fork_age_days=max_fork_age_days
            )

            result = await display_service.show_promising_forks(repository_url, filters, max_forks)

            if verbose:
                promising_count = result["promising_forks"]
                total_count = result["total_forks"]
                console.print(f"\n[green]✓ Found {promising_count} promising forks out of {total_count} total forks[/green]")

        except Exception as e:
            logger.error(f"Failed to display promising forks: {e}")
            raise CLIError(f"Failed to display promising forks: {e}")


async def _analyze_fork(
    config: ForkliftConfig,
    fork_url: str,
    branch: str | None,
    max_commits: int,
    include_merge_commits: bool,
    show_commit_details: bool,
    verbose: bool,
    explain: bool = False
) -> None:
    """Analyze a specific fork and branch for features and changes.

    Args:
        config: Forklift configuration
        fork_url: Fork URL to analyze
        branch: Specific branch to analyze (optional)
        max_commits: Maximum commits to analyze
        include_merge_commits: Whether to include merge commits
        show_commit_details: Whether to show detailed commit information
        verbose: Whether to show verbose output
        explain: Whether to generate commit explanations
    """
    from forklift.analysis.interactive_analyzer import InteractiveAnalyzer
    from forklift.models.filters import ForkDetailsFilter

    async with GitHubClient(config.github) as github_client:
        analyzer = InteractiveAnalyzer(github_client, console)

        try:
            # Create filter object for analysis
            filters = ForkDetailsFilter(
                include_branches=True,
                include_contributors=True,
                include_commit_stats=True,
                max_branches=10,
                max_contributors=10
            )

            # Perform the analysis
            analysis_result = await analyzer.analyze_specific_fork(fork_url, branch, filters)

            # Get the fork details and branch analysis
            fork_details = analysis_result["fork_details"]
            branch_analysis = analysis_result.get("branch_analysis")

            # Display comprehensive analysis results
            console.print("\n" + "="*80)
            console.print("[bold blue]Fork Analysis Results[/bold blue]")
            console.print("="*80)

            # Show commit analysis if we have branch analysis
            if branch_analysis and show_commit_details:
                await _display_commit_analysis(
                    github_client, fork_url, branch or fork_details.fork.default_branch,
                    max_commits, include_merge_commits, explain
                )

            # Show feature analysis summary
            _display_feature_analysis_summary(fork_details, branch_analysis)

            if verbose:
                console.print("\n[green]✓ Fork analysis completed successfully[/green]")
                if branch_analysis:
                    commits_analyzed = len(branch_analysis.get("commits", []))
                    console.print(f"[dim]Analyzed {commits_analyzed} commits in branch '{branch or fork_details.fork.default_branch}'[/dim]")

        except Exception as e:
            logger.error(f"Failed to analyze fork: {e}")
            raise CLIError(f"Failed to analyze fork: {e}")


async def _get_parent_repository_url(github_client: GitHubClient, fork_url: str) -> str | None:
    """
    Get the parent repository URL from a fork URL.

    Args:
        github_client: GitHub API client
        fork_url: URL of the fork repository

    Returns:
        Parent repository URL if fork, None if not a fork or error
    """
    try:
        owner, repo_name = validate_repository_url(fork_url)
        
        # Get raw repository data to access parent information
        repo_data = await github_client.get(f"repos/{owner}/{repo_name}")
        
        if repo_data.get("fork") and repo_data.get("parent"):
            return repo_data["parent"]["html_url"]
        elif repo_data.get("fork"):
            # If it's a fork but parent info is not available, try to construct URL
            # This is a fallback - the parent info should normally be available
            logger.warning(f"Fork {owner}/{repo_name} has no parent info available")
            return None
        else:
            # Not a fork, return the same URL as it might be the parent
            return fork_url
            
    except Exception as e:
        logger.debug(f"Could not determine parent repository for {fork_url}: {e}")
        return None


async def _show_commits(
    config: ForkliftConfig,
    fork_url: str,
    branch: str | None,
    limit: int,
    since_date: datetime | None,
    until_date: datetime | None,
    author: str | None,
    include_merge: bool,
    show_files: bool,
    show_stats: bool,
    verbose: bool,
    explain: bool = False,
    ai_summary: bool = False,
    ai_summary_compact: bool = False,
    detail: bool = False,
    force: bool = False,
    disable_cache: bool = False
) -> None:
    """Show detailed commit information for a repository or branch.

    Args:
        config: Forklift configuration
        fork_url: Repository URL to get commits from
        branch: Branch to show commits from (optional)
        limit: Number of commits to display
        since_date: Show commits since this date (optional)
        until_date: Show commits until this date (optional)
        author: Filter commits by author (optional)
        include_merge: Whether to include merge commits
        show_files: Whether to show changed files
        show_stats: Whether to show detailed statistics
        verbose: Whether to show verbose output
        explain: Whether to generate commit explanations
        ai_summary: Whether to generate AI-powered summaries
        ai_summary_compact: Whether to generate compact AI summaries
        detail: Whether to display comprehensive commit information
        force: Whether to force analysis even for forks with no commits ahead
        disable_cache: Whether to disable caching and fetch fresh data
    """
    async with GitHubClient(config.github) as github_client:
        try:
            # Parse repository URL
            owner, repo_name = validate_repository_url(fork_url)

            # Check fork status before expensive operations if using --detail flag
            if detail and not force:
                from forklift.analysis.fork_commit_status_checker import (
                    ForkCommitStatusChecker,
                )
                from forklift.analysis.fork_qualification_lookup import (
                    ForkQualificationLookup,
                )

                # Initialize qualification lookup service
                cache_manager = None
                try:
                    cache_manager = AnalysisCacheManager()
                    await cache_manager.initialize()
                except Exception as e:
                    logger.warning(f"Failed to initialize cache manager for qualification lookup: {e}")

                qualification_lookup = ForkQualificationLookup(
                    github_client, cache_manager
                )

                try:
                    # Try to get parent repository URL from fork URL
                    parent_repo_url = await _get_parent_repository_url(github_client, fork_url)
                    
                    # Look up qualification data for the parent repository
                    qualification_result = None
                    if parent_repo_url:
                        try:
                            qualification_result = await qualification_lookup.get_fork_qualification_data(
                                parent_repo_url, disable_cache
                            )
                            if qualification_result and verbose:
                                console.print(f"[blue]Using fork qualification data from {parent_repo_url}[/blue]")
                        except Exception as e:
                            logger.debug(f"Could not get qualification data: {e}")

                    # Check fork status using qualification data if available
                    status_checker = ForkCommitStatusChecker(github_client)
                    has_commits = await status_checker.has_commits_ahead(fork_url, qualification_result)

                    if has_commits is False:
                        console.print("[yellow]Fork has no commits ahead of upstream - skipping detailed analysis[/yellow]")
                        console.print("[dim]Use --force flag to analyze anyway[/dim]")
                        return
                    elif has_commits is None:
                        if verbose:
                            console.print("[yellow]Could not determine fork commit status - proceeding with analysis[/yellow]")
                    else:
                        if verbose:
                            console.print("[green]Fork has commits ahead - proceeding with detailed analysis[/green]")

                except Exception as e:
                    logger.warning(f"Fork status check failed: {e}")
                    if verbose:
                        console.print(f"[yellow]Fork status check failed - proceeding with analysis: {e}[/yellow]")
                finally:
                    # Clean up cache manager
                    if cache_manager:
                        try:
                            await cache_manager.close()
                        except Exception as e:
                            logger.warning(f"Failed to close cache manager: {e}")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Fetching repository information...", total=None)

                # Get repository to determine default branch if needed
                repo = await github_client.get_repository(owner, repo_name)
                target_branch = branch or repo.default_branch

                progress.update(task, description=f"Fetching commits from branch '{target_branch}'...")

                # Get commits for the specified branch
                if target_branch:
                    commits_data = await github_client.get_branch_commits(
                        owner, repo_name, target_branch, max_count=limit * 2  # Get extra to allow filtering
                    )
                else:
                    commits_data = await github_client.get_repository_commits(
                        owner, repo_name, per_page=limit * 2, since=since_date, until=until_date
                    )

                progress.update(task, description="Processing commits...")

                # Convert to Commit objects and apply filters
                commits = []
                for commit_data in commits_data:
                    try:
                        commit = Commit.from_github_api(commit_data)

                        # Apply filters
                        if not include_merge and commit.is_merge:
                            continue

                        if author and commit.author.login.lower() != author.lower():
                            continue

                        if since_date and commit.date.replace(tzinfo=None) < since_date:
                            continue

                        if until_date and commit.date.replace(tzinfo=None) > until_date:
                            continue

                        commits.append(commit)

                        if len(commits) >= limit:
                            break

                    except Exception as e:
                        logger.warning(f"Failed to parse commit {commit_data.get('sha', 'unknown')}: {e}")

                progress.update(task, description="Complete!")

            # Generate explanations if requested
            if explain and commits:
                await _display_commit_explanations_for_commits(github_client, owner, repo_name, commits)

            # Handle detail mode with comprehensive display
            if detail and commits:
                await _display_detailed_commits(github_client, config, owner, repo_name, commits, repo, disable_cache)
            else:
                # Generate explanations if requested
                if explain and commits:
                    await _display_commit_explanations_for_commits(github_client, owner, repo_name, commits)

                # Generate AI summaries if requested
                if (ai_summary or ai_summary_compact) and commits:
                    await _display_ai_summaries_for_commits(github_client, config, owner, repo_name, commits, disable_cache, compact_mode=ai_summary_compact)

                # Display commits
                _display_commits_table(commits, repo, target_branch, show_files, show_stats)

            if verbose:
                console.print(f"\n[green]✓ Displayed {len(commits)} commits from branch '{target_branch}'[/green]")
                if author:
                    console.print(f"[dim]Filtered by author: {author}[/dim]")
                if since_date or until_date:
                    date_range = f"Date range: {since_date or 'beginning'} to {until_date or 'now'}"
                    console.print(f"[dim]{date_range}[/dim]")

        except Exception as e:
            logger.error(f"Failed to show commits: {e}")
            raise CLIError(f"Failed to show commits: {e}")


async def _display_commit_analysis(
    github_client: GitHubClient,
    fork_url: str,
    branch: str,
    max_commits: int,
    include_merge_commits: bool,
    explain: bool = False
) -> None:
    """Display detailed commit analysis for a branch.

    Args:
        github_client: GitHub API client
        fork_url: Repository URL
        branch: Branch to analyze
        max_commits: Maximum commits to analyze
        include_merge_commits: Whether to include merge commits
        explain: Whether to generate commit explanations
    """
    owner, repo_name = validate_repository_url(fork_url)

    # Get commits for analysis
    commits_data = await github_client.get_branch_commits(
        owner, repo_name, branch, max_count=max_commits
    )

    # Convert to Commit objects and analyze
    commits = []
    commit_types = {}
    total_changes = 0
    authors = set()
    significant_commits = []

    for commit_data in commits_data:
        try:
            commit = Commit.from_github_api(commit_data)

            # Apply merge commit filter
            if not include_merge_commits and commit.is_merge:
                continue

            commits.append(commit)

            # Analyze commit
            commit_type = commit.get_commit_type()
            commit_types[commit_type] = commit_types.get(commit_type, 0) + 1
            total_changes += commit.total_changes
            authors.add(commit.author.login)

            if commit.is_significant():
                significant_commits.append(commit)

        except Exception as e:
            logger.warning(f"Failed to parse commit {commit_data.get('sha', 'unknown')}: {e}")

    # Generate explanations if requested
    if explain and commits:
        await _display_commit_explanations_for_commits(github_client, owner, repo_name, commits[:10])  # Limit to 10 for readability

    # Display analysis results
    console.print(f"\n[bold yellow]Commit Analysis for branch '{branch}'[/bold yellow]")

    # Summary statistics
    stats_table = Table(title="Analysis Summary")
    stats_table.add_column("Metric", style="cyan", width=25)
    stats_table.add_column("Value", style="green", justify="right")

    stats_table.add_row("Total Commits Analyzed", str(len(commits)))
    stats_table.add_row("Significant Commits", str(len(significant_commits)))
    stats_table.add_row("Total Lines Changed", f"{total_changes:,}")
    stats_table.add_row("Unique Authors", str(len(authors)))
    stats_table.add_row("Average Changes/Commit", f"{total_changes // len(commits) if commits else 0:,}")

    console.print(stats_table)

    # Commit types breakdown
    if commit_types:
        types_table = Table(title="Commit Types Distribution")
        types_table.add_column("Type", style="cyan")
        types_table.add_column("Count", style="yellow", justify="right")
        types_table.add_column("Percentage", style="green", justify="right")

        total_commits = len(commits)
        for commit_type, count in sorted(commit_types.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_commits) * 100 if total_commits > 0 else 0
            types_table.add_row(commit_type.title(), str(count), f"{percentage:.1f}%")

        console.print(types_table)

    # Top contributors
    if authors:
        author_commits = {}
        for commit in commits:
            author_commits[commit.author.login] = author_commits.get(commit.author.login, 0) + 1

        contributors_table = Table(title="Top Contributors")
        contributors_table.add_column("Author", style="cyan")
        contributors_table.add_column("Commits", style="yellow", justify="right")
        contributors_table.add_column("Percentage", style="green", justify="right")

        for author, count in sorted(author_commits.items(), key=lambda x: x[1], reverse=True)[:10]:
            percentage = (count / len(commits)) * 100 if commits else 0
            contributors_table.add_row(author, str(count), f"{percentage:.1f}%")

        console.print(contributors_table)

    # Show most significant commits
    if significant_commits:
        console.print(f"\n[bold]SIGNIFICANT - Most Significant Commits (top {min(5, len(significant_commits))})[/bold]")

        # Sort by total changes (descending)
        significant_commits.sort(key=lambda c: c.total_changes, reverse=True)

        for i, commit in enumerate(significant_commits[:5], 1):
            message = commit.message.split("\n")[0]  # First line only
            if len(message) > 60:
                message = message[:57] + "..."

            console.print(f"{i}. [bold]{commit.sha[:7]}[/bold] - {message}")
            console.print(f"   [dim]by {commit.author.login} • {commit.total_changes:,} lines changed • {commit.get_commit_type()}[/dim]")


async def _display_commit_explanations_for_commits(
    github_client: GitHubClient,
    owner: str,
    repo_name: str,
    commits: list
) -> None:
    """Display commit explanations for a list of commits.

    Args:
        github_client: GitHub API client
        owner: Repository owner
        repo_name: Repository name
        commits: List of Commit objects to explain
    """
    from forklift.analysis.commit_explanation_engine import CommitExplanationEngine
    from forklift.analysis.explanation_formatter import ExplanationFormatter
    from forklift.models.analysis import AnalysisContext, CommitWithExplanation
    from forklift.models.github import Repository

    console.print("\n[bold blue]Commit Explanations[/bold blue]")
    console.print("=" * 60)

    try:
        # Create repository and context objects
        repository = Repository(
            owner=owner,
            name=repo_name,
            full_name=f"{owner}/{repo_name}",
            url=f"https://api.github.com/repos/{owner}/{repo_name}",
            html_url=f"https://github.com/{owner}/{repo_name}",
            clone_url=f"https://github.com/{owner}/{repo_name}.git"
        )

        # For non-fork repositories, don't create a Fork object
        # The AnalysisContext now supports None for fork field
        context = AnalysisContext(
            repository=repository,
            fork=None,  # No fork object for original repositories
            project_type="unknown",
            main_language="unknown",
            critical_files=[]
        )

        # Create explanation engine and formatter
        explanation_engine = CommitExplanationEngine()
        formatter = ExplanationFormatter(use_colors=True, use_icons=True, use_simple_tables=True)

        # Generate explanations for commits
        commits_with_explanations = []

        with console.status("[bold green]Generating commit explanations..."):
            for commit in commits:
                try:
                    explanation = explanation_engine.explain_commit(commit, context)
                    commits_with_explanations.append(CommitWithExplanation(
                        commit=commit,
                        explanation=explanation
                    ))
                except Exception as e:
                    logger.warning(f"Failed to explain commit {commit.sha[:8]}: {e}")
                    commits_with_explanations.append(CommitWithExplanation(
                        commit=commit,
                        explanation_error=str(e)
                    ))

        if commits_with_explanations:
            # Display explanations using the formatter
            table = formatter.format_explanation_table(commits_with_explanations)
            if isinstance(table, str):
                # Simple ASCII table
                print(table)
            else:
                # Rich table
                console.print(table)

            successful_explanations = sum(1 for c in commits_with_explanations if c.explanation is not None)
            console.print(f"\n[green]✓ Generated {successful_explanations}/{len(commits)} commit explanations[/green]")
        else:
            console.print("[yellow]No commit explanations were generated[/yellow]")

    except Exception as e:
        logger.error(f"Failed to generate commit explanations: {e}")
        console.print(f"[red]Error generating explanations: {e}[/red]")


async def _display_ai_summaries_for_commits(
    github_client: GitHubClient,
    config: ForkliftConfig,
    owner: str,
    repo_name: str,
    commits: list,
    disable_cache: bool = False,
    compact_mode: bool = False
) -> None:
    """Display AI-powered summaries for a list of commits.

    Args:
        github_client: GitHub API client
        config: Forklift configuration
        owner: Repository owner
        repo_name: Repository name
        commits: List of Commit objects to summarize
        disable_cache: Whether to disable caching and fetch fresh data
        compact_mode: Whether to use compact summary style
    """
    from forklift.ai.client import OpenAIClient
    from forklift.ai.error_handler import OpenAIErrorHandler
    from forklift.ai.summary_engine import AICommitSummaryEngine
    from forklift.models.ai_summary import AISummaryConfig
    from forklift.models.github import Repository

    mode_text = " (Compact Mode)" if compact_mode else ""
    console.print(f"\n[bold blue]AI-Powered Commit Summaries{mode_text}[/bold blue]")
    console.print("=" * 60)

    if disable_cache:
        console.print("[yellow]WARNING: Cache disabled - fetching fresh data from GitHub API[/yellow]")

    try:
        # Check if OpenAI API key is configured
        if not config.openai_api_key:
            console.print("[red]Error: OpenAI API key not configured.[/red]")
            console.print("[yellow]Set the OPENAI_API_KEY environment variable or configure it in your settings.[/yellow]")
            return

        # Create repository object
        repository = Repository(
            owner=owner,
            name=repo_name,
            full_name=f"{owner}/{repo_name}",
            url=f"https://api.github.com/repos/{owner}/{repo_name}",
            html_url=f"https://github.com/{owner}/{repo_name}",
            clone_url=f"https://github.com/{owner}/{repo_name}.git"
        )

        # Initialize AI components with proper async context manager
        ai_config = AISummaryConfig(compact_mode=compact_mode)
        error_handler = OpenAIErrorHandler(max_retries=ai_config.retry_attempts)

        # Use async context manager for OpenAI client
        async with OpenAIClient(api_key=config.openai_api_key, config=ai_config) as openai_client:
            summary_engine = AICommitSummaryEngine(
                openai_client=openai_client,
                config=ai_config,
                error_handler=error_handler
            )

            # Prepare commits with diffs for AI processing
            commits_with_diffs = []

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                console=console
            ) as progress:
                # Fetch diffs for commits
                diff_task = progress.add_task("Fetching commit diffs...", total=len(commits))

                for commit in commits:
                    try:
                        # Get commit diff from GitHub API
                        commit_details = await github_client.get_commit_details(owner, repo_name, commit.sha)
                        diff_text = ""

                        # Extract diff from files
                        if commit_details.get("files"):
                            for file in commit_details["files"]:
                                if file.get("patch"):
                                    diff_text += f"\n--- {file.get('filename', 'unknown')}\n"
                                    diff_text += file["patch"]

                        commits_with_diffs.append((commit, diff_text))

                    except Exception as e:
                        logger.warning(f"Failed to fetch diff for commit {commit.sha[:8]}: {e}")
                        # Add commit with empty diff to still attempt summary
                        commits_with_diffs.append((commit, ""))

                    progress.advance(diff_task)

                # Generate AI summaries
                summary_task_desc = "Generating compact AI summaries..." if compact_mode else "Generating AI summaries..."
                summary_task = progress.add_task(summary_task_desc, total=len(commits_with_diffs))

                def progress_callback(progress_pct: float, completed: int, total: int):
                    progress.update(summary_task, completed=completed)

                summaries = await summary_engine.generate_batch_summaries(
                    commits_with_diffs,
                    repository=repository,
                    progress_callback=progress_callback
                )

            # Detect plain text mode (no Rich formatting support)
            plain_text_mode = (
                os.getenv("NO_COLOR") is not None or
                os.getenv("FORKLIFT_NO_COLOR") is not None or
                os.getenv("FORKLIFT_PLAIN_TEXT") is not None or
                not console.is_terminal
            )

            # Display summaries using the new formatter
            if summaries:
                formatter = AISummaryDisplayFormatter(console)

                # Use compact format if requested, otherwise use detailed format for <= 5 commits
                if compact_mode:
                    formatter.format_ai_summaries_compact(commits, summaries, plain_text=plain_text_mode)
                elif len(commits) <= 5:
                    formatter.format_ai_summaries_detailed(commits, summaries, show_metadata=True)
                else:
                    formatter.format_ai_summaries_compact(commits, summaries, plain_text=plain_text_mode)

                # Show usage statistics with enhanced formatting
                usage_stats = summary_engine.get_usage_stats()
                formatter.display_usage_statistics(usage_stats)
            else:
                if plain_text_mode:
                    print("No AI summaries were generated")
                else:
                    console.print("[yellow]No AI summaries were generated[/yellow]")


    except Exception as e:
        logger.error(f"Failed to generate AI summaries: {e}")
        console.print(f"[red]Error generating AI summaries: {e}[/red]")


async def _display_detailed_commits(
    github_client: GitHubClient,
    config: ForkliftConfig,
    owner: str,
    repo_name: str,
    commits: list[Commit],
    repository,
    disable_cache: bool = False
) -> None:
    """Display commits in detailed view with comprehensive information.

    Args:
        github_client: GitHub API client
        config: Forklift configuration
        owner: Repository owner
        repo_name: Repository name
        commits: List of Commit objects to display
        repository: Repository object
        disable_cache: Whether to disable caching and fetch fresh data
    """
    from forklift.ai.client import OpenAIClient
    from forklift.ai.error_handler import OpenAIErrorHandler
    from forklift.ai.summary_engine import AICommitSummaryEngine
    from forklift.models.ai_summary import AISummaryConfig
    from forklift.models.github import Repository

    console.print("\n[bold blue]DETAILS - Detailed Commit View[/bold blue]")
    console.print("=" * 60)

    if disable_cache:
        console.print("[yellow]WARNING: Cache disabled - fetching fresh data from GitHub API[/yellow]")

    try:
        # Create repository object
        repo_obj = Repository(
            owner=owner,
            name=repo_name,
            full_name=f"{owner}/{repo_name}",
            url=f"https://api.github.com/repos/{owner}/{repo_name}",
            html_url=f"https://github.com/{owner}/{repo_name}",
            clone_url=f"https://github.com/{owner}/{repo_name}.git"
        )

        # Initialize AI components if OpenAI API key is available
        ai_engine = None
        if config.openai_api_key:
            try:
                ai_config = AISummaryConfig()
                error_handler = OpenAIErrorHandler(max_retries=ai_config.retry_attempts)

                # Use async context manager for OpenAI client
                async with OpenAIClient(api_key=config.openai_api_key, config=ai_config) as openai_client:
                    ai_engine = AICommitSummaryEngine(
                        openai_client=openai_client,
                        config=ai_config,
                        error_handler=error_handler
                    )

                    # Create fork status checker for batch operations
                    from forklift.analysis.fork_commit_status_checker import (
                        ForkCommitStatusChecker,
                    )
                    fork_status_checker = ForkCommitStatusChecker(github_client)

                    # Create detailed commit display
                    detailed_display = DetailedCommitDisplay(
                        github_client=github_client,
                        ai_engine=ai_engine,
                        console=console,
                        fork_status_checker=fork_status_checker
                    )

                    # Generate detailed view for all commits
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        MofNCompleteColumn(),
                        console=console
                    ) as progress:
                        task = progress.add_task("Generating detailed commit information...", total=len(commits))

                        def progress_callback(completed: int, total: int):
                            progress.update(task, completed=completed)

                        detailed_commits = await detailed_display.generate_detailed_view(
                            commits, repo_obj, progress_callback, force=force
                        )

                    # Display each detailed commit
                    for i, detailed_commit in enumerate(detailed_commits, 1):
                        console.print(f"\n[bold cyan]Commit {i}/{len(detailed_commits)}[/bold cyan]")
                        detailed_display.format_detailed_commit_view(detailed_commit)

                        # Add spacing between commits (except for the last one)
                        if i < len(detailed_commits):
                            console.print()

                    # Show AI usage statistics if available
                    if ai_engine:
                        usage_stats = ai_engine.get_usage_stats()
                        if usage_stats.total_requests > 0:
                            from forklift.ai.display_formatter import (
                                AISummaryDisplayFormatter,
                            )
                            formatter = AISummaryDisplayFormatter(console)
                            formatter.display_usage_statistics(usage_stats, "Detailed View AI Usage")

            except Exception as e:
                logger.warning(f"Failed to initialize AI engine: {e}")
                console.print(f"[yellow]AI summaries unavailable: {e}[/yellow]")
                # Fall back to detailed display without AI
                ai_engine = None

        # If no AI engine available, create detailed display without AI
        if not ai_engine:
            # Create fork status checker for batch operations
            from forklift.analysis.fork_commit_status_checker import (
                ForkCommitStatusChecker,
            )
            fork_status_checker = ForkCommitStatusChecker(github_client)

            detailed_display = DetailedCommitDisplay(
                github_client=github_client,
                ai_engine=None,
                console=console,
                fork_status_checker=fork_status_checker
            )

            # Generate detailed view without AI summaries
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Generating detailed commit information...", total=len(commits))

                def progress_callback(completed: int, total: int):
                    progress.update(task, completed=completed)

                detailed_commits = await detailed_display.generate_detailed_view(
                    commits, repo_obj, progress_callback, force=force
                )

            # Display each detailed commit
            for i, detailed_commit in enumerate(detailed_commits, 1):
                console.print(f"\n[bold cyan]Commit {i}/{len(detailed_commits)}[/bold cyan]")
                detailed_display.format_detailed_commit_view(detailed_commit)

                # Add spacing between commits (except for the last one)
                if i < len(detailed_commits):
                    console.print()

        console.print(f"\n[green]✓ Displayed {len(commits)} commits in detailed view[/green]")

    except Exception as e:
        logger.error(f"Failed to display detailed commits: {e}")
        console.print(f"[red]Error displaying detailed commits: {e}[/red]")


def _display_feature_analysis_summary(fork_details, branch_analysis: dict | None) -> None:
    """Display feature analysis summary.

    Args:
        fork_details: Fork details object
        branch_analysis: Branch analysis results (optional)
    """
    console.print("\n[bold green]ANALYSIS - Feature Analysis Summary[/bold green]")

    fork = fork_details.fork

    # Repository overview
    overview_table = Table(title="Repository Overview")
    overview_table.add_column("Property", style="cyan", width=20)
    overview_table.add_column("Value", style="green")

    overview_table.add_row("Repository", fork.full_name)
    overview_table.add_row("Stars", f"{fork.stars:,}")
    overview_table.add_row("Language", fork.language or "Not specified")
    overview_table.add_row("Total Branches", str(len(fork_details.branches)))
    overview_table.add_row("Contributors", str(fork_details.contributor_count))
    overview_table.add_row("Last Updated", _format_datetime_simple(fork.updated_at))

    console.print(overview_table)

    # Branch activity summary
    if fork_details.branches:
        active_branches = [b for b in fork_details.branches if b.commits_ahead_of_main > 0]

        branch_table = Table(title="Branch Activity")
        branch_table.add_column("Metric", style="cyan", width=25)
        branch_table.add_column("Value", style="yellow", justify="right")

        branch_table.add_row("Total Branches", str(len(fork_details.branches)))
        branch_table.add_row("Branches Ahead of Main", str(len(active_branches)))
        branch_table.add_row("Total Commits", f"{fork_details.total_commits:,}")

        if active_branches:
            max_ahead = max(b.commits_ahead_of_main for b in active_branches)
            branch_table.add_row("Max Commits Ahead", str(max_ahead))

        console.print(branch_table)

    # Analysis insights
    insights = []

    if fork.stars > 10:
        insights.append("[POPULAR] Popular fork with significant community interest")

    if fork_details.contributor_count > 5:
        insights.append("[COLLABORATIVE] Active collaboration with multiple contributors")

    if branch_analysis:
        commits = branch_analysis.get("commits", [])
        if len(commits) > 20:
            insights.append("[ACTIVE] High development activity with many commits")

        commit_types = branch_analysis.get("commit_types", {})
        if commit_types.get("feature", 0) > commit_types.get("fix", 0):
            insights.append("[FEATURES] Feature-focused development")
        elif commit_types.get("fix", 0) > 0:
            insights.append("[BUGFIXES] Bug-fix focused development")

    if len(fork_details.branches) > 5:
        insights.append("[BRANCHES] Multiple development branches indicating active work")

    if insights:
        console.print("\n[bold blue]INSIGHTS - Key Insights[/bold blue]")
        for insight in insights:
            console.print(f"  • {insight}")


def _display_commits_table(
    commits: list,
    repo,
    branch: str,
    show_files: bool,
    show_stats: bool
) -> None:
    """Display commits in a formatted table.

    Args:
        commits: List of Commit objects
        repo: Repository object
        branch: Branch name
        show_files: Whether to show changed files
        show_stats: Whether to show detailed statistics
    """
    if not commits:
        console.print("[yellow]No commits found matching the criteria.[/yellow]")
        return

    # Header
    console.print(f"\n[bold blue]Commits from {repo.full_name} (branch: {branch})[/bold blue]")
    console.print(f"[dim]Showing {len(commits)} commits[/dim]")

    # Main commits table
    table = Table(title="Commit History")
    table.add_column("SHA", style="dim", width=8)
    table.add_column("Message", style="white", min_width=40)
    table.add_column("Author", style="cyan", width=15)
    table.add_column("Date", style="magenta", width=12)
    table.add_column("Type", style="yellow", width=10)
    table.add_column("Changes", style="green", justify="right", width=10)

    for commit in commits:
        # Truncate long commit messages
        message = commit.message.split("\n")[0]  # First line only
        if len(message) > 60:
            message = message[:57] + "..."

        # Format changes
        if commit.total_changes > 0:
            changes = f"+{commit.additions}/-{commit.deletions}"
        else:
            changes = "N/A"

        # Add row with color coding for commit types
        commit_type = commit.get_commit_type()
        type_color = {
            "feature": "[green]feat[/green]",
            "fix": "[red]fix[/red]",
            "docs": "[blue]docs[/blue]",
            "test": "[yellow]test[/yellow]",
            "refactor": "[purple]refactor[/purple]",
            "merge": "[dim]merge[/dim]"
        }.get(commit_type, commit_type)

        table.add_row(
            commit.sha[:7],
            message,
            commit.author.login,
            _format_datetime_simple(commit.date),
            type_color,
            changes
        )

    console.print(table)

    # Show detailed statistics if requested
    if show_stats:
        _display_commit_statistics(commits)

    # Show file changes for recent commits if requested
    if show_files:
        _display_file_changes(commits[:5])  # Show files for top 5 commits


def _display_commit_statistics(commits: list) -> None:
    """Display detailed commit statistics.

    Args:
        commits: List of Commit objects
    """
    if not commits:
        return

    # Calculate statistics
    total_additions = sum(c.additions for c in commits)
    total_deletions = sum(c.deletions for c in commits)
    total_changes = sum(c.total_changes for c in commits)

    authors = {}
    commit_types = {}
    files_changed = set()

    for commit in commits:
        # Author statistics
        author = commit.author.login
        if author not in authors:
            authors[author] = {"commits": 0, "additions": 0, "deletions": 0}
        authors[author]["commits"] += 1
        authors[author]["additions"] += commit.additions
        authors[author]["deletions"] += commit.deletions

        # Commit type statistics
        commit_type = commit.get_commit_type()
        commit_types[commit_type] = commit_types.get(commit_type, 0) + 1

        # Files changed
        files_changed.update(commit.files_changed)

    # Display statistics
    console.print("\n[bold yellow]Detailed Statistics[/bold yellow]")

    # Overall stats
    stats_table = Table(title="Overall Statistics")
    stats_table.add_column("Metric", style="cyan", width=25)
    stats_table.add_column("Value", style="green", justify="right")

    stats_table.add_row("Total Commits", str(len(commits)))
    stats_table.add_row("Total Lines Added", f"{total_additions:,}")
    stats_table.add_row("Total Lines Deleted", f"{total_deletions:,}")
    stats_table.add_row("Net Lines Changed", f"{total_additions - total_deletions:+,}")
    stats_table.add_row("Files Modified", f"{len(files_changed):,}")
    stats_table.add_row("Unique Authors", str(len(authors)))

    if commits:
        avg_changes = total_changes // len(commits)
        stats_table.add_row("Avg Changes/Commit", f"{avg_changes:,}")

    console.print(stats_table)

    # Author breakdown (top 10)
    if len(authors) > 1:
        author_table = Table(title="Top Contributors")
        author_table.add_column("Author", style="cyan")
        author_table.add_column("Commits", style="yellow", justify="right")
        author_table.add_column("Lines Added", style="green", justify="right")
        author_table.add_column("Lines Deleted", style="red", justify="right")

        sorted_authors = sorted(authors.items(), key=lambda x: x[1]["commits"], reverse=True)
        for author, stats in sorted_authors[:10]:
            author_table.add_row(
                author,
                str(stats["commits"]),
                f"{stats['additions']:,}",
                f"{stats['deletions']:,}"
            )

        console.print(author_table)


def _display_file_changes(commits: list) -> None:
    """Display file changes for recent commits.

    Args:
        commits: List of recent Commit objects
    """
    if not commits:
        return

    console.print(f"\n[bold blue]FILES - File Changes (Recent {len(commits)} commits)[/bold blue]")

    for i, commit in enumerate(commits, 1):
        if not commit.files_changed:
            continue

        # Commit header
        message = commit.message.split("\n")[0]
        if len(message) > 50:
            message = message[:47] + "..."

        console.print(f"\n{i}. [bold]{commit.sha[:7]}[/bold] - {message}")
        console.print(f"   [dim]by {commit.author.login} • {len(commit.files_changed)} files changed[/dim]")

        # Show files (limit to 10 per commit)
        files_to_show = commit.files_changed[:10]
        for file_path in files_to_show:
            # Color code by file type
            if file_path.endswith((".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs")):
                file_color = "[green]"
            elif file_path.endswith((".md", ".txt", ".rst", ".doc")):
                file_color = "[blue]"
            elif file_path.endswith((".json", ".yaml", ".yml", ".xml", ".toml")):
                file_color = "[yellow]"
            elif file_path.endswith((".test.py", ".spec.js", ".test.ts")):
                file_color = "[purple]"
            else:
                file_color = "[white]"

            console.print(f"     {file_color}{file_path}[/{file_color.strip('[')}]")

        if len(commit.files_changed) > 10:
            remaining = len(commit.files_changed) - 10
            console.print(f"     [dim]... and {remaining} more files[/dim]")


def _format_datetime_simple(dt: datetime | None) -> str:
    """Format datetime for simple display.

    Args:
        dt: Datetime to format

    Returns:
        Formatted datetime string
    """
    if not dt:
        return "Unknown"

    # Remove timezone info for calculation
    dt_naive = dt.replace(tzinfo=None)
    now = datetime.utcnow()

    # Calculate days ago
    days_ago = (now - dt_naive).days

    if days_ago == 0:
        return "Today"
    elif days_ago == 1:
        return "Yesterday"
    elif days_ago < 7:
        return f"{days_ago}d ago"
    elif days_ago < 30:
        weeks = days_ago // 7
        return f"{weeks}w ago"
    elif days_ago < 365:
        months = days_ago // 30
        return f"{months}mo ago"
    else:
        return dt_naive.strftime("%Y-%m-%d")


async def _show_fork_details(
    config: ForkliftConfig,
    fork_url: str,
    max_branches: int,
    max_contributors: int,
    include_branches: bool,
    include_contributors: bool,
    include_commit_stats: bool,
    verbose: bool
) -> None:
    """Show fork details using the interactive analyzer.

    Args:
        config: Forklift configuration
        fork_url: Fork URL to analyze
        max_branches: Maximum branches to display
        max_contributors: Maximum contributors to display
        include_branches: Whether to include branch information
        include_contributors: Whether to include contributor information
        include_commit_stats: Whether to include commit statistics
        verbose: Whether to show verbose output
    """
    from forklift.analysis.interactive_analyzer import InteractiveAnalyzer
    from forklift.models.filters import ForkDetailsFilter

    async with GitHubClient(config.github) as github_client:
        analyzer = InteractiveAnalyzer(github_client, console)

        try:
            # Create filter object
            filters = ForkDetailsFilter(
                include_branches=include_branches,
                include_contributors=include_contributors,
                include_commit_stats=include_commit_stats,
                max_branches=max_branches,
                max_contributors=max_contributors
            )

            fork_details = await analyzer.show_fork_details(fork_url, filters)

            if verbose:
                console.print("\n[green]✓ Fork details displayed successfully[/green]")
                console.print(f"[dim]Branches: {len(fork_details.branches)}, Contributors: {fork_details.contributor_count}[/dim]")

        except Exception as e:
            logger.error(f"Failed to display fork details: {e}")
            raise CLIError(f"Failed to display fork details: {e}")


def _display_comprehensive_fork_data(qualification_result, verbose: bool) -> None:
    """Display comprehensive fork data in a user-friendly format.

    Args:
        qualification_result: QualifiedForksResult containing all fork data
        verbose: Whether to show verbose output
    """

    # Display summary statistics
    stats = qualification_result.stats
    console.print(f"\n[bold blue]Fork Data Summary for {qualification_result.repository_owner}/{qualification_result.repository_name}[/bold blue]")
    console.print("=" * 80)

    summary_table = Table(title="Collection Summary")
    summary_table.add_column("Metric", style="cyan", width=25)
    summary_table.add_column("Count", style="green", justify="right", width=10)
    summary_table.add_column("Percentage", style="yellow", justify="right", width=12)

    total = stats.total_forks_discovered
    summary_table.add_row("Total Forks", str(total), "100.0%")
    summary_table.add_row("Need Analysis", str(stats.forks_with_commits), f"{stats.analysis_candidate_percentage:.1f}%")
    summary_table.add_row("Can Skip", str(stats.forks_with_no_commits), f"{stats.skip_rate_percentage:.1f}%")
    summary_table.add_row("Archived", str(stats.archived_forks), f"{(stats.archived_forks/total*100) if total > 0 else 0:.1f}%")
    summary_table.add_row("Disabled", str(stats.disabled_forks), f"{(stats.disabled_forks/total*100) if total > 0 else 0:.1f}%")

    console.print(summary_table)

    # Display detailed fork data table
    if qualification_result.collected_forks:
        console.print("\n[bold blue]Detailed Fork Information[/bold blue]")
        console.print("=" * 80)

        fork_table = Table(title=f"All Forks ({len(qualification_result.collected_forks)} total)")
        fork_table.add_column("#", style="dim", width=4)
        fork_table.add_column("Fork Name", style="cyan", min_width=20)
        fork_table.add_column("Owner", style="blue", min_width=15)
        fork_table.add_column("Stars", style="yellow", justify="right", width=6)
        fork_table.add_column("Forks", style="green", justify="right", width=6)
        fork_table.add_column("Language", style="white", width=12)
        fork_table.add_column("Commits Status", style="magenta", width=15)
        fork_table.add_column("Activity", style="orange3", width=20)
        fork_table.add_column("Status", style="red", width=10)

        # Sort forks by stars and activity
        sorted_forks = sorted(
            qualification_result.collected_forks,
            key=lambda x: (x.metrics.stargazers_count, -x.metrics.days_since_last_push),
            reverse=True
        )

        for i, fork_data in enumerate(sorted_forks[:50], 1):  # Show first 50
            metrics = fork_data.metrics

            # Style status indicators
            status_parts = []
            if metrics.archived:
                status_parts.append("[red]Archived[/red]")
            if metrics.disabled:
                status_parts.append("[red]Disabled[/red]")
            if not status_parts:
                status_parts.append("[green]Active[/green]")

            status_display = " ".join(status_parts)

            fork_table.add_row(
                str(i),
                metrics.name,
                metrics.owner,
                str(metrics.stargazers_count),
                str(metrics.forks_count),
                metrics.language or "N/A",
                metrics.commits_ahead_status,
                fork_data.activity_summary,
                status_display
            )

        console.print(fork_table)

        if len(qualification_result.collected_forks) > 50:
            remaining = len(qualification_result.collected_forks) - 50
            console.print(f"[dim]... and {remaining} more forks (use --interactive to explore all)[/dim]")

    # Show efficiency metrics if verbose
    if verbose:
        console.print(f"\n[green]✓ Data collection completed in {stats.processing_time_seconds:.2f} seconds[/green]")
        console.print(f"[blue]API Efficiency: {stats.efficiency_percentage:.1f}% calls saved[/blue]")


async def _interactive_fork_selection(qualification_result, config: ForkliftConfig, verbose: bool) -> None:
    """Interactive mode for selecting and analyzing specific forks.

    Args:
        qualification_result: QualifiedForksResult containing all fork data
        config: Forklift configuration
        verbose: Whether to show verbose output
    """
    from rich.prompt import Confirm


    console.print("\n[bold green]Interactive Fork Selection Mode[/bold green]")
    console.print("=" * 60)

    # Get forks that need analysis (exclude those with no commits)
    analysis_candidates = qualification_result.forks_needing_analysis

    if not analysis_candidates:
        console.print("[yellow]No forks need detailed analysis (all have no commits ahead).[/yellow]")
        return

    console.print(f"Found {len(analysis_candidates)} forks that could benefit from detailed analysis.")
    console.print("These forks have commits ahead of the main repository.\n")

    while True:
        console.print("[bold]Available Actions:[/bold]")
        console.print("1. View analysis candidates")
        console.print("2. Select forks for analysis")
        console.print("3. View fork details")
        console.print("4. Analyze selected forks")
        console.print("5. Exit interactive mode")

        try:
            choice = IntPrompt.ask(
                "\n[cyan]Choose an action (1-5)[/cyan]",
                default=1,
                choices=[1, 2, 3, 4, 5]
            )
        except KeyboardInterrupt:
            console.print("\n[yellow]Exiting interactive mode...[/yellow]")
            break

        if choice == 1:
            # View analysis candidates
            _display_analysis_candidates(analysis_candidates)

        elif choice == 2:
            # Select forks for analysis
            selected_forks = _select_forks_for_analysis(analysis_candidates)
            if selected_forks:
                console.print(f"\n[green]Selected {len(selected_forks)} forks for analysis.[/green]")

                # Ask if user wants to proceed with analysis
                if Confirm.ask("Proceed with analysis of selected forks?", default=True):
                    await _analyze_selected_forks(selected_forks, config, verbose)

        elif choice == 3:
            # View fork details
            _view_fork_details(analysis_candidates)

        elif choice == 4:
            # Analyze all candidates
            if Confirm.ask(f"Analyze all {len(analysis_candidates)} candidate forks?", default=False):
                await _analyze_selected_forks(analysis_candidates, config, verbose)

        elif choice == 5:
            # Exit
            console.print("\n[yellow]Exiting interactive mode...[/yellow]")
            break

        # Ask if user wants to continue
        if choice != 5:
            console.print()  # Add spacing
            if not Confirm.ask("[dim]Continue with interactive mode?[/dim]", default=True):
                break


def _display_analysis_candidates(candidates) -> None:
    """Display analysis candidate forks in a table."""
    console.print(f"\n[bold blue]Analysis Candidates ({len(candidates)} forks)[/bold blue]")

    table = Table(title="Forks with Commits Ahead")
    table.add_column("#", style="dim", width=4)
    table.add_column("Fork Name", style="cyan", min_width=20)
    table.add_column("Owner", style="blue", min_width=15)
    table.add_column("Stars", style="yellow", justify="right", width=6)
    table.add_column("Language", style="white", width=12)
    table.add_column("Activity", style="green", width=20)
    table.add_column("Description", style="dim", width=30)

    for i, fork_data in enumerate(candidates, 1):
        metrics = fork_data.metrics
        description = metrics.description or "No description"
        if len(description) > 27:
            description = description[:27] + "..."

        table.add_row(
            str(i),
            metrics.name,
            metrics.owner,
            str(metrics.stargazers_count),
            metrics.language or "N/A",
            fork_data.activity_summary,
            description
        )

    console.print(table)


def _select_forks_for_analysis(candidates) -> list:
    """Allow user to select specific forks for analysis."""
    from rich.prompt import Prompt

    console.print(f"\n[cyan]Select forks for analysis (1-{len(candidates)})[/cyan]")
    console.print("Enter fork numbers separated by commas (e.g., '1,3,5') or ranges (e.g., '1-5')")
    console.print("Enter 'all' to select all candidates, or 'none' to cancel")

    try:
        selection = Prompt.ask("Selection", default="none")

        if selection.lower() == "none":
            return []
        elif selection.lower() == "all":
            return candidates

        selected_indices = []

        # Parse selection
        for part in selection.split(","):
            part = part.strip()
            if "-" in part:
                # Range selection
                start, end = map(int, part.split("-"))
                selected_indices.extend(range(start, end + 1))
            else:
                # Individual selection
                selected_indices.append(int(part))

        # Convert to fork objects
        selected_forks = []
        for idx in selected_indices:
            if 1 <= idx <= len(candidates):
                selected_forks.append(candidates[idx - 1])

        return selected_forks

    except (ValueError, IndexError) as e:
        console.print(f"[red]Invalid selection: {e}[/red]")
        return []


def _view_fork_details(candidates) -> None:
    """Display detailed information about a specific fork."""

    try:
        fork_num = IntPrompt.ask(
            f"Enter fork number to view details (1-{len(candidates)})",
            default=1
        )

        if 1 <= fork_num <= len(candidates):
            fork_data = candidates[fork_num - 1]
            metrics = fork_data.metrics

            # Display detailed fork information
            console.print(f"\n[bold blue]Fork Details: {metrics.full_name}[/bold blue]")

            details_table = Table(title=f"Details for {metrics.name}")
            details_table.add_column("Property", style="cyan", width=20)
            details_table.add_column("Value", style="green")

            details_table.add_row("Full Name", metrics.full_name)
            details_table.add_row("Owner", metrics.owner)
            details_table.add_row("Description", metrics.description or "No description")
            details_table.add_row("Language", metrics.language or "Not specified")
            details_table.add_row("Stars", str(metrics.stargazers_count))
            details_table.add_row("Forks", str(metrics.forks_count))
            details_table.add_row("Watchers", str(metrics.watchers_count))
            details_table.add_row("Open Issues", str(metrics.open_issues_count))
            details_table.add_row("Size (KB)", str(metrics.size))
            details_table.add_row("License", metrics.license_name or "No license")
            details_table.add_row("Topics", ", ".join(metrics.topics) if metrics.topics else "None")
            details_table.add_row("Created", metrics.created_at.strftime("%Y-%m-%d"))
            details_table.add_row("Last Updated", metrics.updated_at.strftime("%Y-%m-%d"))
            details_table.add_row("Last Push", metrics.pushed_at.strftime("%Y-%m-%d"))
            details_table.add_row("Days Since Push", str(metrics.days_since_last_push))
            details_table.add_row("Activity Status", fork_data.activity_summary)
            details_table.add_row("Commits Status", metrics.commits_ahead_status)
            details_table.add_row("Archived", "Yes" if metrics.archived else "No")
            details_table.add_row("Disabled", "Yes" if metrics.disabled else "No")
            details_table.add_row("Homepage", metrics.homepage or "None")
            details_table.add_row("URL", metrics.html_url)

            console.print(details_table)
        else:
            console.print("[red]Invalid fork number![/red]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")


async def _analyze_selected_forks(selected_forks, config: ForkliftConfig, verbose: bool) -> None:
    """Analyze the selected forks."""
    console.print(f"\n[bold green]Analyzing {len(selected_forks)} selected forks...[/bold green]")

    # This is a placeholder for actual fork analysis
    # In a real implementation, this would use the RepositoryAnalyzer
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Analyzing forks...", total=len(selected_forks))

        for i, fork_data in enumerate(selected_forks):
            metrics = fork_data.metrics
            progress.update(
                task,
                advance=1,
                description=f"Analyzing {metrics.name} ({i+1}/{len(selected_forks)})"
            )

            # Simulate analysis time
            import asyncio
            await asyncio.sleep(0.5)

    console.print(f"\n[green]✓ Analysis completed for {len(selected_forks)} forks![/green]")
    console.print("[dim]Note: This is a demonstration. Full analysis integration coming soon.[/dim]")


if __name__ == "__main__":
    cli()
