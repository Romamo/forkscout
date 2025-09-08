# Implementation Plan

- [x] 1. Remove commit message truncation logic
  - Remove the `_truncate_commit_message()` method from RepositoryDisplayService class
  - Update `format_recent_commits()` method to use full cleaned messages without truncation
  - Preserve existing message cleaning logic (whitespace normalization, newline removal)
  - _Requirements: 1.1, 2.1, 2.2_

- [-] 2. Update commit message formatting to use full content
  - Modify the commit formatting logic to use cleaned messages directly
  - Remove `max_message_length` calculation and usage in commit formatting
  - Ensure both date-based format ("YYYY-MM-DD abc1234 message") and fallback format ("abc1234: message") use full messages
  - _Requirements: 1.1, 1.3, 3.2, 3.3_

- [ ] 3. Create message cleaning helper method
  - Extract message cleaning logic into a separate `_clean_commit_message()` method
  - Implement whitespace normalization and newline removal
  - Handle empty and null message edge cases
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 4. Update column width calculation logic
  - Review `calculate_commits_column_width()` method to remove message length constraints
  - Maintain minimum and maximum width bounds for table structure
  - Ensure column width calculation focuses on table layout rather than content truncation
  - _Requirements: 2.1, 4.1, 4.3_

- [ ] 5. Add unit tests for non-truncated commit formatting
  - Test that long commit messages are displayed without "..." truncation
  - Test that message cleaning logic works correctly (newlines, whitespace)
  - Test that commit format structure remains unchanged (date, hash, message)
  - Test edge cases (empty messages, special characters, very long messages)
  - _Requirements: 1.1, 2.2, 5.1, 5.2, 5.3, 5.4_

- [ ] 6. Add integration tests for full commit display
  - Test `show-forks` command with `--show-commits` option using real repositories
  - Verify that no commit messages contain "..." truncation in output
  - Test with repositories known to have long commit messages
  - Verify table structure remains intact with varying message lengths
  - _Requirements: 1.1, 1.4, 4.1, 4.2_

- [ ] 7. Test backward compatibility and existing functionality
  - Verify all existing command-line options work unchanged
  - Test chronological sorting (newest first) is preserved
  - Test date formatting ("YYYY-MM-DD") remains consistent
  - Test fallback formatting for commits without dates
  - Test "[dim]No commits[/dim]" display for empty commit lists
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 6.1, 6.2, 6.3, 6.4_

- [ ] 8. Validate table structure and formatting integrity
  - Test that table columns remain properly aligned with long commit messages
  - Verify table borders and formatting remain intact
  - Test with various terminal widths to ensure consistent behavior
  - Confirm that Rich table rendering handles long content appropriately
  - _Requirements: 4.1, 4.2, 4.3, 4.4_