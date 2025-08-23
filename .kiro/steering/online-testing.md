# Online Testing Guidelines

## Core Philosophy

Always generate online tests that use real external data alongside mocked tests. Online tests catch issues that mocks cannot, including API changes, rate limiting, authentication issues, and real-world data variations.

## Test Categories

### Online Tests (Free External Requests)
- Tests that use free external APIs or services
- GitHub API calls within rate limits
- Public repository data access
- Free tier service integrations
- Run automatically in CI/CD pipeline

### Billable Tests (Paid External Requests)  
- Tests that consume paid API quotas or services
- Premium GitHub API features
- Paid AI/ML service calls (OpenAI, etc.)
- Cloud service operations with costs
- Run manually or on-demand only

## Test Organization Structure

```
tests/
├── unit/              # Fast, isolated tests with mocks
├── integration/       # Real system integration (local)
├── online/           # Real external API tests (free)
├── billable/         # Real external API tests (paid)
├── contract/         # API contract and schema tests
└── e2e/             # Full end-to-end scenarios
```

## Online Test Implementation

### Free Online Tests
```python
@pytest.mark.online
@pytest.mark.asyncio
async def test_github_api_real_repository():
    """Test GitHub API with real public repository."""
    github_client = GitHubClient(token=os.getenv('GITHUB_TOKEN'))
    
    # Use well-known public repository
    repo = await github_client.get_repository('octocat', 'Hello-World')
    
    assert repo.owner == 'octocat'
    assert repo.name == 'Hello-World'
    assert repo.html_url == 'https://github.com/octocat/Hello-World'
    
    # Verify real data structure matches our models
    assert isinstance(repo.created_at, datetime)
    assert repo.stars >= 0  # Real data validation
```

### Billable Tests
```python
@pytest.mark.billable
@pytest.mark.asyncio
async def test_openai_commit_explanation():
    """Test OpenAI API for commit explanation (billable)."""
    if not os.getenv('OPENAI_API_KEY'):
        pytest.skip("OpenAI API key not available")
    
    explanation_engine = CommitExplanationEngine()
    
    # Test with real commit data
    commit_data = {
        'message': 'feat: add user authentication system',
        'files': ['auth.py', 'models/user.py', 'tests/test_auth.py']
    }
    
    explanation = await explanation_engine.explain_commit(commit_data)
    
    assert explanation is not None
    assert len(explanation.summary) > 0
    assert explanation.impact_assessment is not None
```

## Test Execution Strategy

### Automatic Execution (CI/CD)
```yaml
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
markers = [
    "unit: Fast unit tests with mocks",
    "integration: Integration tests with real local systems", 
    "online: Online tests with free external APIs",
    "billable: Billable tests with paid external APIs",
    "contract: API contract tests",
    "e2e: End-to-end tests"
]

# Default test run (excludes billable)
addopts = "-m 'not billable'"
```

### Manual Execution Commands
```bash
# Run all tests except billable
uv run pytest -m "not billable"

# Run only online tests (free external APIs)
uv run pytest -m "online"

# Run billable tests manually
uv run pytest -m "billable" --tb=short

# Run specific billable test
uv run pytest tests/billable/test_openai_integration.py -v

# Run all tests including billable (full validation)
uv run pytest --tb=short
```

## Environment Configuration

### Test Environment Variables
```bash
# .env.test
GITHUB_TOKEN=ghp_your_token_here
OPENAI_API_KEY=sk-your-key-here  # Only for billable tests
TEST_MODE=online  # online, offline, billable
```

### Configuration Management
```python
# conftest.py
import pytest
import os

def pytest_configure(config):
    """Configure test environment based on markers."""
    if config.getoption("-m") and "billable" in config.getoption("-m"):
        # Ensure billable test environment is configured
        required_vars = ['OPENAI_API_KEY', 'GITHUB_TOKEN']
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            pytest.exit(f"Billable tests require: {', '.join(missing)}")

@pytest.fixture
def github_client_online():
    """Real GitHub client for online tests."""
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        pytest.skip("GitHub token required for online tests")
    return GitHubClient(token)

@pytest.fixture  
def openai_client_billable():
    """Real OpenAI client for billable tests."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        pytest.skip("OpenAI API key required for billable tests")
    return OpenAIClient(api_key)
```

## Online Test Patterns

### Real Data Validation
```python
@pytest.mark.online
@pytest.mark.asyncio
async def test_repository_data_structure():
    """Validate real GitHub data matches our models."""
    github_client = GitHubClient(token=os.getenv('GITHUB_TOKEN'))
    
    # Test with multiple real repositories
    test_repos = [
        ('microsoft', 'vscode'),
        ('facebook', 'react'), 
        ('torvalds', 'linux')
    ]
    
    for owner, name in test_repos:
        repo = await github_client.get_repository(owner, name)
        
        # Validate real data structure
        assert repo.owner == owner
        assert repo.name == name
        assert repo.html_url.startswith('https://github.com/')
        assert isinstance(repo.stars, int)
        assert repo.stars >= 0
        
        # Test serialization with real data
        repo_dict = repo.model_dump()
        reconstructed = Repository(**repo_dict)
        assert reconstructed == repo
```

### Rate Limiting and Error Handling
```python
@pytest.mark.online
@pytest.mark.asyncio
async def test_github_rate_limiting():
    """Test rate limiting behavior with real API."""
    github_client = GitHubClient(token=os.getenv('GITHUB_TOKEN'))
    
    # Check current rate limit
    rate_limit = await github_client.get_rate_limit()
    initial_remaining = rate_limit.remaining
    
    # Make a real API call
    await github_client.get_repository('octocat', 'Hello-World')
    
    # Verify rate limit was consumed
    new_rate_limit = await github_client.get_rate_limit()
    assert new_rate_limit.remaining < initial_remaining
```

### API Contract Validation
```python
@pytest.mark.online
@pytest.mark.contract
@pytest.mark.asyncio
async def test_github_api_contract():
    """Validate GitHub API response format hasn't changed."""
    github_client = GitHubClient(token=os.getenv('GITHUB_TOKEN'))
    
    # Get raw API response
    response = await github_client._make_request('GET', '/repos/octocat/Hello-World')
    
    # Validate expected fields are present
    required_fields = [
        'id', 'name', 'full_name', 'owner', 'html_url', 
        'clone_url', 'stargazers_count', 'forks_count'
    ]
    
    for field in required_fields:
        assert field in response, f"GitHub API missing required field: {field}"
    
    # Validate field types
    assert isinstance(response['id'], int)
    assert isinstance(response['stargazers_count'], int)
    assert isinstance(response['html_url'], str)
```

## Billable Test Management

### Cost Control
```python
@pytest.mark.billable
@pytest.mark.asyncio
async def test_openai_with_cost_control():
    """Test OpenAI API with cost controls."""
    # Limit test to small requests
    max_tokens = 100  # Keep costs low
    
    client = OpenAIClient(api_key=os.getenv('OPENAI_API_KEY'))
    
    response = await client.complete(
        prompt="Explain this commit: 'fix: resolve null pointer exception'",
        max_tokens=max_tokens
    )
    
    assert response is not None
    assert len(response.text) > 0
    
    # Verify cost controls worked
    assert response.usage.total_tokens <= max_tokens
```

### Billable Test Documentation
```python
@pytest.mark.billable
@pytest.mark.asyncio
async def test_expensive_ai_analysis():
    """
    Test comprehensive AI analysis (BILLABLE - ~$0.10 per run).
    
    This test validates the full AI explanation pipeline with real data.
    Cost estimate: $0.05-0.15 depending on commit complexity.
    
    Run manually: pytest tests/billable/test_ai_analysis.py::test_expensive_ai_analysis
    """
    # Implementation with cost tracking
```

## CI/CD Integration

### GitHub Actions Configuration
```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run unit tests
        run: uv run pytest -m "unit" --cov=src

  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run integration tests
        run: uv run pytest -m "integration"

  online-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Run online tests
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: uv run pytest -m "online"

  billable-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'workflow_dispatch'  # Manual trigger only
    steps:
      - uses: actions/checkout@v4
      - name: Run billable tests
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: uv run pytest -m "billable" --tb=short
```

## Test Data Management

### Stable Test Repositories
```python
# Use stable, well-known repositories for consistent testing
STABLE_TEST_REPOS = [
    ('octocat', 'Hello-World'),      # GitHub's official test repo
    ('microsoft', 'vscode'),         # Large, active project
    ('python', 'cpython'),           # Python language repo
    ('torvalds', 'linux'),           # Linux kernel
]

@pytest.mark.online
@pytest.mark.parametrize("owner,name", STABLE_TEST_REPOS)
async def test_repository_analysis(owner, name, github_client_online):
    """Test repository analysis with stable test repositories."""
    repo = await github_client_online.get_repository(owner, name)
    assert repo is not None
    assert repo.owner == owner
    assert repo.name == name
```

### Test Data Validation
```python
@pytest.mark.online
@pytest.mark.asyncio
async def test_real_data_edge_cases():
    """Test with real repositories that have edge cases."""
    github_client = GitHubClient(token=os.getenv('GITHUB_TOKEN'))
    
    # Test repositories with various characteristics
    test_cases = [
        ('octocat', 'Hello-World'),     # Simple repository
        ('microsoft', 'vscode'),        # Large repository
        ('gist', 'gist'),              # Repository with special name
    ]
    
    for owner, name in test_cases:
        repo = await github_client.get_repository(owner, name)
        
        # Validate data integrity with real edge cases
        assert repo.full_name == f"{owner}/{name}"
        assert repo.html_url == f"https://github.com/{owner}/{name}"
        
        # Test serialization with real data variations
        validate_repository_serialization(repo)
```

## Monitoring and Reporting

### Test Execution Tracking
```python
# Track online test execution and costs
@pytest.fixture(autouse=True)
def track_billable_usage(request):
    """Track billable test usage."""
    if 'billable' in request.keywords:
        start_time = time.time()
        yield
        duration = time.time() - start_time
        
        # Log billable test execution
        logger.info(f"Billable test {request.node.name} took {duration:.2f}s")
        
        # Could integrate with cost tracking service
        # cost_tracker.record_test_execution(request.node.name, duration)
```

### Test Result Analysis
```python
@pytest.mark.online
@pytest.mark.asyncio
async def test_api_response_time():
    """Monitor API response times in online tests."""
    github_client = GitHubClient(token=os.getenv('GITHUB_TOKEN'))
    
    start_time = time.time()
    repo = await github_client.get_repository('octocat', 'Hello-World')
    response_time = time.time() - start_time
    
    assert repo is not None
    assert response_time < 5.0  # API should respond within 5 seconds
    
    # Log performance metrics
    logger.info(f"GitHub API response time: {response_time:.2f}s")
```

## Mock Data Generation from Real Data

### Use Online Tests to Generate Accurate Mocks
```python
@pytest.mark.online
@pytest.mark.asyncio
async def test_capture_real_data_for_mocks():
    """Capture real GitHub data to generate accurate mock tests."""
    github_client = GitHubClient(token=os.getenv('GITHUB_TOKEN'))
    
    # Fetch real data
    real_repo = await github_client.get_repository('octocat', 'Hello-World')
    
    # Use real data structure for mock generation
    mock_data = {
        'id': real_repo.id,
        'owner': 'test_owner',  # Anonymize but keep structure
        'name': 'test_repo',
        'full_name': 'test_owner/test_repo',
        'html_url': 'https://github.com/test_owner/test_repo',
        'stargazers_count': real_repo.stargazers_count,  # Real value patterns
        'created_at': real_repo.created_at.isoformat(),  # Real timestamp format
        # ... preserve all real data patterns
    }
    
    # Save for use in unit tests
    save_mock_fixture('realistic_github_repo', mock_data)
```

### Real Data Validation for Mocks
- Always derive mock data from real API responses
- Capture edge cases and variations from real data
- Validate mock data matches real API schemas
- Update mocks periodically from fresh real data

## Best Practices Summary

### Always Include Online Tests
- Every external API integration must have online tests
- Use stable, public test data sources
- Validate real data structure matches models
- Test error conditions with real APIs
- **Generate mock data from real online test responses**

### Separate Billable Tests
- Mark all paid API tests with `@pytest.mark.billable`
- Include cost estimates in test documentation
- Run billable tests manually or on-demand only
- Implement cost controls and limits

### Maintain Test Reliability
- Use stable test repositories and data sources
- Handle rate limiting and API quotas gracefully
- Provide clear error messages for missing credentials
- Monitor test execution times and success rates
- **Keep mock data current with real data patterns**

### Integration with Development Workflow
- Online tests run automatically on main branch
- Billable tests require manual trigger
- Pre-commit hooks exclude billable tests
- CI/CD pipeline separates test categories appropriately
- **Mock tests use data structures captured from online tests**

This approach ensures comprehensive testing with real external data while managing costs and maintaining development velocity. Mock tests remain accurate by being derived from real data captured through online tests.