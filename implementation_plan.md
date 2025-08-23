# Implementation Plan: Fix show-commits Command

## Overview
Fix the `forklift show-commits` command to deliver on its promised functionality by implementing detailed commit fetching when needed.

## Current Problems
1. `--show-files` flag exists but shows no files
2. `--show-stats` flag exists but shows no statistics  
3. `--explain` only works on forks, fails on main repositories
4. Uses basic API calls that don't include file changes or line statistics
5. Command promises features it cannot deliver

## Implementation Strategy

### Phase 1: Core Infrastructure Changes

#### 1.1 Modify GitHub Client
**File**: `src/forklift/github/client.py`

Add method to fetch detailed commits in batch:
```python
async def get_detailed_commits(
    self, 
    owner: str, 
    repo: str, 
    commit_shas: list[str],
    show_progress: bool = True
) -> list[Commit]:
    """Fetch detailed commit information for multiple commits."""
    detailed_commits = []
    
    if show_progress:
        # Use progress bar for multiple API calls
        pass
    
    for sha in commit_shas:
        detailed_commit = await self.get_commit(owner, repo, sha)
        detailed_commits.append(detailed_commit)
    
    return detailed_commits
```

#### 1.2 Update CLI Command Logic
**File**: `src/forklift/cli.py`

Modify `_show_commits` function to:
- Detect when detailed calls are needed
- Use appropriate API endpoints
- Handle progress indication for slow operations

### Phase 2: Feature Implementation

#### 2.1 Fix File Changes Display
**Current**: Shows empty "📁 File Changes" section
**Target**: Show actual files modified in each commit

```python
def _display_file_changes(commits: list[Commit]) -> None:
    """Display actual file changes from detailed commit data."""
    for i, commit in enumerate(commits[:5], 1):
        if commit.files_changed:
            console.print(f"\n{i}. [bold]{commit.sha[:7]}[/bold] - {commit.message.split('\n')[0][:50]}")
            console.print(f"   [dim]{len(commit.files_changed)} files changed • +{commit.additions}/-{commit.deletions}[/dim]")
            
            # Show files (limit to 10 per commit)
            for file in commit.files_changed[:10]:
                console.print(f"   • {file}")
            
            if len(commit.files_changed) > 10:
                console.print(f"   ... and {len(commit.files_changed) - 10} more files")
```

#### 2.2 Fix Statistics Display
**Current**: Shows zeros for all statistics
**Target**: Show real line counts and change metrics

```python
def _display_commit_statistics(commits: list[Commit]) -> None:
    """Display real statistics from detailed commit data."""
    total_additions = sum(c.additions for c in commits)
    total_deletions = sum(c.deletions for c in commits)
    total_changes = sum(c.total_changes for c in commits)
    files_changed = set()
    
    for commit in commits:
        files_changed.update(commit.files_changed)
    
    # Display with real data
    stats_table = Table(title="Commit Statistics")
    stats_table.add_row("Total Lines Added", f"+{total_additions:,}")
    stats_table.add_row("Total Lines Deleted", f"-{total_deletions:,}")
    stats_table.add_row("Net Change", f"{total_additions - total_deletions:+,}")
    stats_table.add_row("Files Modified", f"{len(files_changed):,}")
    stats_table.add_row("Avg Changes/Commit", f"{total_changes // len(commits) if commits else 0:,}")
```

#### 2.3 Fix Explanations for Main Repositories
**Current**: Only works on forks
**Target**: Work on any repository

Remove fork validation from explanation system or make it optional.

### Phase 3: Performance Optimization

#### 3.1 Smart API Usage
```python
async def _show_commits_optimized(
    # ... parameters
    show_files: bool,
    show_stats: bool,
    explain: bool
) -> None:
    """Optimized commit display with smart API usage."""
    
    # Determine if detailed calls are needed
    needs_detailed = show_files or show_stats or explain
    
    if needs_detailed:
        console.print("[yellow]Fetching detailed commit information (this may take longer)...[/yellow]")
        
        # Get basic commits first (fast)
        basic_commits = await github_client.get_repository_commits(
            owner, repo_name, per_page=limit
        )
        
        # Then get detailed info (slower)
        commit_shas = [c.sha for c in basic_commits]
        detailed_commits = await github_client.get_detailed_commits(
            owner, repo_name, commit_shas, show_progress=True
        )
        
        # Display with full information
        _display_detailed_commits(detailed_commits, show_files, show_stats)
        
    else:
        # Use existing fast path
        # ... existing implementation
```

#### 3.2 Progress Indication
Add clear progress bars for slow operations:
```python
with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TaskProgressColumn(),
    console=console
) as progress:
    task = progress.add_task("Fetching detailed commits...", total=len(commit_shas))
    
    for sha in commit_shas:
        detailed_commit = await github_client.get_commit(owner, repo_name, sha)
        detailed_commits.append(detailed_commit)
        progress.advance(task)
```

### Phase 4: User Experience Improvements

#### 4.1 Clear Documentation
Update command help text to be accurate:
```python
@click.option("--show-files", is_flag=True, 
              help="Show changed files for each commit (requires detailed API calls)")
@click.option("--show-stats", is_flag=True, 
              help="Show detailed line statistics (requires detailed API calls)")
```

#### 4.2 Performance Warnings
Warn users about slower operations:
```python
if needs_detailed and limit > 10:
    console.print(f"[yellow]Warning: Fetching detailed info for {limit} commits will make {limit} API calls.[/yellow]")
    if not Confirm.ask("Continue?", default=True):
        return
```

## Implementation Tasks

### Task 1: Infrastructure (High Priority)
- [ ] Add `get_detailed_commits` method to GitHubClient
- [ ] Modify `_show_commits` to detect when detailed calls are needed
- [ ] Add progress indication for multiple API calls

### Task 2: Fix File Changes (High Priority)  
- [ ] Implement `_display_file_changes` with real data
- [ ] Update commit table to show file count
- [ ] Test with various repositories

### Task 3: Fix Statistics (High Priority)
- [ ] Implement `_display_commit_statistics` with real data  
- [ ] Show meaningful metrics (lines added/deleted, files changed)
- [ ] Add summary statistics table

### Task 4: Fix Explanations (Medium Priority)
- [ ] Remove fork-only restriction from explanation system
- [ ] Allow explanations for any repository
- [ ] Update error handling

### Task 5: Performance & UX (Medium Priority)
- [ ] Add performance warnings for large requests
- [ ] Implement smart caching for repeated requests
- [ ] Add confirmation prompts for slow operations

### Task 6: Testing (High Priority)
- [ ] Test with main repositories (not just forks)
- [ ] Test with repositories of different sizes
- [ ] Test all flag combinations
- [ ] Verify API rate limiting handling

## Success Criteria

### Before (Current State)
```bash
uv run forklift show-commits repo --show-files --show-stats
# Output: Basic commit list, no files, no real stats, "N/A" everywhere
```

### After (Target State)  
```bash
uv run forklift show-commits repo --show-files --show-stats
# Output: 
# - Commit list with real file counts
# - Actual files changed for each commit
# - Real line addition/deletion statistics
# - Meaningful summary metrics
```

## Risk Mitigation

### API Rate Limiting
- Implement exponential backoff
- Show clear progress indication
- Allow users to cancel long operations
- Cache results when possible

### Performance Impact
- Warn users about slow operations
- Provide fast path for basic usage
- Consider pagination for large result sets

### Backward Compatibility
- Keep existing fast behavior as default
- Only use detailed calls when explicitly needed
- Maintain existing command interface

## Timeline Estimate

- **Task 1-3 (Core Fixes)**: 2-3 days
- **Task 4 (Explanations)**: 1 day  
- **Task 5 (Performance)**: 1-2 days
- **Task 6 (Testing)**: 1 day
- **Total**: 5-7 days

## Files to Modify

1. `src/forklift/github/client.py` - Add detailed commit fetching
2. `src/forklift/cli.py` - Fix `_show_commits` implementation  
3. `src/forklift/models/github.py` - Ensure Commit model handles all data
4. Tests - Add comprehensive test coverage

This plan will transform the `show-commits` command from a broken promise into a genuinely useful tool for detailed commit analysis.