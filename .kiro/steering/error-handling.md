---
inclusion: always
---

# Error Handling and Logging Guidelines

## Exception Handling Principles

### Exception Hierarchy
- Use specific exception types rather than generic ones
- Create custom exceptions for domain-specific errors
- Inherit from appropriate base exception classes
- Include meaningful error messages and context

```python
class ForkliftError(Exception):
    """Base exception for Forklift application"""
    pass

class GitHubAPIError(ForkliftError):
    """Raised when GitHub API operations fail"""
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data

class RepositoryNotFoundError(GitHubAPIError):
    """Raised when a repository cannot be found"""
    pass

class RateLimitExceededError(GitHubAPIError):
    """Raised when GitHub API rate limit is exceeded"""
    pass
```

### Error Handling Patterns
- Catch specific exceptions, not generic ones
- Handle errors at the appropriate level
- Provide meaningful error messages to users
- Log detailed error information for debugging
- Implement graceful degradation when possible

```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

async def fetch_repository_data(owner: str, repo: str) -> Optional[dict]:
    """Fetch repository data with proper error handling"""
    try:
        async with github_client.get_repository(owner, repo) as response:
            if response.status == 404:
                raise RepositoryNotFoundError(f"Repository {owner}/{repo} not found")
            elif response.status == 403:
                raise RateLimitExceededError("GitHub API rate limit exceeded")
            elif response.status != 200:
                raise GitHubAPIError(f"GitHub API error: {response.status}")
            
            return await response.json()
            
    except aiohttp.ClientError as e:
        logger.error(f"Network error fetching {owner}/{repo}: {e}")
        raise GitHubAPIError(f"Network error: {e}") from e
    except asyncio.TimeoutError as e:
        logger.error(f"Timeout fetching {owner}/{repo}")
        raise GitHubAPIError("Request timeout") from e
```

### Graceful Degradation
- Continue processing when individual operations fail
- Provide fallback mechanisms where appropriate
- Return partial results with error indicators
- Implement circuit breaker patterns for external services

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class AnalysisResult:
    successful_forks: List[dict]
    failed_forks: List[dict]
    errors: List[str]

async def analyze_all_forks(forks: List[dict]) -> AnalysisResult:
    """Analyze all forks with graceful error handling"""
    successful = []
    failed = []
    errors = []
    
    for fork in forks:
        try:
            result = await analyze_fork(fork)
            successful.append(result)
        except Exception as e:
            logger.warning(f"Failed to analyze fork {fork['full_name']}: {e}")
            failed.append(fork)
            errors.append(f"Fork {fork['full_name']}: {str(e)}")
    
    return AnalysisResult(successful, failed, errors)
```

## Logging Standards

### Logging Configuration
- Use structured logging with consistent formats
- Configure different log levels appropriately
- Include contextual information in log messages
- Use correlation IDs for request tracing
- Separate application logs from access logs

```python
import logging
import json
import uuid
from datetime import datetime
from typing import Any, Dict

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'correlation_id'):
            log_entry['correlation_id'] = record.correlation_id
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
            
        return json.dumps(log_entry)

# Configure logging
def setup_logging(log_level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('app.log')
        ]
    )
    
    # Set structured formatter for file handler
    file_handler = logging.getLogger().handlers[1]
    file_handler.setFormatter(StructuredFormatter())
```

### Logging Best Practices
- Log at appropriate levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Include relevant context in log messages
- Never log sensitive information (passwords, tokens, PII)
- Use correlation IDs to trace requests across services
- Log both successful operations and errors

```python
import logging
from contextvars import ContextVar

logger = logging.getLogger(__name__)
correlation_id: ContextVar[str] = ContextVar('correlation_id')

class CorrelationFilter(logging.Filter):
    """Add correlation ID to log records"""
    
    def filter(self, record):
        record.correlation_id = correlation_id.get('unknown')
        return True

# Add filter to logger
logger.addFilter(CorrelationFilter())

async def process_repository(repo_url: str):
    """Example of contextual logging"""
    # Set correlation ID for this request
    correlation_id.set(str(uuid.uuid4()))
    
    logger.info(f"Starting repository analysis", extra={
        'repo_url': repo_url,
        'operation': 'analyze_repository'
    })
    
    try:
        result = await analyze_repository(repo_url)
        logger.info(f"Repository analysis completed", extra={
            'repo_url': repo_url,
            'forks_found': len(result.forks),
            'features_identified': len(result.features)
        })
        return result
        
    except Exception as e:
        logger.error(f"Repository analysis failed", extra={
            'repo_url': repo_url,
            'error': str(e),
            'error_type': type(e).__name__
        }, exc_info=True)
        raise
```

### Security-Conscious Logging
- Never log passwords, API keys, or other secrets
- Hash or mask sensitive data in logs
- Be careful with user-generated content in logs
- Implement log sanitization for PII
- Use separate logs for security events

```python
import hashlib
import re
from typing import Any

def sanitize_for_logging(data: Any) -> Any:
    """Sanitize data before logging to remove sensitive information"""
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if key.lower() in ['password', 'token', 'secret', 'key']:
                sanitized[key] = '[REDACTED]'
            elif key.lower() in ['email', 'user_id']:
                # Hash PII for privacy
                sanitized[key] = hashlib.sha256(str(value).encode()).hexdigest()[:8]
            else:
                sanitized[key] = sanitize_for_logging(value)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_for_logging(item) for item in data]
    elif isinstance(data, str):
        # Remove potential sensitive patterns
        data = re.sub(r'token=[\w-]+', 'token=[REDACTED]', data)
        data = re.sub(r'password=[\w-]+', 'password=[REDACTED]', data)
        return data
    return data

def log_user_action(user_id: str, action: str, details: dict):
    """Log user actions with sanitized data"""
    sanitized_details = sanitize_for_logging(details)
    logger.info(f"User action performed", extra={
        'user_id_hash': hashlib.sha256(user_id.encode()).hexdigest()[:8],
        'action': action,
        'details': sanitized_details
    })
```

## Error Recovery and Resilience

### Retry Logic
- Implement exponential backoff for transient failures
- Set maximum retry limits to prevent infinite loops
- Use jitter to avoid thundering herd problems
- Distinguish between retryable and non-retryable errors

```python
import asyncio
import random
from typing import Callable, Any, Type

async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,)
) -> Any:
    """Retry function with exponential backoff"""
    
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except retryable_exceptions as e:
            if attempt == max_retries:
                logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}")
                raise
            
            delay = min(base_delay * (backoff_factor ** attempt), max_delay)
            if jitter:
                delay *= (0.5 + random.random() * 0.5)  # Add 0-50% jitter
            
            logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}, retrying in {delay:.2f}s: {e}")
            await asyncio.sleep(delay)
```

### Circuit Breaker Pattern
- Prevent cascading failures in distributed systems
- Automatically recover when services become healthy
- Provide fallback mechanisms during outages

```python
import time
from enum import Enum
from typing import Callable, Any

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info("Circuit breaker reset to CLOSED")
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
```

## Monitoring and Alerting

### Error Monitoring
- Track error rates and patterns
- Set up alerts for critical errors
- Monitor error trends over time
- Implement error budgets and SLAs

```python
from dataclasses import dataclass
from typing import Dict, List
import time

@dataclass
class ErrorMetrics:
    total_requests: int
    error_count: int
    error_rate: float
    error_types: Dict[str, int]
    recent_errors: List[dict]

class ErrorMonitor:
    def __init__(self, window_size: int = 3600):  # 1 hour window
        self.window_size = window_size
        self.errors = []
        self.requests = []
    
    def record_request(self, success: bool, error_type: str = None):
        now = time.time()
        self.requests.append(now)
        
        if not success:
            self.errors.append({
                'timestamp': now,
                'error_type': error_type
            })
        
        # Clean old data
        cutoff = now - self.window_size
        self.requests = [r for r in self.requests if r > cutoff]
        self.errors = [e for e in self.errors if e['timestamp'] > cutoff]
    
    def get_metrics(self) -> ErrorMetrics:
        total_requests = len(self.requests)
        error_count = len(self.errors)
        error_rate = error_count / total_requests if total_requests > 0 else 0
        
        error_types = {}
        for error in self.errors:
            error_type = error.get('error_type', 'unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return ErrorMetrics(
            total_requests=total_requests,
            error_count=error_count,
            error_rate=error_rate,
            error_types=error_types,
            recent_errors=self.errors[-10:]  # Last 10 errors
        )
```

### Health Checks
- Implement comprehensive health checks
- Monitor dependencies and external services
- Provide detailed health status information

```python
from typing import Dict, Any
import asyncio

class HealthChecker:
    def __init__(self):
        self.checks = {}
    
    def add_check(self, name: str, check_func: Callable):
        self.checks[name] = check_func
    
    async def run_health_checks(self) -> Dict[str, Any]:
        results = {}
        overall_healthy = True
        
        for name, check_func in self.checks.items():
            try:
                start_time = time.time()
                result = await check_func()
                duration = time.time() - start_time
                
                results[name] = {
                    'status': 'healthy',
                    'duration_ms': round(duration * 1000, 2),
                    'details': result
                }
            except Exception as e:
                overall_healthy = False
                results[name] = {
                    'status': 'unhealthy',
                    'error': str(e),
                    'error_type': type(e).__name__
                }
        
        return {
            'overall_status': 'healthy' if overall_healthy else 'unhealthy',
            'checks': results,
            'timestamp': time.time()
        }

# Example health checks
async def check_database():
    # Check database connectivity
    await database.execute("SELECT 1")
    return "Database connection OK"

async def check_github_api():
    # Check GitHub API connectivity
    response = await github_client.get("/rate_limit")
    return f"GitHub API OK, rate limit: {response['rate']['remaining']}"

# Setup health checker
health_checker = HealthChecker()
health_checker.add_check('database', check_database)
health_checker.add_check('github_api', check_github_api)
```