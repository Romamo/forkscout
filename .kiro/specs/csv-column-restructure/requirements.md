# Requirements Document

## Introduction

The current CSV export format needs to be restructured to improve usability and data organization. Users need a more intuitive column layout with better naming, proper column ordering, and enhanced data presentation. The current format has issues with column naming, ordering, and includes unnecessary columns while missing useful ones.

## Requirements

### Requirement 1

**User Story:** As a user analyzing fork data in spreadsheets, I want the Fork URL to be the first column with a clear name so that I can easily identify and access each fork.

#### Acceptance Criteria

1. WHEN I export CSV data THEN the first column SHALL be named "Fork URL" instead of "fork_url"
2. WHEN I export CSV data THEN the "Fork URL" column SHALL contain the GitHub URL for each fork
3. WHEN I open the CSV in a spreadsheet THEN the Fork URL SHALL be immediately visible as the leftmost column
4. WHEN the fork URL is missing THEN the column SHALL contain an empty value rather than being omitted
5. WHEN I export with URLs disabled THEN the Fork URL column SHALL still be present but empty

### Requirement 2

**User Story:** As a user analyzing fork metadata, I want unnecessary columns removed so that the CSV is cleaner and more focused on essential information.

#### Acceptance Criteria

1. WHEN I export CSV data THEN the "fork_name" column SHALL be removed from the output
2. WHEN I export CSV data THEN the "owner" column SHALL be removed from the output  
3. WHEN I export CSV data THEN the "activity_status" column SHALL be removed from the output
4. WHEN I export CSV data THEN the remaining columns SHALL contain only essential fork information
5. WHEN I compare old and new formats THEN the new format SHALL be more concise without losing critical data

### Requirement 3

**User Story:** As a user analyzing commit information, I want commits_ahead split into separate columns so that I can better understand the commit relationship between forks and upstream.

#### Acceptance Criteria

1. WHEN I export CSV data THEN the "commits_ahead" column SHALL be split into two separate columns
2. WHEN I export CSV data THEN one column SHALL be named "Commits Ahead" showing the number of commits ahead
3. WHEN I export CSV data THEN another column SHALL be named "Commits Behind" showing the number of commits behind
4. WHEN a fork has no commits ahead THEN the "Commits Ahead" column SHALL show 0
5. WHEN a fork has no commits behind THEN the "Commits Behind" column SHALL show 0

### Requirement 4

**User Story:** As a user analyzing fork popularity, I want a Forks column added after the Stars column so that I can see both popularity metrics together.

#### Acceptance Criteria

1. WHEN I export CSV data THEN there SHALL be a "Forks" column positioned immediately after the "Stars" column
2. WHEN I export CSV data THEN the "Forks" column SHALL contain the number of forks for each repository
3. WHEN I export CSV data THEN the column order SHALL be: Fork URL, Stars, Forks, [other columns]
4. WHEN a repository has no forks THEN the "Forks" column SHALL show 0
5. WHEN fork count data is unavailable THEN the "Forks" column SHALL show an empty value

### Requirement 5

**User Story:** As a user working with CSV data in various tools, I want consistent column naming with proper capitalization so that the data is professional and readable.

#### Acceptance Criteria

1. WHEN I export CSV data THEN all column headers SHALL use proper title case with spaces
2. WHEN I export CSV data THEN "fork_url" SHALL become "Fork URL"
3. WHEN I export CSV data THEN "stars" SHALL become "Stars"  
4. WHEN I export CSV data THEN "commits_ahead" SHALL become "Commits Ahead"
5. WHEN I export CSV data THEN "commits_behind" SHALL become "Commits Behind"
6. WHEN I export CSV data THEN "forks_count" SHALL become "Forks"

### Requirement 6

**User Story:** As a user importing CSV data into analysis tools, I want the new column structure to maintain compatibility with existing data processing workflows while providing improved organization.

#### Acceptance Criteria

1. WHEN I export CSV data THEN the new format SHALL maintain all essential data from the original format
2. WHEN I process the CSV programmatically THEN the new column names SHALL be consistent and predictable
3. WHEN I import into spreadsheet applications THEN the column headers SHALL be immediately understandable
4. WHEN I compare data between exports THEN the core fork information SHALL remain accessible
5. WHEN I use the CSV for reporting THEN the column names SHALL be presentation-ready without modification