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


class DescribeRunTest(unittest.TestCase):
    def test_sweep_is_told_apart_from_day_runs(self):
        self.assertEqual(notify.describe_run("schedule", "47 18 * * *"), "12:17 AM late sweep")
        self.assertEqual(notify.describe_run("schedule", "47 4 * * *"), "10:17 AM run")
        self.assertEqual(notify.describe_run("schedule", "17 17 * * *"), "10:47 PM run")

    def test_unknown_schedule_and_manual_runs(self):
        self.assertEqual(notify.describe_run("schedule", "0 0 * * *"), "scheduled run")
        self.assertEqual(notify.describe_run("workflow_dispatch", ""), "manual run")
        self.assertEqual(notify.describe_run(None, None), "manual run")


class QuietHoursTest(unittest.TestCase):
    def at(self, hour):
        from datetime import datetime

        return datetime(2026, 10, 3, hour, 30, tzinfo=notify.TZ)

    def test_late_scheduled_run_stays_silent(self):
        self.assertTrue(notify.quiet_hours(self.at(3), "schedule"))
        self.assertTrue(notify.quiet_hours(self.at(0), "schedule"))

    def test_evening_and_morning_runs_ping(self):
        self.assertFalse(notify.quiet_hours(self.at(22), "schedule"))
        self.assertFalse(notify.quiet_hours(self.at(6), "schedule"))

    def test_manual_run_always_pings(self):
        self.assertFalse(notify.quiet_hours(self.at(3), "workflow_dispatch"))


class MessageTest(unittest.TestCase):
    def test_nudge_only_from_three_days(self):
        entry = "# Day\n\nCommits: 1\n"
        self.assertNotIn("offline", notify.build_daily(entry, 2, TODAY))
        self.assertIn("offline for 3 days", notify.build_daily(entry, 3, TODAY))

    def test_token_expiry_warning(self):
        entry = "# Day\n\nCommits: 1\n"
        soon = notify.TOKEN_EXPIRES["ACTIVITY_TOKEN"] - timedelta(days=7)
        out = notify.build_daily(entry, 0, soon)
        self.assertIn("ACTIVITY_TOKEN expires in 7 days", out)
        self.assertNotIn("DISPATCH_TOKEN", out)
        later = notify.TOKEN_EXPIRES["DISPATCH_TOKEN"] - timedelta(days=1)
        self.assertIn("DISPATCH_TOKEN expires in 1 days", notify.build_daily(entry, 0, later))
        self.assertNotIn("expires", notify.build_daily(entry, 0, TODAY))


if __name__ == "__main__":
    unittest.main()
