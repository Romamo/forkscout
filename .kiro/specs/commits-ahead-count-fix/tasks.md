# Implementation Plan

- [x] 1. Fix GitHub Client Commit Counting Logic
  - Update `get_commits_ahead` method to use `ahead_by` field from compare API response
  - Update `get_commits_ahead_batch` method to use `ahead_by` field instead of counting commits array
  - Add proper error handling for cases where `ahead_by` field is missing
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Add New Count-Only Methods to GitHub Client
  - Create `get_commits_ahead_count` method that returns only the count without commit details
  - Create `get_commits_ahead_batch_counts` method for efficient batch counting
  - Implement proper caching and API optimization for batch operations
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 3. Update Repository Display Service Counting Logic
  - Fix `_get_exact_commit_counts_batch` method to use correct counting logic
  - Remove hardcoded `count=1` parameter that causes the bug
  - Update fork data processing to use accurate commit counts
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [-] 4. Add Configuration Support for Commit Counting
  - Create `CommitCountConfig` dataclass for configurable limits
  - Add CLI options for `--max-commits-count` and `--commit-display-limit`
  - Integrate configuration into repository display service
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 5. Enhance Error Handling for Commit Operations
  - Add specific error handling for private repositories and access issues
  - Implement graceful degradation when comparison fails
  - Add proper error messages and logging for debugging
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ] 6. Add Comprehensive Unit Tests for Commit Counting
  - Test `get_commits_ahead_count` method with various scenarios
  - Test batch counting methods for accuracy and efficiency
  - Test error handling for different failure modes
  - _Requirements: 1.1, 1.2, 2.1, 2.2_

- [ ] 7. Add Integration Tests with Real GitHub Data
  - Test with real repositories that have known commit counts
  - Verify that fixed logic shows correct "+5", "+12", "+23" instead of "+1"
  - Test the specific case mentioned in bug report: `sanila2007/youtube-bot-telegram`
  - _Requirements: 1.1, 1.4_

- [ ] 8. Add Performance and Contract Tests
  - Add performance tests to ensure batch operations are efficient
  - Add contract tests to verify GitHub API response format hasn't changed
  - Test API call optimization and rate limit handling
  - _Requirements: 2.1, 2.2, 2.3_

- [ ] 9. Update Documentation and Help Text
  - Update CLI help text to explain new commit counting options
  - Add documentation for configuration options
  - Update troubleshooting guide for commit counting issues
  - _Requirements: 4.1, 4.2, 5.1_

- [ ] 10. Validate Fix with Original Bug Report
  - Test the exact command from bug report: `uv run forklift show-forks https://github.com/sanila2007/youtube-bot-telegram --detail --ahead-only`
  - Verify that forks now show correct commit counts instead of all "+1"
  - Ensure no regression in other functionality
  - _Requirements: 1.1, 1.2, 1.3, 1.4_