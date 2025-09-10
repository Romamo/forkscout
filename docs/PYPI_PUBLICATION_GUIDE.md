# PyPI Publication Guide for Forkscout

This guide provides step-by-step instructions for publishing Forkscout to PyPI (Python Package Index).

## Prerequisites

### 1. PyPI Account Setup

1. **Create PyPI Account**: Register at [https://pypi.org/account/register/](https://pypi.org/account/register/)
2. **Create Test PyPI Account**: Register at [https://test.pypi.org/account/register/](https://test.pypi.org/account/register/)
3. **Enable 2FA**: Enable two-factor authentication on both accounts for security

### 2. API Token Generation

1. **PyPI API Token**:
   - Go to [https://pypi.org/manage/account/token/](https://pypi.org/manage/account/token/)
   - Create a new API token with "Entire account" scope
   - Save the token securely (starts with `pypi-`)

2. **Test PyPI API Token**:
   - Go to [https://test.pypi.org/manage/account/token/](https://test.pypi.org/manage/account/token/)
   - Create a new API token with "Entire account" scope
   - Save the token securely

### 3. Local Configuration

1. **Copy PyPI configuration template**:
   ```bash
   cp .pypirc.template ~/.pypirc
   ```

2. **Edit ~/.pypirc** and replace the placeholder tokens:
   ```ini
   [distutils]
   index-servers =
       pypi
       testpypi

   [pypi]
   repository = https://upload.pypi.org/legacy/
   username = __token__
   password = pypi-your-actual-token-here

   [testpypi]
   repository = https://test.pypi.org/legacy/
   username = __token__
   password = pypi-your-test-token-here
   ```

3. **Set file permissions**:
   ```bash
   chmod 600 ~/.pypirc
   ```

## Publication Process

### Step 1: Prepare the Package

1. **Ensure version is updated**:
   - Update version in `pyproject.toml`
   - Update version in `src/forkscout/__init__.py`
   - Ensure versions match

2. **Clean previous builds**:
   ```bash
   rm -rf dist/ build/ *.egg-info/
   ```

3. **Build the package**:
   ```bash
   uv build
   ```

4. **Verify build artifacts**:
   ```bash
   ls -la dist/
   # Should show: forkscout-1.0.0.tar.gz and forkscout-1.0.0-py3-none-any.whl
   ```

### Step 2: Test Publication (Recommended)

1. **Install twine**:
   ```bash
   uv add --dev twine
   ```

2. **Validate package**:
   ```bash
   uv run python -m twine check dist/*
   ```

3. **Upload to Test PyPI**:
   ```bash
   uv run python -m twine upload --repository testpypi dist/*
   ```

4. **Test installation from Test PyPI**:
   ```bash
   # Create a test environment
   uv venv test-pypi-install
   
   # Install from Test PyPI
   uv pip install --python test-pypi-install \
     --index-url https://test.pypi.org/simple/ \
     --extra-index-url https://pypi.org/simple/ \
     forkscout==1.0.0
   
   # Test the installation
   uv run --python test-pypi-install forkscout --version
   uv run --python test-pypi-install forkscout --help
   
   # Clean up
   rm -rf test-pypi-install
   ```

### Step 3: Production Publication

1. **Upload to production PyPI**:
   ```bash
   uv run python -m twine upload dist/*
   ```

2. **Verify publication**:
   - Check the package page: [https://pypi.org/project/forkscout/](https://pypi.org/project/forkscout/)
   - Verify metadata, description, and links are correct

3. **Test installation from PyPI**:
   ```bash
   # Create a test environment
   uv venv test-production-install
   
   # Install from production PyPI
   uv pip install --python test-production-install forkscout==1.0.0
   
   # Test the installation
   uv run --python test-production-install forkscout --version
   uv run --python test-production-install forkscout --help
   
   # Clean up
   rm -rf test-production-install
   ```

## Automated Publication Script

Use the provided script for streamlined publication:

```bash
# Test PyPI first (recommended)
python scripts/publish_to_pypi.py --test-pypi

# Production PyPI
python scripts/publish_to_pypi.py --production

# Both in sequence
python scripts/publish_to_pypi.py --test-pypi --production
```

## Post-Publication Tasks

### 1. Update Documentation

1. **Update README.md** with PyPI installation instructions:
   ```markdown
   ## Installation

   Install Forkscout from PyPI:

   ```bash
   pip install forkscout
   ```

   Or using uv:

   ```bash
   uv add forkscout
   ```
   ```

2. **Update project URLs** if needed in `pyproject.toml`

### 2. Create GitHub Release

1. **Tag the release**:
   ```bash
   git tag -a v1.0.0 -m "Release version 1.0.0"
   git push origin v1.0.0
   ```

2. **Create GitHub release**:
   - Go to [https://github.com/Romamo/forkscout/releases](https://github.com/Romamo/forkscout/releases)
   - Click "Create a new release"
   - Select the v1.0.0 tag
   - Add release notes highlighting new features and changes

### 3. Verify Installation

Test installation on different platforms:

```bash
# Test on different Python versions
python3.12 -m pip install forkscout
python3.13 -m pip install forkscout

# Test in different environments
pip install forkscout  # System Python
pipx install forkscout  # Isolated installation
uv tool install forkscout  # UV tool installation
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Verify API tokens are correct and not expired
   - Check ~/.pypirc file permissions (should be 600)
   - Ensure 2FA is properly configured

2. **Package Already Exists**:
   - PyPI doesn't allow overwriting existing versions
   - Increment version number in pyproject.toml and __init__.py
   - Rebuild and upload new version

3. **Metadata Validation Errors**:
   - Run `twine check dist/*` to identify issues
   - Common issues: missing long description, invalid classifiers
   - Fix issues in pyproject.toml and rebuild

4. **Dependency Resolution Issues**:
   - Ensure all dependencies are available on PyPI
   - Check version constraints are not too restrictive
   - Test installation in clean environment

### Getting Help

- **PyPI Help**: [https://pypi.org/help/](https://pypi.org/help/)
- **Twine Documentation**: [https://twine.readthedocs.io/](https://twine.readthedocs.io/)
- **Python Packaging Guide**: [https://packaging.python.org/](https://packaging.python.org/)

## Security Considerations

1. **API Token Security**:
   - Never commit API tokens to version control
   - Use environment variables or secure credential storage
   - Rotate tokens periodically

2. **Package Integrity**:
   - Always verify package contents before upload
   - Use `twine check` to validate metadata
   - Test installation in clean environments

3. **Version Management**:
   - Use semantic versioning (MAJOR.MINOR.PATCH)
   - Never reuse version numbers
   - Tag releases in Git for traceability

## Maintenance

### Regular Tasks

1. **Monitor Package Health**:
   - Check download statistics on PyPI
   - Monitor for security vulnerabilities
   - Update dependencies regularly

2. **Version Updates**:
   - Follow semantic versioning principles
   - Update changelog for each release
   - Test thoroughly before publishing

3. **Community Engagement**:
   - Respond to issues and questions
   - Consider user feedback for improvements
   - Maintain clear documentation

This guide ensures a smooth and secure publication process for Forkscout on PyPI.