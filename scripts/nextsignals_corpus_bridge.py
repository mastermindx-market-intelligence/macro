#!/usr/bin/env python3
"""Bounded temporary bridge for an authorized public-X research backfill.

The API key is read only from TWITTERAPI_IO_KEY. Raw third-party corpus data stays
outside Git; this helper only caches it on the ephemeral runtime and serves the
finished gzip for transfer to the private research volume.
"""
from __future__ import annotations

import gzip
import json
import os
import threading
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = "https://api.twitterapi.io"
TARGET = os.environ.get("TARGET_X_HANDLE", "TailThatWagsDog").lstrip("@")
START = date.fromisoformat(os.environ.get("TARGET_START_DATE", "2024-08-27"))
END = date.fromisoformat(os.environ.get("TARGET_END_DATE", datetime.now(timezone.utc).date().isoformat()))
WINDOW_DAYS = max(1, min(31, int(os.environ.get("WINDOW_DAYS", "14"))))
CACHE = Path(os.environ.get("CORPUS_CACHE", "/tmp/nextsignals-corpus"))
PORT = int(os.environ.get("PORT", "10000"))
KEY = os.environ.get("TWITTERAPI_IO_KEY", "")

STATUS = {
    "state": "starting", "handle": TARGET, "start": START.isoformat(),
    "end": END.isoformat(), "windows_done": 0, "windows_total": 0,
    "pages": 0, "unique_tweets": 0, "error": None, "updated_at": None,
}
LOCK = threading.Lock()


def stamp(**changes):
    with LOCK:
        STATUS.update(changes)
        STATUS["updated_at"] = datetime.now(timezone.utc).isoformat()


def api_get(path: str, params: dict) -> dict:
    if not KEY:
        raise RuntimeError("TWITTERAPI_IO_KEY is missing")
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"X-API-Key": KEY, "User-Agent": "MMX-research-backfill/1"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=45) as res:
                return json.load(res)
        except Exception:
            if attempt == 5:
                raise
            time.sleep(min(30, 1.5 * (2 ** attempt)))
    raise AssertionError("unreachable")


def profile() -> dict:
    return api_get("/twitter/user/info", {"userName": TARGET})


def search_window(start: date, end: date) -> list[dict]:
    query = f"from:{TARGET} since:{start.isoformat()} until:{end.isoformat()}"
    cursor = None
    seen_cursors = set()
    out = []
    for _ in range(1000):
        params = {"query": query, "queryType": "Latest"}
        if cursor:
            params["cursor"] = cursor
        body = api_get("/twitter/tweet/advanced_search", params)
        rows = body.get("tweets") or []
        out.extend(x for x in rows if isinstance(x, dict))
        with LOCK:
            STATUS["pages"] += 1
        nxt = body.get("next_cursor")
        if not nxt or nxt in seen_cursors:
            break
        seen_cursors.add(nxt)
        cursor = nxt
        time.sleep(0.08)
    return out


def corpus_worker():
    CACHE.mkdir(parents=True, exist_ok=True)
    raw_path = CACHE / f"{TARGET}.jsonl.gz"
    manifest_path = CACHE / f"{TARGET}.manifest.json"
    try:
        stamp(state="profiling")
        prof = profile()
        windows = []
        cur = START
        inclusive_end = END + timedelta(days=1)
        while cur < inclusive_end:
            nxt = min(cur + timedelta(days=WINDOW_DAYS), inclusive_end)
            windows.append((cur, nxt))
            cur = nxt
        stamp(state="scraping", windows_total=len(windows))
        by_id = {}
        window_stats = []
        for idx, (a, b) in enumerate(windows, 1):
            rows = search_window(a, b)
            before = len(by_id)
            for row in rows:
                tid = str(row.get("id") or row.get("tweetId") or "")
                if tid:
                    by_id[tid] = row
            window_stats.append({"start": a.isoformat(), "until_exclusive": b.isoformat(), "returned": len(rows), "new_unique": len(by_id)-before})
            stamp(windows_done=idx, unique_tweets=len(by_id))
        rows = list(by_id.values())
        rows.sort(key=lambda x: (x.get("createdAt") or x.get("created_at") or "", str(x.get("id") or "")))
        with gzip.open(raw_path, "wt", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        manifest = {
            "schema": "mmx.external_x_corpus_manifest/v1",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "handle": TARGET,
            "profile": prof,
            "query_window": {"start": START.isoformat(), "end_inclusive": END.isoformat(), "window_days": WINDOW_DAYS},
            "tweet_count": len(rows), "pages": STATUS["pages"], "windows": window_stats,
            "raw_file": raw_path.name,
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        stamp(state="complete", unique_tweets=len(rows))
    except Exception as exc:
        stamp(state="failed", error=f"{type(exc).__name__}: {exc}")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def _json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False, indent=2).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path in ("/", "/status"):
            with LOCK:
                self._json(200, dict(STATUS))
            return
        files = {
            "/manifest": CACHE / f"{TARGET}.manifest.json",
            "/corpus": CACHE / f"{TARGET}.jsonl.gz",
        }
        fp = files.get(path)
        if not fp or not fp.exists():
            self._json(404, {"error": "not ready", "state": STATUS.get("state")})
            return
        data = fp.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/gzip" if path == "/corpus" else "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    threading.Thread(target=corpus_worker, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
