# Requirements Document

## Introduction

This specification replaces the current CSV export functionality in the Forkscout tool to provide better commit information display. Currently, the CSV export includes a single "recent_commits" column that contains concatenated commit data. This enhancement will completely replace that approach by splitting commit information into separate columns (date, SHA, description) and displaying each commit on its own row, while keeping repository information clean and complete on every row.

The enhancement focuses on improving the readability and usability of CSV exports for repository maintainers who need to analyze commit data in spreadsheet applications or other data analysis tools. The new format becomes the default and only CSV export format.

## Requirements

### Requirement 1

**User Story:** As a repository maintainer, I want commit information in CSV exports to be split into separate columns for date, SHA, and description, so that I can easily sort, filter, and analyze commit data in spreadsheet applications.

#### Acceptance Criteria

1. WHEN exporting fork data with commits THEN the system SHALL create separate columns for commit_date, commit_sha, and commit_description instead of a single recent_commits column
2. WHEN displaying commit information THEN the system SHALL format commit_date as YYYY-MM-DD for consistent sorting in spreadsheet applications
3. WHEN showing commit SHA THEN the system SHALL use the short 7-character SHA format for readability while maintaining uniqueness
4. WHEN displaying commit descriptions THEN the system SHALL show the full commit message without truncation or modification
5. WHEN commits contain newlines or special characters THEN the system SHALL properly escape them for CSV compatibility
6. WHEN no commits are available for a fork THEN the system SHALL leave the commit columns empty but still include the fork row

### Requirement 2

**User Story:** As a repository maintainer, I want each commit to appear on its own row in the CSV export, so that I can analyze individual commits without parsing concatenated data.

#### Acceptance Criteria

1. WHEN a fork has multiple commits THEN the system SHALL create one row per commit with each commit's individual data
2. WHEN creating multiple rows for the same fork THEN the system SHALL repeat the repository information (fork name, owner, stars, etc.) on each commit row
3. WHEN displaying fork information across multiple commit rows THEN the system SHALL ensure all fork metadata is identical and consistent
4. WHEN a fork has no commits THEN the system SHALL create a single row with fork information and empty commit columns
5. WHEN commits are displayed in multiple rows THEN the system SHALL order them chronologically with newest commits first

### Requirement 3

**User Story:** As a repository maintainer, I want the CSV export to maintain clean repository information without duplication markers, so that the data is ready for use in analysis tools without additional processing.

#### Acceptance Criteria

1. WHEN creating multiple rows for the same fork THEN the system SHALL NOT use empty cells or special markers to indicate repeated information
2. WHEN displaying repository data across commit rows THEN the system SHALL include complete fork information on every row
3. WHEN exporting to CSV THEN the system SHALL ensure each row is self-contained with all necessary context information
4. WHEN importing the CSV into spreadsheet applications THEN users SHALL be able to sort and filter without losing repository context
5. WHEN analyzing the CSV data THEN each row SHALL contain complete information for both the fork and the specific commit

### Requirement 4

**User Story:** As a repository maintainer, I want the enhanced CSV format to be the default behavior, so that I always get the most useful commit data structure without needing special flags.

#### Acceptance Criteria

1. WHEN using CSV export THEN the system SHALL always use the new multi-row commit format by default
2. WHEN exporting fork data with commits THEN the system SHALL automatically use the new column structure (commit_date, commit_sha, commit_description)
3. WHEN any CSV export operation includes commits THEN the system SHALL consistently apply the multi-row format
4. WHEN the system processes commit data THEN it SHALL replace the old recent_commits column approach entirely
5. WHEN users export CSV data THEN they SHALL receive the enhanced format without needing to specify additional flags

### Requirement 5

**User Story:** As a repository maintainer, I want clear column headers in the enhanced CSV format, so that I can easily understand and work with the exported data.

#### Acceptance Criteria

1. WHEN using the enhanced format THEN the system SHALL use clear column headers: "Fork Name", "Owner", "Stars", "Forks Count", "Commit Date", "Commit SHA", "Commit Description"
2. WHEN exporting with commit rows THEN the system SHALL ensure column headers accurately describe the data format
3. WHEN viewing the CSV in spreadsheet applications THEN the column headers SHALL be descriptive and self-explanatory
4. WHEN analyzing exported data THEN users SHALL be able to understand the data structure without additional documentation
5. WHEN column headers are displayed THEN they SHALL follow consistent naming conventions and formatting

### Requirement 6

**User Story:** As a repository maintainer, I want the enhanced CSV export to handle edge cases gracefully, so that the export process is reliable regardless of commit data variations.

#### Acceptance Criteria

1. WHEN commits have missing dates THEN the system SHALL use empty values in the commit_date column rather than failing
2. WHEN commit messages contain CSV special characters (commas, quotes, newlines) THEN the system SHALL properly escape them according to CSV standards
3. WHEN forks have very long commit messages THEN the system SHALL include the full message without truncation
4. WHEN commits have unusual SHA formats THEN the system SHALL handle them gracefully and display available information
5. WHEN export encounters errors for individual commits THEN the system SHALL continue processing remaining commits and log the errors
6. WHEN no commits are found for any forks THEN the system SHALL create a valid CSV with fork information and empty commit columns
