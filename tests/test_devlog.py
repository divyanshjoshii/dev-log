import sys
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bot"))
import devlog

DAY = datetime(2026, 10, 1, tzinfo=devlog.TZ)


def collection(repos=(), prs=0, issues=0, reviews=0, restricted=0):
    return {
        "totalPullRequestContributions": prs,
        "totalIssueContributions": issues,
        "totalPullRequestReviewContributions": reviews,
        "restrictedContributionsCount": restricted,
        "commitContributionsByRepository": [
            {
                "repository": {
                    "nameWithOwner": n,
                    "isPrivate": p,
                    "primaryLanguage": {"name": lang} if lang else None,
                },
                "contributions": {"totalCount": c},
            }
            for n, p, lang, c in repos
        ],
    }


class ReportDayTest(unittest.TestCase):
    def test_late_run_after_midnight_finishes_yesterday(self):
        late = datetime(2026, 10, 2, 3, 52, tzinfo=devlog.TZ)
        self.assertEqual(devlog.report_day(late), date(2026, 10, 1))

    def test_daytime_run_reports_today(self):
        self.assertEqual(
            devlog.report_day(datetime(2026, 10, 2, 10, 17, tzinfo=devlog.TZ)),
            date(2026, 10, 2),
        )
        self.assertEqual(
            devlog.report_day(datetime(2026, 10, 2, 23, 40, tzinfo=devlog.TZ)),
            date(2026, 10, 2),
        )


class RenderTest(unittest.TestCase):
    def test_no_activity_says_so(self):
        text = devlog.render(DAY, devlog.summarize(collection()))
        self.assertIn("No GitHub activity today", text)

    def test_private_repo_never_named(self):
        s = devlog.summarize(
            collection(
                [
                    ("divyanshjoshii/saathi", True, "Python", 3),
                    ("divyanshjoshii/workout-tracker", False, "JavaScript", 2),
                ]
            )
        )
        text = devlog.render(DAY, s)
        self.assertNotIn("saathi", text)
        self.assertIn("private repositories: 3", text)
        self.assertIn("workout-tracker", text)
        self.assertIn("Commits: 5", text)

    def test_private_language_not_listed(self):
        s = devlog.summarize(
            collection(
                [
                    ("divyanshjoshii/saathi", True, "Rust", 3),
                    ("divyanshjoshii/workout-tracker", False, "JavaScript", 2),
                ]
            )
        )
        text = devlog.render(DAY, s)
        self.assertNotIn("Rust", text)
        self.assertIn("JavaScript", text)

    def test_guard_blocks_private_name(self):
        with self.assertRaises(RuntimeError):
            devlog.guard("worked on Saathi today", {"divyanshjoshii/saathi"})
        devlog.guard("worked on workout-tracker", {"divyanshjoshii/saathi"})

    def test_hidden_private_contributions_count_as_activity(self):
        s = devlog.summarize(collection(restricted=2))
        text = devlog.render(DAY, s)
        self.assertNotIn("No GitHub activity", text)
        self.assertIn("other private contributions (count only): 2", text)

    def test_bot_commits_are_not_counted_but_real_work_is(self):
        self.assertEqual(
            devlog.real_commits(["log: 2026-10-01", "Add chat bot", "log: 2026-10-02"]), 1
        )
        bot_only = devlog.summarize(collection([(devlog.LOG_REPO, False, None, 1)]), own_commits=0)
        self.assertIn("No GitHub activity today", devlog.render(DAY, bot_only))
        real = devlog.summarize(collection([(devlog.LOG_REPO, False, None, 3)]), own_commits=2)
        text = devlog.render(DAY, real)
        self.assertIn("Commits: 2", text)
        self.assertIn("dev-log", text)


if __name__ == "__main__":
    unittest.main()
