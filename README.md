# GitHub Recent Contributors

A Python script that fetches and analyzes recent contributor activity across all repositories in a GitHub organization. The script provides insights into both commit authors and organization members who have been actively contributing.

## Features

- Fetches all repositories from a specified GitHub organization
- Analyzes commits within a specified time period (e.g., last 30 days)
- Identifies unique contributors and their GitHub usernames
- Distinguishes between organization members and external contributors
- Handles API pagination for large organizations with many repositories
- Outputs results in both console and JSON format

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
```bash
# Required: Your GitHub Personal Access Token
GITHUB_PERSONAL_ACCESS_TOKEN=your_github_token_here

# Required: The GitHub organization to analyze
GITHUB_ORG_NAME=microsoft

# Required: Number of days to look back for contributions
NUMBER_OF_DAYS=30

# Required: Path to the JSON output file
OUTPUT_FILE=output.json
```

**Security Note:** The `.env` file is automatically excluded from git via `.gitignore` to prevent accidental token exposure. Never commit your `.env` file to version control.

## Usage

Run the script with:

```bash
python3 github_recent_contributors.py
```

All configuration is read from the `.env` file - no command line arguments needed!

### Example:

```bash
# After setting up your .env file with the desired organization and settings
python3 github_recent_contributors.py
```

## Output

The script provides two types of output:

1. Console output showing:
   - Total number of commit authors in the specified time period
   - Total number of organization members
   - Number of active contributors who are organization members

2. JSON file containing:
   - Organization name
   - Date of analysis
   - Number of days analyzed
   - List of organization members
   - List of commit authors
   - List of contributing members

Example JSON output:
```json
{
    "organization": "example-org",
    "date": "2024-03-20",
    "number_of_days_history": 30,
    "org_members": ["user1", "user2"],
    "commit_authors": ["user1", "user3"],
    "commiting_members": ["user1"]
}
```

## Rate Limiting

The script respects GitHub API rate limits and handles pagination for:
- Repository listing
- Organization member listing
- Commit history

## Error Handling

The script includes error handling for:
- Missing or invalid `.env` file configuration
- Missing GitHub token or other required environment variables
- Invalid API responses
- Empty repositories
- API authentication issues
- Rate limit exceeded errors

## Contributing

Feel free to open issues or submit pull requests with improvements.

## License

[Add your chosen license here]

## Disclaimer

This tool is not officially associated with GitHub. Make sure to comply with GitHub's API terms of service and rate limiting guidelines when using this script. 