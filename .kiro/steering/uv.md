---
inclusion: always
---

# Python Execution Guidelines

## Use `uv run` for Python Commands

This project uses `uv` as the Python package manager and virtual environment tool. Always use `uv run` instead of direct `python` commands to ensure proper dependency management and environment isolation.

### Command Patterns

- **Execute Python scripts**: `uv run python script.py` instead of `python script.py`
- **Run modules**: `uv run python -m module_name` instead of `python -m module_name`
- **Interactive Python**: `uv run python` instead of `python`
- **Install dependencies**: `uv add package_name` instead of `pip install package_name`
- **Development dependencies**: `uv add --dev package_name`

### Benefits

- Automatic virtual environment management
- Consistent dependency resolution
- Faster package installation
- Better reproducibility across environments

### Project Structure

This project follows standard Python conventions with `pyproject.toml` for configuration and dependency management through `uv`.