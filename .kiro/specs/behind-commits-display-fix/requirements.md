# Requirements Document

## Introduction

This specification addresses the missing behind commits display functionality in forkscout. Currently, when a fork has commits behind the parent repository (as indicated by the `behind_by` field in GitHub's compare API), forkscout only shows the ahead commits (+X) but completely ignores the behind commits (-Y). The system should display both ahead and behind commits in the format "+X -Y" when both exist, or just "-Y" when only behind commits exist.

## Requirements

### Requirement 1: Display Behind Commits Count

**User Story:** As a user analyzing forks, I want to see when forks are behind the parent repository, so that I can understand which forks are missing recent updates from the parent.

#### Acceptance Criteria

1. WHEN a fork has commits behind the parent THEN the system SHALL display the number of commits behind (e.g., "-11", "-5", "-23")
2. WHEN a fork has both ahead and behind commits THEN the system SHALL display both counts (e.g., "+9 -11", "+5 -2")
3. WHEN a fork has only behind commits (no ahead) THEN the system SHALL display only the behind count (e.g., "-15")
4. WHEN a fork has no commits ahead or behind THEN the system SHALL display an empty commits column
5. WHEN using the `--detail` flag THEN behind commit counts SHALL be fetched from the GitHub compare API `behind_by` field

### Requirement 2: Extract Behind Commits from GitHub API

**User Story:** As a developer, I want the system to use the `behind_by` field from GitHub's compare API response, so that behind commit counts are accurate and efficient to fetch.

#### Acceptance Criteria

1. WHEN making compare API calls THEN the system SHALL extract the `behind_by` field from the response
2. WHEN a fork has `behind_by > 0` THEN the system SHALL store and display this count
3. WHEN the compare API returns `status: "diverged"` THEN the system SHALL handle both ahead and behind counts
4. WHEN the compare API returns `status: "behind"` THEN the system SHALL display only the behind count

### Requirement 3: Update Display Formatting for Behind Commits

**User Story:** As a user, I want behind commits to be clearly distinguishable from ahead commits in the display, so that I can quickly identify which forks need updates.

#### Acceptance Criteria

1. WHEN displaying behind commits THEN the system SHALL use a minus sign prefix (e.g., "-11")
2. WHEN displaying both ahead and behind THEN the system SHALL use the format "+X -Y" with a space separator
3. WHEN exporting to CSV THEN behind commits SHALL be included in the commits column using the same format
4. WHEN using compact display mode THEN behind commits SHALL be shown in the same format as detailed mode

### Requirement 4: Backward Compatibility with Existing Ahead-Only Logic

**User Story:** As a user with existing workflows, I want the ahead commits functionality to continue working exactly as before, so that my current usage is not disrupted.

#### Acceptance Criteria

1. WHEN a fork has only ahead commits THEN the display SHALL remain unchanged (e.g., "+9")
2. WHEN using `--ahead-only` flag THEN forks with only behind commits SHALL be filtered out
3. WHEN using `--ahead-only` flag THEN forks with both ahead and behind SHALL be included (because they have ahead commits)
4. WHEN existing tests run THEN they SHALL continue to pass without modification

### Requirement 5: Error Handling for Behind Commits

**User Story:** As a user, I want clear error handling when behind commit counting fails, so that I understand why some forks show incomplete information.

#### Acceptance Criteria

1. WHEN compare API fails THEN the system SHALL display "Unknown" for the entire commits column
2. WHEN `behind_by` field is missing from API response THEN the system SHALL assume 0 behind commits
3. WHEN network errors occur THEN the system SHALL retry and fall back gracefully
4. WHEN rate limits are hit THEN the system SHALL handle gracefully without crashing