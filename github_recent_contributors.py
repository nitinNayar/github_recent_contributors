"""
GitHub Recent Contributors Script
---------------------------------
This script fetches and prints the unique contributors from the last 30 days
across all the repositories in a specified GitHub organization.

Directions:
1. Save this script as `github_recent_contributors.py` in a directory of your choice.
2. Open a terminal and navigate to the directory where this script is saved.
3. Install the required Python libraries: `pip3 install requests python-dotenv`
4. Create a .env file with required configuration (see .env.example for template)
5. Run the script with: `python3 github_recent_contributors.py`

Requirements:
- Python 3.x
- A GitHub Personal Access Token

GitHub Permissions Needed:
- repo (or public_repo for public repositories)
- read:org
- read:user
- user:email (optional, but recommended)

Before Running:
- Create a .env file with all required variables (GITHUB_PERSONAL_ACCESS_TOKEN, GITHUB_ORG_NAME, NUMBER_OF_DAYS)
- Ensure your token has the necessary scopes and permissions.
- Output files are automatically saved to outputs/ directory with auto-generated filenames

Note:
- Keep your tokens secure and never expose them in client-side code or public repositories.
- Add .env to your .gitignore file to prevent accidental token exposure.
"""
import requests
import os
import time
from datetime import datetime, timedelta, UTC
import json
from dotenv import load_dotenv


def get_repos(org_name, headers):
    """Fetch all repositories for the given organization."""
    repos = []
    page = 1
    print(f"\nFetching repositories for {org_name}...")
    while True:
        print(f"  Fetching repositories page {page}...")
        response = requests.get(
            f'https://api.github.com/orgs/{org_name}/repos?page={page}',
            headers=headers
        )
        
        if response.status_code == 403:
            error_message = response.json().get('message', 'Unknown error')
            if 'rate limit exceeded' in error_message.lower():
                raise ValueError(
                    f"GitHub API rate limit exceeded. Please wait before trying again.\n"
                    f"Error message: {error_message}"
                )
            else:
                raise ValueError(
                    f"Access denied (403) when fetching repositories for organization {org_name}.\n"
                    f"Possible causes:\n"
                    f"1. The GitHub token is invalid or expired\n"
                    f"2. The token doesn't have sufficient permissions (needs 'repo' or 'public_repo' scope)\n"
                    f"3. The organization name '{org_name}' is incorrect\n"
                    f"4. The token doesn't have access to this organization\n"
                    f"Error message: {error_message}"
                )
        elif response.status_code != 200:
            raise ValueError(f"Error fetching repositories for organization {org_name}. Status code: {response.status_code}")
        
        repos_page = response.json()
        if not repos_page:
            break
        repos.extend(repos_page)
        print(f"  Found {len(repos_page)} repositories on page {page}")
        page += 1
    
    print(f"Total repositories found: {len(repos)}")
    return repos

def get_organization_members(org_name, headers):
    """Fetch all members of the organization."""
    members = []
    page = 1
    while True:
        response = requests.get(
            f'https://api.github.com/orgs/{org_name}/members?page={page}',
            headers=headers
        )
        if response.status_code != 200:
            break
        members_page = response.json()
        if not members_page:
            break
        members.extend(members_page)
        page += 1
    return {member['login'] for member in members}

def get_contributors(org_name, number_of_days, headers, interesting_repos=None):
    # init contributor set
    unique_contributors = set()
    unique_authors = set()
    repos_detail = {}  # Track per-repository contributor details

    # Fetch all repositories in the organization
    repos = get_repos(org_name, headers)

    # Filter repositories if interesting_repos is specified
    if interesting_repos:
        original_count = len(repos)

        # Create case-insensitive lookup set
        interesting_repos_lower = {name.lower() for name in interesting_repos}

        # Filter repos by name (case-insensitive exact match)
        filtered_repos = [
            repo for repo in repos
            if repo['name'].lower() in interesting_repos_lower
        ]

        # Report filtering results
        print(f"\n{'='*60}")
        print(f"Repository Filtering Enabled")
        print(f"{'='*60}")
        print(f"Total repositories in {org_name}: {original_count}")
        print(f"Repositories in INTERESTING_REPOS filter: {len(interesting_repos)}")
        print(f"Matching repositories found: {len(filtered_repos)}")

        # Check for repos that were requested but not found
        found_repo_names = {repo['name'].lower() for repo in filtered_repos}
        missing_repos = interesting_repos_lower - found_repo_names

        if missing_repos:
            print(f"\n⚠️  Warning: The following repositories were specified but not found:")
            for repo in sorted(missing_repos):
                # Find original case from user input for better error messages
                original_name = next(
                    (r for r in interesting_repos if r.lower() == repo),
                    repo
                )
                print(f"    - {original_name}")
            print(f"\nPossible reasons:")
            print(f"  • Repository name typo")
            print(f"  • Repository doesn't exist in {org_name}")
            print(f"  • Repository is private and token lacks access")

        # Replace repos list with filtered list
        repos = filtered_repos

        # Handle edge case: no matching repos
        if not repos:
            print(f"\n❌ Error: No matching repositories found.")
            print(f"Please check your INTERESTING_REPOS configuration.\n")
            return set(), set(), {}  # Return empty sets and empty repos_detail

        print(f"{'='*60}\n")

    print(f"\nAnalyzing {len(repos)} repositories in {org_name}...")

    # Date range calculation using timezone-aware datetime
    since_date = (datetime.now(UTC) - timedelta(days=number_of_days)).isoformat()
    until_date = datetime.now(UTC).isoformat()

    # Loop through each repository in the organization
    for repo in repos:
        owner = repo['owner']['login']
        repo_name = repo['name']
        repo_contributors = {}  # Track contributor names with commit counts
        repo_authors = {}  # Track GitHub usernames with commit counts
        total_commits = 0  # Track total commits for this repository
        
        print(f"\nAnalyzing repository: {owner}/{repo_name}")
        
        # Fetch commits for each repository in the given date range with pagination
        page = 1
        while True:
            print(f"  Fetching commits page {page}...")
            response = requests.get(
                f'https://api.github.com/repos/{owner}/{repo_name}/commits',
                params={'since': since_date, 'until': until_date, 'page': page},
                headers=headers
            )
            
            commits_page = response.json()

            if not isinstance(commits_page, list):
                print(f"  Warning: Repo {repo_name} is empty or error occurred.")
                break

            if not commits_page:
                break

            for commit in commits_page:
                total_commits += 1

                # Track commit author with count
                author_name = commit['commit']['author']['name']
                repo_contributors[author_name] = repo_contributors.get(author_name, 0) + 1

                # Track GitHub author with count
                if commit['author']:
                    github_login = commit['author']['login']
                    repo_authors[github_login] = repo_authors.get(github_login, 0) + 1
            
            page += 1
        
        # Build repos_detail entry for this repository
        repos_detail[repo_name] = {
            "repository_url": repo['html_url'],
            "total_commits": total_commits,
            "unique_contributors_count": len(repo_contributors),
            "unique_github_authors_count": len(repo_authors),
            "commit_authors": repo_contributors,
            "github_authors": repo_authors
        }

        # Update global sets (use .keys() since now dicts)
        unique_contributors.update(repo_contributors.keys())
        unique_authors.update(repo_authors.keys())

        print(f"  Found {len(repo_contributors)} contributors and {len(repo_authors)} GitHub authors in {repo_name}")
        print(f"  Total commits: {total_commits}")

    return unique_contributors, unique_authors, repos_detail

def report_contributors(org_name, number_of_days, interesting_repos=None):
    # init github auth
    token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not token:
        raise ValueError("Please set your GITHUB_PERSONAL_ACCESS_TOKEN as an environment variable.")
    headers = {'Authorization': f'token {token}'}

    org_members = get_organization_members(org_name, headers)
    unique_contributors, unique_authors, repos_detail = get_contributors(org_name, number_of_days, headers, interesting_repos)

    # Generate output filename with org name and unix timestamp
    timestamp = int(time.time())
    output_filename = f"{org_name}__{timestamp}__contributor_count.json"

    # Create outputs directory if it doesn't exist
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)

    # Full output path
    output_path = os.path.join(output_dir, output_filename)

    # Write JSON output
    output_data = {
        "organization": org_name,
        "date": datetime.today().date().strftime('%Y-%m-%d'),
        "number_of_days_history": number_of_days,
        "org_members": list(org_members),
        "commit_authors": list(unique_authors),
        "commiting_members": list(unique_authors & org_members),
        "repos_detail": repos_detail
    }

    with open(output_path, 'w') as file:
        json.dump(output_data, file, indent=2)

    print(f"\n✅ Output saved to: {output_path}")

    # Print unique contributors and their total count        
    print(f"Total commit authors in the last {number_of_days} days:", len(unique_authors))
    print(f"Total members in {org_name}:", len(org_members))
    print(f"Total unique contributors from {org_name} in the last {number_of_days} days:", len(unique_authors & org_members))

if __name__ == '__main__':
    # Load environment variables from .env file
    load_dotenv()

    # Get required variables from environment
    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    org_name = os.getenv("GITHUB_ORG_NAME")
    number_of_days_str = os.getenv("NUMBER_OF_DAYS")

    # Get optional INTERESTING_REPOS configuration
    interesting_repos_str = os.getenv("INTERESTING_REPOS", "")

    # Parse interesting_repos (optional - can be empty)
    interesting_repos = None
    if interesting_repos_str and interesting_repos_str.strip():
        # Split by comma, strip whitespace, filter empty strings, convert to set for fast lookup
        interesting_repos = {
            repo.strip()
            for repo in interesting_repos_str.split(',')
            if repo.strip()
        }

    # Validate required variables
    missing_vars = []
    if not token:
        missing_vars.append("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not org_name:
        missing_vars.append("GITHUB_ORG_NAME")
    if not number_of_days_str:
        missing_vars.append("NUMBER_OF_DAYS")

    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            f"Please create a .env file with all required variables. See .env.example for template."
        )

    # Type narrowing for type checker
    assert number_of_days_str is not None, "NUMBER_OF_DAYS should not be None after validation"

    # Convert number_of_days to integer
    try:
        number_of_days = int(number_of_days_str)
    except ValueError:
        raise ValueError(f"NUMBER_OF_DAYS must be an integer, got: {number_of_days_str}")

    # Run the script
    report_contributors(org_name, number_of_days, interesting_repos)

