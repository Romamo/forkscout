# Requirements Document

## Introduction

This specification addresses a critical bug in the commit counting logic where forks consistently show only "+1" commits ahead regardless of the actual number of commits they have ahead of the parent repository. The issue stems from hardcoded `count=1` parameter in the `get_commits_ahead_batch` method call, which limits the API response to only 1 commit, causing the system to incorrectly calculate the total commits ahead as 1 even when forks have multiple commits ahead.

## Requirements

### Requirement 1: Accurate Commit Count Display

**User Story:** As a user analyzing forks, I want to see the correct number of commits ahead for each fork, so that I can accurately assess the development activity and divergence from the parent repository.

#### Acceptance Criteria

1. WHEN a fork has multiple commits ahead of the parent THEN the system SHALL display the actual number of commits ahead (e.g., "+5", "+12", "+23")
2. WHEN a fork has only 1 commit ahead THEN the system SHALL display "+1" 
3. WHEN a fork has no commits ahead THEN the system SHALL display an empty commits column or "0"
4. WHEN using the `--ahead-only` flag THEN only forks with commits ahead SHALL be displayed with accurate commit counts

### Requirement 2: Efficient API Usage for Commit Counting

**User Story:** As a system administrator, I want the commit counting to be efficient with GitHub API calls, so that we don't exceed rate limits while still getting accurate data.

#### Acceptance Criteria

1. WHEN determining commits ahead THEN the system SHALL use the GitHub compare API to get the total count without fetching all commit details
2. WHEN batch processing forks THEN the system SHALL optimize API calls by reusing parent repository data
3. WHEN a fork has many commits ahead (>100) THEN the system SHALL still report the accurate count without fetching all commit objects
4. WHEN API rate limits are approached THEN the system SHALL handle gracefully with appropriate error messages

### Requirement 3: Backward Compatibility for Detailed Commit Display

**User Story:** As a user who needs detailed commit information, I want the system to still fetch actual commit details when requested, so that I can see commit messages and other metadata.

#### Acceptance Criteria

1. WHEN detailed commit information is needed THEN the system SHALL fetch the appropriate number of commit objects based on display requirements
2. WHEN showing recent commits in tables THEN the system SHALL limit fetched commits to the display limit (e.g., 3-5 commits for table display)
3. WHEN exporting to CSV with commit details THEN the system SHALL fetch the requested number of commits per the configuration
4. WHEN using interactive mode THEN users SHALL be able to request different levels of commit detail

### Requirement 4: Configuration for Commit Count Limits

**User Story:** As a user, I want to configure how many commits ahead are counted and displayed, so that I can balance between accuracy and performance based on my needs.

#### Acceptance Criteria

1. WHEN counting commits ahead THEN the system SHALL support a configurable maximum count limit (default: 100)
2. WHEN a fork exceeds the maximum count THEN the system SHALL display "100+" or similar indicator
3. WHEN performance is critical THEN users SHALL be able to set lower limits for faster processing
4. WHEN accuracy is critical THEN users SHALL be able to set higher limits or unlimited counting

### Requirement 5: Error Handling for Commit Counting

**User Story:** As a user, I want clear error messages when commit counting fails, so that I can understand why some forks show "Unknown" commit counts.

#### Acceptance Criteria

1. WHEN a fork repository is private or inaccessible THEN the system SHALL display "Unknown" in the commits column
2. WHEN API errors occur during comparison THEN the system SHALL log the error and continue processing other forks
3. WHEN network timeouts occur THEN the system SHALL retry with exponential backoff before marking as failed
4. WHEN comparison fails due to divergent histories THEN the system SHALL handle gracefully and report the limitation