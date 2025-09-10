# Design Document

## Overview

This design addresses the repository name validation issue that causes the `forkscout show-forks` command to fail when encountering GitHub repository names with consecutive periods. The solution involves updating the validation logic to be more permissive while maintaining data integrity, implementing graceful error handling, and ensuring robust processing of fork data.

## Architecture

### Current Problem Analysis

The current validation in `Repository.validate_github_name()` includes this rule:
```python
if ".." in v:
    raise ValueError("GitHub names cannot contain consecutive periods")
```

However, the GitHub API is returning repository names like `maybe-finance.._..maybe` that contain consecutive periods, suggesting either:
1. Our validation is more restrictive than GitHub's actual rules
2. There are edge cases in GitHub's naming that we haven't accounted for
3. There may be corrupted or unusual data in some repository names

### Solution Approach

The design follows a **graceful degradation** strategy:
1. **Relaxed Validation**: Update validation rules to match GitHub's actual behavior
2. **Error Isolation**: Prevent individual validation failures from crashing the entire process
3. **Comprehensive Logging**: Provide detailed information about validation issues
4. **Data Sanitization**: Clean problematic names when possible while preserving functionality

## Components and Interfaces

### 1. Updated Repository Model Validation

**File**: `src/forkscout/models/github.py`

```python
@field_validator("owner", "name")
@classmethod
def validate_github_name(cls, v: str) -> str:
    """Validate GitHub username/repository name format with graceful handling."""
    # Basic format check - allow more characters that GitHub actually permits
    if not re.match(r"^[a-zA-Z0-9._-]+$", v):
        logger.warning(f"Repository name '{v}' contains unusual characters, but allowing it")
    
    # Check for leading/trailing periods (GitHub definitely doesn't allow this)
    if v.startswith(".") or v.endswith("."):
        raise ValueError("GitHub names cannot start or end with a period")
    
    # Relaxed consecutive period check - log but don't fail
    if ".." in v:
        logger.warning(f"Repository name '{v}' contains consecutive periods - this may be unusual GitHub data")
        # Don't raise an error, just log the warning
    
    return v
```

### 2. Graceful Error Handling Service

**New Component**: `src/forkscout/models/validation_handler.py`

```python
class ValidationHandler:
    """Handles validation errors gracefully during data processing."""
    
    def __init__(self):
        self.validation_errors = []
        self.processed_count = 0
        self.skipped_count = 0
    
    def safe_create_repository(self, data: dict) -> Repository | None:
        """Safely create Repository with error handling."""
        try:
            return Repository.from_github_api(data)
        except ValidationError as e:
            self.validation_errors.append({
                'repository': data.get('full_name', 'unknown'),
                'error': str(e),
                'data': data
            })
            self.skipped_count += 1
            return None
    
    def get_summary(self) -> dict:
        """Get processing summary."""
        return {
            'processed': self.processed_count,
            'skipped': self.skipped_count,
            'errors': self.validation_errors
        }
```

### 3. Updated Fork Data Collection

**File**: `src/forkscout/analysis/fork_data_collection_engine.py`

The fork data collection engine needs to be updated to use the graceful validation handler:

```python
async def collect_fork_data(self, forks: List[dict]) -> Tuple[List[Repository], ValidationSummary]:
    """Collect fork data with graceful error handling."""
    validation_handler = ValidationHandler()
    valid_repositories = []
    
    for fork_data in forks:
        repository = validation_handler.safe_create_repository(fork_data)
        if repository:
            valid_repositories.append(repository)
            validation_handler.processed_count += 1
    
    # Log summary of validation issues
    summary = validation_handler.get_summary()
    if summary['skipped'] > 0:
        logger.warning(f"Skipped {summary['skipped']} repositories due to validation errors")
        for error in summary['errors'][:5]:  # Log first 5 errors
            logger.warning(f"Validation error for {error['repository']}: {error['error']}")
    
    return valid_repositories, summary
```

### 4. Enhanced Display Service

**File**: `src/forkscout/display/repository_display_service.py`

Update the display service to show validation summary:

```python
async def display_forks_with_validation_summary(self, ...) -> None:
    """Display forks with validation error summary."""
    repositories, validation_summary = await self.collect_detailed_fork_data(...)
    
    # Display the main results
    self.display_forks_table(repositories)
    
    # Display validation summary if there were issues
    if validation_summary['skipped'] > 0:
        console.print(f"\n[yellow]Note: {validation_summary['skipped']} forks were skipped due to data validation issues.[/yellow]")
        if validation_summary['errors']:
            console.print("[dim]Use --verbose flag to see detailed validation errors.[/dim]")
```

## Data Models

### ValidationSummary Model

```python
class ValidationSummary(BaseModel):
    """Summary of validation results during processing."""
    
    processed: int = Field(description="Number of successfully processed items")
    skipped: int = Field(description="Number of items skipped due to validation errors")
    errors: List[dict] = Field(description="List of validation errors encountered")
    
    def has_errors(self) -> bool:
        return self.skipped > 0
    
    def get_error_summary(self) -> str:
        if not self.has_errors():
            return "No validation errors"
        return f"{self.skipped} items skipped due to validation errors"
```

### Updated Repository Model

The Repository model validation will be updated to be more permissive:

```python
@field_validator("owner", "name")
@classmethod
def validate_github_name(cls, v: str) -> str:
    """Validate GitHub username/repository name format."""
    # Allow basic GitHub name patterns
    if not re.match(r"^[a-zA-Z0-9._-]+$", v):
        # Log warning but don't fail for unusual characters
        logger.warning(f"Unusual characters in GitHub name: {v}")
    
    # Strict validation only for patterns GitHub definitely doesn't allow
    if v.startswith(".") or v.endswith("."):
        raise ValueError("GitHub names cannot start or end with a period")
    
    # Relaxed validation for consecutive periods - warn but allow
    if ".." in v:
        logger.warning(f"GitHub name contains consecutive periods: {v}")
    
    return v
```

## Error Handling

### Error Categories

1. **Critical Errors**: Validation failures that indicate serious data corruption
   - Leading/trailing periods in names
   - Completely invalid characters
   - Missing required fields

2. **Warning Errors**: Unusual but potentially valid data
   - Consecutive periods in names
   - Unusual character combinations
   - Edge-case naming patterns

3. **Recoverable Errors**: Issues that can be worked around
   - Individual repository validation failures
   - Partial data corruption
   - Network-related data issues

### Error Handling Strategy

```python
class ErrorSeverity(Enum):
    CRITICAL = "critical"    # Stop processing
    WARNING = "warning"      # Log and continue
    RECOVERABLE = "recoverable"  # Skip item and continue

def handle_validation_error(error: ValidationError, data: dict) -> ErrorSeverity:
    """Determine how to handle a validation error."""
    error_message = str(error)
    
    if "start or end with a period" in error_message:
        return ErrorSeverity.CRITICAL
    elif "consecutive periods" in error_message:
        return ErrorSeverity.WARNING
    elif "Invalid GitHub name format" in error_message:
        return ErrorSeverity.RECOVERABLE
    else:
        return ErrorSeverity.RECOVERABLE
```

## Testing Strategy

### Unit Tests

1. **Repository Validation Tests**
   - Test with various edge-case repository names
   - Test with consecutive periods in names
   - Test with unusual but valid GitHub names
   - Test error handling for invalid names

2. **Validation Handler Tests**
   - Test graceful error handling
   - Test error collection and reporting
   - Test processing summary generation

3. **Integration Tests**
   - Test full fork processing with mixed valid/invalid data
   - Test display service with validation errors
   - Test end-to-end command execution with problematic repositories

### Test Data

Create test fixtures with various repository name patterns:

```python
REPOSITORY_NAME_TEST_CASES = [
    # Valid names
    ("valid-repo", True),
    ("repo.name", True),
    ("repo_name", True),
    ("123repo", True),
    
    # Edge cases that should be allowed
    ("maybe-finance.._..maybe", True),  # The actual failing case
    ("repo..name", True),  # Consecutive periods - warn but allow
    
    # Invalid names that should fail
    (".invalid", False),  # Leading period
    ("invalid.", False),  # Trailing period
    ("", False),  # Empty name
]
```

### Contract Tests

Test with real GitHub API data to ensure our validation matches GitHub's actual behavior:

```python
@pytest.mark.online
async def test_repository_validation_with_real_github_data():
    """Test repository validation with real GitHub API responses."""
    # Test with the specific repository that's causing issues
    github_client = GitHubClient()
    forks = await github_client.get_repository_forks("maybe-finance", "maybe")
    
    validation_handler = ValidationHandler()
    for fork_data in forks[:10]:  # Test first 10 forks
        repo = validation_handler.safe_create_repository(fork_data)
        # Should not crash, even with edge-case names
        assert repo is not None or len(validation_handler.validation_errors) > 0
```

## Performance Considerations

### Validation Performance

- Keep validation logic lightweight to avoid impacting processing speed
- Use compiled regex patterns for better performance
- Minimize logging overhead for common cases

### Error Collection

- Limit the number of detailed errors stored to prevent memory issues
- Use efficient data structures for error collection
- Provide summary statistics instead of storing all error details

### Graceful Degradation

- Ensure that validation errors don't significantly slow down processing
- Use async-safe error handling to maintain concurrency
- Implement circuit breaker pattern if validation errors become excessive

## Migration Strategy

### Phase 1: Update Validation Rules
1. Update Repository model validation to be more permissive
2. Add comprehensive logging for validation edge cases
3. Maintain backward compatibility with existing code

### Phase 2: Add Error Handling
1. Implement ValidationHandler service
2. Update fork data collection to use graceful error handling
3. Add validation summary reporting

### Phase 3: Enhanced User Experience
1. Update display service to show validation summaries
2. Add verbose mode for detailed error reporting
3. Implement user-friendly error messages

### Rollback Plan

If the changes cause issues:
1. Revert validation rules to previous state
2. Add specific exception for the problematic repository name pattern
3. Implement temporary workaround while investigating root cause

This design ensures that the `forkscout show-forks` command will be robust against edge-case repository names while providing users with clear information about any data processing issues encountered.