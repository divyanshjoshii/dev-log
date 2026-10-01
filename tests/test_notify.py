import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bot"))
import notify

TODAY = date(2026, 10, 10)


def write(root, day, text):
    p = Path(root) / f"{day:%Y}" / f"{day:%Y-%m-%d}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


class IdleStreakTest(unittest.TestCase):
    def test_counts_consecutive_idle_days(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, TODAY - timedelta(days=3), "# x\n\nCommits: 2\n")
            for n in range(3):
                write(d, TODAY - timedelta(days=n), "# x\n\n" + notify.NO_ACTIVITY + ".\n")
            self.assertEqual(notify.idle_streak(d, TODAY), 3)

    def test_missing_entry_stops_streak(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, TODAY, "# x\n\n" + notify.NO_ACTIVITY + ".\n")
            self.assertEqual(notify.idle_streak(d, TODAY), 1)


class MessageTest(unittest.TestCase):
    def test_nudge_only_from_three_days(self):
        entry = "# Day\n\nCommits: 1\n"
        self.assertNotIn("offline", notify.build_daily(entry, 2, TODAY))
        self.assertIn("offline for 3 days", notify.build_daily(entry, 3, TODAY))

    def test_token_expiry_warning(self):
        entry = "# Day\n\nCommits: 1\n"
        soon = notify.TOKEN_EXPIRES - timedelta(days=7)
        self.assertIn("expires in 7 days", notify.build_daily(entry, 0, soon))
        self.assertNotIn("expires", notify.build_daily(entry, 0, TODAY))


if __name__ == "__main__":
    unittest.main()
