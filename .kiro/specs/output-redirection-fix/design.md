# Design Document

## Overview

This design addresses the issue where the Recent Commits column gets cut off when output is redirected to a file. The Rich library automatically constrains table width when it detects non-TTY output, causing commit messages to be truncated. The solution is to detect output redirection and set an appropriate maximum width (1000 characters) for the Recent Commits column.

## Architecture

### Current State Analysis

The `RepositoryDisplayService` currently:
- Uses existing terminal width detection for column sizing
- Has unlimited width for Recent Commits column in terminal output
- Gets constrained by Rich library when output is redirected to files

### Target Architecture

Enhanced column width logic that:
- Detects when output is being redirected to a file
- Sets Recent Commits column to 1000 character maximum for file output
- Maintains existing behavior for terminal output
- Uses the existing `TerminalDetector` class for redirection detection

## Components and Interfaces

### Enhanced RepositoryDisplayService

The main component requiring modification:

```python
class RepositoryDisplayService:
    def _get_recent_commits_column_width(self) -> Optional[int]:
        """Get appropriate width for Recent Commits column based on output context"""
        if self.terminal_detector.is_output_redirected():
            return 1000  # Max width for file output
        return None  # Unlimited for terminal output
```

### Terminal Detection Integration

Enhance the existing `TerminalDetector` class:

```python
class TerminalDetector:
    def is_output_redirected(self) -> bool:
        """Detect if stdout is being redirected to a file"""
        return not sys.stdout.isatty()
```

## Data Models

No new data models required. The existing table column configuration will be enhanced to support conditional width settings.

## Error Handling

- Graceful fallback to existing behavior if terminal detection fails
- No breaking changes to existing functionality
- Maintain backward compatibility for all output scenarios

## Testing Strategy

### Unit Tests

- Test terminal detection logic for redirected vs non-redirected output
- Test column width calculation with different output contexts
- Mock-based tests for various redirection scenarios

### Integration Tests

- Test actual output redirection with real commands
- Verify commit messages are not truncated in redirected files
- Validate terminal output remains unchanged
- Test with various commit message lengths

### Contract Tests

- Verify Rich table behavior with different column width settings
- Test that 1000 character width accommodates typical commit messages
- Validate no performance impact from width changes

## Implementation Approach

### Single Phase Implementation

This is a focused fix that can be implemented in one phase:

1. Enhance `TerminalDetector` with redirection detection
2. Modify `RepositoryDisplayService` column width logic
3. Add comprehensive tests for both terminal and file output
4. Validate the fix with real-world scenarios

## Performance Considerations

- Minimal overhead from terminal detection (single system call)
- No impact on terminal display performance
- File output may be slightly larger but more useful
- No memory or processing overhead

## Security Considerations

- No security implications for this change
- Uses standard system calls for terminal detection
- No changes to data handling or external communications