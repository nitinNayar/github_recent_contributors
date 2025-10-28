# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python script that analyzes GitHub organization contributor activity by fetching commit data across all repositories in an organization over a specified time period. The script identifies both organization members and external contributors, then outputs the results in both console and JSON format.

## Key Commands

### Installation
```bash
pip3 install requests python-dotenv
```

### Configuration
1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and set your values:
```bash
GITHUB_PERSONAL_ACCESS_TOKEN=your_github_token_here
GITHUB_ORG_NAME=microsoft
NUMBER_OF_DAYS=30
OUTPUT_FILE=output.json
```

### Running the Script
```bash
python3 github_recent_contributors.py
```

All configuration is read from the `.env` file - no command line arguments needed.

## Architecture

### Main Entry Point
The script loads configuration from `.env` file and operates through `report_contributors()` in github_recent_contributors.py, which orchestrates the entire analysis workflow.

### Core Functions

**Repository Fetching** (`get_repos()` at :38)
- Handles pagination to retrieve all repositories from an organization
- Includes comprehensive error handling for rate limits and permissions
- Returns list of repository objects

**Organization Members** (`get_organization_members()` at :80)
- Fetches all members of the organization with pagination
- Returns a set of member login names for fast lookup

**Contributor Analysis** (`get_contributors()` at :98)
- Main analysis engine that processes commits across all repositories
- Uses timezone-aware datetime for accurate date range calculations (UTC)
- Implements pagination for commit history
- Tracks two separate sets:
  - `unique_contributors`: Commit author names (from commit metadata)
  - `unique_authors`: GitHub usernames (from author objects)
- The distinction is important because commit author names may not match GitHub usernames

### Data Flow

1. Authenticate with GitHub token from environment variable
2. Fetch organization members (for comparison)
3. Fetch all repositories in the organization
4. For each repository:
   - Fetch commits within the date range using `since` and `until` parameters
   - Extract both commit author names and GitHub usernames
   - Handle pagination and empty repositories
5. Calculate intersection between commit authors and organization members
6. Output results to console and JSON file

### API Interaction

The script uses GitHub REST API v3 with:
- Organization repos endpoint: `/orgs/{org}/repos`
- Organization members endpoint: `/orgs/{org}/members`
- Repository commits endpoint: `/repos/{owner}/{repo}/commits`

All requests use token-based authentication via the Authorization header.

### Error Handling

The script includes specific error handling for:
- Missing GitHub token (raises ValueError)
- Rate limit exceeded (403 with specific message)
- Access denied scenarios (403 with detailed diagnostics)
- Invalid API responses (non-200 status codes)
- Empty or inaccessible repositories

## GitHub Token Requirements

The token (configured in `.env` file) must have these permissions:
- `repo` (or `public_repo` for public repos only)
- `read:org`
- `read:user`
- `user:email` (optional but recommended)

**Security Note:** The `.env` file is automatically excluded from git via `.gitignore` to prevent accidental token exposure.

## Output Format

JSON output contains:
- `organization`: Name of the analyzed organization
- `date`: Date of analysis (YYYY-MM-DD)
- `number_of_days_history`: Lookback period
- `org_members`: List of all organization members
- `commit_authors`: List of GitHub usernames who committed
- `commiting_members`: Intersection of authors and members
