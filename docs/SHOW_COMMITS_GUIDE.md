# Show Commits Feature Guide

This guide covers the `--show-commits` functionality in the Forklift tool, which allows you to display recent commits for each fork when using the `show-forks` command.

## Overview

The `--show-commits` option enhances the `show-forks` command by adding a "Recent Commits" column that displays the last N commit messages for each fork. This helps you quickly understand what changes have been made in each fork without having to visit each repository individually.

## Basic Usage

### Show Forks Without Commits (Default)

```bash
forklift show-forks owner/repository
```

This displays the standard fork summary table without commit information.

### Show Forks With Recent Commits

```bash
forklift show-forks owner/repository --show-commits=3
```

This adds a "Recent Commits" column showing the last 3 commit messages for each fork.

## Command Syntax

```bash
forklift show-forks <repository_url> [OPTIONS]
```

### Options

- `--show-commits=N`: Show last N commits for each fork (0-10, default: 0)
  - `N=0`: No commits shown (default behavior)
  - `N=1-10`: Show last N commit messages
- `--max-forks=N`: Limit the number of forks displayed
- `--detail`: Fetch exact commit counts ahead (makes additional API requests)

### Repository URL Formats

The tool accepts various repository URL formats:

- Full GitHub URL: `https://github.com/owner/repo`
- SSH URL: `git@github.com:owner/repo.git`
- Short format: `owner/repo`

## Examples

### Basic Examples

```bash
# Show forks with last 2 commits for each
forklift show-forks microsoft/vscode --show-commits=2

# Show forks with last 5 commits, limited to 20 forks
forklift show-forks facebook/react --show-commits=5 --max-forks=20

# Show detailed fork info with commits
forklift show-forks python/cpython --detail --show-commits=3
```

### Advanced Usage

```bash
# Maximum commits per fork (10)
forklift show-forks owner/repo --show-commits=10

# Combine with other options
forklift show-forks owner/repo --show-commits=3 --max-forks=50 --detail
```

## Output Format

When `--show-commits` is used, the output table includes an additional "Recent Commits" column:

```
Fork Name          Owner        Stars  Last Push    Commits Ahead  Recent Commits
─────────────────────────────────────────────────────────────────────────────────
feature-branch     activedev    25     2024-01-15   5              feat: add auth system
                                                                    fix: resolve timeout
                                                                    docs: update README

bugfix-collection  bugfixer     12     2024-01-12   3              fix: null pointer exception
                                                                    fix: memory leak
                                                                    test: add unit tests
```

### Commit Message Formatting

- Long commit messages are automatically truncated for table readability
- Each commit is shown on a separate line within the cell
- Commit messages are displayed in chronological order (newest first)
- Empty or unavailable commits are handled gracefully

## Performance Considerations

### API Usage

The `--show-commits` option makes additional GitHub API requests:

- **Without `--show-commits`**: 1-2 API calls per fork
- **With `--show-commits`**: 2-3 API calls per fork

### Performance Impact

| Forks | Commits | Estimated Time | API Calls |
|-------|---------|----------------|-----------|
| 10    | 3       | 2-5 seconds    | ~30       |
| 25    | 3       | 5-10 seconds   | ~75       |
| 50    | 5       | 10-20 seconds  | ~150      |
| 100   | 5       | 20-40 seconds  | ~300      |

### Optimization Tips

1. **Use `--max-forks`** to limit the number of forks processed
2. **Start with fewer commits** (1-3) for initial exploration
3. **Use `--show-commits=0`** when you only need fork metadata
4. **Consider rate limits** when analyzing repositories with many forks

## Rate Limiting

GitHub API has rate limits that affect performance:

- **Authenticated requests**: 5,000 per hour
- **Unauthenticated requests**: 60 per hour

The tool automatically handles rate limiting with exponential backoff, but large repositories may take longer to process.

## Error Handling

The tool handles various error scenarios gracefully:

### Common Scenarios

1. **Fork has no commits**: Shows empty commit list
2. **API rate limit exceeded**: Automatically retries with backoff
3. **Network timeout**: Retries failed requests
4. **Private/inaccessible forks**: Skips and continues with others

### Error Messages

```bash
# Rate limit exceeded
Warning: GitHub API rate limit exceeded. Waiting 60 seconds...

# Fork access denied
Warning: Cannot access fork 'owner/private-fork' (private or deleted)

# Network error
Warning: Network error fetching commits for 'owner/fork'. Retrying...
```

## Best Practices

### For Large Repositories

1. **Start small**: Use `--max-forks=10 --show-commits=2` initially
2. **Increase gradually**: Expand limits based on performance
3. **Use filtering**: Combine with `--detail` to focus on active forks

### For Regular Analysis

1. **Consistent commit count**: Use the same N value for comparable results
2. **Document your process**: Note the parameters used for reproducibility
3. **Monitor API usage**: Be aware of rate limit consumption

### For Team Usage

1. **Share configurations**: Document useful parameter combinations
2. **Set expectations**: Communicate expected execution times
3. **Use automation carefully**: Consider API limits in automated workflows

## Troubleshooting

### Slow Performance

**Problem**: Command takes too long to execute
**Solutions**:
- Reduce `--show-commits` value
- Use `--max-forks` to limit scope
- Check network connectivity
- Verify GitHub token is configured

### Missing Commits

**Problem**: Some forks show no commits despite having changes
**Possible Causes**:
- Fork has no commits ahead of upstream
- Commits are in different branch than default
- Fork is private or inaccessible
- API rate limiting causing timeouts

### API Errors

**Problem**: Frequent API errors or timeouts
**Solutions**:
- Verify GitHub token is valid and has appropriate permissions
- Check GitHub API status (status.github.com)
- Reduce concurrent requests by using smaller `--max-forks`
- Wait for rate limit reset if exceeded

## Integration with Other Commands

### Workflow Examples

```bash
# 1. Quick overview without commits
forklift show-forks owner/repo

# 2. Detailed analysis with commits
forklift show-forks owner/repo --detail --show-commits=3

# 3. Focus on specific fork
forklift show-commits owner/specific-fork --branch=feature-branch

# 4. Comprehensive analysis
forklift analyze owner/repo --interactive
```

### Command Combinations

The `--show-commits` feature works well with:

- `--detail`: Get exact commit counts AND recent commit messages
- `--max-forks`: Limit scope for faster execution
- Other filtering options in future versions

## Configuration

### GitHub Token

Ensure your GitHub token is configured for optimal performance:

```bash
forklift configure
# Follow prompts to set GitHub token
```

### Environment Variables

```bash
export GITHUB_TOKEN=your_token_here
export FORKLIFT_MAX_FORKS=50  # Default max forks
```

## Limitations

### Current Limitations

1. **Maximum commits**: Limited to 10 commits per fork
2. **Default branch only**: Only shows commits from the default branch
3. **No commit filtering**: Cannot filter commits by author, date, etc.
4. **Text-only display**: No syntax highlighting or rich formatting

### Future Enhancements

Planned improvements include:
- Branch selection for commit display
- Commit filtering options
- Rich formatting and syntax highlighting
- Export options for commit data
- Caching for improved performance

## FAQ

### Q: Why is the maximum commits limited to 10?

A: This limit balances usefulness with performance and readability. Displaying more commits would make the table unwieldy and significantly increase API usage.

### Q: Can I see commits from specific branches?

A: Currently, only the default branch is supported. Use the `show-commits` command for specific branch analysis.

### Q: How does this affect API rate limits?

A: Each fork with `--show-commits` makes one additional API call. Monitor your usage with repositories having many forks.

### Q: Can I export the commit data?

A: Currently, output is text-based only. Future versions may include export options.

### Q: What happens if a fork is private?

A: Private or inaccessible forks are skipped with a warning message. The tool continues processing other forks.

## Support

For issues, questions, or feature requests related to the `--show-commits` functionality:

1. Check this guide for common solutions
2. Review the troubleshooting section
3. Check existing GitHub issues
4. Create a new issue with detailed information about your use case

Include the following information when reporting issues:
- Command used
- Repository being analyzed
- Error messages (if any)
- Expected vs. actual behavior
- System information (OS, Python version, etc.)