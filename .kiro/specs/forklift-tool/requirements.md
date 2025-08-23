# Requirements Document

## Introduction

The Forklift tool is a GitHub repository analysis system built with Python 3.12 and managed using uv package manager that automatically discovers and evaluates valuable features across all forks of a repository. It scans forks to identify meaningful changes, ranks them by value and impact, generates comprehensive reports for maintainers, and can automatically create pull requests to propose the most valuable features back to the upstream repository. This tool aims to help open source maintainers discover and integrate valuable contributions that might otherwise be lost in the ecosystem of forks.

The tool provides both comprehensive batch analysis and step-by-step interactive analysis commands to help users understand repository ecosystems incrementally. For testing and development, the system uses small repositories like https://github.com/maliayas/github-network-ninja and https://github.com/sanila2007/youtube-bot-telegram to ensure reliable and fast testing scenarios.

## Example repositories not for testing but for production use with multiple valuable forks
https://github.com/aarigs/pandas-ta/network
https://github.com/xgboosted/pandas-ta-classic

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

**User Story:** As a repository maintainer, I want to see short explanations for each commit during analysis, so that I can quickly understand what each change does and whether it has value for the main repository.

#### Acceptance Criteria

1. WHEN I run `forklift analyze <repo-url> --explain` THEN the system SHALL provide short explanations for each commit being analyzed
2. WHEN analyzing commits with --explain THEN the system SHALL generate explanations that describe what the commit does in simple terms
3. WHEN displaying commit explanations THEN the system SHALL show the commit SHA, message, author, and generated explanation in a readable format
4. WHEN the --explain flag is not provided THEN the system SHALL run the standard analysis without detailed commit explanations
5. WHEN generating explanations THEN the system SHALL analyze commit diffs, file changes, and commit messages to understand what changed
6. WHEN analyzing commits with explanations THEN the system SHALL categorize each commit as one of: feature, bugfix, refactor, docs, test, chore, or other
7. WHEN categorizing commits THEN the system SHALL use commit message patterns, file changes, and code analysis to determine the category
8. WHEN generating explanations THEN the system SHALL keep each explanation to 1-2 sentences maximum using clear, simple language
9. WHEN using --explain with step-by-step commands THEN the system SHALL support the flag on analyze-fork and show-commits commands
10. WHEN explaining what a commit does THEN the system SHALL identify if it adds new features that could benefit all main repository users
11. WHEN explaining bug fix commits THEN the system SHALL describe what issue was fixed and if it would help main repository users
12. WHEN explaining refactoring commits THEN the system SHALL describe what code was improved and why it matters
13. WHEN explaining documentation commits THEN the system SHALL describe what documentation was added or improved
14. WHEN explaining test commits THEN the system SHALL describe what tests were added or improved
15. WHEN explaining commits with multiple changes THEN the system SHALL note that the commit does several things at once
16. WHEN generating explanations THEN the system SHALL focus on what changed rather than providing scores or complex analysis
17. WHEN describing commit value THEN the system SHALL simply state whether the change could be useful for the main repository (yes/no/unclear)
18. WHEN commits are unclear or complex THEN the system SHALL state that the commit is difficult to understand or does multiple things

### Requirement 9

**User Story:** As a repository maintainer, I want direct links to GitHub commit pages in commit explanations, so that I can quickly navigate to view the full commit details, diff, and context.

#### Acceptance Criteria

1. WHEN viewing commit explanations THEN the system SHALL include clickable GitHub commit URLs for each analyzed commit
2. WHEN displaying commit information THEN the system SHALL format GitHub links as `https://github.com/{owner}/{repo}/commit/{sha}`
3. WHEN generating reports with explanations THEN the system SHALL include GitHub commit links in markdown format
4. WHEN using CLI commands with --explain flag THEN the system SHALL display GitHub commit URLs alongside explanations
5. WHEN showing commit details THEN the system SHALL provide both short SHA and full GitHub URL for easy access
6. WHEN generating explanations THEN the system SHALL ensure all GitHub links are valid and properly formatted

### Requirement 10

**User Story:** As a repository maintainer, I want clear documentation of evaluation criteria, so that I can understand how the system determines commit categories, impact levels, and value assessments.

#### Acceptance Criteria

1. WHEN reading project documentation THEN the system SHALL provide a dedicated section explaining evaluation criteria
2. WHEN categorizing commits THEN the system SHALL document the patterns and rules used for each category type (feature, bugfix, refactor, docs, test, chore, other)
3. WHEN assessing impact levels THEN the system SHALL document the factors considered (file criticality, change magnitude, test coverage impact)
4. WHEN determining main repository value THEN the system SHALL document the criteria for "yes", "no", and "unclear" assessments
5. WHEN explaining "What Changed" descriptions THEN the system SHALL document how commit messages and file changes are analyzed
6. WHEN users question evaluation results THEN the system SHALL provide clear reasoning based on documented criteria

### Requirement 11

**User Story:** As a repository maintainer, I want to distinguish between the "What Changed" description and evaluation verdict, so that I can understand the difference between factual description and system assessment.

#### Acceptance Criteria

1. WHEN displaying commit explanations THEN the system SHALL clearly separate factual descriptions from evaluative assessments
2. WHEN showing "What Changed" information THEN the system SHALL present it as objective description of changes made
3. WHEN showing evaluation verdict THEN the system SHALL present it as system assessment with clear labeling (e.g., "Assessment:", "Value for main repo:")
4. WHEN formatting explanations THEN the system SHALL use distinct visual formatting for descriptions vs. evaluations
5. WHEN generating reports THEN the system SHALL maintain clear separation between descriptive and evaluative content
6. WHEN users review explanations THEN the system SHALL make it obvious which parts are factual vs. which are system judgments

### Requirement 12

**User Story:** As a repository maintainer, I want enhanced commit explanation display with better formatting, so that I can quickly scan and understand commit analysis results.

#### Acceptance Criteria

1. WHEN displaying commit explanations THEN the system SHALL use consistent formatting with clear visual hierarchy
2. WHEN showing multiple commits THEN the system SHALL use tables or structured layouts for easy scanning
3. WHEN displaying GitHub links THEN the system SHALL format them as clickable links in supported terminals
4. WHEN showing commit categories THEN the system SHALL use color coding or icons for quick visual identification
5. WHEN displaying impact levels THEN the system SHALL use visual indicators (high/medium/low) for quick assessment
6. WHEN formatting explanations THEN the system SHALL ensure readability across different terminal environments

### Requirement 13

**User Story:** As a repository maintainer, I want comprehensive README documentation about evaluation criteria, so that I can understand the system's decision-making process before using it.

#### Acceptance Criteria

1. WHEN reading the README THEN the system SHALL include a dedicated "Evaluation Criteria" section
2. WHEN documenting commit categories THEN the system SHALL provide examples of each category with typical patterns
3. WHEN explaining impact assessment THEN the system SHALL document file criticality rules and change magnitude calculation
4. WHEN describing value assessment THEN the system SHALL provide clear examples of "yes", "no", and "unclear" scenarios
5. WHEN documenting evaluation logic THEN the system SHALL include decision trees or flowcharts where helpful
6. WHEN users need clarification THEN the system SHALL provide troubleshooting section for common evaluation questions

### Requirement 14

**User Story:** As a repository maintainer, I want optimized pagination support for large repositories, so that I can efficiently analyze repositories with thousands of forks and commits without performance degradation.

#### Acceptance Criteria

1. WHEN analyzing repositories with many forks THEN the system SHALL use maximum per_page values (100) for all GitHub API calls to minimize request count
2. WHEN fetching large datasets THEN the system SHALL implement intelligent pagination with configurable batch sizes and concurrent processing
3. WHEN processing paginated results THEN the system SHALL provide progress indicators showing current page and estimated total pages
4. WHEN encountering rate limits during pagination THEN the system SHALL implement smart backoff strategies that account for remaining pages
5. WHEN analyzing large repositories THEN the system SHALL support resumable pagination to continue from interruption points
6. WHEN fetching commits for large branches THEN the system SHALL implement streaming pagination to avoid memory exhaustion
7. WHEN processing multiple forks concurrently THEN the system SHALL implement pagination pooling to optimize API usage across parallel requests
8. WHEN users configure analysis limits THEN the system SHALL respect max_forks, max_commits, and max_branches settings while maintaining efficient pagination
9. WHEN displaying progress for large operations THEN the system SHALL show pagination statistics including pages processed, items fetched, and estimated completion time
10. WHEN handling pagination errors THEN the system SHALL implement retry logic with exponential backoff and continue processing remaining pages

### Requirement 15

**User Story:** As a repository maintainer, I want an interactive mode for the analyze command with stops and user confirmation after each significant step, so that I can control the analysis process and review intermediate results before proceeding.

#### Acceptance Criteria

1. WHEN I run `forklift analyze <repo-url> --interactive` THEN the system SHALL execute analysis in interactive mode with user confirmation stops after each major step
2. WHEN in interactive mode THEN the system SHALL display clear step descriptions and progress indicators before requesting user confirmation
3. WHEN prompted for confirmation THEN the system SHALL provide options to continue or abort the entire analysis
4. WHEN displaying step results THEN the system SHALL show intermediate results in a formatted, easy-to-read manner with key metrics and summaries
5. WHEN I choose to continue THEN the system SHALL proceed to the next analysis step and repeat the confirmation process
6. WHEN steps complete successfully THEN the system SHALL display results and wait for user confirmation to proceed
7. WHEN I choose to abort THEN the system SHALL terminate the analysis gracefully and provide a summary of completed steps
8. WHEN interactive mode is enabled THEN the system SHALL support configuration options for confirmation timeouts and default choices
9. WHEN running in interactive mode THEN the system SHALL provide clear visual separation between different analysis phases
10. WHEN fork discovery completes THEN the system SHALL display fork counts, filtering criteria applied, and ask for confirmation to proceed with analysis
11. WHEN fork filtering completes THEN the system SHALL show the number of forks selected for detailed analysis and request confirmation
12. WHEN analysis of individual forks completes THEN the system SHALL display feature counts, categories found, and ask for confirmation to proceed with ranking
13. WHEN each step completes THEN the system SHALL display step results and metrics before requesting confirmation to proceed
14. WHEN interactive analysis is interrupted THEN the system SHALL provide options to resume from the last completed step
15. WHEN user chooses to abort THEN the system SHALL provide a summary of all completed steps and their results

### Requirement 16

**User Story:** As a repository maintainer, I want to disable caching for analysis operations, so that I can ensure fresh data retrieval and bypass potentially stale cached results when needed.

#### Acceptance Criteria

1. WHEN I run `forklift analyze <repo-url> --disable-cache` THEN the system SHALL bypass all caching mechanisms and fetch fresh data from GitHub API
2. WHEN --disable-cache flag is provided THEN the system SHALL not read from existing cache entries for repository, fork, or commit data
3. WHEN --disable-cache flag is provided THEN the system SHALL not write new data to cache during the analysis process
4. WHEN using --disable-cache THEN the system SHALL display a warning that analysis may take longer due to increased API calls
5. WHEN --disable-cache is combined with other flags THEN the system SHALL respect the cache bypass for all operations including explanations and interactive mode
6. WHEN --disable-cache is used with step-by-step commands THEN the system SHALL bypass cache for show-forks, show-commits, and analyze-fork commands
7. WHEN cache is disabled THEN the system SHALL still respect GitHub API rate limits and implement appropriate backoff strategies
8. WHEN analysis completes with --disable-cache THEN the system SHALL provide timing information showing the impact of bypassing cache
9. WHEN --disable-cache is used THEN the system SHALL log cache bypass operations for debugging and performance analysis
10. WHEN cache is disabled THEN the system SHALL ensure all data is fetched fresh while maintaining data consistency throughout the analysis

### Requirement 17

**User Story:** As a repository maintainer, I want AI-powered commit summaries using OpenAI GPT-4 mini, so that I can get clear, human-readable explanations of what each commit does and its potential impact on my repository.

#### Acceptance Criteria

1. WHEN I run `forklift show-commits <fork-url> --branch <branch-name> --ai-summary` THEN the system SHALL generate AI-powered summaries for each commit using OpenAI GPT-4 mini model
2. WHEN generating AI summaries THEN the system SHALL use a compact prompt "Summarize this commit: what changed, why, impact" without buzzwords or verbose instructions
3. WHEN creating AI summaries THEN the system SHALL include both the commit message and diff text in the analysis
4. WHEN AI summary generation is enabled THEN the system SHALL display commit SHA, GitHub URL, original commit message, and AI-generated summary
5. WHEN using --ai-summary flag THEN the system SHALL require OPENAI_API_KEY environment variable to be set
6. WHEN OpenAI API key is missing THEN the system SHALL display a clear error message and exit gracefully
7. WHEN AI summary generation fails for a commit THEN the system SHALL log the error and continue with remaining commits
8. WHEN generating AI summaries THEN the system SHALL respect OpenAI API rate limits and implement appropriate backoff strategies
9. WHEN AI summaries are requested THEN the system SHALL truncate large diffs to stay within OpenAI token limits (max 8000 characters)
10. WHEN displaying AI summaries THEN the system SHALL format output with clear visual separation between original commit data and AI analysis, keeping summaries concise and under 3 sentences
11. WHEN --ai-summary is combined with other flags THEN the system SHALL work with --disable-cache, --limit, and other existing options
12. WHEN AI summary generation is enabled THEN the system SHALL provide progress indicators showing summary generation status
13. WHEN using AI summaries THEN the system SHALL log API usage statistics for monitoring and cost tracking
14. WHEN AI summary fails due to API errors THEN the system SHALL provide helpful error messages distinguishing between authentication, rate limiting, and other API issues
15. WHEN generating summaries THEN the system SHALL use GPT-4 mini model specifically for cost efficiency while maintaining quality
16. WHEN AI summaries are generated THEN the system SHALL enforce brevity by limiting responses to essential information only, avoiding technical jargon and buzzwords
17. WHEN displaying AI summaries THEN the system SHALL show only the core summary text without structured sections or verbose formatting

### Requirement 18

**User Story:** As a repository maintainer using terminals that don't support Rich formatting, I want clean console output without formatting codes, so that I can read the tool's output clearly without seeing literal formatting characters like `[bold]` or `**text**`.

#### Acceptance Criteria

1. WHEN the system detects a terminal that doesn't support Rich formatting THEN it SHALL automatically disable Rich console formatting and use plain text output
2. WHEN using --no-color or --plain-text flag THEN the system SHALL disable all Rich formatting codes and markdown-style bold formatting throughout the application
3. WHEN Rich formatting is disabled THEN the system SHALL replace `[bold]text[/bold]` patterns with plain text equivalents
4. WHEN Rich formatting is disabled THEN the system SHALL replace `[green]`, `[red]`, `[blue]`, `[yellow]` color codes with plain text or simple prefixes like "SUCCESS:", "ERROR:", "INFO:", "WARNING:"
5. WHEN markdown-style formatting is disabled THEN the system SHALL replace `**text**` patterns with plain text in all output including reports and CLI messages
6. WHEN formatting is disabled THEN the system SHALL maintain information hierarchy using indentation, spacing, and text-based separators instead of colors and bold text
7. WHEN generating reports with formatting disabled THEN the system SHALL produce clean markdown without bold formatting that displays properly in all terminals
8. WHEN displaying tables with formatting disabled THEN the system SHALL use ASCII table borders and plain text headers
9. WHEN showing progress indicators with formatting disabled THEN the system SHALL use simple text-based progress displays
10. WHEN the system cannot detect terminal capabilities THEN it SHALL provide a configuration option to force plain text mode
11. WHEN using plain text mode THEN the system SHALL ensure all information remains accessible and readable without any formatting codes visible
12. WHEN formatting is disabled THEN the system SHALL maintain consistent spacing and alignment for readability