# Implementation Plan

- [x] 1. Analyze current CSV export structure and data availability
  - Examine ForkPreviewItem model to verify all required fields are available (fork_url, stars, forks_count, commits_ahead, commits_behind)
  - Review current _generate_forks_preview_headers() method implementation
  - Analyze _format_fork_preview_row() method to understand current data mapping
  - Document current column order and identify changes needed
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1_

- [x] 2. Update CSV header generation for new column structure
- [x] 2.1 Modify _generate_forks_preview_headers method
  - Update column order to place "Fork URL" first
  - Change column names to proper title case with spaces ("Fork URL", "Stars", "Forks")
  - Remove "fork_name", "owner", and "activity_status" from headers
  - Add "Forks" column after "Stars" column
  - Split commits_ahead into "Commits Ahead" and "Commits Behind" columns
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 3.2, 3.3, 4.2, 4.3, 5.2, 5.3, 5.4, 5.5, 5.6_

- [x] 2.2 Update header generation for different export modes
  - Ensure new headers work with include_urls configuration
  - Verify detail_mode still adds appropriate additional columns
  - Test header generation with various CSVExportConfig options
  - Maintain backward compatibility with existing configuration options
  - _Requirements: 6.1, 6.2_

- [x] 3. Update CSV row data formatting for new structure
- [x] 3.1 Modify _format_fork_preview_row method
  - Reorder data mapping to match new header structure
  - Map fork_url to "Fork URL" as first column
  - Map stars to "Stars" column
  - Map forks_count to new "Forks" column
  - Map commits_ahead to "Commits Ahead" column
  - Add mapping for "Commits Behind" column from available data
  - _Requirements: 1.2, 1.3, 3.2, 3.3, 4.2, 4.3_

- [x] 3.2 Remove obsolete column mappings
  - Remove fork_name from row data mapping
  - Remove owner from row data mapping
  - Remove activity_status from row data mapping
  - Ensure no data loss by verifying essential info is preserved in remaining columns
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ] 4. Implement error handling for missing data
- [ ] 4.1 Add graceful handling for missing Fork URL
  - Handle cases where fork_url is None or empty
  - Provide empty string fallback for missing URLs
  - Log warnings for missing URL data without failing export
  - Ensure export continues when URLs are unavailable
  - _Requirements: 1.4, 1.5_

- [ ] 4.2 Add handling for missing Forks count data
  - Handle cases where forks_count is None or unavailable
  - Provide 0 or empty string fallback for missing fork counts
  - Attempt to use repository.forks_count as fallback if available
  - Log info messages for missing forks count data
  - _Requirements: 4.4, 4.5_

- [ ] 4.3 Add handling for missing Commits Behind data
  - Handle cases where commits_behind data is not available
  - Provide empty string fallback for missing commits behind
  - Attempt to calculate from available commit data if possible
  - Ensure Commits Ahead and Commits Behind columns work independently
  - _Requirements: 3.4, 3.5_

- [x] 5. Create comprehensive unit tests for new column structure
- [x] 5.1 Test new header generation
  - Test column order matches specification exactly
  - Test column names use proper title case with spaces
  - Test removed columns are not present in headers
  - Test new "Forks" column is positioned correctly after "Stars"
  - Test "Commits Ahead" and "Commits Behind" columns are both present
  - _Requirements: 1.1, 2.1, 2.2, 2.3, 3.2, 3.3, 4.2, 5.2, 5.3, 5.4, 5.5, 5.6_

- [x] 5.2 Test data mapping for new structure
  - Test Fork URL appears in first column with correct data
  - Test Stars and Forks columns contain correct numeric data
  - Test Commits Ahead and Commits Behind contain correct values
  - Test data integrity is maintained across format change
  - Test empty/missing data scenarios are handled gracefully
  - _Requirements: 1.2, 1.3, 1.4, 3.2, 3.3, 3.4, 3.5, 4.2, 4.3, 4.4, 4.5_

- [x] 5.3 Test configuration compatibility
  - Test include_urls configuration still works correctly
  - Test detail_mode configuration adds appropriate columns
  - Test various CSVExportConfig combinations work with new format
  - Test backward compatibility with existing configuration options
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 6. Create integration tests for end-to-end functionality
- [x] 6.1 Test complete CSV export workflow
  - Test show-forks command with --csv flag produces new format
  - Test CSV output can be successfully parsed by CSV libraries
  - Test data integrity from fork data through to CSV output
  - Test performance with various dataset sizes
  - _Requirements: 6.1, 6.2, 6.4_

- [x] 6.2 Test CLI integration with new format
  - Test show-forks --csv command produces correct column order
  - Test combination with --detail flag works correctly
  - Test combination with --ahead-only flag works correctly
  - Test output redirection to files works properly
  - _Requirements: 6.2, 6.3, 6.4_

- [x] 6.3 Test spreadsheet application compatibility
  - Test CSV import into Microsoft Excel
  - Test CSV import into Google Sheets
  - Test CSV import into LibreOffice Calc
  - Test column auto-detection and formatting in spreadsheet apps
  - Verify headers are immediately understandable without modification
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.3_

- [ ] 7. Update documentation and examples
- [ ] 7.1 Update CLI help text and documentation
  - Update command help text to describe new CSV column structure
  - Create before/after examples showing the format change
  - Document the new column order and naming conventions
  - Add migration notes for users familiar with old format
  - _Requirements: 6.2, 6.3_

- [ ] 7.2 Create usage examples and validation
  - Provide sample CSV outputs showing the new format
  - Create examples of common spreadsheet analysis workflows
  - Document best practices for working with the new column structure
  - Add troubleshooting guide for common CSV import issues
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.3, 6.4_