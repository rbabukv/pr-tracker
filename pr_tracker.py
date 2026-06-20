#!/usr/bin/env python3
"""
PR Tracker — fetches open PRs for configured GitHub users and publishes to Confluence.

Required environment variables:
  GITHUB_TOKEN       — GitHub Personal Access Token (read access to repos)
  CONFLUENCE_TOKEN   — Confluence Personal Access Token (Bearer auth)
"""

import os
import sys
import json
from datetime import datetime, timezone

import requests
import urllib3
import yaml

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def load_config(path="config.yaml"):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, path)
    with open(config_path) as f:
        return yaml.safe_load(f)


def github_headers():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("Error: GITHUB_TOKEN environment variable is not set")
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }


def fetch_open_prs(users, repos):
    """Fetch open PRs authored by the given users across the specified repos using search API."""
    headers = github_headers()
    prs = []

    for repo in repos:
        for user in users:
            query = f"is:pr is:open repo:{repo} author:{user}"
            url = "https://api.github.com/search/issues"
            params = {
                "q": query,
                "per_page": 100,
                "sort": "updated",
                "order": "desc",
            }
            resp = requests.get(url, headers=headers, params=params)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("items", []):
                pr_url = f"https://api.github.com/repos/{repo}/pulls/{item['number']}"
                pr_resp = requests.get(pr_url, headers=headers)
                if pr_resp.status_code == 200:
                    prs.append({"repo": repo, "pr": pr_resp.json()})

    return prs


def fetch_user_name(login):
    """Fetch the display name for a GitHub user."""
    headers = github_headers()
    url = f"https://api.github.com/users/{login}"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json().get("name") or login
    return login


_user_name_cache = {}


def get_user_display(login):
    """Return 'Display Name (login)' with caching."""
    if login not in _user_name_cache:
        _user_name_cache[login] = fetch_user_name(login)
    name = _user_name_cache[login]
    if name == login:
        return login
    return f"{name} ({login})"


def fetch_reviews(repo, pr_number):
    """Fetch reviews for a specific PR."""
    headers = github_headers()
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews"
    resp = requests.get(url, headers=headers, params={"per_page": 100})
    if resp.status_code != 200:
        return []
    return resp.json()


def format_time(iso_str):
    """Convert ISO timestamp to number of days ago."""
    if not iso_str:
        return "—"
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    days = (now - dt).days
    if days == 0:
        return "today"
    if days == 1:
        return "1 day"
    return f"{days} days"


def determine_pr_state(pr):
    """Determine the display state of a PR."""
    if pr.get("draft"):
        return "Draft"
    if pr.get("mergeable_state") == "blocked":
        return "Changes Requested"
    if pr.get("mergeable_state") == "behind":
        return "Behind Base"
    if pr.get("mergeable_state") == "dirty":
        return "Merge Conflicts"
    return "Open"


def build_pr_table(config):
    """Build the full PR data table."""
    users = config["github_users"]
    repos = config["repos"]

    raw_prs = fetch_open_prs(users, repos)

    rows = []
    for item in raw_prs:
        repo = item["repo"]
        pr = item["pr"]
        pr_number = pr["number"]

        reviews = fetch_reviews(repo, pr_number)

        bot_suffixes = ("[bot]",)
        reviewer_names = []
        approvers = []
        last_review_time = None
        for review in reviews:
            reviewer = review["user"]["login"]
            is_bot = reviewer.endswith(bot_suffixes[0])
            if not is_bot and reviewer not in reviewer_names:
                reviewer_names.append(reviewer)
            if review.get("state") == "APPROVED" and not is_bot:
                if reviewer not in approvers:
                    approvers.append(reviewer)
            submitted = review.get("submitted_at")
            if submitted:
                if last_review_time is None or submitted > last_review_time:
                    last_review_time = submitted

        state = determine_pr_state(pr)

        rows.append({
            "repo": repo,
            "title": pr["title"],
            "url": pr["html_url"],
            "author": get_user_display(pr["user"]["login"]),
            "state": state,
            "created": pr["created_at"],
            "last_modified": pr["updated_at"],
            "last_reviewed": last_review_time,
            "reviewers": reviewer_names,
            "approvers": [get_user_display(a) for a in approvers],
            "number": pr_number,
        })

    rows.sort(key=lambda r: (r["author"].lower(), r["last_modified"]), reverse=True)
    return rows


def generate_html_table(rows):
    """Generate an HTML table suitable for Confluence storage format."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    html = f'<p><strong>Last updated:</strong> {now_str}</p>\n'
    html += '<table>\n<thead>\n<tr>\n'
    html += '<th>Author</th>\n'
    html += '<th>Repository</th>\n'
    html += '<th>PR</th>\n'
    html += '<th>State</th>\n'
    html += '<th>Last Modified</th>\n'
    html += '<th>Last Reviewed</th>\n'
    html += '<th>Reviewers</th>\n'
    html += '<th>Approver(s)</th>\n'
    html += '</tr>\n</thead>\n<tbody>\n'

    for row in rows:
        reviewers_str = ", ".join(row["reviewers"]) if row["reviewers"] else "—"
        approvers_str = ", ".join(row["approvers"]) if row["approvers"] else "—"
        html += '<tr>\n'
        html += f'<td>{row["author"]}</td>\n'
        html += f'<td>{row["repo"]}</td>\n'
        html += f'<td><a href="{row["url"]}">#{row["number"]} {row["title"]}</a></td>\n'
        html += f'<td>{row["state"]}</td>\n'
        html += f'<td>{format_time(row["last_modified"])}</td>\n'
        html += f'<td>{format_time(row["last_reviewed"])}</td>\n'
        html += f'<td>{reviewers_str}</td>\n'
        html += f'<td>{approvers_str}</td>\n'
        html += '</tr>\n'

    html += '</tbody>\n</table>\n'

    if not rows:
        html += '<p><em>No open PRs found for the configured users.</em></p>\n'

    return html


def print_terminal_table(rows):
    """Print a readable table to the terminal."""
    if not rows:
        print("No open PRs found for the configured users.")
        return

    fmt = "{:<15} {:<30} {:<50} {:<12} {:<14} {:<14} {:<30} {}"
    header = fmt.format("Author", "Repo", "PR", "State", "Modified", "Reviewed", "Reviewers", "Approver(s)")
    print(header)
    print("—" * len(header))

    for row in rows:
        reviewers_str = ", ".join(row["reviewers"]) if row["reviewers"] else "—"
        approvers_str = ", ".join(row["approvers"]) if row["approvers"] else "—"
        title = row["title"][:45] + "..." if len(row["title"]) > 45 else row["title"]
        pr_str = f"#{row['number']} {title}"
        print(fmt.format(
            row["author"],
            row["repo"],
            pr_str,
            row["state"],
            format_time(row["last_modified"]),
            format_time(row["last_reviewed"]),
            reviewers_str,
            approvers_str,
        ))


def publish_to_confluence(html_content, config):
    """Create or update the Confluence page with the PR table."""
    conf = config["confluence"]
    base_url = conf["base_url"].rstrip("/")
    space_key = conf["space_key"]
    page_title = conf["page_title"]
    verify_ssl = conf.get("verify_ssl", False)

    token = os.environ.get("CONFLUENCE_TOKEN")
    if not token:
        sys.exit("Error: CONFLUENCE_TOKEN environment variable is not set")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    # Search for existing page
    search_url = f"{base_url}/rest/api/content"
    params = {
        "spaceKey": space_key,
        "title": page_title,
        "expand": "version",
    }
    resp = requests.get(search_url, headers=headers, params=params, verify=verify_ssl)
    if resp.status_code != 200:
        print(f"Confluence API error (HTTP {resp.status_code}):")
        print(resp.text[:500])
        sys.exit(1)
    try:
        results = resp.json().get("results", [])
    except requests.exceptions.JSONDecodeError:
        print("Confluence returned non-JSON response:")
        print(resp.text[:500])
        sys.exit(1)

    if results:
        # Update existing page
        page = results[0]
        page_id = page["id"]
        current_version = page["version"]["number"]

        payload = {
            "id": page_id,
            "type": "page",
            "title": page_title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": html_content,
                    "representation": "storage",
                }
            },
            "version": {"number": current_version + 1},
        }

        url = f"{base_url}/rest/api/content/{page_id}"
        resp = requests.put(url, headers=headers, data=json.dumps(payload), verify=verify_ssl)
        resp.raise_for_status()
        print(f"Updated Confluence page: {base_url}/pages/viewpage.action?pageId={page_id}")
    else:
        # Create new page
        payload = {
            "type": "page",
            "title": page_title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": html_content,
                    "representation": "storage",
                }
            },
        }

        parent_page_id = conf.get("parent_page_id")
        if parent_page_id:
            payload["ancestors"] = [{"id": str(parent_page_id)}]

        resp = requests.post(search_url, headers=headers, data=json.dumps(payload), verify=verify_ssl)
        resp.raise_for_status()
        page_id = resp.json()["id"]
        print(f"Created Confluence page: {base_url}/pages/viewpage.action?pageId={page_id}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Track open PRs and publish to Confluence")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--dry-run", action="store_true", help="Print table to terminal without publishing")
    parser.add_argument("--html", action="store_true", help="Output HTML to stdout instead of publishing")
    args = parser.parse_args()

    config = load_config(args.config)
    print(f"Fetching PRs for users: {', '.join(config['github_users'])}")
    print(f"Searching repos: {', '.join(config['repos'])}")

    rows = build_pr_table(config)
    print(f"Found {len(rows)} open PR(s)\n")

    if args.dry_run:
        print_terminal_table(rows)
        return

    html = generate_html_table(rows)

    if args.html:
        print(html)
        return

    publish_to_confluence(html, config)


if __name__ == "__main__":
    main()
