# Task Management Guidelines

## Task Status Preservation

### Critical Rule: Never Modify Completed or In-Progress Tasks

**NEVER modify tasks that are marked as completed [x] or in progress [-].**

When updating specs or adding new functionality:

- **DO NOT** change the content, requirements, or acceptance criteria of completed tasks
- **DO NOT** add new sub-tasks to completed tasks
- **DO NOT** modify requirement references in completed tasks
- **DO NOT** change task descriptions for tasks that are already done

### Proper Approach for New Requirements

When new functionality is needed:

1. **Create new tasks** instead of modifying existing completed ones
2. **Add new task numbers** (e.g., 8.6, 8.7) rather than editing 8.3 if it's complete
3. **Reference new requirements** in new tasks only
4. **Keep completed work intact** to maintain development history

### Task Status Guidelines

- **[x] Completed**: Task is done and should never be modified
- **[-] In Progress**: Task is being worked on and should not have scope changes
- **[ ] Not Started**: Only these tasks should be modified for scope or requirement changes

### Example of Correct Approach

```markdown
# WRONG - Don't modify completed tasks
- [x] 8.3 Implement CLI commands
  - Original work
  - NEW WORK ADDED HERE ❌

# CORRECT - Create new tasks
- [x] 8.3 Implement CLI commands
  - Original work (unchanged)

- [ ] 8.6 Add new CLI feature
  - New functionality here ✅
```

### Rationale

- Preserves development history and completed work
- Prevents confusion about what was actually implemented
- Maintains task integrity and prevents scope creep
- Allows proper tracking of new vs existing functionality
- Respects the effort already invested in completed tasks

### When Updating Specs

If requirements change and affect completed tasks:

1. **Document the change** in new requirements
2. **Create new tasks** for the additional work needed
3. **Reference both old and new requirements** appropriately
4. **Never retroactively change** what was already completed

This ensures that completed work remains stable and new work is properly tracked and managed.

## Branch-Based Task Implementation

### Task Development Workflow

**Each task must be implemented in its own feature branch and merged only upon successful completion.**

### Branching Strategy

1. **Create Feature Branch**: Before starting any task, create a new branch from main
   ```bash
   git checkout main
   git pull origin main
   git checkout -b task/X.Y-task-description
   ```

2. **Branch Naming Convention**: Use descriptive branch names that match the task
   ```
   task/6.1-implement-markdown-report-generator
   task/7.1-create-pr-creation-service
   task/9.1-sqlite-caching-system
   ```

3. **Implementation Process**:
   - Work exclusively in the feature branch
   - Make atomic commits with clear messages
   - Follow TDD practices (tests first, then implementation)
   - Ensure all tests pass before considering task complete

4. **Completion Criteria**: Before merging, verify:
   - ✅ All task requirements implemented
   - ✅ All tests pass (`uv run pytest`)
   - ✅ Code quality checks pass (`uv run ruff check`, `uv run black --check`)
   - ✅ Type checking passes (`uv run mypy`)
   - ✅ No regression in existing functionality

5. **Merge Process**:
   ```bash
   # Ensure all tests pass
   uv run pytest
   uv run ruff check src/ tests/
   uv run black --check src/ tests/
   uv run mypy src/
   
   # Merge to main
   git checkout main
   git pull origin main
   git merge task/X.Y-task-description
   git push origin main
   
   # Clean up branch
   git branch -d task/X.Y-task-description
   ```

6. **Task Status Update**: Only mark task as complete [x] after successful merge to main

### Benefits of Branch-Based Development

- **Isolation**: Each task is developed in isolation, preventing conflicts
- **Quality Gates**: Ensures all quality checks pass before integration
- **Rollback Safety**: Easy to revert specific features if issues arise
- **Clear History**: Git history clearly shows what was implemented when
- **Parallel Development**: Multiple tasks can be worked on simultaneously
- **Code Review**: Enables proper code review process before merging

### Branch Protection Rules

- **Main Branch**: Should always be in a deployable state
- **No Direct Commits**: Never commit directly to main branch
- **Feature Branches**: All development happens in feature branches
- **Clean Merges**: Use merge commits to preserve feature branch history

### Example Workflow

```bash
# Starting task 6.1
git checkout -b task/6.1-implement-markdown-report-generator

# Implement the task with TDD
# 1. Write failing tests
# 2. Implement minimal code to pass
# 3. Refactor and improve
# 4. Repeat until task complete

# Verify completion
uv run pytest
uv run ruff check src/ tests/
uv run black --check src/ tests/

# Merge when all checks pass
git checkout main
git merge task/6.1-implement-markdown-report-generator
git push origin main

# Update task status to [x] completed
```

This workflow ensures that each task is properly implemented, tested, and integrated without breaking existing functionality.