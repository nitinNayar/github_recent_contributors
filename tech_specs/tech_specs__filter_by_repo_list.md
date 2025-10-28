# Technical Specification: Repository Filtering Feature (INTERESTING_REPOS)

**Document Version:** 1.0
**Date:** 2025-10-28
**Feature Type:** Enhancement
**Status:** Approved for Implementation

---

## Table of Contents
1. [Feature Overview](#feature-overview)
2. [Motivation and Use Cases](#motivation-and-use-cases)
3. [Design Decisions](#design-decisions)
4. [Implementation Details](#implementation-details)
5. [Configuration Format](#configuration-format)
6. [Behavior Specification](#behavior-specification)
7. [Edge Cases](#edge-cases)
8. [Example Scenarios](#example-scenarios)
9. [Testing Strategy](#testing-strategy)
10. [Migration Guide](#migration-guide)

---

## Feature Overview

### Summary
Add an optional repository filter mechanism that allows users to analyze contributors from only a subset of repositories within an organization, rather than analyzing all repositories.

### Current Behavior
The script analyzes **all repositories** in a specified GitHub organization to identify contributors.

### New Behavior
The script can optionally filter repositories by name, analyzing only those specified in the `INTERESTING_REPOS` configuration variable.

### Backward Compatibility
✅ **Fully backward compatible** - Existing users who don't set `INTERESTING_REPOS` will see no change in behavior.

---

## Motivation and Use Cases

### Problem Statement
Large organizations (e.g., Microsoft, Google, Meta) have hundreds or thousands of repositories. Analyzing all of them is:
- **Time-consuming**: API rate limits and processing time
- **Resource-intensive**: Unnecessary API calls for irrelevant repos
- **Unfocused**: Results include contributors from repos the user doesn't care about

### Target Users
1. **Security teams**: Track contributors to critical security repos only
2. **Product teams**: Monitor specific product repositories
3. **Open source managers**: Focus on flagship projects
4. **Auditors**: Analyze compliance for specific repos

### Example Scenarios

**Scenario 1: Security Audit**
```
Organization: microsoft (342 repos)
Focus: Security-critical repos only
Filter: azure-security, defender, security-toolkit
Result: 15 contributors instead of 1,200+
```

**Scenario 2: Product Development**
```
Organization: facebook (500+ repos)
Focus: React ecosystem
Filter: react, react-native, metro
Result: Track React team contributors specifically
```

**Scenario 3: Open Source Program Office**
```
Organization: google (1000+ repos)
Focus: Flagship projects
Filter: chromium, v8, protobuf, tensorflow
Result: Monitor key project activity
```

---

## Design Decisions

### Decision Matrix

| Aspect | Options Considered | Selected | Rationale |
|--------|-------------------|----------|-----------|
| **Input Source** | CLI args, .env file, config file | **.env file** | Consistent with existing config pattern |
| **Format** | Comma-separated, space-separated, JSON | **Comma-separated** | Most common .env convention |
| **Requirement** | Required, optional | **Optional** | Backward compatibility |
| **Matching** | Case-sensitive, case-insensitive, fuzzy | **Case-insensitive exact** | User-friendly but predictable |
| **Error Handling** | Fail hard, warn and continue, silent ignore | **Warn and continue** | Resilient to typos |
| **Scope** | Repo name only, owner/repo format | **Repo name only** | Org already specified |

---

## Implementation Details

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ User Configuration (.env)                                    │
│ INTERESTING_REPOS=repo1,repo2,repo3                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ Main Script (Environment Loading)                           │
│ - Load INTERESTING_REPOS from environment                   │
│ - Parse comma-separated list                                │
│ - Convert to set for O(1) lookup                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ report_contributors(org, days, output, interesting_repos)   │
│ - Pass filter to get_contributors()                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ get_contributors(org, days, headers, interesting_repos)     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 1. Fetch all repos from GitHub API                      │ │
│ │    repos = get_repos(org_name, headers)                 │ │
│ └─────────────────────┬───────────────────────────────────┘ │
│                       ▼                                       │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 2. Apply filter if interesting_repos is provided        │ │
│ │    if interesting_repos:                                │ │
│ │        - Create case-insensitive lookup set             │ │
│ │        - Filter repos by name matching                  │ │
│ │        - Identify missing repos (requested but not found)│ │
│ │        - Print filtering statistics                     │ │
│ │        - Update repos list                              │ │
│ └─────────────────────┬───────────────────────────────────┘ │
│                       ▼                                       │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 3. Process filtered/all repos (existing logic)          │ │
│ │    for repo in repos:                                   │ │
│ │        analyze commits...                               │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Component Changes

#### 1. Environment Variable Parsing (Main Block)

**Location:** `github_recent_contributors.py` lines ~190-195

**New Code:**
```python
# Get optional INTERESTING_REPOS configuration
interesting_repos_str = os.getenv("INTERESTING_REPOS", "")

# Parse interesting_repos (optional - can be empty)
interesting_repos = None
if interesting_repos_str and interesting_repos_str.strip():
    # Split by comma, strip whitespace, filter empty strings, convert to set
    interesting_repos = {
        repo.strip()
        for repo in interesting_repos_str.split(',')
        if repo.strip()
    }
```

**Logic Breakdown:**
1. Read `INTERESTING_REPOS` from environment (default to empty string if not set)
2. Check if the value is non-empty after stripping whitespace
3. Split by comma into list of repo names
4. Strip whitespace from each repo name
5. Filter out any empty strings (handles trailing commas)
6. Convert to set for O(1) lookup performance
7. If no valid repos specified, set to `None` (signals "no filter")

**Time Complexity:** O(n) where n = number of repos in filter list (typically small, <10)

#### 2. Function Signature Updates

**Update `report_contributors()` - Line 155:**
```python
def report_contributors(org_name, number_of_days, output_file, interesting_repos=None):
    # ... existing code ...
    unique_contributors, unique_authors = get_contributors(
        org_name,
        number_of_days,
        headers,
        interesting_repos  # NEW: Pass filter parameter
    )
    # ... rest of function unchanged ...
```

**Update `get_contributors()` - Line 99:**
```python
def get_contributors(org_name, number_of_days, headers, interesting_repos=None):
    # ... function body ...
```

#### 3. Filtering Logic (Core Feature)

**Location:** `get_contributors()` function, after `get_repos()` call

```python
def get_contributors(org_name, number_of_days, headers, interesting_repos=None):
    # init contributor set
    unique_contributors = set()
    unique_authors = set()

    # Fetch all repositories in the organization
    repos = get_repos(org_name, headers)

    # ==================== NEW: FILTERING LOGIC ====================
    if interesting_repos:
        original_count = len(repos)

        # Create case-insensitive lookup set
        # Example: {"typescript", "vscode"} from user input {"TypeScript", "VSCode"}
        interesting_repos_lower = {name.lower() for name in interesting_repos}

        # Filter repositories by name (case-insensitive exact match)
        filtered_repos = [
            repo for repo in repos
            if repo['name'].lower() in interesting_repos_lower
        ]

        # Report filtering results to user
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
            return set(), set()  # Return empty sets - no contributors to analyze

        print(f"{'='*60}\n")
    # ==================== END FILTERING LOGIC ====================

    print(f"\nAnalyzing {len(repos)} repositories in {org_name}...")

    # Rest of function continues unchanged
    # Date range calculation...
    # Repository loop...
    # etc.
```

**Key Implementation Details:**

1. **Case-Insensitive Matching**
   ```python
   interesting_repos_lower = {name.lower() for name in interesting_repos}
   if repo['name'].lower() in interesting_repos_lower
   ```
   - Converts both filter and repo names to lowercase
   - Allows `TypeScript` to match `typescript`

2. **Set-Based Lookup**
   ```python
   interesting_repos_lower = {name.lower() for name in interesting_repos}  # Set
   if repo['name'].lower() in interesting_repos_lower  # O(1) lookup
   ```
   - Uses set for O(1) membership testing
   - More efficient than list for multiple lookups

3. **Missing Repo Detection**
   ```python
   found_repo_names = {repo['name'].lower() for repo in filtered_repos}
   missing_repos = interesting_repos_lower - found_repo_names  # Set difference
   ```
   - Uses set difference to find repos user requested but weren't found
   - Helps catch typos and configuration errors

4. **Preserving Original Case for Errors**
   ```python
   original_name = next(
       (r for r in interesting_repos if r.lower() == repo),
       repo
   )
   ```
   - Finds original user input case for better error messages
   - Shows "TypeScript" in error, not "typescript"

#### 4. Main Block Update

**Location:** Line ~220

```python
# Run the script
report_contributors(org_name, number_of_days, output_file, interesting_repos)
```

---

## Configuration Format

### .env File Format

```bash
# Optional: Comma-separated list of specific repositories to analyze
# If not specified or empty, all repositories in the organization will be analyzed
# Format: Just repository names (not owner/repo format)
# Case-insensitive matching (TypeScript matches typescript)
# Example: typescript,vscode,playwright
INTERESTING_REPOS=
```

### Valid Formats

| Format | Valid | Parsed Result | Notes |
|--------|-------|---------------|-------|
| `INTERESTING_REPOS=` | ✅ | `None` (no filter) | Empty = all repos |
| `INTERESTING_REPOS=typescript` | ✅ | `{"typescript"}` | Single repo |
| `INTERESTING_REPOS=typescript,vscode` | ✅ | `{"typescript", "vscode"}` | Multiple repos |
| `INTERESTING_REPOS=typescript, vscode` | ✅ | `{"typescript", "vscode"}` | Spaces trimmed |
| `INTERESTING_REPOS=typescript,vscode,` | ✅ | `{"typescript", "vscode"}` | Trailing comma ignored |
| `INTERESTING_REPOS= , , ` | ✅ | `None` (no filter) | Only whitespace = no filter |
| `INTERESTING_REPOS=TypeScript,VSCode` | ✅ | `{"typescript", "vscode"}` | Case normalized |
| Not set in .env | ✅ | `None` (no filter) | Backward compatible |

### Invalid Formats (Will be Ignored)

| Format | Behavior | Reason |
|--------|----------|--------|
| `INTERESTING_REPOS=owner/repo` | Warns, continues | Unnecessary owner prefix |
| `INTERESTING_REPOS=["repo1","repo2"]` | Treated as single name | Not JSON, use comma-separated |

---

## Behavior Specification

### Scenario 1: No Filter Specified (Default)

**Configuration:**
```bash
# INTERESTING_REPOS not set
# OR
INTERESTING_REPOS=
```

**Behavior:**
- `interesting_repos` variable = `None`
- Filtering logic skipped entirely
- All repositories analyzed (current behavior)
- No additional console output

**Output:**
```
Fetching repositories for microsoft...
  Fetching repositories page 1...
  Found 100 repositories on page 1
Total repositories found: 342

Analyzing 342 repositories in microsoft...
```

### Scenario 2: Valid Filter with All Repos Found

**Configuration:**
```bash
GITHUB_ORG_NAME=microsoft
INTERESTING_REPOS=typescript,vscode,playwright
```

**Behavior:**
- Fetch all 342 repos from microsoft
- Filter to only 3 repos: typescript, vscode, playwright
- All 3 repos found successfully
- Analyze only those 3 repos

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
  Found 5 contributors and 4 GitHub authors in typescript

Analyzing repository: microsoft/vscode
  Fetching commits page 1...
  Found 8 contributors and 7 GitHub authors in vscode

Analyzing repository: microsoft/playwright
  Fetching commits page 1...
  Found 3 contributors and 3 GitHub authors in playwright
```

### Scenario 3: Filter with Some Repos Not Found

**Configuration:**
```bash
GITHUB_ORG_NAME=microsoft
INTERESTING_REPOS=typescript,vscod,playwright,fake-repo
# Note: "vscod" and "fake-repo" don't exist
```

**Behavior:**
- Fetch all repos
- Find 2 matches: typescript, playwright
- Detect 2 missing: vscod, fake-repo
- Print warning with missing repos
- Continue with 2 valid repos

**Output:**
```
Fetching repositories for microsoft...
Total repositories found: 342

============================================================
Repository Filtering Enabled
============================================================
Total repositories in microsoft: 342
Repositories in INTERESTING_REPOS filter: 4
Matching repositories found: 2

⚠️  Warning: The following repositories were specified but not found:
    - fake-repo
    - vscod

Possible reasons:
  • Repository name typo
  • Repository doesn't exist in microsoft
  • Repository is private and token lacks access
============================================================

Analyzing 2 repositories in microsoft...

Analyzing repository: microsoft/typescript
  ...
Analyzing repository: microsoft/playwright
  ...
```

### Scenario 4: Filter with No Repos Found

**Configuration:**
```bash
GITHUB_ORG_NAME=microsoft
INTERESTING_REPOS=nonexistent1,nonexistent2,nonexistent3
```

**Behavior:**
- Fetch all repos
- Find 0 matches
- Print error message
- Return empty contributor sets
- Exit early (no commit analysis)

**Output:**
```
Fetching repositories for microsoft...
Total repositories found: 342

============================================================
Repository Filtering Enabled
============================================================
Total repositories in microsoft: 342
Repositories in INTERESTING_REPOS filter: 3
Matching repositories found: 0

⚠️  Warning: The following repositories were specified but not found:
    - nonexistent1
    - nonexistent2
    - nonexistent3

Possible reasons:
  • Repository name typo
  • Repository doesn't exist in microsoft
  • Repository is private and token lacks access

❌ Error: No matching repositories found.
Please check your INTERESTING_REPOS configuration.

Total commit authors in the last 30 days: 0
Total members in microsoft: 50
Total unique contributors from microsoft in the last 30 days: 0
```

### Scenario 5: Case-Insensitive Matching

**Configuration:**
```bash
GITHUB_ORG_NAME=microsoft
INTERESTING_REPOS=TypeScript,VSCODE,PlayWright
```

**Actual Repo Names on GitHub:**
- `typescript` (all lowercase)
- `vscode` (all lowercase)
- `playwright` (all lowercase)

**Behavior:**
- Case-insensitive matching succeeds
- All 3 repos found despite case mismatch
- Console output shows actual repo names (lowercase)

**Output:**
```
============================================================
Repository Filtering Enabled
============================================================
Total repositories in microsoft: 342
Repositories in INTERESTING_REPOS filter: 3
Matching repositories found: 3
============================================================

Analyzing 3 repositories in microsoft...

Analyzing repository: microsoft/typescript  ← Actual name (lowercase)
Analyzing repository: microsoft/vscode
Analyzing repository: microsoft/playwright
```

---

## Edge Cases

### Edge Case Matrix

| Case | Input | Expected Behavior | Actual Result |
|------|-------|-------------------|---------------|
| **Empty string** | `INTERESTING_REPOS=` | Analyze all repos | ✅ `interesting_repos = None` |
| **Only whitespace** | `INTERESTING_REPOS=   ` | Analyze all repos | ✅ Stripped, becomes None |
| **Single repo** | `INTERESTING_REPOS=typescript` | Analyze 1 repo | ✅ `{"typescript"}` |
| **Trailing comma** | `INTERESTING_REPOS=repo1,repo2,` | Analyze 2 repos | ✅ Empty string filtered out |
| **Leading comma** | `INTERESTING_REPOS=,repo1,repo2` | Analyze 2 repos | ✅ Empty string filtered out |
| **Multiple commas** | `INTERESTING_REPOS=repo1,,repo2` | Analyze 2 repos | ✅ Empty strings filtered |
| **Spaces around names** | `INTERESTING_REPOS= repo1 , repo2 ` | Analyze 2 repos | ✅ Stripped |
| **Mixed case** | `INTERESTING_REPOS=TypeScript` | Matches `typescript` | ✅ Lowercased |
| **Non-existent repo** | `INTERESTING_REPOS=fake` | Warn, analyze 0 repos | ✅ Warning + empty results |
| **Partial match** | Filter: `type`, Repo: `typescript` | No match | ✅ Exact match required |
| **Variable not set** | `.env` has no `INTERESTING_REPOS` | Analyze all repos | ✅ `getenv` returns empty, becomes None |
| **Owner/repo format** | `INTERESTING_REPOS=microsoft/typescript` | Warns, no match | ⚠️ Looking for repo named "microsoft/typescript" |
| **Unicode characters** | `INTERESTING_REPOS=café-repo` | Match if repo exists | ✅ Python string handling |
| **Very long list** | 100 repo names | Process all | ✅ Set handles well |
| **Duplicate names** | `INTERESTING_REPOS=repo1,repo1,repo1` | De-duplicated by set | ✅ `{"repo1"}` |
| **All repos filtered out** | All names invalid | Error, empty results | ✅ Returns `(set(), set())` |

### Special Case: GitHub API Limitations

**Scenario:** User specifies repos they don't have access to

```bash
INTERESTING_REPOS=public-repo,private-repo-no-access
```

**Behavior:**
- `get_repos()` returns only repos the token can access
- Private repos without access won't appear in repo list
- Filter treats them as "not found"
- Warning message mentions "private and token lacks access"

---

## Example Scenarios

### Example 1: Security Team Use Case

**Context:** Security team wants to track contributors to critical repos

```bash
# .env
GITHUB_ORG_NAME=facebook
NUMBER_OF_DAYS=90
INTERESTING_REPOS=react,react-native,metro,hermes
OUTPUT_FILE=security_audit.json
```

**Expected Results:**
- Analyze only React ecosystem repos
- Identify all contributors in last 90 days
- Generate focused security audit report
- Significantly faster than analyzing 500+ repos

### Example 2: Product Team Dashboard

**Context:** VSCode team wants monthly contributor stats

```bash
# .env
GITHUB_ORG_NAME=microsoft
NUMBER_OF_DAYS=30
INTERESTING_REPOS=vscode,vscode-docs,vscode-extension-samples
OUTPUT_FILE=vscode_monthly.json
```

**Workflow:**
1. Run script monthly
2. Track contributor growth over time
3. Compare internal vs external contributors
4. Generate team reports

### Example 3: Open Source Program Office

**Context:** Track flagship project activity

```bash
# .env for Chromium projects
GITHUB_ORG_NAME=chromium
INTERESTING_REPOS=chromium,v8,devtools-frontend,chromium-dashboard
NUMBER_OF_DAYS=7
OUTPUT_FILE=weekly_chromium.json
```

**Benefits:**
- Weekly snapshots of key projects
- Identify contributor trends
- Monitor external contributions
- Focus on strategic repos only

### Example 4: Compliance Audit

**Context:** Legal team needs contributor list for specific repos

```bash
# .env
GITHUB_ORG_NAME=company-internal
INTERESTING_REPOS=product-alpha,product-beta,shared-library
NUMBER_OF_DAYS=365
OUTPUT_FILE=annual_compliance.json
```

**Use Case:**
- Annual compliance requirement
- Verify CLA/contributor agreements
- Generate audit trail
- Export to JSON for records

---

## Testing Strategy

### Unit Tests

```python
# Pseudo-code for testing

def test_parse_interesting_repos_empty():
    """Test empty string returns None"""
    result = parse_interesting_repos("")
    assert result is None

def test_parse_interesting_repos_single():
    """Test single repo"""
    result = parse_interesting_repos("typescript")
    assert result == {"typescript"}

def test_parse_interesting_repos_multiple():
    """Test multiple repos"""
    result = parse_interesting_repos("typescript,vscode,playwright")
    assert result == {"typescript", "vscode", "playwright"}

def test_parse_interesting_repos_whitespace():
    """Test whitespace handling"""
    result = parse_interesting_repos(" typescript , vscode , playwright ")
    assert result == {"typescript", "vscode", "playwright"}

def test_parse_interesting_repos_trailing_comma():
    """Test trailing comma"""
    result = parse_interesting_repos("typescript,vscode,")
    assert result == {"typescript", "vscode"}

def test_filter_repos_case_insensitive():
    """Test case-insensitive matching"""
    repos = [
        {"name": "typescript", "owner": {"login": "microsoft"}},
        {"name": "vscode", "owner": {"login": "microsoft"}}
    ]
    filter_set = {"TypeScript", "VSCODE"}
    result = filter_repositories(repos, filter_set)
    assert len(result) == 2

def test_filter_repos_not_found():
    """Test repos not in organization"""
    repos = [{"name": "typescript", "owner": {"login": "microsoft"}}]
    filter_set = {"typescript", "nonexistent"}
    result, missing = filter_repositories_with_missing(repos, filter_set)
    assert len(result) == 1
    assert missing == {"nonexistent"}

def test_filter_repos_empty_result():
    """Test all repos filtered out"""
    repos = [{"name": "typescript", "owner": {"login": "microsoft"}}]
    filter_set = {"nonexistent1", "nonexistent2"}
    result = filter_repositories(repos, filter_set)
    assert len(result) == 0
```

### Integration Tests

| Test Case | Setup | Expected Result |
|-----------|-------|-----------------|
| **No filter** | Don't set `INTERESTING_REPOS` | All repos analyzed |
| **Valid filter** | Set 3 valid repo names | Only 3 repos analyzed |
| **Mixed valid/invalid** | 2 valid, 2 invalid names | 2 repos analyzed, warning shown |
| **All invalid** | All repo names invalid | Error message, empty results |
| **Case mismatch** | Filter with different case | Repos found successfully |
| **Large org** | Org with 100+ repos, filter to 5 | Significantly faster runtime |

### Manual Testing Checklist

- [ ] Run with `INTERESTING_REPOS` not set → Verify all repos analyzed
- [ ] Run with `INTERESTING_REPOS=` → Verify all repos analyzed
- [ ] Run with single repo → Verify only that repo analyzed
- [ ] Run with multiple repos → Verify correct filtering
- [ ] Run with non-existent repo → Verify warning message
- [ ] Run with wrong case → Verify case-insensitive matching works
- [ ] Run with whitespace → Verify trimming works
- [ ] Run with trailing commas → Verify parsing handles gracefully
- [ ] Verify JSON output format unchanged
- [ ] Verify console output is clear and helpful
- [ ] Test with private repos token can't access → Verify graceful handling
- [ ] Test with very large organization (100+ repos) → Verify performance improvement

### Performance Testing

**Scenario:** Microsoft organization (342 repos)

| Configuration | Repos Analyzed | API Calls | Approx Time |
|---------------|----------------|-----------|-------------|
| No filter | 342 | ~342+ | ~10-15 min |
| Filter to 10 repos | 10 | ~10+ | ~1-2 min |
| Filter to 3 repos | 3 | ~3+ | ~30 sec |

**Expected Improvement:**
- API calls reduced proportionally
- Execution time reduced proportionally
- Rate limit consumption reduced significantly

---

## Migration Guide

### For Existing Users

**No action required!** The feature is fully backward compatible.

If you want to enable filtering:

1. **Edit `.env` file**
   ```bash
   # Add this line
   INTERESTING_REPOS=repo1,repo2,repo3
   ```

2. **Run script normally**
   ```bash
   python3 github_recent_contributors.py
   ```

3. **Verify filtering in output**
   Look for the "Repository Filtering Enabled" section in console output

### Example Migration

**Before (Analyzing all repos):**
```bash
# .env
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxx
GITHUB_ORG_NAME=microsoft
NUMBER_OF_DAYS=30
OUTPUT_FILE=output.json
```

**After (Filtering specific repos):**
```bash
# .env
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxx
GITHUB_ORG_NAME=microsoft
NUMBER_OF_DAYS=30
OUTPUT_FILE=output.json
INTERESTING_REPOS=typescript,vscode,playwright  # NEW LINE
```

### Reverting to Old Behavior

Simply remove or comment out the line:
```bash
# INTERESTING_REPOS=typescript,vscode,playwright
```

Or set it to empty:
```bash
INTERESTING_REPOS=
```

---

## JSON Output Format

### No Changes to Output Structure

The JSON output format remains **identical**. The only difference is the contributors/authors in the output will be from filtered repos only.

**Example Output (with filtering):**
```json
{
    "organization": "microsoft",
    "date": "2025-10-28",
    "number_of_days_history": 30,
    "org_members": ["user1", "user2", "user3"],
    "commit_authors": ["user1", "user4", "user5"],
    "commiting_members": ["user1"]
}
```

Note: The JSON does **not** indicate which repos were analyzed. To track this:
- Check console output
- Keep separate records of `.env` configurations used
- Add custom metadata if needed (future enhancement)

---

## Future Enhancements (Out of Scope)

Potential future improvements:

1. **Include filter in JSON output**
   ```json
   {
       "filtered_repositories": ["typescript", "vscode"],
       "total_repositories_in_org": 342,
       ...
   }
   ```

2. **Regex or wildcard matching**
   ```bash
   INTERESTING_REPOS=react-*,*-core
   ```

3. **Exclusion filter**
   ```bash
   EXCLUDE_REPOS=archived-*,deprecated-*
   ```

4. **Config file support**
   ```yaml
   # config.yaml
   organization: microsoft
   filters:
     include_repos:
       - typescript
       - vscode
   ```

5. **CLI override**
   ```bash
   python3 github_recent_contributors.py --repos typescript,vscode
   ```

---

## Implementation Checklist

- [ ] Update `.env.example` with `INTERESTING_REPOS` documentation
- [ ] Add environment variable parsing in main block
- [ ] Update `get_contributors()` function signature
- [ ] Implement filtering logic in `get_contributors()`
- [ ] Update `report_contributors()` function signature
- [ ] Pass `interesting_repos` parameter in main block
- [ ] Test with no filter (backward compatibility)
- [ ] Test with valid filter
- [ ] Test with invalid repos (warning handling)
- [ ] Test case-insensitive matching
- [ ] Test edge cases (empty, whitespace, commas)
- [ ] Update `CLAUDE.md` documentation
- [ ] Update main script docstring if needed
- [ ] Verify JSON output format unchanged

---

## References

- Main implementation: `github_recent_contributors.py`
- Related spec: `tech_specs__get_contributors.md`
- Configuration template: `.env.example`
- Project documentation: `CLAUDE.md`

---

## Approval

**Status:** ✅ Approved for Implementation
**Date:** 2025-10-28
**Approver:** Project Owner

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-28 | Technical Documentation | Initial specification |
