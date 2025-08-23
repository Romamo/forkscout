# Technical Specification: Enhanced show-commits Command

## Architecture Overview

### Current Flow (Broken)
```
User runs: forklift show-commits repo --show-files --show-stats
    ↓
CLI calls: github_client.get_branch_commits() 
    ↓  
Returns: Basic commit data (no files, no stats)
    ↓
Display: Empty file changes, zero statistics
```

### New Flow (Fixed)
```
User runs: forklift show-commits repo --show-files --show-stats
    ↓
CLI detects: Detailed data needed (show_files=True OR show_stats=True)
    ↓
CLI calls: github_client.get_repository_commits() [basic list]
    ↓
CLI calls: github_client.get_commit(sha) for each commit [detailed data]
    ↓
Display: Real file changes, real statistics
```

## Code Changes Required

### 1. GitHub Client Enhancement

**File**: `src/forklift/github/client.py`

```python
async def get_detailed_commits_batch(
    self,
    owner: str,
    repo: str, 
    commit_shas: list[str],
    progress_callback: callable = None
) -> list[Commit]:
    """
    Fetch detailed commit information for multiple commits efficiently.
    
    Args:
        owner: Repository owner
        repo: Repository name  
        commit_shas: List of commit SHA hashes
        progress_callback: Optional callback for progress updates
        
    Returns:
        List of detailed Commit objects with file changes and statistics
        
    Raises:
        GitHubAPIError: If API calls fail
        GitHubRateLimitError: If rate limit exceeded
    """
    detailed_commits = []
    
    for i, sha in enumerate(commit_shas):
        try:
            # Use existing get_commit method for detailed info
            detailed_commit = await self.get_commit(owner, repo, sha)
            detailed_commits.append(detailed_commit)
            
            # Progress callback for UI updates
            if progress_callback:
                progress_callback(i + 1, len(commit_shas))
                
        except GitHubAPIError as e:
            logger.warning(f"Failed to fetch detailed commit {sha}: {e}")
            # Continue with other commits, don't fail entire operation
            continue
            
    return detailed_commits
```

### 2. CLI Logic Enhancement

**File**: `src/forklift/cli.py`

```python
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
    explain: bool = False
) -> None:
    """Enhanced commit display with conditional detailed fetching."""
    
    async with GitHubClient(config.github) as github_client:
        owner, repo_name = validate_repository_url(fork_url)
        
        # Determine if we need detailed commit information
        needs_detailed_info = show_files or show_stats or explain
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn() if needs_detailed_info else None,
            TaskProgressColumn() if needs_detailed_info else None,
            console=console
        ) as progress:
            
            # Step 1: Get repository info
            task1 = progress.add_task("Fetching repository information...", total=None)
            repo = await github_client.get_repository(owner, repo_name)
            target_branch = branch or repo.default_branch
            progress.update(task1, completed=True)
            
            # Step 2: Get basic commit list
            task2 = progress.add_task(f"Fetching commits from '{target_branch}'...", total=None)
            basic_commits = await github_client.get_repository_commits(
                owner, repo_name, 
                sha=target_branch,
                per_page=limit,
                since=since_date.isoformat() if since_date else None,
                until=until_date.isoformat() if until_date else None,
                author=author
            )
            progress.update(task2, completed=True)
            
            # Apply filters to basic commits
            filtered_commits = _apply_commit_filters(
                basic_commits, include_merge, author, since_date, until_date, limit
            )
            
            if needs_detailed_info:
                # Step 3: Get detailed information
                if len(filtered_commits) > 10:
                    console.print(f"[yellow]Warning: Fetching detailed info for {len(filtered_commits)} commits requires {len(filtered_commits)} API calls.[/yellow]")
                
                task3 = progress.add_task("Fetching detailed commit information...", total=len(filtered_commits))
                
                def progress_callback(current, total):
                    progress.update(task3, completed=current)
                
                commit_shas = [c.sha for c in filtered_commits]
                detailed_commits = await github_client.get_detailed_commits_batch(
                    owner, repo_name, commit_shas, progress_callback
                )
                
                # Display with detailed information
                _display_detailed_commits(detailed_commits, show_files, show_stats, explain)
                
            else:
                # Fast path: display basic information only
                _display_basic_commits(filtered_commits)

def _apply_commit_filters(
    commits: list[Commit],
    include_merge: bool,
    author: str | None,
    since_date: datetime | None,
    until_date: datetime | None,
    limit: int
) -> list[Commit]:
    """Apply filters to commit list."""
    filtered = []
    
    for commit in commits:
        # Skip merge commits if not requested
        if not include_merge and commit.is_merge:
            continue
            
        # Filter by author
        if author and commit.author.login.lower() != author.lower():
            continue
            
        # Filter by date range
        commit_date = commit.date.replace(tzinfo=None)
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
    explain: bool
) -> None:
    """Display commits with full detailed information."""
    
    # Main commit table with detailed data
    table = Table(title=f"Detailed Commit History ({len(commits)} commits)")
    table.add_column("SHA", style="cyan", width=10)
    table.add_column("Message", style="white", min_width=30, max_width=50)
    table.add_column("Author", style="blue", width=15)
    table.add_column("Date", style="magenta", width=12)
    table.add_column("Type", style="yellow", width=10)
    table.add_column("Files", style="green", justify="right", width=6)
    table.add_column("Changes", style="green", justify="right", width=12)
    
    for commit in commits:
        # Format message
        message = commit.message.split('\n')[0]
        if len(message) > 45:
            message = message[:42] + "..."
            
        # Format changes with real data
        if commit.total_changes > 0:
            changes = f"+{commit.additions}/-{commit.deletions}"
        else:
            changes = "0"
            
        # Color code by significance
        if commit.is_significant():
            style = "bold"
        else:
            style = "dim"
            
        table.add_row(
            commit.sha[:8],
            message,
            commit.author.login,
            commit.date.strftime("%Y-%m-%d"),
            commit.get_commit_type(),
            str(len(commit.files_changed)),
            changes,
            style=style
        )
    
    console.print(table)
    
    # Show file changes if requested
    if show_files:
        _display_file_changes_detailed(commits)
    
    # Show statistics if requested  
    if show_stats:
        _display_statistics_detailed(commits)
        
    # Show explanations if requested
    if explain:
        _display_commit_explanations(commits)

def _display_file_changes_detailed(commits: list[Commit]) -> None:
    """Display actual file changes from detailed commit data."""
    console.print(f"\n[bold blue]📁 File Changes (Recent {min(5, len(commits))} commits)[/bold blue]")
    
    for i, commit in enumerate(commits[:5], 1):
        if not commit.files_changed:
            continue
            
        # Commit header
        message = commit.message.split('\n')[0]
        if len(message) > 60:
            message = message[:57] + "..."
            
        console.print(f"\n{i}. [bold]{commit.sha[:8]}[/bold] - {message}")
        console.print(f"   [dim]by {commit.author.login} • {len(commit.files_changed)} files • +{commit.additions}/-{commit.deletions} lines[/dim]")
        
        # Show files (limit to 10 per commit for readability)
        files_to_show = commit.files_changed[:10]
        for file_path in files_to_show:
            # Color code by file type
            if file_path.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c')):
                file_style = "bright_green"
            elif file_path.endswith(('.md', '.txt', '.rst')):
                file_style = "bright_blue"  
            elif file_path.endswith(('.json', '.yaml', '.yml', '.xml')):
                file_style = "bright_yellow"
            else:
                file_style = "white"
                
            console.print(f"   • [{file_style}]{file_path}[/{file_style}]")
            
        # Show truncation message if needed
        if len(commit.files_changed) > 10:
            remaining = len(commit.files_changed) - 10
            console.print(f"   [dim]... and {remaining} more file{'s' if remaining != 1 else ''}[/dim]")

def _display_statistics_detailed(commits: list[Commit]) -> None:
    """Display real statistics from detailed commit data."""
    
    # Calculate aggregate statistics
    total_additions = sum(c.additions for c in commits)
    total_deletions = sum(c.deletions for c in commits)
    total_changes = sum(c.total_changes for c in commits)
    
    # Collect unique files and authors
    all_files = set()
    authors = {}
    commit_types = {}
    
    for commit in commits:
        all_files.update(commit.files_changed)
        
        # Author statistics
        author = commit.author.login
        if author not in authors:
            authors[author] = {'commits': 0, 'additions': 0, 'deletions': 0}
        authors[author]['commits'] += 1
        authors[author]['additions'] += commit.additions
        authors[author]['deletions'] += commit.deletions
        
        # Commit type statistics
        commit_type = commit.get_commit_type()
        commit_types[commit_type] = commit_types.get(commit_type, 0) + 1
    
    # Overall statistics table
    stats_table = Table(title="Overall Statistics")
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="green")
    
    stats_table.add_row("Total Commits", str(len(commits)))
    stats_table.add_row("Total Lines Added", f"+{total_additions:,}")
    stats_table.add_row("Total Lines Deleted", f"-{total_deletions:,}")
    stats_table.add_row("Net Lines Changed", f"{total_additions - total_deletions:+,}")
    stats_table.add_row("Files Modified", f"{len(all_files):,}")
    stats_table.add_row("Unique Authors", str(len(authors)))
    
    if commits:
        avg_changes = total_changes // len(commits)
        stats_table.add_row("Avg Changes/Commit", f"{avg_changes:,}")
    
    console.print(f"\n{stats_table}")
    
    # Top contributors table
    if len(authors) > 1:
        contributors_table = Table(title="Top Contributors")
        contributors_table.add_column("Author", style="blue")
        contributors_table.add_column("Commits", style="green", justify="right")
        contributors_table.add_column("Lines Added", style="green", justify="right")
        contributors_table.add_column("Lines Deleted", style="red", justify="right")
        
        # Sort by total contributions
        sorted_authors = sorted(
            authors.items(), 
            key=lambda x: x[1]['commits'] + x[1]['additions'] + x[1]['deletions'], 
            reverse=True
        )
        
        for author, stats in sorted_authors[:5]:  # Top 5 contributors
            contributors_table.add_row(
                author,
                str(stats['commits']),
                f"+{stats['additions']:,}",
                f"-{stats['deletions']:,}"
            )
        
        console.print(f"\n{contributors_table}")
    
    # Commit types breakdown
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
        
        console.print(f"\n{types_table}")

def _display_basic_commits(commits: list[Commit]) -> None:
    """Display commits with basic information only (fast path)."""
    
    table = Table(title=f"Commit History ({len(commits)} commits)")
    table.add_column("SHA", style="cyan", width=10)
    table.add_column("Message", style="white", min_width=40)
    table.add_column("Author", style="blue", width=15)
    table.add_column("Date", style="magenta", width=12)
    table.add_column("Type", style="yellow", width=10)
    
    for commit in commits:
        message = commit.message.split('\n')[0]
        if len(message) > 55:
            message = message[:52] + "..."
            
        table.add_row(
            commit.sha[:8],
            message,
            commit.author.login,
            commit.date.strftime("%Y-%m-%d"),
            commit.get_commit_type()
        )
    
    console.print(table)
    console.print(f"\n[dim]Use --show-files or --show-stats for detailed information[/dim]")
```

## Testing Strategy

### Unit Tests
```python
# tests/test_show_commits_enhanced.py

@pytest.mark.asyncio
async def test_show_commits_with_files():
    """Test that --show-files actually shows files."""
    # Mock detailed commit data with files
    # Verify files are displayed in output

@pytest.mark.asyncio  
async def test_show_commits_with_stats():
    """Test that --show-stats shows real statistics."""
    # Mock commits with line changes
    # Verify statistics are calculated correctly

@pytest.mark.asyncio
async def test_show_commits_performance_warning():
    """Test performance warning for large requests."""
    # Test with limit > 10
    # Verify warning is shown

@pytest.mark.asyncio
async def test_show_commits_basic_fast_path():
    """Test that basic usage remains fast."""
    # Test without detailed flags
    # Verify only basic API calls are made
```

### Integration Tests
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_show_commits_real_repository():
    """Test with real GitHub repository."""
    # Test against known repository
    # Verify real file changes are shown

@pytest.mark.integration  
@pytest.mark.asyncio
async def test_show_commits_rate_limiting():
    """Test rate limiting handling."""
    # Test with many commits
    # Verify graceful rate limit handling
```

This technical specification provides the detailed implementation needed to fix the broken `show-commits` command and deliver the promised functionality.