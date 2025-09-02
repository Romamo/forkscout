# Implementation Plan

- [x] 1. Update CSV export configuration system
  - Add commit_date_format configuration option to CSVExportConfig with default "%Y-%m-%d"
  - Remove any existing recent_commits column configuration options
  - Update configuration validation to handle new date format option
  - Write unit tests for updated configuration options
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [-] 2. Implement multi-row CSV formatting logic
- [x] 2.1 Create base fork data extraction method
  - Implement _extract_base_fork_data method to extract repository information that will be repeated across commit rows
  - Include all essential fork metadata (name, owner, stars, forks_count, commits_ahead, commits_behind, is_active, features_count)
  - Add support for optional fields based on configuration (URLs, detail mode fields)
  - Write unit tests for base data extraction with various fork configurations
  - _Requirements: 2.2, 2.3, 3.1, 3.2, 3.3_

- [-] 2.2 Implement commit row generation logic
  - Create _generate_fork_commit_rows method to expand single fork into multiple commit rows
  - Implement _create_commit_row method to combine base fork data with individual commit information
  - Add _create_empty_commit_row method for forks with no commits
  - Ensure consistent repository data duplication across all commit rows for the same fork
  - Write unit tests for commit row generation with various commit scenarios
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ] 2.3 Create commit data formatting methods
  - Implement _format_commit_date method using configurable date format (YYYY-MM-DD)
  - Create _format_commit_sha method to use 7-character short SHA format
  - Implement _escape_commit_message method to properly handle CSV special characters
  - Add proper handling of newlines, commas, and quotes in commit messages
  - Write unit tests for commit data formatting with edge cases
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 6.2, 6.3_

- [ ] 3. Update CSV export headers and structure
- [ ] 3.1 Create enhanced column header generation
  - Implement _generate_enhanced_fork_analysis_headers method for multi-row format
  - Replace "recent_commits" column with "commit_date", "commit_sha", "commit_description" columns
  - Maintain existing columns for repository information
  - Ensure header consistency with data row structure
  - Write unit tests for header generation in both traditional and enhanced formats
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 3.2 Replace main export method logic
  - Modify export_fork_analyses method to use only the new multi-row format
  - Remove old single-row formatting logic and recent_commits column handling
  - Replace existing row generation with new multi-row commit format
  - Update all CSV export methods to use the new format consistently
  - Write unit tests for updated export method with new format
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 4. Implement robust error handling and edge cases
- [ ] 4.1 Add graceful handling of missing commit data
  - Handle forks with no commits by creating single row with empty commit columns
  - Manage missing or invalid commit dates with empty values
  - Handle malformed commit SHAs gracefully
  - Ensure export continues when individual commits fail to process
  - Write unit tests for all edge case scenarios
  - _Requirements: 1.6, 6.1, 6.2, 6.4, 6.5_

- [ ] 4.2 Implement comprehensive CSV escaping
  - Ensure proper escaping of special characters in all text fields
  - Handle very long commit messages without truncation
  - Manage newlines and carriage returns in commit messages
  - Test CSV compatibility with major spreadsheet applications
  - Write unit tests for CSV escaping with various special character combinations
  - _Requirements: 1.5, 6.2, 6.3_

- [ ] 5. Update CLI commands and integration
- [ ] 5.1 Update all CSV export CLI commands
  - Update analyze command to use new CSV format by default
  - Update other CSV export commands (show-forks, etc.) to use new format
  - Remove any old format-related CLI options
  - Update CLI help text to describe the new multi-row commit format
  - Write integration tests for CLI commands with new format
  - _Requirements: 4.1, 4.2, 4.5_

- [ ] 5.2 Update CSV output manager integration
  - Modify CSVOutputManager to use new format configuration
  - Ensure proper configuration passing from CLI to exporter
  - Remove old format handling logic
  - Add logging for new format processing and statistics
  - Write integration tests for output manager with new format
  - _Requirements: 4.3, 4.4, 4.5_

- [ ] 6. Create comprehensive test suite
- [ ] 6.1 Implement unit tests for all new functionality
  - Test configuration enhancement with various option combinations
  - Test multi-row generation with different commit scenarios
  - Test commit data formatting with edge cases and special characters
  - Test header generation for both traditional and enhanced formats
  - Achieve comprehensive coverage of all new methods and logic paths
  - _Requirements: All requirements_

- [ ] 6.2 Add integration tests with real data
  - Test new CSV export format with actual repository data
  - Verify CSV compatibility with Excel, Google Sheets, and other tools
  - Test performance with large datasets containing many commits
  - Validate data consistency across multiple commit rows for same fork
  - Test migration from old format to new format
  - _Requirements: All requirements_

- [ ] 6.3 Create validation and edge case tests
  - Validate that repository information is identical across commit rows for same fork
  - Test chronological ordering of commits in multi-row format
  - Verify proper handling of forks with varying numbers of commits
  - Test edge cases like empty repositories and forks with no commits
  - Test data integrity and consistency in new format
  - _Requirements: 2.4, 2.5, 3.2, 3.3, 6.6_

- [ ] 7. Documentation and examples
- [ ] 7.1 Update CLI documentation
  - Update command help text to describe new multi-row commit format
  - Create examples showing the new CSV format structure
  - Document how to analyze the multi-row commit data effectively
  - Add troubleshooting guide for common CSV import issues
  - Update README with CSV export format changes
  - _Requirements: 4.5, 5.5_

- [ ] 7.2 Create usage examples and best practices
  - Provide sample CSV outputs showing the new format
  - Create examples of spreadsheet analysis workflows with commit rows
  - Document best practices for working with multi-row commit data
  - Add migration notes for users familiar with the old format
  - Include performance considerations for large datasets with many commits
  - _Requirements: 5.4, 5.5_