"""Watchdog: make sure today has a bot commit, start a run if it does not, alert if that fails."""

import json
import urllib.error
import urllib.request
from datetime import timedelta, timezone

import core

IST = timezone(timedelta(hours=5, minutes=30))
FINAL_SCHEDULE = "30 16 * * *"  # 22:00 IST, keep in step with vercel.json


def has_bot_commit(messages):
    return any(m.startswith("log: ") for m in messages)


def fetch_messages(now, token):
    """Commit messages since 00:00 UTC today. That is the same date in UTC and IST until 23:59 IST."""
    since = now.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    url = f"https://api.github.com/repos/{core.REPO}/commits?since={since:%Y-%m-%dT%H:%M:%SZ}&per_page=100"
    headers = {"User-Agent": "git-guy-bot"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=15) as resp:
        return [c["commit"]["message"] for c in json.load(resp)]


def _why(exc):
    return getattr(exc, "code", None) or type(exc).__name__


def run_check(
    env, now, mode, fetch=fetch_messages, dispatch=core.dispatch_workflow, notify=core.send_telegram
):
    """Return "ok", "started" or "failed". Alert on the final check, or on any problem."""
    token = env.get("DISPATCH_TOKEN")
    problems = []
    try:
        if has_bot_commit(fetch(now, token)):
            return "ok"
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
        problems.append(f"could not read commits ({_why(exc)})")

    started = False
    if not token:
        problems.append("DISPATCH_TOKEN is not set")
    else:
        try:
            dispatch(token)
            started = True
        except (urllib.error.URLError, TimeoutError) as exc:
            problems.append(f"could not start a run ({_why(exc)})")

    if mode == "final" or problems:
        text = f"No log commit yet for today at {now.astimezone(IST):%H:%M} IST."
        text += " I started a run." if started else " I could not start a run."
        if problems:
            text += " Problems: " + "; ".join(problems) + "."
        notify(env["TELEGRAM_BOT_TOKEN"], env["TELEGRAM_CHAT_ID"], text)
    return "started" if started else "failed"
