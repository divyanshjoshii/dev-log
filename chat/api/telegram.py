import hmac
import json
import os
import sys
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import core


def send(token, chat_id, text):
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    urllib.request.urlopen(req, timeout=15).read()


class handler(BaseHTTPRequestHandler):
    def _done(self, code=200):
        self.send_response(code)
        self.end_headers()

    def do_POST(self):
        env = os.environ
        got = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not hmac.compare_digest(got, core.webhook_secret(env["TELEGRAM_BOT_TOKEN"])):
            return self._done(403)
        try:
            length = int(self.headers.get("Content-Length", 0))
            message = json.loads(self.rfile.read(length)).get("message") or {}
            reply = core.reply_for(message, env)
            if reply:
                send(env["TELEGRAM_BOT_TOKEN"], message["chat"]["id"], reply)
        except Exception as exc:  # noqa: BLE001  always answer 200 or Telegram retries; log type only
            print("error:", type(exc).__name__)
        self._done()

    def do_GET(self):
        self._done(404)
