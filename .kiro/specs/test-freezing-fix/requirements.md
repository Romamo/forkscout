# Requirements Document

## Introduction

The test suite is currently freezing and taking over 24 minutes to run due to several configuration and async handling issues. Tests are failing with "async def functions are not natively supported" errors and missing fixtures, causing the entire test run to hang.

## Requirements

### Requirement 1

**User Story:** As a developer, I want the test suite to run quickly and reliably, so that I can get fast feedback during development.

#### Acceptance Criteria

1. WHEN I run `uv run pytest --tb=short` THEN the test suite SHALL complete in under 5 minutes
2. WHEN async tests are defined THEN they SHALL have proper `@pytest.mark.asyncio` decorators
3. WHEN the test suite runs THEN it SHALL NOT freeze or hang indefinitely
4. WHEN tests require fixtures THEN those fixtures SHALL be properly defined and available

### Requirement 2

**User Story:** As a developer, I want proper pytest configuration, so that custom marks are recognized and tests are organized correctly.

#### Acceptance Criteria

1. WHEN custom pytest marks are used THEN they SHALL be registered in pytest configuration
2. WHEN tests use marks like `@pytest.mark.contract`, `@pytest.mark.integration`, etc. THEN pytest SHALL recognize them without warnings
3. WHEN the test configuration is updated THEN it SHALL support all existing test categories
4. WHEN tests are categorized THEN they SHALL be able to run independently by category

### Requirement 3

**User Story:** As a developer, I want example tests to be properly structured, so that they don't interfere with the main test suite.

#### Acceptance Criteria

1. WHEN example tests are async THEN they SHALL have proper async decorators
2. WHEN example tests require fixtures THEN those fixtures SHALL be defined or the tests SHALL be parameterized
3. WHEN example tests run THEN they SHALL complete quickly without hanging
4. WHEN example tests fail THEN they SHALL provide clear error messages

### Requirement 4

**User Story:** As a developer, I want to identify and fix all tests that don't complete in reasonable time, so that the entire test suite is efficient.

#### Acceptance Criteria

1. WHEN I analyze the test suite THEN I SHALL identify these specific problematic tests:
   - `examples/test_github_only.py::test_github_functionality` - missing fixture, makes real API calls
   - `examples/test_batch_optimization.py::test_batch_optimization` - missing @pytest.mark.asyncio, makes real API calls
   - `examples/test_rate_limit_fix.py::test_rate_limit_fix` - missing @pytest.mark.asyncio, makes real API calls
   - `examples/test_behind_commits_error_handling.py` - multiple async functions missing decorators
   - `examples/test_behind_commits_fix.py` - async functions missing decorators
   - `examples/test_fork_filtering_cli.py::test_fork_filtering` - missing @pytest.mark.asyncio
   - `examples/test_progress_feedback.py::test_progress_feedback` - missing @pytest.mark.asyncio
2. WHEN tests make real GitHub API calls THEN they SHALL be marked as @pytest.mark.online tests
3. WHEN tests are in examples/ directory THEN they SHALL either be properly mocked or moved to appropriate test categories
4. WHEN async test functions exist THEN they SHALL have @pytest.mark.asyncio decorators
5. WHEN tests require fixtures THEN those fixtures SHALL be defined or tests SHALL be parameterized

### Requirement 5

**User Story:** As a developer, I want to be able to run different test categories separately, so that I can focus on specific types of testing.

#### Acceptance Criteria

1. WHEN I run unit tests THEN they SHALL complete in under 2 minutes
2. WHEN I run integration tests THEN they SHALL be separate from unit tests  
3. WHEN I run online tests THEN they SHALL be marked and skippable
4. WHEN I run performance tests THEN they SHALL be separate from regular tests
5. WHEN I run tests by category THEN each category SHALL have reasonable time limits