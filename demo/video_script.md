# Forklift Demo Video Script
## "From Idea to Production: Building with Kiro"

**Duration:** 3 minutes (180 seconds)
**Target Audience:** Hackathon judges evaluating both the tool and Kiro usage
**Format:** Screen recording with narration

---

## Script Structure

### Opening Hook (0:00 - 0:20) - 20 seconds

**[Screen: GitHub repository with many forks]**

**Narrator:** "Imagine you maintain a popular open source project with hundreds of forks. Hidden in those forks are valuable features, bug fixes, and improvements that could benefit everyone. But manually reviewing hundreds of repositories? That's impossible."

**[Screen: Terminal showing `uv run forkscout analyze` command starting]**

**Narrator:** "Meet Forklift - an AI-powered tool that automatically discovers and ranks valuable features across all forks of your repository."

---

### Problem → Solution (0:20 - 0:50) - 30 seconds

**[Screen: Split view - messy fork landscape vs clean Forklift analysis]**

**Narrator:** "The problem is real. Even small repositories can have dozens of forks with valuable improvements, but there's no efficient way to discover them."

**[Screen: Forklift command running]**

```bash
uv run forkscout analyze https://github.com/maliayas/github-network-ninja --explain
```

**Narrator:** "Forklift solves this by automatically scanning all forks, analyzing commits with AI, and ranking features by their potential value to the main repository."

**[Screen: Results showing categorized commits with explanations]**

**Narrator:** "In seconds, you see exactly what each fork contributes - new features, bug fixes, performance improvements - all ranked and explained."

---

### Tool Demonstration (0:50 - 1:40) - 50 seconds

**[Screen: Terminal showing step-by-step analysis]**

**Narrator:** "Let's see Forklift in action. We'll analyze a real repository with multiple forks."

**[Screen: Command execution]**

```bash
uv run forkscout show-repo https://github.com/maliayas/github-network-ninja
```

**[Screen: Repository overview with statistics]**

**Narrator:** "First, we get an overview - a small but active repository with meaningful forks that demonstrate Forklift's analysis capabilities."

**[Screen: Fork discovery]**

```bash
uv run forkscout show-forks https://github.com/maliayas/github-network-ninja --detail
```

**[Screen: Table showing forks with commit counts and activity]**

**Narrator:** "The fork analysis shows which repositories have new commits, how many commits ahead they are, and their activity levels."

**[Screen: Commit analysis with AI explanations]**

```bash
uv run forklift show-commits https://github.com/elliotberry/github-network-ninja --explain
```

**[Screen: Detailed commit explanations with categories and impact assessment]**

**Narrator:** "For each interesting fork, Forklift analyzes individual commits. AI categorizes them - features, bug fixes, performance improvements - and assesses their value for the main repository."

**[Screen: Generated report]**

```bash
uv run forkscout analyze https://github.com/maliayas/github-network-ninja --output report.md
```

**[Screen: Markdown report with ranked features]**

**Narrator:** "Finally, generate comprehensive reports ranking the most valuable features across all forks, ready for maintainer review."

---

### Kiro Development Showcase (1:40 - 2:40) - 60 seconds

**[Screen: Kiro interface showing spec creation]**

**Narrator:** "But here's what makes this project special - it was built entirely using Kiro's spec-driven development. Let me show you how."

**[Screen: Requirements document]**

**Narrator:** "We started with user stories and acceptance criteria. Kiro helped refine vague requirements like 'analyze forks' into specific, testable criteria with 22 detailed requirements."

**[Screen: Design document with architecture diagrams]**

**Narrator:** "Kiro then guided the design phase, helping choose between architectural options. For example, replacing a complex custom caching system with HTTP-level caching - reducing 1,150 lines of code to just 30."

**[Screen: Task breakdown in tasks.md]**

**Narrator:** "The implementation used 16 different specs, each broken down into focused tasks. Every task references specific requirements and includes comprehensive tests."

**[Screen: Code showing TDD implementation]**

**Narrator:** "Kiro enforced test-driven development through steering rules. Every feature was built with tests first, achieving over 90% test coverage."

**[Screen: Spec evolution timeline]**

**Narrator:** "The project evolved through systematic iterations. Features like commit explanation started simple and evolved into sophisticated AI-powered analysis through multiple spec refinements."

**[Screen: Steering rules documentation]**

**Narrator:** "18 steering files provided continuous guidance - from code quality standards to testing requirements to performance optimization patterns."

---

### Results & Impact (2:40 - 3:00) - 20 seconds

**[Screen: Project statistics and metrics]**

**Narrator:** "The results speak for themselves: 16 specifications, 150+ tasks completed, comprehensive test coverage, and a production-ready tool that solves a real problem for open source maintainers."

**[Screen: GitHub repository and PyPI package]**

**Narrator:** "Forklift is available on PyPI for easy installation, with complete source code and documentation. This demonstrates how Kiro enables building sophisticated, production-ready applications through systematic AI-assisted development."

**[Screen: Call to action with repository URL]**

**Narrator:** "Try Forklift on your own repositories - start with smaller ones like Click or Requests for faster results, then scale up to larger projects."

---

## Technical Production Notes

### Screen Recording Segments

1. **Tool Demo Segments (90 seconds total)**
   - Repository: Use `maliayas/github-network-ninja` for fast, reliable demo execution
   - Commands: Pre-tested and optimized for smooth execution
   - Output: Real data showing valuable features and clear categorization

2. **Kiro Development Segments (60 seconds total)**
   - Spec files: Show actual requirements, design, and tasks documents
   - Code examples: Real TDD implementation with tests
   - Evolution: Before/after examples showing iterative improvement

### Narration Guidelines

- **Pace**: 150-160 words per minute (natural speaking pace)
- **Tone**: Professional but enthusiastic, demonstrating expertise
- **Emphasis**: Highlight both tool capabilities and development process
- **Clarity**: Technical terms explained briefly for broader audience

### Visual Elements

- **Smooth Transitions**: Fade between different screen segments
- **Highlighting**: Cursor movement and highlighting for key information
- **Text Overlays**: Key statistics and URLs for reference
- **Consistent Formatting**: Terminal with clear, readable font size

### Audio Requirements

- **Quality**: Professional microphone with noise cancellation
- **Environment**: Quiet recording space with minimal echo
- **Backup**: Multiple takes of each segment for editing flexibility
- **Timing**: Precise synchronization with screen actions

---

## Demo Repository Selection

### Primary Demo Repository: `maliayas/github-network-ninja`
**Why this repository:**
- **Originally Specified**: This repository was mentioned in the original Forklift spec for testing
- **Ultra-Fast**: Only 2.99s total demo time (measured)
- **Small Scale**: 3 forks, perfect for smooth video recording
- **Proven Performance**: Used during Forklift development
- **Reliable**: Guaranteed to work without timeouts

### Backup Repository: `xgboosted/pandas-ta-classic`
**Why this repository:**
- **Originally Specified**: Mentioned in the original Forklift spec
- **Very Fast**: Only 3.38s total demo time (measured)
- **Good Scale**: 19 forks, shows meaningful fork analysis
- **Real Value**: Demonstrates actual community contributions
- **Quick Results**: Ideal for smooth video recording

### Demo Configuration

```yaml
# demo-config.yaml
analysis:
  max_forks_to_analyze: 50  # Limit for demo performance
  min_score_threshold: 70.0
  
display:
  max_commits_to_show: 5
  terminal_width: 120
  
github:
  rate_limit_buffer: 100  # Ensure smooth demo execution
```

---

## Success Metrics

### Tool Demonstration Success
- [ ] Clear problem statement and solution demonstration
- [ ] Smooth command execution without errors
- [ ] Compelling real-world examples with valuable discoveries
- [ ] Professional output formatting and clear results

### Kiro Development Showcase Success
- [ ] Clear explanation of spec-driven development process
- [ ] Concrete examples of requirements → design → implementation
- [ ] Demonstration of iterative improvement and evolution
- [ ] Evidence of sophisticated AI-assisted development practices

### Overall Video Quality
- [ ] Professional audio and video quality
- [ ] Engaging narrative that maintains viewer interest
- [ ] Balanced coverage of tool capabilities and development process
- [ ] Clear call-to-action and next steps for judges

---

## Post-Production Checklist

### Video Editing
- [ ] Smooth transitions between segments
- [ ] Consistent audio levels throughout
- [ ] Text overlays for key information
- [ ] Captions for accessibility

### Content Verification
- [ ] All commands execute successfully
- [ ] Real data demonstrates tool value
- [ ] Kiro development process clearly explained
- [ ] Technical accuracy verified

### Distribution Preparation
- [ ] Compelling title and description for YouTube
- [ ] Appropriate tags and categories
- [ ] Engaging thumbnail highlighting key features
- [ ] Public visibility for judge access

This script balances technical demonstration with development process showcase, providing judges with a comprehensive view of both the final product and the sophisticated use of Kiro's capabilities in building it.