"""Build context.md: the only data the chat bot is allowed to see.

Only public repositories and the public daily log go in. Needs ACTIVITY_TOKEN.
    python bot/context.py
"""

import json
import os
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from devlog import TZ, USER, activity, guard, render
from notify import NO_ACTIVITY

DAYS = 30
REPOS = 8


def api(path, token):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={"Authorization": f"bearer {token}", "User-Agent": "dev-log"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def public_repos(token):
    repos = api(f"/users/{USER}/repos?type=owner&sort=pushed&per_page=30", token)
    return [r for r in repos if not r["private"] and not r["fork"]][:REPOS]


def repo_line(repo, token):
    commits = api(f"/repos/{repo['full_name']}/commits?per_page=5", token)
    msgs = "; ".join(c["commit"]["message"].splitlines()[0] for c in commits)
    return (
        f"- {repo['name']} | {repo['description'] or 'no description'} | "
        f"{repo['language'] or 'n/a'} | last push {repo['pushed_at'][:10]} | "
        f"open issues {repo['open_issues_count']} | recent commits: {msgs}"
    )


def day_entry(day, log_dir, token):
    """Use the written log entry if there is one, otherwise ask GitHub for that day."""
    path = Path(log_dir) / f"{day:%Y}" / f"{day:%Y-%m-%d}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    start = datetime(day.year, day.month, day.day, tzinfo=TZ)
    summary = activity(start, start + timedelta(days=1), token)
    text = render(start, summary)
    guard(text, summary["private_names"])
    return text


def recent_days(log_dir, today, token):
    """Last DAYS days, newest first, as (date, text) pairs."""
    days = [today - timedelta(days=n) for n in range(DAYS)]
    return [(d, day_entry(d, log_dir, token)) for d in days]


def idle_days(entries):
    streak = 0
    for _, text in entries:
        if NO_ACTIVITY not in text:
            break
        streak += 1
    return streak


def build(today, entries, repo_lines):
    streak = idle_days(entries)
    last = "today" if streak == 0 else (today - timedelta(days=streak)).isoformat()
    if streak == len(entries):
        last = f"none in the last {len(entries)} days"
    lines = [
        "# FACTS",
        f"Today: {today.isoformat()}",
        f"Days in a row with no GitHub activity (up to today): {streak}",
        f"Last day with activity: {last}",
        "",
        "## Public repos",
        *repo_lines,
        "",
        f"## Last {len(entries)} days (newest first, private repos are counts only)",
    ]
    for day, text in entries:
        body = text.split("\n", 2)[2].strip()
        lines.append(f"### {day.isoformat()}\n{body}")
    return "\n".join(lines) + "\n"


def main():
    token = os.environ["ACTIVITY_TOKEN"]
    today = datetime.now(TZ).date()
    repos = public_repos(token)
    text = build(
        today,
        recent_days("log", today, token),
        [repo_line(r, token) for r in repos],
    )
    Path("context.md").write_text(text, encoding="utf-8")
    print(f"wrote context.md ({len(text)} chars, {len(repos)} public repos)")


if __name__ == "__main__":
    main()
