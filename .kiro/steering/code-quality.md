---
inclusion: always
---

# Code Quality Standards

## Linting and Formatting

### Primary Tools
- **Ruff**: Use for linting, import sorting, and code analysis
- **Black**: Use for consistent code formatting
- **mypy**: Use for static type checking

### Configuration
- Configure ruff in `pyproject.toml` with project-specific rules
- Set up pre-commit hooks for automatic checks before commits
- Maintain consistent code style across all Python files
- Use line length of 88 characters (Black default)

### Pre-commit Setup
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.x.x
    hooks:
      - id: black
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.x.x
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

## Code Review Guidelines

### Review Checklist
- **Functionality**: Does the code do what it's supposed to do?
- **Readability**: Is the code easy to understand and maintain?
- **Performance**: Are there any obvious performance issues?
- **Security**: Are there any security vulnerabilities?
- **Testing**: Is the code properly tested with good coverage?
- **Documentation**: Are complex parts properly documented?

### Review Process
- All code must be reviewed before merging to main branch
- Focus on readability, maintainability, and correctness
- Check for proper error handling and edge cases
- Verify that tests cover new functionality
- Ensure code follows established patterns and conventions

### Review Standards
- Be constructive and specific in feedback
- Explain the "why" behind suggestions
- Approve only when confident in code quality
- Request changes for any security or correctness issues

## Documentation Standards

### Code Documentation
- All public functions and classes must have docstrings
- Use Google-style docstrings for consistency
- Include parameter types, return types, and examples where helpful
- Document complex algorithms and business logic

### Type Hints
- Use type hints consistently throughout the codebase
- Import types from `typing` module when needed
- Use `Optional` for nullable parameters
- Define custom types for complex data structures

### Project Documentation
- Maintain up-to-date README with setup and usage instructions
- Document API endpoints with clear examples
- Keep CHANGELOG updated with notable changes
- Include troubleshooting guides for common issues

## Code Organization

### File Structure
- Follow the established project structure guidelines
- Keep related functionality grouped together
- Use descriptive file and module names
- Avoid circular imports through proper dependency management

### Naming Conventions
- Use clear, descriptive names for variables, functions, and classes
- Follow Python naming conventions (PEP 8)
- Use constants for magic numbers and strings
- Prefer explicit names over abbreviations

## Quality Metrics

### Code Coverage
- Maintain minimum 90% test coverage
- Focus on meaningful tests, not just coverage numbers
- Test edge cases and error conditions
- Use coverage reports to identify untested code paths

### Complexity Management
- Keep functions focused and single-purpose
- Break down complex functions into smaller, testable units
- Use early returns to reduce nesting
- Limit cyclomatic complexity per function

### Technical Debt
- Address technical debt regularly, not just during major refactors
- Document known issues and improvement opportunities
- Prioritize debt that impacts development velocity
- Include debt reduction in sprint planning