"""Write one honest diary entry for a day of GitHub activity.

Usage:
    python bot/devlog.py --dry-run            # print today's entry
    python bot/devlog.py --date 2026-10-01    # write log/2026/2026-10-01.md

Needs ACTIVITY_TOKEN (read access) in the environment for live runs.
"""

import argparse
import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

USER = "divyanshjoshii"
LOG_REPO = f"{USER}/dev-log"  # excluded so the bot does not log itself
TZ = timezone(timedelta(hours=5, minutes=30))  # IST

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount
      commitContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner isPrivate primaryLanguage { name } }
        contributions { totalCount }
      }
    }
  }
}
"""


def fetch(day_start, day_end, token):
    body = json.dumps(
        {
            "query": QUERY,
            "variables": {
                "login": USER,
                "from": day_start.astimezone(timezone.utc).isoformat(),
                "to": day_end.astimezone(timezone.utc).isoformat(),
            },
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "User-Agent": "dev-log"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data or not data.get("data", {}).get("user"):
        # Logs are public in a public repo: report messages only, never the payload.
        msgs = [e.get("message", "?") for e in data.get("errors", [])]
        raise RuntimeError(f"GitHub API error: {msgs or 'user not found'}")
    return data["data"]["user"]["contributionsCollection"]


def summarize(collection):
    """Private repos contribute only a commit count. Their names and
    languages never enter the summary (names are kept for the leak guard)."""
    public, private_commits, languages, private_names = {}, 0, {}, set()
    for item in collection["commitContributionsByRepository"]:
        repo = item["repository"]
        if repo["nameWithOwner"] == LOG_REPO:
            continue
        count = item["contributions"]["totalCount"]
        if repo["isPrivate"]:
            private_commits += count
            private_names.add(repo["nameWithOwner"])
            continue
        public[repo["nameWithOwner"]] = count
        lang = (repo["primaryLanguage"] or {}).get("name")
        if lang:
            languages[lang] = languages.get(lang, 0) + count
    return {
        "public": public,
        "private_commits": private_commits,
        "private_names": private_names,
        "languages": sorted(languages, key=languages.get, reverse=True),
        "prs": collection["totalPullRequestContributions"],
        "issues": collection["totalIssueContributions"],
        "reviews": collection["totalPullRequestReviewContributions"],
        "restricted": collection.get("restrictedContributionsCount", 0),
    }


def render(day, s):
    total = sum(s["public"].values()) + s["private_commits"]
    lines = [f"# {day:%A, %d %B %Y}", ""]
    if total + s["prs"] + s["issues"] + s["reviews"] + s["restricted"] == 0:
        lines.append("No GitHub activity today. Took the day off.")
        return "\n".join(lines) + "\n"
    lines.append(f"Commits: {total}")
    for name, n in sorted(s["public"].items(), key=lambda kv: -kv[1]):
        lines.append(f"- [{name}](https://github.com/{name}): {n}")
    if s["private_commits"]:
        lines.append(f"- private repositories: {s['private_commits']}")
    if s["restricted"]:
        lines.append(f"- other private contributions (count only): {s['restricted']}")
    extras = [
        f"{s[k]} {label}"
        for k, label in (("prs", "pull requests"), ("issues", "issues"), ("reviews", "reviews"))
        if s[k]
    ]
    if extras:
        lines += ["", "Also: " + ", ".join(extras) + "."]
    if s["languages"]:
        lines += ["", "Languages: " + ", ".join(s["languages"]) + "."]
    return "\n".join(lines) + "\n"


def guard(text, private_names):
    """Last line of defence: refuse to publish text that mentions a private repo."""
    lowered = text.lower()
    for full in private_names:
        short = full.split("/")[-1].lower()
        if full.lower() in lowered or re.search(rf"\b{re.escape(short)}\b", lowered):
            raise RuntimeError("leak guard: output mentions a private repo; nothing written")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD in IST (default: today)")
    ap.add_argument("--out", default="log", help="output directory")
    ap.add_argument("--dry-run", action="store_true", help="print, do not write")
    args = ap.parse_args()

    now = datetime.now(TZ)
    day = (
        datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=TZ)
        if args.date
        else now.replace(hour=0, minute=0, second=0, microsecond=0)
    )
    end = min(day + timedelta(days=1), now)

    token = os.environ.get("ACTIVITY_TOKEN")
    if not token:
        raise SystemExit("ACTIVITY_TOKEN is not set")
    summary = summarize(fetch(day, end, token))
    text = render(day, summary)
    guard(text, summary["private_names"])

    if args.dry_run:
        print(text)
        return
    path = Path(args.out) / f"{day:%Y}" / f"{day:%Y-%m-%d}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
