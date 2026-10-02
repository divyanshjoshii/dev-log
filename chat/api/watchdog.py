import hmac
import os
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import watch


class handler(BaseHTTPRequestHandler):
    def _reply(self, code, body=""):
        self.send_response(code)
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        secret = os.environ.get("CRON_SECRET", "")
        got = self.headers.get("Authorization", "")
        if not secret or not hmac.compare_digest(got.encode(), f"Bearer {secret}".encode()):
            return self._reply(401)
        mode = parse_qs(urlparse(self.path).query).get("mode", [None])[0]
        if mode not in ("first", "final"):
            schedule = self.headers.get("x-vercel-cron-schedule")
            mode = "final" if schedule == watch.FINAL_SCHEDULE else "first"
        try:
            result = watch.run_check(os.environ, datetime.now(timezone.utc), mode)
        except Exception as exc:  # noqa: BLE001  report the type only, never details
            print("error:", type(exc).__name__)
            result = "error"
        self._reply(200, result)
