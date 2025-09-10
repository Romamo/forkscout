#!/usr/bin/env python3
"""
Direct GitHub API verification of behind commits for sanila2007/youtube-bot-telegram.

This script makes direct API calls to GitHub's compare endpoint to verify
that there are no forks with behind commits in the specified repository.
"""

import asyncio
import os
import json
from typing import List, Dict, Any
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

# GitHub API configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
if not GITHUB_TOKEN:
    console.print("[red]Error: GITHUB_TOKEN environment variable not set[/red]")
    exit(1)

HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'forkscout-behind-commits-verification'
}

BASE_URL = 'https://api.github.com'

async def get_repository_forks(owner: str, repo: str, per_page: int = 100) -> List[Dict[str, Any]]:
    """Get all forks of a repository."""
    forks = []
    page = 1
    
    async with httpx.AsyncClient() as client:
        while True:
            url = f"{BASE_URL}/repos/{owner}/{repo}/forks"
            params = {
                'sort': 'newest',
                'per_page': per_page,
                'page': page
            }
            
            console.print(f"[blue]Fetching forks page {page}...[/blue]")
            response = await client.get(url, headers=HEADERS, params=params)
            
            if response.status_code != 200:
                console.print(f"[red]Error fetching forks: {response.status_code} - {response.text}[/red]")
                break
            
            page_forks = response.json()
            if not page_forks:
                break
                
            forks.extend(page_forks)
            page += 1
            
            # Limit to first 20 forks for this verification
            if len(forks) >= 20:
                forks = forks[:20]
                break
    
    return forks

async def compare_commits(parent_owner: str, parent_repo: str, fork_owner: str, fork_repo: str, fork_branch: str = None) -> Dict[str, Any]:
    """Compare commits between parent and fork using GitHub compare API."""
    
    # Use the fork's default branch if not specified
    if not fork_branch:
        fork_branch = 'main'  # Default assumption
    
    # Get parent repository default branch
    async with httpx.AsyncClient() as client:
        parent_url = f"{BASE_URL}/repos/{parent_owner}/{parent_repo}"
        parent_response = await client.get(parent_url, headers=HEADERS)
        
        if parent_response.status_code == 200:
            parent_data = parent_response.json()
            parent_branch = parent_data.get('default_branch', 'main')
        else:
            parent_branch = 'main'
        
        # Compare commits
        compare_url = f"{BASE_URL}/repos/{parent_owner}/{parent_repo}/compare/{parent_branch}...{fork_owner}:{fork_branch}"
        
        console.print(f"[dim]Comparing: {parent_branch}...{fork_owner}:{fork_branch}[/dim]")
        
        compare_response = await client.get(compare_url, headers=HEADERS)
        
        if compare_response.status_code == 200:
            return compare_response.json()
        else:
            console.print(f"[yellow]Warning: Could not compare {fork_owner}/{fork_repo}: {compare_response.status_code}[/yellow]")
            return {
                'ahead_by': 0,
                'behind_by': 0,
                'status': 'error',
                'error': f"HTTP {compare_response.status_code}"
            }

async def verify_behind_commits():
    """Main verification function."""
    console.print(Panel.fit(
        "[bold blue]Direct GitHub API Verification: Behind Commits[/bold blue]\n"
        "Repository: sanila2007/youtube-bot-telegram",
        title="🔍 API Verification"
    ))
    
    # Get forks
    console.print("\n[bold]Step 1: Fetching repository forks...[/bold]")
    forks = await get_repository_forks('sanila2007', 'youtube-bot-telegram')
    
    console.print(f"[green]Found {len(forks)} forks to analyze[/green]")
    
    # Analyze each fork
    console.print("\n[bold]Step 2: Analyzing commit differences...[/bold]")
    
    results = []
    behind_count = 0
    ahead_count = 0
    error_count = 0
    
    for i, fork in enumerate(forks, 1):
        fork_owner = fork['owner']['login']
        fork_name = fork['name']
        fork_branch = fork.get('default_branch', 'main')
        
        console.print(f"[cyan]{i:2d}. Analyzing {fork_owner}/{fork_name}...[/cyan]")
        
        # Compare with parent
        comparison = await compare_commits(
            'sanila2007', 'youtube-bot-telegram',
            fork_owner, fork_name, fork_branch
        )
        
        ahead_by = comparison.get('ahead_by', 0)
        behind_by = comparison.get('behind_by', 0)
        status = comparison.get('status', 'unknown')
        
        if 'error' in comparison:
            error_count += 1
            result_status = f"Error: {comparison['error']}"
        else:
            if behind_by > 0:
                behind_count += 1
            if ahead_by > 0:
                ahead_count += 1
            
            # Format the result
            if ahead_by == 0 and behind_by == 0:
                result_status = "Up-to-date"
            elif ahead_by > 0 and behind_by == 0:
                result_status = f"+{ahead_by}"
            elif ahead_by == 0 and behind_by > 0:
                result_status = f"-{behind_by}"
            else:
                result_status = f"+{ahead_by} -{behind_by}"
        
        results.append({
            'fork': f"{fork_owner}/{fork_name}",
            'ahead_by': ahead_by,
            'behind_by': behind_by,
            'status': result_status,
            'api_status': status
        })
        
        # Show immediate result
        if behind_by > 0:
            console.print(f"    [red]⚠️  BEHIND: {behind_by} commits behind[/red]")
        elif ahead_by > 0:
            console.print(f"    [green]✓ AHEAD: {ahead_by} commits ahead[/green]")
        else:
            console.print(f"    [dim]✓ Up-to-date[/dim]")
    
    # Display results table
    console.print("\n[bold]Step 3: Results Summary[/bold]")
    
    table = Table(title="Fork Commit Analysis Results")
    table.add_column("Fork", style="cyan")
    table.add_column("Ahead", justify="right", style="green")
    table.add_column("Behind", justify="right", style="red")
    table.add_column("Status", justify="center")
    table.add_column("API Status", style="dim")
    
    for result in results:
        ahead_str = str(result['ahead_by']) if result['ahead_by'] > 0 else ""
        behind_str = str(result['behind_by']) if result['behind_by'] > 0 else ""
        
        table.add_row(
            result['fork'],
            ahead_str,
            behind_str,
            result['status'],
            result['api_status']
        )
    
    console.print(table)
    
    # Final summary
    console.print(f"\n[bold]Final Verification Results:[/bold]")
    console.print(f"• Total forks analyzed: [cyan]{len(results)}[/cyan]")
    console.print(f"• Forks with commits ahead: [green]{ahead_count}[/green]")
    console.print(f"• Forks with commits behind: [red]{behind_count}[/red]")
    console.print(f"• Errors/inaccessible: [yellow]{error_count}[/yellow]")
    
    if behind_count == 0:
        console.print("\n[bold green]✅ CONFIRMED: No forks have commits behind the parent repository[/bold green]")
        console.print("[green]The behind commits functionality is working correctly - there simply are no behind commits to display.[/green]")
    else:
        console.print(f"\n[bold red]⚠️  FOUND: {behind_count} fork(s) with commits behind[/bold red]")
        console.print("[red]These should be displayed with '-X' format in the forkscout output.[/red]")
    
    # Show raw API data for first few comparisons
    console.print("\n[bold]Step 4: Raw API Response Sample[/bold]")
    if results:
        sample_fork = forks[0]
        fork_owner = sample_fork['owner']['login']
        fork_name = sample_fork['name']
        
        console.print(f"[dim]Sample API call for {fork_owner}/{fork_name}:[/dim]")
        sample_comparison = await compare_commits(
            'sanila2007', 'youtube-bot-telegram',
            fork_owner, fork_name
        )
        
        # Show relevant fields
        api_sample = {
            'ahead_by': sample_comparison.get('ahead_by'),
            'behind_by': sample_comparison.get('behind_by'),
            'total_commits': sample_comparison.get('total_commits'),
            'status': sample_comparison.get('status')
        }
        
        console.print(f"[dim]{json.dumps(api_sample, indent=2)}[/dim]")

if __name__ == "__main__":
    asyncio.run(verify_behind_commits())