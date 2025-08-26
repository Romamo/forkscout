# Implementation Plan

- [x] 1. Set up project structure and core dependencies
  - Create directory structure with src/forklift package layout
  - Initialize pyproject.toml with uv package manager configuration
  - Add essential dependencies: httpx (GitHub API), click (CLI), pydantic (data models)
  - Add development dependencies: pytest, black, ruff
  - Configure pyproject.toml with black and ruff settings for code quality
  - _Requirements: 5.4_

- [x] 2. Implement core data models and configuration
- [x] 2.1 Create Pydantic data models for GitHub entities
  - Implement Repository, Fork, Commit, Feature, and RankedFeature models
  - Add validation and serialization methods for all models
  - Write unit tests for model validation and edge cases
  - _Requirements: 1.1, 1.2, 2.1_

- [x] 2.2 Implement configuration management system
  - Create ForkliftConfig and ScoringConfig classes with Pydantic
  - Add support for YAML/JSON configuration file loading
  - Implement environment variable override functionality
  - Write tests for configuration loading and validation
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 3. Build GitHub API client with rate limiting
- [x] 3.1 Implement GitHub API client wrapper
  - Create GitHubClient class with httpx for async HTTP requests
  - Add authentication handling for GitHub tokens
  - Implement basic repository and fork retrieval methods
  - Write unit tests with mocked API responses
  - _Requirements: 1.1, 1.5, 7.1, 7.2_

- [x] 3.2 Add rate limiting and error handling
  - Implement exponential backoff with jitter for rate limits
  - Add retry logic for network failures and API errors
  - Create comprehensive error handling for different API error types
  - Write tests for rate limiting and error recovery scenarios
  - _Requirements: 1.5, 6.1, 6.2, 6.3_

- [x] 4. Implement fork discovery and analysis
- [x] 4.1 Create fork discovery service
  - Implement ForkDiscoveryService to find all repository forks
  - Add filtering logic to identify active forks with unique commits
  - Implement commit comparison to find commits ahead of upstream
  - Write tests for fork discovery and filtering logic
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 4.3 Enhance fork filtering to skip only forks with no commits ahead
  - Add pre-filtering logic to skip only forks with no new commits (created_at >= pushed_at)
  - All other forks must proceed to full commit analysis regardless of age or stars
  - Remove complex prioritization - only bypass forks with definitively no commits ahead
  - Update fork discovery to use simple two-stage filtering (no commits check, then full analysis)
  - Add --scan-all CLI option to bypass filtering and analyze all forks when needed
  - Write tests for simplified filtering logic covering both created_at == pushed_at and created_at > pushed_at scenarios
  - _Requirements: 1.4, 1.5, 1.7_

- [x] 4.4 Optimize fork discovery with early pre-filtering to reduce API calls
  - Move lightweight timestamp filtering before expensive API calls in discover_forks method
  - Restructure _create_fork_with_comparison to be conditional based on pre-filtering
  - Add early filtering step after getting basic fork list but before comparison API calls
  - Implement lightweight fork metadata analysis using only basic repository data
  - Skip expensive /compare/, /repos/, and /users/ API calls for forks with no commits ahead
  - Update logging to show API call savings and performance metrics
  - Write tests to verify API call reduction and maintain filtering accuracy
  - Measure and document performance improvement (target: 60-80% reduction in API calls for typical repositories)
  - _Requirements: 1.4, 1.5_

- [x] 4.2 Build repository analyzer for feature extraction
  - Implement RepositoryAnalyzer to analyze individual forks
  - Add commit analysis to extract meaningful features
  - Implement change categorization (bug fixes, features, improvements)
  - Write tests for feature extraction and categorization
  - _Requirements: 2.1, 2.3, 2.4, 3.3_

- [x] 4.5 Implement commit explanation system
- [x] 4.5.1 Create core data models for commit explanations
  - Implement CommitExplanation, CommitWithExplanation, CommitCategory, and ImpactAssessment Pydantic models
  - Add CategoryType and ImpactLevel enums with appropriate values
  - Create AnalysisContext and FileChange models for explanation context
  - Write unit tests for all new data models including validation and serialization
  - _Requirements: 8.2, 8.6, 8.8_

- [x] 4.5.2 Create CommitCategorizer class with pattern matching
  - Implement commit message pattern analysis using regex patterns for each category type
  - Add file-based category detection using filename patterns and extensions
  - Create confidence scoring system for categorization decisions
  - Write unit tests for message patterns, file patterns, and confidence scoring
  - _Requirements: 8.6, 8.7_

- [x] 4.5.3 Implement ImpactAssessor class
  - Create impact scoring algorithm using change magnitude, file criticality, and quality factors
  - Implement file criticality assessment based on project structure and file types
  - Add test coverage and documentation impact evaluation
  - Write unit tests for impact calculation with various commit scenarios
  - _Requirements: 8.8_

- [x] 4.5.4 Create ExplanationGenerator class
  - Create template system for different category and impact combinations
  - Implement context extraction from commits and file changes
  - Add explanation formatting and conciseness enforcement
  - Write unit tests for template rendering and context extraction
  - _Requirements: 8.9_

- [x] 4.5.5 Build CommitExplanationEngine orchestrator
  - Implement CommitExplanationEngine that coordinates categorizer, assessor, and generator
  - Add single commit explanation method with error handling
  - Create batch processing method for multiple commits
  - Write unit tests for engine coordination and error handling
  - _Requirements: 8.1, 8.5_

- [x] 4.5.6 Enhance RepositoryAnalyzer with explanation support
  - Modify RepositoryAnalyzer constructor to accept optional CommitExplanationEngine
  - Update analyze_fork method to support explain parameter
  - Add commit explanation generation to analysis workflow
  - Write unit tests for analyzer integration with explanations enabled/disabled
  - _Requirements: 8.1, 8.4_

- [x] 5. Create feature ranking and scoring system
- [x] 5.1 Implement feature scoring algorithm
  - Create FeatureRankingEngine with configurable scoring weights
  - Implement scoring based on code quality, community engagement, and recency
  - Add logic to calculate numerical scores from 1-100
  - Write comprehensive tests for scoring algorithm accuracy
  - _Requirements: 2.1, 2.2, 2.5_

- [x] 5.2 Add feature grouping and similarity detection
  - Implement algorithm to identify similar features across forks
  - Add grouping logic for related implementations
  - Create ranking system to order features by calculated scores
  - Write tests for feature grouping and ranking accuracy
  - _Requirements: 2.4, 2.5_

- [ ] 6. Build report generation system
- [-] 6.1 Implement markdown report generator
  - Create ReportGenerator class to produce human-readable reports
  - Add feature summaries with code snippets and fork links
  - Implement categorized organization of features in reports
  - Write tests for report generation and formatting
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 6.2 Add comprehensive reporting features
  - Implement top 20 feature display with detailed score explanations
  - Add fork metadata including author, activity, and statistics
  - Create summary sections with analysis overview and statistics
  - Write tests for complete report generation workflow
  - _Requirements: 3.4, 3.5_

- [ ] 6.3 Add explanation integration to report generation
  - Update markdown report generator to include commit explanations
  - Add explanation sections to generated reports with proper formatting
  - Create summary statistics for explanation categories and impact levels
  - Write tests for report generation with explanations included
  - _Requirements: 8.3, 8.9_

- [ ] 7. Implement pull request automation
- [ ] 7.1 Create PR creation service
  - Implement PRCreatorService for automated pull request generation
  - Add logic to create PRs for features above score threshold
  - Implement proper attribution and source fork linking
  - Write tests for PR creation with mocked GitHub API
  - _Requirements: 4.1, 4.2, 4.3_

- [ ] 7.2 Add advanced PR handling features
  - Implement merge conflict detection and draft PR creation
  - Add support for repository-specific contribution guidelines
  - Create PR description templates with feature value explanations
  - Write tests for conflict handling and guideline compliance
  - _Requirements: 4.4, 4.5_

- [x] 8. Build CLI interface and main application
- [x] 8.1 Implement Click-based CLI interface
  - Create main CLI application with Click framework
  - Add commands for analyze, configure, and schedule operations
  - Implement progress indicators and user feedback
  - Write tests for CLI command parsing and execution
  - _Requirements: 5.1, 5.5, 7.4_

- [x] 8.2 Add advanced CLI features
  - Implement configuration file support and command-line overrides
  - Add scheduling support for recurring analysis
  - Create verbose logging and debug output options
  - Write integration tests for complete CLI workflows
  - _Requirements: 5.2, 5.3, 5.5_

- [x] 8.3 Implement step-by-step analysis CLI commands
  - Create Repository Display Service for incremental repository exploration
  - Implement show-repo command to display detailed repository information
  - Add show-forks command to display fork summary table with key metrics
  - Write unit tests for repository display formatting and data presentation
  - _Requirements: 6.1, 6.3, 6.8_

- [x] 8.4 Add promising forks and detailed fork analysis commands
  - Implement show-promising command with configurable filtering criteria
  - Create show-fork-details command to display branch information and statistics
  - Add Interactive Analyzer service for focused fork/branch analysis
  - Write tests for fork filtering logic and detailed analysis workflows
  - _Requirements: 6.4, 6.5, 6.8_

- [x] 8.5 Implement commit analysis and display commands
  - Create analyze-fork command for specific fork/branch combination analysis
  - Implement show-commits command with detailed commit information display
  - Add formatted output with simple tables and text-based progress indicators
  - Write tests for commit analysis and display formatting
  - _Requirements: 6.6, 6.7, 6.8, 6.9_

- [x] 8.6 Add lightweight fork preview command
  - Implement list-forks command for fast fork preview using minimal API calls
  - Create ForksPreview and ForkPreviewItem data models
  - Add efficient fork listing that shows name, owner, stars, and last push date
  - Write unit tests for lightweight fork preview functionality
  - _Requirements: 6.2_

- [x] 8.7 Fix missing list-forks CLI command implementation
  - Implement missing list_forks_preview method in RepositoryDisplayService
  - Create ForksPreview and ForkPreviewItem data models in models/analysis.py
  - Add @cli.command("list-forks") decorator and function to CLI
  - Implement lightweight fork preview using minimal API calls (no commit analysis)
  - Add proper error handling and simple text formatting for fast fork display
  - Write unit and integration tests for the complete list-forks functionality
  - _Requirements: 6.2_

- [x] 8.8 Add commits ahead column to list-forks command
  - Enhance ForkPreviewItem model to include commits_ahead field
  - Implement corrected logic to detect forks with no commits ahead using created_at >= pushed_at comparison
  - Add "Commits Ahead" column showing "None" for forks with no new commits, "Unknown" for others
  - Update harvesting logic to skip only forks with "None" commits ahead from detailed analysis
  - All other forks (with "Unknown" status) must be scanned with full commit analysis
  - Update list_forks_preview method to display commits ahead status
  - Write unit tests for commits ahead detection covering both created_at == pushed_at and created_at > pushed_at scenarios
  - _Requirements: 6.2_

- [ ] 8.9 Add CLI support for --explain flag
- [x] 8.9.1 Update analyze command with explanation support
  - Add --explain flag to main analyze command
  - Modify command handler to pass explain parameter to analyzer
  - Update progress indicators to show explanation generation status
  - Write integration tests for analyze command with --explain flag
  - _Requirements: 8.1, 8.3_

- [x] 8.9.2 Enhance step-by-step commands with explanations
  - Add --explain flag to analyze-fork and show-commits commands
  - Update command handlers to generate and display explanations
  - Modify output formatting to include explanation information
  - Write integration tests for all enhanced commands with explanation support
  - _Requirements: 8.10_

- [x] 8.9.3 Implement simple text-based explanation display
  - Implement formatted output for commits with explanations using simple text formatting
  - Add text labels for different category types and impact levels (instead of colors/emojis)
  - Create clear hierarchy with indentation and text separators
  - Write unit tests for output formatting and terminal compatibility
  - _Requirements: 8.3, 8.9_

- [ ] 8.9.4 Add explanation configuration support
  - Create ExplanationConfig model with settings for explanation behavior
  - Add configuration options for explanation length, confidence thresholds, and template styles
  - Integrate explanation config into main ForkliftConfig
  - Write unit tests for configuration loading and validation
  - _Requirements: 8.1, 8.9_

- [x] 8.10 Implement GitHub commit links and enhanced formatting
- [x] 8.10.1 Create GitHub link generation system
  - Implement GitHubLinkGenerator class with commit URL generation
  - Add URL validation and formatting methods
  - Update CommitExplanation model to include github_url field
  - Write unit tests for link generation and validation
  - _Requirements: 9.1, 9.2, 9.5, 9.6_

- [x] 8.10.2 Enhance explanation formatting with visual separation
  - Create ExplanationFormatter class for rich terminal output
  - Implement visual separation between descriptions and evaluations
  - Add color coding and icons for categories and impact levels
  - Create FormattedExplanation model for structured display
  - Write unit tests for formatting and visual consistency
  - _Requirements: 11.1, 11.4, 12.1, 12.3, 12.4, 12.5_

- [x] 8.10.3 Update explanation generation to include GitHub links
  - Modify ExplanationGenerator to generate GitHub commit URLs
  - Update CommitExplanationEngine to include links in explanations
  - Ensure all explanation outputs include properly formatted GitHub links
  - Write unit tests for link integration in explanation workflow
  - _Requirements: 9.3, 9.4, 9.6_

- [x] 8.10.4 Enhance CLI output with improved explanation display
  - Update CLI commands to use new ExplanationFormatter
  - Implement table-based display for multiple commit explanations
  - Add clickable links support for supported terminals
  - Ensure consistent formatting across all explanation-enabled commands
  - Write integration tests for enhanced CLI output
  - _Requirements: 12.2, 12.3, 12.6_

- [x] 9. Implement caching and storage layer
- [x] 9.1 Create SQLite-based caching system
  - Implement database schema for caching fork analysis results
  - Add cache invalidation based on repository activity
  - Create data access layer for cached analysis retrieval
  - Write tests for cache operations and data persistence
  - _Requirements: 1.5, 6.3_

- [x] 9.2 Add cache management features
  - Implement cache warming for frequently analyzed repositories
  - Add cache cleanup and maintenance operations
  - Create cache statistics and monitoring capabilities
  - Write tests for cache management and cleanup operations
  - _Requirements: 6.5_

- [ ] 10. Add comprehensive error handling and logging
- [ ] 10.1 Implement robust error handling system
  - Create ErrorHandler class for different error types
  - Add circuit breaker pattern for external API calls
  - Implement graceful degradation when fork analysis fails
  - Write tests for error handling and recovery scenarios
  - _Requirements: 7.1, 7.2, 7.3_

- [ ] 10.2 Add logging and monitoring capabilities
  - Implement comprehensive logging with structured output
  - Add progress tracking and status reporting
  - Create error summary reporting in final analysis
  - Write tests for logging and monitoring functionality
  - _Requirements: 7.4, 7.5_

- [ ] 11. Create comprehensive test suite
- [ ] 11.1 Implement unit tests for all components
  - Write unit tests for all service classes and data models
  - Add mocked tests for GitHub API interactions
  - Create test fixtures for consistent testing data
  - Achieve >90% code coverage across all modules
  - _Requirements: All requirements_

- [ ] 11.2 Add integration tests with specific test repositories
  - Write integration tests using https://github.com/maliayas/github-network-ninja
  - Add tests using https://github.com/sanila2007/youtube-bot-telegram
  - Create step-by-step command integration tests with real fork data
  - Validate all CLI commands work correctly with test repositories
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

- [ ] 11.3 Add end-to-end and performance tests
  - Write end-to-end workflow tests for complete analysis pipeline
  - Create performance tests for large repository analysis
  - Write tests for concurrent processing and rate limiting
  - Add comprehensive error handling and recovery tests
  - _Requirements: All requirements_

- [ ] 12. Finalize packaging and documentation
- [ ] 12.1 Complete package configuration and distribution
  - Finalize pyproject.toml with all dependencies and metadata
  - Create comprehensive README with usage examples
  - Add CLI help documentation and usage guides
  - Write installation and setup instructions
  - _Requirements: 5.4_

- [x] 12.2 Create comprehensive evaluation criteria documentation
  - Write detailed README section explaining evaluation criteria
  - Document commit categorization patterns and rules with examples
  - Create impact assessment documentation with file criticality rules
  - Add value assessment criteria with "yes/no/unclear" examples
  - Include decision trees and flowcharts for evaluation logic
  - Write troubleshooting guide for common evaluation questions
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

- [ ] 12.3 Add final integration and validation
  - Perform end-to-end testing with real repositories
  - Validate all requirements are met through testing
  - Create example configuration files and usage scenarios
  - Write final documentation and troubleshooting guides
  - Test GitHub link functionality and explanation formatting
  - _Requirements: All requirements_

- [ ] 13. Implement enhanced pagination support for large repositories
- [ ] 13.1 Create pagination management infrastructure
  - Implement PaginationManager class with concurrent request handling
  - Create PaginationProgressTracker for real-time progress monitoring
  - Add PaginationConfig, PaginationStats, and PaginationCheckpoint data models
  - Write unit tests for pagination infrastructure components
  - _Requirements: 14.2, 14.3, 14.9_

- [ ] 13.2 Enhance GitHub client with optimized pagination
  - Update GitHubClient to use maximum per_page values (100) for all API calls
  - Implement get_all_repository_forks with progress callbacks and concurrent processing
  - Add get_paginated_commits with streaming support for large datasets
  - Create get_repository_branches_paginated with memory-efficient processing
  - Write unit tests for enhanced GitHub client pagination methods
  - _Requirements: 14.1, 14.6, 14.7_

- [ ] 13.3 Implement resumable pagination with checkpointing
  - Create PaginationCache class for storing pagination state and results
  - Add checkpoint creation and restoration functionality
  - Implement resume_pagination method to continue from interruption points
  - Add cache cleanup and maintenance for expired pagination data
  - Write unit tests for resumable pagination and checkpoint management
  - _Requirements: 14.5, 14.10_

- [ ] 13.4 Add intelligent rate limiting for paginated requests
  - Enhance rate limiting to account for remaining pages in pagination operations
  - Implement smart backoff strategies that consider pagination context
  - Add rate limit pooling for concurrent pagination requests
  - Create adaptive request timing based on API quota and remaining pages
  - Write unit tests for pagination-aware rate limiting
  - _Requirements: 14.4, 14.7_

- [ ] 13.5 Implement streaming pagination for memory efficiency
  - Add streaming pagination support for large commit datasets
  - Implement memory monitoring and automatic streaming threshold detection
  - Create batch processing for paginated results to avoid memory exhaustion
  - Add configurable memory limits and automatic garbage collection
  - Write unit tests for streaming pagination and memory management
  - _Requirements: 14.6, 14.8_

- [ ] 13.6 Enhance CLI with pagination progress indicators
  - Update all CLI commands to show pagination progress for large operations
  - Add progress bars with page counts, items fetched, and estimated completion time
  - Implement pagination statistics display including API calls made and remaining
  - Create configurable progress output formats (verbose, quiet, json)
  - Write integration tests for CLI pagination progress display
  - _Requirements: 14.3, 14.9_

- [ ] 13.7 Add pagination configuration and limits
  - Integrate PaginationConfig into main ForkliftConfig system
  - Add CLI options for max_forks, max_commits, and max_branches limits
  - Implement configurable batch sizes and concurrent request limits
  - Create pagination performance tuning options for different repository sizes
  - Write unit tests for pagination configuration and limit enforcement
  - _Requirements: 14.8_

- [ ] 13.8 Implement comprehensive pagination error handling
  - Add retry logic with exponential backoff for pagination failures
  - Implement graceful handling of partial pagination failures
  - Create error recovery that continues processing remaining pages
  - Add detailed error reporting for pagination issues with context
  - Write unit tests for pagination error scenarios and recovery
  - _Requirements: 14.10_

- [ ] 13.9 Add pagination performance testing and optimization
  - Create performance tests for large repository pagination scenarios
  - Implement benchmarking for different pagination strategies
  - Add memory usage profiling for paginated operations
  - Create optimization recommendations based on repository characteristics
  - Write integration tests with repositories having thousands of forks
  - _Requirements: 14.1, 14.2, 14.6, 14.7_

- [x] 14. Add interactive mode to analyze command with user confirmation stops
- [x] 14.1 Create interactive analysis orchestrator
  - Implement InteractiveAnalysisOrchestrator class to manage step-by-step analysis workflow
  - Add step definitions for each major analysis phase (discovery, filtering, analysis, ranking, reporting)
  - Create user confirmation prompts with clear step descriptions and progress indicators
  - Implement user confirmation stops after each successful step completion
  - Write unit tests for orchestrator workflow management and user interaction handling
  - _Requirements: 15.1, 15.2, 15.3_

- [x] 14.2 Implement interactive step execution with progress display
  - Create InteractiveStep base class with execute, display_results, and get_user_confirmation methods
  - Implement specific step classes for fork discovery, filtering, analysis, and ranking phases
  - Add Rich-based progress displays with step summaries and intermediate results
  - Create user-friendly confirmation prompts with clear step summaries and continue/abort options
  - Write unit tests for step execution and user interaction flows
  - _Requirements: 15.4, 15.5, 15.6_

- [x] 14.3 Add interactive CLI command and configuration
  - Add --interactive flag to main analyze command with interactive mode activation
  - Create InteractiveConfig model with settings for confirmation prompts and display options
  - Implement interactive mode detection and orchestrator initialization in CLI
  - Add configuration options for auto-confirmation timeouts and default choices
  - Write integration tests for interactive analyze command with various user input scenarios
  - _Requirements: 15.7, 15.8, 15.9_

- [x] 14.4 Implement step-specific user confirmations and data display
  - Create formatted displays for fork discovery results with counts and filtering criteria
  - Add confirmation prompts for proceeding with filtered fork analysis
  - Implement intermediate results display for analysis progress with feature counts
  - Create ranking results preview with top features before final report generation
  - Write unit tests for step-specific displays and confirmation handling
  - _Requirements: 15.10, 15.11, 15.12_

- [x] 14.5 Add interactive mode session management and completion summary
  - Implement interactive mode state persistence for resuming interrupted sessions
  - Create comprehensive step completion summaries with metrics and results
  - Add session duration tracking and analysis statistics
  - Implement graceful abort handling with summary of completed work
  - Write unit tests for session management and completion summary generation
  - _Requirements: 15.13, 15.14, 15.15_

- [x] 14.6 Fix analyze command cache disabling parameter bug (HIGH PRIORITY)
  - Fix GitHubClient.get_repository() method to accept disable_cache parameter
  - Update all GitHub API methods to support disable_cache parameter consistently
  - Ensure ForkDiscoveryService can pass disable_cache to all GitHub API calls
  - Add proper parameter handling and validation for cache bypass functionality
  - Fix the "unexpected keyword argument 'disable_cache'" error in analyze command
  - Write unit tests for disable_cache parameter handling in GitHub client methods
  - _Requirements: 22.1, 22.2, 22.5, 22.10_

- [ ] 15. Implement cache disabling functionality for fresh data retrieval
- [ ] 15.1 Add cache bypass infrastructure to core components
  - Create CacheBypassManager class to handle cache disabling logic
  - Add disable_cache parameter to GitHubClient methods for API calls
  - Update CacheManager to support bypass mode that skips read/write operations
  - Add cache bypass logging and statistics tracking
  - Write unit tests for cache bypass functionality and logging
  - _Requirements: 16.2, 16.3, 16.9_

- [ ] 15.2 Enhance GitHub client with cache disabling support
  - Add disable_cache parameter to all GitHub API methods (get_repository, get_forks, get_commits_ahead)
  - Implement cache bypass logic in _get_with_cache method
  - Add cache operation logging for debugging and performance analysis
  - Update pagination methods to support cache disabling
  - Write unit tests for GitHub client cache bypass functionality
  - _Requirements: 16.1, 16.2, 16.3, 16.7_

- [ ] 15.3 Update analysis services with cache disabling support
  - Add disable_cache parameter to ForkDiscoveryService methods
  - Update RepositoryAnalyzer to support cache bypass for fork analysis
  - Modify RepositoryDisplayService and InteractiveAnalyzer to handle cache disabling
  - Add cache bypass support to InteractiveAnalysisOrchestrator
  - Write unit tests for analysis services with cache disabled
  - _Requirements: 16.5, 16.6_

- [ ] 15.4 Add --disable-cache CLI flag to all relevant commands
  - Add --disable-cache flag to main analyze command
  - Update step-by-step commands (show-forks, show-commits, analyze-fork) with cache disabling
  - Implement cache bypass warning messages for user awareness
  - Add timing information display when cache is disabled
  - Write integration tests for all CLI commands with --disable-cache flag
  - _Requirements: 16.1, 16.4, 16.6, 16.8_

- [ ] 15.5 Implement cache configuration and performance monitoring
  - Create CacheConfig model with cache disabling and logging options
  - Add cache bypass statistics collection and reporting
  - Implement performance impact measurement for cache-disabled operations
  - Add configuration options for cache bypass behavior
  - Write unit tests for cache configuration and performance monitoring
  - _Requirements: 16.8, 16.9, 16.10_

- [ ] 15.6 Add comprehensive testing for cache disabling functionality
  - Write integration tests for cache bypass with real GitHub API calls
  - Create performance comparison tests between cached and non-cached operations
  - Add tests for cache bypass with interactive mode and explanations
  - Implement error handling tests for cache bypass scenarios
  - Write end-to-end tests for complete analysis workflow with cache disabled
  - _Requirements: 16.1, 16.5, 16.7, 16.10_

- [ ] 16. Replace custom cache system with Hishel HTTP caching (HIGH PRIORITY)
- [ ] 16.1 Remove custom cache system and add Hishel dependency
  - Add hishel dependency to pyproject.toml for HTTP caching
  - Remove custom cache management code (CacheManager, CacheWarmingConfig, CacheCleanupConfig, etc.)
  - Remove custom SQLite cache implementation (cache.py, cache_manager.py)
  - Update imports and dependencies to remove custom cache references
  - Write migration notes documenting the simplification
  - _Requirements: 21.1, 21.8_

- [ ] 16.2 Integrate Hishel with GitHub client
  - Update GitHubClient to use Hishel-wrapped httpx client for automatic HTTP caching
  - Configure Hishel with SQLite storage backend and appropriate cache settings
  - Set default TTL of 30 minutes for GitHub API responses
  - Remove all custom cache integration code from GitHub client
  - Write unit tests for Hishel integration with mocked HTTP responses
  - _Requirements: 21.2, 21.3, 21.5, 21.10_

- [ ] 16.3 Implement cache bypass functionality with Hishel
  - Replace custom disable_cache logic with Hishel cache bypass configuration
  - Update --disable-cache flag to configure Hishel to bypass cache for the session
  - Remove custom cache bypass code and use Hishel's built-in bypass functionality
  - Update all CLI commands to support cache bypass through Hishel configuration
  - Write unit tests for simplified cache bypass functionality
  - _Requirements: 21.4, 21.12_

- [ ] 16.4 Simplify cache configuration and remove custom config
  - Remove complex CacheConfig and replace with simple Hishel configuration
  - Update ForkliftConfig to use minimal cache settings for Hishel
  - Remove cache warming, cleanup, and monitoring configuration classes
  - Add basic cache location and size limit configuration for Hishel
  - Write unit tests for simplified cache configuration
  - _Requirements: 21.5, 21.10, 21.11_

- [ ] 16.5 Update all service classes to remove custom cache dependencies
  - Remove CacheManager and AnalysisCacheManager dependencies from all services
  - Update CLI commands to remove custom cache initialization code
  - Ensure all services use the simplified Hishel-enabled GitHub client
  - Remove cache management complexity from service constructors
  - Write integration tests for simplified service initialization
  - _Requirements: 21.6, 21.7, 21.12_

- [ ] 16.6 Add basic cache monitoring from Hishel
  - Implement simple cache hit/miss statistics collection from Hishel
  - Add basic cache performance logging (much simpler than custom system)
  - Remove complex cache monitoring and metrics code
  - Add simple cache size and storage monitoring
  - Write unit tests for simplified cache statistics
  - _Requirements: 21.6, 21.7_

- [ ] 16.7 Implement comprehensive testing for simplified cache system
  - Write integration tests for Hishel HTTP caching with real GitHub API calls
  - Create performance tests comparing cached vs non-cached HTTP operations
  - Remove complex cache management tests and replace with simple Hishel tests
  - Test cache persistence across application restarts
  - Write end-to-end tests for complete workflows with Hishel caching enabled
  - _Requirements: 21.1, 21.2, 21.3, 21.7, 21.9_

- [ ] 17. Implement fork qualification data collection for user decision-making
- [x] 17.1 Create fork qualification data models
  - Implement ForkQualificationMetrics data model with all GitHub API fields (stars, forks, size, language, activity dates, topics, etc.)
  - Create QualifiedForksResult to hold collection of fork metrics and statistics
  - Add QualificationStats for summary information (total forks, API calls saved, etc.)
  - Write unit tests for all qualification data models and validation
  - _Requirements: 20.1, 20.2_

- [x] 17.2 Build ForkListProcessor for efficient API usage
  - Implement ForkListProcessor class to handle paginated forks list endpoint calls
  - Add get_all_forks_list_data method using only `/repos/{owner}/{repo}/forks?per_page=100&page=N`
  - Create extract_qualification_fields method to extract all available metrics from fork list response
  - Implement validate_fork_data_completeness for handling missing data gracefully
  - Write unit tests for fork list processing and comprehensive data extraction
  - _Requirements: 20.1, 20.2, 20.9_

- [x] 17.3 Create ForkDataCollectionEngine for data collection and commits-ahead detection
  - Implement ForkDataCollectionEngine class with collect_fork_data_from_list method
  - Extract and organize all qualification metrics without scoring or filtering
  - Add determine_commits_ahead_status method using created_at >= pushed_at comparison logic
  - Implement exclude_archived_and_disabled and exclude_no_commits_ahead methods
  - Calculate activity patterns (days since creation, last update, last push) and commits ahead status
  - Write unit tests for data collection, commits-ahead detection, and organization logic
  - _Requirements: 20.2, 20.3, 20.4.1, 20.4.2, 20.4.3, 20.6, 20.7_

- [x] 17.4 Enhance ForkDiscoveryService with data collection and automatic filtering
  - Add ForkDataCollectionEngine to ForkDiscoveryService constructor
  - Implement discover_and_collect_fork_data method that gathers comprehensive fork information
  - Add automatic exclusion of forks with no commits ahead (created_at >= pushed_at) from expensive analysis
  - Update existing methods to work with collected fork data and commits-ahead detection
  - Add statistics tracking for API call savings from filtering forks with no commits ahead
  - Write unit tests for integrated fork discovery, data collection, and automatic filtering workflow
  - _Requirements: 20.4.2, 20.4.3, 20.9, 20.10, 20.12, 20.13_

- [x] 17.5 Add fork data display CLI commands with commits-ahead status
  - Create show_fork_data method in RepositoryDisplayService to display all collected fork metrics
  - Implement comprehensive fork data display showing stars, forks, size, language, activity dates, topics, commits-ahead status
  - Add clear indication of forks with "No commits ahead" vs "Has commits" based on date comparison
  - Add sortable columns for user decision-making (by stars, activity, size, commits status, etc.)
  - Create clear tabular display showing which forks are excluded from analysis and why
  - Write integration tests for fork data display CLI commands including commits-ahead detection
  - _Requirements: 20.4.1, 20.4.2, 20.4.3, 20.9, 20.10, 20.13_

- [x] 17.6 Let users choose forks for analysis based on displayed data
  - Update CLI to display comprehensive fork data and let users decide which forks to analyze
  - Remove automatic filtering and scoring - present all data for user decision
  - Add optional basic filters (exclude archived/disabled) but no quality scoring
  - Implement user-driven fork selection for detailed analysis
  - Write integration tests for user-driven fork selection workflow
  - _Requirements: 20.8, 20.10, 20.11, 20.13_

- [x] 17.7 Add comprehensive testing for fork data collection system
  - Write unit tests for all data collection components with realistic fork data
  - Create integration tests using test repositories with various fork patterns
  - Add performance tests measuring API call reduction and processing efficiency
  - Implement contract tests for GitHub API fork list response handling
  - Write end-to-end tests for complete data collection workflow with real data
  - _Requirements: 20.1, 20.2, 20.12, 20.13_

- [-] 19. Fix show-forks command to use pagination-only requests (CRITICAL)
- [ ] 19.1 Update CLI to use pagination-only fork data collection
  - Change _show_forks_summary function in src/forklift/cli.py to call show_fork_data instead of show_forks_summary
  - Remove the old show_forks_summary method from RepositoryDisplayService that makes expensive API calls
  - Ensure show-forks command uses only `/repos/{owner}/{repo}/forks?per_page=100&page=N` endpoint
  - Test that no individual repository API calls or comparison API calls are made
  - Verify the command displays comprehensive fork data using only paginated forks list data
  - _Requirements: 20.1, 20.2, 20.10, 20.11_

- [ ] 18. Fix immediate console formatting issues and implement simple, compatible formatting as default
- [x] 18.0 Fix current emoji and Unicode display issues (HIGH PRIORITY)
  - Replace all emoji characters (📝, ❓, 🟢, ❔) with simple text labels in commit explanations
  - Fix Unicode table borders that display as literal characters in some terminals
  - Update ExplanationFormatter to use ASCII characters instead of Unicode box drawing
  - Remove special symbols from commit category and impact displays
  - Write unit tests for ASCII-only output formatting
  - _Requirements: 18.1, 18.2, 18.7_

- [ ] 18. Implement simple, compatible console formatting as default
- [ ] 18.1 Replace Rich formatting with simple text-based output
  - Remove emoji and Unicode symbols from all CLI output (replace ❓, 🟢, ❔ with text labels)
  - Replace Rich table formatting with simple ASCII tables using |, -, + characters
  - Convert color-coded status indicators to text prefixes (SUCCESS:, ERROR:, INFO:, WARNING:)
  - Remove complex Rich markup and use simple indentation and spacing for hierarchy
  - Write unit tests for simple formatting output and compatibility
  - _Requirements: 18.1, 18.2, 18.3, 18.4_

- [ ] 18.2 Update commit explanation display to use simple formatting
  - Replace emoji category indicators (❓, 🟢, etc.) with text labels (OTHER, LOW, UNCLEAR)
  - Convert Rich table borders to simple ASCII characters for commit explanation tables
  - Remove special Unicode characters from all commit display formatting
  - Use plain text separators and indentation instead of Rich visual elements
  - Write unit tests for simplified commit explanation display
  - _Requirements: 18.7, 18.11_

- [ ] 17.3 Add optional enhanced formatting mode
  - Create FormattingMode enum with SIMPLE (default), ENHANCED, and PLAIN options
  - Add --enhanced-formatting CLI flag to enable Rich formatting for users who want it
  - Implement TerminalCapabilityDetector to auto-detect when enhanced formatting is safe
  - Create FormattingConfig model with user preferences for formatting level
  - Write unit tests for formatting mode detection and configuration
  - _Requirements: 18.5, 18.6, 18.12_

- [ ] 17.4 Update all CLI commands to use simple formatting by default
  - Modify all CLI commands to use simple ASCII formatting as the default mode
  - Update progress indicators to use simple text (e.g., "Processing 5/10..." instead of progress bars)
  - Ensure all table displays use ASCII characters and work in any terminal
  - Add --no-color flag support for completely plain text output
  - Write integration tests for all CLI commands with simple formatting
  - _Requirements: 18.8, 18.9, 18.10, 18.11_

- [ ] 18. Implement detailed commit view with comprehensive information display
- [x] 18.1 Add --detail flag to show-commits command
  - Add --detail CLI option to show-commits command with comprehensive output mode
  - Create DetailedCommitDisplay class for formatting detailed commit information
  - Implement automatic AI summary generation when --detail flag is used
  - Add GitHub URL generation and display for each commit in detailed view
  - Write unit tests for detailed commit display formatting and option handling
  - _Requirements: 19.1, 19.2, 19.3, 19.6_

- [ ] 18.2 Implement comprehensive commit information fetching
  - Enhance GitHub client to fetch complete commit details including diff content
  - Add commit diff retrieval with proper formatting and truncation for large diffs
  - Implement commit message formatting with proper line breaks and structure
  - Create diff processing logic to handle various file types and change patterns
  - Write unit tests for commit detail fetching and diff processing
  - _Requirements: 19.4, 19.5, 19.10_

- [ ] 18.3 Integrate AI summary generation with detailed view
  - Modify detailed commit display to automatically trigger AI summary generation
  - Add error handling for AI summary failures in detailed mode
  - Implement progress indicators for detailed processing including AI summary generation
  - Create fallback display when AI summaries are unavailable
  - Write integration tests for detailed view with AI summary integration
  - _Requirements: 19.3, 19.8, 19.9, 19.11_

- [ ] 18.4 Add detailed view formatting and display enhancements
  - Create visual separation between GitHub URL, AI summary, message, and diff sections
  - Implement proper formatting for diff content with syntax highlighting where possible
  - Add support for combining --detail with existing filter options (limit, branch, since, until, author)
  - Create comprehensive output formatting that maintains readability for detailed information
  - Write unit tests for detailed formatting and visual separation
  - _Requirements: 19.6, 19.7, 19.10_

- [ ] 18.5 Add rate limiting and performance optimization for detailed view
  - Implement intelligent rate limiting for combined GitHub API and OpenAI API calls
  - Add batch processing optimization for detailed commit analysis
  - Create progress tracking and estimation for detailed processing operations
  - Implement caching strategies for detailed commit information to reduce API calls
  - Write performance tests for detailed view with various commit volumes
  - _Requirements: 19.11, 19.12_

- [ ] 18.6 Add comprehensive testing for detailed commit view
  - Write unit tests for DetailedCommitDisplay and DetailedCommitProcessor classes
  - Create integration tests for --detail flag with real GitHub repositories
  - Add tests for error handling when AI summary generation fails
  - Write performance tests for detailed view with various commit volumes and rate limiting scenarios
  - Create tests for diff truncation and formatting with large commits
  - Add tests for combining --detail with existing filter options
  - Write tests for progress tracking and batch processing functionality
  - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 19.7, 19.8, 19.9, 19.10, 19.11, 19.12_unit tests for markdown formatting removal and text emphasis
  - _Requirements: 18.5, 18.7, 18.11_

- [ ] 17.4 Update console output system with formatting abstraction
  - Create ConsoleOutput class that abstracts Rich console and plain text output
  - Replace all direct `console.print()` calls with ConsoleOutput methods
  - Implement plain text equivalents for color codes using prefixes (SUCCESS:, ERROR:, INFO:, WARNING:)
  - Add plain text table formatting using ASCII borders and spacing
  - Write unit tests for console output abstraction and plain text formatting
  - _Requirements: 18.4, 18.6, 18.8, 18.11_

- [ ] 17.5 Update progress indicators and visual elements for plain text mode
  - Implement plain text progress indicators using simple text-based displays
  - Create text-based separators and visual hierarchy using indentation and spacing
  - Update all Rich Panel and Table usage to support plain text alternatives
  - Add plain text formatting for interactive prompts and confirmations
  - Write unit tests for plain text progress indicators and visual elements
  - _Requirements: 18.6, 18.9, 18.12_

- [ ] 17.6 Update all CLI commands and display services with formatting compatibility
  - Update src/forklift/cli.py to use new ConsoleOutput abstraction
  - Modify src/forklift/display/repository_display_service.py for formatting compatibility
  - Update explanation formatting in src/forklift/pr/explanation_formatter.py
  - Ensure all show_commit_summary.py and other scripts support plain text mode
  - Write integration tests for all CLI commands with --plain-text flag
  - _Requirements: 18.2, 18.3, 18.4, 18.11_

- [ ] 17.7 Add comprehensive testing for formatting compatibility
  - Write integration tests for all commands with --no-color and --plain-text flags
  - Create tests for terminal capability detection with various terminal types
  - Add tests for formatting conversion accuracy and information preservation
  - Implement visual regression tests comparing Rich and plain text output
  - Write end-to-end tests for complete workflows in plain text mode
  - _Requirements: 18.1, 18.2, 18.11, 18.12_

- [ ] 18. Implement compact AI summary without buzzwords
- [x] 18.1 Update AI summary prompt to be concise and direct
  - Replace verbose prompt with compact "Summarize this commit: what changed, why, impact"
  - Remove buzzwords like "senior developer" and lengthy instructions
  - Update create_summary_prompt method in AICommitSummaryEngine
  - Ensure prompt stays under 50 characters for efficiency
  - Write unit tests for new compact prompt generation
  - _Requirements: 17.2, 17.16_

- [x] 18.2 Simplify AI summary response parsing and display
  - Remove structured section parsing (what_changed, why_changed, potential_side_effects)
  - Update _parse_summary_response to return single summary text only
  - Modify AISummary model to focus on summary_text field only
  - Remove verbose formatting and structured display sections
  - Write unit tests for simplified response parsing
  - _Requirements: 17.10, 17.16, 17.17_

- [x] 18.3 Enforce brevity in AI summary generation
  - Reduce max_tokens in AISummaryConfig from 500 to 150 tokens
  - Add response length validation to ensure summaries stay under 3 sentences
  - Implement post-processing to trim verbose AI responses
  - Update cost estimation for shorter token usage
  - Write unit tests for brevity enforcement and length validation
  - _Requirements: 17.16, 17.17_

- [x] 18.4 Update CLI display for compact AI summaries
  - Modify show-commits command to display compact summaries inline
  - Remove structured formatting and verbose visual separation
  - Update progress indicators to reflect shorter processing times
  - Ensure summaries display cleanly in both Rich and plain text modes
  - Write integration tests for compact AI summary display
  - _Requirements: 17.1, 17.10, 17.17_

- [x] 18.5 Add configuration option for AI summary style
  - Add compact_mode boolean to AISummaryConfig
  - Allow users to choose between compact and detailed summary styles
  - Update CLI to support --ai-summary-compact flag
  - Provide backward compatibility with existing verbose mode
  - Write unit tests for configuration options and CLI flag handling
  - _Requirements: 17.16, 17.17_

- [-] 16. Implement AI-powered commit summaries using OpenAI GPT-4 mini
- [x] 16.1 Create core AI summary data models and configuration
  - Implement AISummary Pydantic model with structured summary fields (what_changed, why_changed, potential_side_effects)
  - Create AISummaryConfig model with OpenAI API settings, token limits, and cost tracking options
  - Add openai_api_key field to ForkliftConfig with optional validation
  - Update CommitDetails model to include optional ai_summary field
  - Write unit tests for all new data models including validation and serialization
  - _Requirements: 17.3, 17.5, 17.9, 17.13_

- [x] 16.2 Implement OpenAI client wrapper with error handling
  - Create OpenAIClient class with async HTTP client for GPT-4 mini API calls
  - Implement API key validation and authentication handling
  - Add rate limiting and retry logic with exponential backoff for API errors
  - Create timeout handling and request cancellation for long-running requests
  - Write unit tests for OpenAI client with mocked API responses and error scenarios
  - _Requirements: 17.5, 17.6, 17.8, 17.14_

- [x] 16.3 Build AI commit summary engine with prompt generation
  - Implement AICommitSummaryEngine class to orchestrate summary generation workflow
  - Create structured prompt generation using the specified template for commit analysis
  - Add diff truncation logic to stay within OpenAI token limits (8000 characters max)
  - Implement batch processing for multiple commits with rate limit management
  - Write unit tests for prompt generation, diff truncation, and batch processing logic
  - _Requirements: 17.2, 17.9, 17.12_

- [x] 16.4 Add comprehensive error handling for AI operations
  - Create OpenAIErrorHandler class for different API error types (authentication, rate limits, timeouts)
  - Implement graceful degradation when AI summary generation fails for individual commits
  - Add detailed error logging with context while protecting API key information
  - Create user-friendly error messages distinguishing between different failure types
  - Write unit tests for error handling scenarios and recovery mechanisms
  - _Requirements: 17.6, 17.7, 17.14_

- [x] 16.5 Enhance show-commits command with AI summary support
  - Add --ai-summary flag to show-commits CLI command
  - Update RepositoryDisplayService to integrate AICommitSummaryEngine
  - Implement AI summary generation workflow within existing commit display logic
  - Add progress indicators for AI summary generation with batch processing status
  - Write integration tests for show-commits command with --ai-summary flag
  - _Requirements: 17.1, 17.4, 17.12_

- [x] 16.6 Implement AI summary display formatting and output
  - Create formatted display for commits with AI summaries using Rich library
  - Add visual separation between original commit data and AI-generated analysis
  - Implement structured display showing what changed, why changed, and potential side effects
  - Add compatibility with existing flags (--disable-cache, --limit) and error handling
  - Write unit tests for AI summary formatting and visual consistency
  - _Requirements: 17.10, 17.11_

- [x] 16.7 Add usage tracking and cost monitoring for AI operations
  - Implement API usage statistics collection (tokens used, requests made, estimated costs)
  - Add cost tracking and reporting for transparency in AI API usage
  - Create configuration options for cost limits and usage monitoring
  - Add logging for AI operations with performance metrics and usage data
  - Write unit tests for usage tracking and cost calculation accuracy
  - _Requirements: 17.13, 17.15_

- [ ] 16.8 Create comprehensive testing suite for AI functionality
  - Write unit tests for all AI summary components with mocked OpenAI responses
  - Create integration tests with real OpenAI API calls (marked as billable tests)
  - Add error scenario testing for API failures, rate limits, and authentication issues
  - Implement performance tests for batch processing and large commit sets
  - Write end-to-end tests for complete AI summary workflow with real repository data
  - _Requirements: 17.1, 17.7, 17.8, 17.14_

- [ ] 16.9 Add AI summary configuration and environment setup
  - Create environment variable validation for OPENAI_API_KEY requirement
  - Add configuration file support for AI summary settings and preferences
  - Implement runtime configuration validation and helpful setup guidance
  - Create documentation for AI summary setup and usage with cost considerations
  - Write tests for configuration loading and environment variable handling
  - _Requirements: 17.5, 17.6_

- [ ] 16.10 Finalize AI summary integration and documentation
  - Update CLI help documentation to include --ai-summary flag and usage examples
  - Create comprehensive README section explaining AI summary functionality and costs
  - Add troubleshooting guide for common AI summary issues and API errors
  - Implement final integration testing with existing forklift commands and workflows
  - Write performance benchmarks and cost analysis for AI summary usage
  - _Requirements: 17.1, 17.11, 17.13, 17.15_
-
 [ ] 17. Fix immediate console formatting issues and implement simple, compatible formatting as default
- [ ] 17.0 Fix current emoji and Unicode display issues (HIGH PRIORITY)
  - Replace all emoji characters (📝, ❓, 🟢, ❔) with simple text labels in commit explanations
  - Fix Unicode table borders that display as literal characters in some terminals
  - Update ExplanationFormatter to use ASCII characters instead of Unicode box drawing
  - Remove special symbols from commit category and impact displays
  - Write unit tests for ASCII-only output formatting
  - _Requirements: 18.1, 18.2, 18.7_

- [ ] 17.1 Replace Rich formatting with simple text-based output
  - Remove emoji and Unicode symbols from all CLI output (replace ❓, 🟢, ❔ with text labels)
  - Replace Rich table formatting with simple ASCII tables using |, -, + characters
  - Convert color-coded status indicators to text prefixes (SUCCESS:, ERROR:, INFO:, WARNING:)
  - Remove complex Rich markup and use simple indentation and spacing for hierarchy
  - Write unit tests for simple formatting output and compatibility
  - _Requirements: 18.1, 18.2, 18.3, 18.4_

- [ ] 17.2 Update commit explanation display to use simple formatting
  - Replace emoji category indicators (❓, 🟢, etc.) with text labels (OTHER, LOW, UNCLEAR, etc.)
  - Convert Rich table displays to simple ASCII tables for commit explanations
  - Remove color coding and use text-based status indicators
  - Implement simple indentation and spacing for visual hierarchy
  - Write unit tests for simple explanation formatting
  - _Requirements: 18.1, 18.7, 18.10_

- [ ] 17.3 Add plain text mode configuration and detection
  - Add --no-color and --plain-text CLI flags to force simple formatting
  - Implement automatic terminal capability detection for fallback to plain text
  - Create configuration options for default formatting mode
  - Add environment variable support for FORKLIFT_PLAIN_TEXT mode
  - Write unit tests for plain text mode activation and detection
  - _Requirements: 18.5, 18.6, 18.11_

- [ ] 17.4 Update progress indicators and status displays
  - Replace Rich progress bars with simple text-based progress (e.g., "Processing 5/10...")
  - Convert status spinners to simple text updates
  - Remove complex visual elements and use clear text descriptions
  - Maintain information hierarchy using indentation and spacing
  - Write unit tests for simple progress display formatting
  - _Requirements: 18.8, 18.10, 18.11_

- [ ] 17.5 Finalize simple formatting integration and testing
  - Ensure all CLI commands use simple formatting by default
  - Test compatibility across different terminal environments
  - Validate that all information remains accessible in plain text mode
  - Create comprehensive integration tests for simple formatting
  - Update documentation to reflect simple formatting as default
  - _Requirements: 18.1, 18.11, 18.12_

- [ ] 18. Enhance show-forks display with improved sorting and simplified columns
- [x] 18.1 Implement enhanced fork sorting logic
  - Create _sort_forks_enhanced method in RepositoryDisplayService with commits-first sorting
  - Implement multi-level sorting: commits status (has commits first), forks count desc, stars desc, last push desc
  - Update fork data collection to support enhanced sorting criteria
  - Write unit tests for enhanced sorting logic with various fork combinations
  - _Requirements: 21.1_

- [-] 18.2 Simplify fork data table columns
  - Remove "#", "Size (KB)", and "Language" columns from Detailed Fork Information table
  - Add "URL" column containing clickable GitHub URLs for each fork repository
  - Update _display_enhanced_fork_data_table method to use simplified column structure
  - Implement _format_fork_url method to generate proper GitHub URLs
  - Write unit tests for simplified table display and column validation
  - _Requirements: 21.2, 21.3_

- [x] 18.3 Update commits ahead display format
  - Change "Commits Status" header to "Commits Ahead" in fork data table
  - Implement _format_commits_ahead_simple method to show "Yes"/"No" instead of technical terms
  - Update commits ahead status formatting throughout the display system
  - Write unit tests for simplified commits ahead display format
  - _Requirements: 21.4_

- [ ] 18.4 Remove redundant display sections
  - Remove "Language Distribution" table from fork data display
  - Remove "Fork Insights" section that duplicates Collection Summary information
  - Update _display_fork_data_table method to exclude redundant sections
  - Add configuration flags _should_exclude_language_distribution and _should_exclude_fork_insights
  - Write unit tests for streamlined display without redundant sections
  - _Requirements: 21.5, 21.6_

- [ ] 18.5 Update CLI integration for enhanced show-forks display
  - Modify show-forks CLI command to use enhanced display methods
  - Update command help text to reflect new sorting and display behavior
  - Ensure backward compatibility with existing show-forks functionality
  - Write integration tests for enhanced show-forks command with real repository data
  - _Requirements: 21.1, 21.2, 21.3, 21.4, 21.5, 21.6_

- [ ] 18.6 Add comprehensive testing for enhanced show-forks functionality
  - Write unit tests for all enhanced display methods and sorting logic
  - Create integration tests using test repositories to validate enhanced display
  - Add performance tests for enhanced sorting with large fork datasets
  - Test enhanced display with various fork data scenarios and edge cases
  - Write regression tests to ensure existing functionality remains intact
  - _Requirements: 21.1, 21.2, 21.3, 21.4, 21.5, 21.6_

- [ ] 19. Implement show-forks --detail functionality with commits ahead API calls
- [x] 19.1 Add --detail flag to show-forks CLI command
  - Add --detail click option to show-forks command in src/forklift/cli.py
  - Update _show_forks_summary function to accept and pass detail parameter
  - Modify command help text to document --detail flag functionality
  - Add parameter validation and error handling for detail mode
  - Write unit tests for CLI command parameter handling with --detail flag
  - _Requirements: 21.1, 21.7, 21.10_

- [ ] 19.2 Implement commits ahead API calls for detailed mode
  - Create get_commits_ahead method in GitHubClient using GitHub's compare API endpoint
  - Add error handling for compare API failures (repository access, branch differences)
  - Implement rate limiting and backoff strategies for additional API calls
  - Add progress indicators for commits ahead API requests
  - Write unit tests for commits ahead API calls with various repository scenarios
  - _Requirements: 21.4, 21.6, 21.8, 21.9, 21.12_

- [ ] 19.3 Create detailed fork display table with reduced columns
  - Implement _display_detailed_fork_table method in RepositoryDisplayService
  - Create table with URL as first column, followed by Stars, Forks, Commits Ahead, Last Push
  - Remove Fork Name, Owner, Activity, and Status columns from detailed display
  - Add exact numeric commit counts display (e.g., "5 commits ahead")
  - Write unit tests for detailed table formatting and column structure
  - _Requirements: 21.2, 21.3, 21.5, 21.11_

- [ ] 19.4 Integrate detailed mode with existing fork data collection
  - Update show_fork_data method to support detail parameter
  - Add commits ahead fetching logic when detail mode is enabled
  - Implement fallback to "Unknown" when commits ahead cannot be determined
  - Add detailed mode statistics and API call tracking
  - Write unit tests for integration between detail mode and fork data collection
  - _Requirements: 21.1, 21.7, 21.8, 21.12_

- [x] 19.5 Optimize show-forks --detail to skip API calls for forks with no commits ahead (HIGH PRIORITY)
  - Update show_fork_data_detailed method to use smart fork filtering based on commits_ahead_status
  - Skip compare API calls for forks already identified as "No commits ahead" using created_at >= pushed_at logic
  - Set exact_commits_ahead = 0 for skipped forks instead of making unnecessary API calls
  - Add filtering logic to only make compare API calls for forks with "Has commits" status
  - Update progress tracking to reflect actual API calls made vs skipped
  - Add logging to show API call savings (e.g., "Skipped 2 forks with no commits ahead, saved 2 API calls")
  - Write unit tests for optimized filtering logic covering various fork scenarios
  - Write integration tests to verify API call reduction with real repository data
  - _Requirements: 1.6, 21.1, 21.4, 21.5_

- [ ] 20. Implement compact commit status display in fork tables
- [ ] 20.1 Update fork display table structure for compact commit format
  - Modify RepositoryDisplayService to combine commits ahead/behind into single "Commits" column
  - Update table column definitions to replace "Commits Ahead" and "Commits Behind" with single "Commits" column
  - Implement format_commits_status method to generate "+X -Y" format strings
  - Update table width calculations to accommodate the new compact format
  - Write unit tests for commit status formatting with various ahead/behind combinations
  - _Requirements: 22.1, 22.2, 22.8_

- [ ] 20.2 Implement commit status formatting logic
  - Create format_commits_compact method that takes commits_ahead and commits_behind parameters
  - Handle edge cases: empty cell (0 ahead, 0 behind), +X (only ahead), -Y (only behind)
  - Add "Unknown" handling for cases where commit status cannot be determined
  - Implement color coding: green for positive ahead values, red for positive behind values
  - Write comprehensive unit tests for all formatting scenarios and edge cases
  - _Requirements: 22.2, 22.3, 22.4, 22.5, 22.6, 22.7_

- [ ] 20.3 Update all fork display commands with compact format
  - Update show-forks command to use new compact commit format
  - Update list-forks command to use consistent commit formatting
  - Update show-fork-data-detailed command to use compact format
  - Ensure consistent formatting across all fork-related display functions
  - Update any fork preview or summary displays to use the new format
  - Write integration tests to verify consistent formatting across all commands
  - _Requirements: 22.11, 22.10_

- [ ] 20.4 Implement sorting logic for compact commit format
  - Update fork sorting logic to handle the new compact commit format
  - Implement primary sort by commits ahead, secondary sort by commits behind
  - Update sort_by="commits" option to work with the new format
  - Handle sorting of "Unknown" commit status entries
  - Add sorting tests for various commit status combinations
  - Write unit tests for sorting logic with the new compact format
  - _Requirements: 22.9, 22.10_

- [ ] 20.5 Update documentation and help text for new format
  - Update CLI help text to describe the new "+X -Y" commit format
  - Update any inline documentation that references the old column structure
  - Add examples of the new format to user documentation
  - Update error messages or user guidance that mentions commit columns
  - Write documentation tests to verify help text accuracy
  - _Requirements: 22.12_

- [ ] 20.6 Add comprehensive testing for compact commit display
  - Write integration tests for the complete fork display workflow with new format
  - Test edge cases: repos with no forks, forks with various commit statuses
  - Test performance impact of the formatting changes
  - Write visual regression tests to ensure table formatting remains readable
  - Test compatibility with existing fork analysis and filtering functionality
  - Write end-to-end tests covering all fork display commands with new format
  - _Requirements: 22.10, 22.8, 22.11_

- [-] 21. Implement --show-commits feature for show-forks command
- [x] 21.1 Add --show-commits CLI option and parameter handling
  - Add --show-commits=N option to show-forks command with integer validation
  - Update CLI argument parsing to handle the new parameter
  - Set default value to 0 (no commits shown) when option not specified
  - Add parameter validation to ensure N is between 0 and reasonable limit (e.g., 10)
  - Update command help text to document the new --show-commits option
  - Write unit tests for CLI parameter parsing and validation
  - _Requirements: 23.1, 23.4_

- [x] 21.2 Implement recent commits fetching functionality
  - Create get_recent_commits method in GitHubClient to fetch last N commits from fork's default branch
  - Add commit data models for storing short SHA and commit message
  - Implement commit message truncation logic (50 characters with "..." indicator)
  - Add error handling for cases where commits cannot be fetched
  - Write unit tests for commit fetching with various scenarios (normal, empty repo, API errors)
  - _Requirements: 23.2, 23.5, 23.6, 23.7, 23.8_

- [x] 21.3 Update fork display table structure for recent commits column
  - Modify RepositoryDisplayService to conditionally add "Recent Commits" column when --show-commits > 0
  - Implement format_recent_commits method to format commits with each commit on a separate line
  - Update table width calculations to accommodate the new variable-width column
  - Add logic to adjust column widths based on content length
  - Write unit tests for table structure changes and commit formatting
  - _Requirements: 23.3, 23.11_

- [-] 21.4 Integrate recent commits fetching with fork display workflow
  - Update show_fork_data method to fetch recent commits when --show-commits is specified
  - Add concurrent fetching of commits for multiple forks to improve performance
  - Implement progress indicators showing commit fetching status for each fork
  - Add rate limiting awareness to prevent API quota exhaustion
  - Handle cases where some forks fail to fetch commits while others succeed
  - Write integration tests for the complete workflow with real GitHub API calls
  - _Requirements: 23.9, 23.10, 23.12_

- [ ] 21.5 Add comprehensive error handling and edge cases
  - Handle forks with no commits (empty repositories)
  - Handle private forks where commits cannot be accessed
  - Implement graceful degradation when API rate limits are hit
  - Add timeout handling for slow commit fetching operations
  - Display appropriate messages for different error scenarios
  - Write unit tests for all error conditions and edge cases
  - _Requirements: 23.6, 23.8, 23.9_

- [ ] 21.6 Add comprehensive testing and documentation
  - Write integration tests for --show-commits with various N values
  - Test performance impact of fetching commits for large numbers of forks
  - Add tests for combination with other flags (--max-forks, --exclude-archived, etc.)
  - Update CLI help documentation and user guides
  - Write end-to-end tests covering the complete show-forks workflow with commits
  - Test table formatting and readability with various commit message lengths
  - _Requirements: 23.10, 23.11, 23.12_

- [ ] 19.6 Add comprehensive testing for show-forks --detail functionality
  - Write integration tests for show-forks --detail with real repository data
  - Create tests for commits ahead API calls with various fork scenarios
  - Add tests for detailed table display and column formatting
  - Test error handling when commits ahead cannot be fetched
  - Write performance tests for additional API calls impact
  - _Requirements: 21.1, 21.4, 21.6, 21.8, 21.9, 21.11, 21.12_

- [ ] 20. Implement smart fork filtering for --detail flag using qualification data
- [x] 20.1 Create fork commit status detection system
  - Implement ForkCommitStatusChecker class to determine if forks have commits ahead using qualification data
  - Add has_commits_ahead method using created_at >= pushed_at comparison logic
  - Create fallback mechanism to GitHub API when qualification data is unavailable
  - Add logging and statistics tracking for fork filtering decisions
  - Write unit tests for commit status detection with various fork scenarios
  - _Requirements: 21.1, 21.2, 21.3, 21.5_

- [ ] 20.2 Enhance show-commits command with smart fork filtering
  - Add pre-analysis check in show-commits command to detect forks with no commits ahead
  - Implement graceful exit with clear messaging when fork has no commits ahead
  - Add --force flag to override no-commits-ahead filtering when needed
  - Update command help text to document the automatic filtering behavior
  - Write unit tests for show-commits command with fork filtering logic
  - _Requirements: 21.1, 21.2, 21.4, 21.10_

- [x] 20.3 Integrate fork filtering with existing --detail functionality
  - Update detailed commit analysis workflow to check fork status before expensive operations
  - Ensure fork filtering is applied before AI summary generation and diff retrieval
  - Add fork filtering support to batch operations and multiple fork processing
  - Implement proper error handling when fork status cannot be determined
  - Write integration tests for --detail flag with fork filtering enabled
  - _Requirements: 21.4, 21.6, 21.7, 21.9_

- [x] 20.4 Add fork filtering configuration and logging
  - Create ForkFilteringConfig model with settings for filtering behavior
  - Add configuration options for enabling/disabling automatic fork filtering
  - Implement detailed logging for fork filtering decisions with fork names and reasons
  - Add statistics collection for filtered vs analyzed forks
  - Write unit tests for fork filtering configuration and logging
  - _Requirements: 21.8, 21.9_

- [ ] 20.5 Implement fork qualification data integration
  - Update show-commits command to use existing fork qualification data when available
  - Add qualification data lookup methods to avoid redundant API calls
  - Implement data freshness checks to ensure qualification data is current
  - Add fallback logic for missing or stale qualification data
  - Write unit tests for qualification data integration and fallback scenarios
  - _Requirements: 21.3, 21.5, 21.9_

- [x] 20.6 Add comprehensive testing for smart fork filtering
  - Write integration tests for fork filtering with real GitHub repositories
  - Create tests for --detail flag with various fork commit status scenarios
  - Add performance tests to verify filtering reduces unnecessary API calls
  - Implement error handling tests for edge cases and API failures
  - Write end-to-end tests for complete fork filtering workflow
  - _Requirements: 21.1, 21.2, 21.4, 21.6, 21.7, 21.10_