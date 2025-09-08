# Requirements Document

## Introduction

This specification addresses the issue where commit messages are being truncated with "..." in the Recent Commits column when using the `show-forks` command with `--show-commits` option. Currently, the system calculates a maximum message length based on column width constraints and truncates commit messages that exceed this length, causing users to lose important information about what changes were made in each commit.

The issue is particularly problematic because:
1. Commit messages are truncated even when there's sufficient terminal space
2. The truncation happens at arbitrary character limits rather than natural word boundaries
3. Users cannot see the full commit message without additional commands
4. The truncation defeats the purpose of the `--show-commits` feature

## Requirements

### Requirement 1: Display Full Commit Messages

**User Story:** As a user, I want to see complete commit messages without truncation, so that I can understand what changes were made in each commit.

#### Acceptance Criteria

1. WHEN displaying commit messages THEN they SHALL be shown in full without truncation
2. WHEN commit messages are long THEN they SHALL wrap naturally or extend the column width
3. WHEN using `--show-commits` option THEN all commit message content SHALL be preserved
4. WHEN terminal width allows THEN commit messages SHALL not be artificially constrained

### Requirement 2: Remove Arbitrary Length Limits

**User Story:** As a user, I want commit message display to not be constrained by arbitrary character limits, so that I don't lose important information due to artificial truncation.

#### Acceptance Criteria

1. WHEN calculating column width THEN commit message length SHALL not be artificially limited
2. WHEN formatting commits THEN the `_truncate_commit_message` method SHALL not truncate content
3. WHEN displaying commits THEN natural content length SHALL determine display width
4. WHEN commit messages vary in length THEN each SHALL be displayed at its natural length

### Requirement 3: Preserve Existing Functionality

**User Story:** As an existing user, I want all current commit display functionality to work unchanged except for the removal of truncation, so that my workflows continue to function properly.

#### Acceptance Criteria

1. WHEN using `--show-commits=N` THEN exactly N commits SHALL be displayed per fork
2. WHEN commits have dates THEN they SHALL be formatted as "YYYY-MM-DD abc1234 message"
3. WHEN commits lack dates THEN they SHALL be formatted as "abc1234: message"
4. WHEN no commits are available THEN "[dim]No commits[/dim]" SHALL be displayed
5. WHEN commits are sorted THEN chronological ordering (newest first) SHALL be maintained

### Requirement 4: Maintain Table Structure

**User Story:** As a user, I want the table structure to remain intact and readable, so that the commit information is presented in an organized format.

#### Acceptance Criteria

1. WHEN displaying commit tables THEN column alignment SHALL remain correct
2. WHEN commit messages are long THEN table borders SHALL not break
3. WHEN content varies THEN table formatting SHALL remain consistent
4. WHEN multiple commits are shown THEN each SHALL be on a separate line within the cell

### Requirement 5: Handle Edge Cases Gracefully

**User Story:** As a user, I want the system to handle various commit message formats and lengths gracefully, so that the display works reliably across different repositories.

#### Acceptance Criteria

1. WHEN commit messages contain newlines THEN they SHALL be cleaned and joined with spaces
2. WHEN commit messages are empty THEN empty string SHALL be returned
3. WHEN commit messages contain special characters THEN they SHALL be displayed correctly
4. WHEN commit messages are very long THEN they SHALL be displayed without breaking the table structure

### Requirement 6: Backward Compatibility

**User Story:** As an existing user, I want all current command-line options and output formats to work unchanged, so that my existing scripts and workflows continue to function.

#### Acceptance Criteria

1. WHEN using existing command flags THEN they SHALL continue to work as expected
2. WHEN output is redirected to files THEN the format SHALL remain compatible
3. WHEN using CSV export THEN commit message formatting SHALL not affect export functionality
4. WHEN running in different terminal widths THEN the functionality SHALL work consistently