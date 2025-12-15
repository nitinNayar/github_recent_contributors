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
    """
    Fetch all repositories for a specified GitHub organization.

    Retrieves the complete list of repositories in a GitHub organization using
    pagination to handle organizations with large numbers of repositories.
    Includes comprehensive error handling for rate limits, permission issues,
    and invalid organization names.

    Parameters
    ----------
    org_name : str
        The name of the GitHub organization to fetch repositories from.
    headers : dict
        Dictionary containing HTTP headers for GitHub API authentication.
        Must include 'Authorization' key with valid GitHub token.

    Returns
    -------
    list of dict
        List of repository objects returned by the GitHub API. Each repository
        object contains metadata such as name, owner, URL, and other attributes.
        Returns empty list if organization has no repositories.

    Raises
    ------
    ValueError
        If the GitHub API rate limit is exceeded (403 with rate limit message).
        If access is denied due to invalid token, insufficient permissions,
        incorrect organization name, or lack of access to the organization.
        If any other HTTP error occurs (non-200 status code).

    Notes
    -----
    This function uses the GitHub REST API v3 endpoint:
    GET /orgs/{org}/repos

    The function automatically handles pagination, fetching all repositories
    across multiple pages if necessary. Progress is printed to console during
    execution.

    Examples
    --------
    >>> headers = {'Authorization': 'token ghp_xxx'}
    >>> repos = get_repos('microsoft', headers)
    >>> len(repos)
    1234
    """
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
    """
    Fetch all members of a specified GitHub organization.

    Retrieves the complete list of members in a GitHub organization using
    pagination to handle organizations with large membership counts. Member
    information is returned as a set of login usernames for efficient lookup
    operations.

    Parameters
    ----------
    org_name : str
        The name of the GitHub organization to fetch members from.
    headers : dict
        Dictionary containing HTTP headers for GitHub API authentication.
        Must include 'Authorization' key with valid GitHub token.

    Returns
    -------
    set of str
        Set containing the GitHub login usernames of all organization members.
        Returns empty set if the organization has no members or if an error
        occurs during API communication.

    Notes
    -----
    This function uses the GitHub REST API v3 endpoint:
    GET /orgs/{org}/members

    The function automatically handles pagination to retrieve all members
    across multiple pages. Unlike get_repos(), this function silently handles
    errors (returns partial results on error) rather than raising exceptions.

    The token used must have 'read:org' scope to access organization membership
    information.

    Examples
    --------
    >>> headers = {'Authorization': 'token ghp_xxx'}
    >>> members = get_organization_members('microsoft', headers)
    >>> 'octocat' in members
    True
    """
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
    """
    Analyze and retrieve contributor activity across organization repositories.

    This is the main analysis engine that processes commits across all (or filtered)
    repositories in an organization within a specified time period. It tracks both
    commit author names and GitHub usernames, providing detailed per-repository
    statistics and aggregate contributor information.

    Parameters
    ----------
    org_name : str
        The name of the GitHub organization to analyze.
    number_of_days : int
        Number of days in the past to analyze commit history. The function will
        analyze commits from (current_date - number_of_days) to current_date.
    headers : dict
        Dictionary containing HTTP headers for GitHub API authentication.
        Must include 'Authorization' key with valid GitHub token.
    interesting_repos : set of str, optional
        Optional set of repository names to filter analysis. If provided, only
        repositories matching these names (case-insensitive) will be analyzed.
        If None (default), all repositories in the organization are analyzed.

    Returns
    -------
    unique_contributors : set of str
        Set of unique commit author names found across all analyzed repositories.
        These are extracted from commit metadata and may not correspond to GitHub
        usernames.
    unique_authors : set of str
        Set of unique GitHub login usernames who authored commits in the analyzed
        repositories. These are GitHub account usernames.
    repos_detail : dict
        Dictionary mapping repository names to detailed statistics. Each entry
        contains:
        - 'repository_url' : str - HTML URL of the repository
        - 'total_commits' : int - Total number of commits in the time period
        - 'unique_contributors_count' : int - Number of unique commit authors
        - 'unique_github_authors_count' : int - Number of unique GitHub usernames
        - 'commit_authors' : dict - Mapping of author names to commit counts
        - 'github_authors' : dict - Mapping of GitHub usernames to commit counts

    Notes
    -----
    This function uses timezone-aware datetime calculations (UTC) to ensure
    accurate date range filtering regardless of local timezone.

    The distinction between 'contributors' and 'authors':
    - Contributors: Names from commit metadata (commit.author.name)
    - Authors: GitHub usernames (commit.author.login)
    These may differ due to git configuration vs GitHub account names.

    When interesting_repos filter is active, the function provides detailed
    reporting about matching/missing repositories and warns about repositories
    that couldn't be found.

    The function uses the GitHub REST API v3 endpoint:
    GET /repos/{owner}/{repo}/commits

    Progress information is printed to console during execution.

    Examples
    --------
    >>> headers = {'Authorization': 'token ghp_xxx'}
    >>> contributors, authors, details = get_contributors('microsoft', 30, headers)
    >>> len(contributors)
    542
    >>> 'typescript' in details
    True

    >>> # With repository filtering
    >>> repos_filter = {'typescript', 'vscode'}
    >>> contributors, authors, details = get_contributors('microsoft', 30, headers, repos_filter)
    >>> len(details)
    2
    """
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
    """
    Generate a comprehensive contributor activity report for a GitHub organization.

    This is the main orchestration function that coordinates the entire contributor
    analysis workflow. It fetches organization data, analyzes contributor activity,
    generates detailed reports, and saves results to both console and JSON file
    format. The output includes both organization members and external contributors.

    Parameters
    ----------
    org_name : str
        The name of the GitHub organization to analyze.
    number_of_days : int
        Number of days in the past to analyze commit history. Typical values
        are 30, 60, or 90 days.
    interesting_repos : set of str, optional
        Optional set of repository names to filter analysis. If provided, only
        these repositories will be analyzed (case-insensitive matching).
        If None (default), all repositories in the organization are analyzed.

    Returns
    -------
    None
        This function does not return a value. Results are output to console
        and saved to a JSON file in the outputs/ directory.

    Raises
    ------
    ValueError
        If GITHUB_PERSONAL_ACCESS_TOKEN environment variable is not set.
        If API requests fail due to authentication or permission issues
        (propagated from get_repos()).

    Notes
    -----
    Output File Naming:
    Files are automatically saved to outputs/ directory with the format:
    {org_name}__{unix_timestamp}__contributor_count.json

    Output Structure:
    The JSON file contains:
    - organization : str - Organization name
    - date : str - Analysis date (YYYY-MM-DD)
    - number_of_days_history : int - Lookback period
    - org_members : list - List of organization member usernames
    - commit_authors : list - List of GitHub usernames who committed
    - commiting_members : list - Intersection of commit_authors and org_members
    - repos_detail : dict - Per-repository detailed statistics

    Token Requirements:
    The GitHub Personal Access Token must have these scopes:
    - repo (or public_repo for public repositories only)
    - read:org
    - read:user
    - user:email (optional but recommended)

    Console Output:
    The function prints:
    - Progress updates during repository and commit fetching
    - Repository filtering information (if applicable)
    - Final summary statistics
    - Output file path

    Examples
    --------
    >>> # Analyze all repositories for last 30 days
    >>> report_contributors('microsoft', 30)

    >>> # Analyze specific repositories for last 90 days
    >>> repos = {'typescript', 'vscode', 'vscode-python'}
    >>> report_contributors('microsoft', 90, repos)

    See Also
    --------
    get_repos : Fetches repository list
    get_organization_members : Fetches member list
    get_contributors : Core analysis function
    """
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

