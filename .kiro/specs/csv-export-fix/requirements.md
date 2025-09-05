# Requirements Document

## Introduction

The CSV export functionality for the `show-forks` command is currently broken due to a mismatch between the data structure keys returned by the repository display service and what the CSV export logic expects. When users run commands like `forklift show-forks <repo> --csv --detail --ahead-only --show-commits=2`, no CSV output is generated because the export logic looks for a `"forks"` key in the returned data, but the actual key is `"collected_forks"`.

## Requirements

### Requirement 1

**User Story:** As a user running the show-forks command with CSV export, I want to receive proper CSV output so that I can process fork data programmatically.

#### Acceptance Criteria

1. WHEN I run `forklift show-forks <repo> --csv` THEN the system SHALL output valid CSV data to stdout
2. WHEN I run `forklift show-forks <repo> --csv --detail` THEN the system SHALL output detailed CSV data with exact commit counts
3. WHEN I run `forklift show-forks <repo> --csv --ahead-only` THEN the system SHALL output CSV data only for forks with commits ahead
4. WHEN I run `forklift show-forks <repo> --csv --show-commits=N` THEN the system SHALL include commit details in the CSV output
5. WHEN there are no forks to export THEN the system SHALL output CSV headers with no data rows

### Requirement 2

**User Story:** As a developer maintaining the CSV export functionality, I want consistent data structure handling so that CSV export works reliably across different display modes.

#### Acceptance Criteria

1. WHEN the repository display service returns fork data THEN the CSV export logic SHALL correctly access the fork data regardless of the method used (show_fork_data or show_fork_data_detailed)
2. WHEN the data structure contains `"collected_forks"` key THEN the CSV export SHALL use that key to access fork data
3. WHEN the data structure is empty or missing expected keys THEN the CSV export SHALL handle the error gracefully and output appropriate headers
4. WHEN debugging CSV export issues THEN the system SHALL provide clear error messages indicating the data structure mismatch

### Requirement 3

**User Story:** As a user combining multiple command flags, I want CSV export to work correctly with all flag combinations so that I can get the exact data I need.

#### Acceptance Criteria

1. WHEN I combine `--csv` with `--detail` THEN the system SHALL export detailed fork information with exact commit counts
2. WHEN I combine `--csv` with `--ahead-only` THEN the system SHALL export only forks that have commits ahead of the upstream
3. WHEN I combine `--csv` with `--show-commits=N` THEN the system SHALL include the last N commits for each fork in the CSV output
4. WHEN I combine `--csv` with `--force-all-commits` THEN the system SHALL fetch commits for all forks regardless of optimization
5. WHEN multiple flags are combined THEN the CSV output SHALL reflect all the requested filtering and data inclusion options

### Requirement 4

**User Story:** As a user redirecting CSV output to files, I want clean CSV data without informational messages so that the output files can be processed by CSV parsing tools.

#### Acceptance Criteria

1. WHEN I run `forklift show-forks <repo> --csv > output.csv` THEN the output file SHALL contain only valid CSV data
2. WHEN filtering is applied with `--ahead-only` THEN filtering statistics messages SHALL be sent to stderr, not stdout
3. WHEN CSV export is active THEN informational messages SHALL not contaminate the CSV output stream
4. WHEN I redirect stdout to a file THEN I SHALL still see filtering and progress messages on stderr
5. WHEN parsing the CSV output file THEN it SHALL be valid CSV format without any non-CSV content