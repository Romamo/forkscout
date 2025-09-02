# Implementation Plan

- [ ] 1. Fix CLI parameter flow for CSV export mode
  - Modify `_show_forks_summary()` to properly handle CSV mode detection
  - Ensure `csv_export=True` parameter is passed to display service methods
  - Add proper console separation for CSV mode (stdout for CSV, stderr for status)
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ] 2. Correct data flow in CSV export functions
  - Fix `_export_forks_csv()` to properly collect and pass fork data
  - Ensure collected fork data is returned from display service methods
  - Add data conversion function for collected forks to CSV format
  - _Requirements: 2.1, 2.2, 2.3_

- [ ] 3. Enhance repository display service for CSV mode
  - Modify `show_fork_data_detailed()` to skip table rendering in CSV mode
  - Modify `show_fork_data()` to skip table rendering in CSV mode
  - Ensure `_render_fork_table()` returns early when `csv_export=True`
  - Return collected fork data in response dictionary for CSV processing
  - _Requirements: 1.1, 2.1, 2.2_

- [ ] 4. Fix CSV exporter empty data handling
  - Replace "No data to export" comment with proper empty CSV headers
  - Add `generate_empty_csv_with_headers()` method to CSVExporter
  - Modify `export_to_csv()` to use proper headers for empty data
  - Ensure headers match the configuration settings (commits, detail mode, etc.)
  - _Requirements: 2.4, 3.1, 3.2, 3.3, 3.4_

- [ ] 5. Enhance CSV output manager
  - Add `export_empty_csv_with_headers()` method to CSVOutputManager
  - Improve error handling to send errors to stderr in CSV mode
  - Add data conversion utilities for collected fork data
  - Ensure Unicode safety in CSV output
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 6. Add comprehensive error handling
  - Implement proper error routing to stderr in CSV mode
  - Add graceful handling of data collection failures
  - Add Unicode error handling with safe fallbacks
  - Ensure CSV output remains clean even when errors occur
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 7. Implement data conversion utilities
  - Create `_convert_collected_forks_to_csv_format()` function
  - Add proper handling of exact commit counts in CSV format
  - Implement commit data formatting for multi-row CSV export
  - Ensure all fork metadata is preserved during conversion
  - _Requirements: 2.1, 2.2, 3.1, 3.2, 3.3_

- [ ] 8. Add comprehensive unit tests
  - Test CLI parameter flow with `--csv` flag
  - Test data collection and conversion in CSV mode
  - Test empty data scenarios with proper header output
  - Test error handling with stderr routing
  - Test Unicode handling in CSV export
  - _Requirements: All requirements validation_

- [ ] 9. Add integration tests for CSV export
  - Test end-to-end CSV export with various flag combinations
  - Test `--detail --ahead-only --csv` scenario specifically
  - Test `--show-commits=N --csv` multi-row format
  - Test error scenarios and recovery
  - Verify no table output appears in CSV mode
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 10. Add contract tests for CSV format validation
  - Validate CSV headers match expected schema
  - Test CSV data integrity and completeness
  - Verify proper escaping and Unicode handling
  - Test compatibility with existing CSV processing tools
  - _Requirements: 3.1, 3.2, 3.3, 3.4_