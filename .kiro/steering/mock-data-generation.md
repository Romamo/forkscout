# Mock Data Generation Guidelines

## Core Philosophy

Always use real data to generate mock tests. Mock data should be derived from actual API responses, real database records, and genuine system outputs to ensure tests reflect real-world scenarios accurately.

## Real Data First Approach

### Capture Real Data for Mock Generation
```python
# ✅ Good: Generate mocks from real API responses
@pytest.mark.online
@pytest.mark.asyncio
async def test_capture_github_repository_data():
    """Capture real GitHub data to generate accurate mocks."""
    github_client = GitHubClient(token=os.getenv('GITHUB_TOKEN'))
    
    # Fetch real repository data
    real_repo = await github_client.get_repository('octocat', 'Hello-World')
    
    # Save real data structure for mock generation
    real_data = real_repo.model_dump()
    
    # Use this data to create accurate mocks
    mock_repo_data = {
        'id': 1296269,  # Real GitHub ID format
        'owner': 'octocat',
        'name': 'Hello-World', 
        'full_name': 'octocat/Hello-World',
        'html_url': 'https://github.com/octocat/Hello-World',
        'clone_url': 'https://github.com/octocat/Hello-World.git',
        'stargazers_count': 2547,  # Real star count (will vary)
        'forks_count': 1325,       # Real fork count (will vary)
        'created_at': '2011-01-26T19:01:12Z',  # Real timestamp format
        'updated_at': '2024-01-15T10:30:45Z',  # Real timestamp format
        # ... other fields from real data
    }
    
    return mock_repo_data
```

### Mock Data Validation Against Real Data
```python
def create_realistic_repository_mock():
    """Create repository mock based on real GitHub data patterns."""
    # Based on analysis of real GitHub repositories
    return {
        'id': 1296269,  # Real GitHub ID (7-8 digits typical)
        'owner': 'octocat',
        'name': 'Hello-World',
        'full_name': 'octocat/Hello-World',
        'description': 'My first repository on GitHub!',  # Real description
        'html_url': 'https://github.com/octocat/Hello-World',
        'clone_url': 'https://github.com/octocat/Hello-World.git',
        'ssh_url': 'git@github.com:octocat/Hello-World.git',
        'stargazers_count': 2547,
        'forks_count': 1325,
        'watchers_count': 2547,  # Often equals stargazers_count
        'open_issues_count': 0,
        'size': 108,  # KB, realistic size
        'default_branch': 'master',  # Real default branch
        'language': 'C',  # Real primary language
        'topics': [],  # Often empty for older repos
        'license': {
            'key': 'mit',
            'name': 'MIT License',
            'spdx_id': 'MIT'
        },
        'private': False,
        'fork': False,
        'archived': False,
        'disabled': False,
        'created_at': '2011-01-26T19:01:12Z',
        'updated_at': '2024-01-15T10:30:45Z',
        'pushed_at': '2011-01-26T19:14:43Z'
    }

@pytest.fixture
def mock_github_repository():
    """Provide realistic repository mock based on real data."""
    return create_realistic_repository_mock()
```

## Data Collection Strategies

### API Response Recording
```python
import json
from pathlib import Path

class RealDataRecorder:
    """Record real API responses for mock generation."""
    
    def __init__(self, output_dir: str = "tests/fixtures/real_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def record_github_repository(self, owner: str, name: str):
        """Record real GitHub repository data."""
        github_client = GitHubClient(token=os.getenv('GITHUB_TOKEN'))
        
        # Fetch real data
        repo = await github_client.get_repository(owner, name)
        languages = await github_client.get_repository_languages(owner, name)
        topics = await github_client.get_repository_topics(owner, name)
        
        # Record complete data structure
        real_data = {
            'repository': repo.model_dump(),
            'languages': languages,
            'topics': topics,
            'recorded_at': datetime.utcnow().isoformat(),
            'source': f'GitHub API - {owner}/{name}'
        }
        
        # Save to fixture file
        fixture_file = self.output_dir / f"github_repo_{owner}_{name}.json"
        with open(fixture_file, 'w') as f:
            json.dump(real_data, f, indent=2, default=str)
        
        return real_data

# Usage in test setup
@pytest.mark.online
@pytest.mark.asyncio
async def test_record_real_data_for_mocks():
    """Record real data to generate accurate mocks."""
    recorder = RealDataRecorder()
    
    # Record data from various repository types
    test_repos = [
        ('octocat', 'Hello-World'),      # Simple, old repository
        ('microsoft', 'vscode'),         # Large, active repository  
        ('python', 'cpython'),           # Language repository
        ('facebook', 'react'),           # Popular frontend library
    ]
    
    for owner, name in test_repos:
        await recorder.record_github_repository(owner, name)
```

### Mock Generation from Real Data
```python
def generate_mock_from_real_data(real_data_file: str) -> dict:
    """Generate mock data from recorded real data."""
    with open(real_data_file, 'r') as f:
        real_data = json.load(f)
    
    # Extract patterns from real data
    repo_data = real_data['repository']
    
    # Create mock with realistic variations
    mock_data = {
        'id': repo_data['id'] + 1000,  # Vary ID but keep format
        'owner': 'test_owner',
        'name': 'test_repo',
        'full_name': 'test_owner/test_repo',
        'description': repo_data['description'],  # Use real description pattern
        'html_url': 'https://github.com/test_owner/test_repo',
        'clone_url': 'https://github.com/test_owner/test_repo.git',
        'stargazers_count': max(0, repo_data['stargazers_count'] - 100),
        'forks_count': max(0, repo_data['forks_count'] - 50),
        'language': repo_data['language'],  # Use real language
        'topics': repo_data['topics'][:2],  # Use subset of real topics
        'license': repo_data['license'],    # Use real license structure
        'created_at': repo_data['created_at'],  # Use real timestamp format
        'updated_at': repo_data['updated_at'],
        # Preserve all real data structure patterns
    }
    
    return mock_data

@pytest.fixture
def realistic_repository_mock():
    """Generate repository mock from real data patterns."""
    return generate_mock_from_real_data('tests/fixtures/real_data/github_repo_octocat_Hello-World.json')
```

## Mock Data Validation

### Validate Mocks Against Real Data Schemas
```python
def validate_mock_data_structure(mock_data: dict, real_data_schema: dict):
    """Validate that mock data matches real data structure."""
    
    # Check all required fields are present
    for field in real_data_schema.get('required_fields', []):
        assert field in mock_data, f"Mock missing required field: {field}"
    
    # Check field types match real data
    for field, expected_type in real_data_schema.get('field_types', {}).items():
        if field in mock_data:
            actual_type = type(mock_data[field])
            assert actual_type == expected_type, f"Field {field} type mismatch: expected {expected_type}, got {actual_type}"
    
    # Check value ranges match real data patterns
    for field, (min_val, max_val) in real_data_schema.get('value_ranges', {}).items():
        if field in mock_data and isinstance(mock_data[field], (int, float)):
            value = mock_data[field]
            assert min_val <= value <= max_val, f"Field {field} value {value} outside realistic range [{min_val}, {max_val}]"

@pytest.fixture
def github_repository_schema():
    """Schema derived from analysis of real GitHub repositories."""
    return {
        'required_fields': [
            'id', 'owner', 'name', 'full_name', 'html_url', 'clone_url',
            'stargazers_count', 'forks_count', 'created_at', 'updated_at'
        ],
        'field_types': {
            'id': int,
            'owner': str,
            'name': str,
            'stargazers_count': int,
            'forks_count': int,
            'private': bool,
            'fork': bool,
        },
        'value_ranges': {
            'stargazers_count': (0, 500000),  # Based on real GitHub data
            'forks_count': (0, 100000),
            'size': (0, 10000000),  # KB
        }
    }

def test_mock_data_realism(realistic_repository_mock, github_repository_schema):
    """Test that mock data matches real data patterns."""
    validate_mock_data_structure(realistic_repository_mock, github_repository_schema)
```

## Edge Case Generation from Real Data

### Capture Real Edge Cases
```python
@pytest.mark.online
@pytest.mark.asyncio
async def test_capture_real_edge_cases():
    """Capture real edge cases for mock generation."""
    github_client = GitHubClient(token=os.getenv('GITHUB_TOKEN'))
    
    # Repositories with interesting edge cases
    edge_case_repos = [
        ('gist', 'gist'),                    # Repository name same as owner
        ('microsoft', 'MS-DOS'),             # Repository with hyphens
        ('torvalds', 'linux'),               # Very large repository
        ('octocat', 'linguist'),             # Repository with many languages
        ('github', 'gitignore'),             # Template repository
    ]
    
    edge_cases = {}
    
    for owner, name in edge_case_repos:
        try:
            repo = await github_client.get_repository(owner, name)
            languages = await github_client.get_repository_languages(owner, name)
            
            # Identify interesting characteristics
            characteristics = {
                'has_hyphen_in_name': '-' in repo.name,
                'owner_equals_name': repo.owner.lower() == repo.name.lower(),
                'very_large': repo.size > 1000000,  # > 1GB
                'many_languages': len(languages) > 10,
                'very_popular': repo.stargazers_count > 100000,
                'template_repo': repo.is_template if hasattr(repo, 'is_template') else False,
            }
            
            edge_cases[f"{owner}/{name}"] = {
                'data': repo.model_dump(),
                'languages': languages,
                'characteristics': characteristics
            }
            
        except Exception as e:
            print(f"Could not fetch {owner}/{name}: {e}")
    
    return edge_cases

def create_edge_case_mocks(edge_cases: dict) -> list:
    """Create mock data for various edge cases based on real data."""
    mocks = []
    
    for repo_name, data in edge_cases.items():
        characteristics = data['characteristics']
        repo_data = data['data']
        
        if characteristics['has_hyphen_in_name']:
            mocks.append({
                'name': 'test-repo-with-hyphens',
                'owner': 'test_owner',
                'full_name': 'test_owner/test-repo-with-hyphens',
                # ... other fields based on real data
            })
        
        if characteristics['very_large']:
            mocks.append({
                'name': 'large_test_repo',
                'size': repo_data['size'],  # Use real large size
                'language': repo_data['language'],
                # ... other fields
            })
        
        # Generate mocks for other edge cases
    
    return mocks
```

## Mock Test Implementation

### Use Real-Data-Based Mocks in Tests
```python
@pytest.fixture
def mock_github_client_with_real_data():
    """Mock GitHub client with responses based on real data."""
    
    # Load real data patterns
    real_repo_data = load_real_repository_data('octocat/Hello-World')
    
    mock_client = AsyncMock()
    
    # Configure mock with realistic responses
    mock_client.get_repository.return_value = Repository(**real_repo_data)
    mock_client.get_repository_languages.return_value = {
        'C': 78.1,
        'Assembly': 21.9
    }  # Based on real Hello-World repository
    
    mock_client.get_repository_topics.return_value = []  # Real topics (empty for Hello-World)
    
    return mock_client

@pytest.mark.asyncio
async def test_repository_analysis_with_realistic_mock(mock_github_client_with_real_data):
    """Test repository analysis with realistic mock data."""
    analyzer = RepositoryAnalyzer(mock_github_client_with_real_data)
    
    # Test with realistic data patterns
    result = await analyzer.analyze_repository('test_owner/test_repo')
    
    # Assertions based on realistic expectations
    assert result is not None
    assert result.repository.owner == 'octocat'  # From real data
    assert result.repository.language == 'C'     # From real data
    assert isinstance(result.repository.stargazers_count, int)
    assert result.repository.stargazers_count >= 0
```

### Parameterized Tests with Real Data Variations
```python
@pytest.mark.parametrize("repo_data", [
    create_mock_from_real_data('octocat/Hello-World'),    # Simple repository
    create_mock_from_real_data('microsoft/vscode'),       # Large repository
    create_mock_from_real_data('python/cpython'),         # Language repository
    create_mock_from_real_data('facebook/react'),         # Popular library
])
@pytest.mark.asyncio
async def test_repository_processing_with_real_variations(repo_data):
    """Test repository processing with various real data patterns."""
    
    # Create mock client with specific real data pattern
    mock_client = AsyncMock()
    mock_client.get_repository.return_value = Repository(**repo_data)
    
    # Test processing with realistic data variations
    processor = RepositoryProcessor(mock_client)
    result = await processor.process_repository(repo_data['full_name'])
    
    # Verify processing works with real data patterns
    assert result is not None
    assert result.name == repo_data['name']
    assert result.owner == repo_data['owner']
```

## Continuous Mock Data Updates

### Automated Real Data Collection
```python
# Script to periodically update mock data from real sources
async def update_mock_data_from_real_sources():
    """Update mock data fixtures from real API responses."""
    
    recorder = RealDataRecorder()
    
    # Standard test repositories
    standard_repos = [
        ('octocat', 'Hello-World'),
        ('microsoft', 'vscode'),
        ('python', 'cpython'),
    ]
    
    for owner, name in standard_repos:
        try:
            real_data = await recorder.record_github_repository(owner, name)
            
            # Generate updated mock from real data
            mock_data = generate_mock_from_real_data_dict(real_data)
            
            # Update fixture files
            update_mock_fixture(f"github_repo_{owner}_{name}", mock_data)
            
            print(f"Updated mock data for {owner}/{name}")
            
        except Exception as e:
            print(f"Failed to update {owner}/{name}: {e}")

# Run periodically to keep mocks current
if __name__ == "__main__":
    asyncio.run(update_mock_data_from_real_sources())
```

## Best Practices Summary

### Always Start with Real Data
- Capture real API responses before creating mocks
- Analyze real data patterns and structures
- Use real field names, types, and value ranges
- Include real edge cases and variations

### Validate Mock Realism
- Compare mock data against real data schemas
- Test that mocks can be processed by real code paths
- Verify mock data matches real API response formats
- Include realistic error scenarios from real APIs

### Keep Mocks Current
- Periodically update mocks from real data sources
- Monitor for API changes that affect mock accuracy
- Version mock data to track changes over time
- Document the real data sources used for each mock

### Test Mock Accuracy
- Write tests that validate mock data against real schemas
- Use online tests to verify mock data matches real responses
- Include contract tests that catch API changes
- Test serialization/deserialization with mock data

This approach ensures that mock tests accurately reflect real-world scenarios and catch issues that purely synthetic test data would miss.