"""Build context.md: the only data the chat bot is allowed to see.

Only public repositories and the public daily log go in. Needs ACTIVITY_TOKEN.
    python bot/context.py
"""

import json
import os
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from devlog import TZ, USER
from notify import idle_streak

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


def recent_days(log_dir, today):
    out = []
    for n in range(DAYS):
        day = today - timedelta(days=n)
        path = Path(log_dir) / f"{day:%Y}" / f"{day:%Y-%m-%d}.md"
        if path.exists():
            out.append(f"### {day:%Y-%m-%d}\n" + path.read_text(encoding="utf-8").split("\n", 2)[2])
    return out


def build(today, streak, repo_lines, days):
    last = "today" if streak == 0 else (today - timedelta(days=streak)).isoformat()
    lines = [
        "# FACTS",
        f"Today: {today.isoformat()}",
        f"Days in a row with no GitHub activity (up to today): {streak}",
        f"Last day with activity: {last}",
        "",
        "## Public repos",
        *repo_lines,
        "",
        "## Recent days (newest first)",
        *days,
    ]
    return "\n".join(lines) + "\n"


def main():
    token = os.environ["ACTIVITY_TOKEN"]
    today = datetime.now(TZ).date()
    repos = public_repos(token)
    text = build(
        today,
        idle_streak("log", today),
        [repo_line(r, token) for r in repos],
        recent_days("log", today),
    )
    Path("context.md").write_text(text, encoding="utf-8")
    print(f"wrote context.md ({len(text)} chars, {len(repos)} public repos)")


if __name__ == "__main__":
    main()
