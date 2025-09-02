# Design Document

## Overview

This design addresses the critical bug where forks consistently show "+1" commits ahead regardless of their actual commit count. The root cause is the hardcoded `count=1` parameter in the `get_commits_ahead_batch` method, which limits API responses to 1 commit and causes incorrect counting logic.

The solution involves separating commit counting from commit detail fetching, using GitHub's compare API more efficiently, and implementing proper configuration for different use cases.

## Architecture

### Current Architecture Issues

The current implementation has a fundamental flaw in the `repository_display_service.py`:

```python
# PROBLEMATIC CODE
batch_results = await self.github_client.get_commits_ahead_batch(
    fork_data_list, owner, repo_name, count=1  # Minimum count to get commit info
)

# Then incorrectly assumes:
commits_ahead = len(commits_ahead_list)  # This will always be 1 if count=1!
```

**What Actually Happens:**

1. **API Call Made**: `GET /repos/parent/repo/compare/main...fork_owner:main`
2. **GitHub Response**: 
   ```json
   {
       "ahead_by": 23,           // Fork actually has 23 commits ahead!
       "commits": [              // But we only requested 1 commit object
           {"sha": "abc123..."}   // So only 1 commit object is returned
       ]
   }
   ```
3. **Our Broken Logic**: `len(commits) = 1`, so we think there's only 1 commit ahead
4. **Display Result**: "+1" (wrong!) instead of "+23" (correct!)

**The Fix:**
Use the `ahead_by` field from the GitHub response instead of counting the `commits` array length.

### New Architecture Design

#### 1. Separation of Concerns

**Commit Counting vs Commit Detail Fetching**

**Count-Only Operations** (for displaying "+23"):
```python
# API Call: GET /repos/parent/repo/compare/main...fork:main
# Response: {"ahead_by": 23, "commits": [...]}
# We use: ahead_by = 23
# Display: "+23"
# Cost: 1 API call, minimal data transfer
```

**Detail Operations** (for showing commit messages):
```python  
# API Call: GET /repos/parent/repo/compare/main...fork:main
# Response: {"ahead_by": 23, "commits": [commit1, commit2, commit3, ...]}
# We use: commits array (first 3-5 for display)
# Display: Commit messages, authors, dates in table
# Cost: 1 API call, larger data transfer (commit objects)
```

**Key Insight**: The same API call gives us both the count AND the details. We just need to use the right field for the right purpose:
- Use `ahead_by` for counting (always accurate)
- Use `commits` array for details (limited by our `count` parameter)

#### 2. Enhanced GitHub Client Methods

**New Method: `get_commits_ahead_count`**
```python
async def get_commits_ahead_count(
    self, fork_owner: str, fork_repo: str, parent_owner: str, parent_repo: str
) -> int:
    """Get the count of commits ahead without fetching commit details."""
```

**Enhanced Method: `get_commits_ahead_batch_counts`**
```python
async def get_commits_ahead_batch_counts(
    self, fork_data_list: list[tuple[str, str]], parent_owner: str, parent_repo: str
) -> dict[str, int]:
    """Get commit counts for multiple forks efficiently."""
```

#### 3. Configuration System

**Commit Count Configuration**
```python
@dataclass
class CommitCountConfig:
    max_count_limit: int = 100  # Maximum commits to count
    display_limit: int = 5      # Maximum commits to fetch for display
    use_unlimited_counting: bool = False  # For accuracy-critical scenarios
    timeout_seconds: int = 30   # Timeout for counting operations
```

## Components and Interfaces

### 1. GitHub API Integration Layer

#### Enhanced GitHubClient Methods

**Count-Only Method**
```python
async def get_commits_ahead_count(
    self, fork_owner: str, fork_repo: str, parent_owner: str, parent_repo: str, 
    max_count: int = 100
) -> int:
    """
    Get the number of commits ahead using GitHub compare API efficiently.
    
    Makes a single API call to:
    GET /repos/{parent_owner}/{parent_repo}/compare/{parent_branch}...{fork_owner}:{fork_branch}
    
    Returns the 'ahead_by' field from the response, which gives the exact count
    without needing to fetch or count individual commit objects.
    
    Args:
        fork_owner: Owner of the fork repository
        fork_repo: Name of the fork repository  
        parent_owner: Owner of the parent repository
        parent_repo: Name of the parent repository
        max_count: Maximum count to return (returns max_count if exceeded)
        
    Returns:
        Exact number of commits the fork is ahead, capped at max_count
        
    Example API Response:
        {
            "ahead_by": 23,     # This is what we return!
            "behind_by": 0,
            "total_commits": 23,
            "commits": [...]    # We ignore this array for counting
        }
    """
```

**Batch Count Method**
```python
async def get_commits_ahead_batch_counts(
    self, fork_data_list: list[tuple[str, str]], parent_owner: str, parent_repo: str,
    max_count: int = 100
) -> dict[str, int]:
    """
    Efficiently get commit counts for multiple forks using batch processing.
    
    API Call Pattern:
    1. GET /repos/{parent_owner}/{parent_repo} (1 call - get parent info)
    2. GET /repos/{fork_owner}/{fork_repo} (N calls - get each fork info) 
    3. GET /repos/{parent_owner}/{parent_repo}/compare/{parent_branch}...{fork_owner}:{fork_branch} (N calls)
    
    Total: 1 + N + N = 2N + 1 API calls (same as current, but with correct results)
    
    For each compare API call, we extract the 'ahead_by' field:
    
    Compare API Response:
    {
        "ahead_by": 15,        # Fork has 15 commits ahead - this is our answer!
        "behind_by": 3,        # Fork is 3 commits behind (we don't use this)
        "total_commits": 15,   # Same as ahead_by for ahead-only comparisons
        "commits": [           # Array of 15 commit objects (we ignore this for counting)
            {"sha": "...", "commit": {...}},
            {"sha": "...", "commit": {...}},
            // ... 13 more commits
        ]
    }
    
    We return: {"fork_owner/fork_repo": 15}
    
    Optimizations:
    - Single parent repository fetch (cached and reused)
    - Concurrent fork repository fetches (up to 5 concurrent)
    - Concurrent compare API calls (up to 5 concurrent)
    - Extract 'ahead_by' field instead of counting commits array
    - No unnecessary commit object parsing
    """
```

#### GitHub Compare API Response Structure

The GitHub compare API endpoint `/repos/{owner}/{repo}/compare/{base}...{head}` returns:

```json
{
    "ahead_by": 5,           // TOTAL commits ahead (this is what we need!)
    "behind_by": 2,          // Commits behind parent
    "total_commits": 5,      // Total commits in comparison (same as ahead_by for ahead-only)
    "status": "ahead",       // Status: "ahead", "behind", "identical", "diverged"
    "commits": [             // Array of actual commit objects (we don't need all of these!)
        {
            "sha": "abc123...",
            "commit": { "message": "...", "author": {...} },
            // ... full commit object data
        },
        // ... up to 250 commits (GitHub's limit)
    ]
}
```

**Key Insight**: The `ahead_by` field gives us the EXACT total count without needing to fetch or count the commits array. This is much more efficient than our current approach of fetching commits with `count=1` and assuming `len(commits) == total_commits_ahead`.

**Current Problem**: 
- We call `get_commits_ahead_batch(count=1)` 
- This fetches only 1 commit object in the `commits` array
- We count `len(commits)` which is always 1
- But `ahead_by` field would tell us the real count (e.g., 5, 12, 23)

**Solution**:
- Use the `ahead_by` field from the compare API response
- Only fetch commit objects when we need details for display
- Separate counting logic from detail fetching logic

### 2. Repository Display Service Updates

#### Method Signature Changes

**Updated Method**
```python
async def _get_exact_commit_counts_batch(
    self, forks_needing_api: list[ForkData], owner: str, repo_name: str,
    config: CommitCountConfig
) -> tuple[int, int]:  # Returns (successful_forks, api_calls_saved)
```

#### Logic Flow

1. **Separate counting from detail fetching**
   ```python
   # For commit counting (efficient)
   batch_counts = await self.github_client.get_commits_ahead_batch_counts(
       fork_data_list, owner, repo_name, max_count=config.max_count_limit
   )
   
   # For commit details (only when needed)
   if need_commit_details:
       batch_details = await self.github_client.get_commits_ahead_batch(
           fork_data_list, owner, repo_name, count=config.display_limit
       )
   ```

2. **Handle different display modes**
   - **Count-only mode**: Use `get_commits_ahead_batch_counts`
   - **Detail mode**: Use both count and detail methods
   - **CSV export**: Use detail method with appropriate limits

### 3. Configuration Management

#### Configuration Integration

**Service Configuration**
```python
class RepositoryDisplayService:
    def __init__(self, github_client: GitHubClient, config: CommitCountConfig = None):
        self.github_client = github_client
        self.commit_config = config or CommitCountConfig()
```

**CLI Integration**
```python
# New CLI options
@click.option('--max-commits-count', default=100, 
              help='Maximum commits to count (0 for unlimited)')
@click.option('--commit-display-limit', default=5,
              help='Maximum commits to fetch for display details')
```

## Data Models

### 1. Enhanced Fork Data Models

**Updated ForkData**
```python
@dataclass
class ForkData:
    # Existing fields...
    exact_commits_ahead: int | None = None
    commits_ahead_limited: bool = False  # True if count hit the limit
    commit_count_error: str | None = None  # Error message if counting failed
```

### 2. Commit Count Result Models

**New Model for Count Results**
```python
@dataclass
class CommitCountResult:
    count: int
    is_limited: bool  # True if count reached max_count_limit
    error: str | None = None
    
@dataclass
class BatchCommitCountResult:
    results: dict[str, CommitCountResult]
    total_api_calls: int
    parent_calls_saved: int
```

## Error Handling

### 1. Graceful Degradation

**Count Failure Handling**
```python
async def safe_get_commits_ahead_count(
    self, fork_owner: str, fork_repo: str, parent_owner: str, parent_repo: str
) -> CommitCountResult:
    """
    Safely get commit count with comprehensive error handling.
    
    Returns CommitCountResult with error information on failure.
    """
```

### 2. Error Categories

1. **Repository Access Errors**: Private repos, deleted repos
2. **Comparison Errors**: Divergent histories, branch mismatches  
3. **API Errors**: Rate limits, network timeouts
4. **Configuration Errors**: Invalid parameters

### 3. Error Display

**Display Format**
- **Unknown**: Repository access issues
- **Error**: API or comparison failures
- **100+**: Count exceeded limit
- **5**: Exact count when available

## Testing Strategy

### 1. Unit Tests

**GitHub Client Tests**
```python
class TestCommitCounting:
    async def test_get_commits_ahead_count_accurate(self):
        """Test that count method returns accurate numbers."""
        
    async def test_batch_count_optimization(self):
        """Test that batch counting saves API calls."""
        
    async def test_count_vs_detail_consistency(self):
        """Test that count and detail methods agree."""
```

**Repository Display Service Tests**
```python
class TestCommitCountDisplay:
    async def test_accurate_count_display(self):
        """Test that UI shows correct commit counts."""
        
    async def test_count_limit_handling(self):
        """Test behavior when counts exceed limits."""
```

### 2. Integration Tests

**Real GitHub Data Tests**
```python
@pytest.mark.online
async def test_real_fork_commit_counting():
    """Test with real GitHub repositories that have known commit counts."""
```

**Performance Tests**
```python
@pytest.mark.performance
async def test_batch_counting_performance():
    """Test that batch counting is faster than individual calls."""
```

### 3. Contract Tests

**GitHub API Contract Tests**
```python
@pytest.mark.contract
async def test_github_compare_api_response_format():
    """Verify GitHub compare API still returns expected fields."""
```

## Implementation Plan

### Phase 1: Core GitHub Client Updates
1. Implement `get_commits_ahead_count` method
2. Implement `get_commits_ahead_batch_counts` method  
3. Add comprehensive error handling
4. Add unit tests for new methods

### Phase 2: Repository Display Service Updates
1. Update `_get_exact_commit_counts_batch` method
2. Separate counting from detail fetching logic
3. Add configuration support
4. Update error handling and display

### Phase 3: CLI and Configuration
1. Add new CLI options for commit counting
2. Integrate configuration system
3. Update help text and documentation
4. Add integration tests

### Phase 4: Testing and Validation
1. Add comprehensive test suite
2. Test with real GitHub repositories
3. Performance testing and optimization
4. Documentation updates

## Performance Considerations

### 1. API Call Optimization

**Current vs New API Usage**
- **Current**: `1 + N + N` calls (parent + N fork repos + N comparisons) with wrong results
- **New**: `1 + N + N` calls (parent + N fork repos + N comparisons) with correct results
- **Optimization**: Same number of calls but accurate results

### 2. Response Size Optimization

**Compare API Efficiency**
- Use `ahead_by` field instead of counting commits array
- Avoid fetching commit objects when only count is needed
- Fetch commit details only for display purposes

### 3. Concurrent Processing

**Batch Processing Improvements**
```python
# Concurrent fork repository fetching
fork_tasks = [fetch_fork_repo(owner, repo) for owner, repo in fork_list]
fork_results = await asyncio.gather(*fork_tasks)

# Concurrent comparison calls
compare_tasks = [compare_commits(fork_info, parent_info) for fork_info in forks]
compare_results = await asyncio.gather(*compare_tasks)
```

## Monitoring and Observability

### 1. Metrics Collection

**Commit Count Metrics**
- Accuracy of count vs actual commits
- API call efficiency ratios
- Error rates by error type
- Performance timing metrics

### 2. Logging Enhancements

**Debug Logging**
```python
logger.debug(f"Commit count for {fork}: {count} (limited: {is_limited})")
logger.info(f"Batch counting: {successful}/{total} forks, {api_calls_saved} calls saved")
```

### 3. Health Checks

**Commit Counting Health**
- Verify count accuracy with known test repositories
- Monitor API response times
- Track error rates and types

This design ensures accurate commit counting while maintaining API efficiency and providing proper error handling for various edge cases.