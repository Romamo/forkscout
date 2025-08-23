# Integration Testing Guidelines

## Core Philosophy

Integration tests are mandatory for any component that crosses system boundaries (cache, database, external APIs, file system). Unit tests with mocks are insufficient for catching real-world integration issues.

## When Integration Tests Are Required

### Cache Integration
- Any component that stores or retrieves data from cache
- Data serialization/deserialization operations
- Cache validation and fallback mechanisms

### External API Integration
- GitHub API client operations
- Rate limiting and error handling
- Authentication and authorization flows

### Database Operations
- Data persistence and retrieval
- Schema migrations and compatibility
- Transaction handling and rollback scenarios

### File System Operations
- Configuration file reading/writing
- Report generation and export
- Log file management

## Integration Test Patterns

### Real System Testing
```python
# ✅ Good: Test with real systems
@pytest.mark.asyncio
async def test_cache_integration():
    cache_manager = CacheManager()  # Real cache
    await cache_manager.initialize()
    
    # Test real operations
    await cache_manager.store(key, data)
    result = await cache_manager.retrieve(key)
    
    assert result == data
```

### End-to-End Data Flow
```python
# ✅ Good: Test complete data pipeline
@pytest.mark.asyncio
async def test_repository_analysis_pipeline():
    # 1. Fetch from GitHub API
    # 2. Process and analyze data
    # 3. Cache results
    # 4. Retrieve from cache
    # 5. Verify data integrity throughout
```

### Error Scenario Testing
```python
# ✅ Good: Test error conditions
@pytest.mark.asyncio
async def test_api_failure_handling():
    # Simulate network failure
    with patch('httpx.AsyncClient.get', side_effect=httpx.ConnectError):
        result = await github_client.get_repository("owner", "repo")
        # Verify graceful error handling
```

## Test Organization

### Directory Structure
```
tests/
├── unit/           # Fast, isolated tests with mocks
├── integration/    # Real system integration tests (local)
├── online/         # Real external API tests (free)
├── billable/       # Real external API tests (paid)
├── contract/       # API contract and schema tests
└── e2e/           # Full end-to-end user scenarios
```

### Test Naming Convention
- `test_*_integration.py` for integration tests
- `test_*_contract.py` for contract tests
- Clear, descriptive test method names that explain the scenario

### Test Categories
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_roundtrip_integration():
    """Integration test for cache data roundtrip."""

@pytest.mark.online
@pytest.mark.asyncio
async def test_github_api_real_data():
    """Online test with real GitHub API data."""

@pytest.mark.billable
@pytest.mark.asyncio
async def test_openai_integration():
    """Billable test with paid external API."""

@pytest.mark.contract
@pytest.mark.asyncio  
async def test_github_api_contract():
    """Contract test for GitHub API response format."""

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_analysis_workflow():
    """End-to-end test of complete analysis workflow."""
```

## Data Management in Tests

### Test Data Strategy
- Use realistic test data that matches production scenarios
- Include edge cases and boundary conditions
- Test with various data sizes and complexity levels

### Test Isolation
```python
@pytest.fixture
async def isolated_cache():
    """Provide isolated cache for each test."""
    cache_manager = CacheManager(db_path=":memory:")
    await cache_manager.initialize()
    yield cache_manager
    await cache_manager.close()
```

### Cleanup and Teardown
- Always clean up resources after tests
- Use fixtures for setup and teardown
- Ensure tests don't interfere with each other

## Performance Considerations

### Test Performance
- Integration tests should complete within reasonable time (< 30s each)
- Use timeouts to prevent hanging tests
- Parallelize tests where possible

### Resource Usage
- Monitor memory usage in long-running tests
- Clean up large objects and connections
- Use connection pooling for database tests

## CI/CD Integration

### Test Execution Strategy
```yaml
# Run different test types at different stages
stages:
  - unit-tests      # Fast feedback (< 2 minutes)
  - integration     # Medium feedback (< 10 minutes)  
  - contract        # Slower feedback (< 20 minutes)
  - e2e            # Full validation (< 60 minutes)
```

### Failure Handling
- Integration test failures should block deployment
- Provide clear error messages and debugging information
- Include logs and artifacts for failed tests

### Test Environment Management
- Use containerized test environments for consistency
- Provide test data seeding and cleanup scripts
- Maintain separate test databases/caches

## Debugging Integration Tests

### Logging and Observability
```python
@pytest.mark.integration
async def test_with_detailed_logging():
    # Enable detailed logging for debugging
    logging.getLogger('forklift').setLevel(logging.DEBUG)
    
    # Test operations with full logging
    result = await component_under_test()
    
    # Assertions with context
    assert result is not None, "Component returned None - check logs for details"
```

### Test Artifacts
- Capture logs, screenshots, and data dumps on failure
- Store test artifacts for post-mortem analysis
- Include timing and performance metrics

### Local Development
- Provide easy way to run integration tests locally
- Include setup scripts for test dependencies
- Document test environment requirements

## Common Anti-Patterns to Avoid

### Over-Mocking in Integration Tests
```python
# ❌ Bad: Too much mocking defeats the purpose
@patch('github_client.get')
@patch('cache_manager.store')
@patch('database.save')
def test_integration(mock_github, mock_cache, mock_db):
    # This is not an integration test!
```

### Testing Implementation Details
```python
# ❌ Bad: Testing internal implementation
def test_cache_uses_sqlite():
    assert isinstance(cache.db, sqlite3.Connection)

# ✅ Good: Testing behavior and contracts
async def test_cache_stores_and_retrieves_data():
    await cache.store("key", {"data": "value"})
    result = await cache.retrieve("key")
    assert result == {"data": "value"}
```

### Ignoring Test Flakiness
```python
# ❌ Bad: Ignoring flaky tests
@pytest.mark.flaky(reruns=3)  # Don't just retry!
def test_sometimes_fails():
    # Fix the root cause instead
```

### Not Testing Error Conditions
```python
# ❌ Bad: Only testing happy path
async def test_successful_api_call():
    result = await api_client.get_data()
    assert result is not None

# ✅ Good: Test error scenarios too
async def test_api_handles_rate_limiting():
    with patch('httpx.get', side_effect=httpx.HTTPStatusError(...)):
        result = await api_client.get_data()
        # Verify graceful error handling
```

## Integration Test Checklist

Before marking integration tests complete:
- [ ] Tests use real systems (no excessive mocking)
- [ ] Error scenarios are covered
- [ ] Data integrity is verified end-to-end
- [ ] Resource cleanup is implemented
- [ ] Tests are isolated and repeatable
- [ ] Performance is within acceptable bounds
- [ ] Logging provides debugging information
- [ ] Tests fail fast with clear error messages

## Maintenance and Evolution

### Test Maintenance
- Review and update tests when system behavior changes
- Remove obsolete tests that no longer provide value
- Refactor tests to improve clarity and maintainability

### Test Coverage Analysis
- Monitor integration test coverage separately from unit tests
- Identify gaps in integration testing
- Prioritize high-risk integration points

### Documentation
- Document test scenarios and their purpose
- Maintain troubleshooting guides for common test failures
- Keep test environment setup instructions current

Integration tests are an investment in system reliability. They catch issues that unit tests miss and provide confidence that components work together correctly in real-world scenarios.