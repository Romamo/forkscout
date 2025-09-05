# Design Document

## Overview

This design outlines the restructuring of CSV export columns to improve usability, readability, and data organization. The changes involve reordering columns, renaming headers for better clarity, removing unnecessary columns, splitting combined data fields, and adding new useful columns. The design maintains backward compatibility in terms of data content while significantly improving the user experience.

## Architecture

### Current CSV Structure Analysis

The existing CSV export system uses the following key components:
- `CSVExporter` class with configurable export options
- `_generate_forks_preview_headers()` method for column header generation
- `_format_fork_preview_row()` method for data formatting
- `CSVExportConfig` for controlling export behavior

### Proposed Changes

The restructure will modify the column generation and formatting methods to implement the new structure while maintaining the existing architecture and configuration system.

## Components and Interfaces

### Modified Components

#### CSVExporter Class
- **Method**: `_generate_forks_preview_headers()`
  - **Change**: Update column order and naming
  - **New Structure**: ["Fork URL", "Stars", "Forks", "Commits Ahead", "Commits Behind", ...]
  - **Removed Columns**: fork_name, owner, activity_status
  - **Added Columns**: Forks (from forks_count data)

- **Method**: `_format_fork_preview_row()`
  - **Change**: Update data mapping to match new headers
  - **New Mappings**: 
    - "Fork URL" ← fork.fork_url (moved to first position)
    - "Stars" ← fork.stars
    - "Forks" ← fork.forks_count (new column)
    - "Commits Ahead" ← fork.commits_ahead
    - "Commits Behind" ← fork.commits_behind (new column)

#### ForkPreviewItem Model
- **Assessment**: Current model should already contain required data
- **Required Fields**: fork_url, stars, forks_count, commits_ahead, commits_behind
- **Action**: Verify all required fields are available in the model

### Data Flow

```
ForkPreviewItem → _format_fork_preview_row() → CSV Row
                ↓
    New Column Mapping:
    - fork_url → "Fork URL" (position 1)
    - stars → "Stars" (position 2)  
    - forks_count → "Forks" (position 3)
    - commits_ahead → "Commits Ahead" (position 4)
    - commits_behind → "Commits Behind" (position 5)
    - [other existing columns continue...]
```

## Data Models

### Updated Column Schema

#### New Column Order and Names
1. **Fork URL** (was fork_url, moved from last to first)
2. **Stars** (was stars, renamed with proper case)
3. **Forks** (new column from forks_count data)
4. **Commits Ahead** (was commits_ahead, renamed with proper case)
5. **Commits Behind** (new column, split from commits data)
6. **[Existing columns continue with proper naming...]**

#### Removed Columns
- `fork_name` - Redundant with Fork URL
- `owner` - Redundant with Fork URL  
- `activity_status` - Not essential for basic analysis

#### Data Type Mapping
```python
{
    "Fork URL": str,           # GitHub URL
    "Stars": int,              # Star count
    "Forks": int,              # Fork count  
    "Commits Ahead": int,      # Commits ahead of upstream
    "Commits Behind": int,     # Commits behind upstream
}
```

### Backward Compatibility Considerations

#### Data Preservation
- All essential data from removed columns is preserved in Fork URL
- No data loss occurs, only presentation changes
- Core functionality remains unchanged

#### Configuration Impact
- Existing `CSVExportConfig` options remain functional
- `include_urls` config still controls URL inclusion
- `detail_mode` config still adds additional columns

## Error Handling

### Missing Data Scenarios

#### Fork URL Missing
- **Behavior**: Show empty string in Fork URL column
- **Fallback**: Continue processing other columns normally
- **Logging**: Log warning about missing URL data

#### Forks Count Missing  
- **Behavior**: Show 0 or empty string in Forks column
- **Fallback**: Use repository.forks_count if available
- **Logging**: Log info about missing forks count

#### Commits Behind Data Missing
- **Behavior**: Show empty string in Commits Behind column
- **Fallback**: Attempt to calculate from available commit data
- **Logging**: Log info about missing commits behind data

### Error Recovery Strategy

```python
def _format_fork_preview_row_safe(self, fork: ForkPreviewItem) -> dict[str, Any]:
    """Format fork row with comprehensive error handling."""
    try:
        return self._format_fork_preview_row(fork)
    except Exception as e:
        logger.warning(f"Error formatting fork row: {e}")
        return self._create_empty_row_with_headers()
```

## Testing Strategy

### Unit Tests

#### Column Header Tests
- Test new column order matches specification
- Test column name formatting (proper case, spaces)
- Test removed columns are not present
- Test new columns are included

#### Data Mapping Tests  
- Test Fork URL appears in first column
- Test Stars and Forks columns have correct data
- Test Commits Ahead/Behind split correctly
- Test empty/missing data handling

#### Configuration Tests
- Test URL inclusion/exclusion still works
- Test detail mode adds appropriate columns
- Test backward compatibility with existing configs

### Integration Tests

#### End-to-End CSV Export
- Test complete CSV export with new format
- Test CSV parsing in common spreadsheet applications
- Test data integrity across format change
- Test performance with large datasets

#### CLI Integration
- Test show-forks command with --csv flag
- Test output redirection works correctly
- Test combination with other flags (--detail, --ahead-only)

### Contract Tests

#### CSV Format Validation
- Test CSV headers match specification exactly
- Test column count is correct
- Test data types in each column
- Test CSV syntax validity

#### Spreadsheet Compatibility
- Test import into Excel
- Test import into Google Sheets
- Test import into LibreOffice Calc
- Test column auto-detection works

## Implementation Approach

### Phase 1: Core Column Restructure
1. Update `_generate_forks_preview_headers()` method
2. Modify `_format_fork_preview_row()` method  
3. Add comprehensive unit tests
4. Verify basic functionality

### Phase 2: Data Validation and Error Handling
1. Add missing data handling
2. Implement error recovery mechanisms
3. Add logging for data issues
4. Test edge cases thoroughly

### Phase 3: Integration and Compatibility
1. Test with existing CLI commands
2. Verify configuration compatibility
3. Test spreadsheet application imports
4. Performance testing with large datasets

### Phase 4: Documentation and Examples
1. Update CLI help text
2. Create example CSV outputs
3. Document migration from old format
4. Add troubleshooting guide

## Performance Considerations

### Memory Usage
- Column restructure should not impact memory usage
- Same data volume, different organization
- No additional data processing required

### Processing Speed
- Minimal impact on export speed
- Column reordering is O(1) operation
- Data mapping changes are constant time

### Scalability
- Maintains existing scalability characteristics
- No additional complexity introduced
- Same performance profile as current implementation

## Security Considerations

### Data Exposure
- No additional sensitive data exposed
- Same data visibility as current format
- URL data already included in existing exports

### Input Validation
- Maintain existing input validation
- No new user input processing required
- Same security profile as current implementation

## Migration Strategy

### Backward Compatibility
- Old CSV processing scripts may need column name updates
- Data content remains the same, only presentation changes
- Provide migration guide for common use cases

### Rollback Plan
- Keep old column generation methods as backup
- Add configuration flag for old format if needed
- Ensure easy reversion if issues arise

### User Communication
- Document changes in release notes
- Provide before/after examples
- Include migration tips for existing workflows