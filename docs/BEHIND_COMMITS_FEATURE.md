# Behind Commits Display Feature

## Overview

Forkscout now displays both **ahead** and **behind** commit counts when analyzing repository forks. This provides a complete picture of how forks have diverged from their parent repository.

## Display Format

The commit count display uses the following format:

- `+9` - Fork has 9 commits ahead of parent (no behind commits)
- `-11` - Fork has 11 commits behind parent (no ahead commits)  
- `+9 -11` - Fork has 9 commits ahead and 11 commits behind parent
- `` (empty) - Fork is identical to parent (no ahead or behind commits)
- `Unknown` - Commit count could not be determined (API error)

## Examples

### Terminal Display
```
URL                                    Stars  Forks  Commits     Last Push
https://github.com/GreatBots/YouTube_bot_telegram  10     2      +9 -11      2 months ago
https://github.com/user/fork                       5      1      +3          1 week ago
https://github.com/another/fork                    2      0      -5          3 days ago
```

### CSV Export
```csv
fork_name,owner,stars,commits_ahead,activity_status,fork_url
YouTube_bot_telegram,GreatBots,10,"+9 -11",Active,https://github.com/GreatBots/YouTube_bot_telegram
fork,user,5,"+3",Active,https://github.com/user/fork
fork,another,2,"-5",Active,https://github.com/another/fork
```

## CLI Usage

### Basic Usage
```bash
# Show forks with basic commit status
forkscout show-forks owner/repo

# Show detailed commit counts (ahead and behind)
forkscout show-forks owner/repo --detail
```

### Filtering Options
```bash
# Show only forks with commits ahead (includes diverged forks)
forkscout show-forks owner/repo --detail --ahead-only

# Export to CSV with behind commits included
forkscout show-forks owner/repo --detail --csv > forks.csv
```

## Technical Details

### GitHub API Integration
- Uses GitHub's compare API: `/repos/{owner}/{repo}/compare/{base}...{head}`
- Extracts both `ahead_by` and `behind_by` fields from API response
- Gracefully handles missing `behind_by` field (defaults to 0 for older API responses)

### Error Handling
- Network timeouts return `Unknown` status
- API rate limits are handled gracefully
- Malformed responses default to safe values
- Missing data fields are handled without crashes

### Performance
- Batch processing minimizes API calls
- Parent repository info is fetched once per batch
- Results are cached to avoid duplicate requests
- Rate limiting prevents API quota exhaustion

## Compatibility

### Backward Compatibility
- Existing `--ahead-only` flag continues to work as expected
- Forks with both ahead and behind commits are included in `--ahead-only` results
- CSV export format maintains compatibility with existing tools
- Display format is enhanced but maintains readability

### API Requirements
- Requires GitHub personal access token
- Works with both public and private repositories (with appropriate permissions)
- Compatible with GitHub Enterprise Server

## Troubleshooting

### Common Issues

**Issue**: Seeing `Unknown` for commit counts
**Solution**: Check GitHub API rate limits and token permissions

**Issue**: Behind commits not showing
**Solution**: Ensure using `--detail` flag to fetch exact counts

**Issue**: CSV export missing behind commits  
**Solution**: Behind commits are included in the `commits_ahead` column as `+X -Y` format

### Debug Information
```bash
# Enable debug logging to see API calls
export FORKSCOUT_LOG_LEVEL=DEBUG
forkscout show-forks owner/repo --detail
```

## Related Documentation

- [Commit Counting Troubleshooting](COMMIT_COUNTING_TROUBLESHOOTING.md)
- [API Rate Limiting](API_RATE_LIMITING.md)
- [CSV Export Format](CSV_EXPORT_FORMAT.md)