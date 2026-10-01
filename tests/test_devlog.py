import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bot"))
import devlog  # noqa: E402

DAY = datetime(2026, 10, 1, tzinfo=devlog.TZ)


def collection(repos=(), prs=0, issues=0, reviews=0):
    return {
        "totalPullRequestContributions": prs,
        "totalIssueContributions": issues,
        "totalPullRequestReviewContributions": reviews,
        "commitContributionsByRepository": [
            {"repository": {"nameWithOwner": n, "isPrivate": p,
                            "primaryLanguage": {"name": lang} if lang else None},
             "contributions": {"totalCount": c}}
            for n, p, lang, c in repos
        ],
    }


class RenderTest(unittest.TestCase):
    def test_no_activity_says_so(self):
        text = devlog.render(DAY, devlog.summarize(collection()))
        self.assertIn("No GitHub activity today", text)

    def test_private_repo_never_named(self):
        s = devlog.summarize(collection([
            ("divyanshjoshii/saathi", True, "Python", 3),
            ("divyanshjoshii/workout-tracker", False, "JavaScript", 2),
        ]))
        text = devlog.render(DAY, s)
        self.assertNotIn("saathi", text)
        self.assertIn("private repositories: 3", text)
        self.assertIn("workout-tracker", text)
        self.assertIn("Commits: 5", text)

    def test_private_language_not_listed(self):
        s = devlog.summarize(collection([
            ("divyanshjoshii/saathi", True, "Rust", 3),
            ("divyanshjoshii/workout-tracker", False, "JavaScript", 2),
        ]))
        text = devlog.render(DAY, s)
        self.assertNotIn("Rust", text)
        self.assertIn("JavaScript", text)

    def test_guard_blocks_private_name(self):
        with self.assertRaises(RuntimeError):
            devlog.guard("worked on Saathi today", {"divyanshjoshii/saathi"})
        devlog.guard("worked on workout-tracker", {"divyanshjoshii/saathi"})

    def test_dev_log_itself_is_excluded(self):
        s = devlog.summarize(collection([(devlog.LOG_REPO, False, None, 1)]))
        self.assertIn("No GitHub activity today", devlog.render(DAY, s))


if __name__ == "__main__":
    unittest.main()
