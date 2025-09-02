# Requirements Document

## Introduction

This specification addresses a critical bug in the CSV export functionality of the `forklift show-forks` command. Currently, when users run the command with the `--csv` flag, they see both a table display and a "No data to export" message instead of proper CSV output. This breaks the intended functionality where CSV export should suppress all interactive elements and output only clean CSV data to stdout.

## Requirements

### Requirement 1: CSV Export Mode Detection

**User Story:** As a user, I want the `--csv` flag to properly suppress all table displays and interactive elements, so that I get clean CSV output suitable for data processing.

#### Acceptance Criteria

1. WHEN I run `forklift show-forks <repo-url> --csv` THEN the system SHALL suppress all table displays and progress indicators
2. WHEN using `--csv` flag THEN the system SHALL output only CSV data to stdout with no additional formatting or messages
3. WHEN CSV export is enabled THEN the system SHALL redirect all status messages and progress indicators to stderr or suppress them entirely
4. WHEN CSV export mode is active THEN the system SHALL NOT display Rich tables, panels, or other formatted output to stdout

### Requirement 2: Data Flow Correction

**User Story:** As a user, I want the collected fork data to be properly passed to the CSV exporter, so that I get the actual fork information in CSV format instead of "No data to export".

#### Acceptance Criteria

1. WHEN fork data is successfully collected THEN the system SHALL pass this data to the CSV exporter
2. WHEN using `--detail --ahead-only --csv` flags THEN the system SHALL export the filtered forks with exact commit counts to CSV
3. WHEN forks with commits ahead are found THEN the CSV output SHALL contain these forks with their commit information
4. WHEN no forks are found after filtering THEN the system SHALL output CSV headers only without the "No data to export" comment

### Requirement 3: CSV Output Format Consistency

**User Story:** As a user, I want the CSV export to include all the same data that would be displayed in the table format, so that I can process the complete fork information programmatically.

#### Acceptance Criteria

1. WHEN exporting with `--detail` flag THEN the CSV SHALL include exact commit counts ahead for each fork
2. WHEN exporting with `--show-commits=N` flag THEN the CSV SHALL include commit information in the multi-row format
3. WHEN exporting with `--ahead-only` flag THEN the CSV SHALL only include forks that have commits ahead
4. WHEN all flags are combined THEN the CSV output SHALL reflect the same filtering and data collection as the table display

### Requirement 4: Error Handling in CSV Mode

**User Story:** As a user, I want proper error handling during CSV export, so that errors don't corrupt the CSV output and are reported appropriately.

#### Acceptance Criteria

1. WHEN errors occur during CSV export THEN error messages SHALL be sent to stderr, not stdout
2. WHEN data collection fails THEN the system SHALL output empty CSV with headers and report errors to stderr
3. WHEN individual fork processing fails THEN the system SHALL continue with remaining forks and log errors to stderr
4. WHEN CSV export encounters Unicode errors THEN the system SHALL handle them gracefully without corrupting the output

### Requirement 5: Integration with Existing Flags

**User Story:** As a user, I want all existing command flags to work correctly with CSV export, so that I can filter and customize the CSV output as needed.

#### Acceptance Criteria

1. WHEN using `--max-forks=N --csv` THEN the CSV SHALL contain at most N forks
2. WHEN using `--ahead-only --csv` THEN the CSV SHALL only contain forks with commits ahead
3. WHEN using `--detail --csv` THEN the CSV SHALL include exact commit counts and detailed information
4. WHEN using `--show-commits=N --csv` THEN the CSV SHALL use multi-row format with commit details
5. WHEN using `--force-all-commits --csv` THEN the CSV SHALL include commits for all forks regardless of ahead status