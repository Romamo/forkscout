# Design Document

## Overview

The commit message truncation issue occurs in the `RepositoryDisplayService.format_recent_commits()` method, specifically in the `_truncate_commit_message()` helper method. The current implementation calculates a maximum message length based on column width constraints and truncates messages that exceed this length, adding "..." to indicate truncation.

The solution is to remove the artificial truncation logic while preserving the existing commit formatting structure, date handling, and sorting functionality. This will allow commit messages to display at their natural length while maintaining table integrity through Rich's built-in table rendering capabilities.

## Architecture

The fix involves modifying the commit message formatting pipeline in the `RepositoryDisplayService` class:

1. **Remove Truncation Logic**: Eliminate the `_truncate_commit_message()` method and its usage
2. **Preserve Message Cleaning**: Keep the message cleaning logic (newline removal, whitespace normalization)
3. **Maintain Column Width Calculation**: Keep existing column width calculation for table structure
4. **Update Format Logic**: Modify `format_recent_commits()` to use full messages without truncation

## Components and Interfaces

### 1. RepositoryDisplayService Class

**Current State:**
- `format_recent_commits()` method calculates `max_message_length` and calls `_truncate_commit_message()`
- `_truncate_commit_message()` truncates messages and adds "..." when they exceed the limit
- Column width calculation considers message length constraints

**Required Changes:**
- Remove `_truncate_commit_message()` method entirely
- Modify `format_recent_commits()` to use full cleaned messages
- Keep message cleaning logic (whitespace normalization)
- Preserve all other formatting logic (dates, hashes, sorting)

### 2. Message Processing Pipeline

**Current Flow:**
```
Raw commit message → Clean message → Calculate max length → Truncate → Format with date/hash
```

**New Flow:**
```
Raw commit message → Clean message → Format with date/hash (no truncation)
```

### 3. Column Width Management

**Current Implementation:**
- `calculate_commits_column_width()` considers message length for width calculation
- `max_message_length` is calculated based on available column width
- Width constraints are applied to prevent table overflow

**Proposed Changes:**
- Keep column width calculation for table structure
- Remove message length constraints from width calculation
- Allow Rich table rendering to handle content overflow naturally
- Maintain minimum width requirements for table readability

## Data Models

### Commit Formatting Structure

**Current Format (with truncation):**
```python
# With date
f"{date_str} {commit.short_sha} {truncated_message}"

# Without date (fallback)
f"{commit.short_sha}: {truncated_message}"
```

**New Format (without truncation):**
```python
# With date
f"{date_str} {commit.short_sha} {cleaned_message}"

# Without date (fallback)  
f"{commit.short_sha}: {cleaned_message}"
```

### Message Cleaning Logic

**Preserve Existing Cleaning:**
```python
def _clean_commit_message(self, message: str) -> str:
    """Clean commit message by removing newlines and normalizing whitespace."""
    if not message:
        return ""
    
    # Clean up the message (remove newlines and extra whitespace)
    return " ".join(message.split())
```

## Error Handling

### Edge Case Handling

**Empty Messages:**
- Continue to return empty string for empty messages
- Maintain existing null/None checking logic

**Special Characters:**
- Preserve existing character handling
- Let Rich table rendering handle display formatting

**Very Long Messages:**
- Remove artificial length limits
- Allow Rich to handle content overflow through terminal scrolling
- Maintain table structure integrity

### Backward Compatibility

**Existing Behavior Preservation:**
- Keep all date formatting logic unchanged
- Maintain chronological sorting (newest first)
- Preserve fallback formatting for commits without dates
- Keep "[dim]No commits[/dim]" for empty commit lists

## Testing Strategy

### Unit Tests

1. **Message Formatting Tests**
   ```python
   def test_format_recent_commits_no_truncation():
       """Test that commit messages are not truncated regardless of length."""
       long_message = "This is a very long commit message that would previously be truncated"
       commits = [create_test_commit(message=long_message)]
       
       result = service.format_recent_commits(commits, column_width=30)
       
       assert "..." not in result
       assert long_message in result
   ```

2. **Message Cleaning Tests**
   ```python
   def test_commit_message_cleaning_preserved():
       """Test that message cleaning logic is preserved."""
       message_with_newlines = "Line 1\nLine 2\n\nLine 3"
       commits = [create_test_commit(message=message_with_newlines)]
       
       result = service.format_recent_commits(commits)
       
       assert "Line 1 Line 2 Line 3" in result
       assert "\n" not in result.split("\n")[0]  # No newlines within message
   ```

3. **Format Structure Tests**
   ```python
   def test_commit_format_structure_unchanged():
       """Test that commit format structure remains unchanged."""
       commits = [create_test_commit(
           message="Test message",
           date=datetime(2024, 1, 15),
           short_sha="abc1234"
       )]
       
       result = service.format_recent_commits(commits)
       
       assert "2024-01-15 abc1234 Test message" in result
   ```

### Integration Tests

1. **Full Display Pipeline Tests**
   ```python
   @pytest.mark.integration
   async def test_show_forks_with_long_commit_messages():
       """Test that show-forks displays long commit messages without truncation."""
       # Test with real repository that has long commit messages
       # Verify no "..." appears in output
       # Confirm full messages are visible
   ```

2. **Table Structure Tests**
   ```python
   @pytest.mark.integration
   def test_table_structure_with_long_messages():
       """Test that table structure remains intact with long messages."""
       # Create commits with varying message lengths
       # Verify table formatting is preserved
       # Check column alignment
   ```

### Manual Testing

1. **Command Line Testing**
   ```bash
   # Test with repository known to have long commit messages
   uv run forkscout show-forks https://github.com/sanila2007/youtube-bot-telegram --detail --ahead-only --show-commits=10
   
   # Verify no truncation occurs
   # Check that full commit messages are visible
   # Confirm table structure is maintained
   ```

2. **Various Terminal Widths**
   - Test in narrow terminals (80 characters)
   - Test in wide terminals (120+ characters)
   - Verify consistent behavior across widths

## Implementation Plan

### Phase 1: Remove Truncation Logic
1. Remove `_truncate_commit_message()` method
2. Update `format_recent_commits()` to use full cleaned messages
3. Add message cleaning as separate method if needed

### Phase 2: Update Column Width Logic
1. Review `calculate_commits_column_width()` method
2. Remove message length constraints from width calculation
3. Ensure minimum width requirements are maintained

### Phase 3: Testing and Validation
1. Add comprehensive unit tests for new behavior
2. Add integration tests with real repositories
3. Test with various commit message lengths and formats
4. Validate table structure integrity

### Phase 4: Documentation and Cleanup
1. Update method documentation
2. Remove unused parameters related to truncation
3. Clean up any remaining truncation-related code

## Backward Compatibility

### Preserved Functionality
- All existing command-line options work unchanged
- Date formatting remains identical ("YYYY-MM-DD")
- Hash formatting remains identical (7-character short SHA)
- Chronological sorting preserved (newest first)
- Fallback formatting for commits without dates
- Empty commit handling ("[dim]No commits[/dim]")

### Output Changes
- **Before**: "2024-01-15 abc1234 Add provenance: false to..."
- **After**: "2024-01-15 abc1234 Add provenance: false to docker-publish.yml"

### No Breaking Changes
- CSV export functionality unaffected
- File output redirection works unchanged
- Progress indicators and logging unchanged
- All existing workflows continue to function

## Performance Considerations

### Rendering Performance
- Removing truncation logic slightly improves performance (fewer string operations)
- Message cleaning performance remains the same
- Rich table rendering handles long content efficiently

### Memory Usage
- Slightly higher memory usage for storing full messages (minimal impact)
- No significant change in overall memory footprint
- Commit data structures remain unchanged

### Terminal Performance
- Modern terminals handle long content efficiently
- Horizontal scrolling works natively
- No impact on data fetching or API performance

## Configuration Options

### Current Configuration
- `column_width` parameter in `format_recent_commits()`
- `min_width` and `max_width` in `calculate_commits_column_width()`
- `show_commits` parameter for number of commits to display

### Maintained Configuration
- All existing configuration options preserved
- `column_width` still used for table structure
- Width calculation methods remain for table layout
- No new configuration options required

### Future Enhancements (Optional)
```python
# Potential future configuration for advanced users
class CommitDisplayConfig:
    enable_message_truncation: bool = False  # Allow re-enabling if needed
    max_message_length: Optional[int] = None  # Override for very long messages
    truncation_indicator: str = "..."  # Customizable truncation indicator
```

## Migration Strategy

### Implementation Steps
1. **Phase 1**: Remove truncation logic (low risk)
2. **Phase 2**: Update tests to verify no truncation (medium risk)
3. **Phase 3**: Test with real repositories (validation)
4. **Phase 4**: Deploy and monitor for issues

### Rollback Plan
- Changes are isolated to formatting methods
- Easy to revert by restoring truncation logic
- No database or cache changes required
- Configuration remains backward compatible

### User Communication
- Document change in release notes
- Explain that commit messages now display in full
- Highlight improved information visibility
- Note that table structure remains unchanged

## Risk Assessment

### Low Risk Changes
- Removing truncation logic (simple string operation removal)
- Preserving existing message cleaning
- Maintaining all other formatting logic

### Medium Risk Areas
- Table rendering with very long messages
- Terminal compatibility across different environments
- Performance with repositories having many long commit messages

### Mitigation Strategies
- Comprehensive testing with various message lengths
- Testing across different terminal types and sizes
- Performance testing with large repositories
- Gradual rollout with monitoring

## Success Criteria

### Functional Success
- Commit messages display without "..." truncation
- Table structure remains intact and readable
- All existing functionality preserved
- No regression in performance or usability

### User Experience Success
- Users can see complete commit information
- Table remains scannable and organized
- Terminal scrolling works naturally for long content
- No breaking changes to existing workflows

### Technical Success
- Clean code without truncation complexity
- Maintained test coverage
- No performance degradation
- Backward compatibility preserved