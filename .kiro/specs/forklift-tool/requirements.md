# Requirements Document

## Introduction

The Forklift tool is a GitHub repository analysis system built with Python 3.12 and managed using uv package manager that automatically discovers and evaluates valuable features across all forks of a repository. It scans forks to identify meaningful changes, ranks them by value and impact, generates comprehensive reports for maintainers, and can automatically create pull requests to propose the most valuable features back to the upstream repository. This tool aims to help open source maintainers discover and integrate valuable contributions that might otherwise be lost in the ecosystem of forks.

The tool provides both comprehensive batch analysis and step-by-step interactive analysis commands to help users understand repository ecosystems incrementally. For testing and development, the system uses small repositories like https://github.com/maliayas/github-network-ninja and https://github.com/sanila2007/youtube-bot-telegram to ensure reliable and fast testing scenarios.

## Example repositories not for testing but for production use with multiple valuable forks
https://github.com/aarigs/pandas-ta
https://github.com/xgboosted/pandas-ta-classic 18 forks
https://github.com/NoMore201/googleplay-api
https://github.com/virattt/ai-hedge-fund (Find forks replaced paid data sources with free ones)
https://github.com/newmarcel/KeepingYouAwake 232 forks
https://github.com/sanila2007/youtube-bot-telegram 19 forks
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

**User Story:** As a repository maintainer, I want clean, simple console output that works reliably across all terminal environments, so that I can read the tool's output clearly without formatting issues or special character problems.

#### Acceptance Criteria

1. WHEN running any forklift command THEN the system SHALL use simple, compatible formatting by default that works in all terminal environments
1.1. WHEN displaying commit explanations THEN the system SHALL NOT use emoji characters (📝, ❓, 🟢, ❔) or Unicode box drawing characters that may display as literal text
2. WHEN displaying output THEN the system SHALL avoid complex Rich formatting, emojis, and special Unicode characters that may not render properly
3. WHEN showing tables THEN the system SHALL use simple ASCII characters (|, -, +) instead of Unicode box drawing characters
4. WHEN indicating status or categories THEN the system SHALL use text labels (SUCCESS, ERROR, INFO, WARNING) instead of colored icons or emojis
5. WHEN using --no-color or --plain-text flag THEN the system SHALL disable all color codes and use only plain text output
6. WHEN the system detects limited terminal capabilities THEN it SHALL automatically fall back to plain text mode
7. WHEN displaying commit explanations THEN the system SHALL use simple text formatting without emojis, special symbols, or complex Rich markup
8. WHEN showing progress indicators THEN the system SHALL use simple text-based progress displays (e.g., "Processing 5/10...")
9. WHEN generating reports THEN the system SHALL produce clean markdown without bold formatting or special characters
10. WHEN formatting is minimal THEN the system SHALL maintain information hierarchy using indentation, spacing, and clear text separators
11. WHEN using simple formatting THEN the system SHALL ensure all information remains accessible and readable in any terminal
12. WHEN displaying data THEN the system SHALL prioritize readability and compatibility over visual aesthetics

### Requirement 19

**User Story:** As a repository maintainer, I want a detailed view option for the show-commits command that displays comprehensive commit information including GitHub URLs, AI summaries, messages, and diffs, so that I can thoroughly analyze individual commits without navigating to multiple sources.

#### Acceptance Criteria

1. WHEN I run `forklift show-commits <fork-url> --detail` THEN the system SHALL display comprehensive commit information for each commit including full GitHub URL, AI summary, commit message, and diff content
2. WHEN using --detail flag THEN the system SHALL generate clickable GitHub commit URLs in the format `https://github.com/{owner}/{repo}/commit/{sha}`
3. WHEN --detail is specified THEN the system SHALL automatically generate AI-powered summaries for each commit using OpenAI GPT-4 mini model
4. WHEN displaying detailed commit information THEN the system SHALL show the original commit message with proper formatting and line breaks
5. WHEN --detail flag is used THEN the system SHALL fetch and display the complete diff content for each commit showing file changes, additions, and deletions
6. WHEN generating detailed output THEN the system SHALL format the information with clear visual separation between GitHub URL, AI summary, commit message, and diff sections
7. WHEN --detail is combined with other flags THEN the system SHALL respect existing options like --limit, --branch, --since, --until, and --author filters
8. WHEN using --detail flag THEN the system SHALL require OPENAI_API_KEY environment variable to be set for AI summary generation
9. WHEN AI summary generation fails in detail mode THEN the system SHALL display the commit without AI summary and continue processing remaining commits
10. WHEN displaying diffs in detail mode THEN the system SHALL truncate extremely large diffs to prevent terminal overflow while maintaining readability
11. WHEN --detail flag is used THEN the system SHALL provide progress indicators showing detailed processing status for each commit
12. WHEN using detail mode THEN the system SHALL respect rate limiting for both GitHub API calls and OpenAI API calls with appropriate backoff strategies

### Requirement 20

**User Story:** As a repository maintainer, I want comprehensive fork data collection using GitHub API paginated forks list to see all available fork information with minimal API requests, so that I can make informed decisions about which forks to analyze in detail.

### Requirement 21

**User Story:** As a repository maintainer, I want optimized show-forks --show-commits functionality that skips downloading commits for forks with no commits ahead, so that I can get faster results and use fewer API calls when viewing fork commit information.

#### Acceptance Criteria

1. WHEN discovering forks THEN the system SHALL use only the paginated forks list endpoint (`/repos/{owner}/{repo}/forks?per_page=100&page=N`) to collect all available fork data without making individual repository API calls
2. WHEN processing forks list pages THEN the system SHALL extract all available metrics from each fork object including stargazers_count, forks_count, size, language, created_at, updated_at, pushed_at, open_issues_count, archived, disabled, and topics
3. WHEN using --show-commits flag THEN the system SHALL skip commit fetching for forks identified as having no commits ahead using created_at >= pushed_at comparison
4. WHEN commits ahead status cannot be determined THEN the system SHALL err on the side of inclusion and fetch commits for analysis
5. WHEN displaying fork information THEN the system SHALL show "No commits ahead" for filtered forks and actual commit counts for analyzed forks
6. WHEN --force flag is provided THEN the system SHALL bypass commit filtering and fetch commits for all forks regardless of status
7. WHEN filtering saves API calls THEN the system SHALL log the number of API calls saved and performance improvement achieved
8. WHEN using optimized show-forks THEN the system SHALL maintain the same output format and information quality as non-optimized mode

### Requirement 22

**User Story:** As a repository maintainer, I want automatic interactive mode detection that disables progress bars when output is redirected, so that I get clean text output for scripting and automation without needing manual flags.

#### Acceptance Criteria

1. WHEN running any forklift command THEN the system SHALL automatically detect if output is being redirected or piped
2. WHEN stdout is redirected (e.g., `forklift analyze repo > output.txt`) THEN the system SHALL automatically disable progress bars and rich formatting
3. WHEN running in a non-TTY environment THEN the system SHALL use plain text output without progress indicators
4. WHEN running in CI/automation environments THEN the system SHALL detect common CI environment variables and disable interactive features
5. WHEN stdin and stdout are both connected to a terminal THEN the system SHALL enable full interactive mode with progress bars and rich formatting
6. WHEN only stdout is redirected but stderr is still a TTY THEN the system SHALL send progress information to stderr while keeping data output clean on stdout
7. WHEN interactive mode is disabled THEN the system SHALL use simple text status messages instead of progress bars
8. WHEN interactive mode is disabled THEN the system SHALL automatically proceed with default options instead of prompting for user input
9. WHEN the system detects interactive mode THEN it SHALL log the detection result for debugging purposes
10. WHEN running commands in different environments THEN the system SHALL maintain consistent functionality regardless of interactive mode statusn_issues_count, archived, disabled, fork, topics
3. WHEN using --show-commits flag THEN the system SHALL optimize by skipping commit downloads for forks with no commits ahead (created_at >= pushed_at)
4. WHEN --force-all-commits flag is provided THEN the system SHALL bypass optimization and download commits for all forks regardless of commits ahead status
5. WHEN displaying forks with --show-commits THEN the system SHALL show recent commits in a dedicated column with commit date, hash, and message
6. WHEN commits cannot be fetched THEN the system SHALL display appropriate fallback message in the Recent Commits column
7. WHEN using --show-commits THEN the system SHALL limit displayed commits to specified number (default 0, max 10 for readability)
8. WHEN processing large numbers of forks THEN the system SHALL provide progress indicators for commit fetching operations
9. WHEN --show-commits is combined with --detail THEN the system SHALL show both exact commit counts and recent commit messages
10. WHEN optimization is applied THEN the system SHALL log statistics about API calls saved by skipping forks with no commits ahead

### Requirement 22

**User Story:** As a repository maintainer, I want an --ahead-only flag for the show-forks command that displays only forks with commits ahead and excludes private forks, so that I can focus on forks that contain potential contributions without being distracted by inactive or inaccessible forks.

#### Acceptance Criteria

1. WHEN I run `forklift show-forks <repo-url> --ahead-only` THEN the system SHALL display only forks that have commits ahead of the upstream repository
2. WHEN using --ahead-only flag THEN the system SHALL automatically exclude all private forks from the results regardless of their commit status
3. WHEN filtering with --ahead-only THEN the system SHALL use the created_at < pushed_at comparison to identify forks with commits ahead
4. WHEN --ahead-only is specified THEN the system SHALL display a summary showing total forks found vs forks displayed after filtering
5. WHEN --ahead-only is combined with other flags THEN the system SHALL apply ahead-only filtering first, then apply other display options (--detail, --show-commits, --max-forks)
6. WHEN no forks have commits ahead THEN the system SHALL display a clear message indicating no qualifying forks were found
7. WHEN --ahead-only filtering is applied THEN the system SHALL show filtering statistics including number of private forks excluded and forks with no commits excluded
8. WHEN using --ahead-only with --detail THEN the system SHALL fetch exact commit counts only for the filtered ahead-only forks
9. WHEN --ahead-only is used with --show-commits THEN the system SHALL display recent commits only for forks that have commits ahead
10. WHEN --ahead-only filtering results in a small number of forks THEN the system SHALL display all qualifying forks without additional pagination limits

### Requirement 21

**User Story:** As a repository maintainer, I want a more intuitive CLI argument name for limiting the number of forks, so that the interface is clearer and more consistent with standard command-line conventions.

#### Acceptance Criteria

1. WHEN using CLI commands that limit fork processing THEN the system SHALL accept `--limit` as the argument name instead of `--max-forks`
2. WHEN `--limit` is provided THEN the system SHALL apply the same functionality as the current `--max-forks` argument
3. WHEN using the analyze command THEN the system SHALL accept `--limit` to specify maximum number of forks to analyze
4. WHEN using the show-forks command THEN the system SHALL accept `--limit` to specify maximum number of forks to display
5. WHEN using the show-promising command THEN the system SHALL accept `--limit` to specify maximum number of promising forks to show
6. WHEN using configuration commands THEN the system SHALL accept `--limit` for setting default fork limits
7. WHEN `--limit` is used THEN the system SHALL maintain the same validation rules (1-1000 range) as the current `--max-forks` argument
8. WHEN help documentation is displayed THEN the system SHALL show `--limit` as the argument name with clear description
9. WHEN error messages reference the argument THEN the system SHALL use `--limit` in all user-facing messages
10. WHEN the CLI is updated THEN the system SHALL completely replace `--max-forks` with `--limit` without backward compatibility last push, and activity ratios for comprehensive fork assessment

### Requirement 21

**User Story:** As a repository maintainer, I want simple and effective HTTP caching using Hishel to replace the complex custom cache system, so that I can benefit from faster subsequent runs with minimal code complexity and maintenance burden.

**Note:** This requirement replaces the over-engineered custom SQLite cache system (tasks 9.1-9.2) with Hishel's HTTP-level caching. The existing custom cache system provides little value compared to using a battle-tested HTTP caching library that handles caching automatically at the transport level.

### Requirement 23

**User Story:** As a repository maintainer, I want to specify any reasonable commit count for the --show-commits flag without artificial limitations, so that I can view the full commit history when analyzing forks with extensive changes.

#### Acceptance Criteria

1. WHEN I run `forklift show-forks <repo-url> --show-commits=N` THEN the system SHALL accept any positive integer value for N without artificial upper limits
2. WHEN --show-commits value is very large (>1000) THEN the system SHALL inform the user about potential performance impact but still proceed
3. WHEN fetching commits THEN the system SHALL use GitHub Compare API pagination to retrieve all requested commits regardless of count, using multiple paginated requests when needed
4. WHEN GitHub Compare API returns 250 commits but more are requested THEN the system SHALL automatically use pagination to fetch additional pages until the requested count is reached
5. WHEN GitHub API limits are reached THEN the system SHALL implement proper rate limiting and backoff strategies to continue fetching
6. WHEN commit fetching encounters API errors THEN the system SHALL retry with exponential backoff and continue with partial results if necessary
7. WHEN displaying large numbers of commits THEN the system SHALL use dynamic column width calculations and consider output formatting for readability
8. WHEN processing many commits per fork THEN the system SHALL provide progress indicators showing current pagination progress and estimated completion
9. WHEN --show-commits is set to large values THEN the system SHALL respect only GitHub API rate limits, not arbitrary application limits
10. WHEN memory usage becomes high due to large commit counts THEN the system SHALL use streaming or batched processing to manage memory efficiently
11. WHEN validation fails for --show-commits THEN the system SHALL only reject negative values or zero, accepting all positive integers

#### Acceptance Criteria

1. WHEN implementing caching THEN the system SHALL use Hishel HTTP caching instead of the custom SQLite cache system
2. WHEN making any GitHub API call THEN Hishel SHALL automatically cache HTTP responses at the transport level
3. WHEN cache data exists and is not expired THEN Hishel SHALL return cached responses without making new HTTP requests
4. WHEN using the --disable-cache flag THEN the system SHALL configure Hishel to bypass cache for all HTTP requests in that session
5. WHEN caching HTTP responses THEN Hishel SHALL use appropriate TTL values (default: 30 minutes for GitHub API responses)
6. WHEN running show-forks command THEN the system SHALL benefit from automatic HTTP caching for instant results on repeated calls
7. WHEN running subsequent analyses THEN the system SHALL leverage cached HTTP responses to significantly reduce API calls and execution time
8. WHEN replacing the custom cache system THEN the system SHALL remove all custom cache management code (CacheManager, CacheWarmingConfig, etc.)
9. WHEN HTTP cache operations fail THEN Hishel SHALL gracefully fall back to direct HTTP requests without failing the operation
10. WHEN the system starts THEN Hishel SHALL automatically initialize HTTP cache storage with minimal configuration
11. WHEN the system shuts down THEN Hishel SHALL handle cache cleanup automatically without custom management code
12. WHEN migrating from custom cache THEN the system SHALL maintain the same user-facing cache functionality with much simpler implementation last push, and activity ratios
5. WHEN identifying forks with no commits ahead THEN the system SHALL use created_at >= pushed_at comparison to detect forks that have never been modified after creation
6. WHEN displaying fork qualification data THEN the system SHALL present comprehensive metrics in organized tables with clear column headers and proper data formatting
7. WHEN processing large numbers of forks THEN the system SHALL handle pagination efficiently and provide progress indicators for data collection operations
8. WHEN fork data collection encounters errors THEN the system SHALL log issues and continue processing remaining forks without failing the entire operation
9. WHEN users need to understand fork characteristics THEN the system SHALL provide summary statistics including total forks, active forks, archived forks, and forks by primary language
10. WHEN collecting fork data THEN the system SHALL respect GitHub API rate limits and implement appropriate backoff strategies during paginated requests

### Requirement 21

**User Story:** As a repository maintainer, I want to automatically ignore forks with no commits ahead when using the --detail flag, so that I can focus detailed analysis only on forks that have actual changes without wasting time on unchanged forks.

#### Acceptance Criteria

1. WHEN I run `forklift show-commits <fork-url> --detail` THEN the system SHALL check if the fork has no commits ahead using already downloaded fork qualification data
2. WHEN using --detail flag on a fork with no commits ahead THEN the system SHALL display a clear message stating "Fork has no commits ahead of upstream - skipping detailed analysis" and exit gracefully
3. WHEN determining if a fork has commits ahead THEN the system SHALL use the created_at >= pushed_at comparison from previously collected fork data without making additional API calls
4. WHEN --detail flag is used on forks with commits ahead THEN the system SHALL proceed with normal detailed analysis including AI summaries, commit messages, and diffs
5. WHEN fork qualification data is not available THEN the system SHALL fall back to making a GitHub API call to determine commits ahead status before proceeding
6. WHEN --detail flag is combined with other filtering options THEN the system SHALL apply the no-commits-ahead check first before applying other filters like --limit, --since, --until
7. WHEN using --detail on multiple forks in batch operations THEN the system SHALL skip forks with no commits ahead and continue processing forks that have changes
8. WHEN a fork is skipped due to no commits ahead THEN the system SHALL log the decision with fork name and reason for transparency
9. WHEN --detail flag encounters forks with ambiguous commit status THEN the system SHALL err on the side of inclusion and proceed with detailed analysis
10. WHEN users want to override the no-commits-ahead filtering THEN the system SHALL provide a --force flag to analyze all forks regardless of commit statusn

### Requirement 21

**User Story:** As a repository maintainer, I want improved show-forks display with better sorting and simplified columns, so that I can quickly identify the most relevant forks for analysis.

#### Acceptance Criteria

1. WHEN displaying the Detailed Fork Information table THEN the system SHALL sort by commits status (has commits first), then forks count descending, then stars descending, then last push date descending
2. WHEN showing fork information THEN the system SHALL remove the "#", "Size (KB)", and "Language" columns from the Detailed Fork Information table
3. WHEN showing fork information THEN the system SHALL add a "URL" column containing the clickable GitHub URL for each fork repository
4. WHEN displaying commits status THEN the system SHALL change the "Commits Status" header to "Commits Ahead" and show "Yes" for forks with commits ahead and "No" for forks without commits ahead
5. WHEN generating fork reports THEN the system SHALL remove the "Language Distribution" table entirely
6. WHEN displaying fork analysis results THEN the system SHALL remove the "Fork Insights" section as it duplicates information from the Collection Summary to detect forks that have never had new commits
4.2. WHEN a fork has created_at >= pushed_at THEN the system SHALL mark it as "No commits ahead" and exclude it from expensive commit analysis
4.3. WHEN a fork has pushed_at > created_at THEN the system SHALL mark it as "Has commits" and include it for potential detailed analysis
5. WHEN displaying fork information THEN the system SHALL show all collected metrics in a clear, sortable format including community engagement indicators (stars, forks, watchers), development indicators (topics, issues, language), and activity patterns
6. WHEN presenting fork data THEN the system SHALL provide basic filtering options to exclude archived=true and disabled=true forks but not apply quality scoring
7. WHEN users review fork data THEN the system SHALL display comprehensive information allowing users to identify valuable forks based on their own criteria and priorities
8. WHEN displaying fork lists THEN the system SHALL show all key metrics (stars, forks, size, language, last activity, topics count, issues count) derived entirely from the forks list data
9. WHEN users want to see all forks THEN the system SHALL display complete fork data including archived and disabled forks with clear status indicators
10. WHEN fork data collection is complete THEN the system SHALL let users choose which forks to analyze in detail based on the comprehensive information provided, automatically excluding forks with no commits ahead
11. WHEN users make fork selections THEN the system SHALL proceed with expensive commit analysis only for user-selected forks that have commits ahead, dramatically reducing API usage
12. WHEN fork data collection is complete THEN the system SHALL provide summary statistics showing total forks discovered, forks with no commits ahead (excluded), forks available for analysis, and percentage of API calls saved by filtering and user selection

### Requirement 22

**User Story:** As a repository maintainer, I want the --disable-cache flag to work correctly with the analyze command, so that I can bypass cached data and get fresh results from GitHub API when needed.

#### Acceptance Criteria

1. WHEN I run `forklift analyze <repo-url> --disable-cache` THEN the system SHALL successfully execute without throwing "unexpected keyword argument 'disable_cache'" errors
2. WHEN --disable-cache flag is provided THEN the GitHubClient methods SHALL accept and properly handle the disable_cache parameter
3. WHEN disable_cache=True is passed to GitHub API methods THEN the system SHALL bypass cache read operations and fetch fresh data from GitHub API
4. WHEN disable_cache=True is passed to GitHub API methods THEN the system SHALL bypass cache write operations and not store fetched data in cache
5. WHEN using --disable-cache THEN all GitHub API methods (get_repository, get_forks, get_commits_ahead, get_user, etc.) SHALL support the disable_cache parameter
6. WHEN cache is disabled THEN the system SHALL log cache bypass operations for debugging and show performance impact
7. WHEN --disable-cache is used THEN the system SHALL still respect GitHub API rate limits and implement appropriate backoff strategies
8. WHEN cache bypass is active THEN the system SHALL provide timing information showing the impact of fetching fresh data
9. WHEN --disable-cache flag is used THEN the system SHALL work correctly with all analysis modes including interactive mode and explanation generation
10. WHEN cache disabling is implemented THEN all existing functionality SHALL continue to work normally when cache is enabled (default behavior)

### Requirement 21

**User Story:** As a repository maintainer, I want enhanced show-forks command with detailed commit information, so that I can see precise commit counts ahead for each fork and have a cleaner table layout focused on the most important metrics.

#### Acceptance Criteria

1. WHEN I run `forklift show-forks <repo-url> --detail` THEN the system SHALL make additional API requests to fetch exact commits ahead count for each fork
2. WHEN using --detail flag THEN the system SHALL display a "Detailed Fork Information" table with URL as the first column, followed by Stars, Forks, Commits Ahead, and Last Push columns only
3. WHEN --detail flag is provided THEN the system SHALL remove Fork Name, Owner, Activity, and Status columns from the table to focus on essential metrics
4. WHEN fetching detailed commit information THEN the system SHALL use GitHub's compare API endpoint to get accurate commits ahead count between fork and upstream repository
5. WHEN --detail flag is used THEN the system SHALL display exact numeric commit counts (e.g., "5 commits ahead") instead of status indicators like "Has commits" or "Unknown"
6. WHEN making additional API requests for --detail THEN the system SHALL respect GitHub API rate limits and implement appropriate backoff strategies
7. WHEN --detail flag is combined with other options THEN the system SHALL work with existing flags like --max-forks, --exclude-archived, and sorting options
8. WHEN detailed commit information cannot be fetched THEN the system SHALL display "Unknown" for that fork's commits ahead count and continue processing other forks
9. WHEN using --detail flag THEN the system SHALL provide progress indicators showing the additional API requests being made for commit comparison
10. WHEN --detail is not provided THEN the system SHALL use the existing behavior with the current table structure and no additional API requests
11. WHEN displaying the detailed table THEN the system SHALL maintain clear formatting and readability with the reduced column set
12. WHEN --detail flag is used THEN the system SHALL log the additional API calls made and their impact on rate limiting for monitoring purposes
13. WHEN using --detail flag THEN the system SHALL skip compare API calls for forks already identified as having no commits ahead using created_at >= pushed_at logic to minimize unnecessary API requests
14. WHEN skipping forks with no commits ahead THEN the system SHALL set their exact commits ahead count to 0 without making compare API calls
15. WHEN optimizing API usage THEN the system SHALL log the number of API calls saved by skipping forks with no commits ahead

### Requirement 22

**User Story:** As a repository maintainer, I want the fork display table to show commits ahead and behind in a single compact column, so that I can quickly see the complete commit status of each fork in a more space-efficient format.

#### Acceptance Criteria

1. WHEN displaying fork information THEN the system SHALL combine "Commits Ahead" and "Commits Behind" columns into a single "Commits" column
2. WHEN showing commit status THEN the system SHALL use the format "+X -Y" where X is commits ahead and Y is commits behind (e.g., "+3 -1" means 3 ahead, 1 behind)
3. WHEN a fork has no commits ahead THEN the system SHALL display "-Y" format (e.g., "-5" means 5 behind)
4. WHEN a fork has no commits behind THEN the system SHALL display "+X" format (e.g., "+2" means 2 ahead)
5. WHEN a fork is completely up-to-date THEN the system SHALL display an empty cell for the cleanest visual appearance
6. WHEN a fork has unknown commit status THEN the system SHALL display "Unknown" in the Commits column
7. WHEN formatting the Commits column THEN the system SHALL use appropriate colors (green for ahead, red for behind) to make the status visually clear
8. WHEN displaying the table THEN the system SHALL adjust column widths to accommodate the new compact format while maintaining readability
9. WHEN sorting by commits THEN the system SHALL sort primarily by commits ahead, then by commits behind as secondary criteria
10. WHEN the compact format is implemented THEN the system SHALL maintain backward compatibility with existing fork analysis functionality
11. WHEN displaying commit information THEN the system SHALL ensure the "+X -Y" format is consistent across all fork display commands (show-forks, list-forks, etc.)
12. WHEN the new format is used THEN the system SHALL update any related documentation and help text to reflect the combined commit status display

### Requirement 23

**User Story:** As a repository maintainer, I want to see recent commit information directly in the show-forks table, so that I can quickly understand what changes have been made in each fork without navigating to individual repositories.

#### Acceptance Criteria

1. WHEN I run `forklift show-forks <repo-url> --show-commits=N` THEN the system SHALL add a "Recent Commits" column showing the last N commits for each fork
2. WHEN --show-commits is specified THEN the system SHALL display each commit as "short_sha: commit_message" format (e.g., "a1b2c3d: Add user authentication")
3. WHEN showing multiple commits THEN the system SHALL display each commit on a separate line within the cell for better readability
4. WHEN --show-commits=0 or not specified THEN the system SHALL not show the Recent Commits column (default behavior)
5. WHEN fetching commit information THEN the system SHALL get commits from the fork's default branch
6. WHEN a fork has fewer commits than requested THEN the system SHALL show all available commits without error
7. WHEN commit messages are very long THEN the system SHALL truncate them to a reasonable length (e.g., 50 characters) with "..." indicator
8. WHEN commit information cannot be fetched THEN the system SHALL display "Unable to fetch commits" in that fork's Recent Commits cell
9. WHEN using --show-commits THEN the system SHALL respect GitHub API rate limits and implement appropriate backoff strategies
10. WHEN --show-commits is combined with other flags THEN the system SHALL work with existing options like --max-forks, --exclude-archived, and sorting
11. WHEN displaying recent commits THEN the system SHALL adjust table layout to accommodate the new column while maintaining readability
12. WHEN --show-commits is used THEN the system SHALL provide progress indicators showing commit fetching status for each fork
13. WHEN using --show-commits THEN the system SHALL skip downloading commits for forks that have no commits ahead of upstream to optimize performance and reduce unnecessary API calls

### Requirement 24

**User Story:** As a repository maintainer, I want optimized show-forks --show-commits functionality that intelligently skips downloading commits for forks with no commits ahead, so that I can get faster results and use fewer API calls when viewing fork commit information.

#### Acceptance Criteria

1. WHEN using `forklift show-forks <repo-url> --show-commits=N` THEN the system SHALL check each fork's commits ahead status before attempting to download commit information
2. WHEN a fork has no commits ahead (created_at >= pushed_at) THEN the system SHALL skip downloading commits for that fork and display "No commits ahead" in the Recent Commits column
3. WHEN a fork has commits ahead (pushed_at > created_at) THEN the system SHALL proceed with downloading the requested number of recent commits
4. WHEN fork commit status is determined from already collected fork data THEN the system SHALL not make additional API calls to check commits ahead status
5. WHEN fork commit status cannot be determined from existing data THEN the system SHALL make a minimal API call to check status before deciding whether to download commits
6. WHEN skipping commit downloads THEN the system SHALL log the number of API calls saved and forks skipped for performance transparency
7. WHEN --show-commits optimization is active THEN the system SHALL provide progress indicators showing which forks are being skipped vs processed
8. WHEN optimization reduces API calls THEN the system SHALL display summary statistics showing API calls saved and performance improvement
9. WHEN using --show-commits with --detail flag THEN the system SHALL apply the same optimization logic to avoid redundant commit downloads
10. WHEN users want to force commit downloads for all forks THEN the system SHALL provide a --force-all-commits flag to bypass the optimization
11. WHEN the optimization encounters errors determining commit status THEN the system SHALL err on the side of inclusion and download commits rather than skip potentially valuable information
12. WHEN --show-commits optimization is complete THEN the system SHALL maintain the same table format and user experience while significantly reducing API usage for repositories with many unchanged forks

### Requirement 22

**User Story:** As a repository maintainer, I want improved GitHub API rate limiting that properly handles long wait times and provides better user feedback, so that I can reliably analyze repositories without operations failing due to rate limit handling issues.

#### Acceptance Criteria

1. WHEN the system encounters 403 Forbidden responses from GitHub API THEN it SHALL log all response headers to help diagnose whether rate limit headers are present
2. WHEN GitHub API returns rate limit headers (x-ratelimit-remaining, x-ratelimit-reset, x-ratelimit-limit) THEN the system SHALL log these values for debugging
3. WHEN rate limit reset time is missing or zero THEN the system SHALL implement intelligent fallback with longer delays instead of short exponential backoff
4. WHEN rate limit reset time is available and longer than max_delay (60 seconds) THEN the system SHALL wait for the full reset time instead of falling back to exponential backoff
5. WHEN waiting for rate limit reset THEN the system SHALL display user-friendly progress messages with countdown timers showing remaining wait time
6. WHEN rate limit wait times are long (>60 seconds) THEN the system SHALL provide periodic progress updates every 30 seconds to show the operation is still active
7. WHEN rate limiting occurs without proper headers THEN the system SHALL implement progressive backoff with longer delays (5min, 15min, 30min) instead of giving up
8. WHEN rate limit errors occur THEN the system SHALL distinguish between temporary rate limits and permanent authentication/authorization failures
9. WHEN multiple rate limit retries are needed THEN the system SHALL continue retrying until successful rather than giving up after max_retries when dealing with rate limits
10. WHEN users encounter rate limiting THEN the system SHALL provide helpful messages explaining the situation and expected resolution time

### Requirement 22

**User Story:** As a repository maintainer, I want enhanced show-forks command functionality with improved table formatting and commit information, so that I can get better insights into fork activity and recent changes.

#### Acceptance Criteria

1. WHEN I run `forklift show-forks <repo-url>` THEN the system SHALL display the "All Forks" table using the same detailed formatting as the --detail flag for consistency
2. WHEN using --show-commits flag THEN the system SHALL download and display only commits that are ahead of the upstream repository, not all commits
3. WHEN displaying commits in the Recent Commits column THEN the system SHALL include the commit date, hash, and commit message for better temporal context
4. WHEN showing recent commits THEN the system SHALL format the information as "YYYY-MM-DD hash commit message" for clear identification and temporal context
5. WHEN --show-commits is used THEN the system SHALL optimize API calls by only fetching commits for forks that have commits ahead of the upstream
6. WHEN displaying the Recent Commits column THEN the system SHALL show both the commit date and message in a clear, scannable format
7. WHEN no commits are ahead for a fork THEN the system SHALL keep the Recent Commits column empty since the commits count column already indicates the status
8. WHEN commits ahead exist THEN the system SHALL display up to the specified number of recent commits with dates in chronological order (newest first)
9. WHEN formatting commit information THEN the system SHALL ensure the date and message fit within reasonable column width for table readability
10. WHEN using --show-commits with --force-all-commits THEN the system SHALL still only show commits ahead, but fetch them for all forks regardless of optimization
11. WHEN displaying the Recent Commits column THEN the system SHALL prevent soft wrapping of commit text to maintain clean table formatting and readability

### Requirement 23

**User Story:** As a repository maintainer, I want consistent table formatting between standard and detailed fork displays, so that I have a unified user experience regardless of which mode I use.

#### Acceptance Criteria

1. WHEN I run `forklift show-forks <repo-url>` and `forklift show-forks <repo-url> --detail` THEN both commands SHALL use the same table structure, column widths, and formatting styles for consistency
2. WHEN displaying fork tables THEN the system SHALL use a universal rendering method that adapts the commit data presentation based on available information (status vs exact counts)
3. WHEN using the universal renderer THEN column widths SHALL be consistent across both modes (URL: 35, Stars: 8, Forks: 8, Commits: 15, Last Push: 14)
4. WHEN displaying commit information THEN the system SHALL show exact counts when available (--detail mode) or status indicators when not available (standard mode) in the same column format
5. WHEN rendering tables THEN the system SHALL use consistent titles, headers, and styling regardless of the data source (pagination-only vs API-enhanced)
6. WHEN showing additional information THEN summary statistics and insights SHALL be displayed consistently in both modes
7. WHEN using --show-commits THEN the Recent Commits column SHALL have identical formatting and behavior in both standard and detailed modes

### Requirement 24

**User Story:** As a repository maintainer, I want improved fork sorting that prioritizes the most valuable forks first, so that I can quickly identify the most promising forks without scrolling through less relevant ones.

#### Acceptance Criteria

1. WHEN displaying forks THEN the system SHALL sort forks using a multi-level priority system that puts the most valuable forks first
2. WHEN sorting forks THEN the system SHALL use the following priority order: (1) Commits ahead status (forks with commits first), (2) Stars count (descending), (3) Forks count (descending), (4) Last push date (most recent first)
3. WHEN comparing commits ahead status THEN forks with "Has commits" SHALL be sorted before forks with "0 commits" or "No commits ahead"
4. WHEN forks have the same commits ahead status THEN they SHALL be sorted by stars count in descending order (highest stars first)
5. WHEN forks have the same commits ahead status and stars count THEN they SHALL be sorted by forks count in descending order (most forked first)
6. WHEN forks have the same commits ahead status, stars count, and forks count THEN they SHALL be sorted by last push date in descending order (most recently active first)
7. WHEN displaying sorted forks THEN the table title SHALL clearly indicate the sorting criteria being used
8. WHEN sorting is applied THEN forks with unknown commit status SHALL be treated as potentially having commits and sorted with high priority
9. WHEN sorting forks THEN the system SHALL handle edge cases gracefully including missing timestamps, null values, and identical metrics
10. WHEN sorting large numbers of forks THEN the system SHALL maintain consistent sorting performance without degradation

### Requirement 25

**User Story:** As a repository maintainer, I want the `get_commits_ahead` method to avoid redundant main repository fetching, so that show-forks --detail runs faster with fewer API calls.

#### Acceptance Criteria

1. WHEN the `get_commits_ahead` method is called multiple times for the same parent repository THEN the system SHALL cache and reuse the parent repository data instead of fetching it repeatedly
2. WHEN caching parent repository data THEN the system SHALL store the repository metadata and default branch information needed for commit comparisons
3. WHEN the cached parent data is used THEN the system SHALL log the API call savings achieved

### Requirement 26

**User Story:** As a repository maintainer, I want to export fork data to CSV format, so that I can analyze fork information in spreadsheet applications, create custom reports, and integrate fork data with other tools.

#### Acceptance Criteria

1. WHEN I run `forklift show-forks <repo-url> --csv` THEN the system SHALL export the main fork table data to CSV format instead of displaying the table
2. WHEN using --csv flag THEN the system SHALL output CSV data to stdout with proper comma-separated values and quoted fields containing commas or special characters
3. WHEN exporting to CSV THEN the system SHALL include all main table columns: Fork URL, Stars, Forks, Commits Ahead, Last Push, and Language
4. WHEN --csv is combined with --show-commits THEN the system SHALL include the Recent Commits column data in the CSV export with commit messages properly escaped
5. WHEN --csv is combined with --detail THEN the system SHALL export exact commit counts instead of status indicators
6. WHEN --csv is combined with --ahead-only THEN the system SHALL export only forks that have commits ahead
7. WHEN --csv is combined with --max-forks THEN the system SHALL respect the fork limit in the CSV export
8. WHEN exporting CSV THEN the system SHALL use standard CSV headers that match the table column names for easy import into spreadsheet applications
9. WHEN CSV export encounters special characters THEN the system SHALL properly escape quotes, commas, and newlines according to CSV standards
10. WHEN --csv flag is used THEN the system SHALL suppress all progress indicators, status messages, and table formatting to ensure clean CSV output
11. WHEN CSV export fails THEN the system SHALL provide clear error messages and exit gracefully without corrupting the output
12. WHEN using --csv THEN the system SHALL maintain the same fork sorting order as the table display (commits ahead first, then by stars, forks, and last push date)