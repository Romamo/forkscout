# Commit Counting Troubleshooting Guide

This guide helps you diagnose and resolve issues related to commit counting in Forklift, particularly when using the `--detail` flag with `show-forks` command.

## Overview

Forklift uses GitHub's compare API to determine how many commits each fork is ahead of the upstream repository. The system has been enhanced to provide accurate commit counts instead of the previous bug where all forks showed "+1" commits.

## Common Issues and Solutions

### Issue: Behind Commits Not Displayed

**Symptoms:**
- Only seeing ahead commits (e.g., "+9") but not behind commits
- Forks that are behind the parent don't show negative counts
- Missing complete divergence information

**Cause:**
Behind commits are only displayed when using the `--detail` flag, which fetches exact commit counts from GitHub's compare API.

**Solution:**
Always use the `--detail` flag to see both ahead and behind commits:
```bash
forklift show-forks owner/repo --detail
```

**Expected Output:**
- `+9 -11` - Fork has 9 commits ahead and 11 commits behind
- `+5` - Fork has 5 commits ahead, 0 behind
- `-3` - Fork has 0 commits ahead, 3 behind
- `` (empty) - Fork is identical to parent

### Issue: All Forks Show "+1" Commits (Legacy Bug)

**Symptoms:**
- Every fork displays "+1" in the commits column regardless of actual commit count
- Using `--detail` flag doesn't show accurate numbers
- Forks with many commits still show only "+1"

**Cause:**
This was a bug in versions prior to the commit counting fix where the system used `count=1` parameter and counted the length of the returned commits array instead of using the `ahead_by` field.

**Solution:**
Update to the latest version of Forklift. The fix uses GitHub's `ahead_by` field from the compare API response for accurate counting.

**Verification:**
```bash
# Test with a known repository that has forks with multiple commits
forklift show-forks sanila2007/youtube-bot-telegram --detail --ahead-only
```

### Issue: Commit Counts Show "100+" Instead of Exact Numbers

**Symptoms:**
- Forks show "100+" instead of exact commit counts
- Very active forks don't show precise numbers
- Counts seem capped at 100

**Cause:**
The default `--max-commits-count` limit is set to 100 for performance reasons.

**Solutions:**

1. **Increase the limit for more accuracy:**
```bash
forklift show-forks owner/repo --detail --max-commits-count 500
```

2. **Use unlimited counting (slower but most accurate):**
```bash
forklift show-forks owner/repo --detail --max-commits-count 0
```

3. **Balance accuracy vs performance:**
```bash
# Good for most cases - counts up to 200 commits
forklift show-forks owner/repo --detail --max-commits-count 200
```

### Issue: Slow Performance When Counting Commits

**Symptoms:**
- Command takes a very long time to complete
- Progress seems to stall on certain forks
- High API usage warnings

**Causes and Solutions:**

1. **High commit count limit:**
```bash
# Problem: Unlimited counting on repository with many active forks
forklift show-forks owner/repo --detail --max-commits-count 0

# Solution: Use reasonable limits
forklift show-forks owner/repo --detail --max-commits-count 100
```

2. **Too many forks being processed:**
```bash
# Problem: Processing hundreds of forks
forklift show-forks popular/repo --detail

# Solution: Limit the number of forks
forklift show-forks popular/repo --detail --max-forks 50
```

3. **Network or API issues:**
```bash
# Add verbose output to diagnose
forklift show-forks owner/repo --detail --verbose
```

### Issue: "Unknown" Commit Counts

**Symptoms:**
- Some forks show "Unknown" in the commits column
- Inconsistent results across forks
- Error messages about API failures

**Common Causes and Solutions:**

1. **Private or deleted forks:**
   - **Cause:** Fork repository is private or has been deleted
   - **Solution:** This is expected behavior; private forks cannot be analyzed
   - **Identification:** Look for "Repository not found" or "Access denied" in verbose output

2. **API rate limiting:**
   - **Cause:** GitHub API rate limit exceeded
   - **Solution:** Wait for rate limit reset or use authentication token
   ```bash
   # Check rate limit status
   curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit
   ```

3. **Network timeouts:**
   - **Cause:** Network connectivity issues or slow responses
   - **Solution:** Retry the command or check network connection
   ```bash
   # Test with verbose output
   forklift show-forks owner/repo --detail --verbose
   ```

4. **Divergent git histories:**
   - **Cause:** Fork has diverged significantly from upstream
   - **Solution:** This is expected for heavily modified forks
   - **Identification:** Look for "no merge base" errors in verbose output

### Issue: Inconsistent Commit Counts Between Runs

**Symptoms:**
- Different commit counts when running the same command multiple times
- Counts change without apparent reason
- Some forks show different numbers on subsequent runs

**Causes and Solutions:**

1. **Active development on forks:**
   - **Cause:** Forks are actively receiving new commits
   - **Solution:** This is expected behavior for active repositories
   - **Verification:** Check fork's recent activity on GitHub

2. **Caching issues:**
   - **Cause:** Stale cache data interfering with fresh API calls
   - **Solution:** Clear cache or disable caching
   ```bash
   # Disable cache for fresh data
   forklift show-forks owner/repo --detail --disable-cache
   ```

3. **API consistency issues:**
   - **Cause:** GitHub API occasionally returns slightly different results
   - **Solution:** This is rare but can happen; results should stabilize

### Issue: Configuration Options Not Working

**Symptoms:**
- `--max-commits-count` seems to be ignored
- `--commit-display-limit` doesn't affect output
- Default values are used despite specifying options

**Diagnostic Steps:**

1. **Verify option syntax:**
```bash
# Correct syntax
forklift show-forks owner/repo --detail --max-commits-count 200

# Incorrect syntax (missing equals sign is OK)
forklift show-forks owner/repo --detail --max-commits-count=200
```

2. **Check for conflicting options:**
```bash
# Some options may override others
forklift show-forks owner/repo --detail --csv --max-commits-count 200
```

3. **Use verbose output to verify configuration:**
```bash
forklift show-forks owner/repo --detail --verbose --max-commits-count 200
```

## Performance Optimization

### Recommended Settings by Repository Size

**Small repositories (< 50 forks):**
```bash
forklift show-forks owner/repo --detail --max-commits-count 0
# Use unlimited counting for complete accuracy
```

**Medium repositories (50-200 forks):**
```bash
forklift show-forks owner/repo --detail --max-commits-count 200
# Balance accuracy with reasonable performance
```

**Large repositories (200+ forks):**
```bash
forklift show-forks owner/repo --detail --max-commits-count 100 --max-forks 100
# Limit both commit counting and fork processing
```

**Very large repositories (500+ forks):**
```bash
forklift show-forks owner/repo --detail --max-commits-count 50 --max-forks 50 --ahead-only
# Focus on most relevant forks only
```

### API Usage Optimization

**Monitor API usage:**
```bash
# Check current rate limit status
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit
```

**Reduce API calls:**
```bash
# Use ahead-only to skip forks with no commits
forklift show-forks owner/repo --detail --ahead-only

# Limit fork processing
forklift show-forks owner/repo --detail --max-forks 25

# Use lower commit count limits
forklift show-forks owner/repo --detail --max-commits-count 50
```

## Configuration Best Practices

### Environment Setup

1. **GitHub Token Configuration:**
```bash
# Set in environment
export GITHUB_TOKEN=your_token_here

# Or in .env file
echo "GITHUB_TOKEN=your_token_here" >> .env
```

2. **Default Configuration:**
Create `forklift.yaml` with sensible defaults:
```yaml
github:
  token: ${GITHUB_TOKEN}

commit_count:
  max_count_limit: 100
  display_limit: 5
  use_unlimited_counting: false
  timeout_seconds: 30
```

### Command-Line Best Practices

1. **Start with basic analysis:**
```bash
forklift show-forks owner/repo
```

2. **Add detail when needed:**
```bash
forklift show-forks owner/repo --detail
```

3. **Optimize for your use case:**
```bash
# For accuracy
forklift show-forks owner/repo --detail --max-commits-count 0

# For speed
forklift show-forks owner/repo --detail --max-commits-count 50 --max-forks 25

# For active forks only
forklift show-forks owner/repo --detail --ahead-only
```

## Debugging Steps

### Step 1: Verify Basic Functionality

```bash
# Test with a simple repository
forklift show-forks octocat/Hello-World --detail --verbose
```

### Step 2: Check Configuration

```bash
# Verify GitHub token is working
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user

# Check Forklift configuration
forklift configure --show
```

### Step 3: Test with Known Repository

```bash
# Use the repository mentioned in the original bug report
forklift show-forks sanila2007/youtube-bot-telegram --detail --ahead-only --verbose
```

### Step 4: Isolate the Issue

```bash
# Test without detail flag
forklift show-forks owner/repo

# Test with minimal options
forklift show-forks owner/repo --detail --max-forks 5

# Test with unlimited counting
forklift show-forks owner/repo --detail --max-commits-count 0 --max-forks 5
```

### Step 5: Collect Diagnostic Information

When reporting issues, include:

1. **Command used:**
```bash
forklift show-forks owner/repo --detail --max-commits-count 200 --verbose
```

2. **Environment information:**
```bash
python --version
pip show forklift
echo $GITHUB_TOKEN | cut -c1-10  # First 10 characters only
```

3. **Error output:**
```bash
# Capture full output
forklift show-forks owner/repo --detail --verbose > output.log 2>&1
```

4. **Expected vs actual behavior:**
- What you expected to see
- What actually happened
- Screenshots if applicable

## Error Messages and Solutions

### "GitHub API rate limit exceeded"

**Solution:**
```bash
# Wait for rate limit reset (shown in error message)
# Or use authenticated requests with higher limits
export GITHUB_TOKEN=your_token_here
```

### "Repository not found or access denied"

**Solutions:**
- Verify repository URL is correct
- Check if repository is public
- Ensure GitHub token has appropriate permissions

### "Timeout while fetching commit data"

**Solutions:**
```bash
# Reduce commit count limit
forklift show-forks owner/repo --detail --max-commits-count 50

# Reduce number of forks processed
forklift show-forks owner/repo --detail --max-forks 25
```

### "Invalid commit count configuration"

**Solutions:**
- Ensure `--max-commits-count` is between 0 and 10000
- Ensure `--commit-display-limit` is between 0 and 100
- Check for typos in option names

## Getting Help

### Before Reporting Issues

1. Check this troubleshooting guide
2. Try the debugging steps above
3. Search existing GitHub issues
4. Test with a simple, public repository

### When Reporting Issues

Include the following information:

1. **Forklift version:** `pip show forklift`
2. **Python version:** `python --version`
3. **Operating system:** `uname -a` (Linux/Mac) or system info (Windows)
4. **Command used:** Full command with all options
5. **Expected behavior:** What should happen
6. **Actual behavior:** What actually happens
7. **Error messages:** Complete error output
8. **Repository:** Public repository that reproduces the issue (if possible)

### Community Resources

- **GitHub Issues:** Report bugs and feature requests
- **Documentation:** Check the main README and docs/ directory
- **Examples:** Look at the examples/ directory for usage patterns

## Advanced Troubleshooting

### Custom Configuration Testing

Create a test configuration file:

```yaml
# test-config.yaml
github:
  token: ${GITHUB_TOKEN}

commit_count:
  max_count_limit: 50
  display_limit: 3
  use_unlimited_counting: false
  timeout_seconds: 60

analysis:
  max_forks_to_analyze: 25
```

Test with custom config:
```bash
forklift show-forks owner/repo --detail --config test-config.yaml
```

### API Response Analysis

For deep debugging, you can examine raw API responses:

```bash
# Test GitHub API directly
curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/owner/repo/compare/main...fork_owner:main"
```

Look for the `ahead_by` field in the response, which should match Forklift's output.

### Performance Profiling

For performance issues:

```bash
# Time the command
time forklift show-forks owner/repo --detail --max-commits-count 100

# Monitor API calls with verbose output
forklift show-forks owner/repo --detail --verbose 2>&1 | grep -i "api\|request\|rate"
```

This troubleshooting guide should help you resolve most commit counting issues. If you continue to experience problems after following these steps, please report the issue with the diagnostic information requested above.