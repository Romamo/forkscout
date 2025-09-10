# Implementation Plan

- [x] 1. Update data models to support behind commits
  - Add `exact_commits_behind: int | None = None` field to `ForkData` class in `src/forkscout/models/fork_data.py`
  - Create new `CommitCountResult` dataclass with `ahead_count` and `behind_count` fields
  - Create new `BatchCommitCountResult` dataclass for batch operations
  - Update existing code that creates `ForkData` instances to handle the new field
  - _Requirements: 1.1, 1.2, 1.3, 4.1_

- [x] 2. Enhance GitHub client to extract behind commits from API
  - Update `get_commits_ahead` method in `src/forkscout/github/client.py` to extract `behind_by` field
  - Update `get_commits_ahead_batch` method to extract and return behind commit counts
  - Add error handling for missing `behind_by` field (default to 0)
  - Update method return types to use new `CommitCountResult` model
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 3. Update repository display service to store behind commits
  - Modify `_get_exact_commit_counts_batch` in `src/forkscout/display/repository_display_service.py` to store behind counts
  - Update fork data processing to set `exact_commits_behind` field from API results
  - Ensure backward compatibility with existing ahead-only logic
  - Add logging for behind commit counts in debug mode
  - _Requirements: 1.1, 1.2, 4.1, 4.2_

- [x] 4. Implement commit count display formatting with behind support
  - Create `_format_commit_count` method in display service to handle behind commits
  - Implement logic for "+9 -11", "-11", "+9", and "" display formats
  - Update table display to use new formatting method
  - Ensure consistent formatting across all display modes
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 5. Update CSV export to include behind commits
  - Modify CSV exporter in `src/forkscout/reporting/csv_exporter.py` to use new commit formatting
  - Ensure CSV output shows behind commits in same format as table display
  - Test CSV export with forks that have behind commits
  - Verify CSV parsing compatibility with external tools
  - _Requirements: 3.4_

- [x] 6. Update filtering logic for --ahead-only flag compatibility
  - Ensure `--ahead-only` flag still works correctly with behind commits
  - Forks with both ahead and behind commits should be included (they have ahead commits)
  - Forks with only behind commits should be excluded
  - Update filtering logic in fork qualification engine if needed
  - _Requirements: 4.2, 4.3_

- [x] 7. Add comprehensive unit tests for behind commits functionality
  - Test `CommitCountResult` and `BatchCommitCountResult` models
  - Test GitHub client methods extract behind counts correctly
  - Test display formatting for all combinations (ahead-only, behind-only, both, neither)
  - Test CSV export formatting includes behind commits
  - Test error handling when `behind_by` field is missing
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 5.1, 5.2_

- [x] 8. Add integration tests with real GitHub data
  - Test with GreatBots/YouTube_bot_telegram fork that has behind commits (ahead=9, behind=11)
  - Test with forks that have only ahead commits (ensure no regression)
  - Test with forks that have only behind commits
  - Test batch processing correctly handles mixed scenarios
  - Verify API response parsing works with real GitHub data
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 9. Add contract tests for GitHub API behind_by field
  - Test that GitHub compare API still returns `behind_by` field
  - Test that `behind_by` field is always a non-negative integer
  - Test different fork scenarios (ahead, behind, diverged, identical)
  - Add monitoring for API response format changes
  - _Requirements: 2.1, 2.2, 5.3_

- [x] 10. Validate fix with original bug report scenario
  - Test the exact command: `uv run forkscout show-forks https://github.com/sanila2007/youtube-bot-telegram --detail --ahead-only --show-commits=2`
  - Verify GreatBots fork now shows "+9 -11" instead of just "+9"
  - Verify other forks display correctly with behind commits
  - Test CSV export includes behind commits
  - Ensure no regression in existing functionality
  - _Requirements: 1.1, 1.2, 1.3, 3.1, 3.2, 3.4_

- [x] 11. Add error handling and edge case tests
  - Test behavior when compare API fails
  - Test behavior when `behind_by` field is missing from response
  - Test behavior with network timeouts and retries
  - Test behavior with invalid or malformed API responses
  - Ensure graceful fallback to "Unknown" display when errors occur
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 12. Update documentation and help text
  - Update CLI help text to mention behind commits display
  - Add examples of behind commits display format to documentation
  - Update troubleshooting guide for commit counting issues
  - Add explanation of "+X -Y" format in user documentation
  - _Requirements: 3.1, 3.2_