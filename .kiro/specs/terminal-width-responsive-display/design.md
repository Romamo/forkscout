# Design Document

## Overview

The terminal width display issue occurs because Rich tables are being constrained by automatic width detection and column width limits, causing truncation and broken layouts in narrow terminals. The solution is to configure Rich tables to render at their natural width without terminal width constraints, allowing the terminal to handle horizontal scrolling natively.

## Architecture

The fix involves modifying the Rich table configuration in the `RepositoryDisplayService` to:

1. **Remove Width Constraints**: Ensure tables are not constrained by terminal width detection
2. **Configure Natural Column Widths**: Allow columns to size based on content rather than terminal limits
3. **Preserve Table Structure**: Maintain proper table formatting and alignment
4. **Maintain Backward Compatibility**: Keep existing behavior for wide terminals

## Components and Interfaces

### 1. Console Configuration

**Current State:**
- CLI already sets `width=None` on Console instances
- Display service creates Console with appropriate width settings for different interaction modes

**Required Changes:**
- Verify all Console instances use `width=None` consistently
- Ensure `expand=False` is set on all tables to prevent auto-expansion

### 2. Table Configuration

**Current State:**
- Tables use `expand=False` which is correct
- Some columns have fixed widths, others use `min_width`
- Recent commits column has dynamic width calculation

**Required Changes:**
- Remove or increase maximum width limits on columns
- Ensure no table-level width constraints
- Configure columns to use natural content-based sizing

### 3. Column Width Management

**Current Implementation:**
```python
# Fixed width columns
table.add_column("Stars", width=8)
table.add_column("Forks", width=8) 
table.add_column("Commits", width=15)

# Dynamic width with limits
commits_width = max(50, min(400, calculated_width))
table.add_column("Recent Commits", width=commits_width)
```

**Proposed Changes:**
```python
# Use min_width instead of fixed width for flexibility
table.add_column("Stars", min_width=8)
table.add_column("Forks", min_width=8)
table.add_column("Commits", min_width=15)

# Remove upper limits on dynamic columns
table.add_column("Recent Commits", min_width=30)  # No max width
```

## Data Models

### Table Configuration Classes

**ForkTableConfig Updates:**
```python
@dataclass
class ForkTableConfig:
    # Use min_width instead of fixed width
    COLUMN_MIN_WIDTHS: ClassVar[dict[str, int]] = {
        "url": 35,
        "stars": 8,
        "forks": 8,
        "commits": 15,
        "last_push": 14,
        "recent_commits": 30,  # Minimum only, no maximum
    }
```

### Console Configuration

**Enhanced Console Setup:**
```python
def create_display_console() -> Console:
    """Create console optimized for natural table width rendering."""
    return Console(
        file=sys.stdout,
        width=None,           # No width constraints
        soft_wrap=False,      # Prevent text wrapping
        force_terminal=False, # Let Rich detect terminal capabilities
        legacy_windows=False  # Use modern terminal features
    )
```

## Error Handling

### Width Detection Fallbacks

**Issue:** Rich might still try to detect terminal width in some cases
**Solution:** Explicitly override width detection behavior

```python
def configure_table_for_natural_width(table: Table) -> None:
    """Configure table to render at natural width."""
    # Ensure table doesn't expand to fill terminal
    table.expand = False
    
    # Set a very large width if Rich tries to constrain
    if hasattr(table, '_width'):
        table._width = None
```

### Column Overflow Handling

**Current:** Uses `overflow="fold"` which can cause wrapping
**Proposed:** Use `overflow="ellipsis"` for fixed-width columns, no overflow for flexible columns

```python
# For columns that should remain compact
table.add_column("Stars", min_width=8, overflow="ellipsis")

# For columns that should show full content
table.add_column("URL", min_width=35)  # No overflow constraint
table.add_column("Recent Commits", min_width=30)  # No overflow constraint
```

## Testing Strategy

### Unit Tests

1. **Table Configuration Tests**
   ```python
   def test_table_natural_width_configuration():
       """Test that tables are configured for natural width rendering."""
       table = create_fork_table()
       assert table.expand == False
       assert all(col.min_width is not None for col in table.columns)
   ```

2. **Console Configuration Tests**
   ```python
   def test_console_width_configuration():
       """Test that console is configured without width constraints."""
       console = create_display_console()
       assert console.width is None
       assert console.soft_wrap == False
   ```

### Integration Tests

1. **Wide Content Rendering**
   ```python
   @pytest.mark.integration
   def test_wide_table_rendering():
       """Test that wide tables render without truncation."""
       # Create table with very long content
       # Verify no truncation occurs
       # Check that table structure remains intact
   ```

2. **Terminal Width Independence**
   ```python
   @pytest.mark.integration  
   def test_terminal_width_independence():
       """Test that table rendering is independent of terminal width."""
       # Mock different terminal widths
       # Verify table output is identical
   ```

### Manual Testing

1. **Narrow Terminal Testing**
   - Test in terminals with widths: 40, 60, 80, 120 characters
   - Verify table structure remains intact
   - Confirm horizontal scrolling works naturally

2. **Content Variation Testing**
   - Test with short and long URLs
   - Test with varying commit message lengths
   - Verify all content is fully visible

## Implementation Plan

### Phase 1: Console Configuration
- Verify all Console instances use `width=None`
- Ensure consistent configuration across all interaction modes
- Add explicit width override if needed

### Phase 2: Table Column Configuration  
- Update column definitions to use `min_width` instead of fixed `width`
- Remove maximum width constraints on content columns
- Update ForkTableConfig class

### Phase 3: Dynamic Width Removal
- Remove dynamic width calculation for Recent Commits column
- Simplify column width logic
- Ensure natural content-based sizing

### Phase 4: Testing and Validation
- Add comprehensive tests for table configuration
- Test with various terminal widths and content lengths
- Validate backward compatibility

## Backward Compatibility

### Wide Terminal Behavior
- Tables in wide terminals will look identical to current behavior
- No visual changes when terminal width is sufficient
- All existing functionality preserved

### Output Redirection
- File output behavior remains unchanged
- CSV export functionality unaffected
- Logging and progress reporting unchanged

### Command Line Interface
- All existing flags and options work unchanged
- No new configuration options required
- Existing workflows continue to function

## Performance Considerations

### Rendering Performance
- Natural width calculation may be slightly faster (no complex width calculations)
- Memory usage remains the same
- No impact on data fetching or processing

### Terminal Performance
- Terminal handles horizontal scrolling natively (no application overhead)
- Large tables may require more terminal buffer space
- Modern terminals handle wide content efficiently

## Configuration Options

### Future Enhancements (Optional)
```python
# Potential configuration options for advanced users
class DisplayConfig:
    max_column_width: Optional[int] = None  # Override for very long content
    force_terminal_width: Optional[int] = None  # Force specific width
    enable_column_wrapping: bool = False  # Allow text wrapping in columns
```

### Environment Variables
```bash
# Potential environment overrides
FORKSCOUT_MAX_COLUMN_WIDTH=1000
FORKSCOUT_FORCE_TERMINAL_WIDTH=120
```

## Migration Strategy

### Gradual Rollout
1. **Phase 1**: Update console configuration (low risk)
2. **Phase 2**: Update table column configuration (medium risk)  
3. **Phase 3**: Remove dynamic width calculations (higher risk)
4. **Phase 4**: Add comprehensive testing and validation

### Rollback Plan
- Each phase can be independently reverted
- Configuration changes are isolated and reversible
- No database or cache changes required

### User Communication
- Document the change in release notes
- Explain that wide tables now scroll horizontally
- Provide guidance for users with very narrow terminals