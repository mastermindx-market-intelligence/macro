#!/usr/bin/env python3
"""Resumable public-X corpus ingest for nextSignals research.

Raw third-party content belongs on the private vendor-source volume, never in Git.
The API key is loaded from TWITTERAPI_IO_KEY or a private key file supplied on-host.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import mimetypes
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

API_BASE = "https://api.twitterapi.io"
DEFAULT_ROOT = Path("/Volumes/Mastermind/vendor-sources/nextsignals")
DEFAULT_KEY_FILE = Path.home() / ".config" / "mastermind" / "twitterapi_io.key"
HTTP_UA = "MMX-nextsignals-research/1.0"
MEDIA_RE = re.compile(r"^https?://(?:pbs\.twimg\.com|video\.twimg\.com)/", re.I)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_key(path: Path) -> str:
    value = os.environ.get("TWITTERAPI_IO_KEY", "").strip()
    if value:
        return value
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    raise RuntimeError(
        "TwitterAPI.io key unavailable. Set TWITTERAPI_IO_KEY or create " + str(path)
    )


def api_get(key: str, path: str, params: dict[str, Any]) -> dict[str, Any]:
    url = API_BASE + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"X-API-Key": key, "User-Agent": HTTP_UA, "Accept": "application/json"},
    )
    last: Exception | None = None
    for attempt in range(7):
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                return json.load(res)
        except Exception as exc:
            last = exc
            if attempt == 6:
                break
            time.sleep(min(45.0, 1.25 * (2**attempt)))
    raise RuntimeError(f"API request failed after retries: {last}")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def write_gz_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
    tmp.replace(path)


def read_gz_json(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def tweet_rows(body: dict[str, Any]) -> list[dict[str, Any]]:
    rows = body.get("tweets")
    if isinstance(rows, list):
        return [x for x in rows if isinstance(x, dict)]
    data = body.get("data")
    if isinstance(data, dict):
        rows = data.get("tweets")
    else:
        rows = data
    return [x for x in (rows or []) if isinstance(x, dict)]


def next_cursor(body: dict[str, Any]) -> str | None:
    for obj in (body, body.get("data") if isinstance(body.get("data"), dict) else {}):
        value = obj.get("next_cursor") or obj.get("nextCursor")
        if value:
            return str(value)
    return None


def iter_windows(start: date, end_inclusive: date, days: int):
    final = end_inclusive + timedelta(days=1)
    cur = start
    while cur < final:
        nxt = min(cur + timedelta(days=days), final)
        yield cur, nxt
        cur = nxt


def window_dir(root: Path, handle: str, start: date, until: date) -> Path:
    return root / "raw" / "api_pages" / handle / f"{start.isoformat()}__{until.isoformat()}"


def fetch_window(key: str, root: Path, handle: str, start: date,
                 until_exclusive: date, pause: float) -> dict[str, Any]:
    dst = window_dir(root, handle, start, until_exclusive)
    done = dst / "DONE.json"
    if done.exists():
        return json.loads(done.read_text(encoding="utf-8"))
    dst.mkdir(parents=True, exist_ok=True)
    query = f"from:{handle} since:{start.isoformat()} until:{until_exclusive.isoformat()}"
    cursor = None
    seen_cursors: set[str] = set()
    page = returned = 0
    ids: set[str] = set()
    while page < 1000:
        params: dict[str, Any] = {"query": query, "queryType": "Latest"}
        if cursor:
            params["cursor"] = cursor
        body = api_get(key, "/twitter/tweet/advanced_search", params)
        page += 1
        rows = tweet_rows(body)
        returned += len(rows)
        for row in rows:
            tid = row.get("id") or row.get("tweetId")
            if tid is not None:
                ids.add(str(tid))
        write_gz_json(dst / f"page_{page:04d}.json.gz", body)
        nxt = next_cursor(body)
        if not nxt or nxt in seen_cursors:
            break
        seen_cursors.add(nxt)
        cursor = nxt
        time.sleep(pause)
    meta = {
        "schema": "mmx.external_x_window/v1", "handle": handle, "query": query,
        "start": start.isoformat(), "until_exclusive": until_exclusive.isoformat(),
        "pages": page, "returned_rows": returned, "unique_ids_in_window": len(ids),
        "completed_at": utcnow(),
    }
    write_json(done, meta)
    return meta


def aggregate(root: Path, handle: str) -> tuple[list[dict[str, Any]], int]:
    base = root / "raw" / "api_pages" / handle
    by_id: dict[str, dict[str, Any]] = {}
    pages = 0
    if not base.exists():
        return [], 0
    for fp in sorted(base.glob("*/*.json.gz")):
        body = read_gz_json(fp)
        pages += 1
        for row in tweet_rows(body):
            tid = row.get("id") or row.get("tweetId")
            if tid is not None:
                by_id[str(tid)] = row
    rows = list(by_id.values())
    rows.sort(key=lambda x: (x.get("createdAt") or x.get("created_at") or "",
                             str(x.get("id") or x.get("tweetId") or "")))
    out = root / "raw" / f"{handle}.tweets.jsonl.gz"
    with gzip.open(out, "wt", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    return rows, pages


def walk_urls(obj: Any):
    if isinstance(obj, str):
        if MEDIA_RE.match(obj):
            yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from walk_urls(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk_urls(value)


def classify_media(url: str) -> str:
    host = urllib.parse.urlsplit(url).netloc.lower()
    if host == "pbs.twimg.com":
        return "image"
    if host == "video.twimg.com":
        return "video"
    return "other"


def media_manifest(root: Path, handle: str,
                   rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        tid = str(row.get("id") or row.get("tweetId") or "")
        for url in walk_urls(row):
            clean = url.replace("http://", "https://", 1)
            key = (tid, clean)
            if not tid or key in seen:
                continue
            seen.add(key)
            entries.append({"tweet_id": tid, "url": clean, "kind": classify_media(clean)})
    entries.sort(key=lambda x: (x["tweet_id"], x["url"]))
    write_json(root / "manifests" / f"{handle}.media.json", entries)
    return entries


def infer_ext(url: str, content_type: str | None) -> str:
    path_ext = Path(urllib.parse.urlsplit(url).path).suffix.lower()
    if path_ext in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4"}:
        return ".jpg" if path_ext == ".jpeg" else path_ext
    ext = mimetypes.guess_extension((content_type or "").split(";", 1)[0].strip())
    return ext or ".bin"


def original_image_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    if parts.netloc.lower() != "pbs.twimg.com":
        return url
    query = urllib.parse.parse_qs(parts.query)
    query["name"] = ["orig"]
    new_query = urllib.parse.urlencode({k: v[-1] for k, v in query.items()})
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path,
                                    new_query, parts.fragment))


def download_images(root: Path, handle: str, entries: list[dict[str, Any]],
                    pause: float) -> dict[str, int]:
    ok = skipped = failed = 0
    log_path = root / "manifests" / f"{handle}.media_downloads.jsonl"
    with log_path.open("a", encoding="utf-8") as log:
        for index, entry in enumerate(entries, 1):
            if entry["kind"] != "image":
                continue
            tid = entry["tweet_id"]
            url = original_image_url(entry["url"])
            digest = hashlib.sha256(entry["url"].encode()).hexdigest()[:16]
            tweet_dir = root / "media" / handle / tid
            existing = list(tweet_dir.glob(digest + ".*")) if tweet_dir.exists() else []
            if existing:
                skipped += 1
                continue
            req = urllib.request.Request(url, headers={"User-Agent": HTTP_UA})
            try:
                with urllib.request.urlopen(req, timeout=60) as res:
                    data = res.read()
                    ext = infer_ext(url, res.headers.get("Content-Type"))
                tweet_dir.mkdir(parents=True, exist_ok=True)
                path = tweet_dir / (digest + ext)
                path.write_bytes(data)
                rec = {**entry, "requested_url": url, "path": str(path),
                       "bytes": len(data), "status": "ok", "at": utcnow()}
                ok += 1
            except Exception as exc:
                rec = {**entry, "requested_url": url, "status": "failed",
                       "error": f"{type(exc).__name__}: {exc}", "at": utcnow()}
                failed += 1
            log.write(json.dumps(rec, ensure_ascii=False) + "\n")
            log.flush()
            if index % 50 == 0:
                print(f"media: {index}/{len(entries)} ok={ok} skipped={skipped} failed={failed}", flush=True)
            time.sleep(pause)
    return {"ok": ok, "skipped": skipped, "failed": failed}


def run_handle(args, key: str, handle: str) -> None:
    root = args.root
    root.mkdir(parents=True, exist_ok=True)
    print(f"[{handle}] profile", flush=True)
    profile = api_get(key, "/twitter/user/info", {"userName": handle})
    write_json(root / "raw" / f"{handle}.profile.json", profile)
    windows = list(iter_windows(args.start, args.end, args.window_days))
    stats = []
    for idx, (a, b) in enumerate(windows, 1):
        meta = fetch_window(key, root, handle, a, b, args.pause)
        stats.append(meta)
        print(f"[{handle}] window {idx}/{len(windows)} {a}..{b} "
              f"pages={meta['pages']} rows={meta['returned_rows']}", flush=True)
    rows, pages = aggregate(root, handle)
    media = media_manifest(root, handle, rows)
    images = sum(1 for x in media if x["kind"] == "image")
    videos = sum(1 for x in media if x["kind"] == "video")
    manifest = {
        "schema": "mmx.external_x_corpus_manifest/v1", "captured_at": utcnow(),
        "handle": handle,
        "date_range": {"start": args.start.isoformat(), "end_inclusive": args.end.isoformat()},
        "window_days": args.window_days, "profile": profile, "tweet_count": len(rows),
        "api_pages": pages, "windows": stats, "media_url_count": len(media),
        "image_url_count": images, "video_url_count": videos,
        "rights_boundary": "private research archive; derived findings only enter Git",
    }
    if args.download_images:
        manifest["image_downloads_this_run"] = download_images(root, handle, media, args.media_pause)
    write_json(root / "manifests" / f"{handle}.corpus.json", manifest)
    print(f"[{handle}] COMPLETE tweets={len(rows)} media_urls={len(media)} images={images} videos={videos}", flush=True)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", action="append", required=True, help="X handle; repeatable")
    ap.add_argument("--start", type=date.fromisoformat, required=True)
    ap.add_argument("--end", type=date.fromisoformat, default=datetime.now(timezone.utc).date())
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--key-file", type=Path, default=DEFAULT_KEY_FILE)
    ap.add_argument("--window-days", type=int, default=14)
    ap.add_argument("--pause", type=float, default=0.12)
    ap.add_argument("--media-pause", type=float, default=0.03)
    ap.add_argument("--download-images", action="store_true")
    args = ap.parse_args()
    if args.window_days < 1 or args.window_days > 31:
        ap.error("--window-days must be between 1 and 31")
    if args.start > args.end:
        ap.error("--start must be <= --end")
    return args


def main() -> int:
    args = parse_args()
    key = load_key(args.key_file)
    for handle in args.handle:
        run_handle(args, key, handle.lstrip("@"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
