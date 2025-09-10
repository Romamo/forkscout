# Requirements Document

## Introduction

The `forkscout show-forks` command fails when processing repositories that contain forks with names that violate our current GitHub name validation rules. Specifically, the command fails with a Pydantic validation error when encountering repository names with consecutive periods (e.g., `maybe-finance.._..maybe`), even though such names appear to exist in the GitHub API response.

This issue prevents users from analyzing repositories that have forks with edge-case naming patterns, making the tool unreliable for real-world usage.

## Requirements

### Requirement 1

**User Story:** As a user, I want the `forkscout show-forks` command to handle all valid GitHub repository names returned by the GitHub API, so that the tool doesn't crash on edge-case naming patterns.

#### Acceptance Criteria

1. WHEN the GitHub API returns a repository name with consecutive periods THEN the system SHALL either accept the name if it's valid according to GitHub's actual rules OR sanitize the name to make it valid
2. WHEN processing fork data with edge-case repository names THEN the system SHALL continue processing other forks instead of failing completely
3. WHEN encountering invalid repository names THEN the system SHALL log a warning but continue execution
4. WHEN displaying results THEN the system SHALL show all processable forks even if some had naming issues

### Requirement 2

**User Story:** As a developer, I want the Repository model validation to accurately reflect GitHub's actual naming rules, so that the validation doesn't reject legitimate GitHub data.

#### Acceptance Criteria

1. WHEN validating repository names THEN the system SHALL use validation rules that match GitHub's actual repository naming constraints
2. WHEN GitHub's naming rules are unclear THEN the system SHALL be permissive and allow names that appear in real GitHub API responses
3. WHEN validation rules are updated THEN the system SHALL maintain backward compatibility with existing cached data
4. WHEN encountering edge cases THEN the system SHALL prioritize functionality over strict validation

### Requirement 3

**User Story:** As a user, I want detailed error information when repository processing fails, so that I can understand what went wrong and potentially work around the issue.

#### Acceptance Criteria

1. WHEN a repository name validation fails THEN the system SHALL log the specific repository name and validation error
2. WHEN continuing after validation errors THEN the system SHALL report how many repositories were skipped due to validation issues
3. WHEN displaying results THEN the system SHALL include a summary of any processing issues encountered
4. WHEN validation errors occur THEN the system SHALL provide actionable information about the issue

### Requirement 4

**User Story:** As a developer, I want robust error handling for data validation issues, so that individual bad data points don't crash the entire analysis.

#### Acceptance Criteria

1. WHEN processing a list of repositories THEN the system SHALL handle validation errors for individual repositories gracefully
2. WHEN a validation error occurs THEN the system SHALL continue processing the remaining repositories
3. WHEN multiple validation errors occur THEN the system SHALL collect and report all errors at the end
4. WHEN all repositories fail validation THEN the system SHALL provide a clear error message explaining the issue