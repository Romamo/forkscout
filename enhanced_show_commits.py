"""
Enhanced show-commits implementation that actually delivers promised functionality.

This file contains the fixed implementation that should replace the current
_show_commits function in src/forklift/cli.py
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.prompt import Confirm

from forklift.config.settings import ForkliftConfig
from forklift.github.client import GitHubClient
from forklift.models.github import Commit

logger = logging.getLogger(__name__)
console = Console()


async def _show_commits_enhanced(
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
    explain: bool = False
) -> None:
    """Enhanced commit display with conditional detailed fetching.
    
    This implementation fixes the core issues:
    1. Actually shows files when --show-files is used
    2. Actually shows statistics when --show-stats is used  
    3. Uses detailed API calls only when needed
    4. Provides clear progress indication for slow operations
    """
    
    async with GitHubClient(config.github) as github_client:
        try:
            # Parse repository URL
            owner, repo_name = validate_repository_url(fork_url)
            
            # Determine if we need detailed commit information
            needs_detailed_info = show_files or show_stats or explain
            
            # Create progress columns based on whether we need detailed info
            progress_columns = [
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}")
            ]
            
            if needs_detailed_info:
                progress_columns.extend([
                    BarColumn(),
                    TaskProgressColumn()
                ])
            
            with Progress(*progress_columns, console=console) as progress:
                
                # Step 1: Get repository info
                task1 = progress.add_task("Fetching repository information...", total=None)
                repo = await github_client.get_repository(owner, repo_name)
                target_branch = branch or repo.default_branch
                progress.update(task1, completed=True, description="Repository information retrieved")
                
                # Step 2: Get basic commit list
                task2 = progress.add_task(f"Fetching commits from '{target_branch}'...", total=None)
                
                # Build parameters for commit query
                since_str = since_date.isoformat() if since_date else None
                until_str = until_date.isoformat() if until_date else None
                
                basic_commits = await github_client.get_repository_commits(
                    owner, repo_name,
                    sha=target_branch,
                    per_page=min(limit * 2, 100),  # Get extra to allow for filtering
                    since=since_str,
                    until=until_str,
                    author=author
                )
                
                progress.update(task2, completed=True, description=f"Retrieved {len(basic_commits)} commits")
                
                # Apply filters to basic commits
                filtered_commits = _apply_commit_filters(
                    basic_commits, include_merge, author, since_date, until_date, limit
                )
                
                if verbose:
                    console.print(f"[dim]Filtered to {len(filtered_commits)} commits after applying filters[/dim]")
                
                if needs_detailed_info:
                    # Warn user about performance impact
                    if len(filtered_commits) > 10:
                        console.print(f"[yellow]⚠️  Fetching detailed info for {len(filtered_commits)} commits requires {len(filtered_commits)} API calls.[/yellow]")
                        console.print(f"[yellow]   This may take {len(filtered_commits) * 0.5:.1f}-{len(filtered_commits) * 1:.1f} seconds and use {len(filtered_commits)} API requests.[/yellow]")
                        
                        if not Confirm.ask("Continue with detailed analysis?", default=True):
                            console.print("[yellow]Falling back to basic commit display...[/yellow]")
                            needs_detailed_info = False
                
                if needs_detailed_info:
                    # Step 3: Get detailed information for each commit
                    task3 = progress.add_task("Fetching detailed commit information...", total=len(filtered_commits))
                    
                    detailed_commits = []
                    for i, commit in enumerate(filtered_commits):
                        try:
                            # Get detailed commit info (includes files and stats)
                            detailed_commit = await github_client.get_commit(owner, repo_name, commit.sha)
                            detailed_commits.append(detailed_commit)
                            
                            progress.update(task3, advance=1, 
                                          description=f"Fetching commit details... ({i+1}/{len(filtered_commits)})")
                            
                        except Exception as e:
                            logger.warning(f"Failed to fetch detailed info for commit {commit.sha}: {e}")
                            # Use basic commit data as fallback
                            detailed_commits.append(commit)
                            progress.update(task3, advance=1)
                    
                    progress.update(task3, completed=True, description="Detailed commit information retrieved")
                    
                    # Display with detailed information
                    _display_detailed_commits(detailed_commits, show_files, show_stats, explain, verbose)
                    
                else:
                    # Fast path: display basic information only
                    _display_basic_commits(filtered_commits, verbose)
                    
        except Exception as e:
            logger.error(f"Failed to show commits: {e}")
            console.print(f"[red]Error: {e}[/red]")
            raise


def _apply_commit_filters(
    commits: list[Commit],
    include_merge: bool,
    author: str | None,
    since_date: datetime | None,
    until_date: datetime | None,
    limit: int
) -> list[Commit]:
    """Apply filters to commit list and return filtered results."""
    filtered = []
    
    for commit in commits:
        # Skip merge commits if not requested
        if not include_merge and commit.is_merge:
            continue
            
        # Filter by author (case-insensitive)
        if author and commit.author.login.lower() != author.lower():
            continue
            
        # Filter by date range
        commit_date = commit.date.replace(tzinfo=None) if commit.date.tzinfo else commit.date
        if since_date and commit_date < since_date:
            continue
        if until_date and commit_date > until_date:
            continue
            
        filtered.append(commit)
        
        # Respect limit
        if len(filtered) >= limit:
            break
            
    return filtered


def _display_detailed_commits(
    commits: list[Commit], 
    show_files: bool, 
    show_stats: bool,
    explain: bool,
    verbose: bool
) -> None:
    """Display commits with full detailed information."""
    
    if not commits:
        console.print("[yellow]No commits found matching the criteria.[/yellow]")
        return
    
    console.print(f"\n[bold blue]Detailed Commit Analysis ({len(commits)} commits)[/bold blue]")
    
    # Main commit table with detailed data
    table = Table(title="Commit History with File Changes")
    table.add_column("SHA", style="cyan", width=10)
    table.add_column("Message", style="white", min_width=25, max_width=45)
    table.add_column("Author", style="blue", width=15)
    table.add_column("Date", style="magenta", width=12)
    table.add_column("Type", style="yellow", width=10)
    table.add_column("Files", style="green", justify="right", width=6)
    table.add_column("Changes", style="green", justify="right", width=12)
    
    for commit in commits:
        # Format message
        message = commit.message.split('\n')[0]
        if len(message) > 40:
            message = message[:37] + "..."
            
        # Format changes with real data
        if hasattr(commit, 'total_changes') and commit.total_changes > 0:
            changes = f"+{commit.additions}/-{commit.deletions}"
            changes_style = "green" if commit.additions > commit.deletions else "red" if commit.deletions > commit.additions else "yellow"
        else:
            changes = "N/A"
            changes_style = "dim"
            
        # Color code by significance
        row_style = "bold" if commit.is_significant() else None
            
        table.add_row(
            commit.sha[:8],
            message,
            commit.author.login,
            commit.date.strftime("%m-%d"),
            commit.get_commit_type(),
            str(len(commit.files_changed)) if hasattr(commit, 'files_changed') else "N/A",
            f"[{changes_style}]{changes}[/{changes_style}]",
            style=row_style
        )
    
    console.print(table)
    
    # Show file changes if requested
    if show_files:
        _display_file_changes_detailed(commits)
    
    # Show statistics if requested  
    if show_stats:
        _display_statistics_detailed(commits)
        
    # Show explanations if requested (placeholder for now)
    if explain:
        console.print(f"\n[yellow]💡 Commit explanations feature coming soon...[/yellow]")


def _display_file_changes_detailed(commits: list[Commit]) -> None:
    """Display actual file changes from detailed commit data."""
    
    commits_with_files = [c for c in commits if hasattr(c, 'files_changed') and c.files_changed]
    
    if not commits_with_files:
        console.print(f"\n[yellow]📁 No file changes available (commits may not have detailed data)[/yellow]")
        return
    
    console.print(f"\n[bold blue]📁 File Changes (Recent {min(5, len(commits_with_files))} commits)[/bold blue]")
    
    for i, commit in enumerate(commits_with_files[:5], 1):
        # Commit header
        message = commit.message.split('\n')[0]
        if len(message) > 60:
            message = message[:57] + "..."
            
        console.print(f"\n{i}. [bold]{commit.sha[:8]}[/bold] - {message}")
        
        # Commit metadata
        file_count = len(commit.files_changed)
        additions = getattr(commit, 'additions', 0)
        deletions = getattr(commit, 'deletions', 0)
        
        console.print(f"   [dim]by {commit.author.login} • {file_count} file{'s' if file_count != 1 else ''} • +{additions}/-{deletions} lines[/dim]")
        
        # Show files (limit to 10 per commit for readability)
        files_to_show = commit.files_changed[:10]
        for file_path in files_to_show:
            # Color code by file type
            if file_path.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs')):
                file_style = "bright_green"
            elif file_path.endswith(('.md', '.txt', '.rst', '.doc')):
                file_style = "bright_blue"  
            elif file_path.endswith(('.json', '.yaml', '.yml', '.xml', '.toml')):
                file_style = "bright_yellow"
            elif file_path.endswith(('.css', '.scss', '.less', '.html')):
                file_style = "bright_magenta"
            else:
                file_style = "white"
                
            console.print(f"   • [{file_style}]{file_path}[/{file_style}]")
            
        # Show truncation message if needed
        if len(commit.files_changed) > 10:
            remaining = len(commit.files_changed) - 10
            console.print(f"   [dim]... and {remaining} more file{'s' if remaining != 1 else ''}[/dim]")


def _display_statistics_detailed(commits: list[Commit]) -> None:
    """Display real statistics from detailed commit data."""
    
    # Filter commits that have detailed statistics
    commits_with_stats = [c for c in commits if hasattr(c, 'additions') and hasattr(c, 'deletions')]
    
    if not commits_with_stats:
        console.print(f"\n[yellow]📊 No detailed statistics available (commits may not have detailed data)[/yellow]")
        return
    
    # Calculate aggregate statistics
    total_additions = sum(getattr(c, 'additions', 0) for c in commits_with_stats)
    total_deletions = sum(getattr(c, 'deletions', 0) for c in commits_with_stats)
    total_changes = sum(getattr(c, 'total_changes', 0) for c in commits_with_stats)
    
    # Collect unique files and authors
    all_files = set()
    authors = {}
    commit_types = {}
    
    for commit in commits_with_stats:
        if hasattr(commit, 'files_changed'):
            all_files.update(commit.files_changed)
        
        # Author statistics
        author = commit.author.login
        if author not in authors:
            authors[author] = {'commits': 0, 'additions': 0, 'deletions': 0}
        authors[author]['commits'] += 1
        authors[author]['additions'] += getattr(commit, 'additions', 0)
        authors[author]['deletions'] += getattr(commit, 'deletions', 0)
        
        # Commit type statistics
        commit_type = commit.get_commit_type()
        commit_types[commit_type] = commit_types.get(commit_type, 0) + 1
    
    # Overall statistics table
    console.print(f"\n[bold blue]📊 Detailed Statistics[/bold blue]")
    
    stats_table = Table(title="Overall Statistics")
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="green")
    
    stats_table.add_row("Total Commits Analyzed", str(len(commits_with_stats)))
    stats_table.add_row("Total Lines Added", f"+{total_additions:,}")
    stats_table.add_row("Total Lines Deleted", f"-{total_deletions:,}")
    stats_table.add_row("Net Lines Changed", f"{total_additions - total_deletions:+,}")
    stats_table.add_row("Files Modified", f"{len(all_files):,}")
    stats_table.add_row("Unique Authors", str(len(authors)))
    
    if commits_with_stats:
        avg_changes = total_changes // len(commits_with_stats) if total_changes > 0 else 0
        stats_table.add_row("Avg Changes/Commit", f"{avg_changes:,}")
    
    console.print(stats_table)
    
    # Top contributors table (if multiple authors)
    if len(authors) > 1:
        contributors_table = Table(title="Top Contributors")
        contributors_table.add_column("Author", style="blue")
        contributors_table.add_column("Commits", style="green", justify="right")
        contributors_table.add_column("Lines Added", style="green", justify="right")
        contributors_table.add_column("Lines Deleted", style="red", justify="right")
        
        # Sort by total contributions (commits + changes)
        sorted_authors = sorted(
            authors.items(), 
            key=lambda x: x[1]['commits'] * 10 + x[1]['additions'] + x[1]['deletions'], 
            reverse=True
        )
        
        for author, stats in sorted_authors[:5]:  # Top 5 contributors
            contributors_table.add_row(
                author,
                str(stats['commits']),
                f"+{stats['additions']:,}",
                f"-{stats['deletions']:,}"
            )
        
        console.print(contributors_table)
    
    # Commit types breakdown (if multiple types)
    if len(commit_types) > 1:
        types_table = Table(title="Commit Types")
        types_table.add_column("Type", style="yellow")
        types_table.add_column("Count", style="green", justify="right")
        types_table.add_column("Percentage", style="blue", justify="right")
        
        sorted_types = sorted(commit_types.items(), key=lambda x: x[1], reverse=True)
        
        for commit_type, count in sorted_types:
            percentage = (count / len(commits)) * 100
            types_table.add_row(
                commit_type.title(),
                str(count),
                f"{percentage:.1f}%"
            )
        
        console.print(types_table)


def _display_basic_commits(commits: list[Commit], verbose: bool) -> None:
    """Display commits with basic information only (fast path)."""
    
    if not commits:
        console.print("[yellow]No commits found matching the criteria.[/yellow]")
        return
    
    console.print(f"\n[bold blue]Commit History ({len(commits)} commits)[/bold blue]")
    
    table = Table(title="Basic Commit Information")
    table.add_column("SHA", style="cyan", width=10)
    table.add_column("Message", style="white", min_width=40)
    table.add_column("Author", style="blue", width=15)
    table.add_column("Date", style="magenta", width=12)
    table.add_column("Type", style="yellow", width=10)
    
    for commit in commits:
        message = commit.message.split('\n')[0]
        if len(message) > 50:
            message = message[:47] + "..."
            
        table.add_row(
            commit.sha[:8],
            message,
            commit.author.login,
            commit.date.strftime("%Y-%m-%d"),
            commit.get_commit_type()
        )
    
    console.print(table)
    
    # Helpful hint for users
    console.print(f"\n[dim]💡 Use --show-files or --show-stats for detailed commit analysis[/dim]")
    if verbose:
        console.print(f"[dim]   This fast mode used 1 API call. Detailed mode would use {len(commits) + 1} API calls.[/dim]")


def validate_repository_url(url: str) -> tuple[str, str]:
    """Validate and parse GitHub repository URL - placeholder implementation."""
    # This should match the existing implementation in cli.py
    import re
    
    patterns = [
        r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
        r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$",
        r"^([^/]+)/([^/]+)$"
    ]
    
    for pattern in patterns:
        match = re.match(pattern, url.strip())
        if match:
            owner, repo = match.groups()
            return owner, repo
    
    raise ValueError(f"Invalid GitHub repository URL: {url}")


# Example usage and testing
if __name__ == "__main__":
    import sys
    from forklift.config.settings import load_config
    
    async def test_enhanced_show_commits():
        """Test the enhanced show-commits functionality."""
        if len(sys.argv) < 2:
            print("Usage: python enhanced_show_commits.py <repo_url> [--show-files] [--show-stats]")
            return
        
        repo_url = sys.argv[1]
        show_files = "--show-files" in sys.argv
        show_stats = "--show-stats" in sys.argv
        
        config = load_config()
        
        await _show_commits_enhanced(
            config=config,
            fork_url=repo_url,
            branch=None,
            limit=5,
            since_date=None,
            until_date=None,
            author=None,
            include_merge=True,
            show_files=show_files,
            show_stats=show_stats,
            verbose=True,
            explain=False
        )
    
    asyncio.run(test_enhanced_show_commits())