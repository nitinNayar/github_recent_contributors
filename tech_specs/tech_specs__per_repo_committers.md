# Technical Specification: Per-Repository Committer Tracking

**Document Version:** 1.0
**Date:** 2025-10-28
**Feature Type:** Enhancement
**Status:** Approved for Implementation

---

## Table of Contents
1. [Feature Overview](#feature-overview)
2. [Motivation and Use Cases](#motivation-and-use-cases)
3. [Design Decisions](#design-decisions)
4. [JSON Output Structure](#json-output-structure)
5. [Implementation Details](#implementation-details)
6. [Data Collection Strategy](#data-collection-strategy)
7. [Edge Cases](#edge-cases)
8. [Performance Considerations](#performance-considerations)
9. [Example Outputs](#example-outputs)
10. [Testing Strategy](#testing-strategy)

---

## Feature Overview

### Summary
Extend the JSON output to include per-repository contributor details, tracking which specific committers contributed to each repository along with their commit counts.

### Current Behavior
The script provides only **aggregated** contributor data:
- Global list of all contributors across all repos
- No per-repository breakdown
- No commit count information

### New Behavior
The script will provide both:
- **Aggregated data** (existing fields, unchanged for backward compatibility)
- **Per-repository breakdown** (new `repos_detail` section with commit counts)

### Backward Compatibility
✅ **Fully backward compatible** - All existing JSON fields remain unchanged. New data is additive only.

---

## Motivation and Use Cases

### Problem Statement
Currently, users cannot answer questions like:
- Which repositories did a specific person contribute to?
- How many commits did each person make to each repo?
- Which repos have the most active contributors?
- What's the contribution distribution across repos?

### Target Users

1. **Engineering Managers**: Track team contributions per project
2. **Open Source Program Offices**: Analyze contribution patterns across repos
3. **Security Teams**: Audit which repos external contributors have access to
4. **Product Managers**: Understand resource allocation across products
5. **Data Analysts**: Generate reports and visualizations of contributor activity

### Example Scenarios

**Scenario 1: Team Contribution Analysis**
```
Question: "How many commits did Alice make to each repository?"
Current Answer: "Alice committed to the org" (no detail)
New Answer: "Alice: typescript (45 commits), vscode (60 commits)"
```

**Scenario 2: Repository Health Check**
```
Question: "Which repositories have the least contributor diversity?"
Current Answer: Cannot answer
New Answer: "repo-abandoned has 1 contributor, repo-active has 25 contributors"
```

**Scenario 3: External Contributor Access**
```
Question: "Which repos did external contributor bob-external touch?"
Current Answer: Cannot answer
New Answer: "bob-external: security-lib (3 commits), docs (1 commit)"
```

**Scenario 4: Resource Allocation**
```
Question: "Which projects are getting the most development attention?"
Current Answer: Cannot answer (without commit count)
New Answer: "project-alpha: 450 commits, project-beta: 120 commits"
```

---

## Design Decisions

### Decision Matrix

| Aspect | Options Considered | Selected | Rationale |
|--------|-------------------|----------|-----------|
| **Output Location** | Same file, separate file | **Same file** | User confirmed, simpler for consumers |
| **Data Tracked** | Names only, names + counts, detailed stats | **Names + counts** | Balances detail with simplicity |
| **Count Granularity** | Per person, per person per repo | **Per person per repo** | Answers "who contributed how much where" |
| **Data Structure** | Array, nested object | **Nested object** | Easy lookup by repo name |
| **Metadata** | Minimal, comprehensive | **Comprehensive** | Includes URLs, counts, totals |
| **Commit Counting** | Unique contributors, all commits | **All commits** | Shows activity level accurately |

### User Requirements (from Q&A)

✅ **Add to existing OUTPUT_FILE** - Extend current JSON structure
✅ **Track git commit author names** - From commit metadata
✅ **Track GitHub usernames** - From GitHub user objects
✅ **Include commit counts per person** - Quantify contributions
✅ **Include total commits per repo** - Repository activity metric
✅ **Include repository URLs** - Easy navigation to repos
✅ **Include unique contributor counts** - Quick summary stats

---

## JSON Output Structure

### Complete Schema

```json
{
  "organization": "string",
  "date": "YYYY-MM-DD",
  "number_of_days_history": number,
  "org_members": ["string", ...],
  "commit_authors": ["string", ...],
  "commiting_members": ["string", ...],

  "repos_detail": {
    "repo_name": {
      "repository_url": "string",
      "total_commits": number,
      "unique_contributors_count": number,
      "unique_github_authors_count": number,
      "commit_authors": {
        "Author Name": commit_count,
        ...
      },
      "github_authors": {
        "github_username": commit_count,
        ...
      }
    },
    ...
  }
}
```

### Field Descriptions

#### Top-Level Fields (Existing - Unchanged)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `organization` | string | GitHub organization name | `"microsoft"` |
| `date` | string | Date of analysis (YYYY-MM-DD) | `"2025-10-28"` |
| `number_of_days_history` | number | Lookback period in days | `30` |
| `org_members` | array[string] | List of organization members | `["user1", "user2"]` |
| `commit_authors` | array[string] | Global list of GitHub usernames who committed | `["user1", "user3"]` |
| `commiting_members` | array[string] | Members who also committed | `["user1"]` |

#### New Top-Level Field

| Field | Type | Description |
|-------|------|-------------|
| `repos_detail` | object | Per-repository contributor details (NEW) |

#### repos_detail Structure

For each repository (key = repository name):

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `repository_url` | string | GitHub URL to the repository | `"https://github.com/microsoft/typescript"` |
| `total_commits` | number | Total commits in date range | `150` |
| `unique_contributors_count` | number | Count of unique git author names | `12` |
| `unique_github_authors_count` | number | Count of unique GitHub usernames | `10` |
| `commit_authors` | object | Git author names → commit counts | `{"Alice Smith": 45}` |
| `github_authors` | object | GitHub usernames → commit counts | `{"alice-s": 45}` |

### Why Two Author Lists?

The distinction between `commit_authors` and `github_authors` is maintained from the original design:

- **`commit_authors`**: Git commit metadata names (from `git config user.name`)
  - Always present (required by git protocol)
  - May be inconsistent ("Alice", "Alice Smith", "A. Smith")
  - Shows how people identify themselves in git

- **`github_authors`**: GitHub account usernames
  - Only present when GitHub can link commit email to account
  - Consistent format (GitHub enforces username standards)
  - Shows verified GitHub identities

**Example Mismatch:**
```json
"commit_authors": {
  "Alice Smith": 45,
  "Charlie Brown": 25
},
"github_authors": {
  "alice-s": 45
  // Note: Charlie Brown has no GitHub account linked
}
```

---

## Implementation Details

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ get_contributors()                                           │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Initialize:                                             │ │
│ │  - unique_contributors (set)                            │ │
│ │  - unique_authors (set)                                 │ │
│ │  - repos_detail (dict)          ← NEW                   │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ For each repository:                                    │ │
│ │  ┌───────────────────────────────────────────────────┐  │ │
│ │  │ Per-repo tracking (changed from sets to dicts):   │  │ │
│ │  │  - repo_contributors = {}    ← CHANGED            │  │ │
│ │  │  - repo_authors = {}         ← CHANGED            │  │ │
│ │  │  - total_commits = 0         ← NEW                │  │ │
│ │  └───────────────────────────────────────────────────┘  │ │
│ │                                                          │ │
│ │  ┌───────────────────────────────────────────────────┐  │ │
│ │  │ For each commit in repo:                          │  │ │
│ │  │  - total_commits += 1                             │  │ │
│ │  │  - repo_contributors[name] = count + 1  ← CHANGED │  │ │
│ │  │  - repo_authors[login] = count + 1      ← CHANGED │  │ │
│ │  └───────────────────────────────────────────────────┘  │ │
│ │                                                          │ │
│ │  ┌───────────────────────────────────────────────────┐  │ │
│ │  │ Build repos_detail entry:             ← NEW       │  │ │
│ │  │  repos_detail[repo_name] = {                      │  │ │
│ │  │    "repository_url": ...,                         │  │ │
│ │  │    "total_commits": total_commits,                │  │ │
│ │  │    "unique_contributors_count": ...,              │  │ │
│ │  │    "unique_github_authors_count": ...,            │  │ │
│ │  │    "commit_authors": repo_contributors,           │  │ │
│ │  │    "github_authors": repo_authors                 │  │ │
│ │  │  }                                                 │  │ │
│ │  └───────────────────────────────────────────────────┘  │ │
│ │                                                          │ │
│ │  ┌───────────────────────────────────────────────────┐  │ │
│ │  │ Update global sets (for backward compatibility):  │  │ │
│ │  │  - unique_contributors.update(                    │  │ │
│ │  │      repo_contributors.keys())     ← CHANGED      │  │ │
│ │  │  - unique_authors.update(                         │  │ │
│ │  │      repo_authors.keys())          ← CHANGED      │  │ │
│ │  └───────────────────────────────────────────────────┘  │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Return three values:                    ← CHANGED       │ │
│ │  return (unique_contributors,                           │ │
│ │          unique_authors,                                │ │
│ │          repos_detail)                                  │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ report_contributors()                                        │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Receive three values:                   ← CHANGED       │ │
│ │  unique_contributors, unique_authors, repos_detail =    │ │
│ │      get_contributors(...)                              │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Build output_data with repos_detail:    ← CHANGED       │ │
│ │  output_data = {                                        │ │
│ │      ... existing fields ...,                           │ │
│ │      "repos_detail": repos_detail       ← NEW           │ │
│ │  }                                                      │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Write JSON with formatting:             ← CHANGED       │ │
│ │  json.dump(output_data, file, indent=2)                 │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Code Change Summary

| Location | Current | New | Change Type |
|----------|---------|-----|-------------|
| `get_contributors()` line ~100 | Initialize 2 sets | Initialize 2 sets + 1 dict | Add variable |
| `get_contributors()` line ~166 | `repo_contributors = set()` | `repo_contributors = {}` | Change type |
| `get_contributors()` line ~167 | `repo_authors = set()` | `repo_authors = {}` | Change type |
| `get_contributors()` line ~168 | N/A | `total_commits = 0` | Add variable |
| `get_contributors()` line ~190 | `.add(name)` | `[name] = get(name,0) + 1` | Change logic |
| `get_contributors()` line ~193 | `.add(login)` | `[login] = get(login,0) + 1` | Change logic |
| `get_contributors()` line ~195 | N/A | Build `repos_detail` entry | Add logic |
| `get_contributors()` line ~198 | `.update(repo_contributors)` | `.update(repo_contributors.keys())` | Add `.keys()` |
| `get_contributors()` line ~199 | `.update(repo_authors)` | `.update(repo_authors.keys())` | Add `.keys()` |
| `get_contributors()` line ~203 | Return 2 values | Return 3 values | Add return value |
| `report_contributors()` line ~215 | Unpack 2 values | Unpack 3 values | Add variable |
| `report_contributors()` line ~226 | N/A | Add `repos_detail` to dict | Add field |
| `report_contributors()` line ~229 | `json.dump(data, file)` | `json.dump(data, file, indent=2)` | Add parameter |

---

## Data Collection Strategy

### From Sets to Dictionaries

**Previous Approach (Sets):**
```python
repo_contributors = set()
for commit in commits:
    repo_contributors.add(commit['commit']['author']['name'])
# Result: {"Alice", "Bob", "Charlie"}
# Lost information: How many commits each person made
```

**New Approach (Dictionaries):**
```python
repo_contributors = {}
for commit in commits:
    name = commit['commit']['author']['name']
    repo_contributors[name] = repo_contributors.get(name, 0) + 1
# Result: {"Alice": 45, "Bob": 30, "Charlie": 25}
# Preserved information: Commit counts per person
```

### Counting Algorithm

**Dictionary `.get()` Method:**
```python
# Safe way to increment count, handles first occurrence
repo_contributors[name] = repo_contributors.get(name, 0) + 1

# Equivalent to:
if name in repo_contributors:
    repo_contributors[name] += 1
else:
    repo_contributors[name] = 1
```

**Example Execution:**
```python
commits = ["Alice", "Bob", "Alice", "Alice", "Bob"]

repo_contributors = {}
for author in commits:
    repo_contributors[author] = repo_contributors.get(author, 0) + 1

# Step by step:
# 1. Alice: {} → {"Alice": 1}
# 2. Bob:   {"Alice": 1} → {"Alice": 1, "Bob": 1}
# 3. Alice: {"Alice": 1, "Bob": 1} → {"Alice": 2, "Bob": 1}
# 4. Alice: {"Alice": 2, "Bob": 1} → {"Alice": 3, "Bob": 1}
# 5. Bob:   {"Alice": 3, "Bob": 1} → {"Alice": 3, "Bob": 2}

# Final: {"Alice": 3, "Bob": 2}
```

### Maintaining Backward Compatibility

**Global Sets Still Needed:**
```python
# After counting per repo, extract unique names for global aggregation
unique_contributors.update(repo_contributors.keys())
unique_authors.update(repo_authors.keys())

# Example:
# Repo 1: {"Alice": 10, "Bob": 5}
# Repo 2: {"Alice": 20, "Charlie": 3}
#
# Global set: {"Alice", "Bob", "Charlie"}  ← Used for existing JSON fields
```

This ensures the existing `commit_authors` and `commiting_members` fields remain unchanged.

---

## Edge Cases

### Edge Case 1: Empty Repository (No Commits)

**Scenario:** Repository exists but has no commits in the date range.

**Handling:**
```json
"repos_detail": {
  "empty-repo": {
    "repository_url": "https://github.com/org/empty-repo",
    "total_commits": 0,
    "unique_contributors_count": 0,
    "unique_github_authors_count": 0,
    "commit_authors": {},
    "github_authors": {}
  }
}
```

**Code Path:** The pagination loop breaks on first empty page, leaving all counters at 0.

### Edge Case 2: Commit Without GitHub Account

**Scenario:** Git commit author email doesn't match any GitHub account.

**Example:**
```json
"repos_detail": {
  "repo1": {
    "commit_authors": {
      "External Contributor": 5
    },
    "github_authors": {}
    // Note: Empty because commit['author'] was None
  }
}
```

**Counts Mismatch:**
- `unique_contributors_count`: 1 (External Contributor)
- `unique_github_authors_count`: 0 (no GitHub account)

This is expected and correct behavior.

### Edge Case 3: Same Person, Multiple Git Identities

**Scenario:** Person commits with different git configurations.

**Example:**
```json
"commit_authors": {
  "Alice Smith": 30,
  "A. Smith": 10,
  "alice": 5
},
"github_authors": {
  "alice-s": 45
}
```

**Behavior:**
- Git names tracked separately (can't automatically merge)
- GitHub username consolidates (if all commits use same email)
- Total: 45 commits (30+10+5 = 45)

**User Action:** Manual reconciliation needed if desired.

### Edge Case 4: INTERESTING_REPOS Filter

**Scenario:** Organization has 100 repos, filter to 3.

**Behavior:**
```json
"repos_detail": {
  "repo1": {...},
  "repo2": {...},
  "repo3": {...}
  // Only 3 entries, not 100
}
```

**Implementation:** Filtering happens before the repo loop, so `repos_detail` naturally contains only analyzed repos.

### Edge Case 5: Very Active Contributor

**Scenario:** Single person makes 10,000 commits to one repo.

**Example:**
```json
"commit_authors": {
  "Bot Account": 10000
},
"total_commits": 10000
```

**Handling:** JSON number type supports this. No special handling needed.

### Edge Case 6: Repository Name Conflicts

**Scenario:** Two repos with same name (impossible in same org).

**Behavior:** N/A - GitHub enforces unique repo names per org.

### Edge Case 7: Special Characters in Names

**Scenario:** Commit author name contains special characters.

**Example:**
```json
"commit_authors": {
  "José García": 10,
  "李明": 5,
  "O'Brien": 3
}
```

**Handling:** JSON UTF-8 encoding handles all Unicode characters. Python's `json.dump()` handles escaping automatically.

---

## Performance Considerations

### Memory Impact

**Before:**
- Per repo: 2 sets (discarded after processing)
- Global: 2 sets
- Estimate: ~100 KB for typical organization

**After:**
- Per repo: 2 dictionaries (kept in `repos_detail`)
- Global: 2 sets
- Estimate: ~300-500 KB for typical organization

**Scaling:**
- 100 repos × 20 contributors/repo × 50 bytes/entry ≈ 100 KB
- Plus commit counts and metadata: ~200-300 KB
- Total: Acceptable for modern systems

### Processing Time Impact

| Phase | Before | After | Change |
|-------|--------|-------|--------|
| API calls | N commits | N commits | No change |
| Commit processing | Set add (O(1)) | Dict update (O(1)) | No change |
| Data aggregation | Set update | Dict + Set update | Minimal |
| JSON writing | Small file | Larger file | +50-100ms |

**Overall Impact:** Negligible (< 1% increase in total runtime)

### JSON File Size Impact

**Example Organization (30-day analysis):**

| Repos | Contributors | Before | After | Increase |
|-------|--------------|--------|-------|----------|
| 10 | 20 | 2 KB | 8 KB | 4x |
| 50 | 100 | 8 KB | 50 KB | 6x |
| 100 | 200 | 15 KB | 120 KB | 8x |
| 500 | 1000 | 50 KB | 800 KB | 16x |

**Mitigation:** File size is still reasonable for most use cases. Users analyzing 500+ repos likely have the infrastructure to handle larger JSON files.

### API Rate Limit Impact

**No change** - Same number of API calls as before. We're just storing more data from the same responses.

---

## Example Outputs

### Example 1: Small Organization

**Setup:**
- Organization: "small-startup"
- Repositories: 3
- Time range: 30 days
- INTERESTING_REPOS: Not set (analyze all)

**Output:**
```json
{
  "organization": "small-startup",
  "date": "2025-10-28",
  "number_of_days_history": 30,
  "org_members": ["alice", "bob"],
  "commit_authors": ["alice", "bob", "external-dev"],
  "commiting_members": ["alice", "bob"],

  "repos_detail": {
    "web-app": {
      "repository_url": "https://github.com/small-startup/web-app",
      "total_commits": 45,
      "unique_contributors_count": 2,
      "unique_github_authors_count": 2,
      "commit_authors": {
        "Alice Smith": 30,
        "Bob Jones": 15
      },
      "github_authors": {
        "alice": 30,
        "bob": 15
      }
    },
    "api-server": {
      "repository_url": "https://github.com/small-startup/api-server",
      "total_commits": 22,
      "unique_contributors_count": 2,
      "unique_github_authors_count": 2,
      "commit_authors": {
        "Bob Jones": 20,
        "Alice Smith": 2
      },
      "github_authors": {
        "bob": 20,
        "alice": 2
      }
    },
    "docs": {
      "repository_url": "https://github.com/small-startup/docs",
      "total_commits": 8,
      "unique_contributors_count": 2,
      "unique_github_authors_count": 1,
      "commit_authors": {
        "External Developer": 5,
        "Alice Smith": 3
      },
      "github_authors": {
        "alice": 3
      }
    }
  }
}
```

**Analysis:**
- Alice: Most active (35 total commits)
- Bob: Focused on api-server (20/22 commits)
- External Developer: Contributed to docs only (no GitHub account)

### Example 2: With INTERESTING_REPOS Filter

**Setup:**
- Organization: "microsoft"
- Total repositories: 342
- INTERESTING_REPOS: "typescript,vscode"
- Time range: 7 days

**Output:**
```json
{
  "organization": "microsoft",
  "date": "2025-10-28",
  "number_of_days_history": 7,
  "org_members": ["user1", "user2", "user3"],
  "commit_authors": ["user1", "user4", "user5"],
  "commiting_members": ["user1"],

  "repos_detail": {
    "typescript": {
      "repository_url": "https://github.com/microsoft/typescript",
      "total_commits": 28,
      "unique_contributors_count": 8,
      "unique_github_authors_count": 8,
      "commit_authors": {
        "Daniel Rosenwasser": 10,
        "Nathan Shively-Sanders": 7,
        "Andrew Branch": 5,
        "Wesley Wigham": 3,
        "Ron Buckton": 1,
        "Sheetal Nandi": 1,
        "Jake Bailey": 1
      },
      "github_authors": {
        "DanielRosenwasser": 10,
        "sandersn": 7,
        "andrewbranch": 5,
        "weswigham": 3,
        "rbuckton": 1,
        "sheetalkamat": 1,
        "jakebailey": 1
      }
    },
    "vscode": {
      "repository_url": "https://github.com/microsoft/vscode",
      "total_commits": 42,
      "unique_contributors_count": 12,
      "unique_github_authors_count": 11,
      "commit_authors": {
        "Benjamin Pasero": 15,
        "Johannes Rieken": 10,
        "Alex Dima": 8,
        "Connor Peet": 4,
        "Matt Bierner": 3,
        "Tyler James Leonhardt": 2
      },
      "github_authors": {
        "bpasero": 15,
        "jrieken": 10,
        "alexandrudima": 8,
        "connor4312": 4,
        "mjbvz": 3,
        "TylerLeonhardt": 2
      }
    }
  }
}
```

**Note:** Only 2 repos in `repos_detail` despite 342 total repos (filtering applied).

### Example 3: Empty Repository

**Setup:**
- Repository: "archived-project"
- Last commit: 6 months ago
- Analysis period: Last 30 days

**Output:**
```json
{
  "repos_detail": {
    "archived-project": {
      "repository_url": "https://github.com/org/archived-project",
      "total_commits": 0,
      "unique_contributors_count": 0,
      "unique_github_authors_count": 0,
      "commit_authors": {},
      "github_authors": {}
    }
  }
}
```

### Example 4: Bot Contributions

**Setup:**
- Repository with automated commits from bots

**Output:**
```json
{
  "repos_detail": {
    "auto-repo": {
      "repository_url": "https://github.com/org/auto-repo",
      "total_commits": 150,
      "unique_contributors_count": 3,
      "unique_github_authors_count": 3,
      "commit_authors": {
        "dependabot": 100,
        "renovate-bot": 40,
        "Alice Smith": 10
      },
      "github_authors": {
        "dependabot[bot]": 100,
        "renovate[bot]": 40,
        "alice": 10
      }
    }
  }
}
```

**Analysis:** Repository is 93% automated (140/150 commits from bots).

---

## Testing Strategy

### Unit Tests (Conceptual)

```python
def test_commit_counting():
    """Verify commit counts are accurate"""
    commits = [
        {"commit": {"author": {"name": "Alice"}}, "author": {"login": "alice"}},
        {"commit": {"author": {"name": "Alice"}}, "author": {"login": "alice"}},
        {"commit": {"author": {"name": "Bob"}}, "author": {"login": "bob"}}
    ]

    result = count_commits(commits)

    assert result["Alice"] == 2
    assert result["Bob"] == 1
    assert len(result) == 2

def test_repos_detail_structure():
    """Verify repos_detail has correct structure"""
    repos_detail = build_repos_detail(repo, commits)

    assert "repository_url" in repos_detail
    assert "total_commits" in repos_detail
    assert "commit_authors" in repos_detail
    assert isinstance(repos_detail["commit_authors"], dict)

def test_empty_repository():
    """Verify empty repos handled correctly"""
    repos_detail = build_repos_detail(repo, [])

    assert repos_detail["total_commits"] == 0
    assert repos_detail["commit_authors"] == {}
    assert repos_detail["unique_contributors_count"] == 0
```

### Integration Tests

| Test Case | Setup | Verification |
|-----------|-------|-------------|
| **Basic counting** | 1 repo, 10 commits, 3 people | Verify counts sum to 10 |
| **Multiple repos** | 3 repos, same person in each | Verify person appears in each repo's detail |
| **Filtering** | INTERESTING_REPOS=repo1,repo2 | Verify only repo1 and repo2 in repos_detail |
| **No GitHub account** | Commit without author object | Verify appears in commit_authors only |
| **Backward compatibility** | Compare old vs new output | Verify all old fields unchanged |
| **Large numbers** | Person with 1000+ commits | Verify JSON handles large numbers |
| **Special characters** | Unicode names | Verify JSON encoding correct |
| **Empty repo** | Repo with 0 commits | Verify empty dicts, counts = 0 |

### Manual Testing Checklist

- [ ] Run with single repository
- [ ] Run with multiple repositories
- [ ] Run with INTERESTING_REPOS filter
- [ ] Verify commit counts match GitHub UI
- [ ] Verify backward compatibility (existing fields unchanged)
- [ ] Check JSON is valid (use JSON validator)
- [ ] Verify JSON formatting is readable (indented)
- [ ] Test with very active repo (100+ commits)
- [ ] Test with empty repo (0 commits)
- [ ] Verify total_commits matches sum of individual counts
- [ ] Verify unique_*_count matches length of author dicts
- [ ] Check repos_detail only contains analyzed repos
- [ ] Verify repository URLs are clickable/correct

### Validation Script

```python
# Script to validate repos_detail structure
import json

def validate_repos_detail(file_path):
    with open(file_path) as f:
        data = json.load(f)

    assert "repos_detail" in data, "Missing repos_detail field"

    for repo_name, repo_data in data["repos_detail"].items():
        # Check required fields
        required_fields = [
            "repository_url",
            "total_commits",
            "unique_contributors_count",
            "unique_github_authors_count",
            "commit_authors",
            "github_authors"
        ]

        for field in required_fields:
            assert field in repo_data, f"{repo_name}: Missing {field}"

        # Verify counts match dict lengths
        assert repo_data["unique_contributors_count"] == len(repo_data["commit_authors"])
        assert repo_data["unique_github_authors_count"] == len(repo_data["github_authors"])

        # Verify commit counts sum correctly
        total = sum(repo_data["commit_authors"].values())
        assert total <= repo_data["total_commits"], f"{repo_name}: Count mismatch"

    print("✅ All validations passed")
```

---

## Migration and Rollout

### For Existing Users

**No action required** - The feature is fully backward compatible.

**To utilize new data:**
- Update any scripts that parse the JSON to handle the new `repos_detail` field
- New field is additive, so existing parsers will continue to work

### Example Consumer Update

**Before (parsing global data):**
```python
with open('output.json') as f:
    data = json.load(f)

print(f"Total authors: {len(data['commit_authors'])}")
```

**After (parsing per-repo data):**
```python
with open('output.json') as f:
    data = json.load(f)

# Old fields still work
print(f"Total authors: {len(data['commit_authors'])}")

# New field available
for repo, details in data['repos_detail'].items():
    print(f"{repo}: {details['total_commits']} commits")
    print(f"  Top contributor: {max(details['commit_authors'].items(), key=lambda x: x[1])}")
```

---

## Future Enhancements (Out of Scope)

Potential future improvements:

1. **Time-series data**: Track contributions over time
2. **File-level granularity**: Which files each person modified
3. **Commit type analysis**: Features vs fixes vs docs
4. **Contributor profiles**: Aggregate stats per person across all repos
5. **Visualization**: Generate charts from repos_detail data
6. **Export formats**: CSV, Excel, etc.
7. **Incremental updates**: Only analyze new commits since last run

---

## Implementation Checklist

- [ ] Initialize `repos_detail = {}` in `get_contributors()`
- [ ] Change `repo_contributors` from set to dict
- [ ] Change `repo_authors` from set to dict
- [ ] Add `total_commits` counter
- [ ] Update commit loop to count instead of just add
- [ ] Build `repos_detail[repo_name]` entry after each repo
- [ ] Update `.update()` calls to use `.keys()`
- [ ] Add `total_commits` to console output
- [ ] Update `get_contributors()` return statement (3 values)
- [ ] Update `report_contributors()` to unpack 3 values
- [ ] Add `repos_detail` to `output_data` dict
- [ ] Add `indent=2` to `json.dump()`
- [ ] Test with no filter
- [ ] Test with INTERESTING_REPOS filter
- [ ] Verify JSON structure
- [ ] Verify backward compatibility

---

## References

- Main implementation: `github_recent_contributors.py`
- Related specs:
  - `tech_specs__get_contributors.md`
  - `tech_specs__filter_by_repo_list.md`
- Configuration: `.env.example`
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
