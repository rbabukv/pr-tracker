# PR Tracker

A command-line tool that tracks open Pull Requests for configured GitHub users across specified repositories and publishes a summary table to Confluence.

## Overview

PR Tracker automates the process of monitoring open PRs for your team. It queries the GitHub API to gather PR details — including review status, approvals, and merge readiness — then formats the data into a structured table that can be viewed in the terminal, exported as HTML, or published directly to a Confluence wiki page.

---

## Features

### 1. GitHub PR Fetching

- Uses the GitHub Search API to find open PRs authored by configured users across specified repositories.
- Fetches detailed PR metadata including title, state, timestamps, and mergeable status.
- Supports tracking multiple users and multiple repositories in a single run.

### 2. Review and Approval Tracking

- Fetches all reviews for each PR.
- Identifies unique reviewers (excluding bots).
- Tracks which reviewers have approved the PR.
- Records the timestamp of the most recent review activity.

### 3. PR State Detection

Determines the current state of each PR based on its metadata:

| State | Condition |
|-------|-----------|
| **Draft** | PR is marked as a draft |
| **Changes Requested** | Mergeable state is "blocked" |
| **Behind Base** | PR branch is behind the base branch |
| **Merge Conflicts** | PR has merge conflicts |
| **Open** | Default state for active PRs |

### 4. User Display Name Resolution

- Resolves GitHub login usernames to full display names via the GitHub Users API.
- Caches resolved names to minimize API calls.
- Falls back to the login username if no display name is set.
- Output format: `Display Name (login)` or just `login` if no name is available.

### 5. Human-Friendly Time Formatting

- Converts ISO timestamps to relative time (e.g., "today", "1 day", "5 days").
- Applied to "Last Modified" and "Last Reviewed" columns.

### 6. Terminal Output (Dry Run)

- Prints a formatted table directly to the terminal.
- Useful for quick checks without publishing anywhere.
- Truncates long PR titles to keep the output readable.

### 7. HTML Output

- Generates a Confluence-compatible HTML table.
- Includes a "Last updated" timestamp header.
- PR titles are hyperlinked to the actual GitHub PR page.
- Displays a message when no open PRs are found.

### 8. Confluence Publishing

- Creates a new Confluence page if one doesn't already exist.
- Updates the existing page (incrementing the version number) if it does exist.
- Supports nesting the page under a parent page via `parent_page_id`.
- Uses Bearer token authentication.
- Configurable SSL verification (disabled by default for internal wikis).

---

## Prerequisites

- Python 3.8+
- A GitHub Personal Access Token with read access to the target repositories
- A Confluence Personal Access Token (only required if publishing to Confluence)

---

## Installation

### Step 1: Clone or download the project

```bash
cd /path/to/your/workspace
git clone <repository-url> pr-tracker
cd pr-tracker
```

### Step 2: Install dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `requests` — HTTP client for GitHub and Confluence APIs
- `PyYAML` — YAML parser for configuration file

### Step 3: Set environment variables

```bash
export GITHUB_TOKEN="your-github-personal-access-token"
export CONFLUENCE_TOKEN="your-confluence-personal-access-token"
```

> `CONFLUENCE_TOKEN` is only required when publishing to Confluence (not needed for `--dry-run` or `--html` modes).

---

## Configuration

Edit `config.yaml` to specify which users and repositories to track, along with Confluence publishing settings.

```yaml
# GitHub usernames to track
github_users:
  - username1
  - username2
  - username3

# Repositories to search (format: "org/repo")
repos:
  - my-org/my-repo
  - another-org/another-repo

# Confluence settings
confluence:
  base_url: "https://your-confluence-instance.com"
  space_key: "YOURSPACE"
  page_title: "Open PR Tracker"
  # Optional: nest the page under an existing parent page
  # parent_page_id: "123456"
  # Optional: enable/disable SSL verification (default: false)
  # verify_ssl: false
```

### Configuration Fields

| Field | Description |
|-------|-------------|
| `github_users` | List of GitHub usernames whose PRs to track |
| `repos` | List of repositories in `org/repo` format |
| `confluence.base_url` | Base URL of your Confluence instance |
| `confluence.space_key` | Confluence space key where the page will be created |
| `confluence.page_title` | Title of the Confluence page |
| `confluence.parent_page_id` | (Optional) ID of the parent page for nesting |
| `confluence.verify_ssl` | (Optional) Whether to verify SSL certificates (default: `false`) |

---

## Usage

### Print PR table to terminal (dry run)

```bash
python pr_tracker.py --dry-run
```

This fetches all open PRs and prints a formatted table to the terminal without publishing anywhere.

### Output HTML to stdout

```bash
python pr_tracker.py --html
```

Prints the generated HTML table to stdout. Useful for piping to a file or integrating with other tools:

```bash
python pr_tracker.py --html > pr_report.html
```

### Publish to Confluence

```bash
python pr_tracker.py
```

Fetches PRs and publishes (or updates) the Confluence page specified in `config.yaml`.

### Use a custom config file

```bash
python pr_tracker.py --config /path/to/custom-config.yaml
```

---

## Command-Line Options

| Option | Description |
|--------|-------------|
| `--config PATH` | Path to config file (default: `config.yaml` in the script directory) |
| `--dry-run` | Print table to terminal without publishing |
| `--html` | Output HTML to stdout instead of publishing |

---

## Output Table Columns

| Column | Description |
|--------|-------------|
| **Author** | PR author's display name and GitHub username |
| **Repository** | The `org/repo` where the PR is open |
| **PR** | PR number and title (linked to GitHub in HTML output) |
| **State** | Current PR state (Draft, Open, Changes Requested, etc.) |
| **Last Modified** | Time since last update (e.g., "3 days") |
| **Last Reviewed** | Time since last review activity |
| **Reviewers** | List of non-bot users who have reviewed |
| **Approver(s)** | List of users who approved the PR |

---

## Example

```bash
$ export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
$ python pr_tracker.py --dry-run

Fetching PRs for users: alice, bob, charlie
Searching repos: my-org/my-repo
Found 3 open PR(s)

Author          Repo                           PR                                                 State        Modified       Reviewed       Reviewers                      Approver(s)
————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————————
Alice (alice)   my-org/my-repo                 #142 Add new authentication flow                   Open         2 days         1 day          dave, eve                      dave
Bob (bob)       my-org/my-repo                 #138 Fix pagination bug in search results          Open         5 days         3 days         alice                          —
Charlie         my-org/my-repo                 #135 [WIP] Refactor database layer                 Draft        today          —              —                              —
```

---

## Automating with Cron

To run the tracker on a schedule (e.g., every weekday at 9 AM):

```bash
0 9 * * 1-5 GITHUB_TOKEN="ghp_xxx" CONFLUENCE_TOKEN="xxx" /usr/bin/python3 /path/to/pr_tracker.py
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Error: GITHUB_TOKEN environment variable is not set` | Export `GITHUB_TOKEN` before running the script |
| `Error: CONFLUENCE_TOKEN environment variable is not set` | Export `CONFLUENCE_TOKEN` (only needed for publishing) |
| HTTP 401 from GitHub | Verify your token has read access to the target repos |
| HTTP 403 rate limit | GitHub API rate limit reached; wait or use a token with higher limits |
| SSL errors with Confluence | Set `verify_ssl: false` in config (for internal instances with self-signed certs) |
