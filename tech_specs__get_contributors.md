# Technical Specification: `get_contributors()` Function

**Document Version:** 1.0
**Date:** 2025-10-28
**Function Location:** `github_recent_contributors.py:99-153`

---

## Table of Contents
1. [Function Overview](#function-overview)
2. [Function Signature](#function-signature)
3. [Return Values](#return-values)
4. [Detailed Step-by-Step Analysis](#detailed-step-by-step-analysis)
5. [Key Design Patterns](#key-design-patterns)
6. [Assumptions and Edge Cases](#assumptions-and-edge-cases)
7. [Example Scenario](#example-scenario)
8. [Integration Points](#integration-points)

---

## Function Overview

The `get_contributors()` function is the core analytical engine of the GitHub Recent Contributors script. It analyzes all repositories in a GitHub organization to identify who has committed code within a specified time window.

**Primary Purpose:** Aggregate contributor data across an entire organization's repository portfolio, distinguishing between git commit author names and GitHub account usernames.

**Key Characteristic:** Implements dual identity tracking to handle the mismatch between git configuration (commit author names) and GitHub accounts (usernames).

---

## Function Signature

```python
def get_contributors(org_name, number_of_days, headers):
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `org_name` | `str` | The GitHub organization name to analyze (e.g., "microsoft", "google") |
| `number_of_days` | `int` | Time window in days to look back from current date (e.g., 30 for last month) |
| `headers` | `dict` | HTTP headers containing GitHub API authentication token |

### Example Usage
```python
headers = {'Authorization': 'token ghp_xxxxxxxxxxxx'}
contributors, authors = get_contributors("microsoft", 30, headers)
```

---

## Return Values

The function returns a tuple of two sets:

```python
return unique_contributors, unique_authors
```

### 1. `unique_contributors` (Set[str])
- **Contents:** Git commit author names from commit metadata
- **Source:** `commit['commit']['author']['name']` field in GitHub API response
- **Example Values:** `{"Alice Smith", "Bob Jones", "John Doe"}`
- **Characteristics:**
  - Always present for every commit (required by git)
  - Based on local git configuration (`git config user.name`)
  - May contain inconsistent formatting (e.g., "Alice", "alice", "A. Smith")

### 2. `unique_authors` (Set[str])
- **Contents:** GitHub usernames/login names
- **Source:** `commit['author']['login']` field in GitHub API response
- **Example Values:** `{"alice-s", "bob-jones", "jdoe123"}`
- **Characteristics:**
  - Only present when GitHub can link commit to an account
  - Based on email matching between commit and GitHub profile
  - May be missing for valid commits (unlinked accounts)
  - Consistent formatting (GitHub enforces username standards)

---

## Detailed Step-by-Step Analysis

### Step 1: Initialize Data Structures (Lines 101-102)

```python
unique_contributors = set()
unique_authors = set()
```

**Purpose:** Creates two empty sets to track contributors globally across all repositories in the organization.

**Why Sets?**
- Automatic deduplication: Same person committing to multiple repos counted once
- O(1) membership testing for efficient lookups
- Unordered collection suitable for identity tracking

**Design Decision:** Two separate sets enable dual identity tracking to handle the git/GitHub identity mismatch problem.

---

### Step 2: Fetch All Repositories (Lines 105-106)

```python
repos = get_repos(org_name, headers)
print(f"\nAnalyzing {len(repos)} repositories in {org_name}...")
```

**Purpose:** Retrieves complete inventory of all repositories in the organization.

**Implementation Details:**
- Calls `get_repos()` helper function (defined at line 39)
- Handles pagination automatically (GitHub returns max 100 repos per page)
- Includes comprehensive error handling:
  - Rate limit detection (403 with rate limit message)
  - Access denied scenarios (403 with permission errors)
  - Invalid organization names (404 errors)

**Returns:** List of repository objects containing metadata (name, owner, URLs, etc.)

---

### Step 3: Calculate Time Range (Lines 109-110)

```python
since_date = (datetime.now(UTC) - timedelta(days=number_of_days)).isoformat()
until_date = datetime.now(UTC).isoformat()
```

**Purpose:** Defines the temporal window for commit analysis using timezone-aware timestamps.

**Breakdown:**
1. `datetime.now(UTC)` - Current time in UTC timezone
2. `timedelta(days=number_of_days)` - Duration object representing N days
3. Subtraction yields starting timestamp
4. `.isoformat()` - Converts to ISO 8601 format (e.g., "2025-09-28T10:30:00+00:00")

**Why UTC?**
- Eliminates timezone ambiguities
- Consistent behavior regardless of script execution location
- Matches GitHub's internal timestamp handling

**API Compatibility:** GitHub API requires ISO 8601 formatted dates for `since` and `until` parameters.

**Example:**
- If run on 2025-10-28 with `number_of_days=7`:
  - `since_date = "2025-10-21T00:00:00+00:00"`
  - `until_date = "2025-10-28T00:00:00+00:00"`

---

### Step 4: Main Repository Loop (Lines 113-151)

This is the core processing section with nested loops for repos and commits.

#### 4a: Extract Repository Information (Lines 114-117)

```python
for repo in repos:
    owner = repo['owner']['login']
    repo_name = repo['name']
    repo_contributors = set()
    repo_authors = set()
```

**Purpose:** Initializes per-repository tracking and extracts metadata.

**Variables:**
- `owner` - Repository owner username (could be org or user account)
- `repo_name` - Repository name (e.g., "react", "typescript")
- `repo_contributors` - Per-repo set for commit author names
- `repo_authors` - Per-repo set for GitHub usernames

**Why Per-Repository Sets?**
1. Enables per-repository statistics/reporting
2. Makes code logic clearer and more modular
3. Facilitates debugging by isolating repository-specific issues

---

#### 4b: Pagination Loop for Commits (Lines 122-129)

```python
page = 1
while True:
    print(f"  Fetching commits page {page}...")
    response = requests.get(
        f'https://api.github.com/repos/{owner}/{repo_name}/commits',
        params={'since': since_date, 'until': until_date, 'page': page},
        headers=headers
    )
```

**Purpose:** Fetches all commits within the date range using paginated API requests.

**API Endpoint:** `GET /repos/{owner}/{repo}/commits`

**Query Parameters:**
- `since` - ISO 8601 timestamp (inclusive start)
- `until` - ISO 8601 timestamp (inclusive end)
- `page` - Page number (1-indexed)

**Pagination Strategy:**
- GitHub returns 30 commits per page by default
- Loop continues until empty page received
- Ensures complete commit history coverage

**Example API Call:**
```
GET https://api.github.com/repos/microsoft/typescript/commits?since=2025-09-28T00:00:00Z&until=2025-10-28T00:00:00Z&page=1
```

---

#### 4c: Error Handling (Lines 131-138)

```python
commits_page = response.json()

if not isinstance(commits_page, list):
    print(f"  Warning: Repo {repo_name} is empty or error occurred.")
    break

if not commits_page:
    break
```

**Purpose:** Handles edge cases and determines pagination termination.

**Check 1: Type Validation**
```python
if not isinstance(commits_page, list):
```
- **Expected:** JSON array of commit objects
- **Unexpected:** JSON object (error message or empty repo indicator)
- **Action:** Print warning and skip to next repository

**Common Causes:**
- Empty repository (no commits)
- Private repository without access
- API error response (rate limit, server error)

**Check 2: Empty Page Detection**
```python
if not commits_page:
```
- **Condition:** List is empty (`[]`)
- **Meaning:** No more commits available (end of pagination)
- **Action:** Exit pagination loop, proceed to next repository

---

#### 4d: Extract Contributor Information (Lines 140-143)

```python
for commit in commits_page:
    repo_contributors.add(commit['commit']['author']['name'])
    if commit['author']:
        repo_authors.add(commit['author']['login'])
```

**Purpose:** Extracts dual identity information from each commit object.

**Critical Data Structure Understanding:**

A GitHub commit API response has this structure:
```json
{
  "commit": {
    "author": {
      "name": "Alice Smith",         // Git commit author name
      "email": "alice@example.com",
      "date": "2025-10-28T10:30:00Z"
    },
    "message": "Fix bug in parser"
  },
  "author": {                        // GitHub user object (may be null)
    "login": "alice-s",              // GitHub username
    "id": 12345,
    "avatar_url": "..."
  }
}
```

**Extraction 1: Git Commit Author Name**
```python
repo_contributors.add(commit['commit']['author']['name'])
```
- **Path:** `commit.commit.author.name`
- **Source:** Git commit metadata/signature
- **Always Present:** Yes (required by git protocol)
- **Configured By:** `git config user.name` on committer's machine
- **Examples:** "John Doe", "j.doe", "John D.", "jdoe@company.com"

**Extraction 2: GitHub Username**
```python
if commit['author']:
    repo_authors.add(commit['author']['login'])
```
- **Path:** `commit.author.login`
- **Source:** GitHub's user database
- **Always Present:** No (conditional check required)
- **Determined By:** Email matching algorithm
- **Examples:** "johndoe", "jdoe123", "john-d"

**Why the Conditional Check?**

`commit['author']` can be `null` when:
1. Commit email doesn't match any GitHub account
2. GitHub account was deleted after commit
3. Company/private email not linked to GitHub profile
4. Commit made before GitHub account creation

**Critical Insight:** This dual tracking handles the fundamental mismatch between:
- **Git's Identity Model:** Configured author names (arbitrary strings)
- **GitHub's Identity Model:** Account-based usernames (verified identities)

---

#### 4e: Increment Page Counter (Line 145)

```python
page += 1
```

**Purpose:** Advances to next page of commits in pagination sequence.

**Flow Control:**
- Continues until `commits_page` is empty
- Handles repositories with hundreds/thousands of commits
- Prevents infinite loops via API's empty page response

---

#### 4f: Merge Repository Results (Lines 148-151)

```python
unique_contributors.update(repo_contributors)
unique_authors.update(repo_authors)

print(f"  Found {len(repo_contributors)} contributors and {len(repo_authors)} GitHub authors in {repo_name}")
```

**Purpose:** Aggregates repository-specific contributors into organization-wide sets.

**Set Operations:**
- `unique_contributors.update(repo_contributors)` - Merges repo contributors into global set
- `unique_authors.update(repo_authors)` - Merges repo authors into global set
- `update()` method adds elements, automatically handling duplicates

**Progress Reporting:**
- Prints per-repository statistics
- Helps track progress through large organizations
- Aids debugging (identify problematic repositories)

**Important Note:** Repository counts may sum to more than global counts due to cross-repository contributors (same person appearing in multiple repos).

---

### Step 5: Return Results (Line 153)

```python
return unique_contributors, unique_authors
```

**Purpose:** Returns both contributor sets to calling function (`report_contributors()`).

**Usage by Caller:**
```python
unique_contributors, unique_authors = get_contributors(org_name, number_of_days, headers)
```

The caller then:
1. Compares `unique_authors` with organization members
2. Generates JSON output
3. Prints summary statistics

---

## Key Design Patterns

### 1. Dual Identity Tracking Pattern

**Problem:** Git commit author names don't reliably map to GitHub accounts.

**Solution:** Track both identity systems simultaneously:
- Git metadata (always available, inconsistent)
- GitHub accounts (may be unavailable, but verified)

**Benefit:** Comprehensive contributor analysis without losing data.

---

### 2. Nested Pagination Pattern

**Structure:**
```
for each repository:
    page = 1
    while commits available:
        fetch commits page
        process commits
        page++
```

**Purpose:** Handles arbitrary data volumes without memory constraints.

**Complexity:** O(R × P) where R = repositories, P = pages per repo

---

### 3. Local-Then-Global Aggregation Pattern

**Flow:**
1. Repository-specific sets (`repo_contributors`, `repo_authors`)
2. Merge into organization-wide sets (`unique_contributors`, `unique_authors`)

**Benefits:**
- Modular code structure
- Per-repository reporting
- Easier debugging and testing

---

### 4. Defensive API Consumption Pattern

**Techniques:**
- Type checking (`isinstance(commits_page, list)`)
- Null checking (`if commit['author']:`)
- Empty response detection (`if not commits_page:`)

**Result:** Robust handling of API edge cases and errors.

---

## Assumptions and Edge Cases

### Assumptions

1. **GitHub API Availability**
   - Assumes API is accessible and responsive
   - Assumes rate limits are not exceeded (handled in `get_repos()`)

2. **Token Permissions**
   - Assumes token has necessary scopes (`repo`, `read:org`)
   - Assumes token is valid and not expired

3. **Data Consistency**
   - Assumes repository list doesn't change during execution
   - Assumes commit history is immutable (valid assumption for git)

4. **Pagination Reliability**
   - Assumes empty page signals end of data
   - Assumes page ordering is consistent

5. **Timezone Handling**
   - Assumes UTC timestamps are acceptable for all use cases
   - Assumes GitHub interprets ISO 8601 dates correctly

### Edge Cases Handled

1. **Empty Repositories**
   - Detection: `not isinstance(commits_page, list)`
   - Handling: Print warning, skip to next repo

2. **Unlinked Commits**
   - Detection: `commit['author']` is `None`
   - Handling: Skip GitHub username extraction, only record git author name

3. **No Commits in Date Range**
   - Detection: First page is empty list
   - Handling: Break pagination loop, proceed to next repo

4. **Large Repositories**
   - Detection: Many pagination cycles
   - Handling: Automatic pagination until exhausted

### Edge Cases NOT Explicitly Handled

1. **Rate Limiting During Commit Fetching**
   - Current code: No rate limit checking in commit loop
   - Risk: Could hit rate limits on large repos
   - Mitigation: Rely on external rate limit handling or manual retry

2. **Network Failures**
   - Current code: No retry logic for failed requests
   - Risk: Transient failures could skip repositories
   - Mitigation: Rely on exceptions bubbling up to caller

3. **Extremely Large Result Sets**
   - Current code: All data held in memory
   - Risk: Memory exhaustion on organizations with thousands of contributors
   - Mitigation: Sets are relatively memory-efficient; unlikely to be problem

---

## Example Scenario

### Scenario Setup

**Organization:** "TechCorp"
**Repositories:** 2 repos (repo-a, repo-b)
**Time Range:** Last 30 days
**Total Commits:** 5 commits across both repos

### Commit Data

**Repository A** - 3 commits:

| Commit | Git Author Name | Git Email | GitHub Username |
|--------|----------------|-----------|-----------------|
| Commit 1 | Alice Smith | alice@tech.com | alice-s |
| Commit 2 | Bob Jones | bob@personal.com | bob-j |
| Commit 3 | Charlie Brown | charlie@external.com | None (no GitHub account linked) |

**Repository B** - 2 commits:

| Commit | Git Author Name | Git Email | GitHub Username |
|--------|----------------|-----------|-----------------|
| Commit 4 | Alice Smith | alice@tech.com | alice-s (same person as Commit 1) |
| Commit 5 | David Lee | david@tech.com | david-l |

### Execution Flow

#### Processing Repository A

```python
repo_contributors = set()  # Empty
repo_authors = set()       # Empty

# Commit 1
repo_contributors.add("Alice Smith")  # {"Alice Smith"}
repo_authors.add("alice-s")           # {"alice-s"}

# Commit 2
repo_contributors.add("Bob Jones")    # {"Alice Smith", "Bob Jones"}
repo_authors.add("bob-j")             # {"alice-s", "bob-j"}

# Commit 3
repo_contributors.add("Charlie Brown") # {"Alice Smith", "Bob Jones", "Charlie Brown"}
# commit['author'] is None, so no GitHub username added
repo_authors                           # {"alice-s", "bob-j"} (unchanged)

# Merge to global
unique_contributors = {"Alice Smith", "Bob Jones", "Charlie Brown"}
unique_authors = {"alice-s", "bob-j"}
```

**Repository A Statistics:**
- 3 commit author names
- 2 GitHub usernames

#### Processing Repository B

```python
repo_contributors = set()  # Reset for new repo
repo_authors = set()       # Reset for new repo

# Commit 4 (Alice Smith again)
repo_contributors.add("Alice Smith")  # {"Alice Smith"}
repo_authors.add("alice-s")           # {"alice-s"}

# Commit 5
repo_contributors.add("David Lee")    # {"Alice Smith", "David Lee"}
repo_authors.add("david-l")           # {"alice-s", "david-l"}

# Merge to global (sets automatically handle duplicates)
unique_contributors.update({"Alice Smith", "David Lee"})
# Result: {"Alice Smith", "Bob Jones", "Charlie Brown", "David Lee"}

unique_authors.update({"alice-s", "david-l"})
# Result: {"alice-s", "bob-j", "david-l"}
```

**Repository B Statistics:**
- 2 commit author names
- 2 GitHub usernames

### Final Results

```python
unique_contributors = {
    "Alice Smith",
    "Bob Jones",
    "Charlie Brown",
    "David Lee"
}
# Total: 4 unique commit author names

unique_authors = {
    "alice-s",
    "bob-j",
    "david-l"
}
# Total: 3 unique GitHub usernames
```

### Key Observations

1. **Deduplication:** Alice Smith appears in both repos but only counted once
2. **Missing GitHub Account:** Charlie Brown has no GitHub username in results
3. **Per-Repo vs Global:** Repo counts (3+2=5 authors) > Global count (4 authors)
4. **Identity Mismatch:** 4 git author names but only 3 GitHub accounts

### Downstream Usage

The `report_contributors()` function would then:

```python
org_members = {"alice-s", "david-l"}  # Example org members

commiting_members = unique_authors & org_members
# Result: {"alice-s", "david-l"}

external_contributors = unique_authors - org_members
# Result: {"bob-j"}
```

This enables analysis of:
- How many org members contributed (2)
- How many external contributors contributed (1)
- Who is contributing but not in org (Bob)

---

## Integration Points

### Called By
- `report_contributors()` function (line 163)
  ```python
  unique_contributors, unique_authors = get_contributors(org_name, number_of_days, headers)
  ```

### Depends On
- `get_repos()` function (line 39) - Repository fetching
- `requests` library - HTTP requests to GitHub API
- `datetime` module - Time calculations

### Outputs Used By
- JSON export functionality (line 171) - `commit_authors` field
- Intersection calculation (line 172) - `commiting_members` analysis
- Console reporting (line 179-181) - Summary statistics

### Error Handling Chain
- Function itself: Minimal error handling (prints warnings)
- Relies on `get_repos()` for comprehensive error handling
- Expects caller to handle exceptions from `requests` library

---

## Performance Considerations

### Time Complexity
- **Best Case:** O(R) where R = number of repositories (all repos empty)
- **Average Case:** O(R × C) where C = average commits per repo in date range
- **Worst Case:** O(R × C × P) where P = pagination factor (30 commits per page)

### Space Complexity
- **Contributor Sets:** O(U) where U = unique contributors across org
- **Temporary Storage:** O(C_max) where C_max = commits in largest repo
- **Total:** O(U + C_max) - dominated by unique contributor count

### API Rate Limits
- **Commits Endpoint:** 5,000 requests/hour for authenticated requests
- **Risk:** Large orgs with many repos can approach limit
- **Mitigation:** Implemented in `get_repos()`, not in this function

### Optimization Opportunities
1. Parallel repository processing (currently sequential)
2. Caching of repository commit counts (avoid unnecessary pagination)
3. Streaming JSON parsing for large commit pages
4. Rate limit backoff/retry logic in commit fetching

---

## Testing Recommendations

### Unit Test Cases

1. **Empty Organization**
   - Input: Organization with 0 repositories
   - Expected: Empty sets returned

2. **Single Repository, Single Commit**
   - Input: 1 repo, 1 commit with both git name and GitHub username
   - Expected: Both sets contain 1 entry

3. **Commit Without GitHub Account**
   - Input: Commit where `commit['author']` is `None`
   - Expected: Git name in `unique_contributors`, nothing in `unique_authors`

4. **Cross-Repository Duplicate**
   - Input: Same person commits to 2 different repos
   - Expected: Single entry in both sets (deduplication)

5. **Pagination Handling**
   - Input: Repository with >30 commits in date range
   - Expected: All commits processed across multiple pages

6. **Date Range Filtering**
   - Input: Repository with commits both inside and outside date range
   - Expected: Only commits within range counted (verify via GitHub API)

### Integration Test Cases

1. **Real Organization Analysis**
   - Use small public organization
   - Verify counts match manual inspection

2. **Rate Limit Recovery**
   - Trigger rate limit
   - Verify graceful handling

3. **Private Repository Access**
   - Test with repos token can't access
   - Verify error messages

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-28 | Technical Documentation | Initial specification document |

---

## References

- GitHub API Documentation: https://docs.github.com/en/rest/commits/commits
- ISO 8601 Date Format: https://en.wikipedia.org/wiki/ISO_8601
- Python datetime module: https://docs.python.org/3/library/datetime.html
- Python sets: https://docs.python.org/3/library/stdtypes.html#set-types-set-frozenset
