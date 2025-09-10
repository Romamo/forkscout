# Recording Script with Timing Cues

## Overview
This script provides precise timing, narration, and action cues for recording the Forklift demo video. Each segment includes exact timing, screen actions, and narration text.

**Total Duration:** 180 seconds (3 minutes)

---

## Segment 1: Opening Hook (0:00 - 0:20)

### Screen Actions
- **0:00-0:05**: Show GitHub repository page (microsoft/vscode) with fork count visible
- **0:05-0:10**: Transition to terminal, cursor ready
- **0:10-0:15**: Begin typing `uv run forkscout analyze` command (don't execute yet)
- **0:15-0:20**: Show command ready to execute, pause for narration

### Narration (20 seconds)
> "Imagine you maintain a popular open source project with hundreds of forks. Hidden in those forks are valuable features, bug fixes, and improvements that could benefit everyone. But manually reviewing hundreds of repositories? That's impossible. Meet Forklift - an AI-powered tool that automatically discovers and ranks valuable features across all forks of your repository."

### Technical Notes
- **Font Size**: 14pt for clear readability
- **Terminal Size**: 120x30 characters
- **Cursor**: Visible but not distracting
- **Typing Speed**: Natural pace, not too fast

---

## Segment 2: Problem → Solution (0:20 - 0:50)

### Screen Actions
- **0:20-0:25**: Show split screen - GitHub forks page vs clean terminal
- **0:25-0:30**: Execute command: `uv run forkscout analyze https://github.com/fastapi/fastapi --explain`
- **0:30-0:40**: Show command running with progress indicators
- **0:40-0:50**: Display initial results with categorized commits

### Narration (30 seconds)
> "The problem is real. Popular repositories like FastAPI have over 3,000 forks. Each fork might contain valuable improvements, but there's no efficient way to discover them. Forklift solves this by automatically scanning all forks, analyzing commits with AI, and ranking features by their potential value to the main repository. In seconds, you see exactly what each fork contributes - new features, bug fixes, performance improvements - all ranked and explained."

### Technical Notes
- **Command**: Pre-tested and cached for smooth execution
- **Output**: Real data showing diverse commit types
- **Timing**: Allow natural pauses for command execution

---

## Segment 3: Tool Demonstration (0:50 - 1:40)

### 3.1 Repository Overview (0:50 - 1:05)

#### Screen Actions
- **0:50-0:52**: Clear terminal, type command
- **0:52-0:55**: Execute: `uv run forkscout show-repo https://github.com/microsoft/vscode`
- **0:55-1:05**: Display repository statistics and metrics

#### Narration (15 seconds)
> "Let's see Forklift in action. We'll analyze a real repository with multiple forks. First, we get an overview - 19,000 forks, but Forklift intelligently filters to focus on active ones with new commits."

### 3.2 Fork Discovery (1:05 - 1:25)

#### Screen Actions
- **1:05-1:08**: Type command: `uv run forkscout show-forks https://github.com/microsoft/vscode --detail`
- **1:08-1:12**: Execute command, show loading
- **1:12-1:25**: Display fork table with commit counts and activity levels

#### Narration (20 seconds)
> "The fork analysis shows which repositories have new commits, how many commits ahead they are, and their activity levels. This table gives us a clear view of the most promising forks to investigate further."

### 3.3 Commit Analysis (1:25 - 1:40)

#### Screen Actions
- **1:25-1:28**: Type: `uv run forklift show-commits https://github.com/coder/code-server --explain`
- **1:28-1:32**: Execute command
- **1:32-1:40**: Show detailed commit explanations with AI categorization

#### Narration (15 seconds)
> "For each interesting fork, Forklift analyzes individual commits. AI categorizes them - features, bug fixes, performance improvements - and assesses their value for the main repository."

---

## Segment 4: Kiro Development Showcase (1:40 - 2:40)

### 4.1 Spec-Driven Development Introduction (1:40 - 1:55)

#### Screen Actions
- **1:40-1:42**: Transition to Kiro interface or spec files
- **1:42-1:45**: Show requirements document
- **1:45-1:50**: Highlight specific requirements with cursor
- **1:50-1:55**: Show evolution from vague to specific requirements

#### Narration (15 seconds)
> "But here's what makes this project special - it was built entirely using Kiro's spec-driven development. We started with user stories and acceptance criteria. Kiro helped refine vague requirements like 'analyze forks' into specific, testable criteria with 22 detailed requirements."

### 4.2 Design and Architecture (1:55 - 2:10)

#### Screen Actions
- **1:55-1:58**: Show design document with architecture diagrams
- **1:58-2:02**: Highlight caching system decision
- **2:02-2:06**: Show before/after code comparison
- **2:06-2:10**: Display architectural benefits

#### Narration (15 seconds)
> "Kiro then guided the design phase, helping choose between architectural options. For example, replacing a complex custom caching system with HTTP-level caching - reducing 1,150 lines of code to just 30."

### 4.3 Task Implementation (2:10 - 2:25)

#### Screen Actions
- **2:10-2:13**: Show tasks.md with task breakdown
- **2:13-2:17**: Highlight task-to-requirement traceability
- **2:17-2:21**: Show TDD implementation example
- **2:21-2:25**: Display test coverage statistics

#### Narration (15 seconds)
> "The implementation used 16 different specs, each broken down into focused tasks. Every task references specific requirements and includes comprehensive tests. Kiro enforced test-driven development through steering rules, achieving over 90% test coverage."

### 4.4 Evolution and Iteration (2:25 - 2:40)

#### Screen Actions
- **2:25-2:28**: Show spec evolution timeline
- **2:28-2:32**: Highlight iterative improvements
- **2:32-2:36**: Show steering rules documentation
- **2:36-2:40**: Display final project statistics

#### Narration (15 seconds)
> "The project evolved through systematic iterations. Features like commit explanation started simple and evolved into sophisticated AI-powered analysis through multiple spec refinements. 18 steering files provided continuous guidance throughout development."

---

## Segment 5: Results & Impact (2:40 - 3:00)

### Screen Actions
- **2:40-2:45**: Show project statistics dashboard
- **2:45-2:50**: Display GitHub repository and PyPI package
- **2:50-2:55**: Show final call-to-action screen
- **2:55-3:00**: End with repository URL and fade out

### Narration (20 seconds)
> "The results speak for themselves: 16 specifications, 150+ tasks completed, comprehensive test coverage, and a production-ready tool that solves a real problem for open source maintainers. Forklift is available on PyPI for easy installation, with complete source code and documentation. This demonstrates how Kiro enables building sophisticated, production-ready applications through systematic AI-assisted development. Try Forklift on your own repositories, and see how Kiro can transform your development process."

---

## Recording Cues and Timing

### Timing Markers
- **0:20** - Transition to problem explanation
- **0:50** - Begin tool demonstration
- **1:40** - Switch to Kiro development showcase
- **2:40** - Final results and call-to-action
- **3:00** - End recording

### Visual Cues
- **Cursor Movement**: Smooth, deliberate movements to highlight key information
- **Typing Speed**: Natural pace, not too fast for viewers to follow
- **Pauses**: Allow time for complex outputs to be absorbed
- **Transitions**: Smooth fades between different screen contexts

### Audio Cues
- **Pace**: 150-160 words per minute
- **Emphasis**: Stress key benefits and technical achievements
- **Pauses**: Natural breaks at segment transitions
- **Tone**: Professional but enthusiastic throughout

---

## Command Reference

### Pre-Recording Setup
```bash
# Set environment
export GITHUB_TOKEN=your_token_here
export COLUMNS=120
export LINES=30

# Navigate to demo directory
cd demo

# Verify configurations
ls -la *.yaml
```

### Demo Commands (in order)
```bash
# 1. Repository overview
uv run forkscout show-repo https://github.com/maliayas/github-network-ninja

# 2. Fork discovery
uv run forkscout show-forks https://github.com/maliayas/github-network-ninja --detail --max-forks 5

# 3. Commit analysis
uv run forklift show-commits https://github.com/elliotberry/github-network-ninja --explain --max-commits 3

# 4. Full analysis (if time permits)
uv run forkscout analyze https://github.com/maliayas/github-network-ninja --output demo-report.md --max-forks 5
```

### Backup Commands (Pandas-TA-Classic)
```bash
# Alternative repository for backup
uv run forkscout show-repo https://github.com/xgboosted/pandas-ta-classic
uv run forkscout show-forks https://github.com/xgboosted/pandas-ta-classic --ahead-only --max-forks 5
```

---

## Post-Recording Checklist

### Immediate Review
- [ ] Check video quality and readability
- [ ] Verify audio clarity and synchronization
- [ ] Confirm all commands executed successfully
- [ ] Validate timing matches script requirements
- [ ] Ensure smooth transitions between segments

### Content Verification
- [ ] Tool demonstration shows clear value
- [ ] Kiro development process well explained
- [ ] Technical accuracy throughout
- [ ] Professional presentation quality
- [ ] Compelling narrative maintained

### Technical Quality
- [ ] 1080p resolution maintained
- [ ] 30fps frame rate consistent
- [ ] Audio levels appropriate
- [ ] No visual artifacts or issues
- [ ] File size reasonable for upload

This detailed recording script ensures consistent, professional execution of the demo video with precise timing and clear technical demonstrations.