# Implementation Plan

- [ ] 1. Enhance TerminalDetector with output redirection detection
  - Add `is_output_redirected()` method to detect when stdout is redirected to a file
  - Use `sys.stdout.isatty()` to determine if output is going to a terminal or file
  - _Requirements: 1.1, 2.1_

- [ ] 2. Modify Recent Commits column width calculation for file output
  - Update the width calculation method to check for output redirection
  - Set maximum width to 1000 characters when output is redirected to a file
  - Maintain existing terminal width logic for terminal output
  - _Requirements: 1.2, 1.3, 2.2_

- [ ] 3. Add integration tests for output redirection behavior
  - Test that Recent Commits column uses 1000 character width for file output
  - Test that terminal output behavior remains unchanged
  - Test with various commit message lengths to ensure no truncation
  - _Requirements: 1.4, 2.3, 3.1_