# Cache Integration Guidelines

## Core Principles for Cache Integration

### Always Validate Before Caching
- Use `validate_before_cache()` to ensure data can be reconstructed
- Include all required fields in cached data structures
- Add schema versioning to cached data for future compatibility

### Handle Cache Validation Failures Gracefully
- Wrap cache reconstruction in try/catch blocks
- Always provide fallback to fresh API calls when cache validation fails
- Log cache validation failures for monitoring

### Test Cache Integration End-to-End
- Write integration tests that exercise real cache serialization/deserialization
- Include contract tests for schema evolution scenarios
- Test with real data structures, not just mocks

## Required Testing Patterns

### Integration Tests for Cache Roundtrips
```python
@pytest.mark.asyncio
async def test_cache_roundtrip():
    # 1. Create original data with all required fields
    # 2. Cache the data through real cache system
    # 3. Retrieve from cache through real reconstruction
    # 4. Verify data integrity and no field loss
```

### Contract Tests for Model Evolution
```python
@pytest.mark.asyncio
async def test_handles_schema_evolution():
    # 1. Create old-format cached data
    # 2. Attempt to use with current schema
    # 3. Verify graceful fallback to API occurs
    # 4. Ensure no crashes or data corruption
```

### Serialization Validation
- Run `python scripts/check_model_serialization.py` before commits
- Validate that all Pydantic models can roundtrip through JSON
- Ensure required fields are properly defined and enforced

## Implementation Requirements

### Cache Data Structure
- Include ALL required fields from Pydantic models
- Add `_schema_version` field to all cached data
- Use `CacheValidator.validate_repository_reconstruction()` before reconstruction

### Error Handling
- Never let cache validation errors crash the application
- Always log cache validation failures with context
- Provide meaningful fallback behavior (usually fresh API call)

### Schema Evolution
- Increment schema version when changing cached data structure
- Provide migration functions for old cached data
- Maintain backward compatibility for at least one version

## Pre-commit Requirements

Before committing code that uses caching:
- [ ] Added integration tests for cache roundtrip
- [ ] Added contract tests for schema evolution  
- [ ] Validated all required fields are cached
- [ ] Added graceful fallback for cache failures
- [ ] Used schema versioning for cached data
- [ ] Ran model serialization validation script
- [ ] Verified pre-commit hooks pass

## Common Pitfalls to Avoid

### Missing Required Fields
```python
# ❌ Bad: Missing required URL fields
repository = Repository(
    name=cached_data["name"],
    owner=cached_data["owner"],
    # Missing: url, html_url, clone_url
)

# ✅ Good: Include all required fields
repository = Repository(
    name=cached_data["name"],
    owner=cached_data["owner"],
    full_name=cached_data["full_name"],
    url=cached_data["url"],
    html_url=cached_data["html_url"],
    clone_url=cached_data["clone_url"],
)
```

### Not Handling Validation Failures
```python
# ❌ Bad: Let validation errors crash
cached_repo = Repository(**cached_data)

# ✅ Good: Handle validation failures gracefully
try:
    cached_repo = Repository(**cached_data)
except ValidationError as e:
    logger.warning(f"Cache validation failed: {e}")
    return await fetch_from_api()
```

### Testing Only with Mocks
```python
# ❌ Bad: Only mock tests miss real serialization issues
@patch('cache_manager.get_data')
def test_component(mock_cache):
    mock_cache.return_value = {"perfect": "mock_data"}

# ✅ Good: Test real cache operations
async def test_component_with_real_cache():
    cache_manager = CacheManager()
    await cache_manager.initialize()
    # Test with real cache operations
```

## Monitoring and Debugging

### Enable Cache Validation Logging
```python
import logging
logging.getLogger('forklift.storage.cache_validation').setLevel(logging.DEBUG)
```

### Monitor Cache Performance
- Track cache hit rates and validation failure rates
- Alert on high validation failure rates (indicates schema issues)
- Monitor cache size and cleanup effectiveness

### Add Validation Metrics
```python
try:
    validate_cached_data(data, Model)
except CacheValidationError:
    metrics.increment('cache.validation.failures')
    raise
```

## Integration with Development Workflow

### Pre-commit Hooks
- Cache integration tests run automatically on relevant file changes
- Model serialization validation runs on model changes
- Prevents cache-breaking changes from being committed

### CI/CD Pipeline
- Full cache integration test suite runs on all PRs
- Contract tests verify backward compatibility
- Performance tests ensure cache doesn't degrade over time

### Code Review Checklist
- Verify all cached data includes required fields
- Check for graceful error handling in cache operations
- Ensure integration tests cover new cache usage
- Validate schema versioning is used appropriately

This guidance ensures that cache integration issues are caught early and prevented through systematic testing and validation practices.