"""Read-only comparison of a captured/public HTML board with one immutable artifact.

Use --html to inspect a previously captured page, or omit it for one public HTTP
GET. --observed-at is required with --html so replay is not misdated as a new
production observation. This verifies server-rendered membership and order;
it does not run JavaScript or establish deployment/source identity.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import urllib.request

PIN = "3d90aad6d83152dfeeaf8345bc995826ac9d3139"
URL = "https://mastermind-x.com/china_stocks.html"


class Cards(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cards = []

    def handle_starttag(self, tag, attrs):
        row = dict(attrs)
        if tag == "a" and "pvcard" in row.get("class", "").split():
            self.cards.append({k: row.get(k) for k in ("class", "data-ticker", "href")})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--sha", default=PIN)
    ap.add_argument("--url", default=URL)
    ap.add_argument("--html")
    ap.add_argument("--observed-at")
    args = ap.parse_args()
    if args.html:
        if not args.observed_at:
            ap.error("--html requires its actual --observed-at timestamp")
        raw = Path(args.html).read_bytes()
        observed_at = args.observed_at
    else:
        with urllib.request.urlopen(args.url, timeout=15) as response:
            raw = response.read()
        observed_at = datetime.now(timezone.utc).isoformat()
    page = raw.decode("utf-8")
    source = subprocess.check_output([
        "git", "-C", args.repo, "show", args.sha + ":site/factordata/china_standouts.json"
    ])
    board = json.loads(source)
    parser = Cards()
    parser.feed(page)
    featured = [r["data-ticker"] for r in parser.cards if "pv-featured" in r["class"].split()]
    overflow = [r["data-ticker"] for r in parser.cards if "pv-featured" not in r["class"].split()]
    expected_featured = [r["ticker"] for r in board["buy"]]
    expected_more_by_score = [r["ticker"] for r in sorted(
        board["more_actionable"], key=lambda r: -float(r["prophet"]["score"])
    )]
    result = {
        "source_sha": args.sha, "observed_at": observed_at, "url": args.url,
        "html_bytes": len(raw), "html_sha256": hashlib.sha256(raw).hexdigest(),
        "artifact_sha256": hashlib.sha256(source).hexdigest(),
        "title": re.findall(r"<title[^>]*>(.*?)</title>", page, re.S)[0],
        "card_count": len(parser.cards),
        "card_class_counts": dict(Counter(r["class"] for r in parser.cards)),
        "featured_n": len(featured), "overflow_n": len(overflow),
        "featured_same_names_and_order_as_pinned_artifact": featured == expected_featured,
        "overflow_same_names_and_score_order_as_pinned_artifact": overflow == expected_more_by_score,
        "featured_tickers": featured,
        "overflow_tickers": overflow,
        "scope": "Server-rendered HTML only; no JavaScript, visual layout, authenticated JSON, exact deployed source SHA, live event consumption or trading proof.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
