# Design Document

## Overview

This design addresses the missing behind commits display functionality in forklift. The root cause is that while the system correctly extracts the `ahead_by` field from GitHub's compare API, it completely ignores the `behind_by` field. The solution involves updating the data models, GitHub client, and display logic to capture, store, and display behind commit counts alongside ahead commit counts.

## Architecture

### Current State Analysis

The current implementation in `src/forklift/github/client.py` correctly extracts `ahead_by` but ignores `behind_by`:

```python
# Current implementation (incomplete)
compare_response = await self._make_request('GET', f'/repos/{parent_owner}/{parent_repo}/compare/{parent_branch}...{fork_owner}:{fork_branch}')

# We extract this:
ahead_by = compare_response.get('ahead_by', 0)

# But we ignore this:
# behind_by = compare_response.get('behind_by', 0)  # <-- MISSING!
```

**GitHub Compare API Response Structure:**
```json
{
    "ahead_by": 9,      // ✅ Currently used
    "behind_by": 11,    // ❌ Currently ignored
    "total_commits": 9,
    "status": "diverged" // Can be: "ahead", "behind", "identical", "diverged"
}
```

### New Architecture Design

#### 1. Data Model Updates

**Enhanced Fork Data Models**

Update the `ForkData` model to include behind commits:

```python
@dataclass
class ForkData:
    # Existing fields...
    exact_commits_ahead: int | None = None
    exact_commits_behind: int | None = None  # NEW FIELD
    commits_ahead_limited: bool = False
    commit_count_error: str | None = None
```

**New Commit Count Result Models**

```python
@dataclass
class CommitCountResult:
    ahead_count: int
    behind_count: int  # NEW FIELD
    is_limited: bool = False
    error: str | None = None

@dataclass
class BatchCommitCountResult:
    results: dict[str, CommitCountResult]
    total_api_calls: int
    parent_calls_saved: int
```

#### 2. GitHub Client Updates

**Enhanced Compare API Response Handling**

```python
async def get_commits_ahead_and_behind_count(
    self, fork_owner: str, fork_repo: str, parent_owner: str, parent_repo: str
) -> CommitCountResult:
    """
    Get both ahead and behind commit counts using GitHub compare API.
    
    API Call: GET /repos/{parent_owner}/{parent_repo}/compare/{parent_branch}...{fork_owner}:{fork_branch}
    
    Example Response:
    {
        "ahead_by": 9,      // Fork has 9 commits ahead of parent
        "behind_by": 11,    // Fork is missing 11 commits from parent
        "total_commits": 9, // Total commits in comparison
        "status": "diverged" // Status indicates relationship
    }
    
    Returns:
        CommitCountResult with both ahead_count=9 and behind_count=11
    """
    try:
        # Get fork and parent repository info
        fork_repo_data = await self.get_repository(fork_owner, fork_repo)
        parent_repo_data = await self.get_repository(parent_owner, parent_repo)
        
        # Compare branches
        compare_url = f'/repos/{parent_owner}/{parent_repo}/compare/{parent_repo_data.default_branch}...{fork_owner}:{fork_repo_data.default_branch}'
        compare_response = await self._make_request('GET', compare_url)
        
        # Extract BOTH ahead and behind counts
        ahead_count = compare_response.get('ahead_by', 0)
        behind_count = compare_response.get('behind_by', 0)  # NEW: Extract behind count
        
        return CommitCountResult(
            ahead_count=ahead_count,
            behind_count=behind_count,
            is_limited=False,
            error=None
        )
        
    except Exception as e:
        logger.error(f"Failed to get commit counts for {fork_owner}/{fork_repo}: {e}")
        return CommitCountResult(
            ahead_count=0,
            behind_count=0,
            is_limited=False,
            error=str(e)
        )
```

**Enhanced Batch Processing**

```python
async def get_commits_ahead_and_behind_batch_counts(
    self, fork_data_list: list[tuple[str, str]], parent_owner: str, parent_repo: str
) -> BatchCommitCountResult:
    """
    Efficiently get both ahead and behind commit counts for multiple forks.
    
    For each fork, makes a compare API call and extracts both:
    - ahead_by: commits the fork is ahead of parent
    - behind_by: commits the fork is behind parent
    
    Returns:
        BatchCommitCountResult with CommitCountResult for each fork containing both counts
    """
    results = {}
    
    # Get parent repository info once
    parent_repo_data = await self.get_repository(parent_owner, parent_repo)
    
    # Process forks in batches
    for fork_owner, fork_repo in fork_data_list:
        try:
            # Get fork repository info
            fork_repo_data = await self.get_repository(fork_owner, fork_repo)
            
            # Compare branches
            compare_url = f'/repos/{parent_owner}/{parent_repo}/compare/{parent_repo_data.default_branch}...{fork_owner}:{fork_repo_data.default_branch}'
            compare_response = await self._make_request('GET', compare_url)
            
            # Extract both counts
            ahead_count = compare_response.get('ahead_by', 0)
            behind_count = compare_response.get('behind_by', 0)  # NEW
            
            results[f"{fork_owner}/{fork_repo}"] = CommitCountResult(
                ahead_count=ahead_count,
                behind_count=behind_count,
                is_limited=False,
                error=None
            )
            
        except Exception as e:
            logger.error(f"Failed to get commit counts for {fork_owner}/{fork_repo}: {e}")
            results[f"{fork_owner}/{fork_repo}"] = CommitCountResult(
                ahead_count=0,
                behind_count=0,
                is_limited=False,
                error=str(e)
            )
    
    return BatchCommitCountResult(
        results=results,
        total_api_calls=len(fork_data_list) * 2 + 1,  # 2 calls per fork + 1 parent call
        parent_calls_saved=len(fork_data_list) - 1
    )
```

#### 3. Repository Display Service Updates

**Enhanced Commit Count Processing**

```python
async def _get_exact_commit_counts_batch(
    self, forks_needing_api: list[ForkData], owner: str, repo_name: str,
    config: CommitCountConfig
) -> tuple[int, int]:
    """
    Get exact commit counts (both ahead and behind) for multiple forks.
    """
    fork_data_list = [(fork.owner, fork.name) for fork in forks_needing_api]
    
    # Get both ahead and behind counts
    batch_result = await self.github_client.get_commits_ahead_and_behind_batch_counts(
        fork_data_list, owner, repo_name
    )
    
    successful_forks = 0
    
    for fork in forks_needing_api:
        fork_key = f"{fork.owner}/{fork.name}"
        
        if fork_key in batch_result.results:
            result = batch_result.results[fork_key]
            
            if result.error is None:
                # Store BOTH ahead and behind counts
                fork.exact_commits_ahead = result.ahead_count
                fork.exact_commits_behind = result.behind_count  # NEW
                fork.commits_ahead_limited = result.is_limited
                successful_forks += 1
            else:
                fork.commit_count_error = result.error
        else:
            fork.commit_count_error = "No result returned"
    
    return successful_forks, batch_result.parent_calls_saved
```

#### 4. Display Formatting Updates

**Enhanced Commit Count Display**

```python
def _format_commit_count(self, fork: ForkData) -> str:
    """
    Format commit count display to include both ahead and behind commits.
    
    Examples:
    - ahead=9, behind=0  -> "+9"
    - ahead=0, behind=11 -> "-11"  
    - ahead=9, behind=11 -> "+9 -11"
    - ahead=0, behind=0  -> ""
    - error occurred     -> "Unknown"
    """
    if fork.commit_count_error:
        return "Unknown"
    
    ahead = fork.exact_commits_ahead or 0
    behind = fork.exact_commits_behind or 0
    
    if ahead == 0 and behind == 0:
        return ""
    elif ahead > 0 and behind == 0:
        return f"+{ahead}"
    elif ahead == 0 and behind > 0:
        return f"-{behind}"
    else:  # both > 0
        return f"+{ahead} -{behind}"
```

**CSV Export Updates**

```python
def _format_commit_count_for_csv(self, fork: ForkData) -> str:
    """
    Format commit count for CSV export including behind commits.
    
    Uses the same format as display: "+9 -11", "-11", "+9", or ""
    """
    return self._format_commit_count(fork)  # Same logic as display
```

## Components and Interfaces

### 1. Data Flow Architecture

```
GitHub Compare API Response
{
  "ahead_by": 9,
  "behind_by": 11,
  "status": "diverged"
}
         ↓
GitHub Client Enhancement
- Extract both ahead_by and behind_by
- Store in CommitCountResult
         ↓
Repository Display Service
- Update ForkData with both counts
- Pass to display formatter
         ↓
Display Formatter
- Format as "+9 -11"
- Handle all combinations
         ↓
User Interface
- Table display: "+9 -11"
- CSV export: "+9 -11"
```

### 2. Interface Definitions

**Enhanced GitHub Client Interface**

```python
class GitHubClient:
    async def get_commits_ahead_and_behind_count(
        self, fork_owner: str, fork_repo: str, parent_owner: str, parent_repo: str
    ) -> CommitCountResult:
        """Get both ahead and behind commit counts for a single fork."""
        
    async def get_commits_ahead_and_behind_batch_counts(
        self, fork_data_list: list[tuple[str, str]], parent_owner: str, parent_repo: str
    ) -> BatchCommitCountResult:
        """Get both ahead and behind commit counts for multiple forks efficiently."""
```

**Enhanced Display Service Interface**

```python
class RepositoryDisplayService:
    def _format_commit_count(self, fork: ForkData) -> str:
        """Format commit count including behind commits."""
        
    def _format_commit_count_for_csv(self, fork: ForkData) -> str:
        """Format commit count for CSV export."""
```

## Data Models

### 1. Enhanced Data Models

**Updated ForkData Model**

```python
@dataclass
class ForkData:
    # Existing fields...
    owner: str
    name: str
    full_name: str
    html_url: str
    description: str | None
    stars: int
    forks: int
    last_push: datetime | None
    
    # Enhanced commit tracking
    exact_commits_ahead: int | None = None
    exact_commits_behind: int | None = None  # NEW FIELD
    commits_ahead_limited: bool = False
    commit_count_error: str | None = None
```

**New Commit Count Models**

```python
@dataclass
class CommitCountResult:
    """Result of commit count operation including both ahead and behind."""
    ahead_count: int
    behind_count: int  # NEW FIELD
    is_limited: bool = False
    error: str | None = None
    
    @property
    def has_ahead_commits(self) -> bool:
        """True if fork has commits ahead of parent."""
        return self.ahead_count > 0
    
    @property
    def has_behind_commits(self) -> bool:
        """True if fork has commits behind parent."""
        return self.behind_count > 0
    
    @property
    def is_diverged(self) -> bool:
        """True if fork has both ahead and behind commits."""
        return self.ahead_count > 0 and self.behind_count > 0

@dataclass
class BatchCommitCountResult:
    """Result of batch commit count operation."""
    results: dict[str, CommitCountResult]
    total_api_calls: int
    parent_calls_saved: int
```

## Error Handling

### 1. Graceful Degradation

**Missing Behind Count Handling**

```python
def _extract_commit_counts(self, compare_response: dict) -> tuple[int, int]:
    """
    Safely extract ahead and behind counts from compare API response.
    
    Handles cases where behind_by field might be missing from older API responses.
    """
    ahead_count = compare_response.get('ahead_by', 0)
    behind_count = compare_response.get('behind_by', 0)  # Defaults to 0 if missing
    
    # Validate counts are non-negative
    ahead_count = max(0, ahead_count)
    behind_count = max(0, behind_count)
    
    return ahead_count, behind_count
```

### 2. Error Display

**Enhanced Error Handling**

```python
def _format_commit_count_with_error_handling(self, fork: ForkData) -> str:
    """
    Format commit count with comprehensive error handling.
    """
    try:
        if fork.commit_count_error:
            return "Unknown"
        
        ahead = fork.exact_commits_ahead
        behind = fork.exact_commits_behind
        
        # Handle None values gracefully
        if ahead is None and behind is None:
            return ""
        
        ahead = ahead or 0
        behind = behind or 0
        
        return self._format_commit_display(ahead, behind)
        
    except Exception as e:
        logger.error(f"Error formatting commit count for {fork.full_name}: {e}")
        return "Error"
```

## Testing Strategy

### 1. Unit Tests

**GitHub Client Tests**

```python
class TestCommitCountsWithBehind:
    async def test_get_commits_ahead_and_behind_count(self):
        """Test extraction of both ahead and behind counts."""
        
    async def test_batch_count_with_behind_commits(self):
        """Test batch processing includes behind counts."""
        
    async def test_behind_count_missing_field_handling(self):
        """Test graceful handling when behind_by field is missing."""
```

**Display Formatting Tests**

```python
class TestCommitCountDisplay:
    def test_format_ahead_only(self):
        """Test display of forks with only ahead commits."""
        assert format_commit_count(ahead=9, behind=0) == "+9"
        
    def test_format_behind_only(self):
        """Test display of forks with only behind commits."""
        assert format_commit_count(ahead=0, behind=11) == "-11"
        
    def test_format_both_ahead_and_behind(self):
        """Test display of forks with both ahead and behind commits."""
        assert format_commit_count(ahead=9, behind=11) == "+9 -11"
        
    def test_format_neither(self):
        """Test display of forks with no commits ahead or behind."""
        assert format_commit_count(ahead=0, behind=0) == ""
```

### 2. Integration Tests

**Real GitHub Data Tests**

```python
@pytest.mark.online
async def test_real_behind_commits_detection():
    """Test with real GitHub repositories that have behind commits."""
    # Test with GreatBots/YouTube_bot_telegram which has behind commits
    github_client = GitHubClient(token=os.getenv('GITHUB_TOKEN'))
    
    result = await github_client.get_commits_ahead_and_behind_count(
        'GreatBots', 'YouTube_bot_telegram',
        'sanila2007', 'youtube-bot-telegram'
    )
    
    # Verify both ahead and behind counts are detected
    assert result.ahead_count > 0  # Should have ahead commits
    assert result.behind_count > 0  # Should have behind commits
    assert result.error is None
```

### 3. Contract Tests

**GitHub API Contract Tests**

```python
@pytest.mark.contract
async def test_github_compare_api_behind_field():
    """Verify GitHub compare API includes behind_by field."""
    # Test that GitHub API still returns behind_by field
    response = await make_github_compare_request(
        'sanila2007/youtube-bot-telegram', 'GreatBots:mai'
    )
    
    assert 'behind_by' in response
    assert isinstance(response['behind_by'], int)
    assert response['behind_by'] >= 0
```

## Implementation Plan

### Phase 1: Data Model Updates
1. Update `ForkData` to include `exact_commits_behind` field
2. Create new `CommitCountResult` and `BatchCommitCountResult` models
3. Update existing code to use new models
4. Add unit tests for new models

### Phase 2: GitHub Client Enhancement
1. Update `get_commits_ahead_count` to extract `behind_by` field
2. Create new `get_commits_ahead_and_behind_count` method
3. Update batch processing methods to handle behind counts
4. Add comprehensive error handling
5. Add unit and integration tests

### Phase 3: Display Service Updates
1. Update `_get_exact_commit_counts_batch` to store behind counts
2. Create `_format_commit_count` method with behind support
3. Update CSV export formatting
4. Add display formatting tests

### Phase 4: Integration and Testing
1. Add integration tests with real GitHub data
2. Test with the specific GreatBots fork that shows the issue
3. Verify backward compatibility with existing functionality
4. Performance testing and optimization

### Phase 5: Documentation and Validation
1. Update documentation to explain behind commits display
2. Add troubleshooting guide for behind commits
3. Validate fix with original bug report scenario
4. Ensure no regression in existing functionality

## Performance Considerations

### 1. API Efficiency

**No Additional API Calls Required**
- Behind commits are extracted from the same compare API call used for ahead commits
- No performance impact on API usage
- Same number of API calls as current implementation

### 2. Memory Usage

**Minimal Memory Impact**
- Adding one integer field (`exact_commits_behind`) per fork
- Negligible memory overhead for typical fork counts

### 3. Display Performance

**Efficient Formatting**
- Simple string formatting logic
- No complex calculations required
- Minimal impact on display rendering time

## Monitoring and Observability

### 1. Metrics Collection

**Behind Commits Metrics**
- Track forks with behind commits vs ahead-only
- Monitor behind commit count distributions
- Track display formatting performance

### 2. Logging Enhancements

**Debug Logging**
```python
logger.debug(f"Commit counts for {fork}: ahead={ahead}, behind={behind}")
logger.info(f"Found {diverged_count} diverged forks with both ahead and behind commits")
```

### 3. Health Checks

**Behind Commits Validation**
- Verify behind counts are being extracted correctly
- Monitor for API response format changes
- Track error rates in behind commit processing

This design ensures that behind commits are properly displayed while maintaining full backward compatibility and API efficiency.