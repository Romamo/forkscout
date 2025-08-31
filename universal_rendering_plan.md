# Universal Fork Table Rendering Implementation Plan

## Overview
Consolidate the two different fork table rendering methods (`_display_fork_data_table` and `_display_detailed_fork_table`) into a single, universal rendering system that provides consistent formatting while adapting to different data sources.

## Current State Analysis

### Existing Methods
1. **`_display_fork_data_table`** (Standard mode)
   - Used by `show_fork_data()` 
   - Shows status-based commit information ("Has commits", "0 commits")
   - Column widths: URL(35), Stars(8), Forks(8), Commits(12), Last Push(12)
   - Includes collection summary and fork insights

2. **`_display_detailed_fork_table`** (Detailed mode)
   - Used by `show_fork_data_detailed()`
   - Shows exact commit counts ("+5", empty for 0)
   - Column widths: URL(35), Stars(8), Forks(8), Commits Ahead(15), Last Push(14)
   - Minimal summary, focuses on precise data

## Proposed Universal Design

### 1. Unified Table Configuration

```python
class ForkTableConfig:
    """Configuration for universal fork table rendering."""
    
    # Standard column widths (consistent across modes)
    COLUMN_WIDTHS = {
        'url': 35,
        'stars': 8, 
        'forks': 8,
        'commits': 15,  # Unified width for both status and exact counts
        'last_push': 14,  # Accommodate "11 months ago"
        'recent_commits_base': 30,  # Minimum width, calculated dynamically
    }
    
    # Column styles
    COLUMN_STYLES = {
        'url': 'cyan',
        'stars': 'yellow',
        'forks': 'green', 
        'commits': 'magenta',
        'last_push': 'blue',
        'recent_commits': 'dim'
    }
```

### 2. Adaptive Data Formatting

```python
class CommitDataFormatter:
    """Handles adaptive formatting of commit information."""
    
    @staticmethod
    def format_commit_info(fork_data, has_exact_counts: bool) -> str:
        """Format commit information based on available data."""
        if has_exact_counts:
            # Detailed mode: show exact counts
            exact_count = getattr(fork_data, 'exact_commits_ahead', None)
            if isinstance(exact_count, int):
                return f"[green]+{exact_count}[/green]" if exact_count > 0 else ""
            else:
                return "[yellow]Unknown[/yellow]"
        else:
            # Standard mode: show status indicators
            status = getattr(fork_data.metrics, 'commits_ahead_status', 'Unknown')
            if status == "No commits ahead":
                return "0 commits"
            elif status == "Has commits":
                return "Has commits"
            else:
                return "[yellow]Unknown[/yellow]"
```

### 3. Universal Rendering Method

```python
async def _render_fork_table(
    self,
    fork_data_list: list,
    table_context: dict,
    show_commits: int = 0,
    force_all_commits: bool = False
) -> None:
    """Universal fork table rendering method.
    
    Args:
        fork_data_list: List of fork data objects
        table_context: Context information (owner, repo, mode, etc.)
        show_commits: Number of recent commits to show
        force_all_commits: Whether to fetch commits for all forks
    """
    
    # 1. Determine rendering mode and capabilities
    has_exact_counts = table_context.get('has_exact_counts', False)
    mode_name = "Detailed" if has_exact_counts else "All"
    
    # 2. Create consistent table structure
    table_title = self._build_table_title(fork_data_list, table_context, show_commits)
    fork_table = Table(title=table_title)
    
    # 3. Add standard columns with unified widths
    self._add_standard_columns(fork_table)
    
    # 4. Conditionally add Recent Commits column
    if show_commits > 0:
        commits_width = self._calculate_commits_column_width(fork_data_list, show_commits)
        fork_table.add_column(
            "Recent Commits", 
            style="dim", 
            width=commits_width, 
            no_wrap=True
        )
    
    # 5. Sort data consistently
    sorted_forks = self._sort_forks_universal(fork_data_list, has_exact_counts)
    
    # 6. Fetch commits if needed
    commits_cache = {}
    if show_commits > 0:
        commits_cache = await self._fetch_commits_concurrently(
            sorted_forks, show_commits, 
            table_context['owner'], table_context['repo'],
            force_all_commits
        )
    
    # 7. Populate table rows
    for fork_data in sorted_forks:
        row_data = self._build_table_row(
            fork_data, has_exact_counts, commits_cache, show_commits
        )
        fork_table.add_row(*row_data)
    
    # 8. Display table and summary
    self._display_table_with_context(fork_table, table_context)
```

### 4. Refactored Method Signatures

```python
async def show_fork_data(self, ...) -> dict[str, Any]:
    """Standard fork data display using universal renderer."""
    # ... existing data collection logic ...
    
    table_context = {
        'owner': owner,
        'repo': repo_name,
        'has_exact_counts': False,
        'mode': 'standard',
        'api_calls_made': 0,
        'api_calls_saved': 0
    }
    
    await self._render_fork_table(
        filtered_forks, table_context, show_commits, force_all_commits
    )

async def show_fork_data_detailed(self, ...) -> dict[str, Any]:
    """Detailed fork data display using universal renderer."""
    # ... existing data collection and API call logic ...
    
    table_context = {
        'owner': owner,
        'repo': repo_name, 
        'has_exact_counts': True,
        'mode': 'detailed',
        'api_calls_made': api_calls_made,
        'api_calls_saved': api_calls_saved
    }
    
    await self._render_fork_table(
        detailed_forks, table_context, show_commits, force_all_commits
    )
```

## Implementation Steps

### Phase 1: Create Universal Components
1. Create `ForkTableConfig` class with standardized column definitions
2. Create `CommitDataFormatter` class for adaptive data formatting
3. Create helper methods for table building (`_add_standard_columns`, `_build_table_title`, etc.)

### Phase 2: Implement Universal Renderer
1. Implement `_render_fork_table` method with full functionality
2. Create `_sort_forks_universal` method that handles both data types
3. Implement `_build_table_row` method for adaptive row construction
4. Create `_display_table_with_context` for consistent summary display

### Phase 3: Refactor Existing Methods
1. Modify `show_fork_data` to use universal renderer
2. Modify `show_fork_data_detailed` to use universal renderer
3. Remove old rendering methods (`_display_fork_data_table`, `_display_detailed_fork_table`)
4. Update all references and imports

### Phase 4: Testing and Validation
1. Create comprehensive unit tests for universal renderer
2. Test with various data scenarios (empty, small, large datasets)
3. Verify consistent formatting across modes
4. Performance testing to ensure no regression
5. Integration testing with real repository data

## Benefits

### Consistency
- Identical column widths and styling across modes
- Consistent table titles and headers
- Unified Recent Commits column behavior

### Maintainability  
- Single source of truth for table rendering logic
- Easier to add new features (affects both modes automatically)
- Reduced code duplication

### User Experience
- Predictable interface regardless of mode
- Consistent visual layout
- Same column positions and widths

### Flexibility
- Easy to add new display modes in the future
- Configurable column widths and styles
- Adaptive content based on available data

## Migration Strategy

### Backward Compatibility
- Maintain existing CLI interface and behavior
- Ensure output format remains functionally identical
- Preserve all existing functionality

### Rollout Plan
1. Implement universal renderer alongside existing methods
2. Add feature flag to switch between old and new renderers
3. Test thoroughly with existing test suite
4. Gradually migrate to universal renderer
5. Remove old methods once fully validated

## Testing Strategy

### Unit Tests
- Test universal renderer with mock data
- Test adaptive formatting with different data types
- Test column width calculations
- Test sorting logic for both modes

### Integration Tests  
- Test with real repository data
- Compare output between old and new renderers
- Test performance with large datasets
- Test error handling and edge cases

### Visual Regression Tests
- Capture table output for comparison
- Ensure consistent formatting
- Verify column alignment and spacing
- Test with various terminal widths

This plan provides a comprehensive approach to unifying the fork table rendering while maintaining all existing functionality and improving consistency across the application.