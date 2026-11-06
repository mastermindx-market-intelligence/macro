"""Loopback-only visual review of the actual Macro template and local assets."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
SITE = (ROOT / "site").resolve()
REVIEW = Path(__file__).resolve().parent / "sector_central.html"

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE), **kwargs)

    def do_GET(self):
        route = unquote(urlsplit(self.path).path)
        if route in ("/", "/sector_central.html"):
            if not REVIEW.is_file():
                self.send_error(503, "Review render is not ready")
                return
            data = REVIEW.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        # Review is anonymous; existing withheld content is never served here.
        if route.startswith(("/premiumdata/", "/api/", "/auth/")):
            self.send_error(401, "Anonymous visual review")
            return
        target = (SITE / route.lstrip("/")).resolve()
        if not target.is_relative_to(SITE) or not target.is_file():
            self.send_error(404)
            return
        super().do_GET()

    def do_POST(self):
        self.send_error(405, "Review is read-only")

    def list_directory(self, path):
        self.send_error(404)
        return None

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "connect-src 'self'")
        super().end_headers()

    def log_message(self, format, *args):
        pass

server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
print("MACRO_REVIEW_URL=http://127.0.0.1:" + str(server.server_port) + "/sector_central.html#overview", flush=True)
server.serve_forever()
