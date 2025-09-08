# Implementation Plan

- [x] 1. Update Repository model validation to be more permissive
  - Modify `validate_github_name` method in `src/forklift/models/github.py` to log warnings instead of raising errors for consecutive periods
  - Keep strict validation only for patterns GitHub definitely doesn't allow (leading/trailing periods)
  - Add comprehensive logging for edge cases to help with debugging
  - _Requirements: 1.1, 2.1, 2.2, 3.1_

- [x] 2. Create ValidationHandler service for graceful error handling
  - Create new file `src/forklift/models/validation_handler.py` with ValidationHandler class
  - Implement `safe_create_repository` method that catches ValidationError and continues processing
  - Add error collection and summary reporting functionality
  - Create ValidationSummary model for structured error reporting
  - _Requirements: 4.1, 4.2, 4.3, 3.2_

- [x] 3. Update fork data collection to use graceful validation
  - Modify `collect_fork_data` method in `src/forklift/analysis/fork_data_collection_engine.py`
  - Integrate ValidationHandler to handle individual repository validation failures
  - Return both valid repositories and validation summary
  - Add logging for validation issues during processing
  - _Requirements: 1.2, 1.3, 4.1, 4.2_

- [x] 4. Update display service to show validation summaries
  - Modify `src/forklift/display/repository_display_service.py` to handle validation summaries
  - Add display of validation error summary when issues occur
  - Implement user-friendly messaging for validation issues
  - Add support for verbose error reporting
  - _Requirements: 1.4, 3.3, 3.4_

- [x] 5. Add comprehensive unit tests for validation handling
  - Create test file `tests/unit/test_repository_validation.py` with edge-case repository name tests
  - Test Repository model validation with various name patterns including consecutive periods
  - Test ValidationHandler error collection and summary generation
  - Create test fixtures with problematic repository names from real-world cases
  - _Requirements: 2.3, 4.4_

- [x] 6. Add integration tests for end-to-end validation handling
  - Create test file `tests/integration/test_validation_error_handling.py`
  - Test full fork processing pipeline with mixed valid/invalid repository data
  - Test display service behavior when validation errors occur
  - Verify that individual validation failures don't crash the entire process
  - _Requirements: 1.1, 1.2, 4.1, 4.2_

- [ ] 7. Add contract tests with real GitHub data
  - Create test file `tests/contract/test_github_repository_validation.py`
  - Test validation with real GitHub API responses including edge cases
  - Test specifically with the `maybe-finance/maybe` repository that caused the original issue
  - Verify that our validation rules match GitHub's actual behavior
  - _Requirements: 2.1, 2.2_

- [-] 8. Update CLI error handling and user messaging
  - Modify CLI command handlers to catch and display validation summaries
  - Add user-friendly error messages when validation issues occur
  - Implement verbose mode flag for detailed validation error reporting
  - Ensure proper exit codes and error reporting for different failure scenarios
  - _Requirements: 3.1, 3.2, 3.3, 3.4_