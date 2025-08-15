# Requirements Document

## Introduction

The Forklift tool is a GitHub repository analysis system built with Python 3.12 and managed using uv package manager that automatically discovers and evaluates valuable features across all forks of a repository. It scans forks to identify meaningful changes, ranks them by value and impact, generates comprehensive reports for maintainers, and can automatically create pull requests to propose the most valuable features back to the upstream repository. This tool aims to help open source maintainers discover and integrate valuable contributions that might otherwise be lost in the ecosystem of forks.

The tool provides both comprehensive batch analysis and step-by-step interactive analysis commands to help users understand repository ecosystems incrementally. For testing and development, the system uses small repositories like https://github.com/maliayas/github-network-ninja and https://github.com/sanila2007/youtube-bot-telegram to ensure reliable and fast testing scenarios.

## Requirements

### Requirement 1

**User Story:** As a repository maintainer, I want to scan all forks of my repository, so that I can discover valuable features and improvements that contributors have made.

#### Acceptance Criteria

1. WHEN a user provides a GitHub repository URL THEN the system SHALL discover and list all public forks of that repository
2. WHEN scanning forks THEN the system SHALL identify commits that are ahead of the upstream repository
3. WHEN analyzing fork commits THEN the system SHALL exclude merge commits and focus on original contributions
4. IF a fork has no unique commits THEN the system SHALL skip it from further analysis
5. WHEN pre-filtering forks THEN the system SHALL use created_at >= pushed_at comparison to identify forks with no new commits and skip only those from expensive commit analysis, while all other forks must be fully scanned
6. WHEN optimizing fork discovery THEN the system SHALL apply lightweight filtering before expensive API calls to minimize unnecessary GitHub API requests and improve performance by 60-80% for typical repositories
7. WHEN the --scan-all option is provided THEN the system SHALL bypass all filtering and analyze every fork regardless of commits ahead status
8. WHEN accessing GitHub data THEN the system SHALL handle API rate limits gracefully with appropriate backoff strategies

### Requirement 2

**User Story:** As a repository maintainer, I want the tool to rank discovered features by value and impact, so that I can prioritize which contributions to review first.

#### Acceptance Criteria

1. WHEN analyzing fork changes THEN the system SHALL calculate a value score based on multiple factors including code quality, test coverage, documentation, and community engagement
2. WHEN ranking features THEN the system SHALL consider the number of stars, forks, and activity on the contributing fork
3. WHEN evaluating commits THEN the system SHALL analyze commit messages, code changes, and file modifications to determine feature significance
4. WHEN multiple forks implement similar features THEN the system SHALL identify and group related implementations
5. WHEN scoring features THEN the system SHALL provide a numerical ranking from 1-100 with clear scoring criteria

### Requirement 3

**User Story:** As a repository maintainer, I want to receive a human-readable report of valuable features, so that I can quickly understand what improvements are available across forks.

#### Acceptance Criteria

1. WHEN analysis is complete THEN the system SHALL generate a comprehensive report in markdown format
2. WHEN creating the report THEN the system SHALL include feature summaries, code snippets, and links to the original fork implementations
3. WHEN presenting features THEN the system SHALL organize them by category (bug fixes, new features, performance improvements, documentation)
4. WHEN showing rankings THEN the system SHALL display the top 20 most valuable features with detailed explanations of their scores
5. WHEN generating reports THEN the system SHALL include metadata about each fork including author, last activity, and fork statistics

### Requirement 4

**User Story:** As a repository maintainer, I want the tool to automatically create pull requests for the most valuable features, so that I can efficiently integrate improvements without manual setup.

#### Acceptance Criteria

1. WHEN configured for automatic PR creation THEN the system SHALL create pull requests for features scoring above a specified threshold
2. WHEN creating pull requests THEN the system SHALL include detailed descriptions explaining the feature value and origin
3. WHEN submitting PRs THEN the system SHALL properly attribute the original author and link to the source fork
4. WHEN creating pull requests THEN the system SHALL handle merge conflicts by creating draft PRs with conflict notifications
5. IF the upstream repository has specific contribution guidelines THEN the system SHALL format PRs according to those requirements

### Requirement 5

**User Story:** As a repository maintainer, I want to configure the tool's behavior and thresholds, so that I can customize the analysis to match my project's needs.

#### Acceptance Criteria

1. WHEN using the tool THEN the system SHALL support configuration files to specify analysis parameters
2. WHEN configuring THEN the system SHALL allow setting minimum score thresholds for automatic PR creation
3. WHEN customizing analysis THEN the system SHALL support excluding specific file types or directories from consideration
4. WHEN setting up THEN the system SHALL allow specifying GitHub authentication tokens and repository access permissions
5. WHEN running analysis THEN the system SHALL support both one-time scans and scheduled recurring analysis

### Requirement 6

**User Story:** As a repository maintainer, I want to analyze repositories using smaller, focused steps, so that I can understand the fork ecosystem incrementally and make informed decisions at each stage.

#### Acceptance Criteria

1. WHEN I run `forklift show-repo <url>` THEN the system SHALL display detailed repository information including name, description, stars, forks count, last activity, primary language, and license
2. WHEN I run `forklift list-forks <url>` THEN the system SHALL display a lightweight preview of all forks using minimal API calls showing fork name, owner, stars, last push date, and commits ahead status (None/Unknown) without detailed commit analysis
3. WHEN I run `forklift show-forks <url>` THEN the system SHALL display a detailed summary table of all forks showing fork name, owner, stars, last activity, commits ahead/behind, and activity status
4. WHEN I run `forklift show-promising <url>` THEN the system SHALL display a filtered list of significant forks based on configurable criteria like minimum stars, recent activity, and commits ahead
5. WHEN I run `forklift show-fork-details <fork-url>` THEN the system SHALL show detailed fork information including all branches, commit counts per branch, and branch activity timestamps
6. WHEN I run `forklift analyze-fork <fork-url> --branch <branch-name>` THEN the system SHALL analyze the specific fork/branch combination and show feature analysis
7. WHEN I run `forklift show-commits <fork-url> --branch <branch-name>` THEN the system SHALL display all commits in that branch with SHA, message, author, date, and file change summary
8. WHEN using any step-by-step command THEN the system SHALL provide clear output formatting with tables, colors, and progress indicators for better readability
9. WHEN commands encounter errors THEN the system SHALL provide helpful error messages and suggest next steps or alternative commands

### Requirement 7

**User Story:** As a repository maintainer, I want the tool to handle errors gracefully and provide clear feedback, so that I can troubleshoot issues and understand the analysis process.

#### Acceptance Criteria

1. WHEN encountering API errors THEN the system SHALL log detailed error messages and continue processing other forks
2. WHEN network issues occur THEN the system SHALL implement retry logic with exponential backoff
3. WHEN analysis fails for a specific fork THEN the system SHALL record the failure reason and continue with remaining forks
4. WHEN running THEN the system SHALL provide progress indicators showing current analysis status
5. WHEN complete THEN the system SHALL generate a summary report including any errors or warnings encountered during analysis

### Requirement 8

**User Story:** As a repository maintainer, I want to see detailed explanations for each commit during analysis, so that I can understand the purpose and value of individual changes without manually reviewing code.

#### Acceptance Criteria

1. WHEN I run `forklift analyze <repo-url> --explain` THEN the system SHALL provide detailed explanations for each commit being analyzed
2. WHEN analyzing commits with --explain THEN the system SHALL generate explanations that include the commit's purpose, type of change, and potential impact
3. WHEN displaying commit explanations THEN the system SHALL show the commit SHA, message, author, and generated explanation in a readable format
4. WHEN the --explain flag is not provided THEN the system SHALL run the standard analysis without detailed commit explanations
5. WHEN generating explanations THEN the system SHALL analyze commit diffs, file changes, and commit messages to create meaningful descriptions
6. WHEN analyzing commits with explanations THEN the system SHALL categorize each commit as one of: feature, bugfix, refactor, docs, test, chore, or other
7. WHEN categorizing commits THEN the system SHALL use commit message patterns, file changes, and code analysis to determine the category
8. WHEN generating commit explanations THEN the system SHALL assess and describe the potential impact of each commit (low, medium, high)
9. WHEN generating explanations THEN the system SHALL keep each explanation to 2-3 sentences maximum using clear, non-technical language
10. WHEN using --explain with step-by-step commands THEN the system SHALL support the flag on analyze-fork and show-commits commands