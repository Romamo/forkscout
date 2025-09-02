# Requirements Document

## Introduction

This specification addresses the issue where the Recent Commits column gets cut off when output is redirected to a file using `> filename.txt`. The Rich library detects non-TTY output and constrains table width, causing commit messages to be truncated or cut off entirely. The solution is to set an appropriate maximum width for the Recent Commits column when output is redirected.

## Requirements

### Requirement 1: Full Recent Commits Display in File Output

**User Story:** As a user, I want to see complete commit messages when redirecting output to a file, so that I can analyze the full commit information without truncation.

#### Acceptance Criteria

1. WHEN a user redirects forklift output to a file (`> file.txt`) THEN the Recent Commits column SHALL display up to 1000 characters per commit message
2. WHEN output is redirected THEN commit messages SHALL NOT be truncated due to table width constraints
3. WHEN viewing the redirected file THEN all commit message content SHALL be preserved and readable
4. WHEN commit messages are shorter than 1000 characters THEN they SHALL be displayed in full without padding

### Requirement 2: Terminal vs File Output Behavior

**User Story:** As a user, I want appropriate column widths for both terminal and file output, so that the display is optimized for each context.

#### Acceptance Criteria

1. WHEN output is displayed in a terminal THEN the Recent Commits column SHALL use existing width calculation logic
2. WHEN output is redirected to a file THEN the Recent Commits column SHALL use a maximum width of 1000 characters
3. WHEN switching between terminal and file output THEN the behavior SHALL adapt automatically
4. WHEN the terminal width changes THEN file output behavior SHALL remain consistent

### Requirement 3: Backward Compatibility

**User Story:** As an existing user, I want terminal display to remain unchanged, so that my existing workflows are not disrupted.

#### Acceptance Criteria

1. WHEN running commands in a terminal THEN the visual output SHALL be identical to current behavior
2. WHEN using interactive features THEN they SHALL continue to work as expected
3. WHEN table formatting occurs THEN terminal display SHALL maintain current width calculations
4. WHEN no redirection is used THEN all existing functionality SHALL work unchanged