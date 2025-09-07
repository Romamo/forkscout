# Implementation Plan

- [x] 1. Fix async test decorators in examples directory
  - Add `@pytest.mark.asyncio` decorators to all async test functions
  - Verify async tests can execute without hanging
  - _Requirements: 1.2, 3.1_

- [x] 2. Remove inappropriate rate limit tests that cause hanging
  - Remove or convert `examples/test_rate_limit_fix.py` to mocked unit test
  - Remove or convert `examples/test_progress_feedback.py` to use mocked delays
  - Move `examples/rate_limiting_demo.py` out of test discovery path
  - _Requirements: 1.1, 1.3, 4.1_

- [x] 3. Fix missing fixtures and parameterization issues
  - Define `commit_url` fixture for `test_github_only.py`
  - Create other missing fixtures in conftest.py
  - Convert tests to parameterized format where appropriate
  - _Requirements: 1.4, 3.3_

- [x] 4. Mock external API calls in unit tests
  - Replace real GitHub API calls with mocks in unit tests
  - Mark tests that need real API calls with `@pytest.mark.online`
  - Ensure unit tests can run without external dependencies
  - _Requirements: 2.2, 4.2_

- [x] 5. Update pytest configuration for custom marks
  - Register all custom pytest marks in pytest.ini
  - Configure default test execution to exclude slow/online tests
  - Add timeout configuration to prevent hanging
  - _Requirements: 2.1, 2.3_

- [x] 6. Organize example tests into proper categories
  - Move appropriate tests to unit/integration/online test directories
  - Remove or convert demo scripts that shouldn't be tests
  - Ensure examples directory doesn't interfere with test discovery
  - _Requirements: 3.2, 4.3, 5.2_

- [x] 7. Add test execution timeouts and error handling
  - Configure pytest timeout plugin or add timeout decorators
  - Add proper error handling for network failures
  - Ensure tests fail fast rather than hanging
  - _Requirements: 1.3, 4.4_

- [x] 8. Validate test suite performance
  - Run full test suite to ensure completion under 5 minutes
  - Verify unit tests complete under 2 minutes
  - Test different execution categories work independently
  - _Requirements: 1.1, 5.1, 5.5_