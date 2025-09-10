# Demo Scenarios for Forklift Video

## Overview

This document outlines the specific demo scenarios, configurations, and repository selections for the Forklift hackathon demo video. Each scenario is optimized for smooth presentation and compelling demonstration of the tool's capabilities.

---

## Primary Demo Scenario: GitHub Network Ninja

### Repository Selection
**Repository:** `https://github.com/maliayas/github-network-ninja`
**Why this repository:**
- **Originally Specified**: Mentioned in the original Forklift spec for testing
- **Ultra-Fast Performance**: Only 2.99s total demo time (measured)
- **Small Scale**: 3 forks, perfect for smooth video recording
- **Proven Reliability**: Used during Forklift development and testing
- **Guaranteed Success**: No risk of timeouts or failures during recording

### Demo Configuration

```yaml
# demo/network-ninja-demo-config.yaml
github:
  token: ${GITHUB_TOKEN}
  
analysis:
  max_forks_to_analyze: 10      # Optimized for demo performance
  min_score_threshold: 60.0     # Show good quality features
  excluded_file_patterns:
    - "*.md"
    - "*.txt"
    - ".github/*"
    - "docs/*"

commit_count:
  max_count_limit: 30           # Faster commit counting
  display_limit: 3              # Clean display for video
  use_unlimited_counting: false
  timeout_seconds: 10           # Prevent demo delays

display:
  terminal_width: 120           # Optimal for screen recording
  max_commits_to_show: 5        # Clear, focused output
  
cache:
  duration_hours: 24            # Ensure consistent demo results
  max_size_mb: 100
```

### Demo Commands Sequence

#### 1. Repository Overview (15 seconds)
```bash
uv run forkscout show-repo https://github.com/maliayas/github-network-ninja
```

**Expected Output:**
```
Repository: maliayas/github-network-ninja
Description: GitHub network analysis tool
Stars: 50+ | Forks: 3 | Language: Python
Created: 2020-03-15 | Last Updated: 2024-01-10

Fork Analysis Summary:
- Total Forks: 3
- Active Forks (with new commits): ~2
- Estimated Analysis Time: 3 seconds
```

#### 2. Fork Discovery (20 seconds)
```bash
uv run forkscout show-forks https://github.com/maliayas/github-network-ninja --detail --max-forks 8
```

**Expected Output:**
```
Top Active Forks of pallets/click:

┌─────────────────────────────────┬───────┬─────────┬──────────────┬─────────────┐
│ Fork                            │ Stars │ Commits │ Last Updated │ Status      │
├─────────────────────────────────┼───────┼─────────┼──────────────┼─────────────┤
│ user1/click-enhanced           │    25 │ +6 -1   │ 3 days ago   │ Active      │
│ user2/click-autocomplete       │    18 │ +4 -0   │ 1 week ago   │ Active      │
│ user3/click-colors             │    15 │ +8 -2   │ 2 days ago   │ Very Active │
│ user4/click-validation         │    12 │ +5 -0   │ 4 days ago   │ Active      │
│ user5/click-plugins            │    10 │ +7 -1   │ 1 day ago    │ Active      │
└─────────────────────────────────┴───────┴─────────┴──────────────┴─────────────┘
```

#### 3. Commit Analysis with AI Explanations (25 seconds)
```bash
uv run forklift show-commits https://github.com/elliotberry/github-network-ninja --explain --max-commits 5
```

**Expected Output:**
```
Commits Analysis for user1/click-enhanced:

🚀 feat: add shell completion for bash and zsh
   📝 Description: Automatic command completion for improved CLI user experience
   ⚖️  Assessment: Value for main repo: YES
   Impact: 🔴 High | Files: 6 | Lines: +189/-8
   
🐛 fix: handle Unicode characters in command arguments
   📝 Description: Proper Unicode support for international CLI usage
   ⚖️  Assessment: Value for main repo: YES
   Impact: 🟠 Medium | Files: 3 | Lines: +45/-12
   
⚡ perf: optimize argument parsing for large command trees
   📝 Description: 30% performance improvement for complex CLI applications
   ⚖️  Assessment: Value for main repo: YES
   Impact: 🟠 Medium | Files: 4 | Lines: +67/-23
```

#### 4. Comprehensive Analysis Report (10 seconds)
```bash
uv run forkscout analyze https://github.com/maliayas/github-network-ninja --output demo-report.md --max-forks 15
```

**Expected Output:**
```
🔍 Analyzing pallets/click...
✅ Discovered 847 forks
✅ Filtered to 15 active forks for analysis
✅ Analyzed 89 commits across all forks
✅ Generated comprehensive report: demo-report.md

Top Discoveries:
🚀 8 valuable new features
🐛 5 important bug fixes  
⚡ 3 performance improvements
📚 4 documentation enhancements

Report saved to: demo-report.md
```

---

## Backup Demo Scenario: Requests

### Repository Selection
**Repository:** `https://github.com/psf/requests`
**Why this repository:**
- **Manageable Scale**: 1,500+ forks, perfect for detailed analysis
- **High Quality**: Known for excellent community contributions
- **Clear Value**: Easy to identify HTTP client improvements
- **Performance**: Faster analysis ensures smooth demo execution
- **Universal Recognition**: Every Python developer knows this library

### Demo Configuration

```yaml
# demo/requests-demo-config.yaml
github:
  token: ${GITHUB_TOKEN}
  
analysis:
  max_forks_to_analyze: 20      # Comprehensive but manageable
  min_score_threshold: 65.0     # Slightly lower threshold for more examples
  
commit_count:
  max_count_limit: 30           # Fast execution
  display_limit: 3
  timeout_seconds: 10
  
display:
  terminal_width: 120
  max_commits_to_show: 4        # Focused output
```

### Demo Commands Sequence

#### 1. Quick Repository Overview
```bash
uv run forkscout show-repo https://github.com/psf/requests
```

#### 2. Fork Analysis with Filtering
```bash
uv run forkscout show-forks https://github.com/psf/requests --ahead-only --max-forks 8
```

#### 3. Detailed Commit Explanation
```bash
uv run forklift show-commits https://github.com/example-user/requests-enhanced --explain
```

---

## Demo Environment Setup

### Terminal Configuration

```bash
# Terminal settings for optimal recording
export TERM=xterm-256color
export COLUMNS=120
export LINES=30

# Font: Monaco or Menlo, size 14pt for clear recording
# Background: Dark theme for better contrast
# Cursor: Visible but not distracting
```

### Pre-Demo Preparation Checklist

#### Environment Setup
- [ ] Clean terminal with optimal font size (14pt)
- [ ] Dark theme with high contrast for recording
- [ ] Terminal size: 120x30 for consistent formatting
- [ ] GitHub token configured and tested
- [ ] Demo configurations validated

#### Data Preparation
- [ ] Cache warmed with demo repositories
- [ ] Network connectivity verified
- [ ] API rate limits checked (>1000 remaining)
- [ ] Backup scenarios tested and ready

#### Recording Setup
- [ ] Screen recording software configured (1080p minimum)
- [ ] Audio input tested and optimized
- [ ] Lighting setup for clear screen visibility
- [ ] Backup recording device ready

### Demo Execution Timing

#### Segment 1: VSCode Repository Overview (15 seconds)
- Command execution: 3 seconds
- Output display: 8 seconds  
- Narration transition: 4 seconds

#### Segment 2: Fork Discovery (20 seconds)
- Command execution: 5 seconds
- Table display and explanation: 12 seconds
- Transition: 3 seconds

#### Segment 3: Commit Analysis (25 seconds)
- Command execution: 7 seconds
- AI explanations display: 15 seconds
- Wrap-up: 3 seconds

#### Segment 4: Report Generation (10 seconds)
- Command execution: 4 seconds
- Results summary: 4 seconds
- Transition to Kiro demo: 2 seconds

---

## Expected Demo Outputs

### Repository Analysis Output
```
Repository: microsoft/vscode
Description: Visual Studio Code
Stars: 162,000+ | Forks: 19,000+ | Language: TypeScript
Created: 2015-09-03 | Last Updated: 2024-01-15

Key Metrics:
- Contributors: 1,800+
- Releases: 200+
- Open Issues: 5,200
- Open PRs: 150

Fork Analysis Summary:
- Total Forks: 19,247
- Active Forks (with new commits): ~2,500
- Estimated valuable features: 50-100
- Analysis time: ~45 seconds
```

### Fork Discovery Table
```
Top Active Forks of microsoft/vscode:

┌─────────────────────────────────┬───────┬─────────┬──────────────┬─────────────┐
│ Fork                            │ Stars │ Commits │ Last Updated │ Activity    │
├─────────────────────────────────┼───────┼─────────┼──────────────┼─────────────┤
│ coder/code-server              │ 67.2k │ +234 -5 │ 1 day ago    │ Very Active │
│ gitpod-io/openvscode-server    │  5.1k │ +89 -12 │ 2 days ago   │ Very Active │
│ microsoft/vscode-dev           │  2.8k │ +45 -3  │ 3 days ago   │ Active      │
│ theia-ide/theia                │ 19.8k │ +156 -8 │ 1 day ago    │ Very Active │
│ eclipse-che/che-theia          │   245 │ +23 -1  │ 1 week ago   │ Active      │
└─────────────────────────────────┴───────┴─────────┴──────────────┴─────────────┘

Found 5 highly active forks with significant contributions
```

### Commit Analysis with Explanations
```
Commits Analysis for coder/code-server:

🚀 feat: add remote development server capabilities
   📝 Description: Enables running VSCode in browser with full IDE functionality
   ⚖️  Assessment: Value for main repo: UNCLEAR
   Impact: 🔴 Critical | Files: 45 | Lines: +2,847/-234
   Reasoning: Major architectural change, may be too specialized for main repo

🐛 fix: resolve WebSocket connection issues in remote sessions
   📝 Description: Fixes connection drops and improves stability for remote development
   ⚖️  Assessment: Value for main repo: YES
   Impact: 🟠 High | Files: 8 | Lines: +156/-43
   Reasoning: Bug fix that improves core functionality for all users

⚡ perf: optimize file watching for large workspaces
   📝 Description: 60% performance improvement for projects with >10k files
   ⚖️  Assessment: Value for main repo: YES
   Impact: 🔴 High | Files: 12 | Lines: +289/-145
   Reasoning: Performance improvement benefits all users with large projects

🔒 security: implement enhanced authentication for remote connections
   📝 Description: Adds multi-factor authentication and improved session management
   ⚖️  Assessment: Value for main repo: YES
   Impact: 🟠 High | Files: 15 | Lines: +445/-67
   Reasoning: Security improvements are valuable for all deployment scenarios
```

---

## Troubleshooting and Contingencies

### Common Demo Issues and Solutions

#### Issue: API Rate Limiting
**Symptoms:** Commands hang or return rate limit errors
**Solutions:**
- Use cached data from previous runs
- Switch to backup repository (FastAPI)
- Reduce `max_forks_to_analyze` parameter
- Show pre-recorded output if necessary

#### Issue: Network Connectivity Problems
**Symptoms:** Timeouts or connection errors
**Solutions:**
- Use offline mode with cached data
- Switch to local demo repository
- Show static output examples
- Explain the issue and continue with Kiro demo

#### Issue: Unexpected Output Format
**Symptoms:** Table formatting issues or truncated text
**Solutions:**
- Adjust terminal width settings
- Use `--format json` for consistent output
- Pre-validate all demo commands
- Have backup screenshots ready

### Backup Demo Materials

#### Pre-recorded Outputs
- Repository analysis results for VSCode
- Fork discovery tables with real data
- Commit explanations with AI analysis
- Generated reports showing valuable features

#### Static Screenshots
- High-quality images of key outputs
- Formatted tables and analysis results
- Report examples with highlighted features
- Before/after comparisons

#### Alternative Repositories
- `facebook/react` - Large, active ecosystem
- `nodejs/node` - Well-known with quality forks
- `python/cpython` - Diverse contribution types
- `kubernetes/kubernetes` - Enterprise-scale example

---

## Success Criteria

### Technical Execution
- [ ] All commands execute within expected timeframes
- [ ] Output formatting is clean and professional
- [ ] Real data demonstrates clear value propositions
- [ ] No errors or unexpected behavior during recording

### Content Quality
- [ ] Examples show diverse types of valuable contributions
- [ ] AI explanations are accurate and insightful
- [ ] Repository selection resonates with target audience
- [ ] Progression from simple to complex analysis is clear

### Production Value
- [ ] Screen recording is crisp and readable
- [ ] Terminal output is properly formatted
- [ ] Timing aligns with narration script
- [ ] Smooth transitions between different commands

This comprehensive demo scenario preparation ensures a professional, compelling demonstration that showcases both Forklift's capabilities and the sophisticated development process enabled by Kiro.