---
inclusion: always
---

# Performance Guidelines

## Code Optimization Principles

### Performance Mindset
- Profile before optimizing - measure, don't guess
- Focus on algorithmic improvements before micro-optimizations
- Optimize for the common case, not edge cases
- Consider readability vs performance trade-offs
- Use appropriate data structures for the task

### Profiling and Measurement
```python
import cProfile
import time
from functools import wraps

def profile_function(func):
    """Decorator to profile function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__} took {end_time - start_time:.4f} seconds")
        return result
    return wrapper

# Use cProfile for detailed analysis
# python -m cProfile -o profile_output.prof your_script.py
```

### Algorithm Optimization
- Choose appropriate time complexity for your use case
- Use built-in functions and libraries when possible
- Consider space-time trade-offs
- Implement caching for expensive computations
- Use generators for memory-efficient iteration

## Resource Management

### Memory Management
- Use generators instead of lists for large datasets
- Implement proper cleanup of resources (files, connections)
- Monitor memory usage in long-running processes
- Use `__slots__` for classes with many instances
- Consider memory pooling for frequently created objects

```python
# Good: Generator for memory efficiency
def process_large_file(filename):
    with open(filename, 'r') as file:
        for line in file:
            yield process_line(line)

# Bad: Loading entire file into memory
# def process_large_file(filename):
#     with open(filename, 'r') as file:
#         return [process_line(line) for line in file.readlines()]
```

### Connection Management
- Implement connection pooling for databases and external services
- Use context managers for resource cleanup
- Set appropriate timeouts for network operations
- Reuse connections when possible
- Monitor connection pool health

```python
import asyncio
import aiohttp
from contextlib import asynccontextmanager

class HTTPClientManager:
    def __init__(self, max_connections=100):
        self.connector = aiohttp.TCPConnector(limit=max_connections)
        self.session = None
    
    @asynccontextmanager
    async def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(connector=self.connector)
        try:
            yield self.session
        finally:
            pass  # Keep session alive for reuse
    
    async def close(self):
        if self.session:
            await self.session.close()
```

### Async/Await Best Practices
- Use async/await for I/O-bound operations
- Avoid blocking operations in async functions
- Use `asyncio.gather()` for concurrent operations
- Implement proper error handling in async code
- Use connection pooling with async HTTP clients

```python
import asyncio
import aiohttp

async def fetch_multiple_urls(urls):
    """Fetch multiple URLs concurrently"""
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url(session, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

async def fetch_url(session, url):
    async with session.get(url) as response:
        return await response.text()
```

## Caching Strategies

### Cache Levels
- **Memory Cache**: Fast access, limited size (Redis, in-memory dicts)
- **Disk Cache**: Persistent, slower access (file system, SQLite)
- **Distributed Cache**: Shared across instances (Redis, Memcached)
- **CDN Cache**: Geographic distribution for static content

### Cache Implementation
```python
from functools import lru_cache
import time
from typing import Dict, Any, Optional

class TTLCache:
    """Time-to-live cache implementation"""
    def __init__(self, ttl_seconds: int = 300):
        self.cache: Dict[str, tuple] = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        self.cache[key] = (value, time.time())

# Use lru_cache for function memoization
@lru_cache(maxsize=128)
def expensive_computation(param):
    # Simulate expensive operation
    time.sleep(1)
    return param * 2
```

### Cache Invalidation
- Implement cache invalidation strategies
- Use cache tags for group invalidation
- Consider cache warming for critical data
- Monitor cache hit rates and effectiveness
- Implement cache versioning for schema changes

## Database Performance

### Query Optimization
- Use database indexes effectively
- Avoid N+1 query problems
- Use query analysis tools (EXPLAIN)
- Implement query result caching
- Use database connection pooling

```python
# Good: Batch loading to avoid N+1 queries
def get_users_with_posts(user_ids):
    users = User.objects.filter(id__in=user_ids).prefetch_related('posts')
    return {user.id: user for user in users}

# Bad: N+1 query problem
# def get_users_with_posts(user_ids):
#     users = {}
#     for user_id in user_ids:
#         user = User.objects.get(id=user_id)
#         user.posts = user.posts.all()  # Additional query for each user
#         users[user_id] = user
#     return users
```

### Database Connection Management
```python
import asyncpg
import asyncio

class DatabasePool:
    def __init__(self, database_url: str, min_size: int = 10, max_size: int = 20):
        self.database_url = database_url
        self.min_size = min_size
        self.max_size = max_size
        self.pool = None
    
    async def initialize(self):
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=self.min_size,
            max_size=self.max_size
        )
    
    async def execute_query(self, query: str, *args):
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)
```

## API Performance

### Response Optimization
- Implement response compression (gzip)
- Use appropriate HTTP caching headers
- Implement pagination for large result sets
- Use field selection to reduce payload size
- Consider GraphQL for flexible data fetching

### Rate Limiting and Throttling
```python
import time
from collections import defaultdict
from typing import Dict

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, identifier: str) -> bool:
        now = time.time()
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if now - req_time < self.window_seconds
        ]
        
        if len(self.requests[identifier]) < self.max_requests:
            self.requests[identifier].append(now)
            return True
        return False
```

## Monitoring and Metrics

### Performance Monitoring
- Track response times and throughput
- Monitor resource usage (CPU, memory, disk)
- Set up alerts for performance degradation
- Use APM tools for detailed performance insights
- Implement health checks for system components

### Key Performance Indicators
```python
import time
import psutil
from dataclasses import dataclass

@dataclass
class PerformanceMetrics:
    response_time: float
    cpu_usage: float
    memory_usage: float
    active_connections: int
    cache_hit_rate: float

def collect_metrics() -> PerformanceMetrics:
    return PerformanceMetrics(
        response_time=get_average_response_time(),
        cpu_usage=psutil.cpu_percent(),
        memory_usage=psutil.virtual_memory().percent,
        active_connections=get_active_connections(),
        cache_hit_rate=get_cache_hit_rate()
    )
```

### Performance Testing
- Include performance tests in your test suite
- Set performance benchmarks and SLAs
- Use load testing tools for capacity planning
- Test performance under different load conditions
- Monitor performance regressions in CI/CD

```python
import pytest
import time

def test_api_response_time():
    """Test that API responds within acceptable time"""
    start_time = time.time()
    response = client.get("/api/users")
    end_time = time.time()
    
    assert response.status_code == 200
    assert end_time - start_time < 0.5  # 500ms SLA

@pytest.mark.performance
def test_concurrent_requests():
    """Test system performance under concurrent load"""
    import concurrent.futures
    
    def make_request():
        return client.get("/api/health")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(100)]
        results = [future.result() for future in futures]
    
    success_rate = sum(1 for r in results if r.status_code == 200) / len(results)
    assert success_rate >= 0.95  # 95% success rate under load
```