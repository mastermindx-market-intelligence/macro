#!/usr/bin/env python3
"""L6.4 capture server (lanes/L6_capture.md): a 127.0.0.1 static server over the L6 render tree.

Usage: serve_l6.py <out_dir> <worktree> <port> <log.jsonl>

Lookup for a request path (the `?v=` cache-buster and any query are dropped):
  1. header X-L6-Variant: <v>  ->  <out>/_variants/<v>/<path>
  2. <out>/<path>              (never _variants/ or _l6_written.json)
  3. `git cat-file blob HEAD:site/<path>` in <worktree>, logged source=head-fallback
     (a blob:none partial clone may fetch the blob lazily; recorded as a GAP, never silent)
  4. 404, logged
premiumdata/* answers 401, the anonymous production response. Every request is one JSONL
line: path, variant, source, status, bytes, sha256. Nothing is written outside <log>.
"""
import hashlib, http.server, json, os, posixpath, subprocess, sys, threading, urllib.parse

OUT, WT, PORT, LOG = os.path.realpath(sys.argv[1]), sys.argv[2], int(sys.argv[3]), sys.argv[4]
TYPES = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
         ".woff2": "font/woff2", ".woff": "font/woff", ".png": "image/png", ".svg": "image/svg+xml",
         ".ico": "image/x-icon", ".txt": "text/plain; charset=utf-8", ".webmanifest": "application/manifest+json"}
_lock, _head = threading.Lock(), {}


def head_blob(rel):
    with _lock:
        if rel not in _head:
            p = subprocess.run(["git", "-C", WT, "cat-file", "blob", f"HEAD:site/{rel}"], capture_output=True)
            _head[rel] = p.stdout if p.returncode == 0 else None
        return _head[rel]


def resolve(rel, variant):
    if variant:
        p = os.path.realpath(os.path.join(OUT, "_variants", variant, rel))
        if p.startswith(OUT + os.sep) and os.path.isfile(p):
            return open(p, "rb").read(), f"variant:{variant}"
    top = rel.split("/", 1)[0]
    if top not in ("_variants", "_l6_written.json"):
        p = os.path.realpath(os.path.join(OUT, rel))
        if p.startswith(OUT + os.sep) and os.path.isfile(p):
            return open(p, "rb").read(), "out"
    b = head_blob(rel)
    if b is not None:
        return b, "head-fallback"
    return None, "missing"


class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, status, body, ctype, rec):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
        rec.update(status=status, bytes=len(body), sha256=hashlib.sha256(body).hexdigest() if body else None)
        with _lock, open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")

    def do_GET(self):
        raw = urllib.parse.urlsplit(self.path).path
        rel = posixpath.normpath(urllib.parse.unquote(raw)).lstrip("/")
        variant = self.headers.get("X-L6-Variant") or None
        rec = dict(path=raw, variant=variant)
        if not rel or rel == ".":
            rel = "index.html"
        if ".." in rel.split("/"):
            rec["source"] = "rejected"
            return self._send(403, b"", "text/plain", rec)
        if rel.split("/", 1)[0] == "premiumdata":
            rec["source"] = "premium-anonymous"
            return self._send(401, b"", "text/plain", rec)
        body, src = resolve(rel, variant)
        rec["source"] = src
        if body is None:
            return self._send(404, b"", "text/plain", rec)
        return self._send(200, body, TYPES.get(os.path.splitext(rel)[1].lower(), "application/octet-stream"), rec)

    do_HEAD = do_GET


if __name__ == "__main__":
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print(f"serve_l6 127.0.0.1:{PORT} out={OUT}", flush=True)
    srv.serve_forever()
