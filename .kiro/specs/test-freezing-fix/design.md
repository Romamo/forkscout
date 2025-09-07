# Design Document

## Overview

The test suite is freezing due to multiple issues: missing async decorators, undefined fixtures, real API calls without proper mocking, and unregistered pytest marks. This design addresses each category of issue systematically to create a fast, reliable test suite.

## Architecture

### Test Organization Strategy
- **Examples Directory**: Convert to proper unit tests with mocks or move to integration tests
- **Async Test Handling**: Ensure all async functions have proper decorators
- **API Call Management**: Separate real API tests from unit tests using proper markers
- **Fixture Management**: Define missing fixtures or convert to parameterized tests

### Test Categories
1. **Unit Tests**: Fast, mocked tests (< 2 minutes total)
2. **Integration Tests**: Real local system tests (< 10 minutes total)
3. **Online Tests**: Real external API tests, marked and skippable
4. **Example Tests**: Converted to proper test format or removed

## Components and Interfaces

### 1. Pytest Configuration Enhancement
**File**: `pytest.ini`
**Purpose**: Register all custom marks and configure test execution
**Interface**:
```ini
[tool:pytest]
markers =
    unit: Unit tests with mocks and isolated components
    integration: Integration tests with real local systems
    online: Online tests with real external APIs (free)
    billable: Billable tests with paid external APIs
    contract: API contract and schema tests
    e2e: End-to-end tests with complete workflows
    performance: Performance and benchmarking tests
    slow: Tests that take longer to run

addopts = -m "not billable and not online" --tb=short -v
asyncio_mode = auto
```

### 2. Example Test Fixes
**Files**: All files in `examples/` directory
**Purpose**: Fix async decorators and API call issues
**Interface**:
- Add `@pytest.mark.asyncio` to all async test functions
- Add `@pytest.mark.online` to tests making real API calls
- Mock external dependencies for unit tests
- Define missing fixtures or convert to parameterized tests
- **Remove inappropriate rate limit tests** that intentionally trigger rate limiting

### 3. Inappropriate Rate Limit Test Removal
**Files**: 
- `examples/test_rate_limit_fix.py` - Tests that intentionally hit rate limits
- `examples/test_progress_feedback.py` - Tests that simulate rate limit errors with real delays
- `examples/rate_limiting_demo.py` - Demo that consumes API quota unnecessarily
**Purpose**: Remove or convert tests that inappropriately consume API rate limits
**Issues**:
- Tests that intentionally trigger rate limiting waste API quota
- Tests with real 10+ second delays cause test suite to hang
- Rate limit testing should use mocks, not real API calls
- Demo scripts should not be in test discovery paths

### 3. Test Fixture Definitions
**File**: `conftest.py` (create if needed)
**Purpose**: Define missing fixtures used by tests
**Interface**:
```python
@pytest.fixture
def commit_url():
    return "https://github.com/octocat/Hello-World/commit/7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"

@pytest.fixture
def mock_github_client():
    return AsyncMock(spec=GitHubClient)
```

### 4. Test Timeout Configuration
**Purpose**: Prevent tests from hanging indefinitely
**Interface**:
- Add timeout decorators to potentially long-running tests
- Configure pytest timeout plugin if needed

## Data Models

### Test Execution Categories
```python
class TestCategory(Enum):
    UNIT = "unit"           # < 2 minutes total, mocked
    INTEGRATION = "integration"  # < 10 minutes total, real local systems
    ONLINE = "online"       # Real external APIs, skippable
    BILLABLE = "billable"   # Paid APIs, manual execution only
    PERFORMANCE = "performance"  # Benchmarking, excluded by default
```

### Test Fix Strategy
```python
@dataclass
class TestFix:
    file_path: str
    issue_type: str  # "missing_async_decorator", "real_api_calls", "missing_fixture"
    fix_action: str  # "add_decorator", "add_mocks", "define_fixture"
    test_functions: List[str]
```

## Error Handling

### Test Execution Errors
- **Missing Decorators**: Add `@pytest.mark.asyncio` to async functions
- **Missing Fixtures**: Define fixtures in conftest.py or convert to parameterized tests
- **Real API Calls**: Mock for unit tests or mark as online tests
- **Hanging Tests**: Add timeouts and proper error handling

### Graceful Degradation
- Tests requiring external services should be skippable
- Missing environment variables should skip tests, not fail them
- Network failures should be handled gracefully in online tests

## Testing Strategy

### Test Execution Phases
1. **Fast Unit Tests**: Run first for immediate feedback (< 2 minutes)
2. **Integration Tests**: Run for local system validation (< 10 minutes)
3. **Online Tests**: Run manually or in CI for external API validation
4. **Performance Tests**: Run separately for benchmarking

### Test Organization
```
tests/
├── unit/           # Fast, mocked tests
├── integration/    # Real local system tests
├── online/         # Real external API tests
├── contract/       # API contract tests
├── e2e/           # End-to-end tests
└── performance/   # Benchmarking tests

examples/          # Convert to proper tests or remove
```

### Execution Commands
```bash
# Fast feedback (default)
uv run pytest

# Include integration tests
uv run pytest -m "not billable and not online"

# Include online tests (manual)
uv run pytest -m "not billable"

# All tests including billable (manual)
uv run pytest --tb=short
```

## Implementation Plan

### Phase 1: Fix Async Decorators
- Add `@pytest.mark.asyncio` to all async test functions
- Verify async tests can run without hanging

### Phase 2: Handle API Calls and Remove Inappropriate Tests
- Mock external API calls in unit tests
- Mark real API tests with `@pytest.mark.online`
- **Remove or convert inappropriate rate limit tests**:
  - `test_rate_limit_fix.py` - Convert to mocked unit test
  - `test_progress_feedback.py` - Mock the delays, don't use real 10-second waits
  - `rate_limiting_demo.py` - Move out of test discovery or convert to proper test
- Ensure tests can run without external dependencies

### Phase 3: Fix Missing Fixtures
- Define `commit_url` fixture for `test_github_only.py`
- Create other missing fixtures as needed
- Convert to parameterized tests where appropriate

### Phase 4: Optimize Test Organization
- Move example tests to appropriate categories
- Configure pytest marks and execution
- Add timeouts to prevent hanging

### Phase 5: Validation
- Run full test suite to ensure no freezing
- Verify test execution times are reasonable
- Confirm all test categories work independently