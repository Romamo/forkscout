# Requirements Document

## Introduction

This specification addresses the need to adjust the logging level for a specific error message in the GitHub API rate limiter. The error message "Non-retryable error in GET repos/*/: Resource not found" is currently logged at ERROR level, but should be logged at WARNING level since "resource not found" errors are expected during repository analysis.

## Requirements

### Requirement 1

**User Story:** As a system administrator monitoring application logs, I want the specific "Resource not found" error message to be logged at WARNING level instead of ERROR level, so that it doesn't trigger unnecessary error alerts.

#### Acceptance Criteria

1. WHEN a GitHubNotFoundError occurs in the rate limiter THEN the system SHALL log the "Non-retryable error" message at WARNING level instead of ERROR level
2. WHEN the error message is "Resource not found" THEN the system SHALL use logger.warning() instead of logger.error()
3. WHEN the change is made THEN all other error logging SHALL remain unchanged