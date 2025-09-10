# Implementation Plan

## Overview

This implementation plan focuses on enhancing the existing circuit breaker and rate limiting system to handle large repositories (>2000 forks) without rebuilding the comprehensive rate limiting that already exists. The tasks are designed to work with the existing `RateLimitHandler`, `CircuitBreaker`, and `GitHubClient` implementations.

## Tasks

- [x] 1. Enhance Circuit Breaker for Large Repositories
  - Modify existing `CircuitBreaker` class to support failure type classification
  - Add repository size awareness to adjust failure thresholds dynamically
  - Implement weighted failure counting where rate limits don't count toward circuit opening
  - Add configuration options for different repository sizes (small: 5 failures, large: 25+ failures)
  - _Requirements: 1.1, 1.3, 1.4_

- [x] 1.1 Add Failure Type Classification
  - Create `FailureType` enum to categorize different types of failures
  - Implement `classify_failure()` method to identify rate limits, network errors, repository access issues
  - Add failure type weights where rate limits have 0.0 weight (don't count toward circuit breaker)
  - Update circuit breaker to use weighted failure counting instead of simple counting
  - _Requirements: 1.1, 1.3_

- [x] 1.2 Implement Repository Size Detection
  - Create `RepositorySizeDetector` class to automatically detect fork count from repository URL
  - Add method to get recommended circuit breaker configuration based on repository size
  - Implement size-based thresholds: <500 forks (standard), 500-1000 (moderate), 1000-2000 (high), >2000 (very high tolerance)
  - Add logging to show detected repository size and applied configuration
  - _Requirements: 1.1, 1.2, 5.2_

- [x] 1.3 Add Graceful Degradation When Circuit Opens
  - Create `GracefulDegradationHandler` to continue processing when circuit breaker opens
  - Implement retry logic that attempts individual fork processing every 30 seconds when circuit is open
  - Add option to skip consistently failing forks instead of stopping entire operation
  - Provide detailed logging about circuit breaker state and recovery attempts
  - _Requirements: 1.2, 4.4_

- [x] 2. Integrate Enhanced Circuit Breaker with Existing GitHub Client
  - Modify `GitHubClient` constructor to accept enhanced circuit breaker configuration
  - Update client initialization to detect repository size and configure circuit breaker appropriately
  - Ensure backward compatibility with existing circuit breaker usage
  - Add factory method to create repository-size-aware GitHub clients
  - _Requirements: 1.1, 1.2, 5.1_

- [x] 2.1 Update GitHub Client Integration
  - Modify existing `GitHubClient.__init__()` to accept `EnhancedCircuitBreaker` instances
  - Add `create_resilient_client()` factory method that auto-detects repository size
  - Ensure existing rate limiting and error handling continue to work unchanged
  - Update circuit breaker call sites to pass failure type information
  - _Requirements: 1.1, 1.2_

- [x] 2.2 Add Repository URL Detection to Analysis Commands
  - Update `show-forks` command to detect repository size before starting analysis
  - Pass repository URL to GitHub client factory for automatic configuration
  - Add logging to show detected configuration being applied
  - Ensure graceful fallback if repository size detection fails
  - _Requirements: 1.1, 5.2_

- [x] 3. Add Command-Line Configuration Options
  - Add `--circuit-breaker-threshold` option to override automatic threshold detection
  - Add `--continue-on-circuit-open` flag to control graceful degradation behavior
  - Add `--skip-failed-forks` flag to control whether to skip or retry failed forks
  - Add `--circuit-open-retry-interval` option to configure retry timing
  - _Requirements: 5.1, 5.3, 5.4_

- [x] 3.1 Implement CLI Resilience Options
  - Add resilience argument group to CLI parser with clear help text
  - Implement option validation and default value handling
  - Pass configuration options to enhanced circuit breaker creation
  - Add verbose logging option to show circuit breaker state changes and retry attempts
  - _Requirements: 5.1, 5.3, 5.4_

- [ ] 4. Add Comprehensive Testing for Large Repository Scenarios
  - Create integration tests that simulate large repository analysis with circuit breaker failures
  - Add tests for failure type classification and weighted counting
  - Test graceful degradation behavior when circuit breaker opens
  - Create performance tests to ensure enhanced circuit breaker doesn't impact normal operations
  - _Requirements: All requirements_

- [ ] 4.1 Create Circuit Breaker Enhancement Tests
  - Test failure type classification for different exception types (rate limits, network errors, API errors)
  - Test weighted failure counting where rate limits don't contribute to circuit opening
  - Test repository size detection and automatic threshold adjustment
  - Test backward compatibility with existing circuit breaker usage
  - _Requirements: 1.1, 1.3, 1.4_

- [ ] 4.2 Create Large Repository Integration Tests
  - Test complete analysis workflow with simulated large repository (>2000 forks)
  - Test graceful degradation when circuit breaker opens during large analysis
  - Test individual fork retry logic when circuit is open
  - Test that successful forks continue processing while failed forks are retried
  - _Requirements: 1.2, 4.4_

- [ ] 4.3 Create Performance and Regression Tests
  - Test that enhanced circuit breaker doesn't slow down normal repository analysis
  - Test memory usage remains reasonable during large repository processing
  - Test that existing rate limiting behavior is unchanged
  - Create regression tests to ensure existing functionality continues working
  - _Requirements: All requirements_

- [ ] 5. Documentation and User Guidance
  - Update CLI help text to explain resilience options for large repositories
  - Add troubleshooting guide for circuit breaker issues
  - Document recommended settings for different repository sizes
  - Create examples showing how to analyze very large repositories effectively
  - _Requirements: 4.4, 5.4_

- [ ] 5.1 Create User Documentation
  - Document new command-line options with examples for large repository analysis
  - Create troubleshooting section explaining circuit breaker behavior and recovery
  - Add examples of analyzing popular repositories with thousands of forks
  - Document how to interpret circuit breaker logs and recovery messages
  - _Requirements: 4.4, 5.4_

## Implementation Notes

### Key Principles

1. **Preserve Existing Functionality**: All existing rate limiting, retry logic, and error handling must continue working unchanged
2. **Backward Compatibility**: Existing code using `GitHubClient` should work without modifications
3. **Minimal Changes**: Focus on enhancing the circuit breaker rather than rebuilding the entire system
4. **Graceful Degradation**: When circuit opens, continue processing successful forks rather than stopping completely

### Integration Points

1. **CircuitBreaker Class**: Enhance existing class in `src/forkscout/github/rate_limiter.py`
2. **GitHubClient Class**: Modify constructor in `src/forkscout/github/client.py` to accept enhanced circuit breaker
3. **CLI Commands**: Update `src/forkscout/cli.py` to add resilience options and use repository-size-aware client creation
4. **Existing Rate Limiting**: Preserve all existing `RateLimitHandler` functionality unchanged

### Testing Strategy

1. **Unit Tests**: Test individual components (failure classification, size detection, graceful degradation)
2. **Integration Tests**: Test complete workflow with simulated large repositories
3. **Performance Tests**: Ensure no regression in normal repository analysis performance
4. **Contract Tests**: Verify backward compatibility with existing circuit breaker usage

This implementation plan addresses the specific issue of circuit breaker opening during large repository analysis while preserving all existing rate limiting and error handling functionality.