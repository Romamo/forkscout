# Implementation Plan

## Phase 1: Foundation Fixes (Critical Priority)

- [x] 1. Fix critical import errors and undefined names
  - Fix `CLIError` import issues in test files
  - Define or import `table_context` where needed
  - Fix `CommitDataFormatter` import path issues
  - Update `ForkQualificationResult` import references
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 2. Fix method signature mismatches in repository display service
  - Update `_fetch_commits_concurrently()` calls to include `base_owner` and `base_repo` parameters
  - Fix `_show_comprehensive_fork_data()` calls to include `show_commits` parameter
  - Update other display service method calls with changed signatures
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 3. Fix basic async mock configuration issues
  - Replace `Mock` with `AsyncMock` for async methods in critical tests
  - Fix "coroutine was never awaited" warnings in high-priority test files
  - Configure proper async return values for mocked methods
  - _Requirements: 4.1, 4.2, 4.4_

## Phase 2: Data Model and Contract Fixes

- [x] 4. Fix Pydantic model validation errors
  - Update `Repository` model test data to include required `url`, `html_url`, `clone_url` fields
  - Fix `Commit` model test data to include required `url` field
  - Fix `ForkQualificationMetrics` validation errors in test data
  - Update model field names and requirements in test fixtures
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 5. Update contract tests to match current API interfaces
  - Fix method signature contract tests
  - Update model field requirement contracts
  - Fix API response format expectations in contract tests
  - Ensure backward compatibility requirements are properly tested
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 6. Fix remaining mock configuration issues
  - Configure GitHub API mocks to return properly structured responses
  - Fix file operation mocks to handle async operations correctly
  - Ensure all mocks match the expected interface of real objects
  - _Requirements: 4.2, 4.3, 4.5_

## Phase 3: Feature-Specific Fixes

- [-] 7. Fix CSV export test failures
  - Update CSV column name expectations (`fork_name` vs `Fork URL`, etc.)
  - Fix CSV data structure access patterns and key errors
  - Update CSV export configuration expectations in tests
  - Fix special character handling and escaping in CSV tests
  - _Requirements: 6.1, 6.2, 6.3, 6.5_

- [ ] 8. Fix display and formatting test failures
  - Update emoji and formatting pattern expectations in display tests
  - Fix table formatting tests to match current display logic
  - Update compact display mode tests for current implementations
  - Fix rich console formatting test expectations
  - _Requirements: 7.1, 7.2, 7.3, 7.5_

- [ ] 9. Fix terminal detection and environment-specific tests
  - Update terminal width detection tests for different environments
  - Fix parent process detection tests that depend on execution environment
  - Make environment-dependent tests more robust or skip appropriately
  - _Requirements: 7.4_

## Phase 4: Integration and Performance Fixes

- [ ] 10. Fix integration test coordination issues
  - Update integration tests to properly coordinate between components
  - Fix component interface mismatches in integration tests
  - Ensure integration tests use consistent data structures
  - _Requirements: 8.2_

- [ ] 11. Fix performance test expectations and benchmarks
  - Update performance test expectations to be realistic for current implementation
  - Fix optimization tests to validate actual optimization benefits
  - Update concurrent processing tests to handle real concurrency scenarios
  - _Requirements: 8.1, 8.4, 8.5_

- [ ] 12. Fix end-to-end workflow tests
  - Update end-to-end tests to simulate realistic user workflows
  - Fix complex workflow test failures with proper component coordination
  - Ensure end-to-end tests use current API interfaces and data structures
  - _Requirements: 8.3_

## Phase 5: Optimization and Cleanup

- [ ] 13. Optimize test execution performance
  - Identify and optimize slow-running tests that exceed reasonable time limits
  - Reduce test execution time without compromising test coverage
  - Ensure test categorization allows efficient subset execution
  - _Requirements: 9.1, 9.3_

- [ ] 14. Improve test error reporting and debugging
  - Ensure test failures provide clear, actionable error messages
  - Add better context and debugging information to complex test failures
  - Improve test isolation to prevent cascading failures
  - _Requirements: 9.2, 9.4_

- [ ] 15. Stabilize flaky tests and final validation
  - Identify and fix intermittent test failures
  - Ensure test suite stability across multiple runs
  - Validate that all fixes maintain backward compatibility
  - Run comprehensive test suite validation
  - _Requirements: 9.5_

## Validation Strategy

Each task should be validated using this approach:

1. **Before Fix**: Run affected tests to confirm current failure state
2. **Apply Fix**: Implement the specific fixes for the task
3. **Immediate Validation**: Run the fixed tests to confirm they now pass
4. **Regression Check**: Run a broader set of tests to ensure no new failures
5. **Progress Tracking**: Update failure count and document progress

## Success Metrics by Phase

- **Phase 1 Complete**: Reduce failures from 308 to <200 (foundation fixes)
- **Phase 2 Complete**: Reduce failures from <200 to <100 (data and contract fixes)
- **Phase 3 Complete**: Reduce failures from <100 to <50 (feature fixes)
- **Phase 4 Complete**: Reduce failures from <50 to <20 (integration fixes)
- **Phase 5 Complete**: Reduce failures from <20 to <10 (final optimization)

## Execution Commands for Validation

```bash
# Phase 1 validation
uv run pytest tests/unit/test_cli.py tests/contract/test_show_commits_contracts.py -v

# Phase 2 validation  
uv run pytest tests/contract/ tests/unit/test_repository_display_service.py -v

# Phase 3 validation
uv run pytest tests/unit/test_csv_export*.py tests/unit/test_step_specific_displays.py -v

# Phase 4 validation
uv run pytest tests/integration/ tests/performance/ -v

# Full validation
uv run pytest --tb=short
```