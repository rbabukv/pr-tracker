---
name: pr-tracker
description: Track open PRs for the configured team members across sgl-project repos and publish the summary table to the Confluence "Open PR Tracker" page. Use when asked to run/refresh the PR tracker, preview open team PRs, or add/remove tracked users or repos.
argument-hint: "[--dry-run] [--html [--output <path>]] [--config <path>] [--add-user|--remove-user <login>] [--add-repo|--remove-repo <org/repo>]"
---

Track open PRs for the users in `config.yaml` and publish the summary table to Confluence.

## Arguments

Arguments are passed inline (space-separated):

- `--dry-run` (optional): Print the PR table to the terminal without publishing
- `--html` (optional): Print the Confluence HTML to stdout instead of publishing
- `--output <path>` (optional): With `--html`, save the HTML to a file for preview
- `--config <path>` (optional): Use a different config file (default: `config.yaml`)
- `--add-user <login>` / `--remove-user <login>` (optional): Edit `github_users` in `config.yaml` before running
- `--add-repo <org/repo>` / `--remove-repo <org/repo>` (optional): Edit `repos` in `config.yaml` before running

## What to do

1. Work from the repository root (the directory containing `pr_tracker.py`).
2. Make sure `GITHUB_TOKEN` (and `CONFLUENCE_TOKEN` unless using `--dry-run`/`--html`) are set. If not already exported, load them the way cron does:
   `set -a && . /etc/environment && . ~/.bash_ai && set +a`
   If they're still missing, stop and ask the user to export them. Never print token values.
3. If any `--add-*` / `--remove-*` args were given, edit `config.yaml` accordingly (avoid duplicate entries) and show the user the diff.
4. Run the tracker based on the arguments:
   - `--dry-run`: `python3 pr_tracker.py --dry-run`
   - `--html`: `python3 pr_tracker.py --html` (redirect to `<path>` if `--output` given)
   - Default (no args): `python3 pr_tracker.py` — publishes/updates the Confluence page
   - Append `--config <path>` if specified
5. Report the results:
   - Users and repos that were searched
   - How many open PRs were found
   - Notable PRs: merge conflicts, behind base, changes requested, or no reviewers yet
   - The Confluence page URL if published, or the error if it failed

## Examples

- `/pr-tracker` — fetch PRs and update the Confluence page
- `/pr-tracker --dry-run` — preview the table in the terminal
- `/pr-tracker --html --output /tmp/pr_tracker.html` — save HTML for preview
- `/pr-tracker --add-user octocat --dry-run` — add a user and preview

## Notes

- Requires `requests` and `PyYAML` (`pip install -r requirements.txt`)
- Confluence target is set in `config.yaml` (currently https://wiki.ith.intel.com, space `AICFIndia`, page "Open PR Tracker")
- A cron job may also run this on a schedule, logging to `cron.log`; check `tail cron.log` for recent failures
- HTTP 403 from GitHub search usually means the rate limit was hit (one search per user×repo); wait a minute and retry
- Don't commit or push config changes unless the user asks
