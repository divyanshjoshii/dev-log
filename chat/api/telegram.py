import hmac
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import core


class handler(BaseHTTPRequestHandler):
    def _done(self, code=200):
        self.send_response(code)
        self.end_headers()

    def do_POST(self):
        env = os.environ
        got = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        expected = core.webhook_secret(env["TELEGRAM_BOT_TOKEN"])
        if not hmac.compare_digest(got.encode(), expected.encode()):
            return self._done(403)
        message = {}
        try:
            length = int(self.headers.get("Content-Length", 0))
            message = json.loads(self.rfile.read(length)).get("message") or {}
            reply = core.reply_for(message, env)
            if reply:
                core.send_telegram(env["TELEGRAM_BOT_TOKEN"], message["chat"]["id"], reply)
        except Exception as exc:  # noqa: BLE001  always answer 200 or Telegram retries
            detail = f"{type(exc).__name__} {getattr(exc, 'code', '')}".strip()
            print("error:", detail)
            chat = message.get("chat", {}).get("id")
            if str(chat) == str(env.get("TELEGRAM_CHAT_ID")):  # only ever tell the owner
                core.send_telegram(
                    env["TELEGRAM_BOT_TOKEN"], chat, f"Something went wrong ({detail})."
                )
        self._done()

    def do_GET(self):
        self._done(404)
