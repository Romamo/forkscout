# Forkscout 🚀

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

### Install Forkscout

#### From PyPI (Recommended)

```bash
# Install with pip
pip install forkscout

# Or with uv
uv add forkscout
```

#### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/Romamo/forkscout.git
cd forkscout

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
   uv run forkscout analyze https://github.com/pallets/click
   ```

3. **Generate a report**:
   ```bash
   uv run forkscout analyze https://github.com/psf/requests --output report.md
   ```

4. **Auto-create PRs for high-value features**:
   ```bash
   uv run forkscout analyze https://github.com/Textualize/rich --auto-pr --min-score 80
   ```

## Configuration

Create a `forkscout.yaml` configuration file:

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

# Commit counting configuration
commit_count:
  max_count_limit: 100          # Maximum commits to count per fork (0 = unlimited)
  display_limit: 5              # Maximum commits to show in display
  use_unlimited_counting: false # Enable unlimited counting by default
  timeout_seconds: 30           # Timeout for commit counting operations

cache:
  duration_hours: 24
  max_size_mb: 100
```

## Usage Examples

### Basic Analysis
```bash
forkscout analyze https://github.com/pallets/click
```

### Fork Analysis Commands
```bash
# Show all forks with compact commit status
forkscout show-forks https://github.com/psf/requests

# Show forks with recent commits in a separate column
forkscout show-forks https://github.com/Textualize/rich --show-commits 3

# Show detailed fork information with exact commit counts
forkscout show-forks https://github.com/pytest-dev/pytest --detail
```

### Commit Counting Options
```bash
# Basic exact commit counting (default: count up to 100 commits)
forkscout show-forks https://github.com/newmarcel/KeepingYouAwake --detail

# Unlimited commit counting for maximum accuracy (slower)
forkscout show-forks https://github.com/aarigs/pandas-ta --detail --max-commits-count 0

# Fast processing with lower commit limit
forkscout show-forks https://github.com/NoMore201/googleplay-api --detail --max-commits-count 50

# Custom display limit for commit messages
forkscout show-forks https://github.com/sanila2007/youtube-bot-telegram --show-commits 3 --commit-display-limit 10

# Focus on active forks only
forkscout show-forks https://github.com/maliayas/github-network-ninja --detail --ahead-only
```

### Understanding Commit Status Format

The fork tables display commit status in a compact "+X -Y" format:
- `+5 -2` means 5 commits ahead, 2 commits behind
- `+3` means 3 commits ahead, up-to-date
- `-1` means 1 commit behind, no new commits  
- Empty cell means completely up-to-date
- `Unknown` means status could not be determined

### With Custom Configuration
```bash
forkscout analyze https://github.com/virattt/ai-hedge-fund --config my-config.yaml
```

### Automated PR Creation
```bash
forkscout analyze https://github.com/xgboosted/pandas-ta-classic --auto-pr --min-score 85
```

### Verbose Output
```bash
forkscout analyze https://github.com/pallets/click --verbose
```

## Troubleshooting

### Common Issues

**Commit counts showing "+1" for all forks:**
- This was a bug in earlier versions. Update to the latest version.
- Use `--detail` flag for accurate commit counting.

**Slow performance with commit counting:**
- Use `--max-commits-count 50` for faster processing
- Limit forks with `--max-forks 25`
- Use `--ahead-only` to skip inactive forks

**"Unknown" commit counts:**
- Usually indicates private/deleted forks or API rate limiting
- Check GitHub token configuration
- Try with `--verbose` for detailed error information

For comprehensive troubleshooting, see [docs/COMMIT_COUNTING_TROUBLESHOOTING.md](docs/COMMIT_COUNTING_TROUBLESHOOTING.md).

## Development

### Setup Development Environment

```bash
# Clone and setup
git clone https://github.com/Romamo/forkscout.git
cd forkscout
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

## Evaluation Criteria

Forkscout uses a sophisticated evaluation system to analyze commits and determine their value for the main repository. This section explains how the system makes decisions about commit categorization, impact assessment, and value determination.

### Commit Categorization

The system categorizes each commit into one of the following types based on commit message patterns and file changes:

#### Category Types and Patterns

**🚀 Feature** - New functionality or enhancements
- **Message patterns**: `feat:`, `feature`, `implement`, `new`, `add`, `introduce`, `create`, `build`, `support for`, `enable`
- **Examples**: 
  - `feat: add user authentication system`
  - `implement OAuth2 login flow`
  - `add support for PostgreSQL database`

**🐛 Bugfix** - Error corrections and issue resolutions
- **Message patterns**: `fix:`, `bug`, `patch`, `hotfix`, `repair`, `resolve`, `correct`, `address`, `issue`, `problem`, `error`
- **Examples**:
  - `fix: resolve memory leak in data processing`
  - `correct validation error in user input`
  - `patch security vulnerability in auth module`

**🔧 Refactor** - Code improvements without functional changes
- **Message patterns**: `refactor:`, `clean`, `improve`, `restructure`, `reorganize`, `simplify`, `extract`, `rename`, `move`
- **Examples**:
  - `refactor: extract common validation logic`
  - `improve code organization in user module`
  - `simplify database connection handling`

**📚 Documentation** - Documentation updates and improvements
- **Message patterns**: `docs:`, `documentation`, `readme`, `comment`, `comments`, `docstring`, `guide`, `tutorial`, `example`
- **File patterns**: `README.*`, `*.md`, `*.rst`, `docs/`, `*.txt`
- **Examples**:
  - `docs: update installation instructions`
  - `add API documentation for user endpoints`
  - `improve code comments in core modules`

**🧪 Test** - Test additions and improvements
- **Message patterns**: `test:`, `tests`, `testing`, `spec`, `unittest`, `pytest`, `coverage`, `mock`, `fixture`, `assert`
- **File patterns**: `test_*.py`, `*_test.py`, `tests/`, `*.test.js`, `*.spec.js`
- **Examples**:
  - `test: add unit tests for user service`
  - `improve test coverage for authentication`
  - `add integration tests for API endpoints`

**🔨 Chore** - Maintenance and build-related changes
- **Message patterns**: `chore:`, `maintenance`, `upgrade`, `dependency`, `dependencies`, `version`, `config`, `configuration`, `setup`
- **File patterns**: `requirements.txt`, `package.json`, `pyproject.toml`, `setup.py`, `Dockerfile`, `.github/`, `.gitignore`
- **Examples**:
  - `chore: update dependencies to latest versions`
  - `upgrade Python to 3.12`
  - `configure CI/CD pipeline`

**⚡ Performance** - Performance optimizations
- **Message patterns**: `perf:`, `performance`, `speed`, `fast`, `optimize`, `optimization`, `efficient`, `cache`, `caching`, `memory`
- **Examples**:
  - `perf: optimize database query performance`
  - `improve memory usage in data processing`
  - `add caching layer for API responses`

**🔒 Security** - Security-related changes
- **Message patterns**: `security:`, `secure`, `vulnerability`, `auth`, `authentication`, `authorization`, `encrypt`, `decrypt`, `hash`
- **File patterns**: `*auth*.py`, `*security*.py`, `*crypto*.py`
- **Examples**:
  - `security: fix SQL injection vulnerability`
  - `implement secure password hashing`
  - `add rate limiting to API endpoints`

**❓ Other** - Changes that don't fit standard categories
- Used when commit patterns don't match any specific category
- Often indicates complex or unclear changes

### Impact Assessment

The system evaluates the potential impact of each commit using multiple factors:

#### File Criticality Rules

Files are assessed for criticality based on their role in the project:

**🔴 Critical Files (Score: 1.0)**
- Core application files: `main.py`, `index.js`, `app.py`, `server.py`
- Entry points: `__init__.py`, `setup.py`, `pyproject.toml`, `package.json`
- Files explicitly listed in project's critical files

**🟠 High Criticality (Score: 0.8-0.9)**
- Security files: `*auth*.py`, `*security*.py`, `*crypto*.py`, `*permission*.py`
- Configuration files: `config.*`, `settings.*`, `.env*`, `Dockerfile`, `docker-compose.yml`

**🟡 Medium-High Criticality (Score: 0.7)**
- Database/model files: `*model*.py`, `*schema*.py`, `*migration*.py`, `*database*.py`

**🟢 Medium Criticality (Score: 0.6)**
- API/interface files: `*api*.py`, `*endpoint*.py`, `*route*.py`, `*controller*.py`

**🔵 Low Criticality (Score: 0.1-0.2)**
- Test files: `test_*.py`, `*_test.py`, `tests/`, `*.test.js`, `*.spec.js`
- Documentation: `README.*`, `*.md`, `*.rst`, `docs/`

#### Change Magnitude Calculation

The system calculates change magnitude based on:
- **Lines changed**: Additions + deletions (weighted 70%)
- **Files changed**: Number of modified files (weighted 30%)
- **Size bonuses**: Large changes (>500 lines) get 1.5x multiplier, medium changes (>200 lines) get 1.2x multiplier

#### Quality Factors

**Test Coverage Factor**
- Measures proportion of test files in the change
- Bonus points for including any test files
- Score: 0.0 (no tests) to 1.0 (comprehensive test coverage)

**Documentation Factor**
- Measures proportion of documentation files
- Bonus points for including any documentation
- Score: 0.0 (no docs) to 1.0 (comprehensive documentation)

**Code Organization Factor**
- Evaluates focus and coherence of changes
- Bonus for focused changes (≤3 files)
- Penalty for scattered changes (>10 files)
- Considers average changes per file

**Commit Quality Factor**
- Message length and descriptiveness
- Conventional commit format bonus
- Penalty for merge commits

#### Impact Level Determination

The system combines all factors to determine overall impact:

- **🔴 Critical (Score ≥ 0.8)**: Major changes to critical files with high quality
- **🟠 High (Score ≥ 0.6)**: Significant changes to important files
- **🟡 Medium (Score ≥ 0.3)**: Moderate changes with reasonable scope
- **🟢 Low (Score < 0.3)**: Minor changes or low-impact files

### Value Assessment for Main Repository

The system determines whether each commit could be valuable for the main repository:

#### "Yes" - Valuable for Main Repository

**Automatic "Yes" Categories:**
- **Bugfixes**: Error corrections benefit all users
- **Security fixes**: Critical for all installations
- **Performance improvements**: Speed benefits everyone
- **Documentation**: Helps all users understand the project
- **Tests**: Improve reliability for everyone

**Conditional "Yes" Examples:**
- **Features**: Substantial new functionality (>50 lines changed)
- **Refactoring**: Significant code improvements
- **Dependency updates**: Security or compatibility improvements

**Example "Yes" Commits:**
```
✅ fix: resolve memory leak in data processing loop
✅ security: patch SQL injection vulnerability in user queries  
✅ perf: optimize database connection pooling (40% faster)
✅ feat: add comprehensive input validation system
✅ docs: add troubleshooting guide for common errors
✅ test: add integration tests for payment processing
```

#### "No" - Not Relevant for Main Repository

**Typical "No" Scenarios:**
- Fork-specific configurations or customizations
- Environment-specific changes
- Personal preferences or styling
- Changes that break compatibility
- Experimental or incomplete features

**Example "No" Commits:**
```
❌ chore: update personal development environment setup
❌ feat: add company-specific branding and logos
❌ config: change database from PostgreSQL to MongoDB for our use case
❌ style: reformat code according to personal preferences
❌ feat: add integration with internal company API
```

#### "Unclear" - Needs Further Review

**Typical "Unclear" Scenarios:**
- Small features that might be too specific
- Refactoring without clear benefits
- Complex changes that do multiple things
- Changes with insufficient context
- Experimental or unfinished work

**Example "Unclear" Commits:**
```
❓ refactor: minor code cleanup in utility functions
❓ feat: add small convenience method for date formatting
❓ fix: workaround for edge case in specific environment
❓ update: misc changes and improvements
❓ feat: experimental feature for advanced users
```

### Decision Trees and Logic Flow

#### Commit Categorization Flow

```
1. Check commit message for conventional commit prefix (feat:, fix:, etc.)
   ├─ If found → Use prefix category with high confidence (0.9)
   └─ If not found → Continue to pattern matching

2. Analyze commit message for category keywords
   ├─ Multiple matches → Use highest priority match
   └─ No matches → Continue to file analysis

3. Analyze changed files for category patterns
   ├─ Strong file pattern match (>80% files) → Use file category
   └─ Weak or mixed patterns → Continue to combination logic

4. Combine message and file analysis
   ├─ Message and files agree → Boost confidence (+0.2)
   ├─ Message confidence > File confidence → Use message category
   ├─ File confidence > Message confidence → Use file category
   └─ Equal confidence → Default to message category or OTHER
```

#### Impact Assessment Flow

```
1. Calculate Change Magnitude
   ├─ Count lines changed (additions + deletions)
   ├─ Count files changed
   └─ Apply size multipliers for large changes

2. Assess File Criticality
   ├─ Check against critical file patterns
   ├─ Calculate weighted average by change size
   └─ Return criticality score (0.0 to 1.0)

3. Evaluate Quality Factors
   ├─ Test coverage: Proportion of test files
   ├─ Documentation: Proportion of doc files  
   ├─ Code organization: Focus and coherence
   └─ Commit quality: Message and format quality

4. Determine Impact Level
   ├─ Combine: 40% magnitude + 40% criticality + 20% quality
   ├─ Score ≥ 0.8 → Critical
   ├─ Score ≥ 0.6 → High
   ├─ Score ≥ 0.3 → Medium
   └─ Score < 0.3 → Low
```

#### Value Assessment Flow

```
1. Check Category Type
   ├─ Bugfix/Security/Performance → Automatic "Yes"
   ├─ Docs/Test → Automatic "Yes"
   └─ Feature/Refactor/Chore → Continue evaluation

2. Analyze Change Scope
   ├─ Substantial changes (>50 lines) → Likely "Yes"
   ├─ Small changes (<20 lines) → Likely "Unclear"
   └─ Medium changes → Continue evaluation

3. Check for Fork-Specific Indicators
   ├─ Personal/company-specific terms → "No"
   ├─ Environment-specific configs → "No"
   └─ Generic improvements → Continue evaluation

4. Final Assessment
   ├─ Clear benefit to all users → "Yes"
   ├─ Clearly fork-specific → "No"
   └─ Uncertain or context-dependent → "Unclear"
```

### Troubleshooting Common Questions

#### "Why was my commit categorized as 'Other'?"

**Possible reasons:**
- Commit message doesn't match known patterns
- Mixed file types that don't clearly indicate category
- Generic or unclear commit message

**Solutions:**
- Use conventional commit format: `feat:`, `fix:`, `docs:`, etc.
- Write descriptive commit messages with clear action words
- Focus commits on single types of changes

#### "Why is the impact level lower than expected?"

**Common causes:**
- Changes affect low-criticality files (tests, docs)
- Small change magnitude (few lines/files changed)
- Poor commit quality (short message, merge commit)
- Low quality factors (no tests or docs included)

**To increase impact:**
- Include changes to core application files
- Add tests and documentation with your changes
- Write descriptive commit messages
- Make focused, substantial changes

#### "Why was my feature marked as 'Unclear' for main repo value?"

**Typical reasons:**
- Feature appears too specific or niche
- Insufficient context to determine general usefulness
- Small or experimental change
- Complex commit that does multiple things

**To improve assessment:**
- Write clear commit messages explaining the benefit
- Include documentation explaining the feature
- Make focused commits that do one thing well
- Consider if the feature would help other users

#### "The system missed an important security fix"

**Possible issues:**
- Commit message doesn't include security keywords
- Files don't match security patterns
- Change appears as refactoring or other category

**Improvements:**
- Use security-related keywords: `security`, `vulnerability`, `auth`, `secure`
- Use conventional commit format: `security: fix vulnerability in...`
- Include security-related files in the change

#### "My documentation update was categorized as 'Chore'"

**Common causes:**
- Files don't match documentation patterns
- Commit message uses maintenance-related words
- Mixed changes including config files

**Solutions:**
- Use doc-specific keywords: `docs`, `documentation`, `readme`
- Focus commits on documentation files only
- Use conventional commit format: `docs: update installation guide`

### Understanding Explanation Output

When using the `--explain` flag, you'll see structured output with clear separation between factual descriptions and system assessments:

```
📝 Description: Added user authentication middleware to handle JWT tokens
⚖️  Assessment: Value for main repo: YES
   Category: 🚀 Feature | Impact: 🔴 High
   Reasoning: Large changes affecting critical security files with test coverage
```

**Key sections:**
- **📝 Description**: Factual description of what changed
- **⚖️ Assessment**: System's evaluation and judgment
- **Category**: Determined commit type with confidence
- **Impact**: Assessed impact level with reasoning
- **Value**: Whether this could help the main repository

This separation helps you distinguish between objective facts about the commit and the system's subjective assessment of its value.

### Visual Formatting Guide

The system uses consistent visual indicators to help you quickly scan results:

**Category Icons:**
- 🚀 Feature - New functionality
- 🐛 Bugfix - Error corrections  
- 🔧 Refactor - Code improvements
- 📚 Documentation - Docs and guides
- 🧪 Test - Testing improvements
- 🔨 Chore - Maintenance tasks
- ⚡ Performance - Speed optimizations
- 🔒 Security - Security fixes
- ❓ Other - Uncategorized changes

**Impact Level Colors:**
- 🔴 Critical - Major system changes
- 🟠 High - Significant improvements
- 🟡 Medium - Moderate changes
- 🟢 Low - Minor modifications

**Value Assessment:**
- ✅ Yes - Valuable for main repository
- ❌ No - Fork-specific only
- ❓ Unclear - Needs further review

**Complexity Indicators:**
- ⚠️ Complex commits that do multiple things are flagged for careful review
- Simple, focused commits are preferred for easier integration

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