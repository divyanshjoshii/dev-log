"""Telegram pings for the daily log.

    python bot/notify.py daily      # after the entry is written
    python bot/notify.py failure    # when the workflow failed

Needs TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID. Without them it prints and exits cleanly.
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

from devlog import TZ, report_day

TOKEN_EXPIRES = {  # secret name -> the expiry date shown on its GitHub token page
    "ACTIVITY_TOKEN": date(2027, 10, 1),
    "DISPATCH_TOKEN": date(2027, 10, 3),
}
WARN_DAYS = {30, 7, 3, 2, 1, 0}
IDLE_AFTER = 3  # days with no activity before the nudges start
NO_ACTIVITY = "No GitHub activity today"


def idle_streak(log_dir, today):
    """Consecutive days up to and including today whose entry says no activity."""
    streak, day = 0, today
    while True:
        path = Path(log_dir) / f"{day:%Y}" / f"{day:%Y-%m-%d}.md"
        if not path.exists() or NO_ACTIVITY not in path.read_text(encoding="utf-8"):
            return streak
        streak, day = streak + 1, day - timedelta(days=1)


def build_daily(entry_text, streak, today):
    body = entry_text.strip().splitlines()
    lines = ["Today's entry is pushed to dev-log.", ""] + body[2:]
    if streak >= IDLE_AFTER:
        lines += ["", f"You have been offline for {streak} days. Come back and commit something."]
    for name, expires in TOKEN_EXPIRES.items():
        left = (expires - today).days
        if left in WARN_DAYS:
            lines += ["", f"{name} expires in {left} days. Make a new one and update the secret."]
    return "\n".join(lines)


def send(text):
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat):
        print("Telegram not configured, skipping:\n" + text)
        return
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=30) as resp:
        if not json.load(resp).get("ok"):
            raise RuntimeError("Telegram rejected the message")
    print("Telegram message sent")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    today = report_day(datetime.now(TZ))
    if mode == "daily":
        entry = Path("log") / f"{today:%Y}" / f"{today:%Y-%m-%d}.md"
        text = entry.read_text(encoding="utf-8") if entry.exists() else ""
        send(build_daily(text, idle_streak("log", today), today))
    elif mode == "failure":
        run = os.environ.get("RUN_URL", "")
        send(f"The daily log run failed. {run}".strip())
    else:
        raise SystemExit("usage: notify.py daily|failure")


if __name__ == "__main__":
    main()
