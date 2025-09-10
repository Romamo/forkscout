# Requirements Document

## Introduction

This specification addresses the issue where GitHub API requests are encountering HTTP 301 redirects, causing excessive INFO-level logging noise. The log output shows requests like `GET https://api.github.com/repos/tiangolo/fastapi/forks` receiving 301 redirects, which should be logged at DEBUG level instead of INFO level to reduce log noise.

## Requirements

### Requirement 1: Appropriate Logging Levels

**User Story:** As a developer debugging API issues, I want appropriate logging levels for different types of HTTP responses, so that I can identify real issues without noise from expected redirects.

#### Acceptance Criteria

1. WHEN redirects are followed successfully THEN they SHALL be logged at DEBUG level, not INFO
2. WHEN API errors occur THEN they SHALL be logged at WARNING or ERROR level as appropriate
3. WHEN rate limiting occurs THEN it SHALL be logged at INFO level with clear context
4. WHEN successful API requests occur THEN they SHALL be logged at DEBUG level

### Requirement 2: Renamed Repository Handling

**User Story:** As a user analyzing repositories, I want the tool to automatically follow renamed repositories and use the correct repository name, so that I can analyze repositories even when they've been renamed.

#### Acceptance Criteria

1. WHEN a repository has been renamed (301 redirect) THEN the client SHALL follow the redirect automatically
2. WHEN following a redirect THEN the client SHALL update the repository information with the new name/owner
3. WHEN a redirect is followed THEN it SHALL be logged at DEBUG level to reduce noise
4. WHEN the final repository is found THEN analysis SHALL proceed with the correct repository details

### Requirement 3: Repository Not Found Handling

**User Story:** As a user analyzing repositories, I want the tool to stop immediately when a repository doesn't exist, so that I don't waste time on failed operations.

#### Acceptance Criteria

1. WHEN a repository is not found (404) THEN the client SHALL stop immediately with a clear error message
2. WHEN a repository has been deleted or made private THEN the client SHALL not attempt redirects or retries