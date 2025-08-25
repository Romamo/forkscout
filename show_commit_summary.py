#!/usr/bin/env python3
"""
Script to show detailed commit summaries with file changes and statistics.
"""

import asyncio
import sys
from datetime import datetime
from forklift.github.client import GitHubClient
from forklift.config.settings import load_config
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

async def show_commit_summary(repo_url: str, limit: int = 5):
    """Show detailed commit summary with file changes."""
    
    # Parse repository URL
    if repo_url.startswith('https://github.com/'):
        repo_path = repo_url.replace('https://github.com/', '')
    else:
        repo_path = repo_url
    
    owner, repo_name = repo_path.split('/')
    
    config = load_config()
    
    async with GitHubClient(config.github) as client:
        console.print(f"[blue]Fetching detailed commit information for {owner}/{repo_name}...[/blue]")
        
        # Get basic commit list first
        commits = await client.get_repository_commits(owner, repo_name, per_page=limit)
        
        console.print(f"\n[green]SUMMARY - Detailed Commit Summary ({len(commits)} commits)[/green]")
        console.print("=" * 80)
        
        for i, commit in enumerate(commits, 1):
            # Get detailed information for each commit
            try:
                detailed_commit = await client.get_commit(owner, repo_name, commit.sha)
                
                # Create summary panel for each commit
                commit_info = []
                commit_info.append(f"[bold]SHA:[/bold] {detailed_commit.sha[:12]}")
                commit_info.append(f"[bold]Author:[/bold] {detailed_commit.author.login}")
                commit_info.append(f"[bold]Date:[/bold] {detailed_commit.date.strftime('%Y-%m-%d %H:%M:%S')}")
                commit_info.append(f"[bold]Type:[/bold] {detailed_commit.get_commit_type()}")
                
                # File changes summary
                if detailed_commit.files_changed:
                    commit_info.append(f"[bold]Files Changed:[/bold] {len(detailed_commit.files_changed)}")
                    commit_info.append(f"[bold]Lines Added:[/bold] +{detailed_commit.additions}")
                    commit_info.append(f"[bold]Lines Deleted:[/bold] -{detailed_commit.deletions}")
                    commit_info.append(f"[bold]Total Changes:[/bold] {detailed_commit.total_changes}")
                    
                    # Show first few files
                    files_to_show = detailed_commit.files_changed[:5]
                    if files_to_show:
                        commit_info.append(f"[bold]Modified Files:[/bold]")
                        for file in files_to_show:
                            commit_info.append(f"  • {file}")
                        if len(detailed_commit.files_changed) > 5:
                            commit_info.append(f"  ... and {len(detailed_commit.files_changed) - 5} more files")
                else:
                    commit_info.append("[yellow]No file change information available[/yellow]")
                
                # Truncate long commit messages
                message = detailed_commit.message.split('\n')[0]
                if len(message) > 60:
                    message = message[:57] + "..."
                
                panel = Panel(
                    "\n".join(commit_info),
                    title=f"Commit {i}: {message}",
                    border_style="blue" if detailed_commit.is_significant() else "dim"
                )
                
                console.print(panel)
                console.print()
                
            except Exception as e:
                console.print(f"[red]Error getting details for commit {commit.sha[:12]}: {e}[/red]")
        
        # Summary statistics
        total_additions = sum(c.additions for c in commits if hasattr(c, 'additions'))
        total_deletions = sum(c.deletions for c in commits if hasattr(c, 'deletions'))
        
        summary_table = Table(title="Summary Statistics")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green")
        
        summary_table.add_row("Total Commits Analyzed", str(len(commits)))
        summary_table.add_row("Total Lines Added", f"+{total_additions:,}")
        summary_table.add_row("Total Lines Deleted", f"-{total_deletions:,}")
        summary_table.add_row("Net Change", f"{total_additions - total_deletions:+,}")
        
        console.print(summary_table)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("[red]Usage: python show_commit_summary.py <repository_url> [limit][/red]")
        console.print("[dim]Example: python show_commit_summary.py https://github.com/owner/repo 5[/dim]")
        sys.exit(1)
    
    repo_url = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    asyncio.run(show_commit_summary(repo_url, limit))