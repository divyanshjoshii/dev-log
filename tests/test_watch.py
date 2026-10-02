import sys
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "chat"))
import core
import watch

NOW = datetime(2026, 10, 3, 16, 30, tzinfo=timezone.utc)  # 22:00 IST
ENV = {"DISPATCH_TOKEN": "t", "TELEGRAM_BOT_TOKEN": "b", "TELEGRAM_CHAT_ID": "42"}


def http_error(code):
    return urllib.error.HTTPError("u", code, "x", {}, None)


class Spy:
    def __init__(self):
        self.dispatched = 0
        self.sent = []

    def dispatch(self, token):
        self.dispatched += 1

    def notify(self, token, chat, text):
        self.sent.append(text)


class WatchdogTest(unittest.TestCase):
    def check(self, mode, messages=None, env=ENV, fetch_error=None, dispatch_error=None):
        spy = Spy()

        def fetch(now, token):
            if fetch_error:
                raise fetch_error
            return messages or []

        def dispatch(token):
            if dispatch_error:
                raise dispatch_error
            spy.dispatch(token)

        result = watch.run_check(env, NOW, mode, fetch=fetch, dispatch=dispatch, notify=spy.notify)
        return result, spy

    def test_commit_present_does_nothing(self):
        result, spy = self.check("final", ["log: 2026-10-03", "other"])
        self.assertEqual((result, spy.dispatched, spy.sent), ("ok", 0, []))

    def test_first_check_starts_a_run_quietly(self):
        result, spy = self.check("first", ["unrelated commit"])
        self.assertEqual((result, spy.dispatched, spy.sent), ("started", 1, []))

    def test_final_check_starts_a_run_and_alerts(self):
        result, spy = self.check("final", [])
        self.assertEqual((result, spy.dispatched), ("started", 1))
        self.assertIn("22:00 IST", spy.sent[0])
        self.assertIn("I started a run", spy.sent[0])

    def test_missing_dispatch_token_alerts_even_on_first_check(self):
        env = {k: v for k, v in ENV.items() if k != "DISPATCH_TOKEN"}
        result, spy = self.check("first", [], env=env)
        self.assertEqual(result, "failed")
        self.assertIn("DISPATCH_TOKEN is not set", spy.sent[0])

    def test_failed_dispatch_alerts_with_code(self):
        result, spy = self.check("first", [], dispatch_error=http_error(403))
        self.assertEqual(result, "failed")
        self.assertIn("403", spy.sent[0])

    def test_unreadable_commits_still_start_a_run(self):
        result, spy = self.check("first", fetch_error=http_error(403))
        self.assertEqual((result, spy.dispatched), ("started", 1))
        self.assertIn("could not read commits", spy.sent[0])


class RunCommandTest(unittest.TestCase):
    ENV = MappingProxyType({"TELEGRAM_CHAT_ID": "42", "GEMINI_API_KEY": "k", "DISPATCH_TOKEN": "t"})

    def run_cmd(self, chat=42, env=None):
        calls = []
        out = core.reply_for(
            {"chat": {"id": chat}, "text": "/run"},
            env or dict(self.ENV),
            dispatcher=lambda token: calls.append(token),
        )
        return out, calls

    def test_owner_can_start_a_run(self):
        out, calls = self.run_cmd()
        self.assertEqual(calls, ["t"])
        self.assertIn("Started", out)

    def test_stranger_cannot(self):
        out, calls = self.run_cmd(chat=7)
        self.assertEqual((out, calls), (None, []))

    def test_missing_token_is_explained(self):
        env = {k: v for k, v in self.ENV.items() if k != "DISPATCH_TOKEN"}
        out, calls = self.run_cmd(env=env)
        self.assertEqual(calls, [])
        self.assertIn("DISPATCH_TOKEN", out)


if __name__ == "__main__":
    unittest.main()
