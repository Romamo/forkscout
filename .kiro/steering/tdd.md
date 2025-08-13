---
inclusion: always
---

# Test-Driven Development (TDD) Guidelines

## Core TDD Principles

Follow strict Test-Driven Development practices for all code changes:

1. **Red-Green-Refactor Cycle**: Write failing tests first, implement minimal code to pass, then refactor
2. **Test First**: Never write production code without a failing test that requires it
3. **Comprehensive Coverage**: Cover all edge cases, error conditions, and boundary values
4. **Proof-Based Testing**: Use real data and concrete examples in test cases

## Testing Framework and Structure

- Use `pytest` as the primary testing framework
- Place tests in a `tests/` directory with structure mirroring the source code
- Name test files with `test_` prefix (e.g., `test_main.py`)
- Use descriptive test method names that explain the scenario being tested

## Test Categories to Include

### Unit Tests
- Test individual functions and methods in isolation
- Mock external dependencies
- Cover all code paths and branches

### Integration Tests
- Test component interactions
- Verify data flow between modules
- Test external API integrations

### Edge Cases and Error Handling
- Invalid inputs and boundary conditions
- Network failures and timeouts
- File system errors and permissions
- Empty datasets and null values

## Test Execution Commands

Always use `uv` for test execution:
- Run all tests: `uv run pytest`
- Run specific test file: `uv run pytest tests/test_filename.py`
- Run with coverage: `uv run pytest --cov=src`
- Run in verbose mode: `uv run pytest -v`

## Test Quality Standards

- Each test should test one specific behavior
- Tests must be independent and able to run in any order
- Use clear arrange-act-assert structure
- Include meaningful assertions with descriptive error messages
- Use fixtures for common test setup

## Completion Criteria

Before marking any task complete:
1. All tests must pass (`uv run pytest`)
2. Code coverage should be maintained or improved
3. No test warnings or deprecation messages
4. All edge cases identified during development must have corresponding tests

## Example Test Structure

```python
def test_function_name_with_valid_input_returns_expected_result():
    # Arrange
    input_data = "test_value"
    expected_result = "expected_output"
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected_result, f"Expected {expected_result}, got {result}"
```