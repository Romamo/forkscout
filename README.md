# Forklift 🚀

A powerful GitHub repository fork analysis tool that automatically discovers valuable features across all forks of a repository, ranks them by impact, and can create pull requests to integrate the best improvements back to the upstream project.

## Features

- **Fork Discovery**: Automatically finds and catalogs all public forks of a repository
- **Feature Analysis**: Identifies meaningful changes and improvements in each fork
- **Smart Ranking**: Scores features based on code quality, community engagement, and impact
- **Report Generation**: Creates comprehensive markdown reports with feature summaries
- **Automated PRs**: Can automatically create pull requests for high-value features
- **Caching**: Intelligent caching system to avoid redundant API calls

## Installation

### Prerequisites

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/) package manager

### Install uv

```bash
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

### Install Forklift

```bash
# Clone the repository
git clone https://github.com/forklift-team/forklift.git
cd forklift

# Install dependencies
uv sync

# Install in development mode
uv pip install -e .
```

## Quick Start

1. **Set up your GitHub token**:
   ```bash
   cp .env.example .env
   # Edit .env and add your GitHub token
   ```

2. **Analyze a repository**:
   ```bash
   uv run forklift analyze https://github.com/owner/repo
   ```

3. **Generate a report**:
   ```bash
   uv run forklift analyze https://github.com/owner/repo --output report.md
   ```

4. **Auto-create PRs for high-value features**:
   ```bash
   uv run forklift analyze https://github.com/owner/repo --auto-pr --min-score 80
   ```

## Configuration

Create a `forklift.yaml` configuration file:

```yaml
github:
  token: ${GITHUB_TOKEN}
  
scoring:
  code_quality_weight: 0.3
  community_engagement_weight: 0.2
  test_coverage_weight: 0.2
  documentation_weight: 0.15
  recency_weight: 0.15

analysis:
  min_score_threshold: 70.0
  max_forks_to_analyze: 100
  excluded_file_patterns:
    - "*.md"
    - "*.txt"
    - ".github/*"

cache:
  duration_hours: 24
  max_size_mb: 100
```

## Usage Examples

### Basic Analysis
```bash
forklift analyze https://github.com/fastapi/fastapi
```

### With Custom Configuration
```bash
forklift analyze https://github.com/fastapi/fastapi --config my-config.yaml
```

### Automated PR Creation
```bash
forklift analyze https://github.com/fastapi/fastapi --auto-pr --min-score 85
```

### Verbose Output
```bash
forklift analyze https://github.com/fastapi/fastapi --verbose
```

## Development

### Setup Development Environment

```bash
# Clone and setup
git clone https://github.com/forklift-team/forklift.git
cd forklift
uv sync --dev

# Install pre-commit hooks
uv run pre-commit install
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run only unit tests
uv run pytest tests/unit/

# Run only integration tests
uv run pytest tests/integration/
```

### Code Quality

```bash
# Format code
uv run black src/ tests/

# Lint code
uv run ruff check src/ tests/

# Type checking
uv run mypy src/
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for your changes
5. Ensure all tests pass (`uv run pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [httpx](https://www.python-httpx.org/) for async HTTP requests
- CLI powered by [Click](https://click.palletsprojects.com/)
- Data validation with [Pydantic](https://pydantic.dev/)
- Package management with [uv](https://docs.astral.sh/uv/)