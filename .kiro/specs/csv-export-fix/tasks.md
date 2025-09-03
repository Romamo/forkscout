# Implementation Plan

- [x] 1. Fix CSV export data structure key mismatch
  - Fix the key access in `_export_forks_csv` function to use `"collected_forks"` instead of `"forks"`
  - Add backward compatibility for both key names
  - Add proper error handling for missing or invalid data structures
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3_

- [x] 2. Add data structure validation helper function
  - Create `_validate_fork_data_structure` function to safely extract fork data
  - Handle multiple possible key names for robustness
  - Add logging for unexpected data structures
  - Return empty list for invalid structures to allow graceful degradation
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 3. Enhance error handling and logging
  - Add detailed error messages for CSV export failures
  - Log data structure information for debugging
  - Ensure errors are sent to stderr while keeping stdout clean for CSV
  - Add proper exception handling with ForkliftOutputError
  - _Requirements: 2.4, 1.5_

- [x] 4. Create unit tests for CSV export fix
  - Test `_validate_fork_data_structure` with various input structures
  - Test CSV export with `"collected_forks"` key
  - Test CSV export with `"forks"` key (backward compatibility)
  - Test error handling for invalid data structures
  - Test empty data handling
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3_

- [x] 5. Create integration tests for CSV export functionality
  - Test full CSV export flow with real repository data
  - Test CSV export with `--detail` flag
  - Test CSV export with `--ahead-only` flag
  - Test CSV export with `--show-commits=N` flag
  - Test CSV export with multiple flag combinations
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 6. Add end-to-end validation tests
  - Test complete command execution with CSV output to stdout
  - Test CSV output redirection to files
  - Test CSV parsing by external tools to ensure valid format
  - Test with the original failing command: `forklift show-forks https://github.com/sanila2007/youtube-bot-telegram --detail --ahead-only --csv --show-commits=2`
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 3.1, 3.2, 3.3, 3.4, 3.5_