# Example of how to integrate detailed commit fetching into existing CLI

# In cli.py, modify the show-commits command:

@cli.command("show-commits")
@click.argument("fork_url")
@click.option("--branch", "-b", help="Branch to show commits from")
@click.option("--limit", "-l", type=click.IntRange(1, 200), default=20)
@click.option("--show-files", is_flag=True, help="Show changed files for each commit")
@click.option("--show-stats", is_flag=True, help="Show detailed statistics")
@click.option("--detailed", is_flag=True, help="Fetch detailed commit information (slower)")  # NEW FLAG
@click.option("--explain", is_flag=True, help="Generate explanations for each commit")
@click.pass_context
def show_commits(
    ctx: click.Context,
    fork_url: str,
    branch: str | None,
    limit: int,
    show_files: bool,
    show_stats: bool,
    detailed: bool,  # NEW PARAMETER
    explain: bool
) -> None:
    """Display detailed commit information for a repository or specific branch."""
    
    # Pass the detailed flag to the implementation
    asyncio.run(_show_commits(
        config, fork_url, branch, limit, None, None, None, 
        False, show_files, show_stats, verbose, explain, detailed  # NEW PARAMETER
    ))

# In the _show_commits implementation:

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
    detailed: bool = False  # NEW PARAMETER
) -> None:
    """Show detailed commit information for a repository or branch."""
    
    async with GitHubClient(config.github) as github_client:
        owner, repo_name = validate_repository_url(fork_url)
        
        if detailed:
            # Use the detailed approach (like my script)
            console.print("[yellow]Fetching detailed commit information (this may take longer)...[/yellow]")
            
            # Get basic commits first
            basic_commits = await github_client.get_repository_commits(
                owner, repo_name, per_page=limit
            )
            
            # Then get detailed info for each
            detailed_commits = []
            with Progress() as progress:
                task = progress.add_task("Fetching commit details...", total=len(basic_commits))
                
                for commit in basic_commits:
                    detailed_commit = await github_client.get_commit(owner, repo_name, commit.sha)
                    detailed_commits.append(detailed_commit)
                    progress.advance(task)
            
            # Display with full information
            _display_detailed_commits(detailed_commits, show_files, show_stats)
            
        else:
            # Use the existing fast approach
            # ... existing implementation
            pass

def _display_detailed_commits(commits: list[Commit], show_files: bool, show_stats: bool):
    """Display commits with full file change information."""
    
    table = Table(title="Detailed Commit History")
    table.add_column("SHA", style="cyan", width=12)
    table.add_column("Message", style="white", min_width=30)
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
        
        # Format changes
        changes = f"+{commit.additions}/-{commit.deletions}" if commit.total_changes > 0 else "N/A"
        
        table.add_row(
            commit.sha[:8],
            message,
            commit.author.login,
            commit.date.strftime("%Y-%m-%d"),
            commit.get_commit_type(),
            str(len(commit.files_changed)),
            changes
        )
    
    console.print(table)
    
    if show_files:
        console.print("\n[bold blue]📁 File Changes[/bold blue]")
        for i, commit in enumerate(commits[:5], 1):  # Show files for first 5 commits
            if commit.files_changed:
                console.print(f"\n{i}. [bold]{commit.sha[:8]}[/bold] - {commit.message.split()[0]}")
                for file in commit.files_changed[:10]:  # Show first 10 files
                    console.print(f"   • {file}")
                if len(commit.files_changed) > 10:
                    console.print(f"   ... and {len(commit.files_changed) - 10} more files")
    
    if show_stats:
        # Display summary statistics
        total_additions = sum(c.additions for c in commits)
        total_deletions = sum(c.deletions for c in commits)
        total_files = sum(len(c.files_changed) for c in commits)
        
        stats_table = Table(title="Summary Statistics")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="green")
        
        stats_table.add_row("Total Commits", str(len(commits)))
        stats_table.add_row("Total Files Changed", str(total_files))
        stats_table.add_row("Total Lines Added", f"+{total_additions:,}")
        stats_table.add_row("Total Lines Deleted", f"-{total_deletions:,}")
        stats_table.add_row("Net Change", f"{total_additions - total_deletions:+,}")
        
        console.print(stats_table)