---
inclusion: always
---

# Git Workflow Guidelines

## Branch Naming Conventions

### Branch Types
- `feature/description-of-feature` - New features or enhancements
- `bugfix/description-of-bug` - Bug fixes for existing functionality
- `hotfix/critical-issue` - Critical fixes that need immediate deployment
- `refactor/component-name` - Code refactoring without functional changes
- `docs/update-description` - Documentation-only changes

### Naming Rules
- Use lowercase with hyphens to separate words
- Keep branch names concise but descriptive
- Include ticket/issue numbers when applicable: `feature/gh-123-user-authentication`
- Avoid special characters and spaces

## Commit Message Standards

### Conventional Commits Format
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Commit Types
- `feat`: New feature for the user
- `fix`: Bug fix for the user
- `docs`: Documentation changes
- `style`: Formatting, missing semicolons, etc.
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to build process or auxiliary tools

### Examples
```
feat(auth): add JWT token validation
fix(api): handle null response in user endpoint
docs: update installation instructions
test(models): add unit tests for User model
```

### Commit Best Practices
- Write clear, descriptive commit messages
- Use imperative mood ("add feature" not "added feature")
- Keep the first line under 50 characters
- Reference issues/tickets when applicable
- Include breaking change notes in footer when needed

## Pull Request Process

### Creating Pull Requests
- Create PRs from feature branches to main branch
- Use descriptive PR titles that summarize the change
- Include comprehensive descriptions explaining what and why
- Link related issues using GitHub keywords (fixes #123, closes #456)
- Add appropriate labels for categorization

### PR Description Template
```markdown
## Description
Brief description of changes made

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No merge conflicts
```

### Review Requirements
- All PRs must be reviewed before merging
- Ensure all CI checks pass
- Address all review comments before merging
- Use "Squash and merge" for feature branches
- Delete feature branches after successful merge

## Branching Strategy

### Main Branch Protection
- Main branch should always be deployable
- Require PR reviews before merging
- Require status checks to pass
- Prevent force pushes to main
- Automatically delete head branches after merge

### Feature Development
1. Create feature branch from latest main
2. Make commits with clear messages
3. Push branch and create PR
4. Address review feedback
5. Merge when approved and tests pass
6. Delete feature branch

### Hotfix Process
1. Create hotfix branch from main
2. Make minimal fix with tests
3. Create PR with expedited review
4. Merge and deploy immediately
5. Ensure fix is included in next regular release

## Git Best Practices

### Local Development
- Pull latest main before creating new branches
- Rebase feature branches on main before creating PR
- Use `git commit --amend` for fixing recent commits
- Avoid committing directly to main branch
- Keep commits atomic and focused

### Conflict Resolution
- Resolve conflicts locally before pushing
- Test thoroughly after resolving conflicts
- Use meaningful commit messages for merge commits
- Ask for help if conflicts are complex

### Repository Hygiene
- Regularly clean up local branches: `git branch -d feature/completed-feature`
- Use `.gitignore` to exclude unnecessary files
- Avoid committing large binary files
- Keep repository size manageable

## Release Management

### Versioning
- Use semantic versioning (MAJOR.MINOR.PATCH)
- Tag releases with version numbers
- Maintain CHANGELOG.md with release notes
- Create GitHub releases for major versions

### Release Process
1. Create release branch from main
2. Update version numbers and changelog
3. Create PR for release branch
4. Merge after review and testing
5. Tag the merge commit with version
6. Create GitHub release with notes