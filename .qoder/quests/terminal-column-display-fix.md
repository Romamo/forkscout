# Terminal Column Display Fix Design

## Overview

This document outlines the design for fixing the column truncation issue in Forklift's terminal display when running commands like:
```
uv run forkscout show-forks https://github.com/sanila2007/youtube-bot-telegram --detail --ahead-only --show-commits=2
```

The issue is that columns are being truncated or wrapped, making it difficult to read the output, especially the first column which should not be empty. The fix will ensure all columns are visible without truncation or wrapping, even when the content is longer than the terminal width.

This specifically affects the `_display_detailed_fork_table` function in `src/forklift/display/repository_display_service.py` which is used by the `show-forks` command with the `--detail` flag.

## Problem Analysis

### Current Issues

1. **Column Truncation**: Rich's Table component automatically truncates columns to fit the terminal width
2. **Column Wrapping**: Content is wrapped instead of being displayed in full
3. **First Column Empty**: The first column (URL) is being truncated to the point of being empty
4. **Fixed Width Limitation**: Even with a width of 1000 for redirected output, tables are still being truncated

### Root Causes

1. **Table Configuration**: The current table configuration in `_display_detailed_fork_table` uses `expand=False` but doesn't prevent truncation
2. **Column Overflow Settings**: Columns are configured with `overflow="fold"` but the table still applies width restrictions
3. **Console Width Limitation**: Even with a fixed width of 1000 for redirected output, the table rendering logic still applies truncation
4. **Missing `no_wrap` Configuration**: While some columns have `no_wrap=True`, the table container itself may still enforce width limits

## Solution Design

### Approach

1. **Modify Table Configuration**: Update the table creation to prevent column truncation
2. **Set Column Properties**: Configure columns with `no_wrap=True` and `overflow="fold"` to ensure full content display
3. **Adjust Console Settings**: Ensure the console is configured to handle long lines without wrapping
4. **Dynamic Width Calculation**: Remove fixed width limitations and allow unlimited width for table display

### Implementation Plan

#### 1. Update `_display_detailed_fork_table` Function

In `/src/forklift/display/repository_display_service.py`, modify the table creation in the `_display_detailed_fork_table` method:

```python
# Current table creation:
fork_table = Table(
    title=f"Detailed Forks ({len(sorted_forks)} active forks with exact commit counts){title_suffix}",
    expand=False       # Don't expand to full console width
)

# Updated table creation:
fork_table = Table(
    title=f"Detailed Forks ({len(sorted_forks)} active forks with exact commit counts){title_suffix}",
    expand=False,
    show_lines=True,
    collapse_padding=True,
    pad_edge=False,
    width=None  # Remove table width restrictions
)
```

#### 2. Update Column Definitions

Update each column to prevent truncation and wrapping:

```python
# Current column definitions:
fork_table.add_column("URL", style="cyan", min_width=35, no_wrap=True, overflow="fold")
fork_table.add_column("Stars", style="yellow", justify="right", width=8, no_wrap=True)
fork_table.add_column("Forks", style="green", justify="right", width=8, no_wrap=True)
fork_table.add_column(
    "Commits Ahead", style="magenta", justify="right", width=15, no_wrap=True
)
fork_table.add_column("Last Push", style="blue", width=14, no_wrap=True)

# Updated column definitions:
fork_table.add_column("URL", style="cyan", min_width=35, no_wrap=True, overflow="fold")
fork_table.add_column("Stars", style="yellow", justify="right", width=8, no_wrap=True, overflow="fold")
fork_table.add_column("Forks", style="green", justify="right", width=8, no_wrap=True, overflow="fold")
fork_table.add_column(
    "Commits Ahead", style="magenta", justify="right", width=15, no_wrap=True, overflow="fold"
)
fork_table.add_column("Last Push", style="blue", width=14, no_wrap=True, overflow="fold")
```

Additionally, ensure that columns with dynamic content also have proper overflow settings:

```python
# For columns with dynamic content that may be long:
fork_table.add_column("Column Name", style="style", no_wrap=True, overflow="fold", max_width=None)
```

#### 3. Add Recent Commits Column Configuration

For the recent commits column (when `show_commits > 0`):

```python
# Current recent commits column:
fork_table.add_column(
    "Recent Commits", 
    style="dim", 
    no_wrap=True,
    min_width=50,
    overflow="fold"
)

# Updated recent commits column:
fork_table.add_column(
    "Recent Commits", 
    style="dim", 
    no_wrap=True,
    min_width=50,
    overflow="fold",
    max_width=None  # Remove maximum width restriction
)
```

#### 4. Update Console Configuration

In the RepositoryDisplayService constructor, update the console configuration for redirected output:

```python
# Current console configuration for redirected output:
self.console = Console(file=sys.stdout, width=1000, force_terminal=True, soft_wrap=False, _environ={})

# Updated console configuration:
self.console = Console(file=sys.stdout, width=None, force_terminal=True, soft_wrap=False, _environ={}, no_wrap=True)
```

Also update the default console configuration:

```python
# Current default console configuration:
self.console = Console(file=sys.stdout, soft_wrap=False)

# Updated default console configuration:
self.console = Console(file=sys.stdout, soft_wrap=False, no_wrap=True)
```

## Technical Details

### Key Changes

1. **Console Configuration**:
   - Set `width=None` to remove width limitations
   - Add `no_wrap=True` to prevent line wrapping
   - Keep `soft_wrap=False` to maintain current behavior

2. **Table Configuration**:
   - Add `show_lines=True` for better visual separation
   - Add `collapse_padding=True` to optimize space usage
   - Keep `expand=False` to prevent automatic expansion
   - Add `width=None` to remove table width restrictions

3. **Column Configuration**:
   - Ensure all columns have `no_wrap=True`
   - Set `overflow="fold"` for all columns to allow content to wrap within cells if needed
   - Remove `max_width` restrictions where applicable

### Scope

This fix will only modify the `_display_detailed_fork_table` function in `src/forklift/display/repository_display_service.py` which is used by the `show-forks` command with the `--detail` flag. No other functions will be modified as part of this bug fix.

### Implementation Steps

1. **Update RepositoryDisplayService Constructor**:
   - Modify console configuration for both redirected and terminal output modes
   - Add `no_wrap=True` to console initialization
   - Set `width=None` for redirected output mode

2. **Update `_display_detailed_fork_table` Method**:
   - Modify table creation to include `width=None` parameter
   - Add `show_lines=True` and `collapse_padding=True` for better visual separation
   - Update all column definitions to include proper `overflow` settings
   - Ensure Recent Commits column has appropriate width settings

3. **Testing and Verification**:
   - Test with the specific command that was causing issues
   - Verify first column is no longer empty
   - Confirm all columns display full content without truncation
   - Test with various terminal widths and output redirection

## Testing Strategy

### Test Cases

1. **Basic Display Test**:
   ```
   uv run forkscout show-forks https://github.com/sanila2007/youtube-bot-telegram --detail --ahead-only --show-commits=2
   ```
   - Verify first column (URL) is not empty
   - Confirm all columns are visible without truncation

2. **Long Content Test**:
   - Test with repositories that have long names or URLs
   - Verify content is fully displayed without wrapping or truncation

3. **Terminal Redirection Test**:
   - Test with output redirection to file
   - Confirm content is properly formatted in file output

4. **Edge Case Test**:
   - Test with repositories having very long commit messages
   - Verify Recent Commits column displays properly

5. **Other Command Tests**:
   - Test `show-forks` without `--detail` flag
   - Test `show-fork-data` command
   - Test other table-based display commands

### Verification Steps

1. Run the specific command that was causing the issue:
   ```
   uv run forkscout show-forks https://github.com/sanila2007/youtube-bot-telegram --detail --ahead-only --show-commits=2
   ```

2. Verify that the first column (URL) is no longer empty

3. Check that all columns display their full content without truncation

4. Confirm that content does not wrap unnecessarily within columns

5. Test with different terminal widths to ensure consistent behavior

6. Test with output redirection to ensure file output is properly formatted

## Expected Results

After implementing the fix:

1. **No Column Truncation**: All columns will display their full content
2. **Visible First Column**: The URL column will no longer be empty
3. **No Unwanted Wrapping**: Content will not wrap within columns unnecessarily
4. **Horizontal Scrolling Support**: Users can horizontally scroll in their terminal to see full content
5. **Consistent Behavior**: Behavior will be consistent across terminal and file output modes

## Backward Compatibility

This change maintains backward compatibility as it only affects the display formatting and does not change any underlying data structures or APIs. The fix ensures that all previously displayed information is still visible, just without truncation.

## Performance Considerations

The changes will have minimal performance impact as they only affect the display rendering and do not introduce additional processing or API calls.

## Conclusion

This design provides a focused solution to the column truncation issue in Forklift's terminal display. By adjusting the Rich library table and console configurations, we can ensure that all column content is fully visible without truncation or unwanted wrapping. The fix specifically targets the `_display_detailed_fork_table` function which is used by the `show-forks` command with the `--detail` flag.

The implementation approach is minimal and focused, ensuring that we maintain backward compatibility while solving the core issue. Testing with the specific command that was causing problems will verify that the first column is no longer empty and that all column content is fully visible. Only the necessary lines of code will be modified to fix this specific bug.