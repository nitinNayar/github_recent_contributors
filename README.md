# GitHub Recent Contributors

A Python script that fetches and analyzes recent contributor activity across repositories in a GitHub organization. The script provides detailed insights into commit authors, organization members, and per-repository contribution patterns.

## Features

### Core Functionality
- **Repository Analysis**: Fetches and analyzes all repositories from a specified GitHub organization
- **Time-based Filtering**: Analyzes commits within a specified time period (e.g., last 7, 30, or 365 days)
- **Contributor Identification**: Identifies unique contributors and their GitHub usernames
- **Member Distinction**: Distinguishes between organization members and external contributors
- **Pagination Handling**: Handles API pagination for large organizations with many repositories

### Advanced Features
- **Repository Filtering**: Analyze only specific repositories using the `INTERESTING_REPOS` filter
- **Per-Repository Tracking**: Detailed breakdown of contributors and commit counts per repository
- **Commit Count Analysis**: Track how many commits each person made to each repository
- **Auto-Generated Output**: Files automatically saved with timestamps to `outputs/` directory

### Output Options
- **Console Output**: Summary statistics and progress information
- **JSON Export**: Comprehensive data export with per-repository details

## Prerequisites

- Python 3.x
- GitHub Personal Access Token with the following permissions:
  - `repo` (or `public_repo` for public repositories only)
  - `read:org`
  - `read:user`
  - `user:email` (optional, but recommended)

## Installation

1. Clone this repository or download the script:
```bash
git clone <repository-url>
# or
wget https://raw.githubusercontent.com/<path-to>/github_recent_contributors.py
```

2. Install the required dependencies:
```bash
pip3 install requests python-dotenv
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit the `.env` file with your configuration:

### Required Variables

```bash
# Your GitHub Personal Access Token
GITHUB_PERSONAL_ACCESS_TOKEN=your_github_token_here

# The GitHub organization to analyze
GITHUB_ORG_NAME=microsoft

# Number of days to look back for contributions
NUMBER_OF_DAYS=30
```

### Optional Variables

```bash
# Filter to analyze only specific repositories (comma-separated list)
# If not set or empty, all repositories in the organization will be analyzed
# Format: Just repository names (not owner/repo format)
# Case-insensitive matching
INTERESTING_REPOS=typescript,vscode,playwright
```

### Configuration Examples

**Analyze All Repositories** (Default):
```bash
GITHUB_ORG_NAME=microsoft
NUMBER_OF_DAYS=30
# INTERESTING_REPOS not set or empty
```

**Filter Specific Repositories**:
```bash
GITHUB_ORG_NAME=microsoft
NUMBER_OF_DAYS=30
INTERESTING_REPOS=typescript,vscode,playwright
```

This will analyze only the `typescript`, `vscode`, and `playwright` repositories from Microsoft's 300+ repositories.

**Security Note:** The `.env` file is automatically excluded from git via `.gitignore` to prevent accidental token exposure. Never commit your `.env` file to version control.

## Usage

Run the script with:

```bash
python3 github_recent_contributors.py
```

All configuration is read from the `.env` file - no command line arguments needed!

### Basic Example (All Repositories)

```bash
# .env configuration
GITHUB_ORG_NAME=microsoft
NUMBER_OF_DAYS=30

# Run the script
python3 github_recent_contributors.py
```

**Output:**
```
Fetching repositories for microsoft...
Total repositories found: 342

Analyzing 342 repositories in microsoft...

Analyzing repository: microsoft/typescript
  Fetching commits page 1...
  Found 45 contributors and 43 GitHub authors in typescript
  Total commits: 150
...

✅ Output saved to: outputs/microsoft__1730131800__contributor_count.json

Total commit authors in the last 30 days: 1245
Total members in microsoft: 850
Total unique contributors from microsoft in the last 30 days: 680
```

### Repository Filtering Example

For large organizations, you may only want to analyze specific repositories:

```bash
# .env configuration
GITHUB_ORG_NAME=microsoft
NUMBER_OF_DAYS=7
INTERESTING_REPOS=typescript,vscode,playwright

# Run the script
python3 github_recent_contributors.py
```

**Output:**
```
Fetching repositories for microsoft...
Total repositories found: 342

============================================================
Repository Filtering Enabled
============================================================
Total repositories in microsoft: 342
Repositories in INTERESTING_REPOS filter: 3
Matching repositories found: 3
============================================================

Analyzing 3 repositories in microsoft...

Analyzing repository: microsoft/typescript
  Fetching commits page 1...
  Found 12 contributors and 12 GitHub authors in typescript
  Total commits: 45
...

✅ Output saved to: outputs/microsoft__1730132000__contributor_count.json

Total commit authors in the last 7 days: 38
Total members in microsoft: 850
Total unique contributors from microsoft in the last 7 days: 25
```

### Output Files

Output files are automatically generated with timestamps and saved to the `outputs/` directory:

- **Format**: `outputs/<org_name>__<unix_timestamp>__contributor_count.json`
- **Example**: `outputs/microsoft__1730131800__contributor_count.json`
- **Benefits**:
  - No manual filename configuration needed
  - Each run creates a new file (no overwriting)
  - Easy to track analysis history
  - Files are organized in one location

## Output

The script provides two types of output:

### Console Output

Shows real-time progress and summary statistics:
- Repository fetching progress
- Filtering information (if using INTERESTING_REPOS)
- Per-repository analysis progress
- Commit and contributor counts per repository
- Total statistics across all analyzed repositories
- Output file location

### JSON Output

Comprehensive data export saved to `outputs/` directory with the following structure:

#### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `organization` | string | GitHub organization name |
| `date` | string | Date of analysis (YYYY-MM-DD) |
| `number_of_days_history` | number | Time window analyzed (in days) |
| `org_members` | array | List of all organization members |
| `commit_authors` | array | List of GitHub usernames who committed |
| `commiting_members` | array | Members who also committed (intersection) |
| `repos_detail` | object | Per-repository breakdown (see below) |

#### Per-Repository Details (`repos_detail`)

For each analyzed repository:

| Field | Type | Description |
|-------|------|-------------|
| `repository_url` | string | GitHub URL to the repository |
| `total_commits` | number | Total commits in the time period |
| `unique_contributors_count` | number | Number of unique git author names |
| `unique_github_authors_count` | number | Number of unique GitHub accounts |
| `commit_authors` | object | Git author names → commit counts |
| `github_authors` | object | GitHub usernames → commit counts |

#### Example JSON Output

```json
{
  "organization": "microsoft",
  "date": "2025-10-28",
  "number_of_days_history": 30,
  "org_members": ["user1", "user2", "user3"],
  "commit_authors": ["user1", "user2", "external-contributor"],
  "commiting_members": ["user1", "user2"],

  "repos_detail": {
    "typescript": {
      "repository_url": "https://github.com/microsoft/typescript",
      "total_commits": 150,
      "unique_contributors_count": 12,
      "unique_github_authors_count": 10,
      "commit_authors": {
        "Alice Smith": 45,
        "Bob Jones": 30,
        "Charlie Brown": 25,
        "David Lee": 20
      },
      "github_authors": {
        "alice-s": 45,
        "bob-j": 30,
        "david-l": 20
      }
    },
    "vscode": {
      "repository_url": "https://github.com/microsoft/vscode",
      "total_commits": 200,
      "unique_contributors_count": 15,
      "unique_github_authors_count": 14,
      "commit_authors": {
        "Alice Smith": 60,
        "Eve Wilson": 50,
        "Frank Miller": 40
      },
      "github_authors": {
        "alice-s": 60,
        "eve-w": 50,
        "frank-m": 40
      }
    }
  }
}
```

#### Understanding Contributor Data

The script tracks two types of identities:

- **`commit_authors`**: Names from git commit metadata (e.g., "Alice Smith")
  - Always present for every commit
  - Based on git configuration (`git config user.name`)
  - May be inconsistent across commits

- **`github_authors`**: GitHub account usernames (e.g., "alice-s")
  - Only present when GitHub can link commit to an account
  - Based on email matching between commit and GitHub profile
  - Consistent and verified

**Note**: Not all commits may have a GitHub author if the commit email doesn't match any GitHub account.

## Advanced Usage

### Repository Filtering Use Cases

#### 1. Security Audits
Focus on security-critical repositories:
```bash
GITHUB_ORG_NAME=mycompany
NUMBER_OF_DAYS=90
INTERESTING_REPOS=security-toolkit,authentication-service,encryption-lib
```

#### 2. Product Team Analysis
Track contributions to specific product repositories:
```bash
GITHUB_ORG_NAME=mycompany
NUMBER_OF_DAYS=30
INTERESTING_REPOS=product-alpha,product-alpha-api,product-alpha-frontend
```

#### 3. Open Source Program Office
Monitor flagship open source projects:
```bash
GITHUB_ORG_NAME=google
NUMBER_OF_DAYS=7
INTERESTING_REPOS=tensorflow,chromium,protobuf
```

#### 4. Weekly Team Reports
Generate weekly contribution reports for active projects:
```bash
GITHUB_ORG_NAME=myteam
NUMBER_OF_DAYS=7
INTERESTING_REPOS=webapp,mobile-app,api-gateway
```

### Tips and Best Practices

1. **Case-Insensitive Matching**: Repository names are matched case-insensitively
   - `INTERESTING_REPOS=TypeScript` matches repository named `typescript`

2. **Performance**: Filtering significantly reduces execution time for large organizations
   - Analyzing 3 repos from Microsoft (342 total) takes ~30 seconds vs ~15 minutes for all repos

3. **Whitespace Handling**: Spaces around repository names are automatically trimmed
   - `INTERESTING_REPOS=repo1, repo2, repo3` works fine

4. **Missing Repositories**: The script warns you if a repository name isn't found
   - Check for typos or verify the repository exists in the organization

5. **Time Ranges**:
   - Short ranges (7 days): Good for weekly reports, faster execution
   - Medium ranges (30 days): Monthly analysis, balanced detail
   - Long ranges (365 days): Annual reports, comprehensive data

### Analyzing Per-Repository Data

The `repos_detail` section in the JSON output enables powerful analysis:

**Find most active contributors:**
```python
import json

with open('outputs/microsoft__1730131800__contributor_count.json') as f:
    data = json.load(f)

for repo, details in data['repos_detail'].items():
    top_contributor = max(details['github_authors'].items(), key=lambda x: x[1])
    print(f"{repo}: {top_contributor[0]} ({top_contributor[1]} commits)")
```

**Identify repos with most activity:**
```python
sorted_repos = sorted(
    data['repos_detail'].items(),
    key=lambda x: x[1]['total_commits'],
    reverse=True
)
print(f"Most active repo: {sorted_repos[0][0]} ({sorted_repos[0][1]['total_commits']} commits)")
```

**Track cross-repo contributors:**
```python
contributor_repos = {}
for repo, details in data['repos_detail'].items():
    for author in details['github_authors'].keys():
        if author not in contributor_repos:
            contributor_repos[author] = []
        contributor_repos[author].append(repo)

# Find people contributing to multiple repos
multi_repo_contributors = {k: v for k, v in contributor_repos.items() if len(v) > 1}
```

## Rate Limiting

The script respects GitHub API rate limits and handles pagination for:
- Repository listing
- Organization member listing
- Commit history

## Error Handling

The script includes comprehensive error handling for:

### Configuration Errors
- Missing or invalid `.env` file configuration
- Missing GitHub token or other required environment variables
- Invalid `NUMBER_OF_DAYS` value (must be an integer)

### API Errors
- Invalid API responses
- API authentication issues (invalid or expired token)
- Rate limit exceeded errors (with helpful messages)
- Access denied to private repositories

### Repository Errors
- Empty repositories (no commits in date range)
- Repositories that don't exist in the organization
- Repository filtering warnings (typos in INTERESTING_REPOS)

### Filtering Warnings

When using `INTERESTING_REPOS`, the script provides helpful feedback:

```
⚠️  Warning: The following repositories were specified but not found:
    - typscript  (typo)
    - fake-repo

Possible reasons:
  • Repository name typo
  • Repository doesn't exist in microsoft
  • Repository is private and token lacks access
```

The script continues execution with the repositories that were found.

## Contributing

Feel free to open issues or submit pull requests with improvements.

## License

[Add your chosen license here]

## Disclaimer

This tool is not officially associated with GitHub. Make sure to comply with GitHub's API terms of service and rate limiting guidelines when using this script. 