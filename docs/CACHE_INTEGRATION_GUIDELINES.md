# Cache Integration Guidelines

## Overview

This document outlines best practices for integrating with the Forkscout caching system to prevent data serialization/deserialization issues.

## Core Principles

### 1. **Always Validate Before Caching**

```python
from forkscout.storage.cache_validation import validate_before_cache, CacheValidationError

# ✅ Good: Validate data before caching
try:
    validated_data = validate_before_cache(repo_data, Repository)
    await cache_manager.cache_repository_metadata(owner, repo, validated_data)
except CacheValidationError as e:
    logger.warning(f"Data validation failed, skipping cache: {e}")
    # Continue without caching
```

### 2. **Handle Cache Validation Failures Gracefully**

```python
# ✅ Good: Graceful fallback when cache validation fails
try:
    cached_data = await cache_manager.get_repository_metadata(owner, repo)
    if cached_data:
        # Validate cached data before using
        CacheValidator.validate_repository_reconstruction(cached_data["repository_data"])
        return reconstruct_from_cache(cached_data)
except CacheValidationError as e:
    logger.warning(f"Cache validation failed, falling back to API: {e}")
    # Fall back to fresh API call

# Fetch from API
return await fetch_from_api(owner, repo)
```

### 3. **Include All Required Fields in Cached Data**

```python
# ❌ Bad: Missing required fields
cached_repo_data = {
    "name": repo.name,
    "owner": repo.owner,
    # Missing: url, html_url, clone_url (required by Repository model)
}

# ✅ Good: Include all required fields
cached_repo_data = {
    "name": repo.name,
    "owner": repo.owner,
    "full_name": repo.full_name,
    "url": repo.url,
    "html_url": repo.html_url,
    "clone_url": repo.clone_url,
    # ... other fields
}
```

### 4. **Use Schema Versioning**

```python
from forkscout.storage.cache_validation import add_schema_version

# ✅ Good: Add schema version to cached data
data_to_cache = add_schema_version(repo_data, "1.0")
await cache_manager.cache_repository_metadata(owner, repo, data_to_cache)

# When retrieving, check compatibility
cached_data = await cache_manager.get_repository_metadata(owner, repo)
if cached_data and CacheValidator.ensure_cache_compatibility(cached_data, "1.0"):
    # Use cached data
else:
    # Schema mismatch, fetch fresh data
```

## Testing Requirements

### 1. **Integration Tests for Cache Roundtrips**

Every component that uses caching must have integration tests that verify:

```python
@pytest.mark.asyncio
async def test_cache_roundtrip():
    """Test that data can be cached and retrieved without loss."""
    # 1. Create original data
    original_data = create_test_data()
    
    # 2. Cache the data
    await cache_component(original_data)
    
    # 3. Retrieve from cache
    cached_data = await retrieve_from_cache()
    
    # 4. Verify data integrity
    assert_data_equivalent(original_data, cached_data)
```

### 2. **Contract Tests for Model Evolution**

```python
@pytest.mark.asyncio
async def test_handles_schema_evolution():
    """Test graceful handling of schema changes."""
    # 1. Create old-format cached data
    old_cached_data = create_old_format_data()
    await inject_into_cache(old_cached_data)
    
    # 2. Attempt to use with new schema
    result = await component_using_cache()
    
    # 3. Verify graceful fallback occurred
    assert result is not None  # Should not crash
    assert api_was_called()    # Should fall back to API
```

### 3. **Serialization Validation Tests**

```python
def test_model_serialization():
    """Test that model can be serialized and deserialized."""
    # 1. Create model instance
    model = MyModel(**test_data)
    
    # 2. Serialize to dict
    serialized = model.model_dump()
    
    # 3. Deserialize back to model
    deserialized = MyModel(**serialized)
    
    # 4. Verify equivalence
    assert model == deserialized
```

## Common Pitfalls to Avoid

### 1. **Missing Required Fields in Cache**

```python
# ❌ Problem: Repository model requires url, html_url, clone_url
repository = Repository(
    name=cached_data["name"],
    owner=cached_data["owner"],
    # Missing required URL fields!
)
```

**Solution**: Always include all required fields when caching.

### 2. **Not Handling Cache Validation Failures**

```python
# ❌ Problem: Cache validation failure crashes the application
cached_repo = Repository(**cached_data)  # May raise ValidationError
```

**Solution**: Wrap in try/catch and fall back to API.

### 3. **Ignoring Schema Evolution**

```python
# ❌ Problem: Old cached data breaks new code
cached_data = get_from_cache()
return NewModel(**cached_data)  # Fails if schema changed
```

**Solution**: Use schema versioning and compatibility checks.

### 4. **Not Testing Real Data Flow**

```python
# ❌ Problem: Unit tests use mocks, miss real serialization issues
@patch('cache_manager.get_data')
def test_component(mock_cache):
    mock_cache.return_value = {"perfect": "mock_data"}
    # Test passes but real cache data might be different!
```

**Solution**: Include integration tests with real cache operations.

## Pre-commit Checklist

Before committing code that uses caching:

- [ ] Added integration tests for cache roundtrip
- [ ] Added contract tests for schema evolution
- [ ] Validated all required fields are cached
- [ ] Added graceful fallback for cache failures
- [ ] Used schema versioning for cached data
- [ ] Ran `python scripts/check_model_serialization.py`
- [ ] Verified pre-commit hooks pass

## Monitoring and Debugging

### 1. **Enable Cache Validation Logging**

```python
import logging
logging.getLogger('forkscout.storage.cache_validation').setLevel(logging.DEBUG)
```

### 2. **Use Cache Statistics**

```python
# Monitor cache hit rates and validation failures
stats = await cache_manager.get_monitoring_metrics()
logger.info(f"Cache hit rate: {stats['cache_stats']['hit_rate']:.1%}")
```

### 3. **Add Validation Metrics**

```python
# Track validation failures
try:
    validate_cached_data(data, Model)
except CacheValidationError:
    metrics.increment('cache.validation.failures')
    raise
```

## Schema Migration Strategy

When evolving models:

1. **Increment schema version** in cached data
2. **Add compatibility checks** for old versions
3. **Provide migration functions** for old data
4. **Maintain backward compatibility** for at least one version
5. **Add deprecation warnings** for old schemas

```python
def migrate_cached_data(cached_data: dict) -> dict:
    """Migrate old cached data to new schema."""
    version = cached_data.get("_schema_version", "0.9")
    
    if version == "0.9":
        # Migrate from 0.9 to 1.0
        cached_data["new_required_field"] = "default_value"
        cached_data["_schema_version"] = "1.0"
    
    return cached_data
```