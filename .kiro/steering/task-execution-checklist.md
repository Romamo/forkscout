---
inclusion: always
---

# Task Execution Checklist

## Mandatory Pre-Implementation Steps

Before implementing any task, you MUST:

1. **Create Feature Branch**:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b task/X.Y-task-description
   ```

2. **Set Task Status**: Mark task as in-progress using taskStatus tool

3. **Confirm Understanding**: Briefly state what you're about to implement

## During Implementation

4. **Follow TDD**: Write tests first, then implementation
5. **Make Atomic Commits**: Clear commit messages for each logical change
6. **Run Tests Frequently**: Ensure nothing breaks as you work

## Mandatory Pre-Completion Steps

Before marking any task complete, you MUST:

7. **Run All Quality Checks**:
   ```bash
   uv run pytest
   uv run ruff check src/ tests/
   uv run black --check src/ tests/
   uv run mypy src/
   ```

8. **Merge to Main**:
   ```bash
   git checkout main
   git pull origin main
   git merge task/X.Y-task-description
   git push origin main
   git branch -d task/X.Y-task-description
   ```

9. **Update Task Status**: Only mark complete AFTER successful merge

## Failure to Follow

If you skip any of these steps, STOP and ask the user to remind you of the proper workflow.